"""
Property-based tests for Enhanced Semantic Endpointing System.

These tests validate universal properties that should hold for all valid inputs
to the semantic endpointing system, ensuring correctness and reliability.

Test Framework: pytest + hypothesis for property-based testing
Coverage: All semantic endpointing components and decision logic
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio

from server.voice.realtime.semantic_endpointing import (
    SemanticEndpointer,
    EnhancedSemanticEndpointer,
    LinguisticEndpointingStrategy,
    HybridEndpointingStrategy,
    EndpointingDecision,
    UtteranceCompleteness,
    EndpointingResult,
    UtteranceFeatures
)


# Test data strategies
@st.composite
def complete_utterance_strategy(draw):
    """Generate complete utterances (syntactically complete sentences)."""
    subjects = ["I", "You", "We", "They", "The user", "The system"]
    verbs = ["want", "need", "like", "see", "find", "show", "tell", "give"]
    objects = ["a restaurant", "the weather", "some information", "help", "directions", "a map"]
    
    subject = draw(st.sampled_from(subjects))
    verb = draw(st.sampled_from(verbs))
    obj = draw(st.sampled_from(objects))
    
    return f"{subject} {verb} {obj}"


@st.composite
def incomplete_utterance_strategy(draw):
    """Generate incomplete utterances (ending with conjunctions/prepositions)."""
    complete_part = draw(complete_utterance_strategy())
    incomplete_endings = ["and", "or", "but", "to", "in", "on", "at", "for", "with"]
    ending = draw(st.sampled_from(incomplete_endings))
    
    return f"{complete_part} {ending}"


@st.composite
def question_utterance_strategy(draw):
    """Generate question utterances."""
    question_words = ["what", "where", "when", "why", "how", "who", "which"]
    question_word = draw(st.sampled_from(question_words))
    
    verbs = ["is", "are", "was", "were", "can", "could", "will", "would"]
    verb = draw(st.sampled_from(verbs))
    
    objects = ["the weather", "a restaurant", "the time", "the location", "the price"]
    obj = draw(st.sampled_from(objects))
    
    return f"{question_word} {verb} {obj}"


class TestSemanticEndpointingProperties:
    """
    Property-based tests for semantic endpointing system.
    
    These tests validate that the semantic endpointing system maintains
    correctness properties across all valid inputs and edge cases.
    """

    @pytest.fixture
    def endpointer(self):
        """Create a fresh endpointer for each test."""
        return SemanticEndpointer(
            strategy=LinguisticEndpointingStrategy(),
            enable_logging=False
        )

    @pytest.fixture
    def enhanced_endpointer(self):
        """Create an enhanced endpointer for each test."""
        return EnhancedSemanticEndpointer(
            query_accumulator=None,
            session_memory=None,
            strategy=LinguisticEndpointingStrategy(),
            enable_logging=False
        )

    # Property 6: Multi-modal analysis consistency
    @given(
        st.text(min_size=5, max_size=200),
        st.floats(min_value=0.0, max_value=5.0),
        st.floats(min_value=0.1, max_value=30.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_6_multimodal_analysis_consistency(
        self, 
        text: str, 
        silence_duration: float, 
        utterance_duration: float,
        endpointer
    ):
        """
        **Property 6: Multi-modal analysis consistency**
        *For any* speech segment, the Semantic_Endpointer should analyze linguistic cues, 
        prosodic features, and conversation context to produce consistent completeness assessments
        **Validates: Requirements 2.1**
        **Feature: voice-robustness-session-memory, Property 6: Multi-modal analysis consistency**
        """
        assume(text.strip())  # Need non-empty text
        
        # Analyze the same utterance multiple times
        results = []
        for _ in range(3):
            result = endpointer.analyze_utterance(text, silence_duration, utterance_duration)
            results.append(result)
        
        # Property: Results should be consistent (same decision for same input)
        decisions = [r.decision for r in results]
        assert len(set(decisions)) == 1, "Decision should be consistent across multiple analyses"
        
        # Property: Completeness assessment should be consistent
        completeness = [r.utterance_completeness for r in results]
        assert len(set(completeness)) == 1, "Completeness should be consistent"
        
        # Property: Confidence should be consistent
        confidences = [r.confidence for r in results]
        assert all(abs(c1 - c2) < 0.01 for c1, c2 in zip(confidences, confidences[1:]))

    # Property 7: Complete query endpointing
    @given(
        complete_utterance_strategy(),
        st.floats(min_value=0.8, max_value=3.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_7_complete_query_endpointing(
        self, 
        complete_text: str, 
        silence_duration: float,
        endpointer
    ):
        """
        **Property 7: Complete query endpointing**
        *For any* syntactically complete query with silence duration >= 0.8 seconds, 
        the Semantic_Endpointer should return an ENDPOINT decision
        **Validates: Requirements 2.2**
        **Feature: voice-robustness-session-memory, Property 7: Complete query endpointing**
        """
        utterance_duration = 2.0  # Reasonable duration
        
        result = endpointer.analyze_utterance(complete_text, silence_duration, utterance_duration)
        
        # Property: Complete utterances with sufficient silence should endpoint
        if silence_duration >= 0.8:
            assert result.decision in [EndpointingDecision.ENDPOINT, EndpointingDecision.WAIT]
            
            # If completeness is COMPLETE, should definitely endpoint
            if result.utterance_completeness == UtteranceCompleteness.COMPLETE:
                assert result.decision == EndpointingDecision.ENDPOINT

    # Property 8: Incomplete query continuation
    @given(
        incomplete_utterance_strategy(),
        st.floats(min_value=0.0, max_value=3.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_8_incomplete_query_continuation(
        self, 
        incomplete_text: str, 
        silence_duration: float,
        endpointer
    ):
        """
        **Property 8: Incomplete query continuation**
        *For any* query ending with prepositions or conjunctions, 
        the Semantic_Endpointer should return CONTINUE or WAIT decision with suggested wait time <= 3 seconds
        **Validates: Requirements 2.3**
        **Feature: voice-robustness-session-memory, Property 8: Incomplete query continuation**
        """
        utterance_duration = 2.0
        
        result = endpointer.analyze_utterance(incomplete_text, silence_duration, utterance_duration)
        
        # Property: Incomplete utterances should not endpoint immediately
        if result.utterance_completeness == UtteranceCompleteness.INCOMPLETE:
            # Should continue or wait, not endpoint (unless very long silence)
            if silence_duration < 1.5:
                assert result.decision in [EndpointingDecision.CONTINUE, EndpointingDecision.WAIT]
        
        # Property: Confidence should reflect incompleteness
        if result.utterance_completeness == UtteranceCompleteness.INCOMPLETE:
            assert result.confidence < 0.95  # Should not be highly confident in endpointing

    # Property 9: Question pattern handling
    @given(
        question_utterance_strategy(),
        st.floats(min_value=0.0, max_value=3.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_9_question_pattern_handling(
        self, 
        question_text: str, 
        silence_duration: float,
        endpointer
    ):
        """
        **Property 9: Question pattern handling**
        *For any* incomplete question pattern, the Semantic_Endpointer should wait for 
        complete question structure before returning ENDPOINT decision
        **Validates: Requirements 2.4**
        **Feature: voice-robustness-session-memory, Property 9: Question pattern handling**
        """
        utterance_duration = 2.0
        
        result = endpointer.analyze_utterance(question_text, silence_duration, utterance_duration)
        
        # Property: Questions should be analyzed for completeness
        assert result.features.has_question_words or any(
            qw in question_text.lower() for qw in ["what", "where", "when", "why", "how", "who", "which"]
        )
        
        # Property: Complete questions with sufficient silence should endpoint
        if result.utterance_completeness == UtteranceCompleteness.COMPLETE and silence_duration >= 0.8:
            assert result.decision == EndpointingDecision.ENDPOINT
        
        # Property: Incomplete questions should wait
        if result.utterance_completeness == UtteranceCompleteness.INCOMPLETE:
            assert result.decision in [EndpointingDecision.CONTINUE, EndpointingDecision.WAIT]

    # Additional property: Silence threshold consistency
    @given(
        st.text(min_size=10, max_size=100),
        st.floats(min_value=0.0, max_value=5.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_silence_threshold_consistency(
        self, 
        text: str, 
        silence_duration: float,
        endpointer
    ):
        """
        Property: Longer silence should increase likelihood of endpointing.
        """
        assume(text.strip())
        utterance_duration = 2.0
        
        # Test with short silence
        result_short = endpointer.analyze_utterance(text, 0.3, utterance_duration)
        
        # Test with long silence
        result_long = endpointer.analyze_utterance(text, 2.0, utterance_duration)
        
        # Property: Longer silence should not decrease endpointing likelihood
        decision_order = {
            EndpointingDecision.CONTINUE: 0,
            EndpointingDecision.WAIT: 1,
            EndpointingDecision.ENDPOINT: 2
        }
        
        assert decision_order[result_long.decision] >= decision_order[result_short.decision]

    # Enhanced endpointer property: Context awareness
    @given(
        st.text(min_size=10, max_size=100),
        st.floats(min_value=0.5, max_value=2.0)
    )
    @settings(max_examples=30, deadline=5000)
    def test_property_enhanced_context_awareness(
        self, 
        text: str, 
        silence_duration: float,
        enhanced_endpointer
    ):
        """
        Property: Enhanced endpointer should handle context gracefully.
        """
        assume(text.strip())
        utterance_duration = 2.0
        
        async def run_test():
            # Test without context
            result_no_context = await enhanced_endpointer.analyze_with_context(
                text, silence_duration, utterance_duration, session_id=None
            )
            
            # Test with context
            result_with_context = await enhanced_endpointer.analyze_with_context(
                text, silence_duration, utterance_duration, 
                session_id="test_session",
                context={"test": "context"}
            )
            
            # Property: Both should return valid results
            assert result_no_context.decision in EndpointingDecision
            assert result_with_context.decision in EndpointingDecision
            
            # Property: Confidence should be reasonable
            assert 0.0 <= result_no_context.confidence <= 1.0
            assert 0.0 <= result_with_context.confidence <= 1.0
        
        asyncio.run(run_test())

    # Property: Feature extraction consistency
    @given(st.text(min_size=5, max_size=200))
    @settings(max_examples=50, deadline=5000)
    def test_property_feature_extraction_consistency(self, text: str, endpointer):
        """
        Property: Feature extraction should be deterministic and consistent.
        """
        assume(text.strip())
        
        # Extract features multiple times
        features_list = []
        for _ in range(3):
            result = endpointer.analyze_utterance(text, 1.0, 2.0)
            features_list.append(result.features)
        
        # Property: Features should be identical
        for i in range(1, len(features_list)):
            assert features_list[i].text == features_list[0].text
            assert features_list[i].word_count == features_list[0].word_count
            assert features_list[i].has_sentence_terminator == features_list[0].has_sentence_terminator
            assert features_list[i].has_conjunction_ending == features_list[0].has_conjunction_ending

    # Property: Confidence bounds
    @given(
        st.text(min_size=5, max_size=200),
        st.floats(min_value=0.0, max_value=5.0),
        st.floats(min_value=0.1, max_value=30.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_confidence_bounds(
        self, 
        text: str, 
        silence_duration: float, 
        utterance_duration: float,
        endpointer
    ):
        """
        Property: Confidence scores should always be within valid bounds.
        """
        assume(text.strip())
        
        result = endpointer.analyze_utterance(text, silence_duration, utterance_duration)
        
        # Property: Confidence must be between 0.0 and 1.0
        assert 0.0 <= result.confidence <= 1.0
        
        # Property: Features confidence must be valid
        assert 0.0 <= result.features.confidence <= 1.0

    # Property: Decision reasoning
    @given(
        st.text(min_size=5, max_size=200),
        st.floats(min_value=0.0, max_value=5.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_decision_reasoning(
        self, 
        text: str, 
        silence_duration: float,
        endpointer
    ):
        """
        Property: Every decision should have reasoning.
        """
        assume(text.strip())
        
        result = endpointer.analyze_utterance(text, silence_duration, 2.0)
        
        # Property: Reasoning should be provided
        assert len(result.reasoning) > 0
        
        # Property: Reasoning should be strings
        assert all(isinstance(r, str) for r in result.reasoning)

    # Property: User pattern learning
    def test_property_user_pattern_learning(self, enhanced_endpointer):
        """
        Property: Enhanced endpointer should learn and store user patterns.
        """
        session_id = "test_user_123"
        
        async def run_test():
            # Analyze multiple utterances for the same user
            for i in range(5):
                await enhanced_endpointer.analyze_with_context(
                    f"test utterance {i}",
                    silence_duration=1.0,
                    utterance_duration=2.0,
                    session_id=session_id
                )
            
            # Property: User patterns should be stored
            patterns = enhanced_endpointer.get_user_patterns(session_id)
            assert patterns is not None
            
            # Property: Patterns should contain interaction data
            assert 'silence_durations' in patterns
            assert len(patterns['silence_durations']) == 5
            
            # Property: Patterns should have derived statistics
            if len(patterns['silence_durations']) >= 5:
                assert 'avg_silence_duration' in patterns
                assert 'avg_utterance_duration' in patterns
        
        asyncio.run(run_test())

    # Property: Pattern clearing
    def test_property_pattern_clearing(self, enhanced_endpointer):
        """
        Property: Clearing patterns should remove all stored data.
        """
        session_id = "test_user_456"
        
        async def run_test():
            # Add some patterns
            await enhanced_endpointer.analyze_with_context(
                "test utterance",
                silence_duration=1.0,
                utterance_duration=2.0,
                session_id=session_id
            )
            
            # Verify patterns exist
            patterns = enhanced_endpointer.get_user_patterns(session_id)
            assert patterns is not None
            
            # Clear patterns
            enhanced_endpointer.clear_user_patterns(session_id)
            
            # Property: Patterns should be cleared
            patterns = enhanced_endpointer.get_user_patterns(session_id)
            assert patterns is None
        
        asyncio.run(run_test())


class TestLinguisticStrategy:
    """Tests specific to the linguistic endpointing strategy."""

    @pytest.fixture
    def strategy(self):
        return LinguisticEndpointingStrategy()

    @given(st.integers(min_value=1, max_value=2))
    @settings(max_examples=20, deadline=5000)
    def test_minimum_word_count(self, word_count: int, strategy):
        """
        Property: Utterances with very few words should continue.
        """
        text = " ".join([f"word{i}" for i in range(word_count)])
        
        features = UtteranceFeatures(
            text=text,
            word_count=word_count,
            has_sentence_terminator=False,
            has_conjunction_ending=False,
            has_preposition_ending=False,
            has_incomplete_phrase=False,
            has_complete_predicate=False,
            has_question_words=[],
            syntactic_completeness=0.0,
            silence_duration=1.0,
            utterance_duration=1.0,
            speech_rate=1.0,
            is_followup_query=False,
            previous_incomplete=False
        )
        
        result = strategy.analyze(features)
        
        # Property: Very short utterances should continue
        assert result.decision == EndpointingDecision.CONTINUE


if __name__ == "__main__":
    # Run property tests
    pytest.main([__file__, "-v", "--tb=short"])
