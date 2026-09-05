"""Importing models here ensures Alembic and create_all see every table."""

from app.models.user import User  # noqa: F401
