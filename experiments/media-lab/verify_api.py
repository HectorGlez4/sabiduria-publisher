#!/usr/bin/env python3
"""Read-only verification of API-published media-lab posts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.platforms.meta import GRAPH, THREADS_GRAPH, _get  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    output = {
        "run_group_id": manifest["run_group_id"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "results": {},
    }
    queries = {
        "facebook": (
            f"{GRAPH}/{manifest['post_ids']['facebook']}",
            "id,permalink_url,created_time,message,full_picture,is_published,is_hidden",
            os.environ["SDB_PAGE_TOKEN"],
        ),
        "instagram": (
            f"{GRAPH}/{manifest['post_ids']['instagram']}",
            "id,permalink,timestamp,caption,media_type,media_url",
            os.environ["SDB_PAGE_TOKEN"],
        ),
        "threads": (
            f"{THREADS_GRAPH}/{manifest['post_ids']['threads']}",
            "id,permalink,timestamp,text,media_type,media_url",
            os.environ["SDB_THREADS_TOKEN"],
        ),
    }
    for platform, (url, fields, token) in queries.items():
        try:
            detail = _get(url, {"fields": fields, "access_token": token})
            output["results"][platform] = {"status": "verified", "detail": detail}
        except Exception as exc:  # noqa: BLE001
            output["results"][platform] = {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print("MEDIA_LAB_VERIFY=" + json.dumps(output, ensure_ascii=False))
    return 1 if any(v["status"] == "failed" for v in output["results"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
