/**
 * Voice Mode Type Definitions
 *
 * Type definitions for real-time voice functionality, matching backend models
 * from server/voice/realtime/models.py
 */

/**
 * Voice agent state during conversation.
 * Matches VoiceState enum from backend.
 */
export type VoiceState =
  | 'disconnected'
  | 'connecting'
  | 'initializing'
  | 'listening'
  | 'processing'
  | 'thinking'
  | 'speaking';

/**
 * Type of underlying agent for voice session.
 * Matches AgentType enum from backend.
 */
export type AgentType = 'moe' | 'smart_router' | 'single_agent';

/**
 * Request to create a new real-time voice session.
 * Matches RealtimeSessionRequest from backend.
 */
export interface CreateVoiceSessionRequest {
  agentType?: AgentType;
  agentId?: string;
  agentConfig?: Record<string, unknown>;
  initialGreeting?: boolean;
}

/**
 * Response containing voice session connection details.
 * Matches RealtimeSessionResponse from backend.
 */
export interface CreateVoiceSessionResponse {
  sessionId: string;
  roomName: string;
  token: string;
  url: string;
}

/**
 * Current status of a voice session.
 * Matches RealtimeSessionStatus from backend.
 */
export interface VoiceSessionStatus {
  sessionId: string;
  roomName: string;
  isActive: boolean;
  participantCount: number;
  agentConnected: boolean;
  agentState?: VoiceState;
  createdAt: string;
  durationSeconds: number;
}

/**
 * Voice configuration settings.
 * Subset of voice_config.yaml settings.
 */
export interface VoiceConfig {
  sttModel: string;
  llmModel: string;
  ttsModel: string;
  ttsVoice: string;
  enableThinkingSound: boolean;
  thinkingVolume: number;
  allowInterruptions: boolean;
}

/**
 * Transcript entry for conversation display.
 */
export interface TranscriptEntry {
  id: string;
  role: 'user' | 'agent';
  text: string;
  isFinal: boolean;
  timestamp: Date;
}

/**
 * Voice mode error with context.
 */
export interface VoiceError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
