"""Per-camera worker: owns one CameraSource + one CameraTracker and runs
the frame loop detect -> track -> publish. One OS thread per camera —
cv2.VideoCapture.read()/grab() are blocking calls that release the GIL
during I/O, so this scales fine at hackathon (~50 camera) scale without
needing asyncio here; detector.predict() calls across threads share one
GPU-resident model (see detector.py), which is fine since each call is a
short, self-contained forward pass.
"""

from __future__ import annotations

import logging
import threading
import time

import numpy as np

import config
import metrics
from anpr import AnprEngine, PlateDedupState
from camera_source import CameraSource, FrameStatus
from detector import Detector
from event_publisher import EventPublisher
from events import PlateEvent, TrackedObject
from snapshot import save as save_snapshot
from tracker import TrackerRegistry

log = logging.getLogger("inference.pipeline")


class CameraWorker(threading.Thread):
    def __init__(
        self,
        camera_id: str,
        detector: Detector,
        tracker_registry: TrackerRegistry,
        anpr_engine: AnprEngine,
        plate_dedup: PlateDedupState,
        publisher: EventPublisher,
        global_stop: threading.Event,
    ) -> None:
        super().__init__(name=f"camera-{camera_id}", daemon=True)
        self.camera_id = camera_id
        self._detector = detector
        self._tracker_registry = tracker_registry
        self._anpr_engine = anpr_engine
        self._plate_dedup = plate_dedup
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
            self._plate_dedup.clear_camera(self.camera_id)
            log.info("camera=%s worker stopped", self.camera_id)

    def _reset_track_state(self, reason: str) -> None:
        # Track IDs are meaningless across this boundary (reconnect or a
        # scene cut) — old ANPR dedup entries keyed by those IDs must go
        # with them, or a brand-new track could inherit stale "already
        # published" state from an unrelated vehicle that happened to get
        # the same track_id before the reset.
        self._tracker_registry.get(self.camera_id).reset(reason)
        self._plate_dedup.clear_camera(self.camera_id)

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

        for obj in tracked:
            self._publisher.publish_detection(obj)
            if obj.class_name in config.VEHICLE_CLASS_NAMES:
                self._try_anpr(obj, image)

        metrics.FRAMES_PROCESSED.labels(camera_id=self.camera_id).inc()
        metrics.INFERENCE_LATENCY_SECONDS.labels(camera_id=self.camera_id).observe(
            time.monotonic() - start
        )

    def _try_anpr(self, obj: TrackedObject, frame: np.ndarray) -> None:
        if not self._anpr_engine.available:
            return
        if self._plate_dedup.should_skip_rerun(self.camera_id, obj.track_id):
            return

        x1, y1, x2, y2 = obj.bbox_xyxy
        h, w = frame.shape[:2]
        crop = frame[max(int(y1), 0) : min(int(y2), h), max(int(x1), 0) : min(int(x2), w)]
        if crop.size == 0:
            return

        metrics.ANPR_ATTEMPTS_TOTAL.labels(camera_id=self.camera_id).inc()
        plate_read = self._anpr_engine.process(crop)
        if plate_read is None:
            return

        # Must check should_publish against the *current* best before
        # record() updates it — recording first would make every read
        # compare against itself and never clear the margin.
        should_publish = self._plate_dedup.should_publish(
            self.camera_id, obj.track_id, plate_read.confidence
        )
        self._plate_dedup.record(self.camera_id, obj.track_id, plate_read.confidence)
        if not should_publish:
            return

        snapshot_path = save_snapshot(self.camera_id, plate_read.plate_text, obj.frame_pts_ms, crop)
        event = PlateEvent(
            camera_id=self.camera_id,
            track_id=obj.track_id,
            plate_text=plate_read.plate_text,
            confidence=plate_read.confidence,
            region=plate_read.region,
            vehicle_class=obj.class_name,
            bbox_xyxy=obj.bbox_xyxy,
            frame_pts_ms=obj.frame_pts_ms,
            wall_ts_ms=obj.wall_ts_ms,
            snapshot_path=snapshot_path,
        )
        self._publisher.publish_plate_event(event)
        metrics.PLATES_READ_TOTAL.labels(camera_id=self.camera_id).inc()
