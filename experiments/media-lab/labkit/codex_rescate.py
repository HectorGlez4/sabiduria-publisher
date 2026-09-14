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
