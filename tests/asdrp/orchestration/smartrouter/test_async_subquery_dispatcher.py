"""
Tests for AsyncSubqueryDispatcher

Tests asynchronous subquery dispatch and execution.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from asdrp.orchestration.smartrouter.async_subquery_dispatcher import AsyncSubqueryDispatcher
from asdrp.orchestration.smartrouter.interfaces import (
    Subquery,
    AgentResponse,
    RoutingPattern,
)
from asdrp.orchestration.smartrouter.config_loader import ErrorHandlingConfig
from asdrp.orchestration.smartrouter.exceptions import DispatchException


class TestAsyncSubqueryDispatcher:
    """Test AsyncSubqueryDispatcher class."""

    @pytest.fixture
    def error_config(self):
        """Create error handling config."""
        return ErrorHandlingConfig(timeout=30.0, retries=2)

    @pytest.fixture
    def mock_factory(self):
        """Create mock agent factory."""
        return MagicMock()

    @pytest.fixture
    def dispatcher(self, mock_factory, error_config):
        """Create AsyncSubqueryDispatcher instance."""
        return AsyncSubqueryDispatcher(
            agent_factory=mock_factory,
            error_config=error_config
        )

    def test_init(self, mock_factory, error_config):
        """Test AsyncSubqueryDispatcher initialization."""
        dispatcher = AsyncSubqueryDispatcher(
            agent_factory=mock_factory,
            error_config=error_config
        )
        assert dispatcher.agent_factory == mock_factory
        assert dispatcher.error_config == error_config
        assert dispatcher.session_id is None

    def test_init_with_session(self, mock_factory, error_config):
        """Test initialization with session ID."""
        dispatcher = AsyncSubqueryDispatcher(
            agent_factory=mock_factory,
            error_config=error_config,
            session_id="test_session"
        )
        assert dispatcher.session_id == "test_session"

    @pytest.mark.asyncio
    async def test_dispatch_success(self, dispatcher, mock_factory):
        """Test successful dispatch."""
        subquery = Subquery(
            id="sq1",
            text="Test query",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        # Mock agent and runner
        mock_agent = MagicMock()
        mock_factory.get_agent = AsyncMock(return_value=mock_agent)
        
        mock_result = MagicMock()
        mock_result.final_output = "Test response"
        
        with patch('asdrp.orchestration.smartrouter.async_subquery_dispatcher.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            response = await dispatcher.dispatch(subquery, "geo")
            
            assert isinstance(response, AgentResponse)
            assert response.subquery_id == "sq1"
            assert response.agent_id == "geo"
            assert response.content == "Test response"
            assert response.success is True

    @pytest.mark.asyncio
    async def test_dispatch_with_timeout(self, dispatcher, mock_factory):
        """Test dispatch with timeout."""
        subquery = Subquery(
            id="sq1",
            text="Test query",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        mock_agent = MagicMock()
        mock_factory.get_agent = AsyncMock(return_value=mock_agent)
        
        with patch('asdrp.orchestration.smartrouter.async_subquery_dispatcher.Runner') as mock_runner:
            mock_runner.run = AsyncMock(side_effect=asyncio.TimeoutError())
            
            response = await dispatcher.dispatch(subquery, "geo", timeout=5.0)
            
            assert response.success is False
            assert "timeout" in response.content.lower() or "timeout" in str(response.metadata)

    @pytest.mark.asyncio
    async def test_dispatch_all(self, dispatcher, mock_factory):
        """Test dispatch_all for multiple subqueries."""
        subqueries = [
            (
                Subquery(
                    id=f"sq{i}",
                    text=f"Query {i}",
                    capability_required="geocoding",
                    dependencies=[],
                    routing_pattern=RoutingPattern.DELEGATION,
                    metadata={}
                ),
                "geo"
            )
            for i in range(3)
        ]
        
        mock_agent = MagicMock()
        mock_factory.get_agent = AsyncMock(return_value=mock_agent)
        
        mock_result = MagicMock()
        mock_result.final_output = "Response"
        
        with patch('asdrp.orchestration.smartrouter.async_subquery_dispatcher.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            responses = await dispatcher.dispatch_all(subqueries)
            
            assert len(responses) == 3
            assert all(isinstance(r, AgentResponse) for r in responses)
            assert all(r.success for r in responses)

    @pytest.mark.asyncio
    async def test_dispatch_all_empty(self, dispatcher):
        """Test dispatch_all with empty list."""
        responses = await dispatcher.dispatch_all([])
        assert responses == []

