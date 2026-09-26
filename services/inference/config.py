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

# -- Plate quality pipeline (multi-vehicle ANPR upgrade) --------------------------
# Laplacian-variance floor below which a plate crop is treated as too
# blurry to bother OCRing at all (see plate_quality.assess).
PLATE_QUALITY_MIN_SHARPNESS = _float("PLATE_QUALITY_MIN_SHARPNESS", 0.08)
# Raw Laplacian-variance value treated as "as sharp as this needs scoring
# for" — purely a normalization constant for the 0-1 sharpness score, not
# a hard cutoff.
PLATE_QUALITY_SHARPNESS_CEILING = _float("PLATE_QUALITY_SHARPNESS_CEILING", 400.0)
PLATE_QUALITY_SIZE_CEILING_MULTIPLIER = _float("PLATE_QUALITY_SIZE_CEILING_MULTIPLIER", 3.0)
PLATE_QUALITY_CONTRAST_CEILING = _float("PLATE_QUALITY_CONTRAST_CEILING", 60.0)
PLATE_QUALITY_ENABLE_CLAHE = os.environ.get("PLATE_QUALITY_ENABLE_CLAHE", "true").lower() == "true"
PLATE_QUALITY_ENABLE_SHARPEN = os.environ.get("PLATE_QUALITY_ENABLE_SHARPEN", "true").lower() == "true"
PLATE_QUALITY_ENABLE_DENOISE = os.environ.get("PLATE_QUALITY_ENABLE_DENOISE", "false").lower() == "true"
# Upscale small-but-usable crops before OCR; 1.0 disables upscaling.
PLATE_QUALITY_UPSCALE_MAX_FACTOR = _float("PLATE_QUALITY_UPSCALE_MAX_FACTOR", 2.0)

# -- Secondary OCR (multi-vehicle ANPR upgrade) -----------------------------------
# Only invoked when the primary (PaddleOCR) read's confidence falls in the
# uncertain band below this value — never run on every crop (brief section
# 10: "Do NOT run both OCR engines on every plate crop").
OCR_SECONDARY_TRIGGER_BELOW_CONFIDENCE = _float("OCR_SECONDARY_TRIGGER_BELOW_CONFIDENCE", 0.75)
OCR_SECONDARY_ENABLED = os.environ.get("OCR_SECONDARY_ENABLED", "true").lower() == "true"

# -- Temporal OCR fusion (multi-vehicle ANPR upgrade) -----------------------------
# Bounded per-track observation buffer — old reads age out automatically
# rather than being retained forever (brief section 12: "Do not store
# every OCR observation permanently").
TEMPORAL_FUSION_MAX_OBSERVATIONS = _int("TEMPORAL_FUSION_MAX_OBSERVATIONS", 20)
# 1 preserves today's behavior (a single confident read is enough to
# publish); raise this to require corroborating reads before a track's
# plate is considered fused/confirmed.
TEMPORAL_FUSION_MIN_OBSERVATIONS_FOR_PUBLISH = _int("TEMPORAL_FUSION_MIN_OBSERVATIONS_FOR_PUBLISH", 1)

# -- Track lifecycle (multi-vehicle ANPR upgrade) ---------------------------------
# Consecutive frames a previously-confirmed track can be absent from
# ByteTrack's output before this service finalizes it as LOST — absorbs
# normal single-frame tracking flicker without prematurely closing out a
# vehicle that's still in view.
TRACK_LOST_GRACE_FRAMES = _int("TRACK_LOST_GRACE_FRAMES", 10)

# -- Vehicle classification enrichment (multi-vehicle ANPR upgrade) --------------
# No fine-tuned manufacturer/model classifier ships in this repo — see
# vehicle_classifier.py's module docstring. These paths follow the exact
# same "check for the file, disable cleanly if absent" convention as
# PLATE_MODEL_PATH above.
ENABLE_VEHICLE_CLASSIFICATION = os.environ.get("ENABLE_VEHICLE_CLASSIFICATION", "true").lower() == "true"
MANUFACTURER_MODEL_PATH = os.environ.get("MANUFACTURER_MODEL_PATH", "models/manufacturer-classifier.pt")
VEHICLE_MODEL_CLASSIFIER_PATH = os.environ.get("VEHICLE_MODEL_CLASSIFIER_PATH", "models/vehicle-model-classifier.pt")
MAKEMODEL_VLM_PATH = os.environ.get("MAKEMODEL_VLM_PATH", "models/makemodel-vlm-450m")
CLASSIFIER_HIGH_CONFIDENCE_THRESHOLD = _float("CLASSIFIER_HIGH_CONFIDENCE_THRESHOLD", 0.85)
CLASSIFIER_PROBABLE_CONFIDENCE_THRESHOLD = _float("CLASSIFIER_PROBABLE_CONFIDENCE_THRESHOLD", 0.60)
# Classification only runs on a track's single best-quality vehicle crop
# (updated as better frames arrive), never every frame — brief section 16:
# "Manufacturer: 1-3 best vehicle crops".
CLASSIFICATION_MIN_FRAMES_BEFORE_ATTEMPT = _int("CLASSIFICATION_MIN_FRAMES_BEFORE_ATTEMPT", 3)

# -- Redis / event bus --------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
REDIS_STREAM_DETECTIONS = os.environ.get("REDIS_STREAM_DETECTIONS", "detections")
REDIS_STREAM_PLATE_EVENTS = os.environ.get("REDIS_STREAM_PLATE_EVENTS", "plate_events")
REDIS_STREAM_VEHICLE_EVENTS = os.environ.get("REDIS_STREAM_VEHICLE_EVENTS", "vehicle_events")
REDIS_STREAM_CAMERA_HEALTH = os.environ.get("REDIS_STREAM_CAMERA_HEALTH", "camera_health")
REDIS_STREAM_MAXLEN = _int("REDIS_STREAM_MAXLEN", 500_000)

# -- Evidence storage (multi-vehicle ANPR upgrade) --------------------------------
EVIDENCE_SAVE_BEST_VEHICLE_FRAME = os.environ.get("EVIDENCE_SAVE_BEST_VEHICLE_FRAME", "true").lower() == "true"
EVIDENCE_SAVE_BEST_PLATE_CROP = os.environ.get("EVIDENCE_SAVE_BEST_PLATE_CROP", "true").lower() == "true"

# -- Misc --------------------------------------------------------------------------
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/data/snapshots")
METRICS_PORT = _int("INFERENCE_METRICS_PORT", 9090)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

VEHICLE_CLASS_NAMES = {"car", "truck", "bus", "motorcycle"}
PERSON_CLASS_NAME = "person"
