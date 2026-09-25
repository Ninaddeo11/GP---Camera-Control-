"""
stream_manager.py — Sentinel Grid ingestion-config service.

go2rtc is the platform's ONLY re-streaming layer: it consumes each camera's
native RTSP/WHEP/HLS source from the gateway catalogue and republishes it
uniformly as RTSP, WHEP, and HLS from one instance, so every downstream
consumer (inference service, video wall) talks to one predictable protocol
set regardless of what the camera actually speaks. There is no mediamtx
sidecar — go2rtc's built-in multi-protocol HTTP API (RTSP republish on
:8554, WHEP/HLS/API on :1984) covers both the low-latency preview leg and
the HLS fallback leg.

Responsibilities:
  1. Poll the camera catalogue (`/api/ingest`) on startup and on a fixed
     interval to discover added/removed/changed cameras. Camera source URLs
     are NEVER hardcoded — they are always resolved from the catalogue, and
     properties (codec, resolution, fps) are read from it too, never assumed.
  2. For each camera, resolve the best available INGESTION source protocol
     in priority order RTSP -> WHEP -> HLS (this is about how *we* pull from
     the camera; go2rtc always republishes as RTSP+WHEP+HLS regardless).
  3. Render go2rtc.yaml from a Jinja2 template so a cold restart recovers
     the full stream list even if the live API push below is lost.
  4. Push stream changes to go2rtc via its HTTP API so the running
     container picks up added/removed/changed cameras without a restart.
  5. Supervise per-camera connection health with exponential backoff
     reconnection (2s -> 4s -> 8s -> 16s -> 30s cap, never a tight loop),
     logging every attempt with camera_id, attempt number, and backoff
     duration.
  6. Expose Prometheus metrics for camera status and reconnection counts.

Hard ingestion constraints this module enforces:
  - RTSP sources are always pulled over TCP (never UDP), which fails across
    NAT/firewalls and produces corrupt frames — see `_with_tcp_transport`.
  - The gateway's control API is never called and streams are never
    published back to it; this module only ever reads `/api/ingest`.
  - Only cameras currently present in the catalogue are kept open in
    go2rtc; removed cameras are torn down promptly rather than left
    consuming gateway capacity.

Constraints that do NOT belong here (enforced downstream, where frames are
actually decoded):
  - PTS-derived timing (never wall-clock), tolerating non-constant frame
    rate, and recovering tracker/background-model state across the scene
    discontinuity when a looping feed cuts back to its start are all the
    inference service's responsibility (services/inference), since this
    module never decodes a frame — it only orchestrates go2rtc.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from prometheus_client import Counter, Gauge, start_http_server

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_DIR = Path(os.environ.get("GENERATED_CONFIG_DIR", str(BASE_DIR / "generated")))

INGEST_API_URL = os.environ.get("INGEST_API_URL", "http://catalogue:9000/api/ingest")
INGEST_POLL_INTERVAL_SECONDS = int(os.environ.get("INGEST_POLL_INTERVAL_SECONDS", "60"))

GO2RTC_API_URL = os.environ.get("GO2RTC_API_URL", "http://go2rtc:1984")

METRICS_PORT = int(os.environ.get("STREAM_MANAGER_METRICS_PORT", "9092"))

BACKOFF_INITIAL_SECONDS = float(os.environ.get("RECONNECT_BACKOFF_INITIAL_SECONDS", "2"))
BACKOFF_MAX_SECONDS = float(os.environ.get("RECONNECT_BACKOFF_MAX_SECONDS", "30"))
HEALTH_CHECK_INTERVAL_SECONDS = float(os.environ.get("HEALTH_CHECK_INTERVAL_SECONDS", "5"))

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("stream_manager")

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

CAMERA_STATUS = Gauge(
    "sentinelgrid_camera_status",
    "1 if the camera's stream has an active producer in go2rtc, else 0",
    ["camera_id"],
)
RECONNECT_ATTEMPTS = Counter(
    "sentinelgrid_reconnect_attempts_total",
    "Total reconnection attempts made per camera",
    ["camera_id"],
)
CATALOGUE_CAMERAS = Gauge(
    "sentinelgrid_catalogue_cameras",
    "Number of cameras currently known from the catalogue",
)
CATALOGUE_POLL_ERRORS = Counter(
    "sentinelgrid_catalogue_poll_errors_total",
    "Number of failed catalogue polls",
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Camera:
    camera_id: str
    name: str
    department: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    resolution: str = ""
    codec: str = ""
    fps: float = 0.0
    protocol: str = ""  # resolved ingestion source: "rtsp" | "whep" | "hls"
    source_url: str = ""  # the go2rtc source string we push

    @property
    def key(self) -> tuple:
        """Identity used to detect a meaningful change vs. just a re-poll."""
        return (self.protocol, self.source_url)


@dataclass
class ReconnectState:
    camera_id: str
    consecutive_failures: int = 0
    next_attempt_at: float = field(default_factory=time.monotonic)
    is_up: bool = False


# ---------------------------------------------------------------------------
# Protocol resolution
# ---------------------------------------------------------------------------


def _with_tcp_transport(rtsp_url: str) -> str:
    """Force RTSP-over-TCP at the go2rtc ingestion layer.

    UDP fails silently across NAT/firewalls and produces corrupt frames that
    look like model bugs downstream — this is a hard requirement, not a
    tuning knob. go2rtc reads per-source options from a URL fragment; if a
    future go2rtc version changes this option name, this is the only place
    that needs to change.
    """
    if "#" in rtsp_url:
        return f"{rtsp_url}&transport=tcp"
    return f"{rtsp_url}#transport=tcp"


def resolve_camera(entry: dict) -> Optional[Camera]:
    """Pick the source protocol for a catalogue entry in priority order
    RTSP -> WHEP -> HLS, and build the go2rtc source string for it.

    Expected catalogue entry shape (see services/catalogue-mock/app.py):
        {
          "camera_id": "AMC-001",
          "name": "...",
          "department": "...",
          "lat": 23.02, "lon": 72.57,
          "resolution": "1920x1080", "codec": "h264", "fps": 25,
          "protocols": {
            "rtsp": "rtsp://user:pass@host:554/stream1",
            "whep": "http://host/whep/endpoint",
            "hls": "http://host/hls/stream/index.m3u8"
          }
        }
    """
    camera_id = entry.get("camera_id")
    if not camera_id:
        log.warning("Skipping catalogue entry with no camera_id: %r", entry)
        return None

    # The gateway reports live status per camera in the catalogue itself
    # (see docs/gateway-contract.md) — a camera already known to be down
    # is skipped here rather than attempted and left to fail through the
    # reconnect/backoff path in _check_health. It stays in `self.cameras`
    # as absent, so it's treated the same as any other camera not
    # currently in the catalogue (no stream pushed, nothing to tear down).
    if entry.get("live") is False:
        return None

    protocols = entry.get("protocols") or {}
    rtsp_url = protocols.get("rtsp")
    whep_url = protocols.get("whep")
    hls_url = protocols.get("hls")

    if rtsp_url:
        protocol, source_url = "rtsp", _with_tcp_transport(rtsp_url)
    elif whep_url:
        protocol, source_url = "whep", f"webrtc:{whep_url}#format=whep"
    elif hls_url:
        protocol, source_url = "hls", f"ffmpeg:{hls_url}#video=h264"
    else:
        log.warning("Camera %s has no usable protocol in catalogue entry; skipping", camera_id)
        return None

    return Camera(
        camera_id=camera_id,
        name=entry.get("name", camera_id),
        department=entry.get("department", ""),
        lat=entry.get("lat"),
        lon=entry.get("lon"),
        resolution=entry.get("resolution", ""),
        codec=entry.get("codec", ""),
        fps=float(entry.get("fps", 0) or 0),
        protocol=protocol,
        source_url=source_url,
    )


# ---------------------------------------------------------------------------
# Catalogue client
# ---------------------------------------------------------------------------


class CatalogueClient:
    """Read-only client for the camera gateway's `/api/ingest` catalogue.

    Consume only: this module never calls the gateway's control API and
    never publishes streams back to it.
    """

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def fetch_cameras(self) -> dict[str, Camera]:
        resp = await self._client.get(INGEST_API_URL, timeout=10.0)
        resp.raise_for_status()
        payload = resp.json()
        entries = payload.get("cameras", payload if isinstance(payload, list) else [])

        cameras: dict[str, Camera] = {}
        for entry in entries:
            cam = resolve_camera(entry)
            if cam is not None:
                cameras[cam.camera_id] = cam
        return cameras


# ---------------------------------------------------------------------------
# go2rtc client
# ---------------------------------------------------------------------------


class Go2rtcClient:
    """Thin wrapper over go2rtc's HTTP API — the only ingestion/re-streaming
    control surface this platform uses.

    NOTE: endpoint shapes follow go2rtc's documented streams API as of the
    `alexxit/go2rtc` image pinned in docker-compose.yml. If a future go2rtc
    version changes this contract, update this class only — nothing else in
    stream_manager depends on go2rtc's wire format.
    """

    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        self._base = GO2RTC_API_URL

    async def upsert_stream(self, camera_id: str, source_url: str) -> None:
        resp = await self._client.put(
            f"{self._base}/api/streams",
            params={"name": camera_id, "src": source_url},
            timeout=10.0,
        )
        resp.raise_for_status()

    async def remove_stream(self, camera_id: str) -> None:
        resp = await self._client.delete(
            f"{self._base}/api/streams",
            params={"src": camera_id},
            timeout=10.0,
        )
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()

    async def list_streams(self) -> dict:
        resp = await self._client.get(f"{self._base}/api/streams", timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    async def is_producer_active(self, camera_id: str, streams: dict) -> bool:
        info = streams.get(camera_id)
        if not info:
            return False
        producers = info.get("producers") or []
        for producer in producers:
            # go2rtc marks a healthy producer with a non-error state and at
            # least one open track.
            if not producer.get("error") and producer.get("state") != "error":
                return True
        return False


# ---------------------------------------------------------------------------
# Config file rendering
# ---------------------------------------------------------------------------


class ConfigRenderer:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(disabled_extensions=("j2",)),
            keep_trailing_newline=True,
        )

    def render(self, cameras: list[Camera]) -> None:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        camera_dicts = [
            {"camera_id": c.camera_id, "source_url": c.source_url} for c in cameras
        ]
        self._render_one("go2rtc.yaml.j2", "go2rtc.yaml", cameras=camera_dicts)

    def _render_one(self, template_name: str, out_name: str, **context) -> None:
        template = self._env.get_template(template_name)
        rendered = template.render(**context)

        # Fail loudly before touching disk if the render produced invalid YAML.
        yaml.safe_load(rendered)

        out_path = GENERATED_DIR / out_name
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp_path.write_text(rendered, encoding="utf-8")
        tmp_path.replace(out_path)
        log.info("Rendered %s (%d bytes)", out_path, len(rendered))


# ---------------------------------------------------------------------------
# Reconciliation + health supervision
# ---------------------------------------------------------------------------


class StreamSupervisor:
    def __init__(
        self,
        catalogue: CatalogueClient,
        go2rtc: Go2rtcClient,
        renderer: ConfigRenderer,
    ) -> None:
        self.catalogue = catalogue
        self.go2rtc = go2rtc
        self.renderer = renderer

        self.cameras: dict[str, Camera] = {}
        self.reconnect_state: dict[str, ReconnectState] = {}
        self._stop = asyncio.Event()

    def request_stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        await self._reconcile()  # initial sync on startup
        await asyncio.gather(self._poll_loop(), self._health_loop())

    async def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=INGEST_POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
            if self._stop.is_set():
                break
            await self._reconcile()

    async def _reconcile(self) -> None:
        try:
            latest = await self.catalogue.fetch_cameras()
        except Exception:
            CATALOGUE_POLL_ERRORS.inc()
            log.exception("Failed to poll catalogue at %s", INGEST_API_URL)
            return

        added = [cid for cid in latest if cid not in self.cameras]
        removed = [cid for cid in self.cameras if cid not in latest]
        changed = [
            cid
            for cid in latest
            if cid in self.cameras and latest[cid].key != self.cameras[cid].key
        ]

        for cid in removed:
            # Close out cameras no longer in the catalogue promptly, rather
            # than leaving a dangling consumer connection open against the
            # gateway (only open what we're actively processing).
            # Covers two distinct catalogue states that both mean "stop
            # serving this camera": it dropped out of /api/ingest entirely,
            # or it's still listed but now reports live=false.
            log.info("Camera %s no longer usable (removed or marked not-live); tearing down stream", cid)
            await self._safe_call(self.go2rtc.remove_stream(cid))
            self.reconnect_state.pop(cid, None)
            try:
                CAMERA_STATUS.remove(cid)
            except KeyError:
                pass  # no metric sample existed for this camera yet

        for cid in added:
            cam = latest[cid]
            log.info(
                "Camera %s (%s) discovered via %s: %s", cid, cam.name, cam.protocol, cam.source_url
            )
            self.reconnect_state[cid] = ReconnectState(camera_id=cid)
            await self._push_stream(cam)

        for cid in changed:
            cam = latest[cid]
            log.info(
                "Camera %s source changed -> %s (%s); re-pushing stream",
                cid,
                cam.source_url,
                cam.protocol,
            )
            await self._push_stream(cam)

        self.cameras = latest
        CATALOGUE_CAMERAS.set(len(self.cameras))

        self.renderer.render(list(self.cameras.values()))

        if added or removed or changed:
            log.info(
                "Reconciliation complete: %d added, %d removed, %d changed, %d total",
                len(added),
                len(removed),
                len(changed),
                len(self.cameras),
            )

    async def _push_stream(self, cam: Camera) -> None:
        await self._safe_call(self.go2rtc.upsert_stream(cam.camera_id, cam.source_url))

    async def _safe_call(self, coro) -> None:
        try:
            await coro
        except Exception:
            log.exception("API call failed while reconciling stream")

    # -- health / reconnect ------------------------------------------------

    async def _health_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=HEALTH_CHECK_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
            if self._stop.is_set():
                break
            await self._check_health()

    async def _check_health(self) -> None:
        try:
            streams = await self.go2rtc.list_streams()
        except Exception:
            log.exception("Failed to query go2rtc /api/streams for health check")
            return

        now = time.monotonic()
        for camera_id, cam in list(self.cameras.items()):
            state = self.reconnect_state.setdefault(camera_id, ReconnectState(camera_id=camera_id))
            up = await self.go2rtc.is_producer_active(camera_id, streams)
            CAMERA_STATUS.labels(camera_id=camera_id).set(1 if up else 0)

            if up:
                if not state.is_up:
                    log.info("Camera %s is back up", camera_id)
                state.is_up = True
                state.consecutive_failures = 0
                continue

            state.is_up = False
            if now < state.next_attempt_at:
                continue  # still within backoff window — never a tight reconnect loop

            state.consecutive_failures += 1
            backoff = min(
                BACKOFF_INITIAL_SECONDS * (2 ** (state.consecutive_failures - 1)),
                BACKOFF_MAX_SECONDS,
            )
            state.next_attempt_at = now + backoff
            RECONNECT_ATTEMPTS.labels(camera_id=camera_id).inc()
            log.warning(
                "Camera %s reconnect attempt #%d (next retry in %.0fs)",
                camera_id,
                state.consecutive_failures,
                backoff,
            )
            await self._push_stream(cam)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    start_http_server(METRICS_PORT)
    log.info("Prometheus metrics exposed on :%d/metrics", METRICS_PORT)

    async with httpx.AsyncClient() as client:
        catalogue = CatalogueClient(client)
        go2rtc = Go2rtcClient(client)
        renderer = ConfigRenderer()

        supervisor = StreamSupervisor(catalogue, go2rtc, renderer)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, supervisor.request_stop)
            except NotImplementedError:
                # Windows lacks add_signal_handler for SIGTERM; best-effort only.
                pass

        log.info(
            "stream_manager starting: catalogue=%s poll_interval=%ds",
            INGEST_API_URL,
            INGEST_POLL_INTERVAL_SECONDS,
        )
        await supervisor.run()

    log.info("stream_manager shut down cleanly")


if __name__ == "__main__":
    asyncio.run(main())
