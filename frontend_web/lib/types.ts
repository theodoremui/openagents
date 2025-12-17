/**
 * Type definitions for the OpenAgents API.
 * These types mirror the backend Pydantic models.
 */

export interface AgentListItem {
  id: string;
  name: string;
  display_name: string;
  type?: string;
  description?: string;
  enabled: boolean;
}

export interface AgentDetail {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  type: string;
  module: string;
  function: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  tools: string[];
  edges: string[];
  session_memory_enabled: boolean;
  enabled: boolean;
}

/**
 * Execution mode for agent interaction
 */
export type ExecutionMode = "mock" | "real" | "stream";

/**
 * Request for agent execution (used by all three modes)
 */
export interface SimulationRequest {
  input: string;
  context?: Record<string, unknown>;
  max_steps?: number;
  session_id?: string;
}

/**
 * Single step in execution trace
 */
export interface SimulationStep {
  agent_id: string;
  agent_name: string;
  action: string;
  output?: string;
  timestamp?: string;
}

/**
 * Response from agent execution (mock or real)
 */
export interface SimulationResponse {
  response: string;
  trace: SimulationStep[];
  metadata: {
    mode?: "mock" | "real";
    agent_id?: string;
    agent_name?: string;
    session_enabled?: boolean;
    session_id?: string;
    max_turns?: number;
    timestamp?: string;
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
    conversation_id?: string;
    response_id?: string;
    [key: string]: unknown;
  };
}

/**
 * Chunk types for streaming responses
 */
export type StreamChunkType = "metadata" | "token" | "step" | "done" | "error";

/**
 * Single chunk in streaming response
 */
export interface StreamChunk {
  type: StreamChunkType;
  content?: string;
  metadata?: Record<string, unknown>;
}

export interface GraphNode {
  id: string;
  type: string;
  data: {
    label: string;
    description?: string;
    type?: string;
    [key: string]: unknown;
  };
  position: {
    x: number;
    y: number;
  };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  animated?: boolean;
}

export interface AgentGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ConfigResponse {
  content: string;
  agents_count: number;
  last_modified?: string;
}

export interface ConfigUpdate {
  content: string;
  validate_only?: boolean;
}

export interface HealthResponse {
  status: string;
  agents_loaded: number;
  version: string;
  orchestrator?: string; // "default" or "smartrouter"
}

export interface ApiError {
  detail: string;
  error_code?: string;
  timestamp?: string;
}

/**
 * SmartRouter-specific types
 */

export type QueryComplexity = "SIMPLE" | "MODERATE" | "COMPLEX";

export interface SmartRouterQueryIntent {
  original_query: string;
  complexity: QueryComplexity;
  domains: string[];
  requires_synthesis: boolean;
  reasoning?: string;
}

export interface SmartRouterSubquery {
  id: string;
  text: string;
  capability_required: string;
  agent_id?: string; // Assigned during routing
  routing_pattern?: "delegation" | "handoff";
}

export interface SmartRouterAgentResponse {
  subquery_id: string;
  agent_id: string;
  agent_name?: string;
  content: string;
  success: boolean;
  error?: string;
  execution_time?: number;
}

export interface SmartRouterSynthesis {
  answer: string;
  sources: string[];
  confidence: number;
  conflicts_resolved?: string[];
}

export interface SmartRouterEvaluation {
  is_high_quality: boolean;
  completeness_score: number;
  accuracy_score: number;
  clarity_score: number;
  should_fallback: boolean;
  issues?: string[];
}

export interface SmartRouterTrace {
  duration?: number;
  phase: "interpretation" | "decomposition" | "routing" | "execution" | "synthesis" | "evaluation";
  timestamp: string;
  data: SmartRouterTraceData;
}

export interface SmartRouterTraceData {
  // Phase-specific data
  intent?: SmartRouterQueryIntent;
  subqueries?: SmartRouterSubquery[];
  responses?: SmartRouterAgentResponse[];
  synthesis?: SmartRouterSynthesis;
  evaluation?: SmartRouterEvaluation;
  // Execution phase specific
  concurrent?: boolean;
  agent_executions?: Array<{
    agent: string;
    status: string;
    duration?: number;
    response?: string;
  }>;
  // Routing phase specific
  pattern?: string;
  domains?: string[];
  selected_agents?: string[];
}

export interface SmartRouterMetadata {
  agents_used?: string[];
  query?: string;
  orchestrator: "smartrouter";
  total_time?: number;
  phases: SmartRouterTrace[];
  final_decision?: "answer" | "fallback";
}
