# MoE Map Rendering Fix - Deployment Checklist

## Overview
This document provides a comprehensive checklist for deploying the MoE map rendering and YelpMCP error fixes to production.

## Pre-Deployment Validation

### 1. Environment Variables Required

#### Backend Environment Variables
- [ ] `YELP_API_KEY` - Required for Yelp business search functionality
  - Obtain from: https://www.yelp.com/developers/v3/manage_app
  - Format: Bearer token string
  - Test: `echo $YELP_API_KEY` should return a non-empty value

- [ ] `GOOGLE_API_KEY` - Required for map rendering and geocoding
  - Obtain from: https://console.cloud.google.com/apis/credentials
  - Required APIs: Maps JavaScript API, Geocoding API
  - Test: `echo $GOOGLE_MAPS_API_KEY` should return a non-empty value

- [ ] `OPENAI_API_KEY` - Required for LLM synthesis and agent execution
  - Obtain from: https://platform.openai.com/api-keys
  - Test: `echo $OPENAI_API_KEY` should return a non-empty value

#### Frontend Environment Variables
- [ ] `NEXT_PUBLIC_GOOGLE_API_KEY` - Required for frontend map rendering
  - Same key as backend GOOGLE_API_KEY
  - Must be prefixed with `NEXT_PUBLIC_` for Next.js
  - Location: `frontend_web/.env.local`

### 2. Configuration Files Validation

#### MoE Configuration (`config/moe.yaml`)
- [ ] Verify all expert agents are defined:
  - `yelp` - Non-MCP Yelp agent (fallback)
  - `yelp_mcp` - MCP-based Yelp agent (primary)
  - `map` - Map visualization agent
  - `geo` - Geocoding agent
  - `one` - Fallback agent

- [ ] Verify synthesis prompt template contains required variables:
  - `{weighted_results}` - Expert outputs
  - `{query}` - User query
  - JSON preservation instructions

- [ ] Verify model configurations:
  - `selection` model for expert selection
  - `synthesis` model for result mixing
  - `fallback` model for fallback agent

#### Agent Configuration (`config/open_agents.yaml`)
- [ ] Verify `yelp_mcp` agent configuration:
  - MCP server command: `uvx yelp-mcp`
  - Working directory: `./yelp-mcp`
  - Transport type: `stdio`
  - Disabled: `false`

- [ ] Verify `map` agent has MapTools configured
- [ ] Verify `yelp` agent exists as fallback

### 3. Test Suite Execution

#### Run Core MoE Tests
```bash
python -m pytest tests/asdrp/orchestration/moe/ -v
```
Expected: 182+ tests passing

#### Run MCP Agent Tests
```bash
python -m pytest tests/asdrp/agents/mcp/ -v
```
Expected: All property-based tests passing

#### Run Integration Tests
```bash
python -m pytest tests/asdrp/orchestration/moe/test_integration_end_to_end.py -v
```
Expected: End-to-end map rendering tests passing

### 4. Manual Validation with Original Failing Query

Run the following test query to validate the complete fix:

```bash
python test_final_validation.py
```

**Expected Results:**
1. Query: "Place the top 3 greek restaurants in San Francisco on a detailed map"
2. MoE selects: `yelp_mcp`, `yelp`, `map` agents
3. Response contains:
   - Business data (names, ratings, addresses)
   - Interactive map JSON block with `"type": "interactive_map"`
   - Coordinates for all 3 restaurants
4. Frontend renders:
   - Interactive Google Map
   - 3 markers with restaurant names
   - Proper zoom and center

## Deployment Steps

### 1. Backend Deployment

#### Heroku Deployment
```bash
# Set environment variables
heroku config:set YELP_API_KEY="your_yelp_api_key" --app your-app-name
heroku config:set GOOGLE_API_KEY="your_google_maps_key" --app your-app-name
heroku config:set OPENAI_API_KEY="your_openai_key" --app your-app-name

# Deploy
git push heroku main

# Verify deployment
heroku logs --tail --app your-app-name
```

#### Docker Deployment
```bash
# Build image
docker build -t openagents-backend .

# Run with environment variables
docker run -d \
  -e YELP_API_KEY="your_yelp_api_key" \
  -e GOOGLE_API_KEY="your_google_maps_key" \
  -e OPENAI_API_KEY="your_openai_key" \
  -p 8000:8000 \
  openagents-backend
```

### 2. Frontend Deployment

#### Vercel Deployment
```bash
# Set environment variables in Vercel dashboard
NEXT_PUBLIC_GOOGLE_API_KEY=your_google_maps_key

# Deploy
vercel --prod
```

#### Manual Deployment
```bash
cd frontend_web
npm run build
npm start
```

### 3. Post-Deployment Validation

#### Health Checks
- [ ] Backend health endpoint: `GET /health`
- [ ] Frontend loads without errors
- [ ] MoE orchestrator initializes successfully

#### Functional Tests
- [ ] Test business search query: "Find pizza restaurants in San Francisco"
- [ ] Test map visualization query: "Show me coffee shops in Seattle on a map"
- [ ] Test combined query: "Place the top 3 greek restaurants in San Francisco on a detailed map"

#### Error Scenarios
- [ ] Test with missing YELP_API_KEY (should fallback to non-MCP yelp agent)
- [ ] Test with invalid query (should return clear error message)
- [ ] Test with malformed JSON (frontend should show error recovery)

## Troubleshooting Guide

### Issue: YelpMCP Agent Returns "Technical Issue" Error

**Symptoms:**
- MoE response contains "technical issue" instead of business data
- Logs show MCP connection failures

**Diagnosis:**
```bash
# Check if YELP_API_KEY is set
echo $YELP_API_KEY

# Check MCP server can start
cd yelp-mcp
uvx yelp-mcp

# Check logs for MCP connection errors
grep "MCP" logs/server.log
```

**Solutions:**
1. Verify YELP_API_KEY is set and valid
2. Ensure `uvx` and `uv` are installed: `pip install uv`
3. Check yelp-mcp directory exists and has correct structure
4. Verify MCP server configuration in `config/open_agents.yaml`

### Issue: Interactive Maps Not Rendering

**Symptoms:**
- Response contains JSON block but no map displays
- Frontend shows raw JSON instead of map

**Diagnosis:**
```bash
# Check if GOOGLE_MAPS_API_KEY is set in frontend
cat frontend_web/.env.local | grep GOOGLE_MAPS_API_KEY

# Check browser console for errors
# Look for: "Google Maps JavaScript API error"
```

**Solutions:**
1. Verify `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is set in frontend `.env.local`
2. Ensure Google Maps JavaScript API is enabled in Google Cloud Console
3. Check API key restrictions (HTTP referrers, API restrictions)
4. Verify JSON block format matches expected schema

### Issue: JSON Blocks Missing from Synthesized Response

**Symptoms:**
- Individual expert responses contain JSON blocks
- Final synthesized response missing JSON blocks

**Diagnosis:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check synthesis logs
grep "JSON block" logs/server.log
grep "synthesis" logs/server.log
```

**Solutions:**
1. Verify synthesis prompt template includes JSON preservation instructions
2. Check result mixer is using enhanced JSON preservation logic
3. Verify post-synthesis validation is enabled
4. Check auto-injection fallback is working

### Issue: Agent Selection Not Including Map Agent

**Symptoms:**
- Map visualization queries don't select map agent
- Only business agents selected

**Diagnosis:**
```bash
# Check agent selection logs
grep "Final selected agents" logs/server.log
grep "map agent" logs/server.log
```

**Solutions:**
1. Verify map intent detection is working
2. Check agent prioritization logic
3. Ensure k-limit allows map agent inclusion
4. Verify map agent is configured in `config/moe.yaml`

## Configuration Reference

### Minimal Working Configuration

#### `config/moe.yaml`
```yaml
experts:
  - id: yelp_mcp
    agent_name: yelp_mcp
    capabilities: ["business_search", "restaurant_search"]
  - id: yelp
    agent_name: yelp
    capabilities: ["business_search", "restaurant_search"]
  - id: map
    agent_name: map
    capabilities: ["map_visualization", "geocoding"]
  - id: geo
    agent_name: geo
    capabilities: ["geocoding", "location_search"]

expert_groups:
  - name: business
    experts: [yelp_mcp, yelp]
  - name: location
    experts: [map, geo]

models:
  selection:
    provider: openai
    model: gpt-4
  synthesis:
    provider: openai
    model: gpt-4
  fallback:
    provider: openai
    model: gpt-3.5-turbo

fallback_agent: one
top_k_experts: 3
```

#### `config/open_agents.yaml`
```yaml
agents:
  yelp_mcp:
    mcp_servers:
      - name: yelp
        command: uvx
        args: [yelp-mcp]
        working_directory: ./yelp-mcp
        transport: stdio
        disabled: false
        env:
          YELP_API_KEY: ${YELP_API_KEY}
```

## Success Criteria

### Functional Requirements
- [x] YelpMCP agent successfully returns business data
- [x] Interactive map JSON blocks preserved through synthesis
- [x] Frontend detects and renders interactive maps
- [x] Fallback mechanisms work when agents fail
- [x] Clear error messages for configuration issues

### Performance Requirements
- [ ] MoE response time < 5 seconds for typical queries
- [ ] MCP connection establishment < 1 second
- [ ] Map rendering < 2 seconds after response received

### Reliability Requirements
- [ ] System handles missing API keys gracefully
- [ ] Fallback to non-MCP yelp agent when MCP fails
- [ ] Partial success when map agent fails
- [ ] Frontend error recovery for malformed JSON

## Rollback Plan

If issues occur in production:

1. **Immediate Rollback:**
   ```bash
   git revert HEAD
   git push heroku main
   ```

2. **Disable MCP Agent:**
   ```yaml
   # In config/open_agents.yaml
   yelp_mcp:
     mcp_servers:
       - disabled: true
   ```

3. **Use Non-MCP Yelp Agent:**
   ```yaml
   # In config/moe.yaml
   experts:
     - id: yelp  # Remove yelp_mcp
   ```

## Monitoring and Alerts

### Key Metrics to Monitor
- MCP connection success rate
- Agent selection distribution
- JSON block preservation rate
- Map rendering success rate
- Response latency (p50, p95, p99)

### Recommended Alerts
- MCP connection failure rate > 10%
- JSON block missing rate > 5%
- Map rendering failure rate > 5%
- Response latency p95 > 10 seconds

## Documentation Links

- [MoE Orchestrator Documentation](../../docs/moe/moe_orchestrator.md)
- [YelpMCP Agent Documentation](../../asdrp/agents/mcp/yelp_mcp_agent.py)
- [Interactive Map Documentation](../../docs/tricks/interactive_maps.md)
- [Configuration Guide](../../docs/agents/agent_configuration.md)

## Sign-off

- [ ] All tests passing
- [ ] Manual validation completed
- [ ] Environment variables configured
- [ ] Configuration files validated
- [ ] Deployment successful
- [ ] Post-deployment validation passed
- [ ] Monitoring and alerts configured

**Deployed by:** _________________  
**Date:** _________________  
**Version:** _________________
