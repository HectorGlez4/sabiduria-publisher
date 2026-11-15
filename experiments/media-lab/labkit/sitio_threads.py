"""Cita de sabiduriadebolsillo.net a Threads (@sabiduriabolsillo) en directo desde el móvil, con el enlace.

Por qué existe (15 nov 2026): el usuario vio en D1 que Threads era lo que más visitas traía al sitio mientras sus
publicaciones llevaban el enlace con `?de=threads` (22–26 oct). Desde el 6 nov solo salía el cruce automático de la
foto de Instagram, sin enlace, y las lecturas cayeron de ~37 a ~14 al día. Este paso vuelve a poner el enlace,
además del cruce desde Instagram, que se queda (decisión del usuario).

Camino (explorado el 15 nov en el SM-S721B, la app en francés):
- La imagen sale del sitio como la de LinkedIn: «Compartir como imagen» → hoja → «More» → lista «Apps» → Threads.
- Threads abre «Nouveau thread» con la tarjeta ya puesta y el nombre de la cuenta como texto encima del campo: la
  cuenta se comprueba leyéndolo, no por color.
- El enlace pegado en el texto sale azul (clicable) y la imagen se queda: no la sustituye la vista previa.
- La X cierra el editor sin preguntar: es el descarte.
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from labkit import telefono
from labkit.sitio_instagram import CIERRE_PIE, PantallaInesperada, _esperar, _exigir_listo, componer_en_el_sitio
from labkit.sitio_linkedin import _un_texto, abrir_app_en_la_hoja

TH = "com.instagram.barcelona"
CUENTA = "sabiduriabolsillo"
NUEVO = ("New thread", "Nouveau thread", "Nuevo hilo")
PUBLICAR = ("Post", "Publier", "Publicar")
LIMITE_PIE = 500  # el de Threads; el mismo que `LIMITS["threads"]` en src/variants.py
MARCA = "?de=threads"  # la Marca de origen que el sitio sí reconoce (sitio-sdb/src/lib/redes.ts)


def pie_threads(texto_plano: str, url: str) -> str:
    """La cita con su atribución, el enlace marcado y la pregunta; sin hashtags (en Threads leen como spam,
    `src/variants.py`). Si no cabe en 500, se recorta la cita y nunca el enlace: un enlace cortado no lleva a nada."""
    # La atribución canónica del sitio llega en una línea («…» — Autor, Obra, año.), como en el pie de Instagram.
    cita = " ".join(l.strip() for l in texto_plano.strip().splitlines() if l.strip())
    cola = f"\n\n{url}{MARCA}\n\n{CIERRE_PIE}"
    espacio = LIMITE_PIE - len(cola)
    if len(cita) > espacio:
        cita = cita[:espacio - 1].rstrip() + "…"
    return cita + cola


def _editor(xml: str) -> bool:
    return _un_texto(xml, NUEVO, TH) is not None and _un_texto(xml, PUBLICAR, TH) is not None


def _cuenta_es_la_nuestra(xml: str) -> bool:
    return any(n["package"] == TH and n["texto"].split(" ")[0].strip() == CUENTA for n in telefono.nodos(xml))


def _exigir_cuenta(xml: str) -> None:
    if not _cuenta_es_la_nuestra(xml):
        raise PantallaInesperada(f"el editor de Threads no muestra la cuenta @{CUENTA}: no se sigue")


def compartir(url: str, plantilla: str, ev: Path) -> dict:
    """De la cita del sitio al editor de Threads con la tarjeta cuadrada. Termina en el editor, sin texto."""
    _exigir_listo()
    texto_plano = componer_en_el_sitio(url, plantilla, "cuadrado")
    abrir_app_en_la_hoja("Threads")
    xml = _esperar(_editor, "el editor de Threads", plazo=40)
    time.sleep(2)
    _exigir_cuenta(telefono.volcado(timeout=20))
    pie = ev / "pie-threads.txt"
    pie.write_text(pie_threads(texto_plano, url), encoding="utf-8")
    return {"url": url, "plantilla": plantilla, "pie": str(pie), "cuenta": CUENTA,
            "captura": str(telefono.captura(ev / "01-editor-threads.png"))}


def escribir_pie(pie: str, ev: Path) -> dict:
    """El texto pegado con tildes (`phone_clipboard.py`) en «Quoi de neuf ?», con el teclado cerrado."""
    _exigir_listo()
    xml = _esperar(_editor, "el editor de Threads")
    campo = next((n for n in telefono.nodos(xml) if n["package"] == TH and n["clase"].endswith("EditText")), None)
    if campo is None:
        raise PantallaInesperada("no aparece el campo del texto en el editor de Threads")
    telefono.tocar(*campo["centro"])
    time.sleep(1.5)
    fichero = ev / "pie-threads.txt"
    fichero.write_text(pie, encoding="utf-8")
    script = Path(__file__).resolve().parent.parent / "phone_clipboard.py"
    r = subprocess.run([sys.executable, str(script), "--file", str(fichero)], capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise PantallaInesperada(f"phone_clipboard falló: {r.stderr or r.stdout}")
    primera = pie.splitlines()[0][:30]
    _esperar(lambda x: telefono.buscar(x, contiene=primera, paquete=TH) is not None, "el texto pegado")
    if telefono.teclado_visible():
        telefono.tecla(4)  # «atrás» con el teclado abierto solo lo cierra
        time.sleep(2)
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado sigue abierto")
    xml = telefono.volcado(timeout=20)
    if not _editor(xml):
        raise PantallaInesperada("al cerrar el teclado se cerró el editor de Threads")
    # El texto largo sube la cabecera fuera de la vista: la cuenta ya se comprobó en `compartir`.
    return {"captura": str(telefono.captura(ev / "04-composer-threads.png"))}


def publicar(ev: Path) -> dict:
    """El único toque que publica en Threads. Solo lo llama quien ya tiene el PASS del revisor."""
    _exigir_listo()
    xml1 = telefono.volcado(timeout=20)
    time.sleep(1.5)
    xml2 = telefono.volcado(timeout=20)
    botones = [_un_texto(x, PUBLICAR, TH) for x in (xml1, xml2)]
    if None in botones or botones[0]["bounds"] != botones[1]["bounds"] or not _editor(xml2):
        raise PantallaInesperada("«Publier» no está quieto en dos volcados del editor de Threads")
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está abierto: no se publica")
    antes = telefono.captura(ev / "05-antes-de-publicar-threads.png")
    publicado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    telefono.tocar(*botones[1]["centro"])
    time.sleep(6)
    return {"publicado_en": publicado_en, "captura_antes": str(antes),
            "captura": str(telefono.captura(ev / "06-tras-publicar-threads.png"))}


def verificar(ev: Path, plazo_s: int = 60) -> dict:
    """El editor ya no está abierto: Threads lo cierra al aceptar la publicación. Si sigue abierto, no salió."""
    limite = time.monotonic() + plazo_s
    while time.monotonic() < limite:
        try:
            xml = telefono.volcado(timeout=20)
        except telefono.TelefonoError:
            time.sleep(2)
            continue
        if not _editor(xml):
            return {"verificado": True, "captura": str(telefono.captura(ev / "07-verificado-threads.png"))}
        time.sleep(3)
    raise PantallaInesperada(f"el editor de Threads sigue abierto {plazo_s} s después de «Publier»")


def descartar(ev: Path) -> dict:
    """Cierra un borrador a medias con la X del editor (Threads no pregunta). Sin editor abierto, no hace nada."""
    xml = telefono.volcado(timeout=20)
    if not _editor(xml):
        return {"descartado": False, "motivo": "no había editor abierto",
                "captura": str(telefono.captura(ev / "descarte-threads.png"))}
    if telefono.teclado_visible():
        telefono.tecla(4)
        time.sleep(1.5)
        xml = telefono.volcado(timeout=20)
    nuevo = _un_texto(xml, NUEVO, TH)
    x1, y1, _, y2 = nuevo["bounds"]
    telefono.tocar(max(40, x1 - 85), (y1 + y2) // 2)  # la X está a la izquierda del título, sin texto propio
    time.sleep(2)
    if _editor(telefono.volcado(timeout=20)):
        raise PantallaInesperada("el editor de Threads sigue abierto tras la X")
    return {"descartado": True, "captura": str(telefono.captura(ev / "descarte-threads.png"))}
