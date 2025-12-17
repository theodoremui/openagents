/**
 * useAudioPlayer Hook
 *
 * Provides audio playback functionality with controls.
 * Features:
 * - Play/pause/stop controls
 * - Volume control
 * - Playback speed control
 * - Progress tracking
 * - Auto-play support
 * - Loop support
 * - Audio visualization data
 * - Error handling
 */

import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Configuration options for audio player
 */
export interface AudioPlayerConfig {
  /** Auto-play when audio source is set (default: false) */
  autoPlay?: boolean;
  /** Loop playback (default: false) */
  loop?: boolean;
  /** Initial volume (0.0 - 1.0, default: 1.0) */
  volume?: number;
  /** Initial playback rate (0.5 - 2.0, default: 1.0) */
  playbackRate?: number;
  /** Preload strategy (default: 'metadata') */
  preload?: 'none' | 'metadata' | 'auto';
  /** Enable audio visualization data (default: false) */
  enableVisualization?: boolean;
}

/**
 * Audio player state and controls
 */
export interface AudioPlayerResult {
  /** Whether audio is currently playing */
  isPlaying: boolean;
  /** Whether audio is loading */
  isLoading: boolean;
  /** Current playback time in seconds */
  currentTime: number;
  /** Total duration in seconds */
  duration: number;
  /** Current volume (0.0 - 1.0) */
  volume: number;
  /** Current playback rate (0.5 - 2.0) */
  playbackRate: number;
  /** Whether audio is muted */
  isMuted: boolean;
  /** Whether playback has ended */
  hasEnded: boolean;
  /** Last error that occurred */
  error: string | null;
  /** Audio frequency data for visualization (if enabled) */
  frequencyData: Uint8Array | null;

  /** Set audio source (URL or Blob) */
  setSource: (source: string | Blob) => void;
  /** Play audio */
  play: () => Promise<void>;
  /** Pause audio */
  pause: () => void;
  /** Stop audio (pause and reset to beginning) */
  stop: () => void;
  /** Seek to specific time in seconds */
  seek: (time: number) => void;
  /** Set volume (0.0 - 1.0) */
  setVolume: (volume: number) => void;
  /** Set playback rate (0.5 - 2.0) */
  setPlaybackRate: (rate: number) => void;
  /** Toggle mute */
  toggleMute: () => void;
  /** Clear error state */
  clearError: () => void;
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: Required<AudioPlayerConfig> = {
  autoPlay: false,
  loop: false,
  volume: 1.0,
  playbackRate: 1.0,
  preload: 'metadata',
  enableVisualization: false,
};

/**
 * Hook for playing audio
 */
export function useAudioPlayer(
  config?: AudioPlayerConfig
): AudioPlayerResult {
  // Merge config with defaults
  const finalConfig: Required<AudioPlayerConfig> = {
    ...DEFAULT_CONFIG,
    ...config,
  };

  // State
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(finalConfig.volume);
  const [playbackRate, setPlaybackRateState] = useState(finalConfig.playbackRate);
  const [isMuted, setIsMuted] = useState(false);
  const [hasEnded, setHasEnded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [frequencyData, setFrequencyData] = useState<Uint8Array | null>(null);

  // Refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceNodeRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  /**
   * Create audio element if not exists
   */
  const getAudioElement = useCallback(() => {
    if (!audioRef.current) {
      const audio = new Audio();
      audio.preload = finalConfig.preload;
      audio.loop = finalConfig.loop;
      audio.volume = finalConfig.volume;
      audio.playbackRate = finalConfig.playbackRate;

      // Event listeners
      audio.addEventListener('loadstart', () => {
        setIsLoading(true);
        setError(null);
      });

      audio.addEventListener('loadedmetadata', () => {
        setDuration(audio.duration);
        setIsLoading(false);
      });

      audio.addEventListener('canplay', () => {
        setIsLoading(false);
      });

      audio.addEventListener('timeupdate', () => {
        setCurrentTime(audio.currentTime);
      });

      audio.addEventListener('play', () => {
        setIsPlaying(true);
        setHasEnded(false);
      });

      audio.addEventListener('pause', () => {
        setIsPlaying(false);
      });

      audio.addEventListener('ended', () => {
        setIsPlaying(false);
        setHasEnded(true);
      });

      audio.addEventListener('error', (e) => {
        const audioError = audio.error;
        let errorMessage = 'Audio playback error';

        if (audioError) {
          switch (audioError.code) {
            case MediaError.MEDIA_ERR_ABORTED:
              errorMessage = 'Playback aborted';
              break;
            case MediaError.MEDIA_ERR_NETWORK:
              errorMessage = 'Network error while loading audio';
              break;
            case MediaError.MEDIA_ERR_DECODE:
              errorMessage = 'Failed to decode audio';
              break;
            case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
              errorMessage = 'Audio format not supported';
              break;
          }
        }

        setError(errorMessage);
        setIsLoading(false);
        setIsPlaying(false);
      });

      audioRef.current = audio;
    }

    return audioRef.current;
  }, [finalConfig.preload, finalConfig.loop, finalConfig.volume, finalConfig.playbackRate]);

  /**
   * Setup audio visualization
   */
  const setupVisualization = useCallback(() => {
    if (!finalConfig.enableVisualization || !audioRef.current) return;

    try {
      // Create audio context and analyser
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;

      // Connect audio element to analyser
      if (!sourceNodeRef.current) {
        const source = audioContext.createMediaElementSource(audioRef.current);
        source.connect(analyser);
        analyser.connect(audioContext.destination);
        sourceNodeRef.current = source;
      }

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      // Update frequency data
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const updateVisualization = () => {
        if (analyserRef.current && isPlaying) {
          analyserRef.current.getByteFrequencyData(dataArray);
          setFrequencyData(new Uint8Array(dataArray));
          animationFrameRef.current = requestAnimationFrame(updateVisualization);
        }
      };

      updateVisualization();
    } catch (err) {
      console.warn('Failed to setup audio visualization:', err);
      // Non-critical, continue without visualization
    }
  }, [finalConfig.enableVisualization, isPlaying]);

  /**
   * Cleanup visualization
   */
  const cleanupVisualization = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    analyserRef.current = null;
    sourceNodeRef.current = null;
    setFrequencyData(null);
  }, []);

  /**
   * Set audio source
   */
  const setSource = useCallback(
    (source: string | Blob) => {
      const audio = getAudioElement();

      // Cleanup previous source
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }

      audio.pause();
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(0);
      setHasEnded(false);
      setError(null);

      // Set new source
      if (source instanceof Blob) {
        const url = URL.createObjectURL(source);
        audio.src = url;
        objectUrlRef.current = url;
      } else {
        audio.src = source;
      }

      // Auto-play if enabled
      if (finalConfig.autoPlay) {
        audio.play().catch((err) => {
          setError(`Auto-play failed: ${err.message}`);
        });
      }
    },
    [finalConfig.autoPlay, getAudioElement]
  );

  /**
   * Play audio
   */
  const play = useCallback(async (): Promise<void> => {
    const audio = getAudioElement();
    setError(null);

    try {
      await audio.play();
      setupVisualization();
    } catch (err) {
      const error = err as Error;
      setError(`Failed to play audio: ${error.message}`);
      throw error;
    }
  }, [getAudioElement, setupVisualization]);

  /**
   * Pause audio
   */
  const pause = useCallback(() => {
    const audio = getAudioElement();
    audio.pause();

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  }, [getAudioElement]);

  /**
   * Stop audio (pause and reset)
   */
  const stop = useCallback(() => {
    const audio = getAudioElement();
    audio.pause();
    audio.currentTime = 0;
    setCurrentTime(0);
    setIsPlaying(false);
    setHasEnded(false);

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  }, [getAudioElement]);

  /**
   * Seek to specific time
   */
  const seek = useCallback(
    (time: number) => {
      const audio = getAudioElement();
      const clampedTime = Math.max(0, Math.min(time, audio.duration || 0));
      audio.currentTime = clampedTime;
      setCurrentTime(clampedTime);
    },
    [getAudioElement]
  );

  /**
   * Set volume
   */
  const setVolume = useCallback(
    (newVolume: number) => {
      const audio = getAudioElement();
      const clampedVolume = Math.max(0, Math.min(1, newVolume));
      audio.volume = clampedVolume;
      setVolumeState(clampedVolume);
    },
    [getAudioElement]
  );

  /**
   * Set playback rate
   */
  const setPlaybackRate = useCallback(
    (rate: number) => {
      const audio = getAudioElement();
      const clampedRate = Math.max(0.5, Math.min(2.0, rate));
      audio.playbackRate = clampedRate;
      setPlaybackRateState(clampedRate);
    },
    [getAudioElement]
  );

  /**
   * Toggle mute
   */
  const toggleMute = useCallback(() => {
    const audio = getAudioElement();
    audio.muted = !audio.muted;
    setIsMuted(audio.muted);
  }, [getAudioElement]);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      // Cleanup audio element
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current = null;
      }

      // Cleanup object URL
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }

      // Cleanup visualization
      cleanupVisualization();
    };
  }, [cleanupVisualization]);

  /**
   * Setup visualization when playing
   */
  useEffect(() => {
    if (isPlaying) {
      setupVisualization();
    }
  }, [isPlaying, setupVisualization]);

  return {
    isPlaying,
    isLoading,
    currentTime,
    duration,
    volume,
    playbackRate,
    isMuted,
    hasEnded,
    error,
    frequencyData,
    setSource,
    play,
    pause,
    stop,
    seek,
    setVolume,
    setPlaybackRate,
    toggleMute,
    clearError,
  };
}
