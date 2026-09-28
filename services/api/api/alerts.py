"""Live alert WebSocket. Browsers can't attach an Authorization header to a
WebSocket handshake, so the access token travels as a query parameter
instead (`?token=...`) — the only place in this API that JWT isn't a
bearer header. The connection is registered with the caller's jurisdiction
scope resolved once at connect time (see alert_dispatcher.py); a rank or
jurisdiction change takes effect on the next reconnect, same as every REST
endpoint takes effect on its next request.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.rbac import User
from security.jwt import InvalidTokenError, TokenType, decode_token
from security.rbac import get_permission_codes
from services.alert_dispatcher import broadcaster
from services.jurisdiction_service import get_user_scope_jurisdiction_ids

log = logging.getLogger("api.alerts")

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.websocket("/stream")
async def alert_stream(websocket: WebSocket, token: str = "") -> None:
    async with AsyncSessionLocal() as db:
        user = await _authenticate(db, token)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        permission_codes = await get_permission_codes(db, user.role_id)
        if "watchlist:read" not in permission_codes:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        scope_ids = await get_user_scope_jurisdiction_ids(db, user)

    await websocket.accept()
    broadcaster.register(websocket, scope_ids)
    log.info("user=%s connected to alert stream (%d jurisdictions in scope)", user.username, len(scope_ids))

    try:
        while True:
            # No client -> server messages are expected; this just blocks
            # until the browser closes the tab/socket.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.unregister(websocket)
        log.info("user=%s disconnected from alert stream", user.username)


async def _authenticate(db: AsyncSession, token: str) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token, TokenType.ACCESS)
    except InvalidTokenError:
        return None

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user
