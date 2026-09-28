"""Streaming watchlist correlation: consumes the same `plate_events` Redis
Stream services/inference publishes to (see plate_event_consumer.py for
why this is a second, independent consumer group rather than a step
bolted onto that one), fuzzy-matches each plate read against the active
watchlist, records a WatchlistMatch, and pushes it to any connected alert
console via alert_dispatcher.broadcaster.

Matching: exact match OR rapidfuzz.token_sort_ratio >= 92, per the project
brief — high enough to absorb a single OCR-confusable character without
matching two genuinely different plates.

Deduplication: the same plate is not re-alerted on the same camera within
a 5-minute window — a vehicle idling in frame would otherwise flood the
console with repeat alerts for a single real event.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from rapidfuzz import fuzz
from sqlalchemy import select

from config import settings
from database import AsyncSessionLocal
from metrics import WATCHLIST_MATCHES_TOTAL
from models.camera import Camera
from models.watchlist import WatchlistEntry, WatchlistMatch
from services import media
from services.alert_dispatcher import broadcaster

log = logging.getLogger("api.watchlist_engine")

_GROUP = "api-watchlist-engine"
_CONSUMER = "api-1"
_BLOCK_MS = 5000
_BATCH_SIZE = 50
_MATCH_THRESHOLD = 92.0
_DEDUP_WINDOW = timedelta(minutes=5)


async def _ensure_group(client: redis.Redis) -> None:
    try:
        # id="$" (new events only from here on), unlike
        # plate_event_consumer's "0" backfill — alerting on stale,
        # already-historical plate reads the moment this service first
        # starts would be misleading, not useful.
        await client.xgroup_create(settings.redis_stream_plate_events, _GROUP, id="$", mkstream=True)
        log.info("Created consumer group %s on stream %s", _GROUP, settings.redis_stream_plate_events)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def _best_match(plate_text: str, entries: list[WatchlistEntry]) -> tuple[WatchlistEntry, float] | None:
    best: tuple[WatchlistEntry, float] | None = None
    for entry in entries:
        if plate_text == entry.plate_text:
            return entry, 100.0
        score = fuzz.token_sort_ratio(plate_text, entry.plate_text)
        if score >= _MATCH_THRESHOLD and (best is None or score > best[1]):
            best = (entry, score)
    return best


class _RecentAlertCache:
    """(watchlist_id, camera_id) -> last alert time, purged lazily."""

    def __init__(self) -> None:
        self._last_alerted: dict[tuple, datetime] = {}

    def should_alert(self, watchlist_id, camera_id: str, now: datetime) -> bool:
        key = (watchlist_id, camera_id)
        last = self._last_alerted.get(key)
        return last is None or (now - last) >= _DEDUP_WINDOW

    def record(self, watchlist_id, camera_id: str, now: datetime) -> None:
        self._last_alerted[(watchlist_id, camera_id)] = now


async def run(stop_event: asyncio.Event) -> None:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    await _ensure_group(client)
    dedup = _RecentAlertCache()
    log.info("watchlist_engine started (group=%s consumer=%s)", _GROUP, _CONSUMER)

    while not stop_event.is_set():
        try:
            response = await client.xreadgroup(
                _GROUP,
                _CONSUMER,
                {settings.redis_stream_plate_events: ">"},
                count=_BATCH_SIZE,
                block=_BLOCK_MS,
            )
        except redis.RedisError:
            log.exception("watchlist_engine: XREADGROUP failed, retrying in 5s")
            await asyncio.sleep(5.0)
            continue

        if not response:
            continue

        _, entries = response[0]
        ack_ids: list[str] = []

        async with AsyncSessionLocal() as db:
            active_entries = (
                await db.execute(select(WatchlistEntry).where(WatchlistEntry.active.is_(True)))
            ).scalars().all()

            for entry_id, fields in entries:
                ack_ids.append(entry_id)
                if not active_entries:
                    continue
                try:
                    await _process_event(db, client, fields, active_entries, dedup)
                except Exception:
                    log.exception("watchlist_engine: failed to process entry %s", entry_id)

            await db.commit()

        if ack_ids:
            await client.xack(settings.redis_stream_plate_events, _GROUP, *ack_ids)

    await client.aclose()
    log.info("watchlist_engine stopped")


async def _process_event(
    db, client: redis.Redis, fields: dict, active_entries: list[WatchlistEntry], dedup: _RecentAlertCache
) -> None:
    plate_text = fields.get("plate_text", "")
    camera_id = fields.get("camera_id", "")
    if not plate_text or not camera_id:
        return

    matched = _best_match(plate_text, active_entries)
    if matched is None:
        return
    watchlist_entry, score = matched

    now = datetime.now(timezone.utc)
    if not dedup.should_alert(watchlist_entry.id, camera_id, now):
        return
    dedup.record(watchlist_entry.id, camera_id, now)

    wall_ts_ms = float(fields.get("wall_ts_ms", 0))
    match = WatchlistMatch(
        watchlist_id=watchlist_entry.id,
        camera_id=camera_id,
        matched_plate_text=plate_text,
        match_score=score,
        confidence=float(fields.get("confidence", 0)),
        wall_ts=datetime.fromtimestamp(wall_ts_ms / 1000.0, tz=timezone.utc) if wall_ts_ms else now,
        snapshot_path=fields.get("snapshot_path", ""),
        matched_at=now,
    )
    db.add(match)
    await db.flush()
    WATCHLIST_MATCHES_TOTAL.inc()

    camera = (
        await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    ).scalar_one_or_none()
    camera_name = camera.name if camera else camera_id
    jurisdiction_id = camera.jurisdiction_id if camera else None

    log.warning(
        "WATCHLIST MATCH: plate=%s watchlist_plate=%s camera=%s score=%.0f priority=%s",
        plate_text,
        watchlist_entry.plate_text,
        camera_id,
        score,
        watchlist_entry.priority,
    )

    await broadcaster.broadcast(
        jurisdiction_id,
        {
            "type": "watchlist_match",
            "match_id": str(match.id),
            "watchlist_id": str(watchlist_entry.id),
            "watchlist_plate_text": watchlist_entry.plate_text,
            "matched_plate_text": plate_text,
            "match_score": score,
            "priority": watchlist_entry.priority,
            "reason": watchlist_entry.reason,
            "camera_id": camera_id,
            "camera_name": camera_name,
            "confidence": match.confidence,
            "wall_ts": match.wall_ts.isoformat(),
            "snapshot_url": media.snapshot_url(match.snapshot_path),
            "acknowledged": False,
        },
    )

    # Also published to the `watchlist_matches` Redis Stream (per the data
    # layer design) independent of the WebSocket push above, so an
    # analytics/audit consumer outside this process can subscribe without
    # going through the API.
    try:
        await client.xadd(
            settings.redis_stream_watchlist_matches,
            {
                "match_id": str(match.id),
                "watchlist_id": str(watchlist_entry.id),
                "watchlist_plate_text": watchlist_entry.plate_text,
                "matched_plate_text": match.matched_plate_text,
                "camera_id": match.camera_id,
                "priority": watchlist_entry.priority,
                "matched_at": match.matched_at.isoformat(),
            },
            maxlen=100_000,
            approximate=True,
        )
    except redis.RedisError:
        log.exception("Failed to publish watchlist_matches Redis event")
