# Agent Configuration System

## Overview

The agent system uses a YAML-based configuration file (`config/open_agents.yaml`) to externalize agent definitions, default instructions, and model parameters. This provides:

- **Centralized Configuration**: All agent settings in one place
- **Easy Maintenance**: Update agents without code changes
- **Model Configuration**: Configure model name, temperature, and other parameters
- **Extensibility**: Add new agents by updating the config file
- **Environment-Specific Settings**: Use different config files for different environments

## Configuration File Structure

The configuration file (`config/open_agents.yaml`) has the following structure:

```yaml
agents:
  <agent_name>:
    display_name: Human-readable name
    module: Python module path
    function: Creation function name
    default_instructions: Default system instructions
    model:
      name: Model identifier (e.g., "gpt-4")
      temperature: Temperature (0.0-2.0)
      max_tokens: Maximum response tokens
    enabled: true/false

defaults:
  model:
    name: Default model name
    temperature: Default temperature
    max_tokens: Default max tokens
```

## Example Configuration

```yaml
agents:
  geo:
    display_name: "GeoAgent"
    module: "asdrp.agents.single.geo_agent"
    function: "create_geo_agent"
    default_instructions: |
      You are a useful agent that can help with geocoding and reverse geocoding.
    model:
      name: "gpt-4"
      temperature: 0.7
      max_tokens: 2000
    enabled: true

defaults:
  model:
    name: "gpt-4"
    temperature: 0.7
    max_tokens: 2000
```

## Usage

### Using Configuration Defaults

```python
from asdrp.agents.agent_factory import AgentFactory

factory = AgentFactory.instance()

# Uses default instructions and model config from YAML
agent = await factory.get_agent("geo")
```

### Custom Instructions

```python
# Override default instructions
agent = await factory.get_agent("geo", "Custom geocoding instructions")
```

### Accessing Configuration

```python
factory = AgentFactory.instance()

# Get agent configuration
config = factory.get_agent_config("geo")
print(config.display_name)  # "GeoAgent"
print(config.model.name)  # "gpt-4"
print(config.model.temperature)  # 0.7

# List available agents
agents = factory.list_available_agents()
# ['geo', 'yelp', 'one', 'finance']
```

### Custom Config File

```python
from pathlib import Path
from asdrp.agents.agent_factory import AgentFactory

# Use custom config file
custom_config = Path("custom_config.yaml")
factory = AgentFactory(config_path=custom_config)
agent = await factory.get_agent("geo")
```

## Configuration Classes

### ModelConfig

Configuration for model settings:

```python
from asdrp.agents.config_loader import ModelConfig

config = ModelConfig(
    name="gpt-4",
    temperature=0.8,
    max_tokens=3000
)
```

**Validation:**
- Temperature must be between 0.0 and 2.0
- max_tokens must be positive

### AgentConfig

Configuration for a single agent:

```python
from asdrp.agents.config_loader import AgentConfig, ModelConfig

model_config = ModelConfig(name="gpt-4", temperature=0.7)
agent_config = AgentConfig(
    display_name="GeoAgent",
    module="asdrp.agents.single.geo_agent",
    function="create_geo_agent",
    default_instructions="Instructions...",
    model=model_config,
    enabled=True
)
```

## AgentConfigLoader

The `AgentConfigLoader` class handles loading and parsing configuration:

```python
from asdrp.agents.config_loader import AgentConfigLoader

loader = AgentConfigLoader()
config = loader.get_agent_config("geo")
agents = loader.list_agents()
is_enabled = loader.is_agent_enabled("geo")
```

## Adding New Agents

To add a new agent:

1. **Create the agent module** (e.g., `new_agent.py`):
   ```python
   def create_new_agent(instructions: str | None = None, 
                       model_config: ModelConfig | None = None) -> AgentProtocol:
       # Agent creation logic
       pass
   ```

2. **Add to config file** (`config/open_agents.yaml`):
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

3. **Use the agent**:
   ```python
   agent = await factory.get_agent("new")
   ```

## Benefits

1. **Separation of Concerns**: Configuration separate from code
2. **Easy Updates**: Change agent settings without code changes
3. **Environment Management**: Different configs for dev/staging/prod
4. **Model Flexibility**: Configure model parameters per agent
5. **Maintainability**: Centralized agent definitions

## Best Practices

1. **Use Config Defaults**: Prefer config defaults over hardcoded values
2. **Validate Config**: Use `AgentConfigLoader` to validate configuration
3. **Environment-Specific Configs**: Use different config files for different environments
4. **Version Control**: Keep config files in version control
5. **Documentation**: Document config structure and parameters

## Error Handling

Configuration errors raise `AgentException`:

```python
from asdrp.agents.protocol import AgentException

try:
    agent = await factory.get_agent("unknown")
except AgentException as e:
    print(f"Error: {e.message}")
    print(f"Agent: {e.agent_name}")
```

## Testing

Configuration system is thoroughly tested:
- Config loading and parsing
- Validation and error handling
- Default value handling
- Agent creation with config
- Custom config files

See `tests/asdrp/agents/test_config_loader.py` and `test_agent_factory_config.py` for full test coverage.

