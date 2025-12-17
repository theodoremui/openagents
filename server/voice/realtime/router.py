"""
FastAPI router for real-time voice endpoints.

Provides REST API endpoints for:
- Creating voice sessions
- Getting session status
- Ending sessions
- Managing configuration
- Health checks
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import Dict, Any, Optional
from loguru import logger

from server.auth import verify_api_key
from .config import RealtimeVoiceConfig
from .models import (
    RealtimeSessionRequest,
    RealtimeSessionResponse,
    RealtimeSessionStatus,
    VoiceConfigUpdate,
    VoiceConfigResponse,
)
from .service import RealtimeVoiceService
from .exceptions import (
    SessionLimitExceeded,
    SessionNotFound,
    LiveKitConnectionException,
    ConfigurationException,
)


# Create router
router = APIRouter(
    prefix="/voice/realtime",
    tags=["voice-realtime"],
)


# Dependency for service injection
_service_instance: Optional[RealtimeVoiceService] = None


def get_voice_realtime_service() -> RealtimeVoiceService:
    """
    Dependency injection for RealtimeVoiceService.

    Returns:
        RealtimeVoiceService instance

    Raises:
        HTTPException: If service is not initialized
    """
    global _service_instance

    if _service_instance is None:
        try:
            logger.info("Initializing RealtimeVoiceService")
            _service_instance = RealtimeVoiceService()
        except ConfigurationException as e:
            logger.error(f"Failed to initialize voice service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Voice service not available: {str(e)}",
            )

    return _service_instance


# Helper for extracting user ID from auth
def get_user_id(api_key: str = Depends(verify_api_key)) -> str:
    """
    Extract user ID from API key authentication.

    For now, returns a placeholder. In production, map API key to user ID.

    Args:
        api_key: Verified API key from dependency

    Returns:
        User ID string
    """
    # TODO: Implement actual user ID extraction from API key
    # For now, use API key hash or fixed user ID
    return "default-user"


@router.post(
    "/session",
    response_model=RealtimeSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_voice_session(
    request: RealtimeSessionRequest,
    user_id: str = Depends(get_user_id),
    service: RealtimeVoiceService = Depends(get_voice_realtime_service),
) -> RealtimeSessionResponse:
    """
    Create a new real-time voice session.

    This endpoint creates a LiveKit room and generates an access token
    for the client to connect. The agent will be automatically dispatched
    to the room when the client connects.

    Args:
        request: Session creation request with agent configuration
        user_id: User ID from authentication
        service: Voice service instance

    Returns:
        RealtimeSessionResponse with room name and access token

    Raises:
        HTTPException: If session creation fails or limits exceeded
    """
    try:
        logger.info(f"Creating voice session for user {user_id}: {request.model_dump()}")

        session = await service.create_session(
            user_id=user_id,
            agent_type=request.agent_type,
            agent_id=request.agent_id,
            agent_config=request.agent_config,
        )

        response = RealtimeSessionResponse(
            session_id=session.id,
            room_name=session.room_name,
            token=session.token,
            url=session.livekit_url,
        )

        logger.info(f"Session created: {session.id}")
        return response

    except SessionLimitExceeded as e:
        logger.warning(f"Session limit exceeded for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except LiveKitConnectionException as e:
        logger.error(f"LiveKit connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to create voice session: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating voice session",
        )


@router.get(
    "/session/{session_id}",
    response_model=RealtimeSessionStatus,
)
async def get_session_status(
    session_id: str,
    user_id: str = Depends(get_user_id),
    service: RealtimeVoiceService = Depends(get_voice_realtime_service),
) -> RealtimeSessionStatus:
    """
    Get the status of a voice session.

    Returns session state, connected participants, and statistics.

    Args:
        session_id: Session identifier
        user_id: User ID from authentication
        service: Voice service instance

    Returns:
        Session status with participant information

    Raises:
        HTTPException: If session not found or not authorized
    """
    try:
        session_status = await service.get_session(session_id, user_id)

        if session_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return session_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting session status",
        )


@router.delete(
    "/session/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def end_voice_session(
    session_id: str,
    user_id: str = Depends(get_user_id),
    service: RealtimeVoiceService = Depends(get_voice_realtime_service),
) -> None:
    """
    End a voice session and cleanup resources.

    This will disconnect all participants and delete the LiveKit room.

    Args:
        session_id: Session identifier
        user_id: User ID from authentication
        service: Voice service instance

    Raises:
        HTTPException: If session not found or not authorized
    """
    try:
        await service.end_session(session_id, user_id)
        logger.info(f"Session ended: {session_id}")

    except SessionNotFound as e:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error ending session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error ending session",
        )


@router.get(
    "/config",
    response_model=VoiceConfigResponse,
)
async def get_voice_config(
    user_id: str = Depends(get_user_id),
    service: RealtimeVoiceService = Depends(get_voice_realtime_service),
) -> VoiceConfigResponse:
    """
    Get current real-time voice configuration.

    Args:
        user_id: User ID from authentication
        service: Voice service instance

    Returns:
        Current configuration settings
    """
    try:
        config = await service.get_config(user_id)
        return VoiceConfigResponse(config=config)

    except Exception as e:
        logger.error(f"Error getting config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting configuration",
        )


@router.put(
    "/config",
    response_model=VoiceConfigResponse,
)
async def update_voice_config(
    update: VoiceConfigUpdate,
    user_id: str = Depends(get_user_id),
    service: RealtimeVoiceService = Depends(get_voice_realtime_service),
) -> VoiceConfigResponse:
    """
    Update real-time voice configuration.

    Note: Some changes may require restarting voice sessions.

    Args:
        update: Configuration update
        user_id: User ID from authentication
        service: Voice service instance

    Returns:
        Updated configuration settings
    """
    try:
        config = await service.update_config(user_id, update)
        return VoiceConfigResponse(config=config)

    except Exception as e:
        logger.error(f"Error updating config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error updating configuration",
        )


@router.get(
    "/session/{session_id}/trace",
)
async def get_session_trace(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> Any:
    """
    Get latest MoE orchestration trace for voice session.

    Returns detailed trace data showing expert selection, parallel execution,
    and result mixing for visualization in ReactFlow.

    Args:
        session_id: Session identifier
        user_id: User ID from authentication

    Returns:
        Trace data in JSON format with session_id, trace, and timestamp

    Raises:
        HTTPException: If no trace available for this session
    """
    try:
        # Import here to avoid circular dependency
        from .agent import _get_trace
        import time
        from dataclasses import asdict

        trace = _get_trace(session_id)

        # IMPORTANT:
        # It's normal for a newly-created voice session to have no trace yet
        # (trace is only produced after the MoE agent processes a request).
        #
        # Returning 404 here causes noisy server access logs if the frontend
        # polls while waiting. Prefer 204 No Content to indicate "not ready".
        if not trace:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # Convert dataclass to dict for JSON serialization
        trace_dict = asdict(trace)

        return {
            "session_id": session_id,
            "trace": trace_dict,
            "timestamp": time.time(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting trace data",
        )


@router.get(
    "/health",
)
async def health_check(
    service: RealtimeVoiceService = Depends(get_voice_realtime_service),
) -> Dict[str, Any]:
    """
    Health check for real-time voice service.

    Returns connectivity status, active sessions, and system health.

    Args:
        service: Voice service instance

    Returns:
        Health status dictionary
    """
    try:
        health = await service.health_check()
        return health

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }
