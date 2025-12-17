/**
 * Service Layer Interfaces
 *
 * Defines abstractions for all services following SOLID principles.
 * These interfaces enable dependency injection and make testing easier.
 */

import type {
  AgentListItem,
  AgentDetail,
  SimulationRequest,
  SimulationResponse,
  StreamChunk,
  ExecutionMode,
} from "../types";

/**
 * Interface for agent execution service
 *
 * Handles all forms of agent execution (mock, real, streaming)
 * following the Strategy pattern for different execution modes.
 */
export interface IAgentExecutionService {
  /**
   * Execute agent with specified mode
   * @param agentId - Agent identifier
   * @param request - Execution request
   * @param mode - Execution mode (mock/real/stream)
   * @returns Promise resolving to response or async generator for streaming
   */
  execute(
    agentId: string,
    request: SimulationRequest,
    mode: ExecutionMode
  ): Promise<SimulationResponse> | AsyncGenerator<StreamChunk, void, unknown>;

  /**
   * Execute with mock mode (fast, no API calls)
   */
  executeMock(
    agentId: string,
    request: SimulationRequest
  ): Promise<SimulationResponse>;

  /**
   * Execute with real mode (complete response)
   */
  executeReal(
    agentId: string,
    request: SimulationRequest
  ): Promise<SimulationResponse>;

  /**
   * Execute with streaming mode (real-time tokens)
   */
  executeStream(
    agentId: string,
    request: SimulationRequest
  ): AsyncGenerator<StreamChunk, void, unknown>;
}

/**
 * Interface for agent management service
 *
 * Handles CRUD operations for agents
 */
export interface IAgentService {
  /**
   * List all available agents
   */
  listAgents(): Promise<AgentListItem[]>;

  /**
   * Get details for specific agent
   */
  getAgent(agentId: string): Promise<AgentDetail>;

  /**
   * Refresh agent list from backend
   */
  refreshAgents(): Promise<void>;
}

/**
 * Interface for configuration service
 *
 * Handles config management operations
 */
export interface IConfigService {
  /**
   * Get current configuration
   */
  getConfig(): Promise<{ content: string; agents_count: number }>;

  /**
   * Update configuration
   */
  updateConfig(content: string): Promise<{ success: boolean; message: string }>;

  /**
   * Validate configuration without saving
   */
  validateConfig(content: string): Promise<{ valid: boolean; message: string }>;
}

/**
 * Interface for streaming service
 *
 * Handles Server-Sent Events streaming
 */
export interface IStreamingService {
  /**
   * Start streaming session
   */
  startStream(
    agentId: string,
    request: SimulationRequest
  ): AsyncGenerator<StreamChunk, void, unknown>;

  /**
   * Stop active stream
   */
  stopStream(): void;

  /**
   * Check if stream is active
   */
  isStreaming(): boolean;
}

/**
 * Interface for session management
 *
 * Handles conversation sessions
 */
export interface ISessionService {
  /**
   * Get or create session ID
   */
  getSessionId(agentId: string): string;

  /**
   * Clear session for agent
   */
  clearSession(agentId: string): void;

  /**
   * Clear all sessions
   */
  clearAllSessions(): void;
}
