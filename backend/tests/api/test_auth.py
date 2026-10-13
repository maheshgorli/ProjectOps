"""Tests for Authentication endpoints and JWT validation."""

from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.security import create_access_token, hash_password
from backend.app.core.config import settings
from backend.app.models.auth import UserORM


@pytest.mark.asyncio
async def test_register_success(client: httpx.AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "display_name": "New User",
            "password": "StrongPassword123!",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@example.com"
    assert data["display_name"] == "New User"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_case_insensitive(client: httpx.AsyncClient):
    # First registration
    res1 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "DupUser@Example.com",
            "display_name": "Dup User 1",
            "password": "StrongPassword123!",
        },
    )
    assert res1.status_code == 201

    # Second registration with different casing
    res2 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dupuser@EXAMPLE.COM",
            "display_name": "Dup User 2",
            "password": "StrongPassword123!",
        },
    )
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password_fails_422(client: httpx.AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "display_name": "Weak Pass User",
            "password": "short",  # < 10 characters
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_fails_422(client: httpx.AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "display_name": "Bad Email User",
            "password": "StrongPassword123!",
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: httpx.AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@example.com",
            "display_name": "Login User",
            "password": "StrongPassword123!",
        },
    )

    # Login with mixed-case email
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "LoginUser@Example.COM",
            "password": "StrongPassword123!",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 60 * 60  # 3600 seconds default


@pytest.mark.asyncio
async def test_login_wrong_password_and_unknown_email_return_identical_401(
    client: httpx.AsyncClient,
):
    # Register a user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "display_name": "Existing User",
            "password": "StrongPassword123!",
        },
    )

    # 1. Login with existing email but wrong password
    res_wrong_pw = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "existing@example.com",
            "password": "WrongPassword123!",
        },
    )

    # 2. Login with non-existent email
    res_unknown_email = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert res_wrong_pw.status_code == 401
    assert res_unknown_email.status_code == 401
    assert res_wrong_pw.json() == res_unknown_email.json()
    assert "invalid email or password" in res_wrong_pw.json()["detail"].lower()


@pytest.mark.asyncio
async def test_expired_token_rejected_401(client: httpx.AsyncClient, auth_user: UserORM):
    secret = settings.auth_secret_key
    assert secret is not None
    # Mint token that expired 1 hour ago
    payload = {
        "sub": auth_user.id,
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    expired_token = jwt.encode(payload, secret, algorithm="HS256")

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "could not validate credentials" in res.json()["detail"].lower()
    assert "WWW-Authenticate" in res.headers
    assert res.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_tampered_token_rejected_401(client: httpx.AsyncClient, auth_user: UserORM):
    # Mint token with a different secret
    tampered_payload = {
        "sub": auth_user.id,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    tampered_token = jwt.encode(
        tampered_payload, "wrong-secret-key-that-does-not-match", algorithm="HS256"
    )

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers


@pytest.mark.asyncio
async def test_inactive_user_rejected_401(
    client: httpx.AsyncClient,
    test_session: AsyncSession,
):
    # Create inactive user
    user = UserORM(
        id="inactive-user-uuid",
        email="inactive@example.com",
        display_name="Inactive User",
        password_hash=hash_password("Password123!"),
        is_active=False,
    )
    test_session.add(user)
    await test_session.commit()

    token = create_access_token(user.id)

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "inactive" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_me_endpoint(auth_client: httpx.AsyncClient, auth_user: UserORM):
    res = await auth_client.get("/api/v1/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == auth_user.id
    assert data["email"] == auth_user.email
    assert data["display_name"] == auth_user.display_name
    assert data["is_active"] is True
    assert "password_hash" not in data
