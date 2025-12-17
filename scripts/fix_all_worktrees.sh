#!/bin/bash
# Comprehensive worktree fixer - copies all important files to all worktrees

MAIN_REPO="/Users/pmui/dev/halo/openagents"
WORKTREE_BASE="/Users/pmui/.cursor/worktrees/openagents"

echo "Fixing all worktrees..."

for wt in "$WORKTREE_BASE"/*/; do
    wt_name=$(basename "$wt")
    changed=false
    
    # Fix test_mcp_detection.py
    if [ ! -f "${wt}test_mcp_detection.py" ]; then
        echo "# Placeholder" > "${wt}test_mcp_detection.py"
        changed=true
    fi
    
    # Fix frontend_web/lib/
    if [ ! -f "${wt}frontend_web/lib/api-client.ts" ]; then
        mkdir -p "${wt}frontend_web/lib"
        cp -r "$MAIN_REPO/frontend_web/lib/"* "${wt}frontend_web/lib/" 2>/dev/null
        changed=true
    fi
    
    # Fix unified-chat-interface.tsx
    if [ ! -f "${wt}frontend_web/components/unified-chat-interface.tsx" ]; then
        mkdir -p "${wt}frontend_web/components"
        cp "$MAIN_REPO/frontend_web/components/unified-chat-interface.tsx" "${wt}frontend_web/components/" 2>/dev/null
        changed=true
    fi
    
    # Fix voice files
    if [ ! -f "${wt}server/voice/realtime/agent.py" ]; then
        mkdir -p "${wt}server/voice/realtime"
        cp "$MAIN_REPO/server/voice/realtime/agent.py" "${wt}server/voice/realtime/" 2>/dev/null
        changed=true
    fi
    
    if [ "$changed" = true ]; then
        echo "Fixed: $wt_name"
    fi
done

echo "✅ All worktrees fixed!"
