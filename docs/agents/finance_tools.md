# Finance Tools Documentation

## Overview

The `FinanceTools` class provides comprehensive access to financial, company, market, and news information using the `yfinance` library. It follows the same pattern as other action tools in the codebase, using the `ToolsMeta` metaclass for automatic tool discovery and creation.

## Features

- **Ticker Information**: Company details, financial metrics, key statistics
- **Historical Data**: Price history with customizable periods and intervals
- **Financial Statements**: Income statements, balance sheets, cash flow statements
- **Corporate Actions**: Dividends, stock splits, earnings calendar
- **Analyst Data**: Recommendations and earnings estimates
- **Options Data**: Options chain data with expiration dates
- **News**: Latest news articles related to tickers
- **Bulk Downloads**: Download data for multiple tickers simultaneously

## Installation

The `yfinance` package is required:

```bash
pip install yfinance
```

Note: `yfinance` does not require API keys - it uses Yahoo Finance's public API.

## Usage

### Basic Usage

```python
from asdrp.actions.finance.finance_tools import FinanceTools

# Get ticker information
info = await FinanceTools.get_ticker_info("AAPL")
print(f"Company: {info['longName']}")
print(f"Market Cap: {info['marketCap']}")

# Get historical data
history = await FinanceTools.get_historical_data("AAPL", period="1mo")
print(f"Retrieved {len(history['data'])} data points")

# Get news
news = await FinanceTools.get_news("AAPL")
for article in news[:5]:
    print(f"- {article['title']}")
```

### Using with Agent Framework

```python
from asdrp.actions.finance.finance_tools import FinanceTools
from agents import Agent

# Use the automatically generated tool_list
agent = Agent(
    name="finance_agent",
    instructions="You are a financial data assistant.",
    tools=FinanceTools.tool_list  # Automatically contains all public methods
)

# Access method names
print(FinanceTools.spec_functions)
# ['download_market_data', 'get_actions', 'get_balance_sheet', ...]
```

## API Reference

### get_ticker_info

Get comprehensive information about a ticker symbol.

**Parameters:**
- `symbol` (str): The ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')

**Returns:**
- `Dict[str, Any]`: Dictionary containing ticker information including company name, sector, market cap, financial metrics, etc.

**Example:**
```python
info = await FinanceTools.get_ticker_info("AAPL")
print(info['longName'])  # Apple Inc.
print(info['sector'])     # Technology
print(info['marketCap'])  # 3000000000000
```

### get_historical_data

Get historical market data for a ticker symbol.

**Parameters:**
- `symbol` (str): The ticker symbol
- `period` (Optional[str]): Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max. Default: "1mo"
- `interval` (Optional[str]): Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo. Default: "1d"
- `start` (Optional[str]): Start date (YYYY-MM-DD). If specified, period is ignored.
- `end` (Optional[str]): End date (YYYY-MM-DD). If specified, period is ignored.
- `prepost` (bool): Include pre/post market data. Default: False
- `auto_adjust` (bool): Adjust OHLC automatically. Default: True
- `actions` (bool): Include dividends and splits. Default: True
- `repair` (bool): Repair price errors. Default: False

**Returns:**
- `Dict[str, Any]`: Dictionary containing historical data with dates as keys

**Example:**
```python
# Get 1 month of daily data
history = await FinanceTools.get_historical_data("AAPL", period="1mo")

# Get specific date range
history = await FinanceTools.get_historical_data(
    "AAPL",
    start="2024-01-01",
    end="2024-01-31",
    interval="1d"
)
```

### get_financials

Get all financial statements (income statement, balance sheet, cash flow) for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing income_stmt, balance_sheet, and cashflow

**Example:**
```python
financials = await FinanceTools.get_financials("AAPL")
print(financials['income_stmt'])
print(financials['balance_sheet'])
print(financials['cashflow'])
```

### get_income_statement

Get income statement (financials) for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing income statement data

### get_balance_sheet

Get balance sheet for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing balance sheet data

### get_cashflow

Get cash flow statement for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing cash flow statement data

### get_dividends

Get dividend history for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing dividend data with dates as keys

**Example:**
```python
dividends = await FinanceTools.get_dividends("AAPL")
for date, amount in dividends['dividends'].items():
    print(f"{date}: ${amount}")
```

### get_splits

Get stock split history for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing split data with dates as keys

### get_actions

Get corporate actions (dividends and splits) for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing dividends and splits data

### get_recommendations

Get analyst recommendations for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing recommendation data

**Example:**
```python
recommendations = await FinanceTools.get_recommendations("AAPL")
print(recommendations['recommendations'])
```

### get_calendar

Get earnings calendar for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `Dict[str, Any]`: Dictionary containing calendar data including earnings dates

### get_news

Get news articles related to a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol

**Returns:**
- `List[Dict[str, Any]]`: List of news article dictionaries. Each article has:
  - `id`: Article identifier
  - `content`: Dictionary containing:
    - `title`: Article title
    - `summary`: Article summary
    - `pubDate`: Publication date (ISO format)
    - `displayTime`: Display time
    - `provider`: Dictionary with `displayName` and `url`
    - `canonicalUrl`: Dictionary with article URL (`url` field)
    - `thumbnail`: Dictionary with image URLs and metadata
    - And other metadata fields

**Example:**
```python
news = await FinanceTools.get_news("AAPL")
for article in news[:5]:
    content = article.get('content', {})
    title = content.get('title', 'N/A')
    provider = content.get('provider', {}).get('displayName', 'Unknown')
    url = content.get('canonicalUrl', {}).get('url', 'N/A')
    print(f"{title} - {provider}")
    print(f"Link: {url}\n")
```

**Note:**
The news structure from yfinance uses a nested format where article details are contained within a `content` key. To access the title, use: `news[0]['content']['title']`

### get_options

Get options chain data for a ticker.

**Parameters:**
- `symbol` (str): The ticker symbol
- `expiration` (Optional[str]): Specific expiration date (YYYY-MM-DD). If None, returns available expiration dates.

**Returns:**
- `Dict[str, Any]`: Dictionary containing:
  - `expirations`: List of available expiration dates
  - `calls`: Call options data (if expiration specified)
  - `puts`: Put options data (if expiration specified)

**Example:**
```python
# Get available expiration dates
options = await FinanceTools.get_options("AAPL")
print(f"Available expirations: {options['expirations']}")

# Get options chain for specific expiration
options = await FinanceTools.get_options("AAPL", expiration="2024-01-19")
print(f"Calls: {len(options['calls'])}")
print(f"Puts: {len(options['puts'])}")
```

### download_market_data

Download historical market data for one or more ticker symbols.

**Parameters:**
- `symbols` (Union[str, List[str]]): Single ticker symbol or list of symbols
- `period` (Optional[str]): Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max. Default: "1mo"
- `interval` (Optional[str]): Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo. Default: "1d"
- `start` (Optional[str]): Start date (YYYY-MM-DD)
- `end` (Optional[str]): End date (YYYY-MM-DD)
- `prepost` (bool): Include pre/post market data. Default: False
- `auto_adjust` (bool): Adjust OHLC automatically. Default: True
- `actions` (bool): Include dividends and splits. Default: True
- `repair` (bool): Repair price errors. Default: False
- `group_by` (str): Group by 'ticker' or 'column'. Default: "ticker"
- `progress` (bool): Show download progress. Default: False

**Returns:**
- `Dict[str, Any]`: Dictionary containing downloaded market data

**Example:**
```python
# Download data for multiple tickers
data = await FinanceTools.download_market_data(
    ["AAPL", "MSFT", "GOOGL"],
    period="1y",
    interval="1d"
)
print(f"Downloaded data for: {data['symbols']}")
```

## Error Handling

All methods raise appropriate exceptions:

- `ValueError`: For invalid input parameters (empty symbols, invalid periods/intervals, etc.)
- `Exception`: For API call failures with descriptive error messages

**Example:**
```python
try:
    info = await FinanceTools.get_ticker_info("INVALID_SYMBOL")
except Exception as e:
    print(f"Error: {e}")

try:
    history = await FinanceTools.get_historical_data("AAPL", period="invalid")
except ValueError as e:
    print(f"Invalid parameter: {e}")
```

## Design Principles

The `FinanceTools` class follows best practices:

- **DRY (Don't Repeat Yourself)**: Common patterns are reused across methods
- **SOLID Principles**: Single responsibility, open/closed, dependency inversion
- **Modularity**: Each method has a clear, focused purpose
- **Extensibility**: Easy to add new methods following the same pattern
- **Robustness**: Comprehensive error handling and input validation
- **Occam's Razor**: Simple, direct implementation without unnecessary complexity

## Implementation Pattern

The class follows the same pattern as `MapTools` and `GeoTools`:

1. Uses `ToolsMeta` metaclass for automatic tool discovery
2. All public methods are `@classmethod` decorated
3. Async methods use `asyncio.run_in_executor` for synchronous yfinance calls
4. Input validation with clear error messages
5. Consistent return format (dictionaries/lists)
6. Comprehensive docstrings

## Testing

Comprehensive tests are available in `tests/asdrp/actions/finance/test_finance_tools.py`:

- ToolsMeta integration tests
- All public API methods with mocked responses
- Error handling tests
- Edge cases and boundary values
- Input validation tests

Run tests with:
```bash
pytest tests/asdrp/actions/finance/test_finance_tools.py
```

## Limitations

- Rate limiting: Yahoo Finance may rate limit requests if too many are made in a short period
- Data availability: Some data may not be available for all tickers
- Historical data: Very old historical data may be limited
- Options data: Only available for US stocks with options trading

## See Also

- [yfinance Documentation](https://ranaroussi.github.io/yfinance/)
- [ToolsMeta Documentation](./toolsmeta.md)
- [Actions Package README](../asdrp/actions/README.md)

