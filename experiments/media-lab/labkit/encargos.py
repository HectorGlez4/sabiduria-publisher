"""
Encargos de imagen: Claude los escribe, Codex los genera, Claude los revisa.

Un encargo es un JSON en experiments/media-lab/encargos/. Las transiciones viven
aquí y en ningún otro sitio, para que Codex (vía lab.py) y Claude no puedan
dejar un encargo en un estado que el otro no espera.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

LOCK_MINUTOS = 30
MAX_EN_COLA = 10
DUENOS_GENERACION = ("codex-heartbeat", "codex-exec")
MAX_NO_LANZADOS = 3  # no-lanzamientos de Codex SEGUIDOS (señal, fallo de Popen o error antes de
                     # lanzar) antes de bloquear; la racha se corta en cuanto Codex sí llega a
                     # correr (marcar_generado o marcar_fallo reinician no_lanzados a 0)

_ID = re.compile(r"ENC-(\d{8})-(\d{3,})")
_FAMILIA = re.compile(r"[A-Za-z0-9_-]+")


class EncargoError(ValueError):
    pass


def _iso(t: datetime) -> str:
    if t.tzinfo is None:
        raise EncargoError("fecha sin zona horaria")
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _entero_positivo(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def nuevo(encargo_id: str, *, coverage_cell_ids: list[str], family_id: str, brief_path: str,
          do_not_use: list[str], formato: dict, prompt: str, restricciones: list[str],
          destino_assets: str, ahora: datetime, variantes: int = 1, max_intentos: int = 2) -> dict:
    if not encargo_id.startswith("ENC-"):
        raise EncargoError("encargo_id debe empezar por ENC-")
    if not 1 <= variantes <= 2:
        raise EncargoError("variantes debe ser 1 o 2")
    if not _FAMILIA.fullmatch(family_id):
        raise EncargoError("family_id no válido: solo letras, dígitos, guion y guion bajo")
    destino = destino_assets.rstrip("/")
    if destino != f"experiments/media-lab/assets/{family_id}":
        raise EncargoError(f"destino_assets debe ser experiments/media-lab/assets/{family_id}")
    # validar (codex_rescate) mide la orientación contra ancho y alto: sin ellos no se comprueba nada.
    if not isinstance(formato, dict) or not all(_entero_positivo(formato.get(k)) for k in ("ancho", "alto")):
        raise EncargoError("formato debe ser un objeto con ancho y alto enteros positivos")
    if not isinstance(prompt, str) or not prompt.strip():
        raise EncargoError("el prompt no puede estar vacío")
    return {
        "encargo_id": encargo_id, "creado_en": _iso(ahora),
        "coverage_cell_ids": list(coverage_cell_ids), "family_id": family_id,
        "brief_path": brief_path, "do_not_use": list(do_not_use), "formato": formato,
        "variantes": variantes, "prompt": prompt, "restricciones": list(restricciones),
        "destino_assets": destino, "max_intentos": max_intentos,
        "estado": "pedido", "lock_owner": None, "lock_expira": None,
        "imagenes": [], "intentos": [], "revision": None, "runs": [], "no_lanzados": 0,
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
    if len(imagenes) > enc["variantes"]:
        raise EncargoError(f"{len(imagenes)} imágenes para {enc['variantes']} variante(s)")
    rutas = [im["ruta"] for im in imagenes]
    if len(set(rutas)) != len(rutas):
        raise EncargoError("rutas de imagen repetidas")
    for ruta in rutas:
        partes = PurePosixPath(ruta).parts
        if ".." in partes or not ruta.startswith(enc["destino_assets"] + "/") or ruta.endswith("/"):
            raise EncargoError(f"{ruta} está fuera de {enc['destino_assets']}")
    enc["imagenes"] = [{**im, "origen": owner, "generado_en": _iso(ahora)} for im in imagenes]
    enc["intentos"].append({"numero": len(enc["intentos"]) + 1, "resultado": "generado",
                            "origen": owner, "en": _iso(ahora)})
    enc.update(estado="generado", lock_owner=None, lock_expira=None)
    enc["no_lanzados"] = 0  # Codex sí corrió: corta la racha de no-lanzamientos
    enc.pop("nota_no_lanzado", None)
    return enc


def marcar_fallo(enc: dict, owner: str, nota: str, ahora: datetime, bloquear: bool = False) -> dict:
    """Anota un intento fallido y suelta el bloqueo. Vuelve a pedido si quedan intentos;
    queda bloqueado si se agotaron o si se pide `bloquear` (p. ej. Codex tocó archivos ajenos:
    otro intento podría repetirlo)."""
    _exigir_bloqueo(enc, owner)
    enc["intentos"].append({"numero": len(enc["intentos"]) + 1, "resultado": "fallo",
                            "origen": owner, "nota": nota, "en": _iso(ahora)})
    agotado = len(enc["intentos"]) >= enc["max_intentos"]
    siguiente = "bloqueado" if bloquear or agotado else "pedido"
    enc.update(estado=siguiente, lock_owner=None, lock_expira=None)
    enc["no_lanzados"] = 0  # Codex sí corrió: corta la racha de no-lanzamientos
    enc.pop("nota_no_lanzado", None)
    return enc


def liberar(enc: dict, owner: str) -> dict:
    """Devuelve a pedido un encargo que `owner` tomó y en el que no llegó a generarse nada:
    una señal, un fallo de `Popen` o cualquier otro error antes de lanzar Codex. Las tres
    causas cuentan igual, señal incluida (su impacto es pequeño: en cuanto Codex corre de
    verdad, `marcar_generado`/`marcar_fallo` cortan la racha).

    No suma intento: Codex no corrió. Cuenta aparte en `no_lanzados` (los JSON viejos sin el
    campo empiezan en 0): al llegar a MAX_NO_LANZADOS no-lanzamientos SEGUIDOS (p. ej. Popen
    falla siempre igual, como E2BIG por un prompt demasiado largo en argv) el encargo queda
    bloqueado en vez de volver a pedido, para no reintentar en bucle. «Seguidos» se corta en
    cuanto Codex sí llega a correr: `marcar_generado` y `marcar_fallo` reinician `no_lanzados`
    a 0. Solo desde generando y por el dueño del bloqueo."""
    _exigir_bloqueo(enc, owner)
    no_lanzados = enc.get("no_lanzados", 0) + 1
    enc["no_lanzados"] = no_lanzados
    if no_lanzados >= MAX_NO_LANZADOS:
        enc["nota_no_lanzado"] = (f"bloqueado tras {no_lanzados} intentos seguidos en los que Codex "
                                  "no llegó a lanzarse (señal, fallo de Popen o error antes de lanzar Codex)")
        enc.update(estado="bloqueado", lock_owner=None, lock_expira=None)
    else:
        enc.update(estado="pedido", lock_owner=None, lock_expira=None)
    return enc


def invalidar(enc: dict, nota: str, ahora: datetime, bloquear: bool = False) -> dict:
    """Deshace un generado de `codex exec` que no pasó las comprobaciones de `lab.py generar`.

    Las imágenes pasan a `imagenes_invalidas` del último intento, con la nota. Queda en
    bloqueado si se pide (Codex tocó archivos ajenos) o si ya no quedan intentos."""
    ultimo = enc["intentos"][-1] if enc.get("intentos") else {}
    if enc["estado"] != "generado" or ultimo.get("origen") != "codex-exec":
        raise EncargoError(f"{enc['encargo_id']}: solo se invalida lo generado por codex-exec, "
                           f"no {enc['estado']} de {ultimo.get('origen')}")
    ultimo["imagenes_invalidas"] = enc["imagenes"]
    ultimo["nota"] = nota
    ultimo["invalidado_en"] = _iso(ahora)
    enc["imagenes"] = []
    agotado = len(enc["intentos"]) >= enc["max_intentos"]
    enc.update(estado="bloqueado" if bloquear or agotado else "pedido", lock_owner=None, lock_expira=None)
    return enc


def revisar(enc: dict, *, aprobado: bool, motivo: str, ahora: datetime,
            correccion: str | None = None) -> dict:
    if enc["estado"] != "generado":
        raise EncargoError(f"solo se revisa un encargo generado, no {enc['estado']}")
    if not aprobado and not correccion:
        raise EncargoError("un rechazo necesita la corrección para el siguiente intento")
    revision = {"resultado": "aprobado" if aprobado else "rechazado",
                "motivo": motivo, "revisado_en": _iso(ahora)}
    if aprobado:
        enc["revision"] = revision
        enc["estado"] = "aprobado"
        return enc
    enc["intentos"][-1]["imagenes_rechazadas"] = enc["imagenes"]
    enc["intentos"][-1]["revision"] = revision
    enc["revision"] = None
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
    # Escritura atómica: un corte a mitad no deja un JSON truncado que bloquee a los dos agentes.
    # El temporal empieza por punto para que no coincida con ENC-*.json.
    tmp = ruta.with_name(f".{ruta.name}.tmp")
    try:
        tmp.write_text(json.dumps(enc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, ruta)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _leer(p: Path) -> dict:
    try:
        enc = cargar(p)
    except (OSError, ValueError) as e:
        raise EncargoError(f"{p.name} ilegible: {e}") from e
    if not isinstance(enc, dict) or not {"creado_en", "encargo_id", "estado"} <= set(enc):
        raise EncargoError(f"{p.name} incompleto: faltan creado_en, encargo_id o estado")
    return enc


def _ordenados(pares: list[tuple[Path, dict]]) -> list[tuple[Path, dict]]:
    return sorted(pares, key=lambda par: (par[1]["creado_en"], par[1]["encargo_id"]))


def listar(carpeta: Path) -> list[tuple[Path, dict]]:
    if not carpeta.exists():
        return []
    return _ordenados([(p, _leer(p)) for p in carpeta.glob("ENC-*.json")])


def listar_tolerante(carpeta: Path) -> tuple[list[tuple[Path, dict]], list[dict]]:
    """Como `listar`, pero los archivos ilegibles o incompletos salen aparte como
    {"archivo", "error"} en lugar de hacer fallar el listado entero."""
    if not carpeta.exists():
        return [], []
    buenos, malos = [], []
    for p in sorted(carpeta.glob("ENC-*.json")):
        try:
            buenos.append((p, _leer(p)))
        except EncargoError as e:
            malos.append({"archivo": p.name, "error": str(e)})
    return _ordenados(buenos), malos


def siguiente_id(carpeta: Path, ahora: datetime) -> str:
    if ahora.tzinfo is None:
        raise EncargoError("fecha sin zona horaria")
    dia = f"{ahora.astimezone(timezone.utc):%Y%m%d}"
    usados = []
    if carpeta.exists():
        for p in carpeta.glob(f"ENC-{dia}-*.json"):
            m = _ID.fullmatch(p.stem)
            if m:
                usados.append(int(m.group(2)))
    return f"ENC-{dia}-{max(usados, default=0) + 1:03d}"
