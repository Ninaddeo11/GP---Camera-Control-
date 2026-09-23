import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistEntryCreate(BaseModel):
    plate_text: str = Field(min_length=4, max_length=16)
    reason: str = ""
    priority: str = "medium"


class WatchlistEntryOut(BaseModel):
    id: uuid.UUID
    plate_text: str
    reason: str
    priority: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistMatchOut(BaseModel):
    id: uuid.UUID
    watchlist_id: uuid.UUID
    watchlist_plate_text: str
    camera_id: str
    camera_name: str
    matched_plate_text: str
    match_score: float
    confidence: float
    priority: str
    reason: str
    wall_ts: datetime
    snapshot_url: str | None
    acknowledged: bool
    acknowledged_by_username: str | None
    acknowledged_at: datetime | None
