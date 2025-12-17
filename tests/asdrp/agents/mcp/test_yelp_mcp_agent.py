#############################################################################
# test_yelp_mcp_agent.py
#
# Comprehensive tests for YelpMCPAgent implementation.
#
# Test Coverage:
# - Agent creation with default and custom instructions
# - MCP server configuration handling
# - Model configuration application
# - Protocol compliance (AgentProtocol interface)
# - MCP tool integration
# - Error handling (ImportError, config errors)
# - Edge cases (missing API key, invalid configs)
# - Default instructions constant
#
# Design Principles:
# - Single Responsibility: Each test class focuses on one aspect
# - DRY: Shared fixtures and helper methods
# - Isolation: Mock MCP server interactions
# - Extensibility: Easy to add new test cases
# - Robustness: Comprehensive error and edge case coverage
#
# IMPORTANT TESTING NOTES:
# ------------------------
# 1. Import Location Matters: The yelp_mcp_agent.py module imports Agent,
#    ModelSettings, and MCPServerStdio INSIDE the create_yelp_mcp_agent()
#    function (not at module level). This enables proper mocking during tests.
#    Tests must patch at "agents.Agent" level, not
#    "asdrp.agents.mcp.yelp_mcp_agent.Agent".
#
# 2. Generic Type Syntax: The implementation uses Agent[Any](**kwargs) which
#    creates a two-step call:
#    - Step 1: Agent.__getitem__(Any) returns a callable
#    - Step 2: That callable is invoked with (**kwargs)
#    Tests must configure mock_agent.__getitem__.return_value to handle this.
#
# 3. MCPServerStdio API Format: Uses OpenAI agents MCP documentation pattern:
#    MCPServerStdio(name="YelpMCP", params={command, args, env, cwd})
#    Tests must check params["command"] and params["args"], not command directly.
#
# 4. Exception Handling: To test exception wrapping, mock all imports that
#    happen inside create_yelp_mcp_agent() to ensure exceptions occur in the
#    try-except block scope.
#
#############################################################################

import pytest
import os
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from typing import Any

from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
from asdrp.agents.mcp.yelp_mcp_agent import (
    create_yelp_mcp_agent,
    DEFAULT_INSTRUCTIONS,
)


class TestYelpMCPAgentCreation:
    """Test YelpMCPAgent creation functionality."""

    @pytest.fixture
    def mock_mcp_server_config(self):
        """Create a valid MCP server configuration."""
        return MCPServerConfig(
            enabled=True,
            command=["uv", "run", "mcp-yelp-agent"],
            working_directory="yelp-mcp",
            env={"YELP_API_KEY": "test-api-key"},
            transport="stdio"
        )

    @pytest.fixture
    def mock_env_with_yelp_key(self, monkeypatch):
        """Set YELP_API_KEY in environment."""
        monkeypatch.setenv("YELP_API_KEY", "test-yelp-key")

    @pytest.fixture
    def mock_agent_imports(self):
        """Mock agents library imports."""
        # Patch at the agents module level since imports happen inside the function
        with patch("agents.Agent") as mock_agent, \
             patch("agents.ModelSettings") as mock_settings, \
             patch("agents.mcp.MCPServerStdio") as mock_mcp:

            # Configure mock agent
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "YelpMCPAgent"
            mock_agent_instance.instructions = DEFAULT_INSTRUCTIONS

            # Handle Agent[Any] generic type syntax
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)
            mock_agent.return_value = mock_agent_instance

            # Configure mock MCP server
            mock_mcp_instance = MagicMock()
            mock_mcp.return_value = mock_mcp_instance

            yield {
                "Agent": mock_agent,
                "ModelSettings": mock_settings,
                "MCPServerStdio": mock_mcp,
                "agent_instance": mock_agent_instance,
                "mcp_instance": mock_mcp_instance
            }

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists() to return True."""
        with patch.object(Path, "exists", return_value=True):
            yield

    def test_default_instructions_constant_exists(self):
        """Test that DEFAULT_INSTRUCTIONS is defined."""
        assert DEFAULT_INSTRUCTIONS is not None
        assert isinstance(DEFAULT_INSTRUCTIONS, str)
        assert len(DEFAULT_INSTRUCTIONS) > 0
        assert "YelpMCPAgent" in DEFAULT_INSTRUCTIONS
        assert "yelp_agent" in DEFAULT_INSTRUCTIONS

    def test_create_with_default_instructions(
        self,
        mock_env_with_yelp_key,
        mock_agent_imports,
        mock_path_exists,
        mock_mcp_server_config
    ):
        """Test agent creation with default instructions."""
        agent = create_yelp_mcp_agent(mcp_server_config=mock_mcp_server_config)

        assert agent is not None
        assert agent.name == "YelpMCPAgent"
        assert agent.instructions == DEFAULT_INSTRUCTIONS
        assert isinstance(agent, AgentProtocol)

    def test_create_with_custom_instructions(
        self,
        mock_env_with_yelp_key,
        mock_agent_imports,
        mock_path_exists,
        mock_mcp_server_config
    ):
        """Test agent creation with custom instructions."""
        custom_instructions = "You are a specialized Yelp restaurant expert."

        mocks = mock_agent_imports
        mocks["agent_instance"].instructions = custom_instructions

        agent = create_yelp_mcp_agent(
            instructions=custom_instructions,
            mcp_server_config=mock_mcp_server_config
        )

        assert agent is not None
        assert agent.name == "YelpMCPAgent"

        # Verify Agent[Any] was called with custom instructions
        # Agent[Any](**kwargs) calls Agent.__getitem__(Any) then calls the result
        mock_agent_generic = mocks["Agent"].__getitem__.return_value
        mock_agent_generic.assert_called_once()
        call_kwargs = mock_agent_generic.call_args[1]
        assert call_kwargs["instructions"] == custom_instructions

    def test_create_with_model_config(
        self,
        mock_env_with_yelp_key,
        mock_agent_imports,
        mock_path_exists,
        mock_mcp_server_config
    ):
        """Test agent creation with model configuration."""
        model_config = ModelConfig(
            name="gpt-4.1-mini",
            temperature=0.8,
            max_tokens=3000
        )

        mocks = mock_agent_imports
        agent = create_yelp_mcp_agent(
            model_config=model_config,
            mcp_server_config=mock_mcp_server_config
        )

        assert agent is not None

        # Verify model configuration was applied
        # Agent[Any](**kwargs) calls Agent.__getitem__(Any) then calls the result
        mock_agent_generic = mocks["Agent"].__getitem__.return_value
        mock_agent_generic.assert_called_once()
        call_kwargs = mock_agent_generic.call_args[1]
        assert call_kwargs["model"] == "gpt-4.1-mini"
        assert "model_settings" in call_kwargs

        # Verify ModelSettings was called
        mocks["ModelSettings"].assert_called_once_with(
            temperature=0.8,
            max_tokens=3000
        )


class TestYelpMCPAgentConfiguration:
    """Test MCP server configuration handling."""

    @pytest.fixture
    def mock_env_with_yelp_key(self, monkeypatch):
        """Set YELP_API_KEY in environment."""
        monkeypatch.setenv("YELP_API_KEY", "test-yelp-key")

    @pytest.fixture
    def mock_agent_imports(self):
        """Mock agents library imports."""
        # Patch at the agents module level since imports happen inside the function
        with patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio") as mock_mcp:

            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "YelpMCPAgent"

            # Handle Agent[Any] generic type syntax
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)
            mock_agent.return_value = mock_agent_instance

            mock_mcp_instance = MagicMock()
            mock_mcp.return_value = mock_mcp_instance

            yield {
                "Agent": mock_agent,
                "MCPServerStdio": mock_mcp,
                "mcp_instance": mock_mcp_instance
            }

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists() to return True."""
        with patch.object(Path, "exists", return_value=True):
            yield

    def test_default_mcp_config_used_when_none_provided(
        self,
        mock_env_with_yelp_key,
        mock_agent_imports,
        mock_path_exists
    ):
        """Test that default MCP config is used when none provided."""
        agent = create_yelp_mcp_agent()

        assert agent is not None

        # Verify MCPServerStdio was called with default config
        mocks = mock_agent_imports
        mocks["MCPServerStdio"].assert_called_once()
        call_kwargs = mocks["MCPServerStdio"].call_args[1]

        # Check for new API format with name and params
        assert "name" in call_kwargs
        assert call_kwargs["name"] == "YelpMCP"
        assert "params" in call_kwargs
        assert call_kwargs["params"]["command"] == "uv"
        assert call_kwargs["params"]["args"] == ["run", "mcp-yelp-agent"]
        assert "YELP_API_KEY" in call_kwargs["params"]["env"]
        assert call_kwargs["params"]["env"]["YELP_API_KEY"] == "test-yelp-key"

    def test_custom_mcp_config_is_used(
        self,
        mock_env_with_yelp_key,
        mock_agent_imports,
        mock_path_exists
    ):
        """Test that custom MCP config is applied."""
        custom_config = MCPServerConfig(
            enabled=True,
            command=["custom", "command"],
            working_directory="/custom/path",
            env={"CUSTOM_VAR": "custom_value", "YELP_API_KEY": "custom-key"},
            transport="stdio"
        )

        with patch.object(Path, "exists", return_value=True):
            agent = create_yelp_mcp_agent(mcp_server_config=custom_config)

        assert agent is not None

        # Verify custom config was used
        mocks = mock_agent_imports
        mocks["MCPServerStdio"].assert_called_once()
        call_kwargs = mocks["MCPServerStdio"].call_args[1]

        # Check for new API format with name and params
        assert "name" in call_kwargs
        assert "params" in call_kwargs
        assert call_kwargs["params"]["command"] == "custom"
        assert call_kwargs["params"]["args"] == ["command"]
        assert "CUSTOM_VAR" in call_kwargs["params"]["env"]

    def test_mcp_disabled_raises_exception(self, mock_agent_imports):
        """Test that disabled MCP config raises AgentException."""
        disabled_config = MCPServerConfig(
            enabled=False,
            command=["test"],
            transport="stdio"
        )

        with pytest.raises(AgentException) as exc_info:
            create_yelp_mcp_agent(mcp_server_config=disabled_config)

        assert "must be enabled" in str(exc_info.value)

    def test_non_stdio_transport_raises_exception(self, mock_agent_imports, mock_path_exists):
        """Test that non-stdio transport raises AgentException."""
        http_config = MCPServerConfig(
            enabled=True,
            command=["test"],
            transport="streamable-http",
            host="localhost",
            port=8080
        )

        with pytest.raises(AgentException) as exc_info:
            create_yelp_mcp_agent(mcp_server_config=http_config)

        assert "only supports stdio transport" in str(exc_info.value)

    def test_missing_yelp_api_key_raises_exception(self, monkeypatch, mock_agent_imports):
        """Test that missing YELP_API_KEY raises AgentException."""
        # Remove YELP_API_KEY from environment
        monkeypatch.delenv("YELP_API_KEY", raising=False)

        with pytest.raises(AgentException) as exc_info:
            create_yelp_mcp_agent()

        assert "YELP_API_KEY" in str(exc_info.value)
        assert "required" in str(exc_info.value)

    def test_nonexistent_working_directory_raises_exception(
        self,
        mock_env_with_yelp_key,
        mock_agent_imports
    ):
        """Test that nonexistent working directory raises AgentException."""
        config = MCPServerConfig(
            enabled=True,
            command=["test"],
            working_directory="/nonexistent/path",
            transport="stdio"
        )

        with pytest.raises(AgentException) as exc_info:
            create_yelp_mcp_agent(mcp_server_config=config)

        assert "working directory does not exist" in str(exc_info.value)


class TestYelpMCPAgentMCPIntegration:
    """Test MCP server integration."""

    @pytest.fixture
    def mock_env_with_yelp_key(self, monkeypatch):
        """Set YELP_API_KEY in environment."""
        monkeypatch.setenv("YELP_API_KEY", "test-yelp-key")

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists() to return True."""
        with patch.object(Path, "exists", return_value=True):
            yield

    def test_mcp_server_passed_as_tool(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that MCP server is passed via mcp_servers parameter to the agent."""
        with patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio") as mock_mcp:

            mock_agent_instance = MagicMock()
            # Handle Agent[Any] generic type syntax
            mock_agent_generic = MagicMock(return_value=mock_agent_instance)
            mock_agent.__getitem__.return_value = mock_agent_generic

            mock_mcp_instance = MagicMock()
            mock_mcp.return_value = mock_mcp_instance

            agent = create_yelp_mcp_agent()

            # Verify Agent[Any] was called with MCP server in mcp_servers
            mock_agent_generic.assert_called_once()
            call_kwargs = mock_agent_generic.call_args[1]
            assert "mcp_servers" in call_kwargs
            assert mock_mcp_instance in call_kwargs["mcp_servers"]


class TestYelpMCPAgentErrorHandling:
    """Test error handling in agent creation."""

    @pytest.fixture
    def mock_env_with_yelp_key(self, monkeypatch):
        """Set YELP_API_KEY in environment."""
        monkeypatch.setenv("YELP_API_KEY", "test-yelp-key")

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists() to return True."""
        with patch.object(Path, "exists", return_value=True):
            yield

    def test_import_error_raises_agent_exception(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that ImportError is wrapped in AgentException."""
        # Patch all imports that happen inside the function to raise ImportError
        with patch("agents.Agent", side_effect=ImportError("Test import error")), \
             patch("agents.ModelSettings", side_effect=ImportError("Test import error")), \
             patch("agents.mcp.MCPServerStdio", side_effect=ImportError("Test import error")):
            with pytest.raises(AgentException) as exc_info:
                create_yelp_mcp_agent()

            assert "Failed to import" in str(exc_info.value)
            assert "openai-agents>=0.5.1" in str(exc_info.value)

    def test_generic_exception_raises_agent_exception(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that generic exceptions are wrapped in AgentException."""
        # Patch Agent to raise RuntimeError when __getitem__ is called (for Agent[Any] syntax)
        with patch("agents.Agent") as mock_agent, \
             patch("agents.ModelSettings"), \
             patch("agents.mcp.MCPServerStdio"):
            # Configure __getitem__ to raise RuntimeError
            mock_agent.__getitem__.side_effect = RuntimeError("Test error")

            with pytest.raises(AgentException) as exc_info:
                create_yelp_mcp_agent()

            assert "Failed to create YelpMCPAgent" in str(exc_info.value)
            assert exc_info.value.agent_name == "yelp_mcp"


class TestYelpMCPAgentProtocolCompliance:
    """Test AgentProtocol compliance."""

    @pytest.fixture
    def mock_env_with_yelp_key(self, monkeypatch):
        """Set YELP_API_KEY in environment."""
        monkeypatch.setenv("YELP_API_KEY", "test-yelp-key")

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists() to return True."""
        with patch.object(Path, "exists", return_value=True):
            yield

    def test_agent_implements_protocol(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that created agent implements AgentProtocol."""
        with patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio"), \
             patch("asdrp.actions.geo.map_tools.MapTools"):

            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "YelpMCPAgent"
            mock_agent_instance.instructions = DEFAULT_INSTRUCTIONS
            # Handle Agent[Any] generic type syntax
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)
            mock_agent.return_value = mock_agent_instance

            agent = create_yelp_mcp_agent()

            assert isinstance(agent, AgentProtocol)
            assert hasattr(agent, "name")
            assert hasattr(agent, "instructions")
            assert agent.name == "YelpMCPAgent"


class TestYelpMCPAgentMapIntegration:
    """Test MapTools integration with YelpMCPAgent."""

    @pytest.fixture
    def mock_env_with_yelp_key(self, monkeypatch):
        """Set YELP_API_KEY in environment."""
        monkeypatch.setenv("YELP_API_KEY", "test-yelp-key")

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists() to return True."""
        with patch.object(Path, "exists", return_value=True):
            yield

    def test_agent_has_maptools(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that YelpMCPAgent includes MapTools."""
        with patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio"), \
             patch("asdrp.actions.geo.map_tools.MapTools") as mock_maptools:

            # Configure MapTools mock
            mock_maptools.tool_list = [MagicMock(name="get_interactive_map_data")]

            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "YelpMCPAgent"
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)

            agent = create_yelp_mcp_agent()

            assert agent is not None

            # Verify Agent was called with tools parameter
            mock_agent_generic = mock_agent.__getitem__.return_value
            mock_agent_generic.assert_called_once()
            call_kwargs = mock_agent_generic.call_args[1]

            # Check that tools parameter was passed
            assert "tools" in call_kwargs
            assert call_kwargs["tools"] == mock_maptools.tool_list

    def test_agent_instructions_mention_maps(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that default instructions mention map visualization."""
        with patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio"), \
             patch("asdrp.actions.geo.map_tools.MapTools"):

            mock_agent_instance = MagicMock()
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)

            agent = create_yelp_mcp_agent()

            # Get the instructions that were passed
            mock_agent_generic = mock_agent.__getitem__.return_value
            call_kwargs = mock_agent_generic.call_args[1]
            instructions = call_kwargs["instructions"]

            # Verify instructions mention map capabilities
            assert "MapTools" in instructions
            assert "get_interactive_map_data" in instructions
            assert "interactive map" in instructions.lower()
            assert "map visualization" in instructions.lower()

    def test_agent_instructions_include_map_workflow(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that instructions include complete map generation workflow."""
        with patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio"), \
             patch("asdrp.actions.geo.map_tools.MapTools"):

            mock_agent_instance = MagicMock()
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)

            agent = create_yelp_mcp_agent()

            mock_agent_generic = mock_agent.__getitem__.return_value
            call_kwargs = mock_agent_generic.call_args[1]
            instructions = call_kwargs["instructions"]

            # Verify workflow steps are documented
            assert "Step 1" in instructions
            assert "Step 2" in instructions
            assert "parse" in instructions.lower() or "extract" in instructions.lower()
            assert "coordinates" in instructions.lower()
            assert "markers" in instructions.lower()

    def test_custom_instructions_preserve_map_capability(
        self,
        mock_env_with_yelp_key,
        mock_path_exists
    ):
        """Test that custom instructions still get MapTools."""
        custom_instructions = "You are a specialized restaurant finder."

        with patch("agents.Agent") as mock_agent, \
             patch("agents.mcp.MCPServerStdio"), \
             patch("asdrp.actions.geo.map_tools.MapTools") as mock_maptools:

            mock_maptools.tool_list = [MagicMock(name="get_interactive_map_data")]
            mock_agent_instance = MagicMock()
            mock_agent.__getitem__.return_value = MagicMock(return_value=mock_agent_instance)

            agent = create_yelp_mcp_agent(instructions=custom_instructions)

            assert agent is not None

            # Verify MapTools still included even with custom instructions
            mock_agent_generic = mock_agent.__getitem__.return_value
            call_kwargs = mock_agent_generic.call_args[1]
            assert "tools" in call_kwargs
            assert call_kwargs["tools"] == mock_maptools.tool_list
            assert call_kwargs["instructions"] == custom_instructions
