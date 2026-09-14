"""
Feed de Instagram por teléfono, un paso por llamada.

Cada función deja una captura en la carpeta de evidencia y termina. Quien dirige
(Claude) mira la captura antes de pedir el siguiente paso: nada de pulsaciones a
ciegas. Si un control no aparece, se lanza PantallaInesperada y no se toca nada más.
Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import phone_clipboard
from labkit import telefono

PAQUETE = "com.instagram.android"
MARCA = "sabiduriabolsillo"
ATRAS, CTRL_IZQ, TECLA_A = 4, 113, 29


class PantallaInesperada(RuntimeError):
    pass


def _nodo(xml: str, **kw) -> dict:
    n = telefono.buscar(xml, **kw)
    if n is None:
        raise PantallaInesperada(f"no aparece {kw}")
    return n


def _esperar(**kw) -> str:
    for _ in range(8):
        xml = telefono.volcado()
        if telefono.buscar(xml, **kw):
            return xml
        time.sleep(1.5)
    raise PantallaInesperada(f"no apareció {kw} tras 12 s")


def primera_miniatura_seleccionada(xml: str) -> bool:
    miniaturas = [n for n in telefono.nodos(xml)
                  if "Miniature de la photo" in n["desc"]
                  and n["desc"].startswith(("Sélectionné", "Désélectionné"))]
    if not miniaturas:
        return False
    primera = min(miniaturas, key=lambda n: (n["bounds"][1], n["bounds"][0]))
    return primera["desc"].startswith("Sélectionné")


def abrir_nueva_publicacion(evidencia: Path) -> Path:
    telefono.lanzar(PAQUETE)
    time.sleep(4)
    telefono.tocar(*_nodo(telefono.volcado(), texto="Profil")["centro"])
    xml = _esperar(contiene="Modifier le profil")
    if not telefono.buscar(xml, texto=MARCA):
        raise PantallaInesperada("el perfil activo no es @sabiduriabolsillo")
    telefono.tocar(*_nodo(xml, texto="Créer")["centro"])
    xml = _esperar(texto="Publication")
    telefono.tocar(*_nodo(xml, texto="Publication")["centro"])
    xml = _esperar(texto="Nouvelle publication")
    if not primera_miniatura_seleccionada(xml):
        raise PantallaInesperada("la foto preseleccionada no es la más reciente")
    return telefono.captura(evidencia / "ig-01-selector.png")


def alternar_recorte(evidencia: Path) -> Path:
    telefono.tocar(*_nodo(telefono.volcado(), texto="Modifier le rognage")["centro"])
    time.sleep(2)
    return telefono.captura(evidencia / "ig-02-recorte.png")


def siguiente(evidencia: Path, nombre: str) -> Path:
    telefono.tocar(*_nodo(telefono.volcado(), texto="Suivant")["centro"])
    time.sleep(4)
    return telefono.captura(evidencia / f"{nombre}.png")


def anadir_audio_sugerido(evidencia: Path) -> dict:
    chip = _nodo(telefono.volcado(), empieza="Audio suggéré.")
    x1, y1, x2, y2 = chip["bounds"]
    # El «+» del chip está a la derecha, en su tercio superior (medido el 2026-09-14).
    telefono.tocar(x2 - 59, y1 + round((y2 - y1) * 0.33))
    xml = _esperar(texto="Terminé")
    telefono.tocar(*_nodo(xml, texto="Terminé")["centro"])
    time.sleep(3)
    tema = chip["desc"].removeprefix("Audio suggéré.").split(". Appuyez")[0].strip()
    return {"tema": tema, "captura": str(telefono.captura(evidencia / "ig-03-audio.png"))}


def escribir_pie(pie: str, evidencia: Path) -> Path:
    xml = _esperar(contiene="Ajouter une légende")
    telefono.tocar(*_nodo(xml, contiene="Ajouter une légende")["centro"])
    time.sleep(2)
    telefono.combinacion(CTRL_IZQ, TECLA_A)
    phone_clipboard.pegar(pie, paste=True)
    time.sleep(2)
    if pie not in telefono.textos(telefono.volcado()):
        raise PantallaInesperada("el pie leído del teléfono no coincide con el archivo")
    telefono.tecla(ATRAS)
    time.sleep(3)
    return telefono.captura(evidencia / "ig-04-compositor.png")


def atras(evidencia: Path, nombre: str) -> Path:
    telefono.tecla(ATRAS)
    time.sleep(3)
    return telefono.captura(evidencia / f"{nombre}.png")


def compartir(pie: str, evidencia: Path) -> dict:
    xml = telefono.volcado()
    faltan = [k for k in ("Nouvelle publication", "Partager") if not telefono.buscar(xml, texto=k)]
    if faltan or pie not in telefono.textos(xml):
        raise PantallaInesperada(f"el compositor no está listo para compartir: {faltan or 'pie distinto'}")
    enviado = datetime.now(timezone.utc)
    telefono.tocar(*_nodo(xml, texto="Partager")["centro"])
    procesado = None
    for _ in range(60):
        time.sleep(1.5)
        if not telefono.buscar(telefono.volcado(), empieza="Publication sur sabiduriabolsillo"):
            procesado = datetime.now(timezone.utc)
            break
    return {"submitted_at": enviado.isoformat(timespec="seconds"),
            "processing_completed_at": procesado.isoformat(timespec="seconds") if procesado else None,
            "captura": str(telefono.captura(evidencia / "ig-05-publicado.png"))}
