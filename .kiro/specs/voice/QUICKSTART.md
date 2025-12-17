# Real-Time Voice Quick Start Guide

**Goal**: Get real-time voice working in 10 minutes
**Prerequisites**: Python 3.11+, Node.js 18+, npm

---

## 🚀 Quick Start (3 Steps)

### Step 1: Get LiveKit Credentials (2 minutes)

1. Go to https://cloud.livekit.io
2. Sign up (free tier - no credit card required)
3. Create a new project
4. Copy your credentials from the dashboard:
   - **API Key** (starts with `API`)
   - **API Secret** (long random string)
   - **WebSocket URL** (starts with `wss://`)

### Step 2: Configure Environment (2 minutes)

Create or edit `.env` in project root:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxx

# OpenAI Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# Backend Configuration (already set if server works)
AUTH_ENABLED=false
HOST=0.0.0.0
PORT=8000
```

**Frontend**: Create `frontend_web/.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=
```

### Step 3: Start Everything (3 minutes)

**Terminal 1 - Install Dependencies**:
```bash
# Install Python dependencies (includes LiveKit)
pip install -e .

# Install frontend dependencies
cd frontend_web
npm install
cd ..
```

**Terminal 2 - Start Backend**:
```bash
python -m server.main
# Wait for: "Application startup complete"
# Verify: curl http://localhost:8000/health
```

**Terminal 3 - Start Worker**:
```bash
./scripts/run_realtime.sh --dev
# Wait for: "Worker started successfully"
# Should show: "Waiting for jobs..."
```

**Terminal 4 - Start Frontend**:
```bash
cd frontend_web
npm run dev
# Wait for: "Ready in Xms"
# Open: http://localhost:3000
```

---

## 🎤 Test Voice Mode (2 minutes)

1. **Open Browser**: http://localhost:3000
2. **Click** "Voice Mode" button (top navigation, microphone icon)
3. **Allow** microphone permission when prompted
4. **Wait** for "Listening" state (green indicator)
5. **Say**: "Hello, can you hear me?"
6. **Watch**: Transcript appears, agent responds with voice
7. **End**: Press Escape or click "End Call" button

**Success Indicators**:
- 🟢 Green indicator shows "Listening"
- 📝 Your words appear in transcript
- 🗣️ Agent responds with voice
- 📝 Agent response appears in transcript

---

## 🐛 Troubleshooting (1 minute each)

### Voice button doesn't appear
- ✅ Check: Frontend built successfully (`npm run build`)
- ✅ Check: Browser console for errors
- ✅ Reload page

### "Connection failed" error
- ✅ Check: Backend running (`curl http://localhost:8000/health`)
- ✅ Check: Worker running (should show "Waiting for jobs")
- ✅ Check: `.env` has correct LiveKit credentials
- ✅ Run: `./scripts/run_realtime.sh --check`

### Microphone permission denied
- ✅ Check: Browser settings → Site settings → Microphone
- ✅ Note: Microphone requires HTTPS in production
- ✅ Click lock icon in address bar → Allow microphone

### Worker fails to start
- ✅ Check: `pip install -e .` completed without errors
- ✅ Check: `.env` has all required variables
- ✅ Run: `./scripts/run_realtime.sh --check`

### Agent doesn't respond
- ✅ Check: OpenAI API key valid
- ✅ Check: OpenAI account has quota
- ✅ Check: Worker logs for errors (Terminal 3)

---

## 📱 Using Voice Mode

### Controls
- **Mute/Unmute**: Click mic button or press `M`
- **Volume**: Adjust slider (0-100%)
- **End Call**: Click phone button or press `Escape`

### States
- **Disconnected**: Gray - Not connected
- **Connecting**: Amber - Establishing connection
- **Listening**: Green - Speak now
- **Thinking**: Blue - Processing your request
- **Speaking**: Purple - Agent is responding

### Tips
- Speak naturally, pause when done
- You can interrupt the agent anytime
- Conversation history is maintained
- Sessions auto-expire after 2 hours

---

## 🔧 Configuration Options

### Change Agent Behavior

Edit `config/voice_config.yaml` under `realtime:` section:

```yaml
realtime:
  # Agent type: smart_router or single_agent
  agent_type: smart_router

  # Default agent for single_agent mode
  default_agent_id: "one"

  # Voice settings
  stt_model: whisper-1
  tts_voice: alloy
  tts_speed: 1.0

  # Behavior
  enable_interruptions: true
  initial_greeting: true
```

### Change Voice Model

Available TTS voices (OpenAI):
- `alloy` - Neutral (default)
- `echo` - Male, clear
- `fable` - British accent
- `onyx` - Deep male
- `nova` - Female, upbeat
- `shimmer` - Female, warm

Change in config or via API:
```bash
curl -X POST http://localhost:8000/voice/realtime/session \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "smart_router",
    "agent_config": {"tts_voice": "nova"}
  }'
```

---

## 📊 Verify Installation

### Health Check
```bash
# Backend
curl http://localhost:8000/health

# Voice system
curl http://localhost:8000/voice/realtime/health
```

**Expected**:
```json
{
  "status": "healthy",
  "livekit_connected": true,
  "active_rooms": 0,
  "active_sessions": 0
}
```

### Configuration Check
```bash
./scripts/run_realtime.sh --check
```

**Expected**:
```
✓ Python 3.12 found
✓ Voice configuration file found
✓ Environment file found
✓ LIVEKIT_URL configured
✓ LIVEKIT_API_KEY configured
✓ LIVEKIT_API_SECRET configured
✓ OPENAI_API_KEY configured
✓ Configuration loaded successfully
✓ LiveKit server is reachable
✓ All checks passed
```

---

## 🎯 What's Next?

### Customize Agent
- Edit agent instructions in `config/open_agents.yaml`
- Add tools to agents for more capabilities
- Configure SmartRouter for multi-agent workflows

### Deploy to Production
1. Get production LiveKit credentials
2. Set up HTTPS (required for microphone)
3. Configure CORS for your domain
4. Use environment-specific configs
5. Monitor logs and usage

### Advanced Features
- Background audio (thinking sounds)
- Custom turn detection
- Multi-modal support (future)
- Analytics and metrics

---

## 📚 Full Documentation

- **Testing Guide**: `.kiro/specs/voice/TESTING_GUIDE.md`
- **Implementation Details**: `.kiro/specs/voice/REALTIME_VOICE_IMPLEMENTATION.md`
- **Specification**: `.kiro/specs/voice/real-time-voice.md`
- **LiveKit Docs**: https://docs.livekit.io/agents/build/

---

## 🆘 Getting Help

1. **Check Logs**: Terminal output shows detailed errors
2. **Run Diagnostics**: `./scripts/run_realtime.sh --check`
3. **Review Issues**: Common problems in TESTING_GUIDE.md
4. **LiveKit Status**: https://status.livekit.io/

---

**Time to working voice**: ~10 minutes
**Difficulty**: Easy (if you follow steps)
**Support**: Full implementation documentation available
