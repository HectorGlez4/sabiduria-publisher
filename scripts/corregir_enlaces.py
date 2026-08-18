#!/usr/bin/env python3
"""
Pide a la API el permalink real de lo ya publicado y corrige el registro.

Las primeras publicaciones guardaron una URL CONSTRUIDA a partir del id. En
Instagram eso da un enlace roto —el permalink usa un codigo corto, no el id
numerico del medio— aunque la publicacion este viva. meta.py ya pide el enlace
real; esto arregla los registros anteriores al cambio.

Necesita SDB_PAGE_TOKEN, asi que se ejecuta desde Actions.

    python3 scripts/corregir_enlaces.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import publish  # noqa: E402
from src.platforms import meta  # noqa: E402

CAMPO = {"facebook": "permalink_url", "instagram": "permalink"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    token = os.environ.get("SDB_PAGE_TOKEN")
    if not token:
        sys.exit("falta SDB_PAGE_TOKEN (esto se ejecuta desde Actions)")

    if not publish.PUBLISHED.exists():
        print("no hay nada publicado")
        return 0

    cambios = 0
    for f in sorted(publish.PUBLISHED.glob("*.json")):
        u = publish.load(f)
        tocada = False
        for red, res in (u.get("results") or {}).items():
            campo = CAMPO.get(red)
            if not campo or not res.get("post_id"):
                continue
            real = meta._permalink(res["post_id"], token, campo, "")
            if real and real != res.get("url"):
                print(f"  {u['id']} · {red}")
                print(f"      antes:  {res.get('url')}")
                print(f"      ahora:  {real}")
                if not a.dry_run:
                    res["url"] = real
                tocada = True
                cambios += 1
        if tocada and not a.dry_run:
            publish.save(u, f)

    print(f"\n{cambios} enlace(s) {'a corregir' if a.dry_run else 'corregidos'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
