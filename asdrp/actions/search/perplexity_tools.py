#############################################################################
# perplexity_tools.py
#
# Perplexity AI tools for search and chat completions using the perplexityai package
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import asyncio
import os
from typing import Any, Dict, List, Optional, AsyncGenerator, Literal

from perplexity import Perplexity, AsyncPerplexity
from perplexity._exceptions import (
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
)

from asdrp.actions.tools_meta import ToolsMeta

# Default models
DEFAULT_MODEL = "sonar"
DEFAULT_SEARCH_MODEL = "sonar"

# Default parameters
DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 60.0


class PerplexityException(Exception):
    """Base exception for Perplexity tools."""
    pass


class PerplexityTools(metaclass=ToolsMeta):
    """
    Tools for AI-powered search and chat using Perplexity AI.

    This class uses the ToolsMeta metaclass which automatically:
    - Discovers all public @classmethod decorated methods
    - Creates `spec_functions` list containing method names
    - Creates `tool_list` containing wrapped function tools ready for agent frameworks

    Perplexity AI combines live web search with multiple AI models to provide
    up-to-date answers backed by verifiable citations. It excels at:
    - Real-time web search with citation verification
    - Comprehensive research with autonomous analysis
    - Complex question answering with up-to-date sources

    The client is configured via the `_setup_class()` hook method using the
    PERPLEXITY_API_KEY environment variable.

    Usage:
    ------
    ```python
    from asdrp.actions.search.perplexity_tools import PerplexityTools

    # Use the automatically generated tool_list
    from agents import Agent
    agent = Agent(tools=PerplexityTools.tool_list)

    # Or call methods directly
    results = await PerplexityTools.search("latest AI developments")
    response = await PerplexityTools.chat("Explain quantum computing")
    async for chunk in PerplexityTools.chat_stream("Tell me about Mars"):
        print(chunk)
    ```

    Authentication:
    --------------
    Set the PERPLEXITY_API_KEY environment variable:
    ```bash
    export PERPLEXITY_API_KEY="your-api-key-here"
    ```

    Or in .env file:
    ```
    PERPLEXITY_API_KEY=your-api-key-here
    ```

    Notes:
    ------
    - All methods are async to support concurrent execution
    - Comprehensive error handling for API failures
    - Supports both synchronous and streaming responses
    - Provides citation verification for all search results
    """

    # ------------- Automatically populated by ToolsMeta -------------
    # List of method names & wrapped function tools to expose as tools
    spec_functions: List[str]
    tool_list: List[Any]

    # Class-level clients (initialized in _setup_class)
    _client: Optional[Perplexity] = None
    _async_client: Optional[AsyncPerplexity] = None

    @classmethod
    def _setup_class(cls) -> None:
        """
        Set up Perplexity clients with API key from environment.

        This method is called automatically by ToolsMeta during class creation.
        It initializes clients only if PERPLEXITY_API_KEY is available.
        If not available, initialization is deferred until first use.
        """
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if api_key:
            cls._client = Perplexity(api_key=api_key, timeout=DEFAULT_TIMEOUT)
            cls._async_client = AsyncPerplexity(api_key=api_key, timeout=DEFAULT_TIMEOUT)

    @classmethod
    def _init_clients_if_needed(cls) -> None:
        """Initialize clients if not already initialized. Raises PerplexityException if API key missing."""
        if cls._async_client is None:
            api_key = os.getenv("PERPLEXITY_API_KEY")
            if not api_key:
                raise PerplexityException(
                    "PERPLEXITY_API_KEY environment variable is not set. "
                    "Please set it to use Perplexity tools."
                )
            cls._client = Perplexity(api_key=api_key, timeout=DEFAULT_TIMEOUT)
            cls._async_client = AsyncPerplexity(api_key=api_key, timeout=DEFAULT_TIMEOUT)

    @classmethod
    async def search(
        cls,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        recency_filter: Optional[Literal["hour", "day", "week", "month", "year"]] = None,
        domain_filter: Optional[List[str]] = None,
        return_citations: bool = True,
        return_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Perform an AI-powered web search with Perplexity.

        This method uses Perplexity's search API to get ranked web search results
        with advanced filtering capabilities. Results include AI-generated summaries
        and verifiable citations.

        Args:
            query (str): Search query string. Cannot be empty.
            max_results (int): Maximum number of results to return. Default is 5.
                Range: 1-20.
            recency_filter (Optional[str]): Filter results by recency.
                Options: "hour", "day", "week", "month", "year".
                None means no filter.
            domain_filter (Optional[List[str]]): List of domains to restrict search to.
                Example: ["wikipedia.org", "arxiv.org"]. None means all domains.
            return_citations (bool): Include citation URLs in results. Default is True.
            return_images (bool): Include image URLs in results. Default is False.
                Note: Image search may not be available for all queries.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'query' (str): The search query
                - 'results' (List[Dict]): List of search results, each containing:
                    - 'title' (str): Result title
                    - 'url' (str): Result URL
                    - 'snippet' (str): Result summary/snippet
                    - 'citations' (List[str]): Citation URLs (if return_citations=True)
                - 'answer' (str): AI-generated answer to the query
                - 'count' (int): Number of results returned
                - 'model' (str): Model used for search

        Raises:
            ValueError: If query is empty or max_results is out of range.
            AuthenticationError: If API key is invalid.
            RateLimitError: If rate limit is exceeded.
            PerplexityException: For other API errors.

        Example:
            >>> results = await PerplexityTools.search(
            ...     "quantum computing breakthroughs 2024",
            ...     max_results=5,
            ...     recency_filter="month"
            ... )
            >>> print(results['answer'])
            >>> for result in results['results']:
            ...     print(f"{result['title']}: {result['url']}")
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty or None.")

        if not (1 <= max_results <= 20):
            raise ValueError("max_results must be between 1 and 20.")

        try:
            cls._init_clients_if_needed()
            
            # Build search request with optional filters
            search_kwargs: Dict[str, Any] = {
                "query": query.strip(),
                "max_results": max_results,
            }

            if recency_filter:
                search_kwargs["search_recency_filter"] = recency_filter

            if domain_filter:
                search_kwargs["search_domain_filter"] = domain_filter

            # Perform search using async client
            search_response = await cls._async_client.search.create(**search_kwargs)

            # Extract results
            results = []
            for result in search_response.results:
                result_dict = {
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet if hasattr(result, 'snippet') else "",
                }
                if return_citations and hasattr(result, 'citations'):
                    result_dict["citations"] = result.citations
                results.append(result_dict)

            return {
                "query": query.strip(),
                "results": results,
                "answer": search_response.answer if hasattr(search_response, 'answer') else "",
                "count": len(results),
                "model": search_response.model if hasattr(search_response, 'model') else DEFAULT_SEARCH_MODEL,
            }

        except (AuthenticationError, RateLimitError, APITimeoutError) as e:
            # Re-raise these exceptions as-is
            raise
        except BadRequestError as e:
            raise PerplexityException(f"Invalid search request: {e}")
        except APIConnectionError as e:
            raise PerplexityException(f"Connection error: {e}")
        except APIError as e:
            raise PerplexityException(f"Search API error: {e}")
        except Exception as e:
            raise PerplexityException(f"Unexpected error during search: {e}")

    @classmethod
    async def chat(
        cls,
        message: str,
        model: str = DEFAULT_MODEL,
        system_prompt: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        return_citations: bool = True,
        search_recency: Optional[Literal["hour", "day", "week", "month", "year"]] = None,
    ) -> Dict[str, Any]:
        """
        Generate an AI response using Perplexity's chat completions API.

        This method uses Perplexity's chat API to generate responses with
        web-grounded reasoning. It combines AI language models with real-time
        web search to provide up-to-date, cited answers.

        Args:
            message (str): User message/question. Cannot be empty.
            model (str): Model to use. Default is "sonar".
                Options: "sonar", "sonar-pro", "sonar-reasoning", etc.
            system_prompt (Optional[str]): System prompt to guide the model's behavior.
                None uses default behavior.
            max_tokens (int): Maximum tokens in the response. Default is 1024.
                Range: 1-4096.
            temperature (float): Sampling temperature for randomness. Default is 0.7.
                Range: 0.0-2.0. Lower is more deterministic, higher is more creative.
            return_citations (bool): Include citation sources in response. Default is True.
            search_recency (Optional[str]): Recency filter for web search sources.
                Options: "hour", "day", "week", "month", "year".
                None means no filter.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'message' (str): User message
                - 'response' (str): AI-generated response
                - 'citations' (List[str]): List of citation URLs (if return_citations=True)
                - 'model' (str): Model used
                - 'usage' (Dict): Token usage statistics:
                    - 'prompt_tokens' (int): Tokens in the prompt
                    - 'completion_tokens' (int): Tokens in the completion
                    - 'total_tokens' (int): Total tokens used
                - 'finish_reason' (str): Reason for completion (e.g., "stop", "length")

        Raises:
            ValueError: If message is empty, max_tokens or temperature out of range.
            AuthenticationError: If API key is invalid.
            RateLimitError: If rate limit is exceeded.
            PerplexityException: For other API errors.

        Example:
            >>> response = await PerplexityTools.chat(
            ...     "Explain the latest breakthroughs in fusion energy",
            ...     model="sonar-pro",
            ...     temperature=0.5,
            ...     search_recency="month"
            ... )
            >>> print(response['response'])
            >>> print(f"Citations: {response['citations']}")
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty or None.")

        if not (1 <= max_tokens <= 4096):
            raise ValueError("max_tokens must be between 1 and 4096.")

        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0.")

        try:
            cls._init_clients_if_needed()
            
            # Build messages list
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": message.strip()
            })

            # Build chat request
            chat_kwargs: Dict[str, Any] = {
                "messages": messages,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if search_recency:
                chat_kwargs["search_recency_filter"] = search_recency

            # Perform chat completion using async client
            completion = await cls._async_client.chat.completions.create(**chat_kwargs)

            # Extract response
            response_content = completion.choices[0].message.content if completion.choices else ""

            # Extract citations if available
            citations = []
            if return_citations and hasattr(completion, 'citations'):
                citations = completion.citations

            # Extract usage information
            usage = {}
            if hasattr(completion, 'usage') and completion.usage:
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }

            finish_reason = completion.choices[0].finish_reason if completion.choices else "unknown"

            return {
                "message": message.strip(),
                "response": response_content,
                "citations": citations,
                "model": completion.model if hasattr(completion, 'model') else model,
                "usage": usage,
                "finish_reason": finish_reason,
            }

        except (AuthenticationError, RateLimitError, APITimeoutError) as e:
            # Re-raise these exceptions as-is
            raise
        except BadRequestError as e:
            raise PerplexityException(f"Invalid chat request: {e}")
        except APIConnectionError as e:
            raise PerplexityException(f"Connection error: {e}")
        except APIError as e:
            raise PerplexityException(f"Chat API error: {e}")
        except Exception as e:
            raise PerplexityException(f"Unexpected error during chat: {e}")

    @classmethod
    async def chat_stream(
        cls,
        message: str,
        model: str = DEFAULT_MODEL,
        system_prompt: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        search_recency: Optional[Literal["hour", "day", "week", "month", "year"]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming AI responses using Perplexity's chat API.

        This method streams response tokens in real-time, allowing for
        progressive display of AI-generated content. Ideal for interactive
        applications where immediate feedback is valuable.

        Args:
            message (str): User message/question. Cannot be empty.
            model (str): Model to use. Default is "sonar".
            system_prompt (Optional[str]): System prompt to guide behavior.
            max_tokens (int): Maximum tokens in response. Default is 1024.
            temperature (float): Sampling temperature. Default is 0.7.
            search_recency (Optional[str]): Recency filter for sources.
                Options: "hour", "day", "week", "month", "year".

        Yields:
            Dict[str, Any]: Streaming chunks with:
                - 'type' (str): Chunk type - "metadata", "token", "citations", or "done"
                - 'content' (Optional[str]): Token content (for type="token")
                - 'metadata' (Optional[Dict]): Metadata (for type="metadata")
                - 'citations' (Optional[List[str]]): Citations (for type="citations")
                - 'finish_reason' (Optional[str]): Finish reason (for type="done")

        Raises:
            ValueError: If message is empty, max_tokens or temperature out of range.
            AuthenticationError: If API key is invalid.
            RateLimitError: If rate limit is exceeded.
            PerplexityException: For other API errors.

        Example:
            >>> async for chunk in PerplexityTools.chat_stream(
            ...     "Explain neural networks",
            ...     model="sonar",
            ...     temperature=0.8
            ... ):
            ...     if chunk['type'] == 'metadata':
            ...         print(f"Model: {chunk['metadata']['model']}")
            ...     elif chunk['type'] == 'token':
            ...         print(chunk['content'], end='', flush=True)
            ...     elif chunk['type'] == 'citations':
            ...         print(f"\nCitations: {chunk['citations']}")
            ...     elif chunk['type'] == 'done':
            ...         print(f"\nFinished: {chunk['finish_reason']}")
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty or None.")

        if not (1 <= max_tokens <= 4096):
            raise ValueError("max_tokens must be between 1 and 4096.")

        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0.")

        try:
            cls._init_clients_if_needed()
            
            # Build messages list
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": message.strip()
            })

            # Build streaming request
            stream_kwargs: Dict[str, Any] = {
                "messages": messages,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }

            if search_recency:
                stream_kwargs["search_recency_filter"] = search_recency

            # Send metadata first
            yield {
                "type": "metadata",
                "metadata": {
                    "model": model,
                    "message": message.strip(),
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            }

            # Stream completion
            stream = await cls._async_client.chat.completions.create(**stream_kwargs)

            citations_sent = False
            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Stream content tokens
                if hasattr(delta, 'content') and delta.content:
                    yield {
                        "type": "token",
                        "content": delta.content
                    }

                # Send citations once if available
                if not citations_sent and hasattr(chunk, 'citations') and chunk.citations:
                    yield {
                        "type": "citations",
                        "citations": chunk.citations
                    }
                    citations_sent = True

                # Send finish reason if available
                if chunk.choices[0].finish_reason:
                    yield {
                        "type": "done",
                        "finish_reason": chunk.choices[0].finish_reason
                    }
                    break

        except (AuthenticationError, RateLimitError, APITimeoutError) as e:
            # Re-raise these exceptions as-is
            raise
        except BadRequestError as e:
            raise PerplexityException(f"Invalid streaming request: {e}")
        except APIConnectionError as e:
            raise PerplexityException(f"Connection error: {e}")
        except APIError as e:
            raise PerplexityException(f"Streaming API error: {e}")
        except Exception as e:
            raise PerplexityException(f"Unexpected error during streaming: {e}")

    @classmethod
    async def multi_turn_chat(
        cls,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        return_citations: bool = True,
    ) -> Dict[str, Any]:
        """
        Continue a multi-turn conversation with Perplexity AI.

        This method allows for conversation context by accepting a list of
        previous messages. Useful for building chatbots and conversational
        agents that maintain context across multiple exchanges.

        Args:
            messages (List[Dict[str, str]]): List of conversation messages.
                Each message must have 'role' ("system", "user", or "assistant")
                and 'content' (message text).
                Example: [
                    {"role": "user", "content": "What is Python?"},
                    {"role": "assistant", "content": "Python is a programming language..."},
                    {"role": "user", "content": "Who created it?"}
                ]
            model (str): Model to use. Default is "sonar".
            max_tokens (int): Maximum tokens in response. Default is 1024.
            temperature (float): Sampling temperature. Default is 0.7.
            return_citations (bool): Include citations. Default is True.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'response' (str): AI-generated response
                - 'citations' (List[str]): Citation URLs (if return_citations=True)
                - 'model' (str): Model used
                - 'usage' (Dict): Token usage statistics
                - 'conversation_length' (int): Total messages in conversation

        Raises:
            ValueError: If messages list is empty or invalid.
            AuthenticationError: If API key is invalid.
            RateLimitError: If rate limit is exceeded.
            PerplexityException: For other API errors.

        Example:
            >>> conversation = [
            ...     {"role": "user", "content": "What is machine learning?"},
            ...     {"role": "assistant", "content": "Machine learning is..."},
            ...     {"role": "user", "content": "Give me an example."}
            ... ]
            >>> response = await PerplexityTools.multi_turn_chat(
            ...     messages=conversation,
            ...     model="sonar-pro"
            ... )
            >>> print(response['response'])
        """
        if not messages or not isinstance(messages, list):
            raise ValueError("Messages must be a non-empty list.")

        # Validate message format
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message at index {i} must be a dictionary.")
            if 'role' not in msg or 'content' not in msg:
                raise ValueError(f"Message at index {i} must have 'role' and 'content' keys.")
            if msg['role'] not in ['system', 'user', 'assistant']:
                raise ValueError(f"Message at index {i} has invalid role: {msg['role']}")

        if not (1 <= max_tokens <= 4096):
            raise ValueError("max_tokens must be between 1 and 4096.")

        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0.")

        try:
            cls._init_clients_if_needed()
            
            # Build chat request
            chat_kwargs: Dict[str, Any] = {
                "messages": messages,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # Perform chat completion
            completion = await cls._async_client.chat.completions.create(**chat_kwargs)

            # Extract response
            response_content = completion.choices[0].message.content if completion.choices else ""

            # Extract citations
            citations = []
            if return_citations and hasattr(completion, 'citations'):
                citations = completion.citations

            # Extract usage
            usage = {}
            if hasattr(completion, 'usage') and completion.usage:
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }

            return {
                "response": response_content,
                "citations": citations,
                "model": completion.model if hasattr(completion, 'model') else model,
                "usage": usage,
                "conversation_length": len(messages) + 1,  # +1 for the response
            }

        except (AuthenticationError, RateLimitError, APITimeoutError) as e:
            # Re-raise these exceptions as-is
            raise
        except BadRequestError as e:
            raise PerplexityException(f"Invalid chat request: {e}")
        except APIConnectionError as e:
            raise PerplexityException(f"Connection error: {e}")
        except APIError as e:
            raise PerplexityException(f"Chat API error: {e}")
        except Exception as e:
            raise PerplexityException(f"Unexpected error during multi-turn chat: {e}")


#---------------------------------------------
# main tests
#---------------------------------------------

async def test_perplexity_tools():
    """Simple smoke test for PerplexityTools methods."""

    print("Testing search:")
    try:
        result = await PerplexityTools.search(
            "artificial intelligence breakthroughs 2024",
            max_results=3,
            recency_filter="month"
        )
        print(f"Query: {result['query']}")
        print(f"Answer: {result['answer'][:200]}...")
        print(f"Found {result['count']} results:")
        for i, r in enumerate(result['results'], 1):
            print(f"  {i}. {r['title']}")
            print(f"     {r['url']}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting chat:")
    try:
        result = await PerplexityTools.chat(
            "Explain quantum entanglement in simple terms",
            model="sonar",
            max_tokens=200,
            temperature=0.5
        )
        print(f"Message: {result['message']}")
        print(f"Response: {result['response']}")
        print(f"Model: {result['model']}")
        print(f"Citations: {result['citations'][:3] if result['citations'] else 'None'}")
        print(f"Usage: {result['usage']}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting chat_stream:")
    try:
        print("Response: ", end='', flush=True)
        async for chunk in PerplexityTools.chat_stream(
            "What is photosynthesis?",
            max_tokens=150,
            temperature=0.7
        ):
            if chunk['type'] == 'token':
                print(chunk['content'], end='', flush=True)
            elif chunk['type'] == 'citations':
                print(f"\n\nCitations: {chunk['citations'][:3]}")
            elif chunk['type'] == 'done':
                print(f"\n\nFinish reason: {chunk['finish_reason']}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting multi_turn_chat:")
    try:
        conversation = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level programming language known for its simplicity and versatility."},
            {"role": "user", "content": "Who created it?"}
        ]
        result = await PerplexityTools.multi_turn_chat(
            messages=conversation,
            max_tokens=100
        )
        print(f"Response: {result['response']}")
        print(f"Conversation length: {result['conversation_length']} turns")
        print(f"Citations: {result['citations'][:3] if result['citations'] else 'None'}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_perplexity_tools())
