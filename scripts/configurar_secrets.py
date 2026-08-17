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


def cuentas(token: str) -> list[dict]:
    r = requests.get(
        f"{GRAPH}/me/accounts",
        params={
            "access_token": token,
            "fields": "id,name,access_token,instagram_business_account{id,username}",
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pagina", help="nombre (o parte) de la página; si falta, las lista")
    ap.add_argument("--repo", default="HectorGlez4/sabiduria-publisher")
    ap.add_argument("--dry-run", action="store_true", help="enseña sin poner nada")
    a = ap.parse_args()

    paginas = cuentas(leer_token())
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
