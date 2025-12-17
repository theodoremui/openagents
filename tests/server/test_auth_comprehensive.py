"""
Comprehensive tests for authentication module.

Tests all authentication functions with edge cases.
"""

import pytest
import os
from unittest.mock import patch
from datetime import timedelta

from server.auth import (
    AuthConfig,
    verify_api_key,
    create_access_token,
    verify_token,
    hash_password,
    verify_password,
    get_auth_config,
)
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader


class TestAuthConfig:
    """Test AuthConfig class."""

    def test_auth_config_enabled(self):
        """Test auth config when enabled."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": "key1,key2"}):
            config = AuthConfig()
            assert config.enabled is True
            assert "key1" in config.api_keys
            assert "key2" in config.api_keys

    def test_auth_config_disabled(self):
        """Test auth config when disabled."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}):
            config = AuthConfig()
            assert config.enabled is False

    def test_auth_config_default_key(self):
        """Test auth config generates default key when none provided."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": ""}, clear=True):
            config = AuthConfig()
            assert len(config.api_keys) > 0
            # Should have default key
            assert all(len(key) > 0 for key in config.api_keys)

    def test_auth_config_custom_default_key(self):
        """Test auth config uses custom default key from env."""
        with patch.dict(os.environ, {
            "AUTH_ENABLED": "true",
            "API_KEYS": "",
            "DEFAULT_API_KEY": "custom_default_key"
        }, clear=True):
            config = AuthConfig()
            assert "custom_default_key" in config.api_keys

    def test_validate_api_key_valid(self):
        """Test validating valid API key."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": "valid_key"}):
            config = AuthConfig()
            assert config.validate_api_key("valid_key") is True

    def test_validate_api_key_invalid(self):
        """Test validating invalid API key."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": "valid_key"}):
            config = AuthConfig()
            assert config.validate_api_key("invalid_key") is False

    def test_validate_api_key_auth_disabled(self):
        """Test validation when auth is disabled."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}):
            config = AuthConfig()
            assert config.validate_api_key("any_key") is True

    def test_load_api_keys_whitespace_handling(self):
        """Test that API keys with whitespace are handled correctly."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": " key1 , key2 , key3 "}):
            config = AuthConfig()
            assert "key1" in config.api_keys
            assert "key2" in config.api_keys
            assert "key3" in config.api_keys

    def test_load_api_keys_empty_strings_filtered(self):
        """Test that empty strings in API_KEYS are filtered out."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": "key1,,key2, ,key3"}):
            config = AuthConfig()
            assert "key1" in config.api_keys
            assert "key2" in config.api_keys
            assert "key3" in config.api_keys
            assert "" not in config.api_keys


class TestGetAuthConfig:
    """Test get_auth_config function."""

    def test_get_auth_config_caching(self):
        """Test that get_auth_config is cached."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true"}):
            config1 = get_auth_config()
            config2 = get_auth_config()
            
            # Should return same instance (cached)
            assert config1 is config2


class TestVerifyApiKey:
    """Test verify_api_key function."""

    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self):
        """Test verifying valid API key."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": "valid_key"}):
            api_key = await verify_api_key("valid_key")
            assert api_key == "valid_key"

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self):
        """Test verifying invalid API key."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "API_KEYS": "valid_key"}):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key("invalid_key")
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_missing(self):
        """Test verifying when API key is missing."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true"}):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(None)
            
            assert exc_info.value.status_code == 401
            assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_auth_disabled(self):
        """Test verifying when auth is disabled."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}):
            api_key = await verify_api_key(None)
            assert api_key == "auth_disabled"


class TestCreateAccessToken:
    """Test create_access_token function."""

    def test_create_access_token_default_expiry(self):
        """Test creating token with default expiry."""
        data = {"user_id": "test_user"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = verify_token(token)
        assert payload["user_id"] == "test_user"
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        """Test creating token with custom expiry."""
        data = {"user_id": "test_user"}
        custom_expiry = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=custom_expiry)
        
        payload = verify_token(token)
        assert payload["user_id"] == "test_user"

    def test_create_access_token_with_multiple_fields(self):
        """Test creating token with multiple data fields."""
        data = {
            "user_id": "test_user",
            "role": "admin",
            "permissions": ["read", "write"]
        }
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload["user_id"] == "test_user"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


class TestVerifyToken:
    """Test verify_token function."""

    def test_verify_token_valid(self):
        """Test verifying valid token."""
        data = {"user_id": "test_user"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload["user_id"] == "test_user"
        assert "exp" in payload

    def test_verify_token_invalid(self):
        """Test verifying invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in exc_info.value.detail

    def test_verify_token_expired(self):
        """Test verifying expired token."""
        from datetime import datetime, UTC
        
        # Create token with past expiry
        data = {"user_id": "test_user"}
        expired_delta = timedelta(minutes=-60)  # Expired 1 hour ago
        token = create_access_token(data, expires_delta=expired_delta)
        
        with pytest.raises(HTTPException):
            verify_token(token)

    def test_verify_token_malformed(self):
        """Test verifying malformed token."""
        with pytest.raises(HTTPException):
            verify_token("not.a.valid.jwt.token.structure")


class TestPasswordHashing:
    """Test password hashing functions."""

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

    def test_verify_password_different_hash_same_password(self):
        """Test that same password generates different hashes but both verify."""
        password = "test_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_verify_password_empty_password(self):
        """Test verifying empty password."""
        hashed = hash_password("")
        
        assert verify_password("", hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_hash_password_special_characters(self):
        """Test hashing password with special characters."""
        password = "p@ssw0rd!#$%^&*()"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("different", hashed) is False














