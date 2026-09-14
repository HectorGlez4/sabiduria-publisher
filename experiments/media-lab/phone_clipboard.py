#!/usr/bin/env python3
"""
Pega texto Unicode en el campo enfocado del Samsung del laboratorio.

    python3 experiments/media-lab/phone_clipboard.py --file caption.txt [--no-paste]

Por qué existe
──────────────
`adb shell input text` solo inyecta ASCII: una leyenda en español pierde tildes,
eñes y «¿». El teléfono no tiene teclado ADB ni `cmd clipboard`, y MaaS360 no
deja al shell tocar el usuario 10. scrcpy sí puede: su servidor corre como shell
y acepta un mensaje de control SET_CLIPBOARD con la orden de pegar.

Se habla con el servidor directamente, sin ventana, para no depender de pulsar
atajos en el escritorio del Mac. El protocolo es interno de scrcpy y cambia entre
versiones: el cliente tiene que coincidir con el servidor instalado (4.1).
"""
from __future__ import annotations

import argparse
import pathlib
import random
import socket
import struct
import subprocess
import time

SERIAL = "R5CXB1AWYNF"
SCRCPY_VERSION = "4.1"
SERVER_LOCAL = "/opt/homebrew/share/scrcpy/scrcpy-server"
SERVER_REMOTE = "/data/local/tmp/scrcpy-server-lab.jar"
TYPE_SET_CLIPBOARD = 9  # ControlMessage.TYPE_SET_CLIPBOARD en scrcpy 4.1


def adb(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, text=True, **kw)


def set_clipboard_message(text: str, paste: bool) -> bytes:
    data = text.encode("utf-8")
    return struct.pack(">BQBI", TYPE_SET_CLIPBOARD, 0, 1 if paste else 0, len(data)) + data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=pathlib.Path)
    ap.add_argument("--no-paste", action="store_true", help="solo copiar, sin pegar")
    a = ap.parse_args()
    text = a.file.read_text(encoding="utf-8").rstrip("\n")

    push = adb("push", SERVER_LOCAL, SERVER_REMOTE)
    if push.returncode != 0:
        raise SystemExit(f"push del servidor falló: {push.stderr.strip()}")

    scid = random.randrange(1, 0x7FFFFFFF)
    port = 27200 + scid % 500
    fwd = adb("forward", f"tcp:{port}", f"localabstract:scrcpy_{scid:08x}")
    if fwd.returncode != 0:
        raise SystemExit(f"adb forward falló: {fwd.stderr.strip()}")

    server = subprocess.Popen(
        ["adb", "-s", SERIAL, "shell",
         f"CLASSPATH={SERVER_REMOTE}", "app_process", "/", "com.genymobile.scrcpy.Server",
         SCRCPY_VERSION, f"scid={scid:08x}", "log_level=info", "tunnel_forward=true",
         "video=false", "audio=false", "control=true", "send_dummy_byte=false",
         "send_device_meta=false", "clipboard_autosync=false", "cleanup=false"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        # Con túnel forward, connect() funciona aunque nadie escuche todavía: el
        # socket se cierra al primer uso. Se reintenta hasta que el envío aguanta.
        deadline = time.time() + 15
        while True:
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=3)
                s.sendall(set_clipboard_message(text, paste=not a.no_paste))
                time.sleep(1.5)
                s.settimeout(0.2)
                try:
                    if s.recv(1) == b"":
                        raise ConnectionResetError("servidor aún no escuchaba")
                except socket.timeout:
                    pass  # conexión viva: el mensaje llegó
                s.close()
                break
            except OSError:
                if time.time() > deadline or server.poll() is not None:
                    out = server.stdout.read() if server.poll() is not None else ""
                    raise SystemExit(f"no se pudo hablar con scrcpy-server:\n{out}")
                time.sleep(0.5)
        print(f"✓ {len(text)} caracteres enviados al portapapeles"
              f"{'' if a.no_paste else ' y pegados'}")
        return 0
    finally:
        server.terminate()
        adb("forward", "--remove", f"tcp:{port}")


if __name__ == "__main__":
    raise SystemExit(main())
