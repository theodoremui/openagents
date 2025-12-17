#############################################################################
# finance_tools.py
#
# Financial data tools using yfinance library
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import asyncio
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    yf = None
    pd = None

from asdrp.actions.tools_meta import ToolsMeta
from asdrp.util.dict_utils import DictUtils

# Timeout for API calls
TIMEOUT_SECONDS = 30


class FinanceTools(metaclass=ToolsMeta):
    """
    Tools for retrieving financial, company, market and news information using yfinance.
    
    This class uses the ToolsMeta metaclass which automatically:
    - Discovers all public @classmethod decorated methods
    - Creates `spec_functions` list containing method names
    - Creates `tool_list` containing wrapped function tools ready for agent frameworks
    
    yfinance library initialization is handled via the `_setup_class()` hook method.
    yfinance does not require API keys - it uses Yahoo Finance public API.
    
    Usage:
    ------
    ```python
    from asdrp.actions.finance.finance_tools import FinanceTools
    
    # Use the automatically generated tool_list
    from agents import Agent
    agent = Agent(tools=FinanceTools.tool_list)
    
    # Or call methods directly
    info = await FinanceTools.get_ticker_info("AAPL")
    history = await FinanceTools.get_historical_data("AAPL", period="1mo")
    ```
    """
    # ------------- Automatically populated by ToolsMeta -------------
    # List of method names & wrapped function tools to expose as tools
    spec_functions: List[str]
    tool_list: List[Any]
    
    @classmethod
    def _setup_class(cls) -> None:
        """
        Set up yfinance library.
        
        This method is called automatically by ToolsMeta during class creation.
        yfinance does not require API keys or special initialization - it uses
        Yahoo Finance public API. This method verifies that yfinance is installed.
        
        Raises:
            ImportError: If yfinance library is not installed.
        """
        if yf is None:
            raise ImportError(
                "yfinance library is required. Install it with: pip install yfinance"
            )
    
    @classmethod
    def _get_excluded_methods(cls) -> set[str]:
        """
        Exclude internal methods from tool discovery.
        
        Returns:
            Set of attribute names to exclude from being discovered as tools.
            This ensures that internal configuration attributes are not included
            in the tool_list.
        """
        return set()
    
    @classmethod
    async def get_ticker_info(cls, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a ticker symbol.
        
        Retrieves company information including business summary, financial metrics,
        key statistics, and other relevant data from Yahoo Finance.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL').
                Can be a single symbol or multiple symbols separated by spaces.
            
        Returns:
            Dict[str, Any]: Dictionary containing ticker information including:
                - Company name, sector, industry
                - Market cap, enterprise value
                - Financial metrics (P/E ratio, EPS, revenue, etc.)
                - Key statistics
                - Business summary
                - And many more fields
            
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            info = await loop.run_in_executor(None, lambda: ticker.info)
            return info if info else {}
        except Exception as e:
            raise Exception(f"Failed to get ticker info for '{symbol}': {e}")
    
    @classmethod
    async def get_historical_data(
        cls,
        symbol: str,
        period: Optional[str] = "1mo",
        interval: Optional[str] = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        prepost: bool = False,
        auto_adjust: bool = True,
        actions: bool = True,
        repair: bool = False
    ) -> Dict[str, Any]:
        """
        Get historical market data for a ticker symbol.
        
        Retrieves historical price data including open, high, low, close, volume,
        and optionally dividends and splits.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
            period (Optional[str]): Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
                Default: "1mo"
            interval (Optional[str]): Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo.
                Default: "1d"
            start (Optional[str]): Download start date string (YYYY-MM-DD) or datetime.
                If specified, period is ignored.
            end (Optional[str]): Download end date string (YYYY-MM-DD) or datetime.
                If specified, period is ignored.
            prepost (bool): Include pre and post market data. Default: False
            auto_adjust (bool): Adjust all OHLC automatically. Default: True
            actions (bool): Download dividends and stock splits data. Default: True
            repair (bool): Repair obvious price errors. Default: False
        
        Returns:
            Dict[str, Any]: Dictionary containing historical data with keys:
                - 'data': DataFrame with columns: Open, High, Low, Close, Volume, Dividends, Stock Splits
                - 'symbol': The ticker symbol
                - 'period': The period used
                - 'interval': The interval used
        
        Raises:
            ValueError: If symbol is empty or invalid parameters provided.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        # Validate period if provided
        valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
        if period and period not in valid_periods:
            raise ValueError(f"Period must be one of {valid_periods}, got '{period}'.")
        
        # Validate interval if provided
        valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
        if interval and interval not in valid_intervals:
            raise ValueError(f"Interval must be one of {valid_intervals}, got '{interval}'.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            
            # Build parameters for history call
            history_params = DictUtils.build_params(
                period=period,
                interval=interval,
                start=start,
                end=end,
                prepost=prepost,
                auto_adjust=auto_adjust,
                actions=actions,
                repair=repair
            )
            
            # Get historical data
            history_func = partial(ticker.history, **history_params)
            hist_data = await loop.run_in_executor(None, history_func)
            
            # Convert DataFrame to dict for JSON serialization
            if hist_data is not None and not hist_data.empty:
                # Convert DataFrame to dict with proper formatting
                data_dict = hist_data.to_dict(orient='index')
                # Convert index (dates) to strings
                result = {
                    'data': {str(idx): {k: (float(v) if pd.notna(v) else None) for k, v in row.items()} 
                            for idx, row in data_dict.items()},
                    'symbol': symbol.strip(),
                    'period': period,
                    'interval': interval,
                    'start': start,
                    'end': end
                }
            else:
                result = {
                    'data': {},
                    'symbol': symbol.strip(),
                    'period': period,
                    'interval': interval,
                    'start': start,
                    'end': end
                }
            
            return result
        except Exception as e:
            raise Exception(f"Failed to get historical data for '{symbol}': {e}")
    
    @classmethod
    async def get_financials(cls, symbol: str) -> Dict[str, Any]:
        """
        Get financial statements (income statement, balance sheet, cash flow) for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'income_stmt': Income statement data
                - 'balance_sheet': Balance sheet data
                - 'cashflow': Cash flow statement data
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            
            # Get all financial statements
            financials = await loop.run_in_executor(None, lambda: ticker.financials)
            balance_sheet = await loop.run_in_executor(None, lambda: ticker.balance_sheet)
            cashflow = await loop.run_in_executor(None, lambda: ticker.cashflow)
            
            result = {
                'symbol': symbol.strip(),
                'income_stmt': financials.to_dict(orient='index') if financials is not None and not financials.empty else {},
                'balance_sheet': balance_sheet.to_dict(orient='index') if balance_sheet is not None and not balance_sheet.empty else {},
                'cashflow': cashflow.to_dict(orient='index') if cashflow is not None and not cashflow.empty else {}
            }
            
            return result
        except Exception as e:
            raise Exception(f"Failed to get financials for '{symbol}': {e}")
    
    @classmethod
    async def get_income_statement(cls, symbol: str) -> Dict[str, Any]:
        """
        Get income statement (financials) for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing income statement data.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            financials = await loop.run_in_executor(None, lambda: ticker.financials)
            
            if financials is not None and not financials.empty:
                return {
                    'symbol': symbol.strip(),
                    'income_stmt': financials.to_dict(orient='index')
                }
            else:
                return {'symbol': symbol.strip(), 'income_stmt': {}}
        except Exception as e:
            raise Exception(f"Failed to get income statement for '{symbol}': {e}")
    
    @classmethod
    async def get_balance_sheet(cls, symbol: str) -> Dict[str, Any]:
        """
        Get balance sheet for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing balance sheet data.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            balance_sheet = await loop.run_in_executor(None, lambda: ticker.balance_sheet)
            
            if balance_sheet is not None and not balance_sheet.empty:
                return {
                    'symbol': symbol.strip(),
                    'balance_sheet': balance_sheet.to_dict(orient='index')
                }
            else:
                return {'symbol': symbol.strip(), 'balance_sheet': {}}
        except Exception as e:
            raise Exception(f"Failed to get balance sheet for '{symbol}': {e}")
    
    @classmethod
    async def get_cashflow(cls, symbol: str) -> Dict[str, Any]:
        """
        Get cash flow statement for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing cash flow statement data.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            cashflow = await loop.run_in_executor(None, lambda: ticker.cashflow)
            
            if cashflow is not None and not cashflow.empty:
                return {
                    'symbol': symbol.strip(),
                    'cashflow': cashflow.to_dict(orient='index')
                }
            else:
                return {'symbol': symbol.strip(), 'cashflow': {}}
        except Exception as e:
            raise Exception(f"Failed to get cashflow for '{symbol}': {e}")
    
    @classmethod
    async def get_dividends(cls, symbol: str) -> Dict[str, Any]:
        """
        Get dividend history for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing dividend data with dates as keys.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            dividends = await loop.run_in_executor(None, lambda: ticker.dividends)
            
            if dividends is not None and not dividends.empty:
                return {
                    'symbol': symbol.strip(),
                    'dividends': {str(idx): float(val) if pd.notna(val) else None 
                                 for idx, val in dividends.items()}
                }
            else:
                return {'symbol': symbol.strip(), 'dividends': {}}
        except Exception as e:
            raise Exception(f"Failed to get dividends for '{symbol}': {e}")
    
    @classmethod
    async def get_splits(cls, symbol: str) -> Dict[str, Any]:
        """
        Get stock split history for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing split data with dates as keys.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            splits = await loop.run_in_executor(None, lambda: ticker.splits)
            
            if splits is not None and not splits.empty:
                return {
                    'symbol': symbol.strip(),
                    'splits': {str(idx): float(val) if pd.notna(val) else None 
                              for idx, val in splits.items()}
                }
            else:
                return {'symbol': symbol.strip(), 'splits': {}}
        except Exception as e:
            raise Exception(f"Failed to get splits for '{symbol}': {e}")
    
    @classmethod
    async def get_actions(cls, symbol: str) -> Dict[str, Any]:
        """
        Get corporate actions (dividends and splits) for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing dividends and splits data.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            actions = await loop.run_in_executor(None, lambda: ticker.actions)
            
            if actions is not None and not actions.empty:
                return {
                    'symbol': symbol.strip(),
                    'actions': {str(idx): {k: (float(v) if pd.notna(v) else None) 
                                          for k, v in row.items()} 
                               for idx, row in actions.to_dict(orient='index').items()}
                }
            else:
                return {'symbol': symbol.strip(), 'actions': {}}
        except Exception as e:
            raise Exception(f"Failed to get actions for '{symbol}': {e}")
    
    @classmethod
    async def get_recommendations(cls, symbol: str) -> Dict[str, Any]:
        """
        Get analyst recommendations for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing recommendation data.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            recommendations = await loop.run_in_executor(None, lambda: ticker.recommendations)
            
            if recommendations is not None and not recommendations.empty:
                return {
                    'symbol': symbol.strip(),
                    'recommendations': recommendations.to_dict(orient='index')
                }
            else:
                return {'symbol': symbol.strip(), 'recommendations': {}}
        except Exception as e:
            raise Exception(f"Failed to get recommendations for '{symbol}': {e}")
    
    @classmethod
    async def get_calendar(cls, symbol: str) -> Dict[str, Any]:
        """
        Get earnings calendar for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            Dict[str, Any]: Dictionary containing calendar data including earnings dates.
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            calendar = await loop.run_in_executor(None, lambda: ticker.calendar)
            
            if calendar is not None and not calendar.empty:
                return {
                    'symbol': symbol.strip(),
                    'calendar': calendar.to_dict(orient='index')
                }
            else:
                return {'symbol': symbol.strip(), 'calendar': {}}
        except Exception as e:
            raise Exception(f"Failed to get calendar for '{symbol}': {e}")
    
    @classmethod
    async def get_news(cls, symbol: str) -> List[Dict[str, Any]]:
        """
        Get news articles related to a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
        
        Returns:
            List[Dict[str, Any]]: List of news article dictionaries. Each article contains:
                - id: Article identifier
                - content: Dictionary containing:
                    - title: Article title
                    - summary: Article summary
                    - pubDate: Publication date (ISO format)
                    - displayTime: Display time
                    - provider: Dictionary with displayName and url
                    - canonicalUrl: Dictionary with article URL
                    - thumbnail: Dictionary with image URLs and metadata
                    - And other metadata fields
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        
        Note:
            The news structure from yfinance has a nested format where article details
            are contained within a 'content' key. This method returns the raw structure
            as provided by yfinance. To access the title, use: news[0]['content']['title']
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            news = await loop.run_in_executor(None, lambda: ticker.news)
            
            return news if news else []
        except Exception as e:
            raise Exception(f"Failed to get news for '{symbol}': {e}")
    
    @classmethod
    async def get_options(cls, symbol: str, expiration: Optional[str] = None) -> Dict[str, Any]:
        """
        Get options chain data for a ticker.
        
        Args:
            symbol (str): The ticker symbol (e.g., 'AAPL').
            expiration (Optional[str]): Specific expiration date (YYYY-MM-DD).
                If None, returns all available expiration dates.
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'expirations': List of available expiration dates
                - 'options': Options chain data if expiration is specified
        
        Raises:
            ValueError: If symbol is empty or None.
            Exception: If the yfinance API call fails.
        """
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or None.")
        
        try:
            loop = asyncio.get_running_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol.strip())
            options = await loop.run_in_executor(None, lambda: ticker.options)
            
            result = {
                'symbol': symbol.strip(),
                'expirations': list(options) if options else []
            }
            
            # If expiration is specified, get options chain for that date
            if expiration:
                if expiration not in options:
                    raise ValueError(f"Expiration '{expiration}' not found. Available: {list(options)}")
                
                opt_chain = await loop.run_in_executor(
                    None,
                    lambda: ticker.option_chain(expiration)
                )
                
                result['expiration'] = expiration
                result['calls'] = opt_chain.calls.to_dict(orient='records') if opt_chain.calls is not None and not opt_chain.calls.empty else []
                result['puts'] = opt_chain.puts.to_dict(orient='records') if opt_chain.puts is not None and not opt_chain.puts.empty else []
            
            return result
        except Exception as e:
            raise Exception(f"Failed to get options for '{symbol}': {e}")
    
    @classmethod
    async def download_market_data(
        cls,
        symbols: Union[str, List[str]],
        period: Optional[str] = "1mo",
        interval: Optional[str] = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        prepost: bool = False,
        auto_adjust: bool = True,
        actions: bool = True,
        repair: bool = False,
        group_by: str = "ticker",
        progress: bool = False
    ) -> Dict[str, Any]:
        """
        Download historical market data for one or more ticker symbols.
        
        This is a convenience method that wraps yfinance.download() for downloading
        data for multiple tickers at once.
        
        Args:
            symbols (Union[str, List[str]]): Single ticker symbol or list of symbols.
            period (Optional[str]): Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
                Default: "1mo"
            interval (Optional[str]): Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo.
                Default: "1d"
            start (Optional[str]): Download start date string (YYYY-MM-DD) or datetime.
            end (Optional[str]): Download end date string (YYYY-MM-DD) or datetime.
            prepost (bool): Include pre and post market data. Default: False
            auto_adjust (bool): Adjust all OHLC automatically. Default: True
            actions (bool): Download dividends and stock splits data. Default: True
            repair (bool): Repair obvious price errors. Default: False
            group_by (str): Group by 'ticker' or 'column'. Default: "ticker"
            progress (bool): Show download progress. Default: False
        
        Returns:
            Dict[str, Any]: Dictionary containing downloaded market data.
        
        Raises:
            ValueError: If symbols is empty or invalid parameters provided.
            Exception: If the yfinance API call fails.
        """
        if not symbols:
            raise ValueError("Symbols cannot be empty or None.")
        
        # Convert single symbol to list
        if isinstance(symbols, str):
            symbols = [symbols]
        
        # Validate period if provided
        valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
        if period and period not in valid_periods:
            raise ValueError(f"Period must be one of {valid_periods}, got '{period}'.")
        
        # Validate interval if provided
        valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
        if interval and interval not in valid_intervals:
            raise ValueError(f"Interval must be one of {valid_intervals}, got '{interval}'.")
        
        try:
            loop = asyncio.get_running_loop()
            
            # Build parameters for download call
            download_params = DictUtils.build_params(
                period=period,
                interval=interval,
                start=start,
                end=end,
                prepost=prepost,
                auto_adjust=auto_adjust,
                actions=actions,
                repair=repair,
                group_by=group_by,
                progress=progress
            )
            
            # Download data
            download_func = partial(yf.download, symbols, **download_params)
            data = await loop.run_in_executor(None, download_func)
            
            # Convert DataFrame to dict
            if data is not None and not data.empty:
                return {
                    'symbols': symbols,
                    'data': data.to_dict(orient='index'),
                    'period': period,
                    'interval': interval
                }
            else:
                return {
                    'symbols': symbols,
                    'data': {},
                    'period': period,
                    'interval': interval
                }
        except Exception as e:
            raise Exception(f"Failed to download market data for '{symbols}': {e}")


#---------------------------------------------
# main tests
#---------------------------------------------

async def test_finance():
    print("Testing get_ticker_info:")
    try:
        info = await FinanceTools.get_ticker_info("AAPL")
        print(f"Company: {info.get('longName', 'N/A')}")
        print(f"Sector: {info.get('sector', 'N/A')}")
        print(f"Market Cap: {info.get('marketCap', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nTesting get_historical_data:")
    try:
        history = await FinanceTools.get_historical_data("AAPL", period="1mo")
        print(f"Retrieved {len(history.get('data', {}))} data points")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nTesting get_news:")
    try:
        news = await FinanceTools.get_news("AAPL")
        print(f"Found {len(news)} news articles")
        if news:
            # News structure has nested content: news[0]['content']['title']
            content = news[0].get('content', {})
            title = content.get('title', 'N/A')
            print(f"  Latest: {title}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_finance())

