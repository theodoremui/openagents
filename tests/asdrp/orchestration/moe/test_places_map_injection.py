from asdrp.orchestration.moe.result_mixer import WeightedMixer
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.config_loader import MoEConfigLoader


def test_places_map_auto_injection_from_yelpmcp_coordinates():
    cfg = MoEConfigLoader().load_config()
    mixer = WeightedMixer(cfg)
    query = "Show me a detailed map of where the best greek restaurants are in San Francisco."
    synthesized = "Here are the top spots:\n\n1. Kokkari\n2. Souvla"

    yelp_like = """## Business 1: Kokkari Estiatorio
- **Coordinates**: 37.796996, -122.398661

## Business 2: Souvla
- **Coordinates**: 37.776318, -122.424394
"""

    expert_results = [
        ExpertResult(expert_id="yelp_mcp", output=yelp_like, success=True, latency_ms=10),
    ]

    out = mixer._auto_inject_missing_places_map(synthesized, query, expert_results)
    assert "```json" in out
    assert "\"type\": \"interactive_map\"" in out
    assert "\"map_type\": \"places\"" in out


