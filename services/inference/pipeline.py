"""Per-camera worker: owns one CameraSource + one CameraTracker + one
per-camera set of TrackSessions and runs the frame loop detect -> track ->
observe -> publish. One OS thread per camera — cv2.VideoCapture.read()/
grab() are blocking calls that release the GIL during I/O, so this scales
fine at hackathon (~50 camera) scale without needing asyncio here;
detector.predict() calls across threads share one GPU-resident model (see
detector.py), which is fine since each call is a short, self-contained
forward pass.

Two kinds of events leave this worker for services/api to consume:
  - PlateEvent (existing, Phase 5/6): one per *published* improvement in a
    track's fused plate read, same real-time semantics as before this
    upgrade — watchlist matching and vehicle_trace depend on this staying
    low-latency, so it is NOT deferred until a track finalizes.
  - VehicleEvent (new): exactly one per *finalized* track (see
    track_state.py), consolidating vehicle type/manufacturer/model and the
    best fused plate read plus best-evidence images — the "one row per
    completed vehicle sighting" view brief sections 18-20/22 ask for.
"""

from __future__ import annotations

import logging
import threading
import time

import numpy as np

import config
import metrics
import plate_quality
from anpr import AnprEngine
from camera_source import CameraSource, FrameStatus
from detector import Detector
from event_publisher import EventPublisher
from events import PlateEvent, TrackedObject, VehicleEvent
from snapshot import save as save_snapshot
from snapshot import save_track_evidence
from temporal_fusion import PlateObservation
from track_state import ClassificationVote, TrackSession, TrackSessionRegistry
from tracker import TrackerRegistry
from vehicle_classifier import ManufacturerClassifier, ModelClassifier, merge_with_priority

log = logging.getLogger("inference.pipeline")


class CameraWorker(threading.Thread):
    def __init__(
        self,
        camera_id: str,
        detector: Detector,
        tracker_registry: TrackerRegistry,
        track_registry: TrackSessionRegistry,
        anpr_engine: AnprEngine,
        manufacturer_classifier: ManufacturerClassifier,
        model_classifier: ModelClassifier,
        publisher: EventPublisher,
        global_stop: threading.Event,
    ) -> None:
        super().__init__(name=f"camera-{camera_id}", daemon=True)
        self.camera_id = camera_id
        self._detector = detector
        self._tracker_registry = tracker_registry
        self._track_registry = track_registry
        self._anpr_engine = anpr_engine
        self._manufacturer_classifier = manufacturer_classifier
        self._model_classifier = model_classifier
        self._publisher = publisher
        self._global_stop = global_stop
        self._local_stop = threading.Event()
        self._source = CameraSource(camera_id)

    def stop(self) -> None:
        self._local_stop.set()

    def run(self) -> None:
        log.info("camera=%s worker starting", self.camera_id)
        try:
            while not self._global_stop.is_set() and not self._local_stop.is_set():
                if not self._source.is_open():
                    self._try_connect()
                    continue

                status, frame = self._source.read()

                if status == FrameStatus.DISCONNECTED:
                    metrics.CAMERA_DISCONNECTS.labels(camera_id=self.camera_id).inc()
                    self._publisher.publish_camera_health(self.camera_id, "disconnected")
                    self._reset_track_state("reconnect")
                    self._source.schedule_reconnect()
                    metrics.RECONNECT_ATTEMPTS.labels(camera_id=self.camera_id).inc()
                    continue

                if status == FrameStatus.NO_FRAME:
                    continue

                if status == FrameStatus.DISCONTINUITY:
                    metrics.SCENE_DISCONTINUITIES.labels(camera_id=self.camera_id).inc()
                    self._reset_track_state("scene discontinuity")

                assert frame is not None
                self._process_frame(frame.image, frame.pts_ms, frame.wall_ts_ms)
        finally:
            self._source.disconnect()
            self._tracker_registry.remove(self.camera_id)
            self._finalize_all_sessions("worker stopped")
            log.info("camera=%s worker stopped", self.camera_id)

    def _reset_track_state(self, reason: str) -> None:
        # Track IDs are meaningless across this boundary (reconnect or a
        # scene cut) — but a session may already have a decent partial
        # read worth keeping (brief section 24: graceful degradation), so
        # every in-flight session is finalized-as-is rather than silently
        # dropped, then the whole per-camera session map is cleared so no
        # stale session can inherit a reused track_id after the reset.
        self._tracker_registry.get(self.camera_id).reset(reason)
        self._finalize_all_sessions(reason)

    def _finalize_all_sessions(self, reason: str) -> None:
        sessions = self._track_registry.pop_all_camera_sessions(self.camera_id)
        if sessions:
            log.info(
                "camera=%s finalizing %d in-flight track session(s) (%s)",
                self.camera_id,
                len(sessions),
                reason,
            )
        for session in sessions:
            self._finalize_track(session)

    def _try_connect(self) -> None:
        if not self._source.should_attempt_reconnect():
            time.sleep(0.2)
            return

        if self._source.connect():
            self._source.note_connected()
            self._publisher.publish_camera_health(self.camera_id, "connected")
        else:
            self._publisher.publish_camera_health(self.camera_id, "disconnected")
            self._source.schedule_reconnect()
            metrics.RECONNECT_ATTEMPTS.labels(camera_id=self.camera_id).inc()

    def _process_frame(self, image, pts_ms: float, wall_ts_ms: float) -> None:
        start = time.monotonic()

        detections = self._detector.predict(image)
        for d in detections:
            metrics.DETECTIONS_TOTAL.labels(camera_id=self.camera_id, class_name=d.class_name).inc()

        tracked = self._tracker_registry.get(self.camera_id).update(
            detections, image, pts_ms, wall_ts_ms
        )
        metrics.TRACKS_ACTIVE.labels(camera_id=self.camera_id).set(len(tracked))

        seen_track_ids: set[int] = set()
        for obj in tracked:
            self._publisher.publish_detection(obj)
            seen_track_ids.add(obj.track_id)
            # Every piece of state below is looked up/created by
            # (camera_id, track_id) — nothing here is a frame-global
            # variable, so N vehicles in the same frame each get their
            # own independent session, buffer, and best-frame slot (brief
            # section 21).
            session = self._track_registry.get_or_create(self.camera_id, obj.track_id)
            session.record_detection(obj.class_name, obj.wall_ts_ms)

            if obj.class_name in config.VEHICLE_CLASS_NAMES:
                self._process_vehicle(obj, session, image)

        # A track_id ByteTrack no longer confirms this frame is either
        # still-but-briefly-occluded (normal) or genuinely gone; either
        # way it's counted as "missing" and only finalized once that's
        # persisted for TRACK_LOST_GRACE_FRAMES consecutive frames.
        for session in self._track_registry.mark_seen(self.camera_id, seen_track_ids):
            self._track_registry.pop(self.camera_id, session.track_id)
            self._finalize_track(session)

        metrics.FRAMES_PROCESSED.labels(camera_id=self.camera_id).inc()
        metrics.INFERENCE_LATENCY_SECONDS.labels(camera_id=self.camera_id).observe(
            time.monotonic() - start
        )

    def _process_vehicle(self, obj: TrackedObject, session: TrackSession, frame: np.ndarray) -> None:
        x1, y1, x2, y2 = obj.bbox_xyxy
        h, w = frame.shape[:2]
        crop = frame[max(int(y1), 0) : min(int(y2), h), max(int(x1), 0) : min(int(x2), w)]
        if crop.size == 0:
            return

        # plate_quality.assess() is a generic sharpness/size/contrast
        # scorer, not plate-specific in its math — reused here rather
        # than writing a second near-identical "vehicle crop quality"
        # module (brief section 30: don't duplicate an existing
        # subsystem). This score is what "best evidence frame" (section
        # 17) is selected by.
        quality = plate_quality.assess(crop).overall
        session.consider_best_vehicle_frame(crop, quality, obj.frame_pts_ms)

        self._try_anpr(obj, session, crop)
        self._try_classification(session)

    def _try_anpr(self, obj: TrackedObject, session: TrackSession, crop: np.ndarray) -> None:
        if not self._anpr_engine.available:
            return
        if session.should_skip_anpr_rerun():
            return

        metrics.ANPR_ATTEMPTS_TOTAL.labels(camera_id=self.camera_id).inc()
        plate_read = self._anpr_engine.process(crop)
        if plate_read is None:
            return

        session.record_plate_observation(
            PlateObservation(
                text=plate_read.plate_text,
                region=plate_read.region,
                detector_confidence=plate_read.detector_confidence,
                ocr_confidence=plate_read.ocr_confidence,
                quality_score=plate_read.quality_score,
                engine=plate_read.engine,
                frame_pts_ms=obj.frame_pts_ms,
            )
        )
        session.consider_best_plate_frame(crop, plate_read.quality_score, obj.frame_pts_ms)
        metrics.PLATE_OBSERVATIONS_TOTAL.labels(camera_id=self.camera_id).inc()

        # Publish the *fused* multi-observation consensus, not the raw
        # single-frame read — this is the one behavior change to the
        # existing real-time plate_events stream: each publish is now
        # backed by every observation collected for this track so far,
        # not just whichever frame happened to trigger this call.
        fused = session.fused_plate()
        if fused is None:
            return
        if not session.should_publish_plate(fused.confidence):
            return
        session.record_published_plate(fused.confidence)

        snapshot_path = save_snapshot(self.camera_id, fused.plate_text, obj.frame_pts_ms, crop)
        event = PlateEvent(
            camera_id=self.camera_id,
            track_id=obj.track_id,
            plate_text=fused.plate_text,
            confidence=fused.confidence,
            region=fused.region,
            vehicle_class=obj.class_name,
            bbox_xyxy=obj.bbox_xyxy,
            frame_pts_ms=obj.frame_pts_ms,
            wall_ts_ms=obj.wall_ts_ms,
            snapshot_path=snapshot_path,
        )
        self._publisher.publish_plate_event(event)
        metrics.PLATES_READ_TOTAL.labels(camera_id=self.camera_id).inc()

    def _try_classification(self, session: TrackSession) -> None:
        if not config.ENABLE_VEHICLE_CLASSIFICATION:
            return
        if not session.should_attempt_classification():
            return
        session.mark_classification_attempted()

        vehicle_image = session.best_vehicle_image
        assert vehicle_image is not None  # guaranteed by should_attempt_classification()

        manufacturer_result = self._manufacturer_classifier.classify(vehicle_image)
        model_result = self._model_classifier.classify(vehicle_image)
        # merge_with_priority is a no-op pass-through here (no VLM result
        # to merge yet — see vehicle_classifier.py's MakeModelVlmAdapter
        # docstring for why) but calling it keeps the "fallback must not
        # override a confident primary result" rule enforced in one place
        # even after a real VLM is dropped in.
        model_result = merge_with_priority(model_result, None)

        manufacturer_vote = (
            ClassificationVote(manufacturer_result.label, manufacturer_result.confidence, manufacturer_result.source)
            if manufacturer_result is not None
            else None
        )
        model_vote = (
            ClassificationVote(model_result.label, model_result.confidence, model_result.source)
            if model_result is not None
            else None
        )
        session.record_classification(manufacturer_vote, model_vote)
        if manufacturer_vote or model_vote:
            metrics.VEHICLE_CLASSIFICATIONS_TOTAL.labels(camera_id=self.camera_id).inc()

    def _finalize_track(self, session: TrackSession) -> None:
        finalized = session.finalize()

        # Graceful degradation (brief section 24): a track with no plate
        # read and no classification is still a real, useful event (at
        # minimum, "a <vehicle_type> was seen") — never discarded just
        # because a lower-priority stage produced nothing.
        vehicle_path, plate_path = save_track_evidence(
            self.camera_id, finalized.track_id, finalized.best_vehicle_image, finalized.best_plate_image
        )

        event = VehicleEvent(
            camera_id=finalized.camera_id,
            track_id=finalized.track_id,
            first_seen_wall_ts_ms=finalized.first_seen_wall_ts_ms,
            last_seen_wall_ts_ms=finalized.last_seen_wall_ts_ms,
            vehicle_type=finalized.vehicle_type,
            vehicle_type_observations=finalized.vehicle_type_observations,
            plate_text=finalized.plate.plate_text if finalized.plate else "",
            plate_confidence=finalized.plate.confidence if finalized.plate else 0.0,
            plate_region=finalized.plate.region if finalized.plate else "",
            plate_valid=finalized.plate is not None,
            plate_observations=finalized.plate.observations if finalized.plate else 0,
            plate_agreement=finalized.plate.agreement if finalized.plate else 0.0,
            manufacturer=finalized.manufacturer.label if finalized.manufacturer else "",
            manufacturer_confidence=finalized.manufacturer.confidence if finalized.manufacturer else 0.0,
            model=finalized.model.label if finalized.model else "",
            model_confidence=finalized.model.confidence if finalized.model else 0.0,
            best_vehicle_image_path=vehicle_path,
            best_plate_image_path=plate_path,
        )
        self._publisher.publish_vehicle_event(event)
        metrics.VEHICLE_EVENTS_FINALIZED_TOTAL.labels(camera_id=self.camera_id).inc()
