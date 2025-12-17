"""
ResultSynthesizer - Response Synthesis and Merging

Merges multiple agent responses into a coherent final answer.
Resolves conflicts and ensures clarity and completeness.

Design Principles:
-----------------
- Single Responsibility: Only responsible for response synthesis
- Dependency Injection: LLM client and config injected
- Robustness: Handles conflicting/incomplete responses
- Clarity: Ensures final answer is coherent and well-formatted

Responsibilities:
----------------
- Merge multiple agent responses into single answer
- Resolve conflicts between responses
- Ensure answer addresses original query
- Maintain source attribution
- Format answer clearly (markdown)
"""

from typing import Dict, List, Optional, Any
import json
import logging

from agents import ModelSettings

from asdrp.orchestration.smartrouter.interfaces import (
    IResultSynthesizer,
    AgentResponse,
    SynthesizedResult,
)
from asdrp.orchestration.smartrouter.exceptions import SynthesisException
from asdrp.orchestration.smartrouter.config_loader import ModelConfig

logger = logging.getLogger(__name__)


class ResultSynthesizer(IResultSynthesizer):
    """
    Implementation of response synthesis using LLM.

    Uses a language model to intelligently merge multiple agent responses
    into a single, coherent answer that addresses the user's original query.

    The synthesizer handles:
    - Combining complementary information
    - Resolving conflicting information
    - Maintaining source attribution
    - Formatting for readability

    Usage:
    ------
    >>> synthesizer = ResultSynthesizer(model_config=ModelConfig(...))
    >>> responses = {
    ...     "sq1": AgentResponse(...),
    ...     "sq2": AgentResponse(...)
    ... }
    >>> result = await synthesizer.synthesize(
    ...     responses,
    ...     "What's the weather in Paris and stock price of Air France?"
    ... )
    >>> print(result.answer)
    """

    # System prompt for response synthesis
    SYNTHESIS_PROMPT = """You are a response synthesis expert. Merge multiple agent responses into one coherent answer.

Your task:
1. Read the original user query
2. Review responses from multiple specialist agents
3. Synthesize a comprehensive, coherent answer that:
   - Addresses the user's original question directly
   - Combines information from all responses
   - Resolves any conflicts (note discrepancies)
   - Maintains factual accuracy
   - Uses clear, structured markdown format
   - Cites sources when helpful

Guidelines:
- If responses conflict, note the discrepancy clearly
- If information is incomplete, acknowledge what's missing
- Keep the answer focused on the user's query
- Use markdown formatting (headers, lists, bold)
- Be concise but complete

Original Query: {query}

Agent Responses:
{responses}

Provide your synthesized answer in this JSON format:
{{
  "answer": "Your synthesized answer in markdown",
  "conflicts_resolved": ["Description of any conflicts resolved"],
  "confidence": 0.0-1.0,
  "notes": "Any important notes about the synthesis"
}}
"""

    def __init__(
        self,
        model_config: ModelConfig,
        llm_client: Optional[Any] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize ResultSynthesizer.

        Args:
            model_config: Configuration for the LLM model
            llm_client: Optional custom LLM client (for testing/DI)
            session_id: Optional session ID for conversation memory
        """
        self.model_config = model_config
        self._llm_client = llm_client
        self.session_id = session_id

        # Create session ONCE during initialization (OpenAI best practice)
        self._session = None
        if session_id:
            from agents import SQLiteSession
            self._session = SQLiteSession(
                session_id=f"{session_id}_synthesizer",
                db_path="data/sessions/smartrouter.db"  # Persistent file-based storage
            )
            logger.info(f"ResultSynthesizer: Created persistent session {session_id}_synthesizer")

    async def synthesize(
        self,
        responses: Dict[str, AgentResponse],
        original_query: str
    ) -> SynthesizedResult:
        """
        Synthesize multiple responses into final answer.

        Uses LLM to intelligently merge agent responses into a coherent
        answer that addresses the original query.

        Args:
            responses: Dictionary of subquery_id -> AgentResponse
            original_query: The original user query for context

        Returns:
            SynthesizedResult with merged answer

        Raises:
            SynthesisException: If synthesis fails

        Examples:
        ---------
        >>> result = await synthesizer.synthesize(responses, original_query)
        >>> print(result.answer)
        ## Weather in Paris
        ...
        ## Air France Stock
        ...
        >>> print(result.confidence)
        0.9
        """
        try:
            logger.debug(
                f"Synthesizing {len(responses)} responses for query: "
                f"{original_query[:100]}..."
            )

            # Handle edge cases
            if not responses:
                raise SynthesisException(
                    "Cannot synthesize with zero responses",
                    context={"query": original_query}
                )

            # Single response - no synthesis needed
            if len(responses) == 1:
                return self._handle_single_response(responses, original_query)

            # Multiple responses - use LLM synthesis
            synthesis_result = await self._call_synthesis_llm(responses, original_query)

            # Parse synthesis result
            result = self._parse_synthesis(synthesis_result, responses)

            logger.info(
                f"Synthesis complete: confidence={result.confidence:.2f}, "
                f"conflicts_resolved={len(result.conflicts_resolved)}"
            )

            return result

        except SynthesisException:
            raise
        except Exception as e:
            raise SynthesisException(
                f"Response synthesis failed: {str(e)}",
                context={"query": original_query, "response_count": len(responses)},
                original_exception=e
            ) from e

    def _handle_single_response(
        self,
        responses: Dict[str, AgentResponse],
        original_query: str
    ) -> SynthesizedResult:
        """
        Handle single response (no synthesis needed).

        Args:
            responses: Dictionary with single response
            original_query: Original query

        Returns:
            SynthesizedResult wrapping the single response
        """
        response = list(responses.values())[0]

        logger.info("Single response, no synthesis needed")

        return SynthesizedResult(
            answer=response.content,
            sources=[response.agent_id],
            confidence=1.0,
            conflicts_resolved=[],
            metadata={
                "single_response": True,
                "subquery_id": response.subquery_id,
                "agent_id": response.agent_id,
            }
        )

    async def _call_synthesis_llm(
        self,
        responses: Dict[str, AgentResponse],
        original_query: str
    ) -> str:
        """
        Call LLM for response synthesis.

        Args:
            responses: Agent responses to synthesize
            original_query: Original user query

        Returns:
            LLM response string (expected to be JSON)

        Raises:
            SynthesisException: If LLM call fails
        """
        try:
            # Format responses for prompt
            formatted_responses = self._format_responses(responses)

            # Build prompt
            prompt = self.SYNTHESIS_PROMPT.format(
                query=original_query,
                responses=formatted_responses
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
                name="ResultSynthesizer",
                instructions=self.SYNTHESIS_PROMPT,
                model=self.model_config.name,
                model_settings=ModelSettings(
                    temperature=self.model_config.temperature,
                    max_tokens=self.model_config.max_tokens,
                ),
            )

            # Use the persistent session created in __init__
            result = await Runner.run(
                agent,
                input=f"Original Query: {original_query}\n\nResponses:\n{formatted_responses}",
                session=self._session
            )
            return str(result.final_output)

        except Exception as e:
            raise SynthesisException(
                f"LLM synthesis call failed: {str(e)}",
                context={"query": original_query, "model": self.model_config.name},
                original_exception=e
            ) from e

    def _format_responses(self, responses: Dict[str, AgentResponse]) -> str:
        """
        Format agent responses for LLM prompt.

        Args:
            responses: Dictionary of agent responses

        Returns:
            Formatted string with all responses
        """
        formatted = []
        for sq_id, response in responses.items():
            formatted.append(
                f"### Response from {response.agent_id} (subquery: {sq_id}):\n"
                f"{response.content}\n"
            )

        return "\n".join(formatted)

    def _parse_synthesis(
        self,
        llm_response: str,
        responses: Dict[str, AgentResponse]
    ) -> SynthesizedResult:
        """
        Parse LLM synthesis response into SynthesizedResult.

        Args:
            llm_response: LLM response (expected JSON)
            responses: Original agent responses

        Returns:
            SynthesizedResult parsed from response

        Raises:
            SynthesisException: If parsing fails
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

            # Extract fields
            answer = data.get("answer", "")
            conflicts = data.get("conflicts_resolved", [])
            confidence = data.get("confidence", 0.8)
            notes = data.get("notes", "")

            # Validate
            if not answer:
                raise SynthesisException(
                    "Synthesized answer is empty",
                    context={"llm_response": llm_response[:200]}
                )

            if not (0.0 <= confidence <= 1.0):
                logger.warning(f"Invalid confidence {confidence}, clamping to [0, 1]")
                confidence = max(0.0, min(1.0, confidence))

            # Extract sources
            sources = list(set(r.agent_id for r in responses.values()))

            return SynthesizedResult(
                answer=answer,
                sources=sources,
                confidence=confidence,
                conflicts_resolved=conflicts if isinstance(conflicts, list) else [],
                metadata={
                    "notes": notes,
                    "response_count": len(responses),
                    "llm_response": llm_response,
                }
            )

        except json.JSONDecodeError:
            # Fallback: treat entire response as answer
            logger.warning(
                "Failed to parse synthesis as JSON, using raw response as answer"
            )
            return SynthesizedResult(
                answer=llm_response,
                sources=list(set(r.agent_id for r in responses.values())),
                confidence=0.7,  # Lower confidence for unparsed response
                conflicts_resolved=[],
                metadata={
                    "parse_fallback": True,
                    "response_count": len(responses),
                }
            )
        except Exception as e:
            raise SynthesisException(
                f"Failed to parse synthesis: {str(e)}",
                context={"llm_response": llm_response[:200]},
                original_exception=e
            ) from e
