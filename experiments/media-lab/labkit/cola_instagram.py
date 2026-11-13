"""Piezas de la cola del publicador que Instagram saca desde el móvil, con música.

El publicador de la nube (src/publish.py, `POR_TELEFONO`) publica Facebook y Threads a su hora y deja en
Instagram la marca `{"via": "telefono", "pendiente": true}`. Cada ciclo del bucle «sitio → Instagram» mira
aquí primero: si hay una pieza pendiente, sale ella en vez de una cita al azar del sitio. Decisión del
usuario del 2026-11-13: solo Instagram desde el móvil, se espera al móvil (nunca sin música) y cada pieza
del feed sale también como Reel.
"""
from __future__ import annotations

from pathlib import Path

# superficie del bucle → clave de `results` en la pieza publicada
CLAVE = {"feed": "instagram", "reel": "instagram_reel", "story": "instagram_story"}
# Un ciclo que elige la pieza cuenta como intento. Tras tantos, lo que falte se abandona: una pieza que
# Instagram rechaza siempre no puede quedarse delante de las demás para siempre.
MAX_INTENTOS = 3


def _marca(unit: dict, clave: str) -> dict:
    return (unit.get("results") or {}).get(clave) or {}


def superficies_pendientes(unit: dict) -> list[str]:
    """Lo que falta por publicar desde el móvil, en el orden del bucle (el Reel primero: es el que llega)."""
    quiere = []
    if _marca(unit, "instagram").get("via") == "telefono":
        quiere += ["reel", "feed"]
    if _marca(unit, "instagram_story").get("via") == "telefono":
        quiere += ["story"]
    return [s for s in quiere
            if not _marca(unit, CLAVE[s]).get("published_at") and not _marca(unit, CLAVE[s]).get("abandonada")]


def _desde(unit: dict) -> str:
    """Desde cuándo espera la pieza: la marca más antigua que dejó el publicador."""
    marcas = [_marca(unit, c).get("encolada_en") for c in ("instagram", "instagram_story")]
    return min([m for m in marcas if m] or [unit.get("publish_at") or ""])


def elegir_pieza(piezas: list[tuple[Path, dict]]) -> tuple[Path, dict, list[str]] | None:
    """La pieza que lleva más tiempo esperando al móvil, con sus superficies pendientes, o None."""
    candidatas = []
    for ruta, unit in piezas:
        pendientes = superficies_pendientes(unit)
        if pendientes:
            candidatas.append((_desde(unit), ruta.name, ruta, unit, pendientes))
    if not candidatas:
        return None
    _, _, ruta, unit, pendientes = min(candidatas, key=lambda c: (c[0], c[1]))
    return ruta, unit, pendientes


def contar_intento(unit: dict, ahora: str) -> list[str]:
    """Suma un intento. Al pasar de MAX_INTENTOS abandona lo que falte y devuelve [] (nada que hacer)."""
    intentos = int(unit.get("intentos_telefono") or 0) + 1
    unit["intentos_telefono"] = intentos
    pendientes = superficies_pendientes(unit)
    if intentos <= MAX_INTENTOS:
        return pendientes
    for s in pendientes:
        marca = unit.setdefault("results", {}).setdefault(CLAVE[s], {"via": "telefono"})
        marca.update({"abandonada": ahora, "motivo": f"sin publicar tras {MAX_INTENTOS} ciclos del móvil"})
        marca.pop("pendiente", None)
    return []


def anotar_publicada(unit: dict, superficie: str, pista: str, publicado_en: str, run: str) -> None:
    """Sustituye la marca de pendiente por lo que salió. Lo demás de la marca (encolada_en) se conserva."""
    marca = unit.setdefault("results", {}).setdefault(CLAVE[superficie], {"via": "telefono"})
    marca.pop("pendiente", None)
    marca.update({"via": "telefono", "published_at": publicado_en, "pista": pista, "run": run})


# Zona libre de cada editor en un lienzo 1080×1920 (la misma que respeta el sitio, historias-y-reels-desde-el-sitio.md):
# el Reel tapa por debajo de y≈1500 con Audio/Texte; la Story, la columna de herramientas desde x≈917 y la barra de
# respuesta por debajo de y≈1660 (zona-segura-de-stories).
CAJA_SEGURA = {"reel": (36, 240, 1044, 1500), "story": (48, 250, 880, 1660)}
LIENZO_VERTICAL = (1080, 1920)


def vertical_seguro(tarjeta: Path, superficie: str, salida: Path) -> Path:
    """La tarjeta 4:5 del feed, entera, dentro de la zona libre del editor de `superficie`, sobre un fondo que
    sigue el degradado de su borde (arriba el color de su esquina de arriba, abajo el de la de abajo). Así nada
    de la tarjeta queda bajo los botones de Instagram y no se ve dónde acaba."""
    from PIL import Image
    x0, y0, x1, y1 = CAJA_SEGURA[superficie]
    ancho, alto = LIENZO_VERTICAL
    with Image.open(tarjeta) as im:
        im = im.convert("RGB")
        escala = min((x1 - x0) / im.width, (y1 - y0) / im.height)
        chica = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
    px, py = x0 + (x1 - x0 - chica.width) // 2, y0 + (y1 - y0 - chica.height) // 2
    arriba, abajo = chica.getpixel((1, 1)), chica.getpixel((1, chica.height - 2))
    columna = Image.new("RGB", (1, alto))
    for y in range(alto):
        t = min(max((y - py) / max(chica.height - 1, 1), 0.0), 1.0)
        columna.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo)))
    lienzo = columna.resize((ancho, alto))
    lienzo.paste(chica, (px, py))
    salida.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(salida)
    return salida
