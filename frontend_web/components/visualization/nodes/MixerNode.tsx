/**
 * Mixer Node Component
 *
 * Displays result mixing stage where expert outputs are combined.
 */

import React, { useRef } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { MixerNodeData } from '@/lib/visualization/builders/MoEFlowBuilder';
import { FlowNodeTooltip } from '../FlowNodeTooltip';

export function MixerNode({ data }: NodeProps) {
  // Type guard to ensure data is MixerNodeData
  const mixerData = data as unknown as MixerNodeData;
  const anchorRef = useRef<HTMLDivElement>(null);

  return (
    <FlowNodeTooltip
      anchorRef={anchorRef as React.RefObject<HTMLElement>}
      placement="bottom"
      offset={14}
      render={({ pinned, close }) => (
        <div className="animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="bg-white/95 backdrop-blur-xl border border-gray-200/80 text-gray-900 p-4 rounded-2xl shadow-[0_20px_70px_-10px_rgba(0,0,0,0.3)] w-96">
            <div className="flex items-start justify-between gap-3">
              <div className="font-bold text-sm text-orange-600">Result Mixer</div>
              {pinned && (
                <button
                  className="text-xs text-gray-500 hover:text-gray-800"
                  onClick={(e) => {
                    e.stopPropagation();
                    close();
                  }}
                >
                  Close (Esc)
                </button>
              )}
            </div>

            <div className="space-y-2 text-xs mt-2">
              <div>
                <span className="text-gray-600">Expert Results:</span>
                <span className="ml-2 font-semibold text-gray-800">{mixerData.expertCount}</span>
              </div>
              <div>
                <span className="text-gray-600">Mixing Time:</span>
                <span className="ml-2 font-semibold text-gray-800">{mixerData.latencyMs.toFixed(2)}ms</span>
              </div>
            </div>

            {pinned && (
              <div className="mt-3 space-y-3 text-[11px] text-gray-700">
                <div>
                  <div className="font-semibold text-gray-800">Input</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-28 overflow-auto">
                    {mixerData.inputSummary || "—"}
                  </div>
                </div>
                <div>
                  <div className="font-semibold text-gray-800">Output</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-40 overflow-auto">
                    {mixerData.output || "—"}
                  </div>
                </div>
              </div>
            )}

            {!pinned && (
              <div className="text-xs text-gray-500 mt-2 italic">
                Click to pin details • Drag to reposition
              </div>
            )}
          </div>
        </div>
      )}
    >
      {({ onMouseEnter, onMouseLeave, onPointerDown, onPointerMove, onClick }) => (
        <div
          className="relative w-[360px]"
          ref={anchorRef}
          onMouseEnter={onMouseEnter}
          onMouseLeave={onMouseLeave}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onClick={onClick}
        >
          {/* Top handles */}
          {/* Visible "main" target handle (kept for UX, but we route edges to hidden handles below) */}
          <Handle id="in" type="target" position={Position.Top} className="w-3 h-3 bg-gray-400/50 border-2 border-white shadow-md" />

          {/* Hidden target handles to avoid multi-arrowhead "blob" at convergence. */}
          {/* We spread incoming expert edges across these handles and only show one arrowhead. */}
          <Handle id="in-0" type="target" position={Position.Top} className="opacity-0" style={{ left: '20%' }} />
          <Handle id="in-1" type="target" position={Position.Top} className="opacity-0" style={{ left: '35%' }} />
          <Handle id="in-2" type="target" position={Position.Top} className="opacity-0" style={{ left: '50%' }} />
          <Handle id="in-3" type="target" position={Position.Top} className="opacity-0" style={{ left: '65%' }} />
          <Handle id="in-4" type="target" position={Position.Top} className="opacity-0" style={{ left: '80%' }} />

          {/* Node content - Liquid glass morphism */}
          <div className="group px-6 py-4 rounded-2xl bg-white border border-slate-200 shadow-[0_10px_30px_-15px_rgba(15,23,42,0.35)] w-[360px] transition-all duration-200 hover:bg-slate-50 hover:shadow-[0_16px_44px_-18px_rgba(15,23,42,0.45)] cursor-move">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-orange-500/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <div className="font-extrabold text-xs uppercase tracking-wider text-gray-700">{mixerData.label}</div>
            </div>

            <div className="space-y-1 text-sm text-gray-800">
              <div className="flex justify-between">
                <span className="font-normal">Expert Results:</span>
                <span className="font-bold">{mixerData.expertCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-normal">Mixing Time:</span>
                <span className="font-bold">{mixerData.latencyMs.toFixed(0)}ms</span>
              </div>
            </div>
          </div>

          {/* Bottom handle */}
          <Handle
            id="out"
            type="source"
            position={Position.Bottom}
            className="w-3 h-3 bg-gray-400/50 border-2 border-white shadow-md"
            // Force true horizontal centering: ReactFlow handle positioning uses left + transform.
            style={{ left: '50%', transform: 'translateX(-50%)' }}
          />
        </div>
      )}
    </FlowNodeTooltip>
  );
}
