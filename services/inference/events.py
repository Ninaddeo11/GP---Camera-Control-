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
    """One normalized plate read from anpr.py, not yet attached to a track."""

    plate_text: str
    confidence: float
    region: str  # 2-letter Indian state/UT RTO code, or "" if unrecognized


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
