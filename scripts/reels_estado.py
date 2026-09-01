#!/usr/bin/env python3
"""
Qué dice Meta de los reels que creemos haber publicado.

    python3 scripts/reels_estado.py

El repo registra un video_id por cada reel y da la publicación por buena. Pero
el id existe desde la fase `start`: que exista NO prueba que el reel esté
publicado ni que sea visible. La fase `finish` puede devolver éxito y el vídeo
quedar en proceso, rechazado o publicado sin aparecer en la pestaña de Reels.

Este script pregunta por cada uno y enseña su estado real. Solo lee.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.platforms.meta import _get, GRAPH  # noqa: E402


def main() -> int:
    page = os.environ["SDB_PAGE_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]

    print("── lo que la página lista como video_reels ──")
    try:
        d = _get(f"{GRAPH}/{page}/video_reels",
                 {"fields": "id,created_time,description,status",
                  "limit": "25", "access_token": token})
        filas = d.get("data", [])
        print(f"  {len(filas)} reels en la página")
        for r in filas[:15]:
            est = r.get("status") or {}
            print(f"  {r.get('created_time','')[:16]}  {r['id']}  "
                  f"video={est.get('video_status','?')} "
                  f"publish={est.get('publishing_phase',{}).get('status','?')}")
    except Exception as e:
        print(f"  ! no se pudo listar: {str(e)[:200]}")

    print("\n── estado de cada reel que el repo dice haber publicado ──")
    nuestros = []
    for f in sorted((ROOT / "content" / "published").glob("*.json")):
        u = json.loads(f.read_text(encoding="utf-8"))
        x = (u.get("results") or {}).get("facebook_reel") or {}
        if x.get("post_id"):
            nuestros.append((x.get("published_at", "")[:16], u["id"], x["post_id"]))
    for cuando, pieza, vid in sorted(nuestros)[-12:]:
        try:
            r = _get(f"{GRAPH}/{vid}",
                     {"fields": "id,created_time,status,permalink_url,is_reference_only",
                      "access_token": token})
            est = r.get("status") or {}
            print(f"  {cuando}  {pieza:22s} video={est.get('video_status','?'):12s} "
                  f"pub={est.get('publishing_phase',{}).get('status','?'):10s} "
                  f"{r.get('permalink_url','sin permalink')}")
        except Exception as e:
            print(f"  {cuando}  {pieza:22s} ! {str(e)[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
