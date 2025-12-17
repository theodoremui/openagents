import asyncio
import pytest

from asdrp.orchestration.moe.result_mixer import WeightedMixer, MixedResult
from asdrp.orchestration.moe.expert_executor import ExpertResult


class _DummyModelCfg:
    def __init__(self):
        self.name = "gpt-4.1-mini"
        self.temperature = 0.0
        self.max_tokens = 256


class _DummyExpertCfg:
    def __init__(self, agents, weight=1.0):
        self.agents = agents
        self.capabilities = []
        self.weight = weight


class _DummyMoEConfig:
    def __init__(self):
        self.moe = {"mixing_strategy": "synthesis"}
        self.models = {"mixing": _DummyModelCfg()}
        self.experts = {
            "location_expert": _DummyExpertCfg(["map"], weight=1.0),
            "geo_expert": _DummyExpertCfg(["geo"], weight=1.0),
        }


def test_mixer_appends_missing_interactive_map_block_when_llm_omits(monkeypatch):
    """
    Regression: MoE synthesis can omit visualization blocks (e.g., interactive map).
    We must preserve them deterministically from expert outputs.
    """
    mixer = WeightedMixer(_DummyMoEConfig())

    expert_map_output = (
        "Here are the directions.\n\n"
        "```json\n"
        '{\n  "type": "interactive_map",\n  "config": {\n    "map_type": "route",\n    "origin": "San Carlos, CA",\n    "destination": "Aptos, CA",\n    "travel_mode": "DRIVING"\n  }\n}\n'
        "```\n"
    )

    results = [
        ExpertResult(expert_id="map", output=expert_map_output, success=True, latency_ms=1.0),
        ExpertResult(expert_id="geo", output="Text-only geo result", success=True, latency_ms=1.0),
    ]

    async def _fake_llm_synthesis(_results, weights, query):
        # Simulate an LLM that forgets to include the json block.
        return MixedResult(content="Synthesized directions without map.", weights=weights, quality_score=0.5)

    monkeypatch.setattr(mixer, "_llm_synthesis", _fake_llm_synthesis)

    mixed = asyncio.run(
        mixer.mix(
            results,
            expert_ids=["map", "geo"],
            query="Show me a routing map from San Carlos to Aptos",
        )
    )
    assert "interactive_map" in mixed.content
    assert '"origin": "San Carlos, CA"' in mixed.content
    assert '"destination": "Aptos, CA"' in mixed.content


def test_mixer_does_not_duplicate_interactive_map_block(monkeypatch):
    mixer = WeightedMixer(_DummyMoEConfig())

    expert_map_block = (
        "```json\n"
        '{ "type": "interactive_map", "config": { "map_type": "route", "origin": "A", "destination": "B" } }\n'
        "```"
    )

    results = [
        ExpertResult(expert_id="map", output=f"Map:\n\n{expert_map_block}\n", success=True, latency_ms=1.0),
        ExpertResult(expert_id="geo", output="Other text", success=True, latency_ms=1.0),
    ]

    async def _fake_llm_synthesis(_results, weights, query):
        # LLM already includes the block, mixer should not append it again.
        return MixedResult(content=f"Here you go:\n\n{expert_map_block}\n", weights=weights, quality_score=0.9)

    monkeypatch.setattr(mixer, "_llm_synthesis", _fake_llm_synthesis)

    mixed = asyncio.run(mixer.mix(results, expert_ids=["map", "geo"], query="route please"))
    assert mixed.content.count("interactive_map") == 1


