"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { getApiClient, ApiClientError } from "@/lib/api-client";
import type { AgentDetail } from "@/lib/types";
import { Loader2, Package, FileCode, Cpu, Settings, Database } from "lucide-react";

interface AgentConfigViewProps {
  agentId: string;
}

/**
 * Agent Config View Component
 *
 * Displays detailed configuration for a selected agent from config/open_agents.yaml.
 *
 * Shows:
 * - Agent metadata (name, type, description)
 * - Python module location (e.g., asdrp.agents.single.geo_agent)
 * - Model configuration (model name, temperature, max tokens)
 * - Available tools
 * - Connected agents (edges in the agent graph)
 * - Session memory settings
 *
 * This makes it clear which Python file implements the agent, allowing
 * developers to easily locate and modify agent code.
 */
export function AgentConfigView({ agentId }: AgentConfigViewProps) {
  const [agent, setAgent] = useState<AgentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!agentId) {
      setAgent(null);
      setLoading(false);
      return;
    }

    async function fetchAgent() {
      try {
        setLoading(true);
        setError(null);
        const client = getApiClient();
        const data = await client.getAgent(agentId);
        setAgent(data);

        console.log(`✓ Loaded agent configuration for: ${data.display_name}`);
        console.log(`  Module: ${data.module}`);
        console.log(`  Function: ${data.function}`);
      } catch (err) {
        const message =
          err instanceof ApiClientError
            ? err.message
            : "Failed to load agent details";
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    fetchAgent();
  }, [agentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-4">
        <p className="text-destructive text-sm">{error}</p>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="py-4">
        <p className="text-muted-foreground text-sm">No agent selected</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Agent Header */}
      <div className="pb-3 border-b border-border/30">
        <div className="flex items-center gap-2 mb-1">
          <Cpu className="h-4 w-4 text-primary" />
          <h3 className="font-semibold">{agent.display_name}</h3>
        </div>
        <p className="text-xs text-muted-foreground">
          ID: <code className="px-1 py-0.5 bg-muted/50 rounded">{agent.id}</code>
        </p>
      </div>

      <div className="space-y-4">
        {/* Description */}
        {agent.description && (
          <div>
            <h4 className="text-xs font-semibold mb-1 flex items-center gap-1 text-muted-foreground">
              <FileCode className="h-3 w-3" />
              Description
            </h4>
            <p className="text-sm">{agent.description}</p>
          </div>
        )}

        {/* Python Module Location */}
        <div className="p-3 bg-muted/30 rounded-lg border border-border/30">
          <h4 className="text-xs font-semibold mb-2 flex items-center gap-1">
            <Package className="h-3 w-3" />
            Python Module
          </h4>
          <div className="space-y-1.5 text-xs font-mono">
            <div className="flex items-start justify-between gap-2">
              <span className="text-muted-foreground shrink-0">Module:</span>
              <code className="bg-background/50 px-2 py-0.5 rounded border border-border/30 text-right break-all">
                {agent.module}
              </code>
            </div>
            <div className="flex items-start justify-between gap-2">
              <span className="text-muted-foreground shrink-0">Function:</span>
              <code className="bg-background/50 px-2 py-0.5 rounded border border-border/30">
                {agent.function}()
              </code>
            </div>
            <div className="mt-2 text-xs text-muted-foreground italic">
              💡 {agent.module.replace(/\./g, '/')}.py
            </div>
          </div>
        </div>

        {/* Type & Status */}
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xs font-semibold mb-1 text-muted-foreground">Type</h4>
            <span className="px-2 py-1 bg-primary/10 text-primary rounded text-xs font-medium">
              {agent.type}
            </span>
          </div>
          <div className="text-right">
            <h4 className="text-xs font-semibold mb-1 text-muted-foreground">Status</h4>
            <span className={`text-xs font-medium ${agent.enabled ? 'text-green-600' : 'text-muted-foreground'}`}>
              {agent.enabled ? '● Active' : '○ Disabled'}
            </span>
          </div>
        </div>

        {/* Model Configuration */}
        <div>
          <h4 className="text-xs font-semibold mb-2 flex items-center gap-1 text-muted-foreground">
            <Settings className="h-3 w-3" />
            Model Configuration
          </h4>
          <div className="text-xs space-y-1.5 bg-muted/30 p-3 rounded-lg border border-border/30">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Model:</span>
              <code className="font-mono">{agent.model_name}</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Temperature:</span>
              <code className="font-mono">{agent.temperature}</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Max Tokens:</span>
              <code className="font-mono">{agent.max_tokens}</code>
            </div>
          </div>
        </div>

        {/* Tools */}
        {agent.tools && agent.tools.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold mb-2 text-muted-foreground">Available Tools</h4>
            <div className="flex flex-wrap gap-1.5">
              {agent.tools.map((tool) => (
                <span
                  key={tool}
                  className="px-2 py-1 bg-primary/10 text-primary rounded text-xs font-mono"
                >
                  {tool}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Connected Agents */}
        {agent.edges && agent.edges.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold mb-2 text-muted-foreground">Connected Agents</h4>
            <div className="flex flex-wrap gap-1.5">
              {agent.edges.map((edge) => (
                <span
                  key={edge}
                  className="px-2 py-1 bg-accent/50 rounded text-xs"
                >
                  {edge}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Session Memory */}
        <div className="pt-3 border-t border-border/30">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold flex items-center gap-1 text-muted-foreground">
              <Database className="h-3 w-3" />
              Session Memory
            </h4>
            <span className="text-xs">
              {agent.session_memory_enabled ? (
                <span className="text-green-600 font-medium">✓ Enabled</span>
              ) : (
                <span className="text-muted-foreground">✗ Disabled</span>
              )}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
