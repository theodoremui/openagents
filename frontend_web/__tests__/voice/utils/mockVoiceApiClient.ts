/**
 * Mock VoiceApiClient for testing.
 *
 * Provides jest.Mocked version of VoiceApiClient with realistic responses.
 */

import { VoiceApiClient } from '@/lib/services/VoiceApiClient';
import type {
  TranscriptResponse,
  SynthesizeRequest,
  VoiceInfo,
  HealthResponse,
} from '@/lib/services/VoiceApiClient';

/**
 * Create mock VoiceApiClient with default responses.
 */
export function createMockVoiceApiClient(): jest.Mocked<VoiceApiClient> {
  const mockClient = {
    transcribe: jest.fn(),
    synthesize: jest.fn(),
    synthesizeStream: jest.fn(),
    listVoices: jest.fn(),
    getVoice: jest.fn(),
    getConfig: jest.fn(),
    updateConfig: jest.fn(),
    healthCheck: jest.fn(),
  } as unknown as jest.Mocked<VoiceApiClient>;

  // Default successful responses
  mockClient.transcribe.mockResolvedValue({
    success: true,
    result: {
      text: 'Mock transcription result',
      words: [
        { word: 'Mock', start: 0.0, end: 0.4 },
        { word: 'transcription', start: 0.4, end: 1.2 },
        { word: 'result', start: 1.2, end: 1.8 },
      ],
      confidence: 0.95,
      language_detected: 'en',
    },
    request_id: 'mock-request-id',
    processing_time_ms: 100,
  });

  mockClient.synthesize.mockResolvedValue(
    new Blob(['mock audio data'], { type: 'audio/mpeg' })
  );

  mockClient.synthesizeStream.mockImplementation(async function* () {
    yield new Uint8Array([1, 2, 3, 4, 5]);
    yield new Uint8Array([6, 7, 8, 9, 10]);
    yield new Uint8Array([11, 12, 13, 14, 15]);
  });

  mockClient.listVoices.mockResolvedValue([
    {
      voice_id: 'mock_voice_1',
      name: 'Mock Voice 1',
      category: 'premade',
      description: 'A mock voice for testing',
      labels: { accent: 'american', age: 'middle-aged', gender: 'female' },
    },
    {
      voice_id: 'mock_voice_2',
      name: 'Mock Voice 2',
      category: 'cloned',
      description: 'Another mock voice',
      labels: { accent: 'british', age: 'young', gender: 'male' },
    },
  ]);

  mockClient.getVoice.mockResolvedValue({
    voice_id: 'mock_voice_1',
    name: 'Mock Voice 1',
    category: 'premade',
    description: 'A mock voice for testing',
  });

  mockClient.getConfig.mockResolvedValue({
    config: {
      enabled: true,
      tts: {
        voice_id: 'default_voice',
        model_id: 'eleven_multilingual_v2',
        stability: 0.5,
        similarity_boost: 0.75,
      },
      stt: {
        model_id: 'scribe_v1',
      },
    },
    last_updated: new Date().toISOString(),
    validation: {
      valid: true,
      errors: [],
      warnings: [],
    },
  });

  mockClient.healthCheck.mockResolvedValue({
    status: 'healthy',
    elevenlabs_connected: true,
    config_loaded: true,
    timestamp: new Date().toISOString(),
  });

  return mockClient;
}

/**
 * Create mock VoiceApiClient that fails with errors.
 */
export function createFailingMockVoiceApiClient(errorMessage: string = 'API Error') {
  const mockClient = createMockVoiceApiClient();

  mockClient.transcribe.mockRejectedValue(new Error(errorMessage));
  mockClient.synthesize.mockRejectedValue(new Error(errorMessage));
  mockClient.synthesizeStream.mockImplementation(async function* () {
    throw new Error(errorMessage);
  });
  mockClient.listVoices.mockRejectedValue(new Error(errorMessage));

  return mockClient;
}

/**
 * Create mock fetch for API client integration tests.
 */
export function setupFetchMock() {
  const mockFetch = jest.fn();

  global.fetch = mockFetch as any;

  // Default successful responses
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    const urlString = url.toString();

    // Transcribe endpoint
    if (urlString.includes('/voice/transcribe')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          result: {
            text: 'Fetch mock transcription',
            words: [],
            confidence: 0.9,
          },
        }),
      });
    }

    // Synthesize endpoint
    if (urlString.includes('/voice/synthesize')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        blob: async () => new Blob(['audio'], { type: 'audio/mpeg' }),
        headers: new Headers({ 'content-type': 'audio/mpeg' }),
      });
    }

    // List voices endpoint
    if (urlString.includes('/voice/voices')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [
          {
            voice_id: 'fetch_voice_1',
            name: 'Fetch Voice 1',
            category: 'premade',
          },
        ],
      });
    }

    // Health check endpoint
    if (urlString.includes('/voice/health')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          healthy: true,
          elevenlabs_connected: true,
        }),
      });
    }

    // Default response
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
  });

  return mockFetch;
}

/**
 * Reset fetch mock.
 */
export function resetFetchMock() {
  if (global.fetch && jest.isMockFunction(global.fetch)) {
    (global.fetch as jest.Mock).mockReset();
  }
}
