"""Deletes plate/vehicle-event evidence (snapshot files + their DB rows)
older than `settings.evidence_retention_days` — brief section 18: "Do NOT
permanently store every video frame" plus a configurable retention policy,
which nothing in this codebase enforced before this script (snapshots and
evidence_exports previously accumulated indefinitely — see README.md
"Known gaps").

Deliberately a standalone script, not a scheduled background task inside
the api process: retention cleanup is an infrequent (daily, say),
possibly-slow filesystem walk, and mixing that into the same asyncio event
loop as request handling and the Redis Streams consumers risks stalling
both under load. Run this from cron/a scheduled job instead:

    docker compose exec api python scripts/cleanup_expired_evidence.py
    docker compose exec api python scripts/cleanup_expired_evidence.py --dry-run

Idempotent — safe to re-run; rows/files already deleted are simply not
found again.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select

from config import settings
from database import AsyncSessionLocal
from models.plate_event import PlateEventRecord
from models.vehicle_event import VehicleEventRecord

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("cleanup_expired_evidence")


def _unlink_if_exists(path_str: str, dry_run: bool) -> bool:
    if not path_str:
        return False
    path = Path(path_str)
    if not path.exists():
        return False
    if dry_run:
        return True
    try:
        path.unlink()
        return True
    except OSError:
        log.exception("Failed to delete evidence file %s", path)
        return False


async def _cleanup_plate_events(cutoff: datetime, dry_run: bool) -> tuple[int, int]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(select(PlateEventRecord).where(PlateEventRecord.wall_ts < cutoff))
        ).scalars().all()

        files_deleted = sum(_unlink_if_exists(r.snapshot_path, dry_run) for r in rows)
        if rows and not dry_run:
            ids = [r.id for r in rows]
            await db.execute(delete(PlateEventRecord).where(PlateEventRecord.id.in_(ids)))
            await db.commit()

        return len(rows), files_deleted


async def _cleanup_vehicle_events(cutoff_ms: float, dry_run: bool) -> tuple[int, int]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(VehicleEventRecord).where(VehicleEventRecord.last_seen_wall_ts_ms < cutoff_ms)
            )
        ).scalars().all()

        files_deleted = 0
        for r in rows:
            files_deleted += _unlink_if_exists(r.best_vehicle_image_path, dry_run)
            files_deleted += _unlink_if_exists(r.best_plate_image_path, dry_run)

        if rows and not dry_run:
            ids = [r.id for r in rows]
            await db.execute(delete(VehicleEventRecord).where(VehicleEventRecord.id.in_(ids)))
            await db.commit()

        return len(rows), files_deleted


async def main(dry_run: bool) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.evidence_retention_days)
    cutoff_ms = cutoff.timestamp() * 1000.0

    plate_rows, plate_files = await _cleanup_plate_events(cutoff, dry_run)
    vehicle_rows, vehicle_files = await _cleanup_vehicle_events(cutoff_ms, dry_run)

    verb = "Would delete" if dry_run else "Deleted"
    log.info(
        "%s %d plate_events row(s) / %d snapshot file(s), %d vehicle_events row(s) / %d evidence file(s) "
        "older than %d day(s) (cutoff=%s)",
        verb,
        plate_rows,
        plate_files,
        vehicle_rows,
        vehicle_files,
        settings.evidence_retention_days,
        cutoff.isoformat(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would be deleted without deleting anything"
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
