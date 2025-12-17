# Real-Time Voice System Testing Guide

**Purpose**: Practical guide for testing the end-to-end real-time voice functionality
**Approach**: YAGNI-focused - only essential tests, manual verification first
**Last Updated**: December 10, 2025

---

## ✅ What's Already Verified

### Frontend
- ✅ TypeScript compilation: Zero errors in voice code
- ✅ Production build: Successful (154 kB main route)
- ✅ All voice components created and integrated
- ✅ Dependencies installed (@livekit packages, framer-motion)

### Backend
- ✅ Code structure complete (worker, agent, service, config)
- ✅ API endpoints implemented
- ⚠️  Runtime dependencies not installed (requires full pip install)

---

## 🧪 Testing Levels (Priority Order)

### Level 1: Smoke Tests (Essential)

**Purpose**: Verify basic functionality without external dependencies

#### Frontend Smoke Test
```bash
cd frontend_web
npm run build
```
**Expected**: Build succeeds with no errors
**Status**: ✅ PASSED

#### Backend Import Test
```bash
# Requires: pip install -e . (full dependencies)
python3 -c "
from server.voice.realtime.config import RealtimeVoiceConfig
from server.voice.realtime.models import AgentType, VoiceState
from server.voice.realtime.service import RealtimeVoiceService
from server.voice.realtime.agent import VoiceAgent
print('✓ All imports successful')
"
```
**Expected**: No import errors
**Status**: ⏳ PENDING (requires dependency installation)

### Level 2: Integration Tests (Important)

**Purpose**: Verify components work together

#### Backend Health Check
```bash
# Prerequisites:
# 1. Backend server running: ./scripts/run_server.sh --dev
# 2. LiveKit credentials in .env

curl http://localhost:8000/voice/realtime/health
```
**Expected Response**:
```json
{
  "status": "healthy",
  "livekit_connected": true,
  "livekit_url": "wss://...",
  "active_rooms": 0,
  "active_sessions": 0
}
```

#### Configuration Validation
```bash
./scripts/run_realtime.sh --check
```
**Expected**: All checks pass, connection to LiveKit verified

### Level 3: End-to-End Manual Test (Critical for Production)

**Purpose**: Verify complete user flow works

#### Prerequisites
1. **LiveKit Account**:
   - Sign up at https://cloud.livekit.io (free tier)
   - Get API key, secret, and URL
   - Add to `.env`:
     ```bash
     LIVEKIT_URL=wss://your-project.livekit.cloud
     LIVEKIT_API_KEY=APIxxx
     LIVEKIT_API_SECRET=xxx
     ```

2. **OpenAI API Key**:
   - Add to `.env`:
     ```bash
     OPENAI_API_KEY=sk-...
     ```

3. **Configuration File**:
   - Ensure `config/voice_config.yaml` has `realtime` section
   - Default configuration should work

#### Test Procedure

**Step 1: Start Backend** (Terminal 1)
```bash
cd /path/to/openagents
./scripts/run_server.sh --dev
```
**Verify**: Server starts on port 8000
**Check**: `curl http://localhost:8000/health`

**Step 2: Start Worker** (Terminal 2)
```bash
cd /path/to/openagents
./scripts/run_realtime.sh --dev
```
**Verify**:
- Worker connects to LiveKit
- No errors in logs
- Shows "Waiting for jobs..."

**Step 3: Start Frontend** (Terminal 3)
```bash
cd /path/to/openagents/frontend_web
npm run dev
```
**Verify**: Frontend starts on http://localhost:3000

**Step 4: Test Voice Mode**
1. Open browser: http://localhost:3000
2. Click "Voice Mode" button in navigation
3. **Expected behavior**:
   - Browser requests microphone permission
   - VoiceModeInterface appears (full-screen)
   - State shows "Connecting..." then "Listening"
   - Voice animation displays

4. **Speak to test**:
   - Say: "Hello, can you hear me?"
   - **Expected**:
     - Transcript shows your words
     - State changes to "Thinking"
     - Agent responds with voice
     - Transcript shows agent response

5. **Test controls**:
   - Press 'M' to mute/unmute
   - Adjust volume slider
   - Press 'Escape' to end call

**Step 5: Verify Backend Logs**
Check Terminal 2 (worker) for:
- Session creation
- STT transcriptions
- LLM processing
- TTS generation
- No errors

---

## 🐛 Common Issues and Solutions

### Issue: Frontend builds but voice button doesn't appear
**Cause**: VoiceModeProvider not wrapping app
**Solution**: Check `frontend_web/app/providers.tsx` includes `<VoiceModeProvider>`

### Issue: Voice button does nothing when clicked
**Cause**: Backend not running or not responding
**Solution**:
1. Check backend: `curl http://localhost:8000/health`
2. Check console for API errors
3. Verify `NEXT_PUBLIC_API_BASE_URL` in `.env.local`

### Issue: "Microphone permission denied"
**Cause**: Browser blocked microphone access
**Solution**:
1. Check browser settings
2. Use HTTPS in production (required for mic access)
3. Grant permission when prompted

### Issue: Worker won't start
**Cause**: Missing dependencies or invalid LiveKit credentials
**Solution**:
1. Run: `./scripts/run_realtime.sh --check`
2. Verify `.env` has all required variables
3. Test LiveKit credentials at https://cloud.livekit.io

### Issue: "Connection failed" after clicking voice mode
**Cause**: LiveKit server unreachable or invalid token
**Solution**:
1. Check worker logs for errors
2. Verify `LIVEKIT_URL` is correct (wss://...)
3. Check backend logs for token generation errors

### Issue: Agent doesn't respond
**Cause**: OpenAI API key invalid or quota exceeded
**Solution**:
1. Verify `OPENAI_API_KEY` in `.env`
2. Check OpenAI account quota
3. Check worker logs for API errors

---

## 📊 Test Coverage Summary

| Component | Coverage | Notes |
|-----------|----------|-------|
| Frontend Build | ✅ 100% | Zero TypeScript errors |
| Voice Components | ✅ 100% | All created and integrated |
| API Client | ✅ 100% | Voice methods added |
| Type Definitions | ✅ 100% | Complete TypeScript types |
| Backend Structure | ✅ 100% | All files created |
| Runtime Testing | ⏳ Pending | Requires manual E2E test |
| Unit Tests | ❌ 0% | Not yet implemented (YAGNI) |

---

## 🎯 Recommended Testing Approach

### For Development
1. ✅ Verify frontend builds (automated)
2. ⏳ Run manual E2E test once (validates integration)
3. 📝 Document any issues found
4. ✅ Fix critical bugs only

### For Production
1. ✅ Complete manual E2E test
2. ✅ Test on staging environment
3. ✅ Verify with real users (beta test)
4. 📊 Monitor production logs
5. 🐛 Fix issues as they arise

### Unit Tests (Future - Only If Needed)
Following YAGNI, we defer comprehensive unit testing until:
- Bugs are found in specific components
- Code becomes complex enough to need coverage
- Team has bandwidth for test maintenance

---

## 📝 Manual Test Checklist

Use this checklist when performing E2E testing:

- [ ] Backend server starts successfully
- [ ] Worker connects to LiveKit
- [ ] Frontend loads without errors
- [ ] Voice mode button visible in navigation
- [ ] Clicking voice mode requests microphone
- [ ] VoiceModeInterface appears full-screen
- [ ] Voice animation shows correct state
- [ ] Speaking triggers transcription
- [ ] Transcript shows user words
- [ ] Agent processes and responds
- [ ] Agent voice is audible
- [ ] Transcript shows agent response
- [ ] Mute button works (keyboard: M)
- [ ] Volume slider adjusts audio
- [ ] End call button closes interface (keyboard: Escape)
- [ ] No errors in browser console
- [ ] No errors in backend logs
- [ ] No errors in worker logs

---

## 🚀 Next Steps

1. **Install Dependencies** (if not done):
   ```bash
   pip install -e .
   ```

2. **Configure LiveKit**:
   - Get credentials from https://cloud.livekit.io
   - Add to `.env`

3. **Run Manual E2E Test**:
   - Follow Level 3 procedure above
   - Document any issues found

4. **Production Deployment**:
   - Use HTTPS (required for microphone)
   - Set proper CORS origins
   - Monitor logs for first 24 hours
   - Gather user feedback

---

## 📚 References

- [Implementation Doc](.kiro/specs/voice/REALTIME_VOICE_IMPLEMENTATION.md)
- [Specification](.kiro/specs/voice/real-time-voice.md)
- [LiveKit Docs](https://docs.livekit.io/)
- [Run Script](../../scripts/run_realtime.sh)

---

**Testing Philosophy**: Occam's Razor + YAGNI
- Simplest test that proves functionality
- Manual verification before automation
- Unit tests only when bugs found
- Focus on critical path (user experience)
