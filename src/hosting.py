"""
Hosting público de las tarjetas.

Instagram y Threads no aceptan subida binaria: Meta DESCARGA la imagen desde una
URL HTTPS pública. Este módulo la publica y devuelve esa URL.

Tres backends, elegidos con SDB_HOSTING:

  github  (por defecto)  Commit del PNG al propio repo y URL de raw.githubusercontent.
                         Cero credenciales nuevas. Exige que el repo sea PÚBLICO,
                         lo cual no es un problema: las tarjetas se publican igual.
  r2                     Cloudflare R2 (o cualquier S3). Para cuando no quieras
                         el repo público o prefieras no ensuciar el historial.
  none                   Falla explícitamente. Útil en tests.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import urllib.request


class HostingError(RuntimeError):
    pass


# ─────────────────────────── GitHub raw ───────────────────────────

def _git(*args: str, cwd: pathlib.Path) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise HostingError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def _repo_slug(root: pathlib.Path) -> str:
    """owner/repo desde el remoto, o desde GITHUB_REPOSITORY dentro de Actions."""
    slug = os.environ.get("GITHUB_REPOSITORY")
    if slug:
        return slug
    url = _git("remote", "get-url", "origin", cwd=root)
    if url.startswith("git@"):
        url = url.split(":", 1)[1]
    else:
        url = url.split("github.com/", 1)[-1]
    return url.removesuffix(".git").strip("/")


# Cuántas veces se reintenta el push cuando otro proceso se adelantó.
#
# Este push ocurre DENTRO de publicar, porque Meta descarga la imagen de
# raw.githubusercontent y tiene que existir en remoto antes de la llamada. Si
# falla, la pieza no se publica: es un fallo de infraestructura disfrazado de
# fallo de contenido.
#
# Desde que hilos.yml empuja a main cada hora hay contención de verdad: entre el
# 27 y el 28 de agosto este push se llevó por delante varias publicaciones con
# "! [rejected] main -> main (fetch first)". Antes de Threads la carrera era rara
# y por eso nunca se vio.
INTENTOS_DE_PUSH = 4


def _empujar(branch: str, root: pathlib.Path) -> None:
    """Push con rebase y reintento: otro proceso puede haber empujado en medio."""
    for intento in range(1, INTENTOS_DE_PUSH + 1):
        try:
            _git("push", "origin", branch, cwd=root)
            return
        except HostingError as e:
            if "rejected" not in str(e) or intento == INTENTOS_DE_PUSH:
                raise
            # --autostash porque en este punto quedan ficheros sin indexar (los
            # PNG de otras piezas, el feed a medio regenerar) y `pull --rebase`
            # se niega a correr con el árbol sucio: "cannot pull with rebase:
            # You have unstaged changes". Eso convertía el reintento en un
            # segundo error en vez de en una solución.
            _git("pull", "--rebase", "--autostash", "origin", branch, cwd=root)


def upload_github(path: pathlib.Path, root: pathlib.Path) -> str:
    """
    Versiona la tarjeta y devuelve su URL cruda.

    Nota: assets/*.png está en .gitignore porque en general la imagen se
    reproduce del JSON. Aquí se fuerza (-f) solo la que se va a publicar, que
    sí tiene que existir en remoto para que Meta la descargue.
    """
    rel = path.relative_to(root)
    branch = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=root)
    slug = _repo_slug(root)

    _git("add", "-f", str(rel), cwd=root)
    status = _git("status", "--porcelain", str(rel), cwd=root)
    if status:
        _git("commit", "-m", f"tarjeta: {path.stem}", cwd=root)
    _empujar(branch, root)

    url = f"https://raw.githubusercontent.com/{slug}/{branch}/{rel.as_posix()}"
    _verify_public(url)
    return url


# ─────────────────────────── Cloudflare R2 / S3 ───────────────────────────

def upload_r2(path: pathlib.Path) -> str:
    try:
        import boto3  # noqa: PLC0415
    except ImportError as e:
        raise HostingError("falta boto3: pip install boto3") from e

    account = os.environ["R2_ACCOUNT_ID"]
    bucket = os.environ.get("R2_BUCKET", "sabiduria-cards")
    public_base = os.environ["R2_PUBLIC_BASE"].rstrip("/")

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    key = f"cards/{path.name}"
    client.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": "image/png"})

    url = f"{public_base}/{key}"
    _verify_public(url)
    return url


# ─────────────────────────── Verificación ───────────────────────────

def _verify_public(url: str, attempts: int = 6) -> None:
    """
    Comprobar que la URL responde ANTES de dársela a Meta.

    Si Meta no puede descargarla devuelve un error genérico y opaco
    ('Param image_url is not a valid URI') que cuesta media hora diagnosticar.
    Mejor fallar aquí, con un mensaje claro.
    """
    import time

    last = ""
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310
                ctype = r.headers.get("Content-Type", "")
                if r.status == 200 and "image" in ctype:
                    return
                last = f"HTTP {r.status}, Content-Type={ctype!r}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(2 * (i + 1))
    raise HostingError(
        f"la imagen no es accesible públicamente tras {attempts} intentos: {url}\n"
        f"  último resultado: {last}\n"
        "  Con backend 'github', casi siempre significa que el repo es privado.\n"
        "  Meta tiene que poder descargar la imagen sin autenticarse."
    )


def upload(path: pathlib.Path, root: pathlib.Path) -> str:
    backend = os.environ.get("SDB_HOSTING", "github").lower()
    if backend == "github":
        return upload_github(path, root)
    if backend == "r2":
        return upload_r2(path)
    raise HostingError(
        f"SDB_HOSTING={backend!r}: sin hosting no se puede publicar en Instagram ni Threads. "
        "Usa 'github' (repo público, cero credenciales) o 'r2'."
    )
