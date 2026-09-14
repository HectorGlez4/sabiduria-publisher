"""
Qué celdas salen en esta ventana.

Una celda es elegible si aún no se ha publicado, tiene un encargo aprobado o ya
usado en otra de sus celdas (el estado de cada celda impide republicar) y su red
y formato están implementados para su ruta. Sin teléfono listo no se eligen
celdas de teléfono, para no gastar la ventana en una que no puede salir.

La segunda celda debe diferir de la primera en red o ruta. Tampoco sale ninguna
celda de Facebook en la misma ventana que una foto de Instagram por teléfono (ni
al revés): Instagram ya copia sola esa foto en la Página, y la spec extiende la
regla a cualquier formato de Facebook para no sumar carga en esa ventana.
"""
from __future__ import annotations

ESTADOS_ELEGIBLES = ("planned", "ready")
ESTADOS_ENCARGO_UTILES = ("aprobado", "usado")
TELEFONO_FASE_1 = {("instagram", "feed_single_image")}
API_FASE_1 = {("facebook", "feed_single_image"), ("facebook", "story_image"),
              ("instagram", "feed_single_image"), ("instagram", "story_image"),
              ("threads", "feed_single_image")}


def _ruta_implementada(c: dict) -> bool:
    clave = (c["platform"], c["native_format"])
    if c["publishing_route"] == "api":
        return clave in API_FASE_1
    if c["publishing_route"] == "android_native":
        return clave in TELEFONO_FASE_1
    return False


def elegibles(celdas: list[dict], todos_encargos: list[dict], telefono_listo: bool = True) -> list[dict]:
    utiles = {cid for e in todos_encargos if e["estado"] in ESTADOS_ENCARGO_UTILES
              for cid in e["coverage_cell_ids"]}
    return [c for c in celdas
            if c["status"] in ESTADOS_ELEGIBLES and c["cell_id"] in utiles and _ruta_implementada(c)
            and (telefono_listo or c["publishing_route"] != "android_native")]


def _es_ig_telefono(c: dict) -> bool:
    return c["platform"] == "instagram" and c["publishing_route"] == "android_native"


def compatibles(a: dict, b: dict) -> bool:
    if a["platform"] == b["platform"] and a["publishing_route"] == b["publishing_route"]:
        return False
    if (_es_ig_telefono(a) and b["platform"] == "facebook") or (_es_ig_telefono(b) and a["platform"] == "facebook"):
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
