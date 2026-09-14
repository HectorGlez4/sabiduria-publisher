"""
Lectura pura de las pantallas de Instagram: perfil, selector, editor, compositor y
envío.

Nada de aquí toca el teléfono ni el reloj: recibe volcados (XML de uiautomator) y
devuelve lo que dicen, o lanza PantallaInesperada si un control es ambiguo. Los pasos
con E/S viven en `instagram_feed`, que reexporta todo lo de `__all__` para no romper
a quien ya importa desde allí.

Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from labkit import telefono

__all__ = [
    "PAQUETE", "MARCA", "ZONA_LOCAL", "CLASES_CAMPO", "MARCAS_FALLO", "ZONA_AVISO_PX", "MARGEN_BANNER_PX",
    "LARGO_AVISO_CORTO", "PantallaInesperada", "banners_de_volcado",
    "perfil_activo", "publicaciones_de_perfil", "fecha_miniatura", "seleccion_unica", "miniatura_coincide",
    "hay_desplegable_hashtags", "punto_mas", "tema_de_chip", "campo_pie", "partager_pulsable",
    "compositor_listo", "observacion_de_volcado", "evaluar_envio",
    "_es_textview", "_dice", "_area", "_campos", "_elegir", "_coincidencias", "_nodo", "_suivant",
    "_tiene_pie", "_exigir_compositor_con_pie",
]

PAQUETE = "com.instagram.android"
MARCA = "sabiduriabolsillo"
ZONA_LOCAL = ZoneInfo("Europe/Madrid")
CLASES_CAMPO = ("android.widget.AutoCompleteTextView", "android.widget.EditText")
MARCAS_FALLO = ("Réessayer", "Impossible de publier", "n’a pas pu", "n'a pas pu")
# El aviso de subida sale arriba del inicio: un texto de fallo solo cuenta con el borde
# inferior a esta altura o menos, o cerca del propio banner «Publication sur…».
ZONA_AVISO_PX = 600
MARGEN_BANNER_PX = 250
# Un texto de fallo así de corto cuenta en cualquier sitio: los pies de otras cuentas son largos.
LARGO_AVISO_CORTO = 80
_MESES = {"janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
          "juillet": 7, "aout": 8, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
          "decembre": 12, "décembre": 12}
_FECHA = re.compile(r"\bdu\s+(\d{1,2})(?:er)?\s+(\S+)\s+(\d{4})\s+(\d{1,2})[:h](\d{2})\b")
_PUBLICACIONES = re.compile(r"\s*(\d[\d \u00a0\u202f]*?)[\s\u00a0\u202f]*publications?\s*")


class PantallaInesperada(RuntimeError):
    pass


def _es_textview(n: dict) -> bool:
    return n["clase"].endswith("TextView") and n["clase"] not in CLASES_CAMPO


def _dice(n: dict, valor: str) -> bool:
    return valor in (n["texto"], n["desc"])


def _area(n: dict) -> int:
    x1, y1, x2, y2 = n["bounds"]
    return (x2 - x1) * (y2 - y1)


# --- Perfil y selector ---------------------------------------------------------

def perfil_activo(xml: str) -> str | None:
    """Título de la barra superior del perfil (TextView de Instagram con el borde
    inferior a 260 px o menos y el centro horizontal entre 300 y 780). None si no hay
    o si hay más de un texto distinto."""
    candidatos = {n["texto"] for n in telefono.buscar_todos(xml, paquete=PAQUETE)
                  if _es_textview(n) and n["texto"] and n["bounds"][3] <= 260
                  and 300 <= n["centro"][0] <= 780}
    return candidatos.pop() if len(candidatos) == 1 else None


def publicaciones_de_perfil(xml: str) -> int | None:
    """Número de publicaciones del content-desc «3 712publications» (el separador de
    miles puede ser espacio, espacio duro o espacio fino). None si falta o si hay
    cifras distintas."""
    cifras = set()
    for n in telefono.buscar_todos(xml, paquete=PAQUETE):
        m = _PUBLICACIONES.fullmatch(n["desc"])
        if m:
            cifras.add(int(re.sub(r"\D", "", m.group(1))))
    return cifras.pop() if len(cifras) == 1 else None


def fecha_miniatura(desc: str) -> datetime | None:
    """Fecha de «… du 14 septembre 2026 10:39» (hora local de Madrid) en UTC."""
    m = _FECHA.search(desc)
    if not m:
        return None
    dia, mes, anio, hora, minuto = m.groups()
    numero_mes = _MESES.get(mes.lower())
    if numero_mes is None:
        return None
    try:
        local = datetime(int(anio), numero_mes, int(dia), int(hora), int(minuto), tzinfo=ZONA_LOCAL)
    except ValueError:
        return None
    return local.astimezone(timezone.utc)


def seleccion_unica(xml: str) -> dict | None:
    """La única miniatura seleccionada del selector; None si hay cero o varias."""
    sel = telefono.buscar_todos(xml, empieza="Sélectionné Miniature", paquete=PAQUETE)
    sel = [n for n in sel if n["desc"].startswith("Sélectionné Miniature")]
    return sel[0] if len(sel) == 1 else None


def miniatura_coincide(desc: str, subido_en: datetime, tolerancia_min: int = 3) -> bool:
    """La miniatura lleva la hora de la subida (precisión de minuto, con tolerancia)."""
    fecha = fecha_miniatura(desc)
    if fecha is None or subido_en.tzinfo is None:
        return False
    return abs(fecha - subido_en) <= timedelta(minutes=tolerancia_min)


# --- Editor y compositor ---------------------------------------------------------

def hay_desplegable_hashtags(xml: str, paquete: str | None = None) -> bool:
    """Sugerencias de hashtags abiertas: un texto que empieza por # fuera del campo del
    pie. Sin `paquete` se miran todos los nodos (ante la duda, se da por abierto); con
    `paquete`, solo los de esa aplicación."""
    return any(n["texto"].startswith("#") and not n["clase"].endswith(("AutoCompleteTextView", "EditText"))
               for n in telefono.buscar_todos(xml, paquete=paquete))


def punto_mas(bounds: tuple[int, int, int, int]) -> tuple[int, int]:
    """El «+» del chip de audio: a la derecha, en su tercio superior (medido el 2026-09-14)."""
    x1, y1, x2, y2 = bounds
    x, y = x2 - 59, y1 + round((y2 - y1) * 0.33)
    if not (x1 < x < x2 and y1 < y < y2):
        raise PantallaInesperada(f"el «+» ({x},{y}) cae fuera del chip {bounds}")
    return x, y


def tema_de_chip(desc: str) -> str | None:
    """«Autumn Days par Morunas» del content-desc del chip de audio sugerido."""
    prefijo = "Audio suggéré."
    if not desc.startswith(prefijo):
        return None
    tema = desc.removeprefix(prefijo).split(". Appuyez")[0].strip()
    return tema or None


def _campos(xml: str) -> list[dict]:
    return [n for n in telefono.buscar_todos(xml, paquete=PAQUETE) if n["clase"] in CLASES_CAMPO]


def campo_pie(xml: str) -> dict | None:
    """El campo del pie de Instagram (AutoCompleteTextView o EditText)."""
    campos = _campos(xml)
    return _elegir(campos, "campo del pie") if campos else None


def partager_pulsable(xml: str) -> bool:
    """Algún «Partager» de Instagram se puede pulsar: el propio nodo es clickable y
    enabled o, si es una etiqueta, su antecesor clickable más cercano está enabled."""
    lista = telefono.nodos(xml)
    for i, n in enumerate(lista):
        if n["package"] != PAQUETE or not _dice(n, "Partager"):
            continue
        if n["clickable"]:
            if n["enabled"]:
                return True
            continue
        nivel = n["profundidad"]
        for anterior in reversed(lista[:i]):
            if anterior["profundidad"] >= nivel:
                continue
            nivel = anterior["profundidad"]
            if anterior["clickable"]:
                if anterior["enabled"] and anterior["package"] == PAQUETE:
                    return True
                break
    return False


def compositor_listo(xml: str, pie: str, tema: str | None) -> list[str]:
    """Problemas que impiden compartir; lista vacía = listo."""
    problemas = []
    if telefono.buscar(xml, texto="Nouvelle publication", paquete=PAQUETE) is None:
        problemas.append("falta «Nouvelle publication»")
    if not any(n["texto"] == pie for n in telefono.buscar_todos(xml, paquete=PAQUETE)):
        problemas.append("el pie del teléfono no coincide con el archivo")
    if tema:
        titulo = tema.split(" par ")[0]
        if not any(_es_textview(n) and n["texto"] == titulo for n in telefono.buscar_todos(xml, paquete=PAQUETE)):
            problemas.append(f"no aparece el tema «{titulo}»")
    botones = telefono.buscar_todos(xml, texto="Partager", paquete=PAQUETE)
    if not botones:
        problemas.append("no hay botón «Partager» de Instagram")
    else:
        if any(telefono.tapado(xml, b) for b in botones):
            problemas.append("«Partager» está tapado")
        if not partager_pulsable(xml):
            problemas.append("Partager no pulsable")
    if hay_desplegable_hashtags(xml):
        problemas.append("desplegable de hashtags abierto")
    return problemas


def _tiene_pie(xml: str, pie: str) -> bool:
    return any(n["texto"] == pie for n in telefono.buscar_todos(xml, paquete=PAQUETE))


def _exigir_compositor_con_pie(xml: str, pie: str) -> None:
    faltan = [k for k in ("Nouvelle publication", "Partager")
              if telefono.buscar(xml, texto=k, paquete=PAQUETE) is None]
    if not _tiene_pie(xml, pie):
        faltan.append("pie exacto")
    if faltan:
        raise PantallaInesperada(f"tras cerrar el teclado falta: {faltan}")


# --- Envío -------------------------------------------------------------------------

def _es_banner(n: dict) -> bool:
    return any(v.startswith(f"Publication sur {MARCA}") for v in (n["texto"], n["desc"]))


def banners_de_volcado(xml: str) -> list[tuple[int, int, int, int]]:
    """Bounds de los avisos «Publication sur <marca>…» de Instagram en el volcado."""
    return [n["bounds"] for n in telefono.buscar_todos(xml, paquete=PAQUETE) if _es_banner(n)]


def _junto_al_aviso(n: dict, banners: list[tuple[int, int, int, int]]) -> bool:
    """El nodo está en la zona del aviso de subida: borde inferior a ZONA_AVISO_PX o menos,
    o a MARGEN_BANNER_PX o menos (en vertical) de alguno de los bounds de banner dados."""
    _, y1, _, y2 = n["bounds"]
    if y2 <= ZONA_AVISO_PX:
        return True
    return any(y1 <= b[3] + MARGEN_BANNER_PX and y2 >= b[1] - MARGEN_BANNER_PX for b in banners)


def _es_aviso_de_fallo(n: dict, banners: list[tuple[int, int, int, int]]) -> bool:
    """Texto de fallo fuera del campo del pie que es corto (≤ LARGO_AVISO_CORTO, en
    cualquier sitio) o está junto al aviso de subida (ver `_junto_al_aviso`)."""
    if n["clase"] in CLASES_CAMPO:
        return False
    return any(any(marca in v for marca in MARCAS_FALLO)
               and (len(v) <= LARGO_AVISO_CORTO or _junto_al_aviso(n, banners))
               for v in (n["texto"], n["desc"]))


def observacion_de_volcado(xml: str, boton_bounds: tuple[int, int, int, int] | None = None,
                           banners_previos: list[tuple[int, int, int, int]] | None = None) -> dict:
    """Lo que dice un volcado tras pulsar Partager.

    - valido: hay Instagram en primer plano.
    - compositor: sigue el título «Nouvelle publication», o el «Partager» pulsado (mismos
      bounds), o el campo del pie. Otro «Partager» (el de compartir una publicación del
      inicio) no cuenta.
    - banner: «Publication sur sabiduriabolsillo…» en este volcado.
    - fallo: un aviso de error de Instagram fuera del campo del pie (texto nuestro) que es
      corto, o que está en la zona del aviso de subida: la de arriba, o junto a un banner de
      este volcado o de `banners_previos` (bounds vistos antes: el banner puede irse justo
      cuando sale el error). Un pie largo de otra cuenta más abajo no cuenta.
    - fallo_texto / fallo_bounds: texto (text o content-desc) y bounds del primer aviso que
      hizo `fallo` True; None si `fallo` es False. Para conciliar en segundos un `fallido`
      provocado por un texto corto ajeno, sin cambiar la decisión de `fallo`."""
    ig = telefono.buscar_todos(xml, paquete=PAQUETE)
    boton = boton_bounds is not None and any(
        _dice(n, "Partager") and n["bounds"] == tuple(boton_bounds) for n in ig)
    propios = [n["bounds"] for n in ig if _es_banner(n)]
    zona = propios + [tuple(b) for b in (banners_previos or [])]
    culpable = next((n for n in ig if _es_aviso_de_fallo(n, zona)), None)
    return {"valido": bool(ig),
            "compositor": any(_dice(n, "Nouvelle publication") for n in ig) or boton
            or any(n["clase"] in CLASES_CAMPO for n in ig),
            "banner": bool(propios),
            "fallo": culpable is not None,
            "fallo_texto": (culpable["texto"] or culpable["desc"]) if culpable else None,
            "fallo_bounds": culpable["bounds"] if culpable else None}


def evaluar_envio(observaciones: list[dict]) -> str:
    """Resultado de las observaciones tomadas tras pulsar, en orden. Los volcados no
    válidos no cuentan.

    - «fallido»: algún volcado válido muestra un aviso de error (manda sobre lo demás).
    - «confirmado»: se vio el banner y los dos últimos válidos no tienen ni banner ni
      compositor.
    - «sin_banner»: los dos últimos válidos no tienen compositor pero el banner no se vio.
    - «timeout» en otro caso."""
    validas = [o for o in observaciones if o["valido"]]
    if any(o.get("fallo") for o in validas):
        return "fallido"
    ultimas = validas[-2:]
    limpias = len(ultimas) == 2 and not any(o["compositor"] or o["banner"] for o in ultimas)
    if limpias and any(o["banner"] for o in validas):
        return "confirmado"
    if limpias:
        return "sin_banner"
    return "timeout"


# --- Elección de controles -------------------------------------------------------

def _elegir(coincidencias: list[dict], que: object) -> dict:
    """Una sola coincidencia útil.

    Varias valen si comparten centro o si todas caben en la primera (un contenedor y su
    botón, un botón y su etiqueta); si no, es ambiguo. Entre las válidas se devuelve la
    única clickable si hay exactamente una y, si no, la de menor área."""
    if len(coincidencias) == 1:
        return coincidencias[0]
    primera = coincidencias[0]
    x1, y1, x2, y2 = primera["bounds"]
    for n in coincidencias[1:]:
        ox1, oy1, ox2, oy2 = n["bounds"]
        dentro = ox1 >= x1 and oy1 >= y1 and ox2 <= x2 and oy2 <= y2
        if n["centro"] != primera["centro"] and not dentro:
            raise PantallaInesperada(f"ambiguo: {que} en {[c['bounds'] for c in coincidencias]}")
    pulsables = [n for n in coincidencias if n["clickable"]]
    if len(pulsables) == 1:
        return pulsables[0]
    return min(coincidencias, key=_area)


def _coincidencias(xml: str, zona: str | None = None, **kw) -> list[dict]:
    todos = telefono.buscar_todos(xml, paquete=PAQUETE, **kw)
    if zona == "arriba":
        return [n for n in todos if n["bounds"][3] <= 300]
    if zona == "abajo":
        return [n for n in todos if n["bounds"][1] >= 1900]
    if zona is not None:
        raise ValueError(f"zona desconocida: {zona}")
    return todos


def _nodo(xml: str, zona: str | None = None, **kw) -> dict:
    """El control de Instagram que coincide (en la zona, si se da). Puro: no toca el teléfono."""
    encontrados = _coincidencias(xml, zona, **kw)
    if not encontrados:
        raise PantallaInesperada(f"no aparece {kw}" + (f" en zona {zona}" if zona else ""))
    return _elegir(encontrados, kw)


def _suivant(xml: str) -> dict:
    """«Suivant» arriba si lo hay; si no, abajo."""
    if _coincidencias(xml, "arriba", texto="Suivant"):
        return _nodo(xml, "arriba", texto="Suivant")
    return _nodo(xml, "abajo", texto="Suivant")
