"""
Pronunciación de un reel narrado y compuerta de aprobación de nombres.

`para_la_voz` reescribe la `voz` de una escena para el sintetizador: los años (enteros sueltos de 3 o
4 cifras, hasta 2999) pasan a palabras y los nombres propios a su forma hablada (`dicho`); cualquier
otra cifra lanza ValueError, porque el validador ya debió pararla. Qué es un nombre lo decide
`narrado_guion.clasificar`, la misma regla del validador y de la ida y vuelta.

La tabla (`narrados/pronunciacion.json`) es `{"Nietzsche": {"dicho": "Niche", "aprobado_por": "", "fecha": ""}}`.
Solo se honra una entrada cuya clave empieza por mayúscula y cuyo `dicho` no está vacío
(`problemas_de_tabla` dice cuáles no), y solo cuenta como aprobada cuando `aprobado_por` no está vacío:
aprobar es un paso humano, nunca se rellena por código. `dicho` igual al nombre escrito es válido
(aprobado tal cual). Los años no necesitan entrada: `numero_en_palabras` es determinista.
"""
from __future__ import annotations

from .narrado_guion import Contexto, anos_en_palabras, clasificar, contexto, nombres_propios

_UNIDADES = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
             "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
             "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
             "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve")
_DECENAS = ("", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
_CENTENAS = ("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos",
             "setecientos", "ochocientos", "novecientos")


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


def _honrada(tabla: dict, nombre: str) -> bool:
    entrada = tabla.get(nombre) if isinstance(tabla, dict) else None
    return (nombre[:1].isupper() and isinstance(entrada, dict) and isinstance(entrada.get("dicho"), str)
            and bool(entrada["dicho"].strip()))


def _aprobado(tabla: dict, nombre: str) -> bool:
    return _honrada(tabla, nombre) and bool(str(tabla[nombre].get("aprobado_por") or "").strip())


def problemas_de_tabla(tabla) -> list[str]:
    """Entradas que la tabla no puede honrar: clave que no empieza por mayúscula, entrada que no es un
    objeto o `dicho` vacío. Lista vacía si toda la tabla vale."""
    if not isinstance(tabla, dict):
        return ["pronunciacion.json debe ser un objeto {nombre: {dicho, aprobado_por, fecha}}"]
    problemas = []
    for clave, entrada in tabla.items():
        if not str(clave)[:1].isupper():
            problemas.append(f"«{clave}»: solo se admiten nombres que empiezan por mayúscula, "
                             f"no palabras ordinarias")
        elif not isinstance(entrada, dict):
            problemas.append(f"«{clave}»: la entrada debe ser un objeto con dicho, aprobado_por y fecha")
        elif not isinstance(entrada.get("dicho"), str) or not entrada["dicho"].strip():
            problemas.append(f"«{clave}»: el dicho está vacío")
    return problemas


def pendientes(guion: dict, tabla: dict, pieza: dict | None = None) -> list[str]:
    """Nombres de las voces del guion sin entrada aprobada, ordenados y sin repetir. Una palabra que abre
    frase y no se puede demostrar ordinaria cuenta como nombre."""
    ctx = contexto(guion, pieza)
    todos = set()
    for escena in guion.get("escenas", []):
        voz = escena.get("voz") if isinstance(escena, dict) else None
        if isinstance(voz, str):
            todos.update(nombres_propios(voz, ctx))
    return sorted(n for n in todos if not _aprobado(tabla, n))


def dicho(tabla: dict, nombre: str) -> str | None:
    """La forma hablada aprobada del nombre, o None."""
    return tabla[nombre]["dicho"] if _aprobado(tabla, nombre) else None


def para_la_voz(voz: str, tabla: dict, ctx: Contexto | None = None) -> str:
    """La voz lista para el sintetizador: años en palabras y nombres aprobados en su forma hablada.
    Cualquier cifra que no sea un año lanza ValueError."""
    partes, desde = [], 0
    for w, inicio, clase in clasificar(voz, ctx):
        forma = dicho(tabla, w) if clase != "ordinaria" else None
        if forma is not None:
            partes += [voz[desde:inicio], forma]
            desde = inicio + len(w)
    return anos_en_palabras("".join(partes) + voz[desde:], numero_en_palabras)
