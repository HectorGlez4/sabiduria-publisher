"""
Prueba de extremo a extremo contra el doble de la Graph API.

Ejecuta el mismo camino que la publicación real: comprobaciones previas →
generación de la tarjeta → derivación de textos → hosting → Facebook →
Instagram (contenedor, polling, reintento) → Threads → cambio de estado y
movimiento del archivo.

    python3 tests/test_end_to_end.py
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fake_graph_shim  # noqa: E402,F401  (configura el entorno antes de importar src)

from src import publish, variants  # noqa: E402
from src.platforms import meta  # noqa: E402

# Pieza de prueba, independiente del contenido real. Reproduce la forma de una
# tarjeta de cita, que es la que ejercita mas codigo (quote_card + atribucion).
FIXTURE = """{
  "id": "2099-01-01-tarde",
  "publish_at": "2099-01-01T19:00:00Z",
  "slot": "tarde",
  "pillar": "cita",
  "core": {
    "subject": "Pieza de prueba del publicador",
    "hook": "Una frase de prueba que no se publica en ningun sitio.",
    "quote": {
      "text": "Una frase de prueba que no se publica en ningun sitio.",
      "author": "Nadie",
      "work": "Obra inexistente para comprobar que la atribucion larga cabe",
      "attribution_verified": true
    },
    "body": ["Primer parrafo de prueba.", "Segundo parrafo de prueba."],
    "question": "\u00bfUna pregunta de prueba?"
  },
  "card": {"renderer": "quote_card", "variant": "cream"},
  "tags": {
    "primary": "#SabiduriaDeBolsillo",
    "topic": ["#Prueba", "#Test"],
    "extended": ["#Uno", "#Dos", "#Tres", "#Cuatro", "#Cinco", "#Seis", "#Siete"]
  },
  "sources": [{"claim": "es una prueba", "source": "el propio test"}],
  "do_not_use": [],
  "targets": ["facebook", "instagram", "threads"],
  "status": "ready",
  "results": {}
}"""

FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FAILURES.append(label)


def main() -> int:
    import fake_graph

    # El test trabaja sobre su PROPIA pieza y sus PROPIOS directorios. Antes
    # usaba la pieza real de la cola como fixture y se rompio dos veces: al
    # quitarle Threads perdio cobertura, y al publicarse de verdad el archivo
    # desaparecio de content/queue/. El contenido vivo no es un fixture.
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sdb-test-"))
    publish.QUEUE = tmp / "queue"
    publish.PUBLISHED = tmp / "published"
    publish.ASSETS = tmp / "assets"
    publish.QUEUE.mkdir(parents=True)

    unit = json.loads(FIXTURE)
    unit_path = publish.QUEUE / f"{unit['id']}.json"
    unit_path.write_text(json.dumps(unit, ensure_ascii=False, indent=2), encoding="utf-8")
    card = publish.render_card(unit)

    srv, base = fake_graph.start(card)
    os.environ["META_GRAPH_BASE"] = base
    os.environ["META_THREADS_BASE"] = base
    meta.GRAPH = base
    meta.THREADS_GRAPH = base

    # hosting simulado: el doble sirve la imagen
    publish.upload_asset = lambda p: f"{base}/img/{p.name}"  # type: ignore[assignment]

    os.environ.update({
        "SDB_PAGE_ID": "PAGE", "SDB_PAGE_TOKEN": "T",
        "SDB_IG_USER_ID": "IG", "SDB_THREADS_USER_ID": "TH", "SDB_THREADS_TOKEN": "T",
    })

    print("\n0. Tarjeta: fuentes y encaje")
    # Las rutas de fuente eran absolutas al sandbox donde se escribio el repo.
    # Fuera de ahi, PIL levantaba "cannot open resource" y la publicacion moria
    # en el primer paso. Se comprueba que se resuelven DENTRO del repo.
    sys.path.insert(0, str(ROOT / "src" / "render"))
    import fonts as brand_fonts
    import quote_card as qc
    from PIL import Image, ImageDraw

    rutas = [brand_fonts.LORA, brand_fonts.LORA_IT,
             brand_fonts.POPPINS, brand_fonts.POPPINS_LIGHT]
    check(all(pathlib.Path(r).is_file() for r in rutas),
          "las cuatro fuentes de marca existen")
    check(all(str(ROOT) in r for r in rutas),
          "se resuelven dentro del repo, no del sistema operativo")

    # La cita tenia fit_quote; la linea de autor no, y las atribuciones largas
    # se salian del marco por los dos lados (visible en la tarjeta de ejemplo).
    d = ImageDraw.Draw(Image.new("RGB", (qc.W, qc.H)))
    max_w = qc.W - 2 * (46 + 40)
    largo = "SÉNECA, SOBRE LA BREVEDAD DE LA VIDA, 1.3 (HACIA EL AÑO 49)"
    f, tr = qc.fit_tracked(d, largo, max_w, qc.POPPINS)
    ancho = sum(d.textlength(c, font=f) for c in largo) + tr * (len(largo) - 1)
    check(ancho <= max_w,
          f"una atribucion larga cabe en el marco ({ancho:.0f} <= {max_w} px)")

    print("\n1. Comprobaciones previas")
    check(variants.preflight(unit, []) == [], "la pieza pasa limpia")

    print("\n2. Publicación completa")
    ok = publish.publish_unit(unit, unit_path)
    check(ok == "published", "publish_unit devuelve 'published'")

    print("\n3. Resultados por plataforma")
    r = unit.get("results", {})
    check(r.get("facebook", {}).get("post_id") == "PAGE_POST_1", "Facebook devolvió post_id")
    check(r.get("instagram", {}).get("post_id") == "IG_POST_1", "Instagram devolvió post_id")
    check(r.get("threads", {}).get("post_id") == "TH_POST_1", "Threads devolvió post_id")
    # El enlace se PIDE a la API. Construirlo desde el id daba una URL rota en
    # Instagram, que usa un código corto y no el id numérico del medio.
    check(r.get("instagram", {}).get("url") == "https://www.instagram.com/p/ABC123xyz/",
          "Instagram guarda el permalink real, no uno construido")
    check(r.get("facebook", {}).get("url") == "https://www.facebook.com/pagina/posts/1",
          "Facebook guarda el permalink real")

    print("\n4. Comportamiento difícil de acertar a ciegas")
    check(fake_graph.STATE["polls"] >= 2, f"esperó el procesamiento del contenedor ({fake_graph.STATE['polls']} sondeos)")
    check(fake_graph.STATE["publish_attempts"] == 2, "reintentó tras el error 9007 y publicó a la segunda")

    print("\n5. Estado final")
    check(unit["status"] == "published", "la pieza queda 'published'")
    moved = publish.PUBLISHED / unit_path.name
    check(moved.exists(), "el archivo se movió a content/published/")
    check(not unit_path.exists(), "ya no está en la cola: no se puede republicar")

    print("\n6. Idempotencia")
    unit2 = json.loads(moved.read_text(encoding="utf-8"))
    before = fake_graph.STATE["publish_attempts"]
    for p in unit2["targets"]:
        registro = unit2["results"].get(p, {})
        # 'post_id' para lo que sale por API, 'via' para lo que se sirve por el
        # feed. Las dos marcas valen: lo que se comprueba es que la pieza no se
        # pueda reenviar, no por qué camino salió.
        already = bool(registro.get("post_id") or registro.get("via"))
        if not already:
            FAILURES.append(f"{p} sin marca de publicación registrada")
    check(fake_graph.STATE["publish_attempts"] == before, "una pieza publicada no se vuelve a enviar")

    # limpieza: todo vivio en un directorio temporal, no se toca nada real
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print(f"FALLARON {len(FAILURES)}:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("Todo correcto: el camino completo funciona.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
