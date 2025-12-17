"""Pytest configuration and fixtures for server tests."""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Set up test environment variables."""
    os.environ["AUTH_ENABLED"] = "false"
    os.environ["TESTING"] = "true"
    yield
    # Cleanup
    os.environ.pop("AUTH_ENABLED", None)
    os.environ.pop("TESTING", None)


@pytest.fixture
def test_api_key():
    """Provide a test API key."""
    return "test_api_key_12345"


@pytest.fixture
def mock_service():
    """Mock AgentService by patching the global _agent_service."""
    service = Mock()
    # Patch the global _agent_service variable directly
    with patch('server.main._agent_service', service):
        # Also patch get_service to return our mock
        with patch('server.main.get_service', return_value=service):
            yield service


@pytest.fixture
def auth_header():
    """Mock authentication - auth is disabled via AUTH_ENABLED=false."""
    return {"X-API-Key": "test_key"}


@pytest.fixture(scope="session")
def test_config_path(tmp_path_factory):
    """Create a temporary config file for testing."""
    config_dir = tmp_path_factory.mktemp("config")
    config_file = config_dir / "test_agents.yaml"

    config_content = """
agents:
  test_agent:
    display_name: "TestAgent"
    module: "test.module"
    function: "create_test_agent"
    default_instructions: "Test instructions"
    model:
      name: "gpt-4"
      temperature: 0.7
      max_tokens: 2000
    session_memory:
      type: "sqlite"
      enabled: true
    enabled: true
"""

    config_file.write_text(config_content)
    return config_file
