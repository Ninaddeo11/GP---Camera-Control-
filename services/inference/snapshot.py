"""Saves a JPEG snapshot for a published plate event, so Phase 9's
evidentiary export has photographic evidence to attach to each plate read
— path convention matches services/api's expectations
(`SNAPSHOT_DIR/{camera_id}/{YYYYMMDD}/{plate}_{pts_ms}.jpg`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

import config

log = logging.getLogger("inference.snapshot")


def save(camera_id: str, plate_text: str, frame_pts_ms: float, image: np.ndarray) -> str:
    date_dir = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = Path(config.SNAPSHOT_DIR) / camera_id / date_dir
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{plate_text}_{int(frame_pts_ms)}.jpg"
        cv2.imwrite(str(out_path), image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return str(out_path)
    except OSError:
        log.exception("Failed to save snapshot for camera=%s plate=%s", camera_id, plate_text)
        return ""


def save_track_evidence(
    camera_id: str, track_id: int, vehicle_image: np.ndarray | None, plate_image: np.ndarray | None
) -> tuple[str, str]:
    """Saves at most two images for one finalized track (track_state.py:
    FinalizedTrack) — the "best_vehicle_frame.jpg"/"best_plate_crop.jpg"
    pair from brief section 18, distinct from save() above (which fires
    once per *published* per-frame plate read, not once per finalized
    track). Returns (vehicle_path, plate_path); either is "" if that image
    wasn't available or the write failed, matching save()'s own "empty
    string means no evidence, not an exception" convention so callers
    never need a try/except around this.
    """
    date_dir = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = Path(config.SNAPSHOT_DIR) / camera_id / date_dir / "events"

    vehicle_path = ""
    plate_path = ""
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        if config.EVIDENCE_SAVE_BEST_VEHICLE_FRAME and vehicle_image is not None and vehicle_image.size > 0:
            path = out_dir / f"track{track_id}_vehicle.jpg"
            cv2.imwrite(str(path), vehicle_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            vehicle_path = str(path)
        if config.EVIDENCE_SAVE_BEST_PLATE_CROP and plate_image is not None and plate_image.size > 0:
            path = out_dir / f"track{track_id}_plate.jpg"
            cv2.imwrite(str(path), plate_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            plate_path = str(path)
    except OSError:
        log.exception("Failed to save track evidence for camera=%s track=%s", camera_id, track_id)

    return vehicle_path, plate_path
