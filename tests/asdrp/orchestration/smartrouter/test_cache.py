"""
Tests for SmartRouter Caching Layer

Comprehensive test suite covering:
- LRU cache eviction
- TTL expiration
- Thread safety
- Performance metrics
- Capability cache
- Routing cache
"""

import pytest
import time
from threading import Thread
from asdrp.orchestration.smartrouter.cache import (
    LRUCache,
    CapabilityCache,
    RoutingCache,
    PerformanceMetrics,
    CacheEntry,
    get_capability_cache,
    get_routing_cache,
    get_performance_metrics,
)


class TestCacheEntry:
    """Tests for CacheEntry class."""

    def test_cache_entry_creation(self):
        """Test basic cache entry creation."""
        entry = CacheEntry(value="test_value", ttl_seconds=60)

        assert entry.value == "test_value"
        assert entry.ttl_seconds == 60
        assert entry.access_count == 0
        assert not entry.is_expired()

    def test_cache_entry_no_expiry(self):
        """Test cache entry without TTL never expires."""
        entry = CacheEntry(value="test_value", ttl_seconds=None)

        # Simulate time passing (won't actually wait)
        entry.created_at = time.time() - 10000

        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expires after TTL."""
        entry = CacheEntry(value="test_value", ttl_seconds=0.1)

        # Should not be expired immediately
        assert not entry.is_expired()

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired now
        assert entry.is_expired()

    def test_cache_entry_access_tracking(self):
        """Test cache entry tracks access count and time."""
        entry = CacheEntry(value="test_value")

        initial_accessed_at = entry.accessed_at
        assert entry.access_count == 0

        # Access entry
        time.sleep(0.01)
        value = entry.access()

        assert value == "test_value"
        assert entry.access_count == 1
        assert entry.accessed_at > initial_accessed_at

        # Access again
        entry.access()
        assert entry.access_count == 2


class TestLRUCache:
    """Tests for LRUCache class."""

    def test_cache_basic_operations(self):
        """Test basic get/set operations."""
        cache = LRUCache(max_size=10)

        # Set value
        cache.set("key1", "value1")

        # Get value
        assert cache.get("key1") == "value1"

        # Get non-existent key
        assert cache.get("key2") is None

    def test_cache_lru_eviction(self):
        """Test LRU eviction when max size exceeded."""
        cache = LRUCache(max_size=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # All should be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # Add one more (should evict key1 as least recently used)
        cache.set("key4", "value4")

        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_lru_access_order(self):
        """Test that accessing an entry makes it most recently used."""
        cache = LRUCache(max_size=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 (makes it most recently used)
        cache.get("key1")

        # Add key4 (should evict key2, not key1)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LRUCache(max_size=10, ttl_seconds=0.1)

        # Set value with default TTL
        cache.set("key1", "value1")

        # Should be present immediately
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        assert cache.get("key1") is None

    def test_cache_ttl_override(self):
        """Test per-entry TTL override."""
        cache = LRUCache(max_size=10, ttl_seconds=10.0)

        # Set value with custom TTL
        cache.set("key1", "value1", ttl_seconds=0.1)

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired despite default TTL being 10s
        assert cache.get("key1") is None

    def test_cache_metrics(self):
        """Test cache metrics tracking."""
        cache = LRUCache(max_size=2)

        # Initial metrics
        metrics = cache.get_metrics()
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0
        assert metrics["evictions"] == 0

        # Set and get (hit)
        cache.set("key1", "value1")
        cache.get("key1")

        metrics = cache.get_metrics()
        assert metrics["hits"] == 1
        assert metrics["misses"] == 0

        # Get non-existent (miss)
        cache.get("key2")

        metrics = cache.get_metrics()
        assert metrics["hits"] == 1
        assert metrics["misses"] == 1

        # Trigger eviction
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        metrics = cache.get_metrics()
        assert metrics["evictions"] == 1
        assert metrics["size"] == 2

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_thread_safety(self):
        """Test cache is thread-safe under concurrent access."""
        cache = LRUCache(max_size=100)
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(100):
                    key = f"key_{worker_id}_{i}"
                    cache.set(key, f"value_{i}")
                    value = cache.get(key)
                    assert value == f"value_{i}" or value is None  # May be evicted
            except Exception as e:
                errors.append(e)

        # Create 10 concurrent threads
        threads = [Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0


class TestCapabilityCache:
    """Tests for CapabilityCache class."""

    def test_capability_cache_initialization(self):
        """Test capability cache initialization."""
        cache = CapabilityCache()

        assert not cache.is_initialized()

        # Initialize with capabilities
        capabilities_map = {
            "geo": ["geocoding", "address_lookup"],
            "finance": ["stocks", "market_data"],
            "map": ["mapping", "directions"],
        }

        cache.initialize(capabilities_map)

        assert cache.is_initialized()

    def test_get_agent_capabilities(self):
        """Test retrieving agent capabilities."""
        cache = CapabilityCache()

        capabilities_map = {
            "geo": ["geocoding", "address_lookup", "geography"],
            "finance": ["stocks", "market_data"],
        }

        cache.initialize(capabilities_map)

        # Get existing agent capabilities
        geo_caps = cache.get_agent_capabilities("geo")
        assert geo_caps == ["geocoding", "address_lookup", "geography"]

        finance_caps = cache.get_agent_capabilities("finance")
        assert finance_caps == ["stocks", "market_data"]

        # Get non-existent agent
        assert cache.get_agent_capabilities("unknown") is None

    def test_find_agents_for_capability(self):
        """Test reverse lookup: capability -> agents."""
        cache = CapabilityCache()

        capabilities_map = {
            "geo": ["geocoding", "geography"],
            "map": ["mapping", "geography"],
            "finance": ["stocks"],
        }

        cache.initialize(capabilities_map)

        # Find agents for a capability
        geography_agents = cache.find_agents_for_capability("geography")
        assert set(geography_agents) == {"geo", "map"}

        geocoding_agents = cache.find_agents_for_capability("geocoding")
        assert geocoding_agents == ["geo"]

        stocks_agents = cache.find_agents_for_capability("stocks")
        assert stocks_agents == ["finance"]

        # Non-existent capability
        assert cache.find_agents_for_capability("unknown") == []


class TestRoutingCache:
    """Tests for RoutingCache class."""

    def test_routing_cache_basic(self):
        """Test basic routing cache operations."""
        cache = RoutingCache(max_size=10, ttl_seconds=60)

        # Set routing
        cache.set_routing("geocoding", "geo")

        # Get routing
        assert cache.get_routing("geocoding") == "geo"

        # Get non-existent routing
        assert cache.get_routing("unknown") is None

    def test_routing_cache_ttl(self):
        """Test routing cache respects TTL."""
        cache = RoutingCache(max_size=10, ttl_seconds=0.1)

        cache.set_routing("geocoding", "geo")

        # Should be present immediately
        assert cache.get_routing("geocoding") == "geo"

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        assert cache.get_routing("geocoding") is None


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics class."""

    def test_metrics_recording(self):
        """Test recording performance metrics."""
        metrics = PerformanceMetrics()

        # Record some durations
        metrics.record("interpretation", 0.5)
        metrics.record("interpretation", 0.6)
        metrics.record("interpretation", 0.7)

        # Get stats
        stats = metrics.get_stats("interpretation")

        assert stats["count"] == 3
        assert stats["min"] == 0.5
        assert stats["max"] == 0.7
        assert stats["avg"] == 0.6

    def test_metrics_percentiles(self):
        """Test percentile calculations."""
        metrics = PerformanceMetrics()

        # Record 100 values
        for i in range(100):
            metrics.record("test_phase", i / 100.0)

        stats = metrics.get_stats("test_phase")

        # Check percentiles
        assert 0.49 <= stats["p50"] <= 0.51
        assert 0.94 <= stats["p95"] <= 0.96
        assert 0.98 <= stats["p99"] <= 1.0

    def test_metrics_all_phases(self):
        """Test getting stats for all phases."""
        metrics = PerformanceMetrics()

        metrics.record("interpretation", 0.5)
        metrics.record("decomposition", 1.0)
        metrics.record("routing", 0.1)

        all_stats = metrics.get_all_stats()

        assert "interpretation" in all_stats
        assert "decomposition" in all_stats
        assert "routing" in all_stats

        assert all_stats["interpretation"]["avg"] == 0.5
        assert all_stats["decomposition"]["avg"] == 1.0
        assert all_stats["routing"]["avg"] == 0.1


class TestGlobalCaches:
    """Tests for global cache instances."""

    def test_get_capability_cache_singleton(self):
        """Test capability cache returns same instance."""
        cache1 = get_capability_cache()
        cache2 = get_capability_cache()

        assert cache1 is cache2

    def test_get_routing_cache_singleton(self):
        """Test routing cache returns same instance."""
        cache1 = get_routing_cache()
        cache2 = get_routing_cache()

        assert cache1 is cache2

    def test_get_performance_metrics_singleton(self):
        """Test performance metrics returns same instance."""
        metrics1 = get_performance_metrics()
        metrics2 = get_performance_metrics()

        assert metrics1 is metrics2
