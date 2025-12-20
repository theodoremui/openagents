#!/usr/bin/env python3
"""
Test Map Agent Output Format

Check exactly what format the Map agent is generating to see why it's wrong.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from agents import Runner

async def test_map_agent_output():
    print("🗺️  TESTING MAP AGENT OUTPUT FORMAT")
    print("=" * 80)
    
    query = "Find the top 3 greek restaurants in San Francisco with addresses and coordinates"
    
    # Get Map agent
    factory = AgentFactory.instance()
    agent, session = await factory.get_agent_with_persistent_session("map", "test_map_output")
    
    print(f"✅ Map agent loaded: {type(agent).__name__}")
    
    # Run the agent
    result = await asyncio.wait_for(
        Runner.run(starting_agent=agent, input=query, session=session, max_turns=10),
        timeout=30.0
    )
    
    output = str(result.final_output) if result.final_output else ""
    
    print(f"📄 Map Agent Output ({len(output)} chars):")
    print("=" * 80)
    print(output)
    print("=" * 80)
    
    # Extract and analyze JSON blocks
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", output, re.DOTALL | re.IGNORECASE)
    
    print(f"\n🔍 JSON ANALYSIS:")
    print(f"Found {len(json_blocks)} JSON blocks")
    
    for i, json_str in enumerate(json_blocks):
        print(f"\n📄 JSON Block {i+1}:")
        print("-" * 40)
        
        try:
            json_obj = json.loads(json_str.strip())
            
            # Pretty print the JSON
            print("Raw JSON:")
            print(json.dumps(json_obj, indent=2))
            
            # Analyze structure
            print(f"\nStructure Analysis:")
            print(f"  Type: {json_obj.get('type')}")
            
            if json_obj.get('type') == 'interactive_map':
                # Check if it has the correct structure
                if 'config' in json_obj:
                    config = json_obj['config']
                    print(f"  ✅ Has 'config' object")
                    print(f"  Map type: {config.get('map_type')}")
                    
                    if 'markers' in config:
                        markers = config['markers']
                        print(f"  ✅ Has 'markers' array with {len(markers)} items")
                        
                        if markers:
                            first_marker = markers[0]
                            print(f"  First marker structure:")
                            for key, value in first_marker.items():
                                print(f"    {key}: {value} ({type(value).__name__})")
                    else:
                        print(f"  ❌ Missing 'markers' array")
                
                elif 'locations' in json_obj:
                    locations = json_obj['locations']
                    print(f"  ❌ Has 'locations' array instead of 'config' (WRONG FORMAT)")
                    print(f"  Number of locations: {len(locations)}")
                    
                    if locations:
                        first_location = locations[0]
                        print(f"  First location structure:")
                        for key, value in first_location.items():
                            if isinstance(value, dict):
                                print(f"    {key}: {value}")
                            else:
                                print(f"    {key}: {value} ({type(value).__name__})")
                
                else:
                    print(f"  ❌ Missing both 'config' and 'locations'")
                    print(f"  Available keys: {list(json_obj.keys())}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            print(f"Raw JSON (first 200 chars):")
            print(json_str[:200])
    
    # Check if the agent is calling the right tools
    print(f"\n🔧 TOOL USAGE ANALYSIS:")
    
    # Look for evidence of MapTools usage
    if "get_interactive_map_data" in output:
        print("✅ Agent mentions get_interactive_map_data")
    else:
        print("❌ Agent doesn't mention get_interactive_map_data")
    
    # Look for coordinates in the output
    coord_matches = re.findall(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output)
    if coord_matches:
        print(f"✅ Found {len(coord_matches)} coordinate pairs:")
        for i, (lat, lng) in enumerate(coord_matches[:3]):
            print(f"  {i+1}: ({lat}, {lng})")
    else:
        print("❌ No coordinate pairs found")
    
    return output

if __name__ == "__main__":
    asyncio.run(test_map_agent_output())