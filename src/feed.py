"""
El feed RSS del que Facebook se sirve.

    python3 -m src.feed            # regenera docs/feed.xml
    python3 -m src.feed --stdout   # lo enseña sin escribir

Por qué existe
──────────────
Nació como vía de escape: entre el 17 y el 25 de agosto de 2026 todo lo que salía
por la Graph API tenía alcance exactamente cero, porque la app estaba en modo
desarrollo. La idea era dársela a dlvr.it, Zapier o IFTTT —que ya tienen su app
verificada por Meta— para que publicaran de forma nativa.

No hizo falta: la app se publicó el 25 de agosto y Facebook volvió a la API. El
feed se queda porque es barato de mantener y es la red de seguridad si Meta
vuelve a cerrar el camino de la API.

Un aviso si algún día se activa un servicio de estos: la página está en New Pages
Experience (`has_transitioned_to_new_page_experience: True`), y ninguno de los
tres la lista entre las páginas disponibles. Zapier cargaba "1 resultado" y no
era esta. Ese es el muro con el que se chocó, y no es cosa de un proveedor
concreto.

Dos detalles que costaron encontrarse y que este módulo depende de ellos
──────────────────────────────────────────────────────────────────────
1. La imagen NO se enlaza desde GitHub Pages. El rastreador de Meta recibe 403
   de Pages —comprobado en el depurador de contenido compartido, con extracción
   nueva y con un robots.txt permisivo—. Sí sabe descargar de
   raw.githubusercontent.com: es exactamente de donde baja hoy las tarjetas que
   publica en Instagram. Por eso el <enclosure> apunta a raw y no al dominio.

2. El enlace lleva `?de=facebook`, la convención del sitio de citas
   (src/lib/redes.ts en hectorglez4.github.io): parámetro en español, conjunto
   cerrado de cinco redes, nada de utm_source. Si alguna vez se publica desde
   otra cuenta, el valor tiene que salir de esa misma lista.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import variants  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLICADAS = ROOT / "content" / "published"
SALIDA = ROOT / "docs" / "feed.xml"

SITIO = "https://sabiduriadebolsillo.net"
FEED_URL = "https://sabiduria.work-it.fr/feed.xml"
REPO = "HectorGlez4/sabiduria-publisher"
RAMA = "main"

# Cuántas piezas se ofrecen. Normalmente es la ventana de recuperación por si el
# servicio de turno estuvo caído un día: solo mira las nuevas.
#
MAXIMO = 25


def _url_de_tarjeta(pieza_id: str) -> str:
    """La misma URL que se le da a Meta al publicar en Instagram. Ver punto 1 del módulo."""
    return f"https://raw.githubusercontent.com/{REPO}/{RAMA}/assets/{pieza_id}.png"


def _fecha(unidad: dict) -> datetime:
    """
    Cuándo salió de verdad, no cuándo estaba previsto.

    `publish_at` es el "no antes de"; la cadencia puede haberla movido horas. El
    orden del feed tiene que ser el orden real de publicación o el servicio de
    turno reordena las piezas al recuperarse de un fallo.
    """
    fb = (unidad.get("results") or {}).get("facebook") or {}
    ig = (unidad.get("results") or {}).get("instagram") or {}
    marca = fb.get("published_at") or ig.get("published_at") or unidad.get("publish_at")
    if not marca:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(marca.replace("Z", "+00:00"))


def _titulo(unidad: dict) -> str:
    """
    El hook, en una línea.

    Las citas traen el hook en dos líneas (la cita y luego "— Autor, obra"); en un
    título RSS eso sale partido y feo, así que se queda la primera.
    """
    hook = (unidad.get("core", {}).get("hook") or unidad["id"]).strip()
    return hook.split("\n")[0].strip().strip('"').strip("“”")


def piezas() -> list[dict]:
    """Lo publicado que iba dirigido a Facebook, de lo más nuevo a lo más viejo."""
    if not PUBLICADAS.exists():
        return []
    fuera = []
    for p in sorted(PUBLICADAS.glob("*.json")):
        unidad = json.loads(p.read_text(encoding="utf-8"))
        # `facebook_reel` cuenta: es la misma pieza en otro formato, y si el
        # respaldo tuviera que entrar en acción tendría que llevarla también.
        if not {"facebook", "facebook_reel"} & set(unidad.get("targets") or []):
            continue
        fuera.append(unidad)
    fuera.sort(key=_fecha, reverse=True)
    return fuera[:MAXIMO]


def _item(unidad: dict) -> str:
    texto = variants.build_all(unidad)["facebook"]["text"]
    enlace = f"{SITIO}/?de=facebook"
    imagen = _url_de_tarjeta(unidad["id"])
    return f"""    <item>
      <title>{escape(_titulo(unidad))}</title>
      <link>{escape(enlace)}</link>
      <guid isPermaLink="false">sdb-{escape(unidad['id'])}</guid>
      <pubDate>{format_datetime(_fecha(unidad))}</pubDate>
      <description><![CDATA[{texto}]]></description>
      <enclosure url="{escape(imagen)}" type="image/png" length="0"/>
      <media:content url="{escape(imagen)}" medium="image" type="image/png"/>
    </item>"""


def construir() -> str:
    cuerpo = "\n".join(_item(u) for u in piezas())
    ahora = format_datetime(datetime.now(timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Sabiduría de Bolsillo</title>
    <link>{SITIO}/</link>
    <description>Historia, filosofía y curiosidades verificadas antes de salir.</description>
    <language>es</language>
    <lastBuildDate>{ahora}</lastBuildDate>
    <atom:link href="{FEED_URL}" rel="self" type="application/rss+xml"/>
{cuerpo}
  </channel>
</rss>
"""


def escribir() -> pathlib.Path:
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(construir(), encoding="utf-8")
    return SALIDA


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true", help="enseñar sin escribir")
    a = ap.parse_args()
    if a.stdout:
        print(construir())
        return 0
    ruta = escribir()
    print(f"{ruta.relative_to(ROOT)} · {len(piezas())} piezas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
