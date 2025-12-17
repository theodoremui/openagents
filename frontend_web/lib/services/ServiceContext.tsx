/**
 * Service Context for Dependency Injection
 *
 * Provides service instances throughout the React component tree.
 * Implements Dependency Injection pattern using React Context.
 *
 * Benefits:
 * - Centralized service management
 * - Easy testing (can inject mock services)
 * - Follows IoC (Inversion of Control) principle
 * - Clean separation of concerns
 */

"use client";

import React, { createContext, useContext, useMemo, ReactNode } from "react";
import { ApiClient, initializeApiClient } from "../api-client";
import { AgentExecutionService } from "./AgentExecutionService";
import { SessionService } from "./SessionService";
import type {
  IAgentExecutionService,
  ISessionService,
} from "./interfaces";

/**
 * Service container interface
 */
interface Services {
  apiClient: ApiClient;
  executionService: IAgentExecutionService;
  sessionService: ISessionService;
}

/**
 * Context for service injection
 */
const ServiceContext = createContext<Services | null>(null);

/**
 * Props for ServiceProvider
 */
interface ServiceProviderProps {
  children: ReactNode;
  /** Optional: Inject custom services (useful for testing) */
  services?: Partial<Services>;
}

/**
 * Service Provider Component
 *
 * Initializes and provides all services to child components.
 * Creates singleton instances for optimal performance.
 */
export function ServiceProvider({
  children,
  services: injectedServices,
}: ServiceProviderProps) {
  const services = useMemo<Services>(() => {
    // Use injected services if provided (for testing)
    if (injectedServices) {
      const apiClient =
        injectedServices.apiClient || initializeApiClient();

      return {
        apiClient,
        executionService:
          injectedServices.executionService ||
          new AgentExecutionService(apiClient),
        sessionService:
          injectedServices.sessionService || new SessionService(),
      };
    }

    // Production: Create service instances
    const apiClient = initializeApiClient();

    return {
      apiClient,
      executionService: new AgentExecutionService(apiClient),
      sessionService: new SessionService(),
    };
  }, [injectedServices]);

  return (
    <ServiceContext.Provider value={services}>
      {children}
    </ServiceContext.Provider>
  );
}

/**
 * Hook to access services
 *
 * Throws error if used outside ServiceProvider.
 */
export function useServices(): Services {
  const context = useContext(ServiceContext);

  if (!context) {
    throw new Error("useServices must be used within ServiceProvider");
  }

  return context;
}

/**
 * Hook to access API client
 */
export function useApiClient(): ApiClient {
  return useServices().apiClient;
}

/**
 * Hook to access execution service
 */
export function useExecutionService(): IAgentExecutionService {
  return useServices().executionService;
}

/**
 * Hook to access session service
 */
export function useSessionService(): ISessionService {
  return useServices().sessionService;
}
