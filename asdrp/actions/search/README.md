# Search & Knowledge Tools

This package contains tools for searching and querying knowledge bases.

## WikiTools

**File**: `wiki_tools.py`

A comprehensive toolkit for interacting with Wikipedia using the `wikipedia` Python package.

### Features

- **Search Wikipedia**: Find pages matching a query with optional suggestions
- **Get Page Summary**: Retrieve concise summaries with configurable sentence count
- **Get Full Content**: Extract complete page content with sections
- **Get Specific Sections**: Retrieve individual sections from pages
- **Get Images**: List all image URLs from a page
- **Get Links**: Extract all internal Wikipedia links
- **Set Language**: Change Wikipedia language (supports 300+ languages)
- **Random Pages**: Get random Wikipedia page titles

### Usage

#### Direct Method Calls

```python
import asyncio
from asdrp.actions.search.wiki_tools import WikiTools

# Search Wikipedia
result = await WikiTools.search("machine learning", results=5)
print(result['results'])  # ['Machine learning', 'Deep learning', ...]

# Get page summary
summary = await WikiTools.get_page_summary("Python (programming language)", sentences=3)
print(summary['summary'])
print(summary['url'])

# Get full page content
content = await WikiTools.get_page_content("Artificial intelligence")
print(f"Length: {content['length']} characters")
print(f"Sections: {content['sections']}")

# Get specific section
section = await WikiTools.get_page_section("Python (programming language)", "History")
print(section['content'])

# Get images from page
images = await WikiTools.get_page_images("Eiffel Tower")
print(f"Found {images['count']} images")

# Get links from page
links = await WikiTools.get_page_links("Machine learning")
print(f"Found {links['count']} links")

# Change language
await WikiTools.set_language("es")  # Spanish
result = await WikiTools.search("inteligencia artificial")

# Get random pages
random = await WikiTools.get_random_page(pages=5)
print(random['pages'])
```

#### Use with Agent Framework

```python
from agents import Agent
from asdrp.actions.search.wiki_tools import WikiTools

# WikiTools automatically integrates with ToolsMeta
agent = Agent(
    name="WikipediaAgent",
    instructions="You are a helpful assistant with access to Wikipedia.",
    tools=WikiTools.tool_list  # All methods automatically available
)

# The agent can now use any WikiTools method
result = agent.run("Tell me about quantum mechanics")
```

### Available Methods

All methods are async and automatically discovered by `ToolsMeta`:

| Method | Description |
|--------|-------------|
| `search(query, results=10, suggestion=False)` | Search Wikipedia for pages |
| `get_page_summary(title, sentences=3, ...)` | Get page summary |
| `get_page_content(title, ...)` | Get full page content |
| `get_page_section(title, section_title, ...)` | Get specific section |
| `get_page_images(title, ...)` | Get image URLs from page |
| `get_page_links(title, ...)` | Get internal links from page |
| `set_language(language_code)` | Change Wikipedia language |
| `get_random_page(pages=1)` | Get random page titles |

### Error Handling

WikiTools handles common Wikipedia exceptions:

- **DisambiguationError**: When a title matches multiple pages
  - The error includes a list of possible page titles
  - Use a more specific title or choose from the options

- **PageError**: When a page doesn't exist
  - Check spelling or try searching first

- **WikipediaException**: General API errors
  - Network issues, rate limiting, etc.

### Example Error Handling

```python
from wikipedia.exceptions import DisambiguationError, PageError

try:
    # This will raise DisambiguationError
    result = await WikiTools.get_page_summary("Python")
except DisambiguationError as e:
    print(f"Ambiguous title. Options: {e.options[:5]}")
    # Try again with specific title
    result = await WikiTools.get_page_summary("Python (programming language)")

try:
    # This will raise PageError
    result = await WikiTools.get_page_summary("NonexistentPage123456")
except PageError:
    print("Page not found!")
```

### Testing

Comprehensive tests are available in `tests/asdrp/actions/search/test_wiki_tools.py`:

```bash
# Run WikiTools tests
pytest tests/asdrp/actions/search/test_wiki_tools.py -v

# Run with coverage
pytest tests/asdrp/actions/search/test_wiki_tools.py --cov=asdrp.actions.search
```

Test coverage includes:
- ✅ ToolsMeta integration
- ✅ All search methods
- ✅ Error handling (disambiguation, page not found)
- ✅ Input validation
- ✅ Edge cases
- ✅ Integration workflows

### Configuration

WikiTools uses the `wikipedia` package which requires no API keys.

**Rate Limiting**: Automatically configured with 30-second timeout.

**Language**: Default is English (`en`). Change with `set_language()`.

### Dependencies

```python
wikipedia>=1.4.0  # Already in pyproject.toml
```

### Architecture

WikiTools follows the same pattern as other action tools:

1. **ToolsMeta Metaclass**: Automatically discovers all `@classmethod` methods
2. **Async Methods**: All methods use `asyncio.run_in_executor` for thread-safe execution
3. **Type Hints**: Full type annotations for better IDE support
4. **Error Handling**: Comprehensive exception handling with descriptive messages
5. **Return Format**: Consistent dictionary returns with predictable keys

### Design Decisions

**Why async?**
- Consistent API with other action tools (GeoTools, YelpTools)
- Supports concurrent execution
- Non-blocking in agent workflows

**Why dictionaries instead of objects?**
- Easier serialization for API responses
- Compatible with OpenAI function calling format
- Simpler testing with mock data

**Why separate methods instead of one "query" method?**
- Clear, specific functionality
- Better for LLM function calling (specific tool descriptions)
- Easier to test individual features

### Future Enhancements

Potential additions:
- Page categories
- Page references/citations
- Revision history
- Page metadata (creation date, edit count)
- Multi-language page linking
- Geospatial queries (pages near location)

### See Also

- [Wikipedia Package Documentation](https://wikipedia.readthedocs.io/)
- [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page)
- [List of Wikipedias](https://en.wikipedia.org/wiki/List_of_Wikipedias)
