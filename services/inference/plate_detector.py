"""License-plate localization: a YOLO11 model fine-tuned specifically for
plate detection, run on the cropped vehicle ROI (not the full frame) — per
the project brief, this replaces openalpr's detector, which the brief
calls out as dated for Indian plates.

No fine-tuned model ships in this repo — training one needs a labeled
Indian-plate dataset and a training run, neither of which this environment
can produce. Rather than guess at a public model URL and bake in a
download that might silently be wrong or unavailable, this class checks
for a local weights file at startup and disables itself with a clear log
message if it's missing. Detection/tracking (Phase 4) keeps working either
way; ANPR (this phase) simply produces no plate reads until a model is
provided. See README.md "ANPR model gap" for how to add one.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

import config

log = logging.getLogger("inference.plate_detector")


class PlateDetector:
    def __init__(self, model_path: str = config.PLATE_MODEL_PATH, device: str = config.DEVICE) -> None:
        self.available = False
        self.device = device
        self._model = None

        if not Path(model_path).exists():
            log.warning(
                "Plate detector model not found at %s — ANPR is disabled until a "
                "fine-tuned plate-detection model is provided (see README.md "
                "'ANPR model gap'). Vehicle detection and tracking are unaffected.",
                model_path,
            )
            return

        from ultralytics import YOLO  # local import: skip the load entirely when disabled

        try:
            self._model = YOLO(model_path)
            self._model.to(device)
            self.available = True
            log.info("Plate detector loaded from %s on device=%s", model_path, device)
        except Exception:
            log.exception("Failed to load plate detector model from %s — ANPR disabled", model_path)

    def detect_best(self, vehicle_crop: np.ndarray) -> tuple[tuple[int, int, int, int], float] | None:
        """Returns the highest-confidence plate bbox (in vehicle_crop's own
        pixel coordinates) and its detection confidence, or None if the
        detector is unavailable or found nothing.
        """
        if not self.available or vehicle_crop.size == 0:
            return None

        results = self._model.predict(
            vehicle_crop,
            device=self.device,
            conf=config.YOLO_PLATE_CONF_THRESHOLD,
            verbose=False,
        )[0]
        if results.boxes is None or len(results.boxes) == 0:
            return None

        best_box = max(results.boxes, key=lambda b: float(b.conf[0]))
        x1, y1, x2, y2 = (int(v) for v in best_box.xyxy[0].tolist())
        return (x1, y1, x2, y2), float(best_box.conf[0])
