"""
Publicación en Facebook Page, Instagram Business y Threads por Graph API.

El flujo de Instagram (contenedor → polling → media_publish, con los reintentos
por "Media ID is not available") está portado del cliente que ya funciona en
WorkItContentCreation: packages/social-apis/src/platforms/instagram/client.ts.
Esa parte es la única delicada de toda la Graph API y no vale la pena
reinventarla — allí ya está depurada contra la API de producción.

Credenciales por variable de entorno. Nunca en el código, nunca en el repo.
"""
from __future__ import annotations

import os
import time

import requests

API_VERSION = os.environ.get("META_API_VERSION", "v24.0")

# META_GRAPH_BASE existe para poder apuntar a un doble de la API en pruebas.
# En producción se deja sin definir y va a los servidores de Meta.
GRAPH = os.environ.get("META_GRAPH_BASE") or f"https://graph.facebook.com/{API_VERSION}"
THREADS_GRAPH = os.environ.get("META_THREADS_BASE") or "https://graph.threads.net/v1.0"

# Códigos con los que Meta dice "la imagen aún no está lista, vuelve a intentarlo".
# Vienen del cliente de WorkIt; sin esto, un porcentaje de publicaciones falla sin motivo.
RETRYABLE = {9007, 24}
RETRYABLE_SUBCODES = {2207006}


class MetaError(RuntimeError):
    pass


def _post(url: str, data: dict, timeout: int = 120) -> dict:
    r = requests.post(url, data=data, timeout=timeout)
    if not r.ok:
        try:
            err = r.json().get("error", {})
        except Exception:  # noqa: BLE001
            raise MetaError(f"HTTP {r.status_code}: {r.text[:300]}") from None
        raise MetaError(
            f"HTTP {r.status_code} · code={err.get('code')} "
            f"subcode={err.get('error_subcode')} · {err.get('message')}"
        )
    return r.json()


def _get(url: str, params: dict, timeout: int = 60) -> dict:
    r = requests.get(url, params=params, timeout=timeout)
    if not r.ok:
        raise MetaError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


# ─────────────────────────── Facebook ───────────────────────────

def publish_facebook(image_url: str, caption: str) -> dict:
    """
    Una sola llamada: POST /{page-id}/photos con url + caption.
    La foto se publica con el copy como pie, que es la regla de imagen.
    """
    page_id = os.environ["SDB_PAGE_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]
    out = _post(
        f"{GRAPH}/{page_id}/photos",
        {"url": image_url, "caption": caption, "access_token": token},
    )
    post_id = out.get("post_id") or out.get("id")
    return {"post_id": post_id, "url": f"https://www.facebook.com/{post_id}"}


# ─────────────────────────── Instagram ───────────────────────────

def _wait_for_container(container_id: str, token: str, attempts: int = 12, delay: int = 5) -> None:
    """Instagram descarga y procesa la imagen de forma asíncrona."""
    for _ in range(attempts):
        time.sleep(delay)
        status = _get(
            f"{GRAPH}/{container_id}",
            {"fields": "status_code,status", "access_token": token},
        )
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise MetaError(f"contenedor {code}: {status.get('status')}")
    raise MetaError(f"el contenedor no quedó listo tras {attempts * delay} s")


def _publish_with_retry(ig_id: str, container_id: str, token: str, attempts: int = 5) -> dict:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return _post(
                f"{GRAPH}/{ig_id}/media_publish",
                {"creation_id": container_id, "access_token": token},
            )
        except MetaError as e:
            last = e
            msg = str(e)
            retryable = any(f"code={c}" in msg for c in RETRYABLE) or any(
                f"subcode={s}" in msg for s in RETRYABLE_SUBCODES
            )
            if not retryable:
                raise
            time.sleep(3 * (i + 1))
    raise MetaError(f"media_publish agotó los reintentos: {last}")


def publish_instagram(image_url: str, caption: str) -> dict:
    """
    Instagram NO acepta subida binaria: descarga la imagen desde image_url,
    que tiene que ser HTTPS y pública. Ese es el requisito que obliga a tener
    hosting de imágenes (ver README, sección "El único bloqueo real").
    """
    ig_id = os.environ["SDB_IG_USER_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]

    container = _post(
        f"{GRAPH}/{ig_id}/media",
        {"image_url": image_url, "caption": caption, "access_token": token},
    )
    _wait_for_container(container["id"], token)
    out = _publish_with_retry(ig_id, container["id"], token)
    return {"post_id": out["id"], "url": f"https://www.instagram.com/p/{out['id']}"}


# ─────────────────────────── Threads ───────────────────────────

def publish_threads(image_url: str, text: str) -> dict:
    """
    Mismo patrón de dos pasos que Instagram. Usa su propio token
    (las credenciales de la app de Threads ya existen en WorkIt).
    """
    user_id = os.environ["SDB_THREADS_USER_ID"]
    token = os.environ["SDB_THREADS_TOKEN"]

    container = _post(
        f"{THREADS_GRAPH}/{user_id}/threads",
        {"media_type": "IMAGE", "image_url": image_url, "text": text, "access_token": token},
    )
    time.sleep(5)
    out = _post(
        f"{THREADS_GRAPH}/{user_id}/threads_publish",
        {"creation_id": container["id"], "access_token": token},
    )
    return {"post_id": out["id"], "url": f"https://www.threads.net/@sabiduriabolsillo/post/{out['id']}"}


# ─────────────────────────── Descubrimiento ───────────────────────────

def discover(user_token: str) -> None:
    """
    Ejecutar UNA vez para obtener los ids y el token de página.
    Imprime lo que hay que meter en los secrets. No guarda nada en disco.

        python3 -c "from src.platforms.meta import discover; discover('TOKEN_DE_USUARIO')"
    """
    data = _get(
        f"{GRAPH}/me/accounts",
        {
            "access_token": user_token,
            "fields": "id,name,access_token,instagram_business_account{id,username}",
        },
    )
    for page in data.get("data", []):
        print(f"\nPágina: {page['name']}")
        print(f"  SDB_PAGE_ID     = {page['id']}")
        print(f"  SDB_PAGE_TOKEN  = <el access_token de esta página; no lo pego aquí>")
        ig = page.get("instagram_business_account")
        if ig:
            print(f"  SDB_IG_USER_ID  = {ig['id']}   (@{ig.get('username')})")
        else:
            print("  sin cuenta de Instagram vinculada")


PUBLISHERS = {
    "facebook": publish_facebook,
    "instagram": publish_instagram,
    "threads": publish_threads,
}
