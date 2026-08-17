"""
Plataformas diseñadas pero NO operativas todavía, con el motivo exacto.

Este archivo existe para que nadie —ni tú, ni yo en otra sesión— pierda una tarde
implementando algo que está bloqueado por un trámite y no por código. Cada
adaptador levanta una excepción que dice qué falta y quién tiene que desbloquearlo.

Verificado el 17 de agosto de 2026 contra la documentación oficial.
"""
from __future__ import annotations


class PlatformBlocked(RuntimeError):
    """La plataforma necesita algo que no depende de escribir código."""


def publish_tiktok(*_args, **_kwargs):
    raise PlatformBlocked(
        "TikTok — bloqueado por AUDITORÍA.\n"
        "  La Content Posting API restringe TODO lo que publica un cliente sin auditar\n"
        "  a privado (SELF_ONLY): /creator_info/query solo devuelve esa opción de\n"
        "  privacidad hasta que TikTok audite la app. Publicar funcionaría, pero no\n"
        "  lo vería nadie.\n"
        "  Falta: scope video.publish + superar la auditoría de TikTok.\n"
        "  Además: TikTok consume VÍDEO. La tarjeta 1080x1350 no sirve tal cual;\n"
        "  hay que generar vídeo (ver nota sobre ffmpeg en el README)."
    )


def publish_youtube(*_args, **_kwargs):
    raise PlatformBlocked(
        "YouTube — bloqueado por AUDITORÍA DE CUMPLIMIENTO.\n"
        "  Todo vídeo subido con videos.insert desde un proyecto de API no verificado\n"
        "  creado después del 28 de julio de 2020 queda en PRIVADO, sin excepción,\n"
        "  hasta pasar la auditoría de cumplimiento con los Términos de Servicio.\n"
        "  Cuota: 1 unidad del bucket de uploads, 100 llamadas al día. La cuota no\n"
        "  es el problema; la verificación sí.\n"
        "  Además: YouTube consume VÍDEO (Shorts para este formato)."
    )


def publish_x(*_args, **_kwargs):
    raise PlatformBlocked(
        "X — bloqueado por CREDENCIALES.\n"
        "  El acceso de escritura a la API de X es de pago y requiere plan propio.\n"
        "  La derivación de texto ya está hecha en src/variants.py (280 caracteres,\n"
        "  dato duro primero): en cuanto haya credenciales, esto son 20 líneas."
    )


def publish_linkedin(*_args, **_kwargs):
    raise PlatformBlocked(
        "LinkedIn — bloqueado por CREDENCIALES.\n"
        "  Requiere app propia y el producto 'Share on LinkedIn' aprobado.\n"
        "  La derivación de texto ya está hecha en src/variants.py."
    )


PENDING = {
    "tiktok": publish_tiktok,
    "youtube": publish_youtube,
    "x": publish_x,
    "linkedin": publish_linkedin,
}
