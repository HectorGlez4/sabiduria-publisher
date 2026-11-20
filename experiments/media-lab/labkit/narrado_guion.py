"""
Guion de un reel narrado: esquema y validador.

Un guion es `{"pieza": id, "diseno": "papel|tinta|siena", "escenas": [...]}`. Cada escena lleva
`tipo`, `voz` (lo que se dice) y `pantalla` (lo que se ve, según el tipo). Los años van en cifras
en `voz` ("en 1888"); quien sintetiza la voz los expande.

`validar` devuelve todos los problemas, no el primero; una lista vacía es un guion válido. Lo que
dice la voz no puede traer nada que la pieza no contenga: ningún año ni nombre propio nuevo.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

TIPOS = ("tachado", "cita", "nombre_ano", "contraste", "pregunta")
DISENOS = ("papel", "tinta", "siena")
MIN_ESCENAS, MAX_ESCENAS = 5, 7

CAMPOS = {
    "tachado": ("etiqueta", "nombre"),
    "cita": ("texto",),
    "nombre_ano": ("etiqueta", "nombre", "ano"),
    "contraste": ("claro", "oscuro"),
    "pregunta": ("texto",),
}
OPCIONALES = {"nombre_ano": ("nota",)}

_COMILLAS = "\"'«»“”‘’„‟`´"
_PALABRA = re.compile(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+")
_INICIO_FRASE = re.compile(r"(?:^|[.!?…¿¡:]\s*)$")


def cargar(ruta: Path) -> dict:
    ruta = Path(ruta)
    try:
        guion = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{ruta}: JSON ilegible ({e})") from e
    if not isinstance(guion, dict):
        raise ValueError(f"{ruta}: el guion debe ser un objeto JSON")
    return guion


def _texto_pieza(pieza: dict) -> str:
    core = pieza.get("core", {})
    quote = core.get("quote") or {}
    partes = [core.get("hook", ""), *(core.get("body") or []), core.get("question", ""),
              quote.get("text", ""), quote.get("author", "")]
    return "\n".join(p for p in partes if isinstance(p, str))


def _normalizar_cita(texto: str) -> str:
    return " ".join(str(texto).strip(_COMILLAS + " \t\n").split())


def nombres_propios(voz: str) -> list[str]:
    """Palabras con mayúscula que no abren frase."""
    salida = []
    for m in _PALABRA.finditer(voz):
        palabra = m.group()
        if not palabra[0].isupper() or palabra.isdigit():
            continue
        if _INICIO_FRASE.search(voz[:m.start()]):
            continue
        salida.append(palabra)
    return salida


def _aparece(termino: str, texto: str) -> bool:
    """El término está en el texto como palabra o número completos, no como parte de otro."""
    return re.search(rf"(?<!\w){re.escape(termino)}(?!\w)", texto) is not None


def _problemas_pantalla(i: int, tipo: str, pantalla: dict, texto_pieza: str) -> list[str]:
    cual = f"escena {i} ({tipo})"
    problemas = []
    nombre = pantalla.get("nombre")
    if isinstance(nombre, str):
        for palabra in dict.fromkeys(m.group() for m in _PALABRA.finditer(nombre)
                                     if m.group()[0].isupper()):
            if not _aparece(palabra, texto_pieza):
                problemas.append(f"{cual}: pantalla.nombre {palabra} no aparece en la pieza")
    ano = pantalla.get("ano")
    if isinstance(ano, str):
        for numero in re.findall(r"\d+", ano):
            if not _aparece(numero, texto_pieza):
                problemas.append(f"{cual}: pantalla.ano {numero} no aparece en la pieza")
    return problemas


def _problemas_voz(i: int, voz: str, texto_pieza: str, prohibidos: list[str]) -> list[str]:
    cual = f"escena {i}"
    if not isinstance(voz, str) or not voz.strip():
        return [f"{cual}: voz vacía"]
    problemas = []
    for numero in re.findall(r"(?<!\d)\d{3,4}(?!\d)", voz):
        if not _aparece(numero, texto_pieza):
            problemas.append(f"{cual}: el año {numero} no aparece en la pieza")
    for nombre in dict.fromkeys(nombres_propios(voz)):
        if not _aparece(nombre, texto_pieza):
            problemas.append(f"{cual}: el nombre {nombre} no aparece en la pieza")
    bajo = voz.lower()
    for termino in prohibidos:
        if isinstance(termino, str) and termino.strip() and termino.lower() in bajo:
            problemas.append(f"{cual}: la voz usa «{termino}», que la pieza tiene en do_not_use")
    return problemas


def validar(guion: dict, pieza: dict, es_falsa_atribucion: bool) -> list[str]:
    if not isinstance(guion, dict):
        return ["el guion debe ser un objeto"]
    problemas: list[str] = []
    if guion.get("diseno") not in DISENOS:
        problemas.append(f"diseno {guion.get('diseno')!r} desconocido (uno de {', '.join(DISENOS)})")
    escenas = guion.get("escenas")
    if not isinstance(escenas, list):
        return problemas + ["escenas debe ser una lista"]
    if not MIN_ESCENAS <= len(escenas) <= MAX_ESCENAS:
        problemas.append(f"debe haber entre {MIN_ESCENAS} y {MAX_ESCENAS} escenas, hay {len(escenas)}")

    texto_pieza = _texto_pieza(pieza)
    prohibidos = pieza.get("do_not_use") or []
    quote = ((pieza.get("core") or {}).get("quote") or {}).get("text", "")
    tipos = []
    for i, e in enumerate(escenas, 1):
        if not isinstance(e, dict):
            problemas.append(f"escena {i}: debe ser un objeto")
            tipos.append(None)
            continue
        tipo = e.get("tipo")
        tipos.append(tipo)
        if tipo not in TIPOS:
            problemas.append(f"escena {i}: tipo {tipo!r} desconocido (uno de {', '.join(TIPOS)})")
        problemas += _problemas_voz(i, e.get("voz"), texto_pieza, prohibidos)
        if tipo not in TIPOS:
            continue
        pantalla = e.get("pantalla")
        if not isinstance(pantalla, dict):
            problemas.append(f"escena {i} ({tipo}): falta pantalla")
            continue
        for campo in CAMPOS[tipo]:
            if not isinstance(pantalla.get(campo), str) or not pantalla[campo].strip():
                problemas.append(f"escena {i} ({tipo}): falta pantalla.{campo}")
        permitidos = CAMPOS[tipo] + OPCIONALES.get(tipo, ())
        for campo in pantalla:
            if campo not in permitidos:
                problemas.append(f"escena {i} ({tipo}): pantalla.{campo} no existe en este tipo")
        if tipo in ("tachado", "nombre_ano"):
            problemas += _problemas_pantalla(i, tipo, pantalla, texto_pieza)
        if tipo == "cita" and isinstance(pantalla.get("texto"), str):
            if _normalizar_cita(pantalla["texto"]) != _normalizar_cita(quote):
                problemas.append(f"escena {i}: el texto de la cita difiere de core.quote.text")
        if tipo == "tachado" and not es_falsa_atribucion:
            problemas.append(f"escena {i}: tachado solo se usa en falsas atribuciones")

    if "cita" not in tipos:
        problemas.append("falta la escena cita")
    if "pregunta" not in tipos:
        problemas.append("falta la escena pregunta")
    elif tipos[-1] != "pregunta" or tipos.count("pregunta") > 1:
        problemas.append("la pregunta debe ser la última escena, y única")
    return problemas
