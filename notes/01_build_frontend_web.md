You are Claude Code, an expert full-stack engineer.

Your task: **Design and implement a Next.js frontend plus a backend in a top-level `server` package** for a multi-agent orchestration system driven by a YAML config file at `config/open_agents.yaml`.

---

## Overall goals

- Build a **Next.js app** with a modern, clean UI and:
  - A top navigation bar
  - **4 main subpages**:
    1. Agent Simulation
    2. Agent Config Editor (with ReactFlow graph)
    3. Help / Docs
    4. Login with Google OAuth or Github OAuth

- Build a **backend in a top-level `server` package** that:
  - Loads and validates `config/open_agents.yaml`
  - Exposes the agents and their relationships via API
  - Provides endpoints to simulate agents / run multi-agent workflows
  - Is structured to support a multi-agent system orchestrated via a graph of specialized agents
  - Has unit and functional tests at the toplevel `tests` folder
  - Has extensive structured documentations in the toplevel `docs` folder

Assume:
- Frontend: Next.js (latest, App Router), TypeScript, React 18
- Styling: Tailwind CSS + a small reusable components library (e.g. shadcn-style design system) for buttons, cards, tabs, etc.
- Graph UI: [`reactflow`](https://www.npmjs.com/package/reactflow)
- YAML parsing: any reasonable JS/TS YAML library (e.g. `js-yaml`)
- Backend: Python 3.11+ using FastAPI (or similar) in a top-level `server` package.
- Secrets are stored in ".env" file at the toplevel

Structure the repo as something like:

- `frontend_web/` – Next.js app
- `server/` – Python backend package
- `asdrp/` - agents, actions, tools and configuration classes and functions
- `config/open_agents.yaml` – shared agent config file

Feel free to adjust exact paths if needed, but **honor that the backend package name is `server`** and the YAML is in `config/open_agents.yaml`.

---

## frontend_web requirements (Next.js app)

### 1. Global layout & styling

- Use **Next.js App Router** (`app/` directory) with TypeScript.
- Configure **Tailwind CSS** for modern, responsive styling.
- Create a shared layout with:
  - A **top navigation bar** that is **easy to navigate** with links to:
    - “Agent Simulation”
    - “Config Editor”
    - “Help”
  - The navbar should:
    - Highlight the current page
    - Collapse nicely on small screens (hamburger or similar)
- Use a consistent color palette, spacing, and typography for a modern dashboard feel.
- Provide a simple light theme with good contrast.

### 2. Page (1): Agent Simulation page

Route: `/` or `/simulate` (your choice, but it should be linked as “Agent Simulation” in the navbar).

Functionality:

- **Layout**: 
  - Left panel: agent selection + read-only configuration view.
  - Right panel: Q&A / simulation interaction area.

- **Left panel features**:
  - Fetch the list of agents from the backend (e.g. `GET /api/agents`).
  - Display a **select dropdown or list** of available agents (e.g. by agent name/id).
  - When an agent is selected:
    - Show its configuration details loaded from the YAML via backend:
      - Name / ID
      - Description
      - Type / role
      - Tools / capabilities
      - Connections to other agents (if present)
    - This should be shown in a readable, structured format (cards/accordions, not raw YAML).

- **Right panel features**:
  - A Q&A / simulation console:
    - Text input where user can type a prompt or question.
    - “Run” / “Send” button to send the query to a simulation endpoint (e.g. `POST /api/agents/{agent_id}/simulate`).
    - Scrollable conversation log showing:
      - User messages
      - Agent responses
      - Optional metadata like which sub-agents were invoked (if available from backend).
  - Show a loading state for in-progress simulations.

- Use reusable components for panels and cards so the UI feels cohesive.

### 3. Page (2): Config Editor & ReactFlow view

Route: `/config-editor`

This page has **two main features**:

1. **YAML Config Editor**
2. **ReactFlow graph view** of the agents

#### 3.1 YAML Config Editor

- Fetch the current `open_agents.yaml` config via backend (e.g. `GET /api/config/agents`).
- Editor requirements:
  - Use a code editor component (e.g. `@monaco-editor/react` or a reasonable alternative) OR a custom collapsible tree UI; the key requirement is:
    - **Allow collapsing & expansion of different YAML sections** (e.g. per top-level agent, or per main section).
  - Provide basic **validation feedback**:
    - If YAML parse fails, show error message.
    - Disable save until valid.
  - Provide **Save / Apply Changes** button:
    - On click, send `PUT /api/config/agents` or similar to update the YAML.
    - Show success / error toast.

- UX suggestions:
  - Split layout: left for editor, right for preview/validation messages (or stacked on small screens).
  - Show a small summary (e.g. “X agents loaded”) above or below the editor.

#### 3.2 ReactFlow graph view

- Below or beside the editor, add a **ReactFlow graph** representing the agents and their relationships.
- Logic:
  - Parse the YAML to identify agents and connections (e.g. edges based on fields like `next_agents`, `children`, or `routes`; pick a schema and document it in comments).
  - Convert agents into ReactFlow **nodes**, and connections into **edges**.
  - Use ReactFlow features:
    - Zoom, pan
    - Draggable nodes
    - Fit-view button
  - When a user **clicks on a node**:
    - Highlight the node
    - Show details for that agent in a side panel (name, description, parameters).
  - Keep the graph in sync with the YAML editor:
    - When YAML content is changed and valid, recompute nodes/edges.
    - For now, you can update graph when user clicks “Refresh Graph” or after a debounce; pick a simple, robust approach.

- Style nodes to be visually clean:
  - Node label = agent name
  - Optional tag for agent type (e.g. “router”, “tool-caller”, etc.)

### 4. Page (3): Help page

Route: `/help`

Content:

- A clean, readable page explaining:
  - What the app is for:
    - Managing and simulating a **multi-agent system** defined in `config/open_agents.yaml`
    - Visualizing the **agent graph** and their orchestration.
  - Overview of main pages and what each does.
  - Libraries and tech used:
    - Next.js
    - React
    - Tailwind CSS
    - ReactFlow
    - YAML parser
    - Backend framework (FastAPI)
  - Links (can be placeholders but should be present as clearly marked):
    - Architecture doc (e.g. `/docs/architecture` or external link placeholder)
    - README
    - Design docs
  - Brief description of the **multi-agent graph concept**:
    - Agents as nodes
    - Edges representing routing, delegation, or data flow
- Use headings, bullet lists, and maybe small info cards for clarity.

---

## Backend requirements (`server` package)

Implement a Python backend (preferably FastAPI) in a top-level `server` package.

### 1. Package structure

An example structure (you can refine):

- `server/__init__.py`
- `server/main.py` – FastAPI app entrypoint
- `server/config_loader.py` – utilities to load/validate `config/open_agents.yaml`
- `server/models.py` – Pydantic models: Agent, AgentGraph, etc.
- `server/agent_graph.py` – logic for multi-agent graph orchestration
- `server/simulation.py` – core simulation/execution logic for agents
- `config/open_agents.yaml` – YAML config file

Expose the FastAPI app so it can be run with `uvicorn server.main:app` or similar.

### 2. YAML config loading & models

- Provide a function to:
  - Load `config/open_agents.yaml`
  - Parse YAML into Python data structures
  - Map them into Pydantic models (`Agent`, `AgentConnection`, `AgentGraph` etc.).
- Example fields for an `Agent` model (adjust to taste):
  - `id: str`
  - `name: str`
  - `description: Optional[str]`
  - `type: str`  (e.g. “router”, “worker”, “tool-caller”)
  - `params: Dict[str, Any]`
  - `edges: List[str]` (IDs of downstream agents or similar)
- Provide helper functions to:
  - Return a list of all agents
  - Return an individual agent by ID
  - Build a graph representation suitable for ReactFlow (nodes + edges).

### 3. API endpoints

Implement at least the following FastAPI endpoints:

- `GET /agents`
  - Returns list of agents (basic metadata).
- `GET /agents/{agent_id}`
  - Returns full config for a specific agent.
- `POST /agents/{agent_id}/simulate`
  - Request body: `{"input": "user prompt"}` (plus optional params).
  - For now, stub the actual simulation logic; return a dummy response like:
    - `{"response": "This is a simulated reply from agent X", "trace": [...]}`
  - Make the design extensible so real logic can be plugged in later.

- `GET /config/agents`
  - Returns the full YAML content as a string (or structured JSON) for the editor.

- `PUT /config/agents`
  - Accepts updated YAML content.
  - Validates YAML:
    - If invalid: return 400 with error details.
    - If valid: overwrite `config/open_agents.yaml` (or save to temp for now) and reload in memory.
  - Return success state and maybe parsed metadata (e.g. number of agents).

- `GET /graph`
  - Returns a graph representation for ReactFlow, e.g.:
    - `{"nodes": [...], "edges": [...]}` with simple shapes:
      - `nodes`: `{ id, data: { label, type }, position }`
      - `edges`: `{ id, source, target }`

These endpoints should be CORS-enabled for the Next.js frontend.

### 4. Multi-agent orchestration skeleton

- In `server/agent_graph.py`, define classes or functions that:
  - Represent an execution graph of agents.
  - Support running a simple “pass a message from one agent to next” pipeline.
- For now, logic can be stubbed but structure should be clear:
  - e.g., `class AgentNode`, `class AgentGraphExecutor`, `run_agent_chain(start_agent_id, input)` etc.
- Wire `POST /agents/{agent_id}/simulate` to call a basic executor function, even if it only returns canned text for now.

---

## Integration details

- Configure the frontend to talk to the backend via environment variables, e.g. `NEXT_PUBLIC_API_BASE_URL`.
- For dev, assume backend runs at `http://localhost:8000` and frontend_web at `http://localhost:3000`.
- Implement basic error handling and loading states on the frontend_web:
  - Show spinners or skeletons while fetching.
  - Show error banners when API calls fail.

---

## Deliverables & output format

When you respond, please:

1. **List the main files and directories** you are creating or modifying (both frontend_web and backend).
2. For each major file, provide the **full code** in separate code blocks, e.g.:

   `frontend_web/app/layout.tsx`:
   ```tsx
   // code here

server/main.py:

# code here

	3.	Include any minimal package.json, requirements.txt, and config files needed to run both frontend_web and backend.
	4.	Keep comments concise but present in tricky parts (YAML parsing, graph mapping, ReactFlow integration).

Focus on clean architecture, good TypeScript types, readable UI, and extensible backend design for future multi-agent orchestration.

