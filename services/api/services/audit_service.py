"""Append-only, hash-chained audit log writer.

This is the ONLY place that constructs an AuditLogEntry — route handlers
and the RBAC dependency call `record()`, never `db.add(AuditLogEntry(...))`
directly, so the hash chain can never be computed inconsistently or
skipped by accident.

Concurrency note: computing "this row's hash = f(previous row's hash, this
row's fields)" is only safe if two concurrent requests can't both read the
same "previous row" and append with the same prev_hash. We take a Postgres
advisory transaction lock scoped to the audit table before reading the
last row, so appends are serialized; the lock is released automatically at
commit/rollback (see database.py get_db).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLogEntry

GENESIS_HASH = "0" * 64

# Arbitrary fixed key for the advisory lock guarding audit_log appends.
# Any two processes using this same constant serialize against each other;
# it doesn't collide with anything else since we never use advisory locks
# elsewhere in this service.
_AUDIT_CHAIN_LOCK_KEY = 875_190_001


def _compute_row_hash(entry: AuditLogEntry) -> str:
    payload = "|".join(
        [
            str(entry.id),
            entry.ts.isoformat(),
            str(entry.user_id or ""),
            entry.username,
            entry.action,
            entry.resource_type,
            entry.resource_id,
            entry.outcome,
            entry.reason,
            entry.ip_address,
            entry.request_path,
            entry.prev_hash,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def record(
    db: AsyncSession,
    *,
    action: str,
    outcome: str,
    user_id: uuid.UUID | None = None,
    username: str = "",
    resource_type: str = "",
    resource_id: str = "",
    reason: str = "",
    ip_address: str = "",
    request_path: str = "",
) -> AuditLogEntry:
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _AUDIT_CHAIN_LOCK_KEY})

    last_hash = (
        await db.execute(
            select(AuditLogEntry.row_hash)
            .order_by(AuditLogEntry.ts.desc(), AuditLogEntry.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    entry = AuditLogEntry(
        id=uuid.uuid4(),
        ts=datetime.now(timezone.utc),
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        reason=reason,
        ip_address=ip_address,
        request_path=request_path,
        prev_hash=last_hash or GENESIS_HASH,
    )
    entry.row_hash = _compute_row_hash(entry)

    db.add(entry)
    await db.flush()
    return entry


async def verify_chain(db: AsyncSession) -> tuple[bool, int]:
    """Recompute every row's hash in timestamp order and confirm it both
    matches the stored row_hash and chains from the previous row. Returns
    (is_intact, row_count). Used by the Phase 9 evidentiary-export tooling
    and by an admin "verify audit integrity" action.
    """
    rows = (
        await db.execute(select(AuditLogEntry).order_by(AuditLogEntry.ts.asc(), AuditLogEntry.id.asc()))
    ).scalars().all()

    expected_prev = GENESIS_HASH
    for row in rows:
        if row.prev_hash != expected_prev:
            return False, len(rows)
        if _compute_row_hash(row) != row.row_hash:
            return False, len(rows)
        expected_prev = row.row_hash

    return True, len(rows)
