#!/bin/bash
# Test script to verify upgrade readiness

set -e

echo "🧪 Testing Upgrade Readiness"
echo "==========================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(dirname "$0")/.."

# Test 1: Type checking
echo -e "${YELLOW}Test 1: TypeScript type checking...${NC}"
if npm run type-check > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Type checking passed${NC}"
else
    echo -e "${RED}✗ Type checking failed${NC}"
    npm run type-check
    exit 1
fi

# Test 2: Linting
echo -e "${YELLOW}Test 2: ESLint checking...${NC}"
if npm run lint > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Linting passed${NC}"
else
    echo -e "${RED}✗ Linting failed${NC}"
    npm run lint
    exit 1
fi

# Test 3: Build
echo -e "${YELLOW}Test 3: Build test...${NC}"
if npm run build > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    npm run build
    exit 1
fi

# Test 4: Tests
echo -e "${YELLOW}Test 4: Running tests...${NC}"
if npm test -- --passWithNoTests > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    npm test
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All pre-upgrade tests passed!${NC}"
echo "Ready for upgrade."













