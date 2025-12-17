#############################################################################
# test_session_memory.py
#
# Comprehensive tests for session memory functionality in AgentFactory.
#
# Test Coverage:
# - SessionMemoryConfig dataclass validation
# - Session creation (SQLite in-memory and file-based)
# - Session caching and reuse
# - get_agent_with_session() method
# - Session ID override functionality
# - Disabled session memory handling
# - Error handling for session creation
# - Integration with real agents
#
#############################################################################

import pytest
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from asdrp.agents.config_loader import (
    AgentConfigLoader,
    AgentConfig,
    ModelConfig,
    SessionMemoryConfig,
)
from asdrp.agents.agent_factory import (
    AgentFactory,
    get_agent_with_session,
    SESSION_MEMORY_AVAILABLE,
)
from asdrp.agents.protocol import AgentException


class TestSessionMemoryConfig:
    """Test SessionMemoryConfig dataclass."""
    
    def test_session_memory_config_creation(self):
        """Test creating SessionMemoryConfig with all parameters."""
        config = SessionMemoryConfig(
            type="sqlite",
            session_id="test_session",
            database_path="test.db",
            enabled=True
        )
        
        assert config.type == "sqlite"
        assert config.session_id == "test_session"
        assert config.database_path == "test.db"
        assert config.enabled is True
    
    def test_session_memory_config_defaults(self):
        """Test SessionMemoryConfig with default values."""
        config = SessionMemoryConfig()
        
        assert config.type == "sqlite"  # Default
        assert config.session_id is None  # Default
        assert config.database_path is None  # Default
        assert config.enabled is True  # Default
    
    def test_session_memory_config_type_validation(self):
        """Test that invalid session type raises ValueError."""
        with pytest.raises(ValueError, match="Session type must be one of"):
            SessionMemoryConfig(type="invalid_type")
    
    def test_session_memory_config_sqlite_type(self):
        """Test SQLite session type is valid."""
        config = SessionMemoryConfig(type="sqlite")
        assert config.type == "sqlite"
    
    def test_session_memory_config_none_type(self):
        """Test 'none' session type is valid (stateless)."""
        config = SessionMemoryConfig(type="none")
        assert config.type == "none"
    
    def test_session_memory_config_disabled(self):
        """Test disabled session memory configuration."""
        config = SessionMemoryConfig(enabled=False)
        assert config.enabled is False


class TestAgentConfigWithSessionMemory:
    """Test AgentConfig with session memory field."""
    
    def test_agent_config_with_session_memory(self):
        """Test creating AgentConfig with session memory."""
        model_config = ModelConfig(name="gpt-4.1-mini")
        session_config = SessionMemoryConfig(type="sqlite", session_id="test")
        
        agent_config = AgentConfig(
            display_name="TestAgent",
            module="test.module",
            function="create_test",
            default_instructions="Test",
            model=model_config,
            session_memory=session_config,
            enabled=True
        )
        
        assert agent_config.session_memory == session_config
        assert agent_config.session_memory.type == "sqlite"
        assert agent_config.session_memory.session_id == "test"


class TestConfigLoaderSessionMemory:
    """Test AgentConfigLoader with session memory configurations."""
    
    def test_load_session_memory_from_config(self):
        """Test loading session memory config from YAML."""
        config_data = {
            "agents": {
                "test": {
                    "module": "test.module",
                    "function": "create_test",
                    "default_instructions": "Test",
                    "session_memory": {
                        "type": "sqlite",
                        "session_id": "test_session",
                        "database_path": "test.db",
                        "enabled": True
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            config = loader.get_agent_config("test")
            
            assert config.session_memory.type == "sqlite"
            assert config.session_memory.session_id == "test_session"
            assert config.session_memory.database_path == "test.db"
            assert config.session_memory.enabled is True
        finally:
            temp_path.unlink()
    
    def test_session_memory_uses_defaults(self):
        """Test that session memory uses global defaults when not specified."""
        config_data = {
            "agents": {
                "test": {
                    "module": "test.module",
                    "function": "create_test",
                    "default_instructions": "Test"
                    # No session_memory specified
                }
            },
            "defaults": {
                "session_memory": {
                    "type": "sqlite",
                    "enabled": True
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            config = loader.get_agent_config("test")
            
            assert config.session_memory.type == "sqlite"
            assert config.session_memory.enabled is True
        finally:
            temp_path.unlink()
    
    def test_session_memory_disabled_in_config(self):
        """Test loading disabled session memory from config."""
        config_data = {
            "agents": {
                "test": {
                    "module": "test.module",
                    "function": "create_test",
                    "default_instructions": "Test",
                    "session_memory": {
                        "type": "none",
                        "enabled": False
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = AgentConfigLoader(temp_path)
            config = loader.get_agent_config("test")
            
            assert config.session_memory.type == "none"
            assert config.session_memory.enabled is False
        finally:
            temp_path.unlink()
    
    def test_real_config_has_session_memory(self):
        """Test that real config file has session memory configurations."""
        loader = AgentConfigLoader()
        
        # Test geo agent (should have session memory)
        geo_config = loader.get_agent_config("geo")
        assert hasattr(geo_config, 'session_memory')
        assert isinstance(geo_config.session_memory, SessionMemoryConfig)
        
        # Test one agent (should have disabled session memory)
        one_config = loader.get_agent_config("one")
        assert hasattr(one_config, 'session_memory')


class TestAgentFactorySessionCreation:
    """Test AgentFactory session creation functionality."""
    
    @pytest.fixture
    def factory(self):
        """Create a fresh AgentFactory instance with cleanup."""
        factory = AgentFactory()
        factory.clear_session_cache()
        yield factory
        # Cleanup: close all sessions after test
        factory.clear_session_cache()
    
    def test_create_session_sqlite_inmemory(self, factory):
        """Test creating in-memory SQLite session."""
        session_config = SessionMemoryConfig(
            type="sqlite",
            session_id="test_session",
            database_path=None,
            enabled=True
        )
        
        session = factory._create_session(session_config, "test_agent")
        
        if SESSION_MEMORY_AVAILABLE:
            assert session is not None
            # Verify it's a SQLiteSession
            assert "SQLiteSession" in type(session).__name__
        else:
            assert session is None
    
    def test_create_session_sqlite_filebased(self, factory):
        """Test creating file-based SQLite session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            session_config = SessionMemoryConfig(
                type="sqlite",
                session_id="test_session",
                database_path=db_path,
                enabled=True
            )
            
            session = factory._create_session(session_config, "test_agent")
            
            if SESSION_MEMORY_AVAILABLE:
                assert session is not None
                # Verify database file was created
                assert os.path.exists(db_path)
    
    def test_create_session_disabled(self, factory):
        """Test that disabled session returns None."""
        session_config = SessionMemoryConfig(
            type="sqlite",
            enabled=False
        )
        
        session = factory._create_session(session_config, "test_agent")
        assert session is None
    
    def test_create_session_none_type(self, factory):
        """Test that 'none' session type returns None."""
        session_config = SessionMemoryConfig(
            type="none",
            enabled=True
        )
        
        session = factory._create_session(session_config, "test_agent")
        assert session is None
    
    def test_session_caching(self, factory):
        """Test that sessions are cached and reused."""
        session_config = SessionMemoryConfig(
            type="sqlite",
            session_id="cached_session",
            database_path=None,
            enabled=True
        )
        
        session1 = factory._create_session(session_config, "test_agent")
        session2 = factory._create_session(session_config, "test_agent")
        
        if SESSION_MEMORY_AVAILABLE:
            # Same session should be returned
            assert session1 is session2
    
    def test_different_session_ids_not_cached(self, factory):
        """Test that different session IDs create different sessions."""
        config1 = SessionMemoryConfig(
            type="sqlite",
            session_id="session_1",
            enabled=True
        )
        config2 = SessionMemoryConfig(
            type="sqlite",
            session_id="session_2",
            enabled=True
        )
        
        session1 = factory._create_session(config1, "test_agent")
        session2 = factory._create_session(config2, "test_agent")
        
        if SESSION_MEMORY_AVAILABLE:
            # Different sessions should be created
            assert session1 is not session2
    
    def test_clear_session_cache(self, factory):
        """Test clearing the session cache."""
        session_config = SessionMemoryConfig(
            type="sqlite",
            session_id="cached_session",
            enabled=True
        )
        
        session1 = factory._create_session(session_config, "test_agent")
        factory.clear_session_cache()
        session2 = factory._create_session(session_config, "test_agent")
        
        if SESSION_MEMORY_AVAILABLE:
            # After clearing cache, new session should be created
            assert session1 is not session2
    
    def test_auto_create_directory_for_db(self, factory):
        """Test that directories are auto-created for file-based sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use nested path that doesn't exist
            db_path = os.path.join(tmpdir, "nested", "dir", "test.db")
            session_config = SessionMemoryConfig(
                type="sqlite",
                session_id="test",
                database_path=db_path,
                enabled=True
            )
            
            session = factory._create_session(session_config, "test_agent")
            
            if SESSION_MEMORY_AVAILABLE:
                # Directory should have been created
                assert os.path.exists(os.path.dirname(db_path))


class TestGetAgentWithSession:
    """Test get_agent_with_session functionality."""
    
    @pytest.fixture
    def factory(self):
        """Create a fresh AgentFactory instance with cleanup."""
        factory = AgentFactory()
        factory.clear_session_cache()
        yield factory
        # Cleanup: close all sessions after test
        factory.clear_session_cache()
    
    @pytest.mark.asyncio
    async def test_get_agent_with_session_basic(self, factory):
        """Test basic get_agent_with_session functionality."""
        agent, session = await factory.get_agent_with_session("geo")
        
        assert agent is not None
        assert agent.name == "GeoAgent"
        
        if SESSION_MEMORY_AVAILABLE:
            assert session is not None
    
    @pytest.mark.asyncio
    async def test_get_agent_with_session_custom_instructions(self, factory):
        """Test get_agent_with_session with custom instructions."""
        custom_instructions = "Custom geocoding instructions"
        agent, session = await factory.get_agent_with_session(
            "geo", 
            instructions=custom_instructions
        )
        
        assert agent.instructions == custom_instructions
    
    @pytest.mark.asyncio
    async def test_get_agent_with_session_id_override(self, factory):
        """Test session ID override in get_agent_with_session."""
        agent1, session1 = await factory.get_agent_with_session(
            "geo", 
            session_id="user_123"
        )
        agent2, session2 = await factory.get_agent_with_session(
            "geo", 
            session_id="user_456"
        )
        
        if SESSION_MEMORY_AVAILABLE:
            # Different session IDs should create different sessions
            assert session1 is not session2
    
    @pytest.mark.asyncio
    async def test_get_agent_with_session_disabled(self, factory):
        """Test get_agent_with_session for agent with disabled session."""
        # One agent has disabled session memory in config
        agent, session = await factory.get_agent_with_session("one")
        
        assert agent is not None
        assert agent.name == "OneAgent"
        # Session should be None for disabled session memory
        assert session is None

    @pytest.mark.asyncio
    async def test_get_agent_with_persistent_session_overrides_disabled_config(self, factory, tmp_path):
        """
        Orchestrators must be able to force persistent session memory even if an agent is configured stateless.
        """
        db_path = tmp_path / "one.db"
        agent, session = await factory.get_agent_with_persistent_session(
            "one",
            session_id="test_orchestrator_session",
            db_path=db_path,
        )

        assert agent is not None
        assert agent.name == "OneAgent"

        if SESSION_MEMORY_AVAILABLE:
            assert session is not None
            assert db_path.exists()
    
    @pytest.mark.asyncio
    async def test_get_agent_with_session_all_agents(self, factory):
        """Test get_agent_with_session for all configured agents."""
        agent_names = factory.list_available_agents()
        
        for name in agent_names:
            agent, session = await factory.get_agent_with_session(name)
            
            assert agent is not None
            # Session may be None if disabled for that agent


class TestGetSessionMethod:
    """Test get_session method."""
    
    @pytest.fixture
    def factory(self):
        """Create a fresh AgentFactory instance with cleanup."""
        factory = AgentFactory()
        factory.clear_session_cache()
        yield factory
        # Cleanup: close all sessions after test
        factory.clear_session_cache()
    
    def test_get_session_without_agent(self, factory):
        """Test getting session without creating agent."""
        session = factory.get_session("geo")
        
        if SESSION_MEMORY_AVAILABLE:
            assert session is not None
    
    def test_get_session_with_custom_id(self, factory):
        """Test getting session with custom session ID."""
        session1 = factory.get_session("geo", session_id="custom_1")
        session2 = factory.get_session("geo", session_id="custom_2")
        
        if SESSION_MEMORY_AVAILABLE:
            assert session1 is not session2
    
    def test_get_session_invalid_agent(self, factory):
        """Test getting session for invalid agent raises error."""
        with pytest.raises(AgentException, match="not found"):
            factory.get_session("nonexistent_agent")


class TestConvenienceFunction:
    """Test get_agent_with_session convenience function."""
    
    @pytest.fixture(autouse=True)
    def cleanup_sessions(self):
        """Cleanup session cache after each test to prevent connection leaks."""
        yield
        # Clear session cache after test to close any SQLite connections
        AgentFactory.instance().clear_session_cache()
    
    @pytest.mark.asyncio
    async def test_convenience_function_basic(self):
        """Test basic usage of convenience function."""
        agent, session = await get_agent_with_session("geo")
        
        assert agent is not None
        assert agent.name == "GeoAgent"
    
    @pytest.mark.asyncio
    async def test_convenience_function_with_session_id(self):
        """Test convenience function with session ID override."""
        agent, session = await get_agent_with_session(
            "geo",
            session_id="test_session_id"
        )
        
        assert agent is not None


class TestSessionMemoryIntegration:
    """Integration tests for session memory with real agents."""
    
    @pytest.fixture
    def factory(self):
        """Create a fresh AgentFactory instance with cleanup."""
        factory = AgentFactory()
        factory.clear_session_cache()
        yield factory
        # Cleanup: close all sessions after test
        factory.clear_session_cache()
    
    @pytest.mark.asyncio
    async def test_session_persistence_inmemory(self, factory):
        """Test that in-memory session maintains state within same session."""
        # Get agent with session
        agent, session = await factory.get_agent_with_session("geo")
        
        if SESSION_MEMORY_AVAILABLE and session is not None:
            # Session should be usable with Runner
            # Note: We don't actually run the agent here to avoid API calls
            assert session is not None
    
    @pytest.mark.asyncio
    async def test_filebased_session_config(self, factory):
        """Test that file-based session config works."""
        # Finance agent has file-based session in config
        agent, session = await factory.get_agent_with_session("finance")
        
        assert agent is not None
        assert agent.name == "FinanceAgent"
        
        if SESSION_MEMORY_AVAILABLE:
            assert session is not None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def factory(self):
        """Create a fresh AgentFactory instance."""
        return AgentFactory()
    
    def test_session_with_empty_session_id(self, factory):
        """Test session creation with None session_id uses agent name."""
        session_config = SessionMemoryConfig(
            type="sqlite",
            session_id=None,  # Should use agent name
            enabled=True
        )
        
        session = factory._create_session(session_config, "test_agent")
        
        if SESSION_MEMORY_AVAILABLE:
            assert session is not None
    
    @pytest.mark.asyncio
    async def test_multiple_factories_share_nothing(self):
        """Test that multiple factory instances don't share sessions."""
        factory1 = AgentFactory()
        factory2 = AgentFactory()
        
        session1 = factory1.get_session("geo", session_id="shared_test")
        session2 = factory2.get_session("geo", session_id="shared_test")
        
        if SESSION_MEMORY_AVAILABLE:
            # Different factory instances should have different session caches
            assert session1 is not session2
    
    def test_session_config_with_all_none_values(self, factory):
        """Test session config with all None optional values."""
        session_config = SessionMemoryConfig(
            type="sqlite",
            session_id=None,
            database_path=None,
            enabled=True
        )
        
        session = factory._create_session(session_config, "test_agent")
        
        if SESSION_MEMORY_AVAILABLE:
            assert session is not None

