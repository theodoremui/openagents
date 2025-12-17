"""
Voice Module REST API Router

FastAPI router with endpoints for TTS, STT, voice management, and configuration.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, Response
from typing import Optional, List
import logging
from datetime import datetime

from .service import VoiceService
from .models import (
    SynthesizeRequest,
    TranscriptResponse,
    TranscriptResult,
    VoiceInfo,
    VoiceConfigResponse,
    VoiceConfigUpdate,
    HealthResponse,
    HealthStatus,
    ProviderPreferenceRequest,
    SelectionStrategy,
    ProviderType
)
from .dependencies import get_voice_service
from .exceptions import VoiceException
from .utils import generate_request_id
from .coordinator import ProviderPreference

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/voice", tags=["voice"])


# Helper function to convert request preferences to coordinator preferences
def _convert_preferences(
    request_prefs: Optional[ProviderPreferenceRequest]
) -> Optional[ProviderPreference]:
    """Convert API request preferences to coordinator preferences."""
    if not request_prefs:
        return None

    # Import provider types from coordinator
    from .providers import ProviderType as CoordinatorProviderType
    from .coordinator import SelectionStrategy as CoordinatorSelectionStrategy

    # Map request enums to coordinator enums
    provider_map = {
        ProviderType.OPENAI: CoordinatorProviderType.OPENAI,
        ProviderType.ELEVENLABS: CoordinatorProviderType.ELEVENLABS,
        ProviderType.LIVEKIT: CoordinatorProviderType.LIVEKIT,
    }

    strategy_map = {
        SelectionStrategy.COST_OPTIMIZED: CoordinatorSelectionStrategy.COST_OPTIMIZED,
        SelectionStrategy.QUALITY_OPTIMIZED: CoordinatorSelectionStrategy.QUALITY_OPTIMIZED,
        SelectionStrategy.LATENCY_OPTIMIZED: CoordinatorSelectionStrategy.LATENCY_OPTIMIZED,
        SelectionStrategy.EXPLICIT: CoordinatorSelectionStrategy.EXPLICIT,
    }

    return ProviderPreference(
        strategy=strategy_map[request_prefs.strategy],
        preferred_provider=provider_map.get(request_prefs.preferred_provider) if request_prefs.preferred_provider else None,
        fallback_enabled=request_prefs.fallback_enabled,
        max_cost_per_request=request_prefs.max_cost_per_request
    )


@router.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (mp3, wav, webm, ogg)"),
    language_code: Optional[str] = Query(None, description="ISO 639-1 language code"),
    tag_audio_events: bool = Query(False, description="Tag audio events like laughter"),
    provider_strategy: Optional[SelectionStrategy] = Query(None, description="Provider selection strategy"),
    preferred_provider: Optional[ProviderType] = Query(None, description="Preferred provider (explicit strategy)"),
    fallback_enabled: bool = Query(True, description="Enable provider fallback on failure"),
    service: VoiceService = Depends(get_voice_service)
) -> TranscriptResponse:
    """
    Transcribe uploaded audio file to text.

    Supports: mp3, wav, webm, ogg formats
    Max file size: 25MB (ElevenLabs limit)

    Returns transcription with word-level timestamps and confidence scores.

    Provider Selection:
    - provider_strategy: Choose provider based on cost, quality, or latency
    - preferred_provider: Explicitly select OpenAI or ElevenLabs (requires explicit strategy)
    - fallback_enabled: Automatically fallback to alternative provider on failure
    """
    request_id = generate_request_id()
    start_time = datetime.now()

    try:
        # Read audio data
        audio_data = await audio.read()

        logger.info(
            f"[{request_id}] Transcription request: {audio.filename}, "
            f"{len(audio_data)} bytes, strategy={provider_strategy}, provider={preferred_provider}"
        )

        # Build provider preferences if specified
        provider_preferences = None
        if provider_strategy or preferred_provider:
            pref_request = ProviderPreferenceRequest(
                strategy=provider_strategy or SelectionStrategy.COST_OPTIMIZED,
                preferred_provider=preferred_provider,
                fallback_enabled=fallback_enabled
            )
            provider_preferences = _convert_preferences(pref_request)

        # Transcribe
        result = await service.transcribe(
            audio_data=audio_data,
            config=None,  # Use defaults, could accept config overrides
            provider_preferences=provider_preferences
        )

        # Calculate processing time
        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return TranscriptResponse(
            success=True,
            result=result,
            request_id=request_id,
            processing_time_ms=processing_time_ms
        )

    except VoiceException as e:
        logger.error(f"[{request_id}] Transcription failed: {e.message}")
        raise HTTPException(
            status_code=400 if e.error_code.value.startswith("VOICE_4") else 500,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/synthesize")
async def synthesize_speech(
    request: SynthesizeRequest,
    service: VoiceService = Depends(get_voice_service)
) -> Response:
    """
    Convert text to speech and return audio.

    Returns audio file directly (Content-Type: audio/mpeg or audio/pcm).

    Provider Selection:
    - Specify provider_preferences in request body to control provider selection
    - Supports cost-optimized, quality-optimized, or explicit provider selection
    - Automatic fallback to alternative providers on failure
    """
    req_id = generate_request_id()

    try:
        logger.info(
            f"[{req_id}] Synthesis request: {len(request.text)} characters, "
            f"strategy={request.provider_preferences.strategy if request.provider_preferences else 'default'}"
        )

        # Convert provider preferences
        provider_preferences = _convert_preferences(request.provider_preferences)

        # Synthesize
        result = await service.synthesize(
            text=request.text,
            config=None,  # TODO: Map request params to config
            profile_name=request.profile_name,
            provider_preferences=provider_preferences
        )

        # Return audio as response
        return Response(
            content=result.audio_data,
            media_type=result.content_type,
            headers={
                "X-Request-ID": result.request_id,
                "X-Character-Count": str(result.character_count),
                "X-Duration-MS": str(result.duration_ms) if result.duration_ms else "0"
            }
        )

    except VoiceException as e:
        logger.error(f"[{req_id}] Synthesis failed: {e.message}")
        raise HTTPException(
            status_code=400 if e.error_code.value.startswith("VOICE_3") else 500,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error(f"[{req_id}] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/synthesize/stream")
async def stream_synthesize_speech(
    request: SynthesizeRequest,
    service: VoiceService = Depends(get_voice_service)
) -> StreamingResponse:
    """
    Stream synthesized speech using Server-Sent Events.

    Returns audio chunks as they become available for real-time playback.

    Provider Selection:
    - Specify provider_preferences in request body to control provider selection
    - Supports cost-optimized, quality-optimized, or explicit provider selection
    """
    req_id = generate_request_id()

    try:
        logger.info(
            f"[{req_id}] Streaming synthesis request: {len(request.text)} characters, "
            f"strategy={request.provider_preferences.strategy if request.provider_preferences else 'default'}"
        )

        # Convert provider preferences
        provider_preferences = _convert_preferences(request.provider_preferences)

        # Create async generator
        async def audio_stream():
            try:
                async for chunk in service.stream_synthesize(
                    text=request.text,
                    config=None,  # TODO: Map request params to config
                    profile_name=request.profile_name,
                    provider_preferences=provider_preferences
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"[{req_id}] Streaming error: {str(e)}", exc_info=True)
                # Can't raise HTTPException in generator, client will see connection close

        # Return streaming response
        return StreamingResponse(
            audio_stream(),
            media_type="audio/mpeg",  # TODO: Make dynamic based on output_format
            headers={
                "X-Request-ID": req_id,
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    except VoiceException as e:
        logger.error(f"[{req_id}] Streaming setup failed: {e.message}")
        raise HTTPException(
            status_code=400 if e.error_code.value.startswith("VOICE_3") else 500,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error(f"[{req_id}] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/voices", response_model=List[VoiceInfo])
async def list_voices(
    refresh: bool = Query(False, description="Force refresh from API"),
    service: VoiceService = Depends(get_voice_service)
) -> List[VoiceInfo]:
    """
    List all available voices.

    Results are cached for 1 hour by default. Use refresh=true to bypass cache.
    """
    try:
        voices = await service.get_voices(refresh=refresh)
        logger.info(f"Returning {len(voices)} voices")
        return voices

    except VoiceException as e:
        logger.error(f"Failed to list voices: {e.message}")
        # Map error codes to appropriate HTTP status codes
        if e.error_code.value == "VOICE_204":  # API_KEY_MISSING_PERMISSION
            status_code = 403  # Forbidden
        elif e.error_code.value == "VOICE_202":  # API_KEY_INVALID
            status_code = 401  # Unauthorized
        elif e.error_code.value == "VOICE_201":  # API_KEY_MISSING
            status_code = 401  # Unauthorized
        elif e.error_code.value.startswith("VOICE_5"):  # Service errors
            status_code = 503  # Service Unavailable
        else:
            status_code = 500  # Internal Server Error
        raise HTTPException(status_code=status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/voices/{voice_id}", response_model=VoiceInfo)
async def get_voice(
    voice_id: str,
    service: VoiceService = Depends(get_voice_service)
) -> VoiceInfo:
    """
    Get details for a specific voice.
    """
    try:
        voice = await service.get_voice(voice_id)
        return voice

    except VoiceException as e:
        logger.error(f"Failed to get voice {voice_id}: {e.message}")
        status_code = 404 if "not found" in e.message.lower() else 500
        raise HTTPException(status_code=status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/config", response_model=VoiceConfigResponse)
async def get_config(
    service: VoiceService = Depends(get_voice_service)
) -> VoiceConfigResponse:
    """
    Get current voice configuration.
    """
    try:
        config = service._config.config
        last_loaded = service._config.last_loaded or datetime.utcnow()

        # Validate configuration
        validation = service._config.validate(config)

        return VoiceConfigResponse(
            config=config.model_dump(exclude_none=True),
            last_updated=last_loaded,
            validation={
                "valid": validation.valid,
                "errors": validation.errors,
                "warnings": validation.warnings
            }
        )

    except Exception as e:
        logger.error(f"Failed to get config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.put("/config", response_model=VoiceConfigResponse)
async def update_config(
    update: VoiceConfigUpdate,
    service: VoiceService = Depends(get_voice_service)
) -> VoiceConfigResponse:
    """
    Update voice configuration.

    Set validate_only=true to validate without saving.
    """
    try:
        from .models import VoiceConfig

        # Parse new configuration
        new_config = VoiceConfig(**update.config)

        # Validate
        validation = service._config.validate(new_config)

        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Configuration validation failed",
                    "errors": validation.errors,
                    "warnings": validation.warnings
                }
            )

        # Save if not validate-only
        if not update.validate_only:
            service._config.save(new_config)
            logger.info("Configuration updated successfully")

        return VoiceConfigResponse(
            config=new_config.model_dump(exclude_none=True),
            last_updated=datetime.utcnow(),
            validation={
                "valid": validation.valid,
                "errors": validation.errors,
                "warnings": validation.warnings
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/health", response_model=HealthResponse)
async def health_check(
    service: VoiceService = Depends(get_voice_service)
) -> HealthResponse:
    """
    Check voice service health status.

    Returns:
    - healthy: All systems operational
    - degraded: Service running but with issues
    - unhealthy: Service not operational
    """
    try:
        health = await service.health_check()

        # Map status string to enum
        status_map = {
            "healthy": HealthStatus.HEALTHY,
            "degraded": HealthStatus.DEGRADED,
            "unhealthy": HealthStatus.UNHEALTHY
        }

        return HealthResponse(
            status=status_map.get(health["status"], HealthStatus.UNHEALTHY),
            elevenlabs_connected=health.get("elevenlabs_connected", False),
            config_loaded=health.get("config_loaded", False),
            timestamp=health.get("timestamp", datetime.utcnow()),
            details=health.get("details", {})
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return HealthResponse(
            status=HealthStatus.UNHEALTHY,
            elevenlabs_connected=False,
            config_loaded=False,
            timestamp=datetime.utcnow(),
            details={"error": str(e)}
        )
