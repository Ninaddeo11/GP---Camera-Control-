"""License-plate localization: a YOLO model run on the cropped vehicle ROI
(not the full frame) to find where the plate is, before OCR ever runs —
per the project brief, this replaces openalpr's detector, which the brief
calls out as dated for Indian plates.

No Indian-plate-*fine-tuned* model ships in this repo — that needs a
labeled Indian-plate dataset and a training run, neither of which this
environment can produce, and guessing at a public model URL and baking in
a download that might silently be wrong risked shipping something worse
than nothing.

What DOES ship (see services/inference/Dockerfile) is a real, verified
one: yasirfaizahmed/license-plate-object-detection on Hugging Face
(Apache 2.0, downloaded at image build time to
models/plate-detector-generic.pt), a YOLOv8 model fine-tuned on the
public "keremberke/license-plate-object-detection" Roboflow dataset —
confirmed by loading it and checking its task/class head before wiring it
in here, not taken on faith. That dataset is general-purpose, not
India-specific, so treat its own reported accuracy (mAP@50 in the high
0.9x range on its own test split) as optimistic for Indian plates
specifically: plate *localization* (finding a rectangular, high-contrast
region) tends to transfer across regions better than OCR does, since it's
a more generic visual task than reading region-specific fonts/layouts,
but that transfer has NOT been empirically verified against real Indian
CCTV footage in this environment — there is none available to test
against. Swap PLATE_MODEL_PATH for a real Indian-plate-fine-tuned model
the moment one exists; nothing else needs to change.

This class checks for a local weights file at startup and disables
itself with a clear log message if it's missing (e.g. the Dockerfile's
download failed) — same graceful-degradation behavior as before this
model existed. Detection/tracking (Phase 4) keeps working either way.
See README.md "ANPR model gap" for more.
"""

from __future__ import annotations

import logging

import numpy as np

import config
from yolo_loader import load_yolo_model

log = logging.getLogger("inference.plate_detector")


class PlateDetector:
    def __init__(self, model_path: str = config.PLATE_MODEL_PATH, device: str = config.DEVICE) -> None:
        self.available = False
        self.device = device
        self._model = None

        try:
            self._model = load_yolo_model(model_path, device)
            self.available = True
            log.info("Plate detector loaded from %s on device=%s", model_path, device)
        except FileNotFoundError:
            log.warning(
                "Plate detector model not found at %s — ANPR is disabled until a "
                "fine-tuned plate-detection model is provided (see README.md "
                "'ANPR model gap'). Vehicle detection and tracking are unaffected.",
                model_path,
            )
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
