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
ADB_TIMEOUT_PUSH = 60
ADB_TIMEOUT_CORTO = 15


def adb(*args: str, timeout: int = ADB_TIMEOUT_CORTO) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"adb {' '.join(args)} no respondió en {timeout} s") from e


def set_clipboard_message(text: str, paste: bool, sequence: int = 0) -> bytes:
    data = text.encode("utf-8")
    return struct.pack(">BQBI", TYPE_SET_CLIPBOARD, sequence, 1 if paste else 0, len(data)) + data


def argumentos_servidor(scid: int) -> list[str]:
    """Orden que arranca scrcpy-server solo con control (sin vídeo ni audio).

    power_on=false es obligatorio: scrcpy 4.1 tiene powerOn activado por defecto y, con
    control y la pantalla apagada, inyecta KEYCODE_POWER al arrancar. El teléfono lo
    gestiona MaaS360 y aquí nunca se despierta."""
    return ["adb", "-s", SERIAL, "shell",
            f"CLASSPATH={SERVER_REMOTE}", "app_process", "/", "com.genymobile.scrcpy.Server",
            SCRCPY_VERSION, f"scid={scid:08x}", "log_level=info", "tunnel_forward=true",
            "video=false", "audio=false", "control=true", "power_on=false", "send_dummy_byte=false",
            "send_device_meta=false", "clipboard_autosync=false", "cleanup=false"]


def _parar(server: subprocess.Popen) -> str:
    """Termina el servidor, espera a que salga y devuelve lo que escribió.

    Tras `kill()` también se espera como mucho 5 s: si ni así sale (adb colgado), se deja
    de leer su salida, se cierra la tubería y se devuelve lo que haya (nada)."""
    if server.poll() is None:
        server.terminate()
    try:
        out, _ = server.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        try:
            out, _ = server.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out = ""
            if server.stdout is not None:
                try:
                    server.stdout.close()
                except OSError:
                    pass
    return out or ""


def pegar(text: str, paste: bool = True) -> None:
    """Pone `text` en el portapapeles del teléfono y, si `paste`, lo pega en el campo enfocado."""
    push = adb("push", SERVER_LOCAL, SERVER_REMOTE, timeout=ADB_TIMEOUT_PUSH)
    if push.returncode != 0:
        raise RuntimeError(f"push del servidor falló: {push.stderr.strip()}")

    scid = random.randrange(1, 0x7FFFFFFF)
    port = 27200 + scid % 500
    fwd = adb("forward", f"tcp:{port}", f"localabstract:scrcpy_{scid:08x}")
    if fwd.returncode != 0:
        raise RuntimeError(f"adb forward falló: {fwd.stderr.strip()}")

    server: subprocess.Popen | None = None
    try:
        server = subprocess.Popen(argumentos_servidor(scid),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # Con túnel forward, connect() funciona aunque nadie escuche todavía: el
        # socket se cierra al primer uso. Se reintenta hasta que el envío aguanta.
        deadline = time.time() + 15
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=3) as s:
                    s.sendall(set_clipboard_message(text, paste=paste))
                    time.sleep(1.5)
                    s.settimeout(0.2)
                    try:
                        if s.recv(1) == b"":
                            raise ConnectionResetError("servidor aún no escuchaba")
                    except socket.timeout:
                        pass  # conexión viva: el mensaje llegó
                return
            except OSError:
                if time.time() > deadline or server.poll() is not None:
                    salida = _parar(server)
                    server = None
                    raise RuntimeError(f"no se pudo hablar con scrcpy-server:\n{salida}")
                time.sleep(0.5)
    finally:
        if server is not None:
            _parar(server)
        try:
            adb("forward", "--remove", f"tcp:{port}")
        except RuntimeError:
            pass  # un forward colgado no debe tapar el error original


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=pathlib.Path)
    ap.add_argument("--no-paste", action="store_true", help="solo copiar, sin pegar")
    a = ap.parse_args()
    text = a.file.read_text(encoding="utf-8").rstrip("\n")
    pegar(text, paste=not a.no_paste)
    print(f"✓ {len(text)} caracteres enviados al portapapeles"
          f"{'' if a.no_paste else ' y pegados'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
