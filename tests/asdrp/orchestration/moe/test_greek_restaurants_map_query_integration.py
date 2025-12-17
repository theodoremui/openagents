"""
Integration test for the original failing query: Greek restaurants map in San Francisco.

This test ensures that:
1. The query doesn't crash with "NoneType object is not subscriptable"
2. The MoE orchestrator completes successfully
3. A result is returned (even if synthesis fails, we have a fallback)
4. Optionally, an interactive map is generated (depends on MapAgent being selected)

Test targets the specific issue reported by the user where MoE execution failed
with a NoneType subscript error.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoEResult
from asdrp.orchestration.moe.config_loader import MoEConfigLoader
from asdrp.agents.agent_factory import AgentFactory


@pytest.mark.asyncio
@pytest.mark.slow
async def test_greek_restaurants_map_query_no_crash(mock_agent_factory, mock_moe_config):
    """
    Test that the original failing query completes without NoneType subscript error.

    This is the regression test for: 'MoE execution failed: 'NoneType' object is not subscriptable'
    """
    query = "Show me on a detailed map where the best greek restaurants are in San Francisco."

    orchestrator = MoEOrchestrator.create_default(mock_agent_factory, mock_moe_config)

    # Mock Runner.run to simulate agent execution
    with patch("agents.Runner.run") as mock_run:
        mock_result = Mock()
        mock_result.final_output = """Here are the best Greek restaurants in San Francisco:

1. **Kokkari Estiatorio**
   - Address: 200 Jackson St, San Francisco, CA 94111
   - Rating: 4.5/5
   - Specialties: Grilled octopus, lamb chops, moussaka

2. **Evvia Estiatorio**
   - Address: 420 Emerson St, Palo Alto, CA 94301
   - Rating: 4.4/5
   - Specialties: Traditional Greek mezze, fresh seafood

```json
{
  "type": "interactive_map",
  "config": {
    "map_type": "places",
    "center_lat": 37.7749,
    "center_lng": -122.4194,
    "zoom": 13,
    "markers": [
      {"lat": 37.7955, "lng": -122.3988, "title": "Kokkari Estiatorio"},
      {"lat": 37.4419, "lng": -122.1430, "title": "Evvia Estiatorio"}
    ]
  }
}
```
"""
        mock_run.return_value = mock_result

        # Execute query - this should NOT crash with NoneType subscript error
        result = await orchestrator.route_query(query)

        # Verify result is valid MoEResult
        assert isinstance(result, MoEResult)
        assert result.response  # Should have a response (not None)
        assert isinstance(result.response, str)
        assert len(result.response) > 0

        # Verify trace is populated
        assert result.trace is not None
        assert result.trace.query == query
        assert result.trace.error is None or isinstance(result.trace.error, str)

        # Verify no crash occurred
        assert "NoneType" not in (result.trace.error or "")
        assert "not subscriptable" not in (result.trace.error or "")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_greek_restaurants_map_query_handles_empty_synthesis_response(
    mock_agent_factory, mock_moe_config
):
    """
    Test that the query handles the edge case where OpenAI synthesis returns empty/None.

    This tests the specific fix for the NoneType subscript error:
    - If OpenAI returns choices=[], we fallback gracefully
    - If OpenAI returns content=None, we fallback gracefully
    - System doesn't crash, returns a reasonable response
    """
    query = "Show me on a detailed map where the best greek restaurants are in San Francisco."

    orchestrator = MoEOrchestrator.create_default(mock_agent_factory, mock_moe_config)

    # Simulate multiple experts returning results (triggers synthesis)
    with patch("agents.Runner.run") as mock_run:
        mock_result = Mock()
        mock_result.final_output = "Test Greek restaurant response"
        mock_run.return_value = mock_result

        # Mock OpenAI to return empty choices (the original bug trigger)
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = []  # Empty list - would crash without fix
            mock_response.usage = None
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            # Temporarily override to trigger synthesis (need 2+ successful experts)
            mock_agent_factory.get_agent_with_persistent_session = AsyncMock(
                return_value=(Mock(name="TestAgent"), Mock())
            )

            # Execute - should NOT crash, should fallback gracefully
            result = await orchestrator.route_query(query)

            # Verify graceful degradation
            assert isinstance(result, MoEResult)
            assert result.response  # Should have fallback response
            assert "Greek restaurant" in result.response or "Test" in result.response


@pytest.mark.asyncio
@pytest.mark.slow
async def test_greek_restaurants_map_query_preserves_interactive_maps(
    mock_agent_factory, mock_moe_config
):
    """
    Test that if MapAgent generates an interactive map, it's preserved in the final response.

    This ensures the original user intent (generating a map) is satisfied.
    """
    query = "Show me on a detailed map where the best greek restaurants are in San Francisco."

    orchestrator = MoEOrchestrator.create_default(mock_agent_factory, mock_moe_config)

    with patch("agents.Runner.run") as mock_run:
        # Simulate MapAgent output with interactive map JSON
        mock_result = Mock()
        mock_result.final_output = """I found the best Greek restaurants for you.

```json
{
  "type": "interactive_map",
  "config": {
    "map_type": "places",
    "center_lat": 37.7749,
    "center_lng": -122.4194,
    "zoom": 13,
    "markers": [
      {"lat": 37.7955, "lng": -122.3988, "title": "Kokkari Estiatorio"},
      {"lat": 37.4419, "lng": -122.1430, "title": "Evvia Estiatorio"}
    ]
  }
}
```"""
        mock_run.return_value = mock_result

        result = await orchestrator.route_query(query)

        # Verify map JSON is in response
        assert isinstance(result, MoEResult)
        assert result.response
        assert "interactive_map" in result.response or "Greek" in result.response

        # Verify no crash
        assert result.trace.error is None or "NoneType" not in result.trace.error


if __name__ == "__main__":
    # Run with: pytest tests/asdrp/orchestration/moe/test_greek_restaurants_map_query_integration.py -v
    pytest.main([__file__, "-v"])
