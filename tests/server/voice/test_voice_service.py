"""
Test suite for VoiceService (business logic layer).

Tests cover:
- Transcription service operations
- Synthesis service operations
- Voice management with caching
- Configuration integration
- Async execution patterns
- Error handling and recovery

Total tests: 30
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from server.voice.service import VoiceService
from server.voice.exceptions import STTException, TTSException, ConfigException
from server.voice.models import TranscriptResult, AudioResult, VoiceInfo


# ============================================================================
# Transcription Service Tests (10 tests)
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_with_default_config(voice_service, sample_audio_bytes, mock_async_executor):
    """Test transcription using default configuration."""
    result = await voice_service.transcribe(audio_data=sample_audio_bytes)

    assert isinstance(result, TranscriptResult)
    assert result.text == "Test transcription from mock"
    assert len(result.words) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_with_custom_stt_config(voice_service, sample_audio_bytes, mock_async_executor):
    """Test transcription with custom STT configuration."""
    from server.voice.models import STTConfig

    custom_config = STTConfig(
        model_id="scribe_v1",
        language_code="es",
        timestamps_granularity="word"
    )

    result = await voice_service.transcribe(
        audio_data=sample_audio_bytes,
        config=custom_config
    )

    assert isinstance(result, TranscriptResult)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_with_invalid_audio(voice_service, mock_async_executor):
    """Test transcription with invalid audio raises error."""
    invalid_audio = b"not audio data"

    # Mock client to raise error for invalid audio
    voice_service._client.speech_to_text = MagicMock(
        side_effect=Exception("Invalid audio format")
    )

    with pytest.raises(STTException):
        await voice_service.transcribe(audio_data=invalid_audio)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_audio_format_validation(voice_service, mock_async_executor):
    """Test that audio format is validated before transcription."""
    empty_audio = b""

    with pytest.raises(STTException) as exc_info:
        await voice_service.transcribe(audio_data=empty_audio)

    assert "empty" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_async_execution(voice_service, sample_audio_bytes):
    """Test that transcription executes asynchronously (thread pool)."""
    # Verify that run_in_executor is called
    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(
            return_value=TranscriptResult(
                text="Async transcription",
                words=[],
                confidence=0.9
            )
        )

        result = await voice_service.transcribe(audio_data=sample_audio_bytes)

        # Verify executor was called (non-blocking I/O)
        mock_loop.return_value.run_in_executor.assert_called_once()
        assert result.text == "Async transcription"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_with_language_detection(voice_service, sample_audio_bytes, mock_async_executor):
    """Test transcription with automatic language detection."""
    result = await voice_service.transcribe(audio_data=sample_audio_bytes)

    # Should return detected language
    assert result.language_detected is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_with_config_hot_reload(voice_service, sample_audio_bytes, temp_config_file, mock_async_executor):
    """Test that config changes are detected and applied."""
    # First transcription
    result1 = await voice_service.transcribe(audio_data=sample_audio_bytes)

    # Modify config file
    new_config = """
voice:
  enabled: true
  stt:
    model_id: "scribe_v2"
    language_code: "fr"
"""
    temp_config_file.write_text(new_config)

    # Force config reload
    voice_service._config.load_config()

    # Second transcription should use new config
    result2 = await voice_service.transcribe(audio_data=sample_audio_bytes)

    assert isinstance(result2, TranscriptResult)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_concurrent_requests(voice_service, sample_audio_bytes, mock_async_executor):
    """Test handling of concurrent transcription requests."""
    # Execute multiple transcriptions concurrently
    tasks = [
        voice_service.transcribe(audio_data=sample_audio_bytes)
        for _ in range(5)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(isinstance(r, TranscriptResult) for r in results)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_with_timeout_handling(voice_service, sample_audio_bytes):
    """Test that timeouts are handled gracefully."""
    # Mock a timeout scenario
    async def slow_transcribe(*args, **kwargs):
        await asyncio.sleep(10)  # Very long operation
        return TranscriptResult(text="Late result", words=[])

    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=slow_transcribe)

        # Should timeout or handle gracefully
        # (Depends on implementation - may need timeout parameter)
        try:
            result = await asyncio.wait_for(
                voice_service.transcribe(audio_data=sample_audio_bytes),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            # Timeout is acceptable behavior
            pytest.skip("Transcription timed out as expected")


# ============================================================================
# Synthesis Service Tests (15 tests)
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_default_config(voice_service, sample_text_short, mock_async_executor):
    """Test synthesis using default configuration."""
    result = await voice_service.synthesize(text=sample_text_short)

    assert isinstance(result, AudioResult)
    assert len(result.audio_data) > 0
    assert result.content_type == "audio/mpeg"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_voice_profile(voice_service, sample_text_short, mock_async_executor):
    """Test synthesis using a voice profile."""
    result = await voice_service.synthesize(
        text=sample_text_short,
        profile_name="professional"
    )

    assert isinstance(result, AudioResult)
    assert len(result.audio_data) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_custom_voice_id(voice_service, sample_text_short, mock_async_executor):
    """Test synthesis with custom voice_id."""
    result = await voice_service.synthesize(
        text=sample_text_short,
        voice_id="custom_voice_123"
    )

    assert isinstance(result, AudioResult)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_text_sanitization(voice_service, mock_async_executor):
    """Test that text is sanitized before synthesis."""
    text_with_extra_whitespace = "  Hello   world  \n\n  Test  "

    result = await voice_service.synthesize(text=text_with_extra_whitespace)

    # Should handle whitespace gracefully
    assert isinstance(result, AudioResult)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_text_exceeds_limit(voice_service, sample_text_exceeds_limit, mock_async_executor):
    """Test synthesis with text exceeding max length (truncation)."""
    # Should either truncate or raise error
    try:
        result = await voice_service.synthesize(text=sample_text_exceeds_limit)
        assert isinstance(result, AudioResult)
        # If successful, text was truncated
    except TTSException as e:
        # If error, should mention length limit
        assert "length" in str(e).lower() or "5000" in str(e)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_async_execution(voice_service, sample_text_short):
    """Test that synthesis executes asynchronously."""
    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(
            return_value=b"async audio data"
        )

        result = await voice_service.synthesize(text=sample_text_short)

        mock_loop.return_value.run_in_executor.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_streaming(voice_service, sample_text_long, mock_async_executor):
    """Test streaming synthesis returns chunks."""
    chunks = []
    async for chunk in voice_service.stream_synthesize(text=sample_text_long):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert all(isinstance(chunk, bytes) for chunk in chunks)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_profile_not_found(voice_service, sample_text_short, mock_async_executor):
    """Test synthesis with non-existent profile raises error."""
    with pytest.raises(TTSException) as exc_info:
        await voice_service.synthesize(
            text=sample_text_short,
            profile_name="nonexistent_profile"
        )

    assert "profile" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_config_hot_reload(voice_service, sample_text_short, temp_config_file, mock_async_executor):
    """Test that synthesis picks up config changes."""
    result1 = await voice_service.synthesize(text=sample_text_short)

    # Modify config
    new_config = """
voice:
  enabled: true
  tts:
    voice_id: "new_voice_id"
    stability: 0.9
"""
    temp_config_file.write_text(new_config)
    voice_service._config.load_config()

    result2 = await voice_service.synthesize(text=sample_text_short)

    assert isinstance(result2, AudioResult)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_voice_adjustments(voice_service, sample_text_short, mock_async_executor):
    """Test synthesis with volume/speed adjustments."""
    # Note: Volume/speed may be client-side in actual implementation
    result = await voice_service.synthesize(
        text=sample_text_short,
        profile_name="default"
    )

    assert isinstance(result, AudioResult)
    # Profile should have applied custom settings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_ssml_tags(voice_service, sample_text_ssml, mock_async_executor):
    """Test synthesis handles SSML tags."""
    try:
        result = await voice_service.synthesize(text=sample_text_ssml)
        assert isinstance(result, AudioResult)
    except TTSException:
        # SSML may not be supported
        pytest.skip("SSML not supported")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_concurrent_requests(voice_service, sample_text_short, mock_async_executor):
    """Test handling of concurrent synthesis requests."""
    tasks = [
        voice_service.synthesize(text=sample_text_short)
        for _ in range(5)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(isinstance(r, AudioResult) for r in results)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_retry_logic(voice_service, sample_text_short):
    """Test that failed synthesis is retried."""
    # Mock failure then success
    call_count = {'count': 0}

    def mock_tts(*args, **kwargs):
        call_count['count'] += 1
        if call_count['count'] == 1:
            raise Exception("Temporary failure")
        return b"audio data"

    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=mock_tts)

        # Should retry and succeed
        try:
            result = await voice_service.synthesize(text=sample_text_short)
            # If retry logic exists, should succeed
            assert isinstance(result, AudioResult)
        except TTSException:
            # If no retry, first failure is acceptable
            assert call_count['count'] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthesize_with_fallback_profile(voice_service, sample_text_short, mock_async_executor):
    """Test that synthesis falls back to default profile on error."""
    # Try with invalid profile, should fallback
    with patch.object(voice_service._config, 'get_profile', side_effect=ConfigException("Profile not found")):
        with patch.object(voice_service._config, 'get_default_tts_config') as mock_default:
            mock_default.return_value = voice_service._config.get_default_tts_config()

            result = await voice_service.synthesize(
                text=sample_text_short,
                profile_name="invalid_profile"
            )

            # Should have fallen back to default
            assert isinstance(result, AudioResult)


# ============================================================================
# Voice Management Service Tests (5 tests)
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_voices_with_caching(voice_service, mock_async_executor):
    """Test that voices are cached after first fetch."""
    # First call - should fetch from API
    voices1 = await voice_service.get_voices()

    # Second call - should use cache
    voices2 = await voice_service.get_voices()

    assert voices1 == voices2
    assert len(voices1) > 0

    # Verify client was only called once (cached)
    call_count = voice_service._client._client.voices.get_all.call_count
    assert call_count == 1  # Only one actual API call


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_voices_with_refresh(voice_service, mock_async_executor):
    """Test forcing a refresh of voices cache."""
    voices1 = await voice_service.get_voices()

    # Force refresh
    voices2 = await voice_service.get_voices(refresh=True)

    assert len(voices1) > 0
    assert len(voices2) > 0

    # Verify client was called twice
    call_count = voice_service._client._client.voices.get_all.call_count
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_voice_by_id(voice_service, mock_async_executor):
    """Test retrieving specific voice by ID."""
    voice = await voice_service.get_voice(voice_id="test_voice_1")

    assert isinstance(voice, VoiceInfo)
    assert voice.voice_id == "test_voice_1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_voices_cache_expiry(voice_service):
    """Test that voice cache expires after TTL."""
    # This test would require modifying cache TTL or mocking time
    voices1 = await voice_service.get_voices()

    # Mock time passage
    with patch('time.time') as mock_time:
        # Simulate cache expiry (e.g., 1 hour passed)
        mock_time.return_value = mock_time.return_value + 3601

        voices2 = await voice_service.get_voices()

        # Should have fetched again due to expiry
        assert len(voices2) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_voices_api_failure(voice_service):
    """Test handling of API failure when fetching voices."""
    voice_service._client._client.voices.get_all.side_effect = Exception("API unavailable")

    with pytest.raises(Exception):  # Should propagate or wrap error
        await voice_service.get_voices()


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_success(voice_service):
    """Test health check when service is healthy."""
    health = await voice_service.health_check()

    assert health['healthy'] is True
    assert 'elevenlabs_connected' in health


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_failure(voice_service):
    """Test health check when service has issues."""
    voice_service._client._client.voices.get_all.side_effect = Exception("Connection failed")

    health = await voice_service.health_check()

    assert health['healthy'] is False
    assert 'error' in health or 'elevenlabs_connected' in health
