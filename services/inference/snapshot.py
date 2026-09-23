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
