/**
 * Selector Node Component
 *
 * Displays expert selection stage with latency and expert count.
 */

import React, { useRef } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { SelectorNodeData } from '@/lib/visualization/builders/MoEFlowBuilder';
import { FlowNodeTooltip } from '../FlowNodeTooltip';

export function SelectorNode({ data }: NodeProps) {
  // Type guard to ensure data is SelectorNodeData
  const selectorData = data as unknown as SelectorNodeData;
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
              <div className="font-bold text-sm text-purple-600">Expert Selector</div>
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
                <span className="text-gray-600">Selected Experts:</span>
                <span className="ml-2 font-semibold text-gray-800">{selectorData.selectedCount}</span>
              </div>
              <div>
                <span className="text-gray-600">Selection Time:</span>
                <span className="ml-2 font-semibold text-gray-800">{selectorData.latencyMs.toFixed(2)}ms</span>
              </div>
            </div>

            {pinned && (
              <div className="mt-3 space-y-3 text-[11px] text-gray-700">
                <div>
                  <div className="font-semibold text-gray-800">Input</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-28 overflow-auto">
                    {selectorData.input || "—"}
                  </div>
                </div>
                <div>
                  <div className="font-semibold text-gray-800">Output</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-40 overflow-auto">
                    {(selectorData.selectedExperts || []).join(", ") || "—"}
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
          <div className="group px-6 py-4 rounded-2xl bg-white border border-slate-200 shadow-[0_10px_30px_-15px_rgba(15,23,42,0.35)] w-[360px] transition-all duration-200 hover:bg-slate-50 hover:shadow-[0_16px_44px_-18px_rgba(15,23,42,0.45)] cursor-move">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-purple-500/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <div className="font-extrabold text-xs uppercase tracking-wider text-gray-700">{selectorData.label}</div>
            </div>

            <div className="space-y-1 text-sm text-gray-800">
              <div className="flex justify-between">
                <span className="font-normal">Selected Experts:</span>
                <span className="font-bold">{selectorData.selectedCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-normal">Selection Time:</span>
                <span className="font-bold">{selectorData.latencyMs.toFixed(0)}ms</span>
              </div>
            </div>
          </div>

          {/* Bottom handle */}
          <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-gray-400/50 border-2 border-white shadow-md" />
        </div>
      )}
    </FlowNodeTooltip>
  );
}
