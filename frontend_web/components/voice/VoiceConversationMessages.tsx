"use client";

import React from "react";
import { useRoomContext, useVoiceAssistant, useTranscriptions } from "@livekit/components-react";

export type VoiceConversationMessage = {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
};

/**
 * Time window (in milliseconds) to combine consecutive user messages.
 * Messages within this window are considered part of the same utterance.
 */
const USER_MESSAGE_MERGE_WINDOW_MS = 3000; // 3 seconds

/**
 * VoiceConversationMessages
 *
 * A small adapter that reads LiveKit transcription text streams and emits
 * a stable message list matching the Chat Interface's left/right bubble layout.
 *
 * Buffers and combines consecutive user messages that are part of the same utterance
 * to prevent fragmenting the user's query into multiple messages.
 *
 * Kept as a dedicated component to:
 * - avoid calling LiveKit hooks outside LiveKitRoom
 * - keep UnifiedChatInterface mostly modality-agnostic
 */
export const VoiceConversationMessages: React.FC<{
  onMessages: (messages: VoiceConversationMessage[]) => void;
}> = ({ onMessages }) => {
  const room = useRoomContext();
  const { agent } = useVoiceAssistant();
  const streams = useTranscriptions();

  const localIdentity = room?.localParticipant?.identity;
  const agentIdentity = agent?.identity;

  const messages = React.useMemo(() => {
    // First, map streams to messages
    const rawMessages = streams
      .filter((s) => !!s.text && s.text.trim().length > 0)
      .map((s) => {
        const identity = s.participantInfo?.identity;
        const role: "user" | "agent" = identity && agentIdentity && identity === agentIdentity ? "agent" : "user";
        const id = `${identity || 'unknown'}:${s.streamInfo?.id || 'stream'}`;
        const ts = typeof s.streamInfo?.timestamp === 'number' ? s.streamInfo.timestamp : Date.now();

        return {
          id,
          role,
          content: s.text,
          timestamp: new Date(ts),
        } satisfies VoiceConversationMessage;
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

    // Merge consecutive user messages within the time window
    const merged: VoiceConversationMessage[] = [];
    
    for (let i = 0; i < rawMessages.length; i++) {
      const current = rawMessages[i];
      
      // Agent messages are always separate (they're already final)
      if (current.role === "agent") {
        merged.push(current);
        continue;
      }

      // For user messages, check if we should merge with previous user message
      if (current.role === "user" && merged.length > 0) {
        const lastMerged = merged[merged.length - 1];
        
        // If last message was also from user and within merge window, combine them
        if (
          lastMerged.role === "user" &&
          current.timestamp.getTime() - lastMerged.timestamp.getTime() <= USER_MESSAGE_MERGE_WINDOW_MS
        ) {
          // Merge: combine content and update timestamp to the latest
          // Replace the last message with merged version
          merged[merged.length - 1] = {
            ...lastMerged,
            content: `${lastMerged.content} ${current.content}`.trim(),
            timestamp: current.timestamp, // Use the latest timestamp
            // Keep the original ID from the first message in the sequence
          };
          continue;
        }
      }

      // Start a new message (either first message, role change, or gap too large)
      merged.push({ ...current });
    }

    return merged;
  }, [streams, agentIdentity]);

  React.useEffect(() => {
    onMessages(messages);
  }, [messages, onMessages]);

  return null;
};
