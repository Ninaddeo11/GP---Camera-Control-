"""Immutable, hash-chained audit log.

Every row's row_hash commits to the previous row's hash plus this row's
own fields, so any row tampered with (or deleted and re-inserted) breaks
the chain from that point forward — verifiable independently of the
database's own access controls. A DB-level trigger (see
migrations/versions/0001_initial.py) additionally rejects UPDATE/DELETE on
this table outright, so even a compromised application can only append.

Only services/audit_service.py writes to this table — no route handler
constructs an AuditLogEntry directly, so the hash chain can never be
computed inconsistently.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class AuditLogEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("outcome IN ('allow', 'deny')", name="ck_audit_outcome"),
    )

    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Nullable + a denormalized username snapshot: the actor may be
    # unauthenticated (a failed login) or later deleted, but the audit
    # trail must still read sensibly.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)
    reason: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    request_path: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
