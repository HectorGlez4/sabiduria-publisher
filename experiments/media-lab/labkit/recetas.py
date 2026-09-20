"""
Registro único de flujos del teléfono.

`TODAS` guarda cada receta escrita. Un par (red, native_format) solo cuenta como implementado
cuando está en `PROMOVIDAS`, con el run de su primera publicación `confirmado` en una ventana
manual. `RECETAS` son las promovidas (de ahí sale `seleccion.TELEFONO_IMPLEMENTADO`) y
`BORRADORES` las demás, que solo aceptan `lab.py encargo-nuevo --borrador` y
`lab.py receta --borrador` (tarea 5) para esa ventana manual.

Cada receta dice a la ventana, en orden, qué comandos de `lab.py` ejecutar en cada fase
(`preparar` hasta la captura de QA, `publicar` y `verificar`), qué valores anota cada uno para
los siguientes (`<valor>` en `args`), qué debe verse en su captura, qué estados salen con 0,
cómo se concilia un 5 y qué copias automáticas produce (`copias`, que también excluyen esa red
en la misma ventana).
"""
from __future__ import annotations

import copy

LAB = ".venv/bin/python experiments/media-lab/lab.py"
CLAVES = ("subcomando", "superficie", "formato_encargo", "preparar", "publicar", "verificar",
          "estados_ok", "conciliacion", "copias", "verificacion", "nota")
FASES = ("preparar", "publicar", "verificar")


class RecetaNoDisponible(ValueError):
    pass


def _cmd(*args: str, ver: str, anota: tuple[str, ...] = ()) -> dict:
    return {"args": list(args), "ver": ver, "anota": list(anota)}


FEED_INSTAGRAM = {
    "subcomando": "ig",
    "superficie": "feed",
    "formato_encargo": {"ancho": 1080, "alto": 1350},
    "preparar": [
        _cmd("telefono-subir", "--local", "<master>", ver="JSON con sha256 y subido_en; no hay captura",
             anota=("subido_en",)),
        _cmd("ig", "abrir", "--run", "<run>", "--subido-en", "<subido_en>",
             ver="ig-01-selector.png: «Nouvelle publication» con la foto subida marcada",
             anota=("publicaciones_antes",)),
        _cmd("ig", "recorte", "--run", "<run>", ver="ig-02-recorte.png: la imagen completa en 4:5 (el volcado no lo muestra)"),
        _cmd("ig", "editor", "--run", "<run>", ver="ig-02b-editor.png: editor con la imagen y el chip «Audio suggéré»"),
        _cmd("ig", "audio", "--run", "<run>", ver="ig-03-audio.png: chip de música añadido", anota=("tema",)),
        _cmd("ig", "detalles", "--run", "<run>", "--tema", "<tema>",
             ver="ig-03b-detalles.png: detalles con la fila de música «<tema>»; aquí se confirma, "
                 "porque después el pie la desplaza fuera del volcado"),
        _cmd("ig", "pie", "--run", "<run>", "--pie", "<pie>",
             ver="ig-04-compositor.png: pie y «Partager» sin teclado ni desplegable (captura de la QA); "
                 "la fila de música puede quedar fuera de pantalla con un pie largo"),
    ],
    "publicar": [
        _cmd("ig", "compartir", "--run", "<run>", "--pie", "<pie>", "--tema", "<tema>",
             "--publicaciones-antes", "<publicaciones_antes>", "[--produccion-cercana]",
             ver="ig-05-publicado.png: perfil de @sabiduriabolsillo tras compartir; "
                 "--produccion-cercana si el último preflight trajo espera; "
                 "--publicaciones-antes none si ig abrir lo dio null"),
    ],
    "verificar": [
        _cmd("telefono-captura", "--run", "<run>", "--nombre", "ig-06-perfil",
             ver="ig-06-perfil.png: la publicación nueva arriba en la cuadrícula del perfil; "
                 "si no muestra el perfil, no navegues a ciegas: anótalo y usa ig-05-publicado"),
    ],
    "estados_ok": ["confirmado"],
    "conciliacion": ("Con 5 no repitas nada: mira captura y captura_antes, captura el perfil con telefono-captura y "
                     "compara la primera publicación con el máster y el pie antes de registrar; nunca por la otra ruta."),
    "copias": [{"red": "facebook", "superficie": "feed",
                "nota": "Instagram comparte la foto en la Página: va en publication.cross_posting del run"}],
    "verificacion": ("Identidad, imagen, pie y música en la captura del perfil. La URL no se lee en el teléfono: "
                     "por `manifiesto-verificacion --instagram-shortcode` si se conoce el shortcode; "
                     "si no, en `missing_data_reasons.post_url`."),
    "nota": "",
}

TODAS: dict[tuple[str, str], dict] = {
    ("instagram", "feed_single_image"): FEED_INSTAGRAM,
}
PROMOVIDAS: dict[tuple[str, str], str] = {
    ("instagram", "feed_single_image"): "CELL-018: primera ventana manual confirmada (2026-09-14)",
}
_faltan = set(PROMOVIDAS) - set(TODAS)
if _faltan:
    raise RuntimeError(f"PROMOVIDAS sin receta en TODAS: {sorted(_faltan)}")
RECETAS = {par: TODAS[par] for par in PROMOVIDAS}
BORRADORES = {par: receta for par, receta in TODAS.items() if par not in PROMOVIDAS}


def para(red: str, formato: str, borrador: bool = False) -> dict:
    """La promovida si existe; el borrador solo con `borrador=True`; si no, `RecetaNoDisponible`,
    con pista cuando hay borrador y no se pidió.

    Devuelve el objeto del propio registro: es de solo lectura (para una copia, `renderizar`)."""
    par = (red, formato)
    if par in RECETAS:
        return RECETAS[par]
    if borrador and par in BORRADORES:
        return BORRADORES[par]
    pista = "" if borrador or par not in BORRADORES else " (hay borrador: --borrador solo en ventana manual)"
    raise RecetaNoDisponible(f"{red}/{formato} no está implementado por teléfono{pista}")


def renderizar(receta: dict) -> dict:
    """Copia profunda de la receta con cada comando también como línea lista para ejecutar;
    mutarla no cambia el registro."""
    fuera = {k: copy.deepcopy(v) for k, v in receta.items() if k not in FASES}
    for fase in FASES:
        fuera[fase] = [{**copy.deepcopy(c), "linea": " ".join([LAB, *c["args"]])} for c in receta[fase]]
    return fuera
