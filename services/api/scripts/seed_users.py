"""Seeds the RBAC foundation: the nine role tiers, the permission set,
role->permission grants, a small jurisdiction hierarchy matching the mock
catalogue's camera departments, and one test user per tier so the demo can
show RBAC by simply logging in as different accounts.

Idempotent — safe to re-run (get-or-create on code/username everywhere).

Run inside the api container:
    docker compose exec api python scripts/seed_users.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from config import settings
from database import AsyncSessionLocal
from models.rbac import Jurisdiction, Permission, Role, RolePermission, User, UserJurisdiction
from security.passwords import hash_password

# Overridable via SEED_DEMO_PASSWORD; the literal here is a dev/demo
# default only. This script refuses to run at all against
# ENVIRONMENT=production unless SEED_DEMO_PASSWORD is also set, so a
# known, guessable password can never end up seeded into a production
# database by someone reusing this script out of habit.
DEMO_PASSWORD = os.environ.get("SEED_DEMO_PASSWORD", "ChangeMe!2026")

ROLES = [
    # (code, tier_level, name)
    ("T1", 1, "State Command (DGP / CP)"),
    ("T2", 2, "Range / Zone (IGP/DIG, Jt. CP)"),
    ("T3", 3, "District (SP, DCP)"),
    ("T4", 4, "Sub-division (DySP, ACP)"),
    ("T5", 5, "Station House Officer (PI)"),
    ("T6", 6, "Field Supervisory (PSI)"),
    ("T7", 7, "Field Operational (ASI/HC/Constable)"),
    ("T8", 8, "Non-police Department Operator (RTO/GSRTC/Health/Municipal)"),
    ("T9", 9, "System Admin (infra only, no investigative data)"),
]

PERMISSIONS = [
    ("camera:read", "View camera registry entries within jurisdiction"),
    ("camera:manage", "Create/update/deactivate camera registry entries"),
    ("vehicle_trace:read", "Query cross-camera vehicle traversal by plate"),
    ("watchlist:read", "View watchlist entries and matches"),
    ("watchlist:write", "Add/remove watchlist entries"),
    ("alert:acknowledge", "Acknowledge/dispatch on a live watchlist alert"),
    ("audit_log:read", "View the immutable audit log"),
    ("evidence:export", "Generate a Section 65B-style evidentiary export"),
    ("user:manage", "Create/update user accounts, roles, and jurisdiction grants"),
]

# Which permission codes each tier holds. T8 deliberately never appears
# next to vehicle_trace/watchlist/audit_log/evidence — that's not a filter
# applied elsewhere, it just isn't granted here.
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "T1": [p for p, _ in PERMISSIONS],  # full access
    "T2": [
        "camera:read", "camera:manage", "vehicle_trace:read", "watchlist:read",
        "watchlist:write", "alert:acknowledge", "audit_log:read", "evidence:export",
    ],
    "T3": [
        "camera:read", "camera:manage", "vehicle_trace:read", "watchlist:read",
        "watchlist:write", "alert:acknowledge", "audit_log:read", "evidence:export",
    ],
    "T4": ["camera:read", "vehicle_trace:read", "watchlist:read", "watchlist:write", "alert:acknowledge"],
    "T5": ["camera:read", "vehicle_trace:read", "watchlist:read", "watchlist:write", "alert:acknowledge"],
    "T6": ["camera:read", "vehicle_trace:read", "watchlist:read", "alert:acknowledge"],
    "T7": ["camera:read", "alert:acknowledge"],
    "T8": ["camera:read"],
    "T9": ["camera:read", "camera:manage", "user:manage"],
}

# (code, name, scope_type, parent_code | None)
JURISDICTIONS = [
    ("GJ-STATE", "Gujarat State", "statewide", None),
    ("AHM-TRAFFIC", "Ahmedabad Traffic Police", "district", "GJ-STATE"),
    ("GJ-HIGHWAY", "Gujarat State Highway Patrol", "district", "GJ-STATE"),
    ("SURAT-CITY", "Surat City Police", "district", "GJ-STATE"),
    ("VADODARA-CITY", "Vadodara City Police", "district", "GJ-STATE"),
    ("DEPT-RTO", "RTO Gujarat", "department", "GJ-STATE"),
    ("DEPT-GSRTC", "GSRTC", "department", "GJ-STATE"),
]

# (username, full_name, badge_number, role_code, department, [jurisdiction_codes])
USERS = [
    ("dgp.shah", "A. Shah", "DGP-001", "T1", "State Command", ["GJ-STATE"]),
    ("igp.range1", "R. Mehta", "IGP-014", "T2", "Range HQ", ["AHM-TRAFFIC", "SURAT-CITY"]),
    ("sp.ahmedabad", "K. Patel", "SP-102", "T3", "Ahmedabad Traffic Police", ["AHM-TRAFFIC"]),
    ("dysp.subdivision", "N. Joshi", "DYSP-045", "T4", "Ahmedabad Traffic Police", ["AHM-TRAFFIC"]),
    ("pi.station", "S. Rana", "PI-233", "T5", "Surat City Police", ["SURAT-CITY"]),
    ("psi.field", "V. Chauhan", "PSI-310", "T6", "Surat City Police", ["SURAT-CITY"]),
    ("constable.patrol", "D. Solanki", "HC-889", "T7", "Vadodara City Police", ["VADODARA-CITY"]),
    ("operator.rto", "M. Desai", "RTO-021", "T8", "RTO Gujarat", ["DEPT-RTO"]),
    ("admin.infra", "System Administrator", None, "T9", "IT Infrastructure", ["GJ-STATE"]),
]


async def _get_or_create_role(db, code: str, tier_level: int, name: str) -> Role:
    role = (await db.execute(select(Role).where(Role.code == code))).scalar_one_or_none()
    if role is None:
        role = Role(code=code, tier_level=tier_level, name=name)
        db.add(role)
        await db.flush()
    return role


async def _get_or_create_permission(db, code: str, description: str) -> Permission:
    perm = (
        await db.execute(select(Permission).where(Permission.code == code))
    ).scalar_one_or_none()
    if perm is None:
        perm = Permission(code=code, description=description)
        db.add(perm)
        await db.flush()
    return perm


async def _get_or_create_jurisdiction(
    db, code: str, name: str, scope_type: str, parent: Jurisdiction | None
) -> Jurisdiction:
    j = (
        await db.execute(select(Jurisdiction).where(Jurisdiction.code == code))
    ).scalar_one_or_none()
    if j is None:
        j = Jurisdiction(
            code=code, name=name, scope_type=scope_type, parent_id=parent.id if parent else None
        )
        db.add(j)
        await db.flush()
    return j


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        roles_by_code = {
            code: await _get_or_create_role(db, code, tier, name) for code, tier, name in ROLES
        }

        permissions_by_code = {
            code: await _get_or_create_permission(db, code, desc) for code, desc in PERMISSIONS
        }

        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            role = roles_by_code[role_code]
            existing = {
                (rp.role_id, rp.permission_id)
                for rp in (
                    await db.execute(select(RolePermission).where(RolePermission.role_id == role.id))
                ).scalars().all()
            }
            for perm_code in perm_codes:
                perm = permissions_by_code[perm_code]
                if (role.id, perm.id) not in existing:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        await db.flush()

        jurisdictions_by_code: dict[str, Jurisdiction] = {}
        for code, name, scope_type, parent_code in JURISDICTIONS:
            parent = jurisdictions_by_code.get(parent_code) if parent_code else None
            jurisdictions_by_code[code] = await _get_or_create_jurisdiction(
                db, code, name, scope_type, parent
            )

        password_hash = hash_password(DEMO_PASSWORD)
        for username, full_name, badge, role_code, department, jur_codes in USERS:
            user = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one_or_none()
            if user is None:
                user = User(
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    badge_number=badge,
                    department=department,
                    role_id=roles_by_code[role_code].id,
                )
                db.add(user)
                await db.flush()

            existing_grants = {
                ug.jurisdiction_id
                for ug in (
                    await db.execute(select(UserJurisdiction).where(UserJurisdiction.user_id == user.id))
                ).scalars().all()
            }
            for jur_code in jur_codes:
                jurisdiction = jurisdictions_by_code[jur_code]
                if jurisdiction.id not in existing_grants:
                    db.add(UserJurisdiction(user_id=user.id, jurisdiction_id=jurisdiction.id))

        await db.commit()

    print(f"Seed complete. {len(USERS)} test users created/verified.")
    print(f"Demo password for every seeded account: {DEMO_PASSWORD}")
    print("Rotate or remove these accounts before any real deployment.")


if __name__ == "__main__":
    if settings.environment == "production" and "SEED_DEMO_PASSWORD" not in os.environ:
        print(
            "Refusing to seed demo accounts: ENVIRONMENT=production and no "
            "SEED_DEMO_PASSWORD override was provided. If you really intend to "
            "seed these accounts in production (e.g. an initial admin), set "
            "SEED_DEMO_PASSWORD to something that isn't this script's default "
            "before re-running.",
            file=sys.stderr,
        )
        sys.exit(1)
    asyncio.run(seed())
