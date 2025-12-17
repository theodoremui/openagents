"""
Tests for SmartRouterConfigLoader

Tests configuration loading, validation, and parsing.
"""

import pytest
import yaml
from pathlib import Path
from tempfile import NamedTemporaryFile
from asdrp.orchestration.smartrouter.config_loader import (
    SmartRouterConfigLoader,
    ModelConfig,
    ModelConfigs,
    DecompositionConfig,
    EvaluationConfig,
    ErrorHandlingConfig,
    SmartRouterConfig,
)
from asdrp.orchestration.smartrouter.exceptions import SmartRouterException


class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_create_model_config(self):
        """Test creating ModelConfig."""
        config = ModelConfig(
            name="gpt-4.1-mini",
            temperature=0.1,
            max_tokens=500
        )
        assert config.name == "gpt-4.1-mini"
        assert config.temperature == 0.1
        assert config.max_tokens == 500


class TestDecompositionConfig:
    """Test DecompositionConfig dataclass."""

    def test_create_decomposition_config(self):
        """Test creating DecompositionConfig."""
        config = DecompositionConfig(
            max_subqueries=10,
            recursion_limit=3,
            fallback_threshold=0.7
        )
        assert config.max_subqueries == 10
        assert config.recursion_limit == 3
        assert config.fallback_threshold == 0.7


class TestEvaluationConfig:
    """Test EvaluationConfig dataclass."""

    def test_create_evaluation_config(self):
        """Test creating EvaluationConfig."""
        config = EvaluationConfig(
            fallback_message="Not enough information",
            quality_threshold=0.7,
            criteria=["completeness", "accuracy"]
        )
        assert config.fallback_message == "Not enough information"
        assert config.quality_threshold == 0.7
        assert config.criteria == ["completeness", "accuracy"]


class TestErrorHandlingConfig:
    """Test ErrorHandlingConfig dataclass."""

    def test_create_error_handling_config(self):
        """Test creating ErrorHandlingConfig."""
        config = ErrorHandlingConfig(
            timeout=30.0,
            retries=2
        )
        assert config.timeout == 30.0
        assert config.retries == 2


class TestSmartRouterConfigLoader:
    """Test SmartRouterConfigLoader class."""

    def test_load_real_config(self):
        """Test loading real configuration file."""
        loader = SmartRouterConfigLoader()
        config = loader.load_config()
        
        assert isinstance(config, SmartRouterConfig)
        assert config.enabled is True
        assert isinstance(config.models, ModelConfigs)
        assert isinstance(config.decomposition, DecompositionConfig)
        assert isinstance(config.evaluation, EvaluationConfig)
        assert isinstance(config.error_handling, ErrorHandlingConfig)
        assert isinstance(config.capabilities, dict)
        assert len(config.capabilities) > 0

    def test_load_config_caching(self):
        """Test that config is cached."""
        loader = SmartRouterConfigLoader()
        config1 = loader.load_config()
        config2 = loader.load_config()
        
        assert config1 is config2  # Same object (cached)

    def test_load_config_reload(self):
        """Test forcing reload."""
        loader = SmartRouterConfigLoader()
        config1 = loader.load_config()
        config2 = loader.load_config(reload=True)
        
        # Should be different objects (reloaded)
        assert config1 is not config2

    def test_load_config_missing_file(self):
        """Test loading non-existent config file."""
        loader = SmartRouterConfigLoader(config_path=Path("nonexistent.yaml"))
        
        with pytest.raises(SmartRouterException):
            loader.load_config()

    def test_load_config_invalid_yaml(self):
        """Test loading invalid YAML."""
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)
        
        try:
            loader = SmartRouterConfigLoader(config_path=temp_path)
            with pytest.raises(SmartRouterException):
                loader.load_config()
        finally:
            temp_path.unlink()

    def test_load_config_minimal(self):
        """Test loading minimal valid config."""
        config_dict = {
            "enabled": True,
            "models": {
                "interpretation": {
                    "name": "gpt-4.1-mini",
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                "decomposition": {
                    "name": "gpt-4.1-mini",
                    "temperature": 0.2,
                    "max_tokens": 1000
                },
                "synthesis": {
                    "name": "gpt-4.1-mini",
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                "evaluation": {
                    "name": "gpt-4.1-mini",
                    "temperature": 0.01,
                    "max_tokens": 500
                }
            },
            "decomposition": {
                "max_subqueries": 10,
                "recursion_limit": 3,
                "fallback_threshold": 0.4
            },
            "capabilities": {
                "geo": ["geocoding"]
            },
            "evaluation": {
                "fallback_message": "Not enough info",
                "quality_threshold": 0.7,
                "criteria": ["completeness"]
            },
            "error_handling": {
                "timeout": 30.0,
                "retries": 2
            }
        }
        
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)
        
        try:
            loader = SmartRouterConfigLoader(config_path=temp_path)
            config = loader.load_config()
            
            assert config.enabled is True
            assert config.models.interpretation.name == "gpt-4.1-mini"
            assert config.decomposition.max_subqueries == 10
            assert "geo" in config.capabilities
        finally:
            temp_path.unlink()

    def test_load_agent_capabilities(self):
        """Test loading capabilities from open_agents.yaml."""
        loader = SmartRouterConfigLoader()
        capabilities = loader._load_agent_capabilities()
        
        assert isinstance(capabilities, dict)
        # Should have some agents
        assert len(capabilities) > 0

    def test_load_agent_capabilities_missing_file(self):
        """Test loading capabilities when agents config is missing."""
        loader = SmartRouterConfigLoader(
            agents_config_path=Path("nonexistent.yaml")
        )
        capabilities = loader._load_agent_capabilities()
        
        # Should return empty dict, not raise
        assert capabilities == {}

    def test_parse_config(self):
        """Test parsing config dictionary."""
        loader = SmartRouterConfigLoader()
        
        config_dict = {
            "enabled": True,
            "models": {
                "interpretation": {"name": "gpt-4.1-mini", "temperature": 0.1, "max_tokens": 500},
                "decomposition": {"name": "gpt-4.1-mini", "temperature": 0.2, "max_tokens": 1000},
                "synthesis": {"name": "gpt-4.1-mini", "temperature": 0.3, "max_tokens": 2000},
                "evaluation": {"name": "gpt-4.1-mini", "temperature": 0.01, "max_tokens": 500}
            },
            "decomposition": {
                "max_subqueries": 10,
                "recursion_limit": 3,
                "fallback_threshold": 0.4
            },
            "capabilities": {"geo": ["geocoding"]},
            "evaluation": {
                "fallback_message": "Not enough",
                "quality_threshold": 0.7,
                "criteria": ["completeness"]
            },
            "error_handling": {
                "timeout": 30.0,
                "retries": 2
            }
        }
        
        config = loader._parse_config(config_dict)
        
        assert isinstance(config, SmartRouterConfig)
        assert config.enabled is True








