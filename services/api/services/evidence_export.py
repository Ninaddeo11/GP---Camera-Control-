"""Section 65B-style evidentiary export: every plate-read event matched to
a search, its snapshot, a CSV summary, and a chain-of-custody manifest
recording the SHA-256 of every file in the package — independent of
audit_log's own hash chain, this is what an investigator hands over as
evidence, so its integrity has to be verifiable without trusting this
service after the fact.

Jurisdiction scoping is identical to vehicle_trace.py's: an event whose
camera isn't in the exporter's jurisdiction is silently excluded, not
included-with-a-warning — an export is evidence, and evidence assembled
from an unauthorized camera is a jurisdiction leak, not a caveat.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.camera import Camera
from models.evidence_export import EvidenceExport
from models.plate_event import PlateEventRecord
from models.rbac import User
from services import vehicle_trace
from services.jurisdiction_service import get_user_scope_jurisdiction_ids

EXPORT_DIR = Path("/data/exports")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def build_export(
    db: AsyncSession,
    user: User,
    plate_query: str,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> EvidenceExport:
    plate_texts = await vehicle_trace.find_matching_plate_texts(db, plate_query)

    query = select(PlateEventRecord).order_by(PlateEventRecord.wall_ts.asc())
    if plate_texts:
        query = query.where(PlateEventRecord.plate_text.in_(plate_texts))
    else:
        query = query.where(PlateEventRecord.plate_text == plate_query)  # yields zero rows, not an error
    if from_ts is not None:
        query = query.where(PlateEventRecord.wall_ts >= from_ts)
    if to_ts is not None:
        query = query.where(PlateEventRecord.wall_ts <= to_ts)

    all_events = (await db.execute(query)).scalars().all()

    scope_ids = await get_user_scope_jurisdiction_ids(db, user)
    camera_ids = {e.camera_id for e in all_events}
    cameras_by_id = {
        c.camera_id: c
        for c in (
            await db.execute(select(Camera).where(Camera.camera_id.in_(camera_ids)))
        ).scalars().all()
    }

    events = [
        e
        for e in all_events
        if (camera := cameras_by_id.get(e.camera_id)) is not None and camera.jurisdiction_id in scope_ids
    ]

    export_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = EXPORT_DIR / f"{export_id}.zip"

    manifest_files: list[dict] = []
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        ["event_id", "camera_id", "camera_name", "plate_text", "confidence", "wall_ts", "snapshot_file"]
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for event in events:
            snapshot_arcname = ""
            snapshot_file = Path(event.snapshot_path) if event.snapshot_path else None
            if snapshot_file is not None and snapshot_file.is_file():
                snapshot_arcname = f"snapshots/{event.camera_id}/{snapshot_file.name}"
                zf.write(snapshot_file, snapshot_arcname)
                manifest_files.append({"path": snapshot_arcname, "sha256": _sha256_file(snapshot_file)})

            camera_name = cameras_by_id[event.camera_id].name
            writer.writerow(
                [
                    str(event.id),
                    event.camera_id,
                    camera_name,
                    event.plate_text,
                    f"{event.confidence:.4f}",
                    event.wall_ts.isoformat(),
                    snapshot_arcname,
                ]
            )

        csv_bytes = csv_buffer.getvalue().encode("utf-8")
        zf.writestr("events.csv", csv_bytes)
        manifest_files.append({"path": "events.csv", "sha256": _sha256_bytes(csv_bytes)})

        manifest = {
            "export_id": str(export_id),
            "plate_query": plate_query,
            "matched_plate_texts": plate_texts or [plate_query],
            "exported_by": user.username,
            "exported_by_full_name": user.full_name,
            "exported_at": now.isoformat(),
            "event_count": len(events),
            "omitted_out_of_jurisdiction_count": len(all_events) - len(events),
            "files": manifest_files,
            "note": (
                "Each file's sha256 above is independently verifiable. "
                "This manifest itself is not self-hashed (a file cannot "
                "commit to its own hash) — the package's overall integrity "
                "is instead the sha256 of the complete .zip, recorded in "
                "the evidence_exports table and returned alongside the "
                "download link."
            ),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    package_sha256 = _sha256_file(zip_path)

    record = EvidenceExport(
        exported_by=user.id,
        plate_text=plate_query,
        event_ids=[str(e.id) for e in events],
        file_path=str(zip_path),
        sha256=package_sha256,
        exported_at=now,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record
