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
