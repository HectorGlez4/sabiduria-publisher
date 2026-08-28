#!/usr/bin/env python3
"""
Publica en Threads desde el archivo, en su propio carril.

    .venv/bin/python scripts/hilos.py --dry-run
    .venv/bin/python scripts/hilos.py --max 3

Por qué un carril aparte
────────────────────────
La cadencia de `variants.py` cuenta UNIDADES, no plataformas: el tope diario y
el espaciado miran cuántas piezas salieron, vengan de la red que vengan. Si
Threads pasara por ahí, veinticuatro hilos al día se comerían los doce huecos
del día entero y no saldría ni una foto ni un reel. Threads necesita su propio
reloj, y lo tiene aquí.

Eso es correcto además por el fondo: el tope existe para no parecer un bot en el
muro de Facebook, donde el público es el mismo y ve las publicaciones seguidas.
Threads es otra superficie, con otro público —hoy, ninguno— y otro ritmo nativo,
que es mucho más alto que el de Facebook.

De dónde sale el contenido
──────────────────────────
Del ARCHIVO entero, no de la cola. En Threads no se ha publicado nunca, así que
las más de cien piezas publicadas son inéditas ahí: no hay repetición que
evitar mientras queden piezas sin hilo. Se elige la más antigua sin publicar en
Threads; cuando se agoten, la que lleve más tiempo sin volver a salir.

Cada pieza guarda su resultado en `results.threads`, igual que las demás redes,
así que el rastro y el control de repetición son el mismo mecanismo de siempre.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import variants  # noqa: E402
from src.platforms import meta  # noqa: E402

ARCHIVO = ROOT / "content" / "published"

# Una por hora, que es lo pedido. El espaciado se mide contra el último hilo
# REAL, no contra el reloj de la ejecución: si GitHub se salta horas —y se las
# salta— la siguiente ejecución encuentra el hueco y publica, en vez de esperar
# a una hora en punto que ya pasó.
MINUTOS_ENTRE_HILOS = 55

# Tope diario propio. La API de Threads admite 250 publicaciones cada 24 h; esto
# está muy por debajo y deja margen para reintentos.
MAX_AL_DIA = 24


def _cuando(u: dict) -> datetime | None:
    r = (u.get("results") or {}).get("threads") or {}
    t = r.get("published_at")
    if not t:
        return None
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def candidatas() -> list[tuple[pathlib.Path, dict]]:
    """Las del archivo, primero las que nunca salieron en Threads."""
    sin_hilo, con_hilo = [], []
    for p in sorted(ARCHIVO.glob("*.json")):
        u = json.loads(p.read_text(encoding="utf-8"))
        if not (u.get("core") or {}).get("hook"):
            continue
        (con_hilo if _cuando(u) else sin_hilo).append((p, u))
    sin_hilo.sort(key=lambda x: x[1]["id"])
    con_hilo.sort(key=lambda x: _cuando(x[1]) or datetime.min.replace(tzinfo=timezone.utc))
    return sin_hilo + con_hilo


def hilos_recientes() -> list[datetime]:
    fuera = []
    for p in ARCHIVO.glob("*.json"):
        t = _cuando(json.loads(p.read_text(encoding="utf-8")))
        if t:
            fuera.append(t)
    return sorted(fuera)


def puede_publicar(ahora: datetime) -> str | None:
    """None si toca; si no, el motivo."""
    previos = hilos_recientes()
    if previos:
        hueco = (ahora - previos[-1]).total_seconds() / 60
        if hueco < MINUTOS_ENTRE_HILOS:
            return (f"a {hueco:.0f} min del último hilo: el mínimo son "
                    f"{MINUTOS_ENTRE_HILOS}")
    hoy = [t for t in previos if t > ahora - timedelta(hours=24)]
    if len(hoy) >= MAX_AL_DIA:
        return f"ya hay {len(hoy)} hilos en 24 h: el máximo son {MAX_AL_DIA}"
    return None


def _registrar(ruta: pathlib.Path, pieza_id: str) -> None:
    """Sube el registro de ESTE hilo antes de esperar al siguiente.

    Registrar al final de la ejecución no vale: con --max 4 y esperas de 55 min
    un job dura tres horas, y en ese hueco otra ejecución arranca con un
    checkout que todavía no tiene estos hilos, elige las mismas piezas y las
    republica. Pasó el 28 de agosto: cuatro hilos salieron dos veces porque la
    ejecución programada de las 05:36 esperó en el grupo de concurrencia, entró
    con el árbol de antes y no vio lo que la anterior llevaba publicado.

    El grupo de concurrencia impide que corran a la vez, no que la segunda
    empiece con datos viejos. Lo único que lo impide es publicar el registro en
    cuanto existe.
    """
    for orden in (["add", str(ruta)],
                  ["commit", "-m", f"hilo: {pieza_id}"],
                  ["pull", "--rebase", "--autostash", "origin", "HEAD"],
                  ["push", "origin", "HEAD"]):
        r = subprocess.run(["git", *orden], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0 and orden[0] not in ("commit",):
            print(f"    ! git {orden[0]}: {r.stderr.strip()[:120]}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=1, metavar="N",
                    help="cuántos hilos como máximo en esta ejecución")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    for n in range(max(a.max, 1)):
        ahora = datetime.now(timezone.utc)
        motivo = puede_publicar(ahora)
        if motivo:
            print(f"  · aún no toca: {motivo}")
            return 0

        cola = candidatas()
        if not cola:
            print("no hay nada en el archivo que publicar")
            return 0
        ruta, u = cola[0]

        texto = variants.build(u, "threads")["text"]
        anterior = _cuando(u)
        marca = "reemitida" if anterior else "inédita en Threads"
        print(f"\n▶ {u['id']} · {(u.get('core') or {}).get('subject', '')[:50]} · {marca}")
        print(f"  {len(texto)} car.")
        if a.dry_run:
            print("  · dry-run: no se publica nada")
            return 0

        # Threads publica texto con enlace: no necesita imagen. El adaptador pide
        # image_url por firma, pero un hilo de solo texto es lo que rinde ahí.
        res = meta.publish_threads(None, texto)
        res["published_at"] = ahora.isoformat()
        u.setdefault("results", {})["threads"] = res
        ruta.write_text(json.dumps(u, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  ✓ threads: {res.get('post_id')}")
        _registrar(ruta, u["id"])

        if n + 1 < max(a.max, 1):
            print(f"  · esperando {MINUTOS_ENTRE_HILOS} min")
            time.sleep(MINUTOS_ENTRE_HILOS * 60 + 30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
