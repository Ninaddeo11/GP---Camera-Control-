"""CLI wrapper around POST /watchlist — adds one or more plates to the
watchlist from the command line, for demo/test setup without opening the
WatchlistConsole UI.

Usage:
    pip install httpx
    python scripts/seed_watchlist.py --username sp.ahmedabad --password ChangeMe!2026 \\
        --plate GJ01AB1234 --reason "Stolen vehicle report #4521" --priority high
"""

from __future__ import annotations

import argparse

import httpx

API_BASE_URL = "http://localhost/api"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--plate", required=True)
    parser.add_argument("--reason", default="")
    parser.add_argument("--priority", default="medium", choices=["low", "medium", "high", "critical"])
    parser.add_argument("--api-base-url", default=API_BASE_URL)
    args = parser.parse_args()

    with httpx.Client(base_url=args.api_base_url, timeout=30.0) as client:
        login = client.post("/auth/login", json={"username": args.username, "password": args.password})
        login.raise_for_status()
        token = login.json()["access_token"]

        resp = client.post(
            "/watchlist",
            headers={"Authorization": f"Bearer {token}"},
            json={"plate_text": args.plate, "reason": args.reason, "priority": args.priority},
        )
        if resp.status_code == 409:
            print(f"{args.plate} is already on the watchlist.")
            return
        resp.raise_for_status()

    print(f"Added {args.plate} to the watchlist (priority={args.priority}).")


if __name__ == "__main__":
    main()
