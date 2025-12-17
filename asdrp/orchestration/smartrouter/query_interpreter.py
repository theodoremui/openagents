"""
QueryInterpreter - Query Parsing and Classification

Interprets user queries to extract intent, complexity, and required domains.
Uses LLM to understand query semantics and classify appropriately.

Design Principles:
-----------------
- Single Responsibility: Only responsible for query interpretation
- Dependency Injection: LLM client injected for testability
- Open/Closed: Easy to extend with new classification logic
- Robustness: Handles malformed queries gracefully

Responsibilities:
----------------
- Parse query text and extract semantic meaning
- Classify query complexity (SIMPLE, MODERATE, COMPLEX)
- Identify required knowledge domains
- Determine if synthesis is needed for final answer
"""

from typing import Dict, Any, Optional, List
import json
import logging

from agents import ModelSettings

from asdrp.orchestration.smartrouter.interfaces import (
    IQueryInterpreter,
    QueryIntent,
    QueryComplexity,
)
from asdrp.orchestration.smartrouter.exceptions import SmartRouterException
from asdrp.orchestration.smartrouter.config_loader import ModelConfig

logger = logging.getLogger(__name__)


class QueryInterpreter(IQueryInterpreter):
    """
    Implementation of query interpretation using LLM.

    Uses a language model to analyze user queries and extract:
    - Complexity classification
    - Required knowledge domains
    - Synthesis requirements
    - Additional metadata

    The interpreter uses a structured prompt to ensure consistent
    output format that can be parsed programmatically.

    Usage:
    ------
    >>> from agents import Agent
    >>> interpreter = QueryInterpreter(model_config=ModelConfig(...))
    >>> intent = await interpreter.interpret("What's the weather in Paris and Berlin?")
    >>> print(intent.complexity)
    QueryComplexity.MODERATE
    >>> print(intent.domains)
    ['geography', 'weather']
    """

    # System prompt for query interpretation
    INTERPRETATION_PROMPT = """You are a query analysis expert. Analyze the user query and provide a structured JSON response.

Classify the query complexity:
- SIMPLE: Single, straightforward question requiring one agent
- MODERATE: Multiple questions or domains, straightforward routing
- COMPLEX: Multiple interdependent questions requiring synthesis

Identify domains from this list:
- geography: ONLY for geocoding - converting addresses to/from coordinates, location lookups
- mapping: Maps, driving directions, routes, navigation, distance calculation, place details
- finance: Stocks, markets, financial data
- search: Web search, general knowledge, real-time information, current events, news, weather
- local_business: Restaurants, shops, reviews
- wikipedia: Encyclopedia knowledge, historical facts
- research: Research papers, academic content, deep analysis
- conversation: Social queries, greetings, farewells, gratitude, friendly chat
- social: Casual conversation, small talk, how are you

CRITICAL DISTINCTION - Geography vs Mapping:
- Use "geography" ONLY for: address→coordinates, coordinates→address, "what's the address", "coordinates of"
- Use "mapping" for: driving directions, routes, navigation, "how to get from X to Y", "show me map", "distance between", "directions from X to Y"

Examples:
- "What are the coordinates of San Francisco?" → geography
- "Show me driving directions from San Carlos to San Francisco" → mapping
- "What's the address of 123 Main St?" → geography
- "How far is it from X to Y?" → mapping
- "Get me a map of downtown" → mapping

SPECIAL RULE FOR REAL-TIME INFORMATION QUERIES:
If the query asks for current/real-time information (weather, news, current events, "what's happening", "latest"), classify as:
- complexity: SIMPLE
- domains: ["search"]
- This ensures routing to agents with web search capabilities (one_agent, perplexity_agent)

SPECIAL RULE FOR SOCIAL/CHITCHAT QUERIES:
If the query is PURELY social with NO information request (greetings, farewells, gratitude, small talk like "hi", "hello", "thank you", "how are you", "bye"), classify as:
- complexity: SIMPLE
- domains: ["conversation", "social"]
- requires_synthesis: false

CRITICAL: GREETING WRAPPERS vs PURE CHITCHAT
Many users wrap their actual questions with friendly greetings. You MUST distinguish:

1. PURE CHITCHAT (route to chitchat):
   - "Hello!" → chitchat
   - "How are you?" → chitchat
   - "Thanks!" → chitchat
   - "Hey there, good morning!" → chitchat
   
2. INFORMATIONAL QUERY WITH GREETING WRAPPER (route based on the QUESTION):
   - "Hey, what's the weather?" → search (NOT chitchat - has weather question)
   - "Hi! Where's the nearest restaurant?" → local_business (NOT chitchat - has question)
   - "Hello, can you find stocks for AAPL?" → finance (NOT chitchat - has question)
   - "Hey there, hey, how's the weather in San Francisco right now?" → search (NOT chitchat)

The PRESENCE OF A GREETING DOES NOT MAKE A QUERY CHITCHAT.
If there is ANY substantive question or information request after the greeting, classify based on that question.
Only classify as ["conversation", "social"] if there is NO actual question being asked.

Determine if synthesis is needed: Multiple responses need to be combined into one coherent answer.

Respond ONLY with valid JSON in this format:
{
  "complexity": "SIMPLE|MODERATE|COMPLEX",
  "domains": ["domain1", "domain2"],
  "requires_synthesis": true|false,
  "reasoning": "Brief explanation of classification"
}

User Query: """

    def __init__(
        self,
        model_config: ModelConfig,
        llm_client: Optional[Any] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize QueryInterpreter.

        Args:
            model_config: Configuration for the LLM model
            llm_client: Optional custom LLM client (for testing/DI)
                       If None, uses openai-agents SDK
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
                session_id=f"{session_id}_interpreter",
                db_path="data/sessions/smartrouter.db"  # Persistent file-based storage
            )
            logger.info(f"QueryInterpreter: Created persistent session {session_id}_interpreter")

    async def interpret(self, query: str) -> QueryIntent:
        """
        Interpret and classify a user query.

        Uses LLM to analyze the query and extract structured intent.
        Falls back to simple classification if LLM fails.

        Args:
            query: The user's query text

        Returns:
            QueryIntent with classification and metadata

        Raises:
            SmartRouterException: If interpretation fails critically

        Examples:
        ---------
        >>> intent = await interpreter.interpret("Find tacos in SF")
        >>> assert intent.complexity == QueryComplexity.SIMPLE
        >>> assert "local_business" in intent.domains

        >>> intent = await interpreter.interpret(
        ...     "What's the stock price of AAPL and tell me about Steve Jobs?"
        ... )
        >>> assert intent.complexity == QueryComplexity.MODERATE
        >>> assert intent.requires_synthesis == True
        """
        try:
            logger.debug(f"Interpreting query: {query[:100]}...")

            # Validate input
            if not query or not query.strip():
                raise SmartRouterException(
                    "Query cannot be empty",
                    context={"query": query}
                )

            # Use LLM to interpret query
            interpretation_result = await self._call_interpretation_llm(query)

            # Parse LLM response
            intent = self._parse_interpretation(query, interpretation_result)

            logger.info(
                f"Query interpreted: complexity={intent.complexity.value}, "
                f"domains={intent.domains}, synthesis={intent.requires_synthesis}"
            )

            return intent

        except SmartRouterException:
            raise
        except Exception as e:
            # Fallback to simple heuristic-based interpretation
            logger.warning(
                f"LLM interpretation failed: {str(e)}. Using fallback heuristics.",
                exc_info=True
            )
            return self._fallback_interpretation(query)

    async def _call_interpretation_llm(self, query: str) -> str:
        """
        Call LLM for query interpretation.

        Args:
            query: User query text

        Returns:
            LLM response string (expected to be JSON)

        Raises:
            SmartRouterException: If LLM call fails
        """
        try:
            if self._llm_client:
                # Custom client (for testing)
                return await self._llm_client.generate(
                    prompt=f"{self.INTERPRETATION_PROMPT}\n{query}",
                    model=self.model_config.name,
                    temperature=self.model_config.temperature,
                    max_tokens=self.model_config.max_tokens,
                )

            # Use openai-agents SDK
            from agents import Agent, Runner

            agent = Agent(
                name="QueryInterpreter",
                instructions=self.INTERPRETATION_PROMPT,
                model=self.model_config.name,
                model_settings=ModelSettings(
                    temperature=self.model_config.temperature,
                    max_tokens=self.model_config.max_tokens,
                ),
            )

            # Use the persistent session created in __init__
            result = await Runner.run(agent, input=query, session=self._session)
            return str(result.final_output)

        except Exception as e:
            raise SmartRouterException(
                f"LLM interpretation call failed: {str(e)}",
                context={"query": query, "model": self.model_config.name},
                original_exception=e
            ) from e

    def _parse_interpretation(self, query: str, llm_response: str) -> QueryIntent:
        """
        Parse LLM response into QueryIntent.

        Args:
            query: Original user query
            llm_response: LLM response (expected JSON)

        Returns:
            QueryIntent parsed from response

        Raises:
            SmartRouterException: If parsing fails
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

            # Extract and validate fields
            complexity_str = data.get("complexity", "SIMPLE").upper()
            try:
                complexity = QueryComplexity[complexity_str]
            except KeyError:
                logger.warning(f"Invalid complexity '{complexity_str}', defaulting to SIMPLE")
                complexity = QueryComplexity.SIMPLE

            domains = data.get("domains", ["search"])
            if not isinstance(domains, list):
                domains = ["search"]

            requires_synthesis = data.get("requires_synthesis", False)
            reasoning = data.get("reasoning", "")

            return QueryIntent(
                original_query=query,
                complexity=complexity,
                domains=domains,
                requires_synthesis=requires_synthesis,
                metadata={
                    "reasoning": reasoning,
                    "llm_response": llm_response,
                }
            )

        except json.JSONDecodeError as e:
            raise SmartRouterException(
                f"Failed to parse LLM response as JSON: {str(e)}",
                context={"llm_response": llm_response[:200]},
                original_exception=e
            ) from e
        except Exception as e:
            raise SmartRouterException(
                f"Failed to parse interpretation: {str(e)}",
                context={"llm_response": llm_response[:200]},
                original_exception=e
            ) from e

    def _fallback_interpretation(self, query: str) -> QueryIntent:
        """
        Fallback heuristic-based interpretation.

        Used when LLM interpretation fails. Uses simple rules:
        - Check for chitchat/social patterns first
        - Check for multiple questions (?, multiple sentences)
        - Check for domain keywords
        - Assume simple if unclear

        Args:
            query: User query text

        Returns:
            QueryIntent based on heuristics
        """
        logger.info("Using fallback heuristic interpretation")

        query_lower = query.lower().strip()

        # Check for chitchat/social patterns first (high priority)
        chitchat_patterns = {
            "greeting": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"],
            "farewell": ["bye", "goodbye", "see you", "farewell", "take care", "catch you later"],
            "gratitude": ["thank you", "thanks", "appreciate", "grateful", "thx"],
            "social": ["how are you", "what's up", "how's it going", "how are things", "how do you do"],
            "small_talk": ["nice weather", "have a nice day", "have a great day", "good luck"],
        }

        # Check if query matches chitchat patterns
        is_chitchat = False
        for patterns in chitchat_patterns.values():
            for pattern in patterns:
                if query_lower == pattern or query_lower.startswith(pattern):
                    is_chitchat = True
                    break
            if is_chitchat:
                break

        # If chitchat detected, return immediately with conversation domain
        if is_chitchat:
            logger.info(f"Detected chitchat query: {query[:50]}...")
            return QueryIntent(
                original_query=query,
                complexity=QueryComplexity.SIMPLE,
                domains=["conversation", "social"],
                requires_synthesis=False,
                metadata={
                    "reasoning": "Fallback heuristic interpretation - chitchat detected",
                    "is_chitchat": True,
                }
            )

        # Count questions and sentences
        question_count = query.count("?")
        sentence_count = len([s for s in query.split(".") if s.strip()])

        # Detect domains by keywords
        domains: List[str] = []

        domain_keywords = {
            "search": ["weather", "news", "current", "latest", "today", "now", "happening", "real-time", "live"],
            "geography": ["address", "coordinates", "lat", "lng", "latitude", "longitude", "geocode", "where is", "where are", "location of", "nearest"],
            "mapping": ["map", "direction", "route", "navigation", "drive", "driving", "distance", "how to get", "from", "to"],
            "finance": ["stock", "price", "market", "ticker", "AAPL", "NYSE", "financial"],
            "local_business": ["restaurant", "cafe", "shop", "review", "yelp", "business"],
            "wikipedia": ["wikipedia", "definition", "explain", "history of"],
            "research": ["perplexity", "research", "study", "paper", "academic"],
        }
        
        # Check for location questions first (geography takes precedence over local_business for "where" queries)
        # This handles cases like "Where is the nearest restaurant?" which should be geography, not local_business
        location_patterns = ["where is", "where are", "location of", "nearest"]
        is_location_query = any(pattern in query_lower for pattern in location_patterns)

        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                # Special handling: If this is a location query and we're about to add local_business,
                # skip local_business to prioritize geography (e.g., "Where is the nearest restaurant?" should be geography)
                if domain == "local_business" and is_location_query:
                    # Skip local_business for location queries - geography should already be added or will be added
                    continue
                domains.append(domain)

        # Default to search if no domain detected
        if not domains:
            domains = ["search"]

        # Determine complexity
        if question_count > 1 or sentence_count > 2:
            complexity = QueryComplexity.MODERATE
            requires_synthesis = True
        elif len(domains) > 1:
            complexity = QueryComplexity.MODERATE
            requires_synthesis = True
        else:
            complexity = QueryComplexity.SIMPLE
            requires_synthesis = False

        return QueryIntent(
            original_query=query,
            complexity=complexity,
            domains=domains,
            requires_synthesis=requires_synthesis,
            metadata={
                "reasoning": "Fallback heuristic interpretation",
                "question_count": question_count,
                "sentence_count": sentence_count,
            }
        )
