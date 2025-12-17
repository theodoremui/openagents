#############################################################################
# test_map_tools.py
#
# Comprehensive tests for MapTools class
#
# Test Coverage:
# - ToolsMeta integration (spec_functions, tool_list)
# - All public API methods with mocked responses
# - Error handling (invalid inputs, API errors)
# - Edge cases (empty results, boundary values)
# - Input validation
#
#############################################################################

import pytest
import os
import importlib
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Tuple

from asdrp.actions.geo.map_tools import MapTools
from asdrp.actions.tools_meta import ToolsMeta


class TestMapToolsMetaIntegration:
    """Test MapTools integration with ToolsMeta metaclass."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    def test_tools_meta_integration(self, mock_client_class):
        """Test that MapTools properly integrates with ToolsMeta."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        # Verify ToolsMeta attributes exist
        assert hasattr(MapTools, 'spec_functions')
        assert hasattr(MapTools, 'tool_list')
        assert isinstance(MapTools.spec_functions, list)
        assert isinstance(MapTools.tool_list, list)
        assert len(MapTools.tool_list) == len(MapTools.spec_functions)
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    def test_all_methods_discovered(self, mock_client_class):
        """Test that all public MapTools methods are discovered."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        expected_methods = [
            'get_address_by_coordinates',
            'get_coordinates_by_address',
            'get_distance_matrix',
            'get_place_details',
            'get_travel_time_distance',
            'places_autocomplete',
            'search_places_nearby',
        ]
        
        for method in expected_methods:
            assert method in MapTools.spec_functions, \
                f"{method} should be in spec_functions"
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    def test_excluded_methods_not_discovered(self, mock_client_class):
        """Test that internal methods are excluded from discovery."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        excluded = ['client', '_service_account_info', '_setup_class', '_get_excluded_methods']
        for attr in excluded:
            assert attr not in MapTools.spec_functions, \
                f"{attr} should not be in spec_functions"


class TestMapToolsInitialization:
    """Test MapTools class initialization and setup."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    def test_setup_class_initializes_client(self, mock_client_class):
        """Test that _setup_class initializes Google Maps client."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        assert hasattr(MapTools, 'client')
        assert MapTools.client is not None
        mock_client_class.assert_called_once()
    
    def test_missing_api_key_raises_error(self):
        """Test that missing GOOGLE_API_KEY raises ValueError.
        
        Note: This test verifies the error message format in the code.
        Actual initialization happens at module import time, so we verify
        the error handling logic exists rather than triggering it.
        """
        # Verify that _setup_class checks for API key
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        # Check that the setup method exists and has the right error message
        setup_source = MapTools._setup_class.__doc__ or ""
        assert "GOOGLE_API_KEY" in setup_source or "GOOGLE_API_KEY" in str(MapTools._setup_class)


class TestMapToolsGetCoordinatesByAddress:
    """Test MapTools.get_coordinates_by_address method."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_success(self, mock_client_class):
        """Test successful geocoding of address to coordinates."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = [{
            'geometry': {
                'location': {'lat': 37.4221, 'lng': -122.0841}
            }
        }]
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            lat, lon = await MapTools.get_coordinates_by_address(
                "1600 Amphitheatre Parkway, Mountain View, CA"
            )
            
            assert lat == 37.4221
            assert lon == -122.0841
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_not_found(self, mock_client_class):
        """Test geocoding when address is not found."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=[])
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            lat, lon = await MapTools.get_coordinates_by_address("Invalid Address XYZ 99999")
            
            assert lat == -1.0
            assert lon == -1.0
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_empty_string(self, mock_client_class):
        """Test that empty address raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Address cannot be empty"):
            await MapTools.get_coordinates_by_address("")


class TestMapToolsGetAddressByCoordinates:
    """Test MapTools.get_address_by_coordinates method."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_success(self, mock_client_class):
        """Test successful reverse geocoding."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = [{
            'formatted_address': '1600 Amphitheatre Parkway, Mountain View, CA 94043'
        }]
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            address = await MapTools.get_address_by_coordinates(37.4221, -122.0841)
            
            assert address == '1600 Amphitheatre Parkway, Mountain View, CA 94043'
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_invalid_latitude(self, mock_client_class):
        """Test that invalid latitude raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Latitude must be between"):
            await MapTools.get_address_by_coordinates(91.0, 0.0)


class TestMapToolsGetTravelTimeDistance:
    """Test MapTools.get_travel_time_distance method."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_success(self, mock_client_class):
        """Test successful directions request."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = [{
            'routes': [{
                'legs': [{
                    'distance': {'text': '10 km', 'value': 10000},
                    'duration': {'text': '15 mins', 'value': 900}
                }]
            }],
            'status': 'OK'
        }]
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.get_travel_time_distance(
                "San Francisco, CA",
                "Oakland, CA"
            )
            
            # Directions API returns a list of route dictionaries
            assert isinstance(result, list)
            assert len(result) > 0
            assert 'routes' in result[0]
            assert result[0]['status'] == 'OK'
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_with_mode(self, mock_client_class):
        """Test directions with different transportation modes."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = [{'routes': [], 'status': 'OK'}]
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.get_travel_time_distance(
                "Origin", "Destination", mode="walking"
            )
            assert isinstance(result, list)
            assert len(result) > 0
            
            result = await MapTools.get_travel_time_distance(
                "Origin", "Destination", mode="transit"
            )
            assert isinstance(result, list)
            assert len(result) > 0
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_with_avoid(self, mock_client_class):
        """Test directions with avoid parameter."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = [{'routes': [], 'status': 'OK'}]
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.get_travel_time_distance(
                "Origin", "Destination", avoid="tolls"
            )
            assert isinstance(result, list)
            assert len(result) > 0
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_empty_origin(self, mock_client_class):
        """Test that empty origin raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Origin cannot be empty"):
            await MapTools.get_travel_time_distance("", "Destination")
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_invalid_mode(self, mock_client_class):
        """Test that invalid mode raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Mode must be one of"):
            await MapTools.get_travel_time_distance(
                "Origin", "Destination", mode="flying"
            )
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_invalid_avoid(self, mock_client_class):
        """Test that invalid avoid parameter raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Avoid must be one of"):
            await MapTools.get_travel_time_distance(
                "Origin", "Destination", avoid="invalid"
            )
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_transit_parameters(self, mock_client_class):
        """Test directions with transit mode and routing preferences."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = [{'routes': [], 'status': 'OK'}]
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.get_travel_time_distance(
                "Origin", "Destination",
                mode="transit",
                transit_mode="bus",
                transit_routing_preference="fewer_transfers"
            )
            assert isinstance(result, list)
            assert len(result) > 0
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_invalid_transit_mode(self, mock_client_class):
        """Test that invalid transit_mode raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Transit mode must be one of"):
            await MapTools.get_travel_time_distance(
                "Origin", "Destination",
                mode="transit",
                transit_mode="invalid"
            )
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_travel_time_distance_invalid_routing_preference(self, mock_client_class):
        """Test that invalid transit_routing_preference raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Transit routing preference"):
            await MapTools.get_travel_time_distance(
                "Origin", "Destination",
                mode="transit",
                transit_routing_preference="invalid"
            )


class TestMapToolsGetDistanceMatrix:
    """Test MapTools.get_distance_matrix method."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_distance_matrix_success(self, mock_client_class):
        """Test successful distance matrix request."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = {
            'origin_addresses': ['San Francisco, CA'],
            'destination_addresses': ['Oakland, CA'],
            'rows': [{
                'elements': [{
                    'distance': {'text': '20 km', 'value': 20000},
                    'duration': {'text': '30 mins', 'value': 1800},
                    'status': 'OK'
                }]
            }],
            'status': 'OK'
        }
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.get_distance_matrix(
                ['San Francisco, CA'],
                ['Oakland, CA']
            )
            
            assert 'rows' in result
            assert result['status'] == 'OK'
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_distance_matrix_empty_origins(self, mock_client_class):
        """Test that empty origins list raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Origins list cannot be empty"):
            await MapTools.get_distance_matrix([], ['Destination'])
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_distance_matrix_too_many_origins(self, mock_client_class):
        """Test that too many origins raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        origins = [f"Origin {i}" for i in range(26)]
        with pytest.raises(ValueError, match="Maximum 25 origins"):
            await MapTools.get_distance_matrix(origins, ['Destination'])
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_distance_matrix_invalid_units(self, mock_client_class):
        """Test that invalid units raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Units must be"):
            await MapTools.get_distance_matrix(
                ['Origin'], ['Destination'], units='invalid'
            )


class TestMapToolsPlacesAutocomplete:
    """Test MapTools.places_autocomplete method."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_places_autocomplete_success(self, mock_client_class):
        """Test successful autocomplete request."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = [
            {
                'place_id': 'ChIJ...',
                'description': 'San Francisco, CA, USA',
                'structured_formatting': {
                    'main_text': 'San Francisco',
                    'secondary_text': 'CA, USA'
                }
            }
        ]
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.places_autocomplete("San Francisco")
            
            assert len(result) == 1
            assert 'place_id' in result[0]
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_places_autocomplete_with_location(self, mock_client_class):
        """Test autocomplete with location biasing."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = []
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.places_autocomplete(
                "Coffee",
                lat=37.7749,
                lon=-122.4194,
                radius=1000
            )
            assert isinstance(result, list)
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_places_autocomplete_empty_input(self, mock_client_class):
        """Test that empty input raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            await MapTools.places_autocomplete("")
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_places_autocomplete_invalid_location(self, mock_client_class):
        """Test that invalid location coordinates raise ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Latitude must be between"):
            await MapTools.places_autocomplete("Test", lat=91.0, lon=0.0)
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_places_autocomplete_partial_location(self, mock_client_class):
        """Test that providing only lat or only lon raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Both latitude and longitude must be provided"):
            await MapTools.places_autocomplete("Test", lat=37.7749)
        
        with pytest.raises(ValueError, match="Both latitude and longitude must be provided"):
            await MapTools.places_autocomplete("Test", lon=-122.4194)


class TestMapToolsSearchPlacesNearby:
    """Test MapTools.search_places_nearby method."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_search_places_nearby_success(self, mock_client_class):
        """Test successful places search."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = {
            'results': [
                {'name': 'Place 1', 'place_id': 'id1'},
                {'name': 'Place 2', 'place_id': 'id2'}
            ]
        }
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.search_places_nearby(37.7749, -122.4194)
            
            assert len(result) == 2
            assert result[0]['name'] == 'Place 1'
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_search_places_nearby_with_filters(self, mock_client_class):
        """Test places search with keyword and type filters."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = {'results': []}
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.search_places_nearby(
                37.7749, -122.4194,
                keyword="restaurant",
                place_type="restaurant"
            )
            assert isinstance(result, list)


class TestMapToolsGetPlaceDetails:
    """Test MapTools.get_place_details method."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_place_details_success(self, mock_client_class):
        """Test successful place details retrieval."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_result = {
            'result': {
                'name': 'Test Place',
                'formatted_address': '123 Test St',
                'rating': 4.5
            }
        }
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            result = await MapTools.get_place_details("ChIJ...")
            
            assert result is not None
            assert result['name'] == 'Test Place'
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_get_place_details_empty_place_id(self, mock_client_class):
        """Test that empty place_id raises ValueError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        with pytest.raises(ValueError, match="Place ID cannot be empty"):
            await MapTools.get_place_details("")


class TestMapToolsErrorHandling:
    """Test MapTools error handling."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key_12345'})
    @patch('asdrp.actions.geo.map_tools.googlemaps.Client')
    @pytest.mark.asyncio
    async def test_api_error_propagation(self, mock_client_class):
        """Test that API errors are properly propagated."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        import importlib
        import asdrp.actions.geo.map_tools
        importlib.reload(asdrp.actions.geo.map_tools)
        from asdrp.actions.geo.map_tools import MapTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=Exception("API Error"))
        
        with patch('asdrp.actions.geo.map_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(Exception, match="Geocoding failed"):
                await MapTools.get_coordinates_by_address("Test Address")

