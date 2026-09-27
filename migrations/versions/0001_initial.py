"""Phase 2 initial schema: RBAC (roles/permissions/jurisdictions/users),
camera registry (PostGIS), and the hash-chained immutable audit log.

Revision ID: 0001
Revises:
Create Date: 2026-09-22

"""

from __future__ import annotations

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "jurisdictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jurisdictions.id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "scope_type IN ('statewide','range','district','station','department')",
            name="ck_jurisdiction_scope_type",
        ),
    )
    op.create_index("ix_jurisdictions_parent_id", "jurisdictions", ["parent_id"])

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(4), nullable=False, unique=True),
        sa.Column("tier_level", sa.Integer, nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.CheckConstraint("tier_level BETWEEN 1 AND 9", name="ck_role_tier_range"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
    )

    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("badge_number", sa.String(64), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_role_id", "users", ["role_id"])

    op.create_table(
        "user_jurisdictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "jurisdiction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jurisdictions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "jurisdiction_id", name="uq_user_jurisdiction"),
    )
    op.create_index("ix_user_jurisdictions_user_id", "user_jurisdictions", ["user_id"])

    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("camera_id", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "jurisdiction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jurisdictions.id"),
            nullable=True,
        ),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("protocol", sa.String(16), nullable=False, server_default=""),
        sa.Column("resolution", sa.String(32), nullable=False, server_default=""),
        sa.Column("codec", sa.String(16), nullable=False, server_default=""),
        sa.Column("fps", sa.Float, nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_cameras_jurisdiction_id", "cameras", ["jurisdiction_id"])
    op.create_index("ix_cameras_is_active", "cameras", ["is_active"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("username", sa.String(64), nullable=False, server_default=""),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("resource_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(8), nullable=False),
        sa.Column("reason", sa.String(128), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column("request_path", sa.String(255), nullable=False, server_default=""),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("row_hash", sa.String(64), nullable=False, unique=True),
        sa.CheckConstraint("outcome IN ('allow', 'deny')", name="ck_audit_outcome"),
    )
    op.create_index("ix_audit_log_ts", "audit_log", ["ts"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])

    # Tamper-evidence at the database level, independent of the app's own
    # access controls: no connection, however privileged the app's own DB
    # role is, can UPDATE or DELETE an audit row once committed. Only a
    # superuser dropping/recreating the trigger itself could bypass this,
    # which is an intentionally loud, out-of-band operation.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: % is not permitted', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_immutable")
    op.drop_table("audit_log")
    op.drop_table("cameras")
    op.drop_table("user_jurisdictions")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("jurisdictions")
