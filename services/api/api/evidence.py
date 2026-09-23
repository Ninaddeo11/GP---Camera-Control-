"""Section 65B-style evidentiary export. `evidence:export` is one of the
most restricted permissions in the system (T1-T3 only, per
scripts/seed_users.py) and every export — generation and download — is
audited, per the acceptance checklist's "audit log captures every access
to tracking/watchlist/export endpoints."
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.evidence_export import EvidenceExport
from models.rbac import User
from schemas.evidence import EvidenceExportRequest, EvidenceExportResult
from security.rbac import require_permission
from services import evidence_export

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _clean_plate_query(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()


@router.post("/export", response_model=EvidenceExportResult)
async def create_export(
    payload: EvidenceExportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("evidence:export", audit_on_success=True)),
) -> EvidenceExportResult:
    record = await evidence_export.build_export(
        db,
        user,
        _clean_plate_query(payload.plate_text),
        from_ts=payload.from_ts,
        to_ts=payload.to_ts,
    )
    return EvidenceExportResult(
        export_id=record.id,
        plate_text=record.plate_text,
        event_count=len(record.event_ids),
        sha256=record.sha256,
        exported_at=record.exported_at,
        download_url=f"/api/evidence/{record.id}/download",
    )


@router.get("/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_permission("evidence:export", resource_id_param="export_id", audit_on_success=True)
    ),
) -> FileResponse:
    record = (
        await db.execute(select(EvidenceExport).where(EvidenceExport.id == export_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Export not found.", "code": "not_found"},
        )

    file_path = Path(record.file_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"detail": "Export file no longer exists on disk.", "code": "export_expired"},
        )

    return FileResponse(
        path=file_path,
        media_type="application/zip",
        filename=f"sentinelgrid-evidence-{record.plate_text}-{export_id}.zip",
    )
