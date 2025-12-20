# Troubleshooting Guide - MoE Map Rendering Fix

## Overview
This guide helps diagnose and fix common issues with the MoE map rendering and YelpMCP error fixes.

## Quick Diagnostic Commands

### 1. Check System Status
```bash
# Check if all services are running
python -c "
import os
print('Environment Variables:')
for var in ['YELP_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY']:
    status = '✅' if os.getenv(var) else '❌'
    print(f'  {var}: {status}')
"

# Test MoE configuration
python -c "
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.agents.agent_factory import AgentFactory
try:
    factory = AgentFactory()
    orchestrator = MoEOrchestrator.create_default('config/moe.yaml', factory)
    print('✅ MoE orchestrator initialized successfully')
except Exception as e:
    print(f'❌ MoE initialization failed: {e}')
"
```

### 2. Test Individual Components
```bash
# Test YelpMCP agent
python -c "
from asdrp.agents.mcp.yelp_mcp_agent import YelpMCPAgent
try:
    agent = YelpMCPAgent.create()
    print('✅ YelpMCP agent created successfully')
except Exception as e:
    print(f'❌ YelpMCP agent failed: {e}')
"

# Test MCP server connection
cd yelp-mcp && uvx yelp-mcp --help
```

## Common Issues and Solutions

### Issue 1: YelpMCP Agent Returns "Technical Issue" Error

#### Symptoms
- MoE response contains "I encountered a technical issue" instead of business data
- Logs show MCP connection failures
- YelpMCP agent not returning valid Yelp results

#### Diagnosis Steps
```bash
# 1. Check YELP_API_KEY
echo "YELP_API_KEY: ${YELP_API_KEY:0:10}..." # Shows first 10 chars

# 2. Test MCP server manually
cd yelp-mcp
uvx yelp-mcp

# 3. Check MCP server logs
python -c "
from asdrp.agents.mcp.yelp_mcp_agent import YelpMCPAgent
import asyncio
async def test():
    try:
        agent = YelpMCPAgent.create()
        result = await agent.run('Find pizza restaurants in San Francisco')
        print(f'Result: {result.output[:200]}...')
    except Exception as e:
        print(f'Error: {e}')
asyncio.run(test())
"
```

#### Solutions
1. **Missing YELP_API_KEY:**
   ```bash
   export YELP_API_KEY="your_yelp_api_key_here"
   ```

2. **Invalid YELP_API_KEY:**
   - Verify key at https://www.yelp.com/developers/v3/manage_app
   - Ensure it's the API Key, not Client ID

3. **MCP Server Not Starting:**
   ```bash
   # Install uv if missing
   pip install uv
   
   # Test MCP server
   cd yelp-mcp
   uvx yelp-mcp --version
   ```

4. **Working Directory Issues:**
   - Ensure `yelp-mcp` directory exists
   - Check `config/open_agents.yaml` working_directory path

5. **Fallback to Non-MCP Yelp:**
   ```yaml
   # Temporarily disable MCP in config/open_agents.yaml
   yelp_mcp:
     mcp_servers:
       - disabled: true
   ```

### Issue 2: Interactive Maps Not Rendering in Frontend

#### Symptoms
- Response contains JSON block but no map displays
- Frontend shows raw JSON instead of interactive map
- Browser console shows Google Maps errors

#### Diagnosis Steps
```bash
# 1. Check frontend environment variable
cat frontend_web/.env.local | grep GOOGLE_API_KEY

# 2. Check JSON block format
python -c "
import re, json
response = '''Your MoE response here'''
pattern = r'```json\s*(\{.*?\})\s*```'
matches = re.findall(pattern, response, re.DOTALL)
for match in matches:
    try:
        data = json.loads(match)
        if data.get('type') == 'interactive_map':
            print('✅ Valid interactive map JSON found')
            print(f'Markers: {len(data.get(\"config\", {}).get(\"markers\", []))}')
        else:
            print(f'❌ JSON type: {data.get(\"type\")}')
    except:
        print('❌ Invalid JSON format')
"

# 3. Test in browser console
# Open browser dev tools and run:
# console.log('Google Maps API loaded:', typeof google !== 'undefined')
```

#### Solutions
1. **Missing Frontend API Key:**
   ```bash
   # Create or update frontend_web/.env.local
   echo "NEXT_PUBLIC_GOOGLE_API_KEY=your_google_maps_key" >> frontend_web/.env.local
   
   # Restart frontend
   cd frontend_web && npm run dev
   ```

2. **Google Maps API Not Enabled:**
   - Go to https://console.cloud.google.com/apis/library
   - Enable "Maps JavaScript API"
   - Enable "Geocoding API"

3. **API Key Restrictions:**
   - Check API key restrictions in Google Cloud Console
   - Add your domain to HTTP referrers
   - Ensure APIs are not restricted

4. **Invalid JSON Format:**
   ```bash
   # Test JSON block extraction
   python -c "
   from asdrp.orchestration.moe.result_mixer import ResultMixer
   mixer = ResultMixer()
   # Test with your response
   "
   ```

### Issue 3: JSON Blocks Missing from Synthesized Response

#### Symptoms
- Individual expert responses contain JSON blocks
- Final synthesized response missing JSON blocks
- LLM removes or modifies JSON during synthesis

#### Diagnosis Steps
```bash
# 1. Check synthesis prompt template
python -c "
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
config = MoEConfigLoader.load_config('config/moe.yaml')
print('Synthesis prompt contains JSON preservation:')
prompt = config.synthesis_prompt
print('✅' if 'JSON' in prompt and 'preserve' in prompt.lower() else '❌')
"

# 2. Test JSON block extraction
python -c "
from asdrp.orchestration.moe.result_mixer import ResultMixer
mixer = ResultMixer()
test_response = '''
Here are some restaurants:
```json
{\"type\": \"interactive_map\", \"config\": {\"markers\": []}}
```
'''
blocks = mixer.extract_interactive_json_blocks(test_response)
print(f'Extracted {len(blocks)} JSON blocks')
"
```

#### Solutions
1. **Update Synthesis Prompt:**
   ```yaml
   # In config/moe.yaml
   synthesis_prompt: |
     Combine the following expert responses into a comprehensive answer.
     
     CRITICAL: If any expert response contains a ```json code block with "type": "interactive_map", 
     you MUST copy that exact JSON block verbatim into your response. Do not modify, summarize, 
     or paraphrase JSON blocks - copy them exactly as they appear.
     
     Expert responses:
     {weighted_results}
     
     User query: {query}
   ```

2. **Enable Post-Synthesis Validation:**
   ```python
   # This is already implemented in the enhanced result mixer
   # Verify it's working by checking logs
   ```

3. **Test Auto-Injection Fallback:**
   ```bash
   # Check if auto-injection is working
   grep "auto-injection" logs/server.log
   ```

### Issue 4: Agent Selection Not Including Map Agent

#### Symptoms
- Map visualization queries don't select map agent
- Only business agents selected for map queries
- No interactive maps generated

#### Diagnosis Steps
```bash
# 1. Check agent selection logs
grep "Final selected agents" logs/server.log | tail -5

# 2. Test map intent detection
python -c "
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
query = 'Show restaurants on a map'
# Check if query triggers map agent selection
"

# 3. Check available agents
python -c "
from asdrp.agents.agent_factory import AgentFactory
factory = AgentFactory()
agents = factory.list_available_agents()
print('Available agents:', agents)
print('Map agent available:', 'map' in agents)
"
```

#### Solutions
1. **Enable Map Agent Prioritization:**
   ```python
   # This is already implemented in the enhanced orchestrator
   # Verify configuration includes map agent
   ```

2. **Check K-Limit Configuration:**
   ```yaml
   # In config/moe.yaml
   top_k_experts: 3  # Ensure this allows map agent
   ```

3. **Verify Map Agent Configuration:**
   ```yaml
   # In config/moe.yaml
   experts:
     - id: map
       agent_name: map
       capabilities: ["map_visualization", "geocoding"]
   ```

### Issue 5: Configuration Validation Errors

#### Symptoms
- MoE orchestrator fails to start
- Configuration validation errors
- Missing agent or model configurations

#### Diagnosis Steps
```bash
# 1. Validate YAML syntax
python -c "
import yaml
try:
    with open('config/moe.yaml') as f:
        config = yaml.safe_load(f)
    print('✅ YAML syntax valid')
except Exception as e:
    print(f'❌ YAML syntax error: {e}')
"

# 2. Check required fields
python -c "
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
try:
    config = MoEConfigLoader.load_config('config/moe.yaml')
    print('✅ Configuration loaded successfully')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

#### Solutions
1. **Fix Missing Model Configurations:**
   ```yaml
   # In config/moe.yaml
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
   ```

2. **Add Missing Expert Definitions:**
   ```yaml
   experts:
     - id: yelp_mcp
       agent_name: yelp_mcp
       capabilities: ["business_search"]
     - id: yelp
       agent_name: yelp
       capabilities: ["business_search"]
     - id: map
       agent_name: map
       capabilities: ["map_visualization"]
   ```

3. **Verify Agent Availability:**
   ```bash
   # Check if all referenced agents exist
   python -c "
   from asdrp.agents.agent_factory import AgentFactory
   factory = AgentFactory()
   available = factory.list_available_agents()
   required = ['yelp', 'yelp_mcp', 'map', 'geo', 'one']
   missing = [agent for agent in required if agent not in available]
   if missing:
       print(f'❌ Missing agents: {missing}')
   else:
       print('✅ All required agents available')
   "
   ```

## Performance Issues

### Issue: Slow Response Times

#### Diagnosis
```bash
# Check response times in logs
grep "Request completed" logs/server.log | tail -10

# Check individual agent performance
grep "Expert execution took" logs/server.log | tail -10
```

#### Solutions
1. **Enable Performance Monitoring:**
   ```python
   # Already implemented in enhanced orchestrator
   # Check logs for performance metrics
   ```

2. **Optimize Agent Selection:**
   ```yaml
   # Reduce top_k_experts if too many agents selected
   top_k_experts: 2
   ```

3. **Enable Caching:**
   ```python
   # Caching is already implemented
   # Check cache hit rates in logs
   ```

## Debugging Tools

### 1. Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python your_application.py
```

### 2. Test Individual Components
```bash
# Test MCP connection
python debug_mcp_connection.py

# Test JSON preservation
python debug_json_preservation.py

# Test agent selection
python debug_agent_selection.py
```

### 3. Validate Complete Flow
```bash
# Run end-to-end test
python test_final_validation.py

# Run specific test query
python -c "
import asyncio
from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.agents.agent_factory import AgentFactory

async def test():
    factory = AgentFactory()
    orchestrator = MoEOrchestrator.create_default('config/moe.yaml', factory)
    result = await orchestrator.route_query('Find pizza restaurants in San Francisco on a map')
    print(f'Response length: {len(result.response)}')
    print(f'Experts used: {result.experts_used}')
    print(f'Contains JSON: {\"interactive_map\" in result.response}')

asyncio.run(test())
"
```

## Emergency Procedures

### 1. Disable MCP Agent (Quick Fix)
```yaml
# In config/open_agents.yaml
yelp_mcp:
  mcp_servers:
    - disabled: true
```

### 2. Use Fallback Agent Only
```yaml
# In config/moe.yaml
experts:
  - id: one  # Only use fallback agent
    agent_name: one
    capabilities: ["general"]
```

### 3. Rollback Configuration
```bash
git checkout HEAD~1 config/
git checkout HEAD~1 asdrp/orchestration/moe/
```

## Getting Help

### 1. Collect Diagnostic Information
```bash
# Create diagnostic report
python -c "
import os, sys
print('=== DIAGNOSTIC REPORT ===')
print(f'Python version: {sys.version}')
print(f'Working directory: {os.getcwd()}')
print('Environment variables:')
for var in ['YELP_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY']:
    value = os.getenv(var)
    print(f'  {var}: {\"SET\" if value else \"NOT SET\"}')

try:
    from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
    print('✅ MoE orchestrator import successful')
except Exception as e:
    print(f'❌ MoE orchestrator import failed: {e}')
"
```

### 2. Check Recent Logs
```bash
tail -50 logs/server.log | grep -E "(ERROR|WARNING|MoE|MCP)"
```

### 3. Contact Support
Include in your support request:
- Diagnostic report output
- Recent log entries
- Specific error messages
- Steps to reproduce the issue
- Expected vs actual behavior

## Prevention

### 1. Regular Health Checks
```bash
# Add to cron job or monitoring
python test_final_validation.py
```

### 2. Configuration Validation
```bash
# Run before deployment
python -c "
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
MoEConfigLoader.load_config('config/moe.yaml')
print('Configuration valid')
"
```

### 3. API Key Monitoring
```bash
# Test API keys regularly
python -c "
import os, requests
yelp_key = os.getenv('YELP_API_KEY')
if yelp_key:
    response = requests.get(
        'https://api.yelp.com/v3/businesses/search',
        headers={'Authorization': f'Bearer {yelp_key}'},
        params={'term': 'test', 'location': 'San Francisco', 'limit': 1}
    )
    print(f'Yelp API: {\"✅ OK\" if response.status_code == 200 else \"❌ FAIL\"}')
"
```