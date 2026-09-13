"""
Qué pasa cuando Threads contesta con un error que no dice si publicó.

El 13 de septiembre threads_publish devolvió HTTP 500 «retry later». A veces el
hilo sale igual. Si el publicador se rinde, el hilo queda sin registrar y la hora
siguiente lo duplica; si reintenta a ciegas, no sabe lo que ha hecho. Aquí se
comprueba que mira en Threads antes de decidir, y que hilos.py no republica lo
que ya está publicado aunque el repo no lo tenga registrado.

    python3 tests/test_threads.py
"""
from __future__ import annotations

import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

import fake_graph  # noqa: E402
from src.platforms import meta  # noqa: E402

FALLOS: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'✓' if cond else '✗'} {msg}")
    if not cond:
        FALLOS.append(msg)


def reiniciar(**estado) -> None:
    fake_graph.STATE.update({"hilos": [], "threads_publish_500": 0, "sale_igual": False})
    fake_graph.STATE.update(estado)


def main() -> int:
    srv, base = fake_graph.start()
    meta.THREADS_GRAPH = base
    meta.time.sleep = lambda s: None
    os.environ.update({"SDB_THREADS_USER_ID": "TH", "SDB_THREADS_TOKEN": "T"})
    # Largo como los de verdad (344-381 caracteres): el enlace queda fuera de la huella.
    texto = ("«Toda licencia en el verso denuncia impotencia en el versificador: el que sabe "
             "su oficio no necesita que la lengua le perdone nada.»\n— Manuel González Prada, "
             "Pájinas libres\n\nhttps://x/cita/a?de=threads")

    print("500 y el hilo salió igual")
    reiniciar(threads_publish_500=1, sale_igual=True)
    r = meta.publish_threads(None, texto)
    check(len(fake_graph.STATE["hilos"]) == 1, "un solo hilo en Threads, no dos")
    check(r["post_id"] == "TH_POST_1", "devuelve el id del hilo que salió")

    print("500 y el hilo no salió")
    reiniciar(threads_publish_500=1)
    r = meta.publish_threads(None, texto)
    check(len(fake_graph.STATE["hilos"]) == 1, "reintenta y sale una vez")
    check(r["post_id"] == "TH_POST_1", "devuelve el id del reintento")

    print("500 en todos los intentos")
    reiniciar(threads_publish_500=meta.INTENTOS_THREADS_PUBLISH)
    try:
        meta.publish_threads(None, texto)
        check(False, "debía fallar")
    except meta.MetaError:
        check(True, "falla con MetaError")
    check(fake_graph.STATE["hilos"] == [], "y no hay nada en Threads")

    print("buscar_hilo")
    ahora = datetime.now(timezone.utc)
    reiniciar(hilos=[{"id": "VIEJO", "text": texto,
                      "timestamp": (ahora - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S+0000")}])
    check(meta.buscar_hilo(texto, ahora - timedelta(days=2)) is None,
          "no cuenta un hilo más viejo que `desde`")
    reiniciar()
    meta.publish_threads(None, texto)
    otro_enlace = texto.replace("?de=threads", "?de=otro")
    check(meta.buscar_hilo("  " + otro_enlace.replace("\n", "  \n"), ahora - timedelta(hours=1)) is not None,
          "lo encuentra aunque cambien los espacios y el enlace del final")
    check(meta.buscar_hilo("«Otra cita distinta.»", ahora - timedelta(hours=1)) is None,
          "no confunde un texto distinto")

    print("hilos._ya_en_threads")
    import hilos  # noqa: E402
    check(hilos._ya_en_threads(texto) is not None, "ve el hilo ya publicado")
    original = meta.buscar_hilo
    def sin_threads(*a, **k):
        raise meta.MetaError("HTTP 500")
    meta.buscar_hilo = sin_threads
    try:
        check(hilos._ya_en_threads(texto) is None, "si Threads no contesta, no bloquea la publicación")
    finally:
        meta.buscar_hilo = original

    srv.shutdown()
    print(f"\n{'OK' if not FALLOS else f'{len(FALLOS)} FALLOS'}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
