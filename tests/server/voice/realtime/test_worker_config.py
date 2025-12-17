from pathlib import Path

import pytest


def _write_voice_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def _required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # RealtimeVoiceConfig validates these at import/load time.
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "test_key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test_secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")


def test_worker_defaults_are_safe(tmp_path: Path, _required_env: None) -> None:
    from server.voice.realtime.config import RealtimeVoiceConfig

    cfg_path = tmp_path / "voice_config.yaml"
    _write_voice_yaml(
        cfg_path,
        """
voice:
  realtime:
    enabled: true
""".lstrip(),
    )

    cfg = RealtimeVoiceConfig.load(cfg_path)
    assert cfg.worker_num_idle_processes == 1
    assert cfg.worker_port == 0
    assert cfg.worker_job_memory_warn_mb == 700
    assert cfg.worker_job_memory_limit_mb == 0
    assert cfg.worker_load_threshold == 0.7
    assert cfg.worker_agent_name == "openagents-voice"


def test_worker_env_overrides_take_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _required_env: None) -> None:
    from server.voice.realtime.config import RealtimeVoiceConfig

    monkeypatch.setenv("OPENAGENTS_LIVEKIT_AGENT_NAME", "custom-agent")
    monkeypatch.setenv("OPENAGENTS_LIVEKIT_NUM_IDLE_PROCESSES", "3")
    monkeypatch.setenv("OPENAGENTS_LIVEKIT_WORKER_PORT", "12345")
    monkeypatch.setenv("OPENAGENTS_LIVEKIT_JOB_MEMORY_WARN_MB", "900")
    monkeypatch.setenv("OPENAGENTS_LIVEKIT_JOB_MEMORY_LIMIT_MB", "1500")
    monkeypatch.setenv("OPENAGENTS_LIVEKIT_LOAD_THRESHOLD", "0.9")

    cfg_path = tmp_path / "voice_config.yaml"
    _write_voice_yaml(
        cfg_path,
        """
voice:
  realtime:
    worker:
      agent_name: "yaml-agent"
      num_idle_processes: 9
      port: 9999
      job_memory_warn_mb: 111
      job_memory_limit_mb: 222
      load_threshold: 0.1
""".lstrip(),
    )

    cfg = RealtimeVoiceConfig.load(cfg_path)
    assert cfg.worker_agent_name == "custom-agent"
    assert cfg.worker_num_idle_processes == 3
    assert cfg.worker_port == 12345
    assert cfg.worker_job_memory_warn_mb == 900
    assert cfg.worker_job_memory_limit_mb == 1500
    assert cfg.worker_load_threshold == 0.9


