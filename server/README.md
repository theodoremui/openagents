# Multi-Agent Orchestration Server

Secure FastAPI server for managing and simulating multi-agent systems.

## Features

- ✅ **Secure API** with API key authentication
- ✅ **SOLID Architecture** with clean separation of concerns
- ✅ **Integration** with existing `asdrp.agents` infrastructure
- ✅ **Comprehensive Tests** with pytest
- ✅ **Type Safety** with Pydantic models and mypy
- ✅ **CORS Support** for frontend integration
- ✅ **Configuration Management** with YAML validation

## Architecture

```
server/
├── __init__.py
├── main.py              # FastAPI app with endpoints
├── models.py            # Pydantic DTOs
├── auth.py              # Authentication & security
├── agent_service.py     # Business logic layer
├── pyproject.toml       # Dependencies (uv)
└── README.md
```

### Design Principles

- **Single Responsibility**: Each module has one clear purpose
- **Dependency Inversion**: Depends on abstractions (`AgentProtocol`, `AgentFactory`)
- **Open/Closed**: Easy to extend without modifying existing code
- **DRY**: Centralized configuration and error handling
- **Loose Coupling**: Service layer separates API from business logic
- **High Cohesion**: Related functionality grouped together

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Navigate to project root
cd /path/to/openagents

# Install dependencies using uv
uv pip install -e server/

# Or install from pyproject.toml
cd server
uv pip install .
```

### Configuration

Create a `.env` file in the project root:

```bash
# Authentication
AUTH_ENABLED=true
API_KEYS=your_api_key_1,your_api_key_2
JWT_SECRET_KEY=your_jwt_secret_key

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=false
LOG_LEVEL=info

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Trusted Hosts
TRUSTED_HOSTS=localhost,127.0.0.1

# Optional
ENABLE_DOCS=true
```

## Running the Server

### Development

```bash
# With auto-reload
python -m server.main

# Or with uvicorn directly
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
# Using environment variables
export AUTH_ENABLED=true
export API_KEYS=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health & Info

- `GET /` - API information
- `GET /health` - Health check

### Agents (Requires Authentication)

**Discovery:**
- `GET /agents` - List all agents
- `GET /agents/{agent_id}` - Get agent details

**Testing (Mock - No API Calls):**
- `POST /agents/{agent_id}/simulate` - Mock response for fast testing

**Execution (Real - OpenAI API Calls):**
- `POST /agents/{agent_id}/chat` - Execute agent (complete response)
- `POST /agents/{agent_id}/chat/stream` - Execute agent (streaming response)

### Configuration (Requires Authentication)

- `GET /config/agents` - Get YAML configuration
- `PUT /config/agents` - Update YAML configuration

### Visualization (Requires Authentication)

- `GET /graph` - Get ReactFlow graph data

## Authentication

All protected endpoints require an `X-API-Key` header:

```bash
# List agents
curl -H "X-API-Key: your_api_key" http://localhost:8000/agents

# Mock agent (no API calls - fast testing)
curl -X POST \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"input": "What is the capital of France?"}' \
  http://localhost:8000/agents/geo/simulate

# Execute agent (real API call - complete response)
curl -X POST \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"input": "What is the capital of France?"}' \
  http://localhost:8000/agents/geo/chat

# Execute agent (real API call - streaming response)
curl -N -X POST \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"input": "What is the capital of France?"}' \
  http://localhost:8000/agents/geo/chat/stream
```

### Disabling Authentication (Development Only)

```bash
export AUTH_ENABLED=false
python -m server.main
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=server --cov-report=html

# Run specific test file
pytest tests/server/test_auth.py -v

# Run specific test
pytest tests/server/test_models.py::TestAgentModels::test_agent_list_item_valid -v
```

## Security Features

### API Key Authentication

- Configurable API keys via environment variables
- Secure key validation
- Custom authentication headers

### JWT Support

- Token generation and verification
- Configurable expiration
- Secure secret key management

### CORS Protection

- Configurable allowed origins
- Credential support
- Method and header restrictions

### Trusted Host Middleware

- Prevents host header attacks
- Configurable allowed hosts

### Input Validation

- Pydantic models for all requests
- Length and range constraints
- Type safety

### Password Hashing

- Bcrypt-based hashing
- Automatic salt generation

## Integration with asdrp.agents

The server integrates seamlessly with the existing `asdrp.agents` infrastructure:

```python
from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.protocol import AgentProtocol
from asdrp.agents.config_loader import AgentConfigLoader

# The server uses these abstractions via AgentService
service = AgentService()
agents = service.list_agents()  # Uses AgentConfigLoader
agent, session = await service.simulate_agent(...)  # Uses AgentFactory
```

## Error Handling

All errors return consistent JSON responses:

```json
{
  "detail": "Error message",
  "error_code": "agent_error",
  "timestamp": "2025-11-29T12:00:00"
}
```

## Development

### Code Quality

```bash
# Format code
black server/

# Lint
ruff server/

# Type check
mypy server/
```

### Adding New Endpoints

1. Define request/response models in `models.py`
2. Add business logic method in `agent_service.py`
3. Create endpoint in `main.py`
4. Write tests in `tests/server/`

### Adding New Agent Types

Agents are defined in `config/open_agents.yaml`. The server automatically discovers and loads them via `AgentFactory`.

## Troubleshooting

### Config File Not Found

```
Error: Configuration file not found: config/open_agents.yaml
```

Solution: Ensure `config/open_agents.yaml` exists in the project root.

### Import Errors

```
ModuleNotFoundError: No module named 'asdrp'
```

Solution: Run server from project root where `asdrp/` is accessible.

### Authentication Failures

```
401 Unauthorized: Missing API key
```

Solution: Include `X-API-Key` header or disable auth for development.

## License

Copyright © 2025 OpenAgents Team
