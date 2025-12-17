/**
 * FlowNodeTooltip
 *
 * Unified tooltip behavior for ReactFlow nodes:
 * - Hover shows a quick tooltip
 * - Click pins the tooltip open (interactive) for deeper inspection
 * - Escape closes the pinned tooltip
 *
 * This provides a single, consistent mechanism across all node types.
 */
 
"use client";

import React from "react";
import { FlowTooltip } from "./FlowTooltip";

export function FlowNodeTooltip({
  anchorRef,
  placement = "bottom",
  offset = 14,
  render,
  children,
}: {
  anchorRef: React.RefObject<HTMLElement>;
  placement?: "top" | "bottom";
  offset?: number;
  render: (opts: { pinned: boolean; close: () => void }) => React.ReactNode;
  children: (handlers: {
    onMouseEnter: () => void;
    onMouseLeave: () => void;
    onPointerDown: (e: React.PointerEvent) => void;
    onPointerMove: (e: React.PointerEvent) => void;
    onClick: (e: React.MouseEvent) => void;
  }) => React.ReactNode;
}) {
  const [hovered, setHovered] = React.useState(false);
  const [pinned, setPinned] = React.useState(false);

  // Avoid treating a drag as a click-to-pin.
  const downRef = React.useRef<{ x: number; y: number } | null>(null);
  const movedRef = React.useRef(false);

  const close = React.useCallback(() => {
    setPinned(false);
  }, []);

  React.useEffect(() => {
    if (!pinned) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [pinned, close]);

  const onMouseEnter = React.useCallback(() => setHovered(true), []);
  const onMouseLeave = React.useCallback(() => {
    setHovered(false);
  }, []);

  const onPointerDown = React.useCallback((e: React.PointerEvent) => {
    downRef.current = { x: e.clientX, y: e.clientY };
    movedRef.current = false;
  }, []);

  const onPointerMove = React.useCallback((e: React.PointerEvent) => {
    const d = downRef.current;
    if (!d) return;
    const dx = Math.abs(e.clientX - d.x);
    const dy = Math.abs(e.clientY - d.y);
    if (dx + dy > 6) movedRef.current = true;
  }, []);

  const onClick = React.useCallback((e: React.MouseEvent) => {
    // If user dragged the node, don't toggle the pinned tooltip.
    if (movedRef.current) return;

    // Prevent the click from being interpreted by parent UI elements.
    e.stopPropagation();
    setPinned((v) => !v);
  }, []);

  const open = hovered || pinned;

  return (
    <>
      {children({ onMouseEnter, onMouseLeave, onPointerDown, onPointerMove, onClick })}
      <FlowTooltip
        open={open}
        anchorRef={anchorRef}
        placement={placement}
        offset={offset}
        interactive={pinned}
      >
        {render({ pinned, close })}
      </FlowTooltip>
    </>
  );
}


