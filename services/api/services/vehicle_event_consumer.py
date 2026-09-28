"""Consumes the `vehicle_events` Redis Stream (published by
services/inference/pipeline.py: _finalize_track, once a
track_state.TrackSession is finalized) into the vehicle_events Postgres
table. Structurally identical to plate_event_consumer.py — its own
consumer group so a restart resumes from where it left off, same
idempotent-insert-on-conflict pattern — kept as a separate module (rather
than folding into plate_event_consumer.py) because the two streams carry
different event shapes and have different downstream consumers
(watchlist_engine.py only cares about plate_events).
"""

from __future__ import annotations

import asyncio
import logging

import redis.asyncio as redis
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import settings
from database import AsyncSessionLocal
from metrics import VEHICLE_EVENTS_PERSISTED_TOTAL
from models.vehicle_event import VehicleEventRecord

log = logging.getLogger("api.vehicle_event_consumer")

_GROUP = "api-vehicle-consumer"
_CONSUMER = "api-1"
_BLOCK_MS = 5000
_BATCH_SIZE = 50


async def _ensure_group(client: redis.Redis) -> None:
    try:
        await client.xgroup_create(settings.redis_stream_vehicle_events, _GROUP, id="0", mkstream=True)
        log.info("Created consumer group %s on stream %s", _GROUP, settings.redis_stream_vehicle_events)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise  # anything other than "group already exists" is unexpected


def _parse_entry(fields: dict[str, str]) -> VehicleEventRecord | None:
    try:
        return VehicleEventRecord(
            camera_id=fields["camera_id"],
            track_id=int(fields["track_id"]),
            first_seen_wall_ts_ms=float(fields["first_seen_wall_ts_ms"]),
            last_seen_wall_ts_ms=float(fields["last_seen_wall_ts_ms"]),
            vehicle_type=fields.get("vehicle_type", "unknown"),
            vehicle_type_observations=int(fields.get("vehicle_type_observations", 0)),
            plate_text=fields.get("plate_text", ""),
            plate_confidence=float(fields.get("plate_confidence", 0.0)),
            plate_region=fields.get("plate_region", ""),
            plate_valid=fields.get("plate_valid", "0") == "1",
            plate_observations=int(fields.get("plate_observations", 0)),
            plate_agreement=float(fields.get("plate_agreement", 0.0)),
            manufacturer=fields.get("manufacturer", ""),
            manufacturer_confidence=float(fields.get("manufacturer_confidence", 0.0)),
            model=fields.get("model", ""),
            model_confidence=float(fields.get("model_confidence", 0.0)),
            best_vehicle_image_path=fields.get("best_vehicle_image_path", ""),
            best_plate_image_path=fields.get("best_plate_image_path", ""),
        )
    except (KeyError, ValueError):
        log.exception("Malformed vehicle_events entry, fields=%r — skipping", fields)
        return None


async def run(stop_event: asyncio.Event) -> None:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    await _ensure_group(client)
    log.info("vehicle_event_consumer started (group=%s consumer=%s)", _GROUP, _CONSUMER)

    while not stop_event.is_set():
        try:
            response = await client.xreadgroup(
                _GROUP,
                _CONSUMER,
                {settings.redis_stream_vehicle_events: ">"},
                count=_BATCH_SIZE,
                block=_BLOCK_MS,
            )
        except redis.RedisError:
            log.exception("vehicle_event_consumer: XREADGROUP failed, retrying in 5s")
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
                        pg_insert(VehicleEventRecord)
                        .values(**{c.name: getattr(record, c.name) for c in VehicleEventRecord.__table__.columns})
                        .on_conflict_do_nothing(index_elements=["stream_entry_id"])
                    )
                    await db.execute(stmt)
                    VEHICLE_EVENTS_PERSISTED_TOTAL.inc()
                # Malformed entries are ACKed too (skipped, not retried) —
                # same rationale as plate_event_consumer.py: a message
                # that fails to parse once will fail forever.
                ack_ids.append(entry_id)

            await db.commit()

        if ack_ids:
            await client.xack(settings.redis_stream_vehicle_events, _GROUP, *ack_ids)

    await client.aclose()
    log.info("vehicle_event_consumer stopped")
