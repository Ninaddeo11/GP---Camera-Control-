"""Multi-frame OCR fusion for a single vehicle track — the piece that
turns several independent, sometimes-conflicting OCR reads of the *same*
vehicle into one confident plate string, instead of treating every frame's
OCR output as its own event.

Deliberately does NOT touch plate_normalizer.py's validation logic (no
duplicate implementation of what counts as a valid Indian plate) — it
fuses raw normalized candidates that already passed that validator, then
re-validates the fused result through the same function before returning,
so a fusion result can never itself be a format the validator would reject.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass

import config
import plate_normalizer


@dataclass(frozen=True)
class PlateObservation:
    """One normalized, already-validated plate read for a track, plus
    enough metadata to weight it against the track's other observations.
    `text`/`region` come from plate_normalizer.normalize() — never raw
    OCR output — so every observation fused here is independently a
    well-formed Indian plate string, just possibly the wrong one.
    """

    text: str
    region: str
    detector_confidence: float
    ocr_confidence: float
    quality_score: float
    engine: str
    frame_pts_ms: float

    @property
    def weight(self) -> float:
        # Detector confidence, OCR confidence, and crop quality each
        # independently affect how much this single read should be
        # trusted — multiplying them (rather than averaging) means a
        # read that's bad on any one axis contributes little, which is
        # the conservative choice for something voting on a legal
        # identifier.
        return max(0.0, self.detector_confidence) * max(0.0, self.ocr_confidence) * max(0.0, self.quality_score)


@dataclass(frozen=True)
class FusedResult:
    plate_text: str
    region: str
    confidence: float
    observations: int
    agreement: float


def _char_vote_fuse(candidates: list[PlateObservation]) -> str:
    """Position-wise weighted character voting across same-length
    candidates. Only called after the caller has already restricted
    `candidates` to one length group, so `text[i]` is defined for every
    candidate at every position.
    """
    length = len(candidates[0].text)
    fused_chars: list[str] = []
    for i in range(length):
        votes: Counter[str] = Counter()
        for obs in candidates:
            votes[obs.text[i]] += obs.weight
        fused_chars.append(max(votes.items(), key=lambda kv: kv[1])[0])
    return "".join(fused_chars)


def fuse(observations: deque[PlateObservation] | list[PlateObservation]) -> FusedResult | None:
    """Weighted temporal consensus across a track's buffered plate
    observations. Returns None if there's nothing to fuse, or if the
    fused string doesn't survive re-validation (should be rare, since
    every input observation was already valid on its own, but a
    character-vote result is not itself guaranteed to be — e.g. voting
    could pick a majority letter at a position that must be a digit).
    """
    obs_list = [o for o in observations if o.weight > 0]
    if not obs_list:
        return None

    if len(obs_list) < config.TEMPORAL_FUSION_MIN_OBSERVATIONS_FOR_PUBLISH:
        return None

    # Group by string length: a plate misread with a dropped/extra
    # character can't be fused character-by-character with correctly-read
    # ones, so pick the length group with the most total weight (i.e. the
    # length the majority of high-quality reads actually agree on) and
    # fuse within it only.
    by_length: dict[int, list[PlateObservation]] = {}
    for obs in obs_list:
        by_length.setdefault(len(obs.text), []).append(obs)
    best_length = max(by_length, key=lambda length: sum(o.weight for o in by_length[length]))
    candidates = by_length[best_length]

    if len(candidates) == 1:
        fused_text = candidates[0].text
    else:
        fused_text = _char_vote_fuse(candidates)

    normalized = plate_normalizer.normalize(fused_text)
    if normalized is None:
        # Voting produced something that doesn't parse as a valid plate —
        # fall back to the single highest-weight observation rather than
        # discarding the track's read entirely.
        best_single = max(candidates, key=lambda o: o.weight)
        fused_text, region = best_single.text, best_single.region
    else:
        fused_text, region = normalized

    agreeing = [o for o in candidates if o.text == fused_text]
    agreement = len(agreeing) / len(candidates)

    total_weight = sum(o.weight for o in candidates)
    weighted_confidence = (
        sum(o.weight * min(o.detector_confidence, o.ocr_confidence) for o in agreeing) / total_weight
        if total_weight > 0
        else 0.0
    )
    # More agreeing, independent observations should increase confidence
    # (a plate read the same way five times is more trustworthy than once),
    # bounded so it can never exceed near-certainty from repetition alone.
    observation_bonus = min(0.08, 0.02 * (len(agreeing) - 1))
    confidence = min(0.99, weighted_confidence + observation_bonus)

    return FusedResult(
        plate_text=fused_text,
        region=region,
        confidence=confidence,
        observations=len(obs_list),
        agreement=agreement,
    )


def new_buffer() -> deque[PlateObservation]:
    return deque(maxlen=config.TEMPORAL_FUSION_MAX_OBSERVATIONS)
