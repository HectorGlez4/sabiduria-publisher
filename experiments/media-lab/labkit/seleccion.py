"""
Qué celdas salen en esta ventana.

Una celda es elegible si aún no se ha publicado, tiene un encargo aprobado y su
ruta está implementada. La segunda celda debe diferir de la primera en red o
ruta, y nunca es Facebook después de Instagram por teléfono (ni al revés):
Instagram ya copia sola esa foto en la Página.
"""
from __future__ import annotations

ESTADOS_ELEGIBLES = ("planned", "ready")
TELEFONO_FASE_1 = {("instagram", "feed_single_image")}


def _ruta_implementada(c: dict) -> bool:
    if c["publishing_route"] == "api":
        return True
    if c["publishing_route"] == "android_native":
        return (c["platform"], c["native_format"]) in TELEFONO_FASE_1
    return False


def elegibles(celdas: list[dict], todos_encargos: list[dict]) -> list[dict]:
    aprobadas = {cid for e in todos_encargos if e["estado"] == "aprobado" for cid in e["coverage_cell_ids"]}
    return [c for c in celdas
            if c["status"] in ESTADOS_ELEGIBLES and c["cell_id"] in aprobadas and _ruta_implementada(c)]


def _es_ig_telefono(c: dict) -> bool:
    return c["platform"] == "instagram" and c["publishing_route"] == "android_native"


def compatibles(a: dict, b: dict) -> bool:
    if a["platform"] == b["platform"] and a["publishing_route"] == b["publishing_route"]:
        return False
    if (_es_ig_telefono(a) and b["platform"] == "facebook") or (_es_ig_telefono(b) and a["platform"] == "facebook"):
        return False
    return True


def elegir(celdas: list[dict], todos_encargos: list[dict], max_celdas: int = 2) -> list[dict]:
    elegidas: list[dict] = []
    for c in elegibles(celdas, todos_encargos):
        if len(elegidas) == max_celdas:
            break
        if all(compatibles(c, e) for e in elegidas):
            elegidas.append(c)
    return elegidas
