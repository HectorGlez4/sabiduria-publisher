"""
Deriva las variantes por plataforma desde la unidad canónica.

Este es el corazón del diseño: la investigación produce UN objeto y aquí se
convierte en cinco textos. Nadie vuelve a escribir un copy por red a mano, que
es de donde salían las asimetrías (Facebook con texto pelado mientras Instagram
llevaba la tarjeta).

Regla: si una plataforma necesita algo que la unidad canónica no tiene, el
arreglo va aquí o en el esquema — nunca en el contenido de una pieza suelta.
"""
from __future__ import annotations

LIMITS = {
    "facebook": {"max_chars": 63206, "max_tags": 5, "cut": 250},
    "instagram": {"max_chars": 2200, "max_tags": 12, "cut": 125},
    "threads": {"max_chars": 500, "max_tags": 0, "cut": 500},
    "x": {"max_chars": 280, "max_tags": 2, "cut": 280},
    "linkedin": {"max_chars": 3000, "max_tags": 3, "cut": 210},
}


def _tags(unit: dict, n: int, extended: bool = False) -> list[str]:
    t = unit.get("tags") or {}
    out = [t.get("primary", "#SabiduriaDeBolsillo")]
    out += list(t.get("topic") or [])
    if extended:
        out += list(t.get("extended") or [])
    seen, uniq = set(), []
    for tag in out:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            uniq.append(tag)
    return uniq[:n]


def _quote_header(unit: dict) -> str | None:
    q = (unit.get("core") or {}).get("quote")
    if not q:
        return None
    attribution = q["author"]
    if q.get("work"):
        attribution += f", {q['work']}"
    return f'"{q["text"]}"\n— {attribution}'


def _long_form(unit: dict, tags: list[str]) -> str:
    core = unit["core"]
    head = _quote_header(unit) or core["hook"]
    parts = [head, *core["body"], core["question"]]
    text = "\n\n".join(p.strip() for p in parts if p and p.strip())
    if tags:
        text += "\n\n" + " ".join(tags)
    return text


def facebook(unit: dict) -> dict:
    """Pie de foto. Facebook corta cerca de los 250 caracteres con 'Ver más'."""
    return {"text": _long_form(unit, _tags(unit, LIMITS["facebook"]["max_tags"]))}


def instagram(unit: dict) -> dict:
    """Mismo texto que Facebook; solo cambian las etiquetas."""
    text = _long_form(unit, _tags(unit, LIMITS["instagram"]["max_tags"], extended=True))
    if len(text) > LIMITS["instagram"]["max_chars"]:
        raise ValueError(f"{unit['id']}: leyenda de Instagram de {len(text)} caracteres, máximo 2200")
    return {"text": text}


def threads(unit: dict) -> dict:
    """
    500 caracteres y sin hashtags: en Threads leen como spam.
    Se queda el gancho y el remate, que es lo que aguanta el formato corto.
    """
    core = unit["core"]
    head = _quote_header(unit) or core["hook"]
    text = f"{head}\n\n{core['body'][-1]}" if core.get("body") else head
    if len(text) > 500:
        text = f"{head}\n\n{core['question']}"
    return {"text": text[:500].rstrip()}


def x(unit: dict) -> dict:
    """
    280 caracteres. El dato duro primero: es lo único que sobrevive al recorte.
    """
    core = unit["core"]
    q = (core.get("quote") or {})
    if q:
        base = f'"{q["text"]}" — {q["author"]}'
    else:
        base = core["hook"]
    tags = _tags(unit, LIMITS["x"]["max_tags"])
    tail = " " + " ".join(tags[1:]) if len(tags) > 1 else ""
    room = 280 - len(tail)
    if len(base) > room:
        base = base[: room - 1].rstrip() + "…"
    return {"text": base + tail}


def linkedin(unit: dict) -> dict:
    """Mismo cuerpo, sin la pregunta de cierre estilo redes y con menos etiquetas."""
    core = unit["core"]
    head = _quote_header(unit) or core["hook"]
    parts = [head, *core["body"]]
    text = "\n\n".join(parts)
    tags = _tags(unit, LIMITS["linkedin"]["max_tags"])
    if tags:
        text += "\n\n" + " ".join(tags)
    return {"text": text[: LIMITS["linkedin"]["max_chars"]]}


RENDERERS = {
    "facebook": facebook,
    "instagram": instagram,
    "threads": threads,
    "x": x,
    "linkedin": linkedin,
}


def build(unit: dict, platform: str) -> dict:
    if platform not in RENDERERS:
        raise KeyError(
            f"'{platform}' no tiene derivación de texto. "
            "TikTok y YouTube consumen vídeo, no texto: ver src/platforms/_pending.py"
        )
    return RENDERERS[platform](unit)


def build_all(unit: dict) -> dict:
    """Todas las variantes de texto de la pieza, para revisar antes de publicar."""
    return {p: build(unit, p) for p in unit.get("targets", []) if p in RENDERERS}


def preflight(unit: dict) -> list[str]:
    """
    Comprobaciones que tienen que pasar ANTES de publicar nada.
    Devuelve la lista de problemas; vacía significa que la pieza es publicable.
    """
    problems = []
    core = unit.get("core") or {}

    if not unit.get("sources"):
        problems.append("sin fuentes: una pieza sin verificación no se publica")
    if not core.get("hook"):
        problems.append("sin gancho")
    if not unit.get("card"):
        problems.append("sin tarjeta: la regla de imagen exige la misma imagen en todas las redes")

    q = core.get("quote")
    if q and not q.get("attribution_verified"):
        problems.append(
            f"cita sin atribución verificada ({q.get('author', '?')}): "
            "las citas mal atribuidas son el peor error de esta página"
        )

    card = unit.get("card") or {}
    if card.get("subtitle") and card["subtitle"].strip() == (core.get("hook") or "").strip():
        problems.append("el subtítulo de la tarjeta repite literalmente el gancho")
    if card.get("body") and len(card["body"]) > 300:
        problems.append(f"cuerpo de tarjeta de {len(card['body'])} caracteres, máximo 300")

    banned = {"#follow4follow", "#viral", "#parati", "#sigueme", "#f4f"}
    all_tags = _tags(unit, 99, extended=True)
    for t in all_tags:
        if t.lower() in banned:
            problems.append(f"etiqueta prohibida: {t} (activa filtros de spam)")

    for p in unit.get("targets", []):
        if p in RENDERERS:
            try:
                out = build(unit, p)
                lim = LIMITS[p]["max_chars"]
                if len(out["text"]) > lim:
                    problems.append(f"{p}: {len(out['text'])} caracteres, máximo {lim}")
            except Exception as e:  # noqa: BLE001
                problems.append(f"{p}: {e}")

    return problems
