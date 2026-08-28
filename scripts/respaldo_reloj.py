#!/usr/bin/env python3
"""
Respaldo del reloj: dispara los workflows cuando GitHub no lo ha hecho.

    .venv/bin/python scripts/respaldo_reloj.py
    .venv/bin/python scripts/respaldo_reloj.py --dry-run

Por qué existe
──────────────
Las ejecuciones programadas de GitHub son "best effort". Entre el 26 y el 28 de
agosto pasaron de disparar cada hora clavada a huecos de diez horas, y la noche
del 27 no dispararon ni una vez en siete. El workflow figura `active`, el cron
es válido y no hay nada encolado: sencillamente no se lanzan.

Con 11 publicaciones diarias necesarias y un tope de 12, un solo día perdido
hace imposible cumplir la semana. Este script es el suelo: comprueba cuándo
corrió cada workflow por última vez y lo dispara si lleva demasiado.

NO sustituye al cron ni compite con él. Si GitHub disparó hace poco, no hace
nada: dos ejecuciones a la vez no publicarían el doble —el grupo de concurrencia
lo impide— pero sí gastarían minutos de runner para nada.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

# Cuánto se tolera sin ejecución antes de disparar, por workflow.
#
# publicar.yml corre con --max 12 y cubre ~4 h de reloj, así que esperar 2 h
# antes de intervenir no pierde nada. hilos.yml publica uno cada 55 min, así que
# se le da algo más de margen que su propio periodo.
UMBRAL_MINUTOS = {
    "publish.yml": 120,
    "hilos.yml": 90,
}


def ultima_ejecucion(workflow: str) -> datetime | None:
    r = subprocess.run(
        ["gh", "run", "list", "--workflow", workflow, "--limit", "1",
         "--json", "createdAt,status"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ! no se pudo consultar {workflow}: {r.stderr.strip()[:120]}",
              file=sys.stderr)
        return None
    filas = json.loads(r.stdout or "[]")
    if not filas:
        return None
    # Una ejecución en marcha cuenta como reciente: disparar otra encima solo
    # la dejaría esperando en el grupo de concurrencia.
    if filas[0].get("status") in ("in_progress", "queued", "waiting"):
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(filas[0]["createdAt"].replace("Z", "+00:00"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    ahora = datetime.now(timezone.utc)
    disparados = 0
    for wf, umbral in UMBRAL_MINUTOS.items():
        ultima = ultima_ejecucion(wf)
        if ultima is None:
            edad = float("inf")
            cuando = "nunca"
        else:
            edad = (ahora - ultima).total_seconds() / 60
            cuando = f"hace {edad:.0f} min"

        if edad < umbral:
            print(f"  {wf:14} {cuando} — al día, no se toca")
            continue

        print(f"  {wf:14} {cuando} — pasa de {umbral} min, se dispara")
        if a.dry_run:
            continue
        r = subprocess.run(["gh", "workflow", "run", wf],
                           capture_output=True, text=True)
        if r.returncode == 0:
            disparados += 1
            print(f"    ✓ lanzado")
        else:
            print(f"    ✗ {r.stderr.strip()[:150]}", file=sys.stderr)

    print(f"\n  {disparados} workflow(s) disparados"
          + (" (dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
