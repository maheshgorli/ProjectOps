"""Security utilities for Argon2 password hashing and JWT token issuance."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.app.core.config import settings

# Initialize Argon2 PasswordHasher
_hasher = PasswordHasher()

# Pre-computed dummy hash used to achieve constant-time behavior on login when user does not exist
_DUMMY_HASH = _hasher.hash("dummy_constant_time_projectops_password")


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using Argon2id."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2 hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def verify_dummy_password(plain_password: str) -> None:
    """Run an Argon2 verification against a dummy hash to prevent timing attacks."""
    try:
        _hasher.verify(_DUMMY_HASH, plain_password)
    except Exception:
        pass


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed HS256 JWT access token with sub, exp, and iat claims."""
    secret_key = settings.get_auth_secret_key()
    now = datetime.now(UTC)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, secret_key, algorithm=settings.auth_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a signed JWT token.

    Raises jwt.PyJWTError (ExpiredSignatureError, InvalidTokenError, etc.) on failure.
    """
    secret_key = settings.get_auth_secret_key()
    return jwt.decode(token, secret_key, algorithms=[settings.auth_algorithm])
