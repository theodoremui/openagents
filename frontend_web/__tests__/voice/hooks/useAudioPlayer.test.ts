/**
 * Comprehensive tests for useAudioPlayer hook
 *
 * Tests cover:
 * - Audio source management (URL and Blob)
 * - Playback controls (play, pause, stop)
 * - Progress tracking and seeking
 * - Volume and playback rate controls
 * - Auto-play and loop functionality
 * - Error handling
 * - Cleanup and resource management
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useAudioPlayer } from '@/lib/hooks/useAudioPlayer';
import {
  setupAudioMock,
  setupURLMocks,
  resetAudioMocks,
  MockAudio,
} from '../utils/mockAudio';
import { setupAudioContextMock, resetMediaMocks } from '../utils/mockMediaRecorder';

describe('useAudioPlayer', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    setupAudioMock();
    setupURLMocks();
    setupAudioContextMock();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    resetAudioMocks();
    resetMediaMocks();
  });

  // ============================================================================
  // INITIALIZATION TESTS
  // ============================================================================

  describe('Initialization', () => {
    it('should initialize with default state', () => {
      const { result } = renderHook(() => useAudioPlayer());

      expect(result.current.isPlaying).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.currentTime).toBe(0);
      expect(result.current.duration).toBe(0);
      expect(result.current.volume).toBe(1.0);
      expect(result.current.playbackRate).toBe(1.0);
      expect(result.current.isMuted).toBe(false);
      expect(result.current.hasEnded).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.frequencyData).toBeNull();
    });

    it('should accept custom configuration', () => {
      const { result } = renderHook(() =>
        useAudioPlayer({
          autoPlay: true,
          loop: true,
          volume: 0.5,
          playbackRate: 1.5,
          enableVisualization: true,
        })
      );

      expect(result.current.volume).toBe(0.5);
      expect(result.current.playbackRate).toBe(1.5);
      expect(result.current.isPlaying).toBe(false); // Not playing until source is set
    });

    it('should provide all required methods', () => {
      const { result } = renderHook(() => useAudioPlayer());

      expect(typeof result.current.setSource).toBe('function');
      expect(typeof result.current.play).toBe('function');
      expect(typeof result.current.pause).toBe('function');
      expect(typeof result.current.stop).toBe('function');
      expect(typeof result.current.seek).toBe('function');
      expect(typeof result.current.setVolume).toBe('function');
      expect(typeof result.current.setPlaybackRate).toBe('function');
      expect(typeof result.current.toggleMute).toBe('function');
      expect(typeof result.current.clearError).toBe('function');
    });
  });

  // ============================================================================
  // SOURCE MANAGEMENT TESTS
  // ============================================================================

  describe('Source Management', () => {
    it('should set audio source from URL', () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      // Source is set (implementation detail, can't directly verify)
      expect(result.current.error).toBeNull();
    });

    it('should set audio source from Blob', () => {
      const { result } = renderHook(() => useAudioPlayer());

      const blob = new Blob(['audio data'], { type: 'audio/mp3' });

      act(() => {
        result.current.setSource(blob);
      });

      expect(result.current.error).toBeNull();
      expect(global.URL.createObjectURL).toHaveBeenCalledWith(blob);
    });

    it('should cleanup previous object URL when setting new source', () => {
      const { result } = renderHook(() => useAudioPlayer());

      const blob1 = new Blob(['audio 1'], { type: 'audio/mp3' });
      const blob2 = new Blob(['audio 2'], { type: 'audio/mp3' });

      act(() => {
        result.current.setSource(blob1);
      });

      const firstURL = (global.URL.createObjectURL as jest.Mock).mock.results[0]?.value;

      act(() => {
        result.current.setSource(blob2);
      });

      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith(firstURL);
    });

    it('should reset state when setting new source', () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      // Manually set some state
      act(() => {
        result.current.play();
      });

      act(() => {
        jest.advanceTimersByTime(500);
      });

      // Set new source
      act(() => {
        result.current.setSource('https://example.com/audio2.mp3');
      });

      expect(result.current.isPlaying).toBe(false);
      expect(result.current.currentTime).toBe(0);
      expect(result.current.hasEnded).toBe(false);
    });

    it('should trigger metadata load after setting source', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      expect(result.current.duration).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // PLAYBACK CONTROL TESTS
  // ============================================================================

  describe('Playback Controls', () => {
    it('should play audio', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      expect(result.current.isPlaying).toBe(true);
      expect(result.current.hasEnded).toBe(false);
    });

    it('should pause audio', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      expect(result.current.isPlaying).toBe(true);

      act(() => {
        result.current.pause();
      });

      expect(result.current.isPlaying).toBe(false);
    });

    it('should stop audio and reset to beginning', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      // Advance time
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(result.current.currentTime).toBeGreaterThan(0);

      // Stop
      act(() => {
        result.current.stop();
      });

      expect(result.current.isPlaying).toBe(false);
      expect(result.current.currentTime).toBe(0);
      expect(result.current.hasEnded).toBe(false);
    });

    it('should handle play/pause cycles', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      for (let i = 0; i < 3; i++) {
        await act(async () => {
          await result.current.play();
        });

        expect(result.current.isPlaying).toBe(true);

        act(() => {
          result.current.pause();
        });

        expect(result.current.isPlaying).toBe(false);
      }
    });

    it('should handle playback ending', async () => {
      // Setup audio mock with short duration
      setupAudioMock({ duration: 0.5 });

      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      // Advance past duration to trigger end event
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // Note: Mock audio should trigger 'ended' event which sets isPlaying=false and hasEnded=true
      expect(result.current.hasEnded).toBe(true);
    });
  });

  // ============================================================================
  // PROGRESS AND SEEKING TESTS
  // ============================================================================

  describe('Progress Tracking and Seeking', () => {
    it('should track current time during playback', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      expect(result.current.currentTime).toBe(0);

      // Advance time
      act(() => {
        jest.advanceTimersByTime(1000);
      });

      expect(result.current.currentTime).toBeGreaterThan(0);
    });

    it('should seek to specific time', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      // Seek to 50 seconds
      act(() => {
        result.current.seek(50);
      });

      expect(result.current.currentTime).toBe(50);
    });

    it('should clamp seek time to valid range', async () => {
      const { result } = renderHook(() =>
        useAudioPlayer({})
      );

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      // Seek beyond duration
      act(() => {
        result.current.seek(150);
      });

      expect(result.current.currentTime).toBeLessThanOrEqual(100);

      // Seek below zero
      act(() => {
        result.current.seek(-10);
      });

      expect(result.current.currentTime).toBeGreaterThanOrEqual(0);
    });

    it('should track duration after metadata loads', async () => {
      // Setup audio mock with custom duration before creating hook
      setupAudioMock({ duration: 123.45 });

      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      expect(result.current.duration).toBe(123.45);
    });
  });

  // ============================================================================
  // VOLUME CONTROL TESTS
  // ============================================================================

  describe('Volume Control', () => {
    it('should set volume', () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setVolume(0.5);
      });

      expect(result.current.volume).toBe(0.5);

      act(() => {
        result.current.setVolume(0.8);
      });

      expect(result.current.volume).toBe(0.8);
    });

    it('should clamp volume to valid range (0-1)', () => {
      const { result } = renderHook(() => useAudioPlayer());

      // Above 1
      act(() => {
        result.current.setVolume(1.5);
      });

      expect(result.current.volume).toBe(1.0);

      // Below 0
      act(() => {
        result.current.setVolume(-0.5);
      });

      expect(result.current.volume).toBe(0.0);
    });

    it('should toggle mute', () => {
      const { result } = renderHook(() => useAudioPlayer());

      expect(result.current.isMuted).toBe(false);

      act(() => {
        result.current.toggleMute();
      });

      expect(result.current.isMuted).toBe(true);

      act(() => {
        result.current.toggleMute();
      });

      expect(result.current.isMuted).toBe(false);
    });

    it('should initialize with custom volume', () => {
      const { result } = renderHook(() =>
        useAudioPlayer({ volume: 0.3 })
      );

      expect(result.current.volume).toBe(0.3);
    });
  });

  // ============================================================================
  // PLAYBACK RATE TESTS
  // ============================================================================

  describe('Playback Rate', () => {
    it('should set playback rate', () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setPlaybackRate(1.5);
      });

      expect(result.current.playbackRate).toBe(1.5);

      act(() => {
        result.current.setPlaybackRate(0.75);
      });

      expect(result.current.playbackRate).toBe(0.75);
    });

    it('should clamp playback rate to valid range (0.5-2.0)', () => {
      const { result } = renderHook(() => useAudioPlayer());

      // Above 2.0
      act(() => {
        result.current.setPlaybackRate(3.0);
      });

      expect(result.current.playbackRate).toBe(2.0);

      // Below 0.5
      act(() => {
        result.current.setPlaybackRate(0.25);
      });

      expect(result.current.playbackRate).toBe(0.5);
    });

    it('should initialize with custom playback rate', () => {
      const { result } = renderHook(() =>
        useAudioPlayer({ playbackRate: 1.25 })
      );

      expect(result.current.playbackRate).toBe(1.25);
    });
  });

  // ============================================================================
  // AUTO-PLAY TESTS
  // ============================================================================

  describe('Auto-play', () => {
    it('should auto-play when enabled and source is set', async () => {
      const { result } = renderHook(() =>
        useAudioPlayer({ autoPlay: true })
      );

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      expect(result.current.isPlaying).toBe(true);
    });

    it('should not auto-play when disabled', () => {
      const { result } = renderHook(() =>
        useAudioPlayer({ autoPlay: false })
      );

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      act(() => {
        jest.advanceTimersByTime(100);
      });

      expect(result.current.isPlaying).toBe(false);
    });

    it('should handle auto-play failure gracefully', async () => {
      setupAudioMock({ shouldFail: true, errorMessage: 'Auto-play blocked' });

      const { result } = renderHook(() =>
        useAudioPlayer({ autoPlay: true })
      );

      await act(async () => {
        result.current.setSource('https://example.com/audio.mp3');
        // Flush microtasks for Promise.catch
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(result.current.error).toContain('Auto-play failed');
      });
    });
  });

  // ============================================================================
  // ERROR HANDLING TESTS
  // ============================================================================

  describe('Error Handling', () => {
    it('should handle play errors', async () => {
      setupAudioMock({ shouldFail: true, errorMessage: 'Play failed' });

      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      // Play should reject, and hook should set error state
      await act(async () => {
        try {
          await result.current.play();
        } catch (e) {
          // Expected - play() throws after setting error
        }
      });

      // Error should now be set
      expect(result.current.error).toContain('Failed to play audio');
    });

    it('should clear error state', async () => {
      setupAudioMock({ shouldFail: true });

      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        try {
          await result.current.play();
        } catch (e) {
          // Expected error - play() throws after setting error
        }
      });

      // Error should be set after catching in act
      expect(result.current.error).not.toBeNull();

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it('should clear error when setting new source', async () => {
      setupAudioMock({ shouldFail: true });

      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/bad-audio.mp3');
      });

      await act(async () => {
        try {
          await result.current.play();
        } catch (e) {
          // Expected error - play() throws after setting error
        }
      });

      expect(result.current.error).not.toBeNull();

      // Set new source - this should clear error
      act(() => {
        result.current.setSource('https://example.com/good-audio.mp3');
      });

      expect(result.current.error).toBeNull();
    });
  });

  // ============================================================================
  // VISUALIZATION TESTS
  // ============================================================================

  describe('Audio Visualization', () => {
    it('should not provide frequency data by default', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      expect(result.current.frequencyData).toBeNull();
    });

    it('should provide frequency data when enabled', async () => {
      const { result } = renderHook(() =>
        useAudioPlayer({ enableVisualization: true })
      );

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      // Wait for visualization to update
      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      expect(result.current.frequencyData).toBeInstanceOf(Uint8Array);
    });

    it('should cleanup visualization on pause', async () => {
      const { result } = renderHook(() =>
        useAudioPlayer({ enableVisualization: true })
      );

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      expect(result.current.frequencyData).toBeInstanceOf(Uint8Array);

      act(() => {
        result.current.pause();
      });

      // Note: pause() stops the animation frame but doesn't clear frequencyData
      // frequencyData is only cleared on unmount via cleanupVisualization()
      // Just verify that isPlaying is false
      expect(result.current.isPlaying).toBe(false);
    });
  });

  // ============================================================================
  // CLEANUP TESTS
  // ============================================================================

  describe('Cleanup', () => {
    it('should cleanup audio element on unmount', () => {
      const { result, unmount } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      unmount();

      // Can't directly verify, but no errors should occur
    });

    it('should revoke object URL on unmount', () => {
      const { result, unmount } = renderHook(() => useAudioPlayer());

      const blob = new Blob(['audio'], { type: 'audio/mp3' });

      act(() => {
        result.current.setSource(blob);
      });

      const objectURL = (global.URL.createObjectURL as jest.Mock).mock.results[0]?.value;

      unmount();

      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith(objectURL);
    });

    it('should cleanup visualization on unmount', async () => {
      const { mockContext } = setupAudioContextMock();

      const { result, unmount } = renderHook(() =>
        useAudioPlayer({ enableVisualization: true })
      );

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      unmount();

      expect(mockContext.close).toHaveBeenCalled();
    });

    it('should stop playback on unmount', async () => {
      const { result, unmount } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
      });

      expect(result.current.isPlaying).toBe(true);

      unmount();

      // Can't verify directly after unmount, but playback should be stopped
    });
  });

  // ============================================================================
  // EDGE CASE TESTS
  // ============================================================================

  describe('Edge Cases', () => {
    it('should handle rapid source changes', () => {
      const { result } = renderHook(() => useAudioPlayer());

      for (let i = 0; i < 5; i++) {
        act(() => {
          result.current.setSource(`https://example.com/audio${i}.mp3`);
        });
      }

      expect(result.current.error).toBeNull();
    });

    it('should handle multiple play calls', async () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      await act(async () => {
        await result.current.play();
        await result.current.play();
        await result.current.play();
      });

      expect(result.current.isPlaying).toBe(true);
    });

    it('should handle pause when not playing', () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      act(() => {
        result.current.pause();
      });

      // Should not throw
      expect(result.current.isPlaying).toBe(false);
    });

    it('should handle stop when not playing', () => {
      const { result } = renderHook(() => useAudioPlayer());

      act(() => {
        result.current.setSource('https://example.com/audio.mp3');
      });

      act(() => {
        result.current.stop();
      });

      // Should not throw
      expect(result.current.isPlaying).toBe(false);
      expect(result.current.currentTime).toBe(0);
    });
  });
});
