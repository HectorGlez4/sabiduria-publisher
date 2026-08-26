#!/usr/bin/env python3
"""
Valida content/drafts/ contra el contrato real del repo.

    python3 scripts/validar_borradores.py            # todos
    python3 scripts/validar_borradores.py --nuevos   # solo lo no comiteado

Existe porque el paso de validación no puede ser el propio prompt. Una rutina que
se comprueba a sí misma informa de lo que cree haber hecho, no de lo que hizo: los
borradores migrados de Cowork venían con `core.subject` desplazado a la raíz y sin
`core.quote`, y el informe de aquella ejecución decía que todo estaba correcto.

Comprueba tres capas, de fuera adentro:

1. **El esquema** (`content/schema.json`), tal cual.
2. **El contrato de la carpeta**: status draft, sin publish_at ni results, id igual
   al nombre del archivo, y sobre todo que el id NO exista ya en queue/ ni en
   published/ — esos ids son la clave del historial y sobrescribir uno borra una
   publicación real.
3. **Lo que el repo va a hacer con la pieza**: el mismo `preflight_separado` que
   usa src/publish.py, más un renderizado de prueba de la tarjeta. El preflight
   solo no basta: una pieza de pilar `cita` sin `core.quote` lo pasaba y reventaba
   luego con KeyError a mitad del render.

Sale con código 1 si algo falla, para que una rutina o un workflow puedan abortar.
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import publish, variants  # noqa: E402

# Una fecha lejana y libre: el preflight necesita un instante para medir cadencia,
# pero aquí no se está programando nada. La fecha real se asigna al encolar.
INSTANTE_DE_PRUEBA = "2099-01-01T19:00:00Z"


def ids_ocupados() -> set[str]:
    return {p.stem for d in ("published", "queue")
            for p in (ROOT / "content" / d).glob("*.json")}


def sin_comitear() -> set[str]:
    salida = subprocess.run(["git", "status", "--porcelain", "--", "content/drafts"],
                            cwd=ROOT, capture_output=True, text=True).stdout
    return {pathlib.Path(l[3:].strip().strip('"')).stem
            for l in salida.splitlines() if l.strip().endswith(".json")}


def revisar(ruta: pathlib.Path, ocupados: set[str], historial: list[dict]) -> list[str]:
    fallos: list[str] = []
    try:
        u = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSON ilegible: {e}"]

    try:
        from jsonschema import Draft7Validator
        esquema = json.loads((ROOT / "content" / "schema.json").read_text(encoding="utf-8"))
        for e in Draft7Validator(esquema).iter_errors(u):
            campo = ".".join(map(str, e.path)) or "(raíz)"
            fallos.append(f"esquema · {campo}: {e.message}")
    except ImportError:
        fallos.append("aviso: falta jsonschema, no se validó el esquema")

    if u.get("status") != "draft":
        fallos.append("status debe ser 'draft'")
    for k in ("publish_at", "results"):
        if k in u:
            fallos.append(f"no debe traer '{k}': la fecha se asigna al encolar")
    if u.get("id") != ruta.stem:
        fallos.append(f"el id '{u.get('id')}' no coincide con el archivo '{ruta.stem}'")
    if ruta.stem in ocupados:
        fallos.append("el id YA EXISTE en queue/ o published/: sobrescribiría historial")
    if not (u.get("core") or {}).get("subject"):
        fallos.append("sin core.subject: la regla de no repetir en 90 días no lo vería")

    permanentes, _ = variants.preflight_separado(
        dict(u, publish_at=INSTANTE_DE_PRUEBA), historial, None)
    # La alternancia y la cadencia dependen de CUÁNDO se publique, y eso aquí no
    # está decidido. Se comprueban al encolar, no ahora.
    fallos += [p for p in permanentes
               if "variante" not in p and "minimo son" not in p and "maximo es" not in p]

    try:
        publish.render_card(dict(u, publish_at=INSTANTE_DE_PRUEBA))
    except Exception as e:
        fallos.append(f"no renderiza la tarjeta: {type(e).__name__}: {e}")

    return fallos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nuevos", action="store_true",
                    help="solo los borradores sin comitear")
    a = ap.parse_args()

    rutas = sorted(pathlib.Path(p) for p in glob.glob(str(ROOT / "content/drafts/*.json")))
    if a.nuevos:
        nuevos = sin_comitear()
        rutas = [r for r in rutas if r.stem in nuevos]
    if not rutas:
        print("No hay borradores que revisar.")
        return 0

    ocupados = ids_ocupados()
    historial = [json.loads(p.read_text(encoding="utf-8"))
                 for p in (ROOT / "content" / "published").glob("*.json")]

    malos = 0
    for r in rutas:
        fallos = revisar(r, ocupados, historial)
        if fallos:
            malos += 1
            print(f"✗ {r.stem}")
            for f in fallos:
                print(f"    {f}")
        else:
            print(f"✓ {r.stem}")

    print(f"\n{len(rutas) - malos}/{len(rutas)} válidos")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
