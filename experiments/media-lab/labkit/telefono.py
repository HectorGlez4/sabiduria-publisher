"""
Primitivas adb para el Samsung del laboratorio (serie R5CXB1AWYNF).

El volcado de uiautomator sirve para ENCONTRAR controles, pero puede ir con
retraso respecto a la pantalla: la evidencia de un estado final es siempre una
captura (screencap), nunca un volcado.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

SERIAL = "R5CXB1AWYNF"
REMOTO_UI = "/sdcard/lab-ui.xml"
_BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


class TelefonoError(RuntimeError):
    pass


def adb(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    r = subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise TelefonoError(f"adb {' '.join(args)}: {r.stderr.decode(errors='replace').strip()[:300]}")
    return r


def shell(cmd: str, timeout: int = 60) -> str:
    return adb("shell", cmd, timeout=timeout).stdout.decode(errors="replace")


def nodos(xml: str) -> list[dict]:
    fuera = []
    for el in ET.fromstring(xml.encode("utf-8")).iter("node"):
        m = _BOUNDS.fullmatch(el.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        if x2 <= x1 or y2 <= y1:
            continue
        fuera.append({"texto": el.get("text", ""), "desc": el.get("content-desc", ""),
                      "clase": el.get("class", ""), "bounds": (x1, y1, x2, y2),
                      "centro": ((x1 + x2) // 2, (y1 + y2) // 2)})
    return fuera


def buscar(xml: str, *, texto: str | None = None, contiene: str | None = None,
           empieza: str | None = None) -> dict | None:
    for n in nodos(xml):
        for valor in (n["texto"], n["desc"]):
            if not valor:
                continue
            if texto is not None and valor == texto:
                return n
            if contiene is not None and contiene in valor:
                return n
            if empieza is not None and valor.startswith(empieza):
                return n
    return None


def textos(xml: str) -> list[str]:
    return [n["texto"] for n in nodos(xml) if n["texto"]]


def volcado() -> str:
    shell(f"uiautomator dump --compressed {REMOTO_UI}", timeout=30)
    return adb("exec-out", "cat", REMOTO_UI).stdout.decode("utf-8", errors="replace")


def captura(destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(adb("exec-out", "screencap", "-p").stdout)
    return destino


def tocar(x: int, y: int) -> None:
    shell(f"input tap {x} {y}")


def tecla(codigo: int) -> None:
    shell(f"input keyevent {codigo}")


def combinacion(*codigos: int) -> None:
    shell("input keycombination " + " ".join(map(str, codigos)))


def lanzar(paquete: str) -> None:
    shell(f"monkey -p {paquete} -c android.intent.category.LAUNCHER 1")


def estado() -> dict:
    listo_adb = adb("get-state").stdout.decode().strip() == "device"
    despierto = "mWakefulness=Awake" in shell("dumpsys power")
    bloqueado = "isKeyguardShowing=true" in shell("dumpsys window")
    return {"adb": listo_adb, "despierto": despierto, "bloqueado": bloqueado,
            "listo": listo_adb and despierto and not bloqueado}


def subir(local: Path, remoto: str) -> str:
    adb("push", str(local), remoto, timeout=120)
    shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remoto}")
    remoto_sha = shell(f"sha256sum {remoto}").split()[0]
    local_sha = hashlib.sha256(local.read_bytes()).hexdigest()
    if remoto_sha != local_sha:
        raise TelefonoError(f"hash distinto en el teléfono: {remoto_sha} != {local_sha}")
    return local_sha
