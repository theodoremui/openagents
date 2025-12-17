#############################################################################
# test_configuration.py
#
# Tests for configuration management functionality.
#
#############################################################################

import pytest
import yaml
import tempfile
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend_stream.modules.configuration import (
    save_configuration,
    validate_yaml,
    update_agent_config
)


class TestConfigurationManagement:
    """Test configuration management functions."""
    
    @patch('frontend_stream.modules.configuration.st')
    def test_validate_yaml_valid(self, mock_st):
        """Test YAML validation with valid YAML."""
        valid_yaml = """
agents:
  test_agent:
    display_name: "Test Agent"
    module: "test.module"
    function: "create_test_agent"
    default_instructions: "Test instructions"
    model:
      name: "gpt-4"
      temperature: 0.7
      max_tokens: 2000
    enabled: true
"""
        # Should return True for valid YAML
        result = validate_yaml(valid_yaml)
        assert result is True
        mock_st.success.assert_called_once()
    
    @patch('frontend_stream.modules.configuration.st')
    def test_validate_yaml_invalid(self, mock_st):
        """Test YAML validation with invalid YAML."""
        invalid_yaml = """
agents:
  test_agent:
    display_name: "Test Agent"
    invalid: [unclosed bracket
"""
        # Should return False for invalid YAML
        result = validate_yaml(invalid_yaml)
        assert result is False
        mock_st.error.assert_called_once()
    
    @patch('frontend_stream.modules.configuration.st')
    def test_save_configuration(self, mock_st):
        """Test saving configuration to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
            temp_path = Path(f.name)
        
        try:
            test_config = """
agents:
  test_agent:
    display_name: "Test Agent"
    module: "test.module"
    function: "create_test_agent"
    default_instructions: "Test instructions"
    model:
      name: "gpt-4"
      temperature: 0.7
      max_tokens: 2000
    enabled: true
"""
            result = save_configuration(temp_path, test_config)
            
            # Verify function returned True
            assert result is True
            
            # Verify file was written
            assert temp_path.exists()
            
            # Verify content
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "test_agent" in content
                assert "Test Agent" in content
            
            mock_st.success.assert_called_once()
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    @patch('frontend_stream.modules.configuration.st')
    def test_update_agent_config(self, mock_st):
        """Test updating agent configuration."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
            temp_path = Path(f.name)
            yaml.dump({
                'agents': {
                    'test_agent': {
                        'display_name': 'Old Name',
                        'module': 'test.module',
                        'function': 'create_test_agent',
                        'default_instructions': 'Old instructions',
                        'model': {
                            'name': 'gpt-4',
                            'temperature': 0.5,
                            'max_tokens': 1000
                        },
                        'enabled': True
                    }
                }
            }, f)
        
        try:
            # Update agent config
            result = update_agent_config(
                temp_path,
                'test_agent',
                'New Name',
                False,
                'gpt-4-turbo',
                0.8,
                3000,
                'New instructions'
            )
            
            # Verify function returned True
            assert result is True
            
            # Verify updates
            with open(temp_path, 'r') as f:
                config = yaml.safe_load(f)
            
            agent_config = config['agents']['test_agent']
            assert agent_config['display_name'] == 'New Name'
            assert agent_config['enabled'] is False
            assert agent_config['model']['name'] == 'gpt-4-turbo'
            assert agent_config['model']['temperature'] == 0.8
            assert agent_config['model']['max_tokens'] == 3000
            assert agent_config['default_instructions'] == 'New instructions'
            
            mock_st.success.assert_called_once()
        
        finally:
            if temp_path.exists():
                temp_path.unlink()

