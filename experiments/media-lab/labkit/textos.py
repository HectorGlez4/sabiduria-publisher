"""
Textos exactos de la interfaz de cada app, tal como salen en los volcados del teléfono.

Instagram y Threads están en francés y Facebook en español: es el idioma configurado en el
teléfono. Si una app cambia de idioma no aparece ningún texto de su tabla y los pasos fallan
cerrados con una pista (`pantalla.pista_idioma`). Estas tablas son también la lista blanca de
los fixtures: `fixtures.podar` vacía cualquier texto que no esté aquí ni case con los patrones.

Las entradas marcadas «confirmar contra el fixture de S1» son el texto esperado: la tarea de
cada flujo las sustituye por lo que la sonda anotó en findings.md.
"""
from __future__ import annotations

import re

PAQUETES = {"instagram": "com.instagram.android", "threads": "com.instagram.barcelona",
            "facebook": "com.facebook.katana", "edits": "com.instagram.basel"}
APPS_TELEFONO = ("instagram", "threads", "facebook")
MARCAS = {"instagram": "sabiduriabolsillo", "threads": "sabiduriabolsillo", "facebook": "Sabiduria De Bolsillo"}
IDIOMAS = {"instagram": "francés", "threads": "francés", "facebook": "español", "edits": "inglés"}

TEXTOS: dict[str, dict[str, str]] = {
    "instagram": {
        "perfil": "Profil",
        "modificar_perfil": "Modifier le profil",
        "crear": "Créer",
        "publicacion": "Publication",
        "nueva_publicacion": "Nouvelle publication",
        "recorte": "Modifier le rognage",
        "siguiente": "Suivant",
        "audio_sugerido": "Audio suggéré.",
        "terminado": "Terminé",
        "compartir": "Partager",
        "seleccionado": "Sélectionné Miniature",
        "deseleccionado": "Désélectionné Miniature",
        "reintentar": "Réessayer",
        "imposible_publicar": "Impossible de publier",
        "recomenzar_titulo": "Recommencer ?",
        "recomenzar": "Recommencer",
        "suprimir": "Supprimer",
    },
    "threads": {
        "publicar": "Publier",  # confirmar contra el fixture de S1
    },
    "facebook": {
        "que_piensas": "¿Qué estás pensando?",
        "publico": "Público",
        "pagina": "Sabiduria De Bolsillo",
        "siguiente": "Siguiente",
        "publicar": "Publicar",
        "ahora_no": "Ahora no",
        "not_now": "Not Now",
        "crear_historia": "Crear historia",
        "musica": "Música",
        "encuesta": "Encuesta",
        "compartir_en_instagram": "Compartir en Instagram",
        "descartar": "Descartar",
        "agregar_nueva": "Agregar nueva",
        "compartir_como_publicacion": "Compartir como publicación",
    },
}

ENVIO = frozenset({"Partager", "Publier", "Publicar", "Compartir", "Compartir historia", "Compartir ahora",
                   "Post", "Share", "Publish"})
ENVIO_IDS = frozenset({"new_thread_screen_post_button"})
# Controles que publican una Story directamente desde el editor o el destino: son envío como los de
# arriba (la sonda nunca los pulsa y `pasos.tocar` tampoco, salvo la lista blanca de `_visor_propio`).
ENVIO_HISTORIA = frozenset({
    "Votre story", "Vos stories", "Amis proches", "Envoyer à", "Partager sur votre story",
    "Tu historia", "Tus historias", "Compartir en tu historia", "Mejores amigos", "Enviar a",
    "Your story", "Your stories", "Close friends", "Send to", "Share to your story",
})
# Diálogos de BORRADO de algo ya publicado (no de descarte de un borrador): nunca se pulsa en ellos.
TITULOS_BORRADO = frozenset({
    "Supprimer le fil ?", "Supprimer le thread ?", "Supprimer la publication ?", "Supprimer la story ?",
    "¿Eliminar publicación?", "¿Eliminar la publicación?", "¿Eliminar historia?", "¿Eliminar hilo?",
    "Delete post?", "Delete thread?", "Delete story?",
})
# Un envío no siempre es un texto exacto: cualquier etiqueta que empiece así cuenta como envío…
PREFIJOS_ENVIO = ("partager", "publier", "publicar", "compartir", "share", "post", "publish", "envoyer",
                  "enviar", "send", "ajouter à votre story", "add to your story")
# …salvo estas excepciones explícitas (conmutadores o navegación, sin espacios de más y en minúsculas).
NO_ENVIO = frozenset({
    "partager à",  # flecha del editor de Story hacia el destino; confirmar contra el fixture de S1
    "partager sur facebook", "partager aussi sur instagram", "compartir en instagram",  # conmutadores; confirmar contra el fixture de S1
})
NO_TOCAR = frozenset({"Anular"})  # «Cambiaste a…» de Facebook: deshace el cambio a la Página

DESCARTE = {
    "instagram": {"titulos": ("Recommencer ?",), "botones": ("Recommencer", "Supprimer")},
    "threads": {"titulos": (), "botones": ()},  # sin descarte automático hasta S1: la tarea 12a añade el diálogo observado si no es de borrado
    "facebook": {"titulos": ("¿Descartar publicación?",), "botones": ("Descartar",)},  # confirmar contra el fixture de S1
}

# (patrón, segundos por unidad): la edad de una publicación o story tal como la escribe cada app.
EDADES: dict[str, tuple[tuple[str, int], ...]] = {
    "instagram": ((r"(\d+)\s*s", 1), (r"(\d+)\s*min", 60), (r"(\d+)\s*h", 3600), (r"À l[’']instant", 0)),
    "threads": ((r"(\d+)\s*s", 1), (r"(\d+)\s*min", 60), (r"(\d+)\s*h", 3600), (r"À l[’']instant", 0)),
    "facebook": ((r"Ahora", 0), (r"(\d+)\s*min", 60), (r"(\d+)\s*h", 3600)),
}  # confirmar contra el fixture de S1

# Textos variables que pueden quedarse en un fixture: fechas de miniatura, recuentos, hashtags públicos.
PATRONES: dict[str, tuple[str, ...]] = {
    "instagram": (r"(?:Sélectionné|Désélectionné) Miniature de la photo du \d{1,2}(?:er)? \S+ \d{4} \d{1,2}[:h]\d{2}",
                  r"\d[\d   ]*publications?",
                  r"[\d   ]+ publications publiques",
                  r"#\S+",
                  r"Audio suggéré\..*",
                  r"Photo de profil de sabiduriabolsillo",  # confirmar contra el fixture de S1
                  r"Story de sabiduriabolsillo"),  # confirmar contra el fixture de S1
    "threads": (r"#\S+", r"Photo de profil de sabiduriabolsillo"),  # confirmar contra el fixture de S1
    "facebook": (r"#\S+", r"Foto del perfil de Sabiduria De Bolsillo", r"Sabiduria De Bolsillo ?✓"),  # confirmar contra el fixture de S1
}
# La marca sola ya está en `MARCAS`; aquí solo formatos concretos que la contienen (fullmatch): una frase
# personal que la mencione no se permite.


def texto(app: str, clave: str) -> str:
    try:
        return TEXTOS[app][clave]
    except KeyError as e:
        raise KeyError(f"textos.py no tiene {app}.{clave}") from e


def es_texto_envio(valor: str) -> bool:
    """Texto o id de un control que publica: texto exacto de `ENVIO` o `ENVIO_HISTORIA` o id del botón de publicar
    de Threads (siempre, sin excepciones), o una etiqueta que empieza por uno de `PREFIJOS_ENVIO` y no está en
    `NO_ENVIO`: las excepciones solo valen para la regla de prefijos. Sin mayúsculas ni espacios de más."""
    limpio = " ".join((valor or "").split()).casefold()
    if not limpio:
        return False
    if limpio in {e.casefold() for e in ENVIO | ENVIO_HISTORIA} or limpio.rsplit("/", 1)[-1] in ENVIO_IDS:
        return True
    return limpio not in NO_ENVIO and limpio.startswith(PREFIJOS_ENVIO)


def conocidos(app: str) -> set[str]:
    descarte = DESCARTE.get(app, {})
    return (set(TEXTOS.get(app, {}).values()) | set(descarte.get("titulos", ())) | set(descarte.get("botones", ()))
            | set(MARCAS.values()) | set(ENVIO) | set(ENVIO_HISTORIA) | set(NO_TOCAR))


def permitido(valor: str, app: str) -> bool:
    """El texto puede quedarse en un fixture de `app`."""
    if valor in conocidos(app):
        return True
    patrones = PATRONES.get(app, ()) + tuple(p for p, _ in EDADES.get(app, ()))
    return any(re.fullmatch(p, valor) for p in patrones)
