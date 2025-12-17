"""
SmartRouter Exception Hierarchy

Domain-specific exceptions for the SmartRouter system, following best practices
for error handling with meaningful messages and exception chaining.

Exception Hierarchy:
-------------------
SmartRouterException (base)
├── QueryDecompositionException
├── RoutingException
├── DispatchException
├── SynthesisException
└── EvaluationException

Design Principles:
-----------------
- Single Responsibility: Each exception type represents one failure category
- Meaningful Messages: Include context about what went wrong
- Exception Chaining: Preserve original exceptions with 'from e'
- Type Safety: Specific exception types for specific failure modes
"""

from typing import Optional, Any


class SmartRouterException(Exception):
    """
    Base exception for SmartRouter system.

    All SmartRouter-related exceptions inherit from this base class,
    allowing callers to catch all SmartRouter errors with a single except clause.

    Attributes:
        message: Human-readable error description
        context: Optional dictionary with additional error context
        original_exception: Optional chained exception that caused this error

    Examples:
    ---------
    >>> try:
    ...     # SmartRouter operation
    ...     pass
    ... except SmartRouterException as e:
    ...     logger.error(f"SmartRouter error: {e.message}", extra=e.context)
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize SmartRouter exception.

        Args:
            message: Human-readable error description
            context: Optional dictionary with error context (query, agent_id, etc.)
            original_exception: Optional exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_exception = original_exception

    def __str__(self) -> str:
        """Return formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


class QueryDecompositionException(SmartRouterException):
    """
    Exception raised when query decomposition fails.

    This occurs when the QueryDecomposer cannot break down a query into
    valid subqueries, detects cyclic dependencies, or exceeds recursion limits.

    Examples:
    ---------
    >>> raise QueryDecompositionException(
    ...     "Cyclic dependency detected in subqueries",
    ...     context={"query": "original query", "cycle": ["sq1", "sq2", "sq1"]}
    ... )
    """
    pass


class RoutingException(SmartRouterException):
    """
    Exception raised when agent routing fails.

    This occurs when the CapabilityRouter cannot find suitable agents for
    subqueries, encounters capability map errors, or fails to determine
    routing patterns (delegation vs handoff).

    Examples:
    ---------
    >>> raise RoutingException(
    ...     "No agent found with capability 'quantum_physics'",
    ...     context={"subquery": "Explain quantum entanglement", "capability": "quantum_physics"}
    ... )
    """
    pass


class DispatchException(SmartRouterException):
    """
    Exception raised when subquery dispatch fails.

    This occurs when the AsyncSubqueryDispatcher encounters agent execution
    errors, timeouts, or communication failures.

    Examples:
    ---------
    >>> raise DispatchException(
    ...     "Agent 'geo' timed out after 30s",
    ...     context={"agent_id": "geo", "timeout": 30, "subquery": "Geocode address"}
    ... )
    """
    pass


class SynthesisException(SmartRouterException):
    """
    Exception raised when response synthesis fails.

    This occurs when the ResultSynthesizer cannot merge agent responses,
    resolve conflicts, or construct a coherent final answer.

    Examples:
    ---------
    >>> raise SynthesisException(
    ...     "Conflicting responses cannot be reconciled",
    ...     context={"responses": 3, "conflicts": ["date", "location"]}
    ... )
    """
    pass


class EvaluationException(SmartRouterException):
    """
    Exception raised when answer evaluation fails.

    This occurs when the LLMJudge cannot assess answer quality, encounters
    LLM API errors, or fails to determine completeness/correctness.

    Examples:
    ---------
    >>> raise EvaluationException(
    ...     "LLM Judge API call failed",
    ...     context={"criteria": ["completeness", "accuracy"], "error": "rate_limit"}
    ... )
    """
    pass
