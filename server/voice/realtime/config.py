"""
Configuration management for real-time voice system.

Loads configuration from the unified voice_config.yaml (under 'realtime' section)
and environment variables for credentials.
"""

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger
from urllib.parse import urlparse, urlunparse

from server.voice.config import VoiceConfigManager
from server.voice.models import AgentType
from .exceptions import ConfigurationException


class RealtimeVoiceConfig:
    """
    Configuration accessor for real-time voice system.

    Loads settings from the unified config/voice_config.yaml under the 'realtime' section
    and environment variables for LiveKit credentials.

    This avoids duplication with the async voice system - both share the same base
    configuration and provider settings.
    """

    def __init__(self, voice_config_manager: Optional[VoiceConfigManager] = None):
        """
        Initialize real-time voice configuration.

        Args:
            voice_config_manager: Optional voice config manager. Creates new if not provided.
        """
        try:
            # Use shared voice configuration manager
            self._voice_config_manager = voice_config_manager or VoiceConfigManager()
            self._voice_config = self._voice_config_manager.load()

            # Extract realtime section from raw YAML (since VoiceConfig model doesn't include it)
            # Load raw YAML to get the realtime section that's not in the Pydantic model
            # Also extract providers section for TTS/STT settings
            config_path = self._voice_config_manager._config_path
            self._raw_config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    raw_config = yaml.safe_load(f)
                self._raw_config = raw_config or {}
                # Navigate to voice.realtime if nested, or realtime if at root
                if isinstance(raw_config, dict):
                    if "voice" in raw_config and isinstance(raw_config["voice"], dict):
                        self._realtime_config = raw_config["voice"].get("realtime", {})
                        self._voice_raw_config = raw_config["voice"]
                    else:
                        self._realtime_config = raw_config.get("realtime", {})
                        self._voice_raw_config = raw_config
                else:
                    self._realtime_config = {}
                    self._voice_raw_config = {}
            else:
                self._realtime_config = {}
                self._voice_raw_config = {}

            if not self._realtime_config:
                logger.debug("No 'realtime' section in voice_config.yaml, using defaults")
                self._realtime_config = self._get_default_realtime_config()
            else:
                logger.debug("Loaded 'realtime' section from voice_config.yaml")

            # Load LiveKit credentials from environment
            # LIVEKIT_URL is used by the LiveKit Agents worker as a websocket URL (ws/wss),
            # but the LiveKit API client expects an HTTP(S) base URL.
            # To make setup less error-prone, we accept either form and derive the other.
            self._livekit_url_raw = os.getenv("LIVEKIT_URL")
            self._livekit_api_key = os.getenv("LIVEKIT_API_KEY")
            self._livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

            # Validate required environment variables
            if not self._livekit_url_raw:
                raise ConfigurationException(
                    message="LIVEKIT_URL environment variable is required",
                    details={"missing_var": "LIVEKIT_URL"}
                )
            if not self._livekit_api_key:
                raise ConfigurationException(
                    message="LIVEKIT_API_KEY environment variable is required",
                    details={"missing_var": "LIVEKIT_API_KEY"}
                )
            if not self._livekit_api_secret:
                raise ConfigurationException(
                    message="LIVEKIT_API_SECRET environment variable is required",
                    details={"missing_var": "LIVEKIT_API_SECRET"}
                )

            # Derive websocket + http urls from LIVEKIT_URL
            self._livekit_ws_url, self._livekit_http_url = self._derive_livekit_urls(
                self._livekit_url_raw
            )

            # Validate OpenAI API key (for STT/LLM/TTS)
            self._openai_api_key = os.getenv("OPENAI_API_KEY")
            if not self._openai_api_key:
                logger.warning("OPENAI_API_KEY not set. Voice features may not work.")

            logger.info("Real-time voice configuration loaded successfully")

        except Exception as e:
            if isinstance(e, ConfigurationException):
                raise
            raise ConfigurationException(
                message=f"Failed to load real-time voice configuration: {str(e)}",
                details={"error": str(e)},
                cause=e
            )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "RealtimeVoiceConfig":
        """
        Load configuration from unified voice config file and environment.

        Args:
            config_path: Path to voice_config.yaml. Uses default if not provided.

        Returns:
            RealtimeVoiceConfig instance

        Raises:
            ConfigurationException: If configuration is invalid or missing required fields
        """
        if config_path:
            voice_config_manager = VoiceConfigManager(config_path)
        else:
            voice_config_manager = VoiceConfigManager()

        return cls(voice_config_manager)

    def _get_default_realtime_config(self) -> Dict[str, Any]:
        """Get default realtime configuration if not found in YAML."""
        return {
            "enabled": True,
            "livekit": {
                "room_empty_timeout": 300,
                "max_participants": 2,
            },
            # Worker tuning for LiveKit Agents.
            # IMPORTANT: LiveKit defaults to multiple idle processes in production.
            # Each process imports torch/onnx + plugins, which can be memory-heavy on laptops.
            # We default to 1 to avoid OS-level SIGKILL/OOM (exit 137).
            "worker": {
                "agent_name": "openagents-voice",
                "num_idle_processes": 1,
                # LiveKit internal HTTP server port (0 = auto-pick free port)
                "port": 0,
                # Memory guardrails per job process (0 = disabled).
                # Use these if you still see OS SIGKILL due to memory pressure.
                "job_memory_warn_mb": 700,
                "job_memory_limit_mb": 0,
                # Worker availability threshold (lower => worker marked unavailable sooner)
                "load_threshold": 0.7,
            },
            "vad": {
                "provider": "silero",
                "activation_threshold": 0.7,  # Higher = less sensitive to noise
                "min_speech_duration": 0.05,
                "min_silence_duration": 0.55,  # Longer = better noise filtering
                "prefix_padding_duration": 0.5,
            },
            "turn_detection": {
                "enabled": False,  # Disabled by default - requires inference executor
                "min_endpointing_delay": 0.5,
                "max_endpointing_delay": 3.0,
            },
            "interruptions": {
                "allow": True,
                "min_duration": 0.5,
                "min_words": 0,
            },
            "agent": {
                "type": "smart_router",
                "instructions": "You are a helpful voice assistant. Speak naturally and concisely.",
                "initial_greeting": True,
                "greeting_instructions": "Greet the user warmly and ask how you can help them today.",
            },
            "audio": {
                "enable_thinking_sound": True,
                "thinking_sound": "subtle_pulse",
                "thinking_volume": 0.3,
                "enable_ambient": False,
                "ambient_sound": "soft_background",
                "ambient_volume": 0.1,
            },
            "limits": {
                "max_sessions_per_user": 3,
                "max_session_duration": 3600,
                "token_ttl_hours": 24,  # 24 hours to avoid expiration issues
            },
        }

    def get_tools(self) -> List[Any]:
        """
        Get list of tools available to the agent.

        Returns:
            List of tool instances (provided by the underlying agent system)
        """
        # Tools are provided by the underlying agent system
        return []

    @property
    def enabled(self) -> bool:
        """Check if real-time voice is enabled."""
        return self._realtime_config.get("enabled", True)

    @property
    def livekit_url(self) -> str:
        """Get LiveKit HTTP(S) base URL for LiveKit API calls."""
        return self._livekit_http_url

    @property
    def livekit_ws_url(self) -> str:
        """Get LiveKit WebSocket URL for clients (and worker)."""
        return self._livekit_ws_url

    def _derive_livekit_urls(self, raw: str) -> tuple[str, str]:
        """
        Derive websocket + http urls from a provided LIVEKIT_URL.

        Accepts:
        - ws://host or wss://host
        - http://host or https://host
        - with optional paths (kept)
        """
        parsed = urlparse(raw)
        scheme = (parsed.scheme or "").lower()

        # If user provided host without scheme, assume wss (most common)
        if not scheme:
            ws = urlunparse(("wss", parsed.netloc or parsed.path, "", "", "", ""))
            http = urlunparse(("https", parsed.netloc or parsed.path, "", "", "", ""))
            logger.warning(f"LIVEKIT_URL had no scheme; assuming wss/https for '{raw}'")
            return ws, http

        if scheme in ("wss", "ws"):
            http_scheme = "https" if scheme == "wss" else "http"
            http = urlunparse((http_scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
            ws = raw
            return ws, http

        if scheme in ("https", "http"):
            ws_scheme = "wss" if scheme == "https" else "ws"
            ws = urlunparse((ws_scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
            http = raw
            return ws, http

        # Unknown scheme: fall back to raw for both and let downstream raise a clearer error
        logger.warning(f"Unrecognized LIVEKIT_URL scheme '{scheme}' in '{raw}'. Using raw value for both ws/http.")
        return raw, raw

    @property
    def livekit_api_key(self) -> str:
        """Get LiveKit API key."""
        return self._livekit_api_key

    @property
    def livekit_api_secret(self) -> str:
        """Get LiveKit API secret."""
        return self._livekit_api_secret

    @property
    def room_empty_timeout(self) -> int:
        """Get room empty timeout in seconds."""
        return self._realtime_config.get("livekit", {}).get("room_empty_timeout", 300)

    @property
    def max_participants(self) -> int:
        """Get maximum participants per room."""
        return self._realtime_config.get("livekit", {}).get("max_participants", 2)

    @property
    def stt_model(self) -> str:
        """Get STT model from providers.openai.stt in config."""
        # Read from providers.openai.stt.model (as per config structure)
        openai_stt = self._voice_raw_config.get("providers", {}).get("openai", {}).get("stt", {})
        if "model" in openai_stt:
            return openai_stt["model"]
        # Fallback to Pydantic model (may have defaults)
        return self._voice_config.stt.model_id

    @property
    def stt_language(self) -> Optional[str]:
        """Get STT language from providers.openai.stt in config."""
        # Read from providers.openai.stt.language (as per config structure)
        openai_stt = self._voice_raw_config.get("providers", {}).get("openai", {}).get("stt", {})
        if "language" in openai_stt:
            return openai_stt["language"]
        # Fallback to Pydantic model (may have defaults)
        return self._voice_config.stt.language_code

    @property
    def llm_model(self) -> str:
        """Get LLM model name (default for real-time)."""
        # Use gpt-4o for real-time voice (better quality)
        return "gpt-4o"

    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature."""
        return 0.7

    @property
    def llm_max_tokens(self) -> int:
        """Get LLM max tokens."""
        return 1024

    @property
    def tts_model(self) -> str:
        """Get TTS model from providers.openai.tts in config."""
        # Read from providers.openai.tts.model (as per config structure)
        openai_tts = self._voice_raw_config.get("providers", {}).get("openai", {}).get("tts", {})
        if "model" in openai_tts:
            return openai_tts["model"]
        # Fallback to Pydantic model (may have defaults)
        return self._voice_config.tts.model_id

    @property
    def tts_voice(self) -> str:
        """Get TTS voice from providers.openai.tts in config."""
        # Read from providers.openai.tts.voice (as per config structure)
        # This is the actual location where the voice is specified for realtime mode
        openai_tts = self._voice_raw_config.get("providers", {}).get("openai", {}).get("tts", {})
        if "voice" in openai_tts:
            return openai_tts["voice"]
        # Fallback to Pydantic model (may have defaults)
        return self._voice_config.tts.voice_id

    @property
    def tts_speed(self) -> float:
        """Get TTS speed from providers.openai.tts in config."""
        # Read from providers.openai.tts.speed (as per config structure)
        openai_tts = self._voice_raw_config.get("providers", {}).get("openai", {}).get("tts", {})
        if "speed" in openai_tts:
            return openai_tts["speed"]
        # Fallback to Pydantic model (may have defaults)
        return self._voice_config.tts.speed or 1.0

    @property
    def vad_provider(self) -> str:
        """Get VAD provider."""
        return self._realtime_config.get("vad", {}).get("provider", "silero")

    @property
    def vad_activation_threshold(self) -> float:
        """Get VAD activation threshold (0.0-1.0). Higher = less sensitive to noise."""
        # Support both 'threshold' (legacy) and 'activation_threshold' (correct) for backward compatibility
        vad_config = self._realtime_config.get("vad", {})
        return vad_config.get("activation_threshold") or vad_config.get("threshold", 0.5)

    @property
    def vad_min_speech_duration(self) -> float:
        """Get VAD minimum speech duration in seconds."""
        return self._realtime_config.get("vad", {}).get("min_speech_duration", 0.05)

    @property
    def vad_min_silence_duration(self) -> float:
        """Get VAD minimum silence duration in seconds. Longer = better noise filtering."""
        return self._realtime_config.get("vad", {}).get("min_silence_duration", 0.55)

    @property
    def vad_prefix_padding_duration(self) -> float:
        """Get VAD prefix padding duration in seconds (audio before speech start)."""
        return self._realtime_config.get("vad", {}).get("prefix_padding_duration", 0.5)

    @property
    def vad_max_speech_duration(self) -> float:
        """Get VAD maximum speech duration in seconds (deprecated, use max_buffered_speech)."""
        return self._realtime_config.get("vad", {}).get("max_speech_duration", 60.0)

    @property
    def turn_detection_enabled(self) -> bool:
        """Check if turn detection is enabled."""
        # Default to False to avoid inference executor errors
        # Turn detection requires an inference executor which may not be available
        # in all environments (especially subprocess contexts)
        return self._realtime_config.get("turn_detection", {}).get("enabled", False)

    @property
    def min_endpointing_delay(self) -> float:
        """Get minimum endpointing delay."""
        return self._realtime_config.get("turn_detection", {}).get("min_endpointing_delay", 0.5)

    @property
    def max_endpointing_delay(self) -> float:
        """Get maximum endpointing delay."""
        return self._realtime_config.get("turn_detection", {}).get("max_endpointing_delay", 3.0)

    # Semantic Endpointing properties
    @property
    def semantic_endpointing_enabled(self) -> bool:
        """Check if semantic endpointing is enabled."""
        return self._realtime_config.get("semantic_endpointing", {}).get("enabled", True)

    @property
    def semantic_min_silence_ambiguous(self) -> float:
        """Get minimum silence duration for ambiguous utterances (seconds)."""
        return self._realtime_config.get("semantic_endpointing", {}).get("min_silence_ambiguous", 0.6)

    @property
    def semantic_min_silence_complete(self) -> float:
        """Get minimum silence duration for complete utterances (seconds)."""
        return self._realtime_config.get("semantic_endpointing", {}).get("min_silence_complete", 1.0)

    @property
    def semantic_max_buffer_duration(self) -> float:
        """Get maximum buffer duration before forcing endpoint (seconds)."""
        return self._realtime_config.get("semantic_endpointing", {}).get("max_buffer_duration", 30.0)

    @property
    def semantic_enable_logging(self) -> bool:
        """Check if semantic endpointing logging is enabled."""
        return self._realtime_config.get("semantic_endpointing", {}).get("enable_logging", False)

    @property
    def semantic_confidence_threshold(self) -> float:
        """Get semantic endpointing confidence threshold (0.0-1.0)."""
        return self._realtime_config.get("semantic_endpointing", {}).get("confidence_threshold", 0.7)

    @property
    def allow_interruptions(self) -> bool:
        """Check if interruptions are allowed."""
        return self._realtime_config.get("interruptions", {}).get("allow", True)

    @property
    def interruption_min_duration(self) -> float:
        """Get minimum interruption duration."""
        return self._realtime_config.get("interruptions", {}).get("min_duration", 0.5)

    @property
    def agent_type(self) -> AgentType:
        """Get default agent type."""
        agent_type_str = self._realtime_config.get("agent", {}).get("type", "moe")  # Default to MOE
        return AgentType(agent_type_str)

    @property
    def agent_instructions(self) -> str:
        """Get agent instructions."""
        return self._realtime_config.get("agent", {}).get(
            "instructions",
            "You are a helpful voice assistant. Speak naturally and concisely."
        )

    @property
    def initial_greeting(self) -> bool:
        """Check if initial greeting is enabled."""
        return self._realtime_config.get("agent", {}).get("initial_greeting", True)

    @property
    def initial_greeting_instructions(self) -> str:
        """Get initial greeting instructions."""
        return self._realtime_config.get("agent", {}).get(
            "greeting_instructions",
            "Greet the user warmly and ask how you can help them today."
        )

    @property
    def enable_thinking_sound(self) -> bool:
        """Check if thinking sound is enabled."""
        return self._realtime_config.get("audio", {}).get("enable_thinking_sound", True)

    @property
    def thinking_sound(self) -> str:
        """Get thinking sound name."""
        return self._realtime_config.get("audio", {}).get("thinking_sound", "subtle_pulse")

    @property
    def thinking_volume(self) -> float:
        """Get thinking sound volume."""
        return self._realtime_config.get("audio", {}).get("thinking_volume", 0.3)

    @property
    def enable_ambient(self) -> bool:
        """Check if ambient sound is enabled."""
        return self._realtime_config.get("audio", {}).get("enable_ambient", False)

    @property
    def ambient_sound(self) -> str:
        """Get ambient sound name."""
        return self._realtime_config.get("audio", {}).get("ambient_sound", "soft_background")

    @property
    def ambient_volume(self) -> float:
        """Get ambient sound volume."""
        return self._realtime_config.get("audio", {}).get("ambient_volume", 0.1)

    @property
    def max_sessions_per_user(self) -> int:
        """Get maximum sessions per user."""
        return self._realtime_config.get("limits", {}).get("max_sessions_per_user", 3)

    @property
    def max_session_duration(self) -> int:
        """Get maximum session duration in seconds."""
        return self._realtime_config.get("limits", {}).get("max_session_duration", 3600)

    @property
    def token_ttl_hours(self) -> int:
        """Get token TTL in hours."""
        return self._realtime_config.get("limits", {}).get("token_ttl_hours", 2)

    # -------------------------------------------------------------------------
    # LiveKit worker tuning (prevents OS SIGKILL / OOM by default)
    # -------------------------------------------------------------------------

    def _get_int_from_env(self, key: str) -> Optional[int]:
        raw = os.getenv(key)
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            logger.warning(f"Ignoring invalid int env var {key}={raw!r}")
            return None

    def _get_float_from_env(self, key: str) -> Optional[float]:
        raw = os.getenv(key)
        if raw is None or raw == "":
            return None
        try:
            return float(raw)
        except ValueError:
            logger.warning(f"Ignoring invalid float env var {key}={raw!r}")
            return None

    @property
    def worker_agent_name(self) -> str:
        """
        Logical agent name shown in LiveKit worker registration.

        Env override: OPENAGENTS_LIVEKIT_AGENT_NAME
        YAML: voice.realtime.worker.agent_name
        """
        env = os.getenv("OPENAGENTS_LIVEKIT_AGENT_NAME")
        if env:
            return env
        return self._realtime_config.get("worker", {}).get("agent_name", "openagents-voice")

    @property
    def worker_num_idle_processes(self) -> int:
        """
        Number of idle job processes to keep warm.

        Env override: OPENAGENTS_LIVEKIT_NUM_IDLE_PROCESSES
        YAML: voice.realtime.worker.num_idle_processes

        Default: 1 (prevents 4+ torch copies on laptops)
        """
        env = self._get_int_from_env("OPENAGENTS_LIVEKIT_NUM_IDLE_PROCESSES")
        if env is not None:
            return max(0, env)
        return int(self._realtime_config.get("worker", {}).get("num_idle_processes", 1))

    @property
    def worker_port(self) -> int:
        """
        Port for LiveKit worker internal HTTP server (health/metrics).
        0 lets LiveKit pick a free port.

        Env override: OPENAGENTS_LIVEKIT_WORKER_PORT
        YAML: voice.realtime.worker.port
        """
        env = self._get_int_from_env("OPENAGENTS_LIVEKIT_WORKER_PORT")
        if env is not None:
            return max(0, env)
        return int(self._realtime_config.get("worker", {}).get("port", 0))

    @property
    def worker_job_memory_warn_mb(self) -> float:
        """
        Memory warning threshold (MB) per job process.

        Env override: OPENAGENTS_LIVEKIT_JOB_MEMORY_WARN_MB
        YAML: voice.realtime.worker.job_memory_warn_mb
        """
        env = self._get_float_from_env("OPENAGENTS_LIVEKIT_JOB_MEMORY_WARN_MB")
        if env is not None:
            return max(0.0, env)
        return float(self._realtime_config.get("worker", {}).get("job_memory_warn_mb", 700))

    @property
    def worker_job_memory_limit_mb(self) -> float:
        """
        Hard memory limit (MB) per job process.
        0 disables the limit.

        Env override: OPENAGENTS_LIVEKIT_JOB_MEMORY_LIMIT_MB
        YAML: voice.realtime.worker.job_memory_limit_mb
        """
        env = self._get_float_from_env("OPENAGENTS_LIVEKIT_JOB_MEMORY_LIMIT_MB")
        if env is not None:
            return max(0.0, env)
        return float(self._realtime_config.get("worker", {}).get("job_memory_limit_mb", 0))

    @property
    def worker_load_threshold(self) -> float:
        """
        Worker load threshold beyond which it is marked unavailable.

        Env override: OPENAGENTS_LIVEKIT_LOAD_THRESHOLD
        YAML: voice.realtime.worker.load_threshold
        """
        env = self._get_float_from_env("OPENAGENTS_LIVEKIT_LOAD_THRESHOLD")
        if env is not None:
            return max(0.0, env)
        return float(self._realtime_config.get("worker", {}).get("load_threshold", 0.7))
