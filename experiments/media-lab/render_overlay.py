#!/usr/bin/env python3
"""Deterministic text overlay for media-lab single-image masters."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FONT_BOLD = ROOT / "assets/fonts/Poppins-Medium.ttf"
FONT_SERIF = ROOT / "assets/fonts/Lora-Variable.ttf"

MARCA = "SABIDURÍA DE BOLSILLO"

# ── Story 9:16: zona segura ─────────────────────────────────────────────────
# El visor de Stories tapa arriba la barra de progreso, el avatar, el nombre de la cuenta y el
# botón de cerrar, y abajo la barra de respuesta y los iconos de corazón y compartir. Todo el
# overlay (panel, titular, subtítulo, aviso y marca) queda dentro de ZONA_SEGURA_HISTORIA; si
# no cabe, render() falla con FueraDeZonaSegura y no dibuja nada.
HISTORIA = (1080, 1920)
HISTORIA_LIBRE_ARRIBA = 250
HISTORIA_LIBRE_ABAJO = 260
HISTORIA_MARGEN_LATERAL = 50
ZONA_SEGURA_HISTORIA = (
    HISTORIA_MARGEN_LATERAL,
    HISTORIA_LIBRE_ARRIBA,
    HISTORIA[0] - HISTORIA_MARGEN_LATERAL,
    HISTORIA[1] - HISTORIA_LIBRE_ABAJO,
)  # (50, 250, 1030, 1660)

HISTORIA_PANEL = (54, HISTORIA_LIBRE_ARRIBA, 1026, HISTORIA_LIBRE_ARRIBA + 430)  # (54, 250, 1026, 680)
HISTORIA_TITULAR_Y = HISTORIA_PANEL[1] + 50  # 300: origen de la 1.ª línea
HISTORIA_TITULAR_PASO = 86
HISTORIA_TITULAR_ANCHO = 876
HISTORIA_TITULAR_TAMANOS = (72, 46)  # máximo y mínimo legible
HISTORIA_SUBTITULO_Y = HISTORIA_PANEL[1] + 330  # 580
HISTORIA_SUBTITULO_TAMANOS = (42, 34)  # máximo y mínimo legible
HISTORIA_SUBTITULO_ANCHO = 876

PILDORA_ALTO = 53
PILDORA_PAD = 18
PILDORA_RADIO = 14
PILDORA_SEPARACION = 16  # hueco mínimo entre aviso y marca en la misma fila
PILDORA_INTERLINEA = 12  # hueco vertical si el aviso sube a la fila de encima
MARCA_TAMANO = 23
AVISO_TAMANO = 20
HISTORIA_PILDORA_ABAJO = ZONA_SEGURA_HISTORIA[3]  # borde inferior de la fila de píldoras: 1660


class FueraDeZonaSegura(ValueError):
    """El overlay de la Story no cabe en la zona segura o sus elementos se solapan."""


Caja = tuple[int, int, int, int]


@dataclass(frozen=True)
class Elemento:
    """Una pieza del overlay de la Story.

    `caja` es lo que ocupa en el máster: el rectángulo del panel o de la píldora, o la tinta del
    texto. `origen` y `fuente` dicen dónde y con qué se escribe `texto`; `tinta` es la caja del
    texto de una píldora (en los textos sueltos coincide con `caja`)."""

    nombre: str
    tipo: str  # "panel", "texto" o "pildora"
    caja: Caja
    texto: str = ""
    origen: tuple[int, int] = (0, 0)
    fuente: ImageFont.FreeTypeFont | None = None
    tinta: Caja | None = None


def fit_font(draw: ImageDraw.ImageDraw, text: str, width: int, max_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(str(FONT_BOLD), size)
        if draw.textbbox((0, 0), text, font=font)[2] <= width:
            return font
    return ImageFont.truetype(str(FONT_BOLD), min_size)


def parse_rgb(value: str) -> tuple[int, int, int]:
    parts = tuple(int(part) for part in value.split(","))
    if len(parts) != 3 or any(part < 0 or part > 255 for part in parts):
        raise argparse.ArgumentTypeError("color must be R,G,B with values from 0 to 255")
    return parts


def _dentro(interior: Caja, exterior: Caja) -> bool:
    return (exterior[0] <= interior[0] and exterior[1] <= interior[1]
            and interior[2] <= exterior[2] and interior[3] <= exterior[3])


def _solapan(a: Caja, b: Caja) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _medidor() -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(Image.new("RGBA", (1, 1)))


def disposicion_story(lines: list[str], sub: str, disclosure: str) -> list[Elemento]:
    """Dónde va cada pieza del overlay de la Story (1080×1920). Pura: solo mide texto, no
    comprueba nada (eso es comprobar_story)."""
    draw = _medidor()
    elementos = [Elemento("panel", "panel", HISTORIA_PANEL)]

    y = HISTORIA_TITULAR_Y
    for i, line in enumerate(lines, start=1):
        font = fit_font(draw, line, HISTORIA_TITULAR_ANCHO, *HISTORIA_TITULAR_TAMANOS)
        box = draw.textbbox((0, 0), line, font=font)
        x = (HISTORIA[0] - (box[2] - box[0])) // 2
        tinta = draw.textbbox((x, y), line, font=font)
        elementos.append(Elemento(f"titular_{i}", "texto", tinta, line, (x, y), font, tinta))
        y += HISTORIA_TITULAR_PASO

    sub_max, sub_min = HISTORIA_SUBTITULO_TAMANOS
    for size in range(sub_max, sub_min - 1, -2):
        sub_font = ImageFont.truetype(str(FONT_SERIF), size)
        sub_box = draw.textbbox((0, 0), sub, font=sub_font)
        if sub_box[2] - sub_box[0] <= HISTORIA_SUBTITULO_ANCHO:
            break
    sub_x = (HISTORIA[0] - (sub_box[2] - sub_box[0])) // 2
    sub_tinta = draw.textbbox((sub_x, HISTORIA_SUBTITULO_Y), sub, font=sub_font)
    elementos.append(Elemento("subtitulo", "texto", sub_tinta, sub, (sub_x, HISTORIA_SUBTITULO_Y), sub_font, sub_tinta))

    fila_top = HISTORIA_PILDORA_ABAJO - PILDORA_ALTO
    brand_font = ImageFont.truetype(str(FONT_BOLD), MARCA_TAMANO)
    brand_box = draw.textbbox((0, 0), MARCA, font=brand_font)
    derecha = ZONA_SEGURA_HISTORIA[2]
    bx = derecha - (brand_box[2] - brand_box[0]) - 2 * PILDORA_PAD
    marca = (bx, fila_top, derecha, fila_top + PILDORA_ALTO)
    marca_origen = (bx + PILDORA_PAD, fila_top + 10)
    elementos.append(Elemento("marca", "pildora", marca, MARCA, marca_origen, brand_font,
                              draw.textbbox(marca_origen, MARCA, font=brand_font)))

    if disclosure:
        aviso_font = ImageFont.truetype(str(FONT_BOLD), AVISO_TAMANO)
        aviso_box = draw.textbbox((0, 0), disclosure, font=aviso_font)
        izquierda = ZONA_SEGURA_HISTORIA[0]
        aviso_derecha = izquierda + (aviso_box[2] - aviso_box[0]) + 2 * PILDORA_PAD
        aviso_top = fila_top
        if aviso_derecha + PILDORA_SEPARACION > bx:
            # No cabe al lado de la marca: sube a la fila de encima, alineado a la izquierda.
            aviso_top = fila_top - PILDORA_INTERLINEA - PILDORA_ALTO
        aviso = (izquierda, aviso_top, aviso_derecha, aviso_top + PILDORA_ALTO)
        aviso_origen = (izquierda + PILDORA_PAD, aviso_top + 12)
        elementos.append(Elemento("aviso", "pildora", aviso, disclosure, aviso_origen, aviso_font,
                                  draw.textbbox(aviso_origen, disclosure, font=aviso_font)))
    return elementos


def comprobar_story(elementos: list[Elemento]) -> None:
    """Lanza FueraDeZonaSegura si algo sale de la zona segura, del panel o de su píldora, o si
    dos piezas se solapan (el panel solo puede contener titular y subtítulo)."""
    x1, y1, x2, y2 = ZONA_SEGURA_HISTORIA
    zona = f"zona segura de Story x {x1}–{x2}, y {y1}–{y2}"
    panel = next(e for e in elementos if e.tipo == "panel")
    for e in elementos:
        if not _dentro(e.caja, ZONA_SEGURA_HISTORIA):
            raise FueraDeZonaSegura(f"{e.nombre} {e.caja} sale de la {zona}: {e.texto!r}")
        if e.tipo == "texto" and not _dentro(e.caja, panel.caja):
            raise FueraDeZonaSegura(f"{e.nombre} {e.caja} no cabe en el panel {panel.caja}: {e.texto!r}")
        if e.tipo == "pildora" and not _dentro(e.tinta, e.caja):
            raise FueraDeZonaSegura(f"el texto de {e.nombre} {e.tinta} no cabe en su píldora {e.caja}")
    piezas = [e for e in elementos if e.tipo != "panel"]
    for i, a in enumerate(piezas):
        if a.tipo == "pildora" and _solapan(a.caja, panel.caja):
            raise FueraDeZonaSegura(f"{a.nombre} {a.caja} se solapa con el panel {panel.caja}")
        for b in piezas[i + 1:]:
            if _solapan(a.caja, b.caja):
                raise FueraDeZonaSegura(f"{a.nombre} {a.caja} se solapa con {b.nombre} {b.caja}")


def cajas_story(lines: list[str], sub: str, disclosure: str) -> dict[str, Caja]:
    """{nombre: (x1, y1, x2, y2)} de cada pieza del overlay de la Story, ya comprobadas."""
    elementos = disposicion_story(lines, sub, disclosure)
    comprobar_story(elementos)
    return {e.nombre: e.caja for e in elementos}


def _pixeles(caja: Caja) -> Caja:
    """Las cajas son semiabiertas (x2 e y2 no se pintan, como en textbbox); rounded_rectangle de
    Pillow incluye x2 e y2, así que se le pasa la última fila y columna que sí se pintan."""
    return caja[0], caja[1], caja[2] - 1, caja[3] - 1


def _dibujar_story(draw: ImageDraw.ImageDraw, elementos: list[Elemento], panel_rgb, accent_rgb) -> None:
    for e in elementos:
        if e.tipo == "panel":
            draw.rounded_rectangle(_pixeles(e.caja), radius=24, fill=(*panel_rgb, 224))
        elif e.tipo == "pildora":
            draw.rounded_rectangle(_pixeles(e.caja), radius=PILDORA_RADIO, fill=(*panel_rgb, 216))
            draw.text(e.origen, e.texto, font=e.fuente, fill=(249, 240, 211, 255))
        elif e.nombre == "subtitulo":
            draw.text(e.origen, e.texto, font=e.fuente, fill=(*accent_rgb, 255))
        else:
            draw.text(e.origen, e.texto, font=e.fuente, fill=(249, 240, 211, 255))


def _dibujar_feed(draw: ImageDraw.ImageDraw, lines: list[str], sub: str, panel_rgb, accent_rgb, disclosure: str) -> None:
    """Feed 4:5 (1080×1350): sin cambios desde antes de la zona segura de Story."""
    draw.rounded_rectangle((54, 76, 1026, 405), radius=24, fill=(*panel_rgb, 224))

    y = 108
    for line in lines:
        font = fit_font(draw, line, 876, 66, 46)
        box = draw.textbbox((0, 0), line, font=font)
        x = (1080 - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=font, fill=(249, 240, 211, 255))
        y += 78

    sub_font = ImageFont.truetype(str(FONT_SERIF), 38)
    sub_box = draw.textbbox((0, 0), sub, font=sub_font)
    sub_y = 340
    draw.text(((1080 - (sub_box[2] - sub_box[0])) // 2, sub_y), sub, font=sub_font, fill=(*accent_rgb, 255))

    brand_font = ImageFont.truetype(str(FONT_BOLD), 23)
    brand_box = draw.textbbox((0, 0), MARCA, font=brand_font)
    pad = 18
    bx = 1030 - (brand_box[2] - brand_box[0]) - 2 * pad
    brand_top = 1268
    draw.rounded_rectangle((bx, brand_top, 1030, brand_top + 53), radius=14, fill=(*panel_rgb, 216))
    draw.text((bx + pad, brand_top + 10), MARCA, font=brand_font, fill=(249, 240, 211, 255))

    if disclosure:
        disclosure_font = ImageFont.truetype(str(FONT_BOLD), 20)
        disclosure_box = draw.textbbox((0, 0), disclosure, font=disclosure_font)
        disclosure_width = disclosure_box[2] - disclosure_box[0]
        disclosure_top = brand_top
        draw.rounded_rectangle(
            (50, disclosure_top, 50 + disclosure_width + 2 * pad, disclosure_top + 53),
            radius=14,
            fill=(*panel_rgb, 216),
        )
        draw.text(
            (50 + pad, disclosure_top + 12),
            disclosure,
            font=disclosure_font,
            fill=(249, 240, 211, 255),
        )


def render(
    source: Path,
    destination: Path,
    lines: list[str],
    sub: str,
    panel_rgb: tuple[int, int, int],
    accent_rgb: tuple[int, int, int],
    output_format: str,
    disclosure: str,
) -> None:
    is_story = output_format == "story"
    elementos = None
    if is_story:
        # Antes de abrir nada: si el overlay no cabe en la zona segura, no se dibuja.
        elementos = disposicion_story(lines, sub, disclosure)
        comprobar_story(elementos)

    image = Image.open(source).convert("RGB")
    target_size = HISTORIA if is_story else (1080, 1350)
    target_ratio = target_size[0] / target_size[1]
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        crop_width = round(image.height * target_ratio)
        left = (image.width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, image.height))
    elif source_ratio < target_ratio:
        crop_height = round(image.width / target_ratio)
        top = (image.height - crop_height) // 2
        image = image.crop((0, top, image.width, top + crop_height))
    image = image.resize(target_size, Image.Resampling.LANCZOS)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if is_story:
        _dibujar_story(draw, elementos, panel_rgb, accent_rgb)
    else:
        _dibujar_feed(draw, lines, sub, panel_rgb, accent_rgb, disclosure)

    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "JPEG", quality=94, optimize=True, progressive=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--headline",
        default="EL PRIMER LIBRO ILUSTRADO|CON FOTOGRAFÍAS|ERA AZUL",
        help="Three lines separated by |",
    )
    parser.add_argument("--subhead", default="Anna Atkins · 1843")
    parser.add_argument("--panel-rgb", type=parse_rgb, default=(5, 39, 73))
    parser.add_argument("--accent-rgb", type=parse_rgb, default=(176, 220, 236))
    parser.add_argument("--format", choices=("feed", "story"), default="feed")
    parser.add_argument("--disclosure", default="")
    args = parser.parse_args()
    lines = args.headline.split("|")
    if len(lines) != 3:
        parser.error("--headline must contain exactly three lines separated by |")
    render(
        args.source,
        args.destination,
        lines,
        args.subhead,
        args.panel_rgb,
        args.accent_rgb,
        args.format,
        args.disclosure,
    )


if __name__ == "__main__":
    main()
