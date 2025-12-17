import pytest
from unittest.mock import Mock, AsyncMock, patch

from server.agent_service import AgentService
from server.models import SimulationRequest


@pytest.mark.asyncio
async def test_guardrail_repairs_moe_response_when_triggered(mock_factory=None):
    """
    If the hallucination guardrail triggers for MoE, the service should return a safe repair response.
    """
    factory = Mock()
    service = AgentService(factory=factory)

    # Stub MoE orchestrator on the service directly
    mock_trace = Mock()
    mock_trace.latency_ms = 10.0
    mock_trace.cache_hit = False
    mock_trace.fallback = False
    mock_trace.request_id = "moe-123"
    mock_trace.query = "q"
    mock_trace.final_response = "r"
    mock_trace.selected_experts = ["one"]

    mock_moe_result = Mock()
    mock_moe_result.response = "Totally unrelated astronomy answer"
    mock_moe_result.experts_used = ["one"]
    mock_moe_result.trace = mock_trace

    service._moe = Mock()
    service._moe.route_query = AsyncMock(return_value=mock_moe_result)

    request = SimulationRequest(input="Tell me about restaurant pins in SF", session_id="s1")

    with patch("server.agent_service.check_ungrounded_hallucination") as mock_check, patch(
        "server.agent_service.should_repair"
    ) as mock_should:
        mock_check.return_value = Mock(risk="high", reason="off topic", safe_repair="Can you clarify which restaurants?")
        mock_should.return_value = True

        resp = await service.chat_agent("moe", request)
        assert resp.response == "Can you clarify which restaurants?"
        assert resp.metadata["guardrails"]["hallucination"]["triggered"] is True


@pytest.mark.asyncio
async def test_guardrail_repairs_smartrouter_response_when_triggered():
    factory = Mock()
    service = AgentService(factory=factory)

    mock_router_result = Mock()
    mock_router_result.answer = "Unrelated answer"
    mock_router_result.traces = []
    mock_router_result.total_time = 0.1
    mock_router_result.final_decision = "direct"
    mock_router_result.agents_used = ["geo"]
    mock_router_result.success = True

    with patch("asdrp.orchestration.smartrouter.smartrouter.SmartRouter") as mock_router_class, patch(
        "server.agent_service.check_ungrounded_hallucination"
    ) as mock_check, patch("server.agent_service.should_repair") as mock_should:
        mock_router = Mock()
        mock_router.route_query = AsyncMock(return_value=mock_router_result)
        mock_router_class.create.return_value = mock_router

        mock_check.return_value = Mock(risk="high", reason="off topic", safe_repair="I’m not sure what you mean—what location?")
        mock_should.return_value = True

        resp = await service.chat_agent("smartrouter", SimulationRequest(input="where is it?", session_id="s2"))
        assert resp.response == "I’m not sure what you mean—what location?"
        assert resp.metadata["guardrails"]["hallucination"]["triggered"] is True


