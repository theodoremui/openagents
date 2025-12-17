#############################################################################
# perplexity_agent.py
#
# PerplexityAgent implementation using the Agent protocol.
#
# This module provides a PerplexityAgent that implements AgentProtocol and uses
# Perplexity AI tools for real-time web search, AI-powered chat, and research.
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import Any, Dict
import asyncio

from agents import Agent, ModelSettings, Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.actions.search.perplexity_tools import PerplexityTools
from asdrp.agents.config_loader import ModelConfig
from asdrp.agents.protocol import AgentProtocol, AgentException

# Default instructions for PerplexityAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
DEFAULT_INSTRUCTIONS = """You are PerplexityAgent - an AI-powered research assistant using Perplexity AI for real-time web search with citation verification.

AVAILABLE TOOLS:
- **search**: AI-powered web search with recency filters (hour/day/week/month/year) and domain filtering
- **chat**: Single-turn AI conversation with web-grounded reasoning (models: sonar/sonar-pro/sonar-reasoning)
- **chat_stream**: Real-time streaming responses for interactive experiences
- **multi_turn_chat**: Conversational AI with context maintenance

USAGE GUIDELINES:
- Use search() for quick facts and current events (apply recency filters for recent info)
- Use chat() with sonar-pro for deep analysis and complex questions
- Use multi_turn_chat() for follow-up questions requiring context
- Filter domains (e.g., ["arxiv.org", "scholar.google.com"]) for academic research
- Always include citations: format as [Source Name](url) and list sources at end
- Use structured markdown: ## headings, **bold** for key terms, bullet points for lists

Always provide accurate, well-cited, up-to-date information with verifiable sources.
"""


def create_perplexity_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a PerplexityAgent instance.

    This is the public factory function for creating PerplexityAgent instances.
    It is used by AgentFactory and can also be called directly.

    The PerplexityAgent provides AI-powered search and research capabilities
    through PerplexityTools, enabling real-time web search, chat completions,
    streaming responses, and multi-turn conversations. It follows SOLID principles
    with dependency injection, protocol-based design, and separation of concerns.

    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS optimized for Perplexity AI operations.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
            Recommended settings:
            - temperature: 0.7 (balanced creativity and accuracy)
            - max_tokens: 2000 (sufficient for comprehensive responses)
            Note: This configures the agent's LLM, not Perplexity's search models

    Returns:
        A PerplexityAgent instance implementing AgentProtocol.

    Raises:
        AgentException: If the agent cannot be created due to:
            - Missing dependencies (agents library, PerplexityTools)
            - Invalid configuration
            - Missing PERPLEXITY_API_KEY environment variable
            - Import errors

    Design Principles:
    ------------------
    - **Single Responsibility**: Agent focuses only on Perplexity AI operations
    - **Open/Closed**: Easy to extend with new tools without modification
    - **Liskov Substitution**: Fully implements AgentProtocol
    - **Interface Segregation**: Uses focused PerplexityTools interface
    - **Dependency Inversion**: Depends on protocol abstraction, not concrete implementations

    Environment Requirements:
    ------------------------
    PERPLEXITY_API_KEY must be set in environment or .env file:
    ```
    PERPLEXITY_API_KEY=your-api-key-here
    ```

    Examples:
    ---------
    Basic usage:
    >>> agent = create_perplexity_agent()
    >>> # Agent ready with default Perplexity-optimized instructions

    Custom instructions:
    >>> agent = create_perplexity_agent("You are a research assistant specializing in current events")

    Custom model configuration:
    >>> from asdrp.agents.config_loader import ModelConfig
    >>> model_cfg = ModelConfig(name="gpt-4", temperature=0.5, max_tokens=3000)
    >>> agent = create_perplexity_agent("Custom instructions", model_cfg)

    Integration with AgentFactory (production use):
    >>> from asdrp.agents.agent_factory import AgentFactory
    >>> factory = AgentFactory.instance()
    >>> agent = factory.get_agent("perplexity")  # Uses config from open_agents.yaml
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS

    try:
        # Build agent creation arguments
        agent_kwargs: Dict[str, Any] = {
            "name": "PerplexityAgent",
            "instructions": instructions,
            "tools": PerplexityTools.tool_list,  # Use automatically generated tool list
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
            f"Failed to import PerplexityAgent dependencies: {str(e)}. "
            f"Ensure 'agents' library and PerplexityTools are installed.",
            agent_name="perplexity"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create PerplexityAgent: {str(e)}. "
            f"Check that PERPLEXITY_API_KEY is set in environment.",
            agent_name="perplexity"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for PerplexityAgent interactive session.

    Creates a PerplexityAgent and runs an interactive loop where users can
    ask questions, search the web, get AI-powered answers with citations,
    and explore current information in real-time.

    Usage:
    ------
    Run this module directly:
    $ python -m asdrp.agents.single.perplexity_agent

    Example queries:
    - "What are the latest developments in AI?"
    - "Search for quantum computing breakthroughs in the past month"
    - "Explain the impact of climate change"
    - "Find recent news about SpaceX"
    - "Compare different approaches to renewable energy"
    - "What's the current status of fusion energy research?"
    """
    try:
        agent = create_perplexity_agent()

        print(f"\n{'='*70}")
        print(f"  {agent.name} - AI-Powered Research Assistant")
        print(f"{'='*70}")
        print("\nPowered by Perplexity AI - Real-time search with AI reasoning")
        print("\nExamples:")
        print("  - What are the latest AI developments?")
        print("  - Search for quantum computing news from the past week")
        print("  - Explain fusion energy breakthroughs")
        print("  - Find recent academic papers on neural networks")
        print("  - What's happening with SpaceX right now?")
        print("\nFeatures:")
        print("  ✓ Real-time web search")
        print("  ✓ Citation verification")
        print("  ✓ Recency filters (hour, day, week, month, year)")
        print("  ✓ Multiple AI models (sonar, sonar-pro, sonar-reasoning)")
        print("\nType your question below (press Enter on empty line to exit)")
        print(f"{'='*70}\n")

        user_input = input(f"Ask {agent.name}: ").strip()
        while user_input:
            try:
                response = await Runner.run(agent, input=user_input)
                print(f"\n{response.final_output}\n")
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")

            user_input = input(f"Ask {agent.name}: ").strip()

        print("\n👋 Goodbye! Stay curious!\n")

    except AgentException as e:
        print(f"\n❌ Failed to create PerplexityAgent: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PERPLEXITY_API_KEY is set in .env file")
        print("  2. Verify perplexityai package is installed: pip install perplexityai")
        print("  3. Check that all dependencies are installed")
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
