# Design Document: MoE Map Rendering and YelpMCP Error Fix

## Overview

This design addresses two critical issues in the OpenAgents MoE orchestrator system that prevent users from receiving complete responses to location-based business queries:

1. **YelpMCP Agent Technical Errors**: The `yelp_mcp` agent fails to connect to its MCP server or returns technical errors instead of business data
2. **Interactive Map Rendering Failures**: The frontend fails to detect and render interactive map JSON payloads from MoE responses

The solution involves fixing MCP server connection issues, enhancing JSON block preservation in the synthesis process, improving frontend map detection, and adding comprehensive error handling and diagnostics.

## Architecture

### Current System Flow
```
User Query → MoE Orchestrator → Expert Selection → Parallel Execution → Result Synthesis → Frontend Rendering
                                      ↓                    ↓                    ↓                    ↓
                               [yelp, yelp_mcp, map]  [Agent Execution]  [LLM Synthesis]    [Map Detection]
```

### Problem Points Identified
1. **MCP Connection Failure**: `yelp_mcp` agent fails to establish MCP server connection
2. **JSON Block Loss**: LLM synthesis removes or modifies interactive map JSON blocks
3. **Frontend Detection**: Chat interface fails to detect map JSON in synthesized responses
4. **Error Propagation**: Technical errors cascade without proper fallback mechanisms

### Enhanced Architecture
```
User Query → MoE Orchestrator → Enhanced Expert Selection → Robust Parallel Execution → JSON-Preserving Synthesis → Enhanced Frontend Rendering
                                         ↓                           ↓                            ↓                            ↓
                              [Prioritized Agent List]    [MCP Health Checks]      [Deterministic JSON Preservation]   [Multi-Pattern Detection]
                                         ↓                           ↓                            ↓                            ↓
                              [Map Agent Prioritization]  [Fallback Mechanisms]    [Auto-Injection Fallbacks]      [Error Recovery]
```

## Components and Interfaces

### 1. YelpMCP Agent Connection Manager

**Location**: `asdrp/agents/mcp/yelp_mcp_agent.py`

**Responsibilities**:
- Validate MCP server configuration and environment variables
- Establish robust MCP server connections with proper error handling
- Provide detailed diagnostic logging for connection failures
- Implement connection health checks and retry mechanisms

**Key Methods**:
```python
def validate_mcp_environment() -> Dict[str, Any]:
    """Validate MCP server environment and configuration"""

def establish_mcp_connection() -> MCPServerStdio:
    """Establish MCP server connection with health checks"""

def diagnose_connection_failure(error: Exception) -> str:
    """Generate detailed diagnostic information for connection failures"""
```

### 2. Enhanced Result Mixer

**Location**: `asdrp/orchestration/moe/result_mixer.py`

**Responsibilities**:
- Preserve interactive map JSON blocks during LLM synthesis
- Implement deterministic JSON block extraction and preservation
- Provide auto-injection fallbacks when maps are missing
- Handle multiple map blocks intelligently

**Key Methods**:
```python
def extract_interactive_json_blocks(text: str) -> List[str]:
    """Extract interactive visualization JSON blocks from text"""

def preserve_json_blocks_in_synthesis(synthesized: str, expert_outputs: List[str]) -> str:
    """Ensure JSON blocks are preserved in synthesized output"""

def auto_inject_missing_maps(synthesized: str, query: str, expert_results: List[ExpertResult]) -> str:
    """Auto-inject maps when missing from visualization queries"""
```

### 3. Frontend Map Detection Engine

**Location**: `frontend_web/components/unified-chat-interface.tsx`

**Responsibilities**:
- Detect interactive map JSON blocks using multiple patterns
- Parse and validate map configurations
- Render InteractiveMap components with error recovery
- Handle malformed JSON gracefully

**Key Functions**:
```typescript
function detectInteractiveMapBlocks(content: string): InteractiveMapBlock[]
function validateMapConfiguration(config: any): boolean
function renderMapWithErrorRecovery(config: InteractiveMapConfig): JSX.Element
```

### 4. MoE Agent Selection Optimizer

**Location**: `asdrp/orchestration/moe/orchestrator.py`

**Responsibilities**:
- Prioritize map agent for visualization queries
- Ensure business + map agent combinations within k-limits
- Implement intelligent agent fallback strategies
- Provide detailed selection logging

**Key Methods**:
```python
def prioritize_agents_for_map_intent(query: str, agent_ids: List[str], max_k: int) -> List[str]:
    """Ensure map agent is included for visualization queries"""

def implement_agent_fallbacks(selected_agents: List[str], failed_agents: List[str]) -> List[str]:
    """Provide fallback agents when primary agents fail"""
```

## Data Models

### MCP Connection Status
```python
@dataclass
class MCPConnectionStatus:
    """Status of MCP server connection"""
    connected: bool
    server_name: str
    command: List[str]
    working_directory: str
    environment_status: Dict[str, bool]  # API keys, etc.
    error_message: Optional[str] = None
    diagnostic_info: Optional[Dict[str, Any]] = None
```

### Interactive Map Block
```python
@dataclass
class InteractiveMapBlock:
    """Detected interactive map JSON block"""
    raw_json: str
    parsed_config: Dict[str, Any]
    map_type: str  # "route", "location", "places"
    valid: bool
    error_message: Optional[str] = None
```

### Agent Execution Result
```python
@dataclass
class EnhancedExpertResult:
    """Enhanced expert execution result with diagnostics"""
    expert_id: str
    success: bool
    output: str
    latency_ms: float
    tools_used: List[str]
    mcp_status: Optional[MCPConnectionStatus] = None
    json_blocks_detected: List[InteractiveMapBlock] = None
    error: Optional[str] = None
    diagnostic_info: Optional[Dict[str, Any]] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: MCP Connection Establishment
*For any* YelpMCP agent initialization with valid configuration, the MCP server connection should be established successfully without connection errors
**Validates: Requirements 1.1**

### Property 2: Business Data Structure Integrity
*For any* successful yelp_mcp agent execution, the returned data should contain all required business fields (names, ratings, addresses, coordinates)
**Validates: Requirements 1.2**

### Property 3: Error Message Clarity
*For any* yelp_mcp agent API error, the system should return a clear error message indicating the specific failure reason
**Validates: Requirements 1.3**

### Property 4: JSON Block Preservation
*For any* expert response containing an interactive_map JSON block, the synthesized output should contain that exact JSON block unchanged
**Validates: Requirements 2.1**

### Property 5: Map Configuration Parsing
*For any* message containing a valid interactive_map JSON block, the frontend should successfully parse and extract the map configuration
**Validates: Requirements 3.1**

### Property 6: Interactive Map Rendering
*For any* valid map configuration, the frontend should render an InteractiveMap component with the provided configuration
**Validates: Requirements 3.2**

### Property 7: Marker Display Accuracy
*For any* map configuration with lat/lng markers, the system should display markers at the correct locations with visible labels
**Validates: Requirements 3.3**

### Property 8: Address Geocoding
*For any* map configuration with address-only markers, the system should geocode addresses to coordinates before rendering
**Validates: Requirements 3.4**

### Property 9: Agent Selection Logic
*For any* query containing both business and location terms, the system should select both business experts and location experts
**Validates: Requirements 4.1**

### Property 10: Map Agent Prioritization
*For any* query explicitly requesting visualization, the system should include the map agent in the selection
**Validates: Requirements 4.2**

### Property 11: Parallel Execution Fallback
*For any* scenario where one business agent fails, the system should use the response from the other business agent without failing the entire query
**Validates: Requirements 4.5**

### Property 12: Business Agent Fallback
*For any* yelp_mcp agent failure, the system should use the response from the yelp agent as a fallback
**Validates: Requirements 5.1**

### Property 13: Partial Success Handling
*For any* scenario where the map agent fails but business agents succeed, the system should return business data without map visualization
**Validates: Requirements 5.3**

### Property 14: Frontend Error Recovery
*For any* malformed JSON block or rendering failure, the system should display an error message and fall back to showing raw JSON
**Validates: Requirements 3.5, 5.5**

### Property 15: Execution Logging Completeness
*For any* expert execution, the system should log execution time and success/failure status for each expert
**Validates: Requirements 6.4**

### Property 16: Configuration Validation
*For any* invalid MoE configuration, the system should prevent orchestrator startup and display specific validation errors
**Validates: Requirements 7.5**

## Error Handling

### MCP Connection Errors
- **Environment Validation**: Check for required environment variables (YELP_API_KEY) before attempting connection
- **Connection Health Checks**: Verify MCP server process starts successfully and responds to basic commands
- **Detailed Diagnostics**: Log command, working directory, environment status, and stderr output on failures
- **Graceful Degradation**: Fall back to non-MCP yelp agent when yelp_mcp fails

### JSON Block Preservation Errors
- **Deterministic Extraction**: Use regex patterns to extract JSON blocks before synthesis
- **Post-Synthesis Validation**: Check if JSON blocks are present in synthesized output
- **Auto-Injection Fallbacks**: Generate maps from coordinates or addresses when blocks are missing
- **Multiple Block Handling**: Preserve all unique interactive map blocks

### Frontend Rendering Errors
- **Multi-Pattern Detection**: Use multiple regex patterns to detect JSON blocks in various formats
- **Configuration Validation**: Validate map configuration structure before rendering
- **Error Boundaries**: Wrap InteractiveMap components in error boundaries
- **Fallback Display**: Show raw JSON with error message when rendering fails

### Agent Selection Errors
- **Map Agent Prioritization**: Ensure map agent is included for visualization queries within k-limits
- **Fallback Strategies**: Replace failed agents with working alternatives
- **Selection Logging**: Log agent selection decisions and confidence scores

## Testing Strategy

### Unit Testing Approach
- **MCP Connection Tests**: Mock MCP server processes and test connection establishment
- **JSON Parsing Tests**: Test JSON block extraction with various formats and edge cases
- **Map Rendering Tests**: Test InteractiveMap component with different configurations
- **Agent Selection Tests**: Test selection logic with various query types

### Property-Based Testing Approach
- **Connection Property Tests**: Generate random MCP configurations and verify connection behavior
- **JSON Preservation Tests**: Generate expert responses with JSON blocks and verify preservation
- **Map Configuration Tests**: Generate random map configurations and verify rendering
- **Query Selection Tests**: Generate queries with business/location terms and verify agent selection

### Integration Testing
- **End-to-End Map Rendering**: Test complete flow from query to rendered map
- **Fallback Mechanism Tests**: Test agent failures and verify fallback behavior
- **Multi-Agent Coordination**: Test parallel execution and result synthesis

### Error Scenario Testing
- **Missing API Keys**: Test behavior with missing YELP_API_KEY and GOOGLE_MAPS_API_KEY
- **MCP Server Failures**: Test various MCP server startup and connection failures
- **Malformed JSON**: Test frontend handling of malformed interactive map JSON
- **Network Timeouts**: Test behavior under network timeout conditions

## Implementation Phases

### Phase 1: MCP Connection Diagnostics and Fixes
1. Enhance YelpMCP agent initialization with comprehensive environment validation
2. Add detailed MCP server connection diagnostics and logging
3. Implement connection health checks and retry mechanisms
4. Add fallback to non-MCP yelp agent when MCP fails

### Phase 2: JSON Block Preservation Enhancement
1. Strengthen synthesis prompt with explicit JSON preservation instructions
2. Implement deterministic JSON block extraction and preservation
3. Add post-synthesis validation to ensure JSON blocks are present
4. Implement auto-injection fallbacks for missing maps

### Phase 3: Frontend Map Detection and Rendering
1. Enhance JSON block detection with multiple regex patterns
2. Improve map configuration validation and error handling
3. Add error boundaries and fallback display for rendering failures
4. Test with various JSON formats and edge cases

### Phase 4: Agent Selection Optimization
1. Implement map agent prioritization for visualization queries
2. Enhance agent selection logging and diagnostics
3. Add intelligent fallback strategies for failed agents
4. Optimize k-limit handling to ensure map agent inclusion

### Phase 5: Comprehensive Testing and Validation
1. Implement property-based tests for all correctness properties
2. Add integration tests for end-to-end map rendering
3. Test error scenarios and fallback mechanisms
4. Performance testing and optimization

## Dependencies

### External Dependencies
- **OpenAI API**: Required for LLM synthesis (existing)
- **Google Maps API**: Required for map rendering and geocoding (existing)
- **Yelp Fusion API**: Required for business data (existing)
- **MCP Protocol**: Required for yelp_mcp agent communication (existing)

### Internal Dependencies
- **Agent Factory**: For creating and managing agent instances (existing)
- **MapTools**: For generating interactive map JSON (existing)
- **Result Mixer**: For synthesizing expert responses (existing)
- **Frontend Chat Interface**: For rendering maps (existing)

### Configuration Dependencies
- **Environment Variables**: YELP_API_KEY, GOOGLE_MAPS_API_KEY, OPENAI_API_KEY
- **MoE Configuration**: config/moe.yaml with synthesis prompt and agent definitions
- **Agent Configuration**: config/open_agents.yaml with yelp_mcp agent definition

## Performance Considerations

### Latency Optimization
- **Parallel Execution**: Execute yelp and yelp_mcp agents in parallel for redundancy
- **Connection Pooling**: Reuse MCP server connections across requests
- **Caching**: Cache geocoding results and map configurations
- **Fast Failure**: Fail fast on MCP connection errors to avoid timeouts

### Resource Management
- **MCP Server Lifecycle**: Properly manage MCP server process lifecycle
- **Memory Usage**: Limit JSON block size and number of markers
- **Connection Limits**: Respect API rate limits for Yelp and Google Maps
- **Error Recovery**: Implement circuit breakers for failing services

### Scalability
- **Stateless Design**: Keep agents stateless for horizontal scaling
- **Configuration Validation**: Validate configuration at startup to prevent runtime errors
- **Monitoring**: Add metrics for connection success rates and response times
- **Graceful Degradation**: Provide partial functionality when services are unavailable