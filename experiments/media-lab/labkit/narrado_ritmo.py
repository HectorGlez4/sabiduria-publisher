"""
Avisos de ritmo de un reel narrado. No frenan nada: van al informe para quien escribe el guion.

Las tres reglas vienen de `ig-reel` (Jake Schincariol, instagram-agent-skill, MIT), ajustadas
a un reel sin cámara: el gancho se decide en los tres primeros segundos; una idea que se
alarga sin cambio pierde a quien mira; y la última línea que repite una palabra del gancho
hace que el bucle del Reel empalme limpio.
"""
from __future__ import annotations

import re
import unicodedata

VENTANA_GANCHO = 3.0   # segundos desde el inicio del vídeo en que la primera frase debe haber acabado
FRASE_LARGA = 5.0      # el original pide 4 s por plano; aquí cada escena mueve algo dentro, de ahí el margen
_PALABRA = re.compile(r"[a-zñ]{5,}")


def _contenido(texto: str) -> set[str]:
    plano = unicodedata.normalize("NFD", texto.lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn" or c == "̃")
    return set(_PALABRA.findall(unicodedata.normalize("NFC", plano)))


def avisos(guion: dict, tiempos: list[dict]) -> list[str]:
    """Lista de avisos legibles; vacía si el ritmo cumple las tres reglas."""
    escenas = guion["escenas"]
    salida = []
    if tiempos and tiempos[0]["fin"] > VENTANA_GANCHO:
        salida.append(f"el gancho acaba en {tiempos[0]['fin']:.1f} s; pasados {VENTANA_GANCHO:g} s el pulgar ya decidió: acórtalo")
    for i, t in enumerate(tiempos):
        dura = t["fin"] - t["inicio"]
        if dura > FRASE_LARGA:
            salida.append(f"la frase de la escena {i + 1} dura {dura:.1f} s (más de {FRASE_LARGA:g}): pártela en dos escenas")
    if len(escenas) >= 3:
        gancho = _contenido(escenas[0]["voz"]) | _contenido(escenas[1]["voz"])
        if not gancho & _contenido(escenas[-1]["voz"]):
            salida.append("la última línea no repite ninguna palabra del gancho: el bucle no empalma")
    return salida
