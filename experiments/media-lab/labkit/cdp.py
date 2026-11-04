"""
Chrome del teléfono por DevTools (CDP), sin dependencias.

    adb forward tcp:9222 localabstract:chrome_devtools_remote

Por qué existe
──────────────
`uiautomator dump` no ve el contenido web de Chrome, así que los botones de la Página de
Cita solo se podían tocar por coordenadas sacadas de una captura. DevTools los encuentra
por el DOM. Y `Runtime.evaluate` con `userGesture: true` cuenta como gesto del usuario,
que es lo que exige `navigator.share` para abrir la hoja de compartir de Android.

Chrome solo atiende DevTools con la app en primer plano: en segundo plano el socket existe
pero no responde.

El cliente WebSocket es el mínimo que necesita CDP (texto, enmascarado, sin extensiones),
como `phone_clipboard.py` habla el protocolo de scrcpy a mano: una dependencia nueva para
cuarenta líneas no compensa.
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import time
import urllib.parse
import urllib.request

from labkit import telefono

PUERTO = 9222
SOCKET_REMOTO = "localabstract:chrome_devtools_remote"
PLAZO_HTTP_S = 8


class CdpError(RuntimeError):
    pass


# --- Tramas WebSocket (puras: las cubren las pruebas) -------------------------

def trama_texto(texto: str, mascara: bytes | None = None) -> bytes:
    """Trama de texto final y enmascarada, como exige el RFC 6455 a un cliente."""
    datos = texto.encode("utf-8")
    mascara = os.urandom(4) if mascara is None else mascara
    n = len(datos)
    if n < 126:
        cabecera = struct.pack("!BB", 0x81, 0x80 | n)
    elif n < 1 << 16:
        cabecera = struct.pack("!BBH", 0x81, 0x80 | 126, n)
    else:
        cabecera = struct.pack("!BBQ", 0x81, 0x80 | 127, n)
    return cabecera + mascara + bytes(b ^ mascara[i % 4] for i, b in enumerate(datos))


def leer_trama(leer) -> tuple[int, bytes]:
    """(opcode, carga) de la siguiente trama. `leer(n)` devuelve exactamente n bytes. El
    servidor no enmascara; si lo hiciera, se desenmascara igual."""
    b1, b2 = leer(2)
    opcode, n = b1 & 0x0F, b2 & 0x7F
    if n == 126:
        n = struct.unpack("!H", leer(2))[0]
    elif n == 127:
        n = struct.unpack("!Q", leer(8))[0]
    mascara = leer(4) if b2 & 0x80 else None
    carga = leer(n)
    if mascara:
        carga = bytes(b ^ mascara[i % 4] for i, b in enumerate(carga))
    return opcode, carga


# --- Conexión -----------------------------------------------------------------

def reenviar() -> None:
    telefono.adb("forward", f"tcp:{PUERTO}", SOCKET_REMOTO, timeout=15)


def pestañas() -> list[dict]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json", timeout=PLAZO_HTTP_S) as r:
            return json.load(r)
    except OSError as e:
        raise CdpError(f"DevTools no responde (¿Chrome en primer plano?): {e}") from e


def pestaña_con(url: str, plazo: float = 20) -> dict:
    """La pestaña de página cuya URL empieza por `url`, esperando a que aparezca."""
    limite = time.monotonic() + plazo
    while True:
        try:
            for p in pestañas():
                if p.get("type") == "page" and p.get("url", "").startswith(url):
                    return p
        except CdpError:
            if time.monotonic() >= limite:
                raise
        if time.monotonic() >= limite:
            raise CdpError(f"no hay pestaña con {url}")
        time.sleep(1)


class Sesion:
    """Una conexión CDP a una pestaña. Úsese con `with`."""

    def __init__(self, ws_url: str):
        partes = urllib.parse.urlparse(ws_url)
        self._s = socket.create_connection(("127.0.0.1", PUERTO), timeout=30)
        clave = base64.b64encode(os.urandom(16)).decode()
        self._s.sendall((f"GET {partes.path} HTTP/1.1\r\nHost: 127.0.0.1:{PUERTO}\r\n"
                         "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                         f"Sec-WebSocket-Key: {clave}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        respuesta = b""
        while b"\r\n\r\n" not in respuesta:
            trozo = self._s.recv(1024)
            if not trozo:
                raise CdpError("DevTools cerró la conexión en el saludo")
            respuesta += trozo
        if b" 101 " not in respuesta.split(b"\r\n", 1)[0]:
            raise CdpError(f"saludo WebSocket rechazado: {respuesta.split(b'\r\n', 1)[0]!r}")
        self._sobrante = respuesta.split(b"\r\n\r\n", 1)[1]
        self._id = 0

    def _leer(self, n: int) -> bytes:
        while len(self._sobrante) < n:
            trozo = self._s.recv(65536)
            if not trozo:
                raise CdpError("DevTools cerró la conexión")
            self._sobrante += trozo
        datos, self._sobrante = self._sobrante[:n], self._sobrante[n:]
        return datos

    def llamar(self, metodo: str, **params) -> dict:
        self._id += 1
        self._s.sendall(trama_texto(json.dumps({"id": self._id, "method": metodo, "params": params})))
        while True:
            opcode, carga = leer_trama(self._leer)
            if opcode == 0x8:
                raise CdpError("DevTools cerró la conexión")
            if opcode != 0x1:
                continue
            mensaje = json.loads(carga)
            if mensaje.get("id") == self._id:
                if "error" in mensaje:
                    raise CdpError(f"{metodo}: {mensaje['error']}")
                return mensaje.get("result", {})

    def evaluar(self, js: str, gesto: bool = False):
        """Valor de `js` (se espera a las promesas). `gesto=True` lo ejecuta como gesto del
        usuario: sin eso, `navigator.share` rechaza abrir la hoja."""
        r = self.llamar("Runtime.evaluate", expression=js, awaitPromise=True,
                        returnByValue=True, userGesture=gesto)
        if "exceptionDetails" in r:
            raise CdpError(f"el JS lanzó: {r['exceptionDetails'].get('text')} "
                           f"{r['exceptionDetails'].get('exception', {}).get('description', '')}")
        return r.get("result", {}).get("value")

    def esperar(self, js: str, plazo: float = 20, descripcion: str = "") -> object:
        """Primer valor verdadero de `js` antes del plazo."""
        limite = time.monotonic() + plazo
        while True:
            valor = self.evaluar(js)
            if valor:
                return valor
            if time.monotonic() >= limite:
                raise CdpError(f"no se cumplió {descripcion or js!r} en {plazo:.0f} s")
            time.sleep(0.5)

    def close(self) -> None:
        self._s.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def sesion_en(url: str) -> Sesion:
    return Sesion(pestaña_con(url)["webSocketDebuggerUrl"])
