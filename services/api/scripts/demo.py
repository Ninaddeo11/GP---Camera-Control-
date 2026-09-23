"""Hackathon demo script: publishes 5 synthetic plate-read events for one
test plate across 3 cameras onto the real `plate_events` Redis Stream —
the exact same stream services/inference publishes to — so they flow
through the real plate_event_consumer and watchlist_engine, then queries
GET /tracking/plate/{plate} and prints the reconstructed route. Also adds
the test plate to the watchlist first, so the same run demonstrates a live
alert too.

This deliberately does NOT write directly to Postgres — publishing onto
Redis and letting the real consumers process it is what actually
demonstrates the pipeline works, not just that the query side does.

Run inside the api container (needs its network access to redis/postgres
and its dependencies):
    docker compose exec api python scripts/demo.py [--plate GJ01AB1234]
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timezone

import httpx
import redis.asyncio as redis

from config import settings

DEMO_CAMERAS = ["AMC-JUNCTION-001", "SG-HIGHWAY-003", "VADODARA-CIRCLE-005"]
API_BASE_URL = "http://localhost:8000/api"
DEMO_USERNAME = "dgp.shah"
DEMO_PASSWORD = "ChangeMe!2026"


async def publish_demo_events(plate: str) -> None:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    now_ms = time.time() * 1000

    # 5 reads across 3 cameras, spaced a few minutes apart in simulated
    # wall-clock time, so vehicle_trace.py's dwell-time and speed-inference
    # logic has something real to compute.
    schedule = [
        (DEMO_CAMERAS[0], 0.93, 0),
        (DEMO_CAMERAS[0], 0.95, 15_000),  # second read at the same camera -> one "stop" with dwell time
        (DEMO_CAMERAS[1], 0.88, 8 * 60_000),
        (DEMO_CAMERAS[2], 0.91, 22 * 60_000),
        (DEMO_CAMERAS[2], 0.97, 22 * 60_000 + 20_000),
    ]

    try:
        for camera_id, confidence, offset_ms in schedule:
            wall_ts_ms = now_ms - (25 * 60_000) + offset_ms  # route finishes ~now, started 25 min ago
            await client.xadd(
                settings.redis_stream_plate_events,
                {
                    "camera_id": camera_id,
                    "track_id": "1",
                    "plate_text": plate,
                    "confidence": f"{confidence:.4f}",
                    "region": plate[:2],
                    "vehicle_class": "car",
                    "bbox_x1": "100", "bbox_y1": "100", "bbox_x2": "300", "bbox_y2": "220",
                    "frame_pts_ms": f"{offset_ms}",
                    "wall_ts_ms": f"{wall_ts_ms:.0f}",
                    "snapshot_path": "",
                },
            )
            print(f"  published: camera={camera_id} confidence={confidence} "
                  f"wall_ts={datetime.fromtimestamp(wall_ts_ms / 1000, tz=timezone.utc).isoformat()}")
    finally:
        await client.aclose()


async def add_to_watchlist(client: httpx.AsyncClient, token: str, plate: str) -> None:
    resp = await client.post(
        f"{API_BASE_URL}/watchlist",
        headers={"Authorization": f"Bearer {token}"},
        json={"plate_text": plate, "reason": "Hackathon demo — flagged for the live demo run", "priority": "high"},
    )
    if resp.status_code not in (201, 409):  # 409 = already on watchlist, fine for a re-run
        resp.raise_for_status()


async def login(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        f"{API_BASE_URL}/auth/login", json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD}
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def main(plate: str) -> None:
    print(f"Demo plate: {plate}\n")

    print("1. Adding plate to watchlist and logging in as State Command...")
    async with httpx.AsyncClient() as client:
        token = await login(client)
        await add_to_watchlist(client, token, plate)

        print("2. Publishing 5 synthetic plate-read events across 3 cameras onto plate_events...")
        await publish_demo_events(plate)

        print("3. Waiting 3s for plate_event_consumer + watchlist_engine to process them...")
        await asyncio.sleep(3.0)

        print("4. Querying GET /tracking/plate/{plate}...\n")
        resp = await client.get(
            f"{API_BASE_URL}/tracking/plate/{plate}", headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        traversal = resp.json()

        print(f"Route for {traversal['plate_text']}: {len(traversal['stops'])} stop(s)")
        for i, stop in enumerate(traversal["stops"], start=1):
            print(
                f"  #{i} {stop['camera_name']} — first seen {stop['first_seen']}, "
                f"dwell {stop['dwell_seconds']:.0f}s, avg confidence {stop['confidence_avg']:.2f}"
                + (f", next leg {stop['inferred_speed_to_next_kmh']} km/h" if stop["inferred_speed_to_next_kmh"] else "")
            )

        print("\n5. Checking for a live watchlist match...")
        resp = await client.get(
            f"{API_BASE_URL}/watchlist/matches?limit=5", headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        matches = resp.json()
        recent = [m for m in matches if m["matched_plate_text"] == plate]
        if recent:
            print(f"  MATCH: {recent[0]['watchlist_plate_text']} matched at {recent[0]['camera_name']} "
                  f"(score {recent[0]['match_score']:.0f}) — visible now in the WatchlistConsole alert feed.")
        else:
            print("  No match recorded yet — the watchlist_engine may still be processing; check again shortly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plate", default="GJ01DM9988", help="Demo plate text (default: GJ01DM9988)")
    args = parser.parse_args()
    asyncio.run(main(args.plate))
