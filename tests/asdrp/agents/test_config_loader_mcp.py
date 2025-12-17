#############################################################################
# test_config_loader_mcp.py
#
# Tests for MCPServerConfig and MCP configuration loading.
#
# Test Coverage:
# - MCPServerConfig dataclass creation and validation
# - MCP configuration parsing from YAML
# - Default value handling
# - Validation errors for invalid configs
# - Integration with AgentConfig
#
#############################################################################

import pytest
from pathlib import Path

from asdrp.agents.config_loader import (
    MCPServerConfig,
    AgentConfig,
    ModelConfig,
    SessionMemoryConfig,
)


class TestMCPServerConfig:
    """Test MCPServerConfig dataclass."""

    def test_create_with_defaults(self):
        """Test creating MCPServerConfig with default values."""
        config = MCPServerConfig()

        assert config.enabled is False
        assert config.command is None
        assert config.working_directory is None
        assert config.env is None
        assert config.transport == "stdio"
        assert config.host is None
        assert config.port is None

    def test_create_stdio_config(self):
        """Test creating valid stdio transport config."""
        config = MCPServerConfig(
            enabled=True,
            command=["uv", "run", "mcp-yelp-agent"],
            working_directory="yelp-mcp",
            env={"YELP_API_KEY": "test-key"},
            transport="stdio"
        )

        assert config.enabled is True
        assert config.command == ["uv", "run", "mcp-yelp-agent"]
        assert config.working_directory == "yelp-mcp"
        assert config.env == {"YELP_API_KEY": "test-key"}
        assert config.transport == "stdio"

    def test_create_http_config(self):
        """Test creating valid HTTP transport config."""
        config = MCPServerConfig(
            enabled=True,
            command=["python", "server.py"],
            transport="streamable-http",
            host="localhost",
            port=8080
        )

        assert config.enabled is True
        assert config.transport == "streamable-http"
        assert config.host == "localhost"
        assert config.port == 8080

    def test_invalid_transport_raises_error(self):
        """Test that invalid transport raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MCPServerConfig(
                enabled=True,
                command=["test"],
                transport="invalid-transport"
            )

        assert "transport must be one of" in str(exc_info.value)

    def test_enabled_without_command_raises_error(self):
        """Test that enabled=True without command raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MCPServerConfig(
                enabled=True,
                command=None,
                transport="stdio"
            )

        assert "command is required when MCP is enabled" in str(exc_info.value)

    def test_http_without_host_raises_error(self):
        """Test that HTTP transport without host raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MCPServerConfig(
                enabled=True,
                command=["test"],
                transport="streamable-http",
                port=8080
                # missing host
            )

        assert "host and port are required" in str(exc_info.value)

    def test_sse_without_port_raises_error(self):
        """Test that SSE transport without port raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            MCPServerConfig(
                enabled=True,
                command=["test"],
                transport="sse",
                host="localhost"
                # missing port
            )

        assert "host and port are required" in str(exc_info.value)


class TestAgentConfigWithMCP:
    """Test AgentConfig integration with MCP configuration."""

    def test_agent_config_without_mcp(self):
        """Test AgentConfig without MCP configuration."""
        config = AgentConfig(
            display_name="TestAgent",
            module="test.module",
            function="create_agent",
            default_instructions="Test instructions",
            model=ModelConfig(name="gpt-4"),
            session_memory=SessionMemoryConfig(),
            mcp_server=None,
            enabled=True
        )

        assert config.mcp_server is None

    def test_agent_config_with_mcp(self):
        """Test AgentConfig with MCP configuration."""
        mcp_config = MCPServerConfig(
            enabled=True,
            command=["uv", "run", "mcp-test"],
            transport="stdio"
        )

        config = AgentConfig(
            display_name="TestAgent",
            module="test.module",
            function="create_agent",
            default_instructions="Test instructions",
            model=ModelConfig(name="gpt-4"),
            session_memory=SessionMemoryConfig(),
            mcp_server=mcp_config,
            enabled=True
        )

        assert config.mcp_server is not None
        assert config.mcp_server.enabled is True
        assert config.mcp_server.command == ["uv", "run", "mcp-test"]


class TestMCPConfigValidation:
    """Test MCP configuration validation logic."""

    def test_disabled_mcp_allows_missing_command(self):
        """Test that disabled MCP doesn't require command."""
        config = MCPServerConfig(
            enabled=False,
            command=None,
            transport="stdio"
        )

        # Should not raise
        assert config.enabled is False
        assert config.command is None

    def test_stdio_allows_missing_host_port(self):
        """Test that stdio transport doesn't require host/port."""
        config = MCPServerConfig(
            enabled=True,
            command=["test"],
            transport="stdio"
            # No host/port needed
        )

        # Should not raise
        assert config.transport == "stdio"
        assert config.host is None
        assert config.port is None
