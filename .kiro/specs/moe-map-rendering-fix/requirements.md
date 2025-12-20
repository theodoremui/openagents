# Requirements Document: MoE Map Rendering and YelpMCP Error Fix

## Introduction

This specification addresses two critical issues in the OpenAgents MoE (Mixture of Experts) orchestrator system:

1. **YelpMCP Agent Technical Issue Error**: The `yelp_mcp` agent consistently returns "technical issue" errors instead of Yelp business results when selected by the MoE orchestrator
2. **Interactive Map Rendering Failure**: The frontend fails to render interactive maps from JSON payloads returned by the MoE orchestrator, despite the JSON being correctly formatted

These issues prevent users from getting complete responses when asking location-based business queries like "Place the top 3 greek restaurants in San Francisco on a detailed map."

## Glossary

- **MoE Orchestrator**: The Mixture of Experts orchestration system that selects and combines multiple specialist agents to answer user queries
- **YelpMCP Agent**: An agent that uses the Model Context Protocol (MCP) to access Yelp Fusion AI capabilities for business search
- **Interactive Map**: A Google Maps-based visualization component that renders business locations with markers and labels
- **JSON Payload**: A structured data format containing map configuration with type "interactive_map"
- **Synthesis Prompt**: The LLM prompt template used by the MoE orchestrator to combine expert responses
- **MapTools**: A set of tools that generate interactive map JSON payloads
- **Frontend Chat Interface**: The React-based UI component that displays agent responses and renders interactive content

## Requirements

### Requirement 1: YelpMCP Agent Error Diagnosis and Fix

**User Story:** As a user querying for restaurant recommendations, I want the YelpMCP agent to return valid Yelp business results instead of technical errors, so that I can see accurate restaurant information.

#### Acceptance Criteria

1. WHEN the MoE orchestrator selects the yelp_mcp agent THEN the system SHALL successfully connect to the Yelp MCP server without connection errors
2. WHEN the yelp_mcp agent executes a business search query THEN the system SHALL return valid Yelp business data including names, ratings, addresses, and coordinates
3. WHEN the yelp_mcp agent encounters an API error THEN the system SHALL provide a clear error message indicating the specific failure reason (e.g., missing API key, rate limit, invalid query)
4. WHEN the YELP_API_KEY environment variable is missing or invalid THEN the system SHALL fail fast with a descriptive error message during agent initialization
5. WHEN the MCP server process fails to start THEN the system SHALL log detailed diagnostic information including command, working directory, and environment variables

### Requirement 2: Interactive Map JSON Preservation in Synthesis

**User Story:** As a user requesting map visualizations, I want the MoE orchestrator to preserve interactive map JSON blocks in synthesized responses, so that I can see visual maps in the chat interface.

#### Acceptance Criteria

1. WHEN an expert agent (map, geo, or yelp_mcp) returns a response containing a ```json code block with "type": "interactive_map" THEN the MoE result mixer SHALL preserve that exact JSON block in the synthesized output
2. WHEN the synthesis prompt combines multiple expert responses THEN the system SHALL explicitly instruct the LLM to copy JSON blocks verbatim without modification
3. WHEN the synthesized response contains an interactive map JSON block THEN the system SHALL place it at an appropriate location in the markdown output (typically at the end after text descriptions)
4. WHEN multiple experts return map JSON blocks THEN the system SHALL preserve all unique map blocks or merge them intelligently based on content
5. WHEN the LLM attempts to summarize or paraphrase a JSON block THEN the system SHALL detect this and regenerate the synthesis with stronger preservation instructions

### Requirement 3: Frontend Interactive Map Detection and Rendering

**User Story:** As a user viewing agent responses, I want interactive map JSON payloads to be automatically detected and rendered as visual maps, so that I can see business locations on an interactive Google Map.

#### Acceptance Criteria

1. WHEN the chat interface receives a message containing a ```json code block with "type": "interactive_map" THEN the system SHALL parse the JSON and extract the map configuration
2. WHEN the map configuration is extracted THEN the system SHALL render an InteractiveMap component with the provided configuration
3. WHEN the map configuration contains markers with lat/lng coordinates THEN the system SHALL display markers at those locations with visible labels
4. WHEN the map configuration contains markers with only addresses THEN the system SHALL geocode the addresses to coordinates before rendering
5. WHEN the JSON block is malformed or missing required fields THEN the system SHALL display an error message and fall back to showing the raw JSON
6. WHEN multiple JSON blocks exist in a single message THEN the system SHALL render all valid interactive map blocks

### Requirement 4: MoE Agent Selection Optimization

**User Story:** As a system administrator, I want the MoE orchestrator to select the most appropriate agents for location-based business queries, so that users receive complete responses with both data and visualizations.

#### Acceptance Criteria

1. WHEN a user query contains both business search terms (e.g., "restaurants") and location terms (e.g., "San Francisco") THEN the system SHALL select both business experts (yelp, yelp_mcp) and location experts (map, geo)
2. WHEN a user query explicitly requests visualization (e.g., "show on map", "place on map") THEN the system SHALL prioritize the map agent in the selection
3. WHEN the top_k_experts limit is reached THEN the system SHALL ensure the map agent is included if visualization is requested
4. WHEN multiple business agents are selected (yelp and yelp_mcp) THEN the system SHALL execute both in parallel and use the successful response
5. WHEN one business agent fails THEN the system SHALL use the response from the other business agent without failing the entire query

### Requirement 5: Error Handling and Fallback Mechanisms

**User Story:** As a user, I want the system to gracefully handle agent failures and provide partial results, so that I still receive useful information even when some agents fail.

#### Acceptance Criteria

1. WHEN the yelp_mcp agent fails with a technical error THEN the system SHALL use the response from the yelp agent (non-MCP) as a fallback
2. WHEN all business agents fail THEN the system SHALL return a clear error message indicating the business search service is unavailable
3. WHEN the map agent fails but business agents succeed THEN the system SHALL return business data without the map visualization
4. WHEN the synthesis step fails THEN the system SHALL return the raw expert responses with minimal formatting
5. WHEN the frontend fails to render a map THEN the system SHALL display the raw JSON with an error message explaining the rendering failure

### Requirement 6: Diagnostic Logging and Observability

**User Story:** As a developer debugging agent issues, I want comprehensive logging of MCP connections, agent executions, and synthesis steps, so that I can quickly identify and fix problems.

#### Acceptance Criteria

1. WHEN the yelp_mcp agent initializes THEN the system SHALL log the MCP server command, working directory, and environment variable status
2. WHEN an MCP server connection fails THEN the system SHALL log the stderr output from the MCP server process
3. WHEN the MoE orchestrator selects experts THEN the system SHALL log the selected agent IDs and their confidence scores
4. WHEN expert execution completes THEN the system SHALL log the execution time and success/failure status for each expert
5. WHEN the synthesis step processes expert responses THEN the system SHALL log whether JSON blocks were detected and preserved

### Requirement 7: Configuration Validation and Documentation

**User Story:** As a system administrator, I want clear documentation and validation of MoE configuration, so that I can correctly configure agents and avoid common misconfigurations.

#### Acceptance Criteria

1. WHEN the MoE orchestrator starts THEN the system SHALL validate that all referenced agents exist in the agent configuration
2. WHEN the synthesis_prompt is loaded THEN the system SHALL validate that it contains the required template variables ({weighted_results}, {query})
3. WHEN the YELP_API_KEY is missing THEN the system SHALL provide documentation links for obtaining and configuring the API key
4. WHEN the GOOGLE_MAPS_API_KEY is missing THEN the system SHALL display a clear error in the frontend with setup instructions
5. WHEN configuration validation fails THEN the system SHALL prevent the orchestrator from starting and display specific validation errors
