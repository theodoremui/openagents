/**
 * Conversation History Context
 *
 * Shared conversation history between text chat and voice mode.
 * This ensures conversation continuity when switching between modes.
 */

"use client";

import React, { createContext, useContext, useState, useCallback, useMemo } from "react";

/**
 * Message role type
 */
export type MessageRole = "user" | "agent" | "system" | "error";

/**
 * Conversation message
 */
export interface ConversationMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  /** Source of the message (text, voice, etc.) */
  source?: "text" | "voice";
  /** Whether this is a final message or still being generated */
  isFinal?: boolean;
  /** Additional metadata (e.g., usage, mode, etc.) */
  metadata?: Record<string, unknown>;
}

/**
 * Conversation history state
 */
interface ConversationHistoryState {
  /** All messages in the conversation */
  messages: ConversationMessage[];
  /** Current agent ID for this conversation */
  agentId: string | null;
}

/**
 * Conversation history context value
 */
interface ConversationHistoryContextValue extends ConversationHistoryState {
  /** Add a message to the conversation */
  addMessage: (message: Omit<ConversationMessage, "id" | "timestamp">) => ConversationMessage;
  /** Update an existing message */
  updateMessage: (id: string, updates: Partial<ConversationMessage>) => void;
  /** Clear all messages */
  clearMessages: () => void;
  /** Set the current agent ID */
  setAgentId: (agentId: string) => void;
  /** Get messages for a specific agent */
  getMessagesForAgent: (agentId: string) => ConversationMessage[];
}

const ConversationHistoryContext = createContext<ConversationHistoryContextValue | null>(null);

/**
 * Conversation History Provider Props
 */
interface ConversationHistoryProviderProps {
  children: React.ReactNode;
}

/**
 * Generate a unique message ID
 */
function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Conversation History Provider Component
 *
 * Provides shared conversation history for text and voice modes.
 */
export const ConversationHistoryProvider: React.FC<ConversationHistoryProviderProps> = ({
  children,
}) => {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [agentId, setAgentId] = useState<string | null>(null);

  /**
   * Add a message to the conversation
   */
  const addMessage = useCallback((message: Omit<ConversationMessage, "id" | "timestamp">): ConversationMessage => {
    const newMessage: ConversationMessage = {
      ...message,
      id: generateMessageId(),
      timestamp: new Date(),
      isFinal: message.isFinal ?? true,
    };

    setMessages((prev) => [...prev, newMessage]);
    return newMessage;
  }, []);

  /**
   * Update an existing message
   */
  const updateMessage = useCallback((id: string, updates: Partial<ConversationMessage>) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
    );
  }, []);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * Get messages for a specific agent
   */
  const getMessagesForAgent = useCallback(
    (targetAgentId: string) => {
      // For now, return all messages
      // In the future, this could filter by agent if multi-agent conversations are supported
      return messages;
    },
    [messages]
  );

  const contextValue = useMemo<ConversationHistoryContextValue>(
    () => ({
      messages,
      agentId,
      addMessage,
      updateMessage,
      clearMessages,
      setAgentId,
      getMessagesForAgent,
    }),
    [messages, agentId, addMessage, updateMessage, clearMessages, getMessagesForAgent]
  );

  return (
    <ConversationHistoryContext.Provider value={contextValue}>
      {children}
    </ConversationHistoryContext.Provider>
  );
};

/**
 * Hook to use conversation history context
 *
 * @throws Error if used outside ConversationHistoryProvider
 */
export const useConversationHistory = (): ConversationHistoryContextValue => {
  const context = useContext(ConversationHistoryContext);
  if (!context) {
    throw new Error("useConversationHistory must be used within ConversationHistoryProvider");
  }
  return context;
};
