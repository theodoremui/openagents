"""
LLMJudge - Answer Quality Evaluation

Evaluates final answer quality using LLM-based judging.
Determines if answer meets quality thresholds or should trigger fallback.

Design Principles:
-----------------
- Single Responsibility: Only responsible for answer evaluation
- Dependency Injection: LLM client and config injected
- Objectivity: Uses clear evaluation criteria
- Robustness: Handles malformed responses gracefully

Responsibilities:
----------------
- Evaluate answer completeness, accuracy, clarity
- Score answer quality (0.0-1.0 per criterion)
- Determine if answer meets quality threshold
- Decide whether to use fallback message
- Identify specific quality issues
"""

from typing import Dict, List, Optional, Any
import json
import logging

from agents import ModelSettings

from asdrp.orchestration.smartrouter.interfaces import (
    IAnswerEvaluator,
    EvaluationResult,
)
from asdrp.orchestration.smartrouter.exceptions import EvaluationException
from asdrp.orchestration.smartrouter.config_loader import ModelConfig, EvaluationConfig

logger = logging.getLogger(__name__)


class LLMJudge(IAnswerEvaluator):
    """
    Implementation of answer evaluation using LLM.

    Uses a language model to objectively evaluate answer quality
    across multiple dimensions (completeness, accuracy, clarity).

    The judge uses structured prompting to generate consistent,
    objective evaluations with clear scoring.

    Usage:
    ------
    >>> judge = LLMJudge(
    ...     model_config=ModelConfig(...),
    ...     eval_config=EvaluationConfig(...)
    ... )
    >>> result = await judge.evaluate(
    ...     answer="Paris has a temperature of...",
    ...     original_query="What's the weather in Paris?",
    ...     criteria=["completeness", "accuracy", "clarity"]
    ... )
    >>> print(result.is_high_quality)
    True
    >>> print(result.completeness_score)
    0.95
    """

    # System prompt for answer evaluation
    EVALUATION_PROMPT = """You are an objective answer quality evaluator. Assess the answer against the criteria.

Evaluation Criteria:
1. **Completeness**: Does the answer fully address the query?
   - 1.0: Fully answers all aspects
   - 0.5: Partially answers
   - 0.0: Doesn't address query

2. **Accuracy**: Is the information factually correct?
   - 1.0: All information appears accurate
   - 0.5: Some uncertain or conflicting information
   - 0.0: Contains clear errors or hallucinations

3. **Clarity**: Is the answer well-formatted and understandable?
   - 1.0: Clear, well-structured, easy to understand
   - 0.5: Somewhat unclear or poorly formatted
   - 0.0: Confusing or incoherent

4. **Faithfulness**: Does the answer stick to provided information?
   - 1.0: Only uses provided information
   - 0.5: Some extrapolation
   - 0.0: Makes unsupported claims

5. **Relevance**: Is the answer relevant to the query?
   - 1.0: Highly relevant
   - 0.5: Somewhat relevant
   - 0.0: Off-topic

6. **Actionability**: Can the user act on this answer?
   - 1.0: Provides actionable information
   - 0.5: Provides some actionable information
   - 0.0: Not actionable

Evaluation Task:
- Original Query: {query}
- Answer to Evaluate: {answer}
- Criteria to Assess: {criteria}

Provide evaluation in this JSON format:
{{
  "completeness_score": 0.0-1.0,
  "accuracy_score": 0.0-1.0,
  "clarity_score": 0.0-1.0,
  "faithfulness_score": 0.0-1.0,
  "relevance_score": 0.0-1.0,
  "actionability_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "issues": ["List any quality issues identified"],
  "reasoning": "Brief explanation of evaluation"
}}
"""

    def __init__(
        self,
        model_config: ModelConfig,
        eval_config: EvaluationConfig,
        llm_client: Optional[Any] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize LLMJudge.

        Args:
            model_config: Configuration for the LLM model
            eval_config: Evaluation configuration (criteria, thresholds)
            llm_client: Optional custom LLM client (for testing/DI)
            session_id: Optional session ID for conversation memory
        """
        self.model_config = model_config
        self.eval_config = eval_config
        self._llm_client = llm_client
        self.session_id = session_id

        # Create session ONCE during initialization (OpenAI best practice)
        self._session = None
        if session_id:
            from agents import SQLiteSession
            self._session = SQLiteSession(
                session_id=f"{session_id}_judge",
                db_path="data/sessions/smartrouter.db"  # Persistent file-based storage
            )
            logger.info(f"LLMJudge: Created persistent session {session_id}_judge")

    async def evaluate(
        self,
        answer: str,
        original_query: str,
        criteria: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        Evaluate answer quality using LLM judge.

        Uses structured evaluation prompt to assess answer across
        multiple quality dimensions. Returns detailed scores and
        recommendation on whether to use fallback message.

        Args:
            answer: The synthesized answer to evaluate
            original_query: The original user query
            criteria: Optional list of evaluation criteria
                     (defaults to config criteria)

        Returns:
            EvaluationResult with scores and fallback decision

        Raises:
            EvaluationException: If evaluation fails

        Examples:
        ---------
        >>> result = await judge.evaluate(
        ...     answer="Paris is the capital of France...",
        ...     original_query="Tell me about Paris",
        ...     criteria=["completeness", "accuracy"]
        ... )
        >>> print(result.is_high_quality)
        True
        >>> print(result.should_fallback)
        False
        """
        try:
            logger.debug(f"Evaluating answer for query: {original_query[:100]}...")

            # Validate inputs
            if not answer or not answer.strip():
                logger.warning("Answer is empty, using fallback")
                return self._create_fallback_result(
                    "Answer is empty",
                    original_query
                )

            # Use configured criteria if not specified
            criteria = criteria or self.eval_config.criteria

            # Call LLM for evaluation
            evaluation_result = await self._call_evaluation_llm(
                answer,
                original_query,
                criteria
            )

            # Parse evaluation result
            result = self._parse_evaluation(evaluation_result, answer, original_query)

            # Determine if answer meets quality threshold
            is_high_quality = result.completeness_score >= self.eval_config.quality_threshold \
                and result.accuracy_score >= self.eval_config.quality_threshold \
                and result.clarity_score >= self.eval_config.quality_threshold

            # Update result
            result.is_high_quality = is_high_quality
            result.should_fallback = not is_high_quality

            logger.info(
                f"Evaluation complete: is_high_quality={is_high_quality}, "
                f"scores=[C:{result.completeness_score:.2f}, "
                f"A:{result.accuracy_score:.2f}, "
                f"Cl:{result.clarity_score:.2f}]"
            )

            return result

        except EvaluationException:
            raise
        except Exception as e:
            # On evaluation failure, be conservative and use fallback
            logger.error(f"Evaluation failed: {str(e)}", exc_info=True)
            return self._create_fallback_result(
                f"Evaluation error: {str(e)}",
                original_query
            )

    async def _call_evaluation_llm(
        self,
        answer: str,
        original_query: str,
        criteria: List[str]
    ) -> str:
        """
        Call LLM for answer evaluation.

        Args:
            answer: Answer to evaluate
            original_query: Original user query
            criteria: Evaluation criteria

        Returns:
            LLM response string (expected to be JSON)

        Raises:
            EvaluationException: If LLM call fails
        """
        try:
            # Build prompt
            prompt = self.EVALUATION_PROMPT.format(
                query=original_query,
                answer=answer,
                criteria=", ".join(criteria)
            )

            if self._llm_client:
                # Custom client (for testing)
                return await self._llm_client.generate(
                    prompt=prompt,
                    model=self.model_config.name,
                    temperature=self.model_config.temperature,
                    max_tokens=self.model_config.max_tokens,
                )

            # Use openai-agents SDK
            from agents import Agent, Runner

            agent = Agent(
                name="LLMJudge",
                instructions=self.EVALUATION_PROMPT,
                model=self.model_config.name,
                model_settings=ModelSettings(
                    temperature=self.model_config.temperature,
                    max_tokens=self.model_config.max_tokens,
                ),
            )

            # Use the persistent session created in __init__
            result = await Runner.run(
                agent,
                input=f"Query: {original_query}\n\nAnswer:\n{answer}\n\nCriteria: {', '.join(criteria)}",
                session=self._session
            )
            return str(result.final_output)

        except Exception as e:
            raise EvaluationException(
                f"LLM evaluation call failed: {str(e)}",
                context={"query": original_query, "model": self.model_config.name},
                original_exception=e
            ) from e

    def _parse_evaluation(
        self,
        llm_response: str,
        answer: str,
        original_query: str
    ) -> EvaluationResult:
        """
        Parse LLM evaluation response into EvaluationResult.

        Args:
            llm_response: LLM response (expected JSON)
            answer: The evaluated answer
            original_query: Original query

        Returns:
            EvaluationResult parsed from response

        Raises:
            EvaluationException: If parsing fails
        """
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_str = llm_response.strip()
            if json_str.startswith("```json"):
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif json_str.startswith("```"):
                json_str = json_str.split("```")[1].split("```")[0].strip()

            # Parse JSON
            data = json.loads(json_str)

            # Extract scores (clamp to [0, 1])
            def clamp_score(score: float) -> float:
                return max(0.0, min(1.0, score))

            completeness = clamp_score(data.get("completeness_score", 0.5))
            accuracy = clamp_score(data.get("accuracy_score", 0.5))
            clarity = clamp_score(data.get("clarity_score", 0.5))

            # Extract issues
            issues = data.get("issues", [])
            if not isinstance(issues, list):
                issues = []

            # Extract reasoning
            reasoning = data.get("reasoning", "")

            # Determine if high quality (will be overridden by caller)
            is_high_quality = (
                completeness >= self.eval_config.quality_threshold
                and accuracy >= self.eval_config.quality_threshold
                and clarity >= self.eval_config.quality_threshold
            )

            return EvaluationResult(
                is_high_quality=is_high_quality,
                completeness_score=completeness,
                accuracy_score=accuracy,
                clarity_score=clarity,
                issues=issues,
                should_fallback=not is_high_quality,
                metadata={
                    "reasoning": reasoning,
                    "llm_response": llm_response,
                    "threshold": self.eval_config.quality_threshold,
                }
            )

        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse evaluation as JSON: {str(e)}. "
                f"Using conservative fallback."
            )
            return self._create_fallback_result(
                "Failed to parse evaluation JSON",
                original_query
            )
        except Exception as e:
            raise EvaluationException(
                f"Failed to parse evaluation: {str(e)}",
                context={"llm_response": llm_response[:200]},
                original_exception=e
            ) from e

    def _create_fallback_result(
        self,
        reason: str,
        original_query: str
    ) -> EvaluationResult:
        """
        Create evaluation result indicating fallback should be used.

        Args:
            reason: Reason for fallback
            original_query: Original query

        Returns:
            EvaluationResult with low scores and fallback=True
        """
        return EvaluationResult(
            is_high_quality=False,
            completeness_score=0.0,
            accuracy_score=0.0,
            clarity_score=0.0,
            issues=[reason],
            should_fallback=True,
            metadata={
                "fallback_reason": reason,
                "query": original_query,
            }
        )
