"""
Real-time voice agent module using LiveKit Agents framework.

This module implements continuous, natural voice conversations using:
- LiveKit Agents framework for agent lifecycle management
- OpenAI STT (Speech-to-Text) for transcription
- OpenAI LLM for intelligence (routing through existing agent system)
- OpenAI TTS (Text-to-Speech) for voice synthesis
- WebRTC for reliable audio transport

Architecture: STT → LLM → TTS pipeline with VAD and turn detection.

Configuration is unified with async voice in config/voice_config.yaml under 'realtime' section.
"""

from .config import RealtimeVoiceConfig
from .models import (
    AgentType,
    VoiceState,
    RealtimeSessionRequest,
    RealtimeSessionResponse,
    RealtimeSessionStatus,
    RealtimeSession,
    VoiceConfigUpdate,
    VoiceConfigResponse,
)
from .exceptions import (
    RealtimeVoiceException,
    SessionLimitExceeded,
    SessionNotFound,
    LiveKitConnectionException,
)
from .service import RealtimeVoiceService

__all__ = [
    "RealtimeVoiceConfig",
    "AgentType",
    "VoiceState",
    "RealtimeSessionRequest",
    "RealtimeSessionResponse",
    "RealtimeSessionStatus",
    "RealtimeSession",
    "VoiceConfigUpdate",
    "VoiceConfigResponse",
    "RealtimeVoiceException",
    "SessionLimitExceeded",
    "SessionNotFound",
    "LiveKitConnectionException",
    "RealtimeVoiceService",
]
