"""Read-only client for the camera gateway's `/api/ingest` catalogue —
this service only needs to know which camera_ids currently exist; go2rtc
(see services/ingestion-config) has already normalized every one of them
into a uniform RTSP republish, so this module doesn't need the catalogue's
protocol/source details at all, only the id list. Consume only: never the
gateway's control API, matching the same rule stream_manager.py follows.
"""

from __future__ import annotations

import logging

import httpx

import config

log = logging.getLogger("inference.catalogue_client")


async def fetch_active_camera_ids() -> set[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(config.INGEST_API_URL, timeout=10.0)
        resp.raise_for_status()
        payload = resp.json()

    entries = payload.get("cameras", payload if isinstance(payload, list) else [])
    camera_ids: set[str] = set()
    for entry in entries:
        camera_id = entry.get("camera_id")
        # The gateway reports live status per camera in the catalogue
        # itself (see docs/gateway-contract.md) — skip spinning up a
        # worker thread for a camera it already knows is down, same as
        # stream_manager.py does on the ingestion side.
        if camera_id and entry.get("live") is not False:
            camera_ids.add(camera_id)
    return camera_ids
