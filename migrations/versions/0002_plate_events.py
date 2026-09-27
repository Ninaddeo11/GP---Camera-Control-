"""Phase 6: persisted plate reads (plate_events), consumed from Redis
Streams by services/plate_event_consumer.py.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plate_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("camera_id", sa.String(128), nullable=False),
        sa.Column("track_id", sa.Integer, nullable=False),
        sa.Column("plate_text", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("region", sa.String(2), nullable=False, server_default=""),
        sa.Column("vehicle_class", sa.String(16), nullable=False, server_default=""),
        sa.Column("bbox", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("frame_pts_ms", sa.Float, nullable=False),
        sa.Column("wall_ts_ms", sa.Float, nullable=False),
        sa.Column("wall_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("stream_entry_id", sa.String(32), nullable=False, unique=True),
    )
    # plate_text lookups (exact + prefix, for the fuzzy pre-filter in
    # vehicle_trace.py) and time-ordered traversal reconstruction are the
    # two access patterns that matter here.
    op.create_index("ix_plate_events_plate_text", "plate_events", ["plate_text"])
    op.create_index("ix_plate_events_camera_id", "plate_events", ["camera_id"])
    op.create_index("ix_plate_events_wall_ts", "plate_events", ["wall_ts"])


def downgrade() -> None:
    op.drop_table("plate_events")
