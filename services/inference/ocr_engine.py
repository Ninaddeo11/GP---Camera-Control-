"""OCR on a localized plate crop, using PaddleOCR — per the project brief
("a modern OCR (PaddleOCR or a fine-tuned CRNN)") rather than openalpr's
bundled OCR. Runs on CPU deliberately: PaddleOCR's GPU build
(`paddlepaddle-gpu`) targets its own CUDA/cuDNN version, which risks
conflicting with the PyTorch CUDA build already installed for YOLO11 in
the same container (see Dockerfile) — plate crops are small, so CPU OCR is
fast enough per-read without that risk. If OCR throughput becomes the
bottleneck at higher camera counts, moving this to its own CPU-only sidecar
container is a cleaner fix than sharing a GPU runtime with two different
frameworks' CUDA builds.

Version-dependent risk: PaddleOCR's `.ocr()` return shape has changed
across versions (nesting depth, whether angle-classification results are
included). This is pinned to `paddleocr==2.7.3` (requirements.txt) and
`_parse_result` is defensive — a shape it doesn't recognize is logged once
and treated as "no read" rather than crashing the camera worker thread.
"""

from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger("inference.ocr_engine")


class OCREngine:
    def __init__(self) -> None:
        self.available = False
        self._ocr = None
        try:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(use_angle_cls=False, lang="en", use_gpu=False, show_log=False)
            self.available = True
            log.info("PaddleOCR engine initialized (CPU)")
        except Exception:
            log.exception("Failed to initialize PaddleOCR — ANPR text recognition disabled")

    def read(self, plate_crop: np.ndarray) -> tuple[str, float] | None:
        """Returns (raw_text, confidence) for the plate crop, concatenating
        multiple detected text lines top-to-bottom (two-line Indian plates
        commonly OCR as two separate lines), or None if nothing was read.
        Confidence is the minimum across lines — a plate is only as
        trustworthy as its worst-read line.
        """
        if not self.available or plate_crop.size == 0:
            return None

        try:
            raw = self._ocr.ocr(plate_crop, cls=False)
        except Exception:
            log.exception("PaddleOCR inference failed on a plate crop")
            return None

        return self._parse_result(raw)

    @staticmethod
    def _parse_result(raw) -> tuple[str, float] | None:
        # Expected shape: raw = [ [ [box_points, (text, conf)], ... ] ]
        # (one outer list per input image; we always pass exactly one).
        try:
            lines = raw[0] if raw else None
            if not lines:
                return None

            entries = []  # (top_y, text, conf)
            for box_points, (text, conf) in lines:
                if not text:
                    continue
                top_y = min(p[1] for p in box_points)
                entries.append((top_y, text, float(conf)))

            if not entries:
                return None

            entries.sort(key=lambda e: e[0])  # top-to-bottom reading order
            combined_text = "".join(text for _, text, _ in entries)
            min_conf = min(conf for _, _, conf in entries)
            return combined_text, min_conf
        except Exception:
            log.exception("Unrecognized PaddleOCR result shape — treating as no read")
            return None
