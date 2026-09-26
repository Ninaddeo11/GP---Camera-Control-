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


class VehicleEventOut(BaseModel):
    """One finalized vehicle track (multi-vehicle ANPR upgrade) —
    consolidated vehicle type/manufacturer/model plus the best fused plate
    read, distinct from RecentDetectionOut's per-publish plate_events rows.
    """

    id: uuid.UUID
    camera_id: str
    camera_name: str
    track_id: int
    last_seen: datetime

    vehicle_type: str
    plate_text: str
    plate_confidence: float
    plate_valid: bool
    manufacturer: str
    manufacturer_confidence: float
    model: str
    model_confidence: float

    vehicle_snapshot_url: str | None
    plate_snapshot_url: str | None
