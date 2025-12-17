"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import type { SmartRouterMetadata } from "@/lib/types";
import type { MoETrace } from "@/lib/visualization/types";
import type { SimulationStep } from "@/lib/types";

/**
 * Orchestration Panel Context (backwards-compatible name: SmartRouterContext)
 *
 * Manages the state and visibility of the right-side orchestration visualization panel.
 *
 * Design Principles:
 * - SRP: State only (no rendering)
 * - Open/Closed: Add new panel kinds without rewriting callers
 * - Backwards compatible: existing SmartRouter callers can keep using openPanel(metadata)
 */

type PanelKind = "smartrouter" | "moe" | "execution" | null;

interface SmartRouterContextState {
  // Panel state
  isPanelOpen: boolean;
  panelKind: PanelKind;

  // Payloads
  metadata: SmartRouterMetadata | null;
  moeTrace: MoETrace | null;
  executionTrace: SimulationStep[] | null;

  // Actions
  /** Backwards-compatible: opens SmartRouter panel content */
  openPanel: (metadata: SmartRouterMetadata) => void;
  /** Opens MoE trace content (used by voice mode) */
  openMoETrace: (trace: MoETrace, options?: { open?: boolean }) => void;
  /** Opens generic execution trace content (for any agent) */
  openExecutionTrace: (trace: SimulationStep[], options?: { open?: boolean }) => void;

  expandPanel: () => void;
  closePanel: () => void;
  togglePanel: () => void;

  updateMetadata: (metadata: SmartRouterMetadata) => void;
  clearMetadata: () => void;
  clearMoETrace: () => void;
  clearExecutionTrace: () => void;
  clearAll: () => void;
}

const SmartRouterContext = createContext<SmartRouterContextState | undefined>(undefined);

interface SmartRouterProviderProps {
  children: ReactNode;
}

export function SmartRouterProvider({ children }: SmartRouterProviderProps) {
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [panelKind, setPanelKind] = useState<PanelKind>(null);
  const [metadata, setMetadata] = useState<SmartRouterMetadata | null>(null);
  const [moeTrace, setMoETrace] = useState<MoETrace | null>(null);
  const [executionTrace, setExecutionTrace] = useState<SimulationStep[] | null>(null);

  const openPanel = useCallback((newMetadata: SmartRouterMetadata) => {
    setPanelKind("smartrouter");
    setMetadata(newMetadata);
    setMoETrace(null);
    setExecutionTrace(null);
    // Open by default so users always see the reasoning panel is available.
    // They can collapse it via the floating button.
    setIsPanelOpen(true);
  }, []);

  const openMoETrace = useCallback((trace: MoETrace, options?: { open?: boolean }) => {
    setPanelKind("moe");
    setMoETrace(trace);
    setMetadata(null);
    setExecutionTrace(null);
    // For voice-mode, default to open for immediate visibility
    setIsPanelOpen(options?.open ?? true);
  }, []);

  const openExecutionTrace = useCallback((trace: SimulationStep[], options?: { open?: boolean }) => {
    setPanelKind("execution");
    setExecutionTrace(trace);
    setMetadata(null);
    setMoETrace(null);
    // Default to collapsed; user can expand.
    setIsPanelOpen(options?.open ?? false);
  }, []);

  const expandPanel = useCallback(() => {
    setIsPanelOpen(true);
  }, []);

  const closePanel = useCallback(() => {
    setIsPanelOpen(false);
  }, []);

  const togglePanel = useCallback(() => {
    setIsPanelOpen((prev) => !prev);
  }, []);

  const updateMetadata = useCallback((newMetadata: SmartRouterMetadata) => {
    setPanelKind("smartrouter");
    setMetadata(newMetadata);
    setMoETrace(null);
  }, []);

  const clearMetadata = useCallback(() => {
    setMetadata(null);
    setIsPanelOpen(false);
    setPanelKind((k) => (k === "smartrouter" ? null : k));
  }, []);

  const clearMoETrace = useCallback(() => {
    setMoETrace(null);
    setIsPanelOpen(false);
    setPanelKind((k) => (k === "moe" ? null : k));
  }, []);

  const clearExecutionTrace = useCallback(() => {
    setExecutionTrace(null);
    setIsPanelOpen(false);
    setPanelKind((k) => (k === "execution" ? null : k));
  }, []);

  const clearAll = useCallback(() => {
    setMetadata(null);
    setMoETrace(null);
    setExecutionTrace(null);
    setPanelKind(null);
    setIsPanelOpen(false);
  }, []);

  const value: SmartRouterContextState = {
    isPanelOpen,
    panelKind,
    metadata,
    moeTrace,
    executionTrace,
    openPanel,
    openMoETrace,
    openExecutionTrace,
    expandPanel,
    closePanel,
    togglePanel,
    updateMetadata,
    clearMetadata,
    clearMoETrace,
    clearExecutionTrace,
    clearAll,
  };

  return (
    <SmartRouterContext.Provider value={value}>
      {children}
    </SmartRouterContext.Provider>
  );
}

export function useSmartRouterPanel(): SmartRouterContextState {
  const context = useContext(SmartRouterContext);
  if (!context) {
    throw new Error("useSmartRouterPanel must be used within SmartRouterProvider");
  }
  return context;
}
