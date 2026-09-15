"""
Lectura pura y genérica de pantallas (Instagram, Threads, Facebook).

Nada de aquí toca el teléfono ni el reloj: recibe volcados de uiautomator y devuelve lo que
dicen, o lanza PantallaInesperada si un control falta o es ambiguo. Lo propio de cada app
vive en `<app>_pantallas.py`.

Las zonas «arriba» y «abajo» son relativas al alto del volcado: 300 y 1900 px sobre los 2340
del teléfono actual (≈12,8 % y 81,2 %), para que un volcado de otro alto no las desplace.
"""
from __future__ import annotations

from labkit import telefono, textos

CLASES_CAMPO = ("android.widget.AutoCompleteTextView", "android.widget.EditText")
_SUFIJOS_CAMPO = tuple(clase.rsplit(".", 1)[-1] for clase in CLASES_CAMPO)
# El teléfono actual (Samsung SM-S721B, serie R5CXB1AWYNF) mide 1080×2340 (`adb shell wm size`:
# «Physical size: 1080x2340») y la raíz de sus volcados reales del 2026-09-14 es
# «[0,0][1080,2340]» (medido 2026-09-15); los volcados de alto 2316 en evidence/ son del
# teléfono anterior.
ALTO_REFERENCIA = 2340
LIMITE_ARRIBA_PX = 300
LIMITE_ABAJO_PX = 1900


class PantallaInesperada(RuntimeError):
    pass


def dice(n: dict, valor: str) -> bool:
    return valor in (n["texto"], n["desc"])


def area(n: dict) -> int:
    x1, y1, x2, y2 = n["bounds"]
    return (x2 - x1) * (y2 - y1)


def alto_volcado(xml: str) -> int:
    """Alto de la pantalla según el volcado: el borde inferior del nodo raíz (profundidad 0)
    que cuenta como la pantalla completa, o el alto de referencia si ninguno cuenta.

    Cuenta un nodo raíz cuya esquina superior izquierda está en el origen (0, 0), que ocupa
    todo el ancho de la pantalla (`x2 >= ANCHO_PANTALLA_PX`) y cuyo borde inferior pasa de
    `LIMITE_ABAJO_PX`. Un volcado de una ventana emergente enfocable tiene la emergente como
    raíz, con un origen que no es (0, 0); un contenedor en el origen pero más estrecho o más
    bajo que la pantalla tampoco es la pantalla completa. Ninguno de los dos debe usarse para
    escalar las zonas «arriba»/«abajo» (fallaría abierto: un nodo intermedio contaría como
    «abajo»)."""
    return _alto_de_nodos(telefono.nodos(xml))


def _alto_de_nodos(lista: list[dict]) -> int:
    """`alto_volcado` sobre los nodos ya leídos de un volcado."""
    completas = [n["bounds"][3] for n in lista
                 if n["profundidad"] == 0 and n["bounds"][:2] == (0, 0)
                 and n["bounds"][2] >= ANCHO_PANTALLA_PX and n["bounds"][3] > LIMITE_ABAJO_PX]
    return max(completas, default=ALTO_REFERENCIA)


def volcado_de_emergente(xml: str) -> bool:
    """El volcado tiene como raíz una ventana emergente enfocable, no el árbol completo de la
    pantalla: hay algún nodo raíz (profundidad 0) y ninguno empieza en el origen (0, 0)."""
    raices = [n["bounds"][:2] for n in telefono.nodos(xml) if n["profundidad"] == 0]
    return bool(raices) and (0, 0) not in raices


def elegir(coincidencias: list[dict], que: object) -> dict:
    """Una sola coincidencia útil.

    Varias valen si comparten centro o si todas caben en la primera (un contenedor y su
    botón, un botón y su etiqueta); si no, es ambiguo. Entre las válidas se devuelve la
    única clickable si hay exactamente una y, si no, la de menor área."""
    if not coincidencias:
        raise PantallaInesperada(f"no aparece {que}")
    if len(coincidencias) == 1:
        return coincidencias[0]
    primera = coincidencias[0]
    x1, y1, x2, y2 = primera["bounds"]
    for n in coincidencias[1:]:
        ox1, oy1, ox2, oy2 = n["bounds"]
        dentro = ox1 >= x1 and oy1 >= y1 and ox2 <= x2 and oy2 <= y2
        if n["centro"] != primera["centro"] and not dentro:
            raise PantallaInesperada(f"ambiguo: {que} en {[c['bounds'] for c in coincidencias]}")
    pulsables = [n for n in coincidencias if n["clickable"]]
    if len(pulsables) == 1:
        return pulsables[0]
    return min(coincidencias, key=area)


def coincidencias(xml: str, paquete: str | None, zona: str | None = None, **kw) -> list[dict]:
    """Nodos de `paquete` que cumplen los criterios de `telefono.buscar_todos`, en la zona dada."""
    if zona not in (None, "arriba", "abajo"):
        raise ValueError(f"zona desconocida: {zona}")
    todos = telefono.buscar_todos(xml, paquete=paquete, **kw)
    if zona is None:
        return todos
    alto = alto_volcado(xml)
    if zona == "arriba":
        return [n for n in todos if n["bounds"][3] * ALTO_REFERENCIA <= LIMITE_ARRIBA_PX * alto]
    return [n for n in todos if n["bounds"][1] * ALTO_REFERENCIA >= LIMITE_ABAJO_PX * alto]


def nodo(xml: str, paquete: str | None, zona: str | None = None, **kw) -> dict:
    """El control de `paquete` que coincide (en la zona, si se da)."""
    encontrados = coincidencias(xml, paquete, zona, **kw)
    if not encontrados:
        raise PantallaInesperada(f"no aparece {kw}" + (f" en zona {zona}" if zona else ""))
    return elegir(encontrados, kw)


def pulsable(xml: str, *, etiqueta: str, paquete: str) -> bool:
    """Algún control con `etiqueta` (texto o content-desc) de `paquete` se puede pulsar: el propio
    nodo es clickable y enabled o, si es una etiqueta, su antecesor clickable más cercano está
    enabled y es del mismo paquete. `etiqueta` y `paquete` son solo por nombre: los dos son
    `str` y un intercambio no debe fallar en silencio."""
    lista = telefono.nodos(xml)
    for i, n in enumerate(lista):
        if n["package"] != paquete or not dice(n, etiqueta):
            continue
        if n["clickable"]:
            if n["enabled"]:
                return True
            continue
        nivel = n["profundidad"]
        for anterior in reversed(lista[:i]):
            if anterior["profundidad"] >= nivel:
                continue
            nivel = anterior["profundidad"]
            if anterior["clickable"]:
                if anterior["enabled"] and anterior["package"] == paquete:
                    return True
                break
    return False


def tiene_texto(xml: str, *, texto: str, paquete: str) -> bool:
    """Algún nodo de `paquete` cuyo `text` (nunca `content-desc`) es exactamente `texto`.
    `texto` y `paquete` son solo por nombre: los dos son `str` y un intercambio no debe fallar
    en silencio."""
    return any(n["texto"] == texto for n in telefono.buscar_todos(xml, paquete=paquete))


def hay_desplegable(xml: str, paquete: str | None = None, *, prefijo: str = "#") -> bool:
    """Sugerencias abiertas: un texto que empieza por `prefijo` fuera de un campo de texto. Sin
    `paquete` se miran todos los nodos (ante la duda, se da por abierto). `prefijo` es solo por
    nombre: es un `str` como `paquete` y un intercambio no debe fallar en silencio."""
    return any(n["texto"].startswith(prefijo) and not n["clase"].endswith(_SUFIJOS_CAMPO)
               for n in telefono.buscar_todos(xml, paquete=paquete))


def evaluar_envio(observaciones: list[dict]) -> str:
    """Resultado de las observaciones tomadas tras pulsar, en orden. Los volcados no
    válidos no cuentan.

    - «fallido»: algún volcado válido muestra un aviso de error (manda sobre lo demás).
    - «confirmado»: se vio el aviso de envío («banner») y los dos últimos válidos no tienen ni
      aviso ni compositor.
    - «sin_banner»: los dos últimos válidos no tienen compositor pero el aviso no se vio.
    - «timeout» en otro caso."""
    validas = [o for o in observaciones if o["valido"]]
    if any(o.get("fallo") for o in validas):
        return "fallido"
    ultimas = validas[-2:]
    limpias = len(ultimas) == 2 and not any(o["compositor"] or o["banner"] for o in ultimas)
    if limpias and any(o["banner"] for o in validas):
        return "confirmado"
    if limpias:
        return "sin_banner"
    return "timeout"


# --- Ventanas emergentes (tarea 10f de la fase 1) -----------------------------------
# Un desplegable de sugerencias puede ser una PopupWindow que `uiautomator dump` no incluye:
# se lee de `telefono.ventanas_emergentes` y se reconoce por su solape con controles que sí
# están en el volcado (las referencias las da cada app).

UMBRAL_ANCHO_DESPLEGABLE = 0.9  # fracción del ancho del padre que ocupa un desplegable real
ANCHO_PANTALLA_PX = 1080  # medida del Samsung del laboratorio, si la emergente no trae ancho_padre


def se_solapan_verticalmente(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[1] < b[3] and b[1] < a[3]


def emergente_solapada(emergentes: list[dict], referencias: list[tuple[int, int, int, int]]) -> dict | None:
    """La primera de `emergentes` que cuenta como abierta sobre los controles de `referencias`: sin frame
    legible cuenta siempre; con frame, si se solapa verticalmente con alguna referencia; sin referencias en
    el volcado, cuenta cualquiera (falla cerrado). None si ninguna cuenta."""
    for e in emergentes:
        frame = e.get("frame")
        if frame is None or not referencias or any(se_solapan_verticalmente(frame, r) for r in referencias):
            return e
    return None


def parece_desplegable(e: dict) -> bool:
    """El frame de `e` ocupa al menos UMBRAL_ANCHO_DESPLEGABLE del ancho de su padre (o de ANCHO_PANTALLA_PX):
    un desplegable ocupa casi todo el ancho, un tooltip no. Sin frame cuenta como desplegable (falla cerrado)."""
    frame = e.get("frame")
    if frame is None:
        return True
    return (frame[2] - frame[0]) >= UMBRAL_ANCHO_DESPLEGABLE * (e.get("ancho_padre") or ANCHO_PANTALLA_PX)


def describe_emergente(e: dict) -> str:
    """«ventana emergente <nombre> en <frame>», para mensajes de diagnóstico."""
    frame = e.get("frame")
    return f"ventana emergente {e['nombre']} en {frame if frame is not None else 'sin frame legible'}"


def pista_idioma(xml: str, app: str) -> str:
    """« (ningún texto conocido…)» si el volcado tiene nodos de `app` pero ninguno de su tabla de
    textos: la app ha podido cambiar de idioma. Cadena vacía en otro caso, y también si `app` no
    tiene tabla en `textos.TEXTOS` (p. ej. Edits): sin tabla no hay pista fiable que dar."""
    if app not in textos.TEXTOS:
        return ""
    propios = telefono.buscar_todos(xml, paquete=textos.PAQUETES[app])
    if not propios:
        return ""
    conocidos = set(textos.TEXTOS[app].values())
    if any(n["texto"] in conocidos or n["desc"] in conocidos for n in propios):
        return ""
    return f" (ningún texto conocido de {app} en {textos.IDIOMAS.get(app, '?')}: ¿cambió el idioma de la app?)"


def _bloquea_toque(n: dict, ignorar: tuple[str, ...] = ()) -> bool:
    """El propio nodo (sin mirar descendientes) es de envío o está prohibido: su texto, descripción o
    id son de envío, o coincide con `NO_TOCAR`. `ignorar` exime, CAMPO a campo (texto, desc,
    resource-id), el valor que coincida con una etiqueta de la lista vía `textos.coincide_o_prefijo`
    (exacto o por prefijo seguido de separador); los demás campos del mismo nodo se siguen mirando."""
    texto, desc, rid = n["texto"], n["desc"], n["resource_id"]
    permitido_texto = textos.coincide_o_prefijo(texto, ignorar)
    permitido_desc = textos.coincide_o_prefijo(desc, ignorar)
    permitido_rid = textos.coincide_o_prefijo(rid, ignorar)
    envio_texto = not permitido_texto and textos.es_texto_envio(texto)
    envio_desc = not permitido_desc and textos.es_texto_envio(desc)
    envio_rid = not permitido_rid and textos.es_texto_envio(rid)
    prohibido = (not permitido_texto and textos.es_no_tocar(texto)) or (not permitido_desc and textos.es_no_tocar(desc))
    return envio_texto or envio_desc or envio_rid or prohibido


# Contenedores raíz PULSABLES de pantalla completa cuyos descendientes NO se miran en la regla del centro
# (`_bajo_el_toque`): envuelven la pantalla entera, así que con ellos cualquier envío de la pantalla bloquearía
# cualquier toque. Resource-id COMPLETO, comparado exacto (nunca por sufijo ni prefijo), y solo si el nodo es del
# paquete de ese id y cubre la pantalla (`contenedor_raiz_ignorado`).
# - `quick_capture_root_container`: editor de Story de Instagram 446.0.0.49.77, medido en la sonda S1 de la fase 2
#   (2026-09-15, volcados ig-05b-sin-aviso-camara e ig-06-historia-editor-audio de SONDA-F2-S1-IG): FrameLayout
#   pulsable sin etiqueta en [0,0][1080,2340] (la raíz del volcado) que contiene las herramientas («Stickers», dentro
#   del pulsable `asset_button`) y la barra de compartir («Vos stories», «Partager sur»).
CONTENEDORES_RAIZ_IGNORADOS = frozenset({"com.instagram.android:id/quick_capture_root_container"})
FRACCION_PANTALLA_COMPLETA = 0.95  # del ancho (ANCHO_PANTALLA_PX) y del alto (`alto_volcado`) que debe cubrir


def contenedor_raiz_ignorado(n: dict, alto: int) -> bool:
    """`n` es un contenedor raíz de `CONTENEDORES_RAIZ_IGNORADOS`: pulsable, con resource-id COMPLETO en la lista
    (igualdad exacta), del paquete que nombra ese id y de al menos FRACCION_PANTALLA_COMPLETA del ancho de la pantalla
    y de `alto` (el alto del volcado). Un nodo con ese id pero más pequeño no cuenta."""
    rid = n["resource_id"]
    if not n["clickable"] or rid not in CONTENEDORES_RAIZ_IGNORADOS or n["package"] != rid.split(":", 1)[0]:
        return False
    x1, y1, x2, y2 = n["bounds"]
    return (x2 - x1 >= FRACCION_PANTALLA_COMPLETA * ANCHO_PANTALLA_PX
            and y2 - y1 >= FRACCION_PANTALLA_COMPLETA * alto)


def _bajo_el_toque(lista: list[dict], n: dict, bloquea, *, descendientes: bool = True,
                   solo_pulsables: bool = False) -> dict | None:
    """La regla del centro, común a `es_envio` y a las guardias de `nodo_sonda`: el primer nodo que cumple
    `bloquea(nodo)` y recibiría el toque en el centro de `n`, o None. Mira, en este orden, `n` mismo y, para cada nodo
    de `lista` (de cualquier paquete, en orden de documento) cuyas bounds contienen el centro: el propio nodo (con
    `solo_pulsables`, solo si es pulsable) y, con `descendientes`, los descendientes de ese nodo si es PULSABLE (los
    siguientes en orden de documento con profundidad mayor, hasta el primero que no lo sea).

    Excepción: los descendientes de un contenedor raíz de `CONTENEDORES_RAIZ_IGNORADOS` que cubre la pantalla
    (`contenedor_raiz_ignorado`) no se miran por ser descendientes suyos. Solo se salta ESE recorrido: `n`, el propio
    contenedor, cualquier nodo cuyas bounds contienen el centro (pulsable o no) y los descendientes de cualquier otro
    pulsable bajo el centro se siguen mirando. Vale igual para las tres guardias que pasan por aquí (envío o
    prohibido, id de envío sin etiqueta y borrado), y también para `punto_bloqueado`, porque el motivo es el mismo en
    todas: ese contenedor envuelve la pantalla entera, así que su recorrido de descendientes mira TODOS los controles
    de la pantalla y bloquearía cualquier toque del editor en cuanto haya uno de envío o de borrado en otra parte. La
    de id de envío no recorre descendientes (`descendientes=False`), así que ahí la excepción no cambia nada. La lista
    es solo para ese contenedor raíz medido: cualquier otro pulsable sigue bloqueando por sus descendientes."""
    if bloquea(n):
        return n
    cx, cy = n["centro"]
    alto = _alto_de_nodos(lista)
    for k, m in enumerate(lista):
        x1, y1, x2, y2 = m["bounds"]
        if not (x1 <= cx < x2 and y1 <= cy < y2):
            continue
        if (m["clickable"] or not solo_pulsables) and bloquea(m):
            return m
        if descendientes and m["clickable"] and not contenedor_raiz_ignorado(m, alto):
            for hijo in lista[k + 1:]:
                if hijo["profundidad"] <= m["profundidad"]:
                    break
                if bloquea(hijo):
                    return hijo
    return None


def es_envio(xml: str, n: dict, ignorar: tuple[str, ...] = ()) -> bool:
    """Pulsar `n` podría enviar (o tocar un control prohibido) si: `n` mismo bloquea; algún nodo del
    volcado (de cualquier paquete) cuyas bounds contienen el centro del toque bloquea; o algún nodo
    PULSABLE cuyas bounds contienen el centro tiene un descendiente que bloquea (cubre tanto el
    antecesor clickable que recibe el toque como cualquier otro contenedor pulsable de otra rama del
    árbol que solape ese punto: un botón de pantalla completa sin etiqueta propia que envuelve un
    «Partager» bloquea cualquier toque dentro, a propósito, salvo el contenedor raíz medido de
    `CONTENEDORES_RAIZ_IGNORADOS`, ver `_bajo_el_toque`). `ignorar` exime esa etiqueta, campo a
    campo, en cualquier nodo del volcado que la tenga (no solo en `n`), sin ocultar ningún otro
    control de envío. `_bajo_el_toque` ya mira `n` antes que nada."""
    return _bajo_el_toque(telefono.nodos(xml), n, lambda m: _bloquea_toque(m, ignorar)) is not None


def punto_bloqueado(xml: str, x: int, y: int) -> dict | None:
    """El nodo que impide empezar o acabar un gesto (un deslizamiento) en (x, y), o None si el punto es seguro. Mismas
    reglas que un toque de `nodo_sonda` en ese punto: un título de borrado en cualquier parte del volcado; un nodo bajo
    el punto, o un descendiente de un pulsable bajo el punto, que es de envío o prohibido (`es_envio`) o de borrado; o
    un pulsable bajo el punto sin texto ni desc con id de envío."""
    todos = telefono.nodos(xml)
    titulo = next((m for m in todos if any(v and textos.es_titulo_borrado(v) for v in (m["texto"], m["desc"]))), None)
    if titulo is not None:
        return titulo
    punto = {"texto": "", "desc": "", "resource_id": "", "clase": "", "package": "", "clickable": False,
             "enabled": True, "profundidad": -1, "bounds": (x, y, x + 1, y + 1), "centro": (x, y)}
    return (_bajo_el_toque(todos, punto, _bloquea_toque)
            or _bajo_el_toque(todos, punto, _envio_sin_etiqueta, descendientes=False, solo_pulsables=True)
            or _bajo_el_toque(todos, punto, _es_borrado))


def motivo_tapado(xml: str, x: int, y: int, paquete: str) -> str | None:
    """Por qué el punto (x, y) no está a la vista de `paquete`, o None si lo que se dibuja encima en ese punto es de
    `paquete`. Cuenta como tapado si ningún nodo de `paquete` contiene el punto o si, detrás del último que lo contiene
    en orden de documento, otro nodo lo contiene (siempre de otro paquete: una notificación de systemui, un diálogo).

    Para un PUNTO que no es un nodo (el inicio de un gesto): solo cuenta lo de otro paquete dibujado después del último
    nodo propio. Para un NODO del volcado que se va a tocar está `telefono.tapado`, que cuenta cualquier nodo posterior
    que contenga su centro, también de la propia app.

    Es la regla de `telefono.tapado` (lo dibujado después tapa) llevada a un punto. `telefono.tapado` no sirve tal
    cual: un nodo sintético de 1×1 no está en el volcado y da siempre tapado, y con el nodo más profundo bajo el punto
    también, porque en los perfiles reales `modal_container` y `overlay_layout_container` (pantalla completa, vacíos)
    van después en el documento."""
    lista = telefono.nodos(xml)
    bajo = [(i, n) for i, n in enumerate(lista)
            if n["bounds"][0] <= x < n["bounds"][2] and n["bounds"][1] <= y < n["bounds"][3]]
    propios = [i for i, n in bajo if n["package"] == paquete]
    if not propios:
        return f"ningún nodo de {paquete} en ({x}, {y})"
    encima = next((n for i, n in bajo if i > propios[-1]), None)
    if encima is not None:
        etiqueta = encima["texto"] or encima["desc"] or encima["resource_id"] or encima["clase"]
        return f"un nodo de {encima['package']} ({etiqueta!r} en {encima['bounds']}) tapa ({x}, {y})"
    return None


def nodo_sonda(xml: str, paquete: str, *, texto: str | None = None, desc: str | None = None,
               resource_id: str | None = None) -> dict:
    """El único nodo de `paquete` con ese texto, content-desc o resource-id (basta el final tras «/»), si pulsarlo
    no puede enviar, borrar ni tocar un control prohibido. Solo para sondas supervisadas. Lanza PantallaInesperada,
    en este orden:
    1. si cualquier nodo del volcado, de cualquier paquete, es un título de borrado (`textos.es_titulo_borrado`);
    2. si no hay exactamente un nodo de `paquete` que case con el criterio;
    3. si pulsarlo podría enviar o tocar un control prohibido (`es_envio`);
    4. si el propio nodo, o un nodo PULSABLE bajo su centro, es un botón sin texto ni desc con id de envío
       (`textos.es_id_envio`);
    5. si el propio nodo, un nodo bajo su centro o un descendiente de un pulsable bajo su centro es un control de
       borrado (`textos.es_texto_borrado`)."""
    def rid(valor: str) -> str:
        return valor.rsplit("/", 1)[-1]

    todos = telefono.nodos(xml)
    titulo = next((m for m in todos if any(v and textos.es_titulo_borrado(v) for v in (m["texto"], m["desc"]))), None)
    if titulo is not None:
        raise PantallaInesperada(f"hay un diálogo de borrado en pantalla ({titulo['texto'] or titulo['desc']!r}): "
                                 "la sonda no toca nada")
    lista = [n for n in todos if n["package"] == paquete and (
        (texto is not None and n["texto"] == texto) or (desc is not None and n["desc"] == desc)
        or (resource_id is not None and n["resource_id"] and rid(n["resource_id"]) == rid(resource_id)))]
    if len(lista) != 1:
        raise PantallaInesperada(f"la sonda solo toca un nodo único: {len(lista)} coincidencias")
    if es_envio(xml, lista[0]):
        raise PantallaInesperada("la sonda no pulsa controles de envío ni prohibidos")
    # Solo el nodo y los PULSABLES bajo el centro, sin descendientes: `followers_share_content` y `post_capture_*` son
    # contenedores no pulsables que cubren el compositor y el editor enteros.
    por_id = _bajo_el_toque(todos, lista[0], _envio_sin_etiqueta, descendientes=False, solo_pulsables=True)
    if por_id is not None:
        raise PantallaInesperada(f"la sonda no pulsa un botón sin etiqueta con id de envío ({por_id['resource_id']!r})")
    borrado = _bajo_el_toque(todos, lista[0], _es_borrado)
    if borrado is not None:
        raise PantallaInesperada(f"la sonda no pulsa controles de borrado ({borrado['texto'] or borrado['desc']!r})")
    return lista[0]


def _envio_sin_etiqueta(n: dict) -> bool:
    """Botón sin texto ni desc cuyo id tiene una palabra de envío (`textos.es_id_envio`)."""
    return not n["texto"] and not n["desc"] and textos.es_id_envio(n["resource_id"])


def _es_borrado(n: dict) -> bool:
    """Control de borrado por su texto o su desc (`textos.es_texto_borrado`)."""
    return any(v and textos.es_texto_borrado(v) for v in (n["texto"], n["desc"]))


def boton_descarte(xml: str, app: str) -> dict:
    """El botón de descartar de `app`, solo si el volcado muestra su diálogo de descarte exacto
    (comparado con `textos.normalizar_titulo`, así que las comillas y el espacio antes de «?» no
    importan) y ningún título de `textos.TITULOS_BORRADO` en CUALQUIER paquete del volcado, no solo
    el de `app`. Nunca un control de envío. Los botones del diálogo se comparan solo por `texto`
    (nunca `desc`) a propósito: los textos de `DESCARTE` son literales de botón, no descripciones."""
    paquete = textos.PAQUETES[app]
    tabla = textos.DESCARTE[app]
    nodos_paquete = telefono.buscar_todos(xml, paquete=paquete)
    borrado = next((n for n in telefono.nodos(xml)
                    if any(v and textos.es_titulo_borrado(v) for v in (n["texto"], n["desc"]))), None)
    if borrado is not None:
        raise PantallaInesperada(f"el diálogo parece de borrado ({borrado['texto'] or borrado['desc']!r}), no de descarte: no se pulsa nada")
    if not any(textos.es_titulo_descarte(n["texto"], app) or textos.es_titulo_descarte(n["desc"], app)
               for n in nodos_paquete):
        raise PantallaInesperada(f"no se ve el diálogo de descarte de {app} {tabla['titulos']}: no se pulsa nada")
    for etiqueta in tabla["botones"]:
        etiqueta_norm = textos.normalizar(etiqueta)
        candidatos = [n for n in nodos_paquete if textos.normalizar(n["texto"]) == etiqueta_norm]
        if candidatos:
            boton = elegir(candidatos, etiqueta)
            if es_envio(xml, boton):
                raise PantallaInesperada(f"el botón {etiqueta!r} del diálogo parece de envío: no se pulsa")
            return boton
    raise PantallaInesperada(f"el diálogo de descarte de {app} no tiene {tabla['botones']}")
