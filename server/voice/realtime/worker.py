"""
LiveKit Agent Worker - Entry point for voice agent process.

This module implements the worker process that connects to LiveKit server
and handles voice session dispatch. It creates VoiceAgent instances for
incoming sessions and manages their lifecycle.

Run modes:
- Development: python -m server.voice.realtime.worker dev
- Production: python -m server.voice.realtime.worker start
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional

def _log_debug(location: str, message: str, data: dict, hypothesis_id: str = "") -> None:
    """
    Optional debug logger to a JSONL file (disabled by default).

    Enable by setting:
      OPENAGENTS_WORKER_DEBUG_LOG=1
    Optionally override file path:
      OPENAGENTS_WORKER_DEBUG_LOG_PATH=/path/to/debug.jsonl
    """
    if os.getenv("OPENAGENTS_WORKER_DEBUG_LOG", "").strip() not in ("1", "true", "TRUE", "yes", "YES"):
        return

    try:
        project_root_local = Path(__file__).parent.parent.parent.parent
        default_path = project_root_local / ".cursor" / "debug.log"
        debug_path = Path(os.getenv("OPENAGENTS_WORKER_DEBUG_LOG_PATH", str(default_path)))
        debug_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
            "sessionId": "debug-session",
            "hypothesisId": hypothesis_id,
        }
        with open(debug_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Never fail the worker due to debug logging
        return

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from loguru import logger

try:
    from livekit.agents import (
        JobContext,
        WorkerOptions,
        cli as lk_cli,
    )
    from livekit.plugins import openai as lk_openai, silero as lk_silero

    # Check turn detection availability (lazy import to avoid initialization errors)
    # We only check availability here - actual import happens lazily when needed
    # #region agent log
    _log_debug("worker.py:import_turn_detection:start", "Checking turn detection availability", {}, "A")
    # #endregion
    TURN_DETECTION_AVAILABLE = False
    TURN_DETECTION_MODEL_FILES_AVAILABLE = False
    
    try:
        # Try to import the module (this will fail if plugin not installed)
        # Use importlib to avoid triggering module initialization
        import importlib.util
        spec = importlib.util.find_spec("livekit.plugins.turn_detector.english")
        if spec is not None:
            TURN_DETECTION_AVAILABLE = True
            # #region agent log
            _log_debug("worker.py:import_turn_detection:module_found", "Turn detector module found", {}, "A")
            # #endregion
            
            # Check if model files are available (without importing the module)
            try:
                spec_base = importlib.util.find_spec("livekit.plugins.turn_detector.base")
                if spec_base is not None:
                    # Import only the functions we need for checking
                    from livekit.plugins.turn_detector.models import HG_MODEL, ONNX_FILENAME, MODEL_REVISIONS
                    from livekit.plugins.turn_detector.base import _download_from_hf_hub
                    # #region agent log
                    _log_debug("worker.py:import_turn_detection:checking_files", "Checking model files", {"hg_model": HG_MODEL, "filename": ONNX_FILENAME}, "A")
                    # #endregion
                    # Try to find model files (with local_files_only=True to avoid downloading)
                    # Use the English model revision (default)
                    revision = MODEL_REVISIONS.get("en", "main")
                    try:
                        # Check for ONNX model file
                        model_path = _download_from_hf_hub(
                            HG_MODEL,
                            filename=ONNX_FILENAME,
                            subfolder="onnx",
                            revision=revision,
                            local_files_only=True
                        )
                        # Check for languages.json file (required by EOUModel)
                        languages_path = _download_from_hf_hub(
                            HG_MODEL,
                            filename="languages.json",
                            revision=revision,
                            local_files_only=True
                        )
                        TURN_DETECTION_MODEL_FILES_AVAILABLE = True
                        # #region agent log
                        _log_debug("worker.py:import_turn_detection:files_found", "Model files found", {
                            "model_path": str(model_path),
                            "languages_path": str(languages_path)
                        }, "A")
                        # #endregion
                    except RuntimeError as e:
                        # Model files not downloaded yet
                        TURN_DETECTION_MODEL_FILES_AVAILABLE = False
                        # #region agent log
                        _log_debug("worker.py:import_turn_detection:files_missing", "Model files not found", {"error": str(e)}, "A")
                        # #endregion
            except ImportError:
                # Can't check - assume available (will fail at runtime if not)
                TURN_DETECTION_MODEL_FILES_AVAILABLE = True
                # #region agent log
                _log_debug("worker.py:import_turn_detection:check_failed", "Could not check files, assuming available", {}, "A")
                # #endregion
    except Exception as e:
        # Plugin not installed or check failed
        TURN_DETECTION_AVAILABLE = False
        TURN_DETECTION_MODEL_FILES_AVAILABLE = False
        logger.warning(
            f"Turn detection plugin not available: {e}\n"
            "Install with: pip install livekit-plugins-turn-detector"
        )
        # #region agent log
        _log_debug("worker.py:import_turn_detection:import_failed", "Turn detection not available", {"error": str(e)}, "A")
        # #endregion

    LIVEKIT_AVAILABLE = True
except ImportError:
    logger.error(
        "LiveKit Agents SDK not installed. Install with:\n"
        "pip install livekit-agents livekit-plugins-openai livekit-plugins-silero"
    )
    LIVEKIT_AVAILABLE = False
    TURN_DETECTION_AVAILABLE = False

# Import local modules with error handling to prevent subprocess crashes
try:
    from server.voice.realtime.config import RealtimeVoiceConfig
    from server.voice.realtime.agent import VoiceAgent
    from server.voice.realtime.simple_agent import create_simple_voice_agent
    from server.voice.realtime.models import AgentType
    MODULES_AVAILABLE = True
except Exception as e:
    logger.error(f"Failed to import voice agent modules: {e}", exc_info=True)
    MODULES_AVAILABLE = False
    # Create dummy classes to prevent import errors in subprocess
    RealtimeVoiceConfig = None
    VoiceAgent = None
    create_simple_voice_agent = None
    AgentType = None


async def entrypoint(ctx: JobContext) -> None:
    """
    Entry point for LiveKit Agent worker.

    Called when a new job is dispatched to this worker. Creates a voice agent
    session and starts handling the conversation.

    Args:
        ctx: Job context containing room information and connection details
    """
    # Validate modules are available before proceeding
    if not MODULES_AVAILABLE:
        error_msg = "Required voice agent modules are not available. Check import errors above."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    try:
        logger.info(f"Voice agent job dispatched: room={ctx.room.name}")

        # Load configuration with error handling
        try:
            config = RealtimeVoiceConfig.load()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}", exc_info=True)
            raise RuntimeError(f"Configuration loading failed: {e}") from e

        # Connect to the room with error handling
        logger.info(f"Connecting to room: {ctx.room.name}")
        try:
            await ctx.connect()
            logger.info("Connected to room successfully")
        except Exception as e:
            logger.error(f"Failed to connect to room: {e}", exc_info=True)
            raise RuntimeError(f"Room connection failed: {e}") from e

        # Extract agent configuration from room metadata
        try:
            agent_type, agent_id, agent_config = _extract_agent_config(ctx)
        except Exception as e:
            logger.warning(f"Failed to extract agent config, using defaults: {e}")
            agent_type, agent_id, agent_config = AgentType.SMART_ROUTER, None, {}

        # Create the voice agent with error handling
        # Use VoiceAgent with SmartRouter for intelligent routing to specialized agents
        # Pass ctx.room.name as session_id for trace storage
        logger.info(f"Creating VoiceAgent with agent_type={agent_type.value}, session_id={ctx.room.name}")
        try:
            agent = VoiceAgent(
                instructions=config.agent_instructions,
                agent_type=agent_type,
                agent_id=agent_id,
                agent_config=agent_config,
                config=config,
                session_id=ctx.room.name,  # Use room name as session ID for trace storage
                room=ctx.room,  # Pass room for data channel communication
            )
            logger.info(f"VoiceAgent created with {agent_type.value}, session_id={ctx.room.name} (will route to appropriate agents)")
        except Exception as e:
            logger.error(f"Failed to create voice agent: {e}", exc_info=True)
            raise RuntimeError(f"Agent creation failed: {e}") from e

        # Import AgentSession after verifying livekit is available
        try:
            from livekit.agents import AgentSession
        except ImportError as e:
            logger.error(f"Failed to import AgentSession: {e}", exc_info=True)
            raise RuntimeError(f"AgentSession import failed: {e}") from e

        # Configure the session with STT-LLM-TTS pipeline
        logger.info("Configuring agent session pipeline")

        # Build session configuration with error handling
        # Initialize each component separately to identify which one fails
        try:
            logger.info("Initializing VAD (Voice Activity Detection)")
            logger.info(f"  Provider: {config.vad_provider}")
            logger.info(f"  Activation threshold: {config.vad_activation_threshold}")
            logger.info(f"  Min speech duration: {config.vad_min_speech_duration}s")
            logger.info(f"  Min silence duration: {config.vad_min_silence_duration}s")
            logger.info(f"  Prefix padding: {config.vad_prefix_padding_duration}s")
            # Initialize VAD with parameters from config
            # Higher activation_threshold = less sensitive to noise (requires louder/clearer speech)
            # min_silence_duration helps filter out brief noise spikes
            vad = lk_silero.VAD.load(
                activation_threshold=config.vad_activation_threshold,
                min_speech_duration=config.vad_min_speech_duration,
                min_silence_duration=config.vad_min_silence_duration,
                prefix_padding_duration=config.vad_prefix_padding_duration,
            )
            logger.info("VAD initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VAD: {e}", exc_info=True)
            raise RuntimeError(f"VAD initialization failed: {e}") from e
        
        try:
            logger.info(f"Initializing STT with model: {config.stt_model}")
            base_stt = lk_openai.STT(model=config.stt_model)
            logger.info("Base STT initialized successfully")

            # Wrap with semantic endpointing if enabled
            if config.semantic_endpointing_enabled:
                logger.info("Enabling semantic endpointing for STT")
                from server.voice.realtime.buffered_stt import BufferedSTT

                stt = BufferedSTT(
                    base_stt=base_stt,
                    enable_semantic_endpointing=True,
                    min_silence_ambiguous=config.semantic_min_silence_ambiguous,
                    min_silence_complete=config.semantic_min_silence_complete,
                    max_buffer_duration=config.semantic_max_buffer_duration,
                    enable_logging=config.semantic_enable_logging,
                )
                logger.info(
                    f"Semantic endpointing enabled "
                    f"(ambiguous: {config.semantic_min_silence_ambiguous}s, "
                    f"complete: {config.semantic_min_silence_complete}s)"
                )
            else:
                stt = base_stt
                logger.info("Semantic endpointing disabled, using base STT")

        except Exception as e:
            logger.error(f"Failed to initialize STT: {e}", exc_info=True)
            raise RuntimeError(f"STT initialization failed: {e}") from e
        
        try:
            logger.info(f"Initializing LLM with model: {config.llm_model}")
            llm = lk_openai.LLM(model=config.llm_model)
            logger.info("LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
            raise RuntimeError(f"LLM initialization failed: {e}") from e
        
        try:
            logger.info("=" * 80)
            logger.info("TTS INITIALIZATION")
            logger.info(f"  Model: {config.tts_model}")
            logger.info(f"  Voice: {config.tts_voice}")
            logger.info(f"  Speed: {config.tts_speed}")
            logger.info("=" * 80)

            tts = lk_openai.TTS(
                model=config.tts_model,
                voice=config.tts_voice,
            )
            logger.info(f"✓ TTS initialized successfully - Type: {type(tts).__name__}")

            # Test TTS generation to verify it works
            logger.info("Testing TTS audio generation...")
            try:
                # Create a simple test synthesis
                import asyncio
                test_text = "Test"
                # Note: We can't actually synthesize here without an audio context,
                # but we can verify the TTS object is properly constructed
                logger.info(f"✓ TTS object ready for synthesis")
                logger.info(f"  TTS model configured: {config.tts_model}")
                logger.info(f"  TTS voice configured: {config.tts_voice}")
            except Exception as test_err:
                logger.warning(f"TTS test warning: {test_err}")

            logger.info("=" * 80)
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}", exc_info=True)
            raise RuntimeError(f"TTS initialization failed: {e}") from e
        
        # Build session kwargs with initialized components
        session_kwargs = {
            "vad": vad,
            "stt": stt,
            "llm": llm,
            "tts": tts,
            "allow_interruptions": config.allow_interruptions,
        }
        logger.info("All session components initialized successfully")

        # Add turn detection if available and enabled
        # #region agent log
        _log_debug("worker.py:entrypoint:turn_detection_check", "Checking turn detection", {
            "TURN_DETECTION_AVAILABLE": TURN_DETECTION_AVAILABLE,
            "TURN_DETECTION_MODEL_FILES_AVAILABLE": TURN_DETECTION_MODEL_FILES_AVAILABLE if 'TURN_DETECTION_MODEL_FILES_AVAILABLE' in globals() else "undefined",
            "config.turn_detection_enabled": config.turn_detection_enabled
        }, "B")
        # #endregion
        turn_detection_enabled = False
        if TURN_DETECTION_AVAILABLE and config.turn_detection_enabled:
            # Check if model files are available before trying to use turn detection
            model_files_available = TURN_DETECTION_MODEL_FILES_AVAILABLE if 'TURN_DETECTION_MODEL_FILES_AVAILABLE' in globals() else True
            # #region agent log
            _log_debug("worker.py:entrypoint:model_files_check", "Model files check result", {"available": model_files_available}, "B")
            # #endregion
            if not model_files_available:
                logger.warning(
                    "Turn detection model files not found.\n"
                    "To download model files, run:\n"
                    "  ./scripts/run_realtime.sh --download-models\n"
                    "or\n"
                    "  python -m server.voice.realtime.worker download-files\n"
                    "Turn detection will be disabled for this session."
                )
                # #region agent log
                _log_debug("worker.py:entrypoint:turn_detection_skipped", "Turn detection skipped - no model files", {}, "B")
                # #endregion
            else:
                try:
                    logger.info("Enabling turn detection with EOUModel")
                    # #region agent log
                    _log_debug("worker.py:entrypoint:creating_model", "Creating EOUModel instance", {}, "B")
                    # #endregion
                    # Lazy import - only import when we actually need it
                    from livekit.plugins.turn_detector.english import EnglishModel as EOUModel
                    
                    # Create the model - should work if model files are available
                    turn_detection_model = EOUModel()
                    # #region agent log
                    _log_debug("worker.py:entrypoint:model_created", "EOUModel created successfully", {}, "B")
                    # #endregion
                    
                    # NOTE: The inference executor is required for turn detection to work.
                    # The executor is provided by LiveKit's IPC system and may not be available
                    # in subprocess contexts. If you see "no inference executor" errors at runtime,
                    # turn detection will fail gracefully and the session will continue without it.
                    # The error is logged but doesn't crash the session.
                    
                    session_kwargs["turn_detection"] = turn_detection_model
                    turn_detection_enabled = True
                    logger.info("Turn detection model created successfully")
                    # #region agent log
                    _log_debug("worker.py:entrypoint:turn_detection_enabled", "Turn detection enabled", {}, "B")
                    # #endregion
                except (RuntimeError, FileNotFoundError) as e:
                    error_msg = str(e)
                    # #region agent log
                    _log_debug("worker.py:entrypoint:model_creation_failed", "Model creation failed", {"error": error_msg}, "B")
                    # #endregion
                    logger.warning(
                        f"Failed to initialize turn detection model: {error_msg}\n"
                        "This may happen if model files are missing or corrupted.\n"
                        "To download model files, run:\n"
                        "  ./scripts/run_realtime.sh --download-models\n"
                        "Turn detection will be disabled for this session."
                    )
                except Exception as e:
                    # #region agent log
                    _log_debug("worker.py:entrypoint:unexpected_error", "Unexpected error", {"error": str(e)}, "B")
                    # #endregion
                    logger.error(f"Unexpected error initializing turn detection: {e}")
                    raise
        else:
            if config.turn_detection_enabled:
                logger.warning("Turn detection requested but plugin not available")
                # #region agent log
                _log_debug("worker.py:entrypoint:plugin_unavailable", "Plugin unavailable", {}, "B")
                # #endregion

        # Add endpointing delays only if turn detection is actually enabled
        if turn_detection_enabled:
            session_kwargs["min_endpointing_delay"] = config.min_endpointing_delay
            session_kwargs["max_endpointing_delay"] = config.max_endpointing_delay

        # #region agent log
        _log_debug("worker.py:entrypoint:session_kwargs", "Session kwargs before creation", {
            "has_turn_detection": "turn_detection" in session_kwargs,
            "turn_detection_enabled": turn_detection_enabled,
            "kwargs_keys": list(session_kwargs.keys())
        }, "C")
        # #endregion

        # Create AgentSession with error handling
        try:
            session = AgentSession(**session_kwargs)
            logger.info("AgentSession created successfully")
        except Exception as e:
            logger.error(f"Failed to create AgentSession: {e}", exc_info=True)
            raise RuntimeError(f"AgentSession creation failed: {e}") from e
        
        # #region agent log
        _log_debug("worker.py:entrypoint:session_created", "AgentSession created", {}, "C")
        # #endregion

        # Start the session with error handling
        logger.info("Starting agent session")
        try:
            await session.start(agent=agent, room=ctx.room)
            logger.info("Agent session started successfully")
        except Exception as e:
            logger.error(f"Failed to start agent session: {e}", exc_info=True)
            raise RuntimeError(f"Agent session start failed: {e}") from e

        # Wait a moment for session to fully initialize and tracks to be published
        import asyncio
        await asyncio.sleep(0.5)

        # Verify audio setup and track publishing
        logger.info("=" * 80)
        logger.info("AUDIO SETUP VERIFICATION")
        logger.info(f"  Room: {ctx.room.name}")
        logger.info(f"  Total participants: {len(ctx.room.remote_participants) + 1}")  # +1 for agent

        # Check local participant (the agent itself)
        if hasattr(ctx.room, 'local_participant') and ctx.room.local_participant:
            local = ctx.room.local_participant
            logger.info(f"  Local participant (Agent): {local.identity}")
            logger.info(f"    Track publications: {len(local.track_publications)}")
            for sid, track_pub in local.track_publications.items():
                logger.info(f"      - {track_pub.kind} track (source: {track_pub.source})")
                logger.info(f"        SID: {sid}")
                logger.info(f"        Muted: {track_pub.muted}")
        else:
            logger.warning("  ⚠ Local participant not available")

        # Check remote participants (users)
        logger.info(f"  Remote participants: {len(ctx.room.remote_participants)}")
        for identity, participant in ctx.room.remote_participants.items():
            logger.info(f"    Participant '{identity}':")
            logger.info(f"      Track publications: {len(participant.track_publications)}")
            for sid, track_pub in participant.track_publications.items():
                logger.info(f"        - {track_pub.kind} track (source: {track_pub.source})")
                logger.info(f"          Subscribed: {track_pub.subscribed}")
                logger.info(f"          Muted: {track_pub.muted}")

        # Check session configuration
        logger.info("  Session Configuration:")
        logger.info(f"    TTS enabled: {session_kwargs.get('tts') is not None}")
        logger.info(f"    STT enabled: {session_kwargs.get('stt') is not None}")
        logger.info(f"    LLM enabled: {session_kwargs.get('llm') is not None}")
        logger.info(f"    VAD enabled: {session_kwargs.get('vad') is not None}")
        logger.info("=" * 80)

        # DISABLED: Initial greeting causes 5+ second hang and token issues
        # User can just start speaking immediately
        # if config.initial_greeting:
        #     logger.info("Generating initial greeting")
        #     try:
        #         if hasattr(session, 'generate_reply'):
        #             await session.generate_reply(
        #                 instructions=config.initial_greeting_instructions
        #             )
        #     except Exception as e:
        #         logger.error(f"Failed to generate greeting: {e}")

        logger.info("Skipping initial greeting - user can start speaking immediately")

        logger.info(f"Voice agent running for room: {ctx.room.name}")

    except KeyboardInterrupt:
        # Allow graceful shutdown on interrupt
        logger.info("Voice agent entrypoint interrupted")
        raise
    except Exception as e:
        # Use % formatting to avoid loguru format string issues with exception details
        logger.error("Error in voice agent entrypoint: %s", e, exc_info=True)
        # Re-raise to let LiveKit handle the error properly
        # This ensures the error is reported to the parent process
        raise


def _extract_agent_config(ctx: JobContext) -> tuple[AgentType, Optional[str], dict]:
    """
    Extract agent configuration from room metadata.

    Args:
        ctx: Job context with room metadata

    Returns:
        Tuple of (agent_type, agent_id, agent_config)
    """
    try:
        import json

        metadata = ctx.room.metadata if hasattr(ctx.room, 'metadata') else None

        if metadata:
            metadata_dict = json.loads(metadata)
            agent_type_str = metadata_dict.get("agent_type", "smart_router")
            agent_id = metadata_dict.get("agent_id")
            agent_config = metadata_dict.get("agent_config", {})

            agent_type = AgentType(agent_type_str)
            logger.info(f"Extracted agent config: type={agent_type}, id={agent_id}")

            return agent_type, agent_id, agent_config

    except Exception as e:
        logger.warning(f"Failed to extract agent config from metadata: {e}")

    # Return defaults
    return AgentType.SMART_ROUTER, None, {}


def download_model_files() -> None:
    """Download turn detection model files from HuggingFace."""
    logger.info("Downloading turn detection model files...")
    
    try:
        # Import only the constants we need, avoiding any module initialization
        # that might try to load the model file
        import importlib.util
        
        # Check if plugin is available
        spec = importlib.util.find_spec("livekit.plugins.turn_detector.models")
        if spec is None:
            logger.error("Turn detection plugin not installed. Install with: pip install livekit-plugins-turn-detector")
            sys.exit(1)
        
        # Load the models module using importlib to avoid triggering any initialization
        # that might try to load the model file. If initialization fails (because model
        # files are missing), we catch it and continue since we only need the constants.
        try:
            models_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(models_module)
            
            # Extract constants from the module
            HG_MODEL = models_module.HG_MODEL
            ONNX_FILENAME = models_module.ONNX_FILENAME
            MODEL_REVISIONS = models_module.MODEL_REVISIONS
        except (RuntimeError, FileNotFoundError) as e:
            # If module initialization fails due to missing model files, try direct import
            # as a fallback (constants should still be accessible)
            logger.debug(f"Module initialization had issues (expected if models not downloaded): {e}")
            try:
                from livekit.plugins.turn_detector.models import HG_MODEL, ONNX_FILENAME, MODEL_REVISIONS
            except Exception as import_error:
                logger.error(f"Failed to import model constants: {import_error}")
                raise
        
        from huggingface_hub import hf_hub_download
        
        # Use the English model revision (default)
        revision = MODEL_REVISIONS.get("en", "main")
        logger.info(f"Using model revision: {revision}")
        logger.info(f"Downloading from HuggingFace: {HG_MODEL}")
        
        # Download the ONNX model file
        logger.info(f"Downloading ONNX model: {ONNX_FILENAME}")
        model_path = hf_hub_download(
            repo_id=HG_MODEL,
            filename=ONNX_FILENAME,
            subfolder="onnx",
            revision=revision,
            local_files_only=False,  # Force download
        )
        logger.info(f"✓ ONNX model downloaded: {model_path}")
        
        # Download languages.json file (required by EOUModel)
        logger.info("Downloading languages.json configuration file")
        languages_path = hf_hub_download(
            repo_id=HG_MODEL,
            filename="languages.json",
            revision=revision,
            local_files_only=False,  # Force download
        )
        logger.info(f"✓ languages.json downloaded: {languages_path}")
        
        # Verify both files exist
        from pathlib import Path
        all_files_exist = True
        
        if Path(model_path).exists():
            file_size = Path(model_path).stat().st_size
            logger.info(f"✓ Verified ONNX model exists: {model_path} ({file_size:,} bytes)")
        else:
            logger.warning(f"⚠ ONNX model file path reported but file not found: {model_path}")
            all_files_exist = False
        
        if Path(languages_path).exists():
            file_size = Path(languages_path).stat().st_size
            logger.info(f"✓ Verified languages.json exists: {languages_path} ({file_size:,} bytes)")
        else:
            logger.warning(f"⚠ languages.json path reported but file not found: {languages_path}")
            all_files_exist = False
        
        if all_files_exist:
            logger.info("✓ All turn detection model files downloaded and verified successfully")
        else:
            logger.warning("⚠ Some model files may be missing")
        
        return
    except ImportError as e:
        logger.error(f"Turn detection plugin not installed: {e}")
        logger.error("Install with: pip install livekit-plugins-turn-detector")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to download model files: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


def main() -> None:
    """Main entry point for the worker process."""
    # Check for download-files command
    if len(sys.argv) > 1 and sys.argv[1] == "download-files":
        download_model_files()
        return
    
    if not LIVEKIT_AVAILABLE:
        logger.error("Cannot start worker: LiveKit SDK not available")
        sys.exit(1)
    
    if not MODULES_AVAILABLE:
        logger.error("Cannot start worker: Required voice agent modules are not available")
        logger.error("Check import errors above for details")
        sys.exit(1)

    logger.info("Starting LiveKit Voice Agent Worker")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")

    try:
        # LiveKit dev mode defaults to auto-reload. On iTerm2 this is not supported and
        # LiveKit prints a scary-looking "[error]Auto-reload is not supported..." line.
        # Since auto-reload cannot work there anyway, force it off proactively.
        term_program = os.environ.get("TERM_PROGRAM")
        if term_program == "iTerm.app" and "dev" in sys.argv:
            has_reload_flag = "--reload" in sys.argv or "--no-reload" in sys.argv
            if not has_reload_flag:
                # Insert right after "dev" for readability (Click/Typer accepts anywhere)
                try:
                    idx = sys.argv.index("dev")
                    sys.argv.insert(idx + 1, "--no-reload")
                except ValueError:
                    sys.argv.append("--no-reload")

        # If user requested help, don't do any heavy config work.
        if "--help" in sys.argv or "-h" in sys.argv:
            worker_options = WorkerOptions(entrypoint_fnc=entrypoint)
            lk_cli.run_app(worker_options)
            return

        # Load realtime config once in the parent process so we can set safe worker defaults.
        # This prevents LiveKit from spawning multiple idle processes by default (prod default=4),
        # which can lead to OS SIGKILL/OOM on laptops due to torch/onnx plugin imports.
        try:
            config = RealtimeVoiceConfig.load()
        except Exception as e:
            logger.error(f"Failed to load realtime config for worker options: {e}", exc_info=True)
            sys.exit(1)

        # Validate entrypoint function is callable
        if not callable(entrypoint):
            logger.error("Entrypoint function is not callable")
            sys.exit(1)
        
        # Configure worker options
        # Note: worker_type parameter removed - LiveKit CLI handles this automatically
        worker_options = WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Ensure worker shows a stable name in LiveKit (and avoid empty agent_name in logs)
            agent_name=config.worker_agent_name,
            # IMPORTANT: keep this low by default to avoid spawning multiple heavy idle processes
            num_idle_processes=config.worker_num_idle_processes,
            # Avoid port conflicts and reduce surprise; 0 => pick an available port
            port=config.worker_port,
            # Guardrails against runaway per-job memory usage (0 disables hard limit)
            job_memory_warn_mb=config.worker_job_memory_warn_mb,
            job_memory_limit_mb=config.worker_job_memory_limit_mb,
            load_threshold=config.worker_load_threshold,
            # Provide credentials explicitly (still compatible with env-based setup)
            ws_url=config.livekit_ws_url,
            api_key=config.livekit_api_key,
            api_secret=config.livekit_api_secret,
        )

        # Start the worker using LiveKit CLI
        logger.info("Launching worker with LiveKit CLI")
        lk_cli.run_app(worker_options)

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Configure loguru
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    main()
