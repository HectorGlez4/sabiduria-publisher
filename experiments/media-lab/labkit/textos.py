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
import unicodedata

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
# Sufijos exactos (tras la última «/») de resource-id de botones de envío: se comparan por igualdad, nunca
# por prefijo (los contenedores `post_capture_*` del editor no son envío y bloquearían todos los toques).
# `share_footer_button` es el «Partager» del compositor de Instagram (sonda SONDA-10F de la fase 1).
ENVIO_IDS = frozenset({"new_thread_screen_post_button", "share_footer_button"})
# Palabras que, en el final de un resource-id partido por «_», delatan un botón de envío SIN etiqueta
# («composer_post_button» de Facebook). La sonda solo las mira en el nodo que toca y en los nodos PULSABLES bajo su
# centro, nunca en cualquier contenedor: `followers_share_content` cubre todo el compositor de Instagram y
# `post_capture_*` el editor.
ENVIO_ID_PALABRAS = frozenset({"post", "share", "send", "publish", "submit", "publicar", "compartir", "enviar"})
# Controles que publican una Story directamente desde el editor o el destino: son envío como los de
# arriba (la sonda nunca los pulsa y `pasos.tocar` tampoco, salvo que la etiqueta esté en la lista
# blanca del visor propio de la fase 2).
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
# Verbos de BORRAR: una etiqueta que empieza por uno de ellos (seguido de fin o de un separador no alfanumérico)
# es un control de borrado; la sonda nunca lo pulsa.
BORRADO_VERBOS = ("supprimer", "eliminar", "borrar", "delete", "remove", "retirer",
                  "mover a la papelera", "move to trash", "placer dans la corbeille")

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

# ── Lo que puede quedarse en un fixture ──────────────────────────────────────────────────────────────────────
# Estos patrones solo deciden qué queda en un fixture (`fixtures.podar`/`revisar` vía `permitido`): ningún lector de
# pantallas los usa. Son textos variables: fechas de miniatura, recuentos, formatos concretos que contienen la marca y,
# solo en `text`, hashtags. La marca sola ya está en `MARCAS`; aquí solo formatos concretos que la contienen
# (fullmatch): una frase personal que la mencione no se permite. Del chip de audio solo vale el literal «Audio
# suggéré.» (en `TEXTOS`); con el tema detrás no, así que un fixture del editor pierde el texto del chip entero (y con
# él el tema): lo que se pruebe sobre el tema usa un volcado sintético.
#
# Umbrales de cifras seguidas: una edad lleva de 1 a 3 (`EDADES_FIXTURE`), un hashtag menos de 4 (`_HASHTAG`) y
# ningún valor 6 o más (`_CIFRAS_LARGAS`), salvo un texto exacto de la tabla.
PATRONES_FIXTURE: dict[str, tuple[str, ...]] = {
    "instagram": (r"(?:Sélectionné|Désélectionné) Miniature de la photo du \d{1,2}(?:er)? \S+ \d{4} \d{1,2}[:h]\d{2}",
                  r"\d[\d   ]*publications?",
                  r"[\d   ]+ publications publiques",
                  r"Photo de profil de sabiduriabolsillo",  # confirmar contra el fixture de S1
                  r"Story de sabiduriabolsillo"),  # confirmar contra el fixture de S1
    "threads": (r"Photo de profil de sabiduriabolsillo",),  # confirmar contra el fixture de S1
    "facebook": (r"Foto del perfil de Sabiduria De Bolsillo", r"Sabiduria De Bolsillo ?✓"),  # confirmar contra el fixture de S1
}
_HASHTAG = r"#[^\W\d_](?!\w*\d{4})\w*"  # empieza por letra y sin 4 o más cifras seguidas
# Solo en el atributo `text` (nunca en `hint`, `content-desc` ni otros): hashtags públicos del pie.
PATRONES_FIXTURE_TEXTO: dict[str, tuple[str, ...]] = {
    "instagram": (_HASHTAG,), "threads": (_HASHTAG,), "facebook": (_HASHTAG,)}


def _edades_fixture(edades: dict | None = None) -> dict[str, tuple[str, ...]]:
    """Las edades de `EDADES` con cada `\\d+` acotado a 1-3 cifras. Falla al importar si algún patrón de `EDADES`
    lleva una cifra que no quede acotada así (p. ej. `\\d*`, `\\d{2,}` o una clase con `0-9` y cuantificador, como
    `[0-9]+`): la tabla de lectura no cambia. `edades` sustituye a `EDADES` solo en las pruebas."""
    edades = EDADES if edades is None else edades
    derivadas = {app: tuple(p.replace(r"\d+", r"\d{1,3}") for p, _ in tabla) for app, tabla in edades.items()}
    for app, patrones in derivadas.items():
        for patron in patrones:
            if re.search(r"\\d(?!\{1,3\})|\[[^\]]*0-9[^\]]*\](?:[*+]|\{(?!1,3\}))", patron):
                raise ValueError(f"EDADES[{app!r}] tiene una cifra sin acotar a 1-3 en un fixture: {patron!r}")
    return derivadas


EDADES_FIXTURE: dict[str, tuple[str, ...]] = _edades_fixture()
_CIFRAS_LARGAS = re.compile(r"\d{6,}")


def texto(app: str, clave: str) -> str:
    try:
        return TEXTOS[app][clave]
    except KeyError as e:
        raise KeyError(f"textos.py no tiene {app}.{clave}") from e


def normalizar(valor: str) -> str:
    """NFKC, sin caracteres de formato invisibles (categoría Unicode `Cf`: ancho cero, marcas de
    dirección…), espacios colapsados (NBSP y espacio fino incluidos, que `str.split()` ya trata como
    separador) y en minúsculas. Una sola normalización para comparar textos de envío, títulos de
    borrado y de descarte contra lo que trae el volcado."""
    forma = unicodedata.normalize("NFKC", valor or "")
    sin_invisibles = "".join(c for c in forma if unicodedata.category(c) != "Cf")
    return " ".join(sin_invisibles.split()).casefold()


_COMILLAS = "«»“”‘’\"'"


def normalizar_titulo(valor: str) -> str:
    """`normalizar`, y además sin comillas (rectas, tipográficas, angulares o de ancho completo: «»
    “” ‘’ "' ＂＇) ni espacio antes de un «?» de cierre: para comparar títulos de diálogo («Supprimer
    la publication?», «Supprimer la « publication » ?» y «Delete "post"?» son el mismo título).

    Las comillas se quitan DESPUÉS de `normalizar`, no antes: NFKC convierte una comilla de ancho
    completo (＂ U+FF02, ＇ U+FF07) en la recta correspondiente, así que quitarlas antes de NFKC las
    dejaría pasar sin quitar."""
    sin_comillas = "".join(c for c in normalizar(valor) if c not in _COMILLAS)
    return re.sub(r"\s+\?", "?", " ".join(sin_comillas.split()))


# Formas normalizadas de las constantes de arriba, precalculadas una vez al importar (no en cada
# llamada). `permitir`/`ignorar`, al venir de fuera y cambiar en cada llamada, se normaliza siempre
# en el momento, nunca aquí.
_ENVIO_NORM = frozenset(normalizar(e) for e in ENVIO)
_NO_TOCAR_NORM = frozenset(normalizar(t) for t in NO_TOCAR)
_NO_ENVIO_NORM = frozenset(map(normalizar, NO_ENVIO))
_TITULOS_BORRADO_NORM = frozenset(normalizar_titulo(t) for t in TITULOS_BORRADO)
_DESCARTE_TITULOS_NORM = {app: frozenset(normalizar_titulo(t) for t in tabla["titulos"])
                          for app, tabla in DESCARTE.items()}


def es_titulo_borrado(valor: str) -> bool:
    """`valor` (comparado con `normalizar_titulo`) es uno de los títulos de `TITULOS_BORRADO`: un
    diálogo de BORRADO de algo ya publicado, no de descarte de un borrador."""
    limpio = normalizar_titulo(valor)
    return bool(limpio) and limpio in _TITULOS_BORRADO_NORM


def es_titulo_descarte(valor: str, app: str) -> bool:
    """`valor` (comparado con `normalizar_titulo`) es uno de los títulos de descarte de `app` en
    `DESCARTE`."""
    limpio = normalizar_titulo(valor)
    return bool(limpio) and limpio in _DESCARTE_TITULOS_NORM.get(app, frozenset())


def coincide_o_prefijo(valor: str, candidatos) -> bool:
    """`valor` coincide, tras `normalizar`, con alguno de `candidatos` (normalizados): exacto, o por
    prefijo seguido de un separador no alfanumérico («Votre story, 2 nouvelles» coincide con «Votre
    story»). `candidatos` debe ser una colección de etiquetas, nunca un `str` ni un `bytes`: si lo
    fuera, cada carácter contaría como un candidato distinto."""
    if isinstance(candidatos, (str, bytes)):
        raise TypeError("candidatos debe ser una colección de etiquetas, no una cadena")
    limpio = normalizar(valor)
    if not limpio:
        return False
    for c in candidatos:
        if not c:
            continue
        prefijo = normalizar(c)
        if prefijo and (limpio == prefijo or (limpio.startswith(prefijo) and not limpio[len(prefijo)].isalnum())):
            return True
    return False


def es_no_tocar(valor: str) -> bool:
    """`valor` (normalizado) es exactamente uno de `NO_TOCAR`."""
    limpio = normalizar(valor)
    return bool(limpio) and limpio in _NO_TOCAR_NORM


def es_texto_envio(valor: str) -> bool:
    """Texto o id de un control que publica: texto exacto de `ENVIO` o `ENVIO_HISTORIA`, una etiqueta
    que EMPIEZA por un texto de `ENVIO_HISTORIA` seguido de un separador no alfanumérico («Votre
    story, 2 nouvelles»: sigue siendo el mismo control con un contador o una coma añadidos), el id del
    botón de publicar de Threads (siempre, sin excepciones), o una etiqueta que empieza por uno de
    `PREFIJOS_ENVIO` y no está en `NO_ENVIO` (las excepciones solo valen para la regla de prefijos,
    nunca para `ENVIO`/`ENVIO_HISTORIA`). Comparación con `normalizar`."""
    limpio = normalizar(valor)
    if not limpio:
        return False
    if limpio in _ENVIO_NORM or limpio.rsplit("/", 1)[-1] in ENVIO_IDS:
        return True
    if coincide_o_prefijo(valor, ENVIO_HISTORIA):
        return True
    return limpio not in _NO_ENVIO_NORM and limpio.startswith(PREFIJOS_ENVIO)


def conocidos(app: str) -> set[str]:
    descarte = DESCARTE.get(app, {})
    return (set(TEXTOS.get(app, {}).values()) | set(descarte.get("titulos", ())) | set(descarte.get("botones", ()))
            | set(MARCAS.values()) | set(ENVIO) | set(ENVIO_HISTORIA) | set(NO_TOCAR))


def es_id_envio(resource_id: str) -> bool:
    """El final del resource-id (tras la última «/»), partido por «_», contiene una palabra de `ENVIO_ID_PALABRAS`
    («composer_post_button», «direct_private_share_x»). No mira texto ni desc: quien llama decide cuándo cuenta."""
    sufijo = (resource_id or "").rsplit("/", 1)[-1].casefold()
    return bool(ENVIO_ID_PALABRAS.intersection(sufijo.split("_")))


def es_texto_borrado(valor: str) -> bool:
    """Etiqueta (o sufijo de id) de un control de borrado: tras `normalizar`, empieza por uno de `BORRADO_VERBOS`
    seguido de fin o de un separador no alfanumérico («Supprimer», «Eliminar publicación», «delete_button»)."""
    return coincide_o_prefijo(valor, BORRADO_VERBOS)


def permitido(valor: str, app: str, atributo: str = "text") -> bool:
    """El valor del `atributo` (por defecto `text`) puede quedarse en un fixture de `app`. Los hashtags solo
    valen en `text`; ningún valor con 6 o más cifras seguidas vale salvo un texto exacto de la tabla."""
    if valor in conocidos(app):
        return True
    if _CIFRAS_LARGAS.search(valor):
        return False
    patrones = (PATRONES_FIXTURE.get(app, ()) + EDADES_FIXTURE.get(app, ())
                + (PATRONES_FIXTURE_TEXTO.get(app, ()) if atributo == "text" else ()))
    return any(re.fullmatch(p, valor) for p in patrones)
