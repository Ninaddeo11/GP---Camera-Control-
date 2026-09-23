"""Camera registry — the GIS-backed foundation the rest of the platform
(video wall, watchlist correlation, vehicle trace) reads camera identity
and location from. Populated from the gateway catalogue via
services/camera_registry_sync.py (see api/cameras.py POST /cameras/sync);
CRUD here lets an operator correct/enrich what the catalogue provides
(assign a jurisdiction, rename, deactivate).
"""

from __future__ import annotations

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.base import TimestampMixin, UUIDPrimaryKeyMixin
from models.rbac import Jurisdiction

CAMERA_STATUSES = ("unknown", "live", "offline", "reconnecting")


class Camera(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cameras"

    # Matches the catalogue's camera_id (see services/ingestion-config) —
    # this is the join key between the registry and go2rtc/inference events.
    camera_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    jurisdiction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True
    )
    jurisdiction: Mapped[Jurisdiction | None] = relationship("Jurisdiction")

    # SRID 4326 (WGS84 lat/lon), nullable until the camera has a confirmed
    # GIS fix — never defaulted to (0, 0), which would place it in the
    # Gulf of Guinea and silently corrupt map/trace views.
    location: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )

    protocol: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    resolution: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    codec: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    fps: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
