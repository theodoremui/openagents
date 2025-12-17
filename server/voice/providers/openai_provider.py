"""
OpenAI Voice Provider

Implements voice operations using OpenAI's:
- Speech-to-Text: Whisper (whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe)
- Text-to-Speech: gpt-4o-mini-tts with 11 voices

Features:
- Word-level timestamps for transcriptions
- Multiple voice options for TTS
- Streaming support for real-time audio playback
- Instruction-based voice control (tone, speed, emotion)

Docs:
- STT: https://platform.openai.com/docs/guides/speech-to-text
- TTS: https://platform.openai.com/docs/guides/text-to-speech
"""
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import tempfile
import logging
from typing import AsyncIterator, Optional, List, Dict, Any
from dotenv import load_dotenv
import asyncio

from openai import AsyncOpenAI, OpenAIError

from . import IVoiceProvider, ProviderType
from ..models import (
    TranscriptResult,
    AudioResult,
    VoiceInfo,
    VoiceLabels,
    WordTimestamp,
    TTSConfig,
    STTConfig,
    ProviderHealthStatus
)
from ..exceptions import (
    VoiceException,
    VoiceClientException,
    TTSException,
    STTException,
    VoiceErrorCode
)
from ..utils import (
    generate_request_id,
    validate_audio_format,
    sanitize_text_for_tts,
    estimate_tts_duration
)

load_dotenv()
logger = logging.getLogger(__name__)


# OpenAI TTS Voices (as of December 2025)
OPENAI_VOICES: Dict[str, Dict[str, Any]] = {
    "alloy": {
        "name": "Alloy",
        "description": "Balanced, neutral voice",
        "gender": "neutral",
        "style": "professional"
    },
    "ash": {
        "name": "Ash",
        "description": "Smooth, warm voice",
        "gender": "neutral",
        "style": "friendly"
    },
    "ballad": {
        "name": "Ballad",
        "description": "Expressive, storytelling voice",
        "gender": "neutral",
        "style": "dramatic"
    },
    "coral": {
        "name": "Coral",
        "description": "Clear, cheerful voice",
        "gender": "female",
        "style": "friendly"
    },
    "echo": {
        "name": "Echo",
        "description": "Deep, authoritative voice",
        "gender": "male",
        "style": "professional"
    },
    "fable": {
        "name": "Fable",
        "description": "Warm, engaging voice",
        "gender": "neutral",
        "style": "storytelling"
    },
    "nova": {
        "name": "Nova",
        "description": "Bright, energetic voice",
        "gender": "female",
        "style": "energetic"
    },
    "onyx": {
        "name": "Onyx",
        "description": "Deep, powerful voice",
        "gender": "male",
        "style": "authoritative"
    },
    "sage": {
        "name": "Sage",
        "description": "Calm, wise voice",
        "gender": "neutral",
        "style": "calm"
    },
    "shimmer": {
        "name": "Shimmer",
        "description": "Soft, gentle voice",
        "gender": "female",
        "style": "gentle"
    }
}


class OpenAIProvider(IVoiceProvider):
    """
    OpenAI voice provider implementation.

    Cost-effective alternative to premium providers, with excellent quality
    for most use cases. Ideal for high-volume applications.

    Pricing (as of Dec 2025):
    - STT (Whisper): $0.006 / minute
    - STT (gpt-4o-transcribe): $0.01 / minute
    - TTS (gpt-4o-mini-tts): $0.012 / 1M characters
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.

        Args:
            api_key: Optional API key. Falls back to OPENAI_API_KEY env var.

        Raises:
            VoiceClientException: If API key is missing or invalid.
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self._api_key:
            raise VoiceClientException(
                message="OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
                error_code=VoiceErrorCode.API_KEY_MISSING,
                details={"env_var": "OPENAI_API_KEY"}
            )

        try:
            self._client = AsyncOpenAI(api_key=self._api_key)
            logger.info("OpenAI voice provider initialized")
        except Exception as e:
            raise VoiceClientException(
                message=f"Failed to initialize OpenAI client: {str(e)}",
                error_code=VoiceErrorCode.CLIENT_INIT_FAILED,
                cause=e
            )

        # Configuration
        self._default_stt_model = "gpt-4o-transcribe"  # Best quality
        self._default_tts_model = "gpt-4o-mini-tts"    # Best value
        self._default_voice = "coral"                   # Friendly, clear

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_realtime(self) -> bool:
        return False  # OpenAI Realtime API is separate, not implemented here

    async def transcribe(
        self,
        audio_data: bytes,
        config: Optional[STTConfig] = None
    ) -> TranscriptResult:
        """
        Transcribe audio using OpenAI Whisper or gpt-4o-transcribe.

        Models:
        - whisper-1: Classic Whisper, good quality, lower cost
        - gpt-4o-transcribe: Latest model, best quality
        - gpt-4o-mini-transcribe: Fast, good quality, cost-effective

        Features:
        - Word-level timestamps
        - Multi-language support (98 languages)
        - Automatic language detection
        - Optional prompts for context

        Args:
            audio_data: Raw audio bytes (mp3, wav, webm, m4a, etc.)
            config: Optional STT configuration

        Returns:
            TranscriptResult with text and word timestamps

        Raises:
            STTException: If transcription fails
        """
        request_id = generate_request_id()
        logger.info(f"[{request_id}] OpenAI transcription request: {len(audio_data)} bytes")

        # Determine model
        model = (config.model_id if config else None) or self._default_stt_model

        try:
            # OpenAI requires a file-like object, so create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            try:
                # Call OpenAI Transcriptions API
                # FIX: gpt-4o-transcribe does NOT support verbose_json
                is_gpt4o = model.startswith("gpt-4o")
                
                with open(temp_path, "rb") as audio_file:
                    if is_gpt4o:
                        response = await self._client.audio.transcriptions.create(
                            model=model,
                            file=audio_file,
                            response_format="json",
                            language=config.language_code if config else None,
                            prompt=config.prompt if config and hasattr(config, 'prompt') else None
                        )
                    else:
                        response = await self._client.audio.transcriptions.create(
                            model=model,
                            file=audio_file,
                            response_format="verbose_json",
                            timestamp_granularities=["word"],
                            language=config.language_code if config else None,
                            prompt=config.prompt if config and hasattr(config, 'prompt') else None
                        )
                # Parse response
                words = []
                if hasattr(response, 'words') and response.words:
                    words = [
                        WordTimestamp(
                            word=word.word,
                            start=word.start,
                            end=word.end,
                            confidence=1.0  # OpenAI doesn't provide confidence scores
                        )
                        for word in response.words
                    ]

                # Convert duration to milliseconds if available
                duration_ms = None
                if hasattr(response, 'duration') and response.duration:
                    duration_ms = int(response.duration * 1000)  # Convert seconds to ms

                result = TranscriptResult(
                    text=response.text,
                    words=words,
                    duration_ms=duration_ms,
                    language_detected=response.language if hasattr(response, 'language') else None,
                    confidence=1.0  # OpenAI doesn't provide overall confidence
                )

                logger.info(
                    f"[{request_id}] OpenAI transcription successful: "
                    f"{len(result.text)} chars, {len(words)} words"
                )

                return result

            finally:
                # Clean up temp file
                os.unlink(temp_path)

        except OpenAIError as e:
            logger.error(f"[{request_id}] OpenAI transcription failed: {str(e)}")
            raise STTException(
                message=f"OpenAI transcription failed: {str(e)}",
                error_code=VoiceErrorCode.STT_TRANSCRIPTION_FAILED,
                cause=e,
                details={"provider": "openai", "model": model}
            )
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
            raise STTException(
                message=f"Transcription error: {str(e)}",
                error_code=VoiceErrorCode.STT_TRANSCRIPTION_FAILED,
                cause=e
            )

    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> AudioResult:
        """
        Synthesize speech using gpt-4o-mini-tts.

        Voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer

        Features:
        - Instruction-based control (tone, speed, emotion)
        - Multiple voices with different characteristics
        - High-quality audio output
        - Supports SSML-like instructions

        Example instructions:
        - "Speak in a cheerful and positive tone."
        - "Speak slowly and clearly."
        - "Use a professional, authoritative tone."

        Args:
            text: Text to synthesize
            config: Optional TTS configuration

        Returns:
            AudioResult with audio data

        Raises:
            TTSException: If synthesis fails
        """
        request_id = generate_request_id()
        logger.info(f"[{request_id}] OpenAI synthesis request: {len(text)} chars")

        # Sanitize text
        sanitized_text = sanitize_text_for_tts(text)

        # Get voice and model
        voice_id = (config.voice_id if config else None) or self._default_voice
        model = self._default_tts_model

        # Get instructions if provided
        instructions = None
        if config and hasattr(config, 'instructions') and config.instructions:
            instructions = config.instructions

        try:
            # Call OpenAI Text-to-Speech API
            response = await self._client.audio.speech.create(
                model=model,
                voice=voice_id,
                input=sanitized_text,
                instructions=instructions,
                response_format="mp3"  # or wav, opus, aac, flac, pcm
            )

            # Get audio bytes
            audio_bytes = await response.aread()

            # Estimate duration in milliseconds
            duration_ms = int(estimate_tts_duration(text) * 1000) if estimate_tts_duration(text) else None

            result = AudioResult(
                audio_data=audio_bytes,
                content_type="audio/mpeg",
                duration_ms=duration_ms,
                request_id=request_id,
                character_count=len(sanitized_text)
            )

            logger.info(
                f"[{request_id}] OpenAI synthesis successful: "
                f"{len(audio_bytes)} bytes, ~{duration_ms}ms"
            )

            return result

        except OpenAIError as e:
            logger.error(f"[{request_id}] OpenAI synthesis failed: {str(e)}")
            raise TTSException(
                message=f"OpenAI synthesis failed: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                cause=e,
                details={"provider": "openai", "voice": voice_id}
            )
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
            raise TTSException(
                message=f"Synthesis error: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                cause=e
            )

    async def synthesize_stream(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio using OpenAI's streaming API.

        Enables lower latency by streaming audio chunks as they're generated.

        Args:
            text: Text to synthesize
            config: Optional TTS configuration

        Yields:
            Audio chunks as bytes

        Raises:
            TTSException: If synthesis fails
        """
        request_id = generate_request_id()
        logger.info(f"[{request_id}] OpenAI streaming synthesis: {len(text)} chars")

        # Sanitize text
        sanitized_text = sanitize_text_for_tts(text)

        # Get voice and model
        voice_id = (config.voice_id if config else None) or self._default_voice
        model = self._default_tts_model

        # Get instructions if provided
        instructions = None
        if config and hasattr(config, 'instructions') and config.instructions:
            instructions = config.instructions

        try:
            # Call OpenAI streaming API
            async with self._client.audio.speech.with_streaming_response.create(
                model=model,
                voice=voice_id,
                input=sanitized_text,
                instructions=instructions,
                response_format="wav"  # WAV/PCM for lowest latency
            ) as response:
                # Stream chunks
                chunk_count = 0
                async for chunk in response.iter_bytes(chunk_size=4096):
                    chunk_count += 1
                    yield chunk

                logger.info(
                    f"[{request_id}] OpenAI streaming synthesis complete: "
                    f"{chunk_count} chunks"
                )

        except OpenAIError as e:
            logger.error(f"[{request_id}] OpenAI streaming synthesis failed: {str(e)}")
            raise TTSException(
                message=f"OpenAI streaming synthesis failed: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                cause=e,
                details={"provider": "openai", "voice": voice_id}
            )
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
            raise TTSException(
                message=f"Streaming synthesis error: {str(e)}",
                error_code=VoiceErrorCode.TTS_SYNTHESIS_FAILED,
                cause=e
            )

    async def list_voices(self) -> List[VoiceInfo]:
        """
        Get list of available OpenAI TTS voices.

        Returns:
            List of 10 available voices with metadata
        """
        voices = []

        for voice_id, voice_data in OPENAI_VOICES.items():
            voices.append(VoiceInfo(
                voice_id=voice_id,
                name=voice_data["name"],
                category="premade",
                labels=VoiceLabels(
                    gender=voice_data.get("gender"),
                    accent="american",
                    age="adult",
                    use_case=voice_data.get("style"),
                    description=voice_data["description"]
                )
            ))

        return voices

    async def health_check(self) -> ProviderHealthStatus:
        """
        Check OpenAI API health and connectivity.

        Returns:
            ProviderHealthStatus with availability information
        """
        try:
            # Make a minimal API call to check connectivity
            # List models as a lightweight check
            models = await self._client.models.list()

            return ProviderHealthStatus(
                healthy=True,
                provider="openai",
                message="OpenAI API is available",
                details={
                    "api_available": True,
                    "models_count": len(list(models))
                }
            )

        except OpenAIError as e:
            logger.warning(f"OpenAI health check failed: {str(e)}")
            return ProviderHealthStatus(
                healthy=False,
                provider="openai",
                message=f"OpenAI API unavailable: {str(e)}",
                details={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"OpenAI health check error: {str(e)}", exc_info=True)
            return ProviderHealthStatus(
                healthy=False,
                provider="openai",
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)}
            )
