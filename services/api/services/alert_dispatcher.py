"""In-process WebSocket fan-out for live watchlist alerts.

A module-level singleton because this API service runs as one process
(see main.py) — every WebSocket connection and every alert to broadcast
both live here. Each connection is registered with the jurisdiction scope
resolved once at connect time (api/alerts.py); a broadcast only reaches
connections whose scope actually covers the matched camera's jurisdiction
— the same access rule as every other endpoint, just pushed instead of
pulled.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import WebSocket

log = logging.getLogger("api.alert_dispatcher")


class AlertBroadcaster:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, set[uuid.UUID]] = {}

    def register(self, ws: WebSocket, jurisdiction_scope: set[uuid.UUID]) -> None:
        self._connections[ws] = jurisdiction_scope

    def unregister(self, ws: WebSocket) -> None:
        self._connections.pop(ws, None)

    async def broadcast(self, camera_jurisdiction_id: uuid.UUID | None, payload: dict) -> None:
        if camera_jurisdiction_id is None:
            return  # an unassigned camera's alert has no scope to check against — drop it
        dead: list[WebSocket] = []
        for ws, scope in list(self._connections.items()):
            if camera_jurisdiction_id not in scope:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)


broadcaster = AlertBroadcaster()
