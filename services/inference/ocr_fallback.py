"""Secondary OCR engine (EasyOCR), used only when the primary engine
(ocr_engine.py's PaddleOCR-based OCREngine) reads a plate with low
confidence — per the brief: "Do NOT run both OCR engines on every plate
crop." anpr.py decides when to invoke this; this module only implements
the read() call itself, in the same (text, confidence) shape as
OCREngine.read() so anpr.py can treat both engines interchangeably.

Same CPU-only rationale as ocr_engine.py: EasyOCR's GPU path uses its own
torch CUDA context, which could double up with (rather than cleanly share)
the CUDA context YOLO11 already holds in this process. EasyOCR reuses the
torch install already present for YOLO11 (see requirements.txt), so this
only adds the `easyocr` package itself, not a second deep-learning
framework.
"""

from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger("inference.ocr_fallback")


class EasyOcrEngine:
    def __init__(self) -> None:
        self.available = False
        self._reader = None
        try:
            import easyocr

            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            self.available = True
            log.info("EasyOCR fallback engine initialized (CPU)")
        except Exception:
            log.exception("Failed to initialize EasyOCR — secondary OCR engine disabled")

    def read(self, plate_crop: np.ndarray) -> tuple[str, float] | None:
        """Returns (raw_text, confidence) for the plate crop, concatenating
        detected lines top-to-bottom and taking the minimum confidence
        across lines — mirrors OCREngine.read()'s exact convention so
        anpr.py can compare/merge results from either engine uniformly.
        """
        if not self.available or plate_crop.size == 0:
            return None

        try:
            # detail=1 returns (box, text, confidence) tuples; paragraph=False
            # keeps line-level granularity, matching PaddleOCR's line-based
            # output that OCREngine._parse_result already assumes.
            results = self._reader.readtext(plate_crop, detail=1, paragraph=False)
        except Exception:
            log.exception("EasyOCR inference failed on a plate crop")
            return None

        if not results:
            return None

        entries = []  # (top_y, text, conf)
        for box_points, text, conf in results:
            if not text:
                continue
            top_y = min(p[1] for p in box_points)
            entries.append((top_y, text, float(conf)))

        if not entries:
            return None

        entries.sort(key=lambda e: e[0])
        combined_text = "".join(text for _, text, _ in entries)
        min_conf = min(conf for _, _, conf in entries)
        return combined_text, min_conf
