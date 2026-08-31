#!/usr/bin/env python3
"""
Coloca un borrador de contenido en la cola, calculando turno, hora y variante.

La división es deliberada. La investigación —que es lo que las tareas de Cowork
hacen bien— produce SOLO contenido verificado: el texto, las fuentes y los
descartes. Todo lo que hay que llevar en la cabeza y es fácil de equivocar lo
calcula este script:

  · el turno libre siguiente, sin pisar nada
  · la hora base de la franja más un jitter de 5 a 50 minutos
  · la variante cream/gold, alternando contra la ÚLTIMA PUBLICACIÓN REAL

Esa última línea es el motivo de que esto exista. La alternancia ya se calculó
mal una vez, contra la entrada anterior de la cola en vez de contra lo
publicado, y hubo que reescribir 39 entradas para arreglarlo. Un LLM no debería
tener que llevar esa cuenta; un contador determinista sí.

    python3 scripts/programar.py borrador.json
    python3 scripts/programar.py borrador.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import publish, variants  # noqa: E402

# Hora base de cada franja, en UTC. De linea-editorial.md: 08:00 / 13:00 / 19:30
# de CDMX (UTC-6). La de noche cae en el día siguiente en UTC.
BASE = {"manana": (14, 0, 0), "tarde": (19, 0, 0), "noche": (1, 30, 1)}
ORDEN = ["manana", "tarde", "noche"]
JITTER_MIN, JITTER_MAX = 5, 50


def cadena() -> list[dict]:
    """Todo lo publicado y lo encolado, en orden de tiempo."""
    c = list(publish.load_history())
    c += [publish.load(f) for f in publish.QUEUE.glob("*.json")]
    c.sort(key=lambda u: u.get("publish_at") or "")
    return c


def instante(fecha: str, franja: str) -> str:
    """Hora base de la franja más jitter. Nunca el mismo minuto dos días seguidos."""
    h, m, mas_dias = BASE[franja]
    base = datetime.fromisoformat(fecha).replace(
        hour=h, minute=m, tzinfo=timezone.utc) + timedelta(days=mas_dias)
    return (base + timedelta(minutes=random.randint(JITTER_MIN, JITTER_MAX))
            ).strftime("%Y-%m-%dT%H:%M:00Z")


def siguiente_turno(ahora: datetime) -> tuple[str, str, str]:
    """
    Primer turno libre cuya hora esté en el FUTURO.

    Lo de 'en el futuro' no es un detalle. Sin ello elegía la franja de mañana
    del propio día, que ya había pasado, y la pieza aterrizaba ANTES de la
    última publicación real: entonces la variante se calculaba contra la pieza
    equivocada y todo lo demás salía torcido.
    """
    tomados = {f.stem for f in publish.QUEUE.glob("*.json")}
    if publish.PUBLISHED.exists():
        tomados |= {f.stem for f in publish.PUBLISHED.glob("*.json")}

    dia = ahora.date()
    for _ in range(120):
        for franja in ORDEN:
            pid = f"{dia.isoformat()}-{franja}"
            if pid in tomados:
                continue
            cuando = instante(dia.isoformat(), franja)
            if datetime.fromisoformat(cuando.replace("Z", "+00:00")) > ahora:
                return dia.isoformat(), franja, cuando
        dia += timedelta(days=1)
    raise RuntimeError("no queda hueco en 120 días")


def variante_para(cuando: str) -> str:
    """
    Alterna contra el ORIGINAL ANTERIOR en el tiempo, no contra el final de la
    cola: así da igual que la pieza se añada al final o rellene un hueco.

    Si hay vecino posterior se comprueba que tampoco choque con él. Cuando los
    dos vecinos llevan la misma variante el hueco es irrellenable sin romper la
    cadena, y más vale decirlo que dejar el problema escondido.
    """
    # Las reemisiones NO cuentan como referencia, igual que en
    # variants._problemas_de_historial. Estan exentas de alternar —salen con el
    # resto de reglas de historial— y dejarlas fijar la referencia rompia este
    # script contra el preflight: aqui se alternaba contra el vecino temporal,
    # que con el ritmo agresivo casi siempre es una reemision, y alli contra la
    # ultima ORIGINAL. Las dos daban variantes distintas, asi que programar.py
    # escribia una variante que publish.py rechazaba despues. Bloqueaba TODA
    # pieza nueva, no una: el 31 de agosto no se podia encolar nada.
    c = [u for u in cadena() if not u.get("reemision_de")]
    antes = [u for u in c if (u.get("publish_at") or "") < cuando]
    despues = [u for u in c if (u.get("publish_at") or "") > cuando]

    if not antes:
        elegida = "cream"
    else:
        previa = (antes[-1].get("card") or {}).get("variant")
        elegida = "gold" if previa == "cream" else "cream"

    if despues and (despues[0].get("card") or {}).get("variant") == elegida:
        print(f"  ⚠ el hueco queda entre dos '{elegida}': no se puede alternar "
              "sin romper la cadena. Revisa la cola.")
    return elegida


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("borrador", help="JSON con el contenido verificado")
    ap.add_argument("--fecha", help="forzar fecha AAAA-MM-DD")
    ap.add_argument("--franja", choices=ORDEN, help="forzar franja")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    u = json.loads(pathlib.Path(a.borrador).read_text(encoding="utf-8"))

    faltan = [c for c in ("core", "sources") if not u.get(c)]
    if faltan:
        sys.exit(f"al borrador le falta: {', '.join(faltan)}")
    if not u.get("card"):
        sys.exit("al borrador le falta 'card' (renderer y textos de la tarjeta)")

    if a.fecha and a.franja:
        fecha, franja = a.fecha, a.franja
        cuando = instante(fecha, franja)
    else:
        fecha, franja, cuando = siguiente_turno(datetime.now(timezone.utc))

    u["id"] = f"{fecha}-{franja}"
    u["slot"] = franja
    u["publish_at"] = cuando
    u["card"]["variant"] = variante_para(cuando)
    u.setdefault("targets", ["facebook", "instagram"])
    u.setdefault("results", {})
    u.setdefault("tags", {"primary": "#SabiduriaDeBolsillo", "topic": [], "extended": []})
    u["status"] = "ready"

    # Se juzga en SU turno, con la cadena completa por delante: es lo mismo que
    # hace el ensayo, y responde a la pregunta util (¿pasara cuando le toque?).
    historial = publish.load_history()
    for p in sorted(publish.QUEUE.glob("*.json")):
        otra = publish.load(p)
        if (otra.get("publish_at") or "") < u["publish_at"]:
            otra = dict(otra)
            otra["results"] = {"_simulado": {"published_at": otra.get("publish_at")}}
            historial.append(otra)

    problemas = variants.preflight(u, historial)
    print(f"\n{u['id']}  ·  {u['slot']}  ·  {u['card']['variant']}")
    print(f"  publish_at: {u['publish_at']}")
    print(f"  tema:       {u['core'].get('subject', '')[:60]}")
    print(f"  fuentes:    {len(u.get('sources') or [])}   descartes: {len(u.get('do_not_use') or [])}")

    if problemas:
        print("\n  ✗ no pasa las comprobaciones previas:")
        for p in problemas:
            print(f"      - {p}")
        return 1
    print("  ✓ pasa las comprobaciones previas")

    if a.dry_run:
        print("\ndry-run: no se ha escrito nada")
        return 0

    destino = publish.QUEUE / f"{u['id']}.json"
    publish.save(u, destino)
    print(f"\nescrita en {destino.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
