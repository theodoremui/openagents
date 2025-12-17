"""
Comprehensive tests for agent execution endpoints.

Tests the three distinct endpoint types:
1. /simulate - Mock responses (no API calls)
2. /chat - Real execution (complete response)
3. /chat/stream - Real execution (streaming response)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

# Mock the asdrp modules before importing server
import os
import sys
sys.path.insert(0, "/Users/pmui/dev/halo/openagents")

# Set TESTING environment variable to disable TrustedHostMiddleware
os.environ["TESTING"] = "true"
os.environ["AUTH_ENABLED"] = "false"  # Disable auth for tests

# Import real AgentException instead of mocking it as Exception
from asdrp.agents.protocol import AgentException, AgentProtocol

# Mock asdrp.agents modules
mock_agent_protocol = Mock()
mock_agent_protocol.AgentProtocol = AgentProtocol
mock_agent_protocol.AgentException = AgentException

sys.modules['asdrp'] = Mock()
sys.modules['asdrp.agents'] = Mock()
sys.modules['asdrp.agents.protocol'] = mock_agent_protocol
sys.modules['asdrp.agents.agent_factory'] = Mock()
sys.modules['asdrp.agents.config_loader'] = Mock()

from server.main import app
from server.models import SimulationRequest, SimulationResponse


class TestSimulateEndpoint:
    """Tests for POST /agents/{agent_id}/simulate - Mock responses."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked service."""
        # mock_service and auth_header are provided by conftest.py
        return TestClient(app)

    def test_simulate_returns_mock_response(self, client, mock_service, auth_header):
        """Test that /simulate returns mock response with mode='mock'."""
        # Arrange
        mock_service.simulate_agent = AsyncMock(return_value=SimulationResponse(
            response="[MOCK] Test response",
            trace=[],
            metadata={"mode": "mock", "agent_id": "geo"}
        ))

        # Act
        response = client.post(
            "/agents/geo/simulate",
            headers=auth_header,
            json={"input": "Test input"}
        )

        # Assert
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["mode"] == "mock"
        assert "[MOCK]" in data["response"]
        assert mock_service.simulate_agent.called

    def test_simulate_no_api_calls(self, client, mock_service, auth_header):
        """Test that /simulate makes no actual API calls."""
        # Arrange
        mock_service.simulate_agent = AsyncMock(return_value=SimulationResponse(
            response="[MOCK] Fast response",
            trace=[],
            metadata={"mode": "mock"}
        ))

        # Act
        response = client.post(
            "/agents/geo/simulate",
            headers=auth_header,
            json={"input": "Test"}
        )

        # Assert
        assert response.status_code == 200
        # Verify no Runner.run() calls (would be in chat_agent, not simulate_agent)
        assert mock_service.simulate_agent.called
        assert not hasattr(mock_service, 'chat_agent') or not mock_service.chat_agent.called

    @pytest.mark.skipif(
        os.getenv("AUTH_ENABLED", "false").lower() != "true",
        reason="Auth is disabled in test environment"
    )
    def test_simulate_requires_authentication(self, client, mock_service):
        """Test that /simulate requires API key when auth is enabled."""
        # Setup mock service with async method to avoid errors if auth passes
        mock_service.simulate_agent = AsyncMock(return_value=SimulationResponse(
            response="test", trace=[], metadata={}
        ))
        
        # Act - no auth header (auth should be enabled for this test)
        response = client.post(
            "/agents/geo/simulate",
            json={"input": "Test"}
        )
        # Assert
        assert response.status_code == 401

    def test_simulate_validates_input(self, client, mock_service, auth_header):
        """Test that /simulate validates request format."""
        # Act - missing required 'input' field
        response = client.post(
            "/agents/geo/simulate",
            headers=auth_header,
            json={}
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestChatEndpoint:
    """Tests for POST /agents/{agent_id}/chat - Real execution."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked service."""
        return TestClient(app)

    def test_chat_returns_real_response(self, client, mock_service, auth_header):
        """Test that /chat returns real response with mode='real'."""
        # Arrange
        mock_service.chat_agent = AsyncMock(return_value=SimulationResponse(
            response="The capital of France is Paris.",
            trace=[],
            metadata={
                "mode": "real",
                "agent_id": "geo",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}
            }
        ))

        # Act
        response = client.post(
            "/agents/geo/chat",
            headers=auth_header,
            json={"input": "What is the capital of France?"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["mode"] == "real"
        assert "usage" in data["metadata"]
        assert "[MOCK]" not in data["response"]
        assert mock_service.chat_agent.called

    def test_chat_includes_usage_metadata(self, client, mock_service, auth_header):
        """Test that /chat includes token usage in metadata."""
        # Arrange
        mock_service.chat_agent = AsyncMock(return_value=SimulationResponse(
            response="Answer",
            trace=[],
            metadata={
                "mode": "real",
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 20,
                    "total_tokens": 70
                }
            }
        ))

        # Act
        response = client.post(
            "/agents/geo/chat",
            headers=auth_header,
            json={"input": "Test"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "usage" in data["metadata"]
        assert data["metadata"]["usage"]["total_tokens"] == 70

    def test_chat_supports_session(self, client, mock_service, auth_header):
        """Test that /chat supports session_id parameter."""
        # Arrange
        mock_service.chat_agent = AsyncMock(return_value=SimulationResponse(
            response="Answer",
            trace=[],
            metadata={
                "mode": "real",
                "session_id": "test-session-123",
                "session_enabled": True
            }
        ))

        # Act
        response = client.post(
            "/agents/geo/chat",
            headers=auth_header,
            json={"input": "Test", "session_id": "test-session-123"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["session_enabled"] is True
        assert data["metadata"]["session_id"] == "test-session-123"

    @pytest.mark.skipif(
        os.getenv("AUTH_ENABLED", "false").lower() != "true",
        reason="Auth is disabled in test environment"
    )
    def test_chat_requires_authentication(self, client, mock_service):
        """Test that /chat requires API key when auth is enabled."""
        # Setup mock service with async method
        mock_service.chat_agent = AsyncMock(return_value=SimulationResponse(
            response="test", trace=[], metadata={}
        ))
        
        # Act - no auth header (auth should be enabled for this test)
        response = client.post(
            "/agents/geo/chat",
            json={"input": "Test"}
        )
        # Assert
        assert response.status_code == 401


class TestChatStreamEndpoint:
    """Tests for POST /agents/{agent_id}/chat/stream - Real streaming."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked service."""
        return TestClient(app)

    async def async_stream_generator(self):
        """Helper to generate mock stream chunks."""
        from server.models import StreamChunk
        yield StreamChunk(type="metadata", metadata={"agent_id": "geo"})
        yield StreamChunk(type="token", content="Hello")
        yield StreamChunk(type="token", content=" World")
        yield StreamChunk(type="done", metadata={})

    def test_chat_stream_returns_sse(self, client, mock_service, auth_header):
        """Test that /chat/stream returns Server-Sent Events format."""
        # Arrange
        mock_service.chat_agent_streaming = Mock(return_value=self.async_stream_generator())

        # Act
        response = client.post(
            "/agents/geo/chat/stream",
            headers=auth_header,
            json={"input": "Test"}
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"

    def test_chat_stream_includes_metadata_chunk(self, client, mock_service, auth_header):
        """Test that /chat/stream includes metadata chunk first."""
        # Arrange
        mock_service.chat_agent_streaming = Mock(return_value=self.async_stream_generator())

        # Act
        response = client.post(
            "/agents/geo/chat/stream",
            headers=auth_header,
            json={"input": "Test"}
        )

        # Assert
        assert response.status_code == 200
        content = response.text
        assert "data:" in content
        assert '"type":"metadata"' in content or '"type": "metadata"' in content

    @pytest.mark.skipif(
        os.getenv("AUTH_ENABLED", "false").lower() != "true",
        reason="Auth is disabled in test environment"
    )
    def test_chat_stream_requires_authentication(self, client, mock_service):
        """Test that /chat/stream requires API key when auth is enabled."""
        # Act - no auth header (auth should be enabled for this test)
        response = client.post(
            "/agents/geo/chat/stream",
            json={"input": "Test"}
        )
        # Assert
        assert response.status_code == 401


class TestEndpointComparison:
    """Integration tests comparing all three endpoints."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked service."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_service_with_methods(self, mock_service):
        """Setup mock service with all methods."""
        mock_service.simulate_agent = AsyncMock()
        mock_service.chat_agent = AsyncMock()
        mock_service.chat_agent_streaming = Mock()
        return mock_service

    def test_all_endpoints_accept_same_request_format(self, client, mock_service_with_methods, auth_header):
        """Test that all three endpoints accept the same request format."""
        mock_service = mock_service_with_methods
        # Arrange
        request_data = {
            "input": "Test input",
            "context": {"user_id": "123"},
            "max_steps": 10,
            "session_id": "session-123"
        }

        mock_service.simulate_agent.return_value = SimulationResponse(
            response="Mock", trace=[], metadata={}
        )
        mock_service.chat_agent.return_value = SimulationResponse(
            response="Real", trace=[], metadata={}
        )
        mock_service.chat_agent_streaming.return_value = iter([])

        # Act - Call all three endpoints
        response_simulate = client.post("/agents/geo/simulate", headers=auth_header, json=request_data)
        response_chat = client.post("/agents/geo/chat", headers=auth_header, json=request_data)
        response_stream = client.post("/agents/geo/chat/stream", headers=auth_header, json=request_data)

        # Assert - All accept the request
        assert response_simulate.status_code == 200
        assert response_chat.status_code == 200
        assert response_stream.status_code == 200

    def test_simulate_vs_chat_metadata_differs(self, client, mock_service_with_methods, auth_header):
        """Test that /simulate and /chat return different metadata.mode values."""
        mock_service = mock_service_with_methods
        # Arrange
        mock_service.simulate_agent.return_value = SimulationResponse(
            response="Mock", trace=[], metadata={"mode": "mock"}
        )
        mock_service.chat_agent.return_value = SimulationResponse(
            response="Real", trace=[], metadata={"mode": "real"}
        )

        # Act
        response_simulate = client.post(
            "/agents/geo/simulate",
            headers=auth_header,
            json={"input": "Test"}
        )
        response_chat = client.post(
            "/agents/geo/chat",
            headers=auth_header,
            json={"input": "Test"}
        )

        # Assert
        assert response_simulate.json()["metadata"]["mode"] == "mock"
        assert response_chat.json()["metadata"]["mode"] == "real"


class TestErrorHandling:
    """Tests for error handling across all endpoints."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked service."""
        return TestClient(app)

    def test_simulate_handles_agent_not_found(self, client, mock_service, auth_header):
        """Test error handling when agent doesn't exist."""
        # Arrange
        from asdrp.agents.protocol import AgentException
        mock_service.simulate_agent = AsyncMock(side_effect=AgentException("Agent not found"))

        # Act
        response = client.post(
            "/agents/nonexistent/simulate",
            headers=auth_header,
            json={"input": "Test"}
        )

        # Assert
        assert response.status_code == 400
        assert "Agent not found" in response.json()["detail"]

    def test_chat_handles_execution_failure(self, client, mock_service, auth_header):
        """Test error handling when agent execution fails."""
        # Arrange
        from asdrp.agents.protocol import AgentException
        mock_service.chat_agent = AsyncMock(side_effect=AgentException("Execution failed"))

        # Act
        response = client.post(
            "/agents/geo/chat",
            headers=auth_header,
            json={"input": "Test"}
        )

        # Assert
        assert response.status_code == 400
        assert "Execution failed" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
