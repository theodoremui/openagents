"""
Tests for CapabilityRouter

Tests agent routing based on capability maps.
"""

import pytest
from asdrp.orchestration.smartrouter.capability_router import CapabilityRouter
from asdrp.orchestration.smartrouter.interfaces import (
    Subquery,
    RoutingPattern,
)
from asdrp.orchestration.smartrouter.exceptions import RoutingException


class TestCapabilityRouter:
    """Test CapabilityRouter class."""

    def test_route_simple_match(self):
        """Test routing with simple capability match."""
        capability_map = {
            "geo": ["geocoding", "reverse_geocoding"],
            "finance": ["stocks", "market_data"],
        }
        router = CapabilityRouter(capability_map)
        
        subquery = Subquery(
            id="sq1",
            text="Find address",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        agent_id, pattern = router.route(subquery)
        
        assert agent_id == "geo"
        assert pattern == RoutingPattern.DELEGATION

    def test_route_multiple_matches(self):
        """Test routing when multiple agents have capability."""
        capability_map = {
            "geo": ["geocoding", "mapping"],
            "map": ["geocoding", "mapping", "routing"],
        }
        router = CapabilityRouter(capability_map)
        
        subquery = Subquery(
            id="sq1",
            text="Geocode address",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        agent_id, pattern = router.route(subquery)
        
        # Should select most specialized (more capabilities)
        assert agent_id in ["geo", "map"]
        assert pattern == RoutingPattern.DELEGATION

    def test_route_no_match(self):
        """Test routing when no agent has capability."""
        capability_map = {
            "geo": ["geocoding"],
            "finance": ["stocks"],
        }
        router = CapabilityRouter(capability_map)
        
        subquery = Subquery(
            id="sq1",
            text="Unknown capability",
            capability_required="quantum_physics",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        with pytest.raises(RoutingException):
            router.route(subquery)

    def test_route_handoff_pattern(self):
        """Test routing with handoff pattern."""
        capability_map = {
            "geo": ["geocoding"],
        }
        router = CapabilityRouter(capability_map)
        
        subquery = Subquery(
            id="sq1",
            text="Complex iterative query",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.HANDOFF,
            metadata={}
        )
        
        agent_id, pattern = router.route(subquery)
        
        assert agent_id == "geo"
        assert pattern == RoutingPattern.HANDOFF

    def test_route_empty_capability_map(self):
        """Test routing with empty capability map."""
        # Disable cache to avoid interference from previous tests
        router = CapabilityRouter({}, use_cache=False)
        
        subquery = Subquery(
            id="sq1",
            text="Test",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        with pytest.raises(RoutingException):
            router.route(subquery)

    def test_route_reverse_index(self):
        """Test that reverse index is built correctly."""
        capability_map = {
            "geo": ["geocoding", "reverse_geocoding"],
            "finance": ["stocks"],
        }
        router = CapabilityRouter(capability_map)
        
        # Check reverse index
        assert "geocoding" in router._reverse_index
        assert "reverse_geocoding" in router._reverse_index
        assert "stocks" in router._reverse_index
        assert "geo" in router._reverse_index["geocoding"]
        assert "finance" in router._reverse_index["stocks"]

    def test_route_overlapping_capabilities(self):
        """Test routing with overlapping capabilities."""
        capability_map = {
            "one": ["search", "general_knowledge"],
            "perplexity": ["search", "research"],
        }
        router = CapabilityRouter(capability_map)
        
        subquery = Subquery(
            id="sq1",
            text="Search query",
            capability_required="search",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        agent_id, pattern = router.route(subquery)
        
        # Should select one of them
        assert agent_id in ["one", "perplexity"]
        assert pattern == RoutingPattern.DELEGATION

