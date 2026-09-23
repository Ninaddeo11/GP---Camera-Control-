"""Read-only view onto the immutable audit log (see models/audit.py and
services/audit_service.py for how it's written and hash-chained).
`audit_log:read` is T1-T3 only, per scripts/seed_users.py — deliberately
excluding T9 (infra admin, no investigative data by default).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.audit import AuditLogEntry
from models.rbac import User
from schemas.audit import AuditChainVerification, AuditLogEntryOut
from security.rbac import require_permission
from services import audit_service

router = APIRouter(prefix="/admin/audit-log", tags=["audit"])


@router.get("", response_model=list[AuditLogEntryOut])
async def list_audit_log(
    username: str | None = None,
    action: str | None = None,
    outcome: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit_log:read", audit_on_success=True)),
) -> list[AuditLogEntryOut]:
    query = select(AuditLogEntry).order_by(AuditLogEntry.ts.desc())
    if username:
        query = query.where(AuditLogEntry.username == username)
    if action:
        query = query.where(AuditLogEntry.action == action)
    if outcome:
        query = query.where(AuditLogEntry.outcome == outcome)
    if since:
        query = query.where(AuditLogEntry.ts >= since)

    rows = (
        await db.execute(query.limit(min(limit, 500)).offset(max(offset, 0)))
    ).scalars().all()
    return [AuditLogEntryOut.model_validate(r) for r in rows]


@router.get("/verify", response_model=AuditChainVerification)
async def verify_audit_chain(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit_log:read", audit_on_success=True)),
) -> AuditChainVerification:
    intact, row_count = await audit_service.verify_chain(db)
    return AuditChainVerification(intact=intact, row_count=row_count)
