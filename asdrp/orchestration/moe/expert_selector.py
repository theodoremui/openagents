"""
Expert Selector - Tier 1 of MoE Pipeline.

Selects relevant expert agents based on query analysis.
"""

from typing import List, Dict, Set

from asdrp.orchestration.moe.interfaces import IExpertSelector
from asdrp.orchestration.moe.config_loader import MoEConfig
from asdrp.orchestration.moe.exceptions import ExpertSelectionException


class CapabilityBasedSelector(IExpertSelector):
    """
    Select experts based on capability matching.

    Strategy:
    1. Extract keywords from query (simple NLP)
    2. Match keywords to expert capabilities
    3. Return top-k experts by match score

    Fast and deterministic (no LLM call).
    """

    def __init__(self, config: MoEConfig):
        """
        Initialize selector with configuration.

        Args:
            config: MoE configuration
        """
        self._config = config
        self._capability_map = self._build_capability_map()

    def _build_capability_map(self) -> Dict[str, List[str]]:
        """
        Build mapping of capability -> agent_ids.

        Example:
            {
                "geocoding": ["geo", "map"],
                "restaurants": ["yelp", "yelp_mcp"],
                ...
            }

        Returns:
            Dict mapping capabilities to agent IDs
        """
        capability_map: Dict[str, List[str]] = {}

        for expert_name, expert_config in self._config.experts.items():
            for capability in expert_config.capabilities:
                if capability not in capability_map:
                    capability_map[capability] = []
                capability_map[capability].extend(expert_config.agents)

        return capability_map

    async def select(
        self,
        query: str,
        k: int = 3,
        threshold: float = 0.3
    ) -> List[str]:
        """
        Select experts based on capability matching.

        Args:
            query: User query
            k: Max experts to select
            threshold: Min match score

        Returns:
            List of agent IDs (e.g., ["yelp", "geo", "map"])

        Raises:
            ExpertSelectionException: If selection fails
        """
        try:
            # Extract keywords
            keywords = self._extract_keywords(query)

            # Keep selector deterministic and quiet; tracing happens at orchestrator level.

            if not keywords:
                # Fallback to chitchat or general agent
                print(f"[ExpertSelector] No keywords extracted, using fallback")
                return self._get_fallback_experts(k)

            # Check for location/place query heuristics
            # If query looks like it's asking about a place/location, boost location experts
            is_location_query = self._is_likely_location_query(query, keywords)

            # (Optional) location query boost

            # Score experts (bidirectional matching for better coverage)
            expert_scores: Dict[str, float] = {}
            for keyword in keywords:
                keyword_lower = keyword.lower()
                for capability, agents in self._capability_map.items():
                    capability_lower = capability.lower()

                    # Match if keyword is in capability OR capability is in keyword
                    # This handles: "map" matches "maps", "driving" matches "drive", etc.
                    if (keyword_lower in capability_lower or
                        capability_lower in keyword_lower or
                        keyword_lower == capability_lower):
                        for agent_id in agents:
                            if agent_id not in expert_scores:
                                expert_scores[agent_id] = 0.0
                            expert_scores[agent_id] += 1.0

            # Apply location query boost if detected
            if is_location_query:
                # Get location expert agents from config
                location_agents = []
                for expert_name, expert_config in self._config.experts.items():
                    if "location" in expert_name.lower():
                        location_agents.extend(expert_config.agents)

                # Boost location agents significantly
                for agent_id in location_agents:
                    if agent_id not in expert_scores:
                        expert_scores[agent_id] = 0.0
                    expert_scores[agent_id] += 3.0  # Strong boost

            # Normalize scores
            if expert_scores:
                max_score = max(expert_scores.values())
                expert_scores = {
                    agent_id: score / max_score
                    for agent_id, score in expert_scores.items()
                }

            # Filter and sort
            selected = [
                (agent_id, score)
                for agent_id, score in expert_scores.items()
                if score >= threshold
            ]
            selected.sort(key=lambda x: x[1], reverse=True)

            # Apply dynamic selection with relevance gap filter
            # Don't force k agents if they're not relevant
            final_selected = self._apply_relevance_gap_filter(
                selected,
                max_k=k,
                relevance_gap_threshold=0.2  # Slightly higher for lexical (less precise)
            )


            # Return agent IDs
            result = [agent_id for agent_id, score in final_selected]


            # If no experts selected, use fallback
            if not result:
                result = self._get_fallback_experts(k)

            return result

        except Exception as e:
            raise ExpertSelectionException(f"Expert selection failed: {e}")

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query.

        Strategy:
        - Remove only basic stop words (keep domain-relevant terms)
        - Preserve location/place names
        - Keep action verbs that indicate intent
        - Extract unique words

        Args:
            query: User query

        Returns:
            List of keywords
        """
        # Minimal stop words - only remove truly non-informative words
        # DO NOT remove: find, show, get, search, etc. (they indicate intent)
        stop_words: Set[str] = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "this", "that", "these", "those",
            "i", "you", "he", "she", "it", "we", "they",
            "my", "your", "his", "her", "its", "our", "their",
            "me", "him", "her", "us", "them",
            "can", "could", "will", "would", "shall", "should", "may", "might", "must",
            "do", "does", "did", "have", "has", "had",
            "and", "or", "but", "not", "if", "then", "so",
            "of", "as"
        }

        # Tokenize conservatively: keep alpha-numeric words, strip punctuation.
        # This fixes cases like "Francisco." being dropped.
        words = query.lower().split()

        cleaned: List[str] = []
        for w in words:
            token = "".join(ch for ch in w if ch.isalnum())
            if not token:
                continue
            if token in stop_words:
                continue
            cleaned.append(token)

        # Deduplicate while preserving order (stable for downstream prioritization).
        seen: Set[str] = set()
        out: List[str] = []
        for t in cleaned:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def _is_likely_location_query(self, query: str, keywords: List[str]) -> bool:
        """
        Heuristic to detect if a query is asking about a location/place.

        Indicators:
        1. Contains location-related words (directions, map, where, near, etc.)
        2. Query pattern suggests place name (capitalized words, multi-word terms)
        3. Contains location prepositions (to, from, in, at, near)

        Args:
            query: Original user query
            keywords: Extracted keywords

        Returns:
            True if likely a location query, False otherwise
        """
        query_lower = query.lower()

        # Strong location indicators
        location_indicators = {
            "directions", "map", "maps", "where", "near", "nearby",
            "address", "location", "navigate", "navigation", "route",
            "driving", "drive", "walk", "go", "going",
            "distance", "miles", "km", "away",
            "street", "road", "avenue", "boulevard",
            "city", "town", "place", "area",
        }

        # Location prepositions that indicate place queries
        location_prepositions = {"to", "from", "in", "near", "around", "at"}

        # Check for location indicators in keywords or query
        has_location_keyword = any(
            indicator in query_lower or indicator in keywords
            for indicator in location_indicators
        )

        # Check for location prepositions
        has_location_preposition = any(
            f" {prep} " in f" {query_lower} "
            for prep in location_prepositions
        )

        # Check for capitalized words (potential place names like "San Carlos", "New York")
        words = query.split()
        has_capitalized_words = sum(1 for w in words if w[0].isupper() and len(w) > 1) >= 2

        # If query has location indicators OR (prepositions AND capitalized words)
        is_location = has_location_keyword or (has_location_preposition and has_capitalized_words)

        # Additional check: short queries with capitalized words are likely place names
        if len(keywords) <= 3 and has_capitalized_words:
            is_location = True

        return is_location

    @staticmethod
    def _apply_relevance_gap_filter(
        sorted_agents: List[tuple[str, float]],
        max_k: int = 3,
        relevance_gap_threshold: float = 0.2
    ) -> List[tuple[str, float]]:
        """
        Apply relevance gap filtering to avoid selecting weakly matched agents.

        Strategy:
        - Always select the top agent (most relevant)
        - Add additional agents only if gap from previous < threshold
        - Stop when gap > threshold or max_k reached

        Args:
            sorted_agents: List of (agent_id, score) sorted by score desc
            max_k: Maximum number of agents to select
            relevance_gap_threshold: Max score gap to include next agent

        Returns:
            Filtered list of (agent_id, score) tuples
        """
        if not sorted_agents:
            return []

        # Always include the top agent
        selected = [sorted_agents[0]]

        # Add additional agents if relevance gap is small
        for i in range(1, min(len(sorted_agents), max_k)):
            prev_score = sorted_agents[i - 1][1]
            curr_score = sorted_agents[i][1]
            gap = prev_score - curr_score

            if gap <= relevance_gap_threshold:
                selected.append(sorted_agents[i])
                print(f"[ExpertSelector] Adding agent {sorted_agents[i][0]} (gap={gap:.3f} < {relevance_gap_threshold})")
            else:
                print(f"[ExpertSelector] Stopping selection: gap={gap:.3f} > {relevance_gap_threshold}")
                break

        return selected

    def _get_fallback_experts(self, k: int = 1) -> List[str]:
        """
        Get fallback experts when no match found.

        Returns general-purpose agents like chitchat or one (web search).
        Prioritizes single agent for efficiency.

        Args:
            k: Number of experts to return (default 1 for fallback)

        Returns:
            List of fallback agent IDs
        """
        # Priority order for fallback
        fallback_priority = ["chitchat", "one", "perplexity"]

        # Find available fallback agents
        available_fallback = []
        for expert_name, expert_config in self._config.experts.items():
            for agent in expert_config.agents:
                if agent in fallback_priority and agent not in available_fallback:
                    available_fallback.append(agent)

        # Sort by priority
        available_fallback.sort(key=lambda x: fallback_priority.index(x) if x in fallback_priority else 999)

        # Return single agent for fallback (most efficient)
        return available_fallback[:k] if available_fallback else ["one"]
