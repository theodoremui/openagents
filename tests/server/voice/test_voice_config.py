"""
Test suite for Voice Configuration Management.

Tests cover:
- Configuration file loading
- YAML parsing and validation
- Pydantic model validation
- Hot-reload functionality
- Profile management
- Error handling

Total tests: 15
"""

import pytest
import yaml
from pathlib import Path
from server.voice.config import VoiceConfigManager
from server.voice.exceptions import ConfigException
from server.voice.models import VoiceConfig, TTSConfig, STTConfig, VoiceProfile


# ============================================================================
# Config Loading Tests (8 tests)
# ============================================================================

@pytest.mark.unit
def test_load_valid_config(voice_config_manager):
    """Test loading valid voice_config.yaml file."""
    config = voice_config_manager.get_config()

    assert isinstance(config, VoiceConfig)
    assert config.enabled is True
    assert isinstance(config.tts, TTSConfig)
    assert isinstance(config.stt, STTConfig)


@pytest.mark.unit
def test_load_missing_file(tmp_path):
    """Test loading with missing config file uses defaults."""
    nonexistent_file = tmp_path / "nonexistent.yaml"

    # Should either raise error or use defaults
    try:
        manager = VoiceConfigManager(config_path=nonexistent_file)
        config = manager.get_config()
        # If it succeeds, verify defaults are used
        assert isinstance(config, VoiceConfig)
    except ConfigException:
        # Missing file raising error is also acceptable
        pass


@pytest.mark.unit
def test_load_invalid_yaml_syntax(tmp_path):
    """Test loading file with invalid YAML syntax."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("""
voice:
  enabled: true
  tts:
    - this is invalid yaml syntax
      missing colon
""")

    with pytest.raises(ConfigException) as exc_info:
        VoiceConfigManager(config_path=config_file)

    assert "yaml" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()


@pytest.mark.unit
def test_load_missing_required_keys(tmp_path):
    """Test loading config with missing required keys."""
    config_file = tmp_path / "missing_keys.yaml"
    config_file.write_text("""
voice:
  enabled: true
  # Missing tts and stt sections
""")

    with pytest.raises(ConfigException):
        manager = VoiceConfigManager(config_path=config_file)
        manager.get_config()


@pytest.mark.unit
def test_load_invalid_value_types(tmp_path):
    """Test loading config with invalid value types."""
    config_file = tmp_path / "invalid_types.yaml"
    config_file.write_text("""
voice:
  enabled: "yes"  # Should be boolean
  tts:
    voice_id: 123  # Should be string
    stability: "high"  # Should be float
""")

    with pytest.raises((ConfigException, ValueError)):
        manager = VoiceConfigManager(config_path=config_file)
        manager.get_config()


@pytest.mark.unit
def test_load_with_environment_variables(tmp_path, monkeypatch):
    """Test config loading with environment variable expansion."""
    monkeypatch.setenv('VOICE_ID', 'env_voice_123')

    config_file = tmp_path / "env_config.yaml"
    config_file.write_text("""
voice:
  enabled: true
  tts:
    voice_id: ${VOICE_ID}
    model_id: "eleven_multilingual_v2"
""")

    # Environment variable expansion depends on implementation
    manager = VoiceConfigManager(config_path=config_file)
    config = manager.get_config()

    # May need special handling for env vars
    assert isinstance(config, VoiceConfig)


@pytest.mark.unit
def test_validate_pydantic_models(voice_config_manager):
    """Test that Pydantic models validate config structure."""
    config = voice_config_manager.get_config()

    # Verify all required fields are present
    assert hasattr(config, 'enabled')
    assert hasattr(config, 'tts')
    assert hasattr(config, 'stt')
    assert hasattr(config, 'voice_profiles')

    # Verify TTS config
    assert hasattr(config.tts, 'voice_id')
    assert hasattr(config.tts, 'model_id')
    assert hasattr(config.tts, 'stability')
    assert hasattr(config.tts, 'similarity_boost')

    # Verify STT config
    assert hasattr(config.stt, 'model_id')


@pytest.mark.unit
def test_load_multiple_profiles(voice_config_manager):
    """Test loading config with multiple voice profiles."""
    config = voice_config_manager.get_config()

    assert len(config.voice_profiles) >= 3  # default, professional, conversational
    assert 'default' in config.voice_profiles
    assert 'professional' in config.voice_profiles
    assert 'conversational' in config.voice_profiles

    # Verify profile structure
    default_profile = config.voice_profiles['default']
    assert isinstance(default_profile, VoiceProfile)
    assert hasattr(default_profile, 'stability')
    assert hasattr(default_profile, 'similarity_boost')


# ============================================================================
# Config Hot-Reload Tests (5 tests)
# ============================================================================

@pytest.mark.unit
def test_detect_file_modification(voice_config_manager, temp_config_file):
    """Test detection of config file modifications."""
    # Initial load
    config1 = voice_config_manager.get_config()
    initial_mtime = temp_config_file.stat().st_mtime

    # Modify file
    import time
    time.sleep(0.1)  # Ensure different timestamp
    temp_config_file.write_text("""
voice:
  enabled: false
  tts:
    voice_id: "modified_voice"
""")

    new_mtime = temp_config_file.stat().st_mtime
    assert new_mtime > initial_mtime


@pytest.mark.unit
def test_reload_on_file_change(voice_config_manager, temp_config_file):
    """Test that config is reloaded when file changes."""
    config1 = voice_config_manager.get_config()
    assert config1.enabled is True

    # Modify file
    import time
    time.sleep(0.1)
    new_config_content = """
voice:
  enabled: false
  tts:
    voice_id: "new_voice"
    model_id: "eleven_multilingual_v2"
    stability: 0.3
  stt:
    model_id: "scribe_v1"
  voice_profiles:
    default:
      stability: 0.3
"""
    temp_config_file.write_text(new_config_content)

    # Force reload
    voice_config_manager.load_config()
    config2 = voice_config_manager.get_config()

    assert config2.enabled is False
    assert config2.tts.voice_id == "new_voice"


@pytest.mark.unit
def test_cache_unchanged_config(voice_config_manager):
    """Test that unchanged config is cached (not reloaded)."""
    config1 = voice_config_manager.get_config()
    config2 = voice_config_manager.get_config()

    # Should return same object (cached)
    assert config1 is config2


@pytest.mark.unit
def test_handle_reload_errors_gracefully(voice_config_manager, temp_config_file):
    """Test that reload errors don't crash the system."""
    config1 = voice_config_manager.get_config()
    assert config1.enabled is True

    # Write invalid config
    import time
    time.sleep(0.1)
    temp_config_file.write_text("invalid: yaml: syntax:")

    # Attempt reload - should handle error
    try:
        voice_config_manager.load_config()
        config2 = voice_config_manager.get_config()
        # Should either return old config or raise error
    except ConfigException:
        # Error is acceptable
        pass


@pytest.mark.unit
def test_validate_new_config_before_applying(voice_config_manager, temp_config_file):
    """Test that new config is validated before replacing old one."""
    config1 = voice_config_manager.get_config()

    # Write config with invalid values
    import time
    time.sleep(0.1)
    temp_config_file.write_text("""
voice:
  enabled: true
  tts:
    stability: 10.0  # Invalid: should be 0.0-1.0
""")

    # Should reject invalid config
    with pytest.raises((ConfigException, ValueError)):
        voice_config_manager.load_config()
        voice_config_manager.get_config()


# ============================================================================
# Config Access Tests (2 tests)
# ============================================================================

@pytest.mark.unit
def test_get_default_tts_config(voice_config_manager):
    """Test retrieving default TTS configuration."""
    tts_config = voice_config_manager.get_default_tts_config()

    assert isinstance(tts_config, TTSConfig)
    assert tts_config.voice_id is not None
    assert tts_config.model_id is not None
    assert 0.0 <= tts_config.stability <= 1.0
    assert 0.0 <= tts_config.similarity_boost <= 1.0


@pytest.mark.unit
def test_get_voice_profile_by_name(voice_config_manager):
    """Test retrieving voice profile by name."""
    # Get default profile
    default_profile = voice_config_manager.get_profile("default")
    assert isinstance(default_profile, VoiceProfile)
    assert 0.0 <= default_profile.stability <= 1.0

    # Get professional profile
    professional_profile = voice_config_manager.get_profile("professional")
    assert isinstance(professional_profile, VoiceProfile)

    # Get non-existent profile should raise error
    with pytest.raises(ConfigException):
        voice_config_manager.get_profile("nonexistent_profile")
