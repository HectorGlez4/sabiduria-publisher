#!/usr/bin/env python3
"""
Por qué las publicaciones de Facebook no llegan a nadie.

    python3 scripts/diagnostico_meta.py

No imprime ni un solo carácter de ningún token. Está pensado para correr
dentro de GitHub Actions (workflow_dispatch), que es donde viven los secrets.

Qué contesta, en este orden:

  1. ¿De qué app es el token?  Si es una app distinta de la que publicaba
     antes, ya tenemos el cambio del 17 de agosto localizado.

  2. ¿Qué permisos trae y la página está publicada?

  3. LA PRUEBA. Recorre el feed de la página y pide a la propia API las
     impresiones de cada publicación. Las hechas a mano antes del 17 de
     agosto tienen alcance; las de la API, cero. Ver esa frontera en los
     datos de Meta —no en Business Suite, no en una captura— es lo que
     convierte la sospecha en diagnóstico.

     Meta documenta que "any data generated while an app is in Development
     mode, such as test posts, can only be seen by role users". Eso da
     exactamente esto: la publicación existe, tú la ves porque tienes rol
     en la app, y no la ve nadie más.
     https://developers.facebook.com/docs/development/build-and-test/app-modes
"""
from __future__ import annotations

import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.platforms.meta import GRAPH, MetaError, _get  # noqa: E402


def seccion(titulo: str) -> None:
    print(f"\n{'─' * 62}\n{titulo}\n{'─' * 62}")


def de_quien_es_el_token(token: str) -> str | None:
    """
    debug_token dice a qué app pertenece. Se autentica con el propio token
    como app-token improvisado; si Meta lo rechaza no pasa nada, seguimos.
    """
    seccion("1 · De qué app es el token")
    try:
        d = _get(f"{GRAPH}/debug_token",
                 {"input_token": token, "access_token": token}).get("data", {})
    except MetaError as e:
        print(f"  no se pudo inspeccionar el token: {e}")
        return None

    app_id = d.get("app_id")
    print(f"  app          {d.get('application', '(sin nombre)')}  (id {app_id})")
    print(f"  tipo         {d.get('type')}")
    print(f"  válido       {d.get('is_valid')}")
    caduca = d.get("expires_at")
    print(f"  caduca       {'nunca' if caduca == 0 else caduca}")
    print(f"  permisos     {', '.join(d.get('scopes') or []) or '(ninguno)'}")
    print("\n  → Compara este id con el de la app que publicaba antes del 17 de agosto.")
    print("    Si no coinciden, ahí está el cambio.")
    print(f"    Modo de la app: https://developers.facebook.com/apps/{app_id}/settings/basic/")
    return app_id


def estado_de_la_pagina(page_id: str, token: str) -> None:
    seccion("2 · Estado de la página")
    try:
        d = _get(f"{GRAPH}/{page_id}", {
            "fields": "id,name,fan_count,followers_count,is_published,"
                      "verification_status,has_transitioned_to_new_page_experience",
            "access_token": token,
        })
    except MetaError as e:
        print(f"  no se pudo leer la página: {e}")
        return
    for k, v in d.items():
        print(f"  {k:46s} {v}")
    if d.get("is_published") is False:
        print("\n  ⚠ La página está SIN publicar. Nada de lo que salga de aquí llega a nadie.")


def impresiones_por_publicacion(page_id: str, token: str, cuantas: int = 30) -> None:
    """
    La frontera, medida por la propia API.

    post_impressions_unique es el alcance. Se pide publicación por publicación
    porque el insight vive en el objeto de la publicación, no en el feed.
    """
    seccion(f"3 · Alcance real de las últimas {cuantas} publicaciones (según la API)")
    try:
        feed = _get(f"{GRAPH}/{page_id}/posts", {
            "fields": "id,created_time,is_published,is_hidden,privacy,message",
            "limit": cuantas,
            "access_token": token,
        }).get("data", [])
    except MetaError as e:
        print(f"  no se pudo leer el feed: {e}")
        return

    print(f"  {'creada':17s} {'alcance':>8s} {'impres.':>8s}  {'privacidad':12s} oculta  texto")
    for p in feed:
        alcance = impresiones = "?"
        try:
            ins = _get(f"{GRAPH}/{p['id']}/insights", {
                "metric": "post_impressions_unique,post_impressions",
                "access_token": token,
            }).get("data", [])
            vals = {m["name"]: m["values"][0].get("value") for m in ins if m.get("values")}
            alcance = vals.get("post_impressions_unique", "?")
            impresiones = vals.get("post_impressions", "?")
        except MetaError as e:
            alcance = f"err({e})"[:14]

        privacidad = (p.get("privacy") or {}).get("value") or "?"
        texto = (p.get("message") or "").replace("\n", " ")[:34]
        print(f"  {p.get('created_time', '')[:16]:17s} {str(alcance):>8s} "
              f"{str(impresiones):>8s}  {privacidad:12s} "
              f"{str(p.get('is_hidden')):6s}  {texto}")

    print("\n  Lee la columna 'alcance' de abajo arriba y busca dónde cae a 0.")
    print("  Si el corte coincide con la primera publicación del bot")
    print("  (17 ago 2026, 20:02 UTC), el problema es la app, no el contenido.")


def main() -> int:
    try:
        page_id = os.environ["SDB_PAGE_ID"]
        token = os.environ["SDB_PAGE_TOKEN"]
    except KeyError as e:
        print(f"falta la variable {e}. En local: exportar desde .env; "
              f"en Actions ya vienen de los secrets.", file=sys.stderr)
        return 1

    print(f"Diagnóstico de la página {page_id} · API {GRAPH.rsplit('/', 1)[-1]}")
    de_quien_es_el_token(token)
    estado_de_la_pagina(page_id, token)
    impresiones_por_publicacion(page_id, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
