"""
Feed de Instagram por teléfono, un paso por llamada.

Cada función deja una captura en la carpeta de evidencia y termina. Quien dirige
(Claude) mira la captura antes de pedir el siguiente paso: nada de pulsaciones a
ciegas. Si un control no aparece, o aparece en más de un sitio, se lanza
PantallaInesperada y no se toca nada más.

Cada paso empieza comprobando que el teléfono está listo y, si no, se detiene: nunca
lo despierta ni lo desbloquea (lo gestiona MaaS360).

Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import phone_clipboard
from labkit import telefono

PAQUETE = "com.instagram.android"
MARCA = "sabiduriabolsillo"
ATRAS, CTRL_IZQ, TECLA_A = 4, 113, 29
ESPERA_S = 25
OBSERVACION_S = 90
ZONA_LOCAL = ZoneInfo("Europe/Madrid")
CLASES_CAMPO = ("android.widget.AutoCompleteTextView", "android.widget.EditText")
_MESES = {"janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
          "juillet": 7, "aout": 8, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
          "decembre": 12, "décembre": 12}
_FECHA = re.compile(r"\bdu\s+(\d{1,2})(?:er)?\s+(\S+)\s+(\d{4})\s+(\d{1,2})[:h](\d{2})\b")
_PUBLICACIONES = re.compile(r"\s*(\d[\d \u00a0\u202f]*?)[\s\u00a0\u202f]*publications?\s*")


class PantallaInesperada(RuntimeError):
    pass


class BorradorPendiente(PantallaInesperada):
    """Instagram abrió con una publicación a medias: la resuelve una persona."""


class TelefonoNoListo(PantallaInesperada):
    """Dormido, bloqueado o sin adb. No se intenta arreglar."""


# --- Lectura pura de pantallas -----------------------------------------------

def _es_textview(n: dict) -> bool:
    return n["clase"].endswith("TextView") and n["clase"] not in CLASES_CAMPO


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


def hay_desplegable_hashtags(xml: str) -> bool:
    """Sugerencias de hashtags abiertas: un texto que empieza por # fuera del campo del
    pie. No se filtra por paquete: ante la duda, se da por abierto."""
    return any(n["texto"].startswith("#") and not n["clase"].endswith(("AutoCompleteTextView", "EditText"))
               for n in telefono.nodos(xml))


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


def campo_pie(xml: str) -> dict | None:
    """El campo del pie de Instagram (AutoCompleteTextView o EditText)."""
    campos = [n for n in telefono.buscar_todos(xml, paquete=PAQUETE) if n["clase"] in CLASES_CAMPO]
    return _elegir(campos, "campo del pie") if campos else None


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
    elif any(telefono.tapado(xml, b) for b in botones):
        problemas.append("«Partager» está tapado")
    if hay_desplegable_hashtags(xml):
        problemas.append("desplegable de hashtags abierto")
    return problemas


def observacion_de_volcado(xml: str) -> dict:
    """Lo que dice un volcado tras pulsar Partager. Sin Instagram en primer plano no es válido."""
    return {"valido": telefono.buscar(xml, paquete=PAQUETE) is not None,
            "compositor": telefono.buscar(xml, texto="Partager", paquete=PAQUETE) is not None
            or telefono.buscar(xml, texto="Nouvelle publication", paquete=PAQUETE) is not None,
            "banner": telefono.buscar(xml, empieza=f"Publication sur {MARCA}", paquete=PAQUETE) is not None}


def evaluar_envio(observaciones: list[dict]) -> str:
    """«confirmado»: se vio el banner en un volcado válido y los dos últimos válidos
    no tienen ni banner ni compositor. «sin_banner»: los dos últimos válidos no tienen
    compositor pero el banner no se vio nunca. «timeout» en otro caso. Los volcados
    no válidos no cuentan."""
    validas = [o for o in observaciones if o["valido"]]
    ultimas = validas[-2:]
    limpias = len(ultimas) == 2 and not any(o["compositor"] or o["banner"] for o in ultimas)
    if limpias and any(o["banner"] for o in validas):
        return "confirmado"
    if limpias:
        return "sin_banner"
    return "timeout"


def _elegir(coincidencias: list[dict], que: object) -> dict:
    """Una sola coincidencia útil. Varias valen si comparten centro o si todas caben en
    la primera (un botón y su etiqueta); si no, es ambiguo."""
    primera = coincidencias[0]
    x1, y1, x2, y2 = primera["bounds"]
    for n in coincidencias[1:]:
        ox1, oy1, ox2, oy2 = n["bounds"]
        dentro = ox1 >= x1 and oy1 >= y1 and ox2 <= x2 and oy2 <= y2
        if n["centro"] != primera["centro"] and not dentro:
            raise PantallaInesperada(f"ambiguo: {que} en {[c['bounds'] for c in coincidencias]}")
    return primera


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


# --- Pasos (E/S) ---------------------------------------------------------------

def _exigir_listo() -> None:
    e = telefono.estado()
    if not e["listo"]:
        raise TelefonoNoListo(f"el teléfono no está listo (no se despierta ni se desbloquea): {e}")


def _esperar_que(cumple, descripcion: str) -> str:
    """Primer volcado válido que cumple la condición, con un plazo de ESPERA_S."""
    inicio = time.monotonic()
    ultimo_error = ""
    while True:
        try:
            xml = telefono.volcado()
            if cumple(xml):
                return xml
        except telefono.TelefonoError as e:
            ultimo_error = f" (último error: {e})"
        transcurrido = time.monotonic() - inicio
        if transcurrido >= ESPERA_S:
            raise PantallaInesperada(f"no apareció {descripcion} tras {transcurrido:.1f} s{ultimo_error}")
        time.sleep(1.5)


def _esperar(zona: str | None = None, **kw) -> str:
    return _esperar_que(lambda xml: bool(_coincidencias(xml, zona, **kw)), f"{kw}")


def _volcado_fresco() -> str:
    return _esperar_que(lambda xml: True, "un volcado válido")


def abrir_nueva_publicacion(evidencia: Path, subido_en: datetime | str) -> dict:
    """Desde el perfil de la marca hasta el selector con la foto recién subida marcada."""
    if isinstance(subido_en, str):
        subido_en = datetime.fromisoformat(subido_en)
    _exigir_listo()
    telefono.lanzar(PAQUETE)
    time.sleep(4)
    xml = _esperar_que(lambda x: telefono.buscar(x, paquete=PAQUETE) is not None, "Instagram en primer plano")
    if telefono.buscar(xml, texto="Nouvelle publication", paquete=PAQUETE) or campo_pie(xml):
        raise BorradorPendiente("Instagram abrió con una publicación a medias: no se toca")
    telefono.tocar(*_nodo(xml, "abajo", texto="Profil")["centro"])
    xml = _esperar(contiene="Modifier le profil")
    perfil = perfil_activo(xml)
    if perfil != MARCA:
        raise PantallaInesperada(f"el perfil activo es {perfil!r}, no @{MARCA}")
    publicaciones_antes = publicaciones_de_perfil(xml)
    telefono.tocar(*_nodo(xml, "arriba", texto="Créer")["centro"])
    xml = _esperar(texto="Publication")
    telefono.tocar(*_nodo(xml, texto="Publication")["centro"])
    xml = _esperar(texto="Nouvelle publication")
    sel = seleccion_unica(xml)
    if sel is None:
        raise PantallaInesperada("no hay exactamente una miniatura seleccionada")
    if not miniatura_coincide(sel["desc"], subido_en):
        raise PantallaInesperada(f"la miniatura seleccionada no es la subida a las {subido_en.isoformat()}: {sel['desc']}")
    return {"captura": str(telefono.captura(evidencia / "ig-01-selector.png")),
            "publicaciones_antes": publicaciones_antes}


def alternar_recorte(evidencia: Path) -> Path:
    """Pulsa el conmutador de recorte UNA vez. El volcado no muestra si queda en 4:5
    (el contenedor mide lo mismo): quien dirige lo confirma en la captura."""
    _exigir_listo()
    xml = _esperar(texto="Modifier le rognage")
    telefono.tocar(*_nodo(xml, texto="Modifier le rognage")["centro"])
    time.sleep(2)
    return telefono.captura(evidencia / "ig-02-recorte.png")


def siguiente(evidencia: Path, nombre: str) -> Path:
    _exigir_listo()
    xml = _esperar(texto="Suivant")
    telefono.tocar(*_suivant(xml)["centro"])
    time.sleep(4)
    return telefono.captura(evidencia / f"{nombre}.png")


def anadir_audio_sugerido(evidencia: Path) -> dict:
    _exigir_listo()
    xml = _esperar(empieza="Audio suggéré.")
    chip = _nodo(xml, empieza="Audio suggéré.")
    tema = tema_de_chip(chip["desc"])
    if tema is None:
        raise PantallaInesperada(f"el chip de audio no dice qué tema es: {chip['desc']!r}")
    telefono.tocar(*punto_mas(chip["bounds"]))
    xml = _esperar(texto="Terminé")
    telefono.tocar(*_nodo(xml, texto="Terminé")["centro"])
    time.sleep(3)
    return {"tema": tema, "captura": str(telefono.captura(evidencia / "ig-03-audio.png"))}


def detalles(evidencia: Path) -> Path:
    """Del editor a la pantalla de detalles; quien dirige la mira antes de escribir el pie."""
    _exigir_listo()
    xml = _esperar(texto="Suivant")
    telefono.tocar(*_suivant(xml)["centro"])
    _esperar_que(lambda x: campo_pie(x) is not None, "el campo del pie")
    return telefono.captura(evidencia / "ig-03b-detalles.png")


def _exigir_compositor_con_pie(xml: str, pie: str) -> None:
    faltan = [k for k in ("Nouvelle publication", "Partager")
              if telefono.buscar(xml, texto=k, paquete=PAQUETE) is None]
    if not any(n["texto"] == pie for n in telefono.buscar_todos(xml, paquete=PAQUETE)):
        faltan.append("pie exacto")
    if faltan:
        raise PantallaInesperada(f"tras cerrar el teclado falta: {faltan}")


def escribir_pie(pie: str, evidencia: Path) -> Path:
    _exigir_listo()
    xml = _esperar_que(lambda x: campo_pie(x) is not None, "el campo del pie")
    telefono.tocar(*campo_pie(xml)["centro"])
    time.sleep(2)
    telefono.combinacion(CTRL_IZQ, TECLA_A)
    phone_clipboard.pegar(pie, paste=True)
    time.sleep(2)
    xml = _volcado_fresco()
    if not any(n["texto"] == pie for n in telefono.buscar_todos(xml, paquete=PAQUETE)):
        raise PantallaInesperada("el pie leído del teléfono no coincide con el archivo")
    for _ in range(2):
        if not telefono.teclado_visible() and not hay_desplegable_hashtags(xml):
            break
        telefono.tecla(ATRAS)
        time.sleep(2)
        xml = _volcado_fresco()
        _exigir_compositor_con_pie(xml, pie)
    else:
        if telefono.teclado_visible() or hay_desplegable_hashtags(xml):
            raise PantallaInesperada("el teclado o el desplegable siguen abiertos tras 2 «atrás»")
    return telefono.captura(evidencia / "ig-04-compositor.png")


def atras(evidencia: Path, nombre: str) -> Path:
    _exigir_listo()
    telefono.tecla(ATRAS)
    time.sleep(3)
    return telefono.captura(evidencia / f"{nombre}.png")


def compartir(pie: str, tema: str | None, evidencia: Path, publicaciones_antes: int | None) -> dict:
    """Pulsa Partager una sola vez (nunca se reintenta) y observa el resultado."""
    _exigir_listo()
    xml1 = _volcado_fresco()
    problemas = compositor_listo(xml1, pie, tema)
    if problemas:
        raise PantallaInesperada(f"el compositor no está listo para compartir: {problemas}")
    time.sleep(1.5)
    xml2 = _volcado_fresco()
    problemas = compositor_listo(xml2, pie, tema)
    if problemas:
        raise PantallaInesperada(f"el compositor no está listo para compartir (2.º volcado): {problemas}")
    posiciones = [[n["bounds"] for n in telefono.buscar_todos(x, texto="Partager", paquete=PAQUETE)]
                  for x in (xml1, xml2)]
    if posiciones[0] != posiciones[1]:
        raise PantallaInesperada(f"«Partager» se ha movido entre volcados: {posiciones}")
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está visible (o no se sabe): no se comparte")
    boton = _nodo(xml2, texto="Partager")
    captura_antes = str(telefono.captura(evidencia / "ig-05a-antes.png"))
    _exigir_listo()

    enviado = datetime.now(timezone.utc)
    telefono.tocar(*boton["centro"])

    observaciones: list[dict] = []
    procesado = None
    inicio = time.monotonic()
    while time.monotonic() - inicio < OBSERVACION_S:
        time.sleep(1.5)
        try:
            observaciones.append(observacion_de_volcado(telefono.volcado()))
        except telefono.TelefonoError:
            observaciones.append({"valido": False, "compositor": False, "banner": False})
        parcial = evaluar_envio(observaciones)
        if parcial == "confirmado":
            procesado = datetime.now(timezone.utc)
            break
        if parcial == "sin_banner" and time.monotonic() - inicio >= 20:
            break
    estado = evaluar_envio(observaciones)

    avisos = []
    publicaciones_despues = None
    try:
        if telefono.estado()["listo"]:
            xml = _esperar("abajo", texto="Profil")
            telefono.tocar(*_nodo(xml, "abajo", texto="Profil")["centro"])
            xml = _esperar(contiene="Modifier le profil")
            perfil = perfil_activo(xml)
            if perfil == MARCA:
                publicaciones_despues = publicaciones_de_perfil(xml)
            else:
                avisos.append(f"tras compartir el perfil activo es {perfil!r}")
        else:
            avisos.append("tras compartir el teléfono no está listo: no se leyó el perfil")
    except (PantallaInesperada, telefono.TelefonoError) as e:
        avisos.append(f"no se pudo leer el perfil tras compartir: {e}")
    if (estado == "confirmado" and publicaciones_antes is not None and publicaciones_despues is not None
            and publicaciones_despues != publicaciones_antes + 1):
        estado = "conteo_no_cuadra"

    try:
        captura = str(telefono.captura(evidencia / "ig-05-publicado.png"))
    except telefono.TelefonoError as e:
        captura = None
        avisos.append(f"no se pudo capturar tras compartir: {e}")
    return {"estado": estado,
            "submitted_at": enviado.isoformat(timespec="seconds"),
            "processing_completed_at": procesado.isoformat(timespec="seconds") if procesado else None,
            "publicaciones_antes": publicaciones_antes,
            "publicaciones_despues": publicaciones_despues,
            "captura": captura,
            "captura_antes": captura_antes,
            "avisos": avisos}
