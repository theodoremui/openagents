/**
 * Voice Components
 *
 * Central export for all voice-related components.
 * Implements specification Section 6: Frontend Specification
 */

export { VoiceModeProvider, useVoiceMode } from "./VoiceModeProvider";
export { VoiceStateAnimation } from "./VoiceStateAnimation";
export { VoiceControls } from "./VoiceControls";
export { VoiceTranscript } from "./VoiceTranscript";
export { VoiceModeInterface } from "./VoiceModeInterface";

// Re-export types for convenience
export type {
  VoiceState,
  AgentType,
  CreateVoiceSessionRequest,
  CreateVoiceSessionResponse,
  VoiceSessionStatus,
  TranscriptEntry,
} from "@/lib/types/voice";
export { VoiceConversationMessages } from "./VoiceConversationMessages";
export type { VoiceConversationMessage } from "./VoiceConversationMessages";
