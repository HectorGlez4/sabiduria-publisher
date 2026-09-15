"""
Lectura pura y genérica de pantallas (Instagram, Threads, Facebook).

Nada de aquí toca el teléfono ni el reloj: recibe volcados de uiautomator y devuelve lo que
dicen, o lanza PantallaInesperada si un control falta o es ambiguo. Lo propio de cada app
vive en `<app>_pantallas.py`.

Las zonas «arriba» y «abajo» son relativas al alto del volcado: 300 y 1900 px sobre los 2340
del teléfono actual (≈12,8 % y 81,2 %), para que un volcado de otro alto no las desplace.
"""
from __future__ import annotations

from labkit import telefono

CLASES_CAMPO = ("android.widget.AutoCompleteTextView", "android.widget.EditText")
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
    """Alto de la pantalla según el volcado: el borde inferior más bajo de los nodos raíz
    (profundidad 0). Sin nodos, el alto de referencia."""
    return max((n["bounds"][3] for n in telefono.nodos(xml) if n["profundidad"] == 0), default=ALTO_REFERENCIA)


def elegir(coincidencias: list[dict], que: object) -> dict:
    """Una sola coincidencia útil.

    Varias valen si comparten centro o si todas caben en la primera (un contenedor y su
    botón, un botón y su etiqueta); si no, es ambiguo. Entre las válidas se devuelve la
    única clickable si hay exactamente una y, si no, la de menor área."""
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


def pulsable(xml: str, etiqueta: str, paquete: str) -> bool:
    """Algún control con `etiqueta` (texto o content-desc) de `paquete` se puede pulsar: el propio
    nodo es clickable y enabled o, si es una etiqueta, su antecesor clickable más cercano está
    enabled y es del mismo paquete."""
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


def tiene_texto(xml: str, texto: str, paquete: str) -> bool:
    return any(n["texto"] == texto for n in telefono.buscar_todos(xml, paquete=paquete))


def hay_desplegable(xml: str, paquete: str | None = None, prefijo: str = "#") -> bool:
    """Sugerencias abiertas: un texto que empieza por `prefijo` fuera de un campo de texto. Sin
    `paquete` se miran todos los nodos (ante la duda, se da por abierto)."""
    return any(n["texto"].startswith(prefijo) and not n["clase"].endswith(("AutoCompleteTextView", "EditText"))
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
