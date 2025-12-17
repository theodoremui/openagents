/**
 * DownwardBezierEdge
 *
 * Simplest visually pleasing edge for top-to-bottom flows:
 * a single smooth bezier curve that (when target is below source) never needs
 * orthogonal kinks/loops.
 */
import React from 'react';
import { BaseEdge, EdgeProps, getSmoothStepPath } from '@xyflow/react';

export function DownwardBezierEdge(props: EdgeProps) {
  const { id, sourceX, sourceY, targetX, targetY, style, markerEnd } = props;

  // If the user drags nodes such that the "target" is above the source, fall back to smoothstep.
  if (targetY <= sourceY) {
    const [path] = getSmoothStepPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
      borderRadius: 18,
      offset: 24,
    });
    return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />;
  }

  const dx = targetX - sourceX;
  const dy = targetY - sourceY;

  // Control points keep Y strictly increasing → avoids "going back up".
  const c1x = sourceX;
  const c1y = sourceY + dy * 0.35;
  const c2x = targetX;
  const c2y = sourceY + dy * 0.65;

  // If essentially vertical, a straight line reads best.
  if (Math.abs(dx) < 2) {
    const path = `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`;
    return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />;
  }

  const path = `M ${sourceX} ${sourceY} C ${c1x} ${c1y} ${c2x} ${c2y} ${targetX} ${targetY}`;
  return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />;
}




