#############################################################################
# test_tools_meta.py
#
# Tests for the general ToolsMeta metaclass
#
#############################################################################

import pytest
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

from asdrp.actions.tools_meta import ToolsMeta


class TestToolsMeta:
    """Test the general ToolsMeta metaclass functionality."""
    
    def test_basic_class_method_discovery(self):
        """Test that class methods are discovered correctly."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def method_one(cls) -> str:
                """First test method."""
                return "one"
            
            @classmethod
            def method_two(cls, arg: str) -> str:
                """Second test method."""
                return f"two_{arg}"
            
            @classmethod
            def _private_method(cls) -> str:
                """Private method should be excluded."""
                return "private"
        
        # Check that public methods are discovered
        assert 'method_one' in TestTools.spec_functions
        assert 'method_two' in TestTools.spec_functions
        assert '_private_method' not in TestTools.spec_functions
        
        # Check that spec_functions is sorted
        assert TestTools.spec_functions == sorted(TestTools.spec_functions)
    
    def test_excluded_methods_not_discovered(self):
        """Test that excluded methods are not in spec_functions."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def public_method(cls) -> str:
                return "public"
        
        # Check default exclusions
        assert '__init__' not in TestTools.spec_functions
        assert '__new__' not in TestTools.spec_functions
        assert 'spec_functions' not in TestTools.spec_functions
        assert 'tool_list' not in TestTools.spec_functions
    
    def test_tool_list_creation(self):
        """Test that tool_list is created from discovered methods."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def test_method(cls) -> str:
                return "test"
        
        # Check that tool_list exists and has correct length
        assert hasattr(TestTools, 'tool_list')
        assert isinstance(TestTools.tool_list, list)
        assert len(TestTools.tool_list) == len(TestTools.spec_functions)
        
        # Check that tools are wrapped (they should have name attribute)
        for tool in TestTools.tool_list:
            assert hasattr(tool, 'name') or hasattr(tool, '__name__')
    
    def test_custom_excluded_methods(self):
        """Test that custom excluded methods work via _get_excluded_methods classmethod."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def _get_excluded_methods(cls) -> set[str]:
                return {'custom_excluded'}
            
            @classmethod
            def public_method(cls) -> str:
                return "public"
            
            @classmethod
            def custom_excluded(cls) -> str:
                return "excluded"
        
        assert 'public_method' in TestTools.spec_functions
        assert 'custom_excluded' not in TestTools.spec_functions
    
    def test_setup_class_hook(self):
        """Test that _setup_class classmethod hook is called during class creation."""
        setup_called = []
        
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def _setup_class(cls) -> None:
                setup_called.append(cls)
                cls.custom_attr = "setup_complete"
            
            @classmethod
            def test_method(cls) -> str:
                return "test"
        
        # Check that setup was called
        assert len(setup_called) == 1
        assert setup_called[0] is TestTools
        assert hasattr(TestTools, 'custom_attr')
        assert TestTools.custom_attr == "setup_complete"
    
    def test_multiple_classes_independence(self):
        """Test that multiple classes using ToolsMeta are independent."""
        class ToolsA(metaclass=ToolsMeta):
            @classmethod
            def method_a(cls) -> str:
                return "a"
        
        class ToolsB(metaclass=ToolsMeta):
            @classmethod
            def method_b(cls) -> str:
                return "b"
        
        # Check that each class has its own spec_functions and tool_list
        assert ToolsA.spec_functions != ToolsB.spec_functions
        assert 'method_a' in ToolsA.spec_functions
        assert 'method_b' in ToolsB.spec_functions
        assert 'method_a' not in ToolsB.spec_functions
        assert 'method_b' not in ToolsA.spec_functions
    
    def test_inheritance(self):
        """Test that inheritance works correctly with ToolsMeta."""
        class BaseTools(metaclass=ToolsMeta):
            @classmethod
            def base_method(cls) -> str:
                return "base"
        
        class DerivedTools(BaseTools):
            @classmethod
            def derived_method(cls) -> str:
                return "derived"
        
        # Check that both methods are discovered
        assert 'base_method' in DerivedTools.spec_functions
        assert 'derived_method' in DerivedTools.spec_functions
    
    def test_no_class_methods(self):
        """Test that a class with no class methods still works."""
        class EmptyTools(metaclass=ToolsMeta):
            pass
        
        assert hasattr(EmptyTools, 'spec_functions')
        assert isinstance(EmptyTools.spec_functions, list)
        assert len(EmptyTools.spec_functions) == 0
        assert hasattr(EmptyTools, 'tool_list')
        assert isinstance(EmptyTools.tool_list, list)
        assert len(EmptyTools.tool_list) == 0
    
    def test_instance_methods_not_discovered(self):
        """Test that instance methods (not classmethods) are not discovered."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def class_method(cls) -> str:
                return "class"
            
            def instance_method(self) -> str:
                return "instance"
        
        assert 'class_method' in TestTools.spec_functions
        assert 'instance_method' not in TestTools.spec_functions
    
    def test_static_methods_not_discovered(self):
        """Test that static methods are not discovered (only classmethods)."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def class_method(cls) -> str:
                return "class"
            
            @staticmethod
            def static_method() -> str:
                return "static"
        
        assert 'class_method' in TestTools.spec_functions
        assert 'static_method' not in TestTools.spec_functions
    
    def test_setup_class_can_access_class_attributes(self):
        """Test that _setup_class can set and access class attributes."""
        class TestTools(metaclass=ToolsMeta):
            BASE_URL = "https://api.example.com"
            
            @classmethod
            def _setup_class(cls) -> None:
                cls.api_key = "test_key"
                cls.headers = {"Authorization": f"Bearer {cls.api_key}"}
                # Verify we can access class attributes
                assert cls.BASE_URL == "https://api.example.com"
            
            @classmethod
            def test_method(cls) -> str:
                return "test"
        
        assert TestTools.api_key == "test_key"
        assert TestTools.headers == {"Authorization": "Bearer test_key"}
    
    def test_excluded_methods_override_defaults(self):
        """Test that custom exclusions are added to defaults, not replacing them."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def _get_excluded_methods(cls) -> set[str]:
                return {'custom_excluded'}
            
            @classmethod
            def public_method(cls) -> str:
                return "public"
            
            @classmethod
            def custom_excluded(cls) -> str:
                return "excluded"
        
        # Default exclusions still apply
        assert 'spec_functions' not in TestTools.spec_functions
        assert 'tool_list' not in TestTools.spec_functions
        # Custom exclusions also apply
        assert 'custom_excluded' not in TestTools.spec_functions
        # Public methods are included
        assert 'public_method' in TestTools.spec_functions
    
    def test_tool_list_matches_spec_functions(self):
        """Test that tool_list contains exactly one tool per spec_function."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def method_a(cls) -> str:
                return "a"
            
            @classmethod
            def method_b(cls) -> str:
                return "b"
            
            @classmethod
            def method_c(cls) -> str:
                return "c"
        
        assert len(TestTools.tool_list) == len(TestTools.spec_functions)
        assert len(TestTools.tool_list) == 3
    
    def test_tool_list_contains_callable_tools(self):
        """Test that tool_list contains tool objects."""
        class TestTools(metaclass=ToolsMeta):
            @classmethod
            def test_method(cls, arg: str) -> str:
                return f"result_{arg}"
        
        assert len(TestTools.tool_list) == 1
        tool = TestTools.tool_list[0]
        # Tools should be wrapped by function_tool (FunctionTool objects have on_invoke_tool)
        assert hasattr(tool, 'on_invoke_tool') or callable(tool)
    
    def test_class_variables_not_included(self):
        """Test that class variables are not included in spec_functions."""
        class TestTools(metaclass=ToolsMeta):
            # Class variables should not be discovered
            BASE_URL = "https://api.example.com"
            API_VERSION = "v1"
            config = {"timeout": 30}
            
            @classmethod
            def test_method(cls) -> str:
                return "test"
        
        # Only methods should be in spec_functions, not variables
        assert 'test_method' in TestTools.spec_functions
        assert 'BASE_URL' not in TestTools.spec_functions
        assert 'API_VERSION' not in TestTools.spec_functions
        assert 'config' not in TestTools.spec_functions
    
    def test_properties_not_included(self):
        """Test that properties are not included in spec_functions."""
        class TestTools(metaclass=ToolsMeta):
            _value = "test"
            
            @property
            def value(self) -> str:
                return self._value
            
            @classmethod
            def test_method(cls) -> str:
                return "test"
        
        # Only class methods should be included, not properties
        assert 'test_method' in TestTools.spec_functions
        assert 'value' not in TestTools.spec_functions

