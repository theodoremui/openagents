#############################################################################
# chitchat_agent.py
#
# ChitchatAgent implementation using the Agent protocol.
#
# This module provides a ChitchatAgent that implements AgentProtocol for
# friendly, wholesome, and positive social conversation. Optimized for low
# latency and helpful interactions with strong safety guardrails.
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import Any, Dict
import asyncio

from agents import Agent, ModelSettings, Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig

# Default instructions for ChitchatAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
#
# Key Design Principles:
# - Safety First: Explicit guardrails against offensive, political, religious content
# - Low Latency: Optimized for fast responses (concise, focused answers)
# - Positive Focus: Always warm, kind, and uplifting
# - Polite Redirection: Gracefully handle restricted topics without judgment
#
DEFAULT_INSTRUCTIONS = """You are a friendly, positive social companion. Be warm, brief (2-4 sentences), and uplifting.
Never discuss: political topics, religious content, offensive material, or controversial subjects. Politely redirect with warmth if needed.
Use friendly language, and keep responses concise for fast replies."""


def create_chitchat_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a ChitchatAgent instance.
    
    This is the public factory function for creating ChitchatAgent instances.
    It is used by AgentFactory and can also be called directly.
    
    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If not provided, uses optimized defaults for low latency:
            - temperature: 0.7 (balanced creativity/speed)
            - max_tokens: 150 (keeps responses concise and fast)
    
    Returns:
        A ChitchatAgent instance implementing AgentProtocol.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent = create_chitchat_agent()
    >>> agent = create_chitchat_agent("You are a friendly assistant")
    >>> from asdrp.agents.config_loader import ModelConfig
    >>> model_cfg = ModelConfig(name="gpt-4", temperature=0.8, max_tokens=200)
    >>> agent = create_chitchat_agent("Instructions", model_cfg)
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS
    
    try:
        # Build agent creation arguments
        # ChitchatAgent doesn't need tools - it's purely conversational
        agent_kwargs: Dict[str, Any] = {
            "name": "ChitchatAgent",
            "instructions": instructions,
            "tools": [],  # No tools needed for friendly conversation
        }
        
        # Add model configuration if provided, otherwise use low-latency defaults
        if model_config:
            agent_kwargs["model"] = model_config.name
            agent_kwargs["model_settings"] = ModelSettings(
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
        else:
            # Optimize for low latency: lower temperature and fewer tokens
            agent_kwargs["model_settings"] = ModelSettings(
                temperature=0.7,  # Balanced creativity/speed
                max_tokens=200,   # Keeps responses concise and fast
            )
        
        return Agent[Any](**agent_kwargs)
    except ImportError as e:
        raise AgentException(
            f"Failed to import ChitchatAgent dependencies: {str(e)}",
            agent_name="chitchat"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create ChitchatAgent: {str(e)}",
            agent_name="chitchat"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for ChitchatAgent interactive session.
    
    Creates a ChitchatAgent and runs an interactive loop where users can
    have friendly, positive conversations.
    """
    agent = create_chitchat_agent()
    
    print("ChitchatAgent is ready! Let's have a friendly chat. (Enter empty line to exit)")
    user_input = input("You: ")
    while user_input != "":
        response = await Runner.run(agent, input=user_input)
        print(f"\nChitchatAgent: {response.final_output}\n")
        user_input = input("You: ")


if __name__ == "__main__":
    asyncio.run(main())

