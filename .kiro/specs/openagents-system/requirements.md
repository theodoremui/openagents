# Requirements Document

## Introduction

OpenAgents is a production-ready multi-agent orchestration platform that enables developers to create, manage, and deploy intelligent AI agents with an intuitive web interface. The system provides a full-stack solution with clean architecture principles, supporting multiple execution modes (Mock, Real, Stream) for flexible development and deployment workflows.

## Glossary

- **Agent**: An AI-powered entity that processes user input and generates responses using language models
- **AgentProtocol**: A Python Protocol defining the interface that all agents must implement
- **AgentFactory**: A factory class responsible for creating and initializing agent instances
- **Tool**: A function or capability that an agent can use to perform specific tasks
- **ToolsMeta**: A metaclass that automatically discovers and registers tools from class methods
- **MCP (Model Context Protocol)**: A standardized protocol for connecting AI models to external data sources and tools
- **Session Memory**: Persistent conversation history maintained across multiple agent interactions
- **Execution Mode**: The method by which an agent processes requests (Mock, Real, or Stream)
- **Mock Mode**: Fast testing mode that returns simulated responses without making actual API calls
- **Real Mode**: Production mode that makes actual OpenAI API calls and returns complete responses
- **Stream Mode**: Real-time mode that streams tokens as they are generated for optimal user experience
- **Backend**: The FastAPI server that provides REST API endpoints for agent operations
- **Frontend**: The Next.js web application that provides the user interface
- **YAML Configuration**: The configuration file that defines all available agents and their settings
- **Dependency Injection**: A design pattern where services are provided to components via React Context

## Requirements

### Requirement 1: Agent Protocol and Factory System

**User Story:** As a developer, I want a standardized way to create and manage agents, so that I can easily add new agents without modifying core system code.

#### Acceptance Criteria

1. THE System SHALL define an AgentProtocol that specifies required attributes (name, instructions) for all agents
2. THE System SHALL provide an AgentFactory that creates agent instances based on configuration
3. WHEN a developer requests an agent by name, THE AgentFactory SHALL dynamically import the agent module and invoke its factory function
4. THE AgentFactory SHALL support session memory creation and caching for agents
5. WHEN an agent name is invalid or disabled, THE System SHALL raise an AgentException with a descriptive error message

### Requirement 2: Configuration-Driven Architecture

**User Story:** As a system administrator, I want to configure agents through YAML files, so that I can modify agent behavior without changing code.

#### Acceptance Criteria

1. THE System SHALL load agent configurations from a YAML file (config/open_agents.yaml)
2. WHEN the configuration file is updated, THE System SHALL reload configurations without requiring a restart in development mode
3. THE System SHALL validate YAML configuration structure and required fields
4. THE System SHALL support configuration of model settings (name, temperature, max_tokens) for each agent
5. THE System SHALL support configuration of session memory settings (type, database_path, enabled) for each agent
6. THE System SHALL support configuration of MCP server settings (command, working_directory, transport) for MCP-enabled agents
7. WHEN an agent is marked as disabled in configuration, THE System SHALL exclude it from the available agents list

### Requirement 3: Tools System with Automatic Discovery

**User Story:** As a developer, I want tools to be automatically discovered from class methods, so that I don't have to manually register each tool.

#### Acceptance Criteria

1. THE System SHALL provide a ToolsMeta metaclass that automatically discovers public class methods
2. WHEN a class uses ToolsMeta as its metaclass, THE System SHALL create a spec_functions list containing method names
3. WHEN a class uses ToolsMeta as its metaclass, THE System SHALL create a tool_list containing wrapped function tools
4. THE System SHALL support a _setup_class() hook for class-level initialization
5. THE System SHALL support a _get_excluded_methods() hook to exclude specific methods from tool discovery
6. THE System SHALL exclude default methods (__init__, __new__, etc.) from tool discovery

### Requirement 4: MCP Integration

**User Story:** As a developer, I want to integrate external MCP servers with agents, so that agents can access tools and resources beyond their built-in functionality.

#### Acceptance Criteria

1. THE System SHALL support MCP server integration via stdio transport
2. WHEN an agent has MCP configuration enabled, THE System SHALL create an MCPServerStdio instance with the configured command
3. THE System SHALL manage MCP server subprocess lifecycle (start, monitor, shutdown)
4. WHEN the application shuts down, THE System SHALL gracefully terminate all running MCP servers
5. THE System SHALL support hybrid agents that combine MCP server tools with direct tools
6. WHEN an MCP server fails to start, THE System SHALL raise an AgentException with diagnostic information

### Requirement 5: Session Memory Management

**User Story:** As a user, I want my conversations with agents to be remembered, so that I can have contextual multi-turn interactions.

#### Acceptance Criteria

1. THE System SHALL support SQLite-based session memory for conversation history
2. THE System SHALL support both in-memory and file-based SQLite sessions
3. WHEN session memory is enabled for an agent, THE System SHALL create or retrieve a session object
4. THE System SHALL cache session objects by session_id to enable reuse across multiple calls
5. WHEN session_id is provided, THE System SHALL use it to maintain separate conversation histories
6. THE System SHALL support stateless agents by setting session memory type to "none"

### Requirement 6: REST API Endpoints

**User Story:** As a frontend developer, I want well-defined REST API endpoints, so that I can build user interfaces that interact with agents.

#### Acceptance Criteria

1. THE System SHALL provide a GET /agents endpoint that returns a list of all enabled agents
2. THE System SHALL provide a GET /agents/{agent_id} endpoint that returns detailed information about a specific agent
3. THE System SHALL provide a POST /agents/{agent_id}/simulate endpoint for mock execution without API calls
4. THE System SHALL provide a POST /agents/{agent_id}/chat endpoint for real execution with complete responses
5. THE System SHALL provide a POST /agents/{agent_id}/chat/stream endpoint for streaming execution with token-by-token responses
6. THE System SHALL provide a GET /health endpoint for health checks
7. THE System SHALL provide a GET /graph endpoint for agent relationship visualization
8. THE System SHALL provide GET and PUT /config/agents endpoints for configuration management

### Requirement 7: Authentication and Security

**User Story:** As a system administrator, I want secure API access, so that unauthorized users cannot access the system.

#### Acceptance Criteria

1. THE System SHALL support API key authentication via X-API-Key header
2. WHEN AUTH_ENABLED is true, THE System SHALL validate API keys for all protected endpoints
3. WHEN an invalid API key is provided, THE System SHALL return a 401 Unauthorized response
4. THE System SHALL support multiple API keys configured via environment variables
5. THE System SHALL support CORS configuration for cross-origin requests
6. THE System SHALL support trusted host middleware for production deployments
7. WHEN AUTH_ENABLED is false, THE System SHALL allow unauthenticated access for development

### Requirement 8: Frontend User Interface

**User Story:** As a user, I want an intuitive web interface, so that I can easily interact with agents without technical knowledge.

#### Acceptance Criteria

1. THE System SHALL provide a web interface built with Next.js 14 and TypeScript
2. THE System SHALL display a list of available agents in a dropdown selector
3. THE System SHALL provide three execution modes (Mock, Real, Stream) with visual indicators
4. THE System SHALL display agent configuration details in a sidebar panel
5. THE System SHALL provide a chat interface for sending messages and viewing responses
6. THE System SHALL support markdown rendering for agent responses including images, code blocks, and tables
7. THE System SHALL provide auto-scrolling behavior that respects manual user scrolling
8. THE System SHALL display loading states and error messages appropriately

### Requirement 9: Service Layer Architecture

**User Story:** As a frontend developer, I want a clean service layer, so that business logic is separated from UI components.

#### Acceptance Criteria

1. THE System SHALL provide an AgentExecutionService that encapsulates execution logic
2. THE System SHALL provide a SessionService that manages session IDs and persistence
3. THE System SHALL use dependency injection via React Context to provide services to components
4. THE System SHALL implement the Strategy pattern for execution mode selection
5. THE System SHALL provide a singleton ApiClient for HTTP communication
6. THE System SHALL support mocking of services for testing purposes

### Requirement 10: Streaming Response Handling

**User Story:** As a user, I want to see agent responses in real-time, so that I get immediate feedback during long-running operations.

#### Acceptance Criteria

1. THE System SHALL support Server-Sent Events (SSE) for streaming responses
2. WHEN stream mode is selected, THE System SHALL display tokens as they are generated
3. THE System SHALL handle different chunk types (metadata, token, step, done, error)
4. THE System SHALL accumulate streamed tokens into a complete message
5. THE System SHALL provide visual feedback during streaming (typing indicator, progress)
6. WHEN streaming completes, THE System SHALL mark the message as complete
7. WHEN streaming encounters an error, THE System SHALL display an error message and allow retry

### Requirement 11: Configuration Editor

**User Story:** As a system administrator, I want to edit agent configurations through the UI, so that I can make changes without accessing the server filesystem.

#### Acceptance Criteria

1. THE System SHALL provide a YAML editor with syntax highlighting
2. THE System SHALL validate YAML syntax before saving
3. WHEN configuration is saved, THE System SHALL reload the agent factory
4. THE System SHALL provide a graph visualization of agent relationships
5. THE System SHALL support backup of previous configurations
6. WHEN validation fails, THE System SHALL display specific error messages

### Requirement 12: Error Handling and Diagnostics

**User Story:** As a developer, I want comprehensive error handling, so that I can quickly diagnose and fix issues.

#### Acceptance Criteria

1. THE System SHALL provide an AgentException class for agent-related errors
2. WHEN an error occurs, THE System SHALL include the agent name in the exception
3. THE System SHALL provide a GET /agents/{agent_id}/tools endpoint for diagnostic tool inspection
4. THE System SHALL log errors with appropriate severity levels
5. THE System SHALL return structured error responses with error codes and timestamps
6. THE System SHALL handle network errors, timeout errors, and API errors gracefully

### Requirement 13: Testing Infrastructure

**User Story:** As a developer, I want comprehensive test coverage, so that I can confidently make changes without breaking functionality.

#### Acceptance Criteria

1. THE System SHALL provide unit tests for all service classes
2. THE System SHALL provide component tests for all React components
3. THE System SHALL provide integration tests for API client functionality
4. THE System SHALL achieve greater than 90% code coverage on core logic
5. THE System SHALL support mocking of external dependencies (API calls, MCP servers)
6. THE System SHALL provide test utilities for common testing patterns

### Requirement 14: Geographic and Mapping Tools

**User Story:** As a user, I want agents that can work with geographic data and maps, so that I can get location-based information and visualizations.

#### Acceptance Criteria

1. THE System SHALL provide GeoTools for geocoding (address to coordinates) and reverse geocoding (coordinates to address)
2. THE System SHALL provide MapTools for Google Maps integration (routes, places, static maps, interactive maps)
3. WHEN a user requests a route, THE System SHALL generate a visual map with accurate driving directions
4. THE System SHALL extract encoded polylines from Google Maps API to display routes that follow real roads
5. THE System SHALL support different map types (roadmap, satellite, terrain, hybrid)
6. THE System SHALL provide distance and travel time calculations
7. THE System SHALL support nearby place searches with visual map display

### Requirement 15: Financial Data Tools

**User Story:** As a user, I want agents that can access financial data, so that I can get stock prices and company information.

#### Acceptance Criteria

1. THE System SHALL provide FinanceTools for accessing stock market data
2. THE System SHALL support retrieving current stock prices by symbol
3. THE System SHALL support retrieving historical stock data with configurable time periods
4. THE System SHALL support retrieving company information and fundamentals
5. WHEN financial data is unavailable, THE System SHALL return appropriate error messages

### Requirement 16: Local Business Search

**User Story:** As a user, I want agents that can search for local businesses, so that I can find restaurants, shops, and services.

#### Acceptance Criteria

1. THE System SHALL provide YelpTools for Yelp API integration
2. THE System SHALL support business search by location, category, and keywords
3. THE System SHALL support retrieving detailed business information by ID
4. THE System SHALL support retrieving business reviews and ratings
5. THE System SHALL provide YelpMCPAgent for next-generation search via Yelp Fusion AI
6. WHEN using YelpMCPAgent, THE System SHALL support multi-turn conversations with chat_id
7. WHEN using YelpMCPAgent, THE System SHALL support itinerary and progressive route planning

### Requirement 17: Performance Optimization

**User Story:** As a user, I want fast response times, so that I can work efficiently without waiting.

#### Acceptance Criteria

1. THE System SHALL return mock responses in less than 200ms
2. THE System SHALL support code splitting by route in the frontend
3. THE System SHALL cache session objects to avoid repeated creation
4. THE System SHALL use singleton pattern for API client to avoid repeated initialization
5. THE System SHALL support lazy loading of heavy dependencies (Monaco Editor, ReactFlow)
6. THE System SHALL optimize bundle size to less than 100 kB for initial load

### Requirement 18: Deployment and Operations

**User Story:** As a DevOps engineer, I want easy deployment options, so that I can run the system in various environments.

#### Acceptance Criteria

1. THE System SHALL support running via convenience scripts (run_server.sh)
2. THE System SHALL support Docker deployment with docker-compose
3. THE System SHALL support environment-specific configuration via .env files
4. THE System SHALL provide health check endpoints for monitoring
5. THE System SHALL support graceful shutdown with cleanup of resources
6. THE System SHALL log startup information including loaded agents and MCP servers
