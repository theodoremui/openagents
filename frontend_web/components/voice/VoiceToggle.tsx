/**
 * VoiceToggle Component
 *
 * Toggle button for voice recording with visual feedback.
 * Features:
 * - Mic button with recording state
 * - Permission request handling
 * - Duration display
 * - Error handling
 * - Accessible with keyboard support
 */

'use client';

import React, { useState } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useVoice } from '@/lib/hooks/useVoice';
import { cn } from '@/lib/utils';

/**
 * VoiceToggle props
 */
export interface VoiceToggleProps {
  /** Callback when recording completes with transcript */
  onTranscript?: (text: string) => void;
  /** Callback when recording completes with audio blob */
  onRecording?: (audioBlob: Blob) => void;
  /** Enable auto-transcribe on stop */
  autoTranscribe?: boolean;
  /** Custom className */
  className?: string;
  /** Button size */
  size?: 'sm' | 'default' | 'lg' | 'icon';
  /** Button variant */
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  /** Show duration text */
  showDuration?: boolean;
  /** Disabled state */
  disabled?: boolean;
}

/**
 * Format duration in seconds to MM:SS
 */
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * VoiceToggle component
 */
export const VoiceToggle: React.FC<VoiceToggleProps> = ({
  onTranscript,
  onRecording,
  autoTranscribe = false,
  className,
  size = 'default',
  variant = 'default',
  showDuration = true,
  disabled = false,
}) => {
  const voice = useVoice({ autoTranscribe });
  const [isProcessing, setIsProcessing] = useState(false);

  /**
   * Handle toggle recording
   */
  const handleToggle = async () => {
    try {
      if (voice.isRecording) {
        // Stop recording
        setIsProcessing(true);
        const audioBlob = await voice.stopRecording();

        // Call callback with audio
        if (onRecording) {
          onRecording(audioBlob);
        }

        // If auto-transcribe is enabled and we have a transcript, call callback
        if (autoTranscribe && voice.lastTranscript) {
          if (onTranscript) {
            onTranscript(voice.lastTranscript.result.text);
          }
        }

        setIsProcessing(false);
      } else {
        // Check permission first
        if (!voice.hasRecordingPermission) {
          // This will be handled by useAudioRecorder internally
        }

        // Start recording
        await voice.startRecording();
      }
    } catch (err) {
      const error = err as Error;
      console.error('Voice toggle error:', error);
      setIsProcessing(false);
      // Error is tracked in voice.recordingError
    }
  };

  /**
   * Get button state styling
   */
  const getButtonClass = () => {
    if (voice.isRecording) {
      return 'bg-red-500 hover:bg-red-600 text-white animate-pulse';
    }
    return '';
  };

  /**
   * Get icon based on state
   */
  const getIcon = () => {
    if (isProcessing || voice.isTranscribing) {
      return <Loader2 className="h-4 w-4 animate-spin" />;
    }

    if (voice.isRecording) {
      return <Mic className="h-4 w-4" />;
    }

    if (voice.recordingError) {
      return <MicOff className="h-4 w-4" />;
    }

    return <Mic className="h-4 w-4" />;
  };

  /**
   * Get tooltip text
   */
  const getTooltip = () => {
    if (voice.recordingError) {
      return `Error: ${voice.recordingError}`;
    }

    if (voice.isRecording) {
      return 'Stop recording';
    }

    if (!voice.hasRecordingPermission) {
      return 'Click to enable microphone';
    }

    return 'Start recording';
  };

  /**
   * Get duration display
   */
  const getDurationDisplay = () => {
    if (!showDuration || !voice.isRecording) return null;

    return (
      <span className="text-xs font-mono ml-2">
        {formatDuration(voice.recordingDuration)}
      </span>
    );
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Button
        onClick={handleToggle}
        size={size}
        variant={variant}
        disabled={disabled || isProcessing}
        className={cn(getButtonClass())}
        title={getTooltip()}
        aria-label={voice.isRecording ? 'Stop recording' : 'Start recording'}
      >
        {getIcon()}
        {size !== 'icon' && (
          <span className="ml-2">
            {voice.isRecording ? 'Stop' : 'Record'}
          </span>
        )}
      </Button>

      {getDurationDisplay()}

      {/* Error display */}
      {voice.recordingError && (
        <span className="text-xs text-red-500 max-w-xs truncate">
          {voice.recordingError}
        </span>
      )}
    </div>
  );
};

export default VoiceToggle;
