#!/bin/bash
# Setup MoE (Mixture of Experts) Orchestrator
#
# This script initializes the MoE orchestrator by:
# 1. Validating configuration
# 2. Creating required data directories
# 3. Initializing cache databases
# 4. Verifying expert agent availability

set -e

echo "🚀 Setting up MoE Orchestrator..."
echo

# Navigate to project root
cd "$(dirname "$0")/../.."

# Check if config exists
if [ ! -f "config/moe.yaml" ]; then
    echo "❌ Error: config/moe.yaml not found"
    exit 1
fi

echo "✓ Configuration file found: config/moe.yaml"

# Validate configuration using Python
echo
echo "📋 Validating MoE configuration..."
python3 << 'PYTHON_SCRIPT'
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path.cwd()))

try:
    from asdrp.orchestration.moe.config_loader import MoEConfigLoader
    from asdrp.agents.config_loader import AgentConfigLoader

    # Load MoE config
    moe_loader = MoEConfigLoader()
    moe_config = moe_loader.load_config()

    print(f"✓ MoE configuration loaded successfully")
    print(f"  - Enabled: {moe_config.enabled}")
    print(f"  - Strategy: {moe_config.moe.get('selection_strategy', 'N/A')}")
    print(f"  - Top-k experts: {moe_config.moe.get('top_k_experts', 'N/A')}")
    print(f"  - Expert groups: {len(moe_config.experts)}")

    # Validate expert agents exist
    agent_loader = AgentConfigLoader()
    available_agents = agent_loader.list_agents()

    print(f"\n✓ Found {len(available_agents)} available agents")

    moe_loader.validate_expert_agents(available_agents)
    print(f"✓ All expert agents validated")

    # List expert groups
    print(f"\n📊 Expert Groups:")
    for expert_name, expert_config in moe_config.experts.items():
        print(f"  - {expert_name}: {', '.join(expert_config.agents)}")

except Exception as e:
    print(f"❌ Configuration validation failed: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -ne 0 ]; then
    echo
    echo "❌ MoE setup failed. Please check configuration."
    exit 1
fi

# Create data directories
echo
echo "📁 Creating data directories..."
mkdir -p data/orchestration/moe/cache
mkdir -p data/orchestration/moe/traces
mkdir -p data/orchestration/moe/traces/json
echo "✓ Data directories created"

# Initialize cache database (if enabled)
echo
echo "💾 Initializing cache..."
python3 << 'PYTHON_SCRIPT'
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

try:
    from asdrp.orchestration.moe.config_loader import MoEConfigLoader
    from asdrp.orchestration.moe.cache import SemanticCache

    loader = MoEConfigLoader()
    config = loader.load_config()

    if config.cache.enabled:
        cache = SemanticCache(config)
        print("✓ Cache database initialized")
    else:
        print("ℹ  Cache disabled in configuration")

except Exception as e:
    print(f"⚠  Warning: Cache initialization failed: {e}", file=sys.stderr)
    print("   (This is non-critical - MoE will work without cache)")
PYTHON_SCRIPT

# Summary
echo
echo "=" * 60
echo "✅ MoE Orchestrator setup complete!"
echo
echo "Next steps:"
echo "  1. Start the server: python -m server.main"
echo "  2. Use agent_id 'moe' in API calls"
echo "  3. Example: POST /agents/moe/chat"
echo
echo "Configuration: config/moe.yaml"
echo "Data directory: data/orchestration/moe/"
echo "=" * 60
