#!/usr/bin/env python3
"""
Test script for semantic MoE routing.

This script tests the semantic expert selector to ensure queries
correctly route to appropriate agents using embedding similarity.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import pytest

# Load environment variables from server/.env
env_path = Path(__file__).parent / "server" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from {env_path}")
else:
    print(f"Warning: {env_path} not found")

# Verify API key is set
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not set. Please set it in server/.env or environment.")
    exit(1)

from asdrp.orchestration.moe.config_loader import load_moe_config
from asdrp.orchestration.moe.semantic_selector import SemanticSelector


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_routing():
    """Test semantic routing for various query types."""

    # Load config
    config = load_moe_config()
    selector = SemanticSelector(config)

    # Test queries
    test_cases = [
        {
            "query": "San Carlos",
            "expected_types": ["location"],
            "description": "Place name query"
        },
        {
            "query": "directions to San Francisco",
            "expected_types": ["location"],
            "description": "Directions query"
        },
        {
            "query": "how do I get to Mountain View",
            "expected_types": ["location"],
            "description": "Navigation query"
        },
        {
            "query": "where is New York",
            "expected_types": ["location"],
            "description": "Location query"
        },
        {
            "query": "restaurants near me",
            "expected_types": ["business"],
            "description": "Business search query"
        },
        {
            "query": "pizza places nearby",
            "expected_types": ["business"],
            "description": "Food search query"
        },
        {
            "query": "what is the capital of France",
            "expected_types": ["knowledge", "search"],
            "description": "Knowledge query"
        },
        {
            "query": "stock price of AAPL",
            "expected_types": ["finance"],
            "description": "Finance query"
        },
        {
            "query": "tell me about quantum computing",
            "expected_types": ["knowledge", "search"],
            "description": "General knowledge query"
        },
    ]

    # Agent type mapping
    agent_types = {
        "geo": "location",
        "map": "location",
        "yelp": "business",
        "yelp_mcp": "business",
        "finance": "finance",
        "wiki": "knowledge",
        "perplexity": "search",
        "one": "search",
        "chitchat": "chitchat"
    }

    print("\n" + "="*80)
    print("Semantic MoE Routing Test")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    for test_case in test_cases:
        query = test_case["query"]
        expected_types = test_case["expected_types"]
        description = test_case["description"]

        print(f"\n📝 Test: {description}")
        print(f"Query: '{query}'")
        print(f"Expected types: {expected_types}")

        try:
            # Run selector
            selected = await selector.select(query, k=3, threshold=0.5)

            print(f"Selected agents: {selected}")

            # Map selected agents to types
            selected_types = [agent_types.get(agent, "unknown") for agent in selected]
            print(f"Selected types: {selected_types}")

            # Check if at least one expected type was selected
            matches = [t for t in selected_types if t in expected_types]

            if matches:
                print(f"✅ PASS - Matched types: {matches}")
                passed += 1
            else:
                print(f"❌ FAIL - Expected one of {expected_types}, got {selected_types}")
                failed += 1

        except Exception as e:
            print(f"❌ ERROR - {e}")
            failed += 1

    print("\n" + "="*80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*80 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_semantic_routing())
    exit(0 if success else 1)
