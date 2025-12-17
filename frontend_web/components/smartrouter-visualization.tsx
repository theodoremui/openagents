"use client";

import { useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import type {
  SmartRouterMetadata,
  SmartRouterTrace,
  SmartRouterSubquery,
} from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Brain,
  GitBranch,
  Route,
  Play,
  Merge,
  CheckCircle,
  XCircle,
  Clock
} from "lucide-react";

interface SmartRouterVisualizationProps {
  metadata: SmartRouterMetadata;
}

/**
 * SmartRouter Visualization Component
 *
 * Displays the SmartRouter orchestration flow as an interactive graph.
 * Shows all phases: interpretation, decomposition, routing, execution, synthesis, evaluation.
 *
 * Design Principles:
 * - Single Responsibility: Only visualizes SmartRouter traces
 * - Dependency Injection: Receives metadata via props
 * - Type Safety: Uses TypeScript types
 */
export function SmartRouterVisualization({ metadata }: SmartRouterVisualizationProps) {
  // Generate ReactFlow nodes and edges from SmartRouter metadata
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    let yPosition = 0;
    const ySpacing = 150;
    const xSpacing = 250;

    // Safety check: if phases is not available, return empty graph
    if (!metadata.phases || !Array.isArray(metadata.phases)) {
      // Return minimal graph showing SmartRouter was used but no trace data
      nodes.push({
        id: "smartrouter",
        type: "default",
        data: { label: "SmartRouter\n(Trace data not available)" },
        position: { x: 400, y: 100 },
        style: {
          background: "#6366f1",
          color: "#fff",
          border: "1px solid #555",
          borderRadius: "8px",
          padding: "20px",
          minWidth: "250px",
          textAlign: "center",
        },
      });
      return { nodes, edges };
    }

    // Helper to create node
    const createNode = (
      id: string,
      label: string,
      type: string,
      data: Record<string, unknown> = {},
      x = 400,
      y = yPosition
    ): Node => {
      yPosition += ySpacing;
      return {
        id,
        type: "default",
        data: { label, ...data },
        position: { x, y },
        style: {
          background: getNodeColor(type),
          color: "#fff",
          border: "1px solid #555",
          borderRadius: "8px",
          padding: "10px",
          minWidth: "180px",
        },
      };
    };

    // Helper to get node color by phase
    const getNodeColor = (type: string): string => {
      const colors: Record<string, string> = {
        start: "#6366f1",
        interpretation: "#8b5cf6",
        decomposition: "#a855f7",
        routing: "#c026d3",
        execution: "#d946ef",
        synthesis: "#ec4899",
        evaluation: "#f43f5e",
        result: "#22c55e",
        fallback: "#ef4444",
      };
      return colors[type] || "#64748b";
    };

    // 1. Start node
    nodes.push(createNode("start", "User Query", "start"));
    let lastNodeId = "start";

    // 2. Process each phase
    metadata.phases.forEach((trace, index) => {
      const phaseId = `phase-${index}-${trace.phase}`;

      switch (trace.phase) {
        case "interpretation":
          if (trace.data.intent) {
            const intent = trace.data.intent;
            nodes.push(
              createNode(
                phaseId,
                `Interpretation\n${intent.complexity}`,
                "interpretation",
                {
                  domains: intent.domains.join(", "),
                  reasoning: intent.reasoning
                }
              )
            );
            edges.push({
              id: `${lastNodeId}-${phaseId}`,
              source: lastNodeId,
              target: phaseId,
              animated: true,
              label: "Interpret",
            });
            lastNodeId = phaseId;
          }
          break;

        case "decomposition":
          if (trace.data.subqueries && trace.data.subqueries.length > 0) {
            const decompNode = createNode(
              phaseId,
              `Decomposition\n${trace.data.subqueries.length} subqueries`,
              "decomposition"
            );
            nodes.push(decompNode);
            edges.push({
              id: `${lastNodeId}-${phaseId}`,
              source: lastNodeId,
              target: phaseId,
              animated: true,
              label: "Decompose",
            });

            // Add subquery nodes
            trace.data.subqueries.forEach((sq, sqIndex) => {
              const sqId = `subquery-${sq.id}`;
              nodes.push({
                id: sqId,
                type: "default",
                data: {
                  label: `${sq.id}\n${sq.capability_required}`,
                  text: sq.text,
                },
                position: {
                  x: 200 + sqIndex * xSpacing,
                  y: yPosition,
                },
                style: {
                  background: "#3b82f6",
                  color: "#fff",
                  border: "1px solid #555",
                  borderRadius: "8px",
                  padding: "10px",
                  minWidth: "150px",
                  fontSize: "12px",
                },
              });
              edges.push({
                id: `${phaseId}-${sqId}`,
                source: phaseId,
                target: sqId,
                animated: true,
              });
            });

            yPosition += ySpacing;
            lastNodeId = phaseId;
          }
          break;

        case "routing":
          if (trace.data.subqueries) {
            const routingNode = createNode(
              phaseId,
              "Capability Routing",
              "routing"
            );
            nodes.push(routingNode);
            edges.push({
              id: `${lastNodeId}-${phaseId}`,
              source: lastNodeId,
              target: phaseId,
              animated: true,
              label: "Route",
            });
            lastNodeId = phaseId;
          }
          break;

        case "execution":
          if (trace.data.responses && trace.data.responses.length > 0) {
            const execNode = createNode(
              phaseId,
              `Execution\n${trace.data.responses.length} agents`,
              "execution"
            );
            nodes.push(execNode);
            edges.push({
              id: `${lastNodeId}-${phaseId}`,
              source: lastNodeId,
              target: phaseId,
              animated: true,
              label: "Execute",
            });

            // Add agent response nodes
            trace.data.responses.forEach((resp, respIndex) => {
              const agentNodeId = `agent-${resp.agent_id}-${respIndex}`;
              nodes.push({
                id: agentNodeId,
                type: "default",
                data: {
                  label: `${resp.agent_name || resp.agent_id}\n${resp.success ? "✓" : "✗"}`,
                  success: resp.success,
                  error: resp.error,
                },
                position: {
                  x: 200 + respIndex * xSpacing,
                  y: yPosition,
                },
                style: {
                  background: resp.success ? "#22c55e" : "#ef4444",
                  color: "#fff",
                  border: "1px solid #555",
                  borderRadius: "8px",
                  padding: "10px",
                  minWidth: "150px",
                  fontSize: "12px",
                },
              });
              edges.push({
                id: `${phaseId}-${agentNodeId}`,
                source: phaseId,
                target: agentNodeId,
                animated: true,
                markerEnd: {
                  type: MarkerType.ArrowClosed,
                },
              });
            });

            yPosition += ySpacing;
            lastNodeId = phaseId;
          }
          break;

        case "synthesis":
          if (trace.data.synthesis) {
            const synth = trace.data.synthesis;
            nodes.push(
              createNode(
                phaseId,
                `Synthesis\nConfidence: ${(synth.confidence * 100).toFixed(0)}%`,
                "synthesis",
                { sources: synth.sources.join(", ") }
              )
            );
            edges.push({
              id: `${lastNodeId}-${phaseId}`,
              source: lastNodeId,
              target: phaseId,
              animated: true,
              label: "Synthesize",
            });
            lastNodeId = phaseId;
          }
          break;

        case "evaluation":
          if (trace.data.evaluation) {
            const evaluation = trace.data.evaluation;
            nodes.push(
              createNode(
                phaseId,
                `Evaluation\n${evaluation.is_high_quality ? "High Quality" : "Low Quality"}`,
                "evaluation",
                {
                  completeness: evaluation.completeness_score,
                  accuracy: evaluation.accuracy_score,
                  clarity: evaluation.clarity_score,
                }
              )
            );
            edges.push({
              id: `${lastNodeId}-${phaseId}`,
              source: lastNodeId,
              target: phaseId,
              animated: true,
              label: "Evaluate",
            });
            lastNodeId = phaseId;
          }
          break;
      }
    });

    // Final result node
    const finalNodeId = metadata.final_decision === "fallback" ? "fallback" : "result";
    const finalLabel = metadata.final_decision === "fallback"
      ? "Fallback\n(Insufficient quality)"
      : "Answer Returned";
    nodes.push(
      createNode(
        finalNodeId,
        finalLabel,
        metadata.final_decision === "fallback" ? "fallback" : "result"
      )
    );
    edges.push({
      id: `${lastNodeId}-${finalNodeId}`,
      source: lastNodeId,
      target: finalNodeId,
      animated: true,
      label: metadata.final_decision === "fallback" ? "Fallback" : "Return",
      style: {
        stroke: metadata.final_decision === "fallback" ? "#ef4444" : "#22c55e",
      },
    });

    return { nodes, edges };
  }, [metadata]);

  return (
    <Card className="w-full h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          SmartRouter Orchestration Flow
        </CardTitle>
        <CardDescription>
          Interactive visualization of multi-agent routing and synthesis
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Phases</span>
            <span className="text-2xl font-bold">{metadata.phases?.length || 0}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Total Time</span>
            <span className="text-2xl font-bold">
              {metadata.total_time ? `${metadata.total_time.toFixed(2)}s` : "N/A"}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Decision</span>
            <Badge variant={metadata.final_decision === "fallback" ? "destructive" : "default"}>
              {metadata.final_decision === "fallback" ? "Fallback" : "Answer"}
            </Badge>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Orchestrator</span>
            <Badge variant="outline">SmartRouter</Badge>
          </div>
        </div>

        {/* ReactFlow Graph */}
        <div className="h-[600px] border rounded-md bg-muted/20">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            attributionPosition="bottom-right"
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>

        {/* Phase Details */}
        {metadata.phases && metadata.phases.length > 0 && (
          <div className="mt-4 space-y-2">
            <h3 className="text-sm font-semibold">Phase Details</h3>
            <div className="space-y-2">
              {metadata.phases.map((phase, index) => (
                <PhaseDetail key={index} phase={phase} index={index} />
              ))}
            </div>
          </div>
        )}

        {/* Message when trace data is not available */}
        {(!metadata.phases || metadata.phases.length === 0) && (
          <div className="mt-4 p-4 border rounded-md bg-muted/30 text-center">
            <p className="text-sm text-muted-foreground">
              <strong>Note:</strong> Detailed trace visualization is not available yet.
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              SmartRouter executed successfully, but trace data capture is pending implementation.
              See <code className="px-1 py-0.5 bg-muted rounded text-xs">docs/SMARTROUTER_FRONTEND_INTEGRATION.md</code> for details.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Phase Detail Component
 *
 * Shows detailed information for a specific SmartRouter phase.
 */
function PhaseDetail({ phase, index }: { phase: SmartRouterTrace; index: number }) {
  const getPhaseIcon = (phaseName: string) => {
    const icons: Record<string, React.ReactNode> = {
      interpretation: <Brain className="h-4 w-4" />,
      decomposition: <GitBranch className="h-4 w-4" />,
      routing: <Route className="h-4 w-4" />,
      execution: <Play className="h-4 w-4" />,
      synthesis: <Merge className="h-4 w-4" />,
      evaluation: <CheckCircle className="h-4 w-4" />,
    };
    return icons[phaseName] || <Clock className="h-4 w-4" />;
  };

  return (
    <details className="border rounded-md p-3 bg-card">
      <summary className="cursor-pointer flex items-center gap-2 font-medium">
        {getPhaseIcon(phase.phase)}
        <span className="capitalize">{phase.phase}</span>
        <Badge variant="outline" className="ml-auto text-xs">
          {new Date(phase.timestamp).toLocaleTimeString()}
        </Badge>
      </summary>
      <div className="mt-3 pl-6 space-y-2 text-sm">
        {phase.data.intent && (
          <div>
            <span className="font-semibold">Intent:</span>
            <div className="ml-2">
              <div>Complexity: <Badge>{phase.data.intent.complexity}</Badge></div>
              <div>Domains: {phase.data.intent.domains.join(", ")}</div>
              {phase.data.intent.reasoning && (
                <div className="text-muted-foreground text-xs mt-1">
                  {phase.data.intent.reasoning}
                </div>
              )}
            </div>
          </div>
        )}

        {phase.data.subqueries && (
          <div>
            <span className="font-semibold">Subqueries ({phase.data.subqueries.length}):</span>
            <ul className="ml-2 space-y-1">
              {phase.data.subqueries.map((sq) => (
                <li key={sq.id} className="text-xs">
                  <strong>{sq.id}:</strong> {sq.text}
                  <Badge variant="secondary" className="ml-2 text-xs">
                    {sq.capability_required}
                  </Badge>
                  {sq.agent_id && (
                    <Badge variant="outline" className="ml-1 text-xs">
                      → {sq.agent_id}
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {phase.data.responses && (
          <div>
            <span className="font-semibold">Agent Responses ({phase.data.responses.length}):</span>
            <ul className="ml-2 space-y-1">
              {phase.data.responses.map((resp, idx) => (
                <li key={idx} className="text-xs flex items-center gap-2">
                  {resp.success ? (
                    <CheckCircle className="h-3 w-3 text-green-500" />
                  ) : (
                    <XCircle className="h-3 w-3 text-red-500" />
                  )}
                  <strong>{resp.agent_name || resp.agent_id}:</strong>
                  {resp.success ? (
                    <span className="text-muted-foreground">
                      {resp.content.substring(0, 80)}...
                    </span>
                  ) : (
                    <span className="text-red-500">{resp.error}</span>
                  )}
                  {resp.execution_time && (
                    <Badge variant="outline" className="ml-auto text-xs">
                      {resp.execution_time.toFixed(2)}s
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {phase.data.synthesis && (
          <div>
            <span className="font-semibold">Synthesis:</span>
            <div className="ml-2">
              <div>
                Confidence: <Badge>{(phase.data.synthesis.confidence * 100).toFixed(0)}%</Badge>
              </div>
              <div>Sources: {phase.data.synthesis.sources.join(", ")}</div>
              {phase.data.synthesis.conflicts_resolved && phase.data.synthesis.conflicts_resolved.length > 0 && (
                <div className="text-xs text-muted-foreground mt-1">
                  Conflicts resolved: {phase.data.synthesis.conflicts_resolved.length}
                </div>
              )}
            </div>
          </div>
        )}

        {phase.data.evaluation && (
          <div>
            <span className="font-semibold">Evaluation:</span>
            <div className="ml-2 space-y-1">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  Completeness:
                  <Badge variant="outline" className="ml-1">
                    {(phase.data.evaluation.completeness_score * 100).toFixed(0)}%
                  </Badge>
                </div>
                <div>
                  Accuracy:
                  <Badge variant="outline" className="ml-1">
                    {(phase.data.evaluation.accuracy_score * 100).toFixed(0)}%
                  </Badge>
                </div>
                <div>
                  Clarity:
                  <Badge variant="outline" className="ml-1">
                    {(phase.data.evaluation.clarity_score * 100).toFixed(0)}%
                  </Badge>
                </div>
              </div>
              <div>
                Quality: {" "}
                <Badge variant={phase.data.evaluation.is_high_quality ? "default" : "destructive"}>
                  {phase.data.evaluation.is_high_quality ? "High" : "Low"}
                </Badge>
              </div>
              {phase.data.evaluation.issues && phase.data.evaluation.issues.length > 0 && (
                <div className="text-xs text-muted-foreground">
                  Issues: {phase.data.evaluation.issues.join(", ")}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </details>
  );
}
