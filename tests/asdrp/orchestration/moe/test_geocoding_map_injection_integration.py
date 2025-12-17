"""
Integration test for geocoding-based map injection in result mixer.

Tests the complete workflow:
1. User query contains map intent ("show on map")
2. Yelp returns venues with addresses (but no coordinates)
3. Synthesized response has addresses
4. Geocoder extracts addresses and geocodes them
5. Places map JSON is auto-injected into response

This test validates the fix for the issue where queries like:
"What are the top 3 greek restaurants in San Francisco? Show them on a detailed map"
returned text without an interactive map.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from asdrp.orchestration.moe.result_mixer import WeightedMixer, MixedResult
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.config_loader import MoEConfig, ModelConfig, ExpertGroupConfig, MoECacheConfig


@pytest.fixture
def mock_moe_config():
    """Mock MoE configuration for testing."""
    return MoEConfig(
        enabled=True,
        moe={
            "mixing_strategy": "synthesis",
            "top_k_experts": 3,
        },
        models={
            "selection": ModelConfig(
                name="gpt-4.1-mini",
                temperature=0.0,
                max_tokens=1000
            ),
            "mixing": ModelConfig(
                name="gpt-4.1-mini",
                temperature=0.7,
                max_tokens=2000
            )
        },
        experts={
            "business_expert": ExpertGroupConfig(
                agents=["yelp"],
                capabilities=["restaurants"],
                weight=1.0
            ),
            "location_expert": ExpertGroupConfig(
                agents=["map"],
                capabilities=["maps"],
                weight=1.0
            )
        },
        cache=MoECacheConfig(
            enabled=False,
            type="none",
            storage={"backend": "none"},
            policy={}
        ),
        error_handling={
            "fallback_agent": "one",
            "fallback_message": "I apologize, but I encountered an issue."
        },
        tracing={"enabled": False, "storage": {"backend": "none"}, "exporters": []}
    )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_geocoding_map_injection_for_restaurant_query(mock_moe_config):
    """
    Test complete workflow: addresses → geocoding → map injection.

    Scenario: User asks for "top 3 greek restaurants" with "show on map"
    Expected: Even though Yelp returns only addresses, map is auto-injected via geocoding
    """
    mixer = WeightedMixer(mock_moe_config)

    query = "What are the top 3 greek restaurants in San Francisco? Show them on a detailed map"

    # Simulate Yelp agent response (addresses but NO coordinates)
    yelp_output = """Here are the top 3 Greek restaurants in San Francisco:

1. Souvla - 517 Hayes St, San Francisco, CA 94102
   Rating: 4.5/5 - Modern Greek street food

2. Kokkari Estiatorio - 200 Jackson St, San Francisco, CA 94111
   Rating: 4.4/5 - Upscale Greek dining

3. Milos Meze - 3348 Steiner St, San Francisco, CA 94123
   Rating: 4.6/5 - Traditional Greek cuisine"""

    expert_results = [
        ExpertResult(
            expert_id="yelp",
            output=yelp_output,
            success=True,
            latency_ms=500.0
        )
    ]

    # Mock OpenAI synthesis to return text without map
    with patch("openai.AsyncOpenAI") as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_message = Mock()
        # Synthesis returns clean text (no map JSON)
        mock_message.content = yelp_output
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock(total_tokens=500)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        # Mock geocoding to return coordinates
        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            mock_geocode.side_effect = [
                {"latitude": 37.7769, "longitude": -122.4211},  # Souvla
                {"latitude": 37.7955, "longitude": -122.4020},  # Kokkari
                {"latitude": 37.7684, "longitude": -122.4147}   # Milos Meze
            ]

            # Execute mixing (should auto-inject map via geocoding)
            result = await mixer.mix(expert_results, ["yelp"], query)

            # Verify result
            assert isinstance(result, MixedResult)
            assert result.content

            # CRITICAL: Verify map was injected
            assert "```json" in result.content
            assert "interactive_map" in result.content
            assert "places" in result.content

            # Verify markers are present
            assert "37.7769" in result.content or "37.77" in result.content  # Souvla coords
            assert "Souvla" in result.content
            assert "Kokkari" in result.content
            assert "Milos" in result.content

            # Verify venues were geocoded (at least 3, may extract more due to pattern matching)
            assert mock_geocode.call_count >= 3


@pytest.mark.asyncio
async def test_geocoding_map_injection_skipped_for_non_map_queries(mock_moe_config):
    """
    Test that geocoding is NOT triggered for queries without map intent.

    Scenario: User asks for restaurants but doesn't request a map
    Expected: No geocoding, no map injection
    """
    mixer = WeightedMixer(mock_moe_config)

    query = "What are the best greek restaurants in San Francisco?"  # No "map" keyword

    yelp_output = "1. Souvla - 517 Hayes St, San Francisco, CA 94102"

    expert_results = [
        ExpertResult(
            expert_id="yelp",
            output=yelp_output,
            success=True,
            latency_ms=500.0
        )
    ]

    with patch("openai.AsyncOpenAI") as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = yelp_output
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock(total_tokens=500)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            result = await mixer.mix(expert_results, ["yelp"], query)

            # Verify NO geocoding was attempted (query lacks map intent)
            assert mock_geocode.call_count == 0

            # Verify NO map in response
            assert "```json" not in result.content or "interactive_map" not in result.content


@pytest.mark.asyncio
async def test_geocoding_map_injection_handles_geocoding_failure_gracefully(mock_moe_config):
    """
    Test graceful handling when geocoding fails.

    Scenario: Geocoding API fails or returns no results
    Expected: Response returned without map (fail-safe, no crash)
    """
    mixer = WeightedMixer(mock_moe_config)

    query = "Show me greek restaurants on a map in San Francisco"

    yelp_output = "1. Souvla - 517 Hayes St, San Francisco, CA 94102"

    expert_results = [
        ExpertResult(
            expert_id="yelp",
            output=yelp_output,
            success=True,
            latency_ms=500.0
        )
    ]

    with patch("openai.AsyncOpenAI") as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = yelp_output
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock(total_tokens=500)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        # Mock geocoding to fail
        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            mock_geocode.return_value = None  # Geocoding failure

            # Should NOT crash
            result = await mixer.mix(expert_results, ["yelp"], query)

            # Verify result is returned (fail-safe)
            assert isinstance(result, MixedResult)
            assert result.content

            # Map may or may not be present (depends on fallback logic)
            # The important thing is: NO CRASH


if __name__ == "__main__":
    # Run with: pytest tests/asdrp/orchestration/moe/test_geocoding_map_injection_integration.py -v
    pytest.main([__file__, "-v"])
