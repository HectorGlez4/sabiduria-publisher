#!/usr/bin/env python3
"""
Descubre los ids de la página y de Instagram y deja los secrets puestos, sin que
el token pase nunca por una pantalla.

El token de usuario se lee de .env (que está en .gitignore) o de la variable
SDB_USER_TOKEN. El token de página no se imprime jamás: viaja por una tubería
hasta `gh secret set`, que lo lee de stdin.

    # 1. pon tu token de usuario en .env, en una linea:
    #    SDB_USER_TOKEN=EAA...
    # 2. ejecuta:
    python3 scripts/configurar_secrets.py --pagina "Sabiduria De Bolsillo"

Con --dry-run enseña qué encontró y qué secrets pondría, sin tocar nada.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import requests  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = os.environ.get("META_API_VERSION", "v24.0")
# Igual que en meta.py: permite apuntar a un doble de la API para probar esto
# sin gastar un token real. En uso normal se deja sin definir.
GRAPH = os.environ.get("META_GRAPH_BASE") or f"https://graph.facebook.com/{API}"
APP_ID_POR_DEFECTO = "3733795406925924"
WORKIT_ENV = "/Users/hec/dev/WorkItContentCreation/server/.env"


def leer_token() -> str:
    tok = os.environ.get("SDB_USER_TOKEN", "").strip()
    if tok:
        return tok
    env = ROOT / ".env"
    if env.is_file():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith("SDB_USER_TOKEN="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(
        "No encuentro el token de usuario.\n"
        "  Añade a .env una línea:  SDB_USER_TOKEN=EAA...\n"
        "  (.env está en .gitignore; el token no sale de tu máquina)"
    )


def leer_app_secret() -> tuple[str, str]:
    """App id y secret. El secret no se imprime ni se registra en ningun sitio."""
    app_id = os.environ.get("SDB_APP_ID", "").strip() or APP_ID_POR_DEFECTO
    sec = os.environ.get("SDB_APP_SECRET", "").strip()
    fuentes = [ROOT / ".env", pathlib.Path(WORKIT_ENV)]
    for f in fuentes:
        if sec:
            break
        if not f.is_file():
            continue
        for linea in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            for clave in ("SDB_APP_SECRET=", "FACEBOOK_APP_SECRET="):
                if linea.startswith(clave):
                    sec = linea.split("=", 1)[1].strip().strip('"').strip("'")
            if linea.startswith("FACEBOOK_APP_ID=") and not os.environ.get("SDB_APP_ID"):
                app_id = linea.split("=", 1)[1].strip().strip('"').strip("'")
    if not sec:
        sys.exit(
            "No encuentro el App Secret, y sin el no se puede canjear el token.\n"
            f"  Lo busco en {ROOT / '.env'} (SDB_APP_SECRET=) y en {WORKIT_ENV}\n"
            "  (FACEBOOK_APP_SECRET=). No lo imprimo en ningun momento."
        )
    return app_id, sec


def canjear_por_larga_duracion(corto: str) -> str:
    """
    Cambia el token de ~1 h del Explorer por uno de ~60 dias.

    Importa mas de lo que parece: los tokens de PAGINA heredan la caducidad del
    token de usuario con el que se piden. Pedidos con el token corto, caducan en
    una hora y manana no se publica. Pedidos con uno de larga duracion, los
    tokens de pagina ya no caducan.
    """
    app_id, secret = leer_app_secret()
    r = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": secret,
            "fb_exchange_token": corto,
        },
        timeout=60,
    )
    if not r.ok:
        err = r.json().get("error", {})
        sys.exit(
            f"No se pudo canjear el token: {err.get('message', r.text[:200])}\n"
            "  Comprueba que el App Secret corresponde a la app del token."
        )
    largo = r.json().get("access_token")
    if not largo:
        sys.exit("El canje no devolvio token.")
    print("  ✓ token de usuario canjeado por uno de larga duracion (~60 dias)")
    return largo


def cuentas(token: str) -> list[dict]:
    r = requests.get(
        f"{GRAPH}/me/accounts",
        params={
            "access_token": token,
            "fields": "id,name,access_token,tasks,instagram_business_account{id,username}",
        },
        timeout=60,
    )
    if not r.ok:
        err = r.json().get("error", {})
        sys.exit(
            f"La Graph API rechazó la llamada: {err.get('message', r.text[:200])}\n"
            f"  code={err.get('code')} subcode={err.get('error_subcode')}\n"
            "  Suele ser un token caducado o sin el scope pages_show_list."
        )
    return r.json().get("data", [])


def poner_secret(nombre: str, valor: str, repo: str) -> None:
    """El valor entra por stdin. No se imprime ni se pasa por la línea de comandos."""
    p = subprocess.run(
        ["gh", "secret", "set", nombre, "--repo", repo],
        input=valor, text=True, capture_output=True,
    )
    if p.returncode != 0:
        sys.exit(f"gh secret set {nombre}: {p.stderr.strip()}")
    print(f"  ✓ {nombre}")


def verificar(token_pagina: str, page_id: str, ig_id: str | None,
              tasks: list[str] | None) -> int:
    """
    Comprueba de SOLO LECTURA que el token de pagina sirve de verdad.

    Existe para separar "las credenciales estan mal" de "la orquestacion esta
    mal" ANTES de publicar en una pagina real. No escribe nada.
    """
    fallos = 0

    r = requests.get(f"{GRAPH}/{page_id}",
                     params={"fields": "name,fan_count,verification_status",
                             "access_token": token_pagina}, timeout=60)
    if r.ok:
        d = r.json()
        print(f"  ✓ pagina: {d.get('name')} · {d.get('fan_count', '?')} seguidores "
              f"· {d.get('verification_status', 'sin dato')}")
    else:
        fallos += 1
        print(f"  ✗ pagina: {r.json().get('error', {}).get('message', r.text[:120])}")

    # 'tasks' dice que permisos REALES hay sobre la pagina. Viene de la llamada
    # de descubrimiento, que se hace con el token de USUARIO: pedirselo a
    # /me/accounts con el token de PAGINA falla, y ademas falla en silencio.
    if tasks is None:
        fallos += 1
        print("  ✗ no se pudo leer 'tasks': no se puede confirmar permiso de publicar")
    else:
        tiene = "CREATE_CONTENT" in tasks
        fallos += 0 if tiene else 1
        print(f"  {'✓' if tiene else '✗'} permiso de publicar (CREATE_CONTENT)")
        print(f"      permisos sobre la pagina: {', '.join(tasks) or '(ninguno)'}")

    if ig_id:
        r = requests.get(f"{GRAPH}/{ig_id}",
                         params={"fields": "username,media_count",
                                 "access_token": token_pagina}, timeout=60)
        if r.ok:
            d = r.json()
            print(f"  ✓ instagram: @{d.get('username')} · {d.get('media_count', '?')} publicaciones")
        else:
            fallos += 1
            print(f"  ✗ instagram: {r.json().get('error', {}).get('message', r.text[:120])}")

    return fallos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pagina", help="nombre (o parte) de la página; si falta, las lista")
    ap.add_argument("--repo", default="HectorGlez4/sabiduria-publisher")
    ap.add_argument("--dry-run", action="store_true", help="enseña sin poner nada")
    ap.add_argument("--verificar", action="store_true",
                    help="comprueba de solo lectura que el token sirve; no publica")
    a = ap.parse_args()

    print("\nCanjeando el token del Explorer, que dura ~1 hora:")
    token = canjear_por_larga_duracion(leer_token())
    paginas = cuentas(token)
    if not paginas:
        sys.exit("El token no da acceso a ninguna página. ¿Falta el scope pages_show_list?")

    print(f"\nPáginas visibles con este token ({len(paginas)}):")
    for p in paginas:
        ig = p.get("instagram_business_account") or {}
        marca = "IG @" + ig["username"] if ig.get("username") else "sin IG vinculado"
        print(f"  · {p['name']:38s} id={p['id']:20s} {marca}")

    if not a.pagina:
        print("\nVuelve a ejecutar con --pagina \"<nombre>\" para poner los secrets.")
        return 0

    match = [p for p in paginas if a.pagina.lower() in p["name"].lower()]
    if len(match) != 1:
        sys.exit(f"\n'{a.pagina}' encaja con {len(match)} páginas. Afina el nombre.")
    pag = match[0]
    ig = pag.get("instagram_business_account") or {}

    print(f"\nElegida: {pag['name']}")
    if not ig.get("id"):
        print("  ⚠ Esta página NO tiene cuenta de Instagram Business vinculada.")
        print("    Instagram no podrá publicar hasta que la vincules en Meta Business.")
    if not pag.get("access_token"):
        sys.exit("  ✗ La respuesta no trae token de página. ¿Falta pages_read_engagement?")

    secrets = {"SDB_PAGE_ID": pag["id"], "SDB_PAGE_TOKEN": pag["access_token"]}
    if ig.get("id"):
        secrets["SDB_IG_USER_ID"] = ig["id"]

    if a.verificar:
        print("\nVerificando de solo lectura (no se publica nada):")
        fallos = verificar(pag["access_token"], pag["id"], ig.get("id"), pag.get("tasks"))
        if fallos:
            print(f"\n{fallos} comprobacion(es) fallaron. NO publiques todavia.")
            return 1
        print("\nLas credenciales sirven. El publicador puede salir.")
        return 0

    if a.dry_run:
        print(f"\nPondría estos secrets en {a.repo} (valores ocultos):")
        for k in secrets:
            print(f"  · {k}")
        return 0

    print(f"\nPoniendo secrets en {a.repo}:")
    for k, v in secrets.items():
        poner_secret(k, v, a.repo)
    print("\nListo. El token de página no se ha impreso en ningún momento.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
