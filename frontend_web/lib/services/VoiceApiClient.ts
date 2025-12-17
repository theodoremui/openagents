/**
 * Voice API Client
 *
 * HTTP client for interacting with the backend Voice module REST API.
 * Provides methods for TTS, STT, voice management, and configuration.
 */

// VoiceApiClient uses environment variables directly for configuration
// This ensures it works even before the main ApiClient is initialized

/**
 * Voice synthesis request
 */
export interface SynthesizeRequest {
  text: string;
  voice_id?: string;
  model_id?: string;
  profile_name?: string;
  output_format?: string;
}

/**
 * Transcript result with word timestamps
 */
export interface TranscriptWord {
  word: string;
  start: number;
  end: number;
  confidence?: number;
}

export interface TranscriptResult {
  text: string;
  words: TranscriptWord[];
  confidence?: number;
  language_detected?: string;
  duration_ms?: number;
}

/**
 * Transcription response
 */
export interface TranscriptResponse {
  success: boolean;
  result: TranscriptResult;
  request_id: string;
  processing_time_ms: number;
}

/**
 * Voice information
 */
export interface VoiceInfo {
  voice_id: string;
  name: string;
  category?: string;
  description?: string;
  labels?: Record<string, string>;
  preview_url?: string;
}

/**
 * Voice configuration
 */
export interface VoiceConfig {
  enabled: boolean;
  tts: {
    voice_id: string;
    model_id: string;
    output_format: string;
    stability: number;
    similarity_boost: number;
    style: number;
    use_speaker_boost: boolean;
    max_text_length: number;
    timeout: number;
  };
  stt: {
    model_id: string;
    language_code?: string;
    tag_audio_events: boolean;
    timestamps_granularity: string;
    diarize: boolean;
    max_speakers: number;
    timeout: number;
  };
  voice_profiles: Record<string, any>;
  default_profile: string;
  cache: {
    voice_list_ttl: number;
    enable_response_cache: boolean;
  };
  logging: {
    log_api_calls: boolean;
    log_audio_data: boolean;
    level: string;
  };
}

/**
 * Configuration response
 */
export interface VoiceConfigResponse {
  config: Record<string, any>;
  last_updated: string;
  validation: {
    valid: boolean;
    errors: string[];
    warnings: string[];
  };
}

/**
 * Configuration update request
 */
export interface VoiceConfigUpdate {
  config: Record<string, any>;
  validate_only?: boolean;
}

/**
 * Health status
 */
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  elevenlabs_connected: boolean;
  config_loaded: boolean;
  timestamp: string;
  details?: Record<string, any>;
}

/**
 * Voice API client for interacting with backend voice endpoints
 */
export class VoiceApiClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(baseUrl?: string, apiKey?: string) {
    // Use provided values or fall back to environment variables
    // This matches the initialization in api-client.ts
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    this.apiKey = apiKey || process.env.NEXT_PUBLIC_API_KEY || '';
    console.log('[VoiceApiClient] Initialized with baseUrl:', this.baseUrl);
  }

  /**
   * Get headers for API requests
   */
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    return headers;
  }

  /**
   * Get headers for multipart/form-data requests
   */
  private getMultipartHeaders(): HeadersInit {
    const headers: HeadersInit = {};

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    // Don't set Content-Type - browser will set it with boundary
    return headers;
  }

  /**
   * Transcribe audio file to text
   *
   * @param audioBlob - Audio file as Blob
   * @param options - Optional transcription settings
   * @returns Transcription result with text and timestamps
   */
  async transcribe(
    audioBlob: Blob,
    options?: {
      languageCode?: string;
      tagAudioEvents?: boolean;
    }
  ): Promise<TranscriptResponse> {
    console.log('[VoiceApiClient] transcribe called, blob size:', audioBlob.size, 'type:', audioBlob.type);
    
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const url = new URL(`${this.baseUrl}/voice/transcribe`);
    if (options?.languageCode) {
      url.searchParams.append('language_code', options.languageCode);
    }
    if (options?.tagAudioEvents !== undefined) {
      url.searchParams.append('tag_audio_events', String(options.tagAudioEvents));
    }

    console.log('[VoiceApiClient] Sending transcribe request to:', url.toString());

    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: this.getMultipartHeaders(),
      body: formData,
    });

    console.log('[VoiceApiClient] Transcribe response status:', response.status);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      console.error('[VoiceApiClient] Transcribe error:', error);
      throw new Error(error.detail?.message || error.error || 'Transcription failed');
    }

    const result = await response.json();
    console.log('[VoiceApiClient] Transcribe result:', result);
    return result;
  }

  /**
   * Synthesize text to speech
   *
   * @param request - Synthesis request with text and settings
   * @returns Audio blob
   */
  async synthesize(request: SynthesizeRequest): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/voice/synthesize`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.detail?.message || error.error || 'Synthesis failed');
    }

    return response.blob();
  }

  /**
   * Stream synthesized speech (Server-Sent Events)
   *
   * @param request - Synthesis request
   * @returns Async iterator of audio chunks
   */
  async *synthesizeStream(request: SynthesizeRequest): AsyncGenerator<Uint8Array, void, unknown> {
    const response = await fetch(`${this.baseUrl}/voice/synthesize/stream`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.detail?.message || error.error || 'Streaming synthesis failed');
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        yield value;
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * List all available voices
   *
   * @param refresh - Force refresh from API (bypass cache)
   * @returns List of available voices
   */
  async listVoices(refresh = false): Promise<VoiceInfo[]> {
    const url = new URL(`${this.baseUrl}/voice/voices`);
    if (refresh) {
      url.searchParams.append('refresh', 'true');
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.detail?.message || error.error || 'Failed to list voices');
    }

    return response.json();
  }

  /**
   * Get details for a specific voice
   *
   * @param voiceId - Voice ID
   * @returns Voice information
   */
  async getVoice(voiceId: string): Promise<VoiceInfo> {
    const response = await fetch(`${this.baseUrl}/voice/voices/${voiceId}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.detail?.message || error.error || 'Failed to get voice');
    }

    return response.json();
  }

  /**
   * Get current voice configuration
   *
   * @returns Voice configuration
   */
  async getConfig(): Promise<VoiceConfigResponse> {
    const response = await fetch(`${this.baseUrl}/voice/config`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.detail?.message || error.error || 'Failed to get config');
    }

    return response.json();
  }

  /**
   * Update voice configuration
   *
   * @param update - Configuration update
   * @returns Updated configuration
   */
  async updateConfig(update: VoiceConfigUpdate): Promise<VoiceConfigResponse> {
    const response = await fetch(`${this.baseUrl}/voice/config`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(update),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.detail?.message || error.error || 'Failed to update config');
    }

    return response.json();
  }

  /**
   * Check voice service health
   *
   * @returns Health status
   */
  async healthCheck(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/voice/health`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      // Health endpoint may return unhealthy status with 200
      // But if it's a hard failure, parse error
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.detail?.message || error.error || 'Health check failed');
    }

    return response.json();
  }
}

/**
 * Singleton instance
 */
let voiceApiClientInstance: VoiceApiClient | null = null;

/**
 * Get or create VoiceApiClient singleton instance
 */
export function getVoiceApiClient(): VoiceApiClient {
  if (!voiceApiClientInstance) {
    console.log('[VoiceApiClient] Creating singleton instance');
    voiceApiClientInstance = new VoiceApiClient();
  }
  return voiceApiClientInstance;
}

/**
 * Reset singleton instance (for testing)
 */
export function resetVoiceApiClient(): void {
  voiceApiClientInstance = null;
}
