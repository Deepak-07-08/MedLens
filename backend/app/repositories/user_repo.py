"""All database access for users. No business logic, no HTTP."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(db: Session, email: str) -> User | None:
    # Emails are stored lowercased so lookup is case-insensitive.
    stmt = select(User).where(User.email == email.strip().lower())
    return db.execute(stmt).scalar_one_or_none()


def get_by_id(db: Session, user_id: uuid.UUID | str) -> User | None:
    try:
        uid = uuid.UUID(str(user_id))
    except (ValueError, AttributeError):
        return None
    return db.get(User, uid)


def create(
    db: Session,
    *,
    email: str,
    password_hash: str,
    full_name: str | None,
    role: str,
) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=password_hash,
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
