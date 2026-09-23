"""CLI wrapper around POST /evidence/export + GET /evidence/{id}/download
— generates a Section 65B-style evidentiary package for a plate and saves
it locally, without needing the web UI. Requires an account with
evidence:export (T1-T3, per services/api/scripts/seed_users.py).

Usage:
    pip install httpx
    python scripts/export_evidence.py --username sp.ahmedabad --password ChangeMe!2026 --plate GJ01AB1234
"""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx

API_BASE_URL = "http://localhost/api"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--plate", required=True)
    parser.add_argument("--out", default=None, help="Output .zip path (default: ./<plate>-evidence.zip)")
    parser.add_argument("--api-base-url", default=API_BASE_URL)
    args = parser.parse_args()

    out_path = Path(args.out or f"{args.plate}-evidence.zip")

    with httpx.Client(base_url=args.api_base_url, timeout=60.0) as client:
        login = client.post("/auth/login", json={"username": args.username, "password": args.password})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        export_resp = client.post("/evidence/export", headers=headers, json={"plate_text": args.plate})
        export_resp.raise_for_status()
        export_result = export_resp.json()

        print(f"Export {export_result['export_id']}: {export_result['event_count']} event(s), "
              f"sha256={export_result['sha256']}")

        download_resp = client.get(export_result["download_url"], headers=headers)
        download_resp.raise_for_status()
        out_path.write_bytes(download_resp.content)

    print(f"Saved to {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
