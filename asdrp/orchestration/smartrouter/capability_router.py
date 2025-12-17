"""
CapabilityRouter - Agent Selection Based on Capabilities

Routes subqueries to appropriate agents based on capability maps.
Determines routing patterns (delegation vs handoff) based on query characteristics.

Design Principles:
-----------------
- Single Responsibility: Only responsible for agent routing
- Dependency Injection: Capability map injected for testability
- Open/Closed: Easy to add new routing strategies
- Robustness: Handles missing capabilities gracefully

Responsibilities:
----------------
- Match subqueries to agents using capability keywords
- Determine appropriate routing pattern
- Handle capability overlaps (multiple agents)
- Provide fallback routing when no exact match
"""

from typing import Dict, List, Tuple, Set, Optional
import logging

from asdrp.orchestration.smartrouter.interfaces import (
    ICapabilityRouter,
    Subquery,
    RoutingPattern,
)
from asdrp.orchestration.smartrouter.exceptions import RoutingException
from asdrp.orchestration.smartrouter.cache import get_capability_cache, get_routing_cache

logger = logging.getLogger(__name__)


class CapabilityRouter(ICapabilityRouter):
    """
    Implementation of capability-based agent routing.

    Uses a capability map (agent_id -> list of capabilities) to match
    subqueries to appropriate agents. Handles capability overlaps by
    selecting the most specialized agent.

    The router also determines the appropriate routing pattern:
    - DELEGATION: For most queries (agent completes and returns)
    - HANDOFF: For iterative/complex queries (agent takes over)

    Usage:
    ------
    >>> capability_map = {
    ...     "geo": ["geocoding", "reverse_geocoding", "mapping"],
    ...     "finance": ["stocks", "market_data"],
    ...     "one": ["search", "general_knowledge"]
    ... }
    >>> router = CapabilityRouter(capability_map)
    >>> subquery = Subquery(
    ...     id="sq1",
    ...     text="Find address for coordinates",
    ...     capability_required="reverse_geocoding",
    ...     ...
    ... )
    >>> agent_id, pattern = router.route(subquery)
    >>> assert agent_id == "geo"
    >>> assert pattern == RoutingPattern.DELEGATION
    """

    def __init__(self, capability_map: Dict[str, List[str]], use_cache: bool = True):
        """
        Initialize CapabilityRouter.

        Args:
            capability_map: Dictionary mapping agent_id to list of capabilities
                Example: {"geo": ["geocoding", "mapping"], ...}
            use_cache: Enable caching for improved performance (default: True)
        """
        self.capability_map = capability_map
        self.use_cache = use_cache

        # Build reverse index: capability -> list of agent_ids
        self._reverse_index: Dict[str, List[str]] = {}
        for agent_id, capabilities in capability_map.items():
            for capability in capabilities:
                if capability not in self._reverse_index:
                    self._reverse_index[capability] = []
                self._reverse_index[capability].append(agent_id)

        # Initialize global capability cache
        if self.use_cache:
            capability_cache = get_capability_cache()
            if not capability_cache.is_initialized():
                capability_cache.initialize(capability_map)
                logger.info("CapabilityCache initialized with capability map")

        logger.debug(
            f"CapabilityRouter initialized with {len(capability_map)} agents, "
            f"{len(self._reverse_index)} unique capabilities, "
            f"cache={'enabled' if use_cache else 'disabled'}"
        )

    def route(self, subquery: Subquery) -> Tuple[str, RoutingPattern]:
        """
        Route a subquery to an appropriate agent.

        Selects agent based on capability match. If multiple agents
        have the capability, selects the most specialized one.

        Args:
            subquery: The subquery to route

        Returns:
            Tuple of (agent_id, routing_pattern)

        Raises:
            RoutingException: If no suitable agent found

        Examples:
        ---------
        >>> agent_id, pattern = router.route(subquery)
        >>> print(f"Routing to {agent_id} with {pattern.value}")
        Routing to geo with delegation
        """
        try:
            logger.debug(
                f"Routing subquery {subquery.id}: "
                f"capability={subquery.capability_required}"
            )

            # Check routing cache for capability -> agent_id mapping
            if self.use_cache:
                routing_cache = get_routing_cache()
                cached_agent_id = routing_cache.get_routing(subquery.capability_required)
                if cached_agent_id:
                    routing_pattern = self._determine_routing_pattern(subquery, cached_agent_id)
                    logger.debug(
                        f"Routing cache hit for capability '{subquery.capability_required}': "
                        f"agent '{cached_agent_id}'"
                    )
                    return cached_agent_id, routing_pattern

            # Find agents with required capability
            candidates = self._find_candidate_agents(subquery.capability_required)

            if not candidates:
                raise RoutingException(
                    f"No agent found with capability '{subquery.capability_required}'",
                    context={
                        "subquery_id": subquery.id,
                        "capability": subquery.capability_required,
                        "available_capabilities": list(self._reverse_index.keys()),
                    }
                )

            # Select best agent from candidates
            agent_id = self._select_best_agent(subquery, candidates)

            # Determine routing pattern (use subquery's preference if set)
            routing_pattern = self._determine_routing_pattern(subquery, agent_id)

            # Cache routing decision
            if self.use_cache:
                routing_cache = get_routing_cache()
                routing_cache.set_routing(subquery.capability_required, agent_id)

            logger.info(
                f"Routed subquery {subquery.id} to agent '{agent_id}' "
                f"with pattern {routing_pattern.value}"
            )

            return agent_id, routing_pattern

        except RoutingException:
            raise
        except Exception as e:
            raise RoutingException(
                f"Routing failed for subquery {subquery.id}: {str(e)}",
                context={
                    "subquery_id": subquery.id,
                    "capability": subquery.capability_required,
                },
                original_exception=e
            ) from e

    def get_capabilities(self, agent_id: str) -> List[str]:
        """
        Get capabilities for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of capability keywords

        Raises:
            RoutingException: If agent not found

        Examples:
        ---------
        >>> capabilities = router.get_capabilities("geo")
        >>> print(capabilities)
        ['geocoding', 'reverse_geocoding', 'mapping']
        """
        if agent_id not in self.capability_map:
            raise RoutingException(
                f"Agent '{agent_id}' not found in capability map",
                context={
                    "agent_id": agent_id,
                    "available_agents": list(self.capability_map.keys()),
                }
            )

        return self.capability_map[agent_id]

    def _find_candidate_agents(self, capability: str) -> List[str]:
        """
        Find all agents that have the required capability.

        Args:
            capability: Capability keyword to search for

        Returns:
            List of agent IDs (may be empty)
        """
        # Check cache first
        if self.use_cache:
            capability_cache = get_capability_cache()
            cached_agents = capability_cache.find_agents_for_capability(capability)
            if cached_agents:
                logger.debug(f"Cache hit for capability '{capability}': {cached_agents}")
                return cached_agents

        # Exact match
        if capability in self._reverse_index:
            return self._reverse_index[capability]

        # Fuzzy match: capability is substring of agent capability
        fuzzy_candidates: List[str] = []
        for agent_capability, agents in self._reverse_index.items():
            if capability in agent_capability or agent_capability in capability:
                fuzzy_candidates.extend(agents)

        if fuzzy_candidates:
            logger.debug(
                f"No exact match for '{capability}', using fuzzy match: "
                f"{fuzzy_candidates}"
            )
            return fuzzy_candidates

        # Fallback: check if any agent has capability as primary domain
        # E.g., "geo" agent for "geography" capability
        for agent_id in self.capability_map.keys():
            if agent_id in capability or capability in agent_id:
                logger.debug(
                    f"No capability match for '{capability}', "
                    f"using agent domain match: {agent_id}"
                )
                return [agent_id]

        return []

    def _select_best_agent(self, subquery: Subquery, candidates: List[str]) -> str:
        """
        Select the best agent from multiple candidates.

        Selection heuristics:
        1. Agent with fewest total capabilities (most specialized)
        2. First agent alphabetically (deterministic)

        Args:
            subquery: The subquery being routed
            candidates: List of candidate agent IDs

        Returns:
            Selected agent ID
        """
        if len(candidates) == 1:
            return candidates[0]

        logger.debug(
            f"Multiple candidates for subquery {subquery.id}: {candidates}. "
            f"Selecting most specialized."
        )

        # Select agent with fewest capabilities (most specialized)
        selected = min(
            candidates,
            key=lambda agent_id: (
                len(self.capability_map[agent_id]),  # Fewer capabilities = more specialized
                agent_id,  # Alphabetical tie-breaker
            )
        )

        logger.debug(f"Selected agent '{selected}' from {candidates}")
        return selected

    def _determine_routing_pattern(
        self,
        subquery: Subquery,
        agent_id: str  # Reserved for future agent-specific routing logic
    ) -> RoutingPattern:
        """
        Determine appropriate routing pattern.

        Uses subquery's routing_pattern if specified, otherwise uses delegation.
        Handoff is used for iterative/complex interactions.

        Args:
            subquery: The subquery being routed
            agent_id: Target agent ID (reserved for future use)

        Returns:
            RoutingPattern (DELEGATION or HANDOFF)
        """
        # Use subquery's preferred pattern if specified
        if subquery.routing_pattern:
            return subquery.routing_pattern

        # Default: use delegation for most queries
        # Handoff would be determined by QueryDecomposer based on query analysis
        # Future: agent-specific routing preferences could use agent_id here
        return RoutingPattern.DELEGATION

    def get_all_agents(self) -> List[str]:
        """
        Get list of all available agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self.capability_map.keys())

    def get_all_capabilities(self) -> Set[str]:
        """
        Get set of all available capabilities.

        Returns:
            Set of capability keywords
        """
        return set(self._reverse_index.keys())

    def can_route(self, capability: str) -> bool:
        """
        Check if a capability can be routed to any agent.

        Args:
            capability: Capability keyword

        Returns:
            True if at least one agent has this capability
        """
        candidates = self._find_candidate_agents(capability)
        return len(candidates) > 0
