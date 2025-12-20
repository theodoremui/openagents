# Configuration Requirements for MoE Map Rendering Fix

## Overview
This document outlines the configuration requirements for the MoE map rendering and YelpMCP error fixes.

## Environment Variables

### Required for Production Deployment

#### Backend Environment Variables
```bash
# Yelp API for business search
export YELP_API_KEY="your_yelp_api_key_here"

# Google Maps API for geocoding and map rendering
export GOOGLE_API_KEY="your_google_api_key_here"

# OpenAI API for LLM synthesis
export OPENAI_API_KEY="your_openai_api_key_here"
```

#### Frontend Environment Variables
```bash
# Create frontend_web/.env.local
NEXT_PUBLIC_GOOGLE_API_KEY=your_google_api_key_here
```

### API Key Setup Instructions

#### 1. Yelp API Key
1. Visit https://www.yelp.com/developers/v3/manage_app
2. Create a new app or use existing app
3. Copy the API Key (not Client ID)
4. Set as `YELP_API_KEY` environment variable

#### 2. Google Maps API Key
1. Visit https://console.cloud.google.com/apis/credentials
2. Create a new project or select existing project
3. Enable the following APIs:
   - Maps JavaScript API
   - Geocoding API
4. Create credentials (API Key)
5. Set as `GOOGLE_MAPS_API_KEY` environment variable
6. Set as `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in frontend

#### 3. OpenAI API Key
1. Visit https://platform.openai.com/api-keys
2. Create a new API key
3. Set as `OPENAI_API_KEY` environment variable

## Configuration Files

### MoE Configuration (config/moe.yaml)
The MoE configuration has been enhanced with:
- Proper expert agent definitions
- Enhanced synthesis prompt with JSON preservation
- Fallback mechanisms
- Performance optimizations

### Agent Configuration (config/open_agents.yaml)
The agent configuration includes:
- YelpMCP agent with MCP server setup
- Proper environment variable references
- Fallback agent configurations

## Validation Commands

### Test Environment Setup
```bash
# Check if all required environment variables are set
python -c "
import os
required = ['YELP_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY']
missing = [var for var in required if not os.getenv(var)]
if missing:
    print(f'Missing: {missing}')
else:
    print('All environment variables set')
"
```

### Test MoE Configuration
```bash
# Run configuration validation
python -c "
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
try:
    config = MoEConfigLoader.load_config('config/moe.yaml')
    print('✅ MoE configuration valid')
except Exception as e:
    print(f'❌ MoE configuration error: {e}')
"
```

### Test Agent Configuration
```bash
# Run agent factory validation
python -c "
from asdrp.agents.agent_factory import AgentFactory
try:
    factory = AgentFactory()
    agents = factory.list_available_agents()
    print(f'✅ Available agents: {agents}')
except Exception as e:
    print(f'❌ Agent configuration error: {e}')
"
```

### Test Complete System
```bash
# Run the final validation script
python test_final_validation.py
```

## Troubleshooting

### Common Issues

#### 1. "Missing required environment variable"
**Solution:** Set the missing environment variable as described above.

#### 2. "MCP server connection failed"
**Symptoms:** YelpMCP agent returns "technical issue" errors
**Solutions:**
- Ensure `uvx` is installed: `pip install uv`
- Check YELP_API_KEY is valid
- Verify yelp-mcp directory exists

#### 3. "Google Maps JavaScript API error"
**Symptoms:** Maps don't render in frontend
**Solutions:**
- Check NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is set in frontend/.env.local
- Verify Google Maps JavaScript API is enabled
- Check API key restrictions

#### 4. "Configuration validation failed"
**Symptoms:** MoE orchestrator fails to start
**Solutions:**
- Verify config/moe.yaml syntax
- Check all referenced agents exist
- Ensure model configurations are complete

## Development vs Production

### Development Environment
- Can use placeholder API keys for testing (some features may not work)
- Local configuration files
- Debug logging enabled

### Production Environment
- All API keys must be valid and properly configured
- Environment variables set in deployment platform
- Production logging levels
- Monitoring and alerting configured

## Security Considerations

### API Key Security
- Never commit API keys to version control
- Use environment variables or secure secret management
- Rotate API keys regularly
- Set appropriate API key restrictions

### Frontend Security
- NEXT_PUBLIC_ variables are exposed to browser
- Only include necessary API keys in frontend
- Use domain restrictions for Google Maps API key

## Deployment Platforms

### Heroku
```bash
heroku config:set YELP_API_KEY="your_key" --app your-app
heroku config:set GOOGLE_API_KEY="your_key" --app your-app
heroku config:set OPENAI_API_KEY="your_key" --app your-app
```

### Docker
```dockerfile
ENV YELP_API_KEY=your_key
ENV GOOGLE_API_KEY=your_key
ENV OPENAI_API_KEY=your_key
```

### Vercel (Frontend)
Set environment variables in Vercel dashboard:
- NEXT_PUBLIC_GOOGLE_API_KEY

## Monitoring

### Health Checks
- MCP server connection status
- API key validity
- Agent availability
- Configuration validation

### Metrics to Track
- MCP connection success rate
- API call success rates
- Response latency
- Error rates by component

## Support

For configuration issues:
1. Check this documentation
2. Review deployment checklist
3. Run validation scripts
4. Check application logs
5. Contact development team

## Version Information

This configuration is for MoE Map Rendering Fix v1.0
- Supports YelpMCP agent with fallback
- Enhanced JSON block preservation
- Interactive map rendering
- Comprehensive error handling