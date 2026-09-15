"""
Feed de Instagram por teléfono, un paso por llamada.

Cada función deja una captura en la carpeta de evidencia y termina. Quien dirige (Claude)
mira la captura antes de pedir el siguiente paso: nada de pulsaciones a ciegas. Lo común
(esperas, escritura, envío con un toque) vive en `pasos`; la lectura pura de pantallas en
`instagram_pantallas`, que se reexporta desde aquí (`IG.observacion_de_volcado`, `IG._nodo`…
siguen funcionando).

Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import time  # noqa: F401 — las pruebas de la fase 1 sustituyen instagram_feed.time.sleep y .monotonic
from datetime import datetime
from pathlib import Path

from labkit import pasos, reloj, telefono
from labkit.instagram_pantallas import *  # noqa: F401,F403 — reexporta `instagram_pantallas.__all__`
from labkit.instagram_pantallas import (MARCA, PAQUETE, PantallaInesperada, _campos, _coincidencias,
                                        _exigir_compositor_con_pie, _nodo, _suivant, banners_de_volcado,
                                        campo_pie, compositor_listo, emergente_desplegable, hay_desplegable_hashtags,
                                        miniatura_coincide, observacion_de_volcado, perfil_activo,
                                        publicaciones_de_perfil, punto_mas, seleccion_unica, tema_de_chip)
# ATRAS y ESTABILIZACION_TIMEOUT_S los usan los pasos de aquí (`atras`, docstrings); CTRL_IZQ y TECLA_A ya
# no (van dentro de `pasos.escribir_texto`): solo lectura, se quedan reexportados porque las pruebas de la
# fase 1 los leen como IG.CTRL_IZQ/IG.TECLA_A.
from labkit.pasos import (ATRAS, CTRL_IZQ, ESTABILIZACION_TIMEOUT_S, TECLA_A,  # noqa: F401
                          BorradorPendiente, TelefonoNoListo)


def _esperar(zona: str | None = None, **kw) -> str:
    return pasos.esperar_que(lambda xml: bool(_coincidencias(xml, zona, **kw)), f"{kw}")


def abrir_nueva_publicacion(evidencia: Path, subido_en: datetime | str) -> dict:
    """Desde el perfil de la marca hasta el selector con la foto recién subida marcada.

    `lanzar` reanuda Instagram donde se quedó; con un vídeo en marcha (un Reel abierto desde un mensaje
    directo) ningún volcado llega a leerse. Solo en ese caso (`pasos.SinVolcado`: nada leído, así que no hay
    ningún borrador visto que proteger) se fuerza el cierre UNA vez, se relanza en frío y se vuelve a esperar
    con el mismo criterio; el resultado lo anota en `arranque_en_frio`. Si algún volcado se leyó, el error
    sale como siempre y la app no se toca."""
    if isinstance(subido_en, str):
        subido_en = datetime.fromisoformat(subido_en)
    pasos.exigir_listo()
    try:
        telefono.cerrar_cortina()
    except telefono.TelefonoError:
        pass  # best-effort: si no se puede replegar, se sigue e Instagram decide si hay bloqueo

    def lanzar_y_esperar() -> str:
        telefono.lanzar(PAQUETE)
        reloj.dormir(4)
        return pasos.esperar_que(
            lambda x: bool(_coincidencias(x, "abajo", texto="Profil"))
            or telefono.buscar(x, texto="Nouvelle publication", paquete=PAQUETE) is not None
            or bool(_campos(x)),
            "Instagram listo (Profil, «Nouvelle publication» o el campo del pie)")

    arranque_en_frio = False
    try:
        xml = lanzar_y_esperar()
    except pasos.SinVolcado:
        pasos.exigir_listo()
        telefono.forzar_cierre(PAQUETE)
        arranque_en_frio = True
        xml = lanzar_y_esperar()  # si vuelve a fallar, el error sale tal cual: no hay otro cierre
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
        raise PantallaInesperada(
            f"la miniatura seleccionada no es la subida a las {subido_en.isoformat()}: {sel['desc']}")
    return {"captura": str(telefono.captura(evidencia / "ig-01-selector.png")),
            "publicaciones_antes": publicaciones_antes, "arranque_en_frio": arranque_en_frio}


def alternar_recorte(evidencia: Path) -> Path:
    """Pulsa el conmutador de recorte UNA vez. El volcado no muestra si queda en 4:5 (el
    contenedor mide lo mismo): quien dirige lo confirma en la captura."""
    pasos.exigir_listo()
    xml = _esperar(texto="Modifier le rognage")
    telefono.tocar(*_nodo(xml, texto="Modifier le rognage")["centro"])
    reloj.dormir(2)
    return telefono.captura(evidencia / "ig-02-recorte.png")


def siguiente(evidencia: Path, nombre: str) -> Path:
    pasos.exigir_listo()
    xml = _esperar(texto="Suivant")
    telefono.tocar(*_suivant(xml)["centro"])
    reloj.dormir(4)
    return telefono.captura(evidencia / f"{nombre}.png")


def anadir_audio_sugerido(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = _esperar(empieza="Audio suggéré.")
    chip = _nodo(xml, empieza="Audio suggéré.")
    tema = tema_de_chip(chip["desc"])
    if tema is None:
        raise PantallaInesperada(f"el chip de audio no dice qué tema es: {chip['desc']!r}")
    telefono.tocar(*punto_mas(chip["bounds"]))
    xml = _esperar(texto="Terminé")
    telefono.tocar(*_nodo(xml, texto="Terminé")["centro"])
    reloj.dormir(3)
    return {"tema": tema, "captura": str(telefono.captura(evidencia / "ig-03-audio.png"))}


def detalles(evidencia: Path) -> Path:
    """Del editor a la pantalla de detalles; quien dirige la mira antes de escribir el pie."""
    pasos.exigir_listo()
    xml = _esperar(texto="Suivant")
    telefono.tocar(*_suivant(xml)["centro"])
    pasos.esperar_que(lambda x: campo_pie(x) is not None, "el campo del pie")
    return telefono.captura(evidencia / "ig-03b-detalles.png")


def escribir_pie(pie: str, evidencia: Path) -> Path:
    """Pega el pie y solo captura con el compositor estable, sin teclado ni desplegable de hashtags, ya sea
    por nodos o como ventana emergente (tarea 10f); ver `pasos.escribir_texto`."""
    pasos.escribir_texto(pie, PAQUETE, campo=campo_pie,
                         exigir=lambda x: _exigir_compositor_con_pie(x, pie),
                         desplegable_nodos=lambda x: hay_desplegable_hashtags(x, paquete=PAQUETE),
                         emergente=emergente_desplegable)
    return telefono.captura(evidencia / "ig-04-compositor.png")


def atras(evidencia: Path, nombre: str) -> Path:
    """«Atrás» solo con Instagram en primer plano."""
    return pasos.atras(PAQUETE, evidencia, nombre)


def compartir(pie: str, tema: str | None, evidencia: Path, publicaciones_antes: int | None,
              produccion_cercana: bool = False) -> dict:
    """Pulsa Partager una sola vez (nunca se reintenta) y observa el resultado.

    Estados: «confirmado» (banner, compositor cerrado y el perfil suma una publicación),
    «confirmado_sin_conteo» (igual, pero falta uno de los dos conteos, o `produccion_cercana`:
    el publicador de producción pudo sumar la suya), «conteo_no_cuadra», «fallido»,
    «sin_banner», «timeout» y «error_tras_pulsar». Desde la pulsación nada se propaga."""

    def observador_nuevo(boton: dict):
        banners_vistos: list[tuple[int, int, int, int]] = []  # el error puede salir cuando el banner ya se fue

        def observar(xml: str) -> dict:
            obs = observacion_de_volcado(xml, boton["bounds"], banners_vistos)
            banners_vistos.extend(banners_de_volcado(xml))
            return obs
        return observar

    def despues(resultado: dict, estado: str) -> str:
        avisos = resultado["avisos"]
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
            publicaciones_despues = resultado["publicaciones_despues"]
            if publicaciones_antes is None or publicaciones_despues is None:
                estado = "confirmado_sin_conteo"
            elif publicaciones_despues != publicaciones_antes + 1:
                estado = "conteo_no_cuadra"
            elif produccion_cercana:
                estado = "confirmado_sin_conteo"
                avisos.append("producción publicó cerca: el +1 del perfil no prueba que sea esta publicación")
        return estado

    return pasos.enviar(
        paquete=PAQUETE, nombre_app="Instagram", etiqueta="Partager", evidencia=evidencia,
        captura_antes="ig-05a-antes.png", captura_final="ig-05-publicado.png", captura_error="ig-05-error.png",
        listo=lambda x, emergentes: compositor_listo(x, pie, tema, emergentes),
        botones=lambda x: telefono.buscar_todos(x, texto="Partager", paquete=PAQUETE),
        observador_nuevo=observador_nuevo, despues=despues,
        extra={"publicaciones_antes": publicaciones_antes, "publicaciones_despues": None})
