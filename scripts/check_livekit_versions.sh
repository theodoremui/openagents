#!/bin/bash
# Check LiveKit package versions

echo "========================================="
echo "LiveKit Package Versions"
echo "========================================="

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✓ Activated .venv"
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Activated venv"
else
    echo "⚠ No virtual environment found, using system Python"
fi

echo ""
echo "Checking installed versions:"
echo "-----------------------------------------"

pip show livekit | grep -E "^(Name|Version):"
echo ""
pip show livekit-agents | grep -E "^(Name|Version):"
echo ""
pip show livekit-plugins-openai | grep -E "^(Name|Version):"
echo ""
pip show livekit-plugins-silero | grep -E "^(Name|Version):"
echo ""

echo "========================================="
echo "Required versions (from pyproject.toml):"
echo "  livekit>=0.17.0"
echo "  livekit-agents>=0.9.0"
echo "  livekit-plugins-openai>=0.9.0"
echo "  livekit-plugins-silero>=0.9.0"
echo "========================================="
echo ""

# Check if upgrade needed
OPENAI_PLUGIN_VERSION=$(pip show livekit-plugins-openai 2>/dev/null | grep "Version:" | awk '{print $2}')

if [ -z "$OPENAI_PLUGIN_VERSION" ]; then
    echo "❌ livekit-plugins-openai not installed!"
    echo ""
    echo "Install with:"
    echo "  pip install livekit-plugins-openai>=0.9.0"
elif [ "$(printf '%s\n' "0.9.0" "$OPENAI_PLUGIN_VERSION" | sort -V | head -n1)" = "0.9.0" ]; then
    echo "✅ livekit-plugins-openai version $OPENAI_PLUGIN_VERSION meets requirements"
else
    echo "⚠ livekit-plugins-openai version $OPENAI_PLUGIN_VERSION is below 0.9.0"
    echo ""
    echo "Upgrade with:"
    echo "  pip install --upgrade livekit-plugins-openai>=0.9.0"
fi
