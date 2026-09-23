"""CLI wrapper around POST /cameras/sync — populates the camera registry
from the gateway catalogue. Requires a statewide-scoped account (see
services/api/api/cameras.py sync_cameras for why).

Usage:
    pip install httpx
    python scripts/seed_cameras.py --username dgp.shah --password ChangeMe!2026
"""

from __future__ import annotations

import argparse

import httpx

API_BASE_URL = "http://localhost/api"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--api-base-url", default=API_BASE_URL)
    args = parser.parse_args()

    with httpx.Client(base_url=args.api_base_url, timeout=30.0) as client:
        login = client.post("/auth/login", json={"username": args.username, "password": args.password})
        login.raise_for_status()
        token = login.json()["access_token"]

        resp = client.post("/cameras/sync", headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        result = resp.json()

    print(f"Added: {result['added']}, updated: {result['updated']}")
    if result["unassigned_jurisdiction"]:
        print(f"Unassigned jurisdiction (needs a manual PATCH): {result['unassigned_jurisdiction']}")


if __name__ == "__main__":
    main()
