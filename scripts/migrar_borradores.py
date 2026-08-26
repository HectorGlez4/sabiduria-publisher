#!/usr/bin/env python3
"""
Migra los borradores del montaje anterior (Cowork, claude/borradores/*.json) al
contrato del repo (content/drafts/*.json).

Qué hace, en orden:
  1. Lee los borradores viejos.
  2. Descarta duplicados de tema, quedándose con el mejor verificado.
  3. Asigna franja por pilar y un id AAAA-MM-DD-franja libre, respetando los ids
     ya ocupados en content/published/ y content/queue/.
  4. Escribe solo las claves del contrato: sin copy por plataforma, sin tags,
     sin publish_at, sin results, status "draft".

Uso:
    python3 migrar_borradores.py --origen ./borradores-viejos --destino content/drafts \
        --desde 2026-09-02 [--repo .]

--repo se usa para leer los ids ocupados. Si no se pasa, solo respeta --desde.

Este script NO valida contra content/schema.json: eso lo hace el workflow.
Si el esquema real pide claves distintas, cambia MAPA_SALIDA y vuelve a correrlo;
es idempotente sobre el origen.
"""
import argparse
import glob
import json
import os
import pathlib
import re
import unicodedata
from datetime import date, timedelta

FRANJA_POR_PILAR = {
    "figura": "manana",
    "curiosidad": "manana",
    "arte-y-ciencia": "manana",
    "arte y ciencia": "manana",
    "cita": "tarde",
    "civilizacion": "noche",
    "civilización": "noche",
    "mitologia": "noche",
    "filosofia": "noche",
    "filosofía": "noche",
}

ORDEN_FRANJAS = ["manana", "tarde", "noche"]

# Claves que NO pasan al repo, y por qué.
DESCARTADAS = {
    "tags": "copy por plataforma: las etiquetas las deriva src/variants.py",
}


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


ARTICULOS = {"el", "la", "los", "las", "un", "una", "de", "del", "y"}


def clave_tema(borrador):
    """Huella del tema, para detectar duplicados entre borradores.

    Los dos duplicados reales tienen el sujeto redactado distinto —"Matilde
    Hidalgo de Procel (Ecuador, 1924)" y "Matilde Hidalgo (Ecuador)"— así que la
    huella se toma sobre las dos primeras palabras con contenido, saltando
    artículos y preposiciones iniciales.
    """
    sujeto = borrador.get("core", {}).get("subject", "")
    tokens = [t for t in slug(sujeto).split("-") if t]
    while tokens and tokens[0] in ARTICULOS:
        tokens.pop(0)
    return " ".join(tokens[:2])


def calidad(borrador):
    """Para elegir entre duplicados: más fuentes y más do_not_use gana."""
    return (len(borrador.get("sources", [])), len(borrador.get("do_not_use", [])))


def ids_ocupados(repo):
    if not repo:
        return set()
    ocupados = set()
    for sub in ("published", "queue"):
        for f in glob.glob(os.path.join(repo, "content", sub, "*.json")):
            ocupados.add(pathlib.Path(f).stem)
    return ocupados


def asignar_ids(por_franja, desde, ocupados):
    """Un id por franja y día, saltando los ocupados."""
    asignados = {}
    cursor = {f: desde for f in ORDEN_FRANJAS}
    for franja in ORDEN_FRANJAS:
        for b in por_franja.get(franja, []):
            d = cursor[franja]
            while f"{d.isoformat()}-{franja}" in ocupados:
                d += timedelta(days=1)
            nuevo = f"{d.isoformat()}-{franja}"
            asignados[id(b)] = nuevo
            ocupados.add(nuevo)
            cursor[franja] = d + timedelta(days=1)
    return asignados


def MAPA_SALIDA(borrador, nuevo_id):
    """Las claves que van al repo. Cambiar aquí si schema.json pide otra cosa."""
    salida = {
        "id": nuevo_id,
        "status": "draft",
        "pillar": borrador.get("pillar"),
        "core": {
            "hook": borrador["core"]["hook"],
            "body": borrador["core"]["body"],
            "question": borrador["core"]["question"],
        },
        "card": borrador.get("card"),
        "sources": borrador.get("sources", []),
        "do_not_use": borrador.get("do_not_use", []),
    }
    # subject se conserva como nota interna: es lo que permite detectar repeticiones
    # de tema dentro de 90 días sin releer el cuerpo entero.
    salida["_subject"] = borrador["core"].get("subject")
    return {k: v for k, v in salida.items() if v is not None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--origen", required=True)
    p.add_argument("--destino", required=True)
    p.add_argument("--desde", required=True, help="AAAA-MM-DD de la primera franja libre")
    p.add_argument("--repo", default=None)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    archivos = sorted(glob.glob(os.path.join(a.origen, "*.json")))
    if not archivos:
        raise SystemExit(f"No hay JSON en {a.origen}")

    # 1. Cargar y deduplicar
    mejores, descartes = {}, []
    for f in archivos:
        b = json.load(open(f, encoding="utf-8"))
        b["_origen"] = os.path.basename(f)
        k = clave_tema(b)
        if k in mejores:
            perdedor = min(mejores[k], b, key=calidad)
            ganador = max(mejores[k], b, key=calidad)
            descartes.append((perdedor["_origen"], ganador["_origen"]))
            mejores[k] = ganador
        else:
            mejores[k] = b

    # 2. Repartir por franja
    por_franja = {}
    sin_franja = []
    for b in mejores.values():
        franja = FRANJA_POR_PILAR.get((b.get("pillar") or "").strip().lower())
        if not franja:
            sin_franja.append(b["_origen"])
            continue
        por_franja.setdefault(franja, []).append(b)
    for franja in por_franja:
        por_franja[franja].sort(key=lambda b: b["_origen"])

    # 3. Ids
    desde = date.fromisoformat(a.desde)
    asignados = asignar_ids(por_franja, desde, ids_ocupados(a.repo))

    # 4. Escribir
    os.makedirs(a.destino, exist_ok=True)
    escritos = []
    for franja in ORDEN_FRANJAS:
        for b in por_franja.get(franja, []):
            nuevo_id = asignados[id(b)]
            salida = MAPA_SALIDA(b, nuevo_id)
            ruta = os.path.join(a.destino, f"{nuevo_id}.json")
            if not a.dry_run:
                with open(ruta, "w", encoding="utf-8") as fh:
                    json.dump(salida, fh, ensure_ascii=False, indent=2)
                    fh.write("\n")
            escritos.append((nuevo_id, b["_origen"], b.get("pillar"),
                             len(b.get("sources", []))))

    # Informe
    print(f"Origen: {len(archivos)} borradores")
    if descartes:
        print(f"\nDuplicados descartados ({len(descartes)}):")
        for perdedor, ganador in descartes:
            print(f"  - {perdedor}  (se conserva {ganador}, mejor verificado)")
    if sin_franja:
        print(f"\nSin franja asignable, revisar el pilar ({len(sin_franja)}):")
        for f in sin_franja:
            print(f"  - {f}")
    print(f"\nEscritos: {len(escritos)}")
    for nuevo_id, origen, pilar, n in escritos:
        print(f"  {nuevo_id}.json   <- {origen}   [{pilar}, {n} fuentes]")
    print(f"\nClaves no migradas: " +
          "; ".join(f"{k} ({v})" for k, v in DESCARTADAS.items()))


if __name__ == "__main__":
    main()
