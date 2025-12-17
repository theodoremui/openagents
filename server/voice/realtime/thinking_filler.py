"""
Thinking Filler System for Realtime Voice Agent

Provides friendly, contextual "filler" responses while the agent processes queries.
Improves user experience by acknowledging the query and setting expectations.

Design Principles:
- Natural language fillers that sound conversational
- Context-aware selection based on query characteristics
- Variety to avoid repetition
- Appropriate duration expectations
"""

import random
import re
from typing import Optional, Literal
from loguru import logger


QueryType = Literal[
    "search",      # Web search, research, "find", "look up"
    "calculation", # Math, data analysis
    "location",    # Directions, maps, places
    "knowledge",   # Factual questions, "what is", "who is"
    "creative",    # Writing, brainstorming
    "general",     # Default catch-all
]


class ThinkingFillerService:
    """
    Service for generating appropriate thinking fillers based on query context.

    Architecture:
    - Analyzes query to determine type and expected duration
    - Selects appropriate filler from curated list
    - Provides variety through randomization
    - Logs filler selection for monitoring
    """

    # Filler phrases organized by context
    FILLERS = {
        "search": [
            "Let me search for that.",
            "I'll look that up for you.",
            "Searching now.",
            "Let me find that information.",
            "Looking into that.",
            "I'll search for the latest information.",
            "Checking that now.",
        ],
        "calculation": [
            "Let me calculate that.",
            "I'll work that out.",
            "Calculating now.",
            "Let me figure that out.",
            "I'll do the math.",
            "Working on that calculation.",
        ],
        "location": [
            "Let me check the location for you.",
            "I'll look that place up right now.",
            "I'm finding those directions.",
            "Let me map that out for you.",
            "I'm checking that route now.",
            "Looking up that address for you.",
            "Let me get you those directions.",
            "I'm searching for that location.",
        ],
        "knowledge": [
            "Let me think about that.",
            "I'll get you that information.",
            "Let me recall that.",
            "Thinking.",
            "Let me check my knowledge base.",
            "I'll find that out.",
        ],
        "creative": [
            "Let me think creatively about that.",
            "I'll work on that.",
            "Brainstorming now.",
            "Let me put something together.",
            "Working on it.",
        ],
        "general": [
            "Just a moment while I process that.",
            "Hold on a second, I'm checking.",
            "Let me check that for you right now.",
            "Give me just a moment to find that.",
            "I'll help with that, one second.",
            "Let me see what I can find.",
            "I'm working on that now.",
            "One moment please while I search.",
            "Let me think about that question.",
            "I'm on it, checking now.",
            "I'm looking into that for you.",
            "Let me gather that information.",
        ],
    }

    # Query patterns for classification (order matters - more specific first)
    PATTERNS = {
        "creative": [
            r"\b(write|create|generate|compose|draft)\b",
            r"\b(brainstorm|ideas|creative|imagine)\b",
            r"\b(story|poem|essay|email|letter)\b",
        ],
        "calculation": [
            r"\d+\s*[+\-*/×÷]\s*\d+",  # Math expressions first
            r"\bwhat is \d+",  # "what is 100 divided by 5"
            r"\b(calculate|compute|multiply|divide|add|subtract)\b",
            r"\b(average|mean|total|sum|percent)\b",
        ],
        "location": [
            r"\b(direction|route|map|navigate|address)\b",
            r"\b(where is.*(?:restaurant|hotel|store|near|location|place))\b",  # "where is" for places
            r"\b(how do i get|take me to|give me directions)\b",
            r"\b(restaurant|hotel|store|near me|nearby|nearest)\b",
        ],
        "knowledge": [
            r"\bwhat is (?!.*\d)",  # "what is" without numbers (knowledge, not math)
            r"\b(who is|when did|where did|why|how does)\b",
            r"\b(explain|describe|tell me about|define)\b",
            r"\b(what to|what should|which|recommend|suggest|advice)\b",  # Recommendation queries
        ],
        "search": [
            r"\b(search|find|look up|show me)\b",
            r"\b(latest|news|current|recent) (?:news|information|articles)",
            r"\bhow (?:do i |can i )?(?:find|get|search)",
        ],
    }

    @classmethod
    def classify_query(cls, query: str) -> QueryType:
        """
        Classify query into one of the predefined types.

        Args:
            query: User's query text

        Returns:
            Query type classification
        """
        query_lower = query.lower()

        # Check each pattern type
        for query_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    logger.debug(f"Query classified as '{query_type}' based on pattern: {pattern}")
                    return query_type  # type: ignore

        # Default to general
        logger.debug("Query classified as 'general' (no specific pattern matched)")
        return "general"

    @classmethod
    def get_filler(cls, query: str, previous_filler: Optional[str] = None) -> str:
        """
        Get appropriate thinking filler for the query.

        Args:
            query: User's query text
            previous_filler: Previously used filler (to avoid repetition)

        Returns:
            Thinking filler text
        """
        # Classify query
        query_type = cls.classify_query(query)

        # Get available fillers for this type
        fillers = cls.FILLERS[query_type].copy()

        # Remove previous filler to avoid repetition
        if previous_filler and previous_filler in fillers and len(fillers) > 1:
            fillers.remove(previous_filler)

        # Select random filler
        filler = random.choice(fillers)

        logger.info(f"Selected filler for query type '{query_type}': '{filler}'")

        return filler

    @classmethod
    def estimate_duration(cls, query: str) -> Literal["short", "medium", "long"]:
        """
        Estimate how long the query might take to process.

        Args:
            query: User's query text

        Returns:
            Duration estimate: "short" (<2s), "medium" (2-5s), "long" (>5s)
        """
        query_lower = query.lower()
        word_count = len(query.split())

        # Long duration indicators
        long_indicators = [
            "research", "comprehensive", "detailed", "analyze", "compare",
            "multiple", "several", "list all", "find all"
        ]
        if any(indicator in query_lower for indicator in long_indicators):
            return "long"

        # Short duration indicators
        short_indicators = [
            "what time", "current", "quick", "simple", "just", "only"
        ]
        if any(indicator in query_lower for indicator in short_indicators):
            return "short"

        # Heuristic: longer queries might take longer to process
        if word_count > 20:
            return "long"
        elif word_count > 10:
            return "medium"
        else:
            return "short"

    @classmethod
    def should_use_filler(cls, query: str) -> bool:
        """
        Determine if a thinking filler should be used for this query.

        Skip fillers for:
        - Empty queries
        - Short greetings/acknowledgments
        - Chitchat queries (conversational, no research/tools needed)

        Args:
            query: User's query text

        Returns:
            True if filler should be used
        """
        # Don't use filler for empty queries
        query_stripped = query.strip()
        if not query_stripped:
            logger.debug("Skipping filler for empty query")
            return False

        query_lower = query_stripped.lower()
        word_count = len(query_stripped.split())

        # Check for short greetings/acknowledgments (1-2 words)
        if word_count <= 4:
            # Common quick-turn phrases where a filler adds latency/noise.
            # Keep this purely lexical/regex-based for minimal overhead.
            quick_phrases = [
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
                "k",
                "kk",
                "yep",
                "yeah",
                "nope",
                "nah",
                "sure",
                "sounds good",
                "all good",
                "got it",
            ]

            # Normalize punctuation for exact-match checks
            normalized = re.sub(r"[^\w\s']", "", query_lower).strip()
            if normalized in quick_phrases:
                logger.debug("Skipping filler for quick greeting/acknowledgment")
                return False

            # Match short greetings like:
            # "hello there", "hey there!", "hi!", "good morning", "good evening"
            greeting_patterns = [
                r"^(hi|hello|hey|hiya|howdy|greetings)(\s+there)?$",
                r"^(good\s+(morning|afternoon|evening|night))$",
            ]
            for pattern in greeting_patterns:
                if re.search(pattern, normalized):
                    logger.debug("Skipping filler for greeting pattern")
                    return False

        # Check for chitchat patterns (conversational, no work needed)
        # Use ^ and $ or specific endings to avoid false matches
        chitchat_patterns = [
            r"^(how are you|how's it going|how do you do|nice to meet you)(\?|\.)?$",
            r"^(what's up|wassup|sup)(\?|\.)?$",
            r"^(good morning|good afternoon|good evening|good night)(\?|\.)?$",
            r"^(see you later|see you|bye|goodbye|talk to you later|catch you later)(\?|\.)?$",
            r"^(nice talking|great chatting|enjoyed talking)(\?|\.)?$",
            r"^(you'?re welcome|no problem|anytime|my pleasure)(\?|\.)?$",
            r"^(yes|no|sure|absolutely|definitely|nope|nah)(\?|\.)?$",  # Single word confirmations
            r"^(cool|great|awesome|nice|perfect|excellent|wonderful)(\?|\.)?$",  # Single word reactions
        ]

        for pattern in chitchat_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Skipping filler for chitchat query: '{query[:50]}'")
                return False

        # Use filler for all other queries (research, search, calculation, etc.)
        return True


class FillerHistory:
    """
    Tracks recently used fillers to ensure variety.

    Simple implementation with fixed-size history.
    """

    def __init__(self, max_history: int = 5):
        self.history: list[str] = []
        self.max_history = max_history

    def add(self, filler: str) -> None:
        """Add filler to history."""
        self.history.append(filler)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_last(self) -> Optional[str]:
        """Get most recently used filler."""
        return self.history[-1] if self.history else None

    def avoid(self) -> list[str]:
        """Get list of fillers to avoid."""
        return self.history.copy()


# Singleton instance for session-level history
_filler_history = FillerHistory()


def get_thinking_filler(query: str) -> Optional[str]:
    """
    Convenience function to get a thinking filler for a query.

    Args:
        query: User's query text

    Returns:
        Thinking filler text, or None if filler not needed
    """
    if not ThinkingFillerService.should_use_filler(query):
        return None

    # Get previous filler to avoid repetition
    previous = _filler_history.get_last()

    # Get new filler
    filler = ThinkingFillerService.get_filler(query, previous)

    # Add to history
    _filler_history.add(filler)

    return filler


# Export main API
__all__ = [
    "ThinkingFillerService",
    "FillerHistory",
    "get_thinking_filler",
    "QueryType",
]
