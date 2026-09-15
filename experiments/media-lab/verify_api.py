#!/usr/bin/env python3
"""Read-only verification of API-published media-lab posts.

Con --metricas, además de comprobar que la publicación existe, pide a la Graph
API las instantáneas de audiencia (alcance, interacciones, …) de cada
plataforma. Una métrica no soportada o una superficie sin API de métricas (las
Stories de Facebook) no marca la publicación como fallida: queda anotada en
`results[plataforma]["metrics_errors"]`. El código de salida solo refleja si la
propia publicación se pudo leer, nunca las métricas.

Ningún token llega al JSON de salida ni a stdout: todo texto de error pasa por
`_redactar` antes de guardarse o imprimirse (incluida la excepción que levante
`requests` al pedir una página de `paging.next`, que lleva el access_token en
la URL).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.platforms.meta import GRAPH, THREADS_GRAPH, _get  # noqa: E402

CONSULTAS = {
    "facebook": (GRAPH, "id,permalink_url,created_time,message,full_picture,is_published,is_hidden", "SDB_PAGE_TOKEN"),
    "instagram": (GRAPH, "id,permalink,timestamp,caption,media_type,media_url", "SDB_PAGE_TOKEN"),
    "threads": (THREADS_GRAPH, "id,permalink,timestamp,text,media_type,media_url", "SDB_THREADS_TOKEN"),
}

# Los mismos nombres de plataforma que CONSULTAS, salvo instagram que se parte en
# feed/story porque son dos superficies con métricas distintas en la misma API.
# post_media_view y post_total_media_view_unique son el reemplazo moderno de
# post_impressions*/post_impressions_unique para posts de una sola imagen; se piden
# los seis a la vez y, si Meta ya retiró alguno de los antiguos, ese queda en
# metrics_errors sin tirar a los demás (ver _fetch_metrics).
METRICAS = {
    "facebook": ["post_impressions_unique", "post_impressions", "post_clicks",
                 "post_reactions_by_type_total", "post_media_view", "post_total_media_view_unique"],
    "instagram_feed": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"],
    "instagram_story": ["reach", "views", "replies", "navigation"],
    "threads": ["views", "likes", "replies", "reposts", "quotes", "shares"],
}
INSIGHTS_BASE = {"facebook": GRAPH, "instagram": GRAPH, "threads": THREADS_GRAPH}

_PAGINAS_MEDIA = 3
# access_token= (query string normal), access_token%3D (la misma clave cuando toda la
# URL viaja codificada dentro de otra, p. ej. un redirect) y "access_token": "…" (un
# cuerpo JSON de error que Meta a veces hace eco de la petición). Insensible a
# mayúsculas: un ACCESS_TOKEN= en un log no debería colarse por eso.
_TOKEN_RE = re.compile(r"(access_token=)[^&\s'\"]+", re.IGNORECASE)
_TOKEN_ENC_RE = re.compile(r"(access_token%3d)[^&%\s'\"]+", re.IGNORECASE)
_TOKEN_JSON_RE = re.compile(r'("access_token"\s*:\s*")[^"]*(")', re.IGNORECASE)
_AUTH_RE = re.compile(r"Authorization: (OAuth|Bearer) \S+", re.IGNORECASE)
# Nombre completo o no: cualquier variable de entorno tipo SDB_*TOKEN* es un secreto.
_SECRETO_ENV_RE = re.compile(r"SDB_.*TOKEN", re.IGNORECASE)
_LARGO_MINIMO_SECRETO = 8


def _secretos_del_entorno() -> list[str]:
    """Valores de variables de entorno tipo SDB_*TOKEN* (SDB_PAGE_TOKEN, SDB_THREADS_TOKEN,
    o cualquier credencial futura con ese patrón). Un mensaje de error puede traer el
    token suelto, sin "access_token=" ni ninguna otra marca delante, así que redactar
    solo por patrón no basta: hay que conocer el valor y quitarlo donde aparezca. Los
    valores vacíos o de menos de _LARGO_MINIMO_SECRETO caracteres no cuentan, para que
    un valor corto de prueba (o mal configurado) no empiece a borrar texto legítimo."""
    return [v for n, v in os.environ.items()
            if v and len(v) >= _LARGO_MINIMO_SECRETO and _SECRETO_ENV_RE.search(n)]


def _redactar(texto: str) -> str:
    """Ni un access_token (en cualquiera de sus formas) ni una cabecera Authorization
    sobreviven a esto, y tampoco el valor en crudo de ningún secreto que esté en el
    entorno ahora mismo (ni su forma percent-encoded, por si viajó dentro de una URL).
    Se aplica a todo texto de error y, como red de seguridad final, al JSON completo
    antes de escribirlo o imprimirlo."""
    if not isinstance(texto, str):
        return texto
    texto = _TOKEN_RE.sub(r"\1***", texto)
    texto = _TOKEN_ENC_RE.sub(r"\1***", texto)
    texto = _TOKEN_JSON_RE.sub(r"\1***\2", texto)
    texto = _AUTH_RE.sub("***", texto)
    for valor in _secretos_del_entorno():
        if valor in texto:
            texto = texto.replace(valor, "***")
        codificado = quote(valor, safe="")
        if codificado != valor and codificado in texto:
            texto = texto.replace(codificado, "***")
    return texto


def _msg(exc: BaseException, limite: int = 500) -> str:
    return _redactar(str(exc))[:limite]


def _valor(item: dict):
    """Una métrica de insights trae su dato en values[0].value (series de tiempo,
    como post_reactions_by_type_total, cuyo valor es a su vez un dict de reacción→
    conteo) o en total_value.value (métricas agregadas de versiones recientes de la
    API de Instagram). Ninguna de las dos formas se inventa aquí: se lee la que
    Meta haya mandado."""
    if item.get("values"):
        return item["values"][0].get("value")
    if item.get("total_value") is not None:
        return item["total_value"].get("value")
    return None


def _fetch_metrics(base: str, object_id: str, token: str, metrics: list[str]) -> tuple[dict, dict]:
    """Pide todas las métricas juntas; si el grupo entero falla (basta una métrica no
    soportada por ese tipo de objeto para tirar la respuesta completa), reintenta una
    por una para no perder las que sí funcionan."""
    valores: dict[str, object] = {}
    errores: dict[str, str] = {}
    faltan = list(metrics)
    try:
        data = _get(f"{base}/{object_id}/insights",
                    {"metric": ",".join(metrics), "access_token": token}).get("data", [])
        for item in data:
            if item.get("name") in metrics:
                valores[item["name"]] = _valor(item)
        faltan = [m for m in metrics if m not in valores]
    except Exception:  # noqa: BLE001 - el grupo puede fallar por una sola métrica
        pass
    for metric in faltan:
        try:
            data = _get(f"{base}/{object_id}/insights",
                        {"metric": metric, "access_token": token}).get("data", [])
            if data:
                valores[metric] = _valor(data[0])
            else:
                errores[metric] = "sin datos"
        except Exception as exc:  # noqa: BLE001
            errores[metric] = f"{type(exc).__name__}: {_msg(exc, 300)}"
    return valores, errores


def _metricas_de(platform: str, surface: str | None) -> list[str] | None:
    """None significa: esta superficie no tiene métricas por API."""
    if platform == "facebook":
        return None if surface == "story" else METRICAS["facebook"]
    if platform == "instagram":
        return METRICAS["instagram_story"] if surface == "story" else METRICAS["instagram_feed"]
    if platform == "threads":
        return METRICAS["threads"]
    return None


def _agregar_metricas(resultado: dict, platform: str, post_id: str, token: str, surface: str | None) -> None:
    resultado["metrics_observed_at"] = datetime.now(timezone.utc).isoformat()
    metrics = _metricas_de(platform, surface)
    if metrics is None:
        resultado["metrics"] = {}
        resultado["metrics_errors"] = {"*": "not_available_via_api"}
        return
    valores, errores = _fetch_metrics(INSIGHTS_BASE[platform], post_id, token, metrics)
    resultado["metrics"] = valores
    if errores:
        resultado["metrics_errors"] = errores


def _buscar_media_por_shortcode(ig_user_id: str, shortcode: str, token: str) -> str | None:
    """El post_id de una publicación de Instagram hecha por teléfono es el shortcode
    de su permalink (p. ej. DdR54JEgxHN), no un id de Graph: hay que buscarlo en el
    feed de medios de la cuenta y casarlo por "/p/<shortcode>/".

    Solo casa publicaciones de imagen fija: el permalink de un Reel es
    "/reel/<shortcode>/", no "/p/<shortcode>/", así que hoy no se encuentra (no hay
    ruta de Reels por teléfono todavía; cuando la haya, esta función necesita casar
    también ese patrón)."""
    marca = f"/p/{shortcode}/"
    url = f"{GRAPH}/{ig_user_id}/media"
    params = {"fields": "id,permalink,timestamp", "limit": 50, "access_token": token}
    for _ in range(_PAGINAS_MEDIA):
        resp = _get(url, params)
        for item in resp.get("data", []):
            if marca in (item.get("permalink") or ""):
                return item["id"]
        siguiente = (resp.get("paging") or {}).get("next")
        if not siguiente:
            return None
        # El "next" de paging trae el access_token en la propia URL: nunca se guarda
        # ni se imprime en crudo (ni siquiera en un mensaje de error), solo se usa
        # para la siguiente petición.
        url, params = siguiente, {}
    return None


def _resolver_shortcode_instagram(shortcode: str) -> tuple[str | None, str | None, str | None]:
    """(graph_media_id, error_type, error). Los tres tipos de fallo se distinguen para
    que el informe diga qué hacer: ConfiguracionIncompleta (falta una variable de
    entorno: hay que configurarla), BusquedaFallida (la API o la red fallaron: hay que
    reintentar) o ShortcodeNoEncontrado (se buscó bien y no está: no es un fallo
    transitorio)."""
    try:
        ig_user_id = os.environ["SDB_IG_USER_ID"]
        token = os.environ["SDB_PAGE_TOKEN"]
    except KeyError as exc:
        return None, "ConfiguracionIncompleta", f"falta la variable de entorno {exc}"
    try:
        media_id = _buscar_media_por_shortcode(ig_user_id, shortcode, token)
    except Exception as exc:  # noqa: BLE001
        return None, "BusquedaFallida", f"{type(exc).__name__}: {_msg(exc, 300)}"
    if media_id is None:
        return None, "ShortcodeNoEncontrado", f"ningún medio reciente de {ig_user_id} tiene el shortcode {shortcode!r} en su permalink"
    return media_id, None, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metricas", action="store_true", help="además de comprobar el post, lee sus métricas")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    output = {
        "run_group_id": manifest["run_group_id"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "results": {},
    }

    surfaces = manifest.get("surfaces") or {}
    shortcodes = manifest.get("instagram_shortcodes") or {}
    post_ids = dict(manifest.get("post_ids") or {})
    graph_media_ids: dict[str, str] = {}

    if "instagram" in shortcodes and "instagram" not in post_ids:
        media_id, error_type, error = _resolver_shortcode_instagram(shortcodes["instagram"])
        if media_id is None:
            output["results"]["instagram"] = {
                "status": "failed", "error_type": error_type, "error": error,
            }
        else:
            post_ids["instagram"] = media_id
            graph_media_ids["instagram"] = media_id

    for platform, post_id in post_ids.items():
        if platform in output["results"]:
            continue  # instagram ya resuelto (y fallido) arriba
        try:
            base, fields, token_env = CONSULTAS[platform]
            token = os.environ[token_env]
            detail = _get(f"{base}/{post_id}", {"fields": fields, "access_token": token})
            resultado = {"status": "verified", "detail": detail}
            if platform in graph_media_ids:
                resultado["graph_media_id"] = graph_media_ids[platform]
            if args.metricas:
                _agregar_metricas(resultado, platform, post_id, token, surfaces.get(platform))
            output["results"][platform] = resultado
        except Exception as exc:  # noqa: BLE001
            output["results"][platform] = {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": _msg(exc),
            }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    texto_indentado = _redactar(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    args.output.write_text(texto_indentado)
    print(_redactar("MEDIA_LAB_VERIFY=" + json.dumps(output, ensure_ascii=False)))
    return 1 if any(v["status"] == "failed" for v in output["results"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
