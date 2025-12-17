/**
 * Voice Transcript Component
 *
 * Displays real-time transcription of voice conversation.
 * Implements specification Section 6.5: Voice Transcript Display
 *
 * Features:
 * - User and agent transcripts in distinct styles
 * - In-progress transcripts with visual indication
 * - Auto-scroll to latest content
 * - Copyable transcript text
 * - Virtualization for long conversations
 */

"use client";

import React, { useRef, useEffect, useState } from "react";
import { useVoiceAssistant } from "@livekit/components-react";
import { useVoiceMode } from "./VoiceModeProvider";
import type { TranscriptEntry } from "@/lib/types/voice";
import { useConversationHistory } from "@/lib/contexts/ConversationHistoryContext";

interface VoiceTranscriptProps {
  className?: string;
}

/**
 * Voice Transcript Component
 *
 * Displays conversation transcripts with auto-scroll.
 */
export const VoiceTranscript: React.FC<VoiceTranscriptProps> = ({
  className = "",
}) => {
  const { agentTranscriptions } = useVoiceAssistant();
  const { orchestrationTrace } = useVoiceMode();
  const { addMessage } = useConversationHistory();
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const seenTraceIdsRef = useRef<Set<string>>(new Set());

  /**
   * Update entries from LiveKit transcriptions
   */
  useEffect(() => {
    if (agentTranscriptions && agentTranscriptions.length > 0) {
      const newEntries: TranscriptEntry[] = agentTranscriptions.map((t, i) => {
        // LiveKit transcriptions: ReceivedTranscriptionSegment
        // Properties: text, final, firstReceivedTime, lastReceivedTime, id, language
        // We need to infer role from context

        return {
          id: `${t.id || i}`,
          role: "agent" as const, // Transcriptions from LiveKit are agent responses
          text: t.text || "",
          isFinal: t.final ?? false,
          timestamp: new Date(t.lastReceivedTime || Date.now()),
        };
      });

      setEntries(newEntries);
    }
  }, [agentTranscriptions]);

  /**
   * Fallback transcript source: MoE orchestration trace.
   * LiveKit transcriptions may not be configured, but trace.final_response is.
   * We append one user+agent turn per unique request_id.
   */
  useEffect(() => {
    if (!orchestrationTrace?.request_id) return;
    const id = orchestrationTrace.request_id;
    if (seenTraceIdsRef.current.has(id)) return;
    seenTraceIdsRef.current.add(id);

    const now = new Date();
    const userText = orchestrationTrace.query?.trim();
    const agentText = orchestrationTrace.final_response?.trim();

    if (!userText && !agentText) return;

    setEntries((prev) => {
      const next = [...prev];
      if (userText) {
        next.push({
          id: `trace:${id}:user`,
          role: "user",
          text: userText,
          isFinal: true,
          timestamp: now,
        });
        // Add to shared conversation history
        addMessage({
          role: "user",
          content: userText,
          source: "voice",
        });
      }
      if (agentText) {
        next.push({
          id: `trace:${id}:agent`,
          role: "agent",
          text: agentText,
          isFinal: true,
          timestamp: now,
        });
        // Add to shared conversation history
        addMessage({
          role: "agent",
          content: agentText,
          source: "voice",
        });
      }
      return next.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
    });
  }, [orchestrationTrace, addMessage]);

  /**
   * Detect user scrolling
   */
  const handleScroll = () => {
    if (!scrollRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 50;

    if (!isAtBottom) {
      setIsUserScrolling(true);

      // Clear previous timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }

      // Resume auto-scroll after 3 seconds of no scrolling
      scrollTimeoutRef.current = setTimeout(() => {
        setIsUserScrolling(false);
      }, 3000);
    } else {
      setIsUserScrolling(false);
    }
  };

  /**
   * Auto-scroll to bottom when new entries added or text updates
   * Only scroll if user is not manually scrolling
   */
  useEffect(() => {
    if (!isUserScrolling && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [entries, isUserScrolling]);

  /**
   * Cleanup timeout on unmount
   */
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className={`relative h-full ${className}`}>
      {/* Use native scroll instead of ScrollArea for better control */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto p-4 custom-scrollbar"
      >
        <div className="space-y-3">
          {entries.length === 0 ? (
            <p className="text-center text-muted-foreground text-sm">
              Conversation transcript will appear here
            </p>
          ) : (
            entries.map((entry) => (
              <TranscriptBubble key={entry.id} entry={entry} />
            ))
          )}
          {/* Scroll anchor for auto-scroll */}
          <div id="transcript-end" ref={messagesEndRef} />
        </div>
      </div>

      {/* Scroll-to-bottom button (visible when user is scrolling) */}
      {isUserScrolling && (
        <button
          onClick={() => {
            setIsUserScrolling(false);
            scrollRef.current?.scrollTo({
              top: scrollRef.current.scrollHeight,
              behavior: 'smooth',
            });
          }}
          className="absolute bottom-4 right-4 p-2 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-all animate-in fade-in duration-200"
          aria-label="Scroll to bottom"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 14l-7 7m0 0l-7-7m7 7V3"
            />
          </svg>
        </button>
      )}
    </div>
  );
};

/**
 * Individual transcript bubble
 */
const TranscriptBubble: React.FC<{ entry: TranscriptEntry }> = ({ entry }) => {
  const isAgent = entry.role === "agent";

  return (
    <div
      className={`flex ${isAgent ? "justify-start" : "justify-end"}`}
    >
      <div
        className={`max-w-[80%] px-4 py-2 rounded-2xl ${
          isAgent
            ? "bg-muted text-muted-foreground rounded-bl-none"
            : "bg-primary text-primary-foreground rounded-br-none"
        } ${!entry.isFinal ? "opacity-70" : ""}`}
      >
        <p className="text-sm whitespace-pre-wrap">{entry.text}</p>
        {!entry.isFinal && (
          <span className="inline-flex items-center gap-1 text-xs opacity-70 mt-1">
            <span className="animate-pulse">●</span>
            Transcribing...
          </span>
        )}
      </div>
    </div>
  );
};
