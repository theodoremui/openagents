# Real-Time Voice Agent System

Production-ready real-time voice conversation system using LiveKit Agents framework.

## Unified Configuration

**Important:** Real-time voice shares configuration with the async voice system in `config/voice_config.yaml`.

The `realtime` section configures real-time-specific settings (LiveKit, VAD, turn detection), while STT/TTS settings are inherited from the main `voice` configuration for consistency.

## Preventing "Killed: 9" / Exit 137 (OS SIGKILL)

If the worker starts and then abruptly exits with `Killed: 9` (exit code 137), it’s usually **the OS terminating the process due to memory pressure**.

By default, LiveKit Agents keeps multiple idle subprocesses in production mode. Each subprocess imports heavy dependencies (e.g. `torch`/onnx via plugins), so laptops can get OOM-killed even before you handle any calls.

OpenAgents now defaults to **1 idle process** to keep memory stable, and exposes worker tuning under `voice.realtime.worker`:

```yaml
voice:
  realtime:
    worker:
      num_idle_processes: 1
      # 0 => auto-pick port for the worker HTTP server
      port: 0
      # Memory guardrails (MB) per job process; 0 disables hard limit
      job_memory_warn_mb: 700
      job_memory_limit_mb: 0
      load_threshold: 0.7
      agent_name: "openagents-voice"
```

Env overrides (useful for quick experiments):
- `OPENAGENTS_LIVEKIT_NUM_IDLE_PROCESSES`
- `OPENAGENTS_LIVEKIT_JOB_MEMORY_WARN_MB`
- `OPENAGENTS_LIVEKIT_JOB_MEMORY_LIMIT_MB`
- `OPENAGENTS_LIVEKIT_LOAD_THRESHOLD`
- `OPENAGENTS_LIVEKIT_WORKER_PORT`
- `OPENAGENTS_LIVEKIT_AGENT_NAME`

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

This installs the unified voice system dependencies including:
- `livekit`, `livekit-agents`, `livekit-api` - LiveKit framework
- `livekit-plugins-openai`, `livekit-plugins-silero` - Plugins
- `loguru` - Structured logging

### 2. Configure Environment

Add to your `.env` file:

```bash
# OpenAI API Key (shared with async voice)
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# LiveKit Credentials (get from https://cloud.livekit.io)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxx
LIVEKIT_API_SECRET=xxx
```

### 3. Configure Unified Voice System

Edit `config/voice_config.yaml` - the `realtime` section is already configured:

```yaml
voice:
  # Existing async voice settings...
  providers:
    openai:
      tts:
        voice: "coral"  # Shared with real-time
        model: "gpt-4o-mini-tts"
      stt:
        model: "gpt-4o-transcribe"

  # Real-time voice settings
  realtime:
    enabled: true
    agent:
      type: smart_router  # or single_agent
      instructions: |
        You are a helpful voice assistant...
```

### 4. Start Backend Server

```bash
cd server
python -m server.main
```

Expected output:
```
✓ Voice module API endpoints registered
✓ Real-time voice module API endpoints registered
```

### 5. Start Voice Agent Worker

In a separate terminal:

```bash
python -m server.voice.realtime.worker
```

## Architecture

### Unified Configuration Flow

```
config/voice_config.yaml
├── voice.providers.openai.tts     → Used by both async & realtime
├── voice.providers.openai.stt     → Used by both async & realtime
├── voice.voice_profiles           → Shared profiles
└── voice.realtime                 → Real-time specific settings
    ├── livekit (credentials from env)
    ├── vad
    ├── turn_detection
    ├── interruptions
    ├── agent
    ├── audio
    └── limits
```

### Component Integration

```
┌─────────────────────────────────────┐
│   Unified Voice Configuration       │
│   (config/voice_config.yaml)        │
└──────────┬──────────────┬───────────┘
           │              │
  ┌────────▼──────┐  ┌───▼──────────┐
  │ Async Voice   │  │ Real-time    │
  │ (ElevenLabs/  │  │ Voice        │
  │  OpenAI TTS)  │  │ (LiveKit)    │
  └───────────────┘  └──────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
        ┌───▼───┐     ┌────▼────┐   ┌───▼────┐
        │  STT  │     │   LLM   │   │  TTS   │
        │OpenAI │     │SmartRouter│ │ OpenAI │
        └───────┘     │SingleAgent│ └────────┘
                      └────┬──────┘
                           │
                  ┌────────▼──────────┐
                  │  Existing Agents  │
                  │  Tools & MCP      │
                  └───────────────────┘
```

## API Endpoints

All real-time voice endpoints are under `/voice/realtime`:

### Create Session

```bash
curl -X POST http://localhost:8000/voice/realtime/session \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "smart_router",
    "initial_greeting": true
  }'
```

Response:
```json
{
  "session_id": "uuid",
  "room_name": "voice-user-uuid",
  "token": "jwt_token",
  "url": "wss://your-project.livekit.cloud"
}
```

### Get Session Status

```bash
curl http://localhost:8000/voice/realtime/session/{session_id} \
  -H "X-API-Key: your_key"
```

### End Session

```bash
curl -X DELETE http://localhost:8000/voice/realtime/session/{session_id} \
  -H "X-API-Key: your_key"
```

### Get Configuration

```bash
curl http://localhost:8000/voice/realtime/config \
  -H "X-API-Key: your_key"
```

### Health Check

```bash
curl http://localhost:8000/voice/realtime/health
```

## Configuration Details

### Shared Settings (voice.providers.openai)

These settings are used by BOTH async and real-time voice:

```yaml
voice:
  providers:
    openai:
      tts:
        voice: "coral"        # Used by real-time TTS
        model: "gpt-4o-mini-tts"
        speed: 1.0
      stt:
        model: "gpt-4o-transcribe"  # Used by real-time STT
        language: null
```

### Real-Time Specific Settings (voice.realtime)

```yaml
voice:
  realtime:
    enabled: true

    # LiveKit credentials from environment
    livekit:
      room_empty_timeout: 300
      max_participants: 2

    # Voice Activity Detection
    vad:
      provider: silero
      threshold: 0.5
      min_speech_duration: 0.1
      max_speech_duration: 30.0

    # Turn detection for conversation flow
    turn_detection:
      enabled: true
      min_endpointing_delay: 0.5
      max_endpointing_delay: 3.0

    # Allow user interruptions
    interruptions:
      allow: true
      min_duration: 0.5

    # Agent behavior
    agent:
      type: smart_router  # or single_agent
      instructions: |
        You are a helpful voice assistant...
      initial_greeting: true

    # Background audio (optional)
    audio:
      enable_thinking_sound: true
      thinking_volume: 0.3

    # Session limits
    limits:
      max_sessions_per_user: 3
      max_session_duration: 3600
      token_ttl_hours: 2
```

## Voice Profiles

Voice profiles are shared between async and real-time systems:

```yaml
voice:
  voice_profiles:
    default:
      provider: "openai"
      voice_id: "coral"
      model_id: "gpt-4o-mini-tts"

    professional:
      provider: "openai"
      voice_id: "echo"
      model_id: "gpt-4o-mini-tts"
      speed: 0.9
```

Real-time voice automatically uses the configured voice from `providers.openai.tts`.

## Monitoring

### Health Check

```bash
curl http://localhost:8000/voice/realtime/health
```

Response:
```json
{
  "status": "healthy",
  "livekit_connected": true,
  "livekit_url": "wss://...",
  "active_rooms": 2,
  "active_sessions": 3,
  "timestamp": "2025-12-10T..."
}
```

### Logs

The system uses `loguru` for structured logging:

```
INFO: Real-time voice configuration loaded successfully
INFO: Voice agent job dispatched: room=voice-user-abc
INFO: Connected to room successfully
INFO: Agent session started successfully
```

## Troubleshooting

### Issue: Configuration not loading

**Check:**
1. `config/voice_config.yaml` exists
2. YAML syntax is valid
3. `voice.realtime` section is present

**Test:**
```bash
python -c "from server.voice.realtime.config import RealtimeVoiceConfig; RealtimeVoiceConfig.load()"
```

### Issue: LiveKit connection fails

**Check:**
1. Environment variables set: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
2. URL format is `wss://...` (WebSocket Secure)
3. API credentials are valid

**Test:**
```bash
curl http://localhost:8000/voice/realtime/health
```

### Issue: Voice quality issues

**Optimize:**
1. Adjust TTS settings in `voice.providers.openai.tts`
2. Lower `turn_detection.min_endpointing_delay` for faster responses
3. Use `gpt-4o` LLM for better quality (configured in code)

## Benefits of Unified Configuration

1. **No Duplication**: STT/TTS settings defined once
2. **Consistency**: Both async and real-time use same voice
3. **Easy Management**: Single config file to maintain
4. **Profile Sharing**: Voice profiles work across both systems
5. **Provider Flexibility**: Easy to switch between OpenAI/ElevenLabs

## Development

### Project Structure

```
server/voice/
├── config.py              # Shared config manager
├── models.py              # Shared models (includes RealtimeSession*)
├── realtime/
│   ├── config.py          # Real-time config accessor
│   ├── models.py          # Re-exports from parent
│   ├── service.py         # Session management
│   ├── agent.py           # Voice agent
│   ├── worker.py          # Worker process
│   └── router.py          # FastAPI endpoints
```

### Adding Custom Configuration

1. Edit `config/voice_config.yaml` under `voice.realtime`
2. Add property to `RealtimeVoiceConfig` class
3. Use in `VoiceAgent` or `worker.py`

## Documentation

- [Full Implementation Guide](/.kiro/specs/voice/REALTIME_VOICE_IMPLEMENTATION.md)
- [Voice Specification](/.kiro/specs/voice/real-time-voice.md)
- [LiveKit Agents Docs](https://docs.livekit.io/agents/build/)

---

**Version**: 1.0 (Unified Configuration)
**Status**: Production Ready
**Last Updated**: December 10, 2025
