# Implementation Plan: MoE Map Rendering and YelpMCP Error Fix

## Task Overview

Convert the feature design into a series of prompts for a code-generation LLM that will implement each step with incremental progress. Each task builds on previous tasks and focuses on writing, modifying, or testing code to fix the MoE orchestrator issues.

## Implementation Tasks

- [x] 1. Diagnose and fix YelpMCP agent MCP connection issues
  - Investigate current MCP server connection failures in yelp_mcp agent
  - Add comprehensive environment variable validation and diagnostic logging
  - Implement robust MCP server connection with health checks and retry mechanisms
  - Add fallback to non-MCP yelp agent when MCP connection fails
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 1.1 Write property test for MCP connection establishment
  - **Property 1: MCP Connection Establishment**
  - **Validates: Requirements 1.1**

- [x] 1.2 Write property test for business data structure integrity
  - **Property 2: Business Data Structure Integrity**
  - **Validates: Requirements 1.2**

- [x] 1.3 Write property test for error message clarity
  - **Property 3: Error Message Clarity**
  - **Validates: Requirements 1.3**

- [x] 2. Enhance JSON block preservation in MoE result synthesis
  - Strengthen synthesis prompt template with explicit JSON preservation instructions
  - Implement deterministic JSON block extraction using regex patterns
  - Add post-synthesis validation to ensure interactive map JSON blocks are preserved
  - Implement auto-injection fallbacks when maps are missing from visualization queries
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2.1 Write property test for JSON block preservation
  - **Property 4: JSON Block Preservation**
  - **Validates: Requirements 2.1**

- [x] 3. Improve frontend interactive map detection and rendering
  - Enhance JSON block detection in unified-chat-interface.tsx with multiple regex patterns
  - Improve map configuration validation and error handling
  - Add error boundaries and fallback display for rendering failures
  - Test with various JSON formats and malformed data
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3.1 Write property test for map configuration parsing
  - **Property 5: Map Configuration Parsing**
  - **Validates: Requirements 3.1**

- [x] 3.2 Write property test for interactive map rendering
  - **Property 6: Interactive Map Rendering**
  - **Validates: Requirements 3.2**

- [x] 3.3 Write property test for marker display accuracy
  - **Property 7: Marker Display Accuracy**
  - **Validates: Requirements 3.3**

- [x] 3.4 Write property test for address geocoding
  - **Property 8: Address Geocoding**
  - **Validates: Requirements 3.4**

- [x] 4. Optimize MoE agent selection for map visualization queries
  - Enhance agent selection logic to prioritize map agent for visualization queries
  - Implement intelligent k-limit handling to ensure map agent inclusion
  - Add comprehensive agent selection logging and diagnostics
  - Implement fallback strategies when primary agents fail
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4.1 Write property test for agent selection logic
  - **Property 9: Agent Selection Logic**
  - **Validates: Requirements 4.1**

- [x] 4.2 Write property test for map agent prioritization
  - **Property 10: Map Agent Prioritization**
  - **Validates: Requirements 4.2**

- [x] 4.3 Write property test for parallel execution fallback
  - **Property 11: Parallel Execution Fallback**
  - **Validates: Requirements 4.5**

- [x] 5. Implement comprehensive error handling and fallback mechanisms
  - Add business agent fallback (yelp_mcp → yelp) when MCP fails
  - Implement partial success handling (business data without map when map agent fails)
  - Add frontend error recovery for malformed JSON and rendering failures
  - Enhance error messaging with specific failure reasons and documentation links
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5.1 Write property test for business agent fallback
  - **Property 12: Business Agent Fallback**
  - **Validates: Requirements 5.1**

- [x] 5.2 Write property test for partial success handling
  - **Property 13: Partial Success Handling**
  - **Validates: Requirements 5.3**

- [x] 5.3 Write property test for frontend error recovery
  - **Property 14: Frontend Error Recovery**
  - **Validates: Requirements 3.5, 5.5**

- [x] 6. Add comprehensive diagnostic logging and observability
  - Implement detailed MCP connection logging with command, directory, and environment status
  - Add expert selection and execution logging with timing and success/failure status
  - Implement synthesis step logging for JSON block detection and preservation
  - Add configuration validation logging with specific error messages
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6.1 Write property test for execution logging completeness
  - **Property 15: Execution Logging Completeness**
  - **Validates: Requirements 6.4**

- [x] 7. Enhance configuration validation and documentation
  - Add startup validation for agent existence and configuration completeness
  - Validate synthesis prompt template for required variables
  - Implement clear error messages with documentation links for missing API keys
  - Add configuration validation that prevents orchestrator startup on errors
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7.1 Write property test for configuration validation
  - **Property 16: Configuration Validation**
  - **Validates: Requirements 7.5**

- [x] 8. Integration testing and end-to-end validation
  - Test complete flow from business+map query to rendered interactive map
  - Validate MCP connection fixes with actual Yelp API calls
  - Test JSON block preservation through entire synthesis pipeline
  - Verify frontend map rendering with various configuration formats
  - Test all fallback mechanisms and error scenarios
  - _Requirements: All requirements integration testing_

- [x] 8.1 Write integration tests for end-to-end map rendering
  - Test complete query → MoE → synthesis → frontend rendering flow
  - Verify business data + interactive map rendering works correctly
  - Test with various query types and map configurations

- [x] 8.2 Write integration tests for error scenarios
  - Test missing API keys, MCP server failures, malformed JSON
  - Verify fallback mechanisms work correctly
  - Test partial success scenarios

- [x] 9. Performance optimization and monitoring
  - Optimize MCP connection establishment and reuse
  - Add performance metrics for agent selection and execution timing
  - Implement connection pooling and caching where appropriate
  - Add circuit breakers for failing services
  - _Performance and scalability improvements_

- [x] 10. Final validation and deployment preparation
  - Ensure all tests pass, ask the user if questions arise
  - Validate fixes with the original failing query: "Place the top 3 greek restaurants in San Francisco on a detailed map"
  - Document configuration requirements and troubleshooting steps
  - Prepare deployment checklist with environment variable requirements

## Task Execution Notes

### Critical Dependencies
- Tasks 1-2 must be completed before task 8 (integration testing)
- Task 3 (frontend) can be developed in parallel with tasks 1-2 (backend)
- Task 4 (agent selection) depends on understanding from task 1 (MCP diagnostics)
- Task 5 (error handling) builds on all previous tasks

### Testing Strategy
- Property-based tests are required for comprehensive validation of all correctness properties
- Integration tests in task 8 are critical for validating the complete fix
- Each task should include unit tests for the specific functionality being implemented

### Validation Criteria
- YelpMCP agent successfully returns business data instead of technical errors
- Interactive map JSON blocks are preserved through MoE synthesis
- Frontend successfully detects and renders interactive maps from MoE responses
- Fallback mechanisms work when individual agents fail
- Comprehensive logging provides clear diagnostics for troubleshooting

### Success Metrics
- Original failing query "Place the top 3 greek restaurants in San Francisco on a detailed map" returns both business data and rendered interactive map
- MoE orchestrator selects appropriate agents (yelp_mcp, yelp, map) for business+visualization queries
- System gracefully handles agent failures with appropriate fallbacks
- Clear error messages and diagnostics help with troubleshooting configuration issues