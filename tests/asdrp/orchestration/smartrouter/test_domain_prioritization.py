"""
Unit tests for SmartRouter domain prioritization.

Tests the fix for restaurant routing failure where SmartRouter
was only using the first domain from QueryInterpreter instead of
prioritizing specialized domains.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
from asdrp.orchestration.smartrouter.interfaces import QueryIntent, QueryComplexity
from asdrp.orchestration.smartrouter.trace_capture import TraceCapture


class TestDomainPrioritization:
    """Test domain prioritization logic in simple query routing."""

    @pytest.fixture
    def mock_router_components(self):
        """Create mock components for SmartRouter."""
        config = Mock()
        config.models = Mock()
        config.evaluation = Mock()
        config.evaluation.fallback_message = "Fallback"
        config.capabilities = {"yelp": ["local_business"], "one": ["search"]}  # Mock capabilities dict

        agent_factory = Mock()

        # Mock capability router
        capability_router = Mock()
        capability_router.can_route = Mock(return_value=True)
        capability_router._find_candidate_agents = Mock(return_value=["yelp"])

        return config, agent_factory, capability_router

    @pytest.fixture
    def smartrouter(self, mock_router_components):
        """Create SmartRouter instance with mocked components."""
        config, agent_factory, capability_router = mock_router_components

        router = SmartRouter(
            config=config,
            agent_factory=agent_factory,
            capability_router=capability_router,
            session_id="test_session"
        )

        return router

    @pytest.mark.asyncio
    async def test_local_business_prioritized_over_search(self, smartrouter, mock_router_components):
        """Test that local_business domain is prioritized over search."""
        config, agent_factory, capability_router = mock_router_components

        # Mock agent execution
        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="YelpAgent"), None))

        # Simulate QueryInterpreter returning domains in WRONG order
        intent = QueryIntent(
            original_query="Recommend restaurants in Tokyo",
            complexity=QueryComplexity.SIMPLE,
            domains=["search", "local_business"],  # ❌ Wrong order
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        # Mock Runner.run to avoid actual agent execution
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Restaurant recommendations")

            # Execute routing
            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should have selected local_business (priority 10) over search (priority 1)
        # Verify capability_router was called with "local_business"
        capability_router._find_candidate_agents.assert_called_with("local_business")

    @pytest.mark.asyncio
    async def test_finance_prioritized_over_search(self, smartrouter, mock_router_components):
        """Test that finance domain is prioritized over search."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="FinanceAgent"), None))

        intent = QueryIntent(
            original_query="Stock price of AAPL",
            complexity=QueryComplexity.SIMPLE,
            domains=["search", "finance"],  # Wrong order
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Stock price: $150.00")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should prioritize finance (priority 9) over search (priority 1)
        capability_router._find_candidate_agents.assert_called_with("finance")

    @pytest.mark.asyncio
    async def test_geocoding_prioritized_over_search(self, smartrouter, mock_router_components):
        """Test that geocoding domain is prioritized over search."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="GeoAgent"), None))

        intent = QueryIntent(
            original_query="Coordinates of Tokyo",
            complexity=QueryComplexity.SIMPLE,
            domains=["search", "geocoding"],
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="35.6762° N, 139.6503° E")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should prioritize geocoding (priority 8) over search (priority 1)
        capability_router._find_candidate_agents.assert_called_with("geocoding")

    @pytest.mark.asyncio
    async def test_search_only_when_no_specialized_domain(self, smartrouter, mock_router_components):
        """Test that search is used when it's the only domain."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="OneAgent"), None))

        intent = QueryIntent(
            original_query="What is the weather today?",
            complexity=QueryComplexity.SIMPLE,
            domains=["search"],  # Only search
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Sunny, 72°F")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should use search since it's the only option
        capability_router._find_candidate_agents.assert_called_with("search")

    @pytest.mark.asyncio
    async def test_multiple_specialized_domains_highest_priority_wins(self, smartrouter, mock_router_components):
        """Test that highest priority domain wins among multiple specialized domains."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="YelpAgent"), None))

        intent = QueryIntent(
            original_query="Find Italian restaurants and get directions",
            complexity=QueryComplexity.SIMPLE,
            domains=["mapping", "local_business", "search"],  # Multiple domains
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Italian restaurants found")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # local_business (priority 10) > mapping (priority 7) > search (priority 1)
        capability_router._find_candidate_agents.assert_called_with("local_business")

    @pytest.mark.asyncio
    async def test_fallback_to_alternative_domain_if_primary_not_routable(self, smartrouter, mock_router_components):
        """Test fallback to alternative domain if primary cannot be routed."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="SearchAgent"), None))

        # Mock: local_business NOT routable, but search IS routable
        def can_route_mock(capability):
            return capability != "local_business"

        capability_router.can_route = Mock(side_effect=can_route_mock)
        capability_router._find_candidate_agents = Mock(return_value=["one"])

        intent = QueryIntent(
            original_query="Find restaurants",
            complexity=QueryComplexity.SIMPLE,
            domains=["local_business", "search"],
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Restaurant search results")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should fall back to search since local_business not routable
        # Verify can_route was called for local_business first
        capability_router.can_route.assert_any_call("local_business")

    @pytest.mark.asyncio
    async def test_unknown_domain_defaults_to_priority_zero(self, smartrouter, mock_router_components):
        """Test that unknown domains get priority 0 (lower than search)."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="SearchAgent"), None))

        intent = QueryIntent(
            original_query="Some query",
            complexity=QueryComplexity.SIMPLE,
            domains=["unknown_domain", "search"],  # Unknown domain
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Search results")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should prioritize search (priority 1) over unknown_domain (priority 0)
        capability_router._find_candidate_agents.assert_called_with("search")

    @pytest.mark.asyncio
    async def test_conversation_domain_routing(self, smartrouter, mock_router_components):
        """Test that conversation/social domains route to chitchat agent."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="ChitchatAgent"), None))

        # Mock: chitchat agent is available
        capability_router._find_candidate_agents = Mock(return_value=["chitchat"])

        intent = QueryIntent(
            original_query="Hello, how are you?",
            complexity=QueryComplexity.SIMPLE,
            domains=["conversation", "social"],
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Hello! I'm doing great!")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should route to conversation capability
        capability_router._find_candidate_agents.assert_called_with("conversation")
        assert agent_id == "chitchat"

    @pytest.mark.asyncio
    async def test_empty_domains_defaults_to_search(self, smartrouter, mock_router_components):
        """Test that empty domains list defaults to search."""
        config, agent_factory, capability_router = mock_router_components

        agent_factory.get_agent_with_session = AsyncMock(return_value=(Mock(name="SearchAgent"), None))

        intent = QueryIntent(
            original_query="Generic query",
            complexity=QueryComplexity.SIMPLE,
            domains=[],  # Empty
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Generic search results")

            answer, agent_id = await smartrouter._handle_simple_query_with_trace(intent, trace_capture)

        # Should default to search
        capability_router._find_candidate_agents.assert_called_with("search")


class TestRestaurantQueryScenarios:
    """Test specific restaurant query scenarios that previously failed."""

    @pytest.fixture
    def mock_router(self):
        """Create a SmartRouter with realistic mocking."""
        config = Mock()
        config.models = Mock()
        config.evaluation = Mock()
        config.evaluation.fallback_message = "Fallback"
        config.capabilities = {"yelp": ["local_business"], "one": ["search"]}  # Mock capabilities dict

        agent_factory = Mock()
        agent_factory.get_agent_with_session = AsyncMock(
            return_value=(Mock(name="YelpAgent"), None)
        )

        capability_router = Mock()
        capability_router.can_route = Mock(return_value=True)
        capability_router._find_candidate_agents = Mock(return_value=["yelp"])

        router = SmartRouter(
            config=config,
            agent_factory=agent_factory,
            capability_router=capability_router,
            session_id="test"
        )

        return router, capability_router

    @pytest.mark.asyncio
    async def test_context_based_restaurant_query(self, mock_router):
        """
        Test: "Recommend the top 3 restaurants there"
        (where "there" refers to Tokyo from previous turn)

        This was the ORIGINAL BUG reported by user.
        """
        router, capability_router = mock_router

        # LLM might return domains in either order
        intent = QueryIntent(
            original_query="Recommend the top 3 restaurants there",
            complexity=QueryComplexity.SIMPLE,
            domains=["search", "local_business"],  # Wrong order
            requires_synthesis=False,
            metadata={"context": "Tokyo from previous turn"}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Top 3 restaurants in Tokyo")

            answer, agent_id = await router._handle_simple_query_with_trace(intent, trace_capture)

        # MUST route to local_business (Yelp), NOT search
        capability_router._find_candidate_agents.assert_called_with("local_business")

    @pytest.mark.asyncio
    async def test_explicit_restaurant_query(self, mock_router):
        """Test: "Find the best sushi restaurants in Tokyo" """
        router, capability_router = mock_router

        intent = QueryIntent(
            original_query="Find the best sushi restaurants in Tokyo",
            complexity=QueryComplexity.SIMPLE,
            domains=["local_business", "search"],  # Correct order, but test still works
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Best sushi restaurants in Tokyo")

            answer, agent_id = await router._handle_simple_query_with_trace(intent, trace_capture)

        # Should route to local_business
        capability_router._find_candidate_agents.assert_called_with("local_business")

    @pytest.mark.asyncio
    async def test_generic_food_query(self, mock_router):
        """Test: "Where should I eat in Tokyo?" """
        router, capability_router = mock_router

        intent = QueryIntent(
            original_query="Where should I eat in Tokyo?",
            complexity=QueryComplexity.SIMPLE,
            domains=["search", "local_business"],  # LLM might add both
            requires_synthesis=False,
            metadata={}
        )

        trace_capture = TraceCapture()

        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Great places to eat in Tokyo")

            answer, agent_id = await router._handle_simple_query_with_trace(intent, trace_capture)

        # Should prioritize local_business over search
        capability_router._find_candidate_agents.assert_called_with("local_business")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
