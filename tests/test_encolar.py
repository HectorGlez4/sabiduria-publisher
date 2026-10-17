"""
Qué fotos del banco se quedan fuera del plan de encolar, y cuáles no.

Del 9 al 16 de octubre de 2026 la cola no se rellenó: una foto de Teresa de
Jesús chocaba por tema repetido en 90 días con una cita publicada el 3 de
octubre, el banco se recorre siempre en el mismo orden y la comprobación final
tumbaba el plan entero en cada pasada. Una pieza que valdrá en enero no puede
parar la cola en octubre.

Pero solo lo que arregla el tiempo se aparta. Un fallo que necesita que alguien
lo mire tiene que seguir entrando en el plan para que la comprobación final lo
pare a la vista; apartarlo en silencio sería enterrarlo.

    python3 tests/test_encolar.py
"""
from __future__ import annotations

import datetime
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

import encolar  # noqa: E402
from src import variants  # noqa: E402
from test_reglas import pieza, publicada  # noqa: E402

FALLOS: list[str] = []
AHORA = datetime.datetime(2026, 10, 17, 12, 0, tzinfo=datetime.timezone.utc)


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def main() -> int:
    print("\n1. Tema repetido hace dos semanas: espera")
    hist = [publicada("2026-10-03-tarde", "2026-10-03T19:00:00Z",
                      tema="Teresa de Jesús, «la paciencia todo lo alcanza»")]
    banco = pieza("2026-09-17-extra42", "2026-09-17T19:00:00Z",
                  tema="Teresa de Jesús y las Moradas escritas en 1577")
    m = encolar.en_espera(banco, hist, AHORA)
    check(any("tema repetido" in x for x in m), "sale del plan con el motivo")

    print("\n2. El mismo tema hace cuatro meses: entra")
    hist = [publicada("2026-06-10-tarde", "2026-06-10T19:00:00Z",
                      tema="Teresa de Jesús, «la paciencia todo lo alcanza»")]
    check(encolar.en_espera(banco, hist, AHORA) == [], "pasados 90 días ya no espera")

    print("\n3. Cita ya publicada hace poco: espera")
    hist = [publicada("2026-10-01-tarde", "2026-10-01T19:00:00Z",
                      tema="Otro asunto", cita="La paciencia todo lo alcanza")]
    con_cita = pieza("2026-09-20-extra43", "2026-09-20T19:00:00Z",
                     tema="Un tema distinto", cita="La paciencia todo lo alcanza")
    m = encolar.en_espera(con_cita, hist, AHORA)
    check(any("cita ya publicada" in x for x in m), "sale del plan con el motivo")

    print("\n4. Un fallo que pide revisión NO se aparta")
    sin_atribuir = pieza("2026-09-21-extra44", "2026-09-21T19:00:00Z",
                         tema="Algo nuevo", cita="Una frase nunca publicada")
    sin_atribuir["core"]["quote"]["attribution_verified"] = False
    perm, _ = variants.preflight_separado(sin_atribuir, [], None)
    check(perm != [], "el preflight sí lo bloquea (premisa del caso)")
    check(encolar.en_espera(sin_atribuir, [], AHORA) == [],
          "sigue en el plan para que la comprobación final lo pare a la vista")

    print("\n5. Un choque de color NO se aparta: encolar lo ajusta después")
    hist = [publicada("2026-10-16-tarde", "2026-10-16T19:00:00Z",
                      tema="Otra cosa", variante="gold")]
    dorada = pieza("2026-09-22-extra45", "2026-09-22T19:00:00Z",
                   tema="Algo distinto", variante="gold")
    perm, _ = variants.preflight_separado(dorada, hist, None)
    check(any("variante" in x for x in perm), "el preflight ve el choque (premisa)")
    check(encolar.en_espera(dorada, hist, AHORA) == [], "no espera por el color")

    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El banco aparta lo que el tiempo arregla y nada más.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
