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
                 archivo: bool = False, fila: bool = False):
        self.llamadas: list[str] = []
        self.consultas = 0
        self.fila_tras = fila_tras      # consultas que dicen «No result found.» antes de la fila
        self.sha, self.ancho, self.alto = sha, ancho, alto
        self.archivo, self.fila = archivo, fila

    def adb(self, *args, timeout=60):
        self.llamadas.append("adb " + " ".join(args))
        if args[0] == "push":
            self.archivo = True
        return subprocess.CompletedProcess(args, 0, b"", b"")

    def shell(self, cmd, timeout=60):
        self.llamadas.append("shell " + cmd)
        if cmd.startswith("rm "):
            self.archivo = False
        elif cmd.startswith("content delete"):
            self.fila = False
        elif cmd.startswith("content query"):
            self.consultas += 1
            if self.fila or (self.archivo and self.consultas > self.fila_tras):
                self.fila = True
                return (f"Row: 0 _id=7, _display_name=a-1b2c3d4e.mp4, duration=27533, "
                        f"width={self.ancho}, height={self.alto}\n")
            return "No result found.\n"
        elif cmd.startswith("sha256sum"):
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


def seccion_borrar() -> None:
    print("\n3. borrar_video y sha256_de_video")
    nombre = "a-1b2c3d4e.mp4"
    f = Telefono(archivo=True, fila=True)
    check(con_telefono(f, lambda: telefono.borrar_video(nombre)) is True, "borra el archivo y la fila")
    check(not f.archivo and not f.fila, "no quedan ni archivo ni fila")
    f = Telefono()
    check(con_telefono(f, lambda: telefono.borrar_video(nombre)) is True, "ya borrado: True, sin error")
    check(falla(lambda: con_telefono(Telefono(), lambda: telefono.borrar_video("x';rm.mp4"))), "nombre no seguro: error")
    check(con_telefono(Telefono(archivo=True), lambda: telefono.sha256_de_video(nombre)) == SHA, "sha del archivo presente")
    check(con_telefono(Telefono(), lambda: telefono.sha256_de_video(nombre)) is None, "sha de un archivo ausente: None")


SECCIONES = [seccion_puras, seccion_subir, seccion_borrar]


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
