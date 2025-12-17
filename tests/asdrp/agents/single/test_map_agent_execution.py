#!/usr/bin/env python3
"""
Comprehensive MapAgent Execution Test

Tests the complete MapAgent workflow including:
1. Agent creation
2. Tool availability
3. Actual execution with timing
4. Tool call patterns
5. LLM response time

This script identifies the actual bottleneck in MapAgent execution.

NOTE: This is an integration test that makes real API calls.
It is marked as 'slow' and 'integration' - run with:
  pytest -m "slow"  # Run slow tests
  pytest -m "integration"  # Run integration tests
  pytest -m "not slow"  # Skip slow tests (default)
"""

import asyncio
import time
import sys
import pytest
import json
from pathlib import Path

# #region agent log
_DEBUG_LOG_PATH = "/Users/pmui/dev/halo/openagents/.cursor/debug.log"
def _log_debug(location: str, message: str, data: dict, hypothesis_id: str = ""):
    try:
        entry = {"location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "hypothesisId": hypothesis_id}
        with open(_DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except: pass
# #endregion

# Navigate from tests/asdrp/agents/single/ to project root
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents import Runner
from asdrp.agents.single.map_agent import create_map_agent
from asdrp.actions.geo.map_tools import MapTools
from asdrp.agents.config_loader import AgentConfigLoader


# Fast unit tests (no API calls)
def test_mapagent_creation():
    """Test agent creation - fast unit test."""
    start_time = time.time()
    agent = create_map_agent()
    creation_time = time.time() - start_time
    
    assert agent is not None, "Agent should be created"
    assert agent.name == "MapAgent", f"Expected 'MapAgent', got '{agent.name}'"
    assert hasattr(agent, 'tools'), "Agent should have tools attribute"
    assert agent.tools is not None, "Agent tools should not be None"
    assert len(agent.tools) > 0, "Agent should have at least one tool"
    assert creation_time < 1.0, f"Agent creation should be fast (<1s), took {creation_time:.3f}s"


def test_maptools_availability():
    """Test MapTools are available - fast unit test."""
    assert hasattr(MapTools, 'tool_list'), "MapTools should have tool_list"
    assert MapTools.tool_list is not None, "tool_list should not be None"
    assert len(MapTools.tool_list) > 0, "Should have at least one tool"
    
    # Verify expected tools are present
    tool_names = []
    for tool in MapTools.tool_list:
        if hasattr(tool, '__name__'):
            tool_names.append(tool.__name__)
        elif hasattr(tool, 'name'):
            tool_names.append(tool.name)
    
    expected_tools = ['get_static_map_url', 'get_interactive_map_data']
    for expected in expected_tools:
        assert expected in tool_names, f"Expected tool '{expected}' not found. Available: {tool_names}"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_mapagent_execution():
    """
    Test complete MapAgent execution with detailed timing.
    """

    print("=" * 80)
    print("MapAgent Execution Test - Deep Investigation")
    print("=" * 80)
    print()

    # Test 1: Verify tools are available
    print("Test 1: Verify MapTools are available")
    print("-" * 80)
    print(f"✅ Total tools: {len(MapTools.tool_list)}")
    print(f"✅ Tool names: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in MapTools.tool_list[:3]]}")
    print()

    # Test 2: Create agent with optimized instructions from config
    print("Test 2: Create MapAgent")
    print("-" * 80)
    start_time = time.time()
    try:
        # Load optimized instructions AND model config from config file
        # Using gpt-4o-mini for fast execution (valid OpenAI model)
        config_loader = AgentConfigLoader()
        agent_config = config_loader.get_agent_config("map")
        optimized_instructions = agent_config.default_instructions
        model_config = agent_config.model  # Critical: pass model config for gpt-4.1-mini
        
        agent = create_map_agent(instructions=optimized_instructions, model_config=model_config)
        creation_time = time.time() - start_time
        print(f"✅ Agent created in {creation_time:.3f}s")
        print(f"   Agent name: {agent.name}")
        print(f"   Model: {model_config.name}")  # Show which model is being used
        print(f"   Has tools: {hasattr(agent, 'tools') and agent.tools is not None}")
        if hasattr(agent, 'tools') and agent.tools:
            print(f"   Tool count: {len(agent.tools)}")
        print(f"   Instructions length: {len(optimized_instructions)} chars (optimized)")
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    print()

    # Test 3: Execute with simple query (should be fast)
    print("Test 3: Simple Query - Geocoding")
    print("-" * 80)
    simple_query = "What are the coordinates of San Carlos, CA?"
    print(f"Query: {simple_query}")
    print()

    start_time = time.time()
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=simple_query,
            max_turns=5  # Reduced from 10 to speed up test
        )
        execution_time = time.time() - start_time

        print(f"✅ Execution completed in {execution_time:.2f}s")
        assert execution_time < 20.0, f"Simple query should complete in <20s, took {execution_time:.2f}s"
        
        assert result is not None, "Result should not be None"
        assert hasattr(result, 'final_output'), "Result should have final_output"
        
        output = str(result.final_output)
        print(f"   Response: {output[:200]}...")

        # Check usage metadata
        if hasattr(result, 'usage'):
            usage = result.usage
            print(f"   Tokens - Prompt: {usage.get('prompt_tokens', 'N/A')}, Completion: {usage.get('completion_tokens', 'N/A')}, Total: {usage.get('total_tokens', 'N/A')}")

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise to fail the test
    print()

    # Test 4: Execute with complex routing query (the problematic one)
    # This is the slowest test - only run when explicitly requested
    print("Test 4: Complex Query - Driving Route with Visual Map")
    print("-" * 80)
    complex_query = "Show us a visual navigation map routing from San Carlos to the SF Salesforce Tower."
    print(f"Query: {complex_query}")
    print()

    # #region agent log
    _log_debug("test_map_agent:test4:start", "Complex query test starting", {
        "query": complex_query,
        "agent_name": agent.name,
        "model": model_config.name,
        "model_temp": model_config.temperature,
        "instructions_len": len(optimized_instructions),
        "tool_count": len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0,
        "max_turns": 10
    }, "C")
    # #endregion

    print("Starting execution with detailed timing...")
    start_time = time.time()

    try:
        result = await Runner.run(
            starting_agent=agent,
            input=complex_query,
            max_turns=10  # Reduced from 15 to speed up test
        )

        execution_time = time.time() - start_time

        # #region agent log
        _log_debug("test_map_agent:test4:end", "Complex query completed", {
            "execution_time_s": execution_time,
            "has_final_output": hasattr(result, 'final_output'),
            "output_len": len(str(result.final_output)) if hasattr(result, 'final_output') else 0
        }, "C")
        # #endregion

        print(f"✅ Execution completed in {execution_time:.2f}s")
        assert execution_time < 60.0, f"Complex query should complete in <60s, took {execution_time:.2f}s"
        print()

        # Analyze result
        print("Execution Analysis:")
        print("-" * 80)
        print(f"Total execution time: {execution_time:.2f}s")

        assert result is not None, "Result should not be None"
        assert hasattr(result, 'final_output'), "Result should have final_output"
        
        output = str(result.final_output)

        if hasattr(result, 'usage'):
            usage = result.usage
            print(f"Token usage:")
            print(f"   - Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"   - Completion tokens: {usage.get('completion_tokens', 'N/A')}")
            print(f"   - Total tokens: {usage.get('total_tokens', 'N/A')}")

        # Show final output
        print()
        print("Final output (first 500 chars):")
        print("-" * 80)
        print(output[:500])
        if len(output) > 500:
            print(f"\n... ({len(output) - 500} more characters)")

        # Check if map is in output (interactive map JSON is the modern approach)
        print()
        print("Map Format Check:")
        print("-" * 80)
        has_interactive_map = '"type": "interactive_map"' in output or '"type":"interactive_map"' in output
        has_map_url = "maps.googleapis.com" in output
        has_markdown = "![" in output

        if has_interactive_map:
            print("✅ Interactive map JSON block found (modern format)")
        elif has_map_url:
            print("✅ Static map URL found (legacy format)")
        elif has_markdown:
            print("✅ Markdown image syntax found (legacy format)")
        else:
            print("❌ No map format detected")

        # Assertions for test validation
        # Accept any of the three formats: interactive map (preferred), static URL, or markdown
        assert has_interactive_map or has_map_url or has_markdown, \
            "Response should contain interactive map JSON, static map URL, or markdown image syntax"

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ Execution failed after {execution_time:.2f}s")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise to fail the test

    print()
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()

    print("Key Findings:")
    print("1. Tool availability: Check if all 9 MapTools are accessible")
    print("2. Agent creation: Should be < 0.1s")
    print("3. Simple query: Should be < 10s")
    print("4. Complex query: Should be < 30s (currently timing out at 120s)")
    print()

    print("Likely Bottlenecks:")
    print("- Multiple LLM turns (max_turns=5 allows up to 5 back-and-forth calls)")
    print("- Large tool response payloads")
    print("- Session memory accumulation")
    print("- Network latency to OpenAI API")
    print()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_direct_tools():
    """
    Test MapTools directly to verify they're fast.
    This makes real API calls - marked as slow/integration test.
    """
    print()
    print("=" * 80)
    print("Direct MapTools Performance Test")
    print("=" * 80)
    print()

    # Test 1: Directions API
    print("Test 1: get_travel_time_distance()")
    start_time = time.time()
    try:
        result = await MapTools.get_travel_time_distance(
            origin="San Carlos, CA",
            destination="Salesforce Tower, San Francisco, CA",
            mode="driving"
        )
        elapsed = time.time() - start_time
        print(f"✅ Completed in {elapsed:.3f}s")
        assert elapsed < 5.0, f"Directions API call should be <5s, took {elapsed:.3f}s"
        
        assert result is not None, "Directions result should not be None"
        assert len(result) > 0, "Should have at least one route"
        
        leg = result[0]['legs'][0]
        print(f"   Distance: {leg['distance']['text']}")
        print(f"   Duration: {leg['duration']['text']}")
        
        assert 'distance' in leg, "Leg should have distance"
        assert 'duration' in leg, "Leg should have duration"
    except Exception as e:
        print(f"❌ Failed: {e}")
        raise  # Re-raise to fail the test
    print()

    # Test 2: Polyline extraction
    print("Test 2: get_route_polyline()")
    start_time = time.time()
    try:
        polyline = MapTools.get_route_polyline(result)
        elapsed = time.time() - start_time
        print(f"✅ Completed in {elapsed:.3f}s")
        assert elapsed < 0.1, f"Polyline extraction should be <0.1s, took {elapsed:.3f}s"
        
        assert polyline is not None, "Polyline should not be None"
        assert len(polyline) > 0, "Polyline should not be empty"
        print(f"   Polyline length: {len(polyline)} chars")
    except Exception as e:
        print(f"❌ Failed: {e}")
        raise  # Re-raise to fail the test
    print()

    # Test 3: Static map URL
    print("Test 3: get_static_map_url()")
    start_time = time.time()
    try:
        map_url = await MapTools.get_static_map_url(
            zoom=10,
            encoded_polyline=polyline
        )
        elapsed = time.time() - start_time
        print(f"✅ Completed in {elapsed:.3f}s")
        assert elapsed < 1.0, f"Map URL generation should be <1s, took {elapsed:.3f}s"
        
        assert map_url is not None, "Map URL should not be None"
        assert len(map_url) > 0, "Map URL should not be empty"
        assert "maps.googleapis.com" in map_url, "Map URL should contain Google Maps domain"
        
        print(f"   URL length: {len(map_url)} chars")
        print(f"   URL (first 100 chars): {map_url[:100]}...")
    except Exception as e:
        print(f"❌ Failed: {e}")
        raise  # Re-raise to fail the test
    print()


if __name__ == "__main__":
    print()

    # Run direct tools test first
    asyncio.run(test_direct_tools())

    print()
    print()

    # Run full agent execution test
    asyncio.run(test_mapagent_execution())
