#############################################################################
# map_agent.py
#
# MapAgent implementation using the Agent protocol.
#
# This module provides a MapAgent that implements AgentProtocol and uses
# Google Maps tools for location-based queries, place search, directions,
# and other mapping-related operations.
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import Any, Dict
import asyncio

from agents import Agent, ModelSettings, Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.actions.geo.map_tools import MapTools
from asdrp.agents.config_loader import ModelConfig
from asdrp.agents.protocol import AgentProtocol, AgentException

# Default instructions for MapAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
DEFAULT_INSTRUCTIONS = (
    "You are a powerful mapping and location intelligence agent with access to Google Maps APIs. "
    "You can answer complex location-based queries by strategically chaining multiple tool calls together.\n\n"

    "AVAILABLE TOOLS AND THEIR USE CASES:\n"
    "1. places_autocomplete: Find places by name (e.g., 'Elia Greek restaurant San Carlos CA'). "
    "Returns place_id and description. Use this FIRST when you need to find a place by name.\n"
    "2. get_place_details: Get full details (coordinates, address, phone, etc.) from a place_id. "
    "Use this AFTER places_autocomplete to get coordinates.\n"
    "3. get_coordinates_by_address: Convert addresses to coordinates. Use when you have a full address.\n"
    "4. search_places_nearby: Find places near coordinates. Use place_type parameter to filter by type "
    "(e.g., 'hospital', 'restaurant', 'gas_station'). Use keyword for additional filtering.\n"
    "5. get_distance_matrix: Compare distances/times from one location to multiple destinations. "
    "Use to rank results by proximity.\n"
    "6. get_travel_time_distance: Get route details between two locations.\n"
    "7. get_address_by_coordinates: Convert coordinates to addresses.\n"
    "8. get_static_map_url: Generate a visual map image URL showing locations, routes, or markers.\n"
    "9. get_interactive_map_data: Generate an INTERACTIVE map (as a ```json block) that the frontend renders.\n\n"

    "WORKFLOW FOR COMPLEX QUERIES:\n"
    "When asked to find places near a named location (e.g., 'hospitals near Elia restaurant'):\n"
    "Step 1: Use places_autocomplete to find the named location by its name + city/state.\n"
    "Step 2: Extract the place_id from the autocomplete result.\n"
    "Step 3: Use get_place_details with the place_id to get coordinates (lat, lon).\n"
    "Step 4: Use search_places_nearby with those coordinates and appropriate place_type "
    "(e.g., place_type='hospital' for hospitals). Set radius as needed (default 1000m, max 50000m).\n"
    "Step 5: Optionally use get_distance_matrix to rank results by distance from the origin.\n\n"

    "MAP VISUALIZATION WORKFLOW:\n"
    "When asked for a 'map view', 'routing map', 'directions', 'drive from A to B', or anything route-related:\n"
    "1) Call get_travel_time_distance(origin, destination) to get route details\n"
    "2) MANDATORY for routes: Call get_interactive_map_data(map_type='route', origin=..., destination=...)\n"
    "3) Return BOTH the text directions AND the complete ```json block from get_interactive_map_data.\n\n"
    "For non-route location/places maps:\n"
    "- Use places_autocomplete → get_place_details (or get_coordinates_by_address)\n"
    "- Then call get_interactive_map_data(map_type='location' or 'places', markers=...)\n\n"

    "IMPORTANT GUIDELINES:\n"
    "- ALWAYS use places_autocomplete FIRST when searching for a place by name, even if you don't have exact address.\n"
    "- Use place_type parameter in search_places_nearby for filtering (hospital, restaurant, gas_station, etc.).\n"
    "- Chain tool calls: autocomplete → place_details → search_nearby → distance_matrix.\n"
    "- For route queries, ALWAYS generate an INTERACTIVE map using get_interactive_map_data.\n"
    "- NEVER say you provided a map unless you actually include the ```json block from get_interactive_map_data.\n"
    "- Never ask for clarification if you can find the information using available tools.\n"
    "- Provide complete answers with addresses, distances, and relevant details.\n"
    "- When multiple results are found, rank them by distance using get_distance_matrix.\n\n"

    "EXAMPLES:\n"
    "Query: 'Find hospitals near Elia Greek restaurant in San Carlos, CA'\n"
    "→ Use places_autocomplete('Elia Greek restaurant San Carlos CA')\n"
    "→ Use get_place_details(place_id) to get coordinates\n"
    "→ Use search_places_nearby(lat, lon, place_type='hospital')\n"
    "→ Use get_distance_matrix to rank hospitals by distance\n"
    "→ Provide complete answer with hospital names, addresses, and distances.\n\n"

    "Query: 'Show me a map view of the route from San Francisco to San Carlos'\n"
    "→ Use get_travel_time_distance('San Francisco, CA', 'San Carlos, CA')\n"
    "→ Use get_route_polyline(directions_result) to extract encoded polyline\n"
    "→ Use get_static_map_url(zoom=10, encoded_polyline=polyline)\n"
    "→ Return: ![Route Map](generated_url)"
)


def create_map_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a MapAgent instance.
    
    This is the public factory function for creating MapAgent instances.
    It is used by AgentFactory and can also be called directly.
    
    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
    
    Returns:
        A MapAgent instance implementing AgentProtocol.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent = create_map_agent()
    >>> agent = create_map_agent("You are a mapping expert")
    >>> from asdrp.agents.config_loader import ModelConfig
    >>> model_cfg = ModelConfig(name="gpt-4", temperature=0.8)
    >>> agent = create_map_agent("Instructions", model_cfg)
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS
    
    try:        
        # Build agent creation arguments
        agent_kwargs: Dict[str, Any] = {
            "name": "MapAgent",
            "instructions": instructions,
            "tools": MapTools.tool_list,
        }
        
        # Add model configuration if provided
        if model_config:
            agent_kwargs["model"] = model_config.name
            agent_kwargs["model_settings"] = ModelSettings(
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
        
        return Agent[Any](**agent_kwargs)
    except ImportError as e:
        raise AgentException(
            f"Failed to import MapAgent dependencies: {str(e)}",
            agent_name="map"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create MapAgent: {str(e)}",
            agent_name="map"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for MapAgent interactive session.
    
    Creates a MapAgent and runs an interactive loop where users can
    ask questions about maps, locations, places, and directions.
    """
    agent = create_map_agent()
    
    user_input = input(f"Ask {agent.name}: ")
    while user_input != "":
        response = await Runner.run(agent, input=user_input)
        print(response.final_output)
        user_input = input(f"Ask {agent.name}: ")


if __name__ == "__main__":
    asyncio.run(main())

