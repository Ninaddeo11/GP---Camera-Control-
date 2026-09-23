"""Camera registry endpoints. Every list/read is scoped to the caller's
jurisdiction — there is no "show me everything" escape hatch, including
for admins; T1's statewide grant covers everything by construction (see
services/jurisdiction_service.py), so it doesn't need one.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.camera import Camera
from models.rbac import User
from schemas.camera import CameraCreate, CameraOut, CameraSyncResult, CameraUpdate
from security.rbac import (
    ForbiddenError,
    audit_access,
    check_resource_jurisdiction,
    get_permission_codes,
    require_permission,
)
from services.camera_registry_sync import sync_from_catalogue
from services.jurisdiction_service import get_user_scope_jurisdiction_ids, user_has_statewide_grant

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _point(lat: float | None, lon: float | None) -> WKTElement | None:
    if lat is None or lon is None:
        return None
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def _to_out(camera: Camera) -> CameraOut:
    lat = lon = None
    if camera.location is not None:
        shape = to_shape(camera.location)
        lon, lat = shape.x, shape.y
    return CameraOut(
        id=camera.id,
        camera_id=camera.camera_id,
        name=camera.name,
        department=camera.department,
        jurisdiction_id=camera.jurisdiction_id,
        lat=lat,
        lon=lon,
        protocol=camera.protocol,
        resolution=camera.resolution,
        codec=camera.codec,
        fps=camera.fps,
        status=camera.status,
        is_active=camera.is_active,
        updated_at=camera.updated_at,
    )


async def _load_active_camera(db: AsyncSession, camera_id: str) -> Camera:
    camera = (
        await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    ).scalar_one_or_none()
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Camera not found.", "code": "not_found"},
        )
    return camera


async def _authorize_camera_access(
    db: AsyncSession, request: Request, *, user: User, camera: Camera, action: str
) -> None:
    """isInJurisdiction for a single camera, with one deliberate carve-out:
    an unassigned camera (jurisdiction_id is None) is visible to
    camera:manage holders specifically so they have somewhere to resolve
    it via PATCH — see list_cameras for the matching carve-out on listing.
    Everyone else is denied, same as check_resource_jurisdiction's default
    for an unassigned resource.
    """
    if camera.jurisdiction_id is None:
        permission_codes = await get_permission_codes(db, user.role_id)
        if "camera:manage" in permission_codes:
            return
        await audit_access(
            db,
            request,
            user=user,
            action=action,
            outcome="deny",
            resource_type="camera",
            resource_id=camera.camera_id,
            reason="unassigned_jurisdiction",
        )
        raise ForbiddenError("unassigned_jurisdiction")

    await check_resource_jurisdiction(
        db,
        request,
        user=user,
        jurisdiction_id=camera.jurisdiction_id,
        action=action,
        resource_type="camera",
        resource_id=camera.camera_id,
    )


@router.get("", response_model=list[CameraOut])
async def list_cameras(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("camera:read")),
) -> list[CameraOut]:
    scope_ids = await get_user_scope_jurisdiction_ids(db, user)
    permission_codes = await get_permission_codes(db, user.role_id)

    query = select(Camera).where(Camera.is_active.is_(True))
    if "camera:manage" in permission_codes:
        # Registry managers also see not-yet-assigned cameras, so there's
        # somewhere for "unassigned" sync results to actually be resolved.
        query = query.where(
            or_(Camera.jurisdiction_id.in_(scope_ids), Camera.jurisdiction_id.is_(None))
        )
    else:
        query = query.where(Camera.jurisdiction_id.in_(scope_ids))

    cameras = (await db.execute(query.order_by(Camera.name))).scalars().all()
    return [_to_out(c) for c in cameras]


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(
    camera_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("camera:read", resource_id_param="camera_id")),
) -> CameraOut:
    camera = await _load_active_camera(db, camera_id)
    await _authorize_camera_access(db, request, user=user, camera=camera, action="camera:read")
    return _to_out(camera)


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("camera:manage")),
) -> CameraOut:
    existing = (
        await db.execute(select(Camera).where(Camera.camera_id == payload.camera_id))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "A camera with this camera_id already exists.", "code": "conflict"},
        )

    if payload.jurisdiction_id is not None:
        # camera:manage alone doesn't authorize placing a camera in a
        # jurisdiction outside the actor's own scope — otherwise a
        # district-level manager could plant a camera in another
        # district's tree.
        await check_resource_jurisdiction(
            db,
            request,
            user=user,
            jurisdiction_id=payload.jurisdiction_id,
            action="camera:manage",
            resource_type="camera",
            resource_id=payload.camera_id,
        )

    camera = Camera(
        camera_id=payload.camera_id,
        name=payload.name,
        department=payload.department,
        jurisdiction_id=payload.jurisdiction_id,
        location=_point(payload.lat, payload.lon),
        protocol=payload.protocol,
        resolution=payload.resolution,
        codec=payload.codec,
        fps=payload.fps,
    )
    db.add(camera)
    await db.flush()
    await db.refresh(camera)
    return _to_out(camera)


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: str,
    payload: CameraUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("camera:manage", resource_id_param="camera_id")),
) -> CameraOut:
    camera = await _load_active_camera(db, camera_id)
    await _authorize_camera_access(db, request, user=user, camera=camera, action="camera:manage")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        camera.name = data["name"]
    if "department" in data:
        camera.department = data["department"]
    if "jurisdiction_id" in data:
        if data["jurisdiction_id"] is not None and data["jurisdiction_id"] != camera.jurisdiction_id:
            # Re-checked against the *new* jurisdiction, not just the
            # existing one above — see create_camera for why.
            await check_resource_jurisdiction(
                db,
                request,
                user=user,
                jurisdiction_id=data["jurisdiction_id"],
                action="camera:manage",
                resource_type="camera",
                resource_id=camera_id,
            )
        camera.jurisdiction_id = data["jurisdiction_id"]
    if "is_active" in data:
        camera.is_active = data["is_active"]
    if "lat" in data or "lon" in data:
        camera.location = _point(payload.lat, payload.lon)

    await db.flush()
    await db.refresh(camera)
    return _to_out(camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_camera(
    camera_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("camera:manage", resource_id_param="camera_id")),
) -> None:
    camera = await _load_active_camera(db, camera_id)
    await _authorize_camera_access(db, request, user=user, camera=camera, action="camera:manage")
    camera.is_active = False
    await db.flush()


@router.post("/sync", response_model=CameraSyncResult)
async def sync_cameras(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("camera:manage")),
) -> CameraSyncResult:
    # The catalogue spans every jurisdiction, so syncing it is gated on a
    # true statewide grant, not just camera:manage — see
    # jurisdiction_service.user_has_statewide_grant for why.
    if not await user_has_statewide_grant(db, user):
        await audit_access(
            db,
            request,
            user=user,
            action="camera:manage",
            outcome="deny",
            resource_type="camera_sync",
            reason="statewide_scope_required",
        )
        raise ForbiddenError("statewide_scope_required")

    added, updated, unassigned = await sync_from_catalogue(db)
    await audit_access(
        db,
        request,
        user=user,
        action="camera:manage",
        outcome="allow",
        resource_type="camera_sync",
        resource_id=f"added={added},updated={updated}",
    )
    return CameraSyncResult(added=added, updated=updated, unassigned_jurisdiction=unassigned)
