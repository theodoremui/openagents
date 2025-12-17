import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock, patch


class _DummyAsyncCM:
    def __init__(self):
        self.entered = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_parallel_executor_enters_mcp_server_context_before_runner_run():
    """
    Regression test: MoE ParallelExecutor must enter MCPServerStdio async contexts
    before calling Runner.run(), otherwise MCP tools fail immediately.
    """
    async def _run():
        from asdrp.orchestration.moe.expert_executor import ParallelExecutor

        cfg = SimpleNamespace(moe={"max_concurrent": 1, "timeout_per_expert": 1.0})
        executor = ParallelExecutor(cfg)

        cm = _DummyAsyncCM()
        agent = Mock()
        agent.mcp_servers = [cm]

        async def _fake_run(*, starting_agent, input, context=None, max_turns=None, session=None):
            assert cm.entered is True
            assert context == {"k": "v"}
            out = Mock()
            out.final_output = "ok"
            out.usage = None
            return out

        with patch("agents.Runner.run", new=AsyncMock(side_effect=_fake_run)):
            res = await executor._execute_single(  # noqa: SLF001 (internal method test)
                expert_id="yelp_mcp",
                agent=agent,
                session=None,
                query="find tacos",
                context={"k": "v"},
            )

        assert res.success is True
        assert res.output == "ok"

    asyncio.run(_run())


