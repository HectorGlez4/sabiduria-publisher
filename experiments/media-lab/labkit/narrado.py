"""
Qué piezas publicadas pueden ser un reel narrado, y registro de lo ya construido.

Solo cuentan las historias de «quién lo dijo de verdad» (`candidatas.json`), un reel por cita
distinta y nunca una ya hecha. `elegibles` es pura; `elegir` crea la carpeta del run y `registrar`
añade una línea a `registro.jsonl` sin reescribir las anteriores.

`construir` lleva un guion hasta el mp4 y deja `build/informe.json`; `revisar` anota el veredicto visual.
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import narrado_chequeos as nc
from . import narrado_guion as ng
from . import narrado_proyecto as np_
from . import narrado_pronuncia as npr
from . import narrado_voz as nv

RAIZ = Path(__file__).resolve().parents[3]


class SinCandidatas(Exception):
    """No queda ninguna pieza elegible."""


def _narrados(raiz: Path | None) -> Path:
    return (raiz or RAIZ) / "experiments" / "media-lab" / "narrados"


def clave_cita(texto: str) -> str:
    """Minúsculas, sin tildes y solo letras y dígitos: dos citas iguales dan la misma clave."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", sin_tildes)


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


def registrar(entrada: dict, raiz: Path | None = None) -> None:
    """Añade una línea a `registro.jsonl`; crea el archivo con la primera entrada."""
    ruta = _narrados(raiz) / "registro.jsonl"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


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


def _guion_de(pieza_id: str, base: Path, raiz: Path | None) -> tuple[dict, dict]:
    """Guion y pieza publicada, con el guion ya validado; si no, `_Parada("guion", ...)`."""
    ruta = _narrados(raiz) / pieza_id / "guion.json"
    pieza_json = base / "content" / "published" / f"{pieza_id}.json"
    if not ruta.exists():
        raise _Parada("guion", [f"no existe {ruta}"])
    if not pieza_json.exists():
        raise _Parada("guion", [f"no existe la pieza publicada {pieza_json}"])
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
    return tabla if tabla is not None else _leer_json(_narrados(raiz) / "pronunciacion.json", {})


def _exigir_nombres(guion: dict, tabla: dict) -> None:
    faltan = npr.pendientes(guion, tabla)
    if faltan:
        raise _Parada("nombres", [
            f"nombres sin aprobar: {', '.join(faltan)}; un humano debe rellenar `aprobado_por` "
            f"en narrados/pronunciacion.json tras escuchar cómo los dice la voz"])


def _sintetizar_frases(guion: dict, tabla: dict, motor: str, salida: Path, h: Herramientas):
    carpeta = salida / "voces"
    wavs, duraciones = [], []
    for i, escena in enumerate(guion["escenas"]):
        wav = carpeta / f"{i + 1:02d}.wav"
        duraciones.append(h.sintetizar(npr.para_la_voz(escena["voz"], tabla), wav, motor))
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


def _ida_y_vuelta(guion: dict, tabla: dict, mp4: Path, h: Herramientas) -> list[str]:
    nombres = sorted({n for e in guion["escenas"] for n in npr.nombres(e["voz"], tabla)})
    mensaje = nc.comparar([e["voz"] for e in guion["escenas"]], h.transcribir(mp4)["texto"], nombres)
    return [mensaje] if mensaje else []


def _construir_pasos(pieza_id, guion, tabla, motor, salida, h, informe) -> None:
    """Los pasos tras la compuerta de nombres; el primero que falla lanza `_Parada`."""
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)
    wavs, duraciones = _sintetizar_frases(guion, tabla, motor, salida, h)
    tiempos = nv.linea_de_tiempo([e["tipo"] for e in guion["escenas"]], duraciones)
    total = nv.duracion_total(tiempos)
    informe["duracion"] = total
    voz = salida / "voz.wav"
    h.mezclar(wavs, [t["inicio"] for t in tiempos], total, voz)
    palabras = _palabras_de_la_cita(guion, wavs, tiempos, h)
    proyecto = np_.escribir(salida / "proyecto", guion, tiempos, total, palabras, voz)
    problemas = h.chequeo(proyecto)
    if problemas:
        raise _Parada("chequeo", problemas)
    bruto = h.render(proyecto)
    mp4 = salida / f"{pieza_id}.mp4"
    shutil.copyfile(bruto, mp4)
    informe["mp4"] = str(mp4)
    problemas = h.audio_ok(mp4, tiempos[-1]["fin"])
    if problemas:
        raise _Parada("audio", problemas)
    problemas = _ida_y_vuelta(guion, tabla, mp4, h)
    if problemas:
        raise _Parada("ida_y_vuelta", problemas)
    # cuando la frase acaba la escena ya mostró todo; sin pasar de donde empieza su fundido de salida
    medios = [round(min(t["fin"] + 0.2, t["escena_hasta"] - 0.4), 2) for t in tiempos]
    hoja = salida / "hoja.jpg"
    shutil.copyfile(h.fotogramas(proyecto, medios), hoja)
    informe["hoja"] = str(hoja)


def _escribir_informe(salida: Path, informe: dict) -> None:
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")


def construir(pieza_id: str, *, motor: str = "kokoro", raiz: Path | None = None, tabla: dict | None = None,
              salida: Path | None = None, herramientas: Herramientas | None = None) -> dict:
    """Del guion al mp4, un paso tras otro. Siempre deja `informe.json` en `salida` y lo devuelve.

    Orden: guion válido → nombres aprobados (antes de sintetizar nada) → vaciar `salida` → voz por frase →
    línea de tiempo → mezcla → palabras de la cita → proyecto → chequeo → render → audio → ida y vuelta de
    la voz → fotogramas. El primer paso que falla detiene la corrida y deja sus problemas en el informe."""
    h = herramientas or Herramientas()
    base = raiz or RAIZ
    salida = Path(salida) if salida else _narrados(raiz) / pieza_id / "build"
    informe = {"ok": False, "pieza": pieza_id, "fase": "guion", "problemas": [], "mp4": None, "hoja": None,
               "duracion": None, "construido_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "veredicto": None}
    try:
        guion, _ = _guion_de(pieza_id, base, raiz)
        tabla = _tabla_de(tabla, raiz)
        informe["fase"] = "nombres"
        _exigir_nombres(guion, tabla)
        informe["fase"] = "construccion"
        _construir_pasos(pieza_id, guion, tabla, motor, salida, h, informe)
        informe.update(ok=True, fase="completo")
    except _Parada as p:
        informe.update(fase=p.fase, problemas=p.problemas)
    except (nv.VozFallida, nc.ChequeoFallido, np_.NoCabe) as e:
        informe.update(fase=_fase_de(e, informe), problemas=[str(e)])
    _escribir_informe(salida, informe)
    return informe


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
    """Anota el veredicto visual. Solo sobre un informe `ok`; cualquier veredicto que no sea PASS lo inutiliza."""
    ruta = _narrados(raiz) / pieza_id / "build" / "informe.json"
    if not ruta.exists():
        raise ValueError(f"no hay {ruta}: construye antes de revisar")
    informe = json.loads(ruta.read_text(encoding="utf-8"))
    if informe.get("ok") is not True:
        raise ValueError(f"la construcción de {pieza_id} no está ok (fase {informe.get('fase')}): no se revisa")
    informe["veredicto"] = veredicto
    if veredicto != "PASS":
        informe["ok"] = False
    ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return informe
