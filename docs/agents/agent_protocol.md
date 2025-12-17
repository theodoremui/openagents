# Agent Protocol Design

## Overview

The Agent Protocol provides a unified interface for creating and managing different types of agents in the system. It follows best OOP practices including:

- **Protocol-based design**: Uses Python's `Protocol` for structural subtyping
- **Factory pattern**: Centralized agent creation via `AgentFactory` class
- **Error handling**: Custom `AgentException` for agent-related errors
- **Separation of concerns**: Protocol definition, factory, and implementations are separated
- **No circular dependencies**: Agent creation methods are in their respective modules

## Architecture

### AgentProtocol

The `AgentProtocol` defines the interface that all agents must implement:

```python
@runtime_checkable
class AgentProtocol(Protocol):
    name: str
    instructions: str
```

**Key Features:**
- Runtime-checkable: Can use `isinstance()` to verify protocol compliance
- Minimal interface: Only requires `name` and `instructions` attributes
- Compatible with `agents` library: Works seamlessly with the underlying Agent class

### AgentException

Base exception for all agent-related errors:

```python
class AgentException(Exception):
    def __init__(self, message: str, agent_name: str | None = None):
        ...
```

**Usage:**
- Raised when agent creation fails
- Includes agent name for better error context
- Can be caught specifically for agent-related error handling

### AgentFactory Class

The `AgentFactory` class implements the Factory pattern for creating agents:

```python
class AgentFactory:
    async def get_agent(
        name: str, 
        instructions: str | None = None,
        use_config_defaults: bool = True
    ) -> AgentProtocol:
        ...
    
    def register_agent(name: str, factory_func: Callable) -> None:
        ...
    
    def get_agent_config(agent_name: str) -> AgentConfig:
        ...
    
    def list_available_agents() -> list[str]:
        ...
    
    @classmethod
    def instance() -> 'AgentFactory':
        ...
```

**Key Features:**
- **Configuration-Driven**: Agent registry loaded from YAML config file
- **Singleton pattern**: Use `AgentFactory.instance()` for shared instance
- **Lazy registry initialization**: Avoids circular dependencies
- **Dynamic agent registration**: Can register new agent types at runtime
- **Config defaults**: Uses default instructions and model settings from config
- **Model configuration**: Applies model settings (name, temperature, max_tokens) from config
- **Case-insensitive agent names**: Automatic whitespace handling
- **Comprehensive error handling**: Protocol validation and config validation

**Configuration:**
- Agent definitions loaded from `config/open_agents.yaml`
- Each agent has default instructions, model config, and enabled status
- See [Agent Configuration](./agent_configuration.md) for details

**Supported Agent Types:**
- Defined in configuration file (`config/open_agents.yaml`)
- Default: `"geo"`, `"yelp"`, `"one"`, `"finance"`
- Can be extended by updating config file

### Convenience Function: `get_agent()`

For backward compatibility, a convenience function is provided:

```python
async def get_agent(name: str, instructions: str) -> AgentProtocol:
    ...
```

This function delegates to `AgentFactory.instance().get_agent()`.

## Usage Examples

### Using AgentFactory

```python
from asdrp.agents.agent_factory import AgentFactory

# Create factory instance
factory = AgentFactory.instance()

# Create agent with config defaults (instructions and model from config)
agent = await factory.get_agent("geo")

# Or with custom instructions
agent = await factory.get_agent("geo", "You are a geocoding assistant")

# Access configuration
config = factory.get_agent_config("geo")
print(f"Model: {config.model.name}, Temperature: {config.model.temperature}")

# Use with Runner
from agents import Runner
response = await Runner.run(agent, input="What are the coordinates of NYC?")
print(response.final_output)
```

### Using Convenience Function

```python
from asdrp.agents import get_agent

# Create a GeoAgent (uses singleton factory internally)
agent = await get_agent("geo", "You are a geocoding assistant")

# Use with Runner
from agents import Runner
response = await Runner.run(agent, input="What are the coordinates of NYC?")
print(response.final_output)
```

### Using Agent-Specific Factory Functions

```python
from asdrp.agents.single.geo_agent import create_geo_agent
from asdrp.agents.single.yelp_agent import create_yelp_agent
from asdrp.agents.single.one_agent import create_one_agent

# Create agents with default instructions
geo_agent = await create_geo_agent()
yelp_agent = await create_yelp_agent()
one_agent = await create_one_agent()

# Or with custom instructions
geo_agent = await create_geo_agent("Custom geocoding instructions")
```

### Error Handling

```python
from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.protocol import AgentException

factory = AgentFactory.instance()
try:
    agent = await factory.get_agent("invalid", "Test")
except AgentException as e:
    print(f"Agent error: {e.message}")
    print(f"Agent name: {e.agent_name}")
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

agent = await factory.get_agent("custom", "Custom instructions")
```

## Agent Implementations

### GeoAgent

**Purpose:** Geocoding and reverse geocoding operations

**Tools:** `GeoTools.tool_list`
- `get_coordinates_by_address`: Convert address to coordinates
- `get_address_by_coordinates`: Convert coordinates to address

**Default Instructions:**
> "You are a useful agent that can help with the user's request about geocoding and reverse geocoding. You can convert addresses to coordinates and coordinates to addresses."

### YelpAgent

**Purpose:** Business and restaurant search using Yelp API

**Tools:** `YelpTools.tool_list`
- `search_businesses`: Search for businesses
- `get_business_details`: Get detailed business information
- `get_review_highlights`: Get review highlights

**Default Instructions:**
> "You are a useful agent that can help with finding businesses, restaurants, and reviews using Yelp. You can search for businesses by location, cuisine, and other criteria, and provide detailed information including reviews."

### OneAgent

**Purpose:** General-purpose web search and information retrieval

**Tools:** `[WebSearchTool()]`
- Web search capabilities

**Default Instructions:**
> "You are a useful agent that can help with the user's request. You have access to web search capabilities to find current information and answer questions."

## Design Principles

### SOLID Principles

1. **Single Responsibility**: 
   - Each agent type has a single, well-defined purpose
   - `AgentFactory` is responsible only for agent creation
   - Agent creation methods are in their respective modules

2. **Open/Closed**: 
   - New agent types can be added without modifying existing code
   - Factory can be extended via `register_agent()` method

3. **Liskov Substitution**: 
   - All agents can be used interchangeably via the protocol

4. **Interface Segregation**: 
   - Minimal protocol interface (only what's needed)

5. **Dependency Inversion**: 
   - Factory depends on abstractions (protocol), not concretions
   - Agent creation methods imported lazily to avoid circular dependencies

### DRY (Don't Repeat Yourself)

- Centralized agent creation logic in `AgentFactory`
- Shared error handling via `AgentException`
- Reusable protocol definition

### Modularity

- Protocol definition (`protocol.py`) separate from factory (`agent_factory.py`)
- Each agent type in its own module with its creation method
- Clear separation of concerns: protocol, factory, and implementations

### No Circular Dependencies

- Agent creation methods (`_create_*_agent`) are in their respective modules
- Factory imports from agent modules (one-way dependency)
- Agent modules don't import from factory
- Lazy registry initialization prevents import-time circular dependencies

### Extensibility

To add a new agent type:

1. Create the agent implementation module (e.g., `new_agent.py`) with `create_new_agent()` function in `asdrp/agents/single/`
2. Add agent definition to `config/open_agents.yaml`:
   ```yaml
   agents:
     new:
       display_name: "NewAgent"
       module: "asdrp.agents.single.new_agent"
       function: "create_new_agent"
       default_instructions: "Instructions..."
       model:
         name: "gpt-4"
         temperature: 0.7
       enabled: true
   ```
3. Agent is automatically available via `factory.get_agent("new")`

**No code changes needed** - just update the config file!

## Testing

Comprehensive test coverage includes:

- Protocol compliance verification
- Factory function behavior
- Error handling (invalid names, import errors)
- Agent creation with custom/default instructions
- Runtime protocol checks

See `tests/asdrp/agents/` for full test suite.

## Future Enhancements

Potential improvements:

1. **Agent Registry**: Dynamic agent registration system
2. **Caching**: Cache agent instances for performance
3. **Configuration**: External configuration for agent settings
4. **Middleware**: Support for agent middleware/plugins
5. **Monitoring**: Built-in agent usage monitoring

