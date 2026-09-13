#!/usr/bin/env python3
"""Deterministic text overlay for media-lab single-image masters."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FONT_BOLD = ROOT / "assets/fonts/Poppins-Medium.ttf"
FONT_SERIF = ROOT / "assets/fonts/Lora-Variable.ttf"


def fit_font(draw: ImageDraw.ImageDraw, text: str, width: int, max_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(str(FONT_BOLD), size)
        if draw.textbbox((0, 0), text, font=font)[2] <= width:
            return font
    return ImageFont.truetype(str(FONT_BOLD), min_size)


def render(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGB")
    target_ratio = 4 / 5
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        crop_width = round(image.height * target_ratio)
        left = (image.width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, image.height))
    elif source_ratio < target_ratio:
        crop_height = round(image.width / target_ratio)
        top = (image.height - crop_height) // 2
        image = image.crop((0, top, image.width, top + crop_height))
    image = image.resize((1080, 1350), Image.Resampling.LANCZOS)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((54, 76, 1026, 405), radius=24, fill=(5, 39, 73, 224))

    lines = ["EL PRIMER LIBRO ILUSTRADO", "CON FOTOGRAFÍAS", "ERA AZUL"]
    y = 108
    for line in lines:
        font = fit_font(draw, line, 876, 66, 46)
        box = draw.textbbox((0, 0), line, font=font)
        x = (1080 - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=font, fill=(249, 240, 211, 255))
        y += 78

    sub_font = ImageFont.truetype(str(FONT_SERIF), 38)
    sub = "Anna Atkins · 1843"
    sub_box = draw.textbbox((0, 0), sub, font=sub_font)
    draw.text(((1080 - (sub_box[2] - sub_box[0])) // 2, 340), sub, font=sub_font, fill=(176, 220, 236, 255))

    brand_font = ImageFont.truetype(str(FONT_BOLD), 23)
    brand = "SABIDURÍA DE BOLSILLO"
    brand_box = draw.textbbox((0, 0), brand, font=brand_font)
    pad = 18
    bx = 1030 - (brand_box[2] - brand_box[0]) - 2 * pad
    draw.rounded_rectangle((bx, 1268, 1030, 1321), radius=14, fill=(5, 39, 73, 216))
    draw.text((bx + pad, 1278), brand, font=brand_font, fill=(249, 240, 211, 255))

    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "JPEG", quality=94, optimize=True, progressive=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    render(args.source, args.destination)


if __name__ == "__main__":
    main()
