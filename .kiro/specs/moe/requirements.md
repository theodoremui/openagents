# MoE Orchestrator Requirements Specification

**Project**: OpenAgents
**Component**: MoE (Mixture of Experts) Orchestrator
**Version**: 1.0.0
**Date**: December 13, 2024
**Status**: Final Specification - Architecture-Aligned

---

## 1. Executive Summary

The MoE (Mixture of Experts) Orchestrator is a production-grade three-tier hybrid multi-agent orchestration system for the OpenAgents platform. It follows the same protocol-based, dependency injection patterns established in the codebase.

The orchestrator integrates seamlessly with the existing:
- **Agent System**: `asdrp/agents/` (protocol.py, agent_factory.py, config_loader.py)
- **Orchestration Layer**: `asdrp/orchestration/` (NEW: home for SmartRouter and MoE)
- **API Layer**: `server/` (main.py, agent_service.py, models.py)
- **Frontend**: `frontend_web/` (service layer, API client)
- **Configuration**: `config/` (YAML-based with Pydantic validation)

### Key Objectives

- **Latency**: Achieve 1-2 second end-to-end responses (vs. 6+ seconds sequential)
- **Quality**: Improve accuracy through confidence-weighted consensus aggregation
- **Cost**: Reduce compute costs by 30-50% through intelligent agent selection
- **Interpretability**: Provide complete tracing of all orchestration decisions
- **Modularity**: Clean separation between agents (asdrp/agents/) and orchestration (asdrp/orchestration/)

---

## 2. Architecture Alignment

### 2.1 New Orchestration Layer Structure

The specification proposes moving orchestration patterns to a dedicated `asdrp/orchestration/` directory for better separation of concerns:

```
asdrp/
├── agents/                       # EXISTING: Individual agents
│   ├── protocol.py               # Agent interface
│   ├── agent_factory.py          # Agent creation
│   ├── config_loader.py          # Agent config
│   ├── single/                   # Single-purpose agents
│   │   ├── one_agent.py
│   │   ├── geo_agent.py
│   │   ├── finance_agent.py
│   │   └── ...
│   └── mcp/                      # MCP agents
│
├── orchestration/                # NEW: Orchestration patterns
│   ├── __init__.py
│   │
│   ├── smartrouter/              # MOVED: SmartRouter (from agents/router/)
│   │   ├── __init__.py
│   │   ├── smartrouter.py
│   │   ├── query_interpreter.py
│   │   ├── query_decomposer.py
│   │   ├── capability_router.py
│   │   ├── async_subquery_dispatcher.py
│   │   ├── response_aggregator.py
│   │   ├── result_synthesizer.py
│   │   ├── llm_judge.py
│   │   ├── fast_path_router.py
│   │   ├── cache.py
│   │   ├── interfaces.py
│   │   ├── config_loader.py
│   │   └── exceptions.py
│   │
│   └── moe/                      # NEW: MoE Orchestrator
│       ├── __init__.py
│       ├── orchestrator.py       # Main orchestrator
│       ├── interfaces.py         # Abstract base classes
│       ├── config_loader.py      # MoE config loader
│       ├── exceptions.py         # MoE exceptions
│       ├── expert_selector.py    # Tier 1: Expert selection
│       ├── expert_executor.py    # Tier 2: Parallel execution
│       ├── result_mixer.py       # Tier 3: Result aggregation
│       └── cache.py              # Semantic caching
│
├── actions/                      # EXISTING: Tools for agents
│   ├── tools_meta.py
│   ├── finance/
│   ├── geo/
│   └── ...
│
└── util/                         # EXISTING: Utilities

config/
├── open_agents.yaml              # EXISTING: Agent definitions
├── smartrouter.yaml              # MOVED: SmartRouter config
└── moe.yaml                      # NEW: MoE config

server/
├── main.py                       # MODIFIED: Add MoE endpoint
├── agent_service.py              # MODIFIED: Add MoE execution
└── models.py                     # MODIFIED: Add MoE DTOs

docs/
├── orchestration/                # NEW: Orchestration docs
│   ├── README.md                 # Overview of orchestration patterns
│   ├── smartrouter/              # SmartRouter docs
│   │   ├── ARCHITECTURE.md
│   │   └── ...
│   └── moe/                      # MoE docs
│       ├── ARCHITECTURE.md
│       ├── API.md
│       ├── DEPLOYMENT.md
│       ├── CONFIGURATION.md
│       └── TROUBLESHOOTING.md

tests/
├── asdrp/
│   ├── orchestration/            # NEW: Orchestration tests
│   │   ├── smartrouter/          # MOVED: SmartRouter tests
│   │   │   ├── test_smartrouter.py
│   │   │   └── ...
│   │   └── moe/                  # NEW: MoE tests
│   │       ├── test_orchestrator.py
│   │       ├── test_expert_selector.py
│   │       ├── test_expert_executor.py
│   │       ├── test_result_mixer.py
│   │       └── test_integration.py

scripts/
├── orchestration/                # NEW: Orchestration scripts
│   ├── run_smartrouter.sh        # MOVED: SmartRouter launcher
│   ├── setup_moe.sh              # NEW: MoE setup
│   ├── run_moe.sh                # NEW: MoE launcher
│   └── check_moe_config.py       # NEW: Config validator

data/
└── orchestration/                # NEW: Orchestration data
    ├── smartrouter/              # SmartRouter data
    │   ├── cache/
    │   └── traces/
    └── moe/                      # MoE data
        ├── cache/
        └── traces/
```

### 2.2 Rationale for Separation

**Benefits of `asdrp/orchestration/` structure:**

1. **Clear Separation of Concerns**
   - `asdrp/agents/`: Individual agent implementations (stateless workers)
   - `asdrp/orchestration/`: Orchestration strategies (stateful coordinators)

2. **Parallel Development**
   - Agent developers work in `asdrp/agents/`
   - Orchestration developers work in `asdrp/orchestration/`
   - Minimal merge conflicts

3. **Easier Testing**
   - Unit tests for agents: `tests/asdrp/agents/`
   - Integration tests for orchestration: `tests/asdrp/orchestration/`

4. **Scalability**
   - Easy to add new orchestration patterns (e.g., `dag/`, `pipeline/`, `ensemble/`)
   - No confusion with agent-level code

5. **Import Clarity**
   ```python
   # Clear distinction in imports
   from asdrp.agents.single.geo_agent import create_geo_agent
   from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
   from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
   ```

### 2.3 Agent Factory Integration

The MoE Orchestrator uses the **existing AgentFactory** for expert creation:

```python
# asdrp/orchestration/moe/orchestrator.py

from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.protocol import AgentProtocol
from asdrp.agents.config_loader import AgentConfigLoader
from asdrp.orchestration.moe.interfaces import (
    IExpertSelector,
    IExpertExecutor,
    IResultMixer,
    ICache
)

class MoEOrchestrator:
    """
    MoE Orchestrator using existing AgentFactory.

    Architecture:
    - Located in asdrp/orchestration/moe/ (separate from agents)
    - Uses AgentFactory from asdrp/agents/ for expert creation
    - Follows same patterns as SmartRouter
    """

    def __init__(
        self,
        agent_factory: AgentFactory,
        expert_selector: IExpertSelector,
        expert_executor: IExpertExecutor,
        result_mixer: IResultMixer,
        cache: Optional[ICache] = None
    ):
        self._factory = agent_factory
        self._selector = expert_selector
        self._executor = expert_executor
        self._mixer = result_mixer
        self._cache = cache

    async def route_query(self, query: str, session_id: Optional[str] = None) -> MoEResult:
        """
        Route query through MoE pipeline.

        Flow:
        1. Check cache
        2. Select experts (uses capabilities from config)
        3. Execute in parallel (uses AgentFactory.get_agent_with_session)
        4. Mix results
        5. Store in cache
        """
        # 1. Check cache
        if self._cache:
            cached = await self._cache.get(query)
            if cached:
                return cached

        # 2. Select experts (from asdrp/agents/single/)
        selected_experts = await self._selector.select(query, k=3)

        # 3. Get agents from factory with sessions
        agents_with_sessions = []
        for expert_id in selected_experts:
            agent, session = await self._factory.get_agent_with_session(
                expert_id, session_id
            )
            agents_with_sessions.append((agent, session))

        # 4. Execute in parallel
        results = await self._executor.execute_parallel(
            agents_with_sessions, query
        )

        # 5. Mix results
        final_result = await self._mixer.mix(results, selected_experts)

        # 6. Cache
        if self._cache:
            await self._cache.store(query, final_result)

        return final_result
```

### 2.4 Configuration Pattern

Follows the **same YAML pattern** as existing configs:

```yaml
# config/moe.yaml

# Follows same structure as config/smartrouter.yaml
enabled: true

moe:
  # Expert selection strategy
  selection_strategy: "capability_match"  # or "learned_gating"
  top_k_experts: 3
  confidence_threshold: 0.3

  # Result mixing strategy
  mixing_strategy: "weighted_average"  # or "voting" or "synthesis"

  # Performance settings
  parallel_execution: true
  timeout_per_expert: 10.0
  overall_timeout: 30.0

# Model configs (like smartrouter.yaml)
models:
  selection:
    name: "gpt-4.1-mini"
    temperature: 0.1
    max_tokens: 500
  mixing:
    name: "gpt-4.1-mini"
    temperature: 0.3
    max_tokens: 2000

# Expert groups (map to existing agents from open_agents.yaml)
experts:
  location_expert:
    agents: ["geo", "map"]
    capabilities: ["geocoding", "reverse_geocoding", "directions", "places"]
    weight: 1.0

  search_expert:
    agents: ["one", "perplexity"]
    capabilities: ["web_search", "realtime", "search"]
    weight: 1.0

  business_expert:
    agents: ["yelp", "yelp_mcp"]
    capabilities: ["local_business", "reviews", "restaurants"]
    weight: 1.0

  knowledge_expert:
    agents: ["wiki"]
    capabilities: ["wikipedia", "encyclopedia", "history"]
    weight: 1.0

  finance_expert:
    agents: ["finance"]
    capabilities: ["stocks", "market_data", "financial"]
    weight: 1.0

  chitchat_expert:
    agents: ["chitchat"]
    capabilities: ["conversation", "general"]
    weight: 0.5

# Cache settings
cache:
  enabled: true
  type: "semantic"  # Uses embedding similarity
  storage:
    backend: "sqlite"
    path: "data/orchestration/moe/cache/semantic.db"
  policy:
    similarity_threshold: 0.1  # Cosine similarity
    ttl: 3600  # 1 hour
    max_entries: 10000

# Error handling
error_handling:
  timeout: 30.0
  retries: 2
  fallback_agent: "one"  # Fallback to OneAgent
  fallback_message: "I apologize, but I encountered an issue processing your request."

# Tracing (follows SmartRouter pattern)
tracing:
  enabled: true
  storage:
    backend: "sqlite"
    path: "data/orchestration/moe/traces/orchestration.db"
  exporters:
    - type: "json"
      path: "data/orchestration/moe/traces/json/"
    - type: "console"
      level: "info"
```

### 2.5 Pydantic Models

```python
# asdrp/orchestration/moe/config_loader.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
import yaml

from asdrp.agents.config_loader import ModelConfig  # Reuse existing

@dataclass
class ExpertGroupConfig:
    """Configuration for expert group."""
    agents: List[str]  # Agent IDs from open_agents.yaml
    capabilities: List[str]
    weight: float = 1.0

@dataclass
class MoESelectionConfig:
    """Selection strategy configuration."""
    selection_strategy: Literal["capability_match", "learned_gating"]
    top_k_experts: int = 3
    confidence_threshold: float = 0.3

@dataclass
class MoEMixingConfig:
    """Result mixing configuration."""
    mixing_strategy: Literal["weighted_average", "voting", "synthesis"]

@dataclass
class MoECacheConfig:
    """Cache configuration."""
    enabled: bool = True
    type: Literal["semantic", "exact", "hybrid"]
    storage: Dict[str, Any]
    policy: Dict[str, Any]

@dataclass
class MoEConfig:
    """Complete MoE configuration."""
    enabled: bool
    moe: Dict[str, Any]
    models: Dict[str, ModelConfig]
    experts: Dict[str, ExpertGroupConfig]
    cache: MoECacheConfig
    error_handling: Dict[str, Any]
    tracing: Dict[str, Any]

class MoEConfigLoader:
    """
    MoE configuration loader.

    Follows pattern from:
    - asdrp/agents/config_loader.py (AgentConfigLoader)
    - asdrp/orchestration/smartrouter/config_loader.py (SmartRouterConfigLoader)
    """

    def __init__(self, config_path: str = "config/moe.yaml"):
        self.config_path = Path(config_path)
        self._config_cache: Optional[MoEConfig] = None

    def load_config(self) -> MoEConfig:
        """Load and parse YAML configuration."""
        with open(self.config_path, "r") as f:
            config_dict = yaml.safe_load(f)

        # Validate and parse
        try:
            config = MoEConfig(**config_dict)
            self._config_cache = config
            return config
        except Exception as e:
            from asdrp.orchestration.moe.exceptions import ConfigException
            raise ConfigException(f"Invalid MoE config: {e}")

    def validate_expert_agents(self, agent_config_loader) -> None:
        """
        Validate that all expert agents exist in open_agents.yaml.

        Args:
            agent_config_loader: AgentConfigLoader instance from asdrp.agents

        Ensures MoE config references valid agents.
        """
        from asdrp.agents.config_loader import AgentConfigLoader

        available_agents = set(agent_config_loader.list_agents())

        for expert_name, expert_config in self._config_cache.experts.items():
            for agent_id in expert_config.agents:
                if agent_id not in available_agents:
                    from asdrp.orchestration.moe.exceptions import ConfigException
                    raise ConfigException(
                        f"Expert '{expert_name}' references unknown agent '{agent_id}'"
                    )
```

---

## 3. Core Components

### 3.1 Orchestrator (Main Entry Point)

**Location**: `asdrp/orchestration/moe/orchestrator.py`

**Pattern**: Follows `asdrp/orchestration/smartrouter/smartrouter.py`

```python
# asdrp/orchestration/moe/orchestrator.py

from typing import Optional, List, Tuple, Any
import asyncio
from datetime import datetime
from dataclasses import dataclass

from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.orchestration.moe.interfaces import (
    IExpertSelector,
    IExpertExecutor,
    IResultMixer,
    ICache
)
from asdrp.orchestration.moe.config_loader import MoEConfigLoader, MoEConfig
from asdrp.orchestration.moe.exceptions import MoEException


@dataclass
class MoEResult:
    """Result from MoE orchestration."""
    response: str
    experts_used: List[str]
    trace: "MoETrace"


@dataclass
class MoETrace:
    """Orchestration trace for observability."""
    request_id: str
    latency_ms: float = 0.0
    expert_results: List[Any] = None
    cache_hit: bool = False
    fallback: bool = False
    error: Optional[str] = None


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
        cache: Optional[ICache] = None
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
        """
        self._factory = agent_factory
        self._selector = expert_selector
        self._executor = expert_executor
        self._mixer = result_mixer
        self._config = config
        self._cache = cache

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
        start_time = asyncio.get_event_loop().time()
        request_id = self._generate_request_id()

        try:
            # 1. Check cache
            if self._cache and self._config.cache.enabled:
                cached = await self._cache.get(query)
                if cached:
                    return self._build_cached_result(cached, start_time)

            # 2. Select experts
            selected_expert_ids = await self._selector.select(
                query,
                k=self._config.moe.get("top_k_experts", 3),
                threshold=self._config.moe.get("confidence_threshold", 0.3)
            )

            # 3. Get agents from factory with sessions
            agents_with_sessions = []
            for expert_id in selected_expert_ids:
                agent, session = await self._factory.get_agent_with_session(
                    expert_id, session_id
                )
                agents_with_sessions.append((expert_id, agent, session))

            # 4. Execute in parallel
            expert_results = await self._executor.execute_parallel(
                agents_with_sessions,
                query,
                context,
                timeout=self._config.moe.get("overall_timeout", 30.0)
            )

            # 5. Mix results
            final_result = await self._mixer.mix(
                expert_results,
                selected_expert_ids,
                query
            )

            # 6. Cache
            if self._cache and self._config.cache.enabled:
                await self._cache.store(query, final_result)

            # 7. Build result with trace
            return self._build_result(
                final_result,
                selected_expert_ids,
                expert_results,
                start_time,
                request_id
            )

        except Exception as e:
            # Fallback to default agent
            return await self._handle_fallback(query, session_id, e)

    async def _handle_fallback(
        self,
        query: str,
        session_id: Optional[str],
        error: Exception
    ) -> MoEResult:
        """Fallback to default agent on error."""
        fallback_agent_id = self._config.error_handling.get("fallback_agent", "one")

        try:
            agent, session = await self._factory.get_agent_with_session(
                fallback_agent_id, session_id
            )

            from agents import Runner
            result = await Runner.run(
                starting_agent=agent,
                input=query,
                session=session
            )

            return MoEResult(
                response=str(result.final_output),
                experts_used=[fallback_agent_id],
                trace=MoETrace(
                    request_id=self._generate_request_id(),
                    fallback=True,
                    error=str(error)
                )
            )
        except Exception as fallback_error:
            return MoEResult(
                response=self._config.error_handling.get(
                    "fallback_message",
                    "I apologize, but I encountered an issue."
                ),
                experts_used=[],
                trace=MoETrace(
                    request_id=self._generate_request_id(),
                    fallback=True,
                    error=str(fallback_error)
                )
            )

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return f"moe-{uuid.uuid4().hex[:12]}"

    def _build_result(
        self,
        final_result: Any,
        expert_ids: List[str],
        expert_results: List[Any],
        start_time: float,
        request_id: str
    ) -> MoEResult:
        """Build MoEResult with complete trace."""
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        return MoEResult(
            response=final_result.content,
            experts_used=expert_ids,
            trace=MoETrace(
                request_id=request_id,
                latency_ms=latency_ms,
                expert_results=expert_results,
                cache_hit=False
            )
        )

    def _build_cached_result(self, cached: Any, start_time: float) -> MoEResult:
        """Build MoEResult for cache hit."""
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        return MoEResult(
            response=cached.response,
            experts_used=[],
            trace=MoETrace(
                request_id=self._generate_request_id(),
                latency_ms=latency_ms,
                cache_hit=True
            )
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
        """
        from asdrp.orchestration.moe.expert_selector import CapabilityBasedSelector
        from asdrp.orchestration.moe.expert_executor import ParallelExecutor
        from asdrp.orchestration.moe.result_mixer import WeightedMixer
        from asdrp.orchestration.moe.cache import SemanticCache

        selector = CapabilityBasedSelector(config)
        executor = ParallelExecutor(config)
        mixer = WeightedMixer(config)
        cache = SemanticCache(config) if config.cache.enabled else None

        return cls(
            agent_factory=agent_factory,
            expert_selector=selector,
            expert_executor=executor,
            result_mixer=mixer,
            config=config,
            cache=cache
        )
```

### 3.2 Interfaces

**Location**: `asdrp/orchestration/moe/interfaces.py`

```python
# asdrp/orchestration/moe/interfaces.py

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
```

### 3.3 Expert Selector

**Location**: `asdrp/orchestration/moe/expert_selector.py`

```python
# asdrp/orchestration/moe/expert_selector.py

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
        """
        # Extract keywords
        keywords = self._extract_keywords(query)

        # Score experts
        expert_scores: Dict[str, float] = {}
        for keyword in keywords:
            for capability, agents in self._capability_map.items():
                if keyword.lower() in capability.lower():
                    for agent_id in agents:
                        if agent_id not in expert_scores:
                            expert_scores[agent_id] = 0.0
                        expert_scores[agent_id] += 1.0

        # Normalize scores
        if expert_scores:
            max_score = max(expert_scores.values())
            expert_scores = {
                k: v / max_score for k, v in expert_scores.items()
            }

        # Filter and sort
        selected = [
            (agent_id, score)
            for agent_id, score in expert_scores.items()
            if score >= threshold
        ]
        selected.sort(key=lambda x: x[1], reverse=True)

        # Return top-k
        return [agent_id for agent_id, score in selected[:k]]

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query.

        Simple implementation:
        - Remove stop words
        - Extract unique words
        - Return keywords
        """
        stop_words: Set[str] = {
            "the", "a", "an", "is", "are", "what", "where",
            "when", "how", "who", "why", "which"
        }

        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words]

        return list(set(keywords))
```

### 3.4 Expert Executor

**Location**: `asdrp/orchestration/moe/expert_executor.py`

```python
# asdrp/orchestration/moe/expert_executor.py

from typing import List, Tuple, Optional, Dict, Any
import asyncio
from dataclasses import dataclass

from asdrp.agents.protocol import AgentProtocol
from asdrp.orchestration.moe.interfaces import IExpertExecutor
from asdrp.orchestration.moe.config_loader import MoEConfig


@dataclass
class ExpertResult:
    """Result from expert execution."""
    expert_id: str
    output: str
    success: bool
    latency_ms: float
    error: Optional[str] = None


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
        self._config = config
        self._max_concurrent = config.moe.get("max_concurrent", 10)
        self._timeout_per_expert = config.moe.get("timeout_per_expert", 10.0)

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
        """
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
            # Return partial results
            results = [
                ExpertResult(
                    expert_id=expert_id,
                    output="",
                    success=False,
                    latency_ms=timeout * 1000,
                    error="Overall timeout"
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
        """Execute single agent with timeout."""
        start = asyncio.get_event_loop().time()

        try:
            # Execute agent using OpenAI Runner
            from agents import Runner

            result = await asyncio.wait_for(
                Runner.run(
                    starting_agent=agent,
                    input=query,
                    session=session
                ),
                timeout=self._timeout_per_expert
            )

            latency_ms = (asyncio.get_event_loop().time() - start) * 1000

            return ExpertResult(
                expert_id=expert_id,
                output=str(result.final_output),
                success=True,
                latency_ms=latency_ms
            )

        except asyncio.TimeoutError:
            return ExpertResult(
                expert_id=expert_id,
                output="",
                success=False,
                latency_ms=self._timeout_per_expert * 1000,
                error="Timeout"
            )

        except Exception as e:
            return ExpertResult(
                expert_id=expert_id,
                output="",
                success=False,
                latency_ms=(asyncio.get_event_loop().time() - start) * 1000,
                error=str(e)
            )
```

### 3.5 Result Mixer

**Location**: `asdrp/orchestration/moe/result_mixer.py`

```python
# asdrp/orchestration/moe/result_mixer.py

from typing import List, Dict
from dataclasses import dataclass

from asdrp.orchestration.moe.interfaces import IResultMixer
from asdrp.orchestration.moe.config_loader import MoEConfig
from asdrp.orchestration.moe.expert_executor import ExpertResult


@dataclass
class MixedResult:
    """Mixed result from multiple experts."""
    content: str
    weights: Dict[str, float]
    quality_score: float


class WeightedMixer(IResultMixer):
    """
    Mix expert results using confidence weighting.

    Strategy:
    1. Filter successful results
    2. Weight by expert configuration (from config)
    3. Synthesize using LLM
    """

    def __init__(self, config: MoEConfig):
        self._config = config
        self._mixing_strategy = config.moe.get("mixing_strategy", "synthesis")

    async def mix(
        self,
        expert_results: List[ExpertResult],
        expert_ids: List[str],
        query: str
    ) -> MixedResult:
        """
        Mix expert results.

        Args:
            expert_results: Results from experts
            expert_ids: Expert IDs
            query: Original query

        Returns:
            MixedResult with synthesized content
        """
        # Filter successful results
        successful = [r for r in expert_results if r.success]

        if not successful:
            return MixedResult(
                content="I don't have enough information to answer that.",
                weights={},
                quality_score=0.0
            )

        # Get weights from config
        weights = self._get_weights(successful)

        # Mix using LLM synthesis
        mixed = await self._llm_synthesis(successful, weights, query)

        return mixed

    def _get_weights(self, results: List[ExpertResult]) -> Dict[str, float]:
        """Get weights from config."""
        weights: Dict[str, float] = {}

        for result in results:
            # Find expert group containing this agent
            for expert_name, expert_config in self._config.experts.items():
                if result.expert_id in expert_config.agents:
                    weights[result.expert_id] = expert_config.weight
                    break

        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    async def _llm_synthesis(
        self,
        results: List[ExpertResult],
        weights: Dict[str, float],
        query: str
    ) -> MixedResult:
        """
        Synthesize using LLM.

        Uses gpt-4.1-mini to synthesize expert outputs.
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        model_config = self._config.models.get("mixing")

        # Format weighted results
        weighted_results = "\n\n".join([
            f"[{r.expert_id} - weight: {weights.get(r.expert_id, 0.0):.2f}]\n{r.output}"
            for r in results
        ])

        prompt = f"""Synthesize the following expert responses into a single, coherent answer.

Expert Responses:
{weighted_results}

Original Query: {query}

Synthesize a response that:
- Combines the best information from all experts
- Weights responses by their confidence scores
- Resolves any contradictions
- Is clear and concise
- Cites sources when relevant

Synthesized Response:"""

        response = await client.chat.completions.create(
            model=model_config.name,
            messages=[{"role": "user", "content": prompt}],
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens
        )

        content = response.choices[0].message.content

        return MixedResult(
            content=content,
            weights=weights,
            quality_score=self._estimate_quality(content, results)
        )

    def _estimate_quality(self, content: str, results: List[ExpertResult]) -> float:
        """Estimate synthesis quality."""
        # Simple heuristic: more sources + longer response = higher quality
        source_score = min(len(results) / 3.0, 1.0)
        length_score = min(len(content.split()) / 100.0, 1.0)

        return (source_score * 0.6) + (length_score * 0.4)
```

### 3.6 Exceptions

**Location**: `asdrp/orchestration/moe/exceptions.py`

```python
# asdrp/orchestration/moe/exceptions.py

class MoEException(Exception):
    """Base exception for MoE orchestration errors."""
    pass


class ConfigException(MoEException):
    """Configuration loading or validation error."""
    pass


class ExpertSelectionException(MoEException):
    """Expert selection error."""
    pass


class ExecutionException(MoEException):
    """Expert execution error."""
    pass


class MixingException(MoEException):
    """Result mixing error."""
    pass


class CacheException(MoEException):
    """Cache operation error."""
    pass
```

---

## 4. API Integration

### 4.1 Server Integration

**Location**: `server/agent_service.py` (modifications)

```python
# server/agent_service.py

from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.config_loader import AgentConfigLoader
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.orchestration.moe.config_loader import MoEConfigLoader

class AgentService:
    """Extended to support MoE orchestration."""

    def __init__(self):
        self._factory = AgentFactory.instance()
        self._config_loader = AgentConfigLoader()

        # Initialize MoE orchestrator
        try:
            moe_config = MoEConfigLoader().load_config()
            if moe_config.enabled:
                self._moe = MoEOrchestrator.create_default(
                    self._factory, moe_config
                )
            else:
                self._moe = None
        except Exception as e:
            logger.warning(f"MoE orchestrator not available: {e}")
            self._moe = None

    async def route_moe(
        self,
        request: SimulationRequest
    ) -> SimulationResponse:
        """
        Route query through MoE orchestrator.

        Args:
            request: SimulationRequest with query

        Returns:
            SimulationResponse with synthesized result
        """
        if not self._moe:
            raise HTTPException(
                status_code=503,
                detail="MoE orchestrator not available"
            )

        result = await self._moe.route_query(
            query=request.input,
            session_id=request.session_id,
            context=request.context
        )

        return SimulationResponse(
            response=result.response,
            trace=[
                SimulationStep(
                    agent=expert_id,
                    output=result.response,
                    reasoning="MoE expert"
                )
                for expert_id in result.experts_used
            ],
            metadata={
                "orchestrator": "moe",
                "experts_used": result.experts_used,
                "latency_ms": result.trace.latency_ms,
                "cache_hit": result.trace.cache_hit
            }
        )
```

**Location**: `server/main.py` (modifications)

```python
# server/main.py

@app.post("/agents/moe/chat")
async def chat_moe(
    request: SimulationRequest,
    api_key: str = Depends(verify_api_key)
) -> SimulationResponse:
    """
    Chat endpoint for MoE orchestrator.

    Uses MoE to route query to best experts.
    """
    try:
        response = await agent_service.route_moe(request)
        return response
    except Exception as e:
        logger.error(f"MoE routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 5. Testing Requirements

### 5.1 Test Structure

```
tests/
└── asdrp/
    └── orchestration/            # NEW: Orchestration tests
        ├── __init__.py
        ├── smartrouter/          # MOVED: SmartRouter tests
        │   ├── __init__.py
        │   ├── test_smartrouter.py
        │   └── ...
        └── moe/                  # NEW: MoE tests
            ├── __init__.py
            ├── conftest.py       # Shared fixtures
            ├── test_orchestrator.py
            ├── test_expert_selector.py
            ├── test_expert_executor.py
            ├── test_result_mixer.py
            ├── test_cache.py
            ├── test_config_loader.py
            └── test_integration.py
```

### 5.2 Example Test

**Location**: `tests/asdrp/orchestration/moe/test_orchestrator.py`

```python
# tests/asdrp/orchestration/moe/test_orchestrator.py

import pytest
from unittest.mock import Mock, AsyncMock, patch

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.orchestration.moe.config_loader import MoEConfigLoader


class TestMoEOrchestrator:
    """Test MoE orchestrator."""

    @pytest.fixture
    def mock_factory(self):
        """Mock AgentFactory."""
        factory = Mock()
        return factory

    @pytest.fixture
    def mock_config(self):
        """Mock MoE config."""
        config = MoEConfigLoader().load_config()
        return config

    @pytest.fixture
    def orchestrator(self, mock_factory, mock_config):
        """Create test orchestrator."""
        return MoEOrchestrator.create_default(mock_factory, mock_config)

    @pytest.mark.asyncio
    async def test_route_query(self, orchestrator, mock_factory):
        """Test query routing."""
        # Setup mock
        mock_agent = Mock()
        mock_agent.name = "YelpAgent"
        mock_session = Mock()

        mock_factory.get_agent_with_session = AsyncMock(
            return_value=(mock_agent, mock_session)
        )

        with patch("agents.Runner.run") as mock_run:
            mock_run.return_value = Mock(final_output="Result")

            # Execute
            result = await orchestrator.route_query("Find pizza")

            # Assert
            assert result.response
            assert len(result.experts_used) > 0
```

---

## 6. Documentation

### 6.1 Documentation Structure

```
docs/
└── orchestration/                # NEW: Orchestration docs
    ├── README.md                 # Overview of orchestration patterns
    ├── smartrouter/              # MOVED: SmartRouter docs
    │   ├── ARCHITECTURE.md
    │   ├── API.md
    │   └── ...
    └── moe/                      # NEW: MoE docs
        ├── ARCHITECTURE.md       # Architecture overview
        ├── API.md                # API reference
        ├── DEPLOYMENT.md         # Deployment guide
        ├── CONFIGURATION.md      # Configuration reference
        └── TROUBLESHOOTING.md    # Common issues
```

### 6.2 Orchestration Overview

**Location**: `docs/orchestration/README.md`

```markdown
# OpenAgents Orchestration Layer

The orchestration layer (`asdrp/orchestration/`) provides multiple strategies for coordinating agent execution.

## Available Orchestrators

### SmartRouter
**Location**: `asdrp/orchestration/smartrouter/`
**Strategy**: Sequential query decomposition and multi-agent routing
**Best For**: Complex queries requiring step-by-step reasoning

### MoE (Mixture of Experts)
**Location**: `asdrp/orchestration/moe/`
**Strategy**: Parallel expert execution with weighted synthesis
**Best For**: Queries benefiting from multiple specialized perspectives

## Choosing an Orchestrator

| Orchestrator | Latency | Complexity | Best Use Case |
|-------------|---------|------------|---------------|
| Single Agent | <1s | Simple | Direct queries for one domain |
| MoE | 1-2s | Moderate | Multi-domain queries requiring parallel execution |
| SmartRouter | 3-6s | Complex | Multi-step queries requiring sequential reasoning |

## Integration

All orchestrators use:
- **AgentFactory** from `asdrp/agents/` for agent creation
- **YAML configuration** from `config/`
- **Standard API** via `server/agent_service.py`
```

---

## 7. Deployment

### 7.1 Setup Script

**Location**: `scripts/orchestration/setup_moe.sh`

```bash
#!/bin/bash
# Setup MoE Orchestrator

set -e

echo "Setting up MoE Orchestrator..."

# Validate config
echo "Validating configuration..."
python scripts/orchestration/check_moe_config.py

# Create data directories
mkdir -p data/orchestration/moe/cache
mkdir -p data/orchestration/moe/traces

# Initialize cache database
python -c "
from asdrp.orchestration.moe.cache import SemanticCache
from asdrp.orchestration.moe.config_loader import MoEConfigLoader

config = MoEConfigLoader().load_config()
cache = SemanticCache(config)
print('✓ Cache database initialized')
"

echo "✓ MoE Orchestrator setup complete"
```

### 7.2 Launch Script

**Location**: `scripts/orchestration/run_moe.sh`

```bash
#!/bin/bash
# Launch server with MoE orchestrator

set -e

CONFIG=${1:-config/moe.yaml}
PORT=${2:-8000}

echo "Starting OpenAgents server with MoE orchestrator..."
echo "  Config: $CONFIG"
echo "  Port: $PORT"

cd server
python -m server.main --port $PORT
```

---

## 8. Migration Path

### Phase 1: Create Orchestration Layer (Week 1)
- [ ] Create `asdrp/orchestration/` directory structure
- [ ] Move SmartRouter from `asdrp/agents/router/` to `asdrp/orchestration/smartrouter/`
- [ ] Update all imports in SmartRouter code
- [ ] Update tests to new location
- [ ] Update documentation paths

### Phase 2: Implement MoE Core (Week 2)
- [ ] Implement `orchestrator.py`
- [ ] Implement `interfaces.py`
- [ ] Implement `config_loader.py`
- [ ] Implement `exceptions.py`
- [ ] Write unit tests

### Phase 3: Implement MoE Components (Week 3)
- [ ] Implement `expert_selector.py`
- [ ] Implement `expert_executor.py`
- [ ] Implement `result_mixer.py`
- [ ] Implement `cache.py`
- [ ] Write component tests

### Phase 4: Integration (Week 4)
- [ ] Integrate with AgentFactory
- [ ] Add API endpoints to `server/`
- [ ] Update `agent_service.py`
- [ ] Write integration tests
- [ ] Update documentation

### Phase 5: Production (Week 5)
- [ ] Performance testing
- [ ] Deployment scripts
- [ ] Monitoring setup
- [ ] Launch

---

## Appendix A: Project Structure Summary

```
/Users/pmui/dev/halo/openagents/
├── asdrp/
│   ├── agents/                              # EXISTING: Individual agents
│   │   ├── protocol.py
│   │   ├── agent_factory.py
│   │   ├── config_loader.py
│   │   ├── single/
│   │   └── mcp/
│   │
│   ├── orchestration/                       # NEW: Orchestration layer
│   │   ├── __init__.py
│   │   ├── smartrouter/                     # MOVED from agents/router/
│   │   │   ├── __init__.py
│   │   │   ├── smartrouter.py
│   │   │   ├── interfaces.py
│   │   │   ├── config_loader.py
│   │   │   └── ...
│   │   └── moe/                             # NEW: MoE implementation
│   │       ├── __init__.py
│   │       ├── orchestrator.py
│   │       ├── interfaces.py
│   │       ├── config_loader.py
│   │       ├── exceptions.py
│   │       ├── expert_selector.py
│   │       ├── expert_executor.py
│   │       ├── result_mixer.py
│   │       └── cache.py
│   │
│   ├── actions/                             # EXISTING: Tools
│   └── util/                                # EXISTING: Utilities
│
├── config/
│   ├── open_agents.yaml                     # EXISTING: Agent definitions
│   ├── smartrouter.yaml                     # EXISTING: SmartRouter config
│   └── moe.yaml                             # NEW: MoE config
│
├── server/
│   ├── main.py                              # MODIFIED: Add MoE endpoint
│   ├── agent_service.py                     # MODIFIED: Add MoE support
│   └── models.py                            # MODIFIED: Add MoE DTOs
│
├── docs/
│   └── orchestration/                       # NEW: Orchestration docs
│       ├── README.md
│       ├── smartrouter/
│       └── moe/
│
├── tests/
│   └── asdrp/
│       └── orchestration/                   # NEW: Orchestration tests
│           ├── smartrouter/                 # MOVED: SmartRouter tests
│           └── moe/                         # NEW: MoE tests
│
├── scripts/
│   └── orchestration/                       # NEW: Orchestration scripts
│       ├── setup_moe.sh
│       ├── run_moe.sh
│       └── check_moe_config.py
│
└── data/
    └── orchestration/                       # NEW: Orchestration data
        ├── smartrouter/
        │   ├── cache/
        │   └── traces/
        └── moe/
            ├── cache/
            └── traces/
```

---

## Appendix B: Import Path Changes

### Before (Current)
```python
from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
from asdrp.orchestration.smartrouter.interfaces import IQueryInterpreter
```

### After (Proposed)
```python
from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
from asdrp.orchestration.smartrouter.interfaces import IQueryInterpreter
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.orchestration.moe.interfaces import IExpertSelector
```

---

## Document Metadata

**Authors**: OpenAgents Engineering Team
**Status**: Final Specification - Architecture-Aligned
**Implementation Priority**: P1
**Estimated LOC**: 2,000-3,000 (MoE only)
**Dependencies**: OpenAgents Core, AgentFactory, existing patterns
**Related Documents**: CLAUDE.md, SmartRouter docs

**Change Log**:
- 2024-12-13: Updated to move orchestration to `asdrp/orchestration/`
- Separated agents (asdrp/agents/) from orchestration (asdrp/orchestration/)
- Updated all paths, imports, and documentation accordingly
- Added migration path for SmartRouter relocation
