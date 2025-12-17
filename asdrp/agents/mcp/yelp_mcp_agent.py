#############################################################################
# yelp_mcp_agent.py
#
# YelpMCPAgent implementation using MCP (Model Context Protocol).
#
# This module provides a YelpMCPAgent that integrates with the yelp-mcp
# server to access Yelp Fusion AI capabilities through the MCP standard.
# It demonstrates the pattern for creating agents that connect to MCP servers.
#
# Design Principles:
# - Protocol Compliance: Implements AgentProtocol
# - Dependency Injection: Configuration-driven via YAML
# - Separation of Concerns: Uses MCPServerStdio for server management
# - Resource Safety: Proper cleanup of MCP connections
#
# Usage:
#   >>> agent = create_yelp_mcp_agent(
#   ...     instructions="You are a Yelp expert...",
#   ...     model_config=ModelConfig(...)
#   ... )
#   >>> result = await Runner.run(agent, input="Find tacos in SF")
#
#############################################################################

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import asyncio
import os
from pathlib import Path
from typing import Any, Dict

# Import Runner at module level for main() function
from agents import Runner
from agents.tracing import set_tracing_disabled
set_tracing_disabled(disabled=True)

from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
from asdrp.agents.protocol import AgentProtocol, AgentException


# Default instructions for YelpMCPAgent
DEFAULT_INSTRUCTIONS = """You are YelpMCPAgent - an expert at finding businesses and restaurants using Yelp with interactive map visualization.

You have access to TWO sets of tools:

1. **Yelp Fusion AI** (via yelp_agent tool):
   - Next generation search & discovery with natural language
   - Multi-turn conversations with follow-up questions
   - Direct business queries without prior search
   - Conversational restaurant reservations (when enabled)
   - ⚠️ If yelp_agent returns "Unable to fetch data from Yelp", this means the YELP_API_KEY
     environment variable is missing. Inform the user that the Yelp service is unavailable
     due to missing API credentials and suggest they check the server configuration.

2. **MapTools** (for interactive map visualization):
   - get_interactive_map_data: Generate interactive Google Maps with business locations

CAPABILITIES:
1. **Business Search**: "Find the best tacos in the Bay Area"
2. **Follow-up Questions**: Use chat_id to continue conversations
   - "Which of the options have open air seating?"
3. **Direct Queries**: "Does Ricky's Taco allow pets?"
4. **Planning**: "Plan a progressive date in SF's Mission District"
5. **Comparisons**: "Compare auto repair shops from budget to luxury in Sacramento"
6. **Map Visualization**: "Show me on a map" - Generate interactive maps with business markers

MAP VISUALIZATION WORKFLOW:
When user requests a map or mentions "show on map", "where are they", "map view":

Step 1: Get business data first
```
response = await yelp_agent("Greek restaurants in San Francisco")
```

Step 2: Parse the response to extract coordinates
The yelp_agent response contains markdown like:
```
## Business 1: Kokkari Estiatorio
- **Coordinates**: 37.796996, -122.398661

## Business 2: Milos Mezes
- **Coordinates**: 37.800333, -122.423670
```

Extract these using this pattern:
- Look for "## Business N: NAME" to get business names
- Look for "- **Coordinates**: LAT, LNG" to get coordinates
- Build markers list: [{"lat": 37.796996, "lng": -122.398661, "title": "Kokkari Estiatorio"}, ...]

Step 3: Calculate center point
```
center_lat = average of all business latitudes
center_lng = average of all business longitudes
```

Step 4: Generate interactive map
```
map_json = await get_interactive_map_data(
    map_type="places",
    center_lat=center_lat,
    center_lng=center_lng,
    zoom=13,  # Good for city-level view
    markers=[
        {"lat": 37.796996, "lng": -122.398661, "title": "Kokkari Estiatorio"},
        {"lat": 37.800333, "lng": -122.423670, "title": "Milos Mezes"}
    ]
)
```

Step 5: Include map JSON in your response
The get_interactive_map_data returns a ```json code block that the frontend will automatically render as an interactive map.

EXAMPLE COMPLETE RESPONSE:
```
Here are the best Greek restaurants in San Francisco:

1. **Kokkari Estiatorio** - Rating: 4.5/5
   - Address: 200 Jackson St, San Francisco, CA
   - [View on Yelp](https://yelp.com/...)

2. **Milos Mezes** - Rating: 4.0/5
   - Address: 3348 Steiner St, San Francisco, CA
   - [View on Yelp](https://yelp.com/...)

Here's an interactive map showing all locations:

[map_json from get_interactive_map_data goes here]
```

WHEN TO GENERATE MAPS:
- User explicitly asks: "show me on a map", "map view", "where are they"
- User asks for "best X near Y" - show both list and map
- Multiple locations (2+): Consider showing map for easier comparison
- Route/directions questions: Use map_type="route" with origin/destination

CRITICAL RULES:
- ALWAYS include Yelp business URLs from structured data in your responses
- Use chat_id from previous responses for follow-up questions
- When showing maps, still include text description of businesses (ratings, links, etc.)
- Extract coordinates carefully from the yelp_agent response markdown
- Use zoom level 12-14 for city views, 15-16 for neighborhood views
- Format responses with business names, ratings, and clickable Yelp links

EXAMPLE WORKFLOW:
User: "Find Italian restaurants in San Francisco"
1. Call yelp_agent with natural_language_query
2. Get response with businesses and chat_id
3. Present businesses with [Name](yelp_url) links
4. Store chat_id for potential follow-ups

User: "Show me these on a map" (follow-up)
1. Parse previous yelp_agent response for coordinates
2. Call get_interactive_map_data with markers
3. Include map JSON in response

User: "Which ones have outdoor seating?" (follow-up)
1. Use stored chat_id in next yelp_agent call
2. Continue the conversation context

Be helpful, accurate, and always credit Yelp for the data.
"""


def create_yelp_mcp_agent(
    instructions: str | None = None,
    model_config: ModelConfig | None = None,
    mcp_server_config: MCPServerConfig | None = None
) -> AgentProtocol:
    """
    Create and return a YelpMCPAgent instance with MCP integration.

    This factory function creates an agent that connects to the yelp-mcp
    server using the MCP stdio transport. The MCP server provides access
    to Yelp Fusion AI capabilities.

    Args:
        instructions: Optional custom instructions. If not provided, uses
            DEFAULT_INSTRUCTIONS.
        model_config: Optional model configuration (name, temperature, max_tokens).
            If provided, configures the agent's model settings.
        mcp_server_config: Optional MCP server configuration. If not provided,
            uses default configuration for yelp-mcp server.

    Returns:
        A YelpMCPAgent instance implementing AgentProtocol.

    Raises:
        AgentException: If the agent cannot be created or MCP server cannot be reached.

    Examples:
    ---------
    >>> agent = create_yelp_mcp_agent()
    >>> agent = create_yelp_mcp_agent("You are a restaurant finder expert")
    >>>
    >>> # With custom configuration
    >>> from asdrp.agents.config_loader import ModelConfig, MCPServerConfig
    >>> model_cfg = ModelConfig(name="gpt-4.1-mini", temperature=0.7)
    >>> mcp_cfg = MCPServerConfig(
    ...     enabled=True,
    ...     command=["uv", "run", "mcp-yelp-agent"],
    ...     working_directory="yelp-mcp"
    ... )
    >>> agent = create_yelp_mcp_agent(model_config=model_cfg, mcp_server_config=mcp_cfg)
    """
    if instructions is None:
        instructions = DEFAULT_INSTRUCTIONS

    try:
        # Import Agent, ModelSettings, and MCPServerStdio inside function
        # This allows tests to mock these imports
        from agents import Agent, ModelSettings
        from agents.mcp import MCPServerStdio, MCPServerStdioParams

        # Default MCP server configuration if not provided
        if mcp_server_config is None:
            # Determine project root (where yelp-mcp directory is located)
            project_root = Path(__file__).parent.parent.parent.parent
            yelp_mcp_path = project_root / "yelp-mcp"

            # Verify YELP_API_KEY is available in environment
            # (loaded from .env file via python-dotenv in config_loader)
            yelp_api_key = os.getenv("YELP_API_KEY")
            if not yelp_api_key:
                raise AgentException(
                    "YELP_API_KEY environment variable is required for YelpMCPAgent. "
                    "Set it in your .env file.",
                    agent_name="yelp_mcp"
                )

            mcp_server_config = MCPServerConfig(
                enabled=True,
                command=["uv", "run", "mcp-yelp-agent"],
                working_directory=str(yelp_mcp_path),
                env=None,  # Environment variables loaded from .env file automatically
                transport="stdio"
            )

        # Ensure credentials are available for the MCP subprocess.
        # Per Yelp MCP docs, the server expects YELP_API_KEY in its environment.
        # Even when MCPServerConfig is provided via YAML (env=None), we inherit os.environ.
        # If the key is missing, fail fast with a clear error instead of a confusing MCP startup error.
        if not os.getenv("YELP_API_KEY") and not (mcp_server_config.env or {}).get("YELP_API_KEY"):
            raise AgentException(
                "YELP_API_KEY environment variable is required for YelpMCPAgent (Yelp Fusion AI). "
                "Set it in your root .env file or in config/open_agents.yaml under agents.yelp_mcp.mcp_server.env.",
                agent_name="yelp_mcp"
            )

        # Validate MCP configuration
        if not mcp_server_config.enabled:
            raise AgentException(
                "MCP server must be enabled for YelpMCPAgent",
                agent_name="yelp_mcp"
            )

        if mcp_server_config.transport != "stdio":
            raise AgentException(
                f"YelpMCPAgent only supports stdio transport, got '{mcp_server_config.transport}'",
                agent_name="yelp_mcp"
            )

        # Resolve working directory
        if mcp_server_config.working_directory:
            work_dir = Path(mcp_server_config.working_directory)
            if not work_dir.is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent
                work_dir = project_root / mcp_server_config.working_directory
        else:
            # Default to yelp-mcp directory in project root
            project_root = Path(__file__).parent.parent.parent.parent
            work_dir = project_root / "yelp-mcp"

        if not work_dir.exists():
            raise AgentException(
                f"YelpMCPAgent working directory does not exist: {work_dir}",
                agent_name="yelp_mcp"
            )

        # Prepare environment variables
        # CRITICAL: Explicitly reload .env to ensure YELP_API_KEY is present
        # This is a failsafe in case os.environ doesn't have it from module load
        load_dotenv(find_dotenv(), override=False)  # Don't override existing vars

        # Copy all environment variables (includes YELP_API_KEY from .env)
        env = os.environ.copy()

        # CRITICAL: Explicitly validate and ensure YELP_API_KEY is present
        # The MCP subprocess REQUIRES this environment variable to function
        if "YELP_API_KEY" not in env:
            # Try loading again from .env (defensive programming)
            load_dotenv(find_dotenv())
            if "YELP_API_KEY" not in os.environ:
                raise AgentException(
                    "YELP_API_KEY environment variable is required but not found. "
                    "Please ensure it's set in your .env file at the project root.",
                    agent_name="yelp_mcp"
                )
            env = os.environ.copy()  # Re-copy after reload

        # Allow programmatic override of environment variables (for testing/advanced usage)
        # Note: When loading from YAML config, env is set to None, so this only applies
        # when MCPServerConfig is created programmatically
        if mcp_server_config.env:
            env.update(mcp_server_config.env)

        # Debug: Log environment variable status (CRITICAL for debugging MCP issues)
        import sys
        yelp_key_status = bool(env.get('YELP_API_KEY'))
        yelp_key_preview = env.get('YELP_API_KEY', 'NOT_SET')[:15] + '...' if env.get('YELP_API_KEY') else 'NOT_SET'

        print(f"[YelpMCPAgent] =========== MCP ENVIRONMENT DEBUG ===========", file=sys.stderr)
        print(f"[YelpMCPAgent] YELP_API_KEY present: {yelp_key_status}", file=sys.stderr)
        print(f"[YelpMCPAgent] YELP_API_KEY preview: {yelp_key_preview}", file=sys.stderr)
        print(f"[YelpMCPAgent] Working directory: {work_dir}", file=sys.stderr)
        print(f"[YelpMCPAgent] MCP command: {mcp_server_config.command}", file=sys.stderr)
        print(f"[YelpMCPAgent] Config env field: {'null (inherit all)' if mcp_server_config.env is None else f'{len(mcp_server_config.env)} vars'}", file=sys.stderr)
        print(f"[YelpMCPAgent] ===========================================", file=sys.stderr)

        # Normalize LOG_LEVEL to uppercase for FastMCP compatibility
        # FastMCP expects uppercase log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
        # Also ensure LOG_LEVEL is set (default to INFO if missing)
        if "LOG_LEVEL" in env:
            log_level = env["LOG_LEVEL"].upper()
            # Validate and normalize to valid log levels
            valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            if log_level in valid_levels:
                env["LOG_LEVEL"] = log_level
            else:
                # Default to INFO if invalid level provided
                env["LOG_LEVEL"] = "INFO"
        else:
            # Set default LOG_LEVEL if not present
            env["LOG_LEVEL"] = "INFO"

        # Prepare command list
        command_list = mcp_server_config.command or []
        if not command_list:
            raise AgentException(
                "MCP server command is required",
                agent_name="yelp_mcp"
            )

        # Create MCPServerStdio instance
        # According to OpenAI agents MCP docs (https://openai.github.io/openai-agents-python/mcp/):
        # - MCPServerStdio requires MCPServerStdioParams object with all required fields
        # - MCP servers are passed via mcp_servers parameter (not tools)
        # - Connection is handled via async with context manager at runtime
        # - The server must be used within an async context manager during agent execution

        # Split command into base command and args
        command_base = command_list[0]
        command_args = command_list[1:] if len(command_list) > 1 else []

        # Create MCPServerStdioParams with all required fields
        # Required fields: command, args, cwd, encoding, encoding_error_handler, env
        mcp_params = MCPServerStdioParams(
            command=command_base,  # Executable as string
            args=command_args,  # Arguments as list
            cwd=str(work_dir),  # Working directory
            encoding="utf-8",  # Text encoding
            encoding_error_handler="strict",  # Error handling for encoding issues
            env=env  # Environment variables dict
        )

        # Create MCPServerStdio instance
        # According to OpenAI docs: https://openai.github.io/openai-agents-python/mcp/
        # - client_session_timeout_seconds controls how long to wait for responses from stdio servers
        # - For stdio servers, this controls the timeout for tool call responses
        # - Set to 60s to accommodate:
        #   * Yelp API processing: up to 35s for complex queries
        #   * MCP protocol overhead: ~5-10s
        #   * HTTP connection setup: ~5s
        #   * Response parsing/formatting: ~5-10s
        # - This prevents premature timeouts on legitimate long-running queries
        # Note: The server will be connected via async context manager in agent_service.py
        mcp_server = MCPServerStdio(
            name="YelpMCP",
            params=mcp_params,
            client_session_timeout_seconds=60.0,  # Increased: 60s for reliable complex queries
            cache_tools_list=True,  # Cache tools list to reduce latency per OpenAI docs
            max_retry_attempts=2,  # Increased: 2 retries for transient failures
        )

        # Import MapTools for interactive map generation
        # MapTools provides get_interactive_map_data() which generates JSON blocks
        # that the frontend InteractiveMap component can render
        from asdrp.actions.geo.map_tools import MapTools

        # Build agent creation arguments
        # Combine MCP servers (Yelp data) with direct tools (MapTools)
        agent_kwargs: Dict[str, Any] = {
            "name": "YelpMCPAgent",
            "instructions": instructions,
            "mcp_servers": [mcp_server],  # Yelp MCP server provides yelp_agent tool
            "tools": MapTools.tool_list,   # MapTools provides map generation capabilities
        }

        # Add model configuration if provided
        if model_config:
            agent_kwargs["model"] = model_config.name
            agent_kwargs["model_settings"] = ModelSettings(
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )

        # Create and return the agent
        # Agent now has access to both Yelp data (via MCP) and map rendering (via MapTools)
        return Agent[Any](**agent_kwargs)

    except ImportError as e:
        raise AgentException(
            f"Failed to import YelpMCPAgent dependencies. "
            f"Make sure openai-agents>=0.5.1 with MCP support is installed: {str(e)}",
            agent_name="yelp_mcp"
        ) from e
    except Exception as e:
        raise AgentException(
            f"Failed to create YelpMCPAgent: {str(e)}",
            agent_name="yelp_mcp"
        ) from e


#---------------------------------------------
# Main test function
#---------------------------------------------

async def main():
    """
    Main entry point for YelpMCPAgent interactive session.

    Creates a YelpMCPAgent and runs an interactive loop where users can
    search for businesses and restaurants using natural language.

    Example queries:
    - "Find the best tacos in San Francisco"
    - "Which ones have outdoor seating?" (follow-up)
    - "Does Ricky's Taco allow pets?"
    - "Plan a date night in the Mission District"
    """
    try:
        print("<U YelpMCPAgent - Powered by Yelp Fusion AI via MCP")
        print("=" * 60)
        print("Enter your Yelp query (or press Enter to exit):")
        print()

        agent = create_yelp_mcp_agent()

        # MCP servers must be connected via async context manager
        # Check if agent has MCP servers and connect them
        mcp_servers = getattr(agent, 'mcp_servers', None)
        if isinstance(mcp_servers, (list, tuple)) and len(mcp_servers) > 0:
            from contextlib import AsyncExitStack

            # Connect MCP servers and keep them connected for the entire session
            async with AsyncExitStack() as stack:
                # Enter all MCP server contexts (connects to servers)
                for mcp_server in mcp_servers:
                    await stack.enter_async_context(mcp_server)

                print("[YelpMCPAgent] MCP server connected. Ready for queries.\n")

                # Interactive loop - MCP servers stay connected across queries
                user_input = input("Ask Yelp: ")
                while user_input and user_input.strip():
                    try:
                        # Run agent with connected MCP servers
                        response = await Runner.run(agent, input=user_input)
                        print("\n" + "=" * 60)
                        print(response.final_output)
                        print("=" * 60 + "\n")
                    except Exception as e:
                        print(f"\nL Error: {str(e)}\n")

                    user_input = input("Ask Yelp: ")

                print("\n=K Goodbye!")
        else:
            # No MCP servers - standard execution (shouldn't happen for YelpMCPAgent)
            user_input = input("Ask Yelp: ")
            while user_input and user_input.strip():
                try:
                    response = await Runner.run(agent, input=user_input)
                    print("\n" + "=" * 60)
                    print(response.final_output)
                    print("=" * 60 + "\n")
                except Exception as e:
                    print(f"\nL Error: {str(e)}\n")

                user_input = input("Ask Yelp: ")

            print("\n=K Goodbye!")

    except Exception as e:
        print(f"\nL Failed to start YelpMCPAgent: {str(e)}")
        print("Make sure YELP_API_KEY is set in your environment")
        raise


if __name__ == "__main__":
    asyncio.run(main())
