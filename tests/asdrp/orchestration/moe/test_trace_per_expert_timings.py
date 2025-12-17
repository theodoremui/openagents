import pytest
from unittest.mock import Mock, AsyncMock

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.result_mixer import MixedResult


@pytest.mark.asyncio
async def test_trace_records_per_expert_completion_times(mock_agent_factory, mock_moe_config):
    """
    Regression test: expert_details end_time must reflect each expert's true completion time,
    not a shared timestamp taken after all experts finish.
    """
    mock_selector = Mock()
    mock_selector.select = AsyncMock(return_value=["one", "geo"])

    mock_executor = Mock()
    mock_executor.execute_parallel = AsyncMock(
        return_value=[
            ExpertResult(
                expert_id="one",
                output="A",
                success=True,
                latency_ms=1200.0,
                started_at=100.0,
                ended_at=101.2,
            ),
            ExpertResult(
                expert_id="geo",
                output="B",
                success=True,
                latency_ms=4200.0,
                started_at=100.1,
                ended_at=104.3,
            ),
        ]
    )

    mock_mixer = Mock()
    mock_mixer.mix = AsyncMock(
        return_value=MixedResult(content="ok", weights={"one": 0.5, "geo": 0.5}, quality_score=1.0)
    )

    orchestrator = MoEOrchestrator(
        agent_factory=mock_agent_factory,
        expert_selector=mock_selector,
        expert_executor=mock_executor,
        result_mixer=mock_mixer,
        config=mock_moe_config,
        cache=None,
    )

    result = await orchestrator.route_query("q", session_id="s")
    details = {d.expert_id: d for d in (result.trace.expert_details or [])}

    assert details["one"].start_time == 100.0
    assert details["one"].end_time == 101.2
    assert details["one"].latency_ms == 1200.0

    assert details["geo"].start_time == 100.1
    assert details["geo"].end_time == 104.3
    assert details["geo"].latency_ms == 4200.0

    # Critical: completion times differ (fast expert finishes earlier)
    assert details["one"].end_time < details["geo"].end_time




