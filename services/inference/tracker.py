"""Per-camera ByteTrack, using ultralytics' own BYTETracker implementation
rather than a second, hand-maintained tracking stack — per the project
brief: "use via ultralytics' built-in ByteTrack integration rather than
the standalone repo."

Why not `model.track()`: ultralytics' high-level `.track()` convenience
method is the officially stable public API, but it owns its own RTSP
source loading internally and keys tracker state by stream index in a way
that isn't designed for cameras being added/removed at runtime from an
external catalogue (see camera_source.py, which needs to own the RTSP
connection itself for PTS extraction, reconnect/backoff, and scene-
discontinuity detection). So this module drives `ultralytics.trackers
.byte_tracker.BYTETracker` directly, one instance per camera_id, isolated
in TrackerRegistry.

IMPORTANT — pinned-version assumption: `BYTETracker.update()` is not part
of ultralytics' documented public API surface; it's the same internal call
`.track()` makes under the hood. This module assumes, as of
ultralytics==8.3.40 (pinned in requirements.txt):
  - `update(detections, img)` accepts an object exposing `.conf` (N,),
    `.cls` (N,), and `.xywh` (N,4) as numpy arrays.
  - It returns an (M, 8) numpy array of confirmed tracks, columns
    `[x1, y1, x2, y2, track_id, score, cls, source_detection_index]`.
If a future ultralytics upgrade changes this shape, `_validate_track_output`
below logs a specific, actionable error instead of silently mis-tracking —
check that function first when upgrading the pin.

The riskier assumption is on the INPUT side (`_DetectionBoxes`, i.e. that
`.xywh`/`.conf`/`.cls` are the attribute names and shapes BYTETracker reads)
since a wrong input shape there could produce plausible-looking but wrong
track IDs rather than a clean crash. Before trusting this in the real
deployment, verify it once by running `model.track(one_test_frame,
tracker="bytetrack.yaml")` through ultralytics' own high-level API on the
same frame and confirming the track IDs/boxes match what this module
produces via `CameraTracker.update()` on the same detections.
"""

from __future__ import annotations

import logging

import numpy as np
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import IterableSimpleNamespace, yaml_load
from ultralytics.utils.checks import check_yaml

import config
from events import Detection, TrackedObject

log = logging.getLogger("inference.tracker")

# Stable local class encoding — only needs to be internally consistent
# (BYTETracker doesn't interpret the values, it just carries them through),
# so it need not match COCO's own class ids.
_CLASS_NAMES = sorted(config.VEHICLE_CLASS_NAMES | {config.PERSON_CLASS_NAME})
_CLASS_NAME_TO_ID = {name: i for i, name in enumerate(_CLASS_NAMES)}
_ID_TO_CLASS_NAME = {i: name for name, i in _CLASS_NAME_TO_ID.items()}

_EXPECTED_OUTPUT_COLUMNS = 8


def _load_tracker_args() -> IterableSimpleNamespace:
    cfg = yaml_load(check_yaml(config.TRACKER_CONFIG))
    return IterableSimpleNamespace(**cfg)


class _DetectionBoxes:
    """Minimal stand-in for ultralytics' `Boxes` object — the subset of
    its interface BYTETracker.update() actually reads. See module
    docstring for the exact assumed contract.
    """

    def __init__(self, detections: list[Detection]) -> None:
        n = len(detections)
        if n == 0:
            self.conf = np.zeros((0,), dtype=np.float32)
            self.cls = np.zeros((0,), dtype=np.float32)
            self.xywh = np.zeros((0, 4), dtype=np.float32)
            return

        self.conf = np.array([d.confidence for d in detections], dtype=np.float32)
        self.cls = np.array(
            [_CLASS_NAME_TO_ID[d.class_name] for d in detections], dtype=np.float32
        )
        xywh = []
        for d in detections:
            x1, y1, x2, y2 = d.bbox_xyxy
            w, h = x2 - x1, y2 - y1
            xywh.append((x1 + w / 2.0, y1 + h / 2.0, w, h))
        self.xywh = np.array(xywh, dtype=np.float32)

    def __len__(self) -> int:
        return len(self.conf)


def _validate_track_output(output: np.ndarray) -> bool:
    if output.ndim != 2 or output.shape[1] != _EXPECTED_OUTPUT_COLUMNS:
        log.error(
            "BYTETracker.update() returned shape %s, expected (N, %d) columns "
            "[x1,y1,x2,y2,track_id,score,cls,det_idx]. The pinned ultralytics "
            "version's internal tracker contract may have changed — see "
            "tracker.py's module docstring. Tracking is disabled for this "
            "frame; detections are still being produced, just without track IDs.",
            output.shape,
            _EXPECTED_OUTPUT_COLUMNS,
        )
        return False
    return True


class CameraTracker:
    """Wraps one BYTETracker instance for exactly one camera."""

    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self._tracker = BYTETracker(args=_load_tracker_args(), frame_rate=int(config.TARGET_FPS_PER_CAMERA))

    def update(
        self, detections: list[Detection], frame, frame_pts_ms: float, wall_ts_ms: float
    ) -> list[TrackedObject]:
        # Even with zero detections, update() is still called (with an
        # empty batch) so ByteTrack's own internal ageing/removal of stale
        # tracks progresses on frames with nothing detected.
        boxes = _DetectionBoxes(detections)

        try:
            output = self._tracker.update(boxes, frame)
        except Exception:
            log.exception(
                "camera=%s BYTETracker.update() raised — see tracker.py module "
                "docstring for the assumed ultralytics contract",
                self.camera_id,
            )
            return []

        output = np.asarray(output)
        if output.size == 0:
            return []
        if not _validate_track_output(output):
            return []

        tracked: list[TrackedObject] = []
        for row in output:
            x1, y1, x2, y2, track_id, score, cls_id, _det_idx = row[:8]
            class_name = _ID_TO_CLASS_NAME.get(int(cls_id), "unknown")
            tracked.append(
                TrackedObject(
                    track_id=int(track_id),
                    camera_id=self.camera_id,
                    bbox_xyxy=(float(x1), float(y1), float(x2), float(y2)),
                    class_name=class_name,
                    confidence=float(score),
                    frame_pts_ms=frame_pts_ms,
                    wall_ts_ms=wall_ts_ms,
                )
            )
        return tracked

    def reset(self, reason: str) -> None:
        """Flush all track state. Called on reconnect (stream_manager-level
        discontinuity) and on an in-stream scene discontinuity (e.g. a
        looping demo feed cutting back to its start) — a fresh tracker
        with no memory of prior tracks, not a resume.
        """
        log.info("camera=%s resetting tracker (%s)", self.camera_id, reason)
        self._tracker = BYTETracker(args=_load_tracker_args(), frame_rate=int(config.TARGET_FPS_PER_CAMERA))


class TrackerRegistry:
    """camera_id -> CameraTracker. Never shares state across cameras."""

    def __init__(self) -> None:
        self._trackers: dict[str, CameraTracker] = {}

    def get(self, camera_id: str) -> CameraTracker:
        tracker = self._trackers.get(camera_id)
        if tracker is None:
            tracker = CameraTracker(camera_id)
            self._trackers[camera_id] = tracker
        return tracker

    def remove(self, camera_id: str) -> None:
        self._trackers.pop(camera_id, None)
