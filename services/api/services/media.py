"""Converts an inference-container filesystem path
(`/data/snapshots/{camera_id}/{date}/{file}.jpg`) into a URL the frontend
can load, backed by the `snapshots` Docker volume mounted read-only into
this service (see main.py's StaticFiles mount) — the same volume
services/inference writes into.
"""

from __future__ import annotations

_SNAPSHOT_ROOT = "/data/snapshots"
_URL_PREFIX = "/api/media/snapshots"


def snapshot_url(snapshot_path: str) -> str | None:
    if not snapshot_path:
        return None
    if not snapshot_path.startswith(_SNAPSHOT_ROOT):
        return None
    return _URL_PREFIX + snapshot_path[len(_SNAPSHOT_ROOT) :]
