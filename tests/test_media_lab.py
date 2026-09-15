"""
Pruebas del laboratorio de medios (experiments/media-lab/).

    .venv/bin/python tests/test_media_lab.py
"""
from __future__ import annotations

import contextlib
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
                   formato={"ancho": 1080, "alto": 1350}, prompt="p", restricciones=[],
                   destino_assets="experiments/media-lab/assets/F", ahora=t0)
    check(E.nuevo("ENC-20260915-009", **comunes)["estado"] == "pedido",
          "los datos comunes de estas pruebas son válidos (cada rechazo se debe solo a su cambio)")
    for eid, cambio, label in (("X-1", {}, "id sin ENC-"),
                               ("ENC-20260915-009", {"variantes": 3}, "3 variantes"),
                               ("ENC-20260915-009", {"destino_assets": "/tmp"}, "destino fuera de assets"),
                               ("ENC-20260915-009", {"formato": {}}, "formato sin ancho ni alto"),
                               ("ENC-20260915-009", {"formato": [1080, 1350]}, "formato que no es un objeto"),
                               ("ENC-20260915-009", {"formato": {"ancho": "1080", "alto": 1350}}, "ancho no entero"),
                               ("ENC-20260915-009", {"formato": {"ancho": True, "alto": 1350}}, "ancho booleano"),
                               ("ENC-20260915-009", {"formato": {"ancho": 1080, "alto": 0}}, "alto no positivo"),
                               ("ENC-20260915-009", {"prompt": "  \n"}, "prompt vacío")):
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
    e4b = base()
    E.tomar(e4b, "codex-exec", t0)
    try:
        E.marcar_fallo(e4b, "codex-exec", "Codex cambió .env", t0, bloquear=True)
    except TypeError:
        pass
    check(e4b["estado"] == "bloqueado" and e4b["lock_owner"] is None and e4b["lock_expira"] is None
          and len(e4b["intentos"]) == 1 and e4b["intentos"][0]["resultado"] == "fallo"
          and e4b["intentos"][0]["nota"] == "Codex cambió .env",
          f"marcar_fallo con bloquear queda bloqueado aunque queden intentos, con el intento anotado ({e4b['estado']})")

    print("   · invalidar lo que dejó generado codex exec")
    if not hasattr(E, "invalidar"):
        check(False, "encargos.invalidar existe")
    else:
        e6 = base()
        E.tomar(e6, "codex-exec", t0)
        E.marcar_generado(e6, "codex-exec", img, t0)
        E.invalidar(e6, "Codex cambió .env", t0)
        check(e6["estado"] == "pedido" and e6["imagenes"] == [] and e6["lock_owner"] is None
              and [i["ruta"] for i in e6["intentos"][-1].get("imagenes_invalidas", [])] == [img[0]["ruta"]]
              and e6["intentos"][-1].get("nota") == "Codex cambió .env",
              "invalidar con intentos restantes vuelve a pedido y guarda las imágenes y la nota en el intento")
        e7 = base()
        E.tomar(e7, "codex-exec", t0)
        E.marcar_generado(e7, "codex-exec", img, t0)
        E.invalidar(e7, "archivos ajenos", t0, bloquear=True)
        check(e7["estado"] == "bloqueado" and e7["imagenes"] == [], "invalidar con bloquear deja el encargo bloqueado")
        e8 = base()
        E.tomar(e8, "codex-exec", t0)
        E.marcar_fallo(e8, "codex-exec", "sin imagen", t0)
        E.tomar(e8, "codex-exec", t0)
        E.marcar_generado(e8, "codex-exec", img, t0)
        E.invalidar(e8, "hash distinto", t0)
        check(e8["estado"] == "bloqueado", "invalidar con los intentos agotados bloquea")
        e9 = base()
        E.tomar(e9, "codex-heartbeat", t0)
        E.marcar_generado(e9, "codex-heartbeat", img, t0)
        check(falla(lambda: E.invalidar(e9, "x", t0)) and e9["estado"] == "generado",
              "invalidar no toca lo generado por el heartbeat")
        check(falla(lambda: E.invalidar(base(), "x", t0)), "invalidar exige un encargo generado")
        e10 = base()
        E.tomar(e10, "codex-exec", t0)
        E.marcar_generado(e10, "codex-exec", img, t0)
        E.revisar(e10, aprobado=True, motivo="ok", ahora=t0)
        check(falla(lambda: E.invalidar(e10, "x", t0)) and e10["estado"] == "aprobado",
              "invalidar no toca un encargo ya aprobado")

    print("   · liberar lo que codex exec tomó sin llegar a lanzar Codex (G-1)")
    if not hasattr(E, "liberar"):
        check(False, "encargos.liberar existe")
    else:
        e11 = base()
        E.tomar(e11, "codex-exec", t0)
        E.liberar(e11, "codex-exec")
        check(e11["estado"] == "pedido" and e11["lock_owner"] is None and e11["lock_expira"] is None
              and e11["intentos"] == [], "liberar devuelve el encargo a pedido sin sumar intento y suelta el bloqueo")
        e12 = base()
        E.tomar(e12, "codex-heartbeat", t0)
        check(falla(lambda: E.liberar(e12, "codex-exec")) and e12["estado"] == "generando"
              and e12["lock_owner"] == "codex-heartbeat", "liberar solo lo hace el dueño del bloqueo")
        check(falla(lambda: E.liberar(base(), "codex-exec")), "liberar exige un encargo generando")

        print("   · liberar: tres no-lanzamientos seguidos bloquean el encargo (10e)")
        e13 = base()
        E.tomar(e13, "codex-exec", t0)
        E.liberar(e13, "codex-exec")
        E.tomar(e13, "codex-exec", t0)
        E.liberar(e13, "codex-exec")
        check(e13["estado"] == "pedido" and e13["no_lanzados"] == 2,
              f"dos no-lanzamientos seguidos: sigue en pedido ({e13['estado']}, {e13['no_lanzados']})")
        E.tomar(e13, "codex-exec", t0)
        E.liberar(e13, "codex-exec")
        check(e13["estado"] == "bloqueado" and e13["no_lanzados"] == 3 and e13["lock_owner"] is None
              and e13["intentos"] == [] and e13.get("nota_no_lanzado"),
              f"al tercer no-lanzamiento seguido: bloqueado con nota, sin sumar intento "
              f"({e13['estado']}, {e13['no_lanzados']}, {e13.get('nota_no_lanzado')!r})")

        e14 = base()
        del e14["no_lanzados"]  # simula un JSON viejo sin el campo
        E.tomar(e14, "codex-exec", t0)
        E.liberar(e14, "codex-exec")
        check(e14["estado"] == "pedido" and e14["no_lanzados"] == 1,
              "un encargo viejo sin no_lanzados sigue cargando y cuenta desde 1")

        print("   · liberar: marcar_generado y marcar_fallo cortan la racha de no_lanzados (I-1)")
        e15 = base()
        E.tomar(e15, "codex-exec", t0)
        E.liberar(e15, "codex-exec")
        E.tomar(e15, "codex-exec", t0)
        E.liberar(e15, "codex-exec")
        check(e15["no_lanzados"] == 2, f"dos no-lanzamientos antes de que Codex corra ({e15['no_lanzados']})")
        E.tomar(e15, "codex-exec", t0)
        E.marcar_fallo(e15, "codex-exec", "tiempo agotado", t0)
        check(e15["no_lanzados"] == 0 and e15.get("nota_no_lanzado") is None,
              f"(I-1) marcar_fallo (Codex sí corrió) reinicia no_lanzados a 0 ({e15['no_lanzados']})")
        E.tomar(e15, "codex-exec", t0)
        E.liberar(e15, "codex-exec")
        check(e15["estado"] == "pedido" and e15["no_lanzados"] == 1,
              f"(I-1) tras el reinicio, liberar vuelve a contar desde 1 ({e15['estado']}, {e15['no_lanzados']})")

        e16 = base()
        E.tomar(e16, "codex-exec", t0)
        E.marcar_generado(e16, "codex-exec", img, t0)
        check(e16["no_lanzados"] == 0,
              "(I-1) marcar_generado (Codex sí corrió) deja no_lanzados en 0")

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

    con_shortcode = M.manifiesto_verificacion("LAB-X", {"facebook": "1"},
                                              instagram_shortcodes={"instagram": "DdR54JEgxHN"},
                                              surfaces={"facebook": "story"})
    check(con_shortcode.get("instagram_shortcodes") == {"instagram": "DdR54JEgxHN"},
          "manifiesto de verificación admite un shortcode de Instagram")
    check(con_shortcode.get("surfaces") == {"facebook": "story"},
          "y una superficie explícita de otra red a la vez (una Story de Instagram por teléfono no admite shortcode+story)")
    check(M.manifiesto_verificacion("LAB-X", {}, instagram_shortcodes={"instagram": "DdR54JEgxHN"}) ==
          {"run_group_id": "LAB-X", "post_ids": {}, "instagram_shortcodes": {"instagram": "DdR54JEgxHN"}},
          "solo shortcode, sin post_ids, basta para tener algo que verificar")
    for post_ids, kwargs, label in (
            ({"facebook": "1"}, {"instagram_shortcodes": {"instagram": "abc"}}, "shortcode demasiado corto"),
            ({"facebook": "1"}, {"instagram_shortcodes": {"instagram": "x" * 21}}, "shortcode demasiado largo"),
            ({"facebook": "1"}, {"instagram_shortcodes": {"instagram": "con espacio 12"}}, "shortcode con espacios"),
            ({"facebook": "1"}, {"instagram_shortcodes": {"facebook": "DdR54JEgxHN"}}, "shortcode fuera de instagram"),
            ({"instagram": "123"}, {"instagram_shortcodes": {"instagram": "DdR54JEgxHN"}},
             "instagram con post_id y shortcode a la vez"),
            ({"facebook": "1"}, {"surfaces": {"instagram": "carrusel"}}, "superficie que no es feed ni story"),
            ({"facebook": "1"}, {"surfaces": {"tiktok": "story"}}, "superficie de una red no verificable"),
            ({}, {"instagram_shortcodes": {"instagram": "DdR54JEgxHN"}, "surfaces": {"instagram": "story"}},
             "shortcode de Instagram junto con superficie story (una Story por teléfono no se busca así)")):
        try:
            M.manifiesto_verificacion("LAB-X", post_ids, **kwargs)
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


XML_SELECTOR = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
<node text="" content-desc="" class="android.widget.FrameLayout" bounds="[0,0][1080,2340]">
<node text="Nouvelle publication" content-desc="" class="android.widget.TextView" bounds="[158,92][847,249]"/>
<node text="Suivant" content-desc="" class="android.widget.TextView" bounds="[847,92][1080,249]"/>
<node text="" content-desc="Modifier le rognage" class="android.widget.ImageView" bounds="[34,1194][135,1295]"/>
<node text="" content-desc="Désélectionné Miniature de la photo du 14 septembre 2026 9:29" class="android.view.View" bounds="[542,1479][807,1744]"/>
<node text="" content-desc="Sélectionné Miniature de la photo du 14 septembre 2026 10:39" class="android.view.View" bounds="[273,1479][538,1744]"/>
<node text="" content-desc="Publier uniquement sur le profil" class="android.view.View" bounds="[0,0][0,0]"/>
<node text="«Conténtese con hacer»." content-desc="" class="android.widget.AutoCompleteTextView" bounds="[45,519][1035,1228]"/>
</node>
</hierarchy>"""


PAQUETE_IG = "com.instagram.android"
SELECTOR_IG = XML_SELECTOR.replace("<node ", f'<node package="{PAQUETE_IG}" ')
VOLCADO_OK = "UI hierchary dumped to: /sdcard/lab-ui.xml\n"


def nodo_xml(bounds: str, texto: str = "", desc: str = "", clase: str = "android.widget.TextView",
             paquete: str = PAQUETE_IG, hijos: str = "", extra: str = "") -> str:
    """Un <node> sintético con los atributos que escribe uiautomator."""
    from xml.sax.saxutils import quoteattr
    abre = (f"<node text={quoteattr(texto)} content-desc={quoteattr(desc)} class={quoteattr(clase)} "
            f"package={quoteattr(paquete)} bounds={quoteattr(bounds)} {extra}")
    return f"{abre}>{hijos}</node>" if hijos else f"{abre}/>"


def jerarquia(*hijos: str, alto: int = 2340) -> str:
    raiz = nodo_xml(f"[0,0][1080,{alto}]", clase="android.widget.FrameLayout", hijos="".join(hijos))
    return f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><hierarchy rotation=\"0\">{raiz}</hierarchy>"


PIE_PRUEBA = "«Conténtese con hacer».\n\n#citasdiarias #sabiduria"
BOTON_PARTAGER = nodo_xml("[45,2081][1035,2205]", clase="android.widget.Button", extra='clickable="true"',
                          hijos=nodo_xml("[480,2115][600,2170]", texto="Partager"))
LISTA_HASHTAGS = nodo_xml("[0,1000][1080,1400]", clase="android.widget.ListView",
                          hijos=nodo_xml("[0,1000][1080,1150]", texto="#citasdiarias")
                          + nodo_xml("[0,1150][1080,1300]", texto="10 208 publications publiques"))


def xml_compositor(*, titulo: bool = True, pie: str = PIE_PRUEBA, tema: bool = True,
                   partager: bool = True, despues: str = "", boton: str = BOTON_PARTAGER) -> str:
    return jerarquia(
        nodo_xml("[158,92][922,249]", texto="Nouvelle publication") if titulo else "",
        nodo_xml("[45,300][1035,700]", texto=pie, clase="android.widget.AutoCompleteTextView"),
        nodo_xml("[200,900][600,960]", texto="Autumn Days") if tema else "",
        nodo_xml("[200,960][600,1020]", texto="Morunas") if tema else "",
        boton if partager else "",
        despues)


def xml_inicio(*, banner: bool = False, aviso: str = "", pie_ajeno: str = "") -> str:
    """Inicio de Instagram: una publicación con su propio botón «Partager» y la barra de abajo.
    `pie_ajeno` es el pie de una publicación de otra cuenta, más abajo en pantalla."""
    return jerarquia(
        nodo_xml("[0,250][1080,330]", texto="Publication sur sabiduriabolsillo…") if banner else "",
        nodo_xml("[0,340][1080,420]", texto=aviso) if aviso else "",
        nodo_xml("[0,1200][1080,1320]", texto=pie_ajeno) if pie_ajeno else "",
        nodo_xml("[900,1500][1000,1600]", desc="Partager", clase="android.widget.ImageView",
                 extra='clickable="true"'),
        nodo_xml("[864,2200][1080,2340]", desc="Profil", clase="android.widget.FrameLayout",
                 extra='clickable="true"'))


class IntentoDeES(BaseException):
    """Una prueba intentó hablar con el teléfono de verdad. BaseException para que
    ningún `except Exception` del código la esconda."""


class TelefonoSimulado:
    """Teléfono de mentira: volcados guionizados (el último se repite), toques, teclas y
    capturas anotados, y un reloj que avanza 2 s en cada lectura."""

    def __init__(self, volcados: list, *, teclado: tuple = (False,), emergentes: tuple = ((),),
                 listo: bool = True, falla_tocar: Exception | None = None,
                 falla_pegar: Exception | None = None, falla_cortina: Exception | None = None,
                 tras_cierre: list | None = None, falla_cierre: Exception | None = None,
                 focos: tuple = (), falla_captura: Exception | None = None):
        self.volcados = list(volcados)
        self.falla_cierre = falla_cierre
        self.focos_actuales = list(focos)  # lo que devuelve `focos()`: vacío es «no se puede leer»
        self.falla_captura = falla_captura
        self.tras_cierre = tras_cierre  # si se da, `forzar_cierre` sustituye el guion de volcados por este
        self.teclado = list(teclado)
        self.emergentes = list(emergentes)
        self.listo = listo
        self.falla_tocar = falla_tocar
        self.falla_pegar = falla_pegar
        self.falla_cortina = falla_cortina
        self.toques: list[tuple[int, int]] = []
        self.teclas: list[int] = []
        self.combinaciones: list[tuple] = []
        self.pegados: list[str] = []
        self.capturas: list[str] = []
        self.plazos_captura: list = []
        self.prohibidos: list[str] = []
        self.orden: list[str] = []  # «cortina» y «lanzar:<paquete>», para comprobar el orden
        self.reloj = 1000.0
        self.volcados_leidos = 0
        self.ultimo = None  # el último volcado leído: lo que había en pantalla
        self.toques_en: list[tuple] = []  # (x, y, volcado en pantalla al tocar)

    @staticmethod
    def _siguiente(lista: list):
        return lista.pop(0) if len(lista) > 1 else lista[0]

    def volcado(self, timeout: int = 30) -> str:
        self.volcados_leidos += 1
        v = self._siguiente(self.volcados)
        if isinstance(v, BaseException):
            raise v
        self.ultimo = v
        return v

    def tocar(self, x: int, y: int) -> None:
        self.toques_en.append((x, y, self.ultimo))
        self.toques.append((x, y))
        if self.falla_tocar is not None:
            raise self.falla_tocar

    def tecla(self, codigo: int) -> None:
        self.teclas.append(codigo)

    def combinacion(self, *codigos: int) -> None:
        self.combinaciones.append(codigos)

    def estado(self) -> dict:
        return {"adb": True, "despierto": self.listo, "bloqueado": not self.listo, "listo": self.listo}

    def teclado_estado(self):
        return self._siguiente(self.teclado)

    def ventanas_emergentes(self, paquete: str, timeout: int = 15):
        v = self._siguiente(self.emergentes)
        if isinstance(v, BaseException):
            raise v
        return v

    def teclado_visible(self) -> bool:
        v = self.teclado_estado()
        return True if v is None else v

    def captura(self, destino: pathlib.Path, timeout=None) -> pathlib.Path:
        self.capturas.append(destino.name)
        self.plazos_captura.append(timeout)
        if self.falla_captura is not None:
            raise self.falla_captura
        return destino

    def focos(self, timeout: int = 15) -> list[str]:
        return list(self.focos_actuales)

    def lanzar(self, paquete: str) -> None:
        self.orden.append(f"lanzar:{paquete}")

    def forzar_cierre(self, paquete: str, timeout: int = 15) -> None:
        self.orden.append(f"forzar_cierre:{paquete}")
        if self.falla_cierre is not None:
            raise self.falla_cierre
        if self.tras_cierre is not None:
            self.volcados = list(self.tras_cierre)

    def cerrar_cortina(self) -> None:
        self.orden.append("cortina")
        if self.falla_cortina is not None:
            raise self.falla_cortina

    def pegar(self, texto: str, paste: bool = True) -> None:
        self.pegados.append(texto)
        if self.falla_pegar is not None:
            raise self.falla_pegar

    def monotonic(self) -> float:
        self.reloj += 2
        return self.reloj

    def prohibido(self, *args, **kwargs):
        self.prohibidos.append(repr(args)[:120])
        raise IntentoDeES(repr(args)[:120])


def con_telefono_simulado(sim: TelefonoSimulado, accion):
    """Ejecuta accion() con el teléfono, el portapapeles, subprocess y el reloj
    sustituidos; lo restaura todo pase lo que pase. Devuelve (resultado, excepción)."""
    import subprocess
    import phone_clipboard
    from labkit import instagram_feed, reloj, telefono

    cambios = [(telefono, "volcado", sim.volcado), (telefono, "tocar", sim.tocar),
               (telefono, "tecla", sim.tecla), (telefono, "combinacion", sim.combinacion),
               (telefono, "estado", sim.estado), (telefono, "teclado_visible", sim.teclado_visible),
               (telefono, "teclado_estado", sim.teclado_estado),
               (telefono, "ventanas_emergentes", sim.ventanas_emergentes), (telefono, "captura", sim.captura),
               (telefono, "lanzar", sim.lanzar), (telefono, "cerrar_cortina", sim.cerrar_cortina),
               (telefono, "forzar_cierre", sim.forzar_cierre), (telefono, "focos", sim.focos),
               (telefono, "shell", sim.prohibido),
               (telefono, "adb", sim.prohibido), (phone_clipboard, "pegar", sim.pegar),
               (phone_clipboard, "adb", sim.prohibido), (subprocess, "run", sim.prohibido),
               (subprocess, "Popen", sim.prohibido),
               (instagram_feed.time, "sleep", lambda segundos: None),
               (instagram_feed.time, "monotonic", sim.monotonic),
               (reloj, "dormir", lambda segundos: None),
               (reloj, "monotonic", sim.monotonic)]
    originales = [(obj, nombre, getattr(obj, nombre)) for obj, nombre, _ in cambios]
    try:
        for obj, nombre, nuevo in cambios:
            setattr(obj, nombre, nuevo)
        try:
            return accion(), None
        except (Exception, IntentoDeES) as e:
            return None, e
    finally:
        for obj, nombre, viejo in originales:
            setattr(obj, nombre, viejo)


def xml_perfil(titulo: str = "sabiduriabolsillo", publicaciones: str = "3 712publications",
               abajo: str = "") -> str:
    return jerarquia(
        nodo_xml("[316,92][693,250]", texto=titulo),
        nodo_xml("[960,92][1080,250]", desc="Créer", clase="android.widget.Button"),
        nodo_xml("[40,400][330,560]", desc=publicaciones, clase="android.widget.LinearLayout"),
        nodo_xml("[40,900][520,1000]", texto="Modifier le profil", clase="android.widget.Button"),
        abajo,
        nodo_xml("[864,2200][1080,2340]", desc="Profil", clase="android.widget.FrameLayout"))


def seccion_interfaz() -> None:
    print("\n6. Lectura de la interfaz del teléfono")
    from datetime import datetime, timezone
    import shlex
    from labkit import instagram_feed as IG, telefono as T

    def lanza(accion, error) -> str | None:
        """Mensaje del error esperado, o None si no se lanzó."""
        try:
            accion()
        except error as e:
            return str(e) or type(e).__name__
        return None

    nodos = T.nodos(XML_SELECTOR)
    check(all(n["bounds"] != (0, 0, 0, 0) for n in nodos), "descarta nodos invisibles de tamaño cero")
    s = T.buscar(XML_SELECTOR, texto="Suivant")
    check(s is not None and s["centro"] == (963, 170), "busca por texto exacto y calcula el centro")
    check(T.buscar(XML_SELECTOR, texto="Modifier le rognage") is not None, "también busca en content-desc")
    check(T.buscar(XML_SELECTOR, texto="Publier uniquement sur le profil") is None,
          "no devuelve un nodo invisible aunque coincida")
    check(T.buscar(XML_SELECTOR, empieza="Sélectionné Miniature") is not None, "busca por prefijo")
    check(T.textos(XML_SELECTOR).count("«Conténtese con hacer».") == 1,
          "textos() decodifica entidades y conserva «»")

    print("   · nodos y búsqueda")
    fino = jerarquia(nodo_xml("[5,5][5,9]", texto="línea"), nodo_xml(
        "[10,10][110,60]", texto="Partager", clase="android.widget.Button",
        extra='clickable="true" enabled="false" resource-id="com.instagram.android:id/share"'))
    ns = T.nodos(fino)
    check(all(n["texto"] != "línea" for n in ns), "descarta un nodo de ancho cero [5,5][5,9]")
    boton = T.buscar(fino, texto="Partager")
    check(boton is not None and boton["package"] == PAQUETE_IG and boton["clickable"] is True
          and boton["enabled"] is False and boton["resource_id"] == "com.instagram.android:id/share"
          and boton["clase"] == "android.widget.Button",
          "nodos() da package, clickable, enabled y resource_id")
    check(lanza(lambda: T.nodos("<hierarchy><node"), T.TelefonoError) is not None,
          "un XML roto da TelefonoError, no ParseError")
    mezcla = jerarquia(nodo_xml("[0,0][100,100]", texto="Suivant", paquete="com.android.systemui"),
                       nodo_xml("[0,200][100,300]", texto="Suivant"),
                       nodo_xml("[0,400][100,500]", texto="Suivant", clase="android.widget.Button"))
    check(len(T.buscar_todos(mezcla, texto="Suivant")) == 3, "buscar_todos devuelve todas las coincidencias")
    check([n["bounds"][1] for n in T.buscar_todos(mezcla, texto="Suivant", paquete=PAQUETE_IG)] == [200, 400],
          "buscar_todos filtra por paquete y respeta el orden del documento")
    check([n["bounds"][1] for n in T.buscar_todos(mezcla, paquete=PAQUETE_IG, clase="android.widget.Button")] == [400],
          "buscar_todos filtra por clase sin criterio de texto")
    check(T.buscar(mezcla, texto="Suivant", paquete=PAQUETE_IG)["bounds"][1] == 200,
          "buscar acepta paquete y devuelve la primera")

    print("   · volcados, estado y teclado")
    check(T.volcado_valido(VOLCADO_OK, XML_SELECTOR), "un volcado con «dumped to» y XML legible es válido")
    check(T.volcado_valido(VOLCADO_OK, "\n  " + XML_SELECTOR), "tolera espacios antes de <?xml")
    check(not T.volcado_valido("ERROR: could not get idle state.\n", XML_SELECTOR),
          "«could not get idle state» invalida aunque quede un archivo viejo")
    check(not T.volcado_valido(VOLCADO_OK, ""), "un archivo vacío no es válido")
    check(not T.volcado_valido(VOLCADO_OK, "cat: /sdcard/lab-ui.xml: No such file or directory"),
          "un cat fallido no es válido")
    check(not T.volcado_valido(VOLCADO_OK, "<?xml version='1.0' ?><hierarchy><node"),
          "un XML truncado no es válido")
    e = T.estado_desde_dumpsys("Power\n  mWakefulness=Awake\n", "  isKeyguardShowing=false\n")
    check(e == {"despierto": True, "bloqueado": False, "listo": True}, "despierto y sin bloqueo: listo")
    check(T.estado_desde_dumpsys("  mWakefulness=Asleep\n", "  isKeyguardShowing=false\n")["listo"] is False,
          "dormido: no listo")
    e = T.estado_desde_dumpsys("  mWakefulness=Awake\n", "  isKeyguardShowing=true\n")
    check(e["bloqueado"] is True and e["listo"] is False, "con la pantalla de bloqueo: no listo")
    e = T.estado_desde_dumpsys("  mWakefulness=Awake\n", "WINDOW MANAGER POLICY STATE\n")
    check(e["bloqueado"] is None and e["listo"] is False, "sin isKeyguardShowing no se sabe: no listo")
    check(T.teclado_desde_dumpsys("  mInputShown=true\n") is True, "teclado visible")
    check(T.teclado_desde_dumpsys("  mInputShown=false\n") is False, "teclado oculto")
    check(T.teclado_desde_dumpsys("INPUT METHOD MANAGER\n") is None, "sin mInputShown no se sabe")

    print("   · tapado")
    comp = xml_compositor()
    partager_boton = T.buscar_todos(comp, texto="Partager", paquete=PAQUETE_IG)[0]
    boton_padre = [n for n in T.nodos(comp) if n["clase"] == "android.widget.Button"][0]
    check(not T.tapado(comp, boton_padre), "el hijo TextView de un botón no lo tapa")
    check(not T.tapado(comp, partager_boton), "un nodo sin nada encima no está tapado")
    cubierto = xml_compositor(despues=nodo_xml("[0,1900][1080,2340]", clase="android.widget.ListView"))
    check(T.tapado(cubierto, T.buscar(cubierto, texto="Partager")), "una lista posterior encima sí lo tapa")
    check(T.tapado(cubierto, dict(boton_padre, bounds=(1, 2, 3, 4))), "un nodo que no está en el volcado cuenta como tapado")

    print("   · subida y MediaStore")
    fila = "Row: 0 _display_name=lab-20260914.jpg, date_added=1757839140\n"
    check(T.fila_mediastore_presente(fila, "lab-20260914.jpg"), "reconoce la fila de MediaStore")
    check(not T.fila_mediastore_presente("No result found.\n", "lab-20260914.jpg"), "sin resultado no hay fila")
    check(not T.fila_mediastore_presente(fila.replace(".jpg,", ".jpg.bak,"), "lab-20260914.jpg"),
          "otro nombre parecido no cuenta")
    check(not T.fila_mediastore_presente("", "lab-20260914.jpg"), "salida vacía no cuenta")
    consulta = shlex.split(T.consulta_mediastore("lab-20260914.jpg"))
    check(consulta[:2] == ["content", "query"] and "_display_name='lab-20260914.jpg'" in consulta
          and "content://media/external/images/media" in consulta, "la consulta de MediaStore se cita bien")
    check(lanza(lambda: T.consulta_mediastore("a'b.jpg"), T.TelefonoError) is not None,
          "un nombre con comillas se rechaza")
    h = "ab" * 32
    check(T.sha256_de_salida(f"{h}  /sdcard/Pictures/x.jpg\n") == h, "lee el sha256 de sha256sum")
    check(lanza(lambda: T.sha256_de_salida(""), T.TelefonoError) is not None, "salida vacía de sha256sum: TelefonoError")
    check(lanza(lambda: T.sha256_de_salida("sha256sum: /sdcard/x.jpg: No such file or directory"), T.TelefonoError)
          is not None, "un error de sha256sum: TelefonoError")

    print("   · perfil y selector de Instagram")
    check(IG.perfil_activo(xml_perfil()) == "sabiduriabolsillo", "lee el perfil activo de la barra superior")
    personal = xml_perfil(titulo="cuenta.personal",
                          abajo=nodo_xml("[316,1200][693,1260]", texto="sabiduriabolsillo"))
    check(IG.perfil_activo(personal) == "cuenta.personal",
          "la marca más abajo en pantalla no hace pasar por bueno otro perfil")
    doble = jerarquia(nodo_xml("[316,92][693,250]", texto="uno"), nodo_xml("[400,100][700,240]", texto="dos"))
    check(IG.perfil_activo(doble) is None, "dos títulos distintos arriba: ambiguo")
    check(IG.perfil_activo(jerarquia(nodo_xml("[316,1000][693,1100]", texto="sabiduriabolsillo"))) is None,
          "sin título arriba: None")
    check(IG.publicaciones_de_perfil(xml_perfil()) == 3712, "publicaciones con espacio normal")
    check(IG.publicaciones_de_perfil(xml_perfil(publicaciones="3\u00a0712 publications")) == 3712,
          "publicaciones con espacio duro")
    check(IG.publicaciones_de_perfil(xml_perfil(publicaciones="3\u202f712publications")) == 3712,
          "publicaciones con espacio fino")
    check(IG.publicaciones_de_perfil(xml_perfil(publicaciones="Publications")) is None, "sin número: None")

    madrid = "Sélectionné Miniature de la photo du 14 septembre 2026 10:39"
    check(IG.fecha_miniatura(madrid) == datetime(2026, 9, 14, 8, 39, tzinfo=timezone.utc),
          "la hora de la miniatura es de Madrid (10:39 CEST = 08:39 UTC)")
    check(IG.fecha_miniatura("Miniature de la photo du 5 janvier 2026 9:05")
          == datetime(2026, 1, 5, 8, 5, tzinfo=timezone.utc), "en invierno Madrid es UTC+1")
    check(IG.fecha_miniatura("Désélectionné Miniature de la photo du 1er aout 2026 0:15")
          == datetime(2026, 7, 31, 22, 15, tzinfo=timezone.utc), "acepta «1er» y meses sin tilde")
    check(IG.fecha_miniatura("Miniature de la photo") is None, "sin fecha: None")
    check(IG.fecha_miniatura("Miniature de la photo du 14 septembrr 2026 10:39") is None, "mes desconocido: None")
    check(IG.fecha_miniatura("Miniature de la photo du 31 fevrier 2026 10:39") is None, "fecha imposible: None")

    sel = IG.seleccion_unica(SELECTOR_IG)
    check(sel is not None and sel["desc"] == madrid, "seleccion_unica encuentra la única seleccionada")
    ninguna = SELECTOR_IG.replace('"Sélectionné Miniature', '"Désélectionné Miniature')
    check(IG.seleccion_unica(ninguna) is None, "sin seleccionada: None")
    dos = SELECTOR_IG.replace('"Désélectionné Miniature', '"Sélectionné Miniature')
    check(IG.seleccion_unica(dos) is None, "dos seleccionadas: None")
    check(IG.seleccion_unica(XML_SELECTOR) is None, "una selección fuera de Instagram no cuenta")
    subido = datetime(2026, 9, 14, 8, 40, 30, tzinfo=timezone.utc)
    check(IG.miniatura_coincide(madrid, subido), "la miniatura coincide con la subida dentro de la tolerancia")
    check(not IG.miniatura_coincide(madrid, datetime(2026, 9, 14, 8, 43, 30, tzinfo=timezone.utc)),
          "4,5 min de diferencia no coinciden")
    check(not IG.miniatura_coincide(madrid, datetime(2026, 9, 14, 10, 39)), "una hora sin zona no coincide")
    check(not IG.miniatura_coincide("Sélectionné Miniature", subido), "una miniatura sin fecha no coincide")

    print("   · editor y compositor")
    chip = "Audio suggéré. Autumn Days par Morunas. Appuyez pour accéder à plus d’options …"
    check(IG.tema_de_chip(chip) == "Autumn Days par Morunas", "extrae el tema del chip de audio")
    check(IG.tema_de_chip("Audio. Autumn Days par Morunas") is None, "sin el prefijo del chip: None")
    check(IG.punto_mas((258, 103, 821, 315)) == (762, 173), "el «+» del chip medido el 2026-09-14")
    check(lanza(lambda: IG.punto_mas((0, 0, 50, 10)), IG.PantallaInesperada) is not None,
          "un chip demasiado pequeño no se toca")
    check(not IG.hay_desplegable_hashtags(comp), "un pie con # dentro del campo no es el desplegable")
    check(IG.hay_desplegable_hashtags(xml_compositor(despues=LISTA_HASHTAGS)), "detecta el desplegable de hashtags")
    campo = IG.campo_pie(comp)
    check(campo is not None and campo["texto"] == PIE_PRUEBA, "encuentra el campo del pie por su clase")
    check(IG.campo_pie(XML_SELECTOR) is None, "un campo fuera de Instagram no cuenta")
    tema = "Autumn Days par Morunas"
    check(IG.compositor_listo(comp, PIE_PRUEBA, tema) == [], "compositor listo: sin problemas")
    check(IG.compositor_listo(comp, PIE_PRUEBA, None) == [], "sin tema no se exige canción")
    casos = (
        (xml_compositor(titulo=False), PIE_PRUEBA, "Nouvelle publication"),
        (xml_compositor(pie="«Conténtese con hacer»."), PIE_PRUEBA, "pie"),
        (xml_compositor(tema=False), PIE_PRUEBA, "Autumn Days"),
        (xml_compositor(partager=False), PIE_PRUEBA, "Partager"),
        (cubierto, PIE_PRUEBA, "tapado"),
        (xml_compositor(despues=LISTA_HASHTAGS), PIE_PRUEBA, "desplegable"),
    )
    for xml, pie, clave in casos:
        problemas = IG.compositor_listo(xml, pie, tema)
        check(len(problemas) == 1 and clave in problemas[0], f"compositor_listo detecta: {clave} ({problemas})")
    ajeno = xml_compositor(partager=False, despues=nodo_xml("[45,2081][1035,2205]", texto="Partager",
                                                           paquete="com.android.systemui"))
    check(any("Partager" in p for p in IG.compositor_listo(ajeno, PIE_PRUEBA, tema)),
          "un «Partager» de otro paquete no cuenta")

    print("   · elección de controles")
    dos_suivant = jerarquia(nodo_xml("[847,92][1080,249]", texto="Suivant"),
                            nodo_xml("[700,2100][1040,2250]", texto="Suivant"))
    check(IG._nodo(dos_suivant, zona="arriba", texto="Suivant")["bounds"][1] == 92, "zona arriba elige el de arriba")
    check(IG._nodo(dos_suivant, zona="abajo", texto="Suivant")["bounds"][1] == 2100, "zona abajo elige el de abajo")
    check("ambiguo" in (lanza(lambda: IG._nodo(dos_suivant, texto="Suivant"), IG.PantallaInesperada) or ""),
          "dos controles iguales en sitios distintos: ambiguo")
    anidado = jerarquia(nodo_xml("[45,2081][1035,2205]", texto="Partager", clase="android.widget.Button",
                                 extra='clickable="true"',
                                 hijos=nodo_xml("[480,2115][600,2170]", texto="Partager")))
    check(IG._nodo(anidado, texto="Partager")["clase"] == "android.widget.Button",
          "un botón y su etiqueta con el mismo texto no son ambiguos")
    solo_ajeno = jerarquia(nodo_xml("[847,92][1080,249]", texto="Suivant", paquete="com.android.systemui"))
    check(lanza(lambda: IG._nodo(solo_ajeno, zona="arriba", texto="Suivant"), IG.PantallaInesperada) is not None,
          "un control de otro paquete no se toca")
    check(issubclass(IG.BorradorPendiente, IG.PantallaInesperada)
          and issubclass(IG.TelefonoNoListo, IG.PantallaInesperada), "las excepciones nuevas son PantallaInesperada")

    print("   · confirmación del envío")

    def v(compositor: bool, banner: bool) -> dict:
        return {"valido": True, "compositor": compositor, "banner": banner}

    inval = {"valido": False, "compositor": False, "banner": False}
    check(IG.evaluar_envio([v(True, False), v(False, True), v(False, False), v(False, False)]) == "confirmado",
          "banner y luego dos volcados limpios: confirmado")
    check(IG.evaluar_envio([v(True, False), v(False, True), v(False, False), inval, v(False, False), inval])
          == "confirmado", "los volcados fallidos se ignoran")
    check(IG.evaluar_envio([v(False, True), inval, inval]) == "timeout", "banner sin volcados válidos después: timeout")
    check(IG.evaluar_envio([v(False, True), v(False, False)]) == "timeout", "un solo volcado limpio no basta")
    check(IG.evaluar_envio([v(False, True), v(False, False), v(True, False)]) == "timeout",
          "si vuelve el compositor: timeout")
    check(IG.evaluar_envio([v(True, False), v(False, False), v(False, False)]) == "sin_banner",
          "sin compositor pero sin banner visto: sin_banner")
    check(IG.evaluar_envio([dict(inval, banner=True), v(False, False), v(False, False)]) == "sin_banner",
          "el banner de un volcado inválido no cuenta")
    check(IG.evaluar_envio([]) == "timeout", "sin observaciones: timeout")
    inicio = jerarquia(nodo_xml("[0,250][1080,330]", texto="Publication sur sabiduriabolsillo…"))
    check(IG.observacion_de_volcado(inicio) == {"valido": True, "compositor": False, "banner": True, "fallo": False,
                                                "fallo_texto": None, "fallo_bounds": None},
          "observa el banner en el inicio")
    check(IG.observacion_de_volcado(comp) == {"valido": True, "compositor": True, "banner": False, "fallo": False,
                                              "fallo_texto": None, "fallo_bounds": None},
          "observa el compositor")
    check(IG.observacion_de_volcado(jerarquia().replace(PAQUETE_IG, "com.sec.android.app.launcher"))["valido"] is False,
          "un volcado sin Instagram en primer plano no es válido")

    print("   · segunda revisión: fallos, compositor por bounds y botón pulsable")
    etiqueta = T.buscar(comp, texto="Partager")["bounds"]
    feed = xml_inicio()
    check(IG.observacion_de_volcado(feed, etiqueta)["compositor"] is False,
          "un «Partager» de una publicación del inicio no es el compositor")
    solo_boton = jerarquia(BOTON_PARTAGER)
    check(IG.observacion_de_volcado(solo_boton, etiqueta)["compositor"] is True,
          "el «Partager» pulsado (mismos bounds) sigue siendo el compositor")
    check(IG.observacion_de_volcado(solo_boton)["compositor"] is False, "sin bounds del botón no se compara")
    check(IG.observacion_de_volcado(jerarquia(nodo_xml("[45,300][1035,700]", texto="x",
                                                       clase="android.widget.EditText")))["compositor"] is True,
          "el campo del pie abierto es el compositor")
    for aviso in ("Impossible de publier. Réessayer", "La publication n’a pas pu être partagée",
                  "La publication n'a pas pu être partagée", "Réessayer"):
        check(IG.observacion_de_volcado(xml_inicio(aviso=aviso))["fallo"] is True, f"reconoce el fallo «{aviso}»")
    obs_aviso = IG.observacion_de_volcado(xml_inicio(aviso="Impossible de publier. Réessayer"))
    check(obs_aviso["fallo_texto"] == "Impossible de publier. Réessayer" and obs_aviso["fallo_bounds"] == (0, 340, 1080, 420),
          f"(10e) observacion_de_volcado devuelve el texto y los bounds del aviso que coincidió ({obs_aviso})")
    check(IG.observacion_de_volcado(xml_inicio())["fallo_texto"] is None
          and IG.observacion_de_volcado(xml_inicio())["fallo_bounds"] is None,
          "(10e) sin aviso de fallo, fallo_texto y fallo_bounds son None")
    nodo_mixto = jerarquia(nodo_xml("[0,0][200,100]", texto="algo intrascendente", desc="Réessayer"))
    obs_mixto = IG.observacion_de_volcado(nodo_mixto)
    check(obs_mixto["fallo"] is True and obs_mixto["fallo_texto"] == "Réessayer",
          f"(M-3) fallo_texto es el campo que realmente contiene la marca de fallo, no «texto or desc» ({obs_mixto})")
    texto_largo = "Réessayer: " + "x" * 150
    nodo_largo = jerarquia(nodo_xml("[0,300][1080,400]", texto=texto_largo))
    obs_largo = IG.observacion_de_volcado(nodo_largo)
    check(obs_largo["fallo"] is True and obs_largo["fallo_texto"] == texto_largo[:100] + "…"
          and len(obs_largo["fallo_texto"]) == 101,
          f"(M-4) fallo_texto se recorta a 100 caracteres con «…» si es más largo (len={len(obs_largo['fallo_texto'])})")
    check(IG.observacion_de_volcado(xml_compositor(pie="Réessayer, n'a pas pu"))["fallo"] is False,
          "el texto del propio pie no es un aviso de fallo")
    check(IG.observacion_de_volcado(jerarquia(nodo_xml("[0,0][100,100]", texto="Réessayer",
                                                       paquete="com.android.systemui")))["fallo"] is False,
          "un «Réessayer» de otra aplicación no cuenta")
    fallo = {"valido": True, "compositor": False, "banner": False, "fallo": True}
    check(IG.evaluar_envio([v(False, True), v(False, False), v(False, False), fallo]) == "fallido",
          "un fallo tras el banner manda sobre la confirmación")
    check(IG.evaluar_envio([v(False, True), fallo, v(False, False), v(False, False)]) == "fallido",
          "un fallo visto en cualquier momento da fallido")
    check(IG.evaluar_envio([dict(fallo, valido=False), v(False, True), v(False, False), v(False, False)])
          == "confirmado", "el fallo de un volcado inválido no cuenta")

    print("   · seguimiento de la revisión (10b): fallos solo junto al aviso de subida")
    pie_con_fallo = ("Réessayer n'a pas pu, dice el pie de otra cuenta, que es largo como los pies de verdad "
                     "#citas #sabiduria")
    check(len(pie_con_fallo) > 80, "el pie ajeno de estas pruebas pasa de 80 caracteres")
    check(IG.observacion_de_volcado(xml_inicio(pie_ajeno=pie_con_fallo))["fallo"] is False,
          "(M-2) un pie del inicio más abajo con «Réessayer» no es un fallo")
    check(IG.observacion_de_volcado(xml_inicio(banner=True, pie_ajeno=pie_con_fallo))["fallo"] is False,
          "(M-2) con el banner arriba, un pie lejano con «Réessayer» tampoco")
    banner_bajo = jerarquia(nodo_xml("[0,900][1080,980]", texto="Publication sur sabiduriabolsillo…"),
                            nodo_xml("[0,990][1080,1070]", texto="Impossible de publier. Réessayer"))
    check(IG.observacion_de_volcado(banner_bajo)["fallo"] is True,
          "(M-2) un aviso de error junto al banner cuenta aunque esté por debajo de 600 px")
    check(IG.observacion_de_volcado(jerarquia(nodo_xml("[0,500][1080,600]", texto="Réessayer")))["fallo"] is True,
          "(M-2) un aviso con el borde inferior en 600 px cuenta")
    check(IG.observacion_de_volcado(jerarquia(nodo_xml("[0,1500][1080,1600]", texto="Impossible de publier. Réessayer")))
          ["fallo"] is True, "(10d) sin banner, un aviso corto de Instagram bajo en pantalla sí cuenta")
    ochenta = "Réessayer " + "x" * 70
    check(IG.observacion_de_volcado(jerarquia(nodo_xml("[0,1500][1080,1600]", texto=ochenta)))["fallo"] is True
          and IG.observacion_de_volcado(jerarquia(nodo_xml("[0,1500][1080,1600]", texto=ochenta + "x")))["fallo"] is False,
          "(10d) lejos del aviso, un texto de fallo de 80 caracteres cuenta y uno de 81 no")
    check(IG.observacion_de_volcado(jerarquia(nodo_xml("[0,1500][1080,1600]", texto="Réessayer",
                                                       clase="android.widget.EditText")))["fallo"] is False,
          "(10d) un «Réessayer» corto dentro del campo del pie no cuenta")

    def observa(xml, **kw):
        try:
            return IG.observacion_de_volcado(xml, **kw)
        except Exception as e:  # noqa: BLE001
            return {"error": repr(e)}

    largo_fallo = ("La publication n’a pas pu être partagée. Vérifiez votre connexion et réessayez plus tard, "
                   "s’il vous plaît.")
    banner_bajo_solo = jerarquia(nodo_xml("[0,900][1080,980]", texto="Publication sur sabiduriabolsillo…"))
    fallo_bajo = jerarquia(nodo_xml("[0,990][1080,1070]", texto=largo_fallo))
    check(len(largo_fallo) > 80 and observa(fallo_bajo).get("fallo") is False,
          "(10d) sin banner en este volcado ni en los anteriores, un aviso largo bajo no cuenta")
    check(observa(fallo_bajo, banners_previos=[(0, 900, 1080, 980)]).get("fallo") is True,
          f"(10d) un aviso junto a un banner visto en un volcado anterior cuenta ({observa(fallo_bajo, banners_previos=[(0, 900, 1080, 980)])})")
    check(observa(fallo_bajo, banners_previos=[(0, 250, 1080, 330)]).get("fallo") is False,
          "(10d) un banner anterior lejano no hace contar un aviso largo")
    banners_de = getattr(IG, "banners_de_volcado", None)
    check(banners_de is not None and banners_de(banner_bajo_solo) == [(0, 900, 1080, 980)]
          and banners_de(xml_inicio()) == [],
          "(10d) banners_de_volcado da los bounds de los avisos «Publication sur…»")

    import importlib
    try:
        pantallas = importlib.import_module("labkit.instagram_pantallas")
    except ImportError:
        pantallas = None
    nombres = getattr(pantallas, "__all__", [])
    check(pantallas is not None and {"observacion_de_volcado", "evaluar_envio", "compositor_listo", "perfil_activo",
                                     "seleccion_unica", "_nodo", "PantallaInesperada"} <= set(nombres)
          and all(getattr(IG, n, None) is getattr(pantallas, n) for n in nombres),
          "(M-8) los lectores puros viven en instagram_pantallas y instagram_feed los reexporta")
    fuente = pathlib.Path(pantallas.__file__).read_text(encoding="utf-8") if pantallas else ""
    prohibidas = ("telefono.volcado", "telefono.tocar", "telefono.tecla", "telefono.captura", "telefono.shell",
                  "telefono.adb", "telefono.estado(", "telefono.teclado", "telefono.lanzar", "import time",
                  "phone_clipboard")
    check(bool(fuente) and not [p for p in prohibidas if p in fuente],
          f"(M-8) instagram_pantallas no hace E/S ({[p for p in prohibidas if p in fuente]})")

    check(IG.hay_desplegable_hashtags(jerarquia(nodo_xml("[0,1500][300,1600]", texto="#citas",
                                                         paquete="com.samsung.android.honeyboard"))),
          "sin paquete, cualquier # fuera del campo cuenta como desplegable")
    check(not IG.hay_desplegable_hashtags(jerarquia(nodo_xml("[0,1500][300,1600]", texto="#citas",
                                                             paquete="com.samsung.android.honeyboard")),
                                          paquete=PAQUETE_IG),
          "con paquete, las sugerencias del teclado no son el desplegable de Instagram")

    check(IG.partager_pulsable(comp), "una etiqueta dentro de un botón pulsable se puede pulsar")
    desactivado = xml_compositor(boton=nodo_xml(
        "[45,2081][1035,2205]", clase="android.widget.Button", extra='clickable="true" enabled="false"',
        hijos=nodo_xml("[480,2115][600,2170]", texto="Partager")))
    inerte = xml_compositor(boton=nodo_xml("[45,2081][1035,2205]", clase="android.widget.Button",
                                           hijos=nodo_xml("[480,2115][600,2170]", texto="Partager")))
    for xml, label in ((desactivado, "botón desactivado"), (inerte, "sin nada pulsable")):
        problemas = IG.compositor_listo(xml, PIE_PRUEBA, tema)
        check(problemas == ["Partager no pulsable"], f"compositor_listo detecta Partager no pulsable: {label}")
    directo = xml_compositor(boton=nodo_xml("[45,2081][1035,2205]", texto="Partager", clase="android.widget.Button",
                                            extra='clickable="true"'))
    check(IG.compositor_listo(directo, PIE_PRUEBA, tema) == [], "un botón con el texto y pulsable está listo")

    grande = jerarquia(nodo_xml("[0,1800][1080,2340]", desc="Partager", clase="android.widget.FrameLayout",
                                hijos=nodo_xml("[45,2081][1035,2205]", desc="Partager",
                                               clase="android.widget.Button", extra='clickable="true"')))
    elegido = IG._nodo(grande, texto="Partager")
    check(elegido["clase"] == "android.widget.Button" and elegido["bounds"] == (45, 2081, 1035, 2205),
          "contenedor y botón con la misma desc: elige el único pulsable")
    ninguno = grande.replace(' clickable="true"', "")
    check(IG._nodo(ninguno, texto="Partager")["bounds"] == (45, 2081, 1035, 2205),
          "sin un único pulsable, elige el de menor área")
    fuera_pulsable = grande.replace(' clickable="true"', "").replace(
        'class="android.widget.FrameLayout"', 'class="android.widget.FrameLayout" clickable="true"')
    check(IG._nodo(fuera_pulsable, texto="Partager")["clase"] == "android.widget.FrameLayout",
          "si solo el contenedor es pulsable, elige el contenedor")

    check(T.nodos(fino)[0]["profundidad"] == 0 and T.buscar(fino, texto="Partager")["profundidad"] == 1,
          "nodos() da la profundidad en el árbol")
    check(T.plazos_volcado(30) == (20, 10), "un volcado de 30 s: 20 para volcar y 10 para leer")
    check(all(min(T.plazos_volcado(t)) >= 5 for t in range(1, 61)), "cada parte del volcado tiene 5 s como mínimo")
    check(T.es_png(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8), "reconoce la firma PNG")
    check(not T.es_png(b"") and not T.es_png(b"error: device offline"), "una captura vacía o de texto no es PNG")

    import phone_clipboard
    args = phone_clipboard.argumentos_servidor(0x2A)
    check(args[:4] == ["adb", "-s", phone_clipboard.SERIAL, "shell"], "scrcpy-server se lanza por adb shell")
    check(all(a in args for a in ("power_on=false", "control=true", "video=false", "audio=false", "scid=0000002a")),
          "scrcpy-server sin POWER al arrancar, solo control y scid de 8 cifras hex")

    shell_original = T.shell
    try:
        T.shell = lambda cmd, timeout=60: "  mInputShown=true\n"
        leido = T.teclado_estado()

        def sin_adb(cmd, timeout=60):
            raise T.TelefonoError("sin adb")
        T.shell = sin_adb
        desconocido, visible = T.teclado_estado(), T.teclado_visible()
    finally:
        T.shell = shell_original
    check(leido is True and desconocido is None and visible is True,
          "teclado_estado da None si no se puede leer y teclado_visible lo da por abierto")

    print("   · (Task 10f) ventanas emergentes: el desplegable de hashtags es una ventana aparte")
    dumpsys_popup = """  Window #11 Window{49fd424 u0 PopupWindow:de536c5}:
    mDisplayId=0 rootTaskId=1 mSession=Session{3c0b2c1 12345:u0a10234} mClient=android.os.BinderProxy@8b0a1f0
    mOwnerUid=10234 showForAllUsers=false package=com.instagram.android appop=NONE
    mAttrs={(0,1448)(1080xwrap) gr=TOP START CENTER DISPLAY_CLIP_VERTICAL sim={state=unchanged adjust=resize} ty=APPLICATION_PANEL surfaceInsets=Rect(0, 0 - 0, 0) (manual)
    mParentWindow=Window{e654062 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity} mLayoutAttached=true
    mViewVisibility=0x0 mHaveFrame=true mObscured=false
    mHasSurface=true isReadyForDisplay()=true mWindowRemovalAllowed=false
    Frames: parent=[0,0][1080,2340] display=[0,92][1080,2205] frame=[0,1448][1080,2205] last=[0,1448][1080,2205] insetsChanged=false
    isVisible=true
  Window #12 Window{2e76a1 u0 KHCD.0OKT}:
    mAttrs={(0,0)(1xfill) sim={adjust=resize} ty=APPLICATION_ATTACHED_DIALOG fmt=TRANSLUCENT
    mParentWindow=Window{e654062 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity} mLayoutAttached=false
    mViewVisibility=0x0 mHaveFrame=true mObscured=false
    mHasSurface=true isReadyForDisplay()=true mWindowRemovalAllowed=false
    Frames: parent=[0,92][1080,2205] display=[0,92][1080,2205] frame=[539,92][540,2205] last=[539,92][540,2205] insetsChanged=false
    isVisible=true
  Window #13 Window{e654062 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity}:
    mAttrs={(0,0)(fillxfill) sim={adjust=resize forwardNavigation} ty=BASE_APPLICATION fmt=TRANSPARENT wanim=0x10302f6
    isVisible=true
"""
    popup_esperado = {"nombre": "PopupWindow:de536c5", "frame": (0, 1448, 1080, 2205), "ancho_padre": 1080}
    check(T.ventanas_emergentes_de(dumpsys_popup, PAQUETE_IG) == [popup_esperado],
          "(10f) el lector puro extrae la PopupWindow visible del paquete, con su frame y el ancho del padre")
    sin_popup = dumpsys_popup[dumpsys_popup.index("  Window #12"):]
    check(T.ventanas_emergentes_de(sin_popup, PAQUETE_IG) == [],
          "(10f) sin el bloque PopupWindow no hay emergentes")
    check(T.ventanas_emergentes_de(dumpsys_popup, "com.other.app") == [],
          "(I-1) pedir otro paquete (que no aparece en el texto) no cuenta")
    otro_paquete_en_ambos = dumpsys_popup.replace("com.instagram.android", "com.other.app")
    check(T.ventanas_emergentes_de(otro_paquete_en_ambos, PAQUETE_IG) == [],
          "(I-1) otro paquete tanto en package= como en mParentWindow: no cuenta")
    padre_de_otra_subventana = dumpsys_popup.replace(
        "mParentWindow=Window{e654062 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity} mLayoutAttached=true",
        "mParentWindow=Window{e654062 u0 com.android.systemui/com.android.systemui.SomeDialog} mLayoutAttached=true", 1)
    check(T.ventanas_emergentes_de(padre_de_otra_subventana, PAQUETE_IG) == [popup_esperado],
          "(I-1) mParentWindow de otra subventana pero package=com.instagram.android propio: cuenta igual")
    check(T.ventanas_emergentes_de(dumpsys_popup.replace("isVisible=true", "isVisible=false", 1), PAQUETE_IG) == [],
          "(I-1) isVisible=false explícito: no cuenta")
    sin_isvisible = dumpsys_popup.replace("    isVisible=true\n", "", 1)
    check(T.ventanas_emergentes_de(sin_isvisible, PAQUETE_IG) == [popup_esperado],
          "(I-1) sin isVisible pero con mHasSurface=true: cuenta (falla cerrado)")
    check(T.ventanas_emergentes_de("", PAQUETE_IG) == [], "(10f) texto vacío: lista vacía")

    dumpsys_formato_antiguo = """  Window #7 Window{1a2b3c4 u0 PopupWindow:abc123}:
    mOwnerUid=10234 showForAllUsers=false package=com.instagram.android appop=NONE
    mParentWindow=Window{e654062 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity} mLayoutAttached=true
    mHasSurface=true
    mFrame=[10,1500][1070,2100]
    isVisible=true
"""
    check(T.ventanas_emergentes_de(dumpsys_formato_antiguo, PAQUETE_IG)
          == [{"nombre": "PopupWindow:abc123", "frame": (10, 1500, 1070, 2100), "ancho_padre": None}],
          "(I-1) formato antiguo mFrame=[..][..] (sin línea Frames:): se lee igual, sin ancho de padre")

    dumpsys_sin_frame = """  Window #8 Window{9f8e7d6 u0 PopupWindow:sinframe}:
    mOwnerUid=10234 showForAllUsers=false package=com.instagram.android appop=NONE
    mParentWindow=Window{e654062 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity} mLayoutAttached=true
    mHasSurface=true
    isVisible=true
"""
    emergente_sin_frame = T.ventanas_emergentes_de(dumpsys_sin_frame, PAQUETE_IG)
    check(emergente_sin_frame == [{"nombre": "PopupWindow:sinframe", "frame": None, "ancho_padre": None}],
          "(I-1) sin frame legible: la entrada lleva frame None en vez de descartarse")

    shell_original = T.shell
    try:
        T.shell = lambda cmd, timeout=60: dumpsys_popup
        via_shell = T.ventanas_emergentes(PAQUETE_IG)

        def falla_dumpsys(cmd, timeout=60):
            raise T.TelefonoError("adb no responde")
        T.shell = falla_dumpsys
        fallo = lanza(lambda: T.ventanas_emergentes(PAQUETE_IG), T.TelefonoError)
    finally:
        T.shell = shell_original
    check(via_shell == [popup_esperado],
          "(10f) ventanas_emergentes aplica el lector a la salida de dumpsys")
    check(fallo is not None, "(10f) si dumpsys falla, ventanas_emergentes falla cerrado con TelefonoError")

    print("   · (Task 10f) emergente_desplegable / hay_desplegable_por_ventana: solape con la fila de música o «Partager»")
    check(IG.hay_desplegable_por_ventana(comp, emergente_sin_frame) is True,
          "(I-1) una emergente con frame None cuenta como desplegable abierto, sin importar el solape")
    sin_referencias = jerarquia()  # ni «Partager» ni fila de música: nada con qué descartar la emergente
    cualquier_emergente = [{"nombre": "PopupWindow:x", "frame": (0, 0, 10, 10), "ancho_padre": None}]
    check(IG.hay_desplegable_por_ventana(sin_referencias, cualquier_emergente) is True,
          "(I-2) sin «Partager» ni fila de música en el volcado, cualquier emergente del paquete cuenta (falla cerrado)")
    sin_solape = [{"nombre": "PopupWindow:lejos", "frame": (0, 0, 1080, 500), "ancho_padre": 1080}]
    check(IG.hay_desplegable_por_ventana(comp, sin_solape) is False,
          "(m-4) con «Partager» en el volcado, una emergente que no se solapa no cuenta")
    bordes_que_se_tocan = [{"nombre": "PopupWindow:toca", "frame": (0, 2000, 1080, 2115), "ancho_padre": 1080}]
    check(IG.hay_desplegable_por_ventana(comp, bordes_que_se_tocan) is False,
          "(m-4) bordes que se tocan (y2 de la emergente == y1 de «Partager») no cuenta como solape")

    print("   · (m-2) diagnóstico: el problema y el mensaje nombran la emergente culpable")
    emergente_diagnostico = [popup_esperado]
    problemas_diag = IG.compositor_listo(comp, PIE_PRUEBA, tema, emergente_diagnostico)
    check(len(problemas_diag) == 1 and "PopupWindow:de536c5" in problemas_diag[0]
          and "(0, 1448, 1080, 2205)" in problemas_diag[0],
          f"(m-2) compositor_listo nombra la emergente y su frame en el problema ({problemas_diag})")

    print("   · teléfono simulado")
    import time as reloj
    sleep_original, monotonic_original = reloj.sleep, reloj.monotonic
    evid = pathlib.Path("evidencia-simulada")
    centro = T.buscar(comp, texto="Partager")["centro"]
    perfil_centro = T.buscar(feed, texto="Profil")["centro"]
    publicado = [comp, comp, xml_inicio(banner=True), feed, feed, feed, xml_perfil()]

    sim = TelefonoSimulado(publicado)
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "confirmado" and res["publicaciones_despues"] == 3712,
          f"(a) banner, inicio limpio y perfil +1: confirmado ({err or res['estado']})")
    check(sim.toques.count(centro) == 1 and sim.toques[0] == centro and sim.toques[1:] == [perfil_centro],
          f"(a) un solo toque en Partager y luego Profil ({sim.toques})")
    check(sim.capturas == ["ig-05a-antes.png", "ig-05-publicado.png"] and res["processing_completed_at"],
          "(a) captura antes, captura después y hora de fin")
    check(not sim.prohibidos, "(a) sin E/S real")

    sim = TelefonoSimulado(publicado)
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, None))
    check(err is None and res["estado"] == "confirmado_sin_conteo" and sim.toques.count(centro) == 1,
          f"(b) sin conteo previo: confirmado_sin_conteo con un solo toque ({err or res['estado']})")

    sim = TelefonoSimulado([comp, comp, xml_inicio(banner=True), feed, feed, feed,
                            xml_perfil(publicaciones="3 713publications")])
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "conteo_no_cuadra", f"perfil +2: conteo_no_cuadra ({err or res['estado']})")

    sim = TelefonoSimulado([comp, comp, xml_inicio(banner=True), xml_inicio(aviso="Impossible de publier. Réessayer")])
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "fallido" and sim.toques.count(centro) == 1,
          f"(c) banner y luego aviso de error: fallido con un solo toque ({err or res['estado']})")
    check(any("Impossible de publier. Réessayer" in a for a in res["avisos"]),
          f"(10e) compartir copia el texto del aviso de fallo a avisos ({res['avisos']})")

    sim = TelefonoSimulado([comp], falla_tocar=T.TelefonoError("device offline"))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "error_tras_pulsar" and res["error"].startswith("TelefonoError")
          and res["submitted_at"] and res["captura_antes"] and len(sim.toques) == 1,
          f"(d) el toque falla: error_tras_pulsar, un intento y nada se escapa ({err or res})")
    check(err is None and sim.capturas == ["ig-05a-antes.png", "ig-05-error.png"]
          and str(res.get("captura_error")).endswith("ig-05-error.png"),
          f"(M-3) tras error_tras_pulsar queda la captura ig-05-error.png ({sim.capturas}, {res and res.get('captura_error')})")
    plazo_error = sim.plazos_captura[-1] if len(sim.plazos_captura) == 2 else None
    check(isinstance(plazo_error, (int, float)) and 0 < plazo_error <= 10,
          f"(10d) la captura best-effort del error espera como mucho 10 s ({sim.plazos_captura})")

    sim = TelefonoSimulado([comp], falla_tocar=T.TelefonoError("device offline"))
    captura_normal = sim.captura

    def captura_rota(destino, timeout=None):
        if destino.name == "ig-05-error.png":
            raise OSError(5, "Input/output error")
        return captura_normal(destino, timeout=timeout)
    sim.captura = captura_rota
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "error_tras_pulsar" and res["error"].startswith("TelefonoError")
          and "captura_error" in res and res["captura_error"] is None,
          f"(M-3) si la captura del error también falla, el resultado vuelve igual ({err or res})")

    sim = TelefonoSimulado(publicado)
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711, produccion_cercana=True))
    check(err is None and res["estado"] == "confirmado_sin_conteo" and res["publicaciones_despues"] == 3712
          and sim.toques.count(centro) == 1,
          f"(M-1) con producción cercana un confirmado baja a confirmado_sin_conteo ({err or res['estado']})")
    sim = TelefonoSimulado([comp, comp, xml_inicio(banner=True), xml_inicio(aviso="Impossible de publier. Réessayer")])
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711, produccion_cercana=True))
    check(err is None and res["estado"] == "fallido",
          f"(M-1) con producción cercana un fallido sigue siendo fallido ({err or res['estado']})")
    feed_pie = xml_inicio(pie_ajeno=pie_con_fallo)
    sim = TelefonoSimulado([comp, comp, xml_inicio(banner=True, pie_ajeno=pie_con_fallo), feed_pie, feed_pie, feed_pie,
                            xml_perfil()])
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "confirmado",
          f"(M-2) un pie ajeno con «Réessayer» en el inicio no convierte el envío en fallido ({err or res['estado']})")
    sim = TelefonoSimulado([comp, comp, banner_bajo_solo, fallo_bajo])
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "fallido" and sim.toques.count(centro) == 1,
          f"(10d) compartir recuerda el banner de un volcado anterior: el aviso largo de después da fallido ({err or res['estado']})")

    sim_obs = TelefonoSimulado([comp, comp, T.TelefonoError("volcado no válido")])
    res, err = con_telefono_simulado(sim_obs, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "timeout" and len(sim_obs.toques) == 1,
          f"sin volcados válidos tras pulsar: timeout y un solo toque ({err or res['estado']})")

    sim = TelefonoSimulado([xml_compositor(despues=LISTA_HASHTAGS)])
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(isinstance(err, IG.PantallaInesperada) and not isinstance(err, IntentoDeES) and sim.toques == [],
          f"(e) desplegable abierto: PantallaInesperada sin tocar ({err!r})")

    sim = TelefonoSimulado([comp], teclado=(True,))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(isinstance(err, IG.PantallaInesperada) and sim.toques == [] and sim.capturas == [],
          "con el teclado abierto no se captura ni se toca")

    sim = TelefonoSimulado([comp], teclado=(None,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and "teclado" in str(err) and sim.teclas == []
          and sim.pegados == [PIE_PRUEBA], f"(f) teclado ilegible tras pegar: se para sin «atrás» ({err!r})")

    sim = TelefonoSimulado([comp], teclado=(True, False))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [IG.ATRAS] and sim.capturas == ["ig-04-compositor.png"]
          and sim.combinaciones == [(IG.CTRL_IZQ, IG.TECLA_A)],
          f"(g) teclado abierto y luego cerrado: exactamente un «atrás» ({err!r}, {sim.teclas})")

    print("   · (10e) el desplegable de hashtags puede tardar unos segundos en aparecer tras pegar")
    desplegable = xml_compositor(despues=LISTA_HASHTAGS)
    otra_app = jerarquia(nodo_xml("[0,0][1080,2340]", texto="Écran verrouillé", paquete="com.android.systemui"))

    sim = TelefonoSimulado([comp, comp, desplegable, comp], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [] and sim.capturas == ["ig-04-compositor.png"],
          f"(M-2) el desplegable se cierra solo: se confirma con un volcado fresco y no se pulsa «atrás» "
          f"({err!r}, {sim.teclas}, {sim.capturas})")

    sim = TelefonoSimulado([comp, comp, desplegable, desplegable, comp], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [IG.ATRAS] and sim.capturas == ["ig-04-compositor.png"],
          f"(10e-a) el desplegable sigue abierto tras confirmarlo con un volcado fresco: "
          f"exactamente un «atrás», compositor capturado ({err!r}, {sim.teclas}, {sim.capturas})")

    sim = TelefonoSimulado([desplegable], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and sim.teclas == [IG.ATRAS, IG.ATRAS]
          and "ig-04-compositor.png" not in sim.capturas,
          f"(10e-b) el desplegable sigue abierto tras 2 «atrás»: PantallaInesperada, "
          f"exactamente 2 «atrás» y sin captura del compositor ({err!r}, {sim.teclas}, {sim.capturas})")

    sim = TelefonoSimulado([comp, comp, otra_app], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and sim.teclas == [] and "ig-04-compositor.png" not in sim.capturas,
          f"(I-2) otra pantalla delante en el bucle de limpios: PantallaInesperada, sin «atrás» ni captura "
          f"({err!r}, {sim.teclas}, {sim.capturas})")

    sim = TelefonoSimulado([comp], teclado=(False,))

    def reloj_veloz():
        sim.reloj += 40
        return sim.reloj
    sim.monotonic = reloj_veloz
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and str(IG.ESTABILIZACION_TIMEOUT_S) in str(err)
          and sim.teclas == [] and "ig-04-compositor.png" not in sim.capturas,
          f"(M-1) el bucle de estabilización tiene un tope total: PantallaInesperada sin captura ({err!r})")

    guion_reinicio = [comp, comp, comp, desplegable, desplegable, comp, comp, desplegable, desplegable,
                      comp, comp, comp]
    sim = TelefonoSimulado(guion_reinicio, teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [IG.ATRAS, IG.ATRAS] and sim.capturas == ["ig-04-compositor.png"],
          f"(M-7-i) el desplegable reaparece dos veces: cada «atrás» reinicia la cuenta de limpios "
          f"(sin reinicio saldría solo un «atrás») ({err!r}, {sim.teclas})")

    guion_teclado_y_desplegable = [comp, comp, comp, comp, desplegable, desplegable, comp, comp, comp]
    sim = TelefonoSimulado(guion_teclado_y_desplegable, teclado=(True, False))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [IG.ATRAS, IG.ATRAS] and sim.capturas == ["ig-04-compositor.png"],
          f"(M-7-ii) teclado abierto y luego un desplegable tardío: agotan los 2 «atrás» y aun así "
          f"termina bien ({err!r}, {sim.teclas})")

    sim = TelefonoSimulado([comp], falla_pegar=RuntimeError("no se pudo hablar con scrcpy-server"))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, T.TelefonoError) and str(err).startswith("portapapeles:") and sim.teclas == [],
          f"un fallo del portapapeles sale como TelefonoError ({err!r})")

    sim = TelefonoSimulado([comp], listo=False)
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.TelefonoNoListo) and sim.toques == [] and sim.pegados == [],
          "con el teléfono no listo no se toca ni se pega")

    subida = datetime(2026, 9, 14, 8, 39, tzinfo=timezone.utc)
    sim = TelefonoSimulado([comp])
    res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
    check(isinstance(err, IG.BorradorPendiente) and sim.toques == [], "abrir con un borrador a medias: no se toca")
    check(sim.orden == ["cortina", f"lanzar:{IG.PAQUETE}"],
          f"(10e) abrir cierra la cortina de notificaciones una vez antes de lanzar Instagram ({sim.orden})")

    sim = TelefonoSimulado([comp], falla_cortina=T.TelefonoError("cortina no disponible"))
    res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
    check(isinstance(err, IG.BorradorPendiente) and sim.orden == ["cortina", f"lanzar:{IG.PAQUETE}"],
          f"(M-5) cerrar_cortina falla: abrir sigue adelante y lanza Instagram igual ({err!r}, {sim.orden})")

    print("   · seguimiento de la revisión (10b): teclado, «#» ajeno y pantalla de arranque")
    sim = TelefonoSimulado([comp], teclado=(True, None))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and not isinstance(err, IntentoDeES) and sim.teclas == [IG.ATRAS]
          and "ig-04-compositor.png" not in sim.capturas,
          f"(M-6) teclado abierto y luego ilegible: exactamente un «atrás» y PantallaInesperada ({err!r}, {sim.teclas})")
    sugerencia = nodo_xml("[0,1500][300,1600]", texto="#citas", paquete="com.samsung.android.honeyboard")
    sim = TelefonoSimulado([xml_compositor(despues=sugerencia)], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [] and sim.capturas == ["ig-04-compositor.png"],
          f"(M-6) un «#» de otra aplicación con el teclado cerrado: ningún «atrás» ({err!r}, {sim.teclas})")
    arranque = jerarquia(nodo_xml("[340,1000][740,1400]", desc="Instagram", clase="android.widget.ImageView"))
    menu_crear = jerarquia(nodo_xml("[100,1500][980,1650]", texto="Publication"))
    sim = TelefonoSimulado([arranque, xml_inicio(), xml_perfil(), menu_crear, SELECTOR_IG])
    res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
    check(err is None and sim.toques.count(perfil_centro) == 1 and sim.toques[:1] == [perfil_centro]
          and res["publicaciones_antes"] == 3712 and sim.capturas == ["ig-01-selector.png"],
          f"(M-6) abrir con pantalla de arranque y luego el inicio: exactamente un toque en Profil ({err!r}, {sim.toques})")
    check(sim.orden[:1] == ["cortina"],
          f"(M-7-iv) en el camino feliz de abrir, cerrar_cortina se llama antes de todo lo demás ({sim.orden})")

    print("   · (Task 10f) el desplegable de hashtags como ventana emergente (uiautomator dump no la ve)")
    # ancha (ocupa el 100% del padre): parece_desplegable la trata como el desplegable de verdad.
    emergente_abierta = [{"nombre": "PopupWindow:de536c5", "frame": (0, 1448, 1080, 2205), "ancho_padre": 1080}]
    # estrecha (menos del 90% del padre) pero se solapa con «Partager»: un tooltip no enfocable,
    # no el desplegable; escribir_pie debe pararse sin pulsar «atrás» y compartir sin tocar.
    emergente_estrecha = [{"nombre": "PopupWindow:tooltip1", "frame": (400, 2100, 500, 2180), "ancho_padre": 1080}]
    problema_ancha = IG.compositor_listo(comp, PIE_PRUEBA, tema, emergente_abierta)
    check(len(problema_ancha) == 1 and problema_ancha[0].startswith("desplegable de hashtags abierto (")
          and "PopupWindow:de536c5" in problema_ancha[0] and "(0, 1448, 1080, 2205)" in problema_ancha[0],
          f"(10f, m-2) compositor_listo con una emergente que se solapa con «Partager» añade el problema, "
          f"con nombre y frame ({problema_ancha})")
    check(IG.compositor_listo(comp, PIE_PRUEBA, tema) == [],
          "(10f) sin el parámetro emergentes, compositor_listo se comporta como antes")
    check(IG.compositor_listo(comp, PIE_PRUEBA, tema, []) == [],
          "(10f) con una lista de emergentes vacía, compositor_listo se comporta como antes")
    check(IG.compositor_listo(comp, PIE_PRUEBA, tema, emergente_estrecha) != [],
          "(m-1) compartir/compositor_listo no filtra por ancho: una emergente estrecha que se solapa también cuenta")

    # 1ª llamada (comprobación inicial) y 2ª (confirmación tras «no teclado y desplegable»): abierta;
    # 3ª en adelante (tras el «atrás»): cerrada.
    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_abierta, emergente_abierta, ()))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [IG.ATRAS] and sim.capturas == ["ig-04-compositor.png"],
          f"(10f) la emergente se ve en dos volcados (incluida la confirmación) y luego se cierra tras el «atrás»: "
          f"exactamente un «atrás» y captura ({err!r}, {sim.teclas}, {sim.capturas})")

    # todas las llamadas devuelven la misma emergente abierta: nunca se cierra.
    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_abierta,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and sim.teclas == [IG.ATRAS, IG.ATRAS]
          and "ig-04-compositor.png" not in sim.capturas
          and "PopupWindow:de536c5" in str(err) and "(0, 1448, 1080, 2205)" in str(err),
          f"(10f, m-2) la emergente persiste: PantallaInesperada con nombre y frame, exactamente 2 «atrás» "
          f"y sin captura ({err!r}, {sim.teclas}, {sim.capturas})")

    # todas las llamadas devuelven la misma emergente abierta.
    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_abierta,))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(isinstance(err, IG.PantallaInesperada) and not isinstance(err, IntentoDeES) and sim.toques == [],
          f"(10f) compartir con volcados limpios pero una emergente abierta: PantallaInesperada y ningún toque "
          f"({err!r}, {sim.toques})")

    print("   · (m-1) una emergente estrecha que se solapa no es el desplegable: no se pulsa «atrás»")
    # todas las llamadas devuelven la misma emergente estrecha: nunca «parece» el desplegable.
    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_estrecha,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and sim.teclas == [] and sim.capturas == []
          and "PopupWindow:tooltip1" in str(err),
          f"(m-1) escribir_pie con una emergente estrecha que se solapa: PantallaInesperada sin «atrás» "
          f"({err!r}, {sim.teclas}, {sim.capturas})")

    # todas las llamadas devuelven la misma emergente estrecha.
    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_estrecha,))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(isinstance(err, IG.PantallaInesperada) and not isinstance(err, IntentoDeES) and sim.toques == [],
          f"(m-1) compartir con una emergente estrecha que se solapa: PantallaInesperada igual, sin tocar "
          f"({err!r}, {sim.toques})")

    # única entrada: TelefonoError en cada llamada a ventanas_emergentes.
    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(T.TelefonoError("dumpsys no responde"),))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(isinstance(err, T.TelefonoError) and not isinstance(err, IntentoDeES) and sim.toques == [],
          f"(10f) si ventanas_emergentes falla dentro de compartir, falla cerrado sin tocar ({err!r}, {sim.toques})")

    # única entrada: TelefonoError en cada llamada a ventanas_emergentes dentro de _estado_cierre.
    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(T.TelefonoError("dumpsys no responde"),))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, T.TelefonoError) and not isinstance(err, IntentoDeES) and sim.teclas == []
          and sim.capturas == [],
          f"(m-4) si ventanas_emergentes falla dentro de escribir_pie, se propaga sin pulsar «atrás» "
          f"({err!r}, {sim.teclas}, {sim.capturas})")

    print("   · seguimiento de la revisión (10b): captura sin disco y parada del portapapeles")
    import io
    import subprocess as sp
    import tempfile
    adb_original = T.adb
    plazos_adb: list = []
    try:
        def adb_png(*args, timeout=60):
            plazos_adb.append(timeout)
            return sp.CompletedProcess(args, 0, stdout=b"\x89PNG\r\n\x1a\n" + b"\0" * 8, stderr=b"")
        T.adb = adb_png
        with tempfile.TemporaryDirectory() as d:
            archivo = pathlib.Path(d) / "soy-un-archivo"
            archivo.write_text("x", encoding="utf-8")
            try:
                T.captura(archivo / "sub" / "x.png")
                tipo_error = None
            except Exception as e:  # noqa: BLE001
                tipo_error = type(e)
            buena = T.captura(pathlib.Path(d) / "ev" / "x.png")
            check(tipo_error is T.TelefonoError and buena.is_file(),
                  f"(M-4) captura convierte el OSError del disco en TelefonoError ({tipo_error})")
            plazos_adb.clear()
            T.captura(pathlib.Path(d) / "ev" / "normal.png")
            try:
                T.captura(pathlib.Path(d) / "ev" / "corta.png", timeout=7)
            except TypeError:
                pass
            check(plazos_adb[-1:] == [7] and plazos_adb[:1] == [60],
                  f"(10d) captura pasa su timeout a adb y por defecto sigue en 60 s ({plazos_adb})")
    finally:
        T.adb = adb_original

    class PopenFalso:
        def __init__(self, respuestas: list, falla_wait: BaseException | None = None):
            self.respuestas = list(respuestas)
            self.falla_wait = falla_wait
            self.llamadas: list = []
            self.stdout = io.StringIO()

        def wait(self, timeout=None):
            self.llamadas.append(("wait", timeout))
            if self.falla_wait is not None:
                raise self.falla_wait
            return -9

        def poll(self):
            return None

        def terminate(self):
            self.llamadas.append("terminate")

        def kill(self):
            self.llamadas.append("kill")

        def communicate(self, timeout=None):
            self.llamadas.append(("communicate", timeout))
            r = self.respuestas.pop(0)
            if isinstance(r, BaseException):
                raise r
            return r, None

    atascado = PopenFalso([sp.TimeoutExpired("scrcpy", 5), sp.TimeoutExpired("scrcpy", 5)])
    try:
        salida_parar, escapo = phone_clipboard._parar(atascado), None
    except Exception as e:  # noqa: BLE001
        salida_parar, escapo = None, e
    check(escapo is None and salida_parar == ""
          and atascado.llamadas == ["terminate", ("communicate", 5), "kill", ("communicate", 5), ("wait", 1)]
          and atascado.stdout.closed,
          f"(M-7, 10d) _parar espera 5 s también tras kill, ignora un segundo timeout, cierra stdout y recoge "
          f"con wait(1) ({escapo!r}, {atascado.llamadas})")
    zombi = PopenFalso([sp.TimeoutExpired("scrcpy", 5), sp.TimeoutExpired("scrcpy", 5)],
                       falla_wait=sp.TimeoutExpired("scrcpy", 1))
    try:
        salida_zombi, escapo = phone_clipboard._parar(zombi), None
    except Exception as e:  # noqa: BLE001
        salida_zombi, escapo = None, e
    check(escapo is None and salida_zombi == "" and zombi.llamadas[-1:] == [("wait", 1)],
          f"(10d) si wait(1) también agota el tiempo, _parar vuelve igual ({escapo!r}, {zombi.llamadas})")
    lento = PopenFalso([sp.TimeoutExpired("scrcpy", 5), "adiós\n"])
    check(phone_clipboard._parar(lento) == "adiós\n" and lento.llamadas[-1] == ("communicate", 5),
          "(M-7) si tras kill el servidor sale, _parar devuelve lo que escribió")

    lanzador = jerarquia(nodo_xml("[0,0][1080,200]", texto="Inicio")).replace(PAQUETE_IG, "com.sec.android.app.launcher")
    sim = TelefonoSimulado([lanzador])
    res, err = con_telefono_simulado(sim, lambda: IG.atras(evid, "x"))
    check(isinstance(err, IG.PantallaInesperada) and sim.teclas == [], "atrás sin Instagram en primer plano no se pulsa")

    sim = TelefonoSimulado([comp])
    con_telefono_simulado(sim, lambda: (_ for _ in ()).throw(RuntimeError("escenario roto")))
    check(reloj.sleep is sleep_original and reloj.monotonic is monotonic_original
          and T.volcado.__name__ == "volcado" and T.tocar.__name__ == "tocar"
          and phone_clipboard.pegar.__name__ == "pegar",
          "los sustitutos se restauran aunque el escenario falle")


def _rechaza_familia(E, t) -> bool:
    try:
        E.nuevo("ENC-20260915-010", coverage_cell_ids=["C"], family_id="LAB X;rm", brief_path="b",
                do_not_use=[], formato={"ancho": 1080, "alto": 1350}, prompt="p", restricciones=[],
                destino_assets="experiments/media-lab/assets/LAB X;rm", ahora=t)
        return False
    except E.EncargoError:
        return True


def seccion_codex() -> None:
    print("\n7. Rescate con codex exec")
    import hashlib
    import tempfile
    from datetime import datetime, timezone
    from labkit import codex_rescate as R, encargos as E

    t = datetime(2026, 9, 15, 8, 40, tzinfo=timezone.utc)
    enc = E.nuevo("ENC-20260915-003", coverage_cell_ids=["C1"], family_id="LAB-F01-001",
                  brief_path="b", do_not_use=["no inventar inscripciones"], formato={"ancho": 1080, "alto": 1350},
                  prompt="Un astrolabio", restricciones=["sin texto"],
                  destino_assets="experiments/media-lab/assets/LAB-F01-001", ahora=t, variantes=2)
    check(R.rutas_imagen(enc) == ["experiments/media-lab/assets/LAB-F01-001/ENC-20260915-003-v1.png",
                                  "experiments/media-lab/assets/LAB-F01-001/ENC-20260915-003-v2.png"],
          "una ruta por variante dentro de destino_assets")
    p = R.prompt_para(enc)
    check("codex-generado --encargo ENC-20260915-003 --owner codex-exec" in p, "el prompt usa lab.py para marcar generado")
    check("No uses adb" in p and "No publiques" in p, "el prompt prohíbe publicar y usar el teléfono")
    check("<<<ENCARGO" in p and "ENCARGO>>>" in p and "- sin texto" in p and "- no inventar inscripciones" in p,
          "el encargo va delimitado y con sus restricciones en viñetas")
    cmd = R.comando(p, pathlib.Path("/tmp/salida.json"))
    check(cmd[:2] == [R.CODEX, "exec"] and cmd[cmd.index("-s") + 1] == "workspace-write"
          and "--output-schema" in cmd and cmd[-1] == p, "comando con sandbox workspace-write y esquema")

    from PIL import Image

    def png(ruta: pathlib.Path, ancho: int, alto: int, tipo: str = "PNG") -> str:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (ancho, alto), (120, 90, 60)).save(ruta, tipo)
        return hashlib.sha256(ruta.read_bytes()).hexdigest()

    def generado(raiz: pathlib.Path, imagenes: list[dict]) -> dict:
        e = E.nuevo("ENC-20260915-003", coverage_cell_ids=["C1"], family_id="LAB-F01-001", brief_path="b",
                    do_not_use=[], formato={"ancho": 1080, "alto": 1350}, prompt="Un astrolabio",
                    restricciones=["sin texto"], destino_assets="experiments/media-lab/assets/LAB-F01-001",
                    ahora=t, variantes=2)
        E.tomar(e, "codex-exec", t)
        E.marcar_generado(e, "codex-exec", imagenes, t)
        return e

    base = "experiments/media-lab/assets/LAB-F01-001/"
    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d)
        check(R.validar(enc, raiz) == ["estado pedido, se esperaba generado"], "no valida un encargo sin generar")
        v1 = raiz / (base + "ENC-20260915-003-v1.png")
        e_ok = generado(raiz, [{"ruta": base + "ENC-20260915-003-v1.png", "sha256": png(v1, 768, 1152),
                                "ancho": 768, "alto": 1152}])
        check(R.validar(e_ok, raiz) == [], "valida un PNG pedido, íntegro, del tamaño registrado y vertical")
        v1.write_bytes(b"cambiado")
        check(any("hash" in x for x in R.validar(e_ok, raiz)), "detecta un archivo cambiado")
        v1.unlink()
        check(any("no existe" in x for x in R.validar(e_ok, raiz)), "detecta un archivo que falta")

        otra = raiz / (base + "ENC-20260915-099-v1.png")
        e_ajena = generado(raiz, [{"ruta": base + "ENC-20260915-099-v1.png", "sha256": png(otra, 768, 1152),
                                   "ancho": 768, "alto": 1152}])
        check(any("ruta no pedida" in x for x in R.validar(e_ajena, raiz)),
              "rechaza una imagen registrada en una ruta que no se pidió")

        jpg = raiz / (base + "ENC-20260915-003-v2.png")
        e_jpg = generado(raiz, [{"ruta": base + "ENC-20260915-003-v2.png", "sha256": png(jpg, 768, 1152, "JPEG"),
                                 "ancho": 768, "alto": 1152}])
        check(any("no es PNG" in x for x in R.validar(e_jpg, raiz)), "rechaza un JPEG guardado como .png")

        pequena = raiz / (base + "ENC-20260915-003-v1.png")
        e_peq = generado(raiz, [{"ruta": base + "ENC-20260915-003-v1.png", "sha256": png(pequena, 300, 400),
                                 "ancho": 300, "alto": 400}])
        check(any("demasiado pequeña" in x for x in R.validar(e_peq, raiz)), "rechaza una imagen diminuta")

        e_tam = generado(raiz, [{"ruta": base + "ENC-20260915-003-v1.png", "sha256": png(pequena, 768, 1152),
                                 "ancho": 1024, "alto": 1536}])
        check(any("mide 768x1152" in x for x in R.validar(e_tam, raiz)), "detecta dimensiones distintas de las registradas")

        apaisada = raiz / (base + "ENC-20260915-003-v2.png")
        e_hor = generado(raiz, [{"ruta": base + "ENC-20260915-003-v2.png", "sha256": png(apaisada, 1152, 768),
                                 "ancho": 1152, "alto": 768}])
        check(any("orientación" in x for x in R.validar(e_hor, raiz)), "rechaza una imagen apaisada para un formato vertical")

        vacio = dict(e_ok, imagenes=[])
        check("sin imágenes registradas" in R.validar(vacio, raiz), "un generado sin imágenes no valida")

        enlace = raiz / (base + "ENC-20260915-003-v1.png")
        enlace.unlink(missing_ok=True)
        destino_fuera = raiz / "fuera" / "valida.png"
        sha_fuera = png(destino_fuera, 768, 1152)
        enlace.symlink_to(destino_fuera)
        e_enlace = generado(raiz, [{"ruta": base + "ENC-20260915-003-v1.png", "sha256": sha_fuera,
                                    "ancho": 768, "alto": 1152}])
        check(any("enlace simbólico" in x for x in R.validar(e_enlace, raiz)),
              "rechaza un enlace simbólico en la ruta pedida aunque apunte a un PNG válido")

        cuadrada = raiz / (base + "ENC-20260915-003-v2.png")
        e_cuad = generado(raiz, [{"ruta": base + "ENC-20260915-003-v2.png", "sha256": png(cuadrada, 1024, 1024),
                                  "ancho": 1024, "alto": 1024}])
        check(R.validar(e_cuad, raiz) == [], "acepta una imagen cuadrada para un formato vertical 1080x1350")

    check(_rechaza_familia(E, t), "family_id con espacios o ; se rechaza")


def seccion_cli() -> None:
    print("\n8. CLI lab.py: encargos de extremo a extremo en una carpeta temporal")
    import json
    import os
    import subprocess
    import tempfile
    from PIL import Image

    lab = ROOT / "experiments" / "media-lab" / "lab.py"
    with tempfile.TemporaryDirectory() as d:
        cobertura = pathlib.Path(d) / "coverage.json"
        cobertura.write_text(json.dumps({"cells": [{"cell_id": "CELL-900", "platform": "instagram",
                                                    "native_format": "feed_single_image",
                                                    "publishing_route": "api", "status": "planned"}]}),
                             encoding="utf-8")
        env = {**os.environ, "LAB_ENCARGOS_DIR": d, "LAB_COVERAGE": str(cobertura)}

        def lab_cmd(*args):
            r = subprocess.run([sys.executable, str(lab), *args], cwd=ROOT, env=env,
                               capture_output=True, text=True)
            return r.returncode, r.stdout, r.stderr

        prompt = pathlib.Path(d) / "prompt.txt"
        prompt.write_text("Un astrolabio de latón", encoding="utf-8")
        codigo, out, err = lab_cmd("encargo-nuevo", "--cell", "CELL-900", "--family", "LAB-TEST-001",
                                   "--brief", "b.md", "--formato", '{"ancho":1080,"alto":1350}',
                                   "--prompt-file", str(prompt), "--restriccion", "sin texto")
        check(codigo == 0, f"encargo-nuevo funciona {(err or out)[-200:]}")
        eid = json.loads(out)["encargo_id"]
        codigo, out, _ = lab_cmd("codex-tomar", "--owner", "codex-heartbeat", "--max", "2")
        tomados = json.loads(out)
        check(codigo == 0 and [t["encargo_id"] for t in tomados] == [eid], "codex-tomar devuelve el encargo con sus rutas")
        imagen = ROOT / tomados[0]["rutas"][0]
        imagen.parent.mkdir(parents=True, exist_ok=True)
        try:
            Image.new("RGB", (768, 1152), (200, 180, 120)).save(imagen)
            codigo, out, err = lab_cmd("codex-generado", "--encargo", eid, "--owner", "codex-heartbeat",
                                       "--imagen", tomados[0]["rutas"][0])
            check(codigo == 0 and json.loads(out)[0]["ancho"] == 768,
                  f"codex-generado mide la imagen {(err or out)[-200:]}")
            codigo, _, _ = lab_cmd("encargo-revisar", "--encargo", eid, "--aprobado", "--motivo", "prueba")
            check(codigo == 0, "encargo-revisar aprueba")
            enc = json.loads((pathlib.Path(d) / f"{eid}.json").read_text(encoding="utf-8"))
            check(enc["estado"] == "aprobado", "el archivo del encargo queda aprobado")
            codigo, _, err = lab_cmd("codex-generado", "--encargo", eid, "--owner", "codex-heartbeat",
                                     "--imagen", "/etc/hosts")
            check(codigo != 0, "codex-generado rechaza una imagen fuera de destino_assets")
        finally:
            imagen.unlink(missing_ok=True)
            try:
                imagen.parent.rmdir()
            except OSError:
                pass


def seccion_guardia() -> None:
    print("\n9. Guardia de archivos alrededor de codex exec")
    import hashlib
    import subprocess
    import tempfile
    try:
        from labkit import guardia as G
    except ImportError as e:
        check(False, f"existe labkit.guardia ({e})")
        return

    antes = {"a.txt": "h1", "b.txt": "h2", ".env": "h3", "experiments/media-lab/encargos/ENC-1.json": "h4"}
    check(G.cambios_ajenos(antes, dict(antes), set()) == [], "sin cambios no hay ajenos")
    check(G.cambios_ajenos(antes, {**antes, "a.txt": "otro"}, set()) == ["a.txt"], "detecta un archivo cambiado")
    check(G.cambios_ajenos(antes, {**antes, "c.txt": "h5"}, set()) == ["c.txt"], "detecta un archivo añadido")
    check(G.cambios_ajenos(antes, {**antes, ".env": "-"}, set()) == [".env"], "detecta un archivo borrado")
    revertido = {k: v for k, v in antes.items() if k != "b.txt"}
    check(G.cambios_ajenos(antes, revertido, set()) == ["b.txt"],
          "detecta un archivo devuelto a HEAD (sale de git status: unión de claves)")
    check(G.cambios_ajenos(antes, {**antes, "experiments/media-lab/encargos/ENC-1.json": "h9", "a.txt": "x"},
                           {"experiments/media-lab/encargos/ENC-1.json"}) == ["a.txt"],
          "las rutas permitidas no cuentan")
    check(G.cambios_ajenos({}, {"z": "1", "a": "2"}, set()) == ["a", "z"], "los ajenos salen ordenados")

    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d)
        subprocess.run(["git", "init", "-q", str(raiz)], check=True, capture_output=True, timeout=60)

        def escribir(rel: str, datos: bytes = b"x") -> None:
            p = raiz / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(datos)

        (raiz / ".gitignore").write_text("assets/\n__pycache__/\n.env*\n.claude/\n", encoding="utf-8")
        for rel in (".claude/settings.json", "experiments/media-lab/.env.local",
                    "experiments/media-lab/labkit/__pycache__/m.cpython-314.pyc", "assets/sub/carta.jpg",
                    "assets/.DS_Store", ".DS_Store", ".git/hooks/pre-commit"):
            escribir(rel)
        escribir("nuevo.txt", b"hola")
        (raiz / "enlace.txt").symlink_to("nuevo.txt")
        foto = G.estado_git(raiz)
        x = hashlib.sha256(b"x").hexdigest()
        check(foto.get(".claude/settings.json") == x and foto.get(".claude/settings.local.json") == "-",
              "vigila los permisos de Claude aunque estén ignorados (el que falta vale «-»)")
        check(foto.get("experiments/media-lab/.env.local") == x, "vigila experiments/media-lab/.env*")
        check(foto.get("experiments/media-lab/labkit/__pycache__/m.cpython-314.pyc") == x, "vigila los .pyc del laboratorio")
        check(foto.get("assets/sub/carta.jpg") == x, "vigila cualquier archivo de assets/, no solo png")
        check(foto.get(".git/config", "-") != "-" and foto.get(".git/hooks/pre-commit") == x,
              "vigila .git/config y los ganchos de git")
        check(foto.get("nuevo.txt") == hashlib.sha256(b"hola").hexdigest() and foto.get("enlace.txt") == "enlace:nuevo.txt",
              "incluye lo que da git status y anota los enlaces con su destino")
        check(not any(pathlib.PurePosixPath(r).name == ".DS_Store" for r in foto), "ignora los .DS_Store")


_LAB_CLI = None
_VERIFY_CLI = None


def modulo_verify():
    """verify_api.py importado una sola vez como módulo, para llamar a main() en proceso
    con `_get` sustituido por un doble sin red."""
    global _VERIFY_CLI
    if _VERIFY_CLI is None:
        import importlib.util
        ruta = ROOT / "experiments" / "media-lab" / "verify_api.py"
        spec = importlib.util.spec_from_file_location("verify_api_cli", ruta)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        _VERIFY_CLI = modulo
    return _VERIFY_CLI


def modulo_lab():
    """lab.py importado una sola vez como módulo, para llamar a main() en proceso."""
    global _LAB_CLI
    if _LAB_CLI is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lab_cli", ROOT / "experiments" / "media-lab" / "lab.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        _LAB_CLI = modulo
    return _LAB_CLI


class LabAislado:
    """lab.py en proceso con ROOT, encargos, cerrojo, evidencia y cobertura en una carpeta temporal.

    Llamarlo con los argumentos de la CLI devuelve (código, JSON emitido o None, stderr). Si algo
    se escapa de lab.main() (una IntentoDeES o un error sin capturar) el código es None."""

    _FALTA = object()

    def __init__(self, raiz: pathlib.Path):
        self.raiz = raiz
        self.lab = modulo_lab()
        self.viejos: dict = {}

    def __enter__(self) -> "LabAislado":
        nuevos = {"ROOT": self.raiz, "ENCARGOS": self.raiz / "encargos", "LOCK": self.raiz / ".ventana.lock",
                  "EVIDENCIA": self.raiz / "evidence", "COBERTURA": self.raiz / "coverage.json",
                  "ASSETS_DIR": self.raiz, "TURNOS": self.raiz / "turnos.json",
                  "TURNO_HECHO": self.raiz / ".turno-hecho", "RUNS_DIR": self.raiz / "runs"}
        for nombre, valor in nuevos.items():
            self.viejos[nombre] = getattr(self.lab, nombre, self._FALTA)
            setattr(self.lab, nombre, valor)
        return self

    def __exit__(self, *exc) -> None:
        for nombre, valor in self.viejos.items():
            if valor is self._FALTA:
                delattr(self.lab, nombre)
            else:
                setattr(self.lab, nombre, valor)

    def __call__(self, *args):
        import contextlib
        import io
        import json
        out, err = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ["lab.py", *map(str, args)]
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    codigo = self.lab.main()
                except SystemExit as e:
                    codigo = e.code if isinstance(e.code, int) else 1
                except (Exception, IntentoDeES) as e:
                    codigo = None
                    err.write(f"escapó {e!r}")
        finally:
            sys.argv = argv
        try:
            datos = json.loads(out.getvalue())
        except ValueError:
            datos = None
        return codigo, datos, err.getvalue()


CELDAS_PRUEBA = [
    {"cell_id": "C-IG-TEL", "platform": "instagram", "native_format": "feed_single_image",
     "publishing_route": "android_native", "status": "planned"},
    {"cell_id": "C-FB-API", "platform": "facebook", "native_format": "feed_single_image",
     "publishing_route": "api", "status": "planned"},
    {"cell_id": "C-TH-API", "platform": "threads", "native_format": "feed_single_image",
     "publishing_route": "api", "status": "ready"},
    {"cell_id": "C-STORY", "platform": "instagram", "native_format": "story_image",
     "publishing_route": "api", "status": "planned"},
    {"cell_id": "C-PUB", "platform": "threads", "native_format": "feed_single_image",
     "publishing_route": "api", "status": "published"},
    {"cell_id": "C-CARR", "platform": "instagram", "native_format": "feed_carousel",
     "publishing_route": "api", "status": "planned"},
]


def campo(datos, clave):
    return datos.get(clave) if isinstance(datos, dict) else None


def seccion_cli_en_proceso() -> None:
    print("\n10. CLI lab.py en proceso: validaciones antes de tocar nada")
    import contextlib
    import hashlib
    import json
    import tempfile
    from datetime import datetime, timezone
    from PIL import Image
    from labkit import codex_rescate, encargos as E, instagram_feed, telefono

    t = datetime.now(timezone.utc)
    familia = "LAB-CLI-001"

    @contextlib.contextmanager
    def entorno():
        with tempfile.TemporaryDirectory() as d:
            raiz = pathlib.Path(d)
            (raiz / "encargos").mkdir()
            (raiz / "coverage.json").write_text(json.dumps({"cells": CELDAS_PRUEBA}), encoding="utf-8")
            (raiz / "prompt.txt").write_text("Un astrolabio de latón", encoding="utf-8")
            with LabAislado(raiz) as lab:
                yield lab, raiz

    def guardar_encargo(raiz, n, celdas):
        eid = f"ENC-{t:%Y%m%d}-{n:03d}"
        enc = E.nuevo(eid, coverage_cell_ids=celdas, family_id=familia, brief_path="b.md", do_not_use=[],
                      formato={"ancho": 1080, "alto": 1350}, prompt="Un astrolabio", restricciones=["sin texto"],
                      destino_assets=f"experiments/media-lab/assets/{familia}", ahora=t)
        E.guardar(raiz / "encargos" / f"{eid}.json", enc)
        return eid, enc

    def png(raiz, rel, ancho, alto):
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (ancho, alto), (120, 90, 60)).save(p, "PNG")
        return {"ruta": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "ancho": ancho, "alto": alto}

    def generado(raiz, n, celdas, ancho=768, alto=1152):
        eid, enc = guardar_encargo(raiz, n, celdas)
        imagen = png(raiz, f"experiments/media-lab/assets/{familia}/{eid}-v1.png", ancho, alto)
        E.tomar(enc, "codex-heartbeat", t)
        E.marcar_generado(enc, "codex-heartbeat", [imagen], t)
        E.guardar(raiz / "encargos" / f"{eid}.json", enc)
        return eid

    def aprobar(raiz, n, celdas):
        eid = generado(raiz, n, celdas)
        ruta = raiz / "encargos" / f"{eid}.json"
        E.guardar(ruta, E.revisar(E.cargar(ruta), aprobado=True, motivo="prueba", ahora=t))
        return eid

    def nuevo(lab, *celdas, formato='{"ancho":1080,"alto":1350}'):
        args = ["encargo-nuevo", "--family", familia, "--brief", "b.md", "--formato", formato,
                "--prompt-file", lab.raiz / "prompt.txt"]
        for c in celdas:
            args += ["--cell", c]
        return lab(*args)

    def error(datos) -> str:
        return str(campo(datos, "error") or "")

    llamadas: list[str] = []

    def prohibido(nombre):
        def f(*args, **kwargs):
            llamadas.append(nombre)
            raise IntentoDeES(nombre)
        return f

    parches = [(telefono, n) for n in ("adb", "shell", "volcado", "captura", "estado", "subir", "tocar",
                                       "tecla", "lanzar")]
    parches += [(instagram_feed, n) for n in ("abrir_nueva_publicacion", "alternar_recorte", "siguiente",
                                              "anadir_audio_sugerido", "detalles", "escribir_pie", "atras",
                                              "compartir")]
    originales = [(obj, n, getattr(obj, n)) for obj, n in parches]
    try:
        for obj, n in parches:
            setattr(obj, n, prohibido(n))

        print("   · encargo-nuevo y cola")
        with entorno() as (lab, raiz):
            for n in range(1, 11):
                guardar_encargo(raiz, n, [f"X{n}"])
            codigo, datos, _ = nuevo(lab, "C-FB-API")
            check(codigo == 2 and "cola" in error(datos), f"con 10 en cola el 11.º encargo sale con 2 ({codigo}, {datos})")
            check(len(list((raiz / "encargos").glob("ENC-*.json"))) == 10, "el encargo rechazado por la cola no se guarda")

        with entorno() as (lab, raiz):
            for celdas, label in ((["C-NADA"], "celda que no existe"), (["C-PUB"], "celda ya publicada"),
                                  (["C-CARR"], "ruta sin implementar"),
                                  (["C-FB-API", "C-STORY"], "feed y story mezclados"),
                                  (["C-FB-API", "C-FB-API"], "celda repetida")):
                codigo, datos, _ = nuevo(lab, *celdas)
                check(codigo == 2 and campo(datos, "ok") is False, f"encargo-nuevo rechaza: {label} ({codigo}, {error(datos)})")
            codigo, datos, _ = nuevo(lab, "C-TH-API", formato="{}")
            check(codigo == 2 and campo(datos, "tipo") == "EncargoError",
                  f"encargo-nuevo rechaza un formato sin ancho ni alto ({codigo}, {datos})")
            check(not list((raiz / "encargos").glob("ENC-*.json")), "ningún rechazo deja un encargo")
            codigo, datos, _ = nuevo(lab, "C-TH-API", "C-FB-API")
            eid = str(campo(datos, "encargo_id"))
            check(codigo == 0 and campo(datos, "coverage_cell_ids") == ["C-TH-API", "C-FB-API"],
                  f"dos celdas de feed implementadas y libres: encargo creado ({codigo}, {datos})")
            codigo, datos, _ = nuevo(lab, "C-FB-API")
            check(codigo == 2 and eid in error(datos),
                  f"una celda con un encargo en curso no admite otro ({codigo}, {error(datos)})")

            print("   · codex-fallo, encargo-usado y encargos")
            for _ in range(2):
                lab("codex-tomar", "--owner", "codex-heartbeat", "--max", "1")
                codigo, datos, _ = lab("codex-fallo", "--encargo", eid, "--owner", "codex-heartbeat", "--nota", "sin imagen")
            check(codigo == 0 and campo(datos, "estado") == "bloqueado", f"dos codex-fallo dejan el encargo bloqueado ({datos})")
            ruta = raiz / "encargos" / f"{eid}.json"
            antes = ruta.read_bytes() if ruta.exists() else b""
            codigo, datos, _ = lab("encargo-usado", "--encargo", eid, "--run", "LAB-RUN-1")
            check(codigo == 2 and campo(datos, "ok") is False and ruta.exists() and ruta.read_bytes() == antes,
                  f"encargo-usado rechaza un encargo que no está aprobado ({codigo})")
            codigo, datos, _ = lab("encargo-usado", "--encargo", "../ENC-x", "--run", "LAB-RUN-1")
            check(codigo == 2 and campo(datos, "ok") is False, f"un --encargo con forma rara sale con 2 ({codigo})")
            (raiz / "encargos" / "ENC-20990101-001.json").write_text("{", encoding="utf-8")
            codigo, datos, _ = lab("encargos")
            filas = datos if isinstance(datos, list) else []
            check(codigo == 0 and any(f.get("archivo") == "ENC-20990101-001.json" and f.get("error") for f in filas)
                  and any(f.get("encargo_id") == eid for f in filas),
                  f"encargos lista aparte los archivos ilegibles sin fallar ({codigo})")

        print("   · cerrojo")
        with entorno() as (lab, raiz):
            codigos = [lab(*args)[0] for args in (("lock-tomar", "--dueno", "programada"),
                                                  ("lock-soltar", "--dueno", "manual"),
                                                  ("lock-tomar", "--dueno", "manual"),
                                                  ("lock-soltar", "--dueno", "programada"),
                                                  ("lock-soltar", "--dueno", "programada"),
                                                  ("lock-tomar", "--dueno", "claude"))]
            check(codigos == [0, 3, 3, 0, 3, 2],
                  f"manual no suelta ni pisa el de programada; soltar sin cerrojo da 3; dueño desconocido 2 ({codigos})")
            codigo, datos, _ = lab("lock-tomar", "--dueno", "claude")
            check(codigo == 2 and campo(datos, "ok") is False and campo(datos, "tipo") == "ArgumentoNoValido"
                  and "--dueno" in error(datos),
                  f"un error de argparse (--dueno desconocido) sale con 2 y JSON en stdout ({codigo}, {datos})")
            codigo, datos, _ = lab()
            check(codigo == 2 and campo(datos, "tipo") == "ArgumentoNoValido",
                  f"sin subcomando también sale con 2 y JSON ({codigo}, {datos})")

        print("   · seleccionar")
        with entorno() as (lab, raiz):
            for n, celda in enumerate(("C-IG-TEL", "C-FB-API", "C-TH-API"), start=1):
                aprobar(raiz, n, [celda])
            ids = lambda d: [c["cell_id"] for c in d] if isinstance(d, list) else d  # noqa: E731
            _, datos, _ = lab("seleccionar", "--max", "2")
            check(ids(datos) == ["C-IG-TEL", "C-TH-API"], f"seleccionar con la cobertura temporal ({ids(datos)})")
            _, datos, _ = lab("seleccionar", "--max", "2", "--sin-telefono")
            check(ids(datos) == ["C-FB-API", "C-TH-API"], f"seleccionar --sin-telefono descarta el teléfono ({ids(datos)})")

        print("   · manifiestos")
        with entorno() as (lab, raiz):
            asset = f"experiments/media-lab/assets/{familia}/master.jpg"
            (raiz / asset).parent.mkdir(parents=True, exist_ok=True)
            (raiz / asset).write_bytes(b"jpg")
            (raiz / "fuera.jpg").write_bytes(b"fuera")
            enlace = f"experiments/media-lab/assets/{familia}/enlace.jpg"
            (raiz / enlace).symlink_to(raiz / "fuera.jpg")
            pie = raiz / "pie.txt"
            pie.write_text("Pie de prueba\n", encoding="utf-8")
            api = ("manifiesto-api", "--run-group", "LAB-CLI-001-API", "--caption", f"facebook={pie}")
            manifiestos = raiz / "experiments" / "media-lab" / "manifests"
            for ruta_asset, label in ((str(raiz / asset), "ruta absoluta"),
                                      (f"experiments/media-lab/assets/{familia}/no.jpg", "archivo que no existe"),
                                      (f"experiments/media-lab/assets/{familia}/../../../../fuera.jpg", "ruta con .."),
                                      (enlace, "enlace simbólico")):
                codigo, datos, _ = lab(*api, "--asset", ruta_asset)
                check(codigo == 2 and campo(datos, "ok") is False, f"manifiesto-api rechaza: {label} ({codigo})")
            check(not list(manifiestos.glob("*.json")), "ningún rechazo escribe un manifiesto")
            codigo, datos, _ = lab(*api, "--asset", asset)
            escrito = manifiestos / "LAB-CLI-001-API.json"
            m = json.loads(escrito.read_text(encoding="utf-8")) if escrito.exists() else {}
            check(codigo == 0 and m.get("asset_sha256") == hashlib.sha256(b"jpg").hexdigest()
                  and m.get("captions") == {"facebook": "Pie de prueba"}, f"manifiesto-api escribe el manifiesto ({codigo})")
            codigo, datos, _ = lab(*api, "--asset", asset)
            check(codigo == 2 and escrito.exists() and json.loads(escrito.read_text(encoding="utf-8")) == m,
                  f"manifiesto-api no pisa un manifiesto existente ({codigo})")
            codigo, datos, _ = lab("manifiesto-api", "--run-group", "LAB-CLI-002-API", "--caption", "facebook",
                                   "--asset", asset)
            check(codigo == 2 and campo(datos, "tipo") == "ManifiestoError", f"un --caption sin = da ManifiestoError ({datos})")
            codigo, datos, _ = lab("manifiesto-verificacion", "--run-group", "LAB-CLI-001-API", "--post", "facebook")
            check(codigo == 2 and campo(datos, "tipo") == "ManifiestoError", f"un --post sin = da ManifiestoError ({datos})")
            verificar = ("manifiesto-verificacion", "--run-group", "LAB-CLI-001-API", "--post", "facebook=123_456")
            codigo_1, codigo_2 = lab(*verificar)[0], lab(*verificar)[0]
            check((codigo_1, codigo_2) == (0, 2), f"manifiesto-verificacion escribe una vez y no pisa ({codigo_1}, {codigo_2})")

            codigo, datos, _ = lab("manifiesto-verificacion", "--run-group", "LAB-CLI-002-API",
                                   "--instagram-shortcode", "DdR54JEgxHN", "--post", "facebook=1",
                                   "--superficie", "facebook=story")
            escrito = manifiestos / "LAB-CLI-002-API-verify.json"
            m = json.loads(escrito.read_text(encoding="utf-8")) if escrito.exists() else {}
            check(codigo == 0 and m.get("instagram_shortcodes") == {"instagram": "DdR54JEgxHN"}
                  and m.get("surfaces") == {"facebook": "story"} and m.get("post_ids") == {"facebook": "1"},
                  f"manifiesto-verificacion admite --instagram-shortcode y --superficie a la vez ({codigo}, {m})")
            codigo, datos, _ = lab("manifiesto-verificacion", "--run-group", "LAB-CLI-002B-API",
                                   "--instagram-shortcode", "DdR54JEgxHN", "--superficie", "instagram=story")
            check(codigo == 2 and campo(datos, "tipo") == "ManifiestoError",
                  f"--instagram-shortcode junto con --superficie instagram=story se rechaza: no se busca así ({datos})")
            codigo, datos, _ = lab("manifiesto-verificacion", "--run-group", "LAB-CLI-003-API",
                                   "--instagram-shortcode", "abc")
            check(codigo == 2 and campo(datos, "tipo") == "ManifiestoError",
                  f"un shortcode con formato inválido da ManifiestoError ({datos})")

        print("   · teléfono: argumentos antes de cualquier adb")
        with entorno() as (lab, raiz):
            pie = raiz / "pie.txt"
            pie.write_text("Pie\n", encoding="utf-8")
            png(raiz, "fuera.png", 10, 10)
            enlace = f"experiments/media-lab/assets/{familia}/enlace.png"
            (raiz / enlace).parent.mkdir(parents=True, exist_ok=True)
            (raiz / enlace).symlink_to(raiz / "fuera.png")
            casos = (
                (("ig", "compartir", "--run", "RUN-1", "--pie", pie, "--publicaciones-antes", "3"), "compartir sin --tema"),
                (("ig", "compartir", "--run", "RUN-1", "--pie", pie, "--tema", "T"), "compartir sin --publicaciones-antes"),
                (("ig", "compartir", "--run", "RUN-1", "--tema", "T", "--publicaciones-antes", "3"), "compartir sin --pie"),
                (("ig", "pie", "--run", "RUN-1"), "pie sin --pie"),
                (("ig", "abrir", "--run", "RUN-1"), "abrir sin --subido-en"),
                (("ig", "abrir", "--run", "RUN-1", "--subido-en", "ayer"), "abrir con --subido-en ilegible"),
                (("ig", "abrir", "--run", "RUN-1", "--subido-en", "2026-09-14T10:00:00"), "abrir con --subido-en sin zona"),
                (("ig", "recorte", "--run", "RUN-1", "--produccion-cercana"), "--produccion-cercana fuera de compartir"),
                (("ig", "recorte", "--run", "../x"), "--run con .."),
                (("telefono-captura", "--run", "RUN-1", "--nombre", "../x"), "--nombre con .."),
                (("telefono-atras", "--run", "/tmp/x", "--nombre", "a"), "--run absoluto"),
                (("telefono-subir", "--local", "/etc/hosts"), "subir un archivo de fuera"),
                (("telefono-subir", "--local", "experiments/media-lab/assets/../../../x.png"), "subir con .."),
                (("telefono-subir", "--local", "experiments/media-lab/lab.py"), "subir algo que no es imagen"),
                (("telefono-subir", "--local", enlace), "subir un enlace simbólico"),
            )
            for args, label in casos:
                llamadas.clear()
                codigo, datos, _ = lab(*args)
                check(codigo == 2 and campo(datos, "ok") is False and not llamadas,
                      f"{label}: sale con 2 sin tocar el teléfono ({codigo}, {llamadas})")
            codigo, datos, _ = lab("ig", "abrir", "--run", "RUN-1", "--subido-en", "ayer")
            check(codigo == 2 and campo(datos, "tipo") == "ArgumentoNoValido" and "--subido-en" in error(datos),
                  f"(M-4) un --subido-en ilegible da un error que lo nombra ({codigo}, {datos})")

            recibido: dict = {}

            def compartir_falso(pie_, tema_, ev_, antes_, produccion_cercana=False):
                recibido.update(produccion_cercana=produccion_cercana, antes=antes_)
                return {"estado": "confirmado_sin_conteo" if produccion_cercana else "confirmado"}

            instagram_feed.compartir = compartir_falso
            base_compartir = ("ig", "compartir", "--run", "RUN-1", "--pie", pie, "--tema", "T",
                              "--publicaciones-antes", "3")
            codigo, datos, _ = lab(*base_compartir, "--produccion-cercana")
            check(codigo == 5 and recibido.get("produccion_cercana") is True and recibido.get("antes") == 3
                  and campo(datos, "estado") == "confirmado_sin_conteo",
                  f"(M-1) ig compartir --produccion-cercana lo pasa a compartir y sale con 5 ({codigo}, {recibido})")
            recibido.clear()
            codigo, datos, _ = lab(*base_compartir)
            check(codigo == 0 and recibido.get("produccion_cercana") is False,
                  f"(M-1) sin --produccion-cercana compartir recibe False ({codigo}, {recibido})")

            def pantalla(*args, **kwargs):
                raise instagram_feed.PantallaInesperada("no aparece «Modifier le rognage»")

            def sin_adb(*args, **kwargs):
                raise telefono.TelefonoError("device offline")

            instagram_feed.alternar_recorte = pantalla
            telefono.captura = lambda destino: destino
            codigo, datos, _ = lab("ig", "recorte", "--run", "RUN-1")
            check(codigo == 4 and campo(datos, "tipo") == "PantallaInesperada"
                  and str(campo(datos, "captura")).endswith("RUN-1/ig-inesperada-recorte.png"),
                  f"una pantalla inesperada sale con 4, su captura y JSON ({codigo}, {datos})")
            telefono.subir = sin_adb
            png(raiz, f"experiments/media-lab/assets/{familia}/master.png", 10, 10)
            codigo, datos, _ = lab("telefono-subir", "--local", f"experiments/media-lab/assets/{familia}/master.png")
            check(codigo == 4 and campo(datos, "tipo") == "TelefonoError", f"telefono-subir sin adb sale con 4 ({codigo}, {datos})")
            telefono.captura = sin_adb
            codigo, datos, _ = lab("telefono-captura", "--run", "RUN-1", "--nombre", "perfil")
            check(codigo == 4 and campo(datos, "captura") is None, f"telefono-captura sin adb sale con 4 ({codigo}, {datos})")
            instagram_feed.alternar_recorte = lambda ev: ev / "ig-02-recorte.png"
            codigo, datos, _ = lab("ig", "recorte", "--run", "RUN-1")
            check(codigo == 0 and campo(datos, "ok") is True and str(campo(datos, "captura")).endswith("RUN-1/ig-02-recorte.png"),
                  f"un paso correcto sale con 0 y su captura ({codigo}, {datos})")

            def disco(*args, **kwargs):
                raise OSError(28, "No space left on device")

            instagram_feed.detalles = disco
            telefono.captura = lambda destino: destino
            codigo, datos, _ = lab("ig", "detalles", "--run", "RUN-1")
            check(codigo == 4 and campo(datos, "tipo") == "OSError"
                  and str(campo(datos, "captura")).endswith("RUN-1/ig-inesperada-detalles.png"),
                  f"un OSError dentro del paso sale con 4, captura y JSON ({codigo}, {datos})")
            telefono.captura = disco
            codigo, datos, _ = lab("ig", "detalles", "--run", "RUN-1")
            check(codigo == 4 and campo(datos, "tipo") == "OSError" and campo(datos, "captura") is None,
                  f"si la captura del fallo también da OSError sigue saliendo con 4 ({codigo}, {datos})")

        print("   · codex-generado y encargo-revisar")
        with entorno() as (lab, raiz):
            eid, _ = guardar_encargo(raiz, 1, ["C-FB-API"])
            lab("codex-tomar", "--owner", "codex-heartbeat")
            ruta = raiz / "encargos" / f"{eid}.json"
            pedida = f"experiments/media-lab/assets/{familia}/{eid}-v1.png"
            destino = raiz / pedida
            png(raiz, "fuera/valida.png", 768, 1152)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.symlink_to(raiz / "fuera" / "valida.png")
            png(raiz, f"experiments/media-lab/assets/{familia}/{eid}-v2.png", 768, 1152)
            png(raiz, f"experiments/media-lab/assets/{familia}/otra.png", 768, 1152)

            def generado_cli(*imagenes, owner="codex-heartbeat"):
                args = ["codex-generado", "--encargo", eid, "--owner", owner]
                for im in imagenes:
                    args += ["--imagen", im]
                antes = ruta.read_bytes()
                codigo, datos, _ = lab(*args)
                return codigo, datos, ruta.read_bytes() == antes

            codigo, datos, igual = generado_cli(pedida)
            check(codigo == 2 and igual, f"codex-generado rechaza un enlace simbólico a un PNG válido sin guardar ({codigo})")
            destino.unlink()
            destino.write_text("no soy una imagen", encoding="utf-8")
            codigo, datos, igual = generado_cli(pedida)
            check(codigo == 2 and igual and campo(datos, "ok") is False,
                  f"codex-generado rechaza un archivo de texto sin guardar ({codigo})")
            destino.unlink()
            png(raiz, pedida, 768, 1152)
            for otra, label in ((f"experiments/media-lab/assets/{familia}/{eid}-v2.png", "una variante hermana no pedida"),
                                (f"experiments/media-lab/assets/{familia}/otra.png", "otra imagen de la misma carpeta")):
                codigo, datos, igual = generado_cli(otra)
                check(codigo == 2 and igual, f"codex-generado rechaza {label} ({codigo})")
            codigo, datos, igual = generado_cli(pedida, owner="codex-exec")
            check(codigo == 2 and igual, f"codex-generado rechaza a quien no tiene el bloqueo ({codigo})")
            destino.unlink()
            png(raiz, pedida, 64, 80)
            codigo, datos, igual = generado_cli(pedida)
            check(codigo == 2 and igual and "pequeña" in error(datos),
                  f"codex-generado valida la copia y rechaza una imagen diminuta ({codigo}, {error(datos)})")
            destino.unlink()
            png(raiz, pedida, 768, 1152)
            codigo, datos, igual = generado_cli(pedida)
            check(codigo == 0 and not igual and E.cargar(ruta)["estado"] == "generado",
                  f"codex-generado guarda una imagen pedida e íntegra ({codigo}, {datos})")

            diminuta = generado(raiz, 2, ["C-TH-API"], ancho=64, alto=80)
            codigo, datos, _ = lab("encargo-revisar", "--encargo", diminuta, "--aprobado", "--motivo", "prueba")
            check(codigo == 2 and E.cargar(raiz / "encargos" / f"{diminuta}.json")["estado"] == "generado",
                  f"encargo-revisar --aprobado no aprueba una imagen que no valida ({codigo})")
            codigo, datos, _ = lab("encargo-revisar", "--encargo", eid, "--aprobado", "--motivo", "prueba")
            check(codigo == 0 and E.cargar(ruta)["estado"] == "aprobado", f"encargo-revisar aprueba una imagen íntegra ({codigo})")

            codex_original = codex_rescate.CODEX
            codex_rescate.CODEX = str(raiz / "codex-que-no-existe")
            try:
                codigo, datos, _ = lab("generar", "--encargo", eid)
            finally:
                codex_rescate.CODEX = codex_original
            check(codigo == 2 and campo(datos, "tipo") == "EncargoError",
                  f"generar sobre un encargo aprobado sale con 2 antes de buscar Codex ({codigo}, {datos})")

            pendiente, _ = guardar_encargo(raiz, 3, ["C-TH-API"])
            ruta_pendiente = raiz / "encargos" / f"{pendiente}.json"
            antes = ruta_pendiente.read_bytes()
            check(lab.lab._deshacer(ruta_pendiente, "interrumpido por señal 15", True) == []
                  and ruta_pendiente.read_bytes() == antes,
                  "_deshacer no toca un encargo que sigue en pedido (señal antes de tomarlo)")

            print("   · generar: señal o error antes de lanzar Codex (G-1, G-2)")
            import signal
            import tempfile as tf
            modulo = lab.lab
            viejos = {"CODEX": codex_rescate.CODEX, "comando": codex_rescate.comando,
                      "estado_git": modulo.guardia.estado_git, "_permitidas": modulo._permitidas,
                      "mkdtemp": tf.mkdtemp, "_liberar": modulo._liberar, "_cola": modulo._cola}
            permitidas_original = modulo._permitidas
            try:
                # `python --version` hace de «codex --version»; el Codex de verdad nunca se lanza.
                codex_rescate.CODEX = sys.executable
                codex_rescate.comando = prohibido("codex_rescate.comando")
                modulo.guardia.estado_git = lambda raiz: {}

                def senal_antes_de_lanzar(enc, ruta):
                    signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)  # el manejador de generar, sin señal real
                    return permitidas_original(enc, ruta)

                llamadas.clear()
                modulo._permitidas = senal_antes_de_lanzar
                senalado, _ = guardar_encargo(raiz, 4, ["C-TH-API"])
                codigo, datos, _ = lab("generar", "--encargo", senalado)
                enc_senal = E.cargar(raiz / "encargos" / f"{senalado}.json")
                errores_senal = campo(datos, "errores") or [""]
                check(codigo == 1 and enc_senal["estado"] == "pedido" and enc_senal["intentos"] == []
                      and enc_senal["lock_owner"] is None and not llamadas
                      and errores_senal[0].startswith(f"interrumpido por señal {int(signal.SIGTERM)}"),
                      f"(G-1) señal antes de lanzar Codex: vuelve a pedido sin sumar intento ({codigo}, {datos}, "
                      f"{enc_senal['estado']}, {len(enc_senal['intentos'])} intentos, {llamadas})")
                check(enc_senal.get("no_lanzados") == 1,
                      f"(M-7-iii) una señal antes de lanzar también cuenta como no-lanzamiento ({enc_senal.get('no_lanzados')})")

                modulo._permitidas = permitidas_original

                def sin_disco(*args, **kwargs):
                    raise OSError(28, "No space left on device")

                tf.mkdtemp = sin_disco
                roto, _ = guardar_encargo(raiz, 5, ["C-TH-API"])
                codigo, datos, _ = lab("generar", "--encargo", roto)
                tf.mkdtemp = viejos["mkdtemp"]
                enc_roto = E.cargar(raiz / "encargos" / f"{roto}.json")
                check(codigo == 2 and campo(datos, "tipo") == "OSError" and enc_roto["estado"] == "pedido"
                      and enc_roto["intentos"] == [] and enc_roto["lock_owner"] is None and not llamadas,
                      f"(G-2) un error entre tomar y lanzar Codex no deja el encargo en generando ({codigo}, {datos}, "
                      f"{enc_roto['estado']})")
                check(enc_roto.get("no_lanzados") == 1,
                      f"(M-7-iii) un error antes de lanzar también cuenta como no-lanzamiento ({enc_roto.get('no_lanzados')})")

                print("   · generar sin lanzar Codex no gasta intentos; tras lanzarlo, guardia antes de relanzar (10d)")
                ajena = "experiments/media-lab/results/ajeno-de-prueba.txt"

                def git_que_cambia():
                    fotos = iter([{}])
                    return lambda raiz: next(fotos, {ajena: "1"})

                llamadas.clear()
                modulo._permitidas = senal_antes_de_lanzar
                modulo.guardia.estado_git = git_que_cambia()
                con_ajenos, _ = guardar_encargo(raiz, 6, ["C-TH-API"])
                codigo, datos, _ = lab("generar", "--encargo", con_ajenos)
                modulo._permitidas = permitidas_original
                enc_ajenos = E.cargar(raiz / "encargos" / f"{con_ajenos}.json")
                errores_ajenos = campo(datos, "errores") or [""]
                check(codigo == 6 and campo(datos, "ajenos") == [ajena] and enc_ajenos["estado"] == "pedido"
                      and enc_ajenos["intentos"] == [] and enc_ajenos["lock_owner"] is None and not llamadas
                      and "antes de lanzar Codex" in errores_ajenos[0] and ajena in errores_ajenos[0],
                      f"(10d) señal antes de lanzar con ajenos: se informan, sale con 6 y el encargo vuelve a pedido sin "
                      f"intento ni bloqueo ({codigo}, {datos}, {enc_ajenos['estado']}, {len(enc_ajenos['intentos'])})")

                modulo.guardia.estado_git = lambda raiz: {}
                codex_rescate.comando = lambda prompt, salida: [str(raiz / "codex-que-no-existe")]
                sin_popen, _ = guardar_encargo(raiz, 7, ["C-TH-API"])
                codigo, datos, _ = lab("generar", "--encargo", sin_popen)
                enc_popen = E.cargar(raiz / "encargos" / f"{sin_popen}.json")
                check(codigo == 1 and enc_popen["estado"] == "pedido" and enc_popen["intentos"] == []
                      and enc_popen["lock_owner"] is None and enc_popen.get("no_lanzados") == 1
                      and "no arrancó" in str((campo(datos, "errores") or [""])[0]),
                      f"(10d) si Popen falla, Codex no se lanzó: pedido sin sumar intento ({codigo}, {datos}, "
                      f"{enc_popen['estado']}, {len(enc_popen['intentos'])})")

                for _ in range(2):
                    codigo, datos, _ = lab("generar", "--encargo", sin_popen)
                enc_popen = E.cargar(raiz / "encargos" / f"{sin_popen}.json")
                check(codigo == 1 and enc_popen["estado"] == "bloqueado" and enc_popen["intentos"] == []
                      and enc_popen["lock_owner"] is None and enc_popen.get("no_lanzados") == 3
                      and enc_popen.get("nota_no_lanzado"),
                      f"(10e) Popen falla 3 veces seguidas: el encargo queda bloqueado sin sumar intentos "
                      f"({codigo}, {datos}, {enc_popen['estado']}, {enc_popen.get('no_lanzados')})")

                # Tras lanzar un proceso inofensivo (python -c pass, nunca Codex), falla la lectura de su salida.
                codex_rescate.comando = lambda prompt, salida: [sys.executable, "-c", "pass"]

                def cola_rota(archivo):
                    raise OSError(5, "cola ilegible")

                modulo._cola = cola_rota
                modulo.guardia.estado_git = git_que_cambia()
                tras_lanzar, _ = guardar_encargo(raiz, 8, ["C-TH-API"])
                codigo, datos, salida_err = lab("generar", "--encargo", tras_lanzar)
                modulo._cola = viejos["_cola"]
                enc_tras = E.cargar(raiz / "encargos" / f"{tras_lanzar}.json")
                ultimo = (enc_tras["intentos"] or [{}])[-1]
                check(codigo == 2 and campo(datos, "tipo") == "OSError" and enc_tras["estado"] == "bloqueado"
                      and len(enc_tras["intentos"]) == 1 and ultimo.get("resultado") == "fallo"
                      and "error tras lanzar Codex" in str(ultimo.get("nota")) and ajena in str(ultimo.get("nota"))
                      and ajena in salida_err,
                      f"(10d) una excepción tras lanzar Codex con cambios ajenos pasa la guardia y deja el encargo "
                      f"bloqueado con la nota antes de relanzar "
                      f"({codigo}, {datos}, {enc_tras['estado']}, {ultimo}, {salida_err!r})")

                codex_rescate.comando = prohibido("codex_rescate.comando")
                modulo.guardia.estado_git = lambda raiz: {}
                modulo._liberar = lambda ruta: ["no se pudo liberar el encargo: prueba de stderr"]
                tf.mkdtemp = sin_disco
                sin_liberar, _ = guardar_encargo(raiz, 9, ["C-TH-API"])
                codigo, datos, salida_err = lab("generar", "--encargo", sin_liberar)
                tf.mkdtemp = viejos["mkdtemp"]
                modulo._liberar = viejos["_liberar"]
                check(codigo == 2 and "no se pudo liberar el encargo: prueba de stderr" in salida_err,
                      f"(10d) los errores de _liberar antes de relanzar salen por stderr ({codigo}, {salida_err!r})")
            finally:
                codex_rescate.CODEX = viejos["CODEX"]
                codex_rescate.comando = viejos["comando"]
                modulo.guardia.estado_git = viejos["estado_git"]
                modulo._permitidas = viejos["_permitidas"]
                tf.mkdtemp = viejos["mkdtemp"]
                modulo._liberar = viejos["_liberar"]
                modulo._cola = viejos["_cola"]
    finally:
        for obj, n, f in originales:
            setattr(obj, n, f)


CODEX_FALSO = r'''#!__PYTHON__
"""Codex falso para las pruebas de lab.py generar: nunca habla con nadie."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

args = sys.argv[1:]
if args == ["--version"]:
    print("codex-falso 0.0")
    sys.exit(0)
modo = os.environ["CODEX_FALSO_MODO"]
marcas = Path(os.environ["CODEX_FALSO_MARCAS"])
prompt = args[-1]
salida = Path(args[args.index("-o") + 1])
eid = re.search(r"--encargo (ENC-\d{8}-\d{3,})", prompt).group(1)
rutas = re.findall(r"--imagen (\S+)", prompt)
if modo in ("ajeno", "ajeno-colgado", "ajeno-sin-generar"):
    Path(os.environ["CODEX_FALSO_AJENO"]).write_text("Codex no debería escribir aquí", encoding="utf-8")
if modo == "ajeno-sin-generar":
    sys.exit(1)  # falla sin llamar a codex-generado: el encargo sigue en generando
if modo in ("colgado", "ajeno-colgado"):
    nieto = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    (marcas / "nieto.pid").write_text(str(nieto.pid))
    (marcas / "arrancado").write_text("1")
    time.sleep(120)
    sys.exit(0)
# un hijo en segundo plano que sobrevive a Codex: podría escribir tras la segunda foto
fondo = subprocess.Popen(["sleep", "30"])
(marcas / f"fondo-{eid}.pid").write_text(str(fondo.pid))
from PIL import Image
for ruta in rutas:
    p = Path(ruta)
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (768, 1152), (120, 90, 60)).save(p, "PNG")
imagenes = [x for ruta in rutas for x in ("--imagen", ruta)]
r = subprocess.run([sys.executable, "experiments/media-lab/lab.py", "codex-generado", "--encargo", eid,
                    "--owner", "codex-exec", *imagenes])
if modo == "tmp":
    # lo que dejaría un corte a mitad de encargos.guardar (después de codex-generado, que usa ese nombre)
    (Path(os.environ["LAB_ENCARGOS_DIR"]) / f".{eid}.json.tmp").write_text("{", encoding="utf-8")
salida.write_text(json.dumps({"estado": "generado", "encargo_id": eid}), encoding="utf-8")
sys.exit(r.returncode)
'''


def seccion_generar() -> None:
    print("\n11. generar de extremo a extremo con un Codex falso")
    import json
    import os
    import shutil
    import signal
    import subprocess
    import tempfile
    import time
    import uuid
    from datetime import datetime, timezone
    from labkit import encargos as E

    lab = ROOT / "experiments" / "media-lab" / "lab.py"
    familia = f"LAB-TEST-GEN-{uuid.uuid4().hex[:8].upper()}"
    carpeta_assets = ROOT / "experiments" / "media-lab" / "assets" / familia
    resultados = ROOT / "experiments" / "media-lab" / "results"
    unico = uuid.uuid4().hex
    ajeno = resultados / f"codex-falso-{unico}-b.txt"
    ajeno_senal = resultados / f"codex-falso-{unico}-e.txt"
    ajeno_sin_generar = resultados / f"codex-falso-{unico}-g.txt"
    encargos_en_repo = resultados / f"encargos-prueba-{unico}"
    temporal = pathlib.Path(tempfile.gettempdir())
    salidas_antes = set(temporal.glob("codex-exec-*"))
    t = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        encs = base / "encargos"
        marcas = base / "marcas"
        encs.mkdir()
        marcas.mkdir()
        falso = base / "codex-falso"
        falso.write_text(CODEX_FALSO.replace("__PYTHON__", sys.executable), encoding="utf-8")
        falso.chmod(0o755)

        def encargo(n: int, carpeta: pathlib.Path = encs) -> str:
            eid = f"ENC-{t:%Y%m%d}-{n:03d}"
            E.guardar(carpeta / f"{eid}.json", E.nuevo(
                eid, coverage_cell_ids=["C1"], family_id=familia, brief_path="b.md", do_not_use=[],
                formato={"ancho": 1080, "alto": 1350}, prompt="Un astrolabio", restricciones=["sin texto"],
                destino_assets=f"experiments/media-lab/assets/{familia}", ahora=t))
            return eid

        def generar(eid: str, modo: str, *extra: str, senal: bool = False, carpeta: pathlib.Path = encs,
                    fuera: pathlib.Path = ajeno):
            env = {**os.environ, "MEDIA_LAB_CODEX": str(falso), "LAB_ENCARGOS_DIR": str(carpeta),
                   "CODEX_FALSO_MODO": modo, "CODEX_FALSO_MARCAS": str(marcas), "CODEX_FALSO_AJENO": str(fuera)}
            proc = subprocess.Popen([sys.executable, str(lab), "generar", "--encargo", eid, *extra], cwd=ROOT,
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if senal:
                limite = time.monotonic() + 20
                while not (marcas / "arrancado").exists() and time.monotonic() < limite:
                    time.sleep(0.1)
                proc.send_signal(signal.SIGTERM)
            try:
                out, err = proc.communicate(timeout=90)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
            try:
                datos = json.loads(out)
            except ValueError:
                datos = None
            return proc.returncode, datos, (err or out)[-400:]

        def muerto(archivo_pid: pathlib.Path) -> bool:
            if not archivo_pid.exists():
                return False
            pid = int(archivo_pid.read_text())
            limite = time.monotonic() + 5
            while time.monotonic() < limite:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    return True
                time.sleep(0.1)
            return False

        try:
            eid = encargo(1)
            codigo, datos, cola = generar(eid, "bien")
            enc = E.cargar(encs / f"{eid}.json")
            check(codigo == 0 and campo(datos, "ok") is True and enc["estado"] == "generado"
                  and enc["imagenes"][0]["ancho"] == 768
                  and campo(datos, "respuesta") == {"estado": "generado", "encargo_id": eid},
                  f"(a) Codex genera y registra: exit 0, generado y respuesta leída ({codigo}, {datos or cola})")
            check(muerto(marcas / f"fondo-{eid}.pid"),
                  "(a) tras una salida normal de Codex no sobrevive su hijo en segundo plano")

            eid = encargo(2)
            codigo, datos, cola = generar(eid, "ajeno")
            enc = E.cargar(encs / f"{eid}.json")
            check(codigo == 6 and enc["estado"] == "bloqueado" and enc["imagenes"] == []
                  and str(ajeno.relative_to(ROOT)) in (campo(datos, "ajenos") or []),
                  f"(b) Codex escribe fuera de lo permitido: exit 6 y el encargo no queda generado ({codigo}, {datos or cola})")

            eid = encargo(3)
            inicio = time.monotonic()
            codigo, datos, cola = generar(eid, "colgado", "--timeout", "2")
            duracion = time.monotonic() - inicio
            enc = E.cargar(encs / f"{eid}.json")
            check(codigo == 1 and enc["estado"] == "pedido" and enc["lock_owner"] is None and duracion < 45,
                  f"(c) Codex colgado: exit 1 tras --timeout y el encargo vuelve a pedido ({codigo}, {duracion:.1f} s, {datos or cola})")
            check(muerto(marcas / "nieto.pid"), "(c) el grupo de procesos de Codex muere entero, nietos incluidos")

            for marca in marcas.iterdir():
                marca.unlink()
            eid = encargo(4)
            codigo, datos, cola = generar(eid, "colgado", "--timeout", "60", senal=True)
            enc = E.cargar(encs / f"{eid}.json")
            check(codigo == 1 and datos == {"ok": False, "errores": [f"interrumpido por señal {int(signal.SIGTERM)}"],
                                            "ajenos": []}
                  and enc["estado"] == "pedido",
                  f"(d) SIGTERM a generar: mata a Codex, pasa la guardia, deja el encargo en pedido y sale con 1 ({codigo}, {datos or cola})")
            check(muerto(marcas / "nieto.pid"), "(d) tras la señal no queda ningún proceso de Codex")

            for marca in marcas.iterdir():
                marca.unlink()
            eid = encargo(5)
            codigo, datos, cola = generar(eid, "ajeno-colgado", "--timeout", "60", senal=True, fuera=ajeno_senal)
            enc = E.cargar(encs / f"{eid}.json")
            errores = campo(datos, "errores") or [""]
            check(codigo == 6 and enc["estado"] == "bloqueado" and enc["imagenes"] == [] and len(enc["intentos"]) == 1
                  and str(ajeno_senal.relative_to(ROOT)) in (campo(datos, "ajenos") or [])
                  and errores[0].startswith(f"interrumpido por señal {int(signal.SIGTERM)}; cambió: "),
                  f"(e) Codex escribe fuera y llega SIGTERM con el encargo en generando: exit 6 con los ajenos y "
                  f"el encargo queda bloqueado ({codigo}, {enc['estado']}, {datos or cola})")
            check(muerto(marcas / "nieto.pid"), "(e) tras la señal no queda ningún proceso de Codex")

            eid = encargo(7)
            codigo, datos, cola = generar(eid, "ajeno-sin-generar", fuera=ajeno_sin_generar)
            enc = E.cargar(encs / f"{eid}.json")
            ultimo = (enc["intentos"] or [{}])[-1]
            check(codigo == 6 and enc["estado"] == "bloqueado" and enc["lock_owner"] is None
                  and len(enc["intentos"]) == 1 and ultimo.get("resultado") == "fallo"
                  and str(ajeno_sin_generar.relative_to(ROOT)) in (campo(datos, "ajenos") or []),
                  f"(g) Codex escribe fuera y falla sin registrar imágenes (encargo en generando): exit 6 y el "
                  f"encargo queda bloqueado, no vuelve a pedido ({codigo}, {enc['estado']}, {datos or cola})")

            encargos_en_repo.mkdir(parents=True)
            eid = encargo(6, carpeta=encargos_en_repo)
            codigo, datos, cola = generar(eid, "tmp", carpeta=encargos_en_repo)
            check(codigo == 0 and (encargos_en_repo / f".{eid}.json.tmp").exists()
                  and E.cargar(encargos_en_repo / f"{eid}.json")["estado"] == "generado",
                  f"(f) encargos dentro del repo: el JSON y su temporal de escritura no cuentan como ajenos ({codigo}, {datos or cola})")
            check(set(temporal.glob("codex-exec-*")) == salidas_antes,
                  "ningún generar deja carpetas ni archivos codex-exec-* en el temporal")
        finally:
            shutil.rmtree(carpeta_assets, ignore_errors=True)
            shutil.rmtree(encargos_en_repo, ignore_errors=True)
            ajeno.unlink(missing_ok=True)
            ajeno_senal.unlink(missing_ok=True)
            ajeno_sin_generar.unlink(missing_ok=True)


def seccion_render() -> None:
    print("\n12. render y tarjeta: máster determinista en proceso, sin tocar experiments/media-lab/assets/ del repo")
    import hashlib
    import json
    import tempfile
    from datetime import datetime, timezone
    from PIL import Image
    from labkit import encargos as E

    t = datetime.now(timezone.utc)

    def encargo_aprobado(raiz, familia, eid, formato, ancho_img=None, alto_img=None):
        ancho_img = ancho_img or formato["ancho"]
        alto_img = alto_img or formato["alto"]
        enc = E.nuevo(eid, coverage_cell_ids=["X"], family_id=familia, brief_path="b.md", do_not_use=[],
                      formato=formato, prompt="Un dibujo de prueba", restricciones=["sin texto"],
                      destino_assets=f"experiments/media-lab/assets/{familia}", ahora=t)
        ruta_img = f"experiments/media-lab/assets/{familia}/{eid}-v1.png"
        p = raiz / ruta_img
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (ancho_img, alto_img), (90, 96, 102)).save(p, "PNG")
        imagen = {"ruta": ruta_img, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                  "ancho": ancho_img, "alto": alto_img}
        E.tomar(enc, "codex-heartbeat", t)
        E.marcar_generado(enc, "codex-heartbeat", [imagen], t)
        E.revisar(enc, aprobado=True, motivo="prueba", ahora=t)
        E.guardar(raiz / "encargos" / f"{eid}.json", enc)
        return eid

    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d)
        (raiz / "encargos").mkdir()
        (raiz / "coverage.json").write_text(json.dumps({"cells": []}), encoding="utf-8")
        with LabAislado(raiz) as lab:
            eid_feed = encargo_aprobado(raiz, "LAB-RENDER-001", "ENC-20260101-001", {"ancho": 1080, "alto": 1350})
            eid_story = encargo_aprobado(raiz, "LAB-RENDER-001", "ENC-20260101-002", {"ancho": 1080, "alto": 1920})

            codigo, datos, err = lab("render", "--encargo", eid_feed, "--variante", "1", "--formato", "feed",
                                     "--titular", "UNO|DOS|TRES", "--subtitulo", "Subtítulo",
                                     "--salida", "feed.jpg")
            destino_feed = raiz / "experiments/media-lab/assets/LAB-RENDER-001/feed.jpg"
            check(codigo == 0 and campo(datos, "ok") is True and campo(datos, "ancho") == 1080
                  and campo(datos, "alto") == 1350 and destino_feed.is_file()
                  and campo(datos, "sha256") == hashlib.sha256(destino_feed.read_bytes()).hexdigest(),
                  f"render feed produce un JPEG 1080x1350 con su sha256 ({codigo}, {datos or err})")

            codigo, datos, err = lab("render", "--encargo", eid_story, "--variante", "1", "--formato", "story",
                                     "--titular", "UNO|DOS|TRES", "--subtitulo", "Subtítulo",
                                     "--aviso", "PRESENTADORA FICTICIA", "--salida", "story.jpg")
            destino_story = raiz / "experiments/media-lab/assets/LAB-RENDER-001/story.jpg"
            check(codigo == 0 and campo(datos, "ancho") == 1080 and campo(datos, "alto") == 1920
                  and destino_story.is_file(), f"render story produce un JPEG 1080x1920 ({codigo}, {datos or err})")

            eid_pedido = "ENC-20260101-099"
            enc_pedido = E.nuevo(eid_pedido, coverage_cell_ids=["X"], family_id="LAB-RENDER-001", brief_path="b.md",
                                 do_not_use=[], formato={"ancho": 1080, "alto": 1350}, prompt="Un dibujo",
                                 restricciones=[], destino_assets="experiments/media-lab/assets/LAB-RENDER-001",
                                 ahora=t)
            E.guardar(raiz / "encargos" / f"{eid_pedido}.json", enc_pedido)
            codigo, datos, _ = lab("render", "--encargo", eid_pedido, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "no.jpg")
            check(codigo == 2, f"render rechaza un encargo en pedido ({codigo}, {datos})")

            eid_hash = encargo_aprobado(raiz, "LAB-RENDER-001", "ENC-20260101-003", {"ancho": 1080, "alto": 1350})
            ruta_enc_hash = raiz / "encargos" / f"{eid_hash}.json"
            enc_hash = json.loads(ruta_enc_hash.read_text(encoding="utf-8"))
            enc_hash["imagenes"][0]["sha256"] = "0" * 64
            ruta_enc_hash.write_text(json.dumps(enc_hash), encoding="utf-8")
            codigo, datos, _ = lab("render", "--encargo", eid_hash, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "hash.jpg")
            check(codigo == 2 and campo(datos, "tipo") == "ImagenNoValida",
                  f"render rechaza un sha256 alterado ({codigo}, {datos})")

            print("   · I-2: el JSON del encargo (pudo pasar por Codex) no se da por bueno")

            def sin_escribir_nada(nombre_salida):
                return not (raiz / "experiments/media-lab/assets/LAB-RENDER-001" / nombre_salida).exists()

            eid_abs = encargo_aprobado(raiz, "LAB-RENDER-001", "ENC-20260101-004", {"ancho": 1080, "alto": 1350})
            ruta_enc_abs = raiz / "encargos" / f"{eid_abs}.json"
            enc_abs = json.loads(ruta_enc_abs.read_text(encoding="utf-8"))
            enc_abs["destino_assets"] = "/tmp/destino-absoluto-de-prueba"
            ruta_enc_abs.write_text(json.dumps(enc_abs), encoding="utf-8")
            codigo, datos, _ = lab("render", "--encargo", eid_abs, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "abs-destino.jpg")
            check(codigo == 2 and sin_escribir_nada("abs-destino.jpg"),
                  f"render rechaza un destino_assets absoluto sin escribir nada ({codigo}, {datos})")

            eid_dd = encargo_aprobado(raiz, "LAB-RENDER-001", "ENC-20260101-005", {"ancho": 1080, "alto": 1350})
            ruta_enc_dd = raiz / "encargos" / f"{eid_dd}.json"
            enc_dd = json.loads(ruta_enc_dd.read_text(encoding="utf-8"))
            enc_dd["imagenes"][0]["ruta"] = "experiments/media-lab/assets/LAB-RENDER-001/../../../etc/passwd"
            ruta_enc_dd.write_text(json.dumps(enc_dd), encoding="utf-8")
            codigo, datos, _ = lab("render", "--encargo", eid_dd, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "ruta-dd.jpg")
            check(codigo == 2 and sin_escribir_nada("ruta-dd.jpg"),
                  f"render rechaza una ruta de imagen con «..» sin escribir nada ({codigo}, {datos})")

            eid_rabs = encargo_aprobado(raiz, "LAB-RENDER-001", "ENC-20260101-006", {"ancho": 1080, "alto": 1350})
            ruta_enc_rabs = raiz / "encargos" / f"{eid_rabs}.json"
            enc_rabs = json.loads(ruta_enc_rabs.read_text(encoding="utf-8"))
            enc_rabs["imagenes"][0]["ruta"] = "/etc/passwd"
            ruta_enc_rabs.write_text(json.dumps(enc_rabs), encoding="utf-8")
            codigo, datos, _ = lab("render", "--encargo", eid_rabs, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "ruta-abs.jpg")
            check(codigo == 2 and sin_escribir_nada("ruta-abs.jpg"),
                  f"render rechaza una ruta de imagen absoluta sin escribir nada ({codigo}, {datos})")

            eid_link = encargo_aprobado(raiz, "LAB-RENDER-001", "ENC-20260101-007", {"ancho": 1080, "alto": 1350})
            fuera = raiz / "fuera-del-repo"
            fuera.mkdir()
            imagen_fuera = fuera / "escondida.png"
            Image.new("RGB", (1080, 1350), (10, 20, 30)).save(imagen_fuera, "PNG")
            enlace = raiz / "experiments/media-lab/assets/LAB-RENDER-001/enlace"
            enlace.symlink_to(fuera, target_is_directory=True)
            ruta_enc_link = raiz / "encargos" / f"{eid_link}.json"
            enc_link = json.loads(ruta_enc_link.read_text(encoding="utf-8"))
            enc_link["imagenes"][0] = {
                "ruta": "experiments/media-lab/assets/LAB-RENDER-001/enlace/escondida.png",
                "sha256": hashlib.sha256(imagen_fuera.read_bytes()).hexdigest(), "ancho": 1080, "alto": 1350}
            ruta_enc_link.write_text(json.dumps(enc_link), encoding="utf-8")
            codigo, datos, _ = lab("render", "--encargo", eid_link, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "ruta-enlazada.jpg")
            check(codigo == 2 and sin_escribir_nada("ruta-enlazada.jpg"),
                  f"render rechaza una carpeta intermedia enlazada fuera de destino_assets ({codigo}, {datos})")

            codigo, datos, _ = lab("render", "--encargo", eid_feed, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS", "--subtitulo", "Sub", "--salida", "dos-lineas.jpg")
            check(codigo == 2, f"render exige exactamente 3 líneas en --titular ({codigo}, {datos})")

            codigo, datos, _ = lab("render", "--encargo", eid_feed, "--variante", "1", "--formato", "story",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "mal-formato.jpg")
            check(codigo == 2, f"render rechaza un --formato que no coincide con el del encargo ({codigo}, {datos})")

            for salida, motivo in (("sub/archivo.jpg", "contiene «/»"), ("../fuera.jpg", "contiene «..»"),
                                   ("feed.png", "no es .jpg/.jpeg (render_overlay siempre escribe JPEG)"),
                                   ("archivo con espacio.jpg", "tiene un espacio"),
                                   ("archivo-tílde.jpg", "tiene una tilde")):
                codigo, datos, _ = lab("render", "--encargo", eid_feed, "--variante", "1", "--formato", "feed",
                                       "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", salida)
                check(codigo == 2, f"render rechaza --salida que {motivo} ({codigo}, {datos})")

            codigo, datos, _ = lab("render", "--encargo", eid_feed, "--variante", "1", "--formato", "feed",
                                   "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "feed.jpg")
            check(codigo == 2, f"render no pisa un máster ya existente ({codigo}, {datos})")

            print("   · escritura atómica: un fallo a mitad no deja destino ni temporal")
            import render_overlay

            def render_a_medias(source, destination, lines, sub, panel_rgb, accent_rgb, output_format, disclosure):
                pathlib.Path(destination).write_bytes(b"mitad de un jpeg")
                raise OSError("disco lleno (simulado)")

            destino_falla = raiz / "experiments/media-lab/assets/LAB-RENDER-001/falla.jpg"
            temporal_falla = raiz / "experiments/media-lab/assets/LAB-RENDER-001/.falla.jpg.tmp"
            original_render = render_overlay.render
            render_overlay.render = render_a_medias
            try:
                codigo, datos, _ = lab("render", "--encargo", eid_feed, "--variante", "1", "--formato", "feed",
                                       "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "falla.jpg")
            finally:
                render_overlay.render = original_render
            check(codigo == 2 and not destino_falla.exists() and not temporal_falla.exists(),
                  f"un fallo al renderizar no deja destino ni temporal ({codigo}, {datos})")
            codigo, datos, err = lab("render", "--encargo", eid_feed, "--variante", "1", "--formato", "feed",
                                     "--titular", "UNO|DOS|TRES", "--subtitulo", "Sub", "--salida", "falla.jpg")
            check(codigo == 0 and destino_falla.is_file(),
                  f"un reintento con el mismo --salida funciona tras el fallo ({codigo}, {datos or err})")

        print("   · tarjeta")
        with LabAislado(raiz) as lab:
            codigo, datos, err = lab("tarjeta", "--familia", "LAB-CARD-001",
                                     "--cita", "Una cita breve para la prueba de la tarjeta.",
                                     "--autor", "Autor de Prueba", "--salida", "card.png")
            destino_card = raiz / "experiments/media-lab/assets/LAB-CARD-001/card.png"
            check(codigo == 0 and campo(datos, "ok") is True and campo(datos, "ancho") == 1080
                  and campo(datos, "alto") == 1350 and destino_card.is_file(),
                  f"tarjeta produce un PNG 1080x1350 ({codigo}, {datos or err})")
            codigo, datos, _ = lab("tarjeta", "--familia", "LAB CARD 002", "--cita", "Otra cita.",
                                   "--autor", "Autor", "--salida", "otra.png")
            check(codigo == 2, f"tarjeta rechaza una familia con espacios ({codigo}, {datos})")
            for salida, motivo in (("con espacio.png", "tiene un espacio"), ("con-tílde.png", "tiene una tilde")):
                codigo, datos, _ = lab("tarjeta", "--familia", "LAB-CARD-001", "--cita", "Otra cita.",
                                       "--autor", "Autor", "--salida", salida)
                check(codigo == 2, f"tarjeta rechaza --salida que {motivo} ({codigo}, {datos})")

            import quote_card

            def make_card_a_medias(quote, author, out_path, variant="cream", kicker="SABIDURÍA DE BOLSILLO"):
                pathlib.Path(out_path).write_bytes(b"mitad de un png")
                raise OSError("disco lleno (simulado)")

            destino_falla = raiz / "experiments/media-lab/assets/LAB-CARD-001/falla.png"
            temporal_falla = raiz / "experiments/media-lab/assets/LAB-CARD-001/.falla.png.tmp"
            original_make_card = quote_card.make_card
            quote_card.make_card = make_card_a_medias
            try:
                codigo, datos, _ = lab("tarjeta", "--familia", "LAB-CARD-001",
                                       "--cita", "Otra cita de prueba.", "--autor", "Autor", "--salida", "falla.png")
            finally:
                quote_card.make_card = original_make_card
            check(codigo == 2 and not destino_falla.exists() and not temporal_falla.exists(),
                  f"un fallo al guardar la tarjeta no deja destino ni temporal ({codigo}, {datos})")
            codigo, datos, err = lab("tarjeta", "--familia", "LAB-CARD-001",
                                     "--cita", "Otra cita de prueba.", "--autor", "Autor", "--salida", "falla.png")
            check(codigo == 0 and destino_falla.is_file(),
                  f"un reintento con el mismo --salida funciona tras el fallo ({codigo}, {datos or err})")


def seccion_turno() -> None:
    print("\n13. turno: ventanas cada cada_horas horas alrededor del reloj")
    import json
    import os
    import subprocess
    import tempfile
    from labkit import turnos as T

    def config(d, ancla="2026-09-15T00:40:00+02:00", cada_horas=5, tolerancia_min=30):
        (pathlib.Path(d) / "turnos.json").write_text(
            json.dumps({"ancla": ancla, "cada_horas": cada_horas, "tolerancia_min": tolerancia_min}),
            encoding="utf-8")

    print("   · lógica pura (labkit.turnos)")
    from datetime import datetime
    ancla = datetime.fromisoformat("2026-09-15T00:40:00+02:00")
    casos = [
        ("2026-09-15T00:40:00+02:00", True, "toca"),
        ("2026-09-15T05:40:00+02:00", True, "toca"),
        ("2026-09-15T01:40:00+02:00", False, "fuera del turno"),
        ("2026-09-15T05:35:00+02:00", False, "fuera del turno"),
        ("2026-09-15T06:00:00+02:00", True, "toca"),
        ("2026-09-15T06:11:00+02:00", False, "fuera del turno"),
        # margen de 2 min hacia atrás (M-6): un disparo justo antes de la marca no pierde el turno.
        ("2026-09-15T00:39:00+02:00", True, "toca"),
        ("2026-09-15T00:37:00+02:00", False, "fuera del turno"),
    ]
    for iso, toca_esperado, motivo_esperado in casos:
        r = T.turno_actual(datetime.fromisoformat(iso), ancla, 5, 30, None)
        check(r["toca"] == toca_esperado and r["motivo"] == motivo_esperado,
              f"{iso} → toca={toca_esperado} ({r})")
    r = T.turno_actual(datetime.fromisoformat("2026-09-15T00:40:00+02:00"), ancla, 5, 30,
                       ultimo_atendido="2026-09-14T22:40:00+00:00")
    check(r["toca"] is False and r["motivo"] == "turno ya atendido", f"un turno ya atendido no vuelve a tocar ({r})")
    from zoneinfo import ZoneInfo
    madrid = ZoneInfo("Europe/Madrid")
    r = T.turno_actual(datetime.fromisoformat("2026-10-25T00:41:00+02:00"), ancla, 5, 30, None)
    check((r["siguiente"] - r["turno_inicio"]).total_seconds() == 18000,
          f"dos turnos seguidos a caballo del cambio de hora del 25 de octubre están separados 18000 s reales ({r})")
    check(r["turno_inicio"].astimezone(madrid).isoformat(timespec="seconds") == "2026-10-25T00:40:00+02:00"
          and r["siguiente"].astimezone(madrid).isoformat(timespec="seconds") == "2026-10-25T04:40:00+01:00",
          f"en hora de Madrid el turno pasa de +02:00 a +01:00 con el cambio de hora ({r})")
    # M-7: prueba de DST no tautológica, encadenando el turno_inicio de un lado del cambio de
    # hora con el siguiente del turno del otro lado.
    r_antes = T.turno_actual(datetime.fromisoformat("2026-10-25T00:41:00+02:00"), ancla, 5, 30, None)
    r_despues = T.turno_actual(datetime.fromisoformat("2026-10-25T04:41:00+01:00"), ancla, 5, 30, None)
    check(r_despues["toca"] is True and r_despues["turno_inicio"] == r_antes["siguiente"],
          f"el turno de las 04:41+01:00 es el siguiente del de las 00:40+02:00 ({r_antes}, {r_despues})")

    print("   · CLI lab.py turno")
    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d)
        config(raiz)
        with LabAislado(raiz) as lab:
            codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T00:40:00+02:00")
            check(codigo == 0 and campo(datos, "toca") is True, f"toca en el ancla exacta ({codigo}, {datos})")
            codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T01:40:00+02:00")
            check(codigo == 0 and campo(datos, "toca") is False, f"no toca una hora después ({codigo}, {datos})")
            codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T23:40:00Z")
            check(codigo == 0 and campo(datos, "toca") is True
                  and campo(datos, "turno_inicio_madrid") == "2026-09-16T01:40:00+02:00",
                  f"un día después la hora local ha girado 1h: toca a la 01:40 de Madrid ({codigo}, {datos})")

            turno_hecho = raiz / ".turno-hecho"
            check(not turno_hecho.exists(), "de partida no hay .turno-hecho")

            # M-5: --ahora junto con --marcar exige LAB_TURNOS (delata que es una prueba).
            check("LAB_TURNOS" not in os.environ, "de partida no hay LAB_TURNOS en el entorno")
            codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T00:40:00+02:00", "--marcar")
            check(codigo == 2 and "LAB_TURNOS" in (campo(datos, "error") or "") and not turno_hecho.exists(),
                  f"--ahora junto con --marcar sin LAB_TURNOS sale con 2 sin marcar ({codigo}, {datos})")

            os.environ["LAB_TURNOS"] = str(raiz / "turnos.json")
            try:
                codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T02:00:00+02:00", "--marcar")
                check(codigo == 2 and campo(datos, "error") == "no se marca: fuera del turno"
                      and not turno_hecho.exists(),
                      f"--marcar fuera de turno (sin marcar previo) sale con 2 y no crea .turno-hecho ({codigo}, {datos})")

                codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T00:40:00+02:00", "--marcar")
                check(codigo == 0 and campo(datos, "marcado") is True and turno_hecho.is_file(),
                      f"--marcar escribe .turno-hecho cuando toca ({codigo}, {datos})")
                marcado_antes = turno_hecho.read_text(encoding="utf-8")

                # I-1: dos --marcar seguidos sobre el MISMO turno (mismo --ahora): el segundo no marca.
                codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T00:40:00+02:00", "--marcar")
                check(codigo == 2 and campo(datos, "error") == "no se marca: turno ya atendido"
                      and turno_hecho.read_text(encoding="utf-8") == marcado_antes,
                      f"dos --marcar seguidos sobre el mismo turno: el segundo sale con 2 ({codigo}, {datos})")

                codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T00:45:00+02:00")
                check(codigo == 0 and campo(datos, "toca") is False and campo(datos, "motivo") == "turno ya atendido",
                      f"una segunda llamada ya no toca: turno ya atendido ({codigo}, {datos})")
                codigo, datos, _ = lab("turno", "--ahora", "2026-09-15T02:00:00+02:00", "--marcar")
                check(codigo == 2 and turno_hecho.read_text(encoding="utf-8") == marcado_antes,
                      f"--marcar de un turno ya atendido tampoco toca .turno-hecho ({codigo}, {datos})")
            finally:
                del os.environ["LAB_TURNOS"]

        with LabAislado(raiz) as lab:
            (raiz / "turnos.json").write_text("{ no es json", encoding="utf-8")
            codigo, datos, _ = lab("turno")
            check(codigo == 2, f"turnos.json inválido sale con 2 ({codigo}, {datos})")
            (raiz / "turnos.json").write_text(json.dumps({"ancla": "2026-09-15T00:40:00+02:00"}), encoding="utf-8")
            codigo, datos, _ = lab("turno")
            check(codigo == 2, f"turnos.json incompleto sale con 2 ({codigo}, {datos})")

    print("   · I-1: --marcar es atómico entre dos procesos a la vez")
    with tempfile.TemporaryDirectory() as d2:
        raiz2 = pathlib.Path(d2)
        turnos_json = raiz2 / "turnos.json"
        turnos_json.write_text(json.dumps({"ancla": "2026-09-15T00:40:00+02:00", "cada_horas": 5,
                                           "tolerancia_min": 30}), encoding="utf-8")
        turno_hecho2 = raiz2 / ".turno-hecho"
        env = {**os.environ, "LAB_TURNOS": str(turnos_json), "LAB_TURNO_HECHO": str(turno_hecho2)}
        lab_py = ROOT / "experiments" / "media-lab" / "lab.py"
        cmd = [sys.executable, str(lab_py), "turno", "--ahora", "2026-09-15T00:40:00+02:00", "--marcar"]
        procesos = [subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True) for _ in range(2)]
        salidas = [p.communicate() for p in procesos]
        codigos = sorted(p.returncode for p in procesos)
        check(codigos == [0, 2],
              f"de dos --marcar a la vez sobre el mismo turno, exactamente uno marca ({codigos}, {salidas})")
        check(turno_hecho2.is_file(), "el turno queda marcado tras la carrera de dos procesos")


def _enrutador(reglas):
    """Doble de `_get` sin red. `reglas` es una lista de (predicado(url, params) -> bool,
    respuesta); se usa la primera cuyo predicado casa. `respuesta` puede ser un dict, una
    excepción (se levanta) o una función(params) -> dict."""
    llamadas: list[tuple[str, dict]] = []

    def _get(url, params):
        llamadas.append((url, dict(params)))
        for predicado, respuesta in reglas:
            if predicado(url, params):
                if isinstance(respuesta, BaseException):
                    raise respuesta
                return respuesta(params) if callable(respuesta) else respuesta
        raise AssertionError(f"sin regla falsa para GET {url} {params}")

    _get.llamadas = llamadas
    return _get


def _ejecutar_verify(modulo, manifest, tmp_path, *, metricas=False, get=None, env=None):
    """verify_api.main() en proceso: escribe el manifiesto, sustituye `_get` y el entorno,
    y devuelve (código, verification-result.json, llamadas, stdout)."""
    import contextlib
    import io
    import json
    import os

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "verification-result.json"
    argv = ["verify_api.py", str(manifest_path), "--output", str(output_path)]
    if metricas:
        argv.append("--metricas")

    argv_previo, get_previo, environ_previo = sys.argv, modulo._get, dict(os.environ)
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = argv
        if get is not None:
            modulo._get = get
        if env is not None:
            os.environ.update(env)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                codigo = modulo.main()
            except SystemExit as e:
                codigo = e.code if isinstance(e.code, int) else 1
    finally:
        sys.argv = argv_previo
        modulo._get = get_previo
        os.environ.clear()
        os.environ.update(environ_previo)
    datos = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
    return codigo, datos, (get.llamadas if get is not None else []), out.getvalue()


def seccion_metricas() -> None:
    print("\n14. Métricas desatendidas: verify_api --metricas, shortcode de Instagram y metricas-registrar")
    import json
    import os
    import tempfile
    from labkit import metricas as ME

    modulo = modulo_verify()
    GRAPH, THREADS_GRAPH = modulo.GRAPH, modulo.THREADS_GRAPH
    ENTORNO_META = {"SDB_PAGE_TOKEN": "PT", "SDB_THREADS_TOKEN": "TT", "SDB_IG_USER_ID": "IGUSER"}
    METRICAS_FB = modulo.METRICAS["facebook"]
    METRICAS_IG_FEED = modulo.METRICAS["instagram_feed"]
    METRICAS_IG_STORY = modulo.METRICAS["instagram_story"]
    METRICAS_TH = modulo.METRICAS["threads"]

    def valores(nombre, valor):
        return {"name": nombre, "values": [{"value": valor}]}

    def total_value(nombre, valor):
        return {"name": nombre, "total_value": {"value": valor}}

    print("   · verify_api --metricas: por red, feed, story y la rama total_value de _valor")
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        manifest = {"run_group_id": "LAB-MET-001-API",
                    "post_ids": {"facebook": "FB1", "instagram": "IG1", "threads": "TH1"}}
        respuesta_fb = [valores(n, i) for i, n in enumerate(METRICAS_FB, start=100)]
        # La primera llega en la forma total_value (métricas agregadas más recientes de
        # Meta), no en values: _valor() tiene que saber leer las dos formas.
        respuesta_fb[0] = total_value(METRICAS_FB[0], 999)
        reglas = [
            (lambda u, p, u_=f"{GRAPH}/FB1": u == u_, {"id": "FB1", "permalink_url": "https://fb/x"}),
            (lambda u, p, u_=f"{GRAPH}/IG1": u == u_, {"id": "IG1", "permalink": "https://instagram.com/p/IG1/"}),
            (lambda u, p, u_=f"{THREADS_GRAPH}/TH1": u == u_, {"id": "TH1", "permalink": "https://threads/x"}),
            # Facebook solo trae datos con period=lifetime; Instagram y Threads no llevan period.
            (lambda u, p, u_=f"{GRAPH}/FB1/insights": u == u_ and set(p["metric"].split(",")) == set(METRICAS_FB)
             and p.get("period") == "lifetime",
             {"data": respuesta_fb}),
            (lambda u, p, u_=f"{GRAPH}/IG1/insights": u == u_ and set(p["metric"].split(",")) == set(METRICAS_IG_FEED)
             and "period" not in p,
             {"data": [valores(n, i) for i, n in enumerate(METRICAS_IG_FEED, start=1)]}),
            (lambda u, p, u_=f"{THREADS_GRAPH}/TH1/insights": u == u_ and set(p["metric"].split(",")) == set(METRICAS_TH)
             and "period" not in p,
             {"data": [valores(n, i) for i, n in enumerate(METRICAS_TH, start=10)]}),
        ]
        codigo, datos, _, _ = _ejecutar_verify(modulo, manifest, tmp, metricas=True,
                                               get=_enrutador(reglas), env=ENTORNO_META)
        r = datos["results"] if datos else {}
        esperado_fb = dict(zip(METRICAS_FB, range(100, 100 + len(METRICAS_FB))))
        esperado_fb[METRICAS_FB[0]] = 999
        check(codigo == 0, f"todo verificado sale con 0 ({codigo})")
        check(r.get("facebook", {}).get("metrics") == esperado_fb,
              f"facebook trae sus {len(METRICAS_FB)} métricas, una de ellas en forma total_value ({r.get('facebook')})")
        check("metrics_errors" not in r.get("facebook", {}), "sin errores, no se añade metrics_errors")
        check("metrics_observed_at" in r.get("facebook", {}), "metrics_observed_at queda registrado")
        check(r.get("instagram", {}).get("metrics") == dict(zip(METRICAS_IG_FEED, range(1, 1 + len(METRICAS_IG_FEED)))),
              f"instagram feed trae sus {len(METRICAS_IG_FEED)} métricas ({r.get('instagram')})")
        check(r.get("threads", {}).get("metrics") == dict(zip(METRICAS_TH, range(10, 10 + len(METRICAS_TH)))),
              f"threads trae sus {len(METRICAS_TH)} métricas ({r.get('threads')})")

    print("   · una métrica no soportada va a metrics_errors sin fallar la publicación")
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        manifest = {"run_group_id": "LAB-MET-002-API", "post_ids": {"facebook": "FB1"}}

        def insights_individual(p):
            m = p["metric"]
            if p.get("period") != "lifetime":
                raise RuntimeError("el reintento de una en una perdió period=lifetime")
            if m == "post_clicks":
                raise RuntimeError("(#100) el objeto no admite post_clicks")
            return {"data": [valores(m, len(m))]}

        reglas = [
            (lambda u, p, u_=f"{GRAPH}/FB1": u == u_, {"id": "FB1"}),
            (lambda u, p, u_=f"{GRAPH}/FB1/insights": u == u_ and "," in p["metric"],
             RuntimeError("el grupo entero falla por una métrica no soportada")),
            (lambda u, p, u_=f"{GRAPH}/FB1/insights": u == u_ and "," not in p["metric"], insights_individual),
        ]
        codigo, datos, _, _ = _ejecutar_verify(modulo, manifest, tmp, metricas=True,
                                               get=_enrutador(reglas), env=ENTORNO_META)
        r = (datos or {})["results"]["facebook"]
        esperado = {m: len(m) for m in METRICAS_FB if m != "post_clicks"}
        check(codigo == 0, f"una métrica no soportada no tira el código de salida ({codigo})")
        check(r["status"] == "verified", "la publicación sigue verificada")
        check(r["metrics"] == esperado,
              f"las {len(esperado)} métricas que sí funcionan quedan registradas ({r['metrics']})")
        check(list(r.get("metrics_errors", {})) == ["post_clicks"],
              f"la que falla queda en metrics_errors, no revienta las demás ({r.get('metrics_errors')})")

    print("   · Instagram Story usa sus propias métricas; Facebook Story no tiene métricas por API")
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        manifest = {"run_group_id": "LAB-MET-003-API", "post_ids": {"facebook": "FB1", "instagram": "IG1"},
                    "surfaces": {"facebook": "story", "instagram": "story"}}
        reglas = [
            (lambda u, p, u_=f"{GRAPH}/FB1": u == u_, {"id": "FB1"}),
            (lambda u, p, u_=f"{GRAPH}/IG1": u == u_, {"id": "IG1"}),
            (lambda u, p, u_=f"{GRAPH}/IG1/insights": u == u_ and set(p["metric"].split(",")) == set(METRICAS_IG_STORY),
             {"data": [valores(n, i) for i, n in enumerate(METRICAS_IG_STORY, start=1)]}),
        ]
        codigo, datos, llamadas, _ = _ejecutar_verify(modulo, manifest, tmp, metricas=True,
                                                       get=_enrutador(reglas), env=ENTORNO_META)
        r = datos["results"]
        check(r["facebook"]["metrics"] == {} and r["facebook"]["metrics_errors"] == {"*": "not_available_via_api"},
              f"facebook story: sin métricas por API ({r['facebook']})")
        check(not any(u.endswith("FB1/insights") for u, _ in llamadas),
              "facebook story no llega a pedir insights: se sabe de antemano que no existen")
        check(r["instagram"]["metrics"] == dict(zip(METRICAS_IG_STORY, range(1, 1 + len(METRICAS_IG_STORY)))),
              f"instagram story pide sus propias métricas, no las de feed ({r['instagram']})")

    print("   · búsqueda de Instagram por shortcode (publicaciones por teléfono)")
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        manifest = {"run_group_id": "LAB-MET-004-API", "instagram_shortcodes": {"instagram": "DdR54JEgxHN"}}
        pagina_2 = f"{GRAPH}/IGUSER/media?after=CURSOR1"
        reglas = [
            (lambda u, p, u_=f"{GRAPH}/IGUSER/media": u == u_,
             {"data": [{"id": "1", "permalink": "https://www.instagram.com/p/OTRO1/", "timestamp": "t"}],
              "paging": {"next": pagina_2}}),
            (lambda u, p, u_=pagina_2: u == u_,
             {"data": [{"id": "17999", "permalink": "https://www.instagram.com/p/DdR54JEgxHN/", "timestamp": "t2"}],
              "paging": {}}),
            (lambda u, p, u_=f"{GRAPH}/17999": u == u_, {"id": "17999", "permalink": "https://www.instagram.com/p/DdR54JEgxHN/"}),
        ]
        codigo, datos, llamadas, _ = _ejecutar_verify(modulo, manifest, tmp, get=_enrutador(reglas), env=ENTORNO_META)
        r = datos["results"]["instagram"]
        check(codigo == 0 and r["status"] == "verified", f"el shortcode que casa en la 2.ª página verifica ({codigo}, {r})")
        check(r.get("graph_media_id") == "17999", f"guarda el id de Graph resuelto, no el shortcode ({r})")
        check(sum(1 for u, _ in llamadas if u.endswith("/media") or "after=CURSOR1" in u) == 2,
              "paginó exactamente hasta encontrarlo, ni una página de más")

        manifest_sin = {"run_group_id": "LAB-MET-005-API", "instagram_shortcodes": {"instagram": "NOEXISTE1234"}}
        reglas_sin = [
            (lambda u, p, u_=f"{GRAPH}/IGUSER/media": u == u_,
             {"data": [{"id": "1", "permalink": "https://www.instagram.com/p/OTRO1/", "timestamp": "t"}],
              "paging": {"next": f"{GRAPH}/IGUSER/media?after=A"}}),
            (lambda u, p, u_=f"{GRAPH}/IGUSER/media?after=A": u == u_,
             {"data": [], "paging": {"next": f"{GRAPH}/IGUSER/media?after=B"}}),
            (lambda u, p, u_=f"{GRAPH}/IGUSER/media?after=B": u == u_, {"data": [], "paging": {}}),
        ]
        codigo, datos, llamadas, _ = _ejecutar_verify(modulo, manifest_sin, tmp, get=_enrutador(reglas_sin), env=ENTORNO_META)
        r = datos["results"]["instagram"]
        check(codigo == 1 and r["status"] == "failed" and r["error_type"] == "ShortcodeNoEncontrado",
              f"el shortcode que no casa en 3 páginas falla sin inventar un id ({codigo}, {r})")
        check(len(llamadas) == 3, f"se detiene a las 3 páginas ({len(llamadas)})")

        codigo, datos, _, _ = _ejecutar_verify(modulo, manifest, tmp, get=_enrutador(reglas),
                                               env={"SDB_PAGE_TOKEN": "PT", "SDB_THREADS_TOKEN": "TT"})
        r = datos["results"]["instagram"]
        check(r["status"] == "failed" and r["error_type"] == "ConfiguracionIncompleta" and "SDB_IG_USER_ID" in r["error"],
              f"sin SDB_IG_USER_ID falla con su propio error_type, no ShortcodeNoEncontrado ({r})")

        def revienta_red(p):
            raise ConnectionError("Name or service not known")

        reglas_red = [(lambda u, p, u_=f"{GRAPH}/IGUSER/media": u == u_, revienta_red)]
        codigo, datos, _, _ = _ejecutar_verify(modulo, manifest, tmp, get=_enrutador(reglas_red), env=ENTORNO_META)
        r = datos["results"]["instagram"]
        check(r["status"] == "failed" and r["error_type"] == "BusquedaFallida",
              f"un fallo de red o API al paginar es BusquedaFallida, no ShortcodeNoEncontrado ({r})")

    print("   · nunca se guarda ni se imprime un access_token, aunque venga dentro de un mensaje de error")
    TOKEN = "EAASECRETTOKEN"  # noqa: N806

    def revienta_con_token(p):
        raise RuntimeError(f"HTTP 400: fallo pidiendo https://graph.facebook.com/v24.0/FB1?access_token={TOKEN}")

    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)

        # en la lectura del post
        manifest = {"run_group_id": "LAB-TOK-001-API", "post_ids": {"facebook": "FB1"}}
        codigo, datos, _, salida = _ejecutar_verify(
            modulo, manifest, tmp, metricas=True,
            get=_enrutador([(lambda u, p: True, revienta_con_token)]), env=ENTORNO_META)
        crudo = (tmp / "verification-result.json").read_text(encoding="utf-8")
        check(TOKEN not in crudo and TOKEN not in salida,
              "un token en el error de leer el post no llega ni al JSON ni a stdout")
        check("***" in datos["results"]["facebook"]["error"], "el token queda como *** en su lugar")

        # en métricas (el post se lee bien, insights revienta)
        manifest2 = {"run_group_id": "LAB-TOK-002-API", "post_ids": {"facebook": "FB1"}}
        reglas2 = [
            (lambda u, p, u_=f"{GRAPH}/FB1": u == u_, {"id": "FB1"}),
            (lambda u, p, u_=f"{GRAPH}/FB1/insights": u == u_, revienta_con_token),
        ]
        codigo, datos, _, salida = _ejecutar_verify(modulo, manifest2, tmp, metricas=True,
                                                    get=_enrutador(reglas2), env=ENTORNO_META)
        crudo = (tmp / "verification-result.json").read_text(encoding="utf-8")
        check(TOKEN not in crudo and TOKEN not in salida,
              "un token en el error de métricas no llega ni al JSON ni a stdout")

        # en la paginación del shortcode (paging.next lleva el access_token en la URL)
        manifest3 = {"run_group_id": "LAB-TOK-003-API", "instagram_shortcodes": {"instagram": "DdR54JEgxHN"}}
        siguiente_con_token = f"{GRAPH}/IGUSER/media?access_token={TOKEN}&after=X"
        reglas3 = [
            (lambda u, p, u_=f"{GRAPH}/IGUSER/media": u == u_, {"data": [], "paging": {"next": siguiente_con_token}}),
            (lambda u, p, u_=siguiente_con_token: u == u_, revienta_con_token),
        ]
        codigo, datos, _, salida = _ejecutar_verify(modulo, manifest3, tmp, get=_enrutador(reglas3), env=ENTORNO_META)
        crudo = (tmp / "verification-result.json").read_text(encoding="utf-8")
        check(TOKEN not in crudo and TOKEN not in salida,
              "un token en la URL de paginación o en el error que levanta no llega ni al JSON ni a stdout")

    print("   · _redactar: patrón (mayúsculas, %3D, JSON) y valor de los secretos del entorno")
    from urllib.parse import quote

    entorno_previo = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update({"SDB_PAGE_TOKEN": TOKEN, "SDB_THREADS_TOKEN": "TT"})
        casos = [
            (f'{{"access_token": "{TOKEN}", "ok": true}}', "token en un JSON de error"),
            (f"redirect%3Fto%3Dhttps%3A%2F%2Fx%3Faccess_token%3D{TOKEN}%26foo%3Dbar", "token con %3D"),
            (f"ACCESS_TOKEN={TOKEN} rejected", "ACCESS_TOKEN= en mayúsculas"),
            (f"credential rejected: {TOKEN}", "el token suelto, sin ningún patrón delante"),
        ]
        for texto, label in casos:
            redactado = modulo._redactar(texto)
            check(TOKEN not in redactado and "***" in redactado, f"_redactar quita el token: {label} ({redactado!r})")

        os.environ["SDB_SHORT_TOKEN"] = "PT"  # 2 caracteres: el mismo valor corto que usan otras pruebas
        check(modulo._redactar("PT aparece aquí como texto normal") == "PT aparece aquí como texto normal",
              "un valor de menos de 8 caracteres no activa la redacción por valor (no destroza texto legítimo)")

        os.environ["SDB_OTRA_TOKEN_COSA"] = "OTRASECRETALARGA"
        check("OTRASECRETALARGA" not in modulo._redactar("x OTRASECRETALARGA y"),
              "cualquier variable SDB_*TOKEN* del entorno se redacta por valor, no solo las dos conocidas")

        token_especial = "EAA/SEC+RET=1?"  # más de 8 caracteres, con símbolos que cambian al codificar
        os.environ["SDB_PAGE_TOKEN"] = token_especial
        codificado = quote(token_especial, safe="")
        check(codificado not in modulo._redactar(f"redirect?access_token={codificado}"),
              "el valor de un secreto se redacta también ya percent-encoded (quote(v, safe=''))")

        check(modulo._redactar("nada que redactar aquí") == "nada que redactar aquí",
              "un texto sin secretos ni patrones sale igual")
    finally:
        os.environ.clear()
        os.environ.update(entorno_previo)

    print("   · labkit.metricas.registrar: plataforma del run, cotejo de post_id/shortcode y fechas")
    from datetime import datetime, timezone

    run_base = {"run_id": "LAB-UNIT-FACEBOOK", "platform": "facebook",
                "publication": {"post_id": "FBID-BASE", "submitted_at": "2026-09-13T20:00:00+00:00", "snapshots": []}}
    resultado_multi = {
        "run_group_id": "LAB-UNIT-API", "observed_at": "2026-09-14T20:05:00+00:00",
        "results": {
            "facebook": {"status": "verified", "detail": {"id": "FBID-BASE"}, "metrics": {"post_impressions": 10}},
            "instagram": {"status": "verified", "metrics": {"reach": 500}},
        },
    }
    actualizado = ME.registrar(run_base, resultado_multi, run_group="LAB-UNIT-API",
                               instantanea="24h", ahora=datetime(2026, 9, 14, 20, 6, tzinfo=timezone.utc))
    snap = actualizado["publication"]["snapshots"][0]
    check(list(snap["metricas"]) == ["facebook"], f"solo se registra la red del run, no todas las de results ({snap})")
    check(snap["edad_horas"] == 24.08, f"edad_horas calculada desde submitted_at ({snap})")
    check(run_base["publication"]["snapshots"] == [], "registrar no muta el run que recibió")

    run_sin_post_id = {"run_id": "LAB-UNIT-SIN-POST-ID-FACEBOOK", "platform": "facebook",
                       "publication": {"submitted_at": "2026-09-13T20:00:00+00:00", "snapshots": []}}
    resultado_sin_post_id = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                             "results": {"facebook": {"status": "verified", "detail": {"id": "CUALQUIERA"},
                                         "metrics": {"post_impressions": 1}}}}
    try:
        ME.registrar(run_sin_post_id, resultado_sin_post_id, run_group="G", instantanea="24h",
                     ahora=datetime.now(timezone.utc))
        check(False, "debía rechazar un run sin publication.post_id")
    except ME.MetricasError:
        check(True, "un run sin publication.post_id se rechaza: no hay con qué cotejar el resultado")

    run_api_id = {"run_id": "LAB-UNIT-2-FACEBOOK", "platform": "facebook",
                  "publication": {"post_id": "FBID123", "snapshots": []}}
    resultado_id_ok = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                       "results": {"facebook": {"status": "verified", "detail": {"id": "FBID123"}, "metrics": {}}}}
    ME.registrar(run_api_id, resultado_id_ok, run_group="G", instantanea="24h", ahora=datetime.now(timezone.utc))
    resultado_id_mal = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                        "results": {"facebook": {"status": "verified", "detail": {"id": "OTRO_ID"}, "metrics": {}}}}
    try:
        ME.registrar(run_api_id, resultado_id_mal, run_group="G", instantanea="72h", ahora=datetime.now(timezone.utc))
        check(False, "debía rechazar un id de Graph que no es el del run")
    except ME.MetricasError:
        check(True, "un id de Graph que no es el del run se rechaza (ruta API)")

    run_shortcode = {"run_id": "LAB-UNIT-INSTAGRAM", "platform": "instagram",
                     "publication": {"post_id": "DdR54JEgxHN", "snapshots": []}}
    resultado_permalink_ok = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                              "results": {"instagram": {"status": "verified", "graph_media_id": "17999",
                                          "detail": {"id": "17999", "permalink": "https://www.instagram.com/p/DdR54JEgxHN/"},
                                          "metrics": {}}}}
    con_shortcode = ME.registrar(run_shortcode, resultado_permalink_ok, run_group="G", instantanea="24h",
                                 ahora=datetime.now(timezone.utc))
    check(con_shortcode["publication"]["graph_media_id"] == "17999",
          "el post_id del run de teléfono (el shortcode) se coteja contra el permalink, y cuadra")
    resultado_permalink_mal = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                               "results": {"instagram": {"status": "verified",
                                           "detail": {"id": "18000", "permalink": "https://www.instagram.com/p/OTROCODIGO/"},
                                           "metrics": {}}}}
    try:
        ME.registrar(run_shortcode, resultado_permalink_mal, run_group="G", instantanea="72h",
                     ahora=datetime.now(timezone.utc))
        check(False, "debía rechazar un permalink que no lleva el shortcode del run")
    except ME.MetricasError:
        check(True, "un permalink que no lleva el shortcode del run se rechaza (ruta teléfono)")

    resultado_no_verificado = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                              "results": {"facebook": {"status": "failed", "error": "HTTP 400"}}}
    try:
        ME.registrar(run_base, resultado_no_verificado, run_group="G", instantanea="7d", ahora=datetime.now(timezone.utc))
        check(False, "debía rechazar una plataforma que no quedó verified")
    except ME.MetricasError:
        check(True, "una plataforma failed en el resultado no consume la instantánea (código 2, sin escribir)")

    run_fecha_ingenua = {"run_id": "LAB-UNIT-3-FACEBOOK", "platform": "facebook",
                        "publication": {"post_id": "FB-NAIVE", "submitted_at": "2026-09-13T20:00:00",
                                       "snapshots": []}}  # sin zona
    resultado_simple = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                        "results": {"facebook": {"status": "verified", "detail": {"id": "FB-NAIVE"}, "metrics": {}}}}
    try:
        ME.registrar(run_fecha_ingenua, resultado_simple, run_group="G", instantanea="24h", ahora=datetime.now(timezone.utc))
        check(False, "debía rechazar un submitted_at sin zona horaria en vez de reventar con TypeError")
    except ME.MetricasError:
        check(True, "submitted_at sin zona horaria da MetricasError (código 2), no un TypeError sin capturar")

    run_desfase = {"run_id": "LAB-UNIT-4-FACEBOOK", "platform": "facebook",
                   "publication": {"post_id": "FB-DESFASE", "submitted_at": "2026-09-14T00:00:00+05:00",
                                  "snapshots": []}}
    resultado_desfase = {"run_group_id": "G", "observed_at": "2026-09-14T20:05:00+00:00",
                        "results": {"facebook": {"status": "verified", "detail": {"id": "FB-DESFASE"}, "metrics": {}}}}
    snap_desfase = ME.registrar(run_desfase, resultado_desfase, run_group="G", instantanea="24h",
                               ahora=datetime.now(timezone.utc))["publication"]["snapshots"][0]
    # submitted_at es 2026-09-14T00:00+05:00 = 2026-09-13T19:00 UTC; observed_at es
    # 2026-09-14T20:05 UTC: 25 h 5 min de diferencia real, aunque las horas "de reloj"
    # sean distintas.
    check(snap_desfase["edad_horas"] == 25.08,
          f"la edad se calcula en tiempo real, no restando horas de reloj con desfases distintos ({snap_desfase})")

    print("   · manifiesto-verificacion (C-1: un run_group propio por instantánea) y metricas-registrar (lab.py CLI)")
    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d)
        with LabAislado(raiz) as lab:
            base_grupo = "LAB-SEQ-001-API"
            c0, _, _ = lab("manifiesto-verificacion", "--run-group", base_grupo, "--post", "facebook=1")
            c24, _, _ = lab("manifiesto-verificacion", "--run-group", f"{base_grupo}-M24H", "--post", "facebook=1")
            c72, _, _ = lab("manifiesto-verificacion", "--run-group", f"{base_grupo}-M72H", "--post", "facebook=1")
            check((c0, c24, c72) == (0, 0, 0),
                  f"el manifiesto de publicación (7e) y los de 24h/72h (paso 8) no chocan ({c0}, {c24}, {c72})")
            rutas = [raiz / "experiments" / "media-lab" / "manifests" / f"{g}-verify.json"
                     for g in (base_grupo, f"{base_grupo}-M24H", f"{base_grupo}-M72H")]
            check(all(r.is_file() for r in rutas), f"los tres manifiestos quedan como archivos distintos ({rutas})")

    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d)
        (raiz / "runs").mkdir()
        (raiz / "coverage.json").write_text(json.dumps(
            {"cells": [{"cell_id": "CELL-MET", "measurement_completed_at": []},
                       {"cell_id": "CELL-MET3", "measurement_completed_at": []}]}), encoding="utf-8")
        resultado_dir = raiz / "experiments" / "media-lab" / "results" / "999"
        resultado_dir.mkdir(parents=True)

        def escribir_run(run_id, run):
            (raiz / "runs" / f"{run_id}.json").write_text(json.dumps(run), encoding="utf-8")

        def leer_run(run_id):
            return json.loads((raiz / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))

        def escribir_resultado(nombre, resultado):
            ruta = resultado_dir / nombre
            ruta.write_text(json.dumps(resultado), encoding="utf-8")
            return f"experiments/media-lab/results/999/{nombre}"

        run = {"run_id": "LAB-CLI-MET-FACEBOOK", "coverage_cell_id": "CELL-MET", "platform": "facebook",
               "publication": {"post_id": "FB-CLI-BASE", "submitted_at": "2026-09-13T20:00:00+00:00",
                               "snapshots": []}}
        escribir_run("LAB-CLI-MET-FACEBOOK", run)
        resultado_rel = escribir_resultado("verification-result.json", {
            "run_group_id": "LAB-CLI-MET-API", "observed_at": "2026-09-14T20:05:00+00:00",
            "results": {
                "facebook": {"status": "verified", "detail": {"id": "FB-CLI-BASE"}, "metrics": {"post_impressions": 10}},
                "instagram": {"status": "verified", "metrics": {"reach": 999}},
            }})

        with LabAislado(raiz) as lab:
            base = ("metricas-registrar", "--run", "LAB-CLI-MET-FACEBOOK", "--run-group", "LAB-CLI-MET-API",
                    "--resultado", resultado_rel, "--instantanea", "24h")
            codigo, datos, _ = lab(*base)
            run_tras = leer_run("LAB-CLI-MET-FACEBOOK")
            cobertura_tras = json.loads((raiz / "coverage.json").read_text(encoding="utf-8"))
            check(codigo == 0, f"metricas-registrar ok sale con 0 ({codigo}, {datos})")
            check(run_tras["publication"]["snapshots"] ==
                  [{"instantanea": "24h", "observed_at": "2026-09-14T20:05:00+00:00", "edad_horas": 24.08,
                    "metricas": {"facebook": {"post_impressions": 10}}, "errores": {}}],
                  f"la instantánea queda en el run con su edad, solo con la red del run ({run_tras['publication']['snapshots']})")
            check(cobertura_tras["cells"][0]["measurement_completed_at"] == ["2026-09-14T20:05:00+00:00"],
                  f"coverage.json marca la celda del run ({cobertura_tras})")

            codigo, datos, _ = lab(*base)
            check(codigo == 2, f"la misma instantánea otra vez sale con 2 ({codigo}, {datos})")

            codigo, datos, _ = lab("metricas-registrar", "--run", "LAB-CLI-MET-FACEBOOK",
                                   "--run-group", "LAB-OTRO-GRUPO-API", "--resultado", resultado_rel,
                                   "--instantanea", "72h")
            check(codigo == 2, f"un run_group que no es el del resultado sale con 2 ({codigo}, {datos})")

            codigo, datos, _ = lab("metricas-registrar", "--run", "LAB-CLI-MET-FACEBOOK",
                                   "--run-group", "LAB-CLI-MET-API",
                                   "--resultado", "experiments/media-lab/results/999/no-existe.json",
                                   "--instantanea", "72h")
            check(codigo == 2, f"un resultado que no existe sale con 2 ({codigo}, {datos})")

            # I-2: la red del run no quedó verified en el resultado -> 2, sin consumir la instantánea.
            run2 = {"run_id": "LAB-CLI-MET2-FACEBOOK", "coverage_cell_id": "CELL-MET", "platform": "facebook",
                    "publication": {"submitted_at": "2026-09-13T20:00:00+00:00", "snapshots": []}}
            escribir_run("LAB-CLI-MET2-FACEBOOK", run2)
            resultado_fallido_rel = escribir_resultado("fallido.json", {
                "run_group_id": "LAB-CLI-MET2-API", "observed_at": "2026-09-14T20:05:00+00:00",
                "results": {"facebook": {"status": "failed", "error": "HTTP 400"}}})
            codigo, datos, _ = lab("metricas-registrar", "--run", "LAB-CLI-MET2-FACEBOOK",
                                   "--run-group", "LAB-CLI-MET2-API", "--resultado", resultado_fallido_rel,
                                   "--instantanea", "24h")
            check(codigo == 2 and leer_run("LAB-CLI-MET2-FACEBOOK") == run2,
                  f"facebook failed en el resultado: 2 y el run queda intacto ({codigo}, {datos})")

            # I-1: post_id del run (ruta API) que no corresponde al del resultado -> 2, run intacto.
            run3 = {"run_id": "LAB-CLI-MET3-FACEBOOK", "coverage_cell_id": "CELL-MET", "platform": "facebook",
                    "publication": {"post_id": "FBID-DEL-RUN", "submitted_at": "2026-09-13T20:00:00+00:00",
                                    "snapshots": []}}
            escribir_run("LAB-CLI-MET3-FACEBOOK", run3)
            resultado_otro_post_rel = escribir_resultado("otro-post.json", {
                "run_group_id": "LAB-CLI-MET3-API", "observed_at": "2026-09-14T20:05:00+00:00",
                "results": {"facebook": {"status": "verified", "detail": {"id": "FBID-DE-OTRO-POST"}, "metrics": {}}}})
            codigo, datos, _ = lab("metricas-registrar", "--run", "LAB-CLI-MET3-FACEBOOK",
                                   "--run-group", "LAB-CLI-MET3-API", "--resultado", resultado_otro_post_rel,
                                   "--instantanea", "24h")
            check(codigo == 2 and leer_run("LAB-CLI-MET3-FACEBOOK") == run3,
                  f"el post_id del run no es el del resultado: 2 y el run queda intacto ({codigo}, {datos})")

            # I-3: coverage.json no tiene la celda del run -> 2, ni el run ni coverage.json se tocan.
            run4 = {"run_id": "LAB-CLI-MET4-FACEBOOK", "coverage_cell_id": "CELL-NOPE", "platform": "facebook",
                    "publication": {"post_id": "FB-CLI-MET4", "submitted_at": "2026-09-13T20:00:00+00:00",
                                    "snapshots": []}}
            escribir_run("LAB-CLI-MET4-FACEBOOK", run4)
            resultado_run4_rel = escribir_resultado("run4.json", {
                "run_group_id": "LAB-CLI-MET4-API", "observed_at": "2026-09-14T20:05:00+00:00",
                "results": {"facebook": {"status": "verified", "detail": {"id": "FB-CLI-MET4"}, "metrics": {}}}})
            cobertura_antes = json.loads((raiz / "coverage.json").read_text(encoding="utf-8"))
            codigo, datos, _ = lab("metricas-registrar", "--run", "LAB-CLI-MET4-FACEBOOK",
                                   "--run-group", "LAB-CLI-MET4-API", "--resultado", resultado_run4_rel,
                                   "--instantanea", "24h")
            cobertura_despues = json.loads((raiz / "coverage.json").read_text(encoding="utf-8"))
            check(codigo == 2 and leer_run("LAB-CLI-MET4-FACEBOOK") == run4 and cobertura_despues == cobertura_antes,
                  f"celda inexistente en coverage.json: 2, sin tocar ni el run ni coverage.json ({codigo}, {datos})")

    texto_workflow = (ROOT / ".github" / "workflows" / "media-lab-verify.yml").read_text(encoding="utf-8")
    check("metricas:" in texto_workflow, "media-lab-verify.yml admite el input metricas")
    check("SDB_IG_USER_ID" in texto_workflow, "media-lab-verify.yml expone SDB_IG_USER_ID")
    check("permissions" in texto_workflow and "contents: read" in texto_workflow,
          "media-lab-verify.yml mantiene permissions: contents: read")
    check("upload-artifact" in texto_workflow, "media-lab-verify.yml sigue subiendo el artefacto de verificación")
    check("manifest con .." in texto_workflow, "media-lab-verify.yml valida que --manifest no lleve ..")
    check("manifest fuera de manifests/" in texto_workflow,
          "media-lab-verify.yml exige que --manifest esté bajo experiments/media-lab/manifests/")
    check("run-name:" in texto_workflow and "inputs.manifest" in texto_workflow,
          "media-lab-verify.yml identifica el run por la ruta del manifiesto (run-name), no por la hora")

    texto_publish = (ROOT / ".github" / "workflows" / "media-lab.yml").read_text(encoding="utf-8")
    check("run-name:" in texto_publish and "inputs.manifest" in texto_publish,
          "media-lab.yml también identifica el run por la ruta del manifiesto (run-name)")
    check("media-lab-result-" in texto_publish, "media-lab.yml sube el artefacto media-lab-result-<id>")
    check("live-result.json" in texto_publish, "media-lab.yml escribe live-result.json")


def seccion_pantalla_comun() -> None:
    print("\n12. Fase 2: lectura común de pantallas y reloj")
    import time
    from labkit import instagram_pantallas as IP, pantalla as P, reloj

    check(P.PantallaInesperada is IP.PantallaInesperada, "PantallaInesperada es la misma clase en pantalla e instagram_pantallas")
    check(IP._elegir is P.elegir and IP.evaluar_envio is P.evaluar_envio and IP.CLASES_CAMPO == P.CLASES_CAMPO,
          "instagram_pantallas reexporta elegir, evaluar_envio y CLASES_CAMPO de pantalla")

    alto_2340 = jerarquia(nodo_xml("[0,0][1080,300]", texto="Créer"), nodo_xml("[0,301][1080,400]", texto="Bajo"),
                          nodo_xml("[0,1900][1080,2000]", texto="Profil"), nodo_xml("[0,1899][1080,1950]", texto="Alto"))
    check(P.alto_volcado(alto_2340) == 2340, "el alto del volcado sale del nodo raíz")
    arriba = [n["texto"] for n in P.coincidencias(alto_2340, PAQUETE_IG, "arriba")]
    abajo = [n["texto"] for n in P.coincidencias(alto_2340, PAQUETE_IG, "abajo")]
    check("Créer" in arriba and "Bajo" not in arriba, f"sobre 2340 px «arriba» sigue siendo y2 ≤ 300 ({arriba})")
    check("Profil" in abajo and "Alto" not in abajo, f"sobre 2340 px «abajo» sigue siendo y1 ≥ 1900 ({abajo})")

    alto_2316 = jerarquia(nodo_xml("[0,0][1080,296]", texto="Créer"), nodo_xml("[0,0][1080,297]", texto="Justo"),
                          nodo_xml("[0,1881][1080,1990]", texto="Profil"), nodo_xml("[0,1880][1080,1990]", texto="Casi"),
                          alto=2316)
    arriba = [n["texto"] for n in P.coincidencias(alto_2316, PAQUETE_IG, "arriba")]
    abajo = [n["texto"] for n in P.coincidencias(alto_2316, PAQUETE_IG, "abajo")]
    check(P.alto_volcado(alto_2316) == 2316 and arriba == ["Créer"] and abajo == ["Profil"],
          f"sobre 2316 px las zonas escalan (arriba ≤ 296,9; abajo ≥ 1880,5): {arriba}, {abajo}")
    try:
        P.coincidencias(alto_2340, PAQUETE_IG, "centro")
        ok = False
    except ValueError:
        ok = True
    check(ok, "una zona desconocida es ValueError")

    # Un volcado de una ventana emergente enfocable tiene la emergente como raíz, con un origen
    # que no es (0, 0): alto_volcado no debe escalar las zonas con ese alto encogido (fallaría
    # abierto: un nodo intermedio contaría como «abajo»).
    emergente_xml = ('<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?>'
                     '<hierarchy rotation="0">'
                     + nodo_xml("[517,553][1080,1052]", clase="android.widget.FrameLayout",
                                hijos=nodo_xml("[562,966][725,1015]", texto="Dentro"))
                     + '</hierarchy>')
    check(P.alto_volcado(emergente_xml) == P.ALTO_REFERENCIA,
          "una raíz que no empieza en el origen (ventana emergente) no cuenta: alto de referencia")
    abajo_emergente = [n["texto"] for n in P.coincidencias(emergente_xml, PAQUETE_IG, "abajo")]
    check("Dentro" not in abajo_emergente,
          f"con el alto de referencia, y1=966 no llega a «abajo» (≥1900): {abajo_emergente}")
    check(P.volcado_de_emergente(emergente_xml) and not P.volcado_de_emergente(alto_2316),
          "volcado_de_emergente distingue la raíz de una emergente de la del árbol completo")

    # Una raíz en el origen no basta: si no ocupa todo el ancho de la pantalla (aquí, un
    # contenedor de 600 px) no es la pantalla completa, así que tampoco debe escalar «abajo».
    raiz_estrecha = ('<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?>'
                     '<hierarchy rotation="0">'
                     + nodo_xml("[0,0][600,700]", clase="android.widget.FrameLayout",
                                hijos=nodo_xml("[50,600][550,650]", texto="HijoBajo"))
                     + '</hierarchy>')
    check(P.alto_volcado(raiz_estrecha) == P.ALTO_REFERENCIA,
          "una raíz en el origen más estrecha que la pantalla no cuenta como completa")
    abajo_estrecha = [n["texto"] for n in P.coincidencias(raiz_estrecha, PAQUETE_IG, "abajo")]
    check("HijoBajo" not in abajo_estrecha,
          f"con el alto de referencia, y1=600 no llega a «abajo» (≥1900): {abajo_estrecha}")

    # Ninguna raíz de profundidad 0 cumple las dos condiciones (ancho completo y más alta que
    # LIMITE_ABAJO_PX): ni la del origen (demasiado baja) ni la otra (no está en el origen).
    dos_raices = ('<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?>'
                 '<hierarchy rotation="0">'
                 + nodo_xml("[0,0][1080,500]", clase="android.widget.FrameLayout")
                 + nodo_xml("[50,50][600,600]", clase="android.widget.FrameLayout")
                 + '</hierarchy>')
    check(P.alto_volcado(dos_raices) == P.ALTO_REFERENCIA,
          "ninguna raíz de profundidad 0 es de ancho completo y más alta que LIMITE_ABAJO_PX")

    comp = xml_compositor()
    check(P.pulsable(comp, etiqueta="Partager", paquete=PAQUETE_IG) and IP.partager_pulsable(comp),
          "pulsable generaliza partager_pulsable (etiqueta dentro de un botón clickable)")
    check(not P.pulsable(comp, etiqueta="Partager", paquete="com.facebook.katana"), "pulsable exige el paquete")
    check(P.hay_desplegable(xml_compositor(despues=LISTA_HASHTAGS), PAQUETE_IG)
          and not P.hay_desplegable(xml_compositor(despues=LISTA_HASHTAGS), PAQUETE_IG, prefijo="@"),
          "hay_desplegable mira el prefijo pedido fuera del campo de texto")
    check(P.tiene_texto(comp, texto=PIE_PRUEBA, paquete=PAQUETE_IG) and not P.tiene_texto(comp, texto="otro", paquete=PAQUETE_IG),
          "tiene_texto compara el text exacto (no content-desc) dentro del paquete")
    check(P.nodo(comp, PAQUETE_IG, texto="Nouvelle publication")["texto"] == "Nouvelle publication",
          "nodo devuelve el control del paquete")
    try:
        P.nodo(comp, PAQUETE_IG, texto="No existe")
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "nodo sin coincidencias lanza PantallaInesperada")
    try:
        P.elegir([], "algo")
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "elegir sin coincidencias lanza PantallaInesperada, no IndexError")

    ancha = {"nombre": "PopupWindow:a", "frame": (0, 1448, 1080, 2205), "ancho_padre": 1080}
    estrecha = {"nombre": "PopupWindow:b", "frame": (400, 100, 500, 180), "ancho_padre": 1080}
    sin_frame = {"nombre": "PopupWindow:c", "frame": None, "ancho_padre": None}
    check(IP.parece_desplegable is P.parece_desplegable and IP.describe_emergente is P.describe_emergente,
          "instagram_pantallas reexporta parece_desplegable y describe_emergente de pantalla")
    boton = (45, 2081, 1035, 2205)
    check(P.emergente_solapada([estrecha, ancha], [boton]) is ancha and P.emergente_solapada([estrecha], [boton]) is None
          and P.emergente_solapada([estrecha], []) is estrecha and P.emergente_solapada([sin_frame], [boton]) is sin_frame
          and P.emergente_solapada([], [boton]) is None,
          "emergente_solapada: solape vertical con las referencias; sin referencias o sin frame cuenta (falla cerrado)")
    check(P.parece_desplegable(ancha) and not P.parece_desplegable(estrecha) and P.parece_desplegable(sin_frame)
          and "PopupWindow:a" in P.describe_emergente(ancha),
          "parece_desplegable mide el ancho y describe_emergente nombra la ventana")

    dormidos: list = []
    sleep_original, monotonic_original = time.sleep, time.monotonic
    try:
        time.sleep = dormidos.append
        time.monotonic = lambda: 42.0
        reloj.dormir(3)
        check(dormidos == [3] and reloj.monotonic() == 42.0,
              "reloj llama a time en cada uso (las sustituciones de la fase 1 siguen valiendo)")
    finally:
        time.sleep, time.monotonic = sleep_original, monotonic_original


def seccion_pasos_comunes() -> None:
    print("\n13. Fase 2: pasos comunes del teléfono")
    from labkit import instagram_feed as IG, pantalla as P, pasos, reloj, telefono as T

    check(IG.BorradorPendiente is pasos.BorradorPendiente and IG.TelefonoNoListo is pasos.TelefonoNoListo,
          "instagram_feed reexporta las excepciones de pasos")
    check(IG.ATRAS == pasos.ATRAS and IG.CTRL_IZQ == pasos.CTRL_IZQ and IG.TECLA_A == pasos.TECLA_A
          and IG.ESTABILIZACION_TIMEOUT_S == pasos.ESTABILIZACION_TIMEOUT_S,
          "(M-1) instagram_feed reexporta las constantes de pasos que usa o que leen las pruebas de la fase 1")
    check(not hasattr(IG, "VOLCADOS_LIMPIOS_TRAS_PEGAR") and not hasattr(IG, "INTENTOS_ATRAS_PIE"),
          "(M-1) instagram_feed ya no expone los alias muertos de volcados limpios/intentos de «atrás»")
    evid = pathlib.Path("evidencia-simulada")
    PAQ_FB = "com.facebook.katana"
    TEXTO_FB = "Hola desde Facebook"
    lectura_profil = lambda x: (T.buscar(x, texto="Profil") or {}).get("bounds")  # noqa: E731
    uno = jerarquia(nodo_xml("[864,2200][1080,2340]", desc="Profil"))
    otro = jerarquia(nodo_xml("[0,2200][216,2340]", desc="Profil"))

    sim = TelefonoSimulado([uno, otro, otro, otro])
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_estable(lectura_profil))
    check(err is None and res[1] == (0, 2200, 216, 2340) and sim.volcados_leidos == 4,
          f"esperar_estable devuelve la lectura tras 3 volcados seguidos iguales ({err!r}, {sim.volcados_leidos})")

    sim = TelefonoSimulado([uno, otro] * 40)
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_estable(lectura_profil))
    check(isinstance(err, pasos.PantallaInesperada) and str(pasos.ESTABILIZACION_TIMEOUT_S) in str(err),
          f"una lectura que nunca se estabiliza agota el plazo ({err!r})")

    sim = TelefonoSimulado([uno, otro, otro])
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_estable(lectura_profil, n=2))
    check(err is None and res[1] == (0, 2200, 216, 2340) and sim.volcados_leidos == 3,
          f"(M-1) esperar_estable con n=2 se conforma con 2 volcados seguidos, no 3 ({err!r}, {sim.volcados_leidos})")

    th = jerarquia(nodo_xml("[0,0][1080,200]", texto="Fils", paquete="com.instagram.barcelona"))
    sim = TelefonoSimulado([th])
    res, err = con_telefono_simulado(sim, lambda: pasos.atras("com.instagram.barcelona", evid, "salida-1"))
    check(err is None and sim.teclas == [pasos.ATRAS] and sim.capturas == ["salida-1.png"],
          f"atras pulsa con la app pedida delante ({err!r}, {sim.teclas})")
    sim = TelefonoSimulado([th])
    res, err = con_telefono_simulado(sim, lambda: pasos.atras(PAQ_FB, evid, "salida-1"))
    check(isinstance(err, pasos.PantallaInesperada) and sim.teclas == [], "atras no pulsa con otra app delante")

    boton = {"centro": (540, 2140), "bounds": (45, 2081, 1035, 2205)}
    aviso = jerarquia(nodo_xml("[0,250][1080,330]", texto="ENVIANDO", paquete=PAQ_FB))
    limpio = jerarquia(nodo_xml("[0,250][1080,330]", texto="Inicio", paquete=PAQ_FB))

    def observador(xml):
        return {"valido": True, "compositor": False, "banner": T.buscar(xml, texto="ENVIANDO") is not None,
                "fallo": False}

    sim = TelefonoSimulado([aviso, limpio, limpio])
    res, err = con_telefono_simulado(sim, lambda: pasos.observar_envio(boton, observador, 90))
    check(err is None and res == ("confirmado", None) and sim.toques == [boton["centro"]],
          f"(M-6) observar_envio devuelve (estado, culpable) en vez de escribirlo en un dict compartido "
          f"({err!r}, {res})")

    def observador_fallo(xml):
        return {"valido": True, "compositor": False, "banner": False, "fallo": True,
                "fallo_texto": "Réessayer", "fallo_bounds": (0, 0, 10, 10)}

    sim = TelefonoSimulado([limpio])
    res, err = con_telefono_simulado(sim, lambda: pasos.observar_envio(boton, observador_fallo, 90))
    check(err is None and res[0] == "fallido" and res[1] is not None and res[1]["fallo_texto"] == "Réessayer",
          f"observar_envio también devuelve la observación culpable cuando falla ({err!r}, {res})")

    resultado_compartido: dict = {}
    sim = TelefonoSimulado([aviso, limpio, limpio])
    con_telefono_simulado(sim, lambda: pasos.observar_envio(boton, observador, 90, resultado_compartido))
    check(bool(resultado_compartido.get("submitted_at")) and bool(resultado_compartido.get("processing_completed_at"))
          and "estado" not in resultado_compartido and "fallo" not in resultado_compartido,
          f"observar_envio solo añade los dos timestamps al `resultado` compartido, no estado ni fallo "
          f"({resultado_compartido})")

    sim = TelefonoSimulado([aviso, limpio, limpio])
    res, err = con_telefono_simulado(sim, lambda: pasos.observar_envio(boton, observador, 0))
    check(err is None and res == ("timeout", None),
          f"(M-1) plazo=0 no da tiempo a observar nada: timeout, no confirmado ({err!r}, {res})")

    sim = TelefonoSimulado([limpio], falla_tocar=T.TelefonoError("device offline"))
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="fb-antes.png", captura_final="fb-final.png", captura_error="fb-error.png",
        listo=lambda x, e: [], botones=lambda x: [dict(boton, texto="Publicar", desc="", clickable=True)],
        observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(err is None and res["estado"] == "error_tras_pulsar" and len(sim.toques) == 1
          and sim.capturas == ["fb-antes.png", "fb-error.png"] and sim.plazos_captura[-1] == pasos.CAPTURA_ERROR_S,
          f"enviar: si el toque falla, error_tras_pulsar con captura corta y nada se propaga ({err!r}, {res})")

    sim = TelefonoSimulado([limpio], listo=False)
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: [], botones=lambda x: [],
        observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(isinstance(err, pasos.TelefonoNoListo) and sim.toques == [] and sim.capturas == [],
          "enviar con el teléfono no listo no captura ni toca")

    sim = TelefonoSimulado([limpio], emergentes=(T.TelefonoError("dumpsys no responde"),))
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: [], botones=lambda x: [],
        observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(isinstance(err, T.TelefonoError) and sim.toques == [],
          "enviar: si ventanas_emergentes falla, falla cerrado sin tocar")
    vistas: list = []
    emergente_fb = [{"nombre": "PopupWindow:sug", "frame": (0, 900, 1080, 1500), "ancho_padre": 1080}]
    sim = TelefonoSimulado([limpio], emergentes=(emergente_fb,))
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: vistas.append(e) or (["emergente"] if e else []),
        botones=lambda x: [], observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(isinstance(err, pasos.PantallaInesperada) and vistas == [emergente_fb] and sim.toques == [],
          "enviar pasa a listo las ventanas emergentes del paquete y no pulsa si hay problemas")

    # --- M-5: `extra` no puede redefinir claves propias del resultado --------------------------
    sim = TelefonoSimulado([limpio])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: [], botones=lambda x: [], observador_nuevo=lambda b: observador,
        despues=lambda r, e: e, extra={"estado": "ya puesto"}))
    check(isinstance(err, ValueError) and "estado" in str(err) and sim.toques == [],
          f"(M-5) enviar rechaza un extra que redefine claves propias, antes de tocar nada ({err!r})")

    # --- I-1 y M-2/M-3: la puerta de toque único de `enviar`, con otro paquete cualquiera -------
    def xml_fb(*, mencion=False, boton_bounds="[800,2100][1000,2200]"):
        hijos = [nodo_xml("[45,300][1035,700]", texto=TEXTO_FB, clase="android.widget.EditText", paquete=PAQ_FB),
                 nodo_xml(boton_bounds, texto="Publicar", paquete=PAQ_FB, extra='clickable="true"')]
        if mencion:
            hijos.append(nodo_xml("[0,900][1080,1000]", texto="@alguien", paquete=PAQ_FB))
        return jerarquia(*hijos)

    def xml_fb_dos_botones():
        return jerarquia(
            nodo_xml("[45,300][1035,700]", texto=TEXTO_FB, clase="android.widget.EditText", paquete=PAQ_FB),
            nodo_xml("[100,2100][400,2200]", texto="Publicar", paquete=PAQ_FB, extra='clickable="true"'),
            nodo_xml("[600,2100][900,2200]", texto="Publicar", paquete=PAQ_FB, extra='clickable="true"'))

    botones_fb = lambda x: T.buscar_todos(x, texto="Publicar", paquete=PAQ_FB)  # noqa: E731

    def _listo_2a_falla():
        llamadas: list = []

        def listo(xml, emergentes):
            llamadas.append(xml)
            return [] if len(llamadas) == 1 else ["problema en el 2.º volcado"]
        return listo

    sim = TelefonoSimulado([xml_fb(), xml_fb()])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=_listo_2a_falla(), botones=botones_fb, observador_nuevo=lambda b: observador,
        despues=lambda r, e: e))
    check(isinstance(err, pasos.PantallaInesperada) and "2.º volcado" in str(err) and sim.toques == [],
          f"(I-1a) el 2.º volcado con problemas para sin tocar ({err!r})")

    sim = TelefonoSimulado([xml_fb(), xml_fb(boton_bounds="[800,2050][1000,2150]")])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: [], botones=botones_fb, observador_nuevo=lambda b: observador,
        despues=lambda r, e: e))
    check(isinstance(err, pasos.PantallaInesperada) and "se ha movido entre volcados" in str(err) and sim.toques == [],
          f"(I-1b) «Publicar» movido entre volcados para sin tocar ({err!r})")

    sim = TelefonoSimulado([xml_fb_dos_botones(), xml_fb_dos_botones()])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: [], botones=botones_fb, observador_nuevo=lambda b: observador,
        despues=lambda r, e: e))
    check(isinstance(err, pasos.PantallaInesperada) and "ambiguo" in str(err) and sim.toques == [],
          f"(I-1c) dos «Publicar» sin relación entre sí es ambiguo y no toca ({err!r})")

    sim = TelefonoSimulado([xml_fb(), xml_fb(), aviso, limpio, limpio])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="fb-antes.png", captura_final="fb-final.png", captura_error="fb-error.png",
        listo=lambda x, e: [], botones=botones_fb, observador_nuevo=lambda b: observador,
        despues=lambda r, e: f"hecho:{e}", extra={"canal": "feed"}))
    check(err is None and len(sim.toques) == 1 and res["estado"] == "hecho:confirmado"
          and res["captura"] == "evidencia-simulada/fb-final.png" and res["canal"] == "feed",
          f"(I-1d) camino feliz genérico: un toque, `despues` decide el estado final y `extra` llega "
          f"al resultado ({err!r}, {res})")

    def despues_lanza(resultado, estado):
        raise RuntimeError("fallo al leer tras compartir")

    sim = TelefonoSimulado([xml_fb(), xml_fb(), aviso, limpio, limpio])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="fb-antes.png", captura_final="fb-final.png", captura_error="fb-error.png",
        listo=lambda x, e: [], botones=botones_fb, observador_nuevo=lambda b: observador, despues=despues_lanza))
    check(err is None and res["estado"] == "error_tras_pulsar" and len(sim.toques) == 1
          and res["captura_error"] == "evidencia-simulada/fb-error.png" and res["captura"] is None,
          f"(I-1e) `despues` lanza tras el toque: error_tras_pulsar con la captura de error ({err!r}, {res})")

    def observador_nuevo_falla(boton):
        raise RuntimeError("no se pudo preparar el observador")

    sim = TelefonoSimulado([xml_fb(), xml_fb()])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: [], botones=botones_fb, observador_nuevo=observador_nuevo_falla,
        despues=lambda r, e: e))
    check(isinstance(err, RuntimeError) and not isinstance(err, pasos.PantallaInesperada) and sim.toques == [],
          f"(M-2) observador_nuevo que falla antes del toque se propaga y no cuenta como error_tras_pulsar "
          f"({err!r})")

    def observador_nuevo_desconecta(boton):
        sim.listo = False
        return observador

    sim = TelefonoSimulado([xml_fb(), xml_fb()])
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete=PAQ_FB, nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        captura_antes="a.png", captura_final="b.png", captura_error="c.png",
        listo=lambda x, e: [], botones=botones_fb, observador_nuevo=observador_nuevo_desconecta,
        despues=lambda r, e: e))
    check(isinstance(err, pasos.TelefonoNoListo) and sim.toques == [],
          f"(M-3) el teléfono deja de estar listo justo antes de tocar: TelefonoNoListo sin tocar ({err!r})")

    # --- I-2 y M-4/M-7: `escribir_texto` fuera de Instagram (otro campo, otro desplegable) ------
    def campo_fb(xml):
        return T.buscar(xml, clase="android.widget.EditText", paquete=PAQ_FB)

    def exigir_fb(xml):
        if T.buscar(xml, texto="Publicar", paquete=PAQ_FB) is None:
            raise pasos.PantallaInesperada("falta «Publicar»")

    def desplegable_fb(xml):
        return P.hay_desplegable(xml, PAQ_FB, prefijo="@")

    def emergente_fb(xml, emergentes):
        return P.emergente_solapada(emergentes, [n["bounds"] for n in T.buscar_todos(xml, texto="Publicar",
                                                                                      paquete=PAQ_FB)])

    sim = TelefonoSimulado([xml_fb(), xml_fb(mencion=True), xml_fb(mencion=True), xml_fb(), xml_fb()],
                           teclado=(False,), emergentes=((),))
    res, err = con_telefono_simulado(sim, lambda: pasos.escribir_texto(
        TEXTO_FB, PAQ_FB, campo=campo_fb, exigir=exigir_fb, desplegable_nodos=desplegable_fb,
        emergente=emergente_fb))
    check(err is None and sim.teclas == [pasos.ATRAS],
          f"(I-2a) un desplegable por nodos (no de Instagram) cuesta un «atrás» y reinicia los limpios "
          f"({err!r}, {sim.teclas})")

    estrecha = {"nombre": "PopupWindow:x", "frame": (400, 2100, 500, 2180), "ancho_padre": 1080}
    sim = TelefonoSimulado([xml_fb(), xml_fb()], teclado=(False,), emergentes=((estrecha,),))
    res, err = con_telefono_simulado(sim, lambda: pasos.escribir_texto(
        TEXTO_FB, PAQ_FB, campo=campo_fb, exigir=exigir_fb, desplegable_nodos=desplegable_fb,
        emergente=emergente_fb))
    check(isinstance(err, pasos.PantallaInesperada) and "no parece un desplegable" in str(err) and sim.teclas == [],
          f"(I-2b) una emergente estrecha para con PantallaInesperada sin pulsar «atrás» ({err!r})")

    xml_otro_paquete = jerarquia(
        nodo_xml("[45,300][1035,700]", texto="", clase="android.widget.EditText", paquete=PAQ_FB),
        nodo_xml("[45,300][1035,700]", texto=TEXTO_FB, clase="android.widget.EditText", paquete="com.other.app"))
    sim = TelefonoSimulado([xml_otro_paquete], teclado=(False,), emergentes=((),))
    res, err = con_telefono_simulado(sim, lambda: pasos.escribir_texto(
        TEXTO_FB, PAQ_FB, campo=campo_fb, exigir=exigir_fb, desplegable_nodos=desplegable_fb,
        emergente=emergente_fb))
    check(isinstance(err, pasos.PantallaInesperada) and PAQ_FB in str(err) and "no coincide" in str(err),
          f"(I-2c) el texto solo bajo otro paquete falla la relectura ({err!r})")

    xml_sin_campo = jerarquia(nodo_xml("[0,0][10,10]", texto="nada", paquete=PAQ_FB))
    sim = TelefonoSimulado([xml_sin_campo])
    res, err = con_telefono_simulado(sim, lambda: pasos.escribir_texto(
        TEXTO_FB, PAQ_FB, campo=campo_fb, exigir=exigir_fb, desplegable_nodos=desplegable_fb,
        emergente=emergente_fb))
    check(isinstance(err, pasos.PantallaInesperada) and f"el campo de texto de {PAQ_FB}" in str(err),
          f"(M-4) el mensaje de campo ausente nombra el paquete ({err!r})")

    sim = TelefonoSimulado([xml_fb()], teclado=(False,), emergentes=((),))
    res, err = con_telefono_simulado(sim, lambda: pasos.escribir_texto(
        TEXTO_FB, PAQ_FB, campo=campo_fb, exigir=exigir_fb, desplegable_nodos=desplegable_fb,
        emergente=emergente_fb, volcados_limpios=1))
    check(err is None and sim.volcados_leidos == 2,
          f"(M-1) volcados_limpios=1 se conforma con un único volcado limpio ({err!r}, {sim.volcados_leidos})")

    sim = TelefonoSimulado([xml_fb()], teclado=(False,), emergentes=((),))
    res, err = con_telefono_simulado(sim, lambda: pasos.escribir_texto(
        TEXTO_FB, PAQ_FB, campo=campo_fb, exigir=exigir_fb, desplegable_nodos=desplegable_fb,
        emergente=emergente_fb))
    check(err is None and sim.volcados_leidos == 4,
          f"(M-1) por defecto (volcados_limpios=3) hacen falta más volcados limpios seguidos "
          f"({err!r}, {sim.volcados_leidos})")

    check(reloj.dormir.__name__ == "dormir" and reloj.monotonic.__name__ == "monotonic",
          "con_telefono_simulado restaura el reloj")


XML_BOTON_ENVIO_CON_ICONO = jerarquia(
    nodo_xml("[45,2081][1035,2205]", clase="android.widget.Button", extra='clickable="true"',
             hijos=nodo_xml("[60,2100][120,2180]", desc="Icône", clase="android.widget.ImageView")
             + nodo_xml("[480,2115][600,2170]", texto="Partager")),
    nodo_xml("[847,92][1080,249]", texto="Suivant", extra='clickable="true"'))


def toques_sobre_envio(sim, paquete: str) -> list:
    """Toques del simulador que cayeron dentro de un control de envío (`textos.es_texto_envio` en texto, descripción
    o id) de `paquete` en el volcado que había en pantalla al tocar (`sim.toques_en`)."""
    from labkit import telefono, textos
    return [(x, y) for x, y, xml in sim.toques_en
            if isinstance(xml, str) and any(
                n["package"] == paquete
                and any(textos.es_texto_envio(v) for v in (n["texto"], n["desc"], n["resource_id"]))
                and n["bounds"][0] <= x < n["bounds"][2] and n["bounds"][1] <= y < n["bounds"][3]
                for n in telefono.nodos(xml))]


def lanza(fn, exc: type[BaseException] = Exception) -> bool:
    """`fn()` lanza `exc` (o una subclase) y nada más: para los bloques try/ok repetidos de las
    pruebas que solo comprueban que una llamada falla con el tipo de error esperado."""
    try:
        fn()
    except exc:
        return True
    return False


def seccion_textos_y_descarte() -> None:
    print("\n14. Fase 2: textos, pista de idioma, envío prohibido y descarte")
    from labkit import pantalla as P, pasos, telefono as T, textos as TX

    check(set(TX.APPS_TELEFONO) <= set(TX.PAQUETES) and all(a in TX.TEXTOS for a in TX.APPS_TELEFONO),
          "cada app de teléfono tiene paquete y tabla de textos")
    check(TX.texto("instagram", "perfil") == "Profil" and TX.texto("facebook", "publico") == "Público",
          "texto(app, clave) devuelve el texto exacto")
    for valor in ("Partager", "publier", " Publicar ", "Compartir historia", "Post", "Share",
                  "com.instagram.barcelona:id/new_thread_screen_post_button"):
        check(TX.es_texto_envio(valor), f"es de envío: {valor!r}")
    for valor in ("Vos stories", "Votre story", "Amis proches", "Envoyer à", "Tu historia", "Compartir en tu historia",
                  "Your story", "Close friends"):
        check(TX.es_texto_envio(valor), f"C1: publica una Story, cuenta como envío: {valor!r}")
    for valor in ("Suivant", "Siguiente", "Compartir en Instagram", ""):
        check(not TX.es_texto_envio(valor), f"no es de envío: {valor!r}")
    for valor in ("Partager maintenant", "Publier le fil", "Compartir ahora mismo", "Share now", "Envoyer", "Ajouter à votre story"):
        check(TX.es_texto_envio(valor), f"I-5: por prefijo, es de envío: {valor!r}")
    for valor in ("Partager à", "partager  sur Facebook", "Compartir en Instagram"):
        check(not TX.es_texto_envio(valor), f"I-5: excepción explícita NO_ENVIO, no es de envío: {valor!r}")
    no_envio, no_envio_norm = TX.NO_ENVIO, TX._NO_ENVIO_NORM
    try:
        TX.NO_ENVIO = no_envio | {"partager", "vos stories", "publier le fil"}
        TX._NO_ENVIO_NORM = frozenset(map(TX.normalizar, TX.NO_ENVIO))  # NO_ENVIO se lee ya normalizado
        exactos = TX.es_texto_envio("Partager") and TX.es_texto_envio("Vos stories")
        prefijo_exceptuado = not TX.es_texto_envio("Publier le fil")
    finally:
        TX.NO_ENVIO, TX._NO_ENVIO_NORM = no_envio, no_envio_norm
    check(exactos and prefijo_exceptuado,
          "I-5: NO_ENVIO solo exceptúa de la regla de prefijos; nunca anula un envío exacto de ENVIO o ENVIO_HISTORIA")
    try:
        TX.NO_ENVIO = no_envio - {"compartir en instagram"}
        TX._NO_ENVIO_NORM = frozenset(map(TX.normalizar, TX.NO_ENVIO))
        vuelve_a_bloquear = TX.es_texto_envio("Compartir en Instagram")
    finally:
        TX.NO_ENVIO, TX._NO_ENVIO_NORM = no_envio, no_envio_norm
    check(vuelve_a_bloquear,
          "quitar una excepción de NO_ENVIO (y su versión normalizada) vuelve a bloquear: confirma que "
          "es_texto_envio lee la global _NO_ENVIO_NORM en cada llamada, no un valor capturado una sola vez")
    check(TX._ENVIO_NORM == frozenset(map(TX.normalizar, TX.ENVIO))
          and TX._NO_TOCAR_NORM == frozenset(map(TX.normalizar, TX.NO_TOCAR))
          and TX._NO_ENVIO_NORM == frozenset(map(TX.normalizar, TX.NO_ENVIO))
          and TX._TITULOS_BORRADO_NORM == frozenset(map(TX.normalizar_titulo, TX.TITULOS_BORRADO))
          and TX._DESCARTE_TITULOS_NORM == {app: frozenset(map(TX.normalizar_titulo, tabla["titulos"]))
                                            for app, tabla in TX.DESCARTE.items()},
          "invariante: las constantes _..._NORM precalculadas coinciden con normalizar/normalizar_titulo "
          "aplicado a sus fuentes (ENVIO, NO_TOCAR, NO_ENVIO, TITULOS_BORRADO, DESCARTE)")
    check(TX.permitido("Profil", "instagram")
          and TX.permitido("Sélectionné Miniature de la photo du 14 septembre 2026 10:39", "instagram")
          and TX.permitido("#citasdiarias", "instagram") and TX.permitido("3 min", "instagram")
          and not TX.permitido("Hola Juan, ¿quedamos mañana?", "instagram"),
          "permitido acepta textos de la tabla, marca y patrones, y rechaza texto personal")
    check(TX.permitido("sabiduriabolsillo", "instagram") and TX.permitido("Photo de profil de sabiduriabolsillo", "instagram")
          and not TX.permitido("Juan ha comentado la foto de sabiduriabolsillo", "instagram")
          and not TX.permitido("Mensaje de Juan para Sabiduria De Bolsillo", "facebook"),
          "I4: la marca sola y sus formatos concretos se permiten; una frase personal que la menciona, no")

    ingles = (xml_perfil().replace('"Profil"', '"Profile"').replace("Modifier le profil", "Edit profile")
              .replace('"Créer"', '"Create"').replace("publications", "posts"))
    check("idioma" in P.pista_idioma(ingles, "instagram") and P.pista_idioma(xml_perfil(), "instagram") == "",
          "un perfil de Instagram en inglés da pista de idioma; en francés no")
    check(P.pista_idioma(ingles, "facebook") == "", "sin nodos de la app no hay pista")
    xml_edits = jerarquia(nodo_xml("[0,0][200,100]", texto="Anything", paquete="com.instagram.basel"))
    check(P.pista_idioma(xml_edits, "edits") == "",
          "menor 6: sin tabla de textos en textos.TEXTOS (p. ej. edits) no hay pista falsa, aunque tenga nodos propios")
    sim = TelefonoSimulado([ingles])
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_que(
        lambda x: T.buscar(x, texto="Profil") is not None, "Profil", app="instagram"))
    check(isinstance(err, P.PantallaInesperada) and "idioma" in str(err) and sim.toques == [],
          f"volcado en inglés: esperar_que falla cerrado con un mensaje de idioma ({err!r})")

    for criterio, label in (({"texto": "Partager"}, "la etiqueta de envío"),
                            ({"desc": "Icône"}, "un icono dentro del botón de envío")):
        check(lanza(lambda criterio=criterio: P.nodo_sonda(XML_BOTON_ENVIO_CON_ICONO, PAQUETE_IG, **criterio),
                    P.PantallaInesperada),
              f"nodo_sonda se niega a devolver {label}")
    check(P.nodo_sonda(XML_BOTON_ENVIO_CON_ICONO, PAQUETE_IG, texto="Suivant")["centro"] == (963, 170),
          "nodo_sonda devuelve un nodo único que no es de envío")
    th_publicar = jerarquia(nodo_xml("[800,100][1000,200]", desc="", clase="android.widget.Button",
                                     paquete="com.instagram.barcelona",
                                     extra='clickable="true" resource-id="com.instagram.barcelona:id/new_thread_screen_post_button"'))
    check(lanza(lambda: P.nodo_sonda(th_publicar, "com.instagram.barcelona",
                                     resource_id="new_thread_screen_post_button"), P.PantallaInesperada),
          "nodo_sonda se niega a devolver el botón de publicar de Threads por resource-id")

    icono = T.buscar(XML_BOTON_ENVIO_CON_ICONO, texto="Icône")
    sim = TelefonoSimulado([XML_BOTON_ENVIO_CON_ICONO])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(icono, XML_BOTON_ENVIO_CON_ICONO))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C1: pasos.tocar no pulsa un icono dentro del botón de envío")
    historia = jerarquia(nodo_xml("[40,600][300,860]", desc="Votre story", clase="android.widget.ImageView", extra='clickable="true"'))
    avatar = T.buscar(historia, texto="Votre story")
    sim = TelefonoSimulado([historia])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(avatar, historia))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C1: «Votre story» es envío si no está en la lista blanca")
    sim = TelefonoSimulado([historia])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(avatar, historia, permitir=("Votre story",)))
    check(err is None and sim.toques == [(170, 730)], "C1: con la lista blanca explícita, pasos.tocar abre el visor propio")
    tapado_envio = jerarquia(nodo_xml("[0,500][1080,1000]", texto="Vos stories", clase="android.widget.Button", extra='clickable="true"'),
                             nodo_xml("[40,600][300,860]", desc="Votre story", clase="android.widget.ImageView", extra='clickable="true"'))
    avatar_tapado = T.buscar(tapado_envio, texto="Votre story")
    sim = TelefonoSimulado([tapado_envio])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(avatar_tapado, tapado_envio, permitir=("Votre story",)))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
          "permitir solo ignora «Votre story»: si su centro cae dentro de «Vos stories», no se toca")
    solapado = jerarquia(nodo_xml("[0,2000][1080,2200]", texto="Vos stories", clase="android.widget.Button", extra='clickable="true"'),
                         nodo_xml("[500,2050][600,2150]", desc="Flèche", clase="android.widget.ImageView"))
    flecha = T.buscar(solapado, texto="Flèche")
    check(P.es_envio(solapado, flecha), "C1: un nodo cuyo centro cae dentro de «Vos stories» cuenta como envío")
    check(lanza(lambda: P.nodo_sonda(solapado, PAQUETE_IG, texto="Vos stories"), P.PantallaInesperada),
          "C1: nodo_sonda se niega a devolver «Vos stories»")

    dialogo = jerarquia(nodo_xml("[100,900][980,1000]", texto="Recommencer ?"),
                        nodo_xml("[100,1100][980,1200]", texto="Recommencer", clase="android.widget.Button",
                                 extra='clickable="true"'),
                        nodo_xml("[100,1250][980,1350]", texto="Annuler", clase="android.widget.Button",
                                 extra='clickable="true"'))
    check(P.boton_descarte(dialogo, "instagram")["texto"] == "Recommencer", "boton_descarte lee el diálogo exacto")
    evid = pathlib.Path("evidencia-simulada")
    sim = TelefonoSimulado([dialogo])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(err is None and sim.toques == [(540, 1150)] and sim.capturas == ["descarte.png"],
          f"descartar pulsa solo el botón del diálogo y captura ({err!r}, {sim.toques})")
    sim = TelefonoSimulado([xml_compositor()])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "sin diálogo de descarte no se pulsa nada")
    borrar_th = jerarquia(nodo_xml("[100,900][980,1000]", texto="Supprimer le fil ?", paquete="com.instagram.barcelona"),
                          nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button",
                                   paquete="com.instagram.barcelona", extra='clickable="true"'))
    sim = TelefonoSimulado([borrar_th])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("threads", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "I1: «Supprimer le fil ?» es un borrado: telefono-descartar no pulsa")
    borrar_ig = jerarquia(nodo_xml("[100,800][980,880]", texto="Recommencer ?"),
                          nodo_xml("[100,900][980,1000]", texto="Supprimer la publication ?"),
                          nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button", extra='clickable="true"'))
    sim = TelefonoSimulado([borrar_ig])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and "borrado" in str(err) and sim.toques == [],
          "I1: un título de borrado hace fallar cerrado aunque el diálogo tenga también un título de descarte")

    # --- Revisión de especificación (B1-B3, I1-I3): huecos de seguridad encontrados tras el commit 1f51ed1 ---

    # B1: un nodo pulsable SIN etiqueta propia de envío pero que CONTIENE un descendiente de envío cuenta
    # como envío para cualquier toque cuyo centro caiga dentro de sus bounds, aunque el nodo tocado sea de
    # otra rama del árbol (no descendiente ni antecesor del contenedor).
    otra_rama = jerarquia(
        nodo_xml("[0,2000][1080,2200]", clase="android.widget.Button", extra='clickable="true"',
                 hijos=nodo_xml("[480,2080][600,2120]", texto="Partager")),
        nodo_xml("[500,1980][580,2040]", texto="Suivant", clase="android.widget.Button", extra='clickable="true"'))
    otro_nodo = T.buscar(otra_rama, texto="Suivant")
    check(otro_nodo["centro"] == (540, 2010), f"B1: el nodo de prueba tiene el centro exacto del caso ({otro_nodo['centro']})")
    sim = TelefonoSimulado([otra_rama])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(otro_nodo, otra_rama))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
          f"B1: un nodo de otra rama cuyo centro cae dentro de un contenedor con un descendiente de envío es envío ({err!r})")

    # B2: `permitir` solo salta el CAMPO cuyo valor coincide, no el nodo entero.
    b2_texto_y_desc = jerarquia(nodo_xml("[40,600][300,860]", texto="Partager", desc="Votre story",
                                         clase="android.widget.ImageView", extra='clickable="true"'))
    n_b2a = T.buscar(b2_texto_y_desc, texto="Partager")
    sim = TelefonoSimulado([b2_texto_y_desc])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(n_b2a, b2_texto_y_desc, permitir=("Votre story",)))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
          "B2: permitir solo exime el campo desc; el texto «Partager» del mismo nodo sigue siendo envío")

    b2_desc_y_rid = jerarquia(nodo_xml(
        "[40,600][300,860]", desc="Votre story", clase="android.widget.ImageView",
        extra='clickable="true" resource-id="com.instagram.barcelona:id/new_thread_screen_post_button"'))
    n_b2b = T.buscar(b2_desc_y_rid, texto="Votre story")
    sim = TelefonoSimulado([b2_desc_y_rid])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(n_b2b, b2_desc_y_rid, permitir=("Votre story",)))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
          "B2: permitir solo exime el campo desc; el resource-id de publicar del mismo nodo sigue siendo envío")

    b2_solo_desc = jerarquia(nodo_xml("[40,600][300,860]", desc="Votre story", clase="android.widget.ImageView",
                                      extra='clickable="true"'))
    n_b2c = T.buscar(b2_solo_desc, texto="Votre story")
    sim = TelefonoSimulado([b2_solo_desc])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(n_b2c, b2_solo_desc, permitir=("Votre story",)))
    check(err is None and sim.toques == [(170, 730)],
          "B2: con permitir y solo el campo permitido en el nodo, sigue sin ser envío (caso legítimo del visor)")

    # B3: `boton_descarte` normaliza antes de comparar con TITULOS_BORRADO (NBSP o espacio fino antes del
    # «?» no deben colar un borrado como si fuera un descarte) y mira borrado en cualquier paquete.
    borrado_nbsp = jerarquia(
        nodo_xml("[100,800][980,880]", texto="Recommencer ?"),
        nodo_xml("[100,900][980,1000]", texto="Supprimer la publication ?"),
        nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button", extra='clickable="true"'))
    sim = TelefonoSimulado([borrado_nbsp])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and "borrado" in str(err) and sim.toques == [],
          "B3: un NBSP antes del «?» en el título de borrado se sigue detectando (no se pulsa)")
    borrado_espacio_fino = jerarquia(
        nodo_xml("[100,800][980,880]", texto="Recommencer ?"),
        nodo_xml("[100,900][980,1000]", texto="Supprimer la publication ?"),
        nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button", extra='clickable="true"'))
    sim = TelefonoSimulado([borrado_espacio_fino])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and "borrado" in str(err) and sim.toques == [],
          "B3: un espacio fino antes del «?» en el título de borrado se sigue detectando (no se pulsa)")
    borrado_otro_paquete = jerarquia(
        nodo_xml("[100,800][980,880]", texto="Recommencer ?"),
        nodo_xml("[100,900][980,1000]", texto="Supprimer la publication ?", paquete="com.android.systemui"),
        nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button", extra='clickable="true"'))
    sim = TelefonoSimulado([borrado_otro_paquete])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and "borrado" in str(err) and sim.toques == [],
          "B3: un título de borrado bajo otro paquete también hace fallar cerrado")

    # I1: ENVIO_HISTORIA también cuenta por prefijo (contador o coma añadidos al mismo control).
    for valor in ("Votre story, 2 nouvelles", "Amis proches (12)", "Tu historia · alguien"):
        check(TX.es_texto_envio(valor), f"I1: ENVIO_HISTORIA por prefijo con separador, es de envío: {valor!r}")
    for valor in ("Votre storyX", "Amis prochesX"):
        check(not TX.es_texto_envio(valor), f"I1: sin separador tras el prefijo, no cuenta como envío: {valor!r}")

    # I2: una normalización común (NFKC, sin Cf, espacios colapsados, casefold) usada por es_texto_envio.
    check(TX.es_texto_envio("​Partager"), "I2: un cero-ancho delante no esconde un envío exacto")
    check(TX.normalizar("  Partager ") == "partager", f"I2: normalizar colapsa y quita NBSP ({TX.normalizar('  Partager ')!r})")

    # I3: la regla del centro de es_envio no filtra por paquete: un envío de OTRO paquete que contiene el
    # centro del toque también cuenta (falla cerrado).
    otro_paquete_envio = jerarquia(
        nodo_xml("[0,2000][1080,2200]", texto="Vos stories", clase="android.widget.Button",
                 paquete="com.instagram.barcelona", extra='clickable="true"'),
        nodo_xml("[500,2050][600,2150]", desc="Flèche", clase="android.widget.ImageView", paquete=PAQUETE_IG))
    flecha_otro_paquete = T.buscar(otro_paquete_envio, texto="Flèche")
    check(P.es_envio(otro_paquete_envio, flecha_otro_paquete),
          "I3: un control de envío de otro paquete que contiene el centro del toque también cuenta")

    # --- Re-revisión de 95a421c: R1 (bloqueante), I-a e I-b ---

    # R1: un nodo de envío NO pulsable, sin antecesor pulsable en su propia rama, cuyas bounds contienen
    # el centro de un toque en OTRO nodo pulsable de otra rama («Photo») también debe bloquear.
    sonda_photo_partager = jerarquia(
        nodo_xml("[0,1960][1080,2060]", desc="Photo", clase="android.widget.ImageView", extra='clickable="true"'),
        nodo_xml("[0,2000][1080,2200]", texto="Partager", clase="android.widget.TextView"))
    photo = T.buscar(sonda_photo_partager, texto="Photo")
    check(photo["centro"][1] == 2010 and 2000 <= photo["centro"][1] < 2200,
          f"R1: el centro de «Photo» cae dentro de las bounds de «Partager» ({photo['centro']})")
    check(P.es_envio(sonda_photo_partager, photo),
          "R1: «Partager» no pulsable sin antecesor pulsable, con el centro de «Photo» dentro de sus bounds, bloquea")
    sim = TelefonoSimulado([sonda_photo_partager])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(photo, sonda_photo_partager))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
          f"R1: pasos.tocar tampoco pulsa «Photo» por el «Partager» no pulsable que solapa su centro ({err!r})")

    sonda_photo_publicar_fb = jerarquia(
        nodo_xml("[0,1960][1080,2060]", desc="Photo", clase="android.widget.ImageView", extra='clickable="true"',
                 paquete="com.facebook.katana"),
        nodo_xml("[0,2000][1080,2200]", desc="Publicar", clase="android.widget.TextView", paquete="com.facebook.katana"))
    photo_fb = T.buscar(sonda_photo_publicar_fb, texto="Photo")
    check(P.es_envio(sonda_photo_publicar_fb, photo_fb),
          "R1: lo mismo con desc=«Publicar» de Facebook, no pulsable, bloquea el toque de «Photo»")

    # I-a: `ignorar`/`permitir` compara con la misma regla de prefijo que ENVIO_HISTORIA (I1), no exacto:
    # `permitir=("Tu historia",)` exime también `desc="Tu historia, No vista"` (fb-launch.xml real).
    no_vista = jerarquia(nodo_xml("[40,600][300,860]", desc="Tu historia, No vista",
                                  clase="android.widget.ImageView", extra='clickable="true"',
                                  paquete="com.facebook.katana"))
    n_no_vista = T.buscar(no_vista, texto="Tu historia")
    check(n_no_vista is None, "sanity: buscar exacto no encuentra «Tu historia, No vista»")
    n_no_vista = T.buscar(no_vista, contiene="Tu historia")
    sim = TelefonoSimulado([no_vista])
    res, err = con_telefono_simulado(
        sim, lambda: pasos.tocar(n_no_vista, no_vista, permitir=("Tu historia",)))
    check(err is None and sim.toques == [(170, 730)],
          f"I-a: permitir=(«Tu historia»,) exime «Tu historia, No vista» por prefijo con separador ({err!r})")
    sim = TelefonoSimulado([no_vista])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(n_no_vista, no_vista))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
          "I-a: sin permitir, «Tu historia, No vista» sigue siendo envío (por prefijo, I1)")

    # I-b: NO_TOCAR compara con `textos.normalizar`: mayúsculas, espacios de más y un carácter invisible
    # delante tampoco deben esquivar el bloqueo de «Anular».
    for variante in ("ANULAR", "Anular ", "​Anular"):
        anular = jerarquia(nodo_xml("[400,2000][680,2100]", texto=variante, clase="android.widget.Button",
                                    extra='clickable="true"'))
        n_anular = T.buscar(anular, contiene="nular") or T.buscar(anular, texto=variante)
        sim = TelefonoSimulado([anular])
        res, err = con_telefono_simulado(sim, lambda: pasos.tocar(n_anular, anular))
        check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
              f"I-b: {variante!r} normalizado sigue bloqueando como NO_TOCAR ({err!r})")

    # Menor 1: los títulos de borrado se detectan aunque cambien las comillas o lleven un espacio
    # antes del «?»; «Recommencer ?» sigue siendo un descarte legítimo (no un borrado).
    for titulo_borrado in ("Supprimer la publication?", "Supprimer la « publication » ?", 'Delete "post"?',
                           "Supprimer la ＂publication＂ ?", "Supprimer la ＇publication＇ ?"):
        borrado_variante = jerarquia(
            nodo_xml("[100,800][980,880]", texto="Recommencer ?"),
            nodo_xml("[100,900][980,1000]", texto=titulo_borrado),
            nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button", extra='clickable="true"'))
        sim = TelefonoSimulado([borrado_variante])
        res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
        check(isinstance(err, P.PantallaInesperada) and "borrado" in str(err) and sim.toques == [],
              f"menor 1: {titulo_borrado!r} se detecta como borrado pese a comillas o espacio distintos ({err!r})")
    descarte_mayus = jerarquia(
        nodo_xml("[100,900][980,1000]", texto="RECOMMENCER ?"),
        nodo_xml("[100,1100][980,1200]", texto="Recommencer", clase="android.widget.Button", extra='clickable="true"'))
    sim = TelefonoSimulado([descarte_mayus])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(err is None and sim.toques == [(540, 1150)],
          f"menor 1: «RECOMMENCER ?» en mayúsculas sigue siendo un descarte legítimo ({err!r})")

    # Menor 2: un contenedor pulsable de pantalla completa sin etiqueta propia que envuelve un
    # «Partager» bloquea cualquier toque dentro (falla cerrado a propósito).
    xml_pantalla_completa = jerarquia(
        nodo_xml("[0,0][1080,2340]", clase="android.widget.Button", extra='clickable="true"',
                 hijos=nodo_xml("[480,2080][600,2120]", texto="Partager") + nodo_xml("[10,10][60,60]", texto="Lejos")))
    lejos = T.buscar(xml_pantalla_completa, texto="Lejos")
    check(P.es_envio(xml_pantalla_completa, lejos),
          "menor 2: un contenedor pulsable de pantalla completa con un «Partager» dentro bloquea cualquier toque, aunque esté lejos (falla cerrado)")

    # Importante 1: `permitir`/`ignorar` como `str` se rechaza (cada carácter contaría como candidato).
    check(lanza(lambda: TX.coincide_o_prefijo("Votre story", "Votre story"), TypeError),
          "importante 1: textos.coincide_o_prefijo rechaza candidatos como str")
    votre_story = jerarquia(nodo_xml("[40,600][300,860]", desc="Votre story", clase="android.widget.ImageView",
                                     extra='clickable="true"'))
    n_votre_story = T.buscar(votre_story, texto="Votre story")
    sim = TelefonoSimulado([votre_story])
    res, err = con_telefono_simulado(
        sim, lambda: pasos.tocar(n_votre_story, votre_story, permitir="Votre story"))
    check(isinstance(err, TypeError) and sim.toques == [],
          f"importante 1: pasos.tocar(..., permitir='Votre story') lanza TypeError y no toca nada ({err!r})")


_SIN_RECETA = object()


@contextlib.contextmanager
def receta_temporal(par: tuple[str, str], receta: dict):
    """`receta` como borrador de `par` en `recetas.TODAS` y `recetas.BORRADORES` mientras dura el
    bloque; al salir RESTAURA lo que hubiera en cada diccionario (o su ausencia), en vez de hacer pop.
    Lanza `ValueError` con un par promovido."""
    from labkit import recetas as RC
    if par in RC.PROMOVIDAS:
        raise ValueError("receta_temporal es solo para borradores")
    registros = (RC.TODAS, RC.BORRADORES)
    previos = [d.get(par, _SIN_RECETA) for d in registros]
    try:
        for d in registros:
            d[par] = receta
        yield receta
    finally:
        for d, previo in zip(registros, previos):
            if previo is _SIN_RECETA:
                d.pop(par, None)
            else:
                d[par] = previo


def seccion_recetas_y_seleccion() -> None:
    print("\n15. Fase 2: recetas y selección (un teléfono por ventana, copias, borradores)")
    import argparse
    from labkit import recetas as RC, seleccion as S, textos as TX

    check(S.TELEFONO_FASE_1 == S.TELEFONO_IMPLEMENTADO == frozenset(RC.RECETAS),
          "TELEFONO_FASE_1 es alias de TELEFONO_IMPLEMENTADO, que sale de RECETAS")
    check(("instagram", "feed_single_image") in S.TELEFONO_IMPLEMENTADO, "el feed de Instagram sigue implementado")
    verificacion_ig = RC.TODAS[("instagram", "feed_single_image")]["verificacion"]
    check("menú" not in verificacion_ig and "missing_data_reasons.post_url" in verificacion_ig,
          "la receta del feed de Instagram no promete la URL desde el menú del teléfono: va a missing_data_reasons.post_url")
    check(set(RC.PROMOVIDAS) <= set(RC.TODAS) and not set(RC.RECETAS) & set(RC.BORRADORES)
          and set(RC.RECETAS) | set(RC.BORRADORES) == set(RC.TODAS),
          "PROMOVIDAS está en TODAS y RECETAS/BORRADORES la reparten")
    for par, receta in RC.TODAS.items():
        check(all(k in receta for k in RC.CLAVES) and receta["publicar"] and receta["estados_ok"] == ["confirmado"],
              f"{par}: receta con todas sus claves, un paso de publicar y solo confirmado sale con 0")
        check(isinstance(receta.get("copias"), list)
              and all(isinstance(cp, dict) and set(cp) == {"red", "superficie", "nota"}
                      and cp["red"] in set(TX.APPS_TELEFONO) for cp in receta["copias"]),
              f"{par}: cada copia nombra una red conocida con superficie y nota")

    ap = modulo_lab().construir()
    subcomandos = next(a for a in ap._actions if isinstance(a, argparse._SubParsersAction)).choices
    for par, receta in RC.TODAS.items():
        check(receta["subcomando"] in subcomandos, f"{par}: el subcomando {receta['subcomando']} existe en lab.construir()")
        for fase in RC.FASES:
            for c in receta[fase]:
                sub = subcomandos.get(c["args"][0])
                paso = next((x for x in sub._actions if x.dest == "paso"), None) if sub else None
                check(sub is not None and (paso is None or c["args"][1] in paso.choices),
                      f"{par}/{fase}: «{' '.join(c['args'][:2])}» existe en lab.py")
    linea = RC.renderizar(RC.para("instagram", "feed_single_image"))["preparar"][1]["linea"]
    check(linea.startswith(".venv/bin/python experiments/media-lab/lab.py ig abrir --run <run>"),
          f"renderizar da la línea lista para ejecutar ({linea})")
    render = RC.renderizar(RC.para("instagram", "feed_single_image"))
    render["copias"][0]["red"] = "mutada"
    render["formato_encargo"]["ancho"] = 1
    render["preparar"][0]["args"][0] = "mutado"
    render["preparar"][0]["anota"].append("mutado")
    original = RC.TODAS[("instagram", "feed_single_image")]
    check(original["copias"][0]["red"] == "facebook" and original["formato_encargo"]["ancho"] == 1080
          and original["preparar"][0]["args"][0] == "telefono-subir" and original["preparar"][0]["anota"] == ["subido_en"]
          and "linea" not in original["preparar"][0],
          "mutar el resultado de renderizar no cambia RC.TODAS")
    try:
        RC.para("threads", "feed_video")
        ok = False
    except RC.RecetaNoDisponible:
        ok = True
    check(ok, "para() rechaza un par sin receta promovida")

    def celda(cid, plataforma, formato, ruta):
        return {"cell_id": cid, "platform": plataforma, "native_format": formato,
                "publishing_route": ruta, "status": "planned"}

    ig_tel = celda("A", "instagram", "feed_single_image", "android_native")
    th_tel = celda("B", "threads", "feed_video", "android_native")
    ig_api = celda("C", "instagram", "feed_single_image", "api")
    check(not S.compatibles(ig_tel, th_tel) and not S.compatibles(th_tel, ig_tel),
          "nunca dos celdas android_native en la misma ventana")
    check(S.compatibles(th_tel, ig_api), "sin copias declaradas, Threads por teléfono e Instagram por API son compatibles")
    par_th = ("threads", "feed_video")
    with receta_temporal(par_th, {**RC.TODAS[("instagram", "feed_single_image")],
                                  "copias": [{"red": "instagram", "superficie": "feed", "nota": "prueba"}]}):
        check(not S.compatibles(th_tel, ig_api) and not S.compatibles(ig_api, th_tel),
              "una copia declarada en la receta excluye esa red en la misma ventana")
        check(S._ruta_implementada(th_tel, borradores=True) and not S._ruta_implementada(th_tel),
              "un borrador solo cuenta como implementado con borradores=True")
        check(S.elegir([th_tel], [{"estado": "aprobado", "coverage_cell_ids": ["B"]}]) == [],
              "seleccionar nunca elige una celda de un borrador")
    check(par_th not in RC.TODAS and par_th not in RC.BORRADORES, "receta_temporal quita al salir un par que no existía")
    sin_copias = {k: v for k, v in RC.TODAS[("instagram", "feed_single_image")].items() if k != "copias"}
    with receta_temporal(par_th, sin_copias):
        check(lanza(lambda: S.compatibles(th_tel, ig_api), KeyError),
              "una receta sin clave copias falla visible en vez de quitar la exclusión en silencio")
    receta_a = {**RC.TODAS[("instagram", "feed_single_image")], "nota_prueba": "a"}
    receta_b = {**RC.TODAS[("instagram", "feed_single_image")], "nota_prueba": "b"}
    with receta_temporal(par_th, receta_a):
        with receta_temporal(par_th, receta_b):
            pass
        check(RC.TODAS[par_th] is receta_a and RC.BORRADORES[par_th] is receta_a,
              "receta_temporal restaura el valor previo en TODAS y en BORRADORES")
    par_ig = ("instagram", "feed_single_image")
    original_ig = RC.TODAS[par_ig]
    check(lanza(lambda: receta_temporal(par_ig, sin_copias).__enter__(), ValueError)
          and RC.TODAS[par_ig] is original_ig and par_ig not in RC.BORRADORES,
          "receta_temporal rechaza con ValueError un par promovido y no toca RC.TODAS")


def rechazo(res, fragmento: str, tipo: str = "ArgumentoNoValido") -> bool:
    """`res` = (código, datos, stderr) de lab.py: salió con 2, con `tipo` y un error que contiene `fragmento`."""
    if res is None:
        return False
    codigo, datos, _ = res
    return codigo == 2 and campo(datos, "tipo") == tipo and fragmento in str(campo(datos, "error") or "")


CELDAS_FASE2 = [
    {"cell_id": "C-IG-TEL", "platform": "instagram", "native_format": "feed_single_image",
     "publishing_route": "android_native", "status": "planned"},
    {"cell_id": "C-TH-TEL", "platform": "threads", "native_format": "feed_video",
     "publishing_route": "android_native", "status": "planned"},
    {"cell_id": "C-FB-API", "platform": "facebook", "native_format": "feed_single_image",
     "publishing_route": "api", "status": "planned"},
]


def entorno_lab_fase2():
    """Context manager: lab.py en proceso sobre una carpeta temporal con CELDAS_FASE2."""
    import json
    import tempfile

    @contextlib.contextmanager
    def gestor():
        with tempfile.TemporaryDirectory() as d:
            raiz = pathlib.Path(d)
            (raiz / "encargos").mkdir()
            (raiz / "coverage.json").write_text(json.dumps({"cells": CELDAS_FASE2}), encoding="utf-8")
            (raiz / "prompt.txt").write_text("Un astrolabio de latón", encoding="utf-8")
            with LabAislado(raiz) as lab:
                yield lab, raiz
    return gestor()


def seccion_cli_fase2() -> None:
    print("\n16. Fase 2: lab.py receta, atrás por app, descarte y borradores")
    from labkit import pantalla, pasos, recetas as RC, telefono

    recibido: dict = {}
    atras_original, descartar_original = pasos.atras, pasos.descartar
    captura_original = telefono.captura
    par_th = ("threads", "feed_video")
    try:
        pasos.atras = lambda paquete, ev, nombre: recibido.update(atras=paquete) or ev / f"{nombre}.png"
        pasos.descartar = lambda app, ev, nombre: recibido.update(descartar=app) or ev / f"{nombre}.png"
        with entorno_lab_fase2() as (lab, raiz):
            codigo, datos, _ = lab("receta", "--celda", "C-IG-TEL")
            preparar = campo(datos, "preparar") or []
            check(codigo == 0 and campo(datos, "red") == "instagram" and campo(datos, "borrador") is False
                  and preparar and preparar[0]["args"][0] == "telefono-subir"
                  and "linea" in preparar[0] and campo(datos, "celda") == "C-IG-TEL"
                  and campo(datos, "formato") == "feed_single_image",
                  f"receta de una celda de teléfono implementada, pasada por renderizar ({codigo}, {datos and list(datos)})")
            codigo, datos, _ = lab("receta", "--celda", "C-FB-API")
            check(rechazo((codigo, datos, _), "solo de teléfono"), f"receta rechaza una celda de API ({codigo}, {datos})")
            codigo, datos, _ = lab("receta", "--celda", "C-TH-TEL")
            check(rechazo((codigo, datos, _), "no está implementado"),
                  f"receta rechaza un par sin receta ({codigo}, {datos})")
            codigo, datos, _ = lab("receta", "--celda", "C-NADA")
            check(rechazo((codigo, datos, _), "no está en coverage.json"), "receta rechaza una celda que no existe")

            recibido.clear()
            codigo, datos, _ = lab("telefono-atras", "--app", "threads", "--run", "RUN-1", "--nombre", "salida-1")
            check(codigo == 0 and recibido.get("atras") == "com.instagram.barcelona"
                  and str(campo(datos, "captura")).endswith("RUN-1/salida-1.png"),
                  f"telefono-atras --app threads usa el paquete de Threads ({codigo}, {recibido})")
            check(rechazo(lab("telefono-atras", "--app", "tiktok", "--run", "RUN-1", "--nombre", "s"), "--app"),
                  "telefono-atras rechaza una app sin flujo")
            recibido.clear()
            codigo, datos, _ = lab("telefono-descartar", "--app", "facebook", "--run", "RUN-1", "--nombre", "descarte")
            check(codigo == 0 and recibido.get("descartar") == "facebook",
                  f"telefono-descartar pasa la app a pasos.descartar ({codigo}, {recibido})")
            check(rechazo(lab("telefono-descartar", "--run", "RUN-1", "--nombre", "descarte"), "--app"),
                  "telefono-descartar exige --app")

            recibido.clear()
            codigo, datos, _ = lab("telefono-atras", "--run", "RUN-1", "--nombre", "salida-ig")
            check(codigo == 0 and recibido.get("atras") == "com.instagram.android"
                  and str(campo(datos, "captura")).endswith("RUN-1/salida-ig.png"),
                  f"telefono-atras sin --app (forma de la ventana) pasa el paquete de Instagram a pasos.atras ({codigo}, {recibido})")
            recibido.clear()
            codigo, datos, _ = lab("telefono-atras", "--app", "instagram", "--run", "RUN-1", "--nombre", "salida-ig2")
            check(codigo == 0 and recibido.get("atras") == "com.instagram.android"
                  and str(campo(datos, "captura")).endswith("RUN-1/salida-ig2.png"),
                  f"telefono-atras --app instagram pasa el paquete de Instagram a pasos.atras ({codigo}, {recibido})")

            def descarte_inesperado(app, ev, nombre):
                raise pantalla.PantallaInesperada("prueba")

            descartar_doble = pasos.descartar
            pasos.descartar = descarte_inesperado
            telefono.captura = lambda destino: destino
            codigo, datos, _ = lab("telefono-descartar", "--app", "instagram", "--run", "RUN-1", "--nombre", "descarte")
            check(codigo == 4 and campo(datos, "tipo") == "PantallaInesperada"
                  and str(campo(datos, "captura")).endswith("RUN-1/descarte-inesperada.png"),
                  f"telefono-descartar ante una pantalla inesperada sale con 4 y su captura ({codigo}, {datos})")
            pasos.descartar = descartar_doble
            telefono.captura = captura_original

            nuevo = ("encargo-nuevo", "--cell", "C-TH-TEL", "--family", "LAB-CLI-002", "--brief", "b.md",
                     "--formato", '{"ancho":1080,"alto":1350}', "--prompt-file", raiz / "prompt.txt")
            codigo, datos, _ = lab(*nuevo)
            check(rechazo((codigo, datos, _), "no está implementado"),
                  f"encargo-nuevo rechaza una celda de teléfono sin receta ({codigo})")
            with receta_temporal(par_th, RC.TODAS[("instagram", "feed_single_image")]):
                check(rechazo(lab(*nuevo), "no está implementado"),
                      "encargo-nuevo sin --borrador rechaza una celda de un borrador")
                codigo, datos, _ = lab(*nuevo, "--borrador")
                check(codigo == 0 and campo(datos, "coverage_cell_ids") == ["C-TH-TEL"],
                      f"encargo-nuevo --borrador acepta una celda de un borrador ({codigo}, {datos})")
                codigo, datos, _ = lab("receta", "--celda", "C-TH-TEL", "--borrador")
                check(codigo == 0 and campo(datos, "borrador") is True, f"receta --borrador marca el borrador ({codigo})")
                check(rechazo(lab("receta", "--celda", "C-TH-TEL"), "--borrador"),
                      "sin --borrador la receta de un borrador no sale")
    finally:
        pasos.atras, pasos.descartar = atras_original, descartar_original
        telefono.captura = captura_original


def seccion_sonda_y_fixtures() -> None:
    print("\n17. Fase 2: sondas supervisadas y fixtures podados")
    from labkit import fixtures as FX, telefono as T, textos as TX

    crudo = jerarquia(
        nodo_xml("[0,0][1080,100]", texto="12:04", paquete="com.android.systemui"),
        nodo_xml("[0,200][1080,300]", texto="Profil", desc="Profil"),
        nodo_xml("[0,400][1080,500]", texto="Hola Juan, ¿quedamos mañana?", extra='hint="Écrivez à Juan"'),
        nodo_xml("[0,600][540,900]", desc="Sélectionné Miniature de la photo du 14 septembre 2026 10:39"),
        nodo_xml("[0,1000][1080,1100]", texto="#citasdiarias"))
    podado = FX.podar(crudo, "instagram")
    pares = [(n["texto"], n["desc"]) for n in T.nodos(podado)]
    check(all(n["package"] == PAQUETE_IG for n in T.nodos(podado)), "podar quita los nodos de com.android.systemui")
    check(("Profil", "Profil") in pares and ("#citasdiarias", "") in pares
          and ("", "Sélectionné Miniature de la photo du 14 septembre 2026 10:39") in pares,
          f"podar conserva textos de la tabla, hashtags y fechas de miniatura ({pares})")
    check("Juan" not in podado and "quedamos" not in podado, "podar vacía el texto y el hint personales")
    check(FX.revisar(podado, "instagram") == [] and FX.revisar(crudo, "instagram"),
          "revisar da limpio lo podado y señala lo crudo")

    base = ROOT / "tests" / "fixtures" / "telefono"
    for ruta in sorted(base.glob("*/*.xml")):
        app = ruta.parent.name
        problemas = (FX.revisar(ruta.read_text(encoding="utf-8"), app) if app in TX.APPS_TELEFONO
                     else [f"carpeta de app desconocida: {app}"])
        check(not problemas, f"{ruta.relative_to(ROOT)} está podado y sin com.android.systemui ({problemas[:3]})")

    with entorno_lab_fase2() as (lab, raiz):
        supervisada = ("--run", "SONDA-F2-T", "--nombre", "a", "--supervisada")
        # LabAislado redirige EVIDENCIA a raiz/evidence; en el repo real es experiments/media-lab/evidence/android,
        # así que las sondas quedan en evidence/android/sondas-f2/ (ignorada por evidence/.gitignore).
        check(lab.viejos["EVIDENCIA"].parts[-3:] == ("media-lab", "evidence", "android"),
              f"EVIDENCIA real es experiments/media-lab/evidence/android ({lab.viejos['EVIDENCIA']})")
        check(lab.lab._evidencia("SONDA-F2-X") == raiz / "evidence" / "sondas-f2" / "SONDA-F2-X"
              and lab.lab._evidencia("LAB-X") == raiz / "evidence" / "LAB-X"
              and lab.lab._evidencia("SONDA-R") == raiz / "evidence" / "SONDA-R",
              "las evidencias de las sondas SONDA-F2-* van a sondas-f2/ (ignorada por git) y las demás no")
        for extra, label in ((("--texto", "Partager"), "«Partager»"),
                             (("--texto", "partager"), "«partager» en minúsculas"),
                             (("--texto", "\u200bPartager"), "«Partager» precedido de un carácter de ancho cero"),
                             (("--texto", "Publicar"), "«Publicar»"),
                             (("--desc", "Compartir historia"), "«Compartir historia»"),
                             (("--resource-id", "com.instagram.barcelona:id/new_thread_screen_post_button"),
                              "el id del botón de publicar de Threads"),
                             (("--texto", "Anular"), "«Anular»"),
                             (("--texto", "ANULAR"), "«ANULAR» en mayúsculas"),
                             (("--desc", "Votre story"), "«Votre story» (publica la Story)")):
            sim = TelefonoSimulado([xml_compositor()])
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, *extra))
            check(rechazo(res, "envío") and sim.toques == [] and sim.volcados_leidos == 0 and sim.capturas == [],
                  f"sonda tocar se niega a pulsar {label} antes de tocar el teléfono ({res and res[0]}, {err!r})")
        for args, fragmento, label in ((("sonda", "instagram", "volcar", "--run", "SONDA-F2-T", "--nombre", "a"), "--supervisada",
                                        "sin --supervisada"),
                                       (("sonda", "instagram", "volcar", "--run", "LAB-X", "--nombre", "a", "--supervisada"), "SONDA-F2-",
                                        "--run que no empieza por SONDA-F2-"),
                                       (("sonda", "instagram", "tocar", *supervisada), "--texto", "tocar sin criterio"),
                                       (("sonda", "instagram", "volcar", *supervisada, "--texto", "Suivant"), "--texto",
                                        "volcar con criterio")):
            sim = TelefonoSimulado([xml_compositor()])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0 and sim.toques == [],
                  f"sonda rechaza {label} ({res and res[0]}, {err!r})")

        sim = TelefonoSimulado([XML_BOTON_ENVIO_CON_ICONO])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--desc", "Icône"))
        check(res is not None and res[0] == 4 and sim.toques == [],
              f"sonda tocar no pulsa un icono dentro del botón de envío ({res and res[0]}, {err!r})")
        sim = TelefonoSimulado([XML_BOTON_ENVIO_CON_ICONO])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
        volcado = raiz / "evidence" / "sondas-f2" / "SONDA-F2-T" / "a.xml"
        check(res is not None and res[0] == 0 and sim.toques == [(963, 170)] and volcado.is_file()
              and sim.capturas == ["a.png"],
              f"sonda tocar pulsa un nodo único y deja volcado y captura ({res and res[0]}, {sim.toques})")
        sim = TelefonoSimulado([xml_perfil()])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "threads", "lanzar", "--run", "SONDA-F2-T",
                                                          "--nombre", "b", "--supervisada"))
        check(res is not None and res[0] == 0 and sim.orden == ["lanzar:com.instagram.barcelona"] and sim.toques == [],
              f"sonda lanzar abre la app y vuelca sin tocar ({res and res[0]}, {sim.orden})")

        rel = "experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-T/crudo.xml"
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text(crudo, encoding="utf-8")
        codigo, datos, _ = lab("fixture-podar", "--app", "instagram", "--desde", rel, "--pantalla", "perfil")
        destino = raiz / "tests" / "fixtures" / "telefono" / "instagram" / "perfil.xml"
        check(codigo == 0 and destino.is_file() and "Juan" not in destino.read_text(encoding="utf-8"),
              f"fixture-podar escribe el fixture podado ({codigo}, {datos})")
        for args, fragmento, label in ((("--desde", "/etc/hosts", "--pantalla", "x"), "--desde", "un origen fuera de evidence"),
                                       (("--desde", rel, "--pantalla", "../x"), "--pantalla", "una pantalla con ..")):
            check(rechazo(lab("fixture-podar", "--app", "instagram", *args), fragmento), f"fixture-podar rechaza {label}")

        dir_ig = raiz / "tests" / "fixtures" / "telefono" / "instagram"
        fuera = raiz / "fuera"
        fuera.mkdir()
        victima = fuera / "victima.xml"
        victima.write_text("original", encoding="utf-8")
        (dir_ig / "enlazado.xml").symlink_to(victima)
        check(rechazo(lab("fixture-podar", "--app", "instagram", "--desde", rel, "--pantalla", "enlazado"), "enlace simbólico")
              and victima.read_text(encoding="utf-8") == "original",
              "fixture-podar no escribe a través de un destino que es un enlace simbólico")
        (raiz / "tests" / "fixtures" / "telefono" / "threads").symlink_to(fuera, target_is_directory=True)
        check(rechazo(lab("fixture-podar", "--app", "threads", "--desde", rel, "--pantalla", "perfil"),
                      "sale de tests/fixtures/telefono") and not (fuera / "perfil.xml").exists(),
              "fixture-podar no escribe en una carpeta de app enlazada fuera de tests/fixtures/telefono")
        roto = "experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-T/roto.xml"
        (raiz / roto).write_text("<hierarchy><node", encoding="utf-8")
        res = lab("fixture-podar", "--app", "instagram", "--desde", roto, "--pantalla", "roto")
        check(rechazo(res, "legible", tipo="VolcadoIlegible") and not (dir_ig / "roto.xml").exists(),
              f"fixture-podar rechaza un volcado ilegible sin traceback ({res[0]}, {res[2][-80:]!r})")
        de_facebook = "experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-T/fb.xml"
        (raiz / de_facebook).write_text(jerarquia(nodo_xml("[0,0][100,100]", texto="Publicar", paquete="com.facebook.katana")),
                                        encoding="utf-8")
        res = lab("fixture-podar", "--app", "instagram", "--desde", de_facebook, "--pantalla", "vacio")
        check(rechazo(res, "com.instagram.android", tipo="FixtureVacio") and not (dir_ig / "vacio.xml").exists(),
              f"fixture-podar no escribe un fixture vacío de un volcado de otra app ({res[0]}, {res[1]})")

        # B1: borrado. Un criterio que es un verbo de borrar se rechaza antes de volcar.
        for extra, label in ((("--texto", "Supprimer"), "«Supprimer»"),
                             (("--texto", "SUPPRIMER"), "«SUPPRIMER»"),
                             (("--texto", "\u200bSupprimer"), "«Supprimer» con ancho cero"),
                             (("--texto", "Eliminar"), "«Eliminar»"),
                             (("--texto", "ELIMINAR\u200b"), "«ELIMINAR» con ancho cero"),
                             (("--texto", "Mover a la papelera"), "«Mover a la papelera»"),
                             (("--texto", "MOVER A LA\u00a0PAPELERA"), "«MOVER A LA PAPELERA» con NBSP"),
                             (("--desc", "Delete post"), "«Delete post»"),
                             (("--texto", "Borrar"), "«Borrar»"),
                             (("--resource-id", "com.facebook.katana:id/delete_button"), "un resource-id delete_button")):
            sim = TelefonoSimulado([xml_compositor()])
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, *extra))
            check(rechazo(res, "borrado") and sim.toques == [] and sim.volcados_leidos == 0,
                  f"sonda tocar se niega a pulsar {label} antes de tocar el teléfono ({res and res[0]}, {err!r})")
        th, fb, boton = "com.instagram.barcelona", "com.facebook.katana", "android.widget.Button"
        pulsable = 'clickable="true"'
        dialogos = (
            ("instagram", "--texto", "Annuler", "el diálogo «Supprimer la publication ?» de Instagram",
             jerarquia(nodo_xml("[100,800][980,880]", texto="Supprimer la publication ?"),
                       nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase=boton, extra=pulsable),
                       nodo_xml("[100,1250][980,1350]", texto="Annuler", clase=boton, extra=pulsable))),
            ("threads", "--texto", "Annuler", "el diálogo «Supprimer le thread ?» de Threads",
             jerarquia(nodo_xml("[100,800][980,880]", texto="Supprimer le thread ?", paquete=th),
                       nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase=boton, paquete=th, extra=pulsable),
                       nodo_xml("[100,1250][980,1350]", texto="Annuler", clase=boton, paquete=th, extra=pulsable))),
            ("facebook", "--texto", "Cancelar", "el diálogo «¿Eliminar publicación?» de Facebook",
             jerarquia(nodo_xml("[100,800][980,880]", texto="¿Eliminar publicación?", paquete=fb),
                       nodo_xml("[100,1100][980,1200]", texto="Eliminar", clase=boton, paquete=fb, extra=pulsable),
                       nodo_xml("[100,1250][980,1350]", texto="Cancelar", clase=boton, paquete=fb, extra=pulsable))),
            ("instagram", "--texto", "Annuler", "un título de borrado en mayúsculas y con ancho cero de otro paquete",
             jerarquia(nodo_xml("[100,800][980,880]", texto="\u200bSUPPRIMER LA PUBLICATION ?", paquete="com.android.systemui"),
                       nodo_xml("[100,1250][980,1350]", texto="Annuler", clase=boton, extra=pulsable))),
            ("facebook", "--desc", "Opción", "un menú con «Mover a la papelera» dentro del nodo pulsable",
             jerarquia(nodo_xml("[0,1500][1080,1600]", desc="Opción", clase="android.view.ViewGroup", paquete=fb, extra=pulsable,
                                hijos=nodo_xml("[40,1520][600,1580]", texto="Mover a la papelera", paquete=fb)))),
            ("instagram", "--resource-id", "com.instagram.android:id/boton_rojo", "un nodo elegido por id cuyo texto es «Retirer»",
             jerarquia(nodo_xml("[100,1100][980,1200]", texto="Retirer", clase=boton,
                                extra='clickable="true" resource-id="com.instagram.android:id/boton_rojo"'))),
            ("facebook", "--desc", "Opción", "una fila pulsable con «Mover a la papelera» lejos del centro del toque",
             jerarquia(nodo_xml("[0,1500][1080,1600]", desc="Opción", clase="android.view.ViewGroup", paquete=fb, extra=pulsable,
                                hijos=nodo_xml("[700,1520][1040,1580]", texto="Mover a la papelera", paquete=fb)))),
        )
        for app, opcion, criterio, label, xml in dialogos:
            sim = TelefonoSimulado([xml])
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", app, "tocar", *supervisada, opcion, criterio))
            check(res is not None and res[0] == 4 and campo(res[1], "tipo") == "PantallaInesperada" and sim.toques == [],
                  f"sonda tocar no pulsa nada con {label} ({res and res[0]}, {res and campo(res[1], 'error')})")
        sim = TelefonoSimulado([jerarquia(nodo_xml("[100,1100][980,1200]", texto="Recommencer", clase=boton, extra=pulsable))])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Recommencer"))
        check(res is not None and res[0] == 0 and sim.toques == [(540, 1150)],
              f"«Recommencer» sigue siendo tocable fuera de un diálogo de borrado ({res and res[0]}, {sim.toques})")

        # B2: el nodo se elige sobre una pantalla estable y se toca sobre el último volcado.
        suivant = jerarquia(nodo_xml("[880,120][1060,220]", texto="Suivant", extra=pulsable))
        partager = jerarquia(nodo_xml("[880,120][1060,220]", texto="Partager", clase=boton, extra=pulsable))
        sim = TelefonoSimulado([suivant, partager])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
        check(res is not None and res[0] == 4 and sim.toques == [],
              f"sonda tocar no pulsa si el volcado siguiente trae «Partager» donde estaba «Suivant» ({res and res[0]}, {sim.toques})")
        sim = TelefonoSimulado([suivant, suivant])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
        check(res is not None and res[0] == 0 and sim.toques == [(970, 170)],
              f"con volcados iguales la sonda toca una sola vez ({res and res[0]}, {sim.toques})")
        movido = jerarquia(nodo_xml("[880,320][1060,420]", texto="Suivant", extra=pulsable))
        sim = TelefonoSimulado([suivant, movido])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
        check(res is not None and res[0] == 0 and sim.toques == [(970, 370)] and sim.toques_en[0][2] == movido,
              f"si el nodo se mueve, la sonda espera a que se estabilice y toca sobre el último volcado ({sim.toques})")

        # I1: botón de envío identificado solo por resource-id.
        sim = TelefonoSimulado([xml_compositor()])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada,
                                                          "--resource-id", "com.instagram.android:id/share_footer_button"))
        check(rechazo(res, "envío") and sim.volcados_leidos == 0 and sim.toques == [],
              "sonda tocar rechaza --resource-id share_footer_button antes de volcar")
        boton_rid = jerarquia(nodo_xml("[45,2081][1035,2205]", clase=boton,
                                       extra='clickable="true" resource-id="com.instagram.android:id/share_footer_button"',
                                       hijos=nodo_xml("[60,2100][120,2180]", desc="Flèche", clase="android.widget.ImageView")))
        sim = TelefonoSimulado([boton_rid])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--desc", "Flèche"))
        check(res is not None and res[0] == 4 and sim.toques == [],
              f"sonda tocar no pulsa un nodo inocuo dentro de share_footer_button sin texto ({res and res[0]}, {sim.toques})")
        def en_contenedor(rid: str, extra_contenedor: str = "") -> str:
            return jerarquia(nodo_xml("[0,150][1080,2000]", clase="android.widget.FrameLayout",
                                      extra=f'{extra_contenedor} resource-id="{rid}"',
                                      hijos=nodo_xml("[847,1500][1080,1649]", texto="Suivant", extra=pulsable)))

        # Un contenedor NO pulsable con id de envío no bloquea (ENVIO_IDS compara el sufijo exacto y es_id_envio solo
        # mira pulsables); uno PULSABLE sin etiqueta sí, aunque sea post_capture_* (falla cerrado).
        for rid in ("com.instagram.android:id/post_capture_container", "com.instagram.android:id/followers_share_content"):
            sim = TelefonoSimulado([en_contenedor(rid)])
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
            check(res is not None and res[0] == 0 and sim.toques == [(963, 1574)],
                  f"un contenedor NO pulsable {rid.rsplit('/', 1)[-1]} no bloquea el toque normal ({res and res[0]}, {sim.toques})")
        for rid, label in (("com.instagram.android:id/direct_private_share_x", "direct_private_share_x"),
                           ("com.instagram.android:id/post_capture_container", "post_capture_* pulsable (falla cerrado)")):
            sim = TelefonoSimulado([en_contenedor(rid, pulsable)])
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
            check(res is not None and res[0] == 4 and sim.toques == [],
                  f"un nodo inocuo dentro de un contenedor pulsable sin etiqueta {label} no se pulsa ({res and res[0]}, {sim.toques})")
        compositor_fb = jerarquia(nodo_xml("[900,100][1060,240]", clase="android.view.ViewGroup", paquete=fb,
                                           extra='clickable="true" resource-id="com.facebook.katana:id/composer_post_button"'))
        sim = TelefonoSimulado([compositor_fb])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "facebook", "tocar", *supervisada,
                                                          "--resource-id", "com.facebook.katana:id/composer_post_button"))
        check(res is not None and res[0] == 4 and sim.toques == [],
              f"sonda tocar no pulsa composer_post_button de Facebook sin texto ({res and res[0]}, {res and campo(res[1], 'error')})")
        con_etiqueta = jerarquia(nodo_xml("[0,150][1080,2000]", desc="Options", clase="android.widget.FrameLayout",
                                          extra='clickable="true" resource-id="com.instagram.android:id/share_menu"',
                                          hijos=nodo_xml("[847,1500][1080,1649]", texto="Suivant", extra=pulsable)))
        sim = TelefonoSimulado([con_etiqueta])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
        check(res is not None and res[0] == 0 and sim.toques == [(963, 1574)],
              f"un contenedor pulsable CON etiqueta e id share_menu no bloquea el «Suivant» de dentro ({res and res[0]}, {sim.toques})")

        # I2: nada tapa el nodo (notificación de systemui, aviso de la app o ventana emergente).
        identificar = nodo_xml("[40,300][1040,500]", texto="Identifier des personnes", extra=pulsable)
        tapas = (("una notificación flotante de com.android.systemui", ((),),
                  jerarquia(identificar, nodo_xml("[0,250][1080,650]", clase="android.widget.FrameLayout",
                                                  paquete="com.android.systemui", extra=pulsable,
                                                  hijos=nodo_xml("[40,270][1040,400]", texto="Nouveau message",
                                                                 paquete="com.android.systemui")))),
                 ("un aviso de la propia app", ((),),
                  jerarquia(identificar, nodo_xml("[0,250][1080,650]", desc="Nouveau message", clase="android.widget.FrameLayout",
                                                  extra=pulsable))),
                 ("una ventana emergente fuera del volcado",
                  ([{"nombre": "PopupWindow:1", "frame": (0, 250, 1080, 650), "ancho_padre": 1080}],),
                  jerarquia(identificar)))
        for label, emergentes, xml in tapas:
            sim = TelefonoSimulado([xml], emergentes=emergentes)
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada,
                                                              "--texto", "Identifier des personnes"))
            check(res is not None and res[0] == 4 and sim.toques == [],
                  f"sonda tocar no pulsa si {label} tapa el nodo ({res and res[0]}, {res and campo(res[1], 'error')})")
        sim = TelefonoSimulado([jerarquia(identificar)])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada,
                                                          "--texto", "Identifier des personnes"))
        check(res is not None and res[0] == 0 and sim.toques == [(540, 400)],
              f"sin nada encima el mismo nodo sí se toca ({res and res[0]}, {sim.toques})")

        # Carrera residual: el último volcado, tras mirar las ventanas emergentes, tiene que traer el mismo nodo.
        for ultimo, label in ((movido, "el nodo se mueve"), (partager, "aparece «Partager» en su sitio")):
            sim = TelefonoSimulado([suivant, suivant, suivant, ultimo])
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
            check(res is not None and res[0] == 4 and sim.toques == [],
                  f"si en el último volcado {label}, la sonda sale con 4 sin tocar ({res and res[0]}, {sim.toques})")

        res = lab("fixture-podar", "--app", "instagram", "--desde", rel, "--pantalla", "perfil.xml")
        check(rechazo(res, "sin la extensión .xml") and not (dir_ig / "perfil.xml.xml").exists(),
              f"fixture-podar rechaza --pantalla con .xml ({res[0]}, {res[1]})")

    # I3: podar y revisar no dejan pasar datos personales.
    fugas = jerarquia(
        nodo_xml("[0,200][1080,300]", texto="#juanperez612345678", extra='hint="#juanperez612345678"'),
        nodo_xml("[0,400][1080,500]", desc="Audio suggéré. Juan Pérez García · nota de voz privada"),
        nodo_xml("[0,600][1080,700]", texto="Profil", extra='resource-id="com.instagram.android:id/story_tray_juan.perez"'),
        nodo_xml("[0,800][1080,900]", texto="612345678 s"),
        nodo_xml("[0,1000][1080,1100]", desc="#citasdiarias"),
        nodo_xml("[0,1200][1080,1300]", texto="Profil", extra='resource-id="com.facebook.katana:id/next_button"'),
        nodo_xml("[0,1400][1080,1500]", texto="#citasdiarias",
                 extra='resource-id="com.instagram.android:id/caption_text" hint="#sabiduria"'),
        nodo_xml("[0,1600][1080,1700]", texto="3 min"),
    ).replace("</hierarchy>", '<extra package="com.instagram.android" text="Juan Pérez"/></hierarchy>')
    podado = FX.podar(fugas, "instagram")
    pares = [(n["texto"], n["desc"]) for n in T.nodos(podado)]
    quedan = [f for f in ("juanperez612345678", "Juan Pérez", "nota de voz", "story_tray_juan", "612345678",
                          "com.facebook.katana", "<extra", 'hint="#sabiduria"') if f in podado]
    check(not quedan, f"podar no deja hashtags con cifras, audio con tema, ids ajenos, edades largas ni elementos extraños ({quedan})")
    check('resource-id="com.instagram.android:id/caption_text"' in podado and ("#citasdiarias", "") in pares
          and ("3 min", "") in pares and ("", "#citasdiarias") not in pares,
          f"podar conserva un id limpio de la app, el hashtag en text y una edad corta, pero no un hashtag en desc ({pares})")
    check(FX.revisar(podado, "instagram") == [], f"revisar da limpio el volcado podado ({FX.revisar(podado, 'instagram')[:3]})")
    senalado = " | ".join(FX.revisar(fugas, "instagram"))
    faltan = [f for f in ("text='#juanperez612345678'", "hint='#juanperez612345678'", "Audio suggéré. Juan", "story_tray_juan",
                          "612345678 s", "com.facebook.katana:id/next_button", "content-desc='#citasdiarias'",
                          "hint='#sabiduria'", "<extra>") if f not in senalado]
    check(not faltan, f"revisar señala cada fuga del volcado crudo (faltan {faltan})")
    check(TX.permitido("Audio suggéré.", "instagram") and not TX.permitido("Audio suggéré. Juan Pérez", "instagram")
          and TX.permitido("#sabiduria", "instagram") and not TX.permitido("#sabiduria", "instagram", "hint")
          and not TX.permitido("#juanperez612345678", "instagram") and not TX.permitido("#612", "instagram")
          and TX.permitido("12 h", "instagram") and not TX.permitido("1234 h", "instagram")
          and not TX.permitido("612345678 s", "instagram"),
          "permitido: audio solo literal, hashtags solo en text y sin cifras largas, edades de 1 a 3 cifras")
    check(TX.es_texto_borrado("Supprimer la publication ?") and TX.es_texto_borrado("\u200bELIMINAR")
          and TX.es_texto_borrado("delete_button") and not TX.es_texto_borrado("Recommencer")
          and not TX.es_texto_borrado("Removed") and not TX.es_texto_borrado("Supprimerx"),
          "es_texto_borrado: verbo seguido de fin o separador, normalizado")
    check(TX.es_texto_envio("share_footer_button")
          and not TX.es_texto_envio("com.instagram.android:id/share_footer_button_container")
          and not TX.es_texto_envio("com.instagram.android:id/post_capture_container"),
          "ENVIO_IDS compara el sufijo exacto del resource-id, sin prefijos")
    check(not TX.permitido("#juan61234", "instagram") and not TX.permitido("#ab1234", "instagram")
          and TX.permitido("#citas123", "instagram") and TX.permitido("#citasdiarias", "instagram"),
          "un hashtag de fixture no lleva 4 o más cifras seguidas")
    check(TX.es_id_envio("com.facebook.katana:id/composer_post_button") and TX.es_id_envio("direct_private_share_x")
          and TX.es_id_envio("com.instagram.android:id/SUBMIT") and not TX.es_id_envio("com.instagram.android:id/poster_view")
          and not TX.es_id_envio("com.instagram.android:id/reshared_badge") and not TX.es_id_envio(""),
          "es_id_envio busca palabras enteras del final del id partido por «_»")
    check(not TX.permitido("612345678 publications", "instagram"),
          "un recuento con 6 o más cifras seguidas no se queda en un fixture aunque case el patrón de publicaciones")
    check(FX.revisar(jerarquia(nodo_xml("[0,0][1080,100]", texto="Profil", paquete="com.android.systemui")), "instagram"),
          "revisar señala un nodo de systemui aunque su texto sea de la tabla")
    from labkit import pantalla as P
    check(lanza(lambda: P.nodo_sonda(XML_BOTON_ENVIO_CON_ICONO, PAQUETE_IG, desc="Icône"), P.PantallaInesperada),
          "nodo_sonda rechaza un icono dentro de un botón de envío")
    for patron in (r"[0-9]+ h", r"[0-9]* h", r"[0-9]{2,} h", r"[0-9a-z]+ h", r"\d* h"):
        check(lanza(lambda: TX._edades_fixture({"x": ((patron, None),)}), ValueError),
              f"_edades_fixture falla con una cifra sin acotar: {patron!r}")
    check(TX._edades_fixture({"x": ((r"\d+ h", None), (r"[0-9]{1,3} min", None), (r"[0-9] s", None))})
          == {"x": (r"\d{1,3} h", r"[0-9]{1,3} min", r"[0-9] s")},
          "_edades_fixture acepta \\d+ (lo acota), [0-9]{1,3} y una sola [0-9]")
    import types
    with entorno_lab_fase2() as (lab, raiz):
        desconocida = types.SimpleNamespace(supervisada=True, run="SONDA-F2-T", accion="pulsar", texto=None, desc=None,
                                            resource_id=None, app="instagram", nombre="a")
        sim = TelefonoSimulado([xml_perfil()], listo=False)
        res, err = con_telefono_simulado(sim, lambda: lab.lab.cmd_sonda(desconocida))
        check(isinstance(err, lab.lab.ArgumentoNoValido) and "desconocida" in str(err) and sim.volcados_leidos == 0,
              f"cmd_sonda rechaza una acción desconocida antes de mirar si el teléfono está listo ({res}, {err!r})")


def seccion_arranque_en_frio() -> None:
    print("\n18. Fase 2: arranque en frío de Instagram en ig abrir si ningún volcado es legible")
    import tempfile
    from datetime import datetime, timezone
    from labkit import instagram_feed as IG, pasos, telefono as T

    llamadas: list = []
    original_shell = T.shell
    T.shell = lambda cmd, timeout=60: llamadas.append((cmd, timeout)) or ""
    try:
        T.forzar_cierre(PAQUETE_IG)
    finally:
        T.shell = original_shell
    check(llamadas == [(f"am force-stop {PAQUETE_IG}", 15)],
          f"forzar_cierre ejecuta am force-stop con timeout corto ({llamadas})")

    colgado = T.TelefonoError("uiautomator dump sin respuesta en 5 s")
    arranque = jerarquia(nodo_xml("[340,1000][740,1400]", desc="Instagram", clase="android.widget.ImageView"))
    menu_crear = jerarquia(nodo_xml("[100,1500][980,1650]", texto="Publication"))
    normal = [arranque, xml_inicio(), xml_perfil(), menu_crear, SELECTOR_IG]
    subida = datetime(2026, 9, 14, 8, 39, tzinfo=timezone.utc)
    cierre, lanzar = f"forzar_cierre:{IG.PAQUETE}", f"lanzar:{IG.PAQUETE}"

    # Salidas de `dumpsys window` SINTÉTICAS (solo las líneas de foco) con nombres de actividad plausibles, salvo las
    # marcadas como dato real. Del teléfono constan MediaCaptureActivity (todo el flujo de creación: selector, editor
    # y compositor; fase 1 y 2026-09-15) y MainTabActivity (perfil, 2026-09-15); las demás actividades son inventadas.
    foco_compositor = "com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity"
    foco_principal = "com.instagram.android/com.instagram.mainactivity.InstagramMainActivity"
    foco_reel = "com.instagram.android/com.instagram.clips.viewer.ClipsViewerActivity"
    foco_directo = "com.instagram.android/com.instagram.direct.DirectThreadActivity"
    foco_compositor_corto = "com.instagram.android/.activity.MediaCaptureActivity"  # forma corta, sintética
    dialogo = "com.google.android.permissioncontroller/com.android.permissioncontroller.permission.ui.GrantPermissionsActivity"
    # Dato REAL del teléfono (`adb shell dumpsys window` con Instagram en el perfil, 2026-09-15): forma larga en
    # mCurrentFocus y corta en mFocusedApp.
    real_main_tab = ("  mCurrentFocus=Window{84f3924 u0 com.instagram.android/com.instagram.android.activity.MainTabActivity}\n"
                     "  mFocusedApp=ActivityRecord{234413417 u0 com.instagram.android/.activity.MainTabActivity t2500}\n")
    texto_dialogo = (f"  mCurrentFocus=Window{{5a6b7c u0 {dialogo}}}\n"
                     f"  mFocusedApp=ActivityRecord{{1a2b3c u0 {foco_compositor} t4242}}\n")
    for texto, esperado, label in (
            (f"  mCurrentFocus=Window{{e654062 u0 {foco_compositor}}}\n"
             f"  mFocusedApp=ActivityRecord{{1a2b3c u0 {foco_compositor} t4242}}\n", [foco_compositor, foco_compositor],
             "el compositor"),
            (f"  mCurrentFocus=Window{{7f00a1 u0 {foco_principal}}}\n", [foco_principal], "la actividad principal"),
            (f"  mCurrentFocus=Window{{7f00a2 u0 {foco_reel}}}\n"
             f"  mFocusedApp=ActivityRecord{{2b3c4d u0 {foco_reel} t77}}\n", [foco_reel, foco_reel], "el Reel"),
            (f"  mCurrentFocus=null\n  mFocusedApp=ActivityRecord{{3c4d5e u0 {foco_directo} t78}}\n", [foco_directo],
             "el visor de mensajes solo en mFocusedApp"),
            (f"  mCurrentFocus=Window{{49fd424 u0 PopupWindow:de536c5}}\n"
             f"  mFocusedApp=ActivityRecord{{1a2b3c u0 {foco_compositor} t4242}}\n", [foco_compositor],
             "una ventana sin componente en mCurrentFocus (solo cuenta mFocusedApp)"),
            (real_main_tab, ["com.instagram.android/com.instagram.android.activity.MainTabActivity",
                             "com.instagram.android/.activity.MainTabActivity"],
             "el dato real del perfil (forma larga y corta)"),
            ("  mCurrentFocus=null\n  mFocusedApp=ActivityRecord{1 u0 com.instagram.android/.activity.MediaCaptureActivity t2500}\n",
             [foco_compositor_corto], "el compositor en forma corta solo en mFocusedApp"),
            (texto_dialogo, [dialogo, foco_compositor], "un diálogo de permissioncontroller encima del compositor"),
            # Dato REAL (2026-09-15, selector «Nouvelle publication» abierto); el id de ventana es inventado.
            ("  mCurrentFocus=Window{9d8e7f6 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity}\n",
             [foco_compositor], "el dato real del selector «Nouvelle publication» (flujo de creación)"),
            ("  mCurrentFocus=null\n  mFocusedApp=null\n", [], "un texto sin foco"),
            ("", [], "un texto vacío")):
        check(T.focos_de(texto) == esperado, f"focos_de con {label}: {T.focos_de(texto)!r}")

    sim = TelefonoSimulado([colgado])
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_que(lambda x: True, "algo"))
    check(isinstance(err, pasos.SinVolcado) and isinstance(err, IG.PantallaInesperada) and "último error" in str(err),
          f"esperar_que sin ningún volcado legible lanza SinVolcado, que sigue siendo PantallaInesperada ({err!r})")
    sim = TelefonoSimulado([arranque, colgado])
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_que(lambda x: False, "algo"))
    check(isinstance(err, IG.PantallaInesperada) and not isinstance(err, pasos.SinVolcado),
          f"esperar_que con un volcado leído que no cuadra (y luego errores) no es SinVolcado ({err!r})")

    with tempfile.TemporaryDirectory() as d:
        evid = pathlib.Path(d)

        sim = TelefonoSimulado([colgado], focos=(foco_reel,), tras_cierre=normal)
        res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
        check(err is None and sim.orden == ["cortina", lanzar, cierre, lanzar] and res["arranque_en_frio"] is True
              and res["publicaciones_antes"] == 3712 and not sim.prohibidos
              and sim.capturas == ["ig-00-antes-de-arranque-en-frio.png", "ig-01-selector.png"],
              f"ningún volcado legible: un forzar_cierre, dos lanzar y arranque_en_frio True ({err!r}, {sim.orden})")

        sim = TelefonoSimulado([xml_compositor()], tras_cierre=normal)
        res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
        check(isinstance(err, IG.BorradorPendiente) and cierre not in sim.orden and sim.toques == [],
              f"un borrador pendiente en el primer volcado: BorradorPendiente sin forzar_cierre ({err!r}, {sim.orden})")
        sim = TelefonoSimulado([colgado, colgado, xml_compositor()], tras_cierre=normal)
        res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
        check(isinstance(err, IG.BorradorPendiente) and cierre not in sim.orden and sim.toques == [],
              f"volcados colgados y luego un borrador legible: BorradorPendiente sin forzar_cierre ({err!r}, {sim.orden})")

        for guion, label in (([arranque], "los volcados se leen pero no aparece «Profil»"),
                             ([arranque, colgado], "un volcado leído sin «Profil» y después solo errores")):
            sim = TelefonoSimulado(guion, tras_cierre=normal)
            res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
            check(isinstance(err, IG.PantallaInesperada) and not isinstance(err, pasos.SinVolcado)
                  and "Instagram listo" in str(err) and sim.orden == ["cortina", lanzar] and sim.toques == [],
                  f"{label}: el error de siempre, sin forzar_cierre ({err!r}, {sim.orden})")

        sim = TelefonoSimulado([colgado], listo=False, tras_cierre=normal)
        res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
        check(isinstance(err, IG.TelefonoNoListo) and sim.orden == [],
              f"teléfono no listo: ni lanzar ni forzar_cierre ({err!r}, {sim.orden})")

        sim = TelefonoSimulado(normal, tras_cierre=[colgado])
        res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subida))
        check(err is None and sim.orden == ["cortina", lanzar] and res.get("arranque_en_frio", False) is False,
              f"flujo normal: sin forzar_cierre y arranque_en_frio False ({err!r}, {sim.orden})")

    with entorno_lab_fase2() as (lab, raiz):
        args = ("ig", "abrir", "--run", "RUN-1", "--subido-en", subida.isoformat())
        sim = TelefonoSimulado([colgado], focos=(foco_reel,), tras_cierre=normal)
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 0 and campo(res[1], "arranque_en_frio") is True
              and sim.orden.count(cierre) == 1 and sim.orden.count(lanzar) == 2,
              f"ig abrir emite arranque_en_frio true en su JSON tras el cierre forzado ({res and res[:2]}, {err!r})")
        sim = TelefonoSimulado([colgado], focos=(foco_reel,), tras_cierre=[colgado])
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 4 and campo(res[1], "tipo") == "SinVolcado"
              and sim.orden == ["cortina", lanzar, cierre, lanzar]
              and str(campo(res[1], "error")).endswith(IG.AVISO_ARRANQUE_EN_FRIO),
              f"los volcados fallan también tras el cierre: sale 4 con un solo forzar_cierre, sin bucle "
              f"y el error menciona el arranque en frío ({res and res[:2]}, {sim.orden})")
        check("am force-stop de com.instagram.android" in IG.AVISO_ARRANQUE_EN_FRIO,
              f"el aviso nombra el force-stop de Instagram ({IG.AVISO_ARRANQUE_EN_FRIO!r})")

        sim = TelefonoSimulado([colgado], focos=(foco_reel,), tras_cierre=normal, falla_cierre=T.TelefonoError("adb: device offline"))
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 4 and campo(res[1], "tipo") == "TelefonoError"
              and sim.orden == ["cortina", lanzar, cierre]
              and "device offline" in str(campo(res[1], "error"))
              and IG.AVISO_ARRANQUE_EN_FRIO in str(campo(res[1], "error")),
              f"forzar_cierre falla: sale 4, no relanza y el error menciona el arranque en frío "
              f"({res and res[:2]}, {sim.orden})")

        sim = TelefonoSimulado([colgado], focos=(foco_reel,), tras_cierre=normal)
        listos = [True, False]  # listo al empezar; ya no lo está al ir a forzar el cierre
        sim.estado = lambda: {"adb": True, "listo": listos.pop(0) if len(listos) > 1 else listos[0]}
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 4 and campo(res[1], "tipo") == "TelefonoNoListo"
              and cierre not in sim.orden and IG.AVISO_ARRANQUE_EN_FRIO not in str(campo(res[1], "error")),
              f"el teléfono deja de estar listo antes del cierre: sale 4 sin forzar_cierre y sin el aviso "
              f"({res and res[:2]}, {sim.orden})")

        sim = TelefonoSimulado([colgado], focos=(foco_reel,), tras_cierre=[xml_compositor()])
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 4 and campo(res[1], "tipo") == "BorradorPendiente"
              and sim.orden == ["cortina", lanzar, cierre, lanzar] and sim.toques == []
              and IG.AVISO_ARRANQUE_EN_FRIO in str(campo(res[1], "error")),
              f"BorradorPendiente tras el arranque en frío: sale 4 y el error lo menciona ({res and res[:2]}, {sim.orden})")
        sim = TelefonoSimulado([xml_compositor()])
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 4 and campo(res[1], "tipo") == "BorradorPendiente"
              and IG.AVISO_ARRANQUE_EN_FRIO not in str(campo(res[1], "error")),
              f"BorradorPendiente sin arranque en frío: el error no menciona el aviso ({res and res[:2]})")
        sim = TelefonoSimulado(normal)
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 0 and campo(res[1], "arranque_en_frio") is False and cierre not in sim.orden,
              f"ig abrir en el flujo normal emite arranque_en_frio false ({res and res[:2]}, {err!r})")
        check(IG.CAPTURA_ANTES_DE_ARRANQUE not in sim.capturas, f"el flujo normal no hace la captura previa ({sim.capturas})")

        for focos, falla, motivo, label in (
                ((foco_compositor,), None, "MediaCaptureActivity", "foco en el compositor (MediaCaptureActivity)"),
                ((foco_compositor_corto,), None, "MediaCaptureActivity",
                 "foco del compositor en forma corta (/.activity.MediaCaptureActivity)"),
                (tuple(T.focos_de(texto_dialogo)), None, "MediaCaptureActivity",
                 "diálogo de permissioncontroller en mCurrentFocus con el compositor en mFocusedApp"),
                ((), None, "foco de ventana", "foco ilegible (ni mCurrentFocus ni mFocusedApp)"),
                ((foco_reel,), T.TelefonoError("screencap no devolvió un PNG (0 bytes)"), "captura previa",
                 "captura previa que falla")):
            sim = TelefonoSimulado([colgado], focos=focos, falla_captura=falla, tras_cierre=normal)
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            error = str(campo(res[1], "error")) if res else ""
            check(err is None and res[0] == 4 and campo(res[1], "tipo") == "SinVolcado"
                  and sim.orden == ["cortina", lanzar] and IG.CAPTURA_ANTES_DE_ARRANQUE in sim.capturas
                  and "no se forzó el cierre" in error and motivo in error and IG.AVISO_ARRANQUE_EN_FRIO not in error,
                  f"{label}: sale 4 con SinVolcado, sin forzar_cierre y diciendo por qué ({res and res[:2]}, {sim.orden})")

        sim = TelefonoSimulado([colgado], focos=(foco_principal,), tras_cierre=normal)
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 0 and campo(res[1], "arranque_en_frio") is True
              and sim.orden == ["cortina", lanzar, cierre, lanzar]
              and sim.capturas[:1] == [IG.CAPTURA_ANTES_DE_ARRANQUE],
              f"foco en la actividad principal de Instagram: arranque en frío con la captura previa hecha "
              f"({res and res[:2]}, {sim.capturas})")

        sim = TelefonoSimulado([colgado], focos=tuple(T.focos_de(real_main_tab)), tras_cierre=normal)
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        check(err is None and res[0] == 0 and campo(res[1], "arranque_en_frio") is True
              and sim.orden == ["cortina", lanzar, cierre, lanzar],
              f"los dos focos en MainTabActivity (dato real): cierre permitido ({res and res[:2]}, {sim.orden})")

        sim = TelefonoSimulado([colgado], focos=tuple(T.focos_de(real_main_tab)), tras_cierre=normal)
        captura_simulada = sim.captura

        def captura_selector_sin_disco(destino, timeout=None):
            if destino.name == "ig-01-selector.png":
                sim.capturas.append(destino.name)
                raise OSError(28, "No space left on device")
            return captura_simulada(destino, timeout)

        sim.captura = captura_selector_sin_disco
        res, err = con_telefono_simulado(sim, lambda: lab(*args))
        error = str(campo(res[1], "error")) if res else ""
        check(err is None and res[0] == 4 and campo(res[1], "tipo") == "OSError" and cierre in sim.orden
              and "No space left on device" in error and error.endswith(IG.AVISO_ARRANQUE_EN_FRIO),
              f"un OSError al guardar la captura del selector tras el arranque en frío: sale 4 con el aviso "
              f"({res and res[:2]}, {sim.orden})")


SECCIONES = [
    seccion_portapapeles,
    seccion_encargos,
    seccion_colision,
    seccion_seleccion,
    seccion_manifiesto_y_cerrojo,
    seccion_interfaz,
    seccion_codex,
    seccion_cli,
    seccion_guardia,
    seccion_cli_en_proceso,
    seccion_generar,
    seccion_render,
    seccion_turno,
    seccion_metricas,
    seccion_pantalla_comun,
    seccion_pasos_comunes,
    seccion_textos_y_descarte,
    seccion_recetas_y_seleccion,
    seccion_cli_fase2,
    seccion_sonda_y_fixtures,
    seccion_arranque_en_frio,
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
