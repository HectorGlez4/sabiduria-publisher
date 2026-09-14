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
