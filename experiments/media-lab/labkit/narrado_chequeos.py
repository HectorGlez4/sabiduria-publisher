"""
Chequeos de un reel narrado ya renderizado: composición, audio y viaje de ida y vuelta de la voz.

`chequeo_hyperframes` corre `hyperframes check` sobre el proyecto y devuelve los problemas que
bloquean; `audio_ok` mide el mp4 con ffmpeg; `transcribir` pasa la voz por Whisper y `comparar` la
contrasta con el guion. Un chequeo que corrió y encontró problemas devuelve una lista; que la
herramienta no corra o no termine lanza `ChequeoFallido`.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from .narrado_pronuncia import numero_en_palabras

LIMITE_CHECK = 300       # s máximos para `hyperframes check`
LIMITE_TRANSCRIBE = 600  # s máximos para `hyperframes transcribe`
LIMITE_HERRAMIENTA = 120  # s máximos para ffmpeg y ffprobe
VERSION = "hyperframes@0.9.70"
AVISOS_QUE_BLOQUEAN = ("outside_safe_zone", "text_below_floor")
SECCIONES_CHECK = ("lint", "runtime", "layout", "motion", "contrast", "craft", "audio")
DURACION_MIN, DURACION_MAX = 25.0, 40.0
SILENCIO_MAX = 1.2
LUFS_MIN, LUFS_MAX = -17.0, -15.0
PICO_MAX = -1.0


class ChequeoFallido(Exception):
    """Una herramienta de chequeo no corrió, no terminó o devolvió algo ilegible."""

    def __init__(self, herramienta: str, motivo: str):
        self.herramienta = herramienta
        self.motivo = motivo
        super().__init__(f"{herramienta}: {motivo}")


def _requiere(herramienta: str) -> str:
    ruta = shutil.which(herramienta)
    if not ruta:
        raise ChequeoFallido(herramienta, f"falta la herramienta «{herramienta}» en el PATH")
    return ruta


def _correr(cmd: list[str], herramienta: str, limite: float, **kw) -> subprocess.CompletedProcess:
    """`subprocess.run` con tope de tiempo: al agotarse lanza ChequeoFallido nombrando herramienta y límite."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=limite, **kw)
    except subprocess.TimeoutExpired:
        raise ChequeoFallido(herramienta, f"no terminó en {limite:g} s y se canceló") from None


def _entorno() -> dict:
    return dict(os.environ, DO_NOT_TRACK="1", HYPERFRAMES_SKIP_SKILLS="1")


# ---------------------------------------------------------------- comparar

_NUMERO = re.compile(r"(?<!\w)\d+(?!\w)")
_PUNTUACION = re.compile(r"[.,;:!?¿¡…]")


def _tokens(texto: str) -> list[str]:
    """Palabras normalizadas: cifras a palabras, minúsculas, sin tildes y solo letras."""
    texto = _NUMERO.sub(lambda m: " " + numero_en_palabras(int(m.group())) + " ", texto)
    texto = _PUNTUACION.sub(" ", texto)
    salida = []
    for palabra in texto.split():
        base = unicodedata.normalize("NFD", palabra.lower())
        limpia = "".join(c for c in base if c.isalpha() and not unicodedata.combining(c))
        if limpia:
            salida.append(limpia)
    return salida


def _contexto(palabras: list[str], desde: int, hasta: int, margen: int = 2) -> str:
    return " ".join(palabras[max(0, desde - margen):hasta + margen])


def comparar(guion_voz: list[str], transcrito: str, nombres: list[str] | None = None) -> str | None:
    """`None` si lo que dijo la voz es el guion; si no, un mensaje con unas cinco palabras de contexto.

    Se normalizan los dos lados: cifras a palabras (`numero_en_palabras`), minúsculas, sin tildes y sin
    nada que no sea letra, de modo que la división de palabras («por qué»/«porqué»), la puntuación y las
    cifras no cuentan. Todo lo demás debe coincidir exacto.

    `nombres` son nombres propios del guion que un reconocedor puede escribir distinto («Nietzsche»
    como «Niche», «Frankl» como «Franco»). Cada palabra de esos nombres se quita del guion y, en su
    lugar, la transcripción puede traer cualquier palabra, una sola. Una palabra ordinaria que falta o
    sobra sigue siendo divergencia aunque se pasen nombres.
    """
    comodines = {t for n in (nombres or []) for t in _tokens(n)}
    esperado = _tokens(" ".join(guion_voz))
    dicho = _tokens(transcrito)
    # partes: ("texto", [palabras]) o ("nombre", [palabra])
    partes: list[tuple[str, list[str]]] = []
    for palabra in esperado:
        clase = "nombre" if palabra in comodines else "texto"
        if clase == "texto" and partes and partes[-1][0] == "texto":
            partes[-1][1].append(palabra)
        else:
            partes.append((clase, [palabra]))

    i = 0           # palabra de la transcripción por consumir
    pos_guion = 0   # palabra del guion por la que vamos
    for clase, palabras in partes:
        if clase == "nombre":
            if i >= len(dicho):
                return (f"la voz se quedó sin decir «{palabras[0]}» "
                        f"(guion: «…{_contexto(esperado, pos_guion, pos_guion + 1)}…»)")
            i += 1
            pos_guion += 1
            continue
        objetivo = "".join(palabras)
        acumulado, j, inicios = "", i, []
        while len(acumulado) < len(objetivo) and j < len(dicho):
            inicios.append(len(acumulado))
            acumulado += dicho[j]
            j += 1
        if acumulado != objetivo:
            k = 0
            while k < min(len(acumulado), len(objetivo)) and acumulado[k] == objetivo[k]:
                k += 1
            offset = 0
            for n, p in enumerate(palabras):  # palabra del guion donde empieza la divergencia
                if k < offset + len(p):
                    idx = n
                    break
                offset += len(p)
            else:
                idx = len(palabras) - 1
            tok = next((t for t, ini in enumerate(inicios) if ini <= k), len(inicios) - 1) if inicios else 0
            tok = i + max(tok, 0)
            if k >= len(acumulado):
                dijo = "(nada más)"
            else:
                dijo = f"«…{_contexto(dicho, tok, tok + 1)}…»"
            return (f"el guion dice «…{_contexto(esperado, pos_guion + idx, pos_guion + idx + 1)}…» "
                    f"y la voz dijo {dijo}")
        i = j
        pos_guion += len(palabras)
    if i < len(dicho):
        return f"la voz dijo de más: «{' '.join(dicho[i:i + 5])}…» (tras «{_contexto(esperado, len(esperado) - 3, len(esperado), 0)}»)"
    return None


# ---------------------------------------------------------------- audio

def _duracion(mp4: Path) -> float:
    r = _correr([_requiere("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(mp4)], "ffprobe", LIMITE_HERRAMIENTA)
    try:
        if r.returncode != 0:
            raise ValueError
        return float(r.stdout.strip())
    except ValueError:
        raise ChequeoFallido("ffprobe", f"no pudo medir {Path(mp4).name} (código {r.returncode}): "
                                        f"{(r.stderr.strip() or r.stdout.strip() or 'sin salida')[:300]}") from None


def silencios(mp4: Path) -> list[tuple[float, float]]:
    """Silencios (inicio, fin) con `silencedetect=noise=-40dB:d=0.3`; uno sin `silence_end` llega al final del archivo."""
    r = _correr([_requiere("ffmpeg"), "-hide_banner", "-nostats", "-i", str(mp4), "-vn", "-af",
                 "silencedetect=noise=-40dB:d=0.3", "-f", "null", "-"], "ffmpeg (silencedetect)",
                LIMITE_HERRAMIENTA)
    if r.returncode != 0:
        raise ChequeoFallido("ffmpeg (silencedetect)",
                             f"código {r.returncode}: {r.stderr.strip()[-300:]}")
    inicios = [max(float(x), 0.0) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    fines = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]
    if len(fines) < len(inicios):
        fines.append(max(_duracion(mp4), inicios[len(fines)]))
    return list(zip(inicios, fines))


def medidas(mp4: Path) -> dict:
    """`{"duracion", "lufs", "pico"}`: duración por ffprobe; sonoridad integrada y pico real por `loudnorm`.
    Un valor no finito (audio mudo: -inf) lanza ChequeoFallido."""
    duracion = _duracion(mp4)
    r = _correr([_requiere("ffmpeg"), "-hide_banner", "-nostats", "-i", str(mp4), "-vn", "-af",
                 "loudnorm=print_format=json", "-f", "null", "-"], "ffmpeg (loudnorm)", LIMITE_HERRAMIENTA)
    bloques = re.findall(r"\{[^{}]*\}", r.stderr)
    try:
        datos = json.loads(bloques[-1])
        m = {"duracion": duracion, "lufs": float(datos["input_i"]), "pico": float(datos["input_tp"])}
    except (IndexError, KeyError, ValueError):
        raise ChequeoFallido("ffmpeg (loudnorm)",
                             f"no devolvió las medidas (código {r.returncode}): {r.stderr.strip()[-300:]}") from None
    malas = [k for k, v in m.items() if not math.isfinite(v)]
    if malas:
        raise ChequeoFallido("ffmpeg (loudnorm)", f"medidas no finitas {malas}: ¿audio mudo?")
    return m


def audio_ok(mp4: Path, fin_narracion: float) -> list[str]:
    """Problemas de audio: duración fuera de 25–40 s, silencio de más de 1,2 s que empiece antes de `fin_narracion` (aunque acabe después),
    sonoridad fuera de −17…−15 LUFS o pico por encima de −1,0 dB. Lista vacía si todo está bien."""
    problemas = []
    m = medidas(mp4)
    if not DURACION_MIN <= m["duracion"] <= DURACION_MAX:
        problemas.append(f"duración {m['duracion']:.1f} s fuera de {DURACION_MIN:g}–{DURACION_MAX:g} s")
    for inicio, fin in silencios(mp4):
        # la cola natural empieza en `fin_narracion`; todo silencio largo que empieza antes es un hueco
        if fin - inicio > SILENCIO_MAX and inicio < fin_narracion - 0.05:
            problemas.append(f"silencio de {fin - inicio:.1f} s entre {inicio:.1f} s y {fin:.1f} s "
                             f"(máximo {SILENCIO_MAX:g} s)")
    if not LUFS_MIN <= m["lufs"] <= LUFS_MAX:
        problemas.append(f"sonoridad {m['lufs']:.1f} LUFS fuera de {LUFS_MIN:g}…{LUFS_MAX:g}")
    if m["pico"] > PICO_MAX:
        problemas.append(f"pico {m['pico']:.1f} dB por encima de {PICO_MAX:g} dB")
    return problemas


# ---------------------------------------------------------------- hyperframes

SECCIONES_ACTIVAS = ("contrast", "craft")  # las que la corrida real de la espiga tenía activadas


def problemas_de_check(informe: dict, codigo_salida: int = 0) -> list[str]:
    """Errores y avisos que bloquean (`outside_safe_zone`, `text_below_floor`) de un informe de `check --json`.

    Un informe en el que el chequeo no pudo correr lanza ChequeoFallido: navegador omitido, informe
    truncado, sin muestras de maquetación, una sección ausente o con `findings` mal formado,
    `contrast`/`craft` desactivados, un `errorCount` mayor que los errores leídos, o la herramienta
    con código de salida distinto de cero sin ningún error en el informe."""
    def falla(motivo: str):
        return ChequeoFallido("hyperframes check", motivo)

    if not isinstance(informe, dict):
        raise falla("el informe no es un objeto JSON")
    if informe.get("browserSkipped"):
        raise falla("el navegador se omitió: la maquetación no se comprobó")
    problemas = []
    total_errores = 0
    for seccion in SECCIONES_CHECK:
        datos = informe.get(seccion)
        if not isinstance(datos, dict):
            raise falla(f"falta la sección «{seccion}» del informe")
        hallazgos = datos.get("findings")
        if not isinstance(hallazgos, list) or not all(isinstance(h, dict) for h in hallazgos):
            raise falla(f"la sección «{seccion}» trae `findings` mal formado")
        if seccion in SECCIONES_ACTIVAS and datos.get("enabled") is not True:
            raise falla(f"la sección «{seccion}» está desactivada")
        if seccion == "layout":
            if datos.get("truncated"):
                raise falla("el informe de «layout» está truncado")
            if not isinstance(datos.get("samples"), list) or not datos["samples"]:
                raise falla("«layout» no tomó ninguna muestra")
        errores = sum(1 for h in hallazgos if h.get("severity") == "error")
        total_errores += errores
        contados = datos.get("errorCount", 0)
        if isinstance(contados, int) and contados > errores:
            raise falla(f"«{seccion}» declara {contados} error(es) y solo se leyeron {errores}")
        for h in hallazgos:
            codigo = h.get("code", "?")
            if h.get("severity") == "error" or (h.get("severity") == "warning" and codigo in AVISOS_QUE_BLOQUEAN):
                cuando = f" t={h['time']:g}s" if isinstance(h.get("time"), (int, float)) else ""
                donde = f" {h['selector']}" if h.get("selector") else ""
                texto = f" «{h['text']}»" if h.get("text") else ""
                problemas.append(f"{seccion}: {codigo}{cuando}{donde}{texto} — {h.get('message', '')}")
    if codigo_salida != 0 and total_errores == 0:
        raise falla(f"terminó con código {codigo_salida} pero el informe no trae ningún error que lo explique")
    return problemas


def chequeo_hyperframes(proyecto: Path) -> list[str]:
    """Corre `hyperframes check` en el proyecto; devuelve sus errores y los avisos de zona segura y de
    texto bajo el mínimo. `timeline_track_too_dense` y `nested_structure_needs_subcomposition` se ignoran.
    Si el chequeo no corrió de verdad lanza ChequeoFallido (ver `problemas_de_check`)."""
    r = _correr([_requiere("npx"), "--yes", VERSION, "check", "--no-cache", "--json"],
                "hyperframes check", LIMITE_CHECK, cwd=str(proyecto), env=_entorno())
    try:
        informe = json.loads(r.stdout)
    except ValueError:
        ultima = (r.stderr.strip().splitlines() or [r.stdout.strip()[:200] or "sin salida"])[-1]
        raise ChequeoFallido("hyperframes check",
                             f"código {r.returncode} y sin informe JSON legible: {ultima[:300]}") from None
    return problemas_de_check(informe, r.returncode)


def palabras_de_transcripcion(crudo: list) -> dict:
    """De la transcripción de Whisper (`[{"text","start","end"}]`) a `{"texto", "palabras"}`."""
    palabras = [{"palabra": str(p["text"]), "inicio": float(p["start"])} for p in crudo]
    return {"texto": " ".join(p["palabra"] for p in palabras), "palabras": palabras}


def transcribir(audio: Path) -> dict:
    """Transcribe `audio` con Whisper `small` en español: `{"texto", "palabras": [{"palabra", "inicio"}]}`."""
    with tempfile.TemporaryDirectory() as d:
        r = _correr([_requiere("npx"), "--yes", VERSION, "transcribe", str(Path(audio).resolve()),
                     "-d", d, "--model", "small", "--language", "es", "--json"],
                    "hyperframes transcribe", LIMITE_TRANSCRIBE, env=_entorno())
        destino = Path(d) / "transcript.json"
        if r.returncode != 0 or not destino.exists():
            ultima = (r.stderr.strip().splitlines() or r.stdout.strip().splitlines() or ["sin salida"])[-1]
            raise ChequeoFallido("hyperframes transcribe", f"código {r.returncode}: {ultima[:300]}")
        try:
            crudo = json.loads(destino.read_text(encoding="utf-8"))
            resultado = palabras_de_transcripcion(crudo)
        except (ValueError, KeyError, TypeError):
            raise ChequeoFallido("hyperframes transcribe", "transcript.json ilegible") from None
    if not resultado["palabras"]:
        raise ChequeoFallido("hyperframes transcribe", "la transcripción no tiene palabras")
    return resultado
