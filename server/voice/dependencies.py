"""
FastAPI Dependency Injection Setup for Voice Module

Provides dependency injection functions for VoiceService, VoiceClient,
VoiceCoordinator, and VoiceConfigManager instances.

The dependency injection system supports both legacy (VoiceClient only) and
coordinator (multi-provider) modes. By default, coordinator mode is enabled
for multi-provider support with automatic provider selection and fallback.
"""

from typing import Optional
import logging
import os

from .client import VoiceClient
from .config import VoiceConfigManager
from .service import VoiceService
from .coordinator import VoiceCoordinator
from .exceptions import VoiceClientException

logger = logging.getLogger(__name__)

# Global instances (singleton pattern matching existing server architecture)
_voice_client: Optional[VoiceClient] = None
_voice_config_manager: Optional[VoiceConfigManager] = None
_voice_coordinator: Optional[VoiceCoordinator] = None
_voice_service: Optional[VoiceService] = None

# Configuration: Enable coordinator mode by default (can be disabled via env var)
USE_COORDINATOR_MODE = os.getenv("VOICE_USE_COORDINATOR", "true").lower() == "true"


def get_voice_client() -> VoiceClient:
    """
    Get or create VoiceClient singleton instance.

    Returns:
        VoiceClient instance

    Raises:
        VoiceClientException: If client initialization fails
    """
    global _voice_client

    if _voice_client is None:
        logger.info("Initializing VoiceClient")
        _voice_client = VoiceClient()

    return _voice_client


def get_voice_config_manager() -> VoiceConfigManager:
    """
    Get or create VoiceConfigManager singleton instance.

    Returns:
        VoiceConfigManager instance
    """
    global _voice_config_manager

    if _voice_config_manager is None:
        logger.info("Initializing VoiceConfigManager")
        _voice_config_manager = VoiceConfigManager()
        # Load configuration on first access
        _voice_config_manager.load()

    return _voice_config_manager


def get_voice_coordinator() -> Optional[VoiceCoordinator]:
    """
    Get or create VoiceCoordinator singleton instance.

    Returns:
        VoiceCoordinator instance if coordinator mode is enabled, None otherwise

    Note:
        Coordinator mode is controlled by VOICE_USE_COORDINATOR environment variable.
        Default: enabled (true)
    """
    global _voice_coordinator

    if not USE_COORDINATOR_MODE:
        return None

    if _voice_coordinator is None:
        try:
            logger.info("Initializing VoiceCoordinator for multi-provider support")
            _voice_coordinator = VoiceCoordinator()
        except Exception as e:
            logger.error(f"Failed to initialize VoiceCoordinator: {str(e)}")
            logger.warning("Falling back to legacy VoiceClient mode")
            return None

    return _voice_coordinator


def get_voice_service() -> VoiceService:
    """
    Get or create VoiceService singleton instance.

    This is the main dependency used by API endpoints.

    By default, initializes with VoiceCoordinator for multi-provider support.
    Falls back to legacy VoiceClient mode if coordinator initialization fails
    or if VOICE_USE_COORDINATOR=false.

    Returns:
        VoiceService instance

    Environment Variables:
        VOICE_USE_COORDINATOR: Enable/disable coordinator mode (default: true)
    """
    global _voice_service

    if _voice_service is None:
        client = get_voice_client()
        config_manager = get_voice_config_manager()
        coordinator = get_voice_coordinator()

        mode = "coordinator" if coordinator else "legacy"
        logger.info(f"Initializing VoiceService in {mode} mode")

        _voice_service = VoiceService(
            client=client,
            config_manager=config_manager,
            coordinator=coordinator,
            use_coordinator=coordinator is not None
        )

    return _voice_service


def reset_voice_dependencies() -> None:
    """
    Reset all voice dependencies.

    Useful for testing or when configuration changes require re-initialization.
    """
    global _voice_client, _voice_config_manager, _voice_coordinator, _voice_service

    logger.info("Resetting voice dependencies")

    _voice_client = None
    _voice_config_manager = None
    _voice_coordinator = None
    _voice_service = None
