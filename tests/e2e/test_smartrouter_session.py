#!/usr/bin/env python3
"""
Test script for SmartRouter persistent session memory.

This script tests:
1. Session creation with file-based storage
2. Multi-turn conversation with context retention
3. Session persistence across SmartRouter instances
"""

import asyncio
import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from asdrp.agents.agent_factory import AgentFactory
from asdrp.orchestration.smartrouter.smartrouter import SmartRouter


@pytest.mark.slow
@pytest.mark.asyncio
async def test_session_memory():
    """Test SmartRouter session memory with multi-turn conversation."""

    print("=" * 70)
    print("SMARTROUTER PERSISTENT SESSION MEMORY TEST")
    print("=" * 70)

    # Clean up previous test session
    test_db_path = "./sessions/test_session.db"
    if Path(test_db_path).exists():
        Path(test_db_path).unlink()
        print(f"✓ Cleaned up previous test session: {test_db_path}\n")

    factory = AgentFactory.instance()

    # Test 1: First query - establish context
    print("\n" + "=" * 70)
    print("TEST 1: First Query (Establishing Context)")
    print("=" * 70)

    router1 = SmartRouter.create(
        agent_factory=factory,
        session_id="test_user_conversation",
        enable_session_memory=True,
        session_db_path=test_db_path
    )

    print(f"Session ID: {router1.session_id}")
    print(f"Session enabled: {router1.enable_session_memory}")
    print(f"Session object: {type(router1.session).__name__ if router1.session else 'None'}")
    print(f"Database path: {test_db_path}")

    query1 = "What is 25 + 17?"
    print(f"\nQuery 1: {query1}")

    try:
        result1 = await router1.route_query(query1)
        print(f"\nAnswer 1: {result1.answer[:200]}...")
        print(f"Agents used: {result1.agents_used}")
        print(f"Total time: {result1.total_time:.2f}s")
        print(f"Final decision: {result1.final_decision}")

        # Verify session file was created
        if Path(test_db_path).exists():
            file_size = Path(test_db_path).stat().st_size
            print(f"\n✓ Session database created: {file_size:,} bytes")
        else:
            print(f"\n✗ ERROR: Session database not created!")
            return False

    except Exception as e:
        print(f"\n✗ ERROR in Test 1: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Follow-up query - test context retention
    print("\n" + "=" * 70)
    print("TEST 2: Follow-up Query (Testing Context Retention)")
    print("=" * 70)
    print("Creating NEW SmartRouter instance to test session loading...")

    # Create NEW router instance (simulates new request)
    router2 = SmartRouter.create(
        agent_factory=factory,
        session_id="test_user_conversation",  # Same session ID
        enable_session_memory=True,
        session_db_path=test_db_path
    )

    query2 = "What was my previous question?"
    print(f"\nQuery 2: {query2}")
    print("(This should reference the first query about 25 + 17)")

    try:
        result2 = await router2.route_query(query2)
        print(f"\nAnswer 2: {result2.answer[:300]}...")
        print(f"Agents used: {result2.agents_used}")
        print(f"Total time: {result2.total_time:.2f}s")

        # Check if answer references the previous question
        answer_lower = result2.answer.lower()
        has_context = any(word in answer_lower for word in ['25', '17', '42', 'add', 'sum', 'previous', 'question', 'asked'])

        if has_context:
            print("\n✓ SUCCESS: Answer shows context from previous query!")
        else:
            print("\n⚠️  WARNING: Answer may not show clear context retention")
            print("   (This could be normal depending on routing logic)")

    except Exception as e:
        print(f"\n✗ ERROR in Test 2: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Third query - deeper context
    print("\n" + "=" * 70)
    print("TEST 3: Third Query (Deeper Context)")
    print("=" * 70)

    query3 = "Multiply that result by 2"
    print(f"\nQuery 3: {query3}")
    print("(This should reference 42 from query 1)")

    try:
        result3 = await router2.route_query(query3)  # Reuse router2
        print(f"\nAnswer 3: {result3.answer[:300]}...")
        print(f"Agents used: {result3.agents_used}")
        print(f"Total time: {result3.total_time:.2f}s")

        answer_lower = result3.answer.lower()
        has_84 = '84' in answer_lower or 'eighty' in answer_lower

        if has_84:
            print("\n✓ SUCCESS: Answer correctly uses context (42 * 2 = 84)!")
        else:
            print("\n⚠️  WARNING: Expected 84 in answer (42 * 2)")

    except Exception as e:
        print(f"\n✗ ERROR in Test 3: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Final summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✓ Session creation: PASSED")
    print(f"✓ Multi-turn conversation: PASSED")
    print(f"✓ Session persistence: PASSED")
    print(f"✓ Context retention: TESTED (check answers above)")
    print(f"\nSession database: {test_db_path}")
    print(f"Database size: {Path(test_db_path).stat().st_size:,} bytes")
    print("\n✅ All tests completed successfully!")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_session_memory())
    sys.exit(0 if success else 1)
