#!/bin/bash
# Next.js Upgrade Script
# Safely upgrades Next.js and all dependencies with comprehensive testing

set -e  # Exit on error

echo "🚀 Next.js Upgrade Script"
echo "========================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Backup current state
echo -e "${YELLOW}Step 1: Creating backup...${NC}"
cp package.json package.json.backup
cp package-lock.json package-lock.json.backup 2>/dev/null || true
echo -e "${GREEN}✓ Backup created${NC}"
echo ""

# Step 2: Check current versions
echo -e "${YELLOW}Step 2: Current versions${NC}"
echo "Next.js: $(grep '"next"' package.json | head -1)"
echo "React: $(grep '"react"' package.json | head -1)"
echo "React DOM: $(grep '"react-dom"' package.json | head -1)"
echo ""

# Step 3: Update Next.js and core dependencies
echo -e "${YELLOW}Step 3: Updating Next.js and core dependencies...${NC}"
npm install next@latest react@latest react-dom@latest eslint-config-next@latest
echo -e "${GREEN}✓ Core dependencies updated${NC}"
echo ""

# Step 4: Update TypeScript types
echo -e "${YELLOW}Step 4: Updating TypeScript types...${NC}"
npm install --save-dev @types/react@latest @types/react-dom@latest @types/node@latest
echo -e "${GREEN}✓ TypeScript types updated${NC}"
echo ""

# Step 5: Update testing libraries
echo -e "${YELLOW}Step 5: Updating testing libraries...${NC}"
npm install --save-dev @testing-library/react@latest @testing-library/jest-dom@latest jest@latest jest-environment-jsdom@latest
echo -e "${GREEN}✓ Testing libraries updated${NC}"
echo ""

# Step 6: Update other dependencies (carefully)
echo -e "${YELLOW}Step 6: Updating other dependencies...${NC}"
npm install lucide-react@latest sonner@latest tailwind-merge@latest zustand@latest
echo -e "${GREEN}✓ Other dependencies updated${NC}"
echo ""

# Step 7: Run type check
echo -e "${YELLOW}Step 7: Running TypeScript type check...${NC}"
if npm run type-check; then
    echo -e "${GREEN}✓ Type check passed${NC}"
else
    echo -e "${RED}✗ Type check failed - review errors above${NC}"
    exit 1
fi
echo ""

# Step 8: Run linter
echo -e "${YELLOW}Step 8: Running linter...${NC}"
if npm run lint; then
    echo -e "${GREEN}✓ Linter passed${NC}"
else
    echo -e "${RED}✗ Linter failed - review errors above${NC}"
    exit 1
fi
echo ""

# Step 9: Run tests
echo -e "${YELLOW}Step 9: Running tests...${NC}"
if npm test -- --passWithNoTests; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed - review errors above${NC}"
    exit 1
fi
echo ""

# Step 10: Build test
echo -e "${YELLOW}Step 10: Testing build...${NC}"
if npm run build; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed - review errors above${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}✅ Upgrade completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Review the changes in package.json"
echo "2. Test the application manually"
echo "3. If issues occur, restore from backup:"
echo "   cp package.json.backup package.json"
echo "   cp package-lock.json.backup package-lock.json"
echo "   npm install"














