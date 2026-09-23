"""Phase 7: watchlist entries and matches.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("plate_text", sa.String(16), nullable=False, unique=True),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "priority IN ('low','medium','high','critical')", name="ck_watchlist_priority"
        ),
    )
    op.create_index("ix_watchlist_entries_active", "watchlist_entries", ["active"])

    op.create_table(
        "watchlist_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "watchlist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watchlist_entries.id"),
            nullable=False,
        ),
        sa.Column("camera_id", sa.String(128), nullable=False),
        sa.Column("matched_plate_text", sa.String(16), nullable=False),
        sa.Column("match_score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("wall_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "acknowledged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_watchlist_matches_watchlist_id", "watchlist_matches", ["watchlist_id"])
    op.create_index("ix_watchlist_matches_matched_at", "watchlist_matches", ["matched_at"])
    op.create_index("ix_watchlist_matches_acknowledged", "watchlist_matches", ["acknowledged"])


def downgrade() -> None:
    op.drop_table("watchlist_matches")
    op.drop_table("watchlist_entries")
