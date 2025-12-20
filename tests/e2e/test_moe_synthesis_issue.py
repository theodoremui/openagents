#!/usr/bin/env python3
"""
Test MoE Synthesis Issue

The Map agent returns perfect coordinate data, but it's getting lost.
This script tests the MoE synthesis process to see where coordinates disappear.
"""

import asyncio
import json
import re
from pathlib import Path
import sys

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator

async def test_moe_synthesis():
    print("🔍 TESTING MoE SYNTHESIS ISSUE")
    print("=" * 80)
    
    query = "Place the top 3 greek restaurants in San Francisco as pins on a detailed map"
    
    # Initialize system
    factory = AgentFactory.instance()
    config = MoEConfigLoader().load_config()
    orchestrator = MoEOrchestrator.create_default(factory, config)
    
    print(f"Query: {query}\n")
    
    # Execute with detailed tracing
    result = await orchestrator.route_query(query, session_id="synthesis_test")
    
    print("📊 DETAILED EXPERT ANALYSIS")
    print("-" * 80)
    
    if hasattr(result.trace, 'expert_details') and result.trace.expert_details:
        for detail in result.trace.expert_details:
            print(f"\n🔬 Expert: {detail.expert_id}")
            print(f"Status: {detail.status}")
            
            if detail.error:
                print(f"❌ Error: {detail.error}")
            
            if detail.response:
                response = detail.response
                print(f"✅ Response length: {len(response)} chars")
                
                # Check for coordinates in expert response
                coord_matches = re.findall(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', response)
                if coord_matches:
                    print(f"✅ Expert has coordinates: {coord_matches}")
                else:
                    print(f"❌ Expert has NO coordinates")
                
                # Check for JSON blocks in expert response
                json_blocks = re.findall(r"```json\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE)
                if json_blocks:
                    print(f"✅ Expert has {len(json_blocks)} JSON block(s)")
                    for i, json_str in enumerate(json_blocks):
                        try:
                            json_obj = json.loads(json_str.strip())
                            if json_obj.get('type') == 'interactive_map':
                                config_obj = json_obj.get('config', {})
                                markers = config_obj.get('markers', [])
                                print(f"  JSON {i+1}: {len(markers)} markers")
                                if markers:
                                    first = markers[0]
                                    print(f"    First marker: lat={first.get('lat')}, lng={first.get('lng')}")
                        except:
                            print(f"  JSON {i+1}: Invalid")
                else:
                    print(f"❌ Expert has NO JSON blocks")
                
                # Show first 200 chars of response
                print(f"Preview: {response[:200]}...")
    
    print(f"\n\n📄 FINAL SYNTHESIS RESULT")
    print("-" * 80)
    
    print(f"Final response length: {len(result.response)} chars")
    print(f"Experts used: {result.experts_used}")
    
    # Check final response for coordinates
    final_coord_matches = re.findall(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', result.response)
    if final_coord_matches:
        print(f"✅ Final response has coordinates: {final_coord_matches}")
    else:
        print(f"❌ Final response has NO coordinates")
    
    # Check final response for JSON blocks
    final_json_blocks = re.findall(r"```json\s*(.*?)\s*```", result.response, re.DOTALL | re.IGNORECASE)
    if final_json_blocks:
        print(f"✅ Final response has {len(final_json_blocks)} JSON block(s)")
        for i, json_str in enumerate(final_json_blocks):
            try:
                json_obj = json.loads(json_str.strip())
                if json_obj.get('type') == 'interactive_map':
                    config_obj = json_obj.get('config', {})
                    markers = config_obj.get('markers', [])
                    print(f"  Final JSON {i+1}: {len(markers)} markers")
                    if markers:
                        first = markers[0]
                        print(f"    First marker: lat={first.get('lat')}, lng={first.get('lng')}")
                        print(f"    First marker address: {first.get('address')}")
            except Exception as e:
                print(f"  Final JSON {i+1}: Invalid - {e}")
    else:
        print(f"❌ Final response has NO JSON blocks")
    
    print(f"\nFinal response preview:")
    print("-" * 40)
    print(result.response[:400])
    print("-" * 40)
    
    print(f"\n\n🎯 SYNTHESIS ANALYSIS")
    print("-" * 80)
    
    # Determine what happened during synthesis
    map_expert_had_coords = False
    map_expert_had_json = False
    
    if hasattr(result.trace, 'expert_details') and result.trace.expert_details:
        for detail in result.trace.expert_details:
            if detail.expert_id == "map" and detail.response:
                coord_matches = re.findall(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', detail.response)
                json_blocks = re.findall(r"```json\s*(.*?)\s*```", detail.response, re.DOTALL | re.IGNORECASE)
                
                if coord_matches:
                    map_expert_had_coords = True
                    print(f"✅ Map expert provided coordinates: {len(coord_matches)} pairs")
                
                if json_blocks:
                    map_expert_had_json = True
                    print(f"✅ Map expert provided JSON: {len(json_blocks)} blocks")
    
    final_has_coords = len(final_coord_matches) > 0
    final_has_json = len(final_json_blocks) > 0
    
    if map_expert_had_coords and not final_has_coords:
        print(f"❌ COORDINATES LOST during synthesis!")
        print(f"   → Map expert had coordinates but final response doesn't")
    
    if map_expert_had_json and not final_has_json:
        print(f"❌ JSON BLOCKS LOST during synthesis!")
        print(f"   → Map expert had JSON but final response doesn't")
    
    if map_expert_had_json and final_has_json:
        print(f"✅ JSON blocks preserved during synthesis")
        
        # But check if coordinates within JSON were lost
        map_json_had_coords = False
        final_json_has_coords = False
        
        if hasattr(result.trace, 'expert_details') and result.trace.expert_details:
            for detail in result.trace.expert_details:
                if detail.expert_id == "map" and detail.response:
                    json_blocks = re.findall(r"```json\s*(.*?)\s*```", detail.response, re.DOTALL | re.IGNORECASE)
                    for json_str in json_blocks:
                        try:
                            json_obj = json.loads(json_str.strip())
                            if json_obj.get('type') == 'interactive_map':
                                markers = json_obj.get('config', {}).get('markers', [])
                                if markers and any(m.get('lat') is not None for m in markers):
                                    map_json_had_coords = True
                        except:
                            pass
        
        for json_str in final_json_blocks:
            try:
                json_obj = json.loads(json_str.strip())
                if json_obj.get('type') == 'interactive_map':
                    markers = json_obj.get('config', {}).get('markers', [])
                    if markers and any(m.get('lat') is not None for m in markers):
                        final_json_has_coords = True
            except:
                pass
        
        if map_json_had_coords and not final_json_has_coords:
            print(f"❌ COORDINATES LOST from JSON during synthesis!")
            print(f"   → Map expert JSON had coordinates but final JSON doesn't")
        elif map_json_had_coords and final_json_has_coords:
            print(f"✅ Coordinates preserved in JSON during synthesis")
        else:
            print(f"⚠️  Map expert JSON may not have had coordinates to begin with")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"1. Check if Map expert is actually being selected and executed")
    print(f"2. Verify JSON block preservation in result mixer")
    print(f"3. Check if LLM synthesis is modifying JSON content")
    print(f"4. Test auto-injection fallback mechanisms")

if __name__ == "__main__":
    asyncio.run(test_moe_synthesis())