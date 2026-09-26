"""Manufacturer and model recognition — enrichment on top of the plate
pipeline, never a dependency of it (see anpr.py, temporal_fusion.py: none
of that code imports this module). Vehicle *type* is not handled here; it
already comes for free from detector.py's YOLO class name
("car"/"truck"/"bus"/"motorcycle") and track_state.py's majority vote
across a track's frames, which is a real, working classifier already —
duplicating it with a second model would violate "don't introduce a
second implementation of the same subsystem".

No fine-tuned manufacturer/model classifier ships in this repo, for the
same reason plate_detector.py ships without weights (see that module's
docstring): training one needs a labeled Indian-vehicle dataset this
sandbox can't produce, and guessing at a public model URL to auto-download
risks silently loading the wrong thing. Both classifiers below follow
plate_detector.py's exact pattern: check for a local weights file at
startup, disable with a clear log line if it's missing, and produce None
(never a fabricated label) from classify() while disabled.

The MakeModel-VLM-450M adapter (config.MAKEMODEL_VLM_PATH) is a *third*,
independent fallback path for model recognition specifically — per the
brief, "a low-confidence VLM prediction must not override a high-
confidence result from another classifier" (see merge_with_priority).
It is never auto-downloaded from Hugging Face; like the other two models,
it only activates if a local copy is already present at the configured
path.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import numpy as np

import config

log = logging.getLogger("inference.vehicle_classifier")

ConfidenceTier = Literal["high", "probable", "unknown"]


def confidence_tier(confidence: float) -> ConfidenceTier:
    if confidence >= config.CLASSIFIER_HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if confidence >= config.CLASSIFIER_PROBABLE_CONFIDENCE_THRESHOLD:
        return "probable"
    return "unknown"


class ClassificationResult:
    __slots__ = ("label", "confidence", "tier", "source")

    def __init__(self, label: str, confidence: float, source: str) -> None:
        self.label = label
        self.confidence = confidence
        self.tier: ConfidenceTier = confidence_tier(confidence)
        self.source = source  # e.g. "manufacturer_classifier", "vlm"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"ClassificationResult(label={self.label!r}, confidence={self.confidence:.2f}, tier={self.tier}, source={self.source!r})"


class _YoloClassifier:
    """Shared loader for a YOLO-classification-head model — both
    manufacturer and model recognition are expected to ship as this kind
    of model (see README's model-management docs), so this base class
    exists only to avoid writing the same load/disable/predict scaffolding
    twice, not to add a second detector abstraction on top of detector.py.
    """

    def __init__(self, model_path: str, device: str, label_name: str) -> None:
        self.available = False
        self.device = device
        self._label_name = label_name
        self._model = None

        if not Path(model_path).exists():
            log.info(
                "%s classifier model not found at %s — this enrichment stage stays "
                "disabled (vehicles will report %s=Unknown) until a model is provided. "
                "Plate recognition and vehicle type are unaffected.",
                label_name,
                model_path,
                label_name.lower(),
            )
            return

        from ultralytics import YOLO  # local import: skip the load entirely when disabled

        try:
            self._model = YOLO(model_path)
            self._model.to(device)
            self.available = True
            log.info("%s classifier loaded from %s on device=%s", label_name, model_path, device)
        except Exception:
            log.exception("Failed to load %s classifier from %s — enrichment disabled", label_name, model_path)

    def classify(self, vehicle_crop: np.ndarray) -> ClassificationResult | None:
        if not self.available or vehicle_crop.size == 0:
            return None

        results = self._model.predict(vehicle_crop, device=self.device, verbose=False)[0]
        probs = getattr(results, "probs", None)
        if probs is None:
            return None

        top1_index = int(probs.top1)
        confidence = float(probs.top1conf)
        label = results.names.get(top1_index, "Unknown") if hasattr(results, "names") else "Unknown"
        return ClassificationResult(label=label, confidence=confidence, source=f"{self._label_name.lower()}_classifier")


class ManufacturerClassifier(_YoloClassifier):
    def __init__(self, model_path: str = config.MANUFACTURER_MODEL_PATH, device: str = config.DEVICE) -> None:
        super().__init__(model_path, device, label_name="Manufacturer")


class ModelClassifier(_YoloClassifier):
    """Model recognition — lower priority than manufacturer (section 15),
    and callers may choose to only run this on a crop that already has a
    manufacturer result, though this class itself has no such dependency.
    """

    def __init__(self, model_path: str = config.VEHICLE_MODEL_CLASSIFIER_PATH, device: str = config.DEVICE) -> None:
        super().__init__(model_path, device, label_name="Model")


class MakeModelVlmAdapter:
    """Interface for sanskar003/MakeModel-VLM-450M (or a compatible local
    VLM) as a secondary/fallback signal for model recognition — per the
    brief, "MakeModel-VLM-450M: secondary model/fallback/benchmark", never
    the primary path. Deliberately never downloads from Hugging Face:
    config.MAKEMODEL_VLM_PATH must already point at a local model
    directory, checked the same way as the other two classifiers.

    Real inference code (tokenizer/processor load, generate() call, output
    parsing) is intentionally not implemented here — with no local copy of
    the model available in this environment, writing that call now would
    be untested guesswork against a specific model's API. What's in place
    is everything around that call: the availability check, the
    classify() signature and return type callers already use, and
    merge_with_priority()'s confidence-arbitration rule — so dropping in
    the real generate()/parse step later is the only thing needed to
    activate this path, per the brief's "implement the model interface...
    so the actual model can be dropped in without redesigning the system."
    """

    def __init__(self, model_path: str = config.MAKEMODEL_VLM_PATH) -> None:
        self.available = False
        self._model_dir = Path(model_path)

        if not self._model_dir.exists():
            log.info(
                "MakeModel-VLM adapter: no local model directory at %s — VLM fallback "
                "for model recognition stays disabled. See vehicle_classifier.py "
                "MakeModelVlmAdapter docstring for what's required to activate it.",
                model_path,
            )
            return

        log.warning(
            "MakeModel-VLM adapter: a model directory exists at %s, but the actual "
            "load/generate call is not implemented yet (see class docstring) — "
            "treating as unavailable rather than guessing at its inference API.",
            model_path,
        )

    def classify(self, vehicle_crop: np.ndarray) -> ClassificationResult | None:
        if not self.available:
            return None
        raise NotImplementedError(  # pragma: no cover - unreachable while self.available is always False
            "MakeModelVlmAdapter.available should never be True until real "
            "inference code is added alongside a local model directory."
        )


def merge_with_priority(
    primary: ClassificationResult | None, fallback: ClassificationResult | None
) -> ClassificationResult | None:
    """Section 15/23's rule, made explicit and reusable: a fallback
    (e.g. VLM) result must never overwrite a reliable primary result. A
    fallback is only used when the primary is missing, or when the
    primary itself is not "high" confidence and the fallback is strictly
    more confident.
    """
    if primary is None:
        return fallback
    if fallback is None:
        return primary
    if primary.tier == "high":
        return primary
    return fallback if fallback.confidence > primary.confidence else primary
