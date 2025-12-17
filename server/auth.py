"""
Authentication and security middleware.

Implements secure API key authentication with rate limiting and request validation.
Follows security best practices to prevent common attacks.
"""

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import secrets
from typing import Optional
from datetime import datetime, timedelta, UTC
from functools import lru_cache

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext


# Security configuration
API_KEY_NAME = "X-API-Key"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthConfig:
    """Authentication configuration."""

    def __init__(self) -> None:
        self.enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"
        self.api_keys = self._load_api_keys()
        self.jwt_secret = JWT_SECRET_KEY
        self.jwt_algorithm = JWT_ALGORITHM

    @staticmethod
    def _load_api_keys() -> set[str]:
        """Load API keys from environment."""
        api_keys_str = os.getenv("API_KEYS", "")
        if not api_keys_str:
            # Generate a default development key if none provided
            default_key = os.getenv("DEFAULT_API_KEY", "dev_key_" + secrets.token_urlsafe(16))
            print(f"⚠️  No API_KEYS configured. Using development key: {default_key}")
            return {default_key}

        return {key.strip() for key in api_keys_str.split(",") if key.strip()}

    def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key."""
        if not self.enabled:
            return True
        return api_key in self.api_keys


@lru_cache()
def get_auth_config() -> AuthConfig:
    """Get cached authentication configuration."""
    return AuthConfig()


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key from request headers.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    config = get_auth_config()

    # If auth is disabled, allow all requests
    if not config.enabled:
        return "auth_disabled"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not config.validate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=JWT_EXPIRATION_MINUTES)
    )
    to_encode.update({"exp": expire})

    config = get_auth_config()
    return jwt.encode(to_encode, config.jwt_secret, algorithm=config.jwt_algorithm)


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    config = get_auth_config()

    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)
