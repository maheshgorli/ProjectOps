"""FastAPI dependencies for user authentication and role-based authorization."""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.security import decode_access_token
from backend.app.db.session import get_async_session
from backend.app.models.auth import ProjectMembershipORM, UserORM


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_async_session),
) -> UserORM:
    """
    Extract and validate JWT Bearer token from the Authorization header.

    Rejects missing, expired, tampered tokens, or inactive users with 401 Unauthorized
    and WWW-Authenticate: Bearer header.
    """
    unauthorized_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization:
        raise unauthorized_exc

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise unauthorized_exc

    token = parts[1]
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise unauthorized_exc
    except jwt.PyJWTError:
        raise unauthorized_exc

    stmt = select(UserORM).where(UserORM.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise unauthorized_exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_project_member(
    project_id: str,
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProjectMembershipORM:
    """
    Ensure the authenticated user is a member of the requested project.

    Returns HTTP 404 Not Found (never 403) if the user has no membership,
    preventing the leak of project existence to unauthorized callers.
    """
    stmt = select(ProjectMembershipORM).where(
        ProjectMembershipORM.project_id == project_id,
        ProjectMembershipORM.user_id == current_user.id,
    )
    result = await session.execute(stmt)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    return membership


async def require_project_owner(
    project_id: str,
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProjectMembershipORM:
    """
    Ensure the authenticated user is an owner of the requested project.

    Returns HTTP 404 if the user is not a member (no existence leak).
    Returns HTTP 403 if the user is a member but lacks owner role.
    """
    stmt = select(ProjectMembershipORM).where(
        ProjectMembershipORM.project_id == project_id,
        ProjectMembershipORM.user_id == current_user.id,
    )
    result = await session.execute(stmt)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    if membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project owner role required.",
        )

    return membership
