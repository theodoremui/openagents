"use client";

import { ServiceProvider } from "@/lib/services/ServiceContext";
import { SmartRouterProvider } from "@/lib/contexts/SmartRouterContext";
import { VoiceProvider } from "@/lib/contexts/VoiceContext";
import { VoiceModeProvider } from "@/components/voice";
import { ConversationHistoryProvider } from "@/lib/contexts/ConversationHistoryContext";

/**
 * Global providers wrapper
 *
 * Provides:
 * - ServiceProvider: Dependency injection for services (also initializes API client)
 * - SmartRouterProvider: SmartRouter panel state management
 * - VoiceProvider: Voice interaction state management (async TTS/STT)
 * - ConversationHistoryProvider: Shared conversation history (text + voice)
 * - VoiceModeProvider: Real-time voice mode (LiveKit)
 * - Other global state (can be extended)
 *
 * Follows IoC (Inversion of Control) pattern for clean architecture.
 * Note: API client is initialized by ServiceProvider, not here.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ServiceProvider>
      <SmartRouterProvider>
        <VoiceProvider loadVoicesOnMount={true}>
          <ConversationHistoryProvider>
            <VoiceModeProvider>
              {children}
            </VoiceModeProvider>
          </ConversationHistoryProvider>
        </VoiceProvider>
      </SmartRouterProvider>
    </ServiceProvider>
  );
}
