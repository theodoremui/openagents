/**
 * Tests for Agent Selector Component
 *
 * Tests that the AgentSelector properly discovers and displays
 * agents from config/open_agents.yaml via the backend API.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { AgentSelector } from "@/components/agent-selector";
import { ApiClient } from "@/lib/api-client";

// Mock API Client
jest.mock("@/lib/api-client", () => ({
  getApiClient: jest.fn(),
  ApiClientError: class ApiClientError extends Error {
    constructor(message: string, public statusCode?: number) {
      super(message);
      this.name = "ApiClientError";
    }
  },
}));

describe("AgentSelector", () => {
  const mockOnValueChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should load and display agents from config/open_agents.yaml", async () => {
    const mockAgents = [
      {
        id: "geo",
        name: "geo",
        display_name: "GeoAgent",
        description: "Geocoding agent",
        enabled: true,
      },
      {
        id: "finance",
        name: "finance",
        display_name: "FinanceAgent",
        description: "Financial data agent",
        enabled: true,
      },
      {
        id: "map",
        name: "map",
        display_name: "MapAgent",
        description: "Mapping agent",
        enabled: true,
      },
    ];

    const mockClient = {
      listAgents: jest.fn().mockResolvedValue(mockAgents),
    };

    (require("@/lib/api-client").getApiClient as jest.Mock).mockReturnValue(
      mockClient
    );

    render(<AgentSelector value="" onValueChange={mockOnValueChange} />);

    // Should show loading state
    expect(screen.getByText(/Loading agents/i)).toBeInTheDocument();

    // Wait for agents to load
    await waitFor(() => {
      expect(mockClient.listAgents).toHaveBeenCalled();
    });

    // Should display agent count
    await waitFor(() => {
      expect(screen.getByText(/3 agents loaded/i)).toBeInTheDocument();
    });

    // Should mention config file
    expect(screen.getByText(/config\/open_agents.yaml/i)).toBeInTheDocument();
  });

  it("should display agents from asdrp/agents/single", async () => {
    // These agents are defined in asdrp/agents/single/ and config/open_agents.yaml
    const mockAgents = [
      { id: "geo", name: "geo", display_name: "GeoAgent", enabled: true },
      { id: "finance", name: "finance", display_name: "FinanceAgent", enabled: true },
      { id: "map", name: "map", display_name: "MapAgent", enabled: true },
      { id: "yelp", name: "yelp", display_name: "YelpAgent", enabled: true },
      { id: "one", name: "one", display_name: "OneAgent", enabled: true },
    ];

    const mockClient = {
      listAgents: jest.fn().mockResolvedValue(mockAgents),
    };

    (require("@/lib/api-client").getApiClient as jest.Mock).mockReturnValue(
      mockClient
    );

    render(<AgentSelector value="" onValueChange={mockOnValueChange} />);

    await waitFor(() => {
      expect(screen.getByText(/5 agents loaded/i)).toBeInTheDocument();
    });
  });

  it("should auto-select first agent if none selected", async () => {
    const mockAgents = [
      { id: "geo", name: "geo", display_name: "GeoAgent", enabled: true },
    ];

    const mockClient = {
      listAgents: jest.fn().mockResolvedValue(mockAgents),
    };

    (require("@/lib/api-client").getApiClient as jest.Mock).mockReturnValue(
      mockClient
    );

    render(<AgentSelector value="" onValueChange={mockOnValueChange} />);

    await waitFor(() => {
      expect(mockOnValueChange).toHaveBeenCalledWith("geo");
    });
  });

  it("should sort agents by display name", async () => {
    const mockAgents = [
      { id: "z_agent", name: "z", display_name: "ZAgent", enabled: true },
      { id: "a_agent", name: "a", display_name: "AAgent", enabled: true },
      { id: "m_agent", name: "m", display_name: "MAgent", enabled: true },
    ];

    const mockClient = {
      listAgents: jest.fn().mockResolvedValue(mockAgents),
    };

    (require("@/lib/api-client").getApiClient as jest.Mock).mockReturnValue(
      mockClient
    );

    render(<AgentSelector value="" onValueChange={mockOnValueChange} />);

    // Should auto-select first in sorted order (AAgent)
    await waitFor(() => {
      expect(mockOnValueChange).toHaveBeenCalledWith("a_agent");
    });
  });

  it("should handle API errors gracefully", async () => {
    const mockClient = {
      listAgents: jest.fn().mockRejectedValue(
        new (require("@/lib/api-client").ApiClientError)(
          "Failed to load agents"
        )
      ),
    };

    (require("@/lib/api-client").getApiClient as jest.Mock).mockReturnValue(
      mockClient
    );

    render(<AgentSelector value="" onValueChange={mockOnValueChange} />);

    await waitFor(() => {
      expect(screen.getByText(/Error loading agents/i)).toBeInTheDocument();
      expect(screen.getByText(/Failed to load agents/i)).toBeInTheDocument();
    });
  });

  it("should handle empty agent list", async () => {
    const mockClient = {
      listAgents: jest.fn().mockResolvedValue([]),
    };

    (require("@/lib/api-client").getApiClient as jest.Mock).mockReturnValue(
      mockClient
    );

    render(<AgentSelector value="" onValueChange={mockOnValueChange} />);

    await waitFor(() => {
      expect(screen.getByText(/No agents available/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Check config\/open_agents.yaml/i)
      ).toBeInTheDocument();
    });
  });

  it("should log agent discovery in console (development)", async () => {
    // Temporarily set NODE_ENV to development to test logging behavior
    const originalEnv = process.env.NODE_ENV;
    Object.defineProperty(process, 'env', {
      value: { ...process.env, NODE_ENV: 'development' },
      writable: true,
      configurable: true,
    });
    
    const consoleSpy = jest.spyOn(console, "log").mockImplementation();

    const mockAgents = [
      { id: "geo", name: "geo", display_name: "GeoAgent", enabled: true },
    ];

    const mockClient = {
      listAgents: jest.fn().mockResolvedValue(mockAgents),
    };

    (require("@/lib/api-client").getApiClient as jest.Mock).mockReturnValue(
      mockClient
    );

    render(<AgentSelector value="" onValueChange={mockOnValueChange} />);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining("Loaded 1 agents from config/open_agents.yaml")
      );
    });

    consoleSpy.mockRestore();
    Object.defineProperty(process, 'env', {
      value: { ...process.env, NODE_ENV: originalEnv },
      writable: true,
      configurable: true,
    });
  });
});
