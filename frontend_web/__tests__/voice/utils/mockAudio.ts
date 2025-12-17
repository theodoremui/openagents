/**
 * Mock Audio API for testing audio playback functionality.
 *
 * Provides realistic simulation of HTML Audio element.
 */

export interface MockAudioOptions {
  autoPlay?: boolean;
  shouldFail?: boolean;
  duration?: number;
  errorMessage?: string;
}

export class MockAudio implements Partial<HTMLAudioElement> {
  private _src = '';
  currentTime = 0;
  duration = 100;
  volume = 1;
  playbackRate = 1;
  paused = true;
  ended = false;
  muted = false;
  loop = false;
  preload: "" | "metadata" | "none" | "auto" = 'metadata';
  error: MediaError | null = null;

  onplay: ((this: GlobalEventHandlers, ev: Event) => any) | null = null;
  onpause: ((this: GlobalEventHandlers, ev: Event) => any) | null = null;
  onended: ((this: GlobalEventHandlers, ev: Event) => any) | null = null;
  onerror: OnErrorEventHandler | null = null;
  onloadedmetadata: ((this: GlobalEventHandlers, ev: Event) => any) | null = null;
  ontimeupdate: ((this: GlobalEventHandlers, ev: Event) => any) | null = null;
  onloadstart: ((this: GlobalEventHandlers, ev: Event) => any) | null = null;
  oncanplay: ((this: GlobalEventHandlers, ev: Event) => any) | null = null;

  private listeners: Record<string, Function[]> = {};
  private playInterval?: NodeJS.Timeout;
  private options: MockAudioOptions;

  constructor(src?: string, options?: MockAudioOptions) {
    this.options = options || {};
    if (options?.duration !== undefined) {
      this.duration = options.duration;
    }

    if (src) {
      this._src = src;
      this.simulateLoading();
    }
  }

  private simulateLoading(): void {
    // Simulate loadstart
    setTimeout(() => {
      if (this.onloadstart) {
        this.onloadstart.call(this as any, new Event('loadstart'));
      }
      this.dispatchEvent(new Event('loadstart'));
    }, 5);

    // Simulate metadata loaded
    setTimeout(() => {
      if (this.onloadedmetadata) {
        this.onloadedmetadata.call(this as any, new Event('loadedmetadata'));
      }
      this.dispatchEvent(new Event('loadedmetadata'));
    }, 10);

    // Simulate can play
    setTimeout(() => {
      if (this.oncanplay) {
        this.oncanplay.call(this as any, new Event('canplay'));
      }
      this.dispatchEvent(new Event('canplay'));
    }, 15);
  }

  play(): Promise<void> {
    if (this.options.shouldFail) {
      return Promise.reject(new Error(this.options.errorMessage || 'Play failed'));
    }

    this.paused = false;
    this.ended = false;

    if (this.onplay) {
      this.onplay.call(this as any, new Event('play'));
    }
    this.dispatchEvent(new Event('play'));

    // Simulate playback progress
    this.playInterval = setInterval(() => {
      if (!this.paused && this.currentTime < this.duration) {
        this.currentTime += 0.1;

        if (this.ontimeupdate) {
          this.ontimeupdate.call(this as any, new Event('timeupdate'));
        }
        this.dispatchEvent(new Event('timeupdate'));

        // Check if ended
        if (this.currentTime >= this.duration) {
          this.handleEnded();
        }
      }
    }, 100);

    return Promise.resolve();
  }

  pause(): void {
    this.paused = true;

    if (this.playInterval) {
      clearInterval(this.playInterval);
    }

    if (this.onpause) {
      this.onpause.call(this as any, new Event('pause'));
    }
    this.dispatchEvent(new Event('pause'));
  }

  load(): void {
    this.currentTime = 0;
    this.paused = true;
    this.ended = false;
    this.simulateLoading();
  }

  // Allow setting src dynamically (used by useAudioPlayer)
  set src(value: string) {
    this._src = value;
    if (value) {
      this.simulateLoading();
    }
  }

  get src(): string {
    return this._src;
  }

  private handleEnded(): void {
    this.paused = true;
    this.ended = true;

    if (this.playInterval) {
      clearInterval(this.playInterval);
    }

    if (this.onended) {
      this.onended.call(this as any, new Event('ended'));
    }
    this.dispatchEvent(new Event('ended'));
  }

  addEventListener(type: string, listener: EventListener): void {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(listener);
  }

  removeEventListener(type: string, listener: EventListener): void {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter((l) => l !== listener);
    }
  }

  dispatchEvent(event: Event): boolean {
    if (this.listeners[event.type]) {
      this.listeners[event.type].forEach((listener) => listener(event));
    }
    return true;
  }
}

// Store current options for mock
let currentMockOptions: MockAudioOptions = {};

/**
 * Setup Audio mock in global scope.
 * 
 * IMPORTANT: This completely replaces global.Audio. Call this in beforeEach
 * and call resetAudioMocks() in afterEach.
 */
export function setupAudioMock(defaultOptions?: MockAudioOptions) {
  currentMockOptions = defaultOptions || {};
  
  // Create mock that works with 'new' keyword
  (global as any).Audio = function(this: any, src?: string) {
    return new MockAudio(src, currentMockOptions);
  };

  return (global as any).Audio;
}

/**
 * Setup URL.createObjectURL and revokeObjectURL mocks.
 */
export function setupURLMocks() {
  const objectURLs = new Set<string>();

  global.URL.createObjectURL = jest.fn((blob: Blob) => {
    const url = `blob:mock-${Math.random().toString(36).substr(2, 9)}`;
    objectURLs.add(url);
    return url;
  });

  global.URL.revokeObjectURL = jest.fn((url: string) => {
    objectURLs.delete(url);
  });

  return { objectURLs };
}

/**
 * Reset audio mocks.
 * 
 * Note: This clears the mock options but keeps a basic Audio mock in place
 * to prevent tests from failing if beforeEach doesn't run for some reason.
 */
export function resetAudioMocks() {
  jest.clearAllMocks();
  currentMockOptions = {};
  
  // Reset to a default Audio mock (not deleted, just reset)
  // This prevents issues if beforeEach doesn't run properly
  (global as any).Audio = function(this: any, src?: string) {
    return new MockAudio(src, {});
  };

  // Reset URL mocks
  global.URL.createObjectURL = jest.fn();
  global.URL.revokeObjectURL = jest.fn();
}
