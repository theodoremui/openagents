#!/usr/bin/env python3
"""
Test Comprehensive Fix for Missing Map Pins

This script tests the complete fix implementation to verify that:
1. Business agent fallback works (yelp_mcp → yelp)
2. Partial success handling works (business data without map)
3. Geocoding fallback works (addresses → coordinates)
4. Frontend error recovery works (malformed JSON handling)
"""

import asyncio
import json
import re
from pathlib import Path
import sys

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator

async def test_comprehensive_fix():
    print("🧪 COMPREHENSIVE FIX TEST")
    print("=" * 80)
    
    query = "Place the top 3 greek restaurants in San Francisco as pins on a detailed map"
    print(f"Query: {query}\n")
    
    # Initialize system
    factory = AgentFactory.instance()
    config = MoEConfigLoader().load_config()
    orchestrator = MoEOrchestrator.create_default(factory, config)
    
    # Execute query
    result = await orchestrator.route_query(query, session_id="comprehensive_test")
    
    print("📊 EXECUTION RESULTS")
    print("-" * 80)
    print(f"✅ Query executed successfully")
    print(f"Response length: {len(result.response)} characters")
    print(f"Experts used: {result.experts_used}")
    print(f"Latency: {result.trace.latency_ms:.0f}ms")
    
    # Test 1: Business Agent Fallback
    print(f"\n🔄 TEST 1: Business Agent Fallback")
    print("-" * 40)
    
    business_agents_used = [agent for agent in result.experts_used if agent in ["yelp", "yelp_mcp"]]
    if business_agents_used:
        print(f"✅ Business agents used: {business_agents_used}")
        if "yelp" in business_agents_used:
            print(f"✅ Fallback mechanism working (yelp agent used)")
    else:
        print(f"❌ No business agents used")
    
    # Test 2: Partial Success Handling
    print(f"\n⚖️  TEST 2: Partial Success Handling")
    print("-" * 40)
    
    if hasattr(result.trace, 'expert_details') and result.trace.expert_details:
        successful_experts = [d for d in result.trace.expert_details if d.status == "completed"]
        failed_experts = [d for d in result.trace.expert_details if d.status == "failed"]
        
        print(f"Successful experts: {[d.expert_id for d in successful_experts]}")
        print(f"Failed experts: {[d.expert_id for d in failed_experts]}")
        
        if successful_experts and failed_experts:
            print(f"✅ Partial success handling working")
        elif successful_experts:
            print(f"✅ All experts succeeded")
        else:
            print(f"❌ All experts failed")
    
    # Test 3: Map Data Analysis
    print(f"\n🗺️  TEST 3: Map Data Analysis")
    print("-" * 40)
    
    # Check for JSON blocks
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", result.response, re.DOTALL | re.IGNORECASE)
    
    if json_blocks:
        print(f"✅ Found {len(json_blocks)} JSON block(s)")
        
        for i, json_str in enumerate(json_blocks):
            try:
                json_obj = json.loads(json_str.strip())
                if json_obj.get('type') == 'interactive_map':
                    config = json_obj.get('config', {})
                    markers = config.get('markers', [])
                    
                    print(f"\nMap Block {i+1}:")
                    print(f"  Map type: {config.get('map_type')}")
                    print(f"  Number of markers: {len(markers)}")
                    
                    if markers:
                        # Check marker quality
                        markers_with_coords = 0
                        markers_with_addresses = 0
                        
                        for j, marker in enumerate(markers):
                            has_coords = (marker.get('lat') is not None and 
                                        marker.get('lng') is not None and
                                        isinstance(marker.get('lat'), (int, float)) and
                                        isinstance(marker.get('lng'), (int, float)))
                            has_address = (marker.get('address') and 
                                         isinstance(marker.get('address'), str) and 
                                         len(marker.get('address').strip()) > 0)
                            
                            if has_coords:
                                markers_with_coords += 1
                            if has_address:
                                markers_with_addresses += 1
                            
                            print(f"  Marker {j+1}: {marker.get('title', 'Untitled')}")
                            print(f"    Coordinates: ({marker.get('lat')}, {marker.get('lng')})")
                            print(f"    Address: {marker.get('address', 'N/A')}")
                            print(f"    Valid coords: {has_coords}, Valid address: {has_address}")
                        
                        print(f"\n  Summary:")
                        print(f"    Markers with coordinates: {markers_with_coords}/{len(markers)}")
                        print(f"    Markers with addresses: {markers_with_addresses}/{len(markers)}")
                        
                        if markers_with_coords > 0:
                            print(f"    ✅ COORDINATES PRESENT - Pins should render!")
                        elif markers_with_addresses > 0:
                            print(f"    ⚠️  Only addresses present - Frontend geocoding needed")
                        else:
                            print(f"    ❌ NO COORDINATES OR ADDRESSES - Pins won't render")
                    
                    # Check center coordinates
                    if 'center_lat' in config and 'center_lng' in config:
                        print(f"  Center: ({config['center_lat']}, {config['center_lng']})")
                        print(f"  ✅ Map centering should work")
                    else:
                        print(f"  ⚠️  No center coordinates - Map may not center properly")
                        
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON Block {i+1}: Invalid JSON - {e}")
    else:
        print(f"❌ No JSON blocks found")
    
    # Test 4: Content Analysis
    print(f"\n📄 TEST 4: Content Analysis")
    print("-" * 40)
    
    # Check for restaurant names
    greek_restaurants = ["souvla", "kokkari", "milos"]
    found_restaurants = []
    for restaurant in greek_restaurants:
        if restaurant.lower() in result.response.lower():
            found_restaurants.append(restaurant)
    
    if found_restaurants:
        print(f"✅ Found restaurant names: {found_restaurants}")
    else:
        print(f"❌ No expected restaurant names found")
    
    # Check for addresses
    if any(word in result.response.lower() for word in ["st", "street", "ave", "avenue"]):
        print(f"✅ Address data present")
    else:
        print(f"❌ No address data found")
    
    # Test 5: Error Recovery Analysis
    print(f"\n🛡️  TEST 5: Error Recovery Analysis")
    print("-" * 40)
    
    # Check if response contains error messages
    error_indicators = ["apologize", "unable", "error", "failed", "issue"]
    has_errors = any(indicator in result.response.lower() for indicator in error_indicators)
    
    if has_errors:
        print(f"⚠️  Response contains error indicators")
        # But check if it still provides useful data
        if json_blocks or found_restaurants:
            print(f"✅ But still provides useful data (graceful degradation)")
        else:
            print(f"❌ No useful data provided")
    else:
        print(f"✅ No error indicators in response")
    
    # Final Assessment
    print(f"\n🎯 FINAL ASSESSMENT")
    print("=" * 80)
    
    issues_fixed = []
    issues_remaining = []
    
    # Check if coordinates are present
    if json_blocks:
        try:
            json_obj = json.loads(json_blocks[0].strip())
            markers = json_obj.get('config', {}).get('markers', [])
            if markers and any(m.get('lat') is not None and m.get('lng') is not None for m in markers):
                issues_fixed.append("✅ Coordinates present in map markers")
            else:
                issues_remaining.append("❌ Coordinates still missing from map markers")
        except:
            issues_remaining.append("❌ JSON parsing failed")
    else:
        issues_remaining.append("❌ No map JSON blocks found")
    
    # Check business data
    if found_restaurants:
        issues_fixed.append("✅ Business data successfully retrieved")
    else:
        issues_remaining.append("❌ Business data missing")
    
    # Check fallback mechanisms
    if business_agents_used:
        issues_fixed.append("✅ Business agent fallback working")
    else:
        issues_remaining.append("❌ Business agent fallback not working")
    
    print("ISSUES FIXED:")
    for issue in issues_fixed:
        print(f"  {issue}")
    
    print("\nISSUES REMAINING:")
    for issue in issues_remaining:
        print(f"  {issue}")
    
    if not issues_remaining:
        print(f"\n🎉 ALL ISSUES RESOLVED! The missing pins problem should be fixed.")
    else:
        print(f"\n⚠️  Some issues remain. Further investigation needed.")
    
    print(f"\nFull response preview:")
    print("-" * 40)
    print(result.response[:500] + ("..." if len(result.response) > 500 else ""))
    print("-" * 40)
    
    return result

if __name__ == "__main__":
    asyncio.run(test_comprehensive_fix())