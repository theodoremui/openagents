"use client";

import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  NodeProps,
  Handle,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Brain,
  GitBranch,
  Route,
  Play,
  Merge,
  CheckCircle,
  XCircle,
  Clock,
  X,
  ChevronLeft,
  ChevronRight,
  Info,
  Maximize2,
  Minimize2,
} from "lucide-react";
import type { SmartRouterMetadata } from "@/lib/types";
import type { MoETrace } from "@/lib/visualization/types";
import type { SimulationStep } from "@/lib/types";
import { MoEFlowVisualization } from "@/components/visualization/orchestration/MoEFlowVisualization";
import { useSmartRouterPanel } from "@/lib/contexts/SmartRouterContext";
import { useResizableRightPanelWidth } from "@/lib/hooks/useResizableRightPanelWidth";

/**
 * SmartRouter Panel Component
 *
 * A collapsible right-side panel that displays SmartRouter orchestration flow
 * with interactive visualization using ReactFlow.
 *
 * Design Principles:
 * - Single Responsibility: Only displays SmartRouter visualization
 * - Separation of Concerns: Panel state managed by context, this component only renders
 * - Extensibility: Easy to add new node types and interactions
 * - Performance: Memoized calculations and callbacks
 */

interface NodeData {
  label: string;
  type?: string;
  phase?: string;
  details?: Record<string, unknown>;
  input?: string;
  output?: string;
}

// Custom node component with hover info showing input/output
function CustomNode({ data }: NodeProps<NodeData>) {
  const [showDetails, setShowDetails] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const nodeRef = useRef<HTMLDivElement>(null);

  // Helper to truncate text intelligently
  const truncateText = (text: string, maxLength: number = 150): string => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  // Calculate tooltip position when hovering
  const handleMouseEnter = () => {
    setShowDetails(true);
    if (nodeRef.current) {
      const rect = nodeRef.current.getBoundingClientRect();
      setTooltipPosition({
        x: rect.right + 16, // 16px (1rem) offset to the right
        y: rect.top,
      });
    }
  };

  const handleMouseLeave = () => {
    setShowDetails(false);
    setTooltipPosition(null);
  };

  return (
    <>
      <div
        ref={nodeRef}
        className="relative"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <Handle type="target" position={Position.Top} className="!bg-primary/50 !border-2 !border-primary !w-2 !h-2" />
        <div className="px-4 py-2 rounded-xl shadow-lg border-2 bg-gradient-to-br from-card to-card/80 backdrop-blur-sm hover:shadow-xl transition-all duration-200 hover:scale-[1.02]">
          <div className="text-sm font-semibold text-foreground whitespace-pre-line">
            {data.label}
          </div>
        </div>
        <Handle type="source" position={Position.Bottom} className="!bg-primary/50 !border-2 !border-primary !w-2 !h-2" />
      </div>

      {/* Hover details with input/output - FIXED: Use React Portal to render outside ReactFlow DOM tree */}
      {showDetails && tooltipPosition && (data.details || data.input || data.output) && typeof document !== 'undefined' ? 
        createPortal(
          <div
            className="fixed w-80 p-4 bg-popover/95 border-2 border-primary/30 rounded-xl shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-left-2 duration-200"
            style={{
              left: `${tooltipPosition.x}px`,
              top: `${tooltipPosition.y}px`,
              zIndex: 999999,
              pointerEvents: 'none',
            }}
          >
            <div className="text-sm font-bold mb-3 flex items-center gap-2 text-primary">
              <Info className="h-4 w-4" />
              {data.label.split("\n")[0]}
            </div>

            <div className="space-y-3 text-xs">
              {/* Input */}
              {data.input && (
                <div>
                  <div className="font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                    📥 Input:
                  </div>
                  <div className="bg-muted/50 p-2 rounded-lg font-mono text-foreground break-words">
                    {truncateText(String(data.input), 200)}
                  </div>
                </div>
              )}

              {/* Output */}
              {data.output && (
                <div>
                  <div className="font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                    📤 Output:
                  </div>
                  <div className="bg-muted/50 p-2 rounded-lg font-mono text-foreground break-words">
                    {truncateText(String(data.output), 200)}
                  </div>
                </div>
              )}

              {/* Additional Details */}
              {data.details && Object.keys(data.details).length > 0 && (
                <div>
                  <div className="font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                    ℹ️ Details:
                  </div>
                  <div className="space-y-1">
                    {Object.entries(data.details).map(([key, value]) => (
                      <div key={key} className="flex justify-between gap-2 bg-muted/30 p-1.5 rounded">
                        <span className="text-muted-foreground capitalize font-medium">
                          {key.replace(/_/g, " ")}:
                        </span>
                        <span className="font-mono text-foreground">
                          {typeof value === "object" ? truncateText(JSON.stringify(value), 50) : truncateText(String(value), 50)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>,
          document.body
        ) : null
      }
    </>
  );
}

const nodeTypes = {
  custom: CustomNode,
};

export function SmartRouterPanel() {
  const { isPanelOpen, metadata, moeTrace, executionTrace, panelKind, closePanel, expandPanel } = useSmartRouterPanel();
  const [selectedNode, setSelectedNode] = useState<Node<NodeData> | null>(null);
  const [isMaximized, setIsMaximized] = useState(false);

  const { widthVw, handleProps } = useResizableRightPanelWidth({
    storageKey: "openagents.ui.rightPanelWidthVw",
    defaultWidthVw: 30,
    minWidthVw: 22,
    maxWidthVw: 75,
    enabled: isPanelOpen && !isMaximized,
  });

  // Generate ReactFlow nodes and edges
  const { nodes, edges } = useMemo(() => {
    if (!metadata || panelKind !== 'smartrouter') {
      return { nodes: [], edges: [] };
    }

    const nodes: Node<NodeData>[] = [];
    const edges: Edge[] = [];
    let yPosition = 50;
    const ySpacing = 140;
    const xCenter = 250;  // Center X position for single nodes
    const xSpacing = 200;  // Horizontal spacing for concurrent agents

    // Helper to extract actual text content from trace data
    const extractOutput = (phase: any, defaultText: string): string => {
      if (!phase?.data) return defaultText;

      // For execution phase, we don't have the actual output in trace
      // So we'll show what we know
      if (phase.data.agents) {
        return `Executed ${phase.data.agents.join(", ")} agent(s) successfully`;
      }

      // For other phases, show structured data
      const data = phase.data;
      if (typeof data === 'string') return data;
      if (data.intent) {
        return `Complexity: ${data.intent.complexity}, Domains: ${data.intent.domains?.join(", ") || "N/A"}`;
      }
      if (data.agent) {
        return `Routed to ${data.agent} agent`;
      }
      if (data.passed !== undefined) {
        return data.passed ? "Quality check passed" : `Quality check failed: ${data.issues?.join(", ") || "Unknown issues"}`;
      }

      return JSON.stringify(data).substring(0, 150);
    };

    // Modern, clean color scheme
    const getNodeColor = (type: string): string => {
      const colors: Record<string, string> = {
        start: "#3b82f6",      // Blue - User Query
        agent: "#10b981",      // Green - Agent (most important!)
        interpretation: "#8b5cf6", // Purple - Interpretation
        routing: "#f59e0b",    // Amber - Routing decision
        result: "#22c55e",     // Bright green - Success
        fallback: "#ef4444",   // Red - Fallback
      };
      return colors[type] || "#64748b";
    };

    // Safety check for phases
    if (!metadata.phases || !Array.isArray(metadata.phases)) {
      nodes.push({
        id: "info",
        type: "custom",
        data: {
          label: "SmartRouter Active\n\nTrace data will appear\nwhen available",
          type: "info",
        },
        position: { x: 150, y: 100 },
        style: {
          background: getNodeColor("start"),
          border: "2px solid rgba(255,255,255,0.3)",
          borderRadius: "16px",
          padding: "16px",
          minWidth: "220px",
          fontSize: "14px",
        },
      });
      return { nodes, edges };
    }

    // Start node - User Query
    nodes.push({
      id: "start",
      type: "custom",
      data: {
        label: "📝 User Query",
        type: "start",
        output: metadata.query || "User input query",
      },
      position: { x: 150, y: yPosition },
      style: {
        background: getNodeColor("start"),
        border: "3px solid rgba(255,255,255,0.4)",
        borderRadius: "16px",
        padding: "14px 20px",
        fontSize: "15px",
        fontWeight: "600",
        color: "white",
      },
    });

    let lastNodeId = "start";
    yPosition += ySpacing;

    // Find interpretation data
    const interpretationPhase = metadata.phases.find((p: any) => p.phase === "interpretation");
    const routingPhase = metadata.phases.find((p: any) => p.phase === "routing");
    const executionPhase = metadata.phases.find((p: any) => p.phase === "execution");
    const evaluationPhase = metadata.phases.find((p: any) => p.phase === "evaluation");

    // Show interpretation (complexity)
    if (interpretationPhase?.data?.intent) {
      const intent = interpretationPhase.data.intent;
      const phaseId = "interpretation";

      nodes.push({
        id: phaseId,
        type: "custom",
        data: {
          label: `🧠 SmartRouter\n${intent.complexity} Query`,
          phase: "interpretation",
          input: metadata.query || "User query",
          output: extractOutput(interpretationPhase, `Complexity: ${intent.complexity}`),
          details: {
            complexity: intent.complexity,
            domains: intent.domains?.join(", ") || "N/A",
            requires_synthesis: intent.requires_synthesis ? "Yes" : "No",
            duration: interpretationPhase.duration ? `${interpretationPhase.duration.toFixed(2)}s` : "N/A",
          },
        },
        position: { x: 150, y: yPosition },
        style: {
          background: getNodeColor("interpretation"),
          border: "3px solid rgba(255,255,255,0.4)",
          borderRadius: "16px",
          padding: "14px 20px",
          fontSize: "14px",
          fontWeight: "600",
          color: "white",
          textAlign: "center",
        },
      });

      edges.push({
        id: `${lastNodeId}-${phaseId}`,
        source: lastNodeId,
        target: phaseId,
        type: 'straight',
        animated: true,
        style: { stroke: "#8b5cf6", strokeWidth: 2.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#8b5cf6" },
      });

      lastNodeId = phaseId;
      yPosition += ySpacing;
    }

    // ========================================================================
    // CONCURRENT EXECUTION VISUALIZATION
    // ========================================================================
    // The SmartRouter backend (asyncio.gather) executes multiple agents in parallel
    // when subqueries have no dependencies. We visualize this with:
    //
    // 1. HORIZONTAL LAYOUT: Agents positioned side-by-side (not vertically stacked)
    // 2. PARALLEL EDGES: Multiple edges flowing from routing node to agents simultaneously
    // 3. MERGE NODE: Visual convergence point after parallel execution
    // 4. TIMING BADGES: Show execution duration with "⚡ Parallel" indicator
    //
    // For sequential execution (single agent or dependent subqueries):
    // - VERTICAL LAYOUT: Standard top-to-bottom flow
    // - SINGLE PATH: One edge at a time
    // - TIMING BADGES: Show "🔄 Sequential" indicator
    // ========================================================================

    const agentNames = metadata.agents_used || [];
    const isConcurrent = executionPhase?.data?.concurrent || false;
    const agentExecutions = (executionPhase?.data?.agent_executions || []) as any[];

    if (agentNames.length > 0) {
      // Show routing decision first (which agent was selected)
      const routingData = routingPhase?.data as any;
      if (routingData?.agent || routingData?.agents_selected) {
        const routingId = "routing";
        const selectedAgents = agentNames.join(", ");
        const routingLabel = agentNames.length > 1
          ? `🎯 Selected Agents\n${agentNames.map(a => a.toUpperCase()).join(" + ")}`
          : `🎯 Selected Agent\n${selectedAgents.toUpperCase()}`;

        nodes.push({
          id: routingId,
          type: "custom",
          data: {
            label: routingLabel,
            phase: "routing",
            input: `Query complexity and domains analysis`,
            output: extractOutput(routingPhase, `Routing to ${selectedAgents} agent(s)`),
            details: {
              agents: selectedAgents,
              pattern: routingData?.pattern || "SIMPLE",
              domains: routingData?.domains?.join(", ") || "N/A",
              concurrent: isConcurrent ? "Yes" : "No",
              duration: routingPhase?.duration ? `${routingPhase.duration.toFixed(2)}s` : "N/A",
            },
          },
          position: { x: xCenter, y: yPosition },
          style: {
            background: getNodeColor("routing"),
            border: "3px solid rgba(255,255,255,0.4)",
            borderRadius: "16px",
            padding: "14px 20px",
            fontSize: "14px",
            fontWeight: "700",
            color: "white",
            textAlign: "center",
          },
        });

        edges.push({
          id: `${lastNodeId}-${routingId}`,
          source: lastNodeId,
          target: routingId,
          type: 'straight',
          animated: true,
          style: { stroke: "#f59e0b", strokeWidth: 2.5 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#f59e0b" },
        });

        lastNodeId = routingId;
        yPosition += ySpacing;
      }

      // Show agent(s) execution - HORIZONTAL LAYOUT FOR CONCURRENT EXECUTION
      // This is the key visual innovation: agents are positioned side-by-side when concurrent
      const agentNodeIds: string[] = [];

      if (isConcurrent && agentNames.length > 1) {
        // ====================================================================
        // **CONCURRENT EXECUTION**: Horizontal Layout Algorithm
        // ====================================================================
        // When multiple agents execute in parallel (via asyncio.gather),
        // we position them horizontally (side-by-side) on the same Y level.
        //
        // Algorithm:
        // 1. Calculate total width needed: (agent_count - 1) * xSpacing
        // 2. Calculate starting X: center - (totalWidth / 2)
        // 3. Position each agent at: startX + (index * xSpacing)
        // 4. All agents share same Y position (horizontal alignment)
        // 5. Add parallel edges from routing node to all agents
        //
        // Visual Result:
        //        Routing Node
        //       /      |      \
        //   Agent1  Agent2  Agent3  (all on same Y level)
        //       \      |      /
        //         Merge Node
        // ====================================================================
        const totalWidth = (agentNames.length - 1) * xSpacing;
        const startX = xCenter - totalWidth / 2;

        agentNames.forEach((agentName, index) => {
          const agentId = `agent-${index}`;
          agentNodeIds.push(agentId);
          const xPosition = startX + (index * xSpacing);

          // Find execution info for this specific agent
          const agentExecution = agentExecutions.find((ae: any) => ae.agent_id === agentName);
          // Use individual agent execution time from trace data
          const agentDuration = agentExecution?.execution_time
            ? agentExecution.execution_time.toFixed(2)
            : null;

          nodes.push({
            id: agentId,
            type: "custom",
            data: {
              label: `🤖 ${agentName.charAt(0).toUpperCase() + agentName.slice(1)}Agent\n⚡ Parallel${agentDuration ? ` (${agentDuration}s)` : ''}`,
              phase: "agent",
              input: metadata.query || "User query",
              output: extractOutput(executionPhase, `${agentName} agent executed successfully`),
              details: {
                agent: agentName,
                execution_mode: "CONCURRENT",
                success: agentExecution?.success ? "Yes" : "No",
                duration: agentDuration ? `${agentDuration}s (parallel)` : "N/A",
                total_execution_time: executionPhase?.duration ? `${executionPhase.duration.toFixed(2)}s` : "N/A",
              },
            },
            position: { x: xPosition, y: yPosition },
            style: {
              background: getNodeColor("agent"),
              border: "4px solid rgba(255,255,255,0.5)",
              borderRadius: "16px",
              padding: "18px 24px",
              fontSize: "15px",
              fontWeight: "700",
              color: "white",
              textAlign: "center",
              boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)",
            },
          });

          // Add edge from routing node to each agent (parallel edges)
          edges.push({
            id: `${lastNodeId}-${agentId}`,
            source: lastNodeId,
            target: agentId,
            type: 'straight',
            animated: true,
            style: { stroke: "#10b981", strokeWidth: 3 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981" },
          });
        });

        // Move to next row (all agents on same Y level)
        yPosition += ySpacing;
      } else {
        // **SEQUENTIAL EXECUTION**: Vertical layout (standard)
        agentNames.forEach((agentName, index) => {
          const agentId = `agent-${index}`;
          agentNodeIds.push(agentId);

          // Find execution info for this specific agent
          const agentExecution = agentExecutions.find((ae: any) => ae.agent_id === agentName);
          // Use individual agent execution time from trace data
          const agentDuration = agentExecution?.execution_time
            ? agentExecution.execution_time.toFixed(2)
            : null;

          nodes.push({
            id: agentId,
            type: "custom",
            data: {
              label: `🤖 ${agentName.charAt(0).toUpperCase() + agentName.slice(1)}Agent\n🔄 Sequential${agentDuration ? ` (${agentDuration}s)` : ''}`,
              phase: "agent",
              input: metadata.query || "User query",
              output: extractOutput(executionPhase, `${agentName} agent executed successfully`),
              details: {
                agent: agentName,
                execution_mode: "SEQUENTIAL",
                success: agentExecution?.success ? "Yes" : "No",
                duration: agentDuration ? `${agentDuration}s (sequential)` : "N/A",
              },
            },
            position: { x: xCenter, y: yPosition },
            style: {
              background: getNodeColor("agent"),
              border: "4px solid rgba(255,255,255,0.5)",
              borderRadius: "16px",
              padding: "18px 24px",
              fontSize: "16px",
              fontWeight: "700",
              color: "white",
              textAlign: "center",
              boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)",
            },
          });

          edges.push({
            id: `${lastNodeId}-${agentId}`,
            source: lastNodeId,
            target: agentId,
            type: 'straight',
            animated: true,
            style: { stroke: "#10b981", strokeWidth: 3 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981" },
          });

          lastNodeId = agentId;
          yPosition += ySpacing;
        });
      }

      // ====================================================================
      // MERGE NODE: Visual convergence point for concurrent execution
      // ====================================================================
      // After parallel agent execution, we create a merge node to show
      // where all responses come together before synthesis/evaluation.
      //
      // This provides clear visual feedback that:
      // 1. Multiple agents ran in parallel
      // 2. Their results are being combined
      // 3. Execution is moving to the next phase (synthesis/evaluation)
      //
      // The merge node:
      // - Receives edges from all agent nodes
      // - Positioned at center X (aligned with routing node)
      // - Uses distinct color (indigo) to differentiate from other phases
      // ====================================================================
      if (isConcurrent && agentNames.length > 1) {
        const mergeId = "merge";
        nodes.push({
          id: mergeId,
          type: "custom",
          data: {
            label: `🔗 Merge Results\n${agentNames.length} agents`,
            phase: "merge",
            input: `Results from ${agentNames.length} concurrent agents`,
            output: "All agent responses collected",
            details: {
              agent_count: agentNames.length.toString(),
              execution_mode: "CONCURRENT",
            },
          },
          position: { x: xCenter, y: yPosition },
          style: {
            background: "#6366f1",  // Indigo for merge node
            border: "3px solid rgba(255,255,255,0.4)",
            borderRadius: "16px",
            padding: "14px 20px",
            fontSize: "14px",
            fontWeight: "600",
            color: "white",
            textAlign: "center",
          },
        });

        // Add edges from all agent nodes to merge node
        agentNodeIds.forEach((agentId) => {
          edges.push({
            id: `${agentId}-${mergeId}`,
            source: agentId,
            target: mergeId,
            type: 'straight',
            animated: true,
            style: { stroke: "#6366f1", strokeWidth: 2.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1" },
          });
        });

        lastNodeId = mergeId;
        yPosition += ySpacing;
      }
    }

    // Add evaluation node if quality check was performed
    if (evaluationPhase) {
      const evalId = "evaluation";
      const evalData = evaluationPhase.data as any;
      const passed = evalData.passed !== false;
      const evalIcon = passed ? "✅" : "❌";
      const scores = evalData.scores;
      const threshold = evalData.threshold || 0.7;

      nodes.push({
        id: evalId,
        type: "custom",
        data: {
          label: `${evalIcon} Quality Evaluation`,
          phase: "evaluation",
          input: "Agent response for quality check",
          output: extractOutput(evaluationPhase, "Evaluation complete"),
          details: {
            passed: passed ? "Yes" : "No",
            completeness: scores?.completeness ? `${(scores.completeness * 100).toFixed(0)}%` : "N/A",
            accuracy: scores?.accuracy ? `${(scores.accuracy * 100).toFixed(0)}%` : "N/A",
            clarity: scores?.clarity ? `${(scores.clarity * 100).toFixed(0)}%` : "N/A",
            threshold: `${(threshold * 100).toFixed(0)}%`,
            issues: evalData.issues?.join(", ") || "None",
            duration: evaluationPhase.duration ? `${evaluationPhase.duration.toFixed(2)}s` : "N/A",
          },
        },
        position: { x: 150, y: yPosition },
        style: {
          background: passed ? "#22c55e" : "#ef4444",
          border: "3px solid rgba(255,255,255,0.4)",
          borderRadius: "16px",
          padding: "14px 20px",
          fontSize: "14px",
          fontWeight: "600",
          color: "white",
          textAlign: "center",
        },
      });

      edges.push({
        id: `${lastNodeId}-${evalId}`,
        source: lastNodeId,
        target: evalId,
        type: 'straight',
        animated: true,
        style: { stroke: passed ? "#22c55e" : "#ef4444", strokeWidth: 2.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: passed ? "#22c55e" : "#ef4444" },
      });

      lastNodeId = evalId;
      yPosition += ySpacing;
    }

    // Final result node
    const finalType = metadata.final_decision === "fallback" ? "fallback" : "result";
    const finalIcon = finalType === "fallback" ? "⚠️" : "✅";

    nodes.push({
      id: "final",
      type: "custom",
      data: {
        label: `${finalIcon} Answer ${finalType === "fallback" ? "Fallback" : "Delivered"}`,
        type: finalType,
        input: evaluationPhase ? "Evaluated response" : "Agent response",
        output: finalType === "fallback"
          ? "Fallback: I don't have enough information to answer this question accurately."
          : "Final answer returned to user",
        details: {
          decision: metadata.final_decision || "direct",
          total_time: metadata.total_time ? `${metadata.total_time.toFixed(2)}s` : "N/A",
        },
      },
      position: { x: 150, y: yPosition },
      style: {
        background: getNodeColor(finalType),
        border: "3px solid rgba(255,255,255,0.4)",
        borderRadius: "16px",
        padding: "14px 20px",
        fontSize: "15px",
        fontWeight: "600",
        color: "white",
      },
    });

    edges.push({
      id: `${lastNodeId}-final`,
      source: lastNodeId,
      target: "final",
      type: 'straight',
      animated: true,
      style: {
        stroke: finalType === "fallback" ? "#ef4444" : "#22c55e",
        strokeWidth: 2.5,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: finalType === "fallback" ? "#ef4444" : "#22c55e",
      },
    });

    return { nodes, edges };
  }, [metadata]);

  // Generic execution trace → ReactFlow nodes/edges
  const { execNodes, execEdges } = useMemo(() => {
    if (!executionTrace || panelKind !== "execution") {
      return { execNodes: [] as Node<NodeData>[], execEdges: [] as Edge[] };
    }

    const nodes: Node<NodeData>[] = [];
    const edges: Edge[] = [];
    const x = 150;
    let y = 60;
    const ySpacing = 140;

    nodes.push({
      id: "exec-start",
      type: "custom",
      data: {
        label: "📝 Request",
        type: "start",
        output: "User input submitted",
      },
      position: { x, y },
      style: {
        background: "#3b82f6",
        border: "3px solid rgba(255,255,255,0.4)",
        borderRadius: "16px",
        padding: "14px 20px",
        fontSize: "14px",
        fontWeight: "700",
        color: "white",
      },
    });

    let lastId = "exec-start";
    y += ySpacing;

    executionTrace.forEach((step: SimulationStep, idx: number) => {
      const id = `exec-step-${idx}`;
      const label = `🤖 ${step.agent_name || step.agent_id}\n${step.action}`;
      nodes.push({
        id,
        type: "custom",
        data: {
          label,
          type: "agent",
          input: step.action,
          output: step.output || "",
          details: {
            agent_id: step.agent_id,
            timestamp: step.timestamp || "",
          },
        },
        position: { x, y },
        style: {
          background: "#10b981",
          border: "3px solid rgba(255,255,255,0.4)",
          borderRadius: "16px",
          padding: "14px 20px",
          fontSize: "13px",
          fontWeight: "700",
          color: "white",
          textAlign: "center",
        },
      });

      edges.push({
        id: `${lastId}-${id}`,
        source: lastId,
        target: id,
        type: "straight",
        animated: true,
        style: { stroke: "#10b981", strokeWidth: 2.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981" },
      });

      lastId = id;
      y += ySpacing;
    });

    nodes.push({
      id: "exec-final",
      type: "custom",
      data: {
        label: "✅ Response Delivered",
        type: "result",
        output: "Final response rendered in chat",
      },
      position: { x, y },
      style: {
        background: "#22c55e",
        border: "3px solid rgba(255,255,255,0.4)",
        borderRadius: "16px",
        padding: "14px 20px",
        fontSize: "14px",
        fontWeight: "700",
        color: "white",
      },
    });

    edges.push({
      id: `${lastId}-exec-final`,
      source: lastId,
      target: "exec-final",
      type: "straight",
      animated: true,
      style: { stroke: "#22c55e", strokeWidth: 2.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" },
    });

    return { execNodes: nodes, execEdges: edges };
  }, [executionTrace, panelKind]);

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node<NodeData>) => {
    setSelectedNode(node);
  }, []);

  // Keyboard shortcuts (Escape key)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isPanelOpen) {
        if (isMaximized) {
          // First minimize, then close on second press
          setIsMaximized(false);
        } else {
          closePanel();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPanelOpen, isMaximized, closePanel]);

  // Only show expand button if metadata exists and panel is closed
  const showExpandButton = !isPanelOpen && (metadata || moeTrace || executionTrace);

  return (
    <>
      {/* Panel Container with smooth slide animation - ENHANCED: Responsive 30% width, custom cubic-bezier */}
      <div
        className={`
          fixed glass-panel bg-gradient-to-bl from-card/95 to-card/80 backdrop-blur-xl shadow-2xl flex flex-col
          ${isMaximized
            ? 'inset-0 w-full h-full z-50 border-0'
            : 'right-0 bottom-0 z-40 border-l border-border/50'
          }
          ${isPanelOpen ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        `}
        style={{
          top: isMaximized ? '0' : '6.5rem',
          width: isMaximized ? '100%' : `${widthVw}vw`,
          minWidth: isMaximized ? 'auto' : '384px',
          transition: 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.4s ease-out, width 0.3s ease-out'
        }}
      >
        {/* Resize handle (left edge) */}
        {!isMaximized && isPanelOpen && (
          <div
            data-testid="right-panel-resize-handle"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize right panel"
            className="absolute top-0 bottom-0 -left-2 w-4 z-50 cursor-col-resize group"
            {...handleProps}
            style={{ touchAction: "none" }}
          >
            {/* full-height edge line */}
            <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-[2px] bg-border/60 group-hover:bg-primary/50 transition-colors" />
            {/* Visible grip */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-5 h-16 rounded-full border border-border/70 bg-white/80 backdrop-blur-sm shadow-md group-hover:shadow-lg group-hover:border-primary/40 transition-all" />
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border/30 bg-gradient-to-r from-primary/10 to-transparent">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <Brain className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">
                {panelKind === "moe"
                  ? "MoE Flow"
                  : panelKind === "execution"
                    ? "Execution Flow"
                    : "SmartRouter Flow"}
              </h2>
              <p className="text-xs text-muted-foreground">
                {isMaximized ? 'Full Screen Visualization' : 'Orchestration Visualization'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Maximize/Minimize Button */}
            <Button
              variant="outline"
              size="icon"
              onClick={() => setIsMaximized(!isMaximized)}
              className="h-9 w-9 bg-primary/5 hover:bg-primary/15 border-primary/20 hover:border-primary/40 transition-all hover:scale-105"
              title={isMaximized ? "Minimize to sidebar (Escape)" : "Maximize to fullscreen"}
            >
              {isMaximized ? (
                <Minimize2 className="h-5 w-5 text-primary" />
              ) : (
                <Maximize2 className="h-5 w-5 text-primary" />
              )}
            </Button>

            {/* Close Button */}
            <Button
              variant="outline"
              size="icon"
              onClick={closePanel}
              className="h-9 w-9 bg-destructive/5 hover:bg-destructive/15 border-destructive/20 hover:border-destructive/40 text-destructive transition-all hover:scale-105"
              title="Close panel (Escape)"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

      {/* Stats Summary - Highlight Agents */}
      {panelKind === 'smartrouter' && metadata && (
        <div className="p-4 border-b border-border/30 bg-gradient-to-br from-emerald-500/10 to-transparent">
          {/* Agent(s) Used - Most Prominent */}
          <div className="mb-3 pb-3 border-b border-border/20">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Agents Used</span>
            <div className="flex flex-wrap gap-2 mt-2">
              {metadata.agents_used && metadata.agents_used.length > 0 ? (
                metadata.agents_used.map((agent: string, idx: number) => (
                  <Badge
                    key={idx}
                    className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold px-3 py-1 text-sm"
                  >
                    🤖 {agent}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No agents</span>
              )}
            </div>
          </div>

          {/* Quality Evaluation Scores - Prominent Display */}
          {(() => {
            const evaluationPhase = metadata.phases?.find((p: any) => p.phase === "evaluation");
            const evalData2 = evaluationPhase?.data as any;
            const scores = evalData2?.scores;
            const passed = evalData2?.passed;
            const threshold = evalData2?.threshold || 0.7;

            if (scores) {
              return (
                <div className="mb-3 pb-3 border-b border-border/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Quality Evaluation
                    </span>
                    <Badge variant={passed ? "default" : "destructive"} className="font-semibold">
                      {passed ? "✅ Passed" : "❌ Failed"}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    {/* Completeness Score */}
                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-muted-foreground">Completeness</span>
                        <span className={`text-xs font-bold ${scores.completeness >= threshold ? "text-green-600" : "text-red-600"}`}>
                          {(scores.completeness * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${scores.completeness >= threshold ? "bg-green-600" : "bg-red-600"}`}
                          style={{ width: `${scores.completeness * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Accuracy Score */}
                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-muted-foreground">Accuracy</span>
                        <span className={`text-xs font-bold ${scores.accuracy >= threshold ? "text-green-600" : "text-red-600"}`}>
                          {(scores.accuracy * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${scores.accuracy >= threshold ? "bg-green-600" : "bg-red-600"}`}
                          style={{ width: `${scores.accuracy * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Clarity Score */}
                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-muted-foreground">Clarity</span>
                        <span className={`text-xs font-bold ${scores.clarity >= threshold ? "text-green-600" : "text-red-600"}`}>
                          {(scores.clarity * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${scores.clarity >= threshold ? "bg-green-600" : "bg-red-600"}`}
                          style={{ width: `${scores.clarity * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Threshold indicator */}
                    <div className="text-xs text-muted-foreground mt-1">
                      Threshold: {(threshold * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              );
            }
            return null;
          })()}

          {/* Other Stats */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">Total Time</span>
              <span className="text-lg font-bold">
                {metadata.total_time ? `${metadata.total_time.toFixed(2)}s` : "N/A"}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">Decision</span>
              <Badge variant={metadata.final_decision === "fallback" ? "destructive" : "default"} className="w-fit">
                {metadata.final_decision || "direct"}
              </Badge>
            </div>
          </div>
        </div>
      )}

      {/* ReactFlow Visualization - FIXED: Ensure container doesn't create stacking context that limits tooltip z-index */}
      {panelKind === 'smartrouter' ? (
        <div className="flex-1 relative" style={{ isolation: 'auto' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={isMaximized ? 0.3 : 0.5}
            maxZoom={isMaximized ? 2.0 : 1.5}
            defaultEdgeOptions={{
              animated: true,
              type: 'straight',
              style: { strokeWidth: 2.5 },
            }}
            style={{ position: 'relative', zIndex: 1 }}
          >
            <Background gap={16} size={1} color="hsl(var(--muted-foreground) / 0.08)" />
            <Controls
              className="bg-card border border-border rounded-lg shadow-lg"
              showInteractive={false}
            />
            <MiniMap
              nodeColor={(node) => {
                if (node.id === selectedNode?.id) return "hsl(var(--primary))";
                return "hsl(var(--muted-foreground) / 0.3)";
              }}
              maskColor="hsl(var(--background) / 0.8)"
              className="bg-card border border-border rounded-lg shadow-lg"
              style={{
                width: 80,
                height: 60,
              }}
            />
          </ReactFlow>
        </div>
      ) : panelKind === 'moe' && moeTrace ? (
        <div className="flex-1 overflow-hidden" style={{ isolation: 'auto' }}>
          <MoEFlowVisualization trace={moeTrace} />
        </div>
      ) : panelKind === 'execution' && executionTrace ? (
        <div className="flex-1 relative" style={{ isolation: 'auto' }}>
          <ReactFlow
            nodes={execNodes}
            edges={execEdges}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={isMaximized ? 0.3 : 0.5}
            maxZoom={isMaximized ? 2.0 : 1.5}
            defaultEdgeOptions={{
              animated: true,
              type: 'straight',
              style: { strokeWidth: 2.5 },
            }}
            style={{ position: 'relative', zIndex: 1 }}
          >
            <Background gap={16} size={1} color="hsl(var(--muted-foreground) / 0.08)" />
            <Controls
              className="bg-card border border-border rounded-lg shadow-lg"
              showInteractive={false}
            />
            <MiniMap
              nodeColor={(node) => {
                if (node.id === selectedNode?.id) return "hsl(var(--primary))";
                return "hsl(var(--muted-foreground) / 0.3)";
              }}
              maskColor="hsl(var(--background) / 0.8)"
              className="bg-card border border-border rounded-lg shadow-lg"
              style={{ width: 80, height: 60 }}
            />
          </ReactFlow>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
          No orchestration trace yet.
        </div>
      )}

{/* Selected Node Details */}
      {panelKind === 'smartrouter' && selectedNode && selectedNode.data.details && (
        <div className="p-4 border-t border-border/30 bg-muted/20">
          <div className="text-sm font-semibold mb-2">Selected: {selectedNode.data.label.split("\n")[0]}</div>
          <div className="space-y-1 text-xs">
            {Object.entries(selectedNode.data.details).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-2">
                <span className="text-muted-foreground capitalize">
                  {key.replace(/_/g, " ")}:
                </span>
                <span className="font-mono text-foreground text-right">
                  {typeof value === "object" ? JSON.stringify(value).slice(0, 50) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Help Text */}
      {panelKind === 'smartrouter' && (!metadata?.phases || metadata.phases.length === 0) && (
        <div className="p-4 border-t border-border/30 bg-muted/20">
          <p className="text-xs text-muted-foreground text-center">
            Trace visualization will appear when SmartRouter processes a query with trace data enabled.
          </p>
        </div>
      )}
      </div>

      {/* Floating Round Collapse Button - smoothly fades in when panel is open (but not maximized) */}
      <div
        className={`
          fixed right-4 top-1/2 -translate-y-1/2 z-50
          transition-all duration-300 ease-in-out
          ${isPanelOpen && !isMaximized ? 'opacity-100 scale-100' : 'opacity-0 scale-0 pointer-events-none'}
        `}
      >
        <Button
          variant="default"
          size="icon"
          onClick={closePanel}
          className="h-12 w-12 rounded-full shadow-xl glass-panel backdrop-blur-xl bg-primary/90 hover:bg-primary border border-primary-foreground/20 transition-all hover:scale-110"
          title="Collapse SmartRouter panel (Escape)"
        >
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>

      {/* Floating Circular Expand Button - matches left sidebar style with smooth slide animation */}
      {showExpandButton && (
        <div
          className={`
            fixed right-4 top-1/2 -translate-y-1/2 z-50
            transition-all duration-500 ease-out
            ${showExpandButton ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-12 pointer-events-none'}
          `}
        >
          <Button
            variant="default"
            size="icon"
            onClick={expandPanel}
            className="h-12 w-12 rounded-full shadow-2xl glass-panel backdrop-blur-xl bg-primary/90 hover:bg-primary border-2 border-primary-foreground/20 transition-all duration-300 hover:scale-110 hover:shadow-[0_0_30px_rgba(var(--primary),0.5)] group"
            title="Open SmartRouter panel"
          >
            <ChevronLeft className="h-6 w-6 text-primary-foreground group-hover:scale-110 transition-transform" />
          </Button>
        </div>
      )}
    </>
  );
}
