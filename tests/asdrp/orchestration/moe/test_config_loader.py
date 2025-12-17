"""Tests for MoE Configuration Loader."""

import pytest
import tempfile
from pathlib import Path

from asdrp.orchestration.moe.config_loader import (
    MoEConfigLoader,
    MoEConfig,
    ExpertGroupConfig,
    MoECacheConfig,
    ConfigException,
)


class TestMoEConfigLoader:
    """Test MoE configuration loading."""

    @pytest.fixture
    def valid_config_yaml(self):
        """Valid MoE configuration YAML."""
        return """
enabled: true

moe:
  selection_strategy: "capability_match"
  top_k_experts: 3
  confidence_threshold: 0.3
  mixing_strategy: "synthesis"
  parallel_execution: true
  max_concurrent: 10
  timeout_per_expert: 10.0
  overall_timeout: 30.0

models:
  selection:
    name: "gpt-4.1-mini"
    temperature: 0.1
    max_tokens: 500
  mixing:
    name: "gpt-4.1-mini"
    temperature: 0.3
    max_tokens: 2000

experts:
  search_expert:
    agents: ["one", "perplexity"]
    capabilities: ["web_search", "realtime"]
    weight: 1.0

cache:
  enabled: true
  type: "semantic"
  storage:
    backend: "sqlite"
    path: "test.db"
  policy:
    similarity_threshold: 0.9
    ttl: 3600
    max_entries: 1000

error_handling:
  timeout: 30.0
  retries: 2
  fallback_agent: "one"
  fallback_message: "Error message"

tracing:
  enabled: true
  storage:
    backend: "sqlite"
    path: "traces.db"
  exporters: []
"""

    def test_load_valid_config(self, valid_config_yaml):
        """Test loading valid configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_config_yaml)
            temp_path = Path(f.name)

        try:
            loader = MoEConfigLoader(config_path=temp_path)
            config = loader.load_config()

            assert isinstance(config, MoEConfig)
            assert config.enabled is True
            assert config.moe["top_k_experts"] == 3
            assert "selection" in config.models
            assert "search_expert" in config.experts
            assert config.cache.enabled is True
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises exception."""
        loader = MoEConfigLoader(config_path=Path("nonexistent.yaml"))

        with pytest.raises(ConfigException, match="Config file not found"):
            loader.load_config()

    def test_validate_expert_agents(self, valid_config_yaml):
        """Test validating expert agents exist."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_config_yaml)
            temp_path = Path(f.name)

        try:
            loader = MoEConfigLoader(config_path=temp_path)
            config = loader.load_config()

            # Valid agents
            available_agents = ["one", "perplexity", "geo", "map"]
            loader.validate_expert_agents(available_agents)

            # Invalid agents should raise
            with pytest.raises(ConfigException, match="references unknown agent"):
                loader.validate_expert_agents(["geo", "map"])  # Missing "one", "perplexity"
        finally:
            temp_path.unlink()

    def test_expert_group_validation(self):
        """Test expert group validation."""
        # Valid expert group
        expert = ExpertGroupConfig(
            agents=["one"],
            capabilities=["web_search"],
            weight=1.0
        )
        assert expert.agents == ["one"]

        # Invalid: empty agents
        with pytest.raises(ValueError, match="at least one agent"):
            ExpertGroupConfig(
                agents=[],
                capabilities=["web_search"],
                weight=1.0
            )

        # Invalid: empty capabilities
        with pytest.raises(ValueError, match="at least one capability"):
            ExpertGroupConfig(
                agents=["one"],
                capabilities=[],
                weight=1.0
            )

        # Invalid: negative weight
        with pytest.raises(ValueError, match="Weight must be positive"):
            ExpertGroupConfig(
                agents=["one"],
                capabilities=["web_search"],
                weight=-1.0
            )

    def test_moe_config_validation(self, mock_model_config):
        """Test MoE config validation."""
        # Invalid: top_k_experts < 1
        with pytest.raises(ValueError, match="top_k_experts must be >= 1"):
            MoEConfig(
                enabled=True,
                moe={"top_k_experts": 0},
                models={"selection": mock_model_config, "mixing": mock_model_config},
                experts={"test": ExpertGroupConfig(
                    agents=["one"], capabilities=["test"], weight=1.0
                )},
                cache=MoECacheConfig(),
                error_handling={},
                tracing={}
            )

        # Invalid: missing required model
        with pytest.raises(ValueError, match="Missing required model config"):
            MoEConfig(
                enabled=True,
                moe={},
                models={"selection": mock_model_config},  # Missing "mixing"
                experts={"test": ExpertGroupConfig(
                    agents=["one"], capabilities=["test"], weight=1.0
                )},
                cache=MoECacheConfig(),
                error_handling={},
                tracing={}
            )

        # Invalid: no experts
        with pytest.raises(ValueError, match="At least one expert group"):
            MoEConfig(
                enabled=True,
                moe={},
                models={"selection": mock_model_config, "mixing": mock_model_config},
                experts={},  # Empty
                cache=MoECacheConfig(),
                error_handling={},
                tracing={}
            )
