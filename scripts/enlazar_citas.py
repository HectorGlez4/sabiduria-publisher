#!/usr/bin/env python3
"""
Pone a cada cita el enlace a su página en sabiduriadebolsillo.net.

    .venv/bin/python scripts/enlazar_citas.py --dry-run
    .venv/bin/python scripts/enlazar_citas.py

Para qué
────────
Un hilo de Threads con una cita enlazaba a la portada del sitio. Quien acababa
de leer la frase llegaba a otra cosa y tenía que buscar lo que ya había leído.
Si la cita existe en el sitio, el hilo enlaza a SU página —/cita/{slug}—, con su
autor, su obra y su procedencia: el enlace deja de ser un anuncio del sitio y
pasa a ser la continuación del hilo.

`variants.threads` ya usa `cita_slug` cuando está. Este script es el que lo
rellena, emparejando nuestras citas con `corpus/citas/` del repositorio del
sitio. Lo usa también `encolar.py`, para que lo que escriba la rutina a partir
de ahora llegue a la cola ya enlazado.

Cómo empareja, y por qué así
────────────────────────────
1. Las diez primeras palabras normalizadas —sin tildes ni puntuación— iguales.
2. Si no, las seis primeras iguales, Y el mismo autor, Y un parecido del texto
   completo de al menos 0,6.

El segundo caso existe por dos cosas reales: el sitio conserva grafías antiguas
("vee" en Cervantes) y a veces solo la primera mitad de un aforismo (Gracián).
Pero seis palabras solas no bastan: dos citas distintas pueden empezar igual, y
un slug equivocado lleva al lector a OTRA frase, que es peor que la portada. Por
eso exige autor y parecido.
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITIO = pathlib.Path("/Users/hec/dev/sitio-sdb")
PARECIDO_MINIMO = 0.6


def _palabras(texto: str) -> list[str]:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", t).split()


def corpus_del_sitio() -> dict[str, dict]:
    """slug → {texto, autor}. Vacío si el repo del sitio no está en esta máquina."""
    fuera: dict[str, dict] = {}
    carpeta = SITIO / "corpus" / "citas"
    if not carpeta.exists():
        return fuera
    for f in carpeta.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        texto = re.search(r'^texto:\s*"(.*?)"\s*$', t, re.M)
        slug = re.search(r'^slug:\s*"(.*?)"', t, re.M)
        autor = re.search(r'^autor:\s*"(.*?)"', t, re.M)
        if texto and slug:
            fuera[slug.group(1)] = {"texto": texto.group(1),
                                    "autor": autor.group(1) if autor else ""}
    return fuera


class Emparejador:
    def __init__(self, corpus: dict[str, dict]):
        self.corpus = corpus
        self.por10 = {" ".join(_palabras(v["texto"])[:10]): k for k, v in corpus.items()}
        self.por6: dict[str, list[str]] = {}
        for k, v in corpus.items():
            self.por6.setdefault(" ".join(_palabras(v["texto"])[:6]), []).append(k)

    def slug(self, cita: dict) -> str | None:
        w = _palabras(cita.get("text", ""))
        if not w:
            return None
        exacto = self.por10.get(" ".join(w[:10]))
        if exacto:
            return exacto
        if len(w) < 6:
            return None
        # El autor del corpus es un slug ("miguel-de-cervantes"); el nuestro,
        # lo que escribiera quien redactó la pieza: "Baltasar Gracián
        # (1601-1658)", pero también "Cervantes, Don Quijote II, 25 (1615)",
        # solo con el apellido. Exigir que TODAS las palabras del autor del sitio
        # estén en el nuestro dejaba fuera a Cervantes por no decir "Miguel de".
        # Basta una palabra significativa en común —el apellido—: el emparejado
        # ya exige las seis primeras palabras iguales y parecido del texto
        # entero, así que el autor solo tiene que confirmar, no identificar.
        nuestro_autor = {x for x in _palabras(cita.get("author", "")) if len(x) >= 4}
        for candidato in self.por6.get(" ".join(w[:6]), []):
            suyo = self.corpus[candidato]
            suyo_autor = {x for x in _palabras(suyo["autor"].replace("-", " ")) if len(x) >= 4}
            if not (nuestro_autor & suyo_autor):
                continue
            r = difflib.SequenceMatcher(None, " ".join(w),
                                        " ".join(_palabras(suyo["texto"]))).ratio()
            if r >= PARECIDO_MINIMO:
                return candidato
        return None


def enlazar(unidad: dict, emp: Emparejador) -> bool:
    """Rellena cita_slug si falta y la cita tiene página. True si cambió algo."""
    if unidad.get("cita_slug"):
        return False
    cita = (unidad.get("core") or {}).get("quote") or {}
    if not cita.get("text"):
        return False
    s = emp.slug(cita)
    if not s:
        return False
    unidad["cita_slug"] = s
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    corpus = corpus_del_sitio()
    if not corpus:
        print(f"No encuentro el corpus del sitio en {SITIO}", file=sys.stderr)
        return 1
    emp = Emparejador(corpus)

    total = 0
    for carpeta in ("queue", "published", "drafts"):
        n = 0
        for f in sorted((ROOT / "content" / carpeta).glob("*.json")):
            u = json.loads(f.read_text(encoding="utf-8"))
            if enlazar(u, emp):
                n += 1
                if not a.dry_run:
                    f.write_text(json.dumps(u, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        print(f"  {carpeta:10} {n} citas enlazadas")
        total += n
    print(f"\n  {total} en total" + (" (dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
