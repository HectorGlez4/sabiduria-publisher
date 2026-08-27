#!/usr/bin/env python3
"""
Averigua el SDB_THREADS_USER_ID a partir del token, sin que el token salga de tu máquina.

    export SDB_THREADS_TOKEN='el-token-que-acabas-de-generar'
    .venv/bin/python scripts/threads_user_id.py

Imprime SOLO el id numérico y el nombre de usuario. El token no se imprime, no se
guarda en ningún fichero y no se manda a ninguna parte que no sea graph.threads.net.

Por qué existe: publish_threads necesita dos secretos, el token y el id de usuario,
y Meta solo te da el primero en la consola. El segundo se pregunta a la API con el
primero. Hacerlo con un script en vez de a mano evita pegar el token en un curl que
queda en el historial del shell.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://graph.threads.net/v1.0/me"


def main() -> int:
    token = os.environ.get("SDB_THREADS_TOKEN")
    if not token:
        print("Falta SDB_THREADS_TOKEN en el entorno.\n"
              "  export SDB_THREADS_TOKEN='...'", file=sys.stderr)
        return 2

    url = f"{API}?" + urllib.parse.urlencode(
        {"fields": "id,username", "access_token": token})
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        # El cuerpo del error de Meta no lleva el token, pero sí puede llevar
        # trazas: se recorta a lo que identifica el problema.
        try:
            msg = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        print(f"La API rechazó el token (HTTP {e.code}). {msg[:200]}", file=sys.stderr)
        return 1

    print(f"SDB_THREADS_USER_ID = {d['id']}")
    print(f"  (cuenta: @{d.get('username', '?')})")
    print("\nAñádelo como secreto en GitHub junto al token:")
    print("  https://github.com/HectorGlez4/sabiduria-publisher/settings/secrets/actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
