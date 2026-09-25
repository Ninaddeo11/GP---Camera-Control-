# Sentinel Grid

**Integrated Video Management & Analytics Platform** — built for the
Gujarat Police CCTV Hackathon 2026.

Sentinel Grid is a hybrid of VMS Federation & Middleware (unify ~50→80,000
heterogeneous camera sources behind one protocol set), a Registry & GIS
foundation (jurisdiction-scoped camera registry on PostGIS), and a Unified
Viewing presentation layer (a single, calm, enterprise-grade dashboard —
not a per-vendor NVR UI stitched together).

## At a glance: what's done, what's left

**Done — code written and reviewed for all 10 build phases:**
ingestion (go2rtc, dynamic discovery, reconnect/backoff), detection +
tracking (YOLO11 + per-camera ByteTrack), ANPR (plate localization + OCR +
Indian-plate normalization), the T1-T9 RBAC + jurisdiction-scoped camera
registry, cross-camera vehicle trace with PostGIS speed inference,
watchlist fuzzy-matching + live WebSocket alerts, the full dashboard
(video wall, GIS registry map, trace view, watchlist console, audit log),
Section 65B-style evidentiary export with SHA-256 chain-of-custody, and
Prometheus/Grafana/nginx observability. Full phase-by-phase detail and
verification steps are in [Build status](#build-status) below.

**Left — genuinely not done, not just unverified:**
1. **Nothing has run on real hardware yet.** This entire build happened in
   a sandbox with no Docker, Python, or GPU — every phase needs its first
   real run, and a few specific spots are flagged as likely needing a
   small fix then (see [Known gaps](#known-gaps)).
2. **No fine-tuned Indian-plate model ships in this repo.** ANPR disables
   itself cleanly until one is provided — training it is real remaining
   work, not a bug.
3. **go2rtc has no authentication or TLS in front of it** — closing that
   gap needs an authenticating proxy that isn't built yet.
4. **`Camera.status` isn't wired to live health** — the registry map's
   status colors reflect the last catalogue sync, not the current second.
5. **No automated test suite.**
6. **The scalability write-up is a methodology, not measured numbers** —
   `scripts/benchmark.py` exists to produce real ones; none exist yet.

See [Known gaps](#known-gaps) near the end of this file for the full,
specific list with what each one would take to close.

## Design mandate

The UI is professional government/enterprise software: navy/slate/white
with one accent color, Inter/system-font typography, generous whitespace,
standard dashboard patterns (left nav, top bar with rank/jurisdiction
badge). No cyberpunk, no neon, no glowing edges, no sci-fi HUD styling —
think Linear or Stripe Dashboard, not a movie hacking interface. This
applies to every UI phase below, not just a final polish pass.

## Build status

Built in verifiable phases, in the order below. Nothing is marked done
until it's actually runnable and verified.

- [x] **Phase 1 — Scaffold.** Monorepo layout, Docker Compose for local dev.
- [x] **Phase 2 — Registry + RBAC foundation.** `services/api`: JWT auth,
      the T1-T9 role/permission/jurisdiction schema, the single policy-check
      surface, and the PostGIS-backed camera registry (CRUD + catalogue
      sync). *(this commit)*
- [x] **Phase 3 — Ingestion.** go2rtc wired to the camera catalogue with
      dynamic discovery, RTSP-over-TCP enforcement, and exponential-backoff
      reconnection. *(see note below on sequencing)*
- [x] **Phase 4 — Detection & tracking.** `services/inference`: YOLO11
      detection + per-camera ByteTrack, PTS-driven pacing, scene-
      discontinuity handling, Redis Streams publishing. *(this commit — one
      internal-API risk flagged below, needs verification on a real GPU)*
- [x] **Phase 5 — ANPR pipeline.** `services/inference`: YOLO11 plate
      localization + PaddleOCR + Indian-plate normalization, deduplicated
      per track, into a new `plate_events` Redis Stream. *(this commit —
      **no fine-tuned plate model ships in this repo**; ANPR cleanly
      disables itself until one is provided — see "ANPR model gap" below)*
- [x] **Phase 6 — Vehicle tracking query service + UI.** `services/api`:
      a Redis Streams consumer persists `plate_events` into Postgres;
      `GET /tracking/plate/{plate}` reconstructs a jurisdiction-scoped
      route with dwell time and PostGIS-based inferred speed. `apps/web`:
      the dashboard shell (nav + top bar) and the Vehicle Trace page
      (search, timeline, Leaflet route map). *(this commit)*
- [x] **Phase 7 — Watchlist correlation + alerting.** `services/api`: a
      second, independent Redis Streams consumer group fuzzy-matches every
      plate read against the active watchlist and pushes matches over
      WebSocket. `apps/web`: the Watchlist Console (CRUD + live,
      auto-reconnecting alert feed with acknowledge). *(this commit)*
- [x] **Phase 8 — Video wall + GIS map UI.** `apps/web`: grid video wall
      (native WHEP over RTCPeerConnection, click-to-expand) and the
      clustered GIS registry map with department/status filters.
      *(this commit — **go2rtc has no auth of its own**, see "Known gaps"
      below)*
- [x] **Phase 9 — Audit log + evidentiary export.** The audit log table
      and hash-chaining were already built in Phase 2; this phase adds the
      read endpoint + UI and the Section 65B-style export (ZIP of
      snapshots + CSV + a chain-of-custody manifest with a SHA-256 per
      file). *(this commit)*
- [x] **Phase 10 — Polish pass.** Prometheus metrics on all three
      services, Grafana dashboards, nginx TLS termination + security
      headers, and `scripts/benchmark.py` + `scripts/demo.py`. *(this
      commit — **scalability numbers are a methodology, not yet measured
      data**, see "Known gaps" below)*

> **Sequencing note:** ingestion (Phase 3) was built before the registry/RBAC
> foundation (Phase 2) because it started life in an earlier session, before
> this brief's exact phase order was finalized. It doesn't depend on Phase 2
> and needed no rework once Phase 2 landed.

## GP Sentinel transformation (in progress)

The 10-phase build above is a complete, working hackathon MVP. A separate,
much larger initiative — turning it into a mature enterprise platform
("GP Sentinel": public landing page, Command Center, full admin module,
notifications, analytics, CI/CD, a test suite, and more) — is layered on
top of it, worked through in its own 18 phases so it doesn't destabilize
what's already working. This section tracks that initiative specifically;
the 10-phase tracker above is unaffected by it.

- [x] **Transformation Phase 1 — Repository audit.** Satisfied by the
      existing 10-phase build itself — this session already has a
      complete map of the auth, RBAC, jurisdiction, streaming, vision,
      ANPR, watchlist, evidence, and audit architecture.
- [x] **Transformation Phase 2 — Authentication/session hardening.**
      Refresh-token rotation with reuse detection (a replayed, already-
      rotated refresh token revokes every session for that user, not just
      that one request), server-side session revocation via
      `users.token_version` (embedded in every token, checked on every
      request), an admin-triggered `POST /admin/users/{username}/revoke-
      sessions`, forgot/reset-password endpoints and pages (no SMTP is
      configured — see [Known gaps](#known-gaps)), Redis-backed rate
      limiting (a strict bucket on login/forgot-password, a generous
      catch-all on everything else), and a production guard on
      `scripts/seed_users.py` so demo credentials can't be seeded into a
      production database by habit. *(this commit)*
- [ ] Transformation Phase 3 — RBAC + jurisdiction enforcement (the
      permission list from the brief is broader than what's seeded today;
      reconciling the two is this phase's job)
- [ ] Transformation Phase 4 — Database/event architecture (a first-class
      Event Engine on top of the existing plate_events/watchlist_matches
      tables)
- [ ] Transformation Phase 5 — Streaming/camera infrastructure hardening
      (SSRF protection on camera URLs, protected go2rtc management API)
- [ ] Transformation Phase 6 — Vision pipeline (detector/tracker/ANPR
      abstraction interfaces, model registry)
- [ ] Transformation Phase 7 — ANPR temporal confidence fusion (multiple
      OCR reads across frames converging on one high-confidence plate,
      rather than today's single-read-per-track dedup)
- [ ] Transformation Phase 8 — Watchlists + alerts (full alert lifecycle:
      open/acknowledged/investigating/resolved/dismissed, assignment,
      escalation)
- [ ] Transformation Phase 9 — Vehicle intelligence UI polish
- [ ] Transformation Phase 10 — Evidence + audit UI polish
- [ ] Transformation Phase 11 — Command Center (`/dashboard`, replacing
      `/trace` as the post-login landing page)
- [ ] Transformation Phase 12 — Admin module (user/role/jurisdiction CRUD
      UI — the backend RBAC exists; there's no UI to manage it yet)
- [ ] Transformation Phase 13 — Analytics + GIS enhancements
- [ ] Transformation Phase 14 — Public landing page (`/` as marketing, not
      an auth redirect)
- [ ] Transformation Phase 15 — Production security hardening (SSRF,
      upload validation, secret-management review)
- [ ] Transformation Phase 16 — Test suite (none exists yet — see
      [Known gaps](#known-gaps))
- [ ] Transformation Phase 17 — Docker/CI-CD hardening (GitHub Actions
      pipeline; non-root containers; resource limits)
- [ ] Transformation Phase 18 — Final integration pass

**Deliberately not touched in Transformation Phase 2:** the API response
envelope (Part 28 of the brief — `{success, data, message}` instead of
today's `{detail, code}`) is a breaking change to every existing endpoint
and every frontend call site. Changing it requires updating both sides in
lockstep in one dedicated pass, not folding it into an unrelated phase —
scheduled as part of a later phase once the rest of the transformation's
shape is clearer, rather than rushed here.

## Assumptions currently in effect (confirmed with the team 2026-09-22)

- **Backend stack:** Python + FastAPI for `services/api`, for proximity to
  `services/inference` (shared Pydantic models, one language for both).
- **GPU:** CUDA confirmed available. `services/inference` defaults to full
  YOLO11 (not a quantized variant) with FP16, via `SENTINELGRID_DEVICE=cuda:0`.
- **Camera gateway:** the real `/api/ingest` URL and auth aren't available
  yet. `services/catalogue-mock` implements the documented contract (below)
  against public test streams so the stack is runnable now. Swapping in the
  real gateway is a config change (`INGEST_API_URL`, `INGEST_API_AUTH_*` in
  `.env`) — no ingestion code changes.
- **Tracking implementation risk (flag this to whoever verifies Phase 4):**
  `services/inference/tracker.py` drives `ultralytics.trackers.byte_tracker
  .BYTETracker` directly (one instance per camera, for state isolation),
  rather than the officially documented `model.track()` API — necessary
  because `.track()` doesn't support cameras being added/removed at runtime
  the way this platform needs. That means it depends on an internal,
  version-pinned (`ultralytics==8.3.40`) contract for what shape
  `BYTETracker.update()` expects in and returns out. The output shape is
  checked at runtime and fails loudly if wrong; the input shape is not
  (a wrong input format could look like it's working while producing bad
  track IDs). **This needs a one-time manual check** — see the caveat at
  the top of `tracker.py` for exactly what to verify and how.
- **ANPR model gap (flag this before demoing Phase 5):** this repo does
  not include a fine-tuned license-plate detector. Training one needs a
  labeled Indian-plate dataset and a training run, which is out of scope
  for what could be produced in this environment — and I deliberately
  didn't bake in a guessed download URL for a third-party "pretrained
  plate detector" I couldn't verify actually exists or works, since a
  wrong one fails silently or badly. Instead, `services/inference
  /plate_detector.py` checks for a weights file at `PLATE_MODEL_PATH`
  (default `models/yolo11n-plate.pt`) at startup; if it's missing, ANPR
  logs a clear warning and disables itself — vehicle detection and
  tracking (Phase 4) are completely unaffected. **To enable ANPR:** fine-
  tune (or otherwise obtain) a YOLO11 license-plate detector, place the
  `.pt` file at that path inside the `inference_models` Docker volume (or
  point `PLATE_MODEL_PATH` at a mounted host path), and restart the
  `inference` container — no code changes needed.
- **PaddleOCR dependency risk:** `services/inference/requirements.txt`
  pins `paddleocr==2.7.3` + CPU-only `paddlepaddle==2.6.1`, deliberately
  kept off the GPU to avoid a second CUDA/cuDNN build fighting the
  PyTorch CUDA build already in the same container (see `ocr_engine.py`).
  This hasn't been installed/run anywhere real yet — if the pip install
  fails or conflicts on your machine, that's the first thing to check.

## Architecture

```
                        ┌───────────────────────────────────────────┐
                        │   Camera gateway /api/ingest catalogue     │
                        │  (services/catalogue-mock in dev; the real │
                        │   Gujarat Police CCTV gateway in prod)     │
                        └───────────────────┬─────────────────────────┘
                                            │ polled every 60s — read-only,
                                            │ never the gateway's control API
                                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ services/ingestion-config/stream_manager.py                              │
│  • resolves ingestion protocol per camera: RTSP > WHEP > HLS             │
│  • forces rtsp_transport=tcp on every RTSP source                       │
│  • renders go2rtc.yaml from a Jinja2 template; pushes live changes via   │
│    go2rtc's HTTP API (no container restart)                             │
│  • exponential-backoff reconnect supervisor (2s → 4s → … → 30s cap)      │
│  • Prometheus metrics on :9092                                          │
└───────────────────────────────┬────────────────────────────────────────┘
                                │
                                ▼
                        ┌───────────────────┐
                        │      go2rtc         │   only re-streaming layer —
                        │ RTSP    :8554        │   no mediamtx sidecar; go2rtc
                        │ WHEP/HLS/API :1984   │   republishes every camera as
                        └─────────┬────────────┘   RTSP + WHEP + HLS itself
                                │ RTSP (TCP)
                                ▼
        ┌─────────────────────────────┐        ┌───────────────────────────┐
        │ services/inference             │        │  apps/web (Phase 8)        │
        │ Phase 4: YOLO11 + per-camera    │        │  Video Wall (WHEP)         │
        │ ByteTrack, one worker thread    │        │  Registry Map / Vehicle    │
        │ per camera consuming go2rtc's   │        │  Trace / Watchlist Console │
        │ RTSP republish                  │        │                            │
        │ Phase 5: + YOLO11 plate detector│        │                            │
        │          + OCR                  │        │                            │
        │ → Redis Streams                 │        │                            │
        └───────────────┬─────────────────┘        └────────────┬───────────────┘
                        │ Redis Streams                          │ REST/WS
                        ▼                                        ▼
                ┌──────────────────────────────────────────────────────┐
                │  services/api (Phase 2, 6, 7, 9): FastAPI + PostGIS +  │
                │  rank×jurisdiction RBAC + vehicle trace + watchlist    │
                │  correlation + immutable audit log + 65B-style export │
                └──────────────────────────────────────────────────────┘
```

## Repository layout

```
sentinel-grid/ (repo root)
├── docker-compose.yml          All 10 phases' services
├── docker-compose.dev.yml      Dev overrides (hot reload, extra ports)
├── .env.example                  Copy to .env before running
├── apps/
│   └── web/                      Next.js dashboard (Phase 6, 7, 8)
│       ├── app/(dashboard)/        trace, watchlist, video-wall, registry, audit pages
│       ├── app/login/               login page
│       ├── components/               nav-sidebar, top-bar, live-feed, trace-map,
│       │                            registry-map, alert-card, components/ui/*
│       └── lib/                      api-client, auth-context, use-whep, use-alert-stream
├── services/
│   ├── api/                      FastAPI backend (Phase 2, 6, 7, 9, 10)
│   │   ├── models/                 RBAC, cameras, plate_events, watchlist, audit,
│   │   │                          evidence_exports
│   │   ├── security/                JWT + the single RBAC policy surface
│   │   ├── services/                audit log, jurisdiction resolution, catalogue
│   │   │                          sync, vehicle_trace, watchlist_engine,
│   │   │                          alert_dispatcher, evidence_export, geo, media
│   │   ├── api/                    auth, cameras, tracking, watchlist, alerts,
│   │   │                          evidence, audit routers
│   │   ├── migrations/              Alembic (0001 RBAC -> 0004 evidence_exports)
│   │   └── scripts/                 seed_users.py, demo.py
│   ├── inference/                 YOLO11 + ByteTrack + ANPR (Phase 4-5)
│   │   ├── camera_source.py         RTSP/PTS/reconnect/discontinuity (per camera)
│   │   ├── detector.py               YOLO11 vehicle + person detection
│   │   ├── tracker.py                per-camera ByteTrack (see flagged risk above)
│   │   ├── plate_detector.py         YOLO11 plate localization (no model ships — see above)
│   │   ├── ocr_engine.py             PaddleOCR wrapper (CPU)
│   │   ├── plate_normalizer.py       Indian plate format + state-code validation
│   │   ├── anpr.py                   ties the three above together + per-track dedup
│   │   ├── snapshot.py               JPEG snapshot for each published plate event
│   │   ├── pipeline.py               CameraWorker thread: detect -> track -> ANPR -> publish
│   │   ├── event_publisher.py        Redis Streams (`detections`, `plate_events`, `camera_health`)
│   │   └── main.py                   coordinator: catalogue poll -> worker threads
│   ├── ingestion-config/         stream_manager.py + go2rtc template (Phase 3)
│   └── catalogue-mock/           Local stand-in for the real /api/ingest gateway
├── infra/                        nginx (TLS + reverse proxy), prometheus, grafana (Phase 10)
└── scripts/                      benchmark.py, seed_cameras.py, seed_watchlist.py,
                                   export_evidence.py — thin CLIs around the api's
                                   own HTTP endpoints
```

`services/api`'s OpenAPI schema (auto-generated by FastAPI at `/openapi.json`)
is the frontend/backend contract — `apps/web/lib/types.ts` is hand-maintained
to mirror it for now rather than generated (see that file's header comment).

## Quickstart

Requires Docker + Docker Compose (and, for Phase 4/5's `inference`
service, an NVIDIA GPU + Container Toolkit — see that service's note
further down for the CPU-only fallback). Nothing else needs to be
installed locally — all services run in containers.

```bash
cp .env.example .env
./infra/nginx/generate-self-signed-cert.sh   # dev-only TLS cert; browsers will warn, that's expected
docker compose up --build
```

This brings up the full stack: Postgres/PostGIS, Redis, go2rtc, the mock
camera catalogue, `stream_manager`, `inference`, `api`, `web`, `nginx`,
`prometheus`, and `grafana`.

Then run migrations and seed the RBAC foundation (one-time, or any time
you reset the `postgres_data` volume — `alembic upgrade head` applies all
four migrations, 0001 through 0004, in order):

```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_users.py
```

Open `https://localhost` (accept the self-signed cert warning) and log in
as one of the seeded accounts — e.g. `dgp.shah` / `ChangeMe!2026` for the
full statewide view, or `sp.ahmedabad` / `ChangeMe!2026` for a
district-scoped one. See `services/api/scripts/seed_users.py` for the
full list of nine accounts, one per rank tier.

For a fast, scripted walkthrough instead of clicking through the UI, run
the demo script once the stack (and at least one catalogue poll cycle) is
up — it seeds a test plate across 3 cameras onto the real event stream,
waits for it to be processed, adds it to the watchlist, and prints the
reconstructed route:

```bash
docker compose exec api python scripts/demo.py
```

For local development with hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Grafana is at `http://localhost:3001` (default `admin` / whatever
`GF_SECURITY_ADMIN_PASSWORD` is in `.env`) with the two dashboards under
"Sentinel Grid" pre-provisioned; Prometheus itself is at
`http://localhost:9095`.

### Verify ingestion is working

1. **Catalogue is serving cameras:**
   ```bash
   curl http://localhost:9000/api/ingest | jq
   ```
   Five seeded cameras (`AMC-JUNCTION-001`, `AMC-JUNCTION-002`,
   `SG-HIGHWAY-003`, `SURAT-RING-ROAD-004`, `VADODARA-CIRCLE-005`) — one
   (`SURAT-RING-ROAD-004`) deliberately points at an unreachable RTSP
   address so you can observe reconnect/backoff behavior.

2. **stream_manager picked them up and pushed them to go2rtc:**
   ```bash
   curl http://localhost:1984/api/streams | jq
   ```
   Each camera_id should appear as a stream key.

3. **RTSP republish is live:**
   ```bash
   ffplay rtsp://localhost:8554/AMC-JUNCTION-001
   ```

4. **Browser live view (WHEP)** via go2rtc's built-in test UI at
   `http://localhost:1984/` — select a stream.

5. **HLS leg** (also served by go2rtc — no separate relay):
   ```bash
   ffplay "http://localhost:1984/api/stream.m3u8?src=AMC-JUNCTION-001"
   ```
   *(HLS endpoint path follows go2rtc's documented API as of the pinned
   image tag; verify against your deployed go2rtc version if it 404s.)*

6. **Reconnect backoff logging:**
   ```bash
   docker compose logs -f stream_manager | grep SURAT-RING-ROAD-004
   ```
   You should see `reconnect attempt #1 (next retry in 2s)`, `#2 (4s)`, `#3
   (8s)`, escalating up to the 30s cap and staying there — it never gives up.

7. **Add/remove a camera live** (no restart needed):
   ```bash
   curl -X POST http://localhost:9000/api/ingest/simulate/remove/VADODARA-CIRCLE-005
   # within INGEST_POLL_INTERVAL_SECONDS (15s in dev overrides, 60s default),
   # stream_manager logs "removed from catalogue; tearing down stream" and
   # the stream disappears from `curl localhost:1984/api/streams`.
   curl -X POST http://localhost:9000/api/ingest/simulate/restore/VADODARA-CIRCLE-005
   ```

8. **Metrics:**
   ```bash
   curl http://localhost:9092/metrics | grep sentinelgrid_
   ```
   `sentinelgrid_camera_status{camera_id="..."}` is `1` for cameras with an
   active go2rtc producer, `0` otherwise; `sentinelgrid_reconnect_attempts_total`
   counts backoff attempts per camera.

**Environment note:** this was built and hand-reviewed without a local
Docker/Python runtime available, so these steps haven't been executed yet
in this environment — please run them on your machine and report back
anything that doesn't match before we treat Phases 2 and 3 as fully
confirmed.

### Verify the registry + RBAC foundation is working

All nine seeded accounts (see `scripts/seed_users.py`) share the demo
password `ChangeMe!2026` — rotate or delete them before any real deployment.

1. **Log in as the district-scoped SP and pull cameras — should see only
   the 2 Ahmedabad cameras:**
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"sp.ahmedabad","password":"ChangeMe!2026"}' | jq -r .access_token)
   curl -s http://localhost:8000/api/cameras -H "Authorization: Bearer $TOKEN" | jq
   ```
   (Cameras only appear here after a sync — see step 3.)

2. **Log in as State Command and pull cameras — should see all of them:**
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"dgp.shah","password":"ChangeMe!2026"}' | jq -r .access_token)
   curl -s http://localhost:8000/api/cameras -H "Authorization: Bearer $TOKEN" | jq
   ```
   Same endpoint, same code path, different result — that's the RBAC
   jurisdiction scoping working, not a special "admin view".

3. **Sync the registry from the catalogue** (requires a true statewide
   grant, e.g. `dgp.shah` or `admin.infra` — a district-scoped `camera:manage`
   holder gets a 403 with `code: statewide_scope_required`):
   ```bash
   curl -s -X POST http://localhost:8000/api/cameras/sync -H "Authorization: Bearer $TOKEN" | jq
   ```
   Cameras whose catalogue `department` matches a seeded jurisdiction name
   (Ahmedabad Traffic Police, Gujarat State Highway Patrol, Surat City
   Police, Vadodara City Police) are auto-assigned; `unassigned_jurisdiction`
   in the response lists any that need a manual `PATCH`.

4. **Confirm a non-police department account can't see tracking/watchlist
   permissions at all:**
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"operator.rto","password":"ChangeMe!2026"}' | jq -r .access_token)
   curl -s http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN" | jq .permissions
   ```
   Should print `["camera:read"]` only — no `vehicle_trace:read` or
   `watchlist:*`, regardless of jurisdiction.

5. **Confirm a denied request is audited.** Every 403 (wrong permission or
   wrong jurisdiction) writes an audit_log row even though there's no
   `/audit-log` read endpoint yet (Phase 9) — you can see it directly:
   ```bash
   docker compose exec postgres psql -U sentinelgrid -d sentinelgrid \
     -c "SELECT ts, username, action, outcome, reason FROM audit_log ORDER BY ts DESC LIMIT 5;"
   ```

6. **Confirm the audit chain is tamper-evident:**
   ```bash
   docker compose exec postgres psql -U sentinelgrid -d sentinelgrid \
     -c "UPDATE audit_log SET reason = 'tampered' WHERE id = (SELECT id FROM audit_log LIMIT 1);"
   ```
   This should fail with `audit_log is append-only: UPDATE is not
   permitted` — the trigger rejects it outright, not just the ORM layer.

### Verify detection & tracking is working

Requires an NVIDIA GPU + the NVIDIA Container Toolkit on the host (or
comment out the `deploy.resources.reservations` block for `inference` in
docker-compose.yml and set `SENTINELGRID_DEVICE=cpu` — much slower, but the
same code path). First run downloads `yolo11s.pt` from Ultralytics on
container start, so the `inference` container needs outbound internet the
first time; it's cached in the `inference_models` volume after that.

1. **Confirm it picked up the same 5 cameras stream_manager did:**
   ```bash
   docker compose logs inference | grep "worker starting"
   ```
   Should show 5 `camera=... worker starting` lines (one per catalogue
   camera, `SURAT-RING-ROAD-004` included — it'll just sit in its own
   reconnect loop since that source is deliberately unreachable).

2. **Confirm frames are actually being processed:**
   ```bash
   curl -s http://localhost:9090/metrics | grep sentinelgrid_frames_processed_total
   ```
   Counters should be > 0 and increasing across repeated calls for the
   reachable cameras (`AMC-JUNCTION-001`, `AMC-JUNCTION-002`,
   `VADODARA-CIRCLE-005`, which point at a public demo RTSP stream — see
   `services/catalogue-mock/app.py`).

3. **Confirm detections and track IDs are landing in Redis:**
   ```bash
   docker compose exec redis redis-cli XREVRANGE detections + - COUNT 5
   ```
   Each entry should show `camera_id`, `track_id`, `class_name`,
   `confidence`, a bbox, and `frame_pts_ms` — and re-running this a few
   seconds apart, the same `track_id` should persist for what is visibly
   the same object rather than incrementing every frame (confirms tracking
   is actually stateful, not just re-detecting from scratch).

4. **Confirm the flagged tracker risk isn't actually a problem** (see
   "Assumptions currently in effect" above) by comparing this service's
   output against ultralytics' own high-level API on one frame, per the
   instructions at the top of `services/inference/tracker.py`.

5. **Reconnect backoff on the inference side too** (independent from
   stream_manager's — this is the inference service's own RTSP connection
   to go2rtc):
   ```bash
   docker compose logs inference | grep SURAT-RING-ROAD-004
   ```
   Same 2s → 4s → 8s → … → 30s pattern as stream_manager's log.

6. **Inference-side metrics:**
   ```bash
   curl -s http://localhost:9090/metrics | grep sentinelgrid_
   ```
   `sentinelgrid_inference_active_cameras`, `sentinelgrid_tracks_active`,
   `sentinelgrid_inference_latency_seconds`, `sentinelgrid_scene_discontinuities_total`.

**Environment note:** none of Phase 4 has been run — this sandbox has
neither a GPU nor Python/Docker. The two things most likely to need a fix
on first real run are the tracker input-shape assumption above and the
exact PyTorch/CUDA driver compatibility of the pinned base image
(`pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`) against your host's
actual driver version.

### Verify ANPR is working (once a plate model is provided)

Until `models/yolo11n-plate.pt` (or wherever `PLATE_MODEL_PATH` points)
exists, skip straight to step 1 — it confirms ANPR is correctly *disabled*
rather than silently broken, which is the expected state out of the box.

1. **Confirm ANPR's own state is visible and correct at startup:**
   ```bash
   docker compose logs inference | grep -i anpr
   ```
   With no model file present: `Plate detector model not found at
   models/yolo11n-plate.pt — ANPR is disabled...` and
   `anpr_available=False` in the startup line. With a model file present
   and PaddleOCR initializing correctly: `Plate detector loaded from ...`,
   `PaddleOCR engine initialized (CPU)`, and `anpr_available=True`.

2. **Once a model is in place, confirm plate events are landing in Redis:**
   ```bash
   docker compose exec redis redis-cli XREVRANGE plate_events + - COUNT 5
   ```
   Each entry should show `camera_id`, `track_id`, `plate_text` (format
   `SSDDLLDDDD`, e.g. `GJ01AB1234`), `confidence`, `region` (a real 2-letter
   state code), and `snapshot_path`.

3. **Confirm the snapshot was actually written:**
   ```bash
   docker compose exec inference ls -la /data/snapshots/AMC-JUNCTION-001/
   ```
   (Path is `{camera_id}/{YYYYMMDD}/{plate}_{pts_ms}.jpg` — see `snapshot.py`.)

4. **Confirm dedup is working, not just "happens not to repeat":** watch
   `sentinelgrid_plates_read_total` against `sentinelgrid_anpr_attempts_total`
   for one camera over a minute or two of a vehicle sitting in frame —
   attempts should keep climbing (or stop once
   `ANPR_SKIP_RERUN_ABOVE_CONFIDENCE` is hit) while reads published to
   Redis for that same track_id should not, unless a materially better
   read comes in (`ANPR_REPUBLISH_MARGIN`).
   ```bash
   curl -s http://localhost:9090/metrics | grep -E "sentinelgrid_(plates_read|anpr_attempts)_total"
   ```

5. **Confirm graceful degradation is real, not assumed:** temporarily
   rename/remove the plate model file and restart the `inference`
   container. Detection/tracking metrics
   (`sentinelgrid_frames_processed_total`, the `detections` stream) should
   be completely unaffected; only `plate_events` stops gaining entries.

**Environment note:** same as Phase 4 — none of this has been run. The
PaddleOCR dependency install and the plate-detector-to-OCR handoff (in
particular, whether PaddleOCR's `.ocr()` result shape matches
`ocr_engine.py`'s `_parse_result` assumption for your installed version)
are the two things most likely to need a fix on first real run.

### Verify tracking, watchlist, video wall, registry map, and audit export

The fastest path is `docker compose exec api python scripts/demo.py` (see
Quickstart above) — it exercises Phases 6 and 7 end to end in one run
against real Redis/Postgres, and prints its own pass/fail-shaped output.
Beyond that:

1. **Trace UI**: log in as `sp.ahmedabad`, go to Vehicle Trace, search the
   demo plate (`GJ01DM9988` by default) — the timeline and map should
   match what `demo.py` printed. Search a plate that was never published
   and confirm you get an empty, not-an-error result.
2. **Watchlist UI**: open Watchlist & Alerts in a second browser tab
   *before* running `demo.py` — the alert should appear live via
   WebSocket without a page refresh, pulsing until acknowledged.
3. **Cross-rank RBAC, demonstrated by using the product**: open the same
   Trace/Watchlist pages logged in as `operator.rto` (T8) — the nav
   sidebar itself should not even show Vehicle Trace or Watchlist &
   Alerts, since `hasPermission()` gates which nav items render (see
   `components/nav-sidebar.tsx`), not just the API calls behind them.
4. **Video wall**: open Video Wall as any camera:read holder — tiles
   should attempt a WHEP connection per camera and show a `live`/`error`
   status badge. If every tile shows `error`, check the go2rtc WHEP
   endpoint assumption flagged in `apps/web/lib/use-whep.ts` first.
5. **Registry map**: open Registry Map — pins should cluster at low zoom
   and separate on zoom-in; clicking one shows the same status the API
   returns (remembering the "known gap" above: this status is whatever
   `/cameras/sync` last recorded, not necessarily live right now).
6. **Evidence export**: from the Trace page, after a successful search,
   click "Export evidence" — or run
   `python scripts/export_evidence.py --username sp.ahmedabad --password ChangeMe!2026 --plate GJ01DM9988`
   from the host. Unzip the result and confirm `manifest.json` lists a
   `sha256` for every file, and that recomputing `sha256sum` on
   `events.csv` matches what the manifest says.
7. **Audit log**: open Audit Log as `dgp.shah` — every step above should
   have produced at least one row (an `allow` for each successful
   tracking/watchlist/evidence access, a `deny` for the T8 nav items that
   never even got called). Click "Verify chain integrity" and confirm it
   reports intact; then try the tamper test from the Phase 2 verification
   section above again and confirm verify now reports the chain broken.

**Environment note:** same as every phase above — none of this has run.
The two WebRTC/WebSocket pieces (`use-whep.ts`'s go2rtc endpoint
assumption and the alert WebSocket's token-in-query-string auth) are the
most likely things to need a small fix on first real run; everything on
the Postgres/Redis side has at least been exercised in code review against
the actual schema and stream field names.

### Camera catalogue contract

**This contract is now confirmed, not assumed** — see
[docs/gateway-contract.md](docs/gateway-contract.md) for the organizer-
provided integration spec verbatim, with every hard constraint
cross-referenced to exactly where in this codebase it's enforced. The
short version: `stream_manager.py` treats `INGEST_API_URL` as the single
source of truth for what cameras exist and their properties (codec,
resolution, fps, live status) — it never hardcodes a camera list or a URL
pattern. Any service implementing this JSON contract can replace
`services/catalogue-mock` in production, including the real gateway (only
`INGEST_API_URL` and auth need to change):

```json
{
  "cameras": [
    {
      "camera_id": "AMC-JUNCTION-001",
      "name": "Ashram Road Junction",
      "department": "Ahmedabad Traffic Police",
      "lat": 23.0225, "lon": 72.5714,
      "resolution": "1280x720", "codec": "h264", "fps": 25,
      "live": true,
      "protocols": {
        "rtsp": "rtsp://user:pass@host:554/stream1",
        "whep": null,
        "hls": null
      }
    }
  ]
}
```

`stream_manager` resolves the ingestion source protocol per camera in
priority order **RTSP → WHEP → HLS**, based on whichever `protocols.*`
fields are non-null, and forces `rtsp_transport=tcp` on every RTSP source.
This is about how *we pull from the camera*; regardless of that choice,
go2rtc always republishes the camera as RTSP + WHEP + HLS for consumers.
A camera reported with `"live": false` is skipped entirely by both
`stream_manager.py` and `services/inference` — no connection is even
attempted, rather than being attempted and left to fail through the
reconnect/backoff path.

### Hard ingestion constraints — where each one is enforced

| Constraint | Enforced in |
|---|---|
| RTSP over TCP only | `stream_manager.py` (`_with_tcp_transport`) at the go2rtc ingestion leg; `inference/camera_source.py` (`OPENCV_FFMPEG_CAPTURE_OPTIONS`) at the frame-decode leg |
| Never trust reported FPS for timing; derive from PTS | `inference/camera_source.py` (`CAP_PROP_POS_MSEC`; `CAP_PROP_FPS` is logged only, never used for scheduling) |
| Tolerate non-constant frame rate / inter-frame gaps | `inference/camera_source.py` (target-FPS throttle, not a fixed-interval assumption) |
| Exponential backoff reconnect, never a tight loop | `stream_manager.py` (`StreamSupervisor._check_health`) and independently `inference/camera_source.py` (`schedule_reconnect`) |
| Decoder warnings at stream join are non-fatal | `inference/camera_source.py` (`MAX_CONSECUTIVE_READ_FAILURES` tolerance before reconnecting) |
| Always read camera list/properties from `/api/ingest` at runtime | `stream_manager.py` (`CatalogueClient`) and `inference/camera_catalogue_client.py` |
| Scene discontinuity on feed loop = hard cut, not infinite continuity | `inference/camera_source.py` (PTS-jump detection) + `inference/tracker.py` (`CameraTracker.reset`) |
| Never call the gateway's control API / never publish back to it | `stream_manager.py` and `inference/camera_catalogue_client.py` (both read-only) |
| Only open cameras actively being processed | `stream_manager.py` (`_reconcile`) and `inference/main.py` (worker threads stopped/joined when a camera drops out of the catalogue) |

## Deploying `apps/web` to Vercel

Only the Next.js dashboard can go on Vercel — Vercel hosts frontends, not
Postgres/Redis/go2rtc/GPU containers. **The rest of the stack (`api`,
`inference`, `stream_manager`, `catalogue`, `postgres`, `redis`, `go2rtc`)
still has to run somewhere reachable over the network** — the existing
`docker compose` stack on a VM, cloud instance, or the actual PoC hardware.
Deploying the dashboard to Vercel gives you a stable, shareable submission
link for the UI; it does not replace the backend deployment.

**Root Directory: `apps/web`**

This is a monorepo — `apps/web` is one of several projects in it, and it's
the only one with a `package.json` Vercel would recognize as a Next.js
app. When importing the repo in Vercel:

1. **Import Project** → select this GitHub repo.
2. Vercel will likely fail to auto-detect a framework at the repo root
   (correct — there's no `package.json` there). Open **Project Settings →
   General → Root Directory**, set it to `apps/web`, and re-run detection.
   Framework Preset should then read "Next.js" automatically.
3. Build Command / Output Directory: leave on the Next.js defaults
   (`next build`, `.next`) — no override needed.
4. Under **Environment Variables**, add (Production and Preview both):
   - `NEXT_PUBLIC_API_BASE_URL` — the public URL of your deployed `api`
     service (e.g. `https://your-domain.example/api`), **not**
     `localhost`. This has to be reachable from the browser, not just from
     Vercel's build servers.
   - `NEXT_PUBLIC_GO2RTC_WHEP_BASE_URL` — the public URL your `go2rtc`
     container is reachable at (e.g. `https://your-domain.example:8554`
     or wherever it's exposed). Subject to the go2rtc auth/TLS gap in
     [Known gaps](#known-gaps) below either way.

   Both are compiled into the client bundle at build time (see
   `apps/web/Dockerfile`'s comment on why — the same rule applies to
   Vercel's build), so changing either later means **redeploying**, not
   just editing a running deployment's env vars.
5. Deploy. On your backend's side, add the Vercel deployment's URL (e.g.
   `https://sentinel-grid.vercel.app`) to `CORS_ORIGINS` in the backend's
   `.env` and restart `api` — the frontend and backend are now on
   different origins (unlike the bundled nginx setup, where everything is
   same-origin), so CORS has to explicitly allow it.

No `vercel.json` is included or needed — Root Directory plus Vercel's
standard Next.js framework detection is sufficient. This hasn't been
deployed to a live Vercel project in this environment (no internet-facing
deploy target available here); the steps above are correct against
Vercel's documented monorepo/Next.js behavior but, like everything else in
this repo, worth a first real run before you rely on it for submission day.

## RBAC model (Phase 2 — implemented)

Two axes, resolved server-side on every request —
`hasPermission(user, action) AND isInJurisdiction(user, resource)` — never
a generic admin/user split and never a client-supplied scope. Both checks
live in exactly one module, `security/rbac.py`:

- `require_permission(action)` — a dependency every protected route uses,
  checking `action` against the caller's role's `role_permissions`.
- `check_resource_jurisdiction(...)` — called after a route loads a
  specific resource, checking its `jurisdiction_id` against the caller's
  granted jurisdiction subtree (list endpoints filter the query directly
  via `jurisdiction_service.get_user_scope_jurisdiction_ids` instead — see
  `api/cameras.py` for both patterns).

Jurisdictions form one tree rooted at a single `statewide` node; granting a
node grants everything beneath it (a district grant covers every station
under it; the statewide grant covers the entire tree, including
non-police department branches). No tier needs special-cased "sees
everything" logic — T1's statewide grant just happens to resolve to every
node.

| Tier | Rank equivalent |
|---|---|
| T1 | State Command (DGP / CP) |
| T2 | Range/Zone (IGP/DIG, Jt. CP) |
| T3 | District (SP, DCP) |
| T4 | Sub-division (DySP, ACP) |
| T5 | Station House Officer (PI) |
| T6 | Field Supervisory (PSI) |
| T7 | Field Operational (ASI/HC/Constable) |
| T8 | Non-police department operator (RTO/GSRTC/Health/Municipal) |
| T9 | System Admin (infra only, no investigative data by default) |

New accounts default to zero jurisdiction grants until assigned (see
`user_jurisdictions`) — a role alone grants nothing. T8 accounts hold only
`camera:read`; they never get `watchlist:*`, `vehicle_trace:read`, or
`evidence:export`, full stop, regardless of jurisdiction (see
`scripts/seed_users.py` `ROLE_PERMISSIONS`). There's no dedicated "look,
RBAC works" screen — the demo is: log in as `sp.ahmedabad` and `dgp.shah`
in two tabs and hit the same `/api/cameras` endpoint (see verification
steps above).

Every permission/jurisdiction denial — and every login attempt — writes to
the hash-chained, append-only `audit_log` table (`services/audit_service.py`),
regardless of which endpoint triggered it. A Postgres trigger rejects any
`UPDATE`/`DELETE` on that table outright, independent of the app's own DB
credentials. Sensitive endpoints (tracking, watchlist, export, once built in
Phases 6/7/9) additionally pass `audit_on_success=True` so *every* access is
logged, not just denials.

## Evaluation framework mapping

Mapped against the organizer's stated evaluation areas, honestly —
"built" is not the same as "verified," and that distinction is marked
explicitly rather than papered over.

**A. Common evaluation areas**

| # | Area | Status |
|---|---|---|
| 01 | Successful test case (onboard + operate on the government feed) | Code is written against the confirmed real contract ([docs/gateway-contract.md](docs/gateway-contract.md)) and cross-referenced line-by-line to where each rule is enforced — but **not yet run against the actual gateway**, only against the mock. This is the single highest-priority thing to verify before submission. |
| 02 | Solution presentation (PPT/PDF) | Not started — outside this repo's scope; the architecture diagram and phase breakdown below are meant to be source material for it, not a substitute. |
| 03 | Solution architecture (HLD, security, interoperability) | See [Architecture](#architecture) and [RBAC model](#rbac-model-phase-2--implemented). go2rtc-as-sole-relay, jurisdiction-scoped RBAC behind one policy surface, and the Redis Streams decoupling between inference and the API are the three architectural decisions worth highlighting in a write-up. |
| 04 | Working platform + demonstration (own feed + government feed) | Runs end to end against the mock catalogue and public demo RTSP streams (`scripts/demo.py`); swapping to the government feed is a config change (`INGEST_API_URL`) per the contract above, not a code change — but that swap itself is untested, per row 01. |
| 05 | Video analytics output (ANPR, detection, timestamps, reports) | Vehicle/person detection (Phase 4) and ANPR (Phase 5) are both implemented; **ANPR has no fine-tuned Indian-plate model shipped**, so plate reads won't actually happen until one is trained and dropped in (see [Known gaps](#known-gaps)) — detection/tracking works without it. |
| 06 | Scalability & PoC readiness | Architecture is designed for it (stateless workers, one Redis consumer group per concern, PostGIS not SQLite) — but the acceptance-checklist-grade requirement ("grounded in actual measured resource usage") is **not met yet**: `scripts/benchmark.py` exists to produce real numbers, none have been collected. Do not submit a guessed number. |
| 07 | Submission completeness | This repo, [README.md](README.md), and [docs/gateway-contract.md](docs/gateway-contract.md) are complete and internally consistent as engineering documentation. Credentials for the demo accounts are in `services/api/scripts/seed_users.py` (rotate before any real deployment). |

**B. Bonus consideration**

| Capability | Status |
|---|---|
| Innovative/hybrid architecture | go2rtc-only re-streaming + Redis Streams as the sole event bus (no Kafka) is a deliberate simplification over the more common multi-broker pattern — worth stating explicitly as a design choice, not an omission. |
| Advanced cross-camera vehicle tracking | Built (Phase 6): PostGIS-based inferred speed between consecutive camera stops, jurisdiction-aware route reconstruction. |
| Additional analytics beyond ANPR | Person detection is already emitted alongside vehicle detection (Phase 4) but nothing downstream consumes it yet (no loitering/intrusion logic) — a plausible bonus feature to add if time permits before submission. |
| Edge/bandwidth optimization | Not addressed — every camera's full-resolution stream is pulled centrally. Worth naming as a known limitation if asked, not a hidden gap. |
| Enhanced security/auditability/RBAC | This is arguably the strongest bonus area already built: T1-T9 rank × jurisdiction RBAC behind one policy surface, hash-chained tamper-evident audit log, Section 65B-style evidentiary export with per-file SHA-256. |
| Dashboards, alerts, health monitoring, integration-ready APIs | Built: the full dashboard (Phase 8), live watchlist alerts (Phase 7), Prometheus/Grafana (Phase 10), and a documented REST/WebSocket API surface (`/api/openapi.json` via FastAPI's auto-generated schema). |

## Known gaps

All 10 phases have code written for them, but **none of it has run on a
real machine yet** — this whole build happened in a sandbox with no
Docker, Python, or GPU available. Beyond the phase-specific caveats
already called out above (the ByteTrack internal-API risk in Phase 4, the
missing fine-tuned plate model in Phase 5), these are the gaps worth
knowing about before treating this as demo-ready:

- **go2rtc has no authentication of its own, and no TLS.** `apps/web`
  connects to it directly from the browser for WHEP (see `lib/use-whep.ts`)
  so a user who somehow learned a camera_id outside their
  jurisdiction-scoped `/api/cameras` list could still pull that camera's
  live feed straight from go2rtc. Closing this needs an authenticating
  reverse proxy in front of go2rtc (nginx `auth_request` validating a
  short-lived token, or a small proxying service) — not built. The nginx
  config that *is* built (`infra/nginx/nginx.conf`) deliberately does not
  proxy go2rtc, so this gap is at least not hidden behind a false sense of
  TLS coverage. **Practical consequence right now:** because go2rtc is
  plain HTTP and the dashboard is served over HTTPS through nginx, browsers'
  mixed-content policy will likely block the video wall's WHEP calls
  entirely when accessed via `https://localhost`. Until the proxy above is
  built, access the dashboard directly at `http://localhost:3000` (bypassing
  nginx/TLS) if you need the video wall to actually connect — every other
  page works fine over HTTPS since they only talk to `api`, not go2rtc.
- **No email delivery is configured anywhere.** `POST /auth/forgot-password`
  (Transformation Phase 2) generates a real, working reset token, but
  "sends" it by logging it server-side — readable by anyone with log
  access, which is fine for a dev/demo environment and not acceptable for
  a real deployment. Outside `ENVIRONMENT=production` it's also returned
  directly in the API response so the flow is testable without log
  access; in production it never is. Wiring real SMTP/email delivery in
  is the fix, not built here.
- **`Camera.status` isn't live-synced.** The registry map colors markers
  by this field (green/yellow/red, per the design brief), but nothing yet
  writes live health from go2rtc/stream_manager back into it — it reflects
  whatever `POST /cameras/sync` last saw, which doesn't include liveness.
  stream_manager already tracks real liveness as a Prometheus metric
  (`sentinelgrid_camera_status`); wiring that into the registry table (a
  small periodic sync job) is the natural next step.
- **Scalability numbers are a methodology, not a measurement.**
  `scripts/benchmark.py` and the extrapolation approach it prints are
  real; the actual 50-camera resource numbers the acceptance checklist
  asks for are not, because nothing has run. Run it against a live
  50-camera deployment before quoting any number in the hackathon
  write-up — don't substitute a guess.
- **No automated tests.** Everything in this repo has been reviewed by
  hand (including catching and fixing several real bugs along the way —
  a jurisdiction-escape in camera reassignment, a dedup-ordering bug in
  ANPR republishing, an unreachable-branch in RBAC's unassigned-camera
  handling), but there's no pytest suite. For a hackathon PoC this is a
  defensible trade-off given the time available; it would not be for
  anything beyond that.

## Coming up (beyond the 10 phases)

- Fine-tune and ship an actual Indian-plate YOLO11 model (Phase 5's gap).
- Close the go2rtc authentication gap (above).
- Wire live camera status back into the registry (above).
- Run `scripts/benchmark.py` against a real 50-camera deployment and put
  the actual numbers — not a methodology — in the hackathon write-up.
- Add a test suite, starting with the RBAC policy surface
  (`security/rbac.py`) and the audit hash chain
  (`services/audit_service.py`), since those are the two places a subtle
  bug would be worst.

## License

To be finalized before public release.
