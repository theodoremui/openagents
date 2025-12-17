# OpenAgents - Complete Tutorial

**A step-by-step guide to running and testing the entire OpenAgents multi-agent orchestration system.**

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (5 Minutes)](#quick-start-5-minutes)
4. [Detailed Setup](#detailed-setup)
5. [API Keys Explained](#api-keys-explained)
   - [Two Different API Keys](#two-different-api-keys)
   - [Server API Key (Authentication)](#1-server-api-key-authentication)
   - [Google Maps API Key (Service Integration)](#2-google-maps-api-key-service-integration)
   - [OpenAI API Key (LLM Services)](#3-openai-api-key-llm-services)
   - [Yelp API Key (Yelp Fusion AI)](#4-yelp-api-key-yelp-fusion-ai)
   - [Quick Reference Table](#quick-reference-table)
   - [Getting Your Server API Key](#getting-your-server-api-key)
   - [Testing Your API Keys](#testing-your-api-keys)
6. [Running Tests](#running-tests)
7. [Using the Application](#using-the-application)
   - [Agent Simulation](#1-agent-simulation)
   - [Orchestrators (default / SmartRouter / MoE)](#2-orchestrators-default--smartrouter--moe)
   - [Real-time Voice Mode (LiveKit/WebRTC)](#3-real-time-voice-mode-livekitwebrtc)
   - [Maps (Interactive Maps via MapAgent)](#4-maps-interactive-maps-via-mapagent)
   - [MCP Integration (Model Context Protocol)](#5-mcp-integration-model-context-protocol)
   - [Configuration Editor](#6-configuration-editor)
   - [Graph Visualization](#7-graph-visualization)
   - [Help Page](#8-help-page)
8. [Architecture Deep Dive](#architecture-deep-dive)
9. [Scripts Organization](#scripts-organization)
10. [Troubleshooting](#troubleshooting)
11. [Production Deployment (Generic)](#production-deployment)
12. [Deploying to Heroku Enterprise](#deploying-to-heroku-enterprise)
    - [Heroku Architecture Overview](#heroku-architecture-overview)
    - [Prerequisites for Heroku](#prerequisites-for-heroku)
    - [Step 1: Create Heroku Apps](#step-1-create-heroku-apps)
    - [Step 2: Configure the Backend API](#step-2-configure-the-backend-api)
    - [Step 3: Configure the Realtime Worker](#step-3-configure-the-realtime-worker)
    - [Step 4: Configure the Frontend](#step-4-configure-the-frontend)
    - [Step 5: Environment Variables](#step-5-environment-variables)
    - [Step 6: Deploy](#step-6-deploy)
    - [Step 7: LiveKit Integration](#step-7-livekit-integration)
    - [Step 8: Database Setup](#step-8-database-setup)
    - [Step 9: Scaling & Performance](#step-9-scaling--performance)
    - [Step 10: CI/CD Pipeline](#step-10-cicd-pipeline)
    - [Heroku Troubleshooting](#heroku-troubleshooting)

## 🎯 System Overview

OpenAgents is a full-stack multi-agent orchestration system consisting of:

```mermaid
graph TB
    subgraph "Frontend (Next.js)"
        UI[Web UI<br/>:3000]
    end

    subgraph "Backend (FastAPI)"
        API[REST API<br/>:8000]
        Service[Agent Service]
    end

    subgraph "Core (Python)"
        Factory[Agent Factory]
        Agents[Agent Implementations]
        Config[YAML Config]
    end

    UI -->|HTTP + API Key| API
    API --> Service
    Service --> Factory
    Factory --> Agents
    Agents --> Config

    style UI fill:#4fc3f7
    style API fill:#66bb6a
    style Service fill:#81c784
    style Factory fill:#ffa726
    style Agents fill:#ffb74d
    style Config fill:#ffcc80
```

### Components

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| **Frontend** | Next.js 14 + TypeScript | 3000 | User interface |
| **Backend** | FastAPI + Python 3.11+ | 8000 | REST API |
| **Agents** | Python | - | Agent implementations |
| **Config** | YAML | - | Agent configuration |

## ✅ Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher
- **uv**: Package manager (or pip)
- **Git**: For version control

### Check Versions

```bash
python3 --version    # Should be 3.11+
node --version       # Should be v18+
npm --version        # Should be v9+
```

### Install uv (Recommended)

```bash
pip install uv
```

## 🚀 Quick Start (5 Minutes)

### 1. Clone or Navigate to Project

```bash
cd /path/to/openagents
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env - set AUTH_ENABLED=false for development
nano .env
```

### 3. Start Backend

```bash
# Method 1: Using convenience script (recommended)
./scripts/run_server.sh --install    # Install dependencies
./scripts/run_server.sh --dev        # Run in development mode

# Method 2: Manual
cd server
uv pip install .
cd ..
python -m server.main
```

**Note**: The `run_server.sh` script is located in the `scripts/` folder for better organization. See [Scripts Organization](#scripts-organization) for details.

**Expected output:**
```
🚀 Starting Multi-Agent Orchestration API...
✓ Loaded 6 agents
✓ Agents available: geo, finance, map, one, yelp, yelp_mcp
✓ MCP-enabled agent: YelpMCPAgent (stdio transport)
✓ 1 MCP-enabled agent(s) configured
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Start Frontend (New Terminal)

```bash
cd frontend_web
npm install
cp .env.local.example .env.local

# Edit .env.local - set API_BASE_URL and API_KEY
npm run dev
```

**Expected output:**
```
▲ Next.js 14.2.3
- Local:        http://localhost:3000
✓ Ready in 2.5s
```

### 5. Open Application

Open browser: http://localhost:3000

You should see the OpenAgents interface! 🎉

## 📖 Detailed Setup

### Backend Setup

#### Step 1: Install Dependencies

```bash
cd server

# Using uv (recommended)
uv pip install .

# Or using pip
pip install -e .

# Install dev dependencies
uv pip install ".[dev]"
```

#### Step 2: Configure Environment

```bash
# From project root
cp .env.example .env
```

Edit `.env`:

```env
# Authentication (set to false for development)
AUTH_ENABLED=false

# API Keys (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
API_KEYS=dev_key_12345

# Agent configuration path
AGENT_CONFIG_PATH=config/open_agents.yaml

# Server settings
HOST=0.0.0.0
PORT=8000

# External API Keys (Backend Only - Never expose to frontend)
OPENAI_API_KEY=your_openai_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_key_here
GOOGLE_API_KEY=your_google_maps_key_here
YELP_API_KEY=your_yelp_key_here
```

**Important**: These API keys are used by the backend server to call external APIs. They should **NEVER** be exposed to the frontend. See [Environment Variables Security](#environment-variables-security) for details.

#### Step 3: Verify Configuration

```bash
# Check if config file exists
ls config/open_agents.yaml

# Validate configuration
python -c "from asdrp.agents.config_loader import AgentConfigLoader; loader = AgentConfigLoader(); print(f'Loaded {len(loader.list_agents())} agents')"
```

#### Step 4: Run Backend

```bash
# From project root
python -m server.main
```

Or use the convenience script:

```bash
./scripts/run_server.sh --dev
```

#### Step 5: Test Backend

```bash
# Health check
curl http://localhost:8000/health

# List agents (auth disabled)
curl http://localhost:8000/agents

# Expected response:
# [{"id":"geo","name":"geo","display_name":"GeoAgent", ...}, ...]
```

### Frontend Setup

#### Step 1: Install Dependencies

```bash
cd frontend_web
npm install
```

This installs:
- Next.js, React, TypeScript
- Tailwind CSS, shadcn/ui
- ReactFlow, Monaco Editor
- Testing libraries

#### Step 2: Configure Environment

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:

```env
# Backend API Connection
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev_key_12345  # Must match API_KEYS in root .env

# Client-Side API Keys (Only for browser-rendered features)
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_key_here  # For interactive maps
```

**Important**: 
- `NEXT_PUBLIC_API_KEY` must match `API_KEYS` from root `.env`
- Only include `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` if using interactive maps
- **DO NOT** add backend API keys (`PERPLEXITY_API_KEY`, `OPENAI_API_KEY`, etc.) to frontend `.env.local`
- See [Environment Variables Security](#environment-variables-security) for details

#### Step 3: Run Frontend

```bash
npm run dev
```

#### Step 4: Verify Frontend

Open browser: http://localhost:3000

You should see:
- Navigation bar with 3 links
- Agent Simulation page
- No console errors

## 🔑 API Keys Explained

### Two Different API Keys

The OpenAgents system uses **two different types of API keys** for different purposes. Understanding the difference is critical to avoid authentication errors.

### 1. Server API Key (Authentication)

**Purpose**: Authenticate requests to the OpenAgents backend server
**Header**: `X-API-Key`
**Configuration**: Set in `.env` file as `API_KEYS` or `DEFAULT_API_KEY`

**Example Usage**:
```bash
curl -H "X-API-Key: cZFcwouw09I9f1yNrnsAW2N0FXckNLnv6ccOnXndS18" \
  http://localhost:8000/agents
```

**Where to Find It**:
- Check `.env` file: `grep API_KEYS .env`
- Check server startup logs (if no API_KEYS set, a default key is generated)
- Or generate a new one: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### 2. Google Maps API Key (Service Integration)

**Purpose**: Access Google Maps services (Directions, Geocoding, Static Maps, Interactive Maps)
**Configuration**: Set in `.env` file as `GOOGLE_MAPS_API_KEY`

**Example Configuration**:
```bash
# Backend .env file
GOOGLE_MAPS_API_KEY=AIzaSyAB5fhvThUGG-eaiI4LOYvVAxuOno2MsVg

# Frontend .env.local file (for interactive maps)
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIzaSyAB5fhvThUGG-eaiI4LOYvVAxuOno2MsVg
```

**Where to Find It**:
- Google Cloud Console → APIs & Services → Credentials
- Check `.env` file: `grep GOOGLE_MAPS_API_KEY .env`

### 3. OpenAI API Key (LLM Services)

**Purpose**: Access OpenAI's language models for agent intelligence
**Configuration**: Set in `.env` file as `OPENAI_API_KEY`

**Example Configuration**:
```bash
OPENAI_API_KEY=sk-proj-...
```

**Where to Find It**:
- OpenAI Platform → API Keys → https://platform.openai.com/api-keys

### 4. Perplexity API Key (PerplexityAgent)

**Purpose**: Access Perplexity AI search and chat services via PerplexityAgent
**Configuration**: Set in `.env` file as `PERPLEXITY_API_KEY`

**Example Configuration**:
```bash
PERPLEXITY_API_KEY=your_perplexity_key_here
```

**Where to Find It**:
- Perplexity AI Platform → API Keys → https://www.perplexity.ai/settings/api
- Required for PerplexityAgent to function

**Note**: Only required if you want to use PerplexityAgent. Other agents work without it.

### 5. Yelp API Key (Yelp Fusion AI)

**Purpose**: Access Yelp Fusion AI for business search via YelpMCPAgent
**Configuration**: Set in `.env` file as `YELP_API_KEY`

**Example Configuration**:
```bash
YELP_API_KEY=your_yelp_api_key_here
```

**Where to Find It**:
- Yelp Developers → Create App → https://www.yelp.com/developers/v3/manage_app
- Free trial available; contact fusion@yelp.com to extend

**Note**: Only required if you want to use YelpMCPAgent. Other agents work without it.

### Common Mistake

❌ **Wrong**: Using Google Maps API key as server API key
```bash
curl -H "X-API-Key: AIzaSyAB5fhvThUGG-eaiI4LOYvVAxuOno2MsVg" \
  http://localhost:8000/agents
# Error: {"detail":"Invalid API key"}
```

✅ **Correct**: Using server API key for authentication
```bash
curl -H "X-API-Key: cZFcwouw09I9f1yNrnsAW2N0FXckNLnv6ccOnXndS18" \
  http://localhost:8000/agents
# Success: Returns agent list
```

### Quick Reference Table

| Key Type | Purpose | Header/Env Var | Example Value |
|----------|---------|----------------|---------------|
| **Server API Key** | Backend authentication | `X-API-Key` header | `cZFcwouw09I9f1yNrnsAW2N0FXckNLnv6ccOnXndS18` |
| **Google Maps API Key** | Google Maps services | `GOOGLE_MAPS_API_KEY` env var | `AIzaSyAB5fhvThUGG-eaiI4LOYvVAxuOno2MsVg` |
| **OpenAI API Key** | LLM services | `OPENAI_API_KEY` env var | `sk-proj-...` |
| **Perplexity API Key** | Perplexity AI services | `PERPLEXITY_API_KEY` env var | `pplx-...` |
| **Yelp API Key** | Yelp Fusion AI (YelpMCPAgent) | `YELP_API_KEY` env var | `your_yelp_api_key` |

## 🔐 Environment Variables Security

### Two Separate `.env` Files

This project uses **two separate** `.env` files for security and separation of concerns:

1. **Root `.env`** - Backend/server configuration (Python)
2. **`frontend_web/.env.local`** - Frontend configuration (Next.js)

### Root `.env` File (Backend)

**Location**: `/path/to/openagents/.env`

**Purpose**: Contains all backend API keys and server configuration.

**Key Variables**:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
AUTH_ENABLED=true
API_KEYS=your_backend_api_key_here

# External API Keys (Backend Only - Never expose to frontend)
OPENAI_API_KEY=your_openai_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_key_here
GOOGLE_API_KEY=your_google_maps_key_here
YELP_API_KEY=your_yelp_key_here
```

**Important**: These API keys are used by the backend server to call external APIs. They should **NEVER** be exposed to the frontend.

### Frontend `.env.local` File

**Location**: `/path/to/openagents/frontend_web/.env.local`

**Purpose**: Contains only frontend-specific configuration.

**Key Variables**:

```bash
# Backend API Connection
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your_backend_api_key_here  # Must match API_KEYS in root .env

# Client-Side API Keys (Only for browser-rendered features)
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_key_here  # For interactive maps
```

### Security Rules

#### ✅ DO Include in Frontend `.env.local`:
- `NEXT_PUBLIC_API_BASE_URL` - Backend server URL
- `NEXT_PUBLIC_API_KEY` - Backend authentication key (matches `API_KEYS` in root `.env`)
- `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` - Only because maps render in browser

#### ❌ DO NOT Include in Frontend `.env.local`:
- `PERPLEXITY_API_KEY` - Backend only
- `OPENAI_API_KEY` - Backend only
- `YELP_API_KEY` - Backend only
- `GOOGLE_API_KEY` - Backend only (use `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` for maps)

### Why This Architecture?

1. **Security**: Backend API keys stay on the server and are never exposed to the browser
2. **Separation of Concerns**: Frontend only needs to know how to connect to the backend
3. **Client-Side Exception**: Google Maps needs a client-side key because maps render in the browser

### Setup Steps

1. **Copy root `.env.example` to `.env`**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

2. **Copy frontend `.env.local.example` to `.env.local`**:
   ```bash
   cd frontend_web
   cp .env.local.example .env.local
   # Edit .env.local and set NEXT_PUBLIC_API_KEY to match API_KEYS from root .env
   ```

3. **Verify Setup**:
   ```bash
   # Check backend can access API keys
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('PERPLEXITY_API_KEY:', 'SET' if os.getenv('PERPLEXITY_API_KEY') else 'NOT SET')"
   
   # Check frontend can access backend
   cd frontend_web
   npm run dev
   # Should connect to backend at NEXT_PUBLIC_API_BASE_URL
   ```

### Getting Your Server API Key

#### Option 1: Check .env file
```bash
grep API_KEYS .env
# or
grep DEFAULT_API_KEY .env
```

#### Option 2: Check server startup logs
When the server starts, if no API_KEYS is configured, it prints:
```
⚠️  No API_KEYS configured. Using development key: dev_key_XXXXX
```

#### Option 3: Generate a new one
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Option 4: Disable authentication (development only)
```bash
export AUTH_ENABLED=false
python -m server.main
```

### Testing Your API Keys

**Test Server API Key**:
```bash
# Test with correct server API key
curl -H "X-API-Key: YOUR_SERVER_API_KEY" \
  http://localhost:8000/agents

# Should return: List of agents (JSON)
```

**Test Google Maps API Key** (indirect - via MapAgent):
```bash
# Use the frontend to ask MapAgent:
"Show me a map from San Francisco to San Carlos"

# If Google Maps API key is wrong, you'll see an error in backend logs
```

### API Key Troubleshooting

#### Error: "Invalid API key"
- ✅ Check you're using the **server API key**, not Google Maps API key
- ✅ Verify the key matches what's in `.env` file
- ✅ Make sure server has been restarted after changing `.env`
- ✅ Check server logs for the actual key being used

#### Error: "Missing API key"
- ✅ Include `X-API-Key` header in your request
- ✅ Check header name is exactly `X-API-Key` (case-sensitive)

#### Error: "Google Maps API error"
- ✅ Verify `GOOGLE_MAPS_API_KEY` is set in backend `.env`
- ✅ Check Google Cloud Console that API is enabled
- ✅ Verify billing is enabled on Google Cloud account
- ✅ For interactive maps, also set `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in frontend `.env.local`

#### Error: "PERPLEXITY_API_KEY environment variable is not set"
- ✅ Add `PERPLEXITY_API_KEY=your_key` to root `.env` file
- ❌ Do NOT add it to `frontend_web/.env.local` (backend only)

#### Error: "Invalid API key" when calling backend
- ✅ Check `NEXT_PUBLIC_API_KEY` in `frontend_web/.env.local` matches `API_KEYS` in root `.env`
- ✅ Restart both backend and frontend after changing `.env` files

#### Want to disable auth for development?
```bash
# In .env file
AUTH_ENABLED=false

# Then restart server
python -m server.main
```

### Best Practices

1. **Never commit API keys to git**:
   ```bash
   # Ensure .env and .env.local are in .gitignore
   echo ".env" >> .gitignore
   echo "frontend_web/.env.local" >> .gitignore
   ```

2. **Use different keys for dev/staging/prod**:
   ```bash
   # dev.env
   API_KEYS=dev_key_12345

   # prod.env
   API_KEYS=prod_key_secure_random_string
   ```

3. **Rotate keys regularly** (especially for production)

4. **Use environment-specific Google Maps API keys** with domain restrictions

## 🧪 Running Tests

### Backend Tests

```bash
cd /path/to/openagents

# Run all backend tests
pytest tests/server/ -v

# Run with coverage
pytest tests/server/ --cov=server --cov-report=html

# Open coverage report
open htmlcov/index.html
```

**Expected output:**
```
tests/server/test_auth.py ................... [40%]
tests/server/test_models.py ................ [70%]
tests/server/test_agent_service.py ......... [100%]

30 passed in 3.2s
Coverage: 95%
```

### Frontend Tests

```bash
cd frontend_web

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode (for development)
npm run test:watch
```

**Expected output:**
```
PASS  __tests__/lib/api-client.test.ts
PASS  __tests__/lib/utils.test.ts

Test Suites: 2 passed, 2 total
Tests:       15 passed, 15 total
Coverage:    92.5%
```

### Integration Tests

```bash
# Start the backend + frontend first (text chat)

# Terminal 1: Backend
./scripts/run_server.sh --dev

# Terminal 2: Frontend
cd frontend_web && npm run dev

# Optional (real-time voice):
# Terminal 3: LiveKit worker
# ./scripts/run_realtime.sh --dev
#
# Note: real-time voice uses LiveKit/WebRTC. The backend creates sessions/tokens,
# and the worker joins LiveKit rooms as the AI participant.

# Terminal 3: Run E2E tests (if available)
cd frontend_web && npm run test:e2e
```

## 💡 Using the Application

### 1. Agent Simulation

**Purpose**: Interact with agents in real-time

**Steps**:

1. Navigate to http://localhost:3000
2. Select an agent from dropdown (e.g., "GeoAgent")
3. View agent configuration in left panel
4. Type a message in the console (e.g., "Where is San Francisco?")
5. Click Send or press Enter
6. View agent response and execution trace

**Example Interaction**:

```
User: What is the weather in San Carlos, CA tomorrow?
Agent (MoE): (Uses web search specialists like One/Perplexity when configured)
Trace (example): [one] + [perplexity] → synthesis
```

### 2. Orchestrators (default / SmartRouter / MoE)

OpenAgents supports multiple orchestration modes:

- **default**: direct agent execution (no multi-agent orchestration)
- **smartrouter**: LLM-based query interpretation + decomposition + routing + synthesis
- **moe (Mixture of Experts)**: selects specialist agents (experts) and executes them in parallel, then mixes results

Where this is configured:

- **Backend run mode**: `./scripts/run_server.sh --dev <orchestrator>` (e.g. `moe`, `smartrouter`)
- **MoE behavior**: `config/moe.yaml`
- **SmartRouter behavior**: `config/smartrouter.yaml`

MoE docs (canonical):

- `docs/moe/moe_orchestrator.md`

### 3. Real-time Voice Mode (LiveKit/WebRTC)

Real-time voice mode is powered by **LiveKit**:

- The **frontend** connects to LiveKit over **WebRTC** (audio transport).
- The **backend** creates rooms + tokens and dispatches a job to the worker.
- The **worker** (`./scripts/run_realtime.sh`) joins the LiveKit room and runs STT → LLM → TTS.

Why you need two processes:

- The backend is an HTTP API server.
- The worker is a LiveKit Agents runtime that receives job dispatches and publishes/consumes audio tracks.

Canonical docs:

- `docs/voice/realtime_implementation.md`

### 4. Maps (Interactive Maps via MapAgent)

MapAgent can generate **interactive map payloads** that the frontend renders directly (routes, pins, places).

Common examples:

- “Show me a map from San Francisco to San Carlos”
- “Find coffee shops near Stanford and show them on a map”

Canonical docs:

- `docs/tricks/interactive_maps.md`
- `docs/IMPLEMENTATION_GUIDE.md#geocoding-based-map-injection-fail-safe-places-maps`

### 5. MCP Integration (Model Context Protocol)

**Status**: ✅ Complete (New in v1.0)
**Last Updated**: November 30, 2025

OpenAgents now supports **MCP (Model Context Protocol)** integration, enabling agents to connect to external MCP servers for enhanced capabilities. This allows agents to access tools and resources beyond their built-in functionality.

#### What is MCP?

MCP is a standardized protocol for connecting AI models to external data sources and tools - like "USB-C for AI applications". It enables:

- **Standardized Integration**: One protocol for all external tools
- **Modularity**: Swap MCP servers without changing agent code
- **Extensibility**: Easy to add new capabilities
- **Community**: Growing ecosystem of MCP servers

#### YelpMCPAgent - The Reference Implementation

OpenAgents includes **YelpMCPAgent** as a complete example of MCP integration, connecting to the Yelp Fusion AI MCP server.

**Key Features**:
- 🔍 **Next-Generation Search**: Natural language business search
- 💬 **Multi-Turn Conversations**: Follow-up questions with chat_id
- 🎯 **Direct Business Queries**: Ask about specific businesses
- 🗺️ **Planning**: Itinerary and progressive route planning
- 🍽️ **Reservations**: Conversational table booking (on request)

**Architecture**:
```
YelpMCPAgent (OpenAI Agent)
    ↓ stdio transport
MCPServerStdio (subprocess manager)
    ↓ pipes
yelp-mcp Server (FastMCP)
    ↓ HTTPS API
Yelp Fusion AI API
```

#### Setting Up YelpMCPAgent

##### Prerequisites

1. **Yelp API Key**: [Get a key here](https://www.yelp.com/developers/v3/manage_app)
2. **uv Package Manager**: For yelp-mcp dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

##### Step 1: Install yelp-mcp Dependencies

```bash
# From project root
cd yelp-mcp
uv sync
cd ..
```

##### Step 2: Configure Environment

Add to your `.env` file:

```bash
# Yelp Fusion AI API Key
YELP_API_KEY=your_yelp_api_key_here
```

Or export directly:

```bash
export YELP_API_KEY="your_yelp_api_key_here"
```

##### Step 3: Verify Configuration

The YelpMCPAgent configuration is already in `config/open_agents.yaml`:

```yaml
agents:
  yelp_mcp:
    display_name: YelpMCPAgent
    module: asdrp.agents.mcp.yelp_mcp_agent
    function: create_yelp_mcp_agent
    model:
      name: gpt-4.1-mini
      temperature: 0.7
    session_memory:
      type: sqlite
      enabled: true
    mcp_server:
      enabled: true
      command: [uv, run, mcp-yelp-agent]
      working_directory: yelp-mcp
      # Note: env field is deprecated - set environment variables in .env file
      transport: stdio
    enabled: true
```

##### Step 4: Start Server

```bash
# Using convenience script (recommended)
./scripts/run_server.sh --dev

# Or manually
python -m server.main
```

You should see:
```
✓ MCP-enabled agent: YelpMCPAgent (stdio transport)
✓ 1 MCP-enabled agent(s) configured
```

##### Step 5: Test YelpMCPAgent

**Via Frontend** (http://localhost:3000):

1. Select "YelpMCPAgent" from dropdown
2. Try these queries:
   - "Find the best tacos in San Francisco"
   - "Which ones have outdoor seating?" (follow-up)
   - "Does Ricky's Taco allow pets?"
   - "Plan a progressive dinner in the Mission District"

**Via API**:

```bash
curl -X POST http://localhost:8000/agents/yelp_mcp/chat \
  -H "Content-Type: application/json" \
  -d '{"input": "Find the best tacos in San Francisco"}'
```

##### Step 6: Interactive Testing

Test the agent directly:

```bash
# From project root
python -m asdrp.agents.mcp.yelp_mcp_agent

# You'll see:
# 🍕 YelpMCPAgent - Powered by Yelp Fusion AI via MCP
# Enter your Yelp query (or press Enter to exit):
# Ask Yelp:
```

#### How MCP Integration Works

**1. Configuration** (`config/open_agents.yaml`):
```yaml
mcp_server:
  enabled: true
  command: [uv, run, mcp-yelp-agent]  # Starts MCP server
  working_directory: yelp-mcp          # Where to run command
  # Note: env field is deprecated - set environment variables in .env file
  # Environment variables are automatically loaded from .env using python-dotenv
  transport: stdio                     # Communication method
```

**2. Agent Creation** (automatic):
- AgentFactory reads configuration
- Detects `mcp_server` section
- Passes MCPServerConfig to agent creation function
- Agent creates MCPServerStdio with server command

**3. Runtime**:
- MCPServerStdio starts subprocess running yelp-mcp server
- Agent uses MCP server tools (like `yelp_agent`)
- Server communicates via stdio (stdin/stdout pipes)
- Responses returned to agent for processing

**4. Shutdown** (automatic):
- FastAPI lifespan shutdown hook triggered
- MCPServerManager.shutdown_all() called
- Graceful termination (SIGTERM → wait → SIGKILL)
- All resources cleaned up

#### Creating Your Own MCP Agent

See `docs/MCP_INTEGRATION_GUIDE.md` for a complete guide on creating custom MCP-enabled agents. Quick template:

```python
# asdrp/agents/mcp/my_mcp_agent.py
from agents import Agent
from agents.mcp import MCPServerStdio
from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
from asdrp.agents.protocol import AgentProtocol

def create_my_mcp_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None,
    mcp_server_config: MCPServerConfig | None = None
) -> AgentProtocol:
    # Validate config
    # Create MCPServerStdio
    # Build Agent with MCP server as tool
    return agent
```

Then add to `config/open_agents.yaml`:

```yaml
agents:
  my_mcp:
    display_name: MyMCPAgent
    module: asdrp.agents.mcp.my_mcp_agent
    function: create_my_mcp_agent
    mcp_server:
      enabled: true
      command: [your, mcp, command]
      working_directory: your-mcp-dir
      transport: stdio
```

#### MCP Resources

- **OpenAgents MCP Guide**: `docs/MCP_INTEGRATION_GUIDE.md`
- **Quick Reference**: `docs/MCP_QUICK_REFERENCE.md`
- **Implementation Summary**: `docs/MCP_IMPLEMENTATION_SUMMARY.md`
- **OpenAI Agents MCP Docs**: https://openai.github.io/openai-agents-python/mcp/
- **MCP Protocol Docs**: https://modelcontextprotocol.io/
- **Yelp Fusion AI**: https://docs.developer.yelp.com/reference/v2_ai_chat

#### MCP Benefits

✅ **For Developers**:
- Configuration-driven (no code changes)
- Type-safe with Pydantic validation
- Comprehensive testing and mocking
- Complete documentation

✅ **For Users**:
- Access to powerful external tools
- Reliable error handling
- High-performance stdio transport
- Multiple specialized agents

✅ **For the Project**:
- Easy to add new MCP agents
- Clean, maintainable architecture
- Compatible with existing system
- Ready for future MCP transports (HTTP, SSE)

### 6. Configuration Editor

**Purpose**: Edit agent configuration and visualize relationships

**Steps**:

1. Navigate to http://localhost:3000/config-editor
2. Click "YAML Editor" tab
3. Edit the configuration (syntax highlighting provided)
4. Click "Save" to apply changes
5. Switch to "Graph View" tab
6. See visual representation of agents and connections

**Example Edit**:

```yaml
agents:
  custom_agent:
    display_name: "CustomAgent"
    module: "asdrp.agents.single.custom_agent"
    function: "create_custom_agent"
    model:
      name: "gpt-4"
      temperature: 0.7
```

### 7. Graph Visualization

**Features**:
- **Zoom**: Scroll wheel
- **Pan**: Click and drag background
- **Select Node**: Click on a node
- **View Details**: Selected node details shown below

### 8. Help Page

Navigate to http://localhost:3000/help for in-app documentation.

## 🏗️ Architecture Deep Dive

### System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[Web Browser]
    end

    subgraph "Presentation Layer"
        Pages[Next.js Pages]
        Components[React Components]
    end

    subgraph "API Layer"
        APIClient[API Client<br/>Singleton]
    end

    subgraph "Server Layer"
        FastAPI[FastAPI Server]
        Auth[Authentication]
        Routes[API Routes]
    end

    subgraph "Business Logic"
        Service[Agent Service]
        Factory[Agent Factory]
    end

    subgraph "Data Layer"
        Config[YAML Config]
        Agents[Agent Implementations]
    end

    Browser --> Pages
    Pages --> Components
    Components --> APIClient
    APIClient -->|HTTP + API Key| FastAPI
    FastAPI --> Auth
    Auth --> Routes
    Routes --> Service
    Service --> Factory
    Factory --> Config
    Factory --> Agents
```

### Request Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant NextJS
    participant APIClient
    participant FastAPI
    participant AgentService
    participant AgentFactory
    participant Agent

    User->>Browser: Click "Send Message"
    Browser->>NextJS: Form Submit
    NextJS->>APIClient: simulateAgent(id, input)
    APIClient->>FastAPI: POST /agents/{id}/simulate
    FastAPI->>FastAPI: Verify API Key
    FastAPI->>AgentService: simulate(id, request)
    AgentService->>AgentFactory: get_agent_with_session(id)
    AgentFactory->>Agent: Create & Initialize
    Agent-->>AgentFactory: Agent Instance
    AgentFactory-->>AgentService: (agent, session)
    AgentService->>Agent: Execute with input
    Agent-->>AgentService: Response + Trace
    AgentService-->>FastAPI: SimulationResponse
    FastAPI-->>APIClient: JSON Response
    APIClient-->>NextJS: Typed Data
    NextJS-->>Browser: Update UI
    Browser-->>User: Display Result
```

### Data Models

#### Frontend Types (TypeScript)

```typescript
// lib/types.ts
interface AgentListItem {
  id: string;
  name: string;
  display_name: string;
  enabled: boolean;
}

interface SimulationRequest {
  input: string;
  max_steps?: number;
}

interface SimulationResponse {
  response: string;
  trace: SimulationStep[];
  metadata: Record<string, unknown>;
}
```

#### Backend Models (Python)

```python
# server/models.py
class AgentListItem(BaseModel):
    id: str
    name: str
    display_name: str
    enabled: bool

class SimulationRequest(BaseModel):
    input: str
    max_steps: int = 10

class SimulationResponse(BaseModel):
    response: str
    trace: List[SimulationStep]
    metadata: Dict[str, Any]
```

## 📁 Scripts Organization

**Date**: November 30, 2025
**Status**: ✅ Complete

### Overview

All utility scripts are organized in the `scripts/` folder for better project maintainability:

```
scripts/
├── README.md                 # Documentation for all scripts
├── check_map_tools.sh       # MapAgent tool verification
└── run_server.sh            # Backend server management (moved from root)
```

### Why Scripts Folder?

**Benefits**:
- ✅ Better project organization
- ✅ Easier to find utility scripts
- ✅ Consistent with industry best practices
- ✅ Clear separation: scripts vs source code vs docs
- ✅ Scalable: easy to add new scripts

### Script Details

| Script | Purpose | Key Features |
|--------|---------|--------------|
| `run_server.sh` | Backend server management | Auto venv setup, dev/prod modes, testing |
| `check_map_tools.sh` | Diagnostic for MapAgent tools | API verification, tool discovery check |

### Usage Examples

```bash
# Install dependencies
./scripts/run_server.sh --install

# Run in development mode
./scripts/run_server.sh --dev

# Run in production mode
./scripts/run_server.sh

# Run tests
./scripts/run_server.sh --test

# Show help
./scripts/run_server.sh --help

# Check MapAgent tools
./scripts/check_map_tools.sh
```

### Path Portability

The `run_server.sh` script calculates paths dynamically to work from any directory:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
```

**Benefits**:
- ✅ Works from any working directory
- ✅ No hardcoded paths
- ✅ Resilient to project moves

### Migration History

**Previous Location**: `./run_server.sh` (project root)
**Current Location**: `./scripts/run_server.sh`
**Migration Date**: November 30, 2025

All documentation references have been updated to reflect the new location.

### Future Scripts

As the project grows, consider adding:

1. **`scripts/setup_all.sh`** - Setup both frontend and backend in one command
2. **`scripts/run_tests_all.sh`** - Run backend + frontend tests with combined coverage
3. **`scripts/deploy.sh`** - Deployment automation with environment validation
4. **`scripts/check_deps.sh`** - Verify dependencies and check for security vulnerabilities

### Troubleshooting Scripts

**Issue: "Permission denied"**
```bash
chmod +x scripts/run_server.sh
```

**Issue: "No such file or directory"**
```bash
# Ensure you're in project root
pwd  # Should show: /path/to/openagents
cd /path/to/openagents
./scripts/run_server.sh --dev
```

**Issue: "PROJECT_ROOT not found"**
```bash
# Debug path calculation
bash -x scripts/run_server.sh --help
```

## 🐛 Troubleshooting

### Environment Variable Issues

#### Issue: Backend Can't Access API Keys

**Symptoms**:
- Errors like "PERPLEXITY_API_KEY environment variable is not set"
- Agents fail to initialize
- External API calls fail

**Solutions**:
```bash
# 1. Verify .env file exists in project root
ls -la .env

# 2. Check API key is set
grep PERPLEXITY_API_KEY .env

# 3. Verify python-dotenv is loading the file
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('PERPLEXITY_API_KEY:', 'SET' if os.getenv('PERPLEXITY_API_KEY') else 'NOT SET')"

# 4. Restart backend after changing .env
./scripts/run_server.sh --dev
```

#### Issue: Frontend Can't Connect to Backend

**Symptoms**:
- "Failed to fetch" errors in browser console
- 401 Unauthorized errors
- Connection refused errors

**Solutions**:
```bash
# 1. Verify backend is running
curl http://localhost:8000/health

# 2. Check frontend .env.local exists
ls -la frontend_web/.env.local

# 3. Verify NEXT_PUBLIC_API_KEY matches backend API_KEYS
grep API_KEYS .env
grep NEXT_PUBLIC_API_KEY frontend_web/.env.local

# 4. Check NEXT_PUBLIC_API_BASE_URL is correct
grep NEXT_PUBLIC_API_BASE_URL frontend_web/.env.local
# Should be: http://localhost:8000

# 5. Restart frontend after changing .env.local
cd frontend_web && npm run dev
```

#### Issue: Wrong API Key in Frontend

**Symptoms**:
- "Invalid API key" errors
- 401 Unauthorized responses

**Solutions**:
```bash
# 1. Get backend API key from root .env
grep API_KEYS .env
# Output: API_KEYS=dev_key_12345

# 2. Update frontend .env.local to match
cd frontend_web
echo "NEXT_PUBLIC_API_KEY=dev_key_12345" >> .env.local

# 3. Restart frontend
npm run dev
```

### Common Issues

#### 1. Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'asdrp'`

**Solution**:
```bash
# Ensure you're in project root
pwd  # Should show /path/to/openagents

# Reinstall server package
cd server
uv pip install .
cd ..

# Run from root
python -m server.main
```

#### 2. Frontend Can't Connect to Backend

**Error**: `ApiClientError: Failed to fetch`

**Solution**:
```bash
# Check backend is running
curl http://localhost:8000/health

# Check frontend .env.local
cat frontend_web/.env.local

# Verify API_BASE_URL matches backend
# Verify API_KEY matches backend configuration
```

#### 3. Port Already in Use

**Backend (8000)**:
```bash
lsof -i :8000
kill -9 <PID>
```

**Frontend (3000)**:
```bash
lsof -i :3000
kill -9 <PID>
# Or use different port
cd frontend_web
PORT=3001 npm run dev
```

#### 4. Tests Failing

**Backend**:
```bash
# Clear pytest cache
pytest --cache-clear

# Reinstall in editable mode
cd server
uv pip install -e ".[dev]"

# Run specific test
pytest tests/server/test_auth.py -v
```

**Frontend**:
```bash
cd frontend_web

# Clear Jest cache
npm test -- --clearCache

# Run specific test
npm test -- __tests__/lib/api-client.test.ts
```

#### 5. Configuration Errors

**Error**: `Agent 'X' not found in configuration`

**Solution**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/open_agents.yaml'))"

# Check agent is enabled
grep -A 5 "agent_name:" config/open_agents.yaml
```

### Debug Mode

**Backend**:
```bash
export LOG_LEVEL=debug
python -m server.main
```

**Frontend**:
```env
# .env.local
NEXT_PUBLIC_DEBUG=true
```

Then check browser console for detailed logs.

## 🚀 Production Deployment

### Backend Deployment

#### Option 1: Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY server/ ./server/
COPY asdrp/ ./asdrp/
COPY config/ ./config/

RUN pip install uv
RUN uv pip install ./server

CMD ["python", "-m", "server.main"]
```

```bash
docker build -t openagents-server .
docker run -p 8000:8000 \
  -e AUTH_ENABLED=true \
  -e API_KEYS=prod_key_here \
  openagents-server
```

#### Option 2: Systemd Service

```ini
# /etc/systemd/system/openagents.service
[Unit]
Description=OpenAgents Backend
After=network.target

[Service]
Type=simple
User=openagents
WorkingDirectory=/opt/openagents
Environment="PATH=/opt/openagents/venv/bin"
ExecStart=/opt/openagents/venv/bin/python -m server.main
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable openagents
sudo systemctl start openagents
sudo systemctl status openagents
```

### Frontend Deployment

#### Vercel (Recommended)

```bash
cd frontend_web
npm install -g vercel
vercel login
vercel
```

Set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_API_BASE_URL`: https://your-backend-url.com
- `NEXT_PUBLIC_API_KEY`: your_production_api_key

#### Netlify

```bash
cd frontend_web
npm install -g netlify-cli
netlify login
netlify deploy --prod
```

#### Self-Hosted

```bash
cd frontend_web
npm run build
npm start
```

Use nginx as reverse proxy:

```nginx
server {
    listen 80;
    server_name openagents.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 Performance Monitoring

### Backend Metrics

```bash
# Monitor requests
tail -f /var/log/openagents/access.log

# Check resource usage
htop -p $(pgrep -f "server.main")
```

### Frontend Metrics

Use browser DevTools:
- Network tab: API response times
- Performance tab: Page load times
- Lighthouse: Overall score

## 📚 Additional Resources

- **Backend Documentation**: `server/README.md`
- **Frontend Documentation**: `frontend_web/README.md`
- **Frontend Architecture**: `frontend_web/docs/ARCHITECTURE.md`
- **Frontend Tutorial**: `frontend_web/docs/TUTORIAL.md`
- **API Documentation**: http://localhost:8000/docs (when running)

## 🚢 Deploying to Heroku Enterprise

This section provides a comprehensive guide for deploying the OpenAgents multi-agent orchestration system to **Heroku Enterprise**. For a high-level overview of the system architecture, see the [Project README](README.md).

### Heroku Architecture Overview

OpenAgents requires **three separate Heroku applications** to run in production:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HEROKU ENTERPRISE DEPLOYMENT                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐   │
│  │  openagents-web    │   │  openagents-api    │   │ openagents-realtime│   │
│  │  (Next.js Frontend)│   │  (FastAPI Backend) │   │  (LiveKit Worker)  │   │
│  │                    │   │                    │   │                    │   │
│  │  Buildpack:        │   │  Buildpack:        │   │  Buildpack:        │   │
│  │  heroku/nodejs     │   │  heroku/python     │   │  heroku/python     │   │
│  │                    │   │                    │   │                    │   │
│  │  Dyno: web         │   │  Dyno: web         │   │  Dyno: worker      │   │
│  │  Port: $PORT       │   │  Port: $PORT       │   │  No port (daemon)  │   │
│  └─────────┬──────────┘   └─────────┬──────────┘   └─────────┬──────────┘   │
│            │                        │                        │              │
│            │   HTTPS API Calls      │     Job Dispatch       │              │
│            └────────────────────────┤                        │              │
│                                     │                        │              │
│                                     └────────────────────────┘              │
│                                              │                              │
│                                     ┌────────▼────────┐                     │
│                                     │   LiveKit Cloud │                     │
│                                     │   (WebRTC SFU)  │                     │
│                                     └─────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| App | Purpose | Dyno Type | Buildpack |
|-----|---------|-----------|-----------|
| `openagents-web` | Next.js frontend UI | web | `heroku/nodejs` |
| `openagents-api` | FastAPI REST API + SSE streaming | web | `heroku/python` |
| `openagents-realtime` | LiveKit Agents worker (STT→LLM→TTS) | worker | `heroku/python` |

> **Why three apps?** The frontend, API, and realtime worker have different runtime requirements, scaling needs, and deployment lifecycles. See the [Architecture section in README.md](README.md#-architecture-overview) for details.

### Prerequisites for Heroku

Before deploying, ensure you have:

1. **Heroku CLI** installed and authenticated:
   ```bash
   # Install Heroku CLI
   brew tap heroku/brew && brew install heroku  # macOS
   # or
   curl https://cli-assets.heroku.com/install.sh | sh  # Linux
   
   # Login to Heroku Enterprise
   heroku login
   
   # For Enterprise SSO:
   heroku login --sso
   ```

2. **Heroku Enterprise team** access with permissions to create apps

3. **External services configured**:
   - OpenAI API key
   - LiveKit Cloud account (for voice mode)
   - Google Maps API key (for maps)
   - Yelp API key (for Yelp agent)

4. **Git repository** initialized:
   ```bash
   git init  # if not already
   git add .
   git commit -m "Initial commit"
   ```

### Step 1: Create Heroku Apps

Create three separate Heroku apps within your Enterprise team:

```bash
# Set your Heroku team name
HEROKU_TEAM="your-enterprise-team"

# Create the three apps
heroku create openagents-api --team $HEROKU_TEAM
heroku create openagents-web --team $HEROKU_TEAM
heroku create openagents-realtime --team $HEROKU_TEAM

# Verify apps were created
heroku apps --team $HEROKU_TEAM
```

Add Git remotes for each app:

```bash
# From your project root
git remote add heroku-api https://git.heroku.com/openagents-api.git
git remote add heroku-web https://git.heroku.com/openagents-web.git
git remote add heroku-realtime https://git.heroku.com/openagents-realtime.git

# Verify remotes
git remote -v
```

### Step 2: Configure the Backend API

The backend API (`openagents-api`) runs the FastAPI server.

#### 2.1 Create `Procfile` (project root)

```procfile
# Procfile
web: cd server && uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

#### 2.2 Create `runtime.txt` (project root)

```
python-3.11.9
```

#### 2.3 Configure Python buildpack with uv

Create `bin/post_compile` script for uv support:

```bash
mkdir -p bin
cat > bin/post_compile << 'EOF'
#!/bin/bash
# Post-compile hook for Heroku Python buildpack
# This runs after pip install

echo "-----> Installing uv package manager"
pip install uv

echo "-----> Installing project dependencies with uv"
cd $HOME
uv pip install --system -e .

echo "-----> Installing yelp-mcp dependencies"
cd yelp-mcp
uv sync --frozen
cd ..

echo "-----> Post-compile complete"
EOF
chmod +x bin/post_compile
```

#### 2.4 Create `requirements.txt` (project root)

Even with uv, Heroku needs a `requirements.txt` for initial detection:

```bash
# Generate requirements.txt from pyproject.toml
uv pip compile pyproject.toml -o requirements.txt

# Or create minimal requirements.txt that installs the project
cat > requirements.txt << 'EOF'
# Heroku Python buildpack detection
# Actual dependencies are in pyproject.toml and installed via uv
uv>=0.4.0
-e .
EOF
```

#### 2.5 Set buildpack

```bash
heroku buildpacks:set heroku/python --app openagents-api
```

### Step 3: Configure the Realtime Worker

The realtime worker (`openagents-realtime`) runs the LiveKit Agents daemon.

#### 3.1 Create `Procfile.realtime`

Since we're using a monorepo, create a separate Procfile for the worker:

```procfile
# Procfile.realtime
worker: python -m server.voice.realtime.worker
```

#### 3.2 Deploy with custom Procfile

```bash
# Copy Procfile.realtime to Procfile before deploying
# This is handled in the deploy script (see Step 6)
```

#### 3.3 Configure dyno type

```bash
# The realtime worker uses a worker dyno (not web)
heroku ps:scale web=0 worker=1 --app openagents-realtime
```

### Step 4: Configure the Frontend

The frontend (`openagents-web`) runs the Next.js application.

#### 4.1 Create `frontend_web/Procfile`

```procfile
# frontend_web/Procfile
web: PORT=$PORT node .next/standalone/server.js
```

> **Note**: The Next.js config uses `output: 'standalone'` which requires running the standalone server instead of `next start`.

#### 4.2 Update `frontend_web/package.json`

The project uses Next.js standalone output mode for optimized production builds. Ensure scripts are configured correctly:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build && npm run postbuild",
    "postbuild": "[ -d public ] && cp -r public .next/standalone/ || true; cp -r .next/static .next/standalone/.next/",
    "start": "node .next/standalone/server.js",
    "start:dev": "next start",
    "lint": "next lint"
  },
  "engines": {
    "node": "18.x",
    "npm": "10.x"
  }
}
```

**Why standalone mode?**
- Produces a minimal production bundle (~80% smaller)
- Only includes necessary dependencies
- Optimized for containerized/serverless deployments
- Faster cold starts on Heroku

**Important**: The `postbuild` script copies static assets to the standalone directory since they're not included automatically.

#### 4.3 Create `frontend_web/.node-version`

```
18.20.4
```

#### 4.4 Set buildpack

```bash
heroku buildpacks:set heroku/nodejs --app openagents-web
```

#### 4.5 Configure app root

Since the frontend is in a subdirectory, configure Heroku to use it:

```bash
# Option A: Use heroku-buildpack-monorepo (recommended)
heroku buildpacks:add -i 1 https://github.com/lstoll/heroku-buildpack-monorepo --app openagents-web
heroku config:set APP_BASE=frontend_web --app openagents-web

# Option B: Use git subtree (alternative)
# git subtree push --prefix frontend_web heroku-web main
```

### Step 5: Environment Variables

Configure environment variables for each app.

#### 5.1 Backend API Environment

```bash
# Core settings
heroku config:set AUTH_ENABLED=true --app openagents-api
heroku config:set API_KEYS="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" --app openagents-api
heroku config:set AGENT_CONFIG_PATH=config/open_agents.yaml --app openagents-api
heroku config:set ORCHESTRATOR=moe --app openagents-api

# External API keys
heroku config:set OPENAI_API_KEY=sk-your-openai-key --app openagents-api
heroku config:set PERPLEXITY_API_KEY=pplx-your-key --app openagents-api
heroku config:set GOOGLE_MAPS_API_KEY=AIza-your-key --app openagents-api
heroku config:set GOOGLE_API_KEY=AIza-your-key --app openagents-api
heroku config:set YELP_API_KEY=your-yelp-key --app openagents-api

# LiveKit settings (for session creation)
heroku config:set LIVEKIT_URL=wss://your-project.livekit.cloud --app openagents-api
heroku config:set LIVEKIT_API_KEY=your-livekit-key --app openagents-api
heroku config:set LIVEKIT_API_SECRET=your-livekit-secret --app openagents-api

# Verify configuration
heroku config --app openagents-api
```

#### 5.2 Realtime Worker Environment

```bash
# Copy same API keys as backend
heroku config:set OPENAI_API_KEY=sk-your-openai-key --app openagents-realtime
heroku config:set LIVEKIT_URL=wss://your-project.livekit.cloud --app openagents-realtime
heroku config:set LIVEKIT_API_KEY=your-livekit-key --app openagents-realtime
heroku config:set LIVEKIT_API_SECRET=your-livekit-secret --app openagents-realtime

# Agent configuration
heroku config:set AGENT_CONFIG_PATH=config/open_agents.yaml --app openagents-realtime
heroku config:set ORCHESTRATOR=moe --app openagents-realtime

# Additional API keys for agents
heroku config:set PERPLEXITY_API_KEY=pplx-your-key --app openagents-realtime
heroku config:set GOOGLE_MAPS_API_KEY=AIza-your-key --app openagents-realtime
heroku config:set YELP_API_KEY=your-yelp-key --app openagents-realtime
```

#### 5.3 Frontend Environment

```bash
# API connection (use your actual Heroku API app URL)
heroku config:set NEXT_PUBLIC_API_BASE_URL=https://openagents-api.herokuapp.com --app openagents-web

# Get the API key you set earlier
API_KEY=$(heroku config:get API_KEYS --app openagents-api)
heroku config:set NEXT_PUBLIC_API_KEY=$API_KEY --app openagents-web

# Google Maps (client-side for interactive maps)
heroku config:set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIza-your-key --app openagents-web

# LiveKit for voice mode
heroku config:set NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud --app openagents-web
```

#### 5.4 Environment Variables Summary

| Variable | API | Worker | Frontend | Description |
|----------|-----|--------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | ✅ | ❌ | OpenAI API access |
| `LIVEKIT_URL` | ✅ | ✅ | ✅* | LiveKit server URL |
| `LIVEKIT_API_KEY` | ✅ | ✅ | ❌ | LiveKit API key |
| `LIVEKIT_API_SECRET` | ✅ | ✅ | ❌ | LiveKit secret |
| `GOOGLE_MAPS_API_KEY` | ✅ | ✅ | ✅* | Google Maps API |
| `PERPLEXITY_API_KEY` | ✅ | ✅ | ❌ | Perplexity API |
| `YELP_API_KEY` | ✅ | ✅ | ❌ | Yelp Fusion API |
| `API_KEYS` | ✅ | ❌ | ❌ | Server auth keys |
| `NEXT_PUBLIC_API_KEY` | ❌ | ❌ | ✅ | Frontend auth |
| `NEXT_PUBLIC_API_BASE_URL` | ❌ | ❌ | ✅ | Backend URL |

*Frontend uses `NEXT_PUBLIC_` prefix for client-side access

### Step 6: Deploy

Create a deployment script for consistent deploys:

#### 6.1 Create `scripts/deploy_heroku.sh`

```bash
#!/bin/bash
# scripts/deploy_heroku.sh - Deploy OpenAgents to Heroku Enterprise

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 OpenAgents Heroku Deployment${NC}"
echo "=================================="

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Deploy Backend API
deploy_api() {
    echo -e "\n${GREEN}📦 Deploying Backend API...${NC}"
    
    # Ensure correct Procfile
    cp Procfile.api Procfile 2>/dev/null || cat > Procfile << 'EOF'
web: uvicorn server.main:app --host 0.0.0.0 --port $PORT
EOF
    
    git add Procfile
    git commit -m "Deploy: Configure API Procfile" --allow-empty
    
    git push heroku-api main
    
    echo -e "${GREEN}✅ Backend API deployed${NC}"
    heroku open --app openagents-api
}

# Deploy Realtime Worker
deploy_realtime() {
    echo -e "\n${GREEN}📦 Deploying Realtime Worker...${NC}"
    
    # Use worker Procfile
    cat > Procfile << 'EOF'
worker: python -m server.voice.realtime.worker
EOF
    
    git add Procfile
    git commit -m "Deploy: Configure Realtime Worker Procfile" --allow-empty
    
    git push heroku-realtime main
    
    # Scale worker dyno
    heroku ps:scale web=0 worker=1 --app openagents-realtime
    
    echo -e "${GREEN}✅ Realtime Worker deployed${NC}"
}

# Deploy Frontend
deploy_frontend() {
    echo -e "\n${GREEN}📦 Deploying Frontend...${NC}"
    
    # Using monorepo buildpack
    git push heroku-web main
    
    echo -e "${GREEN}✅ Frontend deployed${NC}"
    heroku open --app openagents-web
}

# Parse arguments
case "${1:-all}" in
    api)
        deploy_api
        ;;
    realtime)
        deploy_realtime
        ;;
    frontend|web)
        deploy_frontend
        ;;
    all)
        deploy_api
        deploy_realtime
        deploy_frontend
        ;;
    *)
        echo "Usage: $0 {api|realtime|frontend|all}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}🎉 Deployment complete!${NC}"
echo "=================================="
echo "Frontend: https://openagents-web.herokuapp.com"
echo "API:      https://openagents-api.herokuapp.com"
echo "API Docs: https://openagents-api.herokuapp.com/docs"
```

Make it executable:

```bash
chmod +x scripts/deploy_heroku.sh
```

#### 6.2 Deploy All Apps

```bash
# Deploy everything
./scripts/deploy_heroku.sh all

# Or deploy individually
./scripts/deploy_heroku.sh api
./scripts/deploy_heroku.sh realtime
./scripts/deploy_heroku.sh frontend
```

#### 6.3 Verify Deployment

```bash
# Check API health
curl https://openagents-api.herokuapp.com/health

# Check API logs
heroku logs --tail --app openagents-api

# Check worker logs
heroku logs --tail --app openagents-realtime

# Check frontend logs
heroku logs --tail --app openagents-web

# Check dyno status
heroku ps --app openagents-api
heroku ps --app openagents-realtime
heroku ps --app openagents-web
```

### Step 7: LiveKit Integration

Voice mode requires LiveKit Cloud for WebRTC media transport.

#### 7.1 LiveKit Cloud Setup

1. Create account at [LiveKit Cloud](https://cloud.livekit.io)
2. Create a new project
3. Get credentials from Settings → API Keys
4. Configure webhook URL: `https://openagents-api.herokuapp.com/voice/webhook`

#### 7.2 Configure LiveKit Webhook

```bash
# Set webhook secret (from LiveKit dashboard)
heroku config:set LIVEKIT_WEBHOOK_SECRET=your-webhook-secret --app openagents-api
```

#### 7.3 Test Voice Mode

1. Open `https://openagents-web.herokuapp.com`
2. Click the microphone icon to enter Voice Mode
3. Check worker logs for connection: `heroku logs --tail --app openagents-realtime`

### Step 8: Database Setup

OpenAgents uses SQLite for session storage by default. For production on Heroku, consider PostgreSQL.

#### 8.1 Add Heroku Postgres

```bash
# Add PostgreSQL to API app
heroku addons:create heroku-postgresql:essential-0 --app openagents-api

# Get database URL
heroku config:get DATABASE_URL --app openagents-api
```

#### 8.2 Configure Session Storage

Update your agent configuration to use PostgreSQL:

```yaml
# config/open_agents.yaml (production override)
session_memory:
  type: postgresql
  database_url: ${DATABASE_URL}
  enabled: true
```

> **Note**: The default SQLite storage works for testing but doesn't persist across dyno restarts. For production, migrate to PostgreSQL.

### Step 9: Scaling & Performance

#### 9.1 Heroku Enterprise Dyno Types

| App | Recommended Dyno | Why |
|-----|-----------------|-----|
| `openagents-api` | Performance-M | Handles concurrent API requests |
| `openagents-realtime` | Performance-L | CPU-intensive audio processing |
| `openagents-web` | Standard-2X | Next.js SSR |

```bash
# Scale dynos
heroku ps:resize web=performance-m --app openagents-api
heroku ps:resize worker=performance-l --app openagents-realtime
heroku ps:resize web=standard-2x --app openagents-web

# Scale horizontally
heroku ps:scale web=2 --app openagents-api
heroku ps:scale worker=2 --app openagents-realtime
```

#### 9.2 Performance Optimization

```bash
# Enable preboot for zero-downtime deploys
heroku features:enable preboot --app openagents-api
heroku features:enable preboot --app openagents-web

# Enable log drains for monitoring
heroku drains:add https://your-logging-service.com/heroku --app openagents-api
```

#### 9.3 Autoscaling (Enterprise)

```bash
# Configure autoscaling for API
heroku autoscale:enable web --app openagents-api \
    --min 2 --max 10 \
    --p95 1000 \
    --notification-email devops@yourcompany.com
```

### Step 10: CI/CD Pipeline

#### 10.1 Heroku Pipeline Setup

```bash
# Create pipeline
heroku pipelines:create openagents --team $HEROKU_TEAM

# Add apps to pipeline
heroku pipelines:add openagents --app openagents-api --stage production
heroku pipelines:add openagents --app openagents-web --stage production
heroku pipelines:add openagents --app openagents-realtime --stage production

# Create staging apps
heroku create openagents-api-staging --team $HEROKU_TEAM
heroku pipelines:add openagents --app openagents-api-staging --stage staging
```

#### 10.2 GitHub Integration

1. Go to Heroku Dashboard → openagents pipeline
2. Click "Connect to GitHub"
3. Select your repository
4. Enable automatic deploys from `main` branch
5. Enable "Wait for CI to pass before deploy"

#### 10.3 GitHub Actions Workflow

Create `.github/workflows/heroku-deploy.yml`:

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install uv
        run: pip install uv
      
      - name: Install dependencies
        run: uv pip install --system -e ".[dev]"
      
      - name: Run backend tests
        run: pytest tests/ -v
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend_web/package-lock.json
      
      - name: Install frontend dependencies
        working-directory: frontend_web
        run: npm ci
      
      - name: Run frontend tests
        working-directory: frontend_web
        run: npm test

  deploy-api:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: akhileshns/heroku-deploy@v3.13.15
        with:
          heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
          heroku_app_name: openagents-api
          heroku_email: ${{ secrets.HEROKU_EMAIL }}

  deploy-realtime:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: akhileshns/heroku-deploy@v3.13.15
        with:
          heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
          heroku_app_name: openagents-realtime
          heroku_email: ${{ secrets.HEROKU_EMAIL }}
          
  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: akhileshns/heroku-deploy@v3.13.15
        with:
          heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
          heroku_app_name: openagents-web
          heroku_email: ${{ secrets.HEROKU_EMAIL }}
          appdir: frontend_web
```

### Heroku Troubleshooting

#### Issue: Build fails with "No module named 'asdrp'"

```bash
# Ensure package is installed in editable mode
# Check requirements.txt includes:
-e .
```

#### Issue: Worker dyno crashes immediately

```bash
# Check logs
heroku logs --tail --app openagents-realtime

# Verify LiveKit credentials
heroku config --app openagents-realtime | grep LIVEKIT

# Ensure worker scale is correct
heroku ps --app openagents-realtime
# Should show: worker.1: up
```

#### Issue: Frontend can't connect to API

```bash
# Verify CORS is configured in backend
# Check server/main.py allows your frontend domain

# Verify frontend env vars
heroku config --app openagents-web | grep NEXT_PUBLIC

# Test API directly
curl -H "X-API-Key: your-key" https://openagents-api.herokuapp.com/health
```

#### Issue: Voice mode not working

```bash
# Check LiveKit worker is running
heroku ps --app openagents-realtime

# Check worker logs for connection
heroku logs --tail --app openagents-realtime | grep -i livekit

# Verify LiveKit credentials match across apps
heroku config:get LIVEKIT_URL --app openagents-api
heroku config:get LIVEKIT_URL --app openagents-realtime
```

#### Issue: Dyno sleeping (free tier)

```bash
# Upgrade to paid dynos for always-on
heroku ps:resize web=basic --app openagents-api

# Or use Heroku Scheduler to ping the app
heroku addons:create scheduler:standard --app openagents-api
```

#### Issue: Memory quota exceeded

```bash
# Check memory usage
heroku logs --app openagents-api | grep "Memory quota"

# Upgrade dyno size
heroku ps:resize web=standard-2x --app openagents-api

# Or optimize your application
heroku config:set WEB_CONCURRENCY=2 --app openagents-api
```

#### Useful Heroku Commands

```bash
# View all apps
heroku apps --team $HEROKU_TEAM

# Restart dynos
heroku restart --app openagents-api

# Run one-off command
heroku run python -c "print('hello')" --app openagents-api

# View metrics
heroku metrics --app openagents-api

# Database operations
heroku pg:info --app openagents-api
heroku pg:psql --app openagents-api

# Release history
heroku releases --app openagents-api

# Rollback
heroku rollback v123 --app openagents-api
```

### Heroku Enterprise Security Considerations

1. **Private Spaces**: Deploy apps in Heroku Private Spaces for network isolation
2. **Shield**: Use Heroku Shield for HIPAA/PCI compliance
3. **SSO**: Configure SAML SSO for team access
4. **Audit Logs**: Enable audit logging for compliance

```bash
# Create app in Private Space
heroku create openagents-api --team $HEROKU_TEAM --space your-private-space

# Enable Shield
heroku addons:create heroku-postgresql:shield-0 --app openagents-api
```

## ✅ Final Checklist

### Local Development
- [ ] Backend server starts without errors
- [ ] Frontend starts without errors
- [ ] Can access http://localhost:3000
- [ ] Can select and interact with agents
- [ ] Can edit and save configuration
- [ ] Graph visualization displays correctly
- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] No console errors in browser
- [ ] API authentication works
- [ ] Voice mode works (if LiveKit configured)

### Heroku Enterprise Deployment
- [ ] All three Heroku apps created (`api`, `web`, `realtime`)
- [ ] Environment variables configured for all apps
- [ ] Backend API deploys successfully
- [ ] Backend health check passes: `curl https://openagents-api.herokuapp.com/health`
- [ ] Realtime worker deploys and runs as `worker` dyno
- [ ] Frontend deploys and connects to API
- [ ] Voice mode works in production (LiveKit integrated)
- [ ] CI/CD pipeline configured (optional)
- [ ] Monitoring and logging enabled (optional)

## 🎉 Success!

You now have a fully functional multi-agent orchestration system!

**What you can do:**
- ✅ Simulate agent interactions
- ✅ Edit agent configurations
- ✅ Visualize agent relationships
- ✅ Run comprehensive tests
- ✅ Deploy to production on Heroku Enterprise
- ✅ Scale horizontally with multiple dynos
- ✅ Use voice mode with LiveKit WebRTC

**Production URLs (after Heroku deployment):**
- Frontend: `https://openagents-web.herokuapp.com`
- API: `https://openagents-api.herokuapp.com`
- API Docs: `https://openagents-api.herokuapp.com/docs`

For questions or issues, check the troubleshooting section or review the documentation files. See the [README.md](README.md) for architecture overview and feature list.

**Happy orchestrating! 🤖🚀**
