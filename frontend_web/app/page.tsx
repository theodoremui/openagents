"use client";

import { useState } from "react";
import { AgentSelector } from "@/components/agent-selector";
import { AgentConfigView } from "@/components/agent-config-view";
import { ExecutionModeToggle } from "@/components/execution-mode-toggle";
import { UnifiedChatInterface } from "@/components/unified-chat-interface";
import { SmartRouterPanel } from "@/components/smartrouter-panel";
import { useSmartRouterPanel } from "@/lib/contexts/SmartRouterContext";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { ExecutionMode } from "@/lib/types";
import { ChevronLeft, ChevronRight, ChevronDown, Settings, Zap, Info } from "lucide-react";

/**
 * Agent Simulation Page
 *
 * Main page for interacting with agents using the new unified interface.
 * Supports three execution modes:
 * - Mock: Fast testing, no API costs
 * - Real: Actual execution with complete response
 * - Stream: Actual execution with real-time token streaming
 *
 * Layout: Collapsible left sidebar (agent selection + mode), Right panel (chat interface)
 */
export default function SimulationPage() {
  const [selectedAgent, setSelectedAgent] = useState("moe");  // Default to MoE orchestrator
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("real");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  // Individual section collapse states - default to collapsed for cleaner initial view
  const [agentSelectorCollapsed, setAgentSelectorCollapsed] = useState(true);
  const [executionModeCollapsed, setExecutionModeCollapsed] = useState(true);
  const [configViewCollapsed, setConfigViewCollapsed] = useState(true);

  // Get SmartRouter panel state to adjust layout
  const { isPanelOpen } = useSmartRouterPanel();

  return (
    <div className="h-full relative">
      {/* Main Layout Container - Account for navigation header height (64px) */}
      <div className="fixed left-0 right-0 bottom-0" style={{ top: '6.5rem' }}>
        {/* Left Sidebar: Fixed Position Panel - Starts below navigation */}
        <div
          className={`
            fixed left-0 bottom-0 z-30
            transition-all duration-500 ease-in-out overflow-hidden
            ${sidebarCollapsed ? 'opacity-0 -translate-x-full pointer-events-none' : 'opacity-100 translate-x-0'}
          `}
          style={{
            top: '6.5rem',
            width: '30vw',
            minWidth: '320px',
            maxWidth: '480px',
          }}
        >
          {/* Single Unified Glass Panel - Full height */}
          <div className="glass-panel backdrop-blur-xl bg-gradient-to-br from-card/80 to-card/40 border-r border-border/50 shadow-lg h-full flex flex-col">
            {/* Unified Header - Title with Collapse Button */}
            <div className="border-b border-border/30 bg-gradient-to-r from-primary/10 to-primary/5">
              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3 flex-1">
                  <div className="p-2 rounded-lg bg-primary/20 shadow-sm">
                    <Settings className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                      Agent Execution
                    </h1>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Select an agent and execution mode to start chatting
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSidebarCollapsed(true)}
                  className="h-10 w-10 hover:bg-primary/20 transition-all rounded-lg ml-2 flex-shrink-0"
                  title="Collapse panel"
                >
                  <ChevronLeft className="h-5 w-5 text-primary" />
                </Button>
              </div>
            </div>

            {/* Collapsible Sections - Scrollable */}
            <div className="divide-y divide-border/30 flex-1 overflow-y-auto custom-scrollbar">
              {/* Agent Selector Section */}
              <div className="transition-all duration-200">
                <button
                  onClick={() => setAgentSelectorCollapsed(!agentSelectorCollapsed)}
                  className="w-full flex items-center justify-between p-3 hover:bg-primary/5 transition-colors group"
                >
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded bg-primary/10 group-hover:bg-primary/20 transition-colors">
                      <Settings className="h-3 w-3 text-primary" />
                    </div>
                    <span className="text-sm font-medium">Agent Selection</span>
                  </div>
                  <ChevronDown
                    className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${agentSelectorCollapsed ? "-rotate-90" : ""
                      }`}
                  />
                </button>
                {!agentSelectorCollapsed && (
                  <div className="px-3 pb-3 animate-in fade-in slide-in-from-top-2 duration-200">
                    <label className="text-xs font-medium text-muted-foreground mb-2 block">
                      Select Agent
                    </label>
                    <AgentSelector
                      value={selectedAgent}
                      onValueChange={setSelectedAgent}
                    />
                  </div>
                )}
              </div>

              {/* Execution Mode Section */}
              {selectedAgent && (
                <div className="transition-all duration-200">
                  <button
                    onClick={() => setExecutionModeCollapsed(!executionModeCollapsed)}
                    className="w-full flex items-center justify-between p-3 hover:bg-primary/5 transition-colors group"
                  >
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded bg-primary/10 group-hover:bg-primary/20 transition-colors">
                        <Zap className="h-3 w-3 text-primary" />
                      </div>
                      <span className="text-sm font-medium">Execution Mode</span>
                    </div>
                    <ChevronDown
                      className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${executionModeCollapsed ? "-rotate-90" : ""
                        }`}
                    />
                  </button>
                  {!executionModeCollapsed && (
                    <div className="px-3 pb-3 animate-in fade-in slide-in-from-top-2 duration-200">
                      <ExecutionModeToggle
                        value={executionMode}
                        onChange={setExecutionMode}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Agent Configuration Section */}
              {selectedAgent && (
                <div className="transition-all duration-200">
                  <button
                    onClick={() => setConfigViewCollapsed(!configViewCollapsed)}
                    className="w-full flex items-center justify-between p-3 hover:bg-primary/5 transition-colors group"
                  >
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded bg-primary/10 group-hover:bg-primary/20 transition-colors">
                        <Info className="h-3 w-3 text-primary" />
                      </div>
                      <span className="text-sm font-medium">Agent Details</span>
                    </div>
                    <ChevronDown
                      className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${configViewCollapsed ? "-rotate-90" : ""
                        }`}
                    />
                  </button>
                  {!configViewCollapsed && (
                    <div className="px-3 pb-3 animate-in fade-in slide-in-from-top-2 duration-200">
                      <AgentConfigView agentId={selectedAgent} />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Chat Interface - Fills remaining space between left and right panels */}
        <div
          className="absolute top-0 bottom-0 transition-all duration-500 ease-in-out"
          style={{
            left: sidebarCollapsed ? '0' : 'min(30vw, 480px)',
            right: isPanelOpen ? 'min(30vw, max(384px, 30vw))' : '0',
            paddingLeft: sidebarCollapsed ? '5rem' : '1rem',
            paddingRight: '1rem',
          }}
        >
          {selectedAgent ? (
            <div className="glass-panel rounded-xl backdrop-blur-xl bg-gradient-to-br from-card/80 to-card/40 border border-border/50 shadow-lg h-full">
              <UnifiedChatInterface
                agentId={selectedAgent}
                mode={executionMode}
                useSession={true}
              />
            </div>
          ) : (
            <Card className="glass-panel rounded-xl backdrop-blur-xl bg-gradient-to-br from-card/60 to-card/30 border border-border/50 shadow-lg p-12 text-center text-muted-foreground h-full flex items-center justify-center">
              <div className="space-y-2">
                <p className="text-lg font-semibold">No Agent Selected</p>
                <p className="text-sm">
                  Select an agent from the configuration panel to start chatting
                </p>
              </div>
            </Card>
          )}
        </div>

        {/* Collapsed Sidebar - Floating Expand Button */}
        <div
          className={`
            fixed left-4 top-1/2 -translate-y-1/2 z-50
            transition-all duration-300 ease-in-out
            ${sidebarCollapsed ? 'opacity-100 scale-100' : 'opacity-0 scale-0 pointer-events-none'}
          `}
        >
          <Button
            variant="default"
            size="icon"
            onClick={() => setSidebarCollapsed(false)}
            className="h-12 w-12 rounded-full shadow-xl glass-panel backdrop-blur-xl bg-primary/90 hover:bg-primary border border-primary-foreground/20 transition-all hover:scale-110"
            title="Expand configuration panel"
          >
            <ChevronRight className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* SmartRouter Visualization Panel - Fixed Position Overlay */}
      <SmartRouterPanel />
    </div>
  );
}
