#!/usr/bin/env python3
"""
Quick diagnostic script to check which tools MapTools exposes.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from asdrp.actions.geo.map_tools import MapTools

print("MapTools.spec_functions:")
print("=" * 60)
for i, func_name in enumerate(MapTools.spec_functions, 1):
    print(f"{i:2d}. {func_name}")

print(f"\nTotal tools: {len(MapTools.spec_functions)}")

# Check for specific tools
print("\n" + "=" * 60)
print("Checking for new tools:")
print("=" * 60)

tools_to_check = ['get_route_polyline', 'get_static_map_url']
for tool in tools_to_check:
    if tool in MapTools.spec_functions:
        print(f"✅ {tool} - FOUND")
    else:
        print(f"❌ {tool} - NOT FOUND")

# Check if they exist as methods
print("\n" + "=" * 60)
print("Checking if methods exist on class:")
print("=" * 60)

for tool in tools_to_check:
    if hasattr(MapTools, tool):
        method = getattr(MapTools, tool)
        print(f"✅ {tool} - EXISTS (type: {type(method).__name__})")
    else:
        print(f"❌ {tool} - DOES NOT EXIST")
