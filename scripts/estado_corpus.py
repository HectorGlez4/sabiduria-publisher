#!/usr/bin/env python3
"""
Lo que hay que saber antes de investigar una pieza nueva.

    python3 scripts/estado_corpus.py

Imprime las franjas libres siguientes y todos los sujetos ya tratados, en
published/, queue/ y drafts/ a la vez.

Existe por una razón concreta: la rutina diaria necesitaba estos dos datos y se
los sacaba escribiendo un heredoc de Python distinto cada vez. Un comando
irrepetible pide permiso cada vez que corre, y una rutina que corre sin nadie
delante se queda congelada en ese diálogo — pasó, y estuvo doce minutos parada
sin dejar error, ni salida, ni commit. Un comando fijo se aprueba una sola vez.
"""
from __future__ import annotations

import collections
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARPETAS = ("published", "queue", "drafts")
FRANJAS = ("manana", "tarde", "noche")
# Cuántos ids se ofrecen y cuántas piezas caben por día.
#
# POR_DIA sube a 8 porque la cola consume 7 piezas nuevas diarias y la rutina
# producía 3: el banco se vaciaba a razón de cuatro al día. Ocho deja margen
# sobre el consumo en vez de ir siempre por detrás.
CUANTAS_LIBRES = 10
POR_DIA = 8


def main() -> int:
    unidades: dict[str, list[dict]] = {}
    ocupados: set[str] = set()
    for c in CARPETAS:
        unidades[c] = []
        for p in sorted((ROOT / "content" / c).glob("*.json")):
            ocupados.add(p.stem)
            try:
                unidades[c].append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass

    # Las franjas libres empiezan DESPUÉS de todo lo programado, no en los
    # huecos intermedios. Los días que el ritmo ya cargó tienen diez piezas
    # entre foto, reel e historia: meter ahí un borrador más no es llenar un
    # hueco, es amontonar. Se busca a partir del día siguiente al último id
    # fechado que exista en cualquiera de las tres carpetas.
    # Se busca después del último día CON CADENCIA REAL, no después del último
    # id que exista. Una pieza suelta aplazada semanas —por ejemplo una
    # reemisión apartada para no repetir contenido— no debe empujar el banco de
    # borradores un mes hacia delante. Un día cuenta como cadencia si tiene al
    # menos tres ids: es lo que hay cuando el día está de verdad programado.
    por_dia: collections.Counter[str] = collections.Counter(
        i[:10] for i in ocupados if i[:4].isdigit())
    densos = [d for d, n in por_dia.items() if n >= 3]
    dia = datetime.date.today() + datetime.timedelta(days=1)
    if densos:
        dia = max(dia, datetime.date.fromisoformat(max(densos)) + datetime.timedelta(days=1))
    # Tres franjas por día no bastan desde que el ritmo pide ocho piezas
    # diarias. Después de manana/tarde/noche se ofrecen ids `extraNN`, que el
    # esquema admite desde el 27 de agosto justamente para esto: originales por
    # encima de las tres del día. El orden importa — las franjas primero, porque
    # son las que llevan la intención editorial de la hora.
    libres: list[str] = []
    while len(libres) < CUANTAS_LIBRES:
        for f in FRANJAS:
            i = f"{dia}-{f}"
            if i not in ocupados:
                libres.append(i)
        for n in range(41, 41 + POR_DIA - len(FRANJAS)):
            i = f"{dia}-extra{n}"
            if i not in ocupados:
                libres.append(i)
        dia += datetime.timedelta(days=1)

    print("IDS LIBRES (toma los primeros, en orden):")
    for i in libres[:CUANTAS_LIBRES]:
        print(f"  {i}")

    print(f"\nIDS OCUPADOS: {len(ocupados)}. No reutilices ninguno: los de "
          f"published/ y queue/ son la clave del historial.")

    print("\nSUJETOS YA TRATADOS — no repitas ninguno, ni nada que comparta con "
          "ellos dos palabras significativas:")
    vistos = set()
    for c in CARPETAS:
        for u in unidades[c]:
            s = ((u.get("core") or {}).get("subject") or "").strip()
            if s and s.lower() not in vistos:
                vistos.add(s.lower())
                print(f"  [{u.get('pillar','?'):13}] {s}")

    print("\nÚLTIMA VARIANTE POR ORDEN DE PUBLICACIÓN (la nueva debe alternar):")
    reales = [u for u in unidades["published"] if u.get("publish_at")]
    reales.sort(key=lambda u: u["publish_at"])
    if reales:
        u = reales[-1]
        print(f"  {u['id']} → {(u.get('card') or {}).get('variant','?')}")
    else:
        print("  (sin historial)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
