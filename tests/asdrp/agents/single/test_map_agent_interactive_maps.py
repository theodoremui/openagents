#!/usr/bin/env python3
"""
Comprehensive Integration Tests for MapAgent Interactive Map Generation

Tests the three workflow types:
1. Route/Directions Maps (origin → destination)
2. Places Maps (multiple locations with markers)
3. Single Location Maps (one place centered)

Following SOLID principles:
- Single Responsibility: Each test validates one workflow type
- Open/Closed: Easy to extend with new test cases
- Dependency Inversion: Tests depend on AgentProtocol abstraction

NOTE: These are integration tests that make real API calls.
Mark as 'slow' and 'integration' - run with: pytest -m "slow"
"""

import asyncio
import pytest
import json
import re
from pathlib import Path
import sys

# Navigate to project root
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents import Runner
from asdrp.agents.single.map_agent import create_map_agent
from asdrp.agents.config_loader import AgentConfigLoader


def extract_interactive_map_json(output: str) -> dict:
    """
    Extract interactive map JSON from agent output.

    Args:
        output: Agent response text containing ```json block

    Returns:
        Parsed JSON dict if found, None otherwise
    """
    # Look for ```json blocks
    json_pattern = r'```json\s*(\{[^`]+\})\s*```'
    matches = re.findall(json_pattern, output, re.DOTALL)

    if not matches:
        return None

    # Parse the first JSON block
    try:
        data = json.loads(matches[0])
        # Validate it's an interactive map
        if data.get("type") == "interactive_map" and "config" in data:
            return data
    except json.JSONDecodeError:
        pass

    return None


def validate_route_map(map_data: dict) -> None:
    """Validate route map structure."""
    assert map_data is not None, "No interactive map JSON found"
    assert map_data["type"] == "interactive_map"

    config = map_data["config"]
    assert config["map_type"] == "route", "Map type should be 'route'"
    assert "origin" in config, "Route map must have origin"
    assert "destination" in config, "Route map must have destination"
    assert "zoom" in config, "Map must have zoom level"


def validate_places_map(map_data: dict, min_markers: int = 1) -> None:
    """Validate places map structure."""
    assert map_data is not None, "No interactive map JSON found"
    assert map_data["type"] == "interactive_map"

    config = map_data["config"]
    assert config["map_type"] == "places", "Map type should be 'places'"

    # Handle both formats: center as object {"lat": x, "lng": y} or separate center_lat/center_lng
    has_center_object = "center" in config and isinstance(config["center"], dict)
    has_center_fields = "center_lat" in config and "center_lng" in config

    assert has_center_object or has_center_fields, \
        "Places map must have either 'center' object or 'center_lat'/'center_lng' fields"

    assert "zoom" in config, "Map must have zoom level"
    assert "markers" in config, "Places map must have markers"
    assert len(config["markers"]) >= min_markers, \
        f"Expected at least {min_markers} markers, got {len(config['markers'])}"

    # Validate marker structure
    for marker in config["markers"]:
        assert "lat" in marker, "Marker must have lat"
        assert "lng" in marker, "Marker must have lng"


def validate_location_map(map_data: dict) -> None:
    """Validate single location map structure."""
    assert map_data is not None, "No interactive map JSON found"
    assert map_data["type"] == "interactive_map"

    config = map_data["config"]
    assert config["map_type"] == "location", "Map type should be 'location'"

    # Handle both formats: center as object {"lat": x, "lng": y} or separate center_lat/center_lng
    has_center_object = "center" in config and isinstance(config["center"], dict)
    has_center_fields = "center_lat" in config and "center_lng" in config

    assert has_center_object or has_center_fields, \
        "Location map must have either 'center' object or 'center_lat'/'center_lng' fields"

    assert "zoom" in config, "Map must have zoom level"


# ============================================================================
# WORKFLOW TYPE 1: Route/Directions Maps
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_route_map_basic_directions():
    """Test basic route query generates interactive map."""
    print("\n" + "="*80)
    print("TEST: Basic Route Map - 'directions from A to B'")
    print("="*80)

    config_loader = AgentConfigLoader()
    agent_config = config_loader.get_agent_config("map")
    agent = create_map_agent(
        instructions=agent_config.default_instructions,
        model_config=agent_config.model
    )

    query = "Give me directions from San Carlos to San Francisco"
    print(f"Query: {query}\n")

    result = await Runner.run(
        starting_agent=agent,
        input=query,
        max_turns=10
    )

    output = str(result.final_output)
    print(f"Output (first 300 chars): {output[:300]}...\n")

    map_data = extract_interactive_map_json(output)
    validate_route_map(map_data)

    print("✅ Route map generated successfully")
    print(f"   Origin: {map_data['config']['origin']}")
    print(f"   Destination: {map_data['config']['destination']}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_route_map_with_keyword_show_route():
    """Test 'show route' keyword triggers map generation."""
    print("\n" + "="*80)
    print("TEST: Route Map with 'show route' keyword")
    print("="*80)

    config_loader = AgentConfigLoader()
    agent_config = config_loader.get_agent_config("map")
    agent = create_map_agent(
        instructions=agent_config.default_instructions,
        model_config=agent_config.model
    )

    query = "Show me the route from Palo Alto to San Jose"
    print(f"Query: {query}\n")

    result = await Runner.run(
        starting_agent=agent,
        input=query,
        max_turns=10
    )

    output = str(result.final_output)
    map_data = extract_interactive_map_json(output)
    validate_route_map(map_data)

    print("✅ Route map generated with 'show route' keyword")


# ============================================================================
# WORKFLOW TYPE 2: Places Maps (Multiple Markers)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_places_map_best_restaurants():
    """Test 'best X in Y' query generates places map with markers."""
    print("\n" + "="*80)
    print("TEST: Places Map - 'best restaurants in location'")
    print("="*80)

    config_loader = AgentConfigLoader()
    agent_config = config_loader.get_agent_config("map")
    agent = create_map_agent(
        instructions=agent_config.default_instructions,
        model_config=agent_config.model
    )

    query = "Show me on a detailed map where the best greek restaurants are in San Francisco"
    print(f"Query: {query}\n")

    result = await Runner.run(
        starting_agent=agent,
        input=query,
        max_turns=15
    )

    output = str(result.final_output)
    print(f"Output (first 500 chars): {output[:500]}...\n")

    map_data = extract_interactive_map_json(output)
    validate_places_map(map_data, min_markers=2)

    print("✅ Places map generated with restaurant markers")
    print(f"   Number of markers: {len(map_data['config']['markers'])}")
    print(f"   Center: ({map_data['config']['center_lat']}, {map_data['config']['center_lng']})")

    # Validate markers have titles
    markers_with_titles = sum(1 for m in map_data['config']['markers'] if 'title' in m)
    print(f"   Markers with titles: {markers_with_titles}/{len(map_data['config']['markers'])}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_places_map_show_on_map_keyword():
    """Test 'show on map' keyword triggers places map."""
    print("\n" + "="*80)
    print("TEST: Places Map - 'show on map' keyword")
    print("="*80)

    config_loader = AgentConfigLoader()
    agent_config = config_loader.get_agent_config("map")
    agent = create_map_agent(
        instructions=agent_config.default_instructions,
        model_config=agent_config.model
    )

    query = "Show on a map the best coffee shops in Palo Alto"
    print(f"Query: {query}\n")

    result = await Runner.run(
        starting_agent=agent,
        input=query,
        max_turns=15
    )

    output = str(result.final_output)
    map_data = extract_interactive_map_json(output)
    validate_places_map(map_data, min_markers=2)

    print("✅ Places map generated with 'show on map' keyword")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_places_map_where_are_keyword():
    """Test 'where are' keyword triggers places map."""
    print("\n" + "="*80)
    print("TEST: Places Map - 'where are' keyword")
    print("="*80)

    config_loader = AgentConfigLoader()
    agent_config = config_loader.get_agent_config("map")
    agent = create_map_agent(
        instructions=agent_config.default_instructions,
        model_config=agent_config.model
    )

    query = "Where are the best pizza places in San Carlos?"
    print(f"Query: {query}\n")

    result = await Runner.run(
        starting_agent=agent,
        input=query,
        max_turns=15
    )

    output = str(result.final_output)
    map_data = extract_interactive_map_json(output)
    validate_places_map(map_data, min_markers=1)

    print("✅ Places map generated with 'where are' keyword")


# ============================================================================
# WORKFLOW TYPE 3: Single Location Map
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_location_map_single_place():
    """Test single place query generates location map."""
    print("\n" + "="*80)
    print("TEST: Single Location Map - specific place")
    print("="*80)

    config_loader = AgentConfigLoader()
    agent_config = config_loader.get_agent_config("map")
    agent = create_map_agent(
        instructions=agent_config.default_instructions,
        model_config=agent_config.model
    )

    query = "Show me a map of the Golden Gate Bridge"
    print(f"Query: {query}\n")

    result = await Runner.run(
        starting_agent=agent,
        input=query,
        max_turns=10
    )

    output = str(result.final_output)
    map_data = extract_interactive_map_json(output)
    validate_location_map(map_data)

    print("✅ Location map generated for single place")
    print(f"   Center: ({map_data['config']['center_lat']}, {map_data['config']['center_lng']})")


# ============================================================================
# Fast Unit Tests (No API Calls)
# ============================================================================

def test_json_extraction_helper():
    """Test the JSON extraction helper function."""
    # Valid JSON
    output = """Here is the map:

```json
{"type": "interactive_map", "config": {"map_type": "route", "origin": "A", "destination": "B", "zoom": 10}}
```
"""
    data = extract_interactive_map_json(output)
    assert data is not None
    assert data["type"] == "interactive_map"
    assert data["config"]["map_type"] == "route"

    # No JSON
    output_no_json = "Just text, no map"
    assert extract_interactive_map_json(output_no_json) is None

    # Invalid JSON
    output_invalid = "```json\n{invalid}\n```"
    assert extract_interactive_map_json(output_invalid) is None


def test_validation_helpers():
    """Test map validation helper functions."""
    # Valid route map
    route_map = {
        "type": "interactive_map",
        "config": {
            "map_type": "route",
            "origin": "A",
            "destination": "B",
            "zoom": 12
        }
    }
    validate_route_map(route_map)  # Should not raise

    # Valid places map
    places_map = {
        "type": "interactive_map",
        "config": {
            "map_type": "places",
            "center_lat": 37.7749,
            "center_lng": -122.4194,
            "zoom": 13,
            "markers": [
                {"lat": 37.7749, "lng": -122.4194, "title": "Place 1"},
                {"lat": 37.7849, "lng": -122.4194, "title": "Place 2"}
            ]
        }
    }
    validate_places_map(places_map, min_markers=2)  # Should not raise

    # Valid location map
    location_map = {
        "type": "interactive_map",
        "config": {
            "map_type": "location",
            "center_lat": 37.7749,
            "center_lng": -122.4194,
            "zoom": 15
        }
    }
    validate_location_map(location_map)  # Should not raise

    print("✅ All validation helpers work correctly")


if __name__ == "__main__":
    # Run fast tests without pytest
    print("\n" + "="*80)
    print("Running Fast Unit Tests")
    print("="*80)

    test_json_extraction_helper()
    test_validation_helpers()

    print("\n✅ All fast tests passed!")
    print("\nTo run integration tests:")
    print("  pytest -m 'slow' tests/asdrp/agents/single/test_map_agent_interactive_maps.py -v")
