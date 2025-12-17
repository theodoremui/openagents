/**
 * MergeDotNode
 *
 * A tiny convergence node used to visually merge multiple incoming edges into a single outgoing edge.
 * This avoids ugly "arrowhead blobs" when many edges terminate on the same handle.
 */
import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

export function MergeDotNode(_props: NodeProps) {
  return (
    <div className="relative">
      {/* Multiple incoming edges */}
      <Handle id="in" type="target" position={Position.Top} className="opacity-0" />
      {/* Single outgoing edge */}
      <Handle id="out" type="source" position={Position.Bottom} className="opacity-0" />

      <div
        className="w-3 h-3 rounded-full bg-slate-500/40 border border-slate-400/60 shadow-sm"
        aria-hidden="true"
      />
    </div>
  );
}


