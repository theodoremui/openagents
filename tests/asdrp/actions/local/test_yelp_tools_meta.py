#############################################################################
# test_yelp_tools_meta.py
#
# Tests for YelpTools using ToolsMeta directly
#
#############################################################################

import pytest
import os
from unittest.mock import patch
from typing import Dict

from asdrp.actions.local.yelp_tools import YelpTools
from asdrp.actions.tools_meta import ToolsMeta


class TestYelpToolsWithToolsMeta:
    """Test YelpTools using ToolsMeta directly."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_api_key_initialization(self):
        """Test that API key is initialized from environment via _setup_class."""
        # Re-import to ensure fresh class creation with mocked env
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        assert hasattr(YelpTools, 'api_key')
        assert YelpTools.api_key == 'test_api_key_12345'
        assert hasattr(YelpTools, 'headers')
        assert YelpTools.headers == {"Authorization": "Bearer test_api_key_12345"}
    
    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="YELP_API_KEY is not set"):
                # Create a test class similar to YelpTools
                class TestYelpTools(metaclass=ToolsMeta):
                    BASE_URL = "https://api.yelp.com/v3"
                    
                    @classmethod
                    def _setup_class(cls) -> None:
                        api_key = os.getenv("YELP_API_KEY")
                        if not api_key:
                            raise ValueError("YELP_API_KEY is not set.")
                        cls.api_key = api_key
                        cls.headers = {"Authorization": f"Bearer {cls.api_key}"}
                    
                    @classmethod
                    def test_method(cls) -> Dict:
                        return {}
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_custom_excluded_methods(self):
        """Test that Yelp-specific attributes are excluded via _get_excluded_methods."""
        # Re-import to ensure fresh class creation
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        # Check that Yelp-specific attributes are excluded
        assert 'api_key' not in YelpTools.spec_functions
        assert 'headers' not in YelpTools.spec_functions
        assert 'BASE_URL' not in YelpTools.spec_functions
        # But public methods should be included
        assert 'search_businesses' in YelpTools.spec_functions


class TestYelpTools:
    """Test YelpTools class integration."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_yelp_tools_has_spec_functions(self):
        """Test that YelpTools has spec_functions populated."""
        # Re-import to ensure fresh class creation with mocked env
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        assert hasattr(YelpTools, 'spec_functions')
        assert isinstance(YelpTools.spec_functions, list)
        assert len(YelpTools.spec_functions) > 0
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_yelp_tools_has_tool_list(self):
        """Test that YelpTools has tool_list populated."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        assert hasattr(YelpTools, 'tool_list')
        assert isinstance(YelpTools.tool_list, list)
        assert len(YelpTools.tool_list) == len(YelpTools.spec_functions)
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_yelp_tools_methods_discovered(self):
        """Test that Yelp API methods are discovered."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        # Check that some expected methods are discovered
        expected_methods = [
            'search_businesses',
            'search_by_phone',
            'get_business_details',
            'get_business_reviews'
        ]
        
        for method in expected_methods:
            assert method in YelpTools.spec_functions, f"{method} should be in spec_functions"
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_yelp_tools_api_configuration(self):
        """Test that API key and headers are configured."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        assert hasattr(YelpTools, 'api_key')
        assert YelpTools.api_key == 'test_api_key_12345'
        assert hasattr(YelpTools, 'headers')
        assert 'Authorization' in YelpTools.headers
        assert YelpTools.headers['Authorization'] == 'Bearer test_api_key_12345'

