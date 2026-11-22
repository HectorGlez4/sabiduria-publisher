"""
Publicar un reel narrado desde el móvil del laboratorio, paso a paso (fase 2).

La ruta es la de la sonda del 22 nov (`narrados/sonda-movil-2026-11-22.md`): subir el mp4 a
MediaStore → perfil de la marca → portada → «Créer» → galería «Nouveau reel» → la casilla del vídeo
subido → editor → «Suivant» → detalles → pie, mención IA y cruces apagados. Cada paso lee `build/movil.json`,
hace su parte y lo deja en el paso siguiente. Nada se adivina: si una pantalla no es la esperada,
PantallaInesperada y no se toca más.

Todo el teléfono pasa por `pasos.*` (los toques, por `pasos.tocar`, que no pulsa nada que publique) y
por funciones con nombre de `telefono`. Del bucle del sitio solo se usa `exigir_cuenta`, a través de la
referencia de este módulo, que las pruebas sustituyen porque llama a `telefono.shell`.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
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

    Antes de nada: `apto_para_publicar` vacío (si no, ValueError con los problemas) y ninguna publicación
    ya compartida de este build. Luego teléfono listo → `telefono.subir_video` con el nombre
    `<pieza>-<8 hex>.mp4` → el sha256 subido es el del informe → estado → captura."""
    problemas = narrado.apto_para_publicar(pieza_id, raiz)
    if problemas:
        raise ValueError(f"{pieza_id} no se puede publicar: {'; '.join(problemas)}")
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
