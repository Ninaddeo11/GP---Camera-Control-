"""Shared fixtures for the inference service's test suite.

No real CCTV footage or trained model weights exist in this repo/sandbox
(see plate_detector.py, vehicle_classifier.py docstrings), so these tests
target the pure-Python/OpenCV logic layers that don't need either: plate
text validation, temporal fusion, quality scoring on synthetic images, and
track lifecycle bookkeeping. Anything that requires an actual YOLO/OCR
model producing real detections on real video is out of scope for this
suite — see docs/anpr-pipeline.md "Testing" for what's covered and what
still needs a real deployment to verify.
"""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def sharp_plate_crop() -> np.ndarray:
    """A high-contrast checkerboard — not a real plate image, but sharp
    edges and full-range contrast, which is exactly what plate_quality's
    Laplacian-variance/contrast scoring measures. Big enough to clear
    ANPR_MIN_CROP_WIDTH/HEIGHT.
    """
    crop = np.zeros((60, 160, 3), dtype=np.uint8)
    crop[::2, ::2] = 255
    crop[1::2, 1::2] = 255
    return crop


@pytest.fixture
def blurry_plate_crop(sharp_plate_crop: np.ndarray) -> np.ndarray:
    """The same pattern, heavily blurred — should score much lower on
    sharpness than sharp_plate_crop.
    """
    import cv2

    return cv2.GaussianBlur(sharp_plate_crop, (15, 15), sigmaX=8)


@pytest.fixture
def tiny_crop() -> np.ndarray:
    """Below ANPR_MIN_CROP_WIDTH/HEIGHT — should never be usable()."""
    return np.zeros((10, 20, 3), dtype=np.uint8)
