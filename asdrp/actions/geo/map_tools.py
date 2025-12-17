#############################################################################
# map_tools.py
#
# Google Maps tools using googlemaps library
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import asyncio
import json
import os
import time
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

# #region agent log
_DEBUG_LOG_PATH = "/Users/pmui/dev/halo/openagents/.cursor/debug.log"
def _log_debug(location: str, message: str, data: dict, hypothesis_id: str = ""):
    import json as _json
    try:
        entry = {"location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "hypothesisId": hypothesis_id}
        with open(_DEBUG_LOG_PATH, "a") as f:
            f.write(_json.dumps(entry) + "\n")
    except: pass
# #endregion

try:
    import googlemaps
    from google.oauth2 import service_account
except ImportError:
    googlemaps = None
    service_account = None

from asdrp.actions.tools_meta import ToolsMeta
from asdrp.util.dict_utils import DictUtils

# Timeout for API calls (increased from 30 to 60 seconds to reduce timeout errors)
# MapAgent often needs multiple sequential API calls, each needs sufficient time
TIMEOUT_SECONDS = 60


class MapTools(metaclass=ToolsMeta):
    """
    Tools for geocoding, reverse geocoding, and place search using Google Maps API.
    
    This class uses the ToolsMeta metaclass which automatically:
    - Discovers all public @classmethod decorated methods
    - Creates `spec_functions` list containing method names
    - Creates `tool_list` containing wrapped function tools ready for agent frameworks
    
    Google Maps client initialization is handled via the `_setup_class()` hook method.
    Uses API key authentication (required by googlemaps library).
    
    Environment Variables:
    ---------------------
    GOOGLE_API_KEY: Required. Google Maps API key for authentication.
    GOOGLE_PROJECT_ID: Optional. Google Cloud project ID (for reference).
    OAUTH_GOOGLE_CLIENT_ID: Optional. OAuth client ID (for reference).
    OAUTH_GOOGLE_CLIENT_SECRET: Optional. OAuth client secret (for reference).
    GOOGLE_SERVICE_ACCOUNT_FILE: Optional. Path to service account JSON file.
        Note: Service account info is loaded for reference but googlemaps library
        uses API key authentication. Service account may be used for other Google APIs.
    
    Usage:
    ------
    ```python
    from asdrp.actions.geo.map_tools import MapTools
    
    # Use the automatically generated tool_list
    from agents import Agent
    agent = Agent(tools=MapTools.tool_list)
    
    # Or call methods directly
    lat, lon = await MapTools.get_coordinates_by_address("1600 Amphitheatre Parkway, Mountain View, CA")
    address = await MapTools.get_address_by_coordinates(37.4221, -122.0841)
    ```
    """
    # Class variables for client configuration (set by _setup_class)
    client: Any  # googlemaps.Client
    
    # ------------- Automatically populated by ToolsMeta -------------
    # List of method names & wrapped function tools to expose as tools
    spec_functions: List[str]
    tool_list: List[Any]
    
    @classmethod
    def _setup_class(cls) -> None:
        """
        Set up Google Maps client instance.
        
        This method is called automatically by ToolsMeta during class creation.
        It initializes the Google Maps client using API key authentication.
        The googlemaps library requires an API key for authentication.
        
        Environment Variables:
        ---------------------
        GOOGLE_API_KEY: Required. Google Maps API key.
        GOOGLE_SERVICE_ACCOUNT_FILE: Optional. Path to service account JSON file.
            Note: Service account is loaded for reference but googlemaps library
            uses API key authentication. Service account info may be used for
            other Google Cloud APIs if needed.
        
        Raises:
            ImportError: If googlemaps library is not installed.
            ValueError: If GOOGLE_API_KEY is not set.
        """
        if googlemaps is None:
            raise ImportError(
                "googlemaps library is required. Install it with: pip install googlemaps"
            )
        
        # Google Maps API requires API key authentication
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable must be set.")
        
        cls.client = googlemaps.Client(key=api_key, timeout=TIMEOUT_SECONDS)
        
        # Optionally load service account file for reference or other Google APIs
        # (Note: googlemaps library doesn't use service accounts directly)
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if service_account_file and Path(service_account_file).exists():
            try:
                with open(service_account_file, 'r') as f:
                    cls._service_account_info = json.load(f)
            except Exception:
                cls._service_account_info = None
        else:
            cls._service_account_info = None
    
    @classmethod
    def _get_excluded_methods(cls) -> set[str]:
        """
        Exclude client instance and service account info from tool discovery.
        
        Returns:
            Set of attribute names to exclude from being discovered as tools.
            This ensures that internal configuration attributes (client, 
            _service_account_info) are not included in the tool_list.
        """
        return {'client', '_service_account_info'}
    
    @classmethod
    async def get_coordinates_by_address(cls, address: str) -> Tuple[float, float]:
        """
        Retrieves the geographical coordinates for a given address using Google Maps
        Geocoding API.
        
        Args:
            address (str): The address to geocode. Should be a well-formed address string.
            
        Returns:
            Tuple[float, float]: A tuple containing (latitude, longitude).
                Returns (-1.0, -1.0) if geocoding fails.
                
        Raises:
            ValueError: If the address string is empty or None.
            Exception: If the Google Maps API call fails.
        """
        # #region agent log
        _start = time.time()
        _log_debug("map_tools.py:get_coordinates_by_address:start", "Tool called", {"address": address}, "B")
        # #endregion
        if not address or not address.strip():
            raise ValueError("Address cannot be empty or None.")
        
        try:
            # Use run_in_executor to run synchronous geocoding in a thread pool
            loop = asyncio.get_running_loop()
            geocode_result = await loop.run_in_executor(
                None,
                cls.client.geocode,
                address
            )
            
            if geocode_result and len(geocode_result) > 0:
                location = geocode_result[0]['geometry']['location']
                # #region agent log
                _elapsed = time.time() - _start
                _log_debug("map_tools.py:get_coordinates_by_address:end", "Tool completed", {"elapsed_ms": int(_elapsed * 1000), "lat": location['lat'], "lng": location['lng']}, "B")
                # #endregion
                return (location['lat'], location['lng'])
            else:
                # #region agent log
                _elapsed = time.time() - _start
                _log_debug("map_tools.py:get_coordinates_by_address:end", "Tool completed - no result", {"elapsed_ms": int(_elapsed * 1000)}, "B")
                # #endregion
                return (-1.0, -1.0)
                
        except Exception as e:
            # #region agent log
            _elapsed = time.time() - _start
            _log_debug("map_tools.py:get_coordinates_by_address:error", "Tool failed", {"elapsed_ms": int(_elapsed * 1000), "error": str(e)}, "B")
            # #endregion
            raise Exception(f"Geocoding failed for address '{address}': {e}")
    
    @classmethod
    async def get_address_by_coordinates(cls, lat: float, lon: float) -> Optional[str]:
        """
        Performs reverse geocoding to get an address from coordinates using Google Maps API.
        
        Args:
            lat (float): Latitude of the location. Must be between -90 and 90.
            lon (float): Longitude of the location. Must be between -180 and 180.
            
        Returns:
            Optional[str]: The formatted address if found, None if no address could be determined.
            
        Raises:
            ValueError: If latitude or longitude are outside valid ranges.
            Exception: If the Google Maps API call fails.
        """
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}.")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {lon}.")
        
        try:
            # Use run_in_executor to run synchronous reverse geocoding in a thread pool
            loop = asyncio.get_running_loop()
            reverse_geocode_result = await loop.run_in_executor(
                None,
                cls.client.reverse_geocode,
                (lat, lon)
            )
            
            if reverse_geocode_result and len(reverse_geocode_result) > 0:
                return reverse_geocode_result[0]['formatted_address']
            else:
                return None
                
        except Exception as e:
            raise Exception(f"Reverse geocoding failed for coordinates ({lat}, {lon}): {e}")
    
    @classmethod
    async def search_places_nearby(
        cls, 
        latitude: float, 
        longitude: float, 
        keyword: Optional[str] = None,
        radius: int = 1000,
        place_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for places near a location using Google Places API.
        
        Args:
            latitude (float): Latitude of the search center. Must be between -90 and 90.
            longitude (float): Longitude of the search center. Must be between -180 and 180.
            keyword (Optional[str]): A term to be matched against all content.
            radius (int): Radius in meters (default: 1000, max: 50000).
            place_type (Optional[str]): Restricts results to places matching the specified type.
                Examples: 'restaurant', 'gas_station', 'hospital', etc.
            
        Returns:
            List[Dict[str, Any]]: List of place dictionaries containing name, location, etc.
                Returns empty list if no places found.
                
        Raises:
            ValueError: If latitude or longitude are outside valid ranges, or radius is invalid.
            Exception: If the Google Maps API call fails.
        """
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {latitude}.")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {longitude}.")
        if not (1 <= radius <= 50000):
            raise ValueError(f"Radius must be between 1 and 50000 meters, got {radius}.")
        
        try:
            loop = asyncio.get_running_loop()
            
            # Build places_nearby parameters
            places_params = DictUtils.build_params(
                location=(latitude, longitude),
                radius=radius,
                keyword=keyword,
                type=place_type
            )
            
            # Use functools.partial to pass keyword arguments
            places_result = await loop.run_in_executor(
                None,
                partial(cls.client.places_nearby, **places_params)
            )
            
            if places_result and 'results' in places_result:
                return places_result['results']
            else:
                return []
                
        except Exception as e:
            raise Exception(
                f"Places search failed for location ({latitude}, {longitude}): {e}"
            )
    
    @classmethod
    async def get_place_details(cls, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a place using its place_id.
        
        Args:
            place_id (str): The Google Places place_id for the location.
            
        Returns:
            Optional[Dict[str, Any]]: Place details dictionary containing name, address,
                phone number, rating, reviews, etc. Returns None if place not found.
                
        Raises:
            ValueError: If place_id is empty or None.
            Exception: If the Google Maps API call fails.
        """
        if not place_id or not place_id.strip():
            raise ValueError("Place ID cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            
            # Use functools.partial to pass keyword arguments
            place_result = await loop.run_in_executor(
                None,
                partial(cls.client.place, place_id=place_id)
            )
            
            if place_result and 'result' in place_result:
                return place_result['result']
            else:
                return None
                
        except Exception as e:
            raise Exception(f"Failed to get place details for place_id '{place_id}': {e}")
    
    @classmethod
    async def get_travel_time_distance(
        cls,
        origin: str,
        destination: str,
        avoid: Optional[str] = None,
        mode: str = "driving",
        transit_mode: Optional[str] = None,
        transit_routing_preference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetches travel directions between two locations using Google Maps Directions API.
        
        Args:
            origin: Starting location address or coordinates (lat,lng format).
            destination: Ending location address or coordinates (lat,lng format).
            avoid: Features to avoid in route calculation. Valid values:
                - 'tolls': Avoid toll roads
                - 'highways': Avoid highways
                - 'ferries': Avoid ferries
                - 'indoor': Avoid indoor steps
            mode: Transportation mode. Valid values:
                - 'driving': Car transportation
                - 'walking': Pedestrian routes
                - 'bicycling': Bicycle routes
                - 'transit': Public transit
            transit_mode: Preferred transit type when mode='transit'. Valid values:
                - 'bus': Bus only
                - 'subway': Subway only
                - 'train': Train only
                - 'tram': Tram only
                - 'rail': Rail only
            transit_routing_preference: Transit routing optimization. Valid values:
                - 'less_walking': Prefer less walking
                - 'fewer_transfers': Prefer fewer transfers
        
        Returns:
            Dict containing the full response from Google Directions API including:
            - routes: Available routes between locations
            - status: API response status
            - error_message: Present if API request failed
        
        Raises:
            ValueError: If origin or destination are empty or invalid.
            Exception: If the Google Maps API call fails.
        """
        # #region agent log
        _start = time.time()
        _log_debug("map_tools.py:get_travel_time_distance:start", "Tool called", {"origin": origin, "destination": destination, "mode": mode}, "A")
        # #endregion
        if not origin or not origin.strip():
            raise ValueError("Origin cannot be empty or None.")
        if not destination or not destination.strip():
            raise ValueError("Destination cannot be empty or None.")
        
        # Validate mode
        valid_modes = ['driving', 'walking', 'bicycling', 'transit']
        if mode not in valid_modes:
            raise ValueError(f"Mode must be one of {valid_modes}, got '{mode}'.")
        
        # Validate avoid parameter
        if avoid:
            valid_avoids = ['tolls', 'highways', 'ferries', 'indoor']
            if avoid not in valid_avoids:
                raise ValueError(f"Avoid must be one of {valid_avoids}, got '{avoid}'.")
        
        # Validate transit_mode
        if transit_mode:
            valid_transit_modes = ['bus', 'subway', 'train', 'tram', 'rail']
            if transit_mode not in valid_transit_modes:
                raise ValueError(
                    f"Transit mode must be one of {valid_transit_modes}, got '{transit_mode}'."
                )
        
        # Validate transit_routing_preference
        if transit_routing_preference:
            valid_prefs = ['less_walking', 'fewer_transfers']
            if transit_routing_preference not in valid_prefs:
                raise ValueError(
                    f"Transit routing preference must be one of {valid_prefs}, "
                    f"got '{transit_routing_preference}'."
                )
        
        try:
            loop = asyncio.get_running_loop()
            
            # Build directions parameters
            directions_params = DictUtils.build_params(
                origin=origin,
                destination=destination,
                mode=mode,
                avoid=avoid,
                transit_mode=transit_mode,
                transit_routing_preference=transit_routing_preference
            )
            
            # Use functools.partial to pass keyword arguments
            directions_result = await loop.run_in_executor(
                None,
                partial(cls.client.directions, **directions_params)
            )
            
            # #region agent log
            _elapsed = time.time() - _start
            _log_debug("map_tools.py:get_travel_time_distance:end", "Tool completed", {"elapsed_ms": int(_elapsed * 1000), "has_result": bool(directions_result)}, "A")
            # #endregion
            return directions_result if directions_result else []
            
        except Exception as e:
            # #region agent log
            _elapsed = time.time() - _start
            _log_debug("map_tools.py:get_travel_time_distance:error", "Tool failed", {"elapsed_ms": int(_elapsed * 1000), "error": str(e)}, "A")
            # #endregion
            raise Exception(
                f"Directions API call failed from '{origin}' to '{destination}': {e}"
            )
    
    @classmethod
    async def get_distance_matrix(
        cls,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        avoid: Optional[str] = None,
        units: str = "metric"
    ) -> Dict[str, Any]:
        """
        Calculate travel distance and time for multiple origin-destination pairs.
        
        Args:
            origins: List of origin addresses or coordinates.
            destinations: List of destination addresses or coordinates.
            mode: Transportation mode. Valid values: 'driving', 'walking', 'bicycling', 'transit'.
            avoid: Features to avoid. Valid values: 'tolls', 'highways', 'ferries', 'indoor'.
            units: Unit system. Valid values: 'metric' (km) or 'imperial' (miles).
        
        Returns:
            Dict containing distance matrix with:
            - origin_addresses: List of origin addresses
            - destination_addresses: List of destination addresses
            - rows: List of distance/time data for each origin-destination pair
            - status: API response status
        
        Raises:
            ValueError: If inputs are invalid.
            Exception: If the API call fails.
        """
        if not origins or len(origins) == 0:
            raise ValueError("Origins list cannot be empty.")
        if not destinations or len(destinations) == 0:
            raise ValueError("Destinations list cannot be empty.")
        if len(origins) > 25:
            raise ValueError("Maximum 25 origins allowed per request.")
        if len(destinations) > 25:
            raise ValueError("Maximum 25 destinations allowed per request.")
        
        valid_modes = ['driving', 'walking', 'bicycling', 'transit']
        if mode not in valid_modes:
            raise ValueError(f"Mode must be one of {valid_modes}, got '{mode}'.")
        
        if avoid:
            valid_avoids = ['tolls', 'highways', 'ferries', 'indoor']
            if avoid not in valid_avoids:
                raise ValueError(f"Avoid must be one of {valid_avoids}, got '{avoid}'.")
        
        if units not in ['metric', 'imperial']:
            raise ValueError(f"Units must be 'metric' or 'imperial', got '{units}'.")
        
        try:
            loop = asyncio.get_running_loop()
            
            distance_params = DictUtils.build_params(
                origins=origins,
                destinations=destinations,
                mode=mode,
                units=units,
                avoid=avoid
            )
            
            # Use functools.partial to pass keyword arguments
            distance_result = await loop.run_in_executor(
                None,
                partial(cls.client.distance_matrix, **distance_params)
            )
            
            return distance_result if distance_result else {
                'origin_addresses': [],
                'destination_addresses': [],
                'rows': [],
                'status': 'ZERO_RESULTS'
            }
            
        except Exception as e:
            raise Exception(f"Distance matrix API call failed: {e}")
    
    @classmethod
    async def places_autocomplete(
        cls,
        input_text: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: Optional[int] = None,
        language: Optional[str] = None,
        types: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get place autocomplete predictions based on input text.

        Args:
            input_text: The text string to autocomplete.
            lat: Optional latitude to bias results towards. Must be between -90 and 90.
            lon: Optional longitude to bias results towards. Must be between -180 and 180.
            radius: Optional radius in meters for location biasing. Must be between 1 and 50000.
            language: Optional language code (e.g., 'en', 'es').
            types: Optional type filter (e.g., 'establishment', 'geocode', 'address').

        Returns:
            List of prediction dictionaries containing place_id, description, etc.

        Raises:
            ValueError: If input_text is empty, or if lat/lon are provided but invalid.
            Exception: If the API call fails.
        """
        # #region agent log
        _start = time.time()
        _log_debug("map_tools.py:places_autocomplete:start", "Tool called", {"input_text": input_text}, "B")
        # #endregion
        if not input_text or not input_text.strip():
            raise ValueError("Input text cannot be empty or None.")

        # Validate location coordinates if provided
        location = None
        if lat is not None or lon is not None:
            if lat is None or lon is None:
                raise ValueError("Both latitude and longitude must be provided together, or neither.")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude must be between -90 and 90, got {lat}.")
            if not (-180 <= lon <= 180):
                raise ValueError(f"Longitude must be between -180 and 180, got {lon}.")
            location = (lat, lon)

        if radius and not (1 <= radius <= 50000):
            raise ValueError(f"Radius must be between 1 and 50000 meters, got {radius}.")

        try:
            loop = asyncio.get_running_loop()

            autocomplete_params = DictUtils.build_params(
                input=input_text,
                location=location,
                radius=radius,
                language=language,
                types=types
            )

            # Use functools.partial to pass keyword arguments
            autocomplete_result = await loop.run_in_executor(
                None,
                partial(cls.client.places_autocomplete, **autocomplete_params)
            )

            # #region agent log
            _elapsed = time.time() - _start
            _log_debug("map_tools.py:places_autocomplete:end", "Tool completed", {"elapsed_ms": int(_elapsed * 1000), "result_count": len(autocomplete_result) if autocomplete_result else 0}, "B")
            # #endregion
            return autocomplete_result if autocomplete_result else []

        except Exception as e:
            # #region agent log
            _elapsed = time.time() - _start
            _log_debug("map_tools.py:places_autocomplete:error", "Tool failed", {"elapsed_ms": int(_elapsed * 1000), "error": str(e)}, "B")
            # #endregion
            raise Exception(f"Places autocomplete API call failed for '{input_text}': {e}")

    @classmethod
    def get_route_polyline(cls, directions_result: Dict[str, Any]) -> Optional[str]:
        """
        Extract the encoded polyline from a Directions API response.

        The Directions API returns an encoded polyline that represents the actual
        driving route following roads. This polyline can be used in Static Maps API
        to display the route accurately.

        Args:
            directions_result: Response from get_travel_time_distance() or
                googlemaps.Client.directions()

        Returns:
            Encoded polyline string, or None if not found

        Example:
            >>> directions = await MapTools.get_travel_time_distance("SF", "San Carlos")
            >>> polyline = MapTools.get_route_polyline(directions)
            >>> # polyline = "abcd123..."  # Encoded string
        """
        # #region agent log
        _start = time.time()
        _log_debug("map_tools.py:get_route_polyline:start", "Tool called", {"has_directions": bool(directions_result)}, "A")
        # #endregion
        try:
            if not directions_result:
                return None

            # Directions API returns a list of routes
            if isinstance(directions_result, list) and len(directions_result) > 0:
                route = directions_result[0]
            elif isinstance(directions_result, dict) and 'routes' in directions_result:
                routes = directions_result['routes']
                if not routes:
                    return None
                route = routes[0]
            else:
                return None

            # Extract polyline from overview_polyline
            if 'overview_polyline' in route:
                polyline_data = route['overview_polyline']
                if isinstance(polyline_data, dict) and 'points' in polyline_data:
                    # #region agent log
                    _elapsed = time.time() - _start
                    _log_debug("map_tools.py:get_route_polyline:end", "Tool completed", {"elapsed_ms": int(_elapsed * 1000), "polyline_len": len(polyline_data['points'])}, "A")
                    # #endregion
                    return polyline_data['points']
                elif isinstance(polyline_data, str):
                    # #region agent log
                    _elapsed = time.time() - _start
                    _log_debug("map_tools.py:get_route_polyline:end", "Tool completed", {"elapsed_ms": int(_elapsed * 1000), "polyline_len": len(polyline_data)}, "A")
                    # #endregion
                    return polyline_data

            # #region agent log
            _elapsed = time.time() - _start
            _log_debug("map_tools.py:get_route_polyline:end", "Tool completed - no polyline", {"elapsed_ms": int(_elapsed * 1000)}, "A")
            # #endregion
            return None

        except (KeyError, IndexError, TypeError) as e:
            # #region agent log
            _elapsed = time.time() - _start
            _log_debug("map_tools.py:get_route_polyline:error", "Tool failed", {"elapsed_ms": int(_elapsed * 1000), "error": str(e)}, "A")
            # #endregion
            # If structure is unexpected, return None
            return None

    @classmethod
    async def get_static_map_url(
        cls,
        center: Optional[str] = None,
        zoom: int = 13,
        size: str = "600x400",
        maptype: str = "roadmap",
        markers: Optional[List[str]] = None,
        path: Optional[List[str]] = None,
        encoded_polyline: Optional[str] = None,
        format: str = "png"
    ) -> str:
        """
        Generate a URL for Google Static Maps API to display a map image.

        Google Static Maps API allows you to embed a map image in your application
        without requiring JavaScript or dynamic page loading. The returned URL can
        be used directly in an <img> tag or markdown ![map](url).

        Args:
            center: Center of the map. Can be address (e.g., "San Francisco, CA") or
                coordinates (e.g., "37.7749,-122.4194"). If not provided, map will be
                centered automatically based on markers or path.
            zoom: Zoom level from 0 (world) to 21+ (street level). Default: 13.
            size: Image dimensions as "widthxheight" (max 640x640 for free tier).
                Examples: "600x400", "400x400", "640x480". Default: "600x400".
            maptype: Map type. Options: 'roadmap' (default), 'satellite', 'terrain', 'hybrid'.
            markers: List of marker specifications. Each marker can be:
                - Simple: "37.7749,-122.4194" (default red marker)
                - Styled: "color:blue|label:A|37.7749,-122.4194"
                - Address: "color:red|label:S|San Francisco, CA"
                Example: ["color:red|label:A|37.7749,-122.4194", "color:blue|label:B|37.8044,-122.2712"]
            path: List of path waypoints to draw a straight line on the map.
                Format: "lat,lng" or address strings.
                Example: ["37.7749,-122.4194", "37.8044,-122.2712"]
                NOTE: This draws straight lines. For actual driving routes, use encoded_polyline.
            encoded_polyline: Encoded polyline string from Directions API.
                This shows the actual driving route following roads.
                Get this from: MapTools.get_route_polyline(directions_result)
                Example: "abcd1234..."  # Encoded polyline string
            format: Image format. Options: 'png' (default), 'png32', 'gif', 'jpg', 'jpg-baseline'.

        Returns:
            str: Complete URL to the static map image that can be used in markdown as ![map](url).

        Raises:
            ValueError: If parameters are invalid (bad zoom, size, maptype, etc.).

        Examples:
            # Simple map centered on a location
            url = await MapTools.get_static_map_url(
                center="San Francisco, CA",
                zoom=12
            )

            # Map with multiple markers
            url = await MapTools.get_static_map_url(
                center="37.7749,-122.4194",
                zoom=13,
                markers=[
                    "color:red|label:A|37.7749,-122.4194",
                    "color:blue|label:B|37.8044,-122.2712"
                ]
            )

            # Map with actual driving route (RECOMMENDED)
            directions = await MapTools.get_travel_time_distance("SF, CA", "San Carlos, CA")
            polyline = MapTools.get_route_polyline(directions)
            url = await MapTools.get_static_map_url(
                zoom=10,
                encoded_polyline=polyline
            )

            # Map with straight line (not recommended for routes)
            url = await MapTools.get_static_map_url(
                zoom=12,
                path=[
                    "37.7749,-122.4194",  # Start
                    "37.8044,-122.2712"   # End
                ]
            )

        Documentation:
            https://developers.google.com/maps/documentation/maps-static/overview
        """
        # #region agent log
        _start = time.time()
        _log_debug("map_tools.py:get_static_map_url:start", "Tool called", {"center": center, "zoom": zoom, "has_polyline": bool(encoded_polyline), "has_markers": bool(markers)}, "A")
        # #endregion
        # Validate zoom level
        if not (0 <= zoom <= 21):
            raise ValueError(f"Zoom must be between 0 and 21, got {zoom}.")

        # Validate size format
        try:
            width, height = size.lower().split('x')
            width_int, height_int = int(width), int(height)
            if width_int > 640 or height_int > 640:
                raise ValueError(
                    f"Size dimensions must be <= 640x640 for free tier, got {size}. "
                    "For larger images, use Google Maps Premium Plan."
                )
            if width_int < 1 or height_int < 1:
                raise ValueError(f"Size dimensions must be positive, got {size}.")
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid size format '{size}'. Expected format: 'widthxheight' (e.g., '600x400')."
            ) from e

        # Validate maptype
        valid_maptypes = ['roadmap', 'satellite', 'terrain', 'hybrid']
        if maptype not in valid_maptypes:
            raise ValueError(
                f"Invalid maptype '{maptype}'. Valid options: {valid_maptypes}"
            )

        # Validate format
        valid_formats = ['png', 'png32', 'gif', 'jpg', 'jpg-baseline']
        if format not in valid_formats:
            raise ValueError(
                f"Invalid format '{format}'. Valid options: {valid_formats}"
            )

        # Get API key from environment
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable must be set.")

        # Build URL
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        params = [
            f"size={size}",
            f"maptype={maptype}",
            f"format={format}",
            f"key={api_key}"
        ]

        # Add center if provided (but not when using encoded_polyline - Google auto-centers)
        if center and not encoded_polyline:
            params.append(f"center={center}")

        # Add zoom (but not when using encoded_polyline - Google auto-fits the route)
        # When encoded_polyline is provided, Google Maps API automatically determines
        # the best zoom level to fit the entire route in the map frame
        if not encoded_polyline:
            params.append(f"zoom={zoom}")

        # Add markers if provided
        if markers:
            for marker in markers:
                params.append(f"markers={marker}")

        # Add encoded polyline if provided (shows actual driving route following roads)
        if encoded_polyline:
            # Static Maps API uses "enc:" prefix for encoded polylines
            # URL-encode the polyline to handle special characters (backslashes, etc.)
            encoded_poly_safe = quote(encoded_polyline, safe='')
            params.append(f"path=color:0x0000ff|weight:5|enc:{encoded_poly_safe}")
        # Add straight path if provided (fallback for simple point-to-point lines)
        elif path:
            path_str = "|".join(path)
            params.append(f"path=color:0x0000ff|weight:5|{path_str}")

        # Construct final URL
        url = f"{base_url}?{'&'.join(params)}"

        # #region agent log
        _elapsed = time.time() - _start
        _log_debug("map_tools.py:get_static_map_url:end", "Tool completed", {"elapsed_ms": int(_elapsed * 1000), "url_len": len(url)}, "A")
        # #endregion
        return url

    @classmethod
    def get_interactive_map_data(
        cls,
        map_type: str,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        waypoints: Optional[List[str]] = None,
        center_lat: Optional[float] = None,
        center_lng: Optional[float] = None,
        zoom: int = 12,
        markers: Optional[List[Dict[str, Any]]] = None,
        travel_mode: str = "driving"
    ) -> str:
        """
        Generate interactive map configuration as JSON markdown code block.

        The frontend will detect this JSON and render an interactive Google Map
        using @vis.gl/react-google-maps. This provides a rich, explorable map
        experience with pan, zoom, and click interactions.

        Args:
            map_type: Type of map to generate. Valid values:
                - "route": Driving directions between origin and destination
                - "location": Single location centered on map
                - "places": Multiple locations shown with markers
            origin: Starting location for route maps. Can be address or coordinates.
            destination: Ending location for route maps. Can be address or coordinates.
            waypoints: Optional intermediate stops for route maps. List of addresses.
            center_lat: Center latitude for location/places maps (-90 to 90).
            center_lng: Center longitude for location/places maps (-180 to 180).
            zoom: Zoom level (1-20, default 12). Lower = more zoomed out.
            markers: List of markers for places maps. Each marker should have:
                - lat: Latitude (required)
                - lng: Longitude (required)
                - title: Marker title (optional)
                - type: Marker type/category (optional)
            travel_mode: Transportation mode for routes. Valid values:
                - "driving" (default): Car routes
                - "walking": Pedestrian routes
                - "bicycling": Bicycle routes
                - "transit": Public transportation

        Returns:
            JSON string in markdown code block format that frontend will detect
            and render as an interactive map component.

        Raises:
            ValueError: If required parameters are missing or invalid.

        Examples:
            # Route map from SF to San Carlos
            >>> data = MapTools.get_interactive_map_data(
            ...     map_type="route",
            ...     origin="San Francisco, CA",
            ...     destination="San Carlos, CA",
            ...     travel_mode="driving"
            ... )

            # Route with waypoints
            >>> data = MapTools.get_interactive_map_data(
            ...     map_type="route",
            ...     origin="San Francisco, CA",
            ...     destination="San Jose, CA",
            ...     waypoints=["Palo Alto, CA", "Mountain View, CA"],
            ...     travel_mode="bicycling"
            ... )

            # Location map centered on a place
            >>> data = MapTools.get_interactive_map_data(
            ...     map_type="location",
            ...     center_lat=37.7749,
            ...     center_lng=-122.4194,
            ...     zoom=14
            ... )

            # Places map with multiple markers
            >>> data = MapTools.get_interactive_map_data(
            ...     map_type="places",
            ...     center_lat=37.7749,
            ...     center_lng=-122.4194,
            ...     zoom=13,
            ...     markers=[
            ...         {"lat": 37.7749, "lng": -122.4194, "title": "San Francisco City Hall"},
            ...         {"lat": 37.7849, "lng": -122.4194, "title": "Civic Center"}
            ...     ]
            ... )

        Frontend Integration:
            The returned JSON will be automatically detected by the chat interface's
            ReactMarkdown renderer. When it sees ```json with type: "interactive_map",
            it will render the InteractiveMap React component instead of a code block.

        Usage in MapAgent:
            MapAgent should call this function when:
            - User explicitly requests "interactive" or "detailed" map
            - Complex routes with multiple waypoints
            - Different travel modes needed
            - Exploration queries (e.g., "show nearby restaurants on map")

            For simple A-to-B routes, use get_static_map_url() instead.
        """
        # Validate map_type
        valid_map_types = ["route", "location", "places"]
        if map_type not in valid_map_types:
            raise ValueError(
                f"Invalid map_type '{map_type}'. Valid options: {valid_map_types}"
            )

        # Validate travel_mode
        valid_travel_modes = ["driving", "walking", "bicycling", "transit"]
        if travel_mode not in valid_travel_modes:
            raise ValueError(
                f"Invalid travel_mode '{travel_mode}'. Valid options: {valid_travel_modes}"
            )

        # Validate zoom
        if not (1 <= zoom <= 20):
            raise ValueError(f"Zoom must be between 1 and 20, got {zoom}.")

        # Build config object
        config: Dict[str, Any] = {
            "map_type": map_type,
            "zoom": zoom,
        }

        # Add type-specific config
        if map_type == "route":
            if not origin or not origin.strip():
                raise ValueError("Route maps require origin parameter")
            if not destination or not destination.strip():
                raise ValueError("Route maps require destination parameter")

            config["origin"] = origin
            config["destination"] = destination
            config["travel_mode"] = travel_mode.upper()

            if waypoints:
                # Validate waypoints
                if not isinstance(waypoints, list):
                    raise ValueError("Waypoints must be a list of addresses")
                if len(waypoints) > 23:  # Google Maps limit is 23 waypoints + origin + destination = 25
                    raise ValueError("Maximum 23 waypoints allowed (Google Maps limit)")

                config["waypoints"] = waypoints

        elif map_type in ["location", "places"]:
            if center_lat is not None and center_lng is not None:
                # Validate center coordinates
                if not (-90 <= center_lat <= 90):
                    raise ValueError(f"Center latitude must be between -90 and 90, got {center_lat}")
                if not (-180 <= center_lng <= 180):
                    raise ValueError(f"Center longitude must be between -180 and 180, got {center_lng}")

                config["center"] = {"lat": center_lat, "lng": center_lng}

            if markers:
                # Validate markers
                if not isinstance(markers, list):
                    raise ValueError("Markers must be a list of marker objects")

                validated_markers = []
                for i, marker in enumerate(markers):
                    if not isinstance(marker, dict):
                        raise ValueError(f"Marker {i} must be a dictionary")

                    # Support two marker shapes:
                    # 1) Coordinate marker: {lat, lng, title?, type?}
                    # 2) Address marker: {address, title?, type?} (frontend geocodes)
                    address = marker.get("address")
                    has_lat_lng = ("lat" in marker) and ("lng" in marker) and (marker.get("lat") is not None) and (marker.get("lng") is not None)
                    if not has_lat_lng and not (isinstance(address, str) and address.strip()):
                        raise ValueError(
                            f"Marker {i} must have either ('lat' and 'lng') or a non-empty 'address' field"
                        )

                    if has_lat_lng:
                        lat, lng = marker["lat"], marker["lng"]
                        if not (-90 <= lat <= 90):
                            raise ValueError(f"Marker {i} latitude must be between -90 and 90, got {lat}")
                        if not (-180 <= lng <= 180):
                            raise ValueError(f"Marker {i} longitude must be between -180 and 180, got {lng}")
                    else:
                        lat, lng = None, None

                    validated_markers.append({
                        "lat": lat,
                        "lng": lng,
                        "address": address.strip() if isinstance(address, str) else "",
                        "title": marker.get("title", ""),
                        "type": marker.get("type", ""),
                    })

                config["markers"] = validated_markers

        # Wrap in interactive_map envelope
        envelope = {
            "type": "interactive_map",
            "config": config
        }

        # Return as JSON markdown code block
        # This will be detected by the frontend's ReactMarkdown renderer
        json_str = json.dumps(envelope, indent=2)
        return f"```json\n{json_str}\n```"


#---------------------------------------------
# main tests
#---------------------------------------------

async def test_maps():
    print("Testing get_coordinates_by_address:")
    address = "1600 Amphitheatre Parkway, Mountain View, CA"
    try:
        lat, lon = await MapTools.get_coordinates_by_address(address)
        print(f"Coordinates for '{address}': ({lat}, {lon})")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nTesting get_address_by_coordinates:")
    test_lat, test_lon = 37.4221, -122.0841
    try:
        result_address = await MapTools.get_address_by_coordinates(test_lat, test_lon)
        print(f"Address for ({test_lat}, {test_lon}): {result_address}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nTesting search_places_nearby:")
    try:
        places = await MapTools.search_places_nearby(
            37.4221, -122.0841, 
            keyword="restaurant", 
            radius=500
        )
        print(f"Found {len(places)} places")
        for i, place in enumerate(places[:3]):
            print(f"  Place {i+1}: {place.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_maps())

