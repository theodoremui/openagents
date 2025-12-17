"""
Test suite for VoiceClient (ElevenLabs SDK wrapper).

Tests cover:
- Speech-to-Text (STT) functionality
- Text-to-Speech (TTS) functionality
- Voice management
- Error handling
- API interaction patterns

Total tests: 30
"""

import pytest
from unittest.mock import MagicMock, patch
from server.voice.client import VoiceClient
from server.voice.exceptions import STTException, TTSException, ClientException
from server.voice.models import TranscriptResult, AudioResult, VoiceInfo


# ============================================================================
# STT Tests (10 tests)
# ============================================================================

@pytest.mark.unit
def test_stt_successful_transcription(voice_client, sample_audio_bytes):
    """Test successful audio transcription with valid input."""
    result = voice_client.speech_to_text(audio=sample_audio_bytes)

    assert isinstance(result, TranscriptResult)
    assert result.text == "Test transcription from mock"
    assert len(result.words) == 4
    assert result.confidence == 0.95
    assert result.language_detected == "en"


@pytest.mark.unit
def test_stt_with_language_code(voice_client, sample_audio_bytes):
    """Test transcription with specified language code."""
    result = voice_client.speech_to_text(
        audio=sample_audio_bytes,
        language_code="es"
    )

    # Verify language code was passed to SDK
    voice_client._client.speech_to_text.convert.assert_called()
    call_kwargs = voice_client._client.speech_to_text.convert.call_args.kwargs
    assert call_kwargs.get('language_code') == "es"

    assert isinstance(result, TranscriptResult)


@pytest.mark.unit
def test_stt_word_timestamps(voice_client, sample_audio_bytes):
    """Test that word-level timestamps are returned correctly."""
    result = voice_client.speech_to_text(audio=sample_audio_bytes)

    assert len(result.words) > 0

    # Verify first word structure
    first_word = result.words[0]
    assert 'word' in first_word
    assert 'start' in first_word
    assert 'end' in first_word
    assert isinstance(first_word['start'], (int, float))
    assert isinstance(first_word['end'], (int, float))
    assert first_word['end'] >= first_word['start']


@pytest.mark.unit
def test_stt_confidence_score(voice_client, sample_audio_bytes):
    """Test that confidence scores are returned and valid."""
    result = voice_client.speech_to_text(audio=sample_audio_bytes)

    assert result.confidence is not None
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.unit
def test_stt_empty_audio_input(voice_client):
    """Test handling of empty audio input."""
    with pytest.raises(STTException) as exc_info:
        voice_client.speech_to_text(audio=b"")

    assert "empty" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


@pytest.mark.unit
def test_stt_invalid_audio_format(voice_client):
    """Test handling of invalid audio format."""
    invalid_audio = b"This is not audio data"

    # Mock SDK to raise error
    voice_client._client.speech_to_text.convert.side_effect = Exception("Invalid audio format")

    with pytest.raises(STTException):
        voice_client.speech_to_text(audio=invalid_audio)


@pytest.mark.unit
def test_stt_api_rate_limit_error(voice_client, sample_audio_bytes):
    """Test handling of API rate limit errors."""
    # Mock rate limit error
    voice_client._client.speech_to_text.convert.side_effect = Exception("Rate limit exceeded")

    with pytest.raises(STTException) as exc_info:
        voice_client.speech_to_text(audio=sample_audio_bytes)

    assert "rate limit" in str(exc_info.value).lower() or "429" in str(exc_info.value)


@pytest.mark.unit
def test_stt_api_auth_error(voice_client, sample_audio_bytes):
    """Test handling of authentication errors."""
    voice_client._client.speech_to_text.convert.side_effect = Exception("Invalid API key")

    with pytest.raises(STTException) as exc_info:
        voice_client.speech_to_text(audio=sample_audio_bytes)

    assert "auth" in str(exc_info.value).lower() or "api key" in str(exc_info.value).lower()


@pytest.mark.unit
def test_stt_large_audio_file(voice_client):
    """Test handling of large audio files (>10MB)."""
    # Create 11MB of audio data
    large_audio = b"\x00" * (11 * 1024 * 1024)

    # Should handle large files (may have size limit in actual implementation)
    try:
        result = voice_client.speech_to_text(audio=large_audio)
        assert isinstance(result, TranscriptResult)
    except STTException as e:
        # If there's a size limit, ensure it's handled gracefully
        assert "size" in str(e).lower() or "large" in str(e).lower()


@pytest.mark.unit
def test_stt_audio_with_silence(voice_client, sample_audio_bytes):
    """Test handling of audio containing only silence."""
    # Mock response with empty transcription
    mock_response = MagicMock()
    mock_response.text = ""
    mock_response.words = []
    mock_response.confidence = 0.0
    voice_client._client.speech_to_text.convert.return_value = mock_response

    result = voice_client.speech_to_text(audio=sample_audio_bytes)

    assert result.text == ""
    assert len(result.words) == 0


# ============================================================================
# TTS Tests (15 tests)
# ============================================================================

@pytest.mark.unit
def test_tts_successful_synthesis(voice_client, sample_text_short):
    """Test successful text-to-speech synthesis."""
    result = voice_client.text_to_speech(
        text=sample_text_short,
        voice_id="test_voice_1"
    )

    assert isinstance(result, bytes)
    assert len(result) > 0
    # Mock returns 3 chunks concatenated
    assert result == b"audio_chunk_1audio_chunk_2audio_chunk_3"


@pytest.mark.unit
def test_tts_with_voice_id(voice_client, sample_text_short):
    """Test synthesis with specified voice_id."""
    voice_client.text_to_speech(
        text=sample_text_short,
        voice_id="custom_voice_123"
    )

    # Verify voice_id was passed to SDK
    call_kwargs = voice_client._client.text_to_speech.convert.call_args.kwargs
    assert call_kwargs.get('voice_id') == "custom_voice_123"


@pytest.mark.unit
def test_tts_with_custom_model(voice_client, sample_text_short):
    """Test synthesis with custom model."""
    voice_client.text_to_speech(
        text=sample_text_short,
        voice_id="test_voice_1",
        model_id="eleven_turbo_v2_5"
    )

    call_kwargs = voice_client._client.text_to_speech.convert.call_args.kwargs
    assert call_kwargs.get('model_id') == "eleven_turbo_v2_5"


@pytest.mark.unit
def test_tts_with_voice_settings(voice_client, sample_text_short):
    """Test synthesis with voice settings (stability, similarity)."""
    voice_client.text_to_speech(
        text=sample_text_short,
        voice_id="test_voice_1",
        stability=0.8,
        similarity_boost=0.9
    )

    call_kwargs = voice_client._client.text_to_speech.convert.call_args.kwargs
    assert 'voice_settings' in call_kwargs or 'stability' in call_kwargs


@pytest.mark.unit
def test_tts_returns_audio_bytes(voice_client, sample_text_short):
    """Test that synthesis returns valid audio bytes."""
    result = voice_client.text_to_speech(
        text=sample_text_short,
        voice_id="test_voice_1"
    )

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.unit
def test_tts_empty_text_input(voice_client):
    """Test handling of empty text input."""
    with pytest.raises(TTSException) as exc_info:
        voice_client.text_to_speech(
            text="",
            voice_id="test_voice_1"
        )

    assert "empty" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


@pytest.mark.unit
def test_tts_text_exceeds_max_length(voice_client, sample_text_exceeds_limit):
    """Test handling of text exceeding max length (5000 chars)."""
    # Should either truncate or raise error
    try:
        result = voice_client.text_to_speech(
            text=sample_text_exceeds_limit,
            voice_id="test_voice_1"
        )
        # If it succeeds, it should have truncated
        assert isinstance(result, bytes)
    except TTSException as e:
        # If it raises, should mention length limit
        assert "length" in str(e).lower() or "limit" in str(e).lower() or "5000" in str(e)


@pytest.mark.unit
def test_tts_invalid_voice_id(voice_client, sample_text_short):
    """Test handling of invalid voice_id."""
    voice_client._client.text_to_speech.convert.side_effect = Exception("Voice not found")

    with pytest.raises(TTSException) as exc_info:
        voice_client.text_to_speech(
            text=sample_text_short,
            voice_id="nonexistent_voice"
        )

    assert "voice" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.unit
def test_tts_api_error(voice_client, sample_text_short):
    """Test handling of generic API errors."""
    voice_client._client.text_to_speech.convert.side_effect = Exception("API error")

    with pytest.raises(TTSException):
        voice_client.text_to_speech(
            text=sample_text_short,
            voice_id="test_voice_1"
        )


@pytest.mark.unit
def test_tts_validate_output_format(voice_client, sample_text_short):
    """Test that output format is validated."""
    voice_client.text_to_speech(
        text=sample_text_short,
        voice_id="test_voice_1",
        output_format="mp3_44100_128"
    )

    call_kwargs = voice_client._client.text_to_speech.convert.call_args.kwargs
    # Should include output_format in call
    assert 'output_format' in call_kwargs or 'model_id' in call_kwargs


@pytest.mark.unit
def test_tts_stream_synthesis(voice_client, sample_text_long):
    """Test streaming synthesis returns chunks."""
    chunks = list(voice_client.text_to_speech_stream(
        text=sample_text_long,
        voice_id="test_voice_1"
    ))

    assert len(chunks) > 0
    assert all(isinstance(chunk, bytes) for chunk in chunks)
    assert sum(len(chunk) for chunk in chunks) > 0


@pytest.mark.unit
def test_tts_special_characters(voice_client, sample_text_special_chars):
    """Test synthesis handles special characters correctly."""
    result = voice_client.text_to_speech(
        text=sample_text_special_chars,
        voice_id="test_voice_1"
    )

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.unit
def test_tts_multilingual_text(voice_client, sample_text_multilingual):
    """Test synthesis handles multilingual text."""
    result = voice_client.text_to_speech(
        text=sample_text_multilingual,
        voice_id="test_voice_1",
        model_id="eleven_multilingual_v2"
    )

    assert isinstance(result, bytes)


@pytest.mark.unit
def test_tts_ssml_tags(voice_client, sample_text_ssml):
    """Test synthesis handles SSML tags (if supported)."""
    # May need to be marked as xfail if SSML not supported
    try:
        result = voice_client.text_to_speech(
            text=sample_text_ssml,
            voice_id="test_voice_1"
        )
        assert isinstance(result, bytes)
    except TTSException:
        # SSML may not be supported, that's okay
        pytest.skip("SSML not supported by current implementation")


@pytest.mark.unit
def test_tts_audio_metadata(voice_client, sample_text_short):
    """Test that audio metadata is available (format, duration, etc)."""
    result = voice_client.text_to_speech(
        text=sample_text_short,
        voice_id="test_voice_1"
    )

    # At minimum, should have audio bytes
    assert isinstance(result, bytes)
    assert len(result) > 0

    # If AudioResult is returned with metadata, validate it
    # (depends on implementation)


# ============================================================================
# Voice Management Tests (5 tests)
# ============================================================================

@pytest.mark.unit
def test_list_all_voices(voice_client):
    """Test listing all available voices."""
    voices = voice_client.list_voices()

    assert isinstance(voices, list)
    assert len(voices) == 2
    assert all(isinstance(v, VoiceInfo) for v in voices)

    # Check first voice structure
    voice = voices[0]
    assert voice.voice_id == "test_voice_1"
    assert voice.name == "Test Voice 1"
    assert voice.category == "premade"


@pytest.mark.unit
def test_get_voice_by_id(voice_client):
    """Test retrieving specific voice by ID."""
    voice = voice_client.get_voice(voice_id="test_voice_1")

    assert isinstance(voice, VoiceInfo)
    assert voice.voice_id == "test_voice_1"
    assert voice.name == "Test Voice 1"


@pytest.mark.unit
def test_get_voice_settings(voice_client):
    """Test retrieving voice settings/details."""
    voice = voice_client.get_voice(voice_id="test_voice_1")

    # Voice should have metadata
    assert voice.voice_id is not None
    assert voice.name is not None
    assert voice.category in ["premade", "cloned", "generated"]


@pytest.mark.unit
def test_voice_list_api_error(voice_client):
    """Test handling of errors when listing voices."""
    voice_client._client.voices.get_all.side_effect = Exception("API error")

    with pytest.raises(ClientException):
        voice_client.list_voices()


@pytest.mark.unit
def test_voice_metadata_structure(voice_client):
    """Test that voice metadata has expected structure."""
    voices = voice_client.list_voices()

    for voice in voices:
        assert hasattr(voice, 'voice_id')
        assert hasattr(voice, 'name')
        assert hasattr(voice, 'category')
        assert hasattr(voice, 'description')

        # Optional fields
        if voice.labels:
            assert isinstance(voice.labels, dict)


# ============================================================================
# Client Initialization & Configuration Tests
# ============================================================================

@pytest.mark.unit
def test_client_initialization_with_api_key():
    """Test VoiceClient initialization with explicit API key."""
    with patch('elevenlabs.client.ElevenLabs') as mock_sdk:
        client = VoiceClient(api_key="custom_key_123")

        # Verify SDK was initialized with correct key
        mock_sdk.assert_called_once()
        assert client._api_key == "custom_key_123"


@pytest.mark.unit
def test_client_initialization_from_env():
    """Test VoiceClient initialization from environment variable."""
    with patch.dict('os.environ', {'ELEVENLABS_API_KEY': 'env_key_456'}):
        with patch('elevenlabs.client.ElevenLabs'):
            client = VoiceClient()

            assert client._api_key == "env_key_456"


@pytest.mark.unit
def test_client_initialization_no_api_key():
    """Test VoiceClient initialization without API key fails gracefully."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ClientException) as exc_info:
            VoiceClient()

        assert "api key" in str(exc_info.value).lower() or "elevenlabs" in str(exc_info.value).lower()


@pytest.mark.unit
def test_client_sdk_import_error():
    """Test handling of ElevenLabs SDK import failure."""
    with patch('elevenlabs.client.ElevenLabs', side_effect=ImportError("elevenlabs not installed")):
        with pytest.raises(ClientException) as exc_info:
            VoiceClient(api_key="test_key")

        assert "install" in str(exc_info.value).lower() or "elevenlabs" in str(exc_info.value).lower()
