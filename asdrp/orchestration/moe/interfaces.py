"""
MoE Orchestrator Interfaces.

Protocol definitions for MoE components following the Protocol pattern.
"""

from typing import Protocol, runtime_checkable, Optional, List, Tuple, Dict, Any


@runtime_checkable
class IExpertSelector(Protocol):
    """
    Protocol for expert selection (Tier 1).

    Implementations:
    - CapabilityBasedSelector: Fast keyword matching
    - EmbeddingSelector: Semantic similarity (future)
    - LearnedGatingSelector: ML-based selection (future)
    """

    async def select(
        self,
        query: str,
        k: int = 3,
        threshold: float = 0.3
    ) -> List[str]:
        """
        Select top-k expert agent IDs for query.

        Args:
            query: User query
            k: Max experts to select
            threshold: Min confidence threshold

        Returns:
            List of agent IDs (e.g., ["yelp", "geo", "map"])
        """
        ...


@runtime_checkable
class IExpertExecutor(Protocol):
    """
    Protocol for parallel execution (Tier 2).

    Implementations:
    - ParallelExecutor: asyncio.gather-based concurrent execution
    - StreamingExecutor: Stream results as they complete (future)
    - DAGExecutor: Dependency-aware execution (future)
    """

    async def execute_parallel(
        self,
        agents_with_sessions: List[Tuple[str, Any, Any]],
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> List[Any]:  # List[ExpertResult]
        """
        Execute agents in parallel.

        Args:
            agents_with_sessions: List of (expert_id, agent, session)
            query: Query to process
            context: Optional context
            timeout: Overall timeout

        Returns:
            List of ExpertResult
        """
        ...


@runtime_checkable
class IResultMixer(Protocol):
    """
    Protocol for result aggregation (Tier 3).

    Implementations:
    - WeightedMixer: LLM-based synthesis with confidence weighting
    - VotingMixer: Consensus voting (future)
    - EnsembleMixer: Multiple mixing strategies (future)
    """

    async def mix(
        self,
        expert_results: List[Any],
        expert_ids: List[str],
        query: str
    ) -> Any:  # MixedResult
        """
        Mix expert results into coherent response.

        Args:
            expert_results: Results from experts
            expert_ids: Expert IDs
            query: Original query

        Returns:
            MixedResult with synthesized content
        """
        ...


@runtime_checkable
class ICache(Protocol):
    """
    Protocol for semantic caching.

    Implementations:
    - SemanticCache: Embedding-based similarity cache
    - ExactCache: Exact string matching (future)
    - HybridCache: Exact + semantic (future)
    """

    async def get(self, query: str) -> Optional[Any]:
        """Get cached result for query."""
        ...

    async def store(self, query: str, result: Any) -> None:
        """Store query-result pair."""
        ...
