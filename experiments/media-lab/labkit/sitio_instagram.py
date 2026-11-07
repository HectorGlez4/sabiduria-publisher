"""
Citas de sabiduriadebolsillo.net a Stories y Reels de Instagram, un paso por llamada.

La imagen la compone la propia Página de Cita («Compartir como imagen», formato Vertical) y
llega a Instagram por la hoja de compartir de Android: no hay un renderer paralelo. La parte
web se maneja por DevTools (`cdp`); la de Android e Instagram, por volcados de uiautomator.

Cada paso deja una captura en la carpeta de evidencia y termina; quien dirige la mira antes
de pedir el siguiente. Publicar es un paso aparte que exige el PASS del revisor visual.

Receta, medidas y trampas: `experiments/media-lab/historias-y-reels-desde-el-sitio.md`.
Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import json
import random
import re
import shlex
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

from labkit import cdp, telefono
from labkit.pantalla import PantallaInesperada

IG = "com.instagram.android"
HOJA = "com.android.intentresolver"
FILA_DE_HOJA = "sem_chooser_row_recycler_view"
ANCHO_ETIQUETA_ENTERA = 120  # «Instagram» entero mide 181 px; cortado contra el borde, ~50
CHROME = "com.android.chrome/com.google.android.apps.chrome.Main"
SITIO = "https://sabiduriadebolsillo.net/cita/"
_URL_DE_CITA = re.compile(r"https://sabiduriadebolsillo\.net/cita/[a-z0-9-]+/")
PLANTILLAS = ("papel", "tinta", "siena")
SUPERFICIES = {"feed": "Feed", "reel": "Reels", "story": "Stories"}  # superficie → opción del menú de la hoja
# El feed muestra el cuadrado entero; Reel y Story necesitan el vertical (el cuadrado pierde el texto por los lados).
FORMATO = {"feed": "cuadrado", "reel": "vertical", "story": "vertical"}
ALTO = {"cuadrado": 1080, "vertical": 1920}
# Botón que solo existe en el editor de cada superficie: confirma que se llegó.
EDITOR = {"feed": "media_thumbnail_tray_button", "reel": "clips_right_action_button",
          "story": "your_story_share_shortcut_button"}
PUBLICAR = {"feed": "share_footer_button", "reel": "share_button", "story": "your_story_share_shortcut_button"}
TEXTO_DEL_STICKER = "Leer la cita"
PARA_TODOS_LOS_REELS = "Arrêter pour tous les reels"
CUENTA = "sabiduriabolsillo"
TOP_PISTAS = 10
ESPERA_S = 25

# Zona del lienzo de la Story (pantalla 1080×2340) donde se busca tinta: a la izquierda de la
# columna de botones del editor (x ≥ 917) y por debajo de la cabecera del visor (y ≈ 250).
TINTA_X = (40, 900)
TINTA_Y = (250, 1700)
UMBRAL_TINTA = 60    # suma de diferencias RGB con el fondo
UNION_BLOQUES = 50   # filas sin tinta que todavía cuentan como el mismo bloque (interlineado)
MARGEN_STICKER = 40  # aire mínimo entre el sticker y cualquier texto
HUECO_Y = (330, 1640)  # dónde puede ir el centro del hueco: bajo la cabecera, sobre la barra de respuesta
TOLERANCIA_ARRASTRE = 30
ARRASTRES = 4  # el arrastre recorre ~70 % de lo pedido: se corrige en varias pasadas


class SinHueco(PantallaInesperada):
    """La cita no deja sitio para el sticker sin taparla: esa cita no se publica como Story."""


class CuentaAjena(PantallaInesperada):
    """Instagram tiene activa otra cuenta: no se publica nada hasta que vuelva la del sitio."""


class Pista(NamedTuple):
    puesto: int
    titulo: str
    artista: str
    explicita: bool
    centro: tuple[int, int]


# --- Lectura pura -------------------------------------------------------------

def _rid(n: dict) -> str:
    return n["resource_id"].split("/")[-1]


def por_id(xml: str, rid: str, paquete: str = IG) -> list[dict]:
    return [n for n in telefono.nodos(xml) if n["package"] == paquete and _rid(n) == rid]


def filas_de_pistas(xml: str) -> list[Pista]:
    """Las filas visibles de la pestaña «Populaires», en orden. Cada fila es un `track_number`
    seguido de su `song_title` y su `artist_name` («Artista • 2:33»). Instagram marca las
    explícitas con «explicite» en el content-desc del título."""
    fuera, actual = [], {}
    for n in telefono.nodos(xml):
        if n["package"] != IG:
            continue
        rid = _rid(n)
        if rid == "track_number" and n["texto"].isdigit():
            actual = {"puesto": int(n["texto"])}
        elif rid == "song_title" and "puesto" in actual:
            actual.update(titulo=n["texto"], explicita="explicite" in n["desc"].lower(), centro=n["centro"])
        elif rid == "artist_name" and "titulo" in actual:
            fuera.append(Pista(actual["puesto"], actual["titulo"], n["texto"].split(" • ")[0],
                               actual["explicita"], actual["centro"]))
            actual = {}
    return fuera


def elegir_pista(filas: list[Pista], recientes: list[str], rng: random.Random) -> Pista | None:
    """La pista que suena con la cita, o None si ninguna vale (el paso se detiene).

    `filas` es el ranking de «Populaires» tal como se ve; `recientes`, los títulos de las
    últimas publicaciones de este flujo, la más reciente primero.

    Decisión del usuario (2026-11-03): al azar entre el top 10, para que cada publicación
    suene distinta. «Audio d’origine» es audio de otra cuenta, no una canción, y la pista
    de la publicación anterior no se repite seguida. Decisión del usuario (2026-11-07): nunca una pista
    marcada como explícita.
    """
    aptas = [f for f in filas if f.puesto <= TOP_PISTAS and not f.titulo.startswith("Audio d") and not f.explicita
             and (not recientes or f.titulo != recientes[0])]
    return rng.choice(aptas) if aptas else None


def lienzo_pintado(captura: Path, minimo: float = 4.0) -> bool:
    """La tarjeta se ve en el editor: en la franja de la cita hay contraste (texto sobre fondo). La vista previa
    en negro es un plano casi uniforme; vale para los tres diseños, también el oscuro."""
    from PIL import Image, ImageStat
    with Image.open(captura) as im:
        franja = im.convert("L").crop((60, 500, im.width - 60, 1500))
        return ImageStat.Stat(franja).stddev[0] >= minimo


def color_de_fondo(px, ancho: tuple[int, int], alto: tuple[int, int]) -> tuple[int, int, int]:
    """El color más frecuente de una muestra de la zona: el fondo de la tarjeta."""
    muestra = Counter(px[x, y] for y in range(alto[0], alto[1], 37) for x in range(ancho[0], ancho[1], 23))
    return muestra.most_common(1)[0][0]


def filas_con_tinta(px, ancho: tuple[int, int] = TINTA_X, alto: tuple[int, int] = TINTA_Y,
                    umbral: int = UMBRAL_TINTA) -> list[int]:
    """Las filas `y` de la zona con al menos dos píxeles que no son fondo."""
    fondo = color_de_fondo(px, ancho, alto)
    filas = []
    for y in range(*alto):
        n = 0
        for x in range(ancho[0], ancho[1], 2):
            if sum(abs(a - b) for a, b in zip(px[x, y][:3], fondo)) > umbral:
                n += 1
                if n >= 2:
                    filas.append(y)
                    break
    return filas


def bloques(filas: list[int], union: int = UNION_BLOQUES) -> list[tuple[int, int]]:
    """Filas con tinta agrupadas en bloques; huecos de menos de `union` no los separan."""
    fuera: list[list[int]] = []
    for y in filas:
        if fuera and y - fuera[-1][1] <= union:
            fuera[-1][1] = y
        else:
            fuera.append([y, y])
    return [tuple(b) for b in fuera]


def centro_del_hueco(bloques_: list[tuple[int, int]], alto_sticker: int, margen: int = MARGEN_STICKER,
                     limites: tuple[int, int] = HUECO_Y) -> int | None:
    """Centro `y` del hueco más alto entre dos bloques donde cabe el sticker con `margen` de
    aire por arriba y por abajo, dentro de `limites`. Si entre bloques no cabe, el hueco de encima
    de la cita, bajo la cabecera del visor (la franja vertical del 7 nov estrechó el de abajo).
    None si no cabe en ninguno: nunca se pone encima del texto."""
    def el_mayor(pares) -> int | None:
        mejor = None
        for fin, inicio in pares:
            libre = inicio - fin - 2 * margen
            centro = (fin + inicio) // 2
            if libre >= alto_sticker and limites[0] <= centro <= limites[1]:
                if mejor is None or libre > mejor[0]:
                    mejor = (libre, centro)
        return None if mejor is None else mejor[1]
    entre = el_mayor((fin, inicio) for (_, fin), (inicio, _) in zip(bloques_, bloques_[1:]))
    if entre is not None or not bloques_:
        return entre
    return el_mayor([(TINTA_Y[0], bloques_[0][0])])


def solapa(caja: tuple[int, int, int, int], bloques_: list[tuple[int, int]], margen: int = MARGEN_STICKER) -> bool:
    """La caja del sticker invade algún bloque de texto, o su margen."""
    _, y1, _, y2 = caja
    return any(y1 - margen < fin and inicio < y2 + margen for inicio, fin in bloques_)


def elegir_cita(citas: list[dict], usadas: set[str], rng: random.Random, largo_max: int = 140) -> dict | None:
    """Una cita de dominio público, corta y no usada. `citas` son los frontmatter del corpus."""
    aptas = [c for c in citas if c.get("estadoDerechos") == "dominio-público"
             and len(c.get("texto", "")) <= largo_max and c.get("slug") not in usadas]
    return rng.choice(aptas) if aptas else None


LIMITE_PIE = 2200  # el de Instagram: un pie más largo se corta sin aviso


HASHTAGS_FIJOS = ("#SabiduriaDeBolsillo", "#Frases", "#Citas", "#Reflexiones")


def hashtag_del_autor(texto_plano: str) -> str | None:
    """«…» — Miguel de Unamuno, Obra. → #MiguelDeUnamuno (sin tildes ni signos)."""
    if " — " not in texto_plano:
        return None
    autor = texto_plano.rsplit(" — ", 1)[1].split(",")[0].strip().rstrip(".")
    plano = unicodedata.normalize("NFKD", autor).encode("ascii", "ignore").decode()
    palabras = re.findall(r"[A-Za-z0-9]+", plano)
    return "#" + "".join(w[:1].upper() + w[1:] for w in palabras) if palabras else None


CIERRE_PIE = "¿Qué te dice a ti?"


def pie_para(texto_plano: str) -> str:
    """El pie: la atribución canónica del sitio, los hashtags y una pregunta. Sin URL: un enlace en el pie le
    quita alcance en Facebook (decisión del usuario, 6 nov); el enlace solo va en el sticker de la Story.
    Termina en la pregunta y nunca en un hashtag, que abriría el desplegable que tapa los botones del composer.
    Los hashtags van desde la prueba del 6 nov: los pies sin ninguno solo llegaban a quien ya seguía la cuenta."""
    etiquetas = " ".join(dict.fromkeys(filter(None, (HASHTAGS_FIJOS[0], hashtag_del_autor(texto_plano),
                                                      *HASHTAGS_FIJOS[1:]))))
    pie = f"{texto_plano}\n\n{etiquetas}\n\n{CIERRE_PIE}"
    if len(pie) > LIMITE_PIE:
        raise ValueError(f"el pie mide {len(pie)} caracteres y el límite de Instagram es {LIMITE_PIE}")
    return pie


# --- Registro -------------------------------------------------------------------

def leer_registro(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def anotar(ruta: Path, entrada: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def usadas_desde(registro: list[dict], dias: int = 90, ahora: datetime | None = None) -> set[str]:
    ahora = ahora or datetime.now(timezone.utc)
    return {e["slug"] for e in registro
            if datetime.fromisoformat(e["publicado_en"]) >= ahora - timedelta(days=dias)}


# --- Teléfono ------------------------------------------------------------------

def quitar_valoracion(xml: str) -> bool:
    """Cierra «Donner une note à Instagram» con «Non merci» si está a la vista. Sale tras publicar y tapa el editor
    siguiente: tumbó casi todas las Stories de la prueba de cada 15 min (5 nov)."""
    if telefono.buscar(xml, texto="Donner une note à Instagram", paquete=IG) is None:
        return False
    boton = telefono.buscar(xml, texto="Non merci", paquete=IG)
    if boton is None:
        return False
    telefono.tocar(*boton["centro"])
    return True


def quitar_whatsapp(xml: str) -> bool:
    """Cierra «Partager dans le statut WhatsApp ?» con «Plus tard»: nunca se comparte con los contactos. Sale al
    pulsar Compartir en el feed y retiene la publicación mientras está abierta (7 nov: la foto no llegó a salir)."""
    if telefono.buscar(xml, contiene="statut WhatsApp", paquete=IG) is None:
        return False
    boton = telefono.buscar(xml, texto="Plus tard", paquete=IG)
    if boton is None:
        return False
    telefono.tocar(*boton["centro"])
    return True


def quitar_dialogos(xml: str) -> bool:
    """Los diálogos de Instagram que tapan el flujo y se cierran sin elegir nada que publique o comparta."""
    return quitar_valoracion(xml) or quitar_whatsapp(xml)


def _esperar(cumple, descripcion: str, plazo: float = ESPERA_S) -> str:
    limite = time.monotonic() + plazo
    while True:
        try:
            xml = telefono.volcado(timeout=20)
            if not quitar_dialogos(xml) and cumple(xml):  # tras quitarla, el plazo sigue corriendo
                return xml
        except telefono.TelefonoError:
            pass
        if time.monotonic() >= limite:
            raise PantallaInesperada(f"no apareció {descripcion} en {plazo:.0f} s")
        time.sleep(1.5)


def _volcar() -> str:
    """Un volcado de ahora, con los reintentos de `_esperar`: un volcado vacío suelto («volcado no
    válido: ''») tumbó un ciclo entero en mitad de `musica` (6 nov, 20:35)."""
    return _esperar(lambda x: True, "un volcado de la pantalla", plazo=15)


def _tocar_id(xml: str, rid: str) -> None:
    nodos = por_id(xml, rid)
    if len(nodos) != 1:
        raise PantallaInesperada(f"se esperaba un único {rid} y hay {len(nodos)}")
    telefono.tocar(*nodos[0]["centro"])


def _tocar_texto(xml: str, texto: str, paquete: str = IG) -> None:
    n = telefono.buscar(xml, texto=texto, paquete=paquete)
    if n is None:
        raise PantallaInesperada(f"no aparece «{texto}»")
    telefono.tocar(*n["centro"])


def _exigir_listo() -> None:
    e = telefono.estado()
    if not e["listo"]:
        raise PantallaInesperada(f"el teléfono no está listo (no se despierta ni se desbloquea): {e}")


def perfil_propio(xml: str, cuenta: str = CUENTA) -> bool | None:
    """En el perfil de `cuenta`: True si es la cuenta activa («Modifier le profil»), False si se ve
    desde otra («Suivi(e)», «S’abonner», «Envoyer un message»). None si el volcado aún no es ese perfil."""
    def hay(*textos: str) -> bool:
        return any(n["package"] == IG and (n["texto"] in textos or n["desc"] in textos) for n in telefono.nodos(xml))
    if not any(n["package"] == IG and _rid(n) == "action_bar_title" and n["texto"] == cuenta
               for n in telefono.nodos(xml)):
        return None
    if hay("Modifier le profil"):
        return True
    if hay("Suivi(e)", "S’abonner", "S'abonner", "Envoyer un message"):
        return False
    return None


def exigir_cuenta(cuenta: str = CUENTA) -> None:
    """Nada se publica desde otra cuenta. El 7 nov Instagram amaneció con la cuenta personal activa
    y el bucle no lo miraba: habría publicado allí."""
    telefono.shell(f"am start -a android.intent.action.VIEW -d {shlex.quote(f'instagram://user?username={cuenta}')}")
    xml = _esperar(lambda x: perfil_propio(x, cuenta) is not None, f"el perfil de {cuenta}", plazo=40)
    if not perfil_propio(xml, cuenta):
        raise CuentaAjena(f"Instagram tiene activa otra cuenta, no {cuenta}: no se publica")


def _instagram_en_la_hoja(intentos: int = 8) -> str:
    """Volcado con Instagram entero en la hoja. En el SM-S918B Instagram no sale en la primera
    pantalla de la fila de apps (la última `sem_chooser_row_recycler_view`; la de arriba es de
    contactos): se desliza esa fila a pasos cortos, porque un deslizamiento largo se pasa y lo deja
    cortado contra el borde. Sin esa fila (el SM-S721B) solo se espera."""
    xml = _esperar(lambda x: bool(por_id(x, FILA_DE_HOJA, HOJA)) or
                   telefono.buscar(x, texto="Instagram", paquete=HOJA) is not None, "la hoja de compartir")
    for _ in range(intentos):
        n = telefono.buscar(xml, texto="Instagram", paquete=HOJA)
        if n is not None and n["bounds"][2] - n["bounds"][0] >= ANCHO_ETIQUETA_ENTERA:
            return xml
        filas = por_id(xml, FILA_DE_HOJA, HOJA)
        if not filas:
            return _esperar(lambda x: telefono.buscar(x, texto="Instagram", paquete=HOJA) is not None,
                            "Instagram en la hoja de compartir")
        x1, y1, x2, y2 = filas[-1]["bounds"]
        y = (y1 + y2) // 2
        if n is not None and n["bounds"][0] <= x1 + 5:  # cortado a la izquierda: volver un poco
            telefono.deslizar(x1 + 150, y, x1 + 450, y, 400)
        else:
            telefono.deslizar(x2 - 100, y, x2 - 400, y, 400)
        time.sleep(1.5)
        xml = telefono.volcado(timeout=20)
    raise PantallaInesperada("Instagram no aparece entero en la fila de apps de la hoja")


def compartir_desde_el_sitio(url: str, plantilla: str, superficie: str, ev: Path) -> dict:
    """Abre la Página de Cita en Chrome, compone la imagen (cuadrada para el feed, vertical
    para Reel y Story) y la manda a Instagram. Termina en el editor de Instagram."""
    if not _URL_DE_CITA.fullmatch(url):
        raise ValueError(f"no es una URL de cita del sitio: {url}")
    if plantilla not in PLANTILLAS or superficie not in SUPERFICIES:
        raise ValueError(f"plantilla {plantilla!r} o superficie {superficie!r} desconocida")
    _exigir_listo()
    exigir_cuenta()
    telefono.cerrar_cortina()
    cdp.reenviar()
    telefono.shell(f"am start -n {CHROME} -a android.intent.action.VIEW -d {shlex.quote(url)}")
    with cdp.sesion_en(url) as s:
        s.esperar("!!document.querySelector('[data-abrir]')", descripcion="el botón de la imagen")
        # La atribución canónica del sitio (la misma que copia «Copiar la cita»): el pie sale de aquí.
        texto_plano = s.evaluar("document.querySelector('[data-imagen]').dataset.textoPlano")
        s.evaluar("document.querySelector('[data-abrir]').click()", gesto=True)
        s.esperar("document.querySelectorAll('[data-formatos] .formato').length === 2",
                  descripcion="los formatos (¿sitio sin el formato vertical?)")
        formato = FORMATO[superficie]
        s.evaluar(f"document.querySelector('.plantilla[data-id=\"{plantilla}\"]').click();"
                  f"document.querySelector('.formato[data-id=\"{formato}\"]').click()")
        s.esperar(f"document.querySelector('[data-lienzo]').height === {ALTO[formato]}",
                  descripcion=f"el lienzo {formato}")
        s.evaluar("document.querySelector('[data-descargar]').click()", gesto=True)
    xml = _instagram_en_la_hoja()
    cx, cy = telefono.buscar(xml, texto="Instagram", paquete=HOJA)["centro"]
    telefono.deslizar(cx, cy, cx, cy, 900)  # pulsación larga: menú Stories · Reels · Feed · Messages
    opcion = SUPERFICIES[superficie]
    xml = _esperar(lambda x: telefono.buscar(x, texto=opcion, paquete=HOJA) is not None, f"«{opcion}» en el menú")
    _tocar_texto(xml, opcion, HOJA)  # por texto: el orden del menú cambia entre usos
    _esperar(lambda x: bool(por_id(x, EDITOR[superficie])), f"el editor de {opcion}", plazo=40)
    time.sleep(2)
    # El Reel a veces abre con la vista previa en negro y la tarjeta tarda en pintarse (5 nov: tres Reels
    # descartados así). Se espera a ver texto en el lienzo antes de seguir; si no llega, pantalla inesperada.
    limite = time.monotonic() + 30
    while superficie == "reel" and not lienzo_pintado(telefono.captura(ev / "01a-editor-espera.png")):
        if time.monotonic() >= limite:
            raise PantallaInesperada("el editor del Reel sigue en negro tras 30 s")
        time.sleep(3)
    pie = ev / "pie.txt"
    pie.write_text(pie_para(texto_plano), encoding="utf-8")
    return {"url": url, "plantilla": plantilla, "formato": formato, "superficie": superficie, "pie": str(pie),
            "captura": str(telefono.captura(ev / f"01-editor-{superficie}.png"))}


def poner_musica(superficie: str, ev: Path, recientes: list[str], rng: random.Random) -> dict:
    """Una pista de «Populaires», sin sticker visible («Musique uniquement»)."""
    _exigir_listo()
    if superficie == "feed":
        # La píldora de arriba aplica el audio SUGERIDO sin preguntar; la herramienta «Audio» abre el buscador.
        xml = _esperar(lambda x: _herramienta_audio(x) is not None, "la herramienta «Audio» del editor")
        telefono.tocar(*_herramienta_audio(xml)["centro"])
    else:
        boton = "music_button" if superficie == "story" else "clips_action_bar_add_music_button"
        _tocar_id(_esperar(lambda x: bool(por_id(x, boton)), "el botón de música"), boton)
    xml = _esperar(lambda x: telefono.buscar(x, texto="Populaires", paquete=IG) is not None, "«Populaires»")
    _tocar_texto(xml, "Populaires")
    xml = _esperar(lambda x: len(filas_de_pistas(x)) >= 3, "el ranking de «Populaires»")
    # El selector enseña de 4 a 9 filas: se desliza la lista hasta ver el puesto TOP_PISTAS. Siempre entre
    # los centros de la primera y la última fila visibles: en el feed la lista es una hoja a media altura y
    # unas coordenadas fijas caerían en las pestañas o arrastrarían la hoja entera.
    vistas = {f.puesto: f for f in filas_de_pistas(xml)}
    for _ in range(4):
        if max(vistas) >= TOP_PISTAS:
            break
        _desplazar_lista(filas_de_pistas(_volcar()), hacia_abajo=True)
        vistas.update({f.puesto: f for f in filas_de_pistas(_volcar())})
    filas = [vistas[k] for k in sorted(vistas)]
    pista = elegir_pista(filas, recientes, rng)
    if pista is None:
        raise PantallaInesperada(f"ninguna pista de «Populaires» vale: {[f.titulo for f in filas]}")
    # Tras deslizar, el centro guardado puede ser de antes: se busca la fila por su puesto.
    for _ in range(6):
        visibles = filas_de_pistas(_volcar())
        en_pantalla = {f.puesto: f for f in visibles}
        if pista.puesto in en_pantalla:
            break
        _desplazar_lista(visibles, hacia_abajo=pista.puesto > max(en_pantalla, default=0))
    else:
        raise PantallaInesperada(f"no se vuelve a ver la fila {pista.puesto} «{pista.titulo}»")
    fila = en_pantalla[pista.puesto]
    if fila.titulo != pista.titulo:
        raise PantallaInesperada(f"el puesto {pista.puesto} ya no es «{pista.titulo}» sino «{fila.titulo}»")
    telefono.tocar(*fila.centro)
    _tocar_id(_esperar(lambda x: bool(por_id(x, "audio_bar_select_tap_target")), "la barra de la pista"),
              "audio_bar_select_tap_target")
    xml = _esperar(lambda x: bool(por_id(x, "music_editor_done_button")) or bool(por_id(x, EDITOR[superficie]))
                   or (superficie == "reel" and _check_del_clip(x) is not None),
                   "el editor del clip o el de la foto")
    if not por_id(xml, "music_editor_done_button") and not por_id(xml, EDITOR[superficie]):
        # Variantes del Reel con la pista arriba y un ✓ en la esquina en vez de «Terminé» (5 nov).
        # Se guarda el volcado para aprender su id; tras el ✓ tiene que volver el editor del Reel.
        (ev / "02-clip-check.xml").write_text(xml, encoding="utf-8")
        telefono.tocar(*_check_del_clip(xml)["centro"])
        _esperar(lambda x: bool(por_id(x, EDITOR[superficie])), "el editor del Reel tras el ✓")
    elif por_id(xml, "music_editor_done_button"):
        # Algunas pistas del Reel solo abren «Choisissez la section…», sin opciones de sticker: nada que tape.
        try:
            xml = _esperar(lambda x: telefono.buscar(x, texto="Musique uniquement", paquete=IG) is not None,
                           "«Musique uniquement»", plazo=6)
            _tocar_texto(xml, "Musique uniquement")  # nunca letras ni carátula: taparían la cita
            time.sleep(1.5)
        except PantallaInesperada:
            if superficie != "reel":
                raise
        _tocar_id(_volcar(), "music_editor_done_button")
    # En el feed no hay editor de clip: la pista queda puesta en la píldora de arriba.
    time.sleep(3)
    return {"pista": pista._asdict() | {"centro": None}, "ranking": [f.titulo for f in filas],
            "captura": str(telefono.captura(ev / f"02-musica-{superficie}.png"))}


def _check_del_clip(xml: str) -> dict | None:
    """El ✓ de «Choisissez la section à ajouter à votre reel»: el nodo pulsable de Instagram arriba a la derecha.
    None si no es esa pantalla o el ✓ no se distingue (entonces cuenta como pantalla inesperada)."""
    # Dos variantes con el ✓ arriba: solo el tramo («Choisissez la section…»), o los estilos del sticker con
    # «Musique uniquement» ya elegido (su rótulo en el centro; con otro estilo elegido no se toca el ✓).
    if (telefono.buscar(xml, contiene="Choisissez la section", paquete=IG) is None
            and telefono.buscar(xml, texto="Musique uniquement", paquete=IG) is None):
        return None
    ancho = max(n["bounds"][2] for n in telefono.nodos(xml))
    candidatos = [n for n in telefono.nodos(xml) if n["package"] == IG and n["clickable"] and n["enabled"]
                  and n["centro"][0] > ancho * 0.8 and n["centro"][1] < 400
                  and n["bounds"][2] - n["bounds"][0] < ancho * 0.25]
    return candidatos[0] if len(candidatos) == 1 else None


def _desplazar_lista(visibles: list[Pista], hacia_abajo: bool) -> None:
    """Desliza la lista de pistas una pantalla, de la última fila visible a la primera (o al revés)."""
    if len(visibles) < 2:
        raise PantallaInesperada(f"no hay filas suficientes para deslizar la lista: {len(visibles)}")
    alto, bajo = visibles[0].centro[1], visibles[-1].centro[1]
    desde, hasta = (bajo, alto) if hacia_abajo else (alto, bajo)
    telefono.deslizar(540, desde, 540, hasta, 600)
    time.sleep(2)


def _herramienta_audio(xml: str) -> dict | None:
    """La herramienta «Audio» de la fila inferior del editor del feed (texto, no la píldora)."""
    n = [m for m in telefono.nodos(xml) if m["package"] == IG and m["texto"] == "Audio" and m["bounds"][1] > 1700]
    return n[0] if len(n) == 1 else None


def _sticker(xml: str) -> dict | None:
    s = [n for n in telefono.nodos(xml) if n["package"] == IG and n["desc"].startswith("Sticker. Appuyez")]
    return s[0] if len(s) == 1 else None


def poner_enlace(url: str, ev: Path) -> dict:
    """Sticker de enlace en el hueco libre más alto entre la cita y la firma. Si no cabe sin
    tapar texto, SinHueco: la Story no se publica."""
    from PIL import Image

    if not _URL_DE_CITA.fullmatch(url):
        raise ValueError(f"no es una URL de cita del sitio: {url}")
    _exigir_listo()
    # El mapa del texto se mide ANTES de poner el sticker: con él encima, lo que tapa no se ve.
    mapa = telefono.captura(ev / "03a-mapa-sin-sticker.png")
    with Image.open(mapa) as im:
        texto = bloques(filas_con_tinta(im.convert("RGB").load()))
    if not texto:
        raise PantallaInesperada("no se ve texto en la tarjeta: ¿no está el editor de Stories?")
    _tocar_id(_volcar(), "asset_button")
    _tocar_texto(_esperar(lambda x: telefono.buscar(x, texto="Sticker à lien", paquete=IG) is not None,
                          "«Sticker à lien»"), "Sticker à lien")
    _esperar(lambda x: bool(por_id(x, "link_sticker_list_web_url_edit_text")), "el campo de la URL")
    telefono.shell(f"input text {shlex.quote(url)}")
    _tocar_id(_volcar(), "link_sticker_custom_cta_row_title")
    _esperar(lambda x: bool(por_id(x, "link_sticker_custom_cta_edit_text")), "el campo del texto del sticker")
    telefono.shell(f"input text {shlex.quote(TEXTO_DEL_STICKER.replace(' ', '%s'))}")
    time.sleep(1)
    xml = _volcar()
    escrita = por_id(xml, "link_sticker_list_web_url_edit_text")
    if not escrita or escrita[0]["texto"] != url:
        raise PantallaInesperada(f"la URL escrita no coincide: {escrita and escrita[0]['texto']!r}")
    _tocar_id(xml, "link_sticker_list_done_button")
    xml = _esperar(lambda x: _sticker(x) is not None, "el sticker en el lienzo")
    caja = _sticker(xml)["bounds"]
    destino = centro_del_hueco(texto, caja[3] - caja[1])
    if destino is None:
        raise SinHueco(f"no cabe el sticker ({caja[3] - caja[1]} px) sin tapar el texto: bloques {texto}")
    for _ in range(ARRASTRES):
        cx, cy = _sticker(xml)["centro"]
        if abs(destino - cy) <= TOLERANCIA_ARRASTRE:
            break
        telefono.deslizar(cx, cy, cx, destino, 900)
        time.sleep(1.5)
        xml = _esperar(lambda x: _sticker(x) is not None, "el sticker tras moverlo")
    caja = _sticker(xml)["bounds"]
    if solapa(caja, texto):
        raise PantallaInesperada(f"el sticker sigue tocando texto: {caja} contra {texto}")
    return {"bloques_de_texto": texto, "destino": destino, "sticker": caja,
            "captura": str(telefono.captura(ev / "03-enlace.png"))}


def escribir_pie(superficie: str, pie: str, ev: Path) -> dict:
    """Feed o Reel: del editor al composer y el pie pegado con tildes (`phone_clipboard.py`)."""
    if superficie == "story":
        raise ValueError("la Story no lleva pie: el enlace va en el sticker")
    _exigir_listo()
    _tocar_id(_volcar(), EDITOR[superficie])
    xml = _esperar(lambda x: bool(por_id(x, "caption_input_text_view"))
                   or telefono.buscar(x, contiene="réutiliser votre contenu", paquete=IG) is not None,
                   "el composer del Reel", plazo=40)
    if telefono.buscar(xml, contiene="réutiliser votre contenu", paquete=IG):
        _tocar_texto(xml, "OK")  # aviso informativo de remix: no cambia ajustes
        xml = _esperar(lambda x: bool(por_id(x, "caption_input_text_view")), "el composer del Reel")
    _tocar_id(xml, "caption_input_text_view")
    time.sleep(1.5)
    fichero = ev / "pie.txt"
    fichero.write_text(pie, encoding="utf-8")
    script = Path(__file__).resolve().parent.parent / "phone_clipboard.py"
    r = subprocess.run([sys.executable, str(script), "--file", str(fichero)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise PantallaInesperada(f"phone_clipboard falló: {r.stderr or r.stdout}")
    time.sleep(2)
    primera = pie.splitlines()[0][:30]
    xml = _esperar(lambda x: telefono.buscar(x, contiene=primera, paquete=IG) is not None, "el pie pegado")
    if telefono.buscar(xml, texto="OK", paquete=IG):
        _tocar_texto(xml, "OK")  # Reel: cierra el editor del pie y el teclado
    elif telefono.teclado_visible():
        telefono.tecla(4)  # feed: «atrás» solo cierra el teclado
    time.sleep(2)
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado sigue abierto tras «OK»")
    salida = {"captura": str(telefono.captura(ev / "04-composer.png"))}
    if superficie == "reel":
        salida["copia_en_story"] = _sin_copia_en_la_story()
        salida["captura_opciones"] = str(telefono.captura(ev / "04b-composer-opciones.png"))
    return salida


def interruptor_junto_a(xml: str, titulo: str) -> dict | None:
    """El interruptor de Instagram en la fila del texto `titulo`, o None. El volcado `--compressed` a veces
    quita el `toggle` de la derecha y deja solo la fila, que es ella misma un `Switch` con su `checked`:
    vale cualquiera de los dos, y el `toggle` si están ambos."""
    t = telefono.buscar(xml, texto=titulo, paquete=IG)
    if t is None:
        return None
    y = t["centro"][1]
    en_la_fila = [n for n in telefono.nodos(xml) if n["package"] == IG and n["bounds"][1] <= y <= n["bounds"][3]
                  and (_rid(n) == "toggle" or n["clase"].endswith(".Switch"))]
    toggles = [n for n in en_la_fila if _rid(n) == "toggle"]
    if len(toggles) == 1:
        return toggles[0]
    return en_la_fila[0] if len(en_la_fila) == 1 else None


def _sin_copia_en_la_story() -> str:
    """Reel: apaga «Votre story» en «Partager aussi sur…». Instagram la trae encendida y recuerda la última
    elección, así que se comprueba en cada Reel (decisión del usuario del 2026-11-04: sin copia automática
    en la Story). Threads y Facebook, en la misma lista, no se tocan."""
    for _ in range(4):
        n = interruptor_junto_a(_volcar(), "Votre story")
        if n is not None:
            break
        telefono.deslizar(540, 1700, 540, 900, 500)  # x en el centro: lejos de los interruptores de la derecha
        time.sleep(1.5)
    else:
        raise PantallaInesperada("no aparece el interruptor «Votre story» en el composer del Reel")
    if not n["checked"]:
        return "ya apagada"
    telefono.tocar(*n["centro"])
    time.sleep(1.5)
    # Apagarlo pregunta «Arrêter l'ajout à votre story ?»: «Arrêter pour tous les reels» es el ajuste de cuenta
    # que el usuario decidió quitar (no «Ne pas ajouter ce reel», que valdría solo para este).
    xml = _volcar()
    if telefono.buscar(xml, texto=PARA_TODOS_LOS_REELS, paquete=IG):
        _tocar_texto(xml, PARA_TODOS_LOS_REELS)
        time.sleep(2)
    n = interruptor_junto_a(_volcar(), "Votre story")
    if n is None or n["checked"]:
        raise PantallaInesperada("«Votre story» sigue encendido tras tocarlo")
    return "apagada"


def publicar(superficie: str, ev: Path) -> dict:
    """El único toque que publica. Solo lo llama quien ya tiene el PASS del revisor."""
    _exigir_listo()
    boton = PUBLICAR[superficie]
    xml1 = _volcar()
    time.sleep(1.5)
    xml2 = _volcar()
    cajas = [[n["bounds"] for n in por_id(x, boton)] for x in (xml1, xml2)]
    if len(cajas[0]) != 1 or cajas[0] != cajas[1]:
        raise PantallaInesperada(f"«{boton}» no está quieto y único en dos volcados: {cajas}")
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está abierto: no se publica")
    antes = str(telefono.captura(ev / "05-antes-de-publicar.png"))
    publicado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _tocar_id(xml2, boton)
    avisos = []
    # Tras pulsar pueden salir, en cualquier orden y con retraso, el aviso del audio original (Reel: decisión del
    # usuario del 2026-11-03, «Désactiver et partager») y la hoja del estado de WhatsApp, que retiene la
    # publicación hasta que se contesta («Plus tard»; 7 nov: en el Reel salió a los ~15 s y lo tumbó). Se vigila
    # los 30 s enteros: la barra de subida sale antes que la hoja, así que verla no basta para parar. La Story no
    # saca ninguna de las dos.
    limite = time.monotonic() + (30 if superficie != "story" else 0)
    while time.monotonic() < limite:
        try:
            xml = telefono.volcado(timeout=10)
        except telefono.TelefonoError:
            time.sleep(1.5)
            continue
        if superficie == "reel" and telefono.buscar(xml, texto="Désactiver et partager", paquete=IG) is not None:
            _tocar_texto(xml, "Désactiver et partager")
            avisos.append("aviso de audio original: «Désactiver et partager»")
        elif quitar_whatsapp(xml):
            avisos.append("hoja del estado de WhatsApp: «Plus tard»")
        time.sleep(1.5)
    time.sleep(5)
    return {"publicado_en": publicado_en, "avisos": avisos, "captura_antes": antes,
            "captura": str(telefono.captura(ev / "06-tras-publicar.png"))}


def _subiendo(xml: str) -> bool:
    """La barra de subida de Instagram sigue en pantalla."""
    return any(n["package"] == IG and n["texto"].startswith(("Partage sur", "Publication sur"))
               for n in telefono.nodos(xml))


_HACE_MINUTOS = re.compile(r"Story de (?P<cuenta>[^,]+), il y a (?P<n>\d+) (?P<unidad>minutes?|secondes?)")


_VISOR = re.compile(r"Story de (?P<cuenta>[^,]+), il y a ")


def _segmento_del_visor(xml: str, cuenta: str) -> str | None:
    """El content-desc del segmento que enseña el visor de Stories de `cuenta`, o None si no está abierto."""
    for n in telefono.nodos(xml):
        m = _VISOR.match(n["desc"])
        if m and m["cuenta"] == cuenta:
            return n["desc"]
    return None


def story_reciente(desc: str, cuenta: str, max_min: int = 5) -> bool:
    """El content-desc del visor es de una Story de `cuenta` publicada hace ≤ `max_min` minutos."""
    m = _HACE_MINUTOS.match(desc)
    # Recién publicada dice «il y a 26 secondes»: también cuenta (7 nov, la tumbaba).
    return bool(m) and m["cuenta"] == cuenta and (m["unidad"].startswith("seconde") or int(m["n"]) <= max_min)


def _recorrer_visor(ev: Path, cuenta: str, camino: str, plazo_s: int = 150) -> dict:
    """Con el visor recién pedido, avanza segmento a segmento hasta una Story propia de hace minutos.

    El visor de las Stories propias empieza por la más antigua de las últimas 24 h: tras una noche de
    prueba son 30 o más, y con 12 saltos no se llegaba a la reciente; al pasar la última el visor se
    cierra y vuelve al perfil (las 30 Stories de la prueba del 6 nov quedaron «sin verificar»). Solo cuenta
    como visor un content-desc con la edad («il y a …»): las destacadas del perfil también empiezan por
    «Story de <cuenta>,» y tocar a ciegas sobre el perfil abre otra cosa (pasó: el «tableau de bord»)."""
    vistos: list[str] = []
    registro = ev / f"07-segmentos-{camino}.txt"
    limite = time.monotonic() + plazo_s
    try:
        while True:
            xml = _esperar(lambda x: _segmento_del_visor(x, cuenta) is not None,
                           "el visor con una Story propia", plazo=20 if not vistos else 10)
            desc = _segmento_del_visor(xml, cuenta)
            vistos.append(desc)
            if story_reciente(desc, cuenta):
                return {"encontrada": True, "desc": desc, "segmento": len(vistos) - 1, "camino": camino,
                        "captura": str(telefono.captura(ev / "07-verificada.png"))}
            if time.monotonic() >= limite:
                raise PantallaInesperada(f"sin una Story de hace minutos tras {len(vistos)} segmentos en {plazo_s} s")
            telefono.tocar(1000, 1000)  # siguiente segmento: solo con el visor confirmado en pantalla
            time.sleep(1.5)
    except PantallaInesperada as e:
        if vistos and "segmentos" not in str(e):
            raise PantallaInesperada(f"el visor se cerró tras {len(vistos)} segmentos sin una Story de hace "
                                     f"minutos (el último: {vistos[-1]!r})") from e
        raise
    finally:
        registro.write_text("\n".join(vistos) + "\n", encoding="utf-8")


def verificar(superficie: str, ev: Path, pista: str, pie: str | None = None,
              cuenta: str = CUENTA) -> dict:
    """Busca lo publicado desde el perfil. No se fía de la bandeja de Stories de la portada:
    va en caché y se desplaza sola."""
    _exigir_listo()
    # Nunca se cierra Instagram aquí: la subida la hace un trabajo en segundo plano (PendingMediaWorker) y
    # cerrar la app la cortaría. Navegar no le afecta. Primero se sale de donde se esté —tras publicar un Reel
    # queda puesto el feed de Reels, que no deja volcar la pantalla— yendo al perfil por enlace profundo:
    # Instagram restaura la última pantalla (a veces una publicación abierta, sin barra de pestañas) y un
    # volcado atrasado puede seguir enseñando una pestaña que ya no está.
    telefono.shell(f"am start -a android.intent.action.VIEW -d {shlex.quote(f'instagram://user?username={cuenta}')}")
    _esperar(lambda x: bool(por_id(x, "profile_tab_icon_view")), "el perfil", plazo=40)
    _esperar(lambda x: not _subiendo(x), "el final de la subida («Partage sur…»)", plazo=180)
    time.sleep(2)
    # En el SM-S918B el perfil abierto por enlace sale en caché: el contador ya sube, pero ni la baldosa nueva ni
    # el aro de la Story aparecen hasta tirar hacia abajo para refrescarlo.
    telefono.deslizar(540, 700, 540, 1700, 500)
    time.sleep(6)
    if superficie == "story":
        xml = _esperar(lambda x: len(por_id(x, "row_profile_header_imageview_frame_layout")) == 1,
                       "la foto del perfil")
        # Por la mitad baja: la burbuja vacía de las notas («Vos pensées ici…») tapa la de arriba y, tocada,
        # abre el editor de notas en vez del visor (pasó en el SM-S918B).
        x1, y1, x2, y2 = por_id(xml, "row_profile_header_imageview_frame_layout")[0]["bounds"]
        telefono.tocar((x1 + x2) // 2, y2 - (y2 - y1) // 5)
        try:
            return _recorrer_visor(ev, cuenta, "perfil")
        except PantallaInesperada as e:
            if "segmentos" in str(e):
                raise  # el visor sí se abrió: la bandeja empezaría otra vez por la más antigua
            # Segundo camino: la bandeja de la portada, donde la Story propia es siempre la primera.
            # Instagram restaura la última pantalla al abrirse, así que se va a la portada por su pestaña.
            telefono.captura(ev / "07a-sin-visor-perfil.png")
            telefono.shell("input keyevent 4")
            time.sleep(2)
            telefono.shell("monkey -p com.instagram.android -c android.intent.category.LAUNCHER 1")
            xml = _esperar(lambda x: bool(por_id(x, "feed_tab")), "la barra de pestañas", plazo=30)
            telefono.tocar(*por_id(xml, "feed_tab")[0]["centro"])
            propia = f"Story de {cuenta}, 0 sur"
            xml = _esperar(lambda x: any(n["desc"].startswith(propia) for n in por_id(x, "avatar_image_view")),
                           f"la Story de {cuenta} en la bandeja", plazo=30)
            telefono.tocar(*[n for n in por_id(xml, "avatar_image_view") if n["desc"].startswith(propia)][0]["centro"])
            try:
                return _recorrer_visor(ev, cuenta, "bandeja")
            except PantallaInesperada as e2:
                raise PantallaInesperada(f"perfil: {e}; bandeja: {e2}") from e2
    # Las baldosas se llaman distinto según la pestaña: `image_button` («Reel par…», «Photo de…») en la
    # Las baldosas se llaman distinto según la pestaña: `image_button` («Reel par…», «Photo de…») en la
    # cuadrícula y `preview_clip_thumbnail` («Reel de <cuenta>. Nombre de vues…») en la de Reels.
    # El Reel se busca en la cuadrícula, no en la pestaña Reels: allí las baldosas se animan, uiautomator no
    # vuelca y 17 de 19 Reels de la prueba del 5 nov quedaron «sin verificar» estando en el perfil.
    pestaña_de, prefijo = {"reel": ("Vue Grille", ("Reel par", "Reel de")), "feed": ("Vue Grille", ("Photo de",))}[superficie]
    xml = _esperar(lambda x: any(n["desc"] == pestaña_de for n in por_id(x, "profile_tab_icon_view")),
                   f"la pestaña «{pestaña_de}» del perfil")
    pestaña = [n for n in por_id(xml, "profile_tab_icon_view") if n["desc"] == pestaña_de]
    telefono.tocar(*pestaña[0]["centro"])
    time.sleep(3)
    # Tocar la pestaña ya elegida abre el orden («Les plus récents» / «Les plus vus») encima de la cuadrícula:
    # se elige el más reciente, que además pone lo recién publicado primero.
    orden = telefono.buscar(_volcar(), texto="Les plus récents", paquete=IG)
    if orden:
        telefono.tocar(*orden["centro"])
        time.sleep(3)
    for i in range(4):  # la cuadrícula puede llevar arriba un Reel fijado
        xml = _esperar(lambda x: True, "un volcado del perfil", plazo=60)  # la pestaña Reels anima las baldosas
        tiles = [n for n in telefono.nodos(xml) if n["package"] == IG and n["desc"].startswith(prefijo)
                 and _rid(n) in ("image_button", "preview_clip_thumbnail")]
        if len(tiles) <= i:
            break
        telefono.tocar(*tiles[i]["centro"])
        time.sleep(4)
        if superficie == "reel":
            # Un Reel en marcha no deja la pantalla en reposo y uiautomator no vuelca: un toque en el centro lo
            # pausa. Solo en Reels: en una foto, dos toques serían un «me gusta».
            telefono.tocar(540, 1000)
            time.sleep(1.5)
        xml = _esperar(lambda x: True, "un volcado del visor", plazo=40)
        # La pista identifica la publicación: el visor de Reels no siempre lleva el pie en el volcado, así
        # que el pie se informa pero no se exige (el visor del feed sí lo enseña).
        if any(f" · {pista}" in n["desc"] or n["desc"].endswith(pista) for n in telefono.nodos(xml)):
            pie_visible = pie is not None and telefono.buscar(
                xml, contiene=pie.splitlines()[0][:25], paquete=IG) is not None
            return {"encontrada": True, "posicion": i, "pie_visible": pie_visible,
                    "captura": str(telefono.captura(ev / "07-verificada.png"))}
        telefono.tecla(4)
        time.sleep(2)
    raise PantallaInesperada(f"no aparece una publicación ({superficie}) con «{pista}» entre las cuatro primeras")
