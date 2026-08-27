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

import re
import unicodedata
from datetime import datetime, timedelta, timezone

# CDMX es UTC-6 todo el año: México suprimió el horario de verano en 2022, así
# que un desfase fijo es correcto y no hace falta base de datos de zonas.
CDMX = timezone(timedelta(hours=-6))

# Ritmo. Subido el 26 de agosto de 2026 de 3/día y 4 h a 10/día y 1 h, por
# decisión explícita: los objetivos semanales de la página piden ~8 publicaciones
# diarias entre foto, reel e historia, y con 3 al día no se alcanzan nunca.
#
# Estos dos números siguen siendo una regla ANTI-SPAM, no una formalidad. Lo que
# protegen es el espaciado: diez piezas repartidas en el día no se parecen a diez
# piezas seguidas en veinte minutos, y solo la segunda forma parece un bot.
# Si hay que subir más, súbase MAX_POR_DIA; bajar HORAS_MINIMAS de 1 es lo que de
# verdad empieza a parecer automatizado.
MAX_POR_DIA = 10
HORAS_MINIMAS = 1

# Recuperación de atrasos.
#
# El espaciado normal de 1 h solo funciona si el reloj dispara una vez por hora.
# Las ejecuciones programadas de GitHub son "best effort": bajo carga se
# retrasan y a veces se descartan. El 27 de agosto se perdieron SIETE horas
# seguidas. Con un hueco así, cada hora perdida es una publicación que ya no
# cabe: la ventana de la semana no se estira.
#
# Por eso una pieza que lleva más de HORAS_DE_ATRASO esperando puede salir con
# un espaciado menor, el justo para drenar el atraso sin amontonar. Veinte
# minutos entre dos piezas atrasadas no es una ráfaga; publicar ocho seguidas en
# diez minutos sí lo sería, y el tope diario lo sigue impidiendo.
HORAS_DE_ATRASO = 3
HORAS_MINIMAS_ATRASO = 0.35
DIAS_SIN_REPETIR = 90

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



# ───────────────── Reglas que dependen del historial ─────────────────
#
# Las tres se comprueban contra lo REALMENTE PUBLICADO (content/published/),
# no contra la cola. Es la distincion que ya se equivoco una vez con la
# alternancia: la cola es una intencion, el historial es un hecho.


def _instante(unit: dict) -> datetime | None:
    """Cuando salio de verdad; si no consta, cuando estaba previsto."""
    for r in (unit.get("results") or {}).values():
        if r.get("published_at"):
            try:
                return datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
            except ValueError:
                pass
    if unit.get("publish_at"):
        try:
            return datetime.fromisoformat(unit["publish_at"].replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _normalizar(t: str) -> str:
    """Minusculas, sin acentos y sin puntuacion, para comparar temas."""
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Palabras que describen la FORMA del contenido, no su tema. Sin quitarlas,
# dos piezas sin nada que ver ("el verso que escribio dias antes de morir" y
# "las lineas que escribio dias antes de morir") parecen la misma. Se midio
# contra los 42 temas reales: con esta lista y umbral 2 no queda ningun falso
# positivo, y sigue detectandose el mismo tema redactado de otra manera.
VACIAS = {
    # gramaticales
    "el", "la", "los", "las", "un", "una", "de", "del", "que", "por", "para",
    "con", "sin", "sobre", "como", "mas", "pero", "sus", "sino", "cuando",
    "donde", "este", "esta", "esto", "esos", "esas", "and", "the", "pero",
    "desde", "hasta", "entre", "tras", "ante", "segun", "aunque", "porque",
    # forma del contenido
    "frase", "frases", "cita", "citas", "verso", "versos", "poema", "poemas",
    "texto", "textos", "libro", "libros", "obra", "obras", "linea", "lineas",
    "palabra", "palabras", "pagina", "paginas", "capitulo", "carta", "cartas",
    "escribio", "escribir", "escrito", "escribia", "dijo", "dice", "decia",
    "publico", "publicada", "publicado", "redacto", "firmo",
    # biografia generica
    "dias", "dia", "anos", "ano", "siglo", "siglos", "morir", "muerte",
    "murio", "nacio", "vida", "muerto", "antes", "despues", "primera",
    "primer", "primero", "segunda", "segundo", "ultima", "ultimo", "propia",
    "propio", "mismo", "misma", "sobre", "acabo", "quedo", "salio",
    "salir", "resulto", "termino", "acabar", "hizo", "hacer",
}


def _claves(t: str) -> set[str]:
    return {w for w in _normalizar(t).split() if len(w) >= 4 and w not in VACIAS}


def _mismo_tema(a: str, b: str) -> bool:
    """
    Dos temas son el mismo si coinciden normalizados, si uno contiene al otro,
    o si comparten dos o mas palabras significativas.

    'Significativa' excluye las palabras de VACIAS, que describen la forma del
    contenido y no su tema. El umbral se fijo midiendo, no a ojo: con umbral 2
    y sin esa lista salian 9 falsos positivos entre los 42 temas reales (pares
    que solo compartian 'frase' y 'cita'); con la lista, ninguno. Importa
    porque un falso positivo BLOQUEA una publicacion legitima.
    """
    na, nb = _normalizar(a).strip(), _normalizar(b).strip()
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    return len(_claves(a) & _claves(b)) >= 2


def _problemas_de_cadencia(unit: dict, historial: list[dict],
                           ahora: datetime | None = None) -> list[str]:
    """
    Máximo 3 al día en hora de CDMX y mínimo 4 h entre publicaciones.

    Va separada del resto a propósito: es el ÚNICO problema que se arregla solo
    con el paso del tiempo. Dentro de unas horas la misma pieza pasa sin tocar
    nada; el contenido mal, la repetición y la alternancia siguen ahí mañana.

    La distinción decide qué hacer cuando una pieza no pasa. Si es cadencia, se
    reintenta luego. Si no, hay que apartarla: pick_due() vuelve a elegir la
    misma pieza vencida en cada ejecución, así que un problema permanente atasca
    la cola entera y no vuelve a publicarse nada.
    """
    problemas: list[str] = []
    cuando = ahora or _instante(unit)
    if not historial or not cuando:
        return problemas
    reales = sorted(t for t in (_instante(h) for h in historial) if t)
    if not reales:
        return problemas

    dia = cuando.astimezone(CDMX).date()
    mismo_dia = [t for t in reales if t.astimezone(CDMX).date() == dia]
    if len(mismo_dia) >= MAX_POR_DIA:
        problemas.append(
            f"ya hay {len(mismo_dia)} publicaciones el {dia} en hora de CDMX: "
            f"el maximo es {MAX_POR_DIA} al dia"
        )
    # El espaciado exigible depende de cuánto lleve esperando la pieza. Se mide
    # contra su hora PREVISTA, no contra el reloj: 'cuando' es el reloj real al
    # publicar de verdad, y comparar el reloj consigo mismo daría cero siempre.
    prevista = _instante(unit)
    atrasada = bool(prevista and (cuando - prevista).total_seconds() > HORAS_DE_ATRASO * 3600)
    minimo = HORAS_MINIMAS_ATRASO if atrasada else HORAS_MINIMAS

    cercanas = [t for t in reales
                if abs((cuando - t).total_seconds()) < minimo * 3600]
    if cercanas:
        h = min(abs((cuando - t).total_seconds()) for t in cercanas) / 3600
        detalle = (f" (en recuperacion: lleva mas de {HORAS_DE_ATRASO} h de atraso)"
                   if atrasada else "")
        problemas.append(
            f"a {h:.1f} h de otra publicacion: el minimo son {minimo:g} horas{detalle}"
        )
    return problemas


def _problemas_de_historial(unit: dict, historial: list[dict],
                            ahora: datetime | None = None) -> list[str]:
    """
    'ahora' es el instante en que se va a publicar de verdad. Importa: la
    cadencia es una regla ANTI-SPAM, asi que mide el espaciado real, no el
    planeado. Una pieza programada a las 01:38 puede estar a 5 h de la anterior
    sobre el papel y salir a 30 minutos si se fuerza por --id o si el cron se
    retrasa. Al publicar se pasa la hora real; al auditar la cola se deja vacio
    y se usa el horario previsto, que ahi es lo correcto.
    """
    problemas: list[str] = []
    cuando = ahora or _instante(unit)
    if not historial:
        return problemas

    reales = [(h, _instante(h)) for h in historial]
    reales = [(h, t) for h, t in reales if t]
    reales.sort(key=lambda x: x[1])

    # Una reemisión repite a propósito: es la MISMA pieza saliendo en otro
    # formato y en otra superficie, semanas después. La regla de los 90 días
    # existe para que no se cuele dos veces el mismo tema por descuido, no para
    # impedir reutilizar el archivo, así que se salta aquí y solo aquí.
    if unit.get("reemision_de"):
        return problemas

    # ── no repetir en 90 dias ──
    if cuando:
        limite = cuando - timedelta(days=DIAS_SIN_REPETIR)
        recientes = [h for h, t in reales if t >= limite]
        tema = (unit.get("core") or {}).get("subject") or ""
        cita = ((unit.get("core") or {}).get("quote") or {}).get("text") or ""
        for h in recientes:
            otro = (h.get("core") or {}).get("subject") or ""
            if tema and _mismo_tema(tema, otro):
                problemas.append(
                    f"tema repetido en menos de {DIAS_SIN_REPETIR} dias: "
                    f"'{otro}' ({h.get('id')})"
                )
            ocita = ((h.get("core") or {}).get("quote") or {}).get("text") or ""
            if cita and ocita and _normalizar(cita) == _normalizar(ocita):
                problemas.append(f"cita ya publicada en {h.get('id')}")

    # ── alternancia contra la ULTIMA PUBLICACION REAL ──
    #
    # Las reemisiones no cuentan como referencia. Están exentas de alternar
    # —salen arriba, con el resto de reglas de historial— y dejarlas fijar la
    # referencia era una asimetría con consecuencias: una reemisión heredaba la
    # variante de su original, no alternaba con nadie, y aun así obligaba a
    # alternar contra ella a la siguiente pieza nueva. Con el ritmo agresivo
    # intercalando reemisiones entre originales, eso bloqueó cuatro piezas de la
    # cola de la última semana de agosto, y el bloqueo es PERMANENTE: pick_due()
    # vuelve a elegir la misma pieza vencida y atasca la cola entera detrás.
    #
    # Si una pieza no tiene que alternar, tampoco puede obligar a otras.
    originales = [r for r in reales if not r[0].get("reemision_de")]
    if not originales:
        return problemas
    ultima = originales[-1][0]
    v_ultima = (ultima.get("card") or {}).get("variant")
    v_esta = (unit.get("card") or {}).get("variant")
    if v_ultima and v_esta and v_ultima == v_esta:
        problemas.append(
            f"variante '{v_esta}' repetida: la ultima publicacion real "
            f"({ultima.get('id')}) tambien salio {v_ultima}"
        )

    return problemas


def preflight(unit: dict, historial: list[dict] | None = None,
              ahora: datetime | None = None) -> list[str]:
    """
    Comprobaciones que tienen que pasar ANTES de publicar nada.
    Devuelve la lista de problemas; vacía significa que la pieza es publicable.

    'historial' son las piezas ya publicadas (content/published/). Sin él no se
    pueden comprobar cadencia, repetición ni alternancia, porque las tres se
    miden contra lo realmente publicado. publish.py lo carga y lo pasa; una
    lista vacía significa que aún no hay historial, no que la regla no aplique.
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
    # Un quote_card sin cita reventaba en publish.py:101 con un KeyError a mitad
    # del renderizado, DESPUES de pasar la comprobacion previa: la regla de abajo
    # solo mira las citas que existen. Salio al migrar 8 piezas cuyo conversor no
    # copio core.quote. Un fallo asi tiene que decir que le falta a la pieza.
    if (unit.get("card") or {}).get("renderer") == "quote_card" and not q:
        problems.append(
            "tarjeta de cita sin core.quote: el renderizador la exige"
        )
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

    problems += _problemas_de_historial(unit, historial or [], ahora)
    problems += _problemas_de_cadencia(unit, historial or [], ahora)

    return problems


def preflight_separado(unit: dict, historial: list[dict] | None = None,
                       ahora: datetime | None = None) -> tuple[list[str], list[str]]:
    """
    Los mismos problemas que preflight(), divididos en (permanentes, transitorios).

    publish.py los necesita separados para decidir entre reintentar más tarde y
    apartar la pieza. Ver _problemas_de_cadencia sobre por qué importa.
    """
    h = historial or []
    transitorios = _problemas_de_cadencia(unit, h, ahora)
    permanentes = [p for p in preflight(unit, h, ahora) if p not in transitorios]
    return permanentes, transitorios
