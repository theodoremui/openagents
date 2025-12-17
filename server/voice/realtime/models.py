"""
Real-time voice models - imports from parent voice module to avoid duplication.

All models are defined in server.voice.models to ensure consistency between
async and real-time voice systems.
"""

from server.voice.models import (
    # Re-export models from parent voice module
    AgentType,
    VoiceState,
    RealtimeSessionRequest,
    RealtimeSessionResponse,
    RealtimeSessionStatus,
    RealtimeSession,
    # Also re-export base models that may be needed
    VoiceConfigUpdate,
    VoiceConfigResponse,
)

__all__ = [
    "AgentType",
    "VoiceState",
    "RealtimeSessionRequest",
    "RealtimeSessionResponse",
    "RealtimeSessionStatus",
    "RealtimeSession",
    "VoiceConfigUpdate",
    "VoiceConfigResponse",
]
