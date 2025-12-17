#############################################################################
# test_mcp_server_manager.py
#
# Comprehensive tests for MCPServerManager.
#
# Test Coverage:
# - Singleton pattern behavior
# - Server lifecycle management (start, stop, shutdown_all)
# - Configuration validation
# - Error handling and edge cases
# - Process management and cleanup
# - Multiple server orchestration
#
# Design Principles:
# - Single Responsibility: Each test class focuses on one aspect
# - Isolation: Tests use mocks to avoid actual process spawning
# - Comprehensive: Cover happy paths, errors, and edge cases
# - Robustness: Ensure proper cleanup in all scenarios
#
#############################################################################

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from asdrp.agents.mcp.mcp_server_manager import (
    MCPServerManager,
    get_mcp_manager,
)
from asdrp.agents.config_loader import MCPServerConfig
from asdrp.agents.protocol import AgentException


class TestMCPServerManagerSingleton:
    """Test singleton pattern behavior of MCPServerManager."""

    def test_instance_returns_singleton(self):
        """Verify that instance() returns the same instance."""
        manager1 = MCPServerManager.instance()
        manager2 = MCPServerManager.instance()

        assert manager1 is manager2
        assert isinstance(manager1, MCPServerManager)

    def test_get_mcp_manager_returns_singleton(self):
        """Verify that get_mcp_manager() returns the singleton."""
        manager1 = get_mcp_manager()
        manager2 = get_mcp_manager()
        manager3 = MCPServerManager.instance()

        assert manager1 is manager2
        assert manager1 is manager3


class TestMCPServerManagerStartServer:
    """Test server startup functionality."""

    @pytest.fixture
    def mock_config_stdio(self):
        """Create a mock stdio transport config."""
        return MCPServerConfig(
            enabled=True,
            command=["uv", "run", "mcp-yelp-agent"],
            working_directory="/path/to/yelp-mcp",
            env={"YELP_API_KEY": "test-key"},
            transport="stdio"
        )

    @pytest.fixture
    def mock_config_http(self):
        """Create a mock HTTP transport config."""
        return MCPServerConfig(
            enabled=True,
            command=["python", "server.py"],
            working_directory="/path/to/server",
            transport="streamable-http",
            host="localhost",
            port=8080
        )

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton between tests."""
        MCPServerManager._instance = None
        MCPServerManager._servers = {}
        MCPServerManager._server_configs = {}
        yield
        MCPServerManager._instance = None
        MCPServerManager._servers = {}
        MCPServerManager._server_configs = {}

    @pytest.mark.asyncio
    async def test_start_server_disabled_config_skips(self, mock_config_stdio):
        """Test that disabled servers are skipped."""
        mock_config_stdio.enabled = False
        manager = MCPServerManager.instance()

        await manager.start_server("test-server", mock_config_stdio)

        assert "test-server" not in manager._servers
        assert "test-server" not in manager._server_configs

    @pytest.mark.asyncio
    async def test_start_server_stdio_transport_stores_config(self, mock_config_stdio, tmp_path):
        """Test that stdio transport servers store config without starting process."""
        manager = MCPServerManager.instance()

        # Create a real temp directory for working directory
        work_dir = tmp_path / "yelp-mcp"
        work_dir.mkdir()
        mock_config_stdio.working_directory = str(work_dir)

        await manager.start_server("yelp-mcp", mock_config_stdio, tmp_path)

        # stdio transport doesn't start a long-running process
        assert "yelp-mcp" not in manager._servers
        assert "yelp-mcp" in manager._server_configs
        assert manager._server_configs["yelp-mcp"] == mock_config_stdio

    @pytest.mark.asyncio
    async def test_start_server_http_transport_starts_process(self, mock_config_http, tmp_path):
        """Test that HTTP transport servers start a subprocess."""
        manager = MCPServerManager.instance()

        # Create a real temp directory for working directory
        work_dir = tmp_path / "server"
        work_dir.mkdir()
        mock_config_http.working_directory = str(work_dir)

        # Mock subprocess
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345

        with patch("subprocess.Popen", return_value=mock_process):
            await manager.start_server("http-server", mock_config_http, tmp_path)

        assert "http-server" in manager._servers
        assert manager._servers["http-server"] == mock_process
        assert "http-server" in manager._server_configs

    @pytest.mark.asyncio
    async def test_start_server_missing_command_raises(self):
        """Test that empty command list raises ValueError from MCPServerConfig."""
        # Validation now happens in MCPServerConfig.__post_init__
        with pytest.raises(ValueError) as exc_info:
            config = MCPServerConfig(
                enabled=True,
                command=[],  # Empty command list
                transport="stdio"
            )

        assert "command is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_server_nonexistent_working_directory_raises(self, mock_config_stdio):
        """Test that non-existent working directory raises AgentException."""
        manager = MCPServerManager.instance()
        project_root = Path("/nonexistent")

        with pytest.raises(AgentException) as exc_info:
            await manager.start_server("test", mock_config_stdio, project_root)

        assert "working directory does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_server_already_running_reuses(self, mock_config_http):
        """Test that starting an already running server reuses it."""
        manager = MCPServerManager.instance()

        # Mock a running process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.pid = 12345
        manager._servers["test-server"] = mock_process

        with patch("subprocess.Popen") as mock_popen:
            await manager.start_server("test-server", mock_config_http)

            # Should not create a new process
            mock_popen.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_server_dead_process_restarts(self, mock_config_http, tmp_path):
        """Test that a dead process is restarted."""
        manager = MCPServerManager.instance()

        # Create a real temp directory for working directory
        work_dir = tmp_path / "server"
        work_dir.mkdir()
        mock_config_http.working_directory = str(work_dir)

        # Mock a dead process
        old_process = MagicMock()
        old_process.poll.return_value = 1  # Process died
        manager._servers["test-server"] = old_process

        # Mock new process
        new_process = MagicMock()
        new_process.poll.return_value = None
        new_process.pid = 67890

        with patch("subprocess.Popen", return_value=new_process):
            await manager.start_server("test-server", mock_config_http, tmp_path)

        assert manager._servers["test-server"] == new_process


class TestMCPServerManagerQueries:
    """Test query methods for server status."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton between tests."""
        MCPServerManager._instance = None
        MCPServerManager._servers = {}
        MCPServerManager._server_configs = {}
        yield
        MCPServerManager._instance = None

    def test_get_server_config_returns_config(self):
        """Test that get_server_config returns stored config."""
        manager = MCPServerManager.instance()
        config = MCPServerConfig(
            enabled=True,
            command=["test"],
            transport="stdio"
        )
        manager._server_configs["test"] = config

        result = manager.get_server_config("test")

        assert result == config

    def test_get_server_config_missing_returns_none(self):
        """Test that get_server_config returns None for unknown server."""
        manager = MCPServerManager.instance()

        result = manager.get_server_config("nonexistent")

        assert result is None

    def test_is_server_running_true_for_running_process(self):
        """Test that is_server_running returns True for running process."""
        manager = MCPServerManager.instance()
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Running
        manager._servers["test"] = mock_process

        assert manager.is_server_running("test") is True

    def test_is_server_running_false_for_dead_process(self):
        """Test that is_server_running returns False for dead process."""
        manager = MCPServerManager.instance()
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Dead
        manager._servers["test"] = mock_process

        assert manager.is_server_running("test") is False

    def test_is_server_running_false_for_unknown_server(self):
        """Test that is_server_running returns False for unknown server."""
        manager = MCPServerManager.instance()

        assert manager.is_server_running("nonexistent") is False

    def test_list_servers_returns_all_servers(self):
        """Test that list_servers returns status for all servers."""
        manager = MCPServerManager.instance()

        config1 = MCPServerConfig(enabled=True, command=["cmd1"], transport="stdio")
        config2 = MCPServerConfig(enabled=True, command=["cmd2"], transport="streamable-http", host="localhost", port=8080)

        manager._server_configs["server1"] = config1
        manager._server_configs["server2"] = config2

        # Mock process for server2
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        manager._servers["server2"] = mock_process

        result = manager.list_servers()

        assert "server1" in result
        assert result["server1"]["status"] == "stopped"
        assert result["server1"]["transport"] == "stdio"

        assert "server2" in result
        assert result["server2"]["status"] == "running"
        assert result["server2"]["transport"] == "streamable-http"


class TestMCPServerManagerShutdown:
    """Test server shutdown functionality."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton between tests."""
        MCPServerManager._instance = None
        MCPServerManager._servers = {}
        MCPServerManager._server_configs = {}
        yield
        MCPServerManager._instance = None

    @pytest.mark.asyncio
    async def test_stop_server_terminates_process(self):
        """Test that stop_server terminates the process."""
        manager = MCPServerManager.instance()

        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Running
        mock_process.pid = 12345
        manager._servers["test"] = mock_process

        await manager.stop_server("test")

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()
        assert "test" not in manager._servers

    @pytest.mark.asyncio
    async def test_stop_server_force_kills_if_timeout(self):
        """Test that stop_server force kills if graceful shutdown times out."""
        manager = MCPServerManager.instance()

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = [
            __import__('subprocess').TimeoutExpired("cmd", 5),
            None
        ]
        manager._servers["test"] = mock_process

        await manager.stop_server("test", timeout=0.1)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert "test" not in manager._servers

    @pytest.mark.asyncio
    async def test_stop_server_missing_server_logs_warning(self):
        """Test that stopping a missing server logs warning."""
        manager = MCPServerManager.instance()

        # Should not raise, just log warning
        await manager.stop_server("nonexistent")

    @pytest.mark.asyncio
    async def test_shutdown_all_stops_all_servers(self):
        """Test that shutdown_all stops all running servers."""
        manager = MCPServerManager.instance()

        # Create multiple mock servers
        mock_process1 = MagicMock()
        mock_process1.poll.return_value = None
        mock_process2 = MagicMock()
        mock_process2.poll.return_value = None

        manager._servers["server1"] = mock_process1
        manager._servers["server2"] = mock_process2

        await manager.shutdown_all()

        mock_process1.terminate.assert_called()
        mock_process2.terminate.assert_called()
        assert len(manager._servers) == 0

    @pytest.mark.asyncio
    async def test_shutdown_all_empty_servers_is_safe(self):
        """Test that shutdown_all with no servers is safe."""
        manager = MCPServerManager.instance()

        # Should not raise
        await manager.shutdown_all()

        assert len(manager._servers) == 0
