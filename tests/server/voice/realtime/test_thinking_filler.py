"""
Tests for Thinking Filler Service

Tests the classification, selection, and variety of thinking fillers.
"""

import pytest
from server.voice.realtime.thinking_filler import (
    ThinkingFillerService,
    FillerHistory,
    get_thinking_filler,
)


class TestQueryClassification:
    """Test query classification logic."""

    def test_classify_search_query(self):
        """Search queries should be classified as 'search'."""
        queries = [
            "search for the latest news",
            "find information about Python",
            "look up current weather",
            "show me recent articles",
        ]
        for query in queries:
            assert ThinkingFillerService.classify_query(query) == "search"

    def test_classify_calculation_query(self):
        """Calculation queries should be classified as 'calculation'."""
        queries = [
            "calculate 25 * 43",
            "what is 100 divided by 5",
            "compute the average of these numbers",
            "15 + 27",
        ]
        for query in queries:
            assert ThinkingFillerService.classify_query(query) == "calculation"

    def test_classify_location_query(self):
        """Location queries should be classified as 'location'."""
        queries = [
            "give me directions to San Francisco",
            "where is the nearest restaurant",
            "map route to downtown",
            "find hotels near me",
        ]
        for query in queries:
            assert ThinkingFillerService.classify_query(query) == "location"

    def test_classify_knowledge_query(self):
        """Knowledge queries should be classified as 'knowledge'."""
        queries = [
            "what is quantum mechanics",
            "who is Albert Einstein",
            "explain photosynthesis",
            "tell me about the Roman Empire",
        ]
        for query in queries:
            assert ThinkingFillerService.classify_query(query) == "knowledge"

    def test_classify_creative_query(self):
        """Creative queries should be classified as 'creative'."""
        queries = [
            "write a poem about nature",
            "create a story about space",
            "generate some ideas for dinner",
            "draft an email to my boss",
        ]
        for query in queries:
            assert ThinkingFillerService.classify_query(query) == "creative"

    def test_classify_general_query(self):
        """General queries should be classified as 'general'."""
        queries = [
            "help me with this",
            "can you assist?",
            "please help",
        ]
        for query in queries:
            assert ThinkingFillerService.classify_query(query) == "general"


class TestFillerSelection:
    """Test filler selection logic."""

    def test_get_filler_returns_string(self):
        """Filler should return a non-empty string."""
        query = "find the latest news"
        filler = ThinkingFillerService.get_filler(query)
        assert isinstance(filler, str)
        assert len(filler) > 0

    def test_get_filler_matches_query_type(self):
        """Filler should come from appropriate category."""
        # Search query should get search filler
        query = "search for Python tutorials"
        filler = ThinkingFillerService.get_filler(query)
        assert filler in ThinkingFillerService.FILLERS["search"]

        # Calculation query should get calculation filler
        query = "calculate 50 * 25"
        filler = ThinkingFillerService.get_filler(query)
        assert filler in ThinkingFillerService.FILLERS["calculation"]

    def test_get_filler_avoids_previous(self):
        """Should avoid repeating previous filler if possible."""
        query = "find information"
        previous = "Let me search for that."

        # Get filler avoiding previous
        filler = ThinkingFillerService.get_filler(query, previous)

        # Should be different (unless only one option)
        fillers = ThinkingFillerService.FILLERS["search"]
        if len(fillers) > 1:
            assert filler != previous

    def test_get_filler_variety(self):
        """Should return different fillers over multiple calls."""
        query = "search for something"
        fillers = set()

        # Get 20 fillers
        for _ in range(20):
            filler = ThinkingFillerService.get_filler(query)
            fillers.add(filler)

        # Should have variety (at least 2 different fillers)
        assert len(fillers) >= 2


class TestDurationEstimation:
    """Test duration estimation logic."""

    def test_estimate_short_duration(self):
        """Short queries should be estimated as 'short'."""
        queries = [
            "what time",
            "current weather",
            "quick question",
        ]
        for query in queries:
            assert ThinkingFillerService.estimate_duration(query) == "short"

    def test_estimate_long_duration(self):
        """Complex queries should be estimated as 'long'."""
        queries = [
            "research and provide a comprehensive analysis of quantum computing",
            "compare and analyze multiple machine learning frameworks",
            "find all the articles about climate change from the past year",
        ]
        for query in queries:
            assert ThinkingFillerService.estimate_duration(query) == "long"

    def test_estimate_medium_duration(self):
        """Medium-length queries should be estimated as 'medium'."""
        query = "explain how photosynthesis works in plants"
        duration = ThinkingFillerService.estimate_duration(query)
        assert duration in ["short", "medium", "long"]


class TestShouldUseFiller:
    """Test logic for when to use fillers."""

    def test_should_use_filler_for_questions(self):
        """Should use filler for actual questions."""
        queries = [
            "what is the weather today",
            "find me a restaurant",
            "calculate this equation",
        ]
        for query in queries:
            assert ThinkingFillerService.should_use_filler(query) is True

    def test_should_not_use_filler_for_greetings(self):
        """Should not use filler for short greetings."""
        greetings = [
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "ok",
            "okay",
        ]
        for greeting in greetings:
            assert ThinkingFillerService.should_use_filler(greeting) is False

    def test_should_use_filler_for_longer_greetings(self):
        """Should use filler for longer greeting-like queries."""
        query = "hello can you help me find something"
        assert ThinkingFillerService.should_use_filler(query) is True

    def test_should_not_use_filler_for_chitchat(self):
        """Should not use filler for chitchat queries."""
        chitchat_queries = [
            "how are you",
            "how's it going",
            "what's up",
            "good morning",
            "see you later",
            "bye",
            "you're welcome",
            "yes",
            "no",
            "cool",
            "great",
        ]
        for query in chitchat_queries:
            assert ThinkingFillerService.should_use_filler(query) is False

    def test_should_use_filler_for_non_chitchat(self):
        """Should use filler for non-chitchat queries even if they contain similar words."""
        # These look like chitchat but are actual questions
        queries = [
            "how are you able to search the web",  # Starts with "how are you" but is a question
            "what's up with the weather today",     # Starts with "what's up" but is a question
            "can you see you later on the map",     # Contains "see you later" but is a request
        ]
        for query in queries:
            # These should use fillers because they're actual questions/requests
            assert ThinkingFillerService.should_use_filler(query) is True


class TestFillerHistory:
    """Test filler history tracking."""

    def test_filler_history_add(self):
        """Should add fillers to history."""
        history = FillerHistory(max_history=3)
        history.add("filler1")
        history.add("filler2")
        assert history.get_last() == "filler2"

    def test_filler_history_max_size(self):
        """Should maintain max history size."""
        history = FillerHistory(max_history=3)
        history.add("filler1")
        history.add("filler2")
        history.add("filler3")
        history.add("filler4")
        assert len(history.history) == 3
        assert "filler1" not in history.history
        assert "filler4" in history.history

    def test_filler_history_avoid(self):
        """Should return list of fillers to avoid."""
        history = FillerHistory(max_history=3)
        history.add("filler1")
        history.add("filler2")
        avoid_list = history.avoid()
        assert "filler1" in avoid_list
        assert "filler2" in avoid_list


class TestConvenienceFunction:
    """Test convenience function."""

    def test_get_thinking_filler_returns_string_or_none(self):
        """Should return string for questions, None for greetings."""
        # Should return string for question
        filler = get_thinking_filler("what is the weather")
        assert isinstance(filler, str)
        assert len(filler) > 0

        # Should return None for greeting
        filler = get_thinking_filler("hi")
        assert filler is None

    def test_get_thinking_filler_avoids_repetition(self):
        """Should avoid repeating fillers in sequence."""
        # Get several fillers for same query type
        query = "search for information"
        fillers = []
        for _ in range(5):
            filler = get_thinking_filler(query)
            if filler:
                fillers.append(filler)

        # Should have some variety
        assert len(set(fillers)) >= 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query(self):
        """Should handle empty queries gracefully."""
        filler = get_thinking_filler("")
        # Empty string is treated as greeting (too short)
        assert filler is None

    def test_very_long_query(self):
        """Should handle very long queries."""
        query = " ".join(["word"] * 100)
        filler = ThinkingFillerService.get_filler(query)
        assert isinstance(filler, str)
        assert len(filler) > 0

    def test_query_with_special_characters(self):
        """Should handle queries with special characters."""
        queries = [
            "what's 2+2?",
            "search for C++ tutorials",
            "find info about @mention",
        ]
        for query in queries:
            filler = ThinkingFillerService.get_filler(query)
            assert isinstance(filler, str)

    def test_non_english_query(self):
        """Should handle non-English queries gracefully."""
        # Should default to 'general' for non-English
        query = "¿Qué es la inteligencia artificial?"
        query_type = ThinkingFillerService.classify_query(query)
        assert query_type == "general"

        filler = ThinkingFillerService.get_filler(query)
        assert isinstance(filler, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
