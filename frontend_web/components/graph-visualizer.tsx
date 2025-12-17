"use client";

import { useEffect, useState, useCallback } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getApiClient, ApiClientError } from "@/lib/api-client";
import type { AgentGraph } from "@/lib/types";
import { Loader2, RefreshCw, Maximize2 } from "lucide-react";

interface GraphVisualizerProps {
  className?: string;
}

/**
 * Graph Visualizer Component
 *
 * Visualizes agent relationships using ReactFlow.
 * Provides interactive graph with zoom, pan, and node selection.
 */
export function GraphVisualizer({ className }: GraphVisualizerProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  async function loadGraph() {
    try {
      setLoading(true);
      setError(null);
      const client = getApiClient();
      const data: AgentGraph = await client.getGraph();

      // Transform data to ReactFlow format
      const flowNodes: Node[] = data.nodes.map((node) => ({
        id: node.id,
        type: node.type,
        data: {
          ...node.data,
        },
        position: node.position,
        style: {
          background: "#fff",
          border: "2px solid #ddd",
          borderRadius: "8px",
          padding: "10px",
          fontSize: "12px",
          width: "180px",
        },
      }));

      const flowEdges: Edge[] = data.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        label: edge.label,
        animated: edge.animated || false,
        style: { stroke: "#999" },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : "Failed to load graph";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadGraph();
  }, []);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNode(node);
    },
    []
  );

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="pt-6 flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <p className="text-destructive">{error}</p>
          <Button onClick={loadGraph} className="mt-4" variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Agent Graph</CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadGraph}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Graph */}
        <div className="border rounded-lg overflow-hidden" style={{ height: "600px" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={0.1}
            maxZoom={2}
          >
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                if (node.id === selectedNode?.id) return "#3b82f6";
                return "#cbd5e1";
              }}
              style={{
                backgroundColor: "#f8fafc",
              }}
            />
          </ReactFlow>
        </div>

        {/* Selected Node Info */}
        {selectedNode && (
          <div className="mt-4 p-4 border rounded-md bg-muted">
            <h4 className="font-semibold mb-2">Selected: {selectedNode.data.label}</h4>
            {selectedNode.data.description && (
              <p className="text-sm text-muted-foreground">
                {selectedNode.data.description}
              </p>
            )}
            {selectedNode.data.type && (
              <p className="text-sm text-muted-foreground mt-1">
                Type: {selectedNode.data.type}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
