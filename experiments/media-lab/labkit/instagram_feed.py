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
MARCAS_FALLO = ("Réessayer", "Impossible de publier", "n’a pas pu", "n'a pas pu")
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


def _dice(n: dict, valor: str) -> bool:
    return valor in (n["texto"], n["desc"])


def _area(n: dict) -> int:
    x1, y1, x2, y2 = n["bounds"]
    return (x2 - x1) * (y2 - y1)


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


def observacion_de_volcado(xml: str, boton_bounds: tuple[int, int, int, int] | None = None) -> dict:
    """Lo que dice un volcado tras pulsar Partager.

    - valido: hay Instagram en primer plano.
    - compositor: sigue el título «Nouvelle publication», o el «Partager» pulsado (mismos
      bounds), o el campo del pie. Otro «Partager» (el de compartir una publicación del
      inicio) no cuenta.
    - banner: «Publication sur sabiduriabolsillo…».
    - fallo: un aviso de error de Instagram (fuera del campo del pie, que es texto nuestro)."""
    ig = telefono.buscar_todos(xml, paquete=PAQUETE)
    boton = boton_bounds is not None and any(
        _dice(n, "Partager") and n["bounds"] == tuple(boton_bounds) for n in ig)
    return {"valido": bool(ig),
            "compositor": any(_dice(n, "Nouvelle publication") for n in ig) or boton
            or any(n["clase"] in CLASES_CAMPO for n in ig),
            "banner": any(v.startswith(f"Publication sur {MARCA}") for n in ig for v in (n["texto"], n["desc"])),
            "fallo": any(marca in v for n in ig if n["clase"] not in CLASES_CAMPO
                         for v in (n["texto"], n["desc"]) for marca in MARCAS_FALLO)}


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


def _tiene_pie(xml: str, pie: str) -> bool:
    return any(n["texto"] == pie for n in telefono.buscar_todos(xml, paquete=PAQUETE))


# --- Pasos (E/S) ---------------------------------------------------------------

def _exigir_listo() -> None:
    e = telefono.estado()
    if not e["listo"]:
        raise TelefonoNoListo(f"el teléfono no está listo (no se despierta ni se desbloquea): {e}")


def _esperar_que(cumple, descripcion: str) -> str:
    """Primer volcado válido que cumple la condición.

    El plazo de ESPERA_S se comprueba entre volcados y cada volcado recibe el tiempo
    que queda (5 s como mínimo), así que la espera total puede pasar de ESPERA_S en lo
    que tarde el último volcado."""
    inicio = time.monotonic()
    ultimo_error = ""
    while True:
        restante = max(5, int(ESPERA_S - (time.monotonic() - inicio)))
        try:
            xml = telefono.volcado(timeout=restante)
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
    xml = _esperar_que(
        lambda x: bool(_coincidencias(x, "abajo", texto="Profil"))
        or telefono.buscar(x, texto="Nouvelle publication", paquete=PAQUETE) is not None
        or bool(_campos(x)),
        "Instagram listo (Profil, «Nouvelle publication» o el campo del pie)")
    if telefono.buscar(xml, texto="Nouvelle publication", paquete=PAQUETE) or _campos(xml):
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
    if not _tiene_pie(xml, pie):
        faltan.append("pie exacto")
    if faltan:
        raise PantallaInesperada(f"tras cerrar el teclado falta: {faltan}")


def _hay_que_cerrar(xml: str) -> bool:
    """Teclado o desplegable de Instagram abiertos. Si no se sabe, se para sin pulsar
    atrás: un «atrás» con todo cerrado sacaría del compositor."""
    teclado = telefono.teclado_estado()
    if teclado is None:
        raise PantallaInesperada("no se puede leer si el teclado está abierto")
    return teclado or hay_desplegable_hashtags(xml, paquete=PAQUETE)


def escribir_pie(pie: str, evidencia: Path) -> Path:
    _exigir_listo()
    xml = _esperar_que(lambda x: campo_pie(x) is not None, "el campo del pie")
    telefono.tocar(*campo_pie(xml)["centro"])
    time.sleep(2)
    telefono.combinacion(CTRL_IZQ, TECLA_A)
    _exigir_listo()
    try:
        phone_clipboard.pegar(pie, paste=True)
    except (RuntimeError, OSError) as e:
        raise telefono.TelefonoError(f"portapapeles: {e}") from e
    time.sleep(2)
    xml = _volcado_fresco()
    if not _tiene_pie(xml, pie):
        raise PantallaInesperada("el pie leído del teléfono no coincide con el archivo")
    for _ in range(2):
        if not _hay_que_cerrar(xml):
            break
        telefono.tecla(ATRAS)
        time.sleep(2)
        xml = _volcado_fresco()
        _exigir_compositor_con_pie(xml, pie)
    else:
        if _hay_que_cerrar(xml):
            raise PantallaInesperada("el teclado o el desplegable siguen abiertos tras 2 «atrás»")
    return telefono.captura(evidencia / "ig-04-compositor.png")


def atras(evidencia: Path, nombre: str) -> Path:
    """«Atrás» solo con Instagram en primer plano."""
    _exigir_listo()
    xml = _volcado_fresco()
    if telefono.buscar(xml, paquete=PAQUETE) is None:
        raise PantallaInesperada("Instagram no está en primer plano: no se pulsa «atrás»")
    telefono.tecla(ATRAS)
    time.sleep(3)
    return telefono.captura(evidencia / f"{nombre}.png")


def compartir(pie: str, tema: str | None, evidencia: Path, publicaciones_antes: int | None) -> dict:
    """Pulsa Partager una sola vez (nunca se reintenta) y observa el resultado.

    Estados: «confirmado» (banner, compositor cerrado y el perfil suma una publicación),
    «confirmado_sin_conteo» (igual, pero falta uno de los dos conteos),
    «conteo_no_cuadra», «fallido» (Instagram avisó de un error), «sin_banner»,
    «timeout» y «error_tras_pulsar» (algo lanzó una excepción desde la pulsación; ver
    `error`). Desde la pulsación nada se propaga: el resultado siempre vuelve."""
    _exigir_listo()
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está visible (o no se sabe): no se comparte")
    captura_antes = str(telefono.captura(evidencia / "ig-05a-antes.png"))
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
    boton = _nodo(xml2, texto="Partager")

    resultado = {"estado": None, "error": None, "submitted_at": None, "processing_completed_at": None,
                 "publicaciones_antes": publicaciones_antes, "publicaciones_despues": None,
                 "captura": None, "captura_antes": captura_antes, "avisos": []}
    avisos = resultado["avisos"]
    try:
        enviado = datetime.now(timezone.utc)
        resultado["submitted_at"] = enviado.isoformat(timespec="seconds")
        telefono.tocar(*boton["centro"])

        observaciones: list[dict] = []
        inicio = time.monotonic()
        while time.monotonic() - inicio < OBSERVACION_S:
            time.sleep(1.5)
            try:
                observaciones.append(observacion_de_volcado(telefono.volcado(), boton["bounds"]))
            except telefono.TelefonoError:
                observaciones.append({"valido": False, "compositor": False, "banner": False, "fallo": False})
            parcial = evaluar_envio(observaciones)
            if parcial == "confirmado":
                resultado["processing_completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                break
            if parcial == "fallido":
                break
        estado = evaluar_envio(observaciones)

        try:
            if telefono.estado()["listo"]:
                xml = _esperar("abajo", texto="Profil")
                telefono.tocar(*_nodo(xml, "abajo", texto="Profil")["centro"])
                xml = _esperar(contiene="Modifier le profil")
                perfil = perfil_activo(xml)
                if perfil == MARCA:
                    resultado["publicaciones_despues"] = publicaciones_de_perfil(xml)
                else:
                    avisos.append(f"tras compartir el perfil activo es {perfil!r}")
            else:
                avisos.append("tras compartir el teléfono no está listo: no se leyó el perfil")
        except (PantallaInesperada, telefono.TelefonoError) as e:
            avisos.append(f"no se pudo leer el perfil tras compartir: {e}")

        if estado == "confirmado":
            despues = resultado["publicaciones_despues"]
            if publicaciones_antes is None or despues is None:
                estado = "confirmado_sin_conteo"
            elif despues != publicaciones_antes + 1:
                estado = "conteo_no_cuadra"
        resultado["estado"] = estado

        try:
            resultado["captura"] = str(telefono.captura(evidencia / "ig-05-publicado.png"))
        except telefono.TelefonoError as e:
            avisos.append(f"no se pudo capturar tras compartir: {e}")
    except Exception as e:  # noqa: BLE001 — tras pulsar, el resultado tiene que volver siempre
        resultado["estado"] = "error_tras_pulsar"
        resultado["error"] = f"{type(e).__name__}: {e}"
    return resultado
