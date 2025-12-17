"""
Fast-Path Bypass for Simple Queries.

Detects queries that can be handled by a single agent (e.g., chitchat)
and routes them directly, bypassing the full MoE pipeline for minimal latency.

Architecture:
    Query → Fast-Path Check → Direct Agent (if match)
                           → Full MoE Pipeline (if no match)

Example latency:
    Before: "Hi there!" → 6000ms (selection + 3 agents + mixing)
    After:  "Hi there!" → 500ms (direct to chitchat)
"""

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import Optional, Dict
import os
from openai import AsyncOpenAI
from loguru import logger

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore


class FastPathDetector:
    """
    Semantic-based fast-path detection using embeddings.

    Pre-computes embeddings for common query patterns (chitchat, greetings)
    and checks if incoming queries are semantically similar.

    If similarity > threshold, bypass MoE and route directly to the target agent.
    """

    def __init__(self, similarity_threshold: float = 0.75):
        """
        Initialize fast-path detector.

        Args:
            similarity_threshold: Min similarity (0-1) to trigger fast-path
                                 0.75 = very similar (recommended)
                                 0.85 = extremely similar (strict)
                                 0.65 = somewhat similar (loose)
        """
        self.similarity_threshold = similarity_threshold

        # API key is only required for the embeddings-based path.
        # We keep a lexical-only fast-path that works even when OPENAI_API_KEY is absent.
        api_key = os.getenv("OPENAI_API_KEY")
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None
        self._pattern_embeddings: Optional[Dict[str, Dict]] = None

        if np is None:
            logger.warning("FastPathDetector numpy unavailable; using pure-Python cosine similarity (slower).")

    async def _initialize_patterns(self):
        """
        Pre-compute embeddings for fast-path patterns.

        Each pattern defines:
        - Examples: Representative queries for this pattern
        - Target agent: Agent to route to if matched
        - Description: What this pattern represents
        """
        if self._pattern_embeddings is not None:
            return  # Already initialized

        if self._client is None:
            # Embeddings-based fast-path is disabled without an API key.
            # Lexical fast-path can still operate.
            self._pattern_embeddings = {}
            logger.warning("FastPathDetector embeddings disabled (OPENAI_API_KEY not set). Using lexical fast-path only.")
            return

        # Define fast-path patterns
        patterns = {
            "chitchat": {
                "target_agent": "chitchat",
                "description": "Simple greetings, small talk, pleasantries",
                "examples": [
                    "hello",
                    "hi there",
                    "hey",
                    "good morning",
                    "how are you",
                    "what's up",
                    "howdy",
                    "greetings",
                    "hi",
                    "hey there",
                    "good afternoon",
                    "good evening",
                    "how's it going",
                    "nice to meet you",
                    "thanks",
                    "thank you",
                    "bye",
                    "goodbye",
                    "see you",
                    "take care",
                    "have a great day"
                ]
            },
            # Future: Add more patterns
            # "simple_fact": {
            #     "target_agent": "wiki",
            #     "examples": ["what is the capital of France", ...]
            # }
        }

        logger.info("Initializing fast-path pattern embeddings...")

        self._pattern_embeddings = {}

        for pattern_name, pattern_config in patterns.items():
            # Compute embeddings for all examples
            example_embeddings = []

            for example in pattern_config["examples"]:
                response = await self._client.embeddings.create(
                    model="text-embedding-3-small",
                    input=example
                )
                # Defensive: if the SDK returns an unexpected shape (data missing),
                # disable embeddings fast-path and fall back to lexical-only.
                if not getattr(response, "data", None):
                    logger.warning("[FastPath] Embeddings response missing data; disabling embeddings fast-path.")
                    self._pattern_embeddings = {}
                    self._client = None
                    return
                raw = response.data[0].embedding
                embedding = np.array(raw) if np is not None else list(raw)
                example_embeddings.append(embedding)

            # Compute centroid (average embedding)
            if np is not None:
                centroid = np.mean(example_embeddings, axis=0)
            else:
                n = len(example_embeddings)
                dim = len(example_embeddings[0])
                sums = [0.0] * dim
                for v in example_embeddings:
                    for i in range(dim):
                        sums[i] += float(v[i])
                centroid = [s / n for s in sums]

            self._pattern_embeddings[pattern_name] = {
                "centroid": centroid,
                "target_agent": pattern_config["target_agent"],
                "description": pattern_config["description"],
                "example_count": len(example_embeddings)
            }

            logger.info(
                f"Loaded pattern '{pattern_name}': {pattern_config['description']} "
                f"({len(example_embeddings)} examples) → {pattern_config['target_agent']}"
            )

        logger.info(f"Fast-path patterns initialized: {list(self._pattern_embeddings.keys())}")

    async def detect_fast_path(self, query: str) -> Optional[str]:
        """
        Check if query matches a fast-path pattern.

        Args:
            query: User query

        Returns:
            Agent ID to route to (e.g., "chitchat"), or None if no match
        """
        # Ultra-fast lexical bypass for greetings/chitchat.
        # This avoids an embeddings API call (network + latency) for the most common voice turns.
        q = (query or "").strip().lower()
        if q:
            normalized = "".join(ch for ch in q if ch.isalnum() or ch.isspace() or ch == "'").strip()
            # Keep patterns strict to avoid misrouting real questions.
            if self._is_lexical_chitchat(normalized):
                logger.info("[FastPath] ✅ LEXICAL MATCH → Routing directly to 'chitchat'")
                return "chitchat"

        # If embeddings are unavailable, stop here.
        if self._client is None:
            return None

        # Initialize patterns if needed
        await self._initialize_patterns()

        # Generate query embedding (defensive against unexpected SDK payloads)
        try:
            response = await self._client.embeddings.create(
                model="text-embedding-3-small",
                input=query
            )
            if not getattr(response, "data", None):
                logger.warning("[FastPath] Embeddings response missing data; skipping embeddings fast-path.")
                return None
            raw = response.data[0].embedding
            query_embedding = np.array(raw) if np is not None else list(raw)
        except Exception as e:
            logger.warning(f"[FastPath] Embeddings fast-path failed ({e}); skipping embeddings fast-path.")
            return None

        # Check similarity with each pattern
        best_match = None
        best_similarity = 0.0

        for pattern_name, pattern_data in self._pattern_embeddings.items():
            centroid = pattern_data["centroid"]
            similarity = self._cosine_similarity(query_embedding, centroid)

            logger.debug(
                f"[FastPath] Pattern '{pattern_name}' similarity: {similarity:.3f}"
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = pattern_data

        # Check if best match exceeds threshold
        if best_similarity >= self.similarity_threshold:
            target_agent = best_match["target_agent"]
            logger.info(
                f"[FastPath] ✅ MATCH - Query matches pattern (similarity={best_similarity:.3f}) "
                f"→ Routing directly to '{target_agent}'"
            )
            return target_agent
        else:
            logger.debug(
                f"[FastPath] ❌ NO MATCH - Best similarity {best_similarity:.3f} < threshold {self.similarity_threshold}"
            )
            return None

    @staticmethod
    def _is_lexical_chitchat(normalized_query: str) -> bool:
        """
        Fast, local-only chitchat detector.

        Intended for voice UX:
        - greetings
        - pleasantries
        - short acknowledgements
        """
        if not normalized_query:
            return False

        words = normalized_query.split()
        if len(words) > 5:
            return False

        # If the user is clearly asking for substantive info, do NOT fast-path to chitchat.
        # (Keep this conservative; we prefer occasional false negatives over misrouting.)
        not_chitchat_markers = {
            "news", "latest", "today", "weather",
            "stock", "stocks", "price", "prices",
            "restaurant", "restaurants", "map", "route", "directions", "drive", "flight",
            "code", "error", "bug", "trace",
        }
        if any(w in not_chitchat_markers for w in words):
            return False

        quick = {
            "hi",
            "hello",
            "hey",
            "hiya",
            "howdy",
            "greetings",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "yep",
            "yeah",
            "nope",
            "nah",
            "sure",
            "good morning",
            "good afternoon",
            "good evening",
            "good night",
            "whats going on",
            "what's going on",
            "what is going on",
            "hows everything",
            "how's everything",
            "how are things",
            # Short small-talk replies (common after "what's up?" / "what's going on?")
            "not much",
            "nothing much",
            "nothing really",
            "not a lot",
            "not alot",
            "nm",
        }
        if normalized_query in quick:
            return True

        # "hello there" / "hey there"
        if len(words) in (1, 2) and words[0] in {"hi", "hello", "hey", "hiya", "howdy"}:
            if len(words) == 1:
                return True
            if words[1] == "there":
                return True

        # A few very common small-talk openings
        if normalized_query in {"how are you", "how's it going", "whats up", "what's up"}:
            return True

        # Pattern: "what's going on" / "what is going on"
        if normalized_query.startswith("what's going on") or normalized_query.startswith("whats going on") or normalized_query.startswith("what is going on"):
            return True

        return False

    @staticmethod
    def _cosine_similarity(a, b) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0-1 range)
        """
        if np is not None:
            dot_product = float(np.dot(a, b))
            norm_a = float(np.linalg.norm(a))
            norm_b = float(np.linalg.norm(b))
        else:
            dot_product = 0.0
            norm_a = 0.0
            norm_b = 0.0
            for x, y in zip(a, b):
                fx = float(x)
                fy = float(y)
                dot_product += fx * fy
                norm_a += fx * fx
                norm_b += fy * fy
            norm_a = norm_a ** 0.5
            norm_b = norm_b ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)

        # Clamp to [0, 1] range (cosine is naturally [-1, 1])
        return max(0.0, min(1.0, similarity))
