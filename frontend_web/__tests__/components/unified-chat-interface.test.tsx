/**
 * Tests for UnifiedChatInterface Component
 *
 * Tests the unified chat interface for all execution modes:
 * - Mock execution
 * - Real execution
 * - Stream execution
 *
 * Tests user interactions, message display, and error handling.
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { UnifiedChatInterface } from "@/components/unified-chat-interface";
import type { IAgentExecutionService, ISessionService } from "@/lib/services/interfaces";
import type { SimulationResponse, StreamChunk } from "@/lib/types";
import { ServiceProvider } from "@/lib/services/ServiceContext";
import { SmartRouterProvider } from "@/lib/contexts/SmartRouterContext";
import { VoiceProvider } from "@/lib/contexts/VoiceContext";
import { ConversationHistoryProvider } from "@/lib/contexts/ConversationHistoryContext";
import { VoiceModeProvider } from "@/components/voice";

// Mock the service context hooks while preserving ServiceProvider
jest.mock("@/lib/services/ServiceContext", () => {
  const actual = jest.requireActual("@/lib/services/ServiceContext");
  return {
    ...actual,
    useExecutionService: jest.fn(),
    useSessionService: jest.fn(),
  };
});

// Mock VoiceApiClient to prevent real API calls
jest.mock("@/lib/services/VoiceApiClient", () => {
  const mockClient = {
    transcribe: jest.fn().mockResolvedValue({
      success: true,
      result: { text: 'mock transcription', words: [], confidence: 0.9 },
    }),
    synthesize: jest.fn().mockResolvedValue(new Blob(['audio'], { type: 'audio/mpeg' })),
    synthesizeStream: jest.fn().mockImplementation(async function* () {
      yield new Uint8Array([1, 2, 3]);
    }),
    listVoices: jest.fn().mockResolvedValue([]),
    getVoice: jest.fn().mockResolvedValue(null),
    getConfig: jest.fn().mockResolvedValue({
      enabled: true,
      tts: { voice_id: 'default', model_id: 'eleven_multilingual_v2' },
      stt: { model_id: 'scribe_v1' },
    }),
    updateConfig: jest.fn().mockResolvedValue(undefined),
    healthCheck: jest.fn().mockResolvedValue({
      healthy: true,
      elevenlabs_connected: true,
      status: 'healthy',
    }),
  };
  return {
    VoiceApiClient: jest.fn().mockImplementation(() => mockClient),
    getVoiceApiClient: jest.fn(() => mockClient),
    resetVoiceApiClient: jest.fn(),
  };
});

import { useExecutionService, useSessionService } from "@/lib/services/ServiceContext";

/**
 * Test helper to render UnifiedChatInterface with all required providers
 */
function renderWithProviders(ui: React.ReactElement) {
  const result = render(
    <ServiceProvider>
      <SmartRouterProvider>
        <VoiceProvider loadVoicesOnMount={false}>
          <ConversationHistoryProvider>
            <VoiceModeProvider>{ui}</VoiceModeProvider>
          </ConversationHistoryProvider>
        </VoiceProvider>
      </SmartRouterProvider>
    </ServiceProvider>
  );
  
  // Override rerender to also wrap with provider
  const originalRerender = result.rerender;
  result.rerender = (ui: React.ReactNode) => {
    return originalRerender(
      <ServiceProvider>
        <SmartRouterProvider>
          <VoiceProvider loadVoicesOnMount={false}>
            <ConversationHistoryProvider>
              <VoiceModeProvider>{ui}</VoiceModeProvider>
            </ConversationHistoryProvider>
          </VoiceProvider>
        </SmartRouterProvider>
      </ServiceProvider>
    );
  };
  
  return result;
}

describe("UnifiedChatInterface", () => {
  let mockExecutionService: jest.Mocked<IAgentExecutionService>;
  let mockSessionService: jest.Mocked<ISessionService>;

  beforeEach(() => {
    // Mock scrollIntoView
    Element.prototype.scrollIntoView = jest.fn();
    // Create mock services
    mockExecutionService = {
      execute: jest.fn(),
      executeMock: jest.fn(),
      executeReal: jest.fn(),
      executeStream: jest.fn(),
    } as any;

    mockSessionService = {
      getSessionId: jest.fn(),
      clearSession: jest.fn(),
      clearAllSessions: jest.fn(),
    };

    // Mock the hooks to return our mocks
    (useExecutionService as jest.Mock).mockReturnValue(mockExecutionService);
    (useSessionService as jest.Mock).mockReturnValue(mockSessionService);

    // Default session ID
    mockSessionService.getSessionId.mockReturnValue("session-123");
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render chat interface", () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      expect(screen.getByText("Chat Interface")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)")).toBeInTheDocument();
    });

    it("should display current mode", () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="real" useSession={true} />
      );

      expect(screen.getByText(/Mode:/)).toBeInTheDocument();
      expect(screen.getAllByText(/real/i).length).toBeGreaterThan(0);
    });

    it("should show session status when enabled", () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      expect(screen.getByText(/Session: Active/i)).toBeInTheDocument();
    });

    it("should not show session status when disabled", () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={false} />
      );

      expect(screen.queryByText(/Session: Active/i)).not.toBeInTheDocument();
    });

    it("should show empty state initially", () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      expect(screen.getByText("Start a conversation")).toBeInTheDocument();
    });

    it("should show mode-specific empty state message", () => {
      const { rerender } = renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      expect(
        screen.getByText(/Using mock mode - instant responses, no API costs/i)
      ).toBeInTheDocument();

      rerender(
        <UnifiedChatInterface agentId="test-agent" mode="real" useSession={true} />
      );

      expect(
        screen.getByText(/Using real mode - actual API calls, complete responses/i)
      ).toBeInTheDocument();

      rerender(
        <UnifiedChatInterface agentId="test-agent" mode="stream" useSession={true} />
      );

      expect(
        screen.getByText(/Using stream mode - real-time token streaming/i)
      ).toBeInTheDocument();
    });
  });

  describe("Mock Execution Mode", () => {
    it("should execute mock request", async () => {
      const mockResponse: SimulationResponse = {
        response: "Mock response",
        trace: [],
        metadata: { mode: "mock" },
      };

      mockExecutionService.executeMock.mockResolvedValueOnce(mockResponse);

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      const submitButton = screen.getByRole("button", { name: /send/i });

      await userEvent.type(input, "Hello");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockExecutionService.executeMock).toHaveBeenCalledWith(
          "test-agent",
          expect.objectContaining({
            input: "Hello",
            session_id: "session-123",
          })
        );
      });

      await waitFor(() => {
        expect(screen.getByText("Hello")).toBeInTheDocument();
        expect(screen.getByText("Mock response")).toBeInTheDocument();
      });
    });

    it("should clear input after submission", async () => {
      mockExecutionService.executeMock.mockResolvedValueOnce({
        response: "Response",
        trace: [],
        metadata: {},
      });

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText(
        "Type your message... (Shift + Enter for new line)"
      ) as HTMLTextAreaElement;

      await userEvent.type(input, "Test message");
      expect(input.value).toBe("Test message");

      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(input.value).toBe("");
      });
    });

    it("should not submit empty messages", async () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const submitButton = screen.getByRole("button", { name: /send/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockExecutionService.executeMock).not.toHaveBeenCalled();
      });
    });

    it("should not submit whitespace-only messages", async () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "   ");

      const submitButton = screen.getByRole("button", { name: /send/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockExecutionService.executeMock).not.toHaveBeenCalled();
      });
    });
  });

  describe("Real Execution Mode", () => {
    it("should execute real request", async () => {
      const mockResponse: SimulationResponse = {
        response: "Real response from OpenAI",
        trace: [],
        metadata: {
          mode: "real",
          usage: {
            total_tokens: 100,
          },
        },
      };

      mockExecutionService.executeReal.mockResolvedValueOnce(mockResponse);

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="real" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Real execution test");

      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(mockExecutionService.executeReal).toHaveBeenCalledWith(
          "test-agent",
          expect.objectContaining({
            input: "Real execution test",
            session_id: "session-123",
          })
        );
      });

      await waitFor(() => {
        expect(screen.getByText("Real response from OpenAI")).toBeInTheDocument();
      });
    });

    it("should display token usage", async () => {
      const mockResponse: SimulationResponse = {
        response: "Response",
        trace: [],
        metadata: {
          mode: "real",
          usage: {
            total_tokens: 150,
          },
        },
      };

      mockExecutionService.executeReal.mockResolvedValueOnce(mockResponse);

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="real" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText(/Tokens: 150/i)).toBeInTheDocument();
      });
    });

    it("should display mode badge", async () => {
      const mockResponse: SimulationResponse = {
        response: "Response",
        trace: [],
        metadata: {
          mode: "real",
        },
      };

      mockExecutionService.executeReal.mockResolvedValueOnce(mockResponse);

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="real" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText("real")).toBeInTheDocument();
      });
    });
  });

  describe("Stream Execution Mode", () => {
    it("should execute streaming request", async () => {
      const mockChunks: StreamChunk[] = [
        { type: "metadata", metadata: { conversation_id: "conv-123" } },
        { type: "token", content: "Hello" },
        { type: "token", content: " world" },
        { type: "done", metadata: { usage: { total_tokens: 50 } } },
      ];

      async function* mockStreamGenerator() {
        for (const chunk of mockChunks) {
          yield chunk;
        }
      }

      mockExecutionService.executeStream.mockReturnValueOnce(
        mockStreamGenerator()
      );

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="stream" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Stream test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(mockExecutionService.executeStream).toHaveBeenCalledWith(
          "test-agent",
          expect.objectContaining({
            input: "Stream test",
            session_id: "session-123",
          })
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/Hello world/)).toBeInTheDocument();
      });
    });

    it("should display tokens incrementally", async () => {
      const mockChunks: StreamChunk[] = [
        { type: "token", content: "The" },
        { type: "token", content: " quick" },
        { type: "token", content: " brown" },
        { type: "token", content: " fox" },
        { type: "done", metadata: {} },
      ];

      async function* mockStreamGenerator() {
        for (const chunk of mockChunks) {
          yield chunk;
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }

      mockExecutionService.executeStream.mockReturnValueOnce(
        mockStreamGenerator()
      );

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="stream" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(
        () => {
          expect(screen.getByText(/The quick brown fox/)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it("should handle stream errors", async () => {
      async function* mockStreamGenerator() {
        yield { type: "token", content: "Start" } as StreamChunk;
        yield { type: "error", content: "Stream connection lost" } as StreamChunk;
      }

      mockExecutionService.executeStream.mockReturnValueOnce(
        mockStreamGenerator()
      );

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="stream" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText(/Stream connection lost/i)).toBeInTheDocument();
      });
    });
  });

  describe("Session Management", () => {
    it("should use session ID when enabled", async () => {
      mockExecutionService.executeMock.mockResolvedValueOnce({
        response: "Response",
        trace: [],
        metadata: {},
      });

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(mockSessionService.getSessionId).toHaveBeenCalledWith("test-agent");
        expect(mockExecutionService.executeMock).toHaveBeenCalledWith(
          "test-agent",
          expect.objectContaining({ session_id: "session-123" })
        );
      });
    });

    it("should not use session ID when disabled", async () => {
      mockExecutionService.executeMock.mockResolvedValueOnce({
        response: "Response",
        trace: [],
        metadata: {},
      });

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={false} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(mockSessionService.getSessionId).not.toHaveBeenCalled();
        expect(mockExecutionService.executeMock).toHaveBeenCalledWith(
          "test-agent",
          expect.objectContaining({ input: "Test" })
        );
      });

      // Verify session_id is undefined
      const callArgs = mockExecutionService.executeMock.mock.calls[0][1];
      expect(callArgs.session_id).toBeUndefined();
    });

    it("should clear session when clear chat button is clicked", async () => {
      mockExecutionService.executeMock.mockResolvedValueOnce({
        response: "Response",
        trace: [],
        metadata: {},
      });

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      // Send a message to show clear button
      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText("Test")).toBeInTheDocument();
      });

      // Click clear chat button
      const clearButton = screen.getByRole("button", { name: /clear chat/i });
      fireEvent.click(clearButton);

      expect(mockSessionService.clearSession).toHaveBeenCalledWith("test-agent");
      expect(screen.queryByText("Test")).not.toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display error message on mock execution failure", async () => {
      mockExecutionService.executeMock.mockRejectedValueOnce(
        new Error("Mock execution failed")
      );

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText(/Mock execution failed/i)).toBeInTheDocument();
        expect(screen.getByText("Error")).toBeInTheDocument();
      });
    });

    it("should display error message on real execution failure", async () => {
      mockExecutionService.executeReal.mockRejectedValueOnce(
        new Error("API rate limit exceeded")
      );

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="real" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText(/API rate limit exceeded/i)).toBeInTheDocument();
      });
    });

    it("should handle generic errors", async () => {
      mockExecutionService.executeMock.mockRejectedValueOnce("Unknown error");

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText(/An error occurred/i)).toBeInTheDocument();
      });
    });
  });

  describe("UI Interactions", () => {
    it("should disable input during loading", async () => {
      let resolvePromise: (value: SimulationResponse) => void;
      const promise = new Promise<SimulationResponse>((resolve) => {
        resolvePromise = resolve;
      });

      mockExecutionService.executeMock.mockReturnValueOnce(promise);

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText(
        "Type your message... (Shift + Enter for new line)"
      ) as HTMLTextAreaElement;
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(input.disabled).toBe(true);
      });

      resolvePromise!({ response: "Response", trace: [], metadata: {} });

      await waitFor(() => {
        expect(input.disabled).toBe(false);
      });
    });

    it("should show loading spinner", async () => {
      let resolvePromise: (value: SimulationResponse) => void;
      const promise = new Promise<SimulationResponse>((resolve) => {
        resolvePromise = resolve;
      });

      mockExecutionService.executeMock.mockReturnValueOnce(promise);

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        // Loading spinner should be visible - button should be disabled
        const submitButton = screen.getByRole("button", { name: /send/i });
        expect(submitButton).toBeDisabled();
      });

      resolvePromise!({ response: "Response", trace: [], metadata: {} });
    });

    it("should submit on Enter key", async () => {
      mockExecutionService.executeMock.mockResolvedValueOnce({
        response: "Response",
        trace: [],
        metadata: {},
      });

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.keyDown(input, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(mockExecutionService.executeMock).toHaveBeenCalled();
      });
    });

    it("should not submit on Shift+Enter", async () => {
      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test");
      fireEvent.keyDown(input, { key: "Enter", shiftKey: true });

      await waitFor(() => {
        expect(mockExecutionService.executeMock).not.toHaveBeenCalled();
      });
    });
  });

  describe("Message Display", () => {
    it("should display messages with timestamps", async () => {
      mockExecutionService.executeMock.mockResolvedValueOnce({
        response: "Response",
        trace: [],
        metadata: {},
      });

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");
      await userEvent.type(input, "Test message");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText("Test message")).toBeInTheDocument();
        expect(screen.getByText("Response")).toBeInTheDocument();
      });
    });

    it("should display multiple messages", async () => {
      mockExecutionService.executeMock
        .mockResolvedValueOnce({ response: "Response 1", trace: [], metadata: {} })
        .mockResolvedValueOnce({ response: "Response 2", trace: [], metadata: {} })
        .mockResolvedValueOnce({ response: "Response 3", trace: [], metadata: {} });

      renderWithProviders(
        <UnifiedChatInterface agentId="test-agent" mode="mock" useSession={true} />
      );

      const input = screen.getByPlaceholderText("Type your message... (Shift + Enter for new line)");

      // Send first message
      await userEvent.type(input, "Message 1");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText("Message 1")).toBeInTheDocument();
        expect(screen.getByText("Response 1")).toBeInTheDocument();
      });

      // Send second message
      await userEvent.type(input, "Message 2");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText("Message 2")).toBeInTheDocument();
        expect(screen.getByText("Response 2")).toBeInTheDocument();
      });

      // Send third message
      await userEvent.type(input, "Message 3");
      fireEvent.submit(input.closest("form")!);

      await waitFor(() => {
        expect(screen.getByText("Message 3")).toBeInTheDocument();
        expect(screen.getByText("Response 3")).toBeInTheDocument();
      });

      // All messages should be visible
      expect(screen.getByText("Message 1")).toBeInTheDocument();
      expect(screen.getByText("Response 1")).toBeInTheDocument();
      expect(screen.getByText("Message 2")).toBeInTheDocument();
      expect(screen.getByText("Response 2")).toBeInTheDocument();
      expect(screen.getByText("Message 3")).toBeInTheDocument();
      expect(screen.getByText("Response 3")).toBeInTheDocument();
    });
  });
});
