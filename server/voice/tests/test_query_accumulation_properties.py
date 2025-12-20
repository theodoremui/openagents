"""
Property-based tests for Query Accumulation System.

These tests validate universal properties that should hold for all valid inputs
to the query accumulation system, ensuring correctness and reliability.

Test Framework: pytest + hypothesis for property-based testing
Coverage: All query accumulation components and edge cases
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, invariant
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio

from server.voice.query_accumulation import (
    IQueryAccumulator,
    BufferedQueryAccumulator,
    SpeechSegment,
    AccumulatedQuery,
    QueryStatus
)


# Test data strategies
@st.composite
def speech_segment_strategy(draw):
    """Generate valid SpeechSegment instances."""
    start_time = draw(st.floats(min_value=0.0, max_value=3600.0))
    duration = draw(st.floats(min_value=0.01, max_value=30.0))
    end_time = start_time + duration
    
    return SpeechSegment(
        text=draw(st.text(min_size=0, max_size=500)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        start_time=start_time,
        end_time=end_time,
        silence_after=draw(st.floats(min_value=0.0, max_value=5.0))
    )


@st.composite
def speech_segment_sequence_strategy(draw):
    """Generate sequences of speech segments with realistic timing."""
    segments = []
    current_time = 0.0
    
    num_segments = draw(st.integers(min_value=1, max_value=20))
    
    for _ in range(num_segments):
        # Add some gap between segments
        gap = draw(st.floats(min_value=0.0, max_value=2.0))
        current_time += gap
        
        # Create segment
        duration = draw(st.floats(min_value=0.1, max_value=5.0))
        silence_after = draw(st.floats(min_value=0.0, max_value=3.0))
        
        segment = SpeechSegment(
            text=draw(st.text(min_size=1, max_size=100)),
            confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
            start_time=current_time,
            end_time=current_time + duration,
            silence_after=silence_after
        )
        
        segments.append(segment)
        current_time = segment.end_time + silence_after
    
    return segments


class TestQueryAccumulationProperties:
    """
    Property-based tests for query accumulation system.
    
    These tests validate that the query accumulation system maintains
    correctness properties across all valid inputs and edge cases.
    """

    @pytest.fixture
    def accumulator(self):
        """Create a fresh accumulator for each test."""
        return BufferedQueryAccumulator(
            max_buffer_duration=45.0,
            min_confidence=0.6,
            stutter_threshold=0.3,
            normalization_enabled=True
        )

    # Property 1: Speech segment buffering with pauses
    @given(speech_segment_sequence_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_property_1_speech_segment_buffering_with_pauses(self, segments: List[SpeechSegment]):
        """
        **Property 1: Speech segment buffering with pauses**
        *For any* sequence of speech segments with pauses up to 2 seconds, 
        the Query_Accumulator should combine them into a single accumulated query
        **Validates: Requirements 1.1**
        **Feature: voice-robustness-session-memory, Property 1: Speech segment buffering with pauses**
        """
        # Filter segments to have pauses <= 2 seconds
        filtered_segments = [seg for seg in segments if seg.silence_after <= 2.0]
        assume(len(filtered_segments) >= 2)  # Need multiple segments to test buffering
        
        accumulator = BufferedQueryAccumulator()
        
        async def run_test():
            accumulated_queries = []
            
            for segment in filtered_segments:
                result = await accumulator.add_segment(segment)
                accumulated_queries.append(result)
            
            # All segments with pauses <= 2s should be buffered together
            final_query = accumulated_queries[-1]
            
            # Property: All segments should be combined into single query
            assert final_query.segment_count == len(filtered_segments)
            
            # Property: Combined text should contain all segment texts
            combined_text = final_query.text
            for segment in filtered_segments:
                if segment.text.strip():  # Only check non-empty texts
                    # Text should be present (may be normalized)
                    assert any(word in combined_text.lower() for word in segment.text.lower().split() if word)
            
            # Property: Status should be ACCUMULATING (not forced completion)
            assert final_query.status == QueryStatus.ACCUMULATING
        
        asyncio.run(run_test())

    # Property 2: Query appending behavior
    @given(st.lists(speech_segment_strategy(), min_size=2, max_size=10))
    @settings(max_examples=50, deadline=5000)
    def test_property_2_query_appending_behavior(self, segments: List[SpeechSegment]):
        """
        **Property 2: Query appending behavior**
        *For any* existing query buffer and new speech segment, adding the segment 
        should append the text while preserving the existing content
        **Validates: Requirements 1.2**
        **Feature: voice-robustness-session-memory, Property 2: Query appending behavior**
        """
        accumulator = BufferedQueryAccumulator()
        
        async def run_test():
            previous_texts = []
            
            for i, segment in enumerate(segments):
                result = await accumulator.add_segment(segment)
                
                # Property: Previous texts should still be present
                current_text = result.text.lower()
                for prev_text in previous_texts:
                    if prev_text.strip():  # Only check non-empty texts
                        # Previous content should be preserved (may be normalized)
                        prev_words = prev_text.split()
                        if prev_words:
                            assert any(word in current_text for word in prev_words)
                
                # Property: Segment count should increase
                assert result.segment_count == i + 1
                
                # Property: New segment should be included
                if segment.text.strip():
                    segment_words = segment.text.lower().split()
                    if segment_words:
                        assert any(word in current_text for word in segment_words)
                
                previous_texts.append(segment.text)
        
        asyncio.run(run_test())

    # Property 3: Stutter normalization
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50, deadline=5000)
    def test_property_3_stutter_normalization(self, base_text: str):
        """
        **Property 3: Stutter normalization**
        *For any* speech segment containing repeated words or stutters, 
        the Query_Accumulator should normalize the text by removing obvious repetitions
        **Validates: Requirements 1.3**
        **Feature: voice-robustness-session-memory, Property 3: Stutter normalization**
        """
        assume(base_text.strip())  # Need non-empty text
        
        # Create stuttered text by repeating words
        words = base_text.split()
        assume(len(words) >= 1)
        
        # Add stutters to first few words
        stuttered_words = []
        for i, word in enumerate(words[:3]):  # Only stutter first 3 words
            if word.lower() in BufferedQueryAccumulator.STUTTER_PRONE_WORDS:
                stuttered_words.extend([word, word])  # Repeat the word
            else:
                stuttered_words.append(word)
        
        # Add remaining words
        stuttered_words.extend(words[3:])
        stuttered_text = ' '.join(stuttered_words)
        
        # Only test if we actually created stutters
        assume(len(stuttered_words) > len(words))
        
        segment = SpeechSegment(
            text=stuttered_text,
            confidence=0.8,
            start_time=0.0,
            end_time=2.0,
            silence_after=0.5
        )
        
        accumulator = BufferedQueryAccumulator(normalization_enabled=True)
        
        async def run_test():
            result = await accumulator.add_segment(segment)
            
            # Property: Normalized text should be shorter than original
            normalized_text = result.text
            assert len(normalized_text.split()) <= len(stuttered_text.split())
            
            # Property: Essential content should be preserved
            original_unique_words = set(words)
            normalized_words = set(normalized_text.lower().split())
            
            # Most original words should still be present (allowing for some normalization)
            preserved_count = sum(1 for word in original_unique_words if word.lower() in normalized_words)
            assert preserved_count >= len(original_unique_words) * 0.7  # At least 70% preserved
        
        asyncio.run(run_test())

    # Property 4: Buffer timeout handling
    @given(st.floats(min_value=30.1, max_value=60.0))
    @settings(max_examples=20, deadline=5000)
    def test_property_4_buffer_timeout_handling(self, total_duration: float):
        """
        **Property 4: Buffer timeout handling**
        *For any* accumulated query exceeding 30 seconds of total speech duration, 
        the Query_Accumulator should force processing and return a timeout status
        **Validates: Requirements 1.4**
        **Feature: voice-robustness-session-memory, Property 4: Buffer timeout handling**
        """
        accumulator = BufferedQueryAccumulator(max_buffer_duration=30.0)
        
        async def run_test():
            current_time = 0.0
            
            # Add segments until we exceed the timeout
            while current_time < total_duration:
                segment_duration = min(5.0, total_duration - current_time)
                
                segment = SpeechSegment(
                    text=f"segment at {current_time}",
                    confidence=0.8,
                    start_time=current_time,
                    end_time=current_time + segment_duration,
                    silence_after=0.1
                )
                
                result = await accumulator.add_segment(segment)
                current_time += segment_duration + 0.1
                
                # Property: Once timeout is exceeded, status should be TIMEOUT
                if result.total_duration > 30.0:
                    assert result.status == QueryStatus.TIMEOUT
                    break
            
            # Property: Final result should have TIMEOUT status
            assert result.status == QueryStatus.TIMEOUT
            
            # Property: Total duration should exceed the limit
            assert result.total_duration > 30.0
        
        asyncio.run(run_test())

    # Property 5: Rolling buffer maintenance
    @given(st.integers(min_value=15, max_value=50))
    @settings(max_examples=20, deadline=5000)
    def test_property_5_rolling_buffer_maintenance(self, num_segments: int):
        """
        **Property 5: Rolling buffer maintenance**
        *For any* sequence of speech segments, the Query_Accumulator should maintain 
        a rolling buffer containing only the last 45 seconds of speech
        **Validates: Requirements 1.5**
        **Feature: voice-robustness-session-memory, Property 5: Rolling buffer maintenance**
        """
        rolling_buffer_size = 10  # segments
        accumulator = BufferedQueryAccumulator(
            rolling_buffer_size=rolling_buffer_size,
            max_buffer_duration=1000.0  # Large timeout to avoid interference
        )
        
        async def run_test():
            segments = []
            current_time = 0.0
            
            for i in range(num_segments):
                segment = SpeechSegment(
                    text=f"segment {i}",
                    confidence=0.8,
                    start_time=current_time,
                    end_time=current_time + 1.0,
                    silence_after=0.1
                )
                
                segments.append(segment)
                await accumulator.add_segment(segment)
                current_time += 1.1
                
                # Property: Rolling buffer should not exceed maximum size
                rolling_buffer = accumulator.get_rolling_buffer()
                assert len(rolling_buffer) <= rolling_buffer_size
                
                # Property: Rolling buffer should contain most recent segments
                if len(segments) > rolling_buffer_size:
                    expected_segments = segments[-rolling_buffer_size:]
                    assert len(rolling_buffer) == rolling_buffer_size
                    
                    # Check that rolling buffer contains the most recent segments
                    for j, expected_seg in enumerate(expected_segments):
                        assert rolling_buffer[j].text == expected_seg.text
        
        asyncio.run(run_test())

    # Additional property: Confidence filtering
    @given(st.floats(min_value=0.0, max_value=0.5))
    @settings(max_examples=30, deadline=5000)
    def test_property_confidence_filtering(self, low_confidence: float):
        """
        Property: Low confidence segments should be filtered out.
        """
        accumulator = BufferedQueryAccumulator(min_confidence=0.6)
        
        segment = SpeechSegment(
            text="low confidence text",
            confidence=low_confidence,
            start_time=0.0,
            end_time=1.0,
            silence_after=0.5
        )
        
        async def run_test():
            result = await accumulator.add_segment(segment)
            
            # Property: Low confidence segments should not be included
            assert result.segment_count == 0
            assert result.text == ""
        
        asyncio.run(run_test())

    # Additional property: Reset behavior
    def test_property_reset_behavior(self):
        """
        Property: Reset should clear all accumulator state.
        """
        accumulator = BufferedQueryAccumulator()
        
        async def run_test():
            # Add some segments
            segment = SpeechSegment(
                text="test segment",
                confidence=0.8,
                start_time=0.0,
                end_time=1.0,
                silence_after=0.5
            )
            
            await accumulator.add_segment(segment)
            
            # Verify state exists
            current_query = accumulator.get_current_query()
            assert current_query is not None
            assert current_query.segment_count > 0
            
            # Reset
            accumulator.reset()
            
            # Property: State should be cleared
            current_query = accumulator.get_current_query()
            assert current_query is None
            
            # Property: Rolling buffer should be preserved (for context)
            rolling_buffer = accumulator.get_rolling_buffer()
            assert len(rolling_buffer) > 0  # Rolling buffer preserved across resets
        
        asyncio.run(run_test())


class QueryAccumulationStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for query accumulation.
    
    This tests the accumulator through sequences of operations to ensure
    state transitions are correct and invariants are maintained.
    """
    
    def __init__(self):
        super().__init__()
        self.accumulator = BufferedQueryAccumulator()
        self.added_segments = []
    
    segments = Bundle('segments')
    
    @rule(target=segments)
    def add_segment(self):
        """Add a speech segment to the accumulator."""
        segment = SpeechSegment(
            text=f"segment {len(self.added_segments)}",
            confidence=0.8,
            start_time=len(self.added_segments) * 1.1,
            end_time=(len(self.added_segments) + 1) * 1.1,
            silence_after=0.1
        )
        
        async def run():
            result = await self.accumulator.add_segment(segment)
            self.added_segments.append(segment)
            return result
        
        return asyncio.run(run())
    
    @rule()
    def reset_accumulator(self):
        """Reset the accumulator state."""
        self.accumulator.reset()
        self.added_segments.clear()
    
    @rule()
    def force_completion(self):
        """Force completion of current query."""
        async def run():
            return await self.accumulator.force_completion()
        
        result = asyncio.run(run())
        if result:
            self.added_segments.clear()  # Completion clears state
    
    @invariant()
    def segment_count_consistency(self):
        """Invariant: Current query segment count should match added segments."""
        current_query = self.accumulator.get_current_query()
        if current_query:
            # Segment count should not exceed added segments
            assert current_query.segment_count <= len(self.added_segments)
    
    @invariant()
    def rolling_buffer_size_limit(self):
        """Invariant: Rolling buffer should not exceed maximum size."""
        rolling_buffer = self.accumulator.get_rolling_buffer()
        assert len(rolling_buffer) <= 10  # Default rolling buffer size
    
    @invariant()
    def confidence_consistency(self):
        """Invariant: Accumulated query confidence should be reasonable."""
        current_query = self.accumulator.get_current_query()
        if current_query and current_query.segment_count > 0:
            assert 0.0 <= current_query.confidence <= 1.0


# Test class for running the state machine
TestQueryAccumulationStateMachine = QueryAccumulationStateMachine.TestCase


if __name__ == "__main__":
    # Run property tests
    pytest.main([__file__, "-v", "--tb=short"])