"""Cita de sabiduriadebolsillo.net a TikTok («Sabiduria de bolsillo») desde el móvil, como foto vertical con música.

Por qué existe (16 nov 2026): el usuario pidió sumar TikTok a la segunda prueba (cada 27 min hasta el martes 17).

Camino (explorado el 16 nov en el SM-S918B, la app en inglés):
- La imagen sale del sitio como la de Threads: «Compartir como imagen» en formato vertical → hoja → «More» →
  lista «Apps» → TikTok. TikTok abre su editor de fotos con la tarjeta y ya le pone una canción (`tv_top_text`).
- «Next» lleva a la pantalla de publicar: «Add a catchy title» (se deja vacío), la descripción, «Drafts» y «Post».
- El enlace del texto no es clicable en TikTok: va igual con `?de=tiktok` (la Marca que el sitio ya acepta, en
  `sitio-sdb/src/lib/redes.ts`), para quien lo copie.
- Descartar: «atrás» hasta el editor y otro «atrás» abre «Discard / Save draft / Send to friends».
- El editor no enseña la cuenta: se comprueba antes, en la pestaña «Profile», por el nombre de la cabecera.

Lección de LinkedIn (16 nov): «el editor se cerró» no prueba que la publicación llegase. Aquí `verificar` además
espera a que no haya ningún aviso de fallo y el ciclo debe mirar el perfil web antes de darla por buena.
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from labkit import telefono
from labkit.sitio_instagram import CIERRE_PIE, PantallaInesperada, _esperar, _exigir_listo, componer_en_el_sitio, pie_para
from labkit.sitio_linkedin import _un_texto, abrir_app_en_la_hoja

TT = "com.zhiliaoapp.musically"
CUENTA = "Sabiduria de bolsillo"   # el nombre de la cabecera del perfil, no el @
SIGUIENTE = ("Next", "Suivant", "Siguiente")
PUBLICAR = ("Post", "Publier", "Publicar")
BORRADORES = ("Drafts", "Brouillons", "Borradores")
DESCARTAR = ("Discard", "Supprimer", "Descartar")
FALLO = ("Couldn't post", "Retry", "Réessayer", "Reintentar", "Upload failed")
LIMITE_PIE = 4000
MARCA = "?de=tiktok"


def pie_tiktok(texto_plano: str, url: str) -> str:
    """El pie de Instagram (cita, hashtags, pregunta) con el enlace marcado tras la cita."""
    cita, etiquetas, cierre = pie_para(texto_plano).rsplit("\n\n", 2)
    if cierre != CIERRE_PIE:
        raise ValueError("pie_para cambió de forma: revisa pie_tiktok")
    pie = f"{cita}\n\nMás citas: {url}{MARCA}\n\n{etiquetas}\n\n{cierre}"
    if len(pie) > LIMITE_PIE:
        raise ValueError(f"el pie mide {len(pie)} caracteres y el límite de TikTok es {LIMITE_PIE}")
    return pie


def _editor(xml: str) -> bool:
    return _un_texto(xml, SIGUIENTE, TT) is not None and telefono.buscar(xml, texto="Your Story", paquete=TT) is not None


def _pantalla_de_publicar(xml: str) -> bool:
    return _un_texto(xml, PUBLICAR, TT) is not None and _un_texto(xml, BORRADORES, TT) is not None


def _cuenta_es_la_nuestra(xml: str) -> bool:
    return any(n["package"] == TT and n["texto"].strip() == CUENTA for n in telefono.nodos(xml))


def _exigir_cuenta() -> None:
    """Abre TikTok en «Profile» y lee el nombre de la cabecera. Sin él, no se sigue."""
    telefono.lanzar(TT)
    xml = _esperar(lambda x: telefono.buscar(x, texto="Profile", paquete=TT) is not None, "la barra de TikTok", plazo=30)
    perfil = next((n for n in telefono.nodos(xml) if n["package"] == TT and n["desc"] == "Profile"), None)
    if perfil is not None:
        telefono.tocar(*perfil["centro"])
        time.sleep(3)
    xml = telefono.volcado(timeout=20)
    if not _cuenta_es_la_nuestra(xml):
        raise PantallaInesperada(f"TikTok no muestra la cuenta «{CUENTA}» en su perfil: no se sigue")


def compartir(url: str, plantilla: str, ev: Path) -> dict:
    """De la cita del sitio a la pantalla de publicar de TikTok con la tarjeta vertical y la música que pone
    TikTok. Termina en esa pantalla, sin texto."""
    _exigir_listo()
    _exigir_cuenta()
    texto_plano = componer_en_el_sitio(url, plantilla, "vertical")
    abrir_app_en_la_hoja("TikTok")
    xml = _esperar(_editor, "el editor de TikTok", plazo=40)
    cancion = None
    for _ in range(4):  # la canción que TikTok elige sola tarda unos segundos en aparecer
        time.sleep(2)
        xml = telefono.volcado(timeout=20)
        cancion = next((n["texto"] for n in telefono.nodos(xml) if n["package"] == TT
                        and n["resource_id"].endswith("/tv_top_text") and n["texto"]), None)
        if cancion:
            break
    editor = telefono.captura(ev / "01-editor-tiktok.png")
    telefono.tocar(*_un_texto(xml, SIGUIENTE, TT)["centro"])
    _esperar(_pantalla_de_publicar, "la pantalla de publicar de TikTok", plazo=30)
    pie = ev / "pie-tiktok.txt"
    pie.write_text(pie_tiktok(texto_plano, url), encoding="utf-8")
    return {"url": url, "plantilla": plantilla, "pie": str(pie), "cuenta": CUENTA, "cancion": cancion,
            "captura_editor": str(editor), "captura": str(telefono.captura(ev / "02-publicar-tiktok.png"))}


def escribir_pie(pie: str, ev: Path) -> dict:
    """La descripción pegada con tildes (`phone_clipboard.py`), con el teclado cerrado. El título se deja vacío."""
    _exigir_listo()
    xml = _esperar(_pantalla_de_publicar, "la pantalla de publicar de TikTok")
    campos = sorted((n for n in telefono.nodos(xml) if n["package"] == TT and n["clase"].endswith("EditText")),
                    key=lambda n: n["bounds"][1])
    if len(campos) < 2:
        raise PantallaInesperada("no aparecen el título y la descripción en la pantalla de publicar de TikTok")
    telefono.tocar(*campos[-1]["centro"])
    time.sleep(1.5)
    fichero = ev / "pie-tiktok.txt"
    fichero.write_text(pie, encoding="utf-8")
    script = Path(__file__).resolve().parent.parent / "phone_clipboard.py"
    r = subprocess.run([sys.executable, str(script), "--file", str(fichero)], capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise PantallaInesperada(f"phone_clipboard falló: {r.stderr or r.stdout}")
    primera = pie.splitlines()[0][:30]
    _esperar(lambda x: telefono.buscar(x, contiene=primera, paquete=TT) is not None, "el texto pegado")
    if telefono.teclado_visible():
        telefono.tecla(4)  # «atrás» con el teclado abierto solo lo cierra
        time.sleep(2)
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado sigue abierto")
    if not _pantalla_de_publicar(telefono.volcado(timeout=20)):
        raise PantallaInesperada("al cerrar el teclado se salió de la pantalla de publicar de TikTok")
    return {"captura": str(telefono.captura(ev / "04-composer-tiktok.png"))}


def publicar(ev: Path) -> dict:
    """El único toque que publica en TikTok. Solo lo llama quien ya tiene el PASS del revisor."""
    _exigir_listo()
    xml1 = telefono.volcado(timeout=20)
    time.sleep(1.5)
    xml2 = telefono.volcado(timeout=20)
    botones = [_un_texto(x, PUBLICAR, TT) for x in (xml1, xml2)]
    if None in botones or botones[0]["bounds"] != botones[1]["bounds"] or not _pantalla_de_publicar(xml2):
        raise PantallaInesperada("«Post» no está quieto en dos volcados de la pantalla de publicar de TikTok")
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está abierto: no se publica")
    antes = telefono.captura(ev / "05-antes-de-publicar-tiktok.png")
    publicado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    telefono.tocar(*botones[1]["centro"])
    time.sleep(8)
    return {"publicado_en": publicado_en, "captura_antes": str(antes),
            "captura": str(telefono.captura(ev / "06-tras-publicar-tiktok.png"))}


def verificar(ev: Path, plazo_s: int = 90) -> dict:
    """La pantalla de publicar se cerró y, pasada la subida, no hay ningún aviso de fallo. No basta solo: el
    ciclo comprueba además el perfil web (lección de LinkedIn, 16 nov)."""
    limite = time.monotonic() + plazo_s
    cerrada = False
    while time.monotonic() < limite:
        try:
            xml = telefono.volcado(timeout=20)
        except telefono.TelefonoError:
            time.sleep(2)
            continue
        if any(telefono.buscar(xml, contiene=t, paquete=TT) for t in FALLO):
            raise PantallaInesperada("TikTok avisa de que la publicación falló")
        if not _pantalla_de_publicar(xml):
            cerrada = True
        time.sleep(5)
    if not cerrada:
        raise PantallaInesperada(f"la pantalla de publicar de TikTok sigue abierta {plazo_s} s después de «Post»")
    return {"verificado": True, "captura": str(telefono.captura(ev / "07-verificado-tiktok.png"))}


def descartar(ev: Path) -> dict:
    """Cierra un borrador a medias: «atrás» hasta el menú del editor y «Discard». Sin TikTok delante, no hace nada."""
    for _ in range(3):
        xml = telefono.volcado(timeout=20)
        boton = _un_texto(xml, DESCARTAR, TT)
        if boton is not None:
            telefono.tocar(*boton["centro"])
            time.sleep(3)
            xml = telefono.volcado(timeout=20)
            if _editor(xml) or _pantalla_de_publicar(xml):
                raise PantallaInesperada("TikTok sigue con el borrador abierto tras «Discard»")
            return {"descartado": True, "captura": str(telefono.captura(ev / "descarte-tiktok.png"))}
        if not (_editor(xml) or _pantalla_de_publicar(xml)):
            return {"descartado": False, "motivo": "no había borrador de TikTok abierto",
                    "captura": str(telefono.captura(ev / "descarte-tiktok.png"))}
        telefono.tecla(4)
        time.sleep(2)
    raise PantallaInesperada("no aparece «Discard» en TikTok")
