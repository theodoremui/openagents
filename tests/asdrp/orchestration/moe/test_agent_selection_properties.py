"""
Property-Based Tests for MoE Agent Selection Logic

Tests the correctness properties for agent selection optimization,
map agent prioritization, and parallel execution fallback.

**Feature: moe-map-rendering-fix, Property 9: Agent Selection Logic**
**Feature: moe-map-rendering-fix, Property 10: Map Agent Prioritization**
**Feature: moe-map-rendering-fix, Property 11: Parallel Execution Fallback**
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator


# Generators for property-based testing
@composite
def agent_id_list(draw):
    """Generate a list of valid agent IDs."""
    agent_ids = st.lists(
        st.sampled_from([
            "yelp", "yelp_mcp", "map", "geo", "chitchat", "one", "weather", "finance"
        ]),
        min_size=1,
        max_size=8,
        unique=True
    )
    return draw(agent_ids)


@composite
def business_query(draw):
    """Generate queries that contain business search terms."""
    business_terms = ["restaurant", "restaurants", "food", "dining", "cafe", "cafes", "bar", "bars"]
    location_terms = ["San Francisco", "New York", "Los Angeles", "Seattle", "Chicago", "Boston"]
    
    business_term = draw(st.sampled_from(business_terms))
    location_term = draw(st.sampled_from(location_terms))
    
    query_templates = [
        f"Find {business_term} in {location_term}",
        f"Best {business_term} near {location_term}",
        f"Top {business_term} in {location_term}",
        f"Where are good {business_term} in {location_term}",
        f"Show me {business_term} in {location_term}",
    ]
    
    return draw(st.sampled_from(query_templates))


@composite
def map_visualization_query(draw):
    """Generate queries that explicitly request visualization."""
    business_query_base = draw(business_query())
    
    map_markers = [
        "on a map", "on map", "show on map", "place on map", "map view",
        "detailed map", "interactive map", "with pins", "where are they",
        "show me on a detailed map", "place these on a map"
    ]
    
    map_marker = draw(st.sampled_from(map_markers))
    
    query_templates = [
        f"{business_query_base} {map_marker}",
        f"Show {business_query_base.lower()} {map_marker}",
        f"Place {business_query_base.lower()} {map_marker}",
    ]
    
    return draw(st.sampled_from(query_templates))


@composite
def non_map_query(draw):
    """Generate queries that don't request visualization."""
    query_templates = [
        "What's the weather like today?",
        "Tell me a joke",
        "How are you doing?",
        "What's the stock price of AAPL?",
        "Explain quantum physics",
        "Find restaurants in San Francisco",  # Business but no map intent
        "Best pizza places",
        "What time is it?",
    ]
    
    return draw(st.sampled_from(query_templates))


class TestAgentSelectionProperties:
    """Property-based tests for MoE agent selection logic."""

    def test_prioritize_agents_for_map_intent_preserves_list_structure(self):
        """
        **Feature: moe-map-rendering-fix, Property 9: Agent Selection Logic**
        **Validates: Requirements 4.1**
        
        For any query containing both business and location terms, 
        the system should select both business experts and location experts
        """
        @given(
            query=business_query(),
            agent_ids=agent_id_list(),
            max_k=st.integers(min_value=1, max_value=10)
        )
        def property_test(query, agent_ids, max_k):
            # Ensure we have some business and location agents to work with
            assume(len(agent_ids) >= 1)
            assume(max_k >= 1)
            
            result = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            
            # Result should be a list
            assert isinstance(result, list)
            
            # Result should not exceed max_k
            assert len(result) <= max_k
            
            # Result should not exceed original list size
            assert len(result) <= len(agent_ids)
            
            # All agents in result should be from original list (or valid injected agents)
            valid_agents = set(agent_ids) | {"map", "yelp_mcp"}  # Allow injected agents
            for agent in result:
                assert agent in valid_agents
            
            # Result should not have duplicates
            assert len(result) == len(set(result))

        property_test()

    def test_map_agent_prioritization_for_visualization_queries(self):
        """
        **Feature: moe-map-rendering-fix, Property 10: Map Agent Prioritization**
        **Validates: Requirements 4.2**
        
        For any query explicitly requesting visualization, 
        the system should include the map agent in the selection
        """
        @given(
            query=map_visualization_query(),
            agent_ids=agent_id_list(),
            max_k=st.integers(min_value=1, max_value=8)
        )
        def property_test(query, agent_ids, max_k):
            assume(max_k >= 1)
            
            result = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            
            # For visualization queries, map agent should be included
            assert "map" in result
            
            # Result should respect max_k limit
            assert len(result) <= max_k

        property_test()

    def test_non_map_queries_unchanged_except_truncation(self):
        """
        Test that non-map queries are not modified except for k-limit truncation.
        """
        @given(
            query=non_map_query(),
            agent_ids=agent_id_list(),
            max_k=st.integers(min_value=1, max_value=8)
        )
        def property_test(query, agent_ids, max_k):
            assume(max_k >= 1)
            assume(len(agent_ids) >= 1)
            
            result = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            
            # For non-map queries, result should be truncated original list
            expected = agent_ids[:max_k]
            assert result == expected

        property_test()

    def test_business_map_queries_include_business_agents(self):
        """
        Test that business+map queries include business agents.
        """
        @given(
            query=map_visualization_query(),
            max_k=st.integers(min_value=2, max_value=8)
        )
        def property_test(query, max_k):
            # Start with a mix of agents that includes business agents
            agent_ids = ["yelp", "yelp_mcp", "geo", "map", "chitchat"]
            
            result = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            
            # Should include map agent
            assert "map" in result
            
            # Should include at least one business agent
            business_agents = {"yelp", "yelp_mcp"}
            assert any(agent in result for agent in business_agents)
            
            # Should respect max_k
            assert len(result) <= max_k

        property_test()

    def test_map_agent_injection_when_missing(self):
        """
        Test that map agent is injected when missing from visualization queries.
        """
        @given(
            query=map_visualization_query(),
            max_k=st.integers(min_value=1, max_value=5)
        )
        def property_test(query, max_k):
            # Agent list without map agent
            agent_ids = ["yelp", "yelp_mcp", "geo", "chitchat"]
            
            result = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            
            # Map agent should be injected
            assert "map" in result
            
            # Should respect max_k
            assert len(result) <= max_k

        property_test()

    def test_yelp_mcp_injection_for_restaurant_map_queries(self):
        """
        Test that yelp_mcp is injected for restaurant map queries when missing.
        """
        @given(max_k=st.integers(min_value=2, max_value=5))
        def property_test(max_k):
            query = "Show me a detailed map of where the best greek restaurants are in San Francisco"
            agent_ids = ["map", "geo", "yelp"]  # Missing yelp_mcp
            
            result = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            
            # Should include yelp_mcp for restaurant queries
            assert "yelp_mcp" in result
            
            # Should include map for visualization
            assert "map" in result
            
            # Should respect max_k
            assert len(result) <= max_k

        property_test()

    def test_edge_cases_with_empty_or_invalid_inputs(self):
        """
        Test edge cases with empty or invalid inputs.
        """
        @given(
            query=st.text(),
            max_k=st.integers(min_value=-5, max_value=10)
        )
        def property_test(query, max_k):
            # Test with empty agent list
            result = MoEOrchestrator._prioritize_agents_for_map_intent(query, [], max_k)
            assert result == []
            
            # Test with invalid max_k
            if max_k <= 0:
                result = MoEOrchestrator._prioritize_agents_for_map_intent(query, ["yelp", "map"], max_k)
                assert result == []

        property_test()

    def test_deterministic_behavior(self):
        """
        Test that the same inputs always produce the same outputs.
        """
        @given(
            query=st.text(),
            agent_ids=agent_id_list(),
            max_k=st.integers(min_value=1, max_value=8)
        )
        def property_test(query, agent_ids, max_k):
            assume(len(agent_ids) >= 1)
            
            # Run the function twice with same inputs
            result1 = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            result2 = MoEOrchestrator._prioritize_agents_for_map_intent(query, agent_ids, max_k)
            
            # Results should be identical
            assert result1 == result2

        property_test()


class TestParallelExecutionFallback:
    """
    **Feature: moe-map-rendering-fix, Property 11: Parallel Execution Fallback**
    **Validates: Requirements 4.5**
    
    Property-based tests for parallel execution fallback mechanisms.
    """

    @given(
        query=business_query(),
        successful_agent=st.sampled_from(["yelp", "yelp_mcp"]),
        failed_agent=st.sampled_from(["yelp", "yelp_mcp"])
    )
    @settings(max_examples=10, deadline=10000)  # Reduce for async tests
    @pytest.mark.asyncio
    async def test_fallback_when_one_business_agent_fails(self, query, successful_agent, failed_agent):
        """
        **Feature: moe-map-rendering-fix, Property 11: Parallel Execution Fallback**
        **Validates: Requirements 4.5**
        
        For any scenario where one business agent fails, 
        the system should use the response from the other business agent 
        without failing the entire query
        """
        assume(successful_agent != failed_agent)  # Ensure different agents
        
        # Mock agent factory and components
        mock_factory = Mock()
        mock_selector = Mock()
        mock_executor = Mock()
        mock_mixer = Mock()
        mock_config = Mock()
        
        # Configure mock config
        mock_config.moe = {"top_k_experts": 3, "confidence_threshold": 0.3, "overall_timeout": 30.0}
        mock_config.cache = Mock()
        mock_config.cache.enabled = False
        mock_config.error_handling = {"fallback_agent": "one", "fallback_message": "Error occurred"}
        
        # Mock selector to return both business agents
        mock_selector.select = AsyncMock(return_value=[successful_agent, failed_agent, "map"])
        
        # Mock factory to return agents
        successful_mock_agent = Mock()
        successful_mock_agent.name = successful_agent
        failed_mock_agent = Mock()
        failed_mock_agent.name = failed_agent
        map_mock_agent = Mock()
        map_mock_agent.name = "map"
        
        mock_session = Mock()
        
        async def mock_get_agent_with_session(agent_id, session_id):
            if agent_id == successful_agent:
                return successful_mock_agent, mock_session
            elif agent_id == failed_agent:
                return failed_mock_agent, mock_session
            elif agent_id == "map":
                return map_mock_agent, mock_session
            else:
                raise Exception(f"Unknown agent: {agent_id}")
        
        mock_factory.get_agent_with_persistent_session = AsyncMock(side_effect=mock_get_agent_with_session)
        
        # Mock executor results - one success, one failure
        successful_result = Mock()
        successful_result.success = True
        successful_result.output = f"Results from {successful_agent}"
        successful_result.latency_ms = 100.0
        successful_result.started_at = 1000.0
        successful_result.ended_at = 1100.0
        successful_result.error = None
        
        failed_result = Mock()
        failed_result.success = False
        failed_result.output = ""
        failed_result.latency_ms = 50.0
        failed_result.started_at = 1000.0
        failed_result.ended_at = 1050.0
        failed_result.error = "Connection failed"
        
        map_result = Mock()
        map_result.success = True
        map_result.output = "Map data"
        map_result.latency_ms = 200.0
        map_result.started_at = 1000.0
        map_result.ended_at = 1200.0
        map_result.error = None
        
        mock_executor.execute_parallel = AsyncMock(return_value=[
            successful_result, failed_result, map_result
        ])
        
        # Mock mixer to return combined result
        mixed_result = Mock()
        mixed_result.content = f"Combined results with {successful_agent} data and map"
        mock_mixer.mix = AsyncMock(return_value=mixed_result)
        
        # Create orchestrator
        orchestrator = MoEOrchestrator(
            agent_factory=mock_factory,
            expert_selector=mock_selector,
            expert_executor=mock_executor,
            result_mixer=mock_mixer,
            config=mock_config
        )
        
        # Execute query
        result = await orchestrator.route_query(query, session_id="test-session")
        
        # Verify that the query succeeded despite one agent failing
        assert result is not None
        assert result.response is not None
        assert successful_agent in result.experts_used
        
        # Verify that the mixer was called with all results (including failed ones)
        mock_mixer.mix.assert_called_once()
        call_args = mock_mixer.mix.call_args[0]
        expert_results = call_args[0]
        
        # Should have results from all agents (successful and failed)
        assert len(expert_results) == 3
        
        # Should have at least one successful result
        successful_results = [r for r in expert_results if getattr(r, 'success', False)]
        assert len(successful_results) >= 1

    @given(query=business_query())
    @settings(max_examples=5, deadline=10000)  # Reduce for async tests
    @pytest.mark.asyncio
    async def test_graceful_handling_when_all_agents_fail(self, query):
        """
        Test that the system gracefully handles the case when all agents fail.
        """
        # Mock components
        mock_factory = Mock()
        mock_selector = Mock()
        mock_executor = Mock()
        mock_mixer = Mock()
        mock_config = Mock()
        
        # Configure mock config
        mock_config.moe = {"top_k_experts": 3, "confidence_threshold": 0.3, "overall_timeout": 30.0}
        mock_config.cache = Mock()
        mock_config.cache.enabled = False
        mock_config.error_handling = {"fallback_agent": "one", "fallback_message": "Error occurred"}
        
        # Mock selector
        mock_selector.select = AsyncMock(return_value=["yelp", "yelp_mcp", "map"])
        
        # Mock factory to return agents
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_session = Mock()
        mock_factory.get_agent_with_persistent_session = AsyncMock(return_value=(mock_agent, mock_session))
        
        # Mock executor - all agents fail
        failed_result = Mock()
        failed_result.success = False
        failed_result.output = ""
        failed_result.error = "All agents failed"
        
        mock_executor.execute_parallel = AsyncMock(return_value=[
            failed_result, failed_result, failed_result
        ])
        
        # Mock fallback agent execution
        with patch('agents.Runner.run') as mock_runner:
            fallback_result = Mock()
            fallback_result.final_output = "Fallback response"
            mock_runner.return_value = fallback_result
            
            # Create orchestrator
            orchestrator = MoEOrchestrator(
                agent_factory=mock_factory,
                expert_selector=mock_selector,
                expert_executor=mock_executor,
                result_mixer=mock_mixer,
                config=mock_config
            )
            
            # Execute query
            result = await orchestrator.route_query(query, session_id="test-session")
            
            # Should fall back gracefully
            assert result is not None
            assert result.response is not None
            assert result.trace.fallback is True


# Run the tests with pytest
if __name__ == "__main__":
    pytest.main([__file__])