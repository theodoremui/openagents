"""
MoE Configuration Loader.

Loads and validates MoE orchestrator configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass, field

from dotenv import load_dotenv, find_dotenv

from asdrp.agents.config_loader import ModelConfig
from asdrp.orchestration.moe.exceptions import ConfigException


@dataclass
class ExpertGroupConfig:
    """Configuration for expert group."""
    agents: List[str]  # Agent IDs from open_agents.yaml
    capabilities: List[str]
    # Optional richer semantic metadata (used by SemanticSelector)
    description: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    anti_examples: List[str] = field(default_factory=list)
    weight: float = 1.0

    def __post_init__(self):
        """Validate expert group configuration."""
        if not self.agents:
            raise ValueError("Expert group must have at least one agent")
        if not self.capabilities:
            raise ValueError("Expert group must have at least one capability")
        # Defensive: ensure list types (YAML mistakes can turn these into strings)
        if not isinstance(self.examples, list):
            raise ValueError(f"examples must be a list, got {type(self.examples).__name__}")
        if not isinstance(self.anti_examples, list):
            raise ValueError(f"anti_examples must be a list, got {type(self.anti_examples).__name__}")
        if self.weight <= 0:
            raise ValueError(f"Weight must be positive, got {self.weight}")


@dataclass
class MoECacheConfig:
    """Cache configuration."""
    enabled: bool = True
    type: Literal["semantic", "exact", "hybrid"] = "semantic"
    storage: Dict[str, Any] = field(default_factory=dict)
    policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MoEConfig:
    """Complete MoE configuration."""
    enabled: bool
    moe: Dict[str, Any]
    models: Dict[str, ModelConfig]
    experts: Dict[str, ExpertGroupConfig]
    cache: MoECacheConfig
    error_handling: Dict[str, Any]
    tracing: Dict[str, Any]

    def __post_init__(self):
        """Validate MoE configuration."""
        # Validate moe settings
        if "top_k_experts" in self.moe:
            k = self.moe["top_k_experts"]
            if k < 1:
                raise ValueError(f"top_k_experts must be >= 1, got {k}")

        # Validate models
        required_models = ["selection", "mixing"]
        for model_name in required_models:
            if model_name not in self.models:
                raise ValueError(f"Missing required model config: {model_name}")

        # Validate experts
        if not self.experts:
            raise ValueError("At least one expert group must be defined")


class MoEConfigLoader:
    """
    MoE configuration loader.

    Follows pattern from:
    - asdrp/agents/config_loader.py (AgentConfigLoader)
    - asdrp/orchestration/smartrouter/config_loader.py (SmartRouterConfigLoader)
    """

    DEFAULT_CONFIG_PATH = Path("config/moe.yaml")

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config loader.

        Args:
            config_path: Path to MoE configuration YAML. Defaults to config/moe.yaml
        """
        # Load environment variables from .env for OPENAI_API_KEY, etc.
        load_dotenv(find_dotenv())

        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config_cache: Optional[MoEConfig] = None

    def load_config(self) -> MoEConfig:
        """
        Load and parse YAML configuration.

        Returns:
            MoEConfig: Parsed and validated configuration

        Raises:
            ConfigException: If config file not found or invalid
        """
        if not self.config_path.exists():
            raise ConfigException(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r") as f:
                config_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigException(f"Failed to parse YAML: {e}")
        except Exception as e:
            raise ConfigException(f"Failed to load config: {e}")

        # Parse configuration
        try:
            config = self._parse_config(config_dict)
            self._config_cache = config
            return config
        except Exception as e:
            raise ConfigException(f"Invalid MoE config: {e}")

    def _parse_config(self, config_dict: Dict[str, Any]) -> MoEConfig:
        """Parse configuration dictionary into MoEConfig."""

        # Parse models
        models = {}
        for model_name, model_dict in config_dict.get("models", {}).items():
            models[model_name] = ModelConfig(**model_dict)

        # Parse experts
        experts = {}
        for expert_name, expert_dict in config_dict.get("experts", {}).items():
            experts[expert_name] = ExpertGroupConfig(**expert_dict)

        # Parse cache config
        cache_dict = config_dict.get("cache", {})
        cache = MoECacheConfig(
            enabled=cache_dict.get("enabled", True),
            type=cache_dict.get("type", "semantic"),
            storage=cache_dict.get("storage", {}),
            policy=cache_dict.get("policy", {})
        )

        return MoEConfig(
            enabled=config_dict.get("enabled", True),
            moe=config_dict.get("moe", {}),
            models=models,
            experts=experts,
            cache=cache,
            error_handling=config_dict.get("error_handling", {}),
            tracing=config_dict.get("tracing", {})
        )

    def validate_expert_agents(self, available_agents: List[str]) -> None:
        """
        Validate that all expert agents exist.

        Args:
            available_agents: List of available agent IDs from open_agents.yaml

        Raises:
            ConfigException: If expert references unknown agent
        """
        if self._config_cache is None:
            raise ConfigException("Config not loaded. Call load_config() first.")

        available_set = set(available_agents)

        for expert_name, expert_config in self._config_cache.experts.items():
            for agent_id in expert_config.agents:
                if agent_id not in available_set:
                    raise ConfigException(
                        f"Expert '{expert_name}' references unknown agent '{agent_id}'"
                    )

    def get_config(self) -> MoEConfig:
        """
        Get cached configuration.

        Returns:
            MoEConfig: Cached configuration

        Raises:
            ConfigException: If config not loaded
        """
        if self._config_cache is None:
            raise ConfigException("Config not loaded. Call load_config() first.")
        return self._config_cache


# Singleton instance for convenience
_config_loader_instance: Optional[MoEConfigLoader] = None


def load_moe_config(config_path: Optional[Path] = None, force_reload: bool = False) -> MoEConfig:
    """
    Convenience function to load MoE configuration.

    Uses singleton pattern to cache config loader instance.

    Args:
        config_path: Optional custom path to config file
        force_reload: Force reload config from disk

    Returns:
        MoEConfig: Loaded and validated configuration

    Raises:
        ConfigException: If config cannot be loaded or is invalid
    """
    global _config_loader_instance

    # Create singleton instance if needed
    if _config_loader_instance is None or config_path is not None:
        _config_loader_instance = MoEConfigLoader(config_path)

    # Load config (will use cache if already loaded and not forcing reload)
    if force_reload or _config_loader_instance._config_cache is None:
        return _config_loader_instance.load_config()

    return _config_loader_instance.get_config()
