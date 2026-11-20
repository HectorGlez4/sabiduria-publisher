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
    def con_n_escenas(n):
        """n escenas con cita y pregunta final: se rellena con contrastes antes de la pregunta."""
        g = _guion_ok()
        relleno = copy.deepcopy(g["escenas"][4])
        cuerpo = g["escenas"][:-1]
        pregunta = g["escenas"][-1]
        while len(cuerpo) + 1 < n:
            cuerpo.append(copy.deepcopy(relleno))
        g["escenas"] = cuerpo[:n - 1] + [pregunta]
        return g

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
    for n in (4, 8):
        g = con_n_escenas(n)
        check(len(g["escenas"]) == n, f"el guion de prueba tiene {n} escenas")
        check(g["escenas"][-1]["tipo"] == "pregunta"
              and any(e["tipo"] == "cita" for e in g["escenas"]),
              f"{n} escenas con cita y pregunta final")
        pr = ng.validar(g, pieza, True)
        check(len(pr) == 1 and "escenas" in pr[0], f"{n} escenas: solo falla el recuento")
    for n in (5, 7):
        check(ng.validar(con_n_escenas(n), pieza, True) == [], f"{n} escenas es válido")
    falso_nombre = _guion_ok()
    falso_nombre["escenas"][0]["pantalla"]["nombre"] = "Viktor Goethe"
    check(any("Goethe" in p and "pantalla.nombre" in p
              for p in ng.validar(falso_nombre, pieza, True)), "pantalla.nombre que la pieza no contiene")
    falso_ano = _guion_ok()
    falso_ano["escenas"][2]["pantalla"]["ano"] = "1889"
    check(any("1889" in p and "pantalla.ano" in p
              for p in ng.validar(falso_ano, pieza, True)), "pantalla.ano que la pieza no contiene")
    check(any("188" in p for p in ng.validar(con_voz("La escribió en 188."), pieza, True)),
          "188 no cuenta como 1888 (palabra completa)")
    check(any("Lo dijo Dios" not in p and "Dios" in p
              for p in ng.validar(con_voz("Lo dijo Dios."), {**pieza, "core": {
                  **pieza["core"], "hook": "", "body": ["Habló la Diosa."],
                  "question": "", "quote": {"text": "", "author": ""}}}, True)),
          "Dios no cuenta como parte de Diosa")
    check(ng.validar([], pieza, True) != [] and ng.validar("x", pieza, True) != [],
          "guion que no es objeto: problema, no excepción")
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
        ruta.write_text("[1, 2]", encoding="utf-8")
        try:
            ng.cargar(ruta)
            check(False, "cargar con raíz que no es objeto lanza ValueError")
        except ValueError as e:
            check(str(ruta) in str(e), "cargar con raíz que no es objeto lanza ValueError con la ruta")


def seccion_pronuncia() -> None:
    print("\n2. Pronunciación y aprobación de nombres")
    from labkit import narrado_pronuncia as npr

    num = npr.numero_en_palabras
    casos = {
        0: "cero", 16: "dieciséis", 21: "veintiuno", 22: "veintidós", 30: "treinta",
        31: "treinta y uno", 100: "cien", 101: "ciento uno", 115: "ciento quince",
        500: "quinientos", 700: "setecientos", 900: "novecientos", 1000: "mil",
        1001: "mil uno", 1500: "mil quinientos", 1888: "mil ochocientos ochenta y ocho",
        1946: "mil novecientos cuarenta y seis", 2000: "dos mil", 2001: "dos mil uno",
        2999: "dos mil novecientos noventa y nueve",
    }
    for n, esperado in casos.items():
        check(num(n) == esperado, f"{n} -> {esperado}")
    for n in (-1, 3000):
        try:
            num(n)
            check(False, f"{n} fuera de rango lanza ValueError")
        except ValueError:
            check(True, f"{n} fuera de rango lanza ValueError")

    guion_ok = _guion_ok()
    tabla_sin_aprobar = {n: {"dicho": n, "aprobado_por": "", "fecha": ""}
                         for n in ("Nietzsche", "Friedrich", "Viktor", "Frankl")}
    tabla_aprobada = {n: {"dicho": n, "aprobado_por": "hec", "fecha": "2026-11-20"}
                      for n in tabla_sin_aprobar}
    tabla_aprobada["Nietzsche"]["dicho"] = "Niche"
    check(npr.pendientes(guion_ok, {}) == ["Frankl", "Friedrich", "Nietzsche", "Viktor"],
          "sin tabla, todos pendientes")
    check(npr.pendientes(guion_ok, tabla_sin_aprobar) != [], "una entrada sin aprobado_por no cuenta")
    check(npr.pendientes(guion_ok, tabla_aprobada) == [], "aprobada, nada pendiente")
    check(npr.para_la_voz("La escribió Nietzsche en 1888.", tabla_aprobada)
          == "La escribió Niche en mil ochocientos ochenta y ocho.", "reescribe solo para la voz")
    check(npr.para_la_voz("Dijo Nietzsche.", tabla_sin_aprobar) == "Dijo Nietzsche.",
          "no reescribe nombres sin aprobar")
    check(npr.para_la_voz("Dijo Nietzschean y 3000 veces.", tabla_aprobada)
          == "Dijo Nietzschean y 3000 veces.", "palabra completa y números fuera de rango intactos")
    check("Frankl" in npr.nombres("Frankl la citó.", tabla_sin_aprobar)
          and "Frankl" not in npr.nombres("Frankl la citó.", {}), "inicial de frase solo si está en la tabla")

    sembrada = json.loads((ROOT / "experiments" / "media-lab" / "narrados" / "pronunciacion.json")
                          .read_text(encoding="utf-8"))
    check(sorted(sembrada) == ["Frankl", "Friedrich", "Nietzsche", "Viktor"], "tabla sembrada con los cuatro nombres")
    check(all(e["aprobado_por"] == "" and e["fecha"] == "" and e["dicho"] for e in sembrada.values()),
          "la tabla sembrada no está aprobada")


SECCIONES = [
    seccion_guion,
    seccion_pronuncia,
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
