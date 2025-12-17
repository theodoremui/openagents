"""
Background audio manager for real-time voice sessions.

Provides thinking sounds, ambient audio, and other audio feedback
synchronized to the agent lifecycle, following the specification's
Requirement 5 for background audio support.
"""

from pathlib import Path
from typing import Optional
from loguru import logger

try:
    # These imports are from livekit-agents - may not be available yet
    # Keep implementation ready for when they are
    from livekit.agents import AudioSource
    from livekit.plugins import openai as lk_openai
    AUDIO_AVAILABLE = True
except ImportError:
    logger.warning("LiveKit audio features not available - install livekit-agents")
    AUDIO_AVAILABLE = False

from .config import RealtimeVoiceConfig


class VoiceAudioManager:
    """
    Manages background audio for voice sessions.

    Provides thinking sounds, ambient audio, and other audio feedback
    synchronized to the agent lifecycle per specification Requirement 5.

    Features:
    - Thinking sound playback during LLM processing
    - Ambient background audio
    - Smooth crossfading between states
    - Configurable volume and sound selection
    """

    # Asset directories (relative to this file)
    ASSETS_DIR = Path(__file__).parent / "assets"
    THINKING_SOUNDS_DIR = ASSETS_DIR / "thinking"
    AMBIENT_SOUNDS_DIR = ASSETS_DIR / "ambient"

    def __init__(self, config: RealtimeVoiceConfig):
        """
        Initialize the audio manager.

        Args:
            config: Voice configuration with audio settings.
        """
        self._config = config
        self._thinking_source: Optional[Any] = None
        self._ambient_source: Optional[Any] = None

        # Ensure asset directories exist
        self.THINKING_SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
        self.AMBIENT_SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"VoiceAudioManager initialized (audio_available={AUDIO_AVAILABLE})")

    def get_thinking_sound_path(self) -> Optional[Path]:
        """
        Get the path to the configured thinking sound file.

        Returns:
            Path to thinking sound file, or None if disabled or not found.
        """
        if not self._config.enable_thinking_sound:
            return None

        sound_file = self.THINKING_SOUNDS_DIR / f"{self._config.thinking_sound}.mp3"

        if sound_file.exists():
            logger.debug(f"Found thinking sound: {sound_file}")
            return sound_file

        # Try WAV format as fallback
        sound_file = sound_file.with_suffix('.wav')
        if sound_file.exists():
            logger.debug(f"Found thinking sound (WAV): {sound_file}")
            return sound_file

        logger.warning(f"Thinking sound not found: {self._config.thinking_sound}")
        return None

    def get_ambient_sound_path(self) -> Optional[Path]:
        """
        Get the path to the configured ambient sound file.

        Returns:
            Path to ambient sound file, or None if disabled or not found.
        """
        if not self._config.enable_ambient:
            return None

        sound_file = self.AMBIENT_SOUNDS_DIR / f"{self._config.ambient_sound}.mp3"

        if sound_file.exists():
            logger.debug(f"Found ambient sound: {sound_file}")
            return sound_file

        # Try WAV format as fallback
        sound_file = sound_file.with_suffix('.wav')
        if sound_file.exists():
            logger.debug(f"Found ambient sound (WAV): {sound_file}")
            return sound_file

        logger.warning(f"Ambient sound not found: {self._config.ambient_sound}")
        return None

    def create_thinking_audio_source(self) -> Optional['AudioSource']:
        """
        Create an audio source for thinking sound.

        Returns:
            AudioSource instance if available and configured, None otherwise.
        """
        if not AUDIO_AVAILABLE:
            return None

        sound_path = self.get_thinking_sound_path()
        if not sound_path:
            return None

        try:
            # Create audio source from file
            # Implementation depends on LiveKit Agents API
            logger.info(f"Creating thinking audio source: {sound_path}")
            # TODO: Implement when LiveKit audio API is finalized
            return None
        except Exception as e:
            logger.error(f"Failed to create thinking audio source: {e}")
            return None

    def create_ambient_audio_source(self) -> Optional['AudioSource']:
        """
        Create an audio source for ambient sound.

        Returns:
            AudioSource instance if available and configured, None otherwise.
        """
        if not AUDIO_AVAILABLE:
            return None

        sound_path = self.get_ambient_sound_path()
        if not sound_path:
            return None

        try:
            # Create looping audio source from file
            logger.info(f"Creating ambient audio source: {sound_path}")
            # TODO: Implement when LiveKit audio API is finalized
            return None
        except Exception as e:
            logger.error(f"Failed to create ambient audio source: {e}")
            return None

    async def play_thinking_sound(self, room: Any) -> None:
        """
        Play thinking sound in the room.

        Args:
            room: LiveKit room to play audio in.
        """
        if not self._config.enable_thinking_sound:
            return

        thinking_source = self.create_thinking_audio_source()
        if thinking_source:
            try:
                logger.debug("Playing thinking sound")
                # TODO: Publish audio track to room
                pass
            except Exception as e:
                logger.error(f"Failed to play thinking sound: {e}")

    async def stop_thinking_sound(self) -> None:
        """Stop playing thinking sound."""
        if self._thinking_source:
            try:
                logger.debug("Stopping thinking sound")
                # TODO: Stop audio track
                self._thinking_source = None
            except Exception as e:
                logger.error(f"Failed to stop thinking sound: {e}")

    async def start_ambient_sound(self, room: Any) -> None:
        """
        Start ambient sound in the room (looping).

        Args:
            room: LiveKit room to play audio in.
        """
        if not self._config.enable_ambient:
            return

        ambient_source = self.create_ambient_audio_source()
        if ambient_source:
            try:
                logger.debug("Starting ambient sound")
                # TODO: Publish looping audio track to room
                pass
            except Exception as e:
                logger.error(f"Failed to start ambient sound: {e}")

    async def stop_ambient_sound(self) -> None:
        """Stop playing ambient sound."""
        if self._ambient_source:
            try:
                logger.debug("Stopping ambient sound")
                # TODO: Stop audio track
                self._ambient_source = None
            except Exception as e:
                logger.error(f"Failed to stop ambient sound: {e}")

    async def cleanup(self) -> None:
        """Cleanup all audio resources."""
        await self.stop_thinking_sound()
        await self.stop_ambient_sound()
        logger.debug("Audio manager cleaned up")
