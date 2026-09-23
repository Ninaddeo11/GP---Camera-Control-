"""Auth endpoints: login, refresh, logout, and /me (used by the frontend's
rank/jurisdiction badge in Phase 8). Every login attempt — success or
failure — writes to the audit log; nothing about authentication is
"quiet".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from config import settings
from models.rbac import Jurisdiction, User, UserJurisdiction
from schemas.auth import (
    AccessTokenResponse,
    JurisdictionOut,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    TokenResponse,
)
from security.jwt import InvalidTokenError, TokenType, create_access_token, create_refresh_token, decode_token
from security.passwords import verify_password
from security.rbac import audit_access, get_permission_codes
from services.redis_client import redis_client

router = APIRouter(prefix="/auth", tags=["auth"])


def _blacklist_key(jti: str) -> str:
    return f"blacklist:refresh:{jti}"


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        await audit_access(
            db,
            request,
            user=user if user and user.is_active else None,
            action="auth:login",
            outcome="deny",
            reason="invalid_credentials",
            resource_type="user",
            resource_id=payload.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid username or password.", "code": "invalid_credentials"},
        )

    await audit_access(
        db, request, user=user, action="auth:login", outcome="allow", resource_type="user",
        resource_id=str(user.id),
    )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in_seconds=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token, TokenType.REFRESH)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid or expired refresh token.", "code": "invalid_refresh_token"},
        ) from None

    if await redis_client.exists(_blacklist_key(token_payload["jti"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "This refresh token has been revoked.", "code": "revoked_refresh_token"},
        )

    user_id = uuid.UUID(token_payload["sub"])
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Account not found or inactive.", "code": "unauthorized"},
        )

    return AccessTokenResponse(
        access_token=create_access_token(user.id),
        expires_in_seconds=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest) -> None:
    try:
        token_payload = decode_token(payload.refresh_token, TokenType.REFRESH)
    except InvalidTokenError:
        return  # already unusable; logout is idempotent

    remaining_seconds = int(token_payload["exp"] - datetime.now(timezone.utc).timestamp())
    if remaining_seconds > 0:
        await redis_client.set(_blacklist_key(token_payload["jti"]), "1", ex=remaining_seconds)


@router.get("/me", response_model=MeResponse)
async def me(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> MeResponse:
    # get_current_user already loads `user.role` via selectinload.
    permission_codes = sorted(await get_permission_codes(db, user.role_id))

    jurisdiction_rows = (
        await db.execute(
            select(Jurisdiction)
            .join(UserJurisdiction, UserJurisdiction.jurisdiction_id == Jurisdiction.id)
            .where(UserJurisdiction.user_id == user.id)
        )
    ).scalars().all()

    return MeResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        badge_number=user.badge_number,
        department=user.department,
        role_code=user.role.code,
        role_name=user.role.name,
        permissions=permission_codes,
        jurisdictions=[JurisdictionOut.model_validate(j) for j in jurisdiction_rows],
    )
