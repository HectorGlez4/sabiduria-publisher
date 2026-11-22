"""
Publicar un reel narrado desde el móvil del laboratorio, paso a paso (fase 2).

La ruta es la de la sonda del 22 nov (`narrados/sonda-movil-2026-11-22.md`): subir el mp4 a
MediaStore → perfil de la marca → portada → «Créer» → galería «Nouveau reel» → la casilla del vídeo
subido → editor → «Suivant» → detalles. Cada paso lee `build/movil.json`, hace su parte y lo deja en el
paso siguiente. Nada se adivina: si una pantalla no es la esperada, PantallaInesperada y no se toca más.

Todo el teléfono pasa por `pasos.*` (los toques, por `pasos.tocar`, que no pulsa nada que publique) y
por funciones con nombre de `telefono`. Del bucle del sitio solo se usa `exigir_cuenta`, a través de la
referencia de este módulo, que las pruebas sustituyen porque llama a `telefono.shell`.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from labkit import instagram_pantallas as ip
from labkit import narrado, pasos, telefono, textos
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
