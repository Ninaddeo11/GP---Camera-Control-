"""plate_quality.py — blur/size/contrast scoring and enhancement, on
synthetic images (no real plate photos available in this sandbox — see
tests/conftest.py). These tests check the scoring *relationships* the
pipeline depends on (sharp beats blurry, big beats tiny), not exact score
values, since the exact numbers are tunable constants in config.py.
"""

from __future__ import annotations

import numpy as np

import config
import plate_quality


class TestAssess:
    def test_sharp_crop_scores_higher_sharpness_than_blurry(self, sharp_plate_crop, blurry_plate_crop):
        sharp = plate_quality.assess(sharp_plate_crop)
        blurry = plate_quality.assess(blurry_plate_crop)
        assert sharp.sharpness > blurry.sharpness

    def test_sharp_crop_of_sufficient_size_is_usable(self, sharp_plate_crop):
        result = plate_quality.assess(sharp_plate_crop)
        assert result.usable is True

    def test_tiny_crop_is_never_usable(self, tiny_crop):
        result = plate_quality.assess(tiny_crop)
        assert result.usable is False

    def test_empty_crop_does_not_crash(self):
        result = plate_quality.assess(np.zeros((0, 0, 3), dtype=np.uint8))
        assert result.usable is False
        assert result.overall == 0.0

    def test_scores_are_bounded_zero_to_one(self, sharp_plate_crop):
        result = plate_quality.assess(sharp_plate_crop)
        for score in (result.sharpness, result.size, result.contrast, result.overall):
            assert 0.0 <= score <= 1.0

    def test_below_min_sharpness_floor_is_unusable_even_if_large(self, blurry_plate_crop):
        # A crop that's large enough but too blurry should still fail
        # usable() — size alone can't compensate for illegible blur.
        very_blurry = blurry_plate_crop.copy()
        import cv2

        very_blurry = cv2.GaussianBlur(very_blurry, (31, 31), sigmaX=20)
        result = plate_quality.assess(very_blurry)
        assert result.sharpness < config.PLATE_QUALITY_MIN_SHARPNESS
        assert result.usable is False


class TestEnhance:
    def test_enhance_does_not_mutate_input(self, sharp_plate_crop):
        original = sharp_plate_crop.copy()
        plate_quality.enhance(sharp_plate_crop)
        assert np.array_equal(sharp_plate_crop, original)

    def test_enhance_returns_same_or_larger_dimensions(self, sharp_plate_crop):
        enhanced = plate_quality.enhance(sharp_plate_crop)
        assert enhanced.shape[0] >= sharp_plate_crop.shape[0]
        assert enhanced.shape[1] >= sharp_plate_crop.shape[1]

    def test_enhance_handles_small_crop_without_crashing(self, tiny_crop):
        enhanced = plate_quality.enhance(tiny_crop)
        assert enhanced is not None
