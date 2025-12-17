"""
Semantic Expert Selector - Using Embeddings for Agent Routing.

This selector uses embeddings to compute semantic similarity between
user queries and expert capabilities, providing more robust and generic routing
than keyword-based approaches.

Architecture:
- Uses pluggable IEmbeddingProvider for flexibility
- Defaults to cached OpenAI embeddings for <50ms selection
- Pre-computes expert embeddings once at initialization
- O(k) similarity computation where k = number of experts (~6)

Performance:
- First query: ~2000ms (OpenAI API call)
- Subsequent queries: <50ms (cache hit + numpy operations)
- Expert embedding initialization: ~1000ms (batched API call)
"""

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import List, Dict, Optional
import os
import time
import numpy as np
from loguru import logger

from asdrp.orchestration.moe.interfaces import IExpertSelector
from asdrp.orchestration.moe.config_loader import MoEConfig
from asdrp.orchestration.moe.exceptions import ExpertSelectionException
from asdrp.orchestration.moe.embedding_providers import (
    IEmbeddingProvider,
    OpenAIEmbeddingProvider,
    CachedEmbeddingProvider
)


class SemanticSelector(IExpertSelector):
    """
    Select experts using semantic similarity (embeddings).

    Strategy:
    1. Generate embedding for user query (cached after first call)
    2. Compare with pre-computed expert capability embeddings
    3. Return top-k experts by cosine similarity

    Advantages over keyword matching:
    - Handles synonyms naturally (e.g., "directions" = "navigation" = "route")
    - Works with place names without needing to detect them explicitly
    - Generalizes to unseen queries
    - More robust to phrasing variations

    Performance Optimization:
    - Uses CachedEmbeddingProvider for <50ms query embedding generation
    - Pre-computes expert embeddings once during initialization
    - Cosine similarity computation is O(k) where k = number of experts

    Example:
        "San Carlos" → high similarity with location expert
        "pizza near me" → high similarity with business expert
        "TSLA stock" → high similarity with finance expert
    """

    def __init__(
        self,
        config: MoEConfig,
        embedding_provider: Optional[IEmbeddingProvider] = None
    ):
        """
        Initialize selector with configuration.

        Args:
            config: MoE configuration
            embedding_provider: Optional custom embedding provider.
                If not provided, creates cached OpenAI provider automatically.

        Raises:
            ValueError: If OpenAI API key not set and no provider given
        """
        self._config = config
        self._expert_embeddings: Optional[Dict[str, np.ndarray]] = None
        self._expert_descriptions: Dict[str, str] = {}

        # Initialize embedding provider with dependency injection
        if embedding_provider is not None:
            # Use injected provider (enables testing and custom implementations)
            self._provider = embedding_provider
            logger.info(f"[SemanticSelector] Using injected embedding provider: {type(embedding_provider).__name__}")
        else:
            # Default: Create cached OpenAI provider
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable not set. "
                    "Semantic selector requires OpenAI API access."
                )

            base_provider = OpenAIEmbeddingProvider(api_key=api_key)
            self._provider = CachedEmbeddingProvider(
                provider=base_provider,
                max_size=10000,  # Cache up to 10K unique queries
                enable_logging=True
            )
            logger.info("[SemanticSelector] Using cached OpenAI embedding provider")

    async def _initialize_embeddings(self):
        """
        Pre-compute embeddings for all expert capabilities.

        This is done once at initialization using batched embedding generation
        for optimal performance (~1s for all experts vs ~2s sequential).

        Performance:
        - Uses batch API call to generate all expert embeddings in parallel
        - Results cached by provider for future instantiations
        - Total time: ~1000ms (vs ~2000ms per expert sequentially)
        """
        if self._expert_embeddings is not None:
            return  # Already initialized

        start_time = time.time()
        logger.info("[SemanticSelector] Initializing expert embeddings (batched)...")

        self._expert_embeddings = {}
        self._expert_to_agents = {}

        # Build descriptions for all experts
        expert_names = []
        descriptions = []

        for expert_name, expert_config in self._config.experts.items():
            # Create rich description from capabilities
            capabilities_text = ", ".join(expert_config.capabilities)
            description = f"Expert for: {capabilities_text}"

            expert_names.append(expert_name)
            descriptions.append(description)
            self._expert_descriptions[expert_name] = description
            self._expert_to_agents[expert_name] = expert_config.agents

        # Batch generate embeddings for all experts
        embeddings = await self._provider.generate_batch_embeddings(descriptions)

        # Map embeddings to expert names
        for expert_name, embedding in zip(expert_names, embeddings):
            self._expert_embeddings[expert_name] = embedding

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[SemanticSelector] Initialized embeddings for {len(self._expert_embeddings)} experts "
            f"in {elapsed_ms:.0f}ms"
        )

    async def select(
        self,
        query: str,
        k: int = 3,
        threshold: float = 0.3
    ) -> List[str]:
        """
        Select experts using semantic similarity with dynamic selection.

        Selection strategy:
        1. Find all experts above absolute threshold
        2. Apply relevance gap analysis (avoid selecting weak matches)
        3. Select top experts until gap > 0.15 or max_k reached

        This ensures:
        - Single-agent queries get 1 agent (chitchat, simple facts)
        - Multi-domain queries get multiple agents (complex research)
        - Weak matches are excluded automatically

        Args:
            query: User query
            k: Max experts to select (upper bound, not fixed)
            threshold: Min similarity score (0-1, cosine similarity)

        Returns:
            List of agent IDs (dynamically sized, 1-k agents)

        Raises:
            ExpertSelectionException: If selection fails
        """
        try:
            # Initialize embeddings if needed
            await self._initialize_embeddings()

            # Track selection latency for performance monitoring
            selection_start = time.time()

            # Generate query embedding (cached after first call)
            query_embedding = await self._provider.generate_embedding(query)

            embedding_time_ms = (time.time() - selection_start) * 1000
            logger.debug(f"[SemanticSelector] Query embedding generated in {embedding_time_ms:.1f}ms")

            # Compute similarity with each expert
            similarities: Dict[str, float] = {}

            for expert_name, expert_embedding in self._expert_embeddings.items():
                # Cosine similarity
                similarity = self._cosine_similarity(query_embedding, expert_embedding)
                similarities[expert_name] = similarity

            logger.debug(f"[SemanticSelector] Expert similarities: {similarities}")

            # Filter by absolute threshold and sort
            selected_experts = [
                (expert_name, sim)
                for expert_name, sim in similarities.items()
                if sim >= threshold
            ]
            selected_experts.sort(key=lambda x: x[1], reverse=True)

            # Dynamic selection with relevance gap analysis
            # Don't force selection of k agents if they're not relevant
            final_experts = self._apply_relevance_gap_filter(
                selected_experts,
                max_k=k,
                relevance_gap_threshold=0.15
            )

            logger.info(f"[SemanticSelector] Dynamic selection: {len(final_experts)} experts from {len(selected_experts)} candidates")

            # Map experts to agents
            selected_agents = []
            for expert_name, sim in final_experts:
                agents = self._expert_to_agents.get(expert_name, [])
                selected_agents.extend(agents)
                logger.debug(f"[SemanticSelector] Expert '{expert_name}' (sim={sim:.3f}) → agents: {agents}")

            # Deduplicate while preserving order
            seen = set()
            result = []
            for agent_id in selected_agents:
                if agent_id not in seen:
                    seen.add(agent_id)
                    result.append(agent_id)

            # Limit to k agents (dynamic upper bound)
            result = result[:k]

            # Log final selection with performance metrics
            total_time_ms = (time.time() - selection_start) * 1000
            logger.info(
                f"[SemanticSelector] Selected {len(result)} agents in {total_time_ms:.1f}ms: {result}"
            )

            # Fallback if no experts selected
            if not result:
                logger.warning("[SemanticSelector] No experts met threshold, using fallback")
                result = self._get_fallback_experts(1)  # Single fallback agent

            # Log cache statistics periodically for monitoring
            if isinstance(self._provider, CachedEmbeddingProvider):
                stats = self._provider.get_cache_stats()
                if stats["total_requests"] % 20 == 0:  # Every 20 requests
                    logger.info(
                        f"[EmbeddingCache] Stats: {stats['hit_rate']:.1%} hit rate "
                        f"({stats['hits']}/{stats['total_requests']} requests, "
                        f"{stats['cache_size']} entries)"
                    )

            return result

        except Exception as e:
            logger.error(f"Semantic expert selection failed: {e}")
            raise ExpertSelectionException(f"Semantic expert selection failed: {e}")

    @staticmethod
    def _apply_relevance_gap_filter(
        sorted_experts: List[tuple[str, float]],
        max_k: int = 3,
        relevance_gap_threshold: float = 0.15
    ) -> List[tuple[str, float]]:
        """
        Apply relevance gap filtering to avoid selecting weakly matched experts.

        Strategy:
        - Always select the top expert (most relevant)
        - Add additional experts only if gap from previous < threshold
        - Stop when gap > threshold or max_k reached

        Examples:
            Scores: [0.85, 0.82, 0.45] → Select 2 (gap 0.03, then 0.37 > 0.15)
            Scores: [0.90, 0.65, 0.60] → Select 1 (gap 0.25 > 0.15)
            Scores: [0.75, 0.72, 0.70] → Select 3 (all gaps < 0.15)

        Args:
            sorted_experts: List of (expert_name, similarity) sorted by similarity desc
            max_k: Maximum number of experts to select
            relevance_gap_threshold: Max similarity gap to include next expert

        Returns:
            Filtered list of (expert_name, similarity) tuples
        """
        if not sorted_experts:
            return []

        # Always include the top expert
        selected = [sorted_experts[0]]

        # Add additional experts if relevance gap is small
        for i in range(1, min(len(sorted_experts), max_k)):
            prev_score = sorted_experts[i - 1][1]
            curr_score = sorted_experts[i][1]
            gap = prev_score - curr_score

            if gap <= relevance_gap_threshold:
                selected.append(sorted_experts[i])
                logger.debug(f"[SemanticSelector] Adding expert {sorted_experts[i][0]} (gap={gap:.3f} < {relevance_gap_threshold})")
            else:
                logger.debug(f"[SemanticSelector] Stopping selection: gap={gap:.3f} > {relevance_gap_threshold}")
                break

        return selected

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0-1 range after normalization)
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)

        # Convert from [-1, 1] to [0, 1] range
        return (similarity + 1) / 2

    def _get_fallback_experts(self, k: int) -> List[str]:
        """
        Get fallback experts when no match found.

        Returns general-purpose agents like chitchat or one (web search).

        Args:
            k: Number of experts to return

        Returns:
            List of fallback agent IDs
        """
        fallback_candidates = []

        # Look for general experts (chitchat, search)
        for expert_name, expert_config in self._config.experts.items():
            if any(agent in ["chitchat", "one", "perplexity"] for agent in expert_config.agents):
                fallback_candidates.extend(expert_config.agents)

        # Deduplicate and limit
        fallback_candidates = list(set(fallback_candidates))

        # Return up to k agents
        return fallback_candidates[:k] if fallback_candidates else ["one"]
