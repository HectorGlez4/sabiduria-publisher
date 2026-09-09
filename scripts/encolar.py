#!/usr/bin/env python3
"""
Pasa contenido del banco y del archivo a la cola de publicación.

    .venv/bin/python scripts/encolar.py --dry-run
    .venv/bin/python scripts/encolar.py --dias 3

Por qué existe
──────────────
La rutina diaria escribe borradores y el publicador consume la cola, pero entre
las dos cosas no había nada: el paso de borrador a cola lo hacía una persona a
mano. Mientras alguien se acordaba, funcionaba. El 9 de septiembre la cola se
quedó en dos piezas y esa semana salieron CERO reels y CERO historias — los
formatos que solo existen si alguien los programa. Las fotos taparon el agujero
en el recuento total y el desplome no se vio hasta mirar por superficie.

Qué encola, y de dónde
──────────────────────
· **Fotos**: del banco (`content/drafts/`), que es contenido nuevo verificado.
  Las citas primero, porque son las que más se comparten.
· **Reels e historias**: reemitiendo el ARCHIVO. No hay que escribir nada nuevo:
  es la misma pieza verificada en otra superficie, y el 98% de los seguidores no
  vio la primera salida.

Reglas que respeta
──────────────────
· El tope diario y el espaciado de `variants.py`, contando solo las superficies
  que la cadencia protege — Threads tiene su propio carril.
· La alternancia de variante contra la predecesora EFECTIVA, que incluye lo ya
  encolado y todavía sin publicar. Calcularla contra la última publicación real
  produce choques que aparecen días después.
· Las reemisiones no repiten contenido que haya salido hace poco. En agosto una
  carrera de push publicó el mismo texto cinco veces; desde entonces la cercanía
  pesa más que la procedencia.

No escribe nada si alguna pieza no pasa esquema y preflight: encolar la mitad de
un plan deja la cola en un estado que nadie planeó.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from zoneinfo import ZoneInfo  # noqa: E402

from src import variants  # noqa: E402

CDMX = ZoneInfo("America/Mexico_City")
QUEUE = ROOT / "content" / "queue"
DRAFTS = ROOT / "content" / "drafts"
PUBLISHED = ROOT / "content" / "published"

# Cuántas piezas de cada tipo por día.
#
# Suman nueve, por debajo del tope de doce de variants.MAX_POR_DIA: el margen es
# para que una ejecución manual o una reemisión suelta quepan sin desbordar.
#
# El reparto no es proporcional a lo que pide el panel, sino a lo que aporta cada
# formato: el reel es la única superficie que llega a NO seguidores, así que pesa
# más de lo que su objetivo semanal sugeriría.
POR_DIA = {"foto": 4, "reel": 3, "historia": 2}

# Horas CDMX en que se reparte el día, de más a menos concurrida.
HORAS = [9, 11, 13, 14, 16, 17, 19, 20, 21, 22]

# Días que una pieza tiene que llevar sin salir para poder reemitirse.
DIAS_DE_REPOSO = 7


def _leer(carpeta: pathlib.Path) -> list[tuple[pathlib.Path, dict]]:
    fuera = []
    for p in sorted(carpeta.glob("*.json")):
        try:
            fuera.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except json.JSONDecodeError as e:
            print(f"  ! {p.name} ilegible: {e}", file=sys.stderr)
    return fuera


def _ultima_salida(unidades: list[dict]) -> dict[str, datetime.datetime]:
    """Cuándo salió por última vez cada SUJETO, contando lo ya programado.

    Lo programado cuenta: si una pieza sale mañana, su contenido no está libre
    hoy. Mirar solo lo publicado fue lo que dejó dos reemisiones del mismo texto
    a pocos días una de otra.
    """
    minimo = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    ultima: dict[str, datetime.datetime] = collections.defaultdict(lambda: minimo)
    for u in unidades:
        s = (u.get("core") or {}).get("subject") or ""
        if not s:
            continue
        for red, x in (u.get("results") or {}).items():
            if x.get("post_id") and red.startswith("facebook") and x.get("published_at"):
                t = datetime.datetime.fromisoformat(x["published_at"].replace("Z", "+00:00"))
                ultima[s] = max(ultima[s], t)
        publicado = any(x.get("post_id") for x in (u.get("results") or {}).values())
        if not publicado and u.get("publish_at"):
            t = datetime.datetime.fromisoformat(u["publish_at"].replace("Z", "+00:00"))
            ultima[s] = max(ultima[s], t)
    return ultima


def huecos(dias: int, cola: list[dict], archivo: list[dict],
           ahora: datetime.datetime) -> list[datetime.datetime]:
    """Horas libres, sin pasar del tope diario ni pisar lo ya programado."""
    ocupadas: dict[datetime.date, set[int]] = collections.defaultdict(set)
    porc: collections.Counter[datetime.date] = collections.Counter()
    for u in cola:
        t = datetime.datetime.fromisoformat(u["publish_at"].replace("Z", "+00:00")).astimezone(CDMX)
        ocupadas[t.date()].add(t.hour)
        porc[t.date()] += 1
    for u in archivo:
        ts = [x["published_at"] for x in (u.get("results") or {}).values()
              if x.get("post_id") and x.get("published_at")]
        if ts:
            d = datetime.datetime.fromisoformat(min(ts).replace("Z", "+00:00")).astimezone(CDMX).date()
            porc[d] += 1

    fuera = []
    dia = ahora.astimezone(CDMX).date()
    for _ in range(dias + 1):
        for h in HORAS:
            if porc[dia] >= variants.MAX_POR_DIA:
                break
            if h in ocupadas[dia]:
                continue
            t = datetime.datetime(dia.year, dia.month, dia.day, h, 26, tzinfo=CDMX)
            if t <= ahora.astimezone(CDMX) + datetime.timedelta(minutes=35):
                continue
            fuera.append(t)
            ocupadas[dia].add(h)
            porc[dia] += 1
        dia += datetime.timedelta(days=1)
    return sorted(fuera)


def candidatas_reemision(archivo: list[dict], ultima: dict, ahora: datetime.datetime,
                         reposo: int) -> list[dict]:
    """Piezas del archivo cuyo contenido lleva suficiente sin aparecer."""
    limite = ahora - datetime.timedelta(days=reposo)
    fuera = []
    for u in archivo:
        s = (u.get("core") or {}).get("subject") or ""
        if not s or u.get("reemision_de"):
            continue
        if ultima[s] <= limite:
            fuera.append((ultima[s], u))
    fuera.sort(key=lambda x: x[0])
    return [u for _, u in fuera]


def reemision(original: dict, formato: str, cuando: datetime.datetime, n: int) -> dict:
    u = json.loads(json.dumps(original))
    sufijo = {"reel": "reel", "historia": "story"}[formato]
    u["id"] = f"{cuando.astimezone(CDMX).date()}-re{n:02d}-{sufijo}"
    u["publish_at"] = cuando.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")
    u["status"] = "ready"
    u["results"] = {}
    u["reemision_de"] = original["id"]
    u["targets"] = (["facebook_reel"] if formato == "reel"
                    else ["facebook_story", "instagram_story"])
    for k in ("attempts", "last_attempt", "blocked_reason", "con_enlace"):
        u.pop(k, None)
    return u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=2, help="cuántos días llenar")
    ap.add_argument("--reposo", type=int, default=DIAS_DE_REPOSO)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    ahora = datetime.datetime.now(datetime.timezone.utc)
    cola = _leer(QUEUE)
    banco = _leer(DRAFTS)
    archivo = _leer(PUBLISHED)
    unidades = [u for _, u in cola + archivo]
    ultima = _ultima_salida(unidades)

    libres = huecos(a.dias, [u for _, u in cola], [u for _, u in archivo], ahora)
    cupo = {k: v * a.dias for k, v in POR_DIA.items()}
    print(f"Huecos libres en {a.dias} día(s): {len(libres)}")
    print(f"Objetivo: {cupo['foto']} fotos · {cupo['reel']} reels · "
          f"{cupo['historia']} historias")

    # Fotos del banco: las citas primero, y dentro de cada grupo más fuentes antes.
    fotos = sorted(
        (b for b in banco
         if not any("REVISAR" in x for x in b[1].get("do_not_use", []))),
        key=lambda b: (b[1]["pillar"] != "cita", -len(b[1].get("sources", []))))
    if len(fotos) < cupo["foto"]:
        print(f"  ⚠ el banco da para {len(fotos)} fotos y hacen falta {cupo['foto']}")

    reemitibles = candidatas_reemision(
        [u for _, u in archivo], ultima, ahora, a.reposo)
    if len(reemitibles) < cupo["reel"] + cupo["historia"]:
        print(f"  ⚠ el archivo da para {len(reemitibles)} reemisiones y hacen falta "
              f"{cupo['reel'] + cupo['historia']}")

    # Intercalado por día: foto, reel, foto, historia…
    #
    # Sin esto el muro sale por bloques —seis fotos seguidas y luego seis
    # reels—, que es justo lo que delata que detrás hay un programa. Se reparte
    # cada tipo lo más separado posible dentro del día.
    def _repartir(dia: dict[str, int]) -> list[str]:
        cubos = [[t] * n for t, n in dia.items() if n]
        cubos.sort(key=len, reverse=True)
        fuera: list[str] = []
        while any(cubos):
            for c in cubos:
                if c:
                    fuera.append(c.pop())
            cubos.sort(key=len, reverse=True)
        return fuera

    plan_tipos: list[str] = []
    for _ in range(a.dias):
        plan_tipos += _repartir(dict(POR_DIA))

    nuevas: list[tuple[pathlib.Path | None, dict]] = []
    i_foto = i_re = 0
    for tipo, cuando in zip(plan_tipos, libres):
        if tipo == "foto":
            if i_foto >= len(fotos):
                continue
            ruta, u = fotos[i_foto]; i_foto += 1
            u = json.loads(json.dumps(u))
            u["id"] = f"{cuando.astimezone(CDMX).date()}-extra{80 + i_foto:02d}"
            u["publish_at"] = cuando.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")
            u["status"] = "ready"
            u["results"] = {}
            u["targets"] = ["facebook", "instagram", "threads"]
            nuevas.append((ruta, u))
        else:
            if i_re >= len(reemitibles):
                continue
            orig = reemitibles[i_re]; i_re += 1
            nuevas.append((None, reemision(orig, tipo, cuando, 50 + i_re)))

    # Alternancia sobre el orden real, contando lo ya encolado.
    todo = sorted([(None, u) for _, u in cola] + nuevas,
                  key=lambda x: x[1]["publish_at"])
    sim = [u for _, u in archivo]
    cambios = 0
    for _, u in todo:
        if not u.get("reemision_de"):
            perm, _ = variants.preflight_separado(u, sim, None)
            if any("variante" in x for x in perm):
                u["card"]["variant"] = "gold" if u["card"]["variant"] == "cream" else "cream"
                cambios += 1
        sim.append(dict(u, status="published",
                        results={"facebook": {"post_id": "sim",
                                              "published_at": u["publish_at"]}}))

    # Comprobación final: o pasa todo, o no se escribe nada.
    from jsonschema import Draft7Validator  # noqa: PLC0415
    v = Draft7Validator(json.loads((ROOT / "content" / "schema.json").read_text(encoding="utf-8")))
    sim = [u for _, u in archivo]
    malas = 0
    for _, u in todo:
        fallos = [e.message for e in v.iter_errors(u)]
        perm, _ = variants.preflight_separado(u, sim, None)
        if fallos or perm:
            malas += 1
            print(f"  ✗ {u['id']}: {(fallos + perm)[0][:70]}")
        sim.append(dict(u, status="published",
                        results={"facebook": {"post_id": "sim",
                                              "published_at": u["publish_at"]}}))

    print(f"\nSe encolarían {len(nuevas)} piezas · {cambios} variantes ajustadas "
          f"· {len(todo) - malas}/{len(todo)} válidas")
    for _, u in nuevas:
        tipo = ("historia" if "facebook_story" in u["targets"]
                else "reel" if "facebook_reel" in u["targets"] else "foto")
        cuando = datetime.datetime.fromisoformat(
            u["publish_at"].replace("Z", "+00:00")).astimezone(CDMX)
        print(f"  {cuando:%m-%d %H:%M}  {tipo:9s} {u['id']:24s} "
              f"{(u.get('core') or {}).get('subject', '')[:40]}")

    if malas:
        print("\n  No se escribe nada: encolar la mitad de un plan deja la cola "
              "en un estado que nadie planeó.")
        return 1
    if a.dry_run:
        print("\n  --dry-run: no se escribe nada")
        return 0

    for _, u in todo:
        (QUEUE / f"{u['id']}.json").write_text(
            json.dumps(u, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for ruta, _ in nuevas:
        if ruta and ruta.exists():
            ruta.unlink()
    print(f"\n  escritas {len(nuevas)} piezas en content/queue/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
