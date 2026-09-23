import uuid
from datetime import datetime

from pydantic import BaseModel


class CameraStop(BaseModel):
    camera_id: str
    camera_name: str
    lat: float | None
    lon: float | None
    first_seen: datetime
    last_seen: datetime
    dwell_seconds: float
    confidence_avg: float
    snapshot_url: str | None
    inferred_speed_to_next_kmh: float | None


class TraversalResult(BaseModel):
    plate_text: str
    stops: list[CameraStop]
    omitted_out_of_jurisdiction_stops: int


class RouteFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict


class RouteGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: list[RouteFeature]


class RecentDetectionOut(BaseModel):
    id: uuid.UUID
    camera_id: str
    camera_name: str
    plate_text: str
    confidence: float
    vehicle_class: str
    wall_ts: datetime
    snapshot_url: str | None
