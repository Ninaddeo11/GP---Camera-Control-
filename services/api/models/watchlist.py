"""Watchlist entries and the matches services/watchlist_engine.py records
against them.

WatchlistMatch deliberately does NOT carry a foreign key to
plate_events.id: it's populated by watchlist_engine.py, an independent
Redis Streams consumer group reading the same `plate_events` stream
plate_event_consumer.py persists from (see services/plate_event_consumer.py
docstring) — the two consumers run concurrently with no ordering
guarantee between them, so a hard FK could race against a row that hasn't
been persisted yet. Denormalizing the handful of fields the alert console
actually needs avoids that race entirely and means rendering an alert
never needs a join.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.base import TimestampMixin, UUIDPrimaryKeyMixin

WATCHLIST_PRIORITIES = ("low", "medium", "high", "critical")


class WatchlistEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "watchlist_entries"

    plate_text: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WatchlistMatch(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "watchlist_matches"

    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("watchlist_entries.id"), nullable=False
    )
    watchlist: Mapped["WatchlistEntry"] = relationship("WatchlistEntry")

    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    matched_plate_text: Mapped[str] = mapped_column(String(16), nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    wall_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
