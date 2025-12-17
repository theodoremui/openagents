"""
Exceptions for real-time voice system.

Custom exception hierarchy for handling voice-related errors with detailed context.
"""

from typing import Optional, Dict, Any


class RealtimeVoiceException(Exception):
    """Base exception for real-time voice system errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            details: Additional context (dict)
            cause: Original exception if this wraps another error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        """String representation with details."""
        parts = [self.message]
        if self.details:
            # Use repr() to avoid format string issues when logging
            parts.append(f"Details: {repr(self.details)}")
        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {str(self.cause)}")
        return " | ".join(parts)


class SessionLimitExceeded(RealtimeVoiceException):
    """Raised when user has too many active sessions."""

    def __init__(self, message: str = "Session limit exceeded", **kwargs):
        super().__init__(message=message, **kwargs)


class SessionNotFound(RealtimeVoiceException):
    """Raised when requested session does not exist."""

    def __init__(self, message: str = "Session not found", **kwargs):
        super().__init__(message=message, **kwargs)


class LiveKitConnectionException(RealtimeVoiceException):
    """Raised when LiveKit server connection fails."""

    def __init__(self, message: str = "Failed to connect to LiveKit server", **kwargs):
        super().__init__(message=message, **kwargs)


class AgentInitializationException(RealtimeVoiceException):
    """Raised when agent initialization fails."""

    def __init__(self, message: str = "Failed to initialize voice agent", **kwargs):
        super().__init__(message=message, **kwargs)


class ConfigurationException(RealtimeVoiceException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str = "Invalid configuration", **kwargs):
        super().__init__(message=message, **kwargs)
