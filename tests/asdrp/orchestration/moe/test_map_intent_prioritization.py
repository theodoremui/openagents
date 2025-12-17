from asdrp.orchestration.moe.orchestrator import MoEOrchestrator


def test_map_intent_keeps_map_within_k_limit_prefers_replacing_geo():
    query = "Show detailed map with pins on where these restaurants are in san francisco."
    selected = ["yelp", "yelp_mcp", "geo", "map"]

    # typical k=3 truncation would drop "map" -> ensure it stays
    out = MoEOrchestrator._prioritize_agents_for_map_intent(query, selected, max_k=3)
    assert "map" in out
    assert len(out) == 3
    # prefer keeping at least one business agent
    assert any(a in out for a in ("yelp", "yelp_mcp"))


def test_map_intent_injects_yelp_mcp_for_restaurant_map_queries():
    query = "Show me a detailed map of where the best greek restaurants are in San Francisco."
    selected = ["map", "geo", "yelp"]  # common truncation case that drops yelp_mcp
    out = MoEOrchestrator._prioritize_agents_for_map_intent(query, selected, max_k=3)
    assert "yelp_mcp" in out
    assert "map" in out
    assert len(out) == 3


def test_map_intent_injects_map_even_if_selector_did_not_include_it():
    query = "Show me these on a map"
    selected = ["yelp", "yelp_mcp", "geo"]
    out = MoEOrchestrator._prioritize_agents_for_map_intent(query, selected, max_k=3)
    assert "map" in out
    assert len(out) == 3


def test_non_map_queries_are_unchanged_except_truncation():
    query = "Find the best greek restaurants in san francisco"
    selected = ["yelp", "yelp_mcp", "geo", "map"]
    out = MoEOrchestrator._prioritize_agents_for_map_intent(query, selected, max_k=3)
    assert out == ["yelp", "yelp_mcp", "geo"]


