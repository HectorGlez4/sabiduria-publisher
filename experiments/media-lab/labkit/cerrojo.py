"""
Una sola ventana a la vez: la programada y una sesión manual no se pisan.

El dueño que ya tiene el cerrojo puede volver a tomarlo para renovarlo antes de
cada celda, y solo el dueño lo suelta. Un cerrojo ilegible, sin zona horaria
fiable o con fecha futura se trata como abandonado o se normaliza; nunca rompe.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ABANDONO = timedelta(minutes=90)
MARGEN_FUTURO = timedelta(minutes=5)
_NUNCA = datetime.min.replace(tzinfo=timezone.utc)


def _leer(ruta: Path) -> tuple[str | None, datetime]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        dueno = datos.get("dueno")
        desde = datetime.fromisoformat(datos["desde"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None, _NUNCA
    if desde.tzinfo is None:
        desde = desde.replace(tzinfo=timezone.utc)
    return dueno, desde


def tomar(ruta: Path, ahora: datetime, dueno: str) -> bool:
    if ruta.exists():
        actual, desde = _leer(ruta)
        if desde > ahora + MARGEN_FUTURO:
            desde = _NUNCA
        if actual != dueno and ahora - desde < ABANDONO:
            return False
    tmp = ruta.with_name(f".{ruta.name}.tmp")
    tmp.write_text(json.dumps({"dueno": dueno, "desde": ahora.isoformat()}), encoding="utf-8")
    os.replace(tmp, ruta)
    return True


def soltar(ruta: Path, dueno: str) -> bool:
    if not ruta.exists():
        return False
    actual, _ = _leer(ruta)
    if actual != dueno:
        return False
    ruta.unlink(missing_ok=True)
    return True
