/**
 * MoE Flow Visualization Component
 *
 * Main ReactFlow visualization showing MoE orchestration pipeline:
 * - Query → Selector → Experts (parallel) → Mixer → Output
 *
 * Features:
 * - Modern, clean, symmetrical layout
 * - Draggable nodes
 * - Animated edges during execution
 * - Hover tooltips for detailed info
 * - Auto-fit view
 */

'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  useEdgesState,
  useNodesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { MoETrace } from '@/lib/visualization/types';
import { MoEFlowBuilder } from '@/lib/visualization/builders/MoEFlowBuilder';
import { QueryNode } from '../nodes/QueryNode';
import { ExpertNode } from '../nodes/ExpertNode';
import { SelectorNode } from '../nodes/SelectorNode';
import { MixerNode } from '../nodes/MixerNode';
import { OutputNode } from '../nodes/OutputNode';
import { MergeDotNode } from '../nodes/MergeDotNode';

interface Props {
  trace: MoETrace;
}

export function MoEFlowVisualization({ trace }: Props) {
  // Register custom node types
  const nodeTypes = useMemo(
    () => ({
      query: QueryNode,
      expert: ExpertNode,
      mergeDot: MergeDotNode,
      selector: SelectorNode,
      mixer: MixerNode,
      output: OutputNode,
    }),
    []
  );

  // Build nodes and edges from trace
  const built = useMemo(() => {
    const builder = new MoEFlowBuilder();
    return {
      nodes: builder.buildNodes(trace),
      edges: builder.buildEdges(trace),
    };
  }, [trace]);

  // Stateful nodes/edges so users can drag nodes and edges re-route naturally.
  const [nodes, setNodes, onNodesChange] = useNodesState(built.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(built.edges);

  // Fit view on init and when the request changes (but don't fight user drags).
  const lastRequestIdRef = useRef<string | null>(null);
  const [shouldFit, setShouldFit] = useState(true);
  const reactFlowInstanceRef = useRef<any>(null);

  useEffect(() => {
    const req = trace.request_id || null;
    const isNewRequest = lastRequestIdRef.current !== req;
    if (lastRequestIdRef.current !== req) {
      lastRequestIdRef.current = req;
      setShouldFit(true);
    }

    // For a new request/trace, always start from the canonical symmetric layout.
    // This prevents stale dragged positions from older layout versions.
    if (isNewRequest) {
      setNodes(built.nodes);
    } else {
      // Merge new trace-driven data into existing node positions (preserves user drag layout).
      setNodes((prev) => {
        const prevById = new Map(prev.map((n) => [n.id, n]));
        return built.nodes.map((n) => {
          const existing = prevById.get(n.id);
          if (!existing) return n;

          // If layout logic changes, reflow to the new canonical positions.
          const existingLayout = (existing.data as any)?.layoutVersion;
          const nextLayout = (n.data as any)?.layoutVersion;
          if (existingLayout && nextLayout && existingLayout !== nextLayout) {
            return n;
          }

          return { ...n, position: existing.position };
        });
      });
    }
    setEdges(built.edges);
  }, [built.nodes, built.edges, setNodes, setEdges, trace.request_id]);

  // Ensure viewport is centered after nodes are set
  useEffect(() => {
    if (shouldFit && reactFlowInstanceRef.current && nodes.length > 0) {
      // Use requestAnimationFrame to ensure nodes are rendered before fitting
      requestAnimationFrame(() => {
        reactFlowInstanceRef.current?.fitView({ 
          padding: 0.2, 
          minZoom: 0.5, 
          maxZoom: 1.5,
          includeHiddenNodes: false,
          duration: 300,
        });
        setShouldFit(false);
      });
    }
  }, [shouldFit, nodes.length]);

  return (
    <div className="w-full h-full bg-gradient-to-br from-slate-100 via-gray-50 to-blue-50 relative overflow-hidden">
      {/* Subtle animated background pattern */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-0 left-0 w-96 h-96 bg-blue-200/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-purple-200/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onInit={(instance) => {
          // Store instance reference for later fitView calls
          reactFlowInstanceRef.current = instance;
          if (shouldFit && nodes.length > 0) {
            // Fit view with equal padding on all sides to ensure perfect centering
            requestAnimationFrame(() => {
              instance.fitView({ 
                padding: 0.2, 
                minZoom: 0.5, 
                maxZoom: 1.5,
                includeHiddenNodes: false,
                duration: 300,
              });
              setShouldFit(false);
            });
          }
        }}
        minZoom={0.3}
        maxZoom={2}
        // Default viewport - will be overridden by fitView on init
        // fitView will center the viewport perfectly based on node positions
        defaultViewport={{ x: 0, y: 0, zoom: 0.9 }}
        nodesDraggable={true}
        nodesConnectable={false}
        // We use click-to-pin tooltips for interaction, so ReactFlow selection outlines
        // just add visual noise (e.g., an extra box around "Final Response").
        elementsSelectable={false}
        // Allow panning the viewport with normal left-click dragging on empty canvas.
        // Previously this was limited to middle/right which made the graph feel "stuck".
        panOnDrag={[0, 1]}
        selectionOnDrag={false}
        zoomOnScroll={true}
        zoomOnPinch={true}
        zoomOnDoubleClick={false}
        className="relative z-10"
      >
        {/* Subtle dot grid background */}
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#94a3b8"
          className="opacity-30"
        />

        {/* Modern glass controls */}
        <Controls
          className="bg-white/80 backdrop-blur-xl border border-white/60 rounded-2xl shadow-[0_8px_32px_0_rgba(31,38,135,0.15)]"
          showInteractive={false}
        />

        {/* Modern glass minimap */}
        <MiniMap
          className="bg-white/80 backdrop-blur-xl border border-white/60 rounded-2xl shadow-[0_8px_32px_0_rgba(31,38,135,0.15)]"
          // Reduce footprint by ~30% (shrinks actual element size, not just visual scale)
          style={{ width: 98, height: 74 }}
          nodeColor={(node) => {
            // Unified subtle coloring
            switch (node.type) {
              case 'query':
                return '#3b82f6';
              case 'selector':
                return '#a855f7';
              case 'expert':
                const data = node.data as any;
                switch (data.status) {
                  case 'completed':
                    return '#10b981';
                  case 'failed':
                    return '#ef4444';
                  case 'executing':
                    return '#3b82f6';
                  default:
                    return '#9ca3af';
                }
              case 'mixer':
                return '#f97316';
              case 'output':
                return '#10b981';
              default:
                return '#9ca3af';
            }
          }}
          nodeBorderRadius={16}
          maskColor="rgba(148, 163, 184, 0.15)"
        />
      </ReactFlow>
    </div>
  );
}
