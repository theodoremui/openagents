"""
Enhanced JSON Block Preservation Tests.

Tests the enhanced JSON block preservation functionality implemented in task 2:
- Multiple regex patterns for robust detection
- Post-synthesis validation and restoration
- Enhanced auto-injection fallbacks
"""

import pytest
import json
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
            "test_expert": ExpertGroupConfig(
                agents=["expert_0", "expert_1"],
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


class TestEnhancedJSONBlockPreservation:
    """Test enhanced JSON block preservation functionality."""

    def test_multiple_regex_patterns_detection(self, mixer):
        """Test that multiple regex patterns can detect JSON blocks in various formats."""
        
        # Test different JSON block formats
        test_cases = [
            # Standard format
            "Here's a map:\n\n```json\n{\"type\": \"interactive_map\", \"config\": {\"map_type\": \"places\"}}\n```",
            # Case-sensitive JSON
            "Here's a map:\n\n```JSON\n{\"type\": \"interactive_map\", \"config\": {\"map_type\": \"places\"}}\n```",
            # Loose spacing
            "Here's a map:\n\n``` json\n{\"type\": \"interactive_map\", \"config\": {\"map_type\": \"places\"}}\n```",
        ]
        
        for test_case in test_cases:
            blocks = mixer._extract_interactive_json_blocks(test_case)
            assert len(blocks) == 1, f"Failed to detect JSON block in: {test_case}"
            assert "interactive_map" in blocks[0]

    def test_has_interactive_map_detection(self, mixer):
        """Test the enhanced _has_interactive_map method."""
        
        # Test cases with maps
        with_map_cases = [
            "```json\n{\"type\": \"interactive_map\", \"config\": {}}\n```",
            "```JSON\n{\"type\": \"interactive_map\", \"config\": {}}\n```",
            "``` json\n{\"type\": \"interactive_map\", \"config\": {}}\n```",
        ]
        
        for case in with_map_cases:
            assert mixer._has_interactive_map(case), f"Failed to detect map in: {case}"
        
        # Test cases without maps
        without_map_cases = [
            "Just some text",
            "```json\n{\"type\": \"other\", \"config\": {}}\n```",
            "```python\nprint('hello')\n```",
            "",
            None
        ]
        
        for case in without_map_cases:
            assert not mixer._has_interactive_map(case), f"False positive for: {case}"

    @pytest.mark.asyncio
    async def test_post_synthesis_validation_restores_missing_blocks(self, mixer):
        """Test that post-synthesis validation restores missing JSON blocks."""
        
        # Create expert results with JSON blocks
        expert_results = [
            ExpertResult(
                expert_id="map_expert",
                output="Here's your map:\n\n```json\n{\"type\": \"interactive_map\", \"config\": {\"map_type\": \"places\", \"markers\": []}}\n```",
                success=True,
                latency_ms=100.0
            ),
            ExpertResult(
                expert_id="text_expert", 
                output="Here are some restaurants in the area.",
                success=True,
                latency_ms=150.0
            )
        ]
        
        # Mock OpenAI to return synthesis without JSON blocks (simulating LLM dropping them)
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = Mock()
            
            # LLM synthesis that drops the JSON block
            synthesized_text = "Here are some great restaurants in the area with directions."
            
            mock_response = Mock()
            mock_message = Mock()
            mock_message.content = synthesized_text
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 100
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Execute mixing
            result = await mixer.mix(expert_results, ["map_expert", "text_expert"], "show restaurants on map")
            
            # Verify that the JSON block was restored despite LLM dropping it
            assert isinstance(result, MixedResult)
            assert result.content is not None
            assert "```json" in result.content
            assert "interactive_map" in result.content
            assert "places" in result.content

    @pytest.mark.asyncio
    async def test_validation_preserves_equivalent_blocks(self, mixer):
        """Test that validation recognizes equivalent JSON blocks and doesn't duplicate."""
        
        original_json = {
            "type": "interactive_map",
            "config": {
                "map_type": "places",
                "markers": [{"lat": 37.7749, "lng": -122.4194, "title": "San Francisco"}]
            }
        }
        
        # Expert result with original JSON
        expert_results = [
            ExpertResult(
                expert_id="map_expert",
                output=f"```json\n{json.dumps(original_json, indent=2)}\n```",
                success=True,
                latency_ms=100.0
            )
        ]
        
        # Mock OpenAI to return synthesis with equivalent but reformatted JSON
        equivalent_json = {
            "type": "interactive_map", 
            "config": {
                "map_type": "places",
                "markers": [{"lat": 37.7749, "lng": -122.4194, "title": "San Francisco"}]
            }
        }
        
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = Mock()
            
            synthesized_text = f"Here's your map:\n\n```json\n{json.dumps(equivalent_json)}\n```"
            
            mock_response = Mock()
            mock_message = Mock()
            mock_message.content = synthesized_text
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 100
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Execute mixing
            result = await mixer.mix(expert_results, ["map_expert"], "show map")
            
            # Should not duplicate - equivalent blocks should be recognized
            json_block_count = result.content.count("```json")
            assert json_block_count == 1, f"Expected 1 JSON block, found {json_block_count}"

    def test_json_block_extraction_with_malformed_json(self, mixer):
        """Test that extraction handles malformed JSON gracefully."""
        
        test_cases = [
            # Valid JSON
            "```json\n{\"type\": \"interactive_map\", \"config\": {}}\n```",
            # Invalid JSON - should be ignored
            "```json\n{\"type\": \"interactive_map\", \"config\": {}\n```",  # Missing closing brace
            # Not interactive map - should be ignored
            "```json\n{\"type\": \"other\", \"config\": {}}\n```",
            # Empty JSON block - should be ignored
            "```json\n\n```",
        ]
        
        text_with_mixed_blocks = "\n\n".join(test_cases)
        blocks = mixer._extract_interactive_json_blocks(text_with_mixed_blocks)
        
        # Should only extract the valid interactive map JSON
        assert len(blocks) == 1
        assert "interactive_map" in blocks[0]

    @pytest.mark.asyncio
    async def test_enhanced_auto_injection_with_has_interactive_map(self, mixer):
        """Test that enhanced auto-injection uses the robust _has_interactive_map check."""
        
        # Create expert results without JSON blocks
        expert_results = [
            ExpertResult(
                expert_id="yelp_expert",
                output="Great restaurants: 1. Tony's Pizza - 123 Main St, San Francisco, CA",
                success=True,
                latency_ms=100.0
            )
        ]
        
        # Mock the geocoding auto-injection to return a map
        async def mock_geocoding_injection(synthesized, query, expert_results):
            if "map" in query.lower():
                return synthesized + "\n\n```json\n{\"type\": \"interactive_map\", \"config\": {\"map_type\": \"places\"}}\n```"
            return synthesized
        
        with patch.object(mixer, '_auto_inject_map_via_geocoding', side_effect=mock_geocoding_injection):
            with patch.object(mixer, '_auto_inject_missing_maps', return_value="No route found"):
                # Execute mixing with map query
                result = await mixer.mix(expert_results, ["yelp_expert"], "show restaurants on map")
                
                # Should have auto-injected a map
                assert isinstance(result, MixedResult)
                assert mixer._has_interactive_map(result.content)
                assert "interactive_map" in result.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])