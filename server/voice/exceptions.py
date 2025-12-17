"""
Custom Exceptions for Voice Module

Provides structured error handling with error codes and context information.
"""
import os
from typing import Optional, Dict, Any
from enum import Enum


class VoiceErrorCode(str, Enum):
    """Enumeration of voice module error codes."""

    # Configuration Errors (1xx)
    CONFIG_NOT_FOUND = "VOICE_101"
    CONFIG_INVALID = "VOICE_102"
    CONFIG_SAVE_FAILED = "VOICE_103"
    GET_VOICES_FAILED = "VOICE_104"

    # Client Errors (2xx)
    API_KEY_MISSING = "VOICE_201"
    API_KEY_INVALID = "VOICE_202"
    API_KEY_MISSING_PERMISSION = "VOICE_204"
    CLIENT_INIT_FAILED = "VOICE_203"

    # TTS Errors (3xx)
    TTS_TEXT_TOO_LONG = "VOICE_301"
    TTS_VOICE_NOT_FOUND = "VOICE_302"
    TTS_MODEL_NOT_AVAILABLE = "VOICE_303"
    TTS_SYNTHESIS_FAILED = "VOICE_304"
    TTS_TIMEOUT = "VOICE_305"

    # STT Errors (4xx)
    STT_AUDIO_INVALID = "VOICE_401"
    STT_AUDIO_TOO_LONG = "VOICE_402"
    STT_TRANSCRIPTION_FAILED = "VOICE_403"
    STT_TIMEOUT = "VOICE_404"
    STT_LANGUAGE_NOT_SUPPORTED = "VOICE_405"

    # Service Errors (5xx)
    SERVICE_UNAVAILABLE = "VOICE_501"
    RATE_LIMIT_EXCEEDED = "VOICE_502"
    QUOTA_EXCEEDED = "VOICE_503"
    NETWORK_ERROR = "VOICE_504"
    ALL_PROVIDERS_FAILED = "VOICE_505"


class VoiceException(Exception):
    """Base exception for all voice module errors."""

    def __init__(
        self,
        message: str,
        error_code: VoiceErrorCode,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize VoiceException.

        Args:
            message: Human-readable error message
            error_code: Error code from VoiceErrorCode enum
            details: Additional context information
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses.

        Returns:
            Dictionary with error, error_code, and details
        """
        return {
            "error": self.message,
            "error_code": self.error_code.value,
            "details": self.details
        }

    def __str__(self) -> str:
        """String representation of the exception."""
        base = f"[{self.error_code.value}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.cause:
            base += f" | Caused by: {str(self.cause)}"
        return base


class VoiceConfigurationException(VoiceException):
    """Exception for configuration-related errors."""

    def __init__(
        self,
        message: str,
        error_code: VoiceErrorCode = VoiceErrorCode.CONFIG_INVALID,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class VoiceClientException(VoiceException):
    """Exception for client initialization and connection errors."""

    def __init__(
        self,
        message: str,
        error_code: VoiceErrorCode = VoiceErrorCode.CLIENT_INIT_FAILED,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class TTSException(VoiceException):
    """Exception for text-to-speech operation errors."""

    def __init__(
        self,
        message: str,
        error_code: VoiceErrorCode = VoiceErrorCode.TTS_SYNTHESIS_FAILED,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class STTException(VoiceException):
    """Exception for speech-to-text operation errors."""

    def __init__(
        self,
        message: str,
        error_code: VoiceErrorCode = VoiceErrorCode.STT_TRANSCRIPTION_FAILED,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class VoiceServiceException(VoiceException):
    """Exception for service-level errors."""

    def __init__(
        self,
        message: str,
        error_code: VoiceErrorCode = VoiceErrorCode.SERVICE_UNAVAILABLE,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


def map_elevenlabs_error(error: Exception) -> VoiceException:
    """
    Map ElevenLabs SDK exceptions to VoiceException types.

    Args:
        error: Original exception from ElevenLabs SDK

    Returns:
        Appropriate VoiceException subclass
    """
    error_str = str(error).lower()
    
    # Check for ElevenLabs ApiError with status_code attribute
    status_code = None
    error_body = None
    if hasattr(error, 'status_code'):
        status_code = error.status_code
    if hasattr(error, 'body'):
        error_body = error.body
        if isinstance(error_body, dict):
            error_body_str = str(error_body).lower()
        else:
            error_body_str = str(error_body).lower()
    else:
        error_body_str = ""

    # Check for missing permissions (401 with missing_permissions in body)
    if status_code == 401:
        if error_body and isinstance(error_body, dict):
            detail = error_body.get('detail', {})
            if isinstance(detail, dict):
                if detail.get('status') == 'missing_permissions' or 'missing_permissions' in str(detail).lower():
                    permission_msg = detail.get('message', 'Missing required API permission')
                    return VoiceClientException(
                        message=f"API key missing required permission: {permission_msg}",
                        error_code=VoiceErrorCode.API_KEY_MISSING_PERMISSION,
                        details={"status_code": 401, "permission_error": permission_msg},
                        cause=error
                    )
        # Generic 401 unauthorized
        return VoiceClientException(
            message="Invalid or missing API key",
            error_code=VoiceErrorCode.API_KEY_INVALID,
            details={"status_code": 401},
            cause=error
        )

    # API Key errors (string-based detection for backward compatibility)
    if "api key" in error_str or "unauthorized" in error_str or "401" in error_str:
        return VoiceClientException(
            message="Invalid or missing API key",
            error_code=VoiceErrorCode.API_KEY_INVALID,
            cause=error
        )

    # Rate limit errors
    if "rate limit" in error_str or "429" in error_str:
        return VoiceServiceException(
            message="Rate limit exceeded",
            error_code=VoiceErrorCode.RATE_LIMIT_EXCEEDED,
            cause=error
        )

    # Quota errors
    if "quota" in error_str or "insufficient credits" in error_str:
        return VoiceServiceException(
            message="Quota exceeded",
            error_code=VoiceErrorCode.QUOTA_EXCEEDED,
            cause=error
        )

    # Network errors
    if "connection" in error_str or "timeout" in error_str or "network" in error_str:
        return VoiceServiceException(
            message="Network error",
            error_code=VoiceErrorCode.NETWORK_ERROR,
            cause=error
        )

    # Voice not found
    if "voice" in error_str and ("not found" in error_str or "404" in error_str):
        return TTSException(
            message="Voice not found",
            error_code=VoiceErrorCode.TTS_VOICE_NOT_FOUND,
            cause=error
        )

    # Model not available
    if "model" in error_str and ("not available" in error_str or "not found" in error_str):
        return TTSException(
            message="Model not available",
            error_code=VoiceErrorCode.TTS_MODEL_NOT_AVAILABLE,
            cause=error
        )

    # Audio errors
    if "audio" in error_str and ("invalid" in error_str or "format" in error_str):
        return STTException(
            message="Invalid audio format",
            error_code=VoiceErrorCode.STT_AUDIO_INVALID,
            cause=error
        )

    # Language errors
    if "language" in error_str and ("not supported" in error_str or "invalid" in error_str):
        return STTException(
            message="Language not supported",
            error_code=VoiceErrorCode.STT_LANGUAGE_NOT_SUPPORTED,
            cause=error
        )

    # Default to service unavailable
    return VoiceServiceException(
        message=f"ElevenLabs service error: {str(error)}",
        error_code=VoiceErrorCode.SERVICE_UNAVAILABLE,
        cause=error
    )
