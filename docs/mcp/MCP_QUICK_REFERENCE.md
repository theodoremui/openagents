# MCP Quick Reference

Quick reference for working with MCP-enabled agents in OpenAgents.

---

## Key Files

```
asdrp/agents/
├── config_loader.py              # MCPServerConfig definition
├── agent_factory.py              # MCP config injection
└── mcp/
    ├── __init__.py               # Module exports
    ├── mcp_server_manager.py     # Lifecycle manager
    └── yelp_mcp_agent.py         # Example implementation

config/open_agents.yaml           # Agent configurations
server/main.py                    # FastAPI integration
server/pyproject.toml             # Dependencies

tests/asdrp/agents/
├── mcp/
│   ├── test_mcp_server_manager.py
│   └── test_yelp_mcp_agent.py
└── test_config_loader_mcp.py

docs/
├── MCP_INTEGRATION_GUIDE.md      # Complete guide
├── MCP_IMPLEMENTATION_SUMMARY.md # Implementation details
└── MCP_QUICK_REFERENCE.md        # This file
```

---

## Configuration Template

```yaml
agents:
  my_mcp_agent:
    display_name: MyMCPAgent
    module: asdrp.agents.mcp.my_mcp_agent
    function: create_my_mcp_agent
    default_instructions: "Your instructions here..."
    model:
      name: gpt-4.1-mini
      temperature: 0.7
      max_tokens: 2000
    session_memory:
      type: sqlite
      enabled: true
    mcp_server:
      enabled: true
      command: [uv, run, mcp-server-command]
      working_directory: mcp-server-dir
      # Note: env field is deprecated - set environment variables in .env file
      transport: stdio
    enabled: true
```

---

## Agent Template

```python
# asdrp/agents/mcp/my_mcp_agent.py
from typing import Any, Dict
from pathlib import Path
import os

from agents import Agent, ModelSettings
from agents.mcp import MCPServerStdio

from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
from asdrp.agents.protocol import AgentProtocol, AgentException

DEFAULT_INSTRUCTIONS = """Your agent instructions..."""

def create_my_mcp_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None,
    mcp_server_config: MCPServerConfig | None = None
) -> AgentProtocol:
    """Create MyMCPAgent with MCP integration."""

    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS

    try:
        # Default MCP config
        if mcp_server_config is None:
            project_root = Path(__file__).parent.parent.parent.parent
            mcp_server_config = MCPServerConfig(
                enabled=True,
                command=["your", "command"],
                working_directory=str(project_root / "your-mcp-dir"),
                env={"API_KEY": os.getenv("API_KEY")},
                transport="stdio"
            )

        # Validate
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

        # Create MCP server
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

---

## Test Template

```python
# tests/asdrp/agents/mcp/test_my_mcp_agent.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
from asdrp.agents.mcp.my_mcp_agent import create_my_mcp_agent

class TestMyMCPAgent:
    @pytest.fixture
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "test-key")

    @pytest.fixture
    def mock_imports(self):
        with patch("asdrp.agents.mcp.my_mcp_agent.Agent") as mock_agent, \
             patch("asdrp.agents.mcp.my_mcp_agent.MCPServerStdio") as mock_mcp:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "MyMCPAgent"
            mock_agent.return_value = mock_agent_instance
            yield {"Agent": mock_agent, "MCPServerStdio": mock_mcp}

    @pytest.fixture
    def mock_path_exists(self):
        with patch.object(Path, "exists", return_value=True):
            yield

    def test_create_agent(self, mock_env, mock_imports, mock_path_exists):
        agent = create_my_mcp_agent()
        assert agent is not None
        assert isinstance(agent, AgentProtocol)
```

---

## Common Commands

```bash
# Verify Python syntax
python -m py_compile asdrp/agents/mcp/my_agent.py

# Run tests
pytest tests/asdrp/agents/mcp/test_my_agent.py -v

# Run with coverage
pytest tests/asdrp/agents/mcp/ --cov=asdrp.agents.mcp

# Start server
cd server
python -m server.main

# Test agent
curl -X POST http://localhost:8000/agents/my_mcp/chat \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"input": "test query"}'
```

---

## Key Classes

### MCPServerConfig

```python
from asdrp.agents.config_loader import MCPServerConfig

config = MCPServerConfig(
    enabled=True,
    command=["uv", "run", "mcp-server"],
    working_directory="mcp-dir",
    env={"KEY": "value"},
    transport="stdio"
)
```

### MCPServerManager

```python
from asdrp.agents.mcp import get_mcp_manager

manager = get_mcp_manager()
await manager.start_server("name", config)
await manager.shutdown_all()
```

### Agent Creation

```python
from asdrp.agents.agent_factory import AgentFactory

factory = AgentFactory.instance()
agent, session = await factory.get_agent_with_session("my_mcp")
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API_KEY required" | `export API_KEY="your-key"` |
| "Working directory does not exist" | Verify path exists |
| "MCP server must be enabled" | Set `enabled: true` in YAML |
| "Failed to start MCP server" | Test command manually |

---

## Best Practices

✅ **DO**:
- Use environment variables for secrets
- Use relative paths in config
- Wrap errors in AgentException
- Mock MCPServerStdio in tests
- Test error paths

❌ **DON'T**:
- Hardcode API keys
- Use absolute paths
- Ignore configuration validation
- Skip error handling
- Forget cleanup

---

## Resources

- [MCP Integration Guide](MCP_INTEGRATION_GUIDE.md) - Complete guide
- [Implementation Summary](MCP_IMPLEMENTATION_SUMMARY.md) - Technical details
- [OpenAI Agents MCP Docs](https://openai.github.io/openai-agents-python/mcp/)
- [MCP Protocol Docs](https://modelcontextprotocol.io/)

---

**For detailed information, see `docs/MCP_INTEGRATION_GUIDE.md`**
