"""
Guardia de archivos alrededor de `lab.py generar`: qué tocó Codex fuera de lo permitido.

`estado_git` saca una foto (huella por ruta) de lo que git ve cambiado más lo ignorado
que importa; `cambios_ajenos` compara dos fotos y no toca el disco, así que es la parte
que cubren las pruebas con datos inventados.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path, PurePosixPath

# Siempre vigilados aunque git no los muestre: secretos, permisos de Claude, configuración
# de git y el cerrojo de ventana. Si faltan, su huella es «-».
FIJOS = (".env", ".claude/settings.local.json", ".claude/settings.json", ".git/config",
         "experiments/media-lab/.ventana.lock", "experiments/media-lab/.turno-hecho",
         "experiments/media-lab/.turno.lock")
# Finder los crea solo con abrir una carpeta: no dicen nada de Codex.
IGNORADOS = {".DS_Store"}


def _rutas_git(raiz: Path) -> list[str]:
    r = subprocess.run(["git", "status", "--porcelain", "-z", "-uall"], cwd=raiz, capture_output=True,
                       timeout=60, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"git status falló: {r.stderr.decode(errors='replace').strip()[:200]}")
    rutas: list[str] = []
    campos = r.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    i = 0
    while i < len(campos):
        registro = campos[i]
        i += 1
        if not registro:
            continue
        rutas.append(registro[3:])
        if registro[0] in "RC" or registro[1] in "RC":
            i += 1  # en -z, un renombrado o copia trae después la ruta de origen
    return rutas


def _archivos(carpeta: Path) -> list[Path]:
    """Archivos y enlaces bajo la carpeta, sin seguir enlaces a directorios."""
    if not carpeta.is_dir():
        return []
    return [p for p in carpeta.rglob("*") if p.is_symlink() or p.is_file()]


def _rutas_vigiladas(raiz: Path) -> list[str]:
    encontrados = list(raiz.glob("experiments/media-lab/.env*"))
    encontrados += _archivos(raiz / ".git" / "hooks")
    encontrados += raiz.glob("experiments/media-lab/**/__pycache__/*.pyc")
    encontrados += _archivos(raiz / "assets")
    return list(FIJOS) + [p.relative_to(raiz).as_posix() for p in encontrados]


def huella(ruta: Path) -> str:
    if ruta.is_symlink():
        return "enlace:" + os.readlink(ruta)
    if ruta.is_file():
        return hashlib.sha256(ruta.read_bytes()).hexdigest()
    return "-"


def estado_git(raiz: Path) -> dict[str, str]:
    """Huella de cada ruta con cambios según git status y de las vigiladas siempre."""
    rutas = _rutas_git(raiz) + _rutas_vigiladas(raiz)
    return {r: huella(raiz / r) for r in rutas if PurePosixPath(r).name not in IGNORADOS}


def cambios_ajenos(antes: dict[str, str], despues: dict[str, str], permitidas: set[str]) -> list[str]:
    """Rutas no permitidas cuya huella cambió, ordenadas.

    Se recorre la unión de claves: una ruta que estaba modificada y vuelve a HEAD desaparece
    de `git status` y también cuenta como cambio."""
    return sorted(r for r in antes.keys() | despues.keys()
                  if antes.get(r) != despues.get(r) and r not in permitidas)
