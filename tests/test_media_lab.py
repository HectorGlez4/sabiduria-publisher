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


def jerarquia(*hijos: str) -> str:
    raiz = nodo_xml("[0,0][1080,2340]", clase="android.widget.FrameLayout", hijos="".join(hijos))
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
                 falla_pegar: Exception | None = None, falla_cortina: Exception | None = None):
        self.volcados = list(volcados)
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

    @staticmethod
    def _siguiente(lista: list):
        return lista.pop(0) if len(lista) > 1 else lista[0]

    def volcado(self, timeout: int = 30) -> str:
        v = self._siguiente(self.volcados)
        if isinstance(v, BaseException):
            raise v
        return v

    def tocar(self, x: int, y: int) -> None:
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
        return destino

    def lanzar(self, paquete: str) -> None:
        self.orden.append(f"lanzar:{paquete}")

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
    from labkit import instagram_feed, telefono

    cambios = [(telefono, "volcado", sim.volcado), (telefono, "tocar", sim.tocar),
               (telefono, "tecla", sim.tecla), (telefono, "combinacion", sim.combinacion),
               (telefono, "estado", sim.estado), (telefono, "teclado_visible", sim.teclado_visible),
               (telefono, "teclado_estado", sim.teclado_estado),
               (telefono, "ventanas_emergentes", sim.ventanas_emergentes), (telefono, "captura", sim.captura),
               (telefono, "lanzar", sim.lanzar), (telefono, "cerrar_cortina", sim.cerrar_cortina),
               (telefono, "shell", sim.prohibido),
               (telefono, "adb", sim.prohibido), (phone_clipboard, "pegar", sim.pegar),
               (phone_clipboard, "adb", sim.prohibido), (subprocess, "run", sim.prohibido),
               (subprocess, "Popen", sim.prohibido),
               (instagram_feed.time, "sleep", lambda segundos: None),
               (instagram_feed.time, "monotonic", sim.monotonic)]
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
    check(T.ventanas_emergentes_de(dumpsys_popup, PAQUETE_IG)
          == [{"nombre": "PopupWindow:de536c5", "frame": (0, 1448, 1080, 2205)}],
          "(10f) el lector puro extrae la PopupWindow visible del paquete, con su frame")
    sin_popup = dumpsys_popup[dumpsys_popup.index("  Window #12"):]
    check(T.ventanas_emergentes_de(sin_popup, PAQUETE_IG) == [],
          "(10f) sin el bloque PopupWindow no hay emergentes")
    check(T.ventanas_emergentes_de(dumpsys_popup, "com.other.app") == [],
          "(10f) una PopupWindow de otro paquete no cuenta")
    check(T.ventanas_emergentes_de(dumpsys_popup.replace("isVisible=true", "isVisible=false", 1), PAQUETE_IG) == [],
          "(10f) isVisible=false no cuenta")
    check(T.ventanas_emergentes_de("", PAQUETE_IG) == [], "(10f) texto vacío: lista vacía")

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
    check(via_shell == [{"nombre": "PopupWindow:de536c5", "frame": (0, 1448, 1080, 2205)}],
          "(10f) ventanas_emergentes aplica el lector a la salida de dumpsys")
    check(fallo is not None, "(10f) si dumpsys falla, ventanas_emergentes falla cerrado con TelefonoError")

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
    emergente_abierta = [{"nombre": "PopupWindow:de536c5", "frame": (0, 1448, 1080, 2205)}]
    check(IG.compositor_listo(comp, PIE_PRUEBA, tema, emergente_abierta)
          == ["desplegable de hashtags abierto (ventana emergente)"],
          "(10f) compositor_listo con una emergente que se solapa con «Partager» añade el problema")
    check(IG.compositor_listo(comp, PIE_PRUEBA, tema) == [],
          "(10f) sin el parámetro emergentes, compositor_listo se comporta como antes")
    check(IG.compositor_listo(comp, PIE_PRUEBA, tema, []) == [],
          "(10f) con una lista de emergentes vacía, compositor_listo se comporta como antes")

    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_abierta, emergente_abierta, ()))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(err is None and sim.teclas == [IG.ATRAS] and sim.capturas == ["ig-04-compositor.png"],
          f"(10f) la emergente se ve en dos volcados (incluida la confirmación) y luego se cierra tras el «atrás»: "
          f"exactamente un «atrás» y captura ({err!r}, {sim.teclas}, {sim.capturas})")

    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_abierta,))
    res, err = con_telefono_simulado(sim, lambda: IG.escribir_pie(PIE_PRUEBA, evid))
    check(isinstance(err, IG.PantallaInesperada) and sim.teclas == [IG.ATRAS, IG.ATRAS]
          and "ig-04-compositor.png" not in sim.capturas,
          f"(10f) la emergente persiste: PantallaInesperada, exactamente 2 «atrás» y sin captura "
          f"({err!r}, {sim.teclas}, {sim.capturas})")

    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(emergente_abierta,))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(isinstance(err, IG.PantallaInesperada) and not isinstance(err, IntentoDeES) and sim.toques == [],
          f"(10f) compartir con volcados limpios pero una emergente abierta: PantallaInesperada y ningún toque "
          f"({err!r}, {sim.toques})")

    sim = TelefonoSimulado([comp], teclado=(False,), emergentes=(T.TelefonoError("dumpsys no responde"),))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(isinstance(err, T.TelefonoError) and not isinstance(err, IntentoDeES) and sim.toques == [],
          f"(10f) si ventanas_emergentes falla dentro de compartir, falla cerrado sin tocar ({err!r}, {sim.toques})")

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
                  "EVIDENCIA": self.raiz / "evidence", "COBERTURA": self.raiz / "coverage.json"}
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
            for n in range(1, 7):
                guardar_encargo(raiz, n, [f"X{n}"])
            codigo, datos, _ = nuevo(lab, "C-FB-API")
            check(codigo == 2 and "cola" in error(datos), f"con 6 en cola el 7.º encargo sale con 2 ({codigo}, {datos})")
            check(len(list((raiz / "encargos").glob("ENC-*.json"))) == 6, "el encargo rechazado por la cola no se guarda")

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
