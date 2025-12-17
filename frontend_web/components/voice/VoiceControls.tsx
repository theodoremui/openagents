/**
 * Voice Controls Component
 *
 * Provides mute, volume, and end call controls for voice sessions.
 * Implements specification Section 6.4: Voice Controls
 *
 * Features:
 * - Mute/unmute microphone toggle
 * - Volume control slider
 * - End call button
 * - Keyboard shortcuts (M for mute, Escape to end)
 * - Haptic feedback on mobile
 * - Visual feedback when muted
 */

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocalParticipant } from "@livekit/components-react";
import { Mic, MicOff, PhoneOff, Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVoiceSettings } from "@/lib/contexts/VoiceContext";

interface VoiceControlsProps {
  onEndCall: () => void;
}

/**
 * Voice Controls Component
 *
 * Provides mute, volume, and call control functionality.
 */
export const VoiceControls: React.FC<VoiceControlsProps> = ({ onEndCall }) => {
  const { localParticipant } = useLocalParticipant();
  const [isMuted, setIsMuted] = useState(false);
  const [voiceSettings, updateVoiceSettings] = useVoiceSettings();
  const volume = useMemo(
    () => Math.round((voiceSettings.volume ?? 1) * 100),
    [voiceSettings.volume]
  );
  const volumePercent = useMemo(() => `${volume}%`, [volume]);

  // IMPORTANT: Radix Slider expects a stable array reference for `value`.
  // Passing `value={[volume]}` creates a new array each render and can trigger
  // internal ref/state churn leading to "Maximum update depth exceeded".
  const handleVolumeChange = useCallback(([v]: number[]) => {
    const next = Math.max(0, Math.min(100, v));
    updateVoiceSettings({ volume: next / 100 });
  }, []);

  /**
   * Toggle microphone mute state
   */
  const toggleMute = useCallback(async () => {
    if (localParticipant) {
      const newMutedState = !isMuted;
      await localParticipant.setMicrophoneEnabled(!newMutedState);
      setIsMuted(newMutedState);

      // Haptic feedback on mobile
      if ("vibrate" in navigator) {
        navigator.vibrate(50);
      }
    }
  }, [localParticipant, isMuted]);

  /**
   * Toggle volume mute
   */
  const toggleVolumeMute = useCallback(() => {
    updateVoiceSettings({ volume: (voiceSettings.volume ?? 1) === 0 ? 1 : 0 });
  }, [updateVoiceSettings, voiceSettings.volume]);

  /**
   * Keyboard shortcuts
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        toggleMute();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onEndCall();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleMute, onEndCall]);

  return (
    <div className="flex items-center justify-center gap-4 p-4">
      {/* Mute Button */}
      <Button
        variant={isMuted ? "destructive" : "secondary"}
        size="lg"
        className={`rounded-full w-14 h-14 ${isMuted ? "animate-pulse" : ""}`}
        onClick={toggleMute}
        aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
        title={`${isMuted ? "Unmute" : "Mute"} (M)`}
      >
        {isMuted ? (
          <MicOff className="w-6 h-6" />
        ) : (
          <Mic className="w-6 h-6" />
        )}
      </Button>

      {/* Volume Control */}
      <div className="flex items-center gap-2 px-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleVolumeMute}
          aria-label={volume === 0 ? "Unmute speaker" : "Mute speaker"}
        >
          {volume === 0 ? (
            <VolumeX className="w-5 h-5" />
          ) : (
            <Volume2 className="w-5 h-5" />
          )}
        </Button>
        {/* Native range input avoids Radix Slider ref churn that can trigger infinite update loops */}
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={volume}
          onChange={(e) => {
            const v = Number(e.target.value);
            updateVoiceSettings({ volume: Math.max(0, Math.min(100, v)) / 100 });
          }}
          aria-label="Volume"
          className="w-24 accent-primary"
          style={{ backgroundSize: volumePercent }}
        />
        <span className="text-sm text-muted-foreground w-8 text-right">
          {volume}%
        </span>
      </div>

      {/* End Call Button */}
      <Button
        variant="destructive"
        size="lg"
        className="rounded-full w-14 h-14"
        onClick={onEndCall}
        aria-label="End voice session"
        title="End call (Escape)"
      >
        <PhoneOff className="w-6 h-6" />
      </Button>
    </div>
  );
};
