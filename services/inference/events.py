"""Shared data model between detector.py, tracker.py, anpr.py, and
event_publisher.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """One raw YOLO detection in a single frame, before tracking."""

    bbox_xyxy: tuple[float, float, float, float]
    class_name: str
    confidence: float


@dataclass(frozen=True)
class TrackedObject:
    """A detection with a stable per-camera track_id assigned by ByteTrack."""

    track_id: int
    camera_id: str
    bbox_xyxy: tuple[float, float, float, float]
    class_name: str
    confidence: float
    frame_pts_ms: float
    wall_ts_ms: float


@dataclass(frozen=True)
class PlateRead:
    """One normalized plate read from anpr.py, not yet attached to a track.
    `confidence` is `detector_confidence * ocr_confidence` (unchanged from
    before this upgrade — anpr.py's ANPR_OCR_MIN_CONFIDENCE gate and
    pipeline.py's pre-upgrade dedup logic both used this combined value).
    `detector_confidence`/`ocr_confidence`/`quality_score`/`engine` are
    additionally exposed, consumed only within this service (by
    track_state.py, to build a temporal_fusion.PlateObservation with each
    signal weighted independently) — none of them cross the Redis Streams
    boundary, so adding them here doesn't touch the wire format
    services/api already consumes.
    """

    plate_text: str
    confidence: float
    region: str  # 2-letter Indian state/UT RTO code, "BH" for Bharat-series, or "" if unrecognized
    detector_confidence: float = 1.0
    ocr_confidence: float = 1.0
    quality_score: float = 1.0
    engine: str = "paddleocr"


@dataclass(frozen=True)
class PlateEvent:
    """A PlateRead attached to a specific track, ready to publish."""

    camera_id: str
    track_id: int
    plate_text: str
    confidence: float
    region: str
    vehicle_class: str
    bbox_xyxy: tuple[float, float, float, float]
    frame_pts_ms: float
    wall_ts_ms: float
    snapshot_path: str


@dataclass(frozen=True)
class VehicleEvent:
    """One finalized track (track_state.py: FinalizedTrack), ready to
    publish as a single consolidated event — the higher-level counterpart
    to the many per-frame PlateEvents a track may have produced along the
    way. Fields are deliberately all-optional-friendly (empty string /
    0.0 / False) rather than Optional[...] so this serializes into flat
    Redis Stream string fields the same way PlateEvent already does,
    without a None-handling special case per field.
    """

    camera_id: str
    track_id: int
    first_seen_wall_ts_ms: float
    last_seen_wall_ts_ms: float

    vehicle_type: str
    vehicle_type_observations: int

    plate_text: str
    plate_confidence: float
    plate_region: str
    plate_valid: bool
    plate_observations: int
    plate_agreement: float

    manufacturer: str
    manufacturer_confidence: float
    model: str
    model_confidence: float

    best_vehicle_image_path: str
    best_plate_image_path: str
