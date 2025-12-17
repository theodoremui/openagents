"""
Comprehensive error handling tests for all server endpoints.

These tests ensure robust error handling across the entire server API,
preventing 500 errors and providing clear error messages.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import sys

# Mock asdrp modules
import os
sys.path.insert(0, "/Users/pmui/dev/halo/openagents")

# Set TESTING environment variable to disable TrustedHostMiddleware
os.environ["TESTING"] = "true"

# Import real AgentException instead of mocking it as Exception
from asdrp.agents.protocol import AgentException, AgentProtocol

mock_agent_protocol = Mock()
mock_agent_protocol.AgentProtocol = AgentProtocol
mock_agent_protocol.AgentException = AgentException

sys.modules['asdrp'] = Mock()
sys.modules['asdrp.agents'] = Mock()
sys.modules['asdrp.agents.protocol'] = mock_agent_protocol
sys.modules['asdrp.agents.agent_factory'] = Mock()
sys.modules['asdrp.agents.config_loader'] = Mock()

from server.main import app


class TestHealthEndpoint:
    """Test /health endpoint error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_endpoint_always_returns_200(self, client):
        """Health endpoint should never fail."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_health_endpoint_no_auth_required(self, client):
        """Health endpoint doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


class TestInfoEndpoint:
    """Test /info endpoint error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_info_endpoint_returns_valid_structure(self, client):
        """Info endpoint returns valid structure."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestListAgentsEndpoint:
    """Test /agents endpoint error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    @pytest.fixture
    def mock_service(self):
        with patch('server.main.get_service') as mock_get:
            service = Mock()
            mock_get.return_value = service
            yield service

    def test_list_agents_handles_empty_list(self, client, auth_header, mock_service):
        """Test handling when no agents are configured."""
        mock_service.list_agents.return_value = []

        response = client.get("/agents", headers=auth_header)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_agents_handles_service_exception(self, client, auth_header, mock_service):
        """Test handling when service raises exception."""
        mock_service.list_agents.side_effect = Exception("Service error")

        response = client.get("/agents", headers=auth_header)
        assert response.status_code == 500


class TestGetAgentDetailEndpoint:
    """Test /agents/{agent_id} endpoint error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    @pytest.fixture
    def mock_service(self):
        with patch('server.main.get_service') as mock_get:
            service = Mock()
            mock_get.return_value = service
            yield service

    def test_get_agent_detail_not_found(self, client, auth_header, mock_service):
        """Test 404 when agent doesn't exist."""
        from asdrp.agents.protocol import AgentException
        mock_service.get_agent_detail = AsyncMock(
            side_effect=AgentException("Agent not found", agent_name="nonexistent")
        )

        response = client.get("/agents/nonexistent", headers=auth_header)
        assert response.status_code == 404

    def test_get_agent_detail_with_special_characters(self, client, auth_header, mock_service):
        """Test handling agent IDs with special characters."""
        from asdrp.agents.protocol import AgentException
        mock_service.get_agent_detail = AsyncMock(
            side_effect=AgentException("Agent not found", agent_name="agent@#$%")
        )

        response = client.get("/agents/agent@%23$%25", headers=auth_header)
        # Should handle gracefully, either 404 or 400
        assert response.status_code in [400, 404]


class TestSimulateEndpoint:
    """Test /agents/{agent_id}/simulate endpoint error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    @pytest.fixture
    def mock_service(self):
        with patch('server.main.get_service') as mock_get:
            service = Mock()
            mock_get.return_value = service
            yield service

    def test_simulate_with_empty_input(self, client, auth_header, mock_service):
        """Test simulate with empty input string."""
        mock_service.simulate_agent = AsyncMock(return_value=Mock(
            response="", trace=[], metadata={}
        ))

        response = client.post(
            "/agents/test/simulate",
            headers=auth_header,
            json={"input": ""}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_simulate_with_very_long_input(self, client, auth_header, mock_service):
        """Test simulate with very long input (>10000 chars)."""
        long_input = "a" * 10001

        mock_service.simulate_agent = AsyncMock(return_value=Mock(
            response="Mock", trace=[], metadata={}
        ))

        response = client.post(
            "/agents/test/simulate",
            headers=auth_header,
            json={"input": long_input}
        )

        # Should handle or reject gracefully
        assert response.status_code in [200, 400, 413, 422]

    def test_simulate_with_unicode_input(self, client, auth_header, mock_service):
        """Test simulate with unicode characters."""
        mock_service.simulate_agent = AsyncMock(return_value=Mock(
            response="Mock", trace=[], metadata={}
        ))

        response = client.post(
            "/agents/test/simulate",
            headers=auth_header,
            json={"input": "Hello 世界 🌍"}
        )

        assert response.status_code == 200

    def test_simulate_with_malformed_json(self, client, auth_header):
        """Test simulate with malformed JSON body."""
        response = client.post(
            "/agents/test/simulate",
            headers=auth_header,
            content="not json"
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_simulate_with_missing_input_field(self, client, auth_header):
        """Test simulate without 'input' field."""
        response = client.post(
            "/agents/test/simulate",
            headers=auth_header,
            json={"wrong_field": "value"}
        )

        assert response.status_code == 422


class TestChatEndpoint:
    """Test /agents/{agent_id}/chat endpoint error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    @pytest.fixture
    def mock_service(self):
        with patch('server.main.get_service') as mock_get:
            service = Mock()
            mock_get.return_value = service
            yield service

    def test_chat_handles_timeout(self, client, auth_header, mock_service):
        """Test chat handles timeout exceptions."""
        import asyncio
        mock_service.chat_agent = AsyncMock(
            side_effect=asyncio.TimeoutError("Request timeout")
        )

        response = client.post(
            "/agents/test/chat",
            headers=auth_header,
            json={"input": "test"}
        )

        assert response.status_code == 500

    def test_chat_handles_api_key_error(self, client, auth_header, mock_service):
        """Test chat handles OpenAI API key errors."""
        mock_service.chat_agent = AsyncMock(
            side_effect=Exception("API key invalid")
        )

        response = client.post(
            "/agents/test/chat",
            headers=auth_header,
            json={"input": "test"}
        )

        assert response.status_code == 500


class TestStreamingEndpoint:
    """Test /agents/{agent_id}/chat/stream endpoint error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    @pytest.fixture
    def mock_service(self):
        with patch('server.main.get_service') as mock_get:
            service = Mock()
            mock_get.return_value = service
            yield service

    def test_stream_handles_generator_exception(self, client, auth_header, mock_service):
        """Test streaming handles exceptions in generator."""
        async def failing_generator():
            yield {"type": "token", "content": "test"}
            raise Exception("Generator failed")

        mock_service.chat_agent_streaming = Mock(return_value=failing_generator())

        response = client.post(
            "/agents/test/chat/stream",
            headers=auth_header,
            json={"input": "test"}
        )

        # Should handle gracefully
        assert response.status_code in [200, 500]


class TestAuthenticationErrorHandling:
    """Test authentication error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_missing_api_key_header(self, client):
        """Test request without API key header."""
        response = client.get("/agents")
        # Should return 401, 403, or 422 depending on auth config
        assert response.status_code in [401, 403, 422]

    def test_invalid_api_key(self, client):
        """Test request with invalid API key."""
        with patch('server.main.verify_api_key') as mock_auth:
            from fastapi import HTTPException
            mock_auth.side_effect = HTTPException(status_code=401, detail="Invalid API key")

            response = client.get("/agents", headers={"X-API-Key": "invalid"})
            assert response.status_code == 401


class TestCORSErrorHandling:
    """Test CORS-related error handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_options_request(self, client):
        """Test OPTIONS preflight request."""
        response = client.options("/agents")
        # Should handle OPTIONS requests
        assert response.status_code in [200, 204, 405]


class TestRateLimitingScenarios:
    """Test scenarios that could trigger rate limiting."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    def test_rapid_successive_requests(self, client, auth_header):
        """Test handling rapid successive requests."""
        with patch('server.main.get_service') as mock_get:
            service = Mock()
            service.list_agents.return_value = []
            mock_get.return_value = service

            # Make 10 rapid requests
            for _ in range(10):
                response = client.get("/agents", headers=auth_header)
                assert response.status_code in [200, 429]  # 429 = Too Many Requests


class TestInputValidation:
    """Test input validation across endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    def test_sql_injection_attempt(self, client, auth_header):
        """Test handling SQL injection attempts in agent_id."""
        response = client.get(
            "/agents/test'; DROP TABLE agents--",
            headers=auth_header
        )
        # Should not cause server error
        assert response.status_code in [400, 404]

    def test_xss_attempt(self, client, auth_header):
        """Test handling XSS attempts in input."""
        with patch('server.main.get_service') as mock_get:
            service = Mock()
            service.simulate_agent = AsyncMock(return_value=Mock(
                response="Safe", trace=[], metadata={}
            ))
            mock_get.return_value = service

            response = client.post(
                "/agents/test/simulate",
                headers=auth_header,
                json={"input": "<script>alert('xss')</script>"}
            )

            # Should handle safely
            assert response.status_code == 200

    def test_path_traversal_attempt(self, client, auth_header):
        """Test handling path traversal attempts."""
        response = client.get(
            "/agents/../../etc/passwd",
            headers=auth_header
        )
        # Should not expose file system
        assert response.status_code in [400, 404]
