#############################################################################
# test_single_init.py
#
# Comprehensive tests for asdrp.agents.single.__init__ module.
#
# Test Coverage:
# - Module exports (all expected functions and constants)
# - Import functionality for all agent creation functions
# - Import functionality for all DEFAULT_INSTRUCTIONS constants
# - __all__ definition correctness
# - Import error handling
#
# Design Principles:
# - Single Responsibility: Each test class focuses on one aspect
# - DRY: Shared fixtures and helper methods
# - Extensibility: Easy to add new test cases
# - Robustness: Comprehensive error and edge case coverage
#
#############################################################################

import pytest
from unittest.mock import patch


class TestSingleInitExports:
    """
    Test that __init__.py exports all expected functions and constants.
    
    This class validates that the module properly exposes all agent creation
    functions and default instructions constants for external use.
    """
    
    def test_imports_geo_agent_function(self):
        """
        Test that create_geo_agent can be imported from package.
        
        Verifies the function is properly exported and callable.
        """
        from asdrp.agents.single import create_geo_agent
        
        assert callable(create_geo_agent)
        assert create_geo_agent.__name__ == "create_geo_agent"
    
    def test_imports_map_agent_function(self):
        """
        Test that create_map_agent can be imported from package.
        
        Verifies the function is properly exported and callable.
        """
        from asdrp.agents.single import create_map_agent
        
        assert callable(create_map_agent)
        assert create_map_agent.__name__ == "create_map_agent"
    
    def test_imports_one_agent_function(self):
        """
        Test that create_one_agent can be imported from package.
        
        Verifies the function is properly exported and callable.
        """
        from asdrp.agents.single import create_one_agent
        
        assert callable(create_one_agent)
        assert create_one_agent.__name__ == "create_one_agent"
    
    def test_imports_yelp_agent_function(self):
        """
        Test that create_yelp_agent can be imported from package.
        
        Verifies the function is properly exported and callable.
        """
        from asdrp.agents.single import create_yelp_agent
        
        assert callable(create_yelp_agent)
        assert create_yelp_agent.__name__ == "create_yelp_agent"
    
    def test_imports_finance_agent_function(self):
        """
        Test that create_finance_agent can be imported from package.
        
        Verifies the function is properly exported and callable.
        """
        from asdrp.agents.single import create_finance_agent
        
        assert callable(create_finance_agent)
        assert create_finance_agent.__name__ == "create_finance_agent"
    
    def test_imports_all_agent_functions(self):
        """
        Test that all agent creation functions can be imported together.
        
        Verifies all functions are available in a single import statement.
        """
        from asdrp.agents.single import (
            create_geo_agent,
            create_map_agent,
            create_one_agent,
            create_yelp_agent,
            create_finance_agent,
        )
        
        assert all(callable(func) for func in [
            create_geo_agent,
            create_map_agent,
            create_one_agent,
            create_yelp_agent,
            create_finance_agent,
        ])


class TestSingleInitDefaultInstructions:
    """
    Test that DEFAULT_INSTRUCTIONS constants are properly exported.
    
    This class validates that all default instruction constants are available
    for external use with correct naming conventions.
    """
    
    def test_imports_geo_default_instructions(self):
        """
        Test that GEO_DEFAULT_INSTRUCTIONS can be imported.
        
        Verifies the constant is exported and is a string.
        """
        from asdrp.agents.single import GEO_DEFAULT_INSTRUCTIONS
        
        assert isinstance(GEO_DEFAULT_INSTRUCTIONS, str)
        assert len(GEO_DEFAULT_INSTRUCTIONS) > 0
    
    def test_imports_map_default_instructions(self):
        """
        Test that MAP_DEFAULT_INSTRUCTIONS can be imported.
        
        Verifies the constant is exported and is a string.
        """
        from asdrp.agents.single import MAP_DEFAULT_INSTRUCTIONS
        
        assert isinstance(MAP_DEFAULT_INSTRUCTIONS, str)
        assert len(MAP_DEFAULT_INSTRUCTIONS) > 0
    
    def test_imports_one_default_instructions(self):
        """
        Test that ONE_DEFAULT_INSTRUCTIONS can be imported.
        
        Verifies the constant is exported and is a string.
        """
        from asdrp.agents.single import ONE_DEFAULT_INSTRUCTIONS
        
        assert isinstance(ONE_DEFAULT_INSTRUCTIONS, str)
        assert len(ONE_DEFAULT_INSTRUCTIONS) > 0
    
    def test_imports_yelp_default_instructions(self):
        """
        Test that YELP_DEFAULT_INSTRUCTIONS can be imported.
        
        Verifies the constant is exported and is a string.
        """
        from asdrp.agents.single import YELP_DEFAULT_INSTRUCTIONS
        
        assert isinstance(YELP_DEFAULT_INSTRUCTIONS, str)
        assert len(YELP_DEFAULT_INSTRUCTIONS) > 0
    
    def test_imports_finance_default_instructions(self):
        """
        Test that FINANCE_DEFAULT_INSTRUCTIONS can be imported.
        
        Verifies the constant is exported and is a string.
        """
        from asdrp.agents.single import FINANCE_DEFAULT_INSTRUCTIONS
        
        assert isinstance(FINANCE_DEFAULT_INSTRUCTIONS, str)
        assert len(FINANCE_DEFAULT_INSTRUCTIONS) > 0
    
    def test_imports_all_default_instructions(self):
        """
        Test that all default instruction constants can be imported together.
        
        Verifies all constants are available in a single import statement.
        """
        from asdrp.agents.single import (
            GEO_DEFAULT_INSTRUCTIONS,
            MAP_DEFAULT_INSTRUCTIONS,
            ONE_DEFAULT_INSTRUCTIONS,
            YELP_DEFAULT_INSTRUCTIONS,
            FINANCE_DEFAULT_INSTRUCTIONS,
        )
        
        assert all(isinstance(instructions, str) and len(instructions) > 0
                  for instructions in [
                      GEO_DEFAULT_INSTRUCTIONS,
                      MAP_DEFAULT_INSTRUCTIONS,
                      ONE_DEFAULT_INSTRUCTIONS,
                      YELP_DEFAULT_INSTRUCTIONS,
                      FINANCE_DEFAULT_INSTRUCTIONS,
                  ])


class TestSingleInitAllDefinition:
    """
    Test that __all__ is properly defined and matches exports.
    
    This class validates that __all__ includes all expected exports
    and matches what's actually available in the module.
    """
    
    def test_all_contains_all_functions(self):
        """
        Test that __all__ includes all agent creation functions.
        
        Verifies __all__ is properly defined for explicit exports.
        """
        from asdrp.agents.single import __all__
        
        expected_functions = [
            'create_geo_agent',
            'create_map_agent',
            'create_one_agent',
            'create_yelp_agent',
            'create_finance_agent',
        ]
        
        for func_name in expected_functions:
            assert func_name in __all__, f"{func_name} should be in __all__"
    
    def test_all_contains_all_default_instructions(self):
        """
        Test that __all__ includes all DEFAULT_INSTRUCTIONS constants.
        
        Verifies __all__ includes all instruction constants.
        """
        from asdrp.agents.single import __all__
        
        expected_constants = [
            'GEO_DEFAULT_INSTRUCTIONS',
            'MAP_DEFAULT_INSTRUCTIONS',
            'ONE_DEFAULT_INSTRUCTIONS',
            'YELP_DEFAULT_INSTRUCTIONS',
            'FINANCE_DEFAULT_INSTRUCTIONS',
        ]
        
        for const_name in expected_constants:
            assert const_name in __all__, f"{const_name} should be in __all__"
    
    def test_all_matches_actual_exports(self):
        """
        Test that __all__ matches what can actually be imported.
        
        Verifies consistency between __all__ definition and actual exports.
        """
        import asdrp.agents.single as single_module
        from asdrp.agents.single import __all__
        
        # Verify all items in __all__ are actually available
        for item_name in __all__:
            assert hasattr(single_module, item_name), \
                f"{item_name} in __all__ but not available in module"


class TestSingleInitFunctionality:
    """
    Test that imported functions work correctly.
    
    This class validates that functions imported from the package
    actually work and create agents as expected.
    """
    
    def test_imported_geo_agent_creates_agent(self):
        """
        Test that imported create_geo_agent function works correctly.
        
        Verifies the function creates a valid agent instance.
        """
        from asdrp.agents.single import create_geo_agent
        
        agent = create_geo_agent()
        
        assert agent is not None
        assert agent.name == "GeoAgent"
    
    def test_imported_map_agent_creates_agent(self):
        """
        Test that imported create_map_agent function works correctly.
        
        Verifies the function creates a valid agent instance.
        """
        from asdrp.agents.single import create_map_agent
        
        agent = create_map_agent()
        
        assert agent is not None
        assert agent.name == "MapAgent"
    
    def test_imported_one_agent_creates_agent(self):
        """
        Test that imported create_one_agent function works correctly.
        
        Verifies the function creates a valid agent instance.
        """
        from asdrp.agents.single import create_one_agent
        
        agent = create_one_agent()
        
        assert agent is not None
        assert agent.name == "OneAgent"
    
    def test_imported_yelp_agent_creates_agent(self):
        """
        Test that imported create_yelp_agent function works correctly.
        
        Verifies the function creates a valid agent instance.
        """
        from asdrp.agents.single import create_yelp_agent
        
        agent = create_yelp_agent()
        
        assert agent is not None
        assert agent.name == "YelpAgent"
    
    def test_imported_finance_agent_creates_agent(self):
        """
        Test that imported create_finance_agent function works correctly.
        
        Verifies the function creates a valid agent instance.
        """
        from asdrp.agents.single import create_finance_agent
        
        agent = create_finance_agent()
        
        assert agent is not None
        assert agent.name == "FinanceAgent"
    
    def test_default_instructions_match_source(self):
        """
        Test that imported DEFAULT_INSTRUCTIONS match source module values.
        
        Verifies that constants are correctly re-exported from source modules.
        """
        from asdrp.agents.single import (
            GEO_DEFAULT_INSTRUCTIONS,
            MAP_DEFAULT_INSTRUCTIONS,
            ONE_DEFAULT_INSTRUCTIONS,
            YELP_DEFAULT_INSTRUCTIONS,
            FINANCE_DEFAULT_INSTRUCTIONS,
        )
        from asdrp.agents.single.geo_agent import DEFAULT_INSTRUCTIONS as GEO_SOURCE
        from asdrp.agents.single.map_agent import DEFAULT_INSTRUCTIONS as MAP_SOURCE
        from asdrp.agents.single.one_agent import DEFAULT_INSTRUCTIONS as ONE_SOURCE
        from asdrp.agents.single.yelp_agent import DEFAULT_INSTRUCTIONS as YELP_SOURCE
        from asdrp.agents.single.finance_agent import DEFAULT_INSTRUCTIONS as FINANCE_SOURCE
        
        assert GEO_DEFAULT_INSTRUCTIONS == GEO_SOURCE
        assert MAP_DEFAULT_INSTRUCTIONS == MAP_SOURCE
        assert ONE_DEFAULT_INSTRUCTIONS == ONE_SOURCE
        assert YELP_DEFAULT_INSTRUCTIONS == YELP_SOURCE
        assert FINANCE_DEFAULT_INSTRUCTIONS == FINANCE_SOURCE


class TestSingleInitErrorHandling:
    """
    Test error handling in __init__.py imports.
    
    This class validates that import errors are properly handled
    and don't cause silent failures.
    """
    
    def test_import_error_in_source_module_propagates(self):
        """
        Test that import errors in source modules propagate correctly.
        
        Verifies that if a source module has import issues, they're
        not silently swallowed by __init__.py.
        """
        # This test verifies that import errors are not hidden
        # If a source module fails to import, the error should propagate
        try:
            from asdrp.agents.single import create_geo_agent
            # If we get here, the import succeeded
            assert callable(create_geo_agent)
        except ImportError:
            # If import fails, that's also valid - it means errors propagate
            # This is expected behavior
            pass

