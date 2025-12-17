#############################################################################
# test_config_loader.py
#
# Comprehensive tests for AgentConfigLoader and configuration system.
#
# Test Coverage:
# - Config file loading and parsing
# - AgentConfig and ModelConfig dataclasses
# - Configuration validation
# - Default value handling
# - Error handling (missing files, invalid YAML, missing keys)
# - Agent listing and enabled status
#
#############################################################################

import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from asdrp.agents.config_loader import (
    AgentConfigLoader,
    AgentConfig,
    ModelConfig,
    SessionMemoryConfig,
)
from asdrp.agents.protocol import AgentException


class TestModelConfig:
    """Test ModelConfig dataclass."""
    
    def test_model_config_creation(self):
        """Test creating ModelConfig with all parameters."""
        config = ModelConfig(name="gpt-4.1-mini", temperature=0.8, max_tokens=3000)
        
        assert config.name == "gpt-4.1-mini"
        assert config.temperature == 0.8
        assert config.max_tokens == 3000
    
    def test_model_config_defaults(self):
        """Test ModelConfig with default values."""
        config = ModelConfig(name="gpt-4.1-mini")
        
        assert config.name == "gpt-4.1-mini"
        assert config.temperature == 0.7  # Default
        assert config.max_tokens == 2000  # Default
    
    def test_model_config_temperature_validation(self):
        """Test that invalid temperature raises ValueError."""
        with pytest.raises(ValueError, match="Temperature must be between"):
            ModelConfig(name="gpt-4.1-mini", temperature=3.0)
        
        with pytest.raises(ValueError, match="Temperature must be between"):
            ModelConfig(name="gpt-4.1-mini", temperature=-1.0)
    
    def test_model_config_max_tokens_validation(self):
        """Test that invalid max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ModelConfig(name="gpt-4.1-mini", max_tokens=0)
        
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ModelConfig(name="gpt-4.1-mini", max_tokens=-1)


class TestAgentConfig:
    """Test AgentConfig dataclass."""
    
    def test_agent_config_creation(self):
        """Test creating AgentConfig with all parameters."""
        model_config = ModelConfig(name="gpt-4.1-mini", temperature=0.7)
        session_config = SessionMemoryConfig(type="sqlite", enabled=True)
        agent_config = AgentConfig(
            display_name="TestAgent",
            module="test.module",
            function="create_test",
            default_instructions="Test instructions",
            model=model_config,
            session_memory=session_config,
            enabled=True
        )
        
        assert agent_config.display_name == "TestAgent"
        assert agent_config.module == "test.module"
        assert agent_config.function == "create_test"
        assert agent_config.default_instructions == "Test instructions"
        assert agent_config.model == model_config
        assert agent_config.session_memory == session_config
        assert agent_config.enabled is True
    
    def test_agent_config_default_enabled(self):
        """Test that enabled defaults to True."""
        model_config = ModelConfig(name="gpt-4.1-mini")
        session_config = SessionMemoryConfig()
        agent_config = AgentConfig(
            display_name="Test",
            module="test",
            function="create",
            default_instructions="",
            model=model_config,
            session_memory=session_config
        )
        
        assert agent_config.enabled is True


class TestAgentConfigLoader:
    """Test AgentConfigLoader class."""
    
    def test_config_loader_with_default_path(self):
        """Test config loader with default path."""
        loader = AgentConfigLoader()
        
        assert loader._config_path is not None
        assert loader._config_path.exists()
        assert loader._config_path.name == "open_agents.yaml"
    
    def test_config_loader_with_custom_path(self):
        """Test config loader with custom path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"agents": {}}, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            assert loader._config_path == temp_path
        finally:
            temp_path.unlink()
    
    def test_config_loader_missing_file(self):
        """Test that missing config file raises AgentException."""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.yaml"
            
            with pytest.raises(AgentException, match="not found"):
                AgentConfigLoader(missing_path)
    
    def test_load_config_success(self):
        """Test successful config loading."""
        config_data = {
            "agents": {
                "test": {
                    "display_name": "TestAgent",
                    "module": "test.module",
                    "function": "create_test",
                    "default_instructions": "Test",
                    "model": {"name": "gpt-4.1-mini"}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            config = loader._load_config()
            
            assert isinstance(config, dict)
            assert "agents" in config
            assert "test" in config["agents"]
        finally:
            temp_path.unlink()
    
    def test_load_config_invalid_yaml(self):
        """Test that invalid YAML raises AgentException."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            with pytest.raises(AgentException, match="Failed to parse"):
                loader._load_config()
        finally:
            temp_path.unlink()
    
    def test_load_config_missing_agents_section(self):
        """Test that missing agents section raises AgentException."""
        config_data = {"other": "data"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            with pytest.raises(AgentException, match="missing required 'agents' section"):
                loader._load_config()
        finally:
            temp_path.unlink()
    
    def test_get_agent_config_success(self):
        """Test getting agent config successfully."""
        loader = AgentConfigLoader()
        config = loader.get_agent_config("geo")
        
        assert isinstance(config, AgentConfig)
        assert config.display_name == "GeoAgent"
        assert config.module == "asdrp.agents.single.geo_agent"
        assert config.function == "create_geo_agent"
        assert isinstance(config.model, ModelConfig)
        # Verify model config is valid (not checking specific value to avoid fragility)
        assert isinstance(config.model.name, str)
        assert len(config.model.name) > 0
        assert 0.0 <= config.model.temperature <= 2.0
        assert config.model.max_tokens > 0
    
    def test_get_agent_config_case_insensitive(self):
        """Test that agent names are case-insensitive."""
        loader = AgentConfigLoader()
        config1 = loader.get_agent_config("GEO")
        config2 = loader.get_agent_config("geo")
        config3 = loader.get_agent_config("Geo")
        
        assert config1.display_name == config2.display_name == config3.display_name
    
    def test_get_agent_config_not_found(self):
        """Test that unknown agent raises AgentException."""
        loader = AgentConfigLoader()
        
        with pytest.raises(AgentException, match="not found in configuration"):
            loader.get_agent_config("unknown_agent")
    
    def test_get_agent_config_missing_required_key(self):
        """Test that missing required key raises AgentException."""
        config_data = {
            "agents": {
                "test": {
                    "display_name": "Test"
                    # Missing module and function
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            with pytest.raises(AgentException, match="Missing required configuration key"):
                loader.get_agent_config("test")
        finally:
            temp_path.unlink()
    
    def test_get_agent_config_uses_defaults(self):
        """Test that agent config uses global defaults when not specified."""
        config_data = {
            "agents": {
                "test": {
                    "module": "test.module",
                    "function": "create_test",
                    "default_instructions": "Test"
                }
            },
            "defaults": {
                "model": {
                    "name": "gpt-4.1-mini",
                    "temperature": 0.9,
                    "max_tokens": 1500
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            config = loader.get_agent_config("test")
            
            assert config.model.name == "gpt-4.1-mini"
            assert config.model.temperature == 0.9
            assert config.model.max_tokens == 1500
        finally:
            temp_path.unlink()
    
    def test_list_agents(self):
        """Test listing available agents."""
        loader = AgentConfigLoader()
        agents = loader.list_agents()
        
        assert isinstance(agents, list)
        assert "geo" in agents
        assert "yelp" in agents
        assert "one" in agents
    
    def test_list_agents_excludes_disabled(self):
        """Test that disabled agents are excluded from list."""
        config_data = {
            "agents": {
                "enabled_agent": {
                    "module": "test.module",
                    "function": "create",
                    "default_instructions": "Test",
                    "enabled": True
                },
                "disabled_agent": {
                    "module": "test.module",
                    "function": "create",
                    "default_instructions": "Test",
                    "enabled": False
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            agents = loader.list_agents()
            
            assert "enabled_agent" in agents
            assert "disabled_agent" not in agents
        finally:
            temp_path.unlink()
    
    def test_is_agent_enabled(self):
        """Test checking if agent is enabled."""
        loader = AgentConfigLoader()
        
        assert loader.is_agent_enabled("geo") is True
        assert loader.is_agent_enabled("unknown") is False
    
    def test_is_agent_enabled_disabled_agent(self):
        """Test checking disabled agent."""
        config_data = {
            "agents": {
                "test": {
                    "module": "test.module",
                    "function": "create",
                    "default_instructions": "Test",
                    "enabled": False
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            assert loader.is_agent_enabled("test") is False
        finally:
            temp_path.unlink()
    
    def test_reload_config(self):
        """Test reloading configuration."""
        config_data1 = {
            "agents": {
                "test": {
                    "module": "test.module",
                    "function": "create",
                    "default_instructions": "Original"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data1, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            config1 = loader.get_agent_config("test")
            
            # Modify config file
            config_data2 = config_data1.copy()
            config_data2["agents"]["test"]["default_instructions"] = "Updated"
            with open(temp_path, 'w') as f:
                yaml.dump(config_data2, f)
            
            # Reload and verify change
            loader.reload_config()
            config2 = loader.get_agent_config("test")
            
            assert config1.default_instructions == "Original"
            assert config2.default_instructions == "Updated"
        finally:
            temp_path.unlink()


class TestConfigIntegration:
    """Integration tests for config loader with real config file."""
    
    def test_load_real_config(self):
        """Test loading the actual config file."""
        loader = AgentConfigLoader()
        
        # Test all agents exist
        for agent_name in ["geo", "yelp", "one"]:
            config = loader.get_agent_config(agent_name)
            assert config.enabled is True
            assert config.display_name is not None
            assert config.module is not None
            assert config.function is not None
            assert config.default_instructions is not None
            assert config.model.name is not None
            assert 0.0 <= config.model.temperature <= 2.0
            assert config.model.max_tokens > 0

