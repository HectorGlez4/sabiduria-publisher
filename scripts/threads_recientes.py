#!/usr/bin/env python3
"""
Los últimos hilos de la cuenta, según Threads y no según el repo.

    python3 scripts/threads_recientes.py [N]     # por defecto, 30

Solo lee y no imprime el token. Sirve para dos preguntas que el registro del
repo no puede contestar: si un hilo salió de verdad cuando la API devolvió un
error, y qué hilos están duplicados y hay que borrar a mano.
"""
from __future__ import annotations

import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.platforms import meta  # noqa: E402


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    hilos = meta.threads_recientes(n)
    veces = collections.Counter(meta.huella(h.get("text")) for h in hilos)

    for h in hilos:
        huella = meta.huella(h.get("text"))
        marca = f"  ← ×{veces[huella]} DUPLICADO" if veces[huella] > 1 else ""
        print(f"{h.get('timestamp', '?')}  {h['id']}  {huella[:60]}{marca}")
        if marca:
            print(f"      {h.get('permalink', '')}")

    duplicados = sum(1 for c in veces.values() if c > 1)
    print(f"\n{len(hilos)} hilos · {duplicados} textos duplicados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
