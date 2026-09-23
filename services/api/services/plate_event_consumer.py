"""Consumes the `plate_events` Redis Stream (published by
services/inference/anpr.py) into the plate_events Postgres table, via a
Redis Streams consumer group so a restart resumes from where it left off
rather than reprocessing or dropping events.

Runs as a background asyncio task inside the `api` process (see main.py's
lifespan) rather than a separate container — one more moving part isn't
worth it at this scale, and it keeps the write path (this consumer) next
to the read path (services/vehicle_trace.py) that depends on it.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import redis.asyncio as redis
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import settings
from database import AsyncSessionLocal
from metrics import PLATE_EVENTS_PERSISTED_TOTAL
from models.plate_event import PlateEventRecord

log = logging.getLogger("api.plate_event_consumer")

_GROUP = "api-plate-consumer"
_CONSUMER = "api-1"
_BLOCK_MS = 5000
_BATCH_SIZE = 50


async def _ensure_group(client: redis.Redis) -> None:
    try:
        # id="0" backfills anything already on the stream when this group
        # is first created (e.g. plate events published before the api
        # service existed in an earlier session) rather than only picking
        # up events from this point forward.
        await client.xgroup_create(settings.redis_stream_plate_events, _GROUP, id="0", mkstream=True)
        log.info("Created consumer group %s on stream %s", _GROUP, settings.redis_stream_plate_events)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise  # anything other than "group already exists" is unexpected


def _parse_entry(fields: dict[str, str]) -> PlateEventRecord | None:
    try:
        wall_ts_ms = float(fields["wall_ts_ms"])
        return PlateEventRecord(
            camera_id=fields["camera_id"],
            track_id=int(fields["track_id"]),
            plate_text=fields["plate_text"],
            confidence=float(fields["confidence"]),
            region=fields.get("region", ""),
            vehicle_class=fields.get("vehicle_class", ""),
            bbox={
                "x1": float(fields.get("bbox_x1", 0)),
                "y1": float(fields.get("bbox_y1", 0)),
                "x2": float(fields.get("bbox_x2", 0)),
                "y2": float(fields.get("bbox_y2", 0)),
            },
            frame_pts_ms=float(fields.get("frame_pts_ms", 0)),
            wall_ts_ms=wall_ts_ms,
            wall_ts=datetime.fromtimestamp(wall_ts_ms / 1000.0, tz=timezone.utc),
            snapshot_path=fields.get("snapshot_path", ""),
        )
    except (KeyError, ValueError):
        log.exception("Malformed plate_events entry, fields=%r — skipping", fields)
        return None


async def run(stop_event: asyncio.Event) -> None:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    await _ensure_group(client)
    log.info("plate_event_consumer started (group=%s consumer=%s)", _GROUP, _CONSUMER)

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
            log.exception("plate_event_consumer: XREADGROUP failed, retrying in 5s")
            await asyncio.sleep(5.0)
            continue

        if not response:
            continue  # BLOCK timeout with nothing new — loop and check stop_event

        _, entries = response[0]
        ack_ids: list[str] = []

        async with AsyncSessionLocal() as db:
            for entry_id, fields in entries:
                record = _parse_entry(fields)
                if record is not None:
                    record.stream_entry_id = entry_id
                    stmt = (
                        pg_insert(PlateEventRecord)
                        .values(**{c.name: getattr(record, c.name) for c in PlateEventRecord.__table__.columns})
                        .on_conflict_do_nothing(index_elements=["stream_entry_id"])
                    )
                    await db.execute(stmt)
                    PLATE_EVENTS_PERSISTED_TOTAL.inc()
                # Malformed entries are ACKed too (skipped, not retried) —
                # a message that fails to parse once will fail forever;
                # leaving it pending would block the group's checkpoint on
                # a poison message indefinitely.
                ack_ids.append(entry_id)

            await db.commit()

        if ack_ids:
            await client.xack(settings.redis_stream_plate_events, _GROUP, *ack_ids)

    await client.aclose()
    log.info("plate_event_consumer stopped")
