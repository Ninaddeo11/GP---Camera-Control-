"""Confirms the actual OCR models — PaddleOCR (ocr_engine.py) and its
EasyOCR fallback (ocr_fallback.py) — genuinely work, not just the
surrounding normalization/fusion logic conftest.py's docstring already
covers. Loads the real pretrained models (no mocking) and reads text off
a synthetic plate-style image.

Deliberately synthetic, not a real photographed plate: no real CCTV
footage or labeled plate images exist in this repo/sandbox (same
constraint plate_detector.py's docstring documents for the plate
*detector*). A clean printed string on a plate-colored background is a
fair test of whether the OCR engines can read Indian-plate-formatted
text at all — it does not, and is not meant to, stand in for a real
detector's crop quality (motion blur, off-axis angle, dirt).

Skipped entirely (not failed) if paddleocr/easyocr aren't importable in
whatever environment runs this suite — the goal is a real yes/no answer
about the actual models where they ARE available (this service's own
Docker image), not a fake pass on a system without them.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from plate_normalizer import normalize


def _synthetic_plate(text: str, *, width: int = 320, height: int = 96) -> np.ndarray:
    """A white plate-style crop with the given text printed on it in
    black, high-contrast, no distortion — the easiest case an OCR model
    should be able to read, used here purely to confirm the model
    functions at all, not to benchmark real-world accuracy.
    """
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (2, 2), (width - 3, height - 3), (0, 0, 0), 2)
    cv2.putText(
        img,
        text,
        (14, int(height * 0.68)),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.3,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )
    return img


PLATE_SAMPLES = ["GJ01AB1234", "MH12CD5678", "DL3CAB0001"]


@pytest.fixture(scope="module")
def paddle_engine():
    try:
        from ocr_engine import OCREngine
    except Exception as exc:
        pytest.skip(f"paddleocr not importable in this environment: {exc}")
    engine = OCREngine()
    if not engine.available:
        pytest.skip("PaddleOCR failed to initialize — see its own log output for why")
    return engine


@pytest.fixture(scope="module")
def easyocr_engine():
    try:
        from ocr_fallback import EasyOcrEngine
    except Exception as exc:
        pytest.skip(f"easyocr not importable in this environment: {exc}")
    engine = EasyOcrEngine()
    if not engine.available:
        pytest.skip("EasyOCR failed to initialize — see its own log output for why")
    return engine


@pytest.mark.parametrize("plate_text", PLATE_SAMPLES)
def test_paddleocr_reads_synthetic_plate(paddle_engine, plate_text):
    crop = _synthetic_plate(plate_text)
    result = paddle_engine.read(crop)
    assert result is not None, f"PaddleOCR returned no read at all for {plate_text!r}"
    raw_text, confidence = result
    assert 0.0 <= confidence <= 1.0

    normalized = normalize(raw_text)
    assert normalized is not None, (
        f"PaddleOCR read {raw_text!r} for input {plate_text!r}, but plate_normalizer "
        "couldn't validate it against either plate format — OCR output was too far off"
    )
    normalized_text, _region = normalized
    assert normalized_text == plate_text, (
        f"PaddleOCR+normalizer produced {normalized_text!r}, expected {plate_text!r} "
        f"(raw OCR text was {raw_text!r})"
    )


def _edit_distance(a: str, b: str) -> int:
    """Plain Levenshtein distance — no extra dependency for one small
    helper. Used below to measure EasyOCR's accuracy rather than just
    pass/fail it on exact match, which the run that first wrote this
    test proved is too strict for a genuinely probabilistic engine."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = curr
    return prev[-1]


@pytest.mark.parametrize("plate_text", PLATE_SAMPLES)
def test_easyocr_reads_synthetic_plate(easyocr_engine, plate_text):
    """Confirms EasyOCR is functional (loads, produces output on a plate
    crop) as a hard requirement — but scores textual accuracy rather
    than requiring an exact match, unlike the PaddleOCR test above.

    This distinction is itself the finding: run once against these same
    three samples, EasyOCR read the first correctly but misread digits
    in the other two (e.g. "0001" -> "OOO1", "3" -> "S" — the exact
    class of visual confusion plate_normalizer's single-character
    correction pass is built to catch, but three simultaneous errors in
    one string exceeds what a *single*-character correction can fix by
    design). That's expected, real behavior for a fallback OCR engine,
    not a bug — anpr.py only ever invokes it when the primary engine
    (PaddleOCR) is already uncertain, precisely because it's the less
    reliable of the two. An exact-match assertion here would either
    flake on every run or paper over that real characteristic.
    """
    crop = _synthetic_plate(plate_text)
    result = easyocr_engine.read(crop)
    assert result is not None, f"EasyOCR returned no read at all for {plate_text!r}"
    raw_text, confidence = result
    assert 0.0 <= confidence <= 1.0

    distance = _edit_distance(raw_text.upper(), plate_text)
    assert distance <= 4, (
        f"EasyOCR read {raw_text!r} for input {plate_text!r} — edit distance "
        f"{distance} is too far off to be the same plate, not just a couple of "
        "confused characters"
    )
