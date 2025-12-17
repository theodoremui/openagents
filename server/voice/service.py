"""
Voice Service Layer

Business logic for voice operations, coordinating between VoiceClient,
configuration management, and caching.
"""

import os
from typing import AsyncIterator, Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta
import asyncio

from .client import VoiceClient
from .config import VoiceConfigManager
from .coordinator import VoiceCoordinator, ProviderPreference, SelectionStrategy
from .providers import ProviderType
from .models import (
    TranscriptResult,
    AudioResult,
    VoiceInfo,
    VoiceLabels,
    TTSConfig,
    STTConfig,
    SynthesizeRequest,
    TranscribeRequest
)
from .exceptions import (
    VoiceException,
    VoiceServiceException,
    VoiceClientException,
    TTSException,
    STTException,
    VoiceErrorCode
)
from .utils import (
    generate_request_id,
    validate_audio_format,
    sanitize_text_for_tts,
    estimate_tts_duration,
    get_content_type_for_format
)

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Core service orchestrating TTS and STT operations.

    Implements caching, validation, and profile management.

    Features:
    - Request validation and sanitization
    - Configuration management with profiles
    - Voice list caching
    - Streaming support for real-time audio
    - Comprehensive error handling
    - Multi-provider support via VoiceCoordinator

    Provider System:
    - Legacy mode: Uses VoiceClient (ElevenLabs only) for backward compatibility
    - Coordinator mode: Uses VoiceCoordinator for multi-provider support
    """

    def __init__(
        self,
        client: Optional[VoiceClient] = None,
        config_manager: Optional[VoiceConfigManager] = None,
        coordinator: Optional[VoiceCoordinator] = None,
        use_coordinator: bool = False
    ):
        """
        Initialize service with injected dependencies.

        Args:
            client: Legacy VoiceClient instance (ElevenLabs). Created if not provided.
            config_manager: Configuration manager. Created with defaults if not provided.
            coordinator: VoiceCoordinator for multi-provider support. Created if use_coordinator=True.
            use_coordinator: Whether to use coordinator mode. If True, coordinator is preferred over client.

        Note:
            If both client and coordinator are provided, coordinator takes precedence when use_coordinator=True.
        """
        self._client = client or VoiceClient()
        self._config = config_manager or VoiceConfigManager()
        self._coordinator = coordinator
        self._use_coordinator = use_coordinator

        # Initialize coordinator if requested but not provided
        if self._use_coordinator and not self._coordinator:
            try:
                self._coordinator = VoiceCoordinator()
                logger.info("VoiceCoordinator initialized automatically")
            except Exception as e:
                logger.warning(f"Failed to initialize VoiceCoordinator: {str(e)}. Falling back to VoiceClient")
                self._use_coordinator = False

        # Cache for voice list
        self._voice_cache: Optional[List[VoiceInfo]] = None
        self._voice_cache_time: Optional[datetime] = None

        mode = "Coordinator" if self._use_coordinator else "Legacy (VoiceClient)"
        logger.info(f"VoiceService initialized in {mode} mode")

    async def transcribe(
        self,
        audio_data: bytes,
        config: Optional[STTConfig] = None,
        session_id: Optional[str] = None,
        provider_preferences: Optional[ProviderPreference] = None
    ) -> TranscriptResult:
        """
        Transcribe audio to text.

        Args:
            audio_data: Raw audio bytes (supports mp3, wav, webm, ogg)
            config: STT configuration overrides
            session_id: Optional session for context continuity
            provider_preferences: Provider selection preferences (coordinator mode only)

        Returns:
            TranscriptResult with text and metadata

        Raises:
            STTException: If transcription fails

        Note:
            When use_coordinator=True, provider_preferences controls which provider is used.
            Otherwise, uses legacy VoiceClient (ElevenLabs).
        """
        request_id = generate_request_id()
        start_time = datetime.now()

        try:
            logger.info(f"[{request_id}] Starting transcription")

            # Validate audio
            if not validate_audio_format(audio_data):
                raise STTException(
                    message="Invalid audio format or size",
                    error_code=VoiceErrorCode.STT_AUDIO_INVALID,
                    details={"size_bytes": len(audio_data)}
                )

            # Get configuration
            stt_config = config or self._config.get_default_stt_config()

            # Log configuration
            if self._config.config.logging.log_api_calls:
                logger.info(
                    f"[{request_id}] Transcription config: model={stt_config.model_id}, "
                    f"language={stt_config.language_code}, audio_size={len(audio_data)} bytes"
                )

            # Choose execution path based on mode
            if self._use_coordinator and self._coordinator:
                # Coordinator mode: Multi-provider support
                logger.debug(f"[{request_id}] Using VoiceCoordinator")
                result = await self._coordinator.transcribe(
                    audio_data=audio_data,
                    config=stt_config,
                    preferences=provider_preferences
                )
            else:
                # Legacy mode: ElevenLabs VoiceClient
                logger.debug(f"[{request_id}] Using legacy VoiceClient")
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._client.speech_to_text(
                        audio=audio_data,
                        model_id=stt_config.model_id,
                        language_code=stt_config.language_code,
                        tag_audio_events=stt_config.tag_audio_events,
                        timestamps_granularity=stt_config.timestamps_granularity,
                        diarize=stt_config.diarize,
                        max_speakers=stt_config.max_speakers
                    )
                )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"[{request_id}] Transcription completed in {processing_time:.2f}s: "
                f"{len(result.text)} characters"
            )

            return result

        except STTException:
            raise
        except Exception as e:
            logger.error(f"[{request_id}] Transcription failed: {str(e)}", exc_info=True)
            raise STTException(
                message=f"Transcription failed: {str(e)}",
                error_code=VoiceErrorCode.STT_TRANSCRIPTION_FAILED,
                details={"request_id": request_id},
                cause=e
            )

    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None,
        profile_name: Optional[str] = None,
        provider_preferences: Optional[ProviderPreference] = None
    ) -> AudioResult:
        """
        Synthesize text to speech audio.

        Args:
            text: Text to convert to speech
            config: TTS configuration overrides
            profile_name: Named voice profile to use
            provider_preferences: Provider selection preferences (coordinator mode only)

        Returns:
            AudioResult with audio data and metadata

        Raises:
            TTSException: If synthesis fails

        Note:
            When use_coordinator=True, provider_preferences controls which provider is used.
            Otherwise, uses legacy VoiceClient (ElevenLabs).
        """
        request_id = generate_request_id()
        start_time = datetime.now()

        try:
            logger.info(f"[{request_id}] Starting synthesis")

            # Sanitize text
            text = sanitize_text_for_tts(text, max_length=5000)

            if not text:
                raise TTSException(
                    message="Text is empty after sanitization",
                    error_code=VoiceErrorCode.TTS_TEXT_TOO_LONG,
                    details={"request_id": request_id}
                )

            # Get configuration (profile overrides default)
            if profile_name:
                profile = self._config.get_profile(profile_name)
                if profile:
                    tts_config = TTSConfig(
                        voice_id=profile.voice_id,
                        model_id=profile.model_id,
                        stability=profile.stability,
                        similarity_boost=profile.similarity_boost,
                        style=profile.style,
                        use_speaker_boost=profile.use_speaker_boost
                    )
                else:
                    logger.warning(f"Profile '{profile_name}' not found, using default")
                    tts_config = config or self._config.get_default_tts_config()
            else:
                tts_config = config or self._config.get_default_tts_config()

            # Log configuration
            if self._config.config.logging.log_api_calls:
                logger.info(
                    f"[{request_id}] Synthesis config: voice={tts_config.voice_id}, "
                    f"model={tts_config.model_id}, text_length={len(text)}"
                )

            # Choose execution path based on mode
            if self._use_coordinator and self._coordinator:
                # Coordinator mode: Multi-provider support
                logger.debug(f"[{request_id}] Using VoiceCoordinator")
                result = await self._coordinator.synthesize(
                    text=text,
                    config=tts_config,
                    preferences=provider_preferences
                )
            else:
                # Legacy mode: ElevenLabs VoiceClient
                logger.debug(f"[{request_id}] Using legacy VoiceClient")
                loop = asyncio.get_event_loop()
                audio_bytes = await loop.run_in_executor(
                    None,
                    lambda: self._client.text_to_speech(
                        text=text,
                        voice_id=tts_config.voice_id,
                        model_id=tts_config.model_id,
                        output_format=tts_config.output_format,
                        stability=tts_config.stability,
                        similarity_boost=tts_config.similarity_boost,
                        style=tts_config.style,
                        use_speaker_boost=tts_config.use_speaker_boost
                    )
                )

                # Build result
                content_type = get_content_type_for_format(tts_config.output_format)
                duration_ms = estimate_tts_duration(text)

                result = AudioResult(
                    audio_data=audio_bytes,
                    content_type=content_type,
                    duration_ms=duration_ms,
                    request_id=request_id,
                    character_count=len(text)
                )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"[{request_id}] Synthesis completed in {processing_time:.2f}s: "
                f"{len(result.audio_data)} bytes"
            )

            return result

        except TTSException:
            raise
        except Exception as e:
            logger.error(f"[{request_id}] Synthesis failed: {str(e)}", exc_info=True)
            raise TTSException(
                message=f"Synthesis failed: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                details={"request_id": request_id},
                cause=e
            )

    async def stream_synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None,
        profile_name: Optional[str] = None,
        provider_preferences: Optional[ProviderPreference] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized speech for real-time playback.

        Yields audio chunks as they become available.

        Args:
            text: Text to convert to speech
            config: TTS configuration overrides
            profile_name: Named voice profile to use
            provider_preferences: Provider selection preferences (coordinator mode only)

        Yields:
            Audio chunks as bytes

        Raises:
            TTSException: If synthesis fails
        """
        request_id = generate_request_id()
        start_time = datetime.now()

        try:
            logger.info(f"[{request_id}] Starting streaming synthesis")

            # Sanitize text
            text = sanitize_text_for_tts(text, max_length=5000)

            if not text:
                raise TTSException(
                    message="Text is empty after sanitization",
                    error_code=VoiceErrorCode.TTS_TEXT_TOO_LONG,
                    details={"request_id": request_id}
                )

            # Get configuration (same as synthesize)
            if profile_name:
                profile = self._config.get_profile(profile_name)
                if profile:
                    tts_config = TTSConfig(
                        voice_id=profile.voice_id,
                        model_id=profile.model_id,
                        stability=profile.stability,
                        similarity_boost=profile.similarity_boost,
                        style=profile.style,
                        use_speaker_boost=profile.use_speaker_boost
                    )
                else:
                    tts_config = config or self._config.get_default_tts_config()
            else:
                tts_config = config or self._config.get_default_tts_config()

            # Log configuration
            if self._config.config.logging.log_api_calls:
                logger.info(
                    f"[{request_id}] Streaming config: voice={tts_config.voice_id}, "
                    f"model={tts_config.model_id}"
                )

            # Choose execution path based on mode
            chunk_count = 0
            total_bytes = 0

            if self._use_coordinator and self._coordinator:
                # Coordinator mode: Multi-provider support
                logger.debug(f"[{request_id}] Using VoiceCoordinator for streaming")
                async for chunk in self._coordinator.synthesize_stream(
                    text=text,
                    config=tts_config,
                    preferences=provider_preferences
                ):
                    chunk_count += 1
                    total_bytes += len(chunk)
                    yield chunk
            else:
                # Legacy mode: ElevenLabs VoiceClient
                logger.debug(f"[{request_id}] Using legacy VoiceClient for streaming")
                for chunk in self._client.text_to_speech_stream(
                    text=text,
                    voice_id=tts_config.voice_id,
                    model_id=tts_config.model_id,
                    output_format=tts_config.output_format,
                    stability=tts_config.stability,
                    similarity_boost=tts_config.similarity_boost,
                    style=tts_config.style,
                    use_speaker_boost=tts_config.use_speaker_boost
                ):
                    chunk_count += 1
                    total_bytes += len(chunk)
                    yield chunk

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"[{request_id}] Streaming synthesis completed in {processing_time:.2f}s: "
                f"{chunk_count} chunks, {total_bytes} bytes"
            )

        except TTSException:
            raise
        except Exception as e:
            logger.error(f"[{request_id}] Streaming synthesis failed: {str(e)}", exc_info=True)
            raise TTSException(
                message=f"Streaming synthesis failed: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                details={"request_id": request_id},
                cause=e
            )

    async def get_voices(self, refresh: bool = False) -> List[VoiceInfo]:
        """
        Get available voices with optional cache refresh.

        Args:
            refresh: Force refresh from API

        Returns:
            List of VoiceInfo objects

        Raises:
            VoiceServiceException: If listing fails (unless cached data available)
        """
        try:
            # Check cache
            cache_ttl = self._config.config.cache.voice_list_ttl
            now = datetime.now()

            if not refresh and self._voice_cache is not None and self._voice_cache_time:
                cache_age = (now - self._voice_cache_time).total_seconds()
                if cache_age < cache_ttl:
                    logger.debug(f"Using cached voice list (age: {cache_age:.1f}s)")
                    return self._voice_cache

            # Fetch from API - use coordinator if enabled, otherwise use legacy client
            if self._use_coordinator and self._coordinator:
                logger.info("Fetching voice list via VoiceCoordinator (multi-provider)")
                # Fetch from coordinator (respects default_provider and enabled providers)
                default_provider = self._config.config.default_provider
                from .providers import ProviderType
                provider_type = ProviderType.OPENAI if default_provider == "openai" else ProviderType.ELEVENLABS if default_provider == "elevenlabs" else None
                
                logger.info(f"Fetching voice list from coordinator (default_provider: {default_provider})")
                voices = await self._coordinator.list_voices(provider_type=provider_type)
                # Coordinator already returns List[VoiceInfo], no conversion needed
            else:
                logger.info("Fetching voice list from ElevenLabs API (legacy mode)")
                loop = asyncio.get_event_loop()
                voices_raw = await loop.run_in_executor(None, self._client.list_voices)

                # Convert raw ElevenLabs responses to VoiceInfo objects
                voices = []
                for voice in voices_raw:
                    voice_info = VoiceInfo(
                        voice_id=voice.voice_id if hasattr(voice, 'voice_id') else str(voice),
                        name=voice.name if hasattr(voice, 'name') else "Unknown",
                        category=voice.category if hasattr(voice, 'category') else None,
                        labels=VoiceLabels(
                            accent=voice.labels.get('accent') if hasattr(voice, 'labels') else None,
                            age=voice.labels.get('age') if hasattr(voice, 'labels') else None,
                            gender=voice.labels.get('gender') if hasattr(voice, 'labels') else None,
                            use_case=voice.labels.get('use case') if hasattr(voice, 'labels') else None,
                            description=voice.labels.get('description') if hasattr(voice, 'labels') else None
                        ),
                        preview_url=voice.preview_url if hasattr(voice, 'preview_url') else None,
                        available_for_tiers=voice.available_for_tiers if hasattr(voice, 'available_for_tiers') else []
                    )
                    voices.append(voice_info)

            # Update cache
            self._voice_cache = voices
            self._voice_cache_time = now

            logger.info(f"Voice list cached: {len(voices)} voices")
            return voices

        except VoiceClientException as e:
            # Check if this is a permission error
            if e.error_code == VoiceErrorCode.API_KEY_MISSING_PERMISSION:
                # Try to return cached data even if expired
                if self._voice_cache is not None:
                    logger.warning(
                        f"API key missing permission for voices_read. "
                        f"Returning cached voice list ({len(self._voice_cache)} voices). "
                        f"Error: {e.message}"
                    )
                    return self._voice_cache
                # No cache available, raise the error
                logger.warning(f"API key missing permission and no cached data available: {e.message}")
                raise VoiceServiceException(
                    message=f"API key missing required permission. {e.message}",
                    error_code=VoiceErrorCode.API_KEY_MISSING_PERMISSION,
                    details=e.details,
                    cause=e
                )
            # For other client errors, re-raise as service exception
            raise VoiceServiceException(
                message=f"Failed to list voices: {e.message}",
                error_code=e.error_code,
                details=e.details,
                cause=e
            )
        except Exception as e:
            logger.error(f"Failed to get voices: {str(e)}", exc_info=True)
            raise VoiceServiceException(
                message=f"Failed to list voices: {str(e)}",
                error_code=VoiceErrorCode.SERVICE_UNAVAILABLE,
                cause=e
            )

    async def get_voice(self, voice_id: str) -> VoiceInfo:
        """
        Get detailed information about a specific voice.

        Args:
            voice_id: Voice identifier

        Returns:
            VoiceInfo object

        Raises:
            VoiceServiceException: If voice not found
        """
        try:
            logger.info(f"Getting voice details for {voice_id}")

            # Use coordinator if enabled, otherwise use legacy client
            if self._use_coordinator and self._coordinator:
                logger.debug(f"Fetching voice '{voice_id}' via VoiceCoordinator (multi-provider)")
                voice_info = await self._coordinator.get_voice(voice_id)
                # Coordinator already returns VoiceInfo, no conversion needed
            else:
                logger.debug(f"Fetching voice '{voice_id}' from ElevenLabs API (legacy mode)")
                # Try to fetch from API
                loop = asyncio.get_event_loop()
                voice = await loop.run_in_executor(None, lambda: self._client.get_voice(voice_id))

                # Convert to VoiceInfo
                voice_info = VoiceInfo(
                    voice_id=voice.voice_id if hasattr(voice, 'voice_id') else voice_id,
                    name=voice.name if hasattr(voice, 'name') else "Unknown",
                    category=voice.category if hasattr(voice, 'category') else None,
                    labels=VoiceLabels(
                        accent=voice.labels.get('accent') if hasattr(voice, 'labels') else None,
                        age=voice.labels.get('age') if hasattr(voice, 'labels') else None,
                        gender=voice.labels.get('gender') if hasattr(voice, 'labels') else None,
                        use_case=voice.labels.get('use case') if hasattr(voice, 'labels') else None,
                        description=voice.labels.get('description') if hasattr(voice, 'labels') else None
                    ),
                    preview_url=voice.preview_url if hasattr(voice, 'preview_url') else None,
                    available_for_tiers=voice.available_for_tiers if hasattr(voice, 'available_for_tiers') else []
                )

            return voice_info

        except Exception as e:
            logger.error(f"Failed to get voice {voice_id}: {str(e)}", exc_info=True)
            raise VoiceServiceException(
                message=f"Failed to get voice: {str(e)}",
                error_code=VoiceErrorCode.SERVICE_UNAVAILABLE,
                cause=e
            )

    def validate_config(self) -> bool:
        """
        Validate current configuration.

        Returns:
            True if valid, False otherwise
        """
        try:
            validation = self._config.validate(self._config.config)
            if not validation.valid:
                logger.error(f"Configuration validation failed: {validation.errors}")
                return False

            if validation.warnings:
                logger.warning(f"Configuration warnings: {validation.warnings}")

            return True

        except Exception as e:
            logger.error(f"Configuration validation error: {str(e)}", exc_info=True)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check service health.

        Returns:
            Health status dictionary with detailed status
        """
        try:
            # Check ElevenLabs connection
            loop = asyncio.get_event_loop()
            elevenlabs_healthy = await loop.run_in_executor(
                None,
                self._client.health_check
            )

            # Check configuration
            config_loaded = self._config.config is not None

            # Determine status
            if elevenlabs_healthy and config_loaded:
                status = "healthy"
            elif config_loaded:
                # Config loaded but API has issues - degraded
                status = "degraded"
            else:
                status = "unhealthy"

            return {
                "status": status,
                "elevenlabs_connected": elevenlabs_healthy,
                "config_loaded": config_loaded,
                "timestamp": datetime.utcnow()
            }

        except VoiceClientException as e:
            # Handle permission errors gracefully
            if e.error_code == VoiceErrorCode.API_KEY_MISSING_PERMISSION:
                # Permission error means API is reachable, just missing permissions
                # This is degraded, not unhealthy
                logger.debug(f"Health check: API reachable but missing permissions: {e.message}")
                return {
                    "status": "degraded",
                    "elevenlabs_connected": True,  # API is reachable
                    "config_loaded": self._config.config is not None,
                    "timestamp": datetime.utcnow(),
                    "details": {
                        "permission_issue": True,
                        "message": "API key missing some permissions (degraded mode)"
                    }
                }
            # Other client errors
            logger.warning(f"Health check failed: {e.message}")
            return {
                "status": "unhealthy",
                "elevenlabs_connected": False,
                "config_loaded": self._config.config is not None,
                "timestamp": datetime.utcnow(),
                "error": e.message
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}", exc_info=True)
            return {
                "status": "unhealthy",
                "elevenlabs_connected": False,
                "config_loaded": False,
                "timestamp": datetime.utcnow(),
                "error": str(e)
            }
