# Session Memory Guide

## Overview

Session memory enables agents to maintain conversation history across multiple interactions. This feature uses the openai-agents SDK's built-in session support to eliminate manual state management.

## Orchestrators (MoE / SmartRouter / Future)

Orchestrators are expected to support **persistent session-level memory** so multi-turn conversations work reliably across:
- Multiple turns
- Multiple underlying specialist agents
- Application restarts (file-based SQLite)

### Key Rules

- **Always provide a `session_id`** when calling orchestrators. If omitted via the API, the server will generate one and return it in response metadata. Clients should **reuse that `session_id`** on subsequent turns to maintain continuity.
- Orchestrators should use **SQLiteSession (file-based)** rooted under `data/sessions/`.
- Orchestrators may need to **force session memory** even when a particular specialist agent is configured stateless, to avoid losing context when the orchestration routes through that component.

## Quick Start

```python
from asdrp.agents.agent_factory import get_agent_with_session
from agents import Runner

# Get agent with session memory
agent, session = await get_agent_with_session("geo")

# First message
result1 = await Runner.run(agent, input="What's near Times Square?", session=session)
print(result1.final_output)

# Follow-up message (context preserved)
result2 = await Runner.run(agent, input="How far is the nearest subway?", session=session)
print(result2.final_output)  # Agent remembers Times Square context
```

## Session Types

### 1. In-Memory SQLite (Default)

Fast, ephemeral storage that's cleared when the application restarts.

```yaml
session_memory:
  type: "sqlite"
  session_id: null          # Auto-generated from agent name
  database_path: null       # null = in-memory
  enabled: true
```

**Best for:**
- Development and testing
- Single-session use cases
- Temporary conversations

**Pros:**
- Fast (no disk I/O)
- Automatic cleanup
- No configuration needed

**Cons:**
- Data lost on application restart
- Not suitable for production persistence

### 2. File-Based SQLite (Persistent)

Persistent storage that survives application restarts.

```yaml
session_memory:
  type: "sqlite"
  session_id: "my_session"
  database_path: "data/sessions/my_agent.db"
  enabled: true
```

**Best for:**
- Production applications
- Long-running conversations
- Multi-session applications

**Pros:**
- Survives restarts
- Can share sessions across instances
- Conversation history preserved

**Cons:**
- Requires disk space
- Slightly slower than in-memory

### 3. Disabled (Stateless)

No session memory - each interaction is independent.

```yaml
session_memory:
  type: "none"
  enabled: false
```

**Best for:**
- One-shot queries
- Stateless API endpoints
- Simple Q&A agents

**Pros:**
- Minimal overhead
- Predictable behavior
- No storage required

**Cons:**
- No conversation context
- Cannot reference previous messages

## Configuration

### YAML Configuration

Configure session memory in `config/open_agents.yaml`:

```yaml
agents:
  geo:
    display_name: "GeoAgent"
    module: "asdrp.agents.single.geo_agent"
    function: "create_geo_agent"
    default_instructions: |
      You are a geocoding assistant...
    model:
      name: "gpt-4.1-mini"
      temperature: 0.7
      max_tokens: 2000
    # Session memory configuration
    session_memory:
      type: "sqlite"
      session_id: null
      database_path: null
      enabled: true
    enabled: true

# Global defaults (applied when not specified per agent)
defaults:
  session_memory:
    type: "sqlite"
    session_id: null
    database_path: null
    enabled: true
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | `"sqlite"` | Session type: `"sqlite"` or `"none"` |
| `session_id` | string | `null` | Unique session identifier. `null` = auto-generated |
| `database_path` | string | `null` | Path to SQLite DB. `null` = in-memory |
| `enabled` | boolean | `true` | Whether session memory is enabled |

## API Reference

### AgentFactory Methods

#### `get_agent_with_session()`

Creates an agent with its configured session memory.

```python
async def get_agent_with_session(
    name: str,
    instructions: str | None = None,
    use_config_defaults: bool = True,
    session_id: str | None = None
) -> Tuple[AgentProtocol, Any]:
```

**Parameters:**
- `name`: Agent name (e.g., "geo", "finance")
- `instructions`: Optional custom instructions
- `use_config_defaults`: Use default instructions from config
- `session_id`: Override the configured session ID

**Returns:**
- Tuple of `(agent, session)` where session may be `None` if disabled

**Example:**
```python
factory = AgentFactory()
agent, session = await factory.get_agent_with_session("geo")
```

#### `get_session()`

Gets or creates a session without creating an agent.

```python
def get_session(
    agent_name: str,
    session_id: str | None = None
) -> Any:
```

**Example:**
```python
session = factory.get_session("geo", session_id="user_123")
```

#### `clear_session_cache()`

Clears all cached session objects.

```python
def clear_session_cache() -> None:
```

**Example:**
```python
factory.clear_session_cache()
```

### Convenience Functions

```python
from asdrp.agents.agent_factory import get_agent_with_session

# Equivalent to AgentFactory.instance().get_agent_with_session()
agent, session = await get_agent_with_session("geo")
```

## Usage Patterns

### Multi-User Sessions

Create separate sessions for different users:

```python
async def handle_user_message(user_id: str, message: str):
    factory = AgentFactory.instance()
    agent, session = await factory.get_agent_with_session(
        "geo",
        session_id=f"user_{user_id}"
    )
    result = await Runner.run(agent, input=message, session=session)
    return result.final_output
```

### Conversation Threads

Maintain multiple conversation threads per user:

```python
async def chat(user_id: str, thread_id: str, message: str):
    session_id = f"{user_id}_{thread_id}"
    agent, session = await get_agent_with_session("geo", session_id=session_id)
    result = await Runner.run(agent, input=message, session=session)
    return result.final_output
```

### Persistent Conversations

Use file-based storage for persistent conversations:

```yaml
# In config/open_agents.yaml
agents:
  support:
    session_memory:
      type: "sqlite"
      database_path: "data/sessions/support.db"
      enabled: true
```

```python
# Conversations persist across restarts
agent, session = await get_agent_with_session("support", session_id="ticket_12345")
```

### Stateless API Endpoint

For stateless endpoints, disable session memory:

```yaml
agents:
  api_agent:
    session_memory:
      type: "none"
      enabled: false
```

```python
# No session returned
agent, session = await get_agent_with_session("api_agent")
assert session is None

# Each call is independent
result = await Runner.run(agent, input="Query")
```

## Session Memory Internals

### SessionMemoryConfig

```python
@dataclass
class SessionMemoryConfig:
    """Configuration for agent session memory."""
    type: str = "sqlite"              # "sqlite" or "none"
    session_id: Optional[str] = None  # null = auto-generated
    database_path: Optional[str] = None  # null = in-memory
    enabled: bool = True
```

### Session Caching

Sessions are cached by the factory using a composite key:

```
cache_key = f"{type}:{session_id}:{database_path}"
```

This means:
- Same session ID + same database path = same session object
- Different session IDs = different session objects
- Clearing cache forces new session creation

### Directory Auto-Creation

For file-based sessions, the factory automatically creates parent directories:

```python
# This works even if data/sessions/ doesn't exist
session_memory:
  database_path: "data/sessions/nested/path/agent.db"
```

## Best Practices

1. **Use Unique Session IDs**: For multi-user apps, include user ID in session_id
2. **Choose Storage Wisely**: In-memory for dev, file-based for production
3. **Clear Cache When Needed**: Use `clear_session_cache()` to reset sessions
4. **Handle None Sessions**: Always check if session is None before using
5. **Gitignore Session Data**: Add `data/sessions/` to `.gitignore`

## Troubleshooting

### Session Not Persisting

**Problem:** Conversation context is lost between calls.

**Solutions:**
1. Ensure you're using the same session object
2. Check that session is not `None`
3. Verify session_id is consistent

### Database File Not Created

**Problem:** File-based session doesn't create database.

**Solutions:**
1. Check `database_path` is set correctly
2. Ensure `enabled: true` in config
3. Verify write permissions on directory

### Memory Usage Growing

**Problem:** In-memory sessions consuming too much RAM.

**Solutions:**
1. Use file-based storage for large conversations
2. Clear session cache periodically
3. Use unique session IDs to limit cache size

## Related Documentation

- [Agent Factory](agent_factory.md) - Factory pattern and agent creation
- [Agent Configuration](agent_configuration.md) - YAML configuration guide
- [Agent Protocol](agent_protocol.md) - AgentProtocol interface

