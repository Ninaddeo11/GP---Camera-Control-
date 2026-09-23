import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogEntryOut(BaseModel):
    id: uuid.UUID
    ts: datetime
    username: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    reason: str
    ip_address: str
    request_path: str

    model_config = {"from_attributes": True}


class AuditChainVerification(BaseModel):
    intact: bool
    row_count: int
