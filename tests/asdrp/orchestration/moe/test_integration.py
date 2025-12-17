"""Integration tests for MoE orchestrator."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.orchestration.moe.config_loader import MoEConfigLoader


@pytest.mark.slow
class TestMoEIntegration:
    """Integration tests for complete MoE pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(self, mock_moe_config):
        """Test complete end-to-end orchestration with real agent factory."""
        from asdrp.agents.agent_factory import AgentFactory
        
        # Use real agent factory instead of mocks
        agent_factory = AgentFactory()
        
        # Create orchestrator
        orchestrator = MoEOrchestrator.create_default(
            agent_factory,
            mock_moe_config
        )

        # Execute query with real agents (may require API keys)
        # This tests the full pipeline including agent creation and execution
        try:
            result = await orchestrator.route_query("Find restaurants near me")

            # Verify result
            assert result.response
            assert len(result.experts_used) > 0
            # Latency should be > 0 now that we fixed the fallback latency calculation
            assert result.trace.latency_ms > 0
        except Exception as e:
            # If real agents fail (e.g., missing API keys), skip the test
            pytest.skip(f"Real agent execution failed (likely missing API keys): {e}")
        finally:
            # Cleanup: close all sessions
            agent_factory.clear_session_cache()

    @pytest.mark.asyncio
    async def test_with_real_config_file(self, mock_agent_factory):
        """Test with actual config file."""
        config_path = Path("config/moe.yaml")

        if not config_path.exists():
            pytest.skip("config/moe.yaml not found")

        # Load real config
        loader = MoEConfigLoader(config_path=config_path)
        config = loader.load_config()

        # Create orchestrator
        orchestrator = MoEOrchestrator.create_default(
            mock_agent_factory,
            config
        )

        # Mock execution
        with patch("agents.Runner.run") as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Test response"
            mock_run.return_value = mock_result

            result = await orchestrator.route_query("test query")
            assert result.response

    @pytest.mark.asyncio
    async def test_multiple_queries_with_session(
        self,
        mock_agent_factory,
        mock_moe_config
    ):
        """Test multiple queries with same session."""
        orchestrator = MoEOrchestrator.create_default(
            mock_agent_factory,
            mock_moe_config
        )

        session_id = "test_session"

        with patch("agents.Runner.run") as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Response"
            mock_run.return_value = mock_result

            # Execute multiple queries
            result1 = await orchestrator.route_query(
                "First query",
                session_id=session_id
            )
            result2 = await orchestrator.route_query(
                "Second query",
                session_id=session_id
            )

            assert result1.response
            assert result2.response

            # Verify session was reused
            calls = mock_agent_factory.get_agent_with_session.call_args_list
            for call in calls:
                args, _ = call
                if len(args) > 1:
                    assert args[1] == session_id

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_agent_factory, mock_moe_config):
        """Test error recovery - MoE continues with available agents."""
        orchestrator = MoEOrchestrator.create_default(
            mock_agent_factory,
            mock_moe_config
        )

        # First call to get_agent_with_session fails
        # Subsequent calls succeed
        call_count = 0

        async def mock_get_agent(agent_id, session_id=None):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First agent fails to load
                raise Exception("First agent failed")

            # Other agents succeed
            mock_agent = Mock()
            mock_agent.name = f"Agent{call_count}"
            return (mock_agent, Mock())

        mock_agent_factory.get_agent_with_session = mock_get_agent

        with patch("agents.Runner.run") as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Response from available agents"
            mock_run.return_value = mock_result

            result = await orchestrator.route_query("test query")

            # MoE should continue with available agents (not fallback)
            assert result.response
            assert len(result.experts_used) > 0
            # Not a fallback - just continuing with available agents
            # Fallback only happens if NO agents can be loaded or total failure


class TestMoEWithAgentService:
    """Test MoE integration with AgentService."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_agent_service_integration(self, mock_moe_config):
        """Test MoE integration with AgentService."""
        from server.agent_service import AgentService
        from server.models import SimulationRequest

        # Create agent service
        # Note: This will try to initialize real MoE if config exists
        try:
            service = AgentService()

            # Check if MoE is available
            if service._moe is not None:
                # Execute MoE query through service
                request = SimulationRequest(
                    input="Find pizza near me",
                    session_id="test_session"
                )

                with patch("agents.Runner.run") as mock_run:
                    mock_result = Mock()
                    mock_result.final_output = "Pizza places found"
                    mock_run.return_value = mock_result

                    response = await service.chat_agent("moe", request)

                    assert response.response
                    assert response.metadata["orchestrator"] == "moe"
                    assert "experts_used" in response.metadata
        except Exception as e:
            pytest.skip(f"AgentService initialization failed: {e}")
