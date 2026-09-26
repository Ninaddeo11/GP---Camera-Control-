"""Plate-crop quality assessment and enhancement, run between plate
detection and OCR. Two separate concerns kept in one module because they
share the same crop and the same config:

  assess()  -> should this crop even be sent to OCR? (too small/blurry
              crops waste an OCR call and produce garbage text)
  enhance() -> make a crop that passes assess() easier for OCR to read.

Every stage is independently toggleable via config (section 9 of the
brief: "Do NOT blindly apply every enhancement to every image"), and this
never runs perspective correction — CCTV plate crops are near-frontal by
construction (the plate detector only fires on plates it can actually
see), and a full homography-based deskew needs corner-point detection this
project has no model for. Sharpness/size/contrast covers the failure modes
actually observed in low-quality RTSP footage.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

import config


@dataclass(frozen=True)
class QualityScore:
    """0-1 sub-scores plus the combined `overall` used both to gate OCR
    and to weight this observation in temporal_fusion.fuse().
    """

    sharpness: float
    size: float
    contrast: float
    overall: float
    usable: bool


def _sharpness_score(gray: np.ndarray) -> float:
    # Variance of the Laplacian — a standard, cheap blur proxy (higher =
    # sharper edges = less motion/focus blur). Normalized against a
    # config ceiling rather than left unbounded, so it combines sensibly
    # with the 0-1 size/contrast scores below.
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return min(1.0, variance / config.PLATE_QUALITY_SHARPNESS_CEILING)


def _size_score(width: int, height: int) -> float:
    # A plate crop just above the OCR-viability floor (ANPR_MIN_CROP_*)
    # is technically usable but marginal; score ramps up to 1.0 at a
    # comfortably larger size rather than being a flat pass/fail, so
    # larger/closer plates are preferred as fusion observations even when
    # a smaller crop also cleared the floor.
    min_dim = min(width, height)
    floor = min(config.ANPR_MIN_CROP_WIDTH, config.ANPR_MIN_CROP_HEIGHT)
    ceiling = floor * config.PLATE_QUALITY_SIZE_CEILING_MULTIPLIER
    if ceiling <= floor:
        return 1.0
    return max(0.0, min(1.0, (min_dim - floor) / (ceiling - floor)))


def _contrast_score(gray: np.ndarray) -> float:
    # Low std-dev = washed out / low-contrast crop (backlight, glare,
    # night IR flare) — OCR engines reliably struggle with these even
    # when nominally "sharp".
    return min(1.0, float(gray.std()) / config.PLATE_QUALITY_CONTRAST_CEILING)


def assess(plate_crop: np.ndarray) -> QualityScore:
    if plate_crop.size == 0:
        return QualityScore(0.0, 0.0, 0.0, 0.0, usable=False)

    h, w = plate_crop.shape[:2]
    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if plate_crop.ndim == 3 else plate_crop

    # float()/bool() here, not just for tidiness: cv2/numpy comparisons
    # produce numpy scalar types (np.float64, np.bool_), which silently
    # break `is True`/`is False` identity checks and can serialize
    # differently than a plain bool/float depending on the caller — this
    # dataclass's fields should always be plain Python types.
    sharpness = float(_sharpness_score(gray))
    size = float(_size_score(w, h))
    contrast = float(_contrast_score(gray))
    overall = float((sharpness * 0.5) + (size * 0.25) + (contrast * 0.25))

    usable = bool(
        w >= config.ANPR_MIN_CROP_WIDTH
        and h >= config.ANPR_MIN_CROP_HEIGHT
        and sharpness >= config.PLATE_QUALITY_MIN_SHARPNESS
    )
    return QualityScore(sharpness=sharpness, size=size, contrast=contrast, overall=overall, usable=usable)


def enhance(plate_crop: np.ndarray) -> np.ndarray:
    """Returns a new array; never mutates `plate_crop` in place, since
    callers (pipeline.py) may still want the original for snapshot/best-
    frame evidence after this runs.
    """
    out = plate_crop

    if config.PLATE_QUALITY_UPSCALE_MAX_FACTOR > 1.0:
        h, w = out.shape[:2]
        min_dim = min(w, h)
        target_min = config.ANPR_MIN_CROP_HEIGHT * 2
        if 0 < min_dim < target_min:
            factor = min(config.PLATE_QUALITY_UPSCALE_MAX_FACTOR, target_min / min_dim)
            out = cv2.resize(out, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)

    if config.PLATE_QUALITY_ENABLE_DENOISE:
        out = cv2.fastNlMeansDenoisingColored(out, None, 5, 5, 7, 21) if out.ndim == 3 else cv2.fastNlMeansDenoising(out, None, 5, 7, 21)

    if config.PLATE_QUALITY_ENABLE_CLAHE:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        if out.ndim == 3:
            lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            l_channel = clahe.apply(l_channel)
            out = cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)
        else:
            out = clahe.apply(out)

    if config.PLATE_QUALITY_ENABLE_SHARPEN:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        out = cv2.filter2D(out, -1, kernel)

    return out
