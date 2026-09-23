"""Per-stream latency + throughput benchmark, run from the host against a
live docker compose stack.

This is the tool for producing the real numbers README.md's "Scalability"
section currently only has a methodology for — run it against your actual
50-camera PoC deployment and record what it prints; do not substitute
guessed numbers.

Usage:
    pip install httpx  # only dependency this needs beyond the stdlib
    python scripts/benchmark.py [--duration 60]

Requires the stack to already be running (`docker compose up`) with
INGEST_POLL_INTERVAL_SECONDS already elapsed at least once, so
stream_manager and inference have had a chance to pick up every camera.
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass

import httpx

STREAM_MANAGER_METRICS = "http://localhost:9092/metrics"
INFERENCE_METRICS = "http://localhost:9090/metrics"
API_METRICS = "http://localhost:8000/metrics"

_METRIC_LINE_RE = re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([0-9.eE+-]+|NaN)$')


def parse_prometheus_text(text: str) -> dict[str, list[tuple[dict[str, str], float]]]:
    """{metric_name: [(labels, value), ...]} from a raw /metrics scrape."""
    metrics: dict[str, list[tuple[dict[str, str], float]]] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        match = _METRIC_LINE_RE.match(line)
        if not match:
            continue
        name, label_str, value_str = match.groups()
        labels = {}
        if label_str:
            for pair in label_str.strip("{}").split(","):
                if not pair:
                    continue
                k, _, v = pair.partition("=")
                labels[k] = v.strip('"')
        try:
            metrics.setdefault(name, []).append((labels, float(value_str)))
        except ValueError:
            continue
    return metrics


def sum_metric(metrics: dict, name: str) -> float:
    return sum(v for _, v in metrics.get(name, []))


@dataclass
class Snapshot:
    ts: float
    stream_manager: dict
    inference: dict
    api: dict


def take_snapshot(client: httpx.Client) -> Snapshot:
    return Snapshot(
        ts=time.monotonic(),
        stream_manager=parse_prometheus_text(client.get(STREAM_MANAGER_METRICS).text),
        inference=parse_prometheus_text(client.get(INFERENCE_METRICS).text),
        api=parse_prometheus_text(client.get(API_METRICS).text),
    )


def report(before: Snapshot, after: Snapshot) -> None:
    elapsed = after.ts - before.ts

    active_cameras = sum_metric(after.stream_manager, "sentinelgrid_catalogue_cameras")
    frames = sum_metric(after.inference, "sentinelgrid_frames_processed_total") - sum_metric(
        before.inference, "sentinelgrid_frames_processed_total"
    )
    plates = sum_metric(after.inference, "sentinelgrid_plates_read_total") - sum_metric(
        before.inference, "sentinelgrid_plates_read_total"
    )
    api_requests = sum_metric(after.api, "sentinelgrid_api_requests_total") - sum_metric(
        before.api, "sentinelgrid_api_requests_total"
    )
    reconnects = sum_metric(after.stream_manager, "sentinelgrid_reconnect_attempts_total") - sum_metric(
        before.stream_manager, "sentinelgrid_reconnect_attempts_total"
    )

    print(f"\n--- Benchmark window: {elapsed:.1f}s ---")
    print(f"Cameras tracked (catalogue):        {active_cameras:.0f}")
    print(f"Frames processed:                   {frames:.0f}  ({frames / elapsed:.2f} fps aggregate)")
    print(f"  -> per-camera avg fps:             {(frames / elapsed / active_cameras) if active_cameras else 0:.2f}")
    print(f"Plates read:                        {plates:.0f}")
    print(f"API requests handled:                {api_requests:.0f}  ({api_requests / elapsed:.2f} req/s)")
    print(f"stream_manager reconnect attempts:    {reconnects:.0f}")
    print(
        "\nExtrapolating to 80,000 cameras: multiply per-camera GPU/CPU/memory\n"
        "usage measured here by (80000 / cameras_tracked), then apply a stated\n"
        "safety margin (e.g. 1.5x-2x) for burst load and non-uniform traffic\n"
        "across regions — see README.md 'Scalability' for the full worked\n"
        "methodology this script's output feeds into."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=60, help="Measurement window in seconds")
    args = parser.parse_args()

    with httpx.Client(timeout=10.0) as client:
        print(f"Taking baseline snapshot, then measuring for {args.duration}s...")
        before = take_snapshot(client)
        time.sleep(args.duration)
        after = take_snapshot(client)

    report(before, after)


if __name__ == "__main__":
    main()
