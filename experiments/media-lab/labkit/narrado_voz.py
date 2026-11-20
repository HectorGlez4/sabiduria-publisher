"""
Voz, línea de tiempo y mezcla de un reel narrado.

Cada frase se sintetiza en su propio archivo (`sintetizar`), se recorta de silencios y se mide. Con
las duraciones medidas, `linea_de_tiempo` coloca cada frase y cada escena, y `mezclar` junta todas las
frases en una sola pista de voz normalizada. Kokoro (`em_santa`) es el motor de producción; `say` es
solo para pruebas y como último recurso. Los motores externos se registran en `MOTORES`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

RAIZ_LAB = Path(__file__).resolve().parent.parent
PYTHON_VOZ = RAIZ_LAB / ".venv-voz" / "bin" / "python"

HUECO_FRASES = 0.45      # silencio entre frases
HUECO_ANTES_DE = 0.7     # silencio antes de una escena `cita` o `pregunta`
TIPOS_CON_PAUSA = ("cita", "pregunta")
ENTRADA = 0.6            # silencio antes de la primera frase
COLA = 2.3               # silencio tras la última frase
ENTRADA_ESCENA = 0.2     # la escena entra 0,2 s antes de su frase
MINIMO_AUDIO = 0.3       # una frase más corta que esto es un fallo del motor
LUFS = -16
PICO_REAL = -1.5

_RECORTE = ("silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB,areverse")


class VozFallida(Exception):
    """La síntesis de una frase no produjo un audio utilizable."""

    def __init__(self, frase: str, motivo: str):
        self.frase = frase
        self.motivo = motivo
        super().__init__(f"voz fallida en «{frase}»: {motivo}")


def _requiere(herramienta: str, frase: str = "") -> str:
    ruta = shutil.which(herramienta)
    if not ruta:
        raise VozFallida(frase, f"falta la herramienta «{herramienta}» en el PATH")
    return ruta


def _duracion(wav: Path) -> float:
    ffprobe = _requiere("ffprobe")
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(wav)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _motor_kokoro(frase: str, salida: Path) -> None:
    npx = _requiere("npx", frase)
    if not PYTHON_VOZ.exists():
        raise VozFallida(frase, f"falta el entorno de voz {PYTHON_VOZ}; sigue narrados/README.md")
    with tempfile.TemporaryDirectory() as d:
        txt = Path(d) / "frase.txt"
        txt.write_text(frase, encoding="utf-8")
        entorno = dict(os.environ, HYPERFRAMES_PYTHON=str(PYTHON_VOZ), DO_NOT_TRACK="1",
                       HYPERFRAMES_SKIP_SKILLS="1")
        r = subprocess.run([npx, "--yes", "hyperframes@0.9.70", "tts", str(txt), "-o", str(salida),
                            "-v", "em_santa", "-l", "es", "--speed", "0.95", "--json"],
                           capture_output=True, text=True, env=entorno)
    if r.returncode != 0:
        ultima = (r.stdout.strip().splitlines() or [r.stderr.strip()])[-1]
        raise VozFallida(frase, f"kokoro terminó con código {r.returncode}: {ultima[:300]}")


def _motor_say(frase: str, salida: Path) -> None:
    say = _requiere("say", frase)
    r = subprocess.run([say, "-v", "Paulina", "-r", "165", "-o", str(salida),
                        "--data-format=LEF32@22050", frase], capture_output=True, text=True)
    if r.returncode != 0:
        raise VozFallida(frase, f"say terminó con código {r.returncode}: {r.stderr.strip()[:300]}")


MOTORES: dict[str, Callable[[str, Path], None]] = {"kokoro": _motor_kokoro, "say": _motor_say}


def sintetizar(frase: str, salida: Path, motor: str = "kokoro") -> float:
    """Sintetiza `frase` en `salida` (WAV mono 48 kHz sin silencios en los extremos); devuelve su duración."""
    if motor not in MOTORES:
        raise VozFallida(frase, f"motor desconocido «{motor}»")
    ffmpeg = _requiere("ffmpeg", frase)
    _requiere("ffprobe", frase)
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        crudo = Path(d) / "crudo.wav"
        MOTORES[motor](frase, crudo)
        if not crudo.exists() or crudo.stat().st_size == 0:
            raise VozFallida(frase, "el motor no escribió ningún audio")
        r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(crudo), "-af", _RECORTE,
                            "-ar", "48000", "-ac", "1", str(salida)], capture_output=True, text=True)
    if r.returncode != 0 or not salida.exists():
        raise VozFallida(frase, f"ffmpeg no pudo recortar el audio: {r.stderr.strip()[:300]}")
    duracion = _duracion(salida)
    if duracion < MINIMO_AUDIO:
        raise VozFallida(frase, f"audio de {duracion:.2f} s, menos de {MINIMO_AUDIO} s")
    return duracion


def linea_de_tiempo(tipos: list[str], duraciones: list[float]) -> list[dict]:
    """Coloca frases y escenas. Cada item: inicio/fin de la frase (3 decimales) y escena_desde/hasta (2)."""
    if len(tipos) != len(duraciones):
        raise ValueError("tipos y duraciones deben tener la misma longitud")
    frases = []
    cursor = ENTRADA
    for tipo, dur in zip(tipos, duraciones):
        if frases:
            cursor += HUECO_ANTES_DE if tipo in TIPOS_CON_PAUSA else HUECO_FRASES
        frases.append((cursor, cursor + dur))
        cursor += dur
    total = cursor + COLA
    items = []
    for i, (inicio, fin) in enumerate(frases):
        desde = 0.0 if i == 0 else round(inicio - ENTRADA_ESCENA, 2)
        hasta = round(total, 2) if i == len(frases) - 1 else round(frases[i + 1][0] - ENTRADA_ESCENA, 2)
        items.append({"inicio": round(inicio, 3), "fin": round(fin, 3),
                      "escena_desde": desde, "escena_hasta": hasta})
    return items


def duracion_total(tiempos: list[dict]) -> float:
    """Duración del reel: fin de la última frase más la cola."""
    return round(tiempos[-1]["fin"] + COLA, 2)


def mezclar(wavs: list[Path], inicios: list[float], total: float, salida: Path) -> None:
    """Junta las frases en una sola pista de `total` s, normalizada a -16 LUFS / -1,5 dB de pico real."""
    if not wavs or len(wavs) != len(inicios):
        raise ValueError("wavs e inicios deben ser listas no vacías de la misma longitud")
    ffmpeg = _requiere("ffmpeg")
    entradas: list[str] = []
    retrasos = []
    for i, (wav, inicio) in enumerate(zip(wavs, inicios)):
        entradas += ["-i", str(wav)]
        ms = round(inicio * 1000)
        retrasos.append(f"[{i}:a]adelay={ms}:all=1[a{i}]")
    etiquetas = "".join(f"[a{i}]" for i in range(len(wavs)))
    filtro = (";".join(retrasos) + f";{etiquetas}amix=inputs={len(wavs)}:normalize=0,"
              f"apad=whole_dur={total},atrim=0:{total},loudnorm=I={LUFS}:TP={PICO_REAL}")
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", *entradas, "-filter_complex", filtro,
                        "-ar", "48000", str(salida)], capture_output=True, text=True)
    if r.returncode != 0 or not salida.exists():
        raise VozFallida("(mezcla)", f"ffmpeg no pudo mezclar: {r.stderr.strip()[:300]}")
