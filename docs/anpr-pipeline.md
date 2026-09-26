# Multi-vehicle ANPR pipeline

This documents the upgraded `services/inference` pipeline: RTSP ingestion
through detection, tracking, plate recognition, temporal fusion, vehicle
classification, and event storage. It supersedes the short "Phase 5 — ANPR
pipeline" description in the main README with the full picture; the
README entry still exists as the changelog-style pointer to this file.

Every stage below already exists in code — nothing here is aspirational.
Where a stage depends on a model this repo doesn't ship (plate detector
weights, manufacturer/model classifier weights), that's called out
explicitly, matching the existing "ANPR model gap" pattern from Phase 5.

## End-to-end flow

```
RTSP (go2rtc republish)
        │
        ▼
CameraSource (services/inference/camera_source.py)
  OpenCV/FFmpeg pull, PTS-paced, drop-oldest — no unbounded frame queue
        │
        ▼
Detector.predict()  (detector.py)
  YOLO11, per frame, returns list[Detection] — 0..N vehicles/persons
        │
        ▼
CameraTracker.update()  (tracker.py)
  ByteTrack, per camera — assigns persistent track_id per vehicle
        │
        ├──────────────────────────────────────────────┐
        ▼                                               ▼
TrackSession.record_detection()                 (for each tracked vehicle)
  (track_state.py — keyed by camera_id+track_id)  vehicle crop
        │                                               │
        │                                               ▼
        │                                    AnprEngine.process()  (anpr.py)
        │                                      plate_detector.py: localize plate
        │                                      plate_quality.py: assess + enhance
        │                                      ocr_engine.py: PaddleOCR (primary)
        │                                      ocr_fallback.py: EasyOCR (only if uncertain)
        │                                      plate_normalizer.py: validate + correct
        │                                               │
        │                                               ▼
        │                                    TrackSession.record_plate_observation()
        │                                               │
        │                                               ▼
        │                                    temporal_fusion.fuse()
        │                                      weighted character-vote consensus
        │                                      across this track's observation buffer
        │                                               │
        │                          ┌────────────────────┤
        │                          ▼                    │
        │                 publish PlateEvent             │
        │                 (real-time, per improvement)   │
        │                                                │
        ▼                                                ▼
vehicle_classifier.py (best vehicle crop, once per track)
  ManufacturerClassifier / ModelClassifier / MakeModelVlmAdapter
        │
        ▼
track lost for TRACK_LOST_GRACE_FRAMES consecutive frames
        │
        ▼
TrackSession.finalize()  ->  FinalizedTrack
        │
        ▼
publish VehicleEvent (one consolidated event per completed sighting)
        │
        ▼
services/api: plate_event_consumer.py + vehicle_event_consumer.py
  Redis Streams -> Postgres (plate_events, vehicle_events)
        │
        ▼
GET /tracking/recent, GET /tracking/vehicle-events/recent,
GET /tracking/plate/{plate}, watchlist_engine.py (plate_events only)
```

## Two event streams, two purposes

- **`plate_events`** (Redis Stream, existing since Phase 5/6) — one
  message per *published improvement* in a track's fused plate read.
  Unchanged in shape and timing semantics by this upgrade: watchlist
  matching (`services/api/services/watchlist_engine.py`) and
  `GET /tracking/plate/{plate}` both depend on this staying low-latency,
  so it is never deferred until a vehicle leaves the frame. What changed
  is *what* gets published — the fused, multi-observation consensus
  (`temporal_fusion.fuse()`) instead of a single frame's raw OCR output.
- **`vehicle_events`** (Redis Stream, new) — exactly one message per
  *finalized* track: vehicle type (majority vote across every frame the
  track was seen in), manufacturer/model (enrichment, may be "Unknown"),
  the final fused plate, and paths to the two retained evidence images.
  Persisted into the new `vehicle_events` Postgres table by
  `services/api/services/vehicle_event_consumer.py`, exposed at
  `GET /tracking/vehicle-events/recent`.

## Track lifecycle

```
NEW -> ACTIVE -> PLATE_OBSERVATION -> CLASSIFICATION -> CONFIRMED -> LOST -> FINALIZED
```

Implemented in `services/inference/track_state.py`. All mutable state
(plate observation buffer, best vehicle/plate crop, classification votes)
lives on one `TrackSession` object keyed by `(camera_id, track_id)` — see
that module's docstring for why this is the mechanism that keeps multiple
simultaneous vehicles from contaminating each other's state. A track
missing from ByteTrack's confirmed output for `TRACK_LOST_GRACE_FRAMES`
consecutive frames (default 10) is finalized: one `VehicleEvent` is
published, and its `TrackSession` is discarded — this is also the entire
memory-bounding mechanism (brief section 18): at most one vehicle crop,
one plate crop, and `TEMPORAL_FUSION_MAX_OBSERVATIONS` (default 20)
lightweight plate-read records are ever held per active track, regardless
of how many frames it's been visible for.

## Temporal OCR fusion

`services/inference/temporal_fusion.py`. Every OCR read that passes plate
validation (`plate_normalizer.normalize()`) is appended to its track's
observation buffer as a `PlateObservation`, weighted by
`detector_confidence * ocr_confidence * quality_score`. `fuse()`:

1. Groups observations by string length (a misread with a dropped/extra
   character can't be voted character-by-character against a
   correctly-length read).
2. Picks the length group with the most total weight.
3. Within that group, does position-wise weighted character voting.
4. Re-validates the voted-on string through `plate_normalizer.normalize()`
   (falls back to the single highest-weight observation if voting produces
   something that doesn't parse).
5. Reports `agreement` (fraction of the winning group's observations that
   exactly matched the fused text) and a confidence that rewards — but
   caps — having more corroborating observations.

## Plate quality and OCR

`services/inference/plate_quality.py` gates a plate crop on sharpness
(Laplacian variance), size, and contrast before it's ever sent to OCR, and
applies CLAHE/sharpening/upscaling (each independently toggleable). OCR
runs `ocr_engine.py` (PaddleOCR) first; `ocr_fallback.py` (EasyOCR) only
runs when PaddleOCR's result is missing or below
`OCR_SECONDARY_TRIGGER_BELOW_CONFIDENCE` — never both engines on every
crop.

`plate_normalizer.py` validates against two formats: standard
(`SS DD L[LL] DDDD`) and Bharat/BH-series (`YY BH DDDD L[L]`), plus a
bounded set of visually-confusable single-character corrections
(0/O, 1/I, 8/B, 5/S, 2/Z) — only ever applied when it turns an otherwise-
invalid string into a valid one.

## Vehicle classification (enrichment, not a dependency)

`services/inference/vehicle_classifier.py`. Vehicle *type* is not handled
here — it's the YOLO detector's own class name
(car/truck/bus/motorcycle), majority-voted across a track's frames in
`track_state.py`, which is real and already working. Manufacturer and
model recognition are separate, optional classifiers that run at most
once per track, on its single best-quality vehicle crop:

- `ManufacturerClassifier` / `ModelClassifier` — same graceful-disable
  pattern as `plate_detector.py`: if
  `MANUFACTURER_MODEL_PATH`/`VEHICLE_MODEL_CLASSIFIER_PATH` doesn't exist,
  the classifier reports itself unavailable and `classify()` always
  returns `None` (never a fabricated label).
- `MakeModelVlmAdapter` — interface for a local `MakeModel-VLM-450M`
  (or compatible) model as a secondary signal for model recognition only.
  Never downloads from Hugging Face; only activates against a local model
  directory. The real `generate()`/parsing call is not implemented (no
  local copy of the model exists in this environment to test against) —
  everything around it (availability check, `classify()` signature,
  confidence arbitration) is, so dropping in that one call is what's left
  to activate it.
- `merge_with_priority()` — a fallback result (e.g. the VLM) can never
  override a `"high"`-confidence primary result; it's only used when the
  primary is missing or itself below `"high"` and the fallback is more
  confident.

**No fine-tuned manufacturer/model classifier ships in this repo** —
training one needs a labeled Indian-vehicle dataset this environment can't
produce, matching the existing plate-detector gap. This enrichment stage
is disabled by default in effect (both classifiers report `available =
False`) until real weights are dropped in at the configured paths.

## Confidence policy

Every classification result carries a tier via
`vehicle_classifier.confidence_tier()`:
`>= CLASSIFIER_HIGH_CONFIDENCE_THRESHOLD` (0.85) → `"high"`,
`>= CLASSIFIER_PROBABLE_CONFIDENCE_THRESHOLD` (0.60) → `"probable"`,
else `"unknown"`. A `VehicleEvent` can legitimately have a high-confidence
plate, a high-confidence vehicle type, and an empty manufacturer/model —
that's a successful event, not a partial failure (brief section 24):
finalize() always runs and always publishes, regardless of which
lower-priority stages produced nothing.

## Configuration

All new knobs follow the existing per-service pattern
(`services/inference/config.py`: flat module constants read from
`os.environ`, no pydantic) — see that file's "multi-vehicle ANPR upgrade"
sections, and `.env.example` for the full list with defaults and
rationale. `services/api/config.py` gained
`redis_stream_vehicle_events` and `evidence_retention_days`.

## Storage and retention

`services/inference/snapshot.py:save_track_evidence()` writes at most two
JPEGs per finalized track (`best_vehicle_frame`, `best_plate_crop`),
independent of `save()`'s existing per-published-plate-read snapshots.
Neither this project's per-read snapshots nor `vehicle_events` evidence
were ever automatically deleted before this upgrade (see README "Known
gaps"); `services/api/scripts/cleanup_expired_evidence.py` now exists to
delete rows/files older than `EVIDENCE_RETENTION_DAYS`, run via cron —
deliberately not a background task inside the API process, since a
filesystem walk doesn't belong sharing an event loop with request handling
and the Streams consumers. It is not scheduled automatically anywhere in
this repo yet; wiring it into a cron container/host crontab is a
deployment-time decision left open.

## Testing

`services/inference/tests/` (pytest; see `requirements-dev.txt`). No real
CCTV footage or trained model weights exist in this repo, so these are
unit tests against the pure logic layers that don't need either:

- `test_plate_normalizer.py` — standard + BH-series formats, confusable
  correction, rejection of garbage input.
- `test_temporal_fusion.py` — the brief's own worked multi-observation
  example, minority-misread rejection, cross-length-group isolation,
  confidence scaling with observation count, and explicit multi-track
  independence.
- `test_plate_quality.py` — sharp-vs-blurry and small-vs-usable scoring
  relationships on synthetic images.
- `test_track_state.py` — full lifecycle transitions, grace-period
  finalization, multi-vehicle/multi-camera independent state, bounded
  best-frame retention, and the publish-dedup/skip-rerun logic.
- `test_vehicle_classifier.py` — confidence tiering and the
  fallback-must-not-override-a-confident-primary rule.

Run with:

```
cd services/inference
pip install -r requirements-dev.txt  # + requirements.txt for a full env
pytest
```

**Not covered by this suite, and not verifiable in this sandbox** (no
Docker, GPU, real camera feed, or trained model weights available): the
actual YOLO plate detector's accuracy, PaddleOCR/EasyOCR's real-world
recognition rate on Indian plates, ByteTrack's ID-persistence behavior end
to end, and the full pipeline wired together against live RTSP. See
"Performance report" below and the top-level README's "Known gaps".

## Performance report

Per the upgrade brief: input FPS, processing FPS, per-stage inference
latency, GPU/CPU utilization, memory usage, and storage-per-1000-events
**cannot be measured in this environment** — there is no Docker runtime,
GPU, or live/recorded camera feed available in this sandbox, and
`scripts/benchmark.py` (mentioned in the main README) has never been run
here either. Reporting fabricated numbers would be worse than reporting
none. To produce real numbers: deploy via `docker compose up`, point at
either the bundled demo RTSP streams or a real feed, and run against the
new Prometheus metrics this upgrade adds
(`sentinelgrid_plate_observations_total`,
`sentinelgrid_vehicle_classifications_total`,
`sentinelgrid_vehicle_events_finalized_total`, alongside the existing
`sentinelgrid_inference_latency_seconds` histogram) plus
`sentinelgrid_plate_events_persisted_total` /
`sentinelgrid_vehicle_events_persisted_total` on the API side.
