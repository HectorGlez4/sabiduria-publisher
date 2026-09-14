"""Una sola ventana a la vez: la programada y una sesión manual no se pisan."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ABANDONO = timedelta(minutes=90)


def tomar(ruta: Path, ahora: datetime, dueno: str) -> bool:
    if ruta.exists():
        try:
            desde = datetime.fromisoformat(json.loads(ruta.read_text(encoding="utf-8"))["desde"])
        except (OSError, ValueError, KeyError):
            desde = datetime.min.replace(tzinfo=timezone.utc)
        if ahora - desde < ABANDONO:
            return False
    ruta.write_text(json.dumps({"dueno": dueno, "desde": ahora.isoformat()}), encoding="utf-8")
    return True


def soltar(ruta: Path) -> None:
    ruta.unlink(missing_ok=True)
