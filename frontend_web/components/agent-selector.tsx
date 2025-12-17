"use client";

import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getApiClient, ApiClientError } from "@/lib/api-client";
import type { AgentListItem } from "@/lib/types";
import { Loader2, AlertCircle, CheckCircle } from "lucide-react";

interface AgentSelectorProps {
  value: string;
  onValueChange: (value: string) => void;
  className?: string;
}

/**
 * Agent Selector Component
 *
 * Dynamically fetches and displays all agents defined in config/open_agents.yaml.
 */
export function AgentSelector({
  value,
  onValueChange,
  className,
}: AgentSelectorProps) {
  const [agents, setAgents] = useState<AgentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchAgents() {
      try {
        setLoading(true);
        setError(null);

        const client = getApiClient();
        const data = await client.listAgents();

        const sortedAgents = data.sort((a, b) =>
          a.display_name.localeCompare(b.display_name)
        );

        setAgents(sortedAgents);

        if (!value && sortedAgents.length > 0) {
          onValueChange(sortedAgents[0].id);
        }

        if (process.env.NODE_ENV === 'development') {
          console.log(`✓ Loaded ${sortedAgents.length} agents from config/open_agents.yaml`);
        }

      } catch (err) {
        const message =
          err instanceof ApiClientError
            ? err.message
            : "Failed to load agents from configuration";
        setError(message);
        if (process.env.NODE_ENV === 'development') {
          console.error('Failed to load agents:', err);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchAgents();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-3 border rounded-md bg-muted/50">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Loading agents from config/open_agents.yaml...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-3 border border-destructive rounded-md bg-destructive/10">
        <AlertCircle className="h-4 w-4 text-destructive" />
        <div className="flex-1">
          <p className="text-sm font-medium text-destructive">Error loading agents</p>
          <p className="text-xs text-destructive/80">{error}</p>
        </div>
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="flex items-center gap-2 p-3 border rounded-md bg-muted/50">
        <AlertCircle className="h-4 w-4 text-muted-foreground" />
        <div className="flex-1">
          <p className="text-sm font-medium text-muted-foreground">No agents available</p>
          <p className="text-xs text-muted-foreground/80">
            Check config/open_agents.yaml for agent definitions
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className={className}>
          <SelectValue placeholder="Select an agent..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="smartrouter">
            🎯 SmartRouter (Multi-Agent Orchestrator)
          </SelectItem>
          {agents.map((agent) => (
            <SelectItem key={agent.id} value={agent.id}>
              {agent.display_name} ({agent.id})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Agent Count Display */}
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <CheckCircle className="h-3 w-3" />
        <span>
          {agents.length} agent{agents.length !== 1 ? 's' : ''} loaded from{' '}
          <code className="px-1 py-0.5 bg-muted rounded">config/open_agents.yaml</code>
        </span>
      </div>

      {/* Debug Info (only in development) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Debug: Agent Sources
          </summary>
          <ul className="mt-2 space-y-1 pl-4 border-l-2 border-muted">
            {agents.map((agent) => (
              <li key={agent.id} className="text-muted-foreground font-mono">
                {agent.id}: {agent.display_name}
                {agent.description && (
                  <span className="text-xs opacity-70 block ml-4">
                    {agent.description.substring(0, 80)}...
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
