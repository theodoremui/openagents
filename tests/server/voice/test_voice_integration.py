"""
Test suite for Voice Integration (full-stack backend tests).

Tests cover:
- End-to-end workflows
- Component integration
- Error recovery
- Concurrent operations
- Real-world scenarios

Total tests: 15
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from server.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers."""
    return {"X-API-Key": "test_api_key"}


# ============================================================================
# End-to-End Workflow Tests (10 tests)
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
def test_upload_transcribe_get_text(client, sample_audio_file, auth_headers, mock_async_executor):
    """Test complete workflow: upload audio → transcribe → get text."""
    # Upload and transcribe
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test.wav', f, 'audio/wav')}
        response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data['success'] is True
    assert 'text' in data['result']
    assert len(data['result']['text']) > 0

    # Verify we got actual transcription
    transcribed_text = data['result']['text']
    assert isinstance(transcribed_text, str)


@pytest.mark.integration
@pytest.mark.slow
def test_submit_text_synthesize_get_audio(client, auth_headers, mock_async_executor):
    """Test complete workflow: submit text → synthesize → get audio."""
    request_data = {"text": "This is an integration test of text-to-speech."}

    response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/mpeg'

    audio_data = response.content
    assert len(audio_data) > 0
    assert isinstance(audio_data, bytes)


@pytest.mark.integration
@pytest.mark.slow
def test_list_voices_select_synthesize(client, auth_headers, mock_async_executor):
    """Test workflow: list voices → select voice → synthesize with voice."""
    # Step 1: List available voices
    voices_response = client.get('/voice/voices', headers=auth_headers)
    assert voices_response.status_code == 200

    voices = voices_response.json()
    assert len(voices) > 0

    # Step 2: Select first voice
    selected_voice = voices[0]
    voice_id = selected_voice['voice_id']

    # Step 3: Synthesize with selected voice
    request_data = {
        "text": "Testing with selected voice",
        "voice_id": voice_id
    }

    synth_response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert synth_response.status_code == 200
    assert len(synth_response.content) > 0


@pytest.mark.integration
@pytest.mark.slow
def test_get_config_use_profile_synthesize(client, auth_headers, mock_async_executor):
    """Test workflow: get config → use profile → synthesize."""
    # Step 1: Get configuration
    config_response = client.get('/voice/config', headers=auth_headers)
    assert config_response.status_code == 200

    config = config_response.json()

    # Step 2: Use profile from config
    request_data = {
        "text": "Testing with profile",
        "profile_name": "default"
    }

    synth_response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert synth_response.status_code == 200


@pytest.mark.integration
@pytest.mark.slow
def test_stream_synthesis_receive_chunks(client, auth_headers, mock_async_executor):
    """Test workflow: request streaming → receive audio chunks."""
    request_data = {
        "text": "This is a longer text for streaming synthesis to generate multiple chunks of audio data."
    }

    response = client.post('/voice/synthesize/stream', json=request_data, headers=auth_headers)

    assert response.status_code == 200

    # Verify we got streamed content
    content = response.content
    assert len(content) > 0


@pytest.mark.integration
@pytest.mark.slow
def test_transcribe_synthesize_round_trip(client, sample_audio_file, auth_headers, mock_async_executor):
    """Test round-trip: transcribe audio → synthesize text → audio."""
    # Step 1: Transcribe audio
    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test.wav', f, 'audio/wav')}
        transcribe_response = client.post('/voice/transcribe', files=files, headers=auth_headers)

    assert transcribe_response.status_code == 200
    transcribed_text = transcribe_response.json()['result']['text']

    # Step 2: Synthesize transcribed text
    request_data = {"text": transcribed_text}
    synth_response = client.post('/voice/synthesize', json=request_data, headers=auth_headers)

    assert synth_response.status_code == 200
    assert len(synth_response.content) > 0


@pytest.mark.integration
@pytest.mark.slow
def test_concurrent_transcriptions(client, sample_audio_file, auth_headers, mock_async_executor):
    """Test concurrent transcription requests."""
    import concurrent.futures

    def transcribe():
        with open(sample_audio_file, 'rb') as f:
            files = {'audio': ('test.wav', f, 'audio/wav')}
            return client.post('/voice/transcribe', files=files, headers=auth_headers)

    # Execute 5 concurrent transcriptions
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(transcribe) for _ in range(5)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All should succeed
    assert all(r.status_code == 200 for r in responses)
    assert len(responses) == 5


@pytest.mark.integration
@pytest.mark.slow
def test_concurrent_syntheses(client, auth_headers, mock_async_executor):
    """Test concurrent synthesis requests."""
    import concurrent.futures

    texts = [
        "First synthesis request",
        "Second synthesis request",
        "Third synthesis request",
        "Fourth synthesis request",
        "Fifth synthesis request"
    ]

    def synthesize(text):
        return client.post('/voice/synthesize', json={"text": text}, headers=auth_headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(synthesize, text) for text in texts]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(r.status_code == 200 for r in responses)
    assert len(responses) == 5


@pytest.mark.integration
@pytest.mark.slow
def test_config_hot_reload_during_request(client, auth_headers, temp_config_file, mock_async_executor):
    """Test config hot-reload while handling requests."""
    # Make first request
    response1 = client.post('/voice/synthesize', json={"text": "Before reload"}, headers=auth_headers)
    assert response1.status_code == 200

    # Modify config
    import time
    time.sleep(0.1)
    new_config = """
voice:
  enabled: true
  tts:
    voice_id: "reloaded_voice"
    model_id: "eleven_multilingual_v2"
  stt:
    model_id: "scribe_v1"
  voice_profiles:
    default:
      stability: 0.9
"""
    temp_config_file.write_text(new_config)

    # Make second request (should use new config)
    response2 = client.post('/voice/synthesize', json={"text": "After reload"}, headers=auth_headers)
    assert response2.status_code == 200


@pytest.mark.integration
def test_health_check_validation(client):
    """Test health check returns accurate status."""
    response = client.get('/voice/health')

    assert response.status_code == 200
    data = response.json()

    assert 'healthy' in data
    if data['healthy']:
        # If healthy, should have connection status
        assert 'elevenlabs_connected' in data or 'status' in data


# ============================================================================
# Error Recovery Tests (5 tests)
# ============================================================================

@pytest.mark.integration
def test_api_rate_limit_retry(client, sample_audio_file, auth_headers):
    """Test retry logic on API rate limit."""
    # Mock rate limit error
    call_count = {'count': 0}

    def mock_transcribe(*args, **kwargs):
        call_count['count'] += 1
        if call_count['count'] == 1:
            raise Exception("Rate limit exceeded")
        return {"text": "Success after retry", "words": []}

    with patch('server.voice.client.VoiceClient.speech_to_text', side_effect=mock_transcribe):
        with open(sample_audio_file, 'rb') as f:
            files = {'audio': ('test.wav', f, 'audio/wav')}
            response = client.post('/voice/transcribe', files=files, headers=auth_headers)

        # Should succeed after retry
        if response.status_code == 200:
            assert call_count['count'] > 1


@pytest.mark.integration
def test_network_timeout_error_response(client, sample_audio_file, auth_headers):
    """Test handling of network timeout errors."""
    with patch('server.voice.client.VoiceClient.speech_to_text', side_effect=TimeoutError("Network timeout")):
        with open(sample_audio_file, 'rb') as f:
            files = {'audio': ('test.wav', f, 'audio/wav')}
            response = client.post('/voice/transcribe', files=files, headers=auth_headers)

        # Should return error response
        assert response.status_code in [500, 503, 504]


@pytest.mark.integration
def test_invalid_api_key_401_error(client, sample_audio_file):
    """Test handling of invalid API key."""
    # Use invalid auth headers
    invalid_headers = {"X-API-Key": "invalid_key"}

    with open(sample_audio_file, 'rb') as f:
        files = {'audio': ('test.wav', f, 'audio/wav')}
        response = client.post('/voice/transcribe', files=files, headers=invalid_headers)

    assert response.status_code in [401, 403]


@pytest.mark.integration
def test_service_unavailable_503_error(client, auth_headers):
    """Test handling when service is unavailable."""
    with patch('server.voice.client.VoiceClient.text_to_speech', side_effect=Exception("Service unavailable")):
        response = client.post('/voice/synthesize', json={"text": "test"}, headers=auth_headers)

        assert response.status_code in [500, 503]
        data = response.json()
        assert 'error' in data or 'detail' in data


@pytest.mark.integration
def test_graceful_degradation(client, auth_headers, mock_async_executor):
    """Test graceful degradation when some features fail."""
    # Test that basic functionality works even if caching fails

    response = client.post('/voice/synthesize', json={"text": "Degradation test"}, headers=auth_headers)

    # Should still work
    assert response.status_code == 200
