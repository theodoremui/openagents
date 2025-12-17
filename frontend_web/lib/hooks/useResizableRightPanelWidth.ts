/**
 * useResizableRightPanelWidth
 *
 * Small, focused hook for a right-docked resizable panel.
 *
 * Design goals:
 * - SRP: only manages width state + pointer drag behavior
 * - DRY: reusable for any right-side docked panel (not just SmartRouterPanel)
 * - Robustness: pointer capture, drag threshold, clamping, persistence
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export function useResizableRightPanelWidth({
  storageKey,
  defaultWidthVw = 30,
  minWidthVw = 22,
  maxWidthVw = 70,
  enabled = true,
}: {
  storageKey: string;
  defaultWidthVw?: number;
  minWidthVw?: number;
  maxWidthVw?: number;
  enabled?: boolean;
}) {
  const clamp = useCallback(
    (v: number) => Math.max(minWidthVw, Math.min(maxWidthVw, v)),
    [minWidthVw, maxWidthVw]
  );

  const [widthVw, setWidthVw] = useState<number>(clamp(defaultWidthVw));
  const resizingRef = useRef(false);
  const downRef = useRef<{ x: number } | null>(null);
  const cleanupMouseListenersRef = useRef<(() => void) | null>(null);

  // Load persisted width
  useEffect(() => {
    if (!enabled) return;
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return;
    setWidthVw(clamp(parsed));
  }, [storageKey, clamp, enabled]);

  // Persist width
  useEffect(() => {
    if (!enabled) return;
    if (typeof window === "undefined") return;
    window.localStorage.setItem(storageKey, String(widthVw));
  }, [storageKey, widthVw, enabled]);

  const applyClientX = useCallback((clientX: number) => {
    const w = typeof window !== "undefined" ? window.innerWidth : 0;
    if (!w) return;
    const nextVw = ((w - clientX) / w) * 100;
    setWidthVw(clamp(nextVw));
  }, [clamp]);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (!enabled) return;
    resizingRef.current = true;
    downRef.current = { x: e.clientX };
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    e.preventDefault();
    e.stopPropagation();
  }, [enabled]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!enabled) return;
    if (!resizingRef.current) return;
    applyClientX(e.clientX);
    e.preventDefault();
    e.stopPropagation();
  }, [applyClientX, enabled]);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    if (!enabled) return;
    resizingRef.current = false;
    downRef.current = null;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    e.preventDefault();
    e.stopPropagation();
  }, [enabled]);

  // Mouse fallback (some environments / embedded webviews may not fully support pointer events)
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (!enabled) return;
    resizingRef.current = true;
    downRef.current = { x: e.clientX };

    // Clean up any previous listeners just in case
    cleanupMouseListenersRef.current?.();
    cleanupMouseListenersRef.current = null;

    const onMove = (ev: MouseEvent) => {
      if (!resizingRef.current) return;
      applyClientX(ev.clientX);
      ev.preventDefault();
      ev.stopPropagation();
    };
    const onUp = (ev: MouseEvent) => {
      resizingRef.current = false;
      downRef.current = null;
      window.removeEventListener("mousemove", onMove, true);
      window.removeEventListener("mouseup", onUp, true);
      cleanupMouseListenersRef.current = null;
      ev.preventDefault();
      ev.stopPropagation();
    };

    window.addEventListener("mousemove", onMove, true);
    window.addEventListener("mouseup", onUp, true);
    cleanupMouseListenersRef.current = () => {
      window.removeEventListener("mousemove", onMove, true);
      window.removeEventListener("mouseup", onUp, true);
    };

    e.preventDefault();
    e.stopPropagation();
  }, [applyClientX, enabled]);

  useEffect(() => {
    return () => {
      cleanupMouseListenersRef.current?.();
      cleanupMouseListenersRef.current = null;
    };
  }, []);

  const handleProps = useMemo(
    () => ({
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onMouseDown,
    }),
    [onPointerDown, onPointerMove, onPointerUp, onMouseDown]
  );

  return { widthVw, setWidthVw, handleProps };
}


