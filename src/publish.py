#!/usr/bin/env python3
"""
Publica la siguiente pieza que toque, en todas sus plataformas.

    python3 -m src.publish --due            # lo que ya venció y sigue 'ready'
    python3 -m src.publish --id 2026-08-18-tarde
    python3 -m src.publish --due --dry-run  # genera, valida y enseña, sin publicar

Diseño: una pieza se marca 'published' solo si TODAS sus plataformas salieron.
Si una falla, las demás quedan registradas y la pieza queda 'failed' con el
detalle. Nunca se republica lo que ya tiene post_id — es la protección contra
duplicados que en el sistema anterior faltaba.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import hosting, variants  # noqa: E402
from src.platforms import meta  # noqa: E402
from src.platforms._pending import PENDING  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content" / "queue"
PUBLISHED = ROOT / "content" / "published"
ASSETS = ROOT / "assets"


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_history() -> list[dict]:
    """
    Lo ya publicado. Sin esto no se pueden comprobar cadencia, repetición ni
    alternancia: las tres se miden contra lo que salió de verdad, no contra la
    cola. Hasta ahora content/published/ solo se escribía y nunca se leía.
    """
    if not PUBLISHED.exists():
        return []
    return [load(p) for p in sorted(PUBLISHED.glob("*.json"))]


def save(unit: dict, path: pathlib.Path) -> None:
    path.write_text(json.dumps(unit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_due() -> tuple[dict, pathlib.Path] | tuple[None, None]:
    now = datetime.now(timezone.utc)
    candidates = []
    for p in sorted(QUEUE.glob("*.json")):
        unit = load(p)
        if unit.get("status") != "ready":
            continue
        when = unit.get("publish_at")
        if when and datetime.fromisoformat(when.replace("Z", "+00:00")) <= now:
            candidates.append((unit, p))
    if not candidates:
        return None, None
    candidates.sort(key=lambda c: c[0]["publish_at"])
    return candidates[0]


def render_card(unit: dict) -> pathlib.Path:
    """Regenera el PNG desde los parámetros. Determinista: no se versiona la imagen."""
    card = unit["card"]
    out = ASSETS / f"{unit['id']}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    script = ROOT / "src" / "render" / f"{card['renderer']}.py"

    cmd = [sys.executable, str(script), "--variant", card["variant"], "--out", str(out)]
    if card["renderer"] == "quote_card":
        q = unit["core"]["quote"]
        author = q["author"]
        if q.get("work"):
            author = f"{q['author']}, {q['work']}"
        cmd += ["--quote", q["text"], "--author", author]
    else:
        cmd += ["--title", card["title"], "--subtitle", card["subtitle"], "--body", card["body"]]

    # Sin capturar y reemitir stderr, un fallo del renderer llega aquí como un
    # CalledProcessError opaco que no dice ni la excepción ni la línea. Costó
    # una sesión entera diagnosticar así unas rutas de fuente inexistentes.
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        detalle = (r.stderr or r.stdout or "(sin salida)").strip()
        raise RuntimeError(
            f"falló el renderer {card['renderer']} (código {r.returncode}):\n{detalle}"
        )
    if not out.exists():
        raise RuntimeError(f"la tarjeta no se generó: {out}")
    return out


def upload_asset(path: pathlib.Path) -> str:
    """
    Publica la imagen y devuelve su URL HTTPS pública.

    Instagram y Threads NO aceptan subida binaria: Meta descarga la imagen desde
    la URL. Ver src/hosting.py para los backends disponibles.
    """
    return hosting.upload(path, ROOT)


def publish_unit(unit: dict, path: pathlib.Path, dry_run: bool = False) -> bool:
    print(f"\n▶ {unit['id']} · {unit['pillar']} · {unit['core'].get('subject', '')}")

    # La hora real, no la programada: si esto sale fuera de horario —por --id
    # o por un cron retrasado— la cadencia tiene que medir el espaciado de
    # verdad, que es lo que ven los filtros de spam.
    problems = variants.preflight(unit, load_history(), datetime.now(timezone.utc))
    if problems:
        print("  ✗ no pasa las comprobaciones previas:")
        for p in problems:
            print(f"      - {p}")
        return False
    print("  ✓ comprobaciones previas")

    card_path = render_card(unit)
    print(f"  ✓ tarjeta: {card_path.name} ({card_path.stat().st_size // 1024} KB)")

    texts = variants.build_all(unit)
    for platform, v in texts.items():
        preview = v["text"].split("\n")[0][:70]
        print(f"      {platform:11s} {len(v['text']):5d} car.  {preview}…")

    if dry_run:
        print("  · dry-run: no se publica nada")
        return True

    image_url = upload_asset(card_path)
    unit.setdefault("results", {})
    ok = True

    for platform in unit.get("targets", []):
        if unit["results"].get(platform, {}).get("post_id"):
            print(f"  · {platform}: ya publicado, se salta")
            continue
        if platform in PENDING:
            PENDING[platform]()  # levanta PlatformBlocked con el motivo exacto
        try:
            fn = meta.PUBLISHERS[platform]
            res = fn(image_url, texts[platform]["text"])
            res["published_at"] = datetime.now(timezone.utc).isoformat()
            unit["results"][platform] = res
            print(f"  ✓ {platform}: {res['post_id']}")
        except Exception as e:  # noqa: BLE001
            unit["results"][platform] = {"error": str(e)}
            print(f"  ✗ {platform}: {e}")
            ok = False
        save(unit, path)

    unit["status"] = "published" if ok else "failed"
    save(unit, path)

    if ok:
        PUBLISHED.mkdir(parents=True, exist_ok=True)
        path.rename(PUBLISHED / path.name)
        print(f"  ✓ movida a content/published/{path.name}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true", help="la pieza vencida más antigua en estado ready")
    ap.add_argument("--id", help="una pieza concreta por id")
    ap.add_argument("--dry-run", action="store_true", help="genera y valida, sin publicar")
    a = ap.parse_args()

    if a.id:
        path = QUEUE / f"{a.id}.json"
        if not path.exists():
            print(f"no existe {path}", file=sys.stderr)
            return 1
        unit = load(path)
    elif a.due:
        unit, path = pick_due()
        if not unit:
            print("nada vencido pendiente de publicar")
            return 0
    else:
        print("usa --due o --id", file=sys.stderr)
        return 1

    return 0 if publish_unit(unit, path, a.dry_run) else 1


if __name__ == "__main__":
    raise SystemExit(main())
