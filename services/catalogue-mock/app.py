"""
services/catalogue-mock/app.py — local stand-in for the Gujarat Police CCTV
gateway's `/api/ingest` catalogue.

The real Sentinel Grid deployment integrates with the gateway's live
`/api/ingest` endpoint. That system isn't reachable from this dev/hackathon
environment yet, so this FastAPI app implements the same contract (see
README.md "Camera catalogue contract") against a small set of public test
RTSP/HLS streams, so the full ingestion stack is runnable and demoable end
to end. The moment the real gateway URL and auth are available, only
INGEST_API_URL (and auth headers, if required) change — no ingestion code
does.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Sentinel Grid Mock Camera Catalogue")


class Protocols(BaseModel):
    rtsp: Optional[str] = None
    whep: Optional[str] = None
    hls: Optional[str] = None


class CameraEntry(BaseModel):
    camera_id: str
    name: str
    department: str
    lat: float
    lon: float
    resolution: str
    codec: str
    fps: float
    # Matches the real gateway's /api/ingest contract, which reports live
    # status per camera alongside its stream properties — see
    # docs/gateway-contract.md. stream_manager.py and
    # services/inference/camera_catalogue_client.py both honor this: a
    # camera the gateway itself already reports as down is skipped rather
    # than attempted and left to fail through the reconnect/backoff path.
    live: bool = True
    protocols: Protocols


# In-memory seed catalogue. `active` cameras (below) is a subset of this
# table so /simulate endpoints can add/remove entries to exercise
# stream_manager's reconciliation logic without editing code.
_ALL_CAMERAS: dict[str, CameraEntry] = {
    "AMC-JUNCTION-001": CameraEntry(
        camera_id="AMC-JUNCTION-001",
        name="Ashram Road Junction",
        department="Ahmedabad Traffic Police",
        lat=23.0225,
        lon=72.5714,
        resolution="1280x720",
        codec="h264",
        fps=25,
        protocols=Protocols(
            rtsp="rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
        ),
    ),
    "AMC-JUNCTION-002": CameraEntry(
        camera_id="AMC-JUNCTION-002",
        name="CG Road Signal",
        department="Ahmedabad Traffic Police",
        lat=23.0339,
        lon=72.5583,
        resolution="1920x1080",
        codec="h264",
        fps=25,
        protocols=Protocols(
            rtsp="rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_175k.mp4"
        ),
    ),
    "SG-HIGHWAY-003": CameraEntry(
        camera_id="SG-HIGHWAY-003",
        name="SG Highway Toll Camera",
        department="Gujarat State Highway Patrol",
        lat=23.0395,
        lon=72.5066,
        resolution="1920x1080",
        codec="h265",
        fps=15,
        protocols=Protocols(hls="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"),
    ),
    "SURAT-RING-ROAD-004": CameraEntry(
        camera_id="SURAT-RING-ROAD-004",
        name="Surat Ring Road Camera",
        department="Surat City Police",
        lat=21.1702,
        lon=72.8311,
        resolution="1280x720",
        codec="h264",
        fps=20,
        # Deliberately unreachable RTSP source, to exercise stream_manager's
        # exponential-backoff reconnect logging during demos.
        protocols=Protocols(rtsp="rtsp://192.0.2.10:554/unreachable"),
    ),
    "VADODARA-CIRCLE-005": CameraEntry(
        camera_id="VADODARA-CIRCLE-005",
        name="Vadodara Sayajigunj Circle",
        department="Vadodara City Police",
        lat=22.3072,
        lon=73.1812,
        resolution="1280x720",
        codec="h264",
        fps=25,
        protocols=Protocols(
            rtsp="rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
        ),
    ),
}

_active_ids: set[str] = set(_ALL_CAMERAS.keys())


@app.get("/api/ingest")
def get_catalogue() -> dict:
    return {"cameras": [_ALL_CAMERAS[cid].model_dump() for cid in sorted(_active_ids)]}


@app.post("/api/ingest/simulate/remove/{camera_id}")
def simulate_remove(camera_id: str) -> dict:
    if camera_id not in _ALL_CAMERAS:
        raise HTTPException(status_code=404, detail="unknown camera_id")
    _active_ids.discard(camera_id)
    return {"camera_id": camera_id, "active": False}


@app.post("/api/ingest/simulate/restore/{camera_id}")
def simulate_restore(camera_id: str) -> dict:
    if camera_id not in _ALL_CAMERAS:
        raise HTTPException(status_code=404, detail="unknown camera_id")
    _active_ids.add(camera_id)
    return {"camera_id": camera_id, "active": True}


@app.post("/api/ingest/simulate/mark-offline/{camera_id}")
def simulate_mark_offline(camera_id: str) -> dict:
    """Distinct from /simulate/remove: this camera stays IN the catalogue
    (as the real gateway would for a camera that's temporarily down) but
    reports live=false, so consumers can skip it without a failed
    connection attempt — the scenario /simulate/remove doesn't cover.
    """
    if camera_id not in _ALL_CAMERAS:
        raise HTTPException(status_code=404, detail="unknown camera_id")
    _ALL_CAMERAS[camera_id].live = False
    return {"camera_id": camera_id, "live": False}


@app.post("/api/ingest/simulate/mark-live/{camera_id}")
def simulate_mark_live(camera_id: str) -> dict:
    if camera_id not in _ALL_CAMERAS:
        raise HTTPException(status_code=404, detail="unknown camera_id")
    _ALL_CAMERAS[camera_id].live = True
    return {"camera_id": camera_id, "live": True}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "camera_count": len(_active_ids)}
