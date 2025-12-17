"""
Buffered STT with Semantic Endpointing.

Wraps LiveKit STT to add semantic endpointing capabilities.
Currently implemented as a pass-through wrapper. Full semantic
endpointing will be implemented in a future version.

For now, semantic endpointing can be configured via VAD settings
in the LiveKit AgentSession configuration.
"""

from typing import Optional
from loguru import logger

try:
    from livekit.agents.stt import STT, STTCapabilities, SpeechEvent
    from livekit.agents import APIConnectOptions
    from livekit.agents.types import NOT_GIVEN, NotGivenOr
    from livekit.agents.utils import AudioBuffer
except ImportError:
    logger.error("livekit-agents not installed")
    raise


class BufferedSTT(STT):
    """
    Buffered STT wrapper with semantic endpointing.

    Currently implemented as a pass-through to the base STT.
    Semantic endpointing logic to be added in future iteration.

    Example:
        >>> base_stt = lk_openai.STT(model="whisper-1")
        >>> semantic_stt = BufferedSTT(base_stt, enable_semantic_endpointing=True)
        >>> # Use semantic_stt in AgentSession as drop-in replacement
    """

    def __init__(
        self,
        base_stt: STT,
        enable_semantic_endpointing: bool = True,
        min_silence_ambiguous: float = 0.6,
        min_silence_complete: float = 1.0,
        max_buffer_duration: float = 30.0,
        enable_logging: bool = False,
    ):
        """
        Initialize buffered STT with semantic endpointing.

        Args:
            base_stt: Underlying STT provider (e.g., OpenAI Whisper)
            enable_semantic_endpointing: Enable semantic analysis (currently no-op)
            min_silence_ambiguous: Silence threshold for ambiguous utterances (seconds)
            min_silence_complete: Silence threshold for complete utterances (seconds)
            max_buffer_duration: Maximum duration to buffer before forcing endpoint (safety)
            enable_logging: Enable detailed logging for debugging
        """
        # Initialize STT capabilities from base STT
        super().__init__(
            capabilities=base_stt.capabilities if hasattr(base_stt, 'capabilities') else STTCapabilities(
                streaming=True,
                interim_results=True
            )
        )

        self._base_stt = base_stt
        self._enable_semantic = enable_semantic_endpointing
        self._max_buffer_duration = max_buffer_duration
        self._enable_logging = enable_logging

        if self._enable_semantic:
            logger.info(
                f"[BufferedSTT] Semantic endpointing configured "
                f"(ambiguous: {min_silence_ambiguous}s, complete: {min_silence_complete}s)"
            )
            logger.info("[BufferedSTT] Note: Full semantic endpointing will be implemented in future version")
        else:
            logger.info("[BufferedSTT] Semantic endpointing disabled")

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> SpeechEvent:
        """
        Implementation of STT recognition.

        Currently delegates directly to base STT.
        Semantic buffering will be added in future iteration.

        Args:
            buffer: Audio buffer from LiveKit
            language: Language code for recognition
            conn_options: API connection options

        Returns:
            SpeechEvent from base STT
        """
        # Delegate to base STT implementation
        return await self._base_stt._recognize_impl(buffer, language=language, conn_options=conn_options)

    def reset_context(self) -> None:
        """
        Reset semantic context (for new user or session).

        Call this when starting a new conversation to clear history.
        """
        if self._enable_logging:
            logger.debug("[BufferedSTT] Context reset")

    async def aclose(self) -> None:
        """Clean up resources."""
        await self._base_stt.aclose()
