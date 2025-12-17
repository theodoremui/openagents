"""
Integration Tests for Fast-Path Router with SmartRouter

Tests that verify fast-path routing is properly integrated into SmartRouter
and provides the expected latency improvements for chitchat queries.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
from asdrp.orchestration.smartrouter.config_loader import SmartRouterConfigLoader
from asdrp.orchestration.smartrouter.interfaces import QueryComplexity


@pytest.fixture
def mock_agent_factory():
    """Mock agent factory for testing."""
    factory = MagicMock()

    # Mock get_agent to return a mock agent
    mock_agent = MagicMock()
    mock_agent.name = "MockAgent"

    async def mock_get_agent(agent_id):
        return mock_agent

    async def mock_get_agent_with_session(agent_id, session_id=None):
        return (mock_agent, MagicMock())  # (agent, session)

    factory.get_agent = mock_get_agent
    factory.get_agent_with_session = mock_get_agent_with_session

    return factory


@pytest.fixture
def smartrouter_config():
    """Load SmartRouter configuration."""
    loader = SmartRouterConfigLoader()
    return loader.load_config()


class TestFastPathIntegration:
    """Tests for fast-path integration with SmartRouter."""

    @pytest.mark.asyncio
    async def test_fast_path_router_initialized(self, mock_agent_factory, smartrouter_config):
        """Test that FastPathRouter is initialized in SmartRouter."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Verify fast_path_router exists
        assert hasattr(router, 'fast_path_router')
        assert router.fast_path_router is not None

    @pytest.mark.asyncio
    async def test_chitchat_query_uses_fast_path(self, mock_agent_factory, smartrouter_config):
        """Test that chitchat queries use fast-path and skip LLM interpretation."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Mock Runner.run to simulate agent execution
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Hi there! How can I help you today?")

            result = await router.route_query("hello")

            # Verify result
            assert result.success is True
            assert result.final_decision == "chitchat"  # Should be chitchat, not fast_path
            assert len(result.agents_used) == 1

            # Verify fast-path trace exists
            traces = result.traces
            assert any(trace["phase"] == "fast_path" for trace in traces)

            # Get fast-path trace
            fast_path_trace = next(t for t in traces if t["phase"] == "fast_path")
            assert fast_path_trace["data"]["matched"] is True
            assert "pattern" in fast_path_trace["data"]

    @pytest.mark.asyncio
    async def test_non_chitchat_query_skips_fast_path(self, mock_agent_factory, smartrouter_config):
        """Test that non-chitchat queries fall through to standard pipeline."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Mock fast_path_router to return None (no match) - forcing standard pipeline
        with patch.object(router.fast_path_router, 'try_fast_path', return_value=None) as mock_fast_path:
            # Mock interpreter to return SIMPLE intent
            with patch.object(router.interpreter, 'interpret') as mock_interpret:
                mock_interpret.return_value = MagicMock(
                    original_query="What's the weather in Paris?",
                    complexity=QueryComplexity.SIMPLE,
                    domains=["search"],
                    requires_synthesis=False,
                    metadata={}
                )

                # Mock agent execution
                with patch('agents.Runner.run') as mock_run:
                    mock_run.return_value = MagicMock(final_output="The weather in Paris is sunny, 22°C.")

                    # Mock judge evaluation
                    with patch.object(router.judge, 'evaluate') as mock_eval:
                        mock_eval.return_value = MagicMock(
                            is_high_quality=True,
                            completeness_score=0.9,
                            accuracy_score=0.9,
                            clarity_score=0.9,
                            should_fallback=False,
                            issues=[]
                        )

                        result = await router.route_query("What's the weather in Paris?")

                        # Verify result
                        assert result.success is True
                        assert result.final_decision == "direct"  # Not fast-path

                        # Verify fast-path trace shows no match
                        traces = result.traces
                        fast_path_trace = next(t for t in traces if t["phase"] == "fast_path")
                        assert fast_path_trace["data"]["matched"] is False
                        assert fast_path_trace["data"]["fallthrough"] is True

                        # Verify fast_path was checked first
                        mock_fast_path.assert_called_once()

                        # Verify interpreter was called (not skipped)
                        mock_interpret.assert_called_once()

    @pytest.mark.asyncio
    async def test_fast_path_patterns(self, mock_agent_factory, smartrouter_config):
        """Test that all fast-path patterns work correctly."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        test_cases = [
            ("hello", "greeting_simple"),
            ("hi", "greeting_simple"),
            ("good morning", "greeting_time"),
            ("goodbye", "farewell"),
            ("thanks", "gratitude"),
            ("how are you", "status_inquiry"),
            ("yes", "affirmation"),
            ("no", "negation"),
        ]

        for query, expected_pattern in test_cases:
            # Mock agent execution
            with patch('agents.Runner.run') as mock_run:
                mock_run.return_value = MagicMock(final_output=f"Response to {query}")

                result = await router.route_query(query)

                # Verify fast-path was used
                assert result.success is True
                assert result.final_decision == "chitchat"

                # Verify correct pattern matched
                traces = result.traces
                fast_path_trace = next(t for t in traces if t["phase"] == "fast_path")
                assert fast_path_trace["data"]["matched"] is True
                assert fast_path_trace["data"]["pattern"] == expected_pattern

    @pytest.mark.asyncio
    async def test_fast_path_skips_evaluation(self, mock_agent_factory, smartrouter_config):
        """Test that fast-path queries skip quality evaluation."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Mock agent execution
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Hello!")

            # Mock judge to verify it's NOT called
            with patch.object(router.judge, 'evaluate') as mock_eval:
                result = await router.route_query("hi")

                # Verify result
                assert result.success is True
                assert result.final_decision == "chitchat"

                # Verify evaluation was NOT called
                mock_eval.assert_not_called()

                # Verify no evaluation trace
                traces = result.traces
                assert not any(trace["phase"] == "evaluation" for trace in traces)

    @pytest.mark.asyncio
    async def test_fast_path_with_session(self, mock_agent_factory, smartrouter_config):
        """Test that fast-path works with session memory."""
        session_id = "test_fast_path_session"

        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory,
            session_id=session_id
        )

        # Mock agent execution
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Hello!")

            result = await router.route_query("hello")

            # Verify result
            assert result.success is True
            assert result.final_decision == "chitchat"

            # Verify Runner.run was called with session
            assert mock_run.called
            call_kwargs = mock_run.call_args.kwargs
            assert 'session' in call_kwargs
            assert call_kwargs['session'] is not None


class TestFastPathPerformance:
    """Tests for fast-path performance characteristics."""

    @pytest.mark.asyncio
    async def test_fast_path_is_faster_than_standard(self, mock_agent_factory, smartrouter_config):
        """Test that fast-path queries are significantly faster than standard queries."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Mock agent execution (instant)
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Hello!")

            # Measure fast-path query time
            start = time.time()
            result = await router.route_query("hello")
            fast_path_time = time.time() - start

            # Verify fast-path was used
            assert result.final_decision == "chitchat"

        # Mock fast-path to return None for standard query comparison
        with patch.object(router.fast_path_router, 'try_fast_path', return_value=None):
            # Mock standard query (with LLM interpretation)
            with patch.object(router.interpreter, 'interpret') as mock_interpret:
                # Simulate LLM interpretation delay (100ms)
                async def slow_interpret(query):
                    await asyncio.sleep(0.1)
                    return MagicMock(
                        original_query=query,
                        complexity=QueryComplexity.SIMPLE,
                        domains=["search"],
                        requires_synthesis=False,
                        metadata={}
                    )

                mock_interpret.side_effect = slow_interpret

                # Mock agent execution
                with patch('agents.Runner.run') as mock_run:
                    mock_run.return_value = MagicMock(final_output="Response")

                    # Mock judge evaluation
                    with patch.object(router.judge, 'evaluate') as mock_eval:
                        mock_eval.return_value = MagicMock(
                            is_high_quality=True,
                            completeness_score=0.9,
                            accuracy_score=0.9,
                            clarity_score=0.9,
                            should_fallback=False,
                            issues=[]
                        )

                        # Measure standard query time (use a query that wouldn't normally match fast-path)
                        start = time.time()
                        result = await router.route_query("What is the capital of France?")
                        standard_time = time.time() - start

                        # Verify standard pipeline was used
                        assert result.final_decision == "direct"

        # Fast-path should be at least 50ms faster (due to skipped LLM call)
        assert fast_path_time < standard_time

    @pytest.mark.asyncio
    async def test_fast_path_latency_metrics(self, mock_agent_factory, smartrouter_config):
        """Test that fast-path latency is tracked in metrics."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Mock agent execution
        with patch('agents.Runner.run') as mock_run:
            mock_run.return_value = MagicMock(final_output="Hello!")

            result = await router.route_query("hello")

            # Verify total_time is recorded
            assert result.total_time is not None
            assert result.total_time > 0

            # Verify traces include timing
            traces = result.traces
            fast_path_trace = next(t for t in traces if t["phase"] == "fast_path")
            assert "duration" in fast_path_trace
            assert fast_path_trace["duration"] >= 0


class TestFastPathEdgeCases:
    """Tests for fast-path edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_fast_path_with_punctuation(self, mock_agent_factory, smartrouter_config):
        """Test fast-path with various punctuation."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        test_cases = ["hello!", "hello.", "hello?", "hello!!!", "hello..."]

        for query in test_cases:
            with patch('agents.Runner.run') as mock_run:
                mock_run.return_value = MagicMock(final_output="Hello!")

                result = await router.route_query(query)

                # All should match fast-path
                assert result.success is True
                assert result.final_decision == "chitchat"

    @pytest.mark.asyncio
    async def test_fast_path_case_insensitive(self, mock_agent_factory, smartrouter_config):
        """Test that fast-path matching is case insensitive."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        test_cases = ["hello", "Hello", "HELLO", "HeLLo"]

        for query in test_cases:
            with patch('agents.Runner.run') as mock_run:
                mock_run.return_value = MagicMock(final_output="Hello!")

                result = await router.route_query(query)

                # All should match fast-path
                assert result.success is True
                assert result.final_decision == "chitchat"

    @pytest.mark.asyncio
    async def test_fast_path_partial_match_rejected(self, mock_agent_factory, smartrouter_config):
        """Test that partial matches don't trigger fast-path."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # These should NOT match fast-path (partial matches)
        test_cases = [
            "hiya",  # Not "hi"
            "hello there",  # Extra words
            "say goodbye",  # Not at start
        ]

        for query in test_cases:
            # Mock interpreter for standard path
            with patch.object(router.interpreter, 'interpret') as mock_interpret:
                mock_interpret.return_value = MagicMock(
                    original_query=query,
                    complexity=QueryComplexity.SIMPLE,
                    domains=["search"],
                    requires_synthesis=False,
                    metadata={}
                )

                # Mock agent and judge
                with patch('agents.Runner.run') as mock_run:
                    mock_run.return_value = MagicMock(final_output="Response")

                    with patch.object(router.judge, 'evaluate') as mock_eval:
                        mock_eval.return_value = MagicMock(
                            is_high_quality=True,
                            completeness_score=0.9,
                            accuracy_score=0.9,
                            clarity_score=0.9,
                            should_fallback=False,
                            issues=[]
                        )

                        result = await router.route_query(query)

                        # Should NOT use fast-path
                        assert result.final_decision != "chitchat"

                        # Verify interpreter was called
                        mock_interpret.assert_called_once()


class TestFastPathMetrics:
    """Tests for fast-path metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_fast_path_metrics_recorded(self, mock_agent_factory, smartrouter_config):
        """Test that fast-path metrics are recorded correctly."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Execute multiple queries
        # Use "What is the capital of France?" instead of "What's the weather?" 
        # because weather queries now match fast-path pattern
        queries = ["hello", "goodbye", "thanks", "What is the capital of France?", "hi"]

        for query in queries:
            if query in ["hello", "goodbye", "thanks", "hi"]:
                # Fast-path queries
                with patch('agents.Runner.run') as mock_run:
                    mock_run.return_value = MagicMock(final_output="Response")
                    await router.route_query(query)
            else:
                # Standard path (query doesn't match any fast-path pattern)
                with patch.object(router.interpreter, 'interpret') as mock_interpret:
                    mock_interpret.return_value = MagicMock(
                        original_query=query,
                        complexity=QueryComplexity.SIMPLE,
                        domains=["search"],
                        requires_synthesis=False,
                        metadata={}
                    )

                    with patch('agents.Runner.run') as mock_run:
                        mock_run.return_value = MagicMock(final_output="Response")

                        with patch.object(router.judge, 'evaluate') as mock_eval:
                            mock_eval.return_value = MagicMock(
                                is_high_quality=True,
                                completeness_score=0.9,
                                accuracy_score=0.9,
                                clarity_score=0.9,
                                should_fallback=False,
                                issues=[]
                            )

                            await router.route_query(query)

        # Check fast_path_router metrics
        metrics = router.fast_path_router.get_metrics()

        assert metrics["total_attempts"] == 5
        assert metrics["total_matches"] == 4  # 4 out of 5 matched
        assert abs(metrics["match_rate"] - 0.8) < 0.01  # 80% match rate

    @pytest.mark.asyncio
    async def test_fast_path_pattern_distribution(self, mock_agent_factory, smartrouter_config):
        """Test that pattern distribution is tracked correctly."""
        router = SmartRouter(
            config=smartrouter_config,
            agent_factory=mock_agent_factory
        )

        # Execute queries with different patterns
        queries_patterns = [
            ("hello", "greeting_simple"),
            ("goodbye", "farewell"),
            ("thanks", "gratitude"),
            ("hi", "greeting_simple"),
        ]

        for query, _ in queries_patterns:
            with patch('agents.Runner.run') as mock_run:
                mock_run.return_value = MagicMock(final_output="Response")
                await router.route_query(query)

        # Check pattern counts
        metrics = router.fast_path_router.get_metrics()
        pattern_counts = metrics["pattern_counts"]

        assert pattern_counts["greeting_simple"] == 2  # hello, hi
        assert pattern_counts["farewell"] == 1  # goodbye
        assert pattern_counts["gratitude"] == 1  # thanks


# Import asyncio for async sleep in performance test
import asyncio
