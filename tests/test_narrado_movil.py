"""
Pruebas del vídeo en el teléfono (labkit/telefono.py: subir_video, borrar_video, sha256_de_video).
Sin teléfono: `telefono.adb` y `telefono.shell` se sustituyen por dobles que anotan las órdenes.

    .venv/bin/python tests/test_narrado_movil.py
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments" / "media-lab"))

from labkit import telefono  # noqa: E402
from test_media_lab import TelefonoSimulado, con_telefono_simulado, jerarquia, nodo_xml  # noqa: E402

FALLOS: list[str] = []
LINEA = "Row: 0 _id=1000023376, _display_name=narrado-sonda.mp4, duration=27533, width=1080, height=1920"
CONTENIDO = b"video de prueba"
SHA = hashlib.sha256(CONTENIDO).hexdigest()
OTRO_SHA = "0" * 64


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def falla(fn, *a) -> bool:
    try:
        fn(*a)
    except telefono.TelefonoError:
        return True
    return False


class Telefono:
    """Doble de adb/shell: anota las órdenes y responde según un estado mínimo del teléfono."""

    def __init__(self, *, fila_tras: int = 0, sha: str = SHA, ancho: int = 1080, alto: int = 1920,
                 archivo: bool = False, fila: bool = False, consulta_fija: str | None = None,
                 error_en: str | None = None, error_sha: str | None = None):
        self.llamadas: list[str] = []
        self.consultas = 0
        self.fila_tras = fila_tras      # consultas que dicen «No result found.» antes de la fila
        self.sha, self.ancho, self.alto = sha, ancho, alto
        self.archivo, self.fila = archivo, fila
        self.consulta_fija, self.error_en, self.error_sha = consulta_fija, error_en, error_sha

    def adb(self, *args, timeout=60):
        self.llamadas.append("adb " + " ".join(args))
        if args[0] == "push":
            self.archivo = True
        return subprocess.CompletedProcess(args, 0, b"", b"")

    def shell(self, cmd, timeout=60):
        self.llamadas.append("shell " + cmd)
        if self.error_en and cmd.startswith(self.error_en):
            raise telefono.TelefonoError(f"adb shell {cmd}: sin respuesta")
        if cmd.startswith("rm "):
            self.archivo = False
        elif cmd.startswith("content delete"):
            self.fila = False
        elif cmd.startswith("content query"):
            self.consultas += 1
            if self.consulta_fija is not None:
                return self.consulta_fija
            if self.fila or (self.archivo and self.consultas > self.fila_tras):
                self.fila = True
                return (f"Row: 0 _id=7, _display_name=a-1b2c3d4e.mp4, duration=27533, "
                        f"width={self.ancho}, height={self.alto}\n")
            return "No result found.\n"
        elif cmd.startswith("sha256sum"):
            if self.error_sha:
                raise telefono.TelefonoError(self.error_sha)
            if not self.archivo:
                raise telefono.TelefonoError("adb shell sha256sum: No such file or directory")
            return f"{self.sha}  /sdcard/Movies/SabiduriaLab/a-1b2c3d4e.mp4\n"
        return ""

    def ordenes(self) -> list[str]:
        return [c for c in self.llamadas if c.startswith("shell ")]


def con_telefono(fake: Telefono, fn):
    """Ejecuta `fn` con adb, shell, la espera y el sueño sustituidos; todo se restaura al salir."""
    guardado = (telefono.adb, telefono.shell, telefono.ESPERA_MEDIASTORE_S, telefono.time.sleep)
    telefono.adb, telefono.shell = fake.adb, fake.shell
    telefono.ESPERA_MEDIASTORE_S = 0.05
    telefono.time.sleep = lambda s: None
    try:
        return fn()
    finally:
        telefono.adb, telefono.shell, telefono.ESPERA_MEDIASTORE_S, telefono.time.sleep = guardado


def local_temporal(directorio: str) -> pathlib.Path:
    p = pathlib.Path(directorio) / "a-1b2c3d4e.mp4"
    p.write_bytes(CONTENIDO)
    return p


def seccion_puras() -> None:
    print("\n1. Leer la fila de MediaStore y armar la consulta")
    check(telefono.fila_de_video(LINEA, "narrado-sonda.mp4") ==
          {"id": 1000023376, "duracion_ms": 27533, "ancho": 1080, "alto": 1920}, "fila de vídeo")
    check(telefono.fila_de_video(LINEA, "otro.mp4") is None, "otro nombre no casa")
    check(telefono.fila_de_video("No result found.", "narrado-sonda.mp4") is None, "sin filas")
    check("video/media" in telefono.consulta_video("a-1b2c3d4e.mp4"), "consulta en el MediaStore de vídeo")
    check("_id:_display_name:duration:width:height" in telefono.consulta_video("a-1b2c3d4e.mp4"), "proyección completa")
    check(falla(telefono.consulta_video, "a b.mp4") and falla(telefono.consulta_video, "x';rm.mp4"),
          "un nombre no seguro no llega a la consulta")
    dos = LINEA + "\n" + LINEA.replace("_id=1000023376", "_id=1000023999").replace("duration=27533", "duration=1")
    check(telefono.fila_de_video(dos, "narrado-sonda.mp4")["id"] == 1000023999, "con dos filas gana el _id más alto")
    check(telefono.fila_de_video("Row: 0 _id=5, _display_name=x-narrado-sonda.mp4, duration=1, width=1080, height=1920",
                                 "narrado-sonda.mp4") is None, "un nombre que lo contiene no casa")
    check(telefono.sin_filas("No result found.\n") and telefono.sin_filas("") and not telefono.sin_filas(LINEA)
          and not telefono.sin_filas("Error while accessing provider:media"), "sin_filas solo con salida vacía o «No result found.»")
    check(telefono.URI_VIDEOS.endswith("/video/media") and telefono.CARPETA_VIDEOS == "/sdcard/Movies/SabiduriaLab",
          "constantes del vídeo")


def seccion_subir() -> None:
    print("\n2. subir_video")
    nombre = "a-1b2c3d4e.mp4"
    with tempfile.TemporaryDirectory() as d:
        local = local_temporal(d)
        f = Telefono(fila_tras=1)
        r = con_telefono(f, lambda: telefono.subir_video(local, nombre))
        check(r["remoto"] == f"/sdcard/Movies/SabiduriaLab/{nombre}" and r["sha256"] == SHA, "devuelve remoto y sha256")
        check((r["duracion_ms"], r["ancho"], r["alto"]) == (27533, 1080, 1920) and r["subido_en"], "devuelve duración, tamaño y hora")
        check(any(c.startswith("shell mkdir -p /sdcard/Movies/SabiduriaLab") for c in f.llamadas), "crea la carpeta")
        check(any(c.startswith("adb push ") for c in f.llamadas), "sube el archivo")
        check(any("MEDIA_SCANNER_SCAN_FILE" in c for c in f.llamadas), "avisa al escáner")
        check(f.consultas == 2, "sondea hasta que aparece la fila")
        check(not any(c.startswith("shell rm") for c in f.llamadas), "en el camino feliz no borra nada")

        f = Telefono(fila_tras=10**6)
        check(falla(lambda: con_telefono(f, lambda: telefono.subir_video(local, nombre))), "sin fila en MediaStore: error")

        f = Telefono(sha=OTRO_SHA)
        check(falla(lambda: con_telefono(f, lambda: telefono.subir_video(local, nombre))), "hash distinto: error")
        check(not f.archivo and not f.fila and any(c.startswith("shell rm") for c in f.llamadas),
              "hash distinto: borra lo subido")

        f = Telefono(ancho=720, alto=1280)
        check(falla(lambda: con_telefono(f, lambda: telefono.subir_video(local, nombre))), "no es 1080×1920: error")
        check(not f.archivo and not f.fila, "no es 1080×1920: borra lo subido")

        f = Telefono()
        check(falla(lambda: con_telefono(f, lambda: telefono.subir_video(local, "a b.mp4"))), "nombre no seguro: error")
        check(f.llamadas == [], "nombre no seguro: no se envía ninguna orden")

        f = Telefono(fila_tras=10**6)
        try:
            con_telefono(f, lambda: telefono.subir_video(local, nombre))
        except telefono.TelefonoError as e:
            check("no aparece" in str(e) and "no se pudo borrar" not in str(e), "timeout: mensaje original")
        check(not f.archivo and any(c.startswith("shell rm") for c in f.llamadas)
              and any(c.startswith("shell content delete") for c in f.llamadas), "timeout: se mandó el borrado")

        f = Telefono(consulta_fija="Row: 0 _id=7, _display_name=a-1b2c3d4e.mp4, duration=NULL, width=NULL, height=NULL")
        try:
            con_telefono(f, lambda: telefono.subir_video(local, nombre))
        except telefono.TelefonoError as e:
            check("width=NULL" in str(e) and "no aparece" not in str(e), "fila ilegible: el mensaje la cita")

        f = Telefono(sha=OTRO_SHA, error_en="rm ")
        try:
            con_telefono(f, lambda: telefono.subir_video(local, nombre))
        except telefono.TelefonoError as e:
            check("hash distinto" in str(e) and str(e).endswith("y no se pudo borrar"), "limpieza fallida: error original + «y no se pudo borrar»")

        f = Telefono(error_sha="adb shell sha256sum: Permission denied")
        try:
            con_telefono(f, lambda: telefono.subir_video(local, nombre))
        except telefono.TelefonoError as e:
            check("Permission denied" in str(e), "error de sha256sum: se propaga")
        check(not f.archivo, "error de sha256sum: se intentó borrar")


def seccion_borrar() -> None:
    print("\n3. borrar_video y sha256_de_video")
    nombre = "a-1b2c3d4e.mp4"
    f = Telefono(archivo=True, fila=True)
    check(con_telefono(f, lambda: telefono.borrar_video(nombre)) is True, "borra el archivo y la fila")
    check(not f.archivo and not f.fila, "no quedan ni archivo ni fila")
    f = Telefono()
    check(con_telefono(f, lambda: telefono.borrar_video(nombre)) is True, "ya borrado: True, sin error")
    check(falla(lambda: con_telefono(Telefono(), lambda: telefono.borrar_video("x';rm.mp4"))), "nombre no seguro: error")
    check(con_telefono(Telefono(consulta_fija="Error while accessing provider:media"), lambda: telefono.borrar_video(nombre)) is False,
          "error del proveedor: no cuenta como borrado")
    check(con_telefono(Telefono(consulta_fija=LINEA.replace("narrado-sonda", "a-1b2c3d4e")), lambda: telefono.borrar_video(nombre)) is False,
          "queda una fila: False")
    check(falla(lambda: con_telefono(Telefono(archivo=True, error_sha="adb shell sha256sum: Permission denied"),
                                     lambda: telefono.sha256_de_video(nombre))), "sha256sum con otro error: TelefonoError")
    check(con_telefono(Telefono(archivo=True), lambda: telefono.sha256_de_video(nombre)) == SHA, "sha del archivo presente")
    check(con_telefono(Telefono(), lambda: telefono.sha256_de_video(nombre)) is None, "sha de un archivo ausente: None")


# ---------------------------------------------------------------- tarea 3: pie, estado, subir y abrir

FIXTURES = ROOT / "tests" / "fixtures" / "narrados" / "movil"
PIEZA = "2026-08-23-tarde"
IG = "com.instagram.android"


def fixture(nombre: str) -> str:
    return (FIXTURES / nombre).read_text(encoding="utf-8")


def lanza(error, fn, *a) -> bool:
    try:
        fn(*a)
    except error:
        return True
    return False


def con_id(rid: str, extra: str = "") -> str:
    return f'resource-id="{IG}:id/{rid}" {extra}'.strip()


def seccion_pie() -> None:
    print("\n4. narrado_pie.pie")
    import json
    from labkit import narrado_pie

    pieza_ok = json.loads((ROOT / "content" / "published" / f"{PIEZA}.json").read_text(encoding="utf-8"))
    p = narrado_pie.pie(pieza_ok)
    check(p.splitlines()[0] == pieza_ok["core"]["hook"].splitlines()[0], "abre con el gancho de la pieza")
    check(p.rstrip().endswith("Voz sintética"), "cierra con «Voz sintética»")
    check("http" not in p and "#SabiduriaDeBolsillo" in p and len(p) <= 2200, "sin URL, con hashtags, dentro del límite")
    bloques = p.split("\n\n")
    check(bloques[0] == pieza_ok["core"]["hook"] and bloques[1] == pieza_ok["core"]["question"]
          and bloques[-1] == "Voz sintética", "gancho, pregunta, etiquetas y firma separados por una línea en blanco")
    etiquetas = bloques[2].split()
    check(etiquetas[0] == "#SabiduriaDeBolsillo" and all(e.startswith("#") for e in etiquetas)
          and len(etiquetas) <= 12 and len({e.lower() for e in etiquetas}) == len(etiquetas),
          f"etiquetas: la principal primero, sin repetir, como mucho 12 ({etiquetas})")
    sin_pregunta = json.loads(json.dumps(pieza_ok))
    sin_pregunta["core"]["question"] = "  "
    check(lanza(ValueError, narrado_pie.pie, sin_pregunta), "sin pregunta: ValueError")
    larga = json.loads(json.dumps(pieza_ok))
    larga["core"]["hook"] = "palabra " * 300
    check(lanza(ValueError, narrado_pie.pie, larga), "más de 2200 caracteres: ValueError")
    con_url = json.loads(json.dumps(pieza_ok))
    con_url["core"]["question"] = "¿Lo viste en https://ejemplo.org?"
    check(lanza(ValueError, narrado_pie.pie, con_url), "con una URL: ValueError")
    repetidas = json.loads(json.dumps(pieza_ok))
    repetidas["tags"] = {"primary": "#SabiduriaDeBolsillo", "topic": ["#sabiduriadebolsillo", "Nietzsche"]}
    check(narrado_pie.pie(repetidas).split("\n\n")[2] == "#SabiduriaDeBolsillo #Nietzsche",
          "una etiqueta repetida no sale dos veces y a la que le falta se le pone «#»")


def arbol(d: str, *, informe: bool = True, **cambios) -> pathlib.Path:
    """Una pieza construida y revisada en un árbol temporal: guion, mp4 e informe ok con PASS."""
    import json
    raiz = pathlib.Path(d)
    carpeta = raiz / "experiments" / "media-lab" / "narrados" / PIEZA
    build = carpeta / "build"
    build.mkdir(parents=True)
    (carpeta / "guion.json").write_text('{"pieza": "%s"}\n' % PIEZA, encoding="utf-8")
    mp4 = build / f"{PIEZA}.mp4"
    mp4.write_bytes(b"mp4 de prueba")
    if informe:
        datos = {"ok": True, "pieza": PIEZA, "fase": "completo", "mp4": str(mp4), "veredicto": "PASS",
                 "sha256_mp4": hashlib.sha256(mp4.read_bytes()).hexdigest(),
                 "sha256_guion": hashlib.sha256((carpeta / "guion.json").read_bytes()).hexdigest()}
        datos.update(cambios)
        (build / "informe.json").write_text(json.dumps(datos), encoding="utf-8")
    return raiz


def seccion_apto_y_estado() -> None:
    print("\n5. apto_para_publicar y el estado del móvil")
    from labkit import narrado

    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        check(narrado.apto_para_publicar(PIEZA, raiz) == [], "una construcción limpia y con PASS: apta")
    with tempfile.TemporaryDirectory() as d:
        problemas = narrado.apto_para_publicar(PIEZA, arbol(d, informe=False))
        check(len(problemas) == 1 and "informe.json" in problemas[0], f"sin informe.json ({problemas})")
    with tempfile.TemporaryDirectory() as d:
        problemas = narrado.apto_para_publicar(PIEZA, arbol(d, ok=False))
        check(any("ok" in p for p in problemas), f"ok: false ({problemas})")
    with tempfile.TemporaryDirectory() as d:
        problemas = narrado.apto_para_publicar(PIEZA, arbol(d, veredicto=None))
        check(any("veredicto" in p for p in problemas), f"veredicto null ({problemas})")
    with tempfile.TemporaryDirectory() as d:
        problemas = narrado.apto_para_publicar(PIEZA, arbol(d, veredicto="FAIL"))
        check(any("veredicto" in p for p in problemas), f"veredicto FAIL ({problemas})")
    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        mp4 = raiz / "experiments" / "media-lab" / "narrados" / PIEZA / "build" / f"{PIEZA}.mp4"
        mp4.write_bytes(mp4.read_bytes()[:-1] + b"X")
        problemas = narrado.apto_para_publicar(PIEZA, raiz)
        check(any("mp4" in p.lower() and "sha256" in p for p in problemas), f"MP4 con un byte cambiado ({problemas})")
    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        mp4 = raiz / "experiments" / "media-lab" / "narrados" / PIEZA / "build" / f"{PIEZA}.mp4"
        mp4.unlink()
        problemas = narrado.apto_para_publicar(PIEZA, raiz)
        check(any("mp4" in p.lower() for p in problemas), f"sin el MP4 ({problemas})")
    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        guion = raiz / "experiments" / "media-lab" / "narrados" / PIEZA / "guion.json"
        guion.write_text(guion.read_text(encoding="utf-8") + " ", encoding="utf-8")
        problemas = narrado.apto_para_publicar(PIEZA, raiz)
        check(any("guion" in p for p in problemas), f"guion cambiado ({problemas})")
    check(lanza(ValueError, narrado.apto_para_publicar, "../x"), "un id no válido: ValueError")

    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        build = raiz / "experiments" / "media-lab" / "narrados" / PIEZA / "build"
        check(narrado.estado_movil(PIEZA, raiz) == {}, "sin movil.json: estado vacío")
        narrado.guardar_estado_movil(PIEZA, {"paso": "subido", "nombre_remoto": "x.mp4"}, raiz)
        check(narrado.estado_movil(PIEZA, raiz) == {"paso": "subido", "nombre_remoto": "x.mp4"},
              "guardar y leer: mismo estado")
        check(sorted(p.name for p in build.iterdir()) == ["2026-08-23-tarde.mp4", "informe.json", "movil.json"],
              "guardar no deja temporales")
        check(lanza(ValueError, narrado.guardar_estado_movil, PIEZA, {"paso": "publicado"}, raiz),
              "un paso desconocido: ValueError")
        check(narrado.estado_movil(PIEZA, raiz)["paso"] == "subido", "un guardado rechazado no toca el archivo")


class MovilSimulado(TelefonoSimulado):
    """Pantallas con nombre sobre el teléfono simulado: el volcado es la pantalla actual y un toque en el
    centro de un control con transición lleva a la siguiente. Un toque sin transición no cambia nada."""

    def __init__(self, pantallas: dict[str, str], inicial: str, transiciones: list[tuple], **kw):
        super().__init__([pantallas[inicial]], **kw)
        self.pantallas = pantallas
        self.recorrido = [inicial]
        self.transiciones = {(origen, centro): destino for origen, centro, destino in transiciones}

    def ir(self, nombre: str) -> None:
        self.volcados = [self.pantallas[nombre]]
        self.recorrido.append(nombre)

    def tocar(self, x: int, y: int) -> None:
        super().tocar(x, y)
        destino = self.transiciones.get((self.recorrido[-1], (x, y)))
        if destino:
            self.ir(destino)


def centro_de(xml: str, rid: str, desc: str | None = None) -> tuple[int, int]:
    lista = [n for n in telefono.nodos(xml) if n["resource_id"] == f"{IG}:id/{rid}"
             and (desc is None or n["desc"] == desc)]
    assert len(lista) == 1, (rid, desc, len(lista))
    return lista[0]["centro"]


FEED_TAB = nodo_xml("[0,2046][216,2181]", desc="Home", clase="android.widget.FrameLayout",
                    extra=con_id("feed_tab", 'clickable="true"'))
PROFILE_TAB = nodo_xml("[864,2046][1080,2181]", desc="Profil", clase="android.widget.FrameLayout",
                       extra=con_id("profile_tab", 'clickable="true"'))


def xml_perfil_movil(*, propio: bool = True, publicaciones: str | None = "4 191publications") -> str:
    return jerarquia(
        nodo_xml("[317,94][714,252]", texto="sabiduriabolsillo", extra=con_id("action_bar_title")),
        nodo_xml("[40,400][330,560]", desc=publicaciones, clase="android.widget.LinearLayout") if publicaciones else "",
        nodo_xml("[40,900][520,1000]", texto="Modifier le profil" if propio else "S’abonner",
                 clase="android.widget.Button", extra='clickable="true"'),
        FEED_TAB, PROFILE_TAB, alto=2316)


XML_INICIO_MOVIL = jerarquia(
    nodo_xml("[0,94][136,252]", desc="Créer", clase="android.widget.Button",
             extra=con_id("action_bar_left_button", 'clickable="true"')),
    nodo_xml("[900,1500][1000,1600]", desc="Partager", clase="android.widget.ImageView", extra='clickable="true"'),
    FEED_TAB, PROFILE_TAB, alto=2316)
XML_REELS = jerarquia(nodo_xml("[0,94][1080,2046]", desc="Reel de otra cuenta", clase="android.view.View"),
                      FEED_TAB, PROFILE_TAB, alto=2316)
SUBIDO_EN = "2026-11-22T13:30:40+00:00"
DURACION_MS = 27533
OTRO_VIDEO = "vidéo du 21 novembre 2026 15:44"


def escenario(**cambios) -> MovilSimulado:
    """Del Reel de otra cuenta en primer plano al detalle del reel, por la ruta de la sonda del 22 nov."""
    pantallas = {"reels": XML_REELS, "perfil": xml_perfil_movil(), "inicio": XML_INICIO_MOVIL,
                 "galeria": fixture("03-crear.xml"), "editor": fixture("04-editor.xml"),
                 "detalles": fixture("05-detalles.xml")}
    pantallas.update(cambios)
    transiciones = [
        ("perfil", centro_de(pantallas["perfil"], "feed_tab"), "inicio"),
        ("inicio", centro_de(pantallas["inicio"], "action_bar_left_button", "Créer"), "galeria"),
        ("galeria", (540, 876), "editor"),  # la casilla del vídeo del 22 nov a las 14:30 (hora de Madrid)
        ("editor", centro_de(pantallas["editor"], "clips_right_action_button", "Suivant"), "detalles"),
    ]
    return MovilSimulado(pantallas, "reels", transiciones)


def con_cuenta(sim: MovilSimulado, llamadas: list):
    """`exigir_cuenta` sin shell: el enlace profundo abre el perfil y se decide con `perfil_propio`."""
    from labkit import sitio_instagram as si

    def exigir(cuenta: str) -> None:
        llamadas.append(cuenta)
        sim.ir("perfil")
        if si.perfil_propio(telefono.volcado(), cuenta) is not True:
            raise si.CuentaAjena(f"Instagram tiene activa otra cuenta, no {cuenta}")
    return exigir


def correr_abrir(sim: MovilSimulado, raiz: pathlib.Path, ev: pathlib.Path, llamadas: list):
    from labkit import narrado_movil as nm
    original = nm.exigir_cuenta
    nm.exigir_cuenta = con_cuenta(sim, llamadas)
    try:
        return con_telefono_simulado(sim, lambda: nm.abrir(PIEZA, ev, raiz=raiz))
    finally:
        nm.exigir_cuenta = original


def seccion_miniatura() -> None:
    print("\n6. elegir_miniatura")
    from labkit import narrado_movil as nm
    from labkit.pantalla import PantallaInesperada

    galeria = fixture("03-crear.xml")
    m = nm.elegir_miniatura(galeria, SUBIDO_EN, DURACION_MS)
    check("22 novembre 2026 14:30" in m["desc"], "elige la miniatura por la hora de subida")
    check(m["centro"] == (540, 876), f"la casilla, no su etiqueta ({m['centro']})")
    check(lanza(PantallaInesperada, nm.elegir_miniatura, galeria, "2026-11-22T10:00:00+00:00", DURACION_MS),
          "sin miniatura de esa hora, se para")
    dos_iguales = galeria.replace(OTRO_VIDEO, "vidéo du 22 novembre 2026 14:30")
    check(lanza(PantallaInesperada, nm.elegir_miniatura, dos_iguales, SUBIDO_EN, DURACION_MS), "dos que casan, se para")
    try:
        nm.elegir_miniatura(dos_iguales, SUBIDO_EN, DURACION_MS)
    except PantallaInesperada as e:
        check("2" in str(e), f"el error dice cuántas casan ({e})")
    check(lanza(PantallaInesperada, nm.elegir_miniatura, galeria, SUBIDO_EN, 31000),
          "misma hora y otra duración (0:31): no casa")
    check(nm.elegir_miniatura(galeria, "2026-11-22T13:30:59+00:00", DURACION_MS)["desc"] == m["desc"]
          and nm.elegir_miniatura(galeria, "2026-11-22T13:29:05+00:00", DURACION_MS)["desc"] == m["desc"],
          "dentro de un minuto de la hora de la casilla, casa")
    check(lanza(PantallaInesperada, nm.elegir_miniatura, galeria, "2026-11-22T13:31:30+00:00", DURACION_MS),
          "a más de un minuto: no casa")
    foto = galeria.replace("Miniature de la vidéo du 22 novembre", "Miniature de la photo du 22 novembre")
    check(lanza(PantallaInesperada, nm.elegir_miniatura, foto, SUBIDO_EN, DURACION_MS), "una foto de esa hora no cuenta")
    sin_etiqueta = galeria.replace('text="0:28" resource-id="com.instagram.android:id/gallery_grid_item_label"',
                                   'text="0:28" resource-id="com.instagram.android:id/otra_cosa"', 1)
    check(lanza(PantallaInesperada, nm.elegir_miniatura, sin_etiqueta, SUBIDO_EN, DURACION_MS),
          "la etiqueta de otra casilla no vale: sin etiqueta propia no casa")
    check(nm.etiqueta_duracion(27533) == "0:28" and nm.etiqueta_duracion(27499) == "0:27"
          and nm.etiqueta_duracion(61500) == "1:02", "la duración redondeada al segundo, m:ss")
    check(lanza(ValueError, nm.elegir_miniatura, galeria, "2026-11-22T13:30:40", DURACION_MS),
          "una hora sin zona: ValueError")
    check(nm.nombre_remoto(PIEZA, "abcdef0123456789" * 4) == f"{PIEZA}-abcdef01.mp4", "nombre remoto <pieza>-<8 hex>.mp4")


def seccion_subir_paso() -> None:
    print("\n7. narrado_movil.subir")
    from labkit import narrado, narrado_movil as nm

    llamadas: list = []

    def subir_falso(local, nombre):
        llamadas.append((pathlib.Path(local), nombre))
        sha = hashlib.sha256(pathlib.Path(local).read_bytes()).hexdigest()
        return {"remoto": f"/sdcard/Movies/SabiduriaLab/{nombre}", "sha256": sha, "subido_en": SUBIDO_EN,
                "duracion_ms": DURACION_MS, "ancho": 1080, "alto": 1920}

    def correr(raiz, ev, sim=None):
        sim = sim or TelefonoSimulado([jerarquia()])
        original = telefono.subir_video
        telefono.subir_video = subir_falso
        try:
            return sim, con_telefono_simulado(sim, lambda: nm.subir(PIEZA, ev, raiz=raiz))
        finally:
            telefono.subir_video = original

    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d, veredicto=None)
        sim, (res, err) = correr(raiz, pathlib.Path(d) / "ev")
        check(isinstance(err, ValueError) and "veredicto" in str(err), f"sin PASS: ValueError con el problema ({err!r})")
        check(llamadas == [] and narrado.estado_movil(PIEZA, raiz) == {}, "sin PASS: no se sube nada ni se escribe estado")

    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        sim, (res, err) = correr(raiz, pathlib.Path(d) / "ev")
        sha = narrado.estado_movil(PIEZA, raiz).get("sha256", "")
        esperado = f"{PIEZA}-{sha[:8]}.mp4"
        check(err is None and len(llamadas) == 1 and llamadas[0][1] == esperado
              and llamadas[0][0].name == f"{PIEZA}.mp4", f"sube el mp4 del informe con el nombre remoto ({err!r}, {llamadas})")
        estado = narrado.estado_movil(PIEZA, raiz)
        check(estado == res and estado["paso"] == "subido" and estado["nombre_remoto"] == esperado
              and estado["subido_en"] == SUBIDO_EN and estado["duracion_ms"] == DURACION_MS,
              f"estado «subido» con nombre, hora y duración ({estado})")
        check(sim.capturas == ["subir-1.png"] and not sim.prohibidos, "captura al final y sin E/S real")

        llamadas.clear()
        narrado.guardar_estado_movil(PIEZA, {**estado, "paso": "compartido"}, raiz)
        sim, (res, err) = correr(raiz, pathlib.Path(d) / "ev")
        check(isinstance(err, ValueError) and llamadas == [], f"tras compartir no se vuelve a subir ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        llamadas.clear()
        raiz = arbol(d)
        sim, (res, err) = correr(raiz, pathlib.Path(d) / "ev", TelefonoSimulado([jerarquia()], listo=False))
        check(err is not None and llamadas == [], f"teléfono bloqueado: no se sube ({err!r})")


def seccion_abrir() -> None:
    print("\n8. narrado_movil.abrir con el teléfono simulado")
    from labkit import narrado, sitio_instagram as si
    from labkit.pantalla import PantallaInesperada
    from labkit.pasos import TelefonoNoListo

    def preparado(d: str) -> pathlib.Path:
        raiz = arbol(d)
        narrado.guardar_estado_movil(PIEZA, {"paso": "subido", "nombre_remoto": f"{PIEZA}-12345678.mp4",
                                             "sha256": "1" * 64, "subido_en": SUBIDO_EN,
                                             "duracion_ms": DURACION_MS}, raiz)
        return raiz

    toque_tab = centro_de(xml_perfil_movil(), "feed_tab")
    toque_crear = centro_de(XML_INICIO_MOVIL, "action_bar_left_button", "Créer")
    toque_suivant = centro_de(fixture("04-editor.xml"), "clips_right_action_button", "Suivant")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = preparado(d), pathlib.Path(d) / "ev", []
        sim = escenario()
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(err is None, f"camino feliz sin error ({err!r})")
        check(cuentas == ["sabiduriabolsillo"], "exige la cuenta de la marca")
        check(sim.toques == [toque_tab, toque_crear, (540, 876), toque_suivant],
              f"toca, en orden, «Home», «Créer», la casilla elegida y «Suivant» ({sim.toques})")
        check(sim.recorrido == ["reels", "perfil", "inicio", "galeria", "editor", "detalles"],
              f"recorre perfil → inicio → galería → editor → detalles ({sim.recorrido})")
        estado = narrado.estado_movil(PIEZA, raiz)
        check(estado.get("paso") == "abierto" and estado.get("publicaciones_antes") == 4191 and estado == res,
              f"queda «abierto» con publicaciones_antes ({estado})")
        check(sim.capturas == ["abrir-1.png"] and not sim.prohibidos, "captura al final y sin E/S real")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = preparado(d), pathlib.Path(d) / "ev", []
        sim = escenario(perfil=xml_perfil_movil(propio=False))
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(isinstance(err, si.CuentaAjena), f"otra cuenta activa: se para ({err!r})")
        check(toque_crear not in sim.toques and sim.toques == [], "otra cuenta: ningún toque, tampoco «Créer»")
        check(narrado.estado_movil(PIEZA, raiz)["paso"] == "subido", "otra cuenta: el estado sigue «subido»")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = preparado(d), pathlib.Path(d) / "ev", []
        sim = escenario(perfil=xml_perfil_movil(publicaciones=None))
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(isinstance(err, PantallaInesperada) and sim.toques == [],
              f"sin recuento de publicaciones legible: se para sin tocar ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = preparado(d), pathlib.Path(d) / "ev", []
        otra = fixture("03-crear.xml").replace('text="Nouveau reel"', 'text="Nouvelle publication"')
        sim = escenario(galeria=otra)
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(isinstance(err, PantallaInesperada) and "Nouvelle publication" in str(err)
              and sim.toques == [toque_tab, toque_crear], f"la galería abre en otro destino: se para ({err!r}, {sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = preparado(d), pathlib.Path(d) / "ev", []
        dos = fixture("03-crear.xml").replace(OTRO_VIDEO, "vidéo du 22 novembre 2026 14:30")
        sim = escenario(galeria=dos)
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(isinstance(err, PantallaInesperada) and sim.toques == [toque_tab, toque_crear],
              f"dos casillas casan: ninguna se toca ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = preparado(d), pathlib.Path(d) / "ev", []
        sin = fixture("03-crear.xml").replace("vidéo du 22 novembre 2026 14:30", "vidéo du 20 novembre 2026 14:30")
        sim = escenario(galeria=sin)
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(isinstance(err, PantallaInesperada) and "0" in str(err) and sim.toques == [toque_tab, toque_crear],
              f"ninguna casilla casa: se para sin tocar ninguna ({err!r})")
        check(narrado.estado_movil(PIEZA, raiz)["paso"] == "subido", "tras pararse el estado sigue «subido»")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = arbol(d), pathlib.Path(d) / "ev", []
        sim = escenario()
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(isinstance(err, ValueError) and cuentas == [] and sim.volcados_leidos == 0 and sim.toques == [],
              f"sin subir antes: ValueError sin tocar el teléfono ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev, cuentas = preparado(d), pathlib.Path(d) / "ev", []
        sim = escenario()
        sim.listo = False
        res, err = correr_abrir(sim, raiz, ev, cuentas)
        check(isinstance(err, TelefonoNoListo) and cuentas == [] and sim.toques == [],
              f"teléfono bloqueado: se para antes de la cuenta ({err!r})")


SECCIONES = [seccion_puras, seccion_subir, seccion_borrar, seccion_pie, seccion_apto_y_estado, seccion_miniatura,
             seccion_subir_paso, seccion_abrir]


def main() -> int:
    for seccion in SECCIONES:
        seccion()
    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): {FALLOS}")
        return 1
    print("El móvil de los narrados cumple sus contratos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
