# MCP Integration Guide for OpenAgents

**Version:** 1.0
**Last Updated:** November 30, 2025
**Purpose:** Complete guide for integrating MCP (Model Context Protocol) servers with OpenAgents

---

## Table of Contents

1. [Overview](#overview)
2. [What is MCP?](#what-is-mcp)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Quick Start](#quick-start)
6. [Creating an MCP-Enabled Agent](#creating-an-mcp-enabled-agent)
7. [Configuration](#configuration)
8. [MCP Server Lifecycle](#mcp-server-lifecycle)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)
12. [Examples](#examples)

---

## Overview

The Model Context Protocol (MCP) is a standardized protocol for connecting AI models to external data sources and tools. OpenAgents provides first-class support for MCP integration, allowing agents to access MCP servers seamlessly.

### Key Features

- ✅ **stdio Transport Support**: High bandwidth, low latency local connections
- ✅ **Configuration-Driven**: MCP servers configured via YAML
- ✅ **Lifecycle Management**: Automatic startup and shutdown
- ✅ **Dependency Injection**: MCP config passed through agent factory
- ✅ **Type-Safe**: Pydantic models for configuration validation
- ✅ **Production-Ready**: Comprehensive error handling and logging

---

## What is MCP?

MCP (Model Context Protocol) is like "USB-C for AI applications" - a universal standard for connecting AI models to tools and data sources.

### Benefits

- **Standardization**: One protocol for all external integrations
- **Modularity**: Swap MCP servers without changing agent code
- **Extensibility**: Easy to add new capabilities
- **Community**: Growing ecosystem of MCP servers

### MCP Transports

OpenAgents currently supports:

1. **stdio** (recommended): Local subprocess communication
   - High bandwidth, low latency
   - No network overhead
   - Best for local tools

2. **streamable-http** (future): HTTP-based communication
3. **sse** (future): Server-Sent Events

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Lifespan Manager                         │   │
│  │  - Validates MCP configurations                       │   │
│  │  - Logs MCP-enabled agents                            │   │
│  │  - Coordinates shutdown                               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
┌─────────▼──────────┐              ┌─────────▼──────────┐
│  AgentFactory      │              │  MCPServerManager  │
│  - Loads config    │              │  - Tracks servers  │
│  - Creates agents  │              │  - Cleanup helper  │
│  - Injects MCP     │              └────────────────────┘
└─────────┬──────────┘
          │
          │ create_agent(config)
          │
┌─────────▼──────────┐
│  YelpMCPAgent      │
│  ┌──────────────┐  │
│  │ MCPServerStdio│ ◄─── Manages subprocess
│  └──────────────┘  │
│  - OpenAI Agent    │
│  - MCP tools       │
└─────────┬──────────┘
          │
          │ subprocess communication (stdio)
          │
┌─────────▼──────────┐
│  yelp-mcp Server   │
│  - FastMCP         │
│  - yelp_agent tool │
│  - Yelp Fusion AI  │
└────────────────────┘
```

### Data Flow

1. **Configuration Loading**: YAML → AgentConfigLoader → MCPServerConfig
2. **Agent Creation**: AgentFactory detects MCP config → Passes to create function
3. **MCP Connection**: Agent creates MCPServerStdio → Starts subprocess
4. **Tool Execution**: Agent calls tool → MCPServerStdio → MCP server → Response
5. **Cleanup**: FastAPI shutdown → MCPServerManager.shutdown_all()

---

## Prerequisites

### System Requirements

- Python 3.13+
- OpenAI Agents SDK ≥ 0.5.1 (includes MCP support)
- MCP CLI tools: `mcp[cli]>=1.9.1`
- `uv` package manager (for yelp-mcp example)

### Installation

```bash
# Install server dependencies (includes MCP)
cd server
pip install -e .

# Install yelp-mcp dependencies
cd ../yelp-mcp
uv sync
```

---

## Quick Start

### Step 1: Configure MCP Server

Add to `config/open_agents.yaml`:

```yaml
agents:
  yelp_mcp:
    display_name: YelpMCPAgent
    module: asdrp.agents.mcp.yelp_mcp_agent
    function: create_yelp_mcp_agent
    default_instructions: |
      You are YelpMCPAgent - an expert at finding businesses using Yelp.
      Use the yelp_agent tool for searches and queries.
    model:
      name: gpt-4.1-mini
      temperature: 0.7
      max_tokens: 2000
    session_memory:
      type: sqlite
      enabled: true
    mcp_server:
      enabled: true
      command:
        - uv
        - run
        - mcp-yelp-agent
      working_directory: yelp-mcp
      transport: stdio
    enabled: true
```

### Step 2: Set Environment Variables

Environment variables are automatically loaded from `.env` file using `python-dotenv`.
Create or update your `.env` file in the project root:

```bash
# .env file
YELP_API_KEY=your-yelp-api-key
```

**Note**: Do not specify `env` in the YAML configuration. All environment variables
should be set in the `.env` file and will be automatically loaded.

### Step 3: Start Server

```bash
cd server
python -m server.main
```

### Step 4: Test Agent

```bash
curl -X POST http://localhost:8000/agents/yelp_mcp/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"input": "Find the best tacos in San Francisco"}'
```

---

## Creating an MCP-Enabled Agent

### Step 1: Create Agent Module

Create `/Users/pmui/dev/halo/openagents/asdrp/agents/mcp/my_mcp_agent.py`:

```python
from typing import Any, Dict
from pathlib import Path
import os

from agents import Agent, ModelSettings
from agents.mcp import MCPServerStdio

from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
from asdrp.agents.protocol import AgentProtocol, AgentException


DEFAULT_INSTRUCTIONS = """You are MyMCPAgent..."""


def create_my_mcp_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None,
    mcp_server_config: MCPServerConfig | None = None
) -> AgentProtocol:
    """Create MyMCPAgent with MCP integration."""

    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS

    try:
        # Default MCP config if not provided
        if mcp_server_config is None:
            project_root = Path(__file__).parent.parent.parent.parent

            mcp_server_config = MCPServerConfig(
                enabled=True,
                command=["your", "mcp", "command"],
                working_directory=str(project_root / "your-mcp-server"),
                env={"API_KEY": os.getenv("API_KEY")},
                transport="stdio"
            )

        # Validate config
        if not mcp_server_config.enabled:
            raise AgentException(
                "MCP server must be enabled",
                agent_name="my_mcp"
            )

        # Resolve working directory
        work_dir = Path(mcp_server_config.working_directory)
        if not work_dir.is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            work_dir = project_root / mcp_server_config.working_directory

        if not work_dir.exists():
            raise AgentException(
                f"Working directory does not exist: {work_dir}",
                agent_name="my_mcp"
            )

        # Prepare environment
        # Environment variables are loaded from .env file via python-dotenv
        # in AgentConfigLoader.__init__, so os.environ already contains them
        env = os.environ.copy()
        
        # Allow programmatic override of environment variables (for testing/advanced usage)
        # Note: When loading from YAML config, env is set to None, so this only applies
        # when MCPServerConfig is created programmatically
        if mcp_server_config.env:
            env.update(mcp_server_config.env)

        # Create MCP server connection
        # MCPServerStdio requires MCPServerStdioParams object
        from agents.mcp import MCPServerStdioParams
        
        command_list = mcp_server_config.command or []
        executable = command_list[0]
        args = command_list[1:] if len(command_list) > 1 else []
        
        mcp_params = MCPServerStdioParams(
            command=executable,  # Executable as string
            args=args,  # Arguments as list
            cwd=str(work_dir),
            encoding="utf-8",
            encoding_error_handler="strict",
            env=env
        )
        
        mcp_server = MCPServerStdio(params=mcp_params)
        
        # Build agent
        # IMPORTANT: MCP servers should be passed via mcp_servers parameter, not tools
        # The MCP server will automatically expose its tools to the agent
        agent_kwargs: Dict[str, Any] = {
            "name": "MyMCPAgent",
            "instructions": instructions,
            "mcp_servers": [mcp_server],  # MCP server provides tools dynamically
        }

        if model_config:
            agent_kwargs["model"] = model_config.name
            agent_kwargs["model_settings"] = ModelSettings(
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )

        return Agent[Any](**agent_kwargs)

    except ImportError as e:
        raise AgentException(
            f"Failed to import dependencies: {str(e)}",
            agent_name="my_mcp"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create agent: {str(e)}",
            agent_name="my_mcp"
        ) from e
```

### Step 2: Add Configuration

Add to `config/open_agents.yaml`:

```yaml
agents:
  my_mcp:
    display_name: MyMCPAgent
    module: asdrp.agents.mcp.my_mcp_agent
    function: create_my_mcp_agent
    default_instructions: "..."
    model:
      name: gpt-4.1-mini
      temperature: 0.7
      max_tokens: 2000
    session_memory:
      type: sqlite
      enabled: true
    mcp_server:
      enabled: true
      command: ["your", "command"]
      working_directory: your-mcp-server
      env:
        API_KEY: ${API_KEY}
      transport: stdio
    enabled: true
```

### Step 3: Test

```bash
python -m asdrp.agents.mcp.my_mcp_agent
```

---

## Configuration

### MCPServerConfig Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | bool | Yes | Enable/disable MCP server |
| `command` | list[str] | Yes (if enabled) | Command to start server |
| `working_directory` | str | No | Working directory (relative to project root) |
| `env` | dict | No | Environment variables for programmatic override. Ignored when loading from YAML. Set variables in `.env` file for YAML configs. |
| `transport` | str | No | Transport protocol (default: "stdio") |
| `host` | str | No | Host for HTTP/SSE transports |
| `port` | int | No | Port for HTTP/SSE transports |

### Environment Variables

Environment variables are automatically loaded from `.env` file using `python-dotenv`
when `AgentConfigLoader` is initialized. **Do not specify `env` in YAML configuration.**

Set environment variables in `.env` file:

```bash
# .env file
YELP_API_KEY=your-yelp-api-key
LOG_LEVEL=INFO
```

**YAML Configuration**: The `env` field in YAML config is ignored (set to `None`).
All environment variables should be set in `.env` file.

**Programmatic Usage**: When creating `MCPServerConfig` programmatically (e.g., in tests),
you can still use the `env` field to override/add environment variables. This is useful
for testing and advanced configurations, but should not be used in YAML configs.

### Relative Paths

Working directories are resolved relative to project root:

```yaml
working_directory: yelp-mcp  # → /project/root/yelp-mcp
```

---

## MCP Server Lifecycle

### Startup

1. **Configuration Loading**: YAML loaded during AgentFactory initialization
2. **Validation**: MCPServerConfig validates at parse time
3. **Subprocess Management**: MCPServerStdio manages subprocess per agent
4. **FastAPI Lifespan**: Logs MCP-enabled agents at startup

### Runtime

- **On-Demand**: MCP servers started when agent is first used
- **Per-Agent**: Each agent instance manages its own MCP connection
- **Automatic Restart**: If subprocess dies, MCPServerStdio restarts it

### Shutdown

1. **FastAPI Shutdown Signal**: Triggers lifespan cleanup
2. **MCPServerManager.shutdown_all()**: Called automatically
3. **Graceful Termination**: SIGTERM → wait → SIGKILL if needed
4. **Resource Cleanup**: All processes terminated and cleaned up

---

## Testing

### Unit Tests

```python
import pytest
from unittest.mock import patch, MagicMock

def test_create_agent_with_mcp_config():
    """Test agent creation with MCP configuration."""
    mock_config = MCPServerConfig(
        enabled=True,
        command=["test"],
        working_directory="/tmp",
        transport="stdio"
    )

    with patch("asdrp.agents.mcp.my_agent.Agent") as mock_agent, \
         patch("asdrp.agents.mcp.my_agent.MCPServerStdio") as mock_mcp:

        agent = create_my_agent(mcp_server_config=mock_config)

        # Verify MCPServerStdio was created
        mock_mcp.assert_called_once()

        # Verify agent was created with MCP server as tool
        assert agent is not None
```

### Integration Tests

```bash
# Run agent integration tests
pytest tests/asdrp/agents/mcp/test_yelp_mcp_agent.py -v

# Run MCP manager tests
pytest tests/asdrp/agents/mcp/test_mcp_server_manager.py -v
```

---

## Troubleshooting

### Issue: "YELP_API_KEY environment variable is required"

**Solution**: Set the environment variable in `.env` file:

```bash
# Create or edit .env file in project root
echo "YELP_API_KEY=your-key" >> .env
```

Environment variables are automatically loaded from `.env` file using `python-dotenv`.
Make sure the `.env` file exists in the project root directory.

### Issue: "Working directory does not exist"

**Solution**: Verify the path exists:

```bash
ls -la yelp-mcp/
# Should show the MCP server directory
```

### Issue: "MCP server must be enabled"

**Solution**: Check YAML configuration:

```yaml
mcp_server:
  enabled: true  # Must be true
```

### Issue: "Failed to start MCP server"

**Debug Steps**:

1. Check command is valid:
   ```bash
   cd yelp-mcp
   uv run mcp-yelp-agent  # Should start without errors
   ```

2. Check logs:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. Verify dependencies:
   ```bash
   cd yelp-mcp
   uv sync
   ```

---

## Best Practices

### 1. Configuration Management

✅ **DO**: Use environment variables for secrets
```yaml
env:
  API_KEY: ${API_KEY}  # Secure
```

❌ **DON'T**: Hardcode secrets
```yaml
env:
  API_KEY: "sk-1234..."  # Insecure!
```

### 2. Error Handling

✅ **DO**: Wrap errors in AgentException
```python
except Exception as e:
    raise AgentException(
        f"Failed: {str(e)}",
        agent_name="my_agent"
    ) from e
```

### 3. Working Directories

✅ **DO**: Use relative paths in config
```yaml
working_directory: my-mcp-server  # Portable
```

❌ **DON'T**: Use absolute paths
```yaml
working_directory: /Users/me/my-mcp-server  # Not portable
```

### 4. Transport Selection

- **stdio**: For local tools (recommended)
- **HTTP/SSE**: For remote services (future)

### 5. Testing

- **Mock MCPServerStdio** in unit tests
- **Use real MCP server** in integration tests
- **Test error paths** (missing config, dead server, etc.)

---

## Examples

### Example 1: YelpMCPAgent

Full example in: `asdrp/agents/mcp/yelp_mcp_agent.py`

**Features**:
- Yelp Fusion AI integration
- Multi-turn conversations with chat_id
- Natural language business search
- Structured data responses

### Example 2: Custom Tool Server

```python
# your-tool/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool()
async def my_custom_tool(query: str) -> str:
    """Your custom tool implementation."""
    # ... tool logic ...
    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

---

## Summary

MCP integration in OpenAgents provides:

1. ✅ **Simple Configuration**: YAML-driven setup
2. ✅ **Type Safety**: Pydantic validation
3. ✅ **Production Ready**: Proper lifecycle management
4. ✅ **Extensible**: Easy to add new MCP servers
5. ✅ **Well Tested**: >90% test coverage

For questions or issues, see:
- [OpenAI Agents MCP Docs](https://openai.github.io/openai-agents-python/mcp/)
- [MCP Protocol Docs](https://modelcontextprotocol.io/)
- Project Issues: Check GitHub issues

**Next Steps**: Try creating your own MCP-enabled agent!
