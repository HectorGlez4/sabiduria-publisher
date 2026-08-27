#!/usr/bin/env python3
"""
Sabiduría de Bolsillo — historia vertical 1080x1920, en PNG.

  python3 src/render/historia.py --title "VALENCIA, 1409" \
      --body "Un fraile vio en la calle…" --out /ruta/salida.png [--variant cream|gold]

Es **el último fotograma del reel**, quieto. No una composición nueva: la de
`reel.py` ya está resuelta a 9:16 con la paleta y las fuentes de la marca, y
tener dos maneras de componer lo mismo garantiza que un día enseñen cosas
distintas. Por eso este módulo no dibuja nada — llama a `fotogramas` y guarda
el estado final.

Por qué historias
─────────────────
En la semana del 16 al 22 de agosto de 2026, UNA historia de esta página hizo
145 visualizaciones mientras 19 publicaciones de feed sumaron 150 entre todas.
Una historia rindió como diecinueve posts. Es el formato con mejor rendimiento
demostrado en esta página concreta, y el bot no lo usaba.

Lo que se acepta y lo que no
────────────────────────────
Meta admite hasta 10 MB, pero recomienda PNG por debajo de 1 MB para que no se
pixele. Un lienzo de degradado y texto sale sobre los 200 KB, así que sobra
margen; aun así se comprueba, porque un PNG que engorde sin que nadie mire se
publicaría borroso y nadie lo sabría hasta verlo en el móvil.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reel import fotogramas  # noqa: E402

# El aviso de Meta: por encima de esto la historia puede salir pixelada.
KB_RECOMENDADOS = 1024


def make_story(title: str, body: str, out_path: str, subtitle: str | None = None,
               question: str | None = None, variant: str = "cream") -> str:
    marcos = fotogramas(title, body, subtitle, question, variant)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    # El formato lo decide la extensión, porque las dos redes no piden lo mismo:
    # Facebook acepta el PNG tal cual, e Instagram documenta JPEG como el ÚNICO
    # formato admitido para publicar por API. Un PNG a /media lo rechaza.
    if out_path.lower().endswith((".jpg", ".jpeg")):
        # JPEG no tiene canal alfa; sin convertir, Pillow falla al guardar.
        marcos[-1].convert("RGB").save(out_path, "JPEG", quality=92, optimize=True)
    else:
        marcos[-1].save(out_path, "PNG", optimize=True)

    kb = os.path.getsize(out_path) // 1024
    if kb > KB_RECOMENDADOS:
        print(f"aviso: {kb} KB — Meta recomienda menos de {KB_RECOMENDADOS} KB "
              f"para que la historia no se pixele", file=sys.stderr)
    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--subtitle")
    p.add_argument("--question")
    p.add_argument("--variant", default="cream", choices=["cream", "gold"])
    p.add_argument("--out", required=True)
    a = p.parse_args()
    ruta = make_story(a.title, a.body, a.out, a.subtitle, a.question, a.variant)
    print(f"{ruta} · {os.path.getsize(ruta) // 1024} KB · 1080x1920")
