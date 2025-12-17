#!/usr/bin/env python3
"""
Check MoE Configuration

Validates MoE orchestrator configuration and reports detailed status.
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from asdrp.orchestration.moe.config_loader import MoEConfigLoader, MoEConfig
from asdrp.agents.config_loader import AgentConfigLoader


def check_config_file() -> bool:
    """Check if config file exists."""
    config_path = project_root / "config" / "moe.yaml"

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False

    print(f"✓ Config file exists: {config_path}")
    return True


def load_and_validate_config() -> MoEConfig:
    """Load and validate MoE configuration."""
    try:
        loader = MoEConfigLoader()
        config = loader.load_config()
        print("✓ Configuration loaded successfully")
        return config
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        sys.exit(1)


def check_expert_agents(config: MoEConfig) -> bool:
    """Check that all expert agents exist."""
    try:
        agent_loader = AgentConfigLoader()
        available_agents = agent_loader.list_agents()

        print(f"\n📋 Available Agents ({len(available_agents)}):")
        for agent in sorted(available_agents):
            print(f"  - {agent}")

        moe_loader = MoEConfigLoader()
        moe_loader._config_cache = config
        moe_loader.validate_expert_agents(available_agents)

        print("\n✓ All expert agents validated")
        return True

    except Exception as e:
        print(f"\n❌ Expert agent validation failed: {e}")
        return False


def print_config_summary(config: MoEConfig):
    """Print configuration summary."""
    print("\n" + "=" * 60)
    print("MoE Configuration Summary")
    print("=" * 60)

    print(f"\n🎯 Status: {'Enabled' if config.enabled else 'Disabled'}")

    print(f"\n⚙️  MoE Settings:")
    print(f"  - Selection strategy: {config.moe.get('selection_strategy', 'N/A')}")
    print(f"  - Top-k experts: {config.moe.get('top_k_experts', 'N/A')}")
    print(f"  - Confidence threshold: {config.moe.get('confidence_threshold', 'N/A')}")
    print(f"  - Mixing strategy: {config.moe.get('mixing_strategy', 'N/A')}")
    print(f"  - Parallel execution: {config.moe.get('parallel_execution', 'N/A')}")
    print(f"  - Overall timeout: {config.moe.get('overall_timeout', 'N/A')}s")

    print(f"\n🤖 Models:")
    for model_name, model_config in config.models.items():
        print(f"  - {model_name}: {model_config.name} "
              f"(temp={model_config.temperature}, "
              f"max_tokens={model_config.max_tokens})")

    print(f"\n👥 Expert Groups ({len(config.experts)}):")
    for expert_name, expert_config in config.experts.items():
        print(f"  - {expert_name}:")
        print(f"      Agents: {', '.join(expert_config.agents)}")
        print(f"      Capabilities: {', '.join(expert_config.capabilities[:5])}"
              f"{'...' if len(expert_config.capabilities) > 5 else ''}")
        print(f"      Weight: {expert_config.weight}")

    print(f"\n💾 Cache:")
    print(f"  - Enabled: {config.cache.enabled}")
    print(f"  - Type: {config.cache.type}")
    if config.cache.enabled:
        storage = config.cache.storage
        print(f"  - Backend: {storage.get('backend', 'N/A')}")
        print(f"  - Path: {storage.get('path', 'N/A')}")

    print(f"\n🔍 Tracing:")
    print(f"  - Enabled: {config.tracing.get('enabled', False)}")
    if config.tracing.get('enabled'):
        storage = config.tracing.get('storage', {})
        print(f"  - Backend: {storage.get('backend', 'N/A')}")
        print(f"  - Path: {storage.get('path', 'N/A')}")

    print(f"\n⚠️  Error Handling:")
    error_handling = config.error_handling
    print(f"  - Timeout: {error_handling.get('timeout', 'N/A')}s")
    print(f"  - Retries: {error_handling.get('retries', 'N/A')}")
    print(f"  - Fallback agent: {error_handling.get('fallback_agent', 'N/A')}")

    print("\n" + "=" * 60)


def check_data_directories():
    """Check if data directories exist."""
    print("\n📁 Data Directories:")

    dirs = [
        project_root / "data" / "orchestration" / "moe" / "cache",
        project_root / "data" / "orchestration" / "moe" / "traces",
        project_root / "data" / "orchestration" / "moe" / "traces" / "json",
    ]

    all_exist = True
    for dir_path in dirs:
        exists = dir_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_path}")
        if not exists:
            all_exist = False

    if not all_exist:
        print("\n💡 Run 'scripts/orchestration/setup_moe.sh' to create directories")

    return all_exist


def main():
    """Main validation function."""
    print("🔍 Checking MoE Orchestrator Configuration\n")

    # 1. Check config file exists
    if not check_config_file():
        sys.exit(1)

    # 2. Load and validate config
    config = load_and_validate_config()

    # 3. Check expert agents
    if not check_expert_agents(config):
        sys.exit(1)

    # 4. Print summary
    print_config_summary(config)

    # 5. Check data directories
    check_data_directories()

    # Final status
    print("\n✅ MoE configuration is valid and ready to use!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
