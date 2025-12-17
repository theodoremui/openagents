# Voice Module Implementation Guide

**Date**: December 13, 2025
**Status**: ✅ REST API Complete | ✅ Provider System Complete | ✅ OpenAI Default | ✅ Real-Time Voice Features | ⏳ LiveKit Full Integration Pending
**Version**: 2.3.0 - OpenAI-First Multi-Provider System with Thinking Fillers

---

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Implementation Status](#implementation-status)
4. [Design Decisions](#design-decisions)
5. [Provider System](#provider-system)
6. [Current Implementation (REST API)](#current-implementation-rest-api)
7. [Real-Time Extension (LiveKit)](#real-time-extension-livekit)
8. [Real-Time Voice Features](#real-time-voice-features)
9. [Quick Start Guide](#quick-start-guide)
10. [How-To Guides](#how-to-guides)
11. [API Reference](#api-reference)
12. [Configuration](#configuration)
13. [Provider Comparison](#provider-comparison)
14. [Testing](#testing)
15. [Troubleshooting](#troubleshooting)
16. [Examples](#examples)
17. [Migration Guide](#migration-guide)
18. [Future Roadmap](#future-roadmap)
19. [Summary](#summary)

---

## Introduction

The Voice Module provides Text-to-Speech (TTS) and Speech-to-Text (STT) capabilities for the OpenAgents platform, enabling natural voice interactions with AI agents.

### Features

- ✅ **Text-to-Speech (TTS)**: Convert agent responses to natural speech
- ✅ **Speech-to-Text (STT)**: Transcribe user voice input to text
- ✅ **Multi-Provider Support**: OpenAI (default) and ElevenLabs (premium) with automatic selection
- ✅ **Cost Optimization**: 96% cost savings with OpenAI as default provider
- ✅ **Automatic Fallback**: Graceful degradation when providers fail
- ✅ **Streaming Support**: Real-time audio streaming for low latency
- ✅ **Multiple Voice Profiles**: 6 pre-configured profiles (4 OpenAI + 2 ElevenLabs)
- ✅ **Configuration Management**: YAML-based config with hot-reload
- ✅ **REST API**: Complete CRUD endpoints for voice operations
- ✅ **Real-Time Voice Features**: Thinking fillers, chitchat detection, immediate TTS playback
- ⏳ **LiveKit Full Integration**: Complete real-time voice chat infrastructure (pending)

### Use Cases

1. **Quick Voice Commands**: "What's the weather today?" (REST API - 2-5s latency)
2. **Extended Conversations**: Multi-turn voice interactions (LiveKit - <500ms latency)
3. **File Transcription**: Upload audio files for transcription (REST API)
4. **Interactive Tutoring**: Real-time voice feedback and Q&A (LiveKit)

---

## Architecture Overview

### System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[React Components]
        B[VoiceContext]
        C[useVoice Hook]
        D[useRealtimeVoice Hook]
    end

    subgraph "Service Layer"
        E[VoiceApiClient<br/>REST]
        F[RealtimeVoiceClient<br/>WebSocket/RTC]
        G[VoiceCoordinator]
    end

    subgraph "Backend - FastAPI"
        H[REST Router<br/>/voice/*]
        I[WebSocket Router<br/>/voice/realtime/*]
        J[VoiceService<br/>REST Logic]
        K[RealtimeVoiceService<br/>WS/RTC Logic]
    end

    subgraph "Provider Layer"
        L[VoiceCoordinator<br/>Orchestration]
        M1[OpenAI Provider<br/>Whisper + TTS]
        M2[ElevenLabs Provider<br/>Scribe + Multilingual]
        M3[LiveKit Provider<br/>WebRTC - Future]
    end

    subgraph "External Services"
        N1[OpenAI API<br/>Whisper + gpt-4o-mini-tts]
        N2[ElevenLabs API<br/>REST + WebSocket]
        N3[LiveKit Cloud<br/>WebRTC]
        N4[OpenAI Agents<br/>LLM]
    end

    A --> B
    A --> C
    A --> D
    B --> G
    C --> E
    G --> L
    D --> F
    E --> H
    F --> I
    H --> J
    I --> K
    J --> L
    K --> L
    L --> M1
    L --> M2
    L --> M3
    M1 --> N1
    M2 --> N2
    M3 --> N3
    K --> N4

    style B fill:#999ccc
    style G fill:#999999
    style L fill:#777777,stroke:#333,stroke-width:4px
    style J fill:#898989
    style K fill:#8e8e8e
```

### Module Structure

```
server/voice/
├── __init__.py          # Module exports
├── models.py            # Pydantic data models (20+ models)
├── exceptions.py        # Custom exceptions with error codes
├── config.py            # YAML configuration management
├── client.py            # ElevenLabs SDK wrapper (legacy)
├── utils.py             # Utility functions
├── dependencies.py      # FastAPI dependency injection
├── service.py           # Business logic layer
├── coordinator.py       # VoiceCoordinator - Provider orchestration ✅
├── router.py            # REST API endpoints (8 endpoints)
├── providers/           # Provider implementations ✅
│   ├── __init__.py      # IVoiceProvider interface
│   ├── openai_provider.py      # OpenAI STT/TTS ✅
│   ├── elevenlabs_provider.py  # ElevenLabs wrapper ✅
│   └── livekit_provider.py     # LiveKit real-time (pending) ⏳
└── realtime/            # Real-time voice
    ├── thinking_filler.py  # Thinking filler service ✅
    ├── agent.py           # Voice agent with filler integration ✅
    ├── service.py         # RealtimeVoiceService (pending)
    ├── room_manager.py    # LiveKit room management (pending)
    └── router.py          # WebSocket endpoints (pending)

frontend_web/lib/
├── hooks/
│   ├── useAudioRecorder.ts
│   ├── useAudioPlayer.ts
│   ├── useVoice.ts
│   └── useRealtimeVoice.ts
├── services/
│   ├── VoiceApiClient.ts
│   └── RealtimeVoiceClient.ts
├── contexts/
│   └── VoiceContext.tsx
└── components/voice/
    ├── VoiceToggle.tsx
    ├── VoiceAnimation.tsx
    ├── VoiceSettings.tsx
    ├── VoiceInputPanel.tsx
    └── LiveKitVoiceChat.tsx
```

---

## Implementation Status

### Overall Status: **96% Complete** ✅

| Component | Status | Completeness | Notes |
|-----------|--------|--------------|-------|
| **Backend Voice Service** | ✅ Complete | 100% | All 18 requirements implemented |
| **Frontend Voice UI** | ✅ Complete | 95% | Core components functional |
| **Voice Configuration** | ✅ Complete | 100% | Multi-provider (OpenAI + ElevenLabs) |
| **Real-Time Voice Features** | ✅ Complete | 100% | Thinking fillers, chitchat detection (Dec 13, 2025) |
| **Testing** | ⚠️ Partial | 82% | 210+ frontend tests, 27 thinking filler tests, backend needs expansion |
| **Documentation** | ✅ Complete | 100% | Comprehensive docs, migration guides |

### Requirement Status (18 Total)

| # | Requirement | Status | Implementation |
|---|-------------|--------|----------------|
| 1 | Voice Client Integration | ✅ | `client.py` + `providers/` |
| 2 | Voice Service Layer | ✅ | `service.py` + `coordinator.py` |
| 3 | REST API Endpoints | ✅ | `router.py` (8 endpoints) |
| 4 | Configuration Management | ✅ | `config.py` + `voice_config.yaml` |
| 5 | Data Models | ✅ | `models.py` (20+ models) |
| 6 | Exception Handling | ✅ | `exceptions.py` (VoiceErrorCode enum) |
| 7 | Frontend Voice Toggle | ✅ | `VoiceToggle.tsx` |
| 8 | Frontend Voice Animation | ✅ | `VoiceAnimation.tsx` |
| 9 | Frontend Audio Recording | ✅ | `useAudioRecorder.ts` |
| 10 | Frontend Audio Playback | ✅ | `useAudioPlayer.ts` |
| 11 | Frontend Voice Context | ✅ | `VoiceContext.tsx` |
| 12 | Frontend Voice API Client | ✅ | `VoiceApiClient.ts` |
| 13 | Frontend Voice Settings | ⚠️ 60% | Basic UI (no YAML editor) |
| 14 | Chat Interface Integration | ✅ | `VoiceInputPanel.tsx` |
| 15 | Backend Unit Tests | ⚠️ 70% | Core tests complete |
| 16 | Backend Integration Tests | ⚠️ 60% | 35 router tests |
| 17 | Frontend Unit Tests | ✅ 80% | 210+ hook tests |
| 18 | Performance Optimization | ✅ | Streaming, caching, lazy-loading |

### Production Readiness

| Category | Status | Details |
|----------|--------|---------|
| **Core Functionality** | ✅ Ready | All 8 REST endpoints operational |
| **Multi-Provider** | ✅ Ready | OpenAI + ElevenLabs with fallback |
| **Error Handling** | ✅ Ready | Comprehensive error codes |
| **Health Monitoring** | ✅ Ready | `/voice/health` endpoint |
| **Logging** | ✅ Ready | Request/response logging |
| **Configuration** | ✅ Ready | Hot-reload YAML config |
| **Test Coverage** | ⚠️ 80% | Backend tests need expansion |

---

## Design Decisions

### Architecture Evaluation

The Voice Module architecture was systematically evaluated in **two phases**:

1. **Phase 1: REST vs Real-Time Architecture** (Initial Implementation)
   - **Selected**: Separate Service Pattern (98.3% score)
   - **Result**: Clean separation between `VoiceService` (REST) and `RealtimeVoiceService` (WebRTC)

2. **Phase 2: Provider System Architecture** (Current)
   - **Selected**: Unified Provider System with Strategy Pattern (94.7% score)
   - **Result**: Extensible provider system with `VoiceCoordinator` orchestrating OpenAI, ElevenLabs, and LiveKit providers

### Selected Architecture: Separate Services + Provider System

```mermaid
graph TD
    A[Frontend VoiceContext] -->|Mode: rest/realtime| B[VoiceCoordinator]
    C1[REST Router] --> C
    B -->|REST requests| C[VoiceService]
    B -->|WebSocket/RTC| D[RealtimeVoiceService]
    
    subgraph "Provider Layer"
        C --> E[Provider Selector]
        E --> F1[OpenAI Provider]
        E --> F2[ElevenLabs Provider]
        E --> F3[LiveKit Provider]
    end
    
    F1 --> G1[OpenAI API]
    F2 --> G2[ElevenLabs API]
    F3 --> G3[LiveKit Cloud]

    style B fill:#999999,stroke:#333,stroke-width:4px
    style C fill:#b2b2b2,stroke:#333,stroke-width:2px
    style D fill:#8f8f8f,stroke:#333,stroke-width:2px
    style E fill:#fff9c4,stroke:#333,stroke-width:3px
```

**Key Design Principles:**
- ✅ **Separation of Concerns**: REST and real-time services are independent
- ✅ **Provider Abstraction**: All providers implement `IVoiceProvider` interface
- ✅ **Strategy Pattern**: Intelligent provider selection based on cost, quality, or latency
- ✅ **Automatic Fallback**: Graceful degradation when providers fail
- ✅ **SOLID Principles**: Open/Closed, Dependency Inversion, Single Responsibility

---

## Provider System

The Voice Module supports multiple providers through a unified interface, with **OpenAI as the default** for cost optimization.

### Provider Architecture

```mermaid
graph TB
    subgraph "Unified Voice Architecture"
        A[VoiceCoordinator<br/>Orchestration Layer] --> B{Provider Selector<br/>Strategy Pattern}

        B --> |Cost Optimized| C[OpenAI Provider<br/>$0.012/1K chars TTS<br/>$0.006/min STT]
        B --> |Quality Optimized| D[ElevenLabs Provider<br/>$0.30/1K chars TTS<br/>$0.015/min STT]
        B --> |Real-time| E[LiveKit Provider<br/>WebRTC Rooms<br/>Future]

        C --> F[OpenAI API<br/>Whisper + gpt-4o-mini-tts]
        D --> G[ElevenLabs API<br/>Scribe + Multilingual]
        E --> H[LiveKit Cloud<br/>Real-time Voice]

        style A fill:#999999,stroke:#333,stroke-width:4px
        style B fill:#9e9e9e,stroke:#333,stroke-width:3px
        style C fill:#8c8c8c,stroke:#333,stroke-width:2px
        style D fill:#8a8a8a,stroke:#333,stroke-width:2px
        style E fill:#a9a9a9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    end
```

### Provider Interface

All providers implement the `IVoiceProvider` interface:

```python
# server/voice/providers/__init__.py

class IVoiceProvider(ABC):
    """Abstract interface for all voice providers"""

    @abstractmethod
    async def transcribe(audio_data, config) -> TranscriptResult:
        """Convert speech to text"""

    @abstractmethod
    async def synthesize(text, config) -> AudioResult:
        """Convert text to speech"""

    @abstractmethod
    async def synthesize_stream(text, config) -> AsyncIterator[bytes]:
        """Stream text to speech"""

    @abstractmethod
    async def list_voices() -> List[VoiceInfo]:
        """List available voices"""

    @abstractmethod
    async def health_check() -> HealthStatus:
        """Check provider health"""
```

### Available Providers

#### 1. OpenAI Provider ✅ Complete (Default)

**Features**:
- ✅ STT using Whisper (whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe)
- ✅ TTS using gpt-4o-mini-tts with 10 voices
- ✅ Word-level timestamps for transcriptions
- ✅ Instruction-based voice control (tone, speed, emotion)
- ✅ Streaming support for low-latency audio
- ✅ Comprehensive error handling

**Pricing**:
- STT: $0.006/minute (whisper-1), $0.01/minute (gpt-4o-transcribe)
- TTS: $0.012 per 1K characters

**File**: `server/voice/providers/openai_provider.py` (~580 lines)

**OpenAI Voice Models**:

| Model | Quality | Speed | Cost | Recommended |
|-------|---------|-------|------|-------------|
| **gpt-4o-mini-tts** | Excellent | Fast | $0.012/1K | ✅ Default TTS |
| **tts-1** | Good | Very fast | $0.015/1K | Budget streaming |
| **tts-1-hd** | Excellent | Moderate | $0.030/1K | High quality |
| **gpt-4o-transcribe** | Best | Fast | $0.01/min | ✅ Default STT |
| **whisper-1** | Good | Fast | $0.006/min | Budget option |

**Available Voices** (10 total):

| Voice | Gender | Style | Best For |
|-------|--------|-------|----------|
| **coral** | Female | Clear, cheerful | Default, general use |
| **echo** | Male | Deep, authoritative | Professional, business |
| **nova** | Female | Bright, energetic | Conversational, chat |
| **ballad** | Neutral | Expressive, dramatic | Storytelling, narration |
| **alloy** | Neutral | Balanced, neutral | Technical content |
| **ash** | Neutral | Smooth, warm | Calm, relaxed |
| **fable** | Neutral | Warm, engaging | Educational |
| **onyx** | Male | Deep, powerful | Announcements |
| **sage** | Neutral | Calm, wise | Meditation, guidance |
| **shimmer** | Female | Soft, gentle | Soothing content |

#### 2. ElevenLabs Provider ✅ Complete (Premium)

**Features**:
- ✅ Wraps existing `VoiceClient` for backward compatibility
- ✅ STT using ElevenLabs Scribe (multi-language, speaker diarization)
- ✅ TTS using ElevenLabs Multilingual v2 (premium quality)
- ✅ Voice settings control (stability, similarity, style)
- ✅ WebSocket streaming support

**Pricing**:
- STT: $0.015/minute
- TTS: $0.30 per 1K characters (premium quality)

**File**: `server/voice/providers/elevenlabs_provider.py` (~380 lines)

#### 3. LiveKit Provider ⏳ Pending

**Planned Features**:
- Real-time bidirectional voice communication
- LiveKit room management
- Agent worker integration
- Low-latency audio pipeline (<500ms)

**File**: `server/voice/providers/livekit_provider.py` (pending)

### Voice Profiles (6 Total)

| Profile | Provider | Voice | Use Case | Speed |
|---------|----------|-------|----------|-------|
| **default** | OpenAI | coral | General use, friendly | 1.0 |
| **professional** | OpenAI | echo | Business, authoritative | 0.9 |
| **conversational** | OpenAI | nova | Chat, energetic | 1.1 |
| **storytelling** | OpenAI | ballad | Narration, dramatic | 0.95 |
| **premium** | ElevenLabs | Rachel | Professional, high quality | - |
| **premium_casual** | ElevenLabs | Bella | Casual, friendly | - |

### VoiceCoordinator

The `VoiceCoordinator` orchestrates provider selection and manages automatic fallback:

```python
# server/voice/coordinator.py

from server.voice.coordinator import VoiceCoordinator, ProviderPreference, SelectionStrategy
from server.voice.providers import ProviderType

coordinator = VoiceCoordinator()

# Cost-optimized transcription (uses OpenAI)
result = await coordinator.transcribe(
    audio_data,
    preferences=ProviderPreference(
        strategy=SelectionStrategy.COST_OPTIMIZED
    )
)

# Quality-optimized synthesis (uses ElevenLabs)
result = await coordinator.synthesize(
    "Hello, world!",
    preferences=ProviderPreference(
        strategy=SelectionStrategy.QUALITY_OPTIMIZED,
        fallback_enabled=True  # Falls back to OpenAI if ElevenLabs fails
    )
)

# Explicit provider selection
result = await coordinator.synthesize(
    "Test",
    preferences=ProviderPreference(
        preferred_provider=ProviderType.OPENAI,
        fallback_enabled=False
    )
)
```

**Selection Strategies**:
- **COST_OPTIMIZED**: Choose cheapest provider (OpenAI for most cases)
- **QUALITY_OPTIMIZED**: Choose best quality (ElevenLabs for TTS)
- **LATENCY_OPTIMIZED**: Choose fastest provider
- **EXPLICIT**: Use user-specified provider

**Features**:
- ✅ Strategy-based provider selection
- ✅ Automatic fallback on provider failures
- ✅ Aggregated voice catalog from all providers
- ✅ Health monitoring for all providers

**File**: `server/voice/coordinator.py` (~550 lines)

### Dependency Injection

The DI system automatically initializes VoiceCoordinator for multi-provider support:

```python
# server/voice/dependencies.py

# Environment variable control
USE_COORDINATOR_MODE = os.getenv("VOICE_USE_COORDINATOR", "true").lower() == "true"

def get_voice_service() -> VoiceService:
    """Initialize VoiceService with coordinator by default."""
    coordinator = get_voice_coordinator()  # Returns None if disabled or fails

    return VoiceService(
        client=get_voice_client(),           # Legacy ElevenLabs client
        config_manager=get_voice_config_manager(),
        coordinator=coordinator,              # Multi-provider coordinator
        use_coordinator=coordinator is not None
    )
```

**Features**:
- ✅ Automatic coordinator initialization
- ✅ Graceful fallback to legacy mode on error
- ✅ Environment variable control (`VOICE_USE_COORDINATOR`)
- ✅ Singleton pattern for performance
- ✅ Proper cleanup with `reset_voice_dependencies()`

---

## Current Implementation (REST API)

### REST Mode Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as React Component
    participant H as useVoice Hook
    participant C as VoiceApiClient
    participant R as REST Router
    participant S as VoiceService
    participant E as Provider API

    U->>UI: Click record
    UI->>H: startRecording()
    H->>H: MediaRecorder.start()
    Note over H: Recording audio...
    U->>UI: Stop recording
    UI->>H: stopRecording()
    H->>H: Get audio blob
    H->>C: transcribe(audioBlob)
    C->>R: POST /voice/transcribe
    R->>S: transcribe(audio_data)
    S->>E: speech_to_text()
    E-->>S: transcript text
    S-->>R: TranscriptResult
    R-->>C: JSON response
    C-->>H: { text, duration, ... }
    H-->>UI: transcript
    UI-->>U: Display text

    Note over U,E: TTS Flow (Agent Response)
    UI->>C: synthesize(text)
    C->>R: POST /voice/synthesize
    R->>S: synthesize(text)
    S->>E: text_to_speech()
    E-->>S: audio bytes
    S-->>R: AudioResult
    R-->>C: MP3 binary
    C-->>UI: Audio blob
    UI->>UI: Play audio
```

### Backend Components

#### 1. VoiceService (Business Logic)

```python
# server/voice/service.py

class VoiceService:
    """
    Core service orchestrating TTS and STT operations.
    
    Features:
    - Request validation and sanitization
    - Configuration management with profiles
    - Voice list caching
    - Streaming support for real-time audio
    - Comprehensive error handling
    """
    
    async def transcribe(
        self,
        audio_data: bytes,
        config: Optional[STTConfig] = None
    ) -> TranscriptResult:
        """Transcribe audio to text."""
        
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        profile: Optional[str] = None
    ) -> AudioResult:
        """Convert text to speech."""
        
    async def stream_synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Stream synthesized audio chunks."""
```

#### 2. REST API Endpoints

```python
# server/voice/router.py

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/transcribe")
async def transcribe_audio(...):
    """Transcribe uploaded audio file."""

@router.post("/synthesize")
async def synthesize_speech(...):
    """Convert text to speech."""

@router.post("/synthesize/stream")
async def stream_synthesize(...):
    """Stream synthesized audio."""

@router.get("/voices")
async def list_voices(...):
    """List available voices."""

@router.get("/voices/{voice_id}")
async def get_voice(...):
    """Get voice details."""

@router.get("/config")
async def get_config(...):
    """Get current configuration."""

@router.put("/config")
async def update_config(...):
    """Update configuration."""

@router.get("/health")
async def health_check(...):
    """Service health check."""
```

### Frontend Components

#### 1. VoiceContext (Global State)

```typescript
// lib/contexts/VoiceContext.tsx

export interface VoiceContextState {
  // Settings
  settings: VoiceSettings;
  updateSettings: (updates: Partial<VoiceSettings>) => void;
  
  // Voices
  voices: VoiceInfo[];
  refreshVoices: () => Promise<void>;
  
  // Health
  health: HealthStatus;
  
  // Client
  client: VoiceApiClient;
}
```

#### 2. useVoice Hook

```typescript
// lib/hooks/useVoice.ts

export function useVoice() {
  const { client, settings } = useVoiceContext();
  
  const recordAndTranscribe = async () => {
    // Record audio
    const audioBlob = await recorder.record();
    
    // Transcribe
    const result = await client.transcribe(audioBlob);
    
    return result.text;
  };
  
  const synthesizeAndPlay = async (text: string) => {
    // Synthesize
    const audioBlob = await client.synthesize(text);
    
    // Play
    await player.play(audioBlob);
  };
}
```

#### 3. Voice Components

```typescript
// components/voice/VoiceToggle.tsx
// - Recording button with state indicators
// - Permission handling
// - Duration display

// components/voice/VoiceAnimation.tsx
// - Real-time audio level visualization
// - Frequency data display
// - Multiple animation styles

// components/voice/VoiceSettings.tsx
// - Voice selector
// - Profile selector
// - TTS/STT toggles
// - Volume and speed controls

// components/voice/VoiceInputPanel.tsx
// - Integrated voice input for chat
// - Error display with troubleshooting hints
// - Permission status indicators
```

---

## Real-Time Extension (LiveKit)

### Real-Time Mode Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as LiveKitVoiceChat
    participant H as useRealtimeVoice
    participant C as RealtimeVoiceClient
    participant R as WebSocket Router
    participant S as RealtimeVoiceService
    participant L as LiveKit Room
    participant A as Agent Worker

    U->>UI: Click "Start Voice Chat"
    UI->>H: connect(agentId)
    H->>C: createSession(agentId)
    C->>R: POST /voice/realtime/sessions
    R->>S: create_session(agentId)
    S->>L: create_room()
    L-->>S: room credentials
    S-->>R: session info
    R-->>C: { room_name, url, token }
    C->>L: connect(url, token)
    Note over C,L: WebRTC connection established

    C->>C: Publish local audio track
    Note over U: User speaks...
    L->>A: Audio frames
    A->>A: STT (stream)
    A->>A: Process with OpenAI Agent
    A->>A: TTS (stream)
    A->>L: Audio response frames
    L->>C: Subscribe to agent audio
    C->>UI: Auto-play audio
    UI-->>U: Hear agent response

    Note over U,A: Continuous bidirectional audio

    U->>UI: Click "End Call"
    UI->>H: disconnect()
    H->>C: disconnect()
    C->>L: disconnect()
    C->>R: DELETE /voice/realtime/sessions/{id}
    R->>S: end_session(id)
    S->>L: delete_room()
```

### When to Use Each Mode

| Use Case | Recommended Mode | Reason |
|----------|-----------------|--------|
| Quick voice commands | REST API | Lower overhead, simpler |
| File transcription | REST API | Only option |
| Multi-turn Q&A | REST API | Good enough, cheaper |
| Real-time conversation | LiveKit | Much better UX |
| Interactive tutoring | LiveKit | Can interrupt, instant feedback |
| Voice agent phone call | LiveKit | Natural phone-like experience |

### MoE Orchestrator Integration

The real-time voice agent supports integration with the **MoE (Mixture of Experts) Orchestrator** for intelligent multi-agent routing. When configured with `AgentType.MOE`, the voice agent routes queries through the MoE orchestrator, which:

1. **Selects Specialist Agents**: Uses semantic similarity to choose relevant expert agents (e.g., `YelpAgent`, `MapAgent`, `PerplexityAgent`)
2. **Parallel Execution**: Executes selected experts concurrently for faster responses
3. **Result Mixing**: Synthesizes expert results into a coherent voice response
4. **Fast-Path Bypass**: Routes simple queries (e.g., chitchat) directly to a single agent for lower latency

**Architecture**:

```
User Speech → STT → VoiceAgent.llm_node() → MoEOrchestrator.route_query()
                                                      ↓
                                    [Expert Selection → Parallel Execution → Result Mixing]
                                                      ↓
                                            VoiceAgent.llm_node() → TTS → User
```

**Configuration**:

The voice agent automatically initializes the MoE orchestrator when `agent_type=AgentType.MOE` is specified. The MoE orchestrator uses the same configuration as the text-based MoE system (`config/moe.yaml`), ensuring consistent behavior across voice and text interfaces.

**Key Benefits**:

- ✅ **Intelligent Routing**: Automatically selects the best agents for each query
- ✅ **Parallel Processing**: Multiple experts execute simultaneously, reducing latency
- ✅ **Voice-Optimized**: Results are formatted for natural speech synthesis
- ✅ **Consistent Behavior**: Same MoE logic for both voice and text interactions

**File**: `server/voice/realtime/agent.py` (lines 199-217)

For detailed MoE documentation, see `docs/moe/moe_orchestrator.md`.

### Implementation Status

- ✅ **REST API**: 100% complete
- ✅ **Real-Time Voice Features**: Thinking filler system complete (December 13, 2025)
  - ✅ Context-aware thinking fillers
  - ✅ FlushSentinel for immediate TTS playback
  - ✅ Chitchat detection and skip logic
  - ✅ 27/27 tests passing
- ⏳ **LiveKit Backend**: Partial (agent integration complete, full infrastructure pending)
- ⏳ **LiveKit Frontend**: Pending
- ⏳ **Mode Selector**: Pending

---

## Real-Time Voice Features

### Thinking Filler System

**Date**: December 13, 2025  
**Status**: ✅ Complete and Production Ready

The thinking filler system provides immediate, context-aware acknowledgments during real-time voice interactions, eliminating awkward silences while the agent processes queries.

#### Problem Statement

The realtime voice agent was **silent** immediately after receiving a user query, creating an awkward pause during the processing phase. Users had no feedback indicating that the agent was:
- Listening to their query
- Processing the request
- Working on a response

#### Solution: Context-Aware Thinking Fillers

We implemented a **thinking filler system** that provides immediate, friendly acknowledgments while the agent processes queries. These fillers are:

1. **Context-aware**: Different responses based on query type (search, calculation, location, etc.)
2. **Varied**: Multiple options per category to avoid repetition
3. **Natural**: Conversational phrases like "Let me search for that" or "Just a moment"
4. **Intelligent**: Skips fillers for short greetings and chitchat to feel more natural

#### Architecture

```
server/voice/realtime/
├── thinking_filler.py          # Core filler service
│   ├── ThinkingFillerService   # Main service class
│   ├── FillerHistory           # Repetition avoidance
│   └── get_thinking_filler()   # Convenience function
├── agent.py                    # Voice agent (MODIFIED)
│   └── llm_node()              # Integrated filler before processing
└── ...
```

#### Query Classification

Queries are classified into **6 categories** using pattern matching:

| Category | Examples | Fillers |
|----------|----------|---------|
| **Search** | "search for X", "find latest news" | "Let me search for that.", "I'll look that up for you." |
| **Calculation** | "calculate 25 * 43", "what is 100 divided by 5" | "Let me calculate that.", "I'll work that out." |
| **Location** | "directions to SF", "where is the nearest restaurant" | "Let me check the location.", "I'll look up that place." |
| **Knowledge** | "what is quantum mechanics", "who is Einstein" | "Let me think about that.", "I'll get you that information." |
| **Creative** | "write a poem", "generate ideas" | "Let me think creatively about that.", "I'll work on that." |
| **General** | "help me with this", "can you assist?" | "Just a moment.", "Hold on a second." |

#### Implementation Details

**File**: `server/voice/realtime/thinking_filler.py`

##### Key Methods

**`classify_query(query: str) -> QueryType`**: Analyzes the query and returns its category using pattern matching.

**`get_filler(query: str, previous_filler: Optional[str] = None) -> str`**: Selects an appropriate filler, avoiding repetition.

**`should_use_filler(query: str) -> bool`**: Determines if a filler should be used for this query (skips chitchat).

##### Integration with Voice Agent

**File**: `server/voice/realtime/agent.py`

```python
async def llm_node(self, chat_ctx: ChatContext, ...) -> AsyncIterable[lk_llm.ChatChunk]:
    user_message = self._extract_user_message(chat_ctx)
    
    # Generate thinking filler before processing
    from server.voice.realtime.thinking_filler import get_thinking_filler
    
    thinking_filler = get_thinking_filler(user_message)
    if thinking_filler:
        logger.info(f"Using thinking filler: '{thinking_filler}'")
        # Yield thinking filler immediately
        yield lk_llm.ChatChunk(
            id="",
            delta=lk_llm.ChoiceDelta(
                content=thinking_filler,
                role="assistant",
            ),
        )
        
        # CRITICAL: Yield FlushSentinel to force immediate TTS playback
        yield FlushSentinel()
        logger.debug("Filler flushed to TTS, now processing query...")
        
        # Yield control to event loop
        await asyncio.sleep(0)
    
    # Route through underlying agent (user already has feedback)
    result = await self._underlying_agent.route_query(user_message)
    # ... yield response
```

#### FlushSentinel Fix

**Problem**: Filler was buffered with response and spoken together (not immediately).

**Root Cause**: LiveKit TTS pipeline buffers ChatChunks for efficiency. Without explicit flush signal, filler and response were sent to TTS simultaneously.

**Solution**: Added `FlushSentinel()` to force immediate TTS playback:

```python
# Yield filler
yield lk_llm.ChatChunk(...)

# CRITICAL: Flush TTS buffer immediately
yield FlushSentinel()

# Yield control to event loop
await asyncio.sleep(0)
```

**Why FlushSentinel is Critical**:
- **Explicit Intent**: Clearly signals "flush TTS buffer now"
- **No Timing Dependency**: Works regardless of processing speed
- **Official API**: Provided by LiveKit for exactly this use case
- **Zero Latency Cost**: Doesn't add arbitrary delays
- **Future-Proof**: If LiveKit changes buffering behavior, FlushSentinel contract remains

**Data Flow**:
```
User query
    ↓
llm_node() receives
    ↓
[1] Yield ChatChunk("Let me see.")  ← Filler
    ↓
[2] Yield FlushSentinel()  ← FLUSH SIGNAL
    ↓
[3] Await asyncio.sleep(0)  ← Yield control
    ↓
[4] Consumer processes filler immediately
    ↓
TTS speaks: "Let me see." (immediately)
    ↓
[5] Await route_query()  ← BLOCKS (filler already spoken)
    ↓
[6] Yield ChatChunk("If you are...")  ← Response
    ↓
[7] Consumer processes response
    ↓
TTS speaks: "If you are..." (separate, after pause)
```

#### Chitchat Detection

**Problem**: Chitchat queries ("how are you") shouldn't have fillers - need instant response.

**Solution**: Added chitchat pattern detection to skip fillers for conversational exchanges.

**Patterns Detected**:
- Greetings: "how are you", "what's up", "good morning"
- Goodbyes: "see you later", "bye", "goodbye"
- Thanks/Welcome: "you're welcome", "no problem"
- Confirmations: "yes", "no", "sure", "cool", "great"

**Implementation**:

```python
@classmethod
def should_use_filler(cls, query: str) -> bool:
    query_stripped = query.strip()
    if not query_stripped:
        return False
    
    query_lower = query_stripped.lower()
    word_count = len(query_stripped.split())
    
    # Check for short greetings/acknowledgments (1-2 words)
    if word_count <= 2:
        greetings = ["hi", "hello", "hey", "thanks", "thank you", "ok", "okay"]
        if query_lower in greetings:
            return False
    
    # Check for chitchat patterns (conversational, no work needed)
    chitchat_patterns = [
        r"^(how are you|how's it going|how do you do|nice to meet you)(\?|\.)?$",
        r"^(what's up|wassup|sup)(\?|\.)?$",
        r"^(good morning|good afternoon|good evening|good night)(\?|\.)?$",
        r"^(see you later|see you|bye|goodbye|talk to you later|catch you later)(\?|\.)?$",
        r"^(nice talking|great chatting|enjoyed talking)(\?|\.)?$",
        r"^(you'?re welcome|no problem|anytime|my pleasure)(\?|\.)?$",
        r"^(yes|no|sure|absolutely|definitely|nope|nah)(\?|\.)?$",
        r"^(cool|great|awesome|nice|perfect|excellent|wonderful)(\?|\.)?$",
    ]
    
    for pattern in chitchat_patterns:
        if re.search(pattern, query_lower):
            return False
    
    return True
```

**Benefits**:
- More natural conversations (chitchat feels instant)
- Faster response for simple queries (~500ms savings per chitchat query)
- Better user experience (users expect instant responses to greetings)

#### Testing

**Test Coverage**: 27/27 tests passing ✅

```
TestQueryClassification (6 tests) ✅
TestFillerSelection (4 tests) ✅
TestDurationEstimation (3 tests) ✅
TestShouldUseFiller (5 tests) ✅  ← Includes chitchat tests
TestFillerHistory (3 tests) ✅
TestConvenienceFunction (2 tests) ✅
TestEdgeCases (4 tests) ✅
```

**Running Tests**:

```bash
python -m pytest tests/server/voice/realtime/test_thinking_filler.py -v
```

#### Performance Impact

| Operation | Time | Impact |
|-----------|------|--------|
| Query classification | < 1ms | Negligible |
| Filler selection | < 1ms | Negligible |
| ChatChunk yield | < 5ms | Negligible |
| **Total overhead** | **< 10ms** | **Minimal** |

**Memory Usage**: < 5 KB (singleton FillerHistory + static data)

#### Usage Examples

**Search Query**:
- **User**: "search for the latest news on AI"
- **Agent**: [Filler] "Let me search for that." → [Processing] → [Response] "Here are the latest AI news articles..."

**Calculation Query**:
- **User**: "what is 25 * 43?"
- **Agent**: [Filler] "Let me calculate that." → [Processing] → [Response] "25 multiplied by 43 equals 1,075."

**Chitchat Query (No Filler)**:
- **User**: "How are you?"
- **Agent**: [No filler - immediate response] "I'm doing great, thanks for asking!"

#### Troubleshooting

**Filler Not Spoken Until Response Ready**:
- **Symptom**: Filler appears in transcript together with response
- **Solution**: Ensure `FlushSentinel()` is yielded after the filler ChatChunk

**Filler Not Generated**:
- **Possible Causes**: Short greeting (intentionally skipped), empty query, import error
- **Solution**: Check logs for "Using thinking filler: '...'" or "Skipping filler for..." messages

**Filler Spoken Too Late**:
- **Solution**: Ensure filler generation and yielding happens **before** the `await route_query()` call

#### Related Files

- **Implementation**: `server/voice/realtime/thinking_filler.py` - Core service
- **Integration**: `server/voice/realtime/agent.py` - Voice agent integration
- **Tests**: `tests/server/voice/realtime/test_thinking_filler.py` - 27 tests

---

## Quick Start Guide

### Backend Setup

#### 1. Install Dependencies

```bash
cd server
pip install -e .
```

#### 2. Configure Environment

```bash
# Required: OpenAI API key (default provider)
export OPENAI_API_KEY="your_openai_key_here"

# Optional: ElevenLabs API key (for premium profiles)
export ELEVENLABS_API_KEY="your_elevenlabs_key_here"

# Optional: Enable coordinator mode (default: true)
export VOICE_USE_COORDINATOR="true"
```

#### 3. Start Server

```bash
python -m server.main
```

#### 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/voice/health

# Expected response:
# {"status":"healthy","elevenlabs_connected":true,"config_loaded":true}

# List voices
curl http://localhost:8000/voice/voices
```

### Frontend Setup

#### 1. Install Dependencies

```bash
cd frontend_web
npm install
```

#### 2. Configure Environment

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your_api_key_here
```

#### 3. Add VoiceProvider to Layout

```typescript
// app/layout.tsx
import { VoiceProvider } from '@/lib/contexts/VoiceContext';

export default function RootLayout({ children }) {
  return (
    <VoiceProvider>
      {children}
    </VoiceProvider>
  );
}
```

#### 4. Use Voice in Components

```typescript
// components/chat.tsx
import { useVoice } from '@/lib/hooks/useVoice';
import { VoiceToggle } from '@/components/voice/VoiceToggle';

export function ChatInterface() {
  const { recordAndTranscribe, synthesizeAndPlay } = useVoice();
  
  return (
    <div>
      <VoiceToggle />
      {/* Chat UI */}
    </div>
  );
}
```

### Deployment Verification

```bash
# 1. Verify configuration
python3 -c "
from server.voice.config import VoiceConfigManager
from pathlib import Path

manager = VoiceConfigManager(Path('config/voice_config.yaml'))
config = manager.load()

assert config.default_provider == 'openai', 'Default provider should be openai'
assert config.tts.model_id == 'gpt-4o-mini-tts', 'TTS model should be gpt-4o-mini-tts'
assert config.stt.model_id == 'gpt-4o-transcribe', 'STT model should be gpt-4o-transcribe'

print('✅ Configuration verified successfully')
"

# 2. Test transcription
curl -X POST "http://localhost:8000/voice/transcribe?provider_strategy=cost_optimized" \
  -F "audio=@test.webm" \
  -H "X-API-Key: your_key"

# 3. Test synthesis
curl -X POST "http://localhost:8000/voice/synthesize" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{"text": "Testing OpenAI synthesis"}'
```

---

## How-To Guides

### How to Transcribe Audio

#### Backend (Python) - Using VoiceCoordinator (Recommended)

```python
from server.voice.coordinator import VoiceCoordinator, ProviderPreference, SelectionStrategy

# Create coordinator
coordinator = VoiceCoordinator()

# Read audio file
with open("recording.webm", "rb") as f:
    audio_data = f.read()

# Transcribe with cost optimization (uses OpenAI)
result = await coordinator.transcribe(
    audio_data,
    preferences=ProviderPreference(
        strategy=SelectionStrategy.COST_OPTIMIZED
    )
)

print(f"Text: {result.text}")
print(f"Duration: {result.duration}s")
print(f"Confidence: {result.confidence}")
```

#### Frontend (TypeScript)

```typescript
import { useVoice } from '@/lib/hooks/useVoice';

function VoiceInput() {
  const { recordAndTranscribe } = useVoice();
  const [transcript, setTranscript] = useState('');
  
  const handleRecord = async () => {
    try {
      const text = await recordAndTranscribe();
      setTranscript(text);
    } catch (error) {
      console.error('Transcription failed:', error);
    }
  };
  
  return (
    <button onClick={handleRecord}>
      Record & Transcribe
    </button>
  );
}
```

#### API (cURL)

```bash
# Cost-optimized (uses OpenAI)
curl -X POST "http://localhost:8000/voice/transcribe?provider_strategy=cost_optimized" \
  -F "audio=@recording.webm" \
  -H "X-API-Key: your_key"

# Quality-optimized (uses ElevenLabs)
curl -X POST "http://localhost:8000/voice/transcribe?provider_strategy=quality_optimized" \
  -F "audio=@recording.webm" \
  -H "X-API-Key: your_key"

# Explicit provider
curl -X POST "http://localhost:8000/voice/transcribe?provider_strategy=explicit&preferred_provider=openai" \
  -F "audio=@recording.webm" \
  -H "X-API-Key: your_key"
```

### How to Synthesize Speech

#### Backend (Python) - Using VoiceCoordinator (Recommended)

```python
from server.voice.coordinator import VoiceCoordinator, ProviderPreference, SelectionStrategy
from server.voice.providers import ProviderType

coordinator = VoiceCoordinator()

# Cost-optimized synthesis (uses OpenAI)
result = await coordinator.synthesize(
    text="Hello, this is a test.",
    preferences=ProviderPreference(
        strategy=SelectionStrategy.COST_OPTIMIZED
    )
)

# Quality-optimized synthesis (uses ElevenLabs)
result = await coordinator.synthesize(
    text="Hello, this is a test.",
    preferences=ProviderPreference(
        strategy=SelectionStrategy.QUALITY_OPTIMIZED,
        fallback_enabled=True  # Falls back to OpenAI if ElevenLabs fails
    )
)

# Save audio file
with open("output.mp3", "wb") as f:
    f.write(result.audio_data)
```

#### API (cURL)

```bash
# Cost-optimized synthesis
curl -X POST "http://localhost:8000/voice/synthesize" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{
    "text": "Hello, world!",
    "provider_preferences": {
      "strategy": "cost_optimized"
    }
  }'

# Explicit OpenAI provider
curl -X POST "http://localhost:8000/voice/synthesize" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{
    "text": "Test OpenAI synthesis",
    "provider_preferences": {
      "strategy": "explicit",
      "preferred_provider": "openai",
      "fallback_enabled": false
    }
  }'

# Streaming with quality optimization
curl -N -X POST "http://localhost:8000/voice/synthesize/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{
    "text": "Long text for streaming...",
    "provider_preferences": {
      "strategy": "quality_optimized"
    }
  }'
```

### How to Configure Voice Profiles

#### YAML Configuration (OpenAI Default)

```yaml
# config/voice_config.yaml

voice:
  enabled: true
  default_provider: "openai"
  default_strategy: "cost_optimized"
  enable_fallback: true

  providers:
    openai:
      enabled: true
      tts:
        model: "gpt-4o-mini-tts"
        voice: "coral"
        speed: 1.0
        response_format: "mp3"
      stt:
        model: "gpt-4o-transcribe"
        response_format: "verbose_json"
        temperature: 0.0

    elevenlabs:
      enabled: true
      tts:
        voice_id: "JBFqnCBsd6RMkjVDRZzb"
        model_id: "eleven_multilingual_v2"
        stability: 0.5
      stt:
        model_id: "scribe_v1"

  voice_profiles:
    default:
      provider: "openai"
      voice_id: "coral"
      model_id: "gpt-4o-mini-tts"
      speed: 1.0

    professional:
      provider: "openai"
      voice_id: "echo"
      model_id: "gpt-4o-mini-tts"
      speed: 0.9
      instructions: "Speak in a professional, measured tone"

    premium:
      provider: "elevenlabs"
      voice_id: "21m00Tcm4TlvDq8ikWAM"
      model_id: "eleven_multilingual_v2"
      stability: 0.7
```

#### Using Profiles in Code

```python
# Use specific profile
result = await service.synthesize(
    text="Hello",
    profile="professional"  # Uses professional profile settings
)
```

```typescript
// Frontend
const { settings, updateSettings } = useVoiceContext();

updateSettings({
  selectedProfile: 'professional'
});
```

### How to Handle Errors

#### Backend Error Handling

```python
from server.voice.exceptions import (
    VoiceException,
    VoiceClientException,
    VoiceErrorCode
)

try:
    result = await service.transcribe(audio_data)
except VoiceClientException as e:
    if e.error_code == VoiceErrorCode.API_KEY_INVALID:
        print("Invalid API key")
    elif e.error_code == VoiceErrorCode.API_KEY_MISSING_PERMISSION:
        print("API key missing required permission")
    else:
        print(f"Error: {e.message}")
except VoiceException as e:
    print(f"Voice error: {e.message}")
```

#### Frontend Error Handling

```typescript
import { VoiceApiClientError } from '@/lib/services/VoiceApiClient';

try {
  const result = await client.transcribe(audioBlob);
} catch (error) {
  if (error instanceof VoiceApiClientError) {
    switch (error.errorCode) {
      case 'VOICE_202':
        console.error('Invalid API key');
        break;
      case 'VOICE_204':
        console.error('API key missing permission');
        break;
      default:
        console.error('Voice error:', error.message);
    }
  }
}
```

---

## API Reference

### REST Endpoints

#### POST `/voice/transcribe`

Transcribe uploaded audio file to text with optional provider selection.

**Request (Multipart Form Data)**:
- `audio` (file, required): Audio file (mp3, wav, webm, ogg)
- `language_code` (query param, optional): ISO 639-1 language code
- `tag_audio_events` (query param, optional): Tag audio events like laughter
- `provider_strategy` (query param, optional): Provider selection strategy
  - `cost_optimized`: Choose cheapest provider (default: OpenAI)
  - `quality_optimized`: Choose best quality provider (default: ElevenLabs)
  - `latency_optimized`: Choose fastest provider
  - `explicit`: Use explicitly specified provider
- `preferred_provider` (query param, optional): Explicit provider selection
  - `openai`: Use OpenAI Whisper
  - `elevenlabs`: Use ElevenLabs Scribe
- `fallback_enabled` (query param, optional): Enable automatic fallback (default: true)

**Response**:
```json
{
  "success": true,
  "result": {
    "text": "Hello, this is a transcription.",
    "duration_ms": 2500,
    "confidence": 0.95,
    "language_detected": "en",
    "words": [
      {
        "word": "Hello",
        "start": 0.0,
        "end": 0.5,
        "confidence": 0.98
      }
    ]
  },
  "request_id": "req_abc123",
  "processing_time_ms": 1500
}
```

#### POST `/voice/synthesize`

Convert text to speech with optional provider selection.

**Request (JSON Body)**:
```json
{
  "text": "Hello, this is a test.",
  "voice_id": "coral",
  "profile_name": "default",
  "provider_preferences": {
    "strategy": "cost_optimized",
    "preferred_provider": null,
    "fallback_enabled": true
  }
}
```

**Response**: Binary audio file (MP3)

**Response Headers**:
- `Content-Type`: `audio/mpeg`
- `X-Request-ID`: Unique request identifier
- `X-Character-Count`: Number of characters synthesized
- `X-Duration-MS`: Audio duration in milliseconds

#### POST `/voice/synthesize/stream`

Stream synthesized audio with optional provider selection.

**Response**: Streaming audio chunks (MP3)

#### GET `/voice/voices`

List available voices from all providers.

#### GET `/voice/voices/{voice_id}`

Get specific voice details.

#### GET `/voice/config`

Get current configuration.

#### PUT `/voice/config`

Update configuration.

#### GET `/voice/health`

Service health check.

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| VOICE_201 | API key missing | 401 |
| VOICE_202 | API key invalid | 401 |
| VOICE_204 | API key missing permission | 403 |
| VOICE_301 | Invalid request | 400 |
| VOICE_302 | Audio format unsupported | 400 |
| VOICE_401 | Configuration error | 500 |
| VOICE_501 | Service unavailable | 503 |
| VOICE_502 | Timeout | 504 |
| VOICE_503 | Rate limit exceeded | 429 |
| VOICE_504 | Network error | 503 |

---

## Configuration

### Configuration File (OpenAI Default)

```yaml
# config/voice_config.yaml

voice:
  enabled: true
  default_provider: "openai"
  default_strategy: "cost_optimized"
  enable_fallback: true

  providers:
    openai:
      enabled: true
      tts:
        model: "gpt-4o-mini-tts"
        voice: "coral"
        speed: 1.0
        response_format: "mp3"
      stt:
        model: "gpt-4o-transcribe"
        response_format: "verbose_json"
        temperature: 0.0
        timestamp_granularities: ["word"]

    elevenlabs:
      enabled: true
      tts:
        voice_id: "JBFqnCBsd6RMkjVDRZzb"
        model_id: "eleven_multilingual_v2"
        stability: 0.5
        similarity_boost: 0.75
      stt:
        model_id: "scribe_v1"

  voice_profiles:
    default:
      provider: "openai"
      voice_id: "coral"
      model_id: "gpt-4o-mini-tts"
      speed: 1.0

    professional:
      provider: "openai"
      voice_id: "echo"
      speed: 0.9
      instructions: "Speak in a professional, measured tone"

    conversational:
      provider: "openai"
      voice_id: "nova"
      speed: 1.1

    storytelling:
      provider: "openai"
      voice_id: "ballad"
      speed: 0.95

    premium:
      provider: "elevenlabs"
      voice_id: "21m00Tcm4TlvDq8ikWAM"
      stability: 0.7
      similarity_boost: 0.8

    premium_casual:
      provider: "elevenlabs"
      voice_id: "EXAVITQu4vr4xnSDxMaL"
      stability: 0.4

  default_profile: "default"

  cache:
    voice_list_ttl: 3600
    enable_response_cache: false

  logging:
    log_api_calls: true
    log_audio_data: false
    level: "INFO"
```

### Environment Variables

```bash
# Required: OpenAI API key (default provider)
OPENAI_API_KEY=your_openai_key_here

# Optional: ElevenLabs API key (for premium profiles)
ELEVENLABS_API_KEY=your_elevenlabs_key_here

# Optional: Enable/disable coordinator mode (default: true)
VOICE_USE_COORDINATOR=true

# Optional: LiveKit (for future real-time voice)
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
```

### Hot Reload

Configuration can be reloaded without restarting the server:

```python
from server.voice.config import VoiceConfigManager

manager = VoiceConfigManager()
manager.reload_config()  # Reloads from YAML file
```

---

## Provider Comparison

### Cost Comparison

| Operation | OpenAI | ElevenLabs | Savings |
|-----------|--------|------------|---------|
| **TTS (1M characters)** | $12 | $300 | **96%** |
| **STT (1000 minutes)** | $6 | $15 | **60%** |
| **Monthly Total** | $18 | $315 | **$297/month** |

### Quality Comparison

| Feature | OpenAI | ElevenLabs |
|---------|--------|------------|
| **Voice Quality** | ⭐⭐⭐⭐☆ Excellent | ⭐⭐⭐⭐⭐ Ultra-Premium |
| **Transcription Accuracy** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Excellent |
| **Language Support** | 98 languages | 29 languages |
| **Voice Customization** | Instructions | Voice cloning |
| **Latency** | ~1-2s | ~1-3s |
| **Streaming** | ✅ Yes | ✅ Yes (+ WebSocket) |

### Performance Metrics

| Metric | OpenAI | ElevenLabs | Coordinator Overhead |
|--------|--------|------------|---------------------|
| **STT Latency** | 1-2s | 1-3s | <10ms |
| **TTS Latency** | 1-2s | 1-3s | <10ms |
| **Streaming** | 200-500ms | 150-300ms | <5ms |
| **Max File Size** | 25 MB | 25 MB | N/A |
| **Concurrent Requests** | High | High | High |

### Use Case Recommendations

| Use Case | Recommended Provider | Reason |
|----------|---------------------|--------|
| High-volume applications | OpenAI | 96% cost savings |
| Premium customer experiences | ElevenLabs | Superior voice quality |
| Multi-language support | OpenAI | 98 languages vs 29 |
| Voice cloning needs | ElevenLabs | Custom voice creation |
| Real-time conversations | LiveKit (future) | <500ms latency |

### Cost Analysis Examples

**Scenario 1: All OpenAI (Cost-Optimized)**
- STT: 100 hours × $0.006 = $0.60
- TTS: 1M chars × $0.012/1K = $12
- **Total: $12.60/month**

**Scenario 2: All ElevenLabs (Quality-Optimized)**
- STT: 100 hours × $0.015 = $1.50
- TTS: 1M chars × $0.30/1K = $300
- **Total: $301.50/month**

**Scenario 3: Hybrid (Recommended)**
- STT: 100 hours × $0.006 = $0.60 (OpenAI)
- TTS (50% OpenAI, 50% ElevenLabs): $156
- **Total: $156.60/month** (48% savings vs all-ElevenLabs)

---

## Testing

### Test Coverage Summary

| Category | Tests | Coverage | Status |
|----------|-------|----------|--------|
| **Frontend Hooks** | 210+ | 80% | ✅ Complete |
| **Backend Router** | 35 | 70% | ⚠️ Partial |
| **Provider Unit** | 16 | 90% | ✅ Complete |
| **Integration** | 10 | 60% | ⚠️ Partial |

### Frontend Test Suites

#### useAudioRecorder Tests (70+ cases)
- ✅ Initialization and configuration
- ✅ Permission management (7 tests)
- ✅ Recording lifecycle (7 tests)
- ✅ Duration tracking (3 tests)
- ✅ Audio level monitoring (4 tests)
- ✅ Error handling (4 tests)
- ✅ Cleanup (3 tests)

#### useAudioPlayer Tests (60+ cases)
- ✅ Source management (5 tests)
- ✅ Playback controls (5 tests)
- ✅ Progress tracking and seeking (4 tests)
- ✅ Volume control (4 tests)
- ✅ Playback rate (3 tests)
- ✅ Auto-play (3 tests)
- ✅ Error handling (3 tests)

#### useVoice Tests (80+ cases)
- ✅ Recording (5 tests)
- ✅ Transcription (8 tests)
- ✅ Synthesis (7 tests)
- ✅ Playback (5 tests)
- ✅ Combined workflows (4 tests)
- ✅ Error handling (3 tests)
- ✅ State propagation (6 tests)

### Backend Test Suites

#### Router Integration Tests (35 tests)
- Transcription (8 tests)
- Synthesis (12 tests)
- Voice management (3 tests)
- Health & config (2 tests)
- Provider selection (10 tests)

#### OpenAI Provider Tests (16 tests)
- ✅ Transcription success and error handling
- ✅ Word-level timestamps
- ✅ Synthesis with instructions
- ✅ Streaming synthesis
- ✅ Health check

### Running Tests

```bash
# Frontend tests
cd frontend_web
npm test -- __tests__/voice/

# Specific hook tests
npm test -- __tests__/voice/hooks/useAudioRecorder.test.ts
npm test -- __tests__/voice/hooks/useAudioPlayer.test.ts
npm test -- __tests__/voice/hooks/useVoice.test.ts

# With coverage
npm test -- __tests__/voice/ --coverage

# Backend tests
cd server
pytest tests/server/voice/ -v

# Specific test file
pytest tests/server/voice/test_voice_router.py -v
```

### Mock Utilities

**MockMediaRecorder** (`__tests__/voice/utils/mockMediaRecorder.ts`):
- Realistic MediaRecorder state machine
- Simulates data available events
- Supports getUserMedia mocking
- Supports AudioContext mocking

**MockAudio** (`__tests__/voice/utils/mockAudio.ts`):
- HTML Audio element simulation
- Play/pause/stop/seek operations
- Metadata loading simulation
- Error scenarios

**MockVoiceApiClient** (`__tests__/voice/utils/mockVoiceApiClient.ts`):
- Mocked API methods
- Configurable responses
- Success/failure scenarios

---

## Troubleshooting

### Voice Input Not Working

If the microphone button doesn't capture audio, check these potential causes:

#### 1. Microphone Permission Not Granted ⚠️ (Most Common)

**Symptoms**:
- Mic button is visible but nothing happens when clicked
- No browser permission popup appears

**Diagnostic Steps**:
1. Open browser DevTools → Console
2. Check for `NotAllowedError` or `PermissionDeniedError`
3. Check browser address bar for microphone permission status

**Solution**:
- Reset microphone permissions in browser settings
- Ensure application is served over HTTPS (not HTTP)
- Check browser console for permission errors

#### 2. HTTP Instead of HTTPS 🔒

**Symptoms**:
- Browser console shows: `getUserMedia() is not supported in insecure contexts`
- Permission popup never appears

**Root Cause**: Modern browsers block microphone access over HTTP for security.

**Solution**:
- Development: Use `https://localhost:3000` or just `localhost`
- Production: Ensure SSL certificate is properly configured

```bash
# If using HTTP, switch to HTTPS:
npm run dev -- --experimental-https
```

#### 3. Backend API Key Missing 🔑

**Symptoms**:
- Recording works
- Browser sends POST to `/voice/transcribe`
- Backend returns `401 Unauthorized`

**Solution**:
- Ensure `NEXT_PUBLIC_API_KEY` is set in `frontend_web/.env.local`
- Verify API key in backend configuration

#### 4. Transcription Silent Failure ⏱️

**Symptoms**:
- Recording works (waveform animation shows)
- But transcript never appears

**Solution**: Check for errors in `voice.transcriptionError` and `voice.recordingError`

### Voice Input Flow Diagram

```
User clicks mic button
  ↓
VoiceInputPanel.handleToggleRecording()
  ↓
useVoice.startRecording()
  ↓
useAudioRecorder.startRecording()
  ↓
1. Check hasPermission (if false, call requestPermission())
  ↓
2. navigator.mediaDevices.getUserMedia({ audio: { ... } })
  ↓
3. Create MediaRecorder with audio stream
  ↓
4. Start recording (mediaRecorder.start())
  ↓
[User speaks into microphone]
  ↓
User clicks mic button again to stop
  ↓
1. Stop MediaRecorder
  ↓
2. Collect audio chunks into Blob
  ↓
3. Call transcribe(audioBlob)
  ↓
4. POST /voice/transcribe
  ↓
5. Backend transcribes audio
  ↓
6. Display transcript in chat input
```

### Common Backend Issues

#### 1. API Key Permission Errors

**Symptom**: `VOICE_204` error when listing voices

**Cause**: ElevenLabs API key doesn't have `voices_read` permission

**Solution**:
1. Check API key permissions in ElevenLabs dashboard
2. Ensure `voices_read` permission is enabled
3. Service will use cached voice list if available

#### 2. Invalid API Key

**Symptom**: `VOICE_202` error on all requests

**Solution**:
1. Verify API key is correct
2. Check API key hasn't been revoked
3. Regenerate API key if needed

#### 3. Audio Format Not Supported

**Symptom**: `VOICE_302` error when transcribing

**Solution**:
- Supported formats: mp3, wav, webm, ogg
- Convert audio to supported format
- Check file isn't corrupted

#### 4. High Latency

**Symptom**: Slow transcription or synthesis

**Solutions**:
- Use streaming for long texts
- Compress audio before upload
- Check network connection
- Monitor API rate limits

### Real-Time Voice Troubleshooting

#### 1. Thinking Filler Not Spoken Until Response Ready

**Symptom**: Filler appears in transcript together with response (e.g., "Let me see.If you are referring to..."), and is spoken at the same time as response.

**Root Cause**: TTS buffer is not being flushed after filler is yielded. The pipeline buffers both filler and response, then sends them together.

**Solution**: Ensure `FlushSentinel()` is yielded after the filler ChatChunk:

```python
# Yield filler
yield lk_llm.ChatChunk(
    id="",
    delta=lk_llm.ChoiceDelta(content=thinking_filler, role="assistant"),
)

# CRITICAL: Flush TTS buffer
yield FlushSentinel()

# Yield control to event loop
await asyncio.sleep(0)
```

**Verification**: Check logs for "Filler flushed to TTS, now processing query..." message immediately after filler is generated.

#### 2. Thinking Filler Spoken Too Late

**Symptom**: Filler is spoken, but only after a long delay (response is already being generated).

**Root Cause**: Agent processing is blocking before the filler is yielded.

**Solution**: Ensure filler generation and yielding happens **before** the `await route_query()` call:

```python
# CORRECT order:
thinking_filler = get_thinking_filler(user_message)
if thinking_filler:
    yield lk_llm.ChatChunk(...)
    yield FlushSentinel()
    await asyncio.sleep(0)

# Now process query (blocking)
result = await self._underlying_agent.route_query(user_message)
```

#### 3. Thinking Filler Not Generated

**Symptom**: No filler is spoken for any query.

**Possible Causes**:
1. **Short greeting**: Filler is intentionally skipped for greetings like "hi"
2. **Empty query**: Filler returns None for empty strings
3. **Chitchat query**: Filler is skipped for chitchat patterns like "how are you"
4. **Import error**: `get_thinking_filler` not imported correctly

**Solution**: Check logs for "Using thinking filler: '...'" or "Skipping filler for..." messages.

#### 4. Filler Always the Same

**Symptom**: Same filler phrase is used repeatedly.

**Root Cause**: FillerHistory may not be working correctly, or only one filler option available for query type.

**Solution**: Check that `FillerHistory` is being used correctly and that multiple fillers exist for the query category.

### Debug Mode

Enable debug logging:

```yaml
# config/voice_config.yaml
voice:
  logging:
    level: "DEBUG"
    log_api_calls: true
```

### Health Check

```bash
# Check service health
curl http://localhost:8000/voice/health

# Response
{
  "status": "healthy",
  "version": "2.2.0",
  "tts_available": true,
  "stt_available": true,
  "api_key_configured": true,
  "openai_connected": true,
  "elevenlabs_connected": true
}
```

---

## Examples

### Example 1: Complete Voice Workflow

```typescript
// Complete example: Record → Transcribe → Send → Receive → Speak

import { useVoice } from '@/lib/hooks/useVoice';

function VoiceChat() {
  const { recordAndTranscribe, synthesizeAndPlay } = useVoice();
  const [messages, setMessages] = useState([]);
  
  const handleVoiceMessage = async () => {
    // 1. Record and transcribe
    const userText = await recordAndTranscribe();
    
    // 2. Add user message
    setMessages(prev => [...prev, { role: 'user', content: userText }]);
    
    // 3. Send to agent (your existing chat logic)
    const agentResponse = await sendToAgent(userText);
    
    // 4. Add agent message
    setMessages(prev => [...prev, { role: 'assistant', content: agentResponse }]);
    
    // 5. Speak agent response
    await synthesizeAndPlay(agentResponse);
  };
  
  return (
    <div>
      <button onClick={handleVoiceMessage}>
        🎤 Speak
      </button>
      <div>
        {messages.map((msg, i) => (
          <div key={i} className={msg.role}>
            {msg.content}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Example 2: Error Handling

```typescript
import { useVoice } from '@/lib/hooks/useVoice';
import { VoiceApiClientError } from '@/lib/services/VoiceApiClient';

function VoiceInputWithErrorHandling() {
  const { recordAndTranscribe } = useVoice();
  const [error, setError] = useState<string | null>(null);
  
  const handleRecord = async () => {
    try {
      setError(null);
      const text = await recordAndTranscribe();
      console.log('Transcribed:', text);
    } catch (err) {
      if (err instanceof VoiceApiClientError) {
        switch (err.errorCode) {
          case 'VOICE_201':
            setError('API key not configured');
            break;
          case 'VOICE_202':
            setError('Invalid API key');
            break;
          case 'VOICE_503':
            setError('Rate limit exceeded. Please wait.');
            break;
          default:
            setError(`Voice error: ${err.message}`);
        }
      } else if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setError('Microphone permission denied');
        } else if (err.name === 'NotFoundError') {
          setError('No microphone found');
        } else {
          setError(`Error: ${err.message}`);
        }
      }
    }
  };
  
  return (
    <div>
      <button onClick={handleRecord}>Record</button>
      {error && <div className="error">{error}</div>}
    </div>
  );
}
```

### Example 3: Backend Integration

```python
# Backend: Custom voice endpoint with agent integration

from fastapi import APIRouter, Depends
from server.voice.coordinator import VoiceCoordinator, ProviderPreference, SelectionStrategy
from server.agent_service import AgentService

router = APIRouter()

@router.post("/agent/voice-chat")
async def voice_chat_with_agent(
    audio: UploadFile,
    agent_id: str,
    coordinator: VoiceCoordinator = Depends(get_voice_coordinator),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Complete voice chat workflow:
    1. Transcribe user audio
    2. Process with agent
    3. Synthesize agent response
    4. Return audio
    """
    # 1. Transcribe (cost-optimized)
    audio_data = await audio.read()
    transcript = await coordinator.transcribe(
        audio_data,
        preferences=ProviderPreference(strategy=SelectionStrategy.COST_OPTIMIZED)
    )
    
    # 2. Process with agent
    agent_response = await agent_service.chat_agent(
        agent_id=agent_id,
        request={"input": transcript.text}
    )
    
    # 3. Synthesize (cost-optimized)
    audio_result = await coordinator.synthesize(
        text=agent_response["output"],
        preferences=ProviderPreference(strategy=SelectionStrategy.COST_OPTIMIZED)
    )
    
    # 4. Return audio
    return Response(
        content=audio_result.audio_data,
        media_type="audio/mpeg"
    )
```

---

## Migration Guide

### Migrating from ElevenLabs to OpenAI Default

Successfully migrated the voice module to use **OpenAI as the default provider** with 96% cost savings.

#### Key Changes

| Setting | Before (ElevenLabs) | After (OpenAI) |
|---------|---------------------|----------------|
| **Default Provider** | ElevenLabs | OpenAI |
| **TTS Model** | eleven_multilingual_v2 | gpt-4o-mini-tts |
| **TTS Voice** | JBFqnCBsd6RMkjVDRZzb | coral |
| **STT Model** | scribe_v1 | gpt-4o-transcribe |
| **TTS Cost** | $0.30/1K chars | $0.012/1K chars |
| **STT Cost** | $0.015/min | $0.006/min |

#### Configuration Changes

```yaml
# Before (ElevenLabs default)
voice:
  tts:
    voice_id: "JBFqnCBsd6RMkjVDRZzb"
    model_id: "eleven_multilingual_v2"

# After (OpenAI default)
voice:
  default_provider: "openai"
  default_strategy: "cost_optimized"
  providers:
    openai:
      tts:
        model: "gpt-4o-mini-tts"
        voice: "coral"
```

#### Backward Compatibility

✅ **100% Backward Compatible** - All existing code continues to work:

```python
# Legacy usage (still works)
result = await service.transcribe(audio_data)
result = await service.synthesize(text="Hello")

# New usage (with provider selection)
result = await coordinator.transcribe(
    audio_data,
    preferences=ProviderPreference(strategy=SelectionStrategy.COST_OPTIMIZED)
)
```

### Migrating from VoiceService to VoiceCoordinator

#### Before (using VoiceService directly)

```python
from server.voice.service import VoiceService

service = VoiceService()
result = await service.transcribe(audio_data)
```

#### After (using VoiceCoordinator)

```python
from server.voice.coordinator import VoiceCoordinator, ProviderPreference, SelectionStrategy

coordinator = VoiceCoordinator()

# Cost-optimized (automatic selection)
result = await coordinator.transcribe(
    audio_data,
    preferences=ProviderPreference(
        strategy=SelectionStrategy.COST_OPTIMIZED
    )
)

# Or explicit provider
result = await coordinator.transcribe(
    audio_data,
    preferences=ProviderPreference(
        preferred_provider=ProviderType.OPENAI
    )
)
```

### Benefits of Migration

1. **Cost Savings**: 96% reduction in TTS costs, 60% in STT costs
2. **Automatic Fallback**: Service continues working if one provider fails
3. **Quality Options**: Choose provider based on quality requirements
4. **Future-Proof**: Easy to add new providers

---

## Future Roadmap

### Phase 1: REST API ✅ Complete

- ✅ Backend implementation (8 files, ~2,000 lines)
- ✅ Frontend core (8 files, ~2,400 lines)
- ✅ Integration with chat interface
- ✅ Configuration management
- ✅ Error handling

### Phase 2: Provider System ✅ Complete

- ✅ Provider interface (`IVoiceProvider`)
- ✅ OpenAI provider implementation (~580 lines)
- ✅ ElevenLabs provider wrapper (~380 lines)
- ✅ VoiceCoordinator orchestration (~550 lines)
- ✅ Strategy-based provider selection
- ✅ Automatic fallback mechanism
- ✅ OpenAI as default provider
- ✅ 16 unit tests for OpenAI provider

### Phase 3: Real-Time Voice Features ✅ Complete (December 13, 2025)

**Backend**:
- ✅ `server/voice/realtime/thinking_filler.py` - Thinking filler service (305 lines)
- ✅ `server/voice/realtime/agent.py` - Voice agent with filler integration
- ✅ `tests/server/voice/realtime/test_thinking_filler.py` - Comprehensive tests (27 tests)

**Features**:
- ✅ Context-aware thinking fillers (6 query categories, 40+ filler phrases)
- ✅ FlushSentinel for immediate TTS playback
- ✅ Chitchat detection and skip logic
- ✅ FillerHistory to avoid repetition
- ✅ Pattern-based query classification

### Phase 4: LiveKit Full Integration ⏳ Pending

**Backend**:
- ⏳ `server/voice/providers/livekit_provider.py` - LiveKit provider
- ⏳ `server/voice/realtime/service.py` - RealtimeVoiceService
- ⏳ `server/voice/realtime/room_manager.py` - LiveKit room management
- ⏳ `server/voice/realtime/router.py` - WebSocket endpoints

**Frontend**:
- ⏳ `lib/services/RealtimeVoiceClient.ts` - LiveKit client
- ⏳ `lib/hooks/useRealtimeVoice.ts` - Real-time hook
- ⏳ `components/voice/LiveKitVoiceChat.tsx` - LiveKit UI
- ⏳ `components/voice/VoiceModeSelector.tsx` - Mode switcher

**Estimated Timeline**: 2-3 weeks

### Phase 5: Testing & Documentation ⏳ In Progress

- ✅ Frontend hook tests (210+ tests)
- ✅ Thinking filler tests (27 tests, all passing)
- ⚠️ Backend unit tests (needs VoiceConfigManager tests)
- ⚠️ Integration tests for coordinator
- ⏳ E2E tests
- ⏳ Performance testing

### Phase 6: Enhancements ⏳ Future

- ⏳ ElevenLabs WebSocket streaming (ultra-low latency)
- ⏳ Cost tracking and analytics dashboard
- ⏳ Provider health monitoring dashboard
- ⏳ A/B testing framework for providers
- ⏳ Voice activity detection (VAD)
- ⏳ Audio caching and optimization
- ⏳ Voice cloning
- ⏳ Emotion detection in speech

---

## Summary

### What's Implemented ✅

- **Backend**: Complete REST API with 8 endpoints
- **Provider System**: Multi-provider architecture with OpenAI (default) and ElevenLabs (premium)
- **VoiceCoordinator**: Strategy-based provider selection and automatic fallback
- **Real-Time Voice Features**: Thinking filler system with context-aware responses (December 13, 2025)
  - Context-aware thinking fillers (6 categories, 40+ phrases)
  - FlushSentinel for immediate TTS playback
  - Chitchat detection and skip logic
  - FillerHistory to avoid repetition
- **Frontend**: Core hooks, services, and components
- **Integration**: Chat interface with voice support
- **Configuration**: YAML-based with hot-reload
- **Error Handling**: Comprehensive error codes and messages
- **Testing**: 210+ frontend tests, 27 thinking filler tests, 35 backend integration tests

### What's Pending ⏳

- **LiveKit Full Integration**: Complete real-time voice chat infrastructure
- **Backend Tests**: VoiceConfigManager unit tests
- **E2E Tests**: Full user workflow tests

### Key Statistics

| Category | Files | Lines | Status |
|----------|-------|-------|--------|
| Backend REST API | 9 | ~2,100 | ✅ Complete |
| Provider System | 4 | ~1,630 | ✅ Complete |
| Real-Time Features | 2 | ~860 | ✅ Complete |
| Frontend Core | 10 | ~2,800 | ✅ Complete |
| Frontend Tests | 3 | ~2,595 | ✅ Complete |
| Real-Time Tests | 1 | ~650 | ✅ Complete |
| Configuration | 2 | ~250 | ✅ Complete |
| **Total** | **31** | **~10,885** | **96% Complete** |

### Key Achievements

#### ✅ Cost Optimization
- 96% cost savings with OpenAI as default (vs ElevenLabs)
- Flexible cost vs. quality trade-offs
- Usage-based provider selection

#### ✅ Technical Excellence
- Clean architecture following SOLID principles
- Strategy pattern for runtime provider selection
- Comprehensive error handling with automatic fallback
- Type-safe interfaces with Protocol classes

#### ✅ Quality & Reliability
- Multiple provider support (no vendor lock-in)
- Automatic failover on provider outages
- 210+ test cases for hooks
- Health monitoring for all providers

#### ✅ Extensibility
- Easy to add new providers (implement interface)
- Provider-agnostic frontend and backend
- Future-proof for real-time voice (LiveKit)

#### ✅ Real-Time Voice Features (December 13, 2025)
- Natural conversation flow with immediate feedback
- Context-aware thinking fillers eliminate awkward silences
- Chitchat detection for instant responses
- Zero breaking changes, backward compatible
- Production ready with 27/27 tests passing

### Next Steps

1. **Immediate**: Test thinking fillers with live voice sessions
2. **Short-term**: Complete LiveKit full integration
3. **Medium-term**: Add comprehensive E2E testing
4. **Long-term**: Advanced features (VAD, emotion detection, voice cloning, MoE visualization)

---

**Last Updated**: December 13, 2025
**Maintainer**: OpenAgents Team
**Status**: Production Ready (REST API + Provider System + Real-Time Features) | Development (LiveKit Full Integration)
