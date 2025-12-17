"""
Voice Configuration Management

Handles loading, saving, validating, and hot-reloading of voice configuration
from YAML files.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import logging
import os
from datetime import datetime

from .models import (
    VoiceConfig,
    TTSConfig,
    STTConfig,
    VoiceProfile,
    CacheConfig,
    LoggingConfig,
    ValidationResult
)
from .exceptions import VoiceConfigurationException, VoiceErrorCode

logger = logging.getLogger(__name__)


class VoiceConfigManager:
    """
    Manages voice configuration loading, saving, and validation.

    Implements hot-reload capability and schema validation using Pydantic models.

    Features:
    - YAML file loading with error handling
    - Schema validation via Pydantic
    - Hot-reload without server restart
    - Profile management
    - Default value inheritance
    """

    DEFAULT_CONFIG_PATH = Path("config/voice_config.yaml")

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. Uses default if not provided.
        """
        self._config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[VoiceConfig] = None
        self._last_loaded: Optional[datetime] = None
        self._file_mtime: Optional[float] = None

    def load(self, force: bool = False) -> VoiceConfig:
        """
        Load configuration from YAML file.

        Args:
            force: Force reload even if already loaded

        Returns:
            VoiceConfig instance

        Raises:
            VoiceConfigurationException: If loading or parsing fails
        """
        try:
            # Check if config exists
            if not self._config_path.exists():
                logger.warning(f"Config file not found: {self._config_path}, using defaults")
                self._config = VoiceConfig()
                self._last_loaded = datetime.now()
                return self._config

            # Check if reload needed
            current_mtime = os.path.getmtime(self._config_path)
            if not force and self._config is not None and self._file_mtime == current_mtime:
                logger.debug("Using cached configuration")
                return self._config

            # Load YAML
            logger.info(f"Loading voice configuration from {self._config_path}")
            with open(self._config_path, "r") as f:
                config_dict = yaml.safe_load(f)

            # Handle empty file
            if config_dict is None:
                logger.warning("Empty config file, using defaults")
                self._config = VoiceConfig()
                self._last_loaded = datetime.now()
                self._file_mtime = current_mtime
                return self._config

            # Extract voice configuration (may be nested under 'voice' key)
            if isinstance(config_dict, dict) and "voice" in config_dict:
                config_dict = config_dict["voice"]

            # Parse into Pydantic model (validates schema)
            self._config = VoiceConfig(**config_dict)
            self._last_loaded = datetime.now()
            self._file_mtime = current_mtime

            logger.info(f"Voice configuration loaded successfully at {self._last_loaded}")
            return self._config

        except yaml.YAMLError as e:
            raise VoiceConfigurationException(
                message=f"Failed to parse YAML configuration: {str(e)}",
                error_code=VoiceErrorCode.CONFIG_INVALID,
                details={"path": str(self._config_path)},
                cause=e
            )
        except Exception as e:
            raise VoiceConfigurationException(
                message=f"Failed to load configuration: {str(e)}",
                error_code=VoiceErrorCode.CONFIG_NOT_FOUND,
                details={"path": str(self._config_path)},
                cause=e
            )

    def save(self, config: VoiceConfig) -> None:
        """
        Save configuration to YAML file.

        Args:
            config: VoiceConfig instance to save

        Raises:
            VoiceConfigurationException: If saving fails
        """
        try:
            # Ensure parent directory exists
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict and wrap in 'voice' key
            config_dict = {"voice": config.model_dump(exclude_none=True)}

            # Write YAML
            with open(self._config_path, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

            # Update cache
            self._config = config
            self._last_loaded = datetime.now()
            self._file_mtime = os.path.getmtime(self._config_path)

            logger.info(f"Configuration saved to {self._config_path}")

        except Exception as e:
            raise VoiceConfigurationException(
                message=f"Failed to save configuration: {str(e)}",
                error_code=VoiceErrorCode.CONFIG_SAVE_FAILED,
                details={"path": str(self._config_path)},
                cause=e
            )

    def reload(self) -> VoiceConfig:
        """
        Force reload configuration from file.

        Returns:
            VoiceConfig instance

        Raises:
            VoiceConfigurationException: If reload fails
        """
        logger.info("Force reloading configuration")
        return self.load(force=True)

    def validate(self, config: VoiceConfig) -> ValidationResult:
        """
        Validate configuration against schema and business rules.

        Args:
            config: VoiceConfig to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Validate TTS config
        if config.tts.max_text_length > 10000:
            warnings.append("max_text_length > 10000 may cause timeouts")

        # Validate ElevenLabs-specific fields if present
        if config.tts.stability is not None and config.tts.stability < 0.3:
            warnings.append("Low stability (<0.3) may produce inconsistent output")

        # Validate OpenAI-specific fields if present
        if config.tts.speed is not None and (config.tts.speed < 0.25 or config.tts.speed > 4.0):
            errors.append("OpenAI TTS speed must be between 0.25 and 4.0")

        # Validate STT config
        if config.stt.timeout > 300:
            warnings.append("STT timeout > 300s is unusually high")

        # Validate voice profiles
        if config.default_profile and config.default_profile not in config.voice_profiles:
            errors.append(f"default_profile '{config.default_profile}' not found in voice_profiles")

        for profile_name, profile in config.voice_profiles.items():
            # Validate ElevenLabs profiles
            if profile.stability is not None and profile.stability < 0.3:
                warnings.append(f"Profile '{profile_name}': low stability may cause inconsistencies")

            # Validate OpenAI profiles
            if profile.speed is not None and (profile.speed < 0.25 or profile.speed > 4.0):
                errors.append(f"Profile '{profile_name}': OpenAI speed must be between 0.25 and 4.0")

        # Validate cache config
        if config.cache.voice_list_ttl < 60:
            warnings.append("voice_list_ttl < 60s may cause excessive API calls")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def get_default_tts_config(self) -> TTSConfig:
        """
        Get default TTS configuration.

        Returns:
            TTSConfig with defaults
        """
        if self._config is None:
            self.load()
        return self._config.tts if self._config else TTSConfig()

    def get_default_stt_config(self) -> STTConfig:
        """
        Get default STT configuration.

        Returns:
            STTConfig with defaults
        """
        if self._config is None:
            self.load()
        return self._config.stt if self._config else STTConfig()

    def get_profile(self, name: str) -> Optional[VoiceProfile]:
        """
        Get voice profile by name.

        Args:
            name: Profile name

        Returns:
            VoiceProfile or None if not found
        """
        if self._config is None:
            self.load()

        if self._config and name in self._config.voice_profiles:
            return self._config.voice_profiles[name]

        logger.warning(f"Voice profile '{name}' not found")
        return None

    @property
    def config(self) -> VoiceConfig:
        """
        Get current configuration, loading if necessary.

        Returns:
            VoiceConfig instance
        """
        if self._config is None:
            self.load()
        return self._config or VoiceConfig()

    @property
    def last_loaded(self) -> Optional[datetime]:
        """Get timestamp of last configuration load."""
        return self._last_loaded

    @property
    def config_path(self) -> Path:
        """Get configuration file path."""
        return self._config_path
