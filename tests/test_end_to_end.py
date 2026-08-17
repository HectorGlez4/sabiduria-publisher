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

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fake_graph_shim  # noqa: E402,F401  (configura el entorno antes de importar src)

from src import publish, variants  # noqa: E402
from src.platforms import meta  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FAILURES.append(label)


def main() -> int:
    import fake_graph

    unit_path = ROOT / "content" / "queue" / "2026-08-17-tarde.json"
    backup = json.loads(unit_path.read_text(encoding="utf-8"))

    # tarjeta primero, para que el servidor pueda servirla
    unit = json.loads(unit_path.read_text(encoding="utf-8"))
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

    print("\n1. Comprobaciones previas")
    check(variants.preflight(unit) == [], "la pieza pasa limpia")

    print("\n2. Publicación completa")
    ok = publish.publish_unit(unit, unit_path)
    check(ok, "publish_unit devuelve éxito")

    print("\n3. Resultados por plataforma")
    r = unit.get("results", {})
    check(r.get("facebook", {}).get("post_id") == "PAGE_POST_1", "Facebook devolvió post_id")
    check(r.get("instagram", {}).get("post_id") == "IG_POST_1", "Instagram devolvió post_id")
    check(r.get("threads", {}).get("post_id") == "TH_POST_1", "Threads devolvió post_id")

    print("\n4. Comportamiento difícil de acertar a ciegas")
    check(fake_graph.STATE["polls"] >= 2, f"esperó el procesamiento del contenedor ({fake_graph.STATE['polls']} sondeos)")
    check(fake_graph.STATE["publish_attempts"] == 2, "reintentó tras el error 9007 y publicó a la segunda")

    print("\n5. Estado final")
    check(unit["status"] == "published", "la pieza queda 'published'")
    moved = ROOT / "content" / "published" / unit_path.name
    check(moved.exists(), "el archivo se movió a content/published/")
    check(not unit_path.exists(), "ya no está en la cola: no se puede republicar")

    print("\n6. Idempotencia")
    unit2 = json.loads(moved.read_text(encoding="utf-8"))
    before = fake_graph.STATE["publish_attempts"]
    for p in unit2["targets"]:
        already = bool(unit2["results"].get(p, {}).get("post_id"))
        if not already:
            FAILURES.append(f"{p} sin post_id registrado")
    check(fake_graph.STATE["publish_attempts"] == before, "una pieza publicada no se vuelve a enviar")

    # restaurar
    srv.shutdown()
    moved.unlink(missing_ok=True)
    unit_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(ROOT / "content" / "published", ignore_errors=True)

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
