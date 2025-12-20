#!/usr/bin/env python3
"""
Test YelpMCP MCP Connection Fix

This script tests if the YelpMCP agent can work properly when MCP servers
are connected correctly using the same pattern as the MoE executor.
"""

import asyncio
import sys
from pathlib import Path
from contextlib import AsyncExitStack

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from agents import Runner

async def test_yelp_mcp_with_proper_connection():
    print("🔧 TESTING YelpMCP WITH PROPER MCP CONNECTION")
    print("=" * 80)
    
    query = "Find the top 3 greek restaurants in San Francisco with addresses and coordinates"
    
    # Get YelpMCP agent
    factory = AgentFactory.instance()
    agent, session = await factory.get_agent_with_persistent_session("yelp_mcp", "test_session")
    
    print(f"✅ YelpMCP agent loaded: {type(agent).__name__}")
    
    # Detect MCP servers using the same logic as MoE executor
    mcp_servers = getattr(agent, "mcp_servers", None)
    if not mcp_servers:
        mcp_servers = getattr(agent, "_mcp_servers", None)
    if not mcp_servers and hasattr(agent, "__dict__"):
        for attr_name, attr_value in agent.__dict__.items():
            if "mcp" in attr_name.lower() and isinstance(attr_value, (list, tuple)):
                mcp_servers = attr_value
                break
    
    if mcp_servers:
        print(f"✅ Found {len(mcp_servers)} MCP server(s)")
        
        # Test MCP connection using AsyncExitStack (same as MoE executor)
        try:
            async with AsyncExitStack() as stack:
                print("🔌 Connecting MCP servers...")
                
                for i, mcp_server in enumerate(mcp_servers):
                    print(f"  Connecting server {i+1}: {type(mcp_server).__name__}")
                    await stack.enter_async_context(mcp_server)
                    print(f"  ✅ Server {i+1} connected")
                
                print("🚀 Running YelpMCP agent with connected MCP servers...")
                
                # Run the agent with MCP servers connected
                result = await asyncio.wait_for(
                    Runner.run(
                        starting_agent=agent,
                        input=query,
                        session=session,
                        max_turns=10
                    ),
                    timeout=30.0
                )
                
                output = str(result.final_output) if result.final_output else ""
                print(f"✅ YelpMCP execution completed")
                print(f"Output length: {len(output)} characters")
                
                if output:
                    print(f"\n📄 YelpMCP Output:")
                    print("-" * 60)
                    print(output[:800] + ("..." if len(output) > 800 else ""))
                    print("-" * 60)
                    
                    # Check for coordinates
                    import re
                    coord_patterns = [
                        r'"lat":\s*([\d.-]+)',
                        r'"lng":\s*([\d.-]+)',
                        r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)',
                    ]
                    
                    found_coords = False
                    for pattern in coord_patterns:
                        matches = re.findall(pattern, output)
                        if matches:
                            print(f"✅ Found coordinates: {matches[:3]}")
                            found_coords = True
                            break
                    
                    if not found_coords:
                        print("❌ No coordinates found in output")
                    
                    # Check for addresses
                    if any(word in output.lower() for word in ["st", "street", "ave", "avenue"]):
                        print("✅ Contains address data")
                    else:
                        print("❌ No address data found")
                    
                    # Check for restaurant names
                    greek_restaurants = ["souvla", "kokkari", "milos", "greek"]
                    found_restaurants = [r for r in greek_restaurants if r in output.lower()]
                    if found_restaurants:
                        print(f"✅ Found restaurants: {found_restaurants}")
                    else:
                        print("❌ No restaurant names found")
                    
                    # Check for error messages
                    error_indicators = ["unable", "error", "failed", "issue", "limitation"]
                    has_errors = any(indicator in output.lower() for indicator in error_indicators)
                    if has_errors:
                        print("⚠️  Output contains error indicators")
                    else:
                        print("✅ No error indicators in output")
                
                else:
                    print("❌ No output from YelpMCP agent")
                
        except Exception as e:
            print(f"❌ YelpMCP execution failed: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("❌ No MCP servers found on YelpMCP agent")
        print("Agent attributes:", [attr for attr in dir(agent) if not attr.startswith("__")])

async def test_individual_agents_comparison():
    """Test all agents individually to compare their outputs."""
    print("\n\n🔬 INDIVIDUAL AGENTS COMPARISON")
    print("=" * 80)
    
    query = "Find the top 3 greek restaurants in San Francisco with addresses and coordinates"
    factory = AgentFactory.instance()
    
    agents_to_test = ["yelp_mcp", "yelp", "map"]
    results = {}
    
    for agent_id in agents_to_test:
        print(f"\n🧪 Testing {agent_id} agent:")
        print("-" * 40)
        
        try:
            agent, session = await factory.get_agent_with_persistent_session(agent_id, f"test_{agent_id}")
            
            # Handle MCP agents specially
            if agent_id == "yelp_mcp":
                mcp_servers = getattr(agent, "mcp_servers", None)
                if mcp_servers:
                    async with AsyncExitStack() as stack:
                        for mcp_server in mcp_servers:
                            await stack.enter_async_context(mcp_server)
                        
                        result = await asyncio.wait_for(
                            Runner.run(starting_agent=agent, input=query, session=session, max_turns=10),
                            timeout=30.0
                        )
                else:
                    print("  ⚠️  No MCP servers - running without MCP")
                    result = await asyncio.wait_for(
                        Runner.run(starting_agent=agent, input=query, session=session, max_turns=10),
                        timeout=30.0
                    )
            else:
                # Regular agents
                result = await asyncio.wait_for(
                    Runner.run(starting_agent=agent, input=query, session=session, max_turns=10),
                    timeout=30.0
                )
            
            output = str(result.final_output) if result.final_output else ""
            results[agent_id] = output
            
            print(f"  ✅ Success - Output length: {len(output)} chars")
            
            # Quick analysis
            import re
            has_coords = bool(re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output))
            has_addresses = any(word in output.lower() for word in ["st", "street", "ave", "avenue"])
            has_restaurants = any(word in output.lower() for word in ["souvla", "kokkari", "milos", "greek"])
            has_errors = any(word in output.lower() for word in ["unable", "error", "failed", "limitation"])
            
            print(f"    Coordinates: {'✅' if has_coords else '❌'}")
            print(f"    Addresses: {'✅' if has_addresses else '❌'}")
            print(f"    Restaurants: {'✅' if has_restaurants else '❌'}")
            print(f"    Errors: {'⚠️' if has_errors else '✅'}")
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            results[agent_id] = None
    
    print(f"\n📊 SUMMARY:")
    print("-" * 40)
    
    working_agents = [agent_id for agent_id, output in results.items() if output and len(output) > 100]
    coord_agents = []
    
    for agent_id, output in results.items():
        if output:
            import re
            if re.search(r'(\d{2}\.\d+),\s*(-?\d{2,3}\.\d+)', output):
                coord_agents.append(agent_id)
    
    print(f"Working agents: {working_agents}")
    print(f"Agents with coordinates: {coord_agents}")
    
    if coord_agents:
        print(f"✅ SUCCESS: {coord_agents[0]} can provide coordinate data!")
        return coord_agents[0], results[coord_agents[0]]
    else:
        print(f"❌ ISSUE: No agent provides coordinate data")
        return None, None

if __name__ == "__main__":
    asyncio.run(test_yelp_mcp_with_proper_connection())
    asyncio.run(test_individual_agents_comparison())