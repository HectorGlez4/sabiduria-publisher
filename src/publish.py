#!/usr/bin/env python3
"""
Publica la siguiente pieza que toque, en todas sus plataformas.

    python3 -m src.publish --due            # lo que ya venció y sigue 'ready'
    python3 -m src.publish --id 2026-08-18-tarde
    python3 -m src.publish --due --dry-run  # genera, valida y enseña, sin publicar

Diseño: una pieza se marca 'published' solo si TODAS sus plataformas salieron.
Si una falla, las demás quedan registradas y la pieza queda 'failed' con el
detalle. Nunca se republica lo que ya tiene post_id — es la protección contra
duplicados que en el sistema anterior faltaba.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import feed, hosting, variants  # noqa: E402
from src.platforms import meta  # noqa: E402
from src.platforms._pending import PENDING  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content" / "queue"
PUBLISHED = ROOT / "content" / "published"
ASSETS = ROOT / "assets"

# Reintentos de una pieza que falló en la plataforma. Un error de Meta suele
# ser pasajero; tres seguidos ya no, y entonces se aparta para que no bloquee
# la cola indefinidamente.
MAX_INTENTOS = 3

# Plataformas que NO se publican por API sino por el feed RSS (src/feed.py).
#
# VACÍO desde el 25 de agosto de 2026: la app WorkItAdmin ya está publicada y
# Facebook vuelve a salir por la Graph API con normalidad.
#
# Lo que pasó, por si vuelve: entre el 17 y el 25 de agosto las publicaciones de
# Facebook tuvieron alcance exactamente cero mientras Instagram iba bien. La causa
# era que la app estaba en modo desarrollo, y Meta solo enseña a los usuarios con
# rol en la app lo que una app genera en ese modo. Costó encontrarlo porque el
# token es de WorkItAdmin (3733795406925924) y no de SabiduriaBolsilloPost: se
# estuvo mirando la app equivocada. `scripts/diagnostico_meta.py` lo dice en su
# primera sección, y es lo primero que hay que ejecutar si el alcance vuelve a
# caer a cero.
#
# Poner {"facebook"} aquí desvía Facebook al feed sin hacer fallar la pieza.
POR_FEED: set[str] = set()


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_history() -> list[dict]:
    """
    Lo ya publicado. Sin esto no se pueden comprobar cadencia, repetición ni
    alternancia: las tres se miden contra lo que salió de verdad, no contra la
    cola. Hasta ahora content/published/ solo se escribía y nunca se leía.
    """
    if not PUBLISHED.exists():
        return []
    return [load(p) for p in sorted(PUBLISHED.glob("*.json"))]


def save(unit: dict, path: pathlib.Path) -> None:
    path.write_text(json.dumps(unit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_due() -> tuple[dict, pathlib.Path] | tuple[None, None]:
    now = datetime.now(timezone.utc)
    candidates = []
    for p in sorted(QUEUE.glob("*.json")):
        unit = load(p)
        if unit.get("status") != "ready":
            continue
        when = unit.get("publish_at")
        if when and datetime.fromisoformat(when.replace("Z", "+00:00")) <= now:
            candidates.append((unit, p))
    if not candidates:
        return None, None
    candidates.sort(key=lambda c: c[0]["publish_at"])
    return candidates[0]


def render_card(unit: dict) -> pathlib.Path:
    """Regenera el PNG desde los parámetros. Determinista: no se versiona la imagen."""
    card = unit["card"]
    out = ASSETS / f"{unit['id']}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    script = ROOT / "src" / "render" / f"{card['renderer']}.py"

    cmd = [sys.executable, str(script), "--variant", card["variant"], "--out", str(out)]
    if card["renderer"] == "quote_card":
        q = unit["core"]["quote"]
        author = q["author"]
        if q.get("work"):
            author = f"{q['author']}, {q['work']}"
        cmd += ["--quote", q["text"], "--author", author]
    else:
        cmd += ["--title", card["title"], "--subtitle", card["subtitle"], "--body", card["body"]]

    # Sin capturar y reemitir stderr, un fallo del renderer llega aquí como un
    # CalledProcessError opaco que no dice ni la excepción ni la línea. Costó
    # una sesión entera diagnosticar así unas rutas de fuente inexistentes.
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        detalle = (r.stderr or r.stdout or "(sin salida)").strip()
        raise RuntimeError(
            f"falló el renderer {card['renderer']} (código {r.returncode}):\n{detalle}"
        )
    if not out.exists():
        raise RuntimeError(f"la tarjeta no se generó: {out}")
    return out


def render_reel(unit: dict) -> pathlib.Path:
    """
    El MP4 vertical de la pieza. Mismo trato que render_card: se regenera desde
    los parámetros y no se versiona.

    Las dos plantillas alimentan los mismos cuatro huecos del reel. En una cita
    el "título" es el autor y el "cuerpo" es la cita, que es justo el orden en
    que se leen en pantalla: primero de quién es, después qué dijo.
    """
    card = unit["card"]
    out = ASSETS / f"{unit['id']}-reel.mp4"
    script = ROOT / "src" / "render" / "reel.py"

    cmd = [sys.executable, str(script), "--variant", card["variant"], "--out", str(out)]
    if card["renderer"] == "quote_card":
        q = unit["core"]["quote"]
        autor = f"{q['author']}, {q['work']}" if q.get("work") else q["author"]
        cmd += ["--title", autor, "--body", q["text"]]
    else:
        cmd += ["--title", card["title"], "--body", card["body"]]
        if card.get("subtitle"):
            cmd += ["--subtitle", card["subtitle"]]
    if unit["core"].get("question"):
        cmd += ["--question", unit["core"]["question"]]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        detalle = (r.stderr or r.stdout or "(sin salida)").strip()
        raise RuntimeError(f"falló el renderer del reel (código {r.returncode}):\n{detalle}")
    if not out.exists():
        raise RuntimeError(f"el reel no se generó: {out}")
    return out


def render_story(unit: dict, formato: str = "png") -> pathlib.Path:
    """
    El PNG vertical de la historia: el último fotograma del reel, quieto.

    Mismos huecos que el reel, y por el mismo motivo — en una cita el título es
    el autor y el cuerpo es la cita.
    """
    card = unit["card"]
    out = ASSETS / f"{unit['id']}-historia.{formato}"
    script = ROOT / "src" / "render" / "historia.py"

    cmd = [sys.executable, str(script), "--variant", card["variant"], "--out", str(out)]
    if card["renderer"] == "quote_card":
        q = unit["core"]["quote"]
        autor = f"{q['author']}, {q['work']}" if q.get("work") else q["author"]
        cmd += ["--title", autor, "--body", q["text"]]
    else:
        cmd += ["--title", card["title"], "--body", card["body"]]
        if card.get("subtitle"):
            cmd += ["--subtitle", card["subtitle"]]
    if unit["core"].get("question"):
        cmd += ["--question", unit["core"]["question"]]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        detalle = (r.stderr or r.stdout or "(sin salida)").strip()
        raise RuntimeError(f"falló el renderer de la historia (código {r.returncode}):\n{detalle}")
    if not out.exists():
        raise RuntimeError(f"la historia no se generó: {out}")
    return out


def upload_asset(path: pathlib.Path) -> str:
    """
    Publica la imagen y devuelve su URL HTTPS pública.

    Instagram y Threads NO aceptan subida binaria: Meta descarga la imagen desde
    la URL. Ver src/hosting.py para los backends disponibles.
    """
    return hosting.upload(path, ROOT)


def contexto_para(unit: dict, dry_run: bool) -> tuple[list[dict], "datetime | None"]:
    """
    Con qué historial y con qué reloj se juzga la pieza.

    Al publicar de verdad: el historial real y la hora real, porque la cadencia
    mide el espaciado que ven los filtros de spam.

    En ensayo: la pieza se juzga EN SU TURNO, no ahora. Cuentan también las
    piezas de la cola programadas antes que ella, que para entonces ya habrán
    salido. Sin esto, un ensayo de una pieza del día 20 la compara contra la
    última publicación real de hoy y da errores de alternancia que no existen,
    y la cadencia la bloquea por estar a media hora de algo que salió hace un
    rato. El ensayo dejaría de servir justo cuando más se usa.
    """
    historial = load_history()
    if not dry_run:
        return historial, datetime.now(timezone.utc)

    cuando = unit.get("publish_at") or ""
    for p in sorted(QUEUE.glob("*.json")):
        otra = load(p)
        if otra.get("id") == unit.get("id"):
            continue
        if (otra.get("publish_at") or "") < cuando:
            otra = dict(otra)
            otra["results"] = {"_simulado": {"published_at": otra.get("publish_at")}}
            historial.append(otra)
    return historial, None


def publish_unit(unit: dict, path: pathlib.Path, dry_run: bool = False) -> str:
    """
    Devuelve el desenlace, no un booleano.

    Hacen falta cuatro, no dos: 'aplazada' —la cadencia dice que aún no toca— es
    funcionamiento normal, no un fallo, y tratarla como tal pintaba el workflow
    de rojo y dispararía el aviso en cada ejecución fuera de ventana.

        published  · salió
        ensayo     · dry-run correcto
        aplazada   · aún no toca; se reintenta sola
        bloqueada  · necesita que alguien mire
        fallida    · falló en la plataforma, se reintentará
    """
    print(f"\n▶ {unit['id']} · {unit['pillar']} · {unit['core'].get('subject', '')}")

    historial, ahora = contexto_para(unit, dry_run)
    permanentes, transitorios = variants.preflight_separado(unit, historial, ahora)

    if permanentes:
        # Se aparta. Si se dejara en 'ready', pick_due() volvería a elegir esta
        # misma pieza vencida en cada ejecución y la cola no avanzaría nunca:
        # un problema de contenido en una pieza silenciaría la página entera.
        print("  ✗ no pasa las comprobaciones previas (requiere intervención):")
        for p in permanentes:
            print(f"      - {p}")
        if not dry_run:
            unit["status"] = "blocked"
            unit["blocked_reason"] = permanentes
            save(unit, path)
            print("  · apartada como 'blocked' para que la cola siga avanzando")
            print("    revísala con: python3 scripts/revisar_bloqueadas.py")
        return "bloqueada"

    if transitorios:
        # Cadencia: se arregla sola con el paso del tiempo. Se deja en 'ready'
        # y se reintenta en la próxima ejecución, sin tocar el archivo.
        print("  · aún no toca, se reintenta en la próxima ejecución:")
        for p in transitorios:
            print(f"      - {p}")
        return "aplazada"

    print("  ✓ comprobaciones previas")

    card_path = render_card(unit)
    print(f"  ✓ tarjeta: {card_path.name} ({card_path.stat().st_size // 1024} KB)")

    texts = variants.build_all(unit)
    for platform, v in texts.items():
        preview = v["text"].split("\n")[0][:70]
        print(f"      {platform:11s} {len(v['text']):5d} car.  {preview}…")
    # El reel no tiene derivación propia en variants.py, así que no sale del
    # bucle de arriba. Sin esta línea, un ensayo de una pieza de mañana no
    # enseñaba NADA de Facebook y parecía que no se iba a publicar allí.
    # Ni el reel ni la historia tienen derivación propia en variants.py, así que
    # no salen del bucle de arriba. Sin estas líneas, un ensayo no enseñaba NADA
    # de esas superficies y parecía que la pieza no se iba a publicar allí — que
    # es exactamente el síntoma con el que se destapó el KeyError del reel.
    if "facebook_reel" in unit.get("targets", []):
        v = variants.build(unit, "facebook")
        print(f"      {'reel (fb)':11s} {len(v['text']):5d} car.  "
              f"{v['text'].split(chr(10))[0][:70]}…")
    for red, etiqueta in (("facebook_story", "historia fb"),
                          ("instagram_story", "historia ig")):
        if red in unit.get("targets", []):
            print(f"      {etiqueta:11s} {'—':>5s} car.  "
                  f"sin pie: el texto va dentro de la imagen, 1080x1920, caduca en 24 h")

    if dry_run:
        print("  · dry-run: no se publica nada")
        return "ensayo"

    image_url = upload_asset(card_path)
    unit.setdefault("results", {})
    ok = True

    for platform in unit.get("targets", []):
        ya = unit["results"].get(platform, {})
        if ya.get("post_id") or ya.get("via"):
            print(f"  · {platform}: ya publicado, se salta")
            continue
        if platform in POR_FEED:
            # Se deja constancia de que la pieza SÍ va a Facebook y por dónde. Sin
            # esta marca, el registro diría que no se publicó, que es falso, y la
            # idempotencia de arriba no tendría de qué agarrarse.
            unit["results"][platform] = {
                "via": "rss",
                "feed": "https://sabiduria.work-it.fr/feed.xml",
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  · {platform}: se sirve por el feed RSS, no por API")
            save(unit, path)
            continue
        if platform in PENDING:
            PENDING[platform]()  # levanta PlatformBlocked con el motivo exacto
        try:
            fn = meta.PUBLISHERS[platform]
            if platform == "facebook_reel":
                # El reel se SUBE, no se descarga de una URL: este adaptador
                # recibe una ruta y no `image_url`.
                #
                # El copy se deriva aquí y NO se saca de `texts`: build_all()
                # solo compone lo que está en `targets`, y en las piezas de
                # mañana 'facebook' ya no está —lo sustituyó 'facebook_reel'—,
                # así que texts["facebook"] daba KeyError. Lo cazó el --dry-run.
                res = fn(str(render_reel(unit)), variants.build(unit, "facebook")["text"])
            elif platform in ("facebook_story", "instagram_story"):
                # La historia SÍ va por URL, como la foto: Meta la descarga. Pero
                # es una imagen distinta —9:16 en vez de 4:5— así que se sube
                # aparte y no se reutiliza `image_url`.
                #
                # Y el formato cambia según la red: Instagram documenta JPEG como
                # el único admitido para publicar por API, mientras que Facebook
                # se traga el PNG. Se renderiza en el que toque en vez de mandar
                # el mismo archivo a las dos y descubrir el rechazo publicando.
                fmt = "jpg" if platform == "instagram_story" else "png"
                res = fn(upload_asset(render_story(unit, fmt)), "")
            else:
                res = fn(image_url, texts[platform]["text"])
            res["published_at"] = datetime.now(timezone.utc).isoformat()
            unit["results"][platform] = res
            print(f"  ✓ {platform}: {res['post_id']}")
        except Exception as e:  # noqa: BLE001
            unit["results"][platform] = {"error": str(e)}
            print(f"  ✗ {platform}: {e}")
            ok = False
        save(unit, path)

    if ok:
        unit["status"] = "published"
        unit.pop("attempts", None)
    else:
        # Un fallo de plataforma se reintenta: la idempotencia impide reenviar
        # lo que ya salió. Antes se marcaba 'failed' sin más y pick_due() la
        # saltaba para siempre: un error pasajero de Meta enterraba una pieza
        # verificada, en silencio.
        intentos = int(unit.get("attempts") or 0) + 1
        unit["attempts"] = intentos
        unit["last_attempt"] = datetime.now(timezone.utc).isoformat()
        if intentos >= MAX_INTENTOS:
            unit["status"] = "blocked"
            unit["blocked_reason"] = [
                f"falló {intentos} veces en la plataforma; último error: "
                + "; ".join(f"{k}: {v['error']}" for k, v in unit["results"].items()
                            if v.get("error"))
            ]
            print(f"  ✗ {intentos} intentos fallidos: apartada como 'blocked'")
        else:
            unit["status"] = "ready"
            print(f"  · intento {intentos} de {MAX_INTENTOS}: se reintentará")
    save(unit, path)

    if ok:
        PUBLISHED.mkdir(parents=True, exist_ok=True)
        path.rename(PUBLISHED / path.name)
        print(f"  ✓ movida a content/published/{path.name}")
        # El feed se regenera DESPUÉS de mover la pieza, porque feed.py lee
        # content/published/. Regenerarlo antes dejaría fuera justo la pieza que
        # se acaba de publicar, que es la única que le importa a dlvr.it.
        ruta_feed = feed.escribir()
        print(f"  ✓ feed: {ruta_feed.relative_to(ROOT)}")
        return "published"
    return "bloqueada" if unit["status"] == "blocked" else "fallida"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true", help="la pieza vencida más antigua en estado ready")
    ap.add_argument("--id", help="una pieza concreta por id")
    ap.add_argument("--dry-run", action="store_true", help="genera y valida, sin publicar")
    ap.add_argument("--max", type=int, default=1, metavar="N",
                    help="con --due, cuantas piezas vencidas intentar como maximo "
                         "en esta ejecucion (por defecto 1)")
    a = ap.parse_args()

    if a.id:
        path = QUEUE / f"{a.id}.json"
        if not path.exists():
            print(f"no existe {path}", file=sys.stderr)
            return 1
        unit = load(path)
    elif a.due:
        # Varias por ejecucion, no una.
        #
        # Con una sola pieza por ejecucion el ritmo real es exactamente el ritmo
        # del reloj, y las ejecuciones programadas de GitHub no son fiables: el
        # 27 de agosto se perdieron siete horas seguidas y con ellas siete
        # publicaciones que ya no cabian en la semana.
        #
        # El bucle NO salta la cadencia: cada pieza vuelve a pasar el preflight.
        # Lo que hace es aprovechar la ejecucion que si ocurrio para drenar lo
        # atrasado, al espaciado reducido que permite variants.HORAS_DE_ATRASO.
        # Se para en cuanto una pieza queda 'aplazada', porque pick_due() elige
        # siempre la mas antigua: si esa no puede salir, las siguientes tampoco.
        ultimo = "published"
        for n in range(max(a.max, 1)):
            unit, path = pick_due()
            if not unit:
                print("nada vencido pendiente de publicar" if n == 0
                      else f"no queda nada mas vencido (salieron {n})")
                return 0
            ultimo = publish_unit(unit, path, a.dry_run)
            if ultimo != "published":
                break
            # Esperar el espaciado antes de la siguiente.
            #
            # Sin esto el bucle no sirve de nada: una ejecución dura minutos y
            # el espaciado de recuperación son 21, así que la segunda pieza
            # siempre salía 'aplazada' a 0,0 h de la primera y el bucle moría en
            # la vuelta dos. Comprobado en la ejecución 33049310523.
            #
            # Esperar dentro del job convierte UNA ejecución superviviente en
            # varias publicaciones, que es justo lo que hace falta cuando GitHub
            # se salta horas enteras. El coste es tener el job ocupado; el grupo
            # de concurrencia ya impide que dos publiquen a la vez.
            if n + 1 < max(a.max, 1) and not a.dry_run:
                espera = variants.HORAS_MINIMAS_ATRASO * 3600 + 60
                print(f"  · esperando {espera / 60:.0f} min para respetar el espaciado")
                time.sleep(espera)
        return 0 if ultimo in ("published", "ensayo", "aplazada") else 1
    else:
        print("usa --due o --id", file=sys.stderr)
        return 1

    desenlace = publish_unit(unit, path, a.dry_run)
    # 'aplazada' no es un fallo: la cadencia dice que aún no toca y la próxima
    # ejecución lo resolverá sola. Si saliera con código 1, el workflow se
    # pintaría de rojo y el aviso saltaría cada vez, que es como se aprende a
    # ignorar los avisos.
    return 0 if desenlace in ("published", "ensayo", "aplazada") else 1


if __name__ == "__main__":
    raise SystemExit(main())
