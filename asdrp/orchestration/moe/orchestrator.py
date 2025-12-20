"""
MoE Orchestrator - Main Coordination Logic.

Coordinates the three-tier MoE pipeline:
1. Expert Selection
2. Parallel Execution
3. Result Mixing
"""

from typing import Optional, List, Any
import asyncio
import uuid
from dataclasses import dataclass
from loguru import logger

from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.protocol import AgentProtocol
from asdrp.orchestration.moe.interfaces import (
    IExpertSelector,
    IExpertExecutor,
    IResultMixer,
    ICache
)
from asdrp.orchestration.moe.config_loader import MoEConfigLoader, MoEConfig
from asdrp.orchestration.moe.exceptions import MoEException
from asdrp.orchestration.moe.fast_path import FastPathDetector


@dataclass
class ExpertExecutionDetail:
    """Detailed execution info for a single expert."""
    expert_id: str
    agent_name: str
    confidence: float
    status: str  # "pending", "executing", "completed", "failed"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    latency_ms: Optional[float] = None
    response: Optional[str] = None
    tools_used: Optional[List[str]] = None
    error: Optional[str] = None


@dataclass
class MoETrace:
    """
    Enhanced orchestration trace for observability and visualization.

    Captures detailed stage-by-stage execution information for ReactFlow display.
    """
    request_id: str
    query: str

    # Timestamps (seconds since epoch)
    selection_start: Optional[float] = None
    selection_end: Optional[float] = None
    execution_start: Optional[float] = None
    execution_end: Optional[float] = None
    mixing_start: Optional[float] = None
    mixing_end: Optional[float] = None

    # Expert details
    selected_experts: Optional[List[str]] = None
    expert_details: Optional[List[ExpertExecutionDetail]] = None

    # Results
    expert_results: Optional[List[Any]] = None
    final_response: Optional[str] = None

    # Performance
    latency_ms: float = 0.0
    cache_hit: bool = False
    fallback: bool = False
    error: Optional[str] = None


@dataclass
class MoEResult:
    """Result from MoE orchestration."""
    response: str
    experts_used: List[str]
    trace: MoETrace


class MoEOrchestrator:
    """
    Mixture of Experts Orchestrator.

    Three-tier pipeline:
    1. Expert Selection: Choose relevant experts based on query
    2. Parallel Execution: Execute selected experts concurrently
    3. Result Mixing: Combine expert outputs with confidence weighting

    Architecture:
    - Located in asdrp/orchestration/moe/ (separate from agents)
    - Uses existing AgentFactory from asdrp/agents/ for expert creation
    - Follows SmartRouter dependency injection pattern
    - Compatible with existing API layer (server/agent_service.py)

    Example:
        >>> from asdrp.agents.agent_factory import AgentFactory
        >>> from asdrp.orchestration.moe.config_loader import MoEConfigLoader
        >>> from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
        >>>
        >>> factory = AgentFactory.instance()
        >>> config = MoEConfigLoader().load_config()
        >>> orchestrator = MoEOrchestrator.create_default(factory, config)
        >>> result = await orchestrator.route_query("Find pizza near me")
    """

    def __init__(
        self,
        agent_factory: AgentFactory,
        expert_selector: IExpertSelector,
        expert_executor: IExpertExecutor,
        result_mixer: IResultMixer,
        config: MoEConfig,
        cache: Optional[ICache] = None,
        fast_path_detector: Optional[FastPathDetector] = None
    ):
        """
        Initialize MoE Orchestrator with dependency injection.

        Args:
            agent_factory: Existing AgentFactory instance from asdrp.agents
            expert_selector: Expert selection component
            expert_executor: Parallel execution component
            result_mixer: Result aggregation component
            config: MoE configuration
            cache: Optional semantic cache
            fast_path_detector: Optional fast-path bypass for simple queries
        """
        self._factory = agent_factory
        self._selector = expert_selector
        self._executor = expert_executor
        self._mixer = result_mixer
        self._config = config
        self._cache = cache
        self._fast_path = fast_path_detector

    @staticmethod
    def _prioritize_agents_for_map_intent(query: str, agent_ids: List[str], max_k: int) -> List[str]:
        """
        Ensure map-focused queries include MapAgent (and keep it within the k-limit).

        Why:
        - Semantic selection can select business_expert (yelp + yelp_mcp) and location_expert (geo + map).
        - With top_k_experts=3, truncation often drops `map`, preventing interactive_map output.

        Policy (deterministic):
        - If the query implies "map/pins/show on map", ensure `map` is included.
        - For business + map queries, prefer: yelp_mcp, yelp, map, geo (in that order, within max_k).
        - If `map` would be dropped due to k-limit, replace `geo` first, otherwise replace the last agent.
        """
        if not agent_ids:
            return agent_ids

        if not isinstance(max_k, int) or max_k <= 0:
            return []

        q = (query or "").lower()

        # Strong intent markers for "show me pins / map view / where are they"
        map_markers = (
            "map",
            "maps",
            "pin",
            "pins",
            "map view",
            "show on map",
            "show me on a map",
            "where are they",
            "where these",
            "detailed map",
            "interactive map",
        )
        map_intent = any(m in q for m in map_markers)
        if not map_intent:
            return agent_ids[:max_k]

        # If we have a map intent, we always want the MapAgent available.
        # Ensure it's present in the candidate list (even if selector didn't include it).
        candidates = list(agent_ids)
        if "map" not in candidates:
            candidates.append("map")

        business_markers = ("restaurant", "restaurants", "food", "dining", "cafe", "cafes", "bar", "bars")
        business_intent = any(m in q for m in business_markers) or ("yelp" in candidates) or ("yelp_mcp" in candidates)

        # For restaurant map requests, YelpMCPAgent is the best default because it can
        # generate a "places" interactive map using coordinates from Yelp results.
        # Semantic selection sometimes truncates away yelp_mcp early, so we re-inject it.
        if business_intent and "yelp_mcp" not in candidates:
            candidates.append("yelp_mcp")

        preferred_order: List[str] = []
        if business_intent:
            for a in ("yelp_mcp", "yelp"):
                if a in candidates:
                    preferred_order.append(a)
        # Map should come before geo for visualization
        if "map" in candidates:
            preferred_order.append("map")
        if "geo" in candidates:
            preferred_order.append("geo")

        # Fill remaining in original order
        seen = set(preferred_order)
        for a in candidates:
            if a not in seen:
                preferred_order.append(a)
                seen.add(a)

        # Enforce max_k but keep map within it.
        trimmed = preferred_order[:max_k]
        if "map" not in trimmed:
            # Prefer replacing geo; otherwise replace last.
            if "geo" in trimmed:
                idx = trimmed.index("geo")
                trimmed[idx] = "map"
            else:
                trimmed[-1] = "map"

        # Deduplicate while preserving order (just in case)
        out: List[str] = []
        seen2 = set()
        for a in trimmed:
            if a not in seen2:
                out.append(a)
                seen2.add(a)
        return out

    async def route_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[dict] = None
    ) -> MoEResult:
        """
        Route query through MoE pipeline.

        Flow:
        1. Check cache (~1ms)
        2. Select experts (~10-50ms)
        3. Execute in parallel (~500-1500ms)
        4. Mix results (~100-300ms)
        5. Store in cache

        Args:
            query: User's natural language query
            session_id: Session ID for multi-turn conversations
            context: Optional context (location, preferences)

        Returns:
            MoEResult with response and trace
        """
        import time
        from asdrp.orchestration.moe.performance_monitor import get_performance_monitor
        
        # Initialize performance monitoring
        perf_monitor = get_performance_monitor()
        perf_context = perf_monitor.start_request()
        
        # Orchestrators must always have session-level memory. If caller didn't provide a session_id,
        # generate one (caller should persist/reuse it across turns for multi-turn continuity).
        if session_id is None:
            session_id = f"moe-{uuid.uuid4().hex}"

        start_time = asyncio.get_event_loop().time()
        request_id = self._generate_request_id()

        # Initialize trace
        trace = MoETrace(request_id=request_id, query=query)

        try:
            # 1. Fast-path check (bypass full pipeline for simple queries)
            if self._fast_path:
                fast_path_agent = await self._fast_path.detect_fast_path(query)
                if fast_path_agent:
                    logger.info(f"[MoE] Fast-path bypass → {fast_path_agent}")
                    result = await self._execute_fast_path(
                        fast_path_agent,
                        query,
                        session_id,
                        start_time,
                        request_id,
                        trace
                    )
                    perf_monitor.finish_request(perf_context, cache_hit=False)
                    return result

            # 2. Check cache
            cache_hit = False
            if self._cache and self._config.cache.enabled:
                cached = await self._cache.get(query)
                if cached:
                    cache_hit = True
                    result = self._build_cached_result(cached, start_time, request_id, trace)
                    perf_monitor.finish_request(perf_context, cache_hit=True)
                    return result

            # 2. Select experts
            perf_monitor.record_selection_start(perf_context)
            trace.selection_start = time.time()
            max_k = self._config.moe.get("top_k_experts", 3)
            from asdrp.orchestration.moe.exceptions import ExpertSelectionException
            try:
                selected_expert_ids = await self._selector.select(
                    query,
                    k=max_k,
                    threshold=self._config.moe.get("confidence_threshold", 0.3)
                )
            except ExpertSelectionException as e:
                # Fail open: semantic selection can fail due to transient embedding/SDK issues.
                # Fall back to deterministic capability selection for this request.
                trace.fallback = True
                trace.error = str(e)
                logger.warning(
                    f"[MoE] Selector failed ({e}); falling back to CapabilityBasedSelector for this request"
                )
                from asdrp.orchestration.moe.expert_selector import CapabilityBasedSelector
                selected_expert_ids = await CapabilityBasedSelector(self._config).select(
                    query,
                    k=max_k,
                    threshold=self._config.moe.get("confidence_threshold", 0.3)
                )
            except Exception as e:
                # Unexpected selector errors should use the configured fallback agent.
                result = await self._handle_fallback(query, session_id, e, trace, start_time)
                perf_monitor.finish_request(perf_context, cache_hit=False)
                return result

            # Defensive: selectors must return list[str]. If a selector returns None (or any
            # malformed value), fail open to fallback agent instead of crashing later with
            # confusing "NoneType is not subscriptable/iterable" errors.
            if not isinstance(selected_expert_ids, list):
                result = await self._handle_fallback(
                    query,
                    session_id,
                    Exception(f"Selector returned invalid type: {type(selected_expert_ids).__name__}"),
                    trace,
                    start_time
                )
                perf_monitor.finish_request(perf_context, cache_hit=False)
                return result

            # Map/pins queries are expected to return an interactive map payload.
            # Ensure MapAgent isn't dropped due to k-limit truncation (common when combined with Yelp agents).
            pre_prioritization = selected_expert_ids[:]
            selected_expert_ids = self._prioritize_agents_for_map_intent(query, selected_expert_ids, max_k)

            if pre_prioritization != selected_expert_ids:
                logger.info(
                    f"[MoE] Map intent prioritization changed agent list:\n"
                    f"  Before: {pre_prioritization}\n"
                    f"  After:  {selected_expert_ids}"
                )

            # Performance optimization: filter experts based on circuit breaker status
            optimized_expert_ids = perf_monitor.optimize_expert_selection(selected_expert_ids, max_k)
            if optimized_expert_ids != selected_expert_ids:
                logger.info(f"[MoE] Performance optimization changed expert selection: {selected_expert_ids} → {optimized_expert_ids}")
                selected_expert_ids = optimized_expert_ids

            logger.info(f"[MoE] Final selected agents: {selected_expert_ids}")

            trace.selection_end = time.time()
            trace.selected_experts = selected_expert_ids
            perf_monitor.record_selection_end(perf_context, selected_expert_ids)

            # Create expert details with initial "pending" status
            trace.expert_details = [
                ExpertExecutionDetail(
                    expert_id=expert_id,
                    agent_name=expert_id,  # Will be updated later
                    confidence=0.8,  # Placeholder, selector doesn't return confidence yet
                    status="pending"
                )
                for expert_id in selected_expert_ids
            ]

            # 3. Get agents from factory with sessions
            agents_with_sessions = []
            failed_agents = []
            
            for expert_id in selected_expert_ids:
                try:
                    agent, session = await self._factory.get_agent_with_persistent_session(
                        expert_id, session_id
                    )
                    
                    # For MCP-enabled agents, verify MCP servers are accessible
                    # This helps catch configuration issues early
                    if expert_id in ("yelp_mcp", "yelp-mcp"):
                        mcp_servers = getattr(agent, "mcp_servers", None)
                        if not mcp_servers:
                            # Try alternative access methods
                            mcp_servers = getattr(agent, "_mcp_servers", None)
                        if not mcp_servers and hasattr(agent, "__dict__"):
                            for attr_name, attr_value in agent.__dict__.items():
                                if "mcp" in attr_name.lower() and isinstance(attr_value, (list, tuple)):
                                    mcp_servers = attr_value
                                    break
                        
                        if mcp_servers:
                            logger.debug(f"[MoE] Verified {expert_id} has {len(mcp_servers)} MCP server(s)")
                        else:
                            logger.warning(
                                f"[MoE] WARNING: {expert_id} should have MCP servers but none detected. "
                                f"Agent type: {type(agent).__name__}. "
                                f"This may cause 'Server not initialized' errors."
                            )
                    
                    agents_with_sessions.append((expert_id, agent, session))

                    # Update agent name in trace
                    for detail in trace.expert_details:
                        if detail.expert_id == expert_id:
                            detail.agent_name = getattr(agent, 'name', expert_id)
                            break
                except Exception as e:
                    logger.warning(f"Failed to get agent {expert_id}: {e}")
                    failed_agents.append(expert_id)

                    # Mark as failed in trace
                    for detail in trace.expert_details:
                        if detail.expert_id == expert_id:
                            detail.status = "failed"
                            detail.error = str(e)
                            break
                    continue

            # Implement business agent fallback: if yelp_mcp fails, ensure yelp is available
            if "yelp_mcp" in failed_agents and "yelp" not in [a[0] for a in agents_with_sessions]:
                logger.info("[MoE] Implementing business agent fallback: yelp_mcp failed, adding yelp")
                try:
                    agent, session = await self._factory.get_agent_with_persistent_session("yelp", session_id)
                    agents_with_sessions.append(("yelp", agent, session))
                    logger.info("[MoE] ✅ Business agent fallback successful: yelp added")
                except Exception as e:
                    logger.warning(f"[MoE] Business agent fallback failed: {e}")

            if not agents_with_sessions:
                # Fallback if no agents could be loaded
                result = await self._handle_fallback(
                    query, session_id, Exception("No agents could be loaded"), trace, start_time
                )
                perf_monitor.finish_request(perf_context, cache_hit=False)
                return result

            # 4. Execute in parallel
            perf_monitor.record_execution_start(perf_context)
            trace.execution_start = time.time()

            # Update status to executing
            for detail in trace.expert_details:
                if detail.status == "pending":
                    detail.status = "executing"
                    # Do not stamp a shared start_time for all experts; the executor records
                    # accurate per-expert started_at/ended_at timestamps.
                    detail.start_time = None

            expert_results = await self._executor.execute_parallel(
                agents_with_sessions,
                query,
                context,
                timeout=self._config.moe.get("overall_timeout", 30.0)
            )
            if not isinstance(expert_results, list):
                result = await self._handle_fallback(
                    query,
                    session_id,
                    Exception(f"Executor returned invalid type: {type(expert_results).__name__}"),
                    trace,
                    start_time
                )
                perf_monitor.finish_request(perf_context, cache_hit=False)
                return result
            trace.execution_end = time.time()
            trace.expert_results = expert_results
            perf_monitor.record_execution_end(perf_context, expert_results)

            # If all experts failed (common when API keys/tools are missing), fail open to the
            # configured fallback agent instead of returning an unhelpful apology.
            successful_experts = []
            try:
                successful_experts = [r for r in expert_results if getattr(r, "success", False)]
                if not successful_experts:
                    logger.warning("[MoE] All selected experts failed - implementing fallback")
                    result = await self._handle_fallback(
                        query, session_id, Exception("All selected experts failed"), trace, start_time
                    )
                    perf_monitor.finish_request(perf_context, cache_hit=False)
                    return result
                else:
                    # Partial success handling: log which experts succeeded/failed
                    failed_experts = [r for r in expert_results if not getattr(r, "success", False)]
                    if failed_experts:
                        failed_ids = [getattr(r, "expert_id", "unknown") for r in failed_experts]
                        successful_ids = [getattr(r, "expert_id", "unknown") for r in successful_experts]
                        logger.info(f"[MoE] Partial success: {len(successful_experts)} succeeded ({successful_ids}), {len(failed_experts)} failed ({failed_ids})")
                        
                        # Special handling for business+map queries where map fails
                        business_agents = ["yelp", "yelp_mcp"]
                        map_agents = ["map", "geo"]
                        
                        successful_business = any(r for r in successful_experts if getattr(r, "expert_id", "") in business_agents)
                        failed_map = any(r for r in failed_experts if getattr(r, "expert_id", "") in map_agents)
                        
                        if successful_business and failed_map and ("map" in query.lower() or "pins" in query.lower()):
                            logger.info("[MoE] Business data available but map failed - will rely on geocoding fallback")
            except Exception:
                # If expert_results is malformed for any reason, continue to mixing.
                pass

            # Update expert details with results
            for i, (expert_id, _, _) in enumerate(agents_with_sessions):
                if i < len(expert_results):
                    result = expert_results[i]
                    for detail in trace.expert_details:
                        if detail.expert_id == expert_id:
                            # Prefer precise timestamps captured by the executor.
                            started_at = getattr(result, "started_at", None) if result else None
                            ended_at = getattr(result, "ended_at", None) if result else None
                            detail.start_time = started_at
                            detail.end_time = ended_at
                            detail.latency_ms = getattr(result, "latency_ms", 0.0) if result else 0.0
                            detail.status = "completed" if getattr(result, "success", False) else "failed"
                            detail.error = getattr(result, "error", None) if result else "Unknown error"
                            # Store FULL output for visualization (no truncation - users need to see complete expert responses)
                            # Extract output from ExpertResult - preserve empty strings as they may be valid responses
                            if result:
                                output = getattr(result, "output", None)
                                # Convert None to empty string, but preserve actual empty strings
                                if output is None:
                                    detail.response = ""
                                else:
                                    detail.response = str(output)  # Ensure it's a string
                            else:
                                detail.response = ""
                            # Extract tools if available
                            if hasattr(result, 'tools_used'):
                                detail.tools_used = result.tools_used
                            break

            # 5. Mix results
            perf_monitor.record_mixing_start(perf_context)
            trace.mixing_start = time.time()
            final_result = await self._mixer.mix(
                expert_results,
                selected_expert_ids,
                query
            )
            trace.mixing_end = time.time()
            perf_monitor.record_mixing_end(perf_context, final_result)
            # Extract content from MixedResult for trace (full content for visualization)
            if final_result and hasattr(final_result, 'content') and final_result.content:
                trace.final_response = str(final_result.content)
            else:
                trace.final_response = None

            # 6. Build result with trace
            result = self._build_result(
                final_result,
                selected_expert_ids,
                expert_results,
                start_time,
                request_id,
                trace
            )

            # 7. Cache
            if self._cache and self._config.cache.enabled:
                await self._cache.store(query, result)

            # 8. Finish performance monitoring
            perf_monitor.finish_request(perf_context, cache_hit=cache_hit)

            return result

        except Exception as e:
            # Fallback to default agent
            result = await self._handle_fallback(query, session_id, e, trace, start_time)
            perf_monitor.finish_request(perf_context, cache_hit=False)
            return result

    async def _execute_fast_path(
        self,
        agent_id: str,
        query: str,
        session_id: Optional[str],
        start_time: float,
        request_id: str,
        trace: MoETrace
    ) -> MoEResult:
        """
        Execute query via fast-path (direct to single agent).

        Bypasses:
        - Expert selection
        - Multi-agent parallel execution
        - Result synthesis

        Args:
            agent_id: Target agent ID (e.g., "chitchat")
            query: User query
            session_id: Session ID
            start_time: Request start time
            request_id: Request ID
            trace: Trace object to update

        Returns:
            MoEResult with fast-path flag set
        """
        import time

        try:
            # Get agent with session
            agent, session = await self._factory.get_agent_with_persistent_session(agent_id, session_id)

            # Update trace - mark as fast-path
            trace.selected_experts = [agent_id]
            trace.expert_details = [
                ExpertExecutionDetail(
                    expert_id=agent_id,
                    agent_name=getattr(agent, 'name', agent_id),
                    confidence=1.0,
                    status="executing",
                    start_time=time.time()
                )
            ]

            # Execute directly (no parallelism needed)
            from agents import Runner
            result = await Runner.run(
                starting_agent=agent,
                input=query,
                session=session
            )

            # Update trace
            trace.expert_details[0].status = "completed"
            trace.expert_details[0].end_time = time.time()
            trace.expert_details[0].latency_ms = (
                trace.expert_details[0].end_time - trace.expert_details[0].start_time
            ) * 1000
            trace.expert_details[0].response = str(result.final_output)

            # Build result
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            trace.latency_ms = latency_ms

            logger.info(
                f"[MoE] Fast-path completed in {latency_ms:.0f}ms "
                f"(bypassed selection + synthesis)"
            )

            return MoEResult(
                response=str(result.final_output),
                experts_used=[agent_id],
                trace=trace
            )

        except Exception as e:
            logger.error(f"Fast-path execution failed: {e}")
            # Fall back to regular pipeline
            trace.error = f"Fast-path failed: {e}"
            return await self._handle_fallback(query, session_id, e, trace, start_time)

    async def _handle_fallback(
        self,
        query: str,
        session_id: Optional[str],
        error: Exception,
        trace: MoETrace,
        start_time: Optional[float] = None
    ) -> MoEResult:
        """
        Fallback to default agent on error.

        Args:
            query: Original query
            session_id: Session ID
            error: Original error
            trace: Existing trace to update

        Returns:
            MoEResult with fallback response
        """
        fallback_agent_id = self._config.error_handling.get("fallback_agent", "one")

        # Update trace with error info
        trace.fallback = True
        trace.error = str(error)

        # Calculate latency from start_time to now
        # Use start_time if provided, otherwise fall back to selection_start
        if start_time is not None:
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        elif trace.selection_start:
            latency_ms = (asyncio.get_event_loop().time() - trace.selection_start) * 1000
        else:
            # If neither is available, use a minimal latency
            latency_ms = 0.0
        trace.latency_ms = latency_ms

        try:
            agent, session = await self._factory.get_agent_with_persistent_session(
                fallback_agent_id, session_id
            )

            from agents import Runner
            result = await Runner.run(
                starting_agent=agent,
                input=query,
                session=session
            )

            # Update latency to include fallback execution time
            if start_time is not None:
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            elif trace.selection_start:
                latency_ms = (asyncio.get_event_loop().time() - trace.selection_start) * 1000
            else:
                latency_ms = 0.0
            trace.latency_ms = latency_ms

            # Post-process: if user asked for a map, ensure we include an interactive_map block
            # even on fallback responses (common when MapAgent/Yelp tools fail or time out).
            try:
                from asdrp.orchestration.moe.map_injector import MapInjector
                injected = MapInjector().inject_if_needed(query=query, answer=str(result.final_output))
            except Exception:
                injected = str(result.final_output)

            return MoEResult(
                response=injected,
                experts_used=[fallback_agent_id],
                trace=trace
            )
        except Exception as fallback_error:
            # Last resort - return error message
            fallback_message = self._config.error_handling.get(
                "fallback_message",
                "I apologize, but I encountered an issue processing your request."
            )

            trace.error = f"Fallback also failed: {str(fallback_error)}"
            # Update latency even on final failure
            if start_time is not None:
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            elif trace.selection_start:
                latency_ms = (asyncio.get_event_loop().time() - trace.selection_start) * 1000
            else:
                latency_ms = 0.0
            trace.latency_ms = latency_ms

            return MoEResult(
                response=fallback_message,
                experts_used=[],
                trace=trace
            )

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return f"moe-{uuid.uuid4().hex[:12]}"

    def _build_result(
        self,
        final_result: Any,
        expert_ids: List[str],
        expert_results: List[Any],
        start_time: float,
        request_id: str,
        trace: MoETrace
    ) -> MoEResult:
        """Build MoEResult with complete trace."""
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        trace.latency_ms = latency_ms

        # Defensive: ensure final_result has content attribute
        if final_result is None:
            logger.error("final_result is None in _build_result")
            response_content = "I apologize, but I encountered an issue processing your request."
        elif not hasattr(final_result, 'content'):
            logger.error(f"final_result missing 'content' attribute: {type(final_result)}")
            response_content = "I apologize, but I encountered an issue processing your request."
        elif final_result.content is None:
            logger.error("final_result.content is None")
            response_content = "I apologize, but I encountered an issue processing your request."
        else:
            response_content = final_result.content

        return MoEResult(
            response=response_content,
            experts_used=expert_ids,
            trace=trace
        )

    def _build_cached_result(
        self,
        cached: dict,
        start_time: float,
        request_id: str,
        trace: MoETrace
    ) -> MoEResult:
        """Build MoEResult for cache hit."""
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        trace.latency_ms = latency_ms
        trace.cache_hit = True
        trace.fallback = False

        # Cache entries currently persist only (response, experts_used).
        # To keep the frontend MoE visualization useful on cache hits, we populate
        # selected_experts + expert_details from experts_used.
        experts_used = cached.get("experts_used", []) or []
        if isinstance(experts_used, list):
            trace.selected_experts = experts_used
            try:
                # Import here to avoid import-time cycles.
                details = []
                for expert_id in experts_used:
                    details.append(
                        ExpertExecutionDetail(
                            expert_id=str(expert_id),
                            agent_name=str(expert_id),
                            confidence=1.0,
                            status="completed",
                        )
                    )
                trace.expert_details = details
            except Exception:
                trace.expert_details = None

        # Post-process cached response with the current map-injection behavior (cache entries can be stale).
        # This ensures that "map" queries rendered from cache still include an interactive_map block.
        resp = cached.get("response", "") or ""
        try:
            from asdrp.orchestration.moe.map_injector import MapInjector
            resp = MapInjector().inject_if_needed(query=trace.query, answer=str(resp))
        except Exception:
            resp = str(resp)

        # Populate final_response for visualization (full content needed for UI)
        trace.final_response = resp if resp else None

        return MoEResult(
            response=resp,
            experts_used=experts_used,
            trace=trace
        )

    @classmethod
    def create_default(
        cls,
        agent_factory: AgentFactory,
        config: MoEConfig
    ) -> "MoEOrchestrator":
        """
        Create orchestrator with default components.

        Args:
            agent_factory: Existing AgentFactory instance
            config: MoE configuration

        Returns:
            Configured MoEOrchestrator
            
        Raises:
            ConfigException: If configuration validation fails
        """
        from asdrp.orchestration.moe.expert_executor import ParallelExecutor
        from asdrp.orchestration.moe.result_mixer import WeightedMixer
        from asdrp.orchestration.moe.cache import SemanticCache
        from asdrp.orchestration.moe.exceptions import ConfigException

        # Validate configuration at startup
        cls._validate_startup_configuration(config, agent_factory)

        # Choose selector based on config
        selection_strategy = config.moe.get("selection_strategy", "capability_match")

        if selection_strategy == "semantic":
            from asdrp.orchestration.moe.semantic_selector import SemanticSelector
            try:
                selector = SemanticSelector(config)
                logger.info("Using SemanticSelector for expert selection")
            except Exception as e:
                # Fail open: if embeddings cannot be initialized (missing env / offline),
                # fall back to deterministic capability selection so MoE still returns results.
                from asdrp.orchestration.moe.expert_selector import CapabilityBasedSelector
                selector = CapabilityBasedSelector(config)
                logger.warning(f"SemanticSelector unavailable ({e}); falling back to CapabilityBasedSelector")
        else:
            from asdrp.orchestration.moe.expert_selector import CapabilityBasedSelector
            selector = CapabilityBasedSelector(config)
            logger.info("Using CapabilityBasedSelector for expert selection")

        executor = ParallelExecutor(config)
        mixer = WeightedMixer(config)
        cache = SemanticCache(config) if config.cache.enabled else None

        # Enable fast-path for chitchat/simple queries (if configured)
        fast_path_enabled = config.moe.get("fast_path_enabled", True)
        fast_path = None
        if fast_path_enabled:
            try:
                fast_path_threshold = config.moe.get("fast_path_threshold", 0.75)
                fast_path = FastPathDetector(similarity_threshold=fast_path_threshold)
                logger.info(f"Fast-path enabled (threshold={fast_path_threshold})")
            except Exception as e:
                logger.warning(f"Fast-path initialization failed: {e}. Continuing without fast-path.")

        return cls(
            agent_factory=agent_factory,
            expert_selector=selector,
            expert_executor=executor,
            result_mixer=mixer,
            config=config,
            cache=cache,
            fast_path_detector=fast_path
        )

    @staticmethod
    def _validate_startup_configuration(config: MoEConfig, agent_factory: AgentFactory) -> None:
        """
        Validate configuration at startup to prevent runtime errors.
        
        Args:
            config: MoE configuration to validate
            agent_factory: Agent factory to check agent availability
            
        Raises:
            ConfigException: If configuration is invalid
        """
        from asdrp.orchestration.moe.exceptions import ConfigException
        
        logger.info("[MoE] Validating configuration at startup...")
        
        # 1. Validate agent existence
        try:
            # Get list of available agents from factory
            available_agents = []
            try:
                # Try to get available agents from factory
                if hasattr(agent_factory, 'get_available_agents'):
                    available_agents = agent_factory.get_available_agents()
                elif hasattr(agent_factory, '_agents'):
                    available_agents = list(agent_factory._agents.keys())
                else:
                    # Fallback: assume common agents are available
                    available_agents = ["yelp", "yelp_mcp", "map", "geo", "one", "chitchat", "wiki", "perplexity", "finance"]
                    logger.warning("[MoE] Could not determine available agents from factory, using default list")
            except Exception as e:
                logger.warning(f"[MoE] Could not get available agents: {e}, skipping agent validation")
                available_agents = []
            
            if available_agents:
                # Validate that all expert agents exist
                available_set = set(available_agents)
                missing_agents = []
                for expert_name, expert_config in config.experts.items():
                    for agent_id in expert_config.agents:
                        if agent_id not in available_set:
                            missing_agents.append((expert_name, agent_id))
                
                if missing_agents:
                    # Log warnings but don't fail startup - agents might be loaded later
                    for expert_name, agent_id in missing_agents:
                        logger.warning(
                            f"[MoE] Expert '{expert_name}' references agent '{agent_id}' which may not be available. "
                            f"Available agents: {sorted(available_agents)}. "
                            f"This may cause runtime errors if the agent is actually missing."
                        )
                else:
                    logger.info(f"[MoE] ✓ All expert agents validated against {len(available_agents)} available agents")
        except ConfigException:
            raise
        except Exception as e:
            logger.warning(f"[MoE] Agent validation failed with unexpected error: {e}")
        
        # 2. Validate synthesis prompt template for required variables
        if config.moe.get("mixing_strategy") == "synthesis":
            synthesis_prompt = config.moe.get("synthesis_prompt", "")
            if synthesis_prompt:
                required_vars = ["{weighted_results}", "{query}"]
                missing_vars = [var for var in required_vars if var not in synthesis_prompt]
                if missing_vars:
                    error_msg = (
                        f"Synthesis prompt template missing required variables: {missing_vars}. "
                        f"The synthesis prompt must include {{weighted_results}} and {{query}} placeholders. "
                        f"Current prompt: '{synthesis_prompt}'"
                    )
                    logger.error(f"[MoE] Configuration validation failed: {error_msg}")
                    raise ConfigException(error_msg)
                
                logger.info("[MoE] ✓ Synthesis prompt template validated")
        
        # 3. Validate fallback agent exists
        fallback_agent = config.error_handling.get("fallback_agent")
        if fallback_agent and available_agents and fallback_agent not in available_agents:
            error_msg = (
                f"Fallback agent '{fallback_agent}' not found in available agents: {sorted(available_agents)}. "
                f"Please ensure the fallback agent exists in config/open_agents.yaml or update "
                f"the fallback_agent setting in config/moe.yaml"
            )
            logger.error(f"[MoE] Configuration validation failed: {error_msg}")
            raise ConfigException(error_msg)
        
        if fallback_agent:
            logger.info(f"[MoE] ✓ Fallback agent '{fallback_agent}' validated")
        
        # 4. Validate model configurations have required fields
        required_models = ["selection", "mixing"]
        for model_name in required_models:
            if model_name not in config.models:
                error_msg = (
                    f"Missing required model configuration: '{model_name}'. "
                    f"Please ensure both 'selection' and 'mixing' models are defined in config/moe.yaml"
                )
                logger.error(f"[MoE] Configuration validation failed: {error_msg}")
                raise ConfigException(error_msg)
            
            model_config = config.models[model_name]
            if not model_config.name:
                error_msg = (
                    f"Model '{model_name}' missing required 'name' field. "
                    f"Please specify a valid model name (e.g., 'gpt-4.1-mini') in config/moe.yaml"
                )
                logger.error(f"[MoE] Configuration validation failed: {error_msg}")
                raise ConfigException(error_msg)
        
        logger.info("[MoE] ✓ Model configurations validated")
        
        # 5. Validate expert group configurations
        if not config.experts:
            error_msg = (
                "No expert groups defined. At least one expert group must be configured. "
                "Please add expert groups to the 'experts' section in config/moe.yaml"
            )
            logger.error(f"[MoE] Configuration validation failed: {error_msg}")
            raise ConfigException(error_msg)
        
        for expert_name, expert_config in config.experts.items():
            if not expert_config.agents:
                error_msg = (
                    f"Expert group '{expert_name}' has no agents defined. "
                    f"Each expert group must have at least one agent."
                )
                logger.error(f"[MoE] Configuration validation failed: {error_msg}")
                raise ConfigException(error_msg)
            
            if not expert_config.capabilities:
                error_msg = (
                    f"Expert group '{expert_name}' has no capabilities defined. "
                    f"Each expert group must have at least one capability."
                )
                logger.error(f"[MoE] Configuration validation failed: {error_msg}")
                raise ConfigException(error_msg)
        
        logger.info(f"[MoE] ✓ All {len(config.experts)} expert groups validated")
        
        logger.info("[MoE] ✅ Configuration validation completed successfully")
