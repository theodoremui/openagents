/**
 * Voice Context
 *
 * Global state management for voice features.
 * Provides:
 * - Voice API client access
 * - Voice settings management
 * - Available voices list
 * - Voice feature flags
 */

'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode, useMemo } from 'react';
import { VoiceApiClient, getVoiceApiClient, VoiceInfo } from '../services/VoiceApiClient';

/**
 * Voice settings that can be customized
 */
export interface VoiceSettings {
  /** Selected voice ID */
  selectedVoiceId: string | null;
  /** Selected voice profile name */
  selectedProfile: string;
  /** TTS enabled */
  ttsEnabled: boolean;
  /** STT enabled */
  sttEnabled: boolean;
  /** Auto-play agent responses */
  autoPlayResponses: boolean;
  /** Playback volume (0.0 - 1.0) */
  volume: number;
  /** Playback speed (0.5 - 2.0) */
  playbackSpeed: number;
}

/**
 * Voice context state
 */
export interface VoiceContextState {
  /** Voice API client */
  client: VoiceApiClient;
  /** Current voice settings */
  settings: VoiceSettings;
  /** Available voices */
  voices: VoiceInfo[];
  /** Whether voices are loading */
  voicesLoading: boolean;
  /** Voice loading error */
  voicesError: string | null;
  /** Voice service health status */
  isHealthy: boolean;

  /** Update voice settings */
  updateSettings: (updates: Partial<VoiceSettings>) => void;
  /** Refresh voices list */
  refreshVoices: () => Promise<void>;
  /** Check service health */
  checkHealth: () => Promise<void>;
}

/**
 * Default voice settings
 */
const DEFAULT_SETTINGS: VoiceSettings = {
  selectedVoiceId: null,
  selectedProfile: 'default',
  ttsEnabled: true,
  sttEnabled: true,
  autoPlayResponses: false,
  volume: 1.0,
  playbackSpeed: 1.0,
};

/**
 * Voice context
 */
const VoiceContext = createContext<VoiceContextState | undefined>(undefined);

/**
 * Voice provider props
 */
export interface VoiceProviderProps {
  children: ReactNode;
  /** Initial voice settings (optional) */
  initialSettings?: Partial<VoiceSettings>;
  /** Whether to load voices on mount (default: true) */
  loadVoicesOnMount?: boolean;
}

/**
 * Voice provider component
 */
export const VoiceProvider: React.FC<VoiceProviderProps> = ({
  children,
  initialSettings,
  loadVoicesOnMount = true,
}) => {
  // Voice API client
  const client = useMemo(() => getVoiceApiClient(), []);

  // State
  const [settings, setSettings] = useState<VoiceSettings>({
    ...DEFAULT_SETTINGS,
    ...initialSettings,
  });
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [voicesError, setVoicesError] = useState<string | null>(null);
  const [isHealthy, setIsHealthy] = useState(true);

  /**
   * Update voice settings
   */
  const updateSettings = (updates: Partial<VoiceSettings>) => {
    setSettings((prev) => ({
      ...prev,
      ...updates,
    }));

    // Persist to localStorage
    if (typeof window !== 'undefined') {
      try {
        const updatedSettings = { ...settings, ...updates };
        localStorage.setItem('voice_settings', JSON.stringify(updatedSettings));
      } catch (err) {
        console.warn('Failed to persist voice settings:', err);
      }
    }
  };

  /**
   * Load voices from API
   */
  const refreshVoices = async () => {
    setVoicesLoading(true);
    setVoicesError(null);

    try {
      const voicesList = await client.listVoices(true); // Force refresh
      setVoices(voicesList);

      // Set default voice if not selected
      if (!settings.selectedVoiceId && voicesList.length > 0) {
        updateSettings({ selectedVoiceId: voicesList[0].voice_id });
      }
    } catch (err) {
      const error = err as Error;
      setVoicesError(error.message);
      console.error('Failed to load voices:', error);
    } finally {
      setVoicesLoading(false);
    }
  };

  /**
   * Check service health
   */
  const checkHealth = async () => {
    try {
      const health = await client.healthCheck();
      setIsHealthy(health.status === 'healthy');
    } catch (err) {
      console.error('Health check failed:', err);
      setIsHealthy(false);
    }
  };

  /**
   * Load settings from localStorage on mount
   */
  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem('voice_settings');
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<VoiceSettings>;
        setSettings((prev) => ({ ...prev, ...parsed }));
      }
    } catch (err) {
      console.warn('Failed to load voice settings from localStorage:', err);
    }
  }, []);

  /**
   * Load voices on mount if enabled
   */
  useEffect(() => {
    if (loadVoicesOnMount) {
      refreshVoices();
      checkHealth();
    }
  }, [loadVoicesOnMount]);

  /**
   * Context value
   */
  const value: VoiceContextState = useMemo(
    () => ({
      client,
      settings,
      voices,
      voicesLoading,
      voicesError,
      isHealthy,
      updateSettings,
      refreshVoices,
      checkHealth,
    }),
    [
      client,
      settings,
      voices,
      voicesLoading,
      voicesError,
      isHealthy,
    ]
  );

  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>;
};

/**
 * Hook to access voice context
 *
 * @throws Error if used outside VoiceProvider
 */
export function useVoiceContext(): VoiceContextState {
  const context = useContext(VoiceContext);

  if (context === undefined) {
    throw new Error('useVoiceContext must be used within a VoiceProvider');
  }

  return context;
}

/**
 * Hook to access voice settings
 */
export function useVoiceSettings(): [VoiceSettings, (updates: Partial<VoiceSettings>) => void] {
  const { settings, updateSettings } = useVoiceContext();
  return [settings, updateSettings];
}

/**
 * Hook to access available voices
 */
export function useVoices(): {
  voices: VoiceInfo[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
} {
  const { voices, voicesLoading, voicesError, refreshVoices } = useVoiceContext();
  return {
    voices,
    loading: voicesLoading,
    error: voicesError,
    refresh: refreshVoices,
  };
}

/**
 * Hook to access voice API client
 */
export function useVoiceClient(): VoiceApiClient {
  const { client } = useVoiceContext();
  return client;
}
