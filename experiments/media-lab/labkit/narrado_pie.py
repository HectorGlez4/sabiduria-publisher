"""
El pie del reel narrado en Instagram. Puro: recibe la pieza publicada y devuelve el texto.

Gancho, línea en blanco, pregunta, línea en blanco, etiquetas como hashtags, línea en blanco y
«Voz sintética». Sin URL y como mucho 2200 caracteres (el límite de Instagram).
"""
from __future__ import annotations

import re

LIMITE = 2200
MAX_HASHTAGS = 12  # el de Instagram en src/variants.py (LIMITS["instagram"]["max_tags"])
PRINCIPAL = "#SabiduriaDeBolsillo"
FIRMA_VOZ = "Voz sintética"
_URL = re.compile(r"https?://|www\.", re.IGNORECASE)


def hashtags(pieza: dict) -> list[str]:
    """La principal, las del tema y las extendidas, en ese orden, sin repetir (sin distinguir
    mayúsculas), con «#» delante y como mucho MAX_HASHTAGS."""
    t = pieza.get("tags") or {}
    todas = [t.get("primary") or PRINCIPAL, *(t.get("topic") or []), *(t.get("extended") or [])]
    vistas, fuera = set(), []
    for etiqueta in todas:
        limpia = "".join(str(etiqueta).split()).lstrip("#")
        if limpia and limpia.lower() not in vistas:
            vistas.add(limpia.lower())
            fuera.append(f"#{limpia}")
    return fuera[:MAX_HASHTAGS]


def pie(pieza: dict) -> str:
    """El pie del reel. ValueError si falta el gancho o la pregunta, si lleva una URL o si pasa de LIMITE."""
    core = pieza.get("core") or {}
    gancho = (core.get("hook") or "").strip()
    pregunta = (core.get("question") or "").strip()
    if not gancho:
        raise ValueError(f"la pieza {pieza.get('id')} no tiene gancho: no hay pie")
    if not pregunta:
        raise ValueError(f"la pieza {pieza.get('id')} no tiene pregunta: no hay pie")
    texto = "\n\n".join([gancho, pregunta, " ".join(hashtags(pieza)), FIRMA_VOZ])
    if _URL.search(texto):
        raise ValueError(f"el pie de {pieza.get('id')} lleva una URL: el reel no enlaza a nada")
    if len(texto) > LIMITE:
        raise ValueError(f"el pie de {pieza.get('id')} mide {len(texto)} caracteres, más de {LIMITE}")
    return texto
