import uuid
from datetime import datetime

from pydantic import BaseModel


class EvidenceExportRequest(BaseModel):
    plate_text: str
    from_ts: datetime | None = None
    to_ts: datetime | None = None


class EvidenceExportResult(BaseModel):
    export_id: uuid.UUID
    plate_text: str
    event_count: int
    sha256: str
    exported_at: datetime
    download_url: str
