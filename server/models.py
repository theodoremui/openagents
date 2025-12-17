"""
Pydantic models for agent API.

This module defines data transfer objects (DTOs) for the FastAPI server,
following SOLID principles and separation of concerns.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentListItem(BaseModel):
    """Simplified agent model for list views."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    display_name: str
    type: str = "agent"
    description: Optional[str] = None
    enabled: bool = True


class AgentDetail(BaseModel):
    """Detailed agent model with full configuration."""

    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    type: str = "agent"
    module: str
    function: str
    model_name: str
    temperature: float
    max_tokens: int
    tools: List[str] = Field(default_factory=list)
    edges: List[str] = Field(default_factory=list)
    session_memory_enabled: bool = True
    enabled: bool = True


class SimulationRequest(BaseModel):
    """Request model for agent simulation."""

    input: str = Field(..., min_length=1, max_length=10000)
    context: Optional[Dict[str, Any]] = None
    max_steps: int = Field(default=10, ge=1, le=100)
    session_id: Optional[str] = None


class SimulationStep(BaseModel):
    """A single step in the simulation trace."""

    agent_id: str
    agent_name: str
    action: str
    output: Optional[str] = None
    timestamp: Optional[str] = None


class SimulationResponse(BaseModel):
    """Response model for agent simulation."""

    response: str
    trace: List[SimulationStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    """ReactFlow node representation."""

    id: str
    type: str = "default"
    data: Dict[str, Any]
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})


class GraphEdge(BaseModel):
    """ReactFlow edge representation."""

    id: str
    source: str
    target: str
    type: str = "default"
    label: Optional[str] = None
    animated: bool = False


class AgentGraph(BaseModel):
    """Graph representation of agents for ReactFlow."""

    nodes: List[GraphNode]
    edges: List[GraphEdge]


class ConfigUpdate(BaseModel):
    """Model for updating configuration."""

    content: str = Field(..., min_length=1)
    validate_only: bool = False


class ConfigResponse(BaseModel):
    """Response model for config operations."""

    content: str
    agents_count: int
    last_modified: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    agents_loaded: int
    version: str = "0.1.0"
    orchestrator: str = "default"  # Active orchestrator: "default" or "smartrouter"


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None
    timestamp: Optional[str] = None


class StreamChunk(BaseModel):
    """A chunk of streaming response data."""

    type: str  # "token", "step", "metadata", "done"
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
