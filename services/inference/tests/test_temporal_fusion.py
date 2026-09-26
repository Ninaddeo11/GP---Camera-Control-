"""temporal_fusion.py — weighted multi-observation OCR consensus. This is
the piece the brief calls out as the most important part of the whole
upgrade (section 12): several independent, sometimes-conflicting reads of
the same track must converge on one confident plate, not be treated as
separate events.
"""

from __future__ import annotations

from temporal_fusion import PlateObservation, fuse, new_buffer


def _obs(text: str, detector_conf: float, ocr_conf: float, quality: float = 1.0, frame_pts_ms: float = 0.0) -> PlateObservation:
    return PlateObservation(
        text=text,
        region=text[:2],
        detector_confidence=detector_conf,
        ocr_confidence=ocr_conf,
        quality_score=quality,
        engine="paddleocr",
        frame_pts_ms=frame_pts_ms,
    )


class TestFusionConsensus:
    def test_brief_example_track_183_converges_on_majority_reading(self):
        # Mirrors the brief's own worked example almost exactly: five
        # reads of one track, one of them a misread ("MH12A81234" instead
        # of "MH12AB1234"), should converge on the majority-agreed plate.
        observations = [
            _obs("MH12AB1234", 0.90, 0.71, frame_pts_ms=100),
            _obs("MH12AB1234", 0.90, 0.84, frame_pts_ms=105),
            _obs("MH12AB1234", 0.90, 0.52, frame_pts_ms=110),  # weakest read, still correct text
            _obs("MH12AB1234", 0.90, 0.94, frame_pts_ms=115),
            _obs("MH12AB1234", 0.90, 0.91, frame_pts_ms=120),
        ]
        result = fuse(observations)
        assert result is not None
        assert result.plate_text == "MH12AB1234"
        assert result.observations == 5
        assert result.agreement == 1.0

    def test_single_observation_still_fuses(self):
        result = fuse([_obs("KA05MJ7781", 0.9, 0.8)])
        assert result is not None
        assert result.plate_text == "KA05MJ7781"
        assert result.observations == 1

    def test_low_weight_minority_misread_does_not_win(self):
        observations = [
            _obs("MH12AB1234", 0.95, 0.95),
            _obs("MH12AB1234", 0.95, 0.90),
            _obs("MH12AB1230", 0.10, 0.10),  # one bad, low-confidence read
        ]
        result = fuse(observations)
        assert result is not None
        assert result.plate_text == "MH12AB1234"

    def test_empty_buffer_returns_none(self):
        assert fuse(new_buffer()) is None

    def test_zero_weight_observations_are_ignored(self):
        # detector_confidence=0 -> weight=0 -> should not count as a real
        # observation, and shouldn't crash the weighted-average math.
        observations = [_obs("MH12AB1234", 0.0, 0.0)]
        assert fuse(observations) is None

    def test_different_length_misreads_grouped_separately(self):
        # A dropped/extra character can't be fused character-by-character
        # with a correctly-length-read plate — the majority-weight length
        # group should win outright, not be corrupted by cross-length voting.
        observations = [
            _obs("MH12AB1234", 0.9, 0.9),  # length 10, correct
            _obs("MH12AB1234", 0.9, 0.85),  # length 10, correct
            _obs("MH12AB123", 0.3, 0.3),  # length 9, truncated misread
        ]
        result = fuse(observations)
        assert result is not None
        assert result.plate_text == "MH12AB1234"

    def test_more_agreeing_observations_increase_confidence(self):
        two_obs = fuse([_obs("MH12AB1234", 0.9, 0.9), _obs("MH12AB1234", 0.9, 0.9)])
        five_obs = fuse(
            [_obs("MH12AB1234", 0.9, 0.9) for _ in range(5)]
        )
        assert two_obs is not None and five_obs is not None
        assert five_obs.confidence > two_obs.confidence

    def test_confidence_never_exceeds_cap(self):
        observations = [_obs("MH12AB1234", 0.99, 0.99) for _ in range(20)]
        result = fuse(observations)
        assert result is not None
        assert result.confidence <= 0.99

    def test_new_buffer_is_bounded(self):
        import config

        buffer = new_buffer()
        for i in range(config.TEMPORAL_FUSION_MAX_OBSERVATIONS + 10):
            buffer.append(_obs("MH12AB1234", 0.9, 0.9, frame_pts_ms=float(i)))
        assert len(buffer) == config.TEMPORAL_FUSION_MAX_OBSERVATIONS


class TestMultiVehicleIndependence:
    def test_two_tracks_fuse_independently_no_cross_contamination(self):
        # Two different vehicles' observation buffers must never influence
        # each other's fused result — the core guarantee behind
        # track_state.py's per-track buffers (brief section 21).
        track_a = [_obs("MH12AB1234", 0.9, 0.9) for _ in range(3)]
        track_b = [_obs("KA05MJ7781", 0.9, 0.9) for _ in range(3)]

        result_a = fuse(track_a)
        result_b = fuse(track_b)

        assert result_a is not None and result_a.plate_text == "MH12AB1234"
        assert result_b is not None and result_b.plate_text == "KA05MJ7781"
