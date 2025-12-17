/**
 * FlowTooltip
 *
 * Renders a hover tooltip in a portal with a very high z-index.
 * This avoids ReactFlow canvas stacking/transform quirks and prevents the tooltip
 * from being obscured by nodes/edges or clipped by overflow-hidden containers.
 */
 
"use client";

import React, { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

type Placement = "top" | "bottom";

export function FlowTooltip({
  open,
  anchorRef,
  placement = "bottom",
  offset = 12,
  interactive = false,
  children,
}: {
  open: boolean;
  anchorRef: React.RefObject<HTMLElement>;
  placement?: Placement;
  offset?: number;
  interactive?: boolean;
  children: React.ReactNode;
}) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  const style = useMemo<React.CSSProperties>(() => {
    if (!pos) return { display: "none" };
    const translateY = placement === "top" ? " translateY(-100%)" : "";
    return {
      position: "fixed",
      top: pos.top,
      left: pos.left,
      transform: `translateX(-50%)${translateY}`,
      pointerEvents: interactive ? "auto" : "none",
    };
  }, [pos, placement, interactive]);

  useEffect(() => {
    if (!open) {
      setPos(null);
      return;
    }

    let raf = 0;
    const update = () => {
      const el = anchorRef.current;
      if (!el) {
        setPos(null);
        raf = requestAnimationFrame(update);
        return;
      }

      const r = el.getBoundingClientRect();
      const centerX = r.left + r.width / 2;
      const top = placement === "top" ? r.top - offset : r.bottom + offset;

      setPos({ top, left: centerX });
      raf = requestAnimationFrame(update);
    };

    raf = requestAnimationFrame(update);
    return () => cancelAnimationFrame(raf);
  }, [open, anchorRef, placement, offset]);

  if (!open || typeof document === "undefined") return null;
  // Render as a single fixed-position portal element so it isn't clipped by ReactFlow transforms.
  // z-index is set to max-int-ish to avoid being obscured by any in-app overlays.
  return createPortal(
    <div style={{ ...style, zIndex: 2147483647 }}>{children}</div>,
    document.body
  );
}


