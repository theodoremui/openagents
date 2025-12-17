#!/usr/bin/env python3
"""
Test script for MoE routing fix.

This script tests the expert selector to ensure location/directions queries
correctly route to geo/map agents instead of perplexity/one/chitchat.
"""

import asyncio
import pytest
from asdrp.orchestration.moe.config_loader import load_moe_config
from asdrp.orchestration.moe.expert_selector import CapabilityBasedSelector


@pytest.mark.slow
@pytest.mark.asyncio
async def test_location_queries():
    """Test various location-related queries."""

    # Load config
    config = load_moe_config()
    selector = CapabilityBasedSelector(config)

    # Test queries
    test_cases = [
        {
            "query": "San Carlos",
            "expected_agents": ["geo", "map"],
            "description": "Place name query"
        },
        {
            "query": "directions to San Francisco",
            "expected_agents": ["geo", "map"],
            "description": "Directions query"
        },
        {
            "query": "how do I get to Mountain View",
            "expected_agents": ["geo", "map"],
            "description": "Navigation query"
        },
        {
            "query": "where is New York",
            "expected_agents": ["geo", "map"],
            "description": "Location query"
        },
        {
            "query": "restaurants near me",
            "expected_agents": ["yelp", "yelp_mcp"],
            "description": "Business search query"
        },
        {
            "query": "what is the capital of France",
            "expected_agents": ["wiki", "perplexity", "one"],
            "description": "Knowledge query"
        },
        {
            "query": "stock price of AAPL",
            "expected_agents": ["finance"],
            "description": "Finance query"
        },
    ]

    print("\n" + "="*80)
    print("MoE Expert Selection Test")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    for test_case in test_cases:
        query = test_case["query"]
        expected = test_case["expected_agents"]
        description = test_case["description"]

        print(f"\n📝 Test: {description}")
        print(f"Query: '{query}'")
        print(f"Expected agents: {expected}")

        # Run selector
        selected = await selector.select(query, k=3, threshold=0.3)

        print(f"Selected agents: {selected}")

        # Check if at least one expected agent was selected
        matches = [agent for agent in selected if agent in expected]

        if matches:
            print(f"✅ PASS - Selected {matches}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected one of {expected}, got {selected}")
            failed += 1

    print("\n" + "="*80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*80 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_location_queries())
    exit(0 if success else 1)
