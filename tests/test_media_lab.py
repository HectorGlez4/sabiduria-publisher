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


def seccion_colision() -> None:
    print("\n3. Colisión con producción")
    import json
    import tempfile
    from datetime import datetime, timedelta, timezone
    from labkit import colision as C

    t = datetime(2026, 9, 15, 8, 40, tzinfo=timezone.utc)
    m = lambda n: timedelta(minutes=n)  # noqa: E731
    check(C.motivo_espera(t, programadas=[], publicadas=[], en_curso=[]) is None, "sin nada cerca se publica")
    check("publicar" in (C.motivo_espera(t, programadas=[], publicadas=[], en_curso=["publicar"]) or ""),
          "si publicar está en curso se espera")
    check(C.motivo_espera(t, programadas=[], publicadas=[], en_curso=["pages build and deployment"]) is None,
          "otros workflows no bloquean")
    check(C.motivo_espera(t, programadas=[], publicadas=[t - m(20)], en_curso=[]) is not None,
          "una publicación de hace 20 min bloquea")
    check(C.motivo_espera(t, programadas=[], publicadas=[t - m(22)], en_curso=[]) is None,
          "una de hace 22 min no bloquea")
    check(C.motivo_espera(t, programadas=[t + m(15)], publicadas=[], en_curso=[]) is not None,
          "una programada dentro de 15 min bloquea")
    check(C.motivo_espera(t, programadas=[t + m(40)], publicadas=[], en_curso=[]) is None,
          "una programada dentro de 40 min no bloquea")
    check("atrasada" in (C.motivo_espera(t, programadas=[t - m(90)], publicadas=[], en_curso=[]) or ""),
          "una pieza atrasada en la cola puede salir en cualquier momento: bloquea")

    with tempfile.TemporaryDirectory() as d:
        cola = pathlib.Path(d) / "queue"
        pub = pathlib.Path(d) / "published"
        cola.mkdir()
        pub.mkdir()
        (cola / "a.json").write_text(json.dumps({"status": "ready", "publish_at": "2026-09-15T08:50:00Z"}))
        (cola / "b.json").write_text(json.dumps({"status": "draft", "publish_at": "2026-09-15T08:45:00Z"}))
        (pub / "c.json").write_text(json.dumps({"results": {
            "facebook": {"published_at": "2026-09-15T08:30:00+00:00"},
            "threads": {"published_at": "2026-09-15T08:35:00+00:00"}}}))
        progs = C.programadas_de_cola(cola)
        check(progs == [datetime(2026, 9, 15, 8, 50, tzinfo=timezone.utc)], "solo cuentan las piezas ready de la cola")
        pubs = C.publicadas_recientes(pub, t)
        check(datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc) in pubs, "lee published_at de results")
        check(all(p <= t for p in pubs), "no devuelve publicaciones futuras")


def seccion_seleccion() -> None:
    print("\n4. Selección de hasta 2 celdas")
    from labkit import seleccion as S

    def celda(cid, plataforma, formato, ruta, estado="planned"):
        return {"cell_id": cid, "platform": plataforma, "native_format": formato,
                "publishing_route": ruta, "status": estado}

    def aprobado(*cids):
        return {"estado": "aprobado", "coverage_cell_ids": list(cids)}

    celdas = [
        celda("C1", "instagram", "feed_single_image", "android_native"),
        celda("C2", "facebook", "feed_single_image", "api"),
        celda("C3", "instagram", "feed_single_image", "android_native"),
        celda("C4", "threads", "feed_single_image", "api"),
        celda("C5", "instagram", "story_image", "android_native"),
        celda("C6", "threads", "feed_single_image", "api", estado="published"),
    ]
    todos = [aprobado("C1", "C2", "C3", "C4", "C5", "C6")]
    elegidas = [c["cell_id"] for c in S.elegir(celdas, todos)]
    check(elegidas == ["C1", "C4"],
          "tras Instagram por teléfono no sale Facebook (copia automática) ni otra celda igual")
    check([c["cell_id"] for c in S.elegir(celdas, [aprobado("C5")])] == [],
          "en la fase 1 el teléfono solo publica el feed de Instagram")
    check([c["cell_id"] for c in S.elegir(celdas, [aprobado("C6")])] == [],
          "una celda ya publicada no es elegible")
    check([c["cell_id"] for c in S.elegir(celdas, [{"estado": "generado", "coverage_cell_ids": ["C1"]}])] == [],
          "sin encargo aprobado no hay celda")
    check(len(S.elegir(celdas, todos, max_celdas=1)) == 1, "respeta max_celdas")
    ids = lambda sel: [c["cell_id"] for c in sel]  # noqa: E731
    check(ids(S.elegir([celda("C9", "instagram", "feed_single_image", "manual")], [aprobado("C9")])) == [],
          "una ruta desconocida no es elegible")
    check(ids(S.elegir([celda("C8", "threads", "feed_single_image", "api", estado="ready")], [aprobado("C8")])) == ["C8"],
          "una celda ready es elegible")
    check(ids(S.elegir([celda("C8", "threads", "feed_single_image", "api", estado="blocked")], [aprobado("C8")])) == [],
          "una celda blocked no es elegible")
    check(ids(S.elegir([celdas[1], celdas[0], celdas[3]], todos)) == ["C2", "C4"],
          "Facebook primero también excluye Instagram por teléfono")
    ig_api = celda("C10", "instagram", "feed_single_image", "api")
    check(ids(S.elegir([celdas[0], ig_api], [aprobado("C1", "C10")])) == ["C1", "C10"],
          "la misma red por rutas distintas sí es compatible")
    check(ids(S.elegir([celda("C11", "instagram", "feed_carousel", "api")], [aprobado("C11")])) == [],
          "la API solo publica imágenes sueltas en la fase 1 (carrusel fuera)")
    check(ids(S.elegir(celdas, [{"estado": "usado", "coverage_cell_ids": ["C1", "C4"]}])) == ["C1", "C4"],
          "un encargo ya usado sigue sirviendo para sus celdas sin publicar")
    check(ids(S.elegir(celdas, todos, telefono_listo=False)) == ["C2", "C4"],
          "sin teléfono listo no se elige ninguna celda de teléfono y Facebook vuelve a ser posible")
    check(S.elegir(celdas, todos, max_celdas=0) == [], "max_celdas=0 no devuelve nada")


def seccion_manifiesto_y_cerrojo() -> None:
    print("\n5. Manifiestos API y cerrojo de ventana")
    import tempfile
    from datetime import datetime, timedelta, timezone
    from labkit import cerrojo, manifiesto as M

    asset = "experiments/media-lab/assets/LAB-F01-001/master-4x5.jpg"
    S = "ab" * 32
    m = M.manifiesto_api("LAB-F01-001-API", asset, S,
                         {"facebook": "Pie FB", "threads": "Pie Threads"}, family_id="LAB-F01-001")
    check(m["route"] == "api" and m["audience"] == "public", "ruta api y audiencia pública explícitas")
    check(m["asset_url"] == M.RAW_BASE + asset, "asset_url apunta al raw de main")
    check(m["platforms"] == ["facebook", "threads"], "platforms sale de los pies")
    check(M.ruta_manifiesto("LAB-F01-001-API") == "experiments/media-lab/manifests/LAB-F01-001-API.json",
          "ruta que acepta el workflow media-lab")
    for args, label in ((("X-1", asset, S, {"facebook": "p"}), "run_group sin LAB-"),
                        (("LAB-a b;rm", asset, S, {"facebook": "p"}), "run_group con caracteres raros"),
                        (("LAB-../../x", asset, S, {"facebook": "p"}), "run_group que escapa de manifests"),
                        (("LAB-X", "/tmp/a.jpg", S, {"facebook": "p"}), "asset fuera de assets"),
                        (("LAB-X", "experiments/media-lab/assets/../../src/x.jpg", S, {"facebook": "p"}), "asset con .."),
                        (("LAB-X", asset, "", {"facebook": "p"}), "sha256 vacío"),
                        (("LAB-X", asset, S, {"tiktok": "p"}), "plataforma sin publicador"),
                        (("LAB-X", asset, S, {"threads": "x" * 501}), "Threads de más de 500"),
                        (("LAB-X", asset, S, {"instagram": "x" * 2201}), "Instagram de más de 2200"),
                        (("LAB-X", asset, S, {"facebook": ""}), "pie vacío"),
                        (("LAB-X", asset, S, {"facebook": "p", "facebook_story": ""}), "feed y story mezclados")):
        try:
            M.manifiesto_api(*args)
            ok = False
        except M.ManifiestoError:
            ok = True
        check(ok, f"rechaza: {label}")

    t = datetime(2026, 9, 15, 8, 40, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as d:
        lock = pathlib.Path(d) / ".ventana.lock"
        check(cerrojo.tomar(lock, t, "programada"), "el cerrojo libre se toma")
        check(not cerrojo.tomar(lock, t + timedelta(minutes=30), "manual"), "un cerrojo de 30 min no se pisa")
        check(cerrojo.tomar(lock, t + timedelta(minutes=91), "manual"), "un cerrojo de más de 90 min se considera abandonado")
        cerrojo.soltar(lock, "manual")
        check(not lock.exists(), "soltar borra el cerrojo")

    check(M.manifiesto_api("LAB-X", asset, S, {"threads": "x" * 500})["captions"]["threads"] == "x" * 500,
          "un pie de Threads de 500 exactos se acepta")
    hist = M.manifiesto_api("LAB-X-STORY", asset, S, {"facebook_story": "", "instagram_story": "ignorado"})
    check(hist["captions"] == {"facebook_story": "", "instagram_story": ""},
          "las historias se publican sin pie")
    check("family_id" not in M.manifiesto_api("LAB-X", asset, S, {"facebook": "p"}), "sin family_id no se añade la clave")
    v = M.manifiesto_verificacion("LAB-F01-001-API", {"facebook": "123_456", "threads": "789"})
    check(v == {"run_group_id": "LAB-F01-001-API", "post_ids": {"facebook": "123_456", "threads": "789"}},
          "manifiesto de verificación con las redes publicadas")
    check(M.ruta_verificacion("LAB-F01-001-API") == "experiments/media-lab/manifests/LAB-F01-001-API-verify.json",
          "la verificación no pisa el manifiesto de publicación")
    for post_ids, label in (({}, "sin post_ids"), ({"tiktok": "1"}, "red no verificable"), ({"facebook": ""}, "post_id vacío")):
        try:
            M.manifiesto_verificacion("LAB-X", post_ids)
            ok = False
        except M.ManifiestoError:
            ok = True
        check(ok, f"verificación rechaza: {label}")

    with tempfile.TemporaryDirectory() as d:
        lock = pathlib.Path(d) / ".ventana.lock"
        for contenido, label in (("[1]", "lista"), ('{"desde": 5}', "desde no textual"), ("no json", "texto")):
            lock.write_text(contenido, encoding="utf-8")
            check(cerrojo.tomar(lock, t, "programada"), f"un cerrojo corrupto ({label}) se trata como abandonado")
        lock.write_text('{"dueno": "manual", "desde": "2026-09-15T08:20:00"}', encoding="utf-8")
        check(not cerrojo.tomar(lock, t, "programada"), "un cerrojo reciente sin zona horaria bloquea sin romper")
        check(cerrojo.tomar(lock, t, "manual"), "el mismo dueño renueva su cerrojo")
        check(not cerrojo.soltar(lock, "programada") and lock.exists(), "otro dueño no suelta el cerrojo")
        lock.write_text('{"dueno": "manual", "desde": "2026-09-15T10:00:00+00:00"}', encoding="utf-8")
        check(cerrojo.tomar(lock, t, "programada"), "un cerrojo con fecha futura se trata como abandonado")
        check(list(pathlib.Path(d).glob(".*.tmp")) == [], "tomar no deja temporales")
        check(not cerrojo.soltar(pathlib.Path(d) / "no-existe.lock", "manual"), "soltar sin cerrojo no rompe")


SECCIONES = [
    seccion_portapapeles,
    seccion_encargos,
    seccion_colision,
    seccion_seleccion,
    seccion_manifiesto_y_cerrojo,
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
