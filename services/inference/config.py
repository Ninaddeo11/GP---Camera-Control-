"""Centralized settings for the inference service, read from environment
variables (see .env.example). Nothing else in this service reads
os.environ directly.
"""

from __future__ import annotations

import os


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


# -- Camera source -------------------------------------------------------------
INGEST_API_URL = os.environ.get("INGEST_API_URL", "http://catalogue:9000/api/ingest")
INGEST_POLL_INTERVAL_SECONDS = _int("INGEST_POLL_INTERVAL_SECONDS", 60)
GO2RTC_RTSP_HOST = os.environ.get("GO2RTC_RTSP_HOST", "go2rtc")
GO2RTC_RTSP_PORT = _int("GO2RTC_RTSP_PORT", 8554)

# -- Model / device --------------------------------------------------------------
DEVICE = os.environ.get("SENTINELGRID_DEVICE", "cpu")  # "cuda:0" or "cpu"
MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "models/yolo11s.pt")
TRACKER_CONFIG = os.environ.get("BYTETRACK_CONFIG", "bytetrack.yaml")

YOLO_VEHICLE_CONF_THRESHOLD = _float("YOLO_VEHICLE_CONF_THRESHOLD", 0.45)
YOLO_PERSON_CONF_THRESHOLD = _float("YOLO_PERSON_CONF_THRESHOLD", 0.50)

# -- Frame pacing -----------------------------------------------------------------
TARGET_FPS_PER_CAMERA = _float("TARGET_FPS_PER_CAMERA", 5.0)
MIN_FPS_PER_CAMERA = _float("MIN_FPS_PER_CAMERA", 2.0)

# -- Reconnect / fault tolerance --------------------------------------------------
RECONNECT_BACKOFF_INITIAL_SECONDS = _float("RECONNECT_BACKOFF_INITIAL_SECONDS", 2.0)
RECONNECT_BACKOFF_MAX_SECONDS = _float("RECONNECT_BACKOFF_MAX_SECONDS", 30.0)
# Consecutive failed frame reads tolerated before treating the camera as
# disconnected — a single bad/missing frame near stream join is normal
# (e.g. no IDR yet), not a reason to reconnect.
MAX_CONSECUTIVE_READ_FAILURES = _int("MAX_CONSECUTIVE_READ_FAILURES", 15)

# A backward or anomalously large PTS jump this big (ms) is treated as a
# scene discontinuity (e.g. a looping demo feed cutting back to its start),
# not a normal inter-frame gap.
DISCONTINUITY_GAP_MS = _float("DISCONTINUITY_GAP_MS", 4000.0)

# -- ANPR (Phase 5) ----------------------------------------------------------------
# No fine-tuned Indian-plate model ships in this repo (that needs a labeled
# training run this sandbox can't produce — see README.md "ANPR model gap").
# PlateDetector checks for this file at startup and disables ANPR with a
# clear log message if it's missing, rather than crashing the service —
# Phase 4 detection/tracking keeps working either way.
PLATE_MODEL_PATH = os.environ.get("PLATE_MODEL_PATH", "models/yolo11n-plate.pt")
YOLO_PLATE_CONF_THRESHOLD = _float("YOLO_PLATE_CONF_THRESHOLD", 0.50)
ANPR_OCR_MIN_CONFIDENCE = _float("ANPR_OCR_MIN_CONFIDENCE", 0.65)
ANPR_MIN_CROP_WIDTH = _int("ANPR_MIN_CROP_WIDTH", 80)
ANPR_MIN_CROP_HEIGHT = _int("ANPR_MIN_CROP_HEIGHT", 30)
# Once a track has a read at/above this confidence, ANPR stops re-running
# for that track — no point spending GPU/CPU time re-reading a plate we
# already read confidently.
ANPR_SKIP_RERUN_ABOVE_CONFIDENCE = _float("ANPR_SKIP_RERUN_ABOVE_CONFIDENCE", 0.90)
# A later read for the same track only gets (re-)published if it beats the
# previously published confidence by at least this much — otherwise it's a
# near-duplicate of what's already in the stream.
ANPR_REPUBLISH_MARGIN = _float("ANPR_REPUBLISH_MARGIN", 0.05)

# -- Redis / event bus --------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
REDIS_STREAM_DETECTIONS = os.environ.get("REDIS_STREAM_DETECTIONS", "detections")
REDIS_STREAM_PLATE_EVENTS = os.environ.get("REDIS_STREAM_PLATE_EVENTS", "plate_events")
REDIS_STREAM_CAMERA_HEALTH = os.environ.get("REDIS_STREAM_CAMERA_HEALTH", "camera_health")
REDIS_STREAM_MAXLEN = _int("REDIS_STREAM_MAXLEN", 500_000)

# -- Misc --------------------------------------------------------------------------
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/data/snapshots")
METRICS_PORT = _int("INFERENCE_METRICS_PORT", 9090)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

VEHICLE_CLASS_NAMES = {"car", "truck", "bus", "motorcycle"}
PERSON_CLASS_NAME = "person"
