import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CameraOut(BaseModel):
    id: uuid.UUID
    camera_id: str
    name: str
    department: str
    jurisdiction_id: uuid.UUID | None
    lat: float | None
    lon: float | None
    protocol: str
    resolution: str
    codec: str
    fps: float
    status: str
    is_active: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class CameraCreate(BaseModel):
    camera_id: str
    name: str
    department: str = ""
    jurisdiction_id: uuid.UUID | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    protocol: str = ""
    resolution: str = ""
    codec: str = ""
    fps: float = 0.0


class CameraUpdate(BaseModel):
    name: str | None = None
    department: str | None = None
    jurisdiction_id: uuid.UUID | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None


class CameraSyncResult(BaseModel):
    added: int
    updated: int
    unassigned_jurisdiction: list[str]
