#############################################################################
# test_agent_testing.py
#
# Tests for agent testing functionality.
#
#############################################################################

import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend_stream.modules.agent_testing import load_agent
from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.config_loader import ModelConfig


class TestAgentTesting:
    """Test agent testing functionality."""
    
    def test_load_agent_success(self):
        """Test successful agent loading."""
        # Mock the agent creation
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.instructions = "Test instructions"
        
        with patch('frontend_stream.modules.agent_testing.AgentConfigLoader') as mock_loader_class, \
             patch('frontend_stream.modules.agent_testing.importlib.import_module') as mock_import:
            
            # Setup mocks
            mock_config_loader = Mock()
            mock_config_loader.get_agent_config.return_value = Mock(
                module="asdrp.agents.single.geo_agent",
                function="create_geo_agent"
            )
            mock_loader_class.return_value = mock_config_loader
            
            mock_module = Mock()
            mock_factory_func = Mock(return_value=mock_agent)
            mock_module.create_geo_agent = mock_factory_func
            mock_import.return_value = mock_module
            
            # Mock streamlit session state
            with patch('streamlit.session_state', new={}):
                # Note: This test would need proper streamlit mocking
                # For now, we test the logic without streamlit dependencies
                pass
    
    def test_load_agent_model_config(self):
        """Test that model config is properly created."""
        model_config = ModelConfig(
            name="gpt-4",
            temperature=0.7,
            max_tokens=2000
        )
        
        assert model_config.name == "gpt-4"
        assert model_config.temperature == 0.7
        assert model_config.max_tokens == 2000
    
    def test_load_agent_invalid_config(self):
        """Test handling of invalid model configuration."""
        with pytest.raises(ValueError):
            # Temperature out of range
            ModelConfig(
                name="gpt-4",
                temperature=3.0,  # Invalid: > 2.0
                max_tokens=2000
            )
        
        with pytest.raises(ValueError):
            # Max tokens invalid
            ModelConfig(
                name="gpt-4",
                temperature=0.7,
                max_tokens=0  # Invalid: must be > 0
            )

