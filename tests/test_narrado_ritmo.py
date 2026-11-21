"""
Pruebas de labkit/narrado_ritmo.py.

    .venv/bin/python tests/test_narrado_ritmo.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments" / "media-lab"))

from labkit import narrado_ritmo as nr  # noqa: E402
from labkit import narrado_voz as nv  # noqa: E402

FALLOS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def main() -> int:
    guion = json.loads((ROOT / "experiments/media-lab/narrados/2026-08-23-tarde/guion.json").read_text(encoding="utf-8"))
    tipos = [e["tipo"] for e in guion["escenas"]]

    print("\n1. El guion de ejemplo con frases cortas no avisa de nada")
    t = nv.linea_de_tiempo(tipos, [2.2, 3.9, 4.8, 4.9, 4.1, 1.2])
    check(nr.avisos(guion, t) == [], "gancho en 2,8 s, ninguna frase de más de 5 s y «porqué» vuelve al final")

    print("\n2. Cada regla avisa por separado")
    t = nv.linea_de_tiempo(tipos, [3.1, 3.9, 4.8, 4.9, 4.1, 1.2])
    a = nr.avisos(guion, t)
    check(len(a) == 1 and "gancho" in a[0] and "3.7" in a[0], "gancho que acaba en 3,7 s")
    t = nv.linea_de_tiempo(tipos, [2.2, 3.9, 5.2, 6.2, 4.1, 1.2])
    a = nr.avisos(guion, t)
    check(len(a) == 2 and "escena 3" in a[0] and "escena 4" in a[1], "dos frases largas, cada una con su escena")
    sin_eco = json.loads(json.dumps(guion))
    sin_eco["escenas"][-1]["voz"] = "¿Y tú qué harías?"
    a = nr.avisos(sin_eco, nv.linea_de_tiempo(tipos, [2.2, 3.9, 4.8, 4.9, 4.1, 1.2]))
    check(len(a) == 1 and "bucle" in a[0], "última línea sin eco del gancho")
    check(nr.avisos({"escenas": guion["escenas"][:2]}, []) == [], "sin tiempos y con dos escenas no inventa avisos")

    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): {FALLOS}")
        return 1
    print("El ritmo cumple sus contratos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
