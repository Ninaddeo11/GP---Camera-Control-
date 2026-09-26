"""Sentinel Grid inference service entrypoint.

Coordinator loop: poll the camera catalogue, start a CameraWorker thread
for each newly-seen camera_id, stop and join the thread for any camera_id
that's dropped out of the catalogue. The detector (one GPU-resident YOLO
model), tracker registry, and event publisher are constructed once here
and shared read-only (detector) or via internal per-camera locking
(tracker registry) across all worker threads.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import threading
import time

from prometheus_client import start_http_server

import config
import metrics
from anpr import AnprEngine
from camera_catalogue_client import fetch_active_camera_ids
from detector import Detector
from event_publisher import EventPublisher
from pipeline import CameraWorker
from track_state import TrackSessionRegistry
from tracker import TrackerRegistry
from vehicle_classifier import ManufacturerClassifier, ModelClassifier

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("inference.main")


def _fetch_active_camera_ids_sync() -> set[str]:
    return asyncio.run(fetch_active_camera_ids())


def main() -> None:
    start_http_server(config.METRICS_PORT)
    log.info("Prometheus metrics exposed on :%d/metrics", config.METRICS_PORT)

    detector = Detector()
    tracker_registry = TrackerRegistry()
    track_registry = TrackSessionRegistry()
    anpr_engine = AnprEngine()  # logs a clear warning and no-ops if disabled
    # Both classifiers log a clear info line and no-op (Unknown) if their
    # model file isn't present — see vehicle_classifier.py.
    manufacturer_classifier = ManufacturerClassifier()
    model_classifier = ModelClassifier()
    publisher = EventPublisher()

    global_stop = threading.Event()

    def _handle_signal(signum, _frame) -> None:
        log.info("Received signal %s — shutting down", signum)
        global_stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    workers: dict[str, CameraWorker] = {}

    log.info(
        "inference service starting: catalogue=%s poll_interval=%ds device=%s model=%s "
        "anpr_available=%s secondary_ocr_available=%s manufacturer_classifier_available=%s "
        "model_classifier_available=%s",
        config.INGEST_API_URL,
        config.INGEST_POLL_INTERVAL_SECONDS,
        config.DEVICE,
        config.MODEL_PATH,
        anpr_engine.available,
        anpr_engine.secondary_ocr.available if anpr_engine.secondary_ocr else False,
        manufacturer_classifier.available,
        model_classifier.available,
    )

    while not global_stop.is_set():
        try:
            active_ids = _fetch_active_camera_ids_sync()
        except Exception:
            log.exception("Failed to poll catalogue at %s — keeping existing workers", config.INGEST_API_URL)
            active_ids = set(workers.keys())

        added = active_ids - workers.keys()
        removed = workers.keys() - active_ids

        for camera_id in removed:
            log.info("camera=%s no longer in catalogue — stopping worker", camera_id)
            workers[camera_id].stop()
            workers[camera_id].join(timeout=5.0)
            del workers[camera_id]

        for camera_id in added:
            log.info("camera=%s discovered — starting worker", camera_id)
            worker = CameraWorker(
                camera_id,
                detector,
                tracker_registry,
                track_registry,
                anpr_engine,
                manufacturer_classifier,
                model_classifier,
                publisher,
                global_stop,
            )
            worker.start()
            workers[camera_id] = worker

        metrics.ACTIVE_CAMERAS.set(len(workers))

        global_stop.wait(timeout=config.INGEST_POLL_INTERVAL_SECONDS)

    log.info("Stopping %d camera workers...", len(workers))
    for worker in workers.values():
        worker.stop()
    for worker in workers.values():
        worker.join(timeout=5.0)
    log.info("inference service shut down cleanly")


if __name__ == "__main__":
    main()
