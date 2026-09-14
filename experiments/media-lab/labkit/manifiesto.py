"""
Manifiestos para .github/workflows/media-lab.yml (publish_api.py) y
.github/workflows/media-lab-verify.yml (verify_api.py).
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

RAW_BASE = "https://raw.githubusercontent.com/HectorGlez4/sabiduria-publisher/main/"
PLATAFORMAS = ("facebook", "facebook_story", "instagram", "instagram_story", "threads")
FEED = {"facebook", "instagram", "threads"}
STORIES = {"facebook_story", "instagram_story"}
# publish_story y publish_instagram_story ignoran el pie: una historia se publica sin él.
SIN_PIE = STORIES
# Los mismos topes que src/variants.py usa en producción.
LIMITES = {"instagram": 2200, "threads": 500}
VERIFICABLES = ("facebook", "instagram", "threads")
_RUN_GROUP = re.compile(r"LAB-[A-Z0-9][A-Z0-9-]*")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class ManifiestoError(ValueError):
    pass


def _validar_run_group(run_group_id: str) -> None:
    if not _RUN_GROUP.fullmatch(run_group_id):
        raise ManifiestoError("run_group_id debe ser LAB- seguido de mayúsculas, dígitos y guiones")


def manifiesto_api(run_group_id: str, asset_path: str, asset_sha256: str, captions: dict[str, str],
                   family_id: str | None = None) -> dict:
    _validar_run_group(run_group_id)
    if not asset_path.startswith("experiments/media-lab/assets/") or ".." in PurePosixPath(asset_path).parts:
        raise ManifiestoError("el asset debe estar bajo experiments/media-lab/assets/")
    if not _SHA256.fullmatch(asset_sha256):
        raise ManifiestoError("asset_sha256 debe ser un sha256 hexadecimal")
    if not captions:
        raise ManifiestoError("sin pies no hay plataformas")
    plataformas = set(captions)
    if plataformas & FEED and plataformas & STORIES:
        raise ManifiestoError("un manifiesto no mezcla feed y stories: la misma imagen no sirve a los dos formatos")
    pies: dict[str, str] = {}
    for plataforma, pie in captions.items():
        if plataforma not in PLATAFORMAS:
            raise ManifiestoError(f"publish_api.py no publica {plataforma}")
        if plataforma in SIN_PIE:
            pies[plataforma] = ""
            continue
        if not pie.strip():
            raise ManifiestoError(f"pie vacío para {plataforma}")
        limite = LIMITES.get(plataforma)
        if limite and len(pie) > limite:
            raise ManifiestoError(f"pie de {plataforma} con {len(pie)} caracteres: máximo {limite}")
        pies[plataforma] = pie
    m = {"run_group_id": run_group_id, "route": "api", "audience": "public",
         "asset_path": asset_path, "asset_sha256": asset_sha256,
         "asset_url": RAW_BASE + asset_path, "platforms": list(captions), "captions": pies}
    if family_id:
        m["family_id"] = family_id
    return m


def manifiesto_verificacion(run_group_id: str, post_ids: dict[str, str]) -> dict:
    _validar_run_group(run_group_id)
    if not post_ids:
        raise ManifiestoError("sin post_ids no hay nada que verificar")
    for plataforma, post_id in post_ids.items():
        if plataforma not in VERIFICABLES:
            raise ManifiestoError(f"verify_api.py no verifica {plataforma}")
        if not str(post_id).strip():
            raise ManifiestoError(f"post_id vacío para {plataforma}")
    return {"run_group_id": run_group_id, "post_ids": dict(post_ids)}


def ruta_manifiesto(run_group_id: str) -> str:
    return f"experiments/media-lab/manifests/{run_group_id}.json"


def ruta_verificacion(run_group_id: str) -> str:
    return f"experiments/media-lab/manifests/{run_group_id}-verify.json"
