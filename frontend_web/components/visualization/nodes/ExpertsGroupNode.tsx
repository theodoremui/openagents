/**
 * ExpertsGroupNode
 *
 * Visual group container for specialist agents in the MoE flow.
 * Renders a dotted outer box to communicate "these nodes are a set".
 */
import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

export function ExpertsGroupNode({ data }: NodeProps) {
  const label = (data as any)?.label ?? 'Specialist Agents';
  const count = (data as any)?.count;

  return (
    <div className="relative w-full h-full">
      {/* Source handle for aggregated output → mixer */}
      <Handle type="source" position={Position.Bottom} className="opacity-0" />

      <div className="w-full h-full rounded-3xl border-2 border-dashed border-slate-300/80 bg-gradient-to-b from-white/70 to-white/40 shadow-[0_18px_50px_-30px_rgba(15,23,42,0.45)]">
        <div className="absolute -top-3 left-6">
          <div className="px-3 py-1 rounded-full bg-white border border-slate-200 shadow-sm text-[11px] font-bold text-slate-700">
            {label}{typeof count === 'number' ? ` • ${count}` : ''}
          </div>
        </div>
      </div>
    </div>
  );
}


