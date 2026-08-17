#!/usr/bin/env python3
"""
Sabiduria De Bolsillo - tarjeta de texto (titulo + cuerpo), 1080x1350.

Genera la tarjeta de los posts de figura historica, civilizacion, filosofia,
curiosidad y arte y ciencia. Desde el 12 ago 2026 la misma imagen se publica
en Facebook y en Instagram: en Facebook va como foto con el copy de pie, no
como post de solo texto.

Uso:
  python3 text_card.py --title "SIMON BOLIVAR" \
      --subtitle "El Libertador que sono con una America unida" \
      --body "Libero 6 naciones del dominio espanol. Murio a los 47 anos, enfermo y desilusionado." \
      --out /ruta/salida.png [--variant cream|gold]

La ruta de --out debe ser /mnt/user-data/outputs/AAAA-MM-DD-franja.png
(franja: manana, tarde o noche).
"""
import argparse
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

GOLD_DARK = (150, 114, 45)
GOLD_LIGHT = (214, 183, 116)
CREAM = (247, 241, 228)
CREAM_DEEP = (238, 228, 208)
INK = (44, 38, 28)

FONT_DIR = "/usr/share/fonts/truetype/google-fonts"
LORA = os.path.join(FONT_DIR, "Lora-Variable.ttf")
LORA_IT = os.path.join(FONT_DIR, "Lora-Italic-Variable.ttf")
POPPINS = os.path.join(FONT_DIR, "Poppins-Medium.ttf")
POPPINS_LIGHT = os.path.join(FONT_DIR, "Poppins-Light.ttf")

W, H = 1080, 1350


def vertical_gradient(size, top, bottom):
    w, h = size
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h), Image.BILINEAR)


def track_text(draw, y, text, font, fill, tracking=0, center_x=W / 2):
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * max(len(text) - 1, 0)
    x = center_x - total / 2
    for ch, wch in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += wch + tracking
    return total


def wrap_to_width(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        probe = (cur + " " + w).strip()
        if draw.textlength(probe, font=font) <= max_w or not cur:
            cur = probe
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_block(draw, text, path, max_w, max_h, start, min_size, line_ratio=1.5):
    for size in range(start, min_size - 1, -2):
        font = ImageFont.truetype(path, size)
        lines = wrap_to_width(draw, text, font, max_w)
        lh = size * line_ratio
        if len(lines) * lh <= max_h:
            return font, lines, lh
    font = ImageFont.truetype(path, min_size)
    return font, wrap_to_width(draw, text, font, max_w), min_size * line_ratio


def make_card(title, body, out_path, subtitle=None, variant="cream",
              kicker="SABIDURÍA DE BOLSILLO"):
    if variant == "gold":
        img = vertical_gradient((W, H), GOLD_LIGHT, GOLD_DARK).convert("RGB")
        fg = accent = CREAM
    else:
        img = vertical_gradient((W, H), CREAM, CREAM_DEEP).convert("RGB")
        fg, accent = INK, GOLD_DARK

    d = ImageDraw.Draw(img)

    m = 46
    d.rectangle([m, m, W - m, H - m], outline=accent, width=3)
    d.rectangle([m + 12, m + 12, W - m - 12, H - m - 12], outline=accent, width=1)

    # Kicker superior
    fk = ImageFont.truetype(POPPINS_LIGHT, 22)
    track_text(d, m + 62, kicker.upper(), fk, accent, tracking=6.5)

    inner_w = W - 2 * (m + 84)

    # Titulo
    ft, tlines, tlh = fit_block(d, title.upper(), LORA, inner_w, 260, 86, 46, 1.22)
    y = 268
    for ln in tlines:
        d.text((W / 2, y), ln, font=ft, fill=fg, anchor="ma")
        y += tlh

    # Filete
    y += 26
    d.line([(W / 2 - 80, y), (W / 2 + 80, y)], fill=accent, width=2)
    y += 44

    # Subtitulo opcional, en cursiva
    if subtitle:
        fs, slines, slh = fit_block(d, subtitle, LORA_IT, inner_w, 190, 50, 32, 1.36)
        for ln in slines:
            d.text((W / 2, y), ln, font=fs, fill=accent, anchor="ma")
            y += slh
        y += 34

    # Cuerpo
    remaining = (H - m - 150) - y
    fb, blines, blh = fit_block(d, body, LORA, inner_w, max(remaining, 120), 48, 28, 1.52)
    for ln in blines:
        d.text((W / 2, y), ln, font=fb, fill=fg, anchor="ma")
        y += blh

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle")
    p.add_argument("--body", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--variant", default="cream", choices=["cream", "gold"])
    p.add_argument("--kicker", default="SABIDURÍA DE BOLSILLO")
    a = p.parse_args()
    print(make_card(a.title, a.body, a.out, a.subtitle, a.variant, a.kicker))
