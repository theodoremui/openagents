#!/usr/bin/env python3
"""
Test business header extraction regex against actual YelpMCP output.
"""

import re

# Current regex from result_mixer.py
BUSINESS_HEADER_REGEX = re.compile(
    r"(?:^\s*##\s*Business\s*\d+\s*:\s*(.+?)\s*$|^\s*\d+\.\s*\*\*(.+?)\*\*)",
    re.IGNORECASE | re.MULTILINE
)

# Test with actual YelpMCP output format
actual_yelp_output = """# Formatted Business Data for LLM Processing

## Introduction
Here are some great Greek restaurants in San Francisco based on your query.

## Chat ID
abc123

## Business 1: Kokkari Estiatorio
- **Price**: $$$$
- **Rating**: 4.5/5 (1234 reviews)
- **Type**: Greek, Seafood
- **Location**: 200 Jackson St, San Francisco, CA 94111
- **Coordinates**: 37.796996, -122.398661
- **URL**: [View on Yelp](https://www.yelp.com/biz/kokkari-estiatorio-san-francisco)
- **Phone**: (415) 981-0983

## Business 2: Milos Mezes
- **Price**: $$$
- **Rating**: 4.0/5 (567 reviews)
- **Type**: Greek, Mediterranean
- **Location**: 3348 Steiner St, San Francisco, CA 94123
- **Coordinates**: 37.800333, -122.423670
- **URL**: [View on Yelp](https://www.yelp.com/biz/milos-mezes-san-francisco)
- **Phone**: (415) 563-8368

## Business 3: Souvla
- **Price**: $$
- **Rating**: 4.2/5 (890 reviews)
- **Type**: Greek, Fast Food
- **Location**: 517 Hayes St, San Francisco, CA 94102
- **Coordinates**: 37.776685, -122.423943
- **URL**: [View on Yelp](https://www.yelp.com/biz/souvla-san-francisco)
- **Phone**: (415) 400-4500"""

def test_business_header_extraction():
    print("🏢 BUSINESS HEADER EXTRACTION TESTING")
    print("=" * 60)
    
    # Test business header extraction
    headers_raw = BUSINESS_HEADER_REGEX.findall(actual_yelp_output)
    print(f"Raw header matches: {len(headers_raw)}")
    
    headers = []
    for h in headers_raw:
        if isinstance(h, tuple):
            # From alternation: ("Name", "") or ("", "Name")
            name = h[0] or h[1] if len(h) >= 2 else h[0]
        else:
            name = h
        if name:
            headers.append(name.strip())
            print(f"  - Business: '{name.strip()}'")
    
    print(f"\nExtracted business names: {len(headers)}")
    
    # Test coordinate extraction
    COORD_REGEX = re.compile(
        r"^\s*(?:-\s*)?(?:\*\*)?(Coordinates|Location|Lat|Position)(?:\*\*)?:\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*$",
        re.IGNORECASE | re.MULTILINE
    )
    
    coords_raw = COORD_REGEX.findall(actual_yelp_output)
    coords = [(lat_s, lng_s) for (_, lat_s, lng_s) in coords_raw]
    
    print(f"Coordinate matches: {len(coords)}")
    for i, (lat_s, lng_s) in enumerate(coords):
        print(f"  - Coordinates {i+1}: ({lat_s}, {lng_s})")
    
    # Test pairing
    print(f"\nPairing Analysis:")
    print(f"  - Business names: {len(headers)}")
    print(f"  - Coordinate pairs: {len(coords)}")
    
    if len(headers) == len(coords):
        print("  ✅ Perfect match - should create markers")
        for name, (lat_s, lng_s) in zip(headers, coords):
            try:
                lat = float(lat_s)
                lng = float(lng_s)
                print(f"    ✅ {name} → ({lat}, {lng})")
            except ValueError as e:
                print(f"    ❌ {name} → Failed to parse: {e}")
    else:
        print("  ❌ Mismatch - no markers will be created")

if __name__ == "__main__":
    test_business_header_extraction()