"""Tests for authentication and security."""

import pytest
import os
from unittest.mock import patch

from server.auth import (
    AuthConfig,
    verify_api_key,
    create_access_token,
    verify_token,
    hash_password,
    verify_password,
)
from fastapi import HTTPException


class TestAuthConfig:
    """Tests for AuthConfig class."""

    def test_auth_config_default(self):
        """Test default auth configuration."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true"}, clear=True):
            config = AuthConfig()
            assert config.enabled is True
            assert len(config.api_keys) > 0

    def test_auth_config_disabled(self):
        """Test disabled authentication."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}, clear=True):
            config = AuthConfig()
            assert config.enabled is False

    def test_auth_config_custom_keys(self):
        """Test loading custom API keys."""
        test_keys = "key1,key2,key3"
        with patch.dict(os.environ, {"API_KEYS": test_keys}):
            config = AuthConfig()
            assert "key1" in config.api_keys
            assert "key2" in config.api_keys
            assert "key3" in config.api_keys
            assert len(config.api_keys) == 3

    def test_validate_api_key_valid(self):
        """Test validating a valid API key."""
        with patch.dict(os.environ, {"API_KEYS": "valid_key", "AUTH_ENABLED": "true"}):
            config = AuthConfig()
            assert config.validate_api_key("valid_key") is True

    def test_validate_api_key_invalid(self):
        """Test validating an invalid API key."""
        with patch.dict(os.environ, {"API_KEYS": "valid_key", "AUTH_ENABLED": "true"}):
            config = AuthConfig()
            assert config.validate_api_key("invalid_key") is False

    def test_validate_api_key_auth_disabled(self):
        """Test validation when auth is disabled."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}):
            config = AuthConfig()
            assert config.validate_api_key("any_key") is True


class TestJWT:
    """Tests for JWT token operations."""

    def test_create_and_verify_token(self):
        """Test creating and verifying a JWT token."""
        data = {"user_id": "test_user", "role": "admin"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token
        payload = verify_token(token)
        assert payload["user_id"] == "test_user"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid_token")

        assert exc_info.value.status_code == 401


class TestPasswordHashing:
    """Tests for password hashing."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that same password generates different hashes."""
        password = "test_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
