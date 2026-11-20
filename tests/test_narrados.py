"""
Pruebas de los reels narrados (experiments/media-lab/labkit/narrado_*.py).

    .venv/bin/python tests/test_narrados.py
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments" / "media-lab"))

FALLOS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def _guion_ok() -> dict:
    return {
        "pieza": "2026-11-10-re55-reel",
        "diseno": "papel",
        "escenas": [
            {"tipo": "tachado", "voz": "Esta frase no es de Viktor Frankl.",
             "pantalla": {"etiqueta": "No es de", "nombre": "Viktor Frankl"}},
            {"tipo": "cita",
             "voz": "Quien tiene un porqué para vivir soporta casi cualquier cómo.",
             "pantalla": {"texto": "Quien tiene un porqué para vivir soporta casi cualquier cómo."}},
            {"tipo": "nombre_ano",
             "voz": "La escribió Friedrich Nietzsche en 1888, como una intuición.",
             "pantalla": {"etiqueta": "La escribió", "nombre": "Friedrich Nietzsche",
                          "ano": "1888"}},
            {"tipo": "nombre_ano",
             "voz": "Frankl la citó con su nombre en 1946, al salir de los campos de concentración.",
             "pantalla": {"etiqueta": "La citó", "nombre": "Viktor Frankl", "ano": "1946",
                          "nota": "al salir de los campos"}},
            {"tipo": "contraste",
             "voz": "Una frase pensada en un escritorio y comprobada en el infierno.",
             "pantalla": {"claro": "pensada en un escritorio", "oscuro": "comprobada en el infierno"}},
            {"tipo": "pregunta", "voz": "¿Cuál es hoy tu porqué?",
             "pantalla": {"texto": "¿Cuál es hoy tu porqué?"}},
        ],
    }


def seccion_guion() -> None:
    print("\n1. Esquema y validador del guion")
    from labkit import narrado_guion as ng

    pieza = json.loads((ROOT / "content" / "published" / "2026-11-10-re55-reel.json")
                       .read_text(encoding="utf-8"))
    ok = _guion_ok()

    def con_tipo(t):
        g = _guion_ok()
        g["escenas"][2]["tipo"] = t
        return g

    def sin(t):
        g = _guion_ok()
        g["escenas"] = [e for e in g["escenas"] if e["tipo"] != t]
        return g

    def con_voz(v):
        g = _guion_ok()
        g["escenas"][4]["voz"] = v
        return g

    pregunta_en_medio = _guion_ok()
    pregunta_en_medio["escenas"].insert(3, pregunta_en_medio["escenas"][-1])
    cuatro = _guion_ok()
    cuatro["escenas"] = cuatro["escenas"][:4]
    ocho = _guion_ok()
    ocho["escenas"] = ocho["escenas"][:5] + ocho["escenas"][2:5] + ocho["escenas"][5:]
    cita_cambiada = _guion_ok()
    cita_cambiada["escenas"][1]["pantalla"]["texto"] = "Quien tiene un porqué soporta todo."
    tres = _guion_ok()
    tres["escenas"][2]["tipo"] = "baile"
    tres["escenas"][3]["voz"] = "Lo dijo Goethe en 1889."
    tres["escenas"][4]["voz"] = ""

    check(ng.TIPOS == ("tachado", "cita", "nombre_ano", "contraste", "pregunta"),
          "TIPOS exactos")
    check(ng.validar(ok, pieza, True) == [], "el guion del spike es válido")
    check(any("tipo" in p for p in ng.validar(con_tipo("baile"), pieza, True)), "tipo desconocido")
    check(any("cita" in p for p in ng.validar(sin("cita"), pieza, True)), "falta la escena cita")
    check(any("última" in p for p in ng.validar(pregunta_en_medio, pieza, True)),
          "pregunta no es la última")
    check(len(ng.validar(cuatro, pieza, True)) >= 1 and len(ng.validar(ocho, pieza, True)) >= 1,
          "5 a 7 escenas")
    check(any("1889" in p for p in ng.validar(con_voz("La escribió en 1889."), pieza, True)),
          "año que la pieza no contiene")
    check(any("Goethe" in p for p in ng.validar(con_voz("Lo dijo Goethe."), pieza, True)),
          "nombre que la pieza no contiene")
    check(any("cita" in p for p in ng.validar(cita_cambiada, pieza, True)),
          "la cita difiere de core.quote.text")
    con_comillas = _guion_ok()
    con_comillas["escenas"][1]["pantalla"]["texto"] = (
        "  «Quien tiene un porqué para vivir soporta casi cualquier cómo.»  ")
    check(ng.validar(con_comillas, pieza, True) == [], "la cita ignora comillas y espacios")
    check(any("tachado" in p for p in ng.validar(ok, pieza, False)),
          "tachado solo en falsas atribuciones")
    check(len(ng.validar(tres, pieza, True)) >= 3, "devuelve todos los problemas, no el primero")
    check(any("vacía" in p for p in ng.validar(con_voz(""), pieza, True)), "voz vacía")
    prohibida = copy.deepcopy(pieza)
    prohibida["do_not_use"] = ["infierno"]
    check(any("infierno" in p for p in ng.validar(ok, prohibida, True)),
          "término de do_not_use en una voz")

    with tempfile.TemporaryDirectory() as d:
        ruta = pathlib.Path(d) / "guion.json"
        ruta.write_text(json.dumps(ok, ensure_ascii=False), encoding="utf-8")
        check(ng.cargar(ruta) == ok, "cargar lee el guion")
        ruta.write_text("{no es json", encoding="utf-8")
        try:
            ng.cargar(ruta)
            check(False, "cargar con JSON roto lanza ValueError")
        except ValueError as e:
            check(str(ruta) in str(e), "cargar con JSON roto lanza ValueError con la ruta")


SECCIONES = [
    seccion_guion,
]


def main() -> int:
    for seccion in SECCIONES:
        seccion()
    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("Los reels narrados cumplen sus contratos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
