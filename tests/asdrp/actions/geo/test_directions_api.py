#!/usr/bin/env python3
"""
Test script to debug Google Directions API and Static Maps API calls.
This will help identify issues with polyline encoding and route visualization.
"""

import sys
import asyncio
import json
from pathlib import Path

# Navigate from tests/asdrp/actions/geo/ to project root
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from asdrp.actions.geo.map_tools import MapTools


async def test_directions_and_map():
    """Test the full workflow: Directions → Polyline → Static Map URL"""

    print("=" * 80)
    print("Testing Google Directions API and Static Maps API")
    print("=" * 80)

    origin = "San Francisco, CA"
    destination = "San Carlos, CA"

    print(f"\n1. Getting directions from '{origin}' to '{destination}'...")
    print("-" * 80)

    # Get directions
    try:
        directions = await MapTools.get_travel_time_distance(
            origin=origin,
            destination=destination,
            mode="driving"
        )

        print(f"✅ Directions API returned {len(directions)} route(s)")

        if not directions:
            print("❌ ERROR: No routes returned")
            return

        # Show first route summary
        route = directions[0]
        if 'legs' in route:
            leg = route['legs'][0]
            distance = leg.get('distance', {}).get('text', 'unknown')
            duration = leg.get('duration', {}).get('text', 'unknown')
            print(f"   Distance: {distance}")
            print(f"   Duration: {duration}")

        if 'summary' in route:
            print(f"   Route summary: {route['summary']}")

        # Check for overview_polyline
        print(f"\n2. Checking for overview_polyline...")
        print("-" * 80)

        if 'overview_polyline' not in route:
            print("❌ ERROR: No overview_polyline in route!")
            print(f"Available keys in route: {list(route.keys())}")
            return

        polyline_data = route['overview_polyline']
        print(f"✅ Found overview_polyline")
        print(f"   Type: {type(polyline_data)}")
        print(f"   Keys: {list(polyline_data.keys()) if isinstance(polyline_data, dict) else 'N/A'}")

        if isinstance(polyline_data, dict) and 'points' in polyline_data:
            polyline_string = polyline_data['points']
            print(f"✅ Found points string")
            print(f"   Length: {len(polyline_string)} characters")
            print(f"   First 50 chars: {polyline_string[:50]}...")
            print(f"   Last 50 chars: ...{polyline_string[-50:]}")
        else:
            print(f"❌ ERROR: 'points' not found in polyline_data")
            return

        # Test get_route_polyline method
        print(f"\n3. Testing get_route_polyline() method...")
        print("-" * 80)

        extracted_polyline = MapTools.get_route_polyline(directions)

        if not extracted_polyline:
            print("❌ ERROR: get_route_polyline() returned None")
            return

        print(f"✅ Successfully extracted polyline")
        print(f"   Length: {len(extracted_polyline)} characters")
        print(f"   Matches original: {extracted_polyline == polyline_string}")

        if extracted_polyline != polyline_string:
            print(f"   ⚠️  WARNING: Extracted polyline differs from original!")
            print(f"   Original first 50: {polyline_string[:50]}")
            print(f"   Extracted first 50: {extracted_polyline[:50]}")

        # Test Static Maps URL generation
        print(f"\n4. Testing get_static_map_url() with encoded polyline...")
        print("-" * 80)

        map_url = await MapTools.get_static_map_url(
            zoom=10,
            encoded_polyline=extracted_polyline
        )

        print(f"✅ Generated Static Maps URL")
        print(f"   Length: {len(map_url)} characters")
        print(f"   URL: {map_url[:200]}...")

        # Verify URL format
        if "enc:" not in map_url:
            print(f"   ❌ ERROR: URL does not contain 'enc:' prefix!")
        else:
            print(f"   ✅ URL contains 'enc:' prefix")

        if "path=" not in map_url:
            print(f"   ❌ ERROR: URL does not contain 'path=' parameter!")
        else:
            print(f"   ✅ URL contains 'path=' parameter")

        # Check for API key
        if "key=" not in map_url:
            print(f"   ⚠️  WARNING: URL does not contain 'key=' parameter")
        else:
            print(f"   ✅ URL contains API key")

        # Test with simple path for comparison
        print(f"\n5. Testing get_static_map_url() with simple path for comparison...")
        print("-" * 80)

        # Get coordinates
        sf_coords = await MapTools.get_coordinates_by_address(origin)
        sc_coords = await MapTools.get_coordinates_by_address(destination)

        simple_map_url = await MapTools.get_static_map_url(
            zoom=10,
            path=[f"{sf_coords[0]},{sf_coords[1]}", f"{sc_coords[0]},{sc_coords[1]}"]
        )

        print(f"✅ Generated simple path URL")
        print(f"   SF coords: {sf_coords}")
        print(f"   SC coords: {sc_coords}")

        # Compare URLs
        print(f"\n6. URL Comparison:")
        print("-" * 80)
        print(f"Encoded polyline URL length: {len(map_url)}")
        print(f"Simple path URL length: {len(simple_map_url)}")

        # Save for manual inspection
        print(f"\n7. Full URLs for manual testing:")
        print("-" * 80)
        print(f"\nEncoded polyline URL:")
        print(map_url)
        print(f"\nSimple path URL:")
        print(simple_map_url)

        print("\n" + "=" * 80)
        print("Testing complete! Check URLs in browser to verify routing.")
        print("=" * 80)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_directions_and_map())
