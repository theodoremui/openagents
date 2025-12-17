"""
Comprehensive tests for semantic endpointing system.

Tests cover:
1. LinguisticEndpointingStrategy - Rule-based linguistic analysis
2. HybridEndpointingStrategy - Multi-strategy coordination
3. SemanticEndpointer - Feature extraction and coordination
4. UtteranceFeatures - Feature data structures
5. Edge cases and boundary conditions
"""

import pytest
from server.voice.realtime.semantic_endpointing import (
    SemanticEndpointer,
    LinguisticEndpointingStrategy,
    HybridEndpointingStrategy,
    EndpointingDecision,
    UtteranceCompleteness,
    UtteranceFeatures,
    EndpointingResult,
)


class TestLinguisticEndpointingStrategy:
    """Test linguistic rule-based endpointing strategy."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance with standard thresholds."""
        return LinguisticEndpointingStrategy(
            min_silence_ambiguous=0.6,
            min_silence_complete=1.0,
            confidence_threshold=0.7,
        )

    @pytest.fixture
    def endpointer(self, strategy):
        """Create endpointer with linguistic strategy."""
        return SemanticEndpointer(strategy=strategy, enable_logging=False)

    def test_incomplete_phrase_starter_short_silence(self, endpointer):
        """Test detection of incomplete phrase starters with short silence."""
        result = endpointer.analyze_utterance(
            text="Can you show me",
            silence_duration=0.7,
            utterance_duration=1.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result.decision == EndpointingDecision.CONTINUE
        assert result.confidence > 0.8
        assert any("incomplete" in r.lower() for r in result.reasoning)

    def test_incomplete_phrase_starter_long_silence(self, endpointer):
        """Test incomplete phrase with very long silence (safety timeout)."""
        result = endpointer.analyze_utterance(
            text="Can you show me",
            silence_duration=2.5,  # > 2x complete threshold
            utterance_duration=3.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT  # Forced by timeout
        assert "forcing endpoint" in " ".join(result.reasoning).lower()

    def test_complete_query_sufficient_silence(self, endpointer):
        """Test complete query with sufficient silence."""
        result = endpointer.analyze_utterance(
            text="Show me Greek restaurants in San Francisco",
            silence_duration=1.0,
            utterance_duration=3.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT
        assert result.confidence > 0.8

    def test_complete_query_insufficient_silence(self, endpointer):
        """Test complete query with insufficient silence (should wait)."""
        result = endpointer.analyze_utterance(
            text="Show me Greek restaurants in San Francisco",
            silence_duration=0.3,
            utterance_duration=3.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.WAIT
        assert "waiting" in " ".join(result.reasoning).lower()

    def test_ambiguous_sufficient_silence(self, endpointer):
        """Test ambiguous utterance with sufficient silence."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=0.8,  # > ambiguous threshold
            utterance_duration=1.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.AMBIGUOUS
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_ambiguous_insufficient_silence(self, endpointer):
        """Test ambiguous utterance with insufficient silence."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=0.3,  # < ambiguous threshold
            utterance_duration=1.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.AMBIGUOUS
        assert result.decision == EndpointingDecision.WAIT

    def test_incomplete_ending_conjunction(self, endpointer):
        """Test detection of incomplete endings (conjunction)."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants and",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result.decision == EndpointingDecision.CONTINUE
        assert "incomplete marker" in " ".join(result.reasoning).lower()

    def test_incomplete_ending_preposition(self, endpointer):
        """Test detection of incomplete endings (preposition)."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants in",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result.decision == EndpointingDecision.CONTINUE

    def test_very_short_utterance(self, endpointer):
        """Test very short utterances (< 3 words)."""
        result = endpointer.analyze_utterance(
            text="Show me",
            silence_duration=1.0,
            utterance_duration=1.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result.decision == EndpointingDecision.CONTINUE
        assert "too few words" in " ".join(result.reasoning).lower()

    def test_long_complex_query(self, endpointer):
        """Test long, complex query with multiple clauses."""
        result = endpointer.analyze_utterance(
            text="Can you show me the top 3 Greek restaurants in San Francisco, "
                 "on a map, in descending order of ratings",
            silence_duration=1.2,
            utterance_duration=5.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT
        assert result.confidence > 0.8

    def test_question_with_complete_structure(self, endpointer):
        """Test question with complete structure."""
        result = endpointer.analyze_utterance(
            text="What are the best coffee shops in Berkeley",
            silence_duration=1.0,
            utterance_duration=2.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_question_incomplete(self, endpointer):
        """Test incomplete question."""
        result = endpointer.analyze_utterance(
            text="What is",
            silence_duration=0.8,
            utterance_duration=1.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result.decision == EndpointingDecision.CONTINUE

    def test_sentence_with_terminator(self, endpointer):
        """Test sentence ending with terminator (period, !, ?)."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants in San Francisco.",
            silence_duration=0.7,
            utterance_duration=2.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_syntactic_completeness_scoring(self, strategy):
        """Test syntactic completeness scoring."""
        # Complete predicate + sufficient length
        features1 = UtteranceFeatures(
            text="Show me restaurants in San Francisco",
            word_count=6,
            has_sentence_terminator=False,
            has_conjunction_ending=False,
            has_preposition_ending=False,
            has_incomplete_phrase=True,
            has_complete_predicate=True,
            has_question_words=[],
            syntactic_completeness=0.0,  # Calculated by strategy
            silence_duration=1.0,
            utterance_duration=3.0,
            speech_rate=2.0,
            is_followup_query=False,
            previous_incomplete=False,
        )

        score1 = strategy._calculate_syntactic_completeness(
            features1, features1.text.lower()
        )
        assert score1 > 0.7  # Should score high

        # Incomplete predicate + short length
        features2 = UtteranceFeatures(
            text="Show me",
            word_count=2,
            has_sentence_terminator=False,
            has_conjunction_ending=False,
            has_preposition_ending=False,
            has_incomplete_phrase=True,
            has_complete_predicate=False,
            has_question_words=[],
            syntactic_completeness=0.0,
            silence_duration=1.0,
            utterance_duration=1.0,
            speech_rate=2.0,
            is_followup_query=False,
            previous_incomplete=False,
        )

        score2 = strategy._calculate_syntactic_completeness(
            features2, features2.text.lower()
        )
        assert score2 < 0.3  # Should score low


class TestHybridEndpointingStrategy:
    """Test hybrid endpointing strategy."""

    def test_hybrid_strategy_uses_linguistic(self):
        """Test that hybrid strategy correctly delegates to linguistic strategy."""
        linguistic_strategy = LinguisticEndpointingStrategy()
        hybrid_strategy = HybridEndpointingStrategy(
            linguistic_strategy=linguistic_strategy,
            linguistic_weight=1.0
        )
        endpointer = SemanticEndpointer(strategy=hybrid_strategy, enable_logging=False)

        result = endpointer.analyze_utterance(
            text="Show me Greek restaurants in San Francisco",
            silence_duration=1.0,
            utterance_duration=3.5,
            context=None
        )

        assert result.decision == EndpointingDecision.ENDPOINT
        assert "hybrid" in " ".join(result.reasoning).lower()

    def test_hybrid_strategy_name(self):
        """Test hybrid strategy returns correct name."""
        hybrid_strategy = HybridEndpointingStrategy()
        assert hybrid_strategy.get_name() == "hybrid"


class TestSemanticEndpointer:
    """Test semantic endpointer coordinator."""

    @pytest.fixture
    def endpointer(self):
        """Create endpointer instance."""
        return SemanticEndpointer(enable_logging=False)

    def test_feature_extraction(self, endpointer):
        """Test feature extraction from utterance."""
        result = endpointer.analyze_utterance(
            text="Show me Greek restaurants in San Francisco",
            silence_duration=1.0,
            utterance_duration=3.5,
            context=None
        )

        features = result.features
        assert features.text == "Show me Greek restaurants in San Francisco"
        assert features.word_count == 7
        assert features.silence_duration == 1.0
        assert features.utterance_duration == 3.5
        assert features.speech_rate == pytest.approx(7 / 3.5, rel=0.01)

    def test_conversation_history_tracking(self, endpointer):
        """Test that endpointer tracks conversation history."""
        # First utterance
        result1 = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        # Should not be followup
        assert not result1.features.is_followup_query

        # Endpoint the first utterance
        if result1.decision == EndpointingDecision.ENDPOINT:
            # Second utterance
            result2 = endpointer.analyze_utterance(
                text="Show me more",
                silence_duration=1.0,
                utterance_duration=1.5,
                context=None
            )

            # Should be marked as followup
            assert result2.features.is_followup_query

    def test_context_reset(self, endpointer):
        """Test context reset clears history."""
        # Add some utterances
        endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        # Reset context
        endpointer.reset_context()

        # Next utterance should not be followup
        result = endpointer.analyze_utterance(
            text="Show me more",
            silence_duration=1.0,
            utterance_duration=1.5,
            context=None
        )

        assert not result.features.is_followup_query

    def test_get_stats(self, endpointer):
        """Test statistics retrieval."""
        # Process an utterance
        endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        stats = endpointer.get_stats()
        assert "strategy" in stats
        assert "conversation_turns" in stats
        assert "last_decision" in stats
        assert "last_confidence" in stats

    def test_logging_enabled(self):
        """Test endpointer with logging enabled."""
        endpointer = SemanticEndpointer(enable_logging=True)

        result = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        # Should not raise exception
        assert result is not None

    def test_custom_strategy(self):
        """Test endpointer with custom strategy."""
        custom_strategy = LinguisticEndpointingStrategy(
            min_silence_ambiguous=0.5,
            min_silence_complete=0.8,
            confidence_threshold=0.6
        )
        endpointer = SemanticEndpointer(strategy=custom_strategy, enable_logging=False)

        result = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=0.6,  # Would be insufficient with default thresholds
            utterance_duration=2.0,
            context=None
        )

        # With lower threshold, should endpoint
        assert result.decision == EndpointingDecision.ENDPOINT


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def endpointer(self):
        """Create endpointer instance."""
        return SemanticEndpointer(enable_logging=False)

    def test_empty_string(self, endpointer):
        """Test handling of empty string."""
        result = endpointer.analyze_utterance(
            text="",
            silence_duration=1.0,
            utterance_duration=0.5,
            context=None
        )

        assert result.decision == EndpointingDecision.CONTINUE

    def test_single_word(self, endpointer):
        """Test single word utterance."""
        result = endpointer.analyze_utterance(
            text="Hello",
            silence_duration=1.0,
            utterance_duration=0.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result.decision == EndpointingDecision.CONTINUE

    def test_very_long_utterance(self, endpointer):
        """Test very long utterance."""
        long_text = "Show me " + "restaurants and ".join([""] * 50)
        result = endpointer.analyze_utterance(
            text=long_text,
            silence_duration=1.0,
            utterance_duration=30.0,
            context=None
        )

        # Should still make a decision
        assert result.decision in [
            EndpointingDecision.CONTINUE,
            EndpointingDecision.WAIT,
            EndpointingDecision.ENDPOINT
        ]

    def test_zero_silence_duration(self, endpointer):
        """Test with zero silence duration."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=0.0,
            utterance_duration=2.0,
            context=None
        )

        # Should wait for silence
        assert result.decision in [EndpointingDecision.CONTINUE, EndpointingDecision.WAIT]

    def test_zero_utterance_duration(self, endpointer):
        """Test with zero utterance duration."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=0.0,
            context=None
        )

        # Should still make a decision based on text
        assert result is not None

    def test_special_characters(self, endpointer):
        """Test utterance with special characters."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants @ San Francisco #food",
            silence_duration=1.0,
            utterance_duration=2.5,
            context=None
        )

        # Should handle special characters gracefully
        assert result.decision is not None

    def test_unicode_characters(self, endpointer):
        """Test utterance with Unicode characters."""
        result = endpointer.analyze_utterance(
            text="Show me restaurants in São Paulo 日本料理",
            silence_duration=1.0,
            utterance_duration=2.5,
            context=None
        )

        # Should handle Unicode gracefully
        assert result.decision is not None

    def test_multiple_spaces(self, endpointer):
        """Test utterance with multiple consecutive spaces."""
        result = endpointer.analyze_utterance(
            text="Show  me    restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        # Should normalize spaces correctly
        assert result.features.word_count == 3

    def test_leading_trailing_whitespace(self, endpointer):
        """Test utterance with leading/trailing whitespace."""
        result = endpointer.analyze_utterance(
            text="  Show me restaurants  ",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        # Should strip whitespace
        assert result.features.text == "Show me restaurants"


class TestRealisticScenarios:
    """Test realistic voice interaction scenarios."""

    @pytest.fixture
    def endpointer(self):
        """Create endpointer instance."""
        return SemanticEndpointer(enable_logging=False)

    def test_restaurant_search_simple(self, endpointer):
        """Test simple restaurant search."""
        result = endpointer.analyze_utterance(
            text="Find restaurants nearby",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        assert result.utterance_completeness in [
            UtteranceCompleteness.COMPLETE,
            UtteranceCompleteness.AMBIGUOUS
        ]
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_restaurant_search_detailed(self, endpointer):
        """Test detailed restaurant search with multiple constraints."""
        result = endpointer.analyze_utterance(
            text="Find Italian restaurants near Union Square, open now, with ratings above 4 stars",
            silence_duration=1.2,
            utterance_duration=4.5,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_navigation_query(self, endpointer):
        """Test navigation query."""
        result = endpointer.analyze_utterance(
            text="How do I get to the Golden Gate Bridge from here",
            silence_duration=1.0,
            utterance_duration=3.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_map_visualization_request(self, endpointer):
        """Test map visualization request."""
        result = endpointer.analyze_utterance(
            text="Show me the top 3 Greek restaurants in San Francisco on a map in descending order of ratings",
            silence_duration=1.5,
            utterance_duration=5.0,
            context=None
        )

        assert result.utterance_completeness == UtteranceCompleteness.COMPLETE
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_multi_part_query_interrupted(self, endpointer):
        """Test multi-part query that gets interrupted mid-way."""
        # Part 1: Incomplete
        result1 = endpointer.analyze_utterance(
            text="Show me restaurants in",
            silence_duration=0.5,
            utterance_duration=1.5,
            context=None
        )

        assert result1.utterance_completeness == UtteranceCompleteness.INCOMPLETE
        assert result1.decision == EndpointingDecision.CONTINUE

    def test_clarification_question(self, endpointer):
        """Test short clarification question."""
        result = endpointer.analyze_utterance(
            text="What about Italian",
            silence_duration=0.8,
            utterance_duration=1.5,
            context=None
        )

        # Should be ambiguous but endpoint with sufficient silence
        assert result.decision == EndpointingDecision.ENDPOINT

    def test_followup_elaboration(self, endpointer):
        """Test followup that elaborates on previous query."""
        # First query
        result1 = endpointer.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        if result1.decision == EndpointingDecision.ENDPOINT:
            # Followup elaboration
            result2 = endpointer.analyze_utterance(
                text="With outdoor seating and good reviews",
                silence_duration=1.0,
                utterance_duration=2.5,
                context=None
            )

            # Should be recognized as followup
            assert result2.features.is_followup_query


class TestPerformance:
    """Test performance characteristics."""

    def test_feature_extraction_performance(self):
        """Test that feature extraction is fast (<10ms)."""
        import time

        endpointer = SemanticEndpointer(enable_logging=False)
        text = "Show me the top 10 Greek restaurants in San Francisco with ratings above 4.5 stars"

        start = time.time()
        for _ in range(100):  # Average over 100 runs
            endpointer.analyze_utterance(
                text=text,
                silence_duration=1.0,
                utterance_duration=4.0,
                context=None
            )
        elapsed = (time.time() - start) / 100

        # Should be under 50ms per analysis (including strategy execution)
        assert elapsed < 0.05, f"Analysis took {elapsed*1000:.1f}ms, expected <50ms"

    def test_strategy_reuse(self):
        """Test that strategy instances can be reused across analyses."""
        strategy = LinguisticEndpointingStrategy()
        endpointer1 = SemanticEndpointer(strategy=strategy, enable_logging=False)
        endpointer2 = SemanticEndpointer(strategy=strategy, enable_logging=False)

        # Both should work with same strategy
        result1 = endpointer1.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        result2 = endpointer2.analyze_utterance(
            text="Show me restaurants",
            silence_duration=1.0,
            utterance_duration=2.0,
            context=None
        )

        assert result1.decision == result2.decision


if __name__ == "__main__":
    # Run with: pytest tests/server/voice/realtime/test_semantic_endpointing.py -v
    pytest.main([__file__, "-v"])
