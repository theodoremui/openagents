/**
 * Voice Mode Provider
 *
 * React context provider for voice mode state management.
 * Handles LiveKit connection, session creation, and state coordination.
 *
 * Based on specification Section 6.1: Voice Mode Component
 */

"use client";

import React, {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { LiveKitRoom, useLocalParticipant, useRoomContext } from "@livekit/components-react";
import { getApiClient, initializeApiClient } from "@/lib/api-client";
import type {
  AgentType,
  VoiceState,
  CreateVoiceSessionRequest,
  CreateVoiceSessionResponse,
} from "@/lib/types/voice";
import type { MoETrace } from "@/lib/visualization/types";

/**
 * Voice mode state
 */
interface VoiceModeState {
  isEnabled: boolean;
  isConnecting: boolean;
  isConnected: boolean;
  sessionId: string | null;
  roomName: string | null;
  token: string | null;
  serverUrl: string | null;
  error: Error | null;
  agentState: VoiceState;
}

/**
 * Voice mode actions
 */
type VoiceModeAction =
  | { type: "START_CONNECTING" }
  | {
      type: "SESSION_CREATED";
      payload: {
        sessionId: string;
        roomName: string;
        token: string;
        serverUrl: string;
      };
    }
  | { type: "ROOM_CONNECTED" }
  | { type: "DISCONNECTED" }
  | { type: "ERROR"; payload: Error }
  | { type: "RESET" }
  | { type: "SET_AGENT_STATE"; payload: VoiceState };

/**
 * Voice mode context value
 */
interface VoiceModeContextValue extends VoiceModeState {
  enterVoiceMode: (options?: {
    agentType?: AgentType;
    agentId?: string;
  }) => Promise<void>;
  exitVoiceMode: () => Promise<void>;
  orchestrationTrace: MoETrace | null;
}

const VoiceModeContext = createContext<VoiceModeContextValue | null>(null);

const initialState: VoiceModeState = {
  isEnabled: false,
  isConnecting: false,
  isConnected: false,
  sessionId: null,
  roomName: null,
  token: null,
  serverUrl: null,
  error: null,
  agentState: "disconnected",
};

/**
 * Voice mode reducer
 */
function voiceModeReducer(
  state: VoiceModeState,
  action: VoiceModeAction
): VoiceModeState {
  switch (action.type) {
    case "START_CONNECTING":
      return {
        ...state,
        isEnabled: true,
        isConnecting: true,
        isConnected: false,
        error: null,
        agentState: "connecting",
      };

    case "SESSION_CREATED":
      return {
        ...state,
        // Still connecting until LiveKit reports onConnected.
        isConnecting: true,
        isConnected: false,
        ...action.payload,
        agentState: "connecting",
      };

    case "ROOM_CONNECTED":
      return {
        ...state,
        isConnecting: false,
        isConnected: true,
        agentState: "initializing",
      };

    case "DISCONNECTED":
      return { ...initialState };

    case "ERROR":
      return {
        ...state,
        isConnecting: false,
        isConnected: false,
        error: action.payload,
        agentState: "disconnected",
      };

    case "RESET":
      return initialState;

    case "SET_AGENT_STATE":
      return {
        ...state,
        agentState: action.payload,
      };

    default:
      return state;
  }
}

/**
 * Voice Mode Provider Props
 */
interface VoiceModeProviderProps {
  children: React.ReactNode;
}

/**
 * Voice Mode Provider Component
 *
 * Provides voice mode state and controls to child components.
 * Manages LiveKit connection and session lifecycle.
 */
/**
 * Data Channel Listener Component
 *
 * Listens for orchestration trace data sent via LiveKit data channel.
 * Must be rendered inside LiveKitRoom to access room context.
 */
const DataChannelListener: React.FC<{
  onTraceReceived: (trace: MoETrace) => void;
}> = ({ onTraceReceived }) => {
  const room = useRoomContext();

  useEffect(() => {
    if (!room) {
      console.log('[DataChannelListener] No room available');
      return;
    }

    console.log('[DataChannelListener] Setting up data channel listener');

    const handleDataReceived = (
      payload: Uint8Array,
      participant?: any,
      kind?: any,
      topic?: string
    ) => {
      try {
        console.log('[DataChannelListener] Data received:', {
          topic,
          size: payload.length,
          participant: participant?.identity
        });

        // Decode payload
        const decoder = new TextDecoder();
        const text = decoder.decode(payload);
        const message = JSON.parse(text);

        console.log('[DataChannelListener] Decoded message:', message.type);

        // Handle orchestration trace
        if (message.type === 'moe_trace' && message.trace) {
          console.log('[DataChannelListener] 📊 MoE trace received via data channel!');
          onTraceReceived(message.trace);
        }
      } catch (error) {
        console.error('[DataChannelListener] Error processing data:', error);
      }
    };

    // Listen for data from all participants
    room.on('dataReceived', handleDataReceived);

    return () => {
      console.log('[DataChannelListener] Cleaning up data channel listener');
      room.off('dataReceived', handleDataReceived);
    };
  }, [room, onTraceReceived]);

  return null;  // This component doesn't render anything
};

export const VoiceModeProvider: React.FC<VoiceModeProviderProps> = ({
  children,
}) => {
  const [state, dispatch] = useReducer(voiceModeReducer, initialState);
  const [orchestrationTrace, setOrchestrationTrace] = useState<MoETrace | null>(null);
  const apiClient = useMemo(() => {
    // In production, ApiClient is typically initialized by ServiceProvider.
    // However, VoiceModeProvider may be mounted in isolation in tests or embedding scenarios.
    // Fall back to initializing from NEXT_PUBLIC_* env vars if needed.
    try {
      return getApiClient();
    } catch {
      return initializeApiClient();
    }
  }, []);

  // Callback for data channel trace reception
  const handleTraceReceived = useCallback((trace: MoETrace) => {
    console.log('[VoiceModeProvider] ✅ Trace received via data channel');
    setOrchestrationTrace(trace);
  }, []);

  /**
   * Enter voice mode - create session and connect
   */
  const enterVoiceMode = useCallback(
    async (options?: {
      agentType?: AgentType;
      agentId?: string;
    }) => {
      dispatch({ type: "START_CONNECTING" });

      try {
        // Request microphone permission
        await navigator.mediaDevices.getUserMedia({ audio: true });

        // Create voice session
        const request: CreateVoiceSessionRequest = {
          agentType: options?.agentType || "moe",  // Default to MoE for visualization
          agentId: options?.agentId,
          initialGreeting: true,
        };

        const session: CreateVoiceSessionResponse =
          await apiClient.createVoiceSession(request);

        dispatch({
          type: "SESSION_CREATED",
          payload: {
            sessionId: session.sessionId,
            roomName: session.roomName,
            token: session.token,
            serverUrl: session.url,
          },
        });
      } catch (error) {
        console.error("Failed to enter voice mode:", error);
        dispatch({ type: "ERROR", payload: error as Error });
      }
    },
    [apiClient]
  );

  /**
   * Exit voice mode - end session and disconnect
   */
  const exitVoiceMode = useCallback(async () => {
    if (state.sessionId) {
      try {
        await apiClient.endVoiceSession(state.sessionId);
      } catch (error) {
        console.error("Failed to end voice session:", error);
      }
    }
    dispatch({ type: "DISCONNECTED" });
  }, [state.sessionId, apiClient]);

  /**
   * Poll for MoE trace data when connected
   *
   * Continuously polls for trace data while connected to capture MoE orchestration
   * visualization. Trace becomes available after MoE processes a query.
   */
  useEffect(() => {
    // The preferred mechanism for trace delivery is the LiveKit data channel
    // (see DataChannelListener). Polling is retained only as an optional fallback.
    //
    // This completely avoids noisy server logs (and wasted requests) while the
    // realtime agent is still initializing or before any trace exists.
    if (process.env.NEXT_PUBLIC_ENABLE_TRACE_POLLING !== 'true') {
      return;
    }

    // CRITICAL: Use roomName (not sessionId) as it matches the backend session_id
    if (!state.roomName || !state.isConnected) {
      console.log('[VoiceModeProvider] Skipping trace poll: no roomName or not connected');
      return;
    }

    // Poll continuously while connected (not just during thinking/processing)
    // Trace data is stored after MoE execution and persists for 5 minutes
    console.log('[VoiceModeProvider] Starting trace polling for room:', state.roomName);

    const pollInterval = setInterval(async () => {
      try {
        const url = `${apiClient.baseUrl}/voice/realtime/session/${state.roomName}/trace`;

        const response = await fetch(url, {
          headers: {
            'X-API-Key': apiClient.apiKey || '',
          },
        });

        if (response.ok) {
          // Handle empty responses (204 No Content)
          if (response.status === 204) {
            // No content, trace not available yet
            return;
          }

          // Check if response has content before parsing
          const contentLength = response.headers.get("content-length");
          if (contentLength === "0") {
            return;
          }

          // Get text first to check if there's content
          const text = await response.text();
          if (!text || text.trim().length === 0) {
            return;
          }

          try {
            const data = JSON.parse(text);
            console.log('[VoiceModeProvider] ✅ Trace data received:', data);
            if (data.trace) {
              setOrchestrationTrace(data.trace);
              console.log('[VoiceModeProvider] 📊 Trace set in state');
            }
          } catch (parseError) {
            console.warn('[VoiceModeProvider] Failed to parse trace JSON:', parseError);
          }
        } else if (response.status !== 204 && response.status !== 404) {
          console.error('[VoiceModeProvider] Failed to fetch trace:', response.status, response.statusText);
        }
        // Silently ignore 204/404 - trace not available yet
      } catch (error) {
        console.error('[VoiceModeProvider] Error polling trace:', error);
      }
    }, 1000); // Poll every 1 second (reduced frequency since it's continuous)

    return () => {
      console.log('[VoiceModeProvider] Stopping trace polling');
      clearInterval(pollInterval);
    };
  }, [state.roomName, state.isConnected, apiClient]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (state.isConnected && state.sessionId) {
        apiClient.endVoiceSession(state.sessionId).catch(console.error);
      }
    };
  }, [state.isConnected, state.sessionId, apiClient]);

  const contextValue: VoiceModeContextValue = useMemo(
    () => ({
      ...state,
      enterVoiceMode,
      exitVoiceMode,
      orchestrationTrace,
    }),
    [state, enterVoiceMode, exitVoiceMode, orchestrationTrace]
  );

  return (
    <VoiceModeContext.Provider value={contextValue}>
      {state.isEnabled && state.token && state.serverUrl ? (
        <LiveKitRoom
          serverUrl={state.serverUrl}
          token={state.token}
          connect={true}
          connectOptions={{ autoSubscribe: true }}
          audio={true}
          video={false}
          onConnected={() => {
            console.log('[VoiceMode] ✅ Connected to LiveKit room');
            console.log('[VoiceMode] Audio enabled: true');
            console.log('[VoiceMode] Server URL:', state.serverUrl);
            console.log('[VoiceMode] Room:', state.roomName);
            dispatch({ type: "ROOM_CONNECTED" });
          }}
          onDisconnected={() => {
            console.log('[VoiceMode] Disconnected from LiveKit room');
            dispatch({ type: "DISCONNECTED" });
          }}
          onError={(error) => {
            console.error('[VoiceMode] ❌ LiveKit error:', error);
            dispatch({ type: "ERROR", payload: error });
          }}
        >
          <MicrophoneAutoEnable />
          <DataChannelListener onTraceReceived={handleTraceReceived} />
          {children}
        </LiveKitRoom>
      ) : (
        children
      )}
    </VoiceModeContext.Provider>
  );
};

/**
 * MicrophoneAutoEnable
 *
 * Ensures the local microphone track is actually published after room connect.
 * Some LiveKit setups can default to mic disabled unless explicitly enabled.
 */
const MicrophoneAutoEnable: React.FC = () => {
  const { localParticipant } = useLocalParticipant();
  const [attempted, setAttempted] = useState(false);

  useEffect(() => {
    if (!localParticipant || attempted) return;
    setAttempted(true);
    (async () => {
      try {
        await localParticipant.setMicrophoneEnabled(true);
        console.log("[VoiceMode] 🎙️ Microphone enabled");
      } catch (err) {
        console.warn("[VoiceMode] Failed to enable microphone:", err);
      }
    })();
  }, [localParticipant, attempted]);

  return null;
};

/**
 * Hook to use voice mode context
 *
 * @throws Error if used outside VoiceModeProvider
 */
export const useVoiceMode = (): VoiceModeContextValue => {
  const context = useContext(VoiceModeContext);
  if (!context) {
    throw new Error("useVoiceMode must be used within VoiceModeProvider");
  }
  return context;
};
