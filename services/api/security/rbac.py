"""The single RBAC policy-check surface. Every protected route goes
through exactly two functions from this module — never a scattered
`if user.role == "..."` in a route handler:

  1. `require_permission(action)` — a FastAPI dependency answering
     `hasPermission(user, action)` from role_permissions. Use it for every
     protected route.
  2. `check_resource_jurisdiction(...)` — answers
     `isInJurisdiction(user, resource)` for a single already-loaded
     resource (a route has to load the resource to 404 on it anyway, so
     the jurisdiction check happens right after that load, not as a
     separate dependency that would need to re-fetch it). For a *list*
     endpoint, filter the query itself by
     `jurisdiction_service.get_user_scope_jurisdiction_ids` instead — see
     api/cameras.py for the pattern.

Both paths funnel through `audit_access` so every allow/deny is recorded
the same way, regardless of which check produced it.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.rbac import Permission, Role, User
from services import audit_service
from services.jurisdiction_service import is_in_jurisdiction


class ForbiddenError(HTTPException):
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "You do not have access to this resource.", "code": reason},
        )


async def get_permission_codes(db: AsyncSession, role_id: uuid.UUID) -> set[str]:
    result = await db.execute(
        select(Permission.code)
        .join(Permission.roles)
        .where(Role.id == role_id)
    )
    return {row[0] for row in result.all()}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


async def audit_access(
    db: AsyncSession,
    request: Request,
    *,
    user: User | None,
    action: str,
    outcome: str,
    resource_type: str = "",
    resource_id: str = "",
    reason: str = "",
) -> None:
    await audit_service.record(
        db,
        action=action,
        outcome=outcome,
        user_id=user.id if user else None,
        username=user.username if user else "",
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
        ip_address=_client_ip(request),
        request_path=request.url.path,
    )


def require_permission(
    action: str,
    *,
    resource_type: str = "",
    resource_id_param: str | None = None,
    audit_on_success: bool = False,
) -> Callable[..., Awaitable[User]]:
    """Returns a dependency that enforces `hasPermission(user, action)`.

    `resource_id_param`, if given, names a path parameter (e.g.
    "camera_id") to record as resource_id on the audit row — purely for
    audit readability, it does not affect the permission decision.

    `audit_on_success=True` should be set on every tracking, watchlist,
    and evidence-export route (per the acceptance checklist: "audit log
    captures every access to tracking/watchlist/export endpoints"). Denials
    are always audited regardless of this flag — a 403 is security-relevant
    on every route, not just the sensitive ones.
    """

    async def dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        codes = await get_permission_codes(db, user.role_id)
        resource_id = request.path_params.get(resource_id_param, "") if resource_id_param else ""

        if action not in codes:
            await audit_access(
                db,
                request,
                user=user,
                action=action,
                outcome="deny",
                resource_type=resource_type,
                resource_id=resource_id,
                reason="insufficient_role",
            )
            raise ForbiddenError("insufficient_role")

        if audit_on_success:
            await audit_access(
                db,
                request,
                user=user,
                action=action,
                outcome="allow",
                resource_type=resource_type,
                resource_id=resource_id,
            )

        return user

    return dependency


async def check_resource_jurisdiction(
    db: AsyncSession,
    request: Request,
    *,
    user: User,
    jurisdiction_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str,
    audit_on_success: bool = False,
) -> None:
    """Enforces `isInJurisdiction(user, resource)` for a single,
    already-loaded resource. Raises 403 (and always audits the denial) if
    the resource's jurisdiction isn't in the user's granted scope.
    """
    if await is_in_jurisdiction(db, user, jurisdiction_id):
        if audit_on_success:
            await audit_access(
                db,
                request,
                user=user,
                action=action,
                outcome="allow",
                resource_type=resource_type,
                resource_id=resource_id,
            )
        return

    await audit_access(
        db,
        request,
        user=user,
        action=action,
        outcome="deny",
        resource_type=resource_type,
        resource_id=resource_id,
        reason="out_of_jurisdiction",
    )
    raise ForbiddenError("out_of_jurisdiction")
