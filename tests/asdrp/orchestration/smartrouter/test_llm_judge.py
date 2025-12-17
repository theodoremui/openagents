"""
Tests for LLMJudge

Tests answer quality evaluation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from asdrp.orchestration.smartrouter.llm_judge import LLMJudge
from asdrp.orchestration.smartrouter.interfaces import EvaluationResult
from asdrp.orchestration.smartrouter.config_loader import ModelConfig, EvaluationConfig
from asdrp.orchestration.smartrouter.exceptions import EvaluationException


class TestLLMJudge:
    """Test LLMJudge class."""

    @pytest.fixture
    def model_config(self):
        """Create a test model config."""
        return ModelConfig(
            name="gpt-4.1-mini",
            temperature=0.01,
            max_tokens=500
        )

    @pytest.fixture
    def eval_config(self):
        """Create evaluation config."""
        return EvaluationConfig(
            fallback_message="Not enough information",
            quality_threshold=0.7,
            criteria=["completeness", "accuracy", "clarity"]
        )

    @pytest.fixture
    def judge(self, model_config, eval_config):
        """Create LLMJudge instance."""
        return LLMJudge(
            model_config=model_config,
            eval_config=eval_config
        )

    def test_init(self, model_config, eval_config):
        """Test LLMJudge initialization."""
        judge = LLMJudge(
            model_config=model_config,
            eval_config=eval_config
        )
        assert judge.model_config == model_config
        assert judge.eval_config == eval_config
        assert judge._llm_client is None

    def test_init_with_custom_client(self, model_config, eval_config):
        """Test initialization with custom LLM client."""
        mock_client = MagicMock()
        judge = LLMJudge(
            model_config=model_config,
            eval_config=eval_config,
            llm_client=mock_client
        )
        assert judge._llm_client == mock_client

    @pytest.mark.asyncio
    async def test_evaluate_high_quality_answer(self, judge):
        """Test evaluating high quality answer."""
        mock_client = AsyncMock()
        mock_client.generate.return_value = '''{
            "completeness_score": 0.9,
            "accuracy_score": 0.95,
            "clarity_score": 0.9,
            "faithfulness_score": 0.85,
            "relevance_score": 0.9,
            "actionability_score": 0.8,
            "overall_score": 0.88,
            "issues": [],
            "reasoning": "High quality answer"
        }'''
        
        judge._llm_client = mock_client
        
        result = await judge.evaluate(
            answer="The weather in Paris is sunny, 22°C",
            original_query="What's the weather in Paris?"
        )
        
        assert isinstance(result, EvaluationResult)
        assert result.is_high_quality is True
        assert result.completeness_score == 0.9
        assert result.accuracy_score == 0.95
        assert result.clarity_score == 0.9

    @pytest.mark.asyncio
    async def test_evaluate_low_quality_answer(self, judge):
        """Test evaluating low quality answer."""
        mock_client = AsyncMock()
        mock_client.generate.return_value = '''{
            "completeness_score": 0.3,
            "accuracy_score": 0.4,
            "clarity_score": 0.5,
            "faithfulness_score": 0.3,
            "relevance_score": 0.4,
            "actionability_score": 0.3,
            "overall_score": 0.35,
            "issues": ["Incomplete", "Unclear"],
            "reasoning": "Low quality answer"
        }'''
        
        judge._llm_client = mock_client
        
        result = await judge.evaluate(
            answer="Weather is okay",
            original_query="What's the weather in Paris?"
        )
        
        assert isinstance(result, EvaluationResult)
        assert result.is_high_quality is False
        assert result.completeness_score == 0.3
        assert result.accuracy_score == 0.4
        assert result.clarity_score == 0.5
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_criteria(self, judge):
        """Test evaluation with custom criteria."""
        mock_client = AsyncMock()
        mock_client.generate.return_value = '''{
            "completeness_score": 0.8,
            "accuracy_score": 0.9,
            "clarity_score": 0.85,
            "faithfulness_score": 0.8,
            "relevance_score": 0.9,
            "actionability_score": 0.8,
            "overall_score": 0.84,
            "issues": [],
            "reasoning": "Good answer"
        }'''
        
        judge._llm_client = mock_client
        
        result = await judge.evaluate(
            answer="Test answer",
            original_query="Test query",
            criteria=["completeness", "accuracy"]
        )
        
        assert isinstance(result, EvaluationResult)
        mock_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_evaluation_result_valid_json(self, judge):
        """Test parsing valid JSON evaluation result."""
        llm_response = '''{
            "completeness_score": 0.9,
            "accuracy_score": 0.8,
            "clarity_score": 0.85,
            "faithfulness_score": 0.9,
            "relevance_score": 0.85,
            "actionability_score": 0.8,
            "overall_score": 0.85,
            "issues": ["Minor issue"],
            "reasoning": "Good answer"
        }'''
        
        result = judge._parse_evaluation(
            llm_response,
            "Test answer",
            "Test query"
        )
        
        assert isinstance(result, EvaluationResult)
        assert result.completeness_score == 0.9
        assert result.accuracy_score == 0.8
        assert result.clarity_score == 0.85
        assert "Minor issue" in result.issues

    @pytest.mark.asyncio
    async def test_parse_evaluation_result_invalid_json(self, judge):
        """Test parsing invalid JSON raises exception."""
        llm_response = "not valid json"
        
        # _parse_evaluation returns fallback result on invalid JSON, doesn't raise
        result = judge._parse_evaluation(
            llm_response,
            "Test answer",
            "Test query"
        )
        assert isinstance(result, EvaluationResult)
        assert result.should_fallback is True

    @pytest.mark.asyncio
    async def test_evaluate_llm_failure(self, judge):
        """Test evaluation when LLM fails."""
        mock_client = AsyncMock()
        mock_client.generate.side_effect = Exception("LLM error")
        
        judge._llm_client = mock_client
        
        with pytest.raises(EvaluationException):
            await judge.evaluate(
                answer="Test answer",
                original_query="Test query"
            )

