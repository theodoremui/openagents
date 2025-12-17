"""
Tests for ResultSynthesizer

Tests response synthesis and merging.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from asdrp.orchestration.smartrouter.result_synthesizer import ResultSynthesizer
from asdrp.orchestration.smartrouter.interfaces import (
    AgentResponse,
    SynthesizedResult,
)
from asdrp.orchestration.smartrouter.config_loader import ModelConfig
from asdrp.orchestration.smartrouter.exceptions import SynthesisException


class TestResultSynthesizer:
    """Test ResultSynthesizer class."""

    @pytest.fixture
    def model_config(self):
        """Create a test model config."""
        return ModelConfig(
            name="gpt-4.1-mini",
            temperature=0.3,
            max_tokens=2000
        )

    @pytest.fixture
    def synthesizer(self, model_config):
        """Create a ResultSynthesizer instance."""
        return ResultSynthesizer(model_config=model_config)

    def test_init(self, model_config):
        """Test ResultSynthesizer initialization."""
        synthesizer = ResultSynthesizer(model_config=model_config)
        assert synthesizer.model_config == model_config
        assert synthesizer._llm_client is None

    def test_init_with_custom_client(self, model_config):
        """Test initialization with custom LLM client."""
        mock_client = MagicMock()
        synthesizer = ResultSynthesizer(
            model_config=model_config,
            llm_client=mock_client
        )
        assert synthesizer._llm_client == mock_client

    @pytest.mark.asyncio
    async def test_synthesize_single_response(self, synthesizer):
        """Test synthesizing single response."""
        responses = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="The address is 123 Main St",
                success=True,
                metadata={}
            )
        }
        
        # Mock LLM to return simple synthesis
        mock_client = AsyncMock()
        mock_client.generate.return_value = '{"answer": "The address is 123 Main St", "conflicts_resolved": [], "confidence": 0.9, "notes": ""}'
        
        synthesizer._llm_client = mock_client
        
        result = await synthesizer.synthesize(
            responses,
            "What is the address?"
        )
        
        assert isinstance(result, SynthesizedResult)
        assert result.answer == "The address is 123 Main St"
        # Single response gets confidence 1.0, not from JSON
        assert result.confidence == 1.0
        assert result.sources == ["geo"]

    @pytest.mark.asyncio
    async def test_synthesize_multiple_responses(self, synthesizer):
        """Test synthesizing multiple responses."""
        responses = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Address: 123 Main St",
                success=True,
                metadata={}
            ),
            "sq2": AgentResponse(
                subquery_id="sq2",
                agent_id="finance",
                content="Stock price: $150",
                success=True,
                metadata={}
            )
        }
        
        mock_client = AsyncMock()
        mock_client.generate.return_value = '{"answer": "Address: 123 Main St. Stock price: $150", "conflicts_resolved": [], "confidence": 0.85, "notes": ""}'
        
        synthesizer._llm_client = mock_client
        
        result = await synthesizer.synthesize(
            responses,
            "What is the address and stock price?"
        )
        
        assert isinstance(result, SynthesizedResult)
        assert "123 Main St" in result.answer
        assert "$150" in result.answer

    @pytest.mark.asyncio
    async def test_synthesize_empty_responses(self, synthesizer):
        """Test synthesizing with empty responses."""
        with pytest.raises(SynthesisException):
            await synthesizer.synthesize({}, "Test query")

    @pytest.mark.asyncio
    async def test_parse_synthesis_result_valid_json(self, synthesizer):
        """Test parsing valid JSON synthesis result."""
        llm_response = '{"answer": "Synthesized answer", "conflicts_resolved": ["date conflict"], "confidence": 0.8, "notes": "Some notes"}'
        responses = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Response 1",
                success=True,
                metadata={}
            )
        }
        result = synthesizer._parse_synthesis(llm_response, responses)
        
        assert result.answer == "Synthesized answer"
        assert result.conflicts_resolved == ["date conflict"]
        assert result.confidence == 0.8
        assert result.metadata.get("notes") == "Some notes"

    @pytest.mark.asyncio
    async def test_parse_synthesis_result_json_in_code_block(self, synthesizer):
        """Test parsing JSON wrapped in markdown code block."""
        llm_response = '```json\n{"answer": "Answer", "conflicts_resolved": [], "confidence": 0.9, "notes": ""}\n```'
        responses = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Response",
                success=True,
                metadata={}
            )
        }
        result = synthesizer._parse_synthesis(llm_response, responses)
        
        assert result.answer == "Answer"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_parse_synthesis_result_invalid_json(self, synthesizer):
        """Test parsing invalid JSON uses fallback."""
        llm_response = "not valid json"
        responses = {
            "sq1": AgentResponse(
                subquery_id="sq1",
                agent_id="geo",
                content="Response",
                success=True,
                metadata={}
            )
        }
        # _parse_synthesis returns fallback result on invalid JSON, doesn't raise
        result = synthesizer._parse_synthesis(llm_response, responses)
        
        assert isinstance(result, SynthesizedResult)
        assert result.answer == llm_response  # Uses raw response as answer
        assert result.confidence == 0.7  # Lower confidence for unparsed

