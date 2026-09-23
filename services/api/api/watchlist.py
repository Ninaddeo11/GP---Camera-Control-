"""Watchlist CRUD and match feed. `watchlist:write` (add/deactivate
entries) and `watchlist:read` (view entries/matches) are separate
permissions — see scripts/seed_users.py — because a tier that should see
alerts doesn't necessarily get to define what's on the watchlist.
Acknowledging a match is gated on `alert:acknowledge` specifically, a
broader-held permission than watchlist:write (field tiers can ack an
alert they're responding to without being able to add watchlist entries).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.camera import Camera
from models.rbac import User
from models.watchlist import WATCHLIST_PRIORITIES, WatchlistEntry, WatchlistMatch
from schemas.watchlist import WatchlistEntryCreate, WatchlistEntryOut, WatchlistMatchOut
from security.rbac import require_permission
from services import media
from services.jurisdiction_service import get_user_scope_jurisdiction_ids

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _normalize_plate(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()


@router.get("", response_model=list[WatchlistEntryOut])
async def list_watchlist(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("watchlist:read")),
) -> list[WatchlistEntryOut]:
    query = select(WatchlistEntry)
    if active_only:
        query = query.where(WatchlistEntry.active.is_(True))
    entries = (await db.execute(query.order_by(WatchlistEntry.created_at.desc()))).scalars().all()
    return [WatchlistEntryOut.model_validate(e) for e in entries]


@router.post("", response_model=WatchlistEntryOut, status_code=status.HTTP_201_CREATED)
async def create_watchlist_entry(
    payload: WatchlistEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("watchlist:write", audit_on_success=True)),
) -> WatchlistEntryOut:
    if payload.priority not in WATCHLIST_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": f"priority must be one of {WATCHLIST_PRIORITIES}.", "code": "invalid_priority"},
        )

    plate_text = _normalize_plate(payload.plate_text)
    existing = (
        await db.execute(select(WatchlistEntry).where(WatchlistEntry.plate_text == plate_text))
    ).scalar_one_or_none()
    if existing is not None:
        if existing.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "This plate is already on the watchlist.", "code": "conflict"},
            )
        existing.active = True
        existing.reason = payload.reason
        existing.priority = payload.priority
        existing.added_by = user.id
        await db.flush()
        return WatchlistEntryOut.model_validate(existing)

    entry = WatchlistEntry(
        plate_text=plate_text, reason=payload.reason, priority=payload.priority, added_by=user.id
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return WatchlistEntryOut.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_watchlist_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_permission("watchlist:write", resource_id_param="entry_id", audit_on_success=True)
    ),
) -> None:
    entry = (
        await db.execute(select(WatchlistEntry).where(WatchlistEntry.id == entry_id))
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Watchlist entry not found.", "code": "not_found"},
        )
    entry.active = False
    await db.flush()


@router.get("/matches", response_model=list[WatchlistMatchOut])
async def list_matches(
    acknowledged: bool | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("watchlist:read", audit_on_success=True)),
) -> list[WatchlistMatchOut]:
    scope_ids = await get_user_scope_jurisdiction_ids(db, user)
    if not scope_ids:
        return []

    scoped_camera_ids = (
        await db.execute(select(Camera.camera_id).where(Camera.jurisdiction_id.in_(scope_ids)))
    ).scalars().all()
    if not scoped_camera_ids:
        return []

    query = select(WatchlistMatch).where(WatchlistMatch.camera_id.in_(scoped_camera_ids))
    if acknowledged is not None:
        query = query.where(WatchlistMatch.acknowledged.is_(acknowledged))
    matches = (
        await db.execute(query.order_by(WatchlistMatch.matched_at.desc()).limit(min(limit, 500)))
    ).scalars().all()

    cameras_by_id = {
        c.camera_id: c
        for c in (
            await db.execute(select(Camera).where(Camera.camera_id.in_(scoped_camera_ids)))
        ).scalars().all()
    }
    watchlist_entries_by_id = {
        e.id: e
        for e in (
            await db.execute(
                select(WatchlistEntry).where(
                    WatchlistEntry.id.in_({m.watchlist_id for m in matches})
                )
            )
        ).scalars().all()
    }
    acknowledgers = {
        u.id: u.username
        for u in (
            await db.execute(
                select(User).where(
                    User.id.in_({m.acknowledged_by for m in matches if m.acknowledged_by})
                )
            )
        ).scalars().all()
    }

    return [
        WatchlistMatchOut(
            id=m.id,
            watchlist_id=m.watchlist_id,
            watchlist_plate_text=watchlist_entries_by_id[m.watchlist_id].plate_text,
            camera_id=m.camera_id,
            camera_name=cameras_by_id[m.camera_id].name if m.camera_id in cameras_by_id else m.camera_id,
            matched_plate_text=m.matched_plate_text,
            match_score=m.match_score,
            confidence=m.confidence,
            priority=watchlist_entries_by_id[m.watchlist_id].priority,
            reason=watchlist_entries_by_id[m.watchlist_id].reason,
            wall_ts=m.wall_ts,
            snapshot_url=media.snapshot_url(m.snapshot_path),
            acknowledged=m.acknowledged,
            acknowledged_by_username=acknowledgers.get(m.acknowledged_by) if m.acknowledged_by else None,
            acknowledged_at=m.acknowledged_at,
        )
        for m in matches
    ]


@router.post("/matches/{match_id}/acknowledge", response_model=WatchlistMatchOut)
async def acknowledge_match(
    match_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_permission("alert:acknowledge", resource_id_param="match_id", audit_on_success=True)
    ),
) -> WatchlistMatchOut:
    match = (
        await db.execute(select(WatchlistMatch).where(WatchlistMatch.id == match_id))
    ).scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Match not found.", "code": "not_found"},
        )

    camera = (
        await db.execute(select(Camera).where(Camera.camera_id == match.camera_id))
    ).scalar_one_or_none()
    scope_ids = await get_user_scope_jurisdiction_ids(db, user)
    if camera is None or camera.jurisdiction_id not in scope_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Out of jurisdiction.", "code": "out_of_jurisdiction"},
        )

    match.acknowledged = True
    match.acknowledged_by = user.id
    match.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()

    watchlist_entry = (
        await db.execute(select(WatchlistEntry).where(WatchlistEntry.id == match.watchlist_id))
    ).scalar_one()

    return WatchlistMatchOut(
        id=match.id,
        watchlist_id=match.watchlist_id,
        watchlist_plate_text=watchlist_entry.plate_text,
        camera_id=match.camera_id,
        camera_name=camera.name,
        matched_plate_text=match.matched_plate_text,
        match_score=match.match_score,
        confidence=match.confidence,
        priority=watchlist_entry.priority,
        reason=watchlist_entry.reason,
        wall_ts=match.wall_ts,
        snapshot_url=media.snapshot_url(match.snapshot_path),
        acknowledged=True,
        acknowledged_by_username=user.username,
        acknowledged_at=match.acknowledged_at,
    )
