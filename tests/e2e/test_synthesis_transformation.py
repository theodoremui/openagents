#!/usr/bin/env python3
"""
Test Synthesis Transformation

Compare the Map agent's individual output vs what comes out of MoE synthesis
to see exactly where the JSON format gets corrupted.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator

async def test_synthesis_transformation():
    print("🔄 SYNTHESIS TRANSFORMATION TEST")
    print("=" * 80)
    
    query = "Place the top 3 greek restaurants in San Francisco as pins on a detailed map"
    
    # Initialize MoE
    factory = AgentFactory.instance()
    config = MoEConfigLoader().load_config()
    orchestrator = MoEOrchestrator.create_default(factory, config)
    
    # Execute MoE
    result = await orchestrator.route_query(query, session_id="synthesis_test")
    
    print(f"Query: {query}")
    print(f"Experts used: {result.experts_used}")
    
    # Check expert outputs from trace
    if hasattr(result.trace, 'expert_details') and result.trace.expert_details:
        print(f"\n📊 EXPERT OUTPUTS:")
        print("-" * 60)
        
        for detail in result.trace.expert_details:
            print(f"\n🔬 Expert: {detail.expert_id}")
            print(f"Status: {detail.status}")
            
            if detail.response:
                response = detail.response
                print(f"Response length: {len(response)} chars")
                
                # Extract JSON from expert response
                expert_json_blocks = re.findall(r"```json\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE)
                
                if expert_json_blocks:
                    print(f"✅ Expert has {len(expert_json_blocks)} JSON block(s)")
                    
                    for i, json_str in enumerate(expert_json_blocks):
                        try:
                            json_obj = json.loads(json_str.strip())
                            if json_obj.get('type') == 'interactive_map':
                                print(f"  JSON {i+1}: interactive_map")
                                
                                # Check structure
                                if 'config' in json_obj:
                                    config_obj = json_obj['config']
                                    markers = config_obj.get('markers', [])
                                    print(f"    ✅ Correct format: config.markers with {len(markers)} items")
                                    
                                    if markers:
                                        first = markers[0]
                                        print(f"    First marker: lat={first.get('lat')}, lng={first.get('lng')}, title='{first.get('title')}'")
                                
                                elif 'locations' in json_obj:
                                    locations = json_obj['locations']
                                    print(f"    ❌ Wrong format: locations array with {len(locations)} items")
                                
                                else:
                                    print(f"    ❌ Unknown format: {list(json_obj.keys())}")
                        
                        except json.JSONDecodeError:
                            print(f"  JSON {i+1}: Invalid JSON")
                else:
                    print(f"❌ Expert has no JSON blocks")
            else:
                print(f"❌ Expert has no response")
    
    # Check final MoE output
    print(f"\n📄 FINAL MoE OUTPUT:")
    print("-" * 60)
    
    final_json_blocks = re.findall(r"```json\s*(.*?)\s*```", result.response, re.DOTALL | re.IGNORECASE)
    
    if final_json_blocks:
        print(f"✅ Final has {len(final_json_blocks)} JSON block(s)")
        
        for i, json_str in enumerate(final_json_blocks):
            try:
                json_obj = json.loads(json_str.strip())
                if json_obj.get('type') == 'interactive_map':
                    print(f"  JSON {i+1}: interactive_map")
                    
                    # Check structure
                    if 'config' in json_obj:
                        config_obj = json_obj['config']
                        markers = config_obj.get('markers', [])
                        print(f"    ✅ Correct format: config.markers with {len(markers)} items")
                        
                        if markers:
                            first = markers[0]
                            print(f"    First marker: lat={first.get('lat')}, lng={first.get('lng')}, title='{first.get('title')}'")
                    
                    elif 'locations' in json_obj:
                        locations = json_obj['locations']
                        print(f"    ❌ Wrong format: locations array with {len(locations)} items")
                        
                        if locations:
                            first = locations[0]
                            print(f"    First location keys: {list(first.keys())}")
                            if 'coordinates' in first:
                                coords = first['coordinates']
                                print(f"    Nested coordinates: {coords}")
                    
                    else:
                        print(f"    ❌ Unknown format: {list(json_obj.keys())}")
            
            except json.JSONDecodeError as e:
                print(f"  JSON {i+1}: Invalid JSON - {e}")
    else:
        print(f"❌ Final has no JSON blocks")
    
    # Comparison
    print(f"\n🎯 TRANSFORMATION ANALYSIS:")
    print("-" * 60)
    
    # Check if Map agent provided correct format
    map_expert_correct = False
    final_correct = False
    
    if hasattr(result.trace, 'expert_details') and result.trace.expert_details:
        for detail in result.trace.expert_details:
            if detail.expert_id == "map" and detail.response:
                expert_json_blocks = re.findall(r"```json\s*(.*?)\s*```", detail.response, re.DOTALL | re.IGNORECASE)
                for json_str in expert_json_blocks:
                    try:
                        json_obj = json.loads(json_str.strip())
                        if json_obj.get('type') == 'interactive_map' and 'config' in json_obj:
                            map_expert_correct = True
                            break
                    except:
                        pass
    
    # Check if final output has correct format
    for json_str in final_json_blocks:
        try:
            json_obj = json.loads(json_str.strip())
            if json_obj.get('type') == 'interactive_map' and 'config' in json_obj:
                final_correct = True
                break
        except:
            pass
    
    print(f"Map expert provides correct format: {map_expert_correct}")
    print(f"Final output has correct format: {final_correct}")
    
    if map_expert_correct and not final_correct:
        print("❌ SYNTHESIS CORRUPTED THE JSON FORMAT!")
        print("   → Map agent provides correct format but synthesis changes it")
        print("   → Issue is in the LLM synthesis step")
    elif map_expert_correct and final_correct:
        print("✅ JSON format preserved through synthesis")
    elif not map_expert_correct:
        print("❌ Map agent provides wrong format")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_synthesis_transformation())