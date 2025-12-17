"""
Embedding Providers - Abstraction for generating text embeddings.

This module provides a pluggable architecture for generating embeddings,
enabling multiple strategies (OpenAI API, local models, cached) to be
composed using dependency injection and decorator patterns.

Design Principles:
- Interface Segregation: IEmbeddingProvider defines minimal contract
- Dependency Inversion: Consumers depend on interface, not implementations
- Open/Closed: Easy to add new providers without modifying existing code
- Decorator Pattern: CachedEmbeddingProvider wraps any provider with caching
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from functools import lru_cache
import hashlib
import numpy as np
from loguru import logger


class IEmbeddingProvider(ABC):
    """
    Interface for embedding generation.

    All embedding providers must implement this interface, enabling
    seamless composition and substitution (Liskov Substitution Principle).
    """

    @abstractmethod
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as numpy array

        Raises:
            Exception: If embedding generation fails
        """
        pass

    @abstractmethod
    async def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently.

        Default implementation calls generate_embedding sequentially,
        but providers can override for batch optimization.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the dimensionality of embeddings produced by this provider."""
        pass


class OpenAIEmbeddingProvider(IEmbeddingProvider):
    """
    Embedding provider using OpenAI's text-embedding-3-small model.

    Characteristics:
    - High quality embeddings (1536 dimensions)
    - API call latency: 100-2000ms (network + processing)
    - Cost: ~$0.00002 per 1K tokens
    - Best for: Production quality, diverse queries

    Usage:
        >>> provider = OpenAIEmbeddingProvider(api_key="sk-...")
        >>> embedding = await provider.generate_embedding("pizza near me")
    """

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key
            model: Embedding model to use (default: text-embedding-3-small)
        """
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimension = 1536  # text-embedding-3-small dimension

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate single embedding via OpenAI API."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=text
        )

        if not getattr(response, "data", None):
            raise ValueError("OpenAI embeddings response missing data")

        embedding = np.array(response.data[0].embedding)
        return embedding

    async def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in single API call.

        OpenAI API supports batching up to 2048 texts per request,
        reducing latency significantly for initialization.
        """
        if not texts:
            return []

        # OpenAI batch limit is 2048 texts per request
        batch_size = 2048
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            response = await self._client.embeddings.create(
                model=self._model,
                input=batch
            )

            if not getattr(response, "data", None):
                raise ValueError("OpenAI embeddings response missing data")

            batch_embeddings = [np.array(item.embedding) for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    @property
    def embedding_dimension(self) -> int:
        return self._dimension


class CachedEmbeddingProvider(IEmbeddingProvider):
    """
    Decorator that adds LRU caching to any embedding provider.

    Wraps another embedding provider and caches results in memory
    using content-addressed hashing (SHA256 of input text).

    Performance:
    - Cache hit: <1ms (in-memory dict lookup)
    - Cache miss: Delegates to wrapped provider

    This implements the Decorator pattern, adding caching behavior
    without modifying the underlying provider.

    Usage:
        >>> base_provider = OpenAIEmbeddingProvider(api_key="...")
        >>> cached = CachedEmbeddingProvider(base_provider, max_size=10000)
        >>> embedding = await cached.generate_embedding("pizza")  # API call
        >>> embedding = await cached.generate_embedding("pizza")  # <1ms cache hit
    """

    def __init__(
        self,
        provider: IEmbeddingProvider,
        max_size: int = 10000,
        enable_logging: bool = True
    ):
        """
        Initialize cached embedding provider.

        Args:
            provider: Underlying embedding provider to wrap
            max_size: Maximum cache entries (LRU eviction)
            enable_logging: Log cache hits/misses for debugging
        """
        self._provider = provider
        self._cache: Dict[str, np.ndarray] = {}
        self._max_size = max_size
        self._enable_logging = enable_logging

        # Statistics for monitoring
        self._stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }

    def _get_cache_key(self, text: str) -> str:
        """
        Generate content-addressed cache key.

        Uses SHA256 hash to create deterministic key from text content,
        ensuring identical queries always get same key.
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding with LRU caching."""
        self._stats["total_requests"] += 1
        cache_key = self._get_cache_key(text)

        # Check cache
        if cache_key in self._cache:
            self._stats["hits"] += 1

            if self._enable_logging and self._stats["total_requests"] % 10 == 0:
                hit_rate = self._stats["hits"] / self._stats["total_requests"]
                logger.debug(
                    f"[EmbeddingCache] Hit rate: {hit_rate:.1%} "
                    f"({self._stats['hits']}/{self._stats['total_requests']})"
                )

            return self._cache[cache_key]

        # Cache miss - generate and cache
        self._stats["misses"] += 1

        if self._enable_logging:
            logger.debug(f"[EmbeddingCache] Cache miss for: {text[:50]}...")

        embedding = await self._provider.generate_embedding(text)

        # Add to cache with LRU eviction
        if len(self._cache) >= self._max_size:
            # Remove oldest entry (Python 3.7+ dicts maintain insertion order)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[cache_key] = embedding
        return embedding

    async def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate batch embeddings with per-item caching.

        Checks cache for each text individually, only calling provider
        for cache misses. This maximizes cache efficiency.
        """
        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for all texts
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)

            if cache_key in self._cache:
                results.append(self._cache[cache_key])
                self._stats["hits"] += 1
            else:
                # Will need to generate this one
                results.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)
                self._stats["misses"] += 1

        self._stats["total_requests"] += len(texts)

        # Generate embeddings for uncached texts
        if uncached_texts:
            if self._enable_logging:
                logger.info(
                    f"[EmbeddingCache] Batch: {len(uncached_texts)}/{len(texts)} "
                    f"cache misses"
                )

            new_embeddings = await self._provider.generate_batch_embeddings(uncached_texts)

            # Insert into results and cache
            for text, embedding, idx in zip(uncached_texts, new_embeddings, uncached_indices):
                cache_key = self._get_cache_key(text)

                # LRU eviction if needed
                if len(self._cache) >= self._max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]

                self._cache[cache_key] = embedding
                results[idx] = embedding

        return results

    @property
    def embedding_dimension(self) -> int:
        return self._provider.embedding_dimension

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dict with hits, misses, total requests, hit rate, cache size
        """
        hit_rate = (
            self._stats["hits"] / self._stats["total_requests"]
            if self._stats["total_requests"] > 0
            else 0.0
        )

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "total_requests": self._stats["total_requests"],
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "max_size": self._max_size
        }

    def clear_cache(self):
        """Clear all cached embeddings."""
        self._cache.clear()
        logger.info("[EmbeddingCache] Cache cleared")


# Future extension point: Local embedding model provider
# class LocalEmbeddingProvider(IEmbeddingProvider):
#     """
#     Provider using local sentence-transformers model.
#
#     Characteristics:
#     - Fast inference: 20-50ms on CPU, 5-10ms on GPU
#     - No API costs
#     - Smaller dimension (384-768)
#     - Best for: High-throughput, latency-sensitive deployments
#
#     Implementation note:
#     Requires sentence-transformers package:
#         pip install sentence-transformers
#
#     Model recommendations:
#     - all-MiniLM-L6-v2: 384 dim, 120MB, very fast
#     - all-mpnet-base-v2: 768 dim, 420MB, better quality
#     """
#     pass
