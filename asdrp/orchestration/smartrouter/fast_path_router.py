"""
FastPathRouter - Pre-classification for Simple Queries

Provides immediate routing for high-confidence simple queries (chitchat,
greetings, weather, etc.) without requiring LLM interpretation. Uses keyword
pattern matching for deterministic, ultra-fast classification.

Design Principles:
------------------
- Single Responsibility: Only handles pre-classification
- Fail-Safe: Returns None if no match (fallback to LLM)
- Conservative: Only matches high-confidence patterns
- Observable: Logs all matches for monitoring

Responsibilities:
-----------------
- Pattern matching against predefined templates
- Immediate QueryIntent generation for matched queries
- Fallthrough to LLM for ambiguous queries

Performance Impact:
-------------------
- Matched queries: 95%+ latency reduction (no LLM call)
- Non-matched queries: <1ms overhead
- Expected match rate: 20-30% of queries
"""

from typing import Dict, Tuple, List, Optional
import re
import logging

from asdrp.orchestration.smartrouter.interfaces import QueryIntent, QueryComplexity

logger = logging.getLogger(__name__)


class FastPathRouter:
    """
    Pre-classifier using keyword patterns for simple queries.

    Provides immediate routing for high-confidence simple queries without
    requiring LLM interpretation. Uses conservative pattern matching to
    ensure zero false positives.

    Pattern Format:
    ---------------
    Each pattern is a tuple of (regex, domains, complexity):
    - regex: Regular expression to match query text
    - domains: List of domain keywords
    - complexity: Query complexity classification

    Usage:
    ------
    >>> router = FastPathRouter()
    >>> intent = router.try_fast_path("Hello!")
    >>> if intent:
    ...     print(f"Fast-path match: {intent.metadata['fast_path_pattern']}")
    ... else:
    ...     # Fall through to LLM interpretation
    ...     pass
    """

    # Pattern set for fast-path routing
    # Format: pattern_name -> (regex, domains, complexity)
    #
    # IMPORTANT: Only match high-confidence, simple patterns.
    # Complex queries (weather, news, etc.) should go through LLM interpretation
    # to properly handle multi-part questions and context.
    #
    # Design Principle: Conservative matching - zero false positives.
    # When in doubt, fall through to LLM.
    PATTERNS: Dict[str, Tuple[str, List[str], QueryComplexity]] = {
        # ===========================================
        # PURE CHITCHAT (only match if ENTIRE query is greeting)
        # ===========================================
        "greeting_simple": (
            r"^(hi|hello|hey|greetings|howdy)(\s|!|\.|\?)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),
        "greeting_time": (
            r"^(good morning|good afternoon|good evening|good day)(\s|!|\.)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),

        # Farewells
        "farewell": (
            r"^(bye|goodbye|see you|farewell|goodnight|cya|ttyl)(\s|!|\.)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),

        # Gratitude
        "gratitude": (
            r"^(thanks|thank you|thx|ty|appreciate it|much appreciated)(\s|!|\.)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),

        # Status inquiries (pure social, no info request)
        "status_inquiry": (
            r"^how (are|r) (you|u)(\s+doing)?(\s|\?|!)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),
        "status_whatsup": (
            r"^(what's up|whats up|wassup|sup)(\s|\?|!)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),

        # Affirmations
        "affirmation": (
            r"^(yes|yeah|yep|yup|sure|ok|okay|alright|sounds good)(\s|!|\.)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),

        # Negations
        "negation": (
            r"^(no|nope|nah|not really)(\s|!|\.)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),
    }

    # Order in which patterns should be checked
    # Only pure chitchat patterns - complex queries go to LLM
    PATTERN_CHECK_ORDER = [
        "greeting_simple",
        "greeting_time",
        "farewell",
        "gratitude",
        "status_inquiry",
        "status_whatsup",
        "affirmation",
        "negation",
    ]

    def __init__(self, enable_logging: bool = True):
        """
        Initialize FastPathRouter.

        Args:
            enable_logging: Enable match logging (default: True)
        """
        self.enable_logging = enable_logging
        self._match_counts: Dict[str, int] = {}
        self._total_attempts = 0
        self._total_matches = 0

        # Copy class PATTERNS to instance to avoid shared state between instances
        self.patterns = self.PATTERNS.copy()
        
        # Copy class PATTERN_CHECK_ORDER to instance for modification by add_pattern
        self._pattern_check_order = list(self.PATTERN_CHECK_ORDER)

        # Compile all patterns once for performance
        self._compiled_patterns: Dict[str, Tuple[re.Pattern, List[str], QueryComplexity]] = {}
        for pattern_name, (regex, domains, complexity) in self.patterns.items():
            self._compiled_patterns[pattern_name] = (
                re.compile(regex, re.IGNORECASE),
                domains,
                complexity
            )

        logger.info(f"FastPathRouter initialized with {len(self.patterns)} patterns")

    def try_fast_path(self, query: str) -> Optional[QueryIntent]:
        """
        Attempt to classify query using keyword patterns.

        Only matches high-confidence, simple chitchat patterns (greetings,
        farewells, gratitude, etc.). Complex queries (weather, news, etc.)
        are NOT matched and fall through to LLM interpretation.

        Args:
            query: User query text

        Returns:
            QueryIntent if matched, None if no match (fall through to LLM)

        Examples:
        ---------
        >>> router = FastPathRouter()
        >>> intent = router.try_fast_path("Hello!")
        >>> assert intent is not None
        >>> assert intent.complexity == QueryComplexity.SIMPLE
        >>> assert "conversation" in intent.domains

        >>> intent = router.try_fast_path("What's the weather in Paris?")
        >>> assert intent is None  # Complex queries fall through to LLM
        """
        self._total_attempts += 1

        # Normalize query for matching
        query_normalized = query.strip()

        # Check patterns in defined order
        for pattern_name in self._pattern_check_order:
            if pattern_name not in self._compiled_patterns:
                continue

            regex, domains, complexity = self._compiled_patterns[pattern_name]
            if regex.match(query_normalized):
                # Match found!
                self._total_matches += 1
                self._match_counts[pattern_name] = self._match_counts.get(pattern_name, 0) + 1

                if self.enable_logging:
                    logger.info(
                        f"Fast-path match: '{query}' -> pattern='{pattern_name}', "
                        f"domains={domains}, complexity={complexity.value}"
                    )

                # Create QueryIntent
                return QueryIntent(
                    original_query=query,
                    complexity=complexity,
                    domains=domains,
                    requires_synthesis=False,
                    metadata={
                        "fast_path": True,
                        "fast_path_pattern": pattern_name,
                        "fast_path_confidence": 1.0,  # Pattern match = 100% confidence
                    }
                )

        # No match found
        if self.enable_logging:
            logger.debug(f"Fast-path: No match for '{query}' (falling through to LLM)")

        return None

    def get_metrics(self) -> Dict[str, any]:
        """
        Get fast-path routing metrics.

        Returns:
            Dictionary with metrics:
            - total_attempts: Total queries attempted
            - total_matches: Total successful matches
            - match_rate: Percentage of successful matches
            - pattern_counts: Matches per pattern

        Examples:
        ---------
        >>> router = FastPathRouter()
        >>> router.try_fast_path("Hello!")
        >>> router.try_fast_path("Goodbye!")
        >>> router.try_fast_path("What's the weather?")
        >>> metrics = router.get_metrics()
        >>> assert metrics["total_attempts"] == 3
        >>> assert metrics["total_matches"] == 2  # Weather doesn't match
        """
        match_rate = (
            self._total_matches / self._total_attempts
            if self._total_attempts > 0
            else 0.0
        )

        return {
            "total_attempts": self._total_attempts,
            "total_matches": self._total_matches,
            "match_rate": match_rate,
            "pattern_counts": dict(self._match_counts),
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._total_attempts = 0
        self._total_matches = 0
        self._match_counts.clear()
        logger.info("Fast-path metrics reset")

    def add_pattern(
        self,
        pattern_name: str,
        regex: str,
        domains: List[str],
        complexity: QueryComplexity
    ) -> None:
        """
        Add a new pattern to the router (for extensibility).

        Args:
            pattern_name: Unique identifier for pattern
            regex: Regular expression to match
            domains: List of domain keywords
            complexity: Query complexity classification

        Examples:
        ---------
        >>> router = FastPathRouter()
        >>> router.add_pattern(
        ...     "custom_greeting",
        ...     r"^yo(\\s|!)*$",
        ...     ["conversation", "social"],
        ...     QueryComplexity.SIMPLE
        ... )
        """
        if pattern_name in self.patterns:
            logger.warning(f"Pattern '{pattern_name}' already exists, overwriting")
        else:
            # Add new pattern to check order (at the end)
            self._pattern_check_order.append(pattern_name)

        self.patterns[pattern_name] = (regex, domains, complexity)
        self._compiled_patterns[pattern_name] = (
            re.compile(regex, re.IGNORECASE),
            domains,
            complexity
        )

        logger.info(f"Added fast-path pattern: {pattern_name}")

    def remove_pattern(self, pattern_name: str) -> bool:
        """
        Remove a pattern from the router.

        Args:
            pattern_name: Pattern identifier to remove

        Returns:
            True if removed, False if not found
        """
        if pattern_name in self.patterns:
            del self.patterns[pattern_name]
            del self._compiled_patterns[pattern_name]
            if pattern_name in self._pattern_check_order:
                self._pattern_check_order.remove(pattern_name)
            logger.info(f"Removed fast-path pattern: {pattern_name}")
            return True

        logger.warning(f"Pattern '{pattern_name}' not found")
        return False

    def list_patterns(self) -> List[str]:
        """
        List all available pattern names.

        Returns:
            List of pattern names
        """
        return list(self.patterns.keys())
