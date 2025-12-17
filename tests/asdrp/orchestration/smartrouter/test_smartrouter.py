"""
Tests for SmartRouter

Comprehensive test suite for the SmartRouter orchestrator.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
from asdrp.orchestration.smartrouter.config_loader import (
    SmartRouterConfig,
    SmartRouterConfigLoader,
    ModelConfig,
    ModelConfigs,
    DecompositionConfig,
    EvaluationConfig,
    ErrorHandlingConfig,
)
from asdrp.orchestration.smartrouter.interfaces import (
    QueryIntent,
    QueryComplexity,
    Subquery,
    AgentResponse,
    SynthesizedResult,
    EvaluationResult,
    RoutingPattern,
)
from asdrp.orchestration.smartrouter.exceptions import SmartRouterException
from asdrp.orchestration.smartrouter.trace_capture import SmartRouterExecutionResult


class TestSmartRouterInitialization:
    """Test SmartRouter initialization."""

    @pytest.fixture
    def config(self):
        """Create a test SmartRouterConfig."""
        return SmartRouterConfig(
            models=ModelConfigs(
                interpretation=ModelConfig("gpt-4.1-mini", 0.1, 500),
                decomposition=ModelConfig("gpt-4.1-mini", 0.2, 1000),
                synthesis=ModelConfig("gpt-4.1-mini", 0.3, 2000),
                evaluation=ModelConfig("gpt-4.1-mini", 0.01, 500),
            ),
            decomposition=DecompositionConfig(10, 3, 0.4),
            capabilities={"geo": ["geocoding"], "finance": ["stocks"]},
            evaluation=EvaluationConfig("Not enough info", 0.7, ["completeness"]),
            error_handling=ErrorHandlingConfig(30.0, 2),
            enabled=True,
        )

    @pytest.fixture
    def mock_factory(self):
        """Create a mock AgentFactory."""
        return MagicMock()

    def test_init_with_config(self, config, mock_factory):
        """Test initialization with config."""
        router = SmartRouter(config, mock_factory)
        
        assert router.config == config
        assert router.agent_factory == mock_factory
        # session_id can be None when explicitly passed as None
        assert router.session_id is None or router.session_id == "smartrouter_default"
        assert router.interpreter is not None
        assert router.decomposer is not None
        assert router.router is not None
        assert router.dispatcher is not None
        assert router.aggregator is not None
        assert router.synthesizer is not None
        assert router.judge is not None

    def test_init_with_session_id(self, config, mock_factory):
        """Test initialization with session ID."""
        router = SmartRouter(config, mock_factory, session_id="test_session")
        
        assert router.session_id == "test_session"

    def test_init_with_custom_components(self, config, mock_factory):
        """Test initialization with custom components."""
        custom_interpreter = MagicMock()
        custom_decomposer = MagicMock()
        
        router = SmartRouter(
            config,
            mock_factory,
            interpreter=custom_interpreter,
            decomposer=custom_decomposer
        )
        
        assert router.interpreter == custom_interpreter
        assert router.decomposer == custom_decomposer

    def test_get_capabilities(self, config, mock_factory):
        """Test getting capabilities."""
        router = SmartRouter(config, mock_factory)
        
        capabilities = router.get_capabilities()
        
        assert capabilities == config.capabilities
        assert "geo" in capabilities
        assert "finance" in capabilities

    def test_get_config(self, config, mock_factory):
        """Test getting config."""
        router = SmartRouter(config, mock_factory)
        
        retrieved_config = router.get_config()
        
        assert retrieved_config == config


class TestSmartRouterCreate:
    """Test SmartRouter.create factory method."""

    @pytest.fixture
    def mock_factory(self):
        """Create a mock AgentFactory."""
        return MagicMock()

    def test_create_with_default_config(self, mock_factory):
        """Test creating SmartRouter with default config."""
        router = SmartRouter.create(mock_factory)
        
        assert isinstance(router, SmartRouter)
        assert router.config.enabled is True
        assert router.agent_factory == mock_factory

    def test_create_with_custom_config_path(self, mock_factory):
        """Test creating SmartRouter with custom config path."""
        router = SmartRouter.create(mock_factory, config_path="config/smartrouter.yaml")
        
        assert isinstance(router, SmartRouter)
        assert router.config.enabled is True

    def test_create_with_session_id(self, mock_factory):
        """Test creating SmartRouter with session ID."""
        router = SmartRouter.create(mock_factory, session_id="test_session")
        
        assert router.session_id == "test_session"

    def test_create_fails_when_disabled(self, mock_factory):
        """Test that create fails when SmartRouter is disabled."""
        with patch('asdrp.orchestration.smartrouter.smartrouter.SmartRouterConfigLoader') as mock_loader:
            mock_config = MagicMock()
            mock_config.enabled = False
            mock_loader.return_value.load_config.return_value = mock_config
            
            with pytest.raises(SmartRouterException):
                SmartRouter.create(mock_factory)


class TestSmartRouterSimpleQuery:
    """Test SmartRouter handling of simple queries."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return SmartRouterConfig(
            models=ModelConfigs(
                interpretation=ModelConfig("gpt-4.1-mini", 0.1, 500),
                decomposition=ModelConfig("gpt-4.1-mini", 0.2, 1000),
                synthesis=ModelConfig("gpt-4.1-mini", 0.3, 2000),
                evaluation=ModelConfig("gpt-4.1-mini", 0.01, 500),
            ),
            decomposition=DecompositionConfig(10, 3, 0.4),
            capabilities={"geo": ["geocoding"], "finance": ["stocks"], "chitchat": ["conversation"]},
            evaluation=EvaluationConfig("Not enough info", 0.7, ["completeness"]),
            error_handling=ErrorHandlingConfig(30.0, 2),
            enabled=True,
        )

    @pytest.fixture
    def mock_factory(self):
        """Create a mock AgentFactory."""
        factory = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "GeoAgent"
        mock_session = MagicMock()
        factory.get_agent = AsyncMock(return_value=mock_agent)
        factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, mock_session))
        return factory

    @pytest.fixture
    def router(self, config, mock_factory):
        """Create a SmartRouter instance."""
        router = SmartRouter(config, mock_factory, session_id=None)
        # Ensure session_id is None to avoid get_agent_with_session calls
        router.session_id = None
        return router

    @pytest.mark.asyncio
    async def test_handle_simple_query(self, router):
        """Test handling simple query."""
        intent = QueryIntent(
            original_query="Find address",
            complexity=QueryComplexity.SIMPLE,
            domains=["geocoding"],
            requires_synthesis=False,
            metadata={}
        )
        
        mock_result = MagicMock()
        mock_result.final_output = "The address is 123 Main St"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            answer = await router._handle_simple_query(intent)
            
            assert answer == "The address is 123 Main St"

    @pytest.mark.asyncio
    async def test_handle_simple_query_with_trace(self, router):
        """Test handling simple query with trace."""
        intent = QueryIntent(
            original_query="Find address",
            complexity=QueryComplexity.SIMPLE,
            domains=["geocoding"],
            requires_synthesis=False,
            metadata={}
        )
        
        from asdrp.orchestration.smartrouter.trace_capture import TraceCapture
        trace_capture = TraceCapture()
        
        mock_result = MagicMock()
        mock_result.final_output = "The address is 123 Main St"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            answer, agent_id = await router._handle_simple_query_with_trace(intent, trace_capture)
            
            assert answer == "The address is 123 Main St"
            assert agent_id == "geo"
            assert len(trace_capture.get_traces()) > 0

    @pytest.mark.asyncio
    async def test_handle_simple_query_chitchat(self, router):
        """Test handling chitchat query routes to chitchat agent."""
        intent = QueryIntent(
            original_query="Hello, how are you?",
            complexity=QueryComplexity.SIMPLE,
            domains=["conversation", "social"],
            requires_synthesis=False,
            metadata={}
        )
        
        mock_result = MagicMock()
        mock_result.final_output = "Hello! I'm doing well, thank you!"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            answer, agent_id = await router._handle_simple_query_with_trace(
                intent,
                router._handle_simple_query_with_trace.__globals__['TraceCapture']()
            )
            
            assert agent_id == "chitchat"
            assert "Hello" in answer

    @pytest.mark.asyncio
    async def test_handle_simple_query_no_agent(self, router):
        """Test handling simple query when no agent available."""
        intent = QueryIntent(
            original_query="Unknown capability query",
            complexity=QueryComplexity.SIMPLE,
            domains=["unknown_capability"],
            requires_synthesis=False,
            metadata={}
        )
        
        from asdrp.orchestration.smartrouter.trace_capture import TraceCapture
        trace_capture = TraceCapture()
        
        # The router falls back to "search" when it can't route a capability.
        # To test the "no agent available" case, we need to ensure that
        # even the fallback "search" capability has no candidates.
        # We'll patch _find_candidate_agents to return empty list for all capabilities
        original_find_candidates = router.router._find_candidate_agents
        router.router._find_candidate_agents = lambda capability: []
        
        with pytest.raises(SmartRouterException):
            await router._handle_simple_query_with_trace(intent, trace_capture)
        
        # Restore original method
        router.router._find_candidate_agents = original_find_candidates


class TestSmartRouterComplexQuery:
    """Test SmartRouter handling of complex queries."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return SmartRouterConfig(
            models=ModelConfigs(
                interpretation=ModelConfig("gpt-4.1-mini", 0.1, 500),
                decomposition=ModelConfig("gpt-4.1-mini", 0.2, 1000),
                synthesis=ModelConfig("gpt-4.1-mini", 0.3, 2000),
                evaluation=ModelConfig("gpt-4.1-mini", 0.01, 500),
            ),
            decomposition=DecompositionConfig(10, 3, 0.4),
            capabilities={"geo": ["geocoding"], "finance": ["stocks"]},
            evaluation=EvaluationConfig("Not enough info", 0.7, ["completeness"]),
            error_handling=ErrorHandlingConfig(30.0, 2),
            enabled=True,
        )

    @pytest.fixture
    def mock_factory(self):
        """Create a mock AgentFactory."""
        factory = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "GeoAgent"
        mock_session = MagicMock()
        factory.get_agent = AsyncMock(return_value=mock_agent)
        factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, mock_session))
        return factory

    @pytest.fixture
    def router(self, config, mock_factory):
        """Create a SmartRouter instance."""
        router = SmartRouter(config, mock_factory, session_id=None)
        # Ensure session_id is None to avoid get_agent_with_session calls
        router.session_id = None
        return router

    @pytest.mark.asyncio
    async def test_handle_complex_query(self, router):
        """Test handling complex query."""
        intent = QueryIntent(
            original_query="What's the weather and stock price?",
            complexity=QueryComplexity.COMPLEX,
            domains=["geography", "finance"],
            requires_synthesis=True,
            metadata={}
        )
        
        # Mock decomposer to return subqueries
        subquery1 = Subquery(
            id="sq1",
            text="What's the weather?",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        subquery2 = Subquery(
            id="sq2",
            text="What's the stock price?",
            capability_required="stocks",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        router.decomposer.decompose = AsyncMock(return_value=[subquery1, subquery2])
        
        # Mock dispatcher
        response1 = AgentResponse(
            subquery_id="sq1",
            agent_id="geo",
            content="Weather is sunny",
            success=True,
            metadata={}
        )
        response2 = AgentResponse(
            subquery_id="sq2",
            agent_id="finance",
            content="Stock price is $100",
            success=True,
            metadata={}
        )
        router.dispatcher.dispatch_all = AsyncMock(return_value=[response1, response2])
        
        # Mock synthesizer
        synthesized = SynthesizedResult(
            answer="Weather is sunny. Stock price is $100",
            sources=["geo", "finance"],
            confidence=0.9,
            conflicts_resolved=[],
            metadata={}
        )
        router.synthesizer.synthesize = AsyncMock(return_value=synthesized)
        
        from asdrp.orchestration.smartrouter.trace_capture import TraceCapture
        trace_capture = TraceCapture()
        agents_used = []
        
        answer = await router._handle_complex_query_with_trace(intent, trace_capture, agents_used)
        
        assert answer == "Weather is sunny. Stock price is $100"
        assert "geo" in agents_used
        assert "finance" in agents_used

    @pytest.mark.asyncio
    async def test_handle_complex_query_empty_decomposition(self, router):
        """Test handling complex query when decomposer returns empty."""
        intent = QueryIntent(
            original_query="Simple query",
            complexity=QueryComplexity.COMPLEX,
            domains=["geocoding"],
            requires_synthesis=False,
            metadata={}
        )
        
        # Mock decomposer to return empty (treats as simple)
        router.decomposer.decompose = AsyncMock(return_value=[])
        
        mock_result = MagicMock()
        mock_result.final_output = "Simple answer"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            from asdrp.orchestration.smartrouter.trace_capture import TraceCapture
            trace_capture = TraceCapture()
            agents_used = []
            
            answer = await router._handle_complex_query_with_trace(intent, trace_capture, agents_used)
            
            assert answer == "Simple answer"

    @pytest.mark.asyncio
    async def test_handle_complex_query_no_successful_responses(self, router):
        """Test handling complex query when all responses fail."""
        intent = QueryIntent(
            original_query="Complex query",
            complexity=QueryComplexity.COMPLEX,
            domains=["geocoding"],
            requires_synthesis=True,
            metadata={}
        )
        
        subquery = Subquery(
            id="sq1",
            text="Query",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        
        router.decomposer.decompose = AsyncMock(return_value=[subquery])
        
        # Mock dispatcher to return failed response
        failed_response = AgentResponse(
            subquery_id="sq1",
            agent_id="geo",
            content="Error occurred",
            success=False,
            metadata={}
        )
        router.dispatcher.dispatch_all = AsyncMock(return_value=[failed_response])
        
        from asdrp.orchestration.smartrouter.trace_capture import TraceCapture
        trace_capture = TraceCapture()
        agents_used = []
        
        answer = await router._handle_complex_query_with_trace(intent, trace_capture, agents_used)
        
        assert answer == router.config.evaluation.fallback_message


class TestSmartRouterRouteQuery:
    """Test SmartRouter.route_query main entry point."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return SmartRouterConfig(
            models=ModelConfigs(
                interpretation=ModelConfig("gpt-4.1-mini", 0.1, 500),
                decomposition=ModelConfig("gpt-4.1-mini", 0.2, 1000),
                synthesis=ModelConfig("gpt-4.1-mini", 0.3, 2000),
                evaluation=ModelConfig("gpt-4.1-mini", 0.01, 500),
            ),
            decomposition=DecompositionConfig(10, 3, 0.4),
            capabilities={"geo": ["geocoding"], "finance": ["stocks"], "chitchat": ["conversation"]},
            evaluation=EvaluationConfig("Not enough info", 0.7, ["completeness"]),
            error_handling=ErrorHandlingConfig(30.0, 2),
            enabled=True,
        )

    @pytest.fixture
    def mock_factory(self):
        """Create a mock AgentFactory."""
        factory = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "GeoAgent"
        mock_session = MagicMock()
        factory.get_agent = AsyncMock(return_value=mock_agent)
        factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, mock_session))
        return factory

    @pytest.fixture
    def router(self, config, mock_factory):
        """Create a SmartRouter instance."""
        router = SmartRouter(config, mock_factory, session_id=None)
        # Ensure session_id is None to avoid get_agent_with_session calls
        router.session_id = None
        return router

    @pytest.mark.asyncio
    async def test_route_query_simple(self, router):
        """Test routing simple query."""
        # Mock interpreter
        intent = QueryIntent(
            original_query="Find address",
            complexity=QueryComplexity.SIMPLE,
            domains=["geocoding"],
            requires_synthesis=False,
            metadata={}
        )
        router.interpreter.interpret = AsyncMock(return_value=intent)
        
        # Mock execution
        mock_result = MagicMock()
        mock_result.final_output = "The address is 123 Main St"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            # Mock judge
            evaluation = EvaluationResult(
                is_high_quality=True,
                completeness_score=0.9,
                accuracy_score=0.9,
                clarity_score=0.9,
                issues=[],
                should_fallback=False,
                metadata={}
            )
            router.judge.evaluate = AsyncMock(return_value=evaluation)
            
            result = await router.route_query("Find address")
            
            assert isinstance(result, SmartRouterExecutionResult)
            assert result.answer == "The address is 123 Main St"
            assert result.success is True
            assert result.final_decision in ["direct", "synthesized"]
            assert "geo" in result.agents_used

    @pytest.mark.asyncio
    async def test_route_query_chitchat(self, router):
        """Test routing chitchat query skips evaluation."""
        # Mock interpreter
        intent = QueryIntent(
            original_query="Hello!",
            complexity=QueryComplexity.SIMPLE,
            domains=["conversation", "social"],
            requires_synthesis=False,
            metadata={}
        )
        router.interpreter.interpret = AsyncMock(return_value=intent)
        
        # Mock judge to verify it's not called
        router.judge.evaluate = AsyncMock()
    
        # Mock execution
        mock_result = MagicMock()
        mock_result.final_output = "Hello! How can I help you?"
    
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
    
            result = await router.route_query("Hello!")
    
            assert isinstance(result, SmartRouterExecutionResult)
            assert result.success is True
            assert result.final_decision == "chitchat"
            # Judge should not be called for chitchat
            router.judge.evaluate.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_query_complex(self, router):
        """Test routing complex query."""
        # Mock interpreter
        intent = QueryIntent(
            original_query="Weather and stock price",
            complexity=QueryComplexity.COMPLEX,
            domains=["geography", "finance"],
            requires_synthesis=True,
            metadata={}
        )
        router.interpreter.interpret = AsyncMock(return_value=intent)
        
        # Mock decomposer
        subquery1 = Subquery(
            id="sq1",
            text="Weather",
            capability_required="geocoding",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        subquery2 = Subquery(
            id="sq2",
            text="Stock price",
            capability_required="stocks",
            dependencies=[],
            routing_pattern=RoutingPattern.DELEGATION,
            metadata={}
        )
        router.decomposer.decompose = AsyncMock(return_value=[subquery1, subquery2])
        
        # Mock dispatcher
        response1 = AgentResponse(
            subquery_id="sq1",
            agent_id="geo",
            content="Sunny",
            success=True,
            metadata={}
        )
        response2 = AgentResponse(
            subquery_id="sq2",
            agent_id="finance",
            content="$100",
            success=True,
            metadata={}
        )
        router.dispatcher.dispatch_all = AsyncMock(return_value=[response1, response2])
        
        # Mock synthesizer
        synthesized = SynthesizedResult(
            answer="Sunny weather. Stock is $100",
            sources=["geo", "finance"],
            confidence=0.9,
            conflicts_resolved=[],
            metadata={}
        )
        router.synthesizer.synthesize = AsyncMock(return_value=synthesized)
        
        # Mock judge
        evaluation = EvaluationResult(
            is_high_quality=True,
            completeness_score=0.9,
            accuracy_score=0.9,
            clarity_score=0.9,
            issues=[],
            should_fallback=False,
            metadata={}
        )
        router.judge.evaluate = AsyncMock(return_value=evaluation)
        
        result = await router.route_query("Weather and stock price")
        
        assert isinstance(result, SmartRouterExecutionResult)
        assert "Sunny" in result.answer
        assert "$100" in result.answer
        assert result.success is True
        assert result.final_decision == "synthesized"
        assert len(result.agents_used) > 1

    @pytest.mark.asyncio
    async def test_route_query_fallback_on_low_quality(self, router):
        """Test routing query with low quality answer triggers fallback."""
        # Mock interpreter
        intent = QueryIntent(
            original_query="Find address",
            complexity=QueryComplexity.SIMPLE,
            domains=["geocoding"],
            requires_synthesis=False,
            metadata={}
        )
        router.interpreter.interpret = AsyncMock(return_value=intent)
        
        # Mock execution
        mock_result = MagicMock()
        mock_result.final_output = "Bad answer"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            # Mock judge to return low quality
            evaluation = EvaluationResult(
                is_high_quality=False,
                completeness_score=0.3,
                accuracy_score=0.3,
                clarity_score=0.3,
                issues=["Incomplete", "Unclear"],
                should_fallback=True,
                metadata={}
            )
            router.judge.evaluate = AsyncMock(return_value=evaluation)
            
            result = await router.route_query("Find address")
            
            assert isinstance(result, SmartRouterExecutionResult)
            assert result.answer == router.config.evaluation.fallback_message
            assert result.final_decision == "fallback"
            assert result.original_answer == "Bad answer"

    @pytest.mark.asyncio
    async def test_route_query_error_handling(self, router):
        """Test routing query error handling."""
        # Mock interpreter to raise exception
        router.interpreter.interpret = AsyncMock(side_effect=SmartRouterException("Test error"))
        
        result = await router.route_query("Test query")
        
        assert isinstance(result, SmartRouterExecutionResult)
        assert result.answer == router.config.evaluation.fallback_message
        assert result.success is False
        assert result.final_decision == "error"

    @pytest.mark.asyncio
    async def test_route_query_unexpected_error(self, router):
        """Test routing query handles unexpected errors."""
        # Mock interpreter to raise unexpected exception
        router.interpreter.interpret = AsyncMock(side_effect=ValueError("Unexpected error"))
        
        result = await router.route_query("Test query")
        
        assert isinstance(result, SmartRouterExecutionResult)
        assert result.answer == router.config.evaluation.fallback_message
        assert result.success is False
        assert result.final_decision == "error"

    @pytest.mark.asyncio
    async def test_route_query_with_context(self, router):
        """Test routing query with context."""
        intent = QueryIntent(
            original_query="Find address",
            complexity=QueryComplexity.SIMPLE,
            domains=["geocoding"],
            requires_synthesis=False,
            metadata={}
        )
        router.interpreter.interpret = AsyncMock(return_value=intent)
        
        mock_result = MagicMock()
        mock_result.final_output = "Address found"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            evaluation = EvaluationResult(
                is_high_quality=True,
                completeness_score=0.9,
                accuracy_score=0.9,
                clarity_score=0.9,
                issues=[],
                should_fallback=False,
                metadata={}
            )
            router.judge.evaluate = AsyncMock(return_value=evaluation)
            
            result = await router.route_query("Find address", context={"key": "value"})
            
            assert isinstance(result, SmartRouterExecutionResult)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_route_query_trace_capture(self, router):
        """Test that route_query captures execution traces."""
        intent = QueryIntent(
            original_query="Find address",
            complexity=QueryComplexity.SIMPLE,
            domains=["geocoding"],
            requires_synthesis=False,
            metadata={}
        )
        router.interpreter.interpret = AsyncMock(return_value=intent)
        
        mock_result = MagicMock()
        mock_result.final_output = "Address found"
        
        with patch('agents.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            evaluation = EvaluationResult(
                is_high_quality=True,
                completeness_score=0.9,
                accuracy_score=0.9,
                clarity_score=0.9,
                issues=[],
                should_fallback=False,
                metadata={}
            )
            router.judge.evaluate = AsyncMock(return_value=evaluation)
            
            result = await router.route_query("Find address")
            
            assert len(result.traces) > 0
            assert result.total_time > 0
            # Check that key phases are captured
            phase_names = [trace["phase"] for trace in result.traces]
            assert "interpretation" in phase_names

