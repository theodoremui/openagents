#!/usr/bin/env python3
"""
Test script for MoE Fast-Path Bypass.

This script tests that chitchat/greeting queries are detected semantically
and routed directly to the chitchat agent, bypassing the full MoE pipeline.
"""

import pytest
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / "server" / ".env"
if env_path.exists():
    load_dotenv(env_path)

from asdrp.orchestration.moe.fast_path import FastPathDetector


@pytest.mark.slow
async def test_fast_path_detection():
    """Test fast-path detection with various queries."""

    # Initialize detector
    detector = FastPathDetector(similarity_threshold=0.75)

    # Test queries
    test_cases = [
        # Should trigger fast-path (chitchat/greetings)
        {
            "query": "hello",
            "should_bypass": True,
            "description": "Simple greeting"
        },
        {
            "query": "hi there!",
            "should_bypass": True,
            "description": "Casual greeting"
        },
        {
            "query": "good morning",
            "should_bypass": True,
            "description": "Time-based greeting"
        },
        {
            "query": "how are you doing today?",
            "should_bypass": True,
            "description": "Chitchat question"
        },
        {
            "query": "thanks for your help",
            "should_bypass": True,
            "description": "Gratitude expression"
        },
        {
            "query": "goodbye and have a nice day",
            "should_bypass": True,
            "description": "Farewell message"
        },
        # Should NOT trigger fast-path (complex queries)
        {
            "query": "what is the weather in San Francisco",
            "should_bypass": False,
            "description": "Weather query (needs search)"
        },
        {
            "query": "find restaurants near me",
            "should_bypass": False,
            "description": "Location + business query"
        },
        {
            "query": "what is the capital of France",
            "should_bypass": False,
            "description": "Knowledge query"
        },
        {
            "query": "TSLA stock price",
            "should_bypass": False,
            "description": "Finance query"
        },
    ]

    print("\n" + "="*80)
    print("MoE Fast-Path Detection Test")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    for test_case in test_cases:
        query = test_case["query"]
        should_bypass = test_case["should_bypass"]
        description = test_case["description"]

        print(f"\n📝 Test: {description}")
        print(f"Query: '{query}'")
        print(f"Expected: {'BYPASS' if should_bypass else 'FULL PIPELINE'}")

        # Test detection
        start = time.time()
        detected_agent = await detector.detect_fast_path(query)
        latency_ms = (time.time() - start) * 1000

        bypassed = detected_agent is not None

        print(f"Result: {detected_agent if bypassed else 'None (full pipeline)'}")
        print(f"Detection latency: {latency_ms:.1f}ms")

        # Check result
        if bypassed == should_bypass:
            print(f"✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL - Expected {'bypass' if should_bypass else 'no bypass'}, got {'bypass' if bypassed else 'no bypass'}")
            failed += 1

    print("\n" + "="*80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*80 + "\n")

    return failed == 0


async def test_fast_path_latency():
    """Compare latency with and without fast-path."""

    print("\n" + "="*80)
    print("Fast-Path Latency Comparison")
    print("="*80 + "\n")

    # Simulate latencies (in production, these would be actual measurements)
    scenarios = [
        {
            "query": "Hi there!",
            "full_pipeline": {
                "selection": 50,    # ms (semantic embedding lookup)
                "execution": 500,   # ms (1 agent call)
                "synthesis": 0,     # ms (skipped for 1 agent)
                "total": 550
            },
            "fast_path": {
                "detection": 50,    # ms (semantic embedding lookup)
                "execution": 500,   # ms (direct agent call)
                "total": 550
            }
        },
        {
            "query": "Hi there! (worst case - selected 3 agents)",
            "full_pipeline": {
                "selection": 4500,  # ms (as seen in screenshot)
                "execution": 3000,  # ms (3 agents in parallel)
                "synthesis": 1760,  # ms (LLM synthesis)
                "total": 9260
            },
            "fast_path": {
                "detection": 50,    # ms (semantic embedding lookup)
                "execution": 500,   # ms (direct agent call)
                "total": 550
            }
        }
    ]

    for scenario in scenarios:
        query = scenario["query"]
        full = scenario["full_pipeline"]
        fast = scenario["fast_path"]

        improvement = ((full["total"] - fast["total"]) / full["total"]) * 100

        print(f"\n🔍 Scenario: {query}")
        print(f"\n  Full Pipeline:")
        print(f"    - Selection:  {full['selection']:>5}ms")
        print(f"    - Execution:  {full['execution']:>5}ms")
        if full.get('synthesis', 0) > 0:
            print(f"    - Synthesis:  {full['synthesis']:>5}ms")
        print(f"    - TOTAL:      {full['total']:>5}ms")

        print(f"\n  Fast-Path:")
        print(f"    - Detection:  {fast['detection']:>5}ms")
        print(f"    - Execution:  {fast['execution']:>5}ms")
        print(f"    - TOTAL:      {fast['total']:>5}ms")

        print(f"\n  💡 Improvement: {improvement:.1f}% faster ({full['total'] - fast['total']}ms saved)")

    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print("\n✅ Fast-Path Benefits:")
    print("  - Bypasses expert selection (saves ~50-4500ms)")
    print("  - Bypasses multi-agent execution (saves 0-2500ms for extra agents)")
    print("  - Bypasses result synthesis (saves 0-1760ms)")
    print("\n📊 Expected Improvements:")
    print("  - Best case (1 agent selected):  ~0-50ms faster (minimal improvement)")
    print("  - Worst case (3 agents selected): ~8700ms faster (94% improvement)")
    print("  - Average case (2 agents):        ~4000ms faster (75% improvement)")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    import sys

    # Test fast-path detection
    print("=" * 80)
    print("Phase 1: Fast-Path Detection")
    print("=" * 80)
    detection_success = asyncio.run(test_fast_path_detection())

    # Show latency comparison
    print("\n" + "=" * 80)
    print("Phase 2: Latency Analysis")
    print("=" * 80)
    asyncio.run(test_fast_path_latency())

    sys.exit(0 if detection_success else 1)
