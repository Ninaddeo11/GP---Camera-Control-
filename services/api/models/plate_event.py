"""Persisted plate reads — the durable record behind vehicle traversal
queries (Phase 6) and watchlist correlation (Phase 7). Populated by
services/plate_event_consumer.py, which reads the `plate_events` Redis
Stream services/inference publishes to (see services/inference/anpr.py);
this table is the only thing tracking.py and watchlist_engine.py query —
neither talks to Redis directly.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class PlateEventRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "plate_events"

    # camera_id (catalogue string), not a FK to cameras.id, because a plate
    # event can arrive for a camera_id the registry hasn't synced yet — the
    # event is still worth keeping; joins to Camera are done by camera_id
    # and tolerate no match (see vehicle_trace.py).
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    plate_text: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str] = mapped_column(String(2), nullable=False, default="")
    vehicle_class: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    bbox: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    frame_pts_ms: Mapped[float] = mapped_column(Float, nullable=False)
    wall_ts_ms: Mapped[float] = mapped_column(Float, nullable=False)
    wall_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # Redis Streams entry id (e.g. "1695312345-0") — used as the consumer
    # group's durable checkpoint and to make re-processing an entry after a
    # crash idempotent (unique constraint in the migration).
    stream_entry_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
