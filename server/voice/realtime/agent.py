"""
Custom Voice Agent implementation bridging LiveKit to existing agent system.

This agent integrates the LiveKit voice pipeline (STT-LLM-TTS) with the existing
OpenAgents system (SmartRouter and SingleAgent), preserving all existing capabilities
while adding real-time voice interaction.
"""

import re
from typing import AsyncIterable, Optional, Any, Dict, List
from loguru import logger

try:
    from livekit.agents import Agent, llm as lk_llm, FlushSentinel
    from livekit.agents.llm import ChatContext, ChatMessage, ChatRole
except ImportError:
    logger.error("livekit-agents not installed. Install with: pip install livekit-agents livekit-plugins-openai livekit-plugins-silero")
    raise

from .config import RealtimeVoiceConfig
from .models import AgentType
from .exceptions import AgentInitializationException

# Trace cache for visualization (in-memory, TTL 5 minutes)
import time
from typing import Tuple

_trace_cache: Dict[str, Tuple[Any, float]] = {}  # {session_id: (trace, timestamp)}
_TRACE_TTL = 300  # 5 minutes


def _store_trace(session_id: str, trace: Any) -> None:
    """Store trace for session."""
    _trace_cache[session_id] = (trace, time.time())
    # Clean old traces
    now = time.time()
    to_delete = [sid for sid, (_, ts) in _trace_cache.items() if now - ts > _TRACE_TTL]
    for sid in to_delete:
        del _trace_cache[sid]


def _get_trace(session_id: str) -> Optional[Any]:
    """Get latest trace for session."""
    if session_id in _trace_cache:
        trace, ts = _trace_cache[session_id]
        if time.time() - ts < _TRACE_TTL:
            return trace
    return None


def strip_markdown_for_tts(text: str) -> str:
    """
    Strip Markdown formatting from text for clean TTS output.

    Removes:
    - Headers (##, ###)
    - Bold/italic (**text**, *text*)
    - Lists (-, *, 1.)
    - Code blocks (```, `)
    - Links ([text](url))
    - Other Markdown syntax

    Args:
        text: Markdown-formatted text

    Returns:
        Clean text suitable for TTS
    """
    if not text:
        return text

    # Remove code blocks (triple backticks)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Remove inline code (single backticks)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Remove headers (##, ###, etc.)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove bold/italic (**text**, __text__, *text*, _text_)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'__(.+?)__', r'\1', text)      # __bold__
    text = re.sub(r'\*(.+?)\*', r'\1', text)      # *italic*
    text = re.sub(r'_(.+?)_', r'\1', text)        # _italic_

    # Remove links but keep link text: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove list markers (-, *, 1., etc.)
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove blockquotes (>)
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rules (---, ***)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)

    # Remove extra whitespace (multiple blank lines)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Clean up leading/trailing whitespace
    text = text.strip()

    return text


class VoiceAgent(Agent):
    """
    Custom voice agent that bridges LiveKit voice pipeline to existing agent system.

    This agent overrides the LLM node to route through the OpenAgents SmartRouter
    or SingleAgent, preserving all existing agent capabilities while adding
    real-time voice interaction.

    Architecture:
    - STT (LiveKit/OpenAI): Speech to text transcription
    - LLM (Custom routing): Routes to SmartRouter or SingleAgent
    - TTS (LiveKit/OpenAI): Text to speech synthesis

    Features:
    - Maintains conversation history across turns
    - Supports tool definitions from existing agent system
    - Handles multi-agent handoffs when using SmartRouter
    - Provides hooks for custom STT/TTS processing
    """

    def __init__(
        self,
        *,
        instructions: str,
        model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        agent_type: AgentType = AgentType.SMART_ROUTER,
        agent_id: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        config: Optional[RealtimeVoiceConfig] = None,
        session_id: Optional[str] = None,
        room: Optional[Any] = None,  # LiveKit Room for data channel
    ):
        """
        Initialize the voice agent.

        Args:
            instructions: System instructions for the agent
            model: LLM model name (optional, uses config default)
            tools: List of tools available to the agent
            agent_type: Type of underlying agent (SMART_ROUTER or SINGLE_AGENT)
            agent_id: Specific agent ID (for SINGLE_AGENT type)
            agent_config: Configuration for the underlying agent
            config: Voice configuration
            room: LiveKit Room for sending data channel messages
        """
        try:
            self._config = config or RealtimeVoiceConfig.load()

            # LiveKit Agent only accepts 'instructions' parameter
            # The LLM model is configured in AgentSession, not here
            # Tools are handled via the llm_node override, not Agent initialization
            super().__init__(
                instructions=instructions,
            )

            # Store model and tools for reference (used in llm_node, not Agent init)
            self._llm_model = model or self._config.llm_model
            self._tools = tools or []

            self._agent_type = agent_type
            self._agent_id = agent_id
            self._agent_config = agent_config or {}
            self._underlying_agent: Optional[Any] = None
            self._conversation_history: List[Dict] = []
            self._session_id = session_id  # For trace storage and conversation memory
            self._room = room  # For data channel communication
            self._single_agent_session: Optional[Any] = None  # Session for SingleAgent mode

            logger.info(f"VoiceAgent initialized with agent_type={agent_type.value}, agent_id={agent_id}, session_id={session_id}, has_room={room is not None}")

        except Exception as e:
            # Use % formatting to avoid loguru format string issues
            logger.error("Failed to initialize VoiceAgent: %s", e)
            raise AgentInitializationException(
                message="Failed to initialize voice agent",
                details={"agent_type": str(agent_type), "error": str(e)},
                cause=e
            )

    async def on_enter(self) -> None:
        """
        Called when this agent becomes active in the session.

        Initializes the underlying agent (SmartRouter or SingleAgent).
        Per specification Section 5.2, this properly initializes the agent
        based on agent_type without using Runner incorrectly.
        """
        try:
            logger.info("VoiceAgent entering session, initializing underlying agent")

            if self._agent_type == AgentType.MOE:
                # Initialize MoE orchestrator using factory method
                from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
                from asdrp.orchestration.moe.config_loader import MoEConfigLoader
                from asdrp.agents.agent_factory import AgentFactory

                agent_factory = AgentFactory.instance()
                moe_config_loader = MoEConfigLoader()
                moe_config = moe_config_loader.load_config()

                # Validate expert agents exist
                from asdrp.agents.config_loader import AgentConfigLoader
                agent_config_loader = AgentConfigLoader()
                available_agents = agent_config_loader.list_agents()
                moe_config_loader.validate_expert_agents(available_agents)

                # Create MoE orchestrator
                self._underlying_agent = MoEOrchestrator.create_default(agent_factory, moe_config)
                logger.info("MoE Orchestrator initialized successfully")

            elif self._agent_type == AgentType.SMART_ROUTER:
                # Initialize SmartRouter using factory method
                from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
                from asdrp.agents.agent_factory import AgentFactory

                agent_factory = AgentFactory.instance()
                # Use SmartRouter.create() factory method which loads config from smartrouter.yaml
                # CRITICAL: Pass session_id to enable conversation memory across turns
                self._underlying_agent = SmartRouter.create(
                    agent_factory,
                    session_id=self._session_id,  # Pass session_id for conversation memory
                    enable_session_memory=True,  # Enable session memory for multi-turn conversations
                )
                logger.info(f"SmartRouter initialized successfully with session_id={self._session_id}")

            else:
                # Initialize SingleAgent via factory pattern
                from asdrp.agents.agent_factory import AgentFactory

                factory = AgentFactory.instance()

                if not self._agent_id:
                    # Default to first available agent
                    from asdrp.agents.config_loader import AgentConfigLoader
                    config_loader = AgentConfigLoader()
                    available_agents = config_loader.list_agents()
                    if available_agents:
                        self._agent_id = available_agents[0]
                        logger.info(f"No agent_id specified, using default: {self._agent_id}")

                if self._agent_id:
                    # Get agent with session memory for conversation history
                    # CRITICAL: Use get_agent_with_persistent_session to ensure session memory
                    # even if the agent config disables it (orchestrators need session-level memory)
                    self._underlying_agent, self._single_agent_session = await factory.get_agent_with_persistent_session(
                        self._agent_id,
                        session_id=self._session_id  # Use voice session_id for conversation memory
                    )
                    logger.info(f"SingleAgent initialized: {self._agent_id} with session_id={self._session_id}")
                else:
                    raise AgentInitializationException(
                        message="No agent available to initialize",
                        details={"agent_type": "single_agent"}
                    )

            await super().on_enter()
            logger.info(f"VoiceAgent entered session with {self._agent_type.value}")

        except Exception as e:
            # Use % formatting to avoid loguru format string issues
            logger.error("Failed to initialize underlying agent: %s", e, exc_info=True)
            raise AgentInitializationException(
                message="Failed to initialize underlying agent in on_enter",
                details={"agent_type": str(self._agent_type), "error": str(e)},
                cause=e
            )

    async def on_exit(self) -> None:
        """
        Called when this agent is being replaced or session ends.

        Cleans up underlying agent resources properly per specification Section 5.2.
        """
        try:
            logger.info("VoiceAgent exiting session, cleaning up resources")

            # Cleanup underlying agent if it exists
            if self._underlying_agent:
                # Cleanup if agent has cleanup method
                if hasattr(self._underlying_agent, 'cleanup'):
                    try:
                        await self._underlying_agent.cleanup()
                        logger.info("Underlying agent cleanup completed")
                    except Exception as e:
                        logger.warning(f"Error during underlying agent cleanup: {e}")

            # Clear resources
            self._underlying_agent = None
            self._conversation_history.clear()
            logger.info(f"Cleared conversation history ({len(self._conversation_history)} messages before clear)")

            await super().on_exit()
            logger.info("VoiceAgent exited session successfully")

        except Exception as e:
            logger.error(f"Error during agent exit: {e}", exc_info=True)

    async def _send_trace_via_data_channel(self, trace: Any) -> None:
        """
        Send MoE trace data via LiveKit data channel.

        This provides immediate trace delivery to the frontend without polling.
        """
        try:
            import json
            from dataclasses import asdict

            # Convert trace to dict
            trace_dict = asdict(trace) if hasattr(trace, '__dataclass_fields__') else trace

            # Create message
            message = {
                "type": "moe_trace",
                "session_id": self._session_id,
                "trace": trace_dict,
                "timestamp": time.time()
            }

            # Send via data channel to all participants
            payload = json.dumps(message).encode('utf-8')
            await self._room.local_participant.publish_data(
                payload=payload,
                topic="orchestration_trace",
                reliable=True
            )

            logger.info(f"✅ Sent MoE trace via data channel: {len(payload)} bytes")

        except Exception as e:
            logger.error(f"Failed to send trace via data channel: {e}", exc_info=True)

    async def llm_node(
        self,
        chat_ctx: ChatContext,
        tools: Optional[List[Any]] = None,
        model_settings: Optional[Any] = None,
    ) -> AsyncIterable[lk_llm.ChatChunk | str | FlushSentinel]:
        """
        Override LLM node to route through existing agent system.

        This method intercepts the LLM call and routes it through the
        SmartRouter or SingleAgent, enabling all existing agent capabilities
        (tools, handoffs, etc.) while maintaining voice pipeline integration.

        Args:
            chat_ctx: Current chat context with message history
            tools: Optional list of tools (not used, tools come from underlying agent)
            model_settings: Optional model settings (not used, model configured in AgentSession)

        Yields:
            ChatChunk with the agent response
        """
        try:
            # Extract the latest user message
            user_message = self._extract_user_message(chat_ctx)
            logger.debug(f"Processing user message: {user_message[:100] if user_message else '(empty)'}...")

            # Handle empty messages (initial greeting, system warmup)
            if not user_message or user_message.strip() == "":
                logger.info("Empty user message detected, generating default greeting")
                response_text = "Hello! I'm your AI assistant. How can I help you today?"

                # Strip Markdown for clean TTS (though greeting shouldn't have Markdown)
                tts_text = strip_markdown_for_tts(response_text)
                logger.info(f"Greeting TTS text: {tts_text}")

                # Yield greeting as plain string for TTS
                yield tts_text

                # Update conversation history (store original with Markdown for transcript)
                self._conversation_history.append({
                    "role": "assistant",
                    "content": response_text,
                })
                return

            if not self._underlying_agent:
                logger.error("Underlying agent not initialized")
                yield "I apologize, but I'm not fully initialized yet. Please try again."
                return

            # Generate thinking filler before processing
            from server.voice.realtime.thinking_filler import get_thinking_filler
            import asyncio

            thinking_filler = get_thinking_filler(user_message)
            if thinking_filler:
                logger.info(f"Using thinking filler: '{thinking_filler}'")
                # Yield thinking filler immediately as plain string
                yield thinking_filler

                # CRITICAL: Yield FlushSentinel to force immediate TTS playback
                # This ensures the filler is spoken BEFORE the agent processes the query
                # Without this, the filler and response are buffered together
                yield FlushSentinel()
                logger.debug("Filler flushed to TTS, now processing query...")

                # Additional async yield point for good measure
                await asyncio.sleep(0)

            # Route through underlying agent
            if self._agent_type == AgentType.MOE:
                # MoE Orchestrator: route_query method returns MoEResult
                # CRITICAL: Pass session_id to maintain conversation history across turns
                logger.info(f"Routing query through MoE Orchestrator: '{user_message}' (session_id={self._session_id})")
                result = await self._underlying_agent.route_query(
                    query=user_message,
                    session_id=self._session_id,  # Pass session_id for conversation memory
                    context=None
                )

                # Log expert selection for debugging
                logger.info(f"MoE selected experts: {result.experts_used}")
                logger.info(f"MoE latency: {result.trace.latency_ms:.2f}ms, cache_hit: {result.trace.cache_hit}")

                # Store trace for visualization
                if self._session_id and hasattr(result, 'trace'):
                    _store_trace(self._session_id, result.trace)
                    logger.debug(f"Stored MoE trace for session: {self._session_id}")

                    # Send trace via data channel for immediate frontend delivery
                    if self._room:
                        await self._send_trace_via_data_channel(result.trace)

                # Extract the final answer from the result
                # MoEResult has 'response' attribute
                response_text = result.response
                logger.info(f"MoE final answer length: {len(response_text)} chars")

                # Strip Markdown for clean TTS output
                tts_text = strip_markdown_for_tts(response_text)
                logger.info(f"MoE response - Original: {len(response_text)} chars, TTS: {len(tts_text)} chars")
                logger.debug(f"TTS text preview: {tts_text[:200]}...")

                # Fallback if markdown stripping removed all content
                if not tts_text or not tts_text.strip():
                    logger.warning("TTS text is empty after markdown stripping - using fallback response")
                    tts_text = "I've generated a response for you. Please check the chat for details."

                # Stream tokens to properly trigger TTS
                # Split into sentences for natural speech pacing
                sentences = re.split(r'([.!?]+\s+)', tts_text)
                sentences = [s for s in sentences if s.strip()]

                # Fallback if no sentences found
                if not sentences:
                    logger.warning("No sentences found after splitting - using full text as single sentence")
                    sentences = [tts_text]

                logger.info(f"Streaming {len(sentences)} sentence chunks to TTS")

                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        logger.debug(f"Yielding sentence chunk {i+1}/{len(sentences)}: {sentence[:50]}...")
                        # Yield plain string - simpler and more compatible with LiveKit TTS
                        yield sentence

                        # CRITICAL: Yield FlushSentinel after first sentence to start audio immediately
                        # This prevents buffering and ensures audio plays as soon as first sentence is ready
                        if i == 0:
                            logger.debug("Flushing first sentence to start TTS immediately")
                            yield FlushSentinel()

            elif self._agent_type == AgentType.SMART_ROUTER:
                # SmartRouter: route_query method returns SmartRouterExecutionResult
                # Note: SmartRouter session_id is set during initialization, not per-query
                logger.info(f"Routing query through SmartRouter: '{user_message}' (session_id={self._session_id})")
                result = await self._underlying_agent.route_query(
                    query=user_message,
                    context=None
                )

                # Log routing decision for debugging
                if hasattr(result, 'selected_agents'):
                    selected = [a.name if hasattr(a, 'name') else str(a) for a in (result.selected_agents or [])]
                    logger.info(f"SmartRouter selected agents: {selected}")
                if hasattr(result, 'interpretation'):
                    logger.info(f"Query interpretation: {result.interpretation}")

                # Extract the final answer from the result
                # SmartRouterExecutionResult has 'answer' attribute directly
                response_text = result.answer
                logger.info(f"SmartRouter final answer length: {len(response_text)} chars")

                # Strip Markdown for clean TTS output
                tts_text = strip_markdown_for_tts(response_text)
                logger.info(f"SmartRouter response - Original: {len(response_text)} chars, TTS: {len(tts_text)} chars")
                logger.debug(f"TTS text preview: {tts_text[:200]}...")

                # Fallback if markdown stripping removed all content
                if not tts_text or not tts_text.strip():
                    logger.warning("TTS text is empty after markdown stripping - using fallback response")
                    tts_text = "I've generated a response for you. Please check the chat for details."

                # CRITICAL: Stream tokens to properly trigger TTS
                # LiveKit's TTS expects streaming tokens, not a single chunk
                # Split into sentences for natural speech pacing
                sentences = re.split(r'([.!?]+\s+)', tts_text)
                sentences = [s for s in sentences if s.strip()]

                # Fallback if no sentences found
                if not sentences:
                    logger.warning("No sentences found after splitting - using full text as single sentence")
                    sentences = [tts_text]

                logger.info(f"Streaming {len(sentences)} sentence chunks to TTS")

                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        logger.debug(f"Yielding sentence chunk {i+1}/{len(sentences)}: {sentence[:50]}...")
                        # Yield plain string - simpler and more compatible with LiveKit TTS
                        yield sentence

                        # CRITICAL: Yield FlushSentinel after first sentence to start audio immediately
                        # This prevents buffering and ensures audio plays as soon as first sentence is ready
                        if i == 0:
                            logger.debug("Flushing first sentence to start TTS immediately")
                            yield FlushSentinel()

            else:
                # SingleAgent: use Runner.run for execution
                # CRITICAL: Use session for conversation memory across turns
                from openai_agents import Runner

                logger.info(f"Executing SingleAgent query: '{user_message}' (session_id={self._session_id})")
                result = await Runner.run(
                    starting_agent=self._underlying_agent,
                    input=user_message,
                    session=self._single_agent_session,  # Use session for conversation memory
                )

                # Extract response and stream as single chunk
                response_text = str(result.final_output) if hasattr(result, 'final_output') else str(result)

                # Strip Markdown for clean TTS output
                tts_text = strip_markdown_for_tts(response_text)
                logger.info(f"SingleAgent response - Original: {len(response_text)} chars, TTS: {len(tts_text)} chars")

                # Fallback if markdown stripping removed all content
                if not tts_text or not tts_text.strip():
                    logger.warning("TTS text is empty after markdown stripping - using fallback response")
                    tts_text = "I've generated a response for you. Please check the chat for details."

                # Stream tokens for TTS
                sentences = re.split(r'([.!?]+\s+)', tts_text)
                sentences = [s for s in sentences if s.strip()]

                # Fallback if no sentences found
                if not sentences:
                    logger.warning("No sentences found after splitting - using full text as single sentence")
                    sentences = [tts_text]

                logger.info(f"Streaming {len(sentences)} sentence chunks to TTS")

                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        logger.debug(f"Yielding sentence chunk {i+1}/{len(sentences)}: {sentence[:50]}...")
                        # Yield plain string - simpler and more compatible with LiveKit TTS
                        yield sentence

                        # CRITICAL: Yield FlushSentinel after first sentence to start audio immediately
                        # This prevents buffering and ensures audio plays as soon as first sentence is ready
                        if i == 0:
                            logger.debug("Flushing first sentence to start TTS immediately")
                            yield FlushSentinel()

            # Update conversation history
            self._conversation_history.append({
                "role": "user",
                "content": user_message,
            })
            self._conversation_history.append({
                "role": "assistant",
                "content": response_text if 'response_text' in locals() else "",
            })

        except Exception as e:
            logger.error(f"Error in llm_node: {e}", exc_info=True)
            yield f"I apologize, but I encountered an error: {str(e)}"

    def _extract_user_message(self, chat_ctx: ChatContext) -> str:
        """
        Extract the latest user message from chat context.

        Args:
            chat_ctx: Chat context with message history

        Returns:
            Latest user message content
        """
        try:
            # Get items from context (LiveKit uses 'items', not 'messages')
            items = chat_ctx.items if hasattr(chat_ctx, 'items') else []

            logger.debug(f"Chat context has {len(items)} items")

            # Find most recent user message
            for item in reversed(items):
                # Check if item is a ChatMessage with user role
                if hasattr(item, 'role') and item.role == "user":
                    # Get text content from the message (it's a property, not a method)
                    if hasattr(item, 'text_content'):
                        content = item.text_content  # Property access, not function call
                        if content and content.strip():
                            logger.debug(f"Found user message: {content[:100]}...")
                            return content
                    elif hasattr(item, 'content'):
                        # Fallback: try content field directly
                        content_items = item.content if isinstance(item.content, list) else [item.content]
                        for content_item in content_items:
                            if hasattr(content_item, 'text'):
                                text = content_item.text
                                if text and text.strip():
                                    logger.debug(f"Found user message: {text[:100]}...")
                                    return text

            logger.warning(f"No user message found in {len(items)} chat items")
            return ""

        except Exception as e:
            logger.error(f"Error extracting user message: {e}", exc_info=True)
            return ""
