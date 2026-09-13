#!/usr/bin/env python3
"""
Publica en Threads desde el archivo, en su propio carril.

    .venv/bin/python scripts/hilos.py --dry-run
    .venv/bin/python scripts/hilos.py --max 3

Por qué un carril aparte
────────────────────────
La cadencia de `variants.py` cuenta UNIDADES, no plataformas: el tope diario y
el espaciado miran cuántas piezas salieron, vengan de la red que vengan. Si
Threads pasara por ahí, veinticuatro hilos al día se comerían los doce huecos
del día entero y no saldría ni una foto ni un reel. Threads necesita su propio
reloj, y lo tiene aquí.

Eso es correcto además por el fondo: el tope existe para no parecer un bot en el
muro de Facebook, donde el público es el mismo y ve las publicaciones seguidas.
Threads es otra superficie, con otro público —hoy, ninguno— y otro ritmo nativo,
que es mucho más alto que el de Facebook.

De dónde sale el contenido
──────────────────────────
Del ARCHIVO entero, no de la cola. En Threads no se ha publicado nunca, así que
las más de cien piezas publicadas son inéditas ahí: no hay repetición que
evitar mientras queden piezas sin hilo. Se elige la más antigua sin publicar en
Threads; cuando se agoten, la que lleve más tiempo sin volver a salir.

Cada pieza guarda su resultado en `results.threads`, igual que las demás redes,
así que el rastro y el control de repetición son el mismo mecanismo de siempre.
"""
from __future__ import annotations

import argparse
import json
import re
import random
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import variants  # noqa: E402
from src.platforms import meta  # noqa: E402

ARCHIVO = ROOT / "content" / "published"

# El corpus del sitio. En el portátil está al lado; en GitHub Actions el workflow
# lo clona y pasa la ruta por SDB_SITIO_DIR. Si no está, el carril sigue tirando
# del archivo como siempre.
SITIO = pathlib.Path(os.environ.get("SDB_SITIO_DIR", "/Users/hec/dev/sitio-sdb"))

# Qué citas del sitio ya salieron como hilo. Va aparte de content/published/ a
# propósito: published/ es la memoria del muro de Facebook e Instagram, y de ahí
# leen la regla de no repetir tema en 90 días y la cadencia. Un hilo de Threads
# no aparece en ese muro y no debe contar en sus reglas.
REGISTRO_SITIO = ROOT / "content" / "hilos_sitio.json"

# Una cita más larga que esto no deja sitio al autor y al enlace dentro de los
# 500 caracteres: variants.threads la cortaría a mitad de frase.
MAX_CITA = 360

# Una por hora, que es lo pedido. El espaciado se mide contra el último hilo
# REAL, no contra el reloj de la ejecución: si GitHub se salta horas —y se las
# salta— la siguiente ejecución encuentra el hueco y publica, en vez de esperar
# a una hora en punto que ya pasó.
MINUTOS_ENTRE_HILOS = 55

# Tope diario propio. La API de Threads admite 250 publicaciones cada 24 h; esto
# está muy por debajo y deja margen para reintentos.
MAX_AL_DIA = 24


def _cuando(u: dict) -> datetime | None:
    r = (u.get("results") or {}).get("threads") or {}
    t = r.get("published_at")
    if not t:
        return None
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def _registro() -> dict:
    if REGISTRO_SITIO.exists():
        return json.loads(REGISTRO_SITIO.read_text(encoding="utf-8"))
    return {}


def _campo(texto: str, clave: str) -> str:
    m = re.search(rf'^{clave}:\s*"(.*?)"\s*$', texto, re.M)
    return m.group(1) if m else ""


def corpus_sitio() -> list[dict]:
    """Las citas del sitio, con lo que hace falta para componer el hilo."""
    citas_dir = SITIO / "corpus" / "citas"
    if not citas_dir.exists():
        return []
    autores = {}
    for f in (SITIO / "corpus" / "autores").glob("*.yml"):
        y = f.read_text(encoding="utf-8")
        nac = re.search(r"^añoNacimiento:\s*(-?\d+)", y, re.M)
        fal = re.search(r"^añoFallecimiento:\s*(-?\d+)", y, re.M)
        años = f" ({nac.group(1)}-{fal.group(1)})" if nac and fal else ""
        autores[f.stem] = {"nombre": _campo(y, "nombre") + años,
                           "semblanza": _campo(y, "semblanza")}
    fuera = []
    for f in sorted(citas_dir.glob("*.md")):
        md = f.read_text(encoding="utf-8")
        slug, texto, autor = _campo(md, "slug"), _campo(md, "texto"), _campo(md, "autor")
        if not (slug and texto and autor in autores) or len(texto) > MAX_CITA:
            continue
        obra = re.search(r'^\s+obra:\s*"(.*?)"', md, re.M)
        fuera.append({"slug": slug, "texto": texto, "autor": autor,
                      "nombre": autores[autor]["nombre"],
                      "semblanza": autores[autor]["semblanza"],
                      "obra": obra.group(1) if obra else ""})
    # Orden barajado pero fijo: alfabético saldrían todas las de Amado Nervo
    # seguidas, y aleatorio cada ejecución no se podría reproducir.
    random.Random(20260913).shuffle(fuera)
    return fuera


def candidata_sitio() -> dict | None:
    """La siguiente cita del sitio que no ha salido, sin repetir autor seguido."""
    registro = _registro()
    # Las que ya están en nuestras piezas salen por el archivo, con su imagen:
    # publicarlas también por aquí sería el mismo texto dos veces.
    nuestras = set()
    for carpeta in ("published", "queue"):
        for p in (ROOT / "content" / carpeta).glob("*.json"):
            q = (json.loads(p.read_text(encoding="utf-8")).get("core") or {}).get("quote") or {}
            if q.get("text"):
                nuestras.add(q["text"].strip().lower()[:60])
    ultimo_autor = ""
    if registro:
        ultimo_autor = max(registro.values(), key=lambda r: r["published_at"]).get("autor", "")
    libres = [c for c in corpus_sitio()
              if c["slug"] not in registro and c["texto"].strip().lower()[:60] not in nuestras]
    for c in libres:
        if c["autor"] != ultimo_autor:
            return c
    return libres[0] if libres else None


def _unidad_de(c: dict) -> dict:
    """Una pieza en memoria, solo para que variants.threads la componga igual.

    No se guarda en ningún sitio: reutilizar variants es lo que garantiza que el
    enlace se reserve antes de cortar a 500 y que el formato sea el de siempre.
    """
    return {"id": f"sitio:{c['slug']}", "cita_slug": c["slug"],
            "core": {"hook": f'"{c["texto"]}"',
                     "body": [c["semblanza"]] if c["semblanza"] else [],
                     "question": "",
                     "quote": {"text": c["texto"], "author": c["nombre"],
                               "work": c["obra"]}}}


def candidatas() -> list[tuple[pathlib.Path, dict]]:
    """Las del archivo, primero las que nunca salieron en Threads."""
    sin_hilo, con_hilo = [], []
    for p in sorted(ARCHIVO.glob("*.json")):
        u = json.loads(p.read_text(encoding="utf-8"))
        if not (u.get("core") or {}).get("hook"):
            continue
        (con_hilo if _cuando(u) else sin_hilo).append((p, u))
    sin_hilo.sort(key=lambda x: x[1]["id"])
    con_hilo.sort(key=lambda x: _cuando(x[1]) or datetime.min.replace(tzinfo=timezone.utc))
    return sin_hilo + con_hilo


def hilos_recientes() -> list[datetime]:
    fuera = []
    for p in ARCHIVO.glob("*.json"):
        t = _cuando(json.loads(p.read_text(encoding="utf-8")))
        if t:
            fuera.append(t)
    # Los del sitio también: si no contaran, el espaciado de 55 min y el tope
    # diario solo verían la mitad de los hilos y el carril publicaría el doble.
    for r in _registro().values():
        fuera.append(datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")))
    return sorted(fuera)


def puede_publicar(ahora: datetime) -> str | None:
    """None si toca; si no, el motivo."""
    previos = hilos_recientes()
    if previos:
        hueco = (ahora - previos[-1]).total_seconds() / 60
        if hueco < MINUTOS_ENTRE_HILOS:
            return (f"a {hueco:.0f} min del último hilo: el mínimo son "
                    f"{MINUTOS_ENTRE_HILOS}")
    hoy = [t for t in previos if t > ahora - timedelta(hours=24)]
    if len(hoy) >= MAX_AL_DIA:
        return f"ya hay {len(hoy)} hilos en 24 h: el máximo son {MAX_AL_DIA}"
    return None


INTENTOS_DE_REGISTRO = 5


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def _registrar(descripcion: str, aplicar) -> bool:
    """Sube el registro de UN hilo en cuanto se publica. True si llegó a origin.

    `aplicar` es una función que escribe el cambio —un campo en un JSON— y
    devuelve las rutas que tocó. Se le pasa la FUNCIÓN y no el fichero ya escrito
    porque puede hacer falta volver a aplicarla.

    Por qué no `pull --rebase`
    ──────────────────────────
    Hasta el 13 de septiembre esto era add, commit, `pull --rebase` y push. Ese día
    fallaron los cuatro pull de un mismo job, cada uno abortó sin subir nada, y
    cuatro hilos quedaron publicados sin registrar: dos se volvieron a publicar a
    la hora siguiente. La causa exacta no se pudo saber —el log cortaba el error a
    120 caracteres— y en local no se reprodujo, ni con clon superficial.

    En vez de apostar por una hipótesis, se quita el rebase: se descarga el main
    más reciente, se descarta lo local, se VUELVE A APLICAR el cambio encima, y se
    empuja. El cambio es diminuto y se sabe entero, así que reconstruirlo es
    trivial y no puede chocar. Si otro proceso empuja en medio, se reintenta desde
    cero.

    Solo en GitHub Actions. El `reset --hard` en un portátil borraría trabajo sin
    comitear; fuera de CI el registro es un commit y un push normales.
    """
    if os.environ.get("GITHUB_ACTIONS") != "true":
        rutas = aplicar()
        _git("add", *map(str, rutas))
        if _git("diff", "--cached", "--quiet").returncode == 0:
            return True
        _git("commit", "-q", "-m", f"hilo: {descripcion}")
        r = _git("push", "-q", "origin", "HEAD")
        if r.returncode != 0:
            print(f"    ! git push (código {r.returncode}):\n{r.stderr.strip()}",
                  file=sys.stderr)
        return r.returncode == 0

    for intento in range(1, INTENTOS_DE_REGISTRO + 1):
        f = _git("fetch", "-q", "origin", "main")
        if f.returncode != 0:
            print(f"    ! fetch, intento {intento} (código {f.returncode}):\n"
                  f"{f.stderr.strip()}", file=sys.stderr)
            time.sleep(min(2 ** intento, 30))
            continue
        _git("reset", "-q", "--hard", "origin/main")
        try:
            rutas = aplicar()
        except Exception as e:  # el fichero desapareció en origin, JSON roto…
            print(f"    ! no se pudo reaplicar el registro: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return False
        _git("add", *map(str, rutas))
        if _git("diff", "--cached", "--quiet").returncode == 0:
            return True   # origin ya lo tenía idéntico
        c = _git("commit", "-q", "-m", f"hilo: {descripcion}")
        if c.returncode != 0:
            print(f"    ! commit, intento {intento} (código {c.returncode}):\n"
                  f"{c.stderr.strip()}", file=sys.stderr)
            continue
        r = _git("push", "-q", "origin", "HEAD:main")
        if r.returncode == 0:
            return True
        print(f"    ! push, intento {intento} (código {r.returncode}):\n"
              f"{r.stderr.strip()}", file=sys.stderr)
        time.sleep(min(2 ** intento, 30))

    print(f"    ✗ registro de «{descripcion}» sin subir tras "
          f"{INTENTOS_DE_REGISTRO} intentos", file=sys.stderr)
    return False

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=1, metavar="N",
                    help="cuántos hilos como máximo en esta ejecución")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    for n in range(max(a.max, 1)):
        ahora = datetime.now(timezone.utc)
        motivo = puede_publicar(ahora)
        if motivo:
            print(f"  · aún no toca: {motivo}")
            return 0

        # Primero una cita del sitio que no haya salido: el archivo ya salió
        # entero en Threads —177 de 177— y seguir tirando de él es republicar.
        # Cada cita del sitio es inédita aquí y enlaza a su propia página.
        c = candidata_sitio()
        if c:
            u = _unidad_de(c)
            texto = variants.build(u, "threads")["text"]
            print(f"\n▶ sitio · {c['nombre'][:30]} · «{c['texto'][:44]}…»")
            print(f"  {len(texto)} car. · …{texto.splitlines()[-1][-70:]}")
            if a.dry_run:
                print("  · dry-run: no se publica nada")
                return 0
            res = meta.publish_threads(None, texto)
            entrada = {"post_id": res.get("post_id"),
                       "published_at": ahora.isoformat(),
                       "autor": c["autor"]}

            def aplicar(slug=c["slug"], entrada=entrada):
                # Relee el registro del disco: tras el reset es el de origin, que
                # puede traer hilos que otro proceso registró mientras tanto.
                registro = _registro()
                registro[slug] = entrada
                REGISTRO_SITIO.write_text(
                    json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                return [REGISTRO_SITIO]

            aplicar()   # en local ya, para que la cadencia lo vea aunque el push falle
            print(f"  ✓ threads: {res.get('post_id')}")
            _registrar(f"sitio {c['slug']}", aplicar)
        else:
            cola = candidatas()
            if not cola:
                print("no hay nada que publicar, ni en el sitio ni en el archivo")
                return 0
            ruta, u = cola[0]

            texto = variants.build(u, "threads")["text"]
            anterior = _cuando(u)
            marca = "reemitida" if anterior else "inédita en Threads"
            print(f"\n▶ {u['id']} · {(u.get('core') or {}).get('subject', '')[:50]} · {marca}")
            print(f"  {len(texto)} car.")
            if a.dry_run:
                print("  · dry-run: no se publica nada")
                return 0

            # Threads publica texto con enlace: no necesita imagen. El adaptador
            # pide image_url por firma, pero un hilo de solo texto es lo que rinde.
            res = meta.publish_threads(None, texto)
            res["published_at"] = ahora.isoformat()

            def aplicar(ruta=ruta, res=res):
                # Relee la pieza: tras el reset es la de origin, que puede traer
                # otros campos cambiados —un cita_slug, un resultado de publish—
                # y solo se toca results.threads.
                pieza = json.loads(ruta.read_text(encoding="utf-8"))
                pieza.setdefault("results", {})["threads"] = res
                ruta.write_text(json.dumps(pieza, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
                return [ruta]

            aplicar()
            print(f"  ✓ threads: {res.get('post_id')}")
            _registrar(u["id"], aplicar)

        if n + 1 < max(a.max, 1):
            print(f"  · esperando {MINUTOS_ENTRE_HILOS} min")
            time.sleep(MINUTOS_ENTRE_HILOS * 60 + 30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
