#!/usr/bin/env python3
"""
Punto de entrada único del laboratorio.

    .venv/bin/python experiments/media-lab/lab.py <subcomando> [...]

Todo lo que toca encargos, teléfono, Codex o GitHub pasa por aquí: basta con
autorizar este comando para que una ejecución desatendida no se quede colgada
esperando un permiso que nadie va a contestar. A propósito no hay ningún
subcomando que borre o cancele publicaciones: eso es manual (media-lab-cancel).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
sys.path.insert(0, str(LAB))

from labkit import cerrojo, codex_rescate, colision, encargos, manifiesto, seleccion  # noqa: E402

ENCARGOS = Path(os.environ.get("LAB_ENCARGOS_DIR", LAB / "encargos"))
EVIDENCIA = LAB / "evidence" / "android"
LOCK = LAB / ".ventana.lock"


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def emitir(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def ruta_encargo(encargo_id: str) -> Path:
    return ENCARGOS / f"{encargo_id}.json"


# ── comprobación previa ─────────────────────────────────────────────────────

def cmd_preflight(a) -> int:
    from labkit import telefono
    t = ahora()
    try:
        tel = telefono.estado()
    except Exception as e:  # noqa: BLE001
        tel = {"listo": False, "error": f"{type(e).__name__}: {e}"}
    try:
        en_curso = colision.workflows_en_curso()
        espera = colision.motivo_espera(
            t, programadas=colision.programadas_de_cola(ROOT / "content" / "queue"),
            publicadas=colision.publicadas_recientes(ROOT / "content" / "published", t),
            en_curso=en_curso)
        github = True
    except Exception as e:  # noqa: BLE001
        github, espera = False, f"GitHub no responde ({type(e).__name__}): sin datos de producción cercana"
    emitir({"ahora": t.isoformat(timespec="seconds"), "telefono": tel, "github": github, "espera": espera})
    return 0


def cmd_lock_tomar(a) -> int:
    ok = cerrojo.tomar(LOCK, ahora(), a.dueno)
    emitir({"cerrojo": ok})
    return 0 if ok else 3


def cmd_lock_soltar(a) -> int:
    soltado = cerrojo.soltar(LOCK, a.dueno)
    emitir({"cerrojo": "soltado" if soltado else "no era tuyo o no existía"})
    return 0


# ── encargos (Claude) ───────────────────────────────────────────────────────

def cmd_encargo_nuevo(a) -> int:
    t = ahora()
    todos = [e for _, e in encargos.listar(ENCARGOS)]
    if encargos.en_cola(todos) >= encargos.MAX_EN_COLA:
        print(f"ya hay {encargos.MAX_EN_COLA} encargos en cola", file=sys.stderr)
        return 2
    enc = encargos.nuevo(
        encargos.siguiente_id(ENCARGOS, t), coverage_cell_ids=a.cell, family_id=a.family,
        brief_path=a.brief, do_not_use=a.do_not_use or [], formato=json.loads(a.formato),
        prompt=Path(a.prompt_file).read_text(encoding="utf-8").strip(),
        restricciones=a.restriccion or [],
        destino_assets=f"experiments/media-lab/assets/{a.family}", ahora=t, variantes=a.variantes)
    encargos.guardar(ruta_encargo(enc["encargo_id"]), enc)
    emitir(enc)
    return 0


def cmd_encargos(a) -> int:
    emitir([{k: e[k] for k in ("encargo_id", "estado", "coverage_cell_ids", "lock_owner", "imagenes")}
            for _, e in encargos.listar(ENCARGOS)])
    return 0


def cmd_encargo_revisar(a) -> int:
    ruta = ruta_encargo(a.encargo)
    enc = encargos.revisar(encargos.cargar(ruta), aprobado=a.aprobado, motivo=a.motivo,
                           ahora=ahora(), correccion=a.correccion)
    encargos.guardar(ruta, enc)
    emitir({"encargo_id": enc["encargo_id"], "estado": enc["estado"]})
    return 0


def cmd_encargo_usado(a) -> int:
    ruta = ruta_encargo(a.encargo)
    enc = encargos.marcar_usado(encargos.cargar(ruta), a.run)
    encargos.guardar(ruta, enc)
    emitir({"encargo_id": enc["encargo_id"], "estado": enc["estado"], "runs": enc["runs"]})
    return 0


def cmd_seleccionar(a) -> int:
    cov = json.loads((LAB / "coverage.json").read_text(encoding="utf-8"))
    emitir(seleccion.elegir(cov["cells"], [e for _, e in encargos.listar(ENCARGOS)],
                            max_celdas=a.max, telefono_listo=not a.sin_telefono))
    return 0


# ── generación (Codex) ──────────────────────────────────────────────────────

def cmd_codex_tomar(a) -> int:
    t = ahora()
    tomados = []
    for ruta, enc in encargos.listar(ENCARGOS):
        if len(tomados) >= a.max:
            break
        if encargos.tomable(enc, t):
            encargos.tomar(enc, a.owner, t)
            encargos.guardar(ruta, enc)
            tomados.append({"encargo_id": enc["encargo_id"], "prompt": enc["prompt"],
                            "restricciones": enc["restricciones"] + enc["do_not_use"],
                            "formato": enc["formato"], "rutas": codex_rescate.rutas_imagen(enc)})
    emitir(tomados)
    return 0


def cmd_codex_generado(a) -> int:
    from PIL import Image
    ruta = ruta_encargo(a.encargo)
    enc = encargos.cargar(ruta)
    imagenes = []
    for rel in a.imagen:
        if not rel.startswith(enc["destino_assets"] + "/"):
            print(f"{rel} está fuera de {enc['destino_assets']}", file=sys.stderr)
            return 2
        p = ROOT / rel
        if not p.is_file():
            print(f"no existe {rel}", file=sys.stderr)
            return 2
        with Image.open(p) as im:
            ancho, alto = im.size
        imagenes.append({"ruta": rel, "sha256": sha256(p), "ancho": ancho, "alto": alto})
    encargos.marcar_generado(enc, a.owner, imagenes, ahora())
    encargos.guardar(ruta, enc)
    emitir(enc["imagenes"])
    return 0


def cmd_codex_fallo(a) -> int:
    ruta = ruta_encargo(a.encargo)
    enc = encargos.marcar_fallo(encargos.cargar(ruta), a.owner, a.nota, ahora())
    encargos.guardar(ruta, enc)
    emitir({"encargo_id": enc["encargo_id"], "estado": enc["estado"]})
    return 0


def _estado_git() -> dict[str, str]:
    """
    Hash actual de las rutas con cambios respecto a HEAD y de lo ignorado que importa.

    Lo ignorado no aparece en `git status`: se añaden a mano los secretos, el cerrojo de
    ventana y las tarjetas de producción, que Codex no debe tocar.
    """
    r = subprocess.run(["git", "status", "--porcelain", "-z", "-uall"], cwd=ROOT, capture_output=True,
                       timeout=60, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"git status falló: {r.stderr.decode(errors='replace').strip()[:200]}")
    rutas: list[str] = []
    campos = r.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    i = 0
    while i < len(campos):
        registro = campos[i]
        i += 1
        if not registro:
            continue
        rutas.append(registro[3:])
        if registro[0] in "RC" or registro[1] in "RC":
            i += 1  # en -z, un renombrado o copia trae después la ruta de origen
    rutas += [".env", "experiments/media-lab/.ventana.lock"]
    rutas += [str(q.relative_to(ROOT)) for q in (ROOT / "assets").glob("*.png")]
    fuera = {}
    for ruta in rutas:
        q = ROOT / ruta
        if q.is_symlink():
            fuera[ruta] = "enlace:" + os.readlink(q)
        elif q.is_file():
            fuera[ruta] = hashlib.sha256(q.read_bytes()).hexdigest()
        else:
            fuera[ruta] = "-"
    return fuera


def cmd_generar(a) -> int:
    ruta = ruta_encargo(a.encargo)
    try:
        v = subprocess.run([codex_rescate.CODEX, "--version"], capture_output=True, text=True,
                           timeout=30, stdin=subprocess.DEVNULL)
        if v.returncode != 0:
            raise OSError(v.stderr.strip()[:200] or f"exit {v.returncode}")
    except (OSError, subprocess.TimeoutExpired) as e:
        emitir({"ok": False, "errores": [f"codex no disponible: {e}"]})
        return 1
    try:
        antes = _estado_git()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        emitir({"ok": False, "errores": [f"no se pudo tomar la foto de git: {e}"]})
        return 1
    enc = encargos.tomar(encargos.cargar(ruta), "codex-exec", ahora())
    encargos.guardar(ruta, enc)
    permitidas = set(codex_rescate.rutas_imagen(enc))
    try:
        permitidas.add(str(ruta.resolve().relative_to(ROOT)))
    except ValueError:
        pass  # LAB_ENCARGOS_DIR fuera del repo (pruebas)
    salida = Path(tempfile.gettempdir()) / f"codex-exec-{a.encargo}.json"
    try:
        proc = subprocess.Popen(codex_rescate.comando(codex_rescate.prompt_para(enc), salida), cwd=ROOT,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=a.timeout)
            codigo, cola = proc.returncode, (out or "")[-1500:]
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)  # también sus hijos: nada escribe tarde
            proc.communicate()
            codigo, cola = None, f"codex exec superó {a.timeout} s"
    except OSError as e:
        codigo, cola = None, f"codex exec no arrancó: {e}"
    try:
        despues = _estado_git()
        ajenos = sorted(r for r in antes.keys() | despues.keys()
                        if antes.get(r) != despues.get(r) and r not in permitidas)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        ajenos = [f"<no se pudo comprobar git: {e}>"]
    enc = encargos.cargar(ruta)
    errores = codex_rescate.validar(enc)
    if ajenos:
        errores.append("Codex cambió archivos no permitidos: " + ", ".join(ajenos))
    if errores:
        if enc["estado"] == "generando" and enc["lock_owner"] == "codex-exec":
            encargos.marcar_fallo(enc, "codex-exec", f"{'; '.join(errores)} | exit={codigo}", ahora())
            encargos.guardar(ruta, enc)
        emitir({"ok": False, "errores": errores, "ajenos": ajenos, "exit": codigo, "salida": cola})
        return 6 if ajenos else 1
    emitir({"ok": True, "imagenes": enc["imagenes"]})
    return 0


# ── API ─────────────────────────────────────────────────────────────────────

def cmd_manifiesto_api(a) -> int:
    captions = {}
    for par in a.caption:
        plataforma, archivo = par.split("=", 1)
        captions[plataforma] = Path(archivo).read_text(encoding="utf-8").rstrip("\n")
    m = manifiesto.manifiesto_api(a.run_group, a.asset, sha256(ROOT / a.asset), captions, family_id=a.family)
    destino = ROOT / manifiesto.ruta_manifiesto(a.run_group)
    destino.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emitir({"manifiesto": manifiesto.ruta_manifiesto(a.run_group), "platforms": m["platforms"]})
    return 0


def cmd_manifiesto_verificacion(a) -> int:
    post_ids = dict(par.split("=", 1) for par in a.post)
    m = manifiesto.manifiesto_verificacion(a.run_group, post_ids)
    destino = ROOT / manifiesto.ruta_verificacion(a.run_group)
    destino.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emitir({"manifiesto": manifiesto.ruta_verificacion(a.run_group)})
    return 0


# ── teléfono ────────────────────────────────────────────────────────────────

def _evidencia(run_id: str) -> Path:
    return EVIDENCIA / run_id


def cmd_telefono_subir(a) -> int:
    from labkit import telefono
    local = ROOT / a.local
    remoto = f"/sdcard/Pictures/SabiduriaLab/{local.name}"
    emitir({"remoto": remoto, **telefono.subir(local, remoto)})
    return 0


def cmd_telefono_captura(a) -> int:
    from labkit import telefono
    emitir({"captura": str(telefono.captura(_evidencia(a.run) / f"{a.nombre}.png"))})
    return 0


def cmd_telefono_atras(a) -> int:
    from labkit import instagram_feed
    emitir({"captura": str(instagram_feed.atras(_evidencia(a.run), a.nombre))})
    return 0


def cmd_ig(a) -> int:
    from labkit import instagram_feed as ig
    from labkit import telefono
    ev = _evidencia(a.run)

    def leer_pie() -> str:
        if not a.pie:
            raise SystemExit("--pie es obligatorio en este paso")
        return Path(a.pie).read_text(encoding="utf-8").rstrip("\n")

    try:
        if a.paso == "abrir":
            if not a.subido_en:
                raise SystemExit("--subido-en es obligatorio en abrir (lo devuelve telefono-subir)")
            res = ig.abrir_nueva_publicacion(ev, a.subido_en)
        elif a.paso == "recorte":
            res = {"captura": ig.alternar_recorte(ev)}
        elif a.paso == "editor":
            res = {"captura": ig.siguiente(ev, "ig-02b-editor")}
        elif a.paso == "audio":
            res = ig.anadir_audio_sugerido(ev)
        elif a.paso == "detalles":
            res = {"captura": ig.detalles(ev)}
        elif a.paso == "pie":
            res = {"captura": ig.escribir_pie(leer_pie(), ev)}
        else:  # compartir: sale con 5 si el envío no queda confirmado, para conciliar antes de nada
            if not a.tema or a.publicaciones_antes is None:
                raise SystemExit("compartir exige --tema y --publicaciones-antes")
            res = ig.compartir(leer_pie(), a.tema, ev, a.publicaciones_antes)
            confirmado = res["estado"] == "confirmado"
            emitir({"ok": confirmado, **res})
            return 0 if confirmado else 5
    except (ig.PantallaInesperada, telefono.TelefonoError) as e:
        try:
            captura = telefono.captura(ev / f"ig-inesperada-{a.paso}.png")
        except telefono.TelefonoError:
            captura = None
        emitir({"ok": False, "tipo": type(e).__name__, "error": str(e), "captura": captura})
        return 4
    emitir({"ok": True, **res})
    return 0


def construir() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="lab.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preflight").set_defaults(func=cmd_preflight)
    p = sub.add_parser("lock-tomar")
    p.add_argument("--dueno", default="claude")
    p.set_defaults(func=cmd_lock_tomar)
    p = sub.add_parser("lock-soltar")
    p.add_argument("--dueno", default="claude")
    p.set_defaults(func=cmd_lock_soltar)

    p = sub.add_parser("encargo-nuevo")
    p.add_argument("--cell", action="append", required=True)
    p.add_argument("--family", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--do-not-use", action="append")
    p.add_argument("--formato", required=True, help="JSON, p. ej. '{\"nativo\":\"feed_single_image\",\"ancho\":1080,\"alto\":1350}'")
    p.add_argument("--prompt-file", required=True)
    p.add_argument("--restriccion", action="append")
    p.add_argument("--variantes", type=int, default=1)
    p.set_defaults(func=cmd_encargo_nuevo)
    sub.add_parser("encargos").set_defaults(func=cmd_encargos)
    p = sub.add_parser("encargo-revisar")
    p.add_argument("--encargo", required=True)
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--aprobado", action="store_true")
    grupo.add_argument("--rechazado", dest="aprobado", action="store_false")
    p.add_argument("--motivo", required=True)
    p.add_argument("--correccion")
    p.set_defaults(func=cmd_encargo_revisar)
    p = sub.add_parser("encargo-usado")
    p.add_argument("--encargo", required=True)
    p.add_argument("--run", required=True)
    p.set_defaults(func=cmd_encargo_usado)
    p = sub.add_parser("seleccionar")
    p.add_argument("--max", type=int, default=2)
    p.add_argument("--sin-telefono", action="store_true", help="descarta celdas android_native")
    p.set_defaults(func=cmd_seleccionar)

    p = sub.add_parser("codex-tomar")
    p.add_argument("--owner", choices=encargos.DUENOS_GENERACION, required=True)
    p.add_argument("--max", type=int, default=2)
    p.set_defaults(func=cmd_codex_tomar)
    p = sub.add_parser("codex-generado")
    p.add_argument("--encargo", required=True)
    p.add_argument("--owner", choices=encargos.DUENOS_GENERACION, required=True)
    p.add_argument("--imagen", action="append", required=True)
    p.set_defaults(func=cmd_codex_generado)
    p = sub.add_parser("codex-fallo")
    p.add_argument("--encargo", required=True)
    p.add_argument("--owner", choices=encargos.DUENOS_GENERACION, required=True)
    p.add_argument("--nota", required=True)
    p.set_defaults(func=cmd_codex_fallo)
    p = sub.add_parser("generar")
    p.add_argument("--encargo", required=True)
    p.add_argument("--timeout", type=int, default=600)
    p.set_defaults(func=cmd_generar)

    p = sub.add_parser("manifiesto-api")
    p.add_argument("--run-group", required=True)
    p.add_argument("--asset", required=True)
    p.add_argument("--caption", action="append", required=True, help="plataforma=ruta_del_pie")
    p.add_argument("--family")
    p.set_defaults(func=cmd_manifiesto_api)
    p = sub.add_parser("manifiesto-verificacion")
    p.add_argument("--run-group", required=True)
    p.add_argument("--post", action="append", required=True, help="plataforma=post_id")
    p.set_defaults(func=cmd_manifiesto_verificacion)

    p = sub.add_parser("telefono-subir")
    p.add_argument("--local", required=True)
    p.set_defaults(func=cmd_telefono_subir)
    for nombre, func in (("telefono-captura", cmd_telefono_captura), ("telefono-atras", cmd_telefono_atras)):
        p = sub.add_parser(nombre)
        p.add_argument("--run", required=True)
        p.add_argument("--nombre", required=True)
        p.set_defaults(func=func)
    p = sub.add_parser("ig")
    p.add_argument("paso", choices=("abrir", "recorte", "editor", "audio", "detalles", "pie", "compartir"))
    p.add_argument("--run", required=True)
    p.add_argument("--pie", help="archivo del pie (pie, compartir)")
    p.add_argument("--subido-en", help="subido_en que devolvió telefono-subir (abrir)")
    p.add_argument("--tema", help="tema que devolvió ig audio (compartir)")
    p.add_argument("--publicaciones-antes", type=int, help="publicaciones_antes que devolvió ig abrir (compartir)")
    p.set_defaults(func=cmd_ig)
    return ap


def main() -> int:
    a = construir().parse_args()
    try:
        return a.func(a)
    except encargos.EncargoError as e:
        print(f"encargo: {e}", file=sys.stderr)
        return 2
    except manifiesto.ManifiestoError as e:
        print(f"manifiesto: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
