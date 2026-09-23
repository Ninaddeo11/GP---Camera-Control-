"""YOLO11 vehicle + person detector.

One model instance is loaded once and shared read-only across every
camera's worker thread (see pipeline.py) — `.predict()` is stateless per
call, so this is safe without a lock; only tracker.py needs per-camera
state isolation.
"""

from __future__ import annotations

import logging

import numpy as np
from ultralytics import YOLO

import config
from events import Detection

log = logging.getLogger("inference.detector")


class Detector:
    def __init__(
        self,
        model_path: str = config.MODEL_PATH,
        device: str = config.DEVICE,
        vehicle_conf: float = config.YOLO_VEHICLE_CONF_THRESHOLD,
        person_conf: float = config.YOLO_PERSON_CONF_THRESHOLD,
    ) -> None:
        self.device = device
        self.half = device.startswith("cuda")  # FP16 on GPU, full precision on CPU
        self.vehicle_conf = vehicle_conf
        self.person_conf = person_conf

        log.info("Loading YOLO model %s on device=%s half=%s", model_path, device, self.half)
        self.model = YOLO(model_path)
        self.model.to(device)
        self.class_names: dict[int, str] = self.model.names

        # Only classes we ever act on are requested from the model, so
        # irrelevant COCO classes (chair, dog, ...) never reach downstream
        # tracking/ANPR work.
        self._wanted_class_ids = [
            cls_id
            for cls_id, name in self.class_names.items()
            if name in config.VEHICLE_CLASS_NAMES or name == config.PERSON_CLASS_NAME
        ]

    def predict(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.predict(
            frame,
            device=self.device,
            half=self.half,
            classes=self._wanted_class_ids,
            verbose=False,
        )[0]

        detections: list[Detection] = []
        if results.boxes is None:
            return detections

        for box in results.boxes:
            cls_id = int(box.cls[0])
            name = self.class_names[cls_id]
            confidence = float(box.conf[0])

            threshold = self.person_conf if name == config.PERSON_CLASS_NAME else self.vehicle_conf
            if confidence < threshold:
                continue

            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            detections.append(
                Detection(
                    bbox_xyxy=(x1, y1, x2, y2),
                    class_name=name,
                    confidence=confidence,
                )
            )

        return detections
