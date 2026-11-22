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
    """Una pieza publicada, construida y revisada en un árbol temporal: guion, mp4 e informe ok con PASS."""
    import json
    import shutil
    raiz = pathlib.Path(d)
    carpeta = raiz / "experiments" / "media-lab" / "narrados" / PIEZA
    build = carpeta / "build"
    build.mkdir(parents=True)
    (carpeta / "guion.json").write_text('{"pieza": "%s"}\n' % PIEZA, encoding="utf-8")
    mp4 = build / f"{PIEZA}.mp4"
    mp4.write_bytes(b"mp4 de prueba")
    publicadas = raiz / "content" / "published"  # la cita de la pieza: `ya_compartida` cruza el registro con ella
    publicadas.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "content" / "published" / f"{PIEZA}.json", publicadas)
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


# ---------------------------------------------------------------- tarea 4: pie, mención IA y cruces

BARRA = {"share_button": (563, 2001, 1035, 2125), "save_draft_button": (45, 2001, 518, 2125)}
FRANJA = (251, 1961)  # bajo la barra de acción y sobre la barra de «Partager», en 05/06/07
DY_FIN = 150  # lo que sube la lista entre 06 y la pantalla «fin», con todas las filas enteras


def pie_de_prueba() -> str:
    import json
    from labkit import narrado_pie
    return narrado_pie.pie(json.loads((ROOT / "content" / "published" / f"{PIEZA}.json").read_text(encoding="utf-8")))


def con_pie(xml: str, pie: str) -> str:
    """05 con el pie escrito en el campo, escapado como lo escribe uiautomator."""
    import html
    vacio = 'text="Écrivez une légende et ajoutez des hashtags…" resource-id="com.instagram.android:id/caption_input_text_view"'
    assert vacio in xml
    escrito = html.escape(pie, quote=True).replace("\n", "&#10;")
    return xml.replace(vacio, f'text="{escrito}" resource-id="com.instagram.android:id/caption_input_text_view"')


def pantalla_fin() -> str:
    """06 con la lista DY_FIN px más arriba: la fila de Facebook, que en 06 queda cortada contra la barra de abajo,
    sale entera (sus bounds de verdad: 192 px de fila, como la de Threads). Lo que sube por encima de la franja queda
    detrás de la barra de acción, como en los volcados reales (uiautomator no recorta al padre)."""
    import re
    xml = fixture("06-detalles-abajo.xml")
    for cortado, entero in (("[0,1846][1080,1961]", "[0,1846][1080,2038]"),
                            ("[169,1946][844,1961]", "[169,1946][844,1995]"),
                            ("[889,1897][1035,1961]", "[889,1897][1035,1987]")):
        assert xml.count(cortado) >= 1, cortado  # la fila de Facebook son dos nodos con las mismas bounds
        xml = xml.replace(cortado, entero)

    def mover(m):
        x1, y1, x2, y2 = map(int, m.groups())
        if FRANJA[0] < y1 < FRANJA[1]:
            y1, y2 = y1 - DY_FIN, y2 - DY_FIN
        return f'bounds="[{x1},{y1}][{x2},{y2}]"'
    return re.sub(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', mover, xml)


def con_estados(xml: str, estados: dict[str, bool], interruptores: dict[str, tuple]) -> str:
    """Pone `checked` de cada interruptor (localizado por sus bounds en esta pantalla) según `estados`."""
    import re

    def poner(m):
        etiqueta = m.group(0)
        for clave, b in interruptores.items():
            if f'bounds="[{b[0]},{b[1]}][{b[2]},{b[3]}]"' in etiqueta:
                return re.sub(r'checked="(true|false)"', f'checked="{str(estados[clave]).lower()}"', etiqueta)
        return etiqueta
    return re.sub(r"<node [^>]*>", poner, xml)


def subir_y(b: tuple, dy: int) -> tuple:
    return (b[0], b[1] - dy, b[2], b[3] - dy)


# Los interruptores de cada pantalla del simulador, por bounds (medidos en 05 y 06, no calculados por el código).
INTERRUPTORES_06 = {"ia": (889, 971, 1035, 1106), "essai": (0, 1435, 1080, 1577),
                    "threads": (889, 1705, 1035, 1795), "facebook": (889, 1897, 1035, 1961)}
INTERRUPTORES_FIN = {"ia": subir_y((889, 971, 1035, 1106), DY_FIN), "essai": subir_y((0, 1435, 1080, 1577), DY_FIN),
                     "threads": subir_y((889, 1705, 1035, 1795), DY_FIN),
                     "facebook": subir_y((889, 1897, 1035, 1987), DY_FIN)}
INTERRUPTORES_ARRIBA = {"ia": (889, 2301, 1035, 2316)}


def dentro(punto: tuple, b: tuple) -> bool:
    return b[0] <= punto[0] < b[2] and b[1] <= punto[1] < b[3]


class DetallesSimulado(TelefonoSimulado):
    """La pantalla de detalles del reel con estado: arriba (05, con el pie que se pegue) o abajo (la pantalla «fin»,
    o 06 si `sin_fin`). Deslizar con el dedo hacia arriba baja la lista; hacia abajo la sube. Tocar el centro de un
    interruptor lo cambia salvo que esté en `atascados`; tocar el de `dialogo_tras` abre en su lugar la hoja
    «Enregistrer le brouillon ?» (09) y ya no se sale de ella; `reenciende` = {tocado: otro} vuelve a encender `otro`
    al tocar `tocado`."""

    def __init__(self, *, ia=False, essai=False, threads=True, facebook=True, atascados=(), dialogo_tras=None,
                 sin_fin=False, pie_pegado=None, reenciende=None, **kw):
        super().__init__([""], **kw)
        self.estados = {"ia": ia, "essai": essai, "threads": threads, "facebook": facebook}
        self.atascados, self.dialogo_tras, self.sin_fin = set(atascados), dialogo_tras, sin_fin
        self.posicion, self.dialogo, self.pie = "arriba", False, pie_pegado
        self.reenciende = reenciende or {}

    def interruptores(self) -> dict[str, tuple]:
        if self.posicion == "arriba":
            return INTERRUPTORES_ARRIBA
        return INTERRUPTORES_06 if self.sin_fin else INTERRUPTORES_FIN

    def pantalla(self) -> str:
        if self.dialogo:
            return fixture("09-atras-2.xml")
        if self.posicion == "arriba":
            base = fixture("05-detalles.xml")
            base = con_pie(base, self.pie) if self.pie is not None else base
        else:
            base = fixture("06-detalles-abajo.xml") if self.sin_fin else pantalla_fin()
        return con_estados(base, self.estados, self.interruptores())

    def volcado(self, timeout: int = 30) -> str:
        self.volcados_leidos += 1
        self.ultimo = self.pantalla()
        return self.ultimo

    def tocar(self, x: int, y: int) -> None:
        super().tocar(x, y)
        for clave, b in self.interruptores().items():
            if dentro((x, y), b):
                if clave == self.dialogo_tras:
                    self.dialogo = True
                elif clave not in self.atascados:
                    self.estados[clave] = not self.estados[clave]
                if clave in self.reenciende:
                    self.estados[self.reenciende[clave]] = True

    def deslizar(self, x1: int, y1: int, x2: int, y2: int, ms: int = 400) -> None:
        super().deslizar(x1, y1, x2, y2, ms)
        self.posicion = "abajo" if y2 < y1 else "arriba"

    def pegar(self, texto: str, paste: bool = True) -> None:
        super().pegar(texto, paste)
        self.pie = texto


def seccion_interruptores() -> None:
    print("\n9. interruptor_de_fila y detalles_listos (puras, sobre los volcados de la sonda)")
    from labkit import narrado_movil as nm, pantalla, textos

    pie = pie_de_prueba()
    ia = nm.interruptor_de_fila(fixture("06-detalles-abajo.xml"), "Ajouter une mention IA")
    check(ia["bounds"] == (889, 971, 1035, 1106) and ia["checked"] is False, "interruptor de la mención IA, apagado")
    check(nm.interruptor_de_fila(fixture("07-mencion-ia.xml"), "Ajouter une mention IA")["checked"] is True,
          "encendido tras el toque")
    faltan = nm.detalles_listos(fixture("06-detalles-abajo.xml"), pie)
    check(any("IA" in f for f in faltan) and any("Threads" in f for f in faltan) and any("Facebook" in f for f in faltan),
          f"la sonda: IA apagada y los dos cruces encendidos ({faltan})")
    check(any("IA" in f for f in nm.detalles_listos(fixture("05-detalles.xml"), pie)), "fila fuera de pantalla = no confirmada")

    arriba = nm.detalles_listos(fixture("05-detalles.xml"), pie)
    check(any("IA" in f and "no está en pantalla" in f for f in arriba),
          f"en 05 la fila IA es una franja bajo la barra de abajo: «no está en pantalla», no «apagada» ({arriba})")
    check(nm.interruptor_de_fila(fixture("05-detalles.xml"), "Ajouter une mention IA")["bounds"] == (889, 2301, 1035, 2316),
          "en 05 el interruptor existe en el volcado (y no por eso cuenta)")
    check(" " in textos.texto("instagram", "mencion_ia") and nm.interruptor_de_fila(
        fixture("06-detalles-abajo.xml"), "Ajouter une mention IA") is not None,
        "la constante lleva el espacio duro del volcado y el título con espacio normal también casa")
    essai = nm.interruptor_de_fila(fixture("06-detalles-abajo.xml"), "Essai")
    check(essai is not None and essai["clase"].endswith(".Switch") and essai["bounds"] == (0, 1435, 1080, 1577),
          "«Essai»: el propio Switch de la fila")
    threads = nm.interruptor_de_fila(fixture("06-detalles-abajo.xml"), "Threads · Public")
    facebook = nm.interruptor_de_fila(fixture("06-detalles-abajo.xml"), "Facebook · Public")
    check(threads["bounds"] == (889, 1705, 1035, 1795) and threads["checked"]
          and facebook["bounds"] == (889, 1897, 1035, 1961) and facebook["checked"],
          "cruces: el `toggle` de cada fila, no el ToggleButton de fila entera que empieza en x=0")
    check(nm.interruptor_de_fila(fixture("06-detalles-abajo.xml"), "Instagram · Public") is None, "sin esa fila: None")
    doble = fixture("06-detalles-abajo.xml").replace('text="Facebook · Public"', 'text="Threads · Public"')
    check(nm.interruptor_de_fila(doble, "Threads · Public") is None, "dos filas con el mismo título: None, no la primera")

    check(any("Facebook" in f and "no está en pantalla" in f for f in faltan),
          f"en 06 la fila de Facebook toca la barra de abajo (cortada): no está en pantalla ({faltan})")
    check(not any("Essai" in f for f in faltan) and not any("audio" in f.lower() for f in faltan),
          f"en 06 «Essai» apagado y «Audio d’origine» presente: sin queja ({faltan})")
    check(any("pie" in f for f in faltan), "en 06 no se ve el campo del pie: el pie no está confirmado")

    fin = pantalla_fin()
    bien = con_estados(fin, {"ia": True, "essai": False, "threads": False, "facebook": False}, INTERRUPTORES_FIN)
    arriba_ok = con_pie(fixture("05-detalles.xml"), pie)
    check(nm.detalles_listos_en_dos(arriba_ok, bien, pie) == [], "pie arriba e interruptores abajo, todo bien: []")
    check([f for f in nm.detalles_listos(bien, pie) if "pie" not in f] == [], "abajo solo falta el pie")
    sin_pie = nm.detalles_listos_en_dos(fixture("05-detalles.xml"), bien, pie)
    check(len(sin_pie) == 1 and "pie" in sin_pie[0], f"el campo con el texto de ayuda: falta el pie ({sin_pie})")
    otro_pie = nm.detalles_listos_en_dos(con_pie(fixture("05-detalles.xml"), "Otro texto\n\n#x"), bien, pie)
    check(len(otro_pie) == 1 and "pie" in otro_pie[0], "otro pie en el campo: falta el pie")
    con_essai = con_estados(fin, {"ia": True, "essai": True, "threads": False, "facebook": False}, INTERRUPTORES_FIN)
    check([f for f in nm.detalles_listos_en_dos(arriba_ok, con_essai, pie)] != []
          and all("Essai" in f for f in nm.detalles_listos_en_dos(arriba_ok, con_essai, pie)), "«Essai» encendido: falta")
    sin_audio = bien.replace("Audio d’origine", "Ma chanson")
    check(any("Audio d’origine" in f for f in nm.detalles_listos_en_dos(arriba_ok, sin_audio, pie)),
          "sin «Audio d’origine»: falta el audio original")
    check(any("Facebook" in f for f in nm.detalles_listos_en_dos(
        arriba_ok, con_estados(fixture("06-detalles-abajo.xml"), {"ia": True, "essai": False, "threads": False,
                                                                   "facebook": False}, INTERRUPTORES_06), pie)),
          "con Facebook cortado contra la barra no vale aunque marque apagado")
    tapado = bien.replace("</hierarchy>",
                          '<node index="9" text="" resource-id="" class="android.widget.FrameLayout" '
                          'package="com.instagram.android" content-desc="" clickable="true" enabled="true" '
                          'bounds="[0,1500][1080,1900]" /></hierarchy>')
    check(any("Threads" in f for f in nm.detalles_listos_en_dos(arriba_ok, tapado, pie)),
          "algo dibujado encima del interruptor: no cuenta")
    check(nm.detalles_listos_en_dos(arriba_ok, fixture("09-atras-2.xml"), pie) != [], "otra pantalla abajo: no listo")
    check(nm.detalles_listos_en_dos(fixture("09-atras-2.xml"), bien, pie) != [], "otra pantalla arriba: no listo")

    print("\n10. La guardia de toques en los interruptores de 06")
    xml = fixture("06-detalles-abajo.xml")
    for titulo in ("Ajouter une mention IA", "Essai", "Threads · Public", "Facebook · Public"):
        n = nm.interruptor_de_fila(xml, titulo)
        check(pantalla.es_envio(xml, n), f"sin lista blanca, la guardia rechaza «{titulo}» (por «Partager aussi sur...»)")
        check(not pantalla.es_envio(xml, n, ignorar=nm.PERMITIR_INTERRUPTORES),
              f"con PERMITIR_INTERRUPTORES, «{titulo}» se puede tocar")
    for rid, b in BARRA.items():
        n = next(m for m in telefono.nodos(xml) if m["resource_id"] == f"{IG}:id/{rid}")
        check(n["bounds"] == b and pantalla.es_envio(xml, n, ignorar=nm.PERMITIR_INTERRUPTORES),
              f"con la misma lista blanca, «{rid}» sigue rechazado")
    check(nm.PERMITIR_INTERRUPTORES == (textos.texto("instagram", "partager_aussi"),) == ("Partager aussi sur...",),
          "la lista blanca es solo la cabecera «Partager aussi sur...»")

    print("\n11. El gesto de la lista")
    for nombre in ("05-detalles.xml", "06-detalles-abajo.xml"):
        for sentido in ("bajar", "subir"):
            x1, y1, x2, y2 = nm.gesto_de_lista(fixture(nombre), sentido)
            check(all(FRANJA[0] < y < FRANJA[1] for y in (y1, y2)) and x1 == x2 and 0 <= x1 < 147
                  and not any(dentro(p, b) for p in ((x1, y1), (x2, y2)) for b in BARRA.values())
                  and ((y2 < y1) if sentido == "bajar" else (y2 > y1)),
                  f"{nombre}, {sentido}: vertical, a la izquierda de los títulos y dentro de la lista ({(x1, y1, x2, y2)})")
    from labkit.pantalla import PantallaInesperada
    check(lanza(PantallaInesperada, nm.gesto_de_lista, fixture("09-atras-2.xml"), "bajar"),
          "sin la barra de abajo ni la de acción no se desliza")


def correr_pie(sim: TelefonoSimulado, raiz: pathlib.Path, ev: pathlib.Path):
    from labkit import narrado_movil as nm
    return con_telefono_simulado(sim, lambda: nm.poner_pie(PIEZA, ev, raiz=raiz))


def preparado_abierto(d: str) -> pathlib.Path:
    import shutil
    from labkit import narrado
    raiz = arbol(d)
    narrado.guardar_estado_movil(PIEZA, {"paso": "abierto", "nombre_remoto": f"{PIEZA}-12345678.mp4",
                                         "sha256": "1" * 64, "subido_en": SUBIDO_EN, "duracion_ms": DURACION_MS,
                                         "publicaciones_antes": 4191}, raiz)
    return raiz


def sin_toques_en_la_barra(sim: TelefonoSimulado) -> bool:
    return not any(dentro(t, b) for t in sim.toques for b in BARRA.values())


def seccion_poner_pie() -> None:
    print("\n12. narrado_movil.poner_pie con el teléfono simulado")
    from labkit import narrado, narrado_movil as nm
    from labkit.pantalla import PantallaInesperada
    from labkit.pasos import TelefonoNoListo

    pie = pie_de_prueba()
    campo = centro_de(fixture("05-detalles.xml"), "caption_input_text_view")
    centro = {k: ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2) for k, b in INTERRUPTORES_FIN.items()}

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado()
        res, err = correr_pie(sim, raiz, ev)
        check(err is None, f"camino feliz sin error ({err!r})")
        check(sim.pegados == [pie], "pega el pie de la pieza, entero")
        check(sim.toques == [campo, centro["ia"], centro["threads"], centro["facebook"]],
              f"toca el campo, la mención IA, Threads y Facebook, en ese orden; «Essai» ya estaba apagado ({sim.toques})")
        check(sin_toques_en_la_barra(sim), "ningún toque dentro de «Partager» ni de «Enregistrer le brouillon»")
        check(sim.estados == {"ia": True, "essai": False, "threads": False, "facebook": False},
              f"queda la IA encendida y lo demás apagado ({sim.estados})")
        sim.posicion = "arriba"
        xml_arriba = sim.pantalla()
        sim.posicion = "abajo"
        check(nm.detalles_listos_en_dos(xml_arriba, sim.pantalla(), pie) == [],
              "la pantalla final del simulador da detalles_listos_en_dos == []")
        estado = narrado.estado_movil(PIEZA, raiz)
        check(estado.get("paso") == "listo" and estado.get("pie_sha256") == hashlib.sha256(pie.encode()).hexdigest()
              and estado.get("publicaciones_antes") == 4191 and estado == res,
              f"estado «listo» con pie_sha256 y lo anterior intacto ({estado})")
        check(len(sim.capturas) == 2 and sim.capturas[0] != sim.capturas[1] and not sim.prohibidos,
              f"dos capturas, arriba y abajo, y sin E/S real ({sim.capturas})")
        check(sim.deslizamientos and all(FRANJA[0] < y < FRANJA[1] for g in sim.deslizamientos for y in (g[1], g[3]))
              and not any(dentro(p, b) for g in sim.deslizamientos for p in ((g[0], g[1]), (g[2], g[3]))
                          for b in BARRA.values()),
              f"cada deslizamiento empieza y acaba dentro de la lista, nunca en la barra ({sim.deslizamientos})")
        check(sim.teclas.count(4) == 0, "sin teclado abierto no se pulsa «atrás»")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(atascados={"ia"})
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, PantallaInesperada), f"la mención IA sigue apagada tras el toque: se para ({err!r})")
        check(narrado.estado_movil(PIEZA, raiz)["paso"] == "abierto", "y el estado sigue «abierto»")
        check(sim.toques == [campo, centro["ia"]] and sin_toques_en_la_barra(sim),
              f"un solo toque en la IA y nada más después ({sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(atascados={"facebook"})
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, PantallaInesperada) and narrado.estado_movil(PIEZA, raiz)["paso"] == "abierto",
              f"Facebook no se apaga: se para y sigue «abierto» ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(reenciende={"facebook": "threads"})
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, PantallaInesperada) and "Threads" in str(err)
              and narrado.estado_movil(PIEZA, raiz)["paso"] == "abierto" and len(sim.capturas) == 1,
              f"apagar Facebook vuelve a encender Threads: la segunda lectura lo ve y se para ({err!r})")
        check(sim.toques == [campo, centro["ia"], centro["threads"], centro["facebook"]],
              f"y no vuelve a tocar Threads por su cuenta ({sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(dialogo_tras="threads")
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, PantallaInesperada) and narrado.estado_movil(PIEZA, raiz)["paso"] == "abierto",
              f"tras tocar Threads sale una hoja: se para ({err!r})")
        check(sim.toques == [campo, centro["ia"], centro["threads"]] and sim.teclas == [],
              f"y no toca nada más ni intenta cerrarla con «atrás» ({sim.toques}, {sim.teclas})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(ia=True, essai=True, threads=False, facebook=False)
        res, err = correr_pie(sim, raiz, ev)
        check(err is None and sim.toques == [campo, centro["essai"]],
              f"«Essai» encendido se apaga y lo que ya está bien no se toca ({err!r}, {sim.toques})")
        check(sim.estados == {"ia": True, "essai": False, "threads": False, "facebook": False}, "queda todo bien")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(sin_fin=True)
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, PantallaInesperada) and sim.toques == [campo],
              f"la fila de Facebook nunca sale entera: se para sin tocar ningún interruptor ({err!r}, {sim.toques})")
        check(0 < len(sim.deslizamientos) <= nm.MAX_DESLIZAMIENTOS,
              f"con un tope de deslizamientos ({len(sim.deslizamientos)})")
        check(narrado.estado_movil(PIEZA, raiz)["paso"] == "abierto", "el estado sigue «abierto»")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": "subido"}, raiz)
        sim = DetallesSimulado()
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, ValueError) and sim.volcados_leidos == 0 and sim.toques == [],
              f"sin «abierto»: ValueError sin tocar el teléfono ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(listo=False)
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, TelefonoNoListo) and sim.toques == [] and sim.pegados == [],
              f"teléfono bloqueado: se para antes de nada ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado()
        sim.dialogo = True
        res, err = correr_pie(sim, raiz, ev)
        check(isinstance(err, PantallaInesperada) and sim.toques == [] and sim.pegados == [],
              f"no está en los detalles del reel: no se escribe nada ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_abierto(d), pathlib.Path(d) / "ev"
        sim = DetallesSimulado(teclado=(True, False))
        res, err = correr_pie(sim, raiz, ev)
        check(err is None and sim.teclas == [4], f"con el teclado abierto tras pegar, un «atrás» y sigue ({err!r}, {sim.teclas})")


# ---------------------------------------------------------------- tarea 5: publicar y descartar

# Lo que enseña Instagram tras «Partager» NUNCA se ha volcado en el teléfono real: estas pantallas son una SUPOSICIÓN
# (el texto del aviso de audio sale de `sitio_instagram.publicar` y de la nota del 3 nov; la forma, de la hoja 09, que
# se vuelca sola, sin la pantalla de debajo). La tarea 8 guarda los volcados reales como fixtures.
def _dialogo(bounds: str, *hijos: str) -> str:
    raiz = nodo_xml(bounds, clase="android.widget.FrameLayout", hijos="".join(hijos))
    return f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><hierarchy rotation=\"0\">{raiz}</hierarchy>"


BOTON_DESACTIVAR = (63, 1300, 1017, 1430)
XML_AVISO_AUDIO = _dialogo(
    "[63,780][1017,1600]",
    nodo_xml("[111,830][969,900]", texto="Mise à jour de votre audio d’origine"),
    nodo_xml("[111,920][969,1200]", texto="Votre audio d’origine pourra être réutilisé."),
    nodo_xml("[63,1300][1017,1430]", texto="Désactiver et partager", clase="android.widget.Button",
             extra='clickable="true" enabled="true"'),
    nodo_xml("[63,1450][1017,1580]", texto="Partager", clase="android.widget.Button",
             extra='clickable="true" enabled="true"'))
BOTON_PLUS_TARD = (0, 1730, 1080, 1860)
XML_WHATSAPP = _dialogo(
    "[0,1400][1080,2316]",
    nodo_xml("[45,1450][1035,1520]", texto="Partager dans le statut WhatsApp ?",
             extra=con_id("action_sheet_header_text_view")),
    nodo_xml("[0,1600][1080,1730]", texto="Partager", clase="android.widget.Button",
             extra=con_id("action_sheet_row_text_view", 'clickable="true"')),
    nodo_xml("[0,1730][1080,1860]", texto="Plus tard", clase="android.widget.Button",
             extra=con_id("action_sheet_row_text_view", 'clickable="true"')))
XML_WHATSAPP_SIN_PLUS_TARD = XML_WHATSAPP.replace('text="Plus tard"', 'text="Pas maintenant"')
XML_OTRO_DIALOGO = _dialogo(
    "[0,1400][1080,2316]",
    nodo_xml("[45,1450][1035,1520]", texto="Nouveautés des reels",
             extra=con_id("action_sheet_header_text_view")),
    nodo_xml("[0,1600][1080,1730]", texto="OK", clase="android.widget.Button",
             extra=con_id("action_sheet_row_text_view", 'clickable="true"')))
XML_TRAS_COMPARTIR = jerarquia(
    nodo_xml("[0,94][1080,180]", texto="Partage sur Reels…"),
    nodo_xml("[900,1500][1000,1600]", desc="Partager", clase="android.widget.ImageView", extra='clickable="true"'),
    FEED_TAB, PROFILE_TAB, alto=2316)
CENTRO_COMPARTIR = ((563 + 1035) // 2, (2001 + 2125) // 2)
CENTRO_DESACTIVAR = ((63 + 1017) // 2, (1300 + 1430) // 2)
CENTRO_PLUS_TARD = (540, (1730 + 1860) // 2)


class PublicarSimulado(DetallesSimulado):
    """Los detalles del reel ya listos (pie pegado, IA encendida, cruces y «Essai» apagados), con la lista abajo. Un toque
    en «Partager» llama a `al_compartir` y pasa a `tras_compartir` (el último se repite); uno en «Désactiver et
    partager», con el aviso en pantalla, pasa a `tras_desactivar`. `retoque(xml)` cambia la pantalla de detalles."""

    def __init__(self, *, pie: str, tras_compartir=(XML_TRAS_COMPARTIR,), tras_desactivar=(XML_TRAS_COMPARTIR,),
                 retoque=None, al_compartir=None, **kw):
        kw.setdefault("ia", True)
        kw.setdefault("threads", False)
        kw.setdefault("facebook", False)
        super().__init__(pie_pegado=pie, **kw)
        self.posicion = "abajo"
        self.tras_compartir, self.tras_desactivar = list(tras_compartir), list(tras_desactivar)
        self.retoque, self.al_compartir = retoque, al_compartir
        self.despues: list[str] | None = None
        self.lecturas = []  # posición de cada volcado de detalles: «arriba» / «abajo»

    def volcado(self, timeout: int = 30) -> str:
        self.volcados_leidos += 1
        v = self.pantalla()
        if isinstance(v, BaseException):
            raise v
        self.ultimo = v
        return v

    def pantalla(self) -> str:
        if self.despues is not None:
            return self._siguiente(self.despues)
        xml = super().pantalla()
        if not self.dialogo:
            self.lecturas.append(self.posicion)
        return self.retoque(xml) if self.retoque else xml

    def tocar(self, x: int, y: int) -> None:
        en_pantalla = self.ultimo
        super().tocar(x, y)
        if self.despues is None and dentro((x, y), BARRA["share_button"]):
            if self.al_compartir:
                self.al_compartir()
            self.despues = list(self.tras_compartir)
        elif self.despues is not None and en_pantalla == XML_AVISO_AUDIO and dentro((x, y), BOTON_DESACTIVAR):
            self.despues = list(self.tras_desactivar)
        elif self.despues is not None and en_pantalla == XML_WHATSAPP and dentro((x, y), BOTON_PLUS_TARD):
            self.despues = list(self.tras_desactivar)


def preparado_listo(d: str) -> pathlib.Path:
    from labkit import narrado, narrado_movil as nm
    raiz = preparado_abierto(d)
    sha = narrado.informe_de(PIEZA, raiz)["sha256_mp4"]
    narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": "listo",
                                         "nombre_remoto": nm.nombre_remoto(PIEZA, sha), "sha256": sha,
                                         "pie_sha256": hashlib.sha256(pie_de_prueba().encode()).hexdigest()}, raiz)
    return raiz


def correr_con_video(sim: TelefonoSimulado, accion, *, sha=None, borrar=True):
    """`accion()` con el teléfono simulado y `telefono.sha256_de_video` / `borrar_video` sustituidos: `sha` es lo que
    devuelve el primero (una excepción se lanza) y `borrar` lo del segundo. Devuelve (resultado, error, borrados)."""
    borrados: list[str] = []

    def sha_falso(nombre):
        if isinstance(sha, BaseException):
            raise sha
        return sha

    def borrar_falso(nombre):
        borrados.append(nombre)
        if isinstance(borrar, BaseException):
            raise borrar
        return borrar

    guardado = (telefono.sha256_de_video, telefono.borrar_video)
    telefono.sha256_de_video, telefono.borrar_video = sha_falso, borrar_falso
    try:
        res, err = con_telefono_simulado(sim, accion)
    finally:
        telefono.sha256_de_video, telefono.borrar_video = guardado
    return res, err, borrados


def correr_publicar(sim, raiz, ev, *, sha="informe"):
    from labkit import narrado, narrado_movil as nm
    if sha == "informe":
        sha = narrado.informe_de(PIEZA, raiz)["sha256_mp4"]
    res, err, _ = correr_con_video(sim, lambda: nm.publicar(PIEZA, ev, raiz=raiz), sha=sha)
    return res, err


def leer_registro(raiz: pathlib.Path) -> list[dict]:
    import json
    ruta = raiz / "experiments" / "media-lab" / "narrados" / "registro.jsonl"
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()] if ruta.exists() else []


def seccion_publicar() -> None:
    print("\n13. narrado_movil.publicar con el teléfono simulado")
    from labkit import narrado, narrado_movil as nm

    pie = pie_de_prueba()

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        en_el_toque: list = []
        registro_en_el_toque: list = []

        def al_compartir():
            en_el_toque.append(narrado.estado_movil(PIEZA, raiz))
            registro_en_el_toque.append(leer_registro(raiz))
        sim = PublicarSimulado(pie=pie, al_compartir=al_compartir)
        res, err = correr_publicar(sim, raiz, ev)
        res = res or {}
        check(err is None, f"camino feliz sin error ({err!r})")
        check(sim.toques == [CENTRO_COMPARTIR], f"toca «Partager» exactamente una vez y nada más ({sim.toques})")
        check(len(en_el_toque) == 1 and en_el_toque[0].get("paso") == "compartido"
              and en_el_toque[0].get("compartido_en"),
              f"en el momento del toque el disco ya dice «compartido» con compartido_en ({en_el_toque})")
        informe = narrado.informe_de(PIEZA, raiz)
        check(len(registro_en_el_toque) == 1 and registro_en_el_toque[0] == [{
            "pieza": PIEZA, "cita": narrado.clave_de_pieza(PIEZA, raiz), "estado": "compartido",
            "compartido_en": en_el_toque[0].get("compartido_en"), "sha256_mp4": informe["sha256_mp4"],
            "nombre_remoto": en_el_toque[0].get("nombre_remoto")}],
              f"en el momento del toque registro.jsonl ya tiene la línea «compartido» ({registro_en_el_toque})")
        estado = narrado.estado_movil(PIEZA, raiz)
        check(estado.get("paso") == "compartido" and estado.get("compartido_en") == res.get("compartido_en")
              and estado.get("pie_sha256") and estado.get("publicaciones_antes") == 4191,
              f"queda «compartido», con lo anterior intacto ({estado})")
        check(set(res) == {"compartido_en", "avisos", "captura_antes", "captura"} and isinstance(res["avisos"], list)
              and res["captura_antes"] and res["captura"], f"devuelve lo observado ({res})")
        check("arriba" in sim.lecturas and sim.lecturas.index("arriba") < len(sim.lecturas) - 1
              and sim.lecturas[-1] == "abajo",
              f"relee el pie arriba (deslizando) y luego los interruptores abajo ({sim.lecturas[:3]}…)")
        check(sim.deslizamientos and all(FRANJA[0] < y < FRANJA[1] for g in sim.deslizamientos for y in (g[1], g[3])),
              f"para releer solo desliza, dentro de la lista ({sim.deslizamientos})")

        sim2 = PublicarSimulado(pie=pie)
        res2, err2 = correr_publicar(sim2, raiz, ev)
        check(isinstance(err2, nm.NoPublicar) and err2.motivos == ["ya se compartió"]
              and sim2.toques == [] and sim2.volcados_leidos == 0,
              f"una segunda llamada: NoPublicar([«ya se compartió»]) sin tocar el teléfono ({err2!r})")

    for paso in ("verificado", "incierto"):
        with tempfile.TemporaryDirectory() as d:
            raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
            narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": paso}, raiz)
            sim = PublicarSimulado(pie=pie)
            res, err = correr_publicar(sim, raiz, ev)
            check(isinstance(err, nm.NoPublicar) and err.motivos == ["ya se compartió"] and sim.toques == [],
                  f"en «{paso}»: ya se compartió ({err!r})")

    def negativa(etiqueta: str, *, preparar=None, sha="informe", busca: str = "", **kw):
        with tempfile.TemporaryDirectory() as d:
            raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
            if preparar:
                preparar(raiz)
            kw.setdefault("pie", pie)
            dialogo = kw.pop("dialogo", False)
            sim = PublicarSimulado(**kw)
            sim.dialogo = dialogo
            res, err = correr_publicar(sim, raiz, ev, sha=sha)
            texto = " ".join(err.motivos) if isinstance(err, nm.NoPublicar) else ""
            check(isinstance(err, nm.NoPublicar) and busca.lower() in texto.lower() and sim.toques == []
                  and narrado.estado_movil(PIEZA, raiz).get("paso") != "compartido",
                  f"{etiqueta}: NoPublicar sin ningún toque ({err!r}, {sim.toques})")

    def con_paso(paso):
        return lambda raiz: narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": paso}, raiz)

    def con_informe(**cambios):
        import json
        def hacer(raiz):
            ruta = raiz / "experiments" / "media-lab" / "narrados" / PIEZA / "build" / "informe.json"
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            datos.update(cambios)
            ruta.write_text(json.dumps(datos), encoding="utf-8")
        return hacer

    def mp4_cambiado(raiz):
        mp4 = raiz / "experiments" / "media-lab" / "narrados" / PIEZA / "build" / f"{PIEZA}.mp4"
        mp4.write_bytes(mp4.read_bytes() + b"X")

    def otro_pie_guardado(raiz):
        narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "pie_sha256": "0" * 64}, raiz)

    def con_dos_botones(xml):
        return xml.replace("</hierarchy>", '<node index="9" text="" resource-id="com.instagram.android:id/share_button" '
                           'class="android.widget.Button" package="com.instagram.android" content-desc="Partager" '
                           'clickable="true" enabled="true" bounds="[600,300][700,400]" /></hierarchy>')

    def boton_apagado(xml):
        viejo = 'content-desc="Partager" checkable="false" checked="false" clickable="true" enabled="true"'
        assert viejo in xml
        return xml.replace(viejo, viejo.replace('enabled="true"', 'enabled="false"'))

    def boton_tapado(xml):
        return xml.replace("</hierarchy>", '<node index="9" text="" resource-id="" class="android.widget.FrameLayout" '
                           'package="com.instagram.android" content-desc="" clickable="false" enabled="true" '
                           'bounds="[500,1980][1080,2150]" /></hierarchy>')

    negativa("estado «abierto»", preparar=con_paso("abierto"), busca="pie")
    negativa("estado «subido»", preparar=con_paso("subido"), busca="abrir")
    negativa("sin veredicto", preparar=con_informe(veredicto=None), busca="veredicto")
    negativa("MP4 cambiado en el disco", preparar=mp4_cambiado, busca="sha256")
    negativa("el pie de la pieza ya no es el que se pegó", preparar=otro_pie_guardado, busca="pie")
    negativa("el vídeo del teléfono es otro", sha=OTRO_SHA, busca="teléfono")
    negativa("el vídeo no está en el teléfono", sha=None, busca="teléfono")
    negativa("sha256_de_video lanza", sha=telefono.TelefonoError("adb: sin respuesta"), busca="teléfono")
    negativa("teléfono bloqueado", listo=False, busca="listo")
    negativa("no están los detalles delante", busca="detalles", dialogo=True)
    negativa("el pie en pantalla es otro (misma primera línea)", pie=pie.replace("Voz sintética", "Voz humana"),
             busca="pie")
    negativa("el pie en pantalla es otro (desde el principio)", pie="Otro texto\n\n#x", busca="pie")
    negativa("Threads vuelve a estar encendido", threads=True, busca="Threads")
    negativa("la mención IA está apagada", ia=False, busca="IA")
    negativa("«Essai» encendido", essai=True, busca="Essai")
    # Con dos share_button la pantalla ya no cuenta como los detalles (`_es_detalles_reel` exige uno): se para en e/f.
    negativa("dos share_button", retoque=con_dos_botones)
    fin_ok = con_estados(pantalla_fin(), {"ia": True, "essai": False, "threads": False, "facebook": False},
                         INTERRUPTORES_FIN)
    check(nm._problemas_del_boton(fin_ok) == [] and any("2 share_button" in p for p in nm._problemas_del_boton(
        con_dos_botones(fin_ok))) and nm._problemas_del_boton(boton_apagado(fin_ok)) != []
          and nm._problemas_del_boton(boton_tapado(fin_ok)) != [],
          "el botón: uno, activo y destapado; dos, desactivado o tapado no vale")
    negativa("share_button desactivado", retoque=boton_apagado, busca="share_button")
    negativa("share_button tapado", retoque=boton_tapado, busca="share_button")
    negativa("teclado abierto", teclado=(True,), busca="teclado")
    negativa("no se sabe si el teclado está abierto", teclado=(None,), busca="teclado")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, falla_tocar=telefono.TelefonoError("adb: se cortó"))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR]
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "compartido"
              and any("se cortó" in a for a in (res or {}).get("avisos", [])),
              f"el toque lanza: vuelve normal, un solo intento y el estado sigue «compartido» ({err!r}, {res})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie)
        original = narrado.guardar_estado_movil

        def no_escribe(*a, **k):
            raise OSError("disco lleno")
        narrado.guardar_estado_movil = no_escribe
        try:
            res, err = correr_publicar(sim, raiz, ev)
        finally:
            narrado.guardar_estado_movil = original
        check(isinstance(err, nm.NoPublicar) and "disco lleno" in str(err) and sim.toques == []
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "listo",
              f"no se puede escribir «compartido»: no se toca nada ({err!r}, {sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie)
        original = narrado.registrar

        def no_registra(*a, **k):
            raise OSError("registro de solo lectura")
        narrado.registrar = no_registra
        try:
            res, err = correr_publicar(sim, raiz, ev)
        finally:
            narrado.registrar = original
        check(isinstance(err, nm.NoPublicar) and "solo lectura" in str(err) and sim.toques == []
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "listo" and leer_registro(raiz) == [],
              f"no se puede escribir el registro: ni estado ni toque ({err!r}, {sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie)
        original = narrado.guardar_estado_movil

        def y_se_bloquea(pieza_id, estado, raiz=None):
            original(pieza_id, estado, raiz)
            if estado.get("paso") == "compartido":
                sim.listo = False  # el último `exigir_listo` de `enviar`, tras las escrituras, falla
        narrado.guardar_estado_movil = y_se_bloquea
        try:
            res, err = correr_publicar(sim, raiz, ev)
        finally:
            narrado.guardar_estado_movil = original
        check(isinstance(err, nm.NoPublicar) and "no se tocó nada" in str(err) and sim.toques == []
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "compartido"
              and [e["estado"] for e in leer_registro(raiz)] == ["compartido"],
              f"falla el último control de enviar tras escribir: cero toques, registro y estado «compartido», y lo "
              f"dice ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        detalles = con_estados(pantalla_fin(), {"ia": True, "essai": False, "threads": False, "facebook": False},
                               INTERRUPTORES_FIN)
        sim = PublicarSimulado(pie=pie, tras_compartir=(detalles,))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR]
              and any("sigue delante" in a for a in (res or {}).get("avisos", [])),
              f"los detalles siguen delante tras el toque: un solo toque y queda en los avisos ({res and res['avisos']})")

    print("\n13b. El registro de la cita sobrevive a reconstruir build/")
    import shutil
    from labkit import narrado_movil as nm2
    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        res, err = correr_publicar(PublicarSimulado(pie=pie), raiz, ev)
        check(err is None and len(leer_registro(raiz)) == 1, "una publicación deja una línea en el registro")
        build = raiz / "experiments" / "media-lab" / "narrados" / PIEZA / "build"
        shutil.rmtree(build)
        arbol_de_nuevo = arbol(str(pathlib.Path(d) / "otra"))  # un build nuevo con PASS, copiado sobre el borrado
        shutil.copytree(arbol_de_nuevo / "experiments" / "media-lab" / "narrados" / PIEZA / "build", build)
        import json
        ruta_inf = build / "informe.json"
        datos = json.loads(ruta_inf.read_text(encoding="utf-8"))
        ruta_inf.write_text(json.dumps({**datos, "mp4": str(build / f"{PIEZA}.mp4")}), encoding="utf-8")
        check(narrado.apto_para_publicar(PIEZA, raiz) == [] and narrado.estado_movil(PIEZA, raiz) == {},
              "tras reconstruir: build apto, sin movil.json")
        llamadas: list = []
        guardado = telefono.subir_video
        telefono.subir_video = lambda *a: llamadas.append(a)
        try:
            sim = TelefonoSimulado([jerarquia()])
            _, err = con_telefono_simulado(sim, lambda: nm2.subir(PIEZA, ev, raiz=raiz))
        finally:
            telefono.subir_video = guardado
        check(isinstance(err, ValueError) and "registro" in str(err) and llamadas == [] and sim.toques == [],
              f"con la cita en el registro, subir se niega aunque build/ sea nuevo ({err!r})")
        sha = narrado.informe_de(PIEZA, raiz)["sha256_mp4"]
        narrado.guardar_estado_movil(PIEZA, {"paso": "listo", "nombre_remoto": nm2.nombre_remoto(PIEZA, sha),
                                             "sha256": sha, "pie_sha256": hashlib.sha256(pie.encode()).hexdigest()},
                                     raiz)
        sim = PublicarSimulado(pie=pie)
        res, err = correr_publicar(sim, raiz, ev)
        check(isinstance(err, nm2.NoPublicar) and len(err.motivos) == 1
              and err.motivos[0].startswith("ya hay un registro de esta cita: compartido el ")
              and sim.toques == [] and sim.volcados_leidos == 0,
              f"y publicar, aun con un estado «listo» a mano, también ({err!r})")

    print("\n13c. Las escrituras llegan al disco (fsync del archivo y de la carpeta)")
    import os
    import stat
    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        llamadas_fsync: list[str] = []
        original_fsync = os.fsync

        def fsync_anotado(fd):
            llamadas_fsync.append("carpeta" if stat.S_ISDIR(os.fstat(fd).st_mode) else "archivo")
            return original_fsync(fd)
        os.fsync = fsync_anotado
        try:
            narrado.registrar({"pieza": PIEZA, "cita": "x", "estado": "compartido"}, raiz)
            del_registro = list(llamadas_fsync)
            llamadas_fsync.clear()
            narrado.guardar_estado_movil(PIEZA, {"paso": "subido"}, raiz)
            del_estado = list(llamadas_fsync)
        finally:
            os.fsync = original_fsync
        check(del_registro == ["archivo", "carpeta"], f"registrar: fsync del archivo y luego de la carpeta ({del_registro})")
        check(del_estado == ["archivo", "carpeta"], f"guardar_estado_movil: fsync del temporal y de build/ ({del_estado})")

    print("\n14. Tras «Partager»: el aviso del audio original y nada más")
    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, tras_compartir=(XML_AVISO_AUDIO,))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR, CENTRO_DESACTIVAR],
              f"el aviso de audio sale: «Désactiver et partager» una vez ({err!r}, {sim.toques})")
        estado = narrado.estado_movil(PIEZA, raiz)
        check(estado.get("paso") == "compartido" and estado.get("avisos_respondidos") == ["audio_original"]
              and any("Désactiver et partager" in a for a in (res or {}).get("avisos", [])),
              f"el estado sigue «compartido» y anota el aviso respondido ({estado.get('avisos_respondidos')})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, tras_compartir=(XML_AVISO_AUDIO,), tras_desactivar=(XML_AVISO_AUDIO,))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR, CENTRO_DESACTIVAR],
              f"si el aviso no se va, no se vuelve a tocar ({sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, tras_compartir=(XML_OTRO_DIALOGO, XML_OTRO_DIALOGO, XML_TRAS_COMPARTIR))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR]
              and any("Nouveautés des reels" in a for a in (res or {}).get("avisos", []))
              and narrado.estado_movil(PIEZA, raiz).get("avisos_respondidos") == [],
              f"otro diálogo: no se toca nada y queda en los avisos ({res and res['avisos']})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, tras_compartir=(telefono.TelefonoError("volcado roto"),))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR]
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "compartido",
              f"sin volcados tras compartir: vuelve normal y sigue «compartido» ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, tras_compartir=(XML_WHATSAPP,), tras_desactivar=(XML_TRAS_COMPARTIR,))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR, CENTRO_PLUS_TARD]
              and narrado.estado_movil(PIEZA, raiz).get("avisos_respondidos") == ["whatsapp"],
              f"la hoja del estado de WhatsApp: «Plus tard» una vez y nada más ({err!r}, {sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, tras_compartir=(XML_WHATSAPP,), tras_desactivar=(XML_WHATSAPP,))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR, CENTRO_PLUS_TARD],
              f"si la hoja no se va, «Plus tard» no se repite ({sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = PublicarSimulado(pie=pie, tras_compartir=(XML_WHATSAPP_SIN_PLUS_TARD,))
        res, err = correr_publicar(sim, raiz, ev)
        check(err is None and sim.toques == [CENTRO_COMPARTIR]
              and narrado.estado_movil(PIEZA, raiz).get("avisos_respondidos") == []
              and any("WhatsApp" in a for a in (res or {}).get("avisos", [])),
              f"la hoja sin «Plus tard»: nada se toca y queda en los avisos ({sim.toques})")

    from labkit import pantalla, pasos
    from labkit.pantalla import PantallaInesperada
    partager = next(n for n in telefono.nodos(XML_WHATSAPP) if n["texto"] == "Partager")
    for permitir, nombre in ((), "vacía"), (nm.PERMITIR_AVISO_AUDIO, "PERMITIR_AVISO_AUDIO"):
        sim = TelefonoSimulado([XML_WHATSAPP])
        _, err = con_telefono_simulado(sim, lambda: pasos.tocar(partager, XML_WHATSAPP, permitir=permitir))
        check(isinstance(err, PantallaInesperada) and sim.toques == [],
              f"en la hoja de WhatsApp la guardia sigue rechazando «Partager» (lista blanca {nombre})")
    boton = next(n for n in telefono.nodos(XML_AVISO_AUDIO) if n["texto"] == "Désactiver et partager")
    check(not pantalla.es_envio(XML_AVISO_AUDIO, boton, ignorar=nm.PERMITIR_AVISO_AUDIO),
          "con PERMITIR_AVISO_AUDIO la guardia deja tocar «Désactiver et partager»")
    fin = con_estados(pantalla_fin(), {"ia": True, "essai": False, "threads": False, "facebook": False},
                      INTERRUPTORES_FIN)
    prohibidos = [(fin, next(n for n in telefono.nodos(fin) if n["resource_id"] == f"{IG}:id/share_button")),
                  (fin, next(n for n in telefono.nodos(fin) if n["resource_id"] == f"{IG}:id/save_draft_button")),
                  (XML_AVISO_AUDIO, next(n for n in telefono.nodos(XML_AVISO_AUDIO) if n["texto"] == "Partager")),
                  (XML_TRAS_COMPARTIR, next(n for n in telefono.nodos(XML_TRAS_COMPARTIR) if n["desc"] == "Partager"))]
    for xml, n in prohibidos:
        sim = TelefonoSimulado([xml])
        _, err = con_telefono_simulado(sim, lambda: pasos.tocar(n, xml, permitir=nm.PERMITIR_AVISO_AUDIO))
        check(isinstance(err, PantallaInesperada) and sim.toques == [],
              f"con PERMITIR_AVISO_AUDIO, «{n['texto'] or n['desc']}» ({n['resource_id'] or 'sin id'}) sigue rechazado")


def seccion_descartar() -> None:
    print("\n15. narrado_movil.descartar")
    from labkit import narrado, narrado_movil as nm

    hoja = fixture("09-atras-2.xml")
    filas = {n["texto"]: n for n in telefono.nodos(hoja) if n["resource_id"].endswith("action_sheet_row_text_view")}
    recommencer = filas["Recommencer"]["centro"]
    prohibidas = [filas["Enregistrer le brouillon"]["bounds"], BARRA["save_draft_button"]]

    class SalidaSimulada(MovilSimulado):
        ATRAS = {"detalles": "editor", "editor": "hoja", "galeria": "inicio"}

        def tecla(self, codigo: int) -> None:
            super().tecla(codigo)
            if codigo == 4 and self.recorrido[-1] in self.ATRAS:
                self.ir(self.ATRAS[self.recorrido[-1]])

    def salida(inicial: str, detalles: str | None = None) -> SalidaSimulada:
        pantallas = {"detalles": detalles or fixture("05-detalles.xml"), "editor": fixture("04-editor.xml"),
                     "hoja": hoja, "galeria": fixture("03-crear.xml"), "inicio": XML_INICIO_MOVIL, "reels": XML_REELS}
        return SalidaSimulada(pantallas, inicial, [("hoja", recommencer, "galeria")])

    def correr(sim, raiz, ev, borrar=True):
        return correr_con_video(sim, lambda: nm.descartar(PIEZA, ev, raiz=raiz), borrar=borrar)

    def nunca_borrador(sim) -> bool:
        return not any(dentro(t, b) for t in sim.toques for b in prohibidas)

    detalles_listos_xml = con_estados(pantalla_fin(), {"ia": True, "essai": False, "threads": False,
                                                       "facebook": False}, INTERRUPTORES_FIN)
    for paso, inicial, detalles in (("listo", "detalles", detalles_listos_xml), ("abierto", "detalles", None)):
        with tempfile.TemporaryDirectory() as d:
            raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
            narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": paso}, raiz)
            nombre = narrado.estado_movil(PIEZA, raiz)["nombre_remoto"]
            sim = salida(inicial, detalles)
            res, err, borrados = correr(sim, raiz, ev)
            check(err is None and sim.recorrido == [inicial, "editor", "hoja", "galeria", "inicio"]
                  and sim.teclas == [4, 4, 4] and sim.toques == [recommencer],
                  f"desde «{paso}»: atrás, atrás, «Recommencer», atrás hasta la portada ({err!r}, {sim.recorrido}, {sim.toques})")
            check(nunca_borrador(sim), f"desde «{paso}»: ningún toque en «Enregistrer le brouillon»")
            estado = narrado.estado_movil(PIEZA, raiz)
            check(borrados == [nombre] and estado.get("paso") == "descartado" and (res or {}).get("video_borrado") is True,
                  f"desde «{paso}»: borra el vídeo del teléfono y queda «descartado» ({borrados}, {estado.get('paso')})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": "subido"}, raiz)
        sim = salida("reels")
        res, err, borrados = correr(sim, raiz, ev)
        check(err is None and sim.toques == [] and sim.teclas == [] and len(borrados) == 1
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "descartado",
              f"desde «subido» con Instagram en otra parte: no navega, solo limpia ({err!r}, {sim.teclas})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = salida("editor")
        res, err, borrados = correr(sim, raiz, ev)
        check(err is None and sim.recorrido == ["editor", "hoja", "galeria", "inicio"] and sim.toques == [recommencer],
              f"desde el editor: un «atrás» menos ({sim.recorrido})")

    for paso in ("compartido", "verificado", "incierto"):
        with tempfile.TemporaryDirectory() as d:
            raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
            narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": paso}, raiz)
            sim = salida("detalles", detalles_listos_xml)
            res, err, borrados = correr(sim, raiz, ev)
            check(isinstance(err, ValueError) and sim.volcados_leidos == 0 and sim.toques == [] and sim.teclas == []
                  and borrados == [] and narrado.estado_movil(PIEZA, raiz).get("paso") == paso,
                  f"en «{paso}» se niega sin tocar nada ni borrar el vídeo ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = salida("detalles", detalles_listos_xml)
        res, err, borrados = correr(sim, raiz, ev, borrar=False)
        check(err is None and res.get("video_borrado") is False and any("borr" in p for p in res["problemas"])
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "descartado",
              f"borrar_video da False: se informa, no se lanza ({res})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = salida("detalles", detalles_listos_xml)
        res, err, borrados = correr(sim, raiz, ev, borrar=telefono.TelefonoError("adb: sin respuesta"))
        check(err is None and res.get("video_borrado") is False and any("sin respuesta" in p for p in res["problemas"])
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "descartado",
              f"borrar_video lanza: se informa, no se lanza ({res})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        cambiada = hoja.replace('text="Recommencer"', 'text="Recommencer plus tard"')
        sim = salida("detalles", detalles_listos_xml)
        sim.pantallas["hoja"] = cambiada
        res, err, borrados = correr(sim, raiz, ev)
        check(err is None and sim.toques == [] and nunca_borrador(sim) and res["problemas"]
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "descartado",
              f"la hoja sin «Recommencer»: no se toca ninguna fila, se informa y se limpia ({res and res['problemas']})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_listo(d), pathlib.Path(d) / "ev"
        sim = salida("detalles", detalles_listos_xml)

        def accion():
            # mientras se borra el vídeo, otro proceso (`publicar`) escribe «compartido»
            guardado = telefono.borrar_video

            def borrar_y_compartir(nombre):
                narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": "compartido",
                                                     "compartido_en": "2026-11-22T15:00:00+00:00"}, raiz)
                return guardado(nombre)
            telefono.borrar_video = borrar_y_compartir
            try:
                return nm.descartar(PIEZA, ev, raiz=raiz)
            finally:
                telefono.borrar_video = guardado
        res, err, borrados = correr_con_video(sim, accion)
        check(isinstance(err, ValueError) and narrado.estado_movil(PIEZA, raiz).get("paso") == "compartido",
              f"el estado pasa a «compartido» a media salida: descartar no lo pisa ({err!r})")

    print("\n16. apto_para_publicar endurecido")
    import json
    with tempfile.TemporaryDirectory() as d:
        raiz = arbol(d)
        carpeta = raiz / "experiments" / "media-lab" / "narrados" / PIEZA
        fuera = carpeta / f"{PIEZA}.mp4"
        fuera.write_bytes((carpeta / "build" / f"{PIEZA}.mp4").read_bytes())
        ruta = carpeta / "build" / "informe.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        ruta.write_text(json.dumps({**datos, "mp4": str(fuera)}), encoding="utf-8")
        problemas = narrado.apto_para_publicar(PIEZA, raiz)
        check(any("build" in p for p in problemas), f"un MP4 fuera de build/ (mismo sha): no apto ({problemas})")
        sub = carpeta / "build" / "sub"
        sub.mkdir()
        (sub / f"{PIEZA}.mp4").write_bytes(fuera.read_bytes())
        ruta.write_text(json.dumps({**datos, "mp4": str(sub / f"{PIEZA}.mp4")}), encoding="utf-8")
        check(any("build" in p for p in narrado.apto_para_publicar(PIEZA, raiz)), "en una subcarpeta de build/: no apto")
        ruta.write_text(json.dumps({**datos, "mp4": str(carpeta / "build" / ".." / "build" / f"{PIEZA}.mp4")}),
                        encoding="utf-8")
        check(narrado.apto_para_publicar(PIEZA, raiz) == [], "una ruta con «..» que acaba en build/: apta")
        ruta.write_text(json.dumps({**datos, "pieza": "2026-01-01-otra"}), encoding="utf-8")
        check(any("2026-01-01-otra" in p for p in narrado.apto_para_publicar(PIEZA, raiz)),
              "un informe de otra pieza: no apto")
        for malo, que in (([1, 2], "una lista"), ({**datos, "mp4": 123}, "mp4 numérico"),
                          ({**datos, "mp4": ["a"]}, "mp4 lista"), ("texto", "una cadena")):
            ruta.write_text(json.dumps(malo), encoding="utf-8")
            try:
                problemas = narrado.apto_para_publicar(PIEZA, raiz)
            except Exception as e:  # noqa: BLE001
                problemas = [f"LANZÓ {e!r}"]
            check(problemas and not any("LANZÓ" in p for p in problemas), f"informe malformado ({que}): problema, no excepción ({problemas})")


# ---------------------------------------------------------------- tarea 6: verificar

# 11-perfil.xml es el volcado REAL del perfil de la marca de la sonda del 22 nov («4 191 publications», la cuadrícula con
# una foto en la casilla 1). Todo lo demás de esta sección es SINTÉTICO, sacado de lo que dice `sitio_instagram.verificar`
# (pestaña «Vue Grille», hoja «Les plus récents», baldosas «Reel par…», barra «Partage sur…»): la hoja del orden y, sobre
# todo, la vista del Reel abierto nunca se han volcado en el teléfono. La tarea 8 guarda los volcados reales.
BALDOSA_REAL_1 = "Photo de Sabiduria De Bolsillo à la ligne 1, colonne 1"
REEL_1 = "Reel par Sabiduria De Bolsillo à la ligne 1, colonne 1"
FOTO_1 = BALDOSA_REAL_1
BANNER_SUBIDA = nodo_xml("[0,252][1080,317]", texto="Partage sur Reels…")
HOJA_ORDEN = nodo_xml(  # SINTÉTICA: la hoja que abre la pestaña de la cuadrícula ya elegida
    "[0,1500][1080,2316]", clase="android.widget.FrameLayout", extra=con_id("bottom_sheet_container"),
    hijos=nodo_xml("[45,1550][1035,1620]", texto="Trier par")
    + nodo_xml("[0,1650][1080,1780]", texto="Les plus récents", clase="android.widget.Button", extra='clickable="true"')
    + nodo_xml("[0,1780][1080,1910]", texto="Les plus vus", clase="android.widget.Button", extra='clickable="true"'))


def perfil_con(recuento: int, baldosa: str = REEL_1, *, banner: bool = False, hoja: bool = False) -> str:
    """11-perfil.xml (real) con otro recuento, otra primera baldosa y, si se pide, la barra de subida o la hoja del
    orden encima (las dos sintéticas)."""
    xml = fixture("11-perfil.xml")
    cifra = f"{recuento:,}".replace(",", " ")
    assert "4 191publications" in xml and BALDOSA_REAL_1 in xml
    xml = xml.replace("4 191publications", f"{cifra}publications").replace('text="4 191"', f'text="{cifra}"')
    xml = xml.replace(BALDOSA_REAL_1, baldosa)
    extra = (BANNER_SUBIDA if banner else "") + (HOJA_ORDEN if hoja else "")
    return xml.replace("</node></hierarchy>", extra + "</node></hierarchy>") if extra else xml


def perfil_ajeno() -> str:
    """11-perfil.xml (real) como perfil PROPIO de otra cuenta: el título de la barra y los nombres, a `cuenta_ajena`."""
    xml = fixture("11-perfil.xml")
    titulo = 'text="sabiduriabolsillo" resource-id="com.instagram.android:id/action_bar_title"'
    assert titulo in xml
    return (xml.replace(titulo, titulo.replace("sabiduriabolsillo", "cuenta_ajena"))
            .replace("Sabiduria De Bolsillo", "Cuenta Ajena"))


def xml_reel_abierto(pie: str) -> str:
    """SINTÉTICA: el Reel abierto desde la cuadrícula, pausado y volcable. Los ids son una suposición; el código no los
    mira: lee el pie de cualquier nodo de texto de Instagram. Lleva su propio «Partager» (el avión de papel)."""
    return jerarquia(
        nodo_xml("[0,94][1080,2046]", desc="Vidéo du reel", clase="android.view.View",
                 extra=con_id("clips_video_container")),
        nodo_xml("[960,1300][1060,1400]", desc="J’aime", clase="android.widget.ImageView", extra='clickable="true"'),
        nodo_xml("[960,1600][1060,1700]", desc="Partager", clase="android.widget.ImageView",
                 extra=con_id("direct_share_button", 'clickable="true"')),
        nodo_xml("[45,1700][600,1760]", texto="sabiduriabolsillo", extra=con_id("clips_author_username")),
        nodo_xml("[45,1770][900,1900]", texto=pie, extra=con_id("clips_caption_component")),
        FEED_TAB, PROFILE_TAB, alto=2340)


ESPERA_VERIFICAR = 15
TOQUES_VERIFICAR: list[tuple] = []
TODOS_VERIFICAR: list = []  # cada simulador de verificar, para mirar al final que nada cerró ni lanzó la app  # (x, y, volcado en pantalla) de todas las pruebas de verificar


class VerificarSimulado(TelefonoSimulado):
    """El teléfono tras compartir, empezando en `inicial` («otra»: un Reel ajeno con la barra de abajo; «detalles» y
    «editor»: fixtures 05 y 04, sin barra; «reel»: el visor). La pestaña `profile_tab` lleva al perfil propio (el de la
    marca, o el de `cuenta_ajena` si `ajena`). En el perfil, antes de refrescar se ve `antes` (en caché); cada refresco
    (deslizar hacia abajo) pasa al siguiente de `recuentos` (el último se repite). «Vue Grille» abre la hoja del orden
    (si `orden`), «Les plus récents» la cierra, la primera baldosa (si es un Reel) abre `xml_reel_abierto(pie_reel)`
    (si `reel_volcable` es False, el visor da TelefonoError en cada volcado, como un Reel en marcha) y «atrás» va
    detalles → editor → otra, y del visor o la hoja al perfil. `banner` = volcados del perfil con la barra de subida;
    `fallos` = números de volcado (1, 2, …) que dan TelefonoError. `dormir` adelanta el reloj."""

    ATRAS = {"detalles": "editor", "editor": "otra", "reel": "perfil", "orden": "perfil"}

    def __init__(self, *, antes: int = 4191, recuentos=(4192,), baldosa: str = REEL_1, pie_reel: str | None = None,
                 banner: int = 0, orden: bool = True, ajena: bool = False, fallos=(), inicial: str = "otra",
                 reel_volcable: bool = True, baldosa_cuadricula: str | None = None,
                 banner_desde_refresco: int | None = None, **kw):
        super().__init__([""], **kw)
        self.recuento, self.recuentos = antes, list(recuentos)
        self.baldosa, self.pie_reel = baldosa, pie_reel
        self.banner, self.hoja_orden, self.ajena, self.fallos = banner, orden, ajena, fallos
        self.reel_volcable = reel_volcable
        self.baldosa_cuadricula = baldosa_cuadricula  # la descripción de la baldosa tras «Vue Grille», si cambia
        self.banner_desde_refresco = banner_desde_refresco  # desde ese refresco (1, 2, …), la barra no se va
        self.en_cuadricula = False
        self.donde = inicial
        self.refrescos = 0
        self.dormido = 0.0
        self.aperturas = 0  # toques en la baldosa que abren el visor
        TODOS_VERIFICAR.append(self)

    def pantalla(self) -> str:
        if self.donde in ("perfil", "orden"):
            if self.ajena:
                return perfil_ajeno()
            banner = self.donde == "perfil" and self.banner > 0
            if banner:
                self.banner -= 1
            if self.banner_desde_refresco is not None and self.refrescos >= self.banner_desde_refresco:
                banner = True
            baldosa = self.baldosa_cuadricula if self.en_cuadricula and self.baldosa_cuadricula else self.baldosa
            return perfil_con(self.recuento, baldosa, banner=banner, hoja=self.donde == "orden")
        if self.donde == "reel":
            if not self.reel_volcable:
                raise telefono.TelefonoError("uiautomator: could not get idle state (Reel en marcha, simulado)")
            return xml_reel_abierto(self.pie_reel)
        if self.donde == "detalles":
            return fixture("05-detalles.xml")
        if self.donde == "editor":
            return fixture("04-editor.xml")
        return XML_REELS

    def volcado(self, timeout: int = 30) -> str:
        self.volcados_leidos += 1
        if self.volcados_leidos in self.fallos:
            raise telefono.TelefonoError(f"volcado {self.volcados_leidos} ilegible (simulado)")
        self.ultimo = self.pantalla()
        return self.ultimo

    def deslizar(self, x1: int, y1: int, x2: int, y2: int, ms: int = 400) -> None:
        super().deslizar(x1, y1, x2, y2, ms)
        if self.donde == "perfil" and y2 > y1:
            self.en_cuadricula = False
            self.refrescos += 1
            self.recuento = self._siguiente(self.recuentos)

    def tocar(self, x: int, y: int) -> None:
        super().tocar(x, y)
        TOQUES_VERIFICAR.append((x, y, self.ultimo))
        en = [n for n in telefono.nodos(self.ultimo or jerarquia()) if dentro((x, y), n["bounds"])]
        if any(n["resource_id"] == f"{IG}:id/profile_tab" for n in en):
            self.donde = "perfil"
        elif self.donde == "perfil" and any(n["desc"] == "Vue Grille" for n in en):
            self.donde = "orden" if self.hoja_orden else "perfil"
            self.en_cuadricula = True
        elif self.donde == "orden" and any(n["texto"] == "Les plus récents" for n in en):
            self.donde = "perfil"
        elif self.donde == "perfil" and self.baldosa.startswith("Reel") and any(
                n["desc"] in (self.baldosa, self.baldosa_cuadricula) for n in en):
            self.donde = "reel"
            self.aperturas += 1

    def tecla(self, codigo: int) -> None:
        super().tecla(codigo)
        if codigo == 4 and self.donde in self.ATRAS:
            self.donde = self.ATRAS[self.donde]

    def dormir(self, segundos: float) -> None:
        self.dormido += segundos
        self.reloj += segundos


def preparado_compartido(d: str) -> pathlib.Path:
    """Como lo deja `publicar`: estado «compartido» y la línea «compartido» en el registro."""
    from labkit import narrado
    raiz = preparado_listo(d)
    estado = {**narrado.estado_movil(PIEZA, raiz), "paso": "compartido", "compartido_en": "2026-11-22T15:00:00+00:00",
              "avisos_respondidos": []}
    narrado.guardar_estado_movil(PIEZA, estado, raiz)
    narrado.registrar({"pieza": PIEZA, "cita": narrado.clave_de_pieza(PIEZA, raiz), "estado": "compartido",
                       "compartido_en": estado["compartido_en"], "sha256_mp4": estado["sha256"],
                       "nombre_remoto": estado["nombre_remoto"]}, raiz)
    return raiz


def correr_verificar(sim: VerificarSimulado, raiz: pathlib.Path, ev: pathlib.Path, *, borrar=True):
    """`verificar` con el teléfono simulado, `exigir_cuenta` sustituida por una que lanza AssertionError (verificar
    nunca la llama), el reloj que avanza al dormir y un
    escritor del estado que apunta, en cada escritura, el paso y el registro que había en el disco en ese momento.
    Devuelve (resultado, error, borrados, escrituras)."""
    from labkit import narrado, narrado_movil as nm, reloj
    escrituras: list[tuple] = []
    original_guardar, original_cuenta = narrado.guardar_estado_movil, nm.exigir_cuenta

    def guardar(pieza_id, estado, raiz_=None):
        escrituras.append((estado.get("paso"), leer_registro(raiz)))
        return original_guardar(pieza_id, estado, raiz_)

    def accion():
        reloj.dormir = sim.dormir  # con_telefono_simulado lo restaura al salir
        return nm.verificar(PIEZA, ev, raiz=raiz)

    def exigir_cuenta_prohibida(cuenta):
        raise AssertionError("verificar llamó a exigir_cuenta, que puede cerrar Instagram")
    narrado.guardar_estado_movil, nm.exigir_cuenta = guardar, exigir_cuenta_prohibida
    try:
        res, err, borrados = correr_con_video(sim, accion, borrar=borrar)
    finally:
        narrado.guardar_estado_movil, nm.exigir_cuenta = original_guardar, original_cuenta
    return res, err, borrados, escrituras


def seccion_verificar() -> None:
    print("\n17. narrado_movil.verificar con el teléfono simulado (perfil real, cuadrícula y Reel abierto sintéticos)")
    from labkit import narrado, narrado_movil as nm, sitio_instagram as si
    from labkit import instagram_pantallas as ip

    pie = pie_de_prueba()
    otro_pie = "Otra frase que no es la nuestra.\n\n#otra"
    RECUPERADO_TEXTO = nm.RECUPERADO
    real = fixture("11-perfil.xml")
    check(ip.publicaciones_de_perfil(real) == 4191 and ip.perfil_activo(real) == "sabiduriabolsillo",
          "el perfil real: la marca y 4 191 publicaciones")
    check(nm.baldosa_mas_reciente(real)["desc"] == BALDOSA_REAL_1,
          "en el perfil real la baldosa más reciente es la de la fila 1, columna 1 (una foto)")
    check(nm.baldosa_mas_reciente(perfil_con(4192))["desc"] == REEL_1, "con un Reel en la casilla 1, es esa")
    check(nm.baldosa_mas_reciente(xml_reel_abierto(pie)) is None, "en el Reel abierto no hay baldosas")
    check(nm.pie_en_pantalla(xml_reel_abierto(pie), pie) and not nm.pie_en_pantalla(xml_reel_abierto(otro_pie), pie),
          "el pie del Reel abierto se reconoce por su primera línea, y otro no")
    cortado = pie.splitlines()[0][:30] + "… plus"
    check([nm.leyenda_del_reel(xml_reel_abierto(x), pie) for x in (pie, otro_pie, cortado, "")]
          == ["coincide", "distinta", "cortada", "ausente"],
          "la leyenda del Reel abierto: coincide, distinta, cortada por «… plus», ausente")
    ajeno = perfil_ajeno()
    check(nm.cuenta_activa_en_perfil(real) == "sabiduriabolsillo" and si.perfil_propio(real) is True
          and nm.cuenta_activa_en_perfil(ajeno) == "cuenta_ajena" and si.perfil_propio(ajeno) is None
          and nm.cuenta_activa_en_perfil(XML_REELS) is None and nm.cuenta_activa_en_perfil(xml_reel_abierto(pie)) is None,
          "la cuenta del perfil propio: la marca en el real, cuenta_ajena en el de otra cuenta, ninguna fuera del perfil")
    check(not nm.pie_en_pantalla(real, pie), "en el perfil no hay pie")
    check(nm.subiendo(perfil_con(4191, banner=True)) and not nm.subiendo(real), "la barra «Partage sur…»")
    check(nm.PLAZO_VERIFICAR_S == 180 and nm.ESPERA_ENTRE_LECTURAS_S == 15, "plazos: 180 s en total, 15 s entre lecturas")

    def ultima(raiz):
        return leer_registro(raiz)[-1]

    def bien_registrado(raiz, escrituras, estado_final, etiqueta):
        reg = leer_registro(raiz)
        check(len(reg) == 2 and reg[0]["estado"] == "compartido" and reg[1]["estado"] == estado_final,
              f"{etiqueta}: el registro tiene la línea «compartido» de publicar y la nueva «{estado_final}» ({reg})")
        linea = reg[-1] if reg else {}
        check(set(linea) == {"pieza", "cita", "estado", "verificado_en", "publicaciones_antes", "publicaciones_despues",
                             "problemas", "sha256_mp4", "nombre_remoto", "video_conservado"}
              and linea["cita"] == narrado.clave_de_pieza(PIEZA, raiz) and linea["pieza"] == PIEZA
              and linea["sha256_mp4"] == reg[0]["sha256_mp4"] and linea["nombre_remoto"] == reg[0]["nombre_remoto"]
              and linea["publicaciones_antes"] == 4191 and isinstance(linea["problemas"], list),
              f"{etiqueta}: la línea trae cita, recuentos, problemas, sha y nombre ({linea})")
        finales = [e for e in escrituras if e[0] == estado_final]
        check(len(escrituras) == 1 and len(finales) == 1 and finales[0][1] == reg,
              f"{etiqueta}: el registro ya tenía la línea «{estado_final}» al escribir el estado ({escrituras})")
        estado = narrado.estado_movil(PIEZA, raiz)
        check(estado.get("paso") == estado_final and estado.get("verificado_en") == linea.get("verificado_en"),
              f"{etiqueta}: el estado queda «{estado_final}» ({estado.get('paso')})")

    def correr(d, **kw):
        borrar = kw.pop("borrar", True)
        plazo = kw.pop("plazo", None)
        raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
        sim = VerificarSimulado(**kw)
        if plazo is not None:
            nm.PLAZO_VERIFICAR_S = plazo
        try:
            res, err, borrados, escrituras = correr_verificar(sim, raiz, ev, borrar=borrar)
        finally:
            nm.PLAZO_VERIFICAR_S = 180
        return raiz, sim, res or {}, err, borrados, escrituras

    nombre = None
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie)
        nombre = narrado.estado_movil(PIEZA, raiz).get("nombre_remoto")
        check(err is None and res.get("estado") == "verificado" and res.get("encontrada") is True,
              f"recuento +1 y el pie del Reel nuevo: «verificado» ({err!r}, {res})")
        check(set(res) == {"estado", "publicaciones_antes", "publicaciones_despues", "encontrada", "problemas",
                           "captura", "video_conservado"} and res["video_conservado"] is False and res["publicaciones_antes"] == 4191 and res["publicaciones_despues"] == 4192
              and res["problemas"] == [] and res["captura"], f"devuelve el resultado completo ({res})")
        bien_registrado(raiz, escrituras, "verificado", "verificado")
        check(borrados == [nombre], f"verificado: borra el vídeo del teléfono ({borrados})")
        tab = centro_de(XML_REELS, "profile_tab")
        check(sim.refrescos >= 1 and sim.toques[:1] == [tab], "llega al perfil con la pestaña «Profil» y refresca")
        check(4 in sim.teclas and sim.donde == "perfil", "tras leer el pie vuelve al perfil con «atrás»")
        check(len(sim.toques) == 4 and sim.aperturas == 1,
              f"toca «Profil», «Vue Grille», «Les plus récents» y la baldosa, nada más ({sim.toques})")
        check(not isinstance(err, AssertionError), "nunca llama a exigir_cuenta (la sustituta lanza AssertionError)")
        check(sim.deslizamientos and all(g[3] > g[1] for g in sim.deslizamientos),
              f"solo desliza hacia abajo, para refrescar ({sim.deslizamientos})")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, recuentos=(4191,), pie_reel=pie)
        check(err is None and res.get("estado") == "incierto" and res.get("encontrada") is False
              and res.get("publicaciones_despues") == 4191, f"el recuento no cambia en todo el plazo: «incierto» ({res})")
        check(any("no cambió" in p for p in res.get("problemas", [])), f"y lo dice ({res.get('problemas')})")
        check(sim.reloj - 1000 >= 180 and sim.refrescos >= 3 and sim.dormido >= 3 * 15, f"espera el plazo entero, refrescando ({sim.refrescos})")
        bien_registrado(raiz, escrituras, "incierto", "recuento sin cambiar")
        check(ultima(raiz)["problemas"] == res.get("problemas"), "los problemas van también al registro")
        check(borrados == [] and res.get("video_conservado") is True and ultima(raiz)["video_conservado"] is True
              and narrado.estado_movil(PIEZA, raiz).get("video_conservado") is True
              and any("el resultado es incierto y la subida podría seguir en curso" in p for p in res["problemas"]),
              "recuento sin cambiar («incierto»): el vídeo se conserva, en el resultado, el registro y el estado")
        check(sim.toques == [centro_de(XML_REELS, "profile_tab")] and all(
                  not any(n["resource_id"].endswith("/share_button") for n in telefono.nodos(xml or jerarquia()))
                  for _, _, xml in sim.toques_en),
              f"recuento sin cambiar: ningún toque salvo «Profil» para llegar al perfil, y ninguno con un share_button "
              f"en pantalla ({sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
        sim = VerificarSimulado(recuentos=(4191,), pie_reel=pie)
        nm.PLAZO_VERIFICAR_S = 60
        try:
            res, err, borrados, escrituras = correr_verificar(sim, raiz, ev)
        finally:
            nm.PLAZO_VERIFICAR_S = 180
        check(err is None and res["estado"] == "incierto" and sim.reloj - 1000 < 120,
              f"el plazo se lee al llamar: con 60 s acaba antes ({sim.reloj - 1000:.0f} s)")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, recuentos=(4193,), pie_reel=pie)
        check(err is None and res.get("estado") == "incierto" and res.get("publicaciones_despues") == 4193,
              f"recuento +2: «incierto» ({res})")
        check(any("más de una publicación" in p and "persona" in p for p in res.get("problemas", [])),
              f"y dice que salió más de una publicación y que lo mire una persona ({res.get('problemas')})")
        check(sim.toques == [centro_de(XML_REELS, "profile_tab")], f"recuento +2: no abre nada ({sim.toques})")
        bien_registrado(raiz, escrituras, "incierto", "recuento +2")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=otro_pie, plazo=900)
        check(err is None and res.get("estado") == "incierto" and res.get("publicaciones_despues") == 4192,
              f"recuento +1 y el Reel más reciente con otro pie: «incierto» ({res})")
        check(any("la leyenda del último Reel no coincide (3 veces)" in p for p in res.get("problemas", [])),
              f"y dice que la leyenda no coincide, 3 veces ({res.get('problemas')})")
        check(sim.aperturas == 3 and sim.refrescos > 6,
              f"otro pie: abre la baldosa 3 veces y luego solo sigue leyendo el recuento ({sim.aperturas}, "
              f"{sim.refrescos} refrescos)")
        bien_registrado(raiz, escrituras, "incierto", "otro pie")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=cortado, plazo=900)
        check(err is None and res.get("estado") == "incierto" and sim.aperturas == 3 and sim.refrescos > 6
              and any("no se pudo leer la leyenda del último Reel (3 veces)" in p for p in res.get("problemas", [])),
              f"leyenda cortada por «… plus»: ilegible, 3 aperturas y luego solo el recuento ({sim.aperturas}, "
              f"{res.get('problemas')})")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, reel_volcable=False)
        check(err is None and res.get("estado") == "incierto" and sim.aperturas == 1
              and any("no se pudo leer la leyenda del último Reel (1 vez)" in p for p in res.get("problemas", [])),
              f"el visor no se deja volcar (Reel en marcha): «incierto», ilegible ({sim.aperturas}, "
              f"{res.get('problemas')})")
        bien_registrado(raiz, escrituras, "incierto", "visor sin volcado")

    for inicial, atras in (("detalles", 2), ("editor", 1), ("reel", 0)):
        with tempfile.TemporaryDirectory() as d:
            raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, inicial=inicial)
            tab = centro_de(XML_REELS if inicial != "reel" else xml_reel_abierto(pie), "profile_tab")
            check(err is None and res.get("estado") == "verificado" and sim.teclas[:atras] == [4] * atras
                  and sim.toques[:1] == [tab],
                  f"empezando en «{inicial}»: {atras} «atrás» y la pestaña «Profil» hasta el perfil, «verificado» "
                  f"({err!r}, {sim.teclas}, {sim.toques[:1]})")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, baldosa=FOTO_1, pie_reel=pie)
        check(err is None and res.get("estado") == "incierto", f"la baldosa más reciente es una foto: «incierto» ({res})")
        check(any("no es un Reel" in p for p in res.get("problemas", [])), f"y lo dice ({res.get('problemas')})")
        check(not any(dentro(t[:2], (0, 1709, 356, 2046)) for t in sim.toques), "la foto no se abre")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, banner=4, pie_reel=pie)
        check(err is None and res.get("estado") == "verificado" and sim.banner == 0 and sim.dormido >= 4 * 15,
              f"la barra de subida un rato y luego nada: «verificado» ({res}, {sim.banner})")
        check(res.get("problemas") == [], "la barra no cuenta como problema")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, fallos=range(3, 16))
        check(err is None and res.get("estado") == "verificado" and res.get("problemas") == []
              and sim.dormido >= ESPERA_VERIFICAR,
              f"una lectura que falla entera (SinVolcado) y luego bien: se reintenta, «verificado» ({err!r}, {res})")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, fallos=range(3, 10**6))
        check(err is None and res.get("estado") == "incierto"
              and any("último error" in p and ("TelefonoError" in p or "SinVolcado" in p) for p in res.get("problemas", [])),
              f"falla hasta el plazo: «incierto» con el último error ({res.get('problemas')})")
        bien_registrado(raiz, escrituras, "incierto", "fallo hasta el plazo")
        check(borrados == [] and res.get("video_conservado") is True, "fallo hasta el plazo («incierto»): vídeo conservado")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, ajena=True, pie_reel=pie)
        check(isinstance(err, si.CuentaAjena) and "otra cuenta" in str(err) and "cuenta_ajena" in str(err)
              and "no se ha hecho nada" in str(err), f"otra cuenta en el perfil: error, no «incierto» ({err!r})")
        check(len(leer_registro(raiz)) == 1 and escrituras == [] and borrados == []
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "compartido"
              and sim.toques == [centro_de(XML_REELS, "profile_tab")] and sim.deslizamientos == [],
              f"otra cuenta: ni línea nueva, ni estado, ni borrado; solo el toque de navegación ({sim.toques})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
        sim = VerificarSimulado(pie_reel=pie, listo=False)
        res, err, borrados, escrituras = correr_verificar(sim, raiz, ev)
        check(err is not None and sim.toques == [] and len(leer_registro(raiz)) == 1 and escrituras == []
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "compartido",
              f"teléfono bloqueado al empezar: error, nada escrito ({err!r})")

    for paso in ("listo", "abierto", "verificado", "incierto"):
        with tempfile.TemporaryDirectory() as d:
            raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
            narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": paso}, raiz)
            sim = VerificarSimulado(pie_reel=pie)
            res, err, borrados, escrituras = correr_verificar(sim, raiz, ev)
            ya = paso in ("verificado", "incierto")
            check(isinstance(err, ValueError) and ("ya verificada" in str(err)) == ya and sim.volcados_leidos == 0
                  and sim.toques == [] and borrados == [] and escrituras == [] and len(leer_registro(raiz)) == 1,
                  f"en «{paso}»: ValueError antes de tocar el teléfono ({err!r})")

    for borrar, que in ((False, "False"), (telefono.TelefonoError("adb: sin respuesta"), "lanza")):
        with tempfile.TemporaryDirectory() as d:
            raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, borrar=borrar)
            check(err is None and res.get("estado") == "verificado" and any(nombre in p for p in res.get("problemas", []))
                  and narrado.estado_movil(PIEZA, raiz).get("paso") == "verificado"
                  and ultima(raiz)["estado"] == "verificado",
                  f"borrar_video {que}: el resultado queda registrado y el problema se informa ({res.get('problemas')})")

    print("\n17b. verificar: confirmación, vídeo conservado, recuperación, emergentes, clave de baldosa, limpiar")
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, recuentos=(4192, 4193), pie_reel=pie)
        check(err is None and res.get("estado") == "incierto" and res.get("publicaciones_despues") == 4193
              and any("confirmación" in p and "más de una publicación" in p for p in res.get("problemas", [])),
              f"S1: +1 y el pie casan, pero la confirmación ve +2: «incierto», más de una publicación ({res})")
        bien_registrado(raiz, escrituras, "incierto", "S1")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, recuentos=(4192, 4192), pie_reel=pie)
        check(err is None and res.get("estado") == "verificado" and sim.refrescos == 2 and sim.aperturas == 1,
              f"la confirmación sigue en +1: «verificado», con un segundo refresco y sin reabrir ({res}, "
              f"{sim.refrescos})")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, recuentos=(4192, 4191), pie_reel=pie)
        check(err is None and res.get("estado") == "incierto" and res.get("encontrada") is False
              and any("bajó" in p for p in res.get("problemas", [])),
              f"la confirmación ve el recuento más bajo: «incierto» con el motivo ({res.get('problemas')})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
        sim = VerificarSimulado(pie_reel=pie)
        original_refresco = nm._recuento_refrescado
        llamadas = []

        def refresco_que_falla_la_segunda(xml):
            llamadas.append(1)
            if len(llamadas) >= 2:
                raise telefono.TelefonoError("volcado ilegible en la confirmación (simulado)")
            return original_refresco(xml)
        nm._recuento_refrescado = refresco_que_falla_la_segunda
        try:
            res, err, borrados, escrituras = correr_verificar(sim, raiz, ev)
        finally:
            nm._recuento_refrescado = original_refresco
        check(err is None and res["estado"] == "incierto"
              and any("confirmación" in p and "no se pudo releer" in p for p in res["problemas"]),
              f"la confirmación no puede leer el recuento: «incierto», sin reintento ({res['problemas']})")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, banner=10**6, pie_reel=pie)
        check(err is None and res.get("estado") == "incierto" and borrados == [] and res.get("video_conservado") is True
              and any("vídeo conservado en el móvil" in p for p in res.get("problemas", [])),
              f"S7: la barra de subida hasta el plazo: «incierto» y el vídeo NO se borra ({borrados}, {res.get('problemas')})")
        check(ultima(raiz).get("video_conservado") is True
              and narrado.estado_movil(PIEZA, raiz).get("video_conservado") is True,
              "S7: video_conservado en el registro y en el estado")
        r2, e2, b2 = correr_con_video(TelefonoSimulado([jerarquia()]), lambda: nm.limpiar(PIEZA, raiz=raiz))
        check(e2 is None and r2 == {"borrado": True, "problemas": []} and b2 == [nombre],
              f"limpiar tras «incierto» borra el vídeo conservado ({r2}, {b2})")
        check(len(leer_registro(raiz)) == 2, "limpiar no escribe en el registro")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, banner=4, pie_reel=pie)
        check(res.get("video_conservado") is False and borrados == [nombre] and ultima(raiz)["video_conservado"] is False,
              "la barra se va antes de acabar: el vídeo se borra como siempre")

    for paso, bien in (("verificado", True), ("incierto", True), ("compartido", False), ("listo", False)):
        with tempfile.TemporaryDirectory() as d:
            raiz = preparado_compartido(d)
            narrado.guardar_estado_movil(PIEZA, {**narrado.estado_movil(PIEZA, raiz), "paso": paso}, raiz)
            for borrar in ((True, False, telefono.TelefonoError("adb: sin respuesta")) if bien else (True,)):
                sim = TelefonoSimulado([jerarquia()])
                r, e, b = correr_con_video(sim, lambda: nm.limpiar(PIEZA, raiz=raiz), borrar=borrar)
                if bien:
                    ok = e is None and r["borrado"] is (borrar is True) and bool(r["problemas"]) is (borrar is not True)
                else:
                    ok = isinstance(e, ValueError) and b == []
                check(ok and sim.toques == [] and sim.volcados_leidos == 0,
                      f"limpiar en «{paso}» (borrar_video → {borrar!r}): {r or e!r}")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
        original = narrado.guardar_estado_movil
        fallos = []

        def guardar_que_falla_una_vez(pieza_id, estado, raiz_=None):
            if not fallos:
                fallos.append(estado.get("paso"))
                raise OSError("sin espacio (simulado)")
            return original(pieza_id, estado, raiz_)
        narrado.guardar_estado_movil = guardar_que_falla_una_vez
        try:
            res, err, borrados, escrituras = correr_verificar(VerificarSimulado(pie_reel=pie), raiz, ev)
        finally:
            narrado.guardar_estado_movil = original
        check(err is not None and "el resultado ya está en el registro: verificado" in str(err) and borrados == []
              and [r["estado"] for r in leer_registro(raiz)] == ["compartido", "verificado"]
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "compartido",
              f"S3: el estado no se escribe tras el registro: el error lo dice y el registro ya lo tiene ({err})")
        sim = VerificarSimulado(antes=4192, recuentos=(4193,), pie_reel=pie)
        res, err, borrados, escrituras = correr_verificar(sim, raiz, ev)
        check(err is None and res.get("estado") == "verificado" and "estado recuperado del registro" in res["problemas"]
              and sim.volcados_leidos == 0 and sim.toques == [] and borrados == []
              and [r["estado"] for r in leer_registro(raiz)] == ["compartido", "verificado"]
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "verificado",
              f"S3: al volver a correr se recupera del registro, sin teléfono y sin otra línea ({res}, {err!r})")

    with tempfile.TemporaryDirectory() as d:
        raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
        narrado.registrar({**leer_registro(raiz)[0], "estado": "incierto", "nombre_remoto": "otro-video.mp4"}, raiz)
        sim = VerificarSimulado(pie_reel=pie)
        res, err, borrados, escrituras = correr_verificar(sim, raiz, ev)
        check(err is None and res.get("estado") == "verificado" and RECUPERADO_TEXTO not in res.get("problemas", [])
              and sim.volcados_leidos > 0 and len(leer_registro(raiz)) == 3,
              f"una línea «incierto» de otro nombre_remoto no se recupera: se verifica con el teléfono ({res})")

    emergente = {"nombre": "PopupWindow:simulada", "frame": (0, 1850, 1080, 1950)}  # sobre la baldosa, solo
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, emergentes=([emergente],))
        check(err is None and res.get("estado") == "incierto" and sim.aperturas == 0
              and not any(dentro(t, (0, 1709, 356, 2046)) for t in sim.toques)
              and any("no se toca la baldosa" in p and "PopupWindow" in p for p in res.get("problemas", [])),
              f"una ventana emergente sobre la baldosa todo el plazo: no se toca, «incierto» ({res.get('problemas')})")
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, emergentes=([emergente],) * 6 + ((),))
        check(err is None and res.get("estado") == "verificado" and sim.aperturas == 1 and sim.dormido >= ESPERA_VERIFICAR,
              f"la ventana emergente se va: la ronda siguiente abre la baldosa, «verificado» ({res}, {sim.aperturas})")

    check(nm.clave_baldosa("Reel par  X à la ligne 1, colonne 1, 3 vues") == nm.clave_baldosa(
          "Reel par X à la ligne 1, colonne 1") and nm.clave_baldosa("Reel par X à la ligne 2, colonne 1")
          != nm.clave_baldosa("Reel par X à la ligne 1, colonne 1"), "clave de baldosa: sin espacios de más ni vistas")
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(
            d, pie_reel=otro_pie, plazo=900, baldosa_cuadricula=REEL_1.replace(" par ", " par  ") + ", 3 vues")
        check(err is None and sim.aperturas == 3 and any("(3 veces)" in p for p in res.get("problemas", [])),
              f"el tope de 3 aperturas salta aunque el perfil y la cuadrícula den la descripción algo distinta "
              f"({sim.aperturas}, {res.get('problemas')})")

    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, falla_captura=RuntimeError("disco lleno"))
        check(err is None and res.get("estado") == "verificado" and ultima(raiz)["estado"] == "verificado"
              and narrado.estado_movil(PIEZA, raiz).get("paso") == "verificado",
              f"una captura que lanza (no TelefonoError) no impide registrar «verificado» ({err!r}, {res})")

    print("\n17c. verificar: el vídeo solo se borra con «verificado» y sin la barra de subida")
    nm._BANNER_EN_RONDA[0] = False
    nm._vistazo(real)
    sin = nm._BANNER_EN_RONDA[0]
    nm._vistazo(perfil_con(4192, banner=True))
    check(sin is False and nm._BANNER_EN_RONDA[0] is True, "_vistazo enciende la marca de la ronda con un volcado con la barra")
    nm._BANNER_EN_RONDA[0] = False
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, banner_desde_refresco=2)
        check(err is None and res.get("estado") == "incierto" and borrados == [] and res.get("video_conservado") is True
              and any("no se pudo releer" in p for p in res["problemas"])
              and ultima(raiz)["video_conservado"] is True
              and narrado.estado_movil(PIEZA, raiz).get("video_conservado") is True,
              f"A1: la barra sale desde el refresco de la confirmación: «incierto» y vídeo conservado ({borrados}, "
              f"{res.get('problemas')})")
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie, recuentos=(4191,), banner_desde_refresco=3)
        check(err is None and res.get("estado") == "incierto" and borrados == [] and res.get("video_conservado") is True,
              f"la barra sale tras un refresco de las últimas rondas: vídeo conservado ({borrados})")
    with tempfile.TemporaryDirectory() as d:
        raiz, sim, res, err, borrados, escrituras = correr(d, pie_reel=pie)
        check(res.get("estado") == "verificado" and borrados == [nombre] and res.get("video_conservado") is False
              and ultima(raiz)["video_conservado"] is False
              and narrado.estado_movil(PIEZA, raiz).get("video_conservado") is False,
              "«verificado» sin barra en ningún volcado: el vídeo se borra y video_conservado es false en todas partes")
    for etiqueta, kw in (("+2", {"recuentos": (4193,)}), ("otro pie", {"pie_reel": otro_pie}),
                         ("popup todo el plazo (A5)", {"emergentes": ([emergente],)})):
        with tempfile.TemporaryDirectory() as d:
            kw.setdefault("pie_reel", pie)
            raiz, sim, res, err, borrados, escrituras = correr(d, **kw)
            check(err is None and res.get("estado") == "incierto" and borrados == [] and res.get("video_conservado")
                  is True and ultima(raiz)["video_conservado"] is True
                  and narrado.estado_movil(PIEZA, raiz).get("video_conservado") is True,
                  f"«incierto» por {etiqueta}: vídeo conservado en el resultado, el registro y el estado ({borrados})")
    for conservado in (True, False):
        with tempfile.TemporaryDirectory() as d:
            raiz, ev = preparado_compartido(d), pathlib.Path(d) / "ev"
            estado_linea = "incierto" if conservado else "verificado"
            narrado.registrar({**leer_registro(raiz)[0], "estado": estado_linea, "verificado_en": "2026-11-22T15:05:00+00:00",
                               "publicaciones_antes": 4191, "publicaciones_despues": 4191, "problemas": [],
                               "video_conservado": conservado}, raiz)
            sim = VerificarSimulado(pie_reel=pie)
            res, err, borrados, escrituras = correr_verificar(sim, raiz, ev)
            estado = narrado.estado_movil(PIEZA, raiz)
            check(err is None and res.get("estado") == estado_linea and estado.get("paso") == estado_linea
                  and estado.get("video_conservado") is conservado and res.get("video_conservado") is conservado
                  and sim.volcados_leidos == 0 and borrados == [] and len(leer_registro(raiz)) == 2,
                  f"recuperación de una línea «{estado_linea}»: video_conservado={conservado} sale de la línea ({estado})")

    check(TODOS_VERIFICAR and all(sim.orden == [] and sim.prohibidos == [] for sim in TODOS_VERIFICAR),
          f"en ninguna prueba de verificar se cierra ni se lanza Instagram ni hay shell/adb "
          f"({[(sim.orden, sim.prohibidos) for sim in TODOS_VERIFICAR if sim.orden or sim.prohibidos]})")
    malos = []
    for x, y, xml in TOQUES_VERIFICAR:
        for n in telefono.nodos(xml or jerarquia()):
            rid = n["resource_id"].rsplit("/", 1)[-1]
            if dentro((x, y), n["bounds"]) and (rid in ("share_button", "save_draft_button")
                                                or "Partager" in (n["texto"], n["desc"])):
                malos.append((x, y, rid or n["texto"] or n["desc"]))
    check(TOQUES_VERIFICAR and not malos,
          f"ningún toque de verificar cae en share_button, save_draft_button ni «Partager» ({len(TOQUES_VERIFICAR)} "
          f"toques, {malos})")


SECCIONES = [seccion_puras, seccion_subir, seccion_borrar, seccion_pie, seccion_apto_y_estado, seccion_miniatura,
             seccion_subir_paso, seccion_abrir, seccion_interruptores, seccion_poner_pie, seccion_publicar,
             seccion_descartar, seccion_verificar]


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
