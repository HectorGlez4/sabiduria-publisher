"""
Pronunciación de un reel narrado y compuerta de aprobación de nombres.

`para_la_voz` reescribe la `voz` de una escena para el sintetizador: los números en cifras (0–2999)
pasan a palabras y los nombres propios a su forma hablada (`dicho`). La tabla
(`narrados/pronunciacion.json`) es `{"Nietzsche": {"dicho": "Niche", "aprobado_por": "", "fecha": ""}}`.
Una entrada solo cuenta cuando `aprobado_por` no está vacío: aprobar es un paso humano, nunca se
rellena por código. `dicho` igual al nombre escrito es válido (aprobado tal cual). Los años no
necesitan entrada: `numero_en_palabras` es determinista.
"""
from __future__ import annotations

import re

from .narrado_guion import _PALABRA, nombres_propios

_UNIDADES = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
             "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
             "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
             "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve")
_DECENAS = ("", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
_CENTENAS = ("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos",
             "setecientos", "ochocientos", "novecientos")
_NUMERO = re.compile(r"(?<!\w)\d+(?!\w)")


def _menor_de_mil(n: int) -> str:
    if n == 100:
        return "cien"
    centenas, resto = divmod(n, 100)
    partes = [_CENTENAS[centenas]] if centenas else []
    if resto < 30:
        if resto or not centenas:
            partes.append(_UNIDADES[resto])
    else:
        decena, unidad = divmod(resto, 10)
        partes.append(_DECENAS[decena] + (f" y {_UNIDADES[unidad]}" if unidad else ""))
    return " ".join(partes)


def numero_en_palabras(n: int) -> str:
    """El número en español hablado, de 0 a 2999."""
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 2999:
        raise ValueError(f"número fuera de 0–2999: {n!r}")
    miles, resto = divmod(n, 1000)
    partes = []
    if miles:
        partes.append("mil" if miles == 1 else f"{_UNIDADES[miles]} mil")
    if resto or not miles:
        partes.append(_menor_de_mil(resto))
    return " ".join(partes)


def nombres(voz: str, tabla: dict | None = None) -> list[str]:
    """Nombres propios de la voz: con mayúscula y sin abrir frase, más los que abren frase y están en la tabla."""
    tabla = tabla or {}
    encontrados = list(nombres_propios(voz))
    for m in _PALABRA.finditer(voz):
        if m.group() in tabla and m.group() not in encontrados:
            encontrados.append(m.group())
    return encontrados


def _aprobado(tabla: dict, nombre: str) -> bool:
    entrada = tabla.get(nombre)
    return isinstance(entrada, dict) and bool(str(entrada.get("aprobado_por", "")).strip())


def pendientes(guion: dict, tabla: dict) -> list[str]:
    """Nombres de las voces del guion sin entrada aprobada, ordenados y sin repetir."""
    todos = set()
    for escena in guion.get("escenas", []):
        voz = escena.get("voz") if isinstance(escena, dict) else None
        if isinstance(voz, str):
            todos.update(nombres(voz, tabla))
    return sorted(n for n in todos if not _aprobado(tabla, n))


def para_la_voz(voz: str, tabla: dict) -> str:
    """La voz lista para el sintetizador: cifras en palabras y nombres aprobados en su forma hablada."""
    def numero(m: re.Match) -> str:
        n = int(m.group())
        return numero_en_palabras(n) if n <= 2999 else m.group()

    def nombre(m: re.Match) -> str:
        return str(tabla[m.group()].get("dicho") or m.group()) if _aprobado(tabla, m.group()) else m.group()

    return _PALABRA.sub(nombre, _NUMERO.sub(numero, voz))
