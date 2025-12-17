#!/bin/bash
# fix_cursor_worktree.sh - Fix Cursor worktree missing files
#
# Usage: ./scripts/fix_cursor_worktree.sh <worktree_id>
# Example: ./scripts/fix_cursor_worktree.sh prh

set -e

MAIN_REPO="/Users/pmui/dev/halo/openagents"
WORKTREE_BASE="/Users/pmui/.cursor/worktrees/openagents"

if [ -z "$1" ]; then
    echo "Usage: $0 <worktree_id>"
    echo "Example: $0 prh"
    exit 1
fi

WORKTREE_ID="$1"
WORKTREE_PATH="$WORKTREE_BASE/$WORKTREE_ID"

if [ ! -d "$WORKTREE_PATH" ]; then
    echo "Error: Worktree not found: $WORKTREE_PATH"
    exit 1
fi

echo "Fixing Cursor worktree: $WORKTREE_ID"
cd "$WORKTREE_PATH"

# Fix 1: Create placeholder for deleted test file
if [ ! -f "test_mcp_detection.py" ]; then
    echo "Creating: test_mcp_detection.py"
    echo "# Placeholder - this file was deleted" > test_mcp_detection.py
fi

# Fix 2: Copy frontend_web/lib/ directory
if [ ! -d "frontend_web/lib" ] || [ ! -f "frontend_web/lib/api-client.ts" ]; then
    echo "Copying: frontend_web/lib/"
    mkdir -p frontend_web/lib
    cp -r "$MAIN_REPO/frontend_web/lib/"* frontend_web/lib/
fi

echo "✅ Worktree $WORKTREE_ID fixed!"
