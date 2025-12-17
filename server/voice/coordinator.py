"""
Voice Coordinator

Orchestrates voice operations across multiple providers using the Strategy pattern.

Features:
- Dynamic provider selection based on preferences
- Automatic fallback on provider failure
- Cost optimization (select cheapest provider that meets requirements)
- Quality optimization (select best provider for quality-sensitive operations)
- A/B testing support
- Provider health monitoring

Architecture:
- Strategy Pattern: Runtime provider selection
- Dependency Injection: Providers injected at initialization
- Fallback Chain: Graceful degradation on provider failures
"""

import logging
from typing import Optional, List, Dict, AsyncIterator
from enum import Enum
import asyncio

from .providers import IVoiceProvider, ProviderType
from .providers.openai_provider import OpenAIProvider
from .providers.elevenlabs_provider import ElevenLabsProvider
from .models import (
    TranscriptResult,
    AudioResult,
    VoiceInfo,
    TTSConfig,
    STTConfig,
    HealthStatus
)
from .exceptions import (
    VoiceException,
    VoiceServiceException,
    VoiceErrorCode
)

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Provider selection strategies"""
    COST_OPTIMIZED = "cost_optimized"      # Choose cheapest provider
    QUALITY_OPTIMIZED = "quality_optimized"  # Choose best quality
    LATENCY_OPTIMIZED = "latency_optimized"  # Choose fastest
    EXPLICIT = "explicit"                    # User-specified provider


class ProviderPreference:
    """
    User preferences for provider selection.

    Allows fine-grained control over which provider to use based on
    operation type, quality requirements, cost constraints, etc.
    """

    def __init__(
        self,
        strategy: SelectionStrategy = SelectionStrategy.COST_OPTIMIZED,  # OpenAI first (reliable)
        preferred_provider: Optional[ProviderType] = None,
        fallback_enabled: bool = True,
        max_cost_per_1k_chars: Optional[float] = None,
        min_quality_score: Optional[float] = None
    ):
        self.strategy = strategy
        self.preferred_provider = preferred_provider
        self.fallback_enabled = fallback_enabled
        self.max_cost_per_1k_chars = max_cost_per_1k_chars
        self.min_quality_score = min_quality_score


class VoiceCoordinator:
    """
    Orchestrates voice operations across multiple providers.

    Responsibilities:
    - Provider lifecycle management (initialization, health checks)
    - Dynamic provider selection based on preferences
    - Fallback handling on provider failures
    - Aggregated voice catalog from all providers
    - Performance monitoring and logging

    Usage:
        coordinator = VoiceCoordinator()

        # Transcribe with automatic provider selection
        result = await coordinator.transcribe(audio_data)

        # Synthesize with specific provider
        result = await coordinator.synthesize(
            text="Hello",
            preferences=ProviderPreference(
                preferred_provider=ProviderType.OPENAI
            )
        )

        # Synthesize with fallback
        result = await coordinator.synthesize(
            text="Hello",
            preferences=ProviderPreference(
                preferred_provider=ProviderType.ELEVENLABS,
                fallback_enabled=True
            )
        )
    """

    def __init__(
        self,
        providers: Optional[Dict[ProviderType, IVoiceProvider]] = None
    ):
        """
        Initialize coordinator with providers.

        Args:
            providers: Optional dict of providers. If not provided, initializes
                      OpenAI and ElevenLabs providers automatically.

        Raises:
            VoiceServiceException: If no providers are available.
        """
        self._providers: Dict[ProviderType, IVoiceProvider] = {}

        if providers:
            self._providers = providers
        else:
            # Initialize default providers
            self._initialize_default_providers()

        if not self._providers:
            raise VoiceServiceException(
                message="No voice providers available",
                error_code=VoiceErrorCode.NO_PROVIDERS_AVAILABLE
            )

        logger.info(
            f"VoiceCoordinator initialized with providers: "
            f"{list(self._providers.keys())}"
        )

    def _initialize_default_providers(self):
        """Initialize OpenAI and ElevenLabs providers."""
        # Try to initialize OpenAI
        try:
            self._providers[ProviderType.OPENAI] = OpenAIProvider()
            logger.info("OpenAI provider initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI provider: {str(e)}")

        # Try to initialize ElevenLabs
        try:
            self._providers[ProviderType.ELEVENLABS] = ElevenLabsProvider()
            logger.info("ElevenLabs provider initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize ElevenLabs provider: {str(e)}")

    def _select_provider_for_transcription(
        self,
        preferences: Optional[ProviderPreference] = None
    ) -> ProviderType:
        """
        Select best provider for transcription based on preferences.

        Selection Logic:
        - EXPLICIT: Use preferred_provider if specified
        - COST_OPTIMIZED: Use OpenAI (cheaper)
        - QUALITY_OPTIMIZED: Use ElevenLabs (higher quality)
        - LATENCY_OPTIMIZED: Use OpenAI (faster API)

        Args:
            preferences: Provider selection preferences

        Returns:
            Selected provider type

        Raises:
            VoiceServiceException: If no suitable provider found
        """
        if not preferences:
            preferences = ProviderPreference()

        # Explicit provider selection
        if preferences.strategy == SelectionStrategy.EXPLICIT:
            if preferences.preferred_provider and preferences.preferred_provider in self._providers:
                return preferences.preferred_provider
            raise VoiceServiceException(
                message=f"Preferred provider {preferences.preferred_provider} not available",
                error_code=VoiceErrorCode.PROVIDER_NOT_AVAILABLE
            )

        # Strategy-based selection
        if preferences.strategy == SelectionStrategy.COST_OPTIMIZED:
            # OpenAI: $0.006/min, ElevenLabs: $0.015/min
            if ProviderType.OPENAI in self._providers:
                return ProviderType.OPENAI
            elif ProviderType.ELEVENLABS in self._providers:
                return ProviderType.ELEVENLABS

        elif preferences.strategy == SelectionStrategy.QUALITY_OPTIMIZED:
            # ElevenLabs has higher transcription quality
            if ProviderType.ELEVENLABS in self._providers:
                return ProviderType.ELEVENLABS
            elif ProviderType.OPENAI in self._providers:
                return ProviderType.OPENAI

        elif preferences.strategy == SelectionStrategy.LATENCY_OPTIMIZED:
            # OpenAI typically has lower latency
            if ProviderType.OPENAI in self._providers:
                return ProviderType.OPENAI
            elif ProviderType.ELEVENLABS in self._providers:
                return ProviderType.ELEVENLABS

        # Fallback: return first available provider
        if self._providers:
            return list(self._providers.keys())[0]

        raise VoiceServiceException(
            message="No providers available for transcription",
            error_code=VoiceErrorCode.NO_PROVIDERS_AVAILABLE
        )

    def _select_provider_for_synthesis(
        self,
        preferences: Optional[ProviderPreference] = None
    ) -> ProviderType:
        """
        Select best provider for synthesis based on preferences.

        Selection Logic:
        - EXPLICIT: Use preferred_provider if specified
        - COST_OPTIMIZED: Use OpenAI ($0.012/1K chars vs $0.30/1K chars)
        - QUALITY_OPTIMIZED: Use ElevenLabs (premium quality)
        - LATENCY_OPTIMIZED: Use OpenAI (faster)

        Args:
            preferences: Provider selection preferences

        Returns:
            Selected provider type

        Raises:
            VoiceServiceException: If no suitable provider found
        """
        if not preferences:
            preferences = ProviderPreference()

        # Explicit provider selection
        if preferences.strategy == SelectionStrategy.EXPLICIT:
            if preferences.preferred_provider and preferences.preferred_provider in self._providers:
                return preferences.preferred_provider
            raise VoiceServiceException(
                message=f"Preferred provider {preferences.preferred_provider} not available",
                error_code=VoiceErrorCode.PROVIDER_NOT_AVAILABLE
            )

        # Strategy-based selection
        if preferences.strategy == SelectionStrategy.COST_OPTIMIZED:
            # OpenAI: $0.012/1K chars, ElevenLabs: $0.30/1K chars
            if ProviderType.OPENAI in self._providers:
                return ProviderType.OPENAI
            elif ProviderType.ELEVENLABS in self._providers:
                return ProviderType.ELEVENLABS

        elif preferences.strategy == SelectionStrategy.QUALITY_OPTIMIZED:
            # ElevenLabs has superior voice quality
            if ProviderType.ELEVENLABS in self._providers:
                return ProviderType.ELEVENLABS
            elif ProviderType.OPENAI in self._providers:
                return ProviderType.OPENAI

        elif preferences.strategy == SelectionStrategy.LATENCY_OPTIMIZED:
            # OpenAI typically faster
            if ProviderType.OPENAI in self._providers:
                return ProviderType.OPENAI
            elif ProviderType.ELEVENLABS in self._providers:
                return ProviderType.ELEVENLABS

        # Fallback: return first available provider
        if self._providers:
            return list(self._providers.keys())[0]

        raise VoiceServiceException(
            message="No providers available for synthesis",
            error_code=VoiceErrorCode.NO_PROVIDERS_AVAILABLE
        )

    def _get_fallback_chain(
        self,
        primary_provider: ProviderType
    ) -> List[ProviderType]:
        """
        Get fallback providers in order of preference.

        Fallback Order:
        1. Primary provider (specified)
        2. OpenAI (cost-effective, reliable)
        3. ElevenLabs (premium quality)
        4. Any other available providers

        Args:
            primary_provider: Primary provider to try first

        Returns:
            List of provider types in fallback order
        """
        fallback_chain = [primary_provider]

        # Add OpenAI as fallback (if not primary)
        if primary_provider != ProviderType.OPENAI and ProviderType.OPENAI in self._providers:
            fallback_chain.append(ProviderType.OPENAI)

        # Add ElevenLabs as fallback (if not primary and not already added)
        if primary_provider != ProviderType.ELEVENLABS and ProviderType.ELEVENLABS in self._providers:
            fallback_chain.append(ProviderType.ELEVENLABS)

        # Add any other providers
        for provider_type in self._providers.keys():
            if provider_type not in fallback_chain:
                fallback_chain.append(provider_type)

        return fallback_chain

    async def transcribe(
        self,
        audio_data: bytes,
        config: Optional[STTConfig] = None,
        preferences: Optional[ProviderPreference] = None
    ) -> TranscriptResult:
        """
        Transcribe audio with automatic provider selection and fallback.

        Args:
            audio_data: Raw audio bytes
            config: Optional STT configuration
            preferences: Provider selection preferences

        Returns:
            TranscriptResult with text and metadata

        Raises:
            VoiceException: If all providers fail
        """
        if not preferences:
            preferences = ProviderPreference()

        # Select primary provider
        primary_provider = self._select_provider_for_transcription(preferences)

        # Get fallback chain
        fallback_chain = self._get_fallback_chain(primary_provider) if preferences.fallback_enabled else [primary_provider]

        logger.info(
            f"Transcription attempt with fallback chain: {fallback_chain}"
        )

        # Try each provider in fallback chain
        last_error = None
        for provider_type in fallback_chain:
            try:
                provider = self._providers[provider_type]
                logger.info(f"Attempting transcription with {provider_type.value}")

                result = await provider.transcribe(audio_data, config)

                logger.info(
                    f"Transcription successful with {provider_type.value}: "
                    f"{len(result.text)} chars"
                )

                return result

            except Exception as e:
                logger.warning(
                    f"Transcription failed with {provider_type.value}: {str(e)}"
                )
                last_error = e
                continue

        # All providers failed
        raise VoiceServiceException(
            message=f"Transcription failed with all providers",
            error_code=VoiceErrorCode.ALL_PROVIDERS_FAILED,
            cause=last_error,
            details={"attempted_providers": [p.value for p in fallback_chain]}
        )

    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None,
        preferences: Optional[ProviderPreference] = None
    ) -> AudioResult:
        """
        Synthesize speech with automatic provider selection and fallback.

        Args:
            text: Text to synthesize
            config: Optional TTS configuration
            preferences: Provider selection preferences

        Returns:
            AudioResult with audio data

        Raises:
            VoiceException: If all providers fail
        """
        if not preferences:
            preferences = ProviderPreference()

        # Select primary provider
        primary_provider = self._select_provider_for_synthesis(preferences)

        # Get fallback chain
        fallback_chain = self._get_fallback_chain(primary_provider) if preferences.fallback_enabled else [primary_provider]

        logger.info(
            f"Synthesis attempt with fallback chain: {fallback_chain}"
        )

        # Try each provider in fallback chain
        last_error = None
        for provider_type in fallback_chain:
            try:
                provider = self._providers[provider_type]
                logger.info(f"Attempting synthesis with {provider_type.value}")

                result = await provider.synthesize(text, config)

                logger.info(
                    f"Synthesis successful with {provider_type.value}: "
                    f"{len(result.audio_data)} bytes"
                )

                return result

            except Exception as e:
                logger.warning(
                    f"Synthesis failed with {provider_type.value}: {str(e)}"
                )
                last_error = e
                continue

        # All providers failed
        raise VoiceServiceException(
            message=f"Synthesis failed with all providers",
            error_code=VoiceErrorCode.ALL_PROVIDERS_FAILED,
            cause=last_error,
            details={"attempted_providers": [p.value for p in fallback_chain]}
        )

    async def synthesize_stream(
        self,
        text: str,
        config: Optional[TTSConfig] = None,
        preferences: Optional[ProviderPreference] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio with automatic provider selection.

        Note: Fallback not supported for streaming (would require buffering).

        Args:
            text: Text to synthesize
            config: Optional TTS configuration
            preferences: Provider selection preferences

        Yields:
            Audio chunks as bytes

        Raises:
            VoiceException: If synthesis fails
        """
        if not preferences:
            preferences = ProviderPreference()

        # Select provider
        provider_type = self._select_provider_for_synthesis(preferences)
        provider = self._providers[provider_type]

        logger.info(f"Streaming synthesis with {provider_type.value}")

        try:
            async for chunk in provider.synthesize_stream(text, config):
                yield chunk

            logger.info(f"Streaming synthesis complete with {provider_type.value}")

        except Exception as e:
            logger.error(
                f"Streaming synthesis failed with {provider_type.value}: {str(e)}"
            )
            raise VoiceServiceException(
                message=f"Streaming synthesis failed: {str(e)}",
                error_code=VoiceErrorCode.TTS_FAILED,
                cause=e,
                details={"provider": provider_type.value}
            )

    async def list_voices(
        self,
        provider_type: Optional[ProviderType] = None
    ) -> List[VoiceInfo]:
        """
        Get available voices from provider(s).

        Args:
            provider_type: Optional provider to query. If None, returns voices from all providers.

        Returns:
            List of VoiceInfo objects

        Raises:
            VoiceException: If voice list retrieval fails
        """
        if provider_type:
            # Get voices from specific provider
            if provider_type not in self._providers:
                raise VoiceServiceException(
                    message=f"Provider {provider_type.value} not available",
                    error_code=VoiceErrorCode.PROVIDER_NOT_AVAILABLE
                )

            provider = self._providers[provider_type]
            return await provider.list_voices()

        # Get voices from all providers
        all_voices = []
        for provider_type, provider in self._providers.items():
            try:
                voices = await provider.list_voices()
                all_voices.extend(voices)
                logger.info(f"Fetched {len(voices)} voices from {provider_type.value}")
            except Exception as e:
                logger.warning(f"Failed to fetch voices from {provider_type.value}: {str(e)}")
                continue

        return all_voices

    async def health_check(self) -> Dict[str, HealthStatus]:
        """
        Check health of all providers.

        Returns:
            Dict mapping provider type to health status
        """
        health_status = {}

        # Check each provider concurrently
        tasks = {
            provider_type: provider.health_check()
            for provider_type, provider in self._providers.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (provider_type, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                health_status[provider_type.value] = HealthStatus(
                    healthy=False,
                    provider=provider_type.value,
                    message=f"Health check failed: {str(result)}"
                )
            else:
                health_status[provider_type.value] = result

        return health_status

    def get_available_providers(self) -> List[ProviderType]:
        """Get list of available provider types."""
        return list(self._providers.keys())

    def has_provider(self, provider_type: ProviderType) -> bool:
        """Check if a specific provider is available."""
        return provider_type in self._providers
