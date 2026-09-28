"""Shared FastAPI dependencies: DB session and the current authenticated
user. `get_current_user` re-resolves the user (and, via
security/rbac.py, their permissions) from the database on every request —
the JWT only proves identity, never carries authorization state.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db as get_db  # re-exported for convenience
from models.rbac import User
from security.jwt import InvalidTokenError, TokenType, decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"detail": detail, "code": "unauthorized"},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials, TokenType.ACCESS)
    except InvalidTokenError:
        raise _unauthorized("Invalid or expired token") from None

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise _unauthorized("Malformed token") from None

    user = (
        await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        raise _unauthorized("Account not found or inactive")

    # Server-side session revocation: a token minted before the user's
    # token_version was last bumped (password reset, or an admin's
    # "revoke sessions" action) is rejected even though it hasn't expired
    # yet — see security/jwt.py's module docstring.
    if payload.get("ver") != user.token_version:
        raise _unauthorized("Session has been revoked")

    return user
