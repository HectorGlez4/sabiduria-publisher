#!/usr/bin/env python3
"""Cancel only the explicitly named public objects from a rejected lab run."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests


GRAPH = "https://graph.facebook.com/v24.0"
THREADS_GRAPH = "https://graph.threads.net/v1.0"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def delete(url: str, token: str) -> dict:
    response = requests.delete(url, params={"access_token": token}, timeout=45)
    payload = response.json()
    if not response.ok:
        raise RuntimeError(f"DELETE failed ({response.status_code}): {payload}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("run_group_id") != "LAB-SMOKE-001-CANCEL":
        raise SystemExit("refusing cancellation outside LAB-SMOKE-001-CANCEL")

    expected_facebook = "100618132774413_1094337836724209"
    expected_threads = "18066257342767471"
    if manifest.get("facebook_post_id") != expected_facebook:
        raise SystemExit("unexpected Facebook target")
    if manifest.get("threads_post_id") != expected_threads:
        raise SystemExit("unexpected Threads target")

    output = {"run_group_id": manifest["run_group_id"], "started_at": now(), "results": {}}
    try:
        output["results"]["facebook_feed"] = {
            "status": "deleted",
            "target": expected_facebook,
            "response": delete(f"{GRAPH}/{expected_facebook}", os.environ["SDB_PAGE_TOKEN"]),
        }
    except Exception as exc:  # noqa: BLE001
        output["results"]["facebook_feed"] = {"status": "failed", "error": str(exc)[:500]}

    try:
        output["results"]["threads_feed"] = {
            "status": "deleted",
            "target": expected_threads,
            "response": delete(f"{THREADS_GRAPH}/{expected_threads}", os.environ["SDB_THREADS_TOKEN"]),
        }
    except Exception as exc:  # noqa: BLE001
        output["results"]["threads_feed"] = {"status": "failed", "error": str(exc)[:500]}

    output["finished_at"] = now()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print("MEDIA_LAB_CANCEL=" + json.dumps(output, ensure_ascii=False))
    return 1 if any(item["status"] == "failed" for item in output["results"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
