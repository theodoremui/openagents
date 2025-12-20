/**
 * Unified Chat Interface Component
 *
 * Single component that handles all three execution modes:
 * - Mock: Fast testing
 * - Real: Complete responses
 * - Stream: Real-time tokens
 *
 * Uses AgentExecutionService via dependency injection.
 * Follows SOLID principles with clear separation of concerns.
 */

"use client";

import React, { useState, useRef, useEffect, useMemo, memo, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useExecutionService, useSessionService } from "@/lib/services/ServiceContext";
import type { ExecutionMode, StreamChunk, SmartRouterMetadata } from "@/lib/types";
import { Send, Loader2, AlertCircle, ArrowDown, Brain, ChevronDown, ChevronUp, Volume2 } from "lucide-react";
import { formatDate } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import { InteractiveMap } from "./interactive-map";
import { useSmartRouterPanel } from "@/lib/contexts/SmartRouterContext";
import { useVoiceMode, VoiceConversationMessages, type VoiceConversationMessage } from "@/components/voice";
import { VoiceInputPanel } from "./voice/VoiceInputPanel";
import { useVoiceSettings, useVoiceClient } from "@/lib/contexts/VoiceContext";
import { RoomAudioRenderer, useRemoteParticipants, useRoomContext } from "@livekit/components-react";
import type { SimulationStep } from "@/lib/types";
import { useConversationHistory, type ConversationMessage } from "@/lib/contexts/ConversationHistoryContext";

interface Message {
  role: "user" | "agent" | "error";
  content: string;
  timestamp: Date;
  metadata?: {
    mode?: string;
    usage?: {
      total_tokens?: number;
    };
    final_decision?: string;
    original_answer?: string;
    [key: string]: unknown;
  };
}

interface UnifiedChatInterfaceProps {
  agentId: string;
  mode: ExecutionMode;
  useSession?: boolean;
}

// Custom sanitize schema to allow images from Google Maps
const customSanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    img: [
      ...(defaultSchema.attributes?.img || []),
      // Allow src from any https source (including googleapis.com)
      ['src', /^https?:\/\//],
      'alt',
      'title',
      'width',
      'height',
      'loading',
      'className',
      'class'
    ],
  },
  protocols: {
    ...defaultSchema.protocols,
    src: ['http', 'https', 'data'],
  },
};

function extractHumanTextFromJson(value: unknown, depth: number = 0): string | null {
  if (depth > 6) return null;

  if (typeof value === "string") {
    const s = value.trim();
    return s.length > 0 ? s : null;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const found = extractHumanTextFromJson(item, depth + 1);
      if (found) return found;
    }
    return null;
  }

  if (!value || typeof value !== "object") return null;

  const obj = value as Record<string, unknown>;
  const preferredKeys = [
    "answer",
    "response",
    "content",
    "final_response",
    "finalResponse",
    "final_answer",
    "finalAnswer",
    "text",
    "message",
    "markdown",
    "output",
    "result",
  ];

  for (const k of preferredKeys) {
    if (k in obj) {
      const found = extractHumanTextFromJson(obj[k], depth + 1);
      if (found) return found;
    }
  }

  // Common OpenAI-ish envelope: { choices: [{ message: { content: "..." } }] }
  const choices = obj["choices"];
  if (Array.isArray(choices) && choices.length > 0) {
    const found = extractHumanTextFromJson(choices[0], depth + 1);
    if (found) return found;
  }

  // A slightly safer fallback: only recurse into common wrapper keys, not *every* value.
  // This avoids accidentally pulling random strings like "agent_id" / "status" and
  // treating them as the primary user-facing answer.
  for (const wrapperKey of ["data", "payload", "result", "output", "message"]) {
    if (wrapperKey in obj) {
      const found = extractHumanTextFromJson(obj[wrapperKey], depth + 1);
      if (found) return found;
    }
  }

  return null;
}

/**
 * VoiceAudioOutput
 *
 * When Voice Mode is active, the agent's TTS is delivered as a remote LiveKit audio track.
 * This component ensures:
 * - remote audio is actually rendered (RoomAudioRenderer)
 * - autoplay is unlocked (room.startAudio, gated by browser policy)
 * - basic, visible diagnostics are shown if audio can't play
 *
 * IMPORTANT: This component must only be rendered inside <LiveKitRoom>.
 */
const VoiceAudioOutput = ({
  ttsEnabled,
  volume,
  playbackSpeed,
}: {
  ttsEnabled: boolean;
  volume: number;
  playbackSpeed: number;
}) => {
  const room = useRoomContext();
  const remoteParticipants = useRemoteParticipants();
  const [audioStartError, setAudioStartError] = useState<string | null>(null);
  const [noRemoteAudio, setNoRemoteAudio] = useState(false);

  // Apply speaker settings to any <audio> elements created by LiveKit.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const v = Math.max(0, Math.min(1, volume));
    const shouldPlay = !!ttsEnabled && v > 0;

    const applyToAll = () => {
      const audios = Array.from(document.querySelectorAll("audio"));
      for (const el of audios) {
        el.muted = !shouldPlay;
        el.volume = v;
        el.playbackRate = playbackSpeed || 1;
        el.autoplay = true;
        el.setAttribute("playsinline", "true");
      }
    };

    applyToAll();
    const observer = new MutationObserver(() => applyToAll());
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [ttsEnabled, volume, playbackSpeed]);

  // Attempt to unlock autoplay (Chrome/Safari).
  useEffect(() => {
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
        setAudioStartError(msg);
      }
    })();
  }, [room]);

  // Detect whether any remote audio track is actually present/subscribed.
  useEffect(() => {
    let hasRemoteAudioTrack = false;
    for (const p of remoteParticipants) {
      p.audioTrackPublications.forEach((pub) => {
        if (pub.isSubscribed && pub.track && !pub.isMuted && pub.isEnabled) {
          hasRemoteAudioTrack = true;
        }
      });
      if (hasRemoteAudioTrack) break;
    }
    setNoRemoteAudio(remoteParticipants.length > 0 && !hasRemoteAudioTrack);
  }, [remoteParticipants]);

  return (
    <div className="mt-1 space-y-1">
      <RoomAudioRenderer />

      {audioStartError ? (
        <div className="text-xs text-amber-700">
          Audio blocked —{" "}
          <button
            className="underline"
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
            click to enable
          </button>
        </div>
      ) : noRemoteAudio ? (
        <div className="text-xs text-slate-600">
          No agent audio track detected (likely LiveKit worker connectivity/auth).
        </div>
      ) : (
        <div className="text-xs text-muted-foreground">
          Audio output: {ttsEnabled && volume > 0 ? "on" : "muted"} • Remote participants:{" "}
          {remoteParticipants.length}
        </div>
      )}
    </div>
  );
};

/**
 * FallbackOriginalAnswer Component
 *
 * Collapsible section that shows the original low-quality answer
 * when SmartRouter uses fallback.
 */
const FallbackOriginalAnswer = ({ originalAnswer }: { originalAnswer: string }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mt-3 border border-amber-500/30 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 bg-amber-500/10 hover:bg-amber-500/20 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
          <AlertCircle className="h-4 w-4" />
          <span>View original response (low quality)</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-amber-700 dark:text-amber-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-amber-700 dark:text-amber-400" />
        )}
      </button>

      {isExpanded && (
        <div className="p-4 bg-amber-500/5 border-t border-amber-500/20 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="text-xs text-amber-800 dark:text-amber-300 mb-2 font-semibold">
            ⚠️ This response was judged as low quality and replaced with a fallback message.
          </div>
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-2 text-muted-foreground">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[
                rehypeRaw,
                [rehypeSanitize, customSanitizeSchema],
              ]}
            >
              {originalAnswer}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Enhanced JSON block detection with multiple patterns and error handling
 */
const detectInteractiveMapBlocks = (content: string): Array<{ config: any; raw: string; source: string }> => {
  const results: Array<{ config: any; raw: string; source: string }> = [];

  const parseJson = (s: string) => {
    try {
      return JSON.parse(s);
    } catch {
      return null;
    }
  };

  const validateMapConfig = (config: any): boolean => {
    if (!config || typeof config !== 'object') return false;

    // Must have a valid map_type
    if (!['route', 'location', 'places'].includes(config.map_type)) return false;

    // Route maps need origin and destination
    if (config.map_type === 'route') {
      return typeof config.origin === 'string' && typeof config.destination === 'string';
    }

    // Location and places maps should have center or markers
    if (config.map_type === 'location' || config.map_type === 'places') {
      const hasValidCenter = config.center &&
        typeof config.center.lat === 'number' &&
        typeof config.center.lng === 'number';
      const hasValidMarkers = Array.isArray(config.markers) && config.markers.length > 0;

      // Check if markers have coordinates OR addresses (for geocoding fallback)
      const hasValidMarkerData = hasValidMarkers && config.markers.some((marker: any) => {
        const hasCoords = typeof marker.lat === 'number' && typeof marker.lng === 'number';
        const hasAddress = typeof marker.address === 'string' && marker.address.trim().length > 0;
        return hasCoords || hasAddress;
      });

      return hasValidCenter || hasValidMarkerData;
    }

    return true;
  };

  const convertLegacyFormat = (data: any): any | null => {
    if (!data || typeof data !== 'object') return null;

    // Handle 'pins' format
    if (data.pins && Array.isArray(data.pins)) {
      return {
        map_type: 'places' as const,
        markers: data.pins.map((pin: any) => ({
          lat: pin.coordinates?.lat || pin.lat,
          lng: pin.coordinates?.lng || pin.lng,
          address: pin.address,
          title: pin.title || pin.name,
          type: pin.type,
        })),
        center: data.center || (data.pins.length > 0 ? {
          lat: data.pins.reduce((sum: number, p: any) => sum + (p.coordinates?.lat || p.lat || 0), 0) / data.pins.length,
          lng: data.pins.reduce((sum: number, p: any) => sum + (p.coordinates?.lng || p.lng || 0), 0) / data.pins.length,
        } : undefined),
        zoom: data.zoom || 13,
      };
    }

    // Handle direct config format
    if (data.map_type || data.markers || data.origin) {
      return data;
    }

    return null;
  };

  // Pattern 1: Standard fenced JSON blocks
  const fencedJsonPattern = /```json\s*\n([\s\S]*?)\n```/gi;
  let match;
  while ((match = fencedJsonPattern.exec(content)) !== null) {
    const jsonContent = match[1].trim();
    const obj = parseJson(jsonContent);

    if (obj && obj.type === 'interactive_map') {
      let config = null;

      if (obj.config && validateMapConfig(obj.config)) {
        config = obj.config;
      } else if (obj.data) {
        config = convertLegacyFormat(obj.data);
      }

      if (config && validateMapConfig(config)) {
        results.push({
          config,
          raw: JSON.stringify(obj, null, 2),
          source: 'fenced-json'
        });
      }
    }
  }

  // Pattern 2: JSON blocks without language specification
  const genericCodePattern = /```\s*\n([\s\S]*?)\n```/gi;
  fencedJsonPattern.lastIndex = 0; // Reset regex
  while ((match = genericCodePattern.exec(content)) !== null) {
    const codeContent = match[1].trim();
    const obj = parseJson(codeContent);

    if (obj && obj.type === 'interactive_map') {
      let config = null;

      if (obj.config && validateMapConfig(obj.config)) {
        config = obj.config;
      } else if (obj.data) {
        config = convertLegacyFormat(obj.data);
      }

      if (config && validateMapConfig(config)) {
        // Check if we already found this in fenced JSON
        const alreadyFound = results.some(r =>
          JSON.stringify(r.config) === JSON.stringify(config)
        );

        if (!alreadyFound) {
          results.push({
            config,
            raw: JSON.stringify(obj, null, 2),
            source: 'generic-code'
          });
        }
      }
    }
  }

  // Pattern 3: Inline JSON (no code fences)
  if (results.length === 0) {
    const obj = parseJson(content);
    if (obj && obj.type === 'interactive_map') {
      let config = null;

      if (obj.config && validateMapConfig(obj.config)) {
        config = obj.config;
      } else if (obj.data) {
        config = convertLegacyFormat(obj.data);
      }

      if (config && validateMapConfig(config)) {
        results.push({
          config,
          raw: JSON.stringify(obj, null, 2),
          source: 'inline-json'
        });
      }
    }
  }

  // Pattern 4: Embedded JSON within text (extract JSON-like structures)
  if (results.length === 0) {
    const embeddedJsonPattern = /\{[^{}]*"type"\s*:\s*"interactive_map"[^{}]*\}/gi;
    while ((match = embeddedJsonPattern.exec(content)) !== null) {
      const obj = parseJson(match[0]);
      if (obj && obj.type === 'interactive_map') {
        let config = null;

        if (obj.config && validateMapConfig(obj.config)) {
          config = obj.config;
        } else if (obj.data) {
          config = convertLegacyFormat(obj.data);
        }

        if (config && validateMapConfig(config)) {
          results.push({
            config,
            raw: JSON.stringify(obj, null, 2),
            source: 'embedded-json'
          });
        }
      }
    }
  }

  return results;
};

/**
 * Error boundary component for InteractiveMap rendering
 */
class MapErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[InteractiveMap] Rendering error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="w-full p-4 border border-destructive/30 rounded-lg bg-destructive/5">
          <div className="flex items-center gap-2 text-destructive mb-2">
            <AlertCircle className="h-4 w-4" />
            <span className="font-semibold text-sm">Map Rendering Error</span>
          </div>
          <p className="text-sm text-muted-foreground mb-2">
            Failed to render interactive map. This may be due to:
          </p>
          <ul className="text-xs text-muted-foreground mb-2 list-disc list-inside">
            <li>Missing or invalid coordinates</li>
            <li>Malformed map configuration</li>
            <li>Google Maps API issues</li>
          </ul>
          <p className="text-xs text-muted-foreground mb-2">
            <strong>Troubleshooting:</strong> Check that markers have valid lat/lng coordinates or addresses for geocoding.
          </p>
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              View error details
            </summary>
            <pre className="mt-2 p-2 bg-muted/50 rounded text-xs overflow-x-auto">
              {this.state.error?.message || 'Unknown error'}
            </pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}
/**
 * MessageItem Component
 *
 * Renders a single message with memoization to prevent unnecessary rerenders.
 * This is critical for performance - prevents interactive maps from rerendering
 * when the user types in the input box.
 *
 * Follows SRP: Single responsibility of rendering one message.
 */
const MessageItem = memo(({ message }: { message: Message }) => {
  const structured = useMemo(() => {
    const raw = (message.content || "").trim();
    if (!raw) return null;

    // Use enhanced detection for interactive maps
    const mapBlocks = detectInteractiveMapBlocks(raw);
    if (mapBlocks.length > 0) {
      // Use the first valid map block found
      const mapBlock = mapBlocks[0];
      return {
        kind: "interactive_map" as const,
        config: mapBlock.config,
        raw: mapBlock.raw,
        source: mapBlock.source,
      };
    }

    const parseJson = (s: string) => {
      try {
        return JSON.parse(s);
      } catch {
        return null;
      }
    };

    // Fallback: try to parse as generic JSON for other structured content
    const wholeMessageMatch = raw.match(/^```json\s*\n([\s\S]*?)\n```\s*$/i);
    if (wholeMessageMatch) {
      const fencedPayload = wholeMessageMatch[1].trim();
      const obj = parseJson(fencedPayload);
      if (obj && typeof obj === "object") {
        // Generic structured response: try to extract a human-readable field
        const text = extractHumanTextFromJson(obj);
        if (typeof text === "string" && text.trim().length > 0) {
          return {
            kind: "extracted_text" as const,
            text,
            raw: JSON.stringify(obj, null, 2),
          };
        }

        // Unknown JSON object
        return { kind: "unknown_json" as const, raw: JSON.stringify(obj, null, 2) };
      }
    }

    // No structured data found
    return null;
  }, [message.content]);

  // Memoize ReactMarkdown components to prevent recreation on every render
  const markdownComponents = useMemo(
    () => ({
      // Custom image rendering with error handling
      img: ({ node, ...props }: any) => {
        const [imageError, setImageError] = useState(false);

        if (imageError || !props.src) {
          return null; // Don't render broken images
        }

        return (
          <img
            {...props}
            className="rounded-lg max-w-full h-auto my-2 shadow-md"
            loading="lazy"
            alt={props.alt || "Image"}
            onError={() => setImageError(true)}
          />
        );
      },

      // Custom code block rendering - detect interactive maps
      code: ({ node, inline, className, children, ...props }: any) => {
        if (!inline) {
          const match = /language-(\w+)/.exec(className || '');
          const code = String(children).replace(/\n$/, '').trim();

          // Detect interactive map JSON using enhanced detection
          if (match && match[1] === 'json') {
            const mapBlocks = detectInteractiveMapBlocks(code);
            if (mapBlocks.length > 0) {
              const mapBlock = mapBlocks[0];
              console.log('[InteractiveMap] Detected interactive_map JSON block via enhanced detection:', {
                source: mapBlock.source,
                hasConfig: !!mapBlock.config
              });

              return (
                <MapErrorBoundary
                  fallback={
                    <div className="w-full p-4 border border-destructive/30 rounded-lg bg-destructive/5 my-2">
                      <div className="flex items-center gap-2 text-destructive mb-2">
                        <AlertCircle className="h-4 w-4" />
                        <span className="font-semibold text-sm">Map Rendering Failed</span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        Unable to render interactive map from JSON block. Showing code instead.
                      </p>
                      <code className="block p-3 rounded-lg bg-muted/60 text-foreground font-mono text-xs overflow-x-auto whitespace-pre">
                        {code}
                      </code>
                    </div>
                  }
                >
                  <InteractiveMap config={mapBlock.config} />
                </MapErrorBoundary>
              );
            }
          }

          // Regular code block
          return (
            <code
              className="block p-3 rounded-lg bg-muted/60 text-foreground font-mono text-xs overflow-x-auto whitespace-pre"
              {...props}
            >
              {children}
            </code>
          );
        }

        // Inline code
        return (
          <code
            className="px-1.5 py-0.5 rounded bg-muted/60 text-foreground font-mono text-xs"
            {...props}
          >
            {children}
          </code>
        );
      },

      // Custom link rendering
      a: ({ node, ...props }: any) => (
        <a
          {...props}
          className="text-primary hover:underline font-medium"
          target="_blank"
          rel="noopener noreferrer"
        />
      ),

      // Custom heading rendering
      h1: ({ node, ...props }: any) => (
        <h1 {...props} className="text-xl font-bold mt-4 mb-2" />
      ),
      h2: ({ node, ...props }: any) => (
        <h2 {...props} className="text-lg font-semibold mt-3 mb-2" />
      ),
      h3: ({ node, ...props }: any) => (
        <h3 {...props} className="text-base font-semibold mt-2 mb-1" />
      ),

      // Custom list rendering
      ul: ({ node, ...props }: any) => (
        <ul {...props} className="list-disc list-inside my-2" />
      ),
      ol: ({ node, ...props }: any) => (
        <ol {...props} className="list-decimal list-inside my-2" />
      ),
      li: ({ node, children, ...props }: any) => {
        // Remove paragraph tags from list items to prevent extra spacing
        // React-markdown wraps list item content in <p> tags which causes gaps
        // We need to unwrap those paragraphs
        return (
          <li {...props} className="my-0 leading-relaxed">
            {children}
          </li>
        );
      },
      p: ({ node, children, ...props }: any) => {
        // Check if parent is a list item by looking at the node structure
        // If the parent is 'listItem', render as inline content without margins
        if (node?.parent?.type === 'listItem') {
          return <>{children}</>;
        }

        return <p {...props}>{children}</p>;
      },

      // Custom table rendering
      table: ({ node, ...props }: any) => (
        <div className="overflow-x-auto my-4">
          <table
            {...props}
            className="min-w-full divide-y divide-border/30"
          />
        </div>
      ),
      th: ({ node, ...props }: any) => (
        <th
          {...props}
          className="px-3 py-2 text-left text-xs font-semibold bg-muted/30"
        />
      ),
      td: ({ node, ...props }: any) => (
        <td
          {...props}
          className="px-3 py-2 text-sm border-t border-border/20"
        />
      ),
    }),
    [] // Empty dependency array - components are stable
  );

  // If the message is a structured payload, render it as rich UI / extracted text
  if (structured?.kind === "interactive_map") {
    return (
      <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
        <div className="max-w-[85%]">
          <MapErrorBoundary
            fallback={
              <div className="w-full p-4 border border-destructive/30 rounded-lg bg-destructive/5">
                <div className="flex items-center gap-2 text-destructive mb-2">
                  <AlertCircle className="h-4 w-4" />
                  <span className="font-semibold text-sm">Map Rendering Failed</span>
                </div>
                <p className="text-sm text-muted-foreground mb-2">
                  Unable to render interactive map. Showing raw configuration instead.
                </p>
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    View raw JSON
                  </summary>
                  <pre className="mt-2 p-2 bg-muted/50 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                    {structured.raw}
                  </pre>
                </details>
              </div>
            }
          >
            <InteractiveMap config={structured.config} />
          </MapErrorBoundary>
          {/* Show detection source for debugging */}
          {process.env.NODE_ENV === 'development' && (structured as any).source && (
            <div className="mt-1 text-xs text-muted-foreground">
              Detected via: {(structured as any).source}
            </div>
          )}
        </div>
      </div>
    );
  }

  const contentToRender =
    structured?.kind === "extracted_text" ? structured.text : message.content;

  return (
    <div
      className={`flex ${message.role === "user" ? "justify-end" : "justify-start"
        }`}
    >
      <div
        className={`message-bubble max-w-[80%] rounded-xl p-4 shadow-md ${message.role === "user"
          ? "bg-gradient-to-br from-primary to-primary/80 text-primary-foreground"
          : message.role === "error"
            ? "bg-gradient-to-br from-destructive/20 to-destructive/10 border border-destructive/30"
            : "bg-gradient-to-br from-muted/90 to-muted/60"
          }`}
      >
        {message.role === "error" && (
          <div className="flex items-center gap-2 mb-2 text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span className="font-semibold text-sm">Error</span>
          </div>
        )}

        <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-ol:my-2 prose-li:my-0 [&_li>p]:my-0 [&_li>p]:inline">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[
              rehypeRaw,
              [rehypeSanitize, customSanitizeSchema],
            ]}
            components={markdownComponents}
          >
            {contentToRender}
          </ReactMarkdown>
        </div>

        {/* If we extracted from JSON, keep raw available but out of the way */}
        {structured && (structured.kind === "extracted_text" || structured.kind === "unknown_json") && (
          <details className="mt-2">
            <summary className="text-xs text-muted-foreground cursor-pointer select-none">
              View raw JSON
            </summary>
            <pre className="mt-2 p-3 rounded-lg bg-muted/60 text-foreground font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
              {structured.raw}
            </pre>
          </details>
        )}

        {/* Collapsible section for original answer when fallback is used */}
        {message.metadata?.final_decision === "fallback" && message.metadata?.original_answer && (
          <FallbackOriginalAnswer originalAnswer={message.metadata.original_answer} />
        )}

        <div className="flex items-center justify-between mt-2 text-xs opacity-70">
          <span>{formatDate(message.timestamp)}</span>
          {message.metadata?.mode && (
            <span className="ml-2 px-2 py-0.5 bg-background/20 rounded">
              {message.metadata.mode}
            </span>
          )}
        </div>

        {/* Show token usage for real/stream modes */}
        {message.metadata?.usage && (
          <div className="mt-2 pt-2 border-t border-border/40 text-xs opacity-70">
            Tokens: {message.metadata.usage.total_tokens || 0}
          </div>
        )}
      </div>
    </div>
  );
});

MessageItem.displayName = 'MessageItem';

/**
 * Unified Chat Interface
 *
 * Handles all execution modes in a single component using the Strategy pattern.
 */
export function UnifiedChatInterface({
  agentId,
  mode,
  useSession = true,
}: UnifiedChatInterfaceProps) {
  // Use shared conversation history
  const { messages: conversationMessages, addMessage, updateMessage, clearMessages, setAgentId: setContextAgentId } = useConversationHistory();

  // Convert ConversationMessage[] to Message[] for display
  // Include both text and voice messages for unified conversation view
  const messages = useMemo(() => {
    return conversationMessages.map(msg => ({
      role: msg.role as "user" | "agent" | "error",
      content: msg.content,
      timestamp: msg.timestamp,
      metadata: {
        source: msg.source,
        ...(msg.metadata || {}),
      },
    }));
  }, [conversationMessages]);

  const { isConnected: isVoiceConnected, orchestrationTrace, exitVoiceMode, agentState } = useVoiceMode();
  const [voiceStreamMessages, setVoiceStreamMessages] = useState<Message[]>([]);
  const [voiceTraceMessages, setVoiceTraceMessages] = useState<Message[]>([]);
  const seenVoiceTraceIdsRef = useRef<Set<string>>(new Set());

  const displayMessages = useMemo(() => {
    if (!isVoiceConnected) return messages;

    // Strategy: In voice mode, orchestrationTrace is the authoritative source.
    // - conversationMessages: May contain messages added by VoiceTranscript component
    // - voiceTraceMessages: Messages from orchestrationTrace (authoritative)
    // - voiceStreamMessages: Real-time LiveKit transcriptions (only for interim feedback)
    //
    // When we have trace messages, we should:
    // 1. Use conversationMessages as base (may already have trace messages from VoiceTranscript)
    // 2. Skip voiceStreamMessages entirely if they duplicate trace messages
    // 3. Only show stream messages if they're truly interim (before trace arrives)

    // Build a set of trace message content for fast lookup
    const traceContentSet = new Set<string>();
    for (const traceMsg of voiceTraceMessages) {
      const normalized = traceMsg.content.trim().toLowerCase().replace(/\s+/g, ' ');
      traceContentSet.add(`${traceMsg.role}:${normalized}`);
    }

    // Start with conversation messages (base)
    const combined: Message[] = [...messages];

    // Add voice trace messages only if they're not already in conversation messages
    // This prevents duplication when VoiceTranscript has already added them
    for (const traceMsg of voiceTraceMessages) {
      const normalized = traceMsg.content.trim().toLowerCase().replace(/\s+/g, ' ');
      const traceKey = `${traceMsg.role}:${normalized}`;

      // Check if this trace message is already in conversation messages
      let alreadyExists = false;
      for (const existing of messages) {
        if (existing.role === traceMsg.role) {
          const existingNormalized = existing.content.trim().toLowerCase().replace(/\s+/g, ' ');
          const timeDiff = Math.abs(traceMsg.timestamp.getTime() - existing.timestamp.getTime());

          // If content matches and timestamps are close, it's already in conversation messages
          if (existingNormalized === normalized && timeDiff < 10000) {
            alreadyExists = true;
            break;
          }
        }
      }

      if (!alreadyExists) {
        combined.push(traceMsg);
      }
    }

    // For voice stream messages: Only add if they don't duplicate trace messages
    // Stream messages are only useful for real-time feedback before trace arrives
    // When trace messages exist, we should be very aggressive about filtering stream messages
    // because LiveKit may transcribe TTS audio, creating duplicates
    for (const streamMsg of voiceStreamMessages) {
      const normalized = streamMsg.content.trim().toLowerCase().replace(/\s+/g, ' ');
      const streamKey = `${streamMsg.role}:${normalized}`;

      // Skip if this stream message duplicates a trace message (exact match)
      if (traceContentSet.has(streamKey)) {
        continue;
      }

      // Aggressive deduplication: If we have any trace messages, check if stream message
      // matches any trace message (even partial matches)
      if (voiceTraceMessages.length > 0) {
        let matchesTrace = false;
        for (const traceMsg of voiceTraceMessages) {
          if (traceMsg.role === streamMsg.role) {
            const traceNormalized = traceMsg.content.trim().toLowerCase().replace(/\s+/g, ' ');
            const timeDiff = Math.abs(streamMsg.timestamp.getTime() - traceMsg.timestamp.getTime());

            // If stream message is a substring of trace message (or vice versa) within 30 seconds,
            // consider it a duplicate - this handles TTS transcription cases
            if (
              timeDiff < 30000 && // 30 second window for TTS transcription
              (normalized === traceNormalized ||
                (normalized.length > 20 && traceNormalized.includes(normalized)) ||
                (traceNormalized.length > 20 && normalized.includes(traceNormalized)))
            ) {
              matchesTrace = true;
              break;
            }
          }
        }
        if (matchesTrace) {
          continue; // Skip this stream message - it's a duplicate of trace
        }
      }

      // Also check if it duplicates any existing message in combined list
      let isDuplicate = false;
      for (const existing of combined) {
        if (existing.role === streamMsg.role) {
          const existingNormalized = existing.content.trim().toLowerCase().replace(/\s+/g, ' ');
          const timeDiff = Math.abs(streamMsg.timestamp.getTime() - existing.timestamp.getTime());

          // Exact match or substring match within time window
          if (
            (normalized === existingNormalized ||
              (normalized.includes(existingNormalized) && existingNormalized.length > 10) ||
              (existingNormalized.includes(normalized) && normalized.length > 10)) &&
            timeDiff < 10000
          ) {
            isDuplicate = true;
            break;
          }
        }
      }

      if (!isDuplicate) {
        combined.push(streamMsg);
      }
    }

    // Final deduplication pass: Remove any remaining exact duplicates
    const deduplicated: Message[] = [];
    const seenKeys = new Set<string>();

    // Sort by timestamp to process in chronological order
    combined.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

    for (const msg of combined) {
      const normalized = msg.content.trim().toLowerCase().replace(/\s+/g, ' ');
      const timestampBucket = Math.floor(msg.timestamp.getTime() / 10000); // 10 second buckets
      const key = `${msg.role}:${normalized}:${timestampBucket}`;

      // Skip exact duplicates
      if (seenKeys.has(key)) {
        continue;
      }

      // Check for near-duplicates with existing messages
      let isDuplicate = false;
      for (const existing of deduplicated) {
        if (existing.role === msg.role) {
          const existingNormalized = existing.content.trim().toLowerCase().replace(/\s+/g, ' ');
          const timeDiff = Math.abs(msg.timestamp.getTime() - existing.timestamp.getTime());

          // Exact match within time window
          if (normalized === existingNormalized && timeDiff < 10000) {
            isDuplicate = true;
            break;
          }

          // Substring match - prefer longer/more complete message
          if (
            (normalized.includes(existingNormalized) || existingNormalized.includes(normalized)) &&
            normalized.length > 10 &&
            existingNormalized.length > 10 &&
            timeDiff < 10000
          ) {
            // Prefer the longer message
            if (msg.content.length > existing.content.length) {
              const index = deduplicated.indexOf(existing);
              deduplicated[index] = msg;
              const existingKey = `${existing.role}:${existingNormalized}:${Math.floor(existing.timestamp.getTime() / 10000)}`;
              seenKeys.delete(existingKey);
              seenKeys.add(key);
            }
            isDuplicate = true;
            break;
          }
        }
      }

      if (!isDuplicate) {
        deduplicated.push(msg);
        seenKeys.add(key);
      }
    }

    return deduplicated;
  }, [messages, voiceTraceMessages, voiceStreamMessages, isVoiceConnected]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const previousMessageCountRef = useRef(0);

  const executionService = useExecutionService();
  const sessionService = useSessionService();
  const { openPanel, openMoETrace, openExecutionTrace, clearMoETrace, togglePanel } = useSmartRouterPanel();
  const [voiceSettings] = useVoiceSettings();
  const voiceClient = useVoiceClient();

  // Set agent ID in context when agentId changes
  useEffect(() => {
    setContextAgentId(agentId);
  }, [agentId, setContextAgentId]);

  // Voice mode: when the backend publishes a MoE trace, show it in the shared right-side panel
  useEffect(() => {
    if (isVoiceConnected && orchestrationTrace) {
      openMoETrace(orchestrationTrace, { open: true });
    }
  }, [isVoiceConnected, orchestrationTrace, openMoETrace]);

  // Voice mode: reliable transcript fallback
  // LiveKit transcription streams are not always available/configured; MoE trace is.
  // We append one user+agent turn per unique request_id.
  // NOTE: We do NOT add these to conversation history here - VoiceTranscript component handles that.
  // We only maintain voiceTraceMessages for display deduplication purposes.
  useEffect(() => {
    if (!isVoiceConnected || !orchestrationTrace?.request_id) return;

    const id = orchestrationTrace.request_id;
    if (seenVoiceTraceIdsRef.current.has(id)) return;
    seenVoiceTraceIdsRef.current.add(id);

    const now = new Date();
    const userText = orchestrationTrace.query?.trim();
    const agentText = orchestrationTrace.final_response?.trim();

    setVoiceTraceMessages((prev) => {
      const next = [...prev];
      if (userText) {
        next.push({ role: 'user', content: userText, timestamp: now, metadata: { mode: 'voice' } });
      }
      if (agentText) {
        next.push({ role: 'agent', content: agentText, timestamp: now, metadata: { mode: 'voice' } });
      }
      return next;
    });
  }, [isVoiceConnected, orchestrationTrace]);


  // When voice mode ends, clear MoE trace panel content (avoids stale traces sticking around)
  useEffect(() => {
    if (!isVoiceConnected) {
      clearMoETrace();
      seenVoiceTraceIdsRef.current = new Set();
      setVoiceTraceMessages([]);
      setVoiceStreamMessages([]);
    }
  }, [isVoiceConnected, clearMoETrace]);


  // Smart auto-scroll: only scroll when agent responds or streaming
  useEffect(() => {
    // Only auto-scroll if:
    // 1. User hasn't manually scrolled up, AND
    // 2. A new agent message was added (not just user message)
    const messageCountChanged = displayMessages.length !== previousMessageCountRef.current;
    const lastMessage = displayMessages[displayMessages.length - 1];
    const isAgentMessage = lastMessage?.role === "agent" || streaming;

    if (messageCountChanged && isAgentMessage && !isUserScrolling) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }

    previousMessageCountRef.current = displayMessages.length;
  }, [displayMessages, streaming, isUserScrolling]);

  // Detect if user is scrolling up manually
  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    const isAtBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 50;

    setShowScrollButton(!isAtBottom);

    // If user scrolls to bottom, resume auto-scrolling
    if (isAtBottom) {
      setIsUserScrolling(false);
    } else if (!streaming && !loading) {
      // Only mark as user scrolling if not actively loading/streaming
      setIsUserScrolling(true);
    }
  };

  // Scroll to bottom function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    setIsUserScrolling(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!input.trim() || !agentId || loading || streaming) return;

    // Add user message to shared history
    addMessage({
      role: "user",
      content: input.trim(),
      source: "text",
    });
    setInput("");

    // Force scroll to bottom immediately after user message is added
    // Use setTimeout to ensure the DOM has updated with the new message
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      setIsUserScrolling(false);
    }, 50);

    setLoading(true);

    try {
      const sessionId = useSession ? sessionService.getSessionId(agentId) : undefined;

      if (mode === "stream") {
        await handleStreamExecution(input.trim(), sessionId);
      } else {
        await handleNonStreamExecution(input.trim(), sessionId);
      }
    } catch (err) {
      // Add error message to shared history
      addMessage({
        role: "error",
        content: err instanceof Error ? err.message : "An error occurred",
        source: "text",
      });
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  };

  /**
   * Handle streaming execution (mode: "stream")
   */
  const handleStreamExecution = async (
    userInput: string,
    sessionId?: string
  ) => {
    setStreaming(true);

    // Create placeholder message for streaming content
    let streamedContent = "";
    let streamMetadata: Record<string, unknown> = {};
    const streamSteps: SimulationStep[] = [];

    // Add placeholder message to shared history
    const streamMessage = addMessage({
      role: "agent",
      content: "",
      source: "text",
      isFinal: false,
    });

    try {
      const stream = executionService.executeStream(agentId, {
        input: userInput,
        session_id: sessionId,
      });

      for await (const chunk of stream) {
        switch (chunk.type) {
          case "metadata":
            streamMetadata = chunk.metadata || {};
            break;

          case "token":
            if (chunk.content) {
              streamedContent += chunk.content;
              // Update message in real-time
              updateMessage(streamMessage.id, {
                content: streamedContent,
              });
            }
            break;

          case "step":
            // Best-effort capture of streamed steps for the execution panel
            if (chunk.content) {
              streamSteps.push({
                agent_id: agentId,
                agent_name: agentId,
                action: "step",
                output: String(chunk.content),
                timestamp: new Date().toISOString(),
              });
            }
            break;

          case "done":
            // Finalize message with metadata
            const finalMetadata = { ...streamMetadata, ...chunk.metadata, mode: "stream" };
            updateMessage(streamMessage.id, {
              isFinal: true,
              metadata: finalMetadata,
            });

            // Open panel if this is an orchestrator response with metadata
            if ((agentId === "smartrouter" || agentId === "moe") && finalMetadata) {
              if (agentId === "moe") {
                // MoE uses openMoETrace with auto-open
                // Extract trace data from metadata
                const moeTrace = (finalMetadata as any).trace;
                if (moeTrace) {
                  openMoETrace(moeTrace, { open: true });
                }
              } else {
                // SmartRouter uses openPanel
                openPanel(finalMetadata as unknown as SmartRouterMetadata);
              }
            } else if (streamSteps.length > 0) {
              // Generic agent stream: make the right panel available (collapsed by default)
              openExecutionTrace(streamSteps, { open: true });
            }
            break;

          case "error":
            throw new Error(chunk.content || "Stream error");
        }
      }
    } catch (err) {
      // Update streaming message with error
      updateMessage(streamMessage.id, {
        content: err instanceof Error ? err.message : "Streaming failed",
        isFinal: true,
      });
    }
  };

  /**
   * Handle non-streaming execution (mode: "mock" or "real")
   */
  const handleNonStreamExecution = async (
    userInput: string,
    sessionId?: string
  ) => {
    const result =
      mode === "mock"
        ? await executionService.executeMock(agentId, {
          input: userInput,
          session_id: sessionId,
        })
        : await executionService.executeReal(agentId, {
          input: userInput,
          session_id: sessionId,
        });

    // Add agent response to shared history
    addMessage({
      role: "agent",
      content: result.response,
      source: "text",
      metadata: result.metadata,
    });

    // Open panel if this is an orchestrator response with metadata
    if ((agentId === "smartrouter" || agentId === "moe") && result.metadata) {
      if (agentId === "moe") {
        // MoE uses openMoETrace with auto-open
        // Extract trace data from metadata
        const moeTrace = (result.metadata as any).trace;
        if (moeTrace) {
          openMoETrace(moeTrace, { open: true });
        }
      } else {
        // SmartRouter uses openPanel
        openPanel(result.metadata as unknown as SmartRouterMetadata);
      }
    } else if (result.trace && result.trace.length > 0) {
      // Generic agents: make the right-side panel available with execution trace
      openExecutionTrace(result.trace as unknown as SimulationStep[], { open: true });
    }
  };

  const handleClearChat = () => {
    clearMessages();
    setIsUserScrolling(false);
    if (useSession) {
      sessionService.clearSession(agentId);
    }
  };

  /**
   * Handle voice transcript
   */
  const handleVoiceTranscript = (transcript: string) => {
    // Set input with voice transcript
    setInput(transcript);
  };

  /**
   * Handle speaking text with TTS
   */
  const handleSpeak = async (text: string) => {
    if (!voiceSettings.ttsEnabled) return;

    try {
      const audioBlob = await voiceClient.synthesize({
        text,
        voice_id: voiceSettings.selectedVoiceId || undefined,
        profile_name: voiceSettings.selectedProfile,
      });

      // Create audio element and play
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.volume = voiceSettings.volume;
      audio.playbackRate = voiceSettings.playbackSpeed;

      await audio.play();

      // Cleanup
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
    } catch (err) {
      console.error('TTS error:', err);
    }
  };

  /**
   * Auto-play agent responses if enabled
   */
  useEffect(() => {
    if (!voiceSettings.autoPlayResponses || !voiceSettings.ttsEnabled) return;

    const lastMessage = displayMessages[displayMessages.length - 1];
    if (lastMessage && lastMessage.role === 'agent' && lastMessage.content) {
      // Only play if not currently streaming
      if (!streaming) {
        handleSpeak(lastMessage.content);
      }
    }
  }, [messages, voiceSettings.autoPlayResponses, voiceSettings.ttsEnabled, streaming]);

  // Memoize the onMessages callback to prevent infinite re-renders
  // The callback is stable because setVoiceStreamMessages is stable from useState
  const handleVoiceMessages = useCallback((msgs: VoiceConversationMessage[]) => {
    setVoiceStreamMessages(
      msgs.map((m) => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        metadata: { mode: 'voice' },
      }))
    );
  }, []); // Empty deps array because setVoiceStreamMessages is stable

  return (
    <div className="flex flex-col h-full">
      {isVoiceConnected && (
        <VoiceConversationMessages
          onMessages={handleVoiceMessages}
        />
      )}

      {/* Header - Fixed */}
      <div className="flex-none border-b border-border/30 bg-gradient-to-r from-primary/5 to-transparent backdrop-blur-sm">
        <div className="flex items-center justify-between p-4">
          <div>
            <h2 className="text-lg font-semibold">Chat Interface</h2>
            {isVoiceConnected && (
              <div className="mt-1 text-xs text-muted-foreground">
                Voice Mode: <span className="font-semibold">{agentState}</span>
                <VoiceAudioOutput
                  ttsEnabled={!!voiceSettings.ttsEnabled}
                  volume={voiceSettings.volume ?? 1}
                  playbackSpeed={voiceSettings.playbackSpeed ?? 1}
                />
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-0.5">
              Mode: <span className="font-semibold capitalize">{mode}</span>
              {useSession && " • Session: Active"}
            </p>
          </div>
          {isVoiceConnected && (
            <Button
              variant="destructive"
              size="sm"
              onClick={async () => {
                await exitVoiceMode();
              }}
            >
              End Voice Mode
            </Button>
          )}
          {messages.length > 0 && (
            <Button variant="outline" size="sm" onClick={handleClearChat}>
              Clear Chat
            </Button>
          )}
        </div>
      </div>

      {/* Messages Area - Flexible, takes remaining space */}
      <div className="flex-1 relative overflow-hidden">
        <div
          ref={scrollAreaRef}
          onScroll={handleScroll}
          className="custom-scrollbar absolute inset-0 overflow-y-auto space-y-4 p-4"
        >
          {displayMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
              <p className="text-lg font-semibold">Start a conversation</p>
              <p className="text-sm mt-2">
                {mode === "mock" && "Using mock mode - instant responses, no API costs"}
                {mode === "real" && "Using real mode - actual API calls, complete responses"}
                {mode === "stream" && "Using stream mode - real-time token streaming"}
              </p>
            </div>
          ) : (
            displayMessages.map((message, index) => (
              <MessageItem key={index} message={message} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Scroll to Bottom Button */}
        {showScrollButton && (
          <Button
            variant="secondary"
            size="icon"
            className="absolute bottom-4 right-4 rounded-full shadow-xl glass-panel backdrop-blur-xl bg-primary/90 hover:bg-primary text-primary-foreground border-0 z-10"
            onClick={scrollToBottom}
          >
            <ArrowDown className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Input Area - Fixed at bottom with modern styling */}
      <div className="flex-none border-t border-border/30 bg-gradient-to-b from-background/95 to-background backdrop-blur-xl shadow-lg">
        <div className="p-4 space-y-3">
          {/* Voice Input Panel */}
          {voiceSettings.sttEnabled && (
            <VoiceInputPanel
              onTranscript={handleVoiceTranscript}
              disabled={loading || streaming || !agentId}
              className="mb-2"
            />
          )}

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="flex-1 relative">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  streaming
                    ? "Streaming in progress..."
                    : "Type your message... (Shift + Enter for new line)"
                }
                className="resize-none pr-12 min-h-[60px] max-h-[200px] glass-panel bg-card/50 border-border/50 focus:border-primary/50 transition-all"
                rows={2}
                disabled={loading || streaming || !agentId}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !loading && !streaming) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
              />
              {/* Character count or status indicator */}
              {input.length > 0 && (
                <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
                  {input.length}
                </div>
              )}
            </div>
            <button
              type="submit"
              disabled={loading || streaming || !input.trim() || !agentId}
              className="shrink-0 h-[60px] px-6 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2"
              title="Send message (or press Enter)"
            >
              {loading || streaming ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'white' }} />
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <Send className="h-5 w-5" style={{ color: 'white' }} />
                  <span>Send</span>
                </>
              )}
            </button>
          </form>

          {/* Mode Info - Compact */}
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            {mode === "mock" && (
              <>
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                <span>Mock mode - simulated responses</span>
              </>
            )}
            {mode === "real" && (
              <>
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                <span>Real mode - actual API calls</span>
              </>
            )}
            {mode === "stream" && (
              <>
                <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>
                <span>Stream mode - real-time tokens</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
