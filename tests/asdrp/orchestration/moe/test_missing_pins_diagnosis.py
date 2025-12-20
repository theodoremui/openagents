"""
Comprehensive diagnostic test for missing pins in interactive maps.

This test traces the complete data flow from YelpMCP agent through MoE orchestrator
to frontend rendering to identify why pins are missing from the interactive map
when querying "Place the top 3 greek restaurants in San Francisco as pins on a detailed map".

**Investigation Focus:**
1. YelpMCP agent output format and coordinate extraction
2. MoE result mixer JSON block preservation
3. Frontend map detection and marker processing
4. Coordinate parsing and validation

**Root Cause Analysis:**
- Does YelpMCP agent include coordinates in its output?
- Are coordinates in the expected format for MapTools?
- Does the result mixer preserve or generate map JSON correctly?
- Does the frontend detect and parse markers properly?
"""

import pytest
import json
import asyncio
import re
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoEResult
from asdrp.orchestration.moe.expert_executor import ExpertResult, ParallelExecutor
from asdrp.orchestration.moe.result_mixer import WeightedMixer, MixedResult
from asdrp.orchestration.moe.config_loader import MoEConfig, ModelConfig, ExpertGroupConfig, MoECacheConfig
from asdrp.agents.protocol import AgentProtocol


class TestMissingPinsDiagnosis:
    """Comprehensive diagnostic tests for missing pins issue."""

    @pytest.fixture
    def mock_moe_config(self):
        """Mock MoE configuration for testing."""
        return MoEConfig(
            enabled=True,
            moe={
                "mixing_strategy": "synthesis",
                "top_k_experts": 3,
                "confidence_threshold": 0.3,
                "synthesis_prompt": """Synthesize the following expert responses into a comprehensive answer.

Expert Responses:
{weighted_results}

Original Query: {query}

CRITICAL - PRESERVE INTERACTIVE CONTENT:
- If any expert response contains a ```json code block (especially with "type": "interactive_map"),
  YOU MUST include that EXACT ```json block in your synthesized response
- DO NOT summarize, paraphrase, or remove ```json blocks - copy them verbatim

Synthesized Response:"""
            },
            models={
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
                    capabilities=["mapping"],
                    weight=0.8
                )
            },
            cache=MoECacheConfig(enabled=False, type="none", storage={"backend": "none"}, policy={}),
            error_handling={"fallback_agent": "one", "fallback_message": "I apologize, but I encountered an issue."},
            tracing={"enabled": False, "storage": {"backend": "none"}, "exporters": []}
        )

    @pytest.fixture
    def mock_agent_factory(self):
        """Mock agent factory with realistic agent responses."""
        factory = Mock()
        
        # Mock agents
        yelp_mcp_agent = Mock(spec=AgentProtocol)
        yelp_mcp_agent.name = "yelp_mcp"
        yelp_mcp_agent.mcp_servers = []
        
        map_agent = Mock(spec=AgentProtocol)
        map_agent.name = "map"
        
        mock_session = Mock()
        
        async def get_agent_with_session(agent_id, session_id):
            agents = {
                "yelp_mcp": (yelp_mcp_agent, mock_session),
                "map": (map_agent, mock_session)
            }
            return agents.get(agent_id, (Mock(), mock_session))
        
        factory.get_agent_with_persistent_session = AsyncMock(side_effect=get_agent_with_session)
        return factory

    def create_realistic_yelp_mcp_output(self) -> str:
        """
        Create realistic YelpMCP agent output based on actual agent behavior.
        
        This simulates the output format that YelpMCP agent produces when it successfully
        retrieves business data from Yelp Fusion AI via MCP.
        """
        return """Here are the top 3 Greek restaurants in San Francisco:

## Business 1: Kokkari Estiatorio
- **Rating**: 4.5/5 (1,234 reviews)
- **Address**: 200 Jackson St, San Francisco, CA 94111
- **Phone**: (415) 981-0983
- **Coordinates**: 37.796996, -122.398661
- **Price Range**: $$$$
- **Specialties**: Upscale Greek cuisine, seafood, lamb dishes
- [View on Yelp](https://www.yelp.com/biz/kokkari-estiatorio-san-francisco)

## Business 2: Milos Mezes
- **Rating**: 4.0/5 (567 reviews)  
- **Address**: 3348 Steiner St, San Francisco, CA 94123
- **Phone**: (415) 563-8368
- **Coordinates**: 37.800333, -122.423670
- **Price Range**: $$$
- **Specialties**: Traditional Greek mezze, grilled octopus, moussaka
- [View on Yelp](https://www.yelp.com/biz/milos-mezes-san-francisco)

## Business 3: Souvla
- **Rating**: 4.2/5 (890 reviews)
- **Address**: 517 Hayes St, San Francisco, CA 94102  
- **Phone**: (415) 400-4500
- **Coordinates**: 37.776685, -122.423943
- **Price Range**: $$
- **Specialties**: Greek street food, souvlaki, Greek salads
- [View on Yelp](https://www.yelp.com/biz/souvla-san-francisco)

These restaurants offer excellent Greek cuisine with different price points and atmospheres. All are highly rated and located in different neighborhoods of San Francisco."""

    def create_realistic_map_agent_output(self) -> str:
        """
        Create realistic MapAgent output with interactive map JSON.
        
        This simulates what MapAgent should produce when it processes the coordinates
        from YelpMCP agent output and generates an interactive map.
        """
        map_config = {
            "type": "interactive_map",
            "config": {
                "map_type": "places",
                "center_lat": 37.791338,  # Average of the 3 restaurants
                "center_lng": -122.415425,
                "zoom": 13,
                "markers": [
                    {
                        "lat": 37.796996,
                        "lng": -122.398661,
                        "title": "Kokkari Estiatorio",
                        "type": "restaurant"
                    },
                    {
                        "lat": 37.800333,
                        "lng": -122.423670,
                        "title": "Milos Mezes", 
                        "type": "restaurant"
                    },
                    {
                        "lat": 37.776685,
                        "lng": -122.423943,
                        "title": "Souvla",
                        "type": "restaurant"
                    }
                ]
            }
        }
        
        json_str = json.dumps(map_config, indent=2)
        return f"I'll create an interactive map showing the locations of these Greek restaurants:\n\n```json\n{json_str}\n```"

    @pytest.mark.asyncio
    async def test_end_to_end_missing_pins_diagnosis(self, mock_moe_config, mock_agent_factory):
        """
        **DIAGNOSTIC TEST: End-to-end missing pins investigation**
        
        This test simulates the exact user query and traces data flow through:
        1. YelpMCP agent output with coordinates
        2. MapAgent output with interactive map JSON
        3. MoE result mixer synthesis and JSON preservation
        4. Frontend map detection and marker processing
        
        **Expected Behavior:**
        - YelpMCP should provide business data with coordinates
        - MapAgent should generate interactive map JSON with markers
        - Result mixer should preserve the JSON block
        - Frontend should detect and render markers
        
        **Potential Root Causes:**
        - Coordinate format mismatch between YelpMCP and MapAgent
        - JSON block loss during synthesis
        - Frontend marker parsing issues
        - Missing or malformed marker data
        """
        query = "Place the top 3 greek restaurants in San Francisco as pins on a detailed map"
        
        # Create mock expert selector
        mock_selector = Mock()
        mock_selector.select = AsyncMock(return_value=["yelp_mcp", "map"])
        
        # Create mock executor with realistic outputs
        mock_executor = Mock()
        
        async def mock_execute_realistic(agents_with_sessions, query, context, timeout):
            results = []
            
            for expert_id, agent, session in agents_with_sessions:
                if expert_id == "yelp_mcp":
                    # Simulate successful YelpMCP response with coordinates
                    yelp_output = self.create_realistic_yelp_mcp_output()
                    results.append(ExpertResult(
                        expert_id="yelp_mcp",
                        output=yelp_output,
                        success=True,
                        latency_ms=1200.0
                    ))
                elif expert_id == "map":
                    # Simulate MapAgent generating interactive map from coordinates
                    map_output = self.create_realistic_map_agent_output()
                    results.append(ExpertResult(
                        expert_id="map",
                        output=map_output,
                        success=True,
                        latency_ms=800.0
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
        
        mock_executor.execute_parallel = AsyncMock(side_effect=mock_execute_realistic)
        
        # Create real result mixer to test actual synthesis behavior
        mixer = WeightedMixer(mock_moe_config)
        
        # Mock OpenAI to simulate synthesis that might lose JSON blocks
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = Mock()
            
            # Simulate LLM synthesis that drops the JSON block (common issue)
            synthesized_without_json = """Here are the top 3 Greek restaurants in San Francisco:

**1. Kokkari Estiatorio** - 4.5/5 stars
Located at 200 Jackson St, this upscale Greek restaurant specializes in seafood and lamb dishes.

**2. Milos Mezes** - 4.0/5 stars  
Found at 3348 Steiner St, offering traditional Greek mezze and grilled octopus.

**3. Souvla** - 4.2/5 stars
At 517 Hayes St, serving Greek street food including souvlaki and Greek salads.

These restaurants are located across different neighborhoods in San Francisco and offer various price points."""
            
            mock_response = Mock()
            mock_message = Mock()
            mock_message.content = synthesized_without_json
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 200
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Create orchestrator
            orchestrator = MoEOrchestrator(
                agent_factory=mock_agent_factory,
                expert_selector=mock_selector,
                expert_executor=mock_executor,
                result_mixer=mixer,
                config=mock_moe_config
            )
            
            # Execute the query
            result = await orchestrator.route_query(query)
            
            # DIAGNOSTIC ANALYSIS
            print("\n" + "="*80)
            print("MISSING PINS DIAGNOSTIC ANALYSIS")
            print("="*80)
            
            # 1. Verify YelpMCP output contains coordinates
            yelp_output = self.create_realistic_yelp_mcp_output()
            coordinates_pattern = r"- \*\*Coordinates\*\*: ([\d.-]+), ([\d.-]+)"
            coordinates_found = re.findall(coordinates_pattern, yelp_output)
            
            print(f"\n1. YelpMCP COORDINATE EXTRACTION:")
            print(f"   - Coordinates found: {len(coordinates_found)}")
            for i, (lat, lng) in enumerate(coordinates_found):
                print(f"   - Restaurant {i+1}: ({lat}, {lng})")
            
            # 2. Verify MapAgent output contains proper JSON
            map_output = self.create_realistic_map_agent_output()
            json_blocks = re.findall(r"```json\s*(.*?)\s*```", map_output, re.DOTALL | re.IGNORECASE)
            
            print(f"\n2. MAP AGENT JSON GENERATION:")
            print(f"   - JSON blocks found: {len(json_blocks)}")
            
            if json_blocks:
                try:
                    map_json = json.loads(json_blocks[0])
                    markers = map_json.get("config", {}).get("markers", [])
                    print(f"   - Markers in JSON: {len(markers)}")
                    for i, marker in enumerate(markers):
                        print(f"   - Marker {i+1}: {marker.get('title')} at ({marker.get('lat')}, {marker.get('lng')})")
                except json.JSONDecodeError as e:
                    print(f"   - JSON parsing error: {e}")
            
            # 3. Check if result mixer preserved JSON blocks
            print(f"\n3. RESULT MIXER JSON PRESERVATION:")
            print(f"   - Final response length: {len(result.response)}")
            
            final_json_blocks = re.findall(r"```json\s*(.*?)\s*```", result.response, re.DOTALL | re.IGNORECASE)
            print(f"   - JSON blocks in final response: {len(final_json_blocks)}")
            
            if final_json_blocks:
                try:
                    final_json = json.loads(final_json_blocks[0])
                    final_markers = final_json.get("config", {}).get("markers", [])
                    print(f"   - Markers preserved: {len(final_markers)}")
                    
                    # Check marker data integrity
                    for i, marker in enumerate(final_markers):
                        lat = marker.get("lat")
                        lng = marker.get("lng") 
                        title = marker.get("title")
                        print(f"   - Final Marker {i+1}: '{title}' at ({lat}, {lng})")
                        
                        # Validate marker data
                        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                            print(f"     ⚠️  ISSUE: Invalid coordinates type - lat: {type(lat)}, lng: {type(lng)}")
                        if not title or not isinstance(title, str):
                            print(f"     ⚠️  ISSUE: Missing or invalid title: {title}")
                            
                except json.JSONDecodeError as e:
                    print(f"   - ❌ JSON parsing error in final response: {e}")
                    print(f"   - Raw JSON: {final_json_blocks[0][:200]}...")
            else:
                print("   - ❌ NO JSON BLOCKS FOUND in final response")
                print("   - This indicates the result mixer failed to preserve the map JSON")
            
            # 4. Simulate frontend marker detection
            print(f"\n4. FRONTEND MARKER DETECTION SIMULATION:")
            
            def simulate_frontend_detection(content: str):
                """Simulate the frontend detectInteractiveMapBlocks function."""
                results = []
                
                # Pattern matching (same as frontend)
                json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
                
                for match in json_pattern.finditer(content):
                    json_str = match.group(1).strip()
                    
                    try:
                        obj = json.loads(json_str)
                        if obj.get("type") == "interactive_map" and "config" in obj:
                            config = obj["config"]
                            markers = config.get("markers", [])
                            
                            # Validate markers (same as frontend)
                            valid_markers = []
                            for marker in markers:
                                if (isinstance(marker.get("lat"), (int, float)) and 
                                    isinstance(marker.get("lng"), (int, float))):
                                    valid_markers.append(marker)
                            
                            results.append({
                                "config": config,
                                "markers": valid_markers,
                                "valid": len(valid_markers) > 0
                            })
                    except json.JSONDecodeError:
                        continue
                
                return results
            
            detected_maps = simulate_frontend_detection(result.response)
            print(f"   - Interactive maps detected: {len(detected_maps)}")
            
            for i, map_data in enumerate(detected_maps):
                markers = map_data["markers"]
                print(f"   - Map {i+1}: {len(markers)} valid markers")
                
                if len(markers) == 0:
                    print("     ❌ NO VALID MARKERS - This would cause missing pins!")
                    
                    # Analyze why markers are invalid
                    raw_markers = map_data["config"].get("markers", [])
                    print(f"     - Raw markers in config: {len(raw_markers)}")
                    
                    for j, raw_marker in enumerate(raw_markers):
                        lat = raw_marker.get("lat")
                        lng = raw_marker.get("lng")
                        title = raw_marker.get("title")
                        
                        issues = []
                        if not isinstance(lat, (int, float)):
                            issues.append(f"lat is {type(lat).__name__}: {lat}")
                        if not isinstance(lng, (int, float)):
                            issues.append(f"lng is {type(lng).__name__}: {lng}")
                        if not title:
                            issues.append("missing title")
                        
                        if issues:
                            print(f"     - Marker {j+1} issues: {', '.join(issues)}")
                else:
                    print("     ✅ Valid markers found - pins should render correctly")
            
            # 5. ROOT CAUSE ANALYSIS
            print(f"\n5. ROOT CAUSE ANALYSIS:")
            
            if len(coordinates_found) == 0:
                print("   ❌ ROOT CAUSE: YelpMCP agent not providing coordinates")
                print("      - YelpMCP output format may have changed")
                print("      - Coordinate extraction pattern may be incorrect")
            elif len(final_json_blocks) == 0:
                print("   ❌ ROOT CAUSE: Result mixer not preserving JSON blocks")
                print("      - LLM synthesis is dropping the interactive map JSON")
                print("      - JSON preservation mechanism is failing")
            elif len(detected_maps) == 0:
                print("   ❌ ROOT CAUSE: Frontend not detecting interactive maps")
                print("      - JSON format may not match frontend expectations")
                print("      - Detection regex patterns may be incorrect")
            elif any(len(m["markers"]) == 0 for m in detected_maps):
                print("   ❌ ROOT CAUSE: Invalid marker data in JSON")
                print("      - Marker coordinates are not numbers")
                print("      - Marker validation is failing in frontend")
            else:
                print("   ✅ All components working correctly")
                print("      - Issue may be in actual agent implementations")
                print("      - Check real YelpMCP and MapAgent outputs")
            
            print("="*80)
            
            # Assertions for test validation
            assert isinstance(result, MoEResult)
            assert result.response is not None
            assert len(result.response.strip()) > 0
            
            # The test should reveal where the issue occurs in the pipeline
            # This diagnostic information will guide the actual fix

    def test_coordinate_extraction_patterns(self):
        """
        **DIAGNOSTIC TEST: Coordinate extraction pattern validation**
        
        Tests various coordinate formats that YelpMCP might produce to ensure
        the extraction patterns work correctly.
        """
        print("\n" + "="*60)
        print("COORDINATE EXTRACTION PATTERN TESTING")
        print("="*60)
        
        test_cases = [
            # Current YelpMCP format
            ("- **Coordinates**: 37.796996, -122.398661", (37.796996, -122.398661)),
            
            # Alternative formats that might be produced
            ("**Coordinates**: 37.796996, -122.398661", (37.796996, -122.398661)),
            ("- Coordinates: 37.796996, -122.398661", (37.796996, -122.398661)),
            ("Coordinates: 37.796996, -122.398661", (37.796996, -122.398661)),
            ("- **Location**: 37.796996, -122.398661", (37.796996, -122.398661)),
            ("Lat: 37.796996, Lng: -122.398661", (37.796996, -122.398661)),
            ("Latitude: 37.796996, Longitude: -122.398661", (37.796996, -122.398661)),
            
            # Edge cases
            ("- **Coordinates**: 37.7969, -122.3986", (37.7969, -122.3986)),  # Fewer decimals
            ("- **Coordinates**: 37, -122", (37.0, -122.0)),  # Integer coordinates
        ]
        
        # Test patterns used in result_mixer.py
        patterns = [
            re.compile(r"- \*\*Coordinates\*\*: ([\d.-]+), ([\d.-]+)", re.IGNORECASE),
            re.compile(r"\*\*Coordinates\*\*: ([\d.-]+), ([\d.-]+)", re.IGNORECASE),
            re.compile(r"- Coordinates: ([\d.-]+), ([\d.-]+)", re.IGNORECASE),
            re.compile(r"Coordinates: ([\d.-]+), ([\d.-]+)", re.IGNORECASE),
            re.compile(r"- \*\*Location\*\*: ([\d.-]+), ([\d.-]+)", re.IGNORECASE),
            re.compile(r"Lat: ([\d.-]+), Lng: ([\d.-]+)", re.IGNORECASE),
        ]
        
        for i, (text, expected) in enumerate(test_cases):
            print(f"\nTest case {i+1}: {text}")
            
            found = False
            for j, pattern in enumerate(patterns):
                match = pattern.search(text)
                if match:
                    lat, lng = float(match.group(1)), float(match.group(2))
                    print(f"  ✅ Pattern {j+1} matched: ({lat}, {lng})")
                    
                    if abs(lat - expected[0]) < 0.0001 and abs(lng - expected[1]) < 0.0001:
                        print(f"     ✅ Coordinates correct")
                    else:
                        print(f"     ❌ Coordinates incorrect: expected {expected}")
                    
                    found = True
                    break
            
            if not found:
                print(f"  ❌ No pattern matched - coordinates not extracted")
        
        print("="*60)

    def test_frontend_marker_validation(self):
        """
        **DIAGNOSTIC TEST: Frontend marker validation logic**
        
        Tests the frontend marker validation logic to ensure it correctly
        identifies valid vs invalid marker data.
        """
        print("\n" + "="*60)
        print("FRONTEND MARKER VALIDATION TESTING")
        print("="*60)
        
        test_markers = [
            # Valid markers
            ({"lat": 37.7749, "lng": -122.4194, "title": "San Francisco"}, True, "Valid marker with all fields"),
            ({"lat": 37.7749, "lng": -122.4194}, True, "Valid marker without title"),
            ({"lat": 37, "lng": -122, "title": "Test"}, True, "Valid marker with integer coordinates"),
            
            # Invalid markers
            ({"lat": "37.7749", "lng": -122.4194, "title": "Test"}, False, "String latitude"),
            ({"lat": 37.7749, "lng": "-122.4194", "title": "Test"}, False, "String longitude"),
            ({"lng": -122.4194, "title": "Test"}, False, "Missing latitude"),
            ({"lat": 37.7749, "title": "Test"}, False, "Missing longitude"),
            ({"lat": None, "lng": -122.4194, "title": "Test"}, False, "Null latitude"),
            ({"lat": 37.7749, "lng": None, "title": "Test"}, False, "Null longitude"),
            ({"address": "123 Main St", "title": "Test"}, True, "Address-only marker (should be valid for geocoding)"),
            ({}, False, "Empty marker"),
        ]
        
        def validate_marker_frontend_style(marker):
            """Simulate frontend marker validation logic."""
            # Check for lat/lng coordinates
            has_lat_lng = (
                "lat" in marker and 
                "lng" in marker and 
                marker.get("lat") is not None and 
                marker.get("lng") is not None and
                isinstance(marker.get("lat"), (int, float)) and
                isinstance(marker.get("lng"), (int, float))
            )
            
            # Check for address (fallback for geocoding)
            has_address = (
                isinstance(marker.get("address"), str) and 
                marker.get("address").strip()
            )
            
            return has_lat_lng or has_address
        
        for i, (marker, expected_valid, description) in enumerate(test_markers):
            print(f"\nTest {i+1}: {description}")
            print(f"  Marker: {marker}")
            
            is_valid = validate_marker_frontend_style(marker)
            
            if is_valid == expected_valid:
                print(f"  ✅ Validation correct: {'Valid' if is_valid else 'Invalid'}")
            else:
                print(f"  ❌ Validation incorrect: Expected {'Valid' if expected_valid else 'Invalid'}, got {'Valid' if is_valid else 'Invalid'}")
        
        print("="*60)

    def test_json_block_preservation_patterns(self):
        """
        **DIAGNOSTIC TEST: JSON block preservation in result mixer**
        
        Tests the JSON block extraction and preservation logic to ensure
        interactive map JSON blocks are correctly identified and preserved.
        """
        print("\n" + "="*60)
        print("JSON BLOCK PRESERVATION TESTING")
        print("="*60)
        
        # Create test content with various JSON block formats
        test_cases = [
            # Standard format
            '''Here are the restaurants:

```json
{
  "type": "interactive_map",
  "config": {
    "map_type": "places",
    "markers": [
      {"lat": 37.7749, "lng": -122.4194, "title": "Restaurant 1"}
    ]
  }
}
```

That's the map.''',
            
            # Different spacing
            '''```json
{"type": "interactive_map", "config": {"map_type": "places", "markers": [{"lat": 37.7749, "lng": -122.4194, "title": "Restaurant 1"}]}}
```''',
            
            # Case variations
            '''```JSON
{
  "type": "interactive_map",
  "config": {
    "map_type": "places"
  }
}
```''',
        ]
        
        # Test the extraction function from result_mixer.py
        from asdrp.orchestration.moe.result_mixer import WeightedMixer
        from asdrp.orchestration.moe.config_loader import MoEConfig, ModelConfig, ExpertGroupConfig, MoECacheConfig
        
        config = MoEConfig(
            enabled=True,
            moe={},
            models={"mixing": ModelConfig(name="gpt-4.1-mini", temperature=0.7, max_tokens=1000)},
            experts={"test": ExpertGroupConfig(agents=["test"], capabilities=["test"], weight=1.0)},
            cache=MoECacheConfig(enabled=False, type="none", storage={"backend": "none"}, policy={}),
            error_handling={},
            tracing={"enabled": False, "storage": {"backend": "none"}, "exporters": []}
        )
        
        mixer = WeightedMixer(config)
        
        for i, test_content in enumerate(test_cases):
            print(f"\nTest case {i+1}:")
            print(f"Content preview: {test_content[:100]}...")
            
            # Extract JSON blocks
            extracted_blocks = mixer._extract_interactive_json_blocks(test_content)
            
            print(f"  Extracted blocks: {len(extracted_blocks)}")
            
            for j, block in enumerate(extracted_blocks):
                print(f"  Block {j+1}: {block[:100]}...")
                
                # Verify it's valid JSON
                try:
                    import json
                    json_match = re.search(r"```json\s*(.*?)\s*```", block, re.DOTALL | re.IGNORECASE)
                    if json_match:
                        parsed = json.loads(json_match.group(1))
                        print(f"    ✅ Valid JSON with type: {parsed.get('type')}")
                        
                        if parsed.get("type") == "interactive_map":
                            markers = parsed.get("config", {}).get("markers", [])
                            print(f"    ✅ Interactive map with {len(markers)} markers")
                        else:
                            print(f"    ❌ Not an interactive map")
                    else:
                        print(f"    ❌ No JSON content found in block")
                except json.JSONDecodeError as e:
                    print(f"    ❌ Invalid JSON: {e}")
        
        print("="*60)


if __name__ == "__main__":
    # Run diagnostic tests
    test = TestMissingPinsDiagnosis()
    
    print("Running Missing Pins Diagnostic Tests...")
    
    # Run individual diagnostic tests
    test.test_coordinate_extraction_patterns()
    test.test_frontend_marker_validation()
    test.test_json_block_preservation_patterns()
    
    print("\nDiagnostic tests completed. Run with pytest for full end-to-end test.")