"""Minimal admin surface — just the one capability Phase 2 (auth/session
hardening) actually needs: an admin-triggered session revocation,
independent of the user's own password-reset self-service path (see
api/auth.py). The full admin module (user CRUD, role management,
jurisdiction management, a proper user list/detail UI) is later,
larger work — not built here, to keep this phase's scope bounded to
auth/session hardening rather than growing into a second module.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.rbac import User
from security.rbac import require_permission

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.post("/{username}/revoke-sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_sessions(
    username: str,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(
        require_permission("user:manage", resource_id_param="username", audit_on_success=True)
    ),
) -> None:
    """Invalidates every access/refresh token this user currently holds,
    on every device, by bumping token_version (see security/jwt.py and
    api/deps.py's get_current_user for how that's enforced). Their next
    request anywhere fails with 401 session_revoked until they log in
    again.
    """
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "User not found.", "code": "not_found"},
        )
    user.token_version += 1
    await db.flush()
