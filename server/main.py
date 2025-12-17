"""
FastAPI application entrypoint.

Main application with secure endpoints, CORS configuration, and proper
error handling. Follows REST API best practices and security guidelines.
"""

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

# Add project root to Python path to ensure asdrp module is importable
# This is needed when running from server/.venv
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from server.models import (
    AgentListItem,
    AgentDetail,
    SimulationRequest,
    SimulationResponse,
    AgentGraph,
    ConfigUpdate,
    ConfigResponse,
    HealthResponse,
    ErrorResponse,
    StreamChunk,
)
from server.agent_service import AgentService
from server.auth import verify_api_key
from asdrp.agents.protocol import AgentException


# Global service instance
_agent_service: AgentService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app."""
    global _agent_service

    # Startup: Initialize services
    print("🚀 Starting Multi-Agent Orchestration API...")

    # Check orchestrator type
    orchestrator_type = os.getenv("ORCHESTRATOR", "default")
    print(f"🎯 Active Orchestrator: {orchestrator_type}")

    # Validate SmartRouter if selected
    if orchestrator_type == "smartrouter":
        try:
            from asdrp.orchestration.smartrouter.config_loader import SmartRouterConfigLoader
            sr_config_loader = SmartRouterConfigLoader()
            sr_config = sr_config_loader.load_config()

            if not sr_config.enabled:
                print("⚠️  Warning: SmartRouter selected but disabled in config. Using default orchestrator.")
                orchestrator_type = "default"
                os.environ["ORCHESTRATOR"] = "default"
            else:
                print(f"✓ SmartRouter configuration loaded from: config/smartrouter.yaml")
                print(f"✓ SmartRouter capabilities: {len(sr_config.capabilities)} agents")
        except Exception as e:
            print(f"⚠️  Warning: Failed to load SmartRouter config: {e}")
            print("   Falling back to default orchestrator.")
            orchestrator_type = "default"
            os.environ["ORCHESTRATOR"] = "default"

    try:
        _agent_service = AgentService()
        agents = _agent_service.list_agents()
        print(f"✓ Loaded {len(agents)} agents")
        print(f"✓ Agents available: {', '.join([a.name for a in agents])}")

        # Initialize MCP server configurations
        # Note: stdio transport servers are managed by agents themselves
        # This just validates configurations and prepares the manager
        from asdrp.agents.mcp import get_mcp_manager
        from asdrp.agents.agent_factory import AgentFactory

        mcp_manager = get_mcp_manager()
        factory = AgentFactory.instance()

        # Check for MCP-enabled agents
        mcp_agent_count = 0
        for agent_item in agents:
            try:
                agent_config = factory.get_agent_config(agent_item.id)
                if agent_config.mcp_server and agent_config.mcp_server.enabled:
                    mcp_agent_count += 1
                    print(f"✓ MCP-enabled agent: {agent_item.display_name} ({agent_config.mcp_server.transport} transport)")
            except Exception as e:
                # Non-critical: continue startup even if MCP check fails
                print(f"⚠️  Could not check MCP config for {agent_item.id}: {e}")

        if mcp_agent_count > 0:
            print(f"✓ {mcp_agent_count} MCP-enabled agent(s) configured")
        else:
            print("ℹ️  No MCP-enabled agents configured")

    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize agent service: {e}")
        print("   Server will start but agent endpoints may return errors")
        _agent_service = AgentService()  # Create service anyway

    # Initialize Voice module
    try:
        from server.voice.dependencies import get_voice_service
        voice_service = get_voice_service()
        print("✓ Voice module initialized")
        # Check if ElevenLabs API key is configured
        if os.getenv("ELEVENLABS_API_KEY"):
            print("✓ ElevenLabs API key configured")
        else:
            print("⚠️  Warning: ELEVENLABS_API_KEY not set. Voice features will be unavailable.")
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize Voice module: {e}")
        print("   Voice endpoints will return errors. Set ELEVENLABS_API_KEY to enable.")

    yield

    # Shutdown: Clean up MCP servers
    print("👋 Shutting down...")
    try:
        from asdrp.agents.mcp import get_mcp_manager
        mcp_manager = get_mcp_manager()
        await mcp_manager.shutdown_all()
    except Exception as e:
        print(f"⚠️  Error during MCP shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Orchestration API",
    description="Secure API for managing and simulating multi-agent systems",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true") == "true" else None,
    redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "true") == "true" else None,
)

# Security middleware - trusted hosts
# Only enable in production; disable in development for easier local testing
trusted_hosts_env = os.getenv("TRUSTED_HOSTS", "")
if (trusted_hosts_env.lower() == "disable" or 
    os.getenv("RELOAD", "false") == "true" or 
    os.getenv("TESTING", "false") == "true"):
    # Skip trusted host middleware in development/testing
    pass
else:
    # In production, use configured hosts or defaults
    default_hosts = "localhost,127.0.0.1"
    trusted_hosts = os.getenv("TRUSTED_HOSTS", default_hosts).split(",")
    # Filter out empty strings and strip whitespace
    trusted_hosts = [h.strip() for h in trusted_hosts if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

# CORS configuration
allowed_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# Include Voice module router (async voice)
try:
    from server.voice.router import router as voice_router
    app.include_router(voice_router)
    print("✓ Voice module API endpoints registered")
except Exception as e:
    print(f"⚠️  Warning: Failed to load Voice module: {e}")
    print("   Voice endpoints will not be available")

# Include Real-time Voice module router
try:
    from server.voice.realtime.router import router as realtime_voice_router
    app.include_router(realtime_voice_router)
    print("✓ Real-time voice module API endpoints registered")
except Exception as e:
    print(f"⚠️  Warning: Failed to load Real-time Voice module: {e}")
    print("   Real-time voice endpoints will not be available. Check LIVEKIT_* environment variables.")


def get_service() -> AgentService:
    """Dependency injection for AgentService."""
    if _agent_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent service not initialized",
        )
    return _agent_service


@app.exception_handler(AgentException)
async def agent_exception_handler(request, exc: AgentException):
    """Handle AgentException errors gracefully."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            detail=exc.message,
            error_code="agent_error",
            timestamp=datetime.utcnow().isoformat(),
        ).model_dump(),
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Multi-Agent Orchestration API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health(service: AgentService = Depends(get_service)):
    """
    Health check endpoint.

    Returns server health status including active orchestrator information.
    """
    try:
        agents = service.list_agents()
        orchestrator = os.getenv("ORCHESTRATOR", "default")
        return HealthResponse(
            status="healthy",
            agents_loaded=len(agents),
            version="0.1.0",
            orchestrator=orchestrator
        )
    except Exception as e:
        orchestrator = os.getenv("ORCHESTRATOR", "default")
        return HealthResponse(
            status="unhealthy",
            agents_loaded=0,
            version="0.1.0",
            orchestrator=orchestrator
        )


@app.get(
    "/agents",
    response_model=list[AgentListItem],
    tags=["Agents"],
    dependencies=[Depends(verify_api_key)],
)
async def list_agents(service: AgentService = Depends(get_service)):
    """
    Get list of all available agents.

    Requires authentication via X-API-Key header.
    """
    return service.list_agents()


@app.get(
    "/agents/{agent_id}",
    response_model=AgentDetail,
    tags=["Agents"],
    dependencies=[Depends(verify_api_key)],
)
async def get_agent(agent_id: str, service: AgentService = Depends(get_service)):
    """
    Get detailed information about a specific agent.

    Args:
        agent_id: Agent identifier (e.g., 'geo', 'finance', 'map')

    Requires authentication via X-API-Key header.
    """
    try:
        return await service.get_agent_detail(agent_id)
    except AgentException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.get(
    "/agents/{agent_id}/tools",
    tags=["Agents - Diagnostics"],
    dependencies=[Depends(verify_api_key)],
)
async def get_agent_tools(agent_id: str, service: AgentService = Depends(get_service)):
    """
    Get the list of tools available to a specific agent.

    This is a diagnostic endpoint to verify which tools an agent has access to.
    Useful for debugging tool availability issues.

    Args:
        agent_id: Agent identifier (e.g., 'geo', 'finance', 'map')

    Returns:
        Dictionary containing:
        - tool_count: Number of tools
        - tool_names: List of tool names
        - has_get_static_map_url: Boolean (for MapAgent)

    Requires authentication via X-API-Key header.
    """
    try:
        # Get agent instance
        from asdrp.agents.agent_factory import AgentFactory
        factory = AgentFactory.instance()
        agent = await factory.get_agent(agent_id)  # Fixed: Added await for async function

        # Extract tool information using robust extraction logic
        # This matches the logic in tests/asdrp/agents/test_tool_extraction.py
        tool_names = []
        if hasattr(agent, 'tools') and agent.tools:
            for i, tool in enumerate(agent.tools):
                try:
                    exceptions_occurred = False
                    
                    # Try accessing attributes directly to catch exceptions
                    try:
                        tool_name = tool.name
                        tool_names.append(tool_name)
                        continue
                    except (AttributeError, Exception):
                        exceptions_occurred = True
                    
                    try:
                        tool_name = tool.__name__
                        tool_names.append(tool_name)
                        continue
                    except (AttributeError, Exception):
                        exceptions_occurred = True
                    
                    try:
                        if hasattr(tool, 'function') and tool.function is not None:
                            tool_name = tool.function.__name__
                            tool_names.append(tool_name)
                            continue
                    except (AttributeError, Exception):
                        exceptions_occurred = True
                    
                    try:
                        tool_name = tool.__class__.__name__
                        tool_names.append(tool_name)
                        continue
                    except (AttributeError, Exception):
                        exceptions_occurred = True
                    
                    # If all attribute accesses failed, use fallback
                    tool_names.append(f"tool_{i}")
                        
                except Exception:
                    # If we can't get the name, use a safe fallback
                    tool_names.append(f"tool_{i}")

        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "tool_count": len(tool_names),
            "tool_names": tool_names,
            "has_get_static_map_url": "get_static_map_url" in tool_names,
            "has_get_interactive_map_data": "get_interactive_map_data" in tool_names,
            "timestamp": datetime.utcnow().isoformat()
        }

    except AgentException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post(
    "/agents/{agent_id}/simulate",
    response_model=SimulationResponse,
    tags=["Agents - Testing"],
    dependencies=[Depends(verify_api_key)],
)
async def simulate_agent(
    agent_id: str,
    request: SimulationRequest,
    service: AgentService = Depends(get_service),
):
    """
    Simulate agent execution with MOCK responses (no actual API calls).

    This endpoint returns stub responses for fast testing and development
    without making actual OpenAI API calls. Useful for:
    - UI development and testing
    - Integration tests
    - CI/CD pipelines
    - Cost-free infrastructure testing

    ⚠️ This is NOT a real agent execution. Use POST /agents/{agent_id}/chat for real execution.

    Args:
        agent_id: Agent identifier (e.g., 'geo', 'finance', 'map')
        request: Simulation request with input and parameters

    Returns:
        Mock response with simulated output

    Requires authentication via X-API-Key header.
    """
    try:
        return await service.simulate_agent(agent_id, request)
    except AgentException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post(
    "/agents/{agent_id}/chat",
    response_model=SimulationResponse,
    tags=["Agents - Execution"],
    dependencies=[Depends(verify_api_key)],
)
async def chat_agent(
    agent_id: str,
    request: SimulationRequest,
    service: AgentService = Depends(get_service),
):
    """
    Execute agent with REAL OpenAI API calls using agents.Runner.run().

    This endpoint actually invokes the OpenAI agents.Agent and returns
    the complete response after execution finishes. This makes real API
    calls and will incur OpenAI usage costs.

    Args:
        agent_id: Agent identifier (e.g., 'geo', 'finance', 'map')
        request: Simulation request with input and parameters

    Returns:
        Complete agent response with trace and metadata

    Requires authentication via X-API-Key header.

    Example:
        ```bash
        curl -X POST \\
          -H "X-API-Key: your_key" \\
          -H "Content-Type: application/json" \\
          -d '{"input": "What is the capital of France?"}' \\
          http://localhost:8000/agents/geo/chat
        ```
    """
    try:
        return await service.chat_agent(agent_id, request)
    except AgentException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post(
    "/agents/{agent_id}/chat/stream",
    tags=["Agents - Execution"],
    dependencies=[Depends(verify_api_key)],
)
async def chat_agent_stream(
    agent_id: str,
    request: SimulationRequest,
    service: AgentService = Depends(get_service),
):
    """
    Execute agent with REAL streaming response using agents.Runner.run_streamed().

    This endpoint invokes the OpenAI agents.Agent and streams the response
    in real-time as tokens are generated. This makes real API calls and will
    incur OpenAI usage costs. Useful for:
    - Interactive chat interfaces
    - Long-running agents
    - Real-time user feedback

    Response format: Server-Sent Events (SSE) with JSON chunks.
    Each chunk has: {"type": "token"|"step"|"metadata"|"done"|"error", "content": "...", "metadata": {...}}

    Args:
        agent_id: Agent identifier (e.g., 'geo', 'finance', 'map')
        request: Simulation request with input and parameters

    Returns:
        Streaming response with real-time tokens

    Requires authentication via X-API-Key header.

    Example (JavaScript):
        ```javascript
        const response = await fetch('/agents/geo/chat/stream', {
            method: 'POST',
            headers: {'X-API-Key': 'your_key', 'Content-Type': 'application/json'},
            body: JSON.stringify({input: 'What is the capital of France?'})
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const {done, value} = await reader.read();
            if (done) break;

            const text = decoder.decode(value);
            const lines = text.split('\\n\\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const chunk = JSON.parse(line.slice(6));
                    if (chunk.type === 'token') {
                        console.log(chunk.content);  // Stream tokens
                    }
                }
            }
        }
        ```

    Example (curl):
        ```bash
        curl -N -X POST \\
          -H "X-API-Key: your_key" \\
          -H "Content-Type: application/json" \\
          -d '{"input": "What is the capital of France?"}' \\
          http://localhost:8000/agents/geo/chat/stream
        ```
    """
    async def generate():
        """Generator function for streaming response."""
        try:
            async for chunk in service.chat_agent_streaming(agent_id, request):
                # Send as JSON + newline for easier parsing
                yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception as e:
            error_chunk = StreamChunk(
                type="error",
                content=f"Stream error: {str(e)}",
                metadata={"agent_id": agent_id}
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.get(
    "/graph",
    response_model=AgentGraph,
    tags=["Visualization"],
    dependencies=[Depends(verify_api_key)],
)
async def get_graph(service: AgentService = Depends(get_service)):
    """
    Get graph representation of agents for ReactFlow visualization.

    Returns nodes and edges for rendering in ReactFlow.

    Requires authentication via X-API-Key header.
    """
    return service.get_agent_graph()


@app.get(
    "/config/agents",
    response_model=ConfigResponse,
    tags=["Configuration"],
    dependencies=[Depends(verify_api_key)],
)
async def get_config(service: AgentService = Depends(get_service)):
    """
    Get current YAML configuration.

    Requires authentication via X-API-Key header.
    """
    config_path = Path("config/open_agents.yaml")

    if not config_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration file not found",
        )

    with open(config_path, "r") as f:
        content = f.read()

    agents = service.list_agents()
    stat = config_path.stat()

    return ConfigResponse(
        content=content,
        agents_count=len(agents),
        last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
    )


@app.put(
    "/config/agents",
    tags=["Configuration"],
    dependencies=[Depends(verify_api_key)],
)
async def update_config(
    update: ConfigUpdate,
    service: AgentService = Depends(get_service),
):
    """
    Update YAML configuration.

    Args:
        update: Configuration update with new YAML content

    Requires authentication via X-API-Key header.
    """
    # Validate YAML
    is_valid, error = service.validate_config(update.content)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML: {error}",
        )

    if update.validate_only:
        return {"valid": True, "message": "YAML is valid"}

    # Save configuration
    config_path = Path("config/open_agents.yaml")

    try:
        # Backup existing config
        if config_path.exists():
            backup_path = config_path.with_suffix(".yaml.bak")
            import shutil

            shutil.copy(config_path, backup_path)

        # Write new config
        with open(config_path, "w") as f:
            f.write(update.content)

        # Reload configuration
        service.reload_config()

        agents = service.list_agents()

        return {
            "success": True,
            "message": "Configuration updated successfully",
            "agents_count": len(agents),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}",
        )


if __name__ == "__main__":
    import argparse
    import uvicorn

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Multi-Agent Orchestration API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default orchestrator:
  python -m server.main

  # Start with SmartRouter orchestrator:
  python -m server.main --orchestrator smartrouter

  # Start with MoE orchestrator:
  python -m server.main --orchestrator moe

  # Start with custom host/port:
  python -m server.main --host 0.0.0.0 --port 8080

Environment Variables:
  ORCHESTRATOR    - Orchestrator type (default/smartrouter/moe). CLI arg overrides.
  PORT            - Server port (default: 8000)
  HOST            - Server host (default: 0.0.0.0)
  RELOAD          - Enable auto-reload (default: false)
  LOG_LEVEL       - Logging level (default: info)
        """
    )

    parser.add_argument(
        "--orchestrator",
        type=str,
        choices=["default", "smartrouter", "moe"],
        default=os.getenv("ORCHESTRATOR", "default"),
        help="Orchestrator type: 'default' (standard agent routing), 'smartrouter' (LLM-based multi-agent orchestration), or 'moe' (Mixture of Experts with parallel execution)"
    )

    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "0.0.0.0"),
        help="Server host address (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Server port (default: 8000)"
    )

    args = parser.parse_args()

    # Set orchestrator in environment for lifecycle/service access
    os.environ["ORCHESTRATOR"] = args.orchestrator

    # Print startup info
    print(f"🎯 Orchestrator: {args.orchestrator}")

    uvicorn.run(
        "server.main:app",
        host=args.host,
        port=args.port,
        reload=os.getenv("RELOAD", "false") == "true",
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
