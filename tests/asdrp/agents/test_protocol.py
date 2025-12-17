#############################################################################
# test_protocol.py
#
# Comprehensive tests for Agent protocol, AgentException, AgentFactory, and get_agent.
#
# Test Coverage:
# - AgentProtocol interface compliance
# - AgentException creation and attributes
# - AgentFactory class (singleton, get_agent, register_agent)
# - get_agent convenience function with all agent types
# - Agent creation functions in their respective modules
# - Error handling (invalid names, missing dependencies)
# - Protocol runtime checks
#
#############################################################################

import pytest
from unittest.mock import patch, MagicMock
from typing import Any

from asdrp.agents.protocol import (
    AgentProtocol,
    AgentException,
)
from asdrp.agents.agent_factory import (
    AgentFactory,
    get_agent,
)
from asdrp.agents.single.geo_agent import create_geo_agent
from asdrp.agents.single.map_agent import create_map_agent
from asdrp.agents.single.yelp_agent import create_yelp_agent
from asdrp.agents.single.one_agent import create_one_agent


class TestAgentException:
    """Test AgentException class."""
    
    def test_agent_exception_with_message_only(self):
        """Test AgentException creation with message only."""
        exc = AgentException("Test error message")
        
        assert str(exc) == "Test error message"
        assert exc.message == "Test error message"
        assert exc.agent_name is None
    
    def test_agent_exception_with_agent_name(self):
        """Test AgentException creation with agent name."""
        exc = AgentException("Test error", agent_name="GeoAgent")
        
        assert "Test error" in str(exc)
        assert "GeoAgent" in str(exc)
        assert exc.message == "Test error"
        assert exc.agent_name == "GeoAgent"
    
    def test_agent_exception_inheritance(self):
        """Test that AgentException inherits from Exception."""
        exc = AgentException("Test")
        
        assert isinstance(exc, Exception)
        assert isinstance(exc, AgentException)


class TestAgentProtocol:
    """Test AgentProtocol interface."""
    
    @pytest.mark.asyncio
    async def test_agent_protocol_has_name_and_instructions(self):
        """Test that agents created via get_agent implement the protocol."""
        agent = await get_agent("geo", "Test instructions")
        
        # Check protocol attributes exist
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'instructions')
        assert isinstance(agent.name, str)
        assert isinstance(agent.instructions, str)
    
    @pytest.mark.asyncio
    async def test_agent_protocol_runtime_check(self):
        """Test that agents pass isinstance check for AgentProtocol."""
        agent = await get_agent("yelp", "Test instructions")
        
        # Runtime checkable protocol should work with isinstance
        assert isinstance(agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_all_agents_implement_protocol(self):
        """Test that all agent types implement the protocol."""
        agent_types = ["geo", "map", "yelp", "one"]
        
        for agent_type in agent_types:
            agent = await get_agent(agent_type, f"Test instructions for {agent_type}")
            assert isinstance(agent, AgentProtocol)
            assert hasattr(agent, 'name')
            assert hasattr(agent, 'instructions')


class TestGetAgent:
    """Test get_agent convenience function."""
    
    @pytest.mark.asyncio
    async def test_get_geo_agent(self):
        """Test creating GeoAgent via get_agent."""
        instructions = "You are a geocoding assistant"
        agent = await get_agent("geo", instructions)
        
        assert agent.name == "GeoAgent"
        assert agent.instructions == instructions
        assert isinstance(agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_get_yelp_agent(self):
        """Test creating YelpAgent via get_agent."""
        instructions = "You help find restaurants"
        agent = await get_agent("yelp", instructions)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == instructions
        assert isinstance(agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_get_one_agent(self):
        """Test creating OneAgent via get_agent."""
        instructions = "You are a research assistant"
        agent = await get_agent("one", instructions)
        
        assert agent.name == "OneAgent"
        assert agent.instructions == instructions
        assert isinstance(agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_get_agent_case_insensitive(self):
        """Test that agent names are case-insensitive."""
        agent1 = await get_agent("GEO", "Test")
        agent2 = await get_agent("geo", "Test")
        agent3 = await get_agent("Geo", "Test")
        
        assert agent1.name == agent2.name == agent3.name == "GeoAgent"
    
    @pytest.mark.asyncio
    async def test_get_agent_whitespace_handling(self):
        """Test that agent names handle whitespace correctly."""
        agent = await get_agent("  geo  ", "Test")
        
        assert agent.name == "GeoAgent"
    
    @pytest.mark.asyncio
    async def test_get_agent_invalid_name(self):
        """Test that invalid agent name raises AgentException."""
        with pytest.raises(AgentException) as exc_info:
            await get_agent("invalid_agent", "Test")
        
        assert exc_info.value.agent_name == "invalid_agent"
        assert "Unknown agent name" in str(exc_info.value)
        assert "invalid_agent" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_agent_empty_name(self):
        """Test that empty agent name raises AgentException."""
        with pytest.raises(AgentException):
            await get_agent("", "Test")
    
    @pytest.mark.asyncio
    async def test_get_agent_custom_instructions(self):
        """Test that custom instructions are used."""
        custom_instructions = "Custom instructions for testing"
        agent = await get_agent("geo", custom_instructions)
        
        assert agent.instructions == custom_instructions


class TestAgentFactory:
    """Test AgentFactory class."""
    
    def test_agent_factory_initialization(self):
        """Test AgentFactory can be instantiated."""
        factory = AgentFactory()
        assert factory is not None
        assert isinstance(factory, AgentFactory)
    
    def test_agent_factory_singleton(self):
        """Test AgentFactory singleton pattern."""
        factory1 = AgentFactory.instance()
        factory2 = AgentFactory.instance()
        
        assert factory1 is factory2
        assert factory1 is AgentFactory._instance
    
    @pytest.mark.asyncio
    async def test_agent_factory_get_geo_agent(self):
        """Test creating GeoAgent via AgentFactory."""
        factory = AgentFactory()
        instructions = "You are a geocoding assistant"
        agent = await factory.get_agent("geo", instructions)
        
        assert agent.name == "GeoAgent"
        assert agent.instructions == instructions
        assert isinstance(agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_agent_factory_get_yelp_agent(self):
        """Test creating YelpAgent via AgentFactory."""
        factory = AgentFactory()
        instructions = "You help find restaurants"
        agent = await factory.get_agent("yelp", instructions)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == instructions
        assert isinstance(agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_agent_factory_get_one_agent(self):
        """Test creating OneAgent via AgentFactory."""
        factory = AgentFactory()
        instructions = "You are a research assistant"
        agent = await factory.get_agent("one", instructions)
        
        assert agent.name == "OneAgent"
        assert agent.instructions == instructions
        assert isinstance(agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_agent_factory_case_insensitive(self):
        """Test that agent names are case-insensitive."""
        factory = AgentFactory()
        agent1 = await factory.get_agent("GEO", "Test")
        agent2 = await factory.get_agent("geo", "Test")
        agent3 = await factory.get_agent("Geo", "Test")
        
        assert agent1.name == agent2.name == agent3.name == "GeoAgent"
    
    @pytest.mark.asyncio
    async def test_agent_factory_invalid_name(self):
        """Test that invalid agent name raises AgentException."""
        factory = AgentFactory()
        with pytest.raises(AgentException) as exc_info:
            await factory.get_agent("invalid_agent", "Test")
        
        assert exc_info.value.agent_name == "invalid_agent"
        assert "Unknown agent name" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_agent_factory_protocol_validation(self):
        """Test that AgentFactory validates protocol compliance."""
        # Create a factory with a custom config that includes test agent
        import yaml
        import tempfile
        from pathlib import Path
        
        config_data = {
            "agents": {
                "test_validation": {
                    "display_name": "TestAgent",
                    "module": "asdrp.agents.single.geo_agent",
                    "function": "create_geo_agent",
                    "default_instructions": "Test",
                    "enabled": True
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            factory = AgentFactory(config_path=temp_path)
            # Override the creation function to return non-compliant agent
            mock_agent = MagicMock()
            mock_agent.name = "TestAgent"
            if hasattr(mock_agent, 'instructions'):
                delattr(mock_agent, 'instructions')
            
            factory.register_agent("test_validation", lambda instructions, model_config=None: mock_agent)
            
            with pytest.raises(AgentException) as exc_info:
                await factory.get_agent("test_validation", "Test")
            
            assert "did not return a valid AgentProtocol instance" in str(exc_info.value)
        finally:
            temp_path.unlink()
    
    def test_agent_factory_register_agent(self):
        """Test registering a new agent type."""
        factory = AgentFactory()
        
        def create_test_agent(instructions: str) -> AgentProtocol:
            from agents import Agent
            return Agent(name="TestAgent", instructions=instructions, tools=[])
        
        factory.register_agent("test", create_test_agent)
        
        # Verify it's registered
        registry = factory._get_registry()
        assert "test" in registry
        assert registry["test"] == create_test_agent
    
    def test_agent_factory_register_agent_empty_name(self):
        """Test that empty agent name raises ValueError."""
        factory = AgentFactory()
        
        def create_test_agent(instructions: str) -> AgentProtocol:
            pass
        
        with pytest.raises(ValueError, match="cannot be empty"):
            factory.register_agent("", create_test_agent)
    
    def test_agent_factory_register_agent_invalid_callable(self):
        """Test that non-callable factory raises ValueError."""
        factory = AgentFactory()
        
        with pytest.raises(ValueError, match="must be callable"):
            factory.register_agent("test", "not a callable")
    
    @pytest.mark.asyncio
    async def test_agent_factory_registered_agent(self):
        """Test using a registered agent."""
        import yaml
        import tempfile
        from pathlib import Path
        
        config_data = {
            "agents": {
                "test": {
                    "display_name": "TestAgent",
                    "module": "asdrp.agents.single.geo_agent",
                    "function": "create_geo_agent",
                    "default_instructions": "Test",
                    "enabled": True
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            factory = AgentFactory(config_path=temp_path)
            
            def create_test_agent(instructions: str, model_config=None) -> AgentProtocol:
                from agents import Agent
                return Agent(name="TestAgent", instructions=instructions, tools=[])
            
            factory.register_agent("test", create_test_agent)
            agent = await factory.get_agent("test", "Test instructions")
            
            assert agent.name == "TestAgent"
            assert agent.instructions == "Test instructions"
        finally:
            temp_path.unlink()


class TestAgentFactories:
    """Test individual agent factory functions."""
    
    def test_create_geo_agent_success(self):
        """Test successful GeoAgent creation."""
        instructions = "Test instructions"
        agent = create_geo_agent(instructions)
        
        assert agent.name == "GeoAgent"
        assert agent.instructions == instructions
        assert hasattr(agent, 'tools')
    
    def test_create_yelp_agent_success(self):
        """Test successful YelpAgent creation."""
        instructions = "Test instructions"
        agent = create_yelp_agent(instructions)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == instructions
        assert hasattr(agent, 'tools')
    
    def test_create_one_agent_success(self):
        """Test successful OneAgent creation."""
        instructions = "Test instructions"
        agent = create_one_agent(instructions)
        
        assert agent.name == "OneAgent"
        assert agent.instructions == instructions
        assert hasattr(agent, 'tools')
    
    def test_create_geo_agent_invalid_model_config(self):
        """Test GeoAgent creation with invalid model config.
        
        Note: Since Agent and GeoTools are imported at module level in geo_agent.py,
        we cannot easily mock import errors. Instead, we test error handling
        with invalid configuration that causes a runtime error.
        """
        from asdrp.agents.config_loader import ModelConfig
        
        # Create a mock model config that will cause an error
        mock_config = MagicMock(spec=ModelConfig)
        mock_config.name = None  # Invalid - will cause error in ModelSettings
        mock_config.temperature = "invalid"  # Invalid type
        mock_config.max_tokens = "invalid"  # Invalid type
        
        # This should raise an AgentException wrapping the underlying error
        with pytest.raises(AgentException) as exc_info:
            create_geo_agent("Test", mock_config)
        
        assert exc_info.value.agent_name == "geo"
        assert "Failed to create" in str(exc_info.value)
    
    def test_create_yelp_agent_import_error(self):
        """Test YelpAgent creation with import error."""
        with patch('asdrp.actions.local.yelp_tools.YelpTools', side_effect=ImportError("No module")):
            with pytest.raises(AgentException) as exc_info:
                create_yelp_agent("Test")
            
            assert exc_info.value.agent_name == "yelp"
            assert "Failed to import" in str(exc_info.value) or "Failed to create" in str(exc_info.value)
    
    def test_create_one_agent_import_error(self):
        """Test OneAgent creation with import error."""
        with patch('agents.WebSearchTool', side_effect=ImportError("No module")):
            with pytest.raises(AgentException) as exc_info:
                create_one_agent("Test")
            
            assert exc_info.value.agent_name == "one"
            assert "Failed to import" in str(exc_info.value) or "Failed to create" in str(exc_info.value)
    
    def test_agent_creation_functions_in_correct_modules(self):
        """Test that agent creation functions are in their respective modules."""
        # Verify public functions are importable from correct modules
        from asdrp.agents.single.geo_agent import create_geo_agent
        from asdrp.agents.single.map_agent import create_map_agent
        from asdrp.agents.single.yelp_agent import create_yelp_agent
        from asdrp.agents.single.one_agent import create_one_agent
        
        assert callable(create_geo_agent)
        assert callable(create_map_agent)
        assert callable(create_yelp_agent)
        assert callable(create_one_agent)


class TestAgentIntegration:
    """Integration tests for agent creation and usage."""
    
    @pytest.mark.asyncio
    async def test_agent_creation_flow(self):
        """Test complete agent creation flow."""
        # Create all agent types
        geo_agent = await get_agent("geo", "Geo instructions")
        map_agent = await get_agent("map", "Map instructions")
        yelp_agent = await get_agent("yelp", "Yelp instructions")
        one_agent = await get_agent("one", "One instructions")
        
        # Verify all agents are created successfully
        assert geo_agent.name == "GeoAgent"
        assert map_agent.name == "MapAgent"
        assert yelp_agent.name == "YelpAgent"
        assert one_agent.name == "OneAgent"
        
        # Verify all implement protocol
        assert isinstance(geo_agent, AgentProtocol)
        assert isinstance(map_agent, AgentProtocol)
        assert isinstance(yelp_agent, AgentProtocol)
        assert isinstance(one_agent, AgentProtocol)
    
    @pytest.mark.asyncio
    async def test_agent_instructions_preserved(self):
        """Test that instructions are preserved correctly."""
        instructions = "Very specific instructions for testing"
        agent = await get_agent("geo", instructions)
        
        assert agent.instructions == instructions
    
    @pytest.mark.asyncio
    async def test_multiple_agents_same_type(self):
        """Test creating multiple agents of the same type."""
        agent1 = await get_agent("geo", "Instructions 1")
        agent2 = await get_agent("geo", "Instructions 2")
        
        # Should be different instances
        assert agent1 is not agent2
        assert agent1.name == agent2.name == "GeoAgent"
        assert agent1.instructions != agent2.instructions

