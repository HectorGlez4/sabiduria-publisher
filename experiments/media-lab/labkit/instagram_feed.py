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

from labkit import pantalla, pasos, reloj, telefono
from labkit.instagram_pantallas import *  # noqa: F401,F403 — reexporta `instagram_pantallas.__all__`
from labkit.instagram_pantallas import (MARCA, PAQUETE, PantallaInesperada, _campos, _coincidencias,
                                        _exigir_compositor_con_pie, _nodo, _suivant, banners_de_volcado,
                                        campo_pie, compositor_listo, emergente_desplegable, gesto_de_refresco,
                                        hay_desplegable_hashtags, miniatura_coincide, observacion_de_volcado,
                                        perfil_activo, publicaciones_de_perfil, punto_mas, seleccion_unica,
                                        tema_de_chip)
# ATRAS y ESTABILIZACION_TIMEOUT_S los usan los pasos de aquí (`atras`, docstrings); CTRL_IZQ y TECLA_A ya
# no (van dentro de `pasos.escribir_texto`): solo lectura, se quedan reexportados porque las pruebas de la
# fase 1 los leen como IG.CTRL_IZQ/IG.TECLA_A.
from labkit.pasos import (ATRAS, CTRL_IZQ, ESTABILIZACION_TIMEOUT_S, TECLA_A,  # noqa: F401
                          BorradorPendiente, TelefonoNoListo)


AVISO_ARRANQUE_EN_FRIO = f"(tras un arranque en frío: am force-stop de {PAQUETE})"
CAPTURA_ANTES_DE_ARRANQUE = "ig-00-antes-de-arranque-en-frio.png"
# Actividad de todo el flujo de creación de Instagram (selector, editor y compositor):
# `com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity`. Consta en el plan de la fase 1
# (sonda SONDA-10F) como ventana padre del desplegable de hashtags y, en el teléfono el 2026-09-15, como foco con el
# selector «Nouvelle publication» abierto.
ACTIVIDAD_CREACION = "MediaCaptureActivity"
DESLIZAR_REFRESCO_MS = 400
ESPERA_TRAS_REFRESCO_S = 3  # el perfil tarda en recargar: dos volcados seguidos antes de eso darían el recuento viejo
VOLCADOS_RECUENTO = 2


def _esperar(zona: str | None = None, **kw) -> str:
    return pasos.esperar_que(lambda xml: bool(_coincidencias(xml, zona, **kw)), f"{kw}")


def _recuento_fresco(xml: str, avisos: list[str]) -> dict:
    """Recuento de publicaciones con el perfil de la marca recargado. `xml` es el volcado del perfil ya verificado
    (@marca con «Modifier le profil»); nunca lanza, todo lo que no sale bien va a `avisos`.

    Desliza UNA vez hacia abajo con `gesto_de_refresco` (pull-to-refresh), espera ESPERA_TRAS_REFRESCO_S y exige el
    mismo recuento en VOLCADOS_RECUENTO volcados frescos seguidos del perfil de la marca (`pasos.esperar_estable`).
    Si el gesto no se puede situar o su inicio o su final caen sobre un control que no se toca
    (`pantalla.punto_bloqueado`), no desliza y devuelve la lectura de `xml` sin refrescar. Si el gesto o la espera
    fallan (no se estabiliza, `TelefonoError`…), el recuento es None.

    Devuelve `{"recuento", "refrescado", "deslizado", "xml"}`: `refrescado` solo si se deslizó y el recuento se
    estabilizó; `deslizado` si se llegó a pedir el gesto (la pantalla puede haber cambiado); `xml`, el último volcado
    estable del perfil, o None si no lo hay."""
    fuera = {"recuento": publicaciones_de_perfil(xml), "refrescado": False, "deslizado": False, "xml": None}
    try:
        x1, y1, x2, y2 = gesto_de_refresco(xml)
    except PantallaInesperada as e:
        avisos.append(f"no se refrescó el perfil ({e}): recuento sin refrescar")
        return fuera
    for extremo, (x, y) in (("empieza", (x1, y1)), ("acaba", (x2, y2))):
        culpable = pantalla.punto_bloqueado(xml, x, y)
        if culpable is not None:
            etiqueta = culpable["texto"] or culpable["desc"] or culpable["resource_id"]
            avisos.append(f"no se refrescó el perfil: el gesto {extremo} en ({x}, {y}) sobre {etiqueta!r}, "
                          f"que no se toca: recuento sin refrescar")
            return fuera

    def lectura(x: str) -> int | None:
        if perfil_activo(x) != MARCA or not _coincidencias(x, contiene="Modifier le profil"):
            return None
        return publicaciones_de_perfil(x)

    fuera.update(recuento=None)
    try:
        pasos.exigir_listo()
        fuera["deslizado"] = True
        telefono.deslizar(x1, y1, x2, y2, DESLIZAR_REFRESCO_MS)
        reloj.dormir(ESPERA_TRAS_REFRESCO_S)
        estable, recuento = pasos.esperar_estable(lectura, VOLCADOS_RECUENTO, "el recuento del perfil tras refrescar")
    except (PantallaInesperada, telefono.TelefonoError, OSError) as e:
        avisos.append(f"el refresco del perfil falló, sin recuento: {type(e).__name__}: {e}")
        return fuera
    return {**fuera, "recuento": recuento, "refrescado": True, "xml": estable}


def abrir_nueva_publicacion(evidencia: Path, subido_en: datetime | str) -> dict:
    """Desde el perfil de la marca hasta el selector con la foto recién subida marcada.

    `lanzar` reanuda Instagram donde se quedó; con un vídeo en marcha (un Reel abierto desde un mensaje
    directo) ningún volcado llega a leerse. Solo en ese caso (`pasos.SinVolcado`: nada leído, así que no hay
    ningún borrador visto que proteger) se fuerza el cierre UNA vez, se relanza en frío y se vuelve a esperar
    con el mismo criterio; el resultado lo anota en `arranque_en_frio`. Si algún volcado se leyó, el error
    sale como siempre y la app no se toca. Todo `PantallaInesperada`, `TelefonoError` u `OSError` desde el intento
    de `forzar_cierre` en adelante sale con el mismo tipo y `AVISO_ARRANQUE_EN_FRIO` al final del mensaje; si ese
    tipo no se puede construir con un solo mensaje (p. ej. `urllib.error.HTTPError`), sale como `PantallaInesperada`
    con el nombre del tipo delante, encadenado al original.

    `publicaciones_antes` sale de `_recuento_fresco`: Instagram puede tener el perfil en memoria con un recuento
    desfasado (medido el 2026-09-15). El resultado dice en `recuento_refrescado` si se recargó y estabilizó, y en
    `avisos` por qué no; si el refresco falla, `publicaciones_antes` es None y el paso sigue."""
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
        xml = pasos.esperar_que(
            lambda x: bool(_coincidencias(x, "abajo", texto="Profil"))
            or telefono.buscar(x, texto="Nouvelle publication", paquete=PAQUETE) is not None
            or bool(_campos(x)),
            "Instagram listo (Profil, «Nouvelle publication» o el campo del pie)")
        if telefono.buscar(xml, texto="Nouvelle publication", paquete=PAQUETE) or _campos(xml):
            raise BorradorPendiente("Instagram abrió con una publicación a medias: no se toca")
        return xml

    arranque_en_frio = False
    try:
        try:
            xml = lanzar_y_esperar()
        except pasos.SinVolcado as sin_volcado:
            pasos.exigir_listo()
            _exigir_arranque_en_frio_seguro(evidencia, sin_volcado)
            arranque_en_frio = True  # desde aquí, cualquier error lleva el aviso (también si falla el cierre)
            telefono.forzar_cierre(PAQUETE)
            xml = lanzar_y_esperar()  # si vuelve a fallar, el error sale con el aviso: no hay otro cierre
        telefono.tocar(*_nodo(xml, "abajo", texto="Profil")["centro"])
        xml = _esperar(contiene="Modifier le profil")
        perfil = perfil_activo(xml)
        if perfil != MARCA:
            raise PantallaInesperada(f"el perfil activo es {perfil!r}, no @{MARCA}")
        avisos: list[str] = []
        fresco = _recuento_fresco(xml, avisos)
        publicaciones_antes = fresco["recuento"]
        if fresco["xml"] is not None:
            xml = fresco["xml"]  # ya es el perfil de la marca, leído tras el refresco
        elif fresco["deslizado"]:
            xml = _esperar(contiene="Modifier le profil")  # el gesto pudo mover la pantalla: se vuelve a verificar
            perfil = perfil_activo(xml)
            if perfil != MARCA:
                raise PantallaInesperada(f"tras refrescar el perfil activo es {perfil!r}, no @{MARCA}")
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
                "publicaciones_antes": publicaciones_antes, "recuento_refrescado": fresco["refrescado"],
                "arranque_en_frio": arranque_en_frio, "avisos": avisos}
    except (PantallaInesperada, telefono.TelefonoError, OSError) as e:
        if not arranque_en_frio:
            raise
        try:
            nuevo = type(e)(f"{e} {AVISO_ARRANQUE_EN_FRIO}")
        except TypeError:  # subclases con constructor de varios argumentos (p. ej. urllib.error.HTTPError)
            raise PantallaInesperada(f"{type(e).__name__}: {e} {AVISO_ARRANQUE_EN_FRIO}") from e
        raise nuevo from e


def _exigir_arranque_en_frio_seguro(evidencia: Path, sin_volcado: pasos.SinVolcado) -> None:
    """Defensa barata antes de `forzar_cierre`: una captura (`screencap` no depende de uiautomator) y los focos de
    ventana (`mCurrentFocus` y `mFocusedApp`). Si la captura falla, no se puede leer ningún foco o CUALQUIERA de los
    dos está en `MediaCaptureActivity`, el flujo de creación (selector, editor y compositor), aunque el otro sea un
    diálogo de permisos encima, NO se fuerza el cierre: sale un `SinVolcado` con el mensaje original y el motivo."""
    def no_se_cierra(motivo: str) -> pasos.SinVolcado:
        return pasos.SinVolcado(f"{sin_volcado}; no se forzó el cierre de Instagram: {motivo}")

    try:
        telefono.captura(evidencia / CAPTURA_ANTES_DE_ARRANQUE)
    except (telefono.TelefonoError, OSError) as e:
        raise no_se_cierra(f"falló la captura previa ({e})") from sin_volcado
    focos = telefono.focos()
    if not focos:
        raise no_se_cierra("no se pudo leer el foco de ventana (ni mCurrentFocus ni mFocusedApp en dumpsys window)") \
            from sin_volcado
    en_creacion = [f for f in focos if ACTIVIDAD_CREACION in f]
    if en_creacion:
        raise no_se_cierra(f"un foco está en el flujo de creación (selector, editor y compositor: "
                           f"{', '.join(en_creacion)}): puede haber una publicación a medias") from sin_volcado


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
    «sin_banner», «timeout» y «error_tras_pulsar». Desde la pulsación nada se propaga.

    `publicaciones_despues` sale de `_recuento_fresco` (perfil recargado y recuento estable); si el refresco
    falla, queda None con el motivo en `avisos`."""

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
                    try:  # tras pulsar: el refresco es best-effort y nunca cambia el estado por lanzar
                        resultado["publicaciones_despues"] = _recuento_fresco(xml, avisos)["recuento"]
                    except Exception as e:  # noqa: BLE001
                        avisos.append(f"el refresco del perfil tras compartir falló: {type(e).__name__}: {e}")
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
