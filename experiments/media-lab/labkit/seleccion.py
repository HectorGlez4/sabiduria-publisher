"""
Qué celdas salen en esta ventana.

Una celda es elegible si aún no se ha publicado, tiene un encargo aprobado o ya usado en otra
de sus celdas (el estado de cada celda impide republicar) y su red y formato están
implementados para su ruta: por API, `API_FASE_1`; por teléfono, las recetas promovidas
(`TELEFONO_IMPLEMENTADO`). Sin teléfono listo no se eligen celdas de teléfono.

Reglas entre las celdas de una ventana:
- La segunda difiere de la primera en red o ruta.
- Ninguna de Facebook con una de Instagram por teléfono, en cualquier formato.
- Como máximo una `android_native`: MaaS360 bloquea a los 120 s y la segunda saldría al menos
  21 min después, casi siempre con el teléfono bloqueado.
- Ninguna de una red que la receta de la celda de teléfono copia automáticamente (`copias`).
"""
from __future__ import annotations

from labkit import recetas

ESTADOS_ELEGIBLES = ("planned", "ready")
ESTADOS_ENCARGO_UTILES = ("aprobado", "usado")
TELEFONO_IMPLEMENTADO = frozenset(recetas.RECETAS)
TELEFONO_FASE_1 = TELEFONO_IMPLEMENTADO  # alias durante la transición a la fase 2
API_FASE_1 = {("facebook", "feed_single_image"), ("facebook", "story_image"),
              ("instagram", "feed_single_image"), ("instagram", "story_image"),
              ("threads", "feed_single_image")}


def _es_telefono(c: dict) -> bool:
    return c["publishing_route"] == "android_native"


def _ruta_implementada(c: dict, borradores: bool = False) -> bool:
    clave = (c["platform"], c["native_format"])
    if c["publishing_route"] == "api":
        return clave in API_FASE_1
    if _es_telefono(c):
        return clave in TELEFONO_IMPLEMENTADO or (borradores and clave in recetas.BORRADORES)
    return False


def elegibles(celdas: list[dict], todos_encargos: list[dict], telefono_listo: bool = True) -> list[dict]:
    utiles = {cid for e in todos_encargos if e["estado"] in ESTADOS_ENCARGO_UTILES
              for cid in e["coverage_cell_ids"]}
    return [c for c in celdas
            if c["status"] in ESTADOS_ELEGIBLES and c["cell_id"] in utiles and _ruta_implementada(c)
            and (telefono_listo or not _es_telefono(c))]


def _es_ig_telefono(c: dict) -> bool:
    return c["platform"] == "instagram" and _es_telefono(c)


def _redes_copiadas(c: dict) -> set[str]:
    """Redes que la receta de una celda de teléfono copia sola. Una receta sin `copias` falla
    visible (KeyError) en vez de quitar la exclusión en silencio."""
    if not _es_telefono(c):
        return set()
    receta = recetas.TODAS.get((c["platform"], c["native_format"]))
    return set() if receta is None else {copia["red"] for copia in receta["copias"]}


def compatibles(a: dict, b: dict) -> bool:
    if a["platform"] == b["platform"] and a["publishing_route"] == b["publishing_route"]:
        return False
    if (_es_ig_telefono(a) and b["platform"] == "facebook") or (_es_ig_telefono(b) and a["platform"] == "facebook"):
        return False
    if _es_telefono(a) and _es_telefono(b):
        return False
    if b["platform"] in _redes_copiadas(a) or a["platform"] in _redes_copiadas(b):
        return False
    return True


def elegir(celdas: list[dict], todos_encargos: list[dict], max_celdas: int = 2,
           telefono_listo: bool = True) -> list[dict]:
    elegidas: list[dict] = []
    for c in elegibles(celdas, todos_encargos, telefono_listo):
        if len(elegidas) >= max_celdas:
            break
        if all(compatibles(c, e) for e in elegidas):
            elegidas.append(c)
    return elegidas
