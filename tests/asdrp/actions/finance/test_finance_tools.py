#############################################################################
# test_finance_tools.py
#
# Comprehensive tests for FinanceTools class
#
# Test Coverage:
# - ToolsMeta integration (spec_functions, tool_list)
# - All public API methods with mocked responses
# - Error handling (invalid inputs, API errors)
# - Edge cases (empty results, boundary values)
# - Input validation
#
#############################################################################

import pytest
import importlib
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List

from asdrp.actions.finance.finance_tools import FinanceTools
from asdrp.actions.tools_meta import ToolsMeta


class TestFinanceToolsMetaIntegration:
    """Test FinanceTools integration with ToolsMeta metaclass."""
    
    def test_tools_meta_integration(self):
        """Test that FinanceTools properly integrates with ToolsMeta."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        # Verify ToolsMeta attributes exist
        assert hasattr(FinanceTools, 'spec_functions')
        assert hasattr(FinanceTools, 'tool_list')
        assert isinstance(FinanceTools.spec_functions, list)
        assert isinstance(FinanceTools.tool_list, list)
        assert len(FinanceTools.tool_list) == len(FinanceTools.spec_functions)
    
    def test_all_methods_discovered(self):
        """Test that all public FinanceTools methods are discovered."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        expected_methods = [
            'download_market_data',
            'get_actions',
            'get_balance_sheet',
            'get_calendar',
            'get_cashflow',
            'get_dividends',
            'get_financials',
            'get_historical_data',
            'get_income_statement',
            'get_news',
            'get_options',
            'get_recommendations',
            'get_splits',
            'get_ticker_info',
        ]
        
        for method in expected_methods:
            assert method in FinanceTools.spec_functions, \
                f"{method} should be in spec_functions"
    
    def test_excluded_methods_not_discovered(self):
        """Test that internal methods are excluded from discovery."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        excluded = ['_setup_class', '_get_excluded_methods']
        for attr in excluded:
            assert attr not in FinanceTools.spec_functions, \
                f"{attr} should not be in spec_functions"


class TestFinanceToolsInitialization:
    """Test FinanceTools class initialization and setup."""
    
    def test_setup_class_verifies_yfinance(self):
        """Test that _setup_class verifies yfinance is installed."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        # Verify setup method exists
        assert hasattr(FinanceTools, '_setup_class')
        assert callable(FinanceTools._setup_class)


class TestFinanceToolsGetTickerInfo:
    """Test FinanceTools.get_ticker_info method."""
    
    @pytest.mark.asyncio
    async def test_get_ticker_info_success(self):
        """Test successful ticker info retrieval."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_info = {
            'longName': 'Apple Inc.',
            'sector': 'Technology',
            'marketCap': 3000000000000
        }
        
        mock_ticker = MagicMock()
        mock_ticker.info = mock_info
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_info])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_ticker_info("AAPL")
                
                assert result == mock_info
    
    @pytest.mark.asyncio
    async def test_get_ticker_info_empty_symbol(self):
        """Test that empty symbol raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            await FinanceTools.get_ticker_info("")
    
    @pytest.mark.asyncio
    async def test_get_ticker_info_none_symbol(self):
        """Test that None symbol raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            await FinanceTools.get_ticker_info(None)


class TestFinanceToolsGetHistoricalData:
    """Test FinanceTools.get_historical_data method."""
    
    @pytest.mark.asyncio
    async def test_get_historical_data_success(self):
        """Test successful historical data retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        # Create mock DataFrame
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102, 103, 104],
            'High': [105, 106, 107, 108, 109],
            'Low': [99, 100, 101, 102, 103],
            'Close': [104, 105, 106, 107, 108],
            'Volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        }, index=dates)
        
        mock_ticker = MagicMock()
        mock_ticker.history = MagicMock(return_value=mock_data)
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_data])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_historical_data("AAPL", period="1mo")
                
                assert 'data' in result
                assert result['symbol'] == 'AAPL'
                assert result['period'] == '1mo'
    
    @pytest.mark.asyncio
    async def test_get_historical_data_invalid_period(self):
        """Test that invalid period raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Period must be one of"):
            await FinanceTools.get_historical_data("AAPL", period="invalid")
    
    @pytest.mark.asyncio
    async def test_get_historical_data_invalid_interval(self):
        """Test that invalid interval raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Interval must be one of"):
            await FinanceTools.get_historical_data("AAPL", interval="invalid")
    
    @pytest.mark.asyncio
    async def test_get_historical_data_empty_symbol(self):
        """Test that empty symbol raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            await FinanceTools.get_historical_data("")


class TestFinanceToolsGetFinancials:
    """Test FinanceTools.get_financials method."""
    
    @pytest.mark.asyncio
    async def test_get_financials_success(self):
        """Test successful financials retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_financials = pd.DataFrame({'2023': [1000000], '2022': [900000]})
        mock_balance_sheet = pd.DataFrame({'2023': [500000], '2022': [450000]})
        mock_cashflow = pd.DataFrame({'2023': [200000], '2022': [180000]})
        
        mock_ticker = MagicMock()
        mock_ticker.financials = mock_financials
        mock_ticker.balance_sheet = mock_balance_sheet
        mock_ticker.cashflow = mock_cashflow
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[
            mock_ticker,
            mock_financials,
            mock_balance_sheet,
            mock_cashflow
        ])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_financials("AAPL")
                
                assert 'income_stmt' in result
                assert 'balance_sheet' in result
                assert 'cashflow' in result
                assert result['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_get_financials_empty_symbol(self):
        """Test that empty symbol raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            await FinanceTools.get_financials("")


class TestFinanceToolsGetIncomeStatement:
    """Test FinanceTools.get_income_statement method."""
    
    @pytest.mark.asyncio
    async def test_get_income_statement_success(self):
        """Test successful income statement retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_financials = pd.DataFrame({'2023': [1000000], '2022': [900000]})
        mock_ticker = MagicMock()
        mock_ticker.financials = mock_financials
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_financials])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_income_statement("AAPL")
                
                assert 'income_stmt' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetBalanceSheet:
    """Test FinanceTools.get_balance_sheet method."""
    
    @pytest.mark.asyncio
    async def test_get_balance_sheet_success(self):
        """Test successful balance sheet retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_balance_sheet = pd.DataFrame({'2023': [500000], '2022': [450000]})
        mock_ticker = MagicMock()
        mock_ticker.balance_sheet = mock_balance_sheet
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_balance_sheet])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_balance_sheet("AAPL")
                
                assert 'balance_sheet' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetCashflow:
    """Test FinanceTools.get_cashflow method."""
    
    @pytest.mark.asyncio
    async def test_get_cashflow_success(self):
        """Test successful cashflow retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_cashflow = pd.DataFrame({'2023': [200000], '2022': [180000]})
        mock_ticker = MagicMock()
        mock_ticker.cashflow = mock_cashflow
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_cashflow])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_cashflow("AAPL")
                
                assert 'cashflow' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetDividends:
    """Test FinanceTools.get_dividends method."""
    
    @pytest.mark.asyncio
    async def test_get_dividends_success(self):
        """Test successful dividends retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        dates = pd.date_range('2024-01-01', periods=3, freq='ME')
        mock_dividends = pd.Series([0.25, 0.25, 0.25], index=dates)
        mock_ticker = MagicMock()
        mock_ticker.dividends = mock_dividends
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_dividends])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_dividends("AAPL")
                
                assert 'dividends' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetSplits:
    """Test FinanceTools.get_splits method."""
    
    @pytest.mark.asyncio
    async def test_get_splits_success(self):
        """Test successful splits retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        dates = pd.date_range('2024-01-01', periods=2, freq='YE')
        mock_splits = pd.Series([2.0, 1.0], index=dates)
        mock_ticker = MagicMock()
        mock_ticker.splits = mock_splits
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_splits])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_splits("AAPL")
                
                assert 'splits' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetActions:
    """Test FinanceTools.get_actions method."""
    
    @pytest.mark.asyncio
    async def test_get_actions_success(self):
        """Test successful actions retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        dates = pd.date_range('2024-01-01', periods=3, freq='ME')
        mock_actions = pd.DataFrame({
            'Dividends': [0.25, 0.25, 0.25],
            'Stock Splits': [0.0, 0.0, 0.0]
        }, index=dates)
        mock_ticker = MagicMock()
        mock_ticker.actions = mock_actions
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_actions])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_actions("AAPL")
                
                assert 'actions' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetRecommendations:
    """Test FinanceTools.get_recommendations method."""
    
    @pytest.mark.asyncio
    async def test_get_recommendations_success(self):
        """Test successful recommendations retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        mock_recommendations = pd.DataFrame({
            'Firm': ['Firm1', 'Firm2', 'Firm3', 'Firm4', 'Firm5'],
            'To Grade': ['Buy', 'Hold', 'Buy', 'Strong Buy', 'Hold']
        }, index=dates)
        mock_ticker = MagicMock()
        mock_ticker.recommendations = mock_recommendations
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_recommendations])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_recommendations("AAPL")
                
                assert 'recommendations' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetCalendar:
    """Test FinanceTools.get_calendar method."""
    
    @pytest.mark.asyncio
    async def test_get_calendar_success(self):
        """Test successful calendar retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_calendar = pd.DataFrame({
            'Earnings Date': ['2024-01-15', '2024-04-15'],
            'Earnings Estimate': [1.50, 1.60]
        })
        mock_ticker = MagicMock()
        mock_ticker.calendar = mock_calendar
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_calendar])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_calendar("AAPL")
                
                assert 'calendar' in result
                assert result['symbol'] == 'AAPL'


class TestFinanceToolsGetNews:
    """Test FinanceTools.get_news method."""
    
    @pytest.mark.asyncio
    async def test_get_news_success(self):
        """Test successful news retrieval."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        # yfinance news structure has nested 'content' key
        mock_news = [
            {
                'id': 'news1',
                'content': {
                    'title': 'Apple Reports Strong Earnings',
                    'summary': 'Apple reported strong earnings',
                    'pubDate': '2024-01-01T10:00:00Z',
                    'provider': {'displayName': 'Reuters'},
                    'canonicalUrl': {'url': 'https://example.com/news1'}
                }
            },
            {
                'id': 'news2',
                'content': {
                    'title': 'Apple Stock Rises',
                    'summary': 'Apple stock rises',
                    'pubDate': '2024-01-02T10:00:00Z',
                    'provider': {'displayName': 'Bloomberg'},
                    'canonicalUrl': {'url': 'https://example.com/news2'}
                }
            }
        ]
        mock_ticker = MagicMock()
        mock_ticker.news = mock_news
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_news])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_news("AAPL")
                
                assert isinstance(result, list)
                assert len(result) == 2
                assert result[0]['content']['title'] == 'Apple Reports Strong Earnings'
    
    @pytest.mark.asyncio
    async def test_get_news_empty_result(self):
        """Test news retrieval with empty result."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_ticker = MagicMock()
        mock_ticker.news = None
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, None])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_news("AAPL")
                
                assert result == []


class TestFinanceToolsGetOptions:
    """Test FinanceTools.get_options method."""
    
    @pytest.mark.asyncio
    async def test_get_options_success(self):
        """Test successful options retrieval."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_options = ['2024-01-19', '2024-02-16', '2024-03-15']
        mock_ticker = MagicMock()
        mock_ticker.options = mock_options
        
        mock_calls = pd.DataFrame({'strike': [150, 155], 'lastPrice': [5.0, 3.0]})
        mock_puts = pd.DataFrame({'strike': [150, 155], 'lastPrice': [4.0, 2.0]})
        mock_option_chain = MagicMock()
        mock_option_chain.calls = mock_calls
        mock_option_chain.puts = mock_puts
        mock_ticker.option_chain = MagicMock(return_value=mock_option_chain)
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[
            mock_ticker,
            mock_options,
            mock_option_chain
        ])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_options("AAPL", expiration="2024-01-19")
                
                assert 'expirations' in result
                assert 'calls' in result
                assert 'puts' in result
                assert result['expiration'] == '2024-01-19'
    
    @pytest.mark.asyncio
    async def test_get_options_no_expiration(self):
        """Test options retrieval without expiration."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_options = ['2024-01-19', '2024-02-16']
        mock_ticker = MagicMock()
        mock_ticker.options = mock_options
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=[mock_ticker, mock_options])
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', return_value=mock_ticker):
                result = await FinanceTools.get_options("AAPL")
                
                assert 'expirations' in result
                assert result['expirations'] == mock_options


class TestFinanceToolsDownloadMarketData:
    """Test FinanceTools.download_market_data method."""
    
    @pytest.mark.asyncio
    async def test_download_market_data_success(self):
        """Test successful market data download."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102, 103, 104],
            'High': [105, 106, 107, 108, 109],
            'Low': [99, 100, 101, 102, 103],
            'Close': [104, 105, 106, 107, 108],
            'Volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        }, index=dates)
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_data)
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.download', return_value=mock_data):
                result = await FinanceTools.download_market_data(["AAPL", "MSFT"], period="1mo")
                
                assert 'data' in result
                assert result['symbols'] == ["AAPL", "MSFT"]
                assert result['period'] == '1mo'
    
    @pytest.mark.asyncio
    async def test_download_market_data_single_symbol(self):
        """Test market data download with single symbol string."""
        import pandas as pd
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102, 103, 104],
            'Close': [104, 105, 106, 107, 108]
        }, index=dates)
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_data)
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.download', return_value=mock_data):
                result = await FinanceTools.download_market_data("AAPL", period="1mo")
                
                assert result['symbols'] == ["AAPL"]
    
    @pytest.mark.asyncio
    async def test_download_market_data_empty_symbols(self):
        """Test that empty symbols raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Symbols cannot be empty"):
            await FinanceTools.download_market_data("")
    
    @pytest.mark.asyncio
    async def test_download_market_data_invalid_period(self):
        """Test that invalid period raises ValueError."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        with pytest.raises(ValueError, match="Period must be one of"):
            await FinanceTools.download_market_data("AAPL", period="invalid")


class TestFinanceToolsErrorHandling:
    """Test FinanceTools error handling."""
    
    @pytest.mark.asyncio
    async def test_api_error_propagation(self):
        """Test that API errors are properly propagated."""
        import importlib
        import asdrp.actions.finance.finance_tools
        importlib.reload(asdrp.actions.finance.finance_tools)
        from asdrp.actions.finance.finance_tools import FinanceTools
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=Exception("API Error"))
        
        with patch('asdrp.actions.finance.finance_tools.asyncio.get_running_loop', return_value=mock_loop):
            with patch('asdrp.actions.finance.finance_tools.yf.Ticker', side_effect=Exception("API Error")):
                with pytest.raises(Exception, match="Failed to get ticker info"):
                    await FinanceTools.get_ticker_info("AAPL")

