#!/usr/bin/env python3
"""
Test different transport modes to see which one matches the screenshot.
"""

import sys
import asyncio
import pytest
from pathlib import Path

# Navigate from tests/asdrp/actions/geo/ to project root
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from asdrp.actions.geo.map_tools import MapTools


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ['driving', 'walking', 'bicycling', 'transit'])
async def test_mode(mode: str):
    """Test a specific transport mode."""
    print(f"\n{'='*80}")
    print(f"Testing mode: {mode.upper()}")
    print(f"{'='*80}")

    origin = "San Francisco, CA"
    destination = "San Carlos, CA"

    try:
        directions = await MapTools.get_travel_time_distance(
            origin=origin,
            destination=destination,
            mode=mode
        )

        assert directions is not None, f"Directions should not be None for mode {mode}"
        assert len(directions) > 0, f"Should have at least one route for mode {mode}"

        route = directions[0]

        # Get route info
        if 'legs' in route:
            leg = route['legs'][0]
            distance = leg.get('distance', {}).get('text', 'unknown')
            duration = leg.get('duration', {}).get('text', 'unknown')
            print(f"Distance: {distance}")
            print(f"Duration: {duration}")
            assert distance != 'unknown', "Distance should be available"
            assert duration != 'unknown', "Duration should be available"

        if 'summary' in route:
            print(f"Summary: {route['summary']}")

        # Get polyline
        polyline = MapTools.get_route_polyline(directions)
        assert polyline is not None, f"Polyline should not be None for mode {mode}"
        assert len(polyline) > 0, f"Polyline should not be empty for mode {mode}"
        
        print(f"Polyline length: {len(polyline)} chars")

        # Generate map URL
        map_url = await MapTools.get_static_map_url(
            zoom=10,
            encoded_polyline=polyline
        )

        assert map_url is not None, "Map URL should not be None"
        assert len(map_url) > 0, "Map URL should not be empty"
        assert "maps.googleapis.com" in map_url, "Map URL should contain Google Maps domain"
        assert "enc:" in map_url or "path=" in map_url, "Map URL should contain encoded polyline or path"

        print(f"\nMap URL:")
        print(map_url)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise  # Re-raise to fail the test


async def _run_mode_test(mode: str):
    """Helper function for standalone execution."""
    print(f"\n{'='*80}")
    print(f"Testing mode: {mode.upper()}")
    print(f"{'='*80}")

    origin = "San Francisco, CA"
    destination = "San Carlos, CA"

    try:
        directions = await MapTools.get_travel_time_distance(
            origin=origin,
            destination=destination,
            mode=mode
        )

        if not directions:
            print(f"❌ No routes returned for {mode}")
            return

        route = directions[0]

        # Get route info
        if 'legs' in route:
            leg = route['legs'][0]
            distance = leg.get('distance', {}).get('text', 'unknown')
            duration = leg.get('duration', {}).get('text', 'unknown')
            print(f"Distance: {distance}")
            print(f"Duration: {duration}")

        if 'summary' in route:
            print(f"Summary: {route['summary']}")

        # Get polyline
        polyline = MapTools.get_route_polyline(directions)
        if polyline:
            print(f"Polyline length: {len(polyline)} chars")

            # Generate map URL
            map_url = await MapTools.get_static_map_url(
                zoom=10,
                encoded_polyline=polyline
            )

            print(f"\nMap URL:")
            print(map_url)
        else:
            print(f"❌ No polyline extracted")

    except Exception as e:
        print(f"❌ ERROR: {e}")


async def main():
    """Test all transport modes (standalone execution)."""
    modes = ['driving', 'walking', 'bicycling', 'transit']

    for mode in modes:
        await _run_mode_test(mode)
        print()


if __name__ == "__main__":
    asyncio.run(main())
