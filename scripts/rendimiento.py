#!/usr/bin/env python3
"""
Qué pilar rinde mejor, con los números de Meta y no con impresiones.

    python3 scripts/rendimiento.py

Pide a la API las reacciones, comentarios y veces compartida de cada publicación
de la página, las cruza con el pilar de la pieza que la generó y saca la media
por pilar.

Por qué existe
──────────────
El repo guardaba el id de cada publicación y su hora, y nada más: ninguna
métrica. Así que la pregunta "¿qué funciona mejor?" solo se podía responder
mirando la página y acordándose, que es exactamente como se toman las decisiones
que luego nadie puede revisar.

Las veces compartida importan más que las reacciones: compartir saca la pieza a
un muro ajeno, y ese es el único mecanismo por el que una página crece sin pagar.
Por eso la tabla ordena por ahí.

Solo lee. No escribe nada.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import variants  # noqa: E402
from src.platforms.meta import _get, GRAPH  # noqa: E402

CAMPOS = ("id,created_time,message,shares,"
          "reactions.summary(true).limit(0),comments.summary(true).limit(0)")


def _huella(texto: str) -> str:
    return texto.split("\n")[0].strip().lower()[:60]


def main() -> int:
    page = os.environ["SDB_PAGE_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]

    posts = _get(f"{GRAPH}/{page}/posts",
                 {"fields": CAMPOS, "limit": "100", "access_token": token}).get("data", [])
    print(f"Meta devuelve {len(posts)} publicaciones\n")

    # pieza por huella de su primera línea de Facebook
    pilar_de = {}
    for carpeta in ("published", "queue"):
        for f in (ROOT / "content" / carpeta).glob("*.json"):
            u = json.loads(f.read_text(encoding="utf-8"))
            try:
                pilar_de[_huella(variants.build(u, "facebook")["text"])] = u["pillar"]
            except Exception:
                pass

    por_pilar = collections.defaultdict(lambda: {"n": 0, "reac": 0, "com": 0, "comp": 0})
    sin_pieza = 0
    for p in posts:
        if not p.get("message"):
            continue
        pilar = pilar_de.get(_huella(p["message"]))
        if not pilar:
            sin_pieza += 1
            continue
        d = por_pilar[pilar]
        d["n"] += 1
        d["reac"] += (p.get("reactions") or {}).get("summary", {}).get("total_count", 0)
        d["com"] += (p.get("comments") or {}).get("summary", {}).get("total_count", 0)
        d["comp"] += (p.get("shares") or {}).get("count", 0)

    print(f"{'pilar':16}{'posts':>6}{'compart./post':>15}{'reacc./post':>13}{'coment./post':>14}")
    filas = sorted(por_pilar.items(), key=lambda kv: -kv[1]["comp"] / max(kv[1]["n"], 1))
    for pilar, d in filas:
        n = max(d["n"], 1)
        print(f"  {pilar:14}{d['n']:>6}{d['comp']/n:>15.1f}{d['reac']/n:>13.1f}{d['com']/n:>14.1f}")

    # ── qué mueve la interacción, más allá del pilar ──
    #
    # El pilar es solo una de las variables. La hora, la longitud y si el texto
    # cierra con pregunta son las otras tres que podemos cambiar sin cambiar el
    # contenido, así que son las primeras que conviene mirar.
    import datetime
    from zoneinfo import ZoneInfo
    CDMX = ZoneInfo("America/Mexico_City")

    filas = []
    for p in posts:
        if not p.get("message"):
            continue
        inter = ((p.get("reactions") or {}).get("summary", {}).get("total_count", 0)
                 + (p.get("comments") or {}).get("summary", {}).get("total_count", 0)
                 + (p.get("shares") or {}).get("count", 0))
        cuando = datetime.datetime.fromisoformat(
            p["created_time"].replace("+0000", "+00:00")).astimezone(CDMX)
        filas.append((inter, cuando, len(p["message"]), p["message"]))

    print("\n── las 8 con más interacción ──")
    for inter, cuando, largo, msg in sorted(filas, key=lambda f: -f[0])[:8]:
        print(f"  {inter:>3}  {cuando:%m-%d %H:%M}  {largo:>4} car.  "
              f"{msg.splitlines()[0][:52]}")

    print("\n── por hora de publicación (CDMX) ──")
    porh = collections.defaultdict(lambda: [0, 0])
    for inter, cuando, _, _ in filas:
        porh[cuando.hour][0] += inter
        porh[cuando.hour][1] += 1
    for hh in sorted(porh):
        s, n = porh[hh]
        print(f"  {hh:02d}:00  {n:>3} posts  {s / n:>5.2f} interacc./post")

    print("\n── por longitud del texto ──")
    for a, b in ((0, 400), (400, 700), (700, 1000), (1000, 99999)):
        sel = [f for f in filas if a <= f[2] < b]
        if sel:
            fin = b if b < 99999 else "+"
            print(f"  {a}-{fin} car.  {len(sel):>3} posts  "
                  f"{sum(f[0] for f in sel) / len(sel):>5.2f} interacc./post")

    print("\n── ¿cierra con pregunta? ──")
    for tiene in (True, False):
        sel = [f for f in filas if ("?" in f[3][-300:]) == tiene]
        if sel:
            print(f"  {'con' if tiene else 'sin'} pregunta  {len(sel):>3} posts  "
                  f"{sum(f[0] for f in sel) / len(sel):>5.2f} interacc./post")

    tot = sum(d["n"] for d in por_pilar.values())
    print(f"\n  {tot} publicaciones emparejadas · {sin_pieza} sin pieza en el repo "
          f"(anteriores al publicador)")
    if tot < 20:
        print("  ⚠ pocas publicaciones emparejadas: la media por pilar todavía no "
              "distingue una tendencia de una casualidad.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
