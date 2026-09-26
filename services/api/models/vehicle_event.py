"""Persisted finalized vehicle tracks — one row per completed vehicle
sighting (consolidated vehicle type/manufacturer/model + best fused plate
read), distinct from plate_events (models/plate_event.py), which keeps its
existing per-publish, real-time semantics unchanged. Populated by
services/vehicle_event_consumer.py, which reads the `vehicle_events` Redis
Stream services/inference publishes to once a track_state.TrackSession is
finalized (see services/inference/pipeline.py: _finalize_track).
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class VehicleEventRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "vehicle_events"

    # camera_id (catalogue string), not a FK — same tolerance-of-unsynced-
    # cameras rationale as PlateEventRecord.camera_id.
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)

    first_seen_wall_ts_ms: Mapped[float] = mapped_column(Float, nullable=False)
    last_seen_wall_ts_ms: Mapped[float] = mapped_column(Float, nullable=False)

    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    vehicle_type_observations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plate_text: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    plate_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    plate_region: Mapped[str] = mapped_column(String(2), nullable=False, default="")
    plate_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plate_observations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    plate_agreement: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Empty string, not null, when a classifier was unavailable or
    # unconfident — matches the brief's "Unknown" rather than a missing
    # value, and keeps every column NOT NULL like the rest of this table.
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    manufacturer_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    best_vehicle_image_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    best_plate_image_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # Redis Streams entry id — same idempotency convention as
    # PlateEventRecord.stream_entry_id.
    stream_entry_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
