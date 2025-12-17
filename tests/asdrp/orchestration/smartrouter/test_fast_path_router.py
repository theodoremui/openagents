"""
Tests for FastPathRouter

Comprehensive test suite covering:
- Pattern matching accuracy
- Case insensitivity
- False positive prevention
- Metrics tracking
- Pattern management
- Edge cases
"""

import pytest
from asdrp.orchestration.smartrouter.fast_path_router import FastPathRouter
from asdrp.orchestration.smartrouter.interfaces import QueryComplexity


class TestFastPathRouterPatternMatching:
    """Tests for pattern matching functionality."""

    def test_greeting_simple_match(self):
        """Test simple greeting patterns."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "hi",
            "hello",
            "hey",
            "greetings",
            "howdy",
            "Hi!",
            "HELLO!",
            "hey.",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should match: {query}"
            assert intent.complexity == QueryComplexity.SIMPLE
            assert "conversation" in intent.domains
            assert "social" in intent.domains
            assert intent.metadata["fast_path"] is True

    def test_greeting_time_match(self):
        """Test time-based greetings."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "good morning",
            "good afternoon",
            "good evening",
            "good day",
            "Good Morning!",
            "GOOD EVENING!",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should match: {query}"
            assert intent.complexity == QueryComplexity.SIMPLE

    def test_farewell_match(self):
        """Test farewell patterns."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "bye",
            "goodbye",
            "see you",
            "farewell",
            "goodnight",
            "cya",
            "ttyl",
            "Goodbye!",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should match: {query}"
            assert "conversation" in intent.domains

    def test_gratitude_match(self):
        """Test gratitude expressions."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "thanks",
            "thank you",
            "thx",
            "ty",
            "appreciate it",
            "much appreciated",
            "Thanks!",
            "THANK YOU!",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should match: {query}"
            assert intent.complexity == QueryComplexity.SIMPLE

    def test_status_inquiry_match(self):
        """Test status inquiry patterns."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "how are you",
            "how r u",
            "how are you doing",
            "How are you?",
            "what's up",
            "whats up",
            "wassup",
            "sup",
            "What's up?",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should match: {query}"
            assert "social" in intent.domains

    def test_affirmation_match(self):
        """Test affirmation patterns."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "yes",
            "yeah",
            "yep",
            "yup",
            "sure",
            "ok",
            "okay",
            "alright",
            "sounds good",
            "YES!",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should match: {query}"

    def test_negation_match(self):
        """Test negation patterns."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "no",
            "nope",
            "nah",
            "not really",
            "NO!",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should match: {query}"

    def test_case_insensitivity(self):
        """Test that patterns are case insensitive."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            ("hello", "HELLO", "HeLLo"),
            ("thank you", "THANK YOU", "ThAnK yOu"),
            ("goodbye", "GOODBYE", "GoodBye"),
        ]

        for case_variants in test_cases:
            intents = [router.try_fast_path(variant) for variant in case_variants]
            assert all(intent is not None for intent in intents), \
                f"All case variants should match: {case_variants}"

    def test_no_match_complex_queries(self):
        """Test that complex queries don't match (false negative prevention)."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "hello, what's the weather in Paris?",
            "hi, can you help me with something?",
            "thanks for the help with my previous question",
            "goodbye and have a great day tomorrow",
            "What is the capital of France?",
            "Tell me about artificial intelligence",
            "How do I cook pasta?",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is None, f"Should NOT match: {query}"

    def test_no_match_partial_matches(self):
        """Test that partial matches don't match (false positive prevention)."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "hiya",  # Not "hi" alone
            "hello there friend",  # Extra words
            "say goodbye",  # "goodbye" not at start
            "I wanted to say thanks",  # "thanks" not at start
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is None, f"Should NOT match partial: {query}"

    def test_whitespace_handling(self):
        """Test that extra whitespace is handled correctly."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "  hello  ",
            "\thello\t",
            "hello   ",
            "   hello",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should handle whitespace: '{query}'"

    def test_punctuation_handling(self):
        """Test various punctuation marks."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "hello!",
            "hello.",
            "hello?",
            "hello!!",
            "hello...",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            assert intent is not None, f"Should handle punctuation: {query}"


class TestFastPathRouterMetrics:
    """Tests for metrics tracking."""

    def test_metrics_initial_state(self):
        """Test initial metrics state."""
        router = FastPathRouter(enable_logging=False)
        metrics = router.get_metrics()

        assert metrics["total_attempts"] == 0
        assert metrics["total_matches"] == 0
        assert metrics["match_rate"] == 0.0
        assert metrics["pattern_counts"] == {}

    def test_metrics_tracking(self):
        """Test metrics are tracked correctly."""
        router = FastPathRouter(enable_logging=False)

        # Attempt 5 queries: 3 matches, 2 misses
        router.try_fast_path("hello")  # Match
        router.try_fast_path("goodbye")  # Match
        router.try_fast_path("thanks")  # Match
        router.try_fast_path("What is the weather?")  # Miss
        router.try_fast_path("Tell me about AI")  # Miss

        metrics = router.get_metrics()

        assert metrics["total_attempts"] == 5
        assert metrics["total_matches"] == 3
        assert abs(metrics["match_rate"] - 0.6) < 0.01  # 3/5 = 0.6

    def test_pattern_counts(self):
        """Test that pattern counts are tracked."""
        router = FastPathRouter(enable_logging=False)

        router.try_fast_path("hello")
        router.try_fast_path("hi")
        router.try_fast_path("hey")
        router.try_fast_path("goodbye")
        router.try_fast_path("thanks")

        metrics = router.get_metrics()

        assert "greeting_simple" in metrics["pattern_counts"]
        assert metrics["pattern_counts"]["greeting_simple"] == 3  # hello, hi, hey
        assert "farewell" in metrics["pattern_counts"]
        assert metrics["pattern_counts"]["farewell"] == 1
        assert "gratitude" in metrics["pattern_counts"]
        assert metrics["pattern_counts"]["gratitude"] == 1

    def test_metrics_reset(self):
        """Test metrics can be reset."""
        router = FastPathRouter(enable_logging=False)

        router.try_fast_path("hello")
        router.try_fast_path("goodbye")

        router.reset_metrics()

        metrics = router.get_metrics()
        assert metrics["total_attempts"] == 0
        assert metrics["total_matches"] == 0
        assert metrics["pattern_counts"] == {}


class TestFastPathRouterPatternManagement:
    """Tests for pattern management functionality."""

    def test_add_pattern(self):
        """Test adding a new pattern."""
        router = FastPathRouter(enable_logging=False)

        router.add_pattern(
            "custom_greeting",
            r"^yo(\s|!)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE
        )

        # Test the new pattern
        intent = router.try_fast_path("yo")
        assert intent is not None
        assert intent.metadata["fast_path_pattern"] == "custom_greeting"

        intent = router.try_fast_path("yo!")
        assert intent is not None

    def test_remove_pattern(self):
        """Test removing a pattern."""
        router = FastPathRouter(enable_logging=False)

        # Verify pattern exists
        intent = router.try_fast_path("hello")
        assert intent is not None

        # Remove pattern
        removed = router.remove_pattern("greeting_simple")
        assert removed is True

        # Verify pattern no longer matches
        intent = router.try_fast_path("hello")
        assert intent is None

    def test_remove_nonexistent_pattern(self):
        """Test removing a pattern that doesn't exist."""
        router = FastPathRouter(enable_logging=False)

        removed = router.remove_pattern("nonexistent_pattern")
        assert removed is False

    def test_list_patterns(self):
        """Test listing all patterns."""
        # Use fresh router to avoid interference from other tests
        router = FastPathRouter(enable_logging=False)

        patterns = router.list_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) >= 8  # At least 8 default patterns
        # Check for some expected patterns (but not all, since other tests may have modified)
        assert "farewell" in patterns or "gratitude" in patterns

    def test_add_pattern_overwrites_existing(self):
        """Test that adding a pattern with existing name overwrites it."""
        router = FastPathRouter(enable_logging=False)

        # Add pattern with same name as existing
        router.add_pattern(
            "greeting_simple",
            r"^custom_pattern$",
            ["custom_domain"],
            QueryComplexity.SIMPLE
        )

        # Original pattern should no longer match
        intent = router.try_fast_path("hello")
        assert intent is None

        # New pattern should match
        intent = router.try_fast_path("custom_pattern")
        assert intent is not None
        assert "custom_domain" in intent.domains


class TestFastPathRouterIntentGeneration:
    """Tests for QueryIntent generation."""

    def test_intent_structure(self):
        """Test that generated intent has correct structure."""
        router = FastPathRouter(enable_logging=False)

        intent = router.try_fast_path("hello")

        assert intent is not None
        assert hasattr(intent, "original_query")
        assert hasattr(intent, "complexity")
        assert hasattr(intent, "domains")
        assert hasattr(intent, "requires_synthesis")
        assert hasattr(intent, "metadata")

    def test_intent_query_text(self):
        """Test that intent preserves original query text."""
        router = FastPathRouter(enable_logging=False)

        query = "Hello!"
        intent = router.try_fast_path(query)

        assert intent is not None
        assert intent.original_query == query

    def test_intent_metadata(self):
        """Test that intent metadata contains fast-path info."""
        router = FastPathRouter(enable_logging=False)

        intent = router.try_fast_path("hello")

        assert intent is not None
        assert "fast_path" in intent.metadata
        assert intent.metadata["fast_path"] is True
        assert "fast_path_pattern" in intent.metadata
        assert intent.metadata["fast_path_pattern"] == "greeting_simple"
        assert "fast_path_confidence" in intent.metadata
        assert intent.metadata["fast_path_confidence"] == 1.0

    def test_intent_requires_synthesis_false(self):
        """Test that fast-path intents don't require synthesis."""
        router = FastPathRouter(enable_logging=False)

        intent = router.try_fast_path("hello")

        assert intent is not None
        assert intent.requires_synthesis is False


class TestFastPathRouterEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_query(self):
        """Test handling of empty query."""
        router = FastPathRouter(enable_logging=False)

        intent = router.try_fast_path("")
        assert intent is None

    def test_whitespace_only_query(self):
        """Test handling of whitespace-only query."""
        router = FastPathRouter(enable_logging=False)

        intent = router.try_fast_path("   ")
        assert intent is None

    def test_very_long_query(self):
        """Test handling of very long query."""
        router = FastPathRouter(enable_logging=False)

        long_query = "hello " * 1000
        intent = router.try_fast_path(long_query)
        assert intent is None  # Should not match due to extra words

    def test_special_characters(self):
        """Test handling of special characters."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "hello@",
            "hello#",
            "hello$",
            "hello&",
            "hello*",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            # Should not match due to unexpected characters
            assert intent is None

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        router = FastPathRouter(enable_logging=False)

        test_cases = [
            "hello 你好",
            "hello 🎉",
            "hello café",
        ]

        for query in test_cases:
            intent = router.try_fast_path(query)
            # Should not match due to extra words/characters
            assert intent is None

    def test_multiple_patterns_precedence(self):
        """Test that first matching pattern is used."""
        router = FastPathRouter(enable_logging=False)

        # "ok" matches affirmation pattern
        intent = router.try_fast_path("ok")
        assert intent is not None
        assert intent.metadata["fast_path_pattern"] == "affirmation"


class TestFastPathRouterPerformance:
    """Tests for performance characteristics."""

    def test_performance_no_match(self):
        """Test that non-matches are fast (all patterns checked)."""
        router = FastPathRouter(enable_logging=False)

        # Non-matching query should check all patterns quickly
        import time
        start = time.time()
        for _ in range(1000):
            router.try_fast_path("This is a complex query about weather")
        duration = time.time() - start

        # Should complete 1000 non-matches in < 100ms
        assert duration < 0.1, f"1000 non-matches took {duration:.3f}s"

    def test_performance_match(self):
        """Test that matches are fast (early exit)."""
        router = FastPathRouter(enable_logging=False)

        # Matching query should exit early
        import time
        start = time.time()
        for _ in range(1000):
            router.try_fast_path("hello")
        duration = time.time() - start

        # Should complete 1000 matches in < 50ms
        assert duration < 0.05, f"1000 matches took {duration:.3f}s"
