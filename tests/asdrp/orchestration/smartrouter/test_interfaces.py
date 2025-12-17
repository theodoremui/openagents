"""
Tests for SmartRouter Interfaces and Data Classes

Tests dataclasses and enums used throughout the SmartRouter system.
"""

import pytest
from asdrp.orchestration.smartrouter.interfaces import (
    QueryComplexity,
    RoutingPattern,
    QueryIntent,
    Subquery,
    SmartRouterTrace,
    SmartRouterResult,
    AgentResponse,
    SynthesizedResult,
)


class TestQueryComplexity:
    """Test QueryComplexity enum."""

    def test_enum_values(self):
        """Test enum has correct values."""
        assert QueryComplexity.SIMPLE.value == "simple"
        assert QueryComplexity.MODERATE.value == "moderate"
        assert QueryComplexity.COMPLEX.value == "complex"

    def test_enum_membership(self):
        """Test enum membership."""
        assert isinstance(QueryComplexity.SIMPLE, QueryComplexity)
        assert isinstance(QueryComplexity.MODERATE, QueryComplexity)
        assert isinstance(QueryComplexity.COMPLEX, QueryComplexity)


class TestRoutingPattern:
    """Test RoutingPattern enum."""

    def test_enum_values(self):
        """Test enum has correct values."""
        assert RoutingPattern.DELEGATION.value == "delegation"
        assert RoutingPattern.HANDOFF.value == "handoff"


class TestQueryIntent:
    """Test QueryIntent dataclass."""

    def test_create_query_intent(self):
        """Test creating QueryIntent."""
        intent = QueryIntent(
            original_query="test query",
            complexity=QueryComplexity.SIMPLE,
            domains=["geography"],
            requires_synthesis=False,
            metadata={"key": "value"}
        )
        assert intent.original_query == "test query"
        assert intent.complexity == QueryComplexity.SIMPLE
        assert intent.domains == ["geography"]
        assert intent.requires_synthesis is False
        assert intent.metadata == {"key": "value"}

    def test_query_intent_defaults(self):
        """Test QueryIntent with minimal fields."""
        intent = QueryIntent(
            original_query="test",
            complexity=QueryComplexity.SIMPLE,
            domains=[],
            requires_synthesis=False,
            metadata={}
        )
        assert intent.original_query == "test"
        assert intent.domains == []
        assert intent.metadata == {}


class TestSubquery:
    """Test Subquery dataclass."""

    def test_create_subquery(self):
        """Test creating Subquery."""
        subquery = Subquery(
            id="sq1",
            text="Find address",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        assert subquery.id == "sq1"
        assert subquery.text == "Find address"
        assert subquery.capability_required == "geocoding"
        assert subquery.dependencies == []
        assert subquery.routing_pattern == RoutingPattern.DELEGATION

    def test_subquery_with_dependencies(self):
        """Test Subquery with dependencies."""
        subquery = Subquery(
            id="sq2",
            text="Process result",
            capability_required="finance",
            dependencies=["sq1"],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        assert subquery.dependencies == ["sq1"]


class TestSmartRouterTrace:
    """Test SmartRouterTrace dataclass."""

    def test_create_trace(self):
        """Test creating SmartRouterTrace."""
        trace = SmartRouterTrace(
            phase="interpretation",
            duration=1.5,
            data={"complexity": "SIMPLE"}
        )
        assert trace.phase == "interpretation"
        assert trace.duration == 1.5
        assert trace.data == {"complexity": "SIMPLE"}


class TestAgentResponse:
    """Test AgentResponse dataclass."""

    def test_create_agent_response(self):
        """Test creating AgentResponse."""
        response = AgentResponse(
            subquery_id="sq1",
            agent_id="geo",
            content="The address is...",
            success=True,
            metadata={}
        )
        assert response.subquery_id == "sq1"
        assert response.agent_id == "geo"
        assert response.content == "The address is..."
        assert response.success is True

    def test_failed_response(self):
        """Test creating failed response."""
        response = AgentResponse(
            subquery_id="sq1",
            agent_id="geo",
            content="Error occurred",
            success=False,
            metadata={"error": "timeout"}
        )
        assert response.success is False
        assert "error" in response.metadata


class TestSynthesizedResult:
    """Test SynthesizedResult dataclass."""

    def test_create_synthesized_result(self):
        """Test creating SynthesizedResult."""
        result = SynthesizedResult(
            answer="Combined answer",
            sources=["geo", "finance"],
            confidence=0.9,
            conflicts_resolved=[],
            metadata={"notes": "No conflicts"}
        )
        assert result.answer == "Combined answer"
        assert result.sources == ["geo", "finance"]
        assert result.confidence == 0.9
        assert result.conflicts_resolved == []
        assert result.metadata == {"notes": "No conflicts"}


class TestSmartRouterResult:
    """Test SmartRouterResult dataclass."""

    def test_create_result(self):
        """Test creating SmartRouterResult."""
        result = SmartRouterResult(
            answer="Final answer",
            traces=[],
            total_time=1.5,
            final_decision="synthesized",
            agents_used=["geo", "finance"]
        )
        assert result.answer == "Final answer"
        assert result.traces == []
        assert result.total_time == 1.5
        assert result.final_decision == "synthesized"
        assert result.agents_used == ["geo", "finance"]

    def test_result_with_traces(self):
        """Test result with traces."""
        trace = SmartRouterTrace(
            phase="interpretation",
            duration=1.0,
            data={}
        )
        result = SmartRouterResult(
            answer="Answer",
            traces=[trace],
            total_time=1.0,
            final_decision="direct",
            agents_used=["geo"]
        )
        assert len(result.traces) == 1
        assert result.traces[0] == trace

