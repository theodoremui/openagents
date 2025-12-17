/**
 * Voice Mode Interface Component
 *
 * Full-screen dedicated interface for voice conversations.
 * Implements specification Section 6.3: Voice Mode Interface
 *
 * Features:
 * - Prominent state animation display
 * - Real-time transcript view
 * - Voice controls (mute, volume, end call)
 * - Connection status and quality indicators
 * - Mobile responsive
 * - Landscape and portrait support
 */

"use client";

import React from "react";
import {
  RoomAudioRenderer,
  useLocalParticipant,
  useRemoteParticipants,
  useRoomContext,
  useVoiceAssistant,
} from "@livekit/components-react";
import { useVoiceMode } from "./VoiceModeProvider";
import { VoiceStateAnimation } from "./VoiceStateAnimation";
import { VoiceTranscript } from "./VoiceTranscript";
import { MoEFlowVisualization } from "@/components/visualization/orchestration/MoEFlowVisualization";
import { X, ChevronRight, ChevronLeft, Mic, MicOff, Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVoiceSettings } from "@/lib/contexts/VoiceContext";

interface VoiceModeInterfaceProps {
  onClose: () => void;
}

const VIS_PANEL_WIDTH_STORAGE_KEY = "openagents.voice.moePanelWidthPct";
const VIS_PANEL_MIN_PCT = 25;
const VIS_PANEL_MAX_PCT = 65;
const VIS_PANEL_DEFAULT_PCT = 40;

/**
 * Voice Mode Interface Component
 *
 * Full-screen interface for voice conversations.
 */
export const VoiceModeInterface: React.FC<VoiceModeInterfaceProps> = ({
  onClose,
}) => {
  const { agentState, exitVoiceMode, orchestrationTrace } = useVoiceMode();
  const { state } = useVoiceAssistant();
  const { localParticipant } = useLocalParticipant();
  const remoteParticipants = useRemoteParticipants();
  const room = useRoomContext();
  const [voiceSettings, updateVoiceSettings] = useVoiceSettings();

  // State for collapsible visualization panel
  const [visualizationOpen, setVisualizationOpen] = React.useState(true);
  const [panelWidthPct, setPanelWidthPct] = React.useState<number>(VIS_PANEL_DEFAULT_PCT);
  const resizeContainerRef = React.useRef<HTMLDivElement | null>(null);
  const isResizingRef = React.useRef(false);
  const [audioStartError, setAudioStartError] = React.useState<string | null>(null);
  const [noRemoteAudio, setNoRemoteAudio] = React.useState(false);

  // Voice controls state (moved from VoiceControls component)
  const [isMuted, setIsMuted] = React.useState(false);
  const volume = React.useMemo(
    () => Math.round((voiceSettings.volume ?? 1) * 100),
    [voiceSettings.volume]
  );
  const volumePercent = React.useMemo(() => `${volume}%`, [volume]);

  // Load persisted panel width
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem(VIS_PANEL_WIDTH_STORAGE_KEY);
    if (!raw) return;
    const parsed = Number(raw);
    if (Number.isFinite(parsed)) {
      const clamped = Math.max(VIS_PANEL_MIN_PCT, Math.min(VIS_PANEL_MAX_PCT, parsed));
      setPanelWidthPct(clamped);
    }
  }, []);

  // Persist panel width
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(VIS_PANEL_WIDTH_STORAGE_KEY, String(panelWidthPct));
  }, [panelWidthPct]);

  // Drag-to-resize divider behavior (pointer events)
  const onResizePointerDown = (e: React.PointerEvent) => {
    if (!resizeContainerRef.current) return;
    isResizingRef.current = true;
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    e.preventDefault();
    e.stopPropagation();
  };

  const onResizePointerMove = (e: React.PointerEvent) => {
    if (!isResizingRef.current) return;
    const container = resizeContainerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const clampedX = Math.max(0, Math.min(rect.width, x));
    const rightPct = ((rect.width - clampedX) / rect.width) * 100;
    const clampedPct = Math.max(VIS_PANEL_MIN_PCT, Math.min(VIS_PANEL_MAX_PCT, rightPct));
    setPanelWidthPct(clampedPct);
    e.preventDefault();
    e.stopPropagation();
  };

  const onResizePointerUp = (e: React.PointerEvent) => {
    if (!isResizingRef.current) return;
    isResizingRef.current = false;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    e.preventDefault();
    e.stopPropagation();
  };

  // Mouse fallback (jsdom + some environments don’t fully support pointer events)
  const cleanupMouseListenersRef = React.useRef<(() => void) | null>(null);
  const onResizeMouseDown = (e: React.MouseEvent) => {
    if (!resizeContainerRef.current) return;
    isResizingRef.current = true;

    cleanupMouseListenersRef.current?.();
    cleanupMouseListenersRef.current = null;

    const onMove = (ev: MouseEvent) => {
      if (!isResizingRef.current) return;
      const container = resizeContainerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const clampedX = Math.max(0, Math.min(rect.width, x));
      const rightPct = ((rect.width - clampedX) / rect.width) * 100;
      const clampedPct = Math.max(VIS_PANEL_MIN_PCT, Math.min(VIS_PANEL_MAX_PCT, rightPct));
      setPanelWidthPct(clampedPct);
      ev.preventDefault();
      ev.stopPropagation();
    };
    const onUp = (ev: MouseEvent) => {
      isResizingRef.current = false;
      window.removeEventListener("mousemove", onMove, true);
      window.removeEventListener("mouseup", onUp, true);
      cleanupMouseListenersRef.current = null;
      ev.preventDefault();
      ev.stopPropagation();
    };

    window.addEventListener("mousemove", onMove, true);
    window.addEventListener("mouseup", onUp, true);
    cleanupMouseListenersRef.current = () => {
      window.removeEventListener("mousemove", onMove, true);
      window.removeEventListener("mouseup", onUp, true);
    };

    e.preventDefault();
    e.stopPropagation();
  };

  React.useEffect(() => {
    return () => {
      cleanupMouseListenersRef.current?.();
      cleanupMouseListenersRef.current = null;
    };
  }, []);

  // Apply global speaker settings to any audio elements created by LiveKit.
  // This ensures the user's "volume" + "TTS enabled" toggles actually affect playback.
  React.useEffect(() => {
    if (typeof document === "undefined") return;
    const volume = Math.max(0, Math.min(1, voiceSettings.volume ?? 1));
    const shouldPlay = !!voiceSettings.ttsEnabled && volume > 0;

    const applyToAll = () => {
      const audios = Array.from(document.querySelectorAll("audio"));
      for (const el of audios) {
        // Avoid muting mic loopback etc. LiveKit uses <audio> for remote tracks.
        el.muted = !shouldPlay;
        el.volume = volume;
        el.playbackRate = voiceSettings.playbackSpeed ?? 1;
        el.autoplay = true;
        el.setAttribute("playsinline", "true");
      }
    };

    applyToAll();

    // Observe for new audio elements (remote tracks can arrive after connect)
    const observer = new MutationObserver(() => applyToAll());
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [voiceSettings.ttsEnabled, voiceSettings.volume, voiceSettings.playbackSpeed]);

  // Attempt to unlock audio playback (autoplay policy).
  React.useEffect(() => {
    if (!room) return;

    (async () => {
      try {
        const maybeStartAudio = (room as any).startAudio as undefined | (() => Promise<void>);
        if (!maybeStartAudio) return;
        await maybeStartAudio();
        setAudioStartError(null);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Audio playback was blocked by the browser";
        console.warn("[VoiceModeInterface] Audio start blocked:", err);
        setAudioStartError(msg);
      }
    })();
  }, [room]);

  // Debug: Log orchestration trace changes
  React.useEffect(() => {
    if (orchestrationTrace) {
      console.log('[VoiceModeInterface] 📊 Orchestration trace received:', orchestrationTrace);
    } else {
      console.log('[VoiceModeInterface] No orchestration trace yet');
    }
  }, [orchestrationTrace]);

  // Debug: Log all participants and their audio tracks
  React.useEffect(() => {
    console.log('[VoiceModeInterface] === AUDIO DIAGNOSTICS ===');
    console.log('[VoiceModeInterface] Room state:', room?.state);
    console.log('[VoiceModeInterface] Total participants:', 1 + remoteParticipants.length);

    if (localParticipant) {
      console.log('[VoiceModeInterface] Local participant:', localParticipant.identity);
      console.log('[VoiceModeInterface] Local audio tracks:', localParticipant.audioTrackPublications.size);
    }

    console.log('[VoiceModeInterface] Remote participants:', remoteParticipants.length);
    let hasRemoteAudioTrack = false;
    remoteParticipants.forEach((participant, index) => {
      console.log(`[VoiceModeInterface] Remote participant ${index}:`, {
        identity: participant.identity,
        audioTracks: participant.audioTrackPublications.size,
        isSpeaking: participant.isSpeaking,
      });

      participant.audioTrackPublications.forEach((pub, key) => {
        if (pub.isSubscribed && pub.track && !pub.isMuted && pub.isEnabled) {
          hasRemoteAudioTrack = true;
        }
        console.log(`[VoiceModeInterface] Remote audio track:`, {
          key,
          kind: pub.kind,
          source: pub.source,
          subscribed: pub.isSubscribed,
          enabled: pub.isEnabled,
          muted: pub.isMuted,
          track: pub.track ? 'available' : 'null',
        });
      });
    });

    console.log('[VoiceModeInterface] =========================');
    setNoRemoteAudio(remoteParticipants.length > 0 && !hasRemoteAudioTrack);
  }, [localParticipant, remoteParticipants, room]);

  /**
   * Handle end call - cleanup and close
   */
  const handleEndCall = async () => {
    await exitVoiceMode();
    onClose();
  };

  /**
   * Toggle microphone mute state
   */
  const toggleMute = React.useCallback(async () => {
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
  const toggleVolumeMute = React.useCallback(() => {
    updateVoiceSettings({ volume: (voiceSettings.volume ?? 1) === 0 ? 1 : 0 });
  }, [updateVoiceSettings, voiceSettings.volume]);

  /**
   * Handle volume change
   */
  const handleVolumeChange = React.useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value);
    updateVoiceSettings({ volume: Math.max(0, Math.min(100, v)) / 100 });
  }, [updateVoiceSettings]);

  // Keyboard shortcuts for voice controls (after function declarations)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        toggleMute();
      } else if (e.key === "Escape") {
        e.preventDefault();
        handleEndCall();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleMute, handleEndCall]);

  /**
   * Get state label for display
   */
  const getStateLabel = (currentState: string): string => {
    const labels: Record<string, string> = {
      disconnected: "Not Connected",
      connecting: "Connecting...",
      initializing: "Starting Agent...",
      listening: "Listening",
      processing: "Processing...",
      thinking: "Thinking...",
      speaking: "Speaking",
    };
    return labels[currentState] || "Unknown";
  };

  /**
   * Get hint text for current state
   */
  const getStateHint = (currentState: string): string => {
    const hints: Record<string, string> = {
      disconnected: "Click the button below to start voice mode",
      connecting: "Establishing secure connection",
      initializing: "The voice agent is preparing to assist you",
      listening: "Speak naturally. The agent will respond when you pause.",
      processing: "Converting your speech to text...",
      thinking: "Processing your request...",
      speaking: "You can interrupt at any time by speaking",
    };
    return hints[currentState] || "";
  };

  /**
   * Get connection quality indicator
   */
  const getConnectionQuality = () => {
    if (!localParticipant) return null;

    // This would ideally come from LiveKit connection stats
    return (
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-green-500" />
        <span className="text-xs text-muted-foreground">Connected</span>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-background flex flex-col">
      {/* Required for reliable remote audio playback */}
      <RoomAudioRenderer />

      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b glass-panel">
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full ${
              agentState === "listening" || agentState === "speaking"
                ? "bg-green-500"
                : "bg-amber-500"
            }`}
          />
          <span className="text-sm font-medium capitalize">
            {getStateLabel(agentState)}
          </span>
        </div>

        <div className="flex items-center gap-4">
          {/* Voice Controls - Moved from footer */}
          <div className="flex items-center gap-3">
            {/* Mute Button */}
            <Button
              variant={isMuted ? "destructive" : "secondary"}
              size="sm"
              className={`rounded-full w-10 h-10 ${isMuted ? "animate-pulse" : ""}`}
              onClick={toggleMute}
              aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
              title={`${isMuted ? "Unmute" : "Mute"} (M)`}
            >
              {isMuted ? (
                <MicOff className="w-4 h-4" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </Button>

            {/* Volume Control */}
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="rounded-full w-8 h-8 p-0"
                onClick={toggleVolumeMute}
                aria-label={volume === 0 ? "Unmute speaker" : "Mute speaker"}
              >
                {volume === 0 ? (
                  <VolumeX className="w-4 h-4" />
                ) : (
                  <Volume2 className="w-4 h-4" />
                )}
              </Button>
              {/* Native range input */}
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={volume}
                onChange={handleVolumeChange}
                aria-label="Volume"
                className="w-20 h-1 accent-primary cursor-pointer"
                style={{ backgroundSize: volumePercent }}
              />
              <span className="text-xs text-muted-foreground w-8 text-right tabular-nums">
                {volume}%
              </span>
            </div>
          </div>

          {getConnectionQuality()}

          {/* End Voice Mode Button */}
          <Button
            variant="destructive"
            size="sm"
            onClick={handleEndCall}
            aria-label="End voice session"
            title="End Voice Mode (Escape)"
            className="rounded-full"
          >
            <X className="w-5 h-5" />
            <span className="ml-2 hidden sm:inline">End Voice Mode</span>
          </Button>
        </div>
      </header>

      {/* Autoplay blocked banner */}
      {audioStartError && (
        <div className="px-4 py-2 border-b bg-amber-50 text-amber-900 flex items-center justify-between gap-3">
          <div className="text-sm">
            <span className="font-medium">Audio is blocked.</span>{" "}
            Click “Enable audio” to hear responses.
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={async () => {
              try {
                const maybeStartAudio = (room as any)?.startAudio as undefined | (() => Promise<void>);
                if (maybeStartAudio) await maybeStartAudio();
                setAudioStartError(null);
              } catch (err) {
                const msg =
                  err instanceof Error ? err.message : "Audio playback was blocked by the browser";
                setAudioStartError(msg);
              }
            }}
          >
            Enable audio
          </Button>
        </div>
      )}

      {/* No remote audio banner (agent not publishing / not subscribed) */}
      {!audioStartError && noRemoteAudio && (
        <div className="px-4 py-2 border-b bg-slate-50 text-slate-900 flex items-center justify-between gap-3">
          <div className="text-sm">
            <span className="font-medium">No agent audio track detected.</span>{" "}
            This is usually a LiveKit worker connectivity/auth issue (not a frontend setting).
          </div>
        </div>
      )}

      {/* Main Content - Split layout with collapsible right panel */}
      <main className="flex-1 flex overflow-hidden relative">
        {/* Left: Transcript and main content */}
        <div
          ref={resizeContainerRef}
          className="flex-1 flex overflow-hidden relative"
        >
          {/* Left: Transcript and main content */}
          <div
            className="flex-1 flex flex-col transition-[width] duration-150 ease-out"
            style={{
              width:
                orchestrationTrace && visualizationOpen
                  ? `${100 - panelWidthPct}%`
                  : "100%",
            }}
          >
          <div className="flex-1 flex flex-col items-center justify-center p-8 overflow-hidden">
            {orchestrationTrace && !visualizationOpen ? (
              <div className="flex flex-col items-center gap-4">
                <p className="text-lg text-muted-foreground">MoE visualization available</p>
                <p className="text-sm text-muted-foreground">
                  Click the panel button on the right to view
                </p>
              </div>
            ) : !orchestrationTrace && (agentState === "listening" || agentState === "speaking" || agentState === "thinking" || agentState === "processing") ? (
              <div className="flex flex-col items-center gap-4">
                <p className="text-lg text-muted-foreground">Waiting for MoE orchestration trace...</p>
                <p className="text-sm text-muted-foreground">
                  (Trace will appear after the agent processes a complex query)
                </p>
              </div>
            ) : (
              <>
                {/* Only show state animation during initial states */}
                {(agentState === "connecting" || agentState === "initializing") && (
                  <>
                    {/* State Animation */}
                    <div className="mb-8">
                      <VoiceStateAnimation className="w-40 h-40 md:w-56 md:h-56" />
                    </div>

                    {/* State Label */}
                    <h2 className="text-2xl font-semibold mb-4">
                      {getStateLabel(agentState)}
                    </h2>

                    {/* Hint Text */}
                    <p className="text-muted-foreground text-center max-w-md">
                      {getStateHint(agentState)}
                    </p>
                  </>
                )}
              </>
            )}
          </div>

          {/* Transcript at bottom - Expanded height since controls moved to header */}
          <div className="h-64 border-t glass-panel overflow-hidden">
            <div className="p-3 border-b">
              <h3 className="text-sm font-medium">Conversation</h3>
            </div>
            <VoiceTranscript className="h-[calc(100%-3rem)]" />
          </div>
          </div>

          {/* Right: Collapsible visualization panel (always rendered; shows placeholder until trace arrives) */}
          <>
              {/* Collapse/Expand button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setVisualizationOpen(!visualizationOpen)}
                className="absolute top-1/2 -translate-y-1/2 z-30 bg-white/90 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.2)] hover:shadow-[0_8px_32px_0_rgba(31,38,135,0.3)] rounded-full p-2"
                style={{
                  right: visualizationOpen ? `calc(${panelWidthPct}% - 12px)` : "1rem",
                }}
                aria-label={visualizationOpen ? "Collapse visualization" : "Expand visualization"}
              >
                {visualizationOpen ? (
                  <ChevronRight className="w-5 h-5" />
                ) : (
                  <ChevronLeft className="w-5 h-5" />
                )}
              </Button>

              {/* Draggable divider */}
              {visualizationOpen && (
                <div
                  data-testid="voice-moe-resize-divider"
                  role="separator"
                  aria-orientation="vertical"
                  aria-label="Resize orchestration panel"
                  className="absolute top-0 bottom-0 z-40 cursor-col-resize group"
                  style={{ right: `${panelWidthPct}%`, width: "14px", touchAction: "none" as any }}
                  onPointerDown={onResizePointerDown}
                  onPointerMove={onResizePointerMove}
                  onPointerUp={onResizePointerUp}
                  onMouseDown={onResizeMouseDown}
                >
                  {/* full-height edge line */}
                  <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-[2px] bg-border/60 group-hover:bg-primary/50 transition-colors" />
                  {/* visible grip */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-5 h-14 rounded-full border border-border/70 bg-white/85 backdrop-blur-sm shadow-md group-hover:shadow-lg group-hover:border-primary/40 transition-all" />
                </div>
              )}

              {/* Visualization panel */}
              <div
                className="border-l glass-panel transition-[width] duration-150 ease-out overflow-hidden"
                style={{
                  width: visualizationOpen ? `${panelWidthPct}%` : "0%",
                }}
              >
                <div className="h-full flex flex-col">
                  <div className="p-3 border-b flex items-center justify-between">
                    <h3 className="text-sm font-medium">Orchestration Flow</h3>
                    <div className="text-xs text-muted-foreground tabular-nums">
                      {Math.round(panelWidthPct)}%
                    </div>
                  </div>
                  <div className="flex-1 overflow-hidden">
                    {orchestrationTrace ? (
                      <MoEFlowVisualization trace={orchestrationTrace} />
                    ) : (
                      <div className="h-full flex items-center justify-center text-sm text-muted-foreground p-4 text-center">
                        Waiting for MoE orchestration trace…
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
        </div>
      </main>
    </div>
  );
};
