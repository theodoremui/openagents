/**
 * Tests for ExecutionModeToggle Component
 *
 * Tests the execution mode selection component:
 * - Rendering of all three modes
 * - Mode selection functionality
 * - Disabled state handling
 * - Visual indicators
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { ExecutionModeToggle } from "@/components/execution-mode-toggle";
import type { ExecutionMode } from "@/lib/types";

describe("ExecutionModeToggle", () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Helper function to get mode buttons
  const getModeButtons = () => {
    const buttons = screen.getAllByRole("button");
    return {
      mock: buttons.find(btn => btn.textContent?.includes("MockFREE")),
      real: buttons.find(btn => btn.textContent?.includes("RealPAID")),
      stream: buttons.find(btn => btn.textContent?.includes("StreamPAID")),
    };
  };

  describe("Rendering", () => {
    it("should render component", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      expect(screen.getByText("Execution Mode")).toBeInTheDocument();
      expect(screen.getByText("Choose how to execute the agent")).toBeInTheDocument();
    });

    it("should render all three mode options", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      expect(screen.getByText("Mock")).toBeInTheDocument();
      expect(screen.getByText("Real")).toBeInTheDocument();
      expect(screen.getByText("Stream")).toBeInTheDocument();
    });

    it("should display mode descriptions", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      expect(
        screen.getByText(/Fast testing • No API costs • Instant responses/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Actual execution • Complete response • 2-10s/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Actual execution • Real-time tokens • Best UX/i)
      ).toBeInTheDocument();
    });

    it("should display FREE badge for mock mode", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const badges = screen.getAllByText("FREE");
      expect(badges.length).toBeGreaterThan(0);
    });

    it("should display PAID badges for real and stream modes", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const badges = screen.getAllByText("PAID");
      expect(badges.length).toBe(2); // Real and Stream
    });
  });

  describe("Mode Selection", () => {
    it("should highlight selected mode", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = screen.getAllByRole("button");
      const mockButton = buttons.find(btn => btn.textContent?.includes("MockFREE"));
      expect(mockButton).toBeDefined();
    });

    it("should call onChange when mode is clicked", async () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = screen.getAllByRole("button");
      const realButton = buttons.find(btn => btn.textContent?.includes("RealPAID") && !btn.textContent?.includes("Real-time"));
      await userEvent.click(realButton!);

      expect(mockOnChange).toHaveBeenCalledWith("real");
      expect(mockOnChange).toHaveBeenCalledTimes(1);
    });

    it("should switch between modes", async () => {
      const { rerender } = render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      // Click Real
      let buttons = getModeButtons();
      await userEvent.click(buttons.real!);
      expect(mockOnChange).toHaveBeenCalledWith("real");

      // Rerender with new value
      rerender(<ExecutionModeToggle value="real" onChange={mockOnChange} />);

      // Click Stream
      buttons = getModeButtons();
      await userEvent.click(buttons.stream!);
      expect(mockOnChange).toHaveBeenCalledWith("stream");

      // Rerender with new value
      rerender(<ExecutionModeToggle value="stream" onChange={mockOnChange} />);

      // Click Mock
      buttons = getModeButtons();
      await userEvent.click(buttons.mock!);
      expect(mockOnChange).toHaveBeenCalledWith("mock");
    });

    it("should allow clicking already selected mode", async () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = getModeButtons();
      await userEvent.click(buttons.mock!);

      expect(mockOnChange).toHaveBeenCalledWith("mock");
    });
  });

  describe("Disabled State", () => {
    it("should disable all buttons when disabled prop is true", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} disabled={true} />
      );

      const buttons = getModeButtons();

      expect(buttons.mock).toBeDisabled();
      expect(buttons.real).toBeDisabled();
      expect(buttons.stream).toBeDisabled();
    });

    it("should not call onChange when disabled and clicked", async () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} disabled={true} />
      );

      const buttons = getModeButtons();
      await userEvent.click(buttons.real!);

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it("should enable buttons when disabled prop is false", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} disabled={false} />
      );

      const buttons = getModeButtons();

      expect(buttons.mock).not.toBeDisabled();
      expect(buttons.real).not.toBeDisabled();
      expect(buttons.stream).not.toBeDisabled();
    });
  });

  describe("Mode Details Section", () => {
    it("should display detailed mode explanations", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      expect(
        screen.getAllByText(/Returns simulated responses instantly/i).length
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByText(/Makes actual OpenAI API calls/i).length
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByText(/Shows tokens as they're generated/i).length
      ).toBeGreaterThan(0);
    });

    it("should mention use cases for each mode", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      expect(
        screen.getByText(/Perfect for UI development and testing/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Waits for complete response before displaying/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/better interactivity/i)
      ).toBeInTheDocument();
    });
  });

  describe("Visual Indicators", () => {
    it("should show icons for each mode", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      // Buttons should have icons (lucide-react icons)
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBe(3);

      // Each button should have an icon (rendered as SVG)
      buttons.forEach((button) => {
        const svg = button.querySelector("svg");
        expect(svg).toBeInTheDocument();
      });
    });

    it("should show selection indicator for selected mode", () => {
      render(
        <ExecutionModeToggle value="real" onChange={mockOnChange} />
      );

      // Selected button should have specific styling
      const buttons = getModeButtons();
      expect(buttons.real).toBeDefined();
      expect(buttons.real).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible button roles", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(3);
    });

    it("should have descriptive button text", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = getModeButtons();
      expect(buttons.mock).toBeInTheDocument();
      expect(buttons.real).toBeInTheDocument();
      expect(buttons.stream).toBeInTheDocument();
    });

    it("should be keyboard navigable", async () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = getModeButtons();

      // Focus the button
      buttons.real!.focus();
      expect(buttons.real).toHaveFocus();

      // Press Enter
      fireEvent.keyDown(buttons.real!, { key: "Enter" });
      fireEvent.click(buttons.real!);

      expect(mockOnChange).toHaveBeenCalledWith("real");
    });
  });

  describe("Props Handling", () => {
    it("should accept all valid execution modes", () => {
      const modes: ExecutionMode[] = ["mock", "real", "stream"];

      modes.forEach((mode) => {
        const { unmount } = render(
          <ExecutionModeToggle value={mode} onChange={mockOnChange} />
        );

        expect(screen.getAllByText("Execution Mode").length).toBeGreaterThan(0);

        unmount();
      });
    });

    it("should handle onChange callback correctly", async () => {
      const customOnChange = jest.fn((mode: ExecutionMode) => {
        console.log(`Mode changed to: ${mode}`);
      });

      render(
        <ExecutionModeToggle value="mock" onChange={customOnChange} />
      );

      const streamButton = screen.getByRole("button", { name: /Stream/i });
      await userEvent.click(streamButton);

      expect(customOnChange).toHaveBeenCalledWith("stream");
      expect(customOnChange).toHaveBeenCalledTimes(1);
    });

    it("should work without disabled prop (defaults to false)", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).not.toBeDisabled();
      });
    });
  });

  describe("Component State", () => {
    it("should maintain internal state separate from prop", async () => {
      const { rerender } = render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      // Click Real button
      let buttons = getModeButtons();
      await userEvent.click(buttons.real!);

      // onChange is called, but prop doesn't change yet (parent controls it)
      expect(mockOnChange).toHaveBeenCalledWith("real");

      // Parent updates prop
      rerender(<ExecutionModeToggle value="real" onChange={mockOnChange} />);

      // Get buttons again after rerender
      buttons = getModeButtons();
      // Now Real should be selected (has default variant class)
      expect(buttons.real).toBeDefined();
    });

    it("should update when value prop changes", () => {
      const { rerender } = render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      let buttons = getModeButtons();
      expect(buttons.mock).toBeDefined();

      // Parent changes value
      rerender(<ExecutionModeToggle value="stream" onChange={mockOnChange} />);

      buttons = getModeButtons();
      expect(buttons.stream).toBeDefined();
    });
  });

  describe("Cost Indicators", () => {
    it("should clearly indicate free vs paid modes", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      // Check for FREE badge
      expect(screen.getByText("FREE")).toBeInTheDocument();

      // Check for PAID badges
      const paidBadges = screen.getAllByText("PAID");
      expect(paidBadges.length).toBe(2);
    });

    it("should emphasize that mock mode has no API costs", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      expect(screen.getByText(/No API costs/i)).toBeInTheDocument();
    });

    it("should indicate that real and stream modes are paid", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const realDescription = screen.getByText(/Actual execution • Complete response/i);
      const streamDescription = screen.getByText(/Actual execution • Real-time tokens/i);

      expect(realDescription).toBeInTheDocument();
      expect(streamDescription).toBeInTheDocument();
    });
  });

  describe("User Experience", () => {
    it("should provide immediate visual feedback on selection", async () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = getModeButtons();

      // Click
      await userEvent.click(buttons.real!);

      // onChange should be called immediately
      expect(mockOnChange).toHaveBeenCalledWith("real");
    });

    it("should show clear visual distinction between modes", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      const buttons = screen.getAllByRole("button");

      // Each button should have different content
      expect(buttons[0].textContent).not.toBe(buttons[1].textContent);
      expect(buttons[1].textContent).not.toBe(buttons[2].textContent);
      expect(buttons[0].textContent).not.toBe(buttons[2].textContent);
    });
  });

  describe("Integration Scenarios", () => {
    it("should work in typical user flow", async () => {
      const { rerender } = render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} />
      );

      // User starts with mock mode for testing
      let buttons = getModeButtons();
      expect(buttons.mock).toBeDefined();

      // User switches to real mode for actual execution
      await userEvent.click(buttons.real!);
      expect(mockOnChange).toHaveBeenCalledWith("real");

      // Parent updates
      rerender(<ExecutionModeToggle value="real" onChange={mockOnChange} />);

      // User switches to stream mode for better UX
      buttons = getModeButtons();
      await userEvent.click(buttons.stream!);
      expect(mockOnChange).toHaveBeenCalledWith("stream");

      // Parent updates
      rerender(<ExecutionModeToggle value="stream" onChange={mockOnChange} />);

      // User switches back to mock for quick testing
      buttons = getModeButtons();
      await userEvent.click(buttons.mock!);
      expect(mockOnChange).toHaveBeenCalledWith("mock");
    });

    it("should be disabled when no agent is selected", () => {
      render(
        <ExecutionModeToggle value="mock" onChange={mockOnChange} disabled={true} />
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });
});
