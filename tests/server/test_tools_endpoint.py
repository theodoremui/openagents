"""
Comprehensive tests for the /agents/{agent_id}/tools diagnostic endpoint.

This endpoint was experiencing 500 errors when trying to extract tool names
from wrapped function objects. These tests ensure robust error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import sys

# Mock asdrp modules before importing server
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


class TestToolsEndpoint:
    """Tests for GET /agents/{agent_id}/tools endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        """Mock authentication."""
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    @pytest.fixture
    def mock_factory(self):
        """Mock AgentFactory."""
        with patch('asdrp.agents.agent_factory.AgentFactory') as mock_factory_class:
            factory = Mock()
            mock_factory_class.instance.return_value = factory
            yield factory

    def test_tools_endpoint_with_normal_tools(self, client, auth_header, mock_factory):
        """Test endpoint with tools that have .name attribute."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

        tool1 = Mock()
        tool1.name = "get_coordinates"

        tool2 = Mock()
        tool2.name = "search_places"

        mock_agent.tools = [tool1, tool2]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test"
        assert data["agent_name"] == "TestAgent"
        assert data["tool_count"] == 2
        assert "get_coordinates" in data["tool_names"]
        assert "search_places" in data["tool_names"]

    def test_tools_endpoint_with_function_objects(self, client, auth_header, mock_factory):
        """Test endpoint with tools that only have __name__ attribute."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

        tool1 = Mock()
        del tool1.name  # Remove .name attribute
        tool1.__name__ = "geocode_address"

        tool2 = Mock()
        del tool2.name
        tool2.__name__ = "reverse_geocode"

        mock_agent.tools = [tool1, tool2]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 2
        assert "geocode_address" in data["tool_names"]
        assert "reverse_geocode" in data["tool_names"]

    def test_tools_endpoint_with_nested_function_attribute(self, client, auth_header, mock_factory):
        """Test endpoint with tools wrapped with .function attribute."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

        inner_function = Mock()
        inner_function.__name__ = "get_place_details"

        tool = Mock()
        del tool.name
        del tool.__name__
        tool.function = inner_function

        mock_agent.tools = [tool]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 1
        assert "get_place_details" in data["tool_names"]

    def test_tools_endpoint_with_class_name_fallback(self, client, auth_header, mock_factory):
        """Test endpoint falls back to __class__.__name__ when other attributes missing."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

        tool = Mock()
        del tool.name
        del tool.__name__
        tool.function = None  # No nested function either
        type(tool).__name__ = "CustomToolWrapper"

        mock_agent.tools = [tool]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 1
        assert "CustomToolWrapper" in data["tool_names"]

    def test_tools_endpoint_with_coroutine_object(self, client, auth_header, mock_factory):
        """Test endpoint handles coroutine objects gracefully (original bug)."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

        # Simulate a coroutine object (the original issue)
        async def async_tool():
            pass

        coroutine_tool = async_tool()  # This creates a coroutine object

        mock_agent.tools = [coroutine_tool]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 1
        # Should get fallback name since coroutine objects don't have .name
        assert len(data["tool_names"]) == 1

        # Cleanup coroutine
        coroutine_tool.close()

    def test_tools_endpoint_with_exception_in_tool_extraction(self, client, auth_header, mock_factory):
        """Test endpoint handles exceptions during tool name extraction."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

        # Create a tool that raises exception on attribute access
        tool = Mock()

        def raise_error(*args, **kwargs):
            raise AttributeError("Attribute access failed")

        tool.__getattribute__ = Mock(side_effect=raise_error)

        mock_agent.tools = [tool]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 1
        # Should use fallback naming
        assert "tool_0" in data["tool_names"]

    def test_tools_endpoint_with_mixed_tool_types(self, client, auth_header, mock_factory):
        """Test endpoint with a mix of different tool types."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "MapAgent"

        # Tool with .name
        tool1 = Mock()
        tool1.name = "get_static_map_url"

        # Tool with __name__
        tool2 = Mock()
        del tool2.name
        tool2.__name__ = "get_interactive_map_data"

        # Tool with nested function
        inner_func = Mock()
        inner_func.__name__ = "get_route_polyline"
        tool3 = Mock()
        del tool3.name
        del tool3.__name__
        tool3.function = inner_func

        mock_agent.tools = [tool1, tool2, tool3]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 3
        assert "get_static_map_url" in data["tool_names"]
        assert "get_interactive_map_data" in data["tool_names"]
        assert "get_route_polyline" in data["tool_names"]

    def test_tools_endpoint_with_no_tools(self, client, auth_header, mock_factory):
        """Test endpoint when agent has no tools."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.tools = []
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 0
        assert data["tool_names"] == []
        assert data["has_get_static_map_url"] is False
        assert data["has_get_interactive_map_data"] is False

    def test_tools_endpoint_with_none_tools(self, client, auth_header, mock_factory):
        """Test endpoint when agent.tools is None."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.tools = None
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 0
        assert data["tool_names"] == []

    def test_tools_endpoint_agent_not_found(self, client, auth_header, mock_factory):
        """Test endpoint returns 404 when agent doesn't exist."""
        # Arrange
        from asdrp.agents.protocol import AgentException
        mock_factory.get_agent.side_effect = AgentException("Agent not found", agent_name="nonexistent")

        # Act
        response = client.get("/agents/nonexistent/tools", headers=auth_header)

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_tools_endpoint_checks_for_interactive_map_tool(self, client, auth_header, mock_factory):
        """Test endpoint specifically checks for new get_interactive_map_data tool."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "MapAgent"

        tool1 = Mock()
        tool1.name = "get_static_map_url"

        tool2 = Mock()
        tool2.name = "get_interactive_map_data"

        mock_agent.tools = [tool1, tool2]
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/map/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["has_get_static_map_url"] is True
        assert data["has_get_interactive_map_data"] is True

    def test_tools_endpoint_includes_timestamp(self, client, auth_header, mock_factory):
        """Test endpoint includes ISO timestamp in response."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.tools = []
        mock_factory.get_agent.return_value = mock_agent

        # Act
        response = client.get("/agents/test/tools", headers=auth_header)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        # Verify it's a valid ISO timestamp format
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))

    def test_tools_endpoint_requires_authentication(self, client, mock_factory):
        """Test endpoint requires valid API key."""
        # Arrange
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.tools = []
        mock_factory.get_agent.return_value = mock_agent

        # Act - no auth header
        response = client.get("/agents/test/tools")

        # Assert
        # Should fail due to missing auth (actual behavior depends on auth middleware)
        assert response.status_code in [401, 403, 422]


class TestToolsEndpointIntegration:
    """Integration tests with real MapAgent tools structure."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_header(self):
        with patch('server.main.verify_api_key') as mock_auth:
            mock_auth.return_value = "test_key"
            yield {"X-API-Key": "test_key"}

    def test_tools_endpoint_with_maptools_structure(self, client, auth_header):
        """Test with structure similar to actual MapTools.tool_list."""
        with patch('asdrp.agents.agent_factory.AgentFactory') as mock_factory_class:
            factory = Mock()
            mock_factory_class.instance.return_value = factory

            # Simulate MapTools.tool_list structure
            mock_agent = Mock()
            mock_agent.name = "MapAgent"

            # Create mock tools that mimic real wrapped functions
            tools = []
            tool_names = [
                "get_coordinates_by_address",
                "get_address_by_coordinates",
                "search_places_nearby",
                "get_place_details",
                "get_travel_time_distance",
                "get_distance_matrix",
                "places_autocomplete",
                "get_route_polyline",
                "get_static_map_url",
                "get_interactive_map_data"
            ]

            for name in tool_names:
                tool = Mock()
                tool.name = name
                tools.append(tool)

            mock_agent.tools = tools
            factory.get_agent.return_value = mock_agent

            # Act
            response = client.get("/agents/map/tools", headers=auth_header)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["tool_count"] == 10
            assert set(data["tool_names"]) == set(tool_names)
            assert data["has_get_static_map_url"] is True
            assert data["has_get_interactive_map_data"] is True
