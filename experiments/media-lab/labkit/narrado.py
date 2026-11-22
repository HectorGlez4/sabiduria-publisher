"""
Qué piezas publicadas pueden ser un reel narrado, y registro de lo ya construido.

Solo cuentan las historias de «quién lo dijo de verdad» (`candidatas.json`), un reel por cita
distinta y nunca una ya hecha. `elegibles` es pura; `elegir` crea la carpeta del run y `registrar`
añade una línea a `registro.jsonl` sin reescribir las anteriores.

`construir` lleva un guion hasta el mp4 y deja `build/informe.json`; `revisar` anota el veredicto visual.
`apto_para_publicar` dice si ese build se puede publicar y `build/movil.json` guarda por dónde va su
publicación desde el móvil (`estado_movil`, `guardar_estado_movil`); construir otra vez lo borra, salvo si
dice que se compartió («compartido», «verificado», «incierto»): entonces `construir` se niega sin borrar nada.
Lo compartido queda además en `registro.jsonl` (`ya_compartida`), que sobrevive a cualquier build.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import narrado_chequeos as nc
from . import narrado_guion as ng
from . import narrado_proyecto as np_
from . import narrado_pronuncia as npr
from . import narrado_ritmo as nr
from . import narrado_voz as nv

RAIZ = Path(__file__).resolve().parents[3]


class SinCandidatas(Exception):
    """No queda ninguna pieza elegible."""


def _narrados(raiz: Path | None) -> Path:
    return (raiz or RAIZ) / "experiments" / "media-lab" / "narrados"


def clave_cita(texto: str) -> str:
    """Minúsculas, sin tildes y solo letras y dígitos: dos citas iguales dan la misma clave."""
    return ng.clave(texto)


def _clave_de(pieza: dict) -> str:
    return clave_cita(pieza.get("core", {}).get("quote", {}).get("text", ""))


def elegibles(publicadas: list[dict], candidatas: list[str], registro: list[dict]) -> list[dict]:
    """Piezas candidatas con cita verificada y cuerpo, una por cita, sin las ya registradas."""
    padre = {p["id"]: p["id"] for p in publicadas}

    def raiz_de(i: str) -> str:
        while padre.get(i, i) != i:
            i = padre[i]
        return i

    def unir(a: str, b: str) -> None:
        ra, rb = raiz_de(a), raiz_de(b)
        if ra != rb:
            padre[max(ra, rb)] = min(ra, rb)

    por_clave: dict[str, str] = {}
    for p in publicadas:
        origen = p.get("reemision_de")
        if origen in padre:
            unir(p["id"], origen)
        clave = _clave_de(p)
        if clave:
            if clave in por_clave:
                unir(p["id"], por_clave[clave])
            else:
                por_clave[clave] = p["id"]

    hechas = {e.get("cita") for e in registro}
    permitidas = set(candidatas)
    elegidas: dict[str, dict] = {}
    for p in sorted(publicadas, key=lambda x: x["id"]):
        core = p.get("core", {})
        if p["id"] not in permitidas or not core.get("body"):
            continue
        if not core.get("quote", {}).get("attribution_verified"):
            continue
        clave = _clave_de(p)
        if not clave or clave in hechas:
            continue
        elegidas.setdefault(raiz_de(p["id"]), p)
    return sorted(elegidas.values(), key=lambda x: x["id"])


def _leer_json(ruta: Path, defecto):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def _leer_registro(raiz: Path | None) -> list[dict]:
    ruta = _narrados(raiz) / "registro.jsonl"
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def es_falsa_atribucion(pieza_id: str, raiz: Path | None = None) -> bool:
    return pieza_id in _leer_json(_narrados(raiz) / "candidatas.json", [])


def elegir(ahora: datetime | None = None, raiz: Path | None = None) -> dict:
    """Primera pieza elegible por id; crea su carpeta de run. No toca el registro."""
    base = raiz or RAIZ
    publicadas = [json.loads(f.read_text(encoding="utf-8"))
                  for f in sorted((base / "content" / "published").glob("*.json"))]
    candidatas = _leer_json(_narrados(raiz) / "candidatas.json", [])
    lista = elegibles(publicadas, candidatas, _leer_registro(raiz))
    if not lista:
        raise SinCandidatas("no queda ninguna pieza elegible para un reel narrado")
    ahora = (ahora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    carpeta = _narrados(raiz) / lista[0]["id"]
    carpeta.mkdir(parents=True, exist_ok=True)
    return {"pieza": lista[0]["id"], "run": ahora.strftime("NARRADO-%Y%m%d-%H%M"),
            "carpeta": str(carpeta), "es_falsa_atribucion": True}


def _fsync_carpeta(carpeta: Path) -> None:
    """Lleva al disco la entrada de directorio (un archivo nuevo o reemplazado): sin esto, tras un corte de luz el
    nombre puede volver a apuntar al archivo viejo."""
    fd = os.open(carpeta, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def registrar(entrada: dict, raiz: Path | None = None) -> None:
    """Añade una línea a `registro.jsonl` y la deja en el disco (flush, fsync del archivo y de su carpeta) antes de
    volver; crea el archivo con la primera entrada. Nunca reescribe las anteriores."""
    ruta = _narrados(raiz) / "registro.jsonl"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    _fsync_carpeta(ruta.parent)


def clave_de_pieza(pieza_id: str, raiz: Path | None = None) -> str:
    """La clave de la cita de la pieza publicada (`content/published/<id>.json`), la misma con la que `elegibles`
    cruza el registro. ValueError si la pieza no está publicada o no tiene cita."""
    _exigir_id(pieza_id)
    ruta = (raiz or RAIZ) / "content" / "published" / f"{pieza_id}.json"
    if not ruta.is_file():
        raise ValueError(f"no existe la pieza publicada {ruta}: no se sabe qué cita es")
    clave = _clave_de(json.loads(ruta.read_text(encoding="utf-8")))
    if not clave:
        raise ValueError(f"{pieza_id} no tiene cita: no se puede cruzar con el registro")
    return clave


def registro_de(pieza_id: str, raiz: Path | None = None) -> list[dict]:
    """Las entradas de `registro.jsonl` de esta pieza, en orden: las de la clave de su cita O las de su id (si alguien
    edita la cita de una pieza ya compartida, el id la sigue bloqueando; si otra pieza tiene la misma cita, la clave).
    Solo lee el disco. ValueError si no se sabe la cita de la pieza."""
    clave = clave_de_pieza(pieza_id, raiz)
    return [e for e in _leer_registro(raiz)
            if isinstance(e, dict) and (e.get("cita") == clave or e.get("pieza") == pieza_id)]


def ya_compartida(pieza_id: str, raiz: Path | None = None) -> dict | None:
    """La entrada más reciente de `registro_de(pieza_id)` (la misma cita o la misma pieza), sea cual sea su `estado`;
    None si no hay ninguna. Solo lee el disco. ValueError si no se sabe la cita de la pieza."""
    coinciden = registro_de(pieza_id, raiz)
    return coinciden[-1] if coinciden else None


class RegistroOcupado(OSError):
    """Otro proceso tiene el cerrojo de `registro.jsonl`: nadie espera, se niega en el acto."""


@contextmanager
def cerrojo_registro(raiz: Path | None = None):
    """`fcntl.flock(LOCK_EX | LOCK_NB)` sobre `narrados/.registro.lock` (fuera de git) mientras dura el bloque: lo que
    se comprueba y se escribe dentro no se cruza con otro proceso. Si está tomado, RegistroOcupado sin esperar. Se
    suelta al salir del bloque, también con una excepción."""
    ruta = _narrados(raiz) / ".registro.lock"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise RegistroOcupado(f"otro proceso tiene el cerrojo del registro ({ruta}): no se espera") from e
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------- construir

@dataclass
class Herramientas:
    """Las herramientas que `construir` invoca; los valores por defecto son las reales."""
    sintetizar: Callable = nv.sintetizar
    mezclar: Callable = nv.mezclar
    transcribir: Callable = nc.transcribir
    chequeo: Callable = nc.chequeo_hyperframes
    render: Callable = nc.render
    fotogramas: Callable = nc.fotogramas
    audio_ok: Callable = nc.audio_ok


class _Parada(Exception):
    """Un paso falló: `fase` y `problemas` van al informe y la construcción se detiene."""

    def __init__(self, fase: str, problemas: list[str]):
        self.fase = fase
        self.problemas = problemas
        super().__init__(fase, problemas)


_ID_PIEZA = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")  # el mismo patrón que `lab.py` exige a los ids


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def _ruta_guion(pieza_id: str, raiz: Path | None) -> Path:
    return _narrados(raiz) / pieza_id / "guion.json"


def _guion_de(pieza_id: str, base: Path, raiz: Path | None, informe: dict) -> tuple[dict, dict]:
    """Guion y pieza publicada, con el guion ya validado; si no, `_Parada("guion", ...)`. Anota el
    sha256 del guion leído en el informe."""
    ruta = _ruta_guion(pieza_id, raiz)
    pieza_json = base / "content" / "published" / f"{pieza_id}.json"
    if not ruta.exists():
        raise _Parada("guion", [f"no existe {ruta}"])
    if not pieza_json.exists():
        raise _Parada("guion", [f"no existe la pieza publicada {pieza_json}"])
    informe["sha256_guion"] = _sha256(ruta)
    try:
        guion = ng.cargar(ruta)
    except ValueError as e:
        raise _Parada("guion", [str(e)]) from None
    pieza = json.loads(pieza_json.read_text(encoding="utf-8"))
    if guion.get("pieza") != pieza_id:
        raise _Parada("guion", [f"el guion dice pieza {guion.get('pieza')!r}, no {pieza_id!r}"])
    problemas = ng.validar(guion, pieza, es_falsa_atribucion(pieza_id, raiz))
    if problemas:
        raise _Parada("guion", problemas)
    return guion, pieza


def _tabla_de(tabla: dict | None, raiz: Path | None) -> dict:
    tabla = tabla if tabla is not None else _leer_json(_narrados(raiz) / "pronunciacion.json", {})
    problemas = npr.problemas_de_tabla(tabla)
    if problemas:
        raise _Parada("pronunciacion", [f"narrados/pronunciacion.json: {p}" for p in problemas])
    return tabla


def _exigir_nombres(guion: dict, tabla: dict, pieza: dict) -> None:
    faltan = npr.pendientes(guion, tabla, pieza)
    if faltan:
        raise _Parada("nombres", [
            f"nombres sin aprobar: {', '.join(faltan)}; un humano debe rellenar `aprobado_por` "
            f"en narrados/pronunciacion.json tras escuchar cómo los dice la voz"])


def _sintetizar_frases(guion: dict, tabla: dict, ctx: ng.Contexto, motor: str, salida: Path, h: Herramientas):
    carpeta = salida / "voces"
    wavs, duraciones = [], []
    for i, escena in enumerate(guion["escenas"]):
        wav = carpeta / f"{i + 1:02d}.wav"
        duraciones.append(h.sintetizar(npr.para_la_voz(escena["voz"], tabla, ctx), wav, motor))
        wavs.append(wav)
    return wavs, duraciones


def _palabras_de_la_cita(guion: dict, wavs: list[Path], tiempos: list[dict], h: Herramientas):
    """Inicio absoluto de cada palabra de la cita en pantalla, o `None` si Whisper no da las mismas."""
    i = next(k for k, e in enumerate(guion["escenas"]) if e["tipo"] == "cita")
    pantalla = guion["escenas"][i]["pantalla"]["texto"].split()
    dichas = h.transcribir(wavs[i])["palabras"]
    if len(dichas) != len(pantalla):
        return None
    return [round(tiempos[i]["inicio"] + p["inicio"], 3) for p in dichas]


def _ida_y_vuelta(guion: dict, tabla: dict, ctx: ng.Contexto, mp4: Path, h: Herramientas) -> list[str]:
    nombres = {n: [d for d in [npr.dicho(tabla, n)] if d]
               for e in guion["escenas"] for n in ng.nombres_propios(e["voz"], ctx)}
    mensaje = nc.comparar([e["voz"] for e in guion["escenas"]], h.transcribir(mp4)["texto"], nombres)
    return [mensaje] if mensaje else []


def _construir_pasos(pieza_id, guion, tabla, ctx, motor, salida, h, informe) -> None:
    """Los pasos tras la compuerta de nombres; el primero que falla lanza `_Parada`."""
    wavs, duraciones = _sintetizar_frases(guion, tabla, ctx, motor, salida, h)
    tiempos = nv.linea_de_tiempo([e["tipo"] for e in guion["escenas"]], duraciones)
    total = nv.duracion_total(tiempos)
    informe["duracion"] = total
    informe["avisos"] = nr.avisos(guion, tiempos)
    if not nc.DURACION_MIN <= total <= nc.DURACION_MAX:
        raise _Parada("tiempos", [f"la narración dura {total:.1f} s, fuera de "
                                  f"{nc.DURACION_MIN:g}–{nc.DURACION_MAX:g} s: alarga o acorta el guion"])
    voz = salida / "voz.wav"
    h.mezclar(wavs, [t["inicio"] for t in tiempos], total, voz)
    palabras = _palabras_de_la_cita(guion, wavs, tiempos, h)
    informe["cita_tiempos"] = "repartidos" if palabras is None else "transcritos"
    proyecto = np_.escribir(salida / "proyecto", guion, tiempos, total, palabras, voz)
    problemas = h.chequeo(proyecto)
    if problemas:
        raise _Parada("chequeo", problemas)
    bruto = h.render(proyecto)
    mp4 = salida / f"{pieza_id}.mp4"
    shutil.copyfile(bruto, mp4)
    informe["mp4"] = str(mp4)
    informe["sha256_mp4"] = _sha256(mp4)
    problemas = h.audio_ok(mp4, tiempos[-1]["fin"])
    if problemas:
        raise _Parada("audio", problemas)
    problemas = _ida_y_vuelta(guion, tabla, ctx, mp4, h)
    if problemas:
        raise _Parada("ida_y_vuelta", problemas)
    # cuando la frase acaba la escena ya mostró todo; sin pasar de donde empieza su fundido de salida
    medios = [round(min(t["fin"] + 0.2, t["escena_hasta"] - 0.4), 2) for t in tiempos]
    medios[-1] = round(tiempos[-1]["escena_hasta"] - 0.5, 2)  # la última escena entra firma y aviso tras la frase
    hoja = salida / "hoja.jpg"
    shutil.copyfile(h.fotogramas(proyecto, medios), hoja)
    informe["hoja"] = str(hoja)


def _exigir_id(pieza_id) -> None:
    if not isinstance(pieza_id, str) or not _ID_PIEZA.fullmatch(pieza_id) or ".." in pieza_id:
        raise ValueError(f"id de pieza no válido: {pieza_id!r} (letras, dígitos, punto, guion y guion bajo; "
                         f"sin «..» ni separadores)")


def _salida_segura(salida: Path | None, pieza_id: str, raiz: Path | None) -> Path:
    """La carpeta que `construir` puede vaciar: `build` dentro de la carpeta de la pieza, o una carpeta
    dentro de la temporal del sistema. Nunca una que contenga `guion.json` o `.git`. Si no, ValueError."""
    carpeta = (_narrados(raiz) / pieza_id).resolve()
    destino = Path(salida).resolve() if salida else carpeta / "build"
    temporal = Path(tempfile.gettempdir()).resolve()
    if not ((destino.name == "build" and carpeta in destino.parents) or temporal in destino.parents):
        raise ValueError(f"salida {destino} no admitida: debe ser una carpeta «build» dentro de {carpeta} "
                         f"o estar dentro de {temporal}")
    if destino.exists():
        if not destino.is_dir():
            raise ValueError(f"salida {destino} existe y no es una carpeta")
        if (destino / "guion.json").exists() or (destino / ".git").exists() \
                or any(destino.rglob("guion.json")) or any(destino.rglob(".git")):
            raise ValueError(f"salida {destino} contiene un guion.json o un .git: no se vacía")
    return destino


def _escribir_informe(salida: Path, informe: dict) -> None:
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")


def construir(pieza_id: str, *, motor: str = "kokoro", raiz: Path | None = None, tabla: dict | None = None,
              salida: Path | None = None, herramientas: Herramientas | None = None) -> dict:
    """Del guion al mp4, un paso tras otro. Deja `informe.json` en `salida` y lo devuelve.

    Excepción: si `salida/movil.json` dice «compartido», «verificado» o «incierto» (o no se lee), devuelve un informe
    `ok: false` en la fase «movil» SIN tocar la carpeta ni escribir el informe: es el rastro local de esa publicación.

    Antes de tocar el disco: id de pieza válido y `salida` admitida (`_salida_segura`); si no, ValueError.
    Orden: borrar el informe anterior → vaciar `salida` → guion válido → tabla de pronunciación sin
    entradas malas → nombres aprobados (antes de sintetizar nada) → voz por frase → línea de tiempo y
    duración de 25–40 s → mezcla → palabras de la cita → proyecto → chequeo → render → audio → ida y
    vuelta de la voz → fotogramas. El primer paso que falla detiene la corrida y deja sus problemas en
    el informe. Un informe `ok` lleva el sha256 del mp4 y del guion con que se hizo."""
    h = herramientas or Herramientas()
    base = raiz or RAIZ
    _exigir_id(pieza_id)
    salida = _salida_segura(salida, pieza_id, raiz)
    informe = {"ok": False, "pieza": pieza_id, "fase": "guion", "problemas": [], "mp4": None, "hoja": None,
               "duracion": None, "avisos": [], "cita_tiempos": None, "sha256_mp4": None, "sha256_guion": None,
               "construido_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "veredicto": None}
    movil = _movil_compartido(salida)
    if movil:  # antes de borrar nada: esa carpeta es el único rastro local de lo compartido
        informe.update(fase="movil", problemas=[movil])
        return informe
    (salida / "informe.json").unlink(missing_ok=True)  # primero: ningún informe ok viejo sobrevive a un fallo
    try:
        if salida.exists():
            shutil.rmtree(salida)  # nada de una corrida anterior (mp4, hoja) sobrevive a esta
        guion, pieza = _guion_de(pieza_id, base, raiz, informe)
        informe["fase"] = "pronunciacion"
        tabla = _tabla_de(tabla, raiz)
        informe["fase"] = "nombres"
        _exigir_nombres(guion, tabla, pieza)
        informe["fase"] = "construccion"
        _construir_pasos(pieza_id, guion, tabla, ng.contexto(guion, pieza), motor, salida, h, informe)
        if _sha256(_ruta_guion(pieza_id, raiz)) != informe["sha256_guion"]:
            raise _Parada("guion", ["guion.json cambió durante la construcción: vuelve a construir"])
        informe.update(ok=True, fase="completo")
    except _Parada as p:
        informe.update(fase=p.fase, problemas=p.problemas)
    except (nv.VozFallida, nc.ChequeoFallido, np_.NoCabe) as e:
        informe.update(fase=_fase_de(e, informe), problemas=[str(e)])
    except Exception as e:  # imprevisto: queda en el informe y se relanza para que `lab.py` falle
        informe.update(problemas=[f"{type(e).__name__}: {e}"])
        _escribir_informe(salida, informe)
        raise
    _escribir_informe(salida, informe)
    return informe


def _movil_compartido(salida: Path) -> str | None:
    """Por qué no se puede vaciar `salida`: su `movil.json` dice «compartido», «verificado» o «incierto», o no se
    puede leer. None si no hay `movil.json` o dice otro paso."""
    ruta = salida / "movil.json"
    if not ruta.exists():
        return None
    try:
        paso = json.loads(ruta.read_text(encoding="utf-8")).get("paso")
    except (OSError, ValueError, AttributeError) as e:
        return f"{ruta} no se puede leer ({e}): no se vacía la carpeta"
    if paso in PASOS_COMPARTIDOS:
        return (f"{ruta} dice «{paso}»: este build se compartió y su carpeta es el rastro de esa publicación; "
                "no se vuelve a construir encima")
    return None


def _fase_de(error: Exception, informe: dict) -> str:
    if isinstance(error, nv.VozFallida):
        return "mezcla" if error.frase == "(mezcla)" else "voz"
    if isinstance(error, np_.NoCabe):
        return "proyecto"
    herramienta = getattr(error, "herramienta", "")
    if "transcribe" in herramienta:
        return "ida_y_vuelta" if informe["mp4"] else "palabras"
    return {"hyperframes check": "chequeo", "hyperframes render": "render",
            "hyperframes snapshot": "fotogramas"}.get(herramienta, "audio")


def revisar(pieza_id: str, veredicto: str, raiz: Path | None = None) -> dict:
    """Anota el veredicto visual. Solo sobre un informe `ok` cuyo mp4 y guion siguen siendo los construidos
    (mismo sha256); si no, ValueError sin anotar nada. Cualquier veredicto que no sea PASS lo inutiliza."""
    _exigir_id(pieza_id)
    ruta = _narrados(raiz) / pieza_id / "build" / "informe.json"
    if not ruta.exists():
        raise ValueError(f"no hay {ruta}: construye antes de revisar")
    informe = json.loads(ruta.read_text(encoding="utf-8"))
    if informe.get("ok") is not True:
        raise ValueError(f"la construcción de {pieza_id} no está ok (fase {informe.get('fase')}): no se revisa")
    mp4 = Path(informe["mp4"]) if informe.get("mp4") else None
    if mp4 is None or not mp4.is_file():
        raise ValueError(f"no está el mp4 del informe ({informe.get('mp4')}): vuelve a construir")
    if _sha256(mp4) != informe.get("sha256_mp4"):
        raise ValueError(f"{mp4.name} no es el que se construyó (sha256 distinto): vuelve a construir")
    guion = _ruta_guion(pieza_id, raiz)
    if not guion.is_file() or _sha256(guion) != informe.get("sha256_guion"):
        raise ValueError("guion.json cambió desde la construcción (sha256 distinto): vuelve a construir")
    informe["veredicto"] = veredicto
    if veredicto != "PASS":
        informe["ok"] = False
    ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return informe


# ---------------------------------------------------------------- publicar desde el móvil

PASOS_MOVIL = ("subido", "abierto", "listo", "compartido", "verificado", "incierto", "descartado")
PASOS_COMPARTIDOS = ("compartido", "verificado", "incierto")


def ruta_build(pieza_id: str, raiz: Path | None = None) -> Path:
    _exigir_id(pieza_id)
    return _narrados(raiz) / pieza_id / "build"


def apto_para_publicar(pieza_id: str, raiz: Path | None = None) -> list[str]:
    """Lo que impide publicar el build de la pieza, leído del disco ahora mismo; vacío si se puede.

    Hace falta `informe.json` (un objeto) con `ok: true` y `veredicto: "PASS"`, el mp4 del informe (una ruta que
    lleva a un archivo directamente dentro del `build/` de la pieza) con el mismo sha256 que `sha256_mp4` y
    `guion.json` con el mismo que `sha256_guion`. Un informe malformado es un problema, no una excepción. Un id no
    válido es ValueError."""
    build = ruta_build(pieza_id, raiz)
    ruta = build / "informe.json"
    if not ruta.is_file():
        return [f"no hay {ruta}: construye y revisa antes de publicar"]
    try:
        informe = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"{ruta} no se puede leer: {e}"]
    if not isinstance(informe, dict):
        return [f"{ruta} no es un objeto JSON ({type(informe).__name__}): vuelve a construir"]
    problemas = []
    if informe.get("pieza") != pieza_id:
        problemas.append(f"el informe es de {informe.get('pieza')!r}, no de {pieza_id}")
    if informe.get("ok") is not True:
        problemas.append(f"la construcción no está ok (fase {informe.get('fase')})")
    if informe.get("veredicto") != "PASS":
        problemas.append(f"el veredicto visual es {informe.get('veredicto')!r}, no «PASS»: falta `revisar`")
    valor = informe.get("mp4")
    mp4 = Path(valor) if isinstance(valor, str) and valor else None
    if not informe.get("sha256_mp4"):
        problemas.append("el informe no trae sha256_mp4")
    elif valor is not None and not isinstance(valor, str):
        problemas.append(f"el mp4 del informe no es una ruta ({type(valor).__name__})")
    elif mp4 is None or not mp4.is_file():
        problemas.append(f"no está el mp4 del informe ({valor})")
    elif mp4.resolve().parent != build.resolve():
        problemas.append(f"el mp4 del informe ({valor}) no está directamente dentro de {build}")
    elif _sha256(mp4) != informe["sha256_mp4"]:
        problemas.append(f"{mp4.name} no es el que se construyó (sha256 distinto): vuelve a construir y revisar")
    guion = _ruta_guion(pieza_id, raiz)
    if not informe.get("sha256_guion"):
        problemas.append("el informe no trae sha256_guion")
    elif not guion.is_file() or _sha256(guion) != informe["sha256_guion"]:
        problemas.append("guion.json cambió desde la construcción (sha256 distinto): vuelve a construir y revisar")
    return problemas


def informe_de(pieza_id: str, raiz: Path | None = None) -> dict:
    """`build/informe.json` tal cual; ValueError si no está."""
    ruta = ruta_build(pieza_id, raiz) / "informe.json"
    if not ruta.is_file():
        raise ValueError(f"no hay {ruta}: construye y revisa antes de publicar")
    return json.loads(ruta.read_text(encoding="utf-8"))


def estado_movil(pieza_id: str, raiz: Path | None = None) -> dict:
    """`build/movil.json`, o {} si todavía no hay ninguno."""
    ruta = ruta_build(pieza_id, raiz) / "movil.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {}


def guardar_estado_movil(pieza_id: str, estado: dict, raiz: Path | None = None) -> None:
    """Escribe `build/movil.json` de una vez (temporal con fsync, reemplazo y fsync de la carpeta): nunca queda a
    medias y, al volver, está en el disco (un corte de luz no trae de vuelta el estado anterior). ValueError si
    `paso` no es uno de PASOS_MOVIL o si la pieza no tiene build."""
    if estado.get("paso") not in PASOS_MOVIL:
        raise ValueError(f"paso del móvil desconocido: {estado.get('paso')!r} (vale {', '.join(PASOS_MOVIL)})")
    build = ruta_build(pieza_id, raiz)
    if not build.is_dir():
        raise ValueError(f"no hay {build}: construye antes de publicar")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=build, prefix=".movil-", suffix=".tmp",
                                     delete=False) as f:
        temporal = Path(f.name)
        try:
            f.write(json.dumps(estado, ensure_ascii=False, indent=2) + "\n")
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            f.close()
            temporal.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporal, build / "movil.json")
    except BaseException:
        temporal.unlink(missing_ok=True)
        raise
    _fsync_carpeta(build)
