/**
 * Mock MediaRecorder for testing audio recording functionality.
 *
 * Provides realistic simulation of browser MediaRecorder API.
 */

export type RecordingState = 'inactive' | 'recording' | 'paused';

export interface MockMediaRecorderOptions {
  autoDataAvailable?: boolean;
  dataChunkSize?: number;
  simulateError?: boolean;
  errorMessage?: string;
}

export class MockMediaRecorder implements Partial<MediaRecorder> {
  state: RecordingState = 'inactive';
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: ((error: Event) => void) | null = null;
  onstart: (() => void) | null = null;
  onpause: (() => void) | null = null;
  onresume: (() => void) | null = null;

  private options: MockMediaRecorderOptions;
  private dataIntervalId?: NodeJS.Timeout;
  private chunks: Blob[] = [];

  constructor(
    public stream: MediaStream,
    options?: MediaRecorderOptions & MockMediaRecorderOptions
  ) {
    this.options = options || {};
  }

  start(timeslice?: number): void {
    if (this.state !== 'inactive') {
      throw new Error('InvalidStateError');
    }

    // Set state first so handlers can be attached
    this.state = 'recording';
    this.chunks = [];

    if (this.onstart) {
      this.onstart();
    }

    // Simulate error after a short delay if configured
    if (this.options.simulateError) {
      // Use setImmediate so the error fires after handlers are attached
      setImmediate(() => {
        this.state = 'inactive';
        if (this.onerror) {
          const errorEvent = new Event('error') as any;
          errorEvent.error = new Error(this.options.errorMessage || 'Recording error');
          this.onerror(errorEvent);
        }
      });
      return;
    }

    // Simulate data available events
    if (this.options.autoDataAvailable !== false) {
      const interval = timeslice || 100;
      this.dataIntervalId = setInterval(() => {
        if (this.state === 'recording' && this.ondataavailable) {
          const blob = new Blob(
            [new Uint8Array(this.options.dataChunkSize || 1024)],
            { type: 'audio/webm' }
          );
          this.chunks.push(blob);
          this.ondataavailable({ data: blob } as BlobEvent);
        }
      }, interval);
    }
  }

  stop(): void {
    // Safe to call even if already inactive (important for cleanup)
    if (this.state === 'inactive') {
      return; // No-op instead of throwing
    }

    if (this.dataIntervalId) {
      clearInterval(this.dataIntervalId);
      this.dataIntervalId = undefined;
    }

    this.state = 'inactive';

    // Send final data if available
    if (this.ondataavailable && this.chunks.length > 0) {
      const finalBlob = new Blob(this.chunks, { type: 'audio/webm' });
      this.ondataavailable({ data: finalBlob } as BlobEvent);
    }

    // Call onstop synchronously for test predictability
    if (this.onstop) {
      this.onstop();
    }
  }

  pause(): void {
    if (this.state !== 'recording') {
      throw new Error('InvalidStateError');
    }

    this.state = 'paused';

    if (this.onpause) {
      this.onpause();
    }
  }

  resume(): void {
    if (this.state !== 'paused') {
      throw new Error('InvalidStateError');
    }

    this.state = 'recording';

    if (this.onresume) {
      this.onresume();
    }
  }

  requestData(): void {
    if (this.state === 'inactive') {
      throw new Error('InvalidStateError');
    }

    if (this.ondataavailable && this.chunks.length > 0) {
      const blob = new Blob(this.chunks, { type: 'audio/webm' });
      this.ondataavailable({ data: blob } as BlobEvent);
    }
  }

  addEventListener(type: string, listener: EventListener): void {
    // Simple implementation
    if (type === 'dataavailable') {
      this.ondataavailable = listener as any;
    } else if (type === 'stop') {
      this.onstop = listener as any;
    } else if (type === 'error') {
      this.onerror = listener as any;
    } else if (type === 'start') {
      this.onstart = listener as any;
    }
  }

  removeEventListener(type: string, listener: EventListener): void {
    if (type === 'dataavailable' && this.ondataavailable === listener) {
      this.ondataavailable = null;
    } else if (type === 'stop' && this.onstop === listener) {
      this.onstop = null;
    }
  }
}

/**
 * Supported MIME types for testing
 */
const SUPPORTED_MIME_TYPES = [
  'audio/webm',
  'audio/webm;codecs=opus',
  'audio/webm; codecs=opus',
  'audio/ogg',
  'audio/wav',
  'audio/mp4',
];

/**
 * Setup MediaRecorder mock in global scope.
 */
export function setupMediaRecorderMock(options?: MockMediaRecorderOptions) {
  const mockRecorder = new MockMediaRecorder({} as MediaStream, options);

  global.MediaRecorder = jest.fn((stream: MediaStream, opts?: MediaRecorderOptions) => {
    return new MockMediaRecorder(stream, { ...opts, ...options });
  }) as any;

  (global.MediaRecorder as any).isTypeSupported = jest.fn((mimeType: string) => {
    // Normalize the mimeType for comparison (remove spaces)
    const normalized = mimeType.replace(/\s+/g, '').toLowerCase();
    return SUPPORTED_MIME_TYPES.some(supported => 
      supported.replace(/\s+/g, '').toLowerCase() === normalized
    );
  });

  return mockRecorder;
}

/**
 * Setup getUserMedia mock.
 */
export function setupGetUserMediaMock(shouldSucceed: boolean = true) {
  const mockStream = {
    getTracks: jest.fn(() => [
      {
        stop: jest.fn(),
        kind: 'audio',
        enabled: true,
        id: 'mock-track-1',
      },
    ]),
    getAudioTracks: jest.fn(() => [
      {
        stop: jest.fn(),
        kind: 'audio',
        enabled: true,
      },
    ]),
  } as unknown as MediaStream;

  // Ensure navigator.mediaDevices exists
  if (!global.navigator) {
    (global as any).navigator = {};
  }

  Object.defineProperty(global.navigator, 'mediaDevices', {
    value: {
      getUserMedia: jest.fn(() => {
      if (shouldSucceed) {
        return Promise.resolve(mockStream);
      } else {
        const error = new Error('Permission denied');
        (error as any).name = 'NotAllowedError';
        return Promise.reject(error);
      }
    }),
    },
    writable: true,
    configurable: true,
  });

  return mockStream;
}

/**
 * Setup AudioContext mock for audio level monitoring.
 */
export function setupAudioContextMock() {
  const mockAnalyser = {
    fftSize: 2048,
    frequencyBinCount: 1024,
    getByteTimeDomainData: jest.fn((array: Uint8Array) => {
      // Simulate audio levels
      for (let i = 0; i < array.length; i++) {
        array[i] = 128 + Math.random() * 20; // Around 128 with some variation
      }
    }),
    getByteFrequencyData: jest.fn((array: Uint8Array) => {
      // Simulate frequency data
      for (let i = 0; i < array.length; i++) {
        array[i] = Math.floor(Math.random() * 128);
      }
    }),
    connect: jest.fn(),
    disconnect: jest.fn(),
  };

  const mockSource = {
    connect: jest.fn(),
    disconnect: jest.fn(),
  };

  const mockContext = {
    createAnalyser: jest.fn(() => mockAnalyser),
    createMediaStreamSource: jest.fn(() => mockSource),
    createMediaElementSource: jest.fn(() => mockSource),
    close: jest.fn().mockResolvedValue(undefined),
    state: 'running',
  };

  (global as any).AudioContext = jest.fn(() => mockContext);
  (global as any).webkitAudioContext = jest.fn(() => mockContext);

  return { mockContext, mockAnalyser, mockSource };
}

/**
 * Reset all media mocks.
 */
export function resetMediaMocks() {
  jest.clearAllMocks();

  if ((global as any).MediaRecorder) {
    delete (global as any).MediaRecorder;
  }

  if (global.navigator?.mediaDevices) {
    delete (global.navigator as any).mediaDevices;
  }

  if ((global as any).AudioContext) {
    delete (global as any).AudioContext;
  }

  if ((global as any).webkitAudioContext) {
    delete (global as any).webkitAudioContext;
  }
}
