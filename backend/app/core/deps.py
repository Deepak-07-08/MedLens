"""Dependencies that protect routes.

Put get_current_user on a route and it cannot be reached without a valid
token. Every patient route from Phase 3 onward will use it.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import ROLE_ADMIN, User
from app.repositories import user_repo

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Your session is not valid. Please sign in again.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    payload = decode_access_token(credentials.credentials)
    if payload is None or not payload.get("sub"):
        raise CREDENTIALS_ERROR

    user = user_repo.get_by_id(db, payload["sub"])
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an administrator account.",
        )
    return current_user
