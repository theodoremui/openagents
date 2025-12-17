#############################################################################
# one_agent.py
#
# OneAgent implementation using the Agent protocol.
#
# This module provides a OneAgent that implements AgentProtocol and uses
# web search tools for general-purpose queries and information retrieval.
#
#############################################################################

from typing import Any
import asyncio

from agents import Runner
from agents.tracing import set_tracing_disabled
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
set_tracing_disabled(disabled=True)

from typing import Any, Dict
from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig

# Default instructions for OneAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
DEFAULT_INSTRUCTIONS = """You are a useful agent that can help with the user's request.
You have access to web search capabilities to find current information
and answer questions.

IMPORTANT FORMATTING GUIDELINES:
- Format responses in clear, structured markdown when appropriate
- Use headings (##, ###), bullet points, numbered lists, and tables for organization
- Use **bold** for emphasis and `code` formatting for technical terms
- Use blockquotes (>) for important notes or citations

IMAGE HANDLING:
- DO NOT use markdown image syntax (![alt](url)) as web search does not provide image URLs
- Instead, when users ask about visual content:
  * Describe the content in detail using text
  * Provide clickable links where users can view images: [View image](url)
  * Use phrases like "You can view this image at: [link]"

EXAMPLES:
❌ Bad: ![Golden Gate Bridge](https://example.com/image.jpg)
✅ Good: The Golden Gate Bridge is a suspension bridge spanning the Golden Gate strait.
         You can view images at: [SF Travel Photos](https://example.com/photos)

Always prioritize accurate, well-formatted text responses with working hyperlinks.
"""


def create_one_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a OneAgent instance.
    
    This is the public factory function for creating OneAgent instances.
    It is used by AgentFactory and can also be called directly.
    
    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
    
    Returns:
        A OneAgent instance implementing AgentProtocol.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent = create_one_agent()
    >>> agent = create_one_agent("You are a research assistant")
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS
    
    try:
        from agents import Agent, WebSearchTool, ModelSettings
        
        # Build agent creation arguments
        agent_kwargs: Dict[str, Any] = {
            "name": "OneAgent",
            "instructions": instructions,
            "tools": [WebSearchTool()],
        }
        
        # Add model configuration if provided
        if model_config:
            agent_kwargs["model"] = model_config.name
            agent_kwargs["model_settings"] = ModelSettings(
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
        
        return Agent[Any](**agent_kwargs)
    except ImportError as e:
        raise AgentException(
            f"Failed to import OneAgent dependencies: {str(e)}",
            agent_name="one"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create OneAgent: {str(e)}",
            agent_name="one"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for OneAgent interactive session.
    
    Creates a OneAgent and runs an interactive loop where users can
    ask general questions and search the web.
    """
    agent = create_one_agent()
    
    user_input = input("Enter your request: ")
    while user_input != "":
        response = await Runner.run(agent, input=user_input)
        print(response.final_output)
        user_input = input("Enter your request: ")


if __name__ == "__main__":
    asyncio.run(main())

