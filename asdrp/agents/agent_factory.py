#############################################################################
# agent_factory.py
#
# AgentFactory class for creating agent instances with session memory support.
#
# This module provides:
# - AgentFactory: A factory class following the Factory pattern
# - Centralized agent creation logic
# - Agent registry management
# - Session memory initialization and caching
# - Error handling and validation
# - Convenience functions: get_agent(), get_agent_with_session()
#
# Session Memory Support:
# - Automatic session creation based on YAML configuration
# - SQLite-based sessions (in-memory or file-based)
# - Session caching for reuse across calls
# - Session ID override for multi-user/multi-thread scenarios
#
# Design Principles:
# - Single Responsibility: Factory is responsible only for agent creation
# - Open/Closed: Easy to extend with new agent types
# - Dependency Inversion: Depends on agent modules, not concrete implementations
# - Separation of Concerns: Agent-specific creation logic in respective modules
#
# Usage:
#   >>> from asdrp.agents.agent_factory import get_agent_with_session
#   >>> agent, session = await get_agent_with_session("geo")
#   >>> from agents import Runner
#   >>> result = await Runner.run(agent, input="Hello", session=session)
#
#############################################################################

from typing import Dict, Callable, Any, Optional, Tuple
from pathlib import Path
from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.config_loader import AgentConfigLoader, AgentConfig, SessionMemoryConfig

# Import session memory types from openai-agents SDK
try:
    from agents import SQLiteSession
    SESSION_MEMORY_AVAILABLE = True
except ImportError:
    SESSION_MEMORY_AVAILABLE = False
    SQLiteSession = None

class AgentFactory:
    """
    Factory class for creating agent instances with optional session memory.
    
    This class implements the Factory pattern to provide a centralized way
    to create different types of agents. It maintains a registry of agent
    creation functions and handles validation and error handling.
    
    Session Memory Support:
    ----------------------
    The factory automatically initializes session memory for agents based on
    configuration. Session memory maintains conversation history across multiple
    agent runs using the openai-agents SDK's built-in session support.
    
    Supported session types:
    - "sqlite": SQLite-based storage (in-memory or file-based)
    - "none": No session memory (stateless)
    
    The factory follows SOLID principles:
    - Single Responsibility: Only responsible for agent creation
    - Open/Closed: Open for extension (new agents), closed for modification
    - Dependency Inversion: Depends on abstractions (protocol), not concretions
    
    Usage:
    ------
    >>> factory = AgentFactory()
    >>> agent, session = await factory.get_agent_with_session("geo", "You are a geocoding assistant")
    >>> # Use session with Runner.run(agent, input=..., session=session)
    
    Or use the singleton instance:
    >>> agent, session = await AgentFactory.instance().get_agent_with_session("geo", "Instructions")
    
    Attributes:
    -----------
    _registry : Dict[str, Callable[[str], AgentProtocol]]
        Internal registry mapping agent names to their creation functions.
        This is populated lazily to avoid circular dependencies.
    _session_cache : Dict[str, Any]
        Cache of session objects keyed by session identifier.
    """
    
    _instance: 'AgentFactory | None' = None
    _registry: Dict[str, Callable[[str], AgentProtocol]] | None = None
    _config_loader: Optional[AgentConfigLoader] = None
    _session_cache: Dict[str, Any] | None = None
    
    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize AgentFactory.
        
        Creates a new factory instance. For most use cases, consider using
        AgentFactory.instance() to get the singleton instance.
        
        Args:
            config_path: Optional path to configuration YAML file. If None, uses
                default config path.
        """
        self._registry = None
        self._config_loader = None
        self._config_path = config_path
        self._session_cache: Dict[str, Any] = {}
    
    @classmethod
    def instance(cls) -> 'AgentFactory':
        """
        Get the singleton instance of AgentFactory.
        
        Returns:
            The singleton AgentFactory instance.
        
        Examples:
        ---------
        >>> factory = AgentFactory.instance()
        >>> agent = await factory.get_agent("geo", "Instructions")
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _get_config_loader(self) -> AgentConfigLoader:
        """
        Get or initialize the configuration loader.
        
        Returns:
            AgentConfigLoader instance.
        """
        if self._config_loader is None:
            self._config_loader = AgentConfigLoader(self._config_path)
        return self._config_loader
    
    def _create_session(
        self, 
        session_config: SessionMemoryConfig,
        agent_name: str
    ) -> Any:
        """
        Create a session object based on configuration.
        
        This method creates and caches session objects for agents. Sessions
        are cached by their session_id to allow reuse across multiple calls.
        
        Args:
            session_config: Session memory configuration from agent config.
            agent_name: Name of the agent (used for default session_id).
        
        Returns:
            A session object (SQLiteSession or None for stateless agents).
        
        Raises:
            AgentException: If session type is unsupported or creation fails.
        """
        if not session_config.enabled or session_config.type == "none":
            return None
        
        if not SESSION_MEMORY_AVAILABLE:
            # Session memory not available in this version of openai-agents
            return None
        
        # Determine session ID (use agent name if not specified)
        session_id = session_config.session_id or f"{agent_name}_session"
        
        # Check cache first
        cache_key = f"{session_config.type}:{session_id}:{session_config.database_path or ':memory:'}"
        if cache_key in self._session_cache:
            return self._session_cache[cache_key]
        
        try:
            if session_config.type == "sqlite":
                # Create SQLite session
                # If database_path is None or empty, use in-memory storage
                if session_config.database_path:
                    # Ensure parent directory exists for file-based storage
                    db_path = Path(session_config.database_path)
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    session = SQLiteSession(
                        session_id=session_id,
                        db_path=str(db_path)
                    )
                else:
                    # In-memory SQLite session
                    session = SQLiteSession(session_id=session_id)
                
                # Cache the session
                self._session_cache[cache_key] = session
                return session
            else:
                raise AgentException(
                    f"Unsupported session type: '{session_config.type}'",
                    agent_name=agent_name
                )
        except Exception as e:
            raise AgentException(
                f"Failed to create session for agent '{agent_name}': {str(e)}",
                agent_name=agent_name
            ) from e

    def _project_root(self) -> Path:
        """
        Resolve the repository/project root directory.

        We keep session DBs under `<repo>/data/sessions/` by default.
        """
        # agent_factory.py lives in: <root>/asdrp/agents/agent_factory.py
        return Path(__file__).resolve().parents[2]

    def _default_persistent_db_path(self, agent_name: str) -> Path:
        """
        Default on-disk SQLite database path for persistent session memory.

        Convention: data/sessions/<agent_name>.db
        """
        normalized = (agent_name or "").lower().strip() or "agent"
        return self._project_root() / "data" / "sessions" / f"{normalized}.db"
    
    def _get_registry(self) -> Dict[str, Callable[[str], AgentProtocol]]:
        """
        Get or initialize the agent registry from configuration.
        
        This method uses lazy initialization to avoid circular dependencies.
        Agent creation functions are imported from their respective modules
        based on configuration file settings.
        
        Returns:
            Dictionary mapping agent names to their creation functions.
        
        Raises:
            AgentException: If agent modules cannot be imported or config is invalid.
        """
        if self._registry is None:
            try:
                config_loader = self._get_config_loader()
                agent_names = config_loader.list_agents()
                
                self._registry = {}
                for agent_name in agent_names:
                    try:
                        config = config_loader.get_agent_config(agent_name)
                        
                        # Skip disabled agents
                        if not config.enabled:
                            continue
                        
                        # Dynamically import the creation function
                        module = __import__(config.module, fromlist=[config.function])
                        factory_func = getattr(module, config.function)
                        
                        self._registry[agent_name] = factory_func
                    except Exception as e:
                        # Log but continue with other agents instead of failing entirely
                        import warnings
                        warnings.warn(
                            f"Failed to load agent '{agent_name}': {str(e)}. "
                            f"Skipping this agent.",
                            UserWarning
                        )
                        continue
                    
            except Exception as e:
                # Reset registry on failure so it can be retried
                self._registry = None
                raise AgentException(
                    f"Failed to initialize agent registry: {str(e)}"
                ) from e
        
        return self._registry
    
    async def get_agent(
        self, 
        name: str, 
        instructions: str | None = None,
        use_config_defaults: bool = True
    ) -> AgentProtocol:
        """
        Create and return an agent instance by name.
        
        This is the main factory method that creates agents based on their
        name. It handles name normalization, validation, and error handling.
        
        Args:
            name: The name/type of agent to create. Valid values are defined
                in the configuration file (config/open_agents.yaml).
            instructions: Optional system instructions for the agent. If None
                and use_config_defaults is True, uses default instructions from
                configuration file.
            use_config_defaults: If True, uses default instructions from config
                when instructions is None. If False, requires explicit instructions.
        
        Returns:
            An agent instance implementing AgentProtocol. The returned agent
            is ready to use with the agents library's Runner.
        
        Raises:
            AgentException: If the agent name is invalid or if agent creation fails.
        
        Examples:
        ---------
        >>> factory = AgentFactory()
        >>> agent = await factory.get_agent("geo", "You are a geocoding assistant")
        >>> assert agent.name == "GeoAgent"
        
        >>> agent = await factory.get_agent("yelp", "You help find restaurants")
        >>> assert agent.name == "YelpAgent"
        
        Notes:
        ------
        - Agent names are case-insensitive and whitespace is trimmed
        - Agent instances are created fresh on each call (not cached)
        - Each agent type has its own set of tools configured automatically
        """
        # Normalize agent name to lowercase for case-insensitive matching
        normalized_name = name.lower().strip()
        
        # Get configuration for this agent first (to check if it exists and is enabled)
        config_loader = self._get_config_loader()
        try:
            agent_config = config_loader.get_agent_config(normalized_name)
        except AgentException:
            # Agent not found in config - check registry for better error message
            registry = self._get_registry()
            valid_names = ", ".join(sorted(registry.keys()))
            raise AgentException(
                f"Unknown agent name: '{name}'. Valid names are: {valid_names}",
                agent_name=name
            )
        
        # Check if agent is enabled
        if not agent_config.enabled:
            raise AgentException(
                f"Agent '{name}' is disabled in configuration",
                agent_name=name
            )
        
        # Get registry (only enabled agents are in registry)
        registry = self._get_registry()
        
        # Verify agent is in registry (should be if enabled)
        if normalized_name not in registry:
            valid_names = ", ".join(sorted(registry.keys()))
            raise AgentException(
                f"Agent '{name}' configuration error: not found in registry. Valid names are: {valid_names}",
                agent_name=name
            )
        
        # Determine instructions to use
        if instructions is None:
            if use_config_defaults:
                instructions = agent_config.default_instructions
            else:
                raise AgentException(
                    f"Instructions required for agent '{name}' when use_config_defaults=False",
                    agent_name=name
                )
        
        # Get the factory function and create the agent
        try:
            factory_func = registry[normalized_name]

            # Check if the factory function accepts mcp_server_config parameter
            # For MCP-based agents, pass the MCP configuration
            import inspect
            sig = inspect.signature(factory_func)
            params = list(sig.parameters.keys())

            if 'mcp_server_config' in params and agent_config.mcp_server:
                # MCP-aware agent: pass model config and MCP config
                agent = factory_func(instructions, agent_config.model, agent_config.mcp_server)
            else:
                # Standard agent: pass model config only
                agent = factory_func(instructions, agent_config.model)

            # Verify the agent implements the protocol
            if not isinstance(agent, AgentProtocol):
                raise AgentException(
                    f"Agent factory for '{name}' did not return a valid AgentProtocol instance",
                    agent_name=name
                )

            return agent
            
        except AgentException:
            # Re-raise AgentException as-is
            raise
        except Exception as e:
            # Wrap any other exceptions in AgentException
            raise AgentException(
                f"Failed to create agent '{name}': {str(e)}",
                agent_name=name
            ) from e
    
    async def get_agent_with_session(
        self,
        name: str,
        instructions: str | None = None,
        use_config_defaults: bool = True,
        session_id: str | None = None
    ) -> Tuple[AgentProtocol, Any]:
        """
        Create and return an agent instance with its session memory.
        
        This method creates an agent along with its configured session memory,
        which can be used with Runner.run() to maintain conversation history.
        
        Args:
            name: The name/type of agent to create.
            instructions: Optional system instructions for the agent.
            use_config_defaults: If True, uses default instructions from config.
            session_id: Optional session ID override. If provided, uses this
                instead of the configured session_id.
        
        Returns:
            Tuple of (agent, session) where session may be None if session
            memory is disabled or unavailable.
        
        Raises:
            AgentException: If the agent cannot be created.
        
        Examples:
        ---------
        >>> factory = AgentFactory()
        >>> agent, session = await factory.get_agent_with_session("geo")
        >>> from agents import Runner
        >>> result = await Runner.run(agent, input="Hello", session=session)
        
        Notes:
        ------
        - Session objects are cached and reused across calls with the same session_id
        - Use different session_id values for separate conversation histories
        - Pass session=None to Runner.run() for stateless operation
        """
        # Get the agent using the standard method
        agent = await self.get_agent(name, instructions, use_config_defaults)
        
        # Get session configuration
        normalized_name = name.lower().strip()
        agent_config = self._get_config_loader().get_agent_config(normalized_name)
        
        # Create session memory configuration, potentially with override
        session_config = agent_config.session_memory
        if session_id is not None:
            # Create a modified config with the override session_id
            session_config = SessionMemoryConfig(
                type=session_config.type,
                session_id=session_id,
                database_path=session_config.database_path,
                enabled=session_config.enabled
            )
        
        # Create session
        session = self._create_session(session_config, normalized_name)
        
        return agent, session

    async def get_agent_with_persistent_session(
        self,
        name: str,
        session_id: str,
        instructions: str | None = None,
        use_config_defaults: bool = True,
        db_path: str | Path | None = None,
    ) -> Tuple[AgentProtocol, Any]:
        """
        Create and return an agent with a guaranteed persistent SQLiteSession.

        This is intended for orchestrators (MoE, SmartRouter, future orchestrators) that must
        provide session-level memory even if the underlying agent config disables session memory.

        Policy:
        - Always returns a SQLiteSession when available (unless openai-agents SQLiteSession is unavailable).
        - Persists to disk under `data/sessions/` by default.
        - Uses the provided `session_id` as the session namespace, so multi-turn conversations
          can be continued by reusing the same session_id.
        """
        if not session_id or not str(session_id).strip():
            raise AgentException("session_id is required for persistent session", agent_name=name)

        agent = await self.get_agent(name, instructions, use_config_defaults)

        if not SESSION_MEMORY_AVAILABLE:
            return agent, None

        normalized_name = name.lower().strip()
        resolved_db_path = Path(db_path) if db_path else self._default_persistent_db_path(normalized_name)

        session_config = SessionMemoryConfig(
            type="sqlite",
            session_id=session_id,
            database_path=str(resolved_db_path),
            enabled=True,
        )

        session = self._create_session(session_config, normalized_name)
        return agent, session

    def get_persistent_session(
        self,
        agent_name: str,
        session_id: str,
        db_path: str | Path | None = None,
    ) -> Any:
        """
        Get or create a guaranteed persistent SQLiteSession for an agent without creating the agent.

        Mirrors get_agent_with_persistent_session() behavior for session creation.
        """
        if not session_id or not str(session_id).strip():
            raise AgentException("session_id is required for persistent session", agent_name=agent_name)

        if not SESSION_MEMORY_AVAILABLE:
            return None

        normalized_name = agent_name.lower().strip()
        resolved_db_path = Path(db_path) if db_path else self._default_persistent_db_path(normalized_name)
        session_config = SessionMemoryConfig(
            type="sqlite",
            session_id=session_id,
            database_path=str(resolved_db_path),
            enabled=True,
        )
        return self._create_session(session_config, normalized_name)
    
    def get_session(
        self,
        agent_name: str,
        session_id: str | None = None
    ) -> Any:
        """
        Get or create a session for an agent without creating the agent.
        
        Useful when you already have an agent and need to get its session,
        or when you want to pre-create sessions.
        
        Args:
            agent_name: Name of the agent (for config lookup).
            session_id: Optional session ID override.
        
        Returns:
            Session object or None if session memory is disabled.
        
        Raises:
            AgentException: If agent config is not found or session creation fails.
        """
        normalized_name = agent_name.lower().strip()
        agent_config = self._get_config_loader().get_agent_config(normalized_name)
        
        session_config = agent_config.session_memory
        if session_id is not None:
            session_config = SessionMemoryConfig(
                type=session_config.type,
                session_id=session_id,
                database_path=session_config.database_path,
                enabled=session_config.enabled
            )
        
        return self._create_session(session_config, normalized_name)
    
    def clear_session_cache(self) -> None:
        """
        Clear all cached session objects.
        
        Useful for testing or when you want to force new session creation.
        This method also attempts to close any SQLiteSession connections
        before clearing the cache to prevent resource leaks.
        """
        # Close all sessions before clearing cache to prevent resource leaks
        if self._session_cache:
            for session in list(self._session_cache.values()):  # Use list() to avoid modification during iteration
                if session is not None and SESSION_MEMORY_AVAILABLE:
                    # SQLiteSession may have a close() method or connection attribute
                    # Try to close it gracefully
                    try:
                        if hasattr(session, 'close'):
                            session.close()
                        elif hasattr(session, '_connection') and session._connection:
                            session._connection.close()
                        # Also try to close any underlying database connection
                        elif hasattr(session, 'db') and hasattr(session.db, 'close'):
                            session.db.close()
                    except Exception:
                        # Ignore errors during cleanup - connection may already be closed
                        pass
        
        if self._session_cache:
            self._session_cache.clear()
    
    def register_agent(self, name: str, factory_func: Callable[[str], AgentProtocol]) -> None:
        """
        Register a new agent type with the factory.
        
        This method allows extending the factory with new agent types at runtime.
        Useful for dynamic agent registration or testing.
        
        Args:
            name: The name of the agent type (will be normalized to lowercase).
            factory_func: A callable that takes instructions (str) and returns
                an AgentProtocol instance.
        
        Raises:
            ValueError: If name is empty or factory_func is not callable.
        
        Examples:
        ---------
        >>> factory = AgentFactory()
        >>> def create_custom_agent(instructions: str) -> AgentProtocol:
        ...     # Custom agent creation logic
        ...     pass
        >>> factory.register_agent("custom", create_custom_agent)
        >>> agent = await factory.get_agent("custom", "Instructions")
        
        Notes:
        ------
        - This method modifies the registry, so it affects all factory instances
        - Registered agents take precedence over built-in agents with the same name
        - Use with caution in production code
        """
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")
        
        if not callable(factory_func):
            raise ValueError("factory_func must be callable")
        
        normalized_name = name.lower().strip()
        registry = self._get_registry()
        registry[normalized_name] = factory_func


    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent (case-insensitive).
        
        Returns:
            AgentConfig object with agent configuration.
        
        Raises:
            AgentException: If agent is not found.
        """
        return self._get_config_loader().get_agent_config(agent_name)
    
    def list_available_agents(self) -> list[str]:
        """
        List all available agent names from configuration.
        
        Returns:
            List of enabled agent names.
        """
        return self._get_config_loader().list_agents()


# Convenience function for backward compatibility
async def get_agent(
    name: str, 
    instructions: str | None = None,
    use_config_defaults: bool = True
) -> AgentProtocol:
    """
    Convenience function to create an agent using the singleton factory instance.
    
    This function provides backward compatibility with the previous API where
    get_agent was a standalone function. It delegates to AgentFactory.instance().
    
    Args:
        name: The name/type of agent to create.
        instructions: Optional system instructions. If None, uses config defaults.
        use_config_defaults: If True, uses default instructions from config when None.
    
    Returns:
        An agent instance implementing AgentProtocol.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent = await get_agent("geo", "You are a geocoding assistant")
    
    See Also:
    ---------
    AgentFactory.get_agent: The underlying factory method.
    """
    return await AgentFactory.instance().get_agent(name, instructions, use_config_defaults)


async def get_agent_with_session(
    name: str,
    instructions: str | None = None,
    use_config_defaults: bool = True,
    session_id: str | None = None
) -> Tuple[AgentProtocol, Any]:
    """
    Convenience function to create an agent with session memory.
    
    This function creates an agent along with its configured session memory,
    which can be used with Runner.run() to maintain conversation history.
    
    Args:
        name: The name/type of agent to create.
        instructions: Optional system instructions. If None, uses config defaults.
        use_config_defaults: If True, uses default instructions from config when None.
        session_id: Optional session ID override.
    
    Returns:
        Tuple of (agent, session) where session may be None if disabled.
    
    Raises:
        AgentException: If the agent cannot be created.
    
    Examples:
    ---------
    >>> agent, session = await get_agent_with_session("geo")
    >>> from agents import Runner
    >>> result = await Runner.run(agent, input="Hello", session=session)
    
    See Also:
    ---------
    AgentFactory.get_agent_with_session: The underlying factory method.
    """
    return await AgentFactory.instance().get_agent_with_session(
        name, instructions, use_config_defaults, session_id
    )

