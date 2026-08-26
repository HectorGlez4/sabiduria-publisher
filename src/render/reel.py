#!/usr/bin/env python3
"""
Sabiduría de Bolsillo — reel vertical 1080x1920 a partir de la misma pieza.

  python3 src/render/reel.py --title "VALENCIA, 1409" \
      --subtitle "El hospital que llamamos el primero, y que no lo fue" \
      --body "Un fraile vio en la calle cómo golpeaban a un hombre…" \
      --question "¿Cuántas veces lo primero fue solo lo primero que quisimos recordar?" \
      --out /ruta/salida.mp4 [--variant cream|gold]

Por qué un reel y no otra tarjeta
─────────────────────────────────
La página tiene 28.000 seguidores y su mejor publicación en 90 días llegó a
408 personas: un 1,5%, con 1 interacción y 0 me gusta. La audiencia está
inerte, y el feed reparte según señales de interacción que aquí no existen.

Los reels son la única superficie de Facebook que reparte a NO seguidores: no
dependen de esa audiencia dormida. La página nunca ha publicado uno —se miró
el top de 90 días y no hay ninguno—, así que es la palanca que queda sin
probar. Lo que no compra es calidad: si el gancho no funciona, un reel muere
igual que una foto.

Cómo se compone
───────────────
No es la tarjeta 4:5 estirada. Se compone nativo a 9:16 con la MISMA paleta,
las MISMAS fuentes y los mismos ayudantes que `text_card` —de ahí el import—
para que sea la misma marca y no un primo lejano.

El movimiento es una revelación por bloques: fondo, título, filete y subtítulo,
cuerpo, y la pregunta al final. Son fotogramas fijos encadenados, sin
transición: como cada uno solo AÑADE al anterior, el corte se lee como que el
texto aparece. Es deterministra y no depende de filtros frágiles de ffmpeg.

Deliberadamente sin música ni texto saltarín: la marca es contemplativa y un
reel estridente la contradiría. Se añade una pista de audio silenciosa porque
Facebook rechaza vídeos sin stream de audio.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fonts import LORA, LORA_IT, POPPINS_LIGHT  # noqa: E402
from text_card import (  # noqa: E402
    CREAM,
    CREAM_DEEP,
    GOLD_DARK,
    GOLD_LIGHT,
    INK,
    fit_block,
    track_text,
    vertical_gradient,
)

W, H = 1080, 1920

# Duración de cada bloque, en segundos. Suman ~8,6 s: por encima del mínimo de
# 3 s de Facebook y muy por debajo del máximo de 90 s. El cuerpo se lleva la
# parte más larga porque es lo único que hay que leer entero.
#
# El título entra en el bloque CERO a propósito. La primera versión abría con
# el lienzo vacío durante 0,9 s, y en un reel ese es justo el segundo que
# decide si alguien se queda: abrir sin gancho es regalarlo.
TIEMPOS = [1.4, 1.8, 3.0, 2.4]


def _lienzo(variant: str):
    """El fondo y el marco, idénticos a los de la tarjeta pero a 9:16."""
    if variant == "gold":
        img = vertical_gradient((W, H), GOLD_LIGHT, GOLD_DARK).convert("RGB")
        fg = accent = CREAM
    else:
        img = vertical_gradient((W, H), CREAM, CREAM_DEEP).convert("RGB")
        fg, accent = INK, GOLD_DARK

    d = ImageDraw.Draw(img)
    m = 52
    d.rectangle([m, m, W - m, H - m], outline=accent, width=3)
    d.rectangle([m + 14, m + 14, W - m - 14, H - m - 14], outline=accent, width=1)
    track_text(d, m + 74, "SABIDURÍA DE BOLSILLO",
               ImageFont.truetype(POPPINS_LIGHT, 24), accent, tracking=7)
    return img, d, fg, accent, m


def fotogramas(title: str, body: str, subtitle: str | None,
               question: str | None, variant: str) -> list[Image.Image]:
    """
    Los cuatro estados de la revelación.

    Se compone SIEMPRE sobre el mismo lienzo y se va acumulando, así que las
    posiciones no pueden bailar entre fotograma y fotograma: se calculan una
    vez, con el lienzo completo, y cada estado dibuja solo hasta donde toca.
    """
    base, d0, fg, accent, m = _lienzo(variant)
    inner_w = W - 2 * (m + 92)

    # Medidas primero, dibujo después. Si se midiera sobre cada fotograma, un
    # cuerpo que encoge la fuente movería el título de sitio a media revelación.
    ft, tlines, tlh = fit_block(d0, title.upper(), LORA, inner_w, 330, 96, 50, 1.22)
    fs = slines = slh = None
    if subtitle:
        fs, slines, slh = fit_block(d0, subtitle, LORA_IT, inner_w, 240, 54, 34, 1.36)
    fq = qlines = qlh = None
    if question:
        fq, qlines, qlh = fit_block(d0, question, LORA_IT, inner_w, 220, 44, 30, 1.4)

    y_titulo = 360
    y_filete = y_titulo + len(tlines) * tlh + 34
    y_sub = y_filete + 48
    y_cuerpo = y_sub + (len(slines) * slh + 40 if slines else 0)
    alto_pregunta = len(qlines) * qlh if qlines else 0
    tope_cuerpo = (H - m - 150) - y_cuerpo - (alto_pregunta + 60 if qlines else 0)
    fb, blines, blh = fit_block(d0, body, LORA, inner_w, max(tope_cuerpo, 140), 52, 30, 1.52)
    y_pregunta = H - m - 120 - alto_pregunta

    def bloque(d, y, lines, font, fill, lh):
        for ln in lines:
            d.text((W / 2, y), ln, font=font, fill=fill, anchor="ma")
            y += lh

    salida = []
    for etapa in range(4):
        img = base.copy()
        d = ImageDraw.Draw(img)
        bloque(d, y_titulo, tlines, ft, fg, tlh)   # el gancho, desde el primer cuadro
        if etapa >= 1:
            d.line([(W / 2 - 90, y_filete), (W / 2 + 90, y_filete)], fill=accent, width=2)
            if slines:
                bloque(d, y_sub, slines, fs, accent, slh)
        if etapa >= 2:
            bloque(d, y_cuerpo, blines, fb, fg, blh)
        if etapa >= 3 and qlines:
            bloque(d, y_pregunta, qlines, fq, accent, qlh)
        salida.append(img)
    return salida


def make_reel(title: str, body: str, out_path: str, subtitle: str | None = None,
              question: str | None = None, variant: str = "cream") -> str:
    marcos = fotogramas(title, body, subtitle, question, variant)
    total = sum(TIEMPOS)

    with tempfile.TemporaryDirectory() as tmp:
        lista = os.path.join(tmp, "lista.txt")
        with open(lista, "w", encoding="utf-8") as f:
            for i, (img, seg) in enumerate(zip(marcos, TIEMPOS)):
                ruta = os.path.join(tmp, f"f{i:03d}.png")
                img.save(ruta, "PNG")
                f.write(f"file '{ruta}'\nduration {seg}\n")
            # El demuxer concat ignora la duración del ÚLTIMO fichero, así que
            # hay que repetirlo. Sin esta línea el vídeo pierde el último bloque.
            f.write(f"file '{os.path.join(tmp, f'f{len(marcos) - 1:03d}.png')}'\n")

        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", lista,
            # Facebook rechaza el vídeo si no trae stream de audio, aunque el
            # reel sea mudo a propósito.
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            # `fps=30` va PRIMERO y no es decorativo. El filtro corre antes de que
            # `-r` multiplique fotogramas, así que sin esto `fade` solo ve los 4
            # cuadros de la lista: al de t=0 le aplica el fundido de entrada
            # entero, lo deja negro, y ese negro se estira los 1,4 s que dura el
            # bloque. El reel abría con la pantalla apagada.
            "-vf", (f"fps=30,fade=t=in:st=0:d=0.4,"
                    f"fade=t=out:st={total - 0.4:.2f}:d=0.4,format=yuv420p"),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
            "-c:a", "aac", "-b:a", "96k", "-shortest",
            # Recorte explícito. Hay que repetir el último fichero para que
            # concat no se coma su bloque, y ffmpeg le regala la duración del
            # anterior: sin este -t el vídeo se iba a 11,5 s y se quedaba en
            # negro 2,7 s después del fundido de salida.
            "-t", f"{total:.2f}",
            "-movflags", "+faststart",
            out_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg falló ({r.returncode}):\n{(r.stderr or '').strip()}")

    if not os.path.exists(out_path):
        raise RuntimeError(f"el reel no se generó: {out_path}")
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
    ruta = make_reel(a.title, a.body, a.out, a.subtitle, a.question, a.variant)
    kb = os.path.getsize(ruta) // 1024
    print(f"{ruta} · {kb} KB · {W}x{H} · {sum(TIEMPOS):.1f}s")
