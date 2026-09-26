"""vehicle_classifier.py — confidence tiering and the "a fallback must
never override a confident primary result" rule (brief sections 15/23).
No real manufacturer/model model ships in this repo (see that module's
docstring), so these tests exercise the graceful-unavailable path and the
pure confidence-arbitration logic, not real classification output.
"""

from __future__ import annotations

import numpy as np

from vehicle_classifier import (
    ClassificationResult,
    ManufacturerClassifier,
    ModelClassifier,
    confidence_tier,
    merge_with_priority,
)


class TestConfidenceTiers:
    def test_high_confidence_tier(self):
        assert confidence_tier(0.90) == "high"

    def test_probable_confidence_tier(self):
        assert confidence_tier(0.70) == "probable"

    def test_unknown_confidence_tier(self):
        assert confidence_tier(0.30) == "unknown"

    def test_result_tier_matches_its_confidence(self):
        result = ClassificationResult(label="Maruti Suzuki", confidence=0.92, source="test")
        assert result.tier == "high"


class TestGracefulUnavailability:
    def test_manufacturer_classifier_disables_when_no_weights_present(self):
        classifier = ManufacturerClassifier(model_path="models/does-not-exist.pt")
        assert classifier.available is False

    def test_disabled_classifier_returns_none_not_a_fabricated_label(self):
        classifier = ManufacturerClassifier(model_path="models/does-not-exist.pt")
        result = classifier.classify(np.zeros((100, 100, 3), dtype=np.uint8))
        assert result is None

    def test_model_classifier_disables_when_no_weights_present(self):
        classifier = ModelClassifier(model_path="models/does-not-exist.pt")
        assert classifier.available is False


class TestMergeWithPriority:
    def test_high_confidence_primary_is_never_overridden(self):
        primary = ClassificationResult(label="Maruti Swift", confidence=0.95, source="model_classifier")
        fallback = ClassificationResult(label="Hyundai i20", confidence=0.99, source="vlm")
        assert merge_with_priority(primary, fallback) is primary

    def test_low_confidence_primary_loses_to_more_confident_fallback(self):
        primary = ClassificationResult(label="Maruti Swift", confidence=0.50, source="model_classifier")
        fallback = ClassificationResult(label="Maruti Swift", confidence=0.80, source="vlm")
        assert merge_with_priority(primary, fallback) is fallback

    def test_low_confidence_primary_beats_even_lower_fallback(self):
        primary = ClassificationResult(label="Maruti Swift", confidence=0.65, source="model_classifier")
        fallback = ClassificationResult(label="Tata Nexon", confidence=0.40, source="vlm")
        assert merge_with_priority(primary, fallback) is primary

    def test_missing_primary_falls_back(self):
        fallback = ClassificationResult(label="Maruti Swift", confidence=0.70, source="vlm")
        assert merge_with_priority(None, fallback) is fallback

    def test_missing_fallback_keeps_primary(self):
        primary = ClassificationResult(label="Maruti Swift", confidence=0.70, source="model_classifier")
        assert merge_with_priority(primary, None) is primary

    def test_both_missing_returns_none(self):
        assert merge_with_priority(None, None) is None
