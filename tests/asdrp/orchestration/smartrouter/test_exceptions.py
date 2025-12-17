"""
Tests for SmartRouter Exception Hierarchy

Tests all exception types to ensure proper inheritance, message formatting,
and context handling.
"""

import pytest
from asdrp.orchestration.smartrouter.exceptions import (
    SmartRouterException,
    QueryDecompositionException,
    RoutingException,
    DispatchException,
    SynthesisException,
    EvaluationException,
)


class TestSmartRouterException:
    """Test base SmartRouterException."""

    def test_basic_exception(self):
        """Test creating exception with just message."""
        exc = SmartRouterException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.context == {}
        assert exc.original_exception is None

    def test_exception_with_context(self):
        """Test exception with context dictionary."""
        context = {"query": "test query", "agent_id": "geo"}
        exc = SmartRouterException("Test error", context=context)
        assert "Test error" in str(exc)
        assert "query=test query" in str(exc)
        assert "agent_id=geo" in str(exc)
        assert exc.context == context

    def test_exception_with_original(self):
        """Test exception chaining."""
        original = ValueError("Original error")
        exc = SmartRouterException("Wrapped error", original_exception=original)
        assert exc.original_exception == original
        assert str(exc) == "Wrapped error"

    def test_exception_with_all_fields(self):
        """Test exception with all fields."""
        original = KeyError("key")
        context = {"key": "value"}
        exc = SmartRouterException(
            "Full error",
            context=context,
            original_exception=original
        )
        assert exc.message == "Full error"
        assert exc.context == context
        assert exc.original_exception == original


class TestQueryDecompositionException:
    """Test QueryDecompositionException."""

    def test_inheritance(self):
        """Test that it inherits from SmartRouterException."""
        exc = QueryDecompositionException("Decomposition failed")
        assert isinstance(exc, SmartRouterException)
        assert str(exc) == "Decomposition failed"

    def test_with_context(self):
        """Test with context."""
        context = {"query": "complex query", "cycle": ["sq1", "sq2"]}
        exc = QueryDecompositionException("Cyclic dependency", context=context)
        assert isinstance(exc, SmartRouterException)
        assert exc.context == context


class TestRoutingException:
    """Test RoutingException."""

    def test_inheritance(self):
        """Test that it inherits from SmartRouterException."""
        exc = RoutingException("Routing failed")
        assert isinstance(exc, SmartRouterException)

    def test_with_context(self):
        """Test with context."""
        context = {"subquery": "test", "capability": "geocoding"}
        exc = RoutingException("No agent found", context=context)
        assert exc.context == context


class TestDispatchException:
    """Test DispatchException."""

    def test_inheritance(self):
        """Test that it inherits from SmartRouterException."""
        exc = DispatchException("Dispatch failed")
        assert isinstance(exc, SmartRouterException)

    def test_with_context(self):
        """Test with context."""
        context = {"agent_id": "geo", "timeout": 30}
        exc = DispatchException("Timeout", context=context)
        assert exc.context == context


class TestSynthesisException:
    """Test SynthesisException."""

    def test_inheritance(self):
        """Test that it inherits from SmartRouterException."""
        exc = SynthesisException("Synthesis failed")
        assert isinstance(exc, SmartRouterException)

    def test_with_context(self):
        """Test with context."""
        context = {"responses": 3, "conflicts": ["date"]}
        exc = SynthesisException("Conflicts", context=context)
        assert exc.context == context


class TestEvaluationException:
    """Test EvaluationException."""

    def test_inheritance(self):
        """Test that it inherits from SmartRouterException."""
        exc = EvaluationException("Evaluation failed")
        assert isinstance(exc, SmartRouterException)

    def test_with_context(self):
        """Test with context."""
        context = {"criteria": ["completeness"], "error": "rate_limit"}
        exc = EvaluationException("API failed", context=context)
        assert exc.context == context


class TestExceptionHierarchy:
    """Test exception hierarchy and catching."""

    def test_catch_all_smartrouter_exceptions(self):
        """Test that base exception catches all subtypes."""
        exceptions = [
            QueryDecompositionException("test"),
            RoutingException("test"),
            DispatchException("test"),
            SynthesisException("test"),
            EvaluationException("test"),
        ]

        for exc in exceptions:
            with pytest.raises(SmartRouterException):
                raise exc

    def test_specific_exception_types(self):
        """Test that specific exception types are preserved."""
        with pytest.raises(QueryDecompositionException):
            raise QueryDecompositionException("test")

        with pytest.raises(RoutingException):
            raise RoutingException("test")

        with pytest.raises(DispatchException):
            raise DispatchException("test")

        with pytest.raises(SynthesisException):
            raise SynthesisException("test")

        with pytest.raises(EvaluationException):
            raise EvaluationException("test")








