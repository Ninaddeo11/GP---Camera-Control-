"""ANPR orchestration: vehicle crop -> plate localization -> OCR ->
normalization -> PlateRead. Ties together plate_detector.py, ocr_engine.py,
and plate_normalizer.py; also owns per-track deduplication so a stationary
or slow-moving vehicle doesn't flood the event stream with the same read
every frame (see PlateDedupState).
"""

from __future__ import annotations

import logging

import numpy as np

import config
import plate_normalizer
from events import PlateRead
from ocr_engine import OCREngine
from plate_detector import PlateDetector

log = logging.getLogger("inference.anpr")


class AnprEngine:
    def __init__(self) -> None:
        self.plate_detector = PlateDetector()
        self.ocr_engine = OCREngine()
        self.available = self.plate_detector.available and self.ocr_engine.available
        if not self.available:
            log.warning(
                "ANPR is disabled this run (plate_detector.available=%s, "
                "ocr_engine.available=%s) — see each module's log line above "
                "for why. Vehicle detection and tracking are unaffected.",
                self.plate_detector.available,
                self.ocr_engine.available,
            )

    def process(self, vehicle_crop: np.ndarray) -> PlateRead | None:
        if not self.available:
            return None

        h, w = vehicle_crop.shape[:2]
        if w < config.ANPR_MIN_CROP_WIDTH or h < config.ANPR_MIN_CROP_HEIGHT:
            return None

        plate_detection = self.plate_detector.detect_best(vehicle_crop)
        if plate_detection is None:
            return None
        (x1, y1, x2, y2), detector_confidence = plate_detection

        plate_crop = vehicle_crop[max(y1, 0) : y2, max(x1, 0) : x2]
        if plate_crop.size == 0:
            return None

        ocr_result = self.ocr_engine.read(plate_crop)
        if ocr_result is None:
            return None
        raw_text, ocr_confidence = ocr_result

        normalized = plate_normalizer.normalize(raw_text)
        if normalized is None:
            return None
        plate_text, region = normalized

        combined_confidence = detector_confidence * ocr_confidence
        if combined_confidence < config.ANPR_OCR_MIN_CONFIDENCE:
            return None

        return PlateRead(plate_text=plate_text, confidence=combined_confidence, region=region)


class PlateDedupState:
    """Per (camera_id, track_id) best-published-confidence, so pipeline.py
    can skip re-running ANPR once a track already has a confident read, and
    skip re-publishing a read that doesn't meaningfully improve on the last
    one. Cleared per-camera whenever that camera's tracker resets (track
    IDs are no longer meaningful after a reconnect or scene discontinuity).
    """

    def __init__(self) -> None:
        self._best: dict[tuple[str, int], float] = {}

    def should_skip_rerun(self, camera_id: str, track_id: int) -> bool:
        best = self._best.get((camera_id, track_id))
        return best is not None and best >= config.ANPR_SKIP_RERUN_ABOVE_CONFIDENCE

    def should_publish(self, camera_id: str, track_id: int, confidence: float) -> bool:
        best = self._best.get((camera_id, track_id))
        return best is None or confidence >= best + config.ANPR_REPUBLISH_MARGIN

    def record(self, camera_id: str, track_id: int, confidence: float) -> None:
        key = (camera_id, track_id)
        self._best[key] = max(confidence, self._best.get(key, 0.0))

    def clear_camera(self, camera_id: str) -> None:
        for key in [k for k in self._best if k[0] == camera_id]:
            del self._best[key]
