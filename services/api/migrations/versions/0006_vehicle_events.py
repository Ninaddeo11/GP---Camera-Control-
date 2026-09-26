"""Multi-vehicle ANPR upgrade: persisted finalized vehicle tracks
(vehicle_events), consumed from Redis Streams by
services/vehicle_event_consumer.py. Distinct from plate_events (0002),
which keeps its existing per-publish semantics.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-26

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicle_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("camera_id", sa.String(128), nullable=False),
        sa.Column("track_id", sa.Integer, nullable=False),
        sa.Column("first_seen_wall_ts_ms", sa.Float, nullable=False),
        sa.Column("last_seen_wall_ts_ms", sa.Float, nullable=False),
        sa.Column("vehicle_type", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("vehicle_type_observations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("plate_text", sa.String(16), nullable=False, server_default=""),
        sa.Column("plate_confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("plate_region", sa.String(2), nullable=False, server_default=""),
        sa.Column("plate_valid", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("plate_observations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("plate_agreement", sa.Float, nullable=False, server_default="0"),
        sa.Column("manufacturer", sa.String(64), nullable=False, server_default=""),
        sa.Column("manufacturer_confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
        sa.Column("model_confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("best_vehicle_image_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("best_plate_image_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("stream_entry_id", sa.String(32), nullable=False, unique=True),
    )
    # Mirrors plate_events' index choices (0002): plate lookups and
    # camera-scoped, time-ordered listing are the two access patterns that
    # matter for GET /tracking/vehicle-events/recent.
    op.create_index("ix_vehicle_events_plate_text", "vehicle_events", ["plate_text"])
    op.create_index("ix_vehicle_events_camera_id", "vehicle_events", ["camera_id"])
    op.create_index("ix_vehicle_events_last_seen_wall_ts_ms", "vehicle_events", ["last_seen_wall_ts_ms"])


def downgrade() -> None:
    op.drop_table("vehicle_events")
