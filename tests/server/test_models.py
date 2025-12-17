"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from server.models import (
    AgentListItem,
    AgentDetail,
    SimulationRequest,
    SimulationResponse,
    SimulationStep,
    GraphNode,
    GraphEdge,
    AgentGraph,
    ConfigUpdate,
)


class TestAgentModels:
    """Tests for agent-related models."""

    def test_agent_list_item_valid(self):
        """Test creating a valid AgentListItem."""
        agent = AgentListItem(
            id="geo",
            name="geo",
            display_name="GeoAgent",
            description="A geocoding agent",
            enabled=True,
        )

        assert agent.id == "geo"
        assert agent.name == "geo"
        assert agent.display_name == "GeoAgent"
        assert agent.enabled is True

    def test_agent_list_item_frozen(self):
        """Test that AgentListItem is immutable."""
        agent = AgentListItem(
            id="geo", name="geo", display_name="GeoAgent", enabled=True
        )

        with pytest.raises(ValidationError):
            agent.name = "new_name"

    def test_agent_detail_valid(self):
        """Test creating a valid AgentDetail."""
        agent = AgentDetail(
            id="finance",
            name="finance",
            display_name="FinanceAgent",
            description="Financial data agent",
            module="asdrp.agents.single.finance_agent",
            function="create_finance_agent",
            model_name="gpt-4.1-mini",
            temperature=0.1,
            max_tokens=2000,
            tools=["yfinance", "alpha_vantage"],
            edges=["reporter"],
            enabled=True,
        )

        assert agent.id == "finance"
        assert agent.model_name == "gpt-4.1-mini"
        assert agent.temperature == 0.1
        assert len(agent.tools) == 2


class TestSimulationModels:
    """Tests for simulation-related models."""

    def test_simulation_request_valid(self):
        """Test creating a valid SimulationRequest."""
        request = SimulationRequest(input="What is the weather today?", max_steps=5)

        assert request.input == "What is the weather today?"
        assert request.max_steps == 5
        assert request.context is None

    def test_simulation_request_with_context(self):
        """Test SimulationRequest with context."""
        request = SimulationRequest(
            input="Test input", context={"user_id": "123", "session": "abc"}
        )

        assert request.context == {"user_id": "123", "session": "abc"}

    def test_simulation_request_validation_empty_input(self):
        """Test that empty input is rejected."""
        with pytest.raises(ValidationError):
            SimulationRequest(input="")

    def test_simulation_request_validation_max_steps(self):
        """Test max_steps validation."""
        with pytest.raises(ValidationError):
            SimulationRequest(input="test", max_steps=0)

        with pytest.raises(ValidationError):
            SimulationRequest(input="test", max_steps=101)

    def test_simulation_step_valid(self):
        """Test creating a valid SimulationStep."""
        step = SimulationStep(
            agent_id="geo",
            agent_name="GeoAgent",
            action="geocode",
            output="Coordinates: 37.7749, -122.4194",
        )

        assert step.agent_id == "geo"
        assert step.agent_name == "GeoAgent"
        assert step.action == "geocode"

    def test_simulation_response_valid(self):
        """Test creating a valid SimulationResponse."""
        response = SimulationResponse(
            response="The location is San Francisco",
            trace=[
                SimulationStep(
                    agent_id="geo",
                    agent_name="GeoAgent",
                    action="geocode",
                    output="Found coordinates",
                )
            ],
            metadata={"duration": 1.23, "tokens": 50},
        )

        assert response.response == "The location is San Francisco"
        assert len(response.trace) == 1
        assert response.metadata["duration"] == 1.23


class TestGraphModels:
    """Tests for graph visualization models."""

    def test_graph_node_valid(self):
        """Test creating a valid GraphNode."""
        node = GraphNode(
            id="agent1",
            type="default",
            data={"label": "Agent 1", "type": "worker"},
            position={"x": 100, "y": 200},
        )

        assert node.id == "agent1"
        assert node.data["label"] == "Agent 1"
        assert node.position["x"] == 100

    def test_graph_edge_valid(self):
        """Test creating a valid GraphEdge."""
        edge = GraphEdge(id="edge1", source="agent1", target="agent2", type="default")

        assert edge.id == "edge1"
        assert edge.source == "agent1"
        assert edge.target == "agent2"

    def test_agent_graph_valid(self):
        """Test creating a valid AgentGraph."""
        graph = AgentGraph(
            nodes=[
                GraphNode(
                    id="agent1",
                    data={"label": "Agent 1"},
                    position={"x": 0, "y": 0},
                ),
                GraphNode(
                    id="agent2",
                    data={"label": "Agent 2"},
                    position={"x": 100, "y": 100},
                ),
            ],
            edges=[GraphEdge(id="e1", source="agent1", target="agent2")],
        )

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1


class TestConfigModels:
    """Tests for configuration models."""

    def test_config_update_valid(self):
        """Test creating a valid ConfigUpdate."""
        update = ConfigUpdate(content="agents:\n  geo:\n    enabled: true")

        assert "agents:" in update.content
        assert update.validate_only is False

    def test_config_update_validation_only(self):
        """Test ConfigUpdate with validate_only flag."""
        update = ConfigUpdate(content="test: value", validate_only=True)

        assert update.validate_only is True

    def test_config_update_empty_content(self):
        """Test that empty content is rejected."""
        with pytest.raises(ValidationError):
            ConfigUpdate(content="")
