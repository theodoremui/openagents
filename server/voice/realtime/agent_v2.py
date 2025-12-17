"""
Proper LiveKit Voice Agent implementation following official documentation.

This implementation follows LiveKit's recommended pattern:
- Simple Agent subclass with instructions
- NO llm_node override (let framework handle TTS)
- Use tools to integrate with SmartRouter
- Let AgentSession manage STT→LLM→TTS pipeline automatically

Reference: https://docs.livekit.io/agents/build/
"""

import re
from typing import Any, Dict, List, Optional
from loguru import logger

try:
    from livekit.agents import Agent
except ImportError:
    logger.error("livekit-agents not installed")
    raise

from .config import RealtimeVoiceConfig
from .models import AgentType
from .exceptions import AgentInitializationException


def strip_markdown_for_speech(text: str) -> str:
    """
    Strip Markdown formatting for natural speech.

    The LiveKit TTS will speak whatever the LLM returns, so we need
    clean text without formatting markers.
    """
    if not text:
        return text

    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove bold/italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)

    # Remove links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove list markers
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


class SmartRouterTool:
    """
    Tool that wraps SmartRouter for use by LiveKit Agent.

    This is the proper way to integrate custom logic:
    - Define as a tool the LLM can call
    - Tool handles SmartRouter routing
    - Returns clean text for TTS
    """

    def __init__(self):
        self._router = None

    async def initialize(self):
        """Lazy initialization of SmartRouter."""
        if self._router is None:
            from asdrp.orchestration.smartrouter.smartrouter import SmartRouter
            from asdrp.agents.agent_factory import AgentFactory

            agent_factory = AgentFactory.instance()
            self._router = SmartRouter.create(agent_factory)
            logger.info("SmartRouter tool initialized")

    async def route_query(self, query: str) -> str:
        """
        Route query through SmartRouter and return clean response.

        Args:
            query: User's question

        Returns:
            Clean text response suitable for TTS
        """
        await self.initialize()

        logger.info(f"Routing query through SmartRouter: {query[:100]}...")

        # Execute query
        result = await self._router.route_query(query)
        response_text = result.answer

        # Strip Markdown for natural speech
        clean_text = strip_markdown_for_speech(response_text)

        logger.info(f"SmartRouter response: {len(response_text)} → {len(clean_text)} chars")
        logger.debug(f"Clean response preview: {clean_text[:200]}...")

        return clean_text


class VoiceAssistant(Agent):
    """
    Voice AI Assistant following LiveKit best practices.

    This agent:
    - Uses SmartRouter via tools (proper integration)
    - Lets LiveKit handle TTS automatically (no llm_node override)
    - Returns clean text without Markdown
    - Works with LiveKit's automatic STT→LLM→TTS pipeline

    Architecture:
    User speaks → STT → LLM (this agent) → calls SmartRouterTool → TTS → audio plays
    """

    def __init__(
        self,
        instructions: Optional[str] = None,
        agent_type: AgentType = AgentType.SMART_ROUTER,
        config: Optional[RealtimeVoiceConfig] = None,
    ):
        """
        Initialize voice assistant.

        Args:
            instructions: System instructions (optional, uses default if not provided)
            agent_type: Type of agent (SMART_ROUTER or SINGLE_AGENT)
            config: Voice configuration
        """
        try:
            self._config = config or RealtimeVoiceConfig.load()
            self._agent_type = agent_type

            # Default instructions that guide the LLM to use SmartRouter
            if instructions is None:
                instructions = """You are a helpful voice AI assistant powered by SmartRouter.

When the user asks a question, you should:
1. Call the route_query tool with their exact question
2. Return the tool's response naturally as if it's your own answer
3. Speak clearly and concisely - avoid complex formatting
4. Be conversational and friendly

IMPORTANT:
- Always use the route_query tool to answer questions
- Don't make up information - use the tool's response
- Keep responses concise for voice interaction
- Avoid saying "according to the tool" - just answer naturally
"""

            # Initialize base Agent with instructions
            # NO tools parameter - we'll add them after initialization
            super().__init__(
                instructions=instructions,
            )

            # Note: We can't pass tools to __init__ because we need async initialization
            # The tool will be added in on_enter()
            self._smart_router_tool = SmartRouterTool()

            logger.info(f"VoiceAssistant initialized with agent_type={agent_type.value}")

        except Exception as e:
            logger.error(f"Failed to initialize VoiceAssistant: {e}")
            raise AgentInitializationException(
                message="Failed to initialize voice assistant",
                details={"agent_type": str(agent_type), "error": str(e)},
                cause=e
            )

    async def on_enter(self) -> None:
        """
        Called when agent becomes active in the session.

        Initialize SmartRouter tool here (async initialization).
        """
        try:
            logger.info("VoiceAssistant entering session")

            # Initialize SmartRouter tool
            await self._smart_router_tool.initialize()

            await super().on_enter()
            logger.info("VoiceAssistant entered session successfully")

        except Exception as e:
            logger.error(f"Failed in on_enter: {e}", exc_info=True)
            raise AgentInitializationException(
                message="Failed to initialize agent in on_enter",
                details={"error": str(e)},
                cause=e
            )

    async def on_exit(self) -> None:
        """
        Called when agent is being replaced or session ends.

        Cleanup resources.
        """
        try:
            logger.info("VoiceAssistant exiting session")

            # Cleanup if needed
            self._smart_router_tool = None

            await super().on_exit()
            logger.info("VoiceAssistant exited successfully")

        except Exception as e:
            logger.error(f"Error during agent exit: {e}", exc_info=True)


def create_voice_assistant(
    instructions: Optional[str] = None,
    agent_type: AgentType = AgentType.SMART_ROUTER,
    config: Optional[RealtimeVoiceConfig] = None,
) -> VoiceAssistant:
    """
    Factory function to create voice assistant.

    Args:
        instructions: Optional custom instructions
        agent_type: Type of agent to use
        config: Optional voice configuration

    Returns:
        VoiceAssistant instance
    """
    return VoiceAssistant(
        instructions=instructions,
        agent_type=agent_type,
        config=config,
    )
