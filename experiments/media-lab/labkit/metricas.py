"""
Registro de métricas de audiencia sobre runs ya publicados.

verify_api.py --metricas lee la API y deja un verification-result.json (en el repo o
bajo un `gh run download`); esto lo une al run y a la celda de coverage.json que
corresponden, deja constancia de la instantánea (24h/72h/7d/story) sin duplicarla y
escribe ambos archivos de forma atómica.

Los runs de hoy no llevan ningún campo que los relacione con el run_group_id del
manifiesto de verificación (ese id es del lote de publicación, no del run por
plataforma: "LAB-F12-001-A-API" frente a "LAB-F12-001-A-FACEBOOK"). En vez de
inventar un campo nuevo en run-template.json que tocaría todos los runs ya escritos,
--run-group es obligatorio en la CLI y aquí solo se comprueba que coincide con el
run_group_id que trae el propio resultado.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

INSTANTANEAS = ("24h", "72h", "7d", "story")


class MetricasError(ValueError):
    pass


def leer_resultado(ruta: Path) -> dict:
    if not ruta.is_file():
        raise MetricasError(f"no existe el resultado: {ruta}")
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise MetricasError(f"el resultado no es JSON válido: {ruta}") from e


def _fecha(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def registrar(run: dict, resultado: dict, *, run_group: str, instantanea: str, ahora: datetime) -> dict:
    """Devuelve una copia de `run` con la instantánea añadida a publication.snapshots.
    No muta `run`. Lanza MetricasError si el resultado es de otro run_group, si la
    instantánea ya estaba registrada o si el resultado no trae run_group_id."""
    if instantanea not in INSTANTANEAS:
        raise MetricasError(f"--instantanea debe ser una de {INSTANTANEAS}: {instantanea!r}")
    resultado_grupo = resultado.get("run_group_id")
    if not resultado_grupo:
        raise MetricasError("el resultado no trae run_group_id")
    if run_group != resultado_grupo:
        raise MetricasError(f"el resultado es de {resultado_grupo!r}, no de {run_group!r}")

    publicacion = dict(run.get("publication") or {})
    snapshots = list(publicacion.get("snapshots") or [])
    if any(s.get("instantanea") == instantanea for s in snapshots):
        raise MetricasError(f"ya hay una instantánea {instantanea!r} registrada en este run")

    observed_at = resultado.get("observed_at") or ahora.isoformat()
    submitted = publicacion.get("submitted_at") or publicacion.get("processing_completed_at")
    edad_horas = None
    if submitted:
        try:
            edad_horas = round((_fecha(observed_at) - _fecha(submitted)).total_seconds() / 3600, 2)
        except ValueError:
            edad_horas = None

    metricas: dict[str, dict] = {}
    errores: dict[str, dict] = {}
    graph_media_id = None
    for plataforma, r in (resultado.get("results") or {}).items():
        if not isinstance(r, dict):
            continue
        if r.get("status") == "verified":
            if r.get("metrics"):
                metricas[plataforma] = r["metrics"]
            if r.get("metrics_errors"):
                errores[plataforma] = r["metrics_errors"]
            if r.get("graph_media_id"):
                graph_media_id = r["graph_media_id"]
        else:
            errores[plataforma] = {"status": r.get("error") or "failed"}

    snapshots.append({
        "instantanea": instantanea,
        "observed_at": observed_at,
        "edad_horas": edad_horas,
        "metricas": metricas,
        "errores": errores,
    })
    publicacion["snapshots"] = snapshots
    if graph_media_id:
        publicacion["graph_media_id"] = graph_media_id

    nuevo = dict(run)
    nuevo["publication"] = publicacion
    return nuevo


def marcar_cobertura(coverage: dict, cell_id: str, fecha: str) -> dict:
    """Devuelve una copia de `coverage` con `fecha` añadida a measurement_completed_at
    de la celda `cell_id`, sin duplicar. No muta `coverage`. Lanza MetricasError si la
    celda no existe."""
    celdas = []
    encontrada = False
    for celda in coverage.get("cells") or []:
        c = dict(celda)
        if c.get("cell_id") == cell_id:
            encontrada = True
            completadas = list(c.get("measurement_completed_at") or [])
            if fecha not in completadas:
                completadas.append(fecha)
            c["measurement_completed_at"] = completadas
        celdas.append(c)
    if not encontrada:
        raise MetricasError(f"coverage.json no tiene la celda {cell_id!r}")
    nuevo = dict(coverage)
    nuevo["cells"] = celdas
    return nuevo


def guardar_json(ruta: Path, datos: dict) -> None:
    """Escritura atómica: un corte a mitad no deja un JSON truncado a medio escribir."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f".{ruta.name}.tmp")
    try:
        tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, ruta)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
