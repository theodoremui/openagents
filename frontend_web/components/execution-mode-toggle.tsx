/**
 * Execution Mode Toggle Component
 *
 * Allows users to switch between execution modes:
 * - Mock: Fast testing, no API costs
 * - Real: Actual execution with complete response
 * - Stream: Actual execution with real-time tokens
 *
 * Follows SOLID principles with clear single responsibility.
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { ExecutionMode } from "@/lib/types";
import { Zap, Play, Radio } from "lucide-react";

interface ExecutionModeToggleProps {
  value: ExecutionMode;
  onChange: (mode: ExecutionMode) => void;
  disabled?: boolean;
}

/**
 * Mode configuration with metadata
 */
const MODE_CONFIG: Record<
  ExecutionMode,
  {
    label: string;
    description: string;
    icon: React.ReactNode;
    color: string;
    badge: string;
  }
> = {
  mock: {
    label: "Mock",
    description: "Fast testing • No API costs • Instant responses",
    icon: <Zap className="h-4 w-4" />,
    color: "bg-purple-500/10 hover:bg-purple-500/20 border-purple-500/20",
    badge: "FREE",
  },
  real: {
    label: "Real",
    description: "Actual execution • Complete response • 2-10s",
    icon: <Play className="h-4 w-4" />,
    color: "bg-green-500/10 hover:bg-green-500/20 border-green-500/20",
    badge: "PAID",
  },
  stream: {
    label: "Stream",
    description: "Actual execution • Real-time tokens • Best UX",
    icon: <Radio className="h-4 w-4" />,
    color: "bg-blue-500/10 hover:bg-blue-500/20 border-blue-500/20",
    badge: "PAID",
  },
};

/**
 * Execution Mode Toggle Component
 */
export function ExecutionModeToggle({
  value,
  onChange,
  disabled = false,
}: ExecutionModeToggleProps) {
  const [selectedMode, setSelectedMode] = useState<ExecutionMode>(value);

  const handleModeChange = (mode: ExecutionMode) => {
    setSelectedMode(mode);
    onChange(mode);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Execution Mode</CardTitle>
        <CardDescription>
          Choose how to execute the agent
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {(Object.keys(MODE_CONFIG) as ExecutionMode[]).map((mode) => {
          const config = MODE_CONFIG[mode];
          const isSelected = selectedMode === mode;

          return (
            <Button
              key={mode}
              variant={isSelected ? "default" : "outline"}
              className={`w-full justify-start h-auto py-3 ${
                !isSelected ? config.color : ""
              }`}
              onClick={() => handleModeChange(mode)}
              disabled={disabled}
            >
              <div className="flex items-start gap-3 w-full">
                <div className="mt-0.5">{config.icon}</div>
                <div className="flex-1 text-left">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{config.label}</span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        config.badge === "FREE"
                          ? "bg-green-500/20 text-green-700 dark:text-green-300"
                          : "bg-orange-500/20 text-orange-700 dark:text-orange-300"
                      }`}
                    >
                      {config.badge}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {config.description}
                  </p>
                </div>
                {isSelected && (
                  <div className="h-4 w-4 rounded-full bg-primary flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                  </div>
                )}
              </div>
            </Button>
          );
        })}

        {/* Mode Details */}
        <div className="pt-4 border-t">
          <div className="text-xs text-muted-foreground space-y-2">
            <p>
              <strong>Mock:</strong> Returns simulated responses instantly.
              Perfect for UI development and testing.
            </p>
            <p>
              <strong>Real:</strong> Makes actual OpenAI API calls. Waits for
              complete response before displaying.
            </p>
            <p>
              <strong>Stream:</strong> Makes actual OpenAI API calls. Shows
              tokens as they're generated for better interactivity.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
