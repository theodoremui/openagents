"""
SmartRouter - Advanced Multi-Agent Orchestrator

Main orchestrator class that coordinates all SmartRouter components to
interpret, decompose, route, execute, synthesize, and evaluate complex queries.

Design Principles:
-----------------
- Single Responsibility: Orchestrates component interactions
- Dependency Injection: All components injected for testability
- Open/Closed: Easy to extend with new components/strategies
- Robustness: Comprehensive error handling and fallback

Orchestration Flow:
------------------
1. QueryInterpreter: Analyze and classify query
2. QueryDecomposer: Break into subqueries (if complex)
3. CapabilityRouter: Route subqueries to agents
4. AsyncSubqueryDispatcher: Execute subqueries concurrently
5. ResponseAggregator: Collect and organize responses
6. ResultSynthesizer: Merge responses into coherent answer
7. LLMJudge: Evaluate quality and decide fallback

Usage:
------
>>> config_loader = SmartRouterConfigLoader()
>>> config = config_loader.load_config()
>>> agent_factory = AgentFactory.instance()
>>>
>>> router = SmartRouter(config, agent_factory)
>>> result = await router.route_query("Complex query here")
>>> print(result)
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
import time
from pathlib import Path

from asdrp.orchestration.smartrouter.config_loader import SmartRouterConfig, SmartRouterConfigLoader

# Import session memory types from openai-agents SDK
try:
    from agents import SQLiteSession
    SESSION_MEMORY_AVAILABLE = True
except ImportError:
    SESSION_MEMORY_AVAILABLE = False
    SQLiteSession = None
from asdrp.orchestration.smartrouter.interfaces import (
    QueryIntent,
    Subquery,
    AgentResponse,
    SynthesizedResult,
    EvaluationResult,
    QueryComplexity,
)
from asdrp.orchestration.smartrouter.exceptions import SmartRouterException
from asdrp.orchestration.smartrouter.query_interpreter import QueryInterpreter
from asdrp.orchestration.smartrouter.query_decomposer import QueryDecomposer
from asdrp.orchestration.smartrouter.capability_router import CapabilityRouter
from asdrp.orchestration.smartrouter.async_subquery_dispatcher import AsyncSubqueryDispatcher
from asdrp.orchestration.smartrouter.response_aggregator import ResponseAggregator
from asdrp.orchestration.smartrouter.result_synthesizer import ResultSynthesizer
from asdrp.orchestration.smartrouter.llm_judge import LLMJudge
from asdrp.orchestration.smartrouter.fast_path_router import FastPathRouter
from asdrp.orchestration.smartrouter.trace_capture import (
    TraceCapture,
    SmartRouterExecutionResult,
)

logger = logging.getLogger(__name__)


class SmartRouter:
    """
    Advanced multi-agent orchestrator using LLM-based routing and synthesis.

    Coordinates multiple specialist agents to answer complex queries by:
    1. Understanding query intent and complexity
    2. Breaking down complex queries into subqueries
    3. Routing subqueries to appropriate agents
    4. Executing subqueries concurrently
    5. Synthesizing responses into coherent answers
    6. Evaluating answer quality

    The SmartRouter follows SOLID principles with dependency injection,
    making it highly testable and extensible.

    Attributes:
        config: SmartRouter configuration
        agent_factory: Factory for creating agents
        interpreter: Query interpretation component
        decomposer: Query decomposition component
        router: Capability-based routing component
        dispatcher: Asynchronous subquery execution component
        aggregator: Response collection component
        synthesizer: Response merging component
        judge: Answer quality evaluation component

    Usage:
    ------
    >>> router = SmartRouter.create(agent_factory)
    >>> result = await router.route_query("What's the weather in Paris and stock price of AAPL?")
    >>> print(result)
    """

    def __init__(
        self,
        config: SmartRouterConfig,
        agent_factory: Any,  # AgentFactory
        interpreter: Optional[QueryInterpreter] = None,
        decomposer: Optional[QueryDecomposer] = None,
        capability_router: Optional[CapabilityRouter] = None,
        dispatcher: Optional[AsyncSubqueryDispatcher] = None,
        aggregator: Optional[ResponseAggregator] = None,
        synthesizer: Optional[ResultSynthesizer] = None,
        judge: Optional[LLMJudge] = None,
        session_id: Optional[str] = None,
        enable_session_memory: bool = False,
        session_db_path: Optional[str] = None
    ):
        """
        Initialize SmartRouter with configuration and components.

        Args:
            config: SmartRouter configuration
            agent_factory: Agent factory instance
            interpreter: Optional custom QueryInterpreter
            decomposer: Optional custom QueryDecomposer
            capability_router: Optional custom CapabilityRouter
            dispatcher: Optional custom AsyncSubqueryDispatcher
            aggregator: Optional custom ResponseAggregator
            synthesizer: Optional custom ResultSynthesizer
            judge: Optional custom LLMJudge
            session_id: Optional session ID for stateful routing
            enable_session_memory: Whether to enable persistent session memory
            session_db_path: Optional path to SQLite database for session storage
        """
        self.config = config
        self.agent_factory = agent_factory
        self.session_id = session_id
        self.enable_session_memory = enable_session_memory
        self.session_db_path = session_db_path
        
        # Create session if session memory is enabled
        self.session = None
        if enable_session_memory and SESSION_MEMORY_AVAILABLE:
            if session_db_path:
                # File-based persistent session
                db_path = Path(session_db_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self.session = SQLiteSession(
                    session_id=session_id or "smartrouter_session",
                    db_path=str(db_path)
                )
            else:
                # In-memory session
                self.session = SQLiteSession(
                    session_id=session_id or "smartrouter_session"
                )
        elif enable_session_memory and not SESSION_MEMORY_AVAILABLE:
            logger.warning(
                "Session memory requested but not available. "
                "Install openai-agents SDK with session support."
            )
        
        # AgentProtocol compliance: name and instructions attributes
        self.name = "SmartRouter"
        self.instructions = "You are SmartRouter - an advanced multi-agent orchestrator that intelligently routes complex queries to specialized agents."

        # Initialize components (use provided or create default)
        # Pass session_id to all LLM components for conversation memory
        self.interpreter = interpreter or QueryInterpreter(
            model_config=config.models.interpretation,
            session_id=session_id
        )

        self.decomposer = decomposer or QueryDecomposer(
            model_config=config.models.decomposition,
            decomp_config=config.decomposition,
            session_id=session_id
        )

        self.router = capability_router or CapabilityRouter(
            capability_map=config.capabilities
        )

        self.dispatcher = dispatcher or AsyncSubqueryDispatcher(
            agent_factory=agent_factory,
            error_config=config.error_handling,
            session_id=session_id,
            session=self.session  # Pass SmartRouter's session if available
        )

        self.aggregator = aggregator or ResponseAggregator()

        self.synthesizer = synthesizer or ResultSynthesizer(
            model_config=config.models.synthesis,
            session_id=session_id
        )

        self.judge = judge or LLMJudge(
            model_config=config.models.evaluation,
            eval_config=config.evaluation,
            session_id=session_id
        )

        # Fast-path router for pre-classification (no LLM)
        self.fast_path_router = FastPathRouter(enable_logging=True)

        logger.info(
            f"SmartRouter initialized with {len(config.capabilities)} agents, "
            f"session_id={session_id}"
        )

    @classmethod
    def create(
        cls,
        agent_factory: Any,
        config_path: Optional[str] = None,
        session_id: Optional[str] = None,
        enable_session_memory: bool = False,
        session_db_path: Optional[str] = None
    ) -> "SmartRouter":
        """
        Factory method to create SmartRouter with default configuration.

        Args:
            agent_factory: Agent factory instance
            config_path: Optional path to smartrouter.yaml
            session_id: Optional session ID
            enable_session_memory: Whether to enable persistent session memory
            session_db_path: Optional path to SQLite database for session storage

        Returns:
            SmartRouter instance

        Raises:
            SmartRouterException: If configuration is invalid

        Examples:
        ---------
        >>> from asdrp.agents.agent_factory import AgentFactory
        >>> factory = AgentFactory.instance()
        >>> router = SmartRouter.create(factory)
        >>> 
        >>> # With session memory
        >>> router = SmartRouter.create(
        ...     factory,
        ...     session_id="user_123",
        ...     enable_session_memory=True,
        ...     session_db_path="./sessions/smartrouter.db"
        ... )
        """
        config_loader = SmartRouterConfigLoader(config_path=config_path)
        config = config_loader.load_config()

        if not config.enabled:
            raise SmartRouterException(
                "SmartRouter is disabled in configuration",
                context={"enabled": False}
            )

        return cls(
            config, 
            agent_factory, 
            session_id=session_id,
            enable_session_memory=enable_session_memory,
            session_db_path=session_db_path
        )

    async def route_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SmartRouterExecutionResult:
        """
        Main entry point: Route and execute a complex query with trace capture.

        Orchestrates the full SmartRouter pipeline:
        1. Interpret query
        2. Decompose if complex
        3. Route to agents
        4. Execute subqueries
        5. Synthesize responses
        6. Evaluate quality
        7. Return answer with execution traces

        Args:
            query: User query text
            context: Optional additional context

        Returns:
            SmartRouterExecutionResult with answer and execution traces

        Raises:
            SmartRouterException: If routing fails critically

        Examples:
        ---------
        >>> result = await router.route_query("What's the weather in Paris?")
        >>> print(result.answer)
        The weather in Paris is currently...
        >>> print(result.agents_used)
        ['one']
        """
        # Initialize trace capture
        trace_capture = TraceCapture()
        agents_used: List[str] = []
        original_answer: Optional[str] = None  # Initialize to avoid UnboundLocalError

        try:
            logger.info(f"SmartRouter processing query: {query[:100]}...")

            # Step 0: Try fast-path FIRST (keyword-based pre-classification)
            with trace_capture.phase("fast_path"):
                fast_path_intent = self.fast_path_router.try_fast_path(query)

                if fast_path_intent:
                    # Fast-path hit: skip LLM interpretation
                    logger.info(
                        f"Fast-path match: pattern={fast_path_intent.metadata['fast_path_pattern']}, "
                        f"domains={fast_path_intent.domains}"
                    )
                    trace_capture.record_data({
                        "matched": True,
                        "pattern": fast_path_intent.metadata["fast_path_pattern"],
                        "confidence": fast_path_intent.metadata["fast_path_confidence"],
                        "domains": fast_path_intent.domains,
                    })

                    # Route directly with fast-path intent (skip interpretation + evaluation)
                    answer, agent_id = await self._handle_simple_query_with_trace(
                        fast_path_intent, trace_capture
                    )
                    agents_used.append(agent_id)

                    # Determine final decision: chitchat if conversation/social domains, otherwise fast_path
                    is_chitchat = "conversation" in fast_path_intent.domains or "social" in fast_path_intent.domains
                    final_decision = "chitchat" if is_chitchat else "fast_path"

                    # Skip evaluation for chitchat (always acceptable)
                    logger.info(f"Fast-path query complete, skipping quality evaluation (decision: {final_decision})")

                    total_time = trace_capture.get_total_time()
                    return SmartRouterExecutionResult(
                        answer=answer,
                        traces=trace_capture.get_traces(),
                        total_time=total_time,
                        final_decision=final_decision,
                        agents_used=agents_used,
                        success=True,
                        original_answer=None,
                    )
                else:
                    # No fast-path match, fall through to standard pipeline
                    logger.debug("No fast-path match, using standard LLM interpretation")
                    trace_capture.record_data({
                        "matched": False,
                        "fallthrough": True,
                    })

            # Step 1: Interpret query (TRACE)
            with trace_capture.phase("interpretation"):
                intent = await self.interpreter.interpret(query)
                trace_capture.record_data({
                    "intent": {
                        "complexity": intent.complexity.value,
                        "domains": intent.domains,
                        "requires_synthesis": intent.requires_synthesis,
                    }
                })
            logger.debug(f"Query intent: {intent.complexity.value}, domains={intent.domains}")

            # Check if this is a chitchat/social query
            is_chitchat = "conversation" in intent.domains or "social" in intent.domains

            # Step 2: Handle based on complexity
            if intent.complexity == QueryComplexity.SIMPLE:
                # Simple query: route directly to single agent (TRACE)
                answer, agent_id = await self._handle_simple_query_with_trace(intent, trace_capture)
                agents_used.append(agent_id)
            else:
                # Complex query: full orchestration pipeline (TRACE)
                answer = await self._handle_complex_query_with_trace(intent, trace_capture, agents_used)

            # Step 3: Evaluate answer quality (skip for chitchat - always friendly and positive)
            if is_chitchat:
                logger.info("Skipping quality evaluation for chitchat query (always acceptable)")
                final_decision = "chitchat"
                original_answer = None  # No fallback needed for chitchat
            else:
                with trace_capture.phase("evaluation"):
                    evaluation = await self.judge.evaluate(answer, query)
                    trace_capture.record_data({
                        "passed": not evaluation.should_fallback,
                        "is_high_quality": evaluation.is_high_quality,
                        "issues": evaluation.issues if evaluation.should_fallback else [],
                        "scores": {
                            "completeness": evaluation.completeness_score,
                            "accuracy": evaluation.accuracy_score,
                            "clarity": evaluation.clarity_score,
                        },
                        "overall_passed": evaluation.completeness_score >= self.config.evaluation.quality_threshold
                            and evaluation.accuracy_score >= self.config.evaluation.quality_threshold
                            and evaluation.clarity_score >= self.config.evaluation.quality_threshold,
                        "threshold": self.config.evaluation.quality_threshold,
                    })

                # Step 4: Return answer or fallback
                original_answer = answer  # Preserve original answer before potential fallback
                if evaluation.should_fallback:
                    logger.warning(
                        f"Answer quality below threshold, using fallback. "
                        f"Issues: {evaluation.issues}"
                    )
                    answer = self.config.evaluation.fallback_message
                    final_decision = "fallback"
                else:
                    final_decision = "synthesized" if len(agents_used) > 1 else "direct"
                    original_answer = None  # No need to store original if not using fallback

            total_time = trace_capture.get_total_time()
            logger.info(f"SmartRouter query completed in {total_time:.2f}s")

            return SmartRouterExecutionResult(
                answer=answer,
                traces=trace_capture.get_traces(),
                total_time=total_time,
                final_decision=final_decision,
                agents_used=agents_used,
                success=True,
                original_answer=original_answer,
            )

        except SmartRouterException as e:
            logger.error(f"SmartRouter error: {e.message}", exc_info=True)
            return SmartRouterExecutionResult(
                answer=self.config.evaluation.fallback_message,
                traces=trace_capture.get_traces(),
                total_time=trace_capture.get_total_time(),
                final_decision="error",
                agents_used=agents_used,
                success=False,
                original_answer=original_answer,
            )
        except Exception as e:
            logger.error(f"Unexpected error in SmartRouter: {str(e)}", exc_info=True)
            return SmartRouterExecutionResult(
                answer=self.config.evaluation.fallback_message,
                traces=trace_capture.get_traces(),
                total_time=trace_capture.get_total_time(),
                final_decision="error",
                agents_used=agents_used,
                success=False,
                original_answer=original_answer,
            )

    async def _handle_simple_query_with_trace(
        self,
        intent: QueryIntent,
        trace_capture: TraceCapture
    ) -> Tuple[str, str]:
        """
        Handle simple query with direct agent routing and trace capture.

        For simple queries, we route directly to a single agent without
        decomposition or synthesis.

        Special handling for chitchat/social queries: Routes to chitchat agent
        for fast, friendly responses.

        Uses domain prioritization to select the best capability when multiple
        domains are present (e.g., prefer "local_business" over "search" for
        restaurant queries).

        Args:
            intent: Query intent
            trace_capture: TraceCapture instance for recording execution

        Returns:
            Tuple of (answer, agent_id)

        Raises:
            SmartRouterException: If routing fails
        """
        logger.debug("Handling simple query with direct routing")

        # Domain prioritization map - higher values = higher priority
        # Real-time informational queries have HIGH priority to prevent chitchat misrouting
        DOMAIN_PRIORITY = {
            "weather": 12,           # Weather queries - HIGHEST (must not be chitchat)
            "news": 12,              # News queries - HIGHEST (must not be chitchat)
            "current_events": 12,    # Current events - HIGHEST
            "local_business": 10,    # Yelp for restaurants/shops - highest accuracy
            "finance": 9,            # Finance agent for stocks/markets
            "geography": 8,          # Geo agent for coordinates/addresses (domain -> capability: geocoding)
            "geocoding": 8,          # Direct capability name for geo agent
            "mapping": 7,            # Map agent for directions/routes
            "research": 6,           # Perplexity for deep research
            "wikipedia": 5,          # Wiki for encyclopedia knowledge
            "conversation": 3,       # Chitchat for social interactions (LOWER priority)
            "social": 3,             # Social queries (LOWER priority)
            "search": 4,             # Generic web search (above chitchat)
            "web_search": 4,         # Web search capability
            "realtime": 11,          # Real-time info (high priority)
        }

        # Domain to capability mapping
        # Maps QueryInterpreter domains to agent capabilities
        DOMAIN_TO_CAPABILITY = {
            "geography": "geocoding",           # GeoAgent: address ↔ coordinates
            "mapping": "mapping",               # MapAgent: directions, routes, maps
            "finance": "finance",               # FinanceAgent: stocks, markets
            "local_business": "local_business", # YelpAgent: restaurants, reviews
            "research": "research",             # PerplexityAgent: deep research
            "wikipedia": "wikipedia",           # WikiAgent: encyclopedia
            "conversation": "conversation",     # ChitchatAgent: social
            "social": "conversation",           # ChitchatAgent: social
            "search": "search",                 # PerplexityAgent: web search
            "web_search": "search",             # Web search capability
            "weather": "weather",               # PerplexityAgent: weather
            "news": "news",                     # PerplexityAgent: news
            "current_events": "current_events", # PerplexityAgent: current events
            "realtime": "realtime",             # PerplexityAgent: real-time info
            "geocoding": "geocoding",           # Direct capability (backward compat)
        }

        # Determine primary domain/capability using prioritization
        if intent.domains:
            # Select domain with highest priority
            primary_domain = max(
                intent.domains,
                key=lambda d: DOMAIN_PRIORITY.get(d, 0)
            )
            # Map domain to capability
            primary_capability = DOMAIN_TO_CAPABILITY.get(primary_domain, primary_domain)
            logger.debug(
                f"Selected primary domain '{primary_domain}' → capability '{primary_capability}' "
                f"(priority {DOMAIN_PRIORITY.get(primary_domain, 0)}) "
                f"from domains {intent.domains}"
            )
        else:
            primary_capability = "search"
            logger.debug("No domains specified, defaulting to 'search'")

        # Special handling for chitchat/social queries
        is_chitchat = "conversation" in intent.domains or "social" in intent.domains
        if is_chitchat:
            logger.info("Detected chitchat/social query - routing to chitchat agent")
            primary_capability = "conversation"
            # Try to route to chitchat agent first
            if self.router.can_route(primary_capability):
                candidates = self.router._find_candidate_agents(primary_capability)
                if candidates and "chitchat" in candidates:
                    agent_id = "chitchat"
                    logger.info(f"Routing chitchat query to ChitchatAgent for fast response")
                else:
                    # Fallback to first candidate if chitchat not found
                    agent_id = candidates[0] if candidates else None
            else:
                agent_id = None
        else:
            # Try to route primary capability
            if not self.router.can_route(primary_capability):
                logger.warning(
                    f"Cannot route primary capability '{primary_capability}', "
                    f"trying alternative domains"
                )

                # Try other domains from intent (sorted by priority)
                agent_id = None
                for domain in sorted(
                    intent.domains,
                    key=lambda d: DOMAIN_PRIORITY.get(d, 0),
                    reverse=True
                ):
                    # Map domain to capability
                    capability = DOMAIN_TO_CAPABILITY.get(domain, domain)
                    if capability != primary_capability and self.router.can_route(capability):
                        logger.info(
                            f"Found alternative routable domain: '{domain}' → capability '{capability}' "
                            f"(priority {DOMAIN_PRIORITY.get(domain, 0)})"
                        )
                        primary_capability = capability
                        candidates = self.router._find_candidate_agents(primary_capability)
                        agent_id = candidates[0] if candidates else None
                        break

                # Only fall back to search if NO domain works
                if not agent_id:
                    logger.warning("No domains routable, falling back to 'search'")
                    primary_capability = "search"
                    candidates = self.router._find_candidate_agents(primary_capability)
                    agent_id = candidates[0] if candidates else None
            else:
                # Primary capability is routable
                candidates = self.router._find_candidate_agents(primary_capability)
                agent_id = candidates[0] if candidates else None

        if not agent_id:
            raise SmartRouterException(
                f"No agent available for capability '{primary_capability}'",
                context={"capability": primary_capability, "query": intent.original_query}
            )

        # Routing phase (TRACE)
        with trace_capture.phase("routing"):
            trace_capture.record_data({
                "pattern": "SIMPLE",
                "agent": agent_id,
                "domains": intent.domains,
            })

        # Execute query directly on agent
        logger.info(f"Routing simple query to agent '{agent_id}'")

        import time
        execution_start = time.time()

        with trace_capture.phase("execution"):
            # Use SmartRouter's session if available, otherwise use agent factory session
            if self.session is not None:
                # SmartRouter has its own session - use it for all agents
                agent = await self.agent_factory.get_agent(agent_id)
                session = self.session
                logger.debug(
                    f"Using SmartRouter session for agent '{agent_id}' "
                    "(enables cross-agent context sharing)"
                )
            elif self.session_id:
                agent, session = await self.agent_factory.get_agent_with_session(
                    agent_id,
                    session_id=self.session_id  # ✅ Shared session for cross-agent context
                )
                logger.debug(
                    f"Using shared session '{self.session_id}' for agent '{agent_id}' "
                    "(enables cross-agent context sharing)"
                )
            else:
                agent = await self.agent_factory.get_agent(agent_id)
                session = None

            from agents import Runner
            result = await Runner.run(
                starting_agent=agent,
                input=intent.original_query,
                session=session
            )

            execution_end = time.time()
            execution_duration = execution_end - execution_start

            trace_capture.record_data({
                "agents": [agent_id],
                "success": True,
                "agent_executions": [{
                    "agent_id": agent_id,
                    "subquery_id": "direct",
                    "success": True,
                    "error": None,
                }],
                "execution_duration": execution_duration,
                "concurrent": False,  # Single agent execution
            })

        return (str(result.final_output), agent_id)

    async def _handle_simple_query(self, intent: QueryIntent) -> str:
        """
        Handle simple query with direct agent routing (legacy method).

        This method is kept for backward compatibility but internally uses
        the trace-enabled version.

        Args:
            intent: Query intent

        Returns:
            Agent response string

        Raises:
            SmartRouterException: If routing fails
        """
        trace_capture = TraceCapture()
        answer, _ = await self._handle_simple_query_with_trace(intent, trace_capture)
        return answer

    async def _handle_complex_query_with_trace(
        self,
        intent: QueryIntent,
        trace_capture: TraceCapture,
        agents_used: List[str]
    ) -> str:
        """
        Handle complex query with full orchestration pipeline and trace capture.

        Executes the complete SmartRouter workflow:
        - Decompose into subqueries
        - Route to agents
        - Execute concurrently
        - Synthesize responses

        Args:
            intent: Query intent
            trace_capture: TraceCapture instance for recording execution
            agents_used: List to populate with agents used during execution

        Returns:
            Synthesized answer string

        Raises:
            SmartRouterException: If orchestration fails
        """
        logger.debug("Handling complex query with full orchestration")

        # Step 1: Decompose query (TRACE)
        with trace_capture.phase("decomposition"):
            subqueries = await self.decomposer.decompose(intent)

            if not subqueries:
                # Decomposer returned empty - treat as simple
                logger.info("Decomposer returned no subqueries, treating as simple")
                trace_capture.record_data({
                    "subquery_count": 0,
                    "fallback_to_simple": True,
                })
                answer, agent_id = await self._handle_simple_query_with_trace(intent, trace_capture)
                agents_used.append(agent_id)
                return answer

            trace_capture.record_data({
                "subquery_count": len(subqueries),
                "subqueries": [
                    {"id": sq.id, "text": sq.text, "capability": sq.capability_required}
                    for sq in subqueries
                ],
            })
            logger.info(f"Query decomposed into {len(subqueries)} subqueries")

        # Step 2: Route subqueries to agents (TRACE)
        with trace_capture.phase("routing"):
            routed_subqueries: List[Tuple[Subquery, str]] = []
            routing_map = {}

            for subquery in subqueries:
                agent_id, routing_pattern = self.router.route(subquery)
                routed_subqueries.append((subquery, agent_id))
                routing_map[subquery.id] = agent_id

                if agent_id not in agents_used:
                    agents_used.append(agent_id)

                logger.debug(
                    f"Routed {subquery.id} ({subquery.capability_required}) "
                    f"to {agent_id} with {routing_pattern.value}"
                )

            trace_capture.record_data({
                "routing": routing_map,
                "agents_selected": agents_used,
            })

        # Step 3: Execute subqueries concurrently (TRACE)
        # Record timing for each agent to visualize parallel execution
        import time
        execution_start = time.time()

        with trace_capture.phase("execution"):
            responses = await self.dispatcher.dispatch_all(
                routed_subqueries,
                timeout=self.config.error_handling.timeout
            )

            execution_end = time.time()
            execution_duration = execution_end - execution_start

            # Build detailed agent execution info for visualization
            agent_executions = []
            for (subquery, agent_id), response in zip(routed_subqueries, responses):
                agent_executions.append({
                    "agent_id": agent_id,
                    "subquery_id": subquery.id,
                    "success": response.success,
                    "error": response.error if not response.success else None,
                })

            trace_capture.record_data({
                "response_count": len(responses),
                "agents": agents_used,
                "success": all(r.success for r in responses),
                "agent_executions": agent_executions,
                "execution_duration": execution_duration,
                "concurrent": len(agents_used) > 1,  # Flag for parallel execution
            })

        # Step 4: Aggregate responses
        aggregated = self.aggregator.aggregate(responses, subqueries)

        # Step 5: Extract successful responses
        successful = self.aggregator.extract_successful(aggregated)

        if not successful:
            logger.warning("No successful responses, using fallback")
            return self.config.evaluation.fallback_message

        # Step 6: Synthesize responses (TRACE)
        with trace_capture.phase("synthesis"):
            synthesized = await self.synthesizer.synthesize(
                successful,
                intent.original_query
            )

            trace_capture.record_data({
                "synthesized_from": len(responses),
                "confidence": synthesized.confidence,
                "sources": synthesized.sources,
            })

            logger.info(
                f"Synthesis complete: confidence={synthesized.confidence:.2f}, "
                f"sources={synthesized.sources}"
            )

        return synthesized.answer

    async def _handle_complex_query(self, intent: QueryIntent) -> str:
        """
        Handle complex query with full orchestration pipeline (legacy method).

        This method is kept for backward compatibility but internally uses
        the trace-enabled version.

        Args:
            intent: Query intent

        Returns:
            Synthesized answer string

        Raises:
            SmartRouterException: If orchestration fails
        """
        trace_capture = TraceCapture()
        agents_used: List[str] = []
        return await self._handle_complex_query_with_trace(intent, trace_capture, agents_used)

    def get_capabilities(self) -> Dict[str, List[str]]:
        """
        Get the capability map for debugging/introspection.

        Returns:
            Dictionary mapping agent_id to list of capabilities
        """
        return self.config.capabilities

    def get_config(self) -> SmartRouterConfig:
        """
        Get the SmartRouter configuration.

        Returns:
            SmartRouterConfig instance
        """
        return self.config


def create_smartrouter(
    instructions: Optional[str] = None,
    model_config: Optional[Any] = None
) -> "SmartRouter":
    """
    Factory function for creating SmartRouter instance.

    This function is called by the AgentFactory when creating a smartrouter agent
    from the open_agents.yaml configuration.

    Args:
        instructions: Optional instructions for SmartRouter (stored in instructions attribute)
        model_config: Optional model configuration (not used, SmartRouter uses smartrouter.yaml)

    Returns:
        SmartRouter instance configured from smartrouter.yaml

    Examples:
    ---------
    >>> from asdrp.agents.agent_factory import AgentFactory
    >>> factory = AgentFactory.instance()
    >>> smartrouter = factory.get_agent("smartrouter")
    """
    from asdrp.agents.agent_factory import AgentFactory

    # Get the agent factory singleton
    agent_factory = AgentFactory.instance()

    # Create SmartRouter using the factory method (loads from smartrouter.yaml)
    smartrouter = SmartRouter.create(agent_factory)
    
    # Set instructions if provided (for AgentProtocol compliance)
    if instructions:
        smartrouter.instructions = instructions

    return smartrouter
