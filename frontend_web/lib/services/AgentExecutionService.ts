/**
 * Agent Execution Service
 *
 * Implements IAgentExecutionService with Strategy pattern for different execution modes.
 * Follows SOLID principles:
 * - Single Responsibility: Only handles agent execution
 * - Open/Closed: Easy to add new execution modes
 * - Dependency Inversion: Depends on ApiClient abstraction
 */

import type { ApiClient } from "../api-client";
import type {
  SimulationRequest,
  SimulationResponse,
  StreamChunk,
  ExecutionMode,
} from "../types";
import type { IAgentExecutionService } from "./interfaces";

export class AgentExecutionService implements IAgentExecutionService {
  constructor(private apiClient: ApiClient) {}

  /**
   * Execute agent with specified mode
   *
   * Uses Strategy pattern to select execution method based on mode.
   */
  public execute(
    agentId: string,
    request: SimulationRequest,
    mode: ExecutionMode
  ): Promise<SimulationResponse> | AsyncGenerator<StreamChunk, void, unknown> {
    switch (mode) {
      case "mock":
        return this.executeMock(agentId, request);
      case "real":
        return this.executeReal(agentId, request);
      case "stream":
        return this.executeStream(agentId, request);
      default:
        throw new Error(`Unknown execution mode: ${mode}`);
    }
  }

  /**
   * Enhance request with markdown formatting instruction if needed
   */
  private enhanceRequestWithMarkdown(request: SimulationRequest): SimulationRequest {
    const wordCount = request.input.trim().split(/\s+/).length;

    // For queries with more than 50 words or containing "explain", "describe", "tell me about",
    // request markdown format
    const needsMarkdown = wordCount > 50 ||
      /\b(explain|describe|tell me about|what is|how does)\b/i.test(request.input);

    if (needsMarkdown) {
      return {
        ...request,
        input: `${request.input}\n\nPlease format your response in structured rich text Markdown format if the response has more than 50 words.`,
      };
    }

    return request;
  }

  /**
   * Execute with mock mode
   *
   * Fast, no API costs, useful for testing
   */
  public async executeMock(
    agentId: string,
    request: SimulationRequest
  ): Promise<SimulationResponse> {
    const enhancedRequest = this.enhanceRequestWithMarkdown(request);
    return this.apiClient.simulateAgent(agentId, enhancedRequest);
  }

  /**
   * Execute with real mode
   *
   * Makes actual OpenAI API calls, returns complete response
   */
  public async executeReal(
    agentId: string,
    request: SimulationRequest
  ): Promise<SimulationResponse> {
    const enhancedRequest = this.enhanceRequestWithMarkdown(request);
    return this.apiClient.chatAgent(agentId, enhancedRequest);
  }

  /**
   * Execute with streaming mode
   *
   * Makes actual OpenAI API calls, streams tokens in real-time
   */
  public async *executeStream(
    agentId: string,
    request: SimulationRequest
  ): AsyncGenerator<StreamChunk, void, unknown> {
    const enhancedRequest = this.enhanceRequestWithMarkdown(request);
    yield* this.apiClient.chatAgentStream(agentId, enhancedRequest);
  }
}
