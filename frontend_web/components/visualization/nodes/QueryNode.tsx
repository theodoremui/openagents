/**
 * Query Node Component
 *
 * Displays the user's query at the top of the MoE flow.
 * Modern, clean design with glass morphism effect.
 */

import React, { useRef } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { QueryNodeData } from '@/lib/visualization/builders/MoEFlowBuilder';
import { FlowNodeTooltip } from '../FlowNodeTooltip';

export function QueryNode({ data }: NodeProps) {
  // Type guard to ensure data is QueryNodeData
  const queryData = data as unknown as QueryNodeData;
  const anchorRef = useRef<HTMLDivElement>(null);

  return (
    <FlowNodeTooltip
      anchorRef={anchorRef as React.RefObject<HTMLElement>}
      placement="bottom"
      offset={14}
      render={({ pinned, close }) => (
        <div className="animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="bg-white/95 backdrop-blur-xl border border-gray-200/80 text-gray-900 p-4 rounded-2xl shadow-[0_20px_70px_-10px_rgba(0,0,0,0.3)] max-w-lg">
            <div className="flex items-start justify-between gap-3">
              <div className="font-bold text-sm text-blue-600">User Query</div>
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

            <div className="text-xs text-gray-700 leading-relaxed mt-2 whitespace-pre-wrap">
              {queryData.query}
            </div>

            {pinned && (
              <div className="mt-3 space-y-2 text-[11px] text-gray-700">
                <div>
                  <div className="font-semibold text-gray-800">Output</div>
                  <div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg p-2 whitespace-pre-wrap max-h-40 overflow-auto">
                    {queryData.output || queryData.query}
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
          {/* Top handle (hidden, for positioning) */}
          <Handle type="target" position={Position.Top} className="opacity-0" />

          {/* Node content - Liquid glass morphism */}
          <div className="group px-6 py-4 rounded-2xl bg-white border border-slate-200 shadow-[0_10px_30px_-15px_rgba(15,23,42,0.35)] w-[360px] transition-all duration-200 hover:bg-slate-50 hover:shadow-[0_16px_44px_-18px_rgba(15,23,42,0.45)] cursor-move">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-blue-500/60 animate-pulse shadow-lg shadow-blue-500/50" />
              <div className="font-extrabold text-xs uppercase tracking-wider text-gray-700">
                {queryData.label}
              </div>
            </div>
            <div className="text-sm leading-relaxed max-w-md overflow-hidden text-ellipsis whitespace-nowrap text-gray-900 font-semibold">
              {queryData.query}
            </div>
          </div>

          {/* Bottom handle */}
          <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-blue-500 border-2 border-white" />
        </div>
      )}
    </FlowNodeTooltip>
  );
}
