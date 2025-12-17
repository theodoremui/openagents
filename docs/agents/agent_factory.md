# AgentFactory Design

## Overview

The `AgentFactory` class provides a centralized, extensible way to create agent instances following the Factory pattern and SOLID principles. It now includes built-in support for session memory to maintain conversation history across multiple agent runs.

## Architecture

### Class Structure

```python
class AgentFactory:
    _instance: 'AgentFactory | None' = None
    _registry: Dict[str, Callable[[str], AgentProtocol]] | None = None
    _session_cache: Dict[str, Any] | None = None
    
    def __init__(config_path: str | Path | None = None)
    @classmethod
    def instance() -> 'AgentFactory'
    async def get_agent(name: str, instructions: str) -> AgentProtocol
    async def get_agent_with_session(name: str, ...) -> Tuple[AgentProtocol, Any]
    def get_session(agent_name: str, session_id: str | None) -> Any
    def register_agent(name: str, factory_func: Callable) -> None
    def clear_session_cache() -> None
    def _get_registry() -> Dict[str, Callable]
    def _create_session(session_config, agent_name) -> Any
```

### Key Design Decisions

1. **Singleton Pattern**: `instance()` method provides a shared factory instance
2. **Lazy Registry**: Registry is initialized only when first accessed
3. **Session Caching**: Session objects are cached for reuse across calls
4. **Separation of Concerns**: Agent creation methods are in their respective modules
5. **No Circular Dependencies**: Factory imports from agent modules, not vice versa

## Usage

### Basic Usage (Without Session Memory)

```python
from asdrp.agents.agent_factory import AgentFactory

# Get singleton instance
factory = AgentFactory.instance()

# Create agents
geo_agent = await factory.get_agent("geo", "Geocoding instructions")
yelp_agent = await factory.get_agent("yelp", "Yelp search instructions")
```

### Usage with Session Memory

```python
from asdrp.agents.agent_factory import AgentFactory, get_agent_with_session
from agents import Runner

# Using factory instance
factory = AgentFactory()
agent, session = await factory.get_agent_with_session("geo")

# Or using convenience function
agent, session = await get_agent_with_session("finance")

# Use session with Runner to maintain conversation history
result = await Runner.run(agent, input="What's the weather?", session=session)

# Continue conversation with same session (context preserved)
result2 = await Runner.run(agent, input="Tell me more", session=session)
```

### Creating Separate Conversation Threads

```python
# Create separate sessions for different users
agent, session1 = await factory.get_agent_with_session("geo", session_id="user_123")
agent, session2 = await factory.get_agent_with_session("geo", session_id="user_456")

# Each session maintains its own conversation history
```

### Getting Session Without Creating Agent

```python
# Pre-create or retrieve session
session = factory.get_session("geo", session_id="my_session")
```

### Dynamic Agent Registration

```python
from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.protocol import AgentProtocol
from agents import Agent

def create_custom_agent(instructions: str) -> AgentProtocol:
    return Agent(name="CustomAgent", instructions=instructions, tools=[])

factory = AgentFactory.instance()
factory.register_agent("custom", create_custom_agent)

# Now can create custom agent
agent = await factory.get_agent("custom", "Custom instructions")
```

## Session Memory

### Overview

Session memory allows agents to maintain conversation history across multiple `Runner.run()` calls. This is powered by the openai-agents SDK's built-in session support.

### Session Types

| Type | Storage | Persistence | Use Case |
|------|---------|-------------|----------|
| `sqlite` (in-memory) | RAM | Until app restarts | Development, testing |
| `sqlite` (file-based) | Disk | Survives restarts | Production, history |
| `none` | None | Stateless | One-shot queries |

### Configuration in YAML

Session memory is configured per-agent in `config/open_agents.yaml`:

```yaml
agents:
  geo:
    # ... other config ...
    session_memory:
      type: "sqlite"          # "sqlite" or "none"
      session_id: null        # null = auto-generated from agent name
      database_path: null     # null = in-memory, or path like "data/sessions/geo.db"
      enabled: true

  finance:
    # ... other config ...
    session_memory:
      type: "sqlite"
      session_id: "finance_session"
      database_path: "data/sessions/finance.db"  # Persistent storage
      enabled: true

  one:
    # ... other config ...
    session_memory:
      type: "none"
      enabled: false  # Stateless agent
```

### Session Caching

Sessions are cached by the factory to enable reuse:

```python
# These return the same session object (cached)
agent1, session1 = await factory.get_agent_with_session("geo")
agent2, session2 = await factory.get_agent_with_session("geo")
assert session1 is session2  # Same session

# Clear cache to force new session creation
factory.clear_session_cache()
```

## Implementation Details

### Registry Initialization

The registry is initialized lazily in `_get_registry()`:

```python
def _get_registry(self) -> Dict[str, Callable[[str], AgentProtocol]]:
    if self._registry is None:
        # Registry is now loaded dynamically from config file
        # Agent modules are imported based on config/open_agents.yaml
        # Example modules: asdrp.agents.single.geo_agent, etc.
        ...
    return self._registry
```

**Benefits:**
- Avoids circular dependencies at import time
- Only imports when needed
- Allows dynamic registration

### Session Creation Flow

1. `get_agent_with_session()` calls `get_agent()` to create the agent
2. Retrieves session memory configuration from agent config
3. Applies session_id override if provided
4. Calls `_create_session()` to create or retrieve cached session
5. Returns `(agent, session)` tuple

### Agent Creation Flow

1. `get_agent()` normalizes the agent name
2. Looks up factory function in registry
3. Calls factory function with instructions
4. Validates returned agent implements `AgentProtocol`
5. Returns agent instance

### Error Handling

All errors are wrapped in `AgentException`:
- Invalid agent names
- Import errors
- Protocol validation failures
- Session creation failures
- Generic exceptions during creation

## Best Practices

1. **Use Singleton**: Prefer `AgentFactory.instance()` for shared factory
2. **Use Sessions for Conversations**: Use `get_agent_with_session()` for multi-turn conversations
3. **Session ID for Users**: Use unique session IDs per user for separate conversation threads
4. **Register Early**: Register custom agents before first use
5. **Validate Protocol**: Ensure custom agents implement `AgentProtocol`
6. **Handle Exceptions**: Always catch `AgentException` when creating agents

## Testing

The factory is thoroughly tested:
- Singleton pattern
- Agent creation for all types
- Session memory creation and caching
- Session ID overrides
- Error handling
- Dynamic registration
- Protocol validation

See `tests/asdrp/agents/test_session_memory.py` for session memory tests.
See `tests/asdrp/agents/test_agent_factory_config.py` for factory tests.
