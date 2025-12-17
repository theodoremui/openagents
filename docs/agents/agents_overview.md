# Agents Overview

## Introduction

The agents package provides a unified interface for creating and managing different types of AI agents. All agents follow a common protocol and can be created through a centralized factory function.

## Quick Start

```python
from asdrp.agents.agent_factory import AgentFactory
from agents import Runner

# Create factory and agent (uses config defaults)
factory = AgentFactory.instance()
agent = await factory.get_agent("geo")

# Or use convenience function
from asdrp.agents import get_agent
agent = await get_agent("geo")

# Use the agent
response = await Runner.run(agent, input="What are the coordinates of NYC?")
print(response.final_output)
```

**Note:** Agents are configured via `config/open_agents.yaml`. Default instructions and model settings come from the configuration file.

## Available Agents

### GeoAgent

Geocoding and reverse geocoding operations using ArcGIS geocoding service.

```python
from asdrp.agents.single.geo_agent import create_geo_agent

agent = await create_geo_agent()
# Or with custom instructions
agent = await create_geo_agent("Custom instructions")
```

**Capabilities:**
- Convert addresses to coordinates
- Convert coordinates to addresses

### MapAgent

Google Maps-based agent for locations, places, directions, and geocoding operations.

```python
from asdrp.agents.single.map_agent import create_map_agent

agent = await create_map_agent()
# Or with custom instructions
agent = await create_map_agent("Custom instructions")
```

**Capabilities:**
- Convert addresses to coordinates using Google Maps Geocoding API
- Convert coordinates to addresses (reverse geocoding)
- Search for places nearby a location
- Get detailed place information
- Calculate travel times and distances
- Get distance matrix for multiple locations
- Place autocomplete suggestions

**Requirements:**
- `GOOGLE_API_KEY` environment variable must be set
- Google Maps API must be enabled in your Google Cloud project

**Example Usage:**
```python
from asdrp.agents import get_agent
from agents import Runner

agent = await get_agent("map")
response = await Runner.run(agent, input="Find coffee shops near Times Square, NYC")
print(response.final_output)
```

### YelpAgent

Business and restaurant search using Yelp API.

```python
from asdrp.agents.single.yelp_agent import create_yelp_agent

agent = await create_yelp_agent()
```

**Capabilities:**
- Search for businesses
- Get business details
- Retrieve review highlights

### OneAgent

General-purpose web search and information retrieval.

```python
from asdrp.agents.single.one_agent import create_one_agent

agent = await create_one_agent()
```

**Capabilities:**
- Web search
- Information retrieval

### FinanceAgent

Financial data and market information retrieval using yfinance.

```python
from asdrp.agents.single.finance_agent import create_finance_agent

agent = await create_finance_agent()
# Or with custom instructions
agent = await create_finance_agent("Custom instructions")
```

**Capabilities:**
- Get ticker information (company details, financial metrics)
- Retrieve historical market data
- Access financial statements (income statement, balance sheet, cash flow)
- Get dividend and stock split history
- Retrieve analyst recommendations
- Get earnings calendar
- Access news articles related to tickers
- Get options chain data
- Download market data for multiple tickers

**Example Usage:**
```python
from asdrp.agents import get_agent
from agents import Runner

agent = await get_agent("finance")
response = await Runner.run(agent, input="What is Apple's current market cap?")
print(response.final_output)
```

See [Finance Tools Documentation](./finance_tools.md) for detailed information about available financial data tools.

## Architecture

See [Agent Protocol Design](./agent_protocol.md) for detailed architecture documentation.

## Error Handling

All agent creation functions raise `AgentException` on failure:

```python
from asdrp.agents.protocol import AgentException

try:
    agent = await get_agent("invalid", "Test")
except AgentException as e:
    print(f"Error: {e.message}")
    print(f"Agent: {e.agent_name}")
```

## Best Practices

1. **Use the factory function**: Prefer `get_agent()` for flexibility
2. **Handle errors**: Always catch `AgentException` when creating agents
3. **Custom instructions**: Provide clear, specific instructions for better results
4. **Protocol compliance**: Use `isinstance(agent, AgentProtocol)` to verify compliance

## Configuration

Agents are configured via `config/open_agents.yaml`. This file defines:
- Available agents and their creation functions
- Default instructions for each agent
- Model configuration (name, temperature, max_tokens)
- Enabled/disabled status

See [Agent Configuration](./agent_configuration.md) for detailed configuration guide.

## Related Documentation

- [Agent Protocol Design](./agent_protocol.md): Detailed protocol documentation
- [Agent Configuration](./agent_configuration.md): Configuration system documentation
- [Actions Package](../asdrp/actions/README.md): Information about agent tools

