/**
 * MoE Flow Builder
 *
 * Transforms MoE trace data into ReactFlow nodes and edges for visualization.
 *
 * Design:
 * - Modern, clean, symmetrical layout
 * - 5 node types: Query, Selector, Expert (parallel), Mixer, Output
 * - Vertical flow from top to bottom
 * - Experts arranged horizontally in parallel
 */

import { Node, Edge, MarkerType } from '@xyflow/react';
import { MoETrace, ExpertExecutionDetail } from '../types';

export interface QueryNodeData {
  label: string;
  query: string;
  status: 'completed';
  output?: string;
}

export interface SelectorNodeData {
  label: string;
  selectedCount: number;
  latencyMs: number;
  status: 'completed';
  input?: string;
  selectedExperts?: string[];
}

export interface ExpertNodeData {
  label: string;
  expertId: string;
  confidence: number;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  latencyMs?: number;
  toolsUsed?: string[];
  error?: string;
  response?: string;
  input?: string;
}

export interface MixerNodeData {
  label: string;
  expertCount: number;
  latencyMs: number;
  status: 'completed';
  inputSummary?: string;
  output?: string;
}

export interface OutputNodeData {
  label: string;
  response?: string;
  totalLatencyMs: number;
  status: 'completed';
  cacheHit: boolean;
  fallback: boolean;
  inputSummary?: string;
}

export class MoEFlowBuilder {
  // IMPORTANT: ReactFlow positions are TOP-LEFT of the node.
  // To keep the flow visually symmetric, we use fixed node widths and compute x positions
  // so that node centers align on a single vertical axis.
  // Bump this when layout logic changes to force a clean reflow in the UI.
  private static readonly LAYOUT_VERSION = 'moe-flow-layout-v5';
  private static readonly CENTER_X = 400;
  private static readonly MAIN_NODE_W = 360;
  private static readonly EXPERT_NODE_W = 220;
  private static readonly EXPERT_GAP = 60;
  // Vertical layout - 30% increase in spacing for less crowded appearance
  // Base spacing increased: 140→182, 140→182, 180→234, 160→208
  private static readonly Y_QUERY = 60;
  private static readonly Y_SELECTOR = 242;    // Was 200 (+42, 30% of 140)
  private static readonly Y_EXPERTS = 424;     // Was 340 (+84, 30% cumulative)
  private static readonly Y_MIXER = 658;       // Was 520 (+138, 30% cumulative)
  private static readonly Y_OUTPUT = 866;      // Was 680 (+186, 30% cumulative)

  private static centerTopLeftX(nodeWidth: number): number {
    return MoEFlowBuilder.CENTER_X - nodeWidth / 2;
  }

  /**
   * Build ReactFlow nodes from MoE trace.
   *
   * Layout:
   * - Query (top center)
   * - Selector (below query)
   * - Experts (horizontal row, centered)
   * - Mixer (below experts)
   * - Output (bottom center)
   */
  buildNodes(trace: MoETrace): Node[] {
    const nodes: Node[] = [];
    const centerX = MoEFlowBuilder.CENTER_X; // Center axis of canvas

    // 1. Query node (top)
    nodes.push({
      id: 'query',
      type: 'query',
      position: { x: MoEFlowBuilder.centerTopLeftX(MoEFlowBuilder.MAIN_NODE_W), y: MoEFlowBuilder.Y_QUERY },
      data: {
        layoutVersion: MoEFlowBuilder.LAYOUT_VERSION,
        label: 'User Query',
        query: trace.query,
        status: 'completed',
        output: trace.query,
      } as unknown as Record<string, unknown>,
      draggable: true,
    });

    // 2. Selector node
    const selectionLatency = trace.selection_end && trace.selection_start
      ? (trace.selection_end - trace.selection_start) * 1000
      : 0;

    nodes.push({
      id: 'selector',
      type: 'selector',
      position: { x: MoEFlowBuilder.centerTopLeftX(MoEFlowBuilder.MAIN_NODE_W), y: MoEFlowBuilder.Y_SELECTOR },
      data: {
        layoutVersion: MoEFlowBuilder.LAYOUT_VERSION,
        label: 'Expert Selection',
        selectedCount: trace.selected_experts?.length || 0,
        latencyMs: selectionLatency,
        status: 'completed',
        input: trace.query,
        selectedExperts: trace.selected_experts || [],
      } as unknown as Record<string, unknown>,
      draggable: true,
    });

    // 3. Expert nodes (parallel layout)
    // Center the expert row perfectly on the center axis
    const experts = trace.expert_details || [];
    const expertW = MoEFlowBuilder.EXPERT_NODE_W;
    const expertGap = MoEFlowBuilder.EXPERT_GAP;
    
    // Calculate total width of the expert row (all nodes + gaps between them)
    const totalRowW = experts.length * expertW + Math.max(0, experts.length - 1) * expertGap;
    
    // Calculate start position so the row is perfectly centered
    // startX positions the left edge of the first node
    const startX = centerX - totalRowW / 2;
    
    // Spacing between expert nodes (node width + gap)
    const expertSpacing = expertW + expertGap;
    
    // Verify: For each expert, its center should align with centerX when evenly spaced
    // Expert center = startX + index * (expertW + expertGap) + expertW/2
    // For a row with N experts, the center of the row is at centerX

    experts.forEach((expert, index) => {
      nodes.push({
        id: `expert-${expert.expert_id}`,
        type: 'expert',
        position: { x: startX + index * expertSpacing, y: MoEFlowBuilder.Y_EXPERTS },
        data: {
          layoutVersion: MoEFlowBuilder.LAYOUT_VERSION,
          label: expert.agent_name,
          expertId: expert.expert_id,
          confidence: expert.confidence,
          status: expert.status,
          // Normalize nulls from backend traces to undefined so UI guards work reliably.
          latencyMs: expert.latency_ms ?? undefined,
          toolsUsed: expert.tools_used,
          error: expert.error,
          response: expert.response,
          input: trace.query,
        } as unknown as Record<string, unknown>,
        draggable: true,
      });
    });

    // 4. Mixer node
    const mixingLatency = trace.mixing_end && trace.mixing_start
      ? (trace.mixing_end - trace.mixing_start) * 1000
      : 0;

    nodes.push({
      id: 'mixer',
      type: 'mixer',
      position: { x: MoEFlowBuilder.centerTopLeftX(MoEFlowBuilder.MAIN_NODE_W), y: MoEFlowBuilder.Y_MIXER },
      data: {
        layoutVersion: MoEFlowBuilder.LAYOUT_VERSION,
        label: 'Result Mixing',
        expertCount: experts.length,
        latencyMs: mixingLatency,
        status: 'completed',
        inputSummary: `${experts.length} expert result(s)`,
        output: trace.final_response,
      } as unknown as Record<string, unknown>,
      draggable: true,
    });

    // 5. Output node (bottom)
    nodes.push({
      id: 'output',
      type: 'output',
      position: { x: MoEFlowBuilder.centerTopLeftX(MoEFlowBuilder.MAIN_NODE_W), y: MoEFlowBuilder.Y_OUTPUT },
      // ReactFlow adds default node wrapper styles (background/border) that can show up
      // as a "mystery rectangle" behind our rounded glass card. Make the wrapper
      // transparent so only the card UI is visible.
      style: { background: 'transparent', border: 'none', boxShadow: 'none' },
      data: {
        layoutVersion: MoEFlowBuilder.LAYOUT_VERSION,
        label: 'Final Response',
        response: trace.final_response,
        totalLatencyMs: trace.latency_ms,
        status: 'completed',
        cacheHit: trace.cache_hit,
        fallback: trace.fallback,
        inputSummary: `${experts.length} expert result(s) → mixed response`,
      } as unknown as Record<string, unknown>,
      draggable: true,
    });

    return nodes;
  }

  /**
   * Build ReactFlow edges from MoE trace.
   *
   * Edges show data flow:
   * - Query → Selector
   * - Selector → Each Expert
   * - Each Completed Expert → Mixer
   * - Mixer → Output
   *
   * Modern styling: Subtle colors with smooth gradients
   */
  buildEdges(trace: MoETrace): Edge[] {
    const edges: Edge[] = [];
    const baseStroke = '#64748b'; // slate-500, visible but subtle
    // Simplest, cleanest rendering: straight edges + good arrowheads.
    // This matches SmartRouter's graph style and avoids odd orthogonal "elbows" when nodes align.
    const edgeType: Edge["type"] = 'straight';
    const baseMarker = {
      type: MarkerType.ArrowClosed as const,
      color: baseStroke,
      width: 16,
      height: 16,
    };
    // Routing is handled by the custom edge; keep edges visually consistent.

    // Query → Selector (subtle gradient edge)
    edges.push({
      id: 'e-query-selector',
      source: 'query',
      target: 'selector',
      animated: false,
      style: {
        stroke: baseStroke,
        strokeWidth: 2.2,
        strokeLinecap: 'round',
        strokeLinejoin: 'round',
        opacity: 0.85,
      },
      type: edgeType,
      markerEnd: baseMarker,
    });

    // Selector → Experts
    const experts = trace.expert_details || [];
    experts.forEach((expert) => {
      const stroke = this.getEdgeColor(expert.status);
      edges.push({
        id: `e-selector-${expert.expert_id}`,
        source: 'selector',
        target: `expert-${expert.expert_id}`,
        animated: expert.status === 'executing',
        style: {
          stroke,
          strokeWidth: 2.2,
          strokeLinecap: 'round',
          strokeLinejoin: 'round',
          opacity: 0.8,
        },
        type: edgeType,
        markerEnd: {
          type: MarkerType.ArrowClosed as const,
          color: stroke,
          width: 16,
          height: 16,
        },
      });
    });

    // Experts → Mixer (fan-in convergence with visual depth)
    // Modern styling: All edges have arrows, but with layered opacity for depth perception.
    // Primary (first completed) has full opacity, others fade progressively for clean hierarchy.
    const primaryIdx = experts.findIndex((e) => e.status === 'completed');
    const chosenPrimaryIdx = primaryIdx >= 0 ? primaryIdx : 0;

    experts.forEach((expert, idx) => {
      const stroke = this.getEdgeColor(expert.status);
      const isPrimary = idx === chosenPrimaryIdx;

      // Create visual hierarchy: primary edge is prominent, others fade for depth
      const edgeOpacity = isPrimary ? 0.75 : 0.45 - (idx * 0.05);
      const arrowOpacity = isPrimary ? 1.0 : 0.6;

      edges.push({
        id: `e-expert-${expert.expert_id}-mixer`,
        source: `expert-${expert.expert_id}`,
        target: 'mixer',
        animated: false,
        style: {
          stroke,
          strokeWidth: isPrimary ? 2.4 : 2.0,
          strokeLinecap: 'round',
          strokeLinejoin: 'round',
          opacity: edgeOpacity,
        },
        type: edgeType,
        markerEnd: {
          type: MarkerType.ArrowClosed as const,
          color: stroke,
          width: isPrimary ? 18 : 14,
          height: isPrimary ? 18 : 14,
        },
        zIndex: isPrimary ? 10 : 5 - idx, // Layer primary edge on top
      });
    });

    // Mixer → Output (explicitly use centered handles for perfect alignment)
    edges.push({
      id: 'e-mixer-output',
      source: 'mixer',
      target: 'output',
      sourceHandle: 'out',  // Explicitly use MixerNode's bottom handle (id="out")
      targetHandle: 'in',    // Explicitly use OutputNode's top handle (id="in", centered)
      animated: false,
      style: {
        stroke: baseStroke,
        strokeWidth: 2.2,
        strokeLinecap: 'round',
        strokeLinejoin: 'round',
        opacity: 0.85,
      },
      type: edgeType,
      markerEnd: baseMarker,
    });

    return edges;
  }

  /**
   * Get edge color based on expert status.
   * Using softer, more subtle colors that match the glass theme.
   */
  private getEdgeColor(status: string): string {
    switch (status) {
      case 'completed':
        return '#10b981'; // Emerald green
      case 'failed':
        return '#ef4444'; // Soft red
      case 'executing':
        return '#3b82f6'; // Sky blue
      case 'pending':
        return '#cbd5e1'; // Light slate
      default:
        return '#cbd5e1';
    }
  }
}
