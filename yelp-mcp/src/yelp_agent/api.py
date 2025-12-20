"""
Optimized Yelp Fusion AI API client with caching, connection pooling, and performance improvements.

Key optimizations:
1. HTTP connection pooling (reuse httpx.AsyncClient)
2. Response caching with TTL (5 minutes)
3. Reduced timeouts (25s instead of 30s)
4. Better error handling
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
from collections import OrderedDict
import asyncio

import httpx

from .loggers import logger


class UserContext(TypedDict):
    latitude: float
    longitude: float


class ResponseCache:
    """
    In-memory LRU cache for Yelp API responses.
    
    Features:
    - TTL-based expiration (5 minutes)
    - LRU eviction
    - Query-based deduplication
    """
    
    def __init__(self, max_size: int = 200, ttl_seconds: int = 300):
        """Initialize cache with max_size entries and ttl_seconds TTL."""
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


# Global cache instance (200 entries, 5 minute TTL)
_cache = ResponseCache(max_size=200, ttl_seconds=300)

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
                    read=25.0,        # 25s read timeout (reduced from 30s)
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


async def make_fusion_ai_request(
    query: str,
    chat_id: Optional[str] = None,
    user_context: Optional[UserContext] = None,
    use_cache: bool = True,
    timeout: float = 25.0,  # Reduced from 30s for faster failure detection
):
    """
    Make optimized Fusion AI request with caching and connection pooling.
    
    Args:
        query: Natural language query
        chat_id: Optional chat ID for conversation context
        user_context: Optional user location context
        use_cache: Whether to use response cache (default: True)
        timeout: Request timeout in seconds (default: 25s, reduced from 30s)
    
    Returns:
        JSON response or None on error
    """
    yelp_api_key = os.getenv("YELP_API_KEY")

    if not yelp_api_key:
        logger.error(
            "CRITICAL: YELP_API_KEY environment variable is missing. "
            "The MCP server cannot access Yelp Fusion AI without this API key. "
            "Please ensure YELP_API_KEY is set in your .env file at the project root. "
            "Check that the parent process (OpenAgents server) has loaded the .env file."
        )
        return None

    # Check cache first (skip for follow-up queries with chat_id)
    if use_cache and not chat_id:
        cached = await _cache.get(query, chat_id, user_context)
        if cached is not None:
            logger.info(f"Cache hit for query: {query[:50]}...")
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
        
        # Cache successful responses (skip for follow-up queries)
        if use_cache and not chat_id:
            await _cache.set(query, result, chat_id, user_context)
        
        return result
        
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error while making Fusion AI request (timeout={timeout}s): {e}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error while making Fusion AI request: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP status error while making Fusion AI request: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while making Fusion AI request: {e}")
        return None
