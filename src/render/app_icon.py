#!/usr/bin/env python3
"""
El icono de la marca: 1024x1024, para la app de Meta y para el sitio.

    python3 src/render/app_icon.py --out docs/icono.png

Se genera en vez de guardarse como binario suelto por el mismo motivo que las
tarjetas: la imagen es una funcion pura del codigo. Si manana cambia el oro de
la paleta, el icono cambia con ella y nadie tiene que acordarse de reexportarlo
desde una herramienta de diseno.

La paleta y las fuentes salen de quote_card.py — a proposito. Un icono que no
es exactamente el mismo oro que las tarjetas se nota, y se nota mal.
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fonts import LORA, POPPINS_LIGHT  # noqa: E402
from quote_card import (  # noqa: E402
    GOLD_DARK,
    GOLD_LIGHT,
    CREAM,
    track_text,
    vertical_gradient,
)

S = 1024


def make_icon(out_path: str) -> None:
    img = vertical_gradient((S, S), GOLD_LIGHT, GOLD_DARK).convert("RGB")
    d = ImageDraw.Draw(img)

    # Marco doble, el mismo gesto que la tarjeta pero a escala de icono.
    m = 64
    d.rectangle([m, m, S - m, S - m], outline=CREAM, width=4)
    d.rectangle([m + 16, m + 16, S - m - 16, S - m - 16], outline=CREAM, width=2)

    # La comilla es lo unico que sobrevive a 32 px. Un monograma "SB" o el
    # nombre completo se convierten en un borron a ese tamano; la comilla
    # sigue leyendose como comilla, y es el gesto que ya identifica a las
    # tarjetas.
    #
    # Se centra por los PIXELES PINTADOS, no por anchor="mm" ni por textbbox().
    # Las dos mienten aqui: para esta comilla en Lora 560 devuelven una caja de
    # 426 px de alto cuando la marca solo pinta unos 160, todos en la mitad de
    # arriba. Centrar con ellas deja el icono cabeceando, con un hueco debajo.
    # Pintamos la comilla en una mascara, miramos donde cae de verdad con
    # getbbox() y compensamos con eso.
    qf = ImageFont.truetype(LORA, 560)
    sonda = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sonda).text((S / 2, S / 2), "“", font=qf, fill=255, anchor="mm")
    arriba, abajo = sonda.getbbox()[1], sonda.getbbox()[3]
    centro_real = (arriba + abajo) / 2          # donde cae con el ancla en S/2
    centro_zona = ((m + 16) + (S - m - 96)) / 2  # del marco interior a la firma
    d.text((S / 2, S / 2 + (centro_zona - centro_real)), "“",
           font=qf, fill=CREAM, anchor="mm")

    # La firma solo existe para los tamanos grandes (la ficha de la app en el
    # panel de Meta, la cabecera del sitio). A 32 px se pierde, y no pasa nada.
    track_text(d, (0, S - m - 96), "SABIDURÍA DE BOLSILLO",
               ImageFont.truetype(POPPINS_LIGHT, 30), CREAM,
               tracking=7.5, anchor_center_x=S / 2)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    print(f"{out_path} · {os.path.getsize(out_path) // 1024} KB · {S}x{S}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="docs/icono.png")
    make_icon(p.parse_args().out)
