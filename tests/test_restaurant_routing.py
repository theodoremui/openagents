"""
Diagnostic test for restaurant routing issue.

Tests what happens when SmartRouter receives:
Turn 1: "Tell me about Tokyo"
Turn 2: "Recommend the top 3 restaurants there"

This should route to yelp or yelp_mcp agent.
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import pytest
from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
from asdrp.agents.agent_factory import AgentFactory

# Load environment variables from server/.env
env_path = Path(__file__).parent / "server" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logger = logging.getLogger(__name__)
    logger.info(f"Loaded environment from {env_path}")
else:
    logger = logging.getLogger(__name__)
    logger.warning(f"No .env file found at {env_path}, using system environment")

# Verify API key is loaded
if not os.getenv("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY not found in environment!")
    logger.error("Please set OPENAI_API_KEY in server/.env or as environment variable")
else:
    logger.info("OPENAI_API_KEY loaded successfully")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_restaurant_routing():
    """Test restaurant query routing with session context."""

    # Initialize SmartRouter with session
    factory = AgentFactory.instance()
    router = SmartRouter.create(
        agent_factory=factory,
        config_path="config/smartrouter.yaml",
        session_id="test_restaurant_routing"
    )

    logger.info("\n" + "="*80)
    logger.info("TEST 1: First turn - Ask about Tokyo")
    logger.info("="*80)

    result1 = await router.route_query("Tell me about Tokyo")
    logger.info(f"\nResult 1:")
    logger.info(f"  Answer: {result1.answer[:200]}...")
    logger.info(f"  Agents used: {result1.agents_used}")
    logger.info(f"  Total time: {result1.total_time:.2f}s")

    logger.info("\n" + "="*80)
    logger.info("TEST 2: Second turn - Ask for restaurants")
    logger.info("="*80)

    result2 = await router.route_query("Recommend the top 3 restaurants there")
    logger.info(f"\nResult 2:")
    logger.info(f"  Answer: {result2.answer[:200]}...")
    logger.info(f"  Agents used: {result2.agents_used}")
    logger.info(f"  Total time: {result2.total_time:.2f}s")

    # Check if correct agent was used
    expected_agents = ["yelp", "yelp_mcp"]
    used_yelp = any(agent in result2.agents_used for agent in expected_agents)

    logger.info("\n" + "="*80)
    logger.info("DIAGNOSIS:")
    logger.info("="*80)
    logger.info(f"  Expected agents: {expected_agents}")
    logger.info(f"  Actually used: {result2.agents_used}")
    logger.info(f"  Used Yelp agent: {'✅ YES' if used_yelp else '❌ NO - BUG!'}")

    # Detailed trace analysis
    logger.info("\n" + "="*80)
    logger.info("TRACE ANALYSIS (Turn 2):")
    logger.info("="*80)

    for i, trace in enumerate(result2.traces, 1):
        # Traces might be dicts or objects
        if isinstance(trace, dict):
            phase = trace.get('phase', 'unknown')
            duration = trace.get('duration', 0)
            data = trace.get('data', {})
        else:
            phase = getattr(trace, 'phase', 'unknown')
            duration = getattr(trace, 'duration', 0)
            data = getattr(trace, 'data', {})

        logger.info(f"\n  Step {i}: {phase}")
        logger.info(f"    Duration: {duration:.2f}s")
        if data:
            if phase == "interpretation":
                logger.info(f"    Complexity: {data.get('complexity')}")
                logger.info(f"    Domains: {data.get('domains')}")
                logger.info(f"    Requires synthesis: {data.get('requires_synthesis')}")
            elif phase == "routing":
                logger.info(f"    Agent selected: {data.get('agent_id') or data.get('agent')}")
                logger.info(f"    Routing pattern: {data.get('routing_pattern') or data.get('pattern')}")

    return used_yelp


@pytest.mark.slow
@pytest.mark.asyncio
async def test_explicit_restaurant_query():
    """Test with explicit location (no session context needed)."""

    factory = AgentFactory.instance()
    router = SmartRouter.create(
        agent_factory=factory,
        config_path="config/smartrouter.yaml",
        session_id="test_explicit_restaurant"
    )

    logger.info("\n" + "="*80)
    logger.info("TEST 3: Explicit restaurant query")
    logger.info("="*80)

    result = await router.route_query("Find the top 3 restaurants in Tokyo")
    logger.info(f"\nResult:")
    logger.info(f"  Answer: {result.answer[:200]}...")
    logger.info(f"  Agents used: {result.agents_used}")
    logger.info(f"  Total time: {result.total_time:.2f}s")

    expected_agents = ["yelp", "yelp_mcp"]
    used_yelp = any(agent in result.agents_used for agent in expected_agents)
    logger.info(f"  Used Yelp agent: {'✅ YES' if used_yelp else '❌ NO - BUG!'}")

    return used_yelp


async def main():
    logger.info("Starting restaurant routing diagnostics...\n")

    try:
        # Test 1 & 2: Context-based query
        context_works = await test_restaurant_routing()

        # Test 3: Explicit query
        explicit_works = await test_explicit_restaurant_query()

        logger.info("\n" + "="*80)
        logger.info("SUMMARY:")
        logger.info("="*80)
        logger.info(f"  Context-based query (Turn 2): {'✅ WORKS' if context_works else '❌ FAILS'}")
        logger.info(f"  Explicit location query: {'✅ WORKS' if explicit_works else '❌ FAILS'}")

        if not context_works:
            logger.error("\n🔴 BUG CONFIRMED: SmartRouter fails to route context-based restaurant queries to Yelp agent!")
            logger.error("   Root cause investigation needed in QueryInterpreter and routing logic.")

    except Exception as e:
        logger.error(f"\n❌ Test failed with exception: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
