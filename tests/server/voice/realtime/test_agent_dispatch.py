import pytest


class _DummyRoom:
    def __init__(self):
        self.created = []
        self.deleted = []

    async def create_room(self, req):
        self.created.append(req)

    async def delete_room(self, req):
        self.deleted.append(req)


class _DummyAgentDispatch:
    def __init__(self):
        self.dispatched = []

    async def create_dispatch(self, req):
        self.dispatched.append(req)
        return {"ok": True}


class _DummyLiveKitAPI:
    def __init__(self):
        self.room = _DummyRoom()
        self.agent_dispatch = _DummyAgentDispatch()


@pytest.mark.asyncio
async def test_create_session_dispatches_agent(monkeypatch):
    from server.voice.realtime.service import RealtimeVoiceService
    from server.voice.realtime.config import RealtimeVoiceConfig

    # minimal env for RealtimeVoiceConfig
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "k")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "s")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAGENTS_LIVEKIT_AGENT_NAME", "openagents-voice")

    cfg = RealtimeVoiceConfig.load()
    svc = RealtimeVoiceService(config=cfg)
    dummy = _DummyLiveKitAPI()

    monkeypatch.setattr(svc, "_get_livekit_api", lambda: dummy)

    session = await svc.create_session(user_id="u1")

    assert session.room_name
    assert len(dummy.room.created) == 1
    assert len(dummy.agent_dispatch.dispatched) == 1
    req = dummy.agent_dispatch.dispatched[0]
    assert getattr(req, "room") == session.room_name
    assert getattr(req, "agent_name") == "openagents-voice"


