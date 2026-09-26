"""Prometheus metrics for the api service, exposed at GET /metrics (see
main.py). Complements services/ingestion-config's :9092 and
services/inference's :9090 — see infra/prometheus/prometheus.yml for all
three scrape targets.
"""

from __future__ import annotations

import time

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

REQUESTS_TOTAL = Counter(
    "sentinelgrid_api_requests_total",
    "HTTP requests handled",
    ["method", "path_template", "status_code"],
)
REQUEST_LATENCY_SECONDS = Histogram(
    "sentinelgrid_api_request_latency_seconds",
    "Request handling latency",
    ["method", "path_template"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)
WATCHLIST_MATCHES_TOTAL = Counter(
    "sentinelgrid_watchlist_matches_total",
    "Watchlist matches recorded by services/watchlist_engine.py",
)
PLATE_EVENTS_PERSISTED_TOTAL = Counter(
    "sentinelgrid_plate_events_persisted_total",
    "Plate events persisted by services/plate_event_consumer.py",
)
VEHICLE_EVENTS_PERSISTED_TOTAL = Counter(
    "sentinelgrid_vehicle_events_persisted_total",
    "Finalized vehicle events persisted by services/vehicle_event_consumer.py",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start

        # request.scope["route"].path is the route *template*
        # ("/cameras/{camera_id}"), not the raw URL — keeps the metric's
        # cardinality bounded regardless of how many distinct camera_ids
        # or plates are ever queried.
        route = request.scope.get("route")
        path_template = getattr(route, "path", request.url.path)

        REQUESTS_TOTAL.labels(
            method=request.method, path_template=path_template, status_code=response.status_code
        ).inc()
        REQUEST_LATENCY_SECONDS.labels(method=request.method, path_template=path_template).observe(elapsed)

        return response


async def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
