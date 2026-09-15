"""
Reloj del laboratorio: el único sitio por donde pasa el tiempo de los pasos del teléfono.

Llama a `time` en cada uso, no guarda referencias: las pruebas de la fase 1 sustituyen
`time.sleep` y `time.monotonic` y siguen valiendo; las nuevas sustituyen solo este módulo.
"""
from __future__ import annotations

import time


def dormir(segundos: float) -> None:
    time.sleep(segundos)


def monotonic() -> float:
    return time.monotonic()
