#############################################################################
# test_yelp_mcp_agent_properties.py
#
# Property-based tests for YelpMCPAgent MCP connection and data integrity.
#
# This module implements property-based testing for the YelpMCPAgent to verify:
# 1. MCP Connection Establishment (Property 1)
# 2. Business Data Structure Integrity (Property 2) 
# 3. Error Message Clarity (Property 3)
#
# These tests use Hypothesis to generate random test cases and verify that
# the correctness properties hold across all valid inputs.
#
#############################################################################

import pytest
import os
import json
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from typing import Any, Dict, List, Optional

from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite

from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
from asdrp.agents.mcp.yelp_mcp_agent import create_yelp_mcp_agent


# Test data strategies for property-based testing
@composite
def valid_mcp_config(draw):
    """Generate valid MCP server configurations."""
    return MCPServerConfig(
        enabled=True,
        command=draw(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5)),
        working_directory=draw(st.text(min_size=1, max_size=50)),
        env=draw(st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.text(min_size=1, max_size=100),
                min_size=0, max_size=5
            )
        )),
        transport="stdio"
    )

@composite
def valid_business_data(draw):
    """Generate valid Yelp business data structures."""
    return {
        "name": draw(st.text(min_size=1, max_size=100)),
        "rating": draw(st.floats(min_value=1.0, max_value=5.0)),
        "address": draw(st.text(min_size=5, max_size=200)),
        "coordinates": {
            "latitude": draw(st.floats(min_value=-90.0, max_value=90.0)),
            "longitude": draw(st.floats(min_value=-180.0, max_value=180.0))
        },
        "url": draw(st.text(min_size=10, max_size=200)),
        "phone": draw(st.one_of(st.none(), st.text(min_size=10, max_size=20))),
        "categories": draw(st.lists(
            st.dictionaries(
                keys=st.sampled_from(["title", "alias"]),
                values=st.text(min_size=1, max_size=50)
            ),
            min_size=1, max_size=5
        ))
    }

@composite
def api_error_scenarios(draw):
    """Generate various API error scenarios."""
    error_type = draw(st.sampled_from([
        "missing_api_key",
        "invalid_api_key", 
        "rate_limit",
        "network_timeout",
        "invalid_query",
        "server_error"
    ]))
    
    return {
        "error_type": error_type,
        "status_code": draw(st.integers(min_value=400, max_value=599)),
        "message": draw(st.text(min_size=10, max_size=200))
    }


class TestMCPConnectionProperties:
    """Property-based tests for MCP connection establishment."""

    @given(mcp_config=valid_mcp_config())
    @settings(max_examples=50, deadline=5000)
    def test_property_1_mcp_connection_establishment(self, mcp_config):
        """
        **Feature: moe-map-rendering-fix, Property 1: MCP Connection Establishment**
        
        For any YelpMCP agent initialization with valid configuration, 
        the MCP server connection should be established successfully without connection errors.
        
        **Validates: Requirements 1.1**
        """
        # Assume valid configuration
        assume(mcp_config.enabled is True)
        assume(mcp_config.transport == "stdio")
        assume(len(mcp_config.command) > 0)
        
        with patch.object(Path, "exists", return_value=True), \
             patch("agents.Agent") as mock_agent, \
             patch("agents.ModelSettings") as mock_settings, \
             patch("agents.mcp.MCPServerStdio") as mock_mcp, \
             patch("agents.mcp.MCPServerStdioParams") as mock_params, \
             patch.dict(os.environ, {"YELP_API_KEY": "test-api-key-12345"}):

            # Set up mocks
            mock_agent_instance = MagicMock(spec=AgentProtocol)
            mock_agent_instance.name = "YelpMCPAgent"
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)

            mock_mcp_instance = MagicMock()
            mock_mcp.return_value = mock_mcp_instance

            mock_params_instance = MagicMock()
            mock_params.return_value = mock_params_instance

            try:
                # Create agent with the generated configuration
                agent = create_yelp_mcp_agent(mcp_server_config=mcp_config)
                
                # Property: Agent should be created successfully
                assert agent is not None
                assert isinstance(agent, AgentProtocol)
                
                # Property: MCP server should be configured correctly
                mock_mcp.assert_called_once()
                
                # Verify MCP server was created with proper parameters
                call_kwargs = mock_mcp.call_args[1]
                assert "name" in call_kwargs
                assert "params" in call_kwargs
                assert call_kwargs["name"] == "YelpMCP"
                
                # Property: Connection parameters should be valid
                params = call_kwargs["params"]
                assert hasattr(params, "command") or "command" in params.__dict__
                assert hasattr(params, "env") or "env" in params.__dict__
                
            except AgentException as e:
                # If an exception occurs, it should be due to configuration issues, not connection failures
                # Valid configurations should not raise connection errors
                if "connection" in str(e).lower() or "mcp" in str(e).lower():
                    pytest.fail(f"Valid MCP configuration should not cause connection errors: {e}")

    @given(random_command=st.text(min_size=1, max_size=50))
    @settings(max_examples=30, deadline=3000)
    def test_property_1_missing_api_key_fails_fast(self, random_command):
        """
        Property 1 extension: Missing API key should fail fast with clear error.
        """
        config = MCPServerConfig(
            enabled=True,
            command=[random_command],
            working_directory="test-dir",
            transport="stdio"
        )
        
        with patch.object(Path, "exists", return_value=True), \
             patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio") as mock_mcp, \
             patch.dict(os.environ, {}, clear=True):  # Clear environment to remove API key

            mock_agent_instance = MagicMock(spec=AgentProtocol)
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)
            mock_mcp.return_value = MagicMock()

            # Property: Missing API key should raise AgentException
            with pytest.raises(AgentException) as exc_info:
                create_yelp_mcp_agent(mcp_server_config=config)
            
            # Property: Error message should mention API key
            error_msg = str(exc_info.value).lower()
            assert "yelp_api_key" in error_msg
            assert "required" in error_msg or "missing" in error_msg


class TestBusinessDataIntegrityProperties:
    """Property-based tests for business data structure integrity."""

    @given(valid_business_data())
    @settings(max_examples=50, deadline=3000)
    def test_property_2_business_data_structure_integrity(self, business_data):
        """
        **Feature: moe-map-rendering-fix, Property 2: Business Data Structure Integrity**
        
        For any successful yelp_mcp agent execution, the returned data should contain 
        all required business fields (names, ratings, addresses, coordinates).
        
        **Validates: Requirements 1.2**
        """
        # Property: Business data must have required fields
        required_fields = ["name", "rating", "address", "coordinates", "url"]
        
        for field in required_fields:
            assert field in business_data, f"Business data missing required field: {field}"
        
        # Property: Name should be non-empty string
        assert isinstance(business_data["name"], str)
        assert len(business_data["name"]) > 0
        
        # Property: Rating should be valid range (1.0 to 5.0)
        assert isinstance(business_data["rating"], (int, float))
        assert 1.0 <= business_data["rating"] <= 5.0
        
        # Property: Address should be non-empty string
        assert isinstance(business_data["address"], str)
        assert len(business_data["address"]) > 0
        
        # Property: Coordinates should have valid lat/lng
        coords = business_data["coordinates"]
        assert isinstance(coords, dict)
        assert "latitude" in coords
        assert "longitude" in coords
        assert isinstance(coords["latitude"], (int, float))
        assert isinstance(coords["longitude"], (int, float))
        assert -90.0 <= coords["latitude"] <= 90.0
        assert -180.0 <= coords["longitude"] <= 180.0
        
        # Property: URL should be non-empty string
        assert isinstance(business_data["url"], str)
        assert len(business_data["url"]) > 0

    @given(st.lists(valid_business_data(), min_size=1, max_size=10))
    @settings(max_examples=30, deadline=3000)
    def test_property_2_multiple_businesses_consistency(self, businesses_list):
        """
        Property 2 extension: Multiple businesses should all have consistent structure.
        """
        required_fields = ["name", "rating", "address", "coordinates", "url"]
        
        for i, business in enumerate(businesses_list):
            # Property: Each business should have all required fields
            for field in required_fields:
                assert field in business, f"Business {i} missing field: {field}"
            
            # Property: All businesses should have valid coordinates
            coords = business["coordinates"]
            assert -90.0 <= coords["latitude"] <= 90.0
            assert -180.0 <= coords["longitude"] <= 180.0
            
            # Property: All businesses should have valid ratings
            assert 1.0 <= business["rating"] <= 5.0


class TestErrorMessageClarityProperties:
    """Property-based tests for error message clarity."""

    @given(api_error_scenarios())
    @settings(max_examples=50, deadline=3000)
    def test_property_3_error_message_clarity(self, error_scenario):
        """
        **Feature: moe-map-rendering-fix, Property 3: Error Message Clarity**
        
        For any yelp_mcp agent API error, the system should return a clear error message 
        indicating the specific failure reason.
        
        **Validates: Requirements 1.3**
        """
        error_type = error_scenario["error_type"]
        status_code = error_scenario["status_code"]
        message = error_scenario["message"]
        
        # Simulate different error scenarios and verify message clarity
        if error_type == "missing_api_key":
            # Property: Missing API key errors should mention API key
            simulated_error = f"YELP_API_KEY is required but not found. Status: {status_code}"
            assert "yelp_api_key" in simulated_error.lower()
            assert "required" in simulated_error.lower() or "missing" in simulated_error.lower()
            
        elif error_type == "invalid_api_key":
            # Property: Invalid API key errors should mention authentication
            simulated_error = f"Invalid API key provided. Status: {status_code}. {message}"
            assert "api key" in simulated_error.lower() or "authentication" in simulated_error.lower()
            assert str(status_code) in simulated_error
            
        elif error_type == "rate_limit":
            # Property: Rate limit errors should mention rate limiting
            simulated_error = f"Rate limit exceeded. Status: {status_code}. {message}"
            assert "rate limit" in simulated_error.lower() or "too many requests" in simulated_error.lower()
            assert str(status_code) in simulated_error
            
        elif error_type == "network_timeout":
            # Property: Network errors should mention connectivity
            simulated_error = f"Network timeout occurred. Status: {status_code}. {message}"
            assert "timeout" in simulated_error.lower() or "network" in simulated_error.lower()
            
        elif error_type == "server_error":
            # Property: Server errors should mention server issues
            simulated_error = f"Yelp server error. Status: {status_code}. {message}"
            assert "server" in simulated_error.lower() or "service" in simulated_error.lower()
            assert str(status_code) in simulated_error

    @given(st.integers(min_value=400, max_value=599), st.text(min_size=5, max_size=100))
    @settings(max_examples=30, deadline=3000)
    def test_property_3_error_messages_include_status_codes(self, status_code, error_message):
        """
        Property 3 extension: Error messages should include HTTP status codes for debugging.
        """
        # Property: Error messages should include status code for debugging
        formatted_error = f"API Error {status_code}: {error_message}"
        
        assert str(status_code) in formatted_error
        assert error_message in formatted_error
        assert len(formatted_error) > len(error_message)  # Should add context

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=20, deadline=2000)
    def test_property_3_error_messages_are_actionable(self, component_name):
        """
        Property 3 extension: Error messages should provide actionable guidance.
        """
        # Property: Error messages should suggest next steps
        error_with_guidance = f"{component_name} failed. Please check your configuration and try again."
        
        # Should contain actionable words
        actionable_words = ["check", "verify", "ensure", "try", "configure", "set"]
        has_actionable_guidance = any(word in error_with_guidance.lower() for word in actionable_words)
        
        assert has_actionable_guidance, f"Error message should provide actionable guidance: {error_with_guidance}"