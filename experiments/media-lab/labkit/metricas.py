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
# run_id no lleva la plataforma en un campo aparte en runs antiguos: se deduce del
# sufijo. Los de Story primero, porque un run_id que acaba en "-FACEBOOK-STORY"
# también acabaría "pareciendo" terminar en algo si se mirara mal el orden.
_SUFIJOS_PLATAFORMA = (
    ("-FACEBOOK-STORY", "facebook"), ("-INSTAGRAM-STORY", "instagram"),
    ("-FACEBOOK", "facebook"), ("-INSTAGRAM", "instagram"), ("-THREADS", "threads"),
)


class MetricasError(ValueError):
    pass


def leer_resultado(ruta: Path) -> dict:
    if not ruta.is_file():
        raise MetricasError(f"no existe el resultado: {ruta}")
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise MetricasError(f"el resultado no es JSON válido: {ruta}") from e


def plataforma_de_run(run: dict) -> str:
    """facebook/instagram/threads, el nombre que usa `results` en un verification-result.json.
    Los runs de hoy ya traen "platform" (ver run-template.json); por si acaso, cae al
    sufijo del run_id ("...-FACEBOOK-STORY" también es facebook: es la misma red, otra
    superficie, no otra entrada en `results`)."""
    plataforma = run.get("platform")
    if plataforma in ("facebook", "instagram", "threads"):
        return plataforma
    run_id = str(run.get("run_id") or "").upper()
    for sufijo, nombre in _SUFIJOS_PLATAFORMA:
        if run_id.endswith(sufijo):
            return nombre
    raise MetricasError(f"no se pudo deducir la plataforma del run: {run.get('run_id')!r}")


def _fecha(texto: str) -> datetime:
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except (ValueError, TypeError) as e:
        raise MetricasError(f"fecha ilegible: {texto!r}") from e


def registrar(run: dict, resultado: dict, *, run_group: str, instantanea: str, ahora: datetime) -> dict:
    """Devuelve una copia de `run` con la instantánea añadida a publication.snapshots.
    No muta `run` ni escribe nada: quien llama decide cuándo (y si) guardar, para poder
    calcular también el coverage.json antes de tocar ningún archivo.

    Lanza MetricasError (código 2 en la CLI, sin escribir nada) si: el resultado es de
    otro run_group; la instantánea ya estaba registrada; el resultado no trae la
    plataforma de este run, o esa plataforma no quedó "verified"; el run no tiene
    publication.post_id; o el post_id del run no corresponde al resultado (ni como id
    de Graph -ruta API- ni como shortcode dentro del permalink -ruta teléfono-)."""
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

    plataforma = plataforma_de_run(run)
    r = (resultado.get("results") or {}).get(plataforma)
    if not isinstance(r, dict):
        raise MetricasError(f"el resultado no trae la plataforma {plataforma!r} de este run")
    if r.get("status") != "verified":
        raise MetricasError(
            f"{plataforma} no está verificado en el resultado (status={r.get('status')!r}): {r.get('error') or ''}")

    post_id = publicacion.get("post_id")
    if not post_id:
        # Sin post_id no hay con qué cotejar que el resultado es realmente el de este
        # run: sin este cotejo, un manifiesto con el post_id equivocado (o el de otra
        # celda) registraría métricas ajenas como si fueran las de este run.
        raise MetricasError(f"el run no tiene publication.post_id: no se puede cotejar con el resultado de {plataforma!r}")
    detail = r.get("detail") or {}
    permalink = detail.get("permalink") or detail.get("permalink_url") or ""
    # Ruta API: post_id es el id de Graph y debe coincidir tal cual. Ruta teléfono
    # (verify_api.py buscó por shortcode): post_id ES el shortcode, así que se
    # comprueba contra el permalink, no contra el id de Graph que devolvió la búsqueda.
    if str(detail.get("id")) != str(post_id) and f"/p/{post_id}/" not in permalink:
        raise MetricasError(
            f"el resultado de {plataforma} no corresponde a este run: post_id={post_id!r}, "
            f"detail.id={detail.get('id')!r}, permalink={permalink!r}")

    observed_at = resultado.get("observed_at") or ahora.isoformat()
    submitted = publicacion.get("submitted_at") or publicacion.get("processing_completed_at")
    edad_horas = None
    if submitted:
        try:
            edad_horas = round((_fecha(observed_at) - _fecha(submitted)).total_seconds() / 3600, 2)
        except (ValueError, TypeError) as e:
            # p. ej. submitted_at sin zona horaria: no se puede restar con observed_at
            # (que sí la lleva). Código 2 limpio, no un TypeError sin capturar.
            raise MetricasError(
                f"no se pudo calcular la edad de la instantánea: submitted_at={submitted!r}, "
                f"observed_at={observed_at!r}") from e

    metricas_val = r.get("metrics") or {}
    errores_val = r.get("metrics_errors") or {}
    graph_media_id = r.get("graph_media_id")

    snapshots.append({
        "instantanea": instantanea,
        "observed_at": observed_at,
        "edad_horas": edad_horas,
        "metricas": {plataforma: metricas_val} if metricas_val else {},
        "errores": {plataforma: errores_val} if errores_val else {},
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
