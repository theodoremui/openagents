"""
Comprehensive tests for configuration management.

Tests config loading, validation, updating, and edge cases.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
from fastapi.testclient import TestClient

# Set test environment
import os
os.environ["TESTING"] = "true"
os.environ["AUTH_ENABLED"] = "false"

from server.main import app
from server.agent_service import AgentService
from server.models import ConfigUpdate, ConfigResponse


class TestGetConfigEndpoint:
    """Test GET /config/agents endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_get_config_success(self, client, mock_service, auth_header):
        """Test getting config successfully."""
        # Create temporary config file
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "open_agents.yaml"
            config_content = """
agents:
  test_agent:
    display_name: "Test Agent"
    module: "test.module"
    function: "create_agent"
"""
            config_path.write_text(config_content)
            
            mock_service.list_agents.return_value = []
            
            with patch('server.main.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.stat.return_value = MagicMock(st_mtime=1234567890.0)
                mock_path_class.return_value = mock_path
                
                with patch('builtins.open', mock_open(read_data=config_content)):
                    response = client.get("/config/agents", headers=auth_header)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "content" in data
                    assert "agents_count" in data
                    assert "last_modified" in data

    def test_get_config_not_found(self, client, mock_service, auth_header):
        """Test getting config when file doesn't exist."""
        with patch('server.main.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path
            
            response = client.get("/config/agents", headers=auth_header)
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestUpdateConfigEndpoint:
    """Test PUT /config/agents endpoint."""

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        return TestClient(app)

    def test_update_config_validate_only(self, client, mock_service, auth_header):
        """Test config validation without saving."""
        valid_config = """
agents:
  test_agent:
    display_name: "Test Agent"
    module: "test.module"
    function: "create_agent"
"""
        update = ConfigUpdate(content=valid_config, validate_only=True)
        
        mock_service.validate_config.return_value = (True, None)
        
        response = client.put(
            "/config/agents",
            json=update.model_dump(),
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        mock_service.validate_config.assert_called_once_with(valid_config)

    def test_update_config_invalid_yaml(self, client, mock_service, auth_header):
        """Test updating config with invalid YAML."""
        invalid_config = "not: valid: yaml: ["
        update = ConfigUpdate(content=invalid_config, validate_only=False)
        
        mock_service.validate_config.return_value = (False, "YAML parse error")
        
        response = client.put(
            "/config/agents",
            json=update.model_dump(),
            headers=auth_header
        )
        
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_update_config_success(self, client, mock_service, auth_header):
        """Test successfully updating config."""
        valid_config = """
agents:
  test_agent:
    display_name: "Test Agent"
    module: "test.module"
    function: "create_agent"
"""
        update = ConfigUpdate(content=valid_config, validate_only=False)
        
        mock_service.validate_config.return_value = (True, None)
        mock_service.list_agents.return_value = [Mock(id="test_agent")]
        mock_service.reload_config = Mock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "open_agents.yaml"
            config_path.write_text("old content")
            
            with patch('server.main.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.with_suffix.return_value = MagicMock()
                mock_path_class.return_value = mock_path
                
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('shutil.copy'):
                        response = client.put(
                            "/config/agents",
                            json=update.model_dump(),
                            headers=auth_header
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert "updated" in data["message"].lower()
                        mock_service.reload_config.assert_called_once()

    def test_update_config_save_error(self, client, mock_service, auth_header):
        """Test handling save errors."""
        valid_config = """
agents:
  test_agent:
    display_name: "Test Agent"
    module: "test.module"
    function: "create_agent"
"""
        update = ConfigUpdate(content=valid_config, validate_only=False)
        
        mock_service.validate_config.return_value = (True, None)
        
        with patch('server.main.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path
            
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                response = client.put(
                    "/config/agents",
                    json=update.model_dump(),
                    headers=auth_header
                )
                
                assert response.status_code == 500
                assert "failed" in response.json()["detail"].lower()


class TestConfigValidation:
    """Test configuration validation logic."""

    @pytest.fixture
    def service(self):
        """Create AgentService instance."""
        with patch("server.agent_service.AgentConfigLoader"):
            return AgentService()

    def test_validate_config_valid_structure(self, service):
        """Test validating well-formed config."""
        valid_yaml = """
agents:
  agent1:
    display_name: "Agent 1"
    module: "module1"
    function: "create_agent1"
  agent2:
    display_name: "Agent 2"
    module: "module2"
    function: "create_agent2"
"""
        is_valid, error = service.validate_config(valid_yaml)
        assert is_valid is True
        assert error is None

    def test_validate_config_missing_required_fields(self, service):
        """Test validating config with missing required fields."""
        invalid_yaml = """
agents:
  agent1:
    display_name: "Agent 1"
    # Missing module and function
"""
        is_valid, error = service.validate_config(invalid_yaml)
        assert is_valid is False
        assert "required field" in error.lower()

    def test_validate_config_agents_not_dict(self, service):
        """Test validating config where agents is not a dict."""
        invalid_yaml = """
agents:
  - agent1
  - agent2
"""
        is_valid, error = service.validate_config(invalid_yaml)
        assert is_valid is False
        assert "dictionary" in error.lower()

    def test_validate_config_root_not_dict(self, service):
        """Test validating config where root is not a dict."""
        invalid_yaml = "- item1\n- item2"
        is_valid, error = service.validate_config(invalid_yaml)
        assert is_valid is False
        assert "dictionary" in error.lower()

    def test_validate_config_yaml_error(self, service):
        """Test validating malformed YAML."""
        invalid_yaml = "not: valid: yaml: ["
        is_valid, error = service.validate_config(invalid_yaml)
        assert is_valid is False
        assert error is not None
        assert "yaml" in error.lower() or "parse" in error.lower()

    def test_validate_config_empty_string(self, service):
        """Test validating empty config."""
        is_valid, error = service.validate_config("")
        assert is_valid is False
        assert error is not None

    def test_validate_config_unicode_content(self, service):
        """Test validating config with unicode content."""
        unicode_yaml = """
agents:
  test_agent:
    display_name: "测试代理"
    module: "test.module"
    function: "create_agent"
"""
        is_valid, error = service.validate_config(unicode_yaml)
        assert is_valid is True
        assert error is None

