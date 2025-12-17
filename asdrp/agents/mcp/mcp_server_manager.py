#############################################################################
# mcp_server_manager.py
#
# MCP Server Lifecycle Manager
#
# This module provides centralized management for MCP (Model Context Protocol)
# server processes. It handles:
# - Starting and stopping MCP server subprocesses
# - Process lifecycle management
# - Resource cleanup and error handling
# - Server connection information
#
# Design Principles:
# - Single Responsibility: Only manages MCP server lifecycle
# - Separation of Concerns: Decoupled from agent creation
# - Resource Safety: Ensures proper cleanup on shutdown
# - Singleton Pattern: Global server registry for efficiency
#
# Usage:
#   >>> manager = MCPServerManager.instance()
#   >>> await manager.start_server("yelp-mcp", ["uv", "run", "mcp-yelp-agent"])
#   >>> # ... use server ...
#   >>> await manager.shutdown_all()
#
#############################################################################

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any

from asdrp.agents.config_loader import MCPServerConfig
from asdrp.agents.protocol import AgentException


logger = logging.getLogger(__name__)


class MCPServerManager:
    """
    Singleton manager for MCP server subprocess lifecycle.

    This class provides centralized management of MCP server processes,
    ensuring proper startup, shutdown, and resource cleanup. It follows
    the Singleton pattern to maintain a global registry of running servers.

    Key Features:
    - Start MCP servers on-demand or at application startup
    - Track running server processes
    - Graceful shutdown with proper resource cleanup
    - Error handling and logging
    - Environment variable injection

    Attributes:
    -----------
    _instance : MCPServerManager | None
        Singleton instance (class variable).
    _servers : Dict[str, subprocess.Popen]
        Registry of running server processes by name.
    _server_configs : Dict[str, MCPServerConfig]
        Configuration for each registered server.
    """

    _instance: Optional["MCPServerManager"] = None
    _servers: Dict[str, subprocess.Popen] = {}
    _server_configs: Dict[str, MCPServerConfig] = {}

    def __init__(self):
        """
        Initialize MCPServerManager.

        Note: Use MCPServerManager.instance() instead of direct instantiation
        to ensure singleton behavior.
        """
        self._servers: Dict[str, subprocess.Popen] = {}
        self._server_configs: Dict[str, MCPServerConfig] = {}

    @classmethod
    def instance(cls) -> "MCPServerManager":
        """
        Get or create the singleton instance.

        Returns:
            MCPServerManager singleton instance.

        Examples:
        ---------
        >>> manager = MCPServerManager.instance()
        >>> manager2 = MCPServerManager.instance()
        >>> assert manager is manager2  # Same instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start_server(
        self,
        server_name: str,
        config: MCPServerConfig,
        project_root: Optional[Path] = None
    ) -> None:
        """
        Start an MCP server subprocess.

        This method starts an MCP server using the provided configuration.
        If a server with the same name is already running, it will be reused.

        Args:
            server_name: Unique identifier for the server (e.g., "yelp-mcp").
            config: MCP server configuration with command, env, etc.
            project_root: Optional project root directory. If None, uses current directory.

        Raises:
            AgentException: If server cannot be started or configuration is invalid.

        Examples:
        ---------
        >>> manager = MCPServerManager.instance()
        >>> config = MCPServerConfig(
        ...     enabled=True,
        ...     command=["uv", "run", "mcp-yelp-agent"],
        ...     working_directory="yelp-mcp",
        ...     env={"YELP_API_KEY": "..."}
        ... )
        >>> await manager.start_server("yelp-mcp", config)
        """
        # Skip if not enabled
        if not config.enabled:
            logger.info(f"MCP server '{server_name}' is disabled in configuration")
            return

        # Check if already running
        if server_name in self._servers:
            process = self._servers[server_name]
            if process.poll() is None:  # Still running
                logger.info(f"MCP server '{server_name}' is already running (PID: {process.pid})")
                return
            else:
                # Process died, clean up
                logger.warning(f"MCP server '{server_name}' process died, restarting...")
                del self._servers[server_name]

        # Validate configuration
        if not config.command:
            raise AgentException(
                f"MCP server '{server_name}' has no command configured",
                agent_name=server_name
            )

        # Determine working directory
        if config.working_directory:
            if Path(config.working_directory).is_absolute():
                work_dir = Path(config.working_directory)
            else:
                # Relative to project root
                root = project_root or Path.cwd()
                work_dir = root / config.working_directory
        else:
            work_dir = project_root or Path.cwd()

        # Validate working directory exists
        if not work_dir.exists():
            raise AgentException(
                f"MCP server '{server_name}' working directory does not exist: {work_dir}",
                agent_name=server_name
            )

        # Prepare environment variables
        # Environment variables are loaded from .env file via python-dotenv
        # in AgentConfigLoader.__init__, so os.environ already contains them
        env = os.environ.copy()
        
        # Allow programmatic override of environment variables (for testing/advanced usage)
        # Note: When loading from YAML config, env is set to None, so this only applies
        # when MCPServerConfig is created programmatically
        if config.env:
            env.update(config.env)
        
        # Normalize LOG_LEVEL to uppercase for FastMCP compatibility
        # FastMCP expects uppercase log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
        if "LOG_LEVEL" in env:
            log_level = env["LOG_LEVEL"].upper()
            # Validate and normalize to valid log levels
            valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            if log_level in valid_levels:
                env["LOG_LEVEL"] = log_level
            else:
                # Default to INFO if invalid level provided
                env["LOG_LEVEL"] = "INFO"

        # Start subprocess
        try:
            logger.info(f"Starting MCP server '{server_name}'...")
            logger.debug(f"  Command: {' '.join(config.command)}")
            logger.debug(f"  Working directory: {work_dir}")
            logger.debug(f"  Transport: {config.transport}")

            # For stdio transport, we don't start a long-running process here
            # because MCPServerStdio in the agent will manage the subprocess
            # We just validate the configuration and store it
            if config.transport == "stdio":
                logger.info(
                    f"MCP server '{server_name}' configured for stdio transport "
                    f"(subprocess will be managed by agent)"
                )
                self._server_configs[server_name] = config
                return

            # For HTTP/SSE transports, start a long-running server process
            process = subprocess.Popen(
                config.command,
                cwd=str(work_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=False  # Binary mode for stdio
            )

            # Give it a moment to start
            await asyncio.sleep(0.5)

            # Check if process started successfully
            if process.poll() is not None:
                # Process already died
                _, stderr = process.communicate()
                raise AgentException(
                    f"MCP server '{server_name}' failed to start. "
                    f"Exit code: {process.returncode}. "
                    f"Stderr: {stderr.decode('utf-8', errors='replace')}",
                    agent_name=server_name
                )

            self._servers[server_name] = process
            self._server_configs[server_name] = config
            logger.info(
                f"✓ MCP server '{server_name}' started successfully (PID: {process.pid})"
            )

        except FileNotFoundError as e:
            raise AgentException(
                f"MCP server '{server_name}' command not found: {config.command[0]}. "
                f"Make sure the command is installed and in PATH.",
                agent_name=server_name
            ) from e
        except Exception as e:
            raise AgentException(
                f"Failed to start MCP server '{server_name}': {str(e)}",
                agent_name=server_name
            ) from e

    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """
        Get configuration for a registered MCP server.

        Args:
            server_name: Server identifier.

        Returns:
            MCPServerConfig if server is registered, None otherwise.

        Examples:
        ---------
        >>> manager = MCPServerManager.instance()
        >>> config = manager.get_server_config("yelp-mcp")
        >>> if config:
        ...     print(f"Transport: {config.transport}")
        """
        return self._server_configs.get(server_name)

    def is_server_running(self, server_name: str) -> bool:
        """
        Check if an MCP server is currently running.

        Args:
            server_name: Server identifier.

        Returns:
            True if server process is running, False otherwise.

        Examples:
        ---------
        >>> manager = MCPServerManager.instance()
        >>> if manager.is_server_running("yelp-mcp"):
        ...     print("Yelp MCP server is ready")
        """
        if server_name not in self._servers:
            return False

        process = self._servers[server_name]
        return process.poll() is None

    async def stop_server(self, server_name: str, timeout: float = 5.0) -> None:
        """
        Stop a specific MCP server.

        This method gracefully stops an MCP server process, first attempting
        SIGTERM, then SIGKILL if the process doesn't terminate.

        Args:
            server_name: Server identifier.
            timeout: Seconds to wait for graceful shutdown before forcing.

        Examples:
        ---------
        >>> manager = MCPServerManager.instance()
        >>> await manager.stop_server("yelp-mcp")
        """
        if server_name not in self._servers:
            logger.warning(f"MCP server '{server_name}' is not running")
            return

        process = self._servers[server_name]

        # Check if already terminated
        if process.poll() is not None:
            logger.info(f"MCP server '{server_name}' already terminated")
            del self._servers[server_name]
            return

        try:
            logger.info(f"Stopping MCP server '{server_name}' (PID: {process.pid})...")

            # Try graceful termination first
            process.terminate()

            # Wait for process to terminate
            try:
                process.wait(timeout=timeout)
                logger.info(f"✓ MCP server '{server_name}' stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                logger.warning(
                    f"MCP server '{server_name}' did not terminate gracefully, forcing..."
                )
                process.kill()
                process.wait(timeout=1.0)
                logger.info(f"✓ MCP server '{server_name}' force stopped")

        except Exception as e:
            logger.error(f"Error stopping MCP server '{server_name}': {e}")
        finally:
            # Clean up registry
            if server_name in self._servers:
                del self._servers[server_name]
            if server_name in self._server_configs:
                del self._server_configs[server_name]

    async def shutdown_all(self, timeout: float = 5.0) -> None:
        """
        Stop all running MCP servers.

        This method should be called during application shutdown to ensure
        proper cleanup of all MCP server processes.

        Args:
            timeout: Seconds to wait for each server to terminate gracefully.

        Examples:
        ---------
        >>> manager = MCPServerManager.instance()
        >>> # At application shutdown:
        >>> await manager.shutdown_all()
        """
        if not self._servers:
            logger.info("No MCP servers to shutdown")
            return

        logger.info(f"Shutting down {len(self._servers)} MCP server(s)...")

        # Stop all servers concurrently
        tasks = [
            self.stop_server(server_name, timeout)
            for server_name in list(self._servers.keys())
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("✓ All MCP servers shut down")

    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered MCP servers and their status.

        Returns:
            Dictionary mapping server names to their status info.

        Examples:
        ---------
        >>> manager = MCPServerManager.instance()
        >>> servers = manager.list_servers()
        >>> for name, info in servers.items():
        ...     print(f"{name}: {info['status']}")
        """
        result = {}

        for server_name, config in self._server_configs.items():
            status = "running" if self.is_server_running(server_name) else "stopped"
            result[server_name] = {
                "status": status,
                "transport": config.transport,
                "command": config.command,
                "working_directory": config.working_directory,
            }

        return result


# Module-level convenience functions
_manager_instance: Optional[MCPServerManager] = None


def get_mcp_manager() -> MCPServerManager:
    """
    Get the global MCP server manager instance.

    This is a convenience function for accessing the singleton manager.

    Returns:
        MCPServerManager singleton instance.

    Examples:
    ---------
    >>> from asdrp.agents.mcp.mcp_server_manager import get_mcp_manager
    >>> manager = get_mcp_manager()
    >>> await manager.start_server("yelp-mcp", config)
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MCPServerManager.instance()
    return _manager_instance
