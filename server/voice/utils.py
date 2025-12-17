"""
Utility Functions for Voice Module

Helper functions for audio processing, validation, and data conversion.
"""

import hashlib
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracking.

    Returns:
        Unique request ID string
    """
    timestamp = str(time.time())
    hash_obj = hashlib.sha256(timestamp.encode())
    return hash_obj.hexdigest()[:16]


def validate_audio_format(audio_data: bytes, max_size_mb: int = 25) -> bool:
    """
    Validate audio data size and format.

    Args:
        audio_data: Audio bytes to validate
        max_size_mb: Maximum file size in MB

    Returns:
        True if valid, False otherwise
    """
    if not audio_data:
        logger.warning("Empty audio data provided")
        return False

    # Check size
    size_mb = len(audio_data) / (1024 * 1024)
    if size_mb > max_size_mb:
        logger.warning(f"Audio file too large: {size_mb:.2f}MB (max: {max_size_mb}MB)")
        return False

    # Basic format validation (check for common audio signatures)
    # MP3: starts with 'ID3' or 0xFF 0xFB
    # WAV: starts with 'RIFF'
    # OGG: starts with 'OggS'
    # WEBM: starts with 0x1A 0x45 0xDF 0xA3

    if len(audio_data) < 4:
        logger.warning("Audio data too short to validate format")
        return False

    # Check signatures
    if audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
        logger.debug("Detected MP3 format")
        return True
    elif audio_data[:4] == b'RIFF':
        logger.debug("Detected WAV format")
        return True
    elif audio_data[:4] == b'OggS':
        logger.debug("Detected OGG format")
        return True
    elif audio_data[:4] == b'\x1a\x45\xdf\xa3':
        logger.debug("Detected WEBM format")
        return True

    logger.warning("Unknown audio format")
    return True  # Allow unknown formats (ElevenLabs may support)


def sanitize_text_for_tts(text: str, max_length: int = 5000) -> str:
    """
    Sanitize text for TTS processing.

    Removes or replaces problematic characters and enforces length limits.

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Trim whitespace
    text = text.strip()

    # Replace multiple spaces with single space
    text = " ".join(text.split())

    # Remove control characters (except newlines and tabs)
    text = "".join(char for char in text if char.isprintable() or char in '\n\t')

    # Truncate if too long
    if len(text) > max_length:
        logger.warning(f"Text truncated from {len(text)} to {max_length} characters")
        text = text[:max_length]

    return text


def format_duration(duration_ms: Optional[int]) -> str:
    """
    Format duration in milliseconds to human-readable string.

    Args:
        duration_ms: Duration in milliseconds

    Returns:
        Formatted duration string (e.g., "1m 23s", "45s")
    """
    if duration_ms is None:
        return "N/A"

    seconds = duration_ms / 1000

    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)

    return f"{minutes}m {remaining_seconds}s"


def estimate_tts_duration(text: str, words_per_minute: int = 150) -> int:
    """
    Estimate TTS audio duration based on text length.

    Args:
        text: Input text
        words_per_minute: Speaking rate (default: 150 wpm)

    Returns:
        Estimated duration in milliseconds
    """
    if not text:
        return 0

    # Count words
    word_count = len(text.split())

    # Calculate duration
    minutes = word_count / words_per_minute
    duration_ms = int(minutes * 60 * 1000)

    return duration_ms


def get_content_type_for_format(output_format: str) -> str:
    """
    Get MIME content type for audio format.

    Args:
        output_format: Audio format identifier

    Returns:
        MIME content type string
    """
    format_map = {
        "mp3_44100_128": "audio/mpeg",
        "mp3_22050_32": "audio/mpeg",
        "pcm_16000": "audio/pcm",
        "pcm_22050": "audio/pcm",
        "pcm_24000": "audio/pcm",
        "pcm_44100": "audio/pcm",
    }

    return format_map.get(output_format, "audio/mpeg")
