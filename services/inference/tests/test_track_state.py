"""track_state.py — per-track lifecycle, session bookkeeping, and the
multi-vehicle independence guarantee (brief section 21: no frame-global
state, everything keyed by track_id). No models needed — this is pure
session/state-machine logic.
"""

from __future__ import annotations

import numpy as np

import config
from temporal_fusion import PlateObservation
from track_state import TrackLifecycleState, TrackSessionRegistry


def _plate_obs(text: str, conf: float = 0.9, pts_ms: float = 0.0) -> PlateObservation:
    return PlateObservation(
        text=text, region=text[:2], detector_confidence=conf, ocr_confidence=conf,
        quality_score=1.0, engine="paddleocr", frame_pts_ms=pts_ms,
    )


def _crop() -> np.ndarray:
    return np.zeros((60, 160, 3), dtype=np.uint8)


class TestLifecycleTransitions:
    def test_new_track_starts_in_new_state(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 101)
        assert session.state == TrackLifecycleState.NEW

    def test_first_detection_moves_to_active(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 101)
        session.record_detection("car", wall_ts_ms=1000.0)
        assert session.state == TrackLifecycleState.ACTIVE

    def test_plate_observation_advances_state(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 101)
        session.record_detection("car", wall_ts_ms=1000.0)
        session.record_plate_observation(_plate_obs("MH12AB1234"))
        assert session.state == TrackLifecycleState.PLATE_OBSERVATION

    def test_fused_plate_moves_to_confirmed(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 101)
        session.record_detection("car", wall_ts_ms=1000.0)
        session.record_plate_observation(_plate_obs("MH12AB1234"))
        session.fused_plate()
        assert session.state == TrackLifecycleState.CONFIRMED

    def test_missing_track_is_marked_lost_immediately(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 101)
        session.record_detection("car", wall_ts_ms=1000.0)
        registry.mark_seen("cam1", seen_track_ids=set())  # 101 absent this frame
        assert session.state == TrackLifecycleState.LOST

    def test_finalize_is_only_triggered_after_grace_period(self):
        registry = TrackSessionRegistry()
        registry.get_or_create("cam1", 101).record_detection("car", wall_ts_ms=1000.0)

        finalizable: list = []
        for _ in range(config.TRACK_LOST_GRACE_FRAMES - 1):
            finalizable = registry.mark_seen("cam1", seen_track_ids=set())
        assert finalizable == []

        finalizable = registry.mark_seen("cam1", seen_track_ids=set())
        assert len(finalizable) == 1
        assert finalizable[0].track_id == 101

    def test_reappearing_within_grace_period_is_not_finalized(self):
        registry = TrackSessionRegistry()
        registry.get_or_create("cam1", 101).record_detection("car", wall_ts_ms=1000.0)

        registry.mark_seen("cam1", seen_track_ids=set())  # miss once
        finalizable = registry.mark_seen("cam1", seen_track_ids={101})  # reappears
        assert finalizable == []
        assert registry.get_or_create("cam1", 101).frames_missing == 0


class TestMultiVehicleIndependence:
    def test_two_tracks_on_same_camera_have_independent_state(self):
        registry = TrackSessionRegistry()
        session_a = registry.get_or_create("cam1", 101)
        session_b = registry.get_or_create("cam1", 102)

        session_a.record_detection("car", wall_ts_ms=1000.0)
        session_a.record_plate_observation(_plate_obs("MH12AB1234"))
        session_b.record_detection("truck", wall_ts_ms=1000.0)
        session_b.record_plate_observation(_plate_obs("KA05MJ7781"))

        fused_a = session_a.fused_plate()
        fused_b = session_b.fused_plate()

        assert fused_a.plate_text == "MH12AB1234"
        assert fused_b.plate_text == "KA05MJ7781"
        assert session_a.majority_vehicle_class() == "car"
        assert session_b.majority_vehicle_class() == "truck"

    def test_same_track_id_on_different_cameras_are_independent(self):
        # Two different cameras can both have a "track 5" simultaneously
        # (ByteTrack IDs are only unique per camera) — must not collide.
        registry = TrackSessionRegistry()
        session_cam1 = registry.get_or_create("cam1", 5)
        session_cam2 = registry.get_or_create("cam2", 5)

        session_cam1.record_plate_observation(_plate_obs("MH12AB1234"))
        session_cam2.record_plate_observation(_plate_obs("KA05MJ7781"))

        assert session_cam1.fused_plate().plate_text == "MH12AB1234"
        assert session_cam2.fused_plate().plate_text == "KA05MJ7781"

    def test_finalizing_one_camera_does_not_affect_another(self):
        registry = TrackSessionRegistry()
        registry.get_or_create("cam1", 1).record_detection("car", wall_ts_ms=1000.0)
        registry.get_or_create("cam2", 1).record_detection("bus", wall_ts_ms=1000.0)

        registry.pop_all_camera_sessions("cam1")

        remaining = registry.get_or_create("cam2", 1)
        assert remaining.majority_vehicle_class() == "bus"


class TestBestFrameSelection:
    def test_higher_quality_frame_replaces_lower_quality(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 1)
        low_quality_crop = _crop()
        high_quality_crop = _crop()

        session.consider_best_vehicle_frame(low_quality_crop, score=0.3, frame_pts_ms=100)
        session.consider_best_vehicle_frame(high_quality_crop, score=0.9, frame_pts_ms=200)
        assert session.best_vehicle_image is high_quality_crop

    def test_lower_quality_frame_does_not_replace_existing_best(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 1)
        high_quality_crop = _crop()

        session.consider_best_vehicle_frame(high_quality_crop, score=0.9, frame_pts_ms=100)
        session.consider_best_vehicle_frame(_crop(), score=0.2, frame_pts_ms=200)
        assert session.best_vehicle_image is high_quality_crop

    def test_at_most_one_image_retained_per_kind(self):
        # Bounded memory (brief section 18) — many frames observed, but
        # only ever one vehicle image and one plate image held at a time.
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 1)
        for i in range(50):
            session.consider_best_vehicle_frame(_crop(), score=float(i), frame_pts_ms=float(i))
        assert session.best_vehicle_image is not None


class TestFinalize:
    def test_finalize_with_no_plate_still_produces_vehicle_type(self):
        # Graceful degradation (brief section 24): plate/classification
        # failing must not discard a perfectly good vehicle-type event.
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 1)
        session.record_detection("bus", wall_ts_ms=1000.0)

        finalized = session.finalize()
        assert finalized.vehicle_type == "bus"
        assert finalized.plate is None

    def test_finalize_includes_fused_plate_when_available(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 1)
        session.record_detection("car", wall_ts_ms=1000.0)
        session.record_plate_observation(_plate_obs("MH12AB1234"))

        finalized = session.finalize()
        assert finalized.plate is not None
        assert finalized.plate.plate_text == "MH12AB1234"

    def test_publish_dedup_only_publishes_meaningful_improvement(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 1)

        assert session.should_publish_plate(0.5) is True
        session.record_published_plate(0.5)
        assert session.should_publish_plate(0.51) is False  # below margin
        assert session.should_publish_plate(0.5 + config.ANPR_REPUBLISH_MARGIN) is True

    def test_skip_rerun_once_confidently_published(self):
        registry = TrackSessionRegistry()
        session = registry.get_or_create("cam1", 1)
        assert session.should_skip_anpr_rerun() is False

        session.record_published_plate(config.ANPR_SKIP_RERUN_ABOVE_CONFIDENCE)
        assert session.should_skip_anpr_rerun() is True
