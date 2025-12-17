#############################################################################
# yelp_agent.py
#
# YelpAgent implementation using the Agent protocol.
#
# This module provides a YelpAgent that implements AgentProtocol and uses
# Yelp business search tools for finding restaurants, businesses, and reviews.
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import asyncio
from typing import Any, Dict

from agents import Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.agents.config_loader import ModelConfig
from asdrp.agents.protocol import AgentProtocol, AgentException

# Default instructions for YelpAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
DEFAULT_INSTRUCTIONS = (
    "You are a useful agent that can help with finding businesses, restaurants, "
    "and reviews using Yelp. You can search for businesses by location, cuisine, "
    "and other criteria, and provide detailed information including reviews."
)


def create_yelp_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a YelpAgent instance.
    
    This is the public factory function for creating YelpAgent instances.
    It is used by AgentFactory and can also be called directly.
    
    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
    
    Returns:
        A YelpAgent instance implementing AgentProtocol.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent = create_yelp_agent()
    >>> agent = create_yelp_agent("You are a restaurant finder expert")
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS
    
    try:        
        from asdrp.actions.local.yelp_tools import YelpTools
        from agents import Agent, ModelSettings
        
        # Build agent creation arguments
        agent_kwargs: Dict[str, Any] = {
            "name": "YelpAgent",
            "instructions": instructions,
            "tools": YelpTools.tool_list,
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
            f"Failed to import YelpAgent dependencies: {str(e)}",
            agent_name="yelp"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create YelpAgent: {str(e)}",
            agent_name="yelp"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for YelpAgent interactive session.
    
    Creates a YelpAgent and runs an interactive loop where users can
    search for businesses and restaurants.
    """
    agent = create_yelp_agent()
    
    user_input = input("Ask Yelp: ")
    while user_input != "":
        response = await Runner.run(agent, input=user_input)
        print(response.final_output)
        user_input = input("Ask Yelp: ")


if __name__ == "__main__":
    asyncio.run(main())

