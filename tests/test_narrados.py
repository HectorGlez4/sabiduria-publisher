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
            from labkit import narrado_chequeos as nc_
            medido = nc_.medidas(mezcla)
            check(-16.5 <= medido["lufs"] <= -15.5 and medido["pico"] <= -1.0,
                  f"mezclar clava -16 LUFS en estéreo ({medido['lufs']:.1f}, pico {medido['pico']:.1f})")
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
    guion_140["escenas"][1]["pantalla"]["texto"] = ("palabra " * 20)[:140]
    check(len(guion_140["escenas"][1]["pantalla"]["texto"]) == 140, "la cita de prueba mide exactamente 140")
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


def seccion_chequeos() -> None:
    print("\n5. Chequeos de composición, audio y transcripción")
    import shutil
    import subprocess
    from labkit import narrado_chequeos as nc

    voz = ["Quien tiene un porqué para vivir, soporta casi cualquier cómo.", "La escribió en 1888."]
    check(nc.comparar(voz, "quien tiene un por qué para vivir soporta casi cualquier como la escribio en "
                           "mil ochocientos ochenta y ocho") is None,
          "tolera división de palabras, tildes, comas y cifras")
    check("casi" in (nc.comparar(voz, "quien tiene un porque para vivir soporta cualquier como la escribio "
                                      "en 1888") or ""), "detecta la palabra que falta")
    check(nc.comparar(voz, voz[0] + " " + voz[1] + " gracias por ver") is not None,
          "detecta palabras de más")
    check("gracias" in (nc.comparar(voz, voz[0] + " " + voz[1] + " gracias por ver") or ""),
          "dice cuáles sobran")
    check(nc.comparar(voz, "quien tiene un porque") is not None, "detecta que la voz se corta")

    nombre = ["La escribió Friedrich Nietzsche en 1888."]
    dicho = "la escribio friedrich niche en mil ochocientos ochenta y ocho"
    check(nc.comparar(nombre, dicho) is not None, "sin nombres, «niche» por «Nietzsche» falla")
    check(nc.comparar(nombre, dicho, ["Nietzsche"]) is None, "con nombres, «niche» por «Nietzsche» pasa")
    check(nc.comparar(nombre, dicho, nombres=None) is not None, "nombres=None es el comportamiento estricto")
    check(nc.comparar(nombre, "la escribio friedrich nietzsche ocho", ["Nietzsche"]) is not None,
          "con nombres, una palabra ordinaria que falta sigue fallando")
    check("escribio" in (nc.comparar(nombre, "la friedrich niche en mil ochocientos ochenta y ocho",
                                     ["Nietzsche"]) or ""), "con nombres, el contexto nombra la palabra caída")
    check(nc.comparar(nombre, dicho + " hoy", ["Nietzsche"]) is not None, "con nombres, sobrar sigue fallando")
    check(nc.comparar(nombre, "la escribio friedrich en mil ochocientos ochenta y ocho", ["Nietzsche"]) is not None,
          "el nombre no puede faltar del todo")
    check(nc.comparar(["Frankl la citó."], "Franco la citó.", ["Frankl"]) is None, "un nombre al inicio")

    fixtures = ROOT / "tests" / "fixtures" / "narrados"
    informe = json.loads((fixtures / "hyperframes-check-espiga.json").read_text(encoding="utf-8"))
    p = nc.problemas_de_check(informe)
    check(len(p) == 6 and all("outside_safe_zone" in x for x in p), f"el check de la espiga da 6 avisos de zona segura ({len(p)})")
    check(sum("right edge" in x for x in p) == 4 and sum("bottom edge" in x for x in p) == 2,
          "cuatro por el borde derecho y dos por el inferior")
    check(not any("timeline_track_too_dense" in x or "nested_structure" in x for x in p),
          "se ignoran la densidad y la subcomposición")
    mixto = {"lint": {"findings": [{"code": "x", "severity": "error", "message": "roto"}]},
             "layout": {"findings": [{"code": "text_below_floor", "severity": "warning", "message": "chico"},
                                     {"code": "otra", "severity": "warning", "message": "ruido"}]}}
    base = lambda: copy.deepcopy(informe)  # noqa: E731
    mixto = base()
    mixto["lint"]["findings"] = [{"code": "x", "severity": "error", "message": "roto"}]
    mixto["lint"]["errorCount"] = 1
    mixto["layout"]["findings"] = [{"code": "text_below_floor", "severity": "warning", "message": "chico"},
                                   {"code": "otra", "severity": "warning", "message": "ruido"}]
    check(len(nc.problemas_de_check(mixto, 1)) == 2, "un error y un text_below_floor cuentan; otro aviso no")

    def falla(inf, codigo=0, etiqueta=""):
        try:
            nc.problemas_de_check(inf, codigo)
            check(False, etiqueta)
        except nc.ChequeoFallido as e:
            check(True, etiqueta + f" ({e.motivo[:50]})")
    falla({}, 0, "informe vacío lanza ChequeoFallido")
    falla([], 0, "informe que no es objeto lanza ChequeoFallido")
    falla({"layout": {}}, 1, "solo layout vacío con código 1 lanza ChequeoFallido")
    falla({"layout": None}, 0, "layout nulo lanza ChequeoFallido")
    x = base(); x["browserSkipped"] = True
    falla(x, 0, "browserSkipped lanza ChequeoFallido")
    x = base(); x["layout"]["truncated"] = True
    falla(x, 0, "layout truncado lanza ChequeoFallido")
    x = base(); x["layout"]["samples"] = []
    falla(x, 0, "layout sin muestras lanza ChequeoFallido")
    x = base(); x["contrast"]["enabled"] = False
    falla(x, 0, "contrast desactivado lanza ChequeoFallido")
    x = base(); x["craft"]["enabled"] = False
    falla(x, 0, "craft desactivado lanza ChequeoFallido")
    x = base(); del x["audio"]
    falla(x, 0, "sección ausente lanza ChequeoFallido")
    x = base(); x["runtime"]["errorCount"] = 2
    falla(x, 1, "errorCount mayor que los errores leídos lanza ChequeoFallido")
    x = base(); x["layout"]["findings"] = None
    falla(x, 0, "findings mal formado lanza ChequeoFallido, no AttributeError")
    x = base(); x["layout"]["findings"] = ["texto"]
    falla(x, 0, "findings con elementos que no son objetos lanza ChequeoFallido")
    falla(base(), 2, "código de salida 2 con informe sin errores lanza ChequeoFallido")
    check(len(nc.problemas_de_check(base(), 0)) == 6, "con código 0 el informe real sigue dando 6")
    x = base(); x["motion"]["enabled"] = False
    check(len(nc.problemas_de_check(x)) == 6, "motion desactivado es como en la corrida real: no falla")

    crudo = json.loads((fixtures / "hyperframes-transcripcion-espiga.json").read_text(encoding="utf-8"))
    t = nc.palabras_de_transcripcion(crudo)
    check(set(t) == {"texto", "palabras"} and set(t["palabras"][0]) == {"palabra", "inicio"}
          and t["palabras"][1]["inicio"] == 0.6, "transcribir devuelve solo texto y palabras con inicio")
    espiga = ["Esta frase no es de Viktor Frankl.",
              "Quien tiene un porqué para vivir, soporta casi cualquier cómo.",
              "La escribió Friedrich Nietzsche en 1888, como una intuición.",
              "Frankl la citó con su nombre en 1946, al salir de los campos de concentración.",
              "Una frase pensada en un escritorio, y comprobada en el infierno.",
              "¿Cuál es hoy tu porqué?"]
    check(nc.comparar(espiga, t["texto"], ["Viktor"]) is None,
          "la transcripción real de la espiga compara igual al guion (con «Viktor» como nombre)")
    check(nc.comparar(espiga, t["texto"]) is not None, "sin nombres, «Victor» por «Viktor» falla")

    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        with tempfile.TemporaryDirectory() as d:
            def tono(nombre: str, dur: int, hueco: str | None = None) -> pathlib.Path:
                f = pathlib.Path(d) / nombre
                af = "volume=0.5" + (f",volume=enable='between(t,{hueco})':volume=0" if hueco else "")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                f"sine=frequency=440:duration={dur}:sample_rate=48000", "-af", af, str(f)],
                               check=True)
                return f
            con_hueco = tono("hueco.wav", 30, "10,12")
            s = nc.silencios(con_hueco)
            check(len(s) == 1 and abs(s[0][0] - 10) < 0.1 and abs(s[0][1] - 12) < 0.1, f"silencios halla el hueco {s}")
            m = nc.medidas(con_hueco)
            check(abs(m["duracion"] - 30) < 0.1 and m["lufs"] < 0 and m["pico"] < 0, f"medidas {m}")
            check(any("silencio" in x for x in nc.audio_ok(con_hueco, 28)), "audio_ok reporta el silencio")
            check(not any("silencio" in x for x in nc.audio_ok(con_hueco, 9)),
                  "un silencio posterior al fin de la narración no cuenta")
            check(any("duración" in x for x in nc.audio_ok(tono("corto.wav", 20), 18)),
                  "audio_ok reporta la duración de 20 s")
            check(not any("duración" in x for x in nc.audio_ok(con_hueco, 28)), "30 s no es problema de duración")
            a_caballo = tono("caballo.wav", 30, "10,15")
            check(any("silencio" in x for x in nc.audio_ok(a_caballo, 12)),
                  "un hueco que cruza fin_narracion se reporta")
            cola = tono("cola.wav", 30, "27.7,30")
            check(not any("silencio" in x for x in nc.audio_ok(cola, 27.7)),
                  "la cola natural que empieza en fin_narracion no se reporta")
            sin_fin = tono("sinfin.wav", 30, "20,30")
            sf = nc.silencios(sin_fin)
            check(len(sf) == 1 and abs(sf[0][1] - 30) < 0.1, f"un silencio sin silence_end llega al final {sf}")
            check(any("silencio" in x for x in nc.audio_ok(sin_fin, 28)),
                  "un silencio sin fin que empieza a media narración se reporta")
            mudo = pathlib.Path(d) / "mudo.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "anullsrc=r=48000:cl=mono", "-t", "30", str(mudo)], check=True)
            try:
                nc.audio_ok(mudo, 28)
                check(False, "audio mudo (medida no finita) lanza ChequeoFallido")
            except nc.ChequeoFallido:
                check(True, "audio mudo (medida no finita) lanza ChequeoFallido")
            try:
                nc.medidas(pathlib.Path(d) / "no-existe.wav")
                check(False, "medir un archivo ausente lanza ChequeoFallido")
            except nc.ChequeoFallido as e:
                check(e.herramienta == "ffprobe", "medir un archivo ausente lanza ChequeoFallido")
    else:
        print("  (omitido: falta ffmpeg o ffprobe)")


def seccion_candidatas() -> None:
    print("candidatas, runs y registro")
    import datetime as dt
    import labkit.narrado as nr

    def pieza(pid, cita, verificada=True, cuerpo=("Texto.",), reemision=None):
        d = {"id": pid, "core": {"subject": "s", "hook": "h", "body": list(cuerpo),
                                 "quote": {"text": cita, "attribution_verified": verificada}}}
        if reemision:
            d["reemision_de"] = reemision
        return d

    a = pieza("2026-01-01-a", "Quien tiene un porqué, vive.")
    a2 = pieza("2026-03-01-a-bis", "quien tiene un PORQUÉ vive", reemision="2026-01-01-a")
    b = pieza("2026-02-01-b", "Otra frase distinta")
    c = pieza("2026-02-02-c", "Frase sin verificar", verificada=False)
    d = pieza("2026-02-03-d", "Fuera de lista")
    e = pieza("2026-02-04-e", "Ya hecha antes")
    todas = [a2, a, b, c, d, e]
    cand = ["2026-01-01-a", "2026-03-01-a-bis", "2026-02-01-b", "2026-02-02-c", "2026-02-04-e"]
    ids = [p["id"] for p in nr.elegibles(todas, cand, [])]
    check("2026-01-01-a" in ids and "2026-03-01-a-bis" not in ids, "reedición cuenta una vez y gana el id anterior")
    check("2026-02-02-c" not in ids, "sin atribución verificada se descarta")
    check("2026-02-03-d" not in ids, "fuera de candidatas se descarta")
    reg = [{"pieza": "otra", "cita": nr.clave_cita("Ya hecha antes"), "run": "x", "construido_en": "2026-01-01T00:00:00Z"}]
    check("2026-02-04-e" not in [p["id"] for p in nr.elegibles(todas, cand, reg)], "cita ya registrada se descarta")
    check(ids == sorted(ids), "elegibles sale ordenado por id")
    check(nr.clave_cita("¡Él, así!") == "elasi", "clave: minúsculas, sin tildes ni signos")

    with tempfile.TemporaryDirectory() as t:
        raiz = pathlib.Path(t)
        (raiz / "content" / "published").mkdir(parents=True)
        (raiz / "experiments" / "media-lab" / "narrados").mkdir(parents=True)
        for p in (a, b):
            (raiz / "content" / "published" / f"{p['id']}.json").write_text(json.dumps(p))
        (raiz / "experiments" / "media-lab" / "narrados" / "candidatas.json").write_text(
            json.dumps(["2026-01-01-a", "2026-02-01-b"]))
        ahora = dt.datetime(2026, 11, 20, 9, 5, tzinfo=dt.timezone.utc)
        r = nr.elegir(ahora=ahora, raiz=raiz)
        check(r["pieza"] == "2026-01-01-a" and r["run"] == "NARRADO-20261120-0905", "elegir da pieza y run")
        check(pathlib.Path(r["carpeta"]).is_dir() and r["es_falsa_atribucion"] is True, "elegir crea la carpeta")
        check(not (raiz / "experiments/media-lab/narrados/registro.jsonl").exists(), "elegir no escribe el registro")
        check(nr.es_falsa_atribucion("2026-02-01-b", raiz) and not nr.es_falsa_atribucion("zzz", raiz),
              "es_falsa_atribucion mira candidatas")
        nr.registrar({"pieza": "2026-01-01-a", "cita": nr.clave_cita(a["core"]["quote"]["text"]),
                      "run": r["run"], "construido_en": "2026-11-20T09:05:00Z"}, raiz)
        nr.registrar({"pieza": "2026-02-01-b", "cita": "x", "run": "y", "construido_en": "z"}, raiz)
        lineas = (raiz / "experiments/media-lab/narrados/registro.jsonl").read_text().splitlines()
        check(len(lineas) == 2 and json.loads(lineas[0])["pieza"] == "2026-01-01-a", "registrar añade sin reescribir")
        r2 = nr.elegir(ahora=ahora, raiz=raiz)
        check(r2["pieza"] == "2026-02-01-b", "tras registrar, elegir pasa a la siguiente cita")
        nr.registrar({"pieza": "2026-02-01-b", "cita": nr.clave_cita(b["core"]["quote"]["text"]),
                      "run": "y", "construido_en": "z"}, raiz)
        try:
            nr.elegir(ahora=ahora, raiz=raiz)
            check(False, "sin candidatas lanza SinCandidatas")
        except nr.SinCandidatas:
            check(True, "sin candidatas lanza SinCandidatas")


def seccion_construir() -> None:
    print("\n7. construir: orquestación con herramientas falsas")
    from pathlib import Path
    import labkit.narrado as nr
    from labkit import narrado_chequeos as nc
    from labkit import narrado_guion as ng

    guion = _guion_ok()
    guion["pieza"] = "2026-08-23-tarde"
    pieza = json.loads((ROOT / "content" / "published" / "2026-08-23-tarde.json").read_text(encoding="utf-8"))
    aprobada = {n: {"dicho": n, "aprobado_por": "ensayo", "fecha": "2026-11-20"}
                for n in ("Frankl", "Friedrich", "Nietzsche", "Viktor")}
    voces = [e["voz"] for e in guion["escenas"]]
    cita = guion["escenas"][1]["pantalla"]["texto"]

    def raiz_falsa(d: Path) -> Path:
        (d / "content" / "published").mkdir(parents=True)
        (d / "content" / "published" / "2026-08-23-tarde.json").write_text(json.dumps(pieza), encoding="utf-8")
        carpeta = d / "experiments" / "media-lab" / "narrados"
        (carpeta / "2026-08-23-tarde").mkdir(parents=True)
        (carpeta / "candidatas.json").write_text('["2026-08-23-tarde"]', encoding="utf-8")
        (carpeta / "2026-08-23-tarde" / "guion.json").write_text(json.dumps(guion), encoding="utf-8")
        return d

    class Falsas:
        def __init__(self, transcripcion_mp4=None, problemas_audio=()):
            self.sintetizadas, self.orden = [], []
            self.mp4 = transcripcion_mp4 if transcripcion_mp4 is not None else " ".join(voces)
            self.problemas_audio = list(problemas_audio)

        def herramientas(self):
            def sintetizar(frase, salida, motor="kokoro"):
                self.sintetizadas.append(frase)
                Path(salida).parent.mkdir(parents=True, exist_ok=True)
                Path(salida).write_bytes(b"wav")
                return 2.0 + 0.1 * len(self.sintetizadas)

            def mezclar(wavs, inicios, total, salida):
                self.orden.append("mezclar")
                Path(salida).write_bytes(b"mezcla")

            def transcribir(audio):
                self.orden.append("transcribir")
                if str(audio).endswith(".mp4"):
                    return {"texto": self.mp4, "palabras": []}
                palabras = [{"palabra": w, "inicio": 0.2 * k} for k, w in enumerate(cita.split())]
                return {"texto": cita, "palabras": palabras}

            def render(proyecto):
                self.orden.append("render")
                (Path(proyecto) / "renders").mkdir(exist_ok=True)
                mp4 = Path(proyecto) / "renders" / "a.mp4"
                mp4.write_bytes(b"mp4")
                return mp4

            def fotogramas(proyecto, segundos):
                self.orden.append("fotogramas")
                self.segundos = segundos
                hoja = Path(proyecto) / "contact-sheet.jpg"
                hoja.write_bytes(b"jpg")
                return hoja

            return nr.Herramientas(sintetizar=sintetizar, mezclar=mezclar, transcribir=transcribir,
                                   chequeo=lambda proyecto: [], render=render, fotogramas=fotogramas,
                                   audio_ok=lambda mp4, fin: list(self.problemas_audio))

    # 1. nombres sin aprobar: se para antes de sintetizar
    with tempfile.TemporaryDirectory() as d:
        raiz = raiz_falsa(Path(d))
        f = Falsas()
        sin_aprobar = {n: {"dicho": n, "aprobado_por": "", "fecha": ""} for n in aprobada}
        inf = nr.construir("2026-08-23-tarde", raiz=raiz, tabla=sin_aprobar, herramientas=f.herramientas())
        check(f.sintetizadas == [], "nombres sin aprobar: no se sintetiza nada")
        check(inf["ok"] is False and inf["fase"] == "nombres", "nombres sin aprobar: fase «nombres»")
        check(any("Nietzsche" in p for p in inf["problemas"]) and any("aprobado_por" in p for p in inf["problemas"]),
              "nombres sin aprobar: se nombran y se dice dónde aprobar")
        check((raiz / "experiments/media-lab/narrados/2026-08-23-tarde/build/informe.json").exists(),
              "nombres sin aprobar: deja informe.json")

    # 2. un archivo viejo en build/ desaparece; una corrida limpia deja ok
    with tempfile.TemporaryDirectory() as d:
        raiz = raiz_falsa(Path(d))
        build = raiz / "experiments/media-lab/narrados/2026-08-23-tarde/build"
        build.mkdir()
        (build / "viejo.txt").write_text("x", encoding="utf-8")
        f = Falsas()
        inf = nr.construir("2026-08-23-tarde", raiz=raiz, tabla=aprobada, herramientas=f.herramientas())
        check(not (build / "viejo.txt").exists(), "build/ se vacía antes de construir")
        check(inf["ok"] is True and inf["fase"] == "completo" and inf["problemas"] == [], "corrida limpia: ok")
        check(len(f.sintetizadas) == 6, "una síntesis por frase")
        check("Niche" not in " ".join(f.sintetizadas) and "mil ochocientos ochenta y ocho" in " ".join(f.sintetizadas),
              "la voz lleva las cifras en palabras")
        check(f.orden == ["mezclar", "transcribir", "render", "transcribir", "fotogramas"],
              f"orden de los pasos ({f.orden})")
        check(len(f.segundos) == 6 and f.segundos == sorted(f.segundos), "un fotograma por escena, en orden")
        en_disco = json.loads((build / "informe.json").read_text(encoding="utf-8"))
        check(en_disco == inf, "informe.json es lo que devuelve construir")
        check(Path(inf["mp4"]) == build / "2026-08-23-tarde.mp4" and Path(inf["mp4"]).exists(), "el mp4 queda en build/")
        check(Path(inf["hoja"]) == build / "hoja.jpg" and Path(inf["hoja"]).exists(), "la hoja queda en build/")
        check(inf["veredicto"] is None and inf["duracion"] > 0, "veredicto vacío y duración")
        # 5. repetir da el mismo informe salvo la hora
        f2 = Falsas()
        inf2 = nr.construir("2026-08-23-tarde", raiz=raiz, tabla=aprobada, herramientas=f2.herramientas())
        quitar = lambda x: {k: v for k, v in x.items() if k != "construido_en"}
        check(quitar(inf) == quitar(inf2), "dos corridas dan el mismo informe salvo construido_en")

    # 3. a la transcripción le falta una palabra
    with tempfile.TemporaryDirectory() as d:
        raiz = raiz_falsa(Path(d))
        f = Falsas(transcripcion_mp4=" ".join(voces).replace("soporta ", ""))
        inf = nr.construir("2026-08-23-tarde", raiz=raiz, tabla=aprobada, herramientas=f.herramientas())
        check(inf["ok"] is False and inf["fase"] == "ida_y_vuelta", "palabra perdida: falla la ida y vuelta")
        check(any("soporta" in p for p in inf["problemas"]), "palabra perdida: el problema la nombra")

    # 4. un chequeo de audio que falla para el proceso antes de transcribir el mp4
    with tempfile.TemporaryDirectory() as d:
        raiz = raiz_falsa(Path(d))
        f = Falsas(problemas_audio=["sonoridad -13 LUFS"])
        inf = nr.construir("2026-08-23-tarde", raiz=raiz, tabla=aprobada, herramientas=f.herramientas())
        check(inf["ok"] is False and inf["fase"] == "audio" and inf["problemas"] == ["sonoridad -13 LUFS"],
              "audio: falla y lo cuenta")
        check(f.orden.count("transcribir") == 1, "audio: no se transcribe el mp4")

    # 5. herramienta que lanza ChequeoFallido
    with tempfile.TemporaryDirectory() as d:
        raiz = raiz_falsa(Path(d))
        f = Falsas()
        h = f.herramientas()

        def rota(proyecto):
            raise nc.ChequeoFallido("hyperframes check", "no corrió")
        h = nr.Herramientas(**{**h.__dict__, "chequeo": rota})
        inf = nr.construir("2026-08-23-tarde", raiz=raiz, tabla=aprobada, herramientas=h)
        check(inf["ok"] is False and inf["fase"] == "chequeo" and "no corrió" in inf["problemas"][0],
              "herramienta rota: queda en el informe")

    # 6. revisar
    with tempfile.TemporaryDirectory() as d:
        raiz = raiz_falsa(Path(d))
        try:
            nr.revisar("2026-08-23-tarde", "PASS", raiz=raiz)
            check(False, "revisar sin informe se niega")
        except ValueError:
            check(True, "revisar sin informe se niega")
        inf = nr.construir("2026-08-23-tarde", raiz=raiz, tabla=aprobada, herramientas=Falsas().herramientas())
        out = nr.revisar("2026-08-23-tarde", "PASS", raiz=raiz)
        check(out["veredicto"] == "PASS" and out["ok"] is True, "PASS deja el informe usable")
        out = nr.revisar("2026-08-23-tarde", "FAIL", raiz=raiz)
        check(out["veredicto"] == "FAIL" and out["ok"] is False, "FAIL marca la construcción como inservible")
        try:
            nr.revisar("2026-08-23-tarde", "PASS", raiz=raiz)
            check(False, "revisar sobre un informe no ok se niega")
        except ValueError:
            check(True, "revisar sobre un informe no ok se niega")


SECCIONES = [
    seccion_guion,
    seccion_pronuncia,
    seccion_voz,
    seccion_proyecto,
    seccion_chequeos,
    seccion_candidatas,
    seccion_construir,
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
