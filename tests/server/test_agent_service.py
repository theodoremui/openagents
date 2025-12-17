"""Tests for AgentService."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from server.agent_service import AgentService
from server.models import SimulationRequest
from asdrp.agents.protocol import AgentException


class TestAgentService:
    """Tests for AgentService class."""

    @pytest.fixture
    def mock_factory(self):
        """Create a mock AgentFactory."""
        factory = Mock()
        return factory

    @pytest.fixture
    def service(self, mock_factory):
        """Create an AgentService instance with mocked factory."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.list_agents.return_value = ["geo", "finance", "map"]
            mock_loader_class.return_value = mock_loader

            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader

            yield service

    def test_list_agents(self, service):
        """Test listing all agents."""
        # Mock config for each agent
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig

        mock_config = AgentConfig(
            display_name="GeoAgent",
            module="asdrp.agents.single.geo_agent",
            function="create_geo_agent",
            default_instructions="Geocoding agent",
            model=ModelConfig(name="gpt-4", temperature=0.7, max_tokens=2000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )

        service._config_loader.get_agent_config.return_value = mock_config

        agents = service.list_agents()

        assert len(agents) == 3
        assert all(agent.enabled for agent in agents)

    def test_get_agent_detail(self, service):
        """Test getting detailed agent information."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig

        mock_config = AgentConfig(
            display_name="FinanceAgent",
            module="asdrp.agents.single.finance_agent",
            function="create_finance_agent",
            default_instructions="Financial data agent",
            model=ModelConfig(name="gpt-4.1-mini", temperature=0.1, max_tokens=2000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )

        service._config_loader.get_agent_config.return_value = mock_config

        detail = service.get_agent_detail("finance")

        assert detail.id == "finance"
        assert detail.display_name == "FinanceAgent"
        assert detail.model_name == "gpt-4.1-mini"
        assert detail.temperature == 0.1

    def test_get_agent_detail_not_found(self, service):
        """Test getting detail for non-existent agent."""
        service._config_loader.get_agent_config.side_effect = AgentException(
            "Agent not found"
        )

        with pytest.raises(AgentException):
            service.get_agent_detail("unknown")

    @pytest.mark.asyncio
    async def test_simulate_agent(self, service, mock_factory):
        """Test agent simulation."""
        # Mock agent and session
        mock_agent = Mock()
        mock_agent.name = "GeoAgent"
        mock_session = Mock()

        mock_factory.get_agent_with_session = AsyncMock(
            return_value=(mock_agent, mock_session)
        )

        request = SimulationRequest(input="Test input", max_steps=5)
        response = await service.simulate_agent("geo", request)

        assert response.response is not None
        assert len(response.trace) > 0
        assert response.metadata["agent_id"] == "geo"

        # Verify factory was called correctly
        mock_factory.get_agent_with_session.assert_called_once()

    def test_get_agent_graph(self, service):
        """Test generating agent graph."""
        from asdrp.agents.config_loader import AgentConfig, ModelConfig, SessionMemoryConfig

        mock_config = AgentConfig(
            display_name="TestAgent",
            module="test.module",
            function="create_agent",
            default_instructions="Test instructions",
            model=ModelConfig(name="gpt-4", temperature=0.7, max_tokens=2000),
            session_memory=SessionMemoryConfig(type="sqlite", enabled=True),
            enabled=True,
        )

        service._config_loader.get_agent_config.return_value = mock_config

        graph = service.get_agent_graph()

        assert len(graph.nodes) == 3  # geo, finance, map
        assert all(node.id in ["geo", "finance", "map"] for node in graph.nodes)

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
        invalid_yaml = """
agents:
  geo:
    display_name: "GeoAgent
    invalid syntax here
"""

        is_valid, error = service.validate_config(invalid_yaml)

        assert is_valid is False
        assert error is not None
        assert "YAML parse error" in error

    def test_validate_config_missing_agents(self, service):
        """Test validating config without agents key."""
        invalid_yaml = """
settings:
  debug: true
"""

        is_valid, error = service.validate_config(invalid_yaml)

        assert is_valid is False
        assert "Missing 'agents' key" in error

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

    def test_reload_config(self, service, mock_factory):
        """Test reloading configuration."""
        service._config_loader.reload_config = Mock()
        mock_factory.clear_session_cache = Mock()

        service.reload_config()

        service._config_loader.reload_config.assert_called_once()
        mock_factory.clear_session_cache.assert_called_once()
