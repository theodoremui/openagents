#############################################################################
# test_geo_tools.py
#
# Comprehensive tests for GeoTools class
#
# Test Coverage:
# - ToolsMeta integration (spec_functions, tool_list)
# - Async geocoding methods with mocked responses
# - Error handling (timeouts, service errors, invalid inputs)
# - Edge cases (empty results, invalid coordinates)
# - Input validation (coordinate ranges, empty addresses)
#
#############################################################################

import pytest
import asyncio
import importlib
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Tuple, Optional

from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.location import Location

from asdrp.actions.geo.geo_tools import GeoTools
from asdrp.actions.tools_meta import ToolsMeta


class TestGeoToolsMetaIntegration:
    """Test GeoTools integration with ToolsMeta metaclass."""
    
    def test_tools_meta_integration(self):
        """Test that GeoTools properly integrates with ToolsMeta."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        # Verify ToolsMeta attributes exist
        assert hasattr(GeoTools, 'spec_functions')
        assert hasattr(GeoTools, 'tool_list')
        assert isinstance(GeoTools.spec_functions, list)
        assert isinstance(GeoTools.tool_list, list)
        assert len(GeoTools.tool_list) == len(GeoTools.spec_functions)
    
    def test_all_methods_discovered(self):
        """Test that all public GeoTools methods are discovered."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        expected_methods = [
            'get_address_by_coordinates',
            'get_coordinates_by_address',
        ]
        
        for method in expected_methods:
            assert method in GeoTools.spec_functions, \
                f"{method} should be in spec_functions"
    
    def test_excluded_methods_not_discovered(self):
        """Test that internal methods are excluded from discovery."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        excluded = ['geocoder', '_setup_class', '_get_excluded_methods']
        for attr in excluded:
            assert attr not in GeoTools.spec_functions, \
                f"{attr} should not be in spec_functions"


class TestGeoToolsInitialization:
    """Test GeoTools class initialization and setup."""
    
    def test_setup_class_initializes_geocoder(self):
        """Test that _setup_class initializes ArcGIS geocoder."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        from geopy.geocoders import ArcGIS
        
        assert hasattr(GeoTools, 'geocoder')
        assert isinstance(GeoTools.geocoder, ArcGIS)
    
    def test_geocoder_timeout_configuration(self):
        """Test that geocoder is initialized with correct timeout."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools, TIMEOUT_SECONDS
        
        assert GeoTools.geocoder.timeout == TIMEOUT_SECONDS


class TestGeoToolsGetCoordinatesByAddress:
    """Test GeoTools.get_coordinates_by_address method."""
    
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_success(self):
        """Test successful geocoding of address to coordinates."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        # Create a mock location
        mock_location = MagicMock()
        mock_location.latitude = 37.4221
        mock_location.longitude = -122.0841
        mock_location.address = "1600 Amphitheatre Parkway, Mountain View, CA"
        
        # Mock asyncio.get_running_loop and run_in_executor
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_location)
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            lat, lon = await GeoTools.get_coordinates_by_address(
                "1600 Amphitheatre Parkway, Mountain View, CA"
            )
            
            assert lat == 37.4221
            assert lon == -122.0841
            # Verify geocoder.geocode was called via run_in_executor
            assert mock_loop.run_in_executor.called
    
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_not_found(self):
        """Test geocoding when address is not found."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        # Mock geocoder returning None (address not found)
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            lat, lon = await GeoTools.get_coordinates_by_address("Invalid Address XYZ 99999")
            
            # Should return error coordinates
            assert lat == -1.0
            assert lon == -1.0
    
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_empty_string(self):
        """Test that empty address raises ValueError."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        with pytest.raises(ValueError, match="Address cannot be empty or None"):
            await GeoTools.get_coordinates_by_address("")
    
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_whitespace_only(self):
        """Test that whitespace-only address raises ValueError."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        with pytest.raises(ValueError, match="Address cannot be empty or None"):
            await GeoTools.get_coordinates_by_address("   ")
    
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_none(self):
        """Test that None address raises ValueError."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        with pytest.raises(ValueError, match="Address cannot be empty or None"):
            await GeoTools.get_coordinates_by_address(None)
    
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_timeout(self):
        """Test handling of GeocoderTimedOut exception."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=GeocoderTimedOut("Timeout"))
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(GeocoderTimedOut, match="Geocoding timed out"):
                await GeoTools.get_coordinates_by_address("Test Address")
    
    @pytest.mark.asyncio
    async def test_get_coordinates_by_address_service_error(self):
        """Test handling of GeocoderServiceError exception."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=GeocoderServiceError("Service error")
        )
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(GeocoderServiceError, match="Geocoding service error"):
                await GeoTools.get_coordinates_by_address("Test Address")


class TestGeoToolsGetAddressByCoordinates:
    """Test GeoTools.get_address_by_coordinates method."""
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_success(self):
        """Test successful reverse geocoding of coordinates to address."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        # Create a mock location
        mock_location = MagicMock()
        mock_location.address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_location)
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            address = await GeoTools.get_address_by_coordinates(37.4221, -122.0841)
            
            assert address == "1600 Amphitheatre Parkway, Mountain View, CA 94043"
            # Verify geocoder.reverse was called via run_in_executor
            assert mock_loop.run_in_executor.called
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_not_found(self):
        """Test reverse geocoding when no address is found."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        # Mock geocoder returning None
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            address = await GeoTools.get_address_by_coordinates(0.0, 0.0)
            
            assert address is None
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_invalid_latitude_too_high(self):
        """Test that latitude > 90 raises ValueError."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            await GeoTools.get_address_by_coordinates(91.0, 0.0)
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_invalid_latitude_too_low(self):
        """Test that latitude < -90 raises ValueError."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            await GeoTools.get_address_by_coordinates(-91.0, 0.0)
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_invalid_longitude_too_high(self):
        """Test that longitude > 180 raises ValueError."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            await GeoTools.get_address_by_coordinates(0.0, 181.0)
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_invalid_longitude_too_low(self):
        """Test that longitude < -180 raises ValueError."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            await GeoTools.get_address_by_coordinates(0.0, -181.0)
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_boundary_values(self):
        """Test that boundary coordinate values are accepted."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            # Test boundary values (should not raise ValueError)
            await GeoTools.get_address_by_coordinates(90.0, 180.0)
            await GeoTools.get_address_by_coordinates(-90.0, -180.0)
            await GeoTools.get_address_by_coordinates(0.0, 0.0)
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_timeout(self):
        """Test handling of GeocoderTimedOut exception."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=GeocoderTimedOut("Timeout"))
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(GeocoderTimedOut, match="Reverse geocoding timed out"):
                await GeoTools.get_address_by_coordinates(37.4221, -122.0841)
    
    @pytest.mark.asyncio
    async def test_get_address_by_coordinates_service_error(self):
        """Test handling of GeocoderServiceError exception."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(
            side_effect=GeocoderServiceError("Service error")
        )
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            with pytest.raises(GeocoderServiceError, match="Reverse geocoding service error"):
                await GeoTools.get_address_by_coordinates(37.4221, -122.0841)


class TestGeoToolsIntegration:
    """Integration tests for GeoTools round-trip operations."""
    
    @pytest.mark.asyncio
    async def test_round_trip_geocoding(self):
        """Test round-trip: address -> coordinates -> address."""
        import importlib
        import asdrp.actions.geo.geo_tools
        importlib.reload(asdrp.actions.geo.geo_tools)
        from asdrp.actions.geo.geo_tools import GeoTools
        
        # Mock forward geocoding
        forward_location = MagicMock()
        forward_location.latitude = 37.4221
        forward_location.longitude = -122.0841
        
        # Mock reverse geocoding
        reverse_location = MagicMock()
        reverse_location.address = "Test Address"
        
        mock_loop = MagicMock()
        
        # First call returns forward location, second returns reverse location
        mock_loop.run_in_executor = AsyncMock(side_effect=[
            forward_location,
            reverse_location
        ])
        
        with patch('asdrp.actions.geo.geo_tools.asyncio.get_running_loop', return_value=mock_loop):
            # Forward geocoding
            lat, lon = await GeoTools.get_coordinates_by_address("Test Address")
            assert lat == 37.4221
            assert lon == -122.0841
            
            # Reverse geocoding
            address = await GeoTools.get_address_by_coordinates(lat, lon)
            assert address == "Test Address"

