"""Prometheus metrics, exposed on :9090/metrics (see config.METRICS_PORT)."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

FRAMES_PROCESSED = Counter(
    "sentinelgrid_frames_processed_total",
    "Frames successfully decoded and run through detection",
    ["camera_id"],
)
DETECTIONS_TOTAL = Counter(
    "sentinelgrid_detections_total",
    "Raw YOLO detections produced (before tracking)",
    ["camera_id", "class_name"],
)
TRACKS_ACTIVE = Gauge(
    "sentinelgrid_tracks_active",
    "Currently active track IDs per camera",
    ["camera_id"],
)
PLATES_READ_TOTAL = Counter(
    "sentinelgrid_plates_read_total",
    "Plate reads published (post-dedup, above confidence threshold)",
    ["camera_id"],
)
ANPR_ATTEMPTS_TOTAL = Counter(
    "sentinelgrid_anpr_attempts_total",
    "Vehicle crops ANPR was attempted on (before any confidence gating)",
    ["camera_id"],
)
INFERENCE_LATENCY_SECONDS = Histogram(
    "sentinelgrid_inference_latency_seconds",
    "Detector + tracker wall-clock latency per processed frame",
    ["camera_id"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0),
)
CAMERA_DISCONNECTS = Counter(
    "sentinelgrid_camera_disconnects_total",
    "Times a camera's frame source transitioned to disconnected",
    ["camera_id"],
)
RECONNECT_ATTEMPTS = Counter(
    "sentinelgrid_inference_reconnect_attempts_total",
    "Reconnect attempts made per camera by this inference worker",
    ["camera_id"],
)
SCENE_DISCONTINUITIES = Counter(
    "sentinelgrid_scene_discontinuities_total",
    "PTS-detected scene discontinuities (e.g. looping demo feed restarts)",
    ["camera_id"],
)
ACTIVE_CAMERAS = Gauge(
    "sentinelgrid_inference_active_cameras",
    "Number of cameras this inference worker is currently processing",
)
