"""
Doble de la Graph API de Meta para probar el flujo completo sin credenciales.

Reproduce el comportamiento que importa y que es difícil de acertar a ciegas:
  - /{page}/photos           devuelve post_id
  - /{ig}/media              devuelve un contenedor
  - GET /{container}         devuelve IN_PROGRESS un par de veces y luego FINISHED
  - /{ig}/media_publish      falla la primera vez con el código 9007 ("Media ID is
                             not available") y funciona al reintentar
  - también sirve la imagen, para verificar el chequeo de URL pública

Si el publicador pasa contra esto, lo único que puede fallar en producción son
las credenciales y los permisos, no la orquestación.
"""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

STATE = {"polls": 0, "publish_attempts": 0, "calls": []}
IMAGE_BYTES = b""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # silencio
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── imagen pública ──
    def do_HEAD(self):  # noqa: N802
        if self.path.startswith("/img"):
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(IMAGE_BYTES)))
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path
        STATE["calls"].append(("GET", path))

        if path.startswith("/img"):
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(IMAGE_BYTES)
            return

        # polling del contenedor
        if re.fullmatch(r"/container_\d+", path):
            STATE["polls"] += 1
            code = "FINISHED" if STATE["polls"] >= 2 else "IN_PROGRESS"
            return self._json(200, {"status_code": code, "status": code})

        return self._json(404, {"error": {"message": f"sin ruta {path}", "code": 100}})

    def do_POST(self):  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        data = parse_qs(self.rfile.read(length).decode())
        STATE["calls"].append(("POST", path))

        if not data.get("access_token"):
            return self._json(401, {"error": {"message": "falta access_token", "code": 190}})

        if path.endswith("/photos"):
            if not data.get("url"):
                return self._json(400, {"error": {"message": "falta url", "code": 100}})
            return self._json(200, {"id": "photo_1", "post_id": "PAGE_POST_1"})

        if path.endswith("/media"):
            if not data.get("image_url"):
                return self._json(
                    400,
                    {"error": {"message": "Param image_url is not a valid URI", "code": 100}},
                )
            return self._json(200, {"id": "container_1"})

        if path.endswith("/media_publish"):
            STATE["publish_attempts"] += 1
            if STATE["publish_attempts"] == 1:
                # el fallo real que obliga a reintentar
                return self._json(
                    400,
                    {"error": {"message": "Media ID is not available", "code": 9007,
                               "error_subcode": 2207006}},
                )
            return self._json(200, {"id": "IG_POST_1"})

        if path.endswith("/threads"):
            return self._json(200, {"id": "th_container_1"})
        if path.endswith("/threads_publish"):
            return self._json(200, {"id": "TH_POST_1"})

        return self._json(404, {"error": {"message": f"sin ruta {path}", "code": 100}})


def start(image_path=None) -> tuple[HTTPServer, str]:
    global IMAGE_BYTES  # noqa: PLW0603
    if image_path:
        IMAGE_BYTES = open(image_path, "rb").read()
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"
