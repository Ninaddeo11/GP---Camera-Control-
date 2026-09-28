"""Resolves `isInJurisdiction(user, resource)` by walking the jurisdiction
tree, rather than a flat list of camera-level grants.

A user is granted one or more jurisdiction nodes (models.rbac.UserJurisdiction).
Granting a node implicitly grants every descendant of that node too (a
district grant covers all its stations; the statewide root grant covers
the entire tree, including department branches — see models/rbac.py). This
module is the only place that walk happens, via a recursive CTE, so the
"does this grant cover that camera" logic exists exactly once.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.rbac import Jurisdiction, User, UserJurisdiction


async def user_has_statewide_grant(db: AsyncSession, user: User) -> bool:
    """True only if `user` is directly granted the statewide root itself
    (not merely a scope that happens to cover a lot of districts). Used to
    gate bulk, catalogue-wide operations like POST /cameras/sync, which
    touch every jurisdiction's cameras regardless of the caller's own
    scope — a district-level camera:manage holder shouldn't be able to
    bulk-create cameras belonging to other districts just by triggering a
    sync.
    """
    result = await db.execute(
        select(Jurisdiction.id)
        .join(UserJurisdiction, UserJurisdiction.jurisdiction_id == Jurisdiction.id)
        .where(UserJurisdiction.user_id == user.id, Jurisdiction.scope_type == "statewide")
    )
    return result.first() is not None


async def get_user_scope_jurisdiction_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    """All jurisdiction ids `user` has access to: their directly granted
    nodes plus every descendant of each. Returns an empty set for a user
    with no grants yet (least-privilege default — see models.rbac.User).
    """
    granted = (
        await db.execute(
            select(UserJurisdiction.jurisdiction_id).where(UserJurisdiction.user_id == user.id)
        )
    ).scalars().all()

    if not granted:
        return set()

    base = (
        select(Jurisdiction.id)
        .where(Jurisdiction.id.in_(granted))
        .cte(name="jurisdiction_scope", recursive=True)
    )
    children = select(Jurisdiction.id).join(base, Jurisdiction.parent_id == base.c.id)
    scope_cte = base.union(children)

    result = await db.execute(select(scope_cte.c.id))
    return {row[0] for row in result.all()}


async def is_in_jurisdiction(
    db: AsyncSession, user: User, jurisdiction_id: uuid.UUID | None
) -> bool:
    """A camera/resource with no jurisdiction assigned yet is visible to
    nobody but the tiers that manage the registry itself — an unassigned
    camera is a data-quality gap, not something to leak into every
    dashboard by defaulting to "visible".
    """
    if jurisdiction_id is None:
        return False
    scope = await get_user_scope_jurisdiction_ids(db, user)
    return jurisdiction_id in scope
