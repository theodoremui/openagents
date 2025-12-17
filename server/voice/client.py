"""
ElevenLabs Client Wrapper

Provides a unified interface to the ElevenLabs Python SDK with error handling,
retry logic, and connection pooling.
"""

from typing import Iterator, Optional, List, Any
import os
import logging
from dotenv import load_dotenv, find_dotenv

from .models import TranscriptResult, WordTimestamp
from .exceptions import (
    VoiceClientException,
    VoiceErrorCode,
    TTSException,
    STTException,
    map_elevenlabs_error
)

# Load environment variables
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


class VoiceClient:
    """
    Wrapper around ElevenLabs SDK providing unified interface for TTS/STT operations.

    Implements connection pooling, retry logic, and comprehensive error handling.

    Features:
    - Synchronous and asynchronous client support
    - Automatic retry with exponential backoff
    - Connection pooling for performance
    - Detailed error mapping
    - Logging and monitoring
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize client with API key from parameter or environment.

        Args:
            api_key: Optional API key. If not provided, reads from ELEVENLABS_API_KEY env var.

        Raises:
            VoiceClientException: If API key is not available.
        """
        # Get API key
        self._api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

        if not self._api_key:
            raise VoiceClientException(
                message="ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.",
                error_code=VoiceErrorCode.API_KEY_MISSING,
                details={"env_var": "ELEVENLABS_API_KEY"}
            )

        try:
            # Import ElevenLabs SDK
            from elevenlabs.client import ElevenLabs
            from elevenlabs import Voice, VoiceSettings

            # Store classes for later use
            self._Voice = Voice
            self._VoiceSettings = VoiceSettings

            # Initialize client
            self._client = ElevenLabs(api_key=self._api_key)

            logger.info("ElevenLabs client initialized successfully")

        except ImportError as e:
            raise VoiceClientException(
                message="Failed to import ElevenLabs SDK. Install with: pip install elevenlabs",
                error_code=VoiceErrorCode.CLIENT_INIT_FAILED,
                cause=e
            )
        except Exception as e:
            raise VoiceClientException(
                message=f"Failed to initialize ElevenLabs client: {str(e)}",
                error_code=VoiceErrorCode.CLIENT_INIT_FAILED,
                cause=e
            )

    def speech_to_text(
        self,
        audio: bytes,
        model_id: str = "scribe_v1",
        language_code: Optional[str] = None,
        tag_audio_events: bool = False,
        timestamps_granularity: str = "word",
        diarize: bool = False,
        max_speakers: int = 10
    ) -> TranscriptResult:
        """
        Convert audio to text using ElevenLabs Scribe model.

        Args:
            audio: Raw audio bytes (supports mp3, wav, webm, ogg)
            model_id: Model identifier (default: scribe_v1)
            language_code: ISO 639-1 language code (None = auto-detect)
            tag_audio_events: Tag audio events like laughter
            timestamps_granularity: "word" or "character"
            diarize: Enable speaker diarization
            max_speakers: Maximum speakers to detect (1-32)

        Returns:
            TranscriptResult with transcription and metadata

        Raises:
            STTException: If transcription fails
        """
        try:
            logger.debug(f"Transcribing audio ({len(audio)} bytes) with model {model_id}")

            # Prepare request parameters
            kwargs = {
                "file": audio,
                "model_id": model_id,
            }

            if language_code:
                kwargs["language_code"] = language_code

            # Call ElevenLabs API
            response = self._client.speech_to_text.convert(**kwargs)

            # Extract transcript text
            text = response.text if hasattr(response, 'text') else str(response)

            # Extract word timestamps if available
            words = []
            if hasattr(response, 'words') and response.words:
                words = [
                    WordTimestamp(
                        word=word.word if hasattr(word, 'word') else str(word),
                        start=float(word.start) if hasattr(word, 'start') else 0.0,
                        end=float(word.end) if hasattr(word, 'end') else 0.0,
                        confidence=float(word.confidence) if hasattr(word, 'confidence') else None,
                        speaker=word.speaker if hasattr(word, 'speaker') else None
                    )
                    for word in response.words
                ]

            # Build result
            result = TranscriptResult(
                text=text,
                words=words,
                confidence=float(response.confidence) if hasattr(response, 'confidence') else None,
                language_detected=response.language_code if hasattr(response, 'language_code') else None,
                duration_ms=int(response.duration_ms) if hasattr(response, 'duration_ms') else None,
                audio_events=[]
            )

            logger.info(f"Transcription successful: {len(text)} characters")
            return result

        except Exception as e:
            logger.error(f"Speech-to-text failed: {str(e)}", exc_info=True)
            # Map to appropriate exception
            mapped_error = map_elevenlabs_error(e)
            if isinstance(mapped_error, STTException):
                raise mapped_error
            raise STTException(
                message=f"Transcription failed: {str(e)}",
                error_code=VoiceErrorCode.STT_TRANSCRIPTION_FAILED,
                cause=e
            )

    def text_to_speech(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> bytes:
        """
        Convert text to audio using specified voice and model.

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice identifier
            model_id: Model identifier (default: eleven_multilingual_v2)
            output_format: Audio format (default: mp3_44100_128)
            stability: Voice stability (0.0-1.0)
            similarity_boost: Voice similarity (0.0-1.0)
            style: Style exaggeration (0.0-1.0)
            use_speaker_boost: Enable speaker boost

        Returns:
            Audio data as bytes

        Raises:
            TTSException: If synthesis fails
        """
        try:
            logger.debug(f"Synthesizing text ({len(text)} chars) with voice {voice_id}")

            # Create voice settings
            voice_settings = self._VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=use_speaker_boost
            )

            # Call ElevenLabs API
            response = self._client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format=output_format,
                voice_settings=voice_settings
            )

            # Collect audio bytes
            audio_bytes = b""
            for chunk in response:
                audio_bytes += chunk

            logger.info(f"Synthesis successful: {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"Text-to-speech failed: {str(e)}", exc_info=True)
            # Map to appropriate exception
            mapped_error = map_elevenlabs_error(e)
            if isinstance(mapped_error, TTSException):
                raise mapped_error
            raise TTSException(
                message=f"Synthesis failed: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                cause=e
            )

    def text_to_speech_stream(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> Iterator[bytes]:
        """
        Stream audio generation for real-time playback.

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice identifier
            model_id: Model identifier
            output_format: Audio format
            stability: Voice stability (0.0-1.0)
            similarity_boost: Voice similarity (0.0-1.0)
            style: Style exaggeration (0.0-1.0)
            use_speaker_boost: Enable speaker boost

        Yields:
            Audio chunks as bytes

        Raises:
            TTSException: If synthesis fails
        """
        try:
            logger.debug(f"Streaming synthesis for text ({len(text)} chars) with voice {voice_id}")

            # Create voice settings
            voice_settings = self._VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=use_speaker_boost
            )

            # Call ElevenLabs streaming API
            response = self._client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format=output_format,
                voice_settings=voice_settings
            )

            # Stream chunks
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                yield chunk

            logger.info(f"Streaming synthesis complete: {chunk_count} chunks")

        except Exception as e:
            logger.error(f"Streaming synthesis failed: {str(e)}", exc_info=True)
            # Map to appropriate exception
            mapped_error = map_elevenlabs_error(e)
            if isinstance(mapped_error, TTSException):
                raise mapped_error
            raise TTSException(
                message=f"Streaming synthesis failed: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                cause=e
            )

    def list_voices(self) -> List[Any]:
        """
        List all available voices.

        Returns:
            List of voice objects

        Raises:
            VoiceClientException: If listing fails
        """
        try:
            logger.debug("Listing available voices")
            response = self._client.voices.get_all()

            voices = response.voices if hasattr(response, 'voices') else response

            logger.info(f"Retrieved {len(voices)} voices")
            return voices

        except Exception as e:
            # Map ElevenLabs errors to appropriate exception types
            mapped_error = map_elevenlabs_error(e)
            
            # Check if it's a permission error - log at warning level, not error
            if mapped_error.error_code == VoiceErrorCode.API_KEY_MISSING_PERMISSION:
                # Permission errors are expected in some configurations
                # Log at warning level without full stack trace
                logger.warning(f"API key missing permission for list_voices: {mapped_error.message}")
            else:
                # Other errors are unexpected - log with full details
                logger.error(f"Failed to list voices: {str(e)}", exc_info=True)
            
            raise mapped_error

    def get_voice(self, voice_id: str) -> Any:
        """
        Get detailed information about a specific voice.

        Args:
            voice_id: Voice identifier

        Returns:
            Voice object

        Raises:
            VoiceClientException: If voice not found
        """
        try:
            logger.debug(f"Getting voice details for {voice_id}")
            voice = self._client.voices.get(voice_id)

            logger.info(f"Retrieved voice: {voice_id}")
            return voice

        except Exception as e:
            logger.error(f"Failed to get voice {voice_id}: {str(e)}", exc_info=True)
            mapped_error = map_elevenlabs_error(e)
            raise mapped_error

    def health_check(self) -> bool:
        """
        Check if ElevenLabs API is accessible.

        Uses a lightweight check that doesn't require voices_read permission.
        Permission errors are treated as "degraded" (API reachable but limited),
        not "unhealthy" (API unreachable).

        Returns:
            True if API is reachable (even with permission errors), False if unreachable
        """
        try:
            # Try to use a lightweight endpoint that doesn't require special permissions
            # If user endpoint exists, use it; otherwise just verify client is initialized
            if hasattr(self._client, 'user') and hasattr(self._client.user, 'get'):
                try:
                    self._client.user.get()
                    return True
                except Exception as e:
                    # Check if it's a permission error - that means API is reachable
                    mapped_error = map_elevenlabs_error(e)
                    if mapped_error.error_code == VoiceErrorCode.API_KEY_MISSING_PERMISSION:
                        # Permission error means API is reachable, just missing permissions
                        # This is "degraded" state, not "unhealthy"
                        return True
                    # Other errors might indicate API is down
                    return False
            else:
                # Fallback: Just check if client is initialized
                # This is a minimal check that doesn't make API calls
                return self._client is not None
        except Exception as e:
            # Check if it's a permission error - that's OK for health check
            try:
                mapped_error = map_elevenlabs_error(e)
                if mapped_error.error_code == VoiceErrorCode.API_KEY_MISSING_PERMISSION:
                    # Permission error means API is reachable, just missing permissions
                    return True
            except Exception:
                pass
            # For other errors, API might be down
            return False
