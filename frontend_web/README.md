# OpenAgents Frontend

Modern, type-safe Next.js frontend for the OpenAgents multi-agent orchestration system with sophisticated glass morphism UI design.

## ✨ Features

### Core Functionality
- ✅ **Agent Execution** - Interactive chat interface with three execution modes (Mock, Real, Stream)
- ✅ **Configuration Editor** - YAML editor with validation and syntax highlighting
- ✅ **Graph Visualization** - Interactive ReactFlow graph of agent relationships
- ✅ **Type-Safe API Client** - Full TypeScript support with error handling
- ✅ **Session Management** - Persistent conversation history per agent
- ✅ **Voice Interaction** - Dual-mode voice support (REST + LiveKit)

### Voice Features (NEW)
- ✅ **REST Voice Mode** - Asynchronous voice interaction
  - Speech-to-Text (STT) with word timestamps
  - Text-to-Speech (TTS) with voice customization
  - Voice profiles (default, professional, conversational)
  - Voice settings (volume, speed, auto-play)
- ✅ **LiveKit Voice Mode** - Real-time voice chat (optional)
  - WebRTC streaming (<500ms latency)
  - Conversational AI with interruption support
  - Voice room management
  - Audio quality optimization
- ✅ **Voice Input Panel** - Integrated into chat interface
- ✅ **Audio Visualization** - Real-time level indicators
- ✅ **Voice Context** - Global voice state management

### Modern UI/UX
- ✅ **Glass Morphism Design** - Contemporary frosted glass aesthetic with backdrop blur
- ✅ **Smart Scrolling** - Intelligent auto-scroll that respects manual scrolling
- ✅ **Markdown Rendering** - Rich text support with images, code blocks, tables, and more
- ✅ **Collapsible Panels** - Customizable workspace with individually collapsible sections
- ✅ **Responsive Design** - Works seamlessly on desktop, tablet, and mobile
- ✅ **Accessibility** - WCAG 2.1 AA compliant with keyboard navigation and screen reader support

### Developer Experience
- ✅ **Comprehensive Tests** - 310+ tests with >90% coverage (backend + frontend)
- ✅ **TypeScript** - Strict typing throughout the codebase
- ✅ **Service Layer** - Clean architecture with dependency injection
- ✅ **Hot Reload** - Fast development with Next.js dev server

## 🏗️ Tech Stack

- **Framework**: Next.js 14.2.33 with App Router (upgradeable to 16.x)
- **Language**: TypeScript 5
- **UI Library**: React 18.3.1 (upgradeable to 19.x)
- **Styling**: Tailwind CSS with custom design system
- **Components**: shadcn/ui (Radix UI primitives)
- **Markdown**: react-markdown with GFM support
- **Graph**: ReactFlow for agent visualization
- **Editor**: Monaco Editor for YAML editing
- **Testing**: Jest + React Testing Library
- **State**: React hooks + Context API (Dependency Injection)

## 📦 Installation

```bash
# Install dependencies (use --legacy-peer-deps for compatibility)
npm install --legacy-peer-deps

# Create environment file
cp .env.local.example .env.local

# Edit .env.local and configure (see Configuration section below)
```

## 🚀 Quick Start

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

The app will be available at `http://localhost:3000` with hot-reload enabled.

## ⚙️ Configuration

The frontend uses `.env.local` for environment configuration. This file is **gitignored** and should be created locally.

### Required Configuration

Create `.env.local` in the `frontend_web/` directory:

```bash
# ============================================================================
# API Configuration (REQUIRED)
# ============================================================================

# Backend API URL (FastAPI server)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# API authentication key (must match backend API_KEYS)
NEXT_PUBLIC_API_KEY=your_secure_api_key_here

# Google Maps API key (for geo/map agents)
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_key_here

# ============================================================================
# Voice Configuration (OPTIONAL - for Voice features)
# ============================================================================

# Voice features are automatically available if backend is configured
# No frontend-specific voice environment variables needed
# Backend handles ElevenLabs API credentials

# ============================================================================
# LiveKit Configuration (OPTIONAL - for Real-time Voice Chat)
# ============================================================================

# Frontend: Only needs public WebSocket URL
NEXT_PUBLIC_LIVEKIT_URL=wss://voice-agent-jojp5ml5.livekit.cloud

# Backend: Requires API credentials (DO NOT prefix with NEXT_PUBLIC_)
# These stay server-side only for security
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://voice-agent-jojp5ml5.livekit.cloud

# ============================================================================
# Optional Configuration
# ============================================================================

# Enable debug logging in browser console
NEXT_PUBLIC_DEBUG=false
```

### Environment Variables Explained

#### API Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | ✅ Yes | Backend FastAPI server URL | `http://localhost:8000` |
| `NEXT_PUBLIC_API_KEY` | ✅ Yes | API authentication key | `your_secure_key_123` |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | ⚠️ For geo agents | Google Maps API key | `AIzaSy...` |

#### Voice Configuration (REST Voice)

Voice features work automatically if the backend is configured with `ELEVENLABS_API_KEY`. No frontend environment variables are needed for REST voice.

**Backend Setup** (in `server/.env`):
```bash
ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

**Features Available**:
- ✅ Speech-to-Text (STT) - Transcribe voice input
- ✅ Text-to-Speech (TTS) - Synthesize voice output
- ✅ Voice profiles (default, professional, conversational)
- ✅ Voice settings (volume, speed, auto-play)

#### LiveKit Configuration (Real-time Voice Chat)

For **real-time, conversational voice interactions** using LiveKit:

**Security Model**:
```
Frontend (Public)          Backend (Private)
├─ NEXT_PUBLIC_LIVEKIT_URL  ├─ LIVEKIT_API_KEY ⚠️ Secret
│  (WebSocket URL)          ├─ LIVEKIT_API_SECRET ⚠️ Secret
│                           └─ LIVEKIT_URL
│
└─ Requests token from backend (POST /voice/livekit/rooms)
   Backend generates token using API credentials
   Frontend connects to LiveKit with token (not credentials)
```

**Why This Design?**
- ✅ Frontend never sees API credentials (secure)
- ✅ Backend generates time-limited tokens per session
- ✅ Tokens can be scoped to specific rooms
- ✅ Follows LiveKit security best practices

**Frontend Variables**:
| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_LIVEKIT_URL` | ✅ For LiveKit | WebSocket URL (safe to expose) |

**Backend Variables** (in `server/.env`):
| Variable | Required | Description |
|----------|----------|-------------|
| `LIVEKIT_API_KEY` | ✅ For LiveKit | API key (keep secret) |
| `LIVEKIT_API_SECRET` | ✅ For LiveKit | API secret (keep secret) |
| `LIVEKIT_URL` | ✅ For LiveKit | WebSocket URL |

**LiveKit Features**:
- ✅ Real-time voice-to-voice chat (<500ms latency)
- ✅ WebRTC streaming
- ✅ Conversational AI with interruption support
- ✅ Voice room management
- ✅ Audio quality optimization

### Configuration Validation

After creating `.env.local`, verify your configuration:

```bash
# Check environment variables are loaded
npm run dev

# In browser console (if NEXT_PUBLIC_DEBUG=true):
# Should see: "API Base URL: http://localhost:8000"
```

**Backend Health Check**:
```bash
# Verify backend is accessible
curl http://localhost:8000/health

# Verify voice is available (if configured)
curl http://localhost:8000/voice/health

# Verify LiveKit is configured (if using)
curl http://localhost:8000/voice/livekit/health
```

### Security Best Practices

#### ✅ Do's

1. **Use NEXT_PUBLIC_ prefix only for safe values**:
   - ✅ `NEXT_PUBLIC_API_BASE_URL` - Just a URL
   - ✅ `NEXT_PUBLIC_LIVEKIT_URL` - WebSocket URL only
   - ❌ `NEXT_PUBLIC_API_KEY` - Exposed but necessary (use API key rotation)

2. **Keep secrets server-side**:
   - ✅ `LIVEKIT_API_KEY` (no prefix) - Backend only
   - ✅ `LIVEKIT_API_SECRET` (no prefix) - Backend only
   - ✅ `ELEVENLABS_API_KEY` (no prefix) - Backend only

3. **Use environment-specific files**:
   - `.env.local` - Local development (gitignored)
   - `.env.production` - Production deployment
   - `.env.test` - Testing environment

4. **Rotate API keys regularly**:
   ```bash
   # Generate new key, update .env.local and backend
   # Test thoroughly before deploying
   ```

#### ❌ Don'ts

- ❌ Never commit `.env.local` to git
- ❌ Never use `NEXT_PUBLIC_` for secrets
- ❌ Never expose `LIVEKIT_API_SECRET` to frontend
- ❌ Never hardcode credentials in source code

### Configuration Examples

#### Example 1: Basic Setup (No Voice)

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev_key_12345
```

**Features**: Agent chat, config editor, graph visualization

#### Example 2: With REST Voice

```bash
# .env.local (frontend)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev_key_12345

# server/.env (backend)
ELEVENLABS_API_KEY=sk_elevenlabs_abc123
```

**Features**: All basic features + voice input/output (2-5s latency)

#### Example 3: Full Setup with LiveKit

```bash
# .env.local (frontend)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev_key_12345
NEXT_PUBLIC_LIVEKIT_URL=wss://voice-agent-xyz.livekit.cloud

# Backend also needs (in server/.env):
LIVEKIT_API_KEY=APIxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxx
LIVEKIT_URL=wss://voice-agent-xyz.livekit.cloud
```

**Features**: All features + real-time voice chat (<500ms latency)

### Troubleshooting Configuration

**Issue**: "API connection failed"
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify API URL in .env.local
cat .env.local | grep NEXT_PUBLIC_API_BASE_URL

# Check for CORS issues in browser console
```

**Issue**: "Voice features not available"
```bash
# Check backend voice health
curl http://localhost:8000/voice/health

# Verify ElevenLabs key is set in backend
# (Check server/.env has ELEVENLABS_API_KEY)
```

**Issue**: "LiveKit connection failed"
```bash
# Check LiveKit health
curl http://localhost:8000/voice/livekit/health

# Verify NEXT_PUBLIC_LIVEKIT_URL in .env.local
# Verify backend has LIVEKIT_API_KEY and LIVEKIT_API_SECRET
```

**Issue**: "Environment variables not loading"
```bash
# Restart Next.js dev server (required after .env changes)
# Stop server (Ctrl+C), then:
npm run dev

# Or clear cache first:
rm -rf .next
npm run dev
```

## 🎨 UI Overview

### Modern Glass Morphism Design

The interface features a sophisticated glass morphism design system:

- **Frosted glass effects** - Backdrop blur on all panels
- **Gradient overlays** - Subtle color transitions
- **Smooth animations** - 300ms transitions with easing
- **Elevated shadows** - Multi-layer shadows for depth
- **Responsive interactions** - Scale and hover effects

### Main Interface Components

```
┌─────────────────────────────────────────────────────────┐
│  Navigation Bar (Glass panel, sticky header)            │
├─────────────────┬───────────────────────────────────────┤
│                 │                                       │
│  Configuration  │  Chat Interface                       │
│  Panel (Left)   │  ┌────────────────────────────────┐  │
│  ┌────────────┐ │  │ Header (Mode, Clear)           │  │
│  │ Agent      │ │  ├────────────────────────────────┤  │
│  │ Selection  │ │  │                                │  │
│  ├────────────┤ │  │ Messages Area                  │  │
│  │ Execution  │ │  │ - Smart scrolling              │  │
│  │ Mode       │ │  │ - Markdown rendering           │  │
│  ├────────────┤ │  │ - Image support                │  │
│  │ Agent      │ │  │                                │  │
│  │ Details    │ │  ├────────────────────────────────┤  │
│  └────────────┘ │  │ Input Area (Always visible)    │  │
│                 │  │ [Textarea] [Send Button]       │  │
│                 │  └────────────────────────────────┘  │
└─────────────────┴───────────────────────────────────────┘
```

### Key UI Features

1. **Collapsible Configuration Panel**
   - Single unified glass panel on the left
   - Collapse entire panel or individual sections
   - Floating expand button when collapsed
   - Smooth slide/fade animations

2. **Enhanced Chat Interface**
   - Fixed viewport height (input always visible)
   - Smart auto-scrolling (only on agent responses)
   - Scroll-to-bottom button when scrolled up
   - Markdown and image rendering
   - Character counter in textarea

3. **Execution Modes**
   - **Mock** (🔵 Blue): Fast testing, no API costs
   - **Real** (🟢 Green): Production mode with actual API calls (DEFAULT)
   - **Stream** (🟣 Purple): Real-time token streaming for best UX

## 🧪 Testing

```bash
# Run all tests
npm test

# Watch mode for development
npm run test:watch

# Generate coverage report
npm run test:coverage
```

**Test Statistics:**
- Test Suites: 7 passed
- Total Tests: 146+ passed
- Coverage: >90% on core logic

## 🏭 Production Build

```bash
# Build optimized production bundle
npm run build

# Test production build locally
npm start
```

**Bundle Sizes:**
- Main route: ~95 kB First Load JS
- Config Editor: ~98 kB
- Help page: ~92 kB

All routes optimized under 100 kB for fast loading!

## 🔄 Upgrading Next.js & React

This section provides a comprehensive guide for upgrading from Next.js 14.2.33 to Next.js 16.x with React 19 support.

### Current vs Target Versions

| Package | Current | Target | Status |
|---------|---------|--------|--------|
| **Next.js** | 14.2.33 | 16.0.7 | Ready to upgrade |
| **React** | 18.3.1 | 19.2.1 | Ready to upgrade |
| **React DOM** | 18.3.1 | 19.2.1 | Ready to upgrade |
| **TypeScript** | 5.x | 5.x | Keep current |

### Upgrade Strategy

The upgrade follows a systematic approach to minimize risk:

1. **Preparation** - Fix syntax errors, create backups, document current state
2. **Core Upgrade** - Update Next.js, React, and React DOM
3. **TypeScript Types** - Update React type definitions
4. **Testing Libraries** - Update Jest and Testing Library
5. **Configuration** - Review and update config files
6. **Code Updates** - Fix breaking changes
7. **Testing** - Comprehensive validation
8. **Verification** - Manual testing of all features

### Quick Start: Automated Upgrade

For the fastest upgrade path, use the automated script:

```bash
cd frontend_web
chmod +x scripts/upgrade-nextjs.sh
./scripts/upgrade-nextjs.sh
```

This script will:
- ✅ Create backups of package files
- ✅ Update all dependencies
- ✅ Run compatibility checks
- ✅ Execute tests
- ✅ Verify the build

### Step-by-Step Manual Upgrade

If you prefer manual control, follow these steps:

#### Pre-Upgrade Checklist

Before starting, ensure you've completed:

- [x] Fixed syntax errors in codebase
- [ ] Run compatibility check: `node scripts/check-compatibility.js`
- [ ] Run pre-upgrade tests: `./scripts/test-upgrade.sh`
- [ ] Create git commit: `git commit -am "Pre-upgrade state"`
- [ ] Backup package files: `cp package.json package.json.backup`

#### Step 1: Update Core Dependencies

```bash
# Update Next.js, React, and React DOM
npm install next@latest react@latest react-dom@latest

# Update ESLint config
npm install --save-dev eslint-config-next@latest
```

#### Step 2: Update TypeScript Types

```bash
npm install --save-dev @types/react@latest @types/react-dom@latest @types/node@latest
```

#### Step 3: Update Testing Libraries

```bash
npm install --save-dev @testing-library/react@latest jest@latest jest-environment-jsdom@latest @types/jest@latest
```

#### Step 4: Update Other Dependencies (Optional)

```bash
npm install lucide-react@latest sonner@latest zustand@latest tailwind-merge@latest
```

#### Step 5: Review Configuration Files

**next.config.js**: Next.js 16 may require updates:
- Review Turbopack options (if using)
- Check output mode compatibility
- Verify environment variable handling

**jest.config.js**: Jest 30 may require updates:
- Check if `next/jest` still works correctly
- Review test configuration

**tsconfig.json**: Should work as-is, but verify:
- JSX settings
- Module resolution

#### Step 6: Fix Breaking Changes

**React 19 Changes**:
- New `use()` hook available
- Updated TypeScript types (may require component prop type updates)
- Server Components improvements

**Next.js 16 Changes**:
- Improved Turbopack support
- Enhanced caching mechanisms
- Better error handling

**Component Updates**:
- Review all `Image` components
- Check `Link` components
- Verify API routes

#### Step 7: Run Tests

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Unit tests
npm test

# Build test
npm run build
```

#### Step 8: Manual Testing

Test all features:
- [ ] Home page loads
- [ ] Agent selection works
- [ ] Chat interface works
- [ ] Mock mode works
- [ ] Real mode works
- [ ] Stream mode works
- [ ] SmartRouter panel works
- [ ] Config editor works
- [ ] Graph visualization works
- [ ] Navigation works
- [ ] Voice features work (if configured)

### Compatibility Matrix

#### Core Dependencies

| Package | Current | Latest | Next.js 16 Compatible | React 19 Compatible |
|---------|---------|--------|----------------------|-------------------|
| next | 14.2.33 | 16.0.7 | ✅ | ✅ |
| react | 18.3.1 | 19.2.1 | ✅ | ✅ |
| react-dom | 18.3.1 | 19.2.1 | ✅ | ✅ |
| @monaco-editor/react | 4.6.0 | Latest | ✅ | ✅ |
| reactflow | 11.11.3 | Latest | ✅ | ✅ |
| react-markdown | 10.1.0 | Latest | ✅ | ✅ |
| zustand | 4.5.2 | 5.0.9 | ✅ | ✅ |
| lucide-react | 0.379.0 | 0.556.0 | ✅ | ✅ |

#### Testing Libraries

| Package | Current | Latest | Compatible |
|---------|---------|--------|------------|
| @testing-library/react | 15.0.7 | 16.3.0 | ✅ |
| jest | 29.7.0 | 30.2.0 | ⚠️ (may need config update) |
| @types/jest | 29.5.12 | 30.0.0 | ✅ |

### Known Issues & Solutions

#### Issue 1: Jest 30 Compatibility
**Problem**: Jest 30 may require configuration updates  
**Solution**: Update `jest.config.js` if needed. The `next/jest` preset should still work, but review the configuration.

#### Issue 2: React 19 Type Changes
**Problem**: TypeScript types may have breaking changes  
**Solution**: Update `@types/react` and `@types/react-dom` to latest versions. Review component prop types if you encounter type errors.

#### Issue 3: Testing Library Updates
**Problem**: `@testing-library/react` 16 may have API changes  
**Solution**: Review test files and update as needed. Most tests should work without changes, but some APIs may have been updated.

#### Issue 4: Build Failing
**Solution**:
```bash
# Clear Next.js cache
rm -rf .next

# Clear node_modules
rm -rf node_modules

# Reinstall
npm install

# Rebuild
npm run build
```

#### Issue 5: Runtime Errors
**Solution**:
1. Check browser console for errors
2. Review [Next.js 16 migration guide](https://nextjs.org/docs/app/guides/upgrading)
3. Review [React 19 migration guide](https://react.dev/blog/2024/04/25/react-19)
4. Review component code for deprecated APIs

### Post-Upgrade Verification

After completing the upgrade, verify everything works:

```bash
# Check versions
npm list next react react-dom

# Should show:
# - next: 16.x.x
# - react: 19.x.x
# - react-dom: 19.x.x
```

**Post-Upgrade Checklist**:
- [ ] All tests pass
- [ ] Build succeeds
- [ ] Type checking passes
- [ ] Linting passes
- [ ] All pages load correctly
- [ ] All components render correctly
- [ ] API calls work
- [ ] Streaming works
- [ ] SmartRouter panel works
- [ ] Voice features work (if configured)
- [ ] No console errors
- [ ] No runtime errors

### Rollback Procedure

If the upgrade causes critical issues, you can rollback:

```bash
# 1. Restore package files
cp package.json.backup package.json
cp package-lock.json.backup package-lock.json

# 2. Reinstall dependencies
rm -rf node_modules .next
npm install

# 3. Verify restoration
npm run build
npm test
```

### Expected Changes

#### Next.js 14 → 16
- ✅ Improved performance and build times
- ✅ Better Turbopack support
- ✅ Enhanced caching mechanisms
- ✅ Better error handling and debugging

#### React 18 → 19
- ✅ New `use()` hook for promises and context
- ✅ Improved Server Components
- ✅ Better TypeScript types
- ✅ Performance improvements

#### Testing Libraries
- ⚠️ `@testing-library/react` 15 → 16: May have API changes
- ⚠️ Jest 29 → 30: May need config updates

### Support Resources

If you encounter issues during upgrade:

1. **[Next.js Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading)** - Official migration guide
2. **[React 19 Upgrade Guide](https://react.dev/blog/2024/04/25/react-19)** - React 19 changes
3. **[Next.js 16 Release Notes](https://nextjs.org/blog/next-16)** - What's new in Next.js 16
4. Review error messages carefully
5. Check dependency compatibility matrix above

### Success Criteria

The upgrade is successful when:
- ✅ All tests pass
- ✅ Build succeeds without errors
- ✅ Type checking passes
- ✅ Linting passes
- ✅ All features work in manual testing
- ✅ No console errors
- ✅ No runtime errors

---

## 📁 Project Structure

```
frontend_web/
├── app/                      # Next.js App Router
│   ├── layout.tsx            # Root layout with ServiceProvider
│   ├── page.tsx              # Agent Execution page (main)
│   ├── config-editor/        # YAML editor + graph page
│   ├── help/                 # Help & documentation page
│   ├── globals.css           # Custom styles (glass morphism)
│   └── providers.tsx         # Global React providers
│
├── components/               # React Components
│   ├── ui/                   # shadcn/ui base components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── select.tsx
│   │   ├── textarea.tsx
│   │   ├── slider.tsx        # NEW: Range slider
│   │   ├── switch.tsx        # NEW: Toggle switch
│   │   ├── radio-group.tsx   # NEW: Radio buttons
│   │   ├── label.tsx         # NEW: Form labels
│   │   └── tabs.tsx
│   ├── voice/                # NEW: Voice components
│   │   ├── VoiceToggle.tsx           # Recording button
│   │   ├── VoiceAnimation.tsx        # Audio visualization
│   │   ├── VoiceSettings.tsx         # Settings panel
│   │   └── VoiceInputPanel.tsx       # Chat integration
│   ├── navigation.tsx        # Top navigation bar
│   ├── agent-selector.tsx    # Agent dropdown selector
│   ├── agent-config-view.tsx # Agent configuration display
│   ├── execution-mode-toggle.tsx  # Mode selector (Mock/Real/Stream)
│   ├── unified-chat-interface.tsx # Main chat component (with voice)
│   ├── yaml-editor.tsx       # Monaco YAML editor
│   └── graph-visualizer.tsx  # ReactFlow graph
│
├── lib/                      # Core Logic
│   ├── services/             # Service Layer
│   │   ├── ServiceContext.tsx           # Dependency Injection
│   │   ├── AgentExecutionService.ts     # Execution logic
│   │   ├── SessionService.ts            # Session management
│   │   └── VoiceApiClient.ts            # NEW: Voice API client
│   ├── hooks/                # NEW: Custom React hooks
│   │   ├── useAudioRecorder.ts          # Recording hook
│   │   ├── useAudioPlayer.ts            # Playback hook
│   │   └── useVoice.ts                  # Unified voice hook
│   ├── contexts/             # NEW: React contexts
│   │   ├── VoiceContext.tsx             # Voice state management
│   │   └── SmartRouterContext.tsx       # SmartRouter panel state
│   ├── api-client.ts         # Singleton API client
│   ├── types.ts              # TypeScript interfaces
│   └── utils.ts              # Helper functions
│
├── __tests__/                # Test Files
│   ├── lib/
│   │   ├── services/         # Service tests (50 tests)
│   │   ├── api-client.test.ts
│   │   └── utils.test.ts
│   ├── components/           # Component tests (96 tests)
│   │   ├── unified-chat-interface.test.tsx
│   │   ├── execution-mode-toggle.test.tsx
│   │   └── agent-selector.test.tsx
│   └── voice/                # NEW: Voice tests (185 tests planned)
│       ├── hooks/            # Hook tests
│       ├── services/         # Voice API client tests
│       ├── contexts/         # Context tests
│       ├── components/       # Voice component tests
│       ├── integration/      # E2E voice tests
│       └── utils/            # Test utilities & mocks
│
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # System architecture (v3.0)
│   ├── TUTORIAL.md           # Complete user guide
│   ├── UI_FEATURES_UPDATE.md # Latest UI features
│   ├── FRONTEND_IMPLEMENTATION.md
│   ├── AGENT_DISCOVERY.md
│   ├── VOICE_IMPLEMENTATION_DESIGN.md     # NEW: Voice design
│   ├── VOICE_LIVEKIT_ANALYSIS.md          # NEW: LiveKit analysis
│   ├── VOICE_DUAL_MODE_ARCHITECTURE.md    # NEW: Dual-mode voice
│   └── VOICE_IMPLEMENTATION_SUMMARY.md    # NEW: Voice summary
│
└── package.json              # Dependencies & scripts
```

## 🎨 Architecture

### Design Patterns

The frontend follows clean architecture principles:

```
Presentation Layer (Components)
          ↓
Business Logic Layer (Services)
          ↓
Data Layer (API Client)
          ↓
Backend (FastAPI Server)
```

**Key Patterns:**
1. **Dependency Injection** - Services provided via React Context
2. **Strategy Pattern** - Execution modes (mock/real/stream)
3. **Singleton** - API Client for centralized requests
4. **Component Composition** - Reusable, testable components

### Service Layer

```typescript
// Dependency Injection Container
ServiceProvider
  ├── AgentExecutionService (business logic)
  ├── SessionService (session management)
  └── ApiClient (HTTP communication)

// Components consume services via hooks
const executionService = useExecutionService();
const sessionService = useSessionService();
```

### Execution Modes

| Mode | Backend Endpoint | Cost | Speed | Use Case |
|------|-----------------|------|-------|----------|
| Mock | `/simulate` | FREE | Instant | Testing UI |
| Real | `/chat` | PAID | 2-10s | Production |
| Stream | `/chat/stream` | PAID | Real-time | Best UX |

## 📚 Documentation

- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - Complete system design with mermaid diagrams
- **[TUTORIAL.md](./docs/TUTORIAL.md)** - Step-by-step setup and usage guide
- **[UI_FEATURES_UPDATE.md](./docs/UI_FEATURES_UPDATE.md)** - Latest UI enhancements with visuals
- **[FRONTEND_IMPLEMENTATION.md](./docs/FRONTEND_IMPLEMENTATION.md)** - Technical implementation details

## 🎯 Key Features Deep Dive

### 1. Markdown Rendering

Full GitHub Flavored Markdown support in chat messages:

```markdown
**Bold**, *italic*, ~~strikethrough~~

# Headings (h1-h6)

`inline code` and code blocks:

```python
def hello_agent():
    return "Hello!"
```

- Bullet lists
- [Links](https://example.com)
- ![Images](https://example.com/image.png)

| Tables | Support |
|--------|---------|
| Data   | Values  |
```

### 2. Smart Scrolling

Intelligent scroll behavior:
- Auto-scrolls ONLY when agent responds
- Pauses auto-scroll when user scrolls up manually
- Shows scroll-to-bottom button when not at bottom
- Smooth animations for all scroll actions

### 3. Glass Morphism CSS

Custom CSS utilities in `globals.css`:

```css
.glass-panel {
  backdrop-filter: blur(20px);
  background: linear-gradient(135deg,
    rgba(255,255,255,0.4) 0%,
    rgba(255,255,255,0.1) 100%);
}

.message-bubble {
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 4px;
}
```

## 🔒 Security

- ✅ API key authentication via secure headers
- ✅ Environment-based configuration (no hardcoded secrets)
- ✅ XSS prevention (React auto-escaping + sanitized markdown)
- ✅ Input validation on all user inputs
- ✅ CORS configuration for backend
- ✅ Secure markdown rendering (rehype-sanitize)

## ♿ Accessibility

WCAG 2.1 AA compliant:

- ✅ Keyboard navigation (Tab, Enter, Escape)
- ✅ ARIA labels and roles
- ✅ Screen reader support
- ✅ Color contrast ratio 4.5:1+
- ✅ Focus indicators
- ✅ Semantic HTML structure
- ✅ Alt text for images

## 🚀 Performance

### Optimizations

1. **Code Splitting** - Automatic route-based splitting by Next.js
2. **Lazy Loading** - Images with `loading="lazy"`
3. **Memoization** - Service singletons, React.memo for expensive components
4. **Optimized Re-renders** - Smart dependency arrays in useEffect
5. **Bundle Analysis** - Monitored bundle sizes under 100 kB

### Lighthouse Scores

Target scores (production):
- Performance: 95+
- Accessibility: 100
- Best Practices: 100
- SEO: 95+

## 🤝 Contributing

### Development Guidelines

1. **Follow Established Patterns**
   - Use dependency injection for services
   - Follow component composition patterns
   - Maintain separation of concerns

2. **Write Tests**
   - Unit tests for services
   - Component tests for UI
   - Target >80% coverage

3. **Type Safety**
   - Use TypeScript strictly (no `any`)
   - Define proper interfaces in `lib/types.ts`
   - Leverage type inference

4. **Documentation**
   - Update relevant docs when adding features
   - Add JSDoc comments for complex functions
   - Include mermaid diagrams for architecture changes

5. **Code Quality**
   - Run `npm run lint` before committing
   - Run `npm test` to ensure tests pass
   - Run `npm run type-check` for TypeScript errors

### Adding New Features

Example workflow:

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Implement feature with tests
# - Add types to lib/types.ts
# - Create service if needed in lib/services/
# - Create component in components/
# - Write tests in __tests__/

# 3. Run quality checks
npm run lint
npm test
npm run type-check

# 4. Update documentation
# - Update relevant docs/*.md files
# - Add mermaid diagrams if needed

# 5. Commit and push
git add .
git commit -m "feat: add my feature"
git push origin feature/my-feature
```

## 🐛 Troubleshooting

### Common Issues

1. **Module Not Found: 'tailwindcss-animate'**
   ```bash
   npm install tailwindcss-animate --legacy-peer-deps
   ```

2. **Markdown Not Rendering**
   ```bash
   npm install react-markdown remark-gfm rehype-raw rehype-sanitize --legacy-peer-deps
   ```

3. **API Connection Failed**
   - Verify backend is running: `curl http://localhost:8000/health`
   - Check `.env.local` has correct `NEXT_PUBLIC_API_BASE_URL`
   - Ensure CORS is enabled on backend

4. **Port Already in Use**
   ```bash
   # Use different port
   PORT=3001 npm run dev
   ```

5. **Cache Issues**
   ```bash
   # Clear Next.js cache
   rm -rf .next
   npm run dev
   ```

6. **Upgrade Issues**
   - See the [Upgrading Next.js & React](#-upgrading-nextjs--react) section above
   - Check compatibility matrix before upgrading
   - Always backup package files before upgrading
   - Review breaking changes documentation

See [TUTORIAL.md](./docs/TUTORIAL.md) for complete troubleshooting guide.

## 📦 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

Set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_API_BASE_URL`: Your production API URL
- `NEXT_PUBLIC_API_KEY`: Your production API key

### Docker

```bash
# Build image
docker build -t openagents-frontend .

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_BASE_URL=https://api.example.com \
  -e NEXT_PUBLIC_API_KEY=your_key \
  openagents-frontend
```

## 🎓 Learning Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui](https://ui.shadcn.com)

## 📊 Version History

- **v3.0** (Nov 2025) - Glass morphism UI, markdown rendering, smart scrolling
- **v2.0** (Oct 2025) - Service layer, dependency injection, execution modes
- **v1.0** (Sep 2025) - Initial release with basic features

## 📝 License

Copyright © 2025 OpenAgents Team

---

**Current Version**: 3.0 (Glass Morphism Edition)
**Last Updated**: November 30, 2025
**Status**: Production Ready ✅
