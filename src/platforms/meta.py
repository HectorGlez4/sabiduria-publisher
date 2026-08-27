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


def _permalink(obj_id: str, token: str, campo: str, respaldo: str) -> str:
    """
    Pregunta a la API por el enlace real en vez de construirlo.

    Construirlo era adivinar, y se adivinaba mal: el permalink de Instagram usa
    un codigo corto, no el id numerico del medio, asi que la URL guardada daba
    "Sorry, this page isn't available" aunque la publicacion estuviera viva.

    Nunca levanta: en este punto la publicacion YA salio, y un enlace es un
    dato de registro. Perder el enlace es molesto; perder la publicacion por no
    poder leerlo seria absurdo.
    """
    try:
        d = _get(f"{GRAPH}/{obj_id}", {"fields": campo, "access_token": token})
        return d.get(campo) or respaldo
    except Exception:  # noqa: BLE001
        return respaldo


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
    return {
        "post_id": post_id,
        "url": _permalink(post_id, token, "permalink_url",
                          f"https://www.facebook.com/{post_id}"),
    }


# ─────────────────────────── Facebook Historias ───────────────────────────

def publish_story(image_url: str, _caption: str = "") -> dict:
    """
    Dos pasos: subir la foto SIN publicar, y luego convertirla en historia.

      POST /{page-id}/photos        published=false   → photo_id
      POST /{page-id}/photo_stories photo_id=…        → {success, post_id}

    El primer paso es el mismo endpoint que usa `publish_facebook`, con una
    diferencia que lo cambia todo: `published=false` deja la foto subida y sin
    aparecer en ninguna parte. Sin ese parámetro tendrías la misma imagen dos
    veces —una en el feed y otra como historia—, que es justo lo que no se quiere.

    Una historia no lleva pie: el texto va dentro de la imagen. Por eso el
    segundo argumento se ignora y está ahí solo para que la firma encaje con la
    de los demás adaptadores y el bucle de publish.py no tenga que distinguir.

    Las historias caducan a las 24 horas. No se registra permalink porque no hay
    nada estable a lo que enlazar.
    """
    page_id = os.environ["SDB_PAGE_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]

    foto = _post(
        f"{GRAPH}/{page_id}/photos",
        {"url": image_url, "published": "false", "access_token": token},
    )
    photo_id = foto.get("id")
    if not photo_id:
        raise MetaError(f"la foto de la historia no devolvió id: {foto}")

    out = _post(
        f"{GRAPH}/{page_id}/photo_stories",
        {"photo_id": photo_id, "access_token": token},
    )
    if not out.get("success", True):
        raise MetaError(f"la historia no se publicó: {out}")

    return {
        "post_id": str(out.get("post_id") or photo_id),
        "photo_id": photo_id,
        # Las historias no tienen permalink estable: duran 24 h y luego no hay
        # nada a lo que apuntar. Se deja constancia en vez de inventar una URL
        # que mañana daría "esta página no está disponible".
        "url": None,
        "caduca": "24h",
    }


# ─────────────────────────── Facebook Reels ───────────────────────────

# Los reels NO pasan por graph.facebook.com para el binario: hay un host
# aparte, y olvidarlo devuelve un error que no menciona el host por ningún lado.
RUPLOAD = os.environ.get("META_RUPLOAD_BASE") or "https://rupload.facebook.com/video-upload"


def publish_reel(video_path: str, description: str) -> dict:
    """
    Tres fases, y ninguna se puede saltar.

      start   POST /{page-id}/video_reels   → devuelve video_id
      upload  POST a rupload.facebook.com con el binario en el cuerpo
      finish  POST /{page-id}/video_reels con video_state=PUBLISHED

    A diferencia de /photos —que es una sola llamada con una URL y ya— aquí el
    vídeo se SUBE. No vale darle una URL pública: por eso este adaptador recibe
    una ruta de fichero y no una URL, y por eso no necesita el hosting de
    src/hosting.py.

    Por qué reels y no fotos: la página tiene 28.000 seguidores y su mejor foto
    en 90 días llegó a 408 personas. Los reels son la única superficie que
    reparte a no seguidores. Ver la cabecera de src/render/reel.py.
    """
    page_id = os.environ["SDB_PAGE_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]
    tamano = os.path.getsize(video_path)

    inicio = _post(
        f"{GRAPH}/{page_id}/video_reels",
        {"upload_phase": "start", "access_token": token},
    )
    video_id = inicio["video_id"]

    # El binario va en el cuerpo crudo, y las cabeceras son obligatorias:
    # 'Authorization: OAuth <token>' —no el parámetro access_token de siempre—
    # más offset y file_size. Si falta file_size, Meta acepta la petición y
    # deja el vídeo a medias sin decir nada.
    with open(video_path, "rb") as f:
        r = requests.post(
            f"{RUPLOAD}/{API_VERSION}/{video_id}",
            headers={
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(tamano),
                "Content-Type": "application/octet-stream",
            },
            data=f.read(),
            timeout=300,
        )
    if not r.ok:
        raise MetaError(f"subida del reel HTTP {r.status_code}: {r.text[:300]}")

    _esperar_reel(video_id, token)

    fin = _post(
        f"{GRAPH}/{page_id}/video_reels",
        {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": description,
            "access_token": token,
        },
    )
    if not fin.get("success", True):
        raise MetaError(f"el reel no se publicó: {fin}")

    return {
        "post_id": video_id,
        "url": _permalink(video_id, token, "permalink_url",
                          f"https://www.facebook.com/reel/{video_id}"),
    }


def _esperar_reel(video_id: str, token: str, attempts: int = 20, delay: int = 6) -> None:
    """
    Facebook procesa el vídeo de forma asíncrona, igual que Instagram con su
    contenedor. Publicar antes de que termine devuelve un reel roto o vacío.

    No levanta si el estado no llega a 'ready': hay vídeos que se quedan en
    'in_progress' y aun así publican bien. Se le da su tiempo y se sigue; si de
    verdad está mal, la fase finish lo dirá con un error de verdad.
    """
    for _ in range(attempts):
        time.sleep(delay)
        try:
            estado = _get(f"{GRAPH}/{video_id}",
                          {"fields": "status", "access_token": token})
        except MetaError:
            continue
        fase = ((estado.get("status") or {}).get("video_status")
                or (estado.get("status") or {}).get("uploading_phase", {}).get("status"))
        if fase in ("ready", "complete", "published"):
            return
        if fase == "error":
            raise MetaError(f"Facebook rechazó el vídeo del reel: {estado.get('status')}")


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
    return {
        "post_id": out["id"],
        "url": _permalink(out["id"], token, "permalink",
                          f"https://www.instagram.com/p/{out['id']}"),
    }


def publish_instagram_story(image_url: str, _caption: str = "") -> dict:
    """
    Historia de Instagram: mismo endpoint que una foto, con media_type=STORIES.

      POST /{ig-user-id}/media          media_type=STORIES, image_url=…
      POST /{ig-user-id}/media_publish  creation_id=…

    Dos cosas que no son iguales que en la foto de feed:

    · **Solo JPEG.** La documentación de publicación de Instagram lo dice sin
      matices: JPEG es el único formato de imagen admitido, y los JPEG
      extendidos (MPO, JPS) tampoco. Por eso publish.py renderiza la historia en
      .jpg para esta red y en .png para Facebook, que sí acepta PNG.

    · **Sin pie.** El texto va dentro de la imagen, como en la de Facebook. El
      segundo argumento existe para que la firma encaje con la de los demás
      adaptadores.

    Caduca en 24 h. No se registra permalink: consultarlo cuesta otra llamada
    para devolver una URL que mañana da "contenido no disponible". Se deja el id
    del medio, que es lo que sirve para pedir métricas mientras vive.
    """
    ig_id = os.environ["SDB_IG_USER_ID"]
    token = os.environ["SDB_PAGE_TOKEN"]

    container = _post(
        f"{GRAPH}/{ig_id}/media",
        {"media_type": "STORIES", "image_url": image_url, "access_token": token},
    )
    _wait_for_container(container["id"], token)
    out = _publish_with_retry(ig_id, container["id"], token)
    return {
        "post_id": out["id"],
        "url": None,
        "caduca": "24h",
    }


# ─────────────────────────── Threads ───────────────────────────

def publish_threads(image_url: str | None, text: str) -> dict:
    """
    Mismo patrón de dos pasos que Instagram. Usa su propio token
    (las credenciales de la app de Threads ya existen en WorkIt).

    Con `image_url` a None publica un hilo de SOLO TEXTO (media_type=TEXT). Es
    lo que usa scripts/hilos.py: en Threads el formato nativo es el texto con su
    enlace, y mandar media_type=IMAGE con image_url vacío hace que la API
    rechace el contenedor. Con imagen sigue funcionando igual que antes, para la
    pieza que salga en las tres redes a la vez.
    """
    user_id = os.environ["SDB_THREADS_USER_ID"]
    token = os.environ["SDB_THREADS_TOKEN"]

    campos = {"text": text, "access_token": token}
    if image_url:
        campos |= {"media_type": "IMAGE", "image_url": image_url}
    else:
        campos["media_type"] = "TEXT"

    container = _post(f"{THREADS_GRAPH}/{user_id}/threads", campos)
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
    # No está en `targets` de ninguna pieza todavía: es la prueba que hay que
    # hacer. Se mete una pieza al día como reel y en dos semanas se compara el
    # alcance contra las fotos, con datos y no con opiniones.
    "facebook_reel": publish_reel,
    # Una historia NO sustituye a la publicación: es otra superficie y caduca en
    # 24 h, así que se suma a los targets en vez de reemplazar nada.
    "facebook_story": publish_story,
    "instagram": publish_instagram,
    # La misma pieza como historia de Instagram. Va aparte de "instagram"
    # porque es otra superficie: la foto vive en el perfil y la historia caduca
    # en 24 h, así que se suman en `targets` en vez de sustituirse.
    "instagram_story": publish_instagram_story,
    "threads": publish_threads,
}
