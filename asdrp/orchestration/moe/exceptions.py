"""
MoE Orchestrator Exceptions.

Custom exception hierarchy for MoE orchestration errors.
"""


class MoEException(Exception):
    """Base exception for MoE orchestration errors."""
    pass


class ConfigException(MoEException):
    """Configuration loading or validation error."""
    pass


class ExpertSelectionException(MoEException):
    """Expert selection error."""
    pass


class ExecutionException(MoEException):
    """Expert execution error."""
    pass


class MixingException(MoEException):
    """Result mixing error."""
    pass


class CacheException(MoEException):
    """Cache operation error."""
    pass
