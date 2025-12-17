# OpenAgents

A production-ready **multi-agent orchestration system** with real-time voice capabilities, featuring a Next.js web UI, FastAPI backend, and sophisticated agent coordination through MoE (Mixture of Experts) and SmartRouter orchestration patterns.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│
│  │ Chat Interface│ │ Voice Mode   │ │ MoE Trace    │ │ Interactive Maps    ││
│  │ (Text + Stream)│ │ (WebRTC)     │ │ Visualization│ │ (Google Maps)      ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                         HTTP/SSE ────┴──── WebRTC (LiveKit)
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Orchestration Layer                              │   │
│  │  ┌─────────────────────────┐    ┌─────────────────────────────────┐  │   │
│  │  │   MoE Orchestrator      │    │      SmartRouter                │  │   │
│  │  │  - Expert Selection     │    │  - Capability Routing           │  │   │
│  │  │  - Parallel Execution   │    │  - Query Decomposition          │  │   │
│  │  │  - Result Synthesis     │    │  - Result Synthesis             │  │   │
│  │  │  - Trace Visualization  │    │  - Fast-Path Detection          │  │   │
│  │  └─────────────────────────┘    └─────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Agent Pool                                    │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │   │
│  │  │Chitchat│ │  Geo   │ │ Finance│ │  Map   │ │  Wiki  │ │Perplexity│ │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └──────────┘ │   │
│  │  ┌────────┐ ┌────────┐ ┌────────────────────────────────────────────┐│   │
│  │  │  Yelp  │ │YelpMCP │ │           MCP Server Integration           ││   │
│  │  │        │ │(+ Maps)│ │      (Model Context Protocol)              ││   │
│  │  └────────┘ └────────┘ └────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                              LiveKit Workers
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REAL-TIME VOICE (LiveKit Agents)                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│
│  │ STT (Whisper)│ │ MoE Agent    │ │ TTS (OpenAI) │ │ Semantic Endpointing ││
│  │ Speech→Text  │ │ Processing   │ │ Text→Speech  │ │ Turn Detection       ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🤖 Multi-Agent System
- **8+ Specialized Agents**: Chitchat, Geo, Finance, Map, Wiki, Perplexity, Yelp, YelpMCP
- **MCP Integration**: Model Context Protocol support for external tool servers (Yelp Fusion AI)
- **Session Memory**: SQLite-backed persistent conversation history per agent
- **Dynamic Agent Loading**: YAML-configured agent pool with hot-reload capability

### 🎯 Intelligent Orchestration

#### MoE (Mixture of Experts) Orchestrator
- **Semantic Expert Selection**: Embedding-based routing using OpenAI embeddings
- **Parallel Execution**: Concurrent agent execution with configurable limits
- **LLM-Based Synthesis**: GPT-4 powered result aggregation
- **Fast-Path Detection**: Bypass orchestration for simple queries (chitchat)
- **Detailed Markdown Output**: Rich formatting for chat interface
- **Interactive Visualizations**: Real-time execution trace with React Flow

#### SmartRouter Orchestrator
- **Capability-Based Routing**: Match queries to agent capabilities
- **Query Decomposition**: Break complex queries into sub-queries
- **LLM Judge**: Evaluate and rank responses
- **Semantic Caching**: Cache responses for similar queries

### 🎤 Real-Time Voice Mode
- **WebRTC Audio**: Low-latency bidirectional audio via LiveKit
- **OpenAI Whisper STT**: High-accuracy speech-to-text
- **OpenAI TTS**: Natural text-to-speech with multiple voices
- **Semantic Endpointing**: Intelligent turn detection
- **Dual Output**: Voice summarizes, chat shows full details
- **MoE Integration**: Voice queries routed through orchestrator

### 🗺️ Interactive Maps
- **Google Maps Integration**: Embedded interactive maps
- **Auto-Injection**: Automatic map generation for location queries
- **Route Visualization**: Driving directions with turn-by-turn
- **Business Markers**: Yelp results plotted on maps
- **Geocoding**: Address-to-coordinate conversion

### 💬 Chat Interface
- **Streaming Responses**: Real-time token streaming via SSE
- **Markdown Rendering**: Rich formatting with syntax highlighting
- **Conversation History**: Persistent chat sessions
- **Agent Selection**: Manual agent override capability
- **Execution Modes**: Real (API) or Mock (testing)

---

## 📁 Project Structure

```
openagents/
├── asdrp/                          # Core Python package
│   ├── actions/                    # Tool implementations
│   │   ├── finance/               # Stock/market data tools
│   │   ├── geo/                   # Geocoding & map tools
│   │   ├── local/                 # Local business (Yelp) tools
│   │   └── search/                # Web search (Perplexity, Wiki)
│   ├── agents/                     # Agent implementations
│   │   ├── single/                # Individual agents
│   │   │   ├── chitchat_agent.py  # Social conversation
│   │   │   ├── finance_agent.py   # Stock queries
│   │   │   ├── geo_agent.py       # Geocoding
│   │   │   ├── map_agent.py       # Interactive maps
│   │   │   ├── wiki_agent.py      # Wikipedia search
│   │   │   ├── perplexity_agent.py # AI-powered search
│   │   │   └── yelp_agent.py      # Business search
│   │   ├── mcp/                   # MCP-enabled agents
│   │   │   └── yelp_mcp_agent.py  # Yelp via MCP server
│   │   ├── agent_factory.py       # Agent creation factory
│   │   ├── config_loader.py       # YAML config loading
│   │   └── protocol.py            # AgentProtocol interface
│   └── orchestration/              # Orchestration systems
│       ├── moe/                   # Mixture of Experts
│       │   ├── orchestrator.py    # Main MoE logic
│       │   ├── expert_selector.py # Semantic selection
│       │   ├── expert_executor.py # Parallel execution
│       │   ├── result_mixer.py    # LLM synthesis
│       │   ├── fast_path.py       # Chitchat bypass
│       │   └── map_injector.py    # Auto map injection
│       └── smartrouter/           # SmartRouter
│           ├── smartrouter.py     # Main router logic
│           ├── capability_router.py
│           └── query_decomposer.py
├── server/                         # FastAPI backend
│   ├── main.py                    # API endpoints
│   ├── agent_service.py           # Agent execution service
│   ├── models.py                  # Pydantic models
│   └── voice/                     # Voice subsystem
│       ├── realtime/              # LiveKit integration
│       │   ├── agent.py           # Voice agent
│       │   ├── worker.py          # LiveKit worker
│       │   └── service.py         # Session management
│       └── providers/             # TTS/STT providers
│           ├── openai_provider.py
│           └── elevenlabs_provider.py
├── frontend_web/                   # Next.js frontend
│   ├── app/                       # Next.js app router
│   ├── components/                # React components
│   │   ├── unified-chat-interface.tsx  # Main chat UI
│   │   ├── interactive-map.tsx    # Google Maps component
│   │   ├── voice/                 # Voice mode components
│   │   │   ├── VoiceModeProvider.tsx
│   │   │   └── VoiceModeInterface.tsx
│   │   └── visualization/         # MoE trace visualization
│   │       └── MoEFlowVisualization.tsx
│   └── lib/                       # Utilities
│       ├── api-client.ts          # Backend API client
│       └── services/              # Frontend services
├── config/                         # Configuration files
│   ├── open_agents.yaml           # Agent definitions
│   ├── moe.yaml                   # MoE orchestrator config
│   ├── smartrouter.yaml           # SmartRouter config
│   └── voice_config.yaml          # Voice mode config
├── yelp-mcp/                       # Yelp MCP server
│   └── src/                       # MCP server implementation
├── tests/                          # Test suites
│   ├── asdrp/                     # Backend tests
│   └── server/                    # API tests
├── scripts/                        # Utility scripts
│   ├── run_server.sh              # Start backend
│   ├── run_realtime.sh            # Start voice worker
│   ├── run_be_tests.sh            # Run backend tests
│   └── run_fe_tests.sh            # Run frontend tests
└── docs/                           # Documentation
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (with uv package manager recommended)
- **Node.js 18+**
- **OpenAI API Key** (required)
- **LiveKit credentials** (for voice mode, optional)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd openagents

# Copy environment template
cp .env.example .env

# Edit .env and set required keys:
# - OPENAI_API_KEY (required)
# - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET (for voice)
# - YELP_API_KEY (for Yelp agent)
# - PERPLEXITY_API_KEY (for Perplexity agent)
```

### 2. Start Backend (Text Chat)

```bash
# Install Python dependencies
pip install -e .

# Start the FastAPI server
./scripts/run_server.sh --dev
```

Backend runs at `http://localhost:8000`

### 3. Start Frontend

```bash
cd frontend_web
npm install

# Configure frontend
cp .env.local.example .env.local
# Edit .env.local:
# - NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# - NEXT_PUBLIC_API_KEY=<your-api-key>

npm run dev
```

Frontend runs at `http://localhost:3000`

### 4. Start Voice Mode (Optional)

In a separate terminal:

```bash
# Start LiveKit Agents worker
./scripts/run_realtime.sh --dev
```

---

## ⚙️ Configuration

### Agent Configuration (`config/open_agents.yaml`)

```yaml
agents:
  chitchat:
    display_name: ChitchatAgent
    module: asdrp.agents.single.chitchat_agent
    function: create_chitchat_agent
    model:
      name: gpt-4.1-nano
      temperature: 0.7
    session_memory:
      type: sqlite
      enabled: true
    capabilities:
      - conversation
      - social
    enabled: true
```

### MoE Configuration (`config/moe.yaml`)

```yaml
moe:
  selection_strategy: "semantic"  # or "capability_match"
  top_k_experts: 3
  confidence_threshold: 0.5
  fast_path_enabled: true
  mixing_strategy: "synthesis"
  parallel_execution: true
  timeout_per_expert: 12.0
```

### Voice Configuration (`config/voice_config.yaml`)

```yaml
voice:
  enabled: true
  default_provider: "openai"
  providers:
    openai:
      tts:
        model: "gpt-4o-mini-tts"
        voice: "sage"
      stt:
        model: "gpt-4o-transcribe"
  realtime:
    agent:
      type: moe
```

---

## 🧪 Testing

### Backend Tests

```bash
./scripts/run_be_tests.sh

# Or run specific tests
python -m pytest tests/asdrp/orchestration/moe/ -v
```

### Frontend Tests

```bash
./scripts/run_fe_tests.sh

# Or directly
cd frontend_web && npm test
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/agents` | List available agents |
| `GET` | `/agents/{id}` | Get agent details |
| `GET` | `/agents/{id}/graph` | Get agent tool graph |
| `POST` | `/agents/{id}/execute` | Execute agent (JSON response) |
| `POST` | `/agents/{id}/chat` | Execute with history |
| `POST` | `/agents/{id}/chat/stream` | Streaming response (SSE) |
| `GET` | `/config` | Get current config |
| `PUT` | `/config` | Update config |
| `POST` | `/voice/realtime/session` | Create voice session |
| `DELETE` | `/voice/realtime/session/{id}` | End voice session |

---

## 🔧 Development

### Adding a New Agent

1. Create agent file in `asdrp/agents/single/`:

```python
# my_agent.py
from agents import Agent
from asdrp.agents.protocol import AgentProtocol

def create_my_agent(instructions=None, model_config=None) -> AgentProtocol:
    return Agent(
        name="MyAgent",
        instructions=instructions or "Default instructions",
        tools=[...],
    )
```

2. Register in `config/open_agents.yaml`:

```yaml
agents:
  my_agent:
    display_name: MyAgent
    module: asdrp.agents.single.my_agent
    function: create_my_agent
    capabilities: [my_capability]
    enabled: true
```

### Adding MCP Integration

See `asdrp/agents/mcp/yelp_mcp_agent.py` for the MCP integration pattern:

```python
from agents.mcp import MCPServerStdio

mcp_server = MCPServerStdio(
    name="MyMCP",
    params=MCPServerStdioParams(...),
)

agent = Agent(
    name="MyMCPAgent",
    mcp_servers=[mcp_server],
)
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| `docs/README.md` | Documentation index |
| `docs/COMPLETE_TUTORIAL.md` | Full setup tutorial |
| `docs/moe/moe_orchestrator.md` | MoE architecture |
| `docs/router/smartrouter.md` | SmartRouter guide |
| `docs/voice/realtime_implementation.md` | Voice mode details |
| `docs/mcp/MCP_INTEGRATION_GUIDE.md` | MCP setup guide |
| `docs/agents/agent_factory.md` | Agent factory patterns |

---

## 🚀 Production Deployment

### Heroku Enterprise

OpenAgents supports deployment to **Heroku Enterprise** with three separate apps:

| App | Purpose | Dyno Type |
|-----|---------|-----------|
| `openagents-web` | Next.js frontend | web |
| `openagents-api` | FastAPI backend | web |
| `openagents-realtime` | LiveKit voice worker | worker |

For complete deployment instructions, see:
- **[Heroku Enterprise Deployment Guide](docs/COMPLETE_TUTORIAL.md#deploying-to-heroku-enterprise)** - Step-by-step setup, CI/CD pipeline, scaling, and troubleshooting

### Docker

For Docker and self-hosted deployments, see the [Production Deployment section](docs/COMPLETE_TUTORIAL.md#production-deployment).

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `LIVEKIT_URL` | Voice | LiveKit server URL |
| `LIVEKIT_API_KEY` | Voice | LiveKit API key |
| `LIVEKIT_API_SECRET` | Voice | LiveKit API secret |
| `YELP_API_KEY` | Yelp | Yelp Fusion API key |
| `PERPLEXITY_API_KEY` | Search | Perplexity API key |
| `GOOGLE_MAPS_API_KEY` | Maps | Google Maps API key |
| `ORCHESTRATOR` | No | `moe` (default) or `smartrouter` |

---

## 📄 License

MIT License - see LICENSE file for details.
