"""Pulls the camera gateway's `/api/ingest` catalogue into the registry
database, so the registry (jurisdiction assignment, GIS metadata, status)
has something to enrich instead of every service re-fetching the raw
catalogue independently. Mirrors the protocol-priority logic in
services/ingestion-config/stream_manager.py (RTSP > WHEP > HLS) purely for
display purposes here — this module never talks to go2rtc.

Jurisdiction assignment on sync is best-effort: a camera whose catalogue
`department` string matches a seeded jurisdiction name is auto-assigned;
anything else is left unassigned (visible only to camera:manage holders)
until an operator assigns it via PATCH /cameras/{camera_id}. Cameras are
never guessed into a jurisdiction — a wrong auto-assignment would leak
footage across a jurisdiction boundary, which is worse than requiring a
manual step.
"""

from __future__ import annotations

import httpx
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.camera import Camera
from models.rbac import Jurisdiction


def _resolve_protocol(entry: dict) -> str:
    protocols = entry.get("protocols") or {}
    if protocols.get("rtsp"):
        return "rtsp"
    if protocols.get("whep"):
        return "whep"
    if protocols.get("hls"):
        return "hls"
    return ""


async def sync_from_catalogue(db: AsyncSession) -> tuple[int, int, list[str]]:
    """Returns (added_count, updated_count, camera_ids_left_unassigned)."""

    headers = {}
    if settings.ingest_api_auth_header and settings.ingest_api_auth_token:
        headers[settings.ingest_api_auth_header] = settings.ingest_api_auth_token

    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.ingest_api_url, headers=headers, timeout=10.0)
        resp.raise_for_status()
        payload = resp.json()

    entries = payload.get("cameras", payload if isinstance(payload, list) else [])

    jurisdictions_by_name = {
        j.name.strip().lower(): j
        for j in (await db.execute(select(Jurisdiction))).scalars().all()
    }

    existing_by_camera_id = {
        c.camera_id: c for c in (await db.execute(select(Camera))).scalars().all()
    }

    added = 0
    updated = 0
    unassigned: list[str] = []

    for entry in entries:
        camera_id = entry.get("camera_id")
        if not camera_id:
            continue

        department = entry.get("department", "")
        jurisdiction = jurisdictions_by_name.get(department.strip().lower())

        camera = existing_by_camera_id.get(camera_id)
        is_new = camera is None
        if is_new:
            camera = Camera(camera_id=camera_id)
            db.add(camera)

        camera.name = entry.get("name", camera_id)
        camera.department = department
        camera.protocol = _resolve_protocol(entry)
        camera.resolution = entry.get("resolution", "")
        camera.codec = entry.get("codec", "")
        camera.fps = float(entry.get("fps", 0) or 0)

        # Only set on first sync — never overwrite a manually corrected
        # jurisdiction assignment or GIS fix on a later sync.
        if is_new and jurisdiction is not None:
            camera.jurisdiction_id = jurisdiction.id
        lat, lon = entry.get("lat"), entry.get("lon")
        if is_new and lat is not None and lon is not None:
            camera.location = WKTElement(f"POINT({lon} {lat})", srid=4326)

        if camera.jurisdiction_id is None:
            unassigned.append(camera_id)

        if is_new:
            added += 1
        else:
            updated += 1

    await db.flush()
    return added, updated, unassigned
