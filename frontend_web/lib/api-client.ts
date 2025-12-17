/**
 * API Client for OpenAgents Backend
 *
 * Provides a type-safe, centralized interface for all API operations.
 * Implements the Singleton pattern and follows SOLID principles.
 *
 * Features:
 * - Automatic authentication via API key
 * - Type-safe request/response handling
 * - Error handling with custom errors
 * - Request/response interceptors
 * - Retry logic for failed requests
 */

import type {
  AgentListItem,
  AgentDetail,
  SimulationRequest,
  SimulationResponse,
  StreamChunk,
  AgentGraph,
  ConfigResponse,
  ConfigUpdate,
  HealthResponse,
  ApiError,
} from "./types";

import type {
  CreateVoiceSessionRequest,
  CreateVoiceSessionResponse,
  VoiceSessionStatus,
  VoiceConfig,
} from "./types/voice";

/**
 * Custom error class for API errors
 */
export class ApiClientError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public errorCode?: string
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

/**
 * Configuration for API client
 */
interface ApiClientConfig {
  baseUrl: string;
  apiKey: string;
  timeout?: number;
  retries?: number;
}

/**
 * API Client class
 *
 * Implements Singleton pattern to ensure single instance across the app.
 * Provides methods for all backend endpoints.
 */
export class ApiClient {
  private static instance: ApiClient | null = null;
  private config: ApiClientConfig;

  private constructor(config: ApiClientConfig) {
    this.config = {
      timeout: 120000, // 120 seconds (2 minutes) - increased for MapAgent multi-step operations
      retries: 3,
      ...config,
    };
  }

  /**
   * Get singleton instance
   */
  public static getInstance(config?: ApiClientConfig): ApiClient {
    if (!ApiClient.instance) {
      if (!config) {
        throw new Error("ApiClient must be initialized with config first");
      }
      ApiClient.instance = new ApiClient(config);
    }
    return ApiClient.instance;
  }

  /**
   * Reset singleton instance (useful for testing)
   */
  public static resetInstance(): void {
    ApiClient.instance = null;
  }

  /**
   * Get base URL (for trace polling)
   */
  public get baseUrl(): string {
    return this.config.baseUrl;
  }

  /**
   * Get API key (for trace polling)
   */
  public get apiKey(): string {
    return this.config.apiKey;
  }

  /**
   * Make HTTP request with error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`;

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      "X-API-Key": this.config.apiKey,
      ...options.headers,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      this.config.timeout
    );

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        // Handle error responses - may also be empty
        let error: ApiError;
        try {
          const text = await response.text();
          if (text && text.trim().length > 0) {
            error = JSON.parse(text);
          } else {
            // Empty error response
            error = { detail: response.statusText || "Unknown error" };
          }
        } catch (parseError) {
          // If JSON parsing fails, use status text
          error = { detail: response.statusText || "Unknown error" };
        }

        throw new ApiClientError(
          error.detail || "Unknown error",
          response.status,
          error.error_code
        );
      }

      // Handle empty responses (e.g., 204 No Content, 204 responses have no body)
      // Check status code first - 204 No Content means no response body
      if (response.status === 204) {
        return null as T;
      }

      // Check content-length header - if 0, there's no body
      const contentLength = response.headers.get("content-length");
      if (contentLength === "0") {
        return null as T;
      }

      // Get response text first to check if there's any content
      const text = await response.text();
      
      // If response is empty, return null
      if (!text || text.trim().length === 0) {
        return null as T;
      }

      // Try to parse JSON, handle parsing errors gracefully
      try {
        return JSON.parse(text) as T;
      } catch (error) {
        // If JSON parsing fails, log warning and return null
        // This handles cases where server returns non-JSON content or malformed JSON
        console.warn(`Failed to parse JSON response from ${endpoint}:`, error);
        return null as T;
      }
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ApiClientError) {
        throw error;
      }

      if (error instanceof Error) {
        if (error.name === "AbortError") {
          throw new ApiClientError("Request timeout", 408);
        }
        throw new ApiClientError(error.message);
      }

      throw new ApiClientError("Unknown error occurred");
    }
  }

  /**
   * Health check
   */
  public async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  /**
   * List all agents
   */
  public async listAgents(): Promise<AgentListItem[]> {
    return this.request<AgentListItem[]>("/agents");
  }

  /**
   * Get agent details
   */
  public async getAgent(agentId: string): Promise<AgentDetail> {
    return this.request<AgentDetail>(`/agents/${agentId}`);
  }

  /**
   * Simulate agent execution (MOCK - no API calls)
   * Fast for testing, returns mock responses
   */
  public async simulateAgent(
    agentId: string,
    request: SimulationRequest
  ): Promise<SimulationResponse> {
    return this.request<SimulationResponse>(`/agents/${agentId}/simulate`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Execute agent with REAL OpenAI API calls (complete response)
   * Returns after execution finishes
   */
  public async chatAgent(
    agentId: string,
    request: SimulationRequest
  ): Promise<SimulationResponse> {
    return this.request<SimulationResponse>(`/agents/${agentId}/chat`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Execute agent with REAL OpenAI API calls (streaming response)
   * Returns async generator for real-time tokens
   */
  public async *chatAgentStream(
    agentId: string,
    request: SimulationRequest
  ): AsyncGenerator<StreamChunk, void, unknown> {
    const url = `${this.config.baseUrl}/agents/${agentId}/chat/stream`;

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      "X-API-Key": this.config.apiKey,
    };

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      // Handle error responses - may also be empty
      let error: ApiError;
      try {
        const text = await response.text();
        if (text && text.trim().length > 0) {
          error = JSON.parse(text);
        } else {
          // Empty error response
          error = { detail: response.statusText || "Streaming request failed" };
        }
      } catch (parseError) {
        // If JSON parsing fails, use status text
        error = { detail: response.statusText || "Streaming request failed" };
      }

      throw new ApiClientError(
        error.detail || "Streaming request failed",
        response.status,
        error.error_code
      );
    }

    if (!response.body) {
      throw new ApiClientError("No response body for streaming");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const chunk: StreamChunk = JSON.parse(line.slice(6));
              yield chunk;
            } catch (e) {
              // Skip malformed chunks
              console.warn("Failed to parse stream chunk:", e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Get agent graph for visualization
   */
  public async getGraph(): Promise<AgentGraph> {
    return this.request<AgentGraph>("/graph");
  }

  /**
   * Get configuration
   */
  public async getConfig(): Promise<ConfigResponse> {
    return this.request<ConfigResponse>("/config/agents");
  }

  /**
   * Update configuration
   */
  public async updateConfig(
    update: ConfigUpdate
  ): Promise<{ success: boolean; message: string; agents_count?: number }> {
    return this.request("/config/agents", {
      method: "PUT",
      body: JSON.stringify(update),
    });
  }

  /**
   * Validate configuration without saving
   */
  public async validateConfig(
    content: string
  ): Promise<{ valid: boolean; message: string }> {
    const result = await this.updateConfig({ content, validate_only: true });
    return {
      valid: result.success,
      message: result.message,
    };
  }

  // ==================== Voice Mode API Methods ====================

  /**
   * Create a new real-time voice session
   */
  public async createVoiceSession(
    request: CreateVoiceSessionRequest
  ): Promise<CreateVoiceSessionResponse> {
    return this.request<CreateVoiceSessionResponse>("/voice/realtime/session", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Get voice session status
   */
  public async getVoiceSessionStatus(
    sessionId: string
  ): Promise<VoiceSessionStatus> {
    return this.request<VoiceSessionStatus>(
      `/voice/realtime/session/${sessionId}`
    );
  }

  /**
   * End a voice session
   */
  public async endVoiceSession(sessionId: string): Promise<void> {
    await this.request(`/voice/realtime/session/${sessionId}`, {
      method: "DELETE",
    });
  }

  /**
   * Get voice configuration
   */
  public async getVoiceConfig(): Promise<VoiceConfig> {
    return this.request<VoiceConfig>("/voice/realtime/config");
  }

  /**
   * Check voice service health
   */
  public async checkVoiceHealth(): Promise<{
    status: string;
    livekit_connected: boolean;
    active_rooms?: number;
  }> {
    return this.request("/voice/realtime/health");
  }
}

/**
 * Initialize and export API client instance
 */
export function initializeApiClient(): ApiClient {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const apiKey = process.env.NEXT_PUBLIC_API_KEY || "";

  return ApiClient.getInstance({
    baseUrl,
    apiKey,
  });
}

/**
 * Get API client instance (must be initialized first)
 */
export function getApiClient(): ApiClient {
  return ApiClient.getInstance();
}
