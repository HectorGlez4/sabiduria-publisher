"""
Pruebas del laboratorio de medios (experiments/media-lab/).

    .venv/bin/python tests/test_media_lab.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments" / "media-lab"))

FALLOS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def seccion_portapapeles() -> None:
    print("\n1. SET_CLIPBOARD con los mismos bytes que el test de scrcpy 4.1")
    import phone_clipboard

    esperado = bytes([9, 1, 2, 3, 4, 5, 6, 7, 8, 1, 0, 0, 0, 13]) + b"hello, world!"
    obtenido = phone_clipboard.set_clipboard_message(
        "hello, world!", paste=True, sequence=0x0102030405060708)
    check(obtenido == esperado, "mensaje idéntico al de test_control_msg_serialize.c")
    msg = phone_clipboard.set_clipboard_message("¿Qué?", paste=False)
    check(msg[9] == 0, "paste=False va como 0")
    check(int.from_bytes(msg[10:14], "big") == 7,
          "la longitud cuenta bytes UTF-8 (7), no caracteres (5)")

    import shutil
    import subprocess
    if shutil.which("scrcpy"):
        partes = subprocess.run(["scrcpy", "--version"], capture_output=True, text=True,
                                timeout=30).stdout.split()
        instalada = partes[1] if len(partes) > 1 else "?"
        check(instalada == phone_clipboard.SCRCPY_VERSION,
              f"scrcpy instalado ({instalada}) coincide con el protocolo fijado "
              f"({phone_clipboard.SCRCPY_VERSION})")
        check(pathlib.Path(phone_clipboard.SERVER_LOCAL).is_file(),
              "existe el scrcpy-server que se sube al teléfono")
    else:
        print("  · scrcpy no está instalado: se omite la comprobación de versión")


SECCIONES = [
    seccion_portapapeles,
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
    print("El laboratorio cumple sus contratos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
