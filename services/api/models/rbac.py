"""RBAC schema: roles (T1-T9), permissions, role_permissions, users,
jurisdictions, and the user<->jurisdiction grants.

Two axes are resolved server-side on every request by security/rbac.py:
`hasPermission(user, action)` (role_permissions) AND
`isInJurisdiction(user, resource)` (user_jurisdictions, walked against the
jurisdiction hierarchy). Neither check lives in a route handler — see
security/rbac.py for the single policy-check dependency both go through.
"""

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
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.base import TimestampMixin, UUIDPrimaryKeyMixin

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
