#!/usr/bin/env python3
"""
Punto de entrada único del laboratorio.

    .venv/bin/python experiments/media-lab/lab.py <subcomando> [...]

Todo lo que toca encargos, teléfono, Codex o GitHub pasa por aquí: basta con
autorizar este comando para que una ejecución desatendida no se quede colgada
esperando un permiso que nadie va a contestar. A propósito no hay ningún
subcomando que borre o cancele publicaciones: eso es manual (media-lab-cancel).

Códigos de salida: 0 bien; 1 fallo de generación o interrupción; 2 argumentos o
datos no válidos (siempre con JSON {"ok": false, "tipo", "error"}); 3 cerrojo no
tomado o no soltado; 4 pantalla inesperada o error del teléfono; 5 envío de
Instagram no confirmado; 6 Codex tocó archivos no permitidos.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(ROOT / "src" / "render"))

from labkit import cerrojo, codex_rescate, colision, encargos, guardia, manifiesto, seleccion, turnos  # noqa: E402

ENCARGOS = Path(os.environ.get("LAB_ENCARGOS_DIR", LAB / "encargos"))
COBERTURA = Path(os.environ.get("LAB_COVERAGE", LAB / "coverage.json"))
# Solo para render/tarjeta: dónde escriben los másteres. Por defecto ROOT (el repo real);
# las pruebas lo redirigen a una carpeta temporal para no ensuciar experiments/media-lab/assets/.
ASSETS_DIR = Path(os.environ.get("LAB_ASSETS_DIR", ROOT))
EVIDENCIA = LAB / "evidence" / "android"
LOCK = LAB / ".ventana.lock"
TURNOS = Path(os.environ.get("LAB_TURNOS", LAB / "turnos.json"))
TURNO_HECHO = Path(os.environ.get("LAB_TURNO_HECHO", LAB / ".turno-hecho"))

DUENOS_VENTANA = ("programada", "manual")
ESTADOS_ACTIVOS = ("pedido", "generando", "generado", "aprobado")
TIMEOUT_CODEX_S = 420
COLA_BYTES = 1500
SENALES = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
ASSETS = "experiments/media-lab/assets/"
EXTENSIONES_SUBIDA = (".png", ".jpg", ".jpeg")
_NOMBRE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_FAMILIA = re.compile(r"[A-Za-z0-9_-]+")
EXTENSIONES_MASTER = (".jpg", ".jpeg", ".png")


class ArgumentoNoValido(ValueError):
    pass


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def emitir(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def ruta_encargo(encargo_id: str) -> Path:
    return ENCARGOS / f"{encargo_id}.json"


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise ArgumentoNoValido(mensaje)


def _rechazo(tipo: str, errores: list[str]) -> int:
    emitir({"ok": False, "tipo": tipo, "error": "; ".join(errores), "errores": errores})
    return 2


def _relativa_sin_salidas(rel: str, base: str, que: str) -> Path:
    """ROOT/rel si rel es relativa, empieza por base, no tiene «..», no es un enlace, existe
    y, resuelta, sigue dentro de ROOT/base."""
    partes = PurePosixPath(rel)
    _exigir(not partes.is_absolute() and rel.startswith(base) and ".." not in partes.parts,
            f"{que} debe ser una ruta relativa bajo {base} sin «..»: {rel}")
    p = ROOT / rel
    _exigir(not p.is_symlink(), f"{que} es un enlace simbólico: {rel}")
    _exigir(p.is_file(), f"{que} no existe: {rel}")
    _exigir(p.resolve().is_relative_to((ROOT / base).resolve()), f"{que} sale de {base}: {rel}")
    return p


def _rgb(valor: str) -> tuple[int, int, int]:
    """Type de argparse para --panel-rgb/--accent-rgb: no depende de Pillow, así que construir()
    no obliga a tenerlo instalado solo para montar los subcomandos."""
    partes = valor.split(",")
    if len(partes) != 3:
        raise argparse.ArgumentTypeError("el color debe ser R,G,B")
    try:
        rgb = tuple(int(p) for p in partes)
    except ValueError:
        raise argparse.ArgumentTypeError("el color debe ser R,G,B con enteros") from None
    if any(v < 0 or v > 255 for v in rgb):
        raise argparse.ArgumentTypeError("el color debe ser R,G,B con valores de 0 a 255")
    return rgb


def _formato_de_encargo(formato: dict) -> str | None:
    """«feed» si alto/ancho ≈ 1.25 (1080x1350), «story» si ≈ 1.78 (1080x1920), si no None."""
    ancho, alto = (formato or {}).get("ancho"), (formato or {}).get("alto")
    if not ancho or not alto:
        return None
    ratio = alto / ancho
    if abs(ratio - 1.25) < 0.03:
        return "feed"
    if abs(ratio - 16 / 9) < 0.03:
        return "story"
    return None


def _nombre_archivo_simple(nombre: str, extensiones: tuple[str, ...], que: str) -> None:
    _exigir(bool(nombre) and "/" not in nombre and ".." not in nombre and nombre not in (".", ".."),
            f"{que} debe ser un nombre de archivo simple, sin «/» ni «..»: {nombre!r}")
    _exigir(Path(nombre).suffix.lower() in extensiones,
            f"{que} debe terminar en {' o '.join(extensiones)}: {nombre!r}")


# ── comprobación previa ─────────────────────────────────────────────────────

def cmd_preflight(a) -> int:
    from labkit import telefono
    t = ahora()
    try:
        tel = telefono.estado()
    except Exception as e:  # noqa: BLE001 — preflight informa, nunca rompe
        tel = {"listo": False, "error": f"{type(e).__name__}: {e}"}
    try:
        en_curso = colision.workflows_en_curso()
        espera = colision.motivo_espera(
            t, programadas=colision.programadas_de_cola(ROOT / "content" / "queue"),
            publicadas=colision.publicadas_recientes(ROOT / "content" / "published", t),
            en_curso=en_curso)
        github = True
    except Exception as e:  # noqa: BLE001
        github, espera = False, f"GitHub no responde ({type(e).__name__}): sin datos de producción cercana"
    emitir({"ahora": t.isoformat(timespec="seconds"), "telefono": tel, "github": github, "espera": espera})
    return 0


def cmd_lock_tomar(a) -> int:
    ok = cerrojo.tomar(LOCK, ahora(), a.dueno)
    emitir({"cerrojo": ok})
    return 0 if ok else 3


def cmd_lock_soltar(a) -> int:
    soltado = cerrojo.soltar(LOCK, a.dueno)
    emitir({"cerrojo": "soltado" if soltado else "no era tuyo o no existía"})
    return 0 if soltado else 3


# ── turno ────────────────────────────────────────────────────────────────────

def _turno_config(ruta: Path) -> tuple[datetime, int, int]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ArgumentoNoValido(f"{ruta.name} ilegible: {type(e).__name__}: {e}") from e
    _exigir(isinstance(datos, dict), f"{ruta.name} debe ser un objeto JSON")
    faltan = {"ancla", "cada_horas", "tolerancia_min"} - set(datos)
    _exigir(not faltan, f"{ruta.name} incompleto: faltan {', '.join(sorted(faltan))}")
    try:
        ancla = datetime.fromisoformat(datos["ancla"])
    except (TypeError, ValueError) as e:
        raise ArgumentoNoValido(f"ancla no es una fecha ISO 8601 válida: {datos.get('ancla')!r}") from e
    _exigir(ancla.tzinfo is not None, "ancla necesita zona horaria")
    cada_horas, tolerancia_min = datos["cada_horas"], datos["tolerancia_min"]
    _exigir(_entero_positivo(cada_horas), "cada_horas debe ser un entero positivo")
    _exigir(_entero_positivo(tolerancia_min), "tolerancia_min debe ser un entero positivo")
    return ancla, cada_horas, tolerancia_min


def _entero_positivo(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def cmd_turno(a) -> int:
    ancla, cada_horas, tolerancia_min = _turno_config(TURNOS)
    if a.ahora:
        try:
            t = datetime.fromisoformat(a.ahora)
        except ValueError as e:
            raise ArgumentoNoValido(f"--ahora no es una fecha ISO 8601: {a.ahora!r}") from e
        _exigir(t.tzinfo is not None, "--ahora necesita zona horaria")
    else:
        t = ahora()
    ultimo = TURNO_HECHO.read_text(encoding="utf-8").strip() if TURNO_HECHO.is_file() else None
    r = turnos.turno_actual(t, ancla, cada_horas, tolerancia_min, ultimo)
    madrid = ZoneInfo("Europe/Madrid")

    def _fechas(clave: str, valor: datetime) -> None:
        salida[clave] = valor.isoformat(timespec="seconds")
        salida[f"{clave}_madrid"] = valor.astimezone(madrid).isoformat(timespec="seconds")

    salida: dict = {"toca": r["toca"], "motivo": r["motivo"],
                    "minutos_desde_inicio": round(r["minutos_desde_inicio"], 3)}
    _fechas("turno_inicio", r["turno_inicio"])
    _fechas("siguiente", r["siguiente"])
    _fechas("ahora", r["ahora"])
    if a.marcar:
        if not r["toca"]:
            return _rechazo("TurnoNoValido", [f"no se marca: {r['motivo']}"])
        tmp = TURNO_HECHO.with_name(f".{TURNO_HECHO.name}.tmp")
        TURNO_HECHO.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(salida["turno_inicio"], encoding="utf-8")
        os.replace(tmp, TURNO_HECHO)
        salida["marcado"] = True
    emitir(salida)
    return 0


# ── encargos (Claude) ───────────────────────────────────────────────────────

def _comprobar_celdas(ids: list[str], todos: list[dict]) -> None:
    """Las celdas existen, se pueden publicar, comparten formato y no tienen ya un encargo en curso."""
    celdas = {c["cell_id"]: c for c in json.loads(COBERTURA.read_text(encoding="utf-8"))["cells"]}
    problemas = []
    if len(set(ids)) != len(ids):
        problemas.append("hay celdas repetidas en --cell")
    for cid in dict.fromkeys(ids):
        c = celdas.get(cid)
        if c is None:
            problemas.append(f"{cid} no está en coverage.json")
            continue
        if c["status"] not in seleccion.ESTADOS_ELEGIBLES:
            problemas.append(f"{cid} está en {c['status']}")
        if not seleccion._ruta_implementada(c):
            problemas.append(f"{cid}: {c['platform']}/{c['native_format']} por {c['publishing_route']} no está implementado")
    formatos = sorted({celdas[cid]["native_format"] for cid in ids if cid in celdas})
    if len(formatos) > 1:
        problemas.append(f"un encargo no mezcla formatos: {', '.join(formatos)}")
    ocupadas = {cid: e["encargo_id"] for e in todos if e["estado"] in ESTADOS_ACTIVOS
                for cid in e.get("coverage_cell_ids", [])}
    for cid in dict.fromkeys(ids):
        if cid in ocupadas:
            problemas.append(f"{cid} ya tiene el encargo {ocupadas[cid]} en curso")
    _exigir(not problemas, "; ".join(problemas))


def cmd_encargo_nuevo(a) -> int:
    t = ahora()
    todos = [e for _, e in encargos.listar(ENCARGOS)]
    _exigir(encargos.en_cola(todos) < encargos.MAX_EN_COLA, f"ya hay {encargos.MAX_EN_COLA} encargos en cola")
    _comprobar_celdas(a.cell, todos)
    enc = encargos.nuevo(
        encargos.siguiente_id(ENCARGOS, t), coverage_cell_ids=a.cell, family_id=a.family,
        brief_path=a.brief, do_not_use=a.do_not_use or [], formato=json.loads(a.formato),
        prompt=Path(a.prompt_file).read_text(encoding="utf-8").strip(),
        restricciones=a.restriccion or [],
        destino_assets=f"{ASSETS}{a.family}", ahora=t, variantes=a.variantes)
    encargos.guardar(ruta_encargo(enc["encargo_id"]), enc)
    emitir(enc)
    return 0


def cmd_encargos(a) -> int:
    buenos, malos = encargos.listar_tolerante(ENCARGOS)
    emitir([{k: e.get(k) for k in ("encargo_id", "estado", "coverage_cell_ids", "lock_owner", "imagenes")}
            for _, e in buenos] + malos)
    return 0


def cmd_encargo_revisar(a) -> int:
    ruta = ruta_encargo(a.encargo)
    enc = encargos.cargar(ruta)
    if a.aprobado:
        errores = codex_rescate.validar(enc, ROOT)
        if errores:
            return _rechazo("ImagenNoValida", errores)
    enc = encargos.revisar(enc, aprobado=a.aprobado, motivo=a.motivo, ahora=ahora(), correccion=a.correccion)
    encargos.guardar(ruta, enc)
    emitir({"encargo_id": enc["encargo_id"], "estado": enc["estado"]})
    return 0


def cmd_encargo_usado(a) -> int:
    ruta = ruta_encargo(a.encargo)
    enc = encargos.marcar_usado(encargos.cargar(ruta), a.run)
    encargos.guardar(ruta, enc)
    emitir({"encargo_id": enc["encargo_id"], "estado": enc["estado"], "runs": enc["runs"]})
    return 0


def cmd_seleccionar(a) -> int:
    cov = json.loads(COBERTURA.read_text(encoding="utf-8"))
    emitir(seleccion.elegir(cov["cells"], [e for _, e in encargos.listar(ENCARGOS)],
                            max_celdas=a.max, telefono_listo=not a.sin_telefono))
    return 0


# ── render (Claude) ─────────────────────────────────────────────────────────

def cmd_render(a) -> int:
    """Máster con texto determinista sobre una imagen ya aprobada. Nunca reutiliza el máster
    de otro encargo: la imagen de origen sale de las imágenes registradas de ESTE encargo."""
    import render_overlay
    from PIL import Image
    enc = encargos.cargar(ruta_encargo(a.encargo))
    if enc["estado"] not in ("aprobado", "usado"):
        return _rechazo("ImagenNoValida", [f"{a.encargo} no está aprobado ni usado (estado {enc['estado']})"])
    if not (1 <= a.variante <= len(enc["imagenes"])):
        return _rechazo("ImagenNoValida", [f"la variante {a.variante} no existe en {a.encargo}"])
    imagen = enc["imagenes"][a.variante - 1]
    origen = ROOT / imagen["ruta"]
    if origen.is_symlink() or not origen.is_file() or sha256(origen) != imagen["sha256"]:
        return _rechazo("ImagenNoValida",
                        [f"la imagen de origen no coincide con el hash registrado: {imagen['ruta']}"])
    lineas = a.titular.split("|")
    _exigir(len(lineas) == 3, "--titular debe tener exactamente 3 líneas separadas por «|»")
    esperado = _formato_de_encargo(enc["formato"])
    _exigir(esperado == a.formato,
            f"--formato {a.formato!r} no coincide con el formato del encargo {enc['formato']} (esperado {esperado!r})")
    _nombre_archivo_simple(a.salida, EXTENSIONES_MASTER, "--salida")
    destino = ASSETS_DIR / enc["destino_assets"] / a.salida
    _exigir(not destino.exists(), f"--salida ya existe: {a.salida}")
    render_overlay.render(origen, destino, lineas, a.subtitulo, a.panel_rgb, a.accent_rgb, a.formato,
                          a.aviso or "")
    with Image.open(destino) as im:
        ancho, alto = im.size
    emitir({"ok": True, "master": f"{enc['destino_assets']}/{a.salida}", "sha256": sha256(destino),
            "ancho": ancho, "alto": alto, "formato": a.formato})
    return 0


def cmd_tarjeta(a) -> int:
    """Tarjeta de cita (src/render/quote_card.py), para encargos que no llevan foto de fondo."""
    import quote_card
    from PIL import Image
    _exigir(bool(_FAMILIA.fullmatch(a.familia)),
            f"--familia no válida: solo letras, dígitos, guion y guion bajo: {a.familia!r}")
    _nombre_archivo_simple(a.salida, (".png",), "--salida")
    destino = ASSETS_DIR / ASSETS / a.familia / a.salida
    _exigir(not destino.exists(), f"--salida ya existe: {a.salida}")
    quote_card.make_card(a.cita, a.autor, str(destino), variant=a.variante)
    with Image.open(destino) as im:
        ancho, alto = im.size
    emitir({"ok": True, "tarjeta": f"{ASSETS}{a.familia}/{a.salida}", "sha256": sha256(destino),
            "ancho": ancho, "alto": alto})
    return 0


# ── generación (Codex) ──────────────────────────────────────────────────────

def cmd_codex_tomar(a) -> int:
    t = ahora()
    tomados = []
    for ruta, enc in encargos.listar(ENCARGOS):
        if len(tomados) >= a.max:
            break
        if encargos.tomable(enc, t):
            encargos.tomar(enc, a.owner, t)
            encargos.guardar(ruta, enc)
            tomados.append({"encargo_id": enc["encargo_id"], "prompt": enc["prompt"],
                            "restricciones": enc["restricciones"] + enc["do_not_use"],
                            "formato": enc["formato"], "rutas": codex_rescate.rutas_imagen(enc)})
    emitir(tomados)
    return 0


def cmd_codex_generado(a) -> int:
    """Registra las imágenes solo si son exactamente las pedidas y la copia resultante valida;
    si algo falla no se guarda nada."""
    from PIL import Image, UnidentifiedImageError
    ruta = ruta_encargo(a.encargo)
    enc = encargos.cargar(ruta)
    pedidas = codex_rescate.rutas_imagen(enc)
    carpeta = (ROOT / enc["destino_assets"]).resolve()
    errores: list[str] = []
    imagenes: list[dict] = []
    for rel in a.imagen:
        p = ROOT / rel
        if rel not in pedidas:
            errores.append(f"{rel} no es una de las rutas pedidas ({', '.join(pedidas)})")
        elif p.is_symlink():
            errores.append(f"{rel} es un enlace simbólico")
        elif not p.is_file():
            errores.append(f"no existe {rel}")
        elif not p.resolve().is_relative_to(carpeta):
            errores.append(f"{rel} sale de {enc['destino_assets']}")
        else:
            try:
                with Image.open(p) as im:
                    ancho, alto = im.size
            except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as e:
                errores.append(f"{rel} no es una imagen legible ({type(e).__name__})")
            else:
                imagenes.append({"ruta": rel, "sha256": sha256(p), "ancho": ancho, "alto": alto})
    copia = copy.deepcopy(enc)
    if not errores:
        try:
            encargos.marcar_generado(copia, a.owner, imagenes, ahora())
        except encargos.EncargoError as e:
            errores.append(str(e))
        else:
            errores += codex_rescate.validar(copia, ROOT)
    if errores:
        return _rechazo("ImagenNoValida", errores)
    encargos.guardar(ruta, copia)
    emitir(copia["imagenes"])
    return 0


def cmd_codex_fallo(a) -> int:
    ruta = ruta_encargo(a.encargo)
    enc = encargos.marcar_fallo(encargos.cargar(ruta), a.owner, a.nota, ahora())
    encargos.guardar(ruta, enc)
    emitir({"encargo_id": enc["encargo_id"], "estado": enc["estado"]})
    return 0


def _matar_grupo(proc: subprocess.Popen | None) -> None:
    """SIGKILL a todo el grupo de Codex mientras su líder sigue sin recoger. Si ya se recogió
    no se toca aquí: eso lo hace `_matar_restos` justo después de la espera."""
    if proc is None or proc.returncode is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _matar_restos(pgid: int) -> None:
    """SIGKILL a lo que quede del grupo de Codex tras recoger al líder: un hijo en segundo
    plano no puede escribir después de la segunda foto de la guardia."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _cola(archivo) -> str:
    archivo.seek(0, os.SEEK_END)
    archivo.seek(max(0, archivo.tell() - COLA_BYTES))
    return archivo.read().decode("utf-8", errors="replace")


def _leer_respuesta(salida: Path):
    try:
        return json.loads(salida.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ejecutar_codex(enc: dict, salida: Path, timeout: int, vivo: dict) -> tuple[int | None, str]:
    """Lanza codex exec en su propio grupo, espera como mucho `timeout` s y devuelve
    (código o None, cola de su salida). `vivo["proc"]` es el proceso mientras corre, para
    que el manejador de señales pueda matarlo. Al volver no queda nada vivo en su grupo."""
    if vivo["senal"] is not None:
        return None, "codex exec no se lanzó: llegó una señal antes"
    with tempfile.TemporaryFile() as registro:
        try:
            proc = subprocess.Popen(codex_rescate.comando(codex_rescate.prompt_para(enc), salida), cwd=ROOT,
                                    stdin=subprocess.DEVNULL, stdout=registro, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        except OSError as e:
            return None, f"codex exec no arrancó: {e}"
        vivo["lanzado"] = True  # desde aquí Codex pudo escribir: una interrupción ya cuenta como intento
        aviso = ""
        vivo["proc"] = proc
        try:
            if vivo["senal"] is not None:  # la señal llegó mientras arrancaba
                _matar_grupo(proc)
            try:
                codigo = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _matar_grupo(proc)  # también sus hijos: nada escribe tarde
                codigo, aviso = None, f"codex exec superó {timeout} s\n"
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    aviso += "codex exec no terminó 10 s después de SIGKILL\n"
        finally:
            vivo["proc"] = None
            _matar_restos(proc.pid)
        return codigo, aviso + _cola(registro)


def _permitidas(enc: dict, ruta: Path) -> set[str]:
    """Lo que Codex puede cambiar: sus imágenes, el JSON del encargo y el temporal de su
    escritura atómica (un corte a mitad de `encargos.guardar` lo deja atrás)."""
    permitidas = set(codex_rescate.rutas_imagen(enc))
    for p in (ruta, ruta.parent / f".{ruta.name}.tmp"):
        try:
            permitidas.add(p.resolve().relative_to(ROOT).as_posix())
        except ValueError:
            pass  # LAB_ENCARGOS_DIR fuera del repo (pruebas)
    return permitidas


def _ajenos(antes: dict[str, str], permitidas: set[str]) -> list[str]:
    try:
        return guardia.cambios_ajenos(antes, guardia.estado_git(ROOT), permitidas)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        return [f"<no se pudo comprobar git: {e}>"]


def _deshacer(ruta: Path, nota: str, bloquear: bool) -> list[str]:
    """Deja el encargo como tras un fallo si codex-exec lo dejó generando o generado; con
    `bloquear` (Codex tocó archivos ajenos) queda bloqueado en los dos casos, para que otra
    ventana no lo reintente. En cualquier otro estado (p. ej. aún en pedido) no hace nada.
    Solo para después de lanzar Codex: si no llegó a lanzarse se usa `_liberar`."""
    try:
        enc = encargos.cargar(ruta)
        if enc["estado"] == "generando" and enc["lock_owner"] == "codex-exec":
            encargos.marcar_fallo(enc, "codex-exec", nota, ahora(), bloquear=bloquear)
        elif enc["estado"] == "generado" and (enc.get("intentos") or [{}])[-1].get("origen") == "codex-exec":
            encargos.invalidar(enc, nota, ahora(), bloquear=bloquear)
        else:
            return []
        encargos.guardar(ruta, enc)
    except (OSError, ValueError, KeyError, TypeError) as e:
        return [f"no se pudo deshacer el encargo: {type(e).__name__}: {e}"]
    return []


def _liberar(ruta: Path) -> list[str]:
    """Devuelve a pedido, sin sumar intento, un encargo que `generar` tomó pero en el que Codex
    no llegó a lanzarse (señal o error antes del lanzamiento): no hubo intento que contar.
    Solo toca un encargo que siga en generando por codex-exec."""
    try:
        enc = encargos.cargar(ruta)
        if enc["estado"] != "generando" or enc["lock_owner"] != "codex-exec":
            return []
        encargos.guardar(ruta, encargos.liberar(enc, "codex-exec"))
    except (OSError, ValueError, KeyError, TypeError) as e:
        return [f"no se pudo liberar el encargo: {type(e).__name__}: {e}"]
    return []


def cmd_generar(a) -> int:
    ruta = ruta_encargo(a.encargo)
    enc = encargos.cargar(ruta)
    if not encargos.tomable(enc, ahora()):
        raise encargos.EncargoError(f"{a.encargo} no se puede tomar en estado {enc['estado']}")
    _exigir(a.timeout > 0, "--timeout debe ser positivo")
    try:
        v = subprocess.run([codex_rescate.CODEX, "--version"], capture_output=True, text=True,
                           timeout=30, stdin=subprocess.DEVNULL)
        if v.returncode != 0:
            raise OSError(v.stderr.strip()[:200] or f"exit {v.returncode}")
    except (OSError, subprocess.TimeoutExpired) as e:
        emitir({"ok": False, "errores": [f"codex no disponible: {e}"]})
        return 1
    try:
        antes = guardia.estado_git(ROOT)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        emitir({"ok": False, "errores": [f"no se pudo tomar la foto de git: {e}"]})
        return 1
    vivo: dict = {"proc": None, "senal": None, "lanzado": False}

    def al_recibir(numero, _marco) -> None:
        # Quien nos llama se va: Codex no puede seguir escribiendo sin nadie que lo compruebe.
        vivo["senal"] = numero
        _matar_grupo(vivo["proc"])

    # Los manejadores van antes de tomar el encargo: una señal a partir de aquí siempre acaba
    # en la limpieza de abajo (y `_deshacer` no toca un encargo que siga en pedido).
    previos = {s: signal.signal(s, al_recibir) for s in SENALES}
    carpeta_salida: Path | None = None
    try:
        enc = encargos.tomar(enc, "codex-exec", ahora())
        encargos.guardar(ruta, enc)
        try:
            permitidas = _permitidas(enc, ruta)
            carpeta_salida = Path(tempfile.mkdtemp(prefix="codex-exec-"))
            salida = carpeta_salida / "respuesta.json"
            codigo, cola = _ejecutar_codex(enc, salida, a.timeout, vivo)
        except Exception as e:
            # Una excepción no puede dejar el encargo en generando 30 minutos.
            if not vivo["lanzado"]:
                # Antes del lanzamiento (`_permitidas`, `mkdtemp`…): se libera en vez de `_deshacer`,
                # porque Codex no corrió y no hay intento que contar.
                problemas = _liberar(ruta)
            else:
                # Codex pudo escribir: guardia y deshacer (contando el intento) antes de relanzar.
                ajenos = _ajenos(antes, permitidas)
                nota = f"error tras lanzar Codex: {type(e).__name__}: {e}"
                if ajenos:
                    nota += f"; cambió: {', '.join(ajenos)}"
                problemas = [nota, *_deshacer(ruta, nota, bloquear=bool(ajenos))]
            for problema in problemas:
                print(problema, file=sys.stderr)
                e.add_note(problema)
            raise
        respuesta = _leer_respuesta(salida)
        ajenos = _ajenos(antes, permitidas)
        if not vivo["lanzado"]:
            # Señal antes del lanzamiento o fallo de Popen: Codex no corrió, así que se libera sin
            # sumar intento ni bloquear aunque haya cambios ajenos (no son suyos); se informan con 6.
            if vivo["senal"] is not None:
                nota = f"interrumpido por señal {vivo['senal']} antes de lanzar Codex"
            else:
                nota = cola.strip() or "codex exec no se lanzó"
            if ajenos:
                nota += f"; cambió: {', '.join(ajenos)}"
            emitir({"ok": False, "errores": [nota, *_liberar(ruta)], "ajenos": ajenos})
            return 6 if ajenos else 1
        if vivo["senal"] is not None:
            nota = f"interrumpido por señal {vivo['senal']}"
            if ajenos:
                nota += f"; cambió: {', '.join(ajenos)}"
            _deshacer(ruta, nota, bloquear=bool(ajenos))
            emitir({"ok": False, "errores": [nota], "ajenos": ajenos})
            return 6 if ajenos else 1
        try:
            enc = encargos.cargar(ruta)
            errores = codex_rescate.validar(enc, ROOT)
        except (OSError, ValueError, KeyError, TypeError) as e:
            errores = [f"encargo ilegible tras codex exec: {type(e).__name__}: {e}"]
        if ajenos:
            errores.append("Codex cambió archivos no permitidos: " + ", ".join(ajenos))
        if errores:
            errores += _deshacer(ruta, f"{'; '.join(errores)} | exit={codigo}", bloquear=bool(ajenos))
            emitir({"ok": False, "errores": errores, "ajenos": ajenos, "exit": codigo, "salida": cola,
                    "respuesta": respuesta})
            return 6 if ajenos else 1
        emitir({"ok": True, "imagenes": enc["imagenes"], "respuesta": respuesta})
        return 0
    finally:
        for s, manejador in previos.items():
            signal.signal(s, manejador)
        if carpeta_salida is not None:
            shutil.rmtree(carpeta_salida, ignore_errors=True)


# ── API ─────────────────────────────────────────────────────────────────────

def _pares(textos: list[str], que: str) -> dict[str, str]:
    fuera: dict[str, str] = {}
    for texto in textos:
        clave, igual, valor = texto.partition("=")
        if not igual or not clave or not valor:
            raise manifiesto.ManifiestoError(f"{que} debe tener la forma plataforma=valor: {texto!r}")
        if clave in fuera:
            raise manifiesto.ManifiestoError(f"{que} repite {clave}")
        fuera[clave] = valor
    return fuera


def _escribir_manifiesto(rel: str, datos: dict) -> None:
    """Crea el manifiesto; si ya existe no lo pisa."""
    destino = ROOT / rel
    texto = json.dumps(datos, ensure_ascii=False, indent=2) + "\n"
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destino.open("x", encoding="utf-8") as f:
            f.write(texto)
    except FileExistsError as e:
        raise manifiesto.ManifiestoError(f"{rel} ya existe: no se pisa un manifiesto") from e


def cmd_manifiesto_api(a) -> int:
    rutas_pies = _pares(a.caption, "--caption")
    try:
        asset = _relativa_sin_salidas(a.asset, ASSETS, "el asset")
    except ArgumentoNoValido as e:
        raise manifiesto.ManifiestoError(str(e)) from e
    captions = {plataforma: Path(archivo).read_text(encoding="utf-8").rstrip("\n")
                for plataforma, archivo in rutas_pies.items()}
    m = manifiesto.manifiesto_api(a.run_group, a.asset, sha256(asset), captions, family_id=a.family)
    _escribir_manifiesto(manifiesto.ruta_manifiesto(a.run_group), m)
    emitir({"manifiesto": manifiesto.ruta_manifiesto(a.run_group), "platforms": m["platforms"]})
    return 0


def cmd_manifiesto_verificacion(a) -> int:
    m = manifiesto.manifiesto_verificacion(a.run_group, _pares(a.post, "--post"))
    _escribir_manifiesto(manifiesto.ruta_verificacion(a.run_group), m)
    emitir({"manifiesto": manifiesto.ruta_verificacion(a.run_group)})
    return 0


# ── teléfono ────────────────────────────────────────────────────────────────

def _evidencia(run_id: str) -> Path:
    return EVIDENCIA / run_id


def _paso_telefono(ev: Path, nombre: str, fn, codigo_de=lambda res: 0) -> int:
    """Ejecuta un paso de teléfono. Ante una pantalla inesperada, un error de adb o de disco
    intenta una captura `nombre`.png, emite JSON y sale con 4; nunca reintenta nada."""
    from labkit import instagram_feed, telefono
    try:
        res = fn()
    except (instagram_feed.PantallaInesperada, telefono.TelefonoError, OSError) as e:
        try:
            captura = telefono.captura(ev / f"{nombre}.png")
        except (telefono.TelefonoError, OSError):
            captura = None
        emitir({"ok": False, "tipo": type(e).__name__, "error": str(e), "captura": captura})
        return 4
    codigo = codigo_de(res)
    emitir({"ok": codigo == 0, **res})
    return codigo


def cmd_telefono_subir(a) -> int:
    from labkit import telefono
    local = _relativa_sin_salidas(a.local, "experiments/media-lab/", "--local")
    _exigir(local.suffix.lower() in EXTENSIONES_SUBIDA, f"--local debe ser {', '.join(EXTENSIONES_SUBIDA)}: {a.local}")
    _exigir(bool(_NOMBRE.fullmatch(local.name)), f"nombre de archivo no apto para MediaStore: {local.name}")
    remoto = f"/sdcard/Pictures/SabiduriaLab/{local.name}"
    return _paso_telefono(_evidencia("subidas"), f"subir-inesperada-{local.stem}",
                          lambda: {"remoto": remoto, **telefono.subir(local, remoto)})


def cmd_telefono_captura(a) -> int:
    from labkit import telefono
    ev = _evidencia(a.run)
    return _paso_telefono(ev, f"{a.nombre}-inesperada",
                          lambda: {"captura": str(telefono.captura(ev / f"{a.nombre}.png"))})


def cmd_telefono_atras(a) -> int:
    from labkit import instagram_feed
    ev = _evidencia(a.run)
    return _paso_telefono(ev, f"{a.nombre}-inesperada",
                          lambda: {"captura": str(instagram_feed.atras(ev, a.nombre))})


def cmd_ig(a) -> int:
    from labkit import instagram_feed as ig
    ev = _evidencia(a.run)
    pie = subido = None
    if a.paso in ("pie", "compartir"):
        _exigir(bool(a.pie), "--pie es obligatorio en este paso")
        pie = Path(a.pie).read_text(encoding="utf-8").rstrip("\n")
    if a.paso == "abrir":
        _exigir(bool(a.subido_en), "--subido-en es obligatorio en abrir (lo devuelve telefono-subir)")
        try:
            subido = datetime.fromisoformat(a.subido_en)
        except ValueError as e:
            raise ArgumentoNoValido(f"--subido-en no es una fecha ISO 8601: {a.subido_en!r}") from e
        _exigir(subido.tzinfo is not None, "--subido-en necesita zona horaria")
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    if a.paso == "compartir":
        _exigir(bool(a.tema) and a.publicaciones_antes is not None, "compartir exige --tema y --publicaciones-antes")
    pasos = {
        "abrir": lambda: ig.abrir_nueva_publicacion(ev, subido),
        "recorte": lambda: {"captura": ig.alternar_recorte(ev)},
        "editor": lambda: {"captura": ig.siguiente(ev, "ig-02b-editor")},
        "audio": lambda: ig.anadir_audio_sugerido(ev),
        "detalles": lambda: {"captura": ig.detalles(ev)},
        "pie": lambda: {"captura": ig.escribir_pie(pie, ev)},
        # compartir sale con 5 si el envío no queda confirmado, para conciliar antes de nada
        "compartir": lambda: ig.compartir(pie, a.tema, ev, a.publicaciones_antes,
                                          produccion_cercana=a.produccion_cercana),
    }
    codigo_de = (lambda res: 0 if res["estado"] == "confirmado" else 5) if a.paso == "compartir" else (lambda res: 0)
    return _paso_telefono(ev, f"ig-inesperada-{a.paso}", pasos[a.paso], codigo_de)


class Analizador(argparse.ArgumentParser):
    """argparse que, ante un error de argumentos, emite el mismo JSON que el resto de errores
    (sale con 2). Los subanalizadores heredan la clase."""

    def error(self, message: str):
        emitir({"ok": False, "tipo": "ArgumentoNoValido", "error": message})
        raise SystemExit(2)


def construir() -> argparse.ArgumentParser:
    ap = Analizador(prog="lab.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preflight").set_defaults(func=cmd_preflight)
    p = sub.add_parser("lock-tomar")
    p.add_argument("--dueno", choices=DUENOS_VENTANA, required=True)
    p.set_defaults(func=cmd_lock_tomar)
    p = sub.add_parser("lock-soltar")
    p.add_argument("--dueno", choices=DUENOS_VENTANA, required=True)
    p.set_defaults(func=cmd_lock_soltar)

    p = sub.add_parser("turno")
    p.add_argument("--ahora", help="fecha ISO 8601 con zona, solo para pruebas")
    p.add_argument("--marcar", action="store_true", help="anota este turno como atendido si toca")
    p.set_defaults(func=cmd_turno)

    p = sub.add_parser("encargo-nuevo")
    p.add_argument("--cell", action="append", required=True)
    p.add_argument("--family", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--do-not-use", action="append")
    p.add_argument("--formato", required=True, help="JSON, p. ej. '{\"nativo\":\"feed_single_image\",\"ancho\":1080,\"alto\":1350}'")
    p.add_argument("--prompt-file", required=True)
    p.add_argument("--restriccion", action="append")
    p.add_argument("--variantes", type=int, default=1)
    p.set_defaults(func=cmd_encargo_nuevo)
    sub.add_parser("encargos").set_defaults(func=cmd_encargos)
    p = sub.add_parser("encargo-revisar")
    p.add_argument("--encargo", required=True)
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--aprobado", action="store_true")
    grupo.add_argument("--rechazado", dest="aprobado", action="store_false")
    p.add_argument("--motivo", required=True)
    p.add_argument("--correccion")
    p.set_defaults(func=cmd_encargo_revisar)
    p = sub.add_parser("encargo-usado")
    p.add_argument("--encargo", required=True)
    p.add_argument("--run", required=True)
    p.set_defaults(func=cmd_encargo_usado)
    p = sub.add_parser("seleccionar")
    p.add_argument("--max", type=int, default=2)
    p.add_argument("--sin-telefono", action="store_true", help="descarta celdas android_native")
    p.set_defaults(func=cmd_seleccionar)

    p = sub.add_parser("render")
    p.add_argument("--encargo", required=True)
    p.add_argument("--variante", type=int, default=1)
    p.add_argument("--formato", choices=("feed", "story"), required=True)
    p.add_argument("--titular", required=True, help="tres líneas separadas por |")
    p.add_argument("--subtitulo", required=True)
    p.add_argument("--aviso", default="", help='p. ej. "PRESENTADORA FICTICIA"')
    p.add_argument("--panel-rgb", type=_rgb, default=(5, 39, 73))
    p.add_argument("--accent-rgb", type=_rgb, default=(176, 220, 236))
    p.add_argument("--salida", required=True, help="nombre de archivo .jpg/.jpeg/.png, sin ruta")
    p.set_defaults(func=cmd_render)
    p = sub.add_parser("tarjeta")
    p.add_argument("--familia", required=True)
    p.add_argument("--cita", required=True)
    p.add_argument("--autor", required=True)
    p.add_argument("--salida", required=True, help="nombre de archivo .png, sin ruta")
    p.add_argument("--variante", choices=("cream", "gold"), default="cream")
    p.set_defaults(func=cmd_tarjeta)

    p = sub.add_parser("codex-tomar")
    p.add_argument("--owner", choices=encargos.DUENOS_GENERACION, required=True)
    p.add_argument("--max", type=int, default=2)
    p.set_defaults(func=cmd_codex_tomar)
    p = sub.add_parser("codex-generado")
    p.add_argument("--encargo", required=True)
    p.add_argument("--owner", choices=encargos.DUENOS_GENERACION, required=True)
    p.add_argument("--imagen", action="append", required=True)
    p.set_defaults(func=cmd_codex_generado)
    p = sub.add_parser("codex-fallo")
    p.add_argument("--encargo", required=True)
    p.add_argument("--owner", choices=encargos.DUENOS_GENERACION, required=True)
    p.add_argument("--nota", required=True)
    p.set_defaults(func=cmd_codex_fallo)
    p = sub.add_parser("generar")
    p.add_argument("--encargo", required=True)
    p.add_argument("--timeout", type=int, default=TIMEOUT_CODEX_S)
    p.set_defaults(func=cmd_generar)

    p = sub.add_parser("manifiesto-api")
    p.add_argument("--run-group", required=True)
    p.add_argument("--asset", required=True)
    p.add_argument("--caption", action="append", required=True, help="plataforma=ruta_del_pie")
    p.add_argument("--family")
    p.set_defaults(func=cmd_manifiesto_api)
    p = sub.add_parser("manifiesto-verificacion")
    p.add_argument("--run-group", required=True)
    p.add_argument("--post", action="append", required=True, help="plataforma=post_id")
    p.set_defaults(func=cmd_manifiesto_verificacion)

    p = sub.add_parser("telefono-subir")
    p.add_argument("--local", required=True, help="imagen bajo experiments/media-lab/ (.png, .jpg o .jpeg)")
    p.set_defaults(func=cmd_telefono_subir)
    for nombre, func in (("telefono-captura", cmd_telefono_captura), ("telefono-atras", cmd_telefono_atras)):
        p = sub.add_parser(nombre)
        p.add_argument("--run", required=True)
        p.add_argument("--nombre", required=True)
        p.set_defaults(func=func)
    p = sub.add_parser("ig")
    p.add_argument("paso", choices=("abrir", "recorte", "editor", "audio", "detalles", "pie", "compartir"))
    p.add_argument("--run", required=True)
    p.add_argument("--pie", help="archivo del pie (pie, compartir)")
    p.add_argument("--subido-en", help="subido_en que devolvió telefono-subir (abrir)")
    p.add_argument("--tema", help="tema que devolvió ig audio (compartir)")
    p.add_argument("--publicaciones-antes", type=int, help="publicaciones_antes que devolvió ig abrir (compartir)")
    p.add_argument("--produccion-cercana", action="store_true",
                   help="preflight trajo espera: un confirmado baja a confirmado_sin_conteo (compartir)")
    p.set_defaults(func=cmd_ig)
    return ap


def main() -> int:
    a = construir().parse_args()
    try:
        encargo_id = getattr(a, "encargo", None)
        if encargo_id is not None:
            _exigir(bool(encargos._ID.fullmatch(encargo_id)), f"--encargo no válido: {encargo_id!r}")
        for campo in ("run", "nombre"):
            valor = getattr(a, campo, None)
            if valor is not None:
                _exigir(bool(_NOMBRE.fullmatch(valor)),
                        f"--{campo} solo admite letras, dígitos, punto, guion y guion bajo: {valor!r}")
        return a.func(a)
    except (encargos.EncargoError, manifiesto.ManifiestoError, OSError, ValueError, KeyError) as e:
        emitir({"ok": False, "tipo": type(e).__name__, "error": str(e)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
