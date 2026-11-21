"""
Pruebas de labkit/atipicos.py.

    .venv/bin/python tests/test_atipicos.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments" / "media-lab"))

from labkit import atipicos  # noqa: E402

FALLOS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def falla(fn, *a) -> bool:
    try:
        fn(*a)
    except ValueError:
        return True
    return False


def main() -> int:
    print("\n1. Leer las vistas como las escribe Instagram")
    check(atipicos.leer_vistas("247") == 247, "247")
    check(atipicos.leer_vistas("1,150") == 1150, "1,150 lleva separador de miles")
    check(atipicos.leer_vistas("781k") == 781_000, "781k")
    check(atipicos.leer_vistas("1.2M") == 1_200_000, "1.2M")
    check(falla(atipicos.leer_vistas, "") and falla(atipicos.leer_vistas, "muchas"), "lo ilegible es un error, no un cero")

    print("\n2. El múltiplo es sobre la mediana de la propia cuenta")
    base = [{"vistas": 200, "diseno": "papel"} for _ in range(11)]
    filas = base + [{"vistas": 1000, "diseno": "siena"}, {"vistas": 280, "diseno": "tinta"},
                    {"vistas": 781_000, "fijada": True}, {"vistas": 30, "madura": False}]
    c = atipicos.clasificar(filas)
    check(len(c) == 13, "la fijada y la que no ha madurado no entran")
    check(c[0]["vistas"] == 1000 and c[0]["multiplo"] == 5.0 and c[0]["nivel"] == "senal", "1000 sobre mediana 200 = 5×, señal")
    check(c[0]["mediana"] == 200, "la fijada de 781k no mueve la mediana")
    check(c[1]["multiplo"] == 1.4 and c[1]["nivel"] == "normal", "1,4× es un día normal")
    check(atipicos.clasificar(base + [{"vistas": 400}])[0]["nivel"] == "medio", "2× queda en medio: ni señal ni ruido")
    check(falla(atipicos.clasificar, base[:5]), "con menos de 12 filas no hay mediana fiable")

    print("\n3. Dos cuentas, cada una con su vara de medir")
    grande = [{"cuenta": "@grande", "vistas": 400_000} for _ in range(12)]
    chica = [{"cuenta": "@chica", "vistas": 4_000} for _ in range(11)] + [{"cuenta": "@chica", "vistas": 40_000}]
    c = atipicos.clasificar(grande + chica)
    check(c[0]["cuenta"] == "@chica" and c[0]["multiplo"] == 10.0, "40.000 en la cuenta chica gana a 400.000 en la grande")
    check(all(f["nivel"] == "normal" for f in c if f["cuenta"] == "@grande"), "400.000 es el martes normal de la grande")

    print("\n4. Qué tienen en común")
    c = atipicos.clasificar(filas)
    r = atipicos.por_atributo(c, "diseno")
    check(r[0]["valor"] == "siena" and r[0]["pocas"], "siena va primera, pero marcada como muestra escasa")
    check(next(x for x in r if x["valor"] == "papel")["n"] == 11, "cuenta las filas de cada valor")
    t = atipicos.tercios(c, "diseno")
    check(t["alto"].get("siena") == 1 and "siena" not in t["bajo"], "siena solo aparece en el tercio alto")

    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): {FALLOS}")
        return 1
    print("Los atípicos cumplen sus contratos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
