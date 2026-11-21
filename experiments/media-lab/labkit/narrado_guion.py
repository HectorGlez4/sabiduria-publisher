"""
Guion de un reel narrado: esquema y validador.

Un guion es `{"pieza": id, "diseno": "papel|tinta|siena", "escenas": [...]}`. Cada escena lleva
`tipo`, `voz` (lo que se dice) y `pantalla` (lo que se ve, según el tipo). Los años van en cifras
(«en 1888»); quien sintetiza la voz los expande. Cualquier otra cifra se escribe con letras.

`validar` devuelve todos los problemas, no el primero; una lista vacía es un guion válido. Ni la voz
ni la pantalla pueden traer nada que la pieza no contenga: ningún año ni nombre propio nuevo. La voz
de la cita es `core.quote.text` y la de la pregunta `core.question`, palabra por palabra.

Qué es un nombre (`clasificar`, la única definición, que usan también la compuerta de pronunciación,
`para_la_voz` y la ida y vuelta): una palabra con mayúscula que no abre frase. Una palabra con
mayúscula que abre frase es ordinaria si está en `FUNCIONALES`; si no, es nombre cuando aparece con
mayúscula sin abrir frase en la pieza o en el guion; si no, ordinaria cuando la pieza la trae en
minúscula; y si no, dudosa: el validador la rechaza y la compuerta la trata como nombre.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

TIPOS = ("tachado", "cita", "nombre_ano", "texto", "contraste", "pregunta")
DISENOS = ("papel", "tinta", "siena")
MIN_ESCENAS, MAX_ESCENAS = 5, 7

CAMPOS = {
    "tachado": ("etiqueta", "nombre"),
    "cita": ("texto",),
    "nombre_ano": ("etiqueta", "nombre", "ano"),
    "texto": ("texto",),
    "contraste": ("claro", "oscuro"),
    "pregunta": ("texto",),
}
OPCIONALES = {"nombre_ano": ("nota",)}

_COMILLAS = "\"'«»“”‘’„‟`´"
_PALABRA = re.compile(r"[^\W\d_]+")
_INICIO_FRASE = re.compile(r"(?:^|[.!?…¿¡:])[\s\"'«“‘(]*$")
_CIFRA = re.compile(r"\S*\d\S*")             # un trozo de texto con alguna cifra
_BORDE_IZQ, _BORDE_DER = "¿¡«\"'“‘(", ".,;:!?…»\"'”’)"
_ANO = re.compile(r"[1-9]\d{2,3}")

FUNCIONALES = frozenset("""
    el la los las lo un una unos unas al del
    este esta esto estos estas ese esa eso esos esas aquel aquella
    yo tú tu él ella ello ellos ellas se nos le mi su sus
    a con de desde en entre hacia hasta para por según sin sobre bajo
    y e o u ni pero sino aunque porque pues si que como cuando mientras
    qué quién quien cuál cual cuándo cuánto cómo dónde donde
    no sí ya hoy así también tampoco nunca siempre quizá quizás solo sólo más menos muy
    aún aun todavía ahora entonces luego después antes aquí allí bien casi
    todo toda todos todas nada nadie algo alguien cada otro otra otros otras
""".split())


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


def clave(texto: str) -> str:
    """Minúsculas, sin tildes y solo letras y dígitos: la puntuación y los espacios no cuentan."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto).lower())
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", sin_tildes)


def _abre_frase(texto: str, inicio: int) -> bool:
    return _INICIO_FRASE.search(texto[:inicio]) is not None


def textos_del_guion(guion) -> list[str]:
    """Todas las cadenas del guion: la voz y cada campo de la pantalla de cada escena."""
    textos = []
    escenas = guion.get("escenas") if isinstance(guion, dict) else None
    for e in escenas if isinstance(escenas, list) else []:
        if not isinstance(e, dict):
            continue
        if isinstance(e.get("voz"), str):
            textos.append(e["voz"])
        if isinstance(e.get("pantalla"), dict):
            textos += [v for v in e["pantalla"].values() if isinstance(v, str)]
    return textos


@dataclass(frozen=True)
class Contexto:
    """Lo que hace falta para decidir si una palabra que abre frase es nombre."""
    con_mayuscula: frozenset = frozenset()  # con mayúscula sin abrir frase, en la pieza o el guion
    minusculas: frozenset = frozenset()     # palabras que la pieza trae en minúscula


def contexto(guion=None, pieza: dict | None = None, textos: list[str] = ()) -> Contexto:
    fuentes = textos_del_guion(guion) + list(textos)
    texto_pieza = _texto_pieza(pieza) if isinstance(pieza, dict) else ""
    con_mayuscula, minusculas = set(), set()
    for texto in fuentes + [texto_pieza]:
        for m in _PALABRA.finditer(texto):
            if m.group()[0].isupper() and not _abre_frase(texto, m.start()):
                con_mayuscula.add(m.group())
    for m in _PALABRA.finditer(texto_pieza):
        if m.group()[0].islower():
            minusculas.add(m.group())
    return Contexto(frozenset(con_mayuscula), frozenset(minusculas))


def clasificar(texto: str, ctx: Contexto | None = None) -> list[tuple[str, int, str]]:
    """Cada palabra con mayúscula del texto: `(palabra, posición, clase)`, clase «nombre», «ordinaria» o
    «dudosa» según la regla del principio del módulo. Sin `ctx`, el contexto es el propio texto."""
    ctx = ctx if ctx is not None else contexto(textos=[texto])
    salida = []
    for m in _PALABRA.finditer(texto):
        w = m.group()
        if not w[0].isupper():
            continue
        if not _abre_frase(texto, m.start()):
            clase = "nombre"
        elif w.lower() in FUNCIONALES:
            clase = "ordinaria"
        elif w in ctx.con_mayuscula:
            clase = "nombre"
        elif w.lower() in ctx.minusculas:
            clase = "ordinaria"
        else:
            clase = "dudosa"
        salida.append((w, m.start(), clase))
    return salida


def nombres_propios(texto: str, ctx: Contexto | None = None) -> list[str]:
    """Las palabras que se tratan como nombre (nombres y dudosas), en orden y con repeticiones."""
    return [w for w, _, clase in clasificar(texto, ctx) if clase != "ordinaria"]


def _ano_de(trozo: str) -> tuple[str, int | None, str]:
    """`(antes, año, después)` de un trozo con cifras: la puntuación de los bordes y el año, o None si el
    núcleo no es un año que se pueda leer (un entero suelto de 3 o 4 cifras, sin cero delante y hasta 2999)."""
    nucleo = trozo.lstrip(_BORDE_IZQ)
    antes = trozo[:len(trozo) - len(nucleo)]
    nucleo = nucleo.rstrip(_BORDE_DER)
    despues = trozo[len(antes) + len(nucleo):]
    ano = int(nucleo) if _ANO.fullmatch(nucleo) and int(nucleo) <= 2999 else None
    return antes, ano, despues


def cifras(texto: str) -> list[tuple[str, int | None]]:
    """Cada trozo del texto con alguna cifra: `(trozo, año)`; `año` es None si el trozo no es un año."""
    return [(m.group(), _ano_de(m.group())[1]) for m in _CIFRA.finditer(texto)]


def anos_en_palabras(texto: str, en_palabras) -> str:
    """El texto con cada año pasado por `en_palabras`; cualquier otra cifra lanza ValueError."""
    def cambio(m: re.Match) -> str:
        antes, ano, despues = _ano_de(m.group())
        if ano is None:
            raise ValueError(f"«{m.group()}» no es un año: escribe el número con letras")
        return antes + en_palabras(ano) + despues
    return _CIFRA.sub(cambio, texto)


def _aparece(termino: str, texto: str) -> bool:
    """El término está en el texto como palabra o número completos, no como parte de otro."""
    return re.search(rf"(?<!\w){re.escape(termino)}(?!\w)", texto) is not None


def _problemas_texto(cual: str, texto: str, texto_pieza: str, prohibidos: list, ctx: Contexto) -> list[str]:
    """Los controles que pasa toda cadena del guion, de voz o de pantalla: cifras, nombres y do_not_use."""
    problemas = []
    for trozo, ano in cifras(texto):
        if ano is None:
            problemas.append(f"{cual}: «{trozo}»: escribe el número con letras (solo los años van en cifras)")
        elif not _aparece(str(ano), texto_pieza):
            problemas.append(f"{cual}: el año {ano} no aparece en la pieza")
    vistos = set()
    for w, _, clase in clasificar(texto, ctx):
        if clase == "ordinaria" or w in vistos:
            continue
        vistos.add(w)
        if clase == "dudosa":
            problemas.append(f"{cual}: «{w}» abre una frase y no está en la pieza: "
                             f"reformula la frase o usa palabras de la pieza")
        elif not _aparece(w, texto_pieza):
            problemas.append(f"{cual}: el nombre {w} no aparece en la pieza")
    bajo = texto.lower()
    for termino in prohibidos:
        if isinstance(termino, str) and termino.strip() and termino.lower() in bajo:
            problemas.append(f"{cual}: usa «{termino}», que la pieza tiene en do_not_use")
    return problemas


def _problemas_pantalla(i: int, tipo: str, pantalla: dict, texto_pieza: str, prohibidos: list,
                        ctx: Contexto) -> list[str]:
    problemas = []
    for campo, valor in pantalla.items():
        if isinstance(valor, str):
            problemas += _problemas_texto(f"escena {i} ({tipo}): pantalla.{campo}", valor, texto_pieza,
                                          prohibidos, ctx)
    nombre = pantalla.get("nombre")
    if isinstance(nombre, str):
        clases = {(w, p): c for w, p, c in clasificar(nombre, ctx)}
        for m in _PALABRA.finditer(nombre):
            if clases.get((m.group(), m.start())) != "nombre":
                problemas.append(f"escena {i} ({tipo}): pantalla.nombre solo lleva nombres de la pieza, "
                                 f"y «{m.group()}» no lo es")
    return problemas


def _problemas_voz(i: int, voz, texto_pieza: str, prohibidos: list, ctx: Contexto) -> list[str]:
    if not isinstance(voz, str) or not voz.strip():
        return [f"escena {i}: voz vacía"]
    return _problemas_texto(f"escena {i}", voz, texto_pieza, prohibidos, ctx)


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
    core = pieza.get("core") or {}
    quote = (core.get("quote") or {}).get("text", "")
    pregunta = core.get("question", "")
    ctx = contexto(guion, pieza)
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
        problemas += _problemas_voz(i, e.get("voz"), texto_pieza, prohibidos, ctx)
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
        problemas += _problemas_pantalla(i, tipo, pantalla, texto_pieza, prohibidos, ctx)
        if tipo == "cita" and isinstance(pantalla.get("texto"), str):
            if _normalizar_cita(pantalla["texto"]) != _normalizar_cita(quote):
                problemas.append(f"escena {i}: el texto de la cita difiere de core.quote.text")
        if tipo == "cita" and isinstance(e.get("voz"), str) and clave(e["voz"]) != clave(quote):
            problemas.append(f"escena {i}: la voz de la cita no dice core.quote.text palabra por palabra")
        if tipo == "pregunta":
            for que, valor in (("la voz", e.get("voz")), ("pantalla.texto", pantalla.get("texto"))):
                if isinstance(valor, str) and clave(valor) != clave(pregunta):
                    problemas.append(f"escena {i}: {que} de la pregunta no dice core.question palabra por palabra")
        if tipo == "tachado" and not es_falsa_atribucion:
            problemas.append(f"escena {i}: tachado solo se usa en falsas atribuciones")

    if "cita" not in tipos:
        problemas.append("falta la escena cita")
    if "pregunta" not in tipos:
        problemas.append("falta la escena pregunta")
    elif tipos[-1] != "pregunta" or tipos.count("pregunta") > 1:
        problemas.append("la pregunta debe ser la última escena, y única")
    return problemas
