"""
Primitivas adb para el Samsung del laboratorio (serie R5CXB1AWYNF).

El volcado de uiautomator sirve para ENCONTRAR controles, pero puede ir con
retraso respecto a la pantalla: la evidencia de un estado final es siempre una
captura (screencap), nunca un volcado.

Este módulo nunca despierta ni desbloquea el teléfono (lo gestiona MaaS360): si no
está listo, lo dice `estado()` y quien llama se detiene. Las funciones puras
(`nodos`, `buscar_todos`, `volcado_valido`, `estado_desde_dumpsys`, `tapado`…) no
tocan el teléfono y son las que cubren las pruebas.
"""
from __future__ import annotations

import hashlib
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SERIAL = "R5CXB1AWYNF"
REMOTO_UI = "/sdcard/lab-ui.xml"
URI_IMAGENES = "content://media/external/images/media"
ESPERA_MEDIASTORE_S = 20
_BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
_NOMBRE_SEGURO = re.compile(r"[A-Za-z0-9._-]+")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_VERSION = re.compile(r"versionName=(\S+)")
# `dumpsys package` responde en 1-2 s; 15 s por app acota el peor caso de `versiones` a 60 s con
# las cuatro apps de textos.PAQUETES (con 30 s eran 120 s en cada `lab.py preflight` de la ventana).
VERSIONES_TIMEOUT_S = 15


class TelefonoError(RuntimeError):
    pass


# --- Lectura pura de volcados ------------------------------------------------

def nodos(xml: str) -> list[dict]:
    """Nodos visibles en orden de documento. Descarta los de ancho o alto cero.

    `clickable` es False si falta el atributo; `enabled` es True si falta (uiautomator
    siempre los escribe, la omisión solo se da en XML sintético). `profundidad` es el
    nivel real en el árbol (0 = primer <node>), contando también los nodos descartados:
    el antecesor visible más cercano de un nodo es el anterior con menor profundidad."""
    try:
        raiz = ET.fromstring(xml.lstrip().encode("utf-8"))
    except ET.ParseError as e:
        raise TelefonoError(f"volcado ilegible: {e}") from e
    fuera = []
    pila = [(raiz, -1)]
    while pila:
        el, nivel = pila.pop()
        if el.tag == "node":
            nivel += 1
            m = _BOUNDS.fullmatch(el.get("bounds", ""))
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                if x2 > x1 and y2 > y1:
                    fuera.append({"texto": el.get("text", ""), "desc": el.get("content-desc", ""),
                                  "clase": el.get("class", ""), "package": el.get("package", ""),
                                  "resource_id": el.get("resource-id", ""),
                                  "clickable": el.get("clickable", "false") == "true",
                                  "enabled": el.get("enabled", "true") == "true",
                                  "profundidad": nivel,
                                  "bounds": (x1, y1, x2, y2),
                                  "centro": ((x1 + x2) // 2, (y1 + y2) // 2)})
        pila.extend((hijo, nivel) for hijo in reversed(list(el)))
    return fuera


def _coincide(n: dict, texto: str | None, contiene: str | None, empieza: str | None) -> bool:
    if texto is None and contiene is None and empieza is None:
        return True
    for valor in (n["texto"], n["desc"]):
        if not valor:
            continue
        if texto is not None and valor == texto:
            return True
        if contiene is not None and contiene in valor:
            return True
        if empieza is not None and valor.startswith(empieza):
            return True
    return False


def buscar_todos(xml: str, *, texto: str | None = None, contiene: str | None = None,
                 empieza: str | None = None, paquete: str | None = None,
                 clase: str | None = None) -> list[dict]:
    """Todas las coincidencias en orden de documento.

    Los criterios de texto (exacto, contiene, empieza) se miran en text y content-desc
    y basta con que se cumpla uno; sin criterio de texto vale cualquier nodo. `paquete`
    y `clase` se comparan exactos y se exigen siempre que se den."""
    return [n for n in nodos(xml)
            if (paquete is None or n["package"] == paquete)
            and (clase is None or n["clase"] == clase)
            and _coincide(n, texto, contiene, empieza)]


def buscar(xml: str, *, texto: str | None = None, contiene: str | None = None,
           empieza: str | None = None, paquete: str | None = None,
           clase: str | None = None) -> dict | None:
    todos = buscar_todos(xml, texto=texto, contiene=contiene, empieza=empieza,
                         paquete=paquete, clase=clase)
    return todos[0] if todos else None


def textos(xml: str) -> list[str]:
    return [n["texto"] for n in nodos(xml) if n["texto"]]


def volcado_valido(salida: str, xml: str) -> bool:
    """El volcado es de ahora y se puede leer.

    Si la interfaz no llega a reposo, uiautomator imprime «ERROR: could not get idle
    state.», no escribe nada y aun así puede salir con 0: sin «dumped to» el archivo
    que se leería es el de antes."""
    if "dumped to" not in salida or "ERROR" in salida:
        return False
    if not xml.lstrip().startswith("<?xml"):
        return False
    try:
        ET.fromstring(xml.lstrip().encode("utf-8"))
    except ET.ParseError:
        return False
    return True


def estado_desde_dumpsys(power: str, window: str) -> dict:
    """Despierto y desbloqueado a partir de `dumpsys power` y `dumpsys window`.

    Si falta isKeyguardShowing no se sabe si está bloqueado: `bloqueado` es None y
    `listo` es False."""
    m = re.search(r"mWakefulness=(\w+)", power)
    despierto = bool(m and m.group(1) == "Awake")
    k = re.search(r"isKeyguardShowing=(true|false)", window)
    bloqueado = None if k is None else k.group(1) == "true"
    return {"despierto": despierto, "bloqueado": bloqueado, "listo": despierto and bloqueado is False}


def focos_de(texto_dumpsys: str) -> list[str]:
    """Componentes `paquete/actividad` de las líneas `mCurrentFocus` y `mFocusedApp` de `dumpsys window`, en ese
    orden (primero todas las de `mCurrentFocus`). Sin `null` ni ventanas sin «/» (p. ej. `PopupWindow:…`); la forma
    corta `paquete/.actividad.Clase` se deja tal cual. Lista vacía si ninguna línea trae componente."""
    focos: list[str] = []
    for clave in ("mCurrentFocus", "mFocusedApp"):
        for m in re.finditer(rf"{clave}=\S*?\{{([^}}]*)\}}", texto_dumpsys):
            focos += [t for t in m.group(1).split() if "/" in t][:1]
    return focos


def teclado_desde_dumpsys(texto: str) -> bool | None:
    """mInputShown de `dumpsys input_method`; None si no aparece."""
    m = re.search(r"mInputShown=(true|false)", texto)
    return None if m is None else m.group(1) == "true"


def tapado(xml: str, nodo: dict) -> bool:
    """Algo dibujado después cubre el centro del nodo.

    Para un NODO del volcado que se va a tocar: cuenta cualquier nodo posterior que contenga el centro, también de la
    propia app. Para un PUNTO que no es un nodo (el inicio de un gesto) está `pantalla.motivo_tapado`.

    El nodo se identifica por (bounds, texto, desc, clase, package): se toma su
    primera aparición en el orden del documento, que es la que deja más nodos
    posteriores por revisar. Cuenta como tapado si un nodo POSTERIOR contiene el
    centro y no cabe entero dentro del nodo (sus propios hijos no lo tapan; una
    lista superpuesta sí). Si el nodo no está en el volcado se devuelve True."""
    clave = ("bounds", "texto", "desc", "clase", "package")
    lista = nodos(xml)
    indice = next((i for i, n in enumerate(lista)
                   if all(n[k] == nodo.get(k) for k in clave)), None)
    if indice is None:
        return True
    x1, y1, x2, y2 = nodo["bounds"]
    cx, cy = nodo["centro"]
    for otro in lista[indice + 1:]:
        ox1, oy1, ox2, oy2 = otro["bounds"]
        contiene_centro = ox1 <= cx < ox2 and oy1 <= cy < oy2
        dentro = ox1 >= x1 and oy1 >= y1 and ox2 <= x2 and oy2 <= y2
        if contiene_centro and not dentro:
            return True
    return False


_VENTANA_DUMPSYS = re.compile(r"Window #\d+ Window\{[0-9a-f]+ u\d+ (?P<nombre>[^}]+)\}:")
_VENTANA_PADRE = re.compile(r"mParentWindow=Window\{[0-9a-f]+ u\d+ (?P<padre>[^}]+)\}")
_VENTANA_PAQUETE_PROPIO = re.compile(r"\bpackage=(\S+)")
_VENTANA_VISIBLE = re.compile(r"\bisVisible=(true|false)\b")
_VENTANA_SURFACE = re.compile(r"\bmHasSurface=(true|false)\b")
_VENTANA_FRAME = re.compile(r"\bframe=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
_VENTANA_FRAME_ANTIGUO = re.compile(r"\bmFrame=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
_VENTANA_FRAME_PADRE = re.compile(r"\bparent=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


def ventanas_emergentes_de(texto: str, paquete: str) -> list[dict]:
    """Ventanas `PopupWindow:*` de `paquete` en `dumpsys window windows` que cuentan como
    visibles: con frame legible o sin él (`"frame": None`, que `hay_desplegable_por_ventana`
    trata como abierta).

    El desplegable de sugerencias de hashtags de Instagram es una ventana aparte que
    `uiautomator dump` no incluye (ver Task 10f): esta lectura complementa al volcado. El
    formato de `dumpsys` varía entre builds de Android, así que ante la duda cada
    comprobación falla cerrado (cuenta la ventana) en vez de descartarla:

    - Paquete: basta con que el bloque sea del paquete dado por su propio `package=` o por
      el `mParentWindow` (comparado como `"<paquete>/"`); con uno de los dos alcanza.
    - Visibilidad: cuenta salvo `isVisible=false` explícito; si falta `isVisible`, cuenta
      salvo `mHasSurface=false` explícito; si faltan ambos, cuenta.
    - Frame: se lee de `frame=[x1,y1][x2,y2]` (formato moderno, dentro de la línea
      `Frames: parent=… display=… frame=… last=…`) o de `mFrame=[x1,y1][x2,y2]` (formato
      antiguo); si no se encuentra ninguno, la entrada lleva `"frame": None` en vez de
      descartarse. `"ancho_padre"` es el ancho de `parent=[x1,y1][x2,y2]` si aparece, o
      `None` si no.

    Cada bloque `Window #N Window{… <nombre>}:` se extiende hasta el siguiente bloque (o
    el final del texto); solo cuentan los que empiezan por «PopupWindow:». Texto vacío da
    lista vacía."""
    encabezados = list(_VENTANA_DUMPSYS.finditer(texto))
    emergentes = []
    for i, m in enumerate(encabezados):
        nombre = m.group("nombre").strip()
        if not nombre.startswith("PopupWindow:"):
            continue
        fin = encabezados[i + 1].start() if i + 1 < len(encabezados) else len(texto)
        bloque = texto[m.end():fin]

        padre = _VENTANA_PADRE.search(bloque)
        del_padre = bool(padre and padre.group("padre").startswith(f"{paquete}/"))
        propio = _VENTANA_PAQUETE_PROPIO.search(bloque)
        es_propio = bool(propio and propio.group(1) == paquete)
        if not (del_padre or es_propio):
            continue

        visible = _VENTANA_VISIBLE.search(bloque)
        if visible is not None:
            if visible.group(1) != "true":
                continue
        else:
            surface = _VENTANA_SURFACE.search(bloque)
            if surface is not None and surface.group(1) != "true":
                continue

        frame_m = _VENTANA_FRAME.search(bloque) or _VENTANA_FRAME_ANTIGUO.search(bloque)
        frame = tuple(map(int, frame_m.groups())) if frame_m else None
        padre_frame = _VENTANA_FRAME_PADRE.search(bloque)
        ancho_padre = int(padre_frame.group(3)) - int(padre_frame.group(1)) if padre_frame else None

        emergentes.append({"nombre": nombre, "frame": frame, "ancho_padre": ancho_padre})
    return emergentes


def consulta_mediastore(nombre: str) -> str:
    """Orden de shell que busca la imagen por nombre en MediaStore."""
    if not _NOMBRE_SEGURO.fullmatch(nombre):
        raise TelefonoError(f"nombre de archivo no apto para la consulta: {nombre!r}")
    return ("content query --uri " + URI_IMAGENES + " --projection _display_name:date_added"
            " --where " + shlex.quote(f"_display_name='{nombre}'"))


def fila_mediastore_presente(salida: str, nombre: str) -> bool:
    """La salida de `content query` trae una fila con ese _display_name exacto."""
    for linea in salida.splitlines():
        if not linea.startswith("Row:"):
            continue
        m = re.search(r"_display_name=(.*?)(?:, \w+=|$)", linea)
        if m and m.group(1) == nombre:
            return True
    return False


def plazos_volcado(timeout: int) -> tuple[int, int]:
    """Reparto del plazo de un volcado: dos tercios para uiautomator y el resto para
    leer el archivo, cada uno de 5 s como mínimo."""
    volcar = max(5, timeout * 2 // 3)
    return volcar, max(5, timeout - volcar)


def es_png(datos: bytes) -> bool:
    return datos.startswith(b"\x89PNG\r\n\x1a\n")


def sha256_de_salida(salida: str) -> str:
    partes = salida.split()
    if not partes or not _SHA256.fullmatch(partes[0]):
        raise TelefonoError(f"sha256sum no dio un hash: {salida.strip()[:200]!r}")
    return partes[0]


def version_desde_dumpsys(salida: str) -> str | None:
    """versionName de `dumpsys package`. Si hay varias distintas (p. ej. un perfil de trabajo de
    MaaS360), todas en orden separadas por « | »; None si no aparece."""
    vistas = list(dict.fromkeys(_VERSION.findall(salida)))
    return " | ".join(vistas) if vistas else None


# --- E/S contra el teléfono --------------------------------------------------

def adb(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise TelefonoError(f"adb {' '.join(args)}: sin respuesta en {timeout} s") from e
    except OSError as e:
        raise TelefonoError(f"adb no se pudo ejecutar: {e}") from e
    if r.returncode != 0:
        raise TelefonoError(f"adb {' '.join(args)}: {r.stderr.decode(errors='replace').strip()[:300]}")
    return r


def shell(cmd: str, timeout: int = 60) -> str:
    return adb("shell", cmd, timeout=timeout).stdout.decode(errors="replace")


def volcado(timeout: int = 30) -> str:
    """Volcado recién hecho; TelefonoError si no es de ahora o no se puede leer.

    `timeout` se reparte entre el volcado y la lectura (ver `plazos_volcado`)."""
    volcar, leer = plazos_volcado(timeout)
    salida = shell(f"rm -f {REMOTO_UI}; uiautomator dump --compressed {REMOTO_UI}", timeout=volcar)
    xml = adb("exec-out", "cat", REMOTO_UI, timeout=leer).stdout.decode("utf-8", errors="replace")
    if not volcado_valido(salida, xml):
        raise TelefonoError(f"volcado no válido: {salida.strip()[:200]!r}")
    return xml


def captura(destino: Path, timeout: int = 60) -> Path:
    """Guarda un screencap en `destino`, esperando a adb como mucho `timeout` s. Un fallo
    del disco (crear la carpeta o escribir) sale como TelefonoError, igual que uno de adb."""
    datos = adb("exec-out", "screencap", "-p", timeout=timeout).stdout
    if not es_png(datos):
        raise TelefonoError(f"screencap no devolvió un PNG ({len(datos)} bytes)")
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)
    except OSError as e:
        raise TelefonoError(f"no se pudo guardar la captura en {destino}: {e}") from e
    return destino


def tocar(x: int, y: int) -> None:
    shell(f"input tap {x} {y}")


def deslizar(x1: int, y1: int, x2: int, y2: int, ms: int = 400) -> None:
    """`input swipe` de (x1, y1) a (x2, y2) en `ms` milisegundos. No comprueba nada: quien llama se asegura de que
    ni el inicio ni el final del gesto caen sobre un control que no se puede tocar (`pantalla.punto_bloqueado`)."""
    shell(f"input swipe {x1} {y1} {x2} {y2} {ms}")


def tecla(codigo: int) -> None:
    shell(f"input keyevent {codigo}")


def combinacion(*codigos: int) -> None:
    shell("input keycombination " + " ".join(map(str, codigos)))


def lanzar(paquete: str) -> None:
    shell(f"monkey -p {paquete} -c android.intent.category.LAUNCHER 1")


def focos(timeout: int = 15) -> list[str]:
    """`focos_de` sobre `dumpsys window` (el mismo comando que lee `estado`); lista vacía si no se puede leer."""
    try:
        return focos_de(shell("dumpsys window", timeout=timeout))
    except TelefonoError:
        return []


def forzar_cierre(paquete: str, timeout: int = 15) -> None:
    """`am force-stop`: el siguiente `lanzar` arranca la app en frío en vez de reanudarla donde se quedó.
    Descarta lo que la app tenga en memoria: solo para quien ya sabe que no hay nada a medias que proteger."""
    shell(f"am force-stop {paquete}", timeout=timeout)


def cerrar_cortina(timeout: int = 15) -> None:
    """Repliega la cortina de notificaciones si está desplegada (no despierta ni desbloquea).
    Timeout corto: quien llama la usa como best-effort y no debe quedarse bloqueado en ella."""
    shell("cmd statusbar collapse", timeout=timeout)


def estado() -> dict:
    """Solo lee: nunca despierta ni desbloquea. Sin teléfono no lanza, dice que no está listo."""
    try:
        conectado = adb("get-state", timeout=15).stdout.decode().strip() == "device"
    except TelefonoError:
        conectado = False
    if not conectado:
        return {"adb": False, "despierto": False, "bloqueado": None, "listo": False}
    try:
        leido = estado_desde_dumpsys(shell("dumpsys power", timeout=30), shell("dumpsys window", timeout=30))
    except TelefonoError:
        leido = {"despierto": False, "bloqueado": None, "listo": False}
    return {"adb": True, **leido}


def ventanas_emergentes(paquete: str, timeout: int = 15) -> list[dict]:
    """Las ventanas `PopupWindow:*` de `paquete` que cuentan como visibles (ver
    `ventanas_emergentes_de`: con frame legible o con `"frame": None`), por ejemplo el
    desplegable de hashtags de Instagram, invisible para `uiautomator dump` (Task 10f).
    Si `dumpsys` falla se propaga TelefonoError: quien llama falla cerrado."""
    return ventanas_emergentes_de(shell("dumpsys window windows", timeout=timeout), paquete)


def teclado_estado() -> bool | None:
    """True/False si se sabe si el teclado está abierto; None si no se puede leer."""
    try:
        return teclado_desde_dumpsys(shell("dumpsys input_method", timeout=30))
    except TelefonoError:
        return None


def teclado_visible() -> bool:
    """Si no se puede saber, se da por visible."""
    visible = teclado_estado()
    return True if visible is None else visible


def versiones(paquetes: dict[str, str]) -> dict[str, str | None]:
    """Versión instalada de cada app (clave → paquete). Solo lee `dumpsys package`: no abre ninguna app.
    Cada app espera como mucho `VERSIONES_TIMEOUT_S`; si esa lectura falla, su versión es None."""
    fuera: dict[str, str | None] = {}
    for app, paquete in paquetes.items():
        try:
            fuera[app] = version_desde_dumpsys(shell(f"dumpsys package {paquete}", timeout=VERSIONES_TIMEOUT_S))
        except TelefonoError:
            fuera[app] = None
    return fuera


def subir(local: Path, remoto: str) -> dict:
    """Sube la imagen, la registra en MediaStore y comprueba el hash.

    `subido_en` (ISO, UTC) es el momento de la subida: la miniatura del selector de
    Instagram debe llevar esa hora."""
    nombre = remoto.rsplit("/", 1)[-1]
    consulta = consulta_mediastore(nombre)
    local_sha = hashlib.sha256(local.read_bytes()).hexdigest()
    q = shlex.quote(remoto)
    adb("push", str(local), remoto, timeout=120)
    subido_en = datetime.now(timezone.utc)
    shell(f"touch {q}")
    shell("am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d " + shlex.quote(f"file://{remoto}"))
    limite = time.monotonic() + ESPERA_MEDIASTORE_S
    while not fila_mediastore_presente(shell(consulta), nombre):
        if time.monotonic() >= limite:
            raise TelefonoError(f"{nombre} no aparece en MediaStore tras {ESPERA_MEDIASTORE_S} s")
        time.sleep(1)
    remoto_sha = sha256_de_salida(shell(f"sha256sum {q}"))
    if remoto_sha != local_sha:
        raise TelefonoError(f"hash distinto en el teléfono: {remoto_sha} != {local_sha}")
    return {"sha256": local_sha, "subido_en": subido_en.isoformat()}
