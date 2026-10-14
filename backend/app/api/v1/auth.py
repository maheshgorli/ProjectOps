"""API endpoints for user registration, authentication, and session identity."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user
from backend.app.auth.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from backend.app.core.config import settings
from backend.app.db.session import get_async_session
from backend.app.models.auth import UserORM
from backend.app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register_user(
    req: UserRegisterRequest,
    session: AsyncSession = Depends(get_async_session),
) -> UserResponse:
    """
    Register a new user account.

    Enforces:
    - Password minimum length 10 characters.
    - Case-insensitive email uniqueness (returns generic 409 Conflict without leaking).
    - Email stored in lowercase.
    - Argon2id password hashing.
    """
    normalized_email = req.email.strip().lower()

    # Check for duplicate email (case-insensitive)
    stmt = select(UserORM).where(UserORM.email == normalized_email)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed: email is already registered.",
        )

    pw_hash = hash_password(req.password)
    user = UserORM(
        id=str(uuid4()),
        email=normalized_email,
        display_name=req.display_name.strip(),
        password_hash=pw_hash,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive an access token",
)
async def login_user(
    req: UserLoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """
    Authenticate user credentials and issue a signed HS256 JWT access token.

    Enforces:
    - Identical generic 401 response for unknown email and wrong password.
    - Constant-time-ish verification (runs dummy Argon2 verify if user is unknown).
    - Rejection of inactive accounts.
    """
    normalized_email = req.email.strip().lower()

    stmt = select(UserORM).where(UserORM.email == normalized_email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Constant-time mitigation against user enumeration
        verify_dummy_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(req.password, user.password_hash) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    expires_in_seconds = settings.access_token_expire_minutes * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve authenticated user profile",
)
async def get_current_user_profile(
    current_user: UserORM = Depends(get_current_user),
) -> UserResponse:
    """Return the profile information of the currently authenticated user."""
    return UserResponse.model_validate(current_user)
