"""
ElevenLabs Voice Provider

Wraps the existing ElevenLabs implementation (server/voice/client.py) and
adds WebSocket streaming support for ultra-low latency.

Features:
- Premium quality TTS with natural voices
- Advanced voice cloning and customization
- Real-time WebSocket streaming
- Multi-language support
- Emotional control and voice settings

Docs: https://elevenlabs.io/docs
"""

import os
import logging
from typing import AsyncIterator, Optional, List, Dict, Any

from . import IVoiceProvider, ProviderType
from ..client import VoiceClient
from ..models import (
    TranscriptResult,
    AudioResult,
    VoiceInfo,
    VoiceLabels,
    TTSConfig,
    STTConfig,
    HealthStatus
)
from ..exceptions import (
    VoiceException,
    VoiceErrorCode,
    VoiceClientException,
    TTSException,
    STTException
)

logger = logging.getLogger(__name__)


class ElevenLabsProvider(IVoiceProvider):
    """
    ElevenLabs voice provider implementation.

    Wraps the existing VoiceClient for backward compatibility while
    implementing the IVoiceProvider interface.

    Premium Features:
    - Ultra-realistic voices
    - Voice cloning (create custom voices)
    - Emotional control (stability, similarity_boost, style)
    - Multi-language support with accent preservation
    - Professional voice library

    Pricing (as of Dec 2025):
    - TTS: $0.30 / 1K characters (premium quality)
    - STT: $0.015 / minute
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ElevenLabs provider.

        Args:
            api_key: Optional API key. Falls back to ELEVENLABS_API_KEY env var.

        Raises:
            VoiceClientException: If API key is missing or client init fails.
        """
        try:
            # Use existing VoiceClient implementation
            self._client = VoiceClient(api_key=api_key)
            logger.info("ElevenLabs voice provider initialized")

            # WebSocket client for streaming (lazy init)
            self._ws_client = None

        except Exception as e:
            raise VoiceClientException(
                message=f"Failed to initialize ElevenLabs provider: {str(e)}",
                cause=e
            )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ELEVENLABS

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_realtime(self) -> bool:
        return False  # Use LiveKit provider for real-time

    async def transcribe(
        self,
        audio_data: bytes,
        config: Optional[STTConfig] = None
    ) -> TranscriptResult:
        """
        Transcribe audio using ElevenLabs Scribe model.

        Features:
        - High accuracy speech recognition
        - Multi-language support
        - Speaker diarization
        - Audio event tagging (laughter, applause, etc.)

        Args:
            audio_data: Raw audio bytes
            config: Optional STT configuration

        Returns:
            TranscriptResult with text and metadata

        Raises:
            STTException: If transcription fails
        """
        logger.info(f"ElevenLabs transcription: {len(audio_data)} bytes")

        try:
            # Delegate to existing VoiceClient
            result = self._client.speech_to_text(
                audio=audio_data,
                model_id=config.model_id if config else "scribe_v1",
                language_code=config.language_code if config else None,
                tag_audio_events=config.tag_audio_events if config and hasattr(config, 'tag_audio_events') else False,
                timestamps_granularity=config.timestamps_granularity if config and hasattr(config, 'timestamps_granularity') else "word",
                diarize=config.diarize if config and hasattr(config, 'diarize') else False,
                max_speakers=config.max_speakers if config and hasattr(config, 'max_speakers') else 10
            )

            return result

        except Exception as e:
            logger.error(f"ElevenLabs transcription failed: {str(e)}")
            raise STTException(
                message=f"ElevenLabs transcription failed: {str(e)}",
                cause=e,
                details={"provider": "elevenlabs"}
            )

    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> AudioResult:
        """
        Synthesize speech using ElevenLabs TTS.

        Features:
        - Ultra-realistic voice quality
        - Emotional control via voice settings
        - Custom voice support
        - Multi-language with accent preservation

        Voice Settings:
        - stability: 0.0-1.0 (higher = more consistent, lower = more expressive)
        - similarity_boost: 0.0-1.0 (how closely to match original voice)
        - style: 0.0-1.0 (style exaggeration, 0 = neutral)
        - use_speaker_boost: bool (enhance clarity and quality)

        Args:
            text: Text to synthesize
            config: Optional TTS configuration

        Returns:
            AudioResult with audio data

        Raises:
            TTSException: If synthesis fails
        """
        logger.info(f"ElevenLabs synthesis: {len(text)} chars")

        try:
            # Delegate to existing VoiceClient
            result = self._client.text_to_speech(
                text=text,
                voice_id=config.voice_id if config else None,
                model_id=config.model_id if config else None,
                output_format=config.output_format if config and hasattr(config, 'output_format') else None,
                stability=config.stability if config and hasattr(config, 'stability') else None,
                similarity_boost=config.similarity_boost if config and hasattr(config, 'similarity_boost') else None,
                style=config.style if config and hasattr(config, 'style') else None,
                use_speaker_boost=config.use_speaker_boost if config and hasattr(config, 'use_speaker_boost') else None
            )

            return result

        except Exception as e:
            logger.error(f"ElevenLabs synthesis failed: {str(e)}")
            raise TTSException(
                message=f"ElevenLabs synthesis failed: {str(e)}",
                cause=e,
                details={"provider": "elevenlabs"}
            )

    async def synthesize_stream(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio using ElevenLabs.

        Two methods:
        1. REST API streaming (existing implementation)
        2. WebSocket streaming (lower latency, for future)

        Args:
            text: Text to synthesize
            config: Optional TTS configuration

        Yields:
            Audio chunks as bytes

        Raises:
            TTSException: If synthesis fails
        """
        logger.info(f"ElevenLabs streaming synthesis: {len(text)} chars")

        try:
            # Use REST API streaming (existing implementation)
            async for chunk in self._client.text_to_speech_stream(
                text=text,
                voice_id=config.voice_id if config else None,
                model_id=config.model_id if config else None,
                output_format=config.output_format if config and hasattr(config, 'output_format') else None
            ):
                yield chunk

        except Exception as e:
            logger.error(f"ElevenLabs streaming synthesis failed: {str(e)}")
            raise TTSException(
                message=f"ElevenLabs streaming synthesis failed: {str(e)}",
                cause=e,
                details={"provider": "elevenlabs"}
            )

    async def synthesize_stream_ws(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio via WebSocket for ultra-low latency.

        WebSocket streaming provides:
        - Lower latency (~200-300ms faster than REST)
        - Real-time audio generation
        - Bidirectional communication

        This is a future enhancement for when ultra-low latency is needed.

        Args:
            text: Text to synthesize
            config: Optional TTS configuration

        Yields:
            Audio chunks as bytes

        Raises:
            TTSException: If synthesis fails
        """
        logger.info(f"ElevenLabs WebSocket streaming synthesis: {len(text)} chars")

        try:
            # Initialize WebSocket client if needed
            if not self._ws_client:
                from elevenlabs.client import ElevenLabs
                self._ws_client = ElevenLabs(api_key=self._client._api_key)

            # Get voice configuration
            voice_id = config.voice_id if config else self._client._config.tts.voice_id
            model_id = config.model_id if config else self._client._config.tts.model_id

            # Open WebSocket connection
            async with self._ws_client.websocket(
                voice_id=voice_id,
                model_id=model_id
            ) as ws:
                # Send text
                await ws.send_text(text)

                # Stream audio chunks
                async for chunk in ws:
                    if hasattr(chunk, 'audio') and chunk.audio:
                        yield chunk.audio

                logger.info("ElevenLabs WebSocket streaming complete")

        except Exception as e:
            logger.error(f"ElevenLabs WebSocket streaming failed: {str(e)}")
            raise TTSException(
                message=f"ElevenLabs WebSocket streaming failed: {str(e)}",
                cause=e,
                details={"provider": "elevenlabs", "method": "websocket"}
            )

    async def list_voices(self) -> List[VoiceInfo]:
        """
        Get list of available ElevenLabs voices.

        Includes:
        - Pre-made voices (high-quality, curated)
        - Cloned voices (if user has created any)
        - Professional voices (premium library)

        Returns:
            List of VoiceInfo objects

        Raises:
            VoiceException: If voice list retrieval fails
        """
        logger.info("Fetching ElevenLabs voices")

        try:
            # Delegate to existing VoiceClient
            voices = self._client.list_voices()

            return voices

        except Exception as e:
            logger.error(f"Failed to fetch ElevenLabs voices: {str(e)}")
            raise VoiceException(
                message=f"Failed to fetch voices: {str(e)}",
                error_code=VoiceErrorCode.GET_VOICES_FAILED,
                cause=e
            )

    async def health_check(self) -> HealthStatus:
        """
        Check ElevenLabs API health and connectivity.

        Uses a lightweight check that doesn't require voices_read permission.
        Permission errors are treated as "degraded" (API reachable but limited),
        not "unhealthy" (API unreachable).

        Returns:
            HealthStatus with availability information
        """
        try:
            # Use the client's health check which handles permission errors gracefully
            # This avoids calling list_voices() which requires voices_read permission
            from ..client import VoiceClient
            if isinstance(self._client, VoiceClient):
                is_healthy = self._client.health_check()
                if is_healthy:
                    return HealthStatus(
                        healthy=True,
                        provider="elevenlabs",
                        message="ElevenLabs API is available",
                        details={"api_available": True}
                    )
                else:
                    return HealthStatus(
                        healthy=False,
                        provider="elevenlabs",
                        message="ElevenLabs API unavailable",
                        details={"api_available": False}
                    )
            else:
                # Fallback: Try to list voices (may fail with permission error)
                voices = await self.list_voices()
                return HealthStatus(
                healthy=True,
                provider="elevenlabs",
                message="ElevenLabs API is available",
                details={
                    "api_available": True,
                    "voices_count": len(voices)
                }
                )

        except Exception as e:
            # Check if it's a permission error
            from ..exceptions import map_elevenlabs_error, VoiceErrorCode
            try:
                mapped_error = map_elevenlabs_error(e)
                if mapped_error.error_code == VoiceErrorCode.API_KEY_MISSING_PERMISSION:
                    # Permission error means API is reachable, just missing permissions
                    # This is degraded, not unhealthy
                    logger.debug(f"ElevenLabs health check: API reachable but missing permissions: {mapped_error.message}")
                    return HealthStatus(
                        healthy=True,  # API is reachable
                        provider="elevenlabs",
                        message="ElevenLabs API is available (degraded: missing some permissions)",
                        details={
                            "api_available": True,
                            "permission_issue": True,
                            "message": mapped_error.message
                        }
                    )
            except Exception:
                pass
            
            # Other errors indicate API might be down
            logger.warning(f"ElevenLabs health check failed: {str(e)}")
            return HealthStatus(
                healthy=False,
                provider="elevenlabs",
                message=f"ElevenLabs API unavailable: {str(e)}",
                details={"error": str(e)}
            )
