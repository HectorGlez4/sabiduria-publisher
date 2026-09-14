"""
Pruebas del laboratorio de medios (experiments/media-lab/).

    .venv/bin/python tests/test_media_lab.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments" / "media-lab"))

FALLOS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        FALLOS.append(label)


def seccion_portapapeles() -> None:
    print("\n1. SET_CLIPBOARD con los mismos bytes que el test de scrcpy 4.1")
    import phone_clipboard

    esperado = bytes([9, 1, 2, 3, 4, 5, 6, 7, 8, 1, 0, 0, 0, 13]) + b"hello, world!"
    obtenido = phone_clipboard.set_clipboard_message(
        "hello, world!", paste=True, sequence=0x0102030405060708)
    check(obtenido == esperado, "mensaje idéntico al de test_control_msg_serialize.c")
    msg = phone_clipboard.set_clipboard_message("¿Qué?", paste=False)
    check(msg[9] == 0, "paste=False va como 0")
    check(int.from_bytes(msg[10:14], "big") == 7,
          "la longitud cuenta bytes UTF-8 (7), no caracteres (5)")

    import shutil
    import subprocess
    if shutil.which("scrcpy"):
        partes = subprocess.run(["scrcpy", "--version"], capture_output=True, text=True,
                                timeout=30).stdout.split()
        instalada = partes[1] if len(partes) > 1 else "?"
        check(instalada == phone_clipboard.SCRCPY_VERSION,
              f"scrcpy instalado ({instalada}) coincide con el protocolo fijado "
              f"({phone_clipboard.SCRCPY_VERSION})")
        check(pathlib.Path(phone_clipboard.SERVER_LOCAL).is_file(),
              "existe el scrcpy-server que se sube al teléfono")
    else:
        print("  · scrcpy no está instalado: se omite la comprobación de versión")


def seccion_encargos() -> None:
    print("\n2. Encargos: estados, bloqueos y archivo")
    import json
    import tempfile
    from datetime import datetime, timedelta, timezone
    from labkit import encargos as E

    t0 = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)

    def base(encargo_id: str = "ENC-20260915-001", variantes: int = 1) -> dict:
        return E.nuevo(
            encargo_id, coverage_cell_ids=["CELL-011"], family_id="LAB-F01-001",
            brief_path="experiments/media-lab/briefs/LAB-F01-001.md", do_not_use=[],
            formato={"nativo": "feed_single_image", "ancho": 1080, "alto": 1350},
            prompt="Un astrolabio de latón sobre una mesa de madera", restricciones=["sin texto"],
            destino_assets="experiments/media-lab/assets/LAB-F01-001", variantes=variantes, ahora=t0)

    img = [{"ruta": "experiments/media-lab/assets/LAB-F01-001/ENC-20260915-001-v1.png",
            "sha256": "ab", "ancho": 1024, "alto": 1536}]

    e = base()
    check(e["estado"] == "pedido" and E.tomable(e, t0), "un encargo nuevo está en pedido y se puede tomar")
    E.tomar(e, "codex-heartbeat", t0)
    check(e["estado"] == "generando" and not E.tomable(e, t0 + timedelta(minutes=29)),
          "con el bloqueo vigente nadie más lo toma")
    check(E.tomable(e, t0 + timedelta(minutes=31)), "un bloqueo vencido se puede retomar")
    try:
        E.marcar_generado(e, "codex-exec", img, t0)
        ok = False
    except E.EncargoError:
        ok = True
    check(ok, "solo el dueño del bloqueo marca generado")
    E.marcar_generado(e, "codex-heartbeat", img, t0)
    check(e["estado"] == "generado" and e["lock_owner"] is None
          and e["imagenes"][0]["origen"] == "codex-heartbeat",
          "generado limpia el bloqueo y anota el origen")
    try:
        E.revisar(e, aprobado=False, motivo="texto espurio", ahora=t0)
        ok = False
    except E.EncargoError:
        ok = True
    check(ok, "un rechazo exige la corrección")
    E.revisar(e, aprobado=False, motivo="texto espurio", ahora=t0,
              correccion="ninguna letra ni número en la imagen")
    check(e["estado"] == "pedido" and "ninguna letra ni número en la imagen" in e["restricciones"]
          and e["imagenes"] == []
          and [i["ruta"] for i in e["intentos"][-1]["imagenes_rechazadas"]] == [img[0]["ruta"]],
          "un rechazo con intentos restantes vuelve a pedido con la corrección")
    E.tomar(e, "codex-exec", t0)
    E.marcar_fallo(e, "codex-exec", "sin imagen", t0)
    check(e["estado"] == "bloqueado", "al agotar 2 intentos queda bloqueado")

    e2 = base()
    E.tomar(e2, "codex-heartbeat", t0)
    E.marcar_generado(e2, "codex-heartbeat", img, t0)
    E.revisar(e2, aprobado=True, motivo="verosímil y sin texto", ahora=t0)
    E.marcar_usado(e2, "LAB-F01-001-A-INSTAGRAM")
    check(e2["estado"] == "usado" and e2["runs"] == ["LAB-F01-001-A-INSTAGRAM"],
          "aprobado pasa a usado con su run")
    check(E.en_cola([base(), e2, e]) == 1, "en_cola cuenta solo pedido y generando")

    comunes = dict(coverage_cell_ids=["C"], family_id="F", brief_path="b", do_not_use=[],
                   formato={}, prompt="p", restricciones=[],
                   destino_assets="experiments/media-lab/assets/F", ahora=t0)
    for eid, cambio, label in (("X-1", {}, "id sin ENC-"),
                               ("ENC-20260915-009", {"variantes": 3}, "3 variantes"),
                               ("ENC-20260915-009", {"destino_assets": "/tmp"}, "destino fuera de assets")):
        try:
            E.nuevo(eid, **{**comunes, **cambio})
            ok = False
        except E.EncargoError:
            ok = True
        check(ok, f"rechaza un encargo inválido: {label}")

    with tempfile.TemporaryDirectory() as d:
        carpeta = pathlib.Path(d)
        check(E.siguiente_id(carpeta, t0) == "ENC-20260915-001", "el primer id del día es 001")
        E.guardar(carpeta / "ENC-20260915-001.json", base())
        check(E.siguiente_id(carpeta, t0) == "ENC-20260915-002", "el siguiente id incrementa")
        leido = E.cargar(carpeta / "ENC-20260915-001.json")
        check(leido["prompt"].startswith("Un astrolabio"), "guardar y cargar conservan el contenido")
        check(json.loads((carpeta / "ENC-20260915-001.json").read_text(encoding="utf-8"))["estado"] == "pedido",
              "el archivo es JSON legible")
        check([e["encargo_id"] for _, e in E.listar(carpeta)] == ["ENC-20260915-001"],
              "listar devuelve los encargos del directorio")

    print("   · endurecimiento tras la revisión de calidad")

    def falla(accion) -> bool:
        try:
            accion()
            return False
        except E.EncargoError:
            return True

    check(e["revision"] is None and e["intentos"][0]["revision"]["motivo"] == "texto espurio",
          "la revisión de un rechazo queda en su intento, no en el encargo")
    e3 = base()
    E.tomar(e3, "codex-heartbeat", t0)
    check(falla(lambda: E.tomar(base(), "otro", t0)), "tomar con un dueño desconocido falla")
    check(falla(lambda: E.tomar(e3, "codex-exec", t0 + timedelta(minutes=5))), "tomar un bloqueo vigente falla")
    E.tomar(e3, "codex-exec", t0 + timedelta(minutes=31))
    check(falla(lambda: E.marcar_generado(e3, "codex-heartbeat", img, t0 + timedelta(minutes=32))),
          "tras robar un bloqueo vencido, el dueño anterior ya no puede marcar generado")
    e4 = base()
    E.tomar(e4, "codex-exec", t0)
    E.marcar_fallo(e4, "codex-exec", "tiempo agotado", t0)
    check(e4["estado"] == "pedido" and e4["lock_owner"] is None, "un fallo con intentos restantes vuelve a pedido")

    v2 = dict(img[0], ruta="experiments/media-lab/assets/LAB-F01-001/ENC-20260915-001-v2.png")
    v3 = dict(img[0], ruta="experiments/media-lab/assets/LAB-F01-001/ENC-20260915-001-v3.png")
    fuera = dict(img[0], ruta="experiments/media-lab/assets/OTRA/ENC-20260915-001-v1.png")
    for label, imagenes in (("más imágenes que variantes", [img[0], v2, v3]),
                            ("rutas repetidas", [img[0], img[0]]),
                            ("imagen fuera de destino_assets", [fuera]),
                            ("ruta que escapa con ..", [dict(img[0], ruta="experiments/media-lab/assets/LAB-F01-001/../../../../src/x.png")])):
        e5 = base(variantes=2)
        E.tomar(e5, "codex-heartbeat", t0)
        check(falla(lambda: E.marcar_generado(e5, "codex-heartbeat", imagenes, t0)),
              f"marcar_generado rechaza: {label}")

    check(falla(lambda: E.nuevo("ENC-20260915-010", **{**comunes, "destino_assets": "experiments/media-lab/assets/OTRA"})),
          "nuevo exige destino_assets = assets/<family_id>")
    check(falla(lambda: E.nuevo("ENC-20260915-011", **{**comunes, "family_id": "..",
                                                       "destino_assets": "experiments/media-lab/assets/.."})),
          "nuevo rechaza un family_id que escapa de assets")
    check(falla(lambda: E.nuevo("ENC-20260915-012", **{**comunes, "ahora": datetime(2026, 9, 15, 8, 0)})),
          "nuevo rechaza una fecha sin zona horaria")

    with tempfile.TemporaryDirectory() as d:
        carpeta = pathlib.Path(d)
        (carpeta / "ENC-20260915-abc.json").write_text("{}", encoding="utf-8")
        (carpeta / "ENC-20260915-004.json").write_text("{}", encoding="utf-8")
        check(E.siguiente_id(carpeta, t0) == "ENC-20260915-005",
              "siguiente_id ignora sufijos no numéricos y sigue al mayor")
    with tempfile.TemporaryDirectory() as d:
        carpeta = pathlib.Path(d)
        E.guardar(carpeta / "ENC-20260915-001.json", base())
        check(list(carpeta.glob(".*.tmp")) == [], "guardar no deja temporales")
        (carpeta / "ENC-20260915-002.json").write_text("{", encoding="utf-8")
        try:
            E.listar(carpeta)
            mensaje = ""
        except E.EncargoError as err:
            mensaje = str(err)
        check("ENC-20260915-002.json" in mensaje, "un encargo ilegible da un error que nombra el archivo")

    with tempfile.TemporaryDirectory() as d:
        carpeta = pathlib.Path(d)
        (carpeta / "ENC-20260915-001.json").write_text("{}", encoding="utf-8")
        try:
            E.listar(carpeta)
            mensaje = ""
        except E.EncargoError as err:
            mensaje = str(err)
        check("ENC-20260915-001.json" in mensaje and "incompleto" in mensaje,
              "un JSON válido pero sin campos da un error que nombra el archivo")


SECCIONES = [
    seccion_portapapeles,
    seccion_encargos,
]


def main() -> int:
    for seccion in SECCIONES:
        seccion()
    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El laboratorio cumple sus contratos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
