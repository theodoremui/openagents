"""
Expert Executor - Tier 2 of MoE Pipeline.

Executes selected experts in parallel.
"""

from typing import List, Tuple, Optional, Dict, Any
import asyncio
from dataclasses import dataclass
import time

from asdrp.agents.protocol import AgentProtocol
from asdrp.orchestration.moe.interfaces import IExpertExecutor
from asdrp.orchestration.moe.config_loader import MoEConfig
from asdrp.orchestration.moe.exceptions import ExecutionException

from loguru import logger

@dataclass
class ExpertResult:
    """Result from expert execution."""
    expert_id: str
    output: str
    success: bool
    latency_ms: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    # Wall-clock timestamps captured at the moment the expert starts/finishes execution.
    # These allow UIs to show true per-expert completion times even when other experts are still running.
    started_at: Optional[float] = None
    ended_at: Optional[float] = None


class ParallelExecutor(IExpertExecutor):
    """
    Execute experts in parallel using asyncio.gather.

    Features:
    - Concurrent execution (up to max_concurrent)
    - Per-expert timeouts
    - Graceful error handling
    - Follows SmartRouter parallel execution pattern
    """

    def __init__(self, config: MoEConfig):
        """
        Initialize executor with configuration.

        Args:
            config: MoE configuration
        """
        self._config = config
        self._max_concurrent = config.moe.get("max_concurrent", 10)
        # Increased default timeout to 25s to match Yelp API timeout
        # This prevents premature timeouts for MCP agents like YelpMCPAgent
        self._timeout_per_expert = config.moe.get("timeout_per_expert", 25.0)

    async def execute_parallel(
        self,
        agents_with_sessions: List[Tuple[str, AgentProtocol, Any]],
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> List[ExpertResult]:
        """
        Execute agents in parallel.

        Args:
            agents_with_sessions: List of (expert_id, agent, session)
            query: Query to process
            context: Optional context
            timeout: Overall timeout

        Returns:
            List of ExpertResult

        Raises:
            ExecutionException: If execution fails critically
        """
        if not agents_with_sessions:
            raise ExecutionException("No agents provided for execution")

        # Create tasks
        tasks = [
            self._execute_single(expert_id, agent, session, query, context)
            for expert_id, agent, session in agents_with_sessions
        ]

        # Execute with overall timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Return partial results with timeout errors
            results = [
                ExpertResult(
                    expert_id=expert_id,
                    output="",
                    success=False,
                    latency_ms=timeout * 1000,
                    error="Overall timeout exceeded"
                )
                for expert_id, _, _ in agents_with_sessions
            ]

        # Convert exceptions to error results
        final_results = []
        for (expert_id, _, _), result in zip(agents_with_sessions, results):
            if isinstance(result, Exception):
                final_results.append(ExpertResult(
                    expert_id=expert_id,
                    output="",
                    success=False,
                    latency_ms=0.0,
                    error=str(result)
                ))
            else:
                final_results.append(result)

        return final_results

    async def _execute_single(
        self,
        expert_id: str,
        agent: AgentProtocol,
        session: Any,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> ExpertResult:
        """
        Execute single agent with timeout.

        Args:
            expert_id: Agent ID
            agent: Agent instance
            session: Session object
            query: Query to process
            context: Optional context

        Returns:
            ExpertResult with execution outcome
        """
        start_monotonic = asyncio.get_event_loop().time()
        started_at = time.time()

        try:
            result = await self._run_agent_with_mcp_support(
                expert_id=expert_id,
                agent=agent,
                query=query,
                context=context,
                session=session
            )

            ended_at = time.time()
            latency_ms = (asyncio.get_event_loop().time() - start_monotonic) * 1000

            return self._build_success_result(
                expert_id=expert_id,
                result=result,
                latency_ms=latency_ms,
                started_at=started_at,
                ended_at=ended_at
            )

        except asyncio.TimeoutError:
            return self._build_timeout_result(
                expert_id=expert_id,
                started_at=started_at
            )

        except Exception as e:
            return self._build_error_result(
                expert_id=expert_id,
                error=e,
                start_monotonic=start_monotonic,
                started_at=started_at
            )

    def _detect_mcp_servers(self, agent: AgentProtocol, expert_id: str) -> Optional[List[Any]]:
        """
        Detect MCP servers attached to an agent using multiple detection strategies.

        MCP-enabled agents require async context management for MCP servers.
        This method tries multiple approaches to find MCP servers since the OpenAI
        Agent class may store them in different locations.

        Follows the pattern from yelp_mcp_agent.py main() function which uses:
        mcp_servers = getattr(agent, 'mcp_servers', None)

        Args:
            agent: Agent instance to inspect
            expert_id: Expert ID for logging

        Returns:
            List of MCP servers if found, None otherwise
        """
        # Strategy 1: Direct attribute access (most common - matches yelp_mcp_agent.py pattern)
        mcp_servers = getattr(agent, "mcp_servers", None)
        if mcp_servers:
            # Validate it's a list/tuple with actual servers
            if isinstance(mcp_servers, (list, tuple)) and len(mcp_servers) > 0:
                logger.debug(f"[MoE Executor] Found {len(mcp_servers)} MCP server(s) via direct 'mcp_servers' attribute for {expert_id}")
                return list(mcp_servers)  # Convert to list for consistency
            elif mcp_servers:  # Non-empty but not list/tuple (shouldn't happen, but handle gracefully)
                logger.warning(f"[MoE Executor] mcp_servers is not a list/tuple for {expert_id}: {type(mcp_servers)}")
                return None

        # Strategy 2: Internal storage attribute
        mcp_servers = getattr(agent, "_mcp_servers", None)
        if mcp_servers:
            if isinstance(mcp_servers, (list, tuple)) and len(mcp_servers) > 0:
                logger.debug(f"[MoE Executor] Found {len(mcp_servers)} MCP server(s) via '_mcp_servers' attribute for {expert_id}")
                return list(mcp_servers)

        # Strategy 3: Dictionary inspection (for custom agent wrappers)
        if hasattr(agent, "__dict__"):
            for attr_name, attr_value in agent.__dict__.items():
                if "mcp" in attr_name.lower() and isinstance(attr_value, (list, tuple)) and len(attr_value) > 0:
                    logger.debug(f"[MoE Executor] Found MCP servers via __dict__['{attr_name}'] for {expert_id}")
                    return list(attr_value)

        # Strategy 4: Internal _agent attribute (OpenAI Agent structure)
        if hasattr(agent, "_agent"):
            inner_agent = getattr(agent, "_agent", None)
            if inner_agent:
                mcp_servers = getattr(inner_agent, "mcp_servers", None) or getattr(inner_agent, "_mcp_servers", None)
                if mcp_servers and isinstance(mcp_servers, (list, tuple)) and len(mcp_servers) > 0:
                    logger.debug(f"[MoE Executor] Found {len(mcp_servers)} MCP server(s) via _agent.mcp_servers for {expert_id}")
                    return list(mcp_servers)

        # Strategy 5: Comprehensive attribute scan (fallback for edge cases)
        agent_attrs = dir(agent)
        for attr in agent_attrs:
            if "mcp" in attr.lower() and not attr.startswith("__"):
                try:
                    attr_value = getattr(agent, attr)
                    if isinstance(attr_value, (list, tuple)) and len(attr_value) > 0:
                        # Validate it looks like an MCP server (has context manager methods)
                        first_item = attr_value[0]
                        if hasattr(first_item, "__aenter__") or hasattr(first_item, "name"):
                            logger.debug(f"[MoE Executor] Found MCP servers via comprehensive scan '{attr}' for {expert_id}")
                            return list(attr_value)
                except Exception as e:
                    logger.debug(f"[MoE Executor] Error checking attribute '{attr}' for {expert_id}: {e}")
                    continue

        # Log warning for known MCP agents that should have servers
        if expert_id in ("yelp_mcp", "yelp-mcp"):
            # Get sample of agent attributes for debugging
            sample_attrs = [attr for attr in dir(agent) if not attr.startswith("__")][:15]
            logger.warning(
                f"[MoE Executor] WARNING: {expert_id} should have MCP servers but none detected. "
                f"Agent type: {type(agent).__name__}, "
                f"has 'mcp_servers': {hasattr(agent, 'mcp_servers')}, "
                f"sample attributes: {sample_attrs}"
            )

        return None

    async def _connect_mcp_servers(
        self,
        mcp_servers: List[Any],
        expert_id: str,
        stack: Any
    ) -> None:
        """
        Connect MCP servers using async context managers.

        Follows the pattern from yelp_mcp_agent.py main() function:
        ```python
        async with AsyncExitStack() as stack:
            for mcp_server in mcp_servers:
                await stack.enter_async_context(mcp_server)
        ```

        Args:
            mcp_servers: List of MCP server instances
            expert_id: Expert ID for logging
            stack: AsyncExitStack to manage contexts

        Raises:
            ExecutionException: If connection fails or server is invalid
        """
        logger.info(f"[MoE Executor] Connecting {len(mcp_servers)} MCP server(s) for {expert_id}")

        for i, mcp_server in enumerate(mcp_servers):
            # Validate MCP server has required context manager methods
            if not hasattr(mcp_server, "__aenter__"):
                logger.error(
                    f"[MoE Executor] MCP server {i+1} for {expert_id} missing __aenter__ method. "
                    f"Server type: {type(mcp_server).__name__}"
                )
                raise ExecutionException(
                    f"MCP server {i+1} for {expert_id} is not a valid async context manager (missing __aenter__)"
                )
            
            if not hasattr(mcp_server, "__aexit__"):
                logger.error(
                    f"[MoE Executor] MCP server {i+1} for {expert_id} missing __aexit__ method. "
                    f"Server type: {type(mcp_server).__name__}"
                )
                raise ExecutionException(
                    f"MCP server {i+1} for {expert_id} is not a valid async context manager (missing __aexit__)"
                )

            try:
                logger.debug(
                    f"[MoE Executor] Entering context for MCP server {i+1}/{len(mcp_servers)} for {expert_id} "
                    f"(type: {type(mcp_server).__name__})"
                )
                # Enter the async context - this connects to the MCP server
                # This is the critical step that makes MCP tools available
                await stack.enter_async_context(mcp_server)
                logger.info(f"[MoE Executor] ✓ Connected MCP server {i+1}/{len(mcp_servers)} for {expert_id}")
            except Exception as e:
                logger.error(
                    f"[MoE Executor] ✗ Failed to connect MCP server {i+1} for {expert_id}: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise ExecutionException(
                    f"Failed to connect MCP server for {expert_id}: {e}"
                ) from e

    async def _run_agent_with_mcp_support(
        self,
        expert_id: str,
        agent: AgentProtocol,
        query: str,
        context: Optional[Dict[str, Any]],
        session: Any
    ) -> Any:
        """
        Run agent with MCP server support if needed.

        Follows the pattern from yelp_mcp_agent.py main() function:
        ```python
        mcp_servers = getattr(agent, 'mcp_servers', None)
        if isinstance(mcp_servers, (list, tuple)) and len(mcp_servers) > 0:
            async with AsyncExitStack() as stack:
                for mcp_server in mcp_servers:
                    await stack.enter_async_context(mcp_server)
                result = await Runner.run(agent, input=query, session=session)
        ```

        Args:
            expert_id: Expert ID
            agent: Agent instance
            query: Query to process
            context: Optional context
            session: Session object

        Returns:
            Runner result
        """
        from agents import Runner
        from contextlib import AsyncExitStack
        from loguru import logger

        mcp_servers = self._detect_mcp_servers(agent, expert_id)

        if mcp_servers and len(mcp_servers) > 0:
            logger.info(f"[MoE Executor] Detected {len(mcp_servers)} MCP server(s) for {expert_id}")
            logger.debug(f"[MoE Executor] Running {expert_id} with connected MCP servers")

            # Use AsyncExitStack to manage MCP server contexts
            # This ensures servers are connected before Runner.run() and cleaned up after
            async with AsyncExitStack() as stack:
                # Connect all MCP servers before running the agent
                # This is critical - MCP tools are only available after connection
                await self._connect_mcp_servers(mcp_servers, expert_id, stack)
                
                # Now run the agent - MCP servers are connected and tools are available
                logger.debug(f"[MoE Executor] MCP servers connected, executing {expert_id} with Runner.run()")
                return await asyncio.wait_for(
                    Runner.run(
                        starting_agent=agent,
                        input=query,
                        context=context,
                        max_turns=10,
                        session=session,
                    ),
                    timeout=self._timeout_per_expert
                )
        else:
            logger.debug(f"[MoE Executor] Running {expert_id} without MCP servers")
            return await asyncio.wait_for(
                Runner.run(
                    starting_agent=agent,
                    input=query,
                    context=context,
                    max_turns=10,
                    session=session,
                ),
                timeout=self._timeout_per_expert
            )

    def _extract_output(self, result: Any, expert_id: str) -> str:
        """
        Extract output text from Runner result.

        Args:
            result: Runner result object
            expert_id: Expert ID for logging

        Returns:
            Output string (empty string if not found)
        """
        from loguru import logger

        output = None

        if hasattr(result, 'final_output'):
            final_output = result.final_output
            if final_output is not None:
                output = str(final_output)
        else:
            # Fallback: try other common attribute names
            output = getattr(result, 'output', None)
            if output is not None:
                output = str(output)

        # Log output for debugging
        if output:
            output_preview = output[:100] + "..." if len(output) > 100 else output
            logger.debug(f"[MoE Executor] {expert_id} output: {output_preview}")
        else:
            logger.warning(
                f"[MoE Executor] {expert_id} has no output "
                f"(final_output={getattr(result, 'final_output', 'N/A')})"
            )

        return output or ""

    def _extract_metadata(self, result: Any) -> Dict[str, Any]:
        """
        Extract metadata from Runner result.

        Args:
            result: Runner result object

        Returns:
            Metadata dictionary
        """
        metadata = {}
        if hasattr(result, 'usage'):
            metadata['usage'] = {
                'total_tokens': getattr(result.usage, 'total_tokens', 0),
                'prompt_tokens': getattr(result.usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(result.usage, 'completion_tokens', 0),
            }
        return metadata

    def _build_success_result(
        self,
        expert_id: str,
        result: Any,
        latency_ms: float,
        started_at: float,
        ended_at: float
    ) -> ExpertResult:
        """
        Build ExpertResult for successful execution.

        Args:
            expert_id: Expert ID
            result: Runner result
            latency_ms: Execution latency in milliseconds
            started_at: Start timestamp
            ended_at: End timestamp

        Returns:
            ExpertResult with success status
        """
        return ExpertResult(
            expert_id=expert_id,
            output=self._extract_output(result, expert_id),
            success=True,
            latency_ms=latency_ms,
            metadata=self._extract_metadata(result),
            started_at=started_at,
            ended_at=ended_at,
        )

    def _build_timeout_result(
        self,
        expert_id: str,
        started_at: float
    ) -> ExpertResult:
        """
        Build ExpertResult for timeout error.

        Args:
            expert_id: Expert ID
            started_at: Start timestamp

        Returns:
            ExpertResult with timeout error
        """
        ended_at = time.time()
        error_msg = f"Timeout after {self._timeout_per_expert}s"

        # Special handling for MapAgent timeouts
        if expert_id == "map":
            error_msg = (
                f"Timeout after {self._timeout_per_expert}s. "
                "Note: Interactive maps may still appear in the final response if generated by "
                "other agents (e.g., YelpMCPAgent, YelpAgent) or auto-injected by the result mixer."
            )

        return ExpertResult(
            expert_id=expert_id,
            output="",
            success=False,
            latency_ms=self._timeout_per_expert * 1000,
            error=error_msg,
            started_at=started_at,
            ended_at=ended_at,
        )

    def _build_error_result(
        self,
        expert_id: str,
        error: Exception,
        start_monotonic: float,
        started_at: float
    ) -> ExpertResult:
        """
        Build ExpertResult for execution error.

        Args:
            expert_id: Expert ID
            error: Exception that occurred
            start_monotonic: Start time (monotonic)
            started_at: Start timestamp

        Returns:
            ExpertResult with error status
        """
        ended_at = time.time()
        latency_ms = (asyncio.get_event_loop().time() - start_monotonic) * 1000

        return ExpertResult(
            expert_id=expert_id,
            output="",
            success=False,
            latency_ms=latency_ms,
            error=f"Execution error: {str(error)}",
            started_at=started_at,
            ended_at=ended_at,
        )
