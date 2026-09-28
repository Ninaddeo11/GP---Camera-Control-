"""gateway-adapter — bridges Sentinel Grid to a real external camera
gateway that doesn't speak this platform's assumed `/api/ingest` contract.

docs/gateway-contract.md documents a bare, unauthenticated catalogue API
(`GET /api/ingest` -> id/location/codec/protocols per camera). The real
gateway wired up here (a cookie-authenticated web dashboard at
REAL_GATEWAY_BASE_URL) doesn't match that shape at all: it exposes
`GET /cameras.json` (id + name only, nothing else) behind a login form,
and its video endpoints 403 ("browser required") without a session
cookie plus a browser-like User-Agent/Referer.

Rather than teach every consumer (stream_manager.py, camera_registry_sync.py)
about this one gateway's particular quirks, this adapter translates
between the two: it owns the login/session and the auth headers, exposes
`/api/ingest` in the exact contract shape those consumers already expect,
and proxies the HLS playlist/segments/key through itself so go2rtc's pull
looks like any other plain, unauthenticated HLS source — identical in
shape to the mock catalogue's streams.
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException, Response

log = logging.getLogger("gateway_adapter")
logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")

GATEWAY_BASE_URL = os.environ["REAL_GATEWAY_BASE_URL"].rstrip("/")
GATEWAY_EMAIL = os.environ["REAL_GATEWAY_EMAIL"]
GATEWAY_PASSWORD = os.environ["REAL_GATEWAY_PASSWORD"]
# The URL OTHER services (go2rtc, via stream_manager) use to reach this
# adapter — the docker-internal hostname locally, this service's own
# public URL once deployed. Never the browser-facing origin; nothing
# outside this container talks to the real gateway directly.
ADAPTER_BASE_URL = os.environ.get("ADAPTER_BASE_URL", "http://localhost:9100").rstrip("/")

# The real gateway 403s ("browser required") on a bare request — it's
# checking for a plausible browser User-Agent/Referer, not a JS
# challenge (confirmed: a plain curl with these two headers plus the
# session cookie succeeds).
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": f"{GATEWAY_BASE_URL}/",
}

# Well-known city/locality centroids, matched against substrings in a
# camera's name — real, public coordinates, never fabricated per-camera
# precision the gateway doesn't actually give us. Cameras with no match
# just get no lat/lon, which camera_registry_sync.py already treats as
# "skip GIS placement, don't guess" — never wrong, just less precise.
_PLACE_COORDS: list[tuple[str, float, float]] = [
    ("rajkot", 22.3039, 70.8022),
    ("junagadh", 21.5222, 70.4579),
    ("gandhidham", 23.0754, 70.1337),
    ("patan", 23.8493, 72.1266),
    ("navsari", 20.9467, 72.9520),
    ("bilimora", 20.7642, 72.9558),
    ("gir-somnath", 20.9014, 70.4011),
    ("gir somnath", 20.9014, 70.4011),
    ("dehgam", 23.1667, 72.8167),
    ("adalaj", 23.1667, 72.5833),
    ("paldi", 23.0175, 72.5645),
    ("janpath", 23.0225, 72.5714),
    ("visat", 23.1000, 72.5833),
]


def _guess_coords(name: str) -> tuple[float | None, float | None]:
    lowered = name.lower()
    for token, lat, lon in _PLACE_COORDS:
        if token in lowered:
            return lat, lon
    return None, None


app = FastAPI()

# No automatic redirect-following: the login POST 302-redirects to "/" on
# success, and that root page is behind the same "browser required" check
# as everything else — letting httpx auto-follow it turned a successful
# login into a hard failure, since the followed GET's response status
# (403, before this fix) is what raise_for_status() saw, not the login
# POST's own 302. The Set-Cookie header we actually need arrives on the
# POST response itself; nothing here needs the redirect followed.
_client = httpx.AsyncClient(follow_redirects=False, timeout=20.0)
_session_cookie: str | None = None
_session_lock = asyncio.Lock()


async def _login() -> str:
    resp = await _client.post(
        f"{GATEWAY_BASE_URL}/auth/login",
        data={"email": GATEWAY_EMAIL, "password": GATEWAY_PASSWORD},
        headers=BROWSER_HEADERS,
    )
    if resp.status_code not in (200, 302):
        resp.raise_for_status()
    cookie = resp.cookies.get("sentinel") or _client.cookies.get("sentinel")
    if not cookie:
        raise RuntimeError("gateway login did not yield a session cookie — check credentials")
    log.info("logged into real gateway, session acquired")
    return cookie


async def _ensure_session() -> str:
    global _session_cookie
    async with _session_lock:
        if _session_cookie is None:
            _session_cookie = await _login()
        return _session_cookie


async def _proxied_get(path: str) -> httpx.Response:
    cookie = await _ensure_session()
    resp = await _client.get(
        f"{GATEWAY_BASE_URL}{path}",
        headers={**BROWSER_HEADERS, "Cookie": f"sentinel={cookie}"},
    )
    if resp.status_code in (401, 403):
        # Session expired (or the gateway allows only one session per
        # account and something else just logged in) — re-login once and
        # retry. Under real load this fires from many camera requests at
        # once, all holding the SAME stale cookie: naively re-logging in
        # per request would have each fresh login invalidate the one
        # before it, so nobody's retry ever lands. Only actually log in
        # if `_session_cookie` still equals the stale value this request
        # saw — whoever gets there first refreshes it, everyone else
        # waiting on the lock just reuses that.
        global _session_cookie
        async with _session_lock:
            if _session_cookie == cookie:
                _session_cookie = await _login()
        resp = await _client.get(
            f"{GATEWAY_BASE_URL}{path}",
            headers={**BROWSER_HEADERS, "Cookie": f"sentinel={_session_cookie}"},
        )
    resp.raise_for_status()
    return resp


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/ingest")
async def ingest():
    try:
        resp = await _proxied_get("/cameras.json")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"real gateway unreachable: {exc}") from exc

    cameras = []
    for cam in resp.json():
        camera_id = cam["id"]
        lat, lon = _guess_coords(cam["name"])
        cameras.append(
            {
                "camera_id": camera_id,
                "name": cam["name"],
                "department": "",
                "lat": lat,
                "lon": lon,
                "resolution": "",
                "codec": "h264",
                "fps": 0,
                "live": True,
                "protocols": {"hls": f"{ADAPTER_BASE_URL}/hls/{camera_id}/index.m3u8"},
            }
        )
    return {"cameras": cameras}


@app.get("/hls/{camera_id}/index.m3u8")
async def hls_playlist(camera_id: str):
    resp = await _proxied_get(f"/{camera_id}/index.m3u8")
    return Response(content=resp.content, media_type="application/vnd.apple.mpegurl")


@app.get("/hls/{camera_id}/{segment}")
async def hls_segment(camera_id: str, segment: str):
    resp = await _proxied_get(f"/{camera_id}/{segment}")
    return Response(content=resp.content, media_type="video/mp2t")


@app.get("/enc.key")
async def hls_key():
    # Declared as an origin-absolute URI ("/enc.key") inside every
    # playlist we proxy back, per the real gateway's own m3u8 — so it has
    # to live at this exact top-level path here too, not nested under
    # /hls/{camera_id}/.
    resp = await _proxied_get("/enc.key")
    return Response(content=resp.content, media_type="application/octet-stream")
