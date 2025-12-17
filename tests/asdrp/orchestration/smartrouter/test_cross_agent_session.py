"""
Unit and integration tests for cross-agent session memory in SmartRouter.

Tests the fix for cross-agent context sharing where session memory
was isolated per agent, preventing context flow between different
agents across conversation turns.

Fix: Use shared session ID for all agents (remove _{agent_id} suffix)
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
from asdrp.orchestration.smartrouter.async_subquery_dispatcher import AsyncSubqueryDispatcher
from asdrp.orchestration.smartrouter.interfaces import QueryIntent, QueryComplexity, Subquery, RoutingPattern
from asdrp.orchestration.smartrouter.trace_capture import TraceCapture


class TestSharedSessionUsage:
    """Test that shared session ID is used for all agents."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock agent factory."""
        factory = Mock()
        factory.get_agent_with_session = AsyncMock(
            return_value=(Mock(name="TestAgent"), Mock(session_id="shared_session"))
        )
        factory.get_agent = AsyncMock(return_value=Mock(name="TestAgent"))
        return factory

    @pytest.fixture
    def smartrouter(self, mock_factory):
        """Create SmartRouter with mocked components."""
        config = Mock()
        config.models = Mock()
        config.evaluation = Mock()
        config.evaluation.fallback_message = "Fallback"
        config.capabilities = {"one": ["search"], "yelp": ["local_business"]}

        capability_router = Mock()
        capability_router.can_route = Mock(return_value=True)
        capability_router._find_candidate_agents = Mock(return_value=["one"])

        return SmartRouter(
            config=config,
            agent_factory=mock_factory,
            capability_router=capability_router,
            session_id="test_session_123"
        )

    @pytest.mark.asyncio
    async def test_shared_session_no_agent_suffix(self, smartrouter, mock_factory):
        """Test that session ID has NO _{agent_id} suffix."""
        intent = QueryIntent(
            original_query="Test query",
            complexity=QueryComplexity.SIMPLE,
            domains=["search"],
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Test response")

            await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Verify session_id passed WITHOUT agent suffix
        mock_factory.get_agent_with_session.assert_called_once()
        call_args = mock_factory.get_agent_with_session.call_args

        assert call_args[1]['session_id'] == "test_session_123"  # NO suffix!
        assert "_one" not in call_args[1]['session_id']
        assert "_yelp" not in call_args[1]['session_id']

    @pytest.mark.asyncio
    async def test_same_session_for_different_agents(self, smartrouter, mock_factory):
        """Test that different agents receive the SAME session ID."""
        intent = QueryIntent(
            original_query="Test query",
            complexity=QueryComplexity.SIMPLE,
            domains=["search"],
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        # First agent call
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Response 1")
            await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        first_call_session = mock_factory.get_agent_with_session.call_args[1]['session_id']

        # Second agent call (simulate different agent)
        smartrouter.router._find_candidate_agents = Mock(return_value=["yelp"])
        intent.domains = ["local_business"]

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Response 2")
            await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        second_call_session = mock_factory.get_agent_with_session.call_args[1]['session_id']

        # Both agents should receive SAME session ID
        assert first_call_session == second_call_session
        assert first_call_session == "test_session_123"

    @pytest.mark.asyncio
    async def test_session_consistency_across_turns(self, smartrouter, mock_factory):
        """Test session ID consistency across multiple conversation turns."""
        turns = [
            ("What is the capital of France?", "search"),
            ("Thai restaurants there", "local_business"),
            ("Show me directions", "mapping"),
        ]

        session_ids_used = []

        for query, domain in turns:
            intent = QueryIntent(
                original_query=query,
                complexity=QueryComplexity.SIMPLE,
                domains=[domain],
                requires_synthesis=False,
                metadata={}
            )

            trace_capture = TraceCapture()

            with patch('agents.Runner.run') as mock_run:
                mock_run.return_value = MagicMock(final_output=f"Response for {query}")
                await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

            session_id = mock_factory.get_agent_with_session.call_args[1]['session_id']
            session_ids_used.append(session_id)

        # All turns should use SAME session ID
        assert len(set(session_ids_used)) == 1  # Only one unique session ID
        assert session_ids_used[0] == "test_session_123"


class TestAsyncSubqueryDispatcherSession:
    """Test that AsyncSubqueryDispatcher uses shared session."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock agent factory."""
        factory = Mock()
        factory.get_agent_with_session = AsyncMock(
            return_value=(Mock(name="TestAgent"), Mock(session_id="shared_session"))
        )
        return factory

    @pytest.fixture
    def dispatcher(self, mock_factory):
        """Create AsyncSubqueryDispatcher with mocked factory."""
        from asdrp.orchestration.smartrouter.config_loader import ErrorHandlingConfig

        error_config = ErrorHandlingConfig(
            timeout=30,
            retries=2
        )

        return AsyncSubqueryDispatcher(
            agent_factory=mock_factory,
            error_config=error_config,
            session_id="dispatcher_session_456"
        )

    @pytest.mark.asyncio
    async def test_dispatcher_uses_shared_session(self, dispatcher, mock_factory):
        """Test that dispatcher passes shared session (no agent suffix)."""
        subquery = Subquery(
            id="sq1",
            text="Test subquery",
            capability_required="search",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Subquery response")

            await dispatcher._execute_subquery(subquery, "one")

        # Verify session_id has NO agent suffix
        mock_factory.get_agent_with_session.assert_called_once()
        call_args = mock_factory.get_agent_with_session.call_args

        assert call_args[1]['session_id'] == "dispatcher_session_456"
        assert "_one" not in call_args[1]['session_id']


class TestCrossAgentContextFlow:
    """Integration tests for context flow between agents."""

    @pytest.fixture
    def mock_factory_with_session_memory(self):
        """Create mock factory that simulates session memory accumulation."""
        factory = Mock()

        # Simulate session messages accumulating
        session_messages = []

        async def mock_get_agent_with_session(agent_id, session_id):
            # Create mock session with accumulated messages
            mock_session = Mock()
            mock_session.session_id = session_id
            mock_session.messages = list(session_messages)  # Copy current messages

            # Mock agent
            mock_agent = Mock()
            mock_agent.name = agent_id

            return (mock_agent, mock_session)

        factory.get_agent_with_session = AsyncMock(side_effect=mock_get_agent_with_session)
        factory._session_messages = session_messages  # Store reference for test validation

        return factory

    @pytest.fixture
    def smartrouter_with_memory(self, mock_factory_with_session_memory):
        """Create SmartRouter with session memory simulation."""
        config = Mock()
        config.models = Mock()
        config.evaluation = Mock()
        config.evaluation.fallback_message = "Fallback"
        config.capabilities = {
            "wiki": ["wikipedia", "search"],
            "yelp": ["local_business"],
        }

        capability_router = Mock()
        capability_router.can_route = Mock(return_value=True)

        def mock_find_candidates(capability):
            if capability == "wikipedia":
                return ["wiki"]
            elif capability == "local_business":
                return ["yelp"]
            else:
                return ["wiki"]

        capability_router._find_candidate_agents = Mock(side_effect=mock_find_candidates)

        return SmartRouter(
            config=config,
            agent_factory=mock_factory_with_session_memory,
            capability_router=capability_router,
            session_id="cross_agent_session"
        )

    @pytest.mark.asyncio
    async def test_wiki_to_yelp_context_flow(self, smartrouter_with_memory, mock_factory_with_session_memory):
        """
        Test context flow: Turn 1 (Wiki: Paris) → Turn 2 (Yelp: restaurants there).

        This is the EXACT scenario from user's screenshot.
        """
        # Turn 1: Ask wiki agent about Paris
        intent1 = QueryIntent(
            original_query="What is the capital of France?",
            complexity=QueryComplexity.SIMPLE,
            domains=["wikipedia"],
            requires_synthesis=False,
            metadata={}
        )

        trace1 = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="The capital of France is Paris.")

            await smartrouter_with_memory._handle_simple_query_with_trace(intent1, trace1)

        # Simulate session message being added after Turn 1
        mock_factory_with_session_memory._session_messages.append({
            "role": "user",
            "content": "What is the capital of France?"
        })
        mock_factory_with_session_memory._session_messages.append({
            "role": "assistant",
            "content": "The capital of France is Paris."
        })

        # Turn 2: Ask yelp agent about restaurants (context-dependent query)
        intent2 = QueryIntent(
            original_query="Please give me a few Thai restaurants there",
            complexity=QueryComplexity.SIMPLE,
            domains=["local_business"],
            requires_synthesis=False,
            metadata={}
        )

        trace2 = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            # Mock yelp agent getting context from shared session
            def mock_run_with_session(starting_agent, input, session):
                # Verify session has messages from Turn 1
                assert len(session.messages) == 2
                assert "capital of France" in session.messages[0]["content"]
                assert "Paris" in session.messages[1]["content"]

                return MagicMock(final_output="Here are Thai restaurants in Paris...")

            mock_run.side_effect = mock_run_with_session

            await smartrouter_with_memory._handle_simple_query_with_trace(intent2, trace2)

        # Verify both agents received SAME session ID
        calls = mock_factory_with_session_memory.get_agent_with_session.call_args_list
        assert len(calls) == 2

        session_id_turn1 = calls[0][1]['session_id']
        session_id_turn2 = calls[1][1]['session_id']

        assert session_id_turn1 == session_id_turn2
        assert session_id_turn1 == "cross_agent_session"

    @pytest.mark.asyncio
    async def test_finance_to_wiki_context_flow(self, smartrouter_with_memory, mock_factory_with_session_memory):
        """Test context flow: Turn 1 (Finance: AAPL stock) → Turn 2 (Wiki: company info)."""
        # Configure capabilities for finance
        smartrouter_with_memory.config.capabilities["finance"] = ["finance"]
        smartrouter_with_memory.router._find_candidate_agents = Mock(
            side_effect=lambda cap: ["finance"] if cap == "finance" else ["wiki"]
        )

        # Turn 1: Finance query
        intent1 = QueryIntent(
            original_query="Stock price of AAPL",
            complexity=QueryComplexity.SIMPLE,
            domains=["finance"],
            requires_synthesis=False,
            metadata={}
        )

        trace1 = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="AAPL: $150.00")
            await smartrouter_with_memory._handle_simple_query_with_trace(intent1, trace1)

        # Turn 2: Wiki query (context-dependent)
        intent2 = QueryIntent(
            original_query="Tell me about this company",
            complexity=QueryComplexity.SIMPLE,
            domains=["wikipedia"],
            requires_synthesis=False,
            metadata={}
        )

        trace2 = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Apple Inc. is a technology company...")
            await smartrouter_with_memory._handle_simple_query_with_trace(intent2, trace2)

        # Verify shared session ID
        calls = mock_factory_with_session_memory.get_agent_with_session.call_args_list
        assert all(call[1]['session_id'] == "cross_agent_session" for call in calls)


class TestSessionIsolationBetweenConversations:
    """Test that different base session_ids remain isolated."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock agent factory."""
        factory = Mock()
        factory.get_agent_with_session = AsyncMock(
            return_value=(Mock(name="TestAgent"), Mock(session_id="test_session"))
        )
        return factory

    @pytest.mark.asyncio
    async def test_different_conversations_have_different_sessions(self, mock_factory):
        """Test that different SmartRouter instances use different sessions."""
        config = Mock()
        config.models = Mock()
        config.evaluation = Mock()
        config.evaluation.fallback_message = "Fallback"
        config.capabilities = {"one": ["search"]}

        capability_router = Mock()
        capability_router.can_route = Mock(return_value=True)
        capability_router._find_candidate_agents = Mock(return_value=["one"])

        # Create two SmartRouter instances with different session IDs
        router1 = SmartRouter(
            config=config,
            agent_factory=mock_factory,
            capability_router=capability_router,
            session_id="conversation_1"
        )

        router2 = SmartRouter(
            config=config,
            agent_factory=mock_factory,
            capability_router=capability_router,
            session_id="conversation_2"
        )

        intent = QueryIntent(
            original_query="Test query",
            complexity=QueryComplexity.SIMPLE,
            domains=["search"],
            requires_synthesis=False,
            metadata={}
        )

        trace = TraceCapture()

        # Execute on both routers
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Response")

            await router1._handle_simple_query_with_trace(intent, trace)
            session_id_1 = mock_factory.get_agent_with_session.call_args[1]['session_id']

            await router2._handle_simple_query_with_trace(intent, trace)
            session_id_2 = mock_factory.get_agent_with_session.call_args[1]['session_id']

        # Different conversations should have different session IDs
        assert session_id_1 != session_id_2
        assert session_id_1 == "conversation_1"
        assert session_id_2 == "conversation_2"


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock agent factory."""
        factory = Mock()
        factory.get_agent_with_session = AsyncMock(
            return_value=(Mock(name="TestAgent"), Mock(session_id="test_session"))
        )
        factory.get_agent = AsyncMock(return_value=Mock(name="TestAgent"))
        return factory

    @pytest.mark.asyncio
    async def test_no_session_mode_still_works(self, mock_factory):
        """Test that SmartRouter without session_id still works."""
        config = Mock()
        config.models = Mock()
        config.evaluation = Mock()
        config.evaluation.fallback_message = "Fallback"
        config.capabilities = {"one": ["search"]}

        capability_router = Mock()
        capability_router.can_route = Mock(return_value=True)
        capability_router._find_candidate_agents = Mock(return_value=["one"])

        # Create SmartRouter WITHOUT session_id
        router = SmartRouter(
            config=config,
            agent_factory=mock_factory,
            capability_router=capability_router,
            session_id=None  # No session
        )

        intent = QueryIntent(
            original_query="Test query",
            complexity=QueryComplexity.SIMPLE,
            domains=["search"],
            requires_synthesis=False,
            metadata={}
        )

        trace = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Response")

            await router._handle_simple_query_with_trace(intent, trace)

        # Should use get_agent (no session) instead of get_agent_with_session
        mock_factory.get_agent.assert_called_once()
        mock_factory.get_agent_with_session.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
