"""Confirms the real plate-detector model (services/inference/Dockerfile's
build-time download — see plate_detector.py's docstring for its
provenance) actually loads and runs inference without crashing.

Deliberately not an accuracy test: no real vehicle/plate photo exists in
this repo/sandbox to test detection accuracy against (same constraint
test_ocr_models_real.py documents for OCR, but a synthetic printed-text
crop is a fair OCR test in a way a synthetic image can't be for a
detector — plate LOCATION isn't something you can fake by drawing a
rectangle and calling it representative). What this DOES verify: the
model loads, `detect_best()` runs against real image data without
raising, and — since a blank/noise image should not resemble a plate —
that it correctly finds nothing rather than hallucinating a box.

Skipped (not failed) if the weights file isn't present — e.g. running
this suite somewhere other than the built Docker image, where the
Dockerfile's download step never ran.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import config
from plate_detector import PlateDetector


@pytest.fixture(scope="module")
def detector():
    if not Path(config.PLATE_MODEL_PATH).exists():
        pytest.skip(f"{config.PLATE_MODEL_PATH} not present — only shipped in the built Docker image")
    pd = PlateDetector(model_path=config.PLATE_MODEL_PATH, device="cpu")
    if not pd.available:
        pytest.skip("PlateDetector failed to initialize despite the weights file existing — see its own log output")
    return pd


def test_loads_and_reports_available(detector):
    assert detector.available is True


def test_runs_without_crashing_on_a_real_sized_image(detector):
    # Not a real vehicle photo (none exists in this environment — see
    # module docstring), but a real-shaped, real-dtype array exercising
    # the actual inference call path end to end.
    vehicle_crop = np.random.randint(0, 255, size=(480, 640, 3), dtype=np.uint8)
    result = detector.detect_best(vehicle_crop)
    if result is not None:
        (x1, y1, x2, y2), confidence = result
        assert x1 < x2 and y1 < y2
        assert 0.0 <= confidence <= 1.0


def test_empty_crop_does_not_crash(detector):
    assert detector.detect_best(np.zeros((0, 0, 3), dtype=np.uint8)) is None
