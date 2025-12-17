#############################################################################
# geo_tools.py
#
# Geocoding tools using geopy
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import asyncio
from typing import Any, List, Optional, Tuple

from geopy.geocoders import ArcGIS
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from asdrp.actions.tools_meta import ToolsMeta

# Timeout for geocoding operations
TIMEOUT_SECONDS = 30


class GeoTools(metaclass=ToolsMeta):
    """
    Tools for geocoding and reverse geocoding using ArcGIS geocoding service.
    
    This class uses the ToolsMeta metaclass which automatically:
    - Discovers all public @classmethod decorated methods
    - Creates `spec_functions` list containing method names
    - Creates `tool_list` containing wrapped function tools ready for agent frameworks
    
    Geocoding service initialization is handled via the `_setup_class()` hook method.
    
    Usage:
    ------
    ```python
    from asdrp.actions.geo.geo_tools import GeoTools
    
    # Use the automatically generated tool_list
    from agents import Agent
    agent = Agent(tools=GeoTools.tool_list)
    
    # Or call methods directly
    lat, lon = await GeoTools.get_coordinates_by_address("1600 Amphitheatre Parkway, Mountain View, CA")
    address = await GeoTools.get_address_by_coordinates(37.4221, -122.0841)
    ```
    """
    # Class variables for geocoder configuration (set by _setup_class)
    geocoder: ArcGIS
    
    # ------------- Automatically populated by ToolsMeta -------------
    # List of method names & wrapped function tools to expose as tools
    spec_functions: List[str]
    tool_list: List[Any]
    
    @classmethod
    def _setup_class(cls) -> None:
        """
        Set up ArcGIS geocoder instance.
        
        This method is called automatically by ToolsMeta during class creation.
        It initializes the ArcGIS geocoder with appropriate timeout settings.
        """
        cls.geocoder = ArcGIS(timeout=TIMEOUT_SECONDS)
    
    @classmethod
    def _get_excluded_methods(cls) -> set[str]:
        """
        Exclude geocoder instance from tool discovery.
        
        Returns:
            Set of attribute names to exclude from being discovered as tools.
            This ensures that internal configuration attributes (geocoder) 
            are not included in the tool_list.
        """
        return {'geocoder'}
    
    @classmethod
    async def get_coordinates_by_address(cls, address: str) -> Tuple[float, float]:
        """
        Retrieves the geographical coordinates for a given address using ArcGIS
        geocoding service.
        
        Args:
            address (str): The address to geocode. Should be a well-formed address string.
            
        Returns:
            Tuple[float, float]: A tuple containing (latitude, longitude).
                Returns (-1.0, -1.0) if geocoding fails.
                
        Raises:
            GeocoderTimedOut: If the geocoding service times out.
            GeocoderServiceError: If the geocoding service encounters an error.
            ValueError: If the address string is empty or None.
        """
        if not address or not address.strip():
            raise ValueError("Address cannot be empty or None.")
        
        try:
            # Use run_in_executor to run synchronous geocoding in a thread pool
            loop = asyncio.get_running_loop()
            location = await loop.run_in_executor(
                None, 
                cls.geocoder.geocode, 
                address
            )
            
            if location:
                return (location.latitude, location.longitude)
            else:
                return (-1.0, -1.0)
                
        except GeocoderTimedOut as e:
            raise GeocoderTimedOut(f"Geocoding timed out for address '{address}': {e}")
        except GeocoderServiceError as e:
            raise GeocoderServiceError(f"Geocoding service error for address '{address}': {e}")
    
    @classmethod
    async def get_address_by_coordinates(cls, lat: float, lon: float) -> Optional[str]:
        """
        Performs reverse geocoding to get an address from coordinates using ArcGIS service.
        
        Args:
            lat (float): Latitude of the location. Must be between -90 and 90.
            lon (float): Longitude of the location. Must be between -180 and 180.
            
        Returns:
            Optional[str]: The formatted address if found, None if no address could be determined.
            
        Raises:
            ValueError: If latitude or longitude are outside valid ranges.
            GeocoderTimedOut: If the geocoding service times out.
            GeocoderServiceError: If the geocoding service encounters an error.
        """
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}.")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {lon}.")
        
        try:
            # Use run_in_executor to run synchronous reverse geocoding in a thread pool
            loop = asyncio.get_running_loop()
            location = await loop.run_in_executor(
                None,
                cls.geocoder.reverse,
                (lat, lon)
            )
            
            if location:
                return location.address
            else:
                return None
                
        except GeocoderTimedOut as e:
            raise GeocoderTimedOut(f"Reverse geocoding timed out for coordinates ({lat}, {lon}): {e}")
        except GeocoderServiceError as e:
            raise GeocoderServiceError(f"Reverse geocoding service error for coordinates ({lat}, {lon}): {e}")


#---------------------------------------------
# main tests
#---------------------------------------------

async def test_geocoding():
    print("Testing get_coordinates_by_address:")
    address = "1600 Amphitheatre Parkway, Mountain View, CA"
    try:
        lat, lon = await GeoTools.get_coordinates_by_address(address)
        print(f"Coordinates for '{address}': ({lat}, {lon})")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nTesting get_address_by_coordinates:")
    test_lat, test_lon = 37.4221, -122.0841
    try:
        result_address = await GeoTools.get_address_by_coordinates(test_lat, test_lon)
        print(f"Address for ({test_lat}, {test_lon}): {result_address}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_geocoding())

