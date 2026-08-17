#!/usr/bin/env python3
"""
Convierte content/_migrar/cola-de-publicacion.md a JSON conforme al esquema.

Determinista y re-ejecutable a proposito: la conversion se puede auditar
comparando la salida con el markdown, y se puede repetir si aparece un fallo.
Nada se escribe a mano.

Lo unico que NO se deriva automaticamente son 'sources' y 'do_not_use': salen de
la prosa del campo Verificacion, que mezcla lo comprobado con lo desmentido y
exige criterio. El conversor extrae lo que puede y **preserva la prosa integra**
en _verificacion_prosa para que ninguna hora de verificacion se pierda por un
fallo de parseo.

    python3 scripts/migrar.py --dry-run     # enseña qué haría
    python3 scripts/migrar.py               # escribe content/queue/*.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shlex
import sys
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
FUENTE = ROOT / "content" / "_migrar" / "cola-de-publicacion.md"
MANUALES = ROOT / "scripts" / "fuentes_manuales.json"
QUEUE = ROOT / "content" / "queue"
PUBLICADAS = ROOT / "content" / "published"

FRANJA = {"mañana": "manana", "manana": "manana", "tarde": "tarde", "noche": "noche"}

PILAR = {
    "cita comentada": "cita",
    "civilizaciones": "civilizacion",
    "civilizaciones y mitología": "civilizacion",
    "curiosidad / dato olvidado": "curiosidad",
    "figura histórica": "figura",
    "filosofía aplicada": "filosofia",
    "arte y ciencia": "arte-ciencia",
}


def trocear(texto: str) -> list[str]:
    """Las entradas van de un '### fecha · franja · ESTADO' al siguiente."""
    partes = re.split(r"^### (?=\d{4}-\d{2}-\d{2} · )", texto, flags=re.M)
    return [p for p in partes if re.match(r"^\d{4}-\d{2}-\d{2} · ", p)]


def campo(bloque: str, nombre: str) -> str | None:
    """Un campo '- **Nombre:** valor', que puede continuar en lineas sueltas."""
    m = re.search(
        rf"^\- \*\*{nombre}:\*\*[ ]?(.*?)(?=^\- \*\*|^\*\*|^```|\Z)",
        bloque, flags=re.M | re.S,
    )
    return m.group(1).strip() if m else None


def bloque_codigo(bloque: str, tras: str) -> str | None:
    """El primer bloque ``` que aparece despues de una etiqueta dada."""
    i = bloque.find(tras)
    if i < 0:
        return None
    m = re.search(r"```\w*\n(.*?)```", bloque[i:], flags=re.S)
    return m.group(1).rstrip("\n") if m else None


def partir_copy(copy: str) -> tuple[str, list[str], str, list[str]]:
    """
    Separa el copy en gancho / cuerpo / pregunta / etiquetas.

    La estructura la fija linea-editorial.md: encabezado, parrafos, una sola
    pregunta de cierre y la linea de etiquetas.
    """
    parrafos = [p.strip() for p in copy.strip().split("\n\n") if p.strip()]
    etiquetas: list[str] = []
    if parrafos and parrafos[-1].lstrip().startswith("#"):
        etiquetas = parrafos.pop().split()
    pregunta = ""
    if parrafos and parrafos[-1].rstrip().endswith("?"):
        pregunta = parrafos.pop()
    gancho = parrafos.pop(0) if parrafos else ""
    return gancho, parrafos, pregunta, etiquetas


def comando_tarjeta(bloque: str) -> str | None:
    """
    El comando de la tarjeta viene de dos formas en el markdown: entre comillas
    invertidas en la misma linea, o en un bloque cercado justo debajo. Las dos
    aparecen en la cola, asi que se aceptan las dos.
    """
    linea = campo(bloque, "Tarjeta") or ""
    m = re.search(r"`([^`]*(?:quote_card|text_card)\.py[^`]*)`", linea, flags=re.S)
    if m:
        return m.group(1)
    cercado = bloque_codigo(bloque, "**Tarjeta:**")
    if cercado and ("quote_card.py" in cercado or "text_card.py" in cercado):
        return cercado
    return None


def args_tarjeta(cmd: str | None) -> dict:
    """Los argumentos exactos del comando de la tarjeta, sin reinterpretarlos."""
    if not cmd:
        return {}
    trozos = shlex.split(cmd.replace("\n", " "))
    renderer = "quote_card" if "quote_card.py" in cmd else "text_card"
    out = {"renderer": renderer}
    i = 0
    while i < len(trozos):
        if trozos[i].startswith("--") and i + 1 < len(trozos):
            out[trozos[i][2:]] = trozos[i + 1]
            i += 2
        else:
            i += 1
    return out


def separar(texto: str, sep: str) -> list[str]:
    """
    Parte por un separador solo cuando esta FUERA de parentesis y de comillas.

    Las fuentes y los descartes llevan parentesis y frases entrecomilladas con
    comas y puntos y coma dentro; partir a lo bruto los trocea mal y se pierde
    justo el detalle que hace util la verificacion.
    """
    partes, actual, prof, comillas = [], [], 0, False
    for ch in texto:
        if ch in '"\u201c\u201d':
            comillas = not comillas
        elif ch == "(":
            prof += 1
        elif ch == ")":
            prof = max(prof - 1, 0)
        if ch == sep and prof == 0 and not comillas:
            partes.append("".join(actual))
            actual = []
        else:
            actual.append(ch)
    partes.append("".join(actual))
    return [limpiar(p) for p in partes if limpiar(p)]


def limpiar(t: str) -> str:
    """Quita el marcado de negrita y cursiva y los restos de puntuacion."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = t.strip().strip(".").strip()
    return re.sub(r"^y\s+", "", t).strip()


def trocear_verificacion(prosa: str, tema: str) -> tuple[list[dict], list[str]]:
    """
    Saca 'sources' y 'do_not_use' de la prosa de Verificacion.

    El markdown marca los dos a mano: 'Fuentes:' (o 'Fuente:') y '**No usar:**'.
    No se inventa el emparejamiento fuente-afirmacion, que la prosa no da: cada
    fuente queda ligada al tema de la pieza, que es lo que de verdad verifica.
    La prosa integra se conserva aparte por si el troceo se deja algo.
    """
    m_no = re.search(r"\*\*No usar:?\*\*\s*(.*?)(?=Fuentes?:|\Z)", prosa, flags=re.S)
    no_usar = separar(m_no.group(1), ";") if m_no else []

    m_fu = re.search(r"Fuentes?:\s*(.*?)(?=\*\*No usar:?\*\*|\Z)", prosa, flags=re.S)
    fuentes = separar(m_fu.group(1), ",") if m_fu else []

    return [{"claim": tema, "source": f} for f in fuentes], no_usar


def convertir(bloque: str) -> dict | None:
    cab = bloque.splitlines()[0]
    m = re.match(r"^(\d{4}-\d{2}-\d{2}) · (\S+) · (.+)$", cab)
    if not m:
        return None
    fecha, franja_txt, estado = m.groups()
    if "EN COLA" not in estado:
        return None
    franja = FRANJA[franja_txt]
    pid = f"{fecha}-{franja}"

    # hora: "**Hora:** 13:34 CDMX = 19:34 UTC"
    hm = re.search(r"\*\*Hora:\*\*.*?(\d{1,2}):(\d{2})\s*UTC", bloque)
    if hm:
        h, mi = int(hm.group(1)), int(hm.group(2))
        base = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cuando = base.replace(hour=h, minute=mi)
        # la franja de noche es 01:30 UTC del dia siguiente
        if franja == "noche" and h < 6:
            cuando += timedelta(days=1)
        publish_at = cuando.strftime("%Y-%m-%dT%H:%M:00Z")
    else:
        publish_at = None

    pilar_txt = (campo(bloque, "Pilar") or "").strip().lower()
    pilar = PILAR.get(pilar_txt)
    if not pilar:
        raise ValueError(f"{pid}: pilar desconocido {pilar_txt!r}")

    tarjeta = args_tarjeta(comando_tarjeta(bloque))
    if not tarjeta:
        raise ValueError(f"{pid}: no se pudo leer el comando de la tarjeta")

    copy_fb = bloque_codigo(bloque, "**Copy Facebook:**")
    if not copy_fb:
        raise ValueError(f"{pid}: falta el copy de Facebook")
    gancho, cuerpo, pregunta, tags_fb = partir_copy(copy_fb)

    tags_ig_raw = bloque_codigo(bloque, "**Copy Instagram:**") or ""
    tags_ig = [t for t in tags_ig_raw.split() if t.startswith("#")]

    principal = "#SabiduriaDeBolsillo"
    topic = [t for t in tags_fb if t.lower() != principal.lower()]
    extended = [t for t in tags_ig
                if t.lower() != principal.lower()
                and t.lower() not in {x.lower() for x in topic}]

    card: dict = {"renderer": tarjeta["renderer"], "variant": tarjeta.get("variant", "cream")}
    if tarjeta["renderer"] == "text_card":
        for k in ("title", "subtitle", "body"):
            if tarjeta.get(k):
                card[k] = tarjeta[k]

    tema = campo(bloque, "Tema") or ""
    prosa = campo(bloque, "Verificación") or ""
    fuentes, no_usar = trocear_verificacion(prosa, tema)

    core: dict = {
        "subject": tema,
        "hook": gancho,
        "body": cuerpo,
        "question": pregunta,
    }
    if tarjeta["renderer"] == "quote_card":
        core["quote"] = {
            "text": tarjeta.get("quote", ""),
            "author": tarjeta.get("author", ""),
            "attribution_verified": True,
        }

    return {
        "id": pid,
        "publish_at": publish_at,
        "slot": franja,
        "pillar": pilar,
        "core": core,
        "card": card,
        "tags": {"primary": principal, "topic": topic, "extended": extended},
        "sources": fuentes,
        "do_not_use": no_usar,
        "_verificacion_prosa": prosa,
        "targets": ["facebook", "instagram"],
        "status": "draft",
        "results": {},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    bloques = trocear(FUENTE.read_text(encoding="utf-8"))
    ya = {p.stem for p in PUBLICADAS.glob("*.json")} if PUBLICADAS.exists() else set()

    unidades, saltadas, errores = [], [], []
    for b in bloques:
        try:
            u = convertir(b)
        except ValueError as e:
            errores.append(str(e))
            continue
        if not u:
            continue
        if u["id"] in ya:
            saltadas.append(u["id"])
            continue
        unidades.append(u)

    # Piezas cuya prosa nombra las fuentes dentro del texto, sin la etiqueta
    # 'Fuentes:'. Se extrajeron a mano; se aplican aqui para que volver a migrar
    # no las pierda.
    manuales = json.loads(MANUALES.read_text(encoding="utf-8")) if MANUALES.is_file() else {}
    aplicadas = []
    for u in unidades:
        extra = manuales.get(u["id"])
        if not extra:
            continue
        if extra.get("sources"):
            u["sources"] = extra["sources"] + u["sources"]
        if extra.get("do_not_use"):
            u["do_not_use"] = extra["do_not_use"] + u["do_not_use"]
        aplicadas.append(u["id"])

    sin_fuente = [u["id"] for u in unidades if not u["sources"]]

    print(f"bloques leidos:      {len(bloques)}")
    print(f"convertidas:         {len(unidades)}")
    if saltadas:
        print(f"saltadas (ya publicadas): {', '.join(saltadas)}")
    if aplicadas:
        print(f"fuentes manuales aplicadas: {', '.join(aplicadas)}")
    if sin_fuente:
        print(f"SIN FUENTES ({len(sin_fuente)}): {', '.join(sin_fuente)}")
        print("  Una pieza sin verificacion no se publica: preflight la bloquea.")
        errores.extend(f"{i}: sin fuentes" for i in sin_fuente)
    if errores:
        print(f"ERRORES ({len(errores)}):")
        for e in errores:
            print(f"  - {e}")

    if a.dry_run:
        print("\ndry-run: no se ha escrito nada")
        return 1 if errores else 0

    QUEUE.mkdir(parents=True, exist_ok=True)
    for u in unidades:
        (QUEUE / f"{u['id']}.json").write_text(
            json.dumps(u, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nescritas {len(unidades)} en {QUEUE}")
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
