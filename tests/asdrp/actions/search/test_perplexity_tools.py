#############################################################################
# test_perplexity_tools.py
#
# Comprehensive tests for PerplexityTools class
#
# Test Coverage:
# - ToolsMeta integration (spec_functions, tool_list)
# - Async Perplexity methods with mocked responses
# - Error handling (authentication, rate limiting, connection errors)
# - Edge cases (empty results, malformed data, streaming)
# - Input validation (empty strings, None values, parameter ranges)
# - Search API (basic, with filters, with citations)
# - Chat API (basic, with system prompt, with recency filter)
# - Streaming API (metadata, tokens, citations, done)
# - Multi-turn chat (conversation context, validation)
#
#############################################################################

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from typing import AsyncGenerator
import httpx

from perplexity._exceptions import (
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
)

from asdrp.actions.search.perplexity_tools import (
    PerplexityTools,
    PerplexityException,
)
from asdrp.actions.tools_meta import ToolsMeta


#############################################################################
# Test Fixtures
#############################################################################

def create_mock_request():
    """Create a mock httpx.Request for exception testing."""
    return httpx.Request("GET", "https://api.perplexity.ai/test")

def create_mock_response(status_code=400):
    """Create a mock httpx.Response for exception testing."""
    request = create_mock_request()
    return httpx.Response(status_code, request=request)

@pytest.fixture
def mock_search_response():
    """Mock search API response."""
    mock_result = MagicMock()
    mock_result.title = "Test Article"
    mock_result.url = "https://example.com/article"
    mock_result.snippet = "This is a test snippet"
    mock_result.citations = ["https://source1.com", "https://source2.com"]

    mock_response = MagicMock()
    mock_response.results = [mock_result]
    mock_response.answer = "This is an AI-generated answer"
    mock_response.model = "sonar"
    return mock_response


@pytest.fixture
def mock_chat_response():
    """Mock chat completion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = "This is a test response"
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 50
    mock_usage.completion_tokens = 100
    mock_usage.total_tokens = 150

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "sonar"
    mock_response.usage = mock_usage
    mock_response.citations = ["https://citation1.com", "https://citation2.com"]
    return mock_response


@pytest.fixture
async def mock_stream_response():
    """Mock streaming response generator."""
    async def stream_generator():
        # Metadata chunk
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta = MagicMock()
        mock_chunk1.choices[0].delta.content = "Hello"
        mock_chunk1.choices[0].finish_reason = None
        yield mock_chunk1

        # Token chunk
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta = MagicMock()
        mock_chunk2.choices[0].delta.content = " world"
        mock_chunk2.choices[0].finish_reason = None
        yield mock_chunk2

        # Done chunk
        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock()]
        mock_chunk3.choices[0].delta = MagicMock()
        mock_chunk3.choices[0].delta.content = None
        mock_chunk3.choices[0].finish_reason = "stop"
        mock_chunk3.citations = ["https://citation.com"]
        yield mock_chunk3

    return stream_generator()


#############################################################################
# Test Classes
#############################################################################

class TestPerplexityToolsMetaIntegration:
    """Test PerplexityTools integration with ToolsMeta metaclass."""

    def test_tools_meta_integration(self):
        """Test that PerplexityTools properly integrates with ToolsMeta."""
        # Verify ToolsMeta attributes exist
        assert hasattr(PerplexityTools, 'spec_functions')
        assert hasattr(PerplexityTools, 'tool_list')
        assert isinstance(PerplexityTools.spec_functions, list)
        assert isinstance(PerplexityTools.tool_list, list)
        assert len(PerplexityTools.tool_list) == len(PerplexityTools.spec_functions)

    def test_all_methods_discovered(self):
        """Test that all public PerplexityTools methods are discovered."""
        expected_methods = [
            'search',
            'chat',
            'chat_stream',
            'multi_turn_chat',
        ]

        for method in expected_methods:
            assert method in PerplexityTools.spec_functions, \
                f"{method} should be in spec_functions"

    def test_excluded_methods_not_discovered(self):
        """Test that internal methods are excluded from discovery."""
        excluded = ['_setup_class', '_get_excluded_methods']
        for attr in excluded:
            assert attr not in PerplexityTools.spec_functions, \
                f"{attr} should not be in spec_functions"


class TestPerplexityToolsInitialization:
    """Test PerplexityTools class initialization and setup."""

    @patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test-api-key'})
    @patch('asdrp.actions.search.perplexity_tools.Perplexity')
    @patch('asdrp.actions.search.perplexity_tools.AsyncPerplexity')
    def test_setup_class_initializes_clients(self, mock_async_client, mock_client):
        """Test that _setup_class initializes clients when API key is available."""
        # Clear existing clients
        PerplexityTools._client = None
        PerplexityTools._async_client = None
        
        # Call _setup_class directly
        PerplexityTools._setup_class()

        # Verify clients were initialized
        mock_client.assert_called_once_with(api_key='test-api-key', timeout=60.0)
        mock_async_client.assert_called_once_with(api_key='test-api-key', timeout=60.0)

    @patch.dict(os.environ, {}, clear=True)
    def test_setup_class_missing_api_key(self):
        """Test that _setup_class doesn't raise when API key is missing (deferred initialization)."""
        # Ensure PERPLEXITY_API_KEY is not set
        if 'PERPLEXITY_API_KEY' in os.environ:
            del os.environ['PERPLEXITY_API_KEY']
        
        # Clear existing clients
        PerplexityTools._client = None
        PerplexityTools._async_client = None

        # _setup_class should not raise - initialization is deferred
        PerplexityTools._setup_class()
        
        # Clients should still be None (will be initialized on first use)
        assert PerplexityTools._client is None
        assert PerplexityTools._async_client is None


class TestPerplexityToolsSearch:
    """Test PerplexityTools.search method."""

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_search_basic(self, mock_client, mock_search_response):
        """Test basic search functionality."""
        mock_client.search.create = AsyncMock(return_value=mock_search_response)

        result = await PerplexityTools.search("test query", max_results=5)

        assert result['query'] == "test query"
        assert result['count'] == 1
        assert result['answer'] == "This is an AI-generated answer"
        assert len(result['results']) == 1
        assert result['results'][0]['title'] == "Test Article"
        assert result['results'][0]['url'] == "https://example.com/article"

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_search_with_recency_filter(self, mock_client, mock_search_response):
        """Test search with recency filter."""
        mock_client.search.create = AsyncMock(return_value=mock_search_response)

        result = await PerplexityTools.search(
            "test query",
            max_results=5,
            recency_filter="month"
        )

        assert result['query'] == "test query"
        mock_client.search.create.assert_called_once()
        call_kwargs = mock_client.search.create.call_args.kwargs
        assert call_kwargs['search_recency_filter'] == "month"

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_search_with_domain_filter(self, mock_client, mock_search_response):
        """Test search with domain filter."""
        mock_client.search.create = AsyncMock(return_value=mock_search_response)

        domains = ["example.com", "test.com"]
        result = await PerplexityTools.search(
            "test query",
            domain_filter=domains
        )

        assert result['query'] == "test query"
        call_kwargs = mock_client.search.create.call_args.kwargs
        assert call_kwargs['search_domain_filter'] == domains

    @pytest.mark.asyncio
    async def test_search_empty_query_raises_error(self):
        """Test that search raises ValueError for empty query."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await PerplexityTools.search("")

    @pytest.mark.asyncio
    async def test_search_invalid_max_results_raises_error(self):
        """Test that search raises ValueError for invalid max_results."""
        with pytest.raises(ValueError, match="max_results must be between 1 and 20"):
            await PerplexityTools.search("test", max_results=0)

        with pytest.raises(ValueError, match="max_results must be between 1 and 20"):
            await PerplexityTools.search("test", max_results=21)

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_search_authentication_error(self, mock_client):
        """Test search handles authentication errors."""
        response = create_mock_response(401)
        mock_client.search.create = AsyncMock(
            side_effect=AuthenticationError("Invalid API key", response=response, body=None)
        )

        with pytest.raises(AuthenticationError):
            await PerplexityTools.search("test query")

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_search_rate_limit_error(self, mock_client):
        """Test search handles rate limit errors."""
        response = create_mock_response(429)
        mock_client.search.create = AsyncMock(
            side_effect=RateLimitError("Rate limit exceeded", response=response, body=None)
        )

        with pytest.raises(RateLimitError):
            await PerplexityTools.search("test query")

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_search_connection_error(self, mock_client):
        """Test search handles connection errors."""
        request = create_mock_request()
        mock_client.search.create = AsyncMock(
            side_effect=APIConnectionError(message="Connection failed", request=request)
        )

        with pytest.raises(PerplexityException, match="Connection error"):
            await PerplexityTools.search("test query")


class TestPerplexityToolsChat:
    """Test PerplexityTools.chat method."""

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_basic(self, mock_client, mock_chat_response):
        """Test basic chat functionality."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        result = await PerplexityTools.chat("test message")

        assert result['message'] == "test message"
        assert result['response'] == "This is a test response"
        assert result['model'] == "sonar"
        assert result['finish_reason'] == "stop"
        assert result['usage']['total_tokens'] == 150

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_with_system_prompt(self, mock_client, mock_chat_response):
        """Test chat with system prompt."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        result = await PerplexityTools.chat(
            "test message",
            system_prompt="You are a helpful assistant"
        )

        assert result['response'] == "This is a test response"
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert len(call_kwargs['messages']) == 2
        assert call_kwargs['messages'][0]['role'] == "system"

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_with_parameters(self, mock_client, mock_chat_response):
        """Test chat with custom parameters."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        result = await PerplexityTools.chat(
            "test message",
            model="sonar-pro",
            max_tokens=500,
            temperature=0.5,
            search_recency="week"
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == "sonar-pro"
        assert call_kwargs['max_tokens'] == 500
        assert call_kwargs['temperature'] == 0.5
        assert call_kwargs['search_recency_filter'] == "week"

    @pytest.mark.asyncio
    async def test_chat_empty_message_raises_error(self):
        """Test that chat raises ValueError for empty message."""
        with pytest.raises(ValueError, match="Message cannot be empty"):
            await PerplexityTools.chat("")

    @pytest.mark.asyncio
    async def test_chat_invalid_max_tokens_raises_error(self):
        """Test that chat raises ValueError for invalid max_tokens."""
        with pytest.raises(ValueError, match="max_tokens must be between 1 and 4096"):
            await PerplexityTools.chat("test", max_tokens=0)

        with pytest.raises(ValueError, match="max_tokens must be between 1 and 4096"):
            await PerplexityTools.chat("test", max_tokens=5000)

    @pytest.mark.asyncio
    async def test_chat_invalid_temperature_raises_error(self):
        """Test that chat raises ValueError for invalid temperature."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            await PerplexityTools.chat("test", temperature=-0.1)

        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            await PerplexityTools.chat("test", temperature=2.1)

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_with_citations(self, mock_client, mock_chat_response):
        """Test chat with citations."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        result = await PerplexityTools.chat("test message", return_citations=True)

        assert result['citations'] == ["https://citation1.com", "https://citation2.com"]


class TestPerplexityToolsChatStream:
    """Test PerplexityTools.chat_stream method."""

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_stream_basic(self, mock_client, mock_stream_response):
        """Test basic streaming functionality."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream_response)

        chunks = []
        async for chunk in PerplexityTools.chat_stream("test message"):
            chunks.append(chunk)

        # Check chunk types - metadata first, then tokens, then citations, then done
        assert chunks[0]['type'] == 'metadata'
        # Find token chunks
        token_chunks = [c for c in chunks if c['type'] == 'token']
        assert len(token_chunks) >= 2
        assert token_chunks[0]['content'] == 'Hello'
        assert token_chunks[1]['content'] == ' world'

    @pytest.mark.asyncio
    async def test_chat_stream_empty_message_raises_error(self):
        """Test that chat_stream raises ValueError for empty message."""
        with pytest.raises(ValueError, match="Message cannot be empty"):
            async for _ in PerplexityTools.chat_stream(""):
                pass

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_stream_metadata_chunk(self, mock_client, mock_stream_response):
        """Test that metadata chunk is sent first."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream_response)

        chunks = []
        async for chunk in PerplexityTools.chat_stream("test"):
            chunks.append(chunk)
            if chunk['type'] == 'metadata':
                assert 'metadata' in chunk
                assert chunk['metadata']['model'] == 'sonar'
                break

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_stream_authentication_error(self, mock_client):
        """Test streaming handles authentication errors."""
        response = create_mock_response(401)
        mock_client.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError("Invalid API key", response=response, body=None)
        )

        with pytest.raises(AuthenticationError):
            async for _ in PerplexityTools.chat_stream("test"):
                pass


class TestPerplexityToolsMultiTurnChat:
    """Test PerplexityTools.multi_turn_chat method."""

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_multi_turn_chat_basic(self, mock_client, mock_chat_response):
        """Test basic multi-turn chat functionality."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]

        result = await PerplexityTools.multi_turn_chat(messages=messages)

        assert result['response'] == "This is a test response"
        assert result['conversation_length'] == 4  # 3 input + 1 response

    @pytest.mark.asyncio
    async def test_multi_turn_chat_empty_messages_raises_error(self):
        """Test that multi_turn_chat raises ValueError for empty messages."""
        with pytest.raises(ValueError, match="Messages must be a non-empty list"):
            await PerplexityTools.multi_turn_chat(messages=[])

    @pytest.mark.asyncio
    async def test_multi_turn_chat_invalid_message_format_raises_error(self):
        """Test that multi_turn_chat validates message format."""
        # Missing 'role' key
        with pytest.raises(ValueError, match="must have 'role' and 'content' keys"):
            await PerplexityTools.multi_turn_chat(
                messages=[{"content": "test"}]
            )

        # Missing 'content' key
        with pytest.raises(ValueError, match="must have 'role' and 'content' keys"):
            await PerplexityTools.multi_turn_chat(
                messages=[{"role": "user"}]
            )

        # Invalid role
        with pytest.raises(ValueError, match="invalid role"):
            await PerplexityTools.multi_turn_chat(
                messages=[{"role": "invalid", "content": "test"}]
            )

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_multi_turn_chat_with_system_message(self, mock_client, mock_chat_response):
        """Test multi-turn chat with system message."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]

        result = await PerplexityTools.multi_turn_chat(messages=messages)

        assert result['response'] == "This is a test response"
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['messages'][0]['role'] == "system"

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_multi_turn_chat_with_citations(self, mock_client, mock_chat_response):
        """Test multi-turn chat returns citations."""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        messages = [{"role": "user", "content": "test"}]
        result = await PerplexityTools.multi_turn_chat(
            messages=messages,
            return_citations=True
        )

        assert result['citations'] == ["https://citation1.com", "https://citation2.com"]


class TestPerplexityToolsEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_search_no_results(self, mock_client):
        """Test search handles no results gracefully."""
        mock_response = MagicMock()
        mock_response.results = []
        mock_response.answer = "No results found"
        mock_response.model = "sonar"

        mock_client.search.create = AsyncMock(return_value=mock_response)

        result = await PerplexityTools.search("test query")

        assert result['count'] == 0
        assert result['results'] == []
        assert result['answer'] == "No results found"

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_chat_no_choices(self, mock_client):
        """Test chat handles response with no choices."""
        mock_response = MagicMock()
        mock_response.choices = []
        mock_response.model = "sonar"
        mock_response.usage = None

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await PerplexityTools.chat("test message")

        assert result['response'] == ""
        assert result['finish_reason'] == "unknown"

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_timeout_error(self, mock_client):
        """Test timeout error handling."""
        request = create_mock_request()
        mock_client.search.create = AsyncMock(
            side_effect=APITimeoutError(request=request)
        )

        with pytest.raises(APITimeoutError):
            await PerplexityTools.search("test query")

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_bad_request_error(self, mock_client):
        """Test bad request error handling."""
        response = create_mock_response(400)
        mock_client.chat.completions.create = AsyncMock(
            side_effect=BadRequestError("Invalid parameters", response=response, body=None)
        )

        with pytest.raises(PerplexityException, match="Invalid chat request"):
            await PerplexityTools.chat("test message")

    @pytest.mark.asyncio
    @patch('asdrp.actions.search.perplexity_tools.PerplexityTools._async_client')
    async def test_generic_api_error(self, mock_client):
        """Test generic API error handling."""
        request = create_mock_request()
        mock_client.search.create = AsyncMock(
            side_effect=APIError("Generic API error", request=request, body=None)
        )

        with pytest.raises(PerplexityException, match="Search API error"):
            await PerplexityTools.search("test query")


class TestPerplexityToolsInputValidation:
    """Test input validation for all methods."""

    @pytest.mark.asyncio
    async def test_search_whitespace_query_raises_error(self):
        """Test that search rejects whitespace-only query."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await PerplexityTools.search("   ")

    @pytest.mark.asyncio
    async def test_chat_whitespace_message_raises_error(self):
        """Test that chat rejects whitespace-only message."""
        with pytest.raises(ValueError, match="Message cannot be empty"):
            await PerplexityTools.chat("   ")

    @pytest.mark.asyncio
    async def test_chat_stream_whitespace_message_raises_error(self):
        """Test that chat_stream rejects whitespace-only message."""
        with pytest.raises(ValueError, match="Message cannot be empty"):
            async for _ in PerplexityTools.chat_stream("   "):
                pass

    @pytest.mark.asyncio
    async def test_multi_turn_chat_not_list_raises_error(self):
        """Test that multi_turn_chat rejects non-list messages."""
        with pytest.raises(ValueError, match="Messages must be a non-empty list"):
            await PerplexityTools.multi_turn_chat(messages="not a list")

    @pytest.mark.asyncio
    async def test_multi_turn_chat_non_dict_message_raises_error(self):
        """Test that multi_turn_chat rejects non-dict messages."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            await PerplexityTools.multi_turn_chat(messages=["not a dict"])


class TestPerplexityToolsIntegration:
    """Integration tests (marked as slow, require real API)."""

    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search_integration(self):
        """Test real search API call."""
        if not os.getenv("PERPLEXITY_API_KEY"):
            pytest.skip("PERPLEXITY_API_KEY not set")

        result = await PerplexityTools.search(
            "Python programming language",
            max_results=3
        )

        assert result['count'] > 0
        assert len(result['results']) > 0
        assert result['query'] == "Python programming language"

    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_chat_integration(self):
        """Test real chat API call."""
        if not os.getenv("PERPLEXITY_API_KEY"):
            pytest.skip("PERPLEXITY_API_KEY not set")

        result = await PerplexityTools.chat(
            "What is 2+2?",
            max_tokens=50
        )

        assert result['response']
        assert result['usage']['total_tokens'] > 0

    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_streaming_integration(self):
        """Test real streaming API call."""
        if not os.getenv("PERPLEXITY_API_KEY"):
            pytest.skip("PERPLEXITY_API_KEY not set")

        chunks = []
        async for chunk in PerplexityTools.chat_stream(
            "Count to 3",
            max_tokens=50
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert any(c['type'] == 'metadata' for c in chunks)
        assert any(c['type'] == 'token' for c in chunks)


#############################################################################
# Test Execution
#############################################################################

if __name__ == "__main__":
    # Run all tests except slow/integration tests
    pytest.main([__file__, "-v", "-m", "not slow"])
