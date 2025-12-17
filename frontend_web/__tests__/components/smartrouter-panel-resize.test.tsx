import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";

// Mock ReactFlow and friends used by SmartRouterPanel (keep it lightweight)
jest.mock("reactflow", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="reactflow">{children}</div>
  ),
  Background: () => <div data-testid="background" />,
  Controls: () => <div data-testid="controls" />,
  MiniMap: () => <div data-testid="minimap" />,
  MarkerType: { ArrowClosed: "arrowclosed" },
  Handle: () => null,
  Position: { Top: "top", Bottom: "bottom" },
}));

// Provide a stable panel state without wiring full provider state machine.
jest.mock("@/lib/contexts/SmartRouterContext", () => ({
  useSmartRouterPanel: () => ({
    isPanelOpen: true,
    panelKind: "moe",
    metadata: null,
    moeTrace: {
      request_id: "r1",
      query: "q",
      latency_ms: 1,
      cache_hit: false,
      fallback: false,
      expert_details: [],
      selected_experts: [],
      final_response: "ok",
    },
    executionTrace: null,
    closePanel: jest.fn(),
    expandPanel: jest.fn(),
  }),
}));

import { SmartRouterPanel } from "@/components/smartrouter-panel";

describe("SmartRouterPanel resize handle", () => {
  it("renders a resize handle when panel is open", () => {
    render(<SmartRouterPanel />);
    expect(screen.getByTestId("right-panel-resize-handle")).toBeInTheDocument();
  });

  it("updates panel width style when dragging the handle", () => {
    // Set a stable viewport width for vw calculations.
    Object.defineProperty(window, "innerWidth", { value: 1000, configurable: true });

    const { container } = render(<SmartRouterPanel />);
    const handle = screen.getByTestId("right-panel-resize-handle");

    // The fixed panel container is the first element with 'fixed glass-panel' classes.
    const panel = container.querySelector("div.fixed.glass-panel") as HTMLDivElement;
    expect(panel).toBeTruthy();

    const before = panel.style.width;

    // Drag left (smaller clientX => larger right-panel width)
    // Use mouse events here (pointer events are not consistently implemented in jsdom).
    fireEvent.mouseDown(handle, { clientX: 800 });
    fireEvent.mouseMove(window, { clientX: 500 });
    fireEvent.mouseUp(window, { clientX: 500 });

    return waitFor(() => {
      const after = panel.style.width;
      expect(after).not.toEqual(before);
      expect(after).toMatch(/vw$/);
    });
  });
});


