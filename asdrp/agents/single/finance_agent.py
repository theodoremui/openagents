#############################################################################
# finance_agent.py
#
# FinanceAgent implementation using the Agent protocol.
#
# This module provides a FinanceAgent that implements AgentProtocol and uses
# financial data tools for retrieving stock information, market data, financial
# statements, news, and other financial information.
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import Any, Dict
import asyncio

from agents import Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import ModelConfig

# Default instructions for FinanceAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
DEFAULT_INSTRUCTIONS = (
    "You are a useful agent that can help with financial data queries. "
    "You can retrieve stock information, historical market data, financial "
    "statements, company information, news, analyst recommendations, options data, "
    "and other financial information for any ticker symbol. When providing financial "
    "data, always include the ticker symbol and relevant context. For news articles, "
    "note that the structure has nested content where titles are in content.title."
)


def create_finance_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a FinanceAgent instance.
    
    This is the public factory function for creating FinanceAgent instances.
    It is used by AgentFactory and can also be called directly.
    
    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
    
    Returns:
        A FinanceAgent instance implementing AgentProtocol.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent = create_finance_agent()
    >>> agent = create_finance_agent("You are a financial data expert")
    >>> from asdrp.agents.config_loader import ModelConfig
    >>> model_cfg = ModelConfig(name="gpt-4", temperature=0.8)
    >>> agent = create_finance_agent("Instructions", model_cfg)
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS
    
    try:
        from asdrp.actions.finance.finance_tools import FinanceTools
        from agents import Agent, ModelSettings
        
        # Build agent creation arguments
        agent_kwargs: Dict[str, Any] = {
            "name": "FinanceAgent",
            "instructions": instructions,
            "tools": FinanceTools.tool_list,
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
            f"Failed to import FinanceAgent dependencies: {str(e)}",
            agent_name="finance"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create FinanceAgent: {str(e)}",
            agent_name="finance"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for FinanceAgent interactive session.
    
    Creates a FinanceAgent and runs an interactive loop where users can
    query financial data, stock information, and market data.
    """
    agent = create_finance_agent()
    
    user_input = input(f"Ask {agent.name}: ")
    while user_input != "":
        response = await Runner.run(agent, input=user_input)
        print(response.final_output)
        user_input = input(f"Ask {agent.name}: ")


if __name__ == "__main__":
    asyncio.run(main())

