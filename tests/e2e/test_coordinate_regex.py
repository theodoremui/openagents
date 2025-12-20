#!/usr/bin/env python3
"""
Test coordinate extraction regex patterns against actual YelpMCP output.
"""

import re

# Current regex from result_mixer.py
CURRENT_COORD_REGEX = re.compile(
    r"^\s*(?:-\s*)?(?:\*\*)?(Coordinates|Location|Lat|Position)(?:\*\*)?:\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*$",
    re.IGNORECASE | re.MULTILINE
)

# Fixed regex (remove ^ and $ anchors)
FIXED_COORD_REGEX = re.compile(
    r"(?:-\s*)?(?:\*\*)?(Coordinates|Location|Lat|Position)(?:\*\*)?:\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)",
    re.IGNORECASE
)

# Test cases from actual YelpMCP output
test_cases = [
    # Actual YelpMCP format
    "- **Coordinates**: 37.796996, -122.398661",
    
    # In context (this is what actually appears)
    """- **Location**: 200 Jackson St, San Francisco, CA 94111
- **Coordinates**: 37.796996, -122.398661
- **URL**: [View on Yelp](https://www.yelp.com/biz/kokkari-estiatorio-san-francisco)""",
    
    # Multi-line business entry
    """## Business 1: Kokkari Estiatorio
- **Price**: $$$$
- **Rating**: 4.5/5 (1234 reviews)
- **Type**: Greek, Seafood
- **Location**: 200 Jackson St, San Francisco, CA 94111
- **Coordinates**: 37.796996, -122.398661
- **URL**: [View on Yelp](https://www.yelp.com/biz/kokkari-estiatorio-san-francisco)
- **Phone**: (415) 981-0983""",
]

def test_regex_patterns():
    print("🔍 COORDINATE REGEX PATTERN TESTING")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}:")
        print(f"Content: {repr(test_case[:100])}...")
        
        # Test current regex
        current_matches = CURRENT_COORD_REGEX.findall(test_case)
        print(f"Current regex matches: {len(current_matches)}")
        for match in current_matches:
            print(f"  - {match}")
        
        # Test fixed regex
        fixed_matches = FIXED_COORD_REGEX.findall(test_case)
        print(f"Fixed regex matches: {len(fixed_matches)}")
        for match in fixed_matches:
            print(f"  - {match}")
        
        if len(fixed_matches) > len(current_matches):
            print("  ✅ Fixed regex finds more matches!")
        elif len(current_matches) == len(fixed_matches) == 0:
            print("  ❌ Neither regex finds matches")
        else:
            print("  ⚠️  Same number of matches")

if __name__ == "__main__":
    test_regex_patterns()