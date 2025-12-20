"""
Property-based tests for MoE Error Handling and Fallback Mechanisms.

**Feature: moe-map-rendering-fix, Properties 12-14: Error Handling and Fallback**
**Validates: Requirements 5.1, 5.3, 3.5, 5.5**

This module implements property-based testing for the MoE orchestrator to verify:
1. Business Agent Fallback (Property 12) - yelp_mcp → yelp fallback when MCP fails
2. Partial Success Handling (Property 13) - business data without map when map agent fails  
3. Frontend Error Recovery (Property 14) - malformed JSON and rendering failure handling

These tests use Hypothesis to generate random test cases and verify that
the correctness properties hold across all valid inputs.
"""

import pytest
import json
import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoEResult, MoETrace
from asdrp.orchestration.moe.expert_executor import ExpertResult, ParallelExecutor
from asdrp.orchestration.moe.result_mixer import WeightedMixer, MixedResult
from asdrp.orchestration.moe.config_loader import MoEConfig, ModelConfig, ExpertGroupConfig, MoECacheConfig
from asdrp.orchestration.moe.exceptions import ExecutionException, MixingException
from asdrp.agents.protocol import AgentProtocol


# Test data strategies for property-based testing

@composite
def business_query(draw):
    """Generate business-related queries that would trigger yelp agents."""
    business_types = ["restaurant", "cafe", "bar", "shop", "hotel", "gym", "salon"]
    locations = ["San Francisco", "New York", "Los Angeles", "Chicago", "Seattle", "Boston"]
    
    business_type = draw(st.sampled_from(business_types))
    location = draw(st.sampled_from(locations))
    
    query_templates = [
        f"Find {business_type}s in {location}",
        f"Show me the best {business_type}s near {location}",
        f"Where are good {business_type}s in {location}",
        f"List top {business_type}s in {location}",
        f"Recommend {business_type}s in {location}"
    ]
    
    return draw(st.sampled_from(query_templates))


@composite
def map_visualization_query(draw):
    """Generate queries that request both business data and map visualization."""
    base_query = draw(business_query())
    map_keywords = ["on a map", "show on map", "detailed map", "interactive map", "map view"]
    map_keyword = draw(st.sampled_from(map_keywords))
    
    return f"{base_query} {map_keyword}"


@composite
def yelp_business_data(draw):
    """Generate realistic Yelp business data."""
    business_name = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs"))))
    rating = draw(st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False))
    address = draw(st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Pc"))))
    
    return {
        "name": business_name,
        "rating": rating,
        "address": address,
        "coordinates": {
            "lat": draw(st.floats(min_value=37.0, max_value=38.0, allow_nan=False, allow_infinity=False)),
            "lng": draw(st.floats(min_value=-123.0, max_value=-122.0, allow_nan=False, allow_infinity=False))
        }
    }


@composite
def expert_execution_scenario(draw):
    """Generate scenarios with different expert success/failure combinations."""
    yelp_mcp_success = draw(st.booleans())
    yelp_success = draw(st.booleans())
    map_success = draw(st.booleans())
    
    # Ensure at least one business agent can succeed for meaningful tests
    if not yelp_mcp_success and not yelp_success:
        yelp_success = True
    
    return {
        "yelp_mcp_success": yelp_mcp_success,
        "yelp_success": yelp_success,
        "map_success": map_success
    }


@pytest.fixture
def mock_moe_config():
    """Mock MoE configuration for testing."""
    return MoEConfig(
        enabled=True,
        moe={
            "mixing_strategy": "synthesis",
            "top_k_experts": 3,
            "confidence_threshold": 0.3,
            "timeout_per_expert": 25.0,
            "overall_timeout": 30.0,
            "synthesis_prompt": "Synthesize: {weighted_results}\nQuery: {query}"
        },
        models={
            "selection": ModelConfig(
                name="gpt-4.1-mini",
                temperature=0.0,
                max_tokens=1000
            ),
            "mixing": ModelConfig(
                name="gpt-4.1-mini", 
                temperature=0.7,
                max_tokens=2000
            )
        },
        experts={
            "business_expert": ExpertGroupConfig(
                agents=["yelp", "yelp_mcp"],
                capabilities=["business_search"],
                weight=1.0
            ),
            "location_expert": ExpertGroupConfig(
                agents=["map", "geo"],
                capabilities=["mapping", "geocoding"],
                weight=0.8
            )
        },
        cache=MoECacheConfig(
            enabled=False,
            type="none",
            storage={"backend": "none"},
            policy={}
        ),
        error_handling={
            "fallback_agent": "one",
            "fallback_message": "I apologize, but I encountered an issue."
        },
        tracing={"enabled": False, "storage": {"backend": "none"}, "exporters": []}
    )


@pytest.fixture
def mock_agent_factory():
    """Mock agent factory for testing."""
    factory = Mock()
    
    # Create mock agents
    yelp_agent = Mock(spec=AgentProtocol)
    yelp_agent.name = "yelp"
    
    yelp_mcp_agent = Mock(spec=AgentProtocol)
    yelp_mcp_agent.name = "yelp_mcp"
    yelp_mcp_agent.mcp_servers = []  # Empty list to simulate MCP connection issues
    
    map_agent = Mock(spec=AgentProtocol)
    map_agent.name = "map"
    
    fallback_agent = Mock(spec=AgentProtocol)
    fallback_agent.name = "one"
    
    # Mock sessions
    mock_session = Mock()
    
    async def get_agent_with_session(agent_id, session_id):
        agents = {
            "yelp": (yelp_agent, mock_session),
            "yelp_mcp": (yelp_mcp_agent, mock_session),
            "map": (map_agent, mock_session),
            "one": (fallback_agent, mock_session)
        }
        return agents.get(agent_id, (fallback_agent, mock_session))
    
    factory.get_agent_with_persistent_session = AsyncMock(side_effect=get_agent_with_session)
    
    return factory


class TestBusinessAgentFallbackProperties:
    """Property-based tests for business agent fallback mechanisms."""

    @given(
        query=business_query(),
        scenario=expert_execution_scenario()
    )
    @settings(max_examples=30, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_12_business_agent_fallback(self, mock_moe_config, mock_agent_factory, query, scenario):
        """
        **Feature: moe-map-rendering-fix, Property 12: Business Agent Fallback**
        **Validates: Requirements 5.1**
        
        Property: For any yelp_mcp agent failure, the system should use the response 
        from the yelp agent as a fallback without failing the entire query.
        """
        # Skip scenarios where both business agents fail (not testing fallback)
        assume(scenario["yelp_mcp_success"] == False and scenario["yelp_success"] == True)
        
        # Create mock expert selector that selects both business agents
        mock_selector = Mock()
        mock_selector.select = AsyncMock(return_value=["yelp_mcp", "yelp", "map"])
        
        # Create mock executor that simulates the failure scenario
        mock_executor = Mock()
        
        async def mock_execute_parallel(agents_with_sessions, query, context, timeout):
            results = []
            
            for expert_id, agent, session in agents_with_sessions:
                if expert_id == "yelp_mcp" and not scenario["yelp_mcp_success"]:
                    # Simulate MCP connection failure
                    results.append(ExpertResult(
                        expert_id="yelp_mcp",
                        output="",
                        success=False,
                        latency_ms=100.0,
                        error="MCP server connection failed: Server not initialized"
                    ))
                elif expert_id == "yelp" and scenario["yelp_success"]:
                    # Simulate successful yelp response
                    business_data = f"Found great restaurants: Restaurant A (4.5 stars), Restaurant B (4.2 stars)"
                    results.append(ExpertResult(
                        expert_id="yelp",
                        output=business_data,
                        success=True,
                        latency_ms=800.0
                    ))
                elif expert_id == "map" and scenario["map_success"]:
                    # Simulate map response
                    map_json = {
                        "type": "interactive_map",
                        "config": {
                            "map_type": "places",
                            "markers": [{"lat": 37.7749, "lng": -122.4194, "title": "Restaurant A"}]
                        }
                    }
                    results.append(ExpertResult(
                        expert_id="map",
                        output=f"```json\n{json.dumps(map_json, indent=2)}\n```",
                        success=True,
                        latency_ms=1200.0
                    ))
                else:
                    # Default failure for other cases
                    results.append(ExpertResult(
                        expert_id=expert_id,
                        output="",
                        success=False,
                        latency_ms=50.0,
                        error="Agent failed"
                    ))
            
            return results
        
        mock_executor.execute_parallel = AsyncMock(side_effect=mock_execute_parallel)
        
        # Create mock result mixer
        mock_mixer = Mock()
        
        async def mock_mix(expert_results, expert_ids, query):
            # Find successful business results
            successful_business = [r for r in expert_results if r.success and r.expert_id in ["yelp", "yelp_mcp"]]
            
            if successful_business:
                # Should use the successful yelp agent result as fallback
                content = successful_business[0].output
                return MixedResult(
                    content=content,
                    weights={"yelp": 1.0},
                    quality_score=0.8
                )
            else:
                return MixedResult(
                    content="No business data available",
                    weights={},
                    quality_score=0.0
                )
        
        mock_mixer.mix = AsyncMock(side_effect=mock_mix)
        
        # Create orchestrator with mocked components
        orchestrator = MoEOrchestrator(
            agent_factory=mock_agent_factory,
            expert_selector=mock_selector,
            expert_executor=mock_executor,
            result_mixer=mock_mixer,
            config=mock_moe_config
        )
        
        # Execute the query
        result = await orchestrator.route_query(query)
        
        # Verify the result
        assert isinstance(result, MoEResult)
        assert result.response is not None
        assert len(result.response.strip()) > 0
        
        # CRITICAL PROPERTY: When yelp_mcp fails, yelp should provide the business data
        # The response should contain business information from the successful yelp agent
        assert "Restaurant A" in result.response or "restaurants" in result.response.lower()
        
        # Verify that yelp was used (not yelp_mcp)
        assert "yelp" in result.experts_used or len([e for e in result.experts_used if e != "yelp_mcp"]) > 0
        
        # The system should not fail completely - should have meaningful business data
        assert "I apologize" not in result.response  # Should not be fallback error message
        assert result.response != "No business data available"


class TestPartialSuccessHandlingProperties:
    """Property-based tests for partial success handling."""

    @given(
        query=map_visualization_query(),
        business_data=yelp_business_data()
    )
    @settings(max_examples=25, deadline=8000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_13_partial_success_handling(self, mock_moe_config, mock_agent_factory, query, business_data):
        """
        **Feature: moe-map-rendering-fix, Property 13: Partial Success Handling**
        **Validates: Requirements 5.3**
        
        Property: For any scenario where the map agent fails but business agents succeed,
        the system should return business data without map visualization.
        """
        # Create mock expert selector
        mock_selector = Mock()
        mock_selector.select = AsyncMock(return_value=["yelp", "map"])
        
        # Create mock executor that simulates business success + map failure
        mock_executor = Mock()
        
        async def mock_execute_partial_success(agents_with_sessions, query, context, timeout):
            results = []
            
            for expert_id, agent, session in agents_with_sessions:
                if expert_id == "yelp":
                    # Simulate successful business data
                    business_output = f"Found {business_data['name']} - {business_data['rating']} stars at {business_data['address']}"
                    results.append(ExpertResult(
                        expert_id="yelp",
                        output=business_output,
                        success=True,
                        latency_ms=600.0
                    ))
                elif expert_id == "map":
                    # Simulate map agent failure
                    results.append(ExpertResult(
                        expert_id="map",
                        output="",
                        success=False,
                        latency_ms=25000.0,  # Timeout
                        error="Timeout after 25s"
                    ))
                else:
                    results.append(ExpertResult(
                        expert_id=expert_id,
                        output="",
                        success=False,
                        latency_ms=100.0,
                        error="Not selected"
                    ))
            
            return results
        
        mock_executor.execute_parallel = AsyncMock(side_effect=mock_execute_partial_success)
        
        # Create mock result mixer that handles partial success
        mock_mixer = Mock()
        
        async def mock_mix_partial(expert_results, expert_ids, query):
            successful_results = [r for r in expert_results if r.success]
            
            if successful_results:
                # Should return business data even without map
                content = successful_results[0].output
                # Note: Real mixer would attempt auto-injection, but for property testing
                # we focus on the core behavior of not failing when map is missing
                return MixedResult(
                    content=content,
                    weights={successful_results[0].expert_id: 1.0},
                    quality_score=0.6  # Reduced quality due to missing map
                )
            else:
                return MixedResult(
                    content="No data available",
                    weights={},
                    quality_score=0.0
                )
        
        mock_mixer.mix = AsyncMock(side_effect=mock_mix_partial)
        
        # Create orchestrator
        orchestrator = MoEOrchestrator(
            agent_factory=mock_agent_factory,
            expert_selector=mock_selector,
            expert_executor=mock_executor,
            result_mixer=mock_mixer,
            config=mock_moe_config
        )
        
        # Execute the query
        result = await orchestrator.route_query(query)
        
        # Verify the result
        assert isinstance(result, MoEResult)
        assert result.response is not None
        assert len(result.response.strip()) > 0
        
        # CRITICAL PROPERTY: Should return business data even when map fails
        # The business information should be present in the response
        assert business_data["name"] in result.response or "Found" in result.response
        
        # Should not be a complete failure
        assert "I apologize" not in result.response
        assert result.response != "No data available"
        
        # Should have used the business agent
        assert "yelp" in result.experts_used
        
        # Quality should be reasonable (partial success is still success)
        assert result.trace.latency_ms > 0  # Should have executed something


class TestFrontendErrorRecoveryProperties:
    """Property-based tests for frontend error recovery mechanisms."""

    @given(
        malformed_json=st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs")))
    )
    @settings(max_examples=20, deadline=5000)
    def test_property_14_frontend_error_recovery_malformed_json(self, malformed_json):
        """
        **Feature: moe-map-rendering-fix, Property 14: Frontend Error Recovery**
        **Validates: Requirements 3.5, 5.5**
        
        Property: For any malformed JSON block or rendering failure, the system should
        display an error message and fall back to showing raw JSON.
        
        Note: This test simulates the frontend behavior since we can't run React components
        in the backend test environment. We test the detection logic that would be used.
        """
        # Simulate malformed JSON in a code block
        malformed_content = f"Here's some data:\n\n```json\n{malformed_json}\n```\n\nThat was the data."
        
        # Test the detection function (simulating frontend logic)
        def detect_interactive_map_blocks_with_error_recovery(content: str):
            """Simulate the frontend detection with error recovery."""
            import re
            
            results = []
            
            # Try to find JSON blocks
            json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
            
            for match in json_pattern.finditer(content):
                json_str = match.group(1).strip()
                
                try:
                    # Try to parse JSON
                    parsed = json.loads(json_str)
                    
                    if isinstance(parsed, dict) and parsed.get("type") == "interactive_map":
                        # Valid interactive map
                        results.append({
                            "config": parsed.get("config"),
                            "raw": json_str,
                            "valid": True,
                            "error": None
                        })
                    else:
                        # Valid JSON but not interactive map
                        results.append({
                            "config": None,
                            "raw": json_str,
                            "valid": False,
                            "error": "Not an interactive map"
                        })
                        
                except json.JSONDecodeError as e:
                    # Malformed JSON - should be handled gracefully
                    results.append({
                        "config": None,
                        "raw": json_str,
                        "valid": False,
                        "error": f"JSON parsing error: {str(e)}"
                    })
            
            return results
        
        # Test the detection with malformed JSON
        detected_blocks = detect_interactive_map_blocks_with_error_recovery(malformed_content)
        
        # CRITICAL PROPERTY: Should detect the block but mark it as invalid
        if "```json" in malformed_content:
            assert len(detected_blocks) > 0
            
            # Should have error information for malformed JSON
            malformed_block = detected_blocks[0]
            assert malformed_block["valid"] == False
            assert malformed_block["error"] is not None
            assert "JSON parsing error" in malformed_block["error"]
            assert malformed_block["raw"] == malformed_json
            
            # The system should provide error recovery information
            # (In real frontend, this would show error message + raw JSON)
            assert len(malformed_block["raw"]) > 0  # Raw content available for fallback display

    @given(
        valid_map_config=st.fixed_dictionaries({
            "map_type": st.sampled_from(["route", "places", "location"]),
            "zoom": st.integers(min_value=1, max_value=20)
        })
    )
    @settings(max_examples=15, deadline=3000)
    def test_property_14_frontend_error_recovery_invalid_config(self, valid_map_config):
        """
        **Feature: moe-map-rendering-fix, Property 14: Frontend Error Recovery**
        **Validates: Requirements 3.5, 5.5**
        
        Property: For any invalid map configuration, the system should validate
        the config and provide appropriate error messages.
        """
        # Create JSON with missing required fields for the map type
        incomplete_json = {
            "type": "interactive_map",
            "config": valid_map_config  # Missing required fields like origin/destination for route
        }
        
        json_str = json.dumps(incomplete_json, indent=2)
        content = f"Map data:\n\n```json\n{json_str}\n```"
        
        # Test validation function (simulating frontend logic)
        def validate_map_configuration(config):
            """Simulate frontend map config validation."""
            if not config or not isinstance(config, dict):
                return False, "Configuration is not a valid object"
            
            map_type = config.get("map_type")
            if map_type not in ["route", "places", "location"]:
                return False, f"Invalid map_type: {map_type}"
            
            if map_type == "route":
                if not config.get("origin") or not config.get("destination"):
                    return False, "Route maps require origin and destination"
            
            elif map_type in ["places", "location"]:
                has_center = (config.get("center_lat") is not None and 
                             config.get("center_lng") is not None)
                has_markers = (isinstance(config.get("markers"), list) and 
                              len(config.get("markers", [])) > 0)
                
                if not has_center and not has_markers:
                    return False, "Places/location maps require center coordinates or markers"
            
            return True, None
        
        # Test validation
        is_valid, error_message = validate_map_configuration(valid_map_config)
        
        # CRITICAL PROPERTY: Should detect configuration issues and provide clear errors
        if valid_map_config.get("map_type") == "route":
            # Route maps without origin/destination should be invalid
            assert is_valid == False
            assert error_message is not None
            assert "origin and destination" in error_message
        
        elif valid_map_config.get("map_type") in ["places", "location"]:
            # Places maps without center or markers should be invalid
            if not valid_map_config.get("center_lat") and not valid_map_config.get("markers"):
                assert is_valid == False
                assert error_message is not None
                assert "center coordinates or markers" in error_message
        
        # Error messages should be descriptive and actionable
        if error_message:
            assert len(error_message) > 10  # Should be descriptive
            assert any(word in error_message.lower() for word in ["require", "invalid", "missing"])