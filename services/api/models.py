from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    Float,
)

from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from geoalchemy2 import Geometry
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base


"""Shared model mixins: UUID primary keys and created/updated timestamps."""

class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )



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

"""RBAC schema: roles (T1-T9), permissions, role_permissions, users,
jurisdictions, and the user<->jurisdiction grants.

Two axes are resolved server-side on every request by security/rbac.py:
`hasPermission(user, action)` (role_permissions) AND
`isInJurisdiction(user, resource)` (user_jurisdictions, walked against the
jurisdiction hierarchy). Neither check lives in a route handler — see
security/rbac.py for the single policy-check dependency both go through.
"""

JURISDICTION_SCOPE_TYPES = ("statewide", "range", "district", "station", "department")


class Jurisdiction(UUIDPrimaryKeyMixin, Base):
    """A node in a single jurisdiction tree, rooted at one 'statewide' node.
    Geographic nodes (range -> district -> station) nest under statewide;
    non-police department nodes (T8, e.g. RTO/GSRTC) are also direct
    children of statewide, as siblings of the geographic branch, rather
    than a second disconnected tree.

    This means a single grant on the statewide root (T1) naturally covers
    every camera in the system — geographic and departmental — via the
    same recursive descendant walk used for every other tier (see
    services/jurisdiction_service.py). A department-scoped grant (T8) on a
    leaf department node covers only that node, since it has no children.
    No tier needs special-case "sees everything" logic.
    """

    __tablename__ = "jurisdictions"
    __table_args__ = (
        CheckConstraint(
            f"scope_type IN {JURISDICTION_SCOPE_TYPES!r}", name="ck_jurisdiction_scope_type"
        ),
    )

    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True
    )

    parent: Mapped["Jurisdiction | None"] = relationship(
        "Jurisdiction", remote_side="Jurisdiction.id", back_populates="children"
    )
    children: Mapped[list["Jurisdiction"]] = relationship(
        "Jurisdiction", back_populates="parent"
    )


class Role(UUIDPrimaryKeyMixin, Base):
    """One of the nine Sentinel Grid rank tiers (T1 highest authority ->
    T9 infra admin). tier_level is the same number as the T-code, stored
    separately so numeric comparisons (`tier_level <= 3`) don't need to
    parse the code string.
    """

    __tablename__ = "roles"
    __table_args__ = (CheckConstraint("tier_level BETWEEN 1 AND 9", name="ck_role_tier_range"),)

    code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)  # "T1".."T9"
    tier_level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )


class Permission(UUIDPrimaryKeyMixin, Base):
    """A single grantable action, e.g. "camera:read", "watchlist:write",
    "evidence:export". Route handlers never hardcode a role check —
    they declare which permission code they require and the RBAC
    dependency resolves it against role_permissions.
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    badge_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    # Least-privilege default: a brand new account has a role but zero
    # jurisdiction grants until explicitly assigned (see UserJurisdiction).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Embedded as the "ver" claim in every access/refresh token this user
    # is issued (security/jwt.py). Bumping it invalidates every token
    # issued before the bump in one step — server-side session revocation
    # without needing a denylist of every individual token ever issued.
    # Bumped on password reset (api/auth.py) and by an admin's explicit
    # "revoke sessions" action (api/admin.py).
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    role: Mapped["Role"] = relationship("Role")
    jurisdiction_grants: Mapped[list["UserJurisdiction"]] = relationship(
        "UserJurisdiction", back_populates="user", cascade="all, delete-orphan"
    )


class UserJurisdiction(UUIDPrimaryKeyMixin, Base):
    """A jurisdiction grant. Granting a node grants everything beneath it
    in the hierarchy too (e.g. a district grant covers every station under
    that district) — resolved by services/jurisdiction_service.py, not
    duplicated as individual rows per descendant.
    """

    __tablename__ = "user_jurisdictions"
    __table_args__ = (UniqueConstraint("user_id", "jurisdiction_id", name="uq_user_jurisdiction"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jurisdictions.id", ondelete="CASCADE"), nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="jurisdiction_grants")
    jurisdiction: Mapped["Jurisdiction"] = relationship("Jurisdiction")



"""Camera registry — the GIS-backed foundation the rest of the platform
(video wall, watchlist correlation, vehicle trace) reads camera identity
and location from. Populated from the gateway catalogue via
services/camera_registry_sync.py (see api/cameras.py POST /cameras/sync);
CRUD here lets an operator correct/enrich what the catalogue provides
(assign a jurisdiction, rename, deactivate).
"""

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

"""A record of every Section 65B-style evidentiary export — who exported
what, when, and the SHA-256 of the resulting package, so the export itself
is independently auditable (on top of the audit_log row the export
endpoint also always writes, per RBAC section of README.md).
"""

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

"""Persisted plate reads — the durable record behind vehicle traversal
queries (Phase 6) and watchlist correlation (Phase 7). Populated by
services/plate_event_consumer.py, which reads the `plate_events` Redis
Stream services/inference publishes to (see services/inference/anpr.py);
this table is the only thing tracking.py and watchlist_engine.py query —
neither talks to Redis directly.
"""

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

