"""Runs camera_registry_sync.sync_from_catalogue on a timer, so the camera
registry (and therefore the Video Wall / Registry Map / jurisdiction
scoping everything else depends on) is populated automatically instead of
requiring an operator to remember to POST /cameras/sync by hand — that
manual-only path was the actual reason the registry could sit at "0
cameras in your jurisdiction" indefinitely even with a live, reachable
catalogue.

Runs as a background asyncio task inside the api process (see main.py's
lifespan), matching the existing plate_event_consumer/watchlist_engine
pattern — one more moving part isn't worth a separate container at this
scale.
"""

from __future__ import annotations

import asyncio
import logging

from config import settings
from database import AsyncSessionLocal
from services.camera_registry_sync import sync_from_catalogue

log = logging.getLogger("api.camera_sync_scheduler")


async def run(stop_event: asyncio.Event) -> None:
    log.info(
        "camera_sync_scheduler started (catalogue=%s interval=%ds)",
        settings.ingest_api_url,
        settings.ingest_poll_interval_seconds,
    )
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                added, updated, unassigned = await sync_from_catalogue(db)
                await db.commit()
                if added or updated:
                    log.info(
                        "camera sync: %d added, %d updated, %d left unassigned",
                        added, updated, len(unassigned),
                    )
        except Exception:
            # A catalogue that's temporarily unreachable (still starting
            # up, network blip) must not crash this loop or take down the
            # api process — just log and retry on the next tick, same
            # tolerance stream_manager already has for its own polling.
            log.exception("camera sync failed — will retry on next tick")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.ingest_poll_interval_seconds)
        except asyncio.TimeoutError:
            pass  # normal: timer elapsed, loop again

    log.info("camera_sync_scheduler stopped")
