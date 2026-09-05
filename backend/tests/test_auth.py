"""
Tests for Phase 2 authentication.

These run against a throwaway in-memory SQLite database, so no Postgres
and no network are needed.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.core.security import hash_password, verify_password

VALID = {
    "email": "clinician@example.com",
    "password": "correct-horse-battery",
    "full_name": "Test Clinician",
}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False,
                                  expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client, **overrides):
    return client.post("/api/auth/register", json={**VALID, **overrides})


# ───────────────────────── password hashing ─────────────────────────

def test_password_hash_is_not_the_password():
    hashed = hash_password("correct-horse-battery")
    assert hashed != "correct-horse-battery"
    assert hashed.startswith("$2b$")
    assert verify_password("correct-horse-battery", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_same_password_produces_different_hashes():
    """Each hash gets its own salt."""
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_survives_a_corrupt_hash():
    assert verify_password("anything", "not-a-real-hash") is False


# ───────────────────────── registration ─────────────────────────

def test_register_returns_a_token_and_the_user(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == VALID["email"]
    assert body["user"]["role"] == "clinician"


def test_register_never_returns_the_password_hash(client):
    body = register(client).json()
    serialised = str(body)
    assert "password_hash" not in serialised
    assert VALID["password"] not in serialised


def test_duplicate_email_is_rejected(client):
    register(client)
    r = register(client)
    assert r.status_code == 409


def test_email_is_case_insensitive(client):
    register(client)
    r = register(client, email="CLINICIAN@EXAMPLE.COM")
    assert r.status_code == 409


def test_short_password_is_rejected(client):
    assert register(client, password="short").status_code == 422


def test_invalid_email_is_rejected(client):
    assert register(client, email="not-an-email").status_code == 422


def test_unknown_role_is_rejected(client):
    assert register(client, role="superuser").status_code == 422


# ───────────────────────── login ─────────────────────────

def test_login_with_correct_credentials(client):
    register(client)
    r = client.post("/api/auth/login", json={
        "email": VALID["email"], "password": VALID["password"],
    })
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_with_wrong_password_fails(client):
    register(client)
    r = client.post("/api/auth/login", json={
        "email": VALID["email"], "password": "wrong-password",
    })
    assert r.status_code == 401


def test_wrong_email_and_wrong_password_look_identical(client):
    """The response must not reveal which accounts exist."""
    register(client)
    unknown = client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": VALID["password"],
    })
    bad_pass = client.post("/api/auth/login", json={
        "email": VALID["email"], "password": "wrong-password",
    })
    assert unknown.status_code == bad_pass.status_code == 401
    assert unknown.json()["detail"] == bad_pass.json()["detail"]


# ───────────────────────── protected routes ─────────────────────────

def test_me_requires_a_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client):
    r = client.get("/api/auth/me",
                   headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code == 401


def test_me_rejects_a_token_signed_with_the_wrong_secret(client):
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    forged = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "role": "admin",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=60)},
        "an-attackers-secret", algorithm="HS256",
    )
    r = client.get("/api/auth/me",
                   headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_me_returns_the_signed_in_user(client):
    token = register(client).json()["access_token"]
    r = client.get("/api/auth/me",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == VALID["email"]
    assert "password_hash" not in r.json()


def test_expired_token_is_rejected(client):
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.config import get_settings

    settings = get_settings()
    expired = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "role": "clinician",
         "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )
    r = client.get("/api/auth/me",
                   headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_health_stays_public(client):
    assert client.get("/api/health").status_code == 200
