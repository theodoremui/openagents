"""
Simple LiveKit Voice Agent - Following Official Documentation Pattern

This is the CORRECT way to implement a LiveKit voice agent:
1. Subclass Agent with instructions
2. NO llm_node override
3. Let AgentSession handle TTS automatically

Reference: https://docs.livekit.io/agents/quickstart/
"""

from typing import Optional
from loguru import logger

try:
    from livekit.agents import Agent
except ImportError:
    logger.error("livekit-agents not installed")
    raise

from .config import RealtimeVoiceConfig
from .exceptions import AgentInitializationException


class SimpleVoiceAgent(Agent):
    """
    Simple voice agent that lets LiveKit handle everything automatically.

    This agent:
    - Provides instructions to the LLM
    - NO custom llm_node (let LiveKit handle it)
    - TTS works automatically through AgentSession
    - Clean, simple, following official docs

    The AgentSession automatically:
    - Captures audio via STT
    - Sends to LLM with agent instructions
    - Synthesizes response via TTS
    - Plays audio back to user
    """

    def __init__(
        self,
        instructions: Optional[str] = None,
        config: Optional[RealtimeVoiceConfig] = None,
    ):
        """
        Initialize simple voice agent.

        Args:
            instructions: System instructions for the LLM
            config: Voice configuration
        """
        try:
            # Load config with error handling
            if config is None:
                try:
                    self._config = RealtimeVoiceConfig.load()
                except Exception as e:
                    logger.error(f"Failed to load RealtimeVoiceConfig: {e}", exc_info=True)
                    raise AgentInitializationException(
                        message="Failed to load voice configuration",
                        details={"error": str(e)},
                        cause=e
                    )
            else:
                self._config = config

            # Default instructions
            if instructions is None:
                instructions = """You are a helpful voice AI assistant.

You eagerly assist users with their questions by providing information from your extensive knowledge.

IMPORTANT for voice interaction:
- Keep responses concise and conversational
- Avoid complex formatting, markdown, or special characters
- Speak naturally as if having a conversation
- Don't use bullet points or numbered lists in speech
- Answer directly without saying "according to" or "based on"

When users ask questions:
- Provide clear, direct answers
- Use simple, spoken language
- Keep responses under 3-4 sentences when possible
- For complex topics, break into digestible chunks
"""

            # Initialize base Agent
            # This is all that's needed! LiveKit handles the rest.
            super().__init__(
                instructions=instructions,
            )

            logger.info("SimpleVoiceAgent initialized")

        except Exception as e:
            logger.error(f"Failed to initialize SimpleVoiceAgent: {e}")
            raise AgentInitializationException(
                message="Failed to initialize simple voice agent",
                details={"error": str(e)},
                cause=e
            )


def create_simple_voice_agent(
    instructions: Optional[str] = None,
    config: Optional[RealtimeVoiceConfig] = None,
) -> SimpleVoiceAgent:
    """
    Factory function to create simple voice agent.

    Args:
        instructions: Optional custom instructions
        config: Optional voice configuration

    Returns:
        SimpleVoiceAgent instance
    """
    return SimpleVoiceAgent(
        instructions=instructions,
        config=config,
    )
