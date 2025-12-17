/**
 * Expert Node Component
 *
 * Displays individual expert execution with status, latency, and tools used.
 * Includes hover tooltip for detailed information.
 */

import React, { useRef } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { ExpertNodeData } from '@/lib/visualization/builders/MoEFlowBuilder';
import { FlowNodeTooltip } from '../FlowNodeTooltip';

export function ExpertNode({ data }: NodeProps) {
  const anchorRef = useRef<HTMLDivElement>(null);

  // Type guard to ensure data is ExpertNodeData
  const expertData = data as unknown as ExpertNodeData;
  const latencyMs = expertData.latencyMs;
  const hasLatency = typeof latencyMs === 'number' && Number.isFinite(latencyMs);

  // Status-based indicator colors (minimal color, using subtle accents)
  const statusIndicator: Record<string, { color: string; pulse: boolean }> = {
    pending: {
      color: 'bg-gray-400/50 shadow-gray-400/30',
      pulse: false,
    },
    executing: {
      color: 'bg-blue-500/60 shadow-blue-500/50',
      pulse: true,
    },
    completed: {
      color: 'bg-green-500/60 shadow-green-500/50',
      pulse: false,
    },
    failed: {
      color: 'bg-red-500/60 shadow-red-500/50',
      pulse: false,
    },
  };

  const indicator = statusIndicator[expertData.status] || statusIndicator.pending;

  return (
    <FlowNodeTooltip
      anchorRef={anchorRef as React.RefObject<HTMLElement>}
      placement="bottom"
      offset={14}
      render={({ pinned, close }) => (
        <div className="animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="bg-white/95 backdrop-blur-xl border border-gray-200/80 text-gray-900 p-4 rounded-2xl shadow-[0_20px_70px_-10px_rgba(0,0,0,0.3)] w-96">
            <div className="flex items-start justify-between gap-3">
              <div className="font-bold text-sm text-emerald-600">{expertData.label}</div>
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
                <span className="text-gray-600">Expert ID:</span>
                <span className="ml-2 font-semibold text-gray-800">{expertData.expertId}</span>
              </div>
              <div>
                <span className="text-gray-600">Status:</span>
                <span className="ml-2 font-semibold text-gray-800">{expertData.status}</span>
              </div>
              <div>
                <span className="text-gray-600">Confidence:</span>
                <span className="ml-2 font-semibold text-gray-800">
                  {(expertData.confidence * 100).toFixed(0)}%
                </span>
              </div>
              {hasLatency && (
                <div>
                  <span className="text-gray-600">Latency:</span>
                  <span className="ml-2 font-semibold text-gray-800">{latencyMs.toFixed(2)}ms</span>
                </div>
              )}
              {expertData.toolsUsed && expertData.toolsUsed.length > 0 && (
                <div>
                  <span className="text-gray-600">Tools Used:</span>
                  <ul className="ml-4 mt-1 list-disc text-gray-700">
                    {expertData.toolsUsed.map((tool: string, i: number) => (
                      <li key={i}>{tool}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {pinned && (
              <div className="mt-3 space-y-3 text-[11px] text-gray-700">
                <div>
                  <div className="font-semibold text-gray-800">Input</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-28 overflow-auto">
                    {expertData.input || "—"}
                  </div>
                </div>
                <div>
                  <div className="font-semibold text-gray-800">Output</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-40 overflow-auto">
                    {expertData.response || "—"}
                  </div>
                </div>
                {expertData.error && (
                  <div className="text-red-700 bg-red-50 border border-red-200 p-2 rounded-lg">
                    <span className="font-bold">Error:</span> {expertData.error}
                  </div>
                )}
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
          className="relative"
          ref={anchorRef}
          onMouseEnter={onMouseEnter}
          onMouseLeave={onMouseLeave}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onClick={onClick}
        >
          {/* Top handle */}
          <Handle type="target" position={Position.Top} className="w-3 h-3 bg-gray-400/50 border-2 border-white shadow-md" />

          {/* Node content - Liquid glass morphism */}
          <div className="group px-5 py-3 rounded-2xl bg-white border border-slate-200 shadow-[0_10px_30px_-15px_rgba(15,23,42,0.35)] w-[220px] h-[132px] transition-all duration-200 hover:bg-slate-50 hover:shadow-[0_16px_44px_-18px_rgba(15,23,42,0.45)] cursor-move">
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${indicator.color} shadow-lg ${indicator.pulse ? 'animate-pulse' : ''}`} />
              <div className="font-extrabold text-xs uppercase tracking-wider text-gray-700">
                {expertData.expertId}
              </div>
            </div>

            <div className="text-sm font-semibold mb-2 text-gray-900">{expertData.label}</div>

            {/* Status indicators */}
            <div className="space-y-1 text-xs text-gray-700">
              <div className="flex justify-between">
                <span>Status:</span>
                <span className="font-semibold">{expertData.status}</span>
              </div>
              {hasLatency && (
                <div className="flex justify-between">
                  <span>Latency:</span>
                  <span className="font-semibold">{latencyMs.toFixed(0)}ms</span>
                </div>
              )}
              {expertData.toolsUsed && expertData.toolsUsed.length > 0 && (
                <div className="flex justify-between">
                  <span>Tools:</span>
                  <span className="font-semibold">{expertData.toolsUsed.length}</span>
                </div>
              )}
            </div>
          </div>

          {/* Bottom handle */}
          <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-gray-400 border-2 border-white" />
        </div>
      )}
    </FlowNodeTooltip>
  );
}
