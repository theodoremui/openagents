"""
Service layer for real-time voice session management.

Handles session creation, token generation, and lifecycle management using LiveKit API.
Implements business logic cleanly separated from API and agent concerns.
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
import uuid

from livekit import api as livekit_api
from livekit.api.agent_dispatch_service import CreateAgentDispatchRequest
from loguru import logger

from .config import RealtimeVoiceConfig
from .models import (
    RealtimeSession,
    RealtimeSessionStatus,
    VoiceConfigUpdate,
    AgentType,
    VoiceState,
)
from .exceptions import (
    SessionLimitExceeded,
    SessionNotFound,
    LiveKitConnectionException,
    ConfigurationException,
)


class RealtimeVoiceService:
    """
    Service layer for real-time voice session management.

    Features:
    - Session creation with unique room names
    - LiveKit token generation with correct permissions
    - Active session tracking per user
    - Session limit enforcement
    - Health check and monitoring
    """

    def __init__(self, config: Optional[RealtimeVoiceConfig] = None):
        """
        Initialize the service.

        Args:
            config: Voice configuration. Loaded from defaults if not provided.
        """
        try:
            self._config = config or RealtimeVoiceConfig.load()
            logger.info("Initializing RealtimeVoiceService")

            # Defer LiveKit API client initialization to avoid event loop issues
            # Initialize lazily when first needed (in async context)
            self._livekit_api: Optional[livekit_api.LiveKitAPI] = None

            # In-memory session storage (replace with database in production)
            self._sessions: Dict[str, RealtimeSession] = {}

            logger.info(f"RealtimeVoiceService initialized with LiveKit at {self._config.livekit_url}")

        except Exception as e:
            logger.error(f"Failed to initialize RealtimeVoiceService: {e}")
            raise ConfigurationException(
                message="Failed to initialize voice service",
                details={"error": str(e)},
                cause=e
            )

    def _get_livekit_api(self) -> livekit_api.LiveKitAPI:
        """
        Get or initialize LiveKit API client (lazy initialization).
        
        This method ensures the API client is initialized in an async context
        when it's actually needed, avoiding event loop issues during service initialization.
        
        Returns:
            LiveKit API client instance
        """
        if self._livekit_api is None:
            self._livekit_api = livekit_api.LiveKitAPI(
                url=self._config.livekit_url,
                api_key=self._config.livekit_api_key,
                api_secret=self._config.livekit_api_secret,
            )
        return self._livekit_api

    async def create_session(
        self,
        user_id: str,
        agent_type: AgentType = AgentType.SMART_ROUTER,
        agent_id: Optional[str] = None,
        agent_config: Optional[Dict] = None,
    ) -> RealtimeSession:
        """
        Create a new voice session.

        Args:
            user_id: ID of the user creating the session
            agent_type: Type of agent to use
            agent_id: Specific agent ID (for SINGLE_AGENT type)
            agent_config: Additional agent configuration

        Returns:
            RealtimeSession with room name and access token

        Raises:
            SessionLimitExceeded: If user has too many active sessions
            LiveKitConnectionException: If LiveKit API call fails
        """
        try:
            # Check session limits
            active_count = sum(
                1 for s in self._sessions.values()
                if s.user_id == user_id and s.is_active
            )

            if active_count >= self._config.max_sessions_per_user:
                logger.warning(f"User {user_id} exceeded session limit ({active_count}/{self._config.max_sessions_per_user})")
                raise SessionLimitExceeded(
                    message=f"Maximum {self._config.max_sessions_per_user} sessions allowed",
                    details={"user_id": user_id, "active_count": active_count}
                )

            # Generate unique identifiers
            session_id = str(uuid.uuid4())
            room_name = f"voice-{user_id}-{session_id[:8]}"

            logger.info(f"Creating voice session: {session_id} (room: {room_name})")

            # Create LiveKit room with metadata for agent dispatch
            metadata = self._build_room_metadata(agent_type, agent_id, agent_config)

            create_room_request = livekit_api.CreateRoomRequest(
                name=room_name,
                empty_timeout=self._config.room_empty_timeout,
                max_participants=self._config.max_participants,
                metadata=metadata,
            )

            await self._get_livekit_api().room.create_room(create_room_request)
            logger.debug(f"LiveKit room created: {room_name}")

            # IMPORTANT: Explicitly dispatch an agent to join the room.
            #
            # Without this, the LiveKit worker will remain idle (no jobs received),
            # the agent will never join as a participant, and users will see
            # "Voice Active" but no microphone input is processed.
            try:
                agent_name = self._config.worker_agent_name
                await self._get_livekit_api().agent_dispatch.create_dispatch(
                    CreateAgentDispatchRequest(
                        room=room_name,
                        agent_name=agent_name,
                        # Keep the same JSON metadata used for the room. The worker reads ctx.room.metadata.
                        metadata=metadata,
                    )
                )
                logger.info(f"Dispatched agent '{agent_name}' to room '{room_name}'")
            except Exception as e:
                logger.error(f"Failed to dispatch agent to room {room_name}: {e}")
                # Best-effort cleanup so we don't leak rooms if dispatch fails.
                try:
                    await self._get_livekit_api().room.delete_room(
                        livekit_api.DeleteRoomRequest(room=room_name)
                    )
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup room after dispatch failure: {cleanup_err}")
                raise

            # Generate access token for user
            token = self._generate_token(
                room_name=room_name,
                participant_identity=f"user-{user_id}",
                participant_name=f"User {user_id}",
            )

            # Create session record
            session = RealtimeSession(
                id=session_id,
                user_id=user_id,
                room_name=room_name,
                token=token,
                livekit_url=self._config.livekit_ws_url,
                agent_type=agent_type,
                agent_id=agent_id,
                created_at=datetime.utcnow(),
                is_active=True,
            )

            self._sessions[session_id] = session
            logger.info(f"Session created successfully: {session_id}")
            return session

        except SessionLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise LiveKitConnectionException(
                message="Failed to create voice session",
                details={"user_id": user_id, "error": str(e)},
                cause=e
            )

    async def get_session(
        self,
        session_id: str,
        user_id: str,
    ) -> Optional[RealtimeSessionStatus]:
        """
        Get session status with participant information.

        Args:
            session_id: Session identifier
            user_id: User identifier (for authorization)

        Returns:
            RealtimeSessionStatus or None if not found or not authorized
        """
        session = self._sessions.get(session_id)
        if not session or session.user_id != user_id:
            logger.warning(f"Session not found or unauthorized: {session_id} for user {user_id}")
            return None

        try:
            # Get room info from LiveKit
            list_participants_request = livekit_api.ListParticipantsRequest(
                room=session.room_name
            )
            participants_response = await self._get_livekit_api().room.list_participants(
                list_participants_request
            )

            participants = participants_response.participants if hasattr(participants_response, 'participants') else []
            agent_connected = any(
                p.identity.startswith("agent-") for p in participants
            )

            duration = (datetime.utcnow() - session.created_at).total_seconds()

            return RealtimeSessionStatus(
                session_id=session.id,
                room_name=session.room_name,
                is_active=session.is_active,
                participant_count=len(participants),
                agent_connected=agent_connected,
                agent_state=VoiceState.LISTENING if agent_connected else VoiceState.INITIALIZING,
                created_at=session.created_at,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.error(f"Failed to get session status for {session_id}: {e}")
            # Return minimal status on error
            return RealtimeSessionStatus(
                session_id=session.id,
                room_name=session.room_name,
                is_active=False,
                participant_count=0,
                agent_connected=False,
                created_at=session.created_at,
                duration_seconds=0,
            )

    async def end_session(self, session_id: str, user_id: str) -> None:
        """
        End a voice session and cleanup resources.

        Args:
            session_id: Session identifier
            user_id: User identifier (for authorization)

        Raises:
            SessionNotFound: If session not found or not authorized
        """
        session = self._sessions.get(session_id)
        if not session or session.user_id != user_id:
            logger.warning(f"Attempted to end non-existent or unauthorized session: {session_id}")
            raise SessionNotFound(
                message=f"Session {session_id} not found",
                details={"session_id": session_id, "user_id": user_id}
            )

        try:
            logger.info(f"Ending session: {session_id} (room: {session.room_name})")

            # Delete the room (disconnects all participants)
            delete_room_request = livekit_api.DeleteRoomRequest(
                room=session.room_name
            )
            await self._get_livekit_api().room.delete_room(delete_room_request)

            # Mark session as inactive
            session.is_active = False
            session.ended_at = datetime.utcnow()

            logger.info(f"Session ended successfully: {session_id}")

        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            # Mark as inactive even if LiveKit cleanup failed
            session.is_active = False
            session.ended_at = datetime.utcnow()

    async def get_config(self, user_id: str) -> Dict:
        """
        Get current voice configuration for user.

        Args:
            user_id: User identifier

        Returns:
            Configuration dictionary
        """
        return {
            "stt_model": self._config.stt_model,
            "llm_model": self._config.llm_model,
            "tts_model": self._config.tts_model,
            "tts_voice": self._config.tts_voice,
            "enable_thinking_sound": self._config.enable_thinking_sound,
            "thinking_volume": self._config.thinking_volume,
            "allow_interruptions": self._config.allow_interruptions,
            "min_endpointing_delay": self._config.min_endpointing_delay,
        }

    async def update_config(self, user_id: str, update: VoiceConfigUpdate) -> Dict:
        """
        Update voice configuration for user.

        Note: Currently updates global config. In production, implement per-user config.

        Args:
            user_id: User identifier
            update: Configuration update

        Returns:
            Updated configuration dictionary
        """
        logger.info(f"Config update requested by user {user_id}: {update.model_dump(exclude_none=True)}")

        # In production, implement per-user configuration persistence
        # For now, we just validate and return current config
        # (updates would require reloading config and potentially restarting workers)

        return await self.get_config(user_id)

    async def health_check(self) -> Dict:
        """
        Check service health and LiveKit connectivity.

        Returns:
            Health status dictionary
        """
        try:
            # Test LiveKit connection by listing rooms
            list_rooms_request = livekit_api.ListRoomsRequest()
            rooms_response = await self._get_livekit_api().room.list_rooms(list_rooms_request)

            rooms = rooms_response.rooms if hasattr(rooms_response, 'rooms') else []

            return {
                "status": "healthy",
                "livekit_connected": True,
                "livekit_url": self._config.livekit_url,
                "active_rooms": len(rooms),
                "active_sessions": len([s for s in self._sessions.values() if s.is_active]),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "livekit_connected": False,
                "livekit_url": self._config.livekit_url,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _generate_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
    ) -> str:
        """
        Generate a LiveKit access token.

        Args:
            room_name: Room name
            participant_identity: Unique participant identifier
            participant_name: Display name

        Returns:
            JWT token string
        """
        token = livekit_api.AccessToken(
            api_key=self._config.livekit_api_key,
            api_secret=self._config.livekit_api_secret,
        )

        token.with_identity(participant_identity)
        token.with_name(participant_name)
        token.with_grants(
            livekit_api.VideoGrants(
                room=room_name,
                room_join=True,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        token.with_ttl(timedelta(hours=self._config.token_ttl_hours))

        return token.to_jwt()

    def _build_room_metadata(
        self,
        agent_type: AgentType,
        agent_id: Optional[str],
        agent_config: Optional[Dict],
    ) -> str:
        """
        Build room metadata for agent dispatch.

        Args:
            agent_type: Type of agent
            agent_id: Specific agent ID
            agent_config: Additional agent configuration

        Returns:
            JSON string with metadata
        """
        import json

        metadata = {
            "agent_type": agent_type.value,
            "agent_config": agent_config or {},
        }

        if agent_id:
            metadata["agent_id"] = agent_id

        return json.dumps(metadata)
