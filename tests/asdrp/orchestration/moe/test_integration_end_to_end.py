"""
Integration tests for MoE Map Rendering and YelpMCP Error Fix.

**Feature: moe-map-rendering-fix, Integration Testing**
**Validates: All requirements integration testing**

This module implements integration tests for the complete MoE pipeline to verify:
1. End-to-end map rendering flow (query → MoE → synthesis → frontend rendering)
2. Error scenario handling (missing API keys, MCP server failures, malformed JSON)
3. Fallback mechanism validation

These tests validate the complete system integration across all components.
"""

import pytest
import json
import asyncio
import tempfile
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoEResult, MoETrace
from asdrp.orchestration.moe.config_loader import MoEConfigLoader, MoEConfig
from asdrp.orchestration.moe.exceptions import ConfigException, ExecutionException
from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.protocol import AgentProtocol


@pytest.fixture
def integration_config():
    """Create a realistic MoE configuration for integration testing."""
    config_dict = {
        "enabled": True,
        "moe": {
            "mixing_strategy": "synthesis",
            "top_k_experts": 3,
            "confidence_threshold": 0.3,
            "timeout_per_expert": 25.0,
            "overall_timeout": 30.0,
            "synthesis_prompt": "Synthesize the following expert responses for the query '{query}':\n\n{weighted_results}\n\nProvide a comprehensive answer that combines the best insights from each expert."
        },
        "models": {
            "selection": {
                "name": "gpt-4.1-mini",
                "temperature": 0.0,
                "max_tokens": 1000
            },
            "mixing": {
                "name": "gpt-4.1-mini", 
                "temperature": 0.7,
                "max_tokens": 2000
            }
        },
        "experts": {
            "business_expert": {
                "agents": ["yelp", "yelp_mcp"],
                "capabilities": ["business_search"],
                "weight": 1.0
            },
            "location_expert": {
                "agents": ["map", "geo"],
                "capabilities": ["mapping", "geocoding"],
                "weight": 0.8
            }
        },
        "cache": {
            "enabled": False,
            "type": "none",
            "storage": {"backend": "none"},
            "policy": {}
        },
        "error_handling": {
            "fallback_agent": "one",
            "fallback_message": "I apologize, but I encountered an issue."
        },
        "tracing": {
            "enabled": True,
            "storage": {"backend": "memory"},
            "exporters": []
        }
    }
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_dict, f)
        temp_path = Path(f.name)
    
    # Load configuration
    loader = MoEConfigLoader(temp_path)
    config = loader.load_config()
    
    # Clean up
    temp_path.unlink()
    
    return config


@pytest.fixture
def mock_agent_factory_integration():
    """Mock agent factory with realistic agent behaviors for integration testing."""
    factory = Mock(spec=AgentFactory)
    
    # Create realistic mock agents
    agents = {}
    
    # Yelp agent - returns business data
    yelp_agent = Mock(spec=AgentProtocol)
    yelp_agent.name = "yelp"
    agents["yelp"] = yelp_agent
    
    # YelpMCP agent - returns business data with coordinates
    yelp_mcp_agent = Mock(spec=AgentProtocol)
    yelp_mcp_agent.name = "yelp_mcp"
    yelp_mcp_agent.mcp_servers = []  # Simulate MCP servers
    agents["yelp_mcp"] = yelp_mcp_agent
    
    # Map agent - returns interactive map JSON
    map_agent = Mock(spec=AgentProtocol)
    map_agent.name = "map"
    agents["map"] = map_agent
    
    # Geo agent - returns geocoding data
    geo_agent = Mock(spec=AgentProtocol)
    geo_agent.name = "geo"
    agents["geo"] = geo_agent
    
    # Fallback agent
    one_agent = Mock(spec=AgentProtocol)
    one_agent.name = "one"
    agents["one"] = one_agent
    
    # Mock sessions
    mock_session = Mock()
    
    async def get_agent_with_session(agent_id, session_id):
        agent = agents.get(agent_id, agents["one"])
        return (agent, mock_session)
    
    factory.get_agent_with_persistent_session = AsyncMock(side_effect=get_agent_with_session)
    
    # Mock available agents for validation
    factory.get_available_agents = Mock(return_value=list(agents.keys()))
    
    return factory


class TestEndToEndMapRendering:
    """Integration tests for end-to-end map rendering flow."""

    @pytest.mark.asyncio
    async def test_complete_map_rendering_flow_success(self, integration_config, mock_agent_factory_integration):
        """
        Test complete flow from business+map query to rendered interactive map.
        
        This test validates the entire pipeline:
        1. Query processing
        2. Expert selection (business + map agents)
        3. Parallel execution with realistic responses
        4. Result synthesis with JSON preservation
        5. Interactive map JSON extraction
        """
        # Mock Runner.run for realistic agent responses
        async def mock_runner_run(starting_agent, input, session, **kwargs):
            mock_result = Mock()
            
            if starting_agent.name == "yelp_mcp":
                # YelpMCP returns business data with coordinates
                mock_result.final_output = """I found great Greek restaurants in San Francisco:

1. **Kokkari Estiatorio** - 200 Jackson St, San Francisco, CA 94111
   - Rating: 4.5/5 stars
   - Coordinates: 37.7956, -122.4009
   - Hours: Mon-Thu 11:30am-10pm, Fri-Sat 11:30am-11pm, Sun 5-10pm

2. **Souvla** - 517 Hayes St, San Francisco, CA 94102  
   - Rating: 4.3/5 stars
   - Coordinates: 37.7766, -122.4242
   - Hours: Daily 11am-10pm

3. **Opa!** - 3149 16th St, San Francisco, CA 94103
   - Rating: 4.2/5 stars  
   - Coordinates: 37.7648, -122.4194
   - Hours: Daily 11am-9pm"""
                
            elif starting_agent.name == "map":
                # Map agent returns interactive map JSON
                map_config = {
                    "type": "interactive_map",
                    "config": {
                        "map_type": "places",
                        "center_lat": 37.7749,
                        "center_lng": -122.4194,
                        "zoom": 13,
                        "markers": [
                            {
                                "lat": 37.7956,
                                "lng": -122.4009,
                                "title": "Kokkari Estiatorio",
                                "description": "4.5/5 stars - 200 Jackson St"
                            },
                            {
                                "lat": 37.7766,
                                "lng": -122.4242,
                                "title": "Souvla", 
                                "description": "4.3/5 stars - 517 Hayes St"
                            },
                            {
                                "lat": 37.7648,
                                "lng": -122.4194,
                                "title": "Opa!",
                                "description": "4.2/5 stars - 3149 16th St"
                            }
                        ]
                    }
                }
                mock_result.final_output = f"Here's an interactive map showing the Greek restaurants:\n\n```json\n{json.dumps(map_config, indent=2)}\n```"
                
            elif starting_agent.name == "yelp":
                # Regular Yelp agent returns business data without coordinates
                mock_result.final_output = """Top Greek restaurants in San Francisco:

• Kokkari Estiatorio - Upscale Greek dining, 4.5 stars
• Souvla - Modern Greek fast-casual, 4.3 stars  
• Opa! - Traditional Greek taverna, 4.2 stars"""
                
            else:
                # Fallback response
                mock_result.final_output = f"Response from {starting_agent.name}"
            
            return mock_result
        
        # Patch Runner.run
        with patch('agents.Runner.run', new=AsyncMock(side_effect=mock_runner_run)):
            # Create orchestrator
            orchestrator = MoEOrchestrator.create_default(
                agent_factory=mock_agent_factory_integration,
                config=integration_config
            )
            
            # Execute map visualization query
            query = "Place the top 3 Greek restaurants in San Francisco as pins on a detailed map"
            result = await orchestrator.route_query(query)
            
            # Verify successful execution
            assert isinstance(result, MoEResult)
            assert result.response is not None
            assert len(result.response) > 0
            
            # Verify experts were used
            assert len(result.experts_used) > 0
            assert any(expert in ["yelp_mcp", "yelp", "map"] for expert in result.experts_used)
            
            # Verify trace information
            assert isinstance(result.trace, MoETrace)
            assert result.trace.latency_ms > 0
            assert result.trace.selected_experts is not None
            assert len(result.trace.selected_experts) > 0
            
            # CRITICAL: Verify interactive map JSON is present in response
            assert "```json" in result.response, "Response should contain JSON block"
            assert "interactive_map" in result.response, "Response should contain interactive map"
            assert "markers" in result.response, "Response should contain map markers"
            
            # Extract and validate JSON
            import re
            json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
            json_matches = json_pattern.findall(result.response)
            
            assert len(json_matches) > 0, "Should find at least one JSON block"
            
            # Parse the JSON to ensure it's valid
            map_json = json.loads(json_matches[0])
            assert map_json["type"] == "interactive_map"
            assert "config" in map_json
            assert "markers" in map_json["config"]
            assert len(map_json["config"]["markers"]) > 0
            
            # Verify markers have required fields
            for marker in map_json["config"]["markers"]:
                assert "lat" in marker
                assert "lng" in marker
                assert "title" in marker
                assert isinstance(marker["lat"], (int, float))
                assert isinstance(marker["lng"], (int, float))

    @pytest.mark.asyncio
    async def test_business_data_without_map_partial_success(self, integration_config, mock_agent_factory_integration):
        """
        Test partial success scenario where business data is available but map fails.
        
        This validates the system's ability to provide useful results even when
        some components fail.
        """
        # Mock Runner.run with map agent failure
        async def mock_runner_run_partial(starting_agent, input, session, **kwargs):
            mock_result = Mock()
            
            if starting_agent.name == "yelp_mcp":
                # YelpMCP succeeds with business data
                mock_result.final_output = """Found Greek restaurants in San Francisco:

1. Kokkari Estiatorio - 200 Jackson St, 4.5 stars
2. Souvla - 517 Hayes St, 4.3 stars
3. Opa! - 3149 16th St, 4.2 stars"""
                
            elif starting_agent.name == "map":
                # Map agent fails (timeout simulation)
                raise asyncio.TimeoutError("Map agent timed out")
                
            elif starting_agent.name == "yelp":
                # Regular Yelp agent succeeds
                mock_result.final_output = "Greek restaurants: Kokkari, Souvla, Opa!"
                
            else:
                mock_result.final_output = f"Response from {starting_agent.name}"
            
            return mock_result
        
        # Patch Runner.run
        with patch('agents.Runner.run', new=AsyncMock(side_effect=mock_runner_run_partial)):
            # Create orchestrator
            orchestrator = MoEOrchestrator.create_default(
                agent_factory=mock_agent_factory_integration,
                config=integration_config
            )
            
            # Execute query
            query = "Show me Greek restaurants in San Francisco on a map"
            result = await orchestrator.route_query(query)
            
            # Verify partial success
            assert isinstance(result, MoEResult)
            assert result.response is not None
            assert len(result.response) > 0
            
            # Should have business data even without map
            assert any(restaurant in result.response for restaurant in ["Kokkari", "Souvla", "Opa"])
            
            # Should not be a complete failure
            assert "I apologize" not in result.response
            
            # Verify trace shows partial success
            assert result.trace.latency_ms > 0
            if result.trace.expert_details:
                successful_experts = [d for d in result.trace.expert_details if d.status == "completed"]
                failed_experts = [d for d in result.trace.expert_details if d.status == "failed"]
                
                # Should have at least one successful expert (business)
                assert len(successful_experts) > 0
                
                # Should have at least one failed expert (map)
                assert len(failed_experts) > 0


class TestErrorScenarioHandling:
    """Integration tests for error scenario handling."""

    @pytest.mark.asyncio
    async def test_mcp_server_failure_fallback(self, integration_config, mock_agent_factory_integration):
        """
        Test MCP server failure with fallback to regular yelp agent.
        
        This validates the business agent fallback mechanism.
        """
        # Mock Runner.run with MCP failure
        async def mock_runner_run_mcp_fail(starting_agent, input, session, **kwargs):
            mock_result = Mock()
            
            if starting_agent.name == "yelp_mcp":
                # YelpMCP fails due to MCP server issue
                raise Exception("MCP server connection failed: Server not initialized")
                
            elif starting_agent.name == "yelp":
                # Regular Yelp agent succeeds as fallback
                mock_result.final_output = "Greek restaurants in SF: Kokkari Estiatorio, Souvla, Opa!"
                
            else:
                mock_result.final_output = f"Response from {starting_agent.name}"
            
            return mock_result
        
        # Patch Runner.run
        with patch('agents.Runner.run', new=AsyncMock(side_effect=mock_runner_run_mcp_fail)):
            # Create orchestrator
            orchestrator = MoEOrchestrator.create_default(
                agent_factory=mock_agent_factory_integration,
                config=integration_config
            )
            
            # Execute query
            query = "Find Greek restaurants in San Francisco"
            result = await orchestrator.route_query(query)
            
            # Verify fallback worked
            assert isinstance(result, MoEResult)
            assert result.response is not None
            assert len(result.response) > 0
            
            # Should have business data from fallback yelp agent
            assert "Greek restaurants" in result.response or "Kokkari" in result.response
            
            # Should not be complete failure
            assert "I apologize" not in result.response

    @pytest.mark.asyncio
    async def test_all_experts_fail_fallback_agent(self, integration_config, mock_agent_factory_integration):
        """
        Test scenario where all selected experts fail, triggering fallback agent.
        
        This validates the system's ultimate fallback mechanism.
        """
        # Mock Runner.run with all experts failing
        async def mock_runner_run_all_fail(starting_agent, input, session, **kwargs):
            mock_result = Mock()
            
            if starting_agent.name in ["yelp_mcp", "yelp", "map", "geo"]:
                # All experts fail
                raise Exception(f"{starting_agent.name} failed")
                
            elif starting_agent.name == "one":
                # Fallback agent succeeds
                mock_result.final_output = "I can help you find information about Greek restaurants in San Francisco. Let me search for that."
                
            else:
                mock_result.final_output = f"Response from {starting_agent.name}"
            
            return mock_result
        
        # Patch Runner.run
        with patch('agents.Runner.run', new=AsyncMock(side_effect=mock_runner_run_all_fail)):
            # Create orchestrator
            orchestrator = MoEOrchestrator.create_default(
                agent_factory=mock_agent_factory_integration,
                config=integration_config
            )
            
            # Execute query
            query = "Find Greek restaurants in San Francisco"
            result = await orchestrator.route_query(query)
            
            # Verify fallback agent was used
            assert isinstance(result, MoEResult)
            assert result.response is not None
            assert len(result.response) > 0
            
            # Should use fallback agent
            assert "one" in result.experts_used
            
            # Should have fallback response
            assert "Greek restaurants" in result.response or "help you find" in result.response
            
            # Trace should indicate fallback
            assert result.trace.fallback == True

    @pytest.mark.asyncio
    async def test_configuration_validation_prevents_startup(self, mock_agent_factory_integration):
        """
        Test that invalid configuration prevents orchestrator startup.
        
        This validates the startup configuration validation.
        """
        # Create configuration with invalid agent reference
        invalid_config_dict = {
            "enabled": True,
            "moe": {"top_k_experts": 2},
            "models": {
                "selection": {
                    "name": "gpt-4.1-mini",
                    "temperature": 0.0,
                    "max_tokens": 1000
                },
                "mixing": {
                    "name": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            },
            "experts": {
                "test_expert": {
                    "agents": ["nonexistent_agent"],  # Invalid agent reference
                    "capabilities": ["business_search"],
                    "weight": 1.0
                }
            },
            "cache": {"enabled": False, "type": "none"},
            "error_handling": {"fallback_agent": "one"},
            "tracing": {"enabled": False}
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config_dict, f)
            temp_path = Path(f.name)
        
        try:
            # Load configuration (this should succeed)
            loader = MoEConfigLoader(temp_path)
            invalid_config = loader.load_config()
            
            # Attempt to create orchestrator should fail due to startup validation
            with pytest.raises(ConfigException) as exc_info:
                MoEOrchestrator.create_default(
                    agent_factory=mock_agent_factory_integration,
                    config=invalid_config
                )
            
            # Verify error message is descriptive
            error_message = str(exc_info.value)
            assert "nonexistent_agent" in error_message
            assert "unknown agent" in error_message.lower()
            
        finally:
            # Clean up
            temp_path.unlink()


class TestFrontendMapDetection:
    """Integration tests for frontend map detection and rendering."""

    def test_interactive_map_json_detection(self):
        """
        Test frontend detection of interactive map JSON blocks.
        
        This simulates the frontend map detection logic.
        """
        # Sample MoE response with interactive map
        moe_response = """I found the top Greek restaurants in San Francisco and placed them on a map:

1. **Kokkari Estiatorio** - Upscale Greek dining
2. **Souvla** - Modern Greek fast-casual  
3. **Opa!** - Traditional Greek taverna

```json
{
  "type": "interactive_map",
  "config": {
    "map_type": "places",
    "center_lat": 37.7749,
    "center_lng": -122.4194,
    "zoom": 13,
    "markers": [
      {
        "lat": 37.7956,
        "lng": -122.4009,
        "title": "Kokkari Estiatorio",
        "description": "4.5/5 stars - 200 Jackson St"
      },
      {
        "lat": 37.7766,
        "lng": -122.4242,
        "title": "Souvla",
        "description": "4.3/5 stars - 517 Hayes St"
      }
    ]
  }
}
```

These restaurants offer authentic Greek cuisine with excellent ratings."""
        
        # Simulate frontend detection logic
        def detect_interactive_maps(content: str):
            """Simulate frontend map detection."""
            import re
            
            maps = []
            json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
            
            for match in json_pattern.finditer(content):
                try:
                    json_data = json.loads(match.group(1))
                    if isinstance(json_data, dict) and json_data.get("type") == "interactive_map":
                        maps.append({
                            "config": json_data.get("config"),
                            "raw": match.group(1),
                            "valid": True
                        })
                except json.JSONDecodeError:
                    maps.append({
                        "config": None,
                        "raw": match.group(1),
                        "valid": False,
                        "error": "Invalid JSON"
                    })
            
            return maps
        
        # Test detection
        detected_maps = detect_interactive_maps(moe_response)
        
        # Verify detection worked
        assert len(detected_maps) == 1, "Should detect one interactive map"
        
        map_data = detected_maps[0]
        assert map_data["valid"] == True, "Map should be valid"
        assert map_data["config"] is not None, "Should have config"
        assert map_data["config"]["map_type"] == "places", "Should be places map"
        assert len(map_data["config"]["markers"]) == 2, "Should have 2 markers"
        
        # Verify marker data
        for marker in map_data["config"]["markers"]:
            assert "lat" in marker and "lng" in marker, "Markers should have coordinates"
            assert "title" in marker, "Markers should have titles"
            assert isinstance(marker["lat"], (int, float)), "Latitude should be numeric"
            assert isinstance(marker["lng"], (int, float)), "Longitude should be numeric"

    def test_malformed_json_error_recovery(self):
        """
        Test frontend error recovery for malformed JSON blocks.
        
        This validates the frontend's ability to handle malformed JSON gracefully.
        """
        # Sample response with malformed JSON
        malformed_response = """Here's the map data:

```json
{
  "type": "interactive_map",
  "config": {
    "map_type": "places",
    "markers": [
      {
        "lat": 37.7956,
        "lng": -122.4009,
        "title": "Restaurant"
        // Missing comma and closing bracket
```

The data above shows the restaurant locations."""
        
        # Simulate frontend detection with error recovery
        def detect_with_error_recovery(content: str):
            """Simulate frontend detection with error handling."""
            import re
            
            results = []
            json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
            
            for match in json_pattern.finditer(content):
                json_str = match.group(1).strip()
                try:
                    json_data = json.loads(json_str)
                    results.append({
                        "valid": True,
                        "data": json_data,
                        "raw": json_str,
                        "error": None
                    })
                except json.JSONDecodeError as e:
                    results.append({
                        "valid": False,
                        "data": None,
                        "raw": json_str,
                        "error": f"JSON parsing error: {str(e)}"
                    })
            
            return results
        
        # Test error recovery
        results = detect_with_error_recovery(malformed_response)
        
        # Verify error handling
        assert len(results) == 1, "Should detect one JSON block"
        
        result = results[0]
        assert result["valid"] == False, "Should be marked as invalid"
        assert result["error"] is not None, "Should have error message"
        assert "JSON parsing error" in result["error"], "Should indicate JSON parsing error"
        assert result["raw"] is not None, "Should preserve raw content for fallback display"
        assert len(result["raw"]) > 0, "Raw content should not be empty"