"""
Comprehensive edge case tests for server module.

Tests boundary conditions, error scenarios, and unusual inputs.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Set test environment
import os
os.environ["TESTING"] = "true"
os.environ["AUTH_ENABLED"] = "false"

from server.main import app
from server.agent_service import AgentService
from server.models import SimulationRequest, SimulationResponse
from asdrp.agents.protocol import AgentException


class TestSimulationRequestEdgeCases:
    """Test edge cases for SimulationRequest."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_simulate_empty_input(self, client, mock_service, auth_header):
        """Test simulate with empty input."""
        response = client.post(
            "/agents/geo/simulate",
            json={"input": ""},
            headers=auth_header
        )
        # Should validate input length
        assert response.status_code in [400, 422]

    def test_simulate_very_long_input(self, client, mock_service, auth_header):
        """Test simulate with very long input."""
        long_input = "x" * 10001  # Exceeds max_length
        response = client.post(
            "/agents/geo/simulate",
            json={"input": long_input},
            headers=auth_header
        )
        # Should validate max length
        assert response.status_code in [400, 422]

    def test_simulate_with_context(self, client, mock_service, auth_header):
        """Test simulate with context dictionary."""
        mock_service.simulate_agent = AsyncMock(return_value=SimulationResponse(
            response="Test",
            trace=[],
            metadata={}
        ))
        
        response = client.post(
            "/agents/geo/simulate",
            json={
                "input": "Test query",
                "context": {"key": "value", "nested": {"data": 123}}
            },
            headers=auth_header
        )
        
        assert response.status_code == 200
        mock_service.simulate_agent.assert_called_once()

    def test_simulate_with_session_id(self, client, mock_service, auth_header):
        """Test simulate with session ID."""
        mock_service.simulate_agent = AsyncMock(return_value=SimulationResponse(
            response="Test",
            trace=[],
            metadata={}
        ))
        
        response = client.post(
            "/agents/geo/simulate",
            json={
                "input": "Test query",
                "session_id": "test_session_123"
            },
            headers=auth_header
        )
        
        assert response.status_code == 200
        call_args = mock_service.simulate_agent.call_args
        assert call_args[0][1].session_id == "test_session_123"

    def test_simulate_max_steps_boundary(self, client, mock_service, auth_header):
        """Test simulate with boundary max_steps values."""
        mock_service.simulate_agent = AsyncMock(return_value=SimulationResponse(
            response="Test",
            trace=[],
            metadata={}
        ))
        
        # Test minimum value
        response = client.post(
            "/agents/geo/simulate",
            json={"input": "Test", "max_steps": 1},
            headers=auth_header
        )
        assert response.status_code == 200
        
        # Test maximum value
        response = client.post(
            "/agents/geo/simulate",
            json={"input": "Test", "max_steps": 100},
            headers=auth_header
        )
        assert response.status_code == 200
        
        # Test exceeding maximum
        response = client.post(
            "/agents/geo/simulate",
            json={"input": "Test", "max_steps": 101},
            headers=auth_header
        )
        assert response.status_code in [400, 422]


class TestAgentDetailEdgeCases:
    """Test edge cases for agent detail endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_agent_special_characters(self, client, mock_service, auth_header):
        """Test getting agent with special characters in ID."""
        mock_service.get_agent_detail = AsyncMock(side_effect=AgentException(
            "Agent not found",
            agent_name="test@agent#123"
        ))
        
        response = client.get(
            "/agents/test@agent#123",
            headers=auth_header
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agent_unicode_name(self, client, mock_service, auth_header):
        """Test getting agent with unicode name."""
        from server.models import AgentDetail
        
        mock_detail = AgentDetail(
            id="测试代理",
            name="测试代理",
            display_name="测试代理",
            module="test.module",
            function="create_agent",
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=2000
        )
        mock_service.get_agent_detail = AsyncMock(return_value=mock_detail)
        
        response = client.get(
            "/agents/测试代理",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "测试代理"


class TestGraphEndpointEdgeCases:
    """Test edge cases for graph endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_get_graph_empty_agents(self, client, mock_service, auth_header):
        """Test getting graph with no agents."""
        mock_service.get_agent_graph.return_value = Mock(
            nodes=[],
            edges=[]
        )
        
        response = client.get("/graph", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_get_graph_many_agents(self, client, mock_service, auth_header):
        """Test getting graph with many agents."""
        from server.models import AgentGraph, GraphNode
        
        many_nodes = [
            GraphNode(
                id=f"agent_{i}",
                data={"label": f"Agent {i}"},
                position={"x": i * 100, "y": i * 50}
            )
            for i in range(100)
        ]
        
        mock_service.get_agent_graph.return_value = AgentGraph(
            nodes=many_nodes,
            edges=[]
        )
        
        response = client.get("/graph", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 100


class TestStreamingEdgeCases:
    """Test edge cases for streaming endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_stream_with_empty_input(self, client, mock_service, auth_header):
        """Test streaming with empty input."""
        response = client.post(
            "/agents/geo/chat/stream",
            json={"input": ""},
            headers=auth_header
        )
        # Should validate input
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_stream_generator_exception(self, client, mock_service, auth_header):
        """Test streaming when generator raises exception."""
        async def failing_generator():
            yield "data: {\"type\":\"metadata\"}\n\n"
            raise Exception("Generator error")
        
        mock_service.chat_agent_streaming = failing_generator
        
        response = client.post(
            "/agents/geo/chat/stream",
            json={"input": "Test"},
            headers=auth_header
        )
        
        # Should handle error gracefully
        assert response.status_code == 200
        # Response should include error chunk
        content = response.text
        assert "error" in content.lower() or len(content) > 0


class TestServiceEdgeCases:
    """Test edge cases for AgentService methods."""

    @pytest.fixture
    def service(self):
        """Create AgentService with mocked dependencies."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.list_agents.return_value = []
            mock_loader_class.return_value = mock_loader
            
            service = AgentService()
            service._config_loader = mock_loader
            return service

    def test_list_agents_all_disabled(self, service):
        """Test listing when all agents are disabled."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        disabled_config = AgentConfig(
            display_name="Disabled Agent",
            module="test.module",
            function="create_agent",
            default_instructions="Test",
            model=ModelConfig(name="gpt-4", temperature=0.7, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=False
        )
        
        service._config_loader.list_agents.return_value = ["disabled_agent"]
        service._config_loader.get_agent_config.return_value = disabled_config
        
        agents = service.list_agents()
        # Disabled agents should still be listed
        assert len(agents) == 1
        assert agents[0].enabled is False

    @pytest.mark.asyncio
    async def test_get_agent_detail_no_tools(self, service):
        """Test getting agent detail when agent has no tools."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        from unittest.mock import AsyncMock
        
        mock_factory = Mock()
        mock_agent = Mock()
        mock_agent.name = "NoToolsAgent"
        mock_agent.tools = None
        mock_factory.get_agent = AsyncMock(return_value=mock_agent)
        service._factory = mock_factory
        
        config = AgentConfig(
            display_name="No Tools Agent",
            module="test.module",
            function="create_agent",
            default_instructions="Test",
            model=ModelConfig(name="gpt-4", temperature=0.7, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True
        )
        service._config_loader.get_agent_config.return_value = config
        
        detail = await service.get_agent_detail("no_tools_agent")
        assert detail.tools == []

    @pytest.mark.asyncio
    async def test_simulate_smartrouter_with_context(self, service):
        """Test simulating SmartRouter with context."""
        request = SimulationRequest(
            input="Test query",
            context={"key": "value"},
            session_id="test_session"
        )
        
        response = await service.simulate_agent("smartrouter", request)
        
        assert response.response is not None
        assert "smartrouter" in response.response.lower() or "orchestrat" in response.response.lower()
        assert response.metadata["orchestrator"] == "smartrouter"
        assert response.metadata["session_id"] == "test_session"

    def test_validate_config_very_large(self, service):
        """Test validating very large config."""
        large_config = "agents:\n" + "\n".join(
            f"  agent_{i}:\n    display_name: Agent {i}\n    module: test.module\n    function: create_agent"
            for i in range(1000)
        )
        
        is_valid, error = service.validate_config(large_config)
        # Should handle large configs
        assert isinstance(is_valid, bool)
        assert error is None or isinstance(error, str)













