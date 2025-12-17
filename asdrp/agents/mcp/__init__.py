"""
MCP (Model Context Protocol) integration module for OpenAgents.

This module provides integration with MCP servers, enabling agents to access
external tools and resources through the Model Context Protocol standard.

Key Components:
---------------
- MCPServerManager: Lifecycle management for MCP server processes
- yelp_mcp_agent: YelpMCPAgent implementation using Yelp MCP server

Usage:
------
>>> from asdrp.agents.mcp import get_mcp_manager
>>> manager = get_mcp_manager()
>>> await manager.start_server("yelp-mcp", config)
"""

from asdrp.agents.mcp.mcp_server_manager import (
    MCPServerManager,
    get_mcp_manager,
)

__all__ = [
    "MCPServerManager",
    "get_mcp_manager",
]
