/**
 * Output Node Component
 *
 * Displays final response with total latency and performance indicators.
 */

import React, { useRef } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { OutputNodeData } from '@/lib/visualization/builders/MoEFlowBuilder';
import { FlowNodeTooltip } from '../FlowNodeTooltip';

export function OutputNode({ data }: NodeProps) {
  // Type guard to ensure data is OutputNodeData
  const outputData = data as unknown as OutputNodeData;
  const anchorRef = useRef<HTMLDivElement>(null);

  return (
    <FlowNodeTooltip
      anchorRef={anchorRef as React.RefObject<HTMLElement>}
      placement="top"
      offset={14}
      render={({ pinned, close }) => (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="bg-white/95 backdrop-blur-xl border border-gray-200/80 text-gray-900 p-4 rounded-2xl shadow-[0_20px_70px_-10px_rgba(0,0,0,0.3)] w-[32rem]">
            <div className="flex items-start justify-between gap-3">
              <div className="font-bold text-sm text-green-600">Final Response</div>
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
                <span className="text-gray-600">Total Latency:</span>
                <span className="ml-2 font-semibold text-gray-800">{outputData.totalLatencyMs.toFixed(0)}ms</span>
              </div>
              <div>
                <span className="text-gray-600">Cache:</span>
                <span className="ml-2 font-semibold text-gray-800">{outputData.cacheHit ? "hit" : "miss"}</span>
              </div>
              <div>
                <span className="text-gray-600">Fallback:</span>
                <span className="ml-2 font-semibold text-gray-800">{outputData.fallback ? "yes" : "no"}</span>
              </div>
            </div>

            {pinned && (
              <div className="mt-3 space-y-3 text-[11px] text-gray-700">
                <div>
                  <div className="font-semibold text-gray-800">Input</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-28 overflow-auto">
                    {outputData.inputSummary || "—"}
                  </div>
                </div>
                <div>
                  <div className="font-semibold text-gray-800">Output</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-64 overflow-auto">
                    {outputData.response || "—"}
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
          {/* Top handle - centered on the node */}
          <Handle
            id="in"
            type="target"
            position={Position.Top}
            className="w-3 h-3 bg-gray-400/50 border-2 border-white shadow-md"
            // Force true horizontal centering: ReactFlow handle positioning uses left + transform.
            // Position at 50% of the 360px container width (180px from left)
            style={{ left: '50%', transform: 'translateX(-50%)' }}
          />

          {/* Node content - Liquid glass morphism */}
          <div className="group px-6 py-4 rounded-2xl bg-white border border-slate-200 shadow-[0_10px_30px_-15px_rgba(15,23,42,0.35)] w-[360px] transition-all duration-200 hover:bg-slate-50 hover:shadow-[0_16px_44px_-18px_rgba(15,23,42,0.45)] cursor-move">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-green-500/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="font-extrabold text-xs uppercase tracking-wider text-gray-700">{outputData.label}</div>
            </div>

            <div className="space-y-1 text-sm text-gray-800">
              <div className="flex justify-between">
                <span className="font-normal">Total Latency:</span>
                <span className="font-bold">{outputData.totalLatencyMs.toFixed(0)}ms</span>
              </div>

              {/* Performance badges */}
              <div className="flex gap-2 mt-2">
                {outputData.cacheHit && (
                  <div className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 rounded-full text-xs font-semibold text-blue-700">
                    ⚡ Cached
                  </div>
                )}
                {outputData.fallback && (
                  <div className="px-2 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-xs font-semibold text-yellow-700">
                    ⚠️ Fallback
                  </div>
                )}
                {!outputData.cacheHit && !outputData.fallback && (
                  <div className="px-2 py-1 bg-green-500/10 border border-green-500/30 rounded-full text-xs font-semibold text-green-700">
                    ✓ Success
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bottom handle (hidden) */}
          <Handle id="out" type="source" position={Position.Bottom} className="opacity-0" />
        </div>
      )}
    </FlowNodeTooltip>
  );
}
