"""Cita de sabiduriadebolsillo.net a la Página de LinkedIn «Sabiduria de Bolsillo», desde el móvil.

Decisión del usuario (14 nov 2026): la Página de empresa, no el perfil personal; solo la foto 4:5, una vez por
ciclo; el pie con el enlace a la cita; solo citas del sitio (no las piezas de la cola).

Por qué este camino (explorado el 14 nov en el SM-S918B):
- Un intent SEND lanzado desde adb abre el editor de LinkedIn VACÍO: descarta la imagen y el texto. Solo los
  acepta cuando llegan por la hoja de compartir de Android, así que la imagen sale del sitio como la de Instagram.
- El selector de imágenes del editor es Google Fotos con la galería personal del teléfono: elegir «la primera»
  publicaría cualquier foto que entrase antes. No se usa.
- En la hoja, LinkedIn no está en la fila de apps sino en «More» → lista «Apps», y al tocarlo pregunta
  «Private message» o «Share in a post».
- El editor no tiene selector de autor: publica con la identidad activa, que se ve en el avatar de la cabecera.
  El de la Página es el logo dorado «S»; el del perfil personal, una foto. Se comprueba por color antes de publicar.
"""
from __future__ import annotations

import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from labkit import telefono
from labkit.sitio_instagram import (HOJA, FILA_DE_HOJA, CIERRE_PIE, PantallaInesperada, _esperar, _exigir_listo,
                                    componer_en_el_sitio, pie_para, por_id)

LI = "com.linkedin.android"
MAS = ("More", "Plus", "Más")                  # el botón que abre la lista completa de apps de la hoja
EN_UN_POST = ("Share in a post", "Partager dans un post", "Compartir en una publicación")
PUBLICAR = ("Post", "Publier", "Publicar")
LIMITE_PIE = 3000
# Avatar de la cabecera del editor (1080 px de ancho). Medido el 14 nov: Página (225, 182, 98) dorado; perfil
# personal (208, 199, 198). El dorado es el único con el rojo muy por encima del azul.
AVATAR = (165, 120, 245, 200)


def pie_linkedin(texto_plano: str, url: str) -> str:
    """El pie de Instagram (cita, hashtags y pregunta) con el enlace a la cita tras la cita: en LinkedIn sí se
    pone, porque allí el enlace es clicable y es lo que trae gente al sitio (decisión del usuario, 14 nov)."""
    cita, etiquetas, cierre = pie_para(texto_plano).rsplit("\n\n", 2)
    if cierre != CIERRE_PIE:
        raise ValueError("pie_para cambió de forma: revisa pie_linkedin")
    # Con la Marca de origen, como Threads (`src/variants.py`): sin ella la visita llega sin red. Ojo: el sitio
    # solo cuenta las marcas de su conjunto cerrado (`sitio-sdb/src/lib/redes.ts`), y «linkedin» aún no está.
    pie = f"{cita}\n\nLee la cita completa: {url}?de=linkedin\n\n{etiquetas}\n\n{cierre}"
    if len(pie) > LIMITE_PIE:
        raise ValueError(f"el pie mide {len(pie)} caracteres y el límite de LinkedIn es {LIMITE_PIE}")
    return pie


def es_la_pagina(rgb: tuple[float, float, float]) -> bool:
    """El color medio del avatar de la cabecera es el dorado de la Página y no una foto de perfil."""
    r, g, b = rgb
    return r > 190 and 140 < g < 215 and r - b > 80


def autor_es_la_pagina(captura: Path) -> tuple[bool, list[int]]:
    from PIL import Image, ImageStat
    with Image.open(captura) as im:
        escala = im.width / 1080
        caja = tuple(round(v * escala) for v in AVATAR)
        media = ImageStat.Stat(im.convert("RGB").crop(caja)).mean
    return es_la_pagina(tuple(media)), [round(v) for v in media]


def _un_texto(xml: str, opciones: tuple[str, ...], paquete: str | None) -> dict | None:
    for t in opciones:
        n = telefono.buscar(xml, texto=t, paquete=paquete)
        if n is not None:
            return n
    return None


def _abrir_linkedin_en_la_hoja(intentos: int = 8) -> None:
    """De la hoja de compartir a «Share in a post» de LinkedIn."""
    abrir_app_en_la_hoja("LinkedIn", intentos)
    xml = _esperar(lambda x: _un_texto(x, EN_UN_POST, None) is not None, "«Share in a post»", plazo=15)
    telefono.tocar(*_un_texto(xml, EN_UN_POST, None)["centro"])


def abrir_app_en_la_hoja(nombre: str, intentos: int = 8) -> None:
    """De la hoja de compartir a la app `nombre`: «More» al final de la fila de apps, luego la lista «Apps»
    desplazada hasta ella. Nunca se lee la fila de arriba de la hoja: son contactos. La usan LinkedIn y Threads."""
    xml = _esperar(lambda x: bool(por_id(x, FILA_DE_HOJA, HOJA)), "la hoja de compartir")
    for _ in range(intentos):
        filas = por_id(xml, FILA_DE_HOJA, HOJA)
        x1, y1, x2, y2 = filas[-1]["bounds"]
        mas = next((n for n in telefono.nodos(xml) if n["package"] == HOJA and n["texto"] in MAS
                    and y1 <= n["bounds"][1] <= y2), None)
        if mas is not None:
            break
        y = (y1 + y2) // 2
        telefono.deslizar(x2 - 100, y, x2 - 400, y, 400)
        time.sleep(1.5)
        xml = telefono.volcado(timeout=20)
    else:
        raise PantallaInesperada("no aparece «More» al final de la fila de apps de la hoja")
    telefono.tocar(*mas["centro"])
    for _ in range(intentos):
        time.sleep(1.5)
        xml = telefono.volcado(timeout=20)
        app = telefono.buscar(xml, texto=nombre, paquete=HOJA)
        if app is not None and app["bounds"][1] > 250:
            break
        telefono.deslizar(540, 1900, 540, 1000, 500)
    else:
        raise PantallaInesperada(f"{nombre} no aparece en la lista «Apps» de la hoja")
    telefono.tocar(*app["centro"])


def _editor(xml: str) -> bool:
    return _un_texto(xml, PUBLICAR, LI) is not None


PAGINA = "Sabiduria de Bolsillo"
MENU = "Menu button: Access my profile and other navigation links"
EXITO = ("Post successful.", "Post successful", "Publication réussie.", "Post publié.", "Post publié",
         "Publicación correcta.")
PANEL = "https://www.linkedin.com/company/105723257/admin/dashboard/"  # el panel de la Página «Sabiduria de Bolsillo»
ESCRIBIR = ("Start a post", "Commencer un post", "Crear una publicación", "Empezar una publicación")
VISTA_PREVIA = ("Sharing preview box", "Fenêtre de présentation du partage", "Vista previa")
SIN_VISTA_PREVIA = ("Cannot display preview", "Impossible d’afficher l’aperçu", "Impossible d'afficher l'aperçu")


def _boton_escribir(xml: str) -> dict | None:
    return next((n for n in telefono.nodos(xml) if n["package"] == LI and n["desc"] in ESCRIBIR), None)


def texto_de_la_cita(url: str) -> str:
    """La atribución canónica que el sitio pone en `data-texto-plano` (la misma que «Copiar la cita»)."""
    import html
    import re
    import urllib.request
    with urllib.request.urlopen(url, timeout=30) as r:
        pagina = r.read().decode("utf-8")
    m = re.search(r'data-texto-plano="([^"]+)"', pagina)
    if m is None:
        raise PantallaInesperada(f"la página de la cita no trae data-texto-plano: {url}")
    return html.unescape(m.group(1))


def compartir(url: str, plantilla: str, ev: Path) -> dict:
    """Abre el editor de la Página desde su panel («Manage pages» → la Página → «Start a post»). Termina en el
    editor vacío con el avatar dorado. `plantilla` no se usa: la imagen llega con la vista previa del enlace.

    Por qué no la hoja de compartir (16 nov 2026): las 6 publicaciones que salieron por la hoja (Chrome → LinkedIn)
    subían la imagen al 100 % y nunca aparecían ni en la Página ni en el perfil, sin aviso. La misma cita escrita
    en el editor del panel de la Página salió al momento con «Post successful.» y la tarjeta en la vista previa."""
    _exigir_listo()
    pie = ev / "pie-linkedin.txt"
    pie.write_text(pie_linkedin(texto_de_la_cita(url), url), encoding="utf-8")
    telefono.forzar_cierre(LI)
    # El panel de la Página por enlace directo: el menú lateral no sirve (17 nov, una oferta de Premium tapaba la
    # Página en «Manage» y fallaron 7 ciclos seguidos).
    telefono.shell(f"am start -a android.intent.action.VIEW -d {PANEL} -p {LI}")
    escribir = lambda x: _boton_escribir(x) is not None
    xml = _esperar(escribir, "el panel de la Página", plazo=40)
    telefono.tocar(*_boton_escribir(xml)["centro"])
    _esperar(_editor, "el editor de la Página", plazo=30)
    time.sleep(2)
    if telefono.teclado_visible():
        telefono.tecla(4)
        time.sleep(1.5)
    captura = telefono.captura(ev / "01-editor-linkedin.png")
    pagina, color = autor_es_la_pagina(captura)
    if not pagina:
        raise PantallaInesperada(f"el editor de LinkedIn no publica como la Página (avatar {color}): no se sigue")
    return {"url": url, "plantilla": plantilla, "pie": str(pie), "autor": "pagina", "avatar": color,
            "captura": str(captura)}


def _pegar(texto: str, fichero: Path) -> None:
    """Pega `texto` con tildes donde esté el cursor (`phone_clipboard.py`)."""
    fichero.write_text(texto, encoding="utf-8")
    script = Path(__file__).resolve().parent.parent / "phone_clipboard.py"
    r = subprocess.run([sys.executable, str(script), "--file", str(fichero)], capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise PantallaInesperada(f"phone_clipboard falló: {r.stderr or r.stdout}")
    time.sleep(1.5)


def escribir_pie(pie: str, ev: Path) -> dict:
    """El pie pegado con tildes en «Share your thoughts…» (`phone_clipboard.py`), con el teclado cerrado."""
    _exigir_listo()
    xml = _esperar(_editor, "el editor de LinkedIn")
    campo = next((n for n in telefono.nodos(xml) if n["package"] == LI and n["clase"].endswith("EditText")), None)
    if campo is None:
        raise PantallaInesperada("no aparece el campo del texto en el editor de LinkedIn")
    telefono.tocar(*campo["centro"])
    time.sleep(1.5)
    (ev / "pie-linkedin.txt").write_text(pie, encoding="utf-8")
    # LinkedIn solo saca la vista previa (la tarjeta) de un enlace TECLEADO: pegado entero no la saca (17 nov, en el
    # SM-S721B). Se pega lo de antes del enlace, el enlace se teclea (es ASCII) y se pega lo de después.
    m = re.search(r"https://\S+", pie)
    if m is None:
        raise ValueError("el pie de LinkedIn no lleva enlace")
    antes, enlace, despues = pie[:m.start()], m.group(0), pie[m.end():]
    _pegar(antes, ev / "pie-linkedin-1.txt")
    primera = pie.splitlines()[0][:30]
    _esperar(lambda x: telefono.buscar(x, contiene=primera, paquete=LI) is not None, "el pie pegado")
    telefono.shell(f"input text {shlex.quote(enlace)}")
    if not despues.startswith("\n"):
        raise ValueError("tras el enlace del pie de LinkedIn debe venir un salto de línea")
    telefono.tecla(66)  # el salto tecleado es lo que cierra el enlace y dispara la vista previa
    time.sleep(1)
    _pegar(despues[1:], ev / "pie-linkedin-2.txt")
    _esperar(lambda x: telefono.buscar(x, contiene=CIERRE_PIE, paquete=LI) is not None, "el final del pie")
    escrito = next((n["texto"] for n in telefono.nodos(telefono.volcado(timeout=20))
                    if n["package"] == LI and n["clase"].endswith("EditText")), "")
    if " ".join(escrito.split()) != " ".join(pie.split()):
        raise PantallaInesperada("el texto del editor de LinkedIn no es el pie exacto")
    if telefono.teclado_visible():
        telefono.tecla(4)  # «atrás» con el teclado abierto solo lo cierra
        time.sleep(2)
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado sigue abierto")
    # La tarjeta llega como vista previa del enlace (la imagen og: del sitio), debajo del texto; con el teclado
    # abierto queda tapada y no sale en el volcado. Sin ella no se publica.
    def vista_previa(x: str) -> bool:
        if any(n["package"] == LI and any(n["texto"].startswith(t) for t in SIN_VISTA_PREVIA) for n in telefono.nodos(x)):
            raise PantallaInesperada("LinkedIn no pudo sacar la vista previa del enlace: sin tarjeta no se publica")
        return any(n["package"] == LI and n["desc"].startswith(VISTA_PREVIA) and "sabiduriadebolsillo.net" in n["desc"]
                   for n in telefono.nodos(x))
    _esperar(vista_previa, "la vista previa del enlace", plazo=45)
    captura = telefono.captura(ev / "04-composer-linkedin.png")
    pagina, color = autor_es_la_pagina(captura)
    if not pagina:
        raise PantallaInesperada(f"el autor dejó de ser la Página (avatar {color})")
    return {"captura": str(captura), "avatar": color}


def publicar(ev: Path) -> dict:
    """El único toque que publica en LinkedIn. Solo lo llama quien ya tiene el PASS del revisor."""
    _exigir_listo()
    xml1 = telefono.volcado(timeout=20)
    time.sleep(1.5)
    xml2 = telefono.volcado(timeout=20)
    botones = [_un_texto(x, PUBLICAR, LI) for x in (xml1, xml2)]
    if None in botones or botones[0]["bounds"] != botones[1]["bounds"]:
        raise PantallaInesperada("«Post» no está quieto en dos volcados")
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está abierto: no se publica")
    antes = telefono.captura(ev / "05-antes-de-publicar-linkedin.png")
    pagina, color = autor_es_la_pagina(antes)
    if not pagina:
        raise PantallaInesperada(f"el autor no es la Página (avatar {color}): no se publica")
    publicado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    telefono.tocar(*botones[1]["centro"])
    time.sleep(8)
    return {"publicado_en": publicado_en, "captura_antes": str(antes),
            "captura": str(telefono.captura(ev / "06-tras-publicar-linkedin.png"))}


def verificar(ev: Path, plazo_s: int = 60) -> dict:
    """LinkedIn enseña «Post successful.» al aceptar la publicación. Que el editor se cierre no basta: por la hoja
    de compartir se cerraba igual y la publicación no llegaba (16 nov)."""
    limite = time.monotonic() + plazo_s
    while time.monotonic() < limite:
        try:
            xml = telefono.volcado(timeout=20)
        except telefono.TelefonoError:
            time.sleep(2)
            continue
        if _un_texto(xml, EXITO, LI) is not None:
            captura = telefono.captura(ev / "07-verificado-linkedin.png")
            cerrar = next((n for n in telefono.nodos(xml) if n["package"] == LI and n["desc"] in ("Close", "Fermer", "Cerrar")
                           and n["bounds"][1] < 300), None)
            if cerrar is not None:  # la X de arriba; nunca la oferta de Premium de abajo
                telefono.tocar(*cerrar["centro"])
            return {"verificado": True, "captura": str(captura)}
        time.sleep(3)
    raise PantallaInesperada(f"LinkedIn no dijo «Post successful.» {plazo_s} s después de «Post»")


DESCARTAR = ("Discard", "Supprimer", "Descartar")


def descartar(ev: Path) -> dict:
    """Cierra un borrador a medias (un fallo o un FAIL del revisor): «Close» del editor y «Discard» en el aviso
    «You haven’t finished your post yet». Si el editor ya no está abierto, no hace nada."""
    xml = telefono.volcado(timeout=20)
    if _un_texto(xml, DESCARTAR, LI) is None:
        if not _editor(xml):
            return {"descartado": False, "motivo": "no había editor abierto",
                    "captura": str(telefono.captura(ev / "descarte-linkedin.png"))}
        cerrar = telefono.buscar(xml, texto="Close", paquete=LI) or telefono.buscar(xml, texto="Fermer", paquete=LI)
        if cerrar is None:
            raise PantallaInesperada("no aparece «Close» en el editor de LinkedIn")
        telefono.tocar(*cerrar["centro"])
        xml = _esperar(lambda x: _un_texto(x, DESCARTAR, LI) is not None, "el aviso de descartar", plazo=15)
    telefono.tocar(*_un_texto(xml, DESCARTAR, LI)["centro"])
    time.sleep(2)
    if _editor(telefono.volcado(timeout=20)):
        raise PantallaInesperada("el editor de LinkedIn sigue abierto tras «Discard»")
    return {"descartado": True, "captura": str(telefono.captura(ev / "descarte-linkedin.png"))}
