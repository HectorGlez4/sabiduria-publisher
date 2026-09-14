"""
Feed de Instagram por teléfono, un paso por llamada.

Cada función deja una captura en la carpeta de evidencia y termina. Quien dirige
(Claude) mira la captura antes de pedir el siguiente paso: nada de pulsaciones a
ciegas. Si un control no aparece, o aparece en más de un sitio, se lanza
PantallaInesperada y no se toca nada más.

Cada paso empieza comprobando que el teléfono está listo y, si no, se detiene: nunca
lo despierta ni lo desbloquea (lo gestiona MaaS360).

Aquí solo están los pasos con E/S. La lectura pura de pantallas vive en
`instagram_pantallas` y se reexporta desde este módulo (`IG.observacion_de_volcado`,
`IG._nodo`… siguen funcionando).

Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import phone_clipboard
from labkit import telefono
from labkit.instagram_pantallas import *  # noqa: F401,F403 — reexporta `instagram_pantallas.__all__`
from labkit.instagram_pantallas import (MARCA, PAQUETE, PantallaInesperada, _campos, _coincidencias,
                                        _exigir_compositor_con_pie, _nodo, _suivant, _tiene_pie, campo_pie,
                                        compositor_listo, evaluar_envio, hay_desplegable_hashtags,
                                        miniatura_coincide, observacion_de_volcado, perfil_activo,
                                        publicaciones_de_perfil, punto_mas, seleccion_unica, tema_de_chip)

ATRAS, CTRL_IZQ, TECLA_A = 4, 113, 29
ESPERA_S = 25
OBSERVACION_S = 90


class BorradorPendiente(PantallaInesperada):
    """Instagram abrió con una publicación a medias: la resuelve una persona."""


class TelefonoNoListo(PantallaInesperada):
    """Dormido, bloqueado o sin adb. No se intenta arreglar."""


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


def compartir(pie: str, tema: str | None, evidencia: Path, publicaciones_antes: int | None,
              produccion_cercana: bool = False) -> dict:
    """Pulsa Partager una sola vez (nunca se reintenta) y observa el resultado.

    Estados: «confirmado» (banner, compositor cerrado y el perfil suma una publicación),
    «confirmado_sin_conteo» (igual, pero falta uno de los dos conteos, o
    `produccion_cercana`: el publicador de producción pudo sumar la suya y el conteo no
    prueba nada), «conteo_no_cuadra», «fallido» (Instagram avisó de un error),
    «sin_banner», «timeout» y «error_tras_pulsar» (algo lanzó una excepción desde la
    pulsación; ver `error` y, si se pudo tomar, `captura_error`). Desde la pulsación nada
    se propaga: el resultado siempre vuelve."""
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
                 "captura": None, "captura_antes": captura_antes, "captura_error": None, "avisos": []}
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
            elif produccion_cercana:
                estado = "confirmado_sin_conteo"
                avisos.append("producción publicó cerca: el +1 del perfil no prueba que sea esta publicación")
        resultado["estado"] = estado

        try:
            resultado["captura"] = str(telefono.captura(evidencia / "ig-05-publicado.png"))
        except telefono.TelefonoError as e:
            avisos.append(f"no se pudo capturar tras compartir: {e}")
    except Exception as e:  # noqa: BLE001 — tras pulsar, el resultado tiene que volver siempre
        resultado["estado"] = "error_tras_pulsar"
        resultado["error"] = f"{type(e).__name__}: {e}"
        try:
            resultado["captura_error"] = str(telefono.captura(evidencia / "ig-05-error.png"))
        except Exception as e_captura:  # noqa: BLE001 — la captura es best-effort: el resultado vuelve igual
            avisos.append(f"no se pudo capturar tras el error: {type(e_captura).__name__}: {e_captura}")
    return resultado
