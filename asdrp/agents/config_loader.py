#############################################################################
# config_loader.py
#
# Agent configuration loader from YAML files.
#
# This module provides:
# - AgentConfigLoader: Class for loading and managing agent configurations
# - ModelConfig: Dataclass for model settings (name, temperature, max_tokens)
# - SessionMemoryConfig: Dataclass for session memory settings
# - AgentConfig: Dataclass combining all agent configuration
# - Configuration validation and error handling
# - Default value handling
# - Type-safe configuration access
#
# Session Memory Support:
# - SQLite-based session storage (in-memory or file-based)
# - Configurable per-agent or via global defaults
# - Enables conversation history across multiple agent runs
#
# Design Principles:
# - Single Responsibility: Only responsible for config loading and access
# - Separation of Concerns: Config loading separate from agent creation
# - DRY: Centralized config access
# - Extensibility: Easy to add new config parameters
#
# Usage:
#   >>> from asdrp.agents.config_loader import AgentConfigLoader
#   >>> loader = AgentConfigLoader()
#   >>> config = loader.get_agent_config("geo")
#   >>> print(config.session_memory.type)  # "sqlite"
#
#############################################################################

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv

from asdrp.agents.protocol import AgentException


@dataclass
class ModelConfig:
    """
    Configuration for agent model settings.
    
    Attributes:
    -----------
    name : str
        Model identifier (e.g., "gpt-4.1", "gpt-4.1-mini").
    temperature : float
        Temperature setting (0.0-2.0). Higher values make output more random.
    max_tokens : int
        Maximum tokens for responses.
    """
    name: str
    temperature: float = 0.7
    max_tokens: int = 2000
    
    def __post_init__(self):
        """Validate model configuration values."""
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {self.temperature}")
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")


@dataclass
class SessionMemoryConfig:
    """
    Configuration for agent session memory.
    
    The openai-agents SDK provides built-in session memory to maintain 
    conversation history across multiple agent runs. This configuration
    controls how session memory is initialized and managed.
    
    Supported session types:
    - "sqlite": SQLite-based session storage (default)
        - Can be in-memory (ephemeral) or file-based (persistent)
        - Lightweight and requires no external dependencies
    - "none": No session memory (stateless agent)
    
    Attributes:
    -----------
    type : str
        Session type: "sqlite" or "none". Default is "sqlite".
    session_id : str | None
        Optional session identifier. If None, a default session ID is generated.
        Useful for maintaining separate conversation histories.
    database_path : str | None
        Path to SQLite database file. If None or ":memory:", uses in-memory storage.
        Use a file path for persistent storage across application restarts.
    enabled : bool
        Whether session memory is enabled. Default is True.
    """
    type: str = "sqlite"
    session_id: Optional[str] = None
    database_path: Optional[str] = None
    enabled: bool = True
    
    def __post_init__(self):
        """Validate session memory configuration values."""
        valid_types = {"sqlite", "none"}
        if self.type not in valid_types:
            raise ValueError(f"Session type must be one of {valid_types}, got '{self.type}'")


@dataclass
class MCPServerConfig:
    """
    Configuration for MCP (Model Context Protocol) server integration.

    MCP servers provide external tools and resources that agents can use.
    This configuration specifies how to connect to an MCP server.

    Attributes:
    -----------
    enabled : bool
        Whether MCP server integration is enabled for this agent.
    command : list[str]
        Command to start the MCP server (e.g., ["uv", "run", "mcp-yelp-agent"]).
    working_directory : str | None
        Working directory for the MCP server process. If None, uses project root.
    env : dict[str, str] | None
        Environment variables to override/add when creating MCP server programmatically.
        When loading from YAML config, this field is set to None and ignored.
        For YAML configs, set environment variables in .env file instead.
        This field is primarily for programmatic usage (tests, advanced configurations).
    transport : str
        Transport protocol: "stdio" (default), "streamable-http", or "sse".
    host : str | None
        Host for HTTP/SSE transports (ignored for stdio).
    port : int | None
        Port for HTTP/SSE transports (ignored for stdio).
    """
    enabled: bool = False
    command: list[str] | None = None
    working_directory: str | None = None
    env: dict[str, str] | None = None
    transport: str = "stdio"
    host: str | None = None
    port: int | None = None

    def __post_init__(self):
        """Validate MCP server configuration values."""
        valid_transports = {"stdio", "streamable-http", "sse"}
        if self.transport not in valid_transports:
            raise ValueError(
                f"MCP transport must be one of {valid_transports}, got '{self.transport}'"
            )

        if self.enabled and not self.command:
            raise ValueError("MCP server command is required when MCP is enabled")

        if self.transport in {"streamable-http", "sse"} and (not self.host or not self.port):
            raise ValueError(
                f"MCP host and port are required for {self.transport} transport"
            )


@dataclass
class AgentConfig:
    """
    Configuration for a single agent type.

    Attributes:
    -----------
    display_name : str
        Human-readable name for the agent.
    module : str
        Python module path where the creation function is located.
    function : str
        Name of the function to call for creating the agent.
    default_instructions : str
        Default system instructions for the agent.
    model : ModelConfig
        Model configuration settings.
    session_memory : SessionMemoryConfig
        Session memory configuration for maintaining conversation history.
    mcp_server : MCPServerConfig | None
        Optional MCP server configuration for external tool integration.
    enabled : bool
        Whether this agent is enabled and available for use.
    """
    display_name: str
    module: str
    function: str
    default_instructions: str
    model: ModelConfig
    session_memory: SessionMemoryConfig
    mcp_server: MCPServerConfig | None = None
    enabled: bool = True


class AgentConfigLoader:
    """
    Loader for agent configurations from YAML files.
    
    This class handles loading, parsing, and validating agent configurations
    from YAML files. It provides type-safe access to configuration values
    and handles default values.
    
    Usage:
    ------
    >>> loader = AgentConfigLoader()
    >>> config = loader.get_agent_config("geo")
    >>> print(config.display_name)  # "GeoAgent"
    >>> print(config.model.temperature)  # 0.7
    
    Attributes:
    -----------
    _config_path : Path
        Path to the configuration file.
    _config_data : Dict[str, Any] | None
        Cached configuration data (loaded lazily).
    """
    
    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize AgentConfigLoader.
        
        Loads environment variables from .env file using python-dotenv.
        Environment variables are automatically available via os.environ
        and should not be specified in the YAML configuration file.
        
        Args:
            config_path: Path to the YAML configuration file. If None, uses
                default path: config/open_agents.yaml relative to project root.
        
        Raises:
            AgentException: If config file cannot be found or loaded.
        """
        # Load environment variables from .env file
        # This makes all environment variables available via os.environ
        load_dotenv(find_dotenv())
        
        if config_path is None:
            # Default to config/open_agents.yaml relative to project root
            # Find project root by looking for config directory
            current_dir = Path(__file__).parent.parent.parent
            config_path = current_dir / "config" / "open_agents.yaml"
        
        self._config_path = Path(config_path)
        self._config_data: Dict[str, Any] | None = None
        
        # Validate config file exists
        if not self._config_path.exists():
            raise AgentException(
                f"Configuration file not found: {self._config_path}",
                agent_name=None
            )
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load and parse the YAML configuration file.
        
        Returns:
            Parsed configuration dictionary.
        
        Raises:
            AgentException: If config file cannot be parsed or is invalid.
        """
        if self._config_data is not None:
            return self._config_data
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f)
            
            if not isinstance(self._config_data, dict):
                raise AgentException(
                    f"Invalid configuration file format: expected dict, got {type(self._config_data)}",
                    agent_name=None
                )
            
            # Validate required top-level keys
            if 'agents' not in self._config_data:
                raise AgentException(
                    "Configuration file missing required 'agents' section",
                    agent_name=None
                )
            
            return self._config_data
            
        except yaml.YAMLError as e:
            raise AgentException(
                f"Failed to parse YAML configuration file: {str(e)}",
                agent_name=None
            ) from e
        except Exception as e:
            raise AgentException(
                f"Failed to load configuration file: {str(e)}",
                agent_name=None
            ) from e
    
    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent (case-insensitive).
        
        Returns:
            AgentConfig object with agent configuration.
        
        Raises:
            AgentException: If agent is not found or configuration is invalid.
        """
        config_data = self._load_config()
        normalized_name = agent_name.lower().strip()
        
        agents = config_data.get('agents', {})
        if normalized_name not in agents:
            valid_names = ", ".join(sorted(agents.keys()))
            raise AgentException(
                f"Agent '{agent_name}' not found in configuration. Valid agents: {valid_names}",
                agent_name=agent_name
            )
        
        agent_data = agents[normalized_name]
        
        # Get defaults
        defaults = config_data.get('defaults', {})
        default_model = defaults.get('model', {})
        
        # Extract model config (use agent-specific or default)
        model_data = agent_data.get('model', default_model)
        model_config = ModelConfig(
            name=model_data.get('name', default_model.get('name', 'gpt-4')),
            temperature=model_data.get('temperature', default_model.get('temperature', 0.7)),
            max_tokens=model_data.get('max_tokens', default_model.get('max_tokens', 2000))
        )
        
        # Extract session memory config (use agent-specific or default)
        default_session = defaults.get('session_memory', {})
        session_data = agent_data.get('session_memory', default_session)
        session_memory_config = SessionMemoryConfig(
            type=session_data.get('type', default_session.get('type', 'sqlite')),
            session_id=session_data.get('session_id', default_session.get('session_id')),
            database_path=session_data.get('database_path', default_session.get('database_path')),
            enabled=session_data.get('enabled', default_session.get('enabled', True))
        )

        # Extract MCP server config (optional, no defaults)
        mcp_server_config = None
        if 'mcp_server' in agent_data:
            mcp_data = agent_data['mcp_server']
            # Note: env field is deprecated - environment variables are loaded
            # automatically from .env file via python-dotenv in __init__
            mcp_server_config = MCPServerConfig(
                enabled=mcp_data.get('enabled', False),
                command=mcp_data.get('command'),
                working_directory=mcp_data.get('working_directory'),
                env=None,  # Environment variables loaded from .env file automatically
                transport=mcp_data.get('transport', 'stdio'),
                host=mcp_data.get('host'),
                port=mcp_data.get('port')
            )

        # Build AgentConfig
        try:
            return AgentConfig(
                display_name=agent_data.get('display_name', agent_name.title()),
                module=agent_data['module'],
                function=agent_data['function'],
                default_instructions=agent_data.get('default_instructions', ''),
                model=model_config,
                session_memory=session_memory_config,
                mcp_server=mcp_server_config,
                enabled=agent_data.get('enabled', True)
            )
        except KeyError as e:
            raise AgentException(
                f"Missing required configuration key '{e.args[0]}' for agent '{agent_name}'",
                agent_name=agent_name
            ) from e
    
    def list_agents(self) -> list[str]:
        """
        List all available agent names from configuration.
        
        Returns:
            List of agent names (normalized to lowercase).
        """
        config_data = self._load_config()
        agents = config_data.get('agents', {})
        return [name for name in agents.keys() if agents[name].get('enabled', True)]
    
    def is_agent_enabled(self, agent_name: str) -> bool:
        """
        Check if an agent is enabled.
        
        Args:
            agent_name: Name of the agent (case-insensitive).
        
        Returns:
            True if agent exists and is enabled, False otherwise.
        """
        try:
            config = self.get_agent_config(agent_name)
            return config.enabled
        except AgentException:
            return False
    
    def reload_config(self) -> None:
        """
        Reload configuration from file.
        
        Useful for testing or when configuration file is updated at runtime.
        """
        self._config_data = None

