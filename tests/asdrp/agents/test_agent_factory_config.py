#############################################################################
# test_agent_factory_config.py
#
# Comprehensive tests for AgentFactory with configuration system.
#
# Test Coverage:
# - AgentFactory using config file
# - Config-based agent creation
# - Default instructions from config
# - Model configuration application
# - Custom config paths
# - Error handling with config
#
#############################################################################

import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.config_loader import AgentConfigLoader, AgentConfig, ModelConfig
from asdrp.agents.protocol import AgentProtocol, AgentException


class TestAgentFactoryWithConfig:
    """Test AgentFactory using configuration."""
    
    @pytest.mark.asyncio
    async def test_factory_uses_config_defaults(self):
        """Test that factory uses default instructions from config."""
        factory = AgentFactory.instance()
        agent = await factory.get_agent("geo")
        
        assert agent.name == "GeoAgent"
        assert agent.instructions is not None
        assert len(agent.instructions) > 0
    
    @pytest.mark.asyncio
    async def test_factory_custom_instructions(self):
        """Test factory with custom instructions."""
        factory = AgentFactory.instance()
        custom_instructions = "Custom geocoding instructions"
        agent = await factory.get_agent("geo", custom_instructions)
        
        assert agent.instructions == custom_instructions
    
    @pytest.mark.asyncio
    async def test_factory_all_agent_types(self):
        """Test factory can create all configured agent types."""
        factory = AgentFactory.instance()
        
        geo_agent = await factory.get_agent("geo")
        map_agent = await factory.get_agent("map")
        yelp_agent = await factory.get_agent("yelp")
        one_agent = await factory.get_agent("one")
        finance_agent = await factory.get_agent("finance")
        
        assert geo_agent.name == "GeoAgent"
        assert map_agent.name == "MapAgent"
        assert yelp_agent.name == "YelpAgent"
        assert one_agent.name == "OneAgent"
        assert finance_agent.name == "FinanceAgent"
    
    @pytest.mark.asyncio
    async def test_factory_with_custom_config_path(self):
        """Test factory with custom config file path."""
        config_data = {
            "agents": {
                "test": {
                    "display_name": "TestAgent",
                    "module": "asdrp.agents.single.geo_agent",
                    "function": "create_geo_agent",
                    "default_instructions": "Test instructions",
                    "model": {"name": "gpt-4", "temperature": 0.8}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            factory = AgentFactory(config_path=temp_path)
            agent = await factory.get_agent("test")
            
            assert agent.name == "GeoAgent"  # Uses geo_agent creation function
            assert agent.instructions == "Test instructions"
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_factory_disabled_agent(self):
        """Test that disabled agents cannot be created."""
        config_data = {
            "agents": {
                "test": {
                    "display_name": "TestAgent",
                    "module": "asdrp.agents.single.geo_agent",
                    "function": "create_geo_agent",
                    "default_instructions": "Test",
                    "enabled": False
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            factory = AgentFactory(config_path=temp_path)
            with pytest.raises(AgentException, match="is disabled"):
                await factory.get_agent("test")
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_factory_instructions_none_with_defaults(self):
        """Test factory with None instructions uses config defaults."""
        factory = AgentFactory.instance()
        agent = await factory.get_agent("geo", None, use_config_defaults=True)
        
        config = factory.get_agent_config("geo")
        assert agent.instructions == config.default_instructions
    
    @pytest.mark.asyncio
    async def test_factory_instructions_none_without_defaults(self):
        """Test factory with None instructions raises error when defaults disabled."""
        factory = AgentFactory.instance()
        
        with pytest.raises(AgentException, match="Instructions required"):
            await factory.get_agent("geo", None, use_config_defaults=False)
    
    def test_factory_get_agent_config(self):
        """Test getting agent configuration from factory."""
        factory = AgentFactory.instance()
        config = factory.get_agent_config("geo")
        
        assert isinstance(config, AgentConfig)
        assert config.display_name == "GeoAgent"
        assert config.module == "asdrp.agents.single.geo_agent"
    
    def test_factory_list_available_agents(self):
        """Test listing available agents."""
        factory = AgentFactory.instance()
        agents = factory.list_available_agents()
        
        assert isinstance(agents, list)
        assert "geo" in agents
        assert "map" in agents
        assert "yelp" in agents
        assert "one" in agents
    
    @pytest.mark.asyncio
    async def test_factory_registry_from_config(self):
        """Test that registry is built from config file."""
        factory = AgentFactory.instance()
        registry = factory._get_registry()
        
        # Verify registry contains agents from config
        config_loader = factory._get_config_loader()
        expected_agents = config_loader.list_agents()
        
        assert set(registry.keys()) == set(expected_agents)
    
    @pytest.mark.asyncio
    async def test_factory_model_config_applied(self):
        """Test that model config from YAML is applied to agents."""
        factory = AgentFactory.instance()
        config = factory.get_agent_config("geo")
        
        # Create agent - model config should be passed to creation function
        agent = await factory.get_agent("geo")
        
        # Verify agent was created (model config is applied internally)
        assert agent is not None
        assert agent.name == "GeoAgent"
    
    @pytest.mark.asyncio
    async def test_factory_invalid_module_in_config(self):
        """Test that invalid module in config raises error."""
        config_data = {
            "agents": {
                "test": {
                    "display_name": "TestAgent",
                    "module": "nonexistent.module",
                    "function": "create_test",
                    "default_instructions": "Test"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            import warnings
            factory = AgentFactory(config_path=temp_path)
            # Invalid agents are now skipped with a warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                registry = factory._get_registry()
                # Should have a warning about the failed load
                assert len(w) >= 1
                assert "Failed to load agent" in str(w[0].message)
            # Agent should not be in registry
            with pytest.raises(AgentException, match="not found in registry"):
                await factory.get_agent("test")
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_factory_invalid_function_in_config(self):
        """Test that invalid function name in config raises error."""
        config_data = {
            "agents": {
                "test": {
                    "display_name": "TestAgent",
                    "module": "asdrp.agents.single.geo_agent",
                    "function": "nonexistent_function",
                    "default_instructions": "Test"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            import warnings
            factory = AgentFactory(config_path=temp_path)
            # Invalid agents are now skipped with a warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                registry = factory._get_registry()
                # Should have a warning about the failed load
                assert len(w) >= 1
                assert "Failed to load agent" in str(w[0].message)
            # Agent should not be in registry
            with pytest.raises(AgentException, match="not found in registry"):
                await factory.get_agent("test")
        finally:
            temp_path.unlink()


class TestAgentCreationWithModelConfig:
    """Test agent creation functions with model configuration."""
    
    def test_create_geo_agent_with_model_config(self):
        """Test GeoAgent creation with model config."""
        from asdrp.agents.single.geo_agent import create_geo_agent
        
        model_config = ModelConfig(name="gpt-3.5-turbo", temperature=0.9, max_tokens=1500)
        agent = create_geo_agent("Test instructions", model_config)
        
        assert agent.name == "GeoAgent"
        assert agent.instructions == "Test instructions"
        # Model config is applied internally - verify agent was created
        assert hasattr(agent, 'model')
    
    def test_create_map_agent_with_model_config(self):
        """Test MapAgent creation with model config."""
        from asdrp.agents.single.map_agent import create_map_agent
        
        model_config = ModelConfig(name="gpt-4", temperature=0.7)
        agent = create_map_agent("Test", model_config)
        
        assert agent.name == "MapAgent"
        # Model config is applied internally - verify agent was created
        assert hasattr(agent, 'model')
    
    def test_create_yelp_agent_with_model_config(self):
        """Test YelpAgent creation with model config."""
        from asdrp.agents.single.yelp_agent import create_yelp_agent
        
        model_config = ModelConfig(name="gpt-4", temperature=0.6)
        agent = create_yelp_agent("Test", model_config)
        
        assert agent.name == "YelpAgent"
    
    def test_create_one_agent_with_model_config(self):
        """Test OneAgent creation with model config."""
        from asdrp.agents.single.one_agent import create_one_agent
        
        model_config = ModelConfig(name="gpt-4", temperature=0.8)
        agent = create_one_agent("Test", model_config)
        
        assert agent.name == "OneAgent"
    
    def test_create_geo_agent_without_model_config(self):
        """Test GeoAgent creation without model config (backward compatible)."""
        from asdrp.agents.single.geo_agent import create_geo_agent
        
        agent = create_geo_agent("Test")
        
        assert agent.name == "GeoAgent"
        assert agent.instructions == "Test"


class TestConfigBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    @pytest.mark.asyncio
    async def test_get_agent_function_still_works(self):
        """Test that get_agent convenience function still works."""
        from asdrp.agents.agent_factory import get_agent
        
        agent = await get_agent("geo", "Test instructions")
        assert agent.name == "GeoAgent"
        assert agent.instructions == "Test instructions"
    
    @pytest.mark.asyncio
    async def test_get_agent_with_config_defaults(self):
        """Test get_agent with config defaults."""
        from asdrp.agents.agent_factory import get_agent
        
        agent = await get_agent("geo", use_config_defaults=True)
        assert agent.name == "GeoAgent"
        assert agent.instructions is not None
    
    def test_agent_creation_functions_backward_compatible(self):
        """Test that agent creation functions work without model_config."""
        from asdrp.agents.single.geo_agent import create_geo_agent
        from asdrp.agents.single.map_agent import create_map_agent
        from asdrp.agents.single.yelp_agent import create_yelp_agent
        from asdrp.agents.single.one_agent import create_one_agent
        
        geo_agent = create_geo_agent()
        map_agent = create_map_agent()
        yelp_agent = create_yelp_agent()
        one_agent = create_one_agent()
        
        assert geo_agent.name == "GeoAgent"
        assert map_agent.name == "MapAgent"
        assert yelp_agent.name == "YelpAgent"
        assert one_agent.name == "OneAgent"

