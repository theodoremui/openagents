/**
 * VoiceInputPanel Component
 * 
 * Simplified voice input panel - fixed click handling issues.
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { useVoice } from '@/lib/hooks/useVoice';
import { useVoiceSettings } from '@/lib/contexts/VoiceContext';
import { VoiceAnimation } from './VoiceAnimation';
import { cn } from '@/lib/utils';

export interface VoiceInputPanelProps {
  onTranscript?: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

export const VoiceInputPanel: React.FC<VoiceInputPanelProps> = ({
  onTranscript,
  disabled = false,
  className,
}) => {
  const voice = useVoice({ autoTranscribe: true });
  const [settings] = useVoiceSettings();
  const [isProcessing, setIsProcessing] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  
  const lastProcessedTranscriptRef = useRef<string | null>(null);
  const waitingForTranscriptRef = useRef(false);

  // Handle transcript when available
  useEffect(() => {
    if (
      voice.lastTranscript &&
      !voice.isRecording &&
      !voice.isTranscribing &&
      waitingForTranscriptRef.current
    ) {
      const transcript = voice.lastTranscript.result?.text;
      console.log('[VoiceInputPanel] Transcript received:', transcript);
      
      if (transcript && transcript !== lastProcessedTranscriptRef.current) {
        lastProcessedTranscriptRef.current = transcript;
        if (onTranscript) {
          onTranscript(transcript);
        }
      }
      
      waitingForTranscriptRef.current = false;
      setIsProcessing(false);
      setLocalError(null);
    }
  }, [voice.lastTranscript, voice.isRecording, voice.isTranscribing, onTranscript]);

  // Handle transcription errors
  useEffect(() => {
    if (voice.transcriptionError && waitingForTranscriptRef.current) {
      console.error('[VoiceInputPanel] Transcription error:', voice.transcriptionError);
      waitingForTranscriptRef.current = false;
      setIsProcessing(false);
      setLocalError(voice.transcriptionError);
    }
  }, [voice.transcriptionError]);

  // Handle recording errors
  useEffect(() => {
    if (voice.recordingError) {
      console.error('[VoiceInputPanel] Recording error:', voice.recordingError);
      setIsProcessing(false);
      waitingForTranscriptRef.current = false;
      setLocalError(voice.recordingError);
    }
  }, [voice.recordingError]);

  // Timeout for processing
  useEffect(() => {
    if (!voice.isRecording && !voice.isTranscribing && isProcessing && waitingForTranscriptRef.current) {
      const timeout = setTimeout(() => {
        if (waitingForTranscriptRef.current) {
          console.warn('[VoiceInputPanel] Voice processing timed out');
          waitingForTranscriptRef.current = false;
          setIsProcessing(false);
          setLocalError('Processing timed out. Please try again.');
        }
      }, 15000);
      return () => clearTimeout(timeout);
    }
  }, [voice.isRecording, voice.isTranscribing, isProcessing]);

  /**
   * Handle click - simple, no useCallback, reads voice.isRecording directly
   */
  const handleClick = async () => {
    console.log('=== BUTTON CLICKED ===');
    console.log('[VoiceInputPanel] voice.isRecording:', voice.isRecording);
    
    setLocalError(null);
    
    try {
      if (voice.isRecording) {
        console.log('[VoiceInputPanel] STOPPING...');
        setIsProcessing(true);
        waitingForTranscriptRef.current = true;
        lastProcessedTranscriptRef.current = null;
        
        const audioBlob = await voice.stopRecording();
        console.log('[VoiceInputPanel] Stopped! Blob size:', audioBlob?.size);
      } else {
        console.log('[VoiceInputPanel] STARTING...');
        await voice.startRecording();
        console.log('[VoiceInputPanel] Started!');
      }
    } catch (err) {
      console.error('[VoiceInputPanel] Error:', err);
      waitingForTranscriptRef.current = false;
      setIsProcessing(false);
      setLocalError(err instanceof Error ? err.message : 'Recording failed');
    }
  };

  if (!settings.sttEnabled) {
    return null;
  }

  const showSpinner = isProcessing || voice.isTranscribing;
  const isActive = voice.isRecording;
  // NEVER disable while recording - user must be able to stop
  const canClick = isActive ? true : !(disabled || isProcessing || voice.isTranscribing);

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Native button - no shadcn Button to avoid any CSS issues */}
      <button
        type="button"
        onClick={handleClick}
        disabled={!canClick}
        className={cn(
          'shrink-0 h-10 w-10 rounded-full transition-all',
          'inline-flex items-center justify-center',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          isActive 
            ? 'bg-red-500 hover:bg-red-600 text-white' 
            : 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
          !canClick && 'opacity-50 cursor-not-allowed'
        )}
        title={isActive ? 'Click to stop recording' : 'Click to start voice input'}
      >
        {showSpinner ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : isActive ? (
          <MicOff className="h-4 w-4" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </button>

      {/* Audio visualization */}
      {isActive && (
        <div className="flex-1">
          <VoiceAnimation
            audioLevel={voice.audioLevel}
            isActive={isActive}
            barCount={5}
            maxHeight={24}
            barWidth={3}
            barGap={3}
            className="h-6"
          />
        </div>
      )}

      {/* Duration */}
      {isActive && voice.recordingDuration > 0 && (
        <span className="text-xs font-mono text-muted-foreground">
          {Math.floor(voice.recordingDuration)}s
        </span>
      )}

      {/* Processing status */}
      {isProcessing && !isActive && (
        <span className="text-xs text-muted-foreground animate-pulse">
          Processing...
        </span>
      )}

      {/* Transcribing status */}
      {voice.isTranscribing && (
        <span className="text-xs text-muted-foreground">
          Transcribing...
        </span>
      )}

      {/* Error */}
      {(voice.recordingError || voice.transcriptionError || localError) && !isActive && !isProcessing && (
        <span className="text-xs text-red-500 truncate max-w-[200px]">
          {voice.recordingError || voice.transcriptionError || localError}
        </span>
      )}
    </div>
  );
};

export default VoiceInputPanel;
