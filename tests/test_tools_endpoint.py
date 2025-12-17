#!/usr/bin/env python3
"""
Quick test script to verify the /agents/{agent_id}/tools endpoint works.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import pytest for test decorator, but don't fail if not available
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from asdrp.agents.agent_factory import AgentFactory


# Only use pytest.mark.asyncio if pytest is available
if HAS_PYTEST:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_map_agent_tools():
        """Test that MapAgent tools are accessible (pytest version)."""
        await _test_map_agent_tools_impl()
else:
    async def test_map_agent_tools():
        """Test that MapAgent tools are accessible (standalone version)."""
        await _test_map_agent_tools_impl()


async def _test_map_agent_tools_impl():
    """Test that MapAgent tools are accessible (shared implementation)."""
    factory = AgentFactory.instance()
    agent = await factory.get_agent("map")

    assert agent is not None, "Agent should not be None"
    assert agent.name == "MapAgent", f"Expected 'MapAgent', got '{agent.name}'"

    # Extract tool names
    tool_names = []
    assert hasattr(agent, 'tools'), "Agent should have 'tools' attribute"
    assert agent.tools is not None, "Agent tools should not be None"
    assert len(agent.tools) > 0, "Agent should have at least one tool"

    for i, tool in enumerate(agent.tools):
        try:
            # Try different ways to extract tool name
            if hasattr(tool, 'name'):
                tool_name = tool.name
            elif hasattr(tool, '__name__'):
                tool_name = tool.__name__
            elif hasattr(tool, 'function') and hasattr(tool.function, '__name__'):
                tool_name = tool.function.__name__
            elif hasattr(tool, '__class__'):
                tool_name = tool.__class__.__name__
            else:
                tool_name = str(type(tool).__name__)

            tool_names.append(tool_name)
        except Exception as e:
            # If extraction fails, use fallback
            tool_names.append(f"tool_{i}")

    assert len(tool_names) > 0, "Should have extracted at least one tool name"
    assert 'get_static_map_url' in tool_names, \
        f"get_static_map_url not found in tools. Available: {tool_names}"
    assert 'get_interactive_map_data' in tool_names, \
        f"get_interactive_map_data not found in tools. Available: {tool_names}"
    
    return tool_names


if __name__ == "__main__":
    # For standalone execution, use asyncio
    import asyncio
    
    async def main():
        print("Testing MapAgent tools extraction...")
        try:
            factory = AgentFactory.instance()
            agent = await factory.get_agent("map")
            print(f"✓ Agent loaded: {agent.name}")
            print(f"✓ Agent has {len(agent.tools)} tools")

            # Extract tool names (same logic as test)
            tool_names = []
            for i, tool in enumerate(agent.tools):
                try:
                    if hasattr(tool, 'name'):
                        tool_name = tool.name
                    elif hasattr(tool, '__name__'):
                        tool_name = tool.__name__
                    elif hasattr(tool, 'function') and hasattr(tool.function, '__name__'):
                        tool_name = tool.function.__name__
                    elif hasattr(tool, '__class__'):
                        tool_name = tool.__class__.__name__
                    else:
                        tool_name = str(type(tool).__name__)
                    tool_names.append(tool_name)
                    print(f"  [{i+1}] {tool_name}")
                except Exception as e:
                    print(f"  [{i+1}] ERROR: {e}")
                    tool_names.append(f"tool_{i}")
            
            print(f"\n✓ Total tools extracted: {len(tool_names)}")
            print(f"✓ Has get_static_map_url: {'get_static_map_url' in tool_names}")
            print(f"✓ Has get_interactive_map_data: {'get_interactive_map_data' in tool_names}")

            if 'get_interactive_map_data' in tool_names:
                print("\n✅ SUCCESS: New interactive map tool is registered!")
                return True
            else:
                print("\n⚠️  WARNING: get_interactive_map_data not found in tools")
                print("Available tools:", tool_names)
                return False
        except AssertionError as e:
            print(f"\n❌ ASSERTION ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
