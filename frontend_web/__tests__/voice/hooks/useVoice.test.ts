/**
 * Comprehensive tests for useVoice hook
 *
 * Tests cover:
 * - Orchestration of useAudioRecorder + useAudioPlayer + VoiceContext
 * - Recording + transcription workflow
 * - Synthesis + playback workflow
 * - Auto-transcribe and auto-play features
 * - Error handling across all operations
 * - Settings integration
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useVoice } from '@/lib/hooks/useVoice';
import * as audioRecorderModule from '@/lib/hooks/useAudioRecorder';
import * as audioPlayerModule from '@/lib/hooks/useAudioPlayer';
import * as voiceContextModule from '@/lib/contexts/VoiceContext';
import { createMockVoiceApiClient } from '../utils/mockVoiceApiClient';

// Mock the hooks
jest.mock('@/lib/hooks/useAudioRecorder');
jest.mock('@/lib/hooks/useAudioPlayer');
jest.mock('@/lib/contexts/VoiceContext');

describe('useVoice', () => {
  let mockRecorder: any;
  let mockPlayer: any;
  let mockVoiceClient: any;
  let mockSettings: any;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();

    // Setup mock recorder
    mockRecorder = {
      isRecording: false,
      duration: 0,
      audioLevel: 0,
      hasPermission: true,
      isRequestingPermission: false,
      error: null,
      startRecording: jest.fn().mockResolvedValue(undefined),
      stopRecording: jest.fn().mockResolvedValue(new Blob(['audio'], { type: 'audio/webm' })),
      cancelRecording: jest.fn(),
      clearError: jest.fn(),
    };

    // Setup mock player
    mockPlayer = {
      isPlaying: false,
      isLoading: false,
      currentTime: 0,
      duration: 0,
      volume: 1.0,
      playbackRate: 1.0,
      isMuted: false,
      hasEnded: false,
      error: null,
      frequencyData: null,
      setSource: jest.fn(),
      play: jest.fn().mockResolvedValue(undefined),
      pause: jest.fn(),
      stop: jest.fn(),
      seek: jest.fn(),
      setVolume: jest.fn(),
      setPlaybackRate: jest.fn(),
      toggleMute: jest.fn(),
      clearError: jest.fn(),
    };

    // Setup mock voice client (fresh instance each time)
    mockVoiceClient = createMockVoiceApiClient();

    // Setup mock settings
    mockSettings = {
      sttEnabled: true,
      ttsEnabled: true,
      selectedVoiceId: 'default_voice',
      selectedProfile: 'default',
      volume: 0.8,
      playbackSpeed: 1.0,
    };

    // Mock the hooks with proper mocking
    jest.mocked(audioRecorderModule.useAudioRecorder).mockReturnValue(mockRecorder);
    jest.mocked(audioPlayerModule.useAudioPlayer).mockReturnValue(mockPlayer);
    jest.mocked(voiceContextModule.useVoiceClient).mockReturnValue(mockVoiceClient);
    jest.mocked(voiceContextModule.useVoiceSettings).mockReturnValue([mockSettings, jest.fn()]);
    jest.mocked(voiceContextModule.useVoiceContext).mockReturnValue({
      settings: mockSettings,
      updateSettings: jest.fn(),
      client: mockVoiceClient,
      voices: [],
      voicesLoading: false,
      voicesError: null,
      isHealthy: true,
      refreshVoices: jest.fn(),
      checkHealth: jest.fn(),
    });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  // ============================================================================
  // INITIALIZATION TESTS
  // ============================================================================

  describe('Initialization', () => {
    it('should initialize with state from sub-hooks', () => {
      const { result } = renderHook(() => useVoice());

      // Recording state from useAudioRecorder
      expect(result.current.isRecording).toBe(false);
      expect(result.current.recordingDuration).toBe(0);
      expect(result.current.audioLevel).toBe(0);
      expect(result.current.hasRecordingPermission).toBe(true);

      // Playback state from useAudioPlayer
      expect(result.current.isPlaying).toBe(false);
      expect(result.current.playbackCurrentTime).toBe(0);
      expect(result.current.playbackDuration).toBe(0);
      expect(result.current.playbackVolume).toBe(1.0);

      // Processing state
      expect(result.current.isTranscribing).toBe(false);
      expect(result.current.isSynthesizing).toBe(false);

      // Results
      expect(result.current.lastTranscript).toBeNull();
      expect(result.current.lastSynthesizedAudio).toBeNull();

      // Errors
      expect(result.current.recordingError).toBeNull();
      expect(result.current.playbackError).toBeNull();
      expect(result.current.transcriptionError).toBeNull();
      expect(result.current.synthesisError).toBeNull();
    });

    it('should provide all required methods', () => {
      const { result } = renderHook(() => useVoice());

      // Recording controls
      expect(typeof result.current.startRecording).toBe('function');
      expect(typeof result.current.stopRecording).toBe('function');
      expect(typeof result.current.cancelRecording).toBe('function');

      // Playback controls
      expect(typeof result.current.playAudio).toBe('function');
      expect(typeof result.current.pauseAudio).toBe('function');
      expect(typeof result.current.stopAudio).toBe('function');
      expect(typeof result.current.setVolume).toBe('function');

      // Voice operations
      expect(typeof result.current.transcribe).toBe('function');
      expect(typeof result.current.synthesize).toBe('function');
      expect(typeof result.current.speakText).toBe('function');

      // Combined workflows
      expect(typeof result.current.recordAndTranscribe).toBe('function');
      expect(typeof result.current.synthesizeAndPlay).toBe('function');

      // Error handling
      expect(typeof result.current.clearErrors).toBe('function');
    });

    it('should accept custom configuration', () => {
      const config = {
        recorderConfig: { maxDuration: 120 },
        playerConfig: { autoPlay: true },
        autoTranscribe: true,
        autoPlaySynthesis: true,
      };

      renderHook(() => useVoice(config));

      expect(audioRecorderModule.useAudioRecorder).toHaveBeenCalledWith(
        config.recorderConfig
      );
      expect(audioPlayerModule.useAudioPlayer).toHaveBeenCalledWith(
        config.playerConfig
      );
    });
  });

  // ============================================================================
  // RECORDING TESTS
  // ============================================================================

  describe('Recording', () => {
    it('should start recording', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(mockRecorder.startRecording).toHaveBeenCalled();
    });

    it('should stop recording and return audio blob', async () => {
      const mockBlob = new Blob(['audio'], { type: 'audio/webm' });
      mockRecorder.stopRecording.mockResolvedValue(mockBlob);

      const { result } = renderHook(() => useVoice());

      let blob: Blob | null = null;

      await act(async () => {
        blob = await result.current.stopRecording();
      });

      expect(mockRecorder.stopRecording).toHaveBeenCalled();
      expect(blob).toBe(mockBlob);
    });

    it('should cancel recording', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.cancelRecording();
      });

      expect(mockRecorder.cancelRecording).toHaveBeenCalled();
    });

    it('should clear last transcript on start recording', async () => {
      const { result } = renderHook(() => useVoice({ autoTranscribe: true }));

      // Set up a transcript
      await act(async () => {
        const blob = new Blob(['audio'], { type: 'audio/webm' });
        await result.current.transcribe(blob);
      });

      expect(result.current.lastTranscript).not.toBeNull();

      // Start new recording
      await act(async () => {
        await result.current.startRecording();
      });

      expect(result.current.lastTranscript).toBeNull();
    });

    it('should clear last transcript on cancel recording', async () => {
      const { result } = renderHook(() => useVoice({ autoTranscribe: true }));

      // Set up a transcript
      await act(async () => {
        const blob = new Blob(['audio'], { type: 'audio/webm' });
        await result.current.transcribe(blob);
      });

      expect(result.current.lastTranscript).not.toBeNull();

      // Cancel recording
      act(() => {
        result.current.cancelRecording();
      });

      expect(result.current.lastTranscript).toBeNull();
    });
  });

  // ============================================================================
  // TRANSCRIPTION TESTS
  // ============================================================================

  describe('Transcription', () => {
    it('should transcribe audio blob', async () => {
      const { result } = renderHook(() => useVoice());

      const blob = new Blob(['audio'], { type: 'audio/webm' });
      let transcript: any = null;

      await act(async () => {
        transcript = await result.current.transcribe(blob);
      });

      expect(mockVoiceClient.transcribe).toHaveBeenCalledWith(blob);
      expect(transcript).toBeTruthy();
      expect(transcript.success).toBe(true);
      expect(result.current.lastTranscript).toBeTruthy();
    });

    it('should set isTranscribing during transcription', async () => {
      const { result } = renderHook(() => useVoice());

      const blob = new Blob(['audio'], { type: 'audio/webm' });

      // Mock slow transcription
      let resolveTranscribe: any;
      mockVoiceClient.transcribe.mockReturnValue(
        new Promise((resolve) => {
          resolveTranscribe = resolve;
        })
      );

      const transcribePromise = act(async () => {
        return result.current.transcribe(blob);
      });

      // Should be transcribing
      expect(result.current.isTranscribing).toBe(true);

      // Resolve transcription
      await act(async () => {
        resolveTranscribe({
          success: true,
          result: { text: 'Test', confidence: 0.9 },
        });
        await transcribePromise;
      });

      // Should be done
      expect(result.current.isTranscribing).toBe(false);
    });

    it('should handle transcription errors', async () => {
      mockVoiceClient.transcribe.mockRejectedValue(new Error('Transcription failed'));

      const { result } = renderHook(() => useVoice());

      const blob = new Blob(['audio'], { type: 'audio/webm' });

      // Catch error within act to allow state to flush
      await act(async () => {
        try {
          await result.current.transcribe(blob);
        } catch (e) {
          // Expected - transcribe throws after setting error state
          expect((e as Error).message).toBe('Transcription failed');
        }
      });

      expect(result.current.transcriptionError).toBe('Transcription failed');
      expect(result.current.isTranscribing).toBe(false);
    });

    it('should throw error when STT is disabled', async () => {
      // Update mock to disable STT
      jest.mocked(voiceContextModule.useVoiceSettings).mockReturnValue([
        { ...mockSettings, sttEnabled: false },
        jest.fn()
      ]);

      const { result } = renderHook(() => useVoice());

      const blob = new Blob(['audio'], { type: 'audio/webm' });

      // Catch the error within act
      let thrownError: Error | null = null;
      await act(async () => {
        try {
          await result.current.transcribe(blob);
        } catch (e) {
          thrownError = e as Error;
        }
      });

      expect(thrownError).not.toBeNull();
      expect(thrownError!.message).toContain('Speech-to-text is disabled');
    });

    it('should auto-transcribe after stop recording when enabled', async () => {
      const { result } = renderHook(() => useVoice({ autoTranscribe: true }));

      await act(async () => {
        await result.current.stopRecording();
      });

      expect(mockVoiceClient.transcribe).toHaveBeenCalled();
      expect(result.current.lastTranscript).not.toBeNull();
    });

    it('should not auto-transcribe when disabled', async () => {
      const { result } = renderHook(() => useVoice({ autoTranscribe: false }));

      await act(async () => {
        await result.current.stopRecording();
      });

      expect(mockVoiceClient.transcribe).not.toHaveBeenCalled();
      expect(result.current.lastTranscript).toBeNull();
    });

    it('should not throw on auto-transcribe failure', async () => {
      mockVoiceClient.transcribe.mockRejectedValue(new Error('Auto-transcribe failed'));

      const { result } = renderHook(() => useVoice({ autoTranscribe: true }));

      // Should not throw - recording still succeeded
      await act(async () => {
        await result.current.stopRecording();
      });

      expect(result.current.transcriptionError).toBe('Auto-transcribe failed');
    });
  });

  // ============================================================================
  // SYNTHESIS TESTS
  // ============================================================================

  describe('Synthesis', () => {
    // Reset mocks before each synthesis test for better isolation
    beforeEach(() => {
      jest.clearAllMocks();
      mockVoiceClient.synthesize.mockResolvedValue(new Blob(['audio'], { type: 'audio/mpeg' }));
    });

    it('should synthesize text to audio', async () => {
      const { result } = renderHook(() => useVoice());

      let audioBlob: Blob | null = null;

      await act(async () => {
        audioBlob = await result.current.synthesize('Hello world');
      });

      expect(mockVoiceClient.synthesize).toHaveBeenCalledWith(
        expect.objectContaining({
          text: 'Hello world',
          voice_id: 'default_voice',
          profile_name: 'default',
        })
      );
      expect(audioBlob).toBeInstanceOf(Blob);
      expect(result.current.lastSynthesizedAudio).toBe(audioBlob);
    });

    it('should set isSynthesizing during synthesis', async () => {
      const { result } = renderHook(() => useVoice());

      // Mock slow synthesis
      let resolveSynthesize: any;
      mockVoiceClient.synthesize.mockReturnValue(
        new Promise((resolve) => {
          resolveSynthesize = resolve;
        })
      );

      const synthesizePromise = act(async () => {
        return result.current.synthesize('Test');
      });

      // Should be synthesizing
      expect(result.current.isSynthesizing).toBe(true);

      // Resolve synthesis
      await act(async () => {
        resolveSynthesize(new Blob(['audio'], { type: 'audio/mpeg' }));
        await synthesizePromise;
      });

      // Should be done
      expect(result.current.isSynthesizing).toBe(false);
    });

    it('should handle synthesis errors', async () => {
      mockVoiceClient.synthesize.mockRejectedValue(new Error('Synthesis failed'));

      const { result } = renderHook(() => useVoice());

      await act(async () => {
        try {
          await result.current.synthesize('Test');
        } catch (e) {
          // Expected - synthesize throws after setting error state
          expect((e as Error).message).toBe('Synthesis failed');
        }
      });

      expect(result.current.synthesisError).toBe('Synthesis failed');
      expect(result.current.isSynthesizing).toBe(false);
    });

    it('should throw error when TTS is disabled', async () => {
      // Update mock to disable TTS
      jest.mocked(voiceContextModule.useVoiceSettings).mockReturnValue([
        { ...mockSettings, ttsEnabled: false },
        jest.fn()
      ]);

      const { result } = renderHook(() => useVoice());

      let thrownError: Error | null = null;
      await act(async () => {
        try {
          await result.current.synthesize('Test');
        } catch (e) {
          thrownError = e as Error;
        }
      });

      expect(thrownError).not.toBeNull();
      expect(thrownError!.message).toContain('Text-to-speech is disabled');
    });

    it('should use voice settings in synthesis', async () => {
      mockSettings.selectedVoiceId = 'custom_voice';
      mockSettings.selectedProfile = 'premium';

      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.synthesize('Test');
      });

      expect(mockVoiceClient.synthesize).toHaveBeenCalledWith(
        expect.objectContaining({
          voice_id: 'custom_voice',
          profile_name: 'premium',
        })
      );
    });

    it('should allow custom synthesis options', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.synthesize('Test', {
          voice_id: 'override_voice',
          model_id: 'eleven_multilingual_v2',
        });
      });

      expect(mockVoiceClient.synthesize).toHaveBeenCalledWith(
        expect.objectContaining({
          text: 'Test',
          voice_id: 'override_voice',
          stability: 0.7,
        })
      );
    });
  });

  // ============================================================================
  // PLAYBACK TESTS
  // ============================================================================

  describe('Playback', () => {
    // Reset mocks before each playback test for better isolation
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should play audio', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.playAudio();
      });

      expect(mockPlayer.play).toHaveBeenCalled();
    });

    it('should apply volume and playback speed from settings', async () => {
      mockSettings.volume = 0.6;
      mockSettings.playbackSpeed = 1.5;

      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.playAudio();
      });

      expect(mockPlayer.setVolume).toHaveBeenCalledWith(0.6);
      expect(mockPlayer.setPlaybackRate).toHaveBeenCalledWith(1.5);
    });

    it('should pause audio', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.pauseAudio();
      });

      expect(mockPlayer.pause).toHaveBeenCalled();
    });

    it('should stop audio', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.stopAudio();
      });

      expect(mockPlayer.stop).toHaveBeenCalled();
    });

    it('should set volume', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.setVolume(0.5);
      });

      expect(mockPlayer.setVolume).toHaveBeenCalledWith(0.5);
    });
  });

  // ============================================================================
  // COMBINED WORKFLOW TESTS
  // ============================================================================

  describe('Combined Workflows', () => {
    // Reset mocks before each combined test for better isolation
    beforeEach(() => {
      jest.clearAllMocks();
      mockVoiceClient.synthesize.mockResolvedValue(new Blob(['audio'], { type: 'audio/mpeg' }));
    });

    it('should synthesize and play text (speakText)', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.speakText('Hello');
      });

      expect(mockVoiceClient.synthesize).toHaveBeenCalled();
      expect(mockPlayer.setSource).toHaveBeenCalled();
      expect(mockPlayer.play).toHaveBeenCalled();
    });

    it('should pass options to speakText', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.speakText('Hello', { voice_id: 'custom' });
      });

      expect(mockVoiceClient.synthesize).toHaveBeenCalledWith(
        expect.objectContaining({
          voice_id: 'custom',
        })
      );
    });

    it('should synthesizeAndPlay be alias for speakText', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.synthesizeAndPlay('Hello');
      });

      expect(mockVoiceClient.synthesize).toHaveBeenCalled();
      expect(mockPlayer.play).toHaveBeenCalled();
    });

    it('recordAndTranscribe should throw with instruction', async () => {
      const { result } = renderHook(() => useVoice());

      await expect(
        act(async () => {
          await result.current.recordAndTranscribe();
        })
      ).rejects.toThrow('call stopRecording() when done');
    });
  });

  // ============================================================================
  // ERROR HANDLING TESTS
  // ============================================================================

  describe('Error Handling', () => {
    it('should expose recorder errors', () => {
      mockRecorder.error = 'Recording error';

      const { result } = renderHook(() => useVoice());

      expect(result.current.recordingError).toBe('Recording error');
    });

    it('should expose player errors', () => {
      mockPlayer.error = 'Playback error';

      const { result } = renderHook(() => useVoice());

      expect(result.current.playbackError).toBe('Playback error');
    });

    it('should clear all errors', async () => {
      mockRecorder.error = 'Recording error';
      mockPlayer.error = 'Playback error';

      const { result } = renderHook(() => useVoice());

      // Set transcription and synthesis errors
      mockVoiceClient.transcribe.mockRejectedValue(new Error('Transcription error'));
      mockVoiceClient.synthesize.mockRejectedValue(new Error('Synthesis error'));

      try {
        await act(async () => {
          await result.current.transcribe(new Blob());
        });
      } catch (e) {}

      try {
        await act(async () => {
          await result.current.synthesize('Test');
        });
      } catch (e) {}

      expect(result.current.transcriptionError).toBeTruthy();
      expect(result.current.synthesisError).toBeTruthy();

      // Clear all errors
      act(() => {
        result.current.clearErrors();
      });

      expect(mockRecorder.clearError).toHaveBeenCalled();
      expect(mockPlayer.clearError).toHaveBeenCalled();
      expect(result.current.transcriptionError).toBeNull();
      expect(result.current.synthesisError).toBeNull();
    });
  });

  // ============================================================================
  // STATE PROPAGATION TESTS
  // ============================================================================

  describe('State Propagation', () => {
    it('should propagate isRecording from recorder', () => {
      mockRecorder.isRecording = true;

      const { result, rerender } = renderHook(() => useVoice());

      rerender();

      expect(result.current.isRecording).toBe(true);
    });

    it('should propagate recording duration from recorder', () => {
      mockRecorder.duration = 42.5;

      const { result, rerender } = renderHook(() => useVoice());

      rerender();

      expect(result.current.recordingDuration).toBe(42.5);
    });

    it('should propagate audio level from recorder', () => {
      mockRecorder.audioLevel = 0.75;

      const { result, rerender } = renderHook(() => useVoice());

      rerender();

      expect(result.current.audioLevel).toBe(0.75);
    });

    it('should propagate isPlaying from player', () => {
      mockPlayer.isPlaying = true;

      const { result, rerender } = renderHook(() => useVoice());

      rerender();

      expect(result.current.isPlaying).toBe(true);
    });

    it('should propagate playback time from player', () => {
      mockPlayer.currentTime = 10.5;

      const { result, rerender } = renderHook(() => useVoice());

      rerender();

      expect(result.current.playbackCurrentTime).toBe(10.5);
    });
  });
});
