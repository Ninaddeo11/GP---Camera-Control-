"""Vehicle tracking query endpoints. Every route here requires
`vehicle_trace:read` (T1-T5 only, per scripts/seed_users.py — T8 never
holds this permission) and, per the acceptance checklist ("audit log
captures every access to tracking/watchlist/export endpoints"), audits
every successful access, not just denials.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.camera import Camera
from models.plate_event import PlateEventRecord
from models.rbac import User
from schemas.tracking import RecentDetectionOut, RouteGeoJSON, TraversalResult
from security.rbac import require_permission
from services import media, vehicle_trace
from services.jurisdiction_service import get_user_scope_jurisdiction_ids

router = APIRouter(prefix="/tracking", tags=["tracking"])


def _clean_plate_query(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()


@router.get("/plate/{plate}", response_model=TraversalResult)
async def get_plate_traversal(
    plate: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_permission("vehicle_trace:read", resource_id_param="plate", audit_on_success=True)
    ),
) -> TraversalResult:
    return await vehicle_trace.build_traversal(db, _clean_plate_query(plate), user)


@router.get("/plate/{plate}/route", response_model=RouteGeoJSON)
async def get_plate_route(
    plate: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_permission("vehicle_trace:read", resource_id_param="plate", audit_on_success=True)
    ),
) -> RouteGeoJSON:
    traversal = await vehicle_trace.build_traversal(db, _clean_plate_query(plate), user)
    return vehicle_trace.to_route_geojson(traversal)


@router.get("/recent", response_model=list[RecentDetectionOut])
async def get_recent_detections(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("vehicle_trace:read", audit_on_success=True)),
) -> list[RecentDetectionOut]:
    scope_ids = await get_user_scope_jurisdiction_ids(db, user)
    if not scope_ids:
        return []

    scoped_camera_ids = (
        await db.execute(select(Camera.camera_id).where(Camera.jurisdiction_id.in_(scope_ids)))
    ).scalars().all()
    if not scoped_camera_ids:
        return []

    events = (
        await db.execute(
            select(PlateEventRecord)
            .where(PlateEventRecord.camera_id.in_(scoped_camera_ids))
            .order_by(PlateEventRecord.wall_ts.desc())
            .limit(min(limit, 200))
        )
    ).scalars().all()

    cameras_by_id = {
        c.camera_id: c
        for c in (
            await db.execute(select(Camera).where(Camera.camera_id.in_(scoped_camera_ids)))
        ).scalars().all()
    }

    return [
        RecentDetectionOut(
            id=e.id,
            camera_id=e.camera_id,
            camera_name=cameras_by_id[e.camera_id].name,
            plate_text=e.plate_text,
            confidence=e.confidence,
            vehicle_class=e.vehicle_class,
            wall_ts=e.wall_ts,
            snapshot_url=media.snapshot_url(e.snapshot_path),
        )
        for e in events
    ]
