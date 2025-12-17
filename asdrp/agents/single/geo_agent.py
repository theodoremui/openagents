#############################################################################
# geo_agent.py
#
# GeoAgent implementation using the Agent protocol.
#
# This module provides a GeoAgent that implements AgentProtocol and uses
# geocoding tools for location-based queries.
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import Any, Dict
import asyncio

from agents import Agent, ModelSettings, Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.actions.geo.geo_tools import GeoTools
from asdrp.agents.config_loader import ModelConfig
from asdrp.agents.protocol import AgentProtocol, AgentException

# Default instructions for GeoAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
DEFAULT_INSTRUCTIONS = (
    "You are a useful agent that can help with the user's request about "
    "geocoding and reverse geocoding. You can convert addresses to coordinates "
    "and coordinates to addresses."
)


def create_geo_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a GeoAgent instance.
    
    This is the public factory function for creating GeoAgent instances.
    It is used by AgentFactory and can also be called directly.
    
    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
    
    Returns:
        A GeoAgent instance implementing AgentProtocol.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent = create_geo_agent()
    >>> agent = create_geo_agent("You are a location expert")
    >>> from asdrp.agents.config_loader import ModelConfig
    >>> model_cfg = ModelConfig(name="gpt-4", temperature=0.8)
    >>> agent = create_geo_agent("Instructions", model_cfg)
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS
    
    try:
        # Build agent creation arguments
        agent_kwargs: Dict[str, Any] = {
            "name": "GeoAgent",
            "instructions": instructions,
            "tools": GeoTools.tool_list,
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
            f"Failed to import GeoAgent dependencies: {str(e)}",
            agent_name="geo"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create GeoAgent: {str(e)}",
            agent_name="geo"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for GeoAgent interactive session.
    
    Creates a GeoAgent and runs an interactive loop where users can
    ask questions about geocoding and reverse geocoding.
    """
    agent = create_geo_agent()
    
    user_input = input(f"Ask {agent.name}: ")
    while user_input != "":
        response = await Runner.run(agent, input=user_input)
        print(response.final_output)
        user_input = input(f"Ask {agent.name}: ")


if __name__ == "__main__":
    asyncio.run(main())

