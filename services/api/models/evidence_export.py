"""A record of every Section 65B-style evidentiary export — who exported
what, when, and the SHA-256 of the resulting package, so the export itself
is independently auditable (on top of the audit_log row the export
endpoint also always writes, per RBAC section of README.md).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class EvidenceExport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "evidence_exports"

    exported_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    plate_text: Mapped[str] = mapped_column(String(16), nullable=False)
    event_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
