/**
 * useVoice Hook
 *
 * Convenience hook that combines useAudioRecorder, useAudioPlayer, and VoiceContext
 * for complete voice interaction functionality.
 */

import { useState, useCallback, useRef } from 'react';
import { useAudioRecorder, AudioRecorderConfig } from './useAudioRecorder';
import { useAudioPlayer, AudioPlayerConfig } from './useAudioPlayer';
import {
  useVoiceContext,
  useVoiceSettings,
  useVoiceClient,
} from '../contexts/VoiceContext';
import type { TranscriptResponse, SynthesizeRequest } from '../services/VoiceApiClient';

export interface VoiceConfig {
  recorderConfig?: AudioRecorderConfig;
  playerConfig?: AudioPlayerConfig;
  autoTranscribe?: boolean;
  autoPlaySynthesis?: boolean;
}

export interface VoiceResult {
  isRecording: boolean;
  recordingDuration: number;
  audioLevel: number;
  hasRecordingPermission: boolean;
  isPlaying: boolean;
  playbackCurrentTime: number;
  playbackDuration: number;
  playbackVolume: number;
  isTranscribing: boolean;
  isSynthesizing: boolean;
  lastTranscript: TranscriptResponse | null;
  lastSynthesizedAudio: Blob | null;
  recordingError: string | null;
  playbackError: string | null;
  transcriptionError: string | null;
  synthesisError: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob>;
  cancelRecording: () => void;
  playAudio: () => Promise<void>;
  pauseAudio: () => void;
  stopAudio: () => void;
  setVolume: (volume: number) => void;
  transcribe: (audioBlob: Blob) => Promise<TranscriptResponse>;
  synthesize: (text: string, options?: Partial<SynthesizeRequest>) => Promise<Blob>;
  speakText: (text: string, options?: Partial<SynthesizeRequest>) => Promise<void>;
  recordAndTranscribe: () => Promise<TranscriptResponse>;
  synthesizeAndPlay: (text: string, options?: Partial<SynthesizeRequest>) => Promise<void>;
  clearErrors: () => void;
}

const DEFAULT_CONFIG: Required<VoiceConfig> = {
  recorderConfig: {},
  playerConfig: {},
  autoTranscribe: false,
  autoPlaySynthesis: false,
};

export function useVoice(config?: VoiceConfig): VoiceResult {
  const finalConfig: Required<VoiceConfig> = {
    ...DEFAULT_CONFIG,
    ...config,
  };

  const recorder = useAudioRecorder(finalConfig.recorderConfig);
  const player = useAudioPlayer(finalConfig.playerConfig);
  const voiceClient = useVoiceClient();
  const [settings] = useVoiceSettings();

  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [lastTranscript, setLastTranscript] = useState<TranscriptResponse | null>(null);
  const [lastSynthesizedAudio, setLastSynthesizedAudio] = useState<Blob | null>(null);
  const [transcriptionError, setTranscriptionError] = useState<string | null>(null);
  const [synthesisError, setSynthesisError] = useState<string | null>(null);

  const lastRecordingRef = useRef<Blob | null>(null);

  const transcribe = useCallback(
    async (audioBlob: Blob): Promise<TranscriptResponse> => {
      console.log('[useVoice] transcribe called, blob size:', audioBlob.size, 'type:', audioBlob.type);
      
      if (!settings.sttEnabled) {
        console.warn('[useVoice] STT is disabled in settings');
        throw new Error('Speech-to-text is disabled in settings');
      }

      setIsTranscribing(true);
      setTranscriptionError(null);

      try {
        console.log('[useVoice] Calling voiceClient.transcribe...');
        const result = await voiceClient.transcribe(audioBlob);
        console.log('[useVoice] Transcription result:', result);
        setLastTranscript(result);
        return result;
      } catch (err) {
        const error = err as Error;
        console.error('[useVoice] Transcription error:', error);
        setTranscriptionError(error.message);
        throw error;
      } finally {
        setIsTranscribing(false);
      }
    },
    [voiceClient, settings.sttEnabled]
  );

  const synthesize = useCallback(
    async (text: string, options?: Partial<SynthesizeRequest>): Promise<Blob> => {
      if (!settings.ttsEnabled) {
        throw new Error('Text-to-speech is disabled in settings');
      }

      setIsSynthesizing(true);
      setSynthesisError(null);

      try {
        const request: SynthesizeRequest = {
          text,
          voice_id: settings.selectedVoiceId || undefined,
          profile_name: settings.selectedProfile,
          ...options,
        };

        const audioBlob = await voiceClient.synthesize(request);
        setLastSynthesizedAudio(audioBlob);
        return audioBlob;
      } catch (err) {
        const error = err as Error;
        setSynthesisError(error.message);
        throw error;
      } finally {
        setIsSynthesizing(false);
      }
    },
    [voiceClient, settings.ttsEnabled, settings.selectedVoiceId, settings.selectedProfile]
  );

  const speakText = useCallback(
    async (text: string, options?: Partial<SynthesizeRequest>): Promise<void> => {
      const audioBlob = await synthesize(text, options);
      player.setSource(audioBlob);
      await player.play();
    },
    [synthesize, player]
  );

  const startRecording = useCallback(async (): Promise<void> => {
    console.log('[useVoice] startRecording called');
    await recorder.startRecording();
    lastRecordingRef.current = null;
    setLastTranscript(null);
    setTranscriptionError(null);
    console.log('[useVoice] Recording started');
  }, [recorder]);

  const stopRecording = useCallback(async (): Promise<Blob> => {
    console.log('[useVoice] stopRecording called, autoTranscribe:', finalConfig.autoTranscribe);
    
    const audioBlob = await recorder.stopRecording();
    console.log('[useVoice] Recording stopped, blob size:', audioBlob.size, 'type:', audioBlob.type);
    lastRecordingRef.current = audioBlob;

    if (finalConfig.autoTranscribe) {
      console.log('[useVoice] Auto-transcribe enabled, calling transcribe...');
      try {
        await transcribe(audioBlob);
        console.log('[useVoice] Auto-transcribe completed successfully');
      } catch (err) {
        console.error('[useVoice] Auto-transcribe failed:', err);
        // Don't throw - recording still succeeded
      }
    } else {
      console.log('[useVoice] Auto-transcribe disabled, skipping transcription');
    }

    return audioBlob;
  }, [recorder, transcribe, finalConfig.autoTranscribe]);

  const cancelRecording = useCallback(() => {
    recorder.cancelRecording();
    lastRecordingRef.current = null;
    setLastTranscript(null);
  }, [recorder]);

  const playAudio = useCallback(async (): Promise<void> => {
    player.setVolume(settings.volume);
    player.setPlaybackRate(settings.playbackSpeed);
    await player.play();
  }, [player, settings.volume, settings.playbackSpeed]);

  const pauseAudio = useCallback(() => {
    player.pause();
  }, [player]);

  const stopAudio = useCallback(() => {
    player.stop();
  }, [player]);

  const setVolume = useCallback(
    (volume: number) => {
      player.setVolume(volume);
    },
    [player]
  );

  const recordAndTranscribe = useCallback(async (): Promise<TranscriptResponse> => {
    await startRecording();
    throw new Error('Recording started - call stopRecording() when done');
  }, [startRecording]);

  const synthesizeAndPlay = useCallback(
    async (text: string, options?: Partial<SynthesizeRequest>): Promise<void> => {
      await speakText(text, options);
    },
    [speakText]
  );

  const clearErrors = useCallback(() => {
    recorder.clearError();
    player.clearError();
    setTranscriptionError(null);
    setSynthesisError(null);
  }, [recorder, player]);

  return {
    isRecording: recorder.isRecording,
    recordingDuration: recorder.duration,
    audioLevel: recorder.audioLevel,
    hasRecordingPermission: recorder.hasPermission,
    isPlaying: player.isPlaying,
    playbackCurrentTime: player.currentTime,
    playbackDuration: player.duration,
    playbackVolume: player.volume,
    isTranscribing,
    isSynthesizing,
    lastTranscript,
    lastSynthesizedAudio,
    recordingError: recorder.error,
    playbackError: player.error,
    transcriptionError,
    synthesisError,
    startRecording,
    stopRecording,
    cancelRecording,
    playAudio,
    pauseAudio,
    stopAudio,
    setVolume,
    transcribe,
    synthesize,
    speakText,
    recordAndTranscribe,
    synthesizeAndPlay,
    clearErrors,
  };
}
