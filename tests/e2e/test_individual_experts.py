#!/usr/bin/env python3
"""
Test Individual Expert Outputs

This script tests each expert individually to see what data they return
for the Greek restaurants query.
"""

import asyncio
import json
import re
from pathlib import Path
import sys

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from agents import Runner

async def test_individual_experts():
    print("🧪 TESTING INDIVIDUAL EXPERT OUTPUTS")
    print("=" * 80)
    
    query = "Find the top 3 greek restaurants in San Francisco with their addresses and coordinates"
    
    factory = AgentFactory.instance()
    session_id = "expert_test"
    
    experts_to_test = ["yelp_mcp", "yelp", "map"]
    
    for expert_id in experts_to_test:
        print(f"\n🔬 TESTING EXPERT: {expert_id}")
        print("-" * 60)
        
        try:
            # Get agent
            agent, session = await factory.get_agent_with_persistent_session(expert_id, session_id)
            print(f"✅ Agent loaded: {type(agent).__name__}")
            
            # Execute query
            print(f"Query: {query}")
            result = await Runner.run(
                starting_agent=agent,
                input=query,
                session=session,
                max_turns=10
            )
            
            output = str(result.final_output) if result.final_output else ""
            print(f"\nOutput length: {len(output)} characters")
            
            if output:
                print(f"\nOutput preview:")
                print("-" * 40)
                print(output[:500] + ("..." if len(output) > 500 else ""))
                print("-" * 40)
                
                # Analyze output for coordinates
                coord_patterns = [
                    (r'"lat":\s*([\d.-]+)', "JSON lat field"),
                    (r'"lng":\s*([\d.-]+)', "JSON lng field"),
                    (r'"latitude":\s*([\d.-]+)', "JSON latitude field"),
                    (r'"longitude":\s*([\d.-]+)', "JSON longitude field"),
                    (r'Coordinates:\s*([\d.-]+),\s*([\d.-]+)', "Coordinates: format"),
                    (r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', "Decimal coordinates"),
                ]
                
                found_coords = False
                for pattern, desc in coord_patterns:
                    matches = re.findall(pattern, output)
                    if matches:
                        print(f"  ✅ Found {desc}: {matches[:3]}")
                        found_coords = True
                
                if not found_coords:
                    print(f"  ❌ NO COORDINATES found in output")
                
                # Check for addresses
                address_indicators = ["st", "ave", "blvd", "rd", "street", "avenue"]
                if any(indicator in output.lower() for indicator in address_indicators):
                    print(f"  ✅ Contains address data")
                    
                    # Extract address lines
                    lines = output.split('\n')
                    address_lines = []
                    for line in lines:
                        if any(indicator in line.lower() for indicator in address_indicators):
                            address_lines.append(line.strip())
                    
                    if address_lines:
                        print(f"  Sample addresses:")
                        for addr in address_lines[:3]:
                            print(f"    - {addr}")
                else:
                    print(f"  ❌ NO ADDRESS data found")
                
                # Check for JSON blocks
                json_blocks = re.findall(r"```json\s*(.*?)\s*```", output, re.DOTALL | re.IGNORECASE)
                if json_blocks:
                    print(f"  ✅ Contains {len(json_blocks)} JSON block(s)")
                    for i, json_str in enumerate(json_blocks):
                        try:
                            json_obj = json.loads(json_str.strip())
                            print(f"    JSON {i+1} type: {json_obj.get('type', 'unknown')}")
                            
                            if json_obj.get('type') == 'interactive_map':
                                config = json_obj.get('config', {})
                                markers = config.get('markers', [])
                                print(f"      Map type: {config.get('map_type')}")
                                print(f"      Markers: {len(markers)}")
                                
                                if markers and isinstance(markers, list):
                                    first = markers[0]
                                    print(f"      First marker: lat={first.get('lat')}, lng={first.get('lng')}")
                                    print(f"      First marker address: {first.get('address', 'N/A')}")
                        except json.JSONDecodeError as e:
                            print(f"    JSON {i+1}: Invalid JSON - {e}")
                else:
                    print(f"  ❌ NO JSON blocks found")
                
                # Check for business names
                greek_restaurants = ["souvla", "kokkari", "milos", "greek", "mediterranean"]
                found_restaurants = []
                for restaurant in greek_restaurants:
                    if restaurant in output.lower():
                        found_restaurants.append(restaurant)
                
                if found_restaurants:
                    print(f"  ✅ Found restaurant references: {found_restaurants}")
                else:
                    print(f"  ❌ NO restaurant names found")
            
            else:
                print("❌ No output from expert")
                
        except Exception as e:
            print(f"❌ Expert {expert_id} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n\n🎯 EXPERT ANALYSIS SUMMARY")
    print("=" * 80)
    print("Based on individual expert testing, we can determine:")
    print("1. Which experts return coordinate data")
    print("2. Which experts return address data")
    print("3. Which experts return JSON map blocks")
    print("4. Where the coordinate loss occurs in the pipeline")

if __name__ == "__main__":
    asyncio.run(test_individual_experts())