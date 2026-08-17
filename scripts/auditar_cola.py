#!/usr/bin/env python3
"""
Audita la cola entera contra las reglas editoriales, sin publicar nada.

Hace lo que preflight() no puede hacer solo: simular la secuencia. preflight
juzga UNA pieza contra el historial de ese momento; esta simulacion publica las
piezas en orden, acumulando historial, que es como se comportan de verdad.

La diferencia importa. Medir las 41 contra un historial congelado marca como
error cada pieza 'cream' posterior a una 'cream', aunque en la secuencia real
haya una 'gold' entre medias.

    python3 scripts/auditar_cola.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import publish, variants  # noqa: E402


def main() -> int:
    historial = list(publish.load_history())
    cola = sorted(
        (json.loads(f.read_text(encoding="utf-8")) for f in publish.QUEUE.glob("*.json")),
        key=lambda u: u.get("publish_at") or "",
    )
    if not cola:
        print("la cola esta vacia")
        return 0

    print(f"historial: {len(historial)} publicadas · cola: {len(cola)} pendientes")
    print(f"rango: {cola[0].get('publish_at','?')[:16]} -> {cola[-1].get('publish_at','?')[:16]}\n")

    bloqueadas = 0
    for u in cola:
        problemas = variants.preflight(u, historial)
        estado = u.get("status")
        marca = "·" if estado == "ready" else "○"
        if problemas:
            bloqueadas += 1
            print(f"  ✗ {u['id']}  {u['core'].get('subject','')[:46]}")
            for p in problemas:
                print(f"       {p}")
        else:
            print(f"  {marca} {u['id']}  {u['card']['variant']:5s} "
                  f"{u['core'].get('subject','')[:52]}")
        # se asume publicada para juzgar la siguiente, igual que en produccion
        simulada = dict(u)
        simulada["results"] = {
            "facebook": {"post_id": "SIMULADO",
                         "published_at": u.get("publish_at")}
        }
        historial.append(simulada)

    borradores = sum(1 for u in cola if u.get("status") != "ready")
    print(f"\nbloqueadas por las reglas: {bloqueadas}/{len(cola)}")
    if borradores:
        print(f"en borrador (no publicables): {borradores}  ·  ○ = draft, · = ready")
    return 1 if bloqueadas else 0


if __name__ == "__main__":
    raise SystemExit(main())
