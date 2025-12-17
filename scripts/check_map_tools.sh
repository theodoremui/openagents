#!/bin/bash

###############################################################################
# check_map_tools.sh
#
# Quick diagnostic script to check if MapAgent has get_static_map_url tool.
#
# Usage:
#   ./scripts/check_map_tools.sh
#
# Requirements:
#   - Backend server running on localhost:8000
#   - API key configured in .env or passed as OPENAGENTS_API_KEY
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${OPENAGENTS_API_KEY:-your_api_key_here}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          MapAgent Tool Availability Diagnostic                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if server is running
echo -e "${YELLOW}1. Checking if backend server is running...${NC}"
if curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Server is running at $API_URL${NC}"
else
    echo -e "${RED}   ❌ Server is NOT running at $API_URL${NC}"
    echo -e "${RED}   Please start the server with: cd server && python -m server.main${NC}"
    exit 1
fi
echo ""

# Check MapAgent tools
echo -e "${YELLOW}2. Fetching MapAgent tools...${NC}"
RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/agents/map/tools" 2>/dev/null)

if [ $? -ne 0 ]; then
    echo -e "${RED}   ❌ Failed to fetch tools (check API key)${NC}"
    echo -e "${RED}   API Key: $API_KEY${NC}"
    exit 1
fi

# Parse response
TOOL_COUNT=$(echo "$RESPONSE" | grep -o '"tool_count":[0-9]*' | grep -o '[0-9]*')
HAS_STATIC_MAP=$(echo "$RESPONSE" | grep -o '"has_get_static_map_url":[a-z]*' | grep -o '[a-z]*')

echo -e "   Total tools: ${BLUE}$TOOL_COUNT${NC}"
echo ""

# Extract tool names
echo -e "${YELLOW}3. Tool list:${NC}"
echo "$RESPONSE" | grep -o '"[a-z_]*"' | grep -v "agent_id\|agent_name\|tool_count\|tool_names\|has_get_static_map_url\|timestamp" | sed 's/"//g' | nl

echo ""

# Check for get_static_map_url
echo -e "${YELLOW}4. Checking for get_static_map_url...${NC}"
if echo "$RESPONSE" | grep -q "get_static_map_url"; then
    echo -e "${GREEN}   ✅ SUCCESS: get_static_map_url is AVAILABLE${NC}"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  MapAgent should now be able to display map images!               ║${NC}"
    echo -e "${GREEN}║                                                                    ║${NC}"
    echo -e "${GREEN}║  Try asking: 'Show me a map view from SF to San Carlos'           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}   ❌ FAIL: get_static_map_url is MISSING${NC}"
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  Backend server needs to be RESTARTED                              ║${NC}"
    echo -e "${RED}║                                                                    ║${NC}"
    echo -e "${RED}║  The tool was added after the server started, so it hasn't         ║${NC}"
    echo -e "${RED}║  been loaded yet. Please restart:                                 ║${NC}"
    echo -e "${RED}║                                                                    ║${NC}"
    echo -e "${RED}║  1. Stop server: Ctrl+C in server terminal                        ║${NC}"
    echo -e "${RED}║  2. Restart: cd server && python -m server.main                    ║${NC}"
    echo -e "${RED}║  3. Run this script again to verify                               ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
