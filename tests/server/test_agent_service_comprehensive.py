"""
Comprehensive tests for AgentService

Tests all methods with edge cases and error handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, UTC

from server.agent_service import AgentService
from server.models import (
    SimulationRequest,
    SimulationResponse,
    SimulationStep,
    AgentGraph,
    GraphNode,
    GraphEdge,
)
from asdrp.agents.protocol import AgentException


class TestAgentServiceListAgents:
    """Test AgentService.list_agents method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        return Mock()

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService with mocked dependencies."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.list_agents.return_value = ["geo", "finance"]
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    def test_list_agents_success(self, service):
        """Test listing agents successfully."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        mock_config = AgentConfig(
            display_name="GeoAgent",
            module="asdrp.agents.single.geo_agent",
            function="create_geo_agent",
            default_instructions="Geocoding agent instructions",
            model=ModelConfig(name="gpt-4.1-mini", temperature=0.1, max_tokens=2000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        service._config_loader.get_agent_config.return_value = mock_config
        
        agents = service.list_agents()
        
        assert len(agents) == 2
        assert all(isinstance(agent, type(agents[0])) for agent in agents)
        assert all(agent.enabled for agent in agents)

    def test_list_agents_skips_invalid(self, service):
        """Test that invalid agents are skipped."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        valid_config = AgentConfig(
            display_name="GeoAgent",
            module="asdrp.agents.single.geo_agent",
            function="create_geo_agent",
            default_instructions="Instructions",
            model=ModelConfig(name="gpt-4.1-mini", temperature=0.1, max_tokens=2000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        
        def get_config_side_effect(name):
            if name == "geo":
                return valid_config
            else:
                raise AgentException("Invalid config", agent_name=name)
        
        service._config_loader.get_agent_config.side_effect = get_config_side_effect
        
        agents = service.list_agents()
        
        assert len(agents) == 1
        assert agents[0].id == "geo"

    def test_list_agents_sorted(self, service):
        """Test that agents are sorted by display_name."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        config1 = AgentConfig(
            display_name="ZAgent",
            module="test",
            function="create",
            default_instructions="Z",
            model=ModelConfig(name="gpt-4", temperature=0.1, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        config2 = AgentConfig(
            display_name="AAgent",
            module="test",
            function="create",
            default_instructions="A",
            model=ModelConfig(name="gpt-4", temperature=0.1, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        
        def get_config_side_effect(name):
            return config1 if name == "geo" else config2
        
        service._config_loader.get_agent_config.side_effect = get_config_side_effect
        
        agents = service.list_agents()
        
        assert agents[0].display_name == "AAgent"
        assert agents[1].display_name == "ZAgent"


class TestAgentServiceGetAgentDetail:
    """Test AgentService.get_agent_detail method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        factory = Mock()
        mock_agent = Mock()
        mock_agent.name = "GeoAgent"
        mock_agent.tools = [Mock(__name__="geocode"), Mock(name="reverse_geocode")]
        factory.get_agent = AsyncMock(return_value=mock_agent)
        return factory

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    @pytest.mark.asyncio
    async def test_get_agent_detail_success(self, service, mock_factory):
        """Test getting agent detail successfully."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        config = AgentConfig(
            display_name="GeoAgent",
            module="asdrp.agents.single.geo_agent",
            function="create_geo_agent",
            default_instructions="Geocoding agent",
            model=ModelConfig(name="gpt-4.1-mini", temperature=0.1, max_tokens=2000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        service._config_loader.get_agent_config.return_value = config
        
        detail = await service.get_agent_detail("geo")
        
        assert detail.id == "geo"
        assert detail.display_name == "GeoAgent"
        assert detail.model_name == "gpt-4.1-mini"
        assert len(detail.tools) == 2

    @pytest.mark.asyncio
    async def test_get_agent_detail_no_tools(self, service, mock_factory):
        """Test getting agent detail when agent has no tools."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        config = AgentConfig(
            display_name="GeoAgent",
            module="test",
            function="create",
            default_instructions="Test",
            model=ModelConfig(name="gpt-4", temperature=0.1, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        service._config_loader.get_agent_config.return_value = config
        
        mock_agent = Mock()
        mock_agent.tools = None
        mock_factory.get_agent = AsyncMock(return_value=mock_agent)
        
        detail = await service.get_agent_detail("geo")
        
        assert detail.tools == []

    @pytest.mark.asyncio
    async def test_get_agent_detail_tool_extraction_fails(self, service, mock_factory):
        """Test getting agent detail when tool extraction fails."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        config = AgentConfig(
            display_name="GeoAgent",
            module="test",
            function="create",
            default_instructions="Test",
            model=ModelConfig(name="gpt-4", temperature=0.1, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        service._config_loader.get_agent_config.return_value = config
        
        mock_agent = Mock()
        mock_agent.tools = [Mock()]  # Tool without name attributes
        mock_factory.get_agent = AsyncMock(return_value=mock_agent)
        
        detail = await service.get_agent_detail("geo")
        
        # Should still return detail even if tool extraction fails
        assert detail.id == "geo"


class TestAgentServiceSimulateAgent:
    """Test AgentService.simulate_agent method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        factory = Mock()
        mock_agent = Mock()
        mock_agent.name = "GeoAgent"
        factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, None))
        return factory

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    @pytest.mark.asyncio
    async def test_simulate_agent_regular(self, service, mock_factory):
        """Test simulating regular agent."""
        request = SimulationRequest(input="Test input", max_steps=5)
        
        response = await service.simulate_agent("geo", request)
        
        assert isinstance(response, SimulationResponse)
        assert "[MOCK RESPONSE" in response.response
        assert response.metadata["mode"] == "mock"
        assert response.metadata["agent_id"] == "geo"

    @pytest.mark.asyncio
    async def test_simulate_agent_smartrouter(self, service):
        """Test simulating SmartRouter."""
        request = SimulationRequest(input="Test query")
        
        response = await service.simulate_agent("smartrouter", request)
        
        assert isinstance(response, SimulationResponse)
        assert "SmartRouter" in response.response
        assert response.metadata["orchestrator"] == "smartrouter"
        assert response.metadata["mode"] == "mock"

    @pytest.mark.asyncio
    async def test_simulate_agent_with_session(self, service, mock_factory):
        """Test simulating agent with session."""
        request = SimulationRequest(input="Test", session_id="test_session")
        
        response = await service.simulate_agent("geo", request)
        
        assert response.metadata["session_enabled"] is True
        assert response.metadata["session_id"] == "test_session"

    @pytest.mark.asyncio
    async def test_simulate_agent_not_found(self, service, mock_factory):
        """Test simulating non-existent agent."""
        mock_factory.get_agent_with_session = AsyncMock(
            side_effect=AgentException("Agent not found", agent_name="unknown")
        )
        
        request = SimulationRequest(input="Test")
        
        with pytest.raises(AgentException):
            await service.simulate_agent("unknown", request)


class TestAgentServiceChatAgent:
    """Test AgentService.chat_agent method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        factory = Mock()
        mock_agent = Mock()
        mock_agent.name = "GeoAgent"
        factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, None))
        return factory

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    @pytest.mark.asyncio
    async def test_chat_agent_success(self, service, mock_factory):
        """Test chatting with agent successfully."""
        from agents import Runner
        
        mock_result = Mock()
        mock_result.final_output = "Agent response"
        mock_result.trace = None
        
        request = SimulationRequest(input="Test input")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            response = await service.chat_agent("geo", request)
            
            assert isinstance(response, SimulationResponse)
            assert response.response == "Agent response"
            assert response.metadata["mode"] == "real"

    @pytest.mark.asyncio
    async def test_chat_agent_smartrouter(self, service):
        """Test chatting with SmartRouter."""
        request = SimulationRequest(input="Test query")
        
        mock_result = Mock()
        mock_result.answer = "SmartRouter answer"
        mock_result.traces = []
        mock_result.total_time = 1.5
        mock_result.final_decision = "direct"
        mock_result.agents_used = ["geo"]
        mock_result.success = True
        
        with patch('asdrp.orchestration.smartrouter.smartrouter.SmartRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.route_query = AsyncMock(return_value=mock_result)
            mock_router_class.create.return_value = mock_router
            
            response = await service.chat_agent("smartrouter", request)
            
            assert isinstance(response, SimulationResponse)
            assert response.response == "SmartRouter answer"
            assert response.metadata["orchestrator"] == "smartrouter"

    @pytest.mark.asyncio
    async def test_chat_agent_with_mcp_servers(self, service, mock_factory):
        """Test chatting with agent that has MCP servers."""
        from agents import Runner
        from contextlib import AsyncExitStack
        
        mock_agent = Mock()
        mock_agent.name = "MCPAgent"
        mock_mcp_server = AsyncMock()
        mock_mcp_server.__aenter__ = AsyncMock(return_value=mock_mcp_server)
        mock_mcp_server.__aexit__ = AsyncMock(return_value=None)
        mock_agent.mcp_servers = [mock_mcp_server]
        
        mock_factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, None))
        
        mock_result = Mock()
        mock_result.final_output = "MCP response"
        mock_result.trace = None
        
        request = SimulationRequest(input="Test")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)
            
            response = await service.chat_agent("mcp_agent", request)
            
            assert response.response == "MCP response"

    @pytest.mark.asyncio
    async def test_chat_agent_error(self, service, mock_factory):
        """Test chatting with agent that raises error."""
        request = SimulationRequest(input="Test")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run = AsyncMock(side_effect=Exception("Execution error"))
            
            with pytest.raises(AgentException):
                await service.chat_agent("geo", request)


class TestAgentServiceExecuteSmartRouter:
    """Test AgentService._execute_smartrouter method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        return Mock()

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    @pytest.mark.asyncio
    async def test_execute_smartrouter_success(self, service):
        """Test executing SmartRouter successfully."""
        from asdrp.orchestration.smartrouter.trace_capture import SmartRouterExecutionResult
        
        request = SimulationRequest(input="Test query")
        
        mock_result = SmartRouterExecutionResult(
            answer="SmartRouter answer",
            traces=[],
            total_time=1.5,
            final_decision="direct",
            agents_used=["geo"],
            success=True,
        )
        
        with patch('asdrp.orchestration.smartrouter.smartrouter.SmartRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.route_query = AsyncMock(return_value=mock_result)
            mock_router_class.create.return_value = mock_router
            
            response = await service._execute_smartrouter(request)
            
            assert isinstance(response, SimulationResponse)
            assert response.response == "SmartRouter answer"
            assert response.metadata["orchestrator"] == "smartrouter"
            assert "phases" in response.metadata

    @pytest.mark.asyncio
    async def test_execute_smartrouter_with_session(self, service):
        """Test executing SmartRouter with session."""
        request = SimulationRequest(input="Test", session_id="test_session")
        
        mock_result = Mock()
        mock_result.answer = "Answer"
        mock_result.traces = []
        mock_result.total_time = 1.0
        mock_result.final_decision = "direct"
        mock_result.agents_used = []
        mock_result.success = True
        
        with patch('asdrp.orchestration.smartrouter.smartrouter.SmartRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.route_query = AsyncMock(return_value=mock_result)
            mock_router_class.create.return_value = mock_router
            
            response = await service._execute_smartrouter(request)
            
            assert response.metadata["session_id"] == "test_session"

    @pytest.mark.asyncio
    async def test_execute_smartrouter_error(self, service):
        """Test executing SmartRouter with error."""
        request = SimulationRequest(input="Test")
        
        with patch('asdrp.orchestration.smartrouter.smartrouter.SmartRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.create.return_value = mock_router
            mock_router.route_query = AsyncMock(side_effect=Exception("SmartRouter error"))
            mock_router_class.create.return_value = mock_router
            
            with pytest.raises(AgentException):
                await service._execute_smartrouter(request)


class TestAgentServiceGetAgentGraph:
    """Test AgentService.get_agent_graph method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        return Mock()

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.list_agents.return_value = ["geo", "finance"]
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    def test_get_agent_graph_success(self, service):
        """Test getting agent graph successfully."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        config = AgentConfig(
            display_name="GeoAgent",
            module="test",
            function="create",
            default_instructions="Test instructions",
            model=ModelConfig(name="gpt-4", temperature=0.1, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        service._config_loader.get_agent_config.return_value = config
        
        graph = service.get_agent_graph()
        
        assert isinstance(graph, AgentGraph)
        assert len(graph.nodes) == 2
        assert all(isinstance(node, GraphNode) for node in graph.nodes)
        assert all(node.id in ["geo", "finance"] for node in graph.nodes)

    def test_get_agent_graph_skips_invalid(self, service):
        """Test that invalid agents are skipped in graph."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        valid_config = AgentConfig(
            display_name="GeoAgent",
            module="test",
            function="create",
            default_instructions="Test",
            model=ModelConfig(name="gpt-4", temperature=0.1, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        
        def get_config_side_effect(name):
            if name == "geo":
                return valid_config
            else:
                raise AgentException("Invalid", agent_name=name)
        
        service._config_loader.get_agent_config.side_effect = get_config_side_effect
        
        graph = service.get_agent_graph()
        
        assert len(graph.nodes) == 1
        assert graph.nodes[0].id == "geo"

    def test_get_agent_graph_layout(self, service):
        """Test that graph nodes have proper layout positions."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig
        
        config = AgentConfig(
            display_name="Agent",
            module="test",
            function="create",
            default_instructions="Test",
            model=ModelConfig(name="gpt-4", temperature=0.1, max_tokens=1000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )
        service._config_loader.get_agent_config.return_value = config
        
        graph = service.get_agent_graph()
        
        for node in graph.nodes:
            assert "x" in node.position
            assert "y" in node.position
            assert isinstance(node.position["x"], (int, float))
            assert isinstance(node.position["y"], (int, float))


class TestAgentServiceValidateConfig:
    """Test AgentService.validate_config method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        return Mock()

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    def test_validate_config_valid(self, service):
        """Test validating valid YAML config."""
        valid_yaml = """
agents:
  geo:
    display_name: "GeoAgent"
    module: "asdrp.agents.single.geo_agent"
    function: "create_geo_agent"
"""
        
        is_valid, error = service.validate_config(valid_yaml)
        
        assert is_valid is True
        assert error is None

    def test_validate_config_invalid_yaml(self, service):
        """Test validating invalid YAML syntax."""
        invalid_yaml = "invalid: yaml: ["
        
        is_valid, error = service.validate_config(invalid_yaml)
        
        assert is_valid is False
        assert error is not None
        assert "YAML parse error" in error

    def test_validate_config_not_dict(self, service):
        """Test validating YAML that's not a dictionary."""
        invalid_yaml = "- item1\n- item2"
        
        is_valid, error = service.validate_config(invalid_yaml)
        
        assert is_valid is False
        assert "must be a dictionary" in error

    def test_validate_config_missing_agents_key(self, service):
        """Test validating config without agents key."""
        invalid_yaml = "settings:\n  debug: true"
        
        is_valid, error = service.validate_config(invalid_yaml)
        
        assert is_valid is False
        assert "Missing 'agents' key" in error

    def test_validate_config_agents_not_dict(self, service):
        """Test validating config where agents is not a dictionary."""
        invalid_yaml = "agents: []"
        
        is_valid, error = service.validate_config(invalid_yaml)
        
        assert is_valid is False
        assert "must be a dictionary" in error

    def test_validate_config_missing_required_fields(self, service):
        """Test validating config with missing required fields."""
        invalid_yaml = """
agents:
  geo:
    display_name: "GeoAgent"
    # Missing module and function
"""
        
        is_valid, error = service.validate_config(invalid_yaml)
        
        assert is_valid is False
        assert "missing required field" in error.lower()


class TestAgentServiceChatAgentStreaming:
    """Test AgentService.chat_agent_streaming method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        factory = Mock()
        mock_agent = Mock()
        mock_agent.name = "GeoAgent"
        factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, None))
        return factory

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    @pytest.mark.asyncio
    async def test_chat_agent_streaming_success(self, service, mock_factory):
        """Test streaming agent response successfully."""
        from agents import Runner
        
        async def mock_stream():
            yield "Hello"
            yield " World"
        
        request = SimulationRequest(input="Test")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run_streamed = mock_stream
            
            chunks = []
            async for chunk in service.chat_agent_streaming("geo", request):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            assert chunks[0].type == "metadata"
            assert any(chunk.type == "token" for chunk in chunks)
            assert any(chunk.type == "done" for chunk in chunks)

    @pytest.mark.asyncio
    async def test_chat_agent_streaming_smartrouter(self, service):
        """Test streaming SmartRouter response."""
        request = SimulationRequest(input="Test query")
        
        mock_response = SimulationResponse(
            response="SmartRouter answer",
            trace=[],
            metadata={"orchestrator": "smartrouter"}
        )
        
        with patch.object(service, '_execute_smartrouter', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response
            
            chunks = []
            async for chunk in service.chat_agent_streaming("smartrouter", request):
                chunks.append(chunk)
            
            assert len(chunks) >= 3  # metadata, token, done
            assert chunks[0].type == "metadata"
            assert chunks[0].metadata["orchestrator"] == "smartrouter"

    @pytest.mark.asyncio
    async def test_chat_agent_streaming_error(self, service, mock_factory):
        """Test streaming agent response with error."""
        request = SimulationRequest(input="Test")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run_streamed = AsyncMock(side_effect=Exception("Stream error"))
            
            chunks = []
            async for chunk in service.chat_agent_streaming("geo", request):
                chunks.append(chunk)
            
            error_chunks = [c for c in chunks if c.type == "error"]
            assert len(error_chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_agent_streaming_agent_not_found(self, service, mock_factory):
        """Test streaming when agent not found."""
        request = SimulationRequest(input="Test")
        
        mock_factory.get_agent_with_session = AsyncMock(
            side_effect=AgentException("Agent not found", agent_name="unknown")
        )
        
        chunks = []
        async for chunk in service.chat_agent_streaming("unknown", request):
            chunks.append(chunk)
        
        error_chunks = [c for c in chunks if c.type == "error"]
        assert len(error_chunks) > 0


class TestAgentServiceReloadConfig:
    """Test AgentService.reload_config method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        factory = Mock()
        factory.clear_session_cache = Mock()
        return factory

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.reload_config = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    def test_reload_config(self, service, mock_factory):
        """Test reloading configuration."""
        service.reload_config()
        
        service._config_loader.reload_config.assert_called_once()
        mock_factory.clear_session_cache.assert_called_once()

