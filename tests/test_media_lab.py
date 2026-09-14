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


def xml_inicio(*, banner: bool = False, aviso: str = "") -> str:
    """Inicio de Instagram: una publicación con su propio botón «Partager» y la barra de abajo."""
    return jerarquia(
        nodo_xml("[0,250][1080,330]", texto="Publication sur sabiduriabolsillo…") if banner else "",
        nodo_xml("[0,340][1080,420]", texto=aviso) if aviso else "",
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

    def __init__(self, volcados: list, *, teclado: tuple = (False,), listo: bool = True,
                 falla_tocar: Exception | None = None, falla_pegar: Exception | None = None):
        self.volcados = list(volcados)
        self.teclado = list(teclado)
        self.listo = listo
        self.falla_tocar = falla_tocar
        self.falla_pegar = falla_pegar
        self.toques: list[tuple[int, int]] = []
        self.teclas: list[int] = []
        self.combinaciones: list[tuple] = []
        self.pegados: list[str] = []
        self.capturas: list[str] = []
        self.prohibidos: list[str] = []
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

    def teclado_visible(self) -> bool:
        v = self.teclado_estado()
        return True if v is None else v

    def captura(self, destino: pathlib.Path) -> pathlib.Path:
        self.capturas.append(destino.name)
        return destino

    def lanzar(self, paquete: str) -> None:
        pass

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
               (telefono, "teclado_estado", sim.teclado_estado), (telefono, "captura", sim.captura),
               (telefono, "lanzar", sim.lanzar), (telefono, "shell", sim.prohibido),
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
    check(IG.observacion_de_volcado(inicio) == {"valido": True, "compositor": False, "banner": True, "fallo": False},
          "observa el banner en el inicio")
    check(IG.observacion_de_volcado(comp) == {"valido": True, "compositor": True, "banner": False, "fallo": False},
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

    sim = TelefonoSimulado([comp], falla_tocar=T.TelefonoError("device offline"))
    res, err = con_telefono_simulado(sim, lambda: IG.compartir(PIE_PRUEBA, tema, evid, 3711))
    check(err is None and res["estado"] == "error_tras_pulsar" and res["error"].startswith("TelefonoError")
          and res["submitted_at"] and res["captura_antes"] and len(sim.toques) == 1,
          f"(d) el toque falla: error_tras_pulsar, un intento y nada se escapa ({err or res})")

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
                do_not_use=[], formato={}, prompt="p", restricciones=[],
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


SECCIONES = [
    seccion_portapapeles,
    seccion_encargos,
    seccion_colision,
    seccion_seleccion,
    seccion_manifiesto_y_cerrojo,
    seccion_interfaz,
    seccion_codex,
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
