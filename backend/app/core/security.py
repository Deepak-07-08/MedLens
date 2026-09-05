"""
Password hashing and JSON Web Tokens.

Two rules enforced here:
  1. Plain passwords are hashed with bcrypt and never stored or logged.
  2. Tokens carry only an id, a role, and an expiry - never an email,
     a password, or any patient information.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

# bcrypt truncates at 72 bytes, so anything longer is rejected up front
# rather than being silently cut short.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8


def hash_password(plain: str) -> str:
    """Hash a password. Cost factor 12 is the OWASP baseline."""
    if len(plain.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long.")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison. Returns False rather than raising."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret,
                      algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Returns the payload, or None if the token is invalid or expired."""
    try:
        return jwt.decode(token, settings.jwt_secret,
                          algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
