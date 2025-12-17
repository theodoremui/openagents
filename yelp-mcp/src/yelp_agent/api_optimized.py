"""
Optimized Yelp Fusion AI API client with caching, connection pooling, and performance improvements.

Key optimizations:
1. HTTP connection pooling (reuse httpx.AsyncClient)
2. Response caching with TTL
3. Parallel request handling
4. Reduced timeouts with early termination
5. Request deduplication
"""

from dotenv import load_dotenv, find_dotenv
# Load .env file but DON'T override environment variables passed from parent process
# This allows the OpenAgents server to pass YELP_API_KEY via subprocess environment
load_dotenv(find_dotenv(), override=False)

import os
import hashlib
import json
import time
from typing import Any, Optional, TypedDict
from functools import lru_cache
import asyncio
from collections import OrderedDict

import httpx

from .loggers import logger


class UserContext(TypedDict):
    latitude: float
    longitude: float


class ResponseCache:
    """
    In-memory LRU cache for Yelp API responses.
    
    Features:
    - TTL-based expiration
    - LRU eviction
    - Query-based deduplication
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries (5 minutes default)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    def _make_key(self, query: str, chat_id: Optional[str] = None, 
                  user_context: Optional[UserContext] = None) -> str:
        """Create cache key from query parameters."""
        key_data = {
            "query": query.lower().strip(),
            "chat_id": chat_id,
            "user_context": user_context
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def get(self, query: str, chat_id: Optional[str] = None,
                  user_context: Optional[UserContext] = None) -> Optional[Any]:
        """Get cached response if available and not expired."""
        async with self._lock:
            key = self._make_key(query, chat_id, user_context)
            
            if key not in self._cache:
                return None
            
            timestamp, value = self._cache[key]
            
            # Check expiration
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            return value
    
    async def set(self, query: str, value: Any, chat_id: Optional[str] = None,
                  user_context: Optional[UserContext] = None) -> None:
        """Store response in cache."""
        async with self._lock:
            key = self._make_key(query, chat_id, user_context)
            
            # Remove if exists
            if key in self._cache:
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = (time.time(), value)
            
            # Evict oldest if over limit
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()


# Global cache instance
_cache = ResponseCache(max_size=200, ttl_seconds=300)  # 5 minute TTL

# Global HTTP client with connection pooling
_http_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    """
    Get or create global HTTP client with connection pooling.
    
    Reuses connections across requests for better performance.
    """
    global _http_client
    
    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            # Create client with optimized settings
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0,      # 5s connection timeout
                    read=35.0,        # 35s read timeout (increased from 25s for complex queries)
                    write=5.0,        # 5s write timeout
                    pool=10.0,        # 10s pool timeout
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=10,  # Keep connections alive
                    max_connections=20,             # Max concurrent connections
                ),
                http2=True,  # Enable HTTP/2 for better performance
            )
            logger.info("Created new HTTP client with connection pooling")
        
        return _http_client


async def close_http_client() -> None:
    """Close global HTTP client."""
    global _http_client
    
    async with _client_lock:
        if _http_client and not _http_client.is_closed:
            await _http_client.aclose()
            _http_client = None
            logger.info("Closed HTTP client")


async def make_fusion_ai_request(
    query: str,
    chat_id: Optional[str] = None,
    user_context: Optional[UserContext] = None,
    use_cache: bool = True,
    timeout: float = 35.0,  # Increased from 25s to 35s for complex queries
) -> Optional[Any]:
    """
    Make optimized Fusion AI request with caching and connection pooling.

    Args:
        query: Natural language query
        chat_id: Optional chat ID for conversation context
        user_context: Optional user location context
        use_cache: Whether to use response cache (default: True)
        timeout: Request timeout in seconds (default: 35s, increased for reliability)

    Returns:
        JSON response or None on error
    """
    yelp_api_key = os.getenv("YELP_API_KEY")
    
    if not yelp_api_key:
        logger.warning(
            "YELP_API_KEY is missing from the environment. Unable to make authorized requests."
        )
        return None
    
    # Check cache first
    # Note: We cache follow-up queries too, using chat_id as part of the key
    # This improves performance for repeated follow-up questions
    if use_cache:
        cached = await _cache.get(query, chat_id, user_context)
        if cached is not None:
            cache_type = "follow-up" if chat_id else "new"
            logger.info(f"Cache hit ({cache_type}) for query: {query[:50]}...")
            return cached
    
    headers = {
        "Authorization": f"Bearer {yelp_api_key}",
        "Content-Type": "application/json",
    }
    
    data: dict[str, Any] = {
        "query": query,
    }
    if chat_id:
        data["chat_id"] = chat_id
    if user_context:
        data["user_context"] = user_context
    
    client = await get_http_client()
    
    try:
        start_time = time.time()
        response = await client.post(
            url="https://api.yelp.com/ai/chat/v2",
            json=data,
            headers=headers,
            timeout=timeout,
        )
        elapsed = time.time() - start_time
        logger.info(f"Yelp API request completed in {elapsed:.2f}s")
        
        response.raise_for_status()
        result = response.json()

        # Cache successful responses (including follow-up queries)
        # Follow-up queries are cached with their chat_id as part of the key
        if use_cache:
            await _cache.set(query, result, chat_id, user_context)

        return result
        
    except httpx.TimeoutException as e:
        elapsed = time.time() - start_time
        logger.error(f"Timeout after {elapsed:.1f}s (limit: {timeout}s) for query: {query[:100]}")
        # Return structured error for better user feedback
        return {
            "error": "timeout",
            "message": f"The query took longer than expected ({elapsed:.1f}s). This usually happens with complex searches. Please try simplifying your query or try again in a moment.",
            "query": query[:100],
            "elapsed_seconds": elapsed
        }
    except httpx.RequestError as e:
        logger.error(f"Network error for query '{query[:50]}...': {e}")
        return {
            "error": "network",
            "message": "Unable to connect to Yelp's servers. Please check your internet connection and try again.",
            "details": str(e)
        }
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        logger.error(f"HTTP {status_code} error for query '{query[:50]}...': {e}")
        if status_code == 429:
            return {
                "error": "rate_limit",
                "message": "Yelp API rate limit exceeded. Please wait a moment and try again.",
                "status_code": status_code
            }
        elif status_code >= 500:
            return {
                "error": "server",
                "message": "Yelp's servers are experiencing issues. Please try again in a moment.",
                "status_code": status_code
            }
        else:
            return {
                "error": "http",
                "message": f"Yelp API returned an error (HTTP {status_code}). Please check your query and try again.",
                "status_code": status_code
            }
    except Exception as e:
        logger.error(f"Unexpected error for query '{query[:50]}...': {type(e).__name__}: {e}")
        return {
            "error": "unexpected",
            "message": "An unexpected error occurred while processing your request. Please try again.",
            "details": f"{type(e).__name__}: {str(e)}"
        }


async def make_parallel_requests(
    queries: list[tuple[str, Optional[str], Optional[UserContext]]],
    timeout: float = 25.0,
) -> list[Optional[Any]]:
    """
    Make multiple Fusion AI requests in parallel.
    
    Args:
        queries: List of (query, chat_id, user_context) tuples
        timeout: Per-request timeout
    
    Returns:
        List of responses (None for failed requests)
    """
    tasks = [
        make_fusion_ai_request(query, chat_id, user_context, timeout=timeout)
        for query, chat_id, user_context in queries
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to None
    return [
        result if not isinstance(result, Exception) else None
        for result in results
    ]


async def clear_cache() -> None:
    """Clear response cache."""
    await _cache.clear()
    logger.info("Cleared Yelp API response cache")



