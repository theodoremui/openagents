"""
Unit tests for domain prioritization logic.

Tests the core prioritization algorithm without needing full SmartRouter setup.
"""

import pytest
from asdrp.orchestration.smartrouter.interfaces import QueryIntent, QueryComplexity


def select_primary_capability_with_priority(domains: list[str]) -> str:
    """
    Select primary capability using domain prioritization.

    This is the core logic being tested - extracted from SmartRouter
    for isolated unit testing.
    """
    # Domain prioritization map - higher values = higher priority
    DOMAIN_PRIORITY = {
        "local_business": 10,   # Yelp for restaurants/shops
        "finance": 9,            # Finance agent for stocks
        "geocoding": 8,          # Geo agent for coordinates
        "mapping": 7,            # Map agent for directions
        "research": 6,           # Perplexity for research
        "wikipedia": 5,          # Wiki for encyclopedia
        "conversation": 4,       # Chitchat for social
        "social": 4,
        "search": 1,             # Generic web search - fallback
    }

    if domains:
        return max(domains, key=lambda d: DOMAIN_PRIORITY.get(d, 0))
    else:
        return "search"


class TestDomainPrioritizationLogic:
    """Test core domain prioritization algorithm."""

    def test_local_business_beats_search(self):
        """local_business (10) should beat search (1)."""
        domains = ["search", "local_business"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"

    def test_local_business_beats_search_reversed_order(self):
        """Priority works regardless of domain order."""
        domains = ["local_business", "search"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"

    def test_finance_beats_search(self):
        """finance (9) should beat search (1)."""
        domains = ["search", "finance"]
        result = select_primary_capability_with_priority(domains)
        assert result == "finance"

    def test_geocoding_beats_search(self):
        """geocoding (8) should beat search (1)."""
        domains = ["search", "geocoding"]
        result = select_primary_capability_with_priority(domains)
        assert result == "geocoding"

    def test_mapping_beats_search(self):
        """mapping (7) should beat search (1)."""
        domains = ["search", "mapping"]
        result = select_primary_capability_with_priority(domains)
        assert result == "mapping"

    def test_research_beats_search(self):
        """research (6) should beat search (1)."""
        domains = ["search", "research"]
        result = select_primary_capability_with_priority(domains)
        assert result == "research"

    def test_wikipedia_beats_search(self):
        """wikipedia (5) should beat search (1)."""
        domains = ["search", "wikipedia"]
        result = select_primary_capability_with_priority(domains)
        assert result == "wikipedia"

    def test_local_business_beats_all_other_domains(self):
        """local_business (10) has highest priority."""
        domains = ["search", "wikipedia", "research", "mapping", "geocoding", "finance", "local_business"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"

    def test_finance_beats_lower_priority_domains(self):
        """finance (9) beats everything except local_business."""
        domains = ["search", "wikipedia", "research", "mapping", "geocoding", "finance"]
        result = select_primary_capability_with_priority(domains)
        assert result == "finance"

    def test_search_only_when_alone(self):
        """search is used when it's the only domain."""
        domains = ["search"]
        result = select_primary_capability_with_priority(domains)
        assert result == "search"

    def test_unknown_domain_has_zero_priority(self):
        """Unknown domains get priority 0, lower than search (1)."""
        domains = ["unknown_domain", "search"]
        result = select_primary_capability_with_priority(domains)
        assert result == "search"  # search (1) beats unknown (0)

    def test_multiple_unknown_domains_with_search(self):
        """search beats multiple unknown domains."""
        domains = ["unknown1", "unknown2", "search", "unknown3"]
        result = select_primary_capability_with_priority(domains)
        assert result == "search"

    def test_conversation_beats_search(self):
        """conversation (4) should beat search (1)."""
        domains = ["search", "conversation"]
        result = select_primary_capability_with_priority(domains)
        assert result == "conversation"

    def test_social_beats_search(self):
        """social (4) should beat search (1)."""
        domains = ["search", "social"]
        result = select_primary_capability_with_priority(domains)
        assert result == "social"

    def test_empty_domains_defaults_to_search(self):
        """Empty domains list should default to search."""
        domains = []
        result = select_primary_capability_with_priority(domains)
        assert result == "search"

    def test_restaurant_query_realistic_scenario(self):
        """
        Realistic scenario: LLM returns ["search", "local_business"]
        for "Recommend the top 3 restaurants there"
        """
        domains = ["search", "local_business"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"  # Must route to Yelp, not search!

    def test_stock_query_realistic_scenario(self):
        """
        Realistic scenario: LLM returns ["search", "finance"]
        for "Stock price of AAPL"
        """
        domains = ["search", "finance"]
        result = select_primary_capability_with_priority(domains)
        assert result == "finance"  # Must route to FinanceAgent, not search!

    def test_geocoding_query_realistic_scenario(self):
        """
        Realistic scenario: LLM returns ["search", "geocoding"]
        for "Coordinates of Tokyo Tower"
        """
        domains = ["search", "geocoding"]
        result = select_primary_capability_with_priority(domains)
        assert result == "geocoding"  # Must route to GeoAgent, not search!


class TestRestaurantQueryPrioritization:
    """Test prioritization for specific restaurant query scenarios."""

    def test_context_based_restaurant_query(self):
        """
        Query: "Recommend the top 3 restaurants there"
        Context: "there" = Tokyo from previous turn

        LLM might return: ["search", "local_business"]
        Must select: "local_business" (Yelp)
        """
        domains = ["search", "local_business"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"

    def test_explicit_restaurant_query(self):
        """
        Query: "Find the best sushi restaurants in Tokyo"

        LLM might return: ["local_business", "search"]
        Must select: "local_business" (Yelp)
        """
        domains = ["local_business", "search"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"

    def test_generic_food_query(self):
        """
        Query: "Where should I eat in Tokyo?"

        LLM might return: ["search", "local_business"]
        Must select: "local_business" (Yelp)
        """
        domains = ["search", "local_business"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"

    def test_restaurant_with_directions(self):
        """
        Query: "Find Italian restaurants and give me directions"

        LLM might return: ["mapping", "local_business", "search"]
        Must select: "local_business" (highest priority: 10)
        """
        domains = ["mapping", "local_business", "search"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"

    def test_restaurant_reviews_query(self):
        """
        Query: "Show me reviews for restaurants in Tokyo"

        LLM might return: ["search", "local_business"]
        Must select: "local_business" (Yelp has reviews)
        """
        domains = ["search", "local_business"]
        result = select_primary_capability_with_priority(domains)
        assert result == "local_business"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
