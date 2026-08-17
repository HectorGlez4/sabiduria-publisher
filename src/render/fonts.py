"""
Resolución de las fuentes de marca.

Las tarjetas van empaquetadas con sus fuentes (assets/fonts/) en lugar de
depender de lo que tenga instalado la máquina. El motivo es el principio que
sostiene el repo: la imagen es una función pura del JSON. Si la fuente la pone
el sistema operativo, deja de serlo — la misma pieza sale distinta en tu Mac y
en Actions, y nadie se entera hasta que está publicada.

Antes esto eran rutas absolutas al sandbox donde se redactó el repo
(/usr/share/fonts/truetype/google-fonts). Fuera de ahí, PIL levantaba
"OSError: cannot open resource", que no dice cuál es la fuente ni dónde la
buscó. Ese camino se conserva como último recurso, pero ya no es el primero.

Orden de búsqueda:
  1. SDB_FONT_DIR         para probar otra tipografía sin tocar el código
  2. assets/fonts/        las empaquetadas: el caso normal
  3. la ruta del sandbox  para que siga funcionando donde se escribió
"""
from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

LEGACY_DIR = "/usr/share/fonts/truetype/google-fonts"


def _dirs() -> list[pathlib.Path]:
    out = []
    env = os.environ.get("SDB_FONT_DIR")
    if env:
        out.append(pathlib.Path(env))
    out.append(ROOT / "assets" / "fonts")
    out.append(pathlib.Path(LEGACY_DIR))
    return out


def find(filename: str) -> str:
    """Ruta absoluta de la fuente, o un error que dice dónde se buscó."""
    tried = []
    for d in _dirs():
        p = d / filename
        tried.append(str(p))
        if p.is_file():
            return str(p)
    raise FileNotFoundError(
        f"no se encuentra la fuente {filename!r}. Buscada en:\n"
        + "".join(f"    {t}\n" for t in tried)
        + "  Las fuentes van empaquetadas en assets/fonts/. Si faltan, el repo\n"
        "  está incompleto: vuelve a clonarlo o define SDB_FONT_DIR."
    )


LORA = find("Lora-Variable.ttf")
LORA_IT = find("Lora-Italic-Variable.ttf")
POPPINS = find("Poppins-Medium.ttf")
POPPINS_LIGHT = find("Poppins-Light.ttf")
