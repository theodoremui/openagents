import pytest

from asdrp.orchestration.moe.result_mixer import WeightedMixer
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.config_loader import MoEConfigLoader


class _FakeOpenAIResponseNoChoices:
    choices = None
    usage = None


class _FakeChatCompletions:
    async def create(self, *args, **kwargs):
        return _FakeOpenAIResponseNoChoices()


class _FakeChat:
    completions = _FakeChatCompletions()


class _FakeAsyncOpenAI:
    def __init__(self, api_key=None):
        self.chat = _FakeChat()


@pytest.mark.asyncio
async def test_llm_synthesis_falls_back_when_choices_missing(monkeypatch):
    # Ensure mixer thinks an API key exists
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    # Patch AsyncOpenAI inside the mixer module import path
    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", _FakeAsyncOpenAI)

    cfg = MoEConfigLoader().load_config()
    mixer = WeightedMixer(cfg)

    results = [
        ExpertResult(expert_id="yelp_mcp", output="Expert output A", success=True, latency_ms=1),
        ExpertResult(expert_id="map", output="Expert output B", success=True, latency_ms=1),
    ]
    weights = {"yelp_mcp": 0.9, "map": 0.1}

    mixed = await mixer._llm_synthesis(results, weights, "q")
    assert "Expert output A" in mixed.content


