"""Request and response shapes for authentication.

Note there is no schema anywhere that returns password_hash.
It cannot leak through the API because no response model contains it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MIN_PASSWORD_LENGTH, MAX_PASSWORD_BYTES
from app.models.user import VALID_ROLES


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)
    role: str = "clinician"

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError("Password is too long.")
        return v

    @field_validator("role")
    @classmethod
    def role_is_known(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(VALID_ROLES)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """The only shape a user is ever returned in."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserResponse
