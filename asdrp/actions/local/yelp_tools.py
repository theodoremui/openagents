#############################################################################
# yelp_tools.py
#
# Yelp tools
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import requests
from typing import Any, Dict, List, Optional

from asdrp.actions.tools_meta import ToolsMeta

# Timeout for API calls
TIMEOUT_SECONDS = 30


class YelpTools(metaclass=ToolsMeta):
    """
    Tools for querying the Yelp API (business search, details, reviews, etc.).
    
    This class uses the ToolsMeta metaclass which automatically:
    - Discovers all public @classmethod decorated methods
    - Creates `spec_functions` list containing method names
    - Creates `tool_list` containing wrapped function tools ready for agent frameworks
    
    Yelp-specific initialization (API key and headers) is handled via the 
    `_setup_class()` hook method.
    
    Environment Variables:
    ---------------------
    YELP_API_KEY: Required. Yelp Fusion API key.
    
    Usage:
    ------
    ```python
    from asdrp.actions.local.yelp_tools import YelpTools
    
    # Use the automatically generated tool_list
    from agents import Agent
    agent = Agent(tools=YelpTools.tool_list)
    
    # Or call methods directly
    results = YelpTools.search_businesses("pizza", 37.7749, -122.4194)
    ```
    """
    # Class variables for API configuration (set by _setup_class)
    BASE_URL = "https://api.yelp.com/v3"    
    api_key: str
    headers: Dict[str, str]

    # ------------- Automatically populated by ToolsMeta -------------
    # List of method names & wrapped function tools to expose as tools
    spec_functions: List[str]
    tool_list: List[Any]
    
    @classmethod
    def _setup_class(cls) -> None:
        """
        Set up Yelp-specific class variables (API key and headers).
        
        This method is called automatically by ToolsMeta during class creation.
        It reads the YELP_API_KEY from environment variables and sets up the
        authorization headers needed for API requests.
        
        Raises:
            ValueError: If YELP_API_KEY is not set in environment variables.
        """
        api_key = os.getenv("YELP_API_KEY")
        if not api_key:
            raise ValueError("YELP_API_KEY is not set.")
        cls.api_key = api_key
        cls.headers = {"Authorization": f"Bearer {cls.api_key}"}
    
    @classmethod
    def _get_excluded_methods(cls) -> set[str]:
        """
        Exclude Yelp-specific class variables from tool discovery.
        
        Returns:
            Set of attribute names to exclude from being discovered as tools.
            This ensures that internal configuration attributes (api_key, headers, 
            BASE_URL) are not included in the tool_list.
        """
        return {'BASE_URL', 'api_key', 'headers'}
    
    @classmethod
    def search_businesses(
        cls, term: str, latitude: float, longitude: float,
        categories: Optional[str] = None, price: Optional[str] = None, limit: int = 20
    ) -> Dict:
        """Search for businesses by keyword, location (lat/long), category, and price level."""
        endpoint = f"{cls.BASE_URL}/businesses/search"
        params = {
            "term": term, "latitude": latitude, "longitude": longitude,
            "categories": categories, "price": price, "limit": limit
        }
        response = requests.get(endpoint, headers=cls.headers, params=params, timeout=TIMEOUT_SECONDS)
        return response.json()
    
    @classmethod
    def search_by_phone(cls, phone: str) -> Dict:
        """Search for a business by phone number."""
        endpoint = f"{cls.BASE_URL}/businesses/search/phone"
        params = {"phone": phone}
        response = requests.get(endpoint, headers=cls.headers, params=params, timeout=TIMEOUT_SECONDS)
        return response.json()
    
    @classmethod
    def match_business(cls, name: str, address1: str, city: str, state: str, country: str) -> Dict:
        """Find a business match by exact name and address."""
        endpoint = f"{cls.BASE_URL}/businesses/matches"
        params = {"name": name, "address1": address1, "city": city, "state": state, "country": country}
        response = requests.get(endpoint, headers=cls.headers, params=params, timeout=TIMEOUT_SECONDS)
        return response.json()
    
    @classmethod
    def get_business_details(cls, business_id: str) -> Dict:
        """Get detailed information for a business (hours, rating, etc.) by Yelp business ID."""
        endpoint = f"{cls.BASE_URL}/businesses/{business_id}"
        response = requests.get(endpoint, headers=cls.headers, timeout=TIMEOUT_SECONDS)
        return response.json()
    
    @classmethod
    def get_business_engagement(cls, business_ids: List[str]) -> Dict:
        """Get engagement metrics (view counts, etc.) for multiple businesses by ID."""
        endpoint = f"{cls.BASE_URL}/businesses/engagement"
        params = {"business_ids": ",".join(business_ids)}
        response = requests.get(endpoint, headers=cls.headers, params=params, timeout=TIMEOUT_SECONDS)
        return response.json()
    
    @classmethod
    def get_business_reviews(cls, business_id: str) -> Dict:
        """Get up to three review excerpts for a given business."""
        endpoint = f"{cls.BASE_URL}/businesses/{business_id}/reviews"
        response = requests.get(endpoint, headers=cls.headers, timeout=TIMEOUT_SECONDS)
        return response.json()
    
    @classmethod
    def get_review_highlights(cls, business_id: str) -> Dict:
        """Get summarized review highlights for a given business."""
        endpoint = f"{cls.BASE_URL}/businesses/{business_id}/review_highlights"
        response = requests.get(endpoint, headers=cls.headers, timeout=TIMEOUT_SECONDS)
        return response.json()

if __name__ == "__main__":
    # Smoke test for YelpTools methods
    # API key is automatically loaded from environment in metaclass

    print("Testing search_businesses:")
    # Coordinates for San Francisco city center
    sf_latitude, sf_longitude = 37.7749, -122.4194
    result = YelpTools.search_businesses("coffee", sf_latitude, sf_longitude)
    businesses = result.get("businesses", [])
    print(f"Found {len(businesses)} coffee businesses in San Francisco")
    for index, business in enumerate(businesses):
        print(f"business {index}: {business['name']}")

