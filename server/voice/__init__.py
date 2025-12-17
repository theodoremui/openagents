"""
Voice Module for OpenAgents

Provides Text-to-Speech (TTS) and Speech-to-Text (STT) capabilities
using ElevenLabs API.

Architecture:
------------
- client.py: ElevenLabs SDK wrapper
- service.py: Business logic layer
- router.py: FastAPI REST API endpoints
- config.py: YAML configuration management
- models.py: Pydantic data models
- exceptions.py: Custom exception types
- dependencies.py: FastAPI dependency injection setup
"""

__version__ = "1.0.0"
__all__ = [
    "VoiceClient",
    "VoiceService",
    "VoiceConfig",
    "VoiceException",
]
