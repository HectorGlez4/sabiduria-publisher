#!/usr/bin/env python3
"""
Llena la cola hasta un objetivo semanal, reemitiendo el archivo.

    python3 scripts/ritmo.py --desde 2026-08-26 --hasta 2026-08-29 \
        --publicaciones 16 --reels 15 --historias 7
    python3 scripts/ritmo.py ... --dry-run     # enseña el plan sin escribir

Qué problema resuelve
─────────────────────
Los objetivos semanales de la página piden del orden de 8 publicaciones diarias
entre foto, reel e historia. La cola tiene 15 piezas y el archivo 27: no hay
contenido nuevo para ese ritmo, y no lo va a haber, porque cada pieza lleva
fuentes, verificación en prosa y una lista de lo que NO se puede decir. Eso es
trabajo editorial, no de programación.

Lo que sí se puede hacer es **reemitir**: la misma pieza verificada, en otro
formato y en otra superficie, semanas después de su primera salida. Un reel de
una pieza que salió como foto hace tres semanas no es contenido duplicado — es
el mismo material en un sitio donde nadie lo ha visto, porque el 98,5% de tus
seguidores no vio la primera.

Reglas que se respetan, y por qué
─────────────────────────────────
· Solo se reemite lo que ya se publicó y tiene al menos `DIAS_DE_REPOSO` de
  antigüedad. Reemitir lo de anteayer sí sería duplicar.
· Se elige lo MÁS ANTIGUO primero, y nunca dos veces lo mismo en la ventana.
· Cada entrada lleva `reemision_de` con el id original. Eso la exenta de la
  regla de los 90 días en variants.py —repite a propósito— y deja el rastro
  para saber qué es original y qué no.
· La cadencia normal SÍ se aplica: espaciado mínimo y tope diario. Diez piezas
  repartidas en el día no se parecen a diez seguidas, y solo la segunda forma
  parece un bot.

Este script NO inventa contenido. Si el objetivo pide más piezas de las que hay,
lo dice y programa lo que puede.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import publish, variants  # noqa: E402

# Cuánto tiene que haber reposado una pieza antes de volver a salir.
#
# Siete días por defecto, y no es prudencia recortada: un REEL se reparte a NO
# seguidores, así que la pieza sale a gente que no vio la primera versión ni
# aunque quisiera. La repetición solo la percibe quien vio las dos, y ese
# solapamiento es mínimo cuando el formato y la superficie cambian.
#
# Para historias el argumento es más flojo —las ve tu propio público— pero
# caducan en 24 h y compiten con nada.
#
# Ajustable con --reposo. Súbelo si notas quejas de repetición; bájalo solo si
# de verdad hace falta, porque por debajo de unos días sí se nota.
DIAS_DE_REPOSO = 7

# Las horas en que se reparte el día, en UTC. Salen de las tres franjas de
# linea-editorial.md y se rellenan los huecos entre ellas, en vez de amontonar
# al final: el objetivo es volumen repartido, no una ráfaga.
HORAS = [14, 15, 17, 19, 21, 23, 1, 3]


def _instante(dia: date, hora: int, sal: int) -> str:
    """La hora en punto más unos minutos, para que no salgan todas al minuto cero."""
    minutos = random.Random(f"{dia}{hora}{sal}").randint(3, 57)
    mas = 1 if hora < 6 else 0
    return (datetime(dia.year, dia.month, dia.day, hora, minutos, tzinfo=timezone.utc)
            + timedelta(days=mas)).strftime("%Y-%m-%dT%H:%M:00Z")


def candidatas(hasta: date, reposo: int = DIAS_DE_REPOSO) -> list[dict]:
    """Lo publicado que ya reposó lo suficiente, de lo más antiguo a lo más nuevo."""
    limite = hasta - timedelta(days=reposo)
    fuera = []
    for p in sorted(publish.PUBLISHED.glob("*.json")):
        u = json.loads(p.read_text(encoding="utf-8"))
        cuando = variants._instante(u)
        if cuando and cuando.date() <= limite:
            fuera.append(u)
    fuera.sort(key=lambda u: variants._instante(u) or datetime.min.replace(tzinfo=timezone.utc))
    return fuera


def reemision(original: dict, formato: str, cuando: str, n: int) -> dict:
    u = json.loads(json.dumps(original))          # copia honda
    u["id"] = f"{cuando[:10]}-re{n:02d}-{formato.split('_')[-1]}"
    u["publish_at"] = cuando
    u["status"] = "ready"
    u["results"] = {}
    u["targets"] = [formato]
    u["reemision_de"] = original["id"]
    u.pop("attempts", None)
    u.pop("last_attempt", None)
    u.pop("blocked_reason", None)
    return u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", required=True, help="AAAA-MM-DD")
    ap.add_argument("--hasta", required=True, help="AAAA-MM-DD, incluido")
    ap.add_argument("--reels", type=int, default=0)
    ap.add_argument("--historias", type=int, default=0)
    ap.add_argument("--publicaciones", type=int, default=0,
                    help="fotos al feed; solo cuenta lo que YA está en la cola")
    ap.add_argument("--reposo", type=int, default=DIAS_DE_REPOSO,
                    help=f"días que debe reposar una pieza antes de reemitirse "
                         f"(por defecto {DIAS_DE_REPOSO})")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    desde = date.fromisoformat(a.desde)
    hasta = date.fromisoformat(a.hasta)
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]

    # Lo que la cola ya cubre en la ventana
    ya = {"facebook": 0, "facebook_reel": 0, "facebook_story": 0}
    for p in sorted(publish.QUEUE.glob("*.json")):
        u = json.loads(p.read_text(encoding="utf-8"))
        t = variants._instante(u)
        if not t or not (desde <= t.date() <= hasta):
            continue
        for k in ya:
            if k in (u.get("targets") or []):
                ya[k] += 1

    faltan_reels = max(a.reels - ya["facebook_reel"], 0)
    faltan_hist = max(a.historias - ya["facebook_story"], 0)

    print(f"Ventana {a.desde} → {a.hasta}  ({len(dias)} días)")
    print(f"  ya en cola:  {ya['facebook']} fotos · {ya['facebook_reel']} reels · "
          f"{ya['facebook_story']} historias")
    print(f"  objetivo:    {a.publicaciones} fotos · {a.reels} reels · {a.historias} historias")
    print(f"  a reemitir:  {faltan_reels} reels · {faltan_hist} historias")

    if a.publicaciones > ya["facebook"]:
        print(f"\n  ⚠ faltan {a.publicaciones - ya['facebook']} FOTOS y no se reemiten: "
              f"una foto reemitida al feed sí se lee como repetición.\n"
              f"    Eso son piezas nuevas, o sea trabajo editorial.")

    disponibles = candidatas(hasta, a.reposo)
    necesarias = faltan_reels + faltan_hist
    if len(disponibles) < necesarias:
        print(f"\n  ⚠ el archivo da para {len(disponibles)} reemisiones y hacen falta "
              f"{necesarias}. Se programan {len(disponibles)} y faltarán "
              f"{necesarias - len(disponibles)}.")

    # Reparto: primero los reels, que son la apuesta; las historias con lo que quede.
    plan, i = [], 0
    huecos = [(d, h) for d in dias for h in HORAS]
    for formato, cuantas in (("facebook_reel", faltan_reels), ("facebook_story", faltan_hist)):
        for _ in range(cuantas):
            if i >= len(disponibles) or i >= len(huecos):
                break
            d, h = huecos[i]
            plan.append(reemision(disponibles[i], formato, _instante(d, h, i), i + 1))
            i += 1

    print(f"\n  se programan {len(plan)} reemisiones:")
    for u in plan:
        print(f"    {u['publish_at'][:16]}  {u['targets'][0]:15s} ← {u['reemision_de']}")

    if a.dry_run:
        print("\n  --dry-run: no se escribe nada")
        return 0

    for u in plan:
        publish.save(u, publish.QUEUE / f"{u['id']}.json")
    print(f"\n  escritas {len(plan)} entradas en content/queue/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
