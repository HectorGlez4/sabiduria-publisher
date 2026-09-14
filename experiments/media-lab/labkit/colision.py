"""
¿Toca esperar por producción?

La regla es la del propio publicador cuando recupera atrasos: 21 minutos entre
dos piezas. Además, mientras `publicar` o `hilos` están subiendo no sale nada del
laboratorio, y una pieza atrasada en la cola cuenta como inminente: el reloj de
GitHub la puede disparar en cualquier momento.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEPARACION = timedelta(minutes=21)
WORKFLOWS_PRODUCCION = ("publicar", "hilos")
ROOT = Path(__file__).resolve().parents[3]


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def motivo_espera(ahora: datetime, *, programadas: list[datetime], publicadas: list[datetime],
                  en_curso: list[str]) -> str | None:
    activos = sorted({w for w in en_curso if w in WORKFLOWS_PRODUCCION})
    if activos:
        return f"producción subiendo: {', '.join(activos)}"
    for t in sorted(publicadas, reverse=True):
        if timedelta(0) <= ahora - t < SEPARACION:
            return f"producción publicó hace {int((ahora - t).total_seconds() // 60)} min"
    for t in sorted(programadas):
        falta = t - ahora
        if falta <= timedelta(0):
            return f"producción atrasada desde {t:%H:%M} UTC: puede salir en cualquier momento"
        if falta < SEPARACION:
            return f"producción publica en {int(falta.total_seconds() // 60)} min"
    return None


def programadas_de_cola(cola: Path) -> list[datetime]:
    fuera = []
    for p in cola.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("status") == "ready" and d.get("publish_at"):
            fuera.append(_dt(d["publish_at"]))
    return sorted(fuera)


def publicadas_recientes(publicados: Path, ahora: datetime, horas: int = 3) -> list[datetime]:
    desde = ahora - timedelta(hours=horas)
    fuera = []
    for p in publicados.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in (d.get("results") or {}).values():
            t = (r or {}).get("published_at") if isinstance(r, dict) else None
            if t:
                cuando = _dt(t)
                if desde <= cuando <= ahora:
                    fuera.append(cuando)
    return sorted(fuera)


def workflows_en_curso() -> list[str]:
    nombres: list[str] = []
    for estado in ("in_progress", "queued"):
        r = subprocess.run(["gh", "run", "list", "--status", estado, "--limit", "20", "--json", "name"],
                           cwd=ROOT, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"gh run list falló: {r.stderr.strip()[:300]}")
        nombres += [x["name"] for x in json.loads(r.stdout)]
    return nombres
