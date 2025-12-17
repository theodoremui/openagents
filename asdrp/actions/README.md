# Actions Package

This package contains action tools for agent frameworks, using the `ToolsMeta` metaclass for automatic tool discovery and creation.

## Overview

The `ToolsMeta` metaclass automatically:
- Discovers all public `@classmethod` decorated methods
- Creates a `spec_functions` list containing method names
- Creates a `tool_list` containing wrapped function tools ready for agent frameworks

## Quick Start

### Creating a New Action Class

```python
from asdrp.actions.tools_meta import ToolsMeta
import os

class MyActionTools(metaclass=ToolsMeta):
    # Optional: Set up class-level configuration
    @classmethod
    def _setup_class(cls) -> None:
        """Called automatically during class creation."""
        cls.api_key = os.getenv("MY_API_KEY")
        if not cls.api_key:
            raise ValueError("MY_API_KEY is not set.")
        cls.headers = {"Authorization": f"Bearer {cls.api_key}"}
    
    # Optional: Exclude additional methods/attributes from tool discovery
    @classmethod
    def _get_excluded_methods(cls) -> set[str]:
        """Return set of names to exclude from tool discovery."""
        return {'api_key', 'headers', 'BASE_URL'}
    
    # Public class methods are automatically discovered as tools
    @classmethod
    def search_something(cls, query: str) -> dict:
        """Search for something. This will be included in tool_list."""
        # Your implementation here
        return {"results": []}
    
    @classmethod
    def get_details(cls, id: str) -> dict:
        """Get details. This will also be included in tool_list."""
        # Your implementation here
        return {"id": id}
```

### Using the Tools

```python
from asdrp.actions.local.yelp_tools import YelpTools
from agents import Agent

# Use the automatically generated tool_list
agent = Agent(
    name="my_agent",
    instructions="You are a helpful assistant.",
    tools=YelpTools.tool_list  # Automatically contains all public class methods
)

# Or access the method names
print(YelpTools.spec_functions)  # ['get_business_details', 'search_businesses', ...]

# Or call methods directly
results = YelpTools.search_businesses("pizza", 37.7749, -122.4194)
```

## Customization Hooks

### `_setup_class()`

Called automatically during class creation, before method discovery. Use this to:
- Initialize API keys from environment variables
- Set up headers or other configuration
- Perform any class-level setup

**Example:**
```python
@classmethod
def _setup_class(cls) -> None:
    cls.api_key = os.getenv("API_KEY")
    cls.base_url = "https://api.example.com"
```

### `_get_excluded_methods()`

Return a set of method/attribute names to exclude from tool discovery. These are added to the default exclusions.

**Default exclusions:**
- Methods starting with `_` (private methods)
- Special methods: `__init__`, `__new__`, `__init_subclass__`, `__class__`
- Metaclass attributes: `spec_functions`, `tool_list`

**Example:**
```python
@classmethod
def _get_excluded_methods(cls) -> set[str]:
    return {'api_key', 'headers', 'BASE_URL', 'internal_helper'}
```

## Available Tool Packages

### Geographic Tools (`geo/`)
- `geo_tools.py`: Geocoding tools using geopy/ArcGIS (address ↔ coordinates)
- `map_tools.py`: Google Maps tools (places, directions, distances)

### Financial Tools (`finance/`)
- `finance_tools.py`: Financial data tools using yfinance (stock data, historical prices)

### Local Business Tools (`local/`)
- `yelp_tools.py`: Yelp API tools (business search, reviews, ratings)

### Search & Knowledge Tools (`search/`)
- `wiki_tools.py`: Wikipedia tools (search, page content, summaries, sections, images, links)

### Core Files
- `tools_meta.py`: The general `ToolsMeta` metaclass

## Testing

Run tests with:
```bash
pytest tests/
```

Test files:
- `tests/asdrp/actions/test_tools_meta.py`: Tests for `ToolsMeta` functionality
- `tests/asdrp/actions/geo/test_geo_tools.py`: Tests for `GeoTools`
- `tests/asdrp/actions/local/test_yelp_tools.py`: Tests for `YelpTools`
- `tests/asdrp/actions/search/test_wiki_tools.py`: Tests for `WikiTools`
- `tests/asdrp/actions/finance/test_finance_tools.py`: Tests for `FinanceTools`

## Design Principles

1. **Simplicity**: Minimal boilerplate - just use the metaclass and define class methods
2. **Explicitness**: Customization happens in the class itself via hooks
3. **Consistency**: All action classes follow the same pattern
4. **Flexibility**: Easy to extend with custom setup and exclusions

