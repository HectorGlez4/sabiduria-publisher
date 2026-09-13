#!/usr/bin/env python3
"""
Trae citas del corpus del sitio al banco de borradores.

    .venv/bin/python scripts/importar_citas.py --cuantas 40 --dry-run
    .venv/bin/python scripts/importar_citas.py --cuantas 40

De dónde salen
──────────────
De `corpus/citas/` del repositorio del sitio (hectorglez4.github.io): 1.367
citas con texto, autor, obra, estado de derechos y fuente con URL. Todas de
dominio público y ya verificadas — es el mismo criterio con el que se admiten al
sitio, que es más estricto que el nuestro porque allí una cita mal atribuida
queda publicada para siempre en una URL canónica.

Para qué
────────
El banco de borradores lo llena una rutina que escribe ocho piezas al día, pero
esa rutina solo corre con la app abierta. Para dos semanas de vacaciones hacían
falta sesenta fotos y el banco daba veintiuna. Aquí hay contenido verificado de
sobra y no depende de que ninguna máquina esté encendida.

Qué se genera y qué no
──────────────────────
El texto, el autor, la obra y la fuente vienen del corpus tal cual. El cuerpo se
compone de la semblanza del autor, que también es del corpus.

La PREGUNTA de cierre se genera a partir del tema, y esa es la parte débil: una
pregunta mecánica nunca es tan buena como una escrita mirando la cita concreta.
Por eso cada pieza importada lo dice en `do_not_use`, para que quien la revise
sepa dónde mirar. Es una decisión consciente: una pregunta mediocre con una cita
verificada rinde más que un hueco en la cola.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITIO = pathlib.Path("/Users/hec/dev/sitio-sdb")
DRAFTS = ROOT / "content" / "drafts"

# Una pregunta por tema. Abiertas y breves, como pide la línea editorial, y
# contestables sin pensar diez minutos — que es lo que baja el coste de comentar.
PREGUNTAS = {
    "el-miedo": "¿Qué miedo te ha enseñado más que su remedio?",
    "el-saber": "¿Qué aprendiste tarde y te habría servido antes?",
    "el-tiempo": "¿En qué se te va el tiempo que no querrías?",
    "el-trabajo": "¿Qué parte de tu trabajo harías gratis?",
    "la-adversidad": "¿Qué te sostuvo la última vez que se puso difícil?",
    "la-amistad": "¿A quién llamarías a las tres de la mañana?",
    "la-felicidad": "¿Cuándo fue la última vez que no te faltaba nada?",
    "la-justicia": "¿Qué injusticia pequeña dejas pasar cada día?",
    "la-libertad": "¿De qué te costó más soltarte?",
    "la-muerte": "¿Qué te gustaría que se contara de ti?",
    "la-palabra": "¿Qué frase te cambió algo?",
    "la-patria": "¿Qué lugar sigues llamando tuyo?",
    "la-prudencia": "¿Qué decisión agradeces no haber tomado deprisa?",
    "la-riqueza": "¿Qué tienes que no comprarías?",
    "la-verdad": "¿Qué verdad te costó más aceptar?",
    "la-vida": "¿Qué harías hoy si no hubiera prisa?",
    "la-virtud": "¿Qué virtud admiras y no practicas?",
}
PREGUNTA_POR_DEFECTO = "¿Qué te deja pensando esta frase?"


def _frontmatter(texto: str) -> dict:
    """Lee el frontmatter YAML sin dependencias: son ficheros planos y regulares."""
    m = re.match(r"^---\n(.*?)\n---", texto, re.S)
    if not m:
        return {}
    datos: dict = {}
    pila = [(0, datos)]
    for linea in m.group(1).split("\n"):
        if not linea.strip() or linea.strip().startswith("#"):
            continue
        sangria = len(linea) - len(linea.lstrip())
        contenido = linea.strip()
        while len(pila) > 1 and sangria <= pila[-1][0]:
            pila.pop()
        destino = pila[-1][1]
        if contenido.startswith("- "):
            destino.setdefault("_lista", []).append(contenido[2:].strip().strip('"'))
            continue
        if ":" not in contenido:
            continue
        clave, _, valor = contenido.partition(":")
        clave, valor = clave.strip(), valor.strip()
        if not valor:
            hijo: dict = {}
            destino[clave] = hijo
            pila.append((sangria, hijo))
        else:
            destino[clave] = valor.strip('"')
    return datos


def _limpia(d: dict) -> dict:
    """Convierte los `_lista` intermedios en listas de verdad."""
    fuera = {}
    for k, v in d.items():
        if isinstance(v, dict):
            if set(v) == {"_lista"}:
                fuera[k] = v["_lista"]
            else:
                fuera[k] = _limpia(v)
        else:
            fuera[k] = v
    return fuera


def autores() -> dict[str, dict]:
    fuera = {}
    for p in (SITIO / "corpus" / "autores").glob("*.yml"):
        fuera[p.stem] = _limpia(_frontmatter("---\n" + p.read_text(encoding="utf-8") + "\n---"))
    return fuera


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cuantas", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not SITIO.exists():
        print(f"No encuentro el repo del sitio en {SITIO}", file=sys.stderr)
        return 1

    aut = autores()
    ya = set()
    for carpeta in ("drafts", "queue", "published"):
        for p in (ROOT / "content" / carpeta).glob("*.json"):
            u = json.loads(p.read_text(encoding="utf-8"))
            q = (u.get("core") or {}).get("quote") or {}
            if q.get("text"):
                ya.add(q["text"].strip().lower()[:60])

    citas = sorted((SITIO / "corpus" / "citas").glob("*.md"))
    random.Random(20260913).shuffle(citas)

    escritas = 0
    por_autor: dict[str, int] = {}
    for ruta in citas:
        if escritas >= a.cuantas:
            break
        d = _limpia(_frontmatter(ruta.read_text(encoding="utf-8")))
        texto = (d.get("texto") or "").strip()
        slug_autor = d.get("autor") or ""
        if not texto or slug_autor not in aut:
            continue
        if texto.lower()[:60] in ya:
            continue
        # UNA por autor, no tres. La regla de no repetir tema en 90 días mira
        # el sujeto, y el sujeto empieza por el nombre del autor: dos palabras
        # significativas que ya disparan la coincidencia. Dos citas del mismo
        # autor se bloquean entre sí aunque sean textos distintos.
        if por_autor.get(slug_autor, 0) >= 1:
            continue
        # La cita tiene que caber en la tarjeta y en el límite de Instagram.
        if len(texto) > 300:
            continue

        info = aut[slug_autor]
        nombre = info.get("nombre", slug_autor)
        años = ""
        if info.get("añoNacimiento"):
            años = f" ({info['añoNacimiento']}-{info.get('añoFallecimiento','')})".replace("-)", ")")
        obra = (d.get("procedencia") or {}).get("obra") or ""
        fuente = d.get("fuente") or {}
        temas = d.get("temas") or []
        tema = temas[0] if temas else ""

        pieza = {
            "id": "PENDIENTE",
            "slot": "tarde",
            "pillar": "cita",
            "core": {
                "subject": f"{nombre} — {texto.split(' ')[0:6] and ' '.join(texto.split(' ')[:5])}",
                "hook": f'"{texto}"',
                "body": [info.get("semblanza", "").strip()] if info.get("semblanza") else
                        [f"{nombre}{años}."],
                "question": PREGUNTAS.get(tema, PREGUNTA_POR_DEFECTO),
                "quote": {
                    "text": texto,
                    "author": f"{nombre}{años}".strip(),
                    "work": obra,
                    "attribution_verified": True,
                },
            },
            "card": {"renderer": "quote_card", "variant": "cream"},
            "sources": [{
                "claim": f"Texto de la cita, atribuida a {nombre}"
                         + (f" en «{obra}»" if obra else "")
                         + f". Estado de derechos: {d.get('estadoDerechos','?')}.",
                "source": fuente.get("nombre", "corpus de sabiduriadebolsillo.net"),
                "url": fuente.get("url", "https://sabiduriadebolsillo.net/"),
            }],
            "do_not_use": [
                "REVISAR LA PREGUNTA: se generó a partir del tema del corpus, no "
                "mirando esta cita concreta. Cámbiala si no encaja.",
            ],
            "cita_slug": d.get("slug", ""),
            "targets": ["facebook", "instagram", "threads"],
            "status": "draft",
        }
        # el subject, corto de verdad
        pieza["core"]["subject"] = f"{nombre}, «{' '.join(texto.split()[:4])}…»"[:70]
        if not pieza["cita_slug"]:
            continue          # sin slug no hay página a la que enlazar

        destino = DRAFTS / f"importada-{ruta.stem[:48]}.json"
        if not a.dry_run:
            destino.write_text(json.dumps(pieza, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        ya.add(texto.lower()[:60])
        por_autor[slug_autor] = por_autor.get(slug_autor, 0) + 1
        escritas += 1
        if escritas <= 5:
            print(f"  {nombre:24s} «{texto[:52]}…»")

    print(f"\n  {escritas} citas importadas"
          + (" (dry-run, no se escribió nada)" if a.dry_run else " a content/drafts/"))
    print(f"  autores distintos: {len(por_autor)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
