"""The users table."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Roles the application understands.
ROLE_CLINICIAN = "clinician"
ROLE_ADMIN = "admin"
VALID_ROLES = (ROLE_CLINICIAN, ROLE_ADMIN)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)

    # bcrypt hash. The plain password is never stored, logged, or returned.
    password_hash: Mapped[str] = mapped_column(String(255))

    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=ROLE_CLINICIAN)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
