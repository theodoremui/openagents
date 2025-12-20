#!/usr/bin/env python3
"""
Test map intent detection logic from MoE orchestrator.
"""

def test_map_intent_detection():
    """Test the map intent detection logic."""
    
    # Copy the logic from orchestrator.py
    def _prioritize_agents_for_map_intent(query: str, agent_ids: list[str], max_k: int) -> list[str]:
        if not agent_ids:
            return agent_ids

        if not isinstance(max_k, int) or max_k <= 0:
            return []

        q = (query or "").lower()

        # Strong intent markers for "show me pins / map view / where are they"
        map_markers = (
            "map",
            "maps", 
            "pin",
            "pins",
            "map view",
            "show on map",
            "show me on a map",
            "where are they",
            "where these",
            "detailed map",
            "interactive map",
        )
        map_intent = any(m in q for m in map_markers)
        
        print(f"Query: '{query}'")
        print(f"Query lowercase: '{q}'")
        print(f"Map markers: {map_markers}")
        print(f"Map intent detected: {map_intent}")
        
        if not map_intent:
            return agent_ids[:max_k]

        # If we have a map intent, we always want the MapAgent available.
        candidates = list(agent_ids)
        if "map" not in candidates:
            candidates.append("map")
            print(f"Added 'map' to candidates: {candidates}")

        business_markers = ("restaurant", "restaurants", "food", "dining", "cafe", "cafes", "bar", "bars")
        business_intent = any(m in q for m in business_markers) or ("yelp" in candidates) or ("yelp_mcp" in candidates)
        
        print(f"Business markers: {business_markers}")
        print(f"Business intent detected: {business_intent}")

        # For restaurant map requests, YelpMCPAgent is the best default
        if business_intent and "yelp_mcp" not in candidates:
            candidates.append("yelp_mcp")
            print(f"Added 'yelp_mcp' to candidates: {candidates}")

        preferred_order = []
        if business_intent:
            for a in ("yelp_mcp", "yelp"):
                if a in candidates:
                    preferred_order.append(a)
        
        # Map should come before geo for visualization
        if "map" in candidates:
            preferred_order.append("map")
        if "geo" in candidates:
            preferred_order.append("geo")

        # Fill remaining in original order
        seen = set(preferred_order)
        for a in candidates:
            if a not in seen:
                preferred_order.append(a)
                seen.add(a)

        print(f"Preferred order: {preferred_order}")

        # Enforce max_k but keep map within it
        trimmed = preferred_order[:max_k]
        if "map" not in trimmed:
            # Prefer replacing geo; otherwise replace last
            if "geo" in trimmed:
                idx = trimmed.index("geo")
                trimmed[idx] = "map"
                print(f"Replaced 'geo' with 'map': {trimmed}")
            else:
                trimmed[-1] = "map"
                print(f"Replaced last agent with 'map': {trimmed}")

        # Deduplicate while preserving order
        out = []
        seen2 = set()
        for a in trimmed:
            if a not in seen2:
                out.append(a)
                seen2.add(a)
        
        print(f"Final agent selection: {out}")
        return out

    # Test cases
    test_cases = [
        {
            "query": "Place the top 3 greek restaurants in San Francisco as pins on a detailed map",
            "initial_agents": ["yelp", "yelp_mcp", "geo"],
            "max_k": 3
        },
        {
            "query": "Find greek restaurants in San Francisco",
            "initial_agents": ["yelp", "yelp_mcp", "geo"],
            "max_k": 3
        },
        {
            "query": "Show me restaurants on a map",
            "initial_agents": ["yelp", "geo"],
            "max_k": 3
        }
    ]
    
    print("🗺️  MAP INTENT DETECTION TESTING")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}:")
        print("-" * 40)
        
        result = _prioritize_agents_for_map_intent(
            test_case["query"],
            test_case["initial_agents"],
            test_case["max_k"]
        )
        
        print(f"Expected: map agent should be included for map queries")
        print(f"Result: {'✅ PASS' if 'map' in result else '❌ FAIL'}")
        print()

if __name__ == "__main__":
    test_map_intent_detection()