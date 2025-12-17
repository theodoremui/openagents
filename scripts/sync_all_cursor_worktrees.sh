#!/bin/bash
# Sync all Cursor worktrees with main repository
# Run this when Cursor shows "Worktree not found" errors

MAIN_REPO="/Users/pmui/dev/halo/openagents"
WORKTREE_BASE="$HOME/.cursor/worktrees/openagents"

echo "🔧 Syncing all Cursor worktrees..."
echo ""

count=0
for worktree in "$WORKTREE_BASE"/*; do
    if [ -d "$worktree" ] && [ "$(basename "$worktree")" != "." ] && [ "$(basename "$worktree")" != ".." ]; then
        worktree_name=$(basename "$worktree")
        
        # Sync all modified files from main repo
        echo "📦 Syncing: $worktree_name"
        
        # List of files that commonly need syncing
        rsync -av --exclude='.git' --exclude='.next' --exclude='node_modules' \
            "$MAIN_REPO/" "$worktree/" \
            --include='server/bin/post_compile' \
            --include='server/setup.py' \
            --include='server/pyproject.toml' \
            --include='server/requirements.txt' \
            --include='frontend_web/lib/api-client.ts' \
            --include='frontend_web/Procfile' \
            --include='frontend_web/package.json' \
            --include='scripts/' \
            --exclude='*' \
            > /dev/null 2>&1 && echo "  ✓ Synced" || echo "  ✗ Failed"
        
        ((count++))
    fi
done

echo ""
echo "✅ Synced $count worktree(s)"
echo ""
echo "You can now try applying changes in Cursor again."
