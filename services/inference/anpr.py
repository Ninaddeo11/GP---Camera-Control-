"""ANPR orchestration: vehicle crop -> plate localization -> quality gate
-> enhancement -> OCR (primary, +secondary when uncertain) -> normalization
-> PlateRead. Ties together plate_detector.py, plate_quality.py,
ocr_engine.py, ocr_fallback.py, and plate_normalizer.py; also owns
per-track deduplication so a stationary or slow-moving vehicle doesn't
flood the event stream with the same read every frame (see PlateDedupState).

This module still returns one PlateRead per call — it has no notion of a
track or of history across frames. Multi-frame temporal fusion lives in
temporal_fusion.py/track_state.py, one layer up (pipeline.py), by design:
this keeps AnprEngine a stateless, easily-testable "one crop in, one read
out" function, and keeps all track-keyed state in exactly one place.
"""

from __future__ import annotations

import logging

import numpy as np

import config
import plate_normalizer
import plate_quality
from events import PlateRead
from ocr_engine import OCREngine
from ocr_fallback import EasyOcrEngine
from plate_detector import PlateDetector

log = logging.getLogger("inference.anpr")


class AnprEngine:
    def __init__(self) -> None:
        self.plate_detector = PlateDetector()
        self.ocr_engine = OCREngine()
        self.secondary_ocr = EasyOcrEngine() if config.OCR_SECONDARY_ENABLED else None
        self.available = self.plate_detector.available and self.ocr_engine.available
        if not self.available:
            log.warning(
                "ANPR is disabled this run (plate_detector.available=%s, "
                "ocr_engine.available=%s) — see each module's log line above "
                "for why. Vehicle detection and tracking are unaffected.",
                self.plate_detector.available,
                self.ocr_engine.available,
            )
        if self.secondary_ocr is not None and not self.secondary_ocr.available:
            log.info("Secondary OCR engine (EasyOCR) unavailable — ANPR will run PaddleOCR only")

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

        quality = plate_quality.assess(plate_crop)
        if not quality.usable:
            return None
        enhanced_crop = plate_quality.enhance(plate_crop)

        # Primary engine always runs; secondary only when primary is
        # missing or uncertain — see plate_quality/ocr_fallback docstrings
        # for why running both unconditionally would waste compute.
        candidates: list[tuple[str, float, str]] = []
        primary = self.ocr_engine.read(enhanced_crop)
        if primary is not None:
            candidates.append((primary[0], primary[1], "paddleocr"))

        primary_confidence = primary[1] if primary is not None else 0.0
        needs_secondary = primary is None or primary_confidence < config.OCR_SECONDARY_TRIGGER_BELOW_CONFIDENCE
        if needs_secondary and self.secondary_ocr is not None and self.secondary_ocr.available:
            secondary = self.secondary_ocr.read(enhanced_crop)
            if secondary is not None:
                candidates.append((secondary[0], secondary[1], "easyocr"))

        if not candidates:
            return None

        best: tuple[str, str, float, float, str] | None = None  # (plate_text, region, combined_confidence, ocr_confidence, engine)
        for raw_text, ocr_confidence, engine in candidates:
            normalized = plate_normalizer.normalize(raw_text)
            if normalized is None:
                continue
            plate_text, region = normalized
            combined_confidence = detector_confidence * ocr_confidence
            if best is None or combined_confidence > best[2]:
                best = (plate_text, region, combined_confidence, ocr_confidence, engine)

        if best is None:
            return None
        plate_text, region, combined_confidence, ocr_confidence, engine = best
        if combined_confidence < config.ANPR_OCR_MIN_CONFIDENCE:
            return None

        return PlateRead(
            plate_text=plate_text,
            confidence=combined_confidence,
            region=region,
            detector_confidence=detector_confidence,
            ocr_confidence=ocr_confidence,
            quality_score=quality.overall,
            engine=engine,
        )
