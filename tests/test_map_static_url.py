"""
Test suite for verifying MapAgent static map URL generation.

This module performs comprehensive testing of:
1. Tool discovery by ToolsMeta
2. URL generation functionality  
3. Agent tool binding
4. Integration with OpenAI function_tool wrapper

Following pytest best practices:
- Tests use assertions instead of return values
- Tests are grouped logically in classes
- Each test validates a specific behavior
"""

import asyncio
import pytest
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


class TestMapToolsDiscovery:
    """Test suite for MapTools tool discovery by ToolsMeta."""
    
    def test_maptool_import(self):
        """Verify MapTools can be imported successfully."""
        from asdrp.actions.geo.map_tools import MapTools
        assert MapTools is not None
    
    def test_spec_functions_populated(self):
        """Verify spec_functions list is populated by ToolsMeta."""
        from asdrp.actions.geo.map_tools import MapTools
        
        assert hasattr(MapTools, 'spec_functions'), "spec_functions attribute missing"
        assert isinstance(MapTools.spec_functions, list), "spec_functions should be a list"
        assert len(MapTools.spec_functions) > 0, "spec_functions should not be empty"
    
    def test_get_static_map_url_discovered(self):
        """Verify get_static_map_url is discovered by ToolsMeta."""
        from asdrp.actions.geo.map_tools import MapTools
        
        assert 'get_static_map_url' in MapTools.spec_functions, \
            f"get_static_map_url not found in spec_functions. Available: {MapTools.spec_functions}"


class TestMapToolsToolList:
    """Test suite for MapTools tool_list wrapper functionality."""
    
    def test_tool_list_populated(self):
        """Verify tool_list is populated by ToolsMeta."""
        from asdrp.actions.geo.map_tools import MapTools
        
        assert hasattr(MapTools, 'tool_list'), "tool_list attribute missing"
        assert isinstance(MapTools.tool_list, list), "tool_list should be a list"
        assert len(MapTools.tool_list) > 0, "tool_list should not be empty"
    
    def test_tool_list_matches_spec_functions(self):
        """Verify tool_list and spec_functions have matching lengths."""
        from asdrp.actions.geo.map_tools import MapTools
        
        assert len(MapTools.tool_list) == len(MapTools.spec_functions), \
            f"Mismatch: {len(MapTools.tool_list)} tools vs {len(MapTools.spec_functions)} spec_functions"
    
    def test_get_static_map_url_in_tool_list(self):
        """Verify get_static_map_url is wrapped properly in tool_list."""
        from asdrp.actions.geo.map_tools import MapTools
        
        tool_names = []
        for tool in MapTools.tool_list:
            name = getattr(tool, 'name', getattr(tool, '__name__', None))
            if name:
                tool_names.append(name)
        
        assert 'get_static_map_url' in tool_names, \
            f"get_static_map_url not found in tool_list. Available: {tool_names}"


class TestStaticMapUrlGeneration:
    """Test suite for static map URL generation functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_center_url(self):
        """Test URL generation with simple center parameter."""
        from asdrp.actions.geo.map_tools import MapTools
        
        url = await MapTools.get_static_map_url(
            center="San Francisco, CA",
            zoom=12,
            size="600x400"
        )
        
        assert url is not None, "URL should not be None"
        assert url.startswith("https://maps.googleapis.com/maps/api/staticmap"), \
            f"Invalid URL base: {url[:50]}"
        assert "zoom=12" in url, "Missing zoom parameter"
        assert "size=600x400" in url, "Missing size parameter"
        assert "key=" in url, "Missing API key"
    
    @pytest.mark.asyncio
    async def test_url_with_markers(self):
        """Test URL generation with marker parameters."""
        from asdrp.actions.geo.map_tools import MapTools
        
        url = await MapTools.get_static_map_url(
            center="37.7749,-122.4194",
            zoom=13,
            markers=["color:red|label:A|37.7749,-122.4194"]
        )
        
        assert url is not None, "URL should not be None"
        assert "markers=" in url, "Missing markers parameter"
    
    @pytest.mark.asyncio
    async def test_url_with_path(self):
        """Test URL generation with path (route) parameter."""
        from asdrp.actions.geo.map_tools import MapTools
        
        url = await MapTools.get_static_map_url(
            zoom=10,
            path=["37.7749,-122.4194", "37.5072,-122.2605"]  # SF to San Carlos
        )
        
        assert url is not None, "URL should not be None"
        assert "path=" in url, "Missing path parameter"


class TestMapAgentIntegration:
    """Test suite for MapAgent tool integration."""
    
    def test_map_agent_creation(self):
        """Verify MapAgent can be created successfully."""
        from asdrp.agents.single.map_agent import create_map_agent
        
        agent = create_map_agent()
        
        assert agent is not None, "Agent should not be None"
        assert agent.name == "MapAgent", f"Expected 'MapAgent', got '{agent.name}'"
    
    def test_map_agent_has_tools(self):
        """Verify MapAgent has tools attribute."""
        from asdrp.agents.single.map_agent import create_map_agent
        
        agent = create_map_agent()
        
        assert hasattr(agent, 'tools'), "Agent should have 'tools' attribute"
        assert len(agent.tools) > 0, "Agent should have at least one tool"
    
    def test_map_agent_has_static_map_tool(self):
        """Verify MapAgent has get_static_map_url tool."""
        from asdrp.agents.single.map_agent import create_map_agent
        
        agent = create_map_agent()
        tool_names = [
            getattr(tool, 'name', getattr(tool, '__name__', '')) 
            for tool in agent.tools
        ]
        
        assert 'get_static_map_url' in tool_names, \
            f"get_static_map_url not found. Available tools: {tool_names}"


class TestMapAgentInstructions:
    """Test suite for MapAgent instruction configuration."""
    
    @pytest.fixture(autouse=True)
    def cleanup_sessions(self):
        """Cleanup session cache before and after each test to prevent connection leaks."""
        from asdrp.agents.agent_factory import AgentFactory
        # Cleanup before test to ensure clean state
        AgentFactory.instance().clear_session_cache()
        yield
        # Clear session cache after test to close any SQLite connections
        AgentFactory.instance().clear_session_cache()
        # Force garbage collection to ensure connections are closed
        import gc
        gc.collect()
    
    def test_instructions_loaded(self):
        """Verify MapAgent instructions can be loaded from config."""
        from asdrp.agents.config_loader import AgentConfigLoader
        
        loader = AgentConfigLoader()
        config = loader.get_agent_config('map')
        
        assert config is not None, "Config should not be None"
        assert config.default_instructions, "Instructions should not be empty"
        assert len(config.default_instructions) > 100, "Instructions seem too short"
    
    def test_instructions_mention_static_map_url(self):
        """Verify instructions mention the get_static_map_url tool."""
        from asdrp.agents.config_loader import AgentConfigLoader
        
        loader = AgentConfigLoader()
        config = loader.get_agent_config('map')
        
        assert 'get_static_map_url' in config.default_instructions, \
            "Instructions should mention get_static_map_url tool"
    
    def test_instructions_include_visual_map_capabilities(self):
        """Verify instructions document visual map generation capabilities."""
        from asdrp.agents.config_loader import AgentConfigLoader
        
        loader = AgentConfigLoader()
        config = loader.get_agent_config('map')
        instructions = config.default_instructions
        
        # Check for visual map generation capability documentation
        # The config may use "VISUAL MAP GENERATION" header or mention "visual map"
        has_visual_section = (
            'VISUAL MAP GENERATION' in instructions or
            'visual map' in instructions.lower()
        )
        assert has_visual_section, \
            "Instructions should document visual map generation capabilities"
        
        # Check for workflow documentation
        # The optimized config uses query-type sections with numbered steps
        # instead of explicit "WORKFLOW" headers (per optimization guidelines)
        has_workflow_documentation = (
            'WORKFLOW' in instructions or 
            'workflow' in instructions.lower() or
            # Condensed config uses query-type sections with numbered steps
            ('queries:' in instructions.lower() and '1.' in instructions) or
            # Or has numbered tool chain documentation  
            ('get_travel_time_distance' in instructions and 'get_route_polyline' in instructions)
        )
        assert has_workflow_documentation, \
            "Instructions should include workflow documentation (numbered steps or workflow sections)"


# ============================================================================
# Main execution for standalone testing (not through pytest)
# ============================================================================

async def _run_manual_tests():
    """Run tests manually with verbose output for debugging."""
    print("\n" + "="*70)
    print("🧪 MAPAGENT STATIC MAP URL - MANUAL TEST SUITE")
    print("="*70)
    
    results = []
    
    # Discovery tests
    print("\n--- Testing Tool Discovery ---")
    try:
        test = TestMapToolsDiscovery()
        test.test_maptool_import()
        test.test_spec_functions_populated()
        test.test_get_static_map_url_discovered()
        results.append(("Tool Discovery", True))
        print("✅ All discovery tests passed")
    except AssertionError as e:
        results.append(("Tool Discovery", False))
        print(f"❌ Discovery test failed: {e}")
    
    # Tool list tests
    print("\n--- Testing Tool List ---")
    try:
        test = TestMapToolsToolList()
        test.test_tool_list_populated()
        test.test_tool_list_matches_spec_functions()
        test.test_get_static_map_url_in_tool_list()
        results.append(("Tool List Wrapper", True))
        print("✅ All tool list tests passed")
    except AssertionError as e:
        results.append(("Tool List Wrapper", False))
        print(f"❌ Tool list test failed: {e}")
    
    # URL generation tests
    print("\n--- Testing URL Generation ---")
    try:
        test = TestStaticMapUrlGeneration()
        await test.test_simple_center_url()
        await test.test_url_with_markers()
        await test.test_url_with_path()
        results.append(("URL Generation", True))
        print("✅ All URL generation tests passed")
    except AssertionError as e:
        results.append(("URL Generation", False))
        print(f"❌ URL generation test failed: {e}")
    
    # Agent integration tests
    print("\n--- Testing Agent Integration ---")
    try:
        test = TestMapAgentIntegration()
        test.test_map_agent_creation()
        test.test_map_agent_has_tools()
        test.test_map_agent_has_static_map_tool()
        results.append(("Agent Integration", True))
        print("✅ All agent integration tests passed")
    except AssertionError as e:
        results.append(("Agent Integration", False))
        print(f"❌ Agent integration test failed: {e}")
    
    # Instructions tests
    print("\n--- Testing Instructions ---")
    try:
        test = TestMapAgentInstructions()
        test.test_instructions_loaded()
        test.test_instructions_mention_static_map_url()
        test.test_instructions_include_visual_map_capabilities()
        results.append(("Instructions Check", True))
        print("✅ All instructions tests passed")
    except AssertionError as e:
        results.append(("Instructions Check", False))
        print(f"❌ Instructions test failed: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n❌ SOME TESTS FAILED - Review output above for details")
    
    print("\n" + "="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = asyncio.run(_run_manual_tests())
    sys.exit(0 if success else 1)
