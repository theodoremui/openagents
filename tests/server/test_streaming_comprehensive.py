"""
Comprehensive tests for streaming functionality.

Tests all streaming edge cases and error scenarios.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from server.agent_service import AgentService
from server.models import SimulationRequest, StreamChunk
from asdrp.agents.protocol import AgentException


class TestChatAgentStreaming:
    """Comprehensive tests for chat_agent_streaming method."""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory."""
        factory = Mock()
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.tools = []
        factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, None))
        return factory

    @pytest.fixture
    def service(self, mock_factory):
        """Create AgentService with mocked dependencies."""
        with patch("server.agent_service.AgentConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            
            service = AgentService(factory=mock_factory)
            service._config_loader = mock_loader
            return service

    @pytest.mark.asyncio
    async def test_streaming_with_mcp_servers(self, service, mock_factory):
        """Test streaming with MCP-enabled agents."""
        mock_agent = Mock()
        mock_agent.name = "MCPAgent"
        mock_agent.mcp_servers = [Mock(), Mock()]
        mock_factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, None))
        
        async def mock_stream():
            yield Mock(content="Token1")
            yield Mock(content="Token2")
        
        request = SimulationRequest(input="Test")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run_streamed = mock_stream
            
            chunks = []
            async for chunk in service.chat_agent_streaming("mcp_agent", request):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            assert chunks[0].type == "metadata"
            assert any(chunk.type == "token" for chunk in chunks)
            assert any(chunk.type == "done" for chunk in chunks)

    @pytest.mark.asyncio
    async def test_streaming_with_session(self, service, mock_factory):
        """Test streaming with session memory."""
        mock_agent = Mock()
        mock_agent.name = "SessionAgent"
        mock_session = Mock()
        mock_factory.get_agent_with_session = AsyncMock(return_value=(mock_agent, mock_session))
        
        async def mock_stream():
            yield Mock(content="Token")
        
        request = SimulationRequest(input="Test", session_id="test_session")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run_streamed = mock_stream
            
            chunks = []
            async for chunk in service.chat_agent_streaming("session_agent", request):
                chunks.append(chunk)
            
            # Verify session is passed to metadata
            metadata_chunk = next((c for c in chunks if c.type == "metadata"), None)
            assert metadata_chunk is not None
            assert metadata_chunk.metadata["session_enabled"] is True
            assert metadata_chunk.metadata["session_id"] == "test_session"

    @pytest.mark.asyncio
    async def test_streaming_import_error(self, service, mock_factory):
        """Test streaming handles Runner import error."""
        request = SimulationRequest(input="Test")
        
        with patch('server.agent_service.Runner', side_effect=ImportError("No module")):
            chunks = []
            async for chunk in service.chat_agent_streaming("test", request):
                chunks.append(chunk)
            
            error_chunks = [c for c in chunks if c.type == "error"]
            assert len(error_chunks) > 0
            assert "import" in error_chunks[0].content.lower()

    @pytest.mark.asyncio
    async def test_streaming_agent_not_found(self, service, mock_factory):
        """Test streaming when agent doesn't exist."""
        request = SimulationRequest(input="Test")
        
        mock_factory.get_agent_with_session = AsyncMock(
            side_effect=AgentException("Agent not found", agent_name="unknown")
        )
        
        chunks = []
        async for chunk in service.chat_agent_streaming("unknown", request):
            chunks.append(chunk)
        
        error_chunks = [c for c in chunks if c.type == "error"]
        assert len(error_chunks) > 0

    @pytest.mark.asyncio
    async def test_streaming_execution_error(self, service, mock_factory):
        """Test streaming handles execution errors."""
        request = SimulationRequest(input="Test")
        
        async def failing_stream():
            raise Exception("Execution failed")
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run_streamed = failing_stream
            
            chunks = []
            async for chunk in service.chat_agent_streaming("test", request):
                chunks.append(chunk)
            
            error_chunks = [c for c in chunks if c.type == "error"]
            assert len(error_chunks) > 0

    @pytest.mark.asyncio
    async def test_streaming_empty_response(self, service, mock_factory):
        """Test streaming with empty response."""
        request = SimulationRequest(input="Test")
        
        async def empty_stream():
            # No chunks
            if False:
                yield
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run_streamed = empty_stream
            
            chunks = []
            async for chunk in service.chat_agent_streaming("test", request):
                chunks.append(chunk)
            
            # Should still have metadata and done chunks
            assert len(chunks) >= 2
            assert chunks[0].type == "metadata"
            assert chunks[-1].type == "done"

    @pytest.mark.asyncio
    async def test_streaming_smartrouter_error(self, service):
        """Test streaming SmartRouter with error."""
        request = SimulationRequest(input="Test")
        
        with patch.object(service, '_execute_smartrouter', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = AgentException("SmartRouter error", agent_name="smartrouter")
            
            chunks = []
            async for chunk in service.chat_agent_streaming("smartrouter", request):
                chunks.append(chunk)
            
            error_chunks = [c for c in chunks if c.type == "error"]
            assert len(error_chunks) > 0

    @pytest.mark.asyncio
    async def test_streaming_chunk_without_content(self, service, mock_factory):
        """Test streaming handles chunks without content attribute."""
        request = SimulationRequest(input="Test")
        
        async def stream_without_content():
            yield Mock()  # No content attribute
            yield "String chunk"
        
        with patch('server.agent_service.Runner') as mock_runner:
            mock_runner.run_streamed = stream_without_content
            
            chunks = []
            async for chunk in service.chat_agent_streaming("test", request):
                chunks.append(chunk)
            
            # Should handle gracefully
            assert len(chunks) > 0
            assert chunks[0].type == "metadata"














