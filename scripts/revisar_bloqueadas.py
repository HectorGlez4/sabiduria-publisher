#!/usr/bin/env python3
"""
Lista las piezas apartadas y, si procede, las devuelve a la cola.

Apartar una pieza evita que atasque la cola, pero sin un sitio donde mirarlas
sería enterrarlas con otro nombre — que es justo el fallo que este repo existe
para eliminar. Esto es ese sitio.

    python3 scripts/revisar_bloqueadas.py                 # listar
    python3 scripts/revisar_bloqueadas.py --reactivar ID  # devolver a 'ready'
    python3 scripts/revisar_bloqueadas.py --reactivar todas
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import publish, variants  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reactivar", metavar="ID",
                    help="id de la pieza, o 'todas'")
    a = ap.parse_args()

    bloqueadas = []
    for f in sorted(publish.QUEUE.glob("*.json")):
        u = publish.load(f)
        if u.get("status") == "blocked":
            bloqueadas.append((u, f))

    if not bloqueadas:
        print("no hay piezas apartadas")
        return 0

    historial = publish.load_history()
    print(f"{len(bloqueadas)} pieza(s) apartada(s):\n")
    for u, f in bloqueadas:
        print(f"  {u['id']}  ·  {u['core'].get('subject', '')[:60]}")
        for r in u.get("blocked_reason") or ["(sin motivo registrado)"]:
            print(f"      {r}")
        if u.get("attempts"):
            print(f"      intentos: {u['attempts']}  ·  ultimo: {u.get('last_attempt', '?')[:19]}")
        # ¿pasaria ahora, si se reactivara?
        perm, _ = variants.preflight_separado(u, historial)
        print(f"      ahora mismo: {'seguiria bloqueada' if perm else 'YA PASARIA — se puede reactivar'}")
        print()

    if not a.reactivar:
        print("Para devolver una a la cola:")
        print("  python3 scripts/revisar_bloqueadas.py --reactivar <id>")
        return 0

    objetivo = [(u, f) for u, f in bloqueadas
                if a.reactivar == "todas" or u["id"] == a.reactivar]
    if not objetivo:
        print(f"'{a.reactivar}' no está entre las apartadas")
        return 1

    for u, f in objetivo:
        perm, _ = variants.preflight_separado(u, historial)
        if perm:
            print(f"  ✗ {u['id']}: sigue sin pasar, no se reactiva")
            for r in perm:
                print(f"      - {r}")
            continue
        u["status"] = "ready"
        u.pop("blocked_reason", None)
        u.pop("attempts", None)
        u.pop("last_attempt", None)
        publish.save(u, f)
        print(f"  ✓ {u['id']} vuelve a la cola")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
