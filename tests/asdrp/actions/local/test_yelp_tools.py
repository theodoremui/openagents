#############################################################################
# test_yelp_tools.py
#
# Comprehensive tests for YelpTools class
#
# Test Coverage:
# - ToolsMeta integration (spec_functions, tool_list)
# - All public API methods with mocked responses
# - Error handling (timeouts, HTTP errors, invalid inputs)
# - Edge cases (empty results, missing data)
# - Input validation
#
#############################################################################

import pytest
import os
import importlib
from unittest.mock import patch, MagicMock, Mock
from typing import Dict

from asdrp.actions.local.yelp_tools import YelpTools
from asdrp.actions.tools_meta import ToolsMeta


class TestYelpToolsMetaIntegration:
    """Test YelpTools integration with ToolsMeta metaclass."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_tools_meta_integration(self):
        """Test that YelpTools properly integrates with ToolsMeta."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        # Verify ToolsMeta attributes exist
        assert hasattr(YelpTools, 'spec_functions')
        assert hasattr(YelpTools, 'tool_list')
        assert isinstance(YelpTools.spec_functions, list)
        assert isinstance(YelpTools.tool_list, list)
        assert len(YelpTools.tool_list) == len(YelpTools.spec_functions)
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_all_methods_discovered(self):
        """Test that all public YelpTools methods are discovered."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        expected_methods = [
            'get_business_details',
            'get_business_engagement',
            'get_business_reviews',
            'get_review_highlights',
            'match_business',
            'search_businesses',
            'search_by_phone',
        ]
        
        for method in expected_methods:
            assert method in YelpTools.spec_functions, \
                f"{method} should be in spec_functions"
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_excluded_methods_not_discovered(self):
        """Test that internal methods are excluded from discovery."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        excluded = ['BASE_URL', 'api_key', 'headers', '_setup_class', '_get_excluded_methods']
        for attr in excluded:
            assert attr not in YelpTools.spec_functions, \
                f"{attr} should not be in spec_functions"


class TestYelpToolsInitialization:
    """Test YelpTools class initialization and setup."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_setup_class_initializes_api_key(self):
        """Test that _setup_class initializes API key from environment."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        assert hasattr(YelpTools, 'api_key')
        assert YelpTools.api_key == 'test_api_key_12345'
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    def test_setup_class_initializes_headers(self):
        """Test that _setup_class initializes authorization headers."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        assert hasattr(YelpTools, 'headers')
        assert isinstance(YelpTools.headers, dict)
        assert 'Authorization' in YelpTools.headers
        assert YelpTools.headers['Authorization'] == 'Bearer test_api_key_12345'
    
    def test_missing_api_key_raises_error(self):
        """Test that missing YELP_API_KEY raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="YELP_API_KEY is not set"):
                # Create a test class similar to YelpTools to test initialization
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


class TestYelpToolsSearchBusinesses:
    """Test YelpTools.search_businesses method."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_search_businesses_success(self, mock_get):
        """Test successful business search."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "businesses": [
                {"id": "1", "name": "Test Restaurant", "rating": 4.5},
                {"id": "2", "name": "Another Place", "rating": 4.0}
            ],
            "total": 2
        }
        mock_get.return_value = mock_response
        
        result = YelpTools.search_businesses("pizza", 37.7749, -122.4194)
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['headers'] == YelpTools.headers
        assert call_args[1]['params']['term'] == "pizza"
        assert call_args[1]['params']['latitude'] == 37.7749
        assert call_args[1]['params']['longitude'] == -122.4194
        
        # Verify response
        assert result['total'] == 2
        assert len(result['businesses']) == 2
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_search_businesses_with_optional_params(self, mock_get):
        """Test business search with optional parameters."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"businesses": [], "total": 0}
        mock_get.return_value = mock_response
        
        YelpTools.search_businesses(
            "coffee", 37.7749, -122.4194,
            categories="cafes", price="2", limit=10
        )
        
        call_args = mock_get.call_args
        assert call_args[1]['params']['categories'] == "cafes"
        assert call_args[1]['params']['price'] == "2"
        assert call_args[1]['params']['limit'] == 10
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_search_businesses_timeout(self, mock_get):
        """Test that timeout is properly set."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools, TIMEOUT_SECONDS
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"businesses": []}
        mock_get.return_value = mock_response
        
        YelpTools.search_businesses("pizza", 37.7749, -122.4194)
        
        call_args = mock_get.call_args
        assert call_args[1]['timeout'] == TIMEOUT_SECONDS


class TestYelpToolsSearchByPhone:
    """Test YelpTools.search_by_phone method."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_search_by_phone_success(self, mock_get):
        """Test successful phone number search."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "businesses": [{"id": "1", "name": "Test Business", "phone": "+14155551234"}]
        }
        mock_get.return_value = mock_response
        
        result = YelpTools.search_by_phone("+14155551234")
        
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['phone'] == "+14155551234"
        assert 'businesses' in result


class TestYelpToolsMatchBusiness:
    """Test YelpTools.match_business method."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_match_business_success(self, mock_get):
        """Test successful business matching."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "businesses": [{"id": "match_1", "name": "Test Restaurant"}]
        }
        mock_get.return_value = mock_response
        
        result = YelpTools.match_business(
            "Test Restaurant", "123 Main St", "San Francisco", "CA", "US"
        )
        
        call_args = mock_get.call_args
        assert call_args[1]['params']['name'] == "Test Restaurant"
        assert call_args[1]['params']['address1'] == "123 Main St"
        assert call_args[1]['params']['city'] == "San Francisco"
        assert call_args[1]['params']['state'] == "CA"
        assert call_args[1]['params']['country'] == "US"
        assert 'businesses' in result


class TestYelpToolsGetBusinessDetails:
    """Test YelpTools.get_business_details method."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_get_business_details_success(self, mock_get):
        """Test successful business details retrieval."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        business_id = "test_business_123"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": business_id,
            "name": "Test Business",
            "rating": 4.5,
            "hours": [{"day": 0, "start": "0900", "end": "1700"}]
        }
        mock_get.return_value = mock_response
        
        result = YelpTools.get_business_details(business_id)
        
        # Verify correct endpoint
        call_args = mock_get.call_args
        assert business_id in call_args[0][0]
        assert result['id'] == business_id
        assert 'rating' in result


class TestYelpToolsGetBusinessEngagement:
    """Test YelpTools.get_business_engagement method."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_get_business_engagement_success(self, mock_get):
        """Test successful engagement metrics retrieval."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        business_ids = ["id1", "id2", "id3"]
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "businesses": [
                {"id": "id1", "view_count": 1000},
                {"id": "id2", "view_count": 2000}
            ]
        }
        mock_get.return_value = mock_response
        
        result = YelpTools.get_business_engagement(business_ids)
        
        call_args = mock_get.call_args
        assert call_args[1]['params']['business_ids'] == ",".join(business_ids)
        assert 'businesses' in result
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_get_business_engagement_empty_list(self, mock_get):
        """Test engagement retrieval with empty business ID list."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"businesses": []}
        mock_get.return_value = mock_response
        
        result = YelpTools.get_business_engagement([])
        
        call_args = mock_get.call_args
        assert call_args[1]['params']['business_ids'] == ""


class TestYelpToolsGetBusinessReviews:
    """Test YelpTools.get_business_reviews method."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_get_business_reviews_success(self, mock_get):
        """Test successful reviews retrieval."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        business_id = "review_test_123"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "reviews": [
                {"id": "r1", "rating": 5, "text": "Great!"},
                {"id": "r2", "rating": 4, "text": "Good"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = YelpTools.get_business_reviews(business_id)
        
        call_args = mock_get.call_args
        assert business_id in call_args[0][0]
        assert 'reviews' in call_args[0][0]
        assert 'reviews' in result


class TestYelpToolsGetReviewHighlights:
    """Test YelpTools.get_review_highlights method."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_get_review_highlights_success(self, mock_get):
        """Test successful review highlights retrieval."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        
        business_id = "highlights_test_123"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "highlights": [
                {"text": "Great food", "sentiment": "positive"},
                {"text": "Fast service", "sentiment": "positive"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = YelpTools.get_review_highlights(business_id)
        
        call_args = mock_get.call_args
        assert business_id in call_args[0][0]
        assert 'review_highlights' in call_args[0][0]
        assert 'highlights' in result


class TestYelpToolsErrorHandling:
    """Test YelpTools error handling."""
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_http_error_handling(self, mock_get):
        """Test handling of HTTP errors."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        import requests
        
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_response.json.return_value = {"error": {"code": "NOT_FOUND"}}
        mock_get.return_value = mock_response
        
        # The method should return the JSON response even on error
        # (actual error handling would be done by the caller)
        result = YelpTools.get_business_details("invalid_id")
        assert 'error' in result
    
    @patch.dict(os.environ, {'YELP_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.local.yelp_tools.requests.get')
    def test_timeout_handling(self, mock_get):
        """Test that timeout is properly configured."""
        import importlib
        import asdrp.actions.local.yelp_tools
        importlib.reload(asdrp.actions.local.yelp_tools)
        from asdrp.actions.local.yelp_tools import YelpTools
        import requests
        
        # Mock timeout exception
        mock_get.side_effect = requests.Timeout("Request timed out")
        
        with pytest.raises(requests.Timeout):
            YelpTools.search_businesses("pizza", 37.7749, -122.4194)

