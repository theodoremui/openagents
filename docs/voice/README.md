# Voice System Documentation

**Last Updated**: December 15, 2025
**Version**: 2.4.0 - With Semantic Endpointing

---

## 📚 Documentation Overview

This directory contains comprehensive documentation for the OpenAgents Voice System, including REST API, real-time voice features, and advanced turn detection.

### Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[voice_implementation.md](./voice_implementation.md)** | Complete implementation guide | Developers, System Architects |
| **[realtime_implementation.md](./realtime_implementation.md)** | Real-time voice features guide | Voice Engineers, Frontend Developers |
| **[semantic_endpointing.md](./semantic_endpointing.md)** | Semantic turn detection system | Voice Engineers, ML Engineers |
| **[visualization.md](./visualization.md)** | Voice interaction visualization | Frontend Developers |
| **[voice_test_plan.md](./voice_test_plan.md)** | Testing strategy and plans | QA Engineers, Developers |

---

## 🎯 Quick Navigation

### For Developers

**Getting Started**:
1. Read [voice_implementation.md](./voice_implementation.md) - Core system architecture
2. Set up configuration in `config/voice_config.yaml`
3. Review [semantic_endpointing.md](./semantic_endpointing.md) - Intelligent turn detection

**Implementing New Features**:
- REST API: See `voice_implementation.md` § API Reference
- Real-time voice: See `realtime_implementation.md`
- Turn detection: See `semantic_endpointing.md` § Implementation Guide

**Troubleshooting**:
- Common issues: `voice_implementation.md` § Troubleshooting
- Semantic endpointing issues: `semantic_endpointing.md` § Troubleshooting
- Test failures: `voice_test_plan.md`

### For System Architects

**Architecture Decisions**:
- Overall system: `voice_implementation.md` § Architecture Overview
- Provider system: `voice_implementation.md` § Provider System
- Semantic endpointing: `semantic_endpointing.md` § Architecture

**Performance & Scalability**:
- REST API performance: `voice_implementation.md` § Performance Optimization
- Real-time latency: `realtime_implementation.md` § Performance
- Semantic endpointing overhead: `semantic_endpointing.md` § Performance Characteristics

### For QA Engineers

**Testing**:
- Test plan: `voice_test_plan.md`
- Semantic endpointing tests: `semantic_endpointing.md` § Testing
- Integration tests: `tests/server/voice/realtime/`

---

## 🚀 Key Features

### 1. REST API Voice Service
- **Status**: ✅ Production Ready
- **Docs**: [voice_implementation.md](./voice_implementation.md)
- **Features**:
  - Text-to-Speech (TTS) with multiple voices
  - Speech-to-Text (STT) with timestamps
  - Multi-provider support (OpenAI, ElevenLabs)
  - Automatic fallback and cost optimization

### 2. Real-Time Voice Chat
- **Status**: ✅ Production Ready
- **Docs**: [realtime_implementation.md](./realtime_implementation.md)
- **Features**:
  - Low-latency voice interactions (<500ms)
  - LiveKit WebRTC integration
  - Thinking fillers and natural responses
  - Session memory for context retention

### 3. Semantic Endpointing (NEW)
- **Status**: ✅ Production Ready (Dec 15, 2025)
- **Docs**: [semantic_endpointing.md](./semantic_endpointing.md)
- **Features**:
  - Intelligent turn detection using linguistic analysis
  - Prevents query fragmentation on long utterances
  - Configurable thresholds for different completeness levels
  - <50ms latency overhead with 85-90% accuracy

---

## 📖 Documentation Structure

### voice_implementation.md (Comprehensive)

**Sections**:
1. Introduction & Features
2. Architecture Overview (REST + Real-Time)
3. Implementation Status (96% complete)
4. Provider System (OpenAI, ElevenLabs, LiveKit)
5. Configuration Management
6. API Reference (8 REST endpoints)
7. Testing & Troubleshooting

**Key Diagrams**:
- System architecture (Frontend → Backend → Providers)
- Provider selection flowchart
- Request/response flows

### realtime_implementation.md

**Sections**:
1. LiveKit Integration
2. WebRTC Architecture
3. Voice Agent Implementation
4. Thinking Fillers System
5. Session Management
6. Performance Optimization

**Key Diagrams**:
- Real-time voice flow
- Thinking filler state machine
- Agent-LLM interaction

### semantic_endpointing.md (NEW)

**Sections**:
1. Problem Statement (query fragmentation)
2. Architecture (Strategy pattern, SOLID design)
3. Core Components (SemanticEndpointer, LinguisticStrategy, BufferedSTT)
4. Decision Flow (CONTINUE/WAIT/ENDPOINT)
5. Implementation Guide (step-by-step)
6. Configuration Profiles (Conservative, Balanced, Responsive)
7. Testing (Unit + Integration)
8. Performance Characteristics (<50ms overhead)

**Key Diagrams**:
- High-level system overview
- Component interaction sequence
- Data flow architecture
- Endpointing decision tree
- Example decision paths

**Code Examples**:
- SemanticEndpointer usage
- BufferedSTT integration
- Custom strategy implementation
- Configuration tuning

---

## 🔧 Configuration

All voice features are configured via **`config/voice_config.yaml`**:

```yaml
voice:
  # Provider configuration
  default_provider: "openai"
  providers:
    openai: { ... }
    elevenlabs: { ... }

  # Real-time voice
  realtime:
    enabled: true
    livekit: { ... }

    # Semantic Endpointing (NEW)
    semantic_endpointing:
      enabled: true
      min_silence_ambiguous: 0.6
      min_silence_complete: 1.0
      max_buffer_duration: 30.0
      confidence_threshold: 0.7
```

**Configuration Profiles**:
- **Conservative**: High accuracy, longer waits (good for complex queries)
- **Balanced**: Default settings (recommended for general use)
- **Responsive**: Low latency, faster responses (good for simple queries)

See `semantic_endpointing.md` § Configuration for full details.

---

## 🧪 Testing

### Test Files

| Test File | Coverage | Purpose |
|-----------|----------|---------|
| `test_semantic_endpointing.py` | 95% | Core semantic analysis logic |
| `test_buffered_stt.py` | 90% | STT buffering and integration |
| `tests/server/voice/realtime/` | 85% | Real-time voice features |
| `frontend_web/__tests__/hooks/` | 80% | Frontend voice hooks |

### Running Tests

```bash
# Semantic endpointing tests
pytest tests/server/voice/realtime/test_semantic_endpointing.py -v

# BufferedSTT tests
pytest tests/server/voice/realtime/test_buffered_stt.py -v

# All voice tests
pytest tests/server/voice/ -v

# Frontend tests
cd frontend_web && npm test -- voice
```

---

## 🎓 Learning Path

### Beginner

1. **Start Here**: `voice_implementation.md` § Introduction
2. **Quick Start**: `voice_implementation.md` § Quick Start Guide
3. **Basic Usage**: Test with `/voice/synthesize` endpoint

### Intermediate

1. **Real-Time Voice**: `realtime_implementation.md`
2. **Configuration**: `voice_config.yaml` reference
3. **Multi-Provider**: `voice_implementation.md` § Provider System

### Advanced

1. **Semantic Endpointing**: `semantic_endpointing.md` (full guide)
2. **Custom Strategies**: Implement `IEndpointingStrategy`
3. **Performance Tuning**: `semantic_endpointing.md` § Performance

---

## 🐛 Troubleshooting Quick Reference

### Query Fragmentation

**Symptom**: Long queries broken into multiple parts
**Solution**: Enable semantic endpointing in `voice_config.yaml`
**Docs**: `semantic_endpointing.md` § Issue 1

### Slow Response Times

**Symptom**: Agent takes too long to respond
**Solution**: Decrease silence thresholds in config
**Docs**: `semantic_endpointing.md` § Issue 2

### High CPU Usage

**Symptom**: CPU spikes during voice interactions
**Solution**: Disable semantic endpointing logging in production
**Docs**: `semantic_endpointing.md` § Issue 5

### Provider Failures

**Symptom**: TTS/STT requests failing
**Solution**: Check provider config and API keys
**Docs**: `voice_implementation.md` § Troubleshooting

---

## 📊 System Status

| Component | Status | Version | Last Updated |
|-----------|--------|---------|--------------|
| REST API | ✅ Production | 2.3.0 | Dec 13, 2025 |
| Real-Time Voice | ✅ Production | 2.3.0 | Dec 13, 2025 |
| Semantic Endpointing | ✅ Production | 2.4.0 | Dec 15, 2025 |
| OpenAI Provider | ✅ Active | 2.3.0 | Dec 13, 2025 |
| ElevenLabs Provider | ✅ Active | 2.3.0 | Dec 13, 2025 |
| LiveKit Integration | ✅ Active | 2.4.0 | Dec 15, 2025 |

---

## 🔮 Future Enhancements

### Planned Features

1. **ML-Based Endpointing**: Replace rule-based with trained model
2. **Prosodic Analysis**: Add audio-based features (pitch, energy)
3. **Context-Aware Endpointing**: Use conversation history
4. **Multi-Language Support**: Extend linguistic rules for other languages
5. **Voice Cloning**: Custom voice profiles
6. **Emotion Detection**: Detect user emotion from voice

### Research Areas

- **Advanced Turn Detection**: Google Duplex-style turn detection
- **Multimodal Endpointing**: Combine audio, video, and text signals
- **Adaptive Thresholds**: Learn optimal thresholds per user

See `semantic_endpointing.md` § Future Enhancements for details.

---

## 📞 Support & Contributing

### Getting Help

- **Documentation Issues**: Check `voice_implementation.md` § Troubleshooting
- **Semantic Endpointing**: See `semantic_endpointing.md` § Troubleshooting
- **Bug Reports**: File issue with relevant logs and config

### Contributing

When contributing voice features:

1. **Read Documentation**: Understand architecture first
2. **Follow Patterns**: Use existing provider/strategy patterns
3. **Add Tests**: Minimum 80% coverage required
4. **Update Docs**: Update relevant documentation files
5. **Performance**: Ensure <50ms overhead for real-time features

---

## 📝 Version History

### 2.4.0 (December 15, 2025) - Semantic Endpointing

- ✅ Added `SemanticEndpointer` with linguistic analysis
- ✅ Implemented `BufferedSTT` wrapper for LiveKit integration
- ✅ Added configuration for semantic endpointing
- ✅ Created comprehensive tests (95% coverage)
- ✅ Documented with mermaid diagrams and code examples

### 2.3.0 (December 13, 2025) - Real-Time Features

- ✅ Thinking filler system
- ✅ Chitchat detection
- ✅ Immediate TTS playback
- ✅ Session memory integration

### 2.2.0 (Earlier) - Provider System

- ✅ Multi-provider architecture
- ✅ OpenAI as default provider
- ✅ ElevenLabs premium option
- ✅ Automatic fallback

---

## 📚 Additional Resources

### External Documentation

- [LiveKit Agents SDK](https://docs.livekit.io/agents/)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [Google Duplex Paper](https://ai.googleblog.com/2018/05/duplex-ai-system-for-natural-conversation.html)

### Related OpenAgents Docs

- `docs/IMPLEMENTATION_GUIDE.md` - Overall system guide
- `config/voice_config.yaml` - Configuration reference
- `server/voice/README.md` - Server-side voice module

---

**Document Version**: 1.0
**Last Updated**: December 15, 2025
**Maintainer**: OpenAgents Team
