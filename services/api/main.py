"""Sentinel Grid API service entrypoint.

Beyond serving HTTP, this process also runs the Redis Streams consumers
that turn services/inference's published events into persisted rows/live
pushes (plate_event_consumer for Phase 6, watchlist_engine +
alert_dispatcher for Phase 7) — background asyncio tasks started in the
lifespan below, not separate containers. One process is simpler to
operate at this scale and keeps the write path next to the read path that
depends on it.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import admin, alerts, audit, auth, cameras, evidence, tracking, watchlist
from config import settings
from metrics import MetricsMiddleware, metrics_endpoint
from security.rate_limit import GeneralRateLimitMiddleware
from services import plate_event_consumer, watchlist_engine

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("api.main")

_background_stop = asyncio.Event()
_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    _background_tasks.append(asyncio.create_task(plate_event_consumer.run(_background_stop)))
    _background_tasks.append(asyncio.create_task(watchlist_engine.run(_background_stop)))
    log.info("Background consumers started")
    yield
    _background_stop.set()
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    log.info("Background consumers stopped")


app = FastAPI(title="Sentinel Grid API", version="0.9.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(GeneralRateLimitMiddleware)

# Read-only view onto the `snapshots` Docker volume services/inference
# writes into — see services/media.py for the path <-> URL mapping.
app.mount("/api/media/snapshots", StaticFiles(directory="/data/snapshots", check_dir=False), name="snapshots")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalizes every error response to {detail: str, code: str},
    whether it came from a plain `HTTPException("message")` or one of our
    structured `{"detail": ..., "code": ...}` details (see security/rbac.py
    and api/auth.py).
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        content = exc.detail
    else:
        content = {"detail": str(exc.detail), "code": "error"}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request.", "code": "validation_error"},
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics_route():
    return await metrics_endpoint()


app.include_router(auth.router, prefix="/api")
app.include_router(cameras.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
