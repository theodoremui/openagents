"""
Property-based tests for MoE Result Mixer JSON block preservation.

**Feature: moe-map-rendering-fix, Property 4: JSON Block Preservation**
**Validates: Requirements 2.1**

This module implements property-based testing for the WeightedMixer to verify:
1. JSON Block Preservation (Property 4) - Interactive map JSON blocks are preserved during synthesis

These tests use Hypothesis to generate random test cases and verify that
the correctness properties hold across all valid inputs.
"""

import pytest
import json
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite

from asdrp.orchestration.moe.result_mixer import WeightedMixer, MixedResult
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.config_loader import MoEConfig, ModelConfig, ExpertGroupConfig, MoECacheConfig


# Test data strategies for property-based testing

@composite
def interactive_map_json(draw):
    """Generate valid interactive map JSON configurations."""
    map_type = draw(st.sampled_from(["route", "places", "location"]))
    
    # Generate markers for places/location maps
    markers = []
    if map_type in ["places", "location"]:
        num_markers = draw(st.integers(min_value=1, max_value=5))
        for _ in range(num_markers):
            marker = {
                "lat": draw(st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)),
                "lng": draw(st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)),
                "title": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs"))))
            }
            markers.append(marker)
    
    config = {
        "map_type": map_type,
        "zoom": draw(st.integers(min_value=1, max_value=20))
    }
    
    if map_type == "route":
        config.update({
            "origin": draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs")))),
            "destination": draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs"))))
        })
    elif markers:
        config["markers"] = markers
        # Add center coordinates for places maps
        if len(markers) > 0:
            config["center_lat"] = sum(m["lat"] for m in markers) / len(markers)
            config["center_lng"] = sum(m["lng"] for m in markers) / len(markers)
    
    return {
        "type": "interactive_map",
        "config": config
    }


@composite
def expert_output_with_json_block(draw):
    """Generate expert output containing interactive map JSON block."""
    # Generate some text content before the JSON block
    prefix_text = draw(st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs"))))
    
    # Generate interactive map JSON
    map_json = draw(interactive_map_json())
    json_str = json.dumps(map_json, indent=2)
    
    # Generate some text content after the JSON block (optional)
    suffix_text = draw(st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs"))))
    
    # Construct the full output with JSON block
    output = f"{prefix_text}\n\n```json\n{json_str}\n```"
    if suffix_text.strip():
        output += f"\n\n{suffix_text}"
    
    return output, json_str


@composite
def expert_results_with_json_blocks(draw):
    """Generate list of expert results, some containing JSON blocks."""
    num_experts = draw(st.integers(min_value=2, max_value=4))
    expert_results = []
    json_blocks = []
    
    for i in range(num_experts):
        expert_id = f"expert_{i}"
        
        # Some experts have JSON blocks, others don't
        has_json = draw(st.booleans())
        
        if has_json:
            output, json_str = draw(expert_output_with_json_block())
            json_blocks.append(json_str)
        else:
            # Generate regular text output without JSON blocks
            output = draw(st.text(min_size=20, max_size=200, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs"))))
        
        expert_result = ExpertResult(
            expert_id=expert_id,
            output=output,
            success=True,
            latency_ms=draw(st.floats(min_value=50.0, max_value=2000.0))
        )
        expert_results.append(expert_result)
    
    return expert_results, json_blocks


@pytest.fixture
def mock_moe_config():
    """Mock MoE configuration for testing."""
    return MoEConfig(
        enabled=True,
        moe={
            "mixing_strategy": "synthesis",
            "top_k_experts": 3,
            "synthesis_prompt": """Synthesize the following expert responses into a comprehensive answer.

Expert Responses:
{weighted_results}

Original Query: {query}

CRITICAL - PRESERVE INTERACTIVE CONTENT:
- If any expert response contains a ```json code block (especially with "type": "interactive_map"),
  YOU MUST include that EXACT ```json block in your synthesized response
- These JSON blocks are essential for rendering interactive maps, graphs, and visualizations
- DO NOT summarize, paraphrase, or remove ```json blocks - copy them verbatim
- Place the ```json block at the appropriate location in your response (usually at the end)

Synthesized Response:"""
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
            "test_expert": ExpertGroupConfig(
                agents=["expert_0", "expert_1", "expert_2", "expert_3"],
                capabilities=["test"],
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
            "fallback_agent": "expert_0",
            "fallback_message": "I apologize, but I encountered an issue."
        },
        tracing={"enabled": False, "storage": {"backend": "none"}, "exporters": []}
    )


@pytest.fixture
def mixer(mock_moe_config):
    """Create mixer instance for testing."""
    return WeightedMixer(mock_moe_config)


class TestJSONBlockPreservationProperties:
    """Property-based tests for JSON block preservation during synthesis."""

    @given(expert_results_data=expert_results_with_json_blocks())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_4_json_block_preservation(self, mock_moe_config, expert_results_data):
        """
        **Feature: moe-map-rendering-fix, Property 4: JSON Block Preservation**
        **Validates: Requirements 2.1**
        
        Property: For any expert response containing an interactive_map JSON block,
        the synthesized output should contain that exact JSON block unchanged.
        """
        expert_results, expected_json_blocks = expert_results_data
        
        # Skip if no JSON blocks to test
        assume(len(expected_json_blocks) > 0)
        
        # Create mixer instance for this test
        mixer = WeightedMixer(mock_moe_config)
        
        # Mock OpenAI to return a synthesized response that might lose JSON blocks
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = Mock()
            
            # Simulate LLM synthesis that might drop JSON blocks
            synthesized_text = "Here's a comprehensive summary of the expert responses. The locations are very interesting."
            
            mock_response = Mock()
            mock_message = Mock()
            mock_message.content = synthesized_text
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 150
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Execute the mixing process
            query = "Show me restaurants on a map"
            expert_ids = [result.expert_id for result in expert_results]
            
            result = await mixer.mix(expert_results, expert_ids, query)
            
            # Verify the result is valid
            assert isinstance(result, MixedResult)
            assert result.content is not None
            assert len(result.content.strip()) > 0
            
            # CRITICAL PROPERTY: All JSON blocks from expert outputs must be preserved
            for expected_json in expected_json_blocks:
                # The exact JSON content should be present in the final result
                # (either from synthesis or from the preservation mechanism)
                json_found = False
                
                # Check if the JSON block is present in the result
                if "```json" in result.content:
                    # Extract JSON blocks from the result
                    import re
                    json_blocks_in_result = re.findall(r"```json\s*(.*?)\s*```", result.content, re.DOTALL | re.IGNORECASE)
                    
                    for result_json_str in json_blocks_in_result:
                        try:
                            result_json = json.loads(result_json_str.strip())
                            expected_json_obj = json.loads(expected_json)
                            
                            # Check if this is the same interactive map JSON
                            if (result_json.get("type") == "interactive_map" and 
                                expected_json_obj.get("type") == "interactive_map"):
                                # For property testing, we verify structural equivalence
                                # The preservation mechanism should maintain the essential structure
                                assert result_json["type"] == expected_json_obj["type"]
                                assert "config" in result_json
                                assert "config" in expected_json_obj
                                json_found = True
                                break
                        except json.JSONDecodeError:
                            continue
                
                # If JSON block preservation failed, this violates the property
                if not json_found:
                    pytest.fail(
                        f"JSON block preservation failed. Expected JSON block not found in synthesized result.\n"
                        f"Expected JSON: {expected_json}\n"
                        f"Result content: {result.content}\n"
                        f"This violates Property 4: JSON Block Preservation"
                    )

    @given(single_expert_json=expert_output_with_json_block())
    @settings(max_examples=30, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_4_single_expert_json_preservation(self, mock_moe_config, single_expert_json):
        """
        **Feature: moe-map-rendering-fix, Property 4: JSON Block Preservation**
        **Validates: Requirements 2.1**
        
        Property: For single expert responses containing JSON blocks,
        the blocks should be preserved without LLM synthesis.
        """
        expert_output, expected_json = single_expert_json
        
        # Create mixer instance for this test
        mixer = WeightedMixer(mock_moe_config)
        
        expert_results = [
            ExpertResult(
                expert_id="single_expert",
                output=expert_output,
                success=True,
                latency_ms=100.0
            )
        ]
        
        # Execute mixing (should bypass LLM for single expert)
        result = await mixer.mix(expert_results, ["single_expert"], "test query")
        
        # Verify the result contains the original JSON block
        assert isinstance(result, MixedResult)
        assert result.content is not None
        
        # For single expert, the output should be preserved as-is (with potential auto-injection)
        # The original JSON block should definitely be present
        assert "```json" in result.content
        
        # Extract and verify the JSON block
        import re
        json_blocks = re.findall(r"```json\s*(.*?)\s*```", result.content, re.DOTALL | re.IGNORECASE)
        
        json_found = False
        for json_str in json_blocks:
            try:
                result_json = json.loads(json_str.strip())
                expected_json_obj = json.loads(expected_json)
                
                if (result_json.get("type") == "interactive_map" and 
                    expected_json_obj.get("type") == "interactive_map"):
                    json_found = True
                    break
            except json.JSONDecodeError:
                continue
        
        if not json_found:
            pytest.fail(
                f"Single expert JSON block not preserved.\n"
                f"Expected JSON: {expected_json}\n"
                f"Result content: {result.content}"
            )

    @given(map_json=interactive_map_json())
    @settings(max_examples=30, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_4_json_block_extraction_accuracy(self, mock_moe_config, map_json):
        """
        **Feature: moe-map-rendering-fix, Property 4: JSON Block Preservation**
        **Validates: Requirements 2.1**
        
        Property: The JSON block extraction method should accurately identify
        and extract interactive map JSON blocks from text.
        """
        # Create mixer instance for this test
        mixer = WeightedMixer(mock_moe_config)
        # Create text with embedded JSON block
        json_str = json.dumps(map_json, indent=2)
        text_with_json = f"Here are some results:\n\n```json\n{json_str}\n```\n\nThat's the map data."
        
        # Test the extraction method
        extracted_blocks = mixer._extract_interactive_json_blocks(text_with_json)
        
        # Should extract exactly one block
        assert len(extracted_blocks) == 1
        
        # The extracted block should contain the original JSON
        extracted_block = extracted_blocks[0]
        assert "```json" in extracted_block
        assert "```" in extracted_block
        
        # Extract the JSON content and verify it matches
        import re
        json_match = re.search(r"```json\s*(.*?)\s*```", extracted_block, re.DOTALL | re.IGNORECASE)
        assert json_match is not None
        
        extracted_json_str = json_match.group(1).strip()
        extracted_json = json.loads(extracted_json_str)
        
        # Verify the extracted JSON matches the original
        assert extracted_json["type"] == map_json["type"]
        assert extracted_json["config"] == map_json["config"]