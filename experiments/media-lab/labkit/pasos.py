"""
Pasos con E/S comunes a todos los flujos del teléfono.

Un paso por llamada y nunca a ciegas: si un control no aparece o es ambiguo se lanza
PantallaInesperada y no se toca nada más. Ningún paso despierta ni desbloquea el teléfono
(MaaS360). Todo el tiempo pasa por `labkit.reloj` y todo el teléfono por `labkit.telefono`,
para que las pruebas los sustituyan sin tocar nada más.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import phone_clipboard
from labkit import pantalla, reloj, telefono
from labkit.pantalla import PantallaInesperada

ATRAS, CTRL_IZQ, TECLA_A = 4, 113, 29
ESPERA_S = 25
OBSERVACION_S = 90
CAPTURA_ERROR_S = 10  # la captura tras un error es best-effort: no alarga la salida
VOLCADOS_LIMPIOS = 3  # seguidos, sin teclado ni desplegable, antes de dar un texto pegado por bueno
ESPERA_ENTRE_VOLCADOS_S = 2.5
INTENTOS_ATRAS = 2  # tope total de «atrás» para cerrar teclado o desplegable tras pegar
ESTABILIZACION_TIMEOUT_S = 60
VOLCADO_NO_VALIDO = {"valido": False, "compositor": False, "banner": False, "fallo": False}
# Claves propias del resultado de `enviar`: un `extra` que las redefina es un error del llamador,
# no algo que se deba resolver a ciegas fusionando diccionarios.
CLAVES_RESERVADAS_ENVIO = {"estado", "error", "submitted_at", "processing_completed_at", "captura",
                          "captura_antes", "captura_error", "avisos"}


class BorradorPendiente(PantallaInesperada):
    """La app abrió con una publicación a medias: la resuelve una persona."""


class TelefonoNoListo(PantallaInesperada):
    """Dormido, bloqueado o sin adb. No se intenta arreglar."""


def exigir_listo() -> None:
    e = telefono.estado()
    if not e["listo"]:
        raise TelefonoNoListo(f"el teléfono no está listo (no se despierta ni se desbloquea): {e}")


def esperar_que(cumple, descripcion: str) -> str:
    """Primer volcado válido que cumple la condición.

    El plazo de ESPERA_S se comprueba entre volcados y cada volcado recibe el tiempo que
    queda (5 s como mínimo), así que la espera total puede pasar de ESPERA_S en lo que tarde
    el último volcado."""
    inicio = reloj.monotonic()
    ultimo_error = ""
    while True:
        restante = max(5, int(ESPERA_S - (reloj.monotonic() - inicio)))
        try:
            xml = telefono.volcado(timeout=restante)
            if cumple(xml):
                return xml
        except telefono.TelefonoError as e:
            ultimo_error = f" (último error: {e})"
        transcurrido = reloj.monotonic() - inicio
        if transcurrido >= ESPERA_S:
            raise PantallaInesperada(f"no apareció {descripcion} tras {transcurrido:.1f} s{ultimo_error}")
        reloj.dormir(1.5)


def volcado_fresco() -> str:
    return esperar_que(lambda xml: True, "un volcado válido")


def esperar_estable(lectura, n: int | None = None,
                     descripcion: str = "una lectura estable") -> tuple[str, object]:
    """(xml, valor) cuando `n` (VOLCADOS_LIMPIOS si no se da) volcados frescos seguidos dan el
    mismo `lectura(xml)` no nulo (None y False reinician la cuenta). Los volcados pueden ir con
    retraso: esta es la regla antes de cualquier lectura decisiva. El plazo total se comprueba
    al empezar cada vuelta."""
    n = VOLCADOS_LIMPIOS if n is None else n
    inicio = reloj.monotonic()
    previo, seguidos = None, 0
    while True:
        if reloj.monotonic() - inicio >= ESTABILIZACION_TIMEOUT_S:
            raise PantallaInesperada(
                f"no hubo {descripcion} en {n} volcados seguidos tras {ESTABILIZACION_TIMEOUT_S} s")
        xml = volcado_fresco()
        valor = lectura(xml)
        if valor is None or valor is False:
            previo, seguidos = None, 0
        elif seguidos and valor == previo:
            seguidos += 1
        else:
            previo, seguidos = valor, 1
        if seguidos >= n:
            return xml, valor
        reloj.dormir(ESPERA_ENTRE_VOLCADOS_S)


def escribir_texto(texto: str, paquete: str, *,
                    campo: Callable[[str], dict | None],
                    exigir: Callable[[str], None],
                    desplegable_nodos: Callable[[str], bool],
                    emergente: Callable[[str, list[dict]], dict | None],
                    volcados_limpios: int | None = None,
                    intentos_atras: int | None = None,
                    timeout: float | None = None,
                    verificar: Callable[[str, str], bool] | None = None) -> str:
    """Pega `texto` en el campo y devuelve el volcado final con la pantalla estable.

    `campo(xml)` localiza el campo (None si no está), `exigir(xml)` lanza PantallaInesperada si la
    pantalla ya no es la del compositor con el texto, `desplegable_nodos(xml)` dice si el volcado muestra
    sugerencias abiertas y `emergente(xml, emergentes)` devuelve la ventana emergente de
    `telefono.ventanas_emergentes(paquete)` que se solapa con los controles del compositor, o None: un
    desplegable de sugerencias puede ser una PopupWindow que `uiautomator dump` no ve (tarea 10f). Una
    emergente que se solapa y parece un desplegable (`pantalla.parece_desplegable`) cuenta como abierto;
    una que se solapa pero no lo parece para con PantallaInesperada sin pulsar «atrás»; un TelefonoError de
    `ventanas_emergentes` se propaga sin pulsar nada.

    `volcados_limpios`, `intentos_atras` y `timeout` sustituyen a VOLCADOS_LIMPIOS, INTENTOS_ATRAS y
    ESTABILIZACION_TIMEOUT_S cuando no son `None`. `verificar(xml, texto)` decide si el texto pegado
    quedó bien escrito; por defecto exige un nodo con `text` exactamente igual dentro de `paquete`
    (`pantalla.tiene_texto`), lo probado hoy en Instagram: Threads y Facebook pueden partir el texto en
    varios nodos, y cada tarea de app confirma en S1 si aquí hace falta otra comparación.

    No da la pantalla por buena hasta ver `volcados_limpios` volcados frescos seguidos sin teclado ni
    desplegable: la app puede abrir sugerencias unos segundos después de pegar. Si solo el desplegable pide
    cerrar, se confirma con un volcado fresco antes de pulsar «atrás». Cada «atrás» reinicia la cuenta, con
    un tope de `intentos_atras` y otro de `timeout` (comprobado al empezar cada vuelta). Si no se sabe si
    el teclado está abierto, se para sin pulsar: un «atrás» con todo cerrado sacaría del compositor."""
    volcados_limpios = VOLCADOS_LIMPIOS if volcados_limpios is None else volcados_limpios
    intentos_atras = INTENTOS_ATRAS if intentos_atras is None else intentos_atras
    timeout = ESTABILIZACION_TIMEOUT_S if timeout is None else timeout
    verificar = verificar or (lambda xml, texto: pantalla.tiene_texto(xml, texto=texto, paquete=paquete))

    exigir_listo()
    xml = esperar_que(lambda x: campo(x) is not None, f"el campo de texto de {paquete}")
    telefono.tocar(*campo(xml)["centro"])
    reloj.dormir(2)
    telefono.combinacion(CTRL_IZQ, TECLA_A)
    exigir_listo()
    try:
        phone_clipboard.pegar(texto, paste=True)
    except (RuntimeError, OSError) as e:
        raise telefono.TelefonoError(f"portapapeles: {e}") from e
    reloj.dormir(2)
    xml = volcado_fresco()
    if not verificar(xml, texto):
        raise PantallaInesperada(f"el texto leído de {paquete} no coincide con el archivo")

    def estado_cierre(x: str) -> tuple[bool, bool, dict | None]:
        teclado = telefono.teclado_estado()
        if teclado is None:
            raise PantallaInesperada("no se puede leer si el teclado está abierto")
        culpable = emergente(x, telefono.ventanas_emergentes(paquete))
        if culpable is not None and not pantalla.parece_desplegable(culpable):
            raise PantallaInesperada(
                f"una ventana emergente se solapa pero no parece un desplegable de sugerencias "
                f"({pantalla.describe_emergente(culpable)}): no se pulsa «atrás»")
        return teclado, desplegable_nodos(x) or culpable is not None, culpable

    atras_usados = 0
    limpios = 0
    inicio = reloj.monotonic()
    while limpios < volcados_limpios:
        if reloj.monotonic() - inicio >= timeout:
            raise PantallaInesperada(f"el compositor no se estabilizó tras {timeout} s pegando el texto")
        exigir(xml)
        teclado, abierto, culpable = estado_cierre(xml)
        if not teclado and abierto:
            xml = volcado_fresco()
            exigir(xml)
            teclado, abierto, culpable = estado_cierre(xml)
        if teclado or abierto:
            atras_usados += 1
            if atras_usados > intentos_atras:
                detalle = f" ({pantalla.describe_emergente(culpable)})" if culpable is not None else ""
                raise PantallaInesperada(
                    f"el teclado o el desplegable siguen abiertos tras {intentos_atras} «atrás»{detalle}")
            telefono.tecla(ATRAS)
            reloj.dormir(2)
            xml = volcado_fresco()
            limpios = 0
            continue
        limpios += 1
        if limpios < volcados_limpios:
            reloj.dormir(ESPERA_ENTRE_VOLCADOS_S)
            xml = volcado_fresco()
    return xml


def atras(paquete: str, evidencia: Path, nombre: str) -> Path:
    """«Atrás» solo con `paquete` en primer plano."""
    exigir_listo()
    xml = volcado_fresco()
    if telefono.buscar(xml, paquete=paquete) is None:
        raise PantallaInesperada(f"{paquete} no está en primer plano: no se pulsa «atrás»")
    telefono.tecla(ATRAS)
    reloj.dormir(3)
    return telefono.captura(evidencia / f"{nombre}.png")


def observar_envio(boton: dict, observador: Callable[[str], dict], plazo: float | None = None,
                    resultado: dict | None = None) -> tuple[str, dict | None]:
    """Pulsa `boton` UNA vez y observa cada 1,5 s con `observador(xml) -> observación` hasta
    `plazo` (OBSERVACION_S si no se da) o hasta que `pantalla.evaluar_envio` dé confirmado o
    fallido. Si se da `resultado`, se le añaden `submitted_at` y, si se confirma,
    `processing_completed_at`: los dos únicos campos que dependen del instante exacto de la
    observación, no del resultado (que decide quien llama). Devuelve `(estado, culpable)`:
    `culpable` es la observación que hizo fallar el envío, o None si no falló. Puede lanzar (el
    toque o el observador): quien llama lo recoge."""
    plazo = OBSERVACION_S if plazo is None else plazo
    resultado = {} if resultado is None else resultado
    resultado["submitted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    telefono.tocar(*boton["centro"])
    observaciones: list[dict] = []
    inicio = reloj.monotonic()
    while reloj.monotonic() - inicio < plazo:
        reloj.dormir(1.5)
        try:
            observaciones.append(observador(telefono.volcado()))
        except telefono.TelefonoError:
            observaciones.append(dict(VOLCADO_NO_VALIDO))
        parcial = pantalla.evaluar_envio(observaciones)
        if parcial == "confirmado":
            resultado["processing_completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            break
        if parcial == "fallido":
            break
    estado = pantalla.evaluar_envio(observaciones)
    culpable = next((o for o in observaciones if o.get("fallo")), None) if estado == "fallido" else None
    return estado, culpable


def enviar(*, paquete: str, nombre_app: str, etiqueta: str, evidencia: Path,
           captura_antes: str, captura_final: str, captura_error: str,
           listo: Callable[[str, list[dict]], list[str]],
           botones: Callable[[str], list[dict]],
           observador_nuevo: Callable[[dict], Callable[[str], dict]],
           despues: Callable[[dict, str], str],
           extra: dict | None = None, plazo: float | None = None) -> dict:
    """Comparte con un solo toque, para cualquier app.

    Antes de pulsar: teléfono listo, teclado cerrado, captura `captura_antes`, `listo(xml, emergentes)`
    (con `telefono.ventanas_emergentes`, que falla cerrado si `dumpsys` falla) sin problemas en dos
    volcados seguidos y `botones(xml)` en los mismos bounds en los dos. `extra` no puede redefinir las
    claves propias del resultado (`ValueError` antes de tocar nada si lo intenta). `observador_nuevo(boton)`
    y una segunda comprobación de `exigir_listo()` se hacen justo antes del toque pero fuera del `try`
    que lo envuelve: si cualquiera de las dos falla ahí, no se ha pulsado nada y no cuenta como
    «error_tras_pulsar». Desde el toque nada se propaga: `despues(resultado, estado)` lee la confirmación
    de la app y devuelve el estado final, la captura final es `captura_final` y cualquier excepción tras
    el toque deja «error_tras_pulsar» con la captura best-effort `captura_error`."""
    if extra and CLAVES_RESERVADAS_ENVIO & extra.keys():
        chocan = sorted(CLAVES_RESERVADAS_ENVIO & extra.keys())
        raise ValueError(f"extra no puede redefinir claves propias del resultado: {chocan}")
    plazo = OBSERVACION_S if plazo is None else plazo
    exigir_listo()
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está visible (o no se sabe): no se comparte")
    ruta_antes = str(telefono.captura(evidencia / captura_antes))
    xml1 = volcado_fresco()
    problemas = listo(xml1, telefono.ventanas_emergentes(paquete))
    if problemas:
        raise PantallaInesperada(f"el compositor no está listo para compartir: {problemas}")
    reloj.dormir(1.5)
    xml2 = volcado_fresco()
    problemas = listo(xml2, telefono.ventanas_emergentes(paquete))
    if problemas:
        raise PantallaInesperada(f"el compositor no está listo para compartir (2.º volcado): {problemas}")
    posiciones = [[n["bounds"] for n in botones(x)] for x in (xml1, xml2)]
    if posiciones[0] != posiciones[1]:
        raise PantallaInesperada(f"«{etiqueta}» se ha movido entre volcados: {posiciones}")
    candidatos = botones(xml2)
    if not candidatos:
        raise PantallaInesperada(f"no aparece «{etiqueta}» de {nombre_app}")
    boton = pantalla.elegir(candidatos, etiqueta)

    resultado = {"estado": None, "error": None, "submitted_at": None, "processing_completed_at": None,
                 "captura": None, "captura_antes": ruta_antes, "captura_error": None, "avisos": [],
                 **(extra or {})}
    avisos = resultado["avisos"]
    observador = observador_nuevo(boton)  # antes del toque: si falla aquí no es «error_tras_pulsar»
    exigir_listo()  # puede haber dejado de estar listo entre el 2.º volcado y este punto
    try:
        estado, culpable = observar_envio(boton, observador, plazo, resultado)
        if estado == "fallido" and culpable:
            avisos.append(f"{nombre_app} avisó de un error: {culpable.get('fallo_texto')!r} "
                          f"en {culpable.get('fallo_bounds')}")
        resultado["estado"] = despues(resultado, estado)
        try:
            resultado["captura"] = str(telefono.captura(evidencia / captura_final))
        except telefono.TelefonoError as e:
            avisos.append(f"no se pudo capturar tras compartir: {e}")
    except Exception as e:  # noqa: BLE001 — tras pulsar, el resultado tiene que volver siempre
        resultado["estado"] = "error_tras_pulsar"
        resultado["error"] = f"{type(e).__name__}: {e}"
        try:
            resultado["captura_error"] = str(
                telefono.captura(evidencia / captura_error, timeout=CAPTURA_ERROR_S))
        except Exception as e_captura:  # noqa: BLE001 — best-effort: el resultado vuelve igual
            avisos.append(f"no se pudo capturar tras el error: {type(e_captura).__name__}: {e_captura}")
    return resultado
