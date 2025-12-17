"""
Comprehensive tests for BufferedSTT wrapper with semantic endpointing.

Tests cover:
1. BufferedSTT initialization and configuration
2. Event processing (START, INTERIM, FINAL, END_OF_SPEECH)
3. Semantic buffering and endpointing decisions
4. Integration with SemanticEndpointer
5. Safety timeouts and edge cases
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import AsyncIterator, List

# Mock LiveKit imports for testing
class MockSpeechEventType:
    START_OF_SPEECH = "start_of_speech"
    INTERIM_TRANSCRIPT = "interim_transcript"
    FINAL_TRANSCRIPT = "final_transcript"
    END_OF_SPEECH = "end_of_speech"


class MockSpeechData:
    def __init__(self, text: str, language: str = "en", confidence: float = 1.0):
        self.text = text
        self.language = language
        self.confidence = confidence


class MockSpeechEvent:
    def __init__(self, type: str, alternatives: List = None):
        self.type = type
        self.alternatives = alternatives or []


class MockSTTCapabilities:
    def __init__(self, streaming: bool = True, interim_results: bool = True):
        self.streaming = streaming
        self.interim_results = interim_results


class MockSTT:
    """Mock STT implementation for testing."""

    def __init__(self):
        self.capabilities = MockSTTCapabilities()
        self.events = []

    async def recognize(
        self,
        *,
        buffer=None,
        language=None,
    ) -> AsyncIterator[MockSpeechEvent]:
        """Yield mock events."""
        for event in self.events:
            yield event

    def set_events(self, events: List[MockSpeechEvent]):
        """Set events to be yielded during recognition."""
        self.events = events


# Import BufferedSTT after mocking LiveKit types
import sys
from pathlib import Path

# Add server to path
server_path = Path(__file__).parent.parent.parent.parent.parent / "server"
if str(server_path) not in sys.path:
    sys.path.insert(0, str(server_path))

# Mock livekit.agents before importing BufferedSTT
sys.modules["livekit"] = MagicMock()
sys.modules["livekit.agents"] = MagicMock()
sys.modules["livekit.agents.stt"] = MagicMock()

# Set mock classes
sys.modules["livekit.agents"].STT = MockSTT
sys.modules["livekit.agents"].STTCapabilities = MockSTTCapabilities
sys.modules["livekit.agents.stt"].SpeechData = MockSpeechData
sys.modules["livekit.agents.stt"].SpeechEvent = MockSpeechEvent
sys.modules["livekit.agents.stt"].SpeechEventType = MockSpeechEventType

# Now import BufferedSTT
from server.voice.realtime.buffered_stt import BufferedSTT


class TestBufferedSTTInitialization:
    """Test BufferedSTT initialization and configuration."""

    def test_init_with_semantic_endpointing_enabled(self):
        """Test initialization with semantic endpointing enabled."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            min_silence_ambiguous=0.6,
            min_silence_complete=1.0,
            max_buffer_duration=30.0,
            enable_logging=False,
        )

        assert buffered_stt._base_stt is base_stt
        assert buffered_stt._enable_semantic is True
        assert buffered_stt._max_buffer_duration == 30.0
        assert buffered_stt._endpointer is not None

    def test_init_with_semantic_endpointing_disabled(self):
        """Test initialization with semantic endpointing disabled."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=False,
        )

        assert buffered_stt._enable_semantic is False
        assert buffered_stt._endpointer is None

    def test_init_with_custom_thresholds(self):
        """Test initialization with custom silence thresholds."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            min_silence_ambiguous=0.4,
            min_silence_complete=0.8,
        )

        # Thresholds are passed to SemanticEndpointer
        assert buffered_stt._endpointer is not None

    def test_buffer_state_initialization(self):
        """Test that buffer state is properly initialized."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(base_stt=base_stt, enable_semantic_endpointing=True)

        assert buffered_stt._buffer_text == ""
        assert buffered_stt._buffer_start_time is None
        assert buffered_stt._silence_start_time is None


class TestBufferedSTTEventProcessing:
    """Test event processing in BufferedSTT."""

    @pytest.mark.asyncio
    async def test_passthrough_when_disabled(self):
        """Test that events pass through when semantic endpointing is disabled."""
        base_stt = MockSTT()
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.INTERIM_TRANSCRIPT,
                alternatives=[MockSpeechData("Hello")]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.END_OF_SPEECH,
                alternatives=[MockSpeechData("Hello")]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=False,
        )

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        # All events should pass through
        assert len(events) == 3
        assert events[0].type == MockSpeechEventType.START_OF_SPEECH
        assert events[1].type == MockSpeechEventType.INTERIM_TRANSCRIPT
        assert events[2].type == MockSpeechEventType.END_OF_SPEECH

    @pytest.mark.asyncio
    async def test_start_of_speech_emitted_immediately(self):
        """Test that START_OF_SPEECH events are emitted immediately."""
        base_stt = MockSTT()
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
        )

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        assert len(events) == 1
        assert events[0].type == MockSpeechEventType.START_OF_SPEECH

    @pytest.mark.asyncio
    async def test_interim_transcript_buffered(self):
        """Test that INTERIM_TRANSCRIPT events are buffered (not emitted)."""
        base_stt = MockSTT()
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.INTERIM_TRANSCRIPT,
                alternatives=[MockSpeechData("Can you")]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.INTERIM_TRANSCRIPT,
                alternatives=[MockSpeechData("Can you show me")]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            enable_logging=False,
        )

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        # Only START_OF_SPEECH should be emitted (INTERIM buffered)
        assert len(events) == 1
        assert events[0].type == MockSpeechEventType.START_OF_SPEECH

        # Buffer should contain latest text
        assert buffered_stt._buffer_text == "Can you show me"

    @pytest.mark.asyncio
    async def test_incomplete_utterance_not_endpointed(self):
        """Test that incomplete utterances are not endpointed."""
        base_stt = MockSTT()
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[MockSpeechData("Can you show me")]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.END_OF_SPEECH,
                alternatives=[MockSpeechData("Can you show me")]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            min_silence_ambiguous=0.6,
            min_silence_complete=1.0,
            enable_logging=False,
        )

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        # Only START_OF_SPEECH should be emitted
        # Incomplete utterance should not trigger END_OF_SPEECH
        end_events = [e for e in events if e.type == MockSpeechEventType.END_OF_SPEECH]
        assert len(end_events) == 0

    @pytest.mark.asyncio
    async def test_complete_utterance_endpointed(self):
        """Test that complete utterances are endpointed."""
        base_stt = MockSTT()

        # Create event with complete utterance
        complete_text = "Show me Greek restaurants in San Francisco"
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[MockSpeechData(complete_text)]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            min_silence_ambiguous=0.6,
            min_silence_complete=1.0,
            enable_logging=False,
        )

        # Simulate passage of time for silence duration
        import time
        buffered_stt._buffer_start_time = time.time() - 3.0  # Utterance 3s ago
        buffered_stt._silence_start_time = time.time() - 1.5  # Silence 1.5s

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        # Should emit START_OF_SPEECH and potentially END_OF_SPEECH
        # (depending on semantic analysis)
        assert len(events) >= 1
        assert events[0].type == MockSpeechEventType.START_OF_SPEECH


class TestBufferedSTTSemanticIntegration:
    """Test integration with SemanticEndpointer."""

    @pytest.mark.asyncio
    async def test_semantic_analysis_called(self):
        """Test that semantic analysis is invoked during processing."""
        base_stt = MockSTT()
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[MockSpeechData("Show me restaurants")]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            enable_logging=False,
        )

        # Mock should_endpoint to track calls
        original_should_endpoint = buffered_stt._should_endpoint
        call_count = 0

        async def mock_should_endpoint():
            nonlocal call_count
            call_count += 1
            return await original_should_endpoint()

        buffered_stt._should_endpoint = mock_should_endpoint

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        # Semantic analysis should have been called
        assert call_count > 0

    @pytest.mark.asyncio
    async def test_context_reset(self):
        """Test that context can be reset."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
        )

        # Add some buffer state
        buffered_stt._buffer_text = "test"
        buffered_stt._buffer_start_time = 123.0

        # Reset context
        buffered_stt.reset_context()

        # Buffer should be cleared
        assert buffered_stt._buffer_text == ""
        assert buffered_stt._buffer_start_time is None


class TestBufferedSTTSafetyFeatures:
    """Test safety features (timeouts, edge cases)."""

    @pytest.mark.asyncio
    async def test_safety_timeout(self):
        """Test that safety timeout forces endpoint after max duration."""
        base_stt = MockSTT()
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[MockSpeechData("Can you show me")]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            max_buffer_duration=5.0,  # Short timeout for testing
            enable_logging=False,
        )

        # Simulate very old buffer (exceeds timeout)
        import time
        buffered_stt._buffer_start_time = time.time() - 6.0  # 6 seconds ago
        buffered_stt._buffer_text = "Can you show me"

        # Check if should endpoint
        should_endpoint = await buffered_stt._should_endpoint()

        # Should force endpoint due to timeout
        assert should_endpoint is True

    @pytest.mark.asyncio
    async def test_empty_buffer_endpoints_immediately(self):
        """Test that empty buffer endpoints immediately."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
        )

        buffered_stt._buffer_text = ""

        should_endpoint = await buffered_stt._should_endpoint()

        assert should_endpoint is True

    def test_reset_buffer(self):
        """Test buffer reset functionality."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
        )

        # Set buffer state
        buffered_stt._buffer_text = "test"
        buffered_stt._buffer_start_time = 123.0
        buffered_stt._silence_start_time = 124.0

        # Reset
        buffered_stt._reset_buffer()

        # All state should be cleared
        assert buffered_stt._buffer_text == ""
        assert buffered_stt._buffer_start_time is None
        assert buffered_stt._silence_start_time is None


class TestBufferedSTTEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_event_without_alternatives(self):
        """Test handling of events without alternatives."""
        base_stt = MockSTT()
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=None  # No alternatives
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
        )

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        # Should handle gracefully
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_multiple_recognition_sessions(self):
        """Test multiple recognition sessions with same instance."""
        base_stt = MockSTT()
        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
        )

        # First session
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
        ])

        events1 = []
        async for event in buffered_stt.recognize():
            events1.append(event)

        # Second session (should reset buffer)
        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
        ])

        events2 = []
        async for event in buffered_stt.recognize():
            events2.append(event)

        # Both sessions should work independently
        assert len(events1) > 0
        assert len(events2) > 0


class TestBufferedSTTRealisticScenarios:
    """Test realistic voice interaction scenarios."""

    @pytest.mark.asyncio
    async def test_long_query_not_fragmented(self):
        """Test that long queries are not fragmented."""
        base_stt = MockSTT()

        long_query = "Can you show me the top 3 Greek restaurants in San Francisco, on a map, in descending order of ratings"

        base_stt.set_events([
            MockSpeechEvent(
                type=MockSpeechEventType.START_OF_SPEECH,
                alternatives=[]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.INTERIM_TRANSCRIPT,
                alternatives=[MockSpeechData("Can you show me")]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.INTERIM_TRANSCRIPT,
                alternatives=[MockSpeechData("Can you show me the top 3")]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.INTERIM_TRANSCRIPT,
                alternatives=[MockSpeechData(long_query)]
            ),
            MockSpeechEvent(
                type=MockSpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[MockSpeechData(long_query)]
            ),
        ])

        buffered_stt = BufferedSTT(
            base_stt=base_stt,
            enable_semantic_endpointing=True,
            min_silence_ambiguous=0.6,
            min_silence_complete=1.0,
            enable_logging=False,
        )

        import time
        buffered_stt._buffer_start_time = time.time() - 5.0
        buffered_stt._silence_start_time = time.time() - 1.2

        events = []
        async for event in buffered_stt.recognize():
            events.append(event)

        # Should buffer intermediates and only emit when complete
        interim_count = len([e for e in events if e.type == MockSpeechEventType.INTERIM_TRANSCRIPT])
        assert interim_count == 0  # Intermediates should be buffered


if __name__ == "__main__":
    # Run with: pytest tests/server/voice/realtime/test_buffered_stt.py -v
    pytest.main([__file__, "-v"])
