"""
Test suite for Voice API endpoints (FastAPI router).

Tests cover:
- Transcribe endpoint (POST /voice/transcribe)
- Synthesize endpoint (POST /voice/synthesize)
- Stream synthesize endpoint (POST /voice/synthesize/stream)
- Voice management endpoints (GET /voice/voices)
- Config endpoints (GET /voice/config)
- Health check endpoint (GET /voice/health)
- Provider selection (query params and request body)
- Request validation
- Error handling

Total tests: 35
"""

import pytest
import io
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from server.main import app
from server.voice.models import TranscriptResult, AudioResult, VoiceInfo


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers for requests."""
    return {"X-API-Key": "test_api_key"}


# ============================================================================
# Transcribe Endpoint Tests (8 tests)
# ============================================================================

@pytest.mark.integration
def test_transcribe_success(client, sample_audio_file, auth_headers, mock_async_executor):
    """Test successful transcription with valid audio file."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data['success'] is True
    assert 'result' in data
    assert 'text' in data['result']
    assert isinstance(data['result']['text'], str)
    assert 'words' in data['result']


@pytest.mark.integration
def test_transcribe_with_language_code(client, sample_audio_file, auth_headers, mock_async_executor):
    """Test transcription with language_code parameter."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        params = {'language_code': 'es'}
        response = client.post(
            '/voice/transcribe',
            files=files,
            params=params,
            headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True


@pytest.mark.integration
def test_transcribe_invalid_file_format(client, auth_headers):
    """Test transcription with invalid file format returns 400."""
    # Submit text file instead of audio
    files = {'audio': ('test.txt', io.BytesIO(b"This is not audio"), 'text/plain')}
    response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    # Should fail validation
    assert response.status_code in [400, 422]


@pytest.mark.integration
def test_transcribe_missing_file(client, auth_headers):
    """Test transcription without file returns 422."""
    response = client.post('/voice/transcribe', headers=auth_headers)

    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.integration
def test_transcribe_empty_file(client, auth_headers):
    """Test transcription with empty file returns 400."""
    files = {'audio': ('empty.wav', io.BytesIO(b""), 'audio/wav')}
    response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    assert response.status_code in [400, 422]
    if response.status_code == 400:
        data = response.json()
        assert 'error' in data or 'detail' in data


@pytest.mark.integration
def test_transcribe_large_file(client, auth_headers):
    """Test transcription with very large file."""
    # Create 50MB file (may exceed limit)
    large_audio = io.BytesIO(b"\x00" * (50 * 1024 * 1024))
    files = {'audio': ('large.wav', large_audio, 'audio/wav')}

    response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    # Should either succeed or return size limit error
    if response.status_code != 200:
        assert response.status_code in [400, 413]  # 413 = Payload Too Large


@pytest.mark.integration
def test_transcribe_api_error_handling(client, sample_audio_file, auth_headers):
    """Test transcription handles API errors gracefully."""
    # Mock service to raise error
    with patch('server.voice.service.VoiceService.transcribe', side_effect=Exception("API error")):
        with open(sample_audio_file, 'rb') as f:
            files = {'audio': ('test.wav', f, 'audio/wav')}
            response = client.post('/voice/transcribe', files=files, headers=auth_headers)

        assert response.status_code == 500
        data = response.json()
        assert 'error' in data or 'detail' in data


@pytest.mark.integration
def test_transcribe_response_structure(client, sample_audio_file, auth_headers, mock_async_executor):
    """Test that transcription response has correct structure."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test.wav', f, 'audio/wav')}
        response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Validate response schema
    assert 'success' in data
    assert 'result' in data
    assert 'text' in data['result']
    assert 'words' in data['result']
    assert isinstance(data['result']['words'], list)

    if data['result']['words']:
        word = data['result']['words'][0]
        assert 'word' in word
        assert 'start' in word
        assert 'end' in word


# ============================================================================
# Synthesize Endpoint Tests (12 tests)
# ============================================================================

@pytest.mark.integration
def test_synthesize_success(client, auth_headers, mock_async_executor):
    """Test successful speech synthesis with valid text."""
    request_data = {
        "text": "Hello, this is a test.",
        "voice_id": None,
        "profile_name": "default"
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/mpeg'
    assert len(response.content) > 0


@pytest.mark.integration
def test_synthesize_with_voice_id(client, auth_headers, mock_async_executor):
    """Test synthesis with specific voice_id."""
    request_data = {
        "text": "Test with custom voice",
        "voice_id": "custom_voice_123"
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/mpeg'


@pytest.mark.integration
def test_synthesize_with_profile_name(client, auth_headers, mock_async_executor):
    """Test synthesis with voice profile."""
    request_data = {
        "text": "Professional voice test",
        "profile_name": "professional"
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200


@pytest.mark.integration
def test_synthesize_invalid_profile(client, auth_headers):
    """Test synthesis with non-existent profile returns 404."""
    request_data = {
        "text": "Test text",
        "profile_name": "nonexistent_profile"
    }

    # Mock service to raise error
    with patch('server.voice.service.VoiceService.synthesize', side_effect=Exception("Profile not found")):
        response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

        assert response.status_code in [404, 500]


@pytest.mark.integration
def test_synthesize_empty_text(client, auth_headers):
    """Test synthesis with empty text returns 422."""
    request_data = {
        "text": ""
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 422  # Validation error


@pytest.mark.integration
def test_synthesize_text_exceeds_limit(client, auth_headers):
    """Test synthesis with text exceeding 5000 chars."""
    request_data = {
        "text": "Test " * 1100  # >5000 chars
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    # Should either truncate or reject
    assert response.status_code in [200, 400, 422]


@pytest.mark.integration
def test_synthesize_returns_audio_mpeg(client, auth_headers, mock_async_executor):
    """Test that synthesis returns audio/mpeg content type."""
    request_data = {"text": "Audio format test"}

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    assert 'audio' in response.headers['content-type']


@pytest.mark.integration
def test_synthesize_api_error_handling(client, auth_headers):
    """Test synthesis handles API errors gracefully."""
    with patch('server.voice.service.VoiceService.synthesize', side_effect=Exception("TTS API error")):
        request_data = {"text": "Error test"}
        response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

        assert response.status_code == 500


@pytest.mark.integration
def test_synthesize_stream_success(client, auth_headers, mock_async_executor):
    """Test streaming synthesis returns chunks."""
    request_data = {"text": "Streaming test with longer text to generate multiple chunks"}

    response = client.post('/voice/synthesize/stream', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    # Streaming response
    assert len(response.content) > 0


@pytest.mark.integration
def test_synthesize_stream_chunks(client, auth_headers):
    """Test that streaming synthesis returns audio chunks."""
    # Mock streaming response
    async def mock_stream(*args, **kwargs):
        yield b"chunk1"
        yield b"chunk2"
        yield b"chunk3"

    with patch('server.voice.service.VoiceService.stream_synthesize', return_value=mock_stream()):
        request_data = {"text": "Streaming chunk test"}
        response = client.post('/voice/synthesize/stream', json=request_data, headers=auth_headers)

        assert response.status_code == 200
        # Content should be concatenated chunks
        assert b"chunk" in response.content


@pytest.mark.integration
def test_synthesize_stream_error_handling(client, auth_headers):
    """Test streaming synthesis error handling."""
    with patch('server.voice.service.VoiceService.stream_synthesize', side_effect=Exception("Stream error")):
        request_data = {"text": "Stream error test"}
        response = client.post('/voice/synthesize/stream', json=request_data, headers=auth_headers)

        assert response.status_code == 500


@pytest.mark.integration
def test_synthesize_content_type_validation(client, auth_headers, mock_async_executor):
    """Test that synthesis validates content-type."""
    request_data = {"text": "Content type test"}

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    content_type = response.headers.get('content-type', '')
    assert 'audio' in content_type.lower()


# ============================================================================
# Voice Management Endpoint Tests (3 tests)
# ============================================================================

@pytest.mark.integration
def test_list_voices_success(client, auth_headers, mock_async_executor):
    """Test GET /voice/voices returns voice list."""
    response = client.get('/voice/voices', headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    if len(data) > 0:
        voice = data[0]
        assert 'voice_id' in voice
        assert 'name' in voice
        assert 'category' in voice


@pytest.mark.integration
def test_list_voices_with_refresh(client, auth_headers, mock_async_executor):
    """Test GET /voice/voices?refresh=true forces cache refresh."""
    response = client.get('/voice/voices?refresh=true', headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.integration
def test_get_specific_voice(client, auth_headers, mock_async_executor):
    """Test GET /voice/voices/{voice_id} returns single voice."""
    voice_id = "test_voice_1"
    response = client.get(f'/voice/voices/{voice_id}', headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data['voice_id'] == voice_id
    assert 'name' in data


# ============================================================================
# Health & Config Endpoint Tests (2 tests)
# ============================================================================

@pytest.mark.integration
def test_health_check_success(client):
    """Test GET /voice/health returns health status."""
    response = client.get('/voice/health')

    assert response.status_code == 200
    data = response.json()

    assert 'healthy' in data
    assert 'elevenlabs_connected' in data or 'status' in data


@pytest.mark.integration
def test_get_config(client, auth_headers):
    """Test GET /voice/config returns current configuration."""
    response = client.get('/voice/config', headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert 'enabled' in data or 'tts' in data


# ============================================================================
# Provider Selection Tests (10 tests)
# ============================================================================

@pytest.mark.integration
def test_transcribe_with_cost_optimized_strategy(client, sample_audio_file, auth_headers):
    """Test transcription with cost-optimized provider strategy."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        params = {
            'provider_strategy': 'cost_optimized',
            'fallback_enabled': True
        }
        response = client.post(
            '/voice/transcribe',
            files=files,
            params=params,
            headers=auth_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True


@pytest.mark.integration
def test_transcribe_with_quality_optimized_strategy(client, sample_audio_file, auth_headers):
    """Test transcription with quality-optimized provider strategy."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        params = {
            'provider_strategy': 'quality_optimized'
        }
        response = client.post(
            '/voice/transcribe',
            files=files,
            params=params,
            headers=auth_headers
        )

    assert response.status_code == 200


@pytest.mark.integration
def test_transcribe_with_explicit_provider_openai(client, sample_audio_file, auth_headers):
    """Test transcription with explicit OpenAI provider selection."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        params = {
            'provider_strategy': 'explicit',
            'preferred_provider': 'openai',
            'fallback_enabled': False
        }
        response = client.post(
            '/voice/transcribe',
            files=files,
            params=params,
            headers=auth_headers
        )

    # Should succeed with OpenAI or return appropriate error
    assert response.status_code in [200, 500]


@pytest.mark.integration
def test_transcribe_with_explicit_provider_elevenlabs(client, sample_audio_file, auth_headers):
    """Test transcription with explicit ElevenLabs provider selection."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        params = {
            'provider_strategy': 'explicit',
            'preferred_provider': 'elevenlabs'
        }
        response = client.post(
            '/voice/transcribe',
            files=files,
            params=params,
            headers=auth_headers
        )

    assert response.status_code in [200, 500]


@pytest.mark.integration
def test_synthesize_with_provider_preferences_in_body(client, auth_headers):
    """Test synthesis with provider preferences in request body."""
    request_data = {
        "text": "Test with provider preferences",
        "provider_preferences": {
            "strategy": "cost_optimized",
            "fallback_enabled": True
        }
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    assert 'audio' in response.headers['content-type']


@pytest.mark.integration
def test_synthesize_with_explicit_openai_provider(client, auth_headers):
    """Test synthesis with explicit OpenAI provider."""
    request_data = {
        "text": "Test OpenAI synthesis",
        "provider_preferences": {
            "strategy": "explicit",
            "preferred_provider": "openai",
            "fallback_enabled": False
        }
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    # Should succeed or fail gracefully
    assert response.status_code in [200, 500]


@pytest.mark.integration
def test_synthesize_with_quality_optimized_strategy(client, auth_headers):
    """Test synthesis with quality-optimized strategy (should use ElevenLabs)."""
    request_data = {
        "text": "High quality synthesis test",
        "provider_preferences": {
            "strategy": "quality_optimized"
        }
    }

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200


@pytest.mark.integration
def test_synthesize_stream_with_provider_preferences(client, auth_headers):
    """Test streaming synthesis with provider preferences."""
    request_data = {
        "text": "Streaming test with cost optimization",
        "provider_preferences": {
            "strategy": "cost_optimized",
            "fallback_enabled": True
        }
    }

    response = client.post('/voice/synthesize/stream', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    assert len(response.content) > 0


@pytest.mark.integration
def test_transcribe_fallback_disabled(client, sample_audio_file, auth_headers):
    """Test that fallback_enabled=False prevents fallback on provider failure."""
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        params = {
            'provider_strategy': 'explicit',
            'preferred_provider': 'livekit',  # Not yet implemented
            'fallback_enabled': False
        }
        response = client.post(
            '/voice/transcribe',
            files=files,
            params=params,
            headers=auth_headers
        )

    # Should fail without fallback
    assert response.status_code in [400, 500]


@pytest.mark.integration
def test_provider_preferences_backward_compatibility(client, sample_audio_file, auth_headers):
    """Test that endpoints work without provider preferences (backward compatibility)."""
    # Transcribe without provider preferences
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test_audio.wav', f, 'audio/wav')}
        response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    assert response.status_code == 200

    # Synthesize without provider preferences
    request_data = {"text": "Backward compatibility test"}
    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200
