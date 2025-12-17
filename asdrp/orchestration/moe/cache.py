"""
Semantic Cache for MoE Orchestrator.

Provides caching of query-result pairs using embedding similarity.
"""

from typing import Optional, Any, Dict
import hashlib
import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict
import asyncio
from loguru import logger

from asdrp.orchestration.moe.interfaces import ICache
from asdrp.orchestration.moe.config_loader import MoEConfig
from asdrp.orchestration.moe.exceptions import CacheException


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    query: str
    response: str
    experts_used: list
    timestamp: float
    ttl: int


class SemanticCache(ICache):
    """
    Semantic cache using embedding similarity.

    For now, implements exact string matching for simplicity.
    Future: Add embedding-based similarity search.
    """

    def __init__(self, config: MoEConfig):
        """
        Initialize cache with configuration.

        Args:
            config: MoE configuration
        """
        self._config = config
        self._enabled = config.cache.enabled

        if not self._enabled:
            return

        # Get storage config
        storage = config.cache.storage
        db_path = storage.get("path", ":memory:")

        # Create parent directory if needed
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite database
        self._db_path = db_path
        self._init_database()

        # Get policy config
        policy = config.cache.policy
        self._similarity_threshold = policy.get("similarity_threshold", 0.9)
        self._ttl = policy.get("ttl", 3600)  # 1 hour default
        self._max_entries = policy.get("max_entries", 10000)

    def _init_database(self):
        """Initialize SQLite database schema."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    experts_used TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    ttl INTEGER NOT NULL
                )
            """)

            # Index for timestamp-based expiration
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON cache_entries(timestamp)
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            raise CacheException(f"Failed to initialize cache database: {e}")

    def _get_query_hash(self, query: str) -> str:
        """
        Get hash of query for exact matching.

        Args:
            query: Query string

        Returns:
            SHA256 hash of normalized query
        """
        # Normalize query (lowercase, strip whitespace)
        #
        # NOTE: We include a cache schema/version prefix to avoid serving stale responses
        # when we change orchestration behavior (e.g., map auto-injection, trace fields).
        # This is a simple, robust way to invalidate older cache entries without requiring
        # manual DB deletion.
        CACHE_VERSION = "v2"
        normalized = f"{CACHE_VERSION}:{query.lower().strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def get(self, query: str) -> Optional[Any]:
        """
        Get cached result for query.

        Args:
            query: Query string

        Returns:
            Cached result if found and not expired, None otherwise
        """
        if not self._enabled:
            return None

        try:
            # Run database operation in thread pool to avoid blocking
            return await asyncio.to_thread(self._get_sync, query)
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Cache get error: {e}")
            return None

    def _get_sync(self, query: str) -> Optional[Dict[str, Any]]:
        """Synchronous cache get."""
        import time

        query_hash = self._get_query_hash(query)

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT response, experts_used, timestamp, ttl
            FROM cache_entries
            WHERE query_hash = ?
        """, (query_hash,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        response, experts_used_json, timestamp, ttl = row

        # Check if expired
        if time.time() - timestamp > ttl:
            # Remove expired entry
            self._remove_sync(query_hash)
            return None

        # Parse experts_used
        experts_used = json.loads(experts_used_json)

        return {
            "response": response,
            "experts_used": experts_used,
            "cached": True
        }

    async def store(self, query: str, result: Any) -> None:
        """
        Store query-result pair in cache.

        Args:
            query: Query string
            result: Result to cache (must have response attribute)
        """
        if not self._enabled:
            return

        try:
            # Run database operation in thread pool
            await asyncio.to_thread(self._store_sync, query, result)
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Cache store error: {e}")

    def _store_sync(self, query: str, result: Any) -> None:
        """Synchronous cache store."""
        import time

        query_hash = self._get_query_hash(query)

        # Extract response and experts_used
        if hasattr(result, 'response'):
            response = result.response
            experts_used = getattr(result, 'experts_used', [])
        else:
            response = str(result)
            experts_used = []

        timestamp = time.time()

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Insert or replace
        cursor.execute("""
            INSERT OR REPLACE INTO cache_entries
            (query_hash, query, response, experts_used, timestamp, ttl)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            query_hash,
            query,
            response,
            json.dumps(experts_used),
            timestamp,
            self._ttl
        ))

        conn.commit()

        # Enforce max_entries limit
        cursor.execute("""
            SELECT COUNT(*) FROM cache_entries
        """)
        row = cursor.fetchone()
        count = row[0] if row else 0

        if count > self._max_entries:
            # Remove oldest entries
            entries_to_remove = count - self._max_entries
            cursor.execute("""
                DELETE FROM cache_entries
                WHERE query_hash IN (
                    SELECT query_hash FROM cache_entries
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
            """, (entries_to_remove,))
            conn.commit()

        conn.close()

    def _remove_sync(self, query_hash: str) -> None:
        """Remove entry by hash."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM cache_entries WHERE query_hash = ?
        """, (query_hash,))
        conn.commit()
        conn.close()

    async def clear(self) -> None:
        """Clear all cache entries."""
        if not self._enabled:
            return

        try:
            await asyncio.to_thread(self._clear_sync)
        except Exception as e:
            raise CacheException(f"Failed to clear cache: {e}")

    def _clear_sync(self) -> None:
        """Synchronous cache clear."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_entries")
        conn.commit()
        conn.close()
