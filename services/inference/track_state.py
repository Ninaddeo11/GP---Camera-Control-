"""Per-vehicle-track session state and lifecycle — the module that makes
"multiple vehicles + multiple plates + poor video + temporal OCR" work
without one vehicle's plate leaking into another's event (brief section
21: "Never use global frame-level variables... All state must be keyed by
track_id"). Every piece of mutable state this upgrade adds (plate
observation buffer, best-evidence crops, classification votes) lives on a
TrackSession keyed by (camera_id, track_id) — nothing here is a shared
mutable outside that.

Lifecycle (brief section 19):

    NEW -> ACTIVE -> PLATE_OBSERVATION -> CLASSIFICATION -> CONFIRMED -> LOST -> FINALIZED

This module treats the middle four states as informational/monotonic
progress markers on one long-lived session object rather than a strict
state machine with enforced transitions — a vehicle can be CONFIRMED (has
a fused plate) on frame 3 and keep accumulating observations for another
50 frames, which is normal, not a modeling error. LOST/FINALIZED are the
only transitions that matter operationally: LOST starts a grace-period
countdown (a track missing from ByteTrack's confirmed output for one frame
is common on a noisy stream, not necessarily gone), and FINALIZED means
"this session produced its one event and its temporary state was
released" (brief section 19, "release temporary frame/track memory" — see
TrackSessionRegistry.pop, called by pipeline.py right after finalize()).
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

import config
import temporal_fusion
from temporal_fusion import FusedResult, PlateObservation

log = logging.getLogger("inference.track_state")


class TrackLifecycleState(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    PLATE_OBSERVATION = "plate_observation"
    CLASSIFICATION = "classification"
    CONFIRMED = "confirmed"
    LOST = "lost"
    FINALIZED = "finalized"


@dataclass
class _BestFrame:
    """One retained crop for a track — "best so far" by a caller-supplied
    quality score, replaced (never accumulated) as better frames arrive.
    This is the entire mechanism behind brief section 18's "do not
    permanently store every frame": at most one vehicle crop and one plate
    crop are ever held in memory per active track, regardless of how many
    frames that track has been seen in.
    """

    image: np.ndarray
    score: float
    frame_pts_ms: float


@dataclass
class ClassificationVote:
    label: str
    confidence: float
    source: str


@dataclass
class TrackSession:
    camera_id: str
    track_id: int
    state: TrackLifecycleState = TrackLifecycleState.NEW
    first_seen_wall_ts_ms: float = 0.0
    last_seen_wall_ts_ms: float = 0.0
    frames_missing: int = 0

    _class_votes: Counter[str] = field(default_factory=Counter)
    _plate_observations: "deque[PlateObservation]" = field(default_factory=temporal_fusion.new_buffer)
    _best_vehicle: _BestFrame | None = field(default=None)
    _best_plate: _BestFrame | None = field(default=None)
    manufacturer: ClassificationVote | None = field(default=None)
    model: ClassificationVote | None = field(default=None)
    _classification_attempted: bool = field(default=False)

    # Mirrors the old module-level PlateDedupState's role, but scoped to
    # this track instead of a separate dict keyed by (camera_id, track_id)
    # — same "only publish if it improves" behavior, one less collection
    # to keep in sync with track lifecycle.
    last_published_confidence: float = 0.0

    def record_detection(self, class_name: str, wall_ts_ms: float) -> None:
        if self.state == TrackLifecycleState.NEW:
            self.first_seen_wall_ts_ms = wall_ts_ms
            self.state = TrackLifecycleState.ACTIVE
        self._class_votes[class_name] += 1
        self.last_seen_wall_ts_ms = wall_ts_ms
        self.frames_missing = 0

    def record_plate_observation(self, obs: PlateObservation) -> None:
        self._plate_observations.append(obs)
        if self.state in (TrackLifecycleState.NEW, TrackLifecycleState.ACTIVE):
            self.state = TrackLifecycleState.PLATE_OBSERVATION

    def record_classification(self, manufacturer: ClassificationVote | None, model: ClassificationVote | None) -> None:
        if manufacturer is not None:
            self.manufacturer = manufacturer
        if model is not None:
            self.model = model
        if manufacturer is not None or model is not None:
            self.state = TrackLifecycleState.CLASSIFICATION

    def consider_best_vehicle_frame(self, crop: np.ndarray, score: float, frame_pts_ms: float) -> None:
        if self._best_vehicle is None or score > self._best_vehicle.score:
            self._best_vehicle = _BestFrame(image=crop, score=score, frame_pts_ms=frame_pts_ms)

    def consider_best_plate_frame(self, crop: np.ndarray, score: float, frame_pts_ms: float) -> None:
        if self._best_plate is None or score > self._best_plate.score:
            self._best_plate = _BestFrame(image=crop, score=score, frame_pts_ms=frame_pts_ms)

    @property
    def best_vehicle_image(self) -> np.ndarray | None:
        return self._best_vehicle.image if self._best_vehicle else None

    @property
    def best_plate_image(self) -> np.ndarray | None:
        return self._best_plate.image if self._best_plate else None

    def should_skip_anpr_rerun(self) -> bool:
        """Mirrors the pre-upgrade PlateDedupState.should_skip_rerun,
        scoped to this track instead of a separate module-level dict — no
        point re-running plate detection/OCR on a track that already has
        a confidently-published read.
        """
        return self.last_published_confidence >= config.ANPR_SKIP_RERUN_ABOVE_CONFIDENCE

    def should_publish_plate(self, confidence: float) -> bool:
        """Mirrors the pre-upgrade PlateDedupState.should_publish: a
        (fused) read only gets published if it beats the last published
        confidence by a meaningful margin, so a stationary vehicle doesn't
        flood plate_events with near-duplicate reads every frame.
        """
        return confidence >= self.last_published_confidence + config.ANPR_REPUBLISH_MARGIN

    def record_published_plate(self, confidence: float) -> None:
        self.last_published_confidence = max(confidence, self.last_published_confidence)

    def fused_plate(self) -> FusedResult | None:
        result = temporal_fusion.fuse(self._plate_observations)
        if result is not None and self.state not in (TrackLifecycleState.LOST, TrackLifecycleState.FINALIZED):
            self.state = TrackLifecycleState.CONFIRMED
        return result

    def majority_vehicle_class(self) -> str | None:
        if not self._class_votes:
            return None
        return self._class_votes.most_common(1)[0][0]

    @property
    def frames_observed(self) -> int:
        return sum(self._class_votes.values())

    def should_attempt_classification(self) -> bool:
        """Manufacturer/model classification runs at most once per track,
        on whatever the best vehicle crop is at that point (brief section
        16: "1-3 best vehicle crops", simplified here to the single best
        one this upgrade tracks) — not every frame, since it's pure
        enrichment on top of an already-published plate/type."""
        return (
            not self._classification_attempted
            and self.frames_observed >= config.CLASSIFICATION_MIN_FRAMES_BEFORE_ATTEMPT
            and self.best_vehicle_image is not None
        )

    def mark_classification_attempted(self) -> None:
        self._classification_attempted = True

    def mark_missing(self) -> None:
        self.frames_missing += 1
        if self.state not in (TrackLifecycleState.LOST, TrackLifecycleState.FINALIZED):
            self.state = TrackLifecycleState.LOST

    def is_finalizable(self) -> bool:
        return self.frames_missing >= config.TRACK_LOST_GRACE_FRAMES

    def finalize(self) -> "FinalizedTrack":
        self.state = TrackLifecycleState.FINALIZED
        fused = self.fused_plate()
        return FinalizedTrack(
            camera_id=self.camera_id,
            track_id=self.track_id,
            vehicle_type=self.majority_vehicle_class() or "unknown",
            vehicle_type_observations=sum(self._class_votes.values()),
            plate=fused,
            manufacturer=self.manufacturer,
            model=self.model,
            best_vehicle_image=self.best_vehicle_image,
            best_plate_image=self.best_plate_image,
            first_seen_wall_ts_ms=self.first_seen_wall_ts_ms,
            last_seen_wall_ts_ms=self.last_seen_wall_ts_ms,
        )


@dataclass(frozen=True)
class FinalizedTrack:
    """The result of TrackSession.finalize() — everything needed to build
    a VehicleEvent (events.py) and save evidence, decoupled from the
    mutable session object so it can outlive the session being discarded.
    """

    camera_id: str
    track_id: int
    vehicle_type: str
    vehicle_type_observations: int
    plate: FusedResult | None
    manufacturer: ClassificationVote | None
    model: ClassificationVote | None
    best_vehicle_image: np.ndarray | None
    best_plate_image: np.ndarray | None
    first_seen_wall_ts_ms: float
    last_seen_wall_ts_ms: float


class TrackSessionRegistry:
    """camera_id -> {track_id: TrackSession}. Never shares state across
    cameras or across tracks — mirrors tracker.py's TrackerRegistry shape
    deliberately, so the two registries stay conceptually parallel (one
    tracker + one session set per camera).
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict[int, TrackSession]] = {}

    def get_or_create(self, camera_id: str, track_id: int) -> TrackSession:
        camera_sessions = self._sessions.setdefault(camera_id, {})
        session = camera_sessions.get(track_id)
        if session is None:
            session = TrackSession(camera_id=camera_id, track_id=track_id)
            camera_sessions[track_id] = session
        return session

    def mark_seen(self, camera_id: str, seen_track_ids: set[int]) -> list[TrackSession]:
        """Call once per processed frame with the track_ids ByteTrack
        confirmed this frame. Returns sessions that just crossed the
        finalize threshold (missing for TRACK_LOST_GRACE_FRAMES
        consecutive frames) — caller is responsible for finalizing and
        then evicting them via pop().
        """
        camera_sessions = self._sessions.get(camera_id, {})
        newly_finalizable: list[TrackSession] = []
        for track_id, session in camera_sessions.items():
            if track_id in seen_track_ids:
                session.frames_missing = 0
                if session.state == TrackLifecycleState.LOST:
                    # Reappeared within the grace period — not lost after all.
                    session.state = TrackLifecycleState.CONFIRMED if session.fused_plate() else TrackLifecycleState.ACTIVE
                continue
            session.mark_missing()
            if session.is_finalizable():
                newly_finalizable.append(session)
        return newly_finalizable

    def pop(self, camera_id: str, track_id: int) -> TrackSession | None:
        camera_sessions = self._sessions.get(camera_id)
        if camera_sessions is None:
            return None
        return camera_sessions.pop(track_id, None)

    def pop_all_camera_sessions(self, camera_id: str) -> list[TrackSession]:
        """Used on reconnect/scene-discontinuity, when track IDs become
        meaningless (see tracker.py's CameraTracker.reset) — every
        in-flight session for that camera is evicted at once. Callers
        should still finalize()+publish each one first if it has a decent
        partial read, rather than silently discarding accumulated
        observations (brief section 24's "graceful degradation" applies
        here too: a reconnect shouldn't erase a vehicle event that was
        90% assembled).
        """
        sessions = list(self._sessions.pop(camera_id, {}).values())
        return sessions
