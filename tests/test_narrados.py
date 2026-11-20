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


def seccion_voz() -> None:
    print("\n3. Voz por frases, línea de tiempo y mezcla")
    import shutil
    import subprocess
    from labkit import narrado_voz as nv

    t = nv.linea_de_tiempo(["tachado", "cita", "nombre_ano", "nombre_ano", "contraste", "pregunta"],
                           [2.217, 3.872, 5.223, 6.24, 4.111, 1.207])
    check([round(x["inicio"], 2) for x in t] == [0.6, 3.52, 7.84, 13.51, 20.2, 25.01],
          "inicios con huecos 0,45 y 0,7")
    check(round(t[-1]["fin"] + 2.3, 2) == 28.52, "duración total con cola")
    check(nv.duracion_total(t) == 28.52, "duracion_total suma la cola")
    check(nv.duracion_total(t) == t[-1]["escena_hasta"], "duracion_total == escena_hasta final")
    raro = nv.linea_de_tiempo(["tachado", "cita", "pregunta"], [0.3333333, 1.0005, 0.7777777])
    check(nv.duracion_total(raro) == raro[-1]["escena_hasta"], "duracion_total == escena_hasta con decimales raros")
    try:
        nv.duracion_total([])
        check(False, "duracion_total([]) lanza ValueError")
    except ValueError as e:
        check("vacía" in str(e), "duracion_total([]) lanza ValueError claro")
    check(t[1]["escena_desde"] == round(t[1]["inicio"] - 0.2, 2), "la escena entra 0,2 s antes")
    check(t[0]["escena_desde"] == 0.0 and t[-1]["escena_hasta"] == 28.52,
          "la primera escena arranca en 0 y la última acaba en el total")
    check(all(t[i]["escena_hasta"] == t[i + 1]["escena_desde"] for i in range(len(t) - 1)),
          "cada escena acaba donde empieza la siguiente")

    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)

        def motor_corto(frase: str, salida: pathlib.Path) -> None:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=0.1", str(salida)], check=True)

        # Tope de tiempo y fallo de ffprobe, sin esperas reales.
        orig_lim = nv.LIMITE_HERRAMIENTA
        nv.LIMITE_HERRAMIENTA = 0.2
        try:
            nv._correr([sys.executable, "-c", "import time; time.sleep(5)"], "herramienta-lenta",
                       nv.LIMITE_HERRAMIENTA, "Frase lenta.")
            check(False, "el tope de tiempo lanza VozFallida")
        except nv.VozFallida as e:
            check("herramienta-lenta" in e.motivo and "0.2" in e.motivo and e.frase == "Frase lenta.",
                  "el tope de tiempo nombra herramienta y límite")
        finally:
            nv.LIMITE_HERRAMIENTA = orig_lim
        if shutil.which("ffprobe"):
            try:
                nv._duracion(d / "no-existe.wav", "Frase.")
                check(False, "ffprobe fallido lanza VozFallida")
            except nv.VozFallida as e:
                check("ffprobe" in e.motivo and "0.00" not in e.motivo, "ffprobe fallido se dice como fallo de la herramienta")

        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            nv.MOTORES["corto"] = motor_corto
            try:
                nv.sintetizar("Frase de prueba muy breve.", d / "corto.wav", motor="corto")
                check(False, "VozFallida con un audio de 0,1 s")
            except nv.VozFallida as e:
                check("Frase de prueba muy breve." in str(e) and e.frase == "Frase de prueba muy breve.",
                      "VozFallida nombra la frase")
            finally:
                del nv.MOTORES["corto"]
        else:
            print("  (omitido: falta ffmpeg)")

        if shutil.which("say") and shutil.which("ffmpeg"):
            dur = nv.sintetizar("Hola, esta es una frase de prueba.", d / "hola.wav", motor="say")
            check(dur > 0.3, f"sintetizar con say dura {dur:.2f} s")
            mezcla = d / "mezcla.wav"
            nv.mezclar([d / "hola.wav", d / "hola.wav"], [0.6, 3.0], 6.0, mezcla)
            check(mezcla.exists() and abs(nv._duracion(mezcla) - 6.0) < 0.1, "mezclar respeta el total")
        else:
            print("  (omitido: falta say o ffmpeg)")


def seccion_proyecto() -> None:
    print("\n4. Generador del proyecto HyperFrames")
    from labkit import narrado_proyecto as np_
    from labkit.narrado_voz import duracion_total, linea_de_tiempo

    guion_ok = _guion_ok()
    tipos = [e["tipo"] for e in guion_ok["escenas"]]
    tiempos_ok = linea_de_tiempo(tipos, [3.0, 4.0, 5.0, 6.0, 4.0, 2.0])
    total = duracion_total(tiempos_ok)
    h = np_.html(guion_ok, tiempos_ok, 28.52, None)
    check('data-duration="28.52"' in h and 'data-width="1080"' in h, "raíz con duración y tamaño")
    check(h.count("<section") == 6, "una sección por escena")
    check("cdn.jsdelivr" not in h and "http" not in h.split("<body")[0], "sin red: gsap y fuentes locales")
    check("Voz sintética" in h and "Sabiduría de Bolsillo" in h, "firma y aviso")
    check(h.count('class="p"') == 10, "la cita va palabra a palabra")
    check("Niche" not in h, "la pantalla no lleva la pronunciación")
    check('window.__timelines["main"]' in h and "tl.seek(0)" in h, "línea de tiempo registrada")
    check('data-composition-id="main"' in h and 'id="voz"' in h and "Math.random" not in h
          and "Date.now" not in h, "raíz de HyperFrames, voz y determinismo")
    s1 = tiempos_ok[1]
    check(f'data-start="{s1["escena_desde"]:g}"' in h, "la sección usa escena_desde")
    check(np_.tamano_cita("x" * 60) == 84 and np_.tamano_cita("x" * 140) >= 56,
          "la cita larga encoge sin bajar de 56")
    check(np_.tamano_cita("x" * 70) == 84 and np_.tamano_cita("x" * 200) == 56, "extremos de tamano_cita")
    try:
        np_.tamano_cita("x" * 201)
        check(False, "201 caracteres lanza NoCabe")
    except np_.NoCabe as e:
        check(e.args[:2] == ("cita", 201), "201 caracteres lanza NoCabe")

    guion_largo = copy.deepcopy(guion_ok)
    guion_largo["escenas"][1]["pantalla"]["texto"] = "x" * 201
    try:
        np_.html(guion_largo, tiempos_ok, total, None)
        check(False, "html() con cita de 201 caracteres lanza NoCabe")
    except np_.NoCabe as e:
        check("escena 2" in str(e) and "201" in str(e) and "200" in str(e),
              "NoCabe nombra la escena, la longitud y el máximo")
    guion_140 = copy.deepcopy(guion_ok)
    guion_140["escenas"][1]["pantalla"]["texto"] = " ".join(["palabra"] * 17)[:140]
    px = np_.tamano_cita(guion_140["escenas"][1]["pantalla"]["texto"])
    h140 = np_.html(guion_140, tiempos_ok, total, None)
    check(f'style="font-size:{px}px"' in h140 and 56 <= px < 84, f"cita de 140 caracteres a {px} px en el HTML")
    script = h.split("<script>", 1)[1]
    check("scale" not in script and "rotation" not in script.lower()
          and "Math.random" not in script, "el guion de animación no escala ni rota")

    g = copy.deepcopy(guion_ok)
    g["escenas"][0]["pantalla"]["nombre"] = "A<b> & C\nD"
    h2 = np_.html(g, tiempos_ok, total, None)
    check("A&lt;b&gt; &amp; C<br />D" in h2 and "A<b>" not in h2, "la pantalla se escapa y \\n pasa a <br />")

    palabras = [round(1 + k * 0.1, 3) for k in range(10)]
    h3 = np_.html(guion_ok, tiempos_ok, total, palabras)
    check("1.9" in h3, "usa los tiempos de palabra dados")
    h4 = np_.html(guion_ok, tiempos_ok, total, palabras[:4])
    check(h4.count('class="p"') == 10, "palabras de otra longitud: reparto uniforme")
    for d in ("tinta", "siena"):
        gd = copy.deepcopy(guion_ok)
        gd["diseno"] = d
        check(np_.html(gd, tiempos_ok, total, None).count("<section") == 6, f"diseño {d}")
    gd = copy.deepcopy(guion_ok)
    gd["diseno"] = "inexistente"
    try:
        np_.html(gd, tiempos_ok, total, None)
        check(False, "diseño desconocido lanza ValueError")
    except ValueError:
        check(True, "diseño desconocido lanza ValueError")

    with tempfile.TemporaryDirectory() as d:
        voz = pathlib.Path(d) / "v.wav"
        voz.write_bytes(b"RIFF")
        dest = pathlib.Path(d) / "proy"
        for _ in range(2):  # segunda vez: sobrescribe
            r = np_.escribir(dest, guion_ok, tiempos_ok, total, None, voz)
        check(r == dest and (dest / "index.html").exists(), "escribir devuelve el destino y escribe index.html")
        check(json.loads((dest / "meta.json").read_text(encoding="utf-8")) ==
              {"id": guion_ok["pieza"], "name": guion_ok["pieza"]}, "meta.json")
        check("paths" in json.loads((dest / "hyperframes.json").read_text(encoding="utf-8")),
              "hyperframes.json")
        faltan = [n for n in ("gsap.min.js", "voz.wav", "Lora-Variable.ttf", "Lora-Italic-Variable.ttf",
                              "Poppins-Medium.ttf", "Poppins-Light.ttf") if not (dest / "assets" / n).exists()]
        check(not faltan, f"assets copiados {faltan}")


SECCIONES = [
    seccion_guion,
    seccion_pronuncia,
    seccion_voz,
    seccion_proyecto,
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
