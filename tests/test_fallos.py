"""
Qué le pasa a una pieza cuando no sale.

Dos modos de fallo con consecuencias opuestas, y los dos eran silenciosos:

  - fallo de plataforma  -> se marcaba 'failed' y pick_due() la saltaba para
                            siempre: un error pasajero de Meta enterraba una
                            pieza verificada
  - fallo de preflight   -> se quedaba en 'ready' y pick_due() volvía a
                            elegirla en cada ejecución: la cola entera se
                            atascaba en ella y no se publicaba nada más

    python3 tests/test_fallos.py
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from src import publish  # noqa: E402

FALLOS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def pieza(pid: str, cuando: str, **kw) -> dict:
    u = {
        "id": pid, "publish_at": cuando, "slot": "tarde", "pillar": "curiosidad",
        "core": {"subject": kw.get("tema", "Tema " + pid), "hook": "Gancho",
                 "body": ["Cuerpo."], "question": "¿Pregunta?"},
        "card": {"renderer": "text_card", "variant": kw.get("variante", "cream"),
                 "title": "T", "subtitle": "S", "body": "B"},
        "tags": {"primary": "#SabiduriaDeBolsillo", "topic": kw.get("topic", ["#Uno"]),
                 "extended": []},
        "sources": [{"claim": "c", "source": "s"}],
        "targets": ["facebook"], "status": "ready", "results": {},
    }
    return u


def entorno() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sdb-fallos-"))
    publish.QUEUE = tmp / "queue"
    publish.PUBLISHED = tmp / "published"
    publish.ASSETS = tmp / "assets"
    publish.QUEUE.mkdir(parents=True)
    publish.PUBLISHED.mkdir(parents=True)
    return tmp


def main() -> int:
    print("\n1. Un problema PERMANENTE aparta la pieza y la cola avanza")
    tmp = entorno()
    mala = pieza("2026-01-01-tarde", "2026-01-01T19:00:00Z", topic=["#viral"])
    buena = pieza("2026-01-02-tarde", "2026-01-02T19:00:00Z", variante="gold")
    pm = publish.QUEUE / "mala.json"
    pb = publish.QUEUE / "buena.json"
    pm.write_text(json.dumps(mala), encoding="utf-8")
    pb.write_text(json.dumps(buena), encoding="utf-8")

    elegida, ruta = publish.pick_due()
    check(elegida["id"] == mala["id"], "pick_due elige primero la vencida más antigua")
    publish.publish_unit(elegida, ruta)
    tras = json.loads(pm.read_text(encoding="utf-8"))
    check(tras["status"] == "blocked", "la pieza con etiqueta prohibida queda 'blocked'")
    check(bool(tras.get("blocked_reason")), "queda registrado el motivo")

    otra, _ = publish.pick_due()
    check(otra is not None and otra["id"] == buena["id"],
          "la cola AVANZA: la siguiente ejecución elige otra pieza")
    shutil.rmtree(tmp, ignore_errors=True)

    print("\n2. Un problema TRANSITORIO no aparta nada: se reintenta")
    # Tiempos relativos a AHORA: al publicar de verdad la cadencia se mide
    # contra el reloj real, así que un historial fechado en enero no la activa.
    tmp = entorno()
    publish.upload_asset = lambda x: "https://example.invalid/x.png"
    hace_2h = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # temas bien distintos: si comparten palabras salta la regla de repeticion
    ya = pieza("2026-01-01-manana", hace_2h, tema="Los quipus incas")
    ya["status"] = "published"
    ya["results"] = {"facebook": {"post_id": "X", "published_at": hace_2h}}
    (publish.PUBLISHED / "ya.json").write_text(json.dumps(ya), encoding="utf-8")
    pegada = pieza("2026-01-01-tarde", hace_2h, variante="gold",
                   tema="Hipatia de Alejandria")
    pp = publish.QUEUE / "pegada.json"
    pp.write_text(json.dumps(pegada), encoding="utf-8")

    ok = publish.publish_unit(json.loads(pp.read_text(encoding="utf-8")), pp)
    tras = json.loads(pp.read_text(encoding="utf-8"))
    check(ok == "aplazada", "a 2 h de la anterior queda aplazada, no fallida")
    check(tras["status"] == "ready", "sigue en 'ready': se reintentará")
    check("blocked_reason" not in tras, "no se le pone motivo de bloqueo")
    shutil.rmtree(tmp, ignore_errors=True)

    print("\n3. Un fallo de plataforma se reintenta y no se entierra")
    tmp = entorno()
    import fake_graph_shim  # noqa: F401
    p = pieza("2026-01-01-tarde", "2026-01-01T19:00:00Z")
    ruta = publish.QUEUE / "p.json"
    ruta.write_text(json.dumps(p), encoding="utf-8")
    publish.upload_asset = lambda x: "https://example.invalid/x.png"

    def revienta(*_a, **_k):
        raise RuntimeError("Meta se cayó")

    from src.platforms import meta
    original = dict(meta.PUBLISHERS)
    meta.PUBLISHERS["facebook"] = revienta
    try:
        for intento in (1, 2):
            publish.publish_unit(json.loads(ruta.read_text(encoding="utf-8")), ruta)
            tras = json.loads(ruta.read_text(encoding="utf-8"))
            check(tras["attempts"] == intento, f"registra el intento {intento}")
            check(tras["status"] == "ready",
                  f"tras el intento {intento} sigue en cola, no enterrada")
            check(publish.pick_due()[0] is not None,
                  f"pick_due la vuelve a encontrar tras el intento {intento}")
        # tercer intento: se agota
        publish.publish_unit(json.loads(ruta.read_text(encoding="utf-8")), ruta)
        tras = json.loads(ruta.read_text(encoding="utf-8"))
        check(tras["status"] == "blocked",
              f"al llegar a {publish.MAX_INTENTOS} intentos se aparta")
        check("Meta se cayó" in " ".join(tras["blocked_reason"]),
              "el motivo guarda el error real de la plataforma")
    finally:
        meta.PUBLISHERS.clear()
        meta.PUBLISHERS.update(original)
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("Ningún modo de fallo entierra una pieza ni atasca la cola.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
