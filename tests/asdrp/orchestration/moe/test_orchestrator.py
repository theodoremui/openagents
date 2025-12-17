"""Tests for MoE Orchestrator."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from asdrp.orchestration.moe.orchestrator import (
    MoEOrchestrator,
    MoEResult,
    MoETrace,
)
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.result_mixer import MixedResult


class TestMoEOrchestrator:
    """Test MoE orchestrator core functionality."""

    @pytest.fixture
    def mock_selector(self):
        """Mock expert selector."""
        selector = Mock()
        selector.select = AsyncMock(return_value=["one", "geo", "yelp"])
        return selector

    @pytest.fixture
    def mock_executor(self):
        """Mock expert executor."""
        executor = Mock()
        executor.execute_parallel = AsyncMock(return_value=[
            ExpertResult(
                expert_id="one",
                output="Web search result",
                success=True,
                latency_ms=500.0
            ),
            ExpertResult(
                expert_id="geo",
                output="Location result",
                success=True,
                latency_ms=300.0
            ),
            ExpertResult(
                expert_id="yelp",
                output="Restaurant result",
                success=True,
                latency_ms=400.0
            ),
        ])
        return executor

    @pytest.fixture
    def mock_mixer(self):
        """Mock result mixer."""
        mixer = Mock()
        mixer.mix = AsyncMock(return_value=MixedResult(
            content="Synthesized response from experts",
            weights={"one": 0.4, "geo": 0.3, "yelp": 0.3},
            quality_score=0.85
        ))
        return mixer

    @pytest.fixture
    def mock_cache(self):
        """Mock cache."""
        cache = Mock()
        cache.get = AsyncMock(return_value=None)
        cache.store = AsyncMock()
        return cache

    @pytest.fixture
    def orchestrator(
        self,
        mock_agent_factory,
        mock_selector,
        mock_executor,
        mock_mixer,
        mock_moe_config,
        mock_cache
    ):
        """Create test orchestrator."""
        return MoEOrchestrator(
            agent_factory=mock_agent_factory,
            expert_selector=mock_selector,
            expert_executor=mock_executor,
            result_mixer=mock_mixer,
            config=mock_moe_config,
            cache=mock_cache
        )

    @pytest.mark.asyncio
    async def test_route_query_success(
        self,
        orchestrator,
        sample_query,
        mock_selector,
        mock_executor,
        mock_mixer
    ):
        """Test successful query routing."""
        result = await orchestrator.route_query(sample_query)

        # Verify result structure
        assert isinstance(result, MoEResult)
        assert result.response == "Synthesized response from experts"
        assert len(result.experts_used) == 3
        assert "one" in result.experts_used
        assert "geo" in result.experts_used
        assert "yelp" in result.experts_used

        # Verify trace
        assert isinstance(result.trace, MoETrace)
        assert result.trace.cache_hit is False
        assert result.trace.fallback is False
        assert result.trace.latency_ms > 0

        # Verify components were called
        mock_selector.select.assert_called_once()
        mock_executor.execute_parallel.assert_called_once()
        mock_mixer.mix.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_query_with_session(
        self,
        orchestrator,
        sample_query,
        mock_agent_factory
    ):
        """Test query routing with session ID."""
        session_id = "test_session_123"

        result = await orchestrator.route_query(
            query=sample_query,
            session_id=session_id
        )

        # Verify session was passed to factory
        calls = mock_agent_factory.get_agent_with_session.call_args_list
        for call in calls:
            args, kwargs = call
            # Session ID should be passed as second argument
            if len(args) > 1:
                assert args[1] == session_id

        assert isinstance(result, MoEResult)

    @pytest.mark.asyncio
    async def test_route_query_with_context(
        self,
        orchestrator,
        sample_query,
        sample_context,
        mock_executor
    ):
        """Test query routing with context."""
        result = await orchestrator.route_query(
            query=sample_query,
            context=sample_context
        )

        # Verify context was passed to executor
        mock_executor.execute_parallel.assert_called_once()
        call_args = mock_executor.execute_parallel.call_args
        # Context is passed as third positional arg or named arg
        assert call_args[0][2] == sample_context or call_args[1].get("context") == sample_context

        assert isinstance(result, MoEResult)

    @pytest.mark.asyncio
    async def test_route_query_cache_hit(
        self,
        orchestrator,
        sample_query,
        mock_cache,
        mock_selector
    ):
        """Test query with cache hit."""
        # Setup cache to return cached result
        cached_result = {
            "response": "Cached response",
            "experts_used": ["one"]
        }
        mock_cache.get = AsyncMock(return_value=cached_result)

        result = await orchestrator.route_query(sample_query)

        # Verify cache was checked
        mock_cache.get.assert_called_once_with(sample_query)

        # Verify result from cache
        assert result.response == "Cached response"
        assert result.trace.cache_hit is True

        # Verify selector/executor were NOT called
        mock_selector.select.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_query_stores_in_cache(
        self,
        orchestrator,
        sample_query,
        mock_cache
    ):
        """Test that successful results are stored in cache."""
        result = await orchestrator.route_query(sample_query)

        # Verify result was stored in cache
        mock_cache.store.assert_called_once()
        call_args = mock_cache.store.call_args
        assert call_args[0][0] == sample_query  # First arg is query
        assert isinstance(call_args[0][1], MoEResult)  # Second arg is result

    @pytest.mark.asyncio
    async def test_route_query_fallback_on_error(
        self,
        orchestrator,
        sample_query,
        mock_selector
    ):
        """Test fallback to default agent on error."""
        # Make selector fail
        mock_selector.select = AsyncMock(
            side_effect=Exception("Selection failed")
        )

        # Mock Runner.run for fallback
        with patch("agents.Runner.run") as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Fallback response"
            mock_run.return_value = mock_result

            result = await orchestrator.route_query(sample_query)

            # Verify fallback was used
            assert isinstance(result, MoEResult)
            assert result.trace.fallback is True
            assert result.trace.error is not None
            assert "one" in result.experts_used  # Fallback agent

    @pytest.mark.asyncio
    async def test_route_query_fallback_when_selector_returns_none(
        self,
        orchestrator,
        sample_query,
        mock_selector,
    ):
        """Selectors must return list[str]. If they return None, MoE should fail open to fallback."""
        mock_selector.select = AsyncMock(return_value=None)

        with patch("agents.Runner.run") as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Fallback response"
            mock_run.return_value = mock_result

            result = await orchestrator.route_query(sample_query)
            assert isinstance(result, MoEResult)
            assert result.trace.fallback is True
            assert "one" in result.experts_used

    @pytest.mark.asyncio
    async def test_route_query_no_agents_loaded(
        self,
        orchestrator,
        sample_query,
        mock_agent_factory
    ):
        """Test fallback when no agents can be loaded."""
        # Make all agent loads fail
        # IMPORTANT: Override get_agent_with_persistent_session (the method actually called by orchestrator)
        mock_agent_factory.get_agent_with_persistent_session = AsyncMock(
            side_effect=Exception("Agent load failed")
        )

        result = await orchestrator.route_query(sample_query)

        # Verify fallback was used
        assert isinstance(result, MoEResult)
        assert result.trace.fallback is True

    @pytest.mark.asyncio
    async def test_create_default_factory_method(
        self,
        mock_agent_factory,
        mock_moe_config
    ):
        """Test create_default factory method."""
        orchestrator = MoEOrchestrator.create_default(
            mock_agent_factory,
            mock_moe_config
        )

        assert isinstance(orchestrator, MoEOrchestrator)
        assert orchestrator._factory == mock_agent_factory
        assert orchestrator._config == mock_moe_config

    def test_generate_request_id(self, orchestrator):
        """Test request ID generation."""
        request_id = orchestrator._generate_request_id()

        assert request_id.startswith("moe-")
        assert len(request_id) == 16  # "moe-" + 12 hex chars

        # Verify uniqueness
        request_id2 = orchestrator._generate_request_id()
        assert request_id != request_id2
