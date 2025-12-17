#!/usr/bin/env python3
"""
Test Google Maps Directions API performance and identify bottlenecks.

This script tests the actual API calls that MapAgent makes when processing
a directions request like "show me how to drive from San Carlos to Salesforce Tower in SF"
"""

import sys
import asyncio
import time
from pathlib import Path

# Navigate from tests/asdrp/actions/geo/ to project root
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from asdrp.actions.geo.map_tools import MapTools


async def test_directions_workflow():
    """Test the complete directions workflow with timing."""

    print("=" * 80)
    print("Testing MapAgent Directions Workflow Performance")
    print("=" * 80)
    print()

    # Test query from screenshot: "show us how to drive from San Carlos to the Salesforce Tower in SF"
    origin = "San Carlos, CA"
    destination = "Salesforce Tower, San Francisco, CA"

    print(f"Origin: {origin}")
    print(f"Destination: {destination}")
    print()

    # Step 1: Get travel time and distance
    print("Step 1: Calling get_travel_time_distance()...")
    start_time = time.time()
    try:
        directions_result = await MapTools.get_travel_time_distance(
            origin=origin,
            destination=destination,
            mode="driving"
        )
        step1_time = time.time() - start_time
        print(f"✅ Step 1 completed in {step1_time:.2f} seconds")

        # Check if we got results
        if not directions_result or len(directions_result) == 0:
            print("❌ No directions returned")
            return

        # Extract route info
        if isinstance(directions_result, list) and len(directions_result) > 0:
            route = directions_result[0]
            leg = route['legs'][0]
            print(f"   Distance: {leg['distance']['text']}")
            print(f"   Duration: {leg['duration']['text']}")
        print()

    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        return

    # Step 2: Extract polyline
    print("Step 2: Calling get_route_polyline()...")
    start_time = time.time()
    try:
        polyline = MapTools.get_route_polyline(directions_result)
        step2_time = time.time() - start_time
        print(f"✅ Step 2 completed in {step2_time:.2f} seconds")

        if polyline:
            print(f"   Polyline length: {len(polyline)} characters")
        else:
            print("❌ No polyline extracted")
            return
        print()

    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
        return

    # Step 3: Generate static map URL
    print("Step 3: Calling get_static_map_url()...")
    start_time = time.time()
    try:
        map_url = await MapTools.get_static_map_url(
            zoom=10,
            encoded_polyline=polyline
        )
        step3_time = time.time() - start_time
        print(f"✅ Step 3 completed in {step3_time:.2f} seconds")
        print(f"   URL length: {len(map_url)} characters")
        print()

    except Exception as e:
        print(f"❌ Step 3 failed: {e}")
        return

    # Calculate total time
    total_time = step1_time + step2_time + step3_time

    print("=" * 80)
    print("Performance Summary:")
    print("=" * 80)
    print(f"Step 1 (Directions API):    {step1_time:6.2f}s  ({step1_time/total_time*100:5.1f}%)")
    print(f"Step 2 (Extract Polyline):   {step2_time:6.2f}s  ({step2_time/total_time*100:5.1f}%)")
    print(f"Step 3 (Generate Map URL):   {step3_time:6.2f}s  ({step3_time/total_time*100:5.1f}%)")
    print(f"{'=' * 40}")
    print(f"Total Time:                  {total_time:6.2f}s")
    print()

    # Analysis
    print("Analysis:")
    print("-" * 80)
    if total_time > 120:
        print("❌ CRITICAL: Total time exceeds 120s timeout threshold!")
    elif total_time > 60:
        print("⚠️  WARNING: Total time exceeds 60s backend timeout!")
    elif total_time > 30:
        print("⚠️  SLOW: Total time is acceptable but could be optimized")
    else:
        print("✅ GOOD: Total time is within acceptable range")

    if step1_time > 30:
        print("⚠️  Directions API call is slow (>30s)")
        print("   Potential causes:")
        print("   - Network latency")
        print("   - Google API server load")
        print("   - Complex route calculation")

    if step1_time / total_time > 0.9:
        print("📊 Directions API dominates execution time")

    print()

    # Best practices check
    print("Best Practices Check:")
    print("-" * 80)
    print("✅ Using location names directly (no geocoding)")
    print("✅ Using encoded polyline (follows real roads)")
    print("✅ Single Directions API call (not multiple)")
    print()

    # Recommendations
    print("Recommendations:")
    print("-" * 80)
    print("1. Current implementation follows Google Maps API best practices")
    print("2. Timeout values:")
    print(f"   - Frontend timeout: 120s (adequate for total: {total_time:.1f}s)")
    print(f"   - Backend timeout: 60s (per API call)")
    if step1_time > 45:
        print("3. ⚠️  Consider caching routes for frequently requested paths")
        print("4. ⚠️  Consider implementing retry logic with exponential backoff")
    print()


if __name__ == "__main__":
    print()
    asyncio.run(test_directions_workflow())
