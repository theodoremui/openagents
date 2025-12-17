#############################################################################
# protocol.py
#
# Agent protocol definition and exception classes.
#
# This module defines:
# - AgentProtocol: A Protocol defining the interface that all agents must implement
# - AgentException: Base exception for agent-related errors
#
# Note: Agent creation is handled by AgentFactory in agent_factory.py
#
#############################################################################

from typing import Protocol, runtime_checkable


@runtime_checkable
class AgentProtocol(Protocol):
    """
    Protocol defining the interface that all agent implementations must follow.
    
    This protocol ensures that all agents have:
    - A name attribute
    - An instructions attribute
    - The ability to be used with the agents library's Runner
    
    The protocol is runtime-checkable, meaning isinstance() checks will work
    at runtime to verify that an object conforms to this protocol.
    
    Attributes:
    -----------
    name : str
        The name of the agent.
    instructions : str
        The system instructions for the agent.
    
    Notes:
    ------
    The protocol is designed to work with the `agents` library's Agent class,
    which provides the actual implementation. This protocol serves as a
    contract that all agent implementations must satisfy.
    """
    name: str
    instructions: str


class AgentException(Exception):
    """
    Base exception class for all agent-related errors.
    
    This exception should be raised when:
    - An agent cannot be created (invalid name, missing dependencies, etc.)
    - An agent encounters an error during initialization
    - Any other agent-related operation fails
    
    Attributes:
    -----------
    message : str
        Human-readable error message describing what went wrong.
    agent_name : str, optional
        The name of the agent that caused the error, if applicable.
    
    Examples:
    ---------
    >>> raise AgentException("Failed to create agent", agent_name="GeoAgent")
    >>> raise AgentException("Invalid agent name: unknown_agent")
    """
    
    def __init__(self, message: str, agent_name: str | None = None):
        """
        Initialize AgentException.
        
        Args:
            message: Human-readable error message.
            agent_name: Optional name of the agent that caused the error.
        """
        self.message = message
        self.agent_name = agent_name
        if agent_name:
            super().__init__(f"{message} (agent: {agent_name})")
        else:
            super().__init__(message)



