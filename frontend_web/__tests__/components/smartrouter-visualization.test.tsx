/**
 * Tests for SmartRouterVisualization component
 * 
 * Tests cover:
 * - Component rendering
 * - Node and edge generation
 * - Phase visualization
 * - Error handling
 * - Edge cases
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { SmartRouterVisualization } from "@/components/smartrouter-visualization";
import type { SmartRouterMetadata, SmartRouterTrace } from "@/lib/types";

// Mock ReactFlow to avoid canvas rendering issues in tests
jest.mock("reactflow", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="reactflow">{children}</div>
  ),
  Background: () => <div data-testid="background" />,
  Controls: () => <div data-testid="controls" />,
  MiniMap: () => <div data-testid="minimap" />,
  MarkerType: {
    ArrowClosed: "arrowclosed",
  },
}));

describe("SmartRouterVisualization", () => {
  const createMockMetadata = (overrides?: Partial<SmartRouterMetadata>): SmartRouterMetadata => ({
    orchestrator: "smartrouter",
    phases: [],
    final_decision: "answer",
    total_time: 1.5,
    ...overrides,
  });

  const createMockTrace = (
    phase: string,
    data: Record<string, unknown> = {}
  ): SmartRouterTrace => ({
    phase: phase as SmartRouterTrace["phase"],
    timestamp: new Date().toISOString(),
    data,
  });

  describe("Component Rendering", () => {
    it("should render without crashing", () => {
      const metadata = createMockMetadata();
      render(<SmartRouterVisualization metadata={metadata} />);
      expect(screen.getByText("SmartRouter Orchestration Flow")).toBeInTheDocument();
    });

    it("should display summary statistics", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("interpretation"),
          createMockTrace("decomposition"),
        ],
        total_time: 2.5,
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText("2")).toBeInTheDocument(); // Phase count
      expect(screen.getByText("2.50s")).toBeInTheDocument(); // Total time
    });

    it("should display final decision badge", () => {
      const metadata = createMockMetadata({ final_decision: "fallback" });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText("Fallback")).toBeInTheDocument();
    });

    it("should display answer badge for successful decisions", () => {
      const metadata = createMockMetadata({ final_decision: "answer" });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText("Answer")).toBeInTheDocument();
    });
  });

  describe("Phase Visualization", () => {
    it("should render interpretation phase", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("interpretation", {
            intent: {
              complexity: "medium",
              domains: ["geography", "navigation"],
              reasoning: "Test reasoning",
            },
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText(/Interpretation/i)).toBeInTheDocument();
    });

    it("should render decomposition phase with subqueries", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("decomposition", {
            subqueries: [
              {
                id: "sq1",
                text: "Find location",
                capability_required: "geo",
              },
            ],
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText(/Decomposition/i)).toBeInTheDocument();
    });

    it("should render routing phase", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("routing", {
            subqueries: [
              {
                id: "sq1",
                text: "Test",
                capability_required: "geo",
              },
            ],
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      // Routing phase should be rendered (check for phase details)
      // The component renders "routing" in phase details, not "Capability Routing" in the graph
      const routingElements = screen.getAllByText(/routing/i);
      expect(routingElements.length).toBeGreaterThan(0);
    });

    it("should render execution phase with agent responses", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("execution", {
            responses: [
              {
                agent_id: "geo",
                agent_name: "GeoAgent",
                success: true,
                content: "Test response",
              },
            ],
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText(/Execution/i)).toBeInTheDocument();
    });

    it("should render synthesis phase", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("synthesis", {
            synthesis: {
              confidence: 0.85,
              sources: ["geo", "map"],
            },
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      // Synthesis phase should be rendered (check for phase details)
      // Multiple elements may contain "synthesis" text, so use getAllByText
      const synthesisElements = screen.getAllByText(/synthesis/i);
      expect(synthesisElements.length).toBeGreaterThan(0);
    });

    it("should render evaluation phase without using reserved keyword", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("evaluation", {
            evaluation: {
              is_high_quality: true,
              completeness_score: 0.9,
              accuracy_score: 0.85,
              clarity_score: 0.8,
            },
          }),
        ],
      });
      
      // This should not throw a syntax error
      expect(() => {
        render(<SmartRouterVisualization metadata={metadata} />);
      }).not.toThrow();
      
      // Evaluation phase should be rendered (check for phase details)
      // Multiple elements contain "evaluation" text, so use getAllByText
      const evaluationElements = screen.getAllByText(/evaluation/i);
      expect(evaluationElements.length).toBeGreaterThan(0);
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty phases array", () => {
      const metadata = createMockMetadata({ phases: [] });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText("0")).toBeInTheDocument(); // Phase count
    });

    it("should handle missing total_time", () => {
      const metadata = createMockMetadata({ total_time: undefined });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText("N/A")).toBeInTheDocument();
    });

    it("should handle phase with missing data", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("interpretation", {}), // No intent data
          createMockTrace("decomposition", {}), // No subqueries
        ],
      });
      
      expect(() => {
        render(<SmartRouterVisualization metadata={metadata} />);
      }).not.toThrow();
    });

    it("should handle evaluation phase with low quality", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("evaluation", {
            evaluation: {
              is_high_quality: false,
              completeness_score: 0.5,
              accuracy_score: 0.4,
              clarity_score: 0.3,
            },
          }),
        ],
      });
      
      expect(() => {
        render(<SmartRouterVisualization metadata={metadata} />);
      }).not.toThrow();
    });
  });

  describe("Phase Details", () => {
    it("should display phase details in expandable sections", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("interpretation", {
            intent: {
              complexity: "high",
              domains: ["geography"],
              reasoning: "Test reasoning",
            },
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      // Phase details should be rendered
      expect(screen.getByText(/interpretation/i)).toBeInTheDocument();
    });

    it("should display subquery details", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("decomposition", {
            subqueries: [
              {
                id: "sq1",
                text: "Find location in San Francisco",
                capability_required: "geo",
                agent_id: "geo",
              },
            ],
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText(/sq1/i)).toBeInTheDocument();
    });

    it("should display agent response details", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("execution", {
            responses: [
              {
                agent_id: "geo",
                agent_name: "GeoAgent",
                success: true,
                content: "San Francisco is located in California",
                execution_time: 1.2,
              },
            ],
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText(/GeoAgent/i)).toBeInTheDocument();
    });

    it("should display evaluation scores", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("evaluation", {
            evaluation: {
              is_high_quality: true,
              completeness_score: 0.95,
              accuracy_score: 0.9,
              clarity_score: 0.85,
              issues: ["minor formatting"],
            },
          }),
        ],
      });
      render(<SmartRouterVisualization metadata={metadata} />);
      
      expect(screen.getByText(/Completeness/i)).toBeInTheDocument();
      expect(screen.getByText(/Accuracy/i)).toBeInTheDocument();
      expect(screen.getByText(/Clarity/i)).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should handle invalid phase data gracefully", () => {
      const metadata = createMockMetadata({
        phases: [
          {
            phase: "unknown_phase" as any,
            timestamp: new Date().toISOString(),
            data: {},
          },
        ],
      });
      
      expect(() => {
        render(<SmartRouterVisualization metadata={metadata} />);
      }).not.toThrow();
    });

    it("should handle malformed evaluation data", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("evaluation", {
            evaluation: {
              // Missing required fields
              is_high_quality: false,
            } as any,
          }),
        ],
      });
      
      expect(() => {
        render(<SmartRouterVisualization metadata={metadata} />);
      }).not.toThrow();
    });
  });

  describe("Reserved Keyword Fix", () => {
    it("should not use 'eval' as a variable name", () => {
      // This test ensures the code doesn't use reserved keywords
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("evaluation", {
            evaluation: {
              is_high_quality: true,
              completeness_score: 0.9,
              accuracy_score: 0.85,
              clarity_score: 0.8,
            },
          }),
        ],
      });
      
      // If eval was used, this would fail in strict mode
      expect(() => {
        render(<SmartRouterVisualization metadata={metadata} />);
      }).not.toThrow();
    });

    it("should correctly access evaluation properties", () => {
      const metadata = createMockMetadata({
        phases: [
          createMockTrace("evaluation", {
            evaluation: {
              is_high_quality: true,
              completeness_score: 0.95,
              accuracy_score: 0.9,
              clarity_score: 0.85,
            },
          }),
        ],
      });
      
      render(<SmartRouterVisualization metadata={metadata} />);
      
      // Should display evaluation data correctly
      const evaluationElements = screen.getAllByText(/evaluation/i);
      expect(evaluationElements.length).toBeGreaterThan(0);
      expect(screen.getByText(/High/i)).toBeInTheDocument();
    });
  });
});

