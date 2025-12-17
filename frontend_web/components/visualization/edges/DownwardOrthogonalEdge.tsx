/**
 * DownwardOrthogonalEdge
 *
 * A custom edge that routes in a clean "down, across, down" shape.
 * This guarantees edges do not go back upward (for normal top-to-bottom flows),
 * eliminating visually noisy "down → up → down" kinks that can happen with
 * generic orthogonal routing when nodes are close or edges converge.
 */
import React from 'react';
import { BaseEdge, EdgeProps, getSmoothStepPath } from '@xyflow/react';

export function DownwardOrthogonalEdge(props: EdgeProps) {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    style,
    markerEnd,
  } = props;

  // If the user drags nodes such that the "target" is above the source, we fall back
  // to smoothstep. Enforcing monotonic-down routing would require overshooting and
  // coming back up, which is exactly what we want to avoid.
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
  const absDx = Math.abs(dx);
  const absDy = Math.abs(dy);

  // If this is effectively a vertical edge, draw a clean downward line.
  // This avoids tiny "box" artifacts caused by rounded-corner routing when dx≈0.
  if (absDx < 2) {
    const path = `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`;
    return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />;
  }

  // Midpoint routing line ensures only downward + horizontal segments.
  // Clamp midY strictly between sourceY and targetY to avoid any upward movement.
  const midY = sourceY + (targetY - sourceY) * 0.58;

  // Rounded turns (quarter-circle arcs) so corners don't look like harsh 90° bends.
  const sign = dx >= 0 ? 1 : -1;

  // Clamp radius so we don't self-intersect on tight edges.
  let r = Math.max(6, Math.min(18, absDx / 2, absDy / 3));
  // Ensure the two rounded corners fit within the available horizontal delta.
  // If not, fall back to a simple orthogonal path (still monotonic-down).
  r = Math.min(r, absDx / 2);
  if (r < 1) {
    const path = `M ${sourceX} ${sourceY} L ${sourceX} ${midY} L ${targetX} ${midY} L ${targetX} ${targetY}`;
    return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />;
  }
  const sweep = sign === 1 ? 1 : 0;

  // Path: down → (arc) → across → (arc) → down, strictly monotonic in Y.
  // 1) Vertical down to just above midY, then arc into horizontal
  // 2) Horizontal to near targetX, then arc into final vertical down
  const x1 = sourceX;
  const y1 = midY - r;
  const x2 = sourceX + sign * r;
  const y2 = midY;
  const x3 = targetX - sign * r;
  const y3 = midY;
  const x4 = targetX;
  const y4 = midY + r;

  const path = [
    `M ${sourceX} ${sourceY}`,
    `L ${x1} ${y1}`,
    `A ${r} ${r} 0 0 ${sweep} ${x2} ${y2}`,
    `L ${x3} ${y3}`,
    `A ${r} ${r} 0 0 ${sweep} ${x4} ${y4}`,
    `L ${targetX} ${targetY}`,
  ].join(' ');

  return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />;
}


