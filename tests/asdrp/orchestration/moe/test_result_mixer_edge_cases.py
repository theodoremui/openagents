"""
Comprehensive Edge Case Tests for MoE Result Mixer.

Tests defensive null handling following SOLID principles:
- Single Responsibility: Each test validates one edge case
- Fail-Safe Design: System degrades gracefully, never crashes
- Defensive Programming: Validates all inputs and handles all None cases
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

from asdrp.orchestration.moe.result_mixer import WeightedMixer, MixedResult
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.config_loader import MoEConfig, ModelConfig, ExpertGroupConfig, MoECacheConfig
from asdrp.orchestration.moe.exceptions import MixingException


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
                agents=["one", "test"],
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
            "fallback_agent": "one",
            "fallback_message": "I apologize, but I encountered an issue."
        },
        tracing={"enabled": False, "storage": {"backend": "none"}, "exporters": []}
    )


@pytest.fixture
def mixer(mock_moe_config):
    """Create mixer instance for testing."""
    return WeightedMixer(mock_moe_config)


class TestNullSafetyDefenses:
    """Test defensive null handling in result mixer."""

    @pytest.mark.asyncio
    async def test_empty_choices_list_handling(self, mixer, mock_moe_config):
        """Test graceful handling when OpenAI returns empty choices list."""
        expert_results = [
            ExpertResult(
                expert_id="one",
                output="Test output",
                success=True,
                latency_ms=100.0
            )
        ]

        # Mock OpenAI to return empty choices list
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.choices = []  # Empty list - the bug trigger
            mock_response.usage = None
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            # Should not crash, should return fallback content
            result = await mixer.mix(expert_results, ["one"], "test query")

            assert isinstance(result, MixedResult)
            assert result.content  # Should have fallback content
            assert "Test output" in result.content or "I'm having trouble" in result.content

    @pytest.mark.asyncio
    async def test_none_choices_handling(self, mixer, mock_moe_config):
        """Test graceful handling when OpenAI returns None for choices."""
        expert_results = [
            ExpertResult(
                expert_id="one",
                output="Test output",
                success=True,
                latency_ms=100.0
            )
        ]

        # Mock OpenAI to return None choices
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.choices = None  # None - another potential bug
            mock_response.usage = None
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            # Should not crash, should return fallback content
            result = await mixer.mix(expert_results, ["one"], "test query")

            assert isinstance(result, MixedResult)
            assert result.content
            assert "Test output" in result.content or "I'm having trouble" in result.content

    @pytest.mark.asyncio
    async def test_none_message_content_handling(self, mixer, mock_moe_config):
        """Test graceful handling when message.content is None."""
        expert_results = [
            ExpertResult(
                expert_id="one",
                output="Test output",
                success=True,
                latency_ms=100.0
            )
        ]

        # Mock OpenAI to return None message content
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_message = Mock()
            mock_message.content = None  # None content
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_response.usage = None
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            # Should not crash, should return fallback content
            result = await mixer.mix(expert_results, ["one"], "test query")

            assert isinstance(result, MixedResult)
            assert result.content
            assert "Test output" in result.content or "I'm having trouble" in result.content

    @pytest.mark.asyncio
    async def test_empty_string_message_content_handling(self, mixer, mock_moe_config):
        """Test graceful handling when message.content is empty string."""
        expert_results = [
            ExpertResult(
                expert_id="one",
                output="Test output",
                success=True,
                latency_ms=100.0
            )
        ]

        # Mock OpenAI to return empty string content
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_message = Mock()
            mock_message.content = "   "  # Whitespace only
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_response.usage = None
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            # Should not crash, should return fallback content
            result = await mixer.mix(expert_results, ["one"], "test query")

            assert isinstance(result, MixedResult)
            assert result.content
            assert "Test output" in result.content or "I'm having trouble" in result.content

    @pytest.mark.asyncio
    async def test_no_successful_results(self, mixer):
        """Test handling when all expert results failed."""
        expert_results = [
            ExpertResult(
                expert_id="one",
                output="",
                success=False,
                latency_ms=100.0,
                error="Failed"
            ),
            ExpertResult(
                expert_id="two",
                output="",
                success=False,
                latency_ms=100.0,
                error="Failed"
            )
        ]

        result = await mixer.mix(expert_results, ["one", "two"], "test query")

        assert isinstance(result, MixedResult)
        assert result.content
        assert "don't have enough information" in result.content or "apologize" in result.content
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_single_successful_result_no_synthesis(self, mixer):
        """Test that single expert bypasses LLM synthesis."""
        expert_results = [
            ExpertResult(
                expert_id="one",
                output="Single expert output",
                success=True,
                latency_ms=100.0
            )
        ]

        # Should not call OpenAI for single expert
        result = await mixer.mix(expert_results, ["one"], "test query")

        assert isinstance(result, MixedResult)
        assert result.content == "Single expert output"
        assert result.weights == {"one": 1.0}
        assert result.quality_score > 0.0

    @pytest.mark.asyncio
    async def test_empty_expert_results_list(self, mixer):
        """Test handling when expert_results is empty list."""
        result = await mixer.mix([], [], "test query")

        assert isinstance(result, MixedResult)
        assert result.content
        assert "don't have enough information" in result.content
        assert result.weights == {}


class TestOrchestratorBuildResultDefenses:
    """Test defensive null handling in orchestrator._build_result."""

    def test_none_final_result_handling(self):
        """Test _build_result handles None final_result gracefully."""
        from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoETrace

        # Create minimal orchestrator (we're just testing _build_result method)
        orchestrator = Mock(spec=MoEOrchestrator)
        orchestrator._generate_request_id = lambda: "test-123"

        # Use the actual _build_result method
        from asdrp.orchestration.moe.orchestrator import MoEOrchestrator as RealOrchestrator
        import time

        trace = MoETrace(request_id="test-123", query="test")
        result = RealOrchestrator._build_result(
            orchestrator,
            final_result=None,  # None final_result
            expert_ids=["one"],
            expert_results=[],
            start_time=time.time(),
            request_id="test-123",
            trace=trace
        )

        # Should not crash, should have error message
        assert result.response
        assert "apologize" in result.response.lower()

    def test_final_result_missing_content_attribute(self):
        """Test _build_result handles missing content attribute."""
        from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoETrace
        import time

        orchestrator = Mock(spec=MoEOrchestrator)
        trace = MoETrace(request_id="test-123", query="test")

        # Create object without content attribute
        bad_result = Mock()
        del bad_result.content  # Remove content attribute

        result = MoEOrchestrator._build_result(
            orchestrator,
            final_result=bad_result,
            expert_ids=["one"],
            expert_results=[],
            start_time=time.time(),
            request_id="test-123",
            trace=trace
        )

        # Should not crash, should have error message
        assert result.response
        assert "apologize" in result.response.lower()

    def test_final_result_none_content_value(self):
        """Test _build_result handles None content value."""
        from asdrp.orchestration.moe.orchestrator import MoEOrchestrator, MoETrace
        import time

        orchestrator = Mock(spec=MoEOrchestrator)
        trace = MoETrace(request_id="test-123", query="test")

        # Create object with None content
        bad_result = Mock()
        bad_result.content = None

        result = MoEOrchestrator._build_result(
            orchestrator,
            final_result=bad_result,
            expert_ids=["one"],
            expert_results=[],
            start_time=time.time(),
            request_id="test-123",
            trace=trace
        )

        # Should not crash, should have error message
        assert result.response
        assert "apologize" in result.response.lower()


if __name__ == "__main__":
    # Run with: pytest tests/asdrp/orchestration/moe/test_result_mixer_edge_cases.py -v
    pytest.main([__file__, "-v"])
