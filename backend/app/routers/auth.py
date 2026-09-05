"""Registration, login, and the current-user lookup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.repositories import user_repo
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id=str(user.id), role=user.role),
        expires_in_minutes=settings.jwt_expire_minutes,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse,
             status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create an account and sign in immediately."""
    if user_repo.get_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Sign in instead.",
        )

    user = user_repo.create(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Exchange email and password for a token.

    A wrong email and a wrong password give the same message, so the
    response cannot be used to discover which accounts exist.
    """
    user = user_repo.get_by_email(db, payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    return _token_response(user)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Who am I? Used by the frontend to restore a session on reload."""
    return current_user
