"""
Shared fixtures for voice tests.

Provides reusable fixtures for:
- Mock ElevenLabs client
- VoiceClient instances
- VoiceConfigManager instances
- VoiceService instances
- Sample audio and text data
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import tempfile
import os


@pytest.fixture
def mock_elevenlabs_client():
    """
    Mock ElevenLabs SDK client.

    Provides mock implementations for:
    - speech_to_text.convert (STT)
    - text_to_speech.convert (TTS)
    - voices.get_all (voice list)
    - voices.get (single voice)
    """
    with patch('elevenlabs.client.ElevenLabs') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Mock STT response
        stt_response = MagicMock()
        stt_response.text = "Test transcription from mock"
        stt_response.words = [
            {"word": "Test", "start": 0.0, "end": 0.4},
            {"word": "transcription", "start": 0.4, "end": 1.2},
            {"word": "from", "start": 1.2, "end": 1.4},
            {"word": "mock", "start": 1.4, "end": 1.8},
        ]
        stt_response.confidence = 0.95
        stt_response.language_code = "en"
        mock_instance.speech_to_text.convert.return_value = stt_response

        # Mock TTS response (streaming chunks)
        def tts_generator():
            yield b"audio_chunk_1"
            yield b"audio_chunk_2"
            yield b"audio_chunk_3"

        mock_instance.text_to_speech.convert.return_value = tts_generator()

        # Mock voices list response
        mock_voice_1 = MagicMock()
        mock_voice_1.voice_id = "test_voice_1"
        mock_voice_1.name = "Test Voice 1"
        mock_voice_1.category = "premade"
        mock_voice_1.description = "A test voice for unit testing"
        mock_voice_1.labels = {"accent": "american", "age": "middle-aged", "gender": "female"}
        mock_voice_1.samples = []
        mock_voice_1.settings = None

        mock_voice_2 = MagicMock()
        mock_voice_2.voice_id = "test_voice_2"
        mock_voice_2.name = "Test Voice 2"
        mock_voice_2.category = "cloned"
        mock_voice_2.description = "Another test voice"
        mock_voice_2.labels = {"accent": "british", "age": "young", "gender": "male"}
        mock_voice_2.samples = []
        mock_voice_2.settings = None

        voices_response = MagicMock()
        voices_response.voices = [mock_voice_1, mock_voice_2]
        mock_instance.voices.get_all.return_value = voices_response

        # Mock single voice response
        mock_instance.voices.get.return_value = mock_voice_1

        yield mock_instance


@pytest.fixture
def voice_client(mock_elevenlabs_client):
    """
    Create VoiceClient instance with mocked ElevenLabs SDK.

    Returns:
        VoiceClient instance ready for testing
    """
    from server.voice.client import VoiceClient

    return VoiceClient(api_key="test_api_key_12345")


@pytest.fixture
def temp_config_file(tmp_path):
    """
    Create temporary voice configuration file.

    Args:
        tmp_path: pytest temporary directory

    Returns:
        Path to temporary config file
    """
    config_file = tmp_path / "voice_config.yaml"
    config_content = """
voice:
  enabled: true

  tts:
    voice_id: "JBFqnCBsd6RMkjVDRZzb"
    model_id: "eleven_multilingual_v2"
    output_format: "mp3_44100_128"
    stability: 0.5
    similarity_boost: 0.75

  stt:
    model_id: "scribe_v1"
    language_code: null
    timestamps_granularity: "word"

  voice_profiles:
    default:
      stability: 0.5
      similarity_boost: 0.75
      style: 0.0
      use_speaker_boost: true

    professional:
      stability: 0.4
      similarity_boost: 0.8
      style: 0.0
      use_speaker_boost: true

    conversational:
      stability: 0.6
      similarity_boost: 0.7
      style: 0.3
      use_speaker_boost: true

  default_profile: "default"
"""
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def voice_config_manager(temp_config_file):
    """
    Create VoiceConfigManager with temporary config file.

    Args:
        temp_config_file: Temporary config file path

    Returns:
        VoiceConfigManager instance
    """
    from server.voice.config import VoiceConfigManager

    return VoiceConfigManager(config_path=temp_config_file)


@pytest.fixture
def voice_service(voice_client, voice_config_manager):
    """
    Create VoiceService with mocked dependencies.

    Args:
        voice_client: Mocked VoiceClient
        voice_config_manager: VoiceConfigManager with temp config

    Returns:
        VoiceService instance ready for testing
    """
    from server.voice.service import VoiceService

    return VoiceService(
        client=voice_client,
        config_manager=voice_config_manager,
    )


@pytest.fixture
def sample_audio_bytes():
    """
    Generate sample audio bytes in WAV format.

    Creates a minimal valid WAV file for testing.

    Returns:
        bytes: Valid WAV audio data
    """
    # Minimal WAV header + silent audio data
    wav_header = (
        b"RIFF"
        + b"\x24\x08\x00\x00"  # Chunk size (2084 bytes)
        + b"WAVE"
        + b"fmt "
        + b"\x10\x00\x00\x00"  # Subchunk1 size (16 for PCM)
        + b"\x01\x00"  # Audio format (1 = PCM)
        + b"\x01\x00"  # Number of channels (1 = mono)
        + b"\x44\xAC\x00\x00"  # Sample rate (44100 Hz)
        + b"\x88\x58\x01\x00"  # Byte rate (88200 bytes/sec)
        + b"\x02\x00"  # Block align (2 bytes)
        + b"\x10\x00"  # Bits per sample (16 bits)
        + b"data"
        + b"\x00\x08\x00\x00"  # Subchunk2 size (2048 bytes of data)
    )

    # Add 2048 bytes of silent audio (zeros)
    audio_data = b"\x00" * 2048

    return wav_header + audio_data


@pytest.fixture
def sample_audio_file(sample_audio_bytes, tmp_path):
    """
    Create temporary audio file.

    Args:
        sample_audio_bytes: Audio data
        tmp_path: pytest temporary directory

    Returns:
        Path to temporary audio file
    """
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(sample_audio_bytes)
    return audio_file


@pytest.fixture
def sample_text_short():
    """Short sample text for TTS testing."""
    return "Hello, this is a test."


@pytest.fixture
def sample_text_long():
    """Long sample text for TTS testing."""
    return """
    This is a much longer text sample that will be used to test
    text-to-speech functionality with more complex content. It includes
    multiple sentences, punctuation marks, and enough words to properly
    test the synthesis capabilities of the system. We want to ensure
    that longer texts are handled correctly, with proper pacing and
    pronunciation throughout the entire passage.
    """


@pytest.fixture
def sample_text_special_chars():
    """Text with special characters for TTS testing."""
    return "Hello! How are you? I'm fine. Cost: $50.00. Email: test@example.com."


@pytest.fixture
def sample_text_multilingual():
    """Multilingual text for TTS testing."""
    return "Hello world. Bonjour le monde. Hola mundo. 你好世界."


@pytest.fixture
def sample_text_ssml():
    """SSML-tagged text for TTS testing."""
    return '<speak>Hello <break time="500ms"/> world!</speak>'


@pytest.fixture
def sample_text_exceeds_limit():
    """Text exceeding max length (5000 chars) for validation testing."""
    return "This is a test. " * 400  # ~6400 chars


@pytest.fixture
def mock_async_executor():
    """
    Mock asyncio executor for testing async operations.

    Yields:
        AsyncMock that immediately returns the provided callable result
    """
    async def mock_executor(executor, func, *args):
        """Execute function immediately (no actual threading)."""
        return func(*args)

    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=mock_executor)
        yield mock_loop


@pytest.fixture
def clear_voice_cache():
    """
    Clear any cached voice data between tests.

    Ensures test isolation by clearing service-level caches.
    """
    yield
    # Reset any module-level caches
    from server.voice import service
    if hasattr(service, '_voice_cache'):
        service._voice_cache.clear()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# Session-scoped setup/teardown
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup test environment for entire test session.

    Sets environment variables and prepares test infrastructure.
    """
    # Set test environment variables
    os.environ['ELEVENLABS_API_KEY'] = 'test_api_key_12345'
    os.environ['TESTING'] = 'true'

    yield

    # Cleanup after all tests
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
