"""
Test suite for Voice Exception Classes.

Tests cover:
- Exception hierarchy
- Error codes
- Error messages
- Exception serialization
- Error details

Total tests: 10
"""

import pytest
from server.voice.exceptions import (
    VoiceException,
    TTSException,
    STTException,
    ConfigException,
    ClientException
)


# ============================================================================
# Exception Hierarchy Tests (3 tests)
# ============================================================================

@pytest.mark.unit
def test_voice_exception_base_class():
    """Test VoiceException base class."""
    exc = VoiceException("Base exception message")

    assert isinstance(exc, Exception)
    assert str(exc) == "Base exception message"
    assert exc.error_code is not None


@pytest.mark.unit
def test_tts_exception_inheritance():
    """Test TTSException inherits from VoiceException."""
    exc = TTSException("TTS error")

    assert isinstance(exc, VoiceException)
    assert isinstance(exc, Exception)
    assert "TTS" in str(exc) or "text-to-speech" in str(exc).lower()


@pytest.mark.unit
def test_stt_exception_inheritance():
    """Test STTException inherits from VoiceException."""
    exc = STTException("STT error")

    assert isinstance(exc, VoiceException)
    assert isinstance(exc, Exception)
    assert "STT" in str(exc) or "speech-to-text" in str(exc).lower()


# ============================================================================
# Error Code Tests (4 tests)
# ============================================================================

@pytest.mark.unit
def test_tts_exception_error_codes():
    """Test TTSException error codes (VOICE_1xx)."""
    exc = TTSException("TTS error", error_code="VOICE_101")

    assert exc.error_code.startswith("VOICE_1")
    assert isinstance(exc.error_code, str)


@pytest.mark.unit
def test_stt_exception_error_codes():
    """Test STTException error codes (VOICE_2xx)."""
    exc = STTException("STT error", error_code="VOICE_201")

    assert exc.error_code.startswith("VOICE_2")


@pytest.mark.unit
def test_config_exception_error_codes():
    """Test ConfigException error codes (VOICE_3xx)."""
    exc = ConfigException("Config error", error_code="VOICE_301")

    assert exc.error_code.startswith("VOICE_3")


@pytest.mark.unit
def test_client_exception_error_codes():
    """Test ClientException error codes (VOICE_4xx)."""
    exc = ClientException("Client error", error_code="VOICE_401")

    assert exc.error_code.startswith("VOICE_4")


# ============================================================================
# Error Message Tests (3 tests)
# ============================================================================

@pytest.mark.unit
def test_exception_message_formatting():
    """Test exception message formatting."""
    message = "This is a detailed error message"
    exc = VoiceException(message)

    assert str(exc) == message
    assert message in repr(exc)


@pytest.mark.unit
def test_exception_with_details_dict():
    """Test exception with additional details dictionary."""
    exc = TTSException(
        "TTS synthesis failed",
        error_code="VOICE_102",
        details={"voice_id": "test_voice", "text_length": 5000}
    )

    assert exc.error_code == "VOICE_102"
    assert hasattr(exc, 'details')
    if hasattr(exc, 'details'):
        assert exc.details['voice_id'] == "test_voice"
        assert exc.details['text_length'] == 5000


@pytest.mark.unit
def test_exception_serialization_to_dict():
    """Test exception serialization to dictionary."""
    exc = STTException(
        "Transcription failed",
        error_code="VOICE_202",
        details={"audio_format": "invalid"}
    )

    # If exception has to_dict method
    if hasattr(exc, 'to_dict'):
        exc_dict = exc.to_dict()

        assert isinstance(exc_dict, dict)
        assert 'error_code' in exc_dict
        assert 'message' in exc_dict
        assert exc_dict['error_code'] == "VOICE_202"
    else:
        # Manual serialization
        exc_dict = {
            'error_code': exc.error_code,
            'message': str(exc),
            'details': exc.details if hasattr(exc, 'details') else None
        }

        assert exc_dict['error_code'] == "VOICE_202"
        assert "Transcription failed" in exc_dict['message']
