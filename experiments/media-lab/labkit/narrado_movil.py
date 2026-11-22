"""
Publicar un reel narrado desde el móvil del laboratorio, paso a paso (fase 2).

La ruta es la de la sonda del 22 nov (`narrados/sonda-movil-2026-11-22.md`): subir el mp4 a
MediaStore → perfil de la marca → portada → «Créer» → galería «Nouveau reel» → la casilla del vídeo
subido → editor → «Suivant» → detalles → pie, mención IA y cruces apagados → «Partager» (`publicar`, una vez) →
`verificar` (recuento del perfil y pie del Reel más reciente; registro y borrado del vídeo). Cada paso lee `build/movil.json`,
hace su parte y lo deja en el paso siguiente. Nada se adivina: si una pantalla no es la esperada,
PantallaInesperada y no se toca más.

Todo el teléfono pasa por `pasos.*` (los toques, por `pasos.tocar`, que no pulsa nada que publique; el único
«Partager», por `pasos.enviar` desde `publicar`) y por funciones con nombre de `telefono`. Del bucle del sitio solo se usan `exigir_cuenta` (en `abrir`, antes de
compartir; nunca en `verificar`, porque su recuperación cierra Instagram), a través de la referencia de este módulo, que
las pruebas sustituyen porque llama a `telefono.shell`, y la excepción `CuentaAjena`.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from labkit import instagram_pantallas as ip
from labkit import narrado, narrado_pie, pantalla, pasos, reloj, telefono, textos
from labkit import sitio_instagram as si
from labkit.pantalla import PantallaInesperada

IG = textos.PAQUETES["instagram"]
CUENTA = textos.MARCAS["instagram"]
TOLERANCIA_MIN = 1  # la casilla lleva la hora de la subida, al minuto
NO_SUBIR_OTRA_VEZ = ("compartido", "verificado", "incierto")

exigir_cuenta = si.exigir_cuenta

# resource-id (sin el paquete) de cada control, medidos en la sonda del 22 nov
ID_INICIO = "feed_tab"
ID_CREAR = "action_bar_left_button"
ID_TITULO_GALERIA = "gallery_title_text"
ID_MINIATURA = "gallery_grid_item_thumbnail"
ID_ETIQUETA = "gallery_grid_item_label"
ID_SIGUIENTE = "clips_right_action_button"
ID_PIE = "caption_input_text_view"
ID_TITULO = "action_bar_title"
ID_BARRA_ACCION = "action_bar_new_title_container"  # arriba, con «Retour» y el título
ID_BARRA_ABAJO = "share_button_container"  # abajo, fija: «Enregistrer le brouillon» y «Partager»
ID_COMPARTIR = "share_button"
ID_BORRADOR = "save_draft_button"
ID_LISTA = "scroll_view"

# El gesto que mueve la lista de detalles: vertical, a X_GESTO_PX del borde izquierdo de la lista (a la izquierda de
# los títulos de fila, que empiezan en x=147), a MARGEN_GESTO_PX como poco de las dos barras, DESLIZAR_PX de recorrido
# en DESLIZAR_MS (lento: arrastra, no lanza) y como mucho MAX_DESLIZAMIENTOS seguidos para ver las filas.
X_GESTO_PX = 60
MARGEN_GESTO_PX = 100
DESLIZAR_PX = 600
DESLIZAR_MS = 800
RECORRIDO_MINIMO_PX = 200
MAX_DESLIZAMIENTOS = 4


def _t(clave: str) -> str:
    return textos.texto("instagram", clave)


class MiniaturaAusente(PantallaInesperada):
    """Ninguna casilla de la galería es el vídeo subido (todavía, o nunca)."""


# ---------------------------------------------------------------- lectura pura

def nombre_remoto(pieza_id: str, sha256_mp4: str) -> str:
    return f"{pieza_id}-{sha256_mp4[:8]}.mp4"


def etiqueta_duracion(duracion_ms: int) -> str:
    """La etiqueta de duración de la galería: segundos redondeados, «m:ss» (27 533 ms → «0:28»)."""
    segundos = (duracion_ms + 500) // 1000
    return f"{segundos // 60}:{segundos % 60:02d}"


def _por_id(xml: str, rid: str) -> list[dict]:
    return [n for n in telefono.nodos(xml) if n["package"] == IG and n["resource_id"] == f"{IG}:id/{rid}"]


def _unico(xml: str, rid: str, *, desc: str | None = None, texto: str | None = None) -> dict:
    lista = [n for n in _por_id(xml, rid)
             if (desc is None or n["desc"] == desc) and (texto is None or n["texto"] == texto)]
    if len(lista) != 1:
        que = desc or texto or ""
        raise PantallaInesperada(f"se esperaba un solo {rid} {que!r} y hay {len(lista)}: no se toca")
    return lista[0]


def _etiqueta_de(lista: list[dict], i: int) -> str | None:
    """El texto de la única `gallery_grid_item_label` hermana de la casilla `lista[i]` (mismo padre)."""
    nivel = lista[i]["profundidad"]
    padre = next((j for j in range(i - 1, -1, -1) if lista[j]["profundidad"] < nivel), None)
    if padre is None:
        return None
    etiquetas = []
    for n in lista[padre + 1:]:
        if n["profundidad"] <= lista[padre]["profundidad"]:
            break
        if n["profundidad"] == nivel and n["resource_id"] == f"{IG}:id/{ID_ETIQUETA}":
            etiquetas.append(n["texto"])
    return etiquetas[0] if len(etiquetas) == 1 else None


def elegir_miniatura(xml: str, subido_en: str, duracion_ms: int) -> dict:
    """La única casilla de la galería que es el vídeo subido: descripción de vídeo con una hora (local
    del teléfono, ver `ip.miniatura_coincide`) a un minuto como mucho de `subido_en`, y su propia etiqueta
    de duración igual a `etiqueta_duracion(duracion_ms)`. Nunca «la primera casilla»: la sonda vio otro
    vídeo de 0:28 en la galería. Ninguna (MiniaturaAusente) o varias: PantallaInesperada con cuántas."""
    momento = datetime.fromisoformat(subido_en)
    if momento.tzinfo is None:
        raise ValueError(f"subido_en sin zona horaria: {subido_en!r}")
    duracion = etiqueta_duracion(duracion_ms)
    lista = telefono.nodos(xml)
    casan = [n for i, n in enumerate(lista)
             if n["package"] == IG and n["resource_id"] == f"{IG}:id/{ID_MINIATURA}"
             and _t("miniatura_video") in n["desc"]
             and ip.miniatura_coincide(n["desc"], momento, tolerancia_min=TOLERANCIA_MIN)
             and _etiqueta_de(lista, i) == duracion]
    if len(casan) != 1:
        error = MiniaturaAusente if not casan else PantallaInesperada
        raise error(f"{len(casan)} casillas de la galería casan con el vídeo subido ({subido_en}, {duracion}): "
                    "hace falta exactamente una")
    return casan[0]


def _es_galeria(xml: str) -> bool:
    return bool(_por_id(xml, ID_TITULO_GALERIA))


def _es_galeria_reel(xml: str) -> bool:
    return any(n["texto"] == _t("nuevo_reel") for n in _por_id(xml, ID_TITULO_GALERIA))


def _es_editor(xml: str) -> bool:
    return any(n["desc"] == _t("siguiente") for n in _por_id(xml, ID_SIGUIENTE))


def _es_detalles(xml: str) -> bool:
    return bool(_por_id(xml, ID_PIE)) and any(n["texto"] == _t("nuevo_reel") for n in _por_id(xml, ID_TITULO))


def _es_portada(xml: str) -> bool:
    return any(n["desc"] == _t("crear") for n in _por_id(xml, ID_CREAR))


# ---------------------------------------------------------------- estado

def _estado_en(pieza_id: str, pasos_validos: tuple[str, ...], raiz: Path | None) -> dict:
    estado = narrado.estado_movil(pieza_id, raiz)
    if estado.get("paso") not in pasos_validos:
        raise ValueError(f"{pieza_id}: el móvil está en {estado.get('paso')!r} y este paso necesita "
                         f"{' o '.join(pasos_validos)}")
    return estado


# ---------------------------------------------------------------- subir

def subir(pieza_id: str, ev: Path, raiz: Path | None = None) -> dict:
    """Sube el mp4 revisado al teléfono y deja el estado en «subido».

    Antes de nada: `apto_para_publicar` vacío (si no, ValueError con los problemas), ninguna línea del registro
    para la cita de la pieza (`narrado.ya_compartida`, que sobrevive a una reconstrucción) y ninguna publicación
    ya compartida de este build. Luego teléfono listo → `telefono.subir_video` con el nombre
    `<pieza>-<8 hex>.mp4` → el sha256 subido es el del informe → estado → captura."""
    problemas = narrado.apto_para_publicar(pieza_id, raiz)
    if problemas:
        raise ValueError(f"{pieza_id} no se puede publicar: {'; '.join(problemas)}")
    registro = narrado.ya_compartida(pieza_id, raiz)
    if registro is not None:
        raise ValueError(f"{pieza_id}: {_texto_registro(registro)}: esta cita no se vuelve a subir")
    previo = narrado.estado_movil(pieza_id, raiz).get("paso")
    if previo in NO_SUBIR_OTRA_VEZ:
        raise ValueError(f"{pieza_id} ya está «{previo}» en el móvil: este build no se vuelve a subir")
    informe = narrado.informe_de(pieza_id, raiz)
    pasos.exigir_listo()
    nombre = nombre_remoto(pieza_id, informe["sha256_mp4"])
    subido = telefono.subir_video(Path(informe["mp4"]), nombre)
    if subido["sha256"] != informe["sha256_mp4"]:
        telefono.borrar_video(nombre)
        raise ValueError(f"el vídeo subido ({subido['sha256'][:8]}) no es el revisado "
                         f"({informe['sha256_mp4'][:8]}): se ha borrado del teléfono")
    estado = {"paso": "subido", "nombre_remoto": nombre, "sha256": subido["sha256"],
              "subido_en": subido["subido_en"], "duracion_ms": subido["duracion_ms"]}
    narrado.guardar_estado_movil(pieza_id, estado, raiz)
    telefono.captura(ev / "subir-1.png")
    return estado


# ---------------------------------------------------------------- abrir

def abrir(pieza_id: str, ev: Path, raiz: Path | None = None) -> dict:
    """Del estado «subido» a la pantalla de detalles del reel con el vídeo subido; estado «abierto».

    Teléfono listo → cuenta de la marca → publicaciones del perfil → portada → «Créer» → galería
    «Nouveau reel» → la casilla del vídeo → editor → «Suivant» → detalles."""
    estado = _estado_en(pieza_id, ("subido",), raiz)
    pasos.exigir_listo()
    exigir_cuenta(CUENTA)
    perfil, antes = _publicaciones_del_perfil()
    portada = _ir_a_la_portada(perfil)
    _abrir_galeria(portada)
    casilla, galeria = _miniatura_estable(estado["subido_en"], estado["duracion_ms"])
    pasos.tocar(casilla, galeria)
    editor = pasos.esperar_que(_es_editor, "el editor del reel", app="instagram")
    pasos.tocar(_unico(editor, ID_SIGUIENTE, desc=_t("siguiente")), editor)
    pasos.esperar_que(_es_detalles, f"los detalles «{_t('nuevo_reel')}» con el campo del pie", app="instagram")
    estado.update(paso="abierto", publicaciones_antes=antes)
    narrado.guardar_estado_movil(pieza_id, estado, raiz)
    telefono.captura(ev / "abrir-1.png")
    return estado


def _publicaciones_del_perfil() -> tuple[str, int]:
    """(volcado, número de publicaciones) del perfil de la marca, igual en varios volcados frescos
    seguidos (los volcados pueden ir con retraso). Si no se lee, PantallaInesperada."""
    def lectura(xml: str) -> int | None:
        return ip.publicaciones_de_perfil(xml) if ip.perfil_activo(xml) == CUENTA else None
    return pasos.esperar_estable(lectura, descripcion=f"el número de publicaciones del perfil de {CUENTA}")


def _ir_a_la_portada(perfil: str) -> str:
    pasos.tocar(_unico(perfil, ID_INICIO, desc=_t("inicio")), perfil)
    return pasos.esperar_que(_es_portada, f"la portada con «{_t('crear')}»", app="instagram")


def _abrir_galeria(portada: str) -> str:
    """Toca «Créer» en la portada y espera la galería. Si abre en otro destino, se para: este paso no
    cambia de destino."""
    pasos.tocar(_unico(portada, ID_CREAR, desc=_t("crear")), portada)
    galeria = pasos.esperar_que(_es_galeria, "la galería", app="instagram")
    if not _es_galeria_reel(galeria):
        titulo = [n["texto"] for n in _por_id(galeria, ID_TITULO_GALERIA)]
        raise PantallaInesperada(f"la galería abrió en {titulo}, no en «{_t('nuevo_reel')}»: no se cambia de destino")
    return galeria


def _miniatura_estable(subido_en: str, duracion_ms: int) -> tuple[dict, str]:
    """(casilla, volcado) cuando varios volcados frescos seguidos muestran la misma casilla del vídeo en
    el mismo sitio: tocar con un volcado atrasado abriría otro vídeo. Dos que casan paran en el acto."""
    ultimo: list[str] = []

    def lectura(xml: str):
        if not _es_galeria_reel(xml):
            return None
        try:
            n = elegir_miniatura(xml, subido_en, duracion_ms)
        except MiniaturaAusente as e:
            ultimo[:] = [str(e)]
            return None
        return n["bounds"], n["desc"]

    try:
        xml, _ = pasos.esperar_estable(lectura, descripcion="la casilla del vídeo subido")
    except PantallaInesperada as e:
        if ultimo:
            raise MiniaturaAusente(f"{e}; {ultimo[0]}") from e
        raise
    return elegir_miniatura(xml, subido_en, duracion_ms), xml


# ---------------------------------------------------------------- pie: lectura pura de la pantalla de detalles

# La guardia de toques (`pasos.tocar` → `pantalla.es_envio`) rechaza CUALQUIER toque dentro de la lista de detalles
# cuando el volcado trae la cabecera «Partager aussi sur...»: `content_view` es pulsable, cubre toda la lista y la
# cabecera es descendiente suya, y su texto empieza por «partager» (`PREFIJOS_ENVIO`; en `NO_ENVIO` solo está
# «partager aussi sur instagram»). Comprobado en 06-detalles-abajo.xml: la mención IA, «Essai» y los dos `toggle` de
# los cruces salen rechazados. `permitir` es lo más estrecho que deja el marco: exime esa etiqueta exacta (o seguida de
# un separador) en cualquier nodo, sin ocultar ningún otro envío: «Partager» (`share_button`) y el contenedor de
# «Enregistrer le brouillon» siguen rechazados con la misma lista (prueba 10). Solo se pasa a los toques de los cuatro
# interruptores.
PERMITIR_INTERRUPTORES = (textos.texto("instagram", "partager_aussi"),)

# (clave, texto de `textos` que ancla la fila, cómo debe quedar, nombre en los mensajes)
FILAS = (("ia", "mencion_ia", True, "mención IA"),
         ("essai", "essai", False, "Essai"),
         ("threads", "cruce_threads", False, "cruce a Threads"),
         ("facebook", "cruce_facebook", False, "cruce a Facebook"))


def _normal(valor: str) -> str:
    """Espacios normalizados: el espacio duro de «Ajouter une mention IA» cuenta como uno normal."""
    return " ".join((valor or "").split())


def _anclas(xml: str, titulo: str) -> list[dict]:
    buscado = _normal(titulo)
    return [n for n in telefono.nodos(xml)
            if n["package"] == IG and buscado and buscado in (_normal(n["texto"]), _normal(n["desc"]))]


def interruptor_de_fila(xml: str, titulo: str) -> dict | None:
    """El interruptor de la fila cuyo único nodo con texto (o content-desc) `titulo` (espacios normalizados) la ancla.
    Si el ancla misma es `checkable` (el Switch «Essai» es la fila entera), es ella. Si no, el nodo `checkable` de
    Instagram, de cualquier clase, cuyo alto se solapa con el del ancla y que empieza a la derecha de donde acaba el
    ancla; si hay varios, el de centro vertical más cercano. None si no hay ancla, si hay más de una, si no hay
    interruptor o si dos empatan. No mira si está en pantalla: eso es `detalles_listos`."""
    anclas = _anclas(xml, titulo)
    if len(anclas) != 1:
        return None
    a = anclas[0]
    if a["checkable"]:
        return a
    ax1, ay1, ax2, ay2 = a["bounds"]
    centro = (ay1 + ay2) / 2
    candidatos = sorted(((abs((n["bounds"][1] + n["bounds"][3]) / 2 - centro), i, n)
                         for i, n in enumerate(telefono.nodos(xml))
                         if n["package"] == IG and n["checkable"] and n["bounds"][0] >= ax2
                         and n["bounds"][1] < ay2 and ay1 < n["bounds"][3]), key=lambda t: (t[0], t[1]))
    if not candidatos or (len(candidatos) > 1 and candidatos[0][0] == candidatos[1][0]):
        return None
    return candidatos[0][2]


def _franja(xml: str) -> tuple[int, int] | None:
    """(y donde acaba la barra de acción, y donde empieza la barra de abajo), o None si falta alguna."""
    arriba, abajo = _por_id(xml, ID_BARRA_ACCION), _por_id(xml, ID_BARRA_ABAJO)
    if len(arriba) != 1 or len(abajo) != 1:
        return None
    return arriba[0]["bounds"][3], abajo[0]["bounds"][1]


def _en_pantalla(n: dict, franja: tuple[int, int] | None) -> bool:
    """`n` está entero entre las dos barras. Estricto: uiautomator da las bounds de lo que se ve, así que un nodo
    cortado por una barra acaba justo en su borde (la fila de Facebook en 06: hasta y=1961, donde empieza la barra) y
    cuenta como fuera. Lo que queda detrás de la barra de abajo también sale en el volcado (la fila IA de 05, en
    y=2301–2316) y tampoco cuenta."""
    return franja is not None and franja[0] < n["bounds"][1] and n["bounds"][3] < franja[1]


def _es_detalles_reel(xml: str) -> bool:
    """La pantalla de detalles «Nouveau reel», en cualquier punto de la lista: título, las dos barras y los dos botones
    de abajo. Sin exigir el campo del pie, que al deslizar sale de la pantalla."""
    return (any(n["texto"] == _t("nuevo_reel") for n in _por_id(xml, ID_TITULO)) and _franja(xml) is not None
            and len(_por_id(xml, ID_COMPARTIR)) == 1 and len(_por_id(xml, ID_BORRADOR)) == 1)


def _interruptor_visible(xml: str, texto_clave: str) -> dict | None:
    """El interruptor de la fila anclada en `_t(texto_clave)` si la fila se ve entera: ancla e interruptor entre las
    barras y nada dibujado encima del interruptor (`telefono.tapado`). Si no, None."""
    if not _es_detalles_reel(xml):
        return None
    franja = _franja(xml)
    anclas = _anclas(xml, _t(texto_clave))
    n = interruptor_de_fila(xml, _t(texto_clave))
    if n is None or len(anclas) != 1 or not _en_pantalla(anclas[0], franja) or not _en_pantalla(n, franja):
        return None
    return None if telefono.tapado(xml, n) else n


def _campo_pie_visible(xml: str) -> dict | None:
    campos = _por_id(xml, ID_PIE)
    if not _es_detalles_reel(xml) or len(campos) != 1 or not _en_pantalla(campos[0], _franja(xml)):
        return None
    return None if telefono.tapado(xml, campos[0]) else campos[0]


def _audio_visible(xml: str) -> bool:
    return _es_detalles_reel(xml) and any(_en_pantalla(n, _franja(xml)) for n in _anclas(xml, _t("audio_original")))


def _primera_linea(pie: str) -> str:
    primera = pie.splitlines()[0] if pie.strip() else ""
    if not primera.strip():
        raise ValueError("el pie no tiene primera línea: no hay con qué comprobar el campo")
    return primera


def _faltas(xml: str, pie: str) -> dict[str, str]:
    """Lo que no está bien en este volcado, por condición: «ia», «essai», «threads», «facebook», «pie», «audio»."""
    faltas: dict[str, str] = {}
    for clave, texto_clave, quiero, nombre in FILAS:
        n = _interruptor_visible(xml, texto_clave)
        if n is None:
            faltas[clave] = f"{nombre}: la fila no está en pantalla (entera, entre las dos barras), no se confirma"
        elif n["checked"] != quiero:
            ahora, debe = ("encendido", "apagado") if n["checked"] else ("apagado", "encendido")
            faltas[clave] = f"{nombre}: {ahora}, tiene que estar {debe}"
    primera = _primera_linea(pie)
    campo = _campo_pie_visible(xml)
    if campo is None:
        faltas["pie"] = "pie: el campo no está en pantalla, no se confirma"
    elif not campo["texto"].startswith(primera):
        faltas["pie"] = f"pie: el campo no empieza por la primera línea del pie ({primera[:40]!r}…)"
    if not _audio_visible(xml):
        faltas["audio"] = f"audio original: «{_t('audio_original')}» no está en pantalla"
    return faltas


def detalles_listos(xml: str, pie: str) -> list[str]:
    """Lo que NO está todavía bien en la pantalla de detalles de este volcado, un mensaje por condición y cada uno con
    su nombre: mención IA apagada; cruce a Threads o a Facebook encendido; «Essai» encendido; el campo del pie no
    empieza por la primera línea de `pie`; «Audio d’origine» ausente. Una fila que no se ve entera entre las dos barras
    (o con algo encima de su interruptor) es «no está en pantalla»: nunca se da por buena. Vacía = todo bien. Pura."""
    return list(_faltas(xml, pie).values())


def detalles_listos_en_dos(xml_arriba: str, xml_abajo: str, pie: str) -> list[str]:
    """`detalles_listos` repartido en dos lecturas, porque el campo del pie y las filas de los interruptores no caben a
    la vez: el pie se confirma en `xml_arriba` y todo lo demás en `xml_abajo`. Vacía = todo bien. Pura."""
    arriba, abajo = _faltas(xml_arriba, pie), _faltas(xml_abajo, pie)
    return [f for clave, f in abajo.items() if clave != "pie"] + ([arriba["pie"]] if "pie" in arriba else [])


def gesto_de_lista(xml: str, sentido: str) -> tuple[int, int, int, int]:
    """(x1, y1, x2, y2) del deslizamiento que mueve la lista de detalles: «bajar» avanza hacia el final de la lista (el
    dedo sube), «subir» vuelve hacia el pie (el dedo baja). Vertical, en x = borde izquierdo de la lista + X_GESTO_PX, y
    con los dos extremos a MARGEN_GESTO_PX como poco de la barra de acción y de la barra de «Partager»: nunca empieza ni
    acaba en una barra. No usa `pantalla.punto_bloqueado`, que aquí bloquea cualquier punto de la lista por la misma
    cabecera «Partager aussi sur...» que obliga a `PERMITIR_INTERRUPTORES`. PantallaInesperada si no es la pantalla de
    detalles o si no hay sitio para RECORRIDO_MINIMO_PX."""
    if sentido not in ("bajar", "subir"):
        raise ValueError(f"sentido {sentido!r}: vale «bajar» o «subir»")
    listas = _por_id(xml, ID_LISTA)
    if not _es_detalles_reel(xml) or len(listas) != 1:
        raise PantallaInesperada("no es la pantalla de detalles «Nouveau reel» con su lista: no se desliza")
    arriba, abajo = _franja(xml)
    lo, hi = max(arriba, listas[0]["bounds"][1]) + MARGEN_GESTO_PX, min(abajo, listas[0]["bounds"][3]) - MARGEN_GESTO_PX
    recorrido = min(DESLIZAR_PX, hi - lo)
    x = listas[0]["bounds"][0] + X_GESTO_PX
    if recorrido < RECORRIDO_MINIMO_PX or x >= listas[0]["bounds"][2]:
        raise PantallaInesperada(f"la lista {listas[0]['bounds']} no deja sitio para deslizar entre las barras")
    return (x, hi, x, hi - recorrido) if sentido == "bajar" else (x, lo, x, lo + recorrido)


# ---------------------------------------------------------------- pie: con el teléfono

def _firma(xml: str) -> tuple:
    """Lo que tiene que repetirse para dar un volcado por quieto. Si el volcado no es la pantalla de detalles (una
    hoja, un diálogo, otra pantalla), PantallaInesperada en el acto: no se intenta cerrar nada."""
    if not _es_detalles_reel(xml):
        visibles = [n["texto"] or n["desc"] for n in telefono.nodos(xml) if n["texto"] or n["desc"]][:6]
        raise PantallaInesperada(f"en lugar de los detalles «{_t('nuevo_reel')}» hay otra pantalla {visibles}: "
                                 "no se toca nada")
    return tuple((n["bounds"], n["texto"], n["desc"], n["checked"]) for n in telefono.nodos(xml))


def _leer_detalles(descripcion: str) -> str:
    return pasos.esperar_estable(_firma, descripcion=descripcion)[0]


def _filas_fuera(xml: str) -> dict[str, str]:
    """Las filas que hacen falta abajo y no se ven enteras: nombre → «encima» (su ancla está por arriba de la barra de
    acción) o «debajo» (por abajo, tapada por la barra o todavía sin volcar)."""
    franja = _franja(xml)
    fuera = {}
    for _, texto_clave, _, nombre in FILAS:
        if _interruptor_visible(xml, texto_clave) is None:
            anclas = _anclas(xml, _t(texto_clave))
            encima = len(anclas) == 1 and franja is not None and anclas[0]["bounds"][1] <= franja[0]
            fuera[nombre] = "encima" if encima else "debajo"
    if not _audio_visible(xml):
        anclas = _anclas(xml, _t("audio_original"))
        fuera["audio original"] = "encima" if anclas and franja and anclas[0]["bounds"][1] <= franja[0] else "debajo"
    return fuera


def _filas_a_la_vista() -> str:
    """Volcado quieto de los detalles con la mención IA, «Essai», los dos cruces y «Audio d’origine» enteros en
    pantalla, deslizando la lista (solo deslizando) MAX_DESLIZAMIENTOS veces como mucho. Si no caben o no aparecen,
    PantallaInesperada."""
    fuera: dict[str, str] = {}
    for intento in range(MAX_DESLIZAMIENTOS + 1):
        xml = _leer_detalles("la pantalla de detalles quieta")
        fuera = _filas_fuera(xml)
        if not fuera:
            return xml
        if intento == MAX_DESLIZAMIENTOS:
            break
        sentidos = set(fuera.values())
        if len(sentidos) > 1:
            raise PantallaInesperada(f"las filas de abajo no caben a la vez en la pantalla: {fuera}")
        pasos.exigir_listo()
        telefono.deslizar(*gesto_de_lista(xml, "subir" if sentidos == {"encima"} else "bajar"), DESLIZAR_MS)
        reloj.dormir(1.5)
    raise PantallaInesperada(f"tras {MAX_DESLIZAMIENTOS} deslizamientos siguen sin verse enteras: {fuera}")


def _fijar(texto_clave: str, quiero: bool, nombre: str) -> str:
    """Deja el interruptor de la fila como `quiero`: lo toca solo si está al revés y espera un volcado fresco que lo
    muestre cambiado. Si no cambia, o sale otra pantalla, PantallaInesperada. «ya estaba» o «cambiado»."""
    xml = _filas_a_la_vista()
    n = _interruptor_visible(xml, texto_clave)
    if n is None:
        raise PantallaInesperada(f"{nombre}: la fila dejó de verse entera")
    if n["checked"] == quiero:
        return "ya estaba"
    barra = [b["bounds"] for rid in (ID_COMPARTIR, ID_BORRADOR) for b in _por_id(xml, rid)]
    cx, cy = n["centro"]
    if any(x1 <= cx < x2 and y1 <= cy < y2 for x1, y1, x2, y2 in barra):
        raise PantallaInesperada(f"{nombre}: el interruptor cae sobre la barra de compartir: no se toca")
    pasos.exigir_listo()
    pasos.tocar(n, xml, permitir=PERMITIR_INTERRUPTORES)

    def cambiado(x: str) -> bool:
        _firma(x)
        m = _interruptor_visible(x, texto_clave)
        return m is not None and m["checked"] == quiero
    pasos.esperar_que(cambiado, f"{nombre} {'encendido' if quiero else 'apagado'} tras el toque", app="instagram")
    return "cambiado"


def _pieza_publicada(pieza_id: str, raiz: Path | None) -> dict:
    narrado.ruta_build(pieza_id, raiz)  # valida el id
    ruta = (raiz or narrado.RAIZ) / "content" / "published" / f"{pieza_id}.json"
    if not ruta.is_file():
        raise ValueError(f"no existe la pieza publicada {ruta}: no hay pie")
    return json.loads(ruta.read_text(encoding="utf-8"))


def _exigir_detalles_con_pie(xml: str, pie: str) -> None:
    if not _es_detalles(xml):
        raise PantallaInesperada(f"tras pegar el pie no está la pantalla de detalles «{_t('nuevo_reel')}» con su campo")
    if not any(n["texto"].startswith(_primera_linea(pie)) for n in _por_id(xml, ID_PIE)):
        raise PantallaInesperada("tras pegar, el campo del pie no empieza por la primera línea del pie")


def _escribir_pie(pie: str) -> None:
    """Pega el pie en el campo con `pasos.escribir_texto` (portapapeles: las tildes llegan) y cierra el teclado y el
    desplegable de hashtags con «atrás» mientras la pantalla de detalles sigue delante. Cualquier ventana emergente de
    Instagram cuenta como desplegable abierto (no hay fila de música ni nada fijo con qué descartarla): si parece un
    desplegable se cierra con «atrás», si no, se para."""
    def campo(x: str) -> dict | None:
        campos = _por_id(x, ID_PIE)
        return campos[0] if _es_detalles(x) and len(campos) == 1 else None

    def escrito(x: str, texto: str) -> bool:
        campos = _por_id(x, ID_PIE)
        return len(campos) == 1 and campos[0]["texto"] == texto

    pasos.escribir_texto(pie, IG, campo=campo, exigir=lambda x: _exigir_detalles_con_pie(x, pie),
                         desplegable_nodos=lambda x: ip.hay_desplegable_hashtags(x, paquete=IG),
                         emergente=lambda x, emergentes: pantalla.emergente_solapada(emergentes, []),
                         verificar=escrito)


def poner_pie(pieza_id: str, ev: Path, raiz: Path | None = None) -> dict:
    """Del estado «abierto» (detalles del reel en pantalla) al estado «listo» con `pie_sha256`; no comparte.

    Teléfono listo → detalles con el campo del pie → pegar el pie → teclado y desplegable cerrados → primera lectura
    (quieta) con el pie en el campo → deslizar la lista → mención IA encendida → «Essai» apagado → cruce a Threads
    apagado → cruce a Facebook apagado (cada uno se toca solo si está al revés, con `pasos.tocar` y
    PERMITIR_INTERRUPTORES, y se espera a verlo cambiado) → segunda lectura (quieta, con todas las filas enteras) →
    `detalles_listos_en_dos` vacío → capturas de las dos vistas → estado. Cualquier otra pantalla en medio:
    PantallaInesperada sin cerrarla. Nunca toca «Partager» ni «Enregistrer le brouillon»."""
    estado = _estado_en(pieza_id, ("abierto",), raiz)
    pie = narrado_pie.pie(_pieza_publicada(pieza_id, raiz))
    pasos.exigir_listo()
    pasos.esperar_que(_es_detalles, f"los detalles «{_t('nuevo_reel')}» con el campo del pie", app="instagram")
    _escribir_pie(pie)
    xml_arriba = _leer_detalles("los detalles con el pie escrito")
    falta = _faltas(xml_arriba, pie).get("pie")
    if falta:
        raise PantallaInesperada(f"tras pegar: {falta}")
    telefono.captura(ev / "pie-1-arriba.png")
    for _, texto_clave, quiero, nombre in FILAS:
        _fijar(texto_clave, quiero, nombre)
    xml_abajo = _filas_a_la_vista()
    faltan = detalles_listos_en_dos(xml_arriba, xml_abajo, pie)
    if faltan:
        raise PantallaInesperada(f"los detalles no quedaron listos: {'; '.join(faltan)}")
    telefono.captura(ev / "pie-2-abajo.png")
    estado.update(paso="listo", pie_sha256=hashlib.sha256(pie.encode("utf-8")).hexdigest())
    narrado.guardar_estado_movil(pieza_id, estado, raiz)
    return estado


# ---------------------------------------------------------------- publicar: el único toque que comparte

ESTADOS_COMPARTIDOS = NO_SUBIR_OTRA_VEZ  # «compartido», «verificado», «incierto»: nunca otro «Partager»
FALTA_PARA_LISTO = {None: "falta `subir`", "subido": "falta `abrir`", "abierto": "falta `pie`",
                    "descartado": "se descartó: hay que volver a `subir`"}
VIGILANCIA_TRAS_COMPARTIR_S = 30  # como `sitio_instagram.publicar`: el aviso de audio puede salir con retraso
# La guardia (`pantalla.es_envio`) no rechaza «Désactiver et partager»: no está en `ENVIO` y no empieza por ningún
# prefijo de envío (empieza por «désactiver»), así que no hace falta eximir nada y la lista blanca más estrecha es la
# vacía. Con ella, «Partager», `share_button`, `save_draft_button` (dentro del contenedor de «Partager») y cualquier
# «Partager» del propio aviso siguen rechazados (prueba 14). SUPOSICIÓN: el aviso se vuelca solo, como la hoja 09; si
# saliera encima de la lista de detalles, la cabecera «Partager aussi sur...» bloquearía el toque, no se tocaría y
# quedaría en los avisos.
PERMITIR_AVISO_AUDIO: tuple[str, ...] = ()


class NoPublicar(Exception):
    """`publicar` se niega sin haber tocado nada. `motivos` dice por qué, uno por condición."""

    def __init__(self, motivos: list[str]):
        self.motivos = list(motivos)
        super().__init__("; ".join(self.motivos))


def _texto_registro(entrada: dict) -> str:
    fecha = entrada.get("compartido_en") or entrada.get("publicado_en") or entrada.get("construido_en") or "?"
    return f"ya hay un registro de esta cita: {entrada.get('estado', '?')} el {fecha}"


def _exigir_sin_registro(pieza_id: str, raiz: Path | None) -> str:
    """La clave de la cita, si `registro.jsonl` no tiene ninguna línea suya; si la tiene, o no se puede leer,
    NoPublicar."""
    try:
        registro = narrado.ya_compartida(pieza_id, raiz)
        clave = narrado.clave_de_pieza(pieza_id, raiz)
    except (OSError, ValueError) as e:
        raise NoPublicar([f"no se puede consultar el registro de la cita: {e}"]) from e
    if registro is not None:
        raise NoPublicar([_texto_registro(registro)])
    return clave


def _estado_para_publicar(pieza_id: str, raiz: Path | None) -> dict:
    try:
        estado = narrado.estado_movil(pieza_id, raiz)
    except (OSError, ValueError) as e:
        raise NoPublicar([f"no se puede leer el estado del móvil: {e}"]) from e
    paso = estado.get("paso") if isinstance(estado, dict) else None
    if paso in ESTADOS_COMPARTIDOS:
        raise NoPublicar(["ya se compartió"])
    if paso != "listo":
        raise NoPublicar([f"el móvil está en {paso!r}, no en «listo»: "
                          f"{FALTA_PARA_LISTO.get(paso, 'estado desconocido')}"])
    return estado


def _pie_comprobado(pieza_id: str, estado: dict, raiz: Path | None) -> str:
    """El pie recalculado de la pieza, si su sha256 es el `pie_sha256` que `poner_pie` dejó escrito."""
    try:
        pie = narrado_pie.pie(_pieza_publicada(pieza_id, raiz))
    except (OSError, ValueError) as e:
        raise NoPublicar([f"no se puede recalcular el pie: {e}"]) from e
    if hashlib.sha256(pie.encode("utf-8")).hexdigest() != estado.get("pie_sha256"):
        raise NoPublicar(["el pie de la pieza ya no es el que se pegó (pie_sha256 distinto): vuelve a `descartar`"])
    return pie


def _exigir_video_en_el_telefono(pieza_id: str, estado: dict, raiz: Path | None) -> str:
    """El vídeo del teléfono es el mp4 revisado: el nombre del estado es el de este build y su sha256, leído ahora,
    el `sha256_mp4` del informe, que devuelve. None (no está) o un error al leerlo: NoPublicar."""
    try:
        informe = narrado.informe_de(pieza_id, raiz)
        esperado = informe["sha256_mp4"]
        nombre = estado.get("nombre_remoto")
        if nombre != nombre_remoto(pieza_id, esperado):
            raise NoPublicar([f"el vídeo del teléfono ({nombre!r}) no es el de este build"])
        en_el_telefono = telefono.sha256_de_video(nombre)
    except NoPublicar:
        raise
    except Exception as e:  # noqa: BLE001 — cualquier duda sobre el vídeo es una negativa
        raise NoPublicar([f"no se pudo leer el vídeo del teléfono: {type(e).__name__}: {e}"]) from e
    if en_el_telefono is None:
        raise NoPublicar([f"{nombre} no está en el teléfono"])
    if en_el_telefono != esperado:
        raise NoPublicar([f"el vídeo del teléfono ({en_el_telefono[:8]}) no es el revisado ({esperado[:8]})"])
    return esperado


def _pie_a_la_vista() -> str:
    """Volcado quieto de los detalles con el campo del pie entero en pantalla, deslizando la lista hacia el pie (solo
    deslizando) MAX_DESLIZAMIENTOS veces como mucho. Si no aparece, PantallaInesperada."""
    for intento in range(MAX_DESLIZAMIENTOS + 1):
        xml = _leer_detalles("la pantalla de detalles quieta, con el pie")
        if _campo_pie_visible(xml) is not None:
            return xml
        if intento == MAX_DESLIZAMIENTOS:
            break
        pasos.exigir_listo()
        telefono.deslizar(*gesto_de_lista(xml, "subir"), DESLIZAR_MS)
        reloj.dormir(1.5)
    raise PantallaInesperada(f"tras {MAX_DESLIZAMIENTOS} deslizamientos el campo del pie sigue sin verse entero")


def _problemas_del_boton(xml: str) -> list[str]:
    """Lo que impide pulsar «Partager» en este volcado: no es la pantalla de detalles, no hay exactamente un
    `share_button`, está desactivado o hay algo dibujado encima de su centro."""
    if not any(n["texto"] == _t("nuevo_reel") for n in _por_id(xml, ID_TITULO)) or _franja(xml) is None:
        return [f"no es la pantalla de detalles «{_t('nuevo_reel')}»"]
    botones = _por_id(xml, ID_COMPARTIR)
    if len(botones) != 1:
        return [f"hay {len(botones)} share_button, no uno"]
    if not botones[0]["enabled"]:
        return ["el share_button está desactivado"]
    if telefono.tapado(xml, botones[0]):
        return ["algo tapa el share_button"]
    return []


def cuentas_en_detalles(xml: str) -> list[str]:
    """Los textos de los títulos de la fila del cruce a Threads (la que ancla el único nodo «Threads · Public»): los
    nodos de Instagram con texto que son hermanos suyos (mismo padre) y están por encima de él. En los volcados 06 y 07
    es uno, `sabiduriabolsillo` en [169,1697][889,1754]: la cuenta que publicará. [] si no hay ancla o título. Pura."""
    lista = telefono.nodos(xml)
    anclas = [i for i, n in enumerate(lista) if n["package"] == IG and _normal(n["texto"]) == _normal(_t("cruce_threads"))]
    if len(anclas) != 1:
        return []
    i = anclas[0]
    nivel = lista[i]["profundidad"]
    padre = next((j for j in range(i - 1, -1, -1) if lista[j]["profundidad"] < nivel), None)
    if padre is None:
        return []
    titulos = []
    for n in lista[padre + 1:]:
        if n["profundidad"] <= lista[padre]["profundidad"]:
            break
        if (n is not lista[i] and n["profundidad"] == nivel and n["package"] == IG and n["texto"].strip()
                and n["bounds"][3] <= lista[i]["bounds"][1]):
            titulos.append(n["texto"])
    return titulos


def _problemas_de_cuenta(xml: str) -> list[str]:
    """La cuenta que publicará, leída en la fila de Threads de los detalles: tiene que ser exactamente un título igual
    a la marca. Si no, el mensaje dice qué hay."""
    titulos = cuentas_en_detalles(xml)
    if titulos == [CUENTA]:
        return []
    return [f"cuenta: la fila de Threads de los detalles no dice solo «{CUENTA}» ({titulos or 'ningún título'}): "
            "no se sabe con qué cuenta se publicaría"]


def _listo_para_compartir(xml: str, emergentes: list[dict], pie: str) -> list[str]:
    """Para `pasos.enviar` (sus dos volcados antes del toque): las filas siguen bien y enteras, el botón es único,
    activo y destapado, y ninguna ventana emergente se le cruza."""
    problemas = ([f for clave, f in _faltas(xml, pie).items() if clave != "pie"] + _problemas_del_boton(xml)
                 + _problemas_de_cuenta(xml))
    culpable = pantalla.emergente_solapada(emergentes, [n["bounds"] for n in _por_id(xml, ID_COMPARTIR)])
    if culpable is not None:
        problemas.append(f"una {pantalla.describe_emergente(culpable)} se cruza con «Partager»")
    return problemas


def _comprobar_antes_de_compartir(pie: str) -> None:
    """e, f y g de `publicar`: teléfono listo; los detalles delante; dos lecturas frescas sin más que deslizar (arriba
    el pie, abajo los interruptores) con `detalles_listos_en_dos` vacío y el campo igual al pie entero; en la última,
    un solo `share_button`, activo y destapado, y el teclado cerrado. NoPublicar con los motivos si algo falla."""
    try:
        pasos.exigir_listo()
        delante = pasos.volcado_fresco()
        if not _es_detalles_reel(delante):
            raise NoPublicar([f"los detalles «{_t('nuevo_reel')}» no están delante"])
        xml_arriba = _pie_a_la_vista()
        xml_abajo = _filas_a_la_vista()
    except (PantallaInesperada, telefono.TelefonoError) as e:
        raise NoPublicar([f"{type(e).__name__}: {e}"]) from e
    motivos = detalles_listos_en_dos(xml_arriba, xml_abajo, pie)
    campos = _por_id(xml_arriba, ID_PIE)
    if len(campos) != 1 or campos[0]["texto"] != pie:
        motivos.append("pie: el campo no tiene el pie entero de la pieza")
    motivos += _problemas_del_boton(xml_abajo) + _problemas_de_cuenta(xml_abajo)
    if telefono.teclado_estado() is not False:
        motivos.append("el teclado está abierto (o no se sabe)")
    if motivos:
        raise NoPublicar(motivos)


def _boton_aviso_audio(xml: str) -> dict | None:
    lista = [n for n in telefono.nodos(xml) if n["package"] == IG
             and textos.normalizar(n["texto"]) == textos.normalizar(_t("desactivar_y_compartir"))]
    return lista[0] if len(lista) == 1 else None


def _es_dialogo(xml: str) -> bool:
    """Un diálogo u hoja: el volcado es una ventana emergente o lleva una hoja de acciones o un diálogo de Instagram."""
    return pantalla.volcado_de_emergente(xml) or any(
        n["resource_id"].rsplit("/", 1)[-1].startswith(("bottom_sheet", "action_sheet", "dialog"))
        for n in telefono.nodos(xml))


def _boton_plus_tard(xml: str) -> dict | None:
    """«Plus tard» de la hoja del estado de WhatsApp: solo si algún nodo contiene «statut WhatsApp» y hay exactamente
    un nodo de Instagram cuyo texto es «Plus tard». None si no."""
    marca = textos.normalizar(_t("statut_whatsapp"))
    if not any(marca in textos.normalizar(n["texto"]) or marca in textos.normalizar(n["desc"])
               for n in telefono.nodos(xml)):
        return None
    lista = [n for n in telefono.nodos(xml) if n["package"] == IG and n["texto"] == _t("plus_tard")]
    return lista[0] if len(lista) == 1 else None


# (clave en `avisos_respondidos`, cómo se encuentra el botón, su texto, `permitir`): lo único que se toca tras compartir
RESPUESTAS_TRAS_COMPARTIR = (
    ("audio_original", _boton_aviso_audio, "desactivar_y_compartir", PERMITIR_AVISO_AUDIO),  # decisión del 3 nov
    ("whatsapp", _boton_plus_tard, "plus_tard", ()),  # decisión del 7 nov: nunca a los contactos; la hoja retiene
)


def _vigilar_tras_compartir(avisos: list[str], respondidos: list[str], anotar) -> None:
    """Tras el toque, VIGILANCIA_TRAS_COMPARTIR_S. Para cada aviso de RESPUESTAS_TRAS_COMPARTIR (el del audio original:
    «Désactiver et partager»; la hoja del estado de WhatsApp: «Plus tard»), si sale en dos volcados seguidos con el
    botón en el mismo sitio, se toca ese botón con `pasos.tocar` y su `permitir`, una sola vez por aviso (aunque siga,
    aunque el toque falle o la guardia lo rechace: eso queda en `avisos` y no se amplía nada). Cualquier otro diálogo
    se anota en `avisos` y no se toca, y si al acabar los detalles siguen delante, también. Nunca se toca nada más."""
    inicio = reloj.monotonic()
    previos: dict[str, tuple] = {}
    intentados: set[str] = set()
    vistos: set = set()
    ultimo = None
    while reloj.monotonic() - inicio < VIGILANCIA_TRAS_COMPARTIR_S:
        reloj.dormir(1.5)
        try:
            xml = telefono.volcado(timeout=10)
        except telefono.TelefonoError:
            previos.clear()
            continue
        ultimo = xml
        encontrado = None
        for clave, buscar, texto_clave, permitir in RESPUESTAS_TRAS_COMPARTIR:
            boton = buscar(xml)
            if boton is not None:
                encontrado = (clave, boton, texto_clave, permitir)
                break
        if encontrado is not None:
            clave, boton, texto_clave, permitir = encontrado
            if clave not in intentados and previos.get(clave) == boton["bounds"]:
                intentados.add(clave)
                try:
                    pasos.exigir_listo()
                    pasos.tocar(boton, xml, permitir=permitir)
                except (PantallaInesperada, telefono.TelefonoError) as e:
                    avisos.append(f"{clave}: no se tocó «{_t(texto_clave)}»: {e}")
                else:
                    respondidos.append(clave)
                    avisos.append(f"{clave}: «{_t(texto_clave)}»")
                    anotar()
            previos = {clave: boton["bounds"]}
            continue
        previos.clear()
        if _es_dialogo(xml):
            firma = tuple(n["texto"] or n["desc"] for n in telefono.nodos(xml) if n["texto"] or n["desc"])[:6]
            if firma not in vistos:
                vistos.add(firma)
                avisos.append(f"otro diálogo tras compartir, no se toca: {list(firma)}")
    if ultimo is not None and _es_detalles_reel(ultimo):
        avisos.append("la pantalla de detalles sigue delante tras compartir")


def publicar(pieza_id: str, ev: Path, raiz: Path | None = None) -> dict:
    """El único toque que publica el reel: «Partager», una sola vez en la vida del build. Nunca se reintenta.

    En este orden, y a la primera que falle NoPublicar(motivos) sin haber tocado nada:
    a. el estado es «listo» («compartido», «verificado» o «incierto»: NoPublicar(["ya se compartió"])), y
       `narrado.ya_compartida` no tiene ninguna línea de esta cita en `registro.jsonl` (sobrevive a reconstruir
       `build/`): si la tiene, NoPublicar(["ya hay un registro de esta cita: <estado> el <fecha>"]);
    b. `narrado.apto_para_publicar` vacío;
    c. el pie recalculado de la pieza tiene el `pie_sha256` guardado;
    d. el sha256 del vídeo del teléfono (`telefono.sha256_de_video`) es el `sha256_mp4` del informe;
    e. teléfono listo y los detalles del reel delante;
    f. dos lecturas frescas, solo deslizando entre ellas (arriba el pie, abajo los interruptores), con
       `detalles_listos_en_dos` vacío y el campo igual al pie entero: se relee todo después de los toques de `pie`;
    g. en la última, un solo `share_button`, activo y destapado, y el teclado cerrado;
    h. ANTES del toque, en `observador_nuevo` (que `pasos.enviar` llama tras sus dos volcados, justo antes de pulsar)
       y con el cerrojo del registro (`narrado.cerrojo_registro`: si otro proceso lo tiene, no se espera y no se pulsa):
       otra vez ninguna línea de la cita o de la pieza y el estado «listo»; luego la línea {"pieza", "cita", "estado": "compartido", "compartido_en", "sha256_mp4", "nombre_remoto"} en
       `registro.jsonl`, luego el estado «compartido» con `compartido_en`, los dos con fsync del archivo y de la
       carpeta, y se releen los dos. Si cualquiera falla, no se pulsa. Si la línea queda escrita y el toque no llega
       a darse, la cita queda bloqueada para siempre: es a propósito, la dirección segura;
    i. una sola llamada a `pasos.enviar`, sin reintento de ningún tipo pase lo que pase;
    j. después, VIGILANCIA_TRAS_COMPARTIR_S vigilando (`_vigilar_tras_compartir`): solo «Désactiver et partager»
       en el aviso del audio original y «Plus tard» en la hoja del estado de WhatsApp, una vez cada uno; lo
       respondido queda en `avisos_respondidos` del estado.

    Desde el toque nada se propaga: devuelve {"compartido_en", "avisos", "captura_antes", "captura"} y el estado
    sigue «compartido»; lo que haya pasado lo resuelve `verificar`. Si el toque mismo lanza, o el proceso muere
    entre h e i, el estado queda «compartido» y también lo resuelve `verificar`, nunca otro `publicar`. Si
    `pasos.enviar` se niega después de h (solo puede ser su último `exigir_listo`, antes de pulsar), NoPublicar
    diciendo que no se tocó nada, y el registro y el estado siguen «compartido» por la misma regla."""
    estado = _estado_para_publicar(pieza_id, raiz)  # a
    clave = _exigir_sin_registro(pieza_id, raiz)  # a': ninguna línea del registro para esta cita
    problemas = narrado.apto_para_publicar(pieza_id, raiz)  # b
    if problemas:
        raise NoPublicar(problemas)
    pie = _pie_comprobado(pieza_id, estado, raiz)  # c
    sha256_mp4 = _exigir_video_en_el_telefono(pieza_id, estado, raiz)  # d
    _comprobar_antes_de_compartir(pie)  # e, f, g

    compartido = {**estado, "paso": "compartido",
                  "compartido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "avisos_respondidos": []}
    linea = {"pieza": pieza_id, "cita": clave, "estado": "compartido", "compartido_en": compartido["compartido_en"],
             "sha256_mp4": sha256_mp4, "nombre_remoto": estado.get("nombre_remoto")}
    escrito: list[str] = []
    respondidos: list[str] = compartido["avisos_respondidos"]

    def observador_nuevo(boton: dict):
        # h, todo antes del toque y con el cerrojo del registro (`fcntl.flock`, sin esperar): otra vez que no hay
        # línea de esta cita ni de esta pieza y que el estado sigue «listo» (otro `publicar` pudo pasar a–g a la vez);
        # la línea del registro (fuera de build/), luego el estado, los dos con fsync, y se releen del disco. Si algo
        # falla aquí `enviar` no pulsa. El cerrojo se suelta antes del toque: desde aquí bloquean la línea y el estado.
        with narrado.cerrojo_registro(raiz):
            previa = narrado.ya_compartida(pieza_id, raiz)
            if previa is not None:
                raise OSError(f"otro proceso registró esta cita mientras tanto ({_texto_registro(previa)})")
            ahora = narrado.estado_movil(pieza_id, raiz).get("paso")
            if ahora != "listo":
                raise OSError(f"el estado pasó a {ahora!r} mientras tanto: otro proceso")
            narrado.registrar(linea, raiz)
            escrito.append("registro")
            narrado.guardar_estado_movil(pieza_id, compartido, raiz)
            escrito.append("estado")
            leido = narrado.estado_movil(pieza_id, raiz)
            if leido.get("paso") != "compartido" or leido.get("compartido_en") != compartido["compartido_en"]:
                raise OSError("el estado leído tras escribirlo no dice «compartido» con este compartido_en")
            if narrado.ya_compartida(pieza_id, raiz) != linea:
                raise OSError("la última línea del registro para esta cita no es la que se acaba de escribir")
        return lambda xml: dict(pasos.VOLCADO_NO_VALIDO)  # la observación es la de `despues`

    def anotar() -> None:
        try:
            narrado.guardar_estado_movil(pieza_id, compartido, raiz)
        except Exception as e:  # noqa: BLE001 — tras el toque nada se propaga
            avisos_previos.append(f"no se pudo anotar el aviso respondido en el estado: {e}")

    avisos_previos: list[str] = []

    def despues(resultado: dict, _estado_envio: str) -> str:
        _vigilar_tras_compartir(resultado["avisos"], respondidos, anotar)
        return "compartido"

    try:
        resultado = pasos.enviar(  # i: la única llamada
            paquete=IG, nombre_app="Instagram", etiqueta=_t("compartir"), evidencia=ev,
            captura_antes="publicar-1-antes.png", captura_final="publicar-2-despues.png",
            captura_error="publicar-error.png",
            listo=lambda xml, emergentes: _listo_para_compartir(xml, emergentes, pie),
            botones=lambda xml: _por_id(xml, ID_COMPARTIR),
            observador_nuevo=observador_nuevo, despues=despues, plazo=0)
    except Exception as e:  # noqa: BLE001 — `enviar` solo propaga lo de antes del toque
        if escrito:
            raise NoPublicar([f"no se pulsó «Partager», no se tocó nada ({type(e).__name__}: {e}); pero ya se "
                              f"escribió {' y '.join(escrito)} como «compartido»: la cita queda bloqueada y lo "
                              "resuelve `verificar`, nunca otro `publicar`"]) from e
        raise NoPublicar([f"no se pulsó «Partager»: {type(e).__name__}: {e}"]) from e

    avisos = list(resultado.get("avisos") or []) + avisos_previos
    if resultado.get("estado") == "error_tras_pulsar":
        avisos.append(f"error tras pulsar «Partager»: {resultado.get('error')}")
    return {"compartido_en": compartido["compartido_en"], "avisos": avisos,
            "captura_antes": resultado.get("captura_antes"),
            "captura": resultado.get("captura") or resultado.get("captura_error")}


# ---------------------------------------------------------------- descartar: la salida antes de compartir

def _es_hoja_borrador(xml: str) -> bool:
    titulo = textos.normalizar_titulo(_t("hoja_borrador"))
    return any(n["package"] == IG and titulo in (textos.normalizar_titulo(n["texto"]), textos.normalizar_titulo(n["desc"]))
               for n in telefono.nodos(xml))


def _boton_recommencer(hoja: str) -> dict:
    """«Recommencer» de la hoja «Enregistrer le brouillon ?», por `pantalla.boton_descarte`, y solo si es esa fila y su
    centro no cae en «Enregistrer le brouillon» (fila o `save_draft_button`). Si no, PantallaInesperada."""
    if not _es_hoja_borrador(hoja):
        raise PantallaInesperada(f"no está la hoja «{_t('hoja_borrador')}»: no se toca nada")
    boton = pantalla.boton_descarte(hoja, "instagram")
    if textos.normalizar(boton["texto"]) != textos.normalizar(_t("recomenzar")):
        raise PantallaInesperada(f"el botón de descarte de la hoja es {boton['texto']!r}, no «{_t('recomenzar')}»: "
                                 "no se toca")
    cx, cy = boton["centro"]
    borrador = textos.normalizar(_t("guardar_borrador"))
    for n in telefono.nodos(hoja):
        if borrador in (textos.normalizar(n["texto"]), textos.normalizar(n["desc"])) \
                or n["resource_id"] == f"{IG}:id/{ID_BORRADOR}":
            x1, y1, x2, y2 = n["bounds"]
            if x1 <= cx < x2 and y1 <= cy < y2:
                raise PantallaInesperada(f"«{_t('recomenzar')}» cae sobre «{_t('guardar_borrador')}»: no se toca")
    return boton


def _salir_del_compositor(ev: Path) -> list[str]:
    """Desde los detalles o el editor del reel: «atrás» (al editor), «atrás» (a la hoja «Enregistrer le brouillon ?»),
    «Recommencer» con `pasos.tocar`, y «atrás» para salir de la galería. Si Instagram está en otra parte, no navega.
    Devuelve lo hecho; cualquier pantalla que no cuadre es PantallaInesperada."""
    pasos.exigir_listo()
    xml = pasos.volcado_fresco()
    hecho: list[str] = []
    if _es_detalles_reel(xml) or _es_detalles(xml):
        pasos.atras(IG, ev, "descartar-1-editor")
        pasos.esperar_que(_es_editor, "el editor del reel tras «atrás»", app="instagram")
        hecho.append("detalles → editor")
    elif not _es_editor(xml):
        return ["Instagram no está en los detalles ni en el editor del reel: no se navega"]
    pasos.atras(IG, ev, "descartar-2-hoja")
    hoja = pasos.esperar_que(_es_hoja_borrador, f"la hoja «{_t('hoja_borrador')}»", app="instagram")
    pasos.tocar(_boton_recommencer(hoja), hoja)
    hecho.append(f"editor → «{_t('recomenzar')}»")
    pasos.esperar_que(_es_galeria, f"la galería tras «{_t('recomenzar')}»", app="instagram")
    pasos.atras(IG, ev, "descartar-3-salida")
    hecho.append("galería → " + ("portada" if _es_portada(pasos.volcado_fresco()) else "fuera de la galería"))
    return hecho


def descartar(pieza_id: str, ev: Path, raiz: Path | None = None) -> dict:
    """La salida de cualquier paso antes de `publicar`: deja Instagram sin el borrador, borra el vídeo del teléfono y
    pone el estado en «descartado». Nunca toca «Enregistrer le brouillon» ni «Partager».

    En «compartido», «verificado» o «incierto» se niega (ValueError) sin tocar el teléfono: eso lo resuelve
    `verificar`. Sin vídeo subido no hay nada que descartar (ValueError). Si Instagram está en los detalles o en el
    editor del reel, sale por «Recommencer» (`_salir_del_compositor`); si está en otra parte, no navega. Siempre, aunque
    la salida falle: `telefono.borrar_video` (un False o un error van a `problemas`, no se lanzan) y estado
    «descartado», salvo que el estado releído justo antes de escribir diga ya «compartido», «verificado» o
    «incierto» (ValueError, el estado no se toca). Devuelve {"paso", "navegacion", "video_borrado", "problemas"}."""
    estado = narrado.estado_movil(pieza_id, raiz)
    paso = estado.get("paso")
    if paso in ESTADOS_COMPARTIDOS:
        raise ValueError(f"{pieza_id} está «{paso}»: ya se compartió, no se descarta (lo resuelve `verificar`)")
    nombre = estado.get("nombre_remoto")
    if not nombre:
        raise ValueError(f"{pieza_id}: no hay vídeo subido que descartar (estado {paso!r})")
    resultado = {"paso": "descartado", "navegacion": [], "video_borrado": False, "problemas": []}
    try:
        resultado["navegacion"] = _salir_del_compositor(ev)
    except (PantallaInesperada, telefono.TelefonoError) as e:
        resultado["problemas"].append(f"al salir de Instagram: {type(e).__name__}: {e}")
    try:
        resultado["video_borrado"] = telefono.borrar_video(nombre) is True
        if not resultado["video_borrado"]:
            resultado["problemas"].append(f"{nombre}: no se pudo confirmar que se borró del teléfono")
    except Exception as e:  # noqa: BLE001 — se informa, no se lanza
        resultado["problemas"].append(f"{nombre}: el borrado falló: {type(e).__name__}: {e}")
    ahora = narrado.estado_movil(pieza_id, raiz).get("paso")  # releído: un `publicar` pudo escribir entretanto
    if ahora in ESTADOS_COMPARTIDOS:
        raise ValueError(f"{pieza_id} pasó a «{ahora}» mientras se descartaba: no se escribe «descartado» "
                         f"(lo resuelve `verificar`); {resultado}")
    estado.update(paso="descartado", descartado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  video_borrado=resultado["video_borrado"])
    narrado.guardar_estado_movil(pieza_id, estado, raiz)
    return resultado


# ---------------------------------------------------------------- verificar: ¿llegó exactamente una publicación?

# Se leen al llamar (las pruebas los acortan): el plazo cuenta desde el principio de `verificar`, para todo el paso.
PLAZO_VERIFICAR_S = 180
LIMITE_DURO_VERIFICAR_S = 360  # tope absoluto, mirado dentro de las lecturas: la confirmación tampoco lo pasa
TIEMPO_AGOTADO = "tiempo máximo de verificación agotado"
ESPERA_LIMPIAR_MIN = 15  # `limpiar` no borra antes de esto desde `compartido_en`: la subida podría seguir
ESPERA_ENTRE_LECTURAS_S = 15
ESPERA_TRAS_REFRESCO_S = 3
DESLIZAR_REFRESCO_MS = 500  # como `sitio_instagram.verificar`
ID_PESTANA_PERFIL = "profile_tab_icon_view"
ID_BALDOSA = "image_button"  # baldosa de la cuadrícula del perfil («Reel par…», «Photo de…»), volcado 11 del 22 nov
PASOS_VERIFICADOS = ("verificado", "incierto")
ID_PESTANA_PROPIA = "profile_tab"  # la pestaña «Profil» de la barra de abajo (volcado 11 del 22 nov)
MAX_ATRAS_VERIFICAR = 3  # «atrás» seguidos, con Instagram delante, buscando la barra de abajo
MAX_APERTURAS = 3  # veces que se abre la misma baldosa (por su descripción) con el pie distinto o ilegible
_FIN_CORTADO = re.compile(r"\s*(?:…|\.\.\.)\s*(?:plus)?\s*$")
LARGO_LEYENDA = 30  # un texto así de largo (o con «#») en el Reel abierto se toma por su leyenda


def subiendo(xml: str) -> bool:
    """La barra de subida de Instagram («Partage sur…», «Publication sur…») está en pantalla."""
    prefijos = (_t("subiendo"), _t("subiendo_publicacion"))
    return any(n["package"] == IG and n["texto"].startswith(prefijos) for n in telefono.nodos(xml))


def cuenta_activa_en_perfil(xml: str) -> str | None:
    """La cuenta cuyo perfil PROPIO enseña el volcado: el texto del único `action_bar_title` de Instagram, si además
    está «Modifier le profil» (solo sale en el perfil de la cuenta activa). None si no es un perfil propio o si hay
    más de un título. Pura: los mismos nodos que `sitio_instagram.perfil_propio`, pero dice CUÁL es la cuenta."""
    titulos = {n["texto"] for n in _por_id(xml, "action_bar_title") if n["texto"]}
    propio = any(n["package"] == IG and _t("modificar_perfil") in (n["texto"], n["desc"]) for n in telefono.nodos(xml))
    return titulos.pop() if propio and len(titulos) == 1 else None


def _es_perfil_de_la_marca(xml: str) -> bool:
    """El perfil de la marca, con ella como cuenta activa («Modifier le profil» a la vista)."""
    return cuenta_activa_en_perfil(xml) == CUENTA


def _opcion_mas_recientes(xml: str) -> dict | None:
    """«Les plus récents» de la hoja del orden de la cuadrícula, si hay exactamente uno."""
    lista = [n for n in telefono.nodos(xml) if n["package"] == IG and n["texto"] == _t("mas_recientes")]
    return lista[0] if len(lista) == 1 else None


def baldosa_mas_reciente(xml: str) -> dict | None:
    """La primera baldosa de la cuadrícula del perfil (`image_button` de Instagram con descripción): la más alta y,
    en su fila, la de más a la izquierda. Con la cuadrícula ordenada por «Les plus récents» es la última
    publicación. None si no hay ninguna. Pura. SUPOSICIÓN sin comprobar: que no haya una publicación fijada arriba."""
    baldosas = [n for n in _por_id(xml, ID_BALDOSA) if n["desc"]]
    return min(baldosas, key=lambda n: (n["bounds"][1], n["bounds"][0])) if baldosas else None


def _es_reel(baldosa: dict) -> bool:
    return baldosa["desc"].startswith((_t("baldosa_reel_par"), _t("baldosa_reel_de")))


def pie_en_pantalla(xml: str, pie: str) -> bool:
    """Algún nodo de texto de Instagram (no un campo editable) empieza por la primera línea de `pie`, con los
    espacios normalizados. Es la comprobación del Reel abierto: no se sabe qué nodo lleva el pie en el visor
    (no se ha volcado nunca), así que no se mira el resource-id. Pura."""
    primera = _normal(_primera_linea(pie))
    return any(n["package"] == IG and n["clase"] not in pantalla.CLASES_CAMPO
               and _normal(n["texto"]).startswith(primera) for n in telefono.nodos(xml))


def _es_cuadricula(xml: str) -> bool:
    return any(n["desc"] == _t("vista_cuadricula") for n in _por_id(xml, ID_PESTANA_PERFIL))


def _motivo_para_no_refrescar(xml: str, gesto: tuple[int, int, int, int]) -> str | None:
    """Por qué no se hace el deslizamiento de refresco sobre `xml`: algo ajeno tapa el inicio
    (`pantalla.motivo_tapado` o una ventana emergente), un extremo cae sobre un control que no se toca
    (`pantalla.punto_bloqueado`) o hay una hoja o un modal de Instagram abierto (`ip.hoja_abierta`). None si nada."""
    x1, y1, x2, y2 = gesto
    ajeno = pantalla.motivo_tapado(xml, x1, y1, IG)
    if ajeno is not None:
        return ajeno
    emergente = pantalla.emergente_solapada(telefono.ventanas_emergentes(IG), [(x1, y1, x1 + 1, y1 + 1)])
    if emergente is not None:
        return f"{pantalla.describe_emergente(emergente)} se solapa con el inicio del gesto"
    for extremo, (x, y) in (("empieza", (x1, y1)), ("acaba", (x2, y2))):
        culpable = pantalla.punto_bloqueado(xml, x, y)
        if culpable is not None:
            etiqueta = culpable["texto"] or culpable["desc"] or culpable["resource_id"]
            return f"el gesto {extremo} en ({x}, {y}) sobre {etiqueta!r}"
    return ip.hoja_abierta(xml)




def leyenda_del_reel(xml: str, pie: str) -> str:
    """Qué dice del pie el Reel abierto en `xml`. Pura. En este orden:
    «coincide»: `pie_en_pantalla`;
    «cortada»: un texto de Instagram acaba en «…» / «...» (con o sin «plus») y lo de antes es el principio (10
    caracteres o más) de la primera línea del pie: no se puede leer entera;
    «distinta»: hay un texto que parece una leyenda (LARGO_LEYENDA caracteres o más, o con «#») y no es esta;
    «ausente»: ninguno de los anteriores (no hay leyenda en el volcado).
    SUPOSICIÓN: el visor nunca se ha volcado; «parece una leyenda» es una heurística."""
    if pie_en_pantalla(xml, pie):
        return "coincide"
    primera = _normal(_primera_linea(pie))
    textos_ig = [_normal(n["texto"]) for n in telefono.nodos(xml)
                 if n["package"] == IG and n["clase"] not in pantalla.CLASES_CAMPO and n["texto"].strip()]
    for t in textos_ig:
        recorte = _FIN_CORTADO.sub("", t)
        if recorte != t and len(recorte) >= 10 and primera.startswith(recorte):
            return "cortada"
    if any(len(t) >= LARGO_LEYENDA or "#" in t for t in textos_ig):
        return "distinta"
    return "ausente"


_CUENTA_DE_VISTAS = re.compile(r"[\s,.;:·…-]*\b\d+(?:[\u202f\u00a0 ]\d{3}|[.,]\d+)*\s*[kKmM]?\s*vues?\b.*$")


def clave_baldosa(desc: str) -> str:
    """La clave con la que se cuentan las aperturas de una baldosa: su descripción con los espacios normalizados y sin
    un recuento de vistas al final («…, 3 vues», «… 1,2 k vues»), que cambia de un volcado a otro. Pura."""
    return _CUENTA_DE_VISTAS.sub("", _normal(desc))


def _tocar_sin_emergente(n: dict, xml: str, que: str) -> None:
    """`pasos.tocar`, pero antes la misma comprobación que el gesto de refresco: si algo ajeno se dibuja sobre el
    centro de `n` (`pantalla.motivo_tapado`) o una ventana emergente de Instagram se le solapa
    (`telefono.ventanas_emergentes`, que la guardia de toques no ve), no se toca: PantallaInesperada."""
    cx, cy = n["centro"]
    motivo = pantalla.motivo_tapado(xml, cx, cy, IG)
    if motivo is None:
        emergente = pantalla.emergente_solapada(telefono.ventanas_emergentes(IG), [n["bounds"]])
        if emergente is not None:
            motivo = f"{pantalla.describe_emergente(emergente)} se le solapa"
    if motivo is not None:
        raise PantallaInesperada(f"no se toca {que}: {motivo}")
    pasos.tocar(n, xml)


def _atras_sin_emergente(ev: Path, nombre: str) -> None:
    """`pasos.atras`, pero no con una ventana emergente de Instagram abierta (PantallaInesperada). Si lo único que
    falla es la captura de después (ya se pulsó «atrás»), no cuenta: la captura es evidencia, no un paso."""
    emergentes = telefono.ventanas_emergentes(IG)
    if emergentes:
        raise PantallaInesperada(f"no se pulsa «atrás»: {pantalla.describe_emergente(emergentes[0])} abierta")
    try:
        pasos.atras(IG, ev, nombre)
    except (PantallaInesperada, telefono.TelefonoError):
        raise
    except Exception:  # noqa: BLE001 — solo puede ser la captura, tras pulsar
        pass


# ¿Se vio la barra de subida en algún volcado de la ronda en curso? `_sondear` lo pone a False al empezar cada ronda
# (la de confirmación sigue a la suya sin ponerlo a cero) y `_vistazo` lo enciende con cualquier volcado que la enseñe:
# el primero, los del refresco (también los de una lectura que no se estabiliza por la barra) y los de la cuadrícula y
# el Reel abierto.
_BANNER_EN_RONDA = [False]


# Instante (`reloj.monotonic`) en que `verificar` deja de leer pase lo que pase: lo pone `verificar` al empezar
# (LIMITE_DURO_VERIFICAR_S desde el principio) y lo quita al acabar. `_vistazo` lo mira en cada volcado, también dentro de
# las lecturas estables y las esperas, así que como mucho se pasa en lo que tarde un volcado.
_LIMITE_DURO: list[float | None] = [None]


class TiempoAgotado(PantallaInesperada):
    """Se pasó LIMITE_DURO_VERIFICAR_S: `verificar` acaba «incierto» sin otra ronda."""


def _vistazo(xml: str) -> str:
    """Cada volcado de `verificar` pasa por aquí: enciende la marca de la barra de subida de la ronda y, pasado el
    límite duro, TiempoAgotado."""
    if subiendo(xml):
        _BANNER_EN_RONDA[0] = True
    if _LIMITE_DURO[0] is not None and reloj.monotonic() >= _LIMITE_DURO[0]:
        raise TiempoAgotado(f"{TIEMPO_AGOTADO} ({LIMITE_DURO_VERIFICAR_S} s)")
    return xml


def _ir_al_perfil(ev: Path) -> str:
    """Volcado fresco del perfil de la marca, llegando SOLO con toques de navegación: nunca `exigir_cuenta` (su
    recuperación cierra Instagram, y la subida de lo que se verifica corre en segundo plano dentro de la app), nunca
    lanzar ni reiniciar la app, nunca cambiar de cuenta. Si la barra «Partage sur…» está delante, devuelve ese volcado
    (ahí no se lee nada). Si la hoja del orden está abierta, «Les plus récents». Si hay barra de abajo, la pestaña
    `profile_tab` (`pasos.tocar`); si no, `pasos.atras` (solo con Instagram delante) hasta MAX_ATRAS_VERIFICAR veces.
    El perfil propio de OTRA cuenta: `si.CuentaAjena`, sin tocar nada más."""
    pasos.exigir_listo()
    xml = _vistazo(pasos.volcado_fresco())
    atras_usados = 0
    for _ in range(2 * MAX_ATRAS_VERIFICAR + 4):
        if subiendo(xml):
            return xml
        cuenta = cuenta_activa_en_perfil(xml)
        if cuenta == CUENTA:
            return xml
        if cuenta is not None:
            raise si.CuentaAjena(f"Instagram enseña el perfil de otra cuenta ({cuenta!r}), no el de {CUENTA}: no se "
                                 "ha hecho nada (ni se cambia de cuenta ni se cierra la app); que lo mire una persona")
        opcion = _opcion_mas_recientes(xml)
        pestanas = _por_id(xml, ID_PESTANA_PROPIA)
        if opcion is not None:
            _tocar_sin_emergente(opcion, xml, f"«{_t('mas_recientes')}»")
            reloj.dormir(2)
        elif len(pestanas) == 1:
            _tocar_sin_emergente(pestanas[0], xml, "la pestaña del perfil")
            reloj.dormir(2)
        elif atras_usados < MAX_ATRAS_VERIFICAR:
            atras_usados += 1
            _atras_sin_emergente(ev, f"verificar-atras-{atras_usados}")
        else:
            raise PantallaInesperada(f"tras {MAX_ATRAS_VERIFICAR} «atrás» no aparece la barra con la pestaña del perfil")
        pasos.exigir_listo()
        xml = _vistazo(pasos.volcado_fresco())
    raise PantallaInesperada(f"no se llegó al perfil de {CUENTA} con la pestaña del perfil")


def _recuento_refrescado(xml: str) -> tuple[int, str]:
    """Tira del perfil hacia abajo (`ip.gesto_de_refresco` sobre `xml`, el gesto comprobado con
    `_motivo_para_no_refrescar`, con el teléfono listo) y lee el número de publicaciones, igual en varios volcados
    frescos seguidos. Devuelve (recuento, volcado). El perfil abierto sale en caché: sin refrescar no sube.
    PantallaInesperada si no."""
    gesto = ip.gesto_de_refresco(xml)
    motivo = _motivo_para_no_refrescar(xml, gesto)
    if motivo is not None:
        raise PantallaInesperada(f"no se refresca el perfil: {motivo}")
    pasos.exigir_listo()
    telefono.deslizar(*gesto, DESLIZAR_REFRESCO_MS)
    reloj.dormir(ESPERA_TRAS_REFRESCO_S)

    def lectura(x: str) -> int | None:
        return ip.publicaciones_de_perfil(x) if _es_perfil_de_la_marca(_vistazo(x)) and not subiendo(x) else None
    estable, recuento = pasos.esperar_estable(lectura, descripcion=f"el número de publicaciones de {CUENTA} tras refrescar")
    return recuento, estable


def _abrir_lo_mas_reciente(pie: str, ev: Path) -> tuple[str, str, str | None]:
    """(resultado, descripción de la baldosa, captura). La pestaña «Vue Grille» (y «Les plus récents» si sale la hoja
    del orden), la baldosa más reciente estable en varios volcados; una foto no se abre («no_reel»). Un Reel se abre
    con `pasos.tocar`; desde ahí nada se propaga: se lee la leyenda en un volcado estable (`leyenda_del_reel`:
    «coincide», «distinta», o «ilegible» si está cortada, no está o el visor no se deja volcar) y, si no coincide, se
    intenta volver con `pasos.atras` (si falla, la ronda siguiente vuelve al perfil). Lo de antes del toque se propaga."""
    pasos.exigir_listo()
    xml = _vistazo(pasos.volcado_fresco())
    if not _es_perfil_de_la_marca(xml):
        raise PantallaInesperada(f"el perfil de {CUENTA} ya no está delante: no se abre la cuadrícula")
    _tocar_sin_emergente(_unico(xml, ID_PESTANA_PERFIL, desc=_t("vista_cuadricula")), xml, f"«{_t('vista_cuadricula')}»")
    reloj.dormir(2)
    xml = _vistazo(pasos.volcado_fresco())
    opcion = _opcion_mas_recientes(xml)
    if opcion is not None:
        _tocar_sin_emergente(opcion, xml, f"«{_t('mas_recientes')}»")
        reloj.dormir(2)

    def baldosa(x: str):
        if not _es_cuadricula(_vistazo(x)) or _opcion_mas_recientes(x) is not None or ip.hoja_abierta(x):
            return None
        n = baldosa_mas_reciente(x)
        return (n["bounds"], n["desc"]) if n is not None else None
    xml, (_, desc) = pasos.esperar_estable(baldosa, descripcion="la baldosa más reciente de la cuadrícula")
    primera = baldosa_mas_reciente(xml)
    if not _es_reel(primera):
        return "no_reel", desc, None
    _tocar_sin_emergente(primera, xml, "la baldosa más reciente")
    reloj.dormir(3)

    def abierto(x: str):
        if _es_cuadricula(_vistazo(x)):
            return None
        return tuple((n["texto"], n["desc"]) for n in telefono.nodos(x))
    try:
        xml, _ = pasos.esperar_estable(abierto, descripcion="el Reel abierto quieto")
        leida = leyenda_del_reel(xml, pie)
    except TiempoAgotado:
        raise
    except (PantallaInesperada, telefono.TelefonoError):
        leida = "ausente"
    if leida == "coincide":
        try:
            captura = str(telefono.captura(ev / "verificar-1-reel.png"))
        except Exception:  # noqa: BLE001 — la captura es evidencia: no impide registrar el resultado
            captura = None
        return "coincide", desc, captura
    try:
        _atras_sin_emergente(ev, "verificar-2-otro-pie")
    except (PantallaInesperada, telefono.TelefonoError):
        pass  # la ronda siguiente vuelve al perfil con `_ir_al_perfil`
    return ("distinta" if leida == "distinta" else "ilegible"), desc, None


def _texto_aperturas(cuentas: dict[str, int]) -> str:
    def veces(n: int) -> str:
        return "1 vez" if n == 1 else f"{n} veces"
    partes = []
    if cuentas.get("distinta"):
        partes.append(f"la leyenda del último Reel no coincide ({veces(cuentas['distinta'])})")
    if cuentas.get("ilegible"):
        partes.append(f"no se pudo leer la leyenda del último Reel ({veces(cuentas['ilegible'])})")
    return "; ".join(partes)


def _mas_de_una(antes: int, despues: int) -> str:
    return (f"más de una publicación nueva: el perfil pasó de {antes} a {despues}; puede haberse publicado dos veces: "
            "que lo mire una persona")


def _confirmar(antes: int, ev: Path, lectura: dict) -> dict:
    """La ronda de confirmación tras un +1 con la leyenda que casa: «atrás» desde el Reel, ESPERA_ENTRE_LECTURAS_S, al
    perfil, sin la barra de subida, refresco y recuento. Sigue en `antes + 1`: «verificado». +2 o más: «incierto» con
    el texto de más de una publicación. Más bajo, ilegible o con la barra delante: «incierto» con el motivo. Una sola
    vez, aunque caiga después del plazo. `si.CuentaAjena` sale tal cual, como en cualquier ronda."""
    try:
        _atras_sin_emergente(ev, "verificar-2-perfil")
    except (PantallaInesperada, telefono.TelefonoError):
        pass  # `_ir_al_perfil` vuelve al perfil con la pestaña
    reloj.dormir(ESPERA_ENTRE_LECTURAS_S)
    base = {"encontrada": False, "captura": lectura["captura"], "despues": lectura["despues"]}
    try:
        xml = _ir_al_perfil(ev)
        if subiendo(xml):
            return {**base, "estado": "incierto", "banner": True,
                    "problemas": [f"confirmación: la barra de subida («{_t('subiendo')}…») volvió a salir tras ver el "
                                  "Reel: no se confirma que haya una sola publicación"]}
        despues, _ = _recuento_refrescado(xml)
    except si.CuentaAjena:
        raise
    except TiempoAgotado:
        return {**base, "estado": "incierto", "banner": _BANNER_EN_RONDA[0],
                "problemas": [f"confirmación: {TIEMPO_AGOTADO} ({LIMITE_DURO_VERIFICAR_S} s)"]}
    except (PantallaInesperada, telefono.TelefonoError) as e:
        return {**base, "estado": "incierto", "banner": _BANNER_EN_RONDA[0],
                "problemas": [f"confirmación: no se pudo releer el recuento tras ver el Reel: {type(e).__name__}: {e}"]}
    if despues >= antes + 2:
        return {**base, "estado": "incierto", "despues": despues, "banner": _BANNER_EN_RONDA[0],
                "problemas": [f"confirmación: {_mas_de_una(antes, despues)}"]}
    if despues != antes + 1:
        return {**base, "estado": "incierto", "despues": despues, "banner": _BANNER_EN_RONDA[0],
                "problemas": [f"confirmación: el recuento bajó a {despues} (se esperaba {antes + 1})"]}
    return {**lectura, "despues": despues, "banner": _BANNER_EN_RONDA[0]}


def _sondear(antes: int, pie: str, ev: Path, inicio: float) -> dict:
    """Las lecturas de `verificar` hasta el plazo (PLAZO_VERIFICAR_S desde `inicio`), cada ESPERA_ENTRE_LECTURAS_S.
    Devuelve {"estado", "despues", "encontrada", "problemas", "captura", "banner"} (`banner`: algún volcado de la última
    ronda, o de la ronda y su confirmación, enseñó la barra de subida; ver `_vistazo`). Un fallo de pantalla o de lectura no acaba antes: se reintenta y, si llega el
    plazo, va a los problemas como último error; solo `si.CuentaAjena` sale en el acto. Una misma baldosa
    (`clave_baldosa`) se abre como mucho MAX_APERTURAS veces con la leyenda distinta o ilegible; después solo se sigue
    leyendo el recuento. Un +1 con la leyenda que casa pasa por `_confirmar` antes de darse por «verificado»."""
    plazo, espera = PLAZO_VERIFICAR_S, ESPERA_ENTRE_LECTURAS_S
    despues: int | None = None
    motivo = None
    ultimo_error = None
    banner = False
    agotado = False
    aperturas: dict[str, dict[str, int]] = {}
    while True:
        _BANNER_EN_RONDA[0] = False
        try:
            xml = _ir_al_perfil(ev)
            if subiendo(xml):
                motivo = f"la barra de subida («{_t('subiendo')}…») seguía en pantalla"
            else:
                despues, perfil = _recuento_refrescado(xml)
                if despues >= antes + 2:
                    return {"estado": "incierto", "despues": despues, "encontrada": False, "captura": None,
                            "banner": _BANNER_EN_RONDA[0], "problemas": [_mas_de_una(antes, despues)]}
                if despues == antes + 1:
                    vista = baldosa_mas_reciente(perfil)
                    vistas = aperturas.get(clave_baldosa(vista["desc"]), {}) if vista is not None else {}
                    if sum(vistas.values()) >= MAX_APERTURAS:
                        motivo = _texto_aperturas(vistas)
                    else:
                        motivo = "el recuento subió en una pero no se llegó a leer la leyenda del Reel más reciente"
                        resultado, desc, captura = _abrir_lo_mas_reciente(pie, ev)
                        if resultado == "coincide":
                            return _confirmar(antes, ev, {"estado": "verificado", "despues": despues,
                                                          "encontrada": True, "captura": captura, "problemas": []})
                        if resultado == "no_reel":
                            motivo = f"la publicación más reciente de la cuadrícula no es un Reel ({desc[:60]!r})"
                        else:
                            cuenta = aperturas.setdefault(clave_baldosa(desc), {})
                            cuenta[resultado] = cuenta.get(resultado, 0) + 1
                            motivo = _texto_aperturas(cuenta)
                else:
                    motivo = (f"el recuento no cambió ({despues}): no consta la publicación; que lo mire una persona "
                              "antes de volver a publicar" if despues == antes
                              else f"el recuento es {despues}, no {antes + 1}")
        except si.CuentaAjena:
            raise
        except TiempoAgotado:
            agotado = True
            banner = _BANNER_EN_RONDA[0]
            break
        except (PantallaInesperada, telefono.TelefonoError) as e:
            ultimo_error = f"{type(e).__name__}: {e}"
        banner = _BANNER_EN_RONDA[0]
        if reloj.monotonic() - inicio >= plazo:
            break
        reloj.dormir(espera)
    problemas = [f"tras {plazo} s: {motivo or 'no se llegó a leer el recuento'}"]
    if agotado:
        problemas = [f"{TIEMPO_AGOTADO} ({LIMITE_DURO_VERIFICAR_S} s): {motivo or 'no se llegó a leer el recuento'}"]
    if ultimo_error:
        problemas.append(f"último error: {ultimo_error}")
    return {"estado": "incierto", "despues": despues, "encontrada": False, "captura": None, "banner": banner,
            "problemas": problemas}


VIDEO_CONSERVADO = "vídeo conservado en el móvil: la subida seguía en curso"
VIDEO_CONSERVADO_INCIERTO = "vídeo conservado en el móvil: el resultado es incierto y la subida podría seguir en curso"
RECUPERADO = "estado recuperado del registro"


def _recuperar_del_registro(pieza_id: str, estado: dict, raiz: Path | None) -> dict | None:
    """Si la línea más reciente del registro para esta cita ya es «verificado» o «incierto» con el mismo
    `nombre_remoto` (un `verificar` anterior escribió el registro y murió antes del estado), escribe el estado desde
    ella y devuelve el resultado registrado, sin tocar el teléfono ni añadir otra línea. None si no es el caso."""
    ultima = narrado.ya_compartida(pieza_id, raiz)
    if (ultima is None or ultima.get("estado") not in PASOS_VERIFICADOS
            or ultima.get("nombre_remoto") != estado.get("nombre_remoto")):
        return None
    conservado = ultima.get("video_conservado")
    conservado = True if conservado is None else bool(conservado)  # una línea sin la clave: lo prudente
    problemas = list(ultima.get("problemas") or []) + [
        RECUPERADO, f"{estado.get('nombre_remoto')}: el vídeo puede seguir en el móvil (no se borró): `limpiar`"]
    estado.update(paso=ultima["estado"], verificado_en=ultima.get("verificado_en"),
                  publicaciones_despues=ultima.get("publicaciones_despues"), problemas_verificar=problemas,
                  video_conservado=conservado)
    narrado.guardar_estado_movil(pieza_id, estado, raiz)
    return {"estado": ultima["estado"], "publicaciones_antes": ultima.get("publicaciones_antes"),
            "publicaciones_despues": ultima.get("publicaciones_despues"),
            "encontrada": ultima["estado"] == "verificado", "problemas": problemas, "captura": None,
            "video_conservado": conservado}


def verificar(pieza_id: str, ev: Path, raiz: Path | None = None) -> dict:
    """Tras `publicar`: ¿llegó exactamente una publicación? Nunca toca «Partager», un borrador, nada de
    `textos.NO_TOCAR` ni nada que la guardia dé por envío: todos los toques van por `pasos.tocar`.

    El estado tiene que ser «compartido» («verificado» o «incierto»: ValueError("ya verificada"); otro: ValueError),
    con `publicaciones_antes` y `nombre_remoto`, y el pie se recalcula, todo antes de tocar el teléfono. Luego:
    a. `pasos.exigir_listo()` (no listo: la excepción sale tal cual, sin registro y con el estado «compartido»). Al
       perfil de la marca se llega en cada ronda con `_ir_al_perfil`: solo toques de navegación (pestaña del perfil,
       «atrás»), NUNCA `exigir_cuenta`, que puede cerrar Instagram y cortar la subida en segundo plano. Otra cuenta
       en el perfil propio, en cualquier ronda: `si.CuentaAjena` tal cual, sin registro, estado «compartido»;
    b. hasta PLAZO_VERIFICAR_S desde el principio, cada ESPERA_ENTRE_LECTURAS_S: con la barra «Partage sur…» se espera;
       si no, se refresca el perfil y se lee el recuento;
    c. con `publicaciones_antes + 1`, la baldosa más reciente de «Vue Grille» («Les plus récents»), si es un Reel, se
       abre y su pie tiene que empezar por la primera línea del pie; luego «atrás». La misma baldosa se abre como
       mucho MAX_APERTURAS veces con la leyenda distinta o ilegible;
    d. «verificado» con las dos cosas Y una ronda de confirmación (`_confirmar`: otra espera, refresco sin la barra de
       subida y el recuento sigue en +1; aunque caiga tras el plazo, una vez); «incierto» con +2 o más (en el acto o en
       la confirmación), o si llega el plazo sin las dos (el recuento no cambió, la baldosa no es un Reel, otro pie, o
       fallos de lectura: el último va a los problemas).
    Todos los toques pasan además por `_tocar_sin_emergente` (nada ajeno encima ni una ventana emergente solapada) y
    «atrás» por `_atras_sin_emergente`: si no, la ronda falla y se reintenta.
    Siempre que se llega a d: la línea {"pieza", "cita", "estado", "verificado_en", "publicaciones_antes",
    "publicaciones_despues", "problemas", "sha256_mp4", "nombre_remoto", "video_conservado"} en el registro
    (`narrado.registrar`), DESPUÉS el estado (los dos duraderos; si el estado falla, el error dice que el resultado ya
    está en el registro) y por último `telefono.borrar_video` (un False o un error van a `problemas`), SOLO con
    «verificado» y sin la barra de subida en ningún volcado de la última ronda ni de la de confirmación. Cualquier
    «incierto», o la barra vista, conserva el vídeo (`video_conservado`; se borra luego con `limpiar`). Si al empezar la última línea del registro de la cita ya es «verificado» o «incierto» con este
    `nombre_remoto`, se recupera el estado de ella sin tocar el teléfono ni escribir otra línea.
    Devuelve {"estado", "publicaciones_antes", "publicaciones_despues", "encontrada", "problemas", "captura",
    "video_conservado"}."""
    estado = narrado.estado_movil(pieza_id, raiz)
    paso = estado.get("paso")
    if paso in PASOS_VERIFICADOS:
        raise ValueError(f"{pieza_id}: ya verificada («{paso}»)")
    if paso != "compartido":
        raise ValueError(f"{pieza_id}: el móvil está en {paso!r}, no en «compartido»: no hay nada que verificar")
    antes, nombre = estado.get("publicaciones_antes"), estado.get("nombre_remoto")
    if not isinstance(antes, int) or isinstance(antes, bool) or not nombre:
        raise ValueError(f"{pieza_id}: el estado no trae publicaciones_antes y nombre_remoto: no se puede verificar")
    recuperado = _recuperar_del_registro(pieza_id, estado, raiz)
    if recuperado is not None:
        return recuperado
    pie = narrado_pie.pie(_pieza_publicada(pieza_id, raiz))
    _primera_linea(pie)
    clave = narrado.clave_de_pieza(pieza_id, raiz)

    inicio = reloj.monotonic()
    pasos.exigir_listo()
    _LIMITE_DURO[0] = inicio + LIMITE_DURO_VERIFICAR_S
    try:
        lectura = _sondear(antes, pie, ev, inicio)
    finally:
        _LIMITE_DURO[0] = None

    problemas = list(lectura["problemas"])
    # El vídeo solo se borra con «verificado» y sin la barra de subida en ningún volcado de la última ronda ni de la de
    # confirmación. Cualquier «incierto» lo conserva: la subida podría seguir leyéndolo. Se borra luego con `limpiar`.
    if lectura["estado"] != "verificado":
        conservar = True
        problemas.append(VIDEO_CONSERVADO_INCIERTO)
    else:
        conservar = bool(lectura.get("banner"))
        if conservar:
            problemas.append(VIDEO_CONSERVADO)
    verificado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    narrado.registrar({"pieza": pieza_id, "cita": clave, "estado": lectura["estado"], "verificado_en": verificado_en,
                       "publicaciones_antes": antes, "publicaciones_despues": lectura["despues"],
                       "problemas": problemas, "sha256_mp4": estado.get("sha256"), "nombre_remoto": nombre,
                       "video_conservado": conservar}, raiz)
    estado.update(paso=lectura["estado"], verificado_en=verificado_en, publicaciones_despues=lectura["despues"],
                  problemas_verificar=problemas, video_conservado=conservar)
    try:
        narrado.guardar_estado_movil(pieza_id, estado, raiz)
    except Exception as e:
        raise RuntimeError(f"{pieza_id}: no se pudo escribir el estado ({type(e).__name__}: {e}); el resultado ya está "
                           f"en el registro: {lectura['estado']}. Vuelve a correr `verificar`: lo recupera del registro "
                           "sin tocar el teléfono") from e

    resultado = {"estado": lectura["estado"], "publicaciones_antes": antes, "publicaciones_despues": lectura["despues"],
                 "encontrada": lectura["encontrada"], "problemas": list(problemas), "captura": lectura["captura"],
                 "video_conservado": conservar}
    if not conservar:
        try:
            if telefono.borrar_video(nombre) is not True:
                resultado["problemas"].append(f"{nombre}: no se pudo confirmar que se borró del teléfono")
        except Exception as e:  # noqa: BLE001 — se informa, no se lanza
            resultado["problemas"].append(f"{nombre}: el borrado falló: {type(e).__name__}: {e}")
    if resultado["captura"] is None:
        try:
            resultado["captura"] = str(telefono.captura(ev / "verificar-final.png"))
        except Exception as e:  # noqa: BLE001 — la captura final es de mejor esfuerzo
            resultado["problemas"].append(f"no se pudo capturar al final: {type(e).__name__}: {e}")
    return resultado


def _ahora() -> datetime:
    """La hora UTC de ahora; las pruebas la sustituyen."""
    return datetime.now(timezone.utc)


def limpiar(pieza_id: str, ev: Path | None = None, raiz: Path | None = None) -> dict:
    """Borra del teléfono el vídeo de una pieza ya verificada («verificado» o «incierto»; si no, ValueError): para el
    vídeo que `verificar` conservó (resultado incierto, o la subida seguía en curso). Córrelo SOLO cuando la subida
    haya terminado seguro: varios minutos después de compartir y sin la barra «Partage sur…» en el perfil; borrar un
    vídeo que Instagram todavía lee cortaría la subida. Por eso se niega (ValueError, con los minutos que faltan) hasta
    ESPERA_LIMPIAR_MIN minutos (leído al llamar) después de `compartido_en` (del estado o, si no, del registro), y si no
    se sabe ese instante. Solo `telefono.borrar_video(nombre_remoto)`: no
    toca nada más del teléfono ni escribe en el registro ni en el estado. `ev` no se usa (la firma es la de los demás
    pasos). Devuelve {"borrado", "problemas"}; un False o un error van a `problemas`, no se lanzan."""
    estado = narrado.estado_movil(pieza_id, raiz)
    if estado.get("paso") not in PASOS_VERIFICADOS:
        raise ValueError(f"{pieza_id}: el móvil está en {estado.get('paso')!r}: `limpiar` solo va tras `verificar`")
    nombre = estado.get("nombre_remoto")
    if not nombre:
        raise ValueError(f"{pieza_id}: el estado no trae nombre_remoto: no se sabe qué vídeo borrar")
    referencia = estado.get("compartido_en") or next(
        (e.get("compartido_en") for e in reversed(narrado.registro_de(pieza_id, raiz)) if e.get("compartido_en")), None)
    if not referencia:
        raise ValueError(f"{pieza_id}: no se sabe cuándo se compartió (ni en el estado ni en el registro): no se borra")
    momento = datetime.fromisoformat(referencia)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    pasado_min = (_ahora() - momento).total_seconds() / 60
    if pasado_min < ESPERA_LIMPIAR_MIN:
        faltan = max(1, math.ceil(ESPERA_LIMPIAR_MIN - pasado_min))
        raise ValueError(f"{pieza_id}: se compartió hace {pasado_min:.0f} min; `limpiar` espera {ESPERA_LIMPIAR_MIN} min "
                         f"desde {referencia} por si la subida sigue: faltan {faltan} min")
    try:
        borrado = telefono.borrar_video(nombre) is True
    except Exception as e:  # noqa: BLE001 — se informa, no se lanza
        return {"borrado": False, "problemas": [f"{nombre}: el borrado falló: {type(e).__name__}: {e}"]}
    return {"borrado": borrado, "problemas": [] if borrado else [f"{nombre}: no se pudo confirmar que se borró"]}
