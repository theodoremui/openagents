"""
Tests for FastAPI endpoints in server/main.py

Comprehensive test suite for all API endpoints following best practices.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Set test environment
os.environ["TESTING"] = "true"
os.environ["AUTH_ENABLED"] = "false"

from server.main import app, get_service
from server.models import (
    AgentListItem,
    AgentDetail,
    SimulationRequest,
    SimulationResponse,
    HealthResponse,
    ConfigResponse,
    ErrorResponse,
    StreamChunk,
)
from asdrp.agents.protocol import AgentException


class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Multi-Agent Orchestration API"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
        assert "docs" in data
        assert "health" in data


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked service."""
        return TestClient(app)

    def test_health_check_healthy(self, client, mock_service):
        """Test health check when service is healthy."""
        mock_service.list_agents.return_value = [
            AgentListItem(id="geo", name="geo", display_name="GeoAgent", enabled=True)
        ]
        
        with patch('server.main.get_service', return_value=mock_service):
            with patch.dict(os.environ, {"ORCHESTRATOR": "default"}):
                response = client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["agents_loaded"] == 1
                assert data["orchestrator"] == "default"

    def test_health_check_unhealthy(self, client, mock_service):
        """Test health check when service fails."""
        mock_service.list_agents.side_effect = Exception("Service error")
        
        with patch('server.main.get_service', return_value=mock_service):
            with patch.dict(os.environ, {"ORCHESTRATOR": "smartrouter"}):
                response = client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["agents_loaded"] == 0
                assert data["orchestrator"] == "smartrouter"


class TestListAgentsEndpoint:
    """Test list agents endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_list_agents_success(self, client, mock_service, auth_header):
        """Test listing agents successfully."""
        mock_service.list_agents.return_value = [
            AgentListItem(id="geo", name="geo", display_name="GeoAgent", enabled=True),
            AgentListItem(id="finance", name="finance", display_name="FinanceAgent", enabled=True),
        ]
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.get("/agents", headers=auth_header)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["id"] in ["finance", "geo"]  # Sorted by display_name

    def test_list_agents_empty(self, client, mock_service, auth_header):
        """Test listing agents when none exist."""
        mock_service.list_agents.return_value = []
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.get("/agents", headers=auth_header)
            
            assert response.status_code == 200
            assert response.json() == []


class TestGetAgentEndpoint:
    """Test get agent detail endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_agent_success(self, client, mock_service, auth_header):
        """Test getting agent detail successfully."""
        detail = AgentDetail(
            id="geo",
            name="geo",
            display_name="GeoAgent",
            description="Geocoding agent",
            module="asdrp.agents.single.geo_agent",
            function="create_geo_agent",
            model_name="gpt-4.1-mini",
            temperature=0.1,
            max_tokens=2000,
            tools=["geocode"],
            enabled=True,
        )
        mock_service.get_agent_detail = AsyncMock(return_value=detail)
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.get("/agents/geo", headers=auth_header)
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "geo"
            assert data["display_name"] == "GeoAgent"
            assert data["model_name"] == "gpt-4.1-mini"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client, mock_service, auth_header):
        """Test getting non-existent agent."""
        mock_service.get_agent_detail = AsyncMock(side_effect=AgentException("Agent not found", agent_name="unknown"))
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.get("/agents/unknown", headers=auth_header)
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestGetAgentToolsEndpoint:
    """Test get agent tools endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_agent_tools_success(self, client, mock_service, auth_header):
        """Test getting agent tools successfully."""
        with patch('server.main.get_service', return_value=mock_service):
            with patch('asdrp.agents.agent_factory.AgentFactory') as mock_factory_class:
                mock_factory = Mock()
                mock_factory.instance.return_value = mock_factory
                mock_factory_class.instance.return_value = mock_factory
                
                mock_agent = Mock()
                mock_agent.name = "GeoAgent"
                mock_agent.tools = [Mock(name="geocode"), Mock(name="reverse_geocode")]
                mock_factory.get_agent = AsyncMock(return_value=mock_agent)
                
                response = client.get("/agents/geo/tools", headers=auth_header)
                
                assert response.status_code == 200
                data = response.json()
                assert data["agent_id"] == "geo"
                assert data["tool_count"] == 2
                assert "geocode" in data["tool_names"]

    @pytest.mark.asyncio
    async def test_get_agent_tools_not_found(self, client, mock_service, auth_header):
        """Test getting tools for non-existent agent."""
        with patch('server.main.get_service', return_value=mock_service):
            with patch('asdrp.agents.agent_factory.AgentFactory') as mock_factory_class:
                mock_factory = Mock()
                mock_factory.instance.return_value = mock_factory
                mock_factory_class.instance.return_value = mock_factory
                mock_factory.get_agent = AsyncMock(side_effect=AgentException("Agent not found", agent_name="unknown"))
                
                response = client.get("/agents/unknown/tools", headers=auth_header)
                
                assert response.status_code == 404


class TestSimulateAgentEndpoint:
    """Test simulate agent endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_simulate_agent_success(self, client, mock_service, auth_header):
        """Test simulating agent successfully."""
        response_obj = SimulationResponse(
            response="[MOCK] Test response",
            trace=[],
            metadata={"mode": "mock", "agent_id": "geo"}
        )
        mock_service.simulate_agent = AsyncMock(return_value=response_obj)
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.post(
                "/agents/geo/simulate",
                headers=auth_header,
                json={"input": "Test input"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["mode"] == "mock"
            assert "[MOCK]" in data["response"]

    @pytest.mark.asyncio
    async def test_simulate_agent_invalid_request(self, client, mock_service, auth_header):
        """Test simulating agent with invalid request."""
        with patch('server.main.get_service', return_value=mock_service):
            response = client.post(
                "/agents/geo/simulate",
                headers=auth_header,
                json={"input": ""}  # Empty input should fail validation
            )
            
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_simulate_agent_error(self, client, mock_service, auth_header):
        """Test simulating agent with error."""
        mock_service.simulate_agent = AsyncMock(side_effect=AgentException("Agent error", agent_name="geo"))
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.post(
                "/agents/geo/simulate",
                headers=auth_header,
                json={"input": "Test"}
            )
            
            assert response.status_code == 400


class TestChatAgentEndpoint:
    """Test chat agent endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_chat_agent_success(self, client, mock_service, auth_header):
        """Test chatting with agent successfully."""
        response_obj = SimulationResponse(
            response="Real agent response",
            trace=[],
            metadata={"mode": "real", "agent_id": "geo"}
        )
        mock_service.chat_agent = AsyncMock(return_value=response_obj)
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.post(
                "/agents/geo/chat",
                headers=auth_header,
                json={"input": "Test input"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["mode"] == "real"
            assert "Real agent response" in data["response"]

    @pytest.mark.asyncio
    async def test_chat_agent_error(self, client, mock_service, auth_header):
        """Test chatting with agent with error."""
        mock_service.chat_agent = AsyncMock(side_effect=AgentException("Execution failed", agent_name="geo"))
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.post(
                "/agents/geo/chat",
                headers=auth_header,
                json={"input": "Test"}
            )
            
            assert response.status_code == 400


class TestChatAgentStreamEndpoint:
    """Test chat agent streaming endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_chat_agent_stream_success(self, client, mock_service, auth_header):
        """Test streaming agent response successfully."""
        async def mock_stream():
            yield StreamChunk(type="metadata", metadata={"agent_id": "geo"})
            yield StreamChunk(type="token", content="Hello")
            yield StreamChunk(type="token", content=" World")
            yield StreamChunk(type="done", metadata={})
        
        mock_service.chat_agent_streaming = mock_stream
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.post(
                "/agents/geo/chat/stream",
                headers=auth_header,
                json={"input": "Test"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            # Read stream
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
                if len(content) > 1000:  # Limit reading
                    break
            
            assert b"data:" in content

    @pytest.mark.asyncio
    async def test_chat_agent_stream_error(self, client, mock_service, auth_header):
        """Test streaming agent response with error."""
        async def mock_stream():
            yield StreamChunk(type="error", content="Stream error", metadata={"agent_id": "geo"})
        
        mock_service.chat_agent_streaming = mock_stream
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.post(
                "/agents/geo/chat/stream",
                headers=auth_header,
                json={"input": "Test"}
            )
            
            assert response.status_code == 200
            content = b"".join(response.iter_bytes(chunk_size=1024))
            assert b"error" in content.lower()


class TestGetGraphEndpoint:
    """Test get graph endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_get_graph_success(self, client, mock_service, auth_header):
        """Test getting agent graph successfully."""
        from server.models import AgentGraph, GraphNode, GraphEdge
        
        graph = AgentGraph(
            nodes=[GraphNode(id="geo", data={"label": "GeoAgent"})],
            edges=[]
        )
        mock_service.get_agent_graph.return_value = graph
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.get("/graph", headers=auth_header)
            
            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert "edges" in data
            assert len(data["nodes"]) == 1


class TestGetConfigEndpoint:
    """Test get config endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_get_config_success(self, client, mock_service, auth_header):
        """Test getting configuration successfully."""
        from pathlib import Path
        
        with patch('server.main.get_service', return_value=mock_service):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = "agents:\n  geo:\n    enabled: true"
                    mock_open.return_value.__enter__.return_value.__exit__ = Mock(return_value=None)
                    
                    mock_stat = Mock()
                    mock_stat.st_mtime = 1234567890.0
                    
                    with patch('pathlib.Path.stat', return_value=mock_stat):
                        mock_service.list_agents.return_value = [
                            AgentListItem(id="geo", name="geo", display_name="GeoAgent", enabled=True)
                        ]
                        
                        response = client.get("/config/agents", headers=auth_header)
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "content" in data
                        assert data["agents_count"] == 1

    def test_get_config_not_found(self, client, mock_service, auth_header):
        """Test getting configuration when file not found."""
        with patch('server.main.get_service', return_value=mock_service):
            with patch('pathlib.Path.exists', return_value=False):
                response = client.get("/config/agents", headers=auth_header)
                
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()


class TestUpdateConfigEndpoint:
    """Test update config endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_update_config_validate_only(self, client, mock_service, auth_header):
        """Test validating config without saving."""
        mock_service.validate_config.return_value = (True, None)
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.put(
                "/config/agents",
                headers=auth_header,
                json={"content": "agents:\n  geo:\n    enabled: true", "validate_only": True}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True

    def test_update_config_invalid(self, client, mock_service, auth_header):
        """Test updating config with invalid YAML."""
        mock_service.validate_config.return_value = (False, "YAML parse error")
        
        with patch('server.main.get_service', return_value=mock_service):
            response = client.put(
                "/config/agents",
                headers=auth_header,
                json={"content": "invalid: yaml: [", "validate_only": False}
            )
            
            assert response.status_code == 400
            assert "Invalid YAML" in response.json()["detail"]

    def test_update_config_success(self, client, mock_service, auth_header):
        """Test updating config successfully."""
        mock_service.validate_config.return_value = (True, None)
        mock_service.list_agents.return_value = [
            AgentListItem(id="geo", name="geo", display_name="GeoAgent", enabled=True)
        ]
        mock_service.reload_config = Mock()
        
        with patch('server.main.get_service', return_value=mock_service):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.with_suffix') as mock_suffix:
                    mock_suffix.return_value = Path("/tmp/config.yaml.bak")
                    with patch('shutil.copy') as mock_copy:
                        with patch('builtins.open', create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.write = Mock()
                            mock_open.return_value.__enter__.return_value.__exit__ = Mock(return_value=None)
                            
                            response = client.put(
                                "/config/agents",
                                headers=auth_header,
                                json={"content": "agents:\n  geo:\n    enabled: true", "validate_only": False}
                            )
                            
                            assert response.status_code == 200
                            data = response.json()
                            assert data["success"] is True
                            mock_service.reload_config.assert_called_once()


class TestExceptionHandler:
    """Test exception handlers."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_agent_exception_handler(self, client, mock_service, auth_header):
        """Test AgentException handler."""
        from server.main import agent_exception_handler
        from fastapi import Request
        
        exc = AgentException("Test error", agent_name="geo")
        request = Request({"type": "http"})
        
        response = await agent_exception_handler(request, exc)
        
        assert response.status_code == 400
        data = response.body
        assert b"Test error" in data


class TestGetService:
    """Test get_service dependency."""

    def test_get_service_available(self):
        """Test get_service when service is available."""
        mock_service = Mock()
        with patch('server.main._agent_service', mock_service):
            service = get_service()
            assert service == mock_service

    def test_get_service_unavailable(self):
        """Test get_service when service is unavailable."""
        with patch('server.main._agent_service', None):
            with pytest.raises(HTTPException) as exc_info:
                get_service()
            
            assert exc_info.value.status_code == 503
            assert "not initialized" in exc_info.value.detail.lower()













