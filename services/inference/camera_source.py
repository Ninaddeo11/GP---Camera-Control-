"""RTSP frame source for one camera, consuming go2rtc's uniform RTSP
republish (`rtsp://go2rtc:8554/{camera_id}`) — never the camera's original
URL or protocol, which is exactly the point of go2rtc normalizing every
source upstream of this service.

Implements the hard ingestion constraints from the project brief:
  - RTSP over TCP only, forced globally via OPENCV_FFMPEG_CAPTURE_OPTIONS
    (set once at import time, below) — OpenCV's FFmpeg backend has no
    reliable per-VideoCapture way to force this, only this process-wide
    environment variable.
  - Timing is derived from PTS (`CAP_PROP_POS_MSEC`), never wall-clock
    arrival or the camera's reported FPS (`CAP_PROP_FPS` is read only for
    logging, never for scheduling or speed/dwell-time math downstream).
  - Non-constant frame rate and inter-frame gaps are tolerated — frames are
    paced by a target-FPS throttle, not by assuming a fixed interval.
  - A single bad/missing frame (e.g. no IDR yet at stream join) is
    non-fatal; only MAX_CONSECUTIVE_READ_FAILURES in a row triggers a
    reconnect.
  - Reconnects use exponential backoff (2s -> 4s -> ... -> 30s cap), never
    a tight loop, logging every attempt.
  - A backward or anomalously large PTS jump is reported as a scene
    discontinuity (e.g. a looping demo feed restarting) via `read()`'s
    return value, so the caller can flush tracker state — this connection
    is NOT torn down for that, since the RTSP session itself is fine.

grab()/retrieve() pattern: OpenCV's FFmpeg backend buffers internally: if
we don't grab() at least as fast as frames arrive, latency grows
unboundedly on a live stream. We always grab() every available frame and
only retrieve()+decode the one we're actually going to process, dropping
the rest — this keeps latency bounded without needing our own frame queue.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum, auto

import cv2

import config

# Must be set before any cv2.VideoCapture(..., cv2.CAP_FFMPEG) is opened —
# this is a process-wide FFmpeg option, not a per-capture one.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

log = logging.getLogger("inference.camera_source")


class FrameStatus(Enum):
    OK = auto()
    NO_FRAME = auto()  # transient — did not reach MAX_CONSECUTIVE_READ_FAILURES
    DISCONNECTED = auto()  # exceeded failure tolerance; caller should reconnect
    DISCONTINUITY = auto()  # frame is valid but PTS jumped — flush tracker state


@dataclass
class Frame:
    image: "cv2.Mat"
    pts_ms: float
    wall_ts_ms: float


def rtsp_url(camera_id: str) -> str:
    return f"rtsp://{config.GO2RTC_RTSP_HOST}:{config.GO2RTC_RTSP_PORT}/{camera_id}"


class CameraSource:
    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self._cap: cv2.VideoCapture | None = None
        self._consecutive_failures = 0
        self._last_pts_ms: float | None = None
        self._reconnect_attempt = 0
        self._next_reconnect_at = 0.0
        self._min_frame_interval_ms = 1000.0 / config.TARGET_FPS_PER_CAMERA
        self._last_processed_wall_ms = 0.0

    # -- connection lifecycle -----------------------------------------------

    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def connect(self) -> bool:
        url = rtsp_url(self.camera_id)
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        # Best-effort: not every backend honors this, but when it does it
        # caps FFmpeg's internal buffer so a slow consumer doesn't build up
        # latency on top of our own grab()-draining below.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            cap.release()
            self._cap = None
            return False

        self._cap = cap
        self._consecutive_failures = 0
        self._last_pts_ms = None
        reported_fps = cap.get(cv2.CAP_PROP_FPS)
        log.info(
            "camera=%s connected url=%s reported_fps=%.1f (informational only — "
            "never used for timing)",
            self.camera_id,
            url,
            reported_fps,
        )
        return True

    def disconnect(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def should_attempt_reconnect(self) -> bool:
        return time.monotonic() >= self._next_reconnect_at

    def schedule_reconnect(self) -> float:
        """Advances the backoff state and returns the delay (seconds) until
        the next attempt is due. Logs every attempt, per the hard
        ingestion constraint on reconnect behavior.
        """
        self._reconnect_attempt += 1
        backoff = min(
            config.RECONNECT_BACKOFF_INITIAL_SECONDS * (2 ** (self._reconnect_attempt - 1)),
            config.RECONNECT_BACKOFF_MAX_SECONDS,
        )
        self._next_reconnect_at = time.monotonic() + backoff
        log.warning(
            "camera=%s reconnect attempt #%d (next retry in %.0fs)",
            self.camera_id,
            self._reconnect_attempt,
            backoff,
        )
        return backoff

    def note_connected(self) -> None:
        self._reconnect_attempt = 0

    # -- frame reading --------------------------------------------------------

    def read(self) -> tuple[FrameStatus, Frame | None]:
        """Drains any buffered frames via grab(), decodes only the most
        recent one, and paces decoding to TARGET_FPS_PER_CAMERA. Returns
        DISCONTINUITY (with the frame still returned) when PTS indicates a
        scene cut — the caller should flush tracker state but keep reading.
        """
        if self._cap is None:
            return FrameStatus.DISCONNECTED, None

        now_ms = time.monotonic() * 1000.0
        if now_ms - self._last_processed_wall_ms < self._min_frame_interval_ms:
            # Still grab (and discard) to drain the decoder buffer and keep
            # latency from drifting, without spending time on a full decode.
            self._cap.grab()
            return FrameStatus.NO_FRAME, None

        ok = self._cap.grab()
        if not ok:
            return self._on_read_failure()

        ok, image = self._cap.retrieve()
        if not ok or image is None:
            return self._on_read_failure()

        self._consecutive_failures = 0
        self._last_processed_wall_ms = now_ms

        pts_ms = self._cap.get(cv2.CAP_PROP_POS_MSEC)
        discontinuity = self._detect_discontinuity(pts_ms)
        self._last_pts_ms = pts_ms

        frame = Frame(image=image, pts_ms=pts_ms, wall_ts_ms=time.time() * 1000.0)
        return (FrameStatus.DISCONTINUITY if discontinuity else FrameStatus.OK), frame

    def _detect_discontinuity(self, pts_ms: float) -> bool:
        if self._last_pts_ms is None:
            return False
        delta = pts_ms - self._last_pts_ms
        # A backward jump (feed restarted) or an implausibly large forward
        # jump (long stall masking a restart) both count — a normal
        # variable-frame-rate gap does not, which is why this threshold is
        # generous rather than tied to the target FPS interval.
        return delta < 0 or delta > config.DISCONTINUITY_GAP_MS

    def _on_read_failure(self) -> tuple[FrameStatus, None]:
        self._consecutive_failures += 1
        if self._consecutive_failures >= config.MAX_CONSECUTIVE_READ_FAILURES:
            log.warning(
                "camera=%s %d consecutive failed reads — treating as disconnected",
                self.camera_id,
                self._consecutive_failures,
            )
            self.disconnect()
            return FrameStatus.DISCONNECTED, None
        # Below tolerance: a decoder warning or missing reference frame at
        # stream join is normal and non-fatal — just try again next loop.
        return FrameStatus.NO_FRAME, None
