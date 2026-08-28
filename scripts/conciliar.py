#!/usr/bin/env python3
"""
Concilia lo que Meta tiene publicado con lo que el repo dice que publicó.

    python3 scripts/conciliar.py            # informe
    python3 scripts/conciliar.py --escribir # además, registra lo que falte

Para qué
────────
El repo es la única memoria de lo publicado, y esa memoria se puede perder: el
`git push` que registra el resultado ocurre DESPUÉS de la llamada a Meta, así
que una carrera entre procesos deja piezas publicadas de verdad y marcadas como
pendientes. La siguiente ejecución las vuelve a publicar.

Pasó el 27 y 28 de agosto: una pieza salió CINCO veces a la página. El fallo de
carrera ya está arreglado, pero la memoria quedó desalineada y nada la realinea
solo — y mientras siga desalineada, se sigue duplicando.

Qué hace
────────
Pide el feed de la página, empareja cada publicación con su pieza por la primera
línea del texto —que es determinista: la deriva `variants.py` de `core`— y saca
tres listas:

  · publicadas en Meta y NO registradas  → se van a republicar
  · duplicadas en Meta                   → hay que borrarlas a mano
  · registradas y ausentes en Meta       → alguien las borró, o el id es viejo

Con --escribir registra las primeras, que es lo único automatizable sin riesgo:
apuntar un id que Meta confirma. Borrar publicaciones NO lo hace este script; es
irreversible y lo decide una persona.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import variants  # noqa: E402
from src.platforms.meta import _get, GRAPH  # noqa: E402


def _primera_linea(texto: str) -> str:
    return texto.split("\n")[0].strip().lower()[:60]


def feed_de_la_pagina(limite: int = 100) -> list[dict]:
    page = os.environ["SDB_PAGE_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]
    d = _get(f"{GRAPH}/{page}/posts",
             {"fields": "id,created_time,message", "limit": str(limite),
              "access_token": token})
    return d.get("data", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--escribir", action="store_true")
    a = ap.parse_args()

    posts = feed_de_la_pagina()
    print(f"Meta devuelve {len(posts)} publicaciones en la página\n")

    # Huella → publicaciones de Meta
    por_huella = collections.defaultdict(list)
    for p in posts:
        if p.get("message"):
            por_huella[_primera_linea(p["message"])].append(p)

    unidades = []
    for carpeta in ("queue", "published"):
        for f in sorted((ROOT / "content" / carpeta).glob("*.json")):
            unidades.append((f, json.loads(f.read_text(encoding="utf-8"))))

    sin_registrar, duplicadas = [], []
    ids_registrados = {x["post_id"].split("_")[-1]
                       for _, u in unidades
                       for x in (u.get("results") or {}).values()
                       if x.get("post_id")}

    for f, u in unidades:
        try:
            huella = _primera_linea(variants.build(u, "facebook")["text"])
        except Exception:
            continue
        encontrados = por_huella.get(huella, [])
        if not encontrados:
            continue
        if len(encontrados) > 1:
            duplicadas.append((u["id"], encontrados))
        nuevos = [p for p in encontrados if p["id"].split("_")[-1] not in ids_registrados]
        marcado = any(x.get("post_id")
                      for k, x in (u.get("results") or {}).items()
                      if k in ("facebook", "facebook_reel"))
        if nuevos and not marcado:
            sin_registrar.append((f, u, nuevos[0]))

    print("── publicadas en Meta y NO registradas (se republicarían) ──")
    if not sin_registrar:
        print("  ninguna")
    for f, u, p in sin_registrar:
        print(f"  {u['id']:24s} → {p['id']}  {p['created_time'][:16]}")

    print("\n── duplicadas en la página (borrar a mano) ──")
    if not duplicadas:
        print("  ninguna")
    for pid, encontrados in duplicadas:
        print(f"  {pid}: {len(encontrados)} copias")
        for p in sorted(encontrados, key=lambda x: x["created_time"]):
            print(f"      {p['created_time'][:16]}  https://www.facebook.com/{p['id']}")

    if a.escribir and sin_registrar:
        for f, u, p in sin_registrar:
            plat = "facebook_reel" if "facebook_reel" in u["targets"] else "facebook"
            u.setdefault("results", {})[plat] = {
                "post_id": p["id"], "published_at": p["created_time"],
                "url": f"https://www.facebook.com/{p['id']}",
                "conciliado": True,
            }
            f.write_text(json.dumps(u, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
            print(f"\n  ✓ registrado {u['id']} ← {p['id']}")
        print("\n  Mover a published/ y decidir el resto lo hace una persona: "
              "una pieza puede tener targets sin publicar todavía.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
