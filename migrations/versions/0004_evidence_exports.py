"""Phase 9: evidence_exports.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-24

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("exported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plate_text", sa.String(16), nullable=False),
        sa.Column("event_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_exports_exported_by", "evidence_exports", ["exported_by"])


def downgrade() -> None:
    op.drop_table("evidence_exports")
