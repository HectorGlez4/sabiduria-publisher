"""
Qué piezas publicadas pueden ser un reel narrado, y registro de lo ya construido.

Solo cuentan las historias de «quién lo dijo de verdad» (`candidatas.json`), un reel por cita
distinta y nunca una ya hecha. `elegibles` es pura; `elegir` crea la carpeta del run y `registrar`
añade una línea a `registro.jsonl` sin reescribir las anteriores.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

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
