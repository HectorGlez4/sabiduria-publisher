# Laboratorio ChatGPT → Claude, fase 1: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codex genera imágenes desde una cola de encargos y Claude encarga, revisa y publica por teléfono (feed de Instagram) y por API desde un único comando autorizado, con una ventana programada tres veces al día.

**Architecture:** Paquete `experiments/media-lab/labkit/` con módulos pequeños y puros donde se puede (encargos, colisión, selección, manifiesto, cerrojo, analizador de la interfaz del teléfono) y módulos finos de E/S (adb, `codex exec`, `gh`). `experiments/media-lab/lab.py` expone todo como subcomandos. Codex y Claude solo se comunican por `experiments/media-lab/encargos/*.json`.

**Tech Stack:** Python 3 del `.venv` del repo (pillow, requests), adb, scrcpy-server 4.1, `codex exec` de la app de ChatGPT, `gh`, tareas programadas de Claude.

**Spec:** `docs/superpowers/specs/2026-09-14-media-lab-chatgpt-claude-design.md`.

**Alcance de esta fase:** el feed de Instagram por teléfono (flujo ya probado a mano el 2026-09-14) y la ruta API completa. Stories, Facebook, Threads y TikTok por teléfono quedan para una fase 2 con su propio plan: hasta entonces la selección solo elige celdas de teléfono con `platform == "instagram"` y `native_format == "feed_single_image"`.

**Desviación de la spec:** el repo no usa pytest (no está en `.venv`). Las pruebas siguen el patrón de `tests/test_reglas.py`: script con `check()` y `FALLOS`, ejecutado con `.venv/bin/python tests/test_media_lab.py`.

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `experiments/media-lab/labkit/__init__.py` | Paquete vacío |
| `experiments/media-lab/labkit/encargos.py` | Estados, bloqueos, lectura y escritura de encargos. Puro salvo `cargar`, `guardar` y `listar`. |
| `experiments/media-lab/labkit/colision.py` | Resume la producción cercana: solo informativo, no frena la publicación. Parte pura y lectura de cola, publicados y `gh`. |
| `experiments/media-lab/labkit/seleccion.py` | Elige hasta 2 celdas elegibles. Puro. |
| `experiments/media-lab/labkit/manifiesto.py` | Construye y valida manifiestos API. Puro. |
| `experiments/media-lab/labkit/cerrojo.py` | Cerrojo de ventana en disco |
| `experiments/media-lab/labkit/telefono.py` | Primitivas adb y analizador del volcado de interfaz |
| `experiments/media-lab/labkit/instagram_feed.py` | Pasos del feed de Instagram, uno por llamada, con captura tras cada paso |
| `experiments/media-lab/labkit/codex_rescate.py` | Prompt, comando y validación de `codex exec` |
| `experiments/media-lab/lab.py` | CLI única |
| `experiments/media-lab/phone_clipboard.py` | Modificar: exponer `pegar()` y `sequence` |
| `experiments/media-lab/codex-resultado.schema.json` | Esquema de la respuesta final de `codex exec` |
| `experiments/media-lab/codex-heartbeat-prompt.md` | Prompt de solo generación para la automatización de Codex |
| `experiments/media-lab/claude-ventana-prompt.md` | Prompt de la tarea programada de Claude |
| `tests/test_media_lab.py` | Pruebas de todo lo anterior |
| `.gitignore` | Ignorar `.ventana.lock` |
| `.claude/settings.local.json` | Permisos para ejecución desatendida |

---

### Task 1: Comitear lo pendiente del laboratorio

**Files:**
- Commit: `experiments/media-lab/phone_clipboard.py`, `experiments/media-lab/assets/LAB-QUOTE-001/`, `experiments/media-lab/runs/LAB-QUOTE-001-INSTAGRAM.json`

- [ ] **Step 1: Comprobar que el run es JSON válido**

Run: `.venv/bin/python -c "import json;json.load(open('experiments/media-lab/runs/LAB-QUOTE-001-INSTAGRAM.json'));print('ok')"`
Expected: `ok`

- [ ] **Step 2: Commit y push**

```bash
git add experiments/media-lab/phone_clipboard.py experiments/media-lab/assets/LAB-QUOTE-001 experiments/media-lab/runs/LAB-QUOTE-001-INSTAGRAM.json
git commit -m "media lab claude: primera publicación nativa LAB-QUOTE-001 y portapapeles del teléfono

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

No añadir `experiments/media-lab/results/34787203020/` ni los `docs/*.md` sin seguimiento: no son de esta tarea.

---

### Task 2: Codex deja de publicar (prompt de solo generación)

**Files:**
- Create: `experiments/media-lab/codex-heartbeat-prompt.md`

- [ ] **Step 1: Escribir el prompt**

```markdown
Continúa el laboratorio Sabiduría de Bolsillo en /Users/hec/dev/sabiduriaPublisher con UN ÚNICO papel: generar imágenes encargadas por Claude.

Prohibido, sin excepciones: publicar en cualquier red, usar adb o el teléfono, lanzar workflows de GitHub, editar coverage.json, runs/, manifests/, progress.md, briefs/ o cualquier archivo fuera de los que se indican abajo. Claude gestiona toda la publicación.

1. Si no existe experiments/media-lab/lab.py o experiments/media-lab/encargos/, termina en silencio.
2. Ejecuta: .venv/bin/python experiments/media-lab/lab.py codex-tomar --owner codex-heartbeat --max 2
   Devuelve una lista JSON. Si está vacía, termina en silencio.
3. Para cada encargo devuelto, genera con tu generación de imágenes integrada una imagen por cada ruta de "rutas", siguiendo "prompt" y todas las "restricciones". Nunca pongas letras, números ni rótulos en la imagen. Guarda cada imagen exactamente en su ruta (PNG).
4. Si todas las imágenes quedaron guardadas, ejecuta:
   .venv/bin/python experiments/media-lab/lab.py codex-generado --encargo <encargo_id> --owner codex-heartbeat --imagen <ruta1> [--imagen <ruta2>]
   Si la generación falló o no puedes cumplir las restricciones, ejecuta:
   .venv/bin/python experiments/media-lab/lab.py codex-fallo --encargo <encargo_id> --owner codex-heartbeat --nota "<motivo breve>"
5. Comitea SOLO experiments/media-lab/encargos/<encargo_id>.json y las imágenes de ese encargo:
   git add <esas rutas exactas>
   git commit -m "media lab codex: encargo <encargo_id> <generado|fallo>"
   git fetch origin main && git rebase origin/main && git push origin HEAD:main
   Si el rebase entra en conflicto: git rebase --abort, deja el commit local y termina informando del conflicto. Nunca uses git reset --hard ni git add -A.
6. Mantente en silencio salvo fallo, conflicto o encargo imposible.
```

- [ ] **Step 2: Pedir al usuario que lo pegue**

Mensaje al usuario: abrir la app de ChatGPT → Codex → Automatizaciones → «Media lab hasta 1 octubre» → sustituir el prompt por el contenido de `experiments/media-lab/codex-heartbeat-prompt.md`, sin cambiar el horario. Esperar confirmación antes de seguir. Con `lab.py` aún inexistente, el paso 1 deja a Codex en reposo.

- [ ] **Step 3: Verificar el cambio sin editar el TOML**

Run: `grep -c "UN ÚNICO papel" ~/.codex/automations/media-lab-hasta-1-octubre/automation.toml`
Expected: `1`

- [ ] **Step 4: Commit**

```bash
git add experiments/media-lab/codex-heartbeat-prompt.md
git commit -m "media lab claude: prompt de solo generación para la automatización de Codex

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Portapapeles probado contra los bytes de scrcpy

**Files:**
- Create: `tests/test_media_lab.py`
- Modify: `experiments/media-lab/phone_clipboard.py`

- [ ] **Step 1: Escribir la prueba**

```python
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
    check(int.from_bytes(msg[10:14], "big") == len("¿Qué?".encode("utf-8")),
          "la longitud cuenta bytes UTF-8, no caracteres")


SECCIONES = [
    seccion_portapapeles,
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
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `TypeError: set_clipboard_message() got an unexpected keyword argument 'sequence'`

- [ ] **Step 3: Implementar**

En `experiments/media-lab/phone_clipboard.py`, sustituir `set_clipboard_message` y extraer `pegar()` de `main()`:

```python
def set_clipboard_message(text: str, paste: bool, sequence: int = 0) -> bytes:
    data = text.encode("utf-8")
    return struct.pack(">BQBI", TYPE_SET_CLIPBOARD, sequence, 1 if paste else 0, len(data)) + data


def pegar(text: str, paste: bool = True) -> None:
    """Pone `text` en el portapapeles del teléfono y, si `paste`, lo pega en el campo enfocado."""
    push = adb("push", SERVER_LOCAL, SERVER_REMOTE)
    if push.returncode != 0:
        raise RuntimeError(f"push del servidor falló: {push.stderr.strip()}")

    scid = random.randrange(1, 0x7FFFFFFF)
    port = 27200 + scid % 500
    fwd = adb("forward", f"tcp:{port}", f"localabstract:scrcpy_{scid:08x}")
    if fwd.returncode != 0:
        raise RuntimeError(f"adb forward falló: {fwd.stderr.strip()}")

    server = subprocess.Popen(
        ["adb", "-s", SERIAL, "shell",
         f"CLASSPATH={SERVER_REMOTE}", "app_process", "/", "com.genymobile.scrcpy.Server",
         SCRCPY_VERSION, f"scid={scid:08x}", "log_level=info", "tunnel_forward=true",
         "video=false", "audio=false", "control=true", "send_dummy_byte=false",
         "send_device_meta=false", "clipboard_autosync=false", "cleanup=false"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        # Con túnel forward, connect() funciona aunque nadie escuche todavía: el
        # socket se cierra al primer uso. Se reintenta hasta que el envío aguanta.
        deadline = time.time() + 15
        while True:
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=3)
                s.sendall(set_clipboard_message(text, paste=paste))
                time.sleep(1.5)
                s.settimeout(0.2)
                try:
                    if s.recv(1) == b"":
                        raise ConnectionResetError("servidor aún no escuchaba")
                except socket.timeout:
                    pass  # conexión viva: el mensaje llegó
                s.close()
                return
            except OSError:
                if time.time() > deadline or server.poll() is not None:
                    out = server.stdout.read() if server.poll() is not None else ""
                    raise RuntimeError(f"no se pudo hablar con scrcpy-server:\n{out}")
                time.sleep(0.5)
    finally:
        server.terminate()
        adb("forward", "--remove", f"tcp:{port}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=pathlib.Path)
    ap.add_argument("--no-paste", action="store_true", help="solo copiar, sin pegar")
    a = ap.parse_args()
    text = a.file.read_text(encoding="utf-8").rstrip("\n")
    pegar(text, paste=not a.no_paste)
    print(f"✓ {len(text)} caracteres enviados al portapapeles"
          f"{'' if a.no_paste else ' y pegados'}")
    return 0
```

- [ ] **Step 4: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: tres `✓` y `El laboratorio cumple sus contratos.`

- [ ] **Step 5: Commit**

```bash
git add tests/test_media_lab.py experiments/media-lab/phone_clipboard.py
git commit -m "media lab claude: probar el portapapeles contra los bytes de scrcpy

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Encargos

**Files:**
- Create: `experiments/media-lab/labkit/__init__.py` (vacío)
- Create: `experiments/media-lab/labkit/encargos.py`
- Modify: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir en `tests/test_media_lab.py`, antes de `SECCIONES`, y añadir `seccion_encargos,` a la lista:

```python
def seccion_encargos() -> None:
    print("\n2. Encargos: estados, bloqueos y archivo")
    import json
    import tempfile
    from datetime import datetime, timedelta, timezone
    from labkit import encargos as E

    t0 = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)

    def base(encargo_id: str = "ENC-20260915-001") -> dict:
        return E.nuevo(
            encargo_id, coverage_cell_ids=["CELL-011"], family_id="LAB-F01-001",
            brief_path="experiments/media-lab/briefs/LAB-F01-001.md", do_not_use=[],
            formato={"nativo": "feed_single_image", "ancho": 1080, "alto": 1350},
            prompt="Un astrolabio de latón sobre una mesa de madera", restricciones=["sin texto"],
            destino_assets="experiments/media-lab/assets/LAB-F01-001", ahora=t0)

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
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `ModuleNotFoundError: No module named 'labkit'`

- [ ] **Step 3: Implementar**

`experiments/media-lab/labkit/__init__.py`: archivo vacío.

`experiments/media-lab/labkit/encargos.py`:

```python
"""
Encargos de imagen: Claude los escribe, Codex los genera, Claude los revisa.

Un encargo es un JSON en experiments/media-lab/encargos/. Las transiciones viven
aquí y en ningún otro sitio, para que Codex (vía lab.py) y Claude no puedan
dejar un encargo en un estado que el otro no espera.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOCK_MINUTOS = 30
MAX_EN_COLA = 6
DUENOS_GENERACION = ("codex-heartbeat", "codex-exec")


class EncargoError(ValueError):
    pass


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def nuevo(encargo_id: str, *, coverage_cell_ids: list[str], family_id: str, brief_path: str,
          do_not_use: list[str], formato: dict, prompt: str, restricciones: list[str],
          destino_assets: str, ahora: datetime, variantes: int = 1, max_intentos: int = 2) -> dict:
    if not encargo_id.startswith("ENC-"):
        raise EncargoError("encargo_id debe empezar por ENC-")
    if not 1 <= variantes <= 2:
        raise EncargoError("variantes debe ser 1 o 2")
    if not destino_assets.startswith("experiments/media-lab/assets/"):
        raise EncargoError("destino_assets debe estar bajo experiments/media-lab/assets/")
    return {
        "encargo_id": encargo_id, "creado_en": _iso(ahora),
        "coverage_cell_ids": list(coverage_cell_ids), "family_id": family_id,
        "brief_path": brief_path, "do_not_use": list(do_not_use), "formato": formato,
        "variantes": variantes, "prompt": prompt, "restricciones": list(restricciones),
        "destino_assets": destino_assets.rstrip("/"), "max_intentos": max_intentos,
        "estado": "pedido", "lock_owner": None, "lock_expira": None,
        "imagenes": [], "intentos": [], "revision": None, "runs": [],
    }


def tomable(enc: dict, ahora: datetime) -> bool:
    if enc["estado"] == "pedido":
        return True
    return (enc["estado"] == "generando" and bool(enc["lock_expira"])
            and _dt(enc["lock_expira"]) <= ahora)


def tomar(enc: dict, owner: str, ahora: datetime) -> dict:
    if owner not in DUENOS_GENERACION:
        raise EncargoError(f"dueño desconocido: {owner}")
    if not tomable(enc, ahora):
        raise EncargoError(f"{enc['encargo_id']} no se puede tomar en estado {enc['estado']}")
    enc.update(estado="generando", lock_owner=owner,
               lock_expira=_iso(ahora + timedelta(minutes=LOCK_MINUTOS)))
    return enc


def _exigir_bloqueo(enc: dict, owner: str) -> None:
    if enc["estado"] != "generando" or enc["lock_owner"] != owner:
        raise EncargoError(f"{enc['encargo_id']} no está bloqueado por {owner}")


def marcar_generado(enc: dict, owner: str, imagenes: list[dict], ahora: datetime) -> dict:
    _exigir_bloqueo(enc, owner)
    if not imagenes:
        raise EncargoError("generado sin imágenes")
    for im in imagenes:
        faltan = {"ruta", "sha256", "ancho", "alto"} - set(im)
        if faltan:
            raise EncargoError(f"imagen sin {sorted(faltan)}")
    enc["imagenes"] = [{**im, "origen": owner, "generado_en": _iso(ahora)} for im in imagenes]
    enc["intentos"].append({"numero": len(enc["intentos"]) + 1, "resultado": "generado",
                            "origen": owner, "en": _iso(ahora)})
    enc.update(estado="generado", lock_owner=None, lock_expira=None)
    return enc


def marcar_fallo(enc: dict, owner: str, nota: str, ahora: datetime) -> dict:
    _exigir_bloqueo(enc, owner)
    enc["intentos"].append({"numero": len(enc["intentos"]) + 1, "resultado": "fallo",
                            "origen": owner, "nota": nota, "en": _iso(ahora)})
    siguiente = "pedido" if len(enc["intentos"]) < enc["max_intentos"] else "bloqueado"
    enc.update(estado=siguiente, lock_owner=None, lock_expira=None)
    return enc


def revisar(enc: dict, *, aprobado: bool, motivo: str, ahora: datetime,
            correccion: str | None = None) -> dict:
    if enc["estado"] != "generado":
        raise EncargoError(f"solo se revisa un encargo generado, no {enc['estado']}")
    if not aprobado and not correccion:
        raise EncargoError("un rechazo necesita la corrección para el siguiente intento")
    enc["revision"] = {"resultado": "aprobado" if aprobado else "rechazado",
                       "motivo": motivo, "revisado_en": _iso(ahora)}
    if aprobado:
        enc["estado"] = "aprobado"
        return enc
    enc["intentos"][-1]["imagenes_rechazadas"] = enc["imagenes"]
    enc["imagenes"] = []
    enc["restricciones"].append(correccion)
    enc["estado"] = "pedido" if len(enc["intentos"]) < enc["max_intentos"] else "bloqueado"
    return enc


def marcar_usado(enc: dict, run_id: str) -> dict:
    if enc["estado"] not in ("aprobado", "usado"):
        raise EncargoError(f"solo se usa un encargo aprobado, no {enc['estado']}")
    if run_id not in enc["runs"]:
        enc["runs"].append(run_id)
    enc["estado"] = "usado"
    return enc


def en_cola(todos: list[dict]) -> int:
    return sum(1 for e in todos if e["estado"] in ("pedido", "generando"))


def cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar(ruta: Path, enc: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(enc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def listar(carpeta: Path) -> list[tuple[Path, dict]]:
    if not carpeta.exists():
        return []
    pares = [(p, cargar(p)) for p in carpeta.glob("ENC-*.json")]
    return sorted(pares, key=lambda par: (par[1]["creado_en"], par[1]["encargo_id"]))


def siguiente_id(carpeta: Path, ahora: datetime) -> str:
    prefijo = f"ENC-{ahora.astimezone(timezone.utc):%Y%m%d}-"
    usados = [int(p.stem.rsplit("-", 1)[1]) for p in carpeta.glob(f"{prefijo}*.json")] if carpeta.exists() else []
    return f"{prefijo}{max(usados, default=0) + 1:03d}"
```

- [ ] **Step 4: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: todas las comprobaciones de las secciones 1 y 2 con `✓`, y termina en `El laboratorio cumple sus contratos.`

- [ ] **Step 5: Commit**

```bash
git add experiments/media-lab/labkit/__init__.py experiments/media-lab/labkit/encargos.py tests/test_media_lab.py
git commit -m "media lab claude: encargos con estados y bloqueos

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Colisión con producción

**Files:**
- Create: `experiments/media-lab/labkit/colision.py`
- Modify: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_colision,`:

```python
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
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `ImportError: cannot import name 'colision' from 'labkit'`

- [ ] **Step 3: Implementar**

`experiments/media-lab/labkit/colision.py`:

```python
"""
Producción cercana: qué está publicando producción alrededor de ahora.

Solo informativo (decisión del usuario, 2026-09-14): el laboratorio publica igual
y copia este motivo en el run como factor de confusión. La ventana es la del propio
publicador cuando recupera atrasos, 21 minutos; también se anotan `publicar` o
`hilos` en curso y las piezas atrasadas de la cola, que pueden salir en cualquier momento.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEPARACION = timedelta(minutes=21)
WORKFLOWS_PRODUCCION = ("publicar", "hilos")
ROOT = Path(__file__).resolve().parents[3]


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def motivo_espera(ahora: datetime, *, programadas: list[datetime], publicadas: list[datetime],
                  en_curso: list[str]) -> str | None:
    activos = sorted({w for w in en_curso if w in WORKFLOWS_PRODUCCION})
    if activos:
        return f"producción subiendo: {', '.join(activos)}"
    for t in sorted(publicadas, reverse=True):
        if timedelta(0) <= ahora - t < SEPARACION:
            return f"producción publicó hace {int((ahora - t).total_seconds() // 60)} min"
    for t in sorted(programadas):
        falta = t - ahora
        if falta <= timedelta(0):
            return f"producción atrasada desde {t:%H:%M} UTC: puede salir en cualquier momento"
        if falta < SEPARACION:
            return f"producción publica en {int(falta.total_seconds() // 60)} min"
    return None


def programadas_de_cola(cola: Path) -> list[datetime]:
    fuera = []
    for p in cola.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("status") == "ready" and d.get("publish_at"):
            fuera.append(_dt(d["publish_at"]))
    return sorted(fuera)


def publicadas_recientes(publicados: Path, ahora: datetime, horas: int = 3) -> list[datetime]:
    desde = ahora - timedelta(hours=horas)
    fuera = []
    for p in publicados.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in (d.get("results") or {}).values():
            t = (r or {}).get("published_at") if isinstance(r, dict) else None
            if t:
                cuando = _dt(t)
                if desde <= cuando <= ahora:
                    fuera.append(cuando)
    return sorted(fuera)


def workflows_en_curso() -> list[str]:
    nombres: list[str] = []
    for estado in ("in_progress", "queued"):
        r = subprocess.run(["gh", "run", "list", "--status", estado, "--limit", "20", "--json", "name"],
                           cwd=ROOT, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"gh run list falló: {r.stderr.strip()[:300]}")
        nombres += [x["name"] for x in json.loads(r.stdout)]
    return nombres
```

- [ ] **Step 4: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: secciones 1–3 con `✓` y `El laboratorio cumple sus contratos.`

- [ ] **Step 5: Commit**

```bash
git add experiments/media-lab/labkit/colision.py tests/test_media_lab.py
git commit -m "media lab claude: comprobación de colisión con producción

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Selección de celdas

> **Ampliada tras la revisión de calidad:** `seleccion.py` añade `API_FASE_1` (solo imágenes sueltas: feed y story de Facebook e Instagram, feed de Threads), acepta encargos `usado` para las celdas hermanas sin publicar, recibe `telefono_listo` y corta con `>=`. El código y las pruebas vigentes están en el commit que sigue a `bc0d857`; lo de abajo es la versión inicial.

**Files:**
- Create: `experiments/media-lab/labkit/seleccion.py`
- Modify: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_seleccion,`:

```python
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
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `ImportError: cannot import name 'seleccion' from 'labkit'`

- [ ] **Step 3: Implementar**

`experiments/media-lab/labkit/seleccion.py`:

```python
"""
Qué celdas salen en esta ventana.

Una celda es elegible si aún no se ha publicado, tiene un encargo aprobado y su
ruta está implementada. La segunda celda debe diferir de la primera en red o
ruta, y nunca es Facebook después de Instagram por teléfono (ni al revés):
Instagram ya copia sola esa foto en la Página.
"""
from __future__ import annotations

ESTADOS_ELEGIBLES = ("planned", "ready")
TELEFONO_FASE_1 = {("instagram", "feed_single_image")}


def _ruta_implementada(c: dict) -> bool:
    if c["publishing_route"] == "api":
        return True
    if c["publishing_route"] == "android_native":
        return (c["platform"], c["native_format"]) in TELEFONO_FASE_1
    return False


def elegibles(celdas: list[dict], todos_encargos: list[dict]) -> list[dict]:
    aprobadas = {cid for e in todos_encargos if e["estado"] == "aprobado" for cid in e["coverage_cell_ids"]}
    return [c for c in celdas
            if c["status"] in ESTADOS_ELEGIBLES and c["cell_id"] in aprobadas and _ruta_implementada(c)]


def _es_ig_telefono(c: dict) -> bool:
    return c["platform"] == "instagram" and c["publishing_route"] == "android_native"


def compatibles(a: dict, b: dict) -> bool:
    if a["platform"] == b["platform"] and a["publishing_route"] == b["publishing_route"]:
        return False
    if (_es_ig_telefono(a) and b["platform"] == "facebook") or (_es_ig_telefono(b) and a["platform"] == "facebook"):
        return False
    return True


def elegir(celdas: list[dict], todos_encargos: list[dict], max_celdas: int = 2) -> list[dict]:
    elegidas: list[dict] = []
    for c in elegibles(celdas, todos_encargos):
        if len(elegidas) == max_celdas:
            break
        if all(compatibles(c, e) for e in elegidas):
            elegidas.append(c)
    return elegidas
```

- [ ] **Step 4: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: secciones 1–4 con `✓`.

- [ ] **Step 5: Commit**

```bash
git add experiments/media-lab/labkit/seleccion.py tests/test_media_lab.py
git commit -m "media lab claude: selección de celdas por ventana

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Manifiestos API y cerrojo de ventana

> **Ampliada tras la revisión de calidad:** las historias se publican sin pie, un manifiesto no mezcla feed y stories, `run_group_id`, `..` y sha256 se validan estrictamente, hay `manifiesto_verificacion`/`ruta_verificacion` (`-verify.json`), `publish_api.py` no publica si el asset servido no coincide con `asset_sha256` (caché del CDN), `verify_api.py` verifica solo las redes presentes, y el cerrojo renueva para su dueño y solo lo suelta su dueño (`soltar(ruta, dueno)`). El código vigente está en el commit que sigue a `d471c6a`; lo de abajo es la versión inicial.

**Files:**
- Create: `experiments/media-lab/labkit/manifiesto.py`
- Create: `experiments/media-lab/labkit/cerrojo.py`
- Modify: `tests/test_media_lab.py`, `.gitignore`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_manifiesto_y_cerrojo,`:

```python
def seccion_manifiesto_y_cerrojo() -> None:
    print("\n5. Manifiestos API y cerrojo de ventana")
    import tempfile
    from datetime import datetime, timedelta, timezone
    from labkit import cerrojo, manifiesto as M

    asset = "experiments/media-lab/assets/LAB-F01-001/master-4x5.jpg"
    m = M.manifiesto_api("LAB-F01-001-API", asset, "ab" * 32,
                         {"facebook": "Pie FB", "threads": "Pie Threads"}, family_id="LAB-F01-001")
    check(m["route"] == "api" and m["audience"] == "public", "ruta api y audiencia pública explícitas")
    check(m["asset_url"] == M.RAW_BASE + asset, "asset_url apunta al raw de main")
    check(m["platforms"] == ["facebook", "threads"], "platforms sale de los pies")
    check(M.ruta_manifiesto("LAB-F01-001-API") == "experiments/media-lab/manifests/LAB-F01-001-API.json",
          "ruta que acepta el workflow media-lab")
    for args, label in ((("X-1", asset, "ab", {"facebook": "p"}), "run_group sin LAB-"),
                        (("LAB-X", "/tmp/a.jpg", "ab", {"facebook": "p"}), "asset fuera de assets"),
                        (("LAB-X", asset, "ab", {"tiktok": "p"}), "plataforma sin publicador"),
                        (("LAB-X", asset, "ab", {"threads": "x" * 501}), "Threads de más de 500"),
                        (("LAB-X", asset, "ab", {"instagram": "x" * 2201}), "Instagram de más de 2200"),
                        (("LAB-X", asset, "ab", {"facebook": ""}), "pie vacío")):
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
        cerrojo.soltar(lock)
        check(not lock.exists(), "soltar borra el cerrojo")
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `ImportError: cannot import name 'cerrojo' from 'labkit'`

- [ ] **Step 3: Implementar**

`experiments/media-lab/labkit/manifiesto.py`:

```python
"""Manifiestos para .github/workflows/media-lab.yml (experiments/media-lab/publish_api.py)."""
from __future__ import annotations

RAW_BASE = "https://raw.githubusercontent.com/HectorGlez4/sabiduria-publisher/main/"
PLATAFORMAS = ("facebook", "facebook_story", "instagram", "instagram_story", "threads")
LIMITES = {"instagram": 2200, "threads": 500}


class ManifiestoError(ValueError):
    pass


def manifiesto_api(run_group_id: str, asset_path: str, asset_sha256: str, captions: dict[str, str],
                   family_id: str | None = None) -> dict:
    if not run_group_id.startswith("LAB-"):
        raise ManifiestoError("run_group_id debe empezar por LAB-")
    if not asset_path.startswith("experiments/media-lab/assets/"):
        raise ManifiestoError("el asset debe estar bajo experiments/media-lab/assets/")
    if not captions:
        raise ManifiestoError("sin pies no hay plataformas")
    for plataforma, pie in captions.items():
        if plataforma not in PLATAFORMAS:
            raise ManifiestoError(f"publish_api.py no publica {plataforma}")
        if not pie.strip():
            raise ManifiestoError(f"pie vacío para {plataforma}")
        limite = LIMITES.get(plataforma)
        if limite and len(pie) > limite:
            raise ManifiestoError(f"pie de {plataforma} con {len(pie)} caracteres: máximo {limite}")
    m = {"run_group_id": run_group_id, "route": "api", "audience": "public",
         "asset_path": asset_path, "asset_sha256": asset_sha256,
         "asset_url": RAW_BASE + asset_path, "platforms": list(captions), "captions": dict(captions)}
    if family_id:
        m["family_id"] = family_id
    return m


def ruta_manifiesto(run_group_id: str) -> str:
    return f"experiments/media-lab/manifests/{run_group_id}.json"
```

`experiments/media-lab/labkit/cerrojo.py`:

```python
"""Una sola ventana a la vez: la programada y una sesión manual no se pisan."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ABANDONO = timedelta(minutes=90)


def tomar(ruta: Path, ahora: datetime, dueno: str) -> bool:
    if ruta.exists():
        try:
            desde = datetime.fromisoformat(json.loads(ruta.read_text(encoding="utf-8"))["desde"])
        except (OSError, ValueError, KeyError):
            desde = datetime.min.replace(tzinfo=timezone.utc)
        if ahora - desde < ABANDONO:
            return False
    ruta.write_text(json.dumps({"dueno": dueno, "desde": ahora.isoformat()}), encoding="utf-8")
    return True


def soltar(ruta: Path) -> None:
    ruta.unlink(missing_ok=True)
```

`.gitignore`: añadir al final la línea

```
experiments/media-lab/.ventana.lock
```

- [ ] **Step 4: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: secciones 1–5 con `✓`.

- [ ] **Step 5: Commit**

```bash
git add experiments/media-lab/labkit/manifiesto.py experiments/media-lab/labkit/cerrojo.py tests/test_media_lab.py .gitignore
git commit -m "media lab claude: manifiestos API y cerrojo de ventana

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Primitivas del teléfono y pasos del feed de Instagram

> **Endurecida tras la revisión de calidad (commit `8cc7eb8`):** volcados validados (`rm -f` + `dumped to`), estado que falla cerrado, `tapado`, `subir` con `subido_en` y MediaStore, cuenta leída en la barra superior, selección única con fecha de la miniatura, `detalles` separado de `escribir_pie`, cierre de teclado/desplegable verificado y `compartir(pie, tema, evidencia, publicaciones_antes)` con `estado` confirmado por aviso de subida y contador del perfil. El código vigente está en ese commit y en la segunda corrección que lo sigue (scrcpy con `power_on=false`, `confirmado` solo con los dos conteos, `fallido` y `error_tras_pulsar`, teclado ilegible sin pulsar Atrás y pruebas con teléfono simulado); lo de abajo es la versión inicial.

**Files:**
- Create: `experiments/media-lab/labkit/telefono.py`
- Create: `experiments/media-lab/labkit/instagram_feed.py`
- Modify: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba (solo la parte pura)**

Añadir antes de `SECCIONES` y registrar `seccion_interfaz,`:

```python
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


def seccion_interfaz() -> None:
    print("\n6. Lectura de la interfaz del teléfono")
    from labkit import instagram_feed, telefono

    nodos = telefono.nodos(XML_SELECTOR)
    check(all(n["bounds"] != (0, 0, 0, 0) for n in nodos), "descarta nodos invisibles de tamaño cero")
    s = telefono.buscar(XML_SELECTOR, texto="Suivant")
    check(s is not None and s["centro"] == (963, 170), "busca por texto exacto y calcula el centro")
    check(telefono.buscar(XML_SELECTOR, texto="Modifier le rognage") is not None, "también busca en content-desc")
    check(telefono.buscar(XML_SELECTOR, texto="Publier uniquement sur le profil") is None,
          "no devuelve un nodo invisible aunque coincida")
    check(telefono.buscar(XML_SELECTOR, empieza="Sélectionné Miniature") is not None, "busca por prefijo")
    check(telefono.textos(XML_SELECTOR).count("«Conténtese con hacer».") == 1,
          "textos() decodifica entidades y conserva «»")
    check(instagram_feed.primera_miniatura_seleccionada(XML_SELECTOR),
          "reconoce que la primera miniatura de la cuadrícula es la seleccionada")
    otro = XML_SELECTOR.replace('"Sélectionné Miniature', '"Désélectionné Miniature', 1).replace(
        'Désélectionné Miniature de la photo du 14 septembre 2026 9:29', 'Sélectionné Miniature de la photo du 14 septembre 2026 9:29')
    check(not instagram_feed.primera_miniatura_seleccionada(otro),
          "detecta cuando la seleccionada no es la primera")
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `ImportError: cannot import name 'instagram_feed' from 'labkit'`

- [ ] **Step 3: Implementar `telefono.py`**

```python
"""
Primitivas adb para el Samsung del laboratorio (serie R5CXB1AWYNF).

El volcado de uiautomator sirve para ENCONTRAR controles, pero puede ir con
retraso respecto a la pantalla: la evidencia de un estado final es siempre una
captura (screencap), nunca un volcado.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

SERIAL = "R5CXB1AWYNF"
REMOTO_UI = "/sdcard/lab-ui.xml"
_BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


class TelefonoError(RuntimeError):
    pass


def adb(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    r = subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise TelefonoError(f"adb {' '.join(args)}: {r.stderr.decode(errors='replace').strip()[:300]}")
    return r


def shell(cmd: str, timeout: int = 60) -> str:
    return adb("shell", cmd, timeout=timeout).stdout.decode(errors="replace")


def nodos(xml: str) -> list[dict]:
    fuera = []
    for el in ET.fromstring(xml.encode("utf-8")).iter("node"):
        m = _BOUNDS.fullmatch(el.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        if x2 <= x1 or y2 <= y1:
            continue
        fuera.append({"texto": el.get("text", ""), "desc": el.get("content-desc", ""),
                      "clase": el.get("class", ""), "bounds": (x1, y1, x2, y2),
                      "centro": ((x1 + x2) // 2, (y1 + y2) // 2)})
    return fuera


def buscar(xml: str, *, texto: str | None = None, contiene: str | None = None,
           empieza: str | None = None) -> dict | None:
    for n in nodos(xml):
        for valor in (n["texto"], n["desc"]):
            if not valor:
                continue
            if texto is not None and valor == texto:
                return n
            if contiene is not None and contiene in valor:
                return n
            if empieza is not None and valor.startswith(empieza):
                return n
    return None


def textos(xml: str) -> list[str]:
    return [n["texto"] for n in nodos(xml) if n["texto"]]


def volcado() -> str:
    shell(f"uiautomator dump --compressed {REMOTO_UI}", timeout=30)
    return adb("exec-out", "cat", REMOTO_UI).stdout.decode("utf-8", errors="replace")


def captura(destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(adb("exec-out", "screencap", "-p").stdout)
    return destino


def tocar(x: int, y: int) -> None:
    shell(f"input tap {x} {y}")


def tecla(codigo: int) -> None:
    shell(f"input keyevent {codigo}")


def combinacion(*codigos: int) -> None:
    shell("input keycombination " + " ".join(map(str, codigos)))


def lanzar(paquete: str) -> None:
    shell(f"monkey -p {paquete} -c android.intent.category.LAUNCHER 1")


def estado() -> dict:
    listo_adb = adb("get-state").stdout.decode().strip() == "device"
    despierto = "mWakefulness=Awake" in shell("dumpsys power")
    bloqueado = "isKeyguardShowing=true" in shell("dumpsys window")
    return {"adb": listo_adb, "despierto": despierto, "bloqueado": bloqueado,
            "listo": listo_adb and despierto and not bloqueado}


def subir(local: Path, remoto: str) -> str:
    adb("push", str(local), remoto, timeout=120)
    shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remoto}")
    remoto_sha = shell(f"sha256sum {remoto}").split()[0]
    local_sha = hashlib.sha256(local.read_bytes()).hexdigest()
    if remoto_sha != local_sha:
        raise TelefonoError(f"hash distinto en el teléfono: {remoto_sha} != {local_sha}")
    return local_sha
```

- [ ] **Step 4: Implementar `instagram_feed.py`**

```python
"""
Feed de Instagram por teléfono, un paso por llamada.

Cada función deja una captura en la carpeta de evidencia y termina. Quien dirige
(Claude) mira la captura antes de pedir el siguiente paso: nada de pulsaciones a
ciegas. Si un control no aparece, se lanza PantallaInesperada y no se toca nada más.
Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import phone_clipboard
from labkit import telefono

PAQUETE = "com.instagram.android"
MARCA = "sabiduriabolsillo"
ATRAS, CTRL_IZQ, TECLA_A = 4, 113, 29


class PantallaInesperada(RuntimeError):
    pass


def _nodo(xml: str, **kw) -> dict:
    n = telefono.buscar(xml, **kw)
    if n is None:
        raise PantallaInesperada(f"no aparece {kw}")
    return n


def _esperar(**kw) -> str:
    for _ in range(8):
        xml = telefono.volcado()
        if telefono.buscar(xml, **kw):
            return xml
        time.sleep(1.5)
    raise PantallaInesperada(f"no apareció {kw} tras 12 s")


def primera_miniatura_seleccionada(xml: str) -> bool:
    miniaturas = [n for n in telefono.nodos(xml)
                  if "Miniature de la photo" in n["desc"]
                  and n["desc"].startswith(("Sélectionné", "Désélectionné"))]
    if not miniaturas:
        return False
    primera = min(miniaturas, key=lambda n: (n["bounds"][1], n["bounds"][0]))
    return primera["desc"].startswith("Sélectionné")


def abrir_nueva_publicacion(evidencia: Path) -> Path:
    telefono.lanzar(PAQUETE)
    time.sleep(4)
    telefono.tocar(*_nodo(telefono.volcado(), texto="Profil")["centro"])
    xml = _esperar(contiene="Modifier le profil")
    if not telefono.buscar(xml, texto=MARCA):
        raise PantallaInesperada("el perfil activo no es @sabiduriabolsillo")
    telefono.tocar(*_nodo(xml, texto="Créer")["centro"])
    xml = _esperar(texto="Publication")
    telefono.tocar(*_nodo(xml, texto="Publication")["centro"])
    xml = _esperar(texto="Nouvelle publication")
    if not primera_miniatura_seleccionada(xml):
        raise PantallaInesperada("la foto preseleccionada no es la más reciente")
    return telefono.captura(evidencia / "ig-01-selector.png")


def alternar_recorte(evidencia: Path) -> Path:
    telefono.tocar(*_nodo(telefono.volcado(), texto="Modifier le rognage")["centro"])
    time.sleep(2)
    return telefono.captura(evidencia / "ig-02-recorte.png")


def siguiente(evidencia: Path, nombre: str) -> Path:
    telefono.tocar(*_nodo(telefono.volcado(), texto="Suivant")["centro"])
    time.sleep(4)
    return telefono.captura(evidencia / f"{nombre}.png")


def anadir_audio_sugerido(evidencia: Path) -> dict:
    chip = _nodo(telefono.volcado(), empieza="Audio suggéré.")
    x1, y1, x2, y2 = chip["bounds"]
    # El «+» del chip está a la derecha, en su tercio superior (medido el 2026-09-14).
    telefono.tocar(x2 - 59, y1 + round((y2 - y1) * 0.33))
    xml = _esperar(texto="Terminé")
    telefono.tocar(*_nodo(xml, texto="Terminé")["centro"])
    time.sleep(3)
    tema = chip["desc"].removeprefix("Audio suggéré.").split(". Appuyez")[0].strip()
    return {"tema": tema, "captura": str(telefono.captura(evidencia / "ig-03-audio.png"))}


def escribir_pie(pie: str, evidencia: Path) -> Path:
    xml = _esperar(contiene="Ajouter une légende")
    telefono.tocar(*_nodo(xml, contiene="Ajouter une légende")["centro"])
    time.sleep(2)
    telefono.combinacion(CTRL_IZQ, TECLA_A)
    phone_clipboard.pegar(pie, paste=True)
    time.sleep(2)
    if pie not in telefono.textos(telefono.volcado()):
        raise PantallaInesperada("el pie leído del teléfono no coincide con el archivo")
    telefono.tecla(ATRAS)
    time.sleep(3)
    return telefono.captura(evidencia / "ig-04-compositor.png")


def atras(evidencia: Path, nombre: str) -> Path:
    telefono.tecla(ATRAS)
    time.sleep(3)
    return telefono.captura(evidencia / f"{nombre}.png")


def compartir(pie: str, evidencia: Path) -> dict:
    xml = telefono.volcado()
    faltan = [k for k in ("Nouvelle publication", "Partager") if not telefono.buscar(xml, texto=k)]
    if faltan or pie not in telefono.textos(xml):
        raise PantallaInesperada(f"el compositor no está listo para compartir: {faltan or 'pie distinto'}")
    enviado = datetime.now(timezone.utc)
    telefono.tocar(*_nodo(xml, texto="Partager")["centro"])
    procesado = None
    for _ in range(60):
        time.sleep(1.5)
        if not telefono.buscar(telefono.volcado(), empieza="Publication sur sabiduriabolsillo"):
            procesado = datetime.now(timezone.utc)
            break
    return {"submitted_at": enviado.isoformat(timespec="seconds"),
            "processing_completed_at": procesado.isoformat(timespec="seconds") if procesado else None,
            "captura": str(telefono.captura(evidencia / "ig-05-publicado.png"))}
```

- [ ] **Step 5: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: secciones 1–6 con `✓`.

- [ ] **Step 6: Commit**

```bash
git add experiments/media-lab/labkit/telefono.py experiments/media-lab/labkit/instagram_feed.py tests/test_media_lab.py
git commit -m "media lab claude: primitivas del teléfono y pasos del feed de Instagram

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Rescate con `codex exec`

> **Ampliada tras la revisión de calidad:** `comando` carga la configuración de Codex del usuario (permiso explícito del usuario, 2026-09-14), el prompt delimita el encargo, `validar` rechaza rutas no pedidas, archivos no PNG, dimensiones distintas, imágenes de lado < 512 y orientación equivocada, `CODEX` admite `MEDIA_LAB_CODEX` y `family_id` solo acepta `[A-Za-z0-9_-]`. El código vigente está en el commit que sigue a `c59b2c0`; lo de abajo es la versión inicial.

**Files:**
- Create: `experiments/media-lab/labkit/codex_rescate.py`
- Create: `experiments/media-lab/codex-resultado.schema.json`
- Modify: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_codex,`:

```python
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
    check("adb" in p and "No publiques" in p, "el prompt prohíbe publicar y usar el teléfono")
    cmd = R.comando(p, pathlib.Path("/tmp/salida.json"))
    check(cmd[:2] == [R.CODEX, "exec"] and cmd[cmd.index("-s") + 1] == "workspace-write"
          and "--output-schema" in cmd and cmd[-1] == p, "comando con sandbox workspace-write y esquema")

    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d)
        check(R.validar(enc, raiz) == [f"estado pedido, se esperaba generado"], "no valida un encargo sin generar")
        ruta = raiz / "experiments/media-lab/assets/LAB-F01-001/ENC-20260915-003-v1.png"
        ruta.parent.mkdir(parents=True)
        ruta.write_bytes(b"png falso")
        E.tomar(enc, "codex-exec", t)
        E.marcar_generado(enc, "codex-exec", [{"ruta": str(ruta.relative_to(raiz)),
                                              "sha256": hashlib.sha256(b"png falso").hexdigest(),
                                              "ancho": 1, "alto": 1}], t)
        check(R.validar(enc, raiz) == [], "valida cuando el archivo existe y el hash coincide")
        ruta.write_bytes(b"cambiado")
        check(any("hash" in e for e in R.validar(enc, raiz)), "detecta un archivo cambiado")
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `ImportError: cannot import name 'codex_rescate' from 'labkit'`

- [ ] **Step 3: Implementar**

`experiments/media-lab/labkit/codex_rescate.py`:

```python
"""
Generación de rescate: Claude pide a Codex un encargo concreto con `codex exec`.

Solo se usa cuando una ventana no tiene imágenes aprobadas. Nunca se da por buena
la respuesta de Codex: se comprueba el archivo y su hash.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex"
ROOT = Path(__file__).resolve().parents[3]
ESQUEMA = ROOT / "experiments" / "media-lab" / "codex-resultado.schema.json"


def rutas_imagen(enc: dict) -> list[str]:
    return [f"{enc['destino_assets']}/{enc['encargo_id']}-v{n}.png" for n in range(1, enc["variantes"] + 1)]


def prompt_para(enc: dict) -> str:
    rutas = rutas_imagen(enc)
    imagenes = " ".join(f"--imagen {r}" for r in rutas)
    restricciones = "\n".join(f"- {r}" for r in enc["restricciones"] + enc["do_not_use"])
    return (
        f"Genera {len(rutas)} imagen(es) para el encargo {enc['encargo_id']} del laboratorio "
        "Sabiduría de Bolsillo, con tu generación de imágenes integrada.\n\n"
        f"Prompt:\n{enc['prompt']}\n\nRestricciones obligatorias:\n{restricciones}\n"
        "- Ninguna letra, número ni rótulo dentro de la imagen.\n\n"
        f"Guarda cada imagen como PNG exactamente en estas rutas del repo: {', '.join(rutas)}.\n"
        "Después ejecuta:\n"
        f".venv/bin/python experiments/media-lab/lab.py codex-generado --encargo {enc['encargo_id']} "
        f"--owner codex-exec {imagenes}\n\n"
        "No publiques nada. No uses adb ni el teléfono. No hagas git add, commit ni push. "
        "No edites ningún otro archivo. Responde con el JSON del esquema indicado."
    )


def comando(prompt: str, salida: Path) -> list[str]:
    return [CODEX, "exec", "-C", str(ROOT), "-s", "workspace-write",
            "--output-schema", str(ESQUEMA), "-o", str(salida), prompt]


def validar(enc: dict, raiz: Path = ROOT) -> list[str]:
    if enc["estado"] != "generado":
        return [f"estado {enc['estado']}, se esperaba generado"]
    errores = []
    if not enc["imagenes"]:
        errores.append("sin imágenes registradas")
    for im in enc["imagenes"]:
        p = raiz / im["ruta"]
        if not p.is_file():
            errores.append(f"no existe {im['ruta']}")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != im["sha256"]:
            errores.append(f"hash distinto en {im['ruta']}")
    return errores
```

`experiments/media-lab/codex-resultado.schema.json`:

```json
{
  "type": "object",
  "properties": {
    "encargo_id": {"type": "string"},
    "imagenes": {"type": "array", "items": {"type": "string"}},
    "ok": {"type": "boolean"},
    "nota": {"type": "string"}
  },
  "required": ["encargo_id", "imagenes", "ok", "nota"],
  "additionalProperties": false
}
```

- [ ] **Step 4: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: secciones 1–7 con `✓`.

- [ ] **Step 5: Commit**

```bash
git add experiments/media-lab/labkit/codex_rescate.py experiments/media-lab/codex-resultado.schema.json tests/test_media_lab.py
git commit -m "media lab claude: generación de rescate con codex exec

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: CLI `lab.py`

**Files:**
- Create: `experiments/media-lab/lab.py`
- Modify: `tests/test_media_lab.py`

- [ ] **Step 0: Seguimiento de la revisión de la tarea 9 en `codex_rescate.py`**

En `experiments/media-lab/labkit/codex_rescate.py`:
- En `validar`, justo antes de `if not p.is_file():`, rechazar enlaces: `if p.is_symlink(): errores.append(f"{im['ruta']} es un enlace simbólico"); continue`.
- En `_validar_imagen`, capturar también `Image.DecompressionBombError`: `except (OSError, UnidentifiedImageError, Image.DecompressionBombError):`.
- Aceptar una imagen cuadrada para un formato rectangular (se recorta bien después): la condición de orientación pasa a `if fa and fh and fa != fh and ancho != alto and (fh > fa) != (alto > ancho):` y el comentario lo dice.

Pruebas nuevas en `seccion_codex` (dentro del directorio temporal): un enlace simbólico en la ruta pedida hacia un PNG válido fuera de `destino_assets` → error «enlace simbólico»; un PNG 1024×1024 registrado como 1024×1024 para el formato 1080×1350 → `validar` sin errores. Quitar el redundante `E.EncargoError is not None and` de la comprobación de `family_id`. Commit aparte: `media lab claude: rescate rechaza enlaces y acepta imágenes cuadradas` con el trailer.

- [ ] **Step 1: Escribir la prueba (flujo de encargos por la CLI, sin teléfono ni red)**

Añadir antes de `SECCIONES` y registrar `seccion_cli,`:

```python
def seccion_cli() -> None:
    print("\n8. CLI lab.py: encargos de extremo a extremo en una carpeta temporal")
    import json
    import os
    import subprocess
    import tempfile
    from PIL import Image

    lab = ROOT / "experiments" / "media-lab" / "lab.py"
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "LAB_ENCARGOS_DIR": d}

        def lab_cmd(*args):
            r = subprocess.run([sys.executable, str(lab), *args], cwd=ROOT, env=env,
                               capture_output=True, text=True)
            return r.returncode, r.stdout, r.stderr

        prompt = pathlib.Path(d) / "prompt.txt"
        prompt.write_text("Un astrolabio de latón", encoding="utf-8")
        codigo, out, err = lab_cmd("encargo-nuevo", "--cell", "CELL-900", "--family", "LAB-TEST-001",
                                   "--brief", "b.md", "--formato", '{"ancho":1080,"alto":1350}',
                                   "--prompt-file", str(prompt), "--restriccion", "sin texto")
        check(codigo == 0, f"encargo-nuevo funciona {err[-200:]}")
        eid = json.loads(out)["encargo_id"]
        codigo, out, _ = lab_cmd("codex-tomar", "--owner", "codex-heartbeat", "--max", "2")
        tomados = json.loads(out)
        check(codigo == 0 and [t["encargo_id"] for t in tomados] == [eid], "codex-tomar devuelve el encargo con sus rutas")
        imagen = ROOT / tomados[0]["rutas"][0]
        imagen.parent.mkdir(parents=True, exist_ok=True)
        try:
            Image.new("RGB", (64, 80), (200, 180, 120)).save(imagen)
            codigo, out, err = lab_cmd("codex-generado", "--encargo", eid, "--owner", "codex-heartbeat",
                                       "--imagen", tomados[0]["rutas"][0])
            check(codigo == 0 and json.loads(out)[0]["ancho"] == 64, f"codex-generado mide la imagen {err[-200:]}")
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
```

- [ ] **Step 2: Ver que falla**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: sección 8 con `✗ encargo-nuevo funciona` (no existe `lab.py`) y `FALLARON`.

- [ ] **Step 3: Implementar `experiments/media-lab/lab.py`**

```python
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
```

- [ ] **Step 4: Ver que pasa**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: secciones 1–8 con `✓` y `El laboratorio cumple sus contratos.`

Run: `.venv/bin/python experiments/media-lab/lab.py --help`
Expected: lista de subcomandos sin error de importación.

- [ ] **Step 5: Corregir el commit del prompt de Codex (hallazgo de la revisión de la tarea 4)**

`codex-tomar --max 2` modifica dos encargos a la vez, pero el prompt vigente comitea uno y hace `git rebase` con el segundo aún modificado, y el rebase se niega a correr. En `experiments/media-lab/codex-heartbeat-prompt.md`, sustituir el paso 5 entero por:

```
5. Cuando hayas terminado con TODOS los encargos devueltos en el paso 2, comitea juntos, en un único commit, sus JSON y sus imágenes:
   git add <cada experiments/media-lab/encargos/<encargo_id>.json devuelto> <cada imagen guardada>
   git commit -m "media lab codex: encargos <id1> [<id2>] <generado|fallo>"
   git fetch origin main && git rebase origin/main && git push origin HEAD:main
   Si el rebase entra en conflicto: git rebase --abort, deja el commit local y termina informando del conflicto. Nunca uses git reset --hard ni git add -A.
```

Comitear el prompt con el resto de la tarea. Después pedir al usuario que vuelva a pegar el archivo completo en la automatización de Codex (mismo horario) y verificar sin editar el TOML:

Run: `python3 -c "import tomllib,pathlib;t=tomllib.loads(pathlib.Path('~/.codex/automations/media-lab-hasta-1-octubre/automation.toml').expanduser().read_text());print(t['prompt'].strip()==pathlib.Path('experiments/media-lab/codex-heartbeat-prompt.md').read_text().strip(), t['status'])"`
Expected: `True ACTIVE`

Hasta que el usuario lo pegue, Codex puede quedarse con encargos modificados sin comitear; no crear encargos reales antes de esa verificación.

- [ ] **Step 6: Commit y push**

```bash
git add experiments/media-lab/lab.py experiments/media-lab/codex-heartbeat-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: CLI única lab.py

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

---

### Task 11: Sondas supervisadas (sin publicar)

**Files:**
- Create (temporal, se borra al terminar): `experiments/media-lab/encargos/ENC-<hoy>-001.json` y su imagen

- [x] **Step 1: Comprobación previa real**

Run: `.venv/bin/python experiments/media-lab/lab.py preflight`
Expected: JSON con `telefono.listo: true` y `github: true`. `espera` puede traer un motivo, porque la sonda no publica.

- [x] **Step 2: Encargo de prueba**

```bash
printf 'Un astrolabio de latón sobre una mesa de madera oscura, luz lateral cálida, fondo liso, estilo fotográfico editorial' > /private/tmp/claude-501/-Users-hec-dev-sabiduriaPublisher/sonda-prompt.txt
.venv/bin/python experiments/media-lab/lab.py encargo-nuevo --cell SONDA --family LAB-SONDA-001 --brief sonda --formato '{"nativo":"feed_single_image","ancho":1080,"alto":1350}' --prompt-file /private/tmp/claude-501/-Users-hec-dev-sabiduriaPublisher/sonda-prompt.txt --restriccion "sin texto"
```

Expected: JSON con `"estado": "pedido"`. Anotar `encargo_id`.

- [x] **Step 3: Sonda de `codex exec` (gasta una generación incluida)**

Antes, anotar en `experiments/media-lab/findings.md` la salida de `/Applications/ChatGPT.app/Contents/Resources/codex --version`. La sonda confirma también que `lab.py generar` no informa archivos `ajenos`.

Run: `.venv/bin/python experiments/media-lab/lab.py generar --encargo <encargo_id> --timeout 600`

- Expected OK: `{"ok": true, "imagenes": [...]}`, con el PNG en `experiments/media-lab/assets/LAB-SONDA-001/`. Abrir la imagen y comprobar que no tiene texto.
- Si falla: guardar la salida en `experiments/media-lab/findings.md` bajo «Rescate codex exec: no disponible». La ventana sigue funcionando solo con la cola de Codex. Anotarlo en la spec (riesgo 1) y continuar.

- [x] **Step 4: Sonda del teléfono hasta el compositor, sin compartir**

Con una foto cualquiera ya en `Pictures/SabiduriaLab`, por ejemplo `LAB-QUOTE-001-gracian.png`:

```bash
.venv/bin/python experiments/media-lab/lab.py telefono-subir --local experiments/media-lab/assets/LAB-QUOTE-001/gracian-hacer-decir-4x5.png
.venv/bin/python experiments/media-lab/lab.py ig abrir --run SONDA-IG --subido-en <subido_en del paso anterior>
.venv/bin/python experiments/media-lab/lab.py ig recorte --run SONDA-IG
.venv/bin/python experiments/media-lab/lab.py ig editor --run SONDA-IG
.venv/bin/python experiments/media-lab/lab.py ig audio --run SONDA-IG
.venv/bin/python experiments/media-lab/lab.py ig detalles --run SONDA-IG
.venv/bin/python experiments/media-lab/lab.py ig pie --run SONDA-IG --pie experiments/media-lab/assets/LAB-QUOTE-001/caption-instagram.txt
```

Tras CADA comando, abrir la captura indicada en `captura` con Read y comprobar que muestra lo esperado antes de lanzar el siguiente: selector, 4:5 completo, editor, chip de música añadido, compositor con pie, música y «Partager» sin desplegable. Si hay desplegable: `lab.py telefono-atras --run SONDA-IG --nombre ig-04b-sin-desplegable`.

- [x] **Step 5: Salir sin publicar**

Pulsar atrás hasta la pantalla de descarte con `lab.py telefono-atras --run SONDA-IG --nombre salida-N` y mirar cada captura. En el diálogo de descarte, localizar el botón de descartar en la captura y pulsarlo con `adb shell input tap X Y`. Esa pulsación es solo de esta sonda supervisada, no del flujo desatendido. Confirmar en el perfil que no hay publicación nueva.

- [x] **Step 6: Limpiar**

```bash
rm -f experiments/media-lab/encargos/ENC-*-001.json
rm -rf experiments/media-lab/assets/LAB-SONDA-001 experiments/media-lab/results/codex-exec-ENC-*.json
```

Si `encargos/` queda vacío, borrarlo también. Nada de esto se comitea.

---

### Task 12: Permisos para ejecución desatendida

**Files:**
- Modify: `.claude/settings.local.json`

- [x] **Step 1: Añadir las reglas**

Añadir al array `permissions.allow`, sin tocar las existentes:

```json
"Bash(.venv/bin/python experiments/media-lab/lab.py *)",
"Bash(.venv/bin/python tests/test_media_lab.py)",
"Bash(gh workflow run media-lab*)",
"Bash(gh run view *)",
"Bash(gh run watch *)",
"Bash(gh run download *)",
"Bash(git add experiments/media-lab/*)",
"Bash(git fetch origin main)",
"Bash(git rebase origin/main)",
"Bash(git rebase --abort)",
"Bash(git push origin HEAD:main)"
```

- [x] **Step 2: Validar el JSON**

Run: `.venv/bin/python -c "import json;d=json.load(open('.claude/settings.local.json'));print(len(d['permissions']['allow']))"`
Expected: `32`, las 21 reglas existentes más 11.

`settings.local.json` es local y no se comitea.

---

### Task 13: Prompt de la ventana y ventana supervisada

**Files:**
- Create: `experiments/media-lab/claude-ventana-prompt.md`

- [x] **Step 1: Escribir el prompt de la ventana**

```markdown
Trabaja en el repo /Users/hec/dev/sabiduriaPublisher. Eres la ventana de publicación del laboratorio Sabiduría de Bolsillo. El diseño completo está en docs/superpowers/specs/2026-09-14-media-lab-chatgpt-claude-design.md: léelo si dudas.

## Reglas que no se rompen
- Códigos de salida de `lab.py`: 0 correcto; 1 fallo del paso; 2 argumentos o datos inválidos (JSON con `error`); 3 cerrojo no soltado; 4 pantalla inesperada o error del teléfono; 5 envío dudoso; 6 Codex cambió archivos no permitidos. Ante 2, corrige la llamada; ante 4 o 5, no toques más el teléfono en la ventana.
- Solo usa estos comandos: `.venv/bin/python experiments/media-lab/lab.py …`, `.venv/bin/python tests/test_media_lab.py`, `gh run list …`, `gh run view …`, `gh run watch …`, `gh run download …`, `gh workflow run media-lab…`, `git add experiments/media-lab/…`, `git commit …`, `git fetch origin main`, `git rebase origin/main`, `git rebase --abort`, `git push origin HEAD:main`. Cualquier otro comando abre un permiso que nadie contesta y te deja colgada. Para leer archivos y capturas usa Read; para editar JSON, Edit o Write.
- Nunca publiques sin PASS explícito de un agente independiente sobre la captura final (experiments/media-lab/visual-qa-gate.md).
- `lab.py preflight` devuelve en `espera` la producción cercana. Es solo informativo: no esperes ni saltes celdas por ello (decisión del usuario, 2026-09-14). Cópialo en `exposure_context.nearby_production_posts` del run y repítelo justo antes de cada Compartir o workflow para registrarlo.
- Nunca pulses nada a ciegas: tras cada `lab.py ig <paso>` abre la captura con Read y confirma que muestra lo esperado.
- Nunca reintentes un envío dudoso por la otra ruta; concilia contra la plataforma primero.
- A partir del 2026-10-02 no publiques: resume y pide al usuario que desactive esta tarea.

## Pasos
1. `lab.py lock-tomar --dueno programada`. Si devuelve `cerrojo: false`, termina: hay otra ventana en curso.
2. `git fetch origin main` y `git rebase origin/main`. Si falla: `git rebase --abort`, `lab.py lock-soltar --dueno programada` y termina informando.
3. `lab.py preflight`. Anota teléfono, github y espera. Si `telefono.listo` es false (bloqueado, dormido o desconectado), no toques el teléfono en toda la ventana: no intentes despertarlo ni desbloquearlo, salta las celdas `android_native`, sigue con las de API y di en el informe que el teléfono no estaba disponible para que el usuario lo desbloquee.
4. `lab.py encargos`. Si algún encargo está en `bloqueado` y no figura aún en experiments/media-lab/progress.md, anótalo allí (id, celdas, motivo del último intento) e inclúyelo en el informe: nadie más lo va a ver. Revisa cada encargo `generado`: abre sus imágenes con Read. Apruébalo (`lab.py encargo-revisar --encargo ID --aprobado --motivo "…"`) solo si la imagen es verosímil, respeta el brief y do_not_use y no tiene texto. Si no: `--rechazado --motivo "…" --correccion "…"`.
5. Reposición: crea encargos con `lab.py encargo-nuevo` (la carpeta de destino sale sola de `--family`: experiments/media-lab/assets/<family_id>) para las próximas celdas `planned` cuya red y formato estén implementados (`TELEFONO_FASE_1` y `API_FASE_1` en experiments/media-lab/labkit/seleccion.py) de experiments/media-lab/coverage.json con brief verificado, sin mezclar en un mismo encargo celdas de feed (4:5) y de story (9:16), hasta como máximo 6 en cola. El prompt de imagen va en un archivo temporal dentro de experiments/media-lab/results/. Si `lab.py seleccionar` devuelve [] y hay algún encargo en `pedido`, `lab.py generar --encargo <el más antiguo>` una sola vez, lanzándolo con el tiempo máximo de la herramienta Bash (`timeout: 600000`) y sin ejecutar la batería de pruebas mientras corre (escribe en el repo y la guardia lo tomaría por cambios ajenos); si genera, revísalo como en el paso 4. Si sale con código 6 (Codex cambió archivos no permitidos), no generes más en esta ventana, no comitees esos cambios y enumera los archivos en el informe para el usuario.
6. `lab.py seleccionar --max 2`, añadiendo `--sin-telefono` si `telefono.listo` era false. Si devuelve [], salta al paso 8.
7. Para cada celda elegida, en orden, dejando al menos 21 min entre la primera publicación y la segunda (vuelve a pasar `lab.py preflight`). Antes de cada celda renueva el cerrojo con `lab.py lock-tomar --dueno programada`; si devuelve `cerrojo: false`, otra sesión tomó el relevo: no publiques más celdas y salta al paso 9:
   a. Crea el máster final con texto determinista (experiments/media-lab/render_overlay.py o src/render/quote_card.py), el pie (verificado contra el brief, ≤2200 en Instagram, ≤500 en Threads) y el run JSON copiando experiments/media-lab/run-template.json.
   b. Teléfono (instagram/feed_single_image): `lab.py telefono-subir --local <máster>` (anota `subido_en`); `lab.py ig abrir --run RUN --subido-en <subido_en>` (anota `publicaciones_antes`); `ig recorte --run RUN` y confirma en la captura que la imagen está completa en 4:5 (el volcado no lo muestra); `ig editor --run RUN`; `ig audio --run RUN` (anota `tema`); `ig detalles --run RUN`; `ig pie --run RUN --pie <archivo>`. Mira cada captura antes del paso siguiente. Si un paso sale con código 4 (`PantallaInesperada`, `BorradorPendiente`, `TelefonoNoListo` o `TelefonoError`), no toques más el teléfono en esta ventana: regístralo con su captura y sigue con API.
      API: `lab.py manifiesto-api --run-group LAB-…-API --asset <máster> --caption facebook=<archivo> …`; commit y push del máster y el manifiesto (sección C de la spec) para que asset_url exista; la vista previa para QA es el máster con el pie.
   c. QA: lanza un agente independiente con las rutas de captura final, máster, pie y visual-qa-gate.md, y exige «VERDICT: PASS»; el revisor solo comprueba que no haya texto ni imagen cortados o tapados. Si FAIL, corrige una vez y repite. Si vuelve a FAIL, abandona la celda (en teléfono: `lab.py telefono-atras` hasta salir, mirando capturas; nunca descartes a ciegas) y regístralo: pon la celda en `"status": "blocked"` con `reason_if_blocked_or_unsupported` en coverage.json para que la siguiente ventana no la vuelva a elegir.
   d. `lab.py preflight` y anota `espera` (producción cercana) en el run. No frena la publicación.
   e. Publica. Teléfono: `lab.py ig compartir --run RUN --pie <archivo> --tema <tema> --publicaciones-antes <n>`, añadiendo `--produccion-cercana` si el último `preflight` trajo `espera` distinto de null (una publicación de producción cercana puede cuadrar el contador por casualidad). Si sale con código 4 porque siguen visibles sugerencias del teclado o un desplegable, es un bloqueo esperado: no reintentes en esta ventana. Si sale con código 5 (`estado` distinto de `confirmado`: `confirmado_sin_conteo`, `conteo_no_cuadra`, `sin_banner`, `timeout`, `fallido` o `error_tras_pulsar`), el envío es dudoso: no repitas nada; mira `captura` y `captura_antes`, comprueba el perfil con `lab.py telefono-captura` y concilia antes de registrar. API: `gh workflow run media-lab -f manifest=<ruta>`, sigue el run con `gh run watch`, descarga el resultado con `gh run download`. Con los post_id del resultado: `lab.py manifiesto-verificacion --run-group <el mismo> --post facebook=<id> …` (solo feed: si la celda es solo de historias, sáltate este paso de verificación), commit y push de ese manifiesto, y `gh workflow run media-lab-verify -f manifest=<ruta>`.
   f. Verifica la publicación en directo (URL/ID, identidad, audiencia, música). En Instagram por teléfono, la copia automática en Facebook va en `publication.cross_posting` del run.
   g. Actualiza el run, la celda de coverage.json, `lab.py encargo-usado --encargo ID --run RUN` y experiments/media-lab/progress.md.
8. Métricas: captura las instantáneas vencidas (24 h, 72 h, 7 d; Stories unas 6 h y antes de caducar) de los runs publicados y guárdalas en sus runs.
9. Commit solo de rutas propias: `git add experiments/media-lab/<rutas concretas>`, `git commit -m "media lab claude: …"`, `git fetch origin main`, `git rebase origin/main` y `git push origin HEAD:main`. Si hay conflicto: `git rebase --abort` e informa.
10. `lab.py lock-soltar --dueno programada`.

## Informe
Si no publicaste nada y no hubo fallo, basta con una línea con el motivo (por ejemplo, ningún encargo aprobado). Si publicaste, da celda, red, ruta, URL y veredicto de QA. Si algo bloqueó, di qué y qué decisión hace falta del usuario.
```

- [x] **Step 2: Ventana supervisada con el usuario presente**

Ejecutar el prompt anterior a mano en esta sesión, paso a paso, usando `--dueno manual` en lugar de `--dueno programada` en `lock-tomar` y `lock-soltar`, con al menos un encargo aprobado para una celda `instagram/feed_single_image/android_native` de `coverage.json`. Comprobar antes que ninguna celda anterior en `coverage.json` tiene encargo aprobado: `seleccionar` sigue ese orden y elegiría primero una celda de API. Si hace falta, antes crear el encargo y esperar a la automatización de Codex o usar `lab.py generar`. Sin confirmación humana antes del paso 7e (decisión del usuario, 2026-09-14): basta el PASS del agente revisor.

- [x] **Step 3: Commit**

```bash
git add experiments/media-lab/claude-ventana-prompt.md
git commit -m "media lab claude: prompt de la ventana de publicación

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14: Tarea programada y documentación

**Files:**
- Modify: `experiments/media-lab/PLAN.md`, `experiments/media-lab/START-HERE.md`, `experiments/media-lab/schedule-preflight.md`, `experiments/media-lab/progress.md`

- [x] **Step 1: Crear la tarea programada**

Llamar a `mcp__scheduled-tasks__create_scheduled_task` con:
- `taskId`: `sabiduria-media-lab`
- `title`: `Laboratorio: ventana de publicación`
- `description`: `Ventana del laboratorio: revisa encargos de Codex, hace QA y publica hasta 2 celdas por teléfono o API.`
- `cronExpression`: `40 10,15,20 * * *`
- `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`

Decir al usuario que solo corre con la app de Claude abierta y que, si está cerrada, corre al abrirla.

- [x] **Step 2: Actualizar la documentación del laboratorio**

Añadir al principio de `experiments/media-lab/START-HERE.md`, `PLAN.md` y `schedule-preflight.md` este bloque:

```markdown
> **Reparto vigente desde 2026-09-14:** Codex (automatización `media-lab-hasta-1-octubre`) solo genera imágenes desde `encargos/`. Claude encarga, revisa, hace QA y publica por teléfono y API desde la tarea programada `sabiduria-media-lab` (10:40, 15:40 y 20:40). Diseño: `docs/superpowers/specs/2026-09-14-media-lab-chatgpt-claude-design.md`. Todo pasa por `experiments/media-lab/lab.py`.
```

En `progress.md`, sustituir la viñeta que empieza por «Temporary Codex heartbeat» por:

```markdown
- Codex heartbeat `media-lab-hasta-1-octubre` now only generates images from `encargos/` (10:10, 15:10, 20:10 until 2026-10-01). Claude scheduled task `sabiduria-media-lab` (10:40, 15:40, 20:40) owns selection, QA and all phone/API publishing, up to 2 cells per window. Phase 1 phone route: Instagram feed only.
```

- [x] **Step 3: Pruebas finales**

Run: `.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

- [x] **Step 4: Commit y push**

```bash
git add experiments/media-lab/START-HERE.md experiments/media-lab/PLAN.md experiments/media-lab/schedule-preflight.md experiments/media-lab/progress.md
git commit -m "media lab claude: documentar el reparto Codex genera / Claude publica

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

---

### Task 10c: `lab.py` robusto para ventanas desatendidas

Resultado de la revisión de calidad de la tarea 10 (commits `75f2691` y `c7efbe2`), implementado en un único commit posterior:

- `generar` con `--timeout` 420 por defecto y manejadores de SIGTERM/SIGHUP/SIGINT que matan el grupo de Codex y dejan el encargo en `fallo` o invalidado; salida de Codex a archivo temporal, sin tuberías que puedan colgarse.
- Guardia (`labkit/guardia.py`): además de `git status`, vigila `.claude/settings*.json`, el `.env` raíz y `experiments/media-lab/.env*`, `.git/config`, `.git/hooks/`, los `.pyc` del laboratorio, el cerrojo de ventana y todo `assets/`; ignora `.DS_Store`. Seguimiento: la guardia también corre si una señal interrumpe `generar` (código 6 si hubo cambios), el grupo de Codex se mata también tras una salida normal, el temporal de escritura atómica del encargo está permitido, `-o` va en un directorio temporal propio y los errores de argumentos salen como JSON.
- `codex-generado` solo acepta las rutas pedidas, rechaza enlaces y no imágenes y valida con `codex_rescate.validar` antes de guardar; `encargo-revisar --aprobado` también valida.
- `encargos.invalidar` para encargos `generado` por `codex-exec` que fallan la guardia o la validación.
- `manifiesto-api` valida la ruta antes de leer, no sobrescribe manifiestos y parsea `plataforma=valor` con error claro.
- `--run`, `--nombre` y `--encargo` validados; todos los errores previsibles salen como JSON con código 2; los comandos de teléfono salen con 4 y captura.
- `encargo-nuevo` valida las celdas contra `coverage.json` (existen, `planned`/`ready`, ruta implementada, un solo formato, sin encargo activo) y `encargos.nuevo` exige `formato` con `ancho`/`alto` y prompt no vacío.
- `lock-tomar`/`lock-soltar` exigen `--dueno programada|manual`; `lock-soltar` sale con 3 si no suelta.
- Prompt de Codex: si `codex-generado` falla, `codex-fallo`; solo se comitean imágenes de encargos generados. El usuario debe volver a pegarlo después de este commit.
- Pruebas en proceso de todos los comandos sin teléfono y de `generar` con un Codex falso (éxito, cambios ajenos → 6, tiempo agotado).

### Task 10e: Menores de la revisión de 10d (antes de la tarea 14)

- [x] `observacion_de_volcado` devuelve el texto y los bounds del aviso de fallo que coincidió, y `compartir` los copia en `avisos`, para conciliar en segundos un `fallido` provocado por un texto corto ajeno (p. ej. un botón «Réessayer» del feed). Opcional: un texto corto que no está junto a un aviso solo corta la observación si aparece en dos volcados válidos seguidos.
- [x] **Bloqueante (sonda del 2026-09-14):** `escribir_pie` devolvió `ok` y la captura `ig-04-compositor.png` mostraba el desplegable de hashtags tapando la música y «Partager»: Instagram lo abre unos segundos después de pegar, y el volcado se hizo antes. Un «atrás» manual lo cerró sin tocar el pie. Arreglo: tras pegar, esperar a que la pantalla se estabilice (p. ej. hasta 3 volcados frescos seguidos, separados 2-3 s, sin teclado ni desplegable) y cerrar con «atrás» cada vez que aparezca, con el mismo tope de 2; hacer la captura solo después. Prueba con teléfono simulado: el desplegable aparece en el segundo volcado tras pegar → exactamente un «atrás» y compositor limpio.
- [x] `abrir`: con la cortina de notificaciones desplegada no ve Instagram y sale con 4 (bien, falla cerrado). Valorar `cmd statusbar collapse` antes de buscar Instagram (no despierta ni desbloquea).
- [x] `generar`: contador aparte `no_lanzados` en el encargo; cada fallo de `Popen` o señal antes del lanzamiento lo incrementa y, al llegar a 3, el encargo pasa a `bloqueado` con nota (evita bucles infinitos si `Popen` falla siempre igual, p. ej. E2BIG por un prompt demasiado largo en argv).

### Task 10f: El detector del desplegable de hashtags no lo ve (bloqueante antes de la tarea 14)

> **Hecha en `d51ffb7` y `f00fff3`** (spec ✅; calidad aprobada con menores; comprobada con los dos `dumpsys window windows` reales: abierto → solo `PopupWindow:de536c5` con frame (0,1448,1080,2205); cerrado → nada). Implementación final: `ventanas_emergentes_de` exige el prefijo `PopupWindow:` y cuenta la ventana por `package=` del bloque o `mParentWindow`, visible salvo `isVisible=false` (o `mHasSurface=false` si falta), frame `frame=`/`mFrame=` o None (cuenta); `emergente_desplegable`/`parece_desplegable` (≥ 90 % del ancho) deciden; `_desplegable_abierto` sustituye a `_hay_que_cerrar`. Menores pendientes: añadir `package=com.instagram.android` al bloque `KHCD` del test; prueba «sin isVisible y mHasSurface=false no cuenta»; docstring de `ventanas_emergentes_de` remite a `emergente_desplegable`.

> **Diagnóstico (sonda SONDA-10F, 2026-09-14 21:46, sin publicar):** el desplegable de sugerencias es una **ventana aparte** que `uiautomator dump` no incluye. Volcado fresco y captura tomados a la vez: el volcado muestra el compositor limpio (`caption_add_on_recyclerview` con «Sondage»/«Invite», `music_track_title`, `share_footer_button` pulsable y sin tapar), la captura muestra el desplegable encima. En `adb shell dumpsys window windows` aparece solo mientras está abierto:
> ```
> Window #11 Window{49fd424 u0 PopupWindow:de536c5}:
>   mAttrs={(0,1448)(1080xwrap) … ty=APPLICATION_PANEL …}
>   mParentWindow=Window{e654062 u0 com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity} mLayoutAttached=true
>   Frames: … frame=[0,1448][1080,2205] …
>   isVisible=true
> ```
> Al cerrarlo desaparece. Las ventanas `KHCD.*` (1 px de ancho, `APPLICATION_ATTACHED_DIALOG`) están en ambos estados y no cuentan. Consecuencia: `compositor_listo` también da el compositor por bueno y `compartir` pulsaría el centro de `share_footer_button`, que el desplegable tapa (inserta un hashtag en vez de publicar; no falla cerrado).
>
> **Arreglo:** `telefono.ventanas_emergentes(paquete)` lee `dumpsys window windows` y devuelve las ventanas `PopupWindow:*` con `isVisible=true` cuyo `mParentWindow` es de `paquete`, con su `frame`. Lector puro `ventanas_emergentes_de(texto_dumpsys, paquete)` probado con el fragmento real de arriba (y el mismo bloque sin la ventana). `_hay_que_cerrar` y `compositor_listo`/`compartir` las consultan: una emergente de Instagram cuyo `frame` se solapa con la fila de música o con «Partager» cuenta como desplegable abierto (cerrar con «atrás» en `escribir_pie`; en `compartir`, `PantallaInesperada` sin tocar). Si `dumpsys` falla, se falla cerrado. El detector por nodos `hay_desplegable_hashtags` se mantiene.

- [x] Ventana supervisada de CELL-018 (2026-09-14 21:35): con el arreglo de 10e, `ig pie` esperó sus volcados limpios y devolvió `ok`, pero la captura `ig-04-compositor.png` mostraba el desplegable de hashtags abierto sobre la música y «Partager» (filas «#historiadelatecnología … publications publiques»). No es solo un problema de tiempos: `hay_desplegable_hashtags(xml, paquete=PAQUETE)` no lo detecta en el volcado. Un `telefono-atras` manual lo cerró. Riesgo: `compartir` tampoco lo vería y podría pulsar sobre una fila del desplegable. Pasos: (1) sonda supervisada que vuelque la jerarquía CON el desplegable abierto (el intento de esta ventana falló por la sintaxis de zsh) y ver paquete, clase y texto de sus filas, o si el volcado sale sin ellas (ventana de sistema, volcado desfasado); (2) detector con volcados reales como fixture (podados); (3) si el volcado no lo muestra nunca, detección alternativa: comparar los bounds del botón «Partager» y de la fila de música con los esperados del compositor limpio (el desplegable los empuja o los oculta), o exigir que «Partager» y la fila de música estén en el volcado y visibles antes de dar el compositor por bueno; (4) prueba con teléfono simulado del fixture real.

> **Hecha en `8df33f3` y `6da5b38`** la tarea 10e (revisión de spec ✅; calidad aprobada con menores). Menores pendientes, no bloquean:
> - m-1: en `escribir_pie`, si el desplegable se cierra solo, el volcado de confirmación cuenta como limpio sin reiniciar la cuenta; con un desplegable intermitente se aceptan 3 limpios no seguidos. Reiniciar la cuenta sin pulsar (el plazo de 60 s acota el bucle) o corregir el docstring. Prueba `[comp, comp] + [D, comp]*N` con el reloj rápido.
> - m-2: la prueba e16 no discrimina (`nuevo()` ya crea `no_lanzados: 0`): liberar antes de `marcar_generado` y comprobar también que se borra `nota_no_lanzado`.
> - m-3: el plazo solo se comprueba al empezar cada vuelta; una vuelta con 3 volcados lentos puede pasar de 60 s. Decirlo en el docstring, como `_esperar_que`.

> **Hecha en `a93094f` y `cb0220a`** la tarea 10d (incluye `marcar_fallo(bloquear=)`: un encargo `generando` con cambios ajenos queda `bloqueado`).

### Task 10d: Menores de la revisión de 10b

- [ ] `observacion_de_volcado(xml, boton_bounds, banners_previos)`: conservar los bounds del aviso «Publication sur…» vistos en volcados anteriores y contar un texto de fallo junto a ellos; contar también un texto de fallo corto (≤ 80 caracteres) en cualquier parte de la pantalla de Instagram. Actualizar la prueba que hoy da por bueno no detectar un aviso bajo 600 px.
- [ ] `generar`: si Codex no llegó a lanzarse (fallo de `Popen` o señal antes del lanzamiento), liberar el encargo sin sumar intento ni bloquear, aunque haya `ajenos` (se informan y sale con 6). Prueba del caso «no lanzado con ajenos».
- [ ] `generar`: si salta una excepción después del lanzamiento, pasar la guardia y `_deshacer(bloquear=bool(ajenos))` antes de relanzar.
- [ ] G-2: los errores de `_liberar` salen por stderr o en la nota de la excepción.
- [ ] `compartir`: la captura de error best-effort usa un tiempo de espera corto (≤ 10 s).
- [ ] `phone_clipboard._parar`: `server.wait(timeout=1)` protegido tras cerrar stdout.

### Task 10b: Seguimiento de la revisión de la tarea 8 (antes de las sondas)

> **Hecha en `ab9779d`** (M-1…M-8, G-1, G-2; los lectores puros viven en `labkit/instagram_pantallas.py`, reexportados desde `instagram_feed.py`).

Menores aprobados sin bloquear en la re-revisión de `98f7c77`. Hacerlos después de la tarea 10 y antes de la tarea 11, con pruebas de teléfono simulado donde aplique:

- [ ] **M-1:** `compartir(..., produccion_cercana: bool = False)`; si es True y el resultado sería `confirmado`, bajarlo a `confirmado_sin_conteo`. `lab.py ig compartir` recibe `--produccion-cercana` y la ventana lo pasa cuando `preflight` trae `espera`.
- [ ] **M-2:** en `observacion_de_volcado`, buscar los textos de fallo solo en la zona del aviso de subida (borde inferior ≤ 600 px o junto al nodo «Publication sur…»), no en pies ajenos del inicio.
- [ ] **M-3:** en el `except` de `compartir`, captura best-effort `ig-05-error.png` envuelta en su propio `try/except Exception`.
- [ ] **M-4:** `telefono.captura` convierte `OSError` de `mkdir`/`write_bytes` en `TelefonoError`; `cmd_ig` valida `--subido-en` con `datetime.fromisoformat` y sale con `SystemExit` claro si no parsea.
- [ ] **M-5:** documentar en la ventana que un código 4 en `ig compartir` por sugerencias del teclado es un bloqueo esperado (falla cerrado).
- [ ] **M-6:** pruebas nuevas: teclado True y luego None → exactamente un «atrás» y `PantallaInesperada`; un «#» de otra app con teclado cerrado → ningún «atrás»; `abrir` con pantalla de arranque y luego inicio con Profil → exactamente un toque en Profil.
- [ ] **M-7:** en `phone_clipboard._parar`, `communicate(timeout=5)` también tras `kill()`, ignorando un segundo `TimeoutExpired`.
- [ ] **G-1 (revisión de 10c):** en `generar`, marcar `vivo["lanzado"] = True` tras `Popen`; si llega una señal antes del lanzamiento y no hay cambios ajenos, devolver el encargo a `pedido` sin sumar intento (`encargos.liberar(enc, owner)` nuevo, con prueba).
- [ ] **G-2 (revisión de 10c):** si entre `tomar` y el lanzamiento de Codex salta una excepción (`_permitidas`, `mkdtemp`), llamar a `_deshacer(ruta, f"error antes de lanzar Codex: {e}", bloquear=False)` y relanzar, para no dejar el encargo en `generando` 30 minutos.
- [ ] **M-8:** mover los lectores puros de `instagram_feed.py` (perfil, selector, compositor, envío) a `labkit/instagram_pantallas.py`, reexportándolos para no romper llamadas; hacerlo antes de añadir Stories en la fase 2.

## Estado de la fase 1 (2026-09-14 22:20)

Tareas 1–14 hechas, con 10b–10f. Sondas en `findings.md`; primera ventana supervisada publicó CELL-018 (https://www.instagram.com/p/DdR54JEgxHN/); tarea programada `sabiduria-media-lab` creada (10:40, 15:40, 20:40). Prompt de Codex actualizado por el usuario (automation.toml modificado 2026-09-14 23:41): coincide con `codex-heartbeat-prompt.md` salvo las comillas invertidas de `codex-generado`/`codex-fallo` en el paso 4, sin cambio de instrucciones; horario 10:10, 15:10 y 20:10 hasta el 2026-10-01, activo.

### Task 15: `lab.py render`/`tarjeta`, turnos cada 5 h y cola de 10 (hecha)

> **Hecha en `1f70b29`, `055019e`, `eaf3371` y `ca7b72f`** (spec ✅; calidad aprobada con menores). Motivo: la primera ventana desatendida (2026-09-15 00:32, `81d0e26`) no podía crear el máster. Decisión del usuario del 2026-09-15: ventanas cada 5 h continuas (la hora se desplaza cada día), hasta 2 celdas; la tarea programada se dispara `40 * * * *` y el paso 0 del prompt es `lab.py turno` (ancla 2026-09-15 00:40, `turnos.json`, tolerancia 30 min y 2 min de adelanto, `--marcar` con `flock`). Menores pendientes: temporal único con `mkstemp` en `_renderizar_y_publicar`; la prueba de dos procesos debería tomar ella el `flock` para discriminar; `cmd_tarjeta` sin la comprobación `destino.parent.resolve().is_relative_to(...)`; quitar `.turno-hecho.tmp` de `.gitignore`; abrir `.turno.lock` con `O_NOFOLLOW`.

### Task 16: métricas desatendidas (hecha)

- [x] Modo `--metricas` en `verify_api.py` y `media-lab-verify.yml`, búsqueda del id de Graph de publicaciones por teléfono (shortcode) y `lab.py metricas-registrar`; diseño en el scratchpad de la sesión del 2026-09-15 (`metricas-diseno.md`), a volcar aquí al empezar. (hecha en `b10757b` y `a7952a7`)

## Fase 2 (plan aparte)

Flujos de teléfono para Instagram Stories (con sticker o encuesta), Facebook feed y Stories como Página, Threads y TikTok. Cada uno necesita su módulo `labkit/<red>_<formato>.py`, pruebas del analizador con volcados reales y ampliar `seleccion.TELEFONO_FASE_1`.
