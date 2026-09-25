"""Auth endpoints: login, refresh (with rotation), logout, forgot/reset
password, and /me. Every login attempt — success or failure — writes to
the audit log; nothing about authentication is "quiet".

Refresh token rotation: each successful /auth/refresh blacklists the
presented refresh token and issues a brand new one, rather than reusing
the same refresh token until its own natural expiry. A blacklisted
refresh token being presented again is treated as a reuse signal (see
`refresh()`) — plausible evidence of a stolen token being replayed after
the legitimate rotation already happened — and revokes every session for
that user via `token_version`, not just the one request.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from config import settings
from models.rbac import Jurisdiction, User, UserJurisdiction
from schemas.auth import (
    ForgotPasswordRequest,
    JurisdictionOut,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from security.jwt import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
)
from security.passwords import hash_password, verify_password
from security.rate_limit import rate_limit
from security.rbac import audit_access, get_permission_codes
from services.redis_client import redis_client

log = logging.getLogger("api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


def _blacklist_key(jti: str) -> str:
    return f"blacklist:refresh:{jti}"


async def _blacklist_refresh_token(payload: dict) -> None:
    remaining_seconds = int(payload["exp"] - datetime.now(timezone.utc).timestamp())
    if remaining_seconds > 0:
        await redis_client.set(_blacklist_key(payload["jti"]), "1", ex=remaining_seconds)


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
        expires_in_seconds=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("auth_login", 5, 900))])
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

    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token, TokenType.REFRESH)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid or expired refresh token.", "code": "invalid_refresh_token"},
        ) from None

    user_id = uuid.UUID(token_payload["sub"])
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    if await redis_client.exists(_blacklist_key(token_payload["jti"])):
        # This token was already rotated away (or explicitly logged out).
        # Being presented again is a reuse signal, not routine staleness
        # — revoke every session for this user, not just deny this one
        # request, since a stolen-and-replayed token means the legitimate
        # session may be compromised too.
        if user is not None:
            user.token_version += 1
            await db.flush()
            await audit_access(
                db, request, user=user, action="auth:refresh", outcome="deny",
                reason="reused_refresh_token_all_sessions_revoked", resource_type="user",
                resource_id=str(user.id),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "This refresh token has been revoked.", "code": "revoked_refresh_token"},
        )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Account not found or inactive.", "code": "unauthorized"},
        )

    if token_payload.get("ver") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Session has been revoked.", "code": "session_revoked"},
        )

    await _blacklist_refresh_token(token_payload)
    return _issue_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest) -> None:
    try:
        token_payload = decode_token(payload.refresh_token, TokenType.REFRESH)
    except InvalidTokenError:
        return  # already unusable; logout is idempotent
    await _blacklist_refresh_token(token_payload)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("auth_forgot_password", 5, 900))],
)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """No SMTP/email delivery is configured anywhere in this project — see
    README.md "Known gaps". Outside production, the reset token is
    returned directly in the response so the flow is actually testable;
    in production it is only logged server-side (`docker compose logs
    api`), which is itself a stopgap worth replacing with real email
    delivery before this is relied on operationally. Either way the
    response is identical regardless of whether the username exists, to
    avoid confirming account existence to an unauthenticated caller.
    """
    user = (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()

    reset_token: str | None = None
    if user is not None and user.is_active:
        reset_token = create_reset_token(user.id, user.token_version)
        # Server-side log stands in for an email send. Anyone with read
        # access to these logs can mint a password reset — acceptable for
        # a hackathon PoC's dev/demo environment, not for a real
        # deployment (see README.md "Known gaps").
        log.warning(
            "Password reset requested for user=%s — token (30 min TTL): %s",
            user.username,
            reset_token,
        )

    response: dict = {
        "detail": "If that account exists, password reset instructions have been issued.",
    }
    if settings.environment != "production" and reset_token is not None:
        response["dev_reset_token"] = reset_token
    return response


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> None:
    try:
        token_payload = decode_token(payload.reset_token, TokenType.RESET)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid or expired reset token.", "code": "invalid_reset_token"},
        ) from None

    user_id = uuid.UUID(token_payload["sub"])
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Account not found or inactive.", "code": "unauthorized"},
        )
    if token_payload.get("ver") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "This reset link is no longer valid.", "code": "invalid_reset_token"},
        )

    user.password_hash = hash_password(payload.new_password)
    # Every existing access/refresh token — on every device — is
    # invalidated by this reset, per the brief's "server-side session
    # revocation" requirement. The user has to log in again everywhere,
    # which is the correct behavior after a password reset.
    user.token_version += 1
    await db.flush()


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
