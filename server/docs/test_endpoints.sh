#!/bin/bash

##############################################################################
# Quick Test Script for Agent Execution Endpoints
#
# Tests all three endpoint types:
# 1. /simulate - Mock responses (no API calls)
# 2. /chat - Real execution (complete response)
# 3. /chat/stream - Real execution (streaming)
#
# Usage:
#   ./test_endpoints.sh [API_KEY]
#
# If API_KEY not provided, will try to read from .env file
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${1}"

# Try to read API key from .env if not provided
if [ -z "$API_KEY" ]; then
    if [ -f ".env" ]; then
        API_KEY=$(grep DEFAULT_API_KEY .env | cut -d= -f2 | tr -d ' ')
        echo -e "${YELLOW}Using API key from .env${NC}"
    fi
fi

if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: API_KEY not provided and not found in .env${NC}"
    echo "Usage: $0 [API_KEY]"
    exit 1
fi

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}Testing Agent Execution Endpoints${NC}"
echo -e "${BLUE}Base URL: $BASE_URL${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo

##############################################################################
# Test 1: Mock Simulation (/simulate)
##############################################################################

echo -e "${YELLOW}Test 1: Mock Simulation (no API calls)${NC}"
echo -e "${BLUE}Endpoint: POST $BASE_URL/agents/geo/simulate${NC}"
echo

RESPONSE=$(curl -s -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": "Test input for mock simulation"}' \
  "$BASE_URL/agents/geo/simulate")

# Check if response contains "mode": "mock"
if echo "$RESPONSE" | jq -e '.metadata.mode == "mock"' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Mock simulation successful${NC}"
    echo -e "  Response: $(echo "$RESPONSE" | jq -r '.response' | head -c 80)..."
    echo -e "  Mode: $(echo "$RESPONSE" | jq -r '.metadata.mode')"
else
    echo -e "${RED}✗ Mock simulation failed${NC}"
    echo "$RESPONSE" | jq .
    exit 1
fi
echo

##############################################################################
# Test 2: Real Execution (/chat)
##############################################################################

echo -e "${YELLOW}Test 2: Real Execution (complete response)${NC}"
echo -e "${BLUE}Endpoint: POST $BASE_URL/agents/geo/chat${NC}"
echo -e "${YELLOW}⚠️  This will make a real OpenAI API call${NC}"
echo

# Ask for confirmation
read -p "Continue with real API call? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Skipping real execution test${NC}"
    echo
else
    START_TIME=$(date +%s)

    RESPONSE=$(curl -s -X POST \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"input": "What is 2+2? Answer briefly."}' \
      "$BASE_URL/agents/geo/chat")

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Check if response contains "mode": "real"
    if echo "$RESPONSE" | jq -e '.metadata.mode == "real"' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Real execution successful${NC}"
        echo -e "  Response: $(echo "$RESPONSE" | jq -r '.response')"
        echo -e "  Mode: $(echo "$RESPONSE" | jq -r '.metadata.mode')"
        echo -e "  Duration: ${DURATION}s"

        # Check for usage metadata
        if echo "$RESPONSE" | jq -e '.metadata.usage' > /dev/null 2>&1; then
            echo -e "  Token Usage:"
            echo "$RESPONSE" | jq '.metadata.usage' | sed 's/^/    /'
        fi
    else
        echo -e "${RED}✗ Real execution failed${NC}"
        echo "$RESPONSE" | jq .
        exit 1
    fi
    echo
fi

##############################################################################
# Test 3: Streaming Execution (/chat/stream)
##############################################################################

echo -e "${YELLOW}Test 3: Streaming Execution (real-time tokens)${NC}"
echo -e "${BLUE}Endpoint: POST $BASE_URL/agents/geo/chat/stream${NC}"
echo -e "${YELLOW}⚠️  This will make a real OpenAI API call${NC}"
echo

# Ask for confirmation
read -p "Continue with streaming test? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Skipping streaming test${NC}"
    echo
else
    echo -e "${GREEN}Streaming response:${NC}"
    echo -n "  "

    curl -N -s -X POST \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"input": "Count from 1 to 5"}' \
      "$BASE_URL/agents/geo/chat/stream" | while IFS= read -r line; do
        if [[ $line == data:* ]]; then
            # Extract JSON from SSE format
            JSON="${line#data: }"

            # Get chunk type and content
            TYPE=$(echo "$JSON" | jq -r '.type' 2>/dev/null)
            CONTENT=$(echo "$JSON" | jq -r '.content' 2>/dev/null)

            case "$TYPE" in
                metadata)
                    echo -e "\n${BLUE}[Metadata received]${NC}"
                    ;;
                token)
                    echo -n "$CONTENT"
                    ;;
                done)
                    echo -e "\n${GREEN}✓ Stream completed${NC}"
                    ;;
                error)
                    echo -e "\n${RED}✗ Stream error: $CONTENT${NC}"
                    exit 1
                    ;;
            esac
        fi
    done
    echo
fi

##############################################################################
# Test 4: Session Persistence
##############################################################################

echo -e "${YELLOW}Test 4: Session Persistence${NC}"
echo -e "${BLUE}Testing conversation history across requests${NC}"
echo

SESSION_ID="test-session-$(date +%s)"

echo -e "Using session ID: ${SESSION_ID}"
echo

# First message with session
RESPONSE1=$(curl -s -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"input\": \"My name is Alice\", \"session_id\": \"$SESSION_ID\"}" \
  "$BASE_URL/agents/geo/simulate")

if echo "$RESPONSE1" | jq -e '.metadata.session_enabled == true' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Session enabled${NC}"
    echo -e "  Session ID: $(echo "$RESPONSE1" | jq -r '.metadata.session_id')"
else
    echo -e "${YELLOW}⚠ Session not enabled (might be expected for mock)${NC}"
fi

echo

##############################################################################
# Summary
##############################################################################

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo
echo -e "${BLUE}Endpoint Summary:${NC}"
echo -e "  ${GREEN}/simulate${NC}      - Mock responses (no API costs, fast)"
echo -e "  ${GREEN}/chat${NC}          - Real execution (complete response)"
echo -e "  ${GREEN}/chat/stream${NC}   - Real execution (streaming tokens)"
echo
echo -e "${BLUE}For more information:${NC}"
echo -e "  Documentation: server/docs/AGENT_EXECUTION.md"
echo -e "  API Docs:      $BASE_URL/docs"
echo
