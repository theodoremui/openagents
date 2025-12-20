#!/usr/bin/env python3
"""
Test MoE vs Individual Agent Execution

This script compares the output of agents when run individually vs through MoE
to identify why coordinates are lost in the MoE pipeline.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from contextlib import AsyncExitStack

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from agents import Runner

async def test_individual_vs_moe():
    print("🔬 INDIVIDUAL vs MoE EXECUTION COMPARISON")
    print("=" * 80)
    
    query = "Find the top 3 greek restaurants in San Francisco with addresses and coordinates"
    
    # Test 1: Individual Agent Execution
    print("\n📍 STEP 1: Individual Agent Execution")
    print("-" * 60)
    
    factory = AgentFactory.instance()
    individual_results = {}
    
    # Test YelpMCP individually
    print("Testing YelpMCP individually...")
    try:
        agent, session = await factory.get_agent_with_persistent_session("yelp_mcp", "individual_test")
        mcp_servers = getattr(agent, "mcp_servers", None)
        
        if mcp_servers:
            async with AsyncExitStack() as stack:
                for mcp_server in mcp_servers:
                    await stack.enter_async_context(mcp_server)
                
                result = await asyncio.wait_for(
                    Runner.run(starting_agent=agent, input=query, session=session, max_turns=10),
                    timeout=30.0
                )
                
                output = str(result.final_output) if result.final_output else ""
                individual_results["yelp_mcp"] = output
                
                # Analyze output
                has_coords = bool(re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output))
                has_json = "```json" in output
                
                print(f"  ✅ YelpMCP individual: {len(output)} chars, coords={has_coords}, json={has_json}")
                
                if has_coords:
                    coords = re.findall(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output)
                    print(f"    Coordinates found: {coords[:3]}")
                
                if has_json:
                    json_blocks = re.findall(r"```json\s*(.*?)\s*```", output, re.DOTALL | re.IGNORECASE)
                    print(f"    JSON blocks: {len(json_blocks)}")
                    
                    for i, json_str in enumerate(json_blocks):
                        try:
                            json_obj = json.loads(json_str.strip())
                            if json_obj.get('type') == 'interactive_map':
                                markers = json_obj.get('config', {}).get('markers', [])
                                print(f"      JSON {i+1}: interactive_map with {len(markers)} markers")
                        except:
                            print(f"      JSON {i+1}: invalid")
        
    except Exception as e:
        print(f"  ❌ YelpMCP individual failed: {e}")
        individual_results["yelp_mcp"] = None
    
    # Test Map individually
    print("\nTesting Map individually...")
    try:
        agent, session = await factory.get_agent_with_persistent_session("map", "individual_test")
        
        result = await asyncio.wait_for(
            Runner.run(starting_agent=agent, input=query, session=session, max_turns=10),
            timeout=30.0
        )
        
        output = str(result.final_output) if result.final_output else ""
        individual_results["map"] = output
        
        # Analyze output
        has_coords = bool(re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output))
        has_json = "```json" in output
        
        print(f"  ✅ Map individual: {len(output)} chars, coords={has_coords}, json={has_json}")
        
        if has_coords:
            coords = re.findall(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output)
            print(f"    Coordinates found: {coords[:3]}")
        
        if has_json:
            json_blocks = re.findall(r"```json\s*(.*?)\s*```", output, re.DOTALL | re.IGNORECASE)
            print(f"    JSON blocks: {len(json_blocks)}")
            
            for i, json_str in enumerate(json_blocks):
                try:
                    json_obj = json.loads(json_str.strip())
                    if json_obj.get('type') == 'interactive_map':
                        markers = json_obj.get('config', {}).get('markers', [])
                        print(f"      JSON {i+1}: interactive_map with {len(markers)} markers")
                        if markers:
                            first_marker = markers[0]
                            print(f"        First marker: lat={first_marker.get('lat')}, lng={first_marker.get('lng')}")
                except:
                    print(f"      JSON {i+1}: invalid")
        
    except Exception as e:
        print(f"  ❌ Map individual failed: {e}")
        individual_results["map"] = None
    
    # Test 2: MoE Execution
    print(f"\n🎯 STEP 2: MoE Execution")
    print("-" * 60)
    
    try:
        config = MoEConfigLoader().load_config()
        orchestrator = MoEOrchestrator.create_default(factory, config)
        
        moe_result = await orchestrator.route_query(query, session_id="moe_test")
        
        print(f"✅ MoE execution completed")
        print(f"  Response length: {len(moe_result.response)} chars")
        print(f"  Experts used: {moe_result.experts_used}")
        print(f"  Latency: {moe_result.trace.latency_ms:.0f}ms")
        
        # Analyze MoE output
        has_coords = bool(re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', moe_result.response))
        has_json = "```json" in moe_result.response
        
        print(f"  MoE final: coords={has_coords}, json={has_json}")
        
        if has_json:
            json_blocks = re.findall(r"```json\s*(.*?)\s*```", moe_result.response, re.DOTALL | re.IGNORECASE)
            print(f"    JSON blocks: {len(json_blocks)}")
            
            for i, json_str in enumerate(json_blocks):
                try:
                    json_obj = json.loads(json_str.strip())
                    if json_obj.get('type') == 'interactive_map':
                        markers = json_obj.get('config', {}).get('markers', [])
                        print(f"      JSON {i+1}: interactive_map with {len(markers)} markers")
                        if markers:
                            first_marker = markers[0]
                            print(f"        First marker: lat={first_marker.get('lat')}, lng={first_marker.get('lng')}")
                except Exception as e:
                    print(f"      JSON {i+1}: invalid - {e}")
        
        # Check expert details from trace
        if hasattr(moe_result.trace, 'expert_details') and moe_result.trace.expert_details:
            print(f"\n  Expert execution details:")
            for detail in moe_result.trace.expert_details:
                print(f"    {detail.expert_id}: status={detail.status}")
                if detail.error:
                    print(f"      Error: {detail.error}")
                if detail.response:
                    expert_has_coords = bool(re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', detail.response))
                    expert_has_json = "```json" in detail.response
                    print(f"      Response: {len(detail.response)} chars, coords={expert_has_coords}, json={expert_has_json}")
        
    except Exception as e:
        print(f"❌ MoE execution failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Comparison Analysis
    print(f"\n📊 STEP 3: Comparison Analysis")
    print("-" * 60)
    
    print("Individual Results:")
    for agent_id, output in individual_results.items():
        if output:
            has_coords = bool(re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output))
            has_json = "```json" in output
            print(f"  {agent_id}: {len(output)} chars, coords={has_coords}, json={has_json}")
        else:
            print(f"  {agent_id}: FAILED")
    
    print(f"\nMoE Result:")
    moe_has_coords = bool(re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', moe_result.response))
    moe_has_json = "```json" in moe_result.response
    print(f"  Final: {len(moe_result.response)} chars, coords={moe_has_coords}, json={moe_has_json}")
    
    # Identify the issue
    print(f"\n🎯 ISSUE ANALYSIS:")
    
    individual_coords = any(
        output and re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output) 
        for output in individual_results.values() if output
    )
    
    if individual_coords and not moe_has_coords:
        print("❌ COORDINATES LOST in MoE pipeline!")
        print("   → Individual agents provide coordinates but MoE final result doesn't")
        print("   → Issue is in MoE orchestration, synthesis, or result mixing")
    elif individual_coords and moe_has_coords:
        print("✅ Coordinates preserved through MoE pipeline")
    elif not individual_coords:
        print("❌ No individual agent provides coordinates")
        print("   → Issue is with individual agent execution")
    
    individual_json = any(
        output and "```json" in output and "interactive_map" in output
        for output in individual_results.values() if output
    )
    
    if individual_json and not moe_has_json:
        print("❌ JSON BLOCKS LOST in MoE pipeline!")
    elif individual_json and moe_has_json:
        print("✅ JSON blocks preserved through MoE pipeline")
    
    return individual_results, moe_result

if __name__ == "__main__":
    asyncio.run(test_individual_vs_moe())