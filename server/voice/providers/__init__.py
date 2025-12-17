"""
Voice Providers Module

Unified provider interface and implementations for multiple voice services.
Supports OpenAI, ElevenLabs, and LiveKit providers via Strategy pattern.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List
from enum import Enum

from ..models import (
    TranscriptResult,
    AudioResult,
    VoiceInfo,
    TTSConfig,
    STTConfig,
    ProviderHealthStatus
)


class ProviderType(str, Enum):
    """Supported voice provider types"""
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"
    LIVEKIT = "livekit"


class IVoiceProvider(ABC):
    """
    Abstract interface for voice providers.

    All voice providers must implement this interface to ensure
    consistent behavior across different backends.

    Strategy Pattern:
    - Allows runtime provider selection
    - Enables fallback mechanisms
    - Facilitates A/B testing
    """

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Get provider type identifier"""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming synthesis"""
        pass

    @property
    @abstractmethod
    def supports_realtime(self) -> bool:
        """Whether provider supports real-time bidirectional voice"""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        config: Optional[STTConfig] = None
    ) -> TranscriptResult:
        """
        Convert audio to text (Speech-to-Text).

        Args:
            audio_data: Raw audio bytes (mp3, wav, webm, ogg, etc.)
            config: Optional STT configuration overrides

        Returns:
            TranscriptResult with text, word timestamps, and metadata

        Raises:
            VoiceException: If transcription fails
        """
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> AudioResult:
        """
        Convert text to audio (Text-to-Speech).

        Args:
            text: Text to synthesize
            config: Optional TTS configuration overrides

        Returns:
            AudioResult with audio data and metadata

        Raises:
            VoiceException: If synthesis fails
        """
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio chunks (Text-to-Speech).

        Enables lower latency by streaming audio as it's generated.

        Args:
            text: Text to synthesize
            config: Optional TTS configuration overrides

        Yields:
            Audio chunks as bytes

        Raises:
            VoiceException: If synthesis fails
        """
        pass

    @abstractmethod
    async def list_voices(self) -> List[VoiceInfo]:
        """
        Get list of available voices for this provider.

        Returns:
            List of VoiceInfo objects with voice metadata

        Raises:
            VoiceException: If voice list retrieval fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> ProviderHealthStatus:
        """
        Check provider health and connectivity.

        Returns:
            ProviderHealthStatus indicating provider availability
        """
        pass


__all__ = [
    "IVoiceProvider",
    "ProviderType",
]
