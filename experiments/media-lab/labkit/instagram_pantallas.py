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

from labkit import pantalla, telefono
from labkit.pantalla import CLASES_CAMPO, PantallaInesperada

__all__ = [
    "PAQUETE", "MARCA", "ZONA_LOCAL", "CLASES_CAMPO", "MARCAS_FALLO", "ZONA_AVISO_PX", "MARGEN_BANNER_PX",
    "LARGO_AVISO_CORTO", "PantallaInesperada", "banners_de_volcado",
    "perfil_activo", "publicaciones_de_perfil", "fecha_miniatura", "seleccion_unica", "miniatura_coincide",
    "DESLIZAR_REFRESCO_PX", "DESLIZAR_MIN_PX", "IDS_HOJA", "IDS_CONTENEDOR_MODAL", "gesto_de_refresco",
    "hoja_abierta",
    "hay_desplegable_hashtags", "hay_desplegable_por_ventana", "emergente_desplegable", "parece_desplegable",
    "describe_emergente", "punto_mas", "tema_de_chip", "campo_pie", "partager_pulsable",
    "compositor_listo", "observacion_de_volcado", "evaluar_envio",
    "_es_textview", "_dice", "_area", "_campos", "_elegir", "_coincidencias", "_nodo", "_suivant",
    "_tiene_pie", "_exigir_compositor_con_pie",
]

PAQUETE = "com.instagram.android"
MARCA = "sabiduriabolsillo"
ZONA_LOCAL = ZoneInfo("Europe/Madrid")
MARCAS_FALLO = ("Réessayer", "Impossible de publier", "n’a pas pu", "n'a pas pu")
# El aviso de subida sale arriba del inicio: un texto de fallo solo cuenta con el borde
# inferior a esta altura o menos, o cerca del propio banner «Publication sur…».
ZONA_AVISO_PX = 600
MARGEN_BANNER_PX = 250
# Un texto de fallo así de corto cuenta en cualquier sitio: los pies de otras cuentas son largos.
LARGO_AVISO_CORTO = 80
# Tope de fallo_texto (y de lo que compartir copia a avisos): puede ser el pie de otra
# cuenta y acaba en un run de git, así que no vale la pena guardarlo entero.
LARGO_FALLO_TEXTO_COPIADO = 100
# Recorrido del «deslizar hacia abajo» que fuerza la recarga del perfil (pull-to-refresh).
DESLIZAR_REFRESCO_PX = 600
DESLIZAR_MIN_PX = 300  # tras recortar al alto del volcado, un gesto más corto no recarga: no se desliza
# Hojas y modales de Instagram (ver `hoja_abierta`): ids medidos en volcados reales del perfil, 2026-09-15.
IDS_HOJA = frozenset({"background_dimmer", "layout_container_bottom_sheet", "bottom_sheet_container"})
IDS_CONTENEDOR_MODAL = frozenset({"modal_container", "overlay_layout_container"})
_MESES = {"janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
          "juillet": 7, "aout": 8, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
          "decembre": 12, "décembre": 12}
_FECHA = re.compile(r"\bdu\s+(\d{1,2})(?:er)?\s+(\S+)\s+(\d{4})\s+(\d{1,2})[:h](\d{2})\b")
_PUBLICACIONES = re.compile(r"\s*(\d[\d \u00a0\u202f]*?)[\s\u00a0\u202f]*publications?\s*")


def _es_textview(n: dict) -> bool:
    return n["clase"].endswith("TextView") and n["clase"] not in CLASES_CAMPO


_dice = pantalla.dice
_area = pantalla.area


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


def gesto_de_refresco(xml: str) -> tuple[int, int, int, int]:
    """(x1, y1, x2, y2) del «deslizar hacia abajo» que recarga el perfil, relativo a nodos reales del volcado: x es
    el centro horizontal de «Modifier le profil»; y1, el punto medio entre el borde inferior del recuento de
    publicaciones más bajo que quede por encima del botón y el borde superior del botón (sin recuento, un alto de
    botón por encima de él); y2 baja DESLIZAR_REFRESCO_PX, sin salir del alto del volcado. Lanza
    PantallaInesperada si no hay un único «Modifier le profil» o si no queda sitio para bajar."""
    bx1, by1, bx2, by2 = _nodo(xml, contiene="Modifier le profil")["bounds"]
    filas = [n["bounds"][3] for n in telefono.buscar_todos(xml, paquete=PAQUETE)
             if _PUBLICACIONES.fullmatch(n["desc"]) and n["bounds"][3] <= by1]
    arriba = max(filas) if filas else max(0, by1 - (by2 - by1))
    alto = pantalla.alto_volcado(xml)
    x, y1 = (bx1 + bx2) // 2, (arriba + by1) // 2
    y2 = min(y1 + DESLIZAR_REFRESCO_PX, alto - 1)
    if y2 - y1 < DESLIZAR_MIN_PX:
        raise PantallaInesperada(f"no hay sitio para deslizar el perfil hacia abajo desde y={y1}: {y2 - y1} px, "
                                 f"menos de {DESLIZAR_MIN_PX} (alto {alto})")
    return x, y1, x, y2


def hoja_abierta(xml: str) -> str | None:
    """Motivo si el volcado muestra una hoja o un modal de Instagram abierto encima de la pantalla, o None. Cuenta un
    nodo de Instagram cuyo resource-id completo es `com.instagram.android:id/<nombre>` con un nombre de IDS_HOJA, o de
    IDS_CONTENEDOR_MODAL con algún descendiente. Medido en volcados reales del perfil: con la hoja «Créer» abierta
    aparecen `bottom_sheet_container`, `background_dimmer` y `layout_container_bottom_sheet` (63 descendientes); en
    reposo `modal_container` y
    `overlay_layout_container` están vacíos y no hay ninguno de los tres (`bottom_sheet_camera_container`, vacío, no
    cuenta)."""
    hojas = {f"{PAQUETE}:id/{nombre}": nombre for nombre in IDS_HOJA}
    modales = {f"{PAQUETE}:id/{nombre}": nombre for nombre in IDS_CONTENEDOR_MODAL}
    lista = telefono.nodos(xml)
    for i, n in enumerate(lista):
        if n["package"] != PAQUETE:
            continue
        rid = n["resource_id"]
        if rid in hojas:
            return f"hoja de Instagram abierta ({hojas[rid]} en {n['bounds']})"
        if rid in modales and i + 1 < len(lista) and lista[i + 1]["profundidad"] > n["profundidad"]:
            return f"modal de Instagram abierto ({modales[rid]} con contenido, en {n['bounds']})"
    return None


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
    return pantalla.hay_desplegable(xml, paquete, prefijo="#")


# Sufijo del resource-id de la fila de música en el compositor (Task 10f, medido el
# 2026-09-14). El desplegable de hashtags es una ventana aparte que uiautomator dump no
# incluye: `emergente_desplegable` la reconoce por su solape con esta fila o con
# «Partager», que sí están en el volcado.
RESOURCE_ID_MUSICA = "music_track_title"
UMBRAL_ANCHO_DESPLEGABLE = pantalla.UMBRAL_ANCHO_DESPLEGABLE
ANCHO_PANTALLA_PX = pantalla.ANCHO_PANTALLA_PX


def _fila_musica_o_partager(xml: str, paquete: str) -> list[tuple[int, int, int, int]]:
    """Bounds de la fila de música (resource-id que acaba en RESOURCE_ID_MUSICA) y de
    «Partager», de `paquete`. Puede salir vacía si el compositor no muestra ninguno."""
    nodos = telefono.buscar_todos(xml, paquete=paquete)
    return ([n["bounds"] for n in nodos if n["resource_id"].endswith(RESOURCE_ID_MUSICA)]
            + [n["bounds"] for n in nodos if _dice(n, "Partager")])


_se_solapan_verticalmente = pantalla.se_solapan_verticalmente


def emergente_desplegable(xml: str, emergentes: list[dict], paquete: str = PAQUETE) -> dict | None:
    """La primera de `emergentes` (ver `telefono.ventanas_emergentes_de`, ya filtradas a su
    paquete) que cuenta como el desplegable de hashtags abierto, o None si ninguna cuenta.
    `paquete` no filtra `emergentes` (ya vienen filtradas): solo se usa para localizar las
    referencias (fila de música o «Partager») en `xml`.

    Sin frame legible (`"frame": None`) no se puede descartar: cuenta siempre (falla
    cerrado). Con frame, cuenta si se solapa verticalmente con la fila de música o con
    «Partager»; si ninguno de los dos aparece en el volcado, cuenta cualquier emergente del
    paquete (Task 10f: el desplegable es una `PopupWindow` que `uiautomator dump` no
    incluye, así que sin referencias en el volcado no hay con qué descartarla)."""
    if not emergentes:
        return None
    return pantalla.emergente_solapada(emergentes, _fila_musica_o_partager(xml, paquete))


def hay_desplegable_por_ventana(xml: str, emergentes: list[dict], paquete: str = PAQUETE) -> bool:
    """Atajo de `emergente_desplegable(xml, emergentes, paquete) is not None`. `paquete` no
    filtra `emergentes` (ya vienen filtradas): solo se usa para localizar las referencias
    (fila de música o «Partager») en `xml`."""
    return emergente_desplegable(xml, emergentes, paquete) is not None


parece_desplegable = pantalla.parece_desplegable
describe_emergente = pantalla.describe_emergente


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
    return pantalla.pulsable(xml, etiqueta="Partager", paquete=PAQUETE)


def compositor_listo(xml: str, pie: str, tema: str | None, emergentes: list[dict] | None = None) -> list[str]:
    """Problemas que impiden compartir; lista vacía = listo.

    `emergentes` (ver `telefono.ventanas_emergentes`) detecta el desplegable de hashtags
    cuando es una ventana aparte que el volcado no muestra (Task 10f); sin él, solo se mira
    el volcado, como antes."""
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
    if hay_desplegable_hashtags(xml, paquete=PAQUETE):
        problemas.append("desplegable de hashtags abierto")
    culpable = emergente_desplegable(xml, emergentes or [])
    if culpable is not None:
        problemas.append(f"desplegable de hashtags abierto ({describe_emergente(culpable)})")
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


def _campo_de_aviso(n: dict) -> str | None:
    """El primero de (texto, desc) que contiene una marca de fallo (ver MARCAS_FALLO), no
    simplemente el que no esté vacío."""
    for v in (n["texto"], n["desc"]):
        if any(marca in v for marca in MARCAS_FALLO):
            return v
    return None


def _recortado(texto: str, limite: int = LARGO_FALLO_TEXTO_COPIADO) -> str:
    """`texto` tal cual si mide `limite` o menos; si no, recortado con «…» al final: puede
    ser el pie de otra cuenta y acaba en un run de git."""
    return texto if len(texto) <= limite else texto[:limite] + "…"


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
    - fallo_texto / fallo_bounds: el primero de (texto, content-desc) que contiene una marca
      de fallo (recortado a LARGO_FALLO_TEXTO_COPIADO caracteres) y los bounds del primer
      aviso que hizo `fallo` True; None si `fallo` es False. Para conciliar en segundos un
      `fallido` provocado por un texto corto ajeno, sin cambiar la decisión de `fallo`."""
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
            "fallo_texto": _recortado(_campo_de_aviso(culpable)) if culpable else None,
            "fallo_bounds": culpable["bounds"] if culpable else None}


evaluar_envio = pantalla.evaluar_envio


# --- Elección de controles -------------------------------------------------------

_elegir = pantalla.elegir


def _coincidencias(xml: str, zona: str | None = None, **kw) -> list[dict]:
    return pantalla.coincidencias(xml, PAQUETE, zona, **kw)


def _nodo(xml: str, zona: str | None = None, **kw) -> dict:
    """El control de Instagram que coincide (en la zona, si se da). Puro: no toca el teléfono."""
    return pantalla.nodo(xml, PAQUETE, zona, **kw)


def _suivant(xml: str) -> dict:
    """«Suivant» arriba si lo hay; si no, abajo."""
    if _coincidencias(xml, "arriba", texto="Suivant"):
        return _nodo(xml, "arriba", texto="Suivant")
    return _nodo(xml, "abajo", texto="Suivant")
