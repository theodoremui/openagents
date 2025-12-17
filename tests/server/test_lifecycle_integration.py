"""
Comprehensive lifecycle and integration tests for server module.

Tests the lifespan management, service initialization, and integration
between components without extraneous mocks.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager

# Set test environment
os.environ["TESTING"] = "true"
os.environ["AUTH_ENABLED"] = "false"

from server.main import app, lifespan, get_service, _agent_service
from server.agent_service import AgentService
from asdrp.agents.protocol import AgentException


class TestLifespanManagement:
    """Test FastAPI lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """Test lifespan startup initializes service successfully."""
        global _agent_service
        original_service = _agent_service
        
        try:
            _agent_service = None
            
            async with lifespan(app):
                # Service should be initialized
                assert _agent_service is not None
                assert isinstance(_agent_service, AgentService)
                
                # Should be able to list agents
                agents = _agent_service.list_agents()
                assert isinstance(agents, list)
        finally:
            _agent_service = original_service

    @pytest.mark.asyncio
    async def test_lifespan_startup_with_smartrouter(self):
        """Test lifespan startup with SmartRouter orchestrator."""
        global _agent_service
        original_service = _agent_service
        original_orchestrator = os.environ.get("ORCHESTRATOR")
        
        try:
            _agent_service = None
            os.environ["ORCHESTRATOR"] = "smartrouter"
            
            async with lifespan(app):
                # Service should be initialized even with SmartRouter
                assert _agent_service is not None
                assert isinstance(_agent_service, AgentService)
        finally:
            _agent_service = original_service
            if original_orchestrator:
                os.environ["ORCHESTRATOR"] = original_orchestrator
            else:
                os.environ.pop("ORCHESTRATOR", None)

    @pytest.mark.asyncio
    async def test_lifespan_startup_handles_errors(self):
        """Test lifespan startup handles initialization errors gracefully."""
        global _agent_service
        original_service = _agent_service
        
        try:
            _agent_service = None
            
            with patch('server.main.AgentService', side_effect=Exception("Init error")):
                # The lifespan should handle the error and still create a service
                async with lifespan(app):
                    # Service should be created even if initialization fails
                    assert _agent_service is not None
        finally:
            _agent_service = original_service

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_cleanup(self):
        """Test lifespan shutdown cleans up resources."""
        global _agent_service
        original_service = _agent_service
        
        try:
            _agent_service = None
            
            with patch('asdrp.agents.mcp.get_mcp_manager') as mock_mcp:
                mock_manager = MagicMock()
                mock_manager.shutdown_all = AsyncMock()
                mock_mcp.return_value = mock_manager
                
                async with lifespan(app):
                    pass
                
                # Shutdown should be called
                mock_manager.shutdown_all.assert_called_once()
        finally:
            _agent_service = original_service


class TestGetService:
    """Test get_service dependency injection."""

    def test_get_service_available(self):
        """Test get_service returns service when available."""
        global _agent_service
        original_service = _agent_service
        
        try:
            _agent_service = AgentService()
            service = get_service()
            assert service is _agent_service
            assert isinstance(service, AgentService)
        finally:
            _agent_service = original_service

    def test_get_service_unavailable(self):
        """Test get_service raises HTTPException when service unavailable."""
        global _agent_service
        original_service = _agent_service
        
        try:
            _agent_service = None
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                get_service()
            
            assert exc_info.value.status_code == 503
            assert "not initialized" in str(exc_info.value.detail)
        finally:
            _agent_service = original_service


class TestExceptionHandler:
    """Test custom exception handlers."""

    @pytest.mark.asyncio
    async def test_agent_exception_handler(self):
        """Test AgentException is handled correctly."""
        from fastapi.testclient import TestClient
        from fastapi import Request
        from server.main import agent_exception_handler
        
        exc = AgentException("Test error", agent_name="test_agent")
        request = Request({"type": "http", "method": "GET", "path": "/test"})
        
        response = await agent_exception_handler(request, exc)
        
        assert response.status_code == 400
        content = response.body.decode()
        assert "Test error" in content
        assert "agent_error" in content


class TestServiceIntegration:
    """Integration tests for AgentService with real dependencies."""

    @pytest.fixture
    def service(self):
        """Create real AgentService instance."""
        return AgentService()

    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service._factory is not None
        assert service._config_loader is not None

    def test_list_agents_integration(self, service):
        """Test listing agents with real config."""
        agents = service.list_agents()
        assert isinstance(agents, list)
        # Should have at least some agents from config
        assert len(agents) > 0

    @pytest.mark.asyncio
    async def test_get_agent_detail_integration(self, service):
        """Test getting agent detail with real config."""
        # Get first available agent
        agents = service.list_agents()
        if len(agents) > 0:
            agent_id = agents[0].id
            detail = await service.get_agent_detail(agent_id)
            assert detail.id == agent_id
            assert detail.display_name is not None
            assert detail.module is not None
            assert detail.function is not None

    def test_get_agent_graph_integration(self, service):
        """Test getting agent graph with real config."""
        graph = service.get_agent_graph()
        assert graph.nodes is not None
        assert graph.edges is not None
        assert len(graph.nodes) > 0

    def test_validate_config_valid(self, service):
        """Test validating valid YAML config."""
        valid_yaml = """
agents:
  test_agent:
    display_name: "Test Agent"
    module: "test.module"
    function: "create_agent"
"""
        is_valid, error = service.validate_config(valid_yaml)
        assert is_valid is True
        assert error is None

    def test_validate_config_invalid(self, service):
        """Test validating invalid YAML config."""
        invalid_yaml = "not: valid: yaml: ["
        is_valid, error = service.validate_config(invalid_yaml)
        assert is_valid is False
        assert error is not None

    def test_validate_config_missing_agents(self, service):
        """Test validating config missing agents key."""
        invalid_yaml = """
other_key:
  value: test
"""
        is_valid, error = service.validate_config(invalid_yaml)
        assert is_valid is False
        assert "agents" in error.lower()

    def test_reload_config(self, service):
        """Test reloading configuration."""
        # Should not raise exception
        service.reload_config()
        
        # Verify config is still accessible
        agents = service.list_agents()
        assert isinstance(agents, list)

