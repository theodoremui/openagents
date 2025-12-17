"""
QueryDecomposer - Query Decomposition into Subqueries

Breaks complex queries into independent, routable subqueries.
Ensures no cyclic dependencies and validates decomposition structure.

Design Principles:
-----------------
- Single Responsibility: Only responsible for query decomposition
- Dependency Injection: LLM client and config injected
- Validation: Strict dependency validation (no cycles)
- Robustness: Handles edge cases (simple queries, malformed output)

Responsibilities:
----------------
- Decompose complex queries into atomic subqueries
- Assign capability requirements to each subquery
- Determine routing patterns (delegation vs handoff)
- Validate dependency graph (acyclic)
- Respect configuration limits (max_subqueries, recursion_limit)
"""

from typing import Dict, Any, Optional, List, Set
import json
import logging
import uuid

from agents import ModelSettings

from asdrp.orchestration.smartrouter.interfaces import (
    IQueryDecomposer,
    QueryIntent,
    Subquery,
    RoutingPattern,
    QueryComplexity,
)
from asdrp.orchestration.smartrouter.exceptions import QueryDecompositionException
from asdrp.orchestration.smartrouter.config_loader import ModelConfig, DecompositionConfig

logger = logging.getLogger(__name__)


class QueryDecomposer(IQueryDecomposer):
    """
    Implementation of query decomposition using LLM.

    Breaks down complex queries into subqueries that can be routed
    to specialist agents. Ensures decomposition is valid (no cycles)
    and respects configuration limits.

    The decomposer uses structured prompting to generate subqueries
    with clear capability requirements and dependencies.

    Usage:
    ------
    >>> decomposer = QueryDecomposer(
    ...     model_config=ModelConfig(...),
    ...     decomp_config=DecompositionConfig(...)
    ... )
    >>> intent = QueryIntent(...)
    >>> subqueries = await decomposer.decompose(intent)
    >>> print(len(subqueries))
    3
    """

    # System prompt for query decomposition
    DECOMPOSITION_PROMPT = """You are a query decomposition expert. Break down the complex query into independent subqueries.

Each subquery should:
- Be atomic and independently executable
- Require one specific capability (geocoding, finance, search, etc.)
- Have clear dependencies on other subqueries (if any)

Available capabilities:
- geocoding: Address to coordinates, reverse geocoding
- finance: Stock prices, market data, financial information
- search: Web search, general knowledge queries
- local_business: Restaurant/business search and reviews
- wikipedia: Encyclopedia knowledge, definitions
- research: Academic research, in-depth analysis
- mapping: Directions, routes, map visualization

Routing patterns:
- delegation: Agent completes task and returns (most common)
- handoff: Agent handles iterative/complex interaction

Respond ONLY with valid JSON array:
[
  {
    "id": "sq1",
    "text": "Subquery text here",
    "capability_required": "capability_name",
    "dependencies": [],
    "routing_pattern": "delegation|handoff"
  },
  ...
]

If query is SIMPLE, return empty array: []

User Query: """

    def __init__(
        self,
        model_config: ModelConfig,
        decomp_config: DecompositionConfig,
        llm_client: Optional[Any] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize QueryDecomposer.

        Args:
            model_config: Configuration for the LLM model
            decomp_config: Decomposition configuration (limits, thresholds)
            llm_client: Optional custom LLM client (for testing/DI)
            session_id: Optional session ID for conversation memory
        """
        self.model_config = model_config
        self.decomp_config = decomp_config
        self._llm_client = llm_client
        self.session_id = session_id

        # Create session ONCE during initialization (OpenAI best practice)
        self._session = None
        if session_id:
            from agents import SQLiteSession
            self._session = SQLiteSession(
                session_id=f"{session_id}_decomposer",
                db_path="data/sessions/smartrouter.db"  # Persistent file-based storage
            )
            logger.info(f"QueryDecomposer: Created persistent session {session_id}_decomposer")

    async def decompose(self, intent: QueryIntent) -> List[Subquery]:
        """
        Decompose a query into subqueries.

        Args:
            intent: Interpreted query intent

        Returns:
            List of Subquery objects (empty for simple queries)

        Raises:
            QueryDecompositionException: If decomposition fails or cycles detected

        Examples:
        ---------
        >>> intent = QueryIntent(
        ...     original_query="Stock price of AAPL and location of Apple HQ",
        ...     complexity=QueryComplexity.MODERATE,
        ...     domains=["finance", "geography"],
        ...     requires_synthesis=True,
        ...     metadata={}
        ... )
        >>> subqueries = await decomposer.decompose(intent)
        >>> assert len(subqueries) == 2
        >>> assert subqueries[0].capability_required == "finance"
        >>> assert subqueries[1].capability_required == "geocoding"
        """
        try:
            logger.debug(f"Decomposing query: {intent.original_query[:100]}...")

            # Simple queries don't need decomposition
            if intent.complexity == QueryComplexity.SIMPLE:
                logger.info("Query is SIMPLE, no decomposition needed")
                return []

            # Use LLM to decompose query
            decomposition_result = await self._call_decomposition_llm(intent)

            # Parse LLM response
            subqueries = self._parse_decomposition(intent, decomposition_result)

            # Validate subqueries
            self._validate_subqueries(subqueries)

            # Validate dependencies
            self.validate_dependencies(subqueries)

            logger.info(
                f"Query decomposed into {len(subqueries)} subqueries: "
                f"{[sq.id for sq in subqueries]}"
            )

            return subqueries

        except QueryDecompositionException:
            raise
        except Exception as e:
            raise QueryDecompositionException(
                f"Query decomposition failed: {str(e)}",
                context={"query": intent.original_query},
                original_exception=e
            ) from e

    async def _call_decomposition_llm(self, intent: QueryIntent) -> str:
        """
        Call LLM for query decomposition.

        Args:
            intent: Query intent

        Returns:
            LLM response string (expected to be JSON array)

        Raises:
            QueryDecompositionException: If LLM call fails
        """
        try:
            # Build prompt with context
            prompt = f"{self.DECOMPOSITION_PROMPT}\n{intent.original_query}\n\n"
            prompt += f"Query Complexity: {intent.complexity.value}\n"
            prompt += f"Domains: {', '.join(intent.domains)}\n"
            prompt += f"Synthesis Required: {intent.requires_synthesis}"

            if self._llm_client:
                # Custom client (for testing)
                return await self._llm_client.generate(
                    prompt=prompt,
                    model=self.model_config.name,
                    temperature=self.model_config.temperature,
                    max_tokens=self.model_config.max_tokens,
                )

            # Use openai-agents SDK
            from agents import Agent, Runner

            agent = Agent(
                name="QueryDecomposer",
                instructions=self.DECOMPOSITION_PROMPT,
                model=self.model_config.name,
                model_settings=ModelSettings(
                    temperature=self.model_config.temperature,
                    max_tokens=self.model_config.max_tokens,
                ),
            )

            # Use the persistent session created in __init__
            result = await Runner.run(agent, input=intent.original_query, session=self._session)
            return str(result.final_output)

        except Exception as e:
            raise QueryDecompositionException(
                f"LLM decomposition call failed: {str(e)}",
                context={"query": intent.original_query, "model": self.model_config.name},
                original_exception=e
            ) from e

    def _parse_decomposition(self, intent: QueryIntent, llm_response: str) -> List[Subquery]:
        """
        Parse LLM response into list of Subquery objects.

        Args:
            intent: Original query intent
            llm_response: LLM response (expected JSON array)

        Returns:
            List of Subquery objects

        Raises:
            QueryDecompositionException: If parsing fails
        """
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_str = llm_response.strip()
            if json_str.startswith("```json"):
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif json_str.startswith("```"):
                json_str = json_str.split("```")[1].split("```")[0].strip()

            # Parse JSON array
            data = json.loads(json_str)

            if not isinstance(data, list):
                raise QueryDecompositionException(
                    "LLM response is not a JSON array",
                    context={"response": llm_response[:200]}
                )

            # Empty array means simple query (no decomposition)
            if not data:
                logger.info("LLM returned empty array, treating as simple query")
                return []

            # Parse each subquery
            subqueries: List[Subquery] = []
            for i, sq_data in enumerate(data):
                try:
                    # Generate ID if not provided or invalid
                    sq_id = sq_data.get("id", f"sq{i+1}")
                    if not sq_id or not isinstance(sq_id, str):
                        sq_id = f"sq{i+1}"

                    # Extract fields
                    text = sq_data.get("text", "")
                    capability = sq_data.get("capability_required", "search")
                    dependencies = sq_data.get("dependencies", [])
                    routing_pattern_str = sq_data.get("routing_pattern", "delegation")

                    # Validate fields
                    if not text:
                        logger.warning(f"Subquery {sq_id} has empty text, skipping")
                        continue

                    if not isinstance(dependencies, list):
                        dependencies = []

                    # Parse routing pattern
                    try:
                        routing_pattern = RoutingPattern[routing_pattern_str.upper()]
                    except KeyError:
                        logger.warning(
                            f"Invalid routing pattern '{routing_pattern_str}', "
                            f"defaulting to DELEGATION"
                        )
                        routing_pattern = RoutingPattern.DELEGATION

                    subquery = Subquery(
                        id=sq_id,
                        text=text,
                        capability_required=capability,
                        dependencies=dependencies,
                        routing_pattern=routing_pattern,
                        metadata={
                            "index": i,
                            "original_query": intent.original_query,
                        }
                    )

                    subqueries.append(subquery)

                except Exception as e:
                    logger.warning(f"Failed to parse subquery {i}: {str(e)}", exc_info=True)
                    continue

            return subqueries

        except json.JSONDecodeError as e:
            raise QueryDecompositionException(
                f"Failed to parse LLM response as JSON: {str(e)}",
                context={"llm_response": llm_response[:200]},
                original_exception=e
            ) from e
        except QueryDecompositionException:
            raise
        except Exception as e:
            raise QueryDecompositionException(
                f"Failed to parse decomposition: {str(e)}",
                context={"llm_response": llm_response[:200]},
                original_exception=e
            ) from e

    def _validate_subqueries(self, subqueries: List[Subquery]) -> None:
        """
        Validate subqueries meet configuration requirements.

        Args:
            subqueries: List of subqueries to validate

        Raises:
            QueryDecompositionException: If validation fails
        """
        # Check max subqueries limit
        if len(subqueries) > self.decomp_config.max_subqueries:
            raise QueryDecompositionException(
                f"Too many subqueries: {len(subqueries)} > {self.decomp_config.max_subqueries}",
                context={
                    "count": len(subqueries),
                    "max": self.decomp_config.max_subqueries,
                }
            )

        # Check for duplicate IDs
        ids = [sq.id for sq in subqueries]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise QueryDecompositionException(
                f"Duplicate subquery IDs: {duplicates}",
                context={"duplicates": duplicates}
            )

        # Check that dependency IDs are valid
        for sq in subqueries:
            for dep_id in sq.dependencies:
                if dep_id not in ids:
                    raise QueryDecompositionException(
                        f"Subquery {sq.id} depends on non-existent subquery {dep_id}",
                        context={"subquery_id": sq.id, "invalid_dependency": dep_id}
                    )

    def validate_dependencies(self, subqueries: List[Subquery]) -> bool:
        """
        Validate that subquery dependencies are acyclic.

        Uses depth-first search to detect cycles in the dependency graph.

        Args:
            subqueries: List of subqueries to validate

        Returns:
            True if dependencies are valid (acyclic)

        Raises:
            QueryDecompositionException: If cyclic dependencies detected

        Examples:
        ---------
        >>> sq1 = Subquery(id="sq1", dependencies=["sq2"], ...)
        >>> sq2 = Subquery(id="sq2", dependencies=["sq1"], ...)
        >>> decomposer.validate_dependencies([sq1, sq2])
        QueryDecompositionException: Cyclic dependency detected: sq1 -> sq2 -> sq1
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        for sq in subqueries:
            graph[sq.id] = sq.dependencies

        # DFS to detect cycles
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            """DFS helper. Returns cycle path if found, None otherwise."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        # Check each connected component
        for sq in subqueries:
            if sq.id not in visited:
                cycle = dfs(sq.id)
                if cycle:
                    cycle_str = " -> ".join(cycle)
                    raise QueryDecompositionException(
                        f"Cyclic dependency detected: {cycle_str}",
                        context={"cycle": cycle}
                    )

        return True
