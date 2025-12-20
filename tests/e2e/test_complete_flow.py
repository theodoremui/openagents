#!/usr/bin/env python3
"""
Complete end-to-end test of the missing pins issue.

This simulates the exact MoE flow to identify where pins are lost.
"""

import json
import re
from typing import List, Dict, Any


class MockExpertResult:
    """Mock expert result for testing."""
    def __init__(self, expert_id: str, output: str, success: bool = True):
        self.expert_id = expert_id
        self.output = output
        self.success = success


def simulate_complete_moe_flow():
    """Simulate the complete MoE flow with realistic data."""
    
    print("🔍 COMPLETE MOE FLOW SIMULATION")
    print("=" * 80)
    
    query = "Place the top 3 greek restaurants in San Francisco as pins on a detailed map"
    print(f"Query: {query}\n")
    
    # Step 1: Agent Selection (we know this works)
    print("STEP 1: Agent Selection")
    print("-" * 40)
    selected_agents = ["yelp_mcp", "yelp", "map"]
    print(f"Selected agents: {selected_agents}")
    print("✅ Map agent correctly selected\n")
    
    # Step 2: Expert Execution (simulate realistic outputs)
    print("STEP 2: Expert Execution")
    print("-" * 40)
    
    # YelpMCP output (realistic format from formatters.py)
    yelp_mcp_output = """# Formatted Business Data for LLM Processing

## Introduction
Here are some great Greek restaurants in San Francisco based on your query.

## Chat ID
abc123

## Business 1: Kokkari Estiatorio
- **Price**: $$$$
- **Rating**: 4.5/5 (1234 reviews)
- **Type**: Greek, Seafood
- **Location**: 200 Jackson St, San Francisco, CA 94111
- **Coordinates**: 37.796996, -122.398661
- **URL**: [View on Yelp](https://www.yelp.com/biz/kokkari-estiatorio-san-francisco)
- **Phone**: (415) 981-0983

## Business 2: Milos Mezes
- **Price**: $$$
- **Rating**: 4.0/5 (567 reviews)
- **Type**: Greek, Mediterranean
- **Location**: 3348 Steiner St, San Francisco, CA 94123
- **Coordinates**: 37.800333, -122.423670
- **URL**: [View on Yelp](https://www.yelp.com/biz/milos-mezes-san-francisco)
- **Phone**: (415) 563-8368

## Business 3: Souvla
- **Price**: $$
- **Rating**: 4.2/5 (890 reviews)
- **Type**: Greek, Fast Food
- **Location**: 517 Hayes St, San Francisco, CA 94102
- **Coordinates**: 37.776685, -122.423943
- **URL**: [View on Yelp](https://www.yelp.com/biz/souvla-san-francisco)
- **Phone**: (415) 400-4500"""
    
    # Yelp output (fallback, similar but different format)
    yelp_output = """Found 3 great Greek restaurants in San Francisco:

1. **Kokkari Estiatorio** - 4.5/5 stars
   Address: 200 Jackson St, San Francisco, CA 94111
   Phone: (415) 981-0983
   
2. **Milos Mezes** - 4.0/5 stars
   Address: 3348 Steiner St, San Francisco, CA 94123
   Phone: (415) 563-8368
   
3. **Souvla** - 4.2/5 stars
   Address: 517 Hayes St, San Francisco, CA 94102
   Phone: (415) 400-4500"""
    
    # MapAgent output (what it SHOULD produce if given coordinates)
    map_output = """I'll create an interactive map showing these Greek restaurants in San Francisco.

```json
{
  "type": "interactive_map",
  "config": {
    "map_type": "places",
    "center_lat": 37.791338,
    "center_lng": -122.415425,
    "zoom": 13,
    "markers": [
      {
        "lat": 37.796996,
        "lng": -122.398661,
        "title": "Kokkari Estiatorio"
      },
      {
        "lat": 37.800333,
        "lng": -122.423670,
        "title": "Milos Mezes"
      },
      {
        "lat": 37.776685,
        "lng": -122.423943,
        "title": "Souvla"
      }
    ]
  }
}
```

The map shows all three restaurants with their exact locations in San Francisco."""
    
    expert_results = [
        MockExpertResult("yelp_mcp", yelp_mcp_output, True),
        MockExpertResult("yelp", yelp_output, True),
        MockExpertResult("map", map_output, True)  # This might not happen in reality
    ]
    
    print(f"YelpMCP output length: {len(yelp_mcp_output)} chars")
    print(f"Yelp output length: {len(yelp_output)} chars") 
    print(f"Map output length: {len(map_output)} chars")
    print(f"Map output contains JSON: {'```json' in map_output}\n")
    
    # Step 3: LLM Synthesis (simulate what actually happens)
    print("STEP 3: LLM Synthesis")
    print("-" * 40)
    
    # This is what the LLM typically produces - it summarizes but drops JSON
    synthesized_response = """Here are the top 3 Greek restaurants in San Francisco:

**1. Kokkari Estiatorio** - 4.5/5 stars
Located at 200 Jackson St, this upscale Greek restaurant specializes in seafood and lamb dishes. Known for excellent service and authentic Greek flavors.
Phone: (415) 981-0983
[View on Yelp](https://www.yelp.com/biz/kokkari-estiatorio-san-francisco)

**2. Milos Mezes** - 4.0/5 stars  
Found at 3348 Steiner St, offering traditional Greek mezze and grilled octopus. Great for sharing plates and casual dining.
Phone: (415) 563-8368
[View on Yelp](https://www.yelp.com/biz/milos-mezes-san-francisco)

**3. Souvla** - 4.2/5 stars
At 517 Hayes St, serving Greek street food including souvlaki and Greek salads. More casual and affordable option.
Phone: (415) 400-4500
[View on Yelp](https://www.yelp.com/biz/souvla-san-francisco)

These restaurants are located across different neighborhoods in San Francisco and offer various price points from casual to upscale dining."""
    
    print(f"Synthesized response length: {len(synthesized_response)} chars")
    print(f"Contains JSON blocks: {'```json' in synthesized_response}")
    print("❌ LLM synthesis dropped the JSON block (common issue)\n")
    
    # Step 4: JSON Block Preservation (should restore missing JSON)
    print("STEP 4: JSON Block Preservation")
    print("-" * 40)
    
    # Extract JSON blocks from expert outputs
    json_blocks = []
    for result in expert_results:
        blocks = extract_json_blocks(result.output)
        json_blocks.extend(blocks)
    
    print(f"JSON blocks found in expert outputs: {len(json_blocks)}")
    
    # Check if synthesized has JSON
    synthesized_blocks = extract_json_blocks(synthesized_response)
    print(f"JSON blocks in synthesized response: {len(synthesized_blocks)}")
    
    # Apply preservation
    if json_blocks and not synthesized_blocks:
        preserved_response = synthesized_response
        for block in json_blocks:
            preserved_response = f"{preserved_response.rstrip()}\n\nInteractive map:\n\n{block}\n"
        print("✅ JSON blocks restored via preservation mechanism")
    else:
        preserved_response = synthesized_response
        print("⚠️  No JSON restoration needed or possible")
    
    print(f"Final response length: {len(preserved_response)} chars")
    print(f"Final response contains JSON: {'```json' in preserved_response}\n")
    
    # Step 5: Auto-Injection (fallback mechanism)
    print("STEP 5: Auto-Injection Mechanism")
    print("-" * 40)
    
    final_response = simulate_auto_injection(preserved_response, query, expert_results)
    
    # Step 6: Frontend Detection
    print("STEP 6: Frontend Map Detection")
    print("-" * 40)
    
    detected_maps = simulate_frontend_detection(final_response)
    
    # Final Analysis
    print("FINAL ANALYSIS")
    print("-" * 40)
    
    if detected_maps and any(len(m["valid_markers"]) > 0 for m in detected_maps):
        total_markers = sum(len(m["valid_markers"]) for m in detected_maps)
        print(f"✅ SUCCESS: {total_markers} valid markers detected")
        print("   - Pins should render correctly on the map")
    else:
        print("❌ FAILURE: No valid markers detected")
        print("   - This explains the missing pins issue")
        
        # Diagnose the failure
        if not detected_maps:
            print("   - Root cause: No interactive maps detected")
        else:
            print("   - Root cause: Invalid marker data")
    
    return final_response


def extract_json_blocks(text: str) -> List[str]:
    """Extract interactive map JSON blocks."""
    pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
    blocks = []
    
    for match in pattern.finditer(text):
        json_content = match.group(1).strip()
        try:
            parsed = json.loads(json_content)
            if parsed.get("type") == "interactive_map":
                full_block = f"```json\n{json_content}\n```"
                blocks.append(full_block)
        except json.JSONDecodeError:
            continue
    
    return blocks


def simulate_auto_injection(synthesized: str, query: str, expert_results: List[MockExpertResult]) -> str:
    """Simulate the auto-injection mechanism from result_mixer.py."""
    
    print("Testing auto-injection conditions:")
    
    q = query.lower()
    
    # Check conditions
    has_map_intent = "map" in q or "maps" in q
    has_existing_json = "```json" in synthesized and "interactive_map" in synthesized
    has_places_intent = any(w in q for w in ("restaurant", "restaurants", "food", "cafe", "cafes", "bar", "bars", "where"))
    
    print(f"  - Map intent ('map' in query): {has_map_intent}")
    print(f"  - Existing JSON in response: {has_existing_json}")
    print(f"  - Places intent (restaurants, etc.): {has_places_intent}")
    
    if not has_map_intent:
        print("  ❌ No map intent - auto-injection skipped")
        return synthesized
    
    if has_existing_json:
        print("  ❌ JSON already exists - auto-injection skipped")
        return synthesized
    
    if not has_places_intent:
        print("  ❌ No places intent - auto-injection skipped")
        return synthesized
    
    print("  ✅ All conditions met - attempting coordinate extraction")
    
    # Extract coordinates using the same patterns as result_mixer.py
    business_header_re = re.compile(
        r"(?:^\s*##\s*Business\s*\d+\s*:\s*(.+?)\s*$|^\s*\d+\.\s*\*\*(.+?)\*\*)",
        re.IGNORECASE | re.MULTILINE
    )
    coord_line_re = re.compile(
        r"^\s*(?:-\s*)?(?:\*\*)?(Coordinates|Location|Lat|Position)(?:\*\*)?:\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*$",
        re.IGNORECASE | re.MULTILINE
    )
    
    markers = []
    
    for result in expert_results:
        if not result.success:
            continue
            
        text = result.output
        
        # Extract business names and coordinates
        headers_raw = business_header_re.findall(text)
        coords_raw = coord_line_re.findall(text)
        
        headers = []
        for h in headers_raw:
            if isinstance(h, tuple):
                name = h[0] or h[1] if len(h) >= 2 else h[0]
            else:
                name = h
            if name:
                headers.append(name.strip())
        
        coords = [(lat_s, lng_s) for (_, lat_s, lng_s) in coords_raw]
        
        print(f"  - {result.expert_id}: {len(headers)} names, {len(coords)} coordinates")
        
        if headers and coords and len(headers) == len(coords):
            for name, (lat_s, lng_s) in zip(headers, coords):
                try:
                    lat = float(lat_s)
                    lng = float(lng_s)
                    markers.append({"lat": lat, "lng": lng, "title": name[:80]})
                    print(f"    ✅ {name} → ({lat}, {lng})")
                except Exception as e:
                    print(f"    ❌ {name} → Failed: {e}")
    
    if len(markers) < 1:
        print(f"  ❌ Insufficient markers ({len(markers)}) - auto-injection failed")
        return synthesized
    
    print(f"  ✅ Creating map with {len(markers)} markers")
    
    # Generate map JSON (simulate MapTools.get_interactive_map_data)
    center_lat = sum(m["lat"] for m in markers) / len(markers)
    center_lng = sum(m["lng"] for m in markers) / len(markers)
    
    map_config = {
        "type": "interactive_map",
        "config": {
            "map_type": "places",
            "center_lat": center_lat,
            "center_lng": center_lng,
            "zoom": 15 if len(markers) == 1 else 13,
            "markers": markers
        }
    }
    
    json_str = json.dumps(map_config, indent=2)
    map_block = f"```json\n{json_str}\n```"
    
    result = f"{synthesized.rstrip()}\n\nInteractive map:\n\n{map_block}\n"
    
    print("  ✅ Auto-injection successful")
    return result


def simulate_frontend_detection(content: str) -> List[Dict[str, Any]]:
    """Simulate frontend map detection."""
    
    json_blocks = extract_json_blocks(content)
    print(f"Frontend detected {len(json_blocks)} JSON blocks")
    
    detected_maps = []
    
    for i, block in enumerate(json_blocks):
        json_match = re.search(r"```json\s*(.*?)\s*```", block, re.DOTALL | re.IGNORECASE)
        if not json_match:
            continue
        
        try:
            map_data = json.loads(json_match.group(1))
            
            if map_data.get("type") != "interactive_map":
                continue
            
            config = map_data.get("config", {})
            markers = config.get("markers", [])
            
            # Validate markers (frontend logic)
            valid_markers = []
            for marker in markers:
                lat = marker.get("lat")
                lng = marker.get("lng")
                
                if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                    valid_markers.append(marker)
                    print(f"  ✅ Valid marker: {marker.get('title', 'Unnamed')} at ({lat}, {lng})")
                else:
                    print(f"  ❌ Invalid marker: lat={type(lat).__name__}, lng={type(lng).__name__}")
            
            detected_maps.append({
                "config": config,
                "valid_markers": valid_markers,
                "total_markers": len(markers)
            })
            
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON parsing error: {e}")
    
    return detected_maps


if __name__ == "__main__":
    simulate_complete_moe_flow()