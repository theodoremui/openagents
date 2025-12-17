"""
Tests for OpenAI Voice Provider

Comprehensive test suite for OpenAI STT/TTS functionality.
"""

import pytest
import os
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from openai import AsyncOpenAI, OpenAIError

from server.voice.providers.openai_provider import OpenAIProvider
from server.voice.providers import ProviderType
from server.voice.models import TranscriptResult, AudioResult, STTConfig, TTSConfig
from server.voice.exceptions import STTException, TTSException, VoiceClientException


@pytest.fixture
def mock_openai_client():
    """Mock AsyncOpenAI client"""
    with patch('server.voice.providers.openai_provider.AsyncOpenAI') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def openai_provider(mock_openai_client):
    """Create OpenAI provider with mocked client"""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
        provider = OpenAIProvider()
        return provider


@pytest.fixture
def sample_audio_bytes():
    """Sample audio data (minimal WAV)"""
    return (
        b"RIFF"
        + b"\x24\x00\x00\x00"
        + b"WAVE"
        + b"fmt "
        + b"\x10\x00\x00\x00"
        + b"\x01\x00"
        + b"\x01\x00"
        + b"\x44\xAC\x00\x00"
        + b"\x88\x58\x01\x00"
        + b"\x02\x00"
        + b"\x10\x00"
        + b"data"
        + b"\x00\x00\x00\x00"
    )


class TestOpenAIProviderInit:
    """Test provider initialization"""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key"""
        with patch('server.voice.providers.openai_provider.AsyncOpenAI'):
            provider = OpenAIProvider(api_key="test_key")
            assert provider._api_key == "test_key"

    def test_init_with_env_var(self):
        """Test initialization with environment variable"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env_key'}):
            with patch('server.voice.providers.openai_provider.AsyncOpenAI'):
                provider = OpenAIProvider()
                assert provider._api_key == "env_key"

    def test_init_without_api_key(self):
        """Test initialization fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(VoiceClientException) as exc_info:
                OpenAIProvider()
            assert "API key not found" in str(exc_info.value)

    def test_provider_properties(self, openai_provider):
        """Test provider properties"""
        assert openai_provider.provider_type == ProviderType.OPENAI
        assert openai_provider.supports_streaming is True
        assert openai_provider.supports_realtime is False


class TestOpenAITranscribe:
    """Test speech-to-text functionality"""

    @pytest.mark.asyncio
    async def test_transcribe_success(self, openai_provider, mock_openai_client, sample_audio_bytes):
        """Test successful transcription"""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Hello world"
        mock_response.duration = 2.5
        mock_response.language = "en"
        mock_response.words = [
            MagicMock(word="Hello", start=0.0, end=0.5),
            MagicMock(word="world", start=0.6, end=1.1)
        ]

        mock_openai_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        # Execute
        result = await openai_provider.transcribe(sample_audio_bytes)

        # Verify
        assert isinstance(result, TranscriptResult)
        assert result.text == "Hello world"
        assert result.duration_ms == 2500  # 2.5 seconds = 2500 ms
        assert result.language_detected == "en"
        assert len(result.words) == 2
        assert result.words[0].word == "Hello"

    @pytest.mark.asyncio
    async def test_transcribe_with_config(self, openai_provider, mock_openai_client, sample_audio_bytes):
        """Test transcription with custom config"""
        config = STTConfig(
            model_id="whisper-1",
            language_code="es"
        )

        mock_response = MagicMock()
        mock_response.text = "Hola mundo"
        mock_response.duration = 2.0
        mock_response.language = "es"
        mock_response.words = []

        mock_openai_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        result = await openai_provider.transcribe(sample_audio_bytes, config)

        assert result.text == "Hola mundo"
        assert result.language_detected == "es"

        # Verify correct model was used
        call_args = mock_openai_client.audio.transcriptions.create.call_args
        assert call_args.kwargs['model'] == "whisper-1"
        assert call_args.kwargs['language'] == "es"

    @pytest.mark.asyncio
    async def test_transcribe_api_error(self, openai_provider, mock_openai_client, sample_audio_bytes):
        """Test transcription handles API errors"""
        mock_openai_client.audio.transcriptions.create = AsyncMock(
            side_effect=OpenAIError("API error")
        )

        with pytest.raises(STTException) as exc_info:
            await openai_provider.transcribe(sample_audio_bytes)

        assert "OpenAI transcription failed" in str(exc_info.value)


class TestOpenAISynthesize:
    """Test text-to-speech functionality"""

    @pytest.mark.asyncio
    async def test_synthesize_success(self, openai_provider, mock_openai_client):
        """Test successful synthesis"""
        # Mock response
        mock_response = MagicMock()
        mock_response.aread = AsyncMock(return_value=b"audio_data_bytes")

        mock_openai_client.audio.speech.create = AsyncMock(return_value=mock_response)

        # Execute
        result = await openai_provider.synthesize("Hello world")

        # Verify
        assert isinstance(result, AudioResult)
        assert result.audio_data == b"audio_data_bytes"
        assert result.content_type == "audio/mpeg"
        assert result.request_id is not None
        assert result.character_count > 0

    @pytest.mark.asyncio
    async def test_synthesize_with_custom_voice(self, openai_provider, mock_openai_client):
        """Test synthesis with custom voice"""
        config = TTSConfig(voice_id="onyx")

        mock_response = MagicMock()
        mock_response.aread = AsyncMock(return_value=b"audio_data")

        mock_openai_client.audio.speech.create = AsyncMock(return_value=mock_response)

        result = await openai_provider.synthesize("Test", config)

        assert result.audio_data == b"audio_data"
        assert result.request_id is not None

        # Verify correct voice was used
        call_args = mock_openai_client.audio.speech.create.call_args
        assert call_args.kwargs['voice'] == "onyx"

    @pytest.mark.asyncio
    async def test_synthesize_with_instructions(self, openai_provider, mock_openai_client):
        """Test synthesis with instructions"""
        config = TTSConfig(
            voice_id="coral",
            instructions="Speak in a cheerful tone"
        )

        mock_response = MagicMock()
        mock_response.aread = AsyncMock(return_value=b"audio_data")

        mock_openai_client.audio.speech.create = AsyncMock(return_value=mock_response)

        await openai_provider.synthesize("Test", config)

        # Verify instructions were passed
        call_args = mock_openai_client.audio.speech.create.call_args
        assert call_args.kwargs['instructions'] == "Speak in a cheerful tone"

    @pytest.mark.asyncio
    async def test_synthesize_api_error(self, openai_provider, mock_openai_client):
        """Test synthesis handles API errors"""
        mock_openai_client.audio.speech.create = AsyncMock(
            side_effect=OpenAIError("API error")
        )

        with pytest.raises(TTSException) as exc_info:
            await openai_provider.synthesize("Test")

        assert "OpenAI synthesis failed" in str(exc_info.value)


class TestOpenAIStreamSynthesize:
    """Test streaming text-to-speech"""

    @pytest.mark.asyncio
    async def test_synthesize_stream_success(self, openai_provider, mock_openai_client):
        """Test successful streaming synthesis"""
        # Mock streaming response
        mock_response = MagicMock()

        async def mock_iter_bytes(chunk_size):
            chunks = [b"chunk1", b"chunk2", b"chunk3"]
            for chunk in chunks:
                yield chunk

        mock_response.iter_bytes = mock_iter_bytes
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create a context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_openai_client.audio.speech.with_streaming_response.create = MagicMock(
            return_value=mock_context_manager
        )

        # Execute
        chunks = []
        async for chunk in openai_provider.synthesize_stream("Hello"):
            chunks.append(chunk)

        # Verify
        assert len(chunks) == 3
        assert chunks[0] == b"chunk1"
        assert chunks[1] == b"chunk2"
        assert chunks[2] == b"chunk3"

    @pytest.mark.asyncio
    async def test_synthesize_stream_api_error(self, openai_provider, mock_openai_client):
        """Test streaming handles API errors"""
        mock_openai_client.audio.speech.with_streaming_response.create = MagicMock(
            side_effect=OpenAIError("API error")
        )

        with pytest.raises(TTSException) as exc_info:
            async for _ in openai_provider.synthesize_stream("Test"):
                pass

        assert "OpenAI streaming synthesis failed" in str(exc_info.value)


class TestOpenAIVoiceManagement:
    """Test voice listing and management"""

    @pytest.mark.asyncio
    async def test_list_voices(self, openai_provider):
        """Test listing available voices"""
        voices = await openai_provider.list_voices()

        assert len(voices) == 10  # OpenAI has 10 voices
        assert all(v.category == "premade" for v in voices)
        assert all(v.name is not None for v in voices)

        # Check specific voices
        voice_ids = [v.voice_id for v in voices]
        assert "alloy" in voice_ids
        assert "coral" in voice_ids
        assert "onyx" in voice_ids


class TestOpenAIHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, openai_provider, mock_openai_client):
        """Test successful health check"""
        # Mock models list response
        mock_models = [MagicMock(), MagicMock(), MagicMock()]
        mock_openai_client.models.list = AsyncMock(return_value=mock_models)

        status = await openai_provider.health_check()

        assert status.healthy is True
        assert status.provider == "openai"
        assert "available" in status.message.lower()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, openai_provider, mock_openai_client):
        """Test health check handles failures"""
        mock_openai_client.models.list = AsyncMock(
            side_effect=OpenAIError("API unavailable")
        )

        status = await openai_provider.health_check()

        assert status.healthy is False
        assert status.provider == "openai"
        assert "unavailable" in status.message.lower()
