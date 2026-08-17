#!/usr/bin/env python3
"""
Sabiduria De Bolsillo - generador de tarjetas de cita (1080x1350, formato feed FB/IG).

Uso:
  python3 quote_card.py --quote "Texto de la cita" --author "Nombre (1900-1980)" \
      --out /ruta/salida.png [--variant cream|gold] [--kicker "SABIDURIA DE BOLSILLO"]

La ruta de --out debe ser /mnt/user-data/outputs/AAAA-MM-DD-franja.png
(franja: manana, tarde o noche).

Identidad visual de la pagina:
  - Dorado calido + crema, tipografia serif (Lora), acentos sans (Poppins) en versalitas.
  - Marco fino, mucho aire, cita centrada, autor discreto, firma de marca abajo.
"""
import argparse
import os
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

# ---- Paleta de marca -------------------------------------------------------
GOLD_DARK = (150, 114, 45)
GOLD = (191, 155, 78)
GOLD_LIGHT = (214, 183, 116)
CREAM = (247, 241, 228)
CREAM_DEEP = (238, 228, 208)
INK = (44, 38, 28)

# Las fuentes van empaquetadas en assets/fonts/ para que la tarjeta sea
# identica en cualquier maquina. Ver src/render/fonts.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fonts import LORA, LORA_IT, POPPINS, POPPINS_LIGHT  # noqa: E402

W, H = 1080, 1350


def vertical_gradient(size, top, bottom):
    w, h = size
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h), Image.BILINEAR)


def track_text(draw, xy, text, font, fill, tracking=0, anchor_center_x=None):
    """Dibuja texto con letter-spacing. Si anchor_center_x, centra en ese eje."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * max(len(text) - 1, 0)
    x, y = xy
    if anchor_center_x is not None:
        x = anchor_center_x - total / 2
    for ch, wch in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += wch + tracking
    return total


def fit_quote(draw, text, max_w, max_h, path, start=78, min_size=40):
    """Busca el mayor tamano de fuente que hace caber la cita."""
    for size in range(start, min_size - 1, -2):
        font = ImageFont.truetype(path, size)
        # ancho medio de caracter para estimar el wrap
        avg = draw.textlength("abcdefghijklmnopqrstuvwxyz ", font=font) / 27
        cols = max(int(max_w / avg), 12)
        lines = textwrap.wrap(text, width=cols)
        lh = size * 1.42
        if len(lines) * lh <= max_h and all(
            draw.textlength(ln, font=font) <= max_w for ln in lines
        ):
            return font, lines, lh
    font = ImageFont.truetype(path, min_size)
    lines = textwrap.wrap(text, width=34)
    return font, lines, min_size * 1.42


def fit_tracked(draw, text, max_w, path, start=30, min_size=17, tracking=3.0):
    """Mayor tamano que hace caber una linea con letter-spacing dentro de max_w.

    La cita ya tenia fit_quote; la linea de autor no, y por eso las atribuciones
    largas ("Seneca, Sobre la brevedad de la vida, 1.3 (hacia el ano 49)") se
    salian del marco por los dos lados. El tracking encoge con la fuente: si se
    dejara fijo, la version pequena parece otra tipografia.
    """
    for size in range(start, min_size - 1, -1):
        font = ImageFont.truetype(path, size)
        tr = tracking * size / start
        w = sum(draw.textlength(ch, font=font) for ch in text)
        w += tr * max(len(text) - 1, 0)
        if w <= max_w:
            return font, tr
    return ImageFont.truetype(path, min_size), tracking * min_size / start


def make_card(quote, author, out_path, variant="cream", kicker="SABIDURÍA DE BOLSILLO"):
    quote = quote.strip().strip('"').strip("“”")
    if variant == "gold":
        img = vertical_gradient((W, H), GOLD_LIGHT, GOLD_DARK).convert("RGB")
        fg, accent, rule = CREAM, CREAM, (247, 241, 228, 120)
    else:
        img = vertical_gradient((W, H), CREAM, CREAM_DEEP).convert("RGB")
        fg, accent, rule = INK, GOLD_DARK, GOLD

    d = ImageDraw.Draw(img)

    # Marco fino
    m = 46
    d.rectangle([m, m, W - m, H - m], outline=accent, width=3)
    d.rectangle([m + 12, m + 12, W - m - 12, H - m - 12], outline=accent, width=1)

    # Comilla decorativa
    qf = ImageFont.truetype(LORA, 190)
    d.text((W / 2, 232), "“", font=qf, fill=accent, anchor="mm")

    # Cita
    box_w, box_h = W - 2 * (m + 92), 620
    font_q, lines, lh = fit_quote(d, quote, box_w, box_h, LORA_IT)
    total_h = len(lines) * lh
    y = 360 + (box_h - total_h) / 2
    for ln in lines:
        d.text((W / 2, y), ln, font=font_q, fill=fg, anchor="ma")
        y += lh

    # Filete + autor
    ry = 1058
    d.line([(W / 2 - 70, ry), (W / 2 + 70, ry)], fill=accent, width=2)
    author_line = author.upper()
    fa, atr = fit_tracked(d, author_line, W - 2 * (m + 40), POPPINS)
    track_text(d, (0, ry + 34), author_line, fa, fg, tracking=atr, anchor_center_x=W / 2)

    # Firma de marca
    fk = ImageFont.truetype(POPPINS_LIGHT, 22)
    track_text(d, (0, H - m - 74), kicker.upper(), fk, accent, tracking=6.5,
               anchor_center_x=W / 2)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--quote", required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--variant", default="cream", choices=["cream", "gold"])
    p.add_argument("--kicker", default="SABIDURÍA DE BOLSILLO")
    a = p.parse_args()
    print(make_card(a.quote, a.author, a.out, a.variant, a.kicker))
