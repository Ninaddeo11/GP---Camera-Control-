"""Publishes tracked-object and plate-read events to Redis Streams
(`detections`, `plate_events`), the decoupling point between this service
and services/api's future consumers (watchlist correlation, Phase 7;
vehicle trace, Phase 6). This service never talks to services/api directly.
"""

from __future__ import annotations

import logging
import time

import redis

import config
from events import PlateEvent, TrackedObject

log = logging.getLogger("inference.event_publisher")


class EventPublisher:
    def __init__(self) -> None:
        self._redis = redis.from_url(config.REDIS_URL, decode_responses=True)

    def publish_detection(self, obj: TrackedObject) -> None:
        x1, y1, x2, y2 = obj.bbox_xyxy
        fields = {
            "camera_id": obj.camera_id,
            "track_id": str(obj.track_id),
            "class_name": obj.class_name,
            "confidence": f"{obj.confidence:.4f}",
            "bbox_x1": f"{x1:.1f}",
            "bbox_y1": f"{y1:.1f}",
            "bbox_x2": f"{x2:.1f}",
            "bbox_y2": f"{y2:.1f}",
            "frame_pts_ms": f"{obj.frame_pts_ms:.1f}",
            "wall_ts_ms": f"{obj.wall_ts_ms:.1f}",
        }
        try:
            self._redis.xadd(
                config.REDIS_STREAM_DETECTIONS,
                fields,
                maxlen=config.REDIS_STREAM_MAXLEN,
                approximate=True,
            )
        except redis.RedisError:
            log.exception("Failed to publish detection event for camera=%s", obj.camera_id)

    def publish_plate_event(self, event: PlateEvent) -> None:
        x1, y1, x2, y2 = event.bbox_xyxy
        fields = {
            "camera_id": event.camera_id,
            "track_id": str(event.track_id),
            "plate_text": event.plate_text,
            "confidence": f"{event.confidence:.4f}",
            "region": event.region,
            "vehicle_class": event.vehicle_class,
            "bbox_x1": f"{x1:.1f}",
            "bbox_y1": f"{y1:.1f}",
            "bbox_x2": f"{x2:.1f}",
            "bbox_y2": f"{y2:.1f}",
            "frame_pts_ms": f"{event.frame_pts_ms:.1f}",
            "wall_ts_ms": f"{event.wall_ts_ms:.1f}",
            "snapshot_path": event.snapshot_path,
        }
        try:
            self._redis.xadd(
                config.REDIS_STREAM_PLATE_EVENTS,
                fields,
                maxlen=config.REDIS_STREAM_MAXLEN,
                approximate=True,
            )
        except redis.RedisError:
            log.exception(
                "Failed to publish plate event for camera=%s track=%s",
                event.camera_id,
                event.track_id,
            )

    def publish_camera_health(self, camera_id: str, status: str, **extra: str) -> None:
        fields = {"camera_id": camera_id, "status": status, "ts_ms": f"{time.time() * 1000:.0f}", **extra}
        try:
            self._redis.xadd(
                config.REDIS_STREAM_CAMERA_HEALTH,
                fields,
                maxlen=50_000,
                approximate=True,
            )
        except redis.RedisError:
            log.exception("Failed to publish camera_health event for camera=%s", camera_id)
