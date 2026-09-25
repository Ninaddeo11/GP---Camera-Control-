"""Access + refresh + password-reset token issuance and verification.

Access tokens are short-lived (15 min default) and carry the user id plus
a `ver` claim (the user's `token_version` at issuance) — role/jurisdiction
are always re-resolved from the database on each request (see api/deps.py
get_current_user), never trusted from the token payload, so a rank/
jurisdiction change takes effect on the user's very next request. `ver` is
the server-side revocation mechanism: bumping `User.token_version`
(password reset, or an admin's explicit "revoke sessions" action)
invalidates every access and refresh token issued before the bump in one
step, without needing a denylist of every individual token ever handed
out.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from jose import JWTError, jwt

from config import settings


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"


class InvalidTokenError(Exception):
    pass


def _create_token(
    user_id: uuid.UUID, token_type: TokenType, expires_delta: timedelta, token_version: int = 0
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type.value,
        "ver": token_version,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, token_version: int) -> str:
    return _create_token(
        user_id,
        TokenType.ACCESS,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
        token_version,
    )


def create_refresh_token(user_id: uuid.UUID, token_version: int) -> str:
    return _create_token(
        user_id,
        TokenType.REFRESH,
        timedelta(days=settings.jwt_refresh_token_expire_days),
        token_version,
    )


def create_reset_token(user_id: uuid.UUID, token_version: int) -> str:
    # Deliberately short-lived (30 min) regardless of access/refresh
    # config — a password-reset link is meant to be used immediately, not
    # sit in an inbox for days.
    return _create_token(user_id, TokenType.RESET, timedelta(minutes=30), token_version)


def decode_token(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"expected a {expected_type.value} token")
    return payload
