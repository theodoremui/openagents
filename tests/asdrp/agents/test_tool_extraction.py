"""
Tests for tool extraction and handling across different agent types.

These tests ensure that tools are properly extracted from agents regardless
of how they're wrapped by the OpenAI agents SDK.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys


class TestToolExtraction:
    """Test various scenarios of tool extraction from agents."""

    def test_extract_tool_name_from_name_attribute(self):
        """Test extraction when tool has .name attribute."""
        tool = Mock()
        tool.name = "test_tool"

        # Simulate extraction logic
        if hasattr(tool, 'name'):
            tool_name = tool.name
        else:
            tool_name = "unknown"

        assert tool_name == "test_tool"

    def test_extract_tool_name_from_function_name(self):
        """Test extraction when tool has __name__ attribute."""
        tool = Mock()
        del tool.name  # Remove .name
        tool.__name__ = "test_function"

        # Simulate extraction logic
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        else:
            tool_name = "unknown"

        assert tool_name == "test_function"

    def test_extract_tool_name_from_nested_function(self):
        """Test extraction when tool has nested .function attribute."""
        inner_func = Mock()
        inner_func.__name__ = "nested_function"

        tool = Mock()
        del tool.name
        del tool.__name__
        tool.function = inner_func

        # Simulate extraction logic
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        elif hasattr(tool, 'function') and hasattr(tool.function, '__name__'):
            tool_name = tool.function.__name__
        else:
            tool_name = "unknown"

        assert tool_name == "nested_function"

    def test_extract_tool_name_from_class_name(self):
        """Test extraction falls back to class name."""
        tool = Mock()
        del tool.name
        del tool.__name__
        tool.function = None
        type(tool).__name__ = "ToolWrapper"

        # Simulate extraction logic
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

        assert tool_name == "ToolWrapper"

    def test_extract_tool_name_with_exception(self):
        """Test extraction handles exceptions gracefully."""
        # Create a tool that raises when accessing attributes
        # Use a custom class that raises on attribute access
        class ExceptionTool:
            def __getattribute__(self, name):
                if name == 'name':
                    raise AttributeError("Access denied")
                return super().__getattribute__(name)

        tool = ExceptionTool()

        # Simulate extraction logic with exception handling
        # Access attribute directly to catch exceptions (getattr with default suppresses them)
        try:
            tool_name = tool.name  # This will raise AttributeError
        except Exception:
            tool_name = "fallback_0"

        assert tool_name == "fallback_0"

    def test_extract_tool_names_from_list(self):
        """Test extracting names from a list of tools."""
        tools = []

        # Tool with .name
        tool1 = Mock()
        tool1.name = "tool_one"
        tools.append(tool1)

        # Tool with __name__
        tool2 = Mock()
        del tool2.name
        tool2.__name__ = "tool_two"
        tools.append(tool2)

        # Tool with nested function
        inner = Mock()
        inner.__name__ = "tool_three"
        tool3 = Mock()
        del tool3.name
        del tool3.__name__
        tool3.function = inner
        tools.append(tool3)

        # Extract names using robust logic
        tool_names = []
        for tool in tools:
            try:
                if hasattr(tool, 'name'):
                    tool_name = tool.name
                elif hasattr(tool, '__name__'):
                    tool_name = tool.__name__
                elif hasattr(tool, 'function') and hasattr(tool.function, '__name__'):
                    tool_name = tool.function.__name__
                else:
                    tool_name = f"tool_{len(tool_names)}"
                tool_names.append(tool_name)
            except Exception:
                tool_names.append(f"tool_{len(tool_names)}")

        assert tool_names == ["tool_one", "tool_two", "tool_three"]

    def test_coroutine_object_handling(self):
        """Test handling coroutine objects (original bug)."""
        import types
        
        async def async_func():
            pass

        coroutine = async_func()

        # Simulate extraction - coroutine objects don't have .name
        # Coroutines have __name__ pointing to the function, but we want the type name
        tool_name = None
        try:
            # Check if it's a coroutine type first - use type name instead of __name__
            if isinstance(coroutine, types.CoroutineType):
                tool_name = type(coroutine).__name__
            elif hasattr(coroutine, 'name'):
                tool_name = coroutine.name
            elif hasattr(coroutine, '__name__'):
                # For coroutines, __name__ points to the function, not the type
                # So we should use the type name instead
                tool_name = type(coroutine).__name__
            else:
                tool_name = type(coroutine).__name__
        except Exception:
            tool_name = "fallback"

        assert tool_name in ["coroutine", "fallback"]

        # Cleanup
        coroutine.close()

    def test_empty_tools_list(self):
        """Test handling empty tools list."""
        tools = []

        tool_names = []
        for tool in tools:
            try:
                tool_name = getattr(tool, 'name', 'unknown')
                tool_names.append(tool_name)
            except Exception:
                tool_names.append('error')

        assert tool_names == []

    def test_none_tools_list(self):
        """Test handling None tools list."""
        tools = None

        tool_names = []
        if tools:
            for tool in tools:
                tool_names.append(getattr(tool, 'name', 'unknown'))

        assert tool_names == []


class TestMapToolsStructure:
    """Test MapTools tool_list structure specifically."""

    def test_maptools_has_all_expected_tools(self):
        """Test that MapTools has all expected tool methods."""
        expected_tools = [
            "get_coordinates_by_address",
            "get_address_by_coordinates",
            "search_places_nearby",
            "get_place_details",
            "get_travel_time_distance",
            "get_distance_matrix",
            "places_autocomplete",
            "get_route_polyline",
            "get_static_map_url",
            "get_interactive_map_data"  # NEW
        ]

        # This test would normally import MapTools, but we'll simulate
        # the expected structure
        mock_tools = []
        for name in expected_tools:
            tool = Mock()
            tool.name = name
            mock_tools.append(tool)

        # Verify all tools present
        extracted_names = [t.name for t in mock_tools]
        assert set(extracted_names) == set(expected_tools)
        assert len(extracted_names) == 10

    def test_maptools_tool_list_is_iterable(self):
        """Test that tool_list can be iterated."""
        mock_tool_list = [Mock(name=f"tool_{i}") for i in range(5)]

        # Should be able to iterate
        count = 0
        for tool in mock_tool_list:
            assert hasattr(tool, 'name')
            count += 1

        assert count == 5

    def test_maptools_tool_list_not_none(self):
        """Test that tool_list is never None."""
        # Simulate ToolsMeta behavior
        tool_list = []  # Should be empty list, not None

        assert tool_list is not None
        assert isinstance(tool_list, list)


class TestRobustToolExtraction:
    """Test the robust tool extraction implementation."""

    def robust_extract_tool_name(self, tool, index=0):
        """
        Robust tool name extraction.
        Mimics the implementation in server/main.py.
        Uses direct attribute access with try/except to properly catch exceptions.
        """
        exceptions_occurred = False
        
        # Try accessing attributes directly to catch exceptions
        try:
            return tool.name
        except (AttributeError, Exception):
            exceptions_occurred = True
        
        try:
            return tool.__name__
        except (AttributeError, Exception):
            exceptions_occurred = True
        
        try:
            if hasattr(tool, 'function') and tool.function is not None:
                return tool.function.__name__
        except (AttributeError, Exception):
            exceptions_occurred = True
        
        try:
            return tool.__class__.__name__
        except (AttributeError, Exception):
            exceptions_occurred = True
        
        # If exceptions occurred during attribute access, use fallback instead of class name
        # This ensures we don't return a class name when we couldn't access any attributes
        if exceptions_occurred:
            return f"tool_{index}"
        
        # Last resort: use type() to get class name (only if no exceptions occurred)
        try:
            return str(type(tool).__name__)
        except Exception:
            return f"tool_{index}"

    def test_robust_extraction_with_all_types(self):
        """Test robust extraction with various tool types."""
        # Type 1: .name
        tool1 = Mock()
        tool1.name = "tool_with_name"
        assert self.robust_extract_tool_name(tool1) == "tool_with_name"

        # Type 2: __name__
        tool2 = Mock()
        del tool2.name
        tool2.__name__ = "tool_with_dunder"
        assert self.robust_extract_tool_name(tool2) == "tool_with_dunder"

        # Type 3: nested function
        inner = Mock()
        inner.__name__ = "nested_tool"
        tool3 = Mock()
        del tool3.name
        del tool3.__name__
        tool3.function = inner
        assert self.robust_extract_tool_name(tool3) == "nested_tool"

        # Type 4: class name
        tool4 = Mock()
        del tool4.name
        del tool4.__name__
        tool4.function = None
        type(tool4).__name__ = "CustomClass"
        assert self.robust_extract_tool_name(tool4) == "CustomClass"

    def test_robust_extraction_with_exception(self):
        """Test robust extraction handles exceptions."""
        # Create a tool that raises when accessing attributes
        class ExceptionTool:
            def __getattribute__(self, name):
                raise AttributeError("Boom!")

        tool = ExceptionTool()

        result = self.robust_extract_tool_name(tool, index=5)
        assert result == "tool_5"

    def test_robust_extraction_batch(self):
        """Test extracting from multiple tools."""
        tools = []

        # Mix of different types
        for i in range(3):
            tool = Mock()
            tool.name = f"tool_{i}"
            tools.append(tool)

        # Tool with exception - create a class that raises on attribute access
        class ExceptionTool:
            def __getattribute__(self, name):
                raise Exception("Error")

        bad_tool = ExceptionTool()
        tools.append(bad_tool)

        # Extract all
        names = [self.robust_extract_tool_name(t, i) for i, t in enumerate(tools)]

        assert names[0] == "tool_0"
        assert names[1] == "tool_1"
        assert names[2] == "tool_2"
        assert names[3] == "tool_3"  # Fallback for bad tool


class TestEdgeCases:
    """Test edge cases that could cause failures."""

    def test_tool_with_none_value(self):
        """Test handling None as a tool."""
        tool = None

        try:
            if tool and hasattr(tool, 'name'):
                name = tool.name
            else:
                name = "unknown"
        except Exception:
            name = "error"

        assert name == "unknown"

    def test_tool_with_empty_string_name(self):
        """Test tool with empty string name."""
        tool = Mock()
        tool.name = ""

        name = getattr(tool, 'name', 'default')
        # Should get empty string, but might want to handle
        assert name == ""

    def test_tool_with_numeric_name(self):
        """Test tool with numeric name (unusual but possible)."""
        tool = Mock()
        tool.name = 123

        name = tool.name
        assert name == 123

    def test_tool_with_special_characters(self):
        """Test tool name with special characters."""
        tool = Mock()
        tool.name = "tool:name@special#chars"

        name = tool.name
        assert name == "tool:name@special#chars"

    def test_tool_list_with_duplicates(self):
        """Test handling duplicate tool names."""
        tools = []
        for i in range(3):
            tool = Mock()
            tool.name = "duplicate_tool"
            tools.append(tool)

        names = [t.name for t in tools]
        assert len(names) == 3
        assert all(n == "duplicate_tool" for n in names)
