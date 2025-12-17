/**
 * useAudioRecorder Hook
 *
 * Provides audio recording functionality using MediaRecorder API.
 * Features:
 * - Microphone permission management
 * - Real-time audio level monitoring
 * - Duration tracking
 * - Configurable recording settings
 * - Auto-stop on max duration
 * - Error handling
 */

import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Configuration options for audio recorder
 */
export interface AudioRecorderConfig {
  /** MIME type for audio encoding (default: 'audio/webm;codecs=opus') */
  mimeType?: string;
  /** Audio bitrate in bits per second (default: 128000) */
  audioBitsPerSecond?: number;
  /** Maximum recording duration in seconds (default: 300 = 5 minutes) */
  maxDuration?: number;
  /** Enable audio level monitoring (default: true) */
  enableAudioLevel?: boolean;
  /** Audio level update interval in ms (default: 100) */
  audioLevelUpdateInterval?: number;
}

/**
 * Audio recorder state and controls
 */
export interface AudioRecorderResult {
  /** Whether recording is currently active */
  isRecording: boolean;
  /** Current recording duration in seconds */
  duration: number;
  /** Current audio level (0.0 - 1.0) */
  audioLevel: number;
  /** Whether microphone permission is granted */
  hasPermission: boolean;
  /** Whether permission request is in progress */
  isRequestingPermission: boolean;
  /** Last error that occurred */
  error: string | null;

  /** Request microphone permission */
  requestPermission: () => Promise<boolean>;
  /** Start recording */
  startRecording: () => Promise<void>;
  /** Stop recording and return audio blob */
  stopRecording: () => Promise<Blob>;
  /** Cancel recording without returning blob */
  cancelRecording: () => void;
  /** Clear error state */
  clearError: () => void;
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: Required<AudioRecorderConfig> = {
  mimeType: 'audio/webm;codecs=opus',
  audioBitsPerSecond: 128000,
  maxDuration: 300, // 5 minutes
  enableAudioLevel: true,
  audioLevelUpdateInterval: 100,
};

/**
 * Hook for recording audio from microphone
 */
export function useAudioRecorder(
  config?: AudioRecorderConfig
): AudioRecorderResult {
  // Merge config with defaults
  const finalConfig: Required<AudioRecorderConfig> = {
    ...DEFAULT_CONFIG,
    ...config,
  };

  // State
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [hasPermission, setHasPermission] = useState(false);
  const [isRequestingPermission, setIsRequestingPermission] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioLevelIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const stopRecordingRef = useRef<(() => Promise<Blob>) | null>(null);

  /**
   * Check if MediaRecorder is supported
   */
  const isMediaRecorderSupported = useCallback(() => {
    return typeof window !== 'undefined' && 'MediaRecorder' in window;
  }, []);

  /**
   * Check if requested MIME type is supported
   */
  const isMimeTypeSupported = useCallback(() => {
    if (!isMediaRecorderSupported()) return false;
    return MediaRecorder.isTypeSupported(finalConfig.mimeType);
  }, [finalConfig.mimeType]);

  /**
   * Request microphone permission
   */
  const requestPermission = useCallback(async (): Promise<boolean> => {
    console.log('[useAudioRecorder] requestPermission called');
    
    if (!isMediaRecorderSupported()) {
      setError('MediaRecorder API is not supported in this browser');
      return false;
    }

    if (!isMimeTypeSupported()) {
      setError(`MIME type '${finalConfig.mimeType}' is not supported`);
      return false;
    }

    setIsRequestingPermission(true);
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Store stream for later use
      audioStreamRef.current = stream;
      setHasPermission(true);
      setIsRequestingPermission(false);
      console.log('[useAudioRecorder] Permission granted');
      return true;
    } catch (err) {
      const error = err as Error;
      console.error('[useAudioRecorder] Permission error:', error);
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        setError('Microphone permission denied. Please allow microphone access.');
      } else if (error.name === 'NotFoundError') {
        setError('No microphone found. Please connect a microphone.');
      } else {
        setError(`Failed to access microphone: ${error.message}`);
      }
      setHasPermission(false);
      setIsRequestingPermission(false);
      return false;
    }
  }, [finalConfig.mimeType, isMimeTypeSupported, isMediaRecorderSupported]);

  /**
   * Setup audio level monitoring
   */
  const setupAudioLevelMonitoring = useCallback(() => {
    if (!finalConfig.enableAudioLevel || !audioStreamRef.current) return;

    try {
      // Create audio context and analyser
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;

      const source = audioContext.createMediaStreamSource(audioStreamRef.current);
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      // Monitor audio level
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      audioLevelIntervalRef.current = setInterval(() => {
        if (analyserRef.current) {
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
          const normalized = Math.min(average / 128, 1.0); // Normalize to 0-1
          setAudioLevel(normalized);
        }
      }, finalConfig.audioLevelUpdateInterval);
    } catch (err) {
      console.warn('[useAudioRecorder] Failed to setup audio level monitoring:', err);
      // Non-critical, continue without monitoring
    }
  }, [finalConfig.enableAudioLevel, finalConfig.audioLevelUpdateInterval]);

  /**
   * Cleanup audio level monitoring
   */
  const cleanupAudioLevelMonitoring = useCallback(() => {
    if (audioLevelIntervalRef.current) {
      clearInterval(audioLevelIntervalRef.current);
      audioLevelIntervalRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    analyserRef.current = null;
    setAudioLevel(0);
  }, []);

  /**
   * Start recording
   */
  const startRecording = useCallback(async (): Promise<void> => {
    console.log('[useAudioRecorder] startRecording called');
    setError(null);

    // Check permission
    if (!hasPermission || !audioStreamRef.current) {
      console.log('[useAudioRecorder] No permission, requesting...');
      const granted = await requestPermission();
      if (!granted) {
        throw new Error('Microphone permission not granted');
      }
    }

    try {
      // Create MediaRecorder
      console.log('[useAudioRecorder] Creating MediaRecorder with mimeType:', finalConfig.mimeType);
      const mediaRecorder = new MediaRecorder(audioStreamRef.current!, {
        mimeType: finalConfig.mimeType,
        audioBitsPerSecond: finalConfig.audioBitsPerSecond,
      });

      // Reset chunks
      audioChunksRef.current = [];

      // Handle data available
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          console.log('[useAudioRecorder] Data chunk received, size:', event.data.size, 'total chunks:', audioChunksRef.current.length);
        }
      };

      // Start recording
      mediaRecorder.start(100); // Collect data every 100ms
      mediaRecorderRef.current = mediaRecorder;
      startTimeRef.current = Date.now();

      console.log('[useAudioRecorder] MediaRecorder started, state:', mediaRecorder.state);

      // Setup audio level monitoring
      setupAudioLevelMonitoring();

      // Start duration tracking
      durationIntervalRef.current = setInterval(() => {
        if (startTimeRef.current) {
          const elapsed = (Date.now() - startTimeRef.current) / 1000;
          setDuration(elapsed);

          // Auto-stop at max duration
          if (elapsed >= finalConfig.maxDuration) {
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
              console.log('[useAudioRecorder] Max duration reached, auto-stopping');
              if (stopRecordingRef.current) {
                stopRecordingRef.current().catch((err) => {
                  console.error('[useAudioRecorder] Auto-stop recording failed:', err);
                });
              }
            }
          }
        }
      }, 100);

      setIsRecording(true);
      console.log('[useAudioRecorder] Recording started successfully');
    } catch (err) {
      const error = err as Error;
      console.error('[useAudioRecorder] Failed to start recording:', error);
      setError(`Failed to start recording: ${error.message}`);
      throw error;
    }
  }, [
    hasPermission,
    finalConfig.mimeType,
    finalConfig.audioBitsPerSecond,
    finalConfig.maxDuration,
    requestPermission,
    setupAudioLevelMonitoring,
  ]);

  /**
   * Stop recording and return blob
   */
  const stopRecording = useCallback(async (): Promise<Blob> => {
    console.log('[useAudioRecorder] stopRecording called');
    
    return new Promise((resolve, reject) => {
      const mediaRecorder = mediaRecorderRef.current;
      
      // Check if MediaRecorder exists
      if (!mediaRecorder) {
        console.error('[useAudioRecorder] MediaRecorder not initialized');
        reject(new Error('Not recording: MediaRecorder not initialized'));
        return;
      }

      console.log('[useAudioRecorder] MediaRecorder state:', mediaRecorder.state);

      // Check MediaRecorder's actual state
      if (mediaRecorder.state === 'inactive' || mediaRecorder.state === 'paused') {
        // If already stopped, try to return existing chunks if available
        if (audioChunksRef.current.length > 0) {
          console.log('[useAudioRecorder] MediaRecorder already stopped, returning existing chunks');
          const blob = new Blob(audioChunksRef.current, {
            type: finalConfig.mimeType,
          });
          // Cleanup state
          cleanupAudioLevelMonitoring();
          if (durationIntervalRef.current) {
            clearInterval(durationIntervalRef.current);
            durationIntervalRef.current = null;
          }
          mediaRecorderRef.current = null;
          startTimeRef.current = null;
          setIsRecording(false);
          setDuration(0);
          resolve(blob);
          return;
        }
        console.error('[useAudioRecorder] MediaRecorder not in recording state and no chunks');
        reject(new Error('Not recording: MediaRecorder is not in recording state'));
        return;
      }

      // Handle stop event
      mediaRecorder.onstop = () => {
        console.log('[useAudioRecorder] MediaRecorder onstop fired, chunks:', audioChunksRef.current.length);
        // Create blob from chunks
        const blob = new Blob(audioChunksRef.current, {
          type: finalConfig.mimeType,
        });
        console.log('[useAudioRecorder] Created blob, size:', blob.size, 'type:', blob.type);

        // Cleanup
        cleanupAudioLevelMonitoring();

        if (durationIntervalRef.current) {
          clearInterval(durationIntervalRef.current);
          durationIntervalRef.current = null;
        }

        mediaRecorderRef.current = null;
        startTimeRef.current = null;
        setIsRecording(false);
        setDuration(0);

        resolve(blob);
      };

      // Handle errors
      mediaRecorder.onerror = (event: any) => {
        const error = event.error || new Error('Recording failed');
        console.error('[useAudioRecorder] MediaRecorder error:', error);
        setError(`Recording error: ${error.message}`);
        setIsRecording(false);
        reject(error);
      };

      // Stop recording
      try {
        console.log('[useAudioRecorder] Calling mediaRecorder.stop()');
        mediaRecorder.stop();
      } catch (err) {
        const error = err as Error;
        console.error('[useAudioRecorder] Failed to stop MediaRecorder:', error);
        setError(`Failed to stop recording: ${error.message}`);
        setIsRecording(false);
        reject(error);
      }
    });
  }, [finalConfig.mimeType, cleanupAudioLevelMonitoring]);

  // Store stopRecording ref for use in interval callbacks
  useEffect(() => {
    stopRecordingRef.current = stopRecording;
  }, [stopRecording]);

  /**
   * Cancel recording without returning blob
   */
  const cancelRecording = useCallback(() => {
    console.log('[useAudioRecorder] cancelRecording called');
    if (!mediaRecorderRef.current || !isRecording) return;

    mediaRecorderRef.current.stop();
    audioChunksRef.current = [];

    cleanupAudioLevelMonitoring();

    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
      durationIntervalRef.current = null;
    }

    mediaRecorderRef.current = null;
    startTimeRef.current = null;
    setIsRecording(false);
    setDuration(0);
  }, [isRecording, cleanupAudioLevelMonitoring]);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Cleanup on unmount ONLY - DO NOT ADD DEPENDENCIES!
   * 
   * ⚠️ CRITICAL: Keep dependency array EMPTY []
   * 
   * Bug: Having [isRecording, ...] causes cleanup to run when isRecording
   * changes, which kills the audio stream while recording is starting.
   * The MediaRecorder then immediately becomes 'inactive' with no chunks.
   * 
   * eslint-disable-next-line react-hooks/exhaustive-deps
   */
  useEffect(() => {
    return () => {
      // Stop MediaRecorder if it exists
      if (mediaRecorderRef.current) {
        try {
          if (mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
          }
        } catch (e) {
          // Ignore errors during cleanup
        }
        mediaRecorderRef.current = null;
      }

      // Stop all audio tracks
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop());
        audioStreamRef.current = null;
      }

      // Clear intervals
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      if (audioLevelIntervalRef.current) {
        clearInterval(audioLevelIntervalRef.current);
        audioLevelIntervalRef.current = null;
      }

      // Close audio context
      if (audioContextRef.current) {
        try {
          audioContextRef.current.close();
        } catch (e) {
          // Ignore
        }
        audioContextRef.current = null;
      }
      analyserRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // MUST be empty - cleanup only on unmount!

  return {
    isRecording,
    duration,
    audioLevel,
    hasPermission,
    isRequestingPermission,
    error,
    requestPermission,
    startRecording,
    stopRecording,
    cancelRecording,
    clearError,
  };
}
