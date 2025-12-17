# CLAUDE.md - AI Assistant Guide for OpenAgents

**Project**: OpenAgents - Multi-Agent Orchestration System
**Version**: 3.0 (Glass Morphism Edition)
**Last Updated**: December 7, 2025
**Purpose**: Guide for AI assistants (Claude, GPT, etc.) to understand and work with this codebase

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Key Patterns & Principles](#key-patterns--principles)
6. [Backend System](#backend-system)
7. [Frontend System](#frontend-system)
8. [Agent System](#agent-system)
9. [Configuration](#configuration)
10. [Testing](#testing)
11. [Common Tasks](#common-tasks)
12. [Important Constraints](#important-constraints)
13. [Troubleshooting](#troubleshooting)

---

## 📖 Project Overview

### What is OpenAgents?

OpenAgents is a **full-stack, production-ready platform** for building, orchestrating, and deploying AI agents with a modern web interface. It enables developers to create specialized agents that can be combined to solve complex tasks.

### Core Capabilities

- 🤖 **Multi-Agent System**: Orchestrate 9 specialized agents (geo, finance, map, web search, Wikipedia, Perplexity AI, Yelp, chitchat)
- 📡 **Three Execution Modes**: Mock (testing), Real (production), Stream (real-time UX)
- 🎨 **Modern Glass Morphism UI**: Contemporary frosted glass aesthetic with backdrop blur
- 📝 **Rich Content**: Markdown rendering with images, code blocks, tables
- 🔒 **Enterprise Security**: API key auth, CORS, input validation
- ✅ **Comprehensive Testing**: >90% coverage across frontend and backend

### Key Features

```
Frontend (Next.js 14)          Backend (FastAPI)           Agents (OpenAI)
├─ Modern UI/UX               ├─ RESTful API              ├─ Protocol-based
├─ Service Layer              ├─ Streaming Support        ├─ Tool-enabled
├─ Smart Scrolling            ├─ Session Management       ├─ Configurable
├─ Markdown Rendering         ├─ Authentication          └─ Factory Pattern
└─ Dependency Injection       └─ CORS & Security
```

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                         │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/HTTPS
        ┌────────▼─────────┐
        │  Frontend (3000) │  Next.js 14 + TypeScript
        │  - React UI      │  - Service Layer (DI)
        │  - Glass Design  │  - API Client (Singleton)
        └────────┬─────────┘
                 │ REST API / SSE
        ┌────────▼─────────┐
        │  Backend (8000)  │  FastAPI + Python 3.11+
        │  - API Endpoints │  - Agent Service Layer
        │  - Auth Layer    │  - Streaming Support
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │  Agent System    │  OpenAI Agents SDK
        │  - AgentFactory  │  - Protocol-based
        │  - ConfigLoader  │  - Tool Integration
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │  OpenAI API      │  GPT-4.1-mini, GPT-4
        │  - LLM Calls     │  - WebSearchTool
        │  - Streaming     │  - Function Calling
        └──────────────────┘
```

### Data Flow

#### 1. User Request → Agent Response (Non-Streaming)
```
User Input
  ↓
Frontend: UnifiedChatInterface
  ↓
Service: AgentExecutionService.executeReal()
  ↓
API Client: POST /agents/{id}/chat
  ↓
Backend: chat_agent endpoint
  ↓
AgentService: chat_agent()
  ↓
AgentFactory: get_agent_with_session()
  ↓
OpenAI: Runner.run(agent, input, session)
  ↓
Response flows back up the stack
  ↓
Frontend: Display in chat
```

#### 2. Streaming Request (Real-time Tokens)
```
User Input
  ↓
Frontend: UnifiedChatInterface (streaming=true)
  ↓
Service: AgentExecutionService.executeStream()
  ↓
API Client: POST /agents/{id}/chat/stream (SSE)
  ↓
Backend: chat_agent_streaming endpoint
  ↓
AgentService: chat_agent_streaming() generator
  ↓
OpenAI: Runner.run_streamed(agent, input, session)
  ↓
Stream chunks (metadata → token → token → ... → done)
  ↓
Frontend: Update message in real-time
```

---

## 🛠️ Technology Stack

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 14.x | React framework with App Router |
| **TypeScript** | 5.x | Type-safe JavaScript |
| **React** | 18.x | UI library |
| **Tailwind CSS** | 3.x | Utility-first styling |
| **shadcn/ui** | Latest | Component library (Radix UI) |
| **react-markdown** | 9.x | Markdown rendering (GFM) |
| **ReactFlow** | 11.x | Graph visualization |
| **Jest** | 29.x | Testing framework |

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11+ | Runtime |
| **FastAPI** | 0.115+ | Web framework |
| **Pydantic** | 2.x | Data validation |
| **OpenAI Agents SDK** | Latest | Agent orchestration |
| **pytest** | 8.x | Testing framework |
| **uvicorn** | 0.32+ | ASGI server |

### Agent Tools

| Tool | Purpose |
|------|---------|
| **WebSearchTool** | Web search (text only, no images) |
| **Google Maps API** | Geocoding, places, directions |
| **Yelp API** | Business search and reviews |
| **yfinance** | Financial data and stock info |
| **Wikipedia API** | Wikipedia search, content, summaries, images, links |
| **Perplexity AI** | AI-powered search with real-time web data and citations |

---

## 📁 Project Structure

```
openagents/
├── frontend_web/                 # Next.js 14 Frontend (v3.0)
│   ├── app/
│   │   ├── layout.tsx            # Root layout with ServiceProvider
│   │   ├── page.tsx              # Main: Agent Execution UI
│   │   ├── config-editor/        # YAML editor + graph visualization
│   │   ├── help/                 # Help documentation page
│   │   └── globals.css           # Glass morphism styles
│   │
│   ├── components/
│   │   ├── ui/                   # shadcn/ui base components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── select.tsx
│   │   │   └── textarea.tsx
│   │   ├── unified-chat-interface.tsx  # Main chat component (CRITICAL)
│   │   ├── navigation.tsx        # Top nav bar with glass effect
│   │   ├── agent-selector.tsx    # Agent dropdown
│   │   ├── execution-mode-toggle.tsx  # Mock/Real/Stream selector
│   │   └── agent-config-view.tsx # Agent details display
│   │
│   ├── lib/
│   │   ├── services/             # Service Layer (Dependency Injection)
│   │   │   ├── ServiceContext.tsx       # DI container
│   │   │   ├── AgentExecutionService.ts # Execution logic (CRITICAL)
│   │   │   ├── SessionService.ts        # Session management
│   │   │   └── interfaces.ts            # Service interfaces
│   │   ├── api-client.ts         # Singleton API client (CRITICAL)
│   │   ├── types.ts              # TypeScript type definitions
│   │   └── utils.ts              # Helper functions
│   │
│   ├── __tests__/                # 146+ tests, >90% coverage
│   │   ├── lib/
│   │   │   └── services/         # Service tests (50 tests)
│   │   └── components/           # Component tests (96 tests)
│   │
│   └── docs/
│       ├── ARCHITECTURE.md       # System design (v3.0)
│       ├── TUTORIAL.md           # Complete user guide
│       └── UI_FEATURES_UPDATE.md # Latest UI features
│
├── server/                       # FastAPI Backend (v2.0)
│   ├── main.py                   # FastAPI app entrypoint (CRITICAL)
│   ├── models.py                 # Pydantic DTOs
│   ├── auth.py                   # Authentication middleware
│   ├── agent_service.py          # Business logic layer (CRITICAL)
│   ├── .env                      # Environment configuration
│   └── requirements.txt          # Python dependencies
│
├── asdrp/agents/                 # Agent Implementation
│   ├── protocol.py               # AgentProtocol definition (CRITICAL)
│   ├── agent_factory.py          # Factory pattern (CRITICAL)
│   ├── config_loader.py          # YAML configuration loader (CRITICAL)
│   │
│   ├── single/                   # Single-purpose agents
│   │   ├── one_agent.py          # General web search agent
│   │   ├── geo_agent.py          # Geocoding agent
│   │   ├── finance_agent.py      # Financial data agent
│   │   ├── map_agent.py          # Google Maps agent
│   │   ├── yelp_agent.py         # Yelp business search agent
│   │   ├── wiki_agent.py         # Wikipedia knowledge assistant
│   │   └── perplexity_agent.py   # Perplexity AI research assistant
│   │
│   └── orchestration/            # Multi-agent orchestrators
│       └── [orchestrators TBD]
│
├── asdrp/actions/                # Agent Tools & Actions
│   ├── tools_meta.py             # ToolsMeta metaclass
│   ├── geo/                      # Geographic tools
│   │   ├── geo_tools.py          # Geocoding tools
│   │   └── map_tools.py          # Google Maps tools
│   ├── finance/                  # Financial tools
│   │   └── finance_tools.py      # Stock data tools
│   ├── local/                    # Local business tools
│   │   └── yelp_tools.py         # Yelp API tools
│   └── search/                   # Search & knowledge tools
│       ├── wiki_tools.py         # Wikipedia tools
│       └── perplexity_tools.py   # Perplexity AI tools
│
├── config/
│   └── open_agents.yaml          # Agent configuration (CRITICAL)
│
├── docs/                         # Project Documentation
│   ├── AGENT_SYSTEM_GUIDE.md
│   ├── COMPLETE_TUTORIAL.md
│   ├── WEB_SEARCH_IMAGE_HANDLING.md
│   └── [other guides]
│
├── tests/                        # Backend tests
│   ├── server/                   # Server tests (50+ tests)
│   └── asdrp/                    # Agent & tool tests
│
├── README.md                     # Main project README
├── SERVER_UPDATE.md              # Backend features documentation
└── PROJECT_README.md             # Comprehensive overview
```

### Critical Files (Must Understand)

When working with this codebase, these files are essential:

**Backend:**
1. `server/main.py` - FastAPI application, all endpoints
2. `server/agent_service.py` - Agent execution logic
3. `asdrp/agents/protocol.py` - Agent interface definition
4. `asdrp/agents/agent_factory.py` - Agent creation and caching
5. `asdrp/agents/config_loader.py` - YAML configuration loader
6. `config/open_agents.yaml` - Agent definitions

**Frontend:**
1. `frontend_web/app/page.tsx` - Main page with collapsible sidebar
2. `frontend_web/components/unified-chat-interface.tsx` - Chat UI
3. `frontend_web/lib/api-client.ts` - Singleton HTTP client
4. `frontend_web/lib/services/AgentExecutionService.ts` - Execution logic
5. `frontend_web/lib/services/ServiceContext.tsx` - Dependency injection

---

## 🎯 Key Patterns & Principles

### Design Patterns Used

#### 1. **Protocol Pattern** (Backend Agents)
```python
# asdrp/agents/protocol.py
@runtime_checkable
class AgentProtocol(Protocol):
    name: str
    instructions: str
```
- All agents implement this protocol
- Runtime checkable for type safety
- Decouples interface from implementation

#### 2. **Factory Pattern** (Agent Creation)
```python
# asdrp/agents/agent_factory.py
class AgentFactory:
    @classmethod
    def instance(cls) -> "AgentFactory":
        # Singleton pattern

    def get_agent(self, agent_id: str) -> AgentProtocol:
        # Factory method

    async def get_agent_with_session(self, agent_id: str, session_id: str = None):
        # Factory with session management
```

#### 3. **Strategy Pattern** (Execution Modes)
```typescript
// frontend_web/lib/services/AgentExecutionService.ts
export class AgentExecutionService {
  executeMock(agentId: string, request: SimulationRequest): Promise<SimulationResponse>
  executeReal(agentId: string, request: SimulationRequest): Promise<SimulationResponse>
  executeStream(agentId: string, request: SimulationRequest): AsyncGenerator<StreamChunk>
}
```

#### 4. **Singleton Pattern** (API Client)
```typescript
// frontend_web/lib/api-client.ts
let apiClientInstance: ApiClient | null = null;

export function getApiClient(): ApiClient {
  if (!apiClientInstance) {
    apiClientInstance = new ApiClient(config);
  }
  return apiClientInstance;
}
```

#### 5. **Dependency Injection** (Frontend Services)
```typescript
// frontend_web/lib/services/ServiceContext.tsx
export const ServiceProvider: React.FC<Props> = ({ children }) => {
  const apiClient = getApiClient();
  const executionService = new AgentExecutionService(apiClient);
  const sessionService = new SessionService();

  return (
    <ServiceContext.Provider value={{ executionService, sessionService }}>
      {children}
    </ServiceContext.Provider>
  );
};
```

### SOLID Principles

The codebase follows SOLID principles rigorously:

**S - Single Responsibility**
- `AgentService` handles only agent operations
- `AuthService` handles only authentication
- `ApiClient` handles only HTTP communication

**O - Open/Closed**
- Easy to add new agents without modifying factory
- Easy to add new execution modes without changing service

**L - Liskov Substitution**
- All agents implement `AgentProtocol`
- Can be used interchangeably via factory

**I - Interface Segregation**
- Focused interfaces: `IAgentExecutionService`, `ISessionService`
- Components only depend on what they need

**D - Dependency Inversion**
- Services depend on abstractions (interfaces)
- High-level modules don't depend on low-level details

---

## 🔧 Backend System

### FastAPI Application

**Location**: `server/main.py`

#### Key Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health` | GET | Health check | No |
| `/info` | GET | Server info | No |
| `/agents` | GET | List agents | Yes |
| `/agents/{id}` | GET | Agent details | Yes |
| `/agents/{id}/simulate` | POST | Mock execution | Yes |
| `/agents/{id}/chat` | POST | Real execution | Yes |
| `/agents/{id}/chat/stream` | POST | Streaming execution | Yes |
| `/config/agents` | GET | Get config YAML | Yes |
| `/config/agents` | PUT | Update config | Yes |
| `/graph` | GET | Agent graph data | Yes |

#### Authentication

```python
# server/auth.py
async def verify_api_key(x_api_key: str = Header(...)):
    if not AUTH_ENABLED:
        return None

    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401)

    return x_api_key
```

**Environment Variables:**
- `AUTH_ENABLED`: Enable/disable authentication
- `API_KEYS`: Comma-separated list of valid keys
- `JWT_SECRET_KEY`: Secret for JWT tokens (if used)

#### CORS Configuration

```python
# server/main.py
allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Agent Service Layer

**Location**: `server/agent_service.py`

This is the **core business logic** layer between the API and agent system.

#### Key Methods

```python
class AgentService:
    def list_agents(self) -> List[AgentListItem]
    def get_agent_detail(self, agent_id: str) -> AgentDetail

    async def simulate_agent(self, agent_id: str, request: SimulationRequest) -> SimulationResponse
    async def chat_agent(self, agent_id: str, request: SimulationRequest) -> SimulationResponse
    async def chat_agent_streaming(self, agent_id: str, request: SimulationRequest) -> AsyncGenerator[StreamChunk]

    def get_agent_graph(self) -> AgentGraph
    def validate_config(self, yaml_content: str) -> tuple[bool, Optional[str]]
```

#### Execution Flow

**Mock Mode** (No API calls):
```python
async def simulate_agent(self, agent_id: str, request: SimulationRequest):
    # 1. Validate agent exists
    agent, session = await self._factory.get_agent_with_session(agent_id)

    # 2. Generate mock response
    response_text = f"[MOCK RESPONSE from {agent.name}]..."

    # 3. Return without OpenAI call
    return SimulationResponse(response=response_text, ...)
```

**Real Mode** (Complete response):
```python
async def chat_agent(self, agent_id: str, request: SimulationRequest):
    # 1. Get agent with session
    agent, session = await self._factory.get_agent_with_session(agent_id)

    # 2. Execute with Runner
    run_result = await Runner.run(
        starting_agent=agent,
        input=request.input,
        session=session
    )

    # 3. Extract response
    return SimulationResponse(
        response=str(run_result.final_output),
        metadata={'usage': run_result.usage, ...}
    )
```

**Stream Mode** (Real-time tokens):
```python
async def chat_agent_streaming(self, agent_id: str, request: SimulationRequest):
    # 1. Get agent
    agent, session = await self._factory.get_agent_with_session(agent_id)

    # 2. Send metadata
    yield StreamChunk(type="metadata", metadata={...})

    # 3. Stream tokens
    async for chunk in Runner.run_streamed(agent, input=..., session=session):
        if hasattr(chunk, 'content'):
            yield StreamChunk(type="token", content=str(chunk.content))

    # 4. Send done
    yield StreamChunk(type="done")
```

### Data Models

**Location**: `server/models.py`

```python
# Request Models
class SimulationRequest(BaseModel):
    input: str
    session_id: Optional[str] = None
    context: Dict[str, Any] = {}
    max_steps: int = 5

# Response Models
class SimulationResponse(BaseModel):
    response: str
    trace: List[SimulationStep]
    metadata: Dict[str, Any]

class StreamChunk(BaseModel):
    type: Literal["metadata", "token", "step", "done", "error"]
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Agent Models
class AgentListItem(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    enabled: bool

class AgentDetail(AgentListItem):
    module: str
    function: str
    model_name: str
    temperature: float
    max_tokens: int
    tools: List[str]
    edges: List[str]
    session_memory_enabled: bool
```

---

## 🎨 Frontend System

### Next.js 14 App Router

**Location**: `frontend_web/app/`

#### Route Structure

```
app/
├── layout.tsx              # Root layout with ServiceProvider
├── page.tsx                # Main: Agent Execution (/)
├── config-editor/
│   └── page.tsx            # Config Editor (/config-editor)
├── help/
│   └── page.tsx            # Help Page (/help)
└── globals.css             # Global styles (glass morphism)
```

#### Main Page Layout

**File**: `frontend_web/app/page.tsx`

```typescript
export default function SimulationPage() {
  // State
  const [selectedAgent, setSelectedAgent] = useState("one");  // Default: OneAgent
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("real");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);  // Collapsed by default

  // Layout: Collapsible sidebar (left) + Chat interface (right)
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left: Configuration Panel (collapsible) */}
      {!sidebarCollapsed && (
        <div className="lg:col-span-1">
          {/* Unified glass panel with Agent Selector, Execution Mode, Agent Details */}
        </div>
      )}

      {/* Collapsed: Floating expand button */}
      {sidebarCollapsed && (
        <div className="fixed left-4 top-1/2 -translate-y-1/2 z-50">
          <Button onClick={() => setSidebarCollapsed(false)}>
            <ChevronRight />
          </Button>
        </div>
      )}

      {/* Right: Chat Interface */}
      <div className={sidebarCollapsed ? "lg:col-span-3 pl-20" : "lg:col-span-2"}>
        <UnifiedChatInterface agentId={selectedAgent} mode={executionMode} />
      </div>
    </div>
  );
}
```

### Service Layer (Dependency Injection)

**Location**: `frontend_web/lib/services/`

#### Service Context

**File**: `ServiceContext.tsx`

```typescript
interface ServiceContextType {
  executionService: IAgentExecutionService;
  sessionService: ISessionService;
}

export const ServiceProvider: React.FC<Props> = ({ children }) => {
  const apiClient = useMemo(() => getApiClient(), []);
  const executionService = useMemo(() => new AgentExecutionService(apiClient), [apiClient]);
  const sessionService = useMemo(() => new SessionService(), []);

  const value = useMemo(() => ({
    executionService,
    sessionService,
  }), [executionService, sessionService]);

  return (
    <ServiceContext.Provider value={value}>
      {children}
    </ServiceContext.Provider>
  );
};

// Hooks for consuming services
export const useExecutionService = (): IAgentExecutionService => { ... }
export const useSessionService = (): ISessionService => { ... }
```

#### Agent Execution Service

**File**: `AgentExecutionService.ts`

```typescript
export class AgentExecutionService implements IAgentExecutionService {
  constructor(private apiClient: ApiClient) {}

  // Enhance request with markdown formatting instruction
  private enhanceRequestWithMarkdown(request: SimulationRequest): SimulationRequest {
    const wordCount = request.input.trim().split(/\s+/).length;
    if (wordCount > 50 || /\b(explain|describe)\b/i.test(request.input)) {
      return {
        ...request,
        input: `${request.input}\n\nPlease format your response in structured rich text Markdown format.`,
      };
    }
    return request;
  }

  async executeMock(agentId: string, request: SimulationRequest): Promise<SimulationResponse> {
    const enhanced = this.enhanceRequestWithMarkdown(request);
    return this.apiClient.simulateAgent(agentId, enhanced);
  }

  async executeReal(agentId: string, request: SimulationRequest): Promise<SimulationResponse> {
    const enhanced = this.enhanceRequestWithMarkdown(request);
    return this.apiClient.chatAgent(agentId, enhanced);
  }

  async *executeStream(agentId: string, request: SimulationRequest): AsyncGenerator<StreamChunk> {
    const enhanced = this.enhanceRequestWithMarkdown(request);
    yield* this.apiClient.chatAgentStream(agentId, enhanced);
  }
}
```

#### Session Service

**File**: `SessionService.ts`

```typescript
export class SessionService implements ISessionService {
  private sessions: Map<string, string> = new Map();

  getSessionId(agentId: string): string {
    if (!this.sessions.has(agentId)) {
      this.sessions.set(agentId, this.generateSessionId());
    }
    return this.sessions.get(agentId)!;
  }

  clearSession(agentId: string): void {
    this.sessions.delete(agentId);
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### API Client (Singleton)

**File**: `frontend_web/lib/api-client.ts`

```typescript
export class ApiClient {
  constructor(private config: ApiConfig) {}

  // Agent discovery
  async listAgents(): Promise<AgentListItem[]> { ... }
  async getAgentDetail(agentId: string): Promise<AgentDetail> { ... }

  // Execution methods
  async simulateAgent(agentId: string, request: SimulationRequest): Promise<SimulationResponse> {
    return this.post(`/agents/${agentId}/simulate`, request);
  }

  async chatAgent(agentId: string, request: SimulationRequest): Promise<SimulationResponse> {
    return this.post(`/agents/${agentId}/chat`, request);
  }

  async *chatAgentStream(agentId: string, request: SimulationRequest): AsyncGenerator<StreamChunk> {
    const response = await fetch(`${this.baseUrl}/agents/${agentId}/chat/stream`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = JSON.parse(line.slice(6));
          yield data as StreamChunk;
        }
      }
    }
  }
}

// Singleton instance
let apiClientInstance: ApiClient | null = null;

export function getApiClient(): ApiClient {
  if (!apiClientInstance) {
    apiClientInstance = new ApiClient({
      baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
      apiKey: process.env.NEXT_PUBLIC_API_KEY || "",
    });
  }
  return apiClientInstance;
}
```

### Unified Chat Interface

**File**: `frontend_web/components/unified-chat-interface.tsx`

This is the **most critical frontend component**.

#### Key Features

1. **Three execution modes** in single component
2. **Smart auto-scrolling** (only on agent responses)
3. **Markdown rendering** with image validation
4. **Real-time streaming** support
5. **Session management** integration

#### Component Structure

```typescript
export function UnifiedChatInterface({
  agentId,
  mode,
  useSession = true,
}: UnifiedChatInterfaceProps) {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [isUserScrolling, setIsUserScrolling] = useState(false);

  // Services (via hooks)
  const executionService = useExecutionService();
  const sessionService = useSessionService();

  // Smart auto-scroll (only on agent messages)
  useEffect(() => {
    const isAgentMessage = messages[messages.length - 1]?.role === "agent" || streaming;
    if (isAgentMessage && !isUserScrolling) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streaming, isUserScrolling]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const sessionId = useSession ? sessionService.getSessionId(agentId) : undefined;

    if (mode === "stream") {
      await handleStreamExecution(input, sessionId);
    } else {
      await handleNonStreamExecution(input, sessionId);
    }
  };

  // Streaming handler
  const handleStreamExecution = async (userInput: string, sessionId?: string) => {
    setStreaming(true);
    let streamedContent = "";

    // Create placeholder message
    setMessages(prev => [...prev, { role: "agent", content: "", timestamp: new Date() }]);

    // Stream tokens
    const stream = executionService.executeStream(agentId, { input: userInput, session_id: sessionId });

    for await (const chunk of stream) {
      if (chunk.type === "token" && chunk.content) {
        streamedContent += chunk.content;
        // Update message in real-time
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1].content = streamedContent;
          return updated;
        });
      }
    }

    setStreaming(false);
  };

  // Layout: Header + Messages + Input (always visible)
  return (
    <div className="flex flex-col h-full">
      {/* Header - Fixed */}
      <div className="flex-none">...</div>

      {/* Messages Area - Flexible */}
      <div className="flex-1 relative overflow-hidden">
        <div className="custom-scrollbar absolute inset-0 overflow-y-auto" onScroll={handleScroll}>
          {messages.map((message, index) => (
            <div key={index}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw, rehypeSanitize]}
                components={{
                  // Image validation
                  img: ({ node, ...props }) => {
                    const [imageError, setImageError] = useState(false);
                    if (imageError || !props.src) return null;
                    return <img {...props} onError={() => setImageError(true)} />;
                  },
                  // ... other components
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ))}
        </div>
      </div>

      {/* Input Area - Fixed at bottom */}
      <div className="flex-none">
        <form onSubmit={handleSubmit}>
          <Textarea value={input} onChange={(e) => setInput(e.target.value)} />
          <button type="submit" disabled={loading || streaming}>
            {loading || streaming ? <Loader2 className="animate-spin" /> : <Send />}
          </button>
        </form>
      </div>
    </div>
  );
}
```

### Glass Morphism Design

**File**: `frontend_web/app/globals.css`

```css
.glass-panel {
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(20px);
  background: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.1) 100%);
  border: 1px solid rgba(255,255,255,0.5);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-panel:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
}

.message-bubble {
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 4px;
}
```

---

## 🤖 Agent System

### Agent Protocol

**File**: `asdrp/agents/protocol.py`

```python
@runtime_checkable
class AgentProtocol(Protocol):
    """Interface that all agents must implement."""
    name: str
    instructions: str
```

All agents must have:
- `name`: Identifier for the agent
- `instructions`: System instructions (prompt)

The protocol uses OpenAI's `agents.Agent` class under the hood.

### Agent Factory

**File**: `asdrp/agents/agent_factory.py`

```python
class AgentFactory:
    """
    Factory for creating and managing agent instances.

    Features:
    - Singleton pattern for global access
    - Agent caching for performance
    - Session memory integration
    - Configuration-driven creation
    """

    _instance: Optional["AgentFactory"] = None
    _agent_cache: Dict[str, AgentProtocol] = {}
    _session_cache: Dict[str, Any] = {}

    @classmethod
    def instance(cls) -> "AgentFactory":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_agent(self, agent_id: str) -> AgentProtocol:
        """
        Get or create agent by ID.

        Flow:
        1. Check cache
        2. Load config from YAML
        3. Import module dynamically
        4. Call creation function
        5. Cache and return
        """
        if agent_id in self._agent_cache:
            return self._agent_cache[agent_id]

        # Load configuration
        config = self._config_loader.get_agent_config(agent_id)

        # Dynamic import
        module = importlib.import_module(config.module)
        create_func = getattr(module, config.function)

        # Create agent
        agent = create_func(
            instructions=config.default_instructions,
            model_config=config.model
        )

        # Cache and return
        self._agent_cache[agent_id] = agent
        return agent

    async def get_agent_with_session(
        self,
        agent_id: str,
        session_id: Optional[str] = None
    ) -> Tuple[AgentProtocol, Optional[Any]]:
        """
        Get agent with session memory.

        Returns:
            Tuple of (agent, session) where session may be None if disabled
        """
        agent = self.get_agent(agent_id)
        config = self._config_loader.get_agent_config(agent_id)

        if not config.session_memory.enabled:
            return (agent, None)

        # Create or retrieve session
        session_key = session_id or f"session_{agent_id}"

        if session_key not in self._session_cache:
            from agents import SessionConfig, SqliteSessionStore

            session_store = SqliteSessionStore(
                database_path=config.session_memory.database_path
            )

            session = SessionConfig(
                session_id=session_key,
                store=session_store
            )

            self._session_cache[session_key] = session

        return (agent, self._session_cache[session_key])
```

### Configuration Loader

**File**: `asdrp/agents/config_loader.py`

```python
class AgentConfigLoader:
    """
    Loads and validates agent configuration from YAML.

    Features:
    - YAML parsing and validation
    - Pydantic models for type safety
    - Default value inheritance
    - Configuration caching
    """

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self._config_cache: Optional[Dict] = None
        self.load_config()

    def load_config(self) -> Dict:
        """Load and parse YAML configuration."""
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate structure
        if not isinstance(config, dict) or "agents" not in config:
            raise ConfigException("Invalid config: missing 'agents' key")

        self._config_cache = config
        return config

    def get_agent_config(self, agent_id: str) -> AgentConfig:
        """
        Get configuration for specific agent.

        Returns:
            AgentConfig with all settings, including defaults
        """
        if self._config_cache is None:
            self.load_config()

        agents = self._config_cache["agents"]

        if agent_id not in agents:
            raise AgentException(f"Agent '{agent_id}' not found", agent_name=agent_id)

        agent_dict = agents[agent_id]

        # Merge with defaults
        defaults = self._config_cache.get("defaults", {})
        merged_config = self._merge_with_defaults(agent_dict, defaults)

        # Parse into Pydantic model
        return AgentConfig(**merged_config)

    def list_agents(self) -> List[str]:
        """List all available agent IDs."""
        if self._config_cache is None:
            self.load_config()

        return [
            agent_id
            for agent_id, config in self._config_cache["agents"].items()
            if config.get("enabled", True)
        ]
```

### Agent Configuration Model

```python
class ModelConfig(BaseModel):
    name: str = "gpt-4.1-mini"
    temperature: float = 0.7
    max_tokens: int = 2000

class SessionMemoryConfig(BaseModel):
    type: Literal["sqlite", "none"] = "sqlite"
    session_id: Optional[str] = None
    database_path: Optional[str] = None
    enabled: bool = True

class AgentConfig(BaseModel):
    display_name: str
    module: str
    function: str
    default_instructions: str
    model: ModelConfig
    session_memory: SessionMemoryConfig
    enabled: bool = True

    # Optional fields
    type: Optional[str] = "single"
    tools: List[str] = []
    edges: List[str] = []
```

### Example Agent Implementation

**File**: `asdrp/agents/single/one_agent.py`

```python
from agents import Agent, WebSearchTool, ModelSettings

DEFAULT_INSTRUCTIONS = """You are a useful agent...
IMAGE HANDLING:
- DO NOT use markdown image syntax (![alt](url))
- Provide clickable links: [View image](url)
"""

def create_one_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """Factory function for creating OneAgent."""

    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS

    agent_kwargs: Dict[str, Any] = {
        "name": "OneAgent",
        "instructions": instructions,
        "tools": [WebSearchTool()],
    }

    if model_config:
        agent_kwargs["model"] = model_config.name
        agent_kwargs["model_settings"] = ModelSettings(
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )

    return Agent[Any](**agent_kwargs)
```

### Tools and Actions

**Location**: `asdrp/actions/`

Tools are organized by domain:

**Geographic Tools** (`geo/`):
- `geo_tools.py`: Geocoding (address ↔ coordinates)
- `map_tools.py`: Google Maps (places, directions, distances)

**Financial Tools** (`finance/`):
- `finance_tools.py`: Stock data, historical prices, company info

**Local Business Tools** (`local/`):
- `yelp_tools.py`: Business search, reviews, ratings

**Search & Knowledge Tools** (`search/`):
- `wiki_tools.py`: Wikipedia search, page content, summaries, sections, images, links

**Tool Pattern**:
```python
from asdrp.actions.tools_meta import ToolsMeta

class GeoTools(metaclass=ToolsMeta):
    """Geographic tools for geocoding."""

    @staticmethod
    def get_coordinates_by_address(address: str) -> dict:
        """Convert address to coordinates.

        Args:
            address: Full address to geocode

        Returns:
            {"latitude": float, "longitude": float, "formatted_address": str}
        """
        # Implementation using Google Maps API
        ...
```

The `ToolsMeta` metaclass automatically converts methods into OpenAI function tools.

---

## ⚙️ Configuration

### Backend Configuration

**File**: `server/.env`

```bash
# Authentication
AUTH_ENABLED=true
API_KEYS=your_secure_api_key_here
JWT_SECRET_KEY=your_jwt_secret_here

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=false  # Set to true for development
LOG_LEVEL=info

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Security
TRUSTED_HOSTS=localhost,127.0.0.1,yourdomain.com
ENABLE_DOCS=true  # Set to false in production

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
```

### Frontend Configuration

**File**: `frontend_web/.env.local`

```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your_api_key_here
```

### Agent Configuration

**File**: `config/open_agents.yaml`

```yaml
agents:
  one:
    display_name: "OneAgent"
    module: "asdrp.agents.single.one_agent"
    function: "create_one_agent"
    default_instructions: |
      You are a useful agent with web search capabilities.

      IMAGE HANDLING:
      - DO NOT use markdown image syntax (![alt](url))
      - Provide clickable links: [View image](url)
    model:
      name: "gpt-4.1-mini"
      temperature: 0.8
      max_tokens: 2000
    session_memory:
      type: "none"
      enabled: false
    enabled: true

defaults:
  model:
    name: "gpt-4.1-mini"
    temperature: 0.7
    max_tokens: 2000
  session_memory:
    type: "sqlite"
    session_id: null
    database_path: null
    enabled: true
```

### External API Keys

**Required APIs:**
- OpenAI API (required for all agents)
- Google Maps API (for geo and map agents)
- Yelp API (for yelp agent)

**Configure in**:
- Backend: `server/.env` → `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, `YELP_API_KEY`
- Or use environment variables directly

---

## 🧪 Testing

### Frontend Tests

**Location**: `frontend_web/__tests__/`

**Run tests**:
```bash
cd frontend_web
npm test                # Run all tests
npm run test:watch      # Watch mode
npm run test:coverage   # Coverage report
```

**Test Structure**:
```
__tests__/
├── lib/
│   ├── api-client.test.ts              # API client tests
│   ├── utils.test.ts                   # Utility function tests
│   └── services/
│       ├── AgentExecutionService.test.ts  # 25 tests
│       └── SessionService.test.ts         # 25 tests
└── components/
    ├── unified-chat-interface.test.tsx    # 48 tests
    ├── agent-selector.test.tsx            # 24 tests
    └── execution-mode-toggle.test.tsx     # 24 tests
```

**Test Statistics**:
- Total: 146+ tests
- Coverage: >90%
- All passing ✅

**Example Test**:
```typescript
describe('AgentExecutionService', () => {
  it('should enhance request with markdown for long inputs', async () => {
    const service = new AgentExecutionService(mockApiClient);
    const longInput = "a ".repeat(60); // >50 words

    await service.executeReal("test", { input: longInput });

    expect(mockApiClient.chatAgent).toHaveBeenCalledWith(
      "test",
      expect.objectContaining({
        input: expect.stringContaining("Markdown format")
      })
    );
  });
});
```

### Backend Tests

**Location**: `tests/`

**Run tests**:
```bash
cd server
pytest                       # Run all tests
pytest --cov=server          # With coverage
pytest -v                    # Verbose output
```

**Test Structure**:
```
tests/
├── server/
│   ├── test_models.py              # Pydantic model tests
│   ├── test_auth.py                # Authentication tests
│   ├── test_agent_service.py       # Service layer tests
│   └── test_agent_endpoints.py     # API endpoint tests
└── asdrp/
    ├── agents/
    │   ├── test_protocol.py
    │   ├── test_agent_factory.py
    │   ├── test_config_loader.py
    │   └── single/
    │       ├── test_one_agent.py
    │       ├── test_geo_agent.py
    │       └── ...
    └── actions/
        ├── test_tools_meta.py
        └── [tool tests]
```

**Test Statistics**:
- Total: 50+ tests
- Coverage: >90%
- All passing ✅

---

## 🔨 Common Tasks

### Adding a New Agent

1. **Create agent module**:
```python
# asdrp/agents/single/my_agent.py
from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig

def create_my_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    from agents import Agent

    return Agent(
        name="MyAgent",
        instructions=instructions or "Default instructions",
        tools=[],  # Add tools here
    )
```

2. **Add to configuration**:
```yaml
# config/open_agents.yaml
agents:
  my_agent:
    display_name: "My Agent"
    module: "asdrp.agents.single.my_agent"
    function: "create_my_agent"
    default_instructions: "You are my custom agent..."
    model:
      name: "gpt-4.1-mini"
      temperature: 0.7
      max_tokens: 2000
    session_memory:
      type: "sqlite"
      enabled: true
    enabled: true
```

3. **Restart backend**:
```bash
cd server
python -m server.main
```

4. **Test in frontend**: Agent will appear in dropdown automatically

### Modifying Agent Instructions

1. **Edit YAML configuration**:
```yaml
# config/open_agents.yaml
agents:
  one:
    default_instructions: |
      Updated instructions here...
```

2. **Restart backend** (config is loaded at startup)

3. **Test**: New instructions take effect immediately

### Adding a New Tool

1. **Create tool class**:
```python
# asdrp/actions/my_domain/my_tools.py
from asdrp.actions.tools_meta import ToolsMeta

class MyTools(metaclass=ToolsMeta):
    @staticmethod
    def my_function(param: str) -> dict:
        """Tool description for LLM.

        Args:
            param: Parameter description

        Returns:
            Result dictionary
        """
        # Implementation
        return {"result": "value"}
```

2. **Use in agent**:
```python
# asdrp/agents/single/my_agent.py
from asdrp.actions.my_domain.my_tools import MyTools

def create_my_agent(...):
    return Agent(
        name="MyAgent",
        instructions=...,
        tools=MyTools.to_openai_tools(),  # Convert to OpenAI tools
    )
```

### Modifying UI Styles

**Global styles**: Edit `frontend_web/app/globals.css`

**Component styles**: Modify Tailwind classes in component files

**Glass effect**: Already defined in `.glass-panel` class

**Example - Change glass opacity**:
```css
/* frontend_web/app/globals.css */
.glass-panel::before {
  background: linear-gradient(135deg,
    rgba(255,255,255,0.5) 0%,    /* Increase from 0.4 */
    rgba(255,255,255,0.2) 100%   /* Increase from 0.1 */
  );
}
```

### Debugging Streaming Issues

1. **Check browser console** for SSE errors
2. **Verify backend logs** for streaming output
3. **Test endpoint directly**:
```bash
curl -N -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}' \
  http://localhost:8000/agents/one/chat/stream
```

4. **Common issues**:
   - CORS blocking SSE connections
   - Frontend not handling SSE format correctly
   - Backend not yielding chunks properly

---

## ⚠️ Important Constraints

### WebSearchTool Limitations

**CRITICAL**: OpenAI's `WebSearchTool` returns **text only**, not images.

**Why this matters**:
- LLM may hallucinate image markdown: `![description](fake-url)`
- These images will not load (broken placeholders)

**Solutions implemented**:
1. **Agent instructions** explicitly prohibit image markdown
2. **Frontend validation** hides broken images gracefully
3. **Smart prompting** requests markdown format for text content

**Documentation**: See `docs/WEB_SEARCH_IMAGE_HANDLING.md`

### Session Memory

**In-memory sessions** (default):
- Fast, no disk I/O
- Lost on server restart
- Good for development

**File-based sessions**:
- Persistent across restarts
- Requires disk space
- Good for production

**Configure per agent** in `config/open_agents.yaml`:
```yaml
session_memory:
  type: "sqlite"               # or "none"
  database_path: null          # null = in-memory, path = file-based
  enabled: true                # Enable/disable session memory
```

### API Rate Limits

**OpenAI API**:
- Rate limits depend on your tier
- Streaming uses same quota as non-streaming
- Monitor usage in metadata: `response.metadata.usage.total_tokens`

**Google Maps API**:
- Free tier: 2,500 requests/day
- Paid tier: $5/1000 requests beyond free tier

**Yelp API**:
- Free: 500 calls/day
- Rate limited to 5 calls/second

### Frontend Build Size

**Target**: <100 kB per route

**Current**:
- Main route: ~95 kB ✅
- Config editor: ~98 kB ✅
- Help page: ~92 kB ✅

**Maintain small bundles**:
- Use dynamic imports for heavy components
- Avoid large dependencies
- Monitor with `npm run build`

### Security Considerations

**Always enable in production**:
- `AUTH_ENABLED=true`
- `ENABLE_DOCS=false` (disable Swagger docs)
- HTTPS only
- Rotate API keys regularly

**CORS**:
- Set `CORS_ORIGINS` to specific domains
- Never use wildcard `*` in production

**Input validation**:
- Backend validates all inputs with Pydantic
- Frontend sanitizes markdown with `rehype-sanitize`

---

## 🐛 Troubleshooting

### Backend Won't Start

**Issue**: Import errors or module not found

**Solution**:
```bash
cd server
source .venv/bin/activate  # Activate venv
pip install -e .           # Reinstall in editable mode
python -m server.main      # Run from project root
```

**Check**:
- Python version: 3.11+
- Virtual environment activated
- Project root in `sys.path`

### Frontend Build Fails

**Issue**: Module not found or type errors

**Solution**:
```bash
cd frontend_web
rm -rf node_modules .next  # Clean build artifacts
npm install --legacy-peer-deps
npm run dev
```

**Check**:
- Node version: 18+
- TypeScript errors: `npm run type-check`
- Missing dependencies: Check `package.json`

### Agent Not Appearing in Dropdown

**Check**:
1. Agent enabled in YAML: `enabled: true`
2. Module path correct: `asdrp.agents.single.agent_name`
3. Function name matches: `create_agent_name`
4. Backend restarted after config change
5. Backend logs for errors during agent loading

### Streaming Not Working

**Symptoms**: No real-time updates, waits for complete response

**Check**:
1. **Backend**: Endpoint using `async for` and yielding chunks
2. **Frontend**: Using `chatAgentStream` method (not `chatAgent`)
3. **Browser**: DevTools → Network → Check for SSE connection
4. **CORS**: Ensure streaming is allowed in CORS config

**Debug**:
```typescript
// Frontend: Log chunks
for await (const chunk of stream) {
  console.log('Chunk:', chunk);  // Should see individual tokens
}
```

### Session Memory Not Working

**Symptoms**: Agent doesn't remember previous messages

**Check**:
1. `session_memory.enabled: true` in config
2. `useSession={true}` in `UnifiedChatInterface`
3. Session ID consistent across requests
4. Backend logs for session creation

**Debug**:
```python
# Backend: Log session usage
print(f"Using session: {session}")
print(f"Session ID: {session.session_id if session else 'None'}")
```

### High Token Usage

**Check**:
1. Session memory accumulating too much history
2. Long system instructions
3. Tools returning large responses
4. `max_tokens` set too high

**Optimize**:
- Clear sessions periodically: `sessionService.clearSession(agentId)`
- Reduce `max_tokens` in config
- Trim tool responses
- Use session memory strategically (not for all agents)

### Glass Effect Not Showing

**Check**:
1. `globals.css` imported in `layout.tsx`
2. Browser supports `backdrop-filter` (Safari, Chrome, Edge)
3. Elements have `.glass-panel` class
4. Not inside opaque parent (backdrop-filter needs transparency)

**Test**:
```html
<div className="glass-panel p-4 border border-white/50">
  Glass effect test
</div>
```

---

## 📚 Additional Resources

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project README |
| `SERVER_UPDATE.md` | Backend features, streaming |
| `frontend_web/docs/ARCHITECTURE.md` | Frontend architecture (v3.0) |
| `frontend_web/docs/TUTORIAL.md` | Complete user guide |
| `frontend_web/docs/UI_FEATURES_UPDATE.md` | Latest UI features |
| `docs/WEB_SEARCH_IMAGE_HANDLING.md` | Image limitations & solutions |
| `docs/AGENT_SYSTEM_GUIDE.md` | Agent development guide |
| `docs/COMPLETE_TUTORIAL.md` | End-to-end tutorial |

### External Links

- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [shadcn/ui Components](https://ui.shadcn.com/)

---

## 🎯 Quick Reference

### Command Cheatsheet

```bash
# Backend
cd server
python -m server.main                 # Start server
pytest                                # Run tests
pytest --cov=server                   # Coverage report

# Frontend
cd frontend_web
npm run dev                           # Start dev server
npm run build                         # Production build
npm test                              # Run tests
npm run type-check                    # TypeScript check

# Full Stack
docker-compose up                     # Start both (Docker)
```

### Key URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### Environment Variables Quick Reference

**Backend** (`.env`):
- `AUTH_ENABLED`: Enable authentication
- `API_KEYS`: Comma-separated API keys
- `CORS_ORIGINS`: Allowed origins
- `OPENAI_API_KEY`: OpenAI API key

**Frontend** (`.env.local`):
- `NEXT_PUBLIC_API_BASE_URL`: Backend URL
- `NEXT_PUBLIC_API_KEY`: API key for backend

---

## 🔄 Version History

- **v3.0** (Nov 2025): Glass morphism UI, markdown rendering, smart scrolling
- **v2.0** (Oct 2025): Service layer, dependency injection, streaming
- **v1.0** (Sep 2025): Initial release

---

**This guide is maintained for AI assistants to quickly understand and work with the OpenAgents codebase. Last updated: November 30, 2025**
