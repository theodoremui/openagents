"""
SmartRouter Component Interfaces

Abstract base classes defining the contracts for SmartRouter components.
Following SOLID principles (Interface Segregation, Dependency Inversion).

Design Principles:
-----------------
- Interface Segregation: Small, focused interfaces for each responsibility
- Dependency Inversion: Depend on abstractions, not concretions
- Open/Closed: Open for extension (new implementations), closed for modification
- Liskov Substitution: Any implementation can be swapped without breaking system

Components:
-----------
- IQueryInterpreter: Query parsing and classification
- IQueryDecomposer: Query decomposition into subqueries
- ICapabilityRouter: Agent selection based on capabilities
- ISubqueryDispatcher: Asynchronous subquery dispatch
- IResponseAggregator: Response collection and organization
- IResultSynthesizer: Response merging and coherence
- IAnswerEvaluator: Quality evaluation and fallback decisions
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class QueryComplexity(Enum):
    """Enum for query complexity classification."""
    SIMPLE = "simple"           # Single agent, direct answer
    MODERATE = "moderate"       # Multiple agents, straightforward routing
    COMPLEX = "complex"         # Multiple agents, dependencies, synthesis required


class RoutingPattern(Enum):
    """Enum for routing patterns."""
    DELEGATION = "delegation"   # Router assigns task, retains control
    HANDOFF = "handoff"         # Router transfers context to agent


@dataclass
class QueryIntent:
    """
    Parsed query intent and classification.

    Attributes:
        original_query: The user's original query text
        complexity: Query complexity classification
        domains: List of knowledge domains involved (e.g., ["geography", "finance"])
        requires_synthesis: Whether multiple responses need to be synthesized
        metadata: Additional context and metadata
    """
    original_query: str
    complexity: QueryComplexity
    domains: List[str]
    requires_synthesis: bool
    metadata: Dict[str, Any]


@dataclass
class Subquery:
    """
    A decomposed subquery to be routed to an agent.

    Attributes:
        id: Unique identifier for this subquery
        text: The subquery text
        capability_required: Capability keyword needed (e.g., "geocoding", "finance")
        dependencies: IDs of subqueries that must complete first
        routing_pattern: Delegation or handoff
        metadata: Additional context
    """
    id: str
    text: str
    capability_required: str
    dependencies: List[str]
    routing_pattern: RoutingPattern
    metadata: Dict[str, Any]


@dataclass
class SmartRouterTrace:
    """
    Execution trace for a single phase of SmartRouter processing.

    Attributes:
        phase: Name of the phase (interpretation, routing, execution, etc.)
        duration: Time taken for this phase in seconds
        data: Phase-specific data (intent, subqueries, responses, etc.)
    """
    phase: str
    duration: float
    data: Dict[str, Any]


@dataclass
class SmartRouterResult:
    """
    Complete result from SmartRouter execution including answer and trace data.

    Attributes:
        answer: Final answer string
        traces: List of execution traces for each phase
        total_time: Total execution time in seconds
        final_decision: Whether answer was synthesized, direct, or fallback
        agents_used: List of agent IDs that were used
    """
    answer: str
    traces: List[SmartRouterTrace]
    total_time: float
    final_decision: str
    agents_used: List[str]


@dataclass
class AgentResponse:
    """
    Response from an agent for a subquery.

    Attributes:
        subquery_id: ID of the subquery this responds to
        agent_id: ID of the agent that generated this response
        content: Response text content
        success: Whether the agent successfully handled the query
        error: Optional error message if success=False
        metadata: Additional response metadata (usage, timing, etc.)
    """
    subquery_id: str
    agent_id: str
    content: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class SynthesizedResult:
    """
    Final synthesized answer from multiple agent responses.

    Attributes:
        answer: The final synthesized answer text
        sources: List of agent IDs that contributed
        confidence: Confidence score (0.0-1.0)
        conflicts_resolved: List of conflicts that were resolved
        metadata: Additional synthesis metadata
    """
    answer: str
    sources: List[str]
    confidence: float
    conflicts_resolved: List[str]
    metadata: Dict[str, Any]


@dataclass
class EvaluationResult:
    """
    LLM Judge evaluation result.

    Attributes:
        is_high_quality: Whether answer meets quality thresholds
        completeness_score: Completeness score (0.0-1.0)
        accuracy_score: Accuracy/correctness score (0.0-1.0)
        clarity_score: Clarity score (0.0-1.0)
        issues: List of identified quality issues
        should_fallback: Whether to use fallback message
        metadata: Additional evaluation metadata
    """
    is_high_quality: bool
    completeness_score: float
    accuracy_score: float
    clarity_score: float
    issues: List[str]
    should_fallback: bool
    metadata: Dict[str, Any]


class IQueryInterpreter(ABC):
    """
    Interface for query interpretation and classification.

    Responsibility: Parse user queries and extract intent, complexity, and domains.
    """

    @abstractmethod
    async def interpret(self, query: str) -> QueryIntent:
        """
        Interpret and classify a user query.

        Args:
            query: The user's query text

        Returns:
            QueryIntent with classification and metadata

        Raises:
            SmartRouterException: If interpretation fails
        """
        pass


class IQueryDecomposer(ABC):
    """
    Interface for query decomposition into subqueries.

    Responsibility: Break complex queries into independent, routable subqueries.
    """

    @abstractmethod
    async def decompose(self, intent: QueryIntent) -> List[Subquery]:
        """
        Decompose a query into subqueries.

        Args:
            intent: Interpreted query intent

        Returns:
            List of Subquery objects (may be empty for simple queries)

        Raises:
            QueryDecompositionException: If decomposition fails or cycles detected
        """
        pass

    @abstractmethod
    def validate_dependencies(self, subqueries: List[Subquery]) -> bool:
        """
        Validate that subquery dependencies are acyclic.

        Args:
            subqueries: List of subqueries to validate

        Returns:
            True if dependencies are valid (acyclic)

        Raises:
            QueryDecompositionException: If cyclic dependencies detected
        """
        pass


class ICapabilityRouter(ABC):
    """
    Interface for agent selection based on capabilities.

    Responsibility: Match subqueries to agents using capability maps.
    """

    @abstractmethod
    def route(self, subquery: Subquery) -> Tuple[str, RoutingPattern]:
        """
        Route a subquery to an appropriate agent.

        Args:
            subquery: The subquery to route

        Returns:
            Tuple of (agent_id, routing_pattern)

        Raises:
            RoutingException: If no suitable agent found
        """
        pass

    @abstractmethod
    def get_capabilities(self, agent_id: str) -> List[str]:
        """
        Get capabilities for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of capability keywords

        Raises:
            RoutingException: If agent not found
        """
        pass


class ISubqueryDispatcher(ABC):
    """
    Interface for asynchronous subquery dispatch.

    Responsibility: Execute subqueries on agents asynchronously with timeout handling.
    """

    @abstractmethod
    async def dispatch(
        self,
        subquery: Subquery,
        agent_id: str,
        timeout: Optional[float] = None
    ) -> AgentResponse:
        """
        Dispatch a subquery to an agent asynchronously.

        Args:
            subquery: The subquery to execute
            agent_id: Target agent identifier
            timeout: Optional timeout in seconds

        Returns:
            AgentResponse with result or error

        Raises:
            DispatchException: If dispatch fails critically
        """
        pass

    @abstractmethod
    async def dispatch_all(
        self,
        subqueries: List[Tuple[Subquery, str]],
        timeout: Optional[float] = None
    ) -> List[AgentResponse]:
        """
        Dispatch multiple subqueries concurrently.

        Args:
            subqueries: List of (subquery, agent_id) tuples
            timeout: Optional timeout in seconds

        Returns:
            List of AgentResponse objects (includes errors)

        Raises:
            DispatchException: If dispatch system fails
        """
        pass


class IResponseAggregator(ABC):
    """
    Interface for response collection and organization.

    Responsibility: Collect agent responses and preserve ordering/context.
    """

    @abstractmethod
    def aggregate(
        self,
        responses: List[AgentResponse],
        subqueries: List[Subquery]
    ) -> Dict[str, AgentResponse]:
        """
        Aggregate responses by subquery ID, maintaining order.

        Args:
            responses: List of agent responses
            subqueries: Original subqueries for context

        Returns:
            Dictionary mapping subquery_id to AgentResponse

        Raises:
            SmartRouterException: If aggregation fails
        """
        pass

    @abstractmethod
    def extract_successful(
        self,
        aggregated: Dict[str, AgentResponse]
    ) -> Dict[str, AgentResponse]:
        """
        Extract only successful responses.

        Args:
            aggregated: Aggregated responses

        Returns:
            Dictionary with only successful responses
        """
        pass


class IResultSynthesizer(ABC):
    """
    Interface for response synthesis.

    Responsibility: Merge agent responses into coherent final answer.
    """

    @abstractmethod
    async def synthesize(
        self,
        responses: Dict[str, AgentResponse],
        original_query: str
    ) -> SynthesizedResult:
        """
        Synthesize multiple responses into final answer.

        Args:
            responses: Dictionary of subquery_id -> AgentResponse
            original_query: The original user query for context

        Returns:
            SynthesizedResult with merged answer

        Raises:
            SynthesisException: If synthesis fails
        """
        pass


class IAnswerEvaluator(ABC):
    """
    Interface for answer quality evaluation (LLM Judge).

    Responsibility: Evaluate final answer quality and decide fallback.
    """

    @abstractmethod
    async def evaluate(
        self,
        answer: str,
        original_query: str,
        criteria: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        Evaluate answer quality using LLM judge.

        Args:
            answer: The synthesized answer to evaluate
            original_query: The original user query
            criteria: Optional list of evaluation criteria
                     (defaults: completeness, accuracy, clarity)

        Returns:
            EvaluationResult with scores and fallback decision

        Raises:
            EvaluationException: If evaluation fails
        """
        pass
