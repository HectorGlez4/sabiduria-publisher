#!/usr/bin/env python3
"""Isolated, manifest-driven publisher for public media-lab API runs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.platforms.meta import (  # noqa: E402
    THREADS_GRAPH,
    _get,
    publish_facebook,
    publish_instagram,
    publish_instagram_story,
    publish_story,
    publish_threads,
)


PUBLISHERS = {
    "facebook": publish_facebook,
    "facebook_story": publish_story,
    "instagram": publish_instagram,
    "instagram_story": publish_instagram_story,
    "threads": publish_threads,
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    run_group_id = manifest.get("run_group_id", "")
    if not run_group_id.startswith("LAB-"):
        raise SystemExit("run_group_id must start with LAB-")
    if manifest.get("route") != "api":
        raise SystemExit("this harness only publishes route=api manifests")
    if manifest.get("audience") != "public":
        raise SystemExit("the campaign manifest must explicitly request public audience")

    asset_url = manifest["asset_url"]
    probe = requests.get(asset_url, timeout=45)
    probe.raise_for_status()
    if not probe.headers.get("content-type", "").startswith("image/"):
        raise SystemExit(f"asset is not an image: {probe.headers.get('content-type')}")

    output = {
        "run_group_id": run_group_id,
        "route": "api",
        "asset_url": asset_url,
        "started_at": iso_now(),
        "results": {},
    }
    failed = False
    for platform in manifest["platforms"]:
        started = iso_now()
        try:
            caption = manifest["captions"][platform]
            result = PUBLISHERS[platform](asset_url, caption)
            if platform == "threads":
                detail = _get(
                    f"{THREADS_GRAPH}/{result['post_id']}",
                    {
                        "fields": "id,permalink,timestamp,media_type",
                        "access_token": os.environ["SDB_THREADS_TOKEN"],
                    },
                )
                result["url"] = detail.get("permalink") or result.get("url")
            output["results"][platform] = {
                "status": "submitted",
                "started_at": started,
                "finished_at": iso_now(),
                **result,
            }
        except Exception as exc:  # noqa: BLE001
            failed = True
            output["results"][platform] = {
                "status": "failed",
                "started_at": started,
                "finished_at": iso_now(),
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }
        finally:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")

    output["finished_at"] = iso_now()
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print("MEDIA_LAB_RESULT=" + json.dumps(output, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
