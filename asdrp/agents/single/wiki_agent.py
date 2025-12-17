#############################################################################
# wiki_agent.py
#
# WikiAgent implementation using the Agent protocol.
#
# This module provides a WikiAgent that implements AgentProtocol and uses
# Wikipedia tools for knowledge retrieval, search, and content exploration.
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import Any, Dict
import asyncio

from agents import Agent, ModelSettings, Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.actions.search.wiki_tools import WikiTools
from asdrp.agents.config_loader import ModelConfig
from asdrp.agents.protocol import AgentProtocol, AgentException

# Default instructions for WikiAgent (kept for backward compatibility)
# Note: Default instructions should come from config file in production use
DEFAULT_INSTRUCTIONS = """You are WikiAgent - an expert knowledge assistant powered by Wikipedia.

AVAILABLE TOOLS:
- **search**: Find Wikipedia articles by keywords
- **get_page_summary**: Get quick overviews (configurable sentence count)
- **get_page_content**: Retrieve full article content with sections
- **get_page_section**: Extract specific sections from articles
- **get_page_images**: List image URLs from pages
- **get_page_links**: Find linked Wikipedia articles
- **set_language**: Switch between Wikipedia language editions
- **get_random_page**: Get random Wikipedia page titles

USAGE GUIDELINES:
- Use search() to find articles, then get_page_summary() for quick overviews
- Use get_page_content() for detailed information, get_page_section() for specific parts
- For disambiguation, list all options and suggest the most relevant
- Format citations as [Article Title](wikipedia_url) and include Wikipedia links
- Provide image URLs as clickable links: [View Image](url) - DO NOT use markdown image syntax
- Use structured markdown: ## headings, **bold** for key terms, bullet points for lists
- Use set_language() when users request other languages

Always provide accurate, well-cited information with proper Wikipedia attribution.
"""


def create_wiki_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None
) -> AgentProtocol:
    """
    Create and return a WikiAgent instance.

    This is the public factory function for creating WikiAgent instances.
    It is used by AgentFactory and can also be called directly.

    The WikiAgent provides comprehensive Wikipedia access through WikiTools,
    enabling knowledge search, article retrieval, content extraction, and
    multi-language support. It follows SOLID principles with dependency injection,
    protocol-based design, and separation of concerns.

    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS optimized for Wikipedia operations.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
            Recommended settings:
            - temperature: 0.7 (balanced creativity and accuracy)
            - max_tokens: 2000 (sufficient for detailed articles)

    Returns:
        A WikiAgent instance implementing AgentProtocol.

    Raises:
        AgentException: If the agent cannot be created due to:
            - Missing dependencies (agents library, WikiTools)
            - Invalid configuration
            - Import errors

    Examples:
    ---------
    Basic usage:
    >>> agent = create_wiki_agent()
    >>> # Agent ready with default Wikipedia-optimized instructions

    Custom instructions:
    >>> agent = create_wiki_agent("You are a research assistant specializing in history")

    Custom model configuration:
    >>> from asdrp.agents.config_loader import ModelConfig
    >>> model_cfg = ModelConfig(name="gpt-4", temperature=0.5, max_tokens=3000)
    >>> agent = create_wiki_agent("Custom instructions", model_cfg)

    Integration with AgentFactory (production use):
    >>> from asdrp.agents.agent_factory import AgentFactory
    >>> factory = AgentFactory.instance()
    >>> agent = factory.get_agent("wiki")  # Uses config from open_agents.yaml
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS

    try:
        # Build agent creation arguments
        agent_kwargs: Dict[str, Any] = {
            "name": "WikiAgent",
            "instructions": instructions,
            "tools": WikiTools.tool_list,  # Use automatically generated tool list
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
            f"Failed to import WikiAgent dependencies: {str(e)}. "
            f"Ensure 'agents' library and WikiTools are installed.",
            agent_name="wiki"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create WikiAgent: {str(e)}",
            agent_name="wiki"
        ) from e


#---------------------------------------------
# main tests
#---------------------------------------------

async def main():
    """
    Main entry point for WikiAgent interactive session.

    Creates a WikiAgent and runs an interactive loop where users can
    ask questions about any Wikipedia topic, search for articles,
    get summaries, explore content, and more.

    Usage:
    ------
    Run this module directly:
    $ python -m asdrp.agents.single.wiki_agent

    Example queries:
    - "Tell me about artificial intelligence"
    - "Search for quantum mechanics"
    - "Give me a summary of Albert Einstein's page"
    - "What are the sections in the Python programming language article?"
    - "Show me images from the Mars article"
    - "Search for machine learning in Spanish"
    """
    try:
        agent = create_wiki_agent()

        print(f"\n{'='*70}")
        print(f"  {agent.name} - Wikipedia Knowledge Assistant")
        print(f"{'='*70}")
        print("\nExamples:")
        print("  - Tell me about quantum computing")
        print("  - Search for machine learning")
        print("  - Get a summary of photosynthesis")
        print("  - What sections are in the Python programming article?")
        print("  - Show me images from the Eiffel Tower page")
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

        print("\n👋 Goodbye! Happy learning!\n")

    except AgentException as e:
        print(f"\n❌ Failed to create WikiAgent: {e}")
        print("Ensure all dependencies are installed and configured correctly.")
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
