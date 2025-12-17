"""
AsyncSubqueryDispatcher - Asynchronous Subquery Execution

Dispatches subqueries to agents asynchronously with timeout and error handling.
Manages concurrent execution and aggregates results.

Design Principles:
-----------------
- Single Responsibility: Only responsible for dispatching subqueries
- Dependency Injection: Agent factory and config injected
- Robustness: Handles timeouts, errors, retries gracefully
- Concurrency: Uses asyncio for parallel execution

Responsibilities:
----------------
- Execute subqueries on target agents asynchronously
- Handle timeouts and retries
- Capture and wrap agent errors
- Support both single and batch dispatch
- Maintain execution order and context
"""

from typing import List, Tuple, Optional, Any
import asyncio
import logging
from datetime import datetime

from agents import Runner

from asdrp.orchestration.smartrouter.interfaces import (
    ISubqueryDispatcher,
    Subquery,
    AgentResponse,
)
from asdrp.orchestration.smartrouter.exceptions import DispatchException
from asdrp.orchestration.smartrouter.config_loader import ErrorHandlingConfig

logger = logging.getLogger(__name__)


class AsyncSubqueryDispatcher(ISubqueryDispatcher):
    """
    Implementation of asynchronous subquery dispatcher.

    Executes subqueries on agents concurrently using asyncio.
    Handles timeouts, errors, and retries according to configuration.

    The dispatcher wraps agent responses in AgentResponse objects,
    capturing success/failure status and metadata.

    Usage:
    ------
    >>> from asdrp.agents.agent_factory import AgentFactory
    >>> factory = AgentFactory.instance()
    >>> error_config = ErrorHandlingConfig(timeout=30, retries=2)
    >>> dispatcher = AsyncSubqueryDispatcher(factory, error_config)
    >>>
    >>> subquery = Subquery(...)
    >>> response = await dispatcher.dispatch(subquery, "geo", timeout=20)
    >>> print(response.success, response.content)
    True The address is...
    """

    def __init__(
        self,
        agent_factory: Any,  # AgentFactory instance
        error_config: ErrorHandlingConfig,
        session_id: Optional[str] = None,
        session: Optional[Any] = None  # SQLiteSession or None
    ):
        """
        Initialize AsyncSubqueryDispatcher.

        Args:
            agent_factory: AgentFactory instance for creating agents
            error_config: Error handling configuration (timeouts, retries)
            session_id: Optional session ID for stateful agents
            session: Optional session object to use (takes precedence over session_id)
        """
        self.agent_factory = agent_factory
        self.error_config = error_config
        self.session_id = session_id
        self.session = session

    async def dispatch(
        self,
        subquery: Subquery,
        agent_id: str,
        timeout: Optional[float] = None
    ) -> AgentResponse:
        """
        Dispatch a subquery to an agent asynchronously.

        Executes the subquery with timeout and retry handling.
        Returns AgentResponse with result or error information.

        Args:
            subquery: The subquery to execute
            agent_id: Target agent identifier
            timeout: Optional timeout in seconds (overrides config)

        Returns:
            AgentResponse with result or error

        Raises:
            DispatchException: If dispatch fails critically (not agent errors)

        Examples:
        ---------
        >>> response = await dispatcher.dispatch(subquery, "geo", timeout=20)
        >>> if response.success:
        ...     print(f"Success: {response.content}")
        ... else:
        ...     print(f"Error: {response.error}")
        """
        start_time = datetime.now()
        timeout_value = timeout or self.error_config.timeout

        logger.debug(
            f"Dispatching subquery {subquery.id} to agent '{agent_id}' "
            f"with timeout {timeout_value}s"
        )

        # Retry loop
        last_error: Optional[Exception] = None
        for attempt in range(self.error_config.retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"Retry attempt {attempt}/{self.error_config.retries} "
                        f"for subquery {subquery.id}"
                    )

                # Execute with timeout
                response = await asyncio.wait_for(
                    self._execute_subquery(subquery, agent_id),
                    timeout=timeout_value
                )

                # Success - add execution time to metadata
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"Subquery {subquery.id} completed successfully "
                    f"in {execution_time:.2f}s (attempt {attempt + 1})"
                )

                # Add execution_time to response metadata
                if response.metadata is None:
                    response.metadata = {}
                response.metadata["execution_time"] = execution_time

                return response

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"Subquery {subquery.id} timed out after {timeout_value}s "
                    f"(attempt {attempt + 1}/{self.error_config.retries + 1})"
                )

                if attempt < self.error_config.retries:
                    # Retry with exponential backoff
                    backoff = 2 ** attempt
                    await asyncio.sleep(backoff)
                    continue

                # Final timeout - return error response
                return AgentResponse(
                    subquery_id=subquery.id,
                    agent_id=agent_id,
                    content="",
                    success=False,
                    error=f"Timeout after {timeout_value}s (retries exhausted)",
                    metadata={
                        "attempts": attempt + 1,
                        "timeout": timeout_value,
                        "execution_time": (datetime.now() - start_time).total_seconds(),
                    }
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Subquery {subquery.id} failed: {str(e)} "
                    f"(attempt {attempt + 1}/{self.error_config.retries + 1})",
                    exc_info=True
                )

                if attempt < self.error_config.retries:
                    # Retry with exponential backoff
                    backoff = 2 ** attempt
                    await asyncio.sleep(backoff)
                    continue

                # Final failure - return error response
                return AgentResponse(
                    subquery_id=subquery.id,
                    agent_id=agent_id,
                    content="",
                    success=False,
                    error=str(e),
                    metadata={
                        "attempts": attempt + 1,
                        "error_type": type(e).__name__,
                        "execution_time": (datetime.now() - start_time).total_seconds(),
                    }
                )

        # Should not reach here, but handle defensively
        return AgentResponse(
            subquery_id=subquery.id,
            agent_id=agent_id,
            content="",
            success=False,
            error=str(last_error) if last_error else "Unknown error",
            metadata={"attempts": self.error_config.retries + 1}
        )

    async def dispatch_all(
        self,
        subqueries: List[Tuple[Subquery, str]],
        timeout: Optional[float] = None
    ) -> List[AgentResponse]:
        """
        Dispatch multiple subqueries concurrently.

        Executes all subqueries in parallel using asyncio.gather.
        Returns responses in the same order as input.

        Args:
            subqueries: List of (subquery, agent_id) tuples
            timeout: Optional timeout in seconds (per subquery)

        Returns:
            List of AgentResponse objects (includes errors)

        Raises:
            DispatchException: If dispatch system fails critically

        Examples:
        ---------
        >>> subqueries = [
        ...     (subquery1, "geo"),
        ...     (subquery2, "finance"),
        ...     (subquery3, "one")
        ... ]
        >>> responses = await dispatcher.dispatch_all(subqueries, timeout=30)
        >>> print(f"{len(responses)} responses received")
        3 responses received
        """
        if not subqueries:
            logger.debug("No subqueries to dispatch")
            return []

        logger.info(f"Dispatching {len(subqueries)} subqueries concurrently")

        try:
            # Create dispatch tasks
            tasks = [
                self.dispatch(subquery, agent_id, timeout)
                for subquery, agent_id in subqueries
            ]

            # Execute concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=False)

            # Log summary
            success_count = sum(1 for r in responses if r.success)
            logger.info(
                f"Batch dispatch completed: {success_count}/{len(responses)} successful"
            )

            return responses

        except Exception as e:
            raise DispatchException(
                f"Batch dispatch failed: {str(e)}",
                context={"subquery_count": len(subqueries)},
                original_exception=e
            ) from e

    async def _execute_subquery(
        self,
        subquery: Subquery,
        agent_id: str
    ) -> AgentResponse:
        """
        Execute a single subquery on an agent.

        Args:
            subquery: The subquery to execute
            agent_id: Target agent identifier

        Returns:
            AgentResponse with result

        Raises:
            Exception: Any agent execution error (caught by dispatch method)
        """
        try:
            # Use SmartRouter's session if available, otherwise use agent factory session
            if self.session is not None:
                # SmartRouter has its own session - use it for all agents
                agent = await self.agent_factory.get_agent(agent_id)
                session = self.session
                logger.debug(
                    f"Using SmartRouter session for agent '{agent_id}' "
                    "in subquery dispatcher"
                )
            elif self.session_id:
                agent, session = await self.agent_factory.get_agent_with_session(
                    agent_id,
                    session_id=self.session_id  # ✅ Shared session for cross-agent context
                )
                logger.debug(
                    f"Using shared session '{self.session_id}' for agent '{agent_id}' "
                    "in subquery dispatcher"
                )
            else:
                agent = await self.agent_factory.get_agent(agent_id)
                session = None

            # Execute subquery
            logger.debug(f"Executing subquery {subquery.id} on agent {agent_id}")

            run_result = await Runner.run(
                starting_agent=agent,
                input=subquery.text,
                session=session
            )

            # Extract response content
            content = str(run_result.final_output)

            # Build metadata
            metadata = {
                "agent_name": agent.name,
                "routing_pattern": subquery.routing_pattern.value,
            }

            # Add usage information if available
            if hasattr(run_result, "usage") and run_result.usage:
                metadata["usage"] = {
                    "total_tokens": getattr(run_result.usage, "total_tokens", None),
                    "prompt_tokens": getattr(run_result.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(run_result.usage, "completion_tokens", None),
                }

            return AgentResponse(
                subquery_id=subquery.id,
                agent_id=agent_id,
                content=content,
                success=True,
                error=None,
                metadata=metadata
            )

        except Exception as e:
            # Let caller handle the exception
            logger.error(
                f"Agent execution failed for subquery {subquery.id}: {str(e)}",
                exc_info=True
            )
            raise
