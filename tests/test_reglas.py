"""
Casos negativos de las tres reglas editoriales que dependen del historial.

Cada regla tiene su caso que DEBE fallar y su caso que DEBE pasar. Un test que
solo comprueba el camino bueno no demuestra que la regla bloquee nada.

    python3 tests/test_reglas.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone  # noqa: E402

from src import variants  # noqa: E402

FALLOS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def pieza(pid: str, cuando: str, *, tema: str = "Tema cualquiera",
          variante: str = "cream", cita: str | None = None) -> dict:
    u = {
        "id": pid,
        "publish_at": cuando,
        "slot": "tarde",
        "pillar": "curiosidad",
        "core": {"subject": tema, "hook": "Un gancho", "body": ["Un cuerpo."],
                 "question": "¿Una pregunta?"},
        "card": {"renderer": "text_card", "variant": variante,
                 "title": "T", "subtitle": "S", "body": "B"},
        "tags": {"primary": "#SabiduriaDeBolsillo", "topic": ["#Uno"], "extended": []},
        "sources": [{"claim": "algo", "source": "alguna fuente"}],
        "targets": ["facebook"],
        "status": "ready",
        "results": {},
    }
    if cita:
        u["core"]["quote"] = {"text": cita, "author": "Alguien",
                              "attribution_verified": True}
        u["card"]["renderer"] = "quote_card"
    return u


def publicada(pid: str, cuando: str, **kw) -> dict:
    u = pieza(pid, cuando, **kw)
    u["status"] = "published"
    u["results"] = {"facebook": {"post_id": "X", "published_at": cuando}}
    return u


def tiene(problemas: list[str], fragmento: str) -> bool:
    return any(fragmento in p for p in problemas)


def main() -> int:
    print("\n1. Sin historial no se bloquea nada (la primera publicación)")
    u = pieza("2026-09-01-tarde", "2026-09-01T19:00:00Z")
    check(variants.preflight(u, []) == [], "una pieza limpia pasa sin historial")

    print("\n2. Máximo 3 al día, en hora de CDMX")
    dia = [publicada(f"2026-09-01-{s}", h) for s, h in
           [("manana", "2026-09-01T14:00:00Z"), ("tarde", "2026-09-01T19:00:00Z"),
            ("noche", "2026-09-02T01:30:00Z")]]
    # 01:30 UTC del 2 es todavia el 1 en CDMX: la cuarta del mismo dia
    cuarta = pieza("2026-09-02-extra", "2026-09-02T02:00:00Z")
    p = variants.preflight(cuarta, dia)
    check(tiene(p, "maximo es 3 al dia"), "una cuarta el mismo día CDMX se bloquea")
    otra = pieza("2026-09-02-manana", "2026-09-02T14:00:00Z", variante="gold")
    check(not tiene(variants.preflight(otra, dia), "maximo es 3"),
          "la primera del día siguiente pasa")

    print("\n3. Mínimo 4 horas entre publicaciones")
    hist = [publicada("2026-09-01-tarde", "2026-09-01T19:00:00Z")]
    pegada = pieza("2026-09-01-noche", "2026-09-01T21:00:00Z", variante="gold")
    check(tiene(variants.preflight(pegada, hist), "minimo son 4 horas"),
          "a 2 h de la anterior se bloquea")
    separada = pieza("2026-09-02-noche", "2026-09-02T01:30:00Z", variante="gold")
    check(not tiene(variants.preflight(separada, hist), "minimo son 4 horas"),
          "a 6,5 h pasa")

    print("\n3b. La cadencia mide la hora REAL, no la programada")
    hist = [publicada("2026-09-01-tarde", "2026-09-01T19:00:00Z")]
    # programada a 6,5 h: sobre el papel esta bien
    tarde = pieza("2026-09-02-noche", "2026-09-02T01:30:00Z", variante="gold")
    check(not tiene(variants.preflight(tarde, hist), "minimo son 4 horas"),
          "a su hora prevista pasa")
    # pero si se fuerza media hora despues de la anterior, no
    forzada = datetime(2026, 9, 1, 19, 30, tzinfo=timezone.utc)
    check(tiene(variants.preflight(tarde, hist, forzada), "minimo son 4 horas"),
          "forzada 30 min despues de la anterior se bloquea")

    print("\n4. Sin repetir tema ni cita en 90 días")
    hist = [publicada("2026-08-01-tarde", "2026-08-01T19:00:00Z",
                      tema="Séneca y el tiempo que se pierde")]
    repe = pieza("2026-09-01-tarde", "2026-09-01T19:00:00Z",
                 tema="Séneca — el tiempo perdido", variante="gold")
    check(tiene(variants.preflight(repe, hist), "tema repetido"),
          "el mismo tema con otras palabras se detecta")
    lejos = pieza("2027-01-01-tarde", "2027-01-01T19:00:00Z",
                  tema="Séneca — el tiempo perdido", variante="gold")
    check(not tiene(variants.preflight(lejos, hist), "tema repetido"),
          "pasados 90 días deja de bloquear")
    distinto = pieza("2026-09-01-tarde", "2026-09-01T19:00:00Z",
                     tema="Los quipus incas y la contabilidad", variante="gold")
    check(not tiene(variants.preflight(distinto, hist), "tema repetido"),
          "un tema distinto no da falso positivo")

    hq = [publicada("2026-08-01-tarde", "2026-08-01T19:00:00Z",
                    cita="No tenemos poco tiempo: hemos perdido mucho.")]
    mismaq = pieza("2026-09-01-tarde", "2026-09-01T19:00:00Z",
                   tema="Otro tema del todo", variante="gold",
                   cita="No tenemos poco tiempo; ¡hemos perdido mucho!")
    check(tiene(variants.preflight(mismaq, hq), "cita ya publicada"),
          "la misma cita con otra puntuación se detecta")

    print("\n5. Alternancia contra la ÚLTIMA PUBLICACIÓN REAL")
    hist = [
        publicada("2026-08-01-tarde", "2026-08-01T19:00:00Z", variante="cream"),
        publicada("2026-08-05-tarde", "2026-08-05T19:00:00Z", variante="gold"),
    ]
    # la ultima real es 'gold': otra 'gold' encadena dos doradas
    mala = pieza("2026-09-01-tarde", "2026-09-01T19:00:00Z",
                 tema="Un tema nuevo", variante="gold")
    check(tiene(variants.preflight(mala, hist), "repetida"),
          "encadenar dos doradas se bloquea")
    buena = pieza("2026-09-01-tarde", "2026-09-01T19:00:00Z",
                  tema="Un tema nuevo", variante="cream")
    check(not tiene(variants.preflight(buena, hist), "repetida"),
          "alternar pasa")
    # y se mide contra la ULTIMA, no contra la primera del historial
    check(tiene(variants.preflight(
        pieza("2026-09-01-tarde", "2026-09-01T19:00:00Z", tema="Otro", variante="gold"),
        hist), "2026-08-05-tarde"),
        "el mensaje señala la última real, no una anterior")

    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("Las tres reglas bloquean lo que deben y dejan pasar lo que deben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
