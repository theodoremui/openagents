"""
Tests for CapabilityRouter Cache Integration

Verifies that:
- Cache is correctly initialized
- Routing decisions are cached
- Cache hits reduce processing time
- Cache can be disabled
"""

import pytest
from asdrp.orchestration.smartrouter.capability_router import CapabilityRouter
from asdrp.orchestration.smartrouter.interfaces import Subquery, RoutingPattern
from asdrp.orchestration.smartrouter.cache import get_capability_cache, get_routing_cache


@pytest.fixture
def capability_map():
    """Sample capability map for testing."""
    return {
        "geo": ["geocoding", "reverse_geocoding", "mapping"],
        "finance": ["stocks", "market_data", "currency"],
        "one": ["search", "general_knowledge", "web_search"],
    }


@pytest.fixture
def sample_subquery():
    """Sample subquery for testing."""
    return Subquery(
        id="sq1",
        text="Find address for coordinates",
        capability_required="reverse_geocoding",
        dependencies=[],
        routing_pattern=RoutingPattern.DELEGATION,
        metadata={},
    )


class TestCapabilityRouterCacheIntegration:
    """Tests for cache integration in CapabilityRouter."""

    def test_cache_enabled_by_default(self, capability_map):
        """Test that cache is enabled by default."""
        router = CapabilityRouter(capability_map)
        assert router.use_cache is True

    def test_cache_can_be_disabled(self, capability_map):
        """Test that cache can be explicitly disabled."""
        router = CapabilityRouter(capability_map, use_cache=False)
        assert router.use_cache is False

    def test_capability_cache_initialization(self, capability_map):
        """Test that capability cache is initialized on router creation."""
        # Clear any existing cache
        capability_cache = get_capability_cache()
        capability_cache._cache.clear()
        capability_cache._reverse_cache.clear()
        capability_cache._initialized = False

        # Create router (should initialize cache)
        router = CapabilityRouter(capability_map, use_cache=True)

        # Verify cache is initialized
        assert capability_cache.is_initialized()

        # Verify cache contains correct data
        geo_caps = capability_cache.get_agent_capabilities("geo")
        assert geo_caps == ["geocoding", "reverse_geocoding", "mapping"]

        # Verify reverse index
        geocoding_agents = capability_cache.find_agents_for_capability("geocoding")
        assert "geo" in geocoding_agents

    def test_routing_cache_stores_decisions(self, capability_map, sample_subquery):
        """Test that routing decisions are cached."""
        # Clear routing cache
        routing_cache = get_routing_cache()
        routing_cache.clear()

        router = CapabilityRouter(capability_map, use_cache=True)

        # First routing (cache miss)
        agent_id, pattern = router.route(sample_subquery)
        assert agent_id == "geo"
        assert pattern == RoutingPattern.DELEGATION

        # Verify routing was cached
        cached_agent = routing_cache.get_routing("reverse_geocoding")
        assert cached_agent == "geo"

    def test_cache_hit_returns_cached_agent(self, capability_map, sample_subquery):
        """Test that cache hit returns cached agent without re-routing."""
        # Clear and pre-populate routing cache
        routing_cache = get_routing_cache()
        routing_cache.clear()
        routing_cache.set_routing("reverse_geocoding", "geo")

        router = CapabilityRouter(capability_map, use_cache=True)

        # Route (should hit cache)
        agent_id, pattern = router.route(sample_subquery)
        assert agent_id == "geo"
        assert pattern == RoutingPattern.DELEGATION

    def test_cache_disabled_routes_normally(self, capability_map, sample_subquery):
        """Test that routing works normally when cache is disabled."""
        router = CapabilityRouter(capability_map, use_cache=False)

        # Route without cache
        agent_id, pattern = router.route(sample_subquery)
        assert agent_id == "geo"
        assert pattern == RoutingPattern.DELEGATION

    def test_cache_miss_falls_through_to_routing(self, capability_map):
        """Test that cache miss triggers normal routing logic."""
        # Clear routing cache
        routing_cache = get_routing_cache()
        routing_cache.clear()

        router = CapabilityRouter(capability_map, use_cache=True)

        # Create subquery with capability not in cache
        subquery = Subquery(
            id="sq2",
            text="Search for stock price",
            capability_required="stocks",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={},
        )

        # Route (cache miss, should fall through)
        agent_id, pattern = router.route(subquery)
        assert agent_id == "finance"
        assert pattern == RoutingPattern.DELEGATION

        # Verify result was cached
        cached_agent = routing_cache.get_routing("stocks")
        assert cached_agent == "finance"

    def test_capability_cache_finds_agents(self, capability_map):
        """Test that capability cache correctly finds agents."""
        router = CapabilityRouter(capability_map, use_cache=True)
        capability_cache = get_capability_cache()

        # Test exact capability match
        geocoding_agents = capability_cache.find_agents_for_capability("geocoding")
        assert "geo" in geocoding_agents

        # Test multi-agent capability
        # (In this test data, only geo has geocoding)
        assert len(geocoding_agents) == 1

    def test_routing_cache_metrics(self, capability_map, sample_subquery):
        """Test that routing cache tracks hits and misses."""
        # Clear routing cache
        routing_cache = get_routing_cache()
        routing_cache.clear()

        router = CapabilityRouter(capability_map, use_cache=True)

        # First route (miss)
        router.route(sample_subquery)

        # Second route (hit)
        router.route(sample_subquery)

        # Check metrics
        metrics = routing_cache.get_metrics()
        assert metrics["hits"] >= 1  # At least one hit
        assert metrics["misses"] >= 1  # At least one miss

    def test_multiple_routes_same_capability(self, capability_map):
        """Test that multiple routes for same capability use cache."""
        # Clear routing cache
        routing_cache = get_routing_cache()
        routing_cache.clear()

        router = CapabilityRouter(capability_map, use_cache=True)

        # Create multiple subqueries with same capability
        subqueries = [
            Subquery(
                id=f"sq{i}",
                text=f"Query {i}",
                capability_required="geocoding",
                dependencies=[],
                routing_pattern=RoutingPattern.DELEGATION,
                metadata={},
            )
            for i in range(5)
        ]

        # Route all subqueries
        for subquery in subqueries:
            agent_id, _ = router.route(subquery)
            assert agent_id == "geo"

        # Check cache metrics (4 hits expected after first miss)
        metrics = routing_cache.get_metrics()
        assert metrics["hits"] >= 4

    def test_cache_respects_routing_pattern_from_subquery(self, capability_map):
        """Test that cache returns agent but respects subquery's routing pattern."""
        routing_cache = get_routing_cache()
        routing_cache.clear()
        routing_cache.set_routing("geocoding", "geo")

        router = CapabilityRouter(capability_map, use_cache=True)

        # Route with HANDOFF pattern
        subquery = Subquery(
            id="sq1",
            text="Test",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.HANDOFF,
            metadata={},
        )

        agent_id, pattern = router.route(subquery)
        assert agent_id == "geo"
        assert pattern == RoutingPattern.HANDOFF  # Should use subquery's pattern

    def test_cache_handles_fuzzy_match(self, capability_map):
        """Test that cache works with fuzzy capability matching."""
        router = CapabilityRouter(capability_map, use_cache=True)

        # Route with partial capability match
        subquery = Subquery(
            id="sq1",
            text="Test",
            capability_required="geo",  # Partial match for "geocoding"
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={},
        )

        agent_id, pattern = router.route(subquery)
        assert agent_id == "geo"  # Should match via fuzzy logic


class TestCapabilityRouterPerformance:
    """Performance tests for cache integration."""

    @pytest.mark.skip(reason="Requires pytest-benchmark (optional dependency)")
    def test_cache_improves_performance(self, capability_map, benchmark):
        """Test that cache improves routing performance (if pytest-benchmark installed)."""
        # This test requires pytest-benchmark
        # Skip if not available
        pytest.importorskip("pytest_benchmark")

        router = CapabilityRouter(capability_map, use_cache=True)

        subquery = Subquery(
            id="sq1",
            text="Test",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={},
        )

        # Benchmark routing (should hit cache after first call)
        def route():
            return router.route(subquery)

        result = benchmark(route)
        assert result[0] == "geo"
