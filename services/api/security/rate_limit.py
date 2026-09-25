"""Redis-backed fixed-window rate limiting.

Fixed window (not sliding-window or token-bucket) is a deliberate
simplification: it can allow a short burst right at a window boundary,
which is an acceptable trade-off for abuse prevention at hackathon-PoC
scale and much simpler to reason about. If this ever needs to be
airtight, swap `dependency()`'s counting for a sliding-window Lua script
without changing the call sites below.

Separate buckets per route category (per the project brief's rate-limit
policy) mean a burst of failed logins doesn't also lock a user out of
GET /cameras, and vice versa.
"""

from __future__ import annotations

import time

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.redis_client import redis_client

# Paths excluded from the general API bucket: health/metrics scraping
# shouldn't compete with real traffic for budget, static snapshot images
# are read-heavy by nature (a busy alert feed loads many), and the alert
# WebSocket is one long-lived connection per client, not a request burst.
_GENERAL_BUCKET_EXCLUDED_PREFIXES = ("/healthz", "/metrics", "/api/media/", "/api/alerts/stream")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, limit: int, window_seconds: int):
    """Returns a FastAPI dependency enforcing `limit` requests per
    `window_seconds` per client IP within `bucket`.
    """

    async def dependency(request: Request) -> None:
        window_index = int(time.time()) // window_seconds
        key = f"ratelimit:{bucket}:{_client_ip(request)}:{window_index}"

        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": f"Too many requests — limit is {limit} per {window_seconds}s.",
                    "code": "rate_limited",
                },
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency


async def check_rate_limit_raw(bucket: str, client_ip: str, limit: int, window_seconds: int) -> bool:
    """Non-dependency form, used by GeneralRateLimitMiddleware below.
    Returns True if the request is within budget.
    """
    window_index = int(time.time()) // window_seconds
    key = f"ratelimit:{bucket}:{client_ip}:{window_index}"

    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, window_seconds)

    return count <= limit


class GeneralRateLimitMiddleware(BaseHTTPMiddleware):
    """A generous, catch-all budget (default 300 requests / 15 min per
    IP — tuned up from the brief's example 100/15min, since normal
    dashboard usage across several open tabs polling different endpoints
    adds up quickly and a false-positive 429 on routine use is worse than
    a slightly looser ceiling) sitting behind the tighter per-route
    buckets (`rate_limit()` on /auth/login etc.), not replacing them.
    """

    def __init__(self, app, *, limit: int = 300, window_seconds: int = 900) -> None:
        super().__init__(app)
        self._limit = limit
        self._window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(_GENERAL_BUCKET_EXCLUDED_PREFIXES):
            return await call_next(request)

        client_ip = _client_ip(request)
        within_budget = await check_rate_limit_raw(
            "api_general", client_ip, self._limit, self._window_seconds
        )
        if not within_budget:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Too many requests — limit is {self._limit} per {self._window_seconds}s.",
                    "code": "rate_limited",
                },
                headers={"Retry-After": str(self._window_seconds)},
            )

        return await call_next(request)
