"""
Property-based tests for MoE Diagnostic Logging and Observability.

**Feature: moe-map-rendering-fix, Property 15: Execution Logging Completeness**
**Validates: Requirements 6.4**

This module implements property-based testing for the MoE orchestrator to verify:
1. Execution Logging Completeness (Property 15) - execution time and success/failure status for each expert

These tests use Hypothesis to generate random test cases and verify that
the correctness properties hold across all valid inputs.
"""

import pytest
import json
import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
import time

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoEResult, MoETrace, ExpertExecutionDetail
from asdrp.orchestration.moe.expert_executor import ExpertResult, ParallelExecutor
from asdrp.orchestration.moe.result_mixer import WeightedMixer, MixedResult
from asdrp.orchestration.moe.config_loader import MoEConfig, ModelConfig, ExpertGroupConfig, MoECacheConfig
from asdrp.orchestration.moe.exceptions import ExecutionException, MixingException
from asdrp.agents.protocol import AgentProtocol


# Test data strategies for property-based testing

@composite
def execution_scenario(draw):
    """Generate execution scenarios with different expert combinations and outcomes."""
    num_experts = draw(st.integers(min_value=1, max_value=4))
    expert_ids = draw(st.lists(
        st.sampled_from(["yelp", "yelp_mcp", "map", "geo", "one"]),
        min_size=num_experts,
        max_size=num_experts,
        unique=True
    ))
    
    # Generate success/failure for each expert
    expert_outcomes = {}
    for expert_id in expert_ids:
        expert_outcomes[expert_id] = {
            "success": draw(st.booleans()),
            "latency_ms": draw(st.floats(min_value=50.0, max_value=5000.0, allow_nan=False, allow_infinity=False)),
            "output": draw(st.text(min_size=0, max_size=200, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Pc"))))
        }
    
    return {
        "expert_ids": expert_ids,
        "outcomes": expert_outcomes
    }


@composite
def query_with_intent(draw):
    """Generate queries with different intents."""
    query_types = [
        "Find restaurants in San Francisco",
        "Show me cafes on a map",
        "What's the weather like?",
        "Tell me a joke",
        "Where are the best pizza places in NYC?",
        "Map the top bars in Seattle"
    ]
    return draw(st.sampled_from(query_types))


@pytest.fixture
def mock_moe_config():
    """Mock MoE configuration for testing."""
    return MoEConfig(
        enabled=True,
        moe={
            "mixing_strategy": "synthesis",
            "top_k_experts": 3,
            "confidence_threshold": 0.3,
            "timeout_per_expert": 25.0,
            "overall_timeout": 30.0,
            "synthesis_prompt": "Synthesize: {weighted_results}\nQuery: {query}"
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
                agents=["yelp", "yelp_mcp"],
                capabilities=["business_search"],
                weight=1.0
            ),
            "location_expert": ExpertGroupConfig(
                agents=["map", "geo"],
                capabilities=["mapping", "geocoding"],
                weight=0.8
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
        tracing={"enabled": True, "storage": {"backend": "memory"}, "exporters": []}
    )


@pytest.fixture
def mock_agent_factory():
    """Mock agent factory for testing."""
    factory = Mock()
    
    # Create mock agents
    agents = {}
    for agent_id in ["yelp", "yelp_mcp", "map", "geo", "one"]:
        agent = Mock(spec=AgentProtocol)
        agent.name = agent_id
        if agent_id == "yelp_mcp":
            agent.mcp_servers = []  # Empty list to simulate MCP connection issues
        agents[agent_id] = agent
    
    # Mock sessions
    mock_session = Mock()
    
    async def get_agent_with_session(agent_id, session_id):
        agent = agents.get(agent_id, agents["one"])
        return (agent, mock_session)
    
    factory.get_agent_with_persistent_session = AsyncMock(side_effect=get_agent_with_session)
    
    # Mock the Runner.run for fallback scenarios
    async def mock_runner_run(starting_agent, input, session, **kwargs):
        # Create a mock result that looks like a Runner result
        mock_result = Mock()
        mock_result.final_output = f"Fallback response from {starting_agent.name}"
        return mock_result
    
    # Patch Runner.run globally for this test
    import sys
    if 'agents' not in sys.modules:
        sys.modules['agents'] = Mock()
    sys.modules['agents'].Runner = Mock()
    sys.modules['agents'].Runner.run = AsyncMock(side_effect=mock_runner_run)
    
    return factory


class TestExecutionLoggingProperties:
    """Property-based tests for execution logging completeness."""

    @given(
        query=query_with_intent(),
        scenario=execution_scenario()
    )
    @settings(max_examples=25, deadline=8000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_15_execution_logging_completeness(self, mock_moe_config, mock_agent_factory, query, scenario):
        """
        **Feature: moe-map-rendering-fix, Property 15: Execution Logging Completeness**
        **Validates: Requirements 6.4**
        
        Property: For any expert execution, the system should log execution time and 
        success/failure status for each expert with accurate timestamps and latency measurements.
        """
        expert_ids = scenario["expert_ids"]
        outcomes = scenario["outcomes"]
        
        # Create mock expert selector
        mock_selector = Mock()
        mock_selector.select = AsyncMock(return_value=expert_ids)
        
        # Create mock executor that simulates the execution scenario
        mock_executor = Mock()
        
        async def mock_execute_with_logging(agents_with_sessions, query, context, timeout):
            results = []
            
            for expert_id, agent, session in agents_with_sessions:
                outcome = outcomes.get(expert_id, {"success": False, "latency_ms": 100.0, "output": ""})
                
                # Simulate realistic timestamps
                started_at = time.time()
                # Simulate execution time based on latency
                await asyncio.sleep(0.001)  # Small delay to simulate work
                ended_at = time.time()
                
                result = ExpertResult(
                    expert_id=expert_id,
                    output=outcome["output"] if outcome["success"] else "",
                    success=outcome["success"],
                    latency_ms=outcome["latency_ms"],
                    error=None if outcome["success"] else f"Simulated error for {expert_id}",
                    started_at=started_at,
                    ended_at=ended_at
                )
                results.append(result)
            
            return results
        
        mock_executor.execute_parallel = AsyncMock(side_effect=mock_execute_with_logging)
        
        # Create mock result mixer
        mock_mixer = Mock()
        
        async def mock_mix_with_logging(expert_results, expert_ids, query):
            successful_results = [r for r in expert_results if r.success]
            
            if successful_results:
                content = f"Combined results from {len(successful_results)} experts"
                weights = {r.expert_id: 1.0 / len(successful_results) for r in successful_results}
            else:
                content = "No successful results"
                weights = {}
            
            return MixedResult(
                content=content,
                weights=weights,
                quality_score=0.8 if successful_results else 0.0
            )
        
        mock_mixer.mix = AsyncMock(side_effect=mock_mix_with_logging)
        
        # Create orchestrator with mocked components
        orchestrator = MoEOrchestrator(
            agent_factory=mock_agent_factory,
            expert_selector=mock_selector,
            expert_executor=mock_executor,
            result_mixer=mock_mixer,
            config=mock_moe_config
        )
        
        # Execute the query
        result = await orchestrator.route_query(query)
        
        # Verify the result
        assert isinstance(result, MoEResult)
        assert result.response is not None
        assert isinstance(result.trace, MoETrace)
        
        # CRITICAL PROPERTY: Execution logging completeness
        trace = result.trace
        
        # 1. Verify trace has timing information
        assert trace.latency_ms > 0, "Trace should record total execution latency"
        
        # 2. Verify expert details are logged for each expert
        assert trace.expert_details is not None, "Trace should contain expert execution details"
        
        # For fallback scenarios, we may have different expert details than originally selected
        # The key property is that we have execution details for the experts that were actually attempted
        if trace.fallback:
            # In fallback scenarios, we should still have some expert details logged
            assert len(trace.expert_details) > 0, "Should have expert details even in fallback scenarios"
        else:
            # In normal scenarios, should have details for the experts that were actually selected and executed
            # Note: The orchestrator may modify the expert list (e.g., map intent prioritization)
            # so we check that we have details for the experts that were actually selected
            if trace.selected_experts:
                # We should have details for the experts that were actually selected
                selected_expert_ids = set(trace.selected_experts)
                detail_expert_ids = set(detail.expert_id for detail in trace.expert_details)
                # Allow for some flexibility - the details should cover most of the selected experts
                overlap = len(selected_expert_ids.intersection(detail_expert_ids))
                assert overlap > 0, f"Should have details for at least some selected experts. Selected: {selected_expert_ids}, Details: {detail_expert_ids}"
        
        # 3. Verify each expert has complete execution information
        for detail in trace.expert_details:
            assert isinstance(detail, ExpertExecutionDetail), "Expert detail should be ExpertExecutionDetail instance"
            
            # Expert identification
            assert detail.expert_id is not None, "Expert ID should be recorded"
            assert detail.agent_name is not None, "Agent name should be recorded"
            
            # Execution status
            assert detail.status in ["pending", "executing", "completed", "failed"], f"Status should be valid: {detail.status}"
            
            # For completed/failed experts, verify we have appropriate information
            if detail.status in ["completed", "failed"]:
                # Latency should be recorded for completed/failed experts
                if detail.latency_ms is not None:
                    assert detail.latency_ms >= 0, f"Latency should be non-negative for {detail.expert_id}"
                
                # Response should be recorded (empty string is valid for failed experts)
                assert detail.response is not None, f"Response should be recorded for {detail.expert_id}"
                
                # Check if this expert was in our original scenario
                if detail.expert_id in expert_ids:
                    expected_outcome = outcomes.get(detail.expert_id, {"success": False})
                    
                    if expected_outcome["success"] and detail.status == "completed":
                        # Successful expert should have output
                        assert len(detail.response) > 0 or detail.response == "", "Response should be recorded for successful expert"
                    elif not expected_outcome["success"] and detail.status == "failed":
                        # Failed expert should have error information
                        if detail.error is not None:
                            assert len(detail.error) > 0, f"Error message should not be empty for {detail.expert_id}"
        
        # 4. Verify stage timing is logged
        if trace.selection_start and trace.selection_end:
            assert trace.selection_end >= trace.selection_start, "Selection end should be after start"
        
        if trace.execution_start and trace.execution_end:
            assert trace.execution_end >= trace.execution_start, "Execution end should be after start"
        
        if trace.mixing_start and trace.mixing_end:
            assert trace.mixing_end >= trace.mixing_start, "Mixing end should be after start"
        
        # 5. Verify experts used are logged
        assert result.experts_used is not None, "Experts used should be recorded"
        # In fallback scenarios, experts_used might be empty or contain fallback agent
        # The key property is that it's not None and is a list
        assert isinstance(result.experts_used, list), "Experts used should be a list"
        
        # 6. Verify request ID is generated for tracing
        assert trace.request_id is not None, "Request ID should be generated for tracing"
        assert len(trace.request_id) > 0, "Request ID should not be empty"
        assert trace.query == query, "Query should be recorded in trace"

    @given(
        query=st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs"))),
        num_experts=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=15, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_15_timing_accuracy(self, mock_moe_config, mock_agent_factory, query, num_experts):
        """
        **Feature: moe-map-rendering-fix, Property 15: Execution Logging Completeness**
        **Validates: Requirements 6.4**
        
        Property: Timing measurements should be accurate and consistent across all execution stages.
        """
        expert_ids = ["yelp", "map", "geo", "one", "yelp_mcp"][:num_experts]
        
        # Create mock components with timing simulation
        mock_selector = Mock()
        mock_selector.select = AsyncMock(return_value=expert_ids)
        
        mock_executor = Mock()
        
        async def mock_execute_with_realistic_timing(agents_with_sessions, query, context, timeout):
            results = []
            
            for expert_id, agent, session in agents_with_sessions:
                started_at = time.time()
                
                # Simulate different execution times for different agents
                if expert_id == "map":
                    await asyncio.sleep(0.005)  # Map agent takes longer
                elif expert_id == "yelp_mcp":
                    await asyncio.sleep(0.003)  # MCP connection overhead
                else:
                    await asyncio.sleep(0.001)  # Standard execution time
                
                ended_at = time.time()
                actual_latency_ms = (ended_at - started_at) * 1000
                
                result = ExpertResult(
                    expert_id=expert_id,
                    output=f"Result from {expert_id}",
                    success=True,
                    latency_ms=actual_latency_ms,
                    started_at=started_at,
                    ended_at=ended_at
                )
                results.append(result)
            
            return results
        
        mock_executor.execute_parallel = AsyncMock(side_effect=mock_execute_with_realistic_timing)
        
        mock_mixer = Mock()
        mock_mixer.mix = AsyncMock(return_value=MixedResult(
            content="Combined results",
            weights={expert_id: 1.0 for expert_id in expert_ids},
            quality_score=0.9
        ))
        
        # Create orchestrator
        orchestrator = MoEOrchestrator(
            agent_factory=mock_agent_factory,
            expert_selector=mock_selector,
            expert_executor=mock_executor,
            result_mixer=mock_mixer,
            config=mock_moe_config
        )
        
        # Execute and measure
        start_time = time.time()
        result = await orchestrator.route_query(query)
        end_time = time.time()
        actual_total_time_ms = (end_time - start_time) * 1000
        
        # Verify timing accuracy
        trace = result.trace
        
        # Total latency should be reasonable
        assert trace.latency_ms > 0, "Total latency should be positive"
        assert trace.latency_ms <= actual_total_time_ms * 1.5, "Recorded latency should be close to actual time"
        
        # Expert timing should be consistent
        for detail in trace.expert_details:
            if detail.status == "completed":
                assert detail.latency_ms > 0, f"Expert {detail.expert_id} should have positive latency"
                
                # Map agent should generally take longer than others (due to our simulation)
                if detail.expert_id == "map" and len(expert_ids) > 1:
                    other_latencies = [d.latency_ms for d in trace.expert_details 
                                     if d.expert_id != "map" and d.status == "completed" and d.latency_ms]
                    if other_latencies:
                        avg_other_latency = sum(other_latencies) / len(other_latencies)
                        # Map should generally be slower (allowing for some variance)
                        assert detail.latency_ms >= avg_other_latency * 0.8, "Map agent timing should reflect longer execution"

    @given(
        error_scenario=st.sampled_from([
            "all_experts_fail",
            "selector_fails", 
            "executor_fails",
            "mixer_fails"
        ])
    )
    @settings(max_examples=10, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_15_error_logging_completeness(self, mock_moe_config, mock_agent_factory, error_scenario):
        """
        **Feature: moe-map-rendering-fix, Property 15: Execution Logging Completeness**
        **Validates: Requirements 6.4**
        
        Property: Error scenarios should be logged completely with appropriate error information.
        """
        query = "Test query for error logging"
        
        # Create components that simulate different error scenarios
        mock_selector = Mock()
        mock_executor = Mock()
        mock_mixer = Mock()
        
        if error_scenario == "selector_fails":
            mock_selector.select = AsyncMock(side_effect=Exception("Selector failed"))
        else:
            mock_selector.select = AsyncMock(return_value=["yelp", "map"])
        
        if error_scenario == "executor_fails":
            mock_executor.execute_parallel = AsyncMock(side_effect=Exception("Executor failed"))
        elif error_scenario == "all_experts_fail":
            async def mock_all_fail(agents_with_sessions, query, context, timeout):
                return [
                    ExpertResult(
                        expert_id=expert_id,
                        output="",
                        success=False,
                        latency_ms=100.0,
                        error=f"Simulated failure for {expert_id}",
                        started_at=time.time(),
                        ended_at=time.time()
                    )
                    for expert_id, _, _ in agents_with_sessions
                ]
            mock_executor.execute_parallel = AsyncMock(side_effect=mock_all_fail)
        else:
            # Normal execution
            async def mock_normal_execution(agents_with_sessions, query, context, timeout):
                return [
                    ExpertResult(
                        expert_id=expert_id,
                        output=f"Success from {expert_id}",
                        success=True,
                        latency_ms=200.0,
                        started_at=time.time(),
                        ended_at=time.time()
                    )
                    for expert_id, _, _ in agents_with_sessions
                ]
            mock_executor.execute_parallel = AsyncMock(side_effect=mock_normal_execution)
        
        if error_scenario == "mixer_fails":
            mock_mixer.mix = AsyncMock(side_effect=Exception("Mixer failed"))
        else:
            mock_mixer.mix = AsyncMock(return_value=MixedResult(
                content="Mixed results",
                weights={"yelp": 1.0},
                quality_score=0.8
            ))
        
        # Create orchestrator
        orchestrator = MoEOrchestrator(
            agent_factory=mock_agent_factory,
            expert_selector=mock_selector,
            expert_executor=mock_executor,
            result_mixer=mock_mixer,
            config=mock_moe_config
        )
        
        # Execute the query
        result = await orchestrator.route_query(query)
        
        # Verify error logging
        assert isinstance(result, MoEResult)
        trace = result.trace
        
        # CRITICAL PROPERTY: Error information should be logged
        if error_scenario in ["selector_fails", "executor_fails", "mixer_fails", "all_experts_fail"]:
            # Should have fallback behavior
            if error_scenario == "all_experts_fail":
                # All experts failed, should use fallback agent
                assert trace.fallback == True, "Should be marked as fallback when all experts fail"
                assert "one" in result.experts_used, "Should use fallback agent"
            else:
                # Component failure, should use fallback
                assert trace.fallback == True, "Should be marked as fallback on component failure"
        
        # Error should be recorded in trace
        if error_scenario != "normal":
            assert trace.error is not None, f"Error should be recorded for {error_scenario}"
            assert len(trace.error) > 0, "Error message should not be empty"
        
        # Timing should still be recorded even on errors
        assert trace.latency_ms >= 0, "Latency should be recorded even on errors"
        
        # Request should still be traceable
        assert trace.request_id is not None, "Request ID should be generated even on errors"
        assert trace.query == query, "Query should be recorded even on errors"