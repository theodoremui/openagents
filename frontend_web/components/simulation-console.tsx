"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { getApiClient, ApiClientError } from "@/lib/api-client";
import type { SimulationResponse, SimulationStep } from "@/lib/types";
import { Send, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/utils";

interface Message {
  role: "user" | "agent";
  content: string;
  timestamp: Date;
  trace?: SimulationStep[];
}

interface SimulationConsoleProps {
  agentId: string;
}

/**
 * Simulation Console Component
 *
 * Provides Q&A interface for interacting with agents.
 * Displays conversation history and agent responses with traces.
 */
export function SimulationConsole({ agentId }: SimulationConsoleProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!input.trim() || !agentId || loading) return;

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const client = getApiClient();
      const response: SimulationResponse = await client.simulateAgent(agentId, {
        input: userMessage.content,
      });

      const agentMessage: Message = {
        role: "agent",
        content: response.response,
        timestamp: new Date(),
        trace: response.trace,
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err) {
      const errorMessage: Message = {
        role: "agent",
        content:
          err instanceof ApiClientError
            ? `Error: ${err.message}`
            : "An error occurred while processing your request.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>Simulation Console</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-4">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto space-y-4 min-h-[400px] max-h-[600px] border rounded-md p-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p>Start a conversation with the agent...</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">
                    {message.content}
                  </p>
                  <p className="text-xs mt-1 opacity-70">
                    {formatDate(message.timestamp)}
                  </p>

                  {/* Show trace for agent messages */}
                  {message.trace && message.trace.length > 0 && (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer opacity-70 hover:opacity-100">
                        Execution Trace ({message.trace.length} steps)
                      </summary>
                      <div className="mt-2 space-y-1">
                        {message.trace.map((step, idx) => (
                          <div key={idx} className="pl-2 border-l-2 border-border">
                            <p className="font-semibold">{step.agent_name}</p>
                            <p className="opacity-70">{step.action}</p>
                            {step.output && (
                              <p className="opacity-60 mt-1">{step.output}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="resize-none"
            rows={3}
            disabled={loading || !agentId}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <Button type="submit" disabled={loading || !input.trim() || !agentId}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
