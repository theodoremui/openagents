"""
Pydantic Data Models for Voice Module

Defines all request/response models, configuration schemas, and data transfer objects
for the voice service.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime


# ============================================================================
# Enums
# ============================================================================

class OutputFormat(str, Enum):
    """Supported audio output formats."""
    MP3_44100_128 = "mp3_44100_128"
    MP3_22050_32 = "mp3_22050_32"
    PCM_16000 = "pcm_16000"
    PCM_22050 = "pcm_22050"
    PCM_24000 = "pcm_24000"
    PCM_44100 = "pcm_44100"


class TTSModel(str, Enum):
    """Available TTS models."""
    MULTILINGUAL_V2 = "eleven_multilingual_v2"
    FLASH_V2_5 = "eleven_flash_v2_5"
    TURBO_V2_5 = "eleven_turbo_v2_5"


class STTModel(str, Enum):
    """Available STT models."""
    SCRIBE_V1 = "scribe_v1"
    SCRIBE_V1_EXPERIMENTAL = "scribe_v1_experimental"


class TimestampGranularity(str, Enum):
    """Timestamp granularity options."""
    WORD = "word"
    CHARACTER = "character"


class HealthStatus(str, Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ProviderType(str, Enum):
    """Available voice providers."""
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"
    LIVEKIT = "livekit"


class SelectionStrategy(str, Enum):
    """Provider selection strategies."""
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    EXPLICIT = "explicit"


# ============================================================================
# Request Models
# ============================================================================

class ProviderPreferenceRequest(BaseModel):
    """Request model for provider selection preferences."""
    strategy: SelectionStrategy = Field(default=SelectionStrategy.COST_OPTIMIZED)
    preferred_provider: Optional[ProviderType] = Field(default=None)
    fallback_enabled: bool = Field(default=True)
    max_cost_per_request: Optional[float] = Field(default=None, ge=0.0)


class SynthesizeRequest(BaseModel):
    """Request model for text-to-speech synthesis."""
    text: str = Field(..., min_length=1, max_length=5000)
    voice_id: Optional[str] = Field(default=None)
    model_id: Optional[TTSModel] = Field(default=None)
    output_format: Optional[OutputFormat] = Field(default=None)
    stability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    similarity_boost: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    style: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    use_speaker_boost: Optional[bool] = Field(default=None)
    profile_name: Optional[str] = Field(default=None)
    provider_preferences: Optional[ProviderPreferenceRequest] = Field(default=None)

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('text cannot be empty or whitespace only')
        return v


class TranscribeRequest(BaseModel):
    """Request model for speech-to-text transcription."""
    language_code: Optional[str] = Field(default=None)
    model_id: Optional[STTModel] = Field(default=None)
    tag_audio_events: bool = Field(default=False)
    timestamps_granularity: TimestampGranularity = Field(default=TimestampGranularity.WORD)
    diarize: bool = Field(default=False)
    max_speakers: Optional[int] = Field(default=None, ge=1, le=32)
    provider_preferences: Optional[ProviderPreferenceRequest] = Field(default=None)


# ============================================================================
# Response Models
# ============================================================================

class WordTimestamp(BaseModel):
    """Word-level timestamp information."""
    word: str
    start: float = Field(..., ge=0.0)
    end: float = Field(..., ge=0.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    speaker: Optional[str] = Field(default=None)


class TranscriptResult(BaseModel):
    """Result of speech-to-text transcription."""
    text: str
    words: List[WordTimestamp] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    language_detected: Optional[str] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None, ge=0)
    audio_events: List[Dict[str, Any]] = Field(default_factory=list)


class TranscriptResponse(BaseModel):
    """API response for transcription endpoint."""
    success: bool = Field(default=True)
    result: TranscriptResult
    request_id: str
    processing_time_ms: int = Field(..., ge=0)


class AudioResult(BaseModel):
    """Result of text-to-speech synthesis."""
    audio_data: bytes
    content_type: str = Field(default="audio/mpeg")
    duration_ms: Optional[int] = Field(default=None, ge=0)
    request_id: str
    character_count: int = Field(..., ge=0)


class VoiceLabels(BaseModel):
    """Voice characteristic labels."""
    accent: Optional[str] = Field(default=None)
    age: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None)
    use_case: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)


class VoiceInfo(BaseModel):
    """Information about an available voice."""
    voice_id: str
    name: str
    category: Optional[str] = Field(default=None)
    labels: VoiceLabels = Field(default_factory=VoiceLabels)
    preview_url: Optional[str] = Field(default=None)
    available_for_tiers: List[str] = Field(default_factory=list)


class VoiceConfigResponse(BaseModel):
    """API response for configuration endpoints."""
    config: Dict[str, Any]
    last_updated: datetime
    validation: Optional[Dict[str, Any]] = Field(default=None)


class VoiceConfigUpdate(BaseModel):
    """Request model for configuration updates."""
    config: Dict[str, Any]
    validate_only: bool = Field(default=False)


class HealthResponse(BaseModel):
    """Health check response."""
    status: HealthStatus
    elevenlabs_connected: bool
    config_loaded: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class ProviderHealthStatus(BaseModel):
    """Provider-specific health check status."""
    healthy: bool
    provider: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Configuration Models
# ============================================================================

class TTSConfig(BaseModel):
    """
    Text-to-Speech configuration model.

    Supports both OpenAI (default) and ElevenLabs providers.

    OpenAI TTS (default):
    - voice_id: Voice name (alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer)
    - model_id: gpt-4o-mini-tts (recommended), tts-1, tts-1-hd
    - speed: Playback speed (0.25 - 4.0)
    - output_format: mp3, opus, aac, flac, wav, pcm
    - instructions: Optional voice control instructions

    ElevenLabs TTS (optional, for premium quality):
    - voice_id: ElevenLabs voice ID
    - model_id: eleven_multilingual_v2, eleven_flash_v2_5, eleven_turbo_v2_5
    - stability: Voice stability (0.0 - 1.0)
    - similarity_boost: Voice similarity (0.0 - 1.0)
    - style: Style exaggeration (0.0 - 1.0)
    - use_speaker_boost: Clarity enhancement
    """
    # Common fields
    voice_id: str = Field(default="coral", description="Voice identifier (OpenAI: voice name, ElevenLabs: voice ID)")
    model_id: str = Field(default="gpt-4o-mini-tts", description="Model identifier")
    output_format: str = Field(default="mp3", description="Audio output format")
    max_text_length: int = Field(default=4096, ge=1, le=10000, description="Maximum text length per request")
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds")

    # OpenAI-specific fields (work with OpenAI provider)
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="OpenAI: Playback speed")
    instructions: Optional[str] = Field(default=None, description="OpenAI: Voice control instructions (tone, speed, emotion)")

    # ElevenLabs-specific fields (work with ElevenLabs provider, optional)
    stability: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="ElevenLabs: Voice stability")
    similarity_boost: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="ElevenLabs: Voice similarity")
    style: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="ElevenLabs: Style exaggeration")
    use_speaker_boost: Optional[bool] = Field(default=None, description="ElevenLabs: Clarity enhancement")


class STTConfig(BaseModel):
    """
    Speech-to-Text configuration model.

    Supports both OpenAI (default) and ElevenLabs providers.

    OpenAI STT (default):
    - model_id: gpt-4o-transcribe (best quality), whisper-1 (cheapest), gpt-4o-mini-transcribe (balance)
    - language_code: ISO 639-1 language code (null = auto-detect)
    - response_format: json, text, srt, verbose_json, vtt
    - temperature: Sampling temperature (0.0 - 1.0)
    - timestamp_granularities: ["word"] or ["segment"]
    - prompt: Optional context to improve accuracy

    ElevenLabs STT (optional, for premium quality):
    - model_id: scribe_v1, scribe_v1_experimental
    - tag_audio_events: Tag laughter, applause, etc.
    - diarize: Speaker diarization (who spoke when)
    - max_speakers: Maximum speakers to detect
    """
    # Common fields
    model_id: str = Field(default="gpt-4o-transcribe", description="Model identifier")
    language_code: Optional[str] = Field(default=None, description="Language code (null = auto-detect)")
    timeout: int = Field(default=60, ge=5, le=300, description="Request timeout in seconds")

    # Timestamp configuration (common, but different formats)
    timestamps_granularity: str = Field(default="word", description="Timestamp granularity: word or character")

    # OpenAI-specific fields
    response_format: Optional[str] = Field(default="verbose_json", description="OpenAI: Response format (json, text, srt, verbose_json, vtt)")
    temperature: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, description="OpenAI: Sampling temperature")
    prompt: Optional[str] = Field(default=None, description="OpenAI: Optional context prompt")
    timestamp_granularities: Optional[List[str]] = Field(default=["word"], description="OpenAI: Timestamp types ([word], [segment])")

    # ElevenLabs-specific fields (optional)
    tag_audio_events: Optional[bool] = Field(default=None, description="ElevenLabs: Tag audio events (laughter, applause)")
    diarize: Optional[bool] = Field(default=None, description="ElevenLabs: Speaker diarization")
    max_speakers: Optional[int] = Field(default=None, ge=1, le=32, description="ElevenLabs: Maximum speakers")

    @field_validator('timestamps_granularity')
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        if v not in ('word', 'character', 'segment'):
            raise ValueError('timestamps_granularity must be word, character, or segment')
        return v


class VoiceProfile(BaseModel):
    """
    Named voice profile configuration.

    Supports both OpenAI and ElevenLabs providers.

    Example OpenAI profile:
    - provider: "openai"
    - voice_id: "coral" (or any OpenAI voice name)
    - model_id: "gpt-4o-mini-tts"
    - speed: 1.0
    - instructions: "Use a warm, conversational tone"

    Example ElevenLabs profile:
    - provider: "elevenlabs"
    - voice_id: "21m00Tcm4TlvDq8ikWAM" (ElevenLabs voice ID)
    - model_id: "eleven_multilingual_v2"
    - stability: 0.7
    - similarity_boost: 0.8
    """
    # Common fields
    voice_id: str = Field(..., description="Voice identifier")
    provider: Optional[str] = Field(default="openai", description="Provider: openai or elevenlabs")
    model_id: str = Field(default="gpt-4o-mini-tts", description="Model identifier")

    # OpenAI-specific fields
    speed: Optional[float] = Field(default=None, ge=0.25, le=4.0, description="OpenAI: Playback speed")
    instructions: Optional[str] = Field(default=None, description="OpenAI: Voice control instructions")

    # ElevenLabs-specific fields
    stability: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="ElevenLabs: Voice stability")
    similarity_boost: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="ElevenLabs: Voice similarity")
    style: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="ElevenLabs: Style exaggeration")
    use_speaker_boost: Optional[bool] = Field(default=None, description="ElevenLabs: Clarity enhancement")


class CacheConfig(BaseModel):
    """Cache configuration."""
    voice_list_ttl: int = Field(default=3600, ge=60)
    enable_response_cache: bool = Field(default=False)
    response_cache_ttl: int = Field(default=86400, ge=3600)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    log_api_calls: bool = Field(default=True)
    log_audio_data: bool = Field(default=False)
    level: str = Field(default="INFO")


class VoiceConfig(BaseModel):
    """
    Root voice configuration model.

    Supports multi-provider voice system with OpenAI (default) and ElevenLabs.
    """
    enabled: bool = Field(default=True, description="Enable/disable voice features")
    default_provider: str = Field(default="openai", description="Default voice provider (openai or elevenlabs)")
    default_strategy: str = Field(default="cost_optimized", description="Default provider selection strategy")
    enable_fallback: bool = Field(default=True, description="Enable automatic provider fallback on errors")

    tts: TTSConfig = Field(default_factory=TTSConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    voice_profiles: Dict[str, VoiceProfile] = Field(default_factory=dict)
    default_profile: str = Field(default="default", description="Default voice profile name")
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ValidationResult(BaseModel):
    """Configuration validation result."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Real-Time Voice Models (LiveKit Integration)
# ============================================================================

class AgentType(str, Enum):
    """Type of agent to use for real-time voice session."""
    MOE = "moe"  # Mixture of Experts (default)
    SMART_ROUTER = "smart_router"
    SINGLE_AGENT = "single_agent"


class VoiceState(str, Enum):
    """Possible states of a real-time voice agent during conversation."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    INITIALIZING = "initializing"
    LISTENING = "listening"
    PROCESSING = "processing"
    THINKING = "thinking"
    SPEAKING = "speaking"


class RealtimeSessionRequest(BaseModel):
    """Request to create a new real-time voice session."""

    model_config = {"populate_by_name": True}

    agent_type: AgentType = Field(
        default=AgentType.MOE,
        description="Type of agent to use (default: MOE)",
        alias="agentType"
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Specific agent ID (for SINGLE_AGENT type)",
        alias="agentId"
    )
    agent_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional agent configuration",
        alias="agentConfig"
    )
    initial_greeting: bool = Field(
        default=True,
        description="Whether agent should greet user initially",
        alias="initialGreeting"
    )


class RealtimeSessionResponse(BaseModel):
    """Response containing real-time session connection details."""

    model_config = {"populate_by_name": True}

    session_id: str = Field(description="Unique session identifier", alias="sessionId")
    room_name: str = Field(description="LiveKit room name", alias="roomName")
    token: str = Field(description="LiveKit access token for client connection")
    url: str = Field(description="LiveKit server WebSocket URL")


class RealtimeSessionStatus(BaseModel):
    """Current status of a real-time voice session."""
    session_id: str
    room_name: str
    is_active: bool
    participant_count: int
    agent_connected: bool
    agent_state: Optional[VoiceState] = None
    created_at: datetime
    duration_seconds: float


class RealtimeSession(BaseModel):
    """Internal session record for tracking active real-time sessions."""
    id: str
    user_id: str
    room_name: str
    token: str
    livekit_url: str
    agent_type: AgentType
    agent_id: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool = True
