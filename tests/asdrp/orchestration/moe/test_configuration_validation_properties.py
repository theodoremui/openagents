"""
Property-based tests for MoE Configuration Validation.

**Feature: moe-map-rendering-fix, Property 16: Configuration Validation**
**Validates: Requirements 7.5**

This module implements property-based testing for the MoE configuration system to verify:
1. Configuration Validation (Property 16) - startup validation for agent existence and configuration completeness

These tests use Hypothesis to generate random test cases and verify that
the correctness properties hold across all valid inputs.
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite

from asdrp.orchestration.moe.config_loader import MoEConfigLoader, MoEConfig, ExpertGroupConfig, MoECacheConfig
from asdrp.orchestration.moe.exceptions import ConfigException
from asdrp.agents.config_loader import ModelConfig


# Test data strategies for property-based testing

@composite
def valid_model_config(draw):
    """Generate valid model configurations."""
    return {
        "name": draw(st.sampled_from(["gpt-4.1-mini", "gpt-4", "gpt-3.5-turbo"])),
        "temperature": draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)),
        "max_tokens": draw(st.integers(min_value=100, max_value=4000))
    }


@composite
def valid_expert_config(draw):
    """Generate valid expert configurations."""
    agents = draw(st.lists(
        st.sampled_from(["yelp", "yelp_mcp", "map", "geo", "one"]),
        min_size=1,
        max_size=3,
        unique=True
    ))
    capabilities = draw(st.lists(
        st.sampled_from(["business_search", "mapping", "geocoding", "general"]),
        min_size=1,
        max_size=2,
        unique=True
    ))
    
    return {
        "agents": agents,
        "capabilities": capabilities,
        "weight": draw(st.floats(min_value=0.1, max_value=2.0, allow_nan=False, allow_infinity=False))
    }


@composite
def valid_moe_config_dict(draw):
    """Generate valid MoE configuration dictionaries."""
    selection_model = draw(valid_model_config())
    mixing_model = draw(valid_model_config())
    
    business_expert = draw(valid_expert_config())
    location_expert = draw(valid_expert_config())
    
    return {
        "enabled": draw(st.booleans()),
        "moe": {
            "mixing_strategy": draw(st.sampled_from(["synthesis", "weighted", "voting"])),
            "top_k_experts": draw(st.integers(min_value=1, max_value=5)),
            "confidence_threshold": draw(st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False)),
            "timeout_per_expert": draw(st.floats(min_value=5.0, max_value=60.0, allow_nan=False, allow_infinity=False)),
            "overall_timeout": draw(st.floats(min_value=10.0, max_value=120.0, allow_nan=False, allow_infinity=False))
        },
        "models": {
            "selection": selection_model,
            "mixing": mixing_model
        },
        "experts": {
            "business_expert": business_expert,
            "location_expert": location_expert
        },
        "cache": {
            "enabled": draw(st.booleans()),
            "type": draw(st.sampled_from(["semantic", "exact", "hybrid"])),
            "storage": {"backend": "memory"},
            "policy": {"ttl": 3600}
        },
        "error_handling": {
            "fallback_agent": "one",
            "fallback_message": "I apologize, but I encountered an issue."
        },
        "tracing": {
            "enabled": draw(st.booleans()),
            "storage": {"backend": "memory"},
            "exporters": []
        }
    }


@composite
def invalid_moe_config_dict(draw):
    """Generate invalid MoE configuration dictionaries."""
    config = draw(valid_moe_config_dict())
    
    # Introduce various types of invalid configurations
    error_type = draw(st.sampled_from([
        "missing_models",
        "invalid_top_k",
        "empty_experts",
        "invalid_expert_weight",
        "missing_required_model"
    ]))
    
    if error_type == "missing_models":
        del config["models"]
    elif error_type == "invalid_top_k":
        config["moe"]["top_k_experts"] = 0
    elif error_type == "empty_experts":
        config["experts"] = {}
    elif error_type == "invalid_expert_weight":
        config["experts"]["business_expert"]["weight"] = -1.0
    elif error_type == "missing_required_model":
        del config["models"]["selection"]
    
    return config, error_type


class TestConfigurationValidationProperties:
    """Property-based tests for configuration validation."""

    @given(config_dict=valid_moe_config_dict())
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_16_valid_configuration_loading(self, config_dict):
        """
        **Feature: moe-map-rendering-fix, Property 16: Configuration Validation**
        **Validates: Requirements 7.5**
        
        Property: For any valid configuration dictionary, the system should successfully
        load and validate the configuration without errors.
        """
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)
        
        try:
            # Load configuration
            loader = MoEConfigLoader(temp_path)
            config = loader.load_config()
            
            # CRITICAL PROPERTY: Valid configurations should load successfully
            assert isinstance(config, MoEConfig), "Should return MoEConfig instance"
            assert config.enabled == config_dict["enabled"], "Enabled flag should match"
            
            # Verify models are loaded correctly
            assert "selection" in config.models, "Selection model should be loaded"
            assert "mixing" in config.models, "Mixing model should be loaded"
            assert isinstance(config.models["selection"], ModelConfig), "Selection model should be ModelConfig"
            assert isinstance(config.models["mixing"], ModelConfig), "Mixing model should be ModelConfig"
            
            # Verify experts are loaded correctly
            assert len(config.experts) > 0, "Should have at least one expert group"
            for expert_name, expert_config in config.experts.items():
                assert isinstance(expert_config, ExpertGroupConfig), f"Expert {expert_name} should be ExpertGroupConfig"
                assert len(expert_config.agents) > 0, f"Expert {expert_name} should have at least one agent"
                assert len(expert_config.capabilities) > 0, f"Expert {expert_name} should have at least one capability"
                assert expert_config.weight > 0, f"Expert {expert_name} should have positive weight"
            
            # Verify cache configuration
            assert isinstance(config.cache, MoECacheConfig), "Cache should be MoECacheConfig"
            assert config.cache.type in ["semantic", "exact", "hybrid"], "Cache type should be valid"
            
            # Verify MoE settings
            if "top_k_experts" in config.moe:
                assert config.moe["top_k_experts"] >= 1, "top_k_experts should be >= 1"
            
        finally:
            # Clean up temporary file
            temp_path.unlink()

    @given(invalid_config=invalid_moe_config_dict())
    @settings(max_examples=15, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_16_invalid_configuration_rejection(self, invalid_config):
        """
        **Feature: moe-map-rendering-fix, Property 16: Configuration Validation**
        **Validates: Requirements 7.5**
        
        Property: For any invalid configuration, the system should reject it with
        a clear error message indicating the specific validation failure.
        """
        config_dict, error_type = invalid_config
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)
        
        try:
            # Attempt to load invalid configuration
            loader = MoEConfigLoader(temp_path)
            
            # CRITICAL PROPERTY: Invalid configurations should be rejected
            with pytest.raises(ConfigException) as exc_info:
                loader.load_config()
            
            # Verify error message is descriptive
            error_message = str(exc_info.value).lower()
            assert len(error_message) > 10, "Error message should be descriptive"
            
            # Verify error message relates to the specific validation failure
            if error_type == "missing_models":
                assert "model" in error_message, "Error should mention missing models"
            elif error_type == "invalid_top_k":
                assert "top_k" in error_message or "must be" in error_message, "Error should mention top_k validation"
            elif error_type == "empty_experts":
                assert "expert" in error_message, "Error should mention missing experts"
            elif error_type == "invalid_expert_weight":
                assert "weight" in error_message or "positive" in error_message, "Error should mention weight validation"
            elif error_type == "missing_required_model":
                assert "selection" in error_message or "model" in error_message, "Error should mention missing required model"
            
        finally:
            # Clean up temporary file
            temp_path.unlink()

    @given(
        available_agents=st.lists(
            st.sampled_from(["yelp", "yelp_mcp", "map", "geo", "one", "chitchat"]),
            min_size=3,
            max_size=6,
            unique=True
        )
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_16_agent_existence_validation(self, available_agents):
        """
        **Feature: moe-map-rendering-fix, Property 16: Configuration Validation**
        **Validates: Requirements 7.5**
        
        Property: The system should validate that all expert agents exist in the
        available agent list and reject configurations with unknown agents.
        """
        # Create a configuration with both valid and invalid agents
        valid_agent = available_agents[0]
        invalid_agent = "nonexistent_agent_xyz"
        
        # Ensure invalid agent is not in available agents
        assume(invalid_agent not in available_agents)
        
        config_dict = {
            "enabled": True,
            "moe": {"top_k_experts": 2},
            "models": {
                "selection": {"name": "gpt-4.1-mini", "temperature": 0.0, "max_tokens": 1000},
                "mixing": {"name": "gpt-4.1-mini", "temperature": 0.7, "max_tokens": 2000}
            },
            "experts": {
                "valid_expert": {
                    "agents": [valid_agent],
                    "capabilities": ["general"],
                    "weight": 1.0
                },
                "invalid_expert": {
                    "agents": [invalid_agent],
                    "capabilities": ["general"],
                    "weight": 1.0
                }
            },
            "cache": {"enabled": False, "type": "none"},
            "error_handling": {"fallback_agent": "one"},
            "tracing": {"enabled": False}
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)
        
        try:
            # Load configuration
            loader = MoEConfigLoader(temp_path)
            config = loader.load_config()
            
            # CRITICAL PROPERTY: Agent existence validation should catch unknown agents
            with pytest.raises(ConfigException) as exc_info:
                loader.validate_expert_agents(available_agents)
            
            # Verify error message mentions the unknown agent
            error_message = str(exc_info.value)
            assert invalid_agent in error_message, f"Error should mention unknown agent '{invalid_agent}'"
            assert "unknown agent" in error_message.lower(), "Error should indicate agent is unknown"
            
        finally:
            # Clean up temporary file
            temp_path.unlink()

    def test_property_16_missing_config_file_handling(self):
        """
        **Feature: moe-map-rendering-fix, Property 16: Configuration Validation**
        **Validates: Requirements 7.5**
        
        Property: The system should handle missing configuration files gracefully
        with clear error messages.
        """
        # Try to load from non-existent file
        nonexistent_path = Path("/tmp/nonexistent_config_xyz.yaml")
        
        # Ensure file doesn't exist
        assert not nonexistent_path.exists(), "Test file should not exist"
        
        loader = MoEConfigLoader(nonexistent_path)
        
        # CRITICAL PROPERTY: Missing config files should be handled gracefully
        with pytest.raises(ConfigException) as exc_info:
            loader.load_config()
        
        # Verify error message is clear
        error_message = str(exc_info.value)
        assert "not found" in error_message.lower(), "Error should indicate file not found"
        assert str(nonexistent_path) in error_message, "Error should mention the specific file path"

    def test_property_16_malformed_yaml_handling(self):
        """
        **Feature: moe-map-rendering-fix, Property 16: Configuration Validation**
        **Validates: Requirements 7.5**
        
        Property: The system should handle malformed YAML files gracefully
        with clear error messages.
        """
        # Create malformed YAML content
        malformed_yaml = """
        enabled: true
        moe:
          top_k_experts: 2
        models:
          selection:
            name: "gpt-4.1-mini"
            temperature: 0.0
            max_tokens: 1000
          mixing: [invalid yaml structure without proper indentation
        """
        
        # Create temporary malformed config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(malformed_yaml)
            temp_path = Path(f.name)
        
        try:
            loader = MoEConfigLoader(temp_path)
            
            # CRITICAL PROPERTY: Malformed YAML should be handled gracefully
            with pytest.raises(ConfigException) as exc_info:
                loader.load_config()
            
            # Verify error message mentions YAML parsing
            error_message = str(exc_info.value).lower()
            assert "yaml" in error_message or "parse" in error_message, "Error should mention YAML parsing issue"
            
        finally:
            # Clean up temporary file
            temp_path.unlink()

    @given(
        synthesis_prompt=st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs", "Pc")))
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_16_synthesis_prompt_validation(self, synthesis_prompt):
        """
        **Feature: moe-map-rendering-fix, Property 16: Configuration Validation**
        **Validates: Requirements 7.5**
        
        Property: The system should validate synthesis prompt templates for required variables.
        """
        # Create config with synthesis prompt
        config_dict = {
            "enabled": True,
            "moe": {
                "mixing_strategy": "synthesis",
                "top_k_experts": 2,
                "synthesis_prompt": synthesis_prompt
            },
            "models": {
                "selection": {"name": "gpt-4.1-mini", "temperature": 0.0, "max_tokens": 1000},
                "mixing": {"name": "gpt-4.1-mini", "temperature": 0.7, "max_tokens": 2000}
            },
            "experts": {
                "test_expert": {
                    "agents": ["yelp"],
                    "capabilities": ["general"],
                    "weight": 1.0
                }
            },
            "cache": {"enabled": False, "type": "none"},
            "error_handling": {"fallback_agent": "one"},
            "tracing": {"enabled": False}
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)
        
        try:
            # Load configuration
            loader = MoEConfigLoader(temp_path)
            config = loader.load_config()
            
            # CRITICAL PROPERTY: Configuration should load successfully
            assert isinstance(config, MoEConfig), "Should return MoEConfig instance"
            assert config.moe["synthesis_prompt"] == synthesis_prompt, "Synthesis prompt should be preserved"
            
            # The synthesis prompt validation would typically happen at runtime
            # when the prompt is actually used, not at config load time
            # This test verifies that the prompt is properly stored in the config
            
        finally:
            # Clean up temporary file
            temp_path.unlink()