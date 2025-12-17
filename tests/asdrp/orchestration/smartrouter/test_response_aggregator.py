"""
Tests for ResponseAggregator

Tests response aggregation, filtering, and statistics.
"""

import pytest
from asdrp.orchestration.smartrouter.response_aggregator import ResponseAggregator
from asdrp.orchestration.smartrouter.interfaces import (
    AgentResponse,
    Subquery,
    RoutingPattern,
)
from asdrp.orchestration.smartrouter.exceptions import SmartRouterException


class TestResponseAggregator:
    """Test ResponseAggregator class."""

    def test_aggregate_responses(self):
        """Test basic response aggregation."""
        aggregator = ResponseAggregator()
        
        subqueries = [
            Subquery(
                id="sq1",
                text="Query 1",
                capability_required="geocoding",
                dependencies=[],
                routing_pattern=RoutingPattern.DELEGATION,
                metadata={}
            ),
            Subquery(
                id="sq2",
                text="Query 2",
                capability_required="finance",
                dependencies=[],
                routing_pattern=RoutingPattern.DELEGATION,
                metadata={}
            ),
        ]
        
        responses = [
            AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Response 1",
                success=True,
                metadata={}
            ),
            AgentResponse(
                subquery_id="sq2",
                agent_id="finance",
                content="Response 2",
                success=True,
                metadata={}
            ),
        ]
        
        aggregated = aggregator.aggregate(responses, subqueries)
        
        assert len(aggregated) == 2
        assert "sq1" in aggregated
        assert "sq2" in aggregated
        assert aggregated["sq1"].content == "Response 1"
        assert aggregated["sq2"].content == "Response 2"

    def test_aggregate_with_missing_response(self):
        """Test aggregation when response is missing."""
        aggregator = ResponseAggregator()
        
        subqueries = [
            Subquery(
                id="sq1",
                text="Query 1",
                capability_required="geocoding",
                dependencies=[],
                routing_pattern=RoutingPattern.DELEGATION,
                metadata={}
            ),
            Subquery(
                id="sq2",
                text="Query 2",
                capability_required="finance",
                dependencies=[],
                routing_pattern=RoutingPattern.DELEGATION,
                metadata={}
            ),
        ]
        
        responses = [
            AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Response 1",
                success=True,
                metadata={}
            ),
        ]
        
        aggregated = aggregator.aggregate(responses, subqueries)
        
        assert len(aggregated) == 1
        assert "sq1" in aggregated
        assert "sq2" not in aggregated

    def test_aggregate_with_duplicate_responses(self):
        """Test aggregation handles duplicate responses."""
        aggregator = ResponseAggregator()
        
        subqueries = [
            Subquery(
                id="sq1",
                text="Query 1",
                capability_required="geocoding",
                dependencies=[],
                routing_pattern=RoutingPattern.DELEGATION,
                metadata={}
            ),
        ]
        
        responses = [
            AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Response 1",
                success=True,
                metadata={}
            ),
            AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Response 2",
                success=True,
                metadata={}
            ),
        ]
        
        aggregated = aggregator.aggregate(responses, subqueries)
        
        assert len(aggregated) == 1
        assert aggregated["sq1"].content == "Response 1"  # First one kept

    def test_extract_successful(self):
        """Test extracting successful responses."""
        aggregator = ResponseAggregator()
        
        aggregated = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Success",
                success=True,
                metadata={}
            ),
            "sq2": AgentResponse(
                subquery_id="sq2",
                agent_id="finance",
                content="Failed",
                success=False,
                metadata={}
            ),
        }
        
        successful = aggregator.extract_successful(aggregated)
        
        assert len(successful) == 1
        assert "sq1" in successful
        assert "sq2" not in successful
        assert successful["sq1"].success is True

    def test_get_failed_responses(self):
        """Test getting failed responses."""
        aggregator = ResponseAggregator()
        
        aggregated = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Success",
                success=True,
                metadata={}
            ),
            "sq2": AgentResponse(
                subquery_id="sq2",
                agent_id="finance",
                content="Failed",
                success=False,
                metadata={}
            ),
        }
        
        failed = aggregator.get_failed_responses(aggregated)
        
        assert len(failed) == 1
        assert "sq2" in failed
        assert "sq1" not in failed
        assert failed["sq2"].success is False

    def test_get_response_statistics(self):
        """Test getting response statistics."""
        aggregator = ResponseAggregator()
        
        aggregated = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Success 1",
                success=True,
                metadata={}
            ),
            "sq2": AgentResponse(
                subquery_id="sq2",
                agent_id="finance",
                content="Success 2",
                success=True,
                metadata={}
            ),
            "sq3": AgentResponse(
                subquery_id="sq3",
                agent_id="one",
                content="Failed",
                success=False,
                metadata={}
            ),
        }
        
        stats = aggregator.get_response_statistics(aggregated)
        
        assert stats["total"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1

    def test_aggregate_empty_responses(self):
        """Test aggregation with empty responses."""
        aggregator = ResponseAggregator()
        
        subqueries = [
            Subquery(
                id="sq1",
                text="Query 1",
                capability_required="geocoding",
                dependencies=[],
                routing_pattern=RoutingPattern.DELEGATION,
                metadata={}
            ),
        ]
        
        aggregated = aggregator.aggregate([], subqueries)
        
        assert len(aggregated) == 0

    def test_aggregate_error_handling(self):
        """Test aggregation error handling."""
        aggregator = ResponseAggregator()
        
        # Invalid responses that might cause errors
        # The actual code tries to call len() on None, which raises TypeError
        # which gets wrapped in SmartRouterException
        with pytest.raises(SmartRouterException) as exc_info:
            aggregator.aggregate(None, [])
        
        # Verify it's wrapped properly
        assert "aggregation failed" in str(exc_info.value).lower()

