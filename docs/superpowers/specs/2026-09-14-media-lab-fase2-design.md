# Laboratorio de medios, fase 2: publicación nativa por teléfono más allá del feed de Instagram

Fecha: 2026-09-14 · Estado: **propuesta**; los valores por defecto de la sección 6 se aplican salvo que el usuario los cambie. Parte de la spec de la fase 1 (`docs/superpowers/specs/2026-09-14-media-lab-chatgpt-claude-design.md`) y de su plan (`docs/superpowers/plans/2026-09-14-media-lab-chatgpt-claude-fase1.md`), que siguen vigentes en todo lo que esta no cambia.

## Objetivo

Que la ventana de publicación de Claude pueda sacar por teléfono (Samsung SM-S721B, serie `R5CXB1AWYNF`) las celdas `android_native` de `coverage.json` que hoy no puede elegir. Son 69 celdas: todas menos las 4 de `instagram/feed_single_image`, que ya cubre la fase 1.

Criterio de éxito:

- Cada flujo implementado tiene un módulo con lectores puros probados contra volcados reales del teléfono actual, podados de datos personales.
- Su primera publicación sale en una ventana manual dirigida paso a paso por Claude con estado `confirmado`, y a partir de ahí la tarea programada lo elige sola.
- Ninguna celda sale sin PASS de QA visual, y cada copia automática entre redes queda en `publication.cross_posting` del run.

Límite de calendario: la campaña termina el 2026-10-01 (quedan 17 días). El orden de la sección 5 pone primero lo que más celdas desbloquea por unidad de esfuerzo. Lo que no llegue queda `planned`, con el motivo en `progress.md`.

## Decisiones tomadas (no se reabren)

| Tema | Decisión |
|---|---|
| Reparto | Codex solo genera imágenes a partir de encargos. Claude encarga, revisa, hace QA y publica, tanto por teléfono como por API. |
| Ritmo | 3 ventanas al día y hasta 2 celdas por ventana. |
| Producción cercana | Solo informativa: se anota en el run y no frena. |
| Confirmación antes de publicar | No hay confirmación humana. Basta el PASS de un agente que solo comprueba texto o imagen cortados o tapados (`visual-qa-gate.md`). |
| Copia automática de Instagram a Facebook | Se deja activa y cuenta como publicación extra, no como celda. |
| Estado del teléfono | La automatización nunca lo despierta ni lo desbloquea. Si no está listo, salta las celdas de teléfono. |
| Codex | Puede usar la configuración del usuario. |

## Alcance

**Entra:**

| Bloque | Pares (red, `native_format`) | Celdas |
|---|---|---|
| R. Refactor común y sondas | — | — |
| A0. Feed de Instagram con música | instagram/feed_image_music | 1 |
| A. Story de imagen en Instagram | instagram/story_image, story_image_music | 6 |
| B. Feed de Threads | threads/feed_single_image, feed_text, feed_image_music | 7 |
| C. Feed de la Página de Facebook | facebook/feed_single_image, feed_text, feed_image_music | 6 |
| D. Story de la Página de Facebook | facebook/story_image, story_image_music | 6 |
| E. Encuestas | instagram/story_poll, facebook/story_poll, threads/feed_poll | 6 |
| F. Multiimagen y secuencias | instagram/feed_carousel, story_sequence; facebook/feed_multi_photo, story_sequence; threads/feed_carousel | 20 |
| G0. Sonda de Edits (sin publicar) | — | — |

Las 20 celdas de F son las 4 de cada par. Las celdas `ready` de A, C, D y B (CELL-006, 007, 009, 010) entran con su flujo.

**No entra:**

- **Vídeo** (12 celdas: `reel_video`, `story_video`, `feed_video`; `fase2-hechos.md` dice 14 en su desglose por flujo, pero el recuento por par da 12 y cuadra con el total de 69). Pasa a una fase 3; ver la decisión 7. En la fase 2 solo se hace la sonda G0.
- **TikTok.** Sigue bloqueado por el puzle de verificación; ver la decisión 8.
- **Marcadores `selected_after_day_7`** (5). Se resuelven con la regla de la decisión 9 y usan flujos ya implementados; no traen código propio.
- **Encuesta en el feed de Facebook** (`pending_deeper_probe`). No tiene celdas.

## 1. Arquitectura

### A. Módulos

El patrón de la fase 1 se mantiene: lectores puros separados de los pasos con E/S, un paso por llamada y captura tras cada paso.

| Archivo | Tipo | Contenido |
|---|---|---|
| `labkit/pantalla.py` (nuevo) | Puro | Lo genérico que hoy vive en `instagram_pantallas.py`: `elegir` (hoy `_elegir`); `coincidencias(xml, paquete, zona)` con zonas **relativas a la altura del volcado** («arriba» ≤ 13 %, «abajo» ≥ 81 %, que equivalen a los 300 y 1900 px actuales sobre 2340); `nodo`; `pulsable(xml, etiqueta, paquete)` (hoy `partager_pulsable`); `evaluar_envio(observaciones)`; `hay_desplegable(xml, paquete, prefijo)`; `PantallaInesperada`. |
| `labkit/pasos.py` (nuevo) | E/S común | `exigir_listo`; `esperar_que`; `volcado_fresco`; `esperar_estable(cumple, n=3)`, el arreglo de la tarea 10e generalizado; `escribir_texto(campo, texto, paquete)`, que generaliza `escribir_pie` (pega con `phone_clipboard`, relee y cierra teclado y desplegables con un tope de 2 «atrás»); `atras(paquete)`; `descartar(paquete)`; `observar_envio(boton, observador, plazo)`, el bucle de `compartir` con la observación como parámetro. Usa `labkit/reloj.py`. |
| `labkit/reloj.py` (nuevo) | E/S mínima | `dormir` y `monotonic`. Las pruebas parchean solo este módulo, en lugar del `time` global como hoy (`tests/test_media_lab.py:607`). |
| `labkit/textos.py` (nuevo) | Datos | Tablas `TEXTOS[app][clave]` con los textos exactos de la interfaz: Instagram y Threads en francés, Facebook en español. Cada `abrir` exige uno de ellos; si falta, el mensaje de `PantallaInesperada` apunta a un posible cambio de idioma. Las tablas son también la lista blanca de los fixtures (sección 6). |
| `labkit/telefono.py` | E/S | Se añaden `arrastrar(x1, y1, x2, y2, ms)` (`input swipe` con duración ≥ 600 ms, validado en la sonda S2), `recientes_mediastore(n)` (las N imágenes más recientes por `date_added`) y `URI_VIDEOS` para G0. |
| `labkit/instagram_pantallas.py` | Puro | Conserva lo propio de Instagram y reexporta desde `pantalla.py` lo que se mueve. Se añaden los lectores de Story de la sección 3A. |
| `labkit/instagram_feed.py` | E/S | Pasa a usar `pasos.py`. Su comportamiento no cambia y sus pruebas siguen verdes sin tocarlas. Admite `n` subidas para el carrusel (F). |
| `labkit/instagram_historia.py` (nuevo) | E/S | Pasos de la Story de Instagram: imagen, sticker de música, encuesta y secuencia. |
| `labkit/threads_pantallas.py` y `labkit/threads_feed.py` (nuevos) | Puro y E/S | Flujo B, más encuesta y carrusel. |
| `labkit/facebook_pantallas.py`, `labkit/facebook_feed.py` y `labkit/facebook_historia.py` (nuevos) | Puro y E/S | Flujos C y D, más encuesta, multifoto y secuencia. |
| `labkit/stickers.py` (nuevo) | Puro | `sticker_en_zona(bounds_sticker, zona_reservada, zonas_texto)`, `destino_arrastre(bounds_sticker, zona_reservada)` y `encuesta_escrita(xml, pregunta, opciones, app)`. |
| `labkit/recetas.py` (nuevo) | Puro | Registro único de flujos implementados: `RECETAS[(red, formato)]`, con la lista ordenada de subcomandos de `lab.py`, qué debe mostrar cada captura, qué estados salen con 0 y qué copias automáticas produce. |
| `labkit/fixtures.py` (nuevo) | Puro | `podar(xml, app)`: borra texto y descripción de los nodos que no estén en `textos.py` ni sean de la marca, y descarta los paquetes ajenos (`com.android.systemui`, notificaciones). |

Una red y un formato cuentan como implementados solo si están en `RECETAS`.

### B. Selección

`seleccion.py`:

- `TELEFONO_FASE_1` pasa a llamarse `TELEFONO_IMPLEMENTADO`, derivado de `recetas.RECETAS`. El nombre antiguo se conserva como alias durante la transición. `encargo-nuevo` y `seleccionar` ya validan contra él.
- `compatibles` mantiene sus reglas: la segunda celda difiere en red o ruta, y ninguna celda de Facebook sale con una de Instagram por teléfono. Esta última ya cubre cualquier formato de Instagram, así que también la Story. Se añaden dos reglas:
  1. **Como máximo una celda `android_native` por ventana.** MaaS360 bloquea la pantalla a los 120 s y la segunda celda sale al menos 21 min después, así que casi siempre encontraría el teléfono bloqueado y la ventana perdería el hueco. El segundo hueco va a API.
  2. **Exclusión por copia automática**, leída de `RECETAS[...]["copias"]`. Hoy son instagram → facebook en feed y Story. Si la sonda S1 encuentra la inversa (Story de Facebook → Instagram) o una de Threads → Instagram, se añade a la tabla y la regla se aplica sola.

### C. Encargos

- **Story con sticker (E):** `formato` admite `zona_reservada: [x1, y1, x2, y2]` en píxeles del máster de 1080×1920. La imagen se genera igual. `render_overlay.py` no escribe texto dentro de la zona, y la receta arrastra el sticker hasta ella.
- **Secuencias (F):** `formato` admite `fotogramas: N` (2–10) y el encargo lleva `prompts_fotogramas[]` en orden. Quien genera guarda `destino_assets/<encargo_id>-f<k>.png`. Cambiar esto obliga a actualizar `codex-heartbeat-prompt.md`, que el usuario vuelve a pegar en la automatización, como en la fase 1.
- No se mezclan en un encargo celdas de feed (4:5), de Story (9:16) y de secuencia.

### D. `lab.py`

Se añade un subcomando por módulo, con los mismos códigos de salida que en la fase 1: 0 correcto, 2 argumentos, 4 pantalla inesperada o teléfono, 5 envío dudoso.

| Subcomando | Pasos (`paso`) |
|---|---|
| `ig` (existente) | Sin cambios; admite `--subido-en` repetido para carrusel |
| `ig-historia` | `abrir`, `elegir`, `audio`, `sticker-musica`, `encuesta`, `destino`, `compartir` |
| `th` | `abrir`, `nuevo`, `texto`, `galeria`, `musica`, `encuesta`, `compartir` |
| `fb` | `abrir`, `nuevo`, `galeria`, `musica`, `pie`, `siguiente`, `compartir` |
| `fb-historia` | `abrir`, `elegir`, `audio`, `sticker-musica`, `encuesta`, `compartir` |

Argumentos comunes: `--run`, `--subido-en` (repetible y en orden), `--pie`, `--tema`, `--produccion-cercana`, `--encuesta <json {pregunta, opciones}>` y `--zona x1,y1,x2,y2`.

Otros subcomandos:

- `telefono-subir --local` se vuelve repetible y sube en orden inverso: el último fotograma primero, porque la rejilla muestra lo más reciente arriba. Devuelve `subido_en` de cada archivo y comprueba con `recientes_mediastore` que las N más recientes son las nuestras y en el orden esperado.
- `telefono-atras --app instagram|threads|facebook` (hoy solo Instagram).
- `telefono-descartar --app X`: pulsa el botón de descartar solo si el volcado muestra el diálogo de descarte con los textos exactos de `textos.py` (FR «Recommencer» / «Supprimer», ES «Descartar» y los que capture S1). Así se puede abandonar un borrador sin pulsar a ciegas.
- `receta --celda CELL-XXX`: imprime en JSON la receta de esa celda (comandos en orden, qué debe verse en cada captura y cómo se verifica).
- `sonda <app> volcar|tocar|atras --run SONDA-F2-… --nombre …`: solo para sesiones supervisadas. Exige `--supervisada`. `tocar` acepta `--texto`, `--desc` o `--resource-id` y pulsa solo un nodo único del paquete. **Se niega a pulsar** cualquier texto de envío de la tabla `ENVIO` (Partager, Publier, Publicar, Compartir, Compartir historia, Post, Share…). `volcar` guarda el XML y la captura en `evidence/android/sondas-f2/`.

`preflight` añade las versiones de Facebook (`com.facebook.katana`), Threads (`com.instagram.barcelona`) y Edits (`com.instagram.basel`), y aclara la versión de Instagram, que hoy es incoherente entre `progress.md` y los runs. No abre ninguna app.

### E. Encaje en el prompt de la ventana

Cambios en `experiments/media-lab/claude-ventana-prompt.md`:

- **Paso 5:** «red y formato implementados» remite a `lab.py receta` / `TELEFONO_IMPLEMENTADO`. Para celdas de encuesta, el encargo lleva `zona_reservada`; para secuencias, `fotogramas`.
- **Paso 7b:** la secuencia fija del feed de Instagram se sustituye por esto: «`lab.py receta --celda <id>` y ejecuta sus comandos en orden; tras cada uno abre la captura y comprueba lo que la receta dice que debe verse». Así el prompt no crece con cada flujo y la receta vive junto al código que prueba.
- **Paso 7c:** en Stories con sticker, el revisor recibe también la `zona_reservada`.
- **Paso 7e:** sale con 0 solo con `confirmado`. Con 5, se concilia como dice la receta (sección 3), nunca por la otra ruta.
- **Paso 7f:** la verificación y la búsqueda de URL de cada flujo (sección 3). Se registra cualquier copia automática que declare la receta.
- **Paso 8:** las Stories se miden hacia las 6 h y antes de caducar (sección 3A).
- **Nueva regla:** «si un paso de teléfono deja un borrador abierto (código 4 a mitad de flujo), intenta salir con `telefono-atras` y `telefono-descartar` mirando capturas; si no puedes, deja constancia en el informe: la siguiente ventana lo encontrará como `BorradorPendiente`».

## 2. Sondas supervisadas (sin publicar)

Todas las hace Claude con el usuario presente, porque el teléfono puede bloquearse y solo el usuario lo desbloquea. Se usan `lab.py sonda …` y los pasos ya implementados; no se pulsa ningún botón de envío. Al salir: `telefono-atras` y descarte, y comprobación en el perfil de que no se publicó nada, como en la tarea 11 de la fase 1.

| Sonda | Cuándo | Qué captura (volcado + captura) | Desbloquea |
|---|---|---|---|
| **S1** | Tras el refactor R | **Instagram FR:** menú Créer (texto de «Story»), selector de galería de Story (content-desc de la miniatura, multiselección), editor (chip de audio ya añadido, botón de música, panel de stickers FR con «Sondage» o equivalente), pantalla de destino («Vos stories», Amis proches, conmutador de Facebook), visor de la story propia de un día anterior si la hay, selector del carrusel de feed (multiselección y ordinales). **Threads FR:** inicio, perfil de marca, compositor, galería (multiselección), música, menú de adjuntos, campos de encuesta, opciones de publicación y cualquier conmutador «Partager aussi sur Instagram». **Facebook ES:** inicio con la Página activa, interstitials, compositor de Página («¿Qué estás pensando?», identidad, Música, Galería con multiselección), pantalla tras «Siguiente» (audiencia y botón final), selector de música, diálogo de descarte, «Crear historia» (galería, editor, stickers ES con «Encuesta», botón y destino de compartir, conmutador «Compartir en Instagram»). | A, B, C, D, F (lectura), fixtures |
| **S2** | Antes de E | En un borrador de Story de Instagram y de Facebook con el máster de zona reservada: añadir la encuesta, escribir pregunta y opciones con el portapapeles, `telefono.arrastrar` hasta la zona y volcar para leer los bounds finales. Sirve para comprobar que `input swipe` mueve el sticker y que el volcado expone su posición. | E |
| **S3** | Antes de F, si S1 no bastó | Multiselección de 3 fotogramas en cada selector: orden de los ordinales, vista previa de la secuencia y música en carrusel. | F |
| **G0** | Cuando no haya otra sonda pendiente | Edits en el teléfono actual: proyecto desde una imagen 9:16 sin franjas, duración de 8–15 s, hoja de audio, «Choose where to share» → Instagram Reel y selector de Facebook. Sin compartir ni descargar con música del catálogo. | Plan de la fase 3 |

Cada sonda deja volcados crudos en `evidence/android/sondas-f2/`. Los fixtures podados (sección 6) van a `tests/fixtures/telefono/<app>/<pantalla>.xml`, con una nota en `findings.md` que dice qué pantalla corresponde a cada fixture y qué textos faltaban.

## 3. Flujos

Común a todos:

- Antes de cualquier toque de composición, `abrir` exige identidad de marca; si no la ve, sale con `PantallaInesperada`.
- Si la app abre con un compositor a medias, sale con `BorradorPendiente`.
- `compartir` comprueba el compositor en dos volcados seguidos, pulsa el botón de envío **una sola vez** y observa con `pasos.observar_envio`. Nada se propaga después de pulsar.
- La evidencia final es siempre `screencap`.
- Estados comunes: `confirmado` (sale con 0), `confirmado_sin_prueba_unica`, `sin_confirmacion`, `timeout`, `fallido` y `error_tras_pulsar` (todos salen con 5).

`confirmado_sin_prueba_unica` sustituye en los flujos nuevos a `confirmado_sin_conteo`: la publicación se vio, pero hay algo que no la distingue de otra.

### A0. Feed de Instagram con música (`feed_image_music`)

Usa la misma receta que `feed_single_image`: la música ya es obligatoria en toda foto. Solo se registra el par en `RECETAS` y la celda anota el tema en el run. No hace falta sonda.

### A. Story de imagen en Instagram (`story_image`, `story_image_music`)

**Pasos:**

1. `telefono-subir` del máster 9:16.
2. `ig-historia abrir`: perfil → exige `@sabiduriabolsillo` → «Créer» → Story (texto FR de S1) → selector de galería → exige una única miniatura seleccionada que coincida con `subido_en`.
3. `elegir`: entra en el editor.
4. `audio`: el chip «Audio suggéré» (se añade si no viene añadido) y se anota el tema. En `story_image_music` también `sticker-musica`, que coloca el sticker visible del tema dentro de la zona reservada.
5. `destino`: exige «Vos stories» (texto de S1) y que no esté marcado Amis proches. Lee el conmutador de Facebook y lo anota; no lo cambia (decisión tomada).
6. QA.
7. `compartir`.

**Confirmación:**

- Tras pulsar, el editor desaparece y se observa el aviso de subida (texto de S1).
- Luego el perfil muestra el anillo de story sin ver y se abre la story propia.
- `confirmado` exige cabecera `sabiduriabolsillo`, edad ≤ 3 min, la barra propia «Activité» y la captura del visor.
- Si `--produccion-cercana` y la producción tiene un target `instagram_story` en ese margen, baja a `confirmado_sin_prueba_unica`. En ese caso se concilia pasando la captura del visor y el máster al revisor: ¿es esta imagen?

**Lectores nuevos:** `destino_historia_correcto`, `chip_audio_historia`, `historia_propia_reciente(xml, max_s)` y `miniatura_galeria_historia`, si su content-desc difiere del selector de feed.

**Riesgos específicos:**

- **Copia automática en la Story de la Página** (insignia de Facebook en «Your stories»). Se registra como extra y la exclusión de Facebook en la ventana ya la cubre.
- El sticker o la etiqueta de música tapan texto. El máster reserva zona y la QA lo revisa.
- Instagram abierto en la cuenta personal: `abrir` falla cerrado.
- La story caduca a las 24 h: medir hacia las 6 h (la ventana siguiente) y antes de caducar.
- `tapado()` no ve el contenido de la imagen; eso lo cubre la QA visual.

**Sonda que lo desbloquea:** S1 (Instagram).

### B. Feed de Threads (`feed_single_image`, `feed_text`, `feed_image_music`)

**Pasos:**

1. `telefono-subir`, salvo en `feed_text`.
2. `th abrir`: lanzar → `barcelona_tab_profile` → exige la marca.
3. `nuevo`: `barcelona_tab_create` → compositor con el Button de identidad `sabiduriabolsillo`.
4. `texto`: `new_thread_screen_composer`, pegar (≤ 500) y releer.
5. `galeria`: `new_thread_screen_gallery_button` → miniatura por hora → confirmar (texto de S1).
6. `musica`: `new_thread_screen_music_button` → primer tema sugerido → anotar. Se omite en `feed_text`.
7. QA.
8. `compartir`: `new_thread_screen_post_button`.

**Confirmación:** el compositor se cierra, aparece el aviso de publicación si existe (S1) y la pestaña de perfil muestra el primer thread con **el texto exacto** y edad ≤ 3 min. El texto exacto lo identifica, así que la producción cercana (`hilos`) no rebaja el estado. La URL se obtiene del permalink, con «Réessayer» transitorio admitido una vez, o de la búsqueda en solo lectura de la sección 4.

**Riesgos específicos:**

- Casi duplicado con la ruta API de la misma familia y ráfaga con `hilos`: se registra y no frena.
- Un posible conmutador «compartir también en Instagram»: se registra como copia si está activo por defecto.
- Los resource-id pueden cambiar con una actualización; en ese caso se busca por texto y, si tampoco aparece, se falla cerrado.

**Sonda que lo desbloquea:** S1 (Threads).

### C. Feed de la Página de Facebook (`feed_single_image`, `feed_text`, `feed_image_music`)

**Pasos:**

1. `telefono-subir`, salvo en `feed_text`.
2. `fb abrir`:
   - Lanzar.
   - Si aparece un interstitial **de la tabla** («Ahora no» / «Not Now»), se pulsa como mucho una vez; cualquier otro detiene el flujo.
   - Nunca se toca «Anular» del aviso «Cambiaste a…».
3. `nuevo`: «¿Qué estás pensando?» → compositor que **debe** mostrar la identidad «Sabiduria De Bolsillo» y la audiencia «Público».
4. `galeria`: miniatura por hora.
5. `musica`: tema sugerido; se omite en `feed_text`.
6. `pie`: `pasos.escribir_texto` en el `AutoCompleteTextView`.
7. `siguiente`: pantalla final (S1).
8. QA.
9. `compartir`: vuelve a exigir identidad y audiencia en dos volcados antes de pulsar.

**Confirmación:** el compositor se cierra y aparece «Publicando…» u otro aviso (S1). Luego, en el perfil de la Página, la primera publicación debe tener autor «Sabiduria De Bolsillo», edad «Ahora» o «1 min», «Público» y **el pie exacto**. El contador redondeado no se usa.

- Si la publicación aparece con el autor personal, el estado es `fallido` con `identidad: personal` y un aviso destacado en el informe: requiere al usuario.
- Un pie idéntico a otro publicado en las últimas 24 h, por ejemplo la copia automática de una foto de Instagram de una ventana anterior, rebaja a `confirmado_sin_prueba_unica`. `lab.py fb pie` rechaza de entrada un pie igual al de un run de Instagram por teléfono de las últimas 24 h.

**Riesgos específicos:**

- Publicar como perfil personal si el cambio de perfil se revierte: doble comprobación antes de pulsar y comprobación del autor después.
- Interstitials nuevos: fallan cerrado.
- Una foto con música puede salir como vídeo: se anota el tipo real en el run.
- Borrador guardado al salir («¿Guardar borrador?»): lo cubre `telefono-descartar`.

**Sonda que lo desbloquea:** S1 (Facebook, compositor y pantalla tras «Siguiente»).

### D. Story de la Página de Facebook (`story_image`, `story_image_music`)

**Pasos:**

1. `telefono-subir`.
2. `fb-historia abrir`: inicio → «Crear historia» → exige identidad de Página en el creador (señal de S1).
3. `elegir`: miniatura por hora.
4. `audio`: «Música» y tema; en `story_image_music`, sticker visible en la zona reservada.
5. QA.
6. `compartir`: exige destino Página y lee sin cambiarlo el conmutador «Compartir en Instagram», si existe.

**Confirmación:** el visor propio muestra la cabecera «Sabiduria De Bolsillo ✓», el pie «Agregar nueva» / «Compartir como publicación» y edad reciente, más la captura. Con producción cercana que publique una Story de Facebook, baja a `confirmado_sin_prueba_unica` y se concilia por captura, como en A.

**Riesgos específicos:**

- Cuenta personal frente a Página.
- Si Facebook copia en Instagram, es una copia nueva: se añade a `RECETAS` y excluye Instagram en la ventana.
- Stickers que tapan contenido.

**Sonda que lo desbloquea:** S1 (Facebook Story).

### E. Encuestas (`story_poll` en Instagram y Facebook, `feed_poll` en Threads)

**Stories:** es la receta A o D más el paso `encuesta`:

1. Panel de stickers → «Sondage» / «Encuesta» (encuesta clásica de 2 opciones: las celdas dicen *single-choice*).
2. Pegar la pregunta y las opciones y releerlas con `stickers.encuesta_escrita`.
3. `telefono.arrastrar` hasta `destino_arrastre(zona_reservada)`.
4. Volcado estable y `sticker_en_zona` sobre los bounds leídos.
5. Si no queda dentro tras 2 arrastres: `PantallaInesperada` y abandono del borrador.

El máster **no** lleva las opciones impresas (en LAB-SMOKE-001 se duplicaron y el sticker las tapó). **Confirmación:** la de A o D, más la captura del visor con la encuesta dentro de la zona, que revisa la QA.

**Threads:** receta B con `encuesta`: menú de adjuntos → `new_thread_screen_poll_button` → campos de S1 → pegar y releer. Se deja la duración por defecto. **Confirmación:** la de B, más la encuesta visible en el thread.

**Riesgos específicos:**

- La posición en el volcado puede ir con retraso: la regla es `esperar_estable`, y la última palabra la tiene la QA sobre la captura.
- El arrastre puede escalar o rotar el sticker: `sticker_en_zona` comprueba los bounds completos, no solo el centro.

**Sondas que lo desbloquean:** S1 (paneles) y S2 (arrastre).

### F. Multiimagen y secuencias

- **Carrusel de Instagram:** receta `ig` con `--subido-en` ×N y multiselección.
- **Story en secuencia (Instagram y Facebook):** multiselección en el selector de Story, que crea N fotogramas.
- **Multifoto de Facebook:** Galería con multiselección.
- **Carrusel de Threads:** galería con multiselección.

**Lector nuevo:** `selecciones_ordenadas(xml, subidas)` generaliza `seleccion_unica`. Exige exactamente N seleccionadas, ordinales 1..N en el orden de los fotogramas y cada miniatura dentro de la tolerancia de su `subido_en`.

**Confirmación:**

- La del flujo base.
- En carrusel, el indicador de N páginas y una captura por fotograma, deslizando dentro de la publicación propia.
- En secuencias, el visor avanzado fotograma a fotograma con captura de cada uno.

La QA recibe todas las capturas y el orden de los másters.

**Riesgos específicos:**

- Orden equivocado.
- La rejilla de Facebook no es un carrusel: se registra el tratamiento real.
- La música puede no ofrecerse en multiselección. En ese caso la sonda lo documenta y la celda registra `music_unavailable_in_native_composer`, con captura, sin bloquear.
- Encargos de N fotogramas: más carga para Codex y cambio en su prompt.

**Sondas que lo desbloquean:** S1 y S3.

## 4. Verificación sin permalink ni conteo

- **Feed de Facebook y Threads:** confirmación en pantalla (sección 3). Después, para tener `post_id` y URL y poder medir, el workflow `media-lab-verify` gana un modo de solo lectura: `-f buscar=<red>` con el pie de un manifiesto. Lista las últimas publicaciones de la Página o de la cuenta de Threads, devuelve la que casa con el pie exacto y se escribe en el run. Los tokens siguen en GitHub Secrets.
- **Stories:** la confirmación es la captura del visor propio. Las métricas salen de la lectura de Stories vivas por API en ese mismo modo, si el adaptador la soporta. Si no, se hace una captura de «Activité» / estadísticas por teléfono en una ventana con el teléfono listo. Si tampoco se puede, la instantánea queda como `missing_data_reasons`.

## 5. Orden de implementación

| # | Tarea | Depende de | Celdas |
|---|---|---|---|
| 0 | Cerrar la fase 1: tarea 10f (el detector no ve el desplegable de hashtags; bloqueante) y tarea 14. La 10e y la primera ventana supervisada (CELL-018, 2026-09-14) ya están hechas | — | — |
| 1 | **R. Refactor común:** `pantalla.py`, `pasos.py`, `reloj.py`, zonas relativas, `textos.py`, `recetas.py` con la receta del feed de Instagram, alias `TELEFONO_FASE_1`, regla de un teléfono por ventana, `telefono-atras --app`, `telefono-descartar`, `receta`, `sonda`, `fixtures.podar`, `preflight` con versiones. Todas las pruebas existentes verdes sin cambiarlas. | 0 | — |
| 2 | Cambio del prompt de la ventana (sección 1E) | 1 | — |
| 3 | **Sonda S1** y fixtures podados | 1 | — |
| 4 | A0: registrar `instagram/feed_image_music` | 1 | 1 |
| 5 | **A. Story de Instagram** (misma app e idioma que la fase 1: valida el refactor con el caso más parecido) | 3 | 6 |
| 6 | **B. Feed de Threads** (resource-id estables; puede ir en paralelo con 5) | 3 | 7 |
| 7 | Modo `buscar` de `media-lab-verify` | — (en paralelo) | — |
| 8 | **C. Feed de la Página de Facebook** | 3, 7 | 6 |
| 9 | **D. Story de la Página de Facebook** (reutiliza lectores de 5 y 8) | 5, 8 | 6 |
| 10 | Sonda S2, `stickers.py`, `zona_reservada` en encargos y `render_overlay` → **E. Encuestas** | 5, 6, 9 | 6 |
| 11 | Sonda S3, `fotogramas` en encargos y en el prompt de Codex (lo pega el usuario) → **F. Multiimagen y secuencias** | 5, 6, 8, 9 | 20 |
| 12 | Sonda G0 y plan de la fase 3 (vídeo) | 3 | — |

Cada flujo entra en `RECETAS` solo cuando se cumplen tres condiciones:

1. Sus pruebas con teléfono simulado pasan.
2. Su primera publicación sale en una ventana manual (`--dueno manual`) dirigida por Claude paso a paso con `confirmado`. Esa ventana no pide confirmación humana antes de publicar.
3. `findings.md` recoge lo aprendido.

Hasta entonces, la tarea programada no lo elige.

## 6. Decisiones abiertas con valor por defecto

Cada una trae un valor para que la planificación no se bloquee.

**1. LaunchAgent `com.sabiduria.medialab.phone-awake`** (actividad cada 45 s; choca con «nunca mantener despierto»).
**Por defecto propuesto (el usuario puede cambiarlo):** se retira. El usuario lo descarga (`launchctl bootout`, porque es configuración persistente de su Mac) y el plan corrige la línea de `progress.md` que lo da por necesario. La spec de la fase 1 ya no depende de él (riesgo de MaaS360). `preflight` informa si sigue cargado, sin tocarlo.
Motivo: la decisión tomada prohíbe despertar el teléfono, y el código ya salta las celdas si no está listo.

**2. Encuestas y stickers en Stories.**
**Por defecto propuesto (el usuario puede cambiarlo):** encuesta nativa obligatoria (es el tratamiento que mide la celda), clásica de 2 opciones, con máster de zona reservada sin opciones impresas y colocación automática por arrastre verificada por volcado y QA. Si la colocación falla dos veces, la celda se abandona y queda `blocked`; no se sustituye por la pregunta impresa.
Motivo: una pregunta impresa sería otro tratamiento y contaminaría la comparación. El fallo de SMOKE se debió al máster, no a la encuesta.

**3. Música en celdas `*_music` frente a las demás.**
**Por defecto propuesto (el usuario puede cambiarlo):**
- En feed (Instagram, Facebook, Threads), `feed_image_music` usa la misma receta que `feed_single_image`, y la celda sigue siendo distinta a efectos de medición.
- En Stories, `story_image` lleva el audio añadido por el chip, sin sticker grande, y `story_image_music` lleva además el **sticker de música visible** en la zona reservada.

Motivo: con la música obligatoria, la única diferencia observable que queda está en Stories, y así las celdas no se fusionan en `coverage.json`.

**4. Copia automática de la Story de Instagram en la Story de la Página.**
**Por defecto propuesto (el usuario puede cambiarlo):** se aplica la decisión ya tomada para el feed. Se deja activa, se registra en `publication.cross_posting` como extra y en esa ventana no sale ninguna celda de Facebook (la regla actual de `compatibles` ya lo cubre). Si S1 descubre otras copias (Facebook → Instagram, Threads → Instagram), se tratan igual.
Motivo: coherencia con la decisión del usuario y ningún cambio de ajustes de cuenta.

**5. Verificación sin permalink ni conteo.**
**Por defecto propuesto (el usuario puede cambiarlo):** basta la lectura en pantalla más la captura para `confirmado`. En Stories: visor propio con marca y edad. En el feed de Facebook y en Threads: primera publicación con autor, edad y **pie exacto**. Con producción cercana del mismo tipo, baja a `confirmado_sin_prueba_unica` y se concilia por captura. La URL y el `post_id` se completan después con el modo de solo lectura de `media-lab-verify` (sección 4), sin retrasar la ventana.
Motivo: el pie exacto identifica la publicación sin depender del contador redondeado, y la lectura por API ya existe como adaptador.

**6. Etiqueta de ubicación nativa (LAB-LOCATION-011).**
**Por defecto propuesto (el usuario puede cambiarlo):** se permite solo un **lugar público real** citado en el brief (museo, monumento, ciudad), buscado por nombre exacto. Nunca la ubicación actual del teléfono, ni sugerencias «cerca de ti», ni lugares privados. Si la búsqueda no da coincidencia exacta, sale sin sticker, con la etiqueta visible impresa, y se registra `location_not_offered`.
Motivo: respeta la prohibición de check-in y de ubicación privada, y coincide con el tratamiento de la celda («native location sticker if offered»).

**7. Alcance de Edits y vídeo.**
**Por defecto propuesto (el usuario puede cambiarlo):** el vídeo pasa a una fase 3. En la fase 2 solo se hace la sonda G0. La música del catálogo de Meta se admite **solo añadida dentro de Edits, Instagram o Facebook y compartida directamente desde la app**, nunca descargada y resubida. LAB-NARRATED-009 queda `planned` hasta que haya voz propia. Los másters de vídeo los montará Claude en la fase 3 a partir de imágenes aprobadas.
Motivo: Codex solo genera imágenes, la primera exportación se rechazó por duración, encuadre y audio, y quedan 17 días de campaña.

**8. TikTok.**
**Por defecto propuesto (el usuario puede cambiarlo):** fuera de la implementación de la fase 2. Cuando el usuario resuelva el puzle: sonda sin publicar (paquete, importación, borrador, vista previa y música), después alta de celdas solo para **publicación de fotos con música** (lo que produce el laboratorio) y un módulo `tiktok_foto.py` con el patrón de esta spec, espaciado respecto a la publicación Meta de la misma variante.
Motivo: todo es desconocido, y el vídeo depende de la fase 3.

**9. Marcadores `selected_after_day_7`.**
**Por defecto propuesto (el usuario puede cambiarlo):** el 2026-09-20 Claude asigna a cada marcador el formato implementado por teléfono, en esa red y superficie (feed o Story), con mejor alcance por seguidor a 72 h entre las celdas maduras. Si no hay dos celdas maduras comparables, usa `feed_single_image` o `story_image`. Deja el motivo en `capability_evidence` y `progress.md`.
Motivo: es una regla objetiva que no bloquea, y usa flujos ya probados.

**10. Threads nativo junto a la API y a `hilos`.**
**Por defecto propuesto (el usuario puede cambiarlo):** se publica aunque haya casi duplicado con la ruta API de la misma familia o ráfaga con `hilos`. Se anota en `exposure_context` del run y no frena.
Motivo: es la aplicación directa de la decisión tomada sobre colisiones.

## 7. Pruebas

Se sigue el patrón de `tests/test_media_lab.py` (script con `check()`, sin pytest).

**Fixtures reales podados:**

- Cada fixture sale de un volcado de S1–S3 pasado por `fixtures.podar`.
- Una prueba recorre `tests/fixtures/telefono/**.xml` y falla si hay texto o descripción no vacíos que no estén en `textos.py`, no sean de la marca o no sean de la forma de fecha y edad esperada.
- Ningún fixture puede contener nodos de `com.android.systemui`.
- Los volcados crudos no salen de `evidence/`.

**Lectores puros, contra fixtures:**

- identidad por app: marca frente a cuenta personal, y Página frente a perfil;
- miniatura por hora (Story de Instagram, Facebook, Threads);
- destino de Story y conmutadores;
- compositor listo por flujo;
- `historia_propia_reciente`, `thread_reciente` y `publicacion_reciente_pagina` con el pie exacto y con uno parecido;
- `selecciones_ordenadas` (orden correcto, invertido, N−1);
- `sticker_en_zona` y `destino_arrastre`;
- `encuesta_escrita`;
- interstitial conocido y desconocido;
- diálogo de descarte.

Casos límite: un fixture en inglés, del teléfono antiguo, falla cerrado con un mensaje de idioma; zonas relativas con volcados de 2316 y 2340 de alto.

**Teléfono simulado por flujo:**

- `TelefonoSimulado` gana `arrastrar`, `recientes_mediastore` y el reloj de `labkit/reloj.py`.
- Camino feliz de cada receta con la secuencia de fixtures: número exacto de toques y **exactamente un toque** en el botón de envío.
- Identidad equivocada: ningún toque de composición.
- Teléfono no listo a mitad de flujo: `TelefonoNoListo` sin tocar nada.
- Desplegable que aparece en el segundo volcado tras pegar: un «atrás».
- Estados de `observar_envio` por flujo, incluida la rebaja por producción cercana en Stories.
- `sonda tocar` se niega con cualquier texto de `ENVIO`.
- Cualquier E/S real lanza `IntentoDeES`.

**Registro y selección:**

- Cada par de `RECETAS` tiene sus subcomandos en `lab.construir()`, y cada paso de receta existe en `choices`.
- `TELEFONO_FASE_1 == TELEFONO_IMPLEMENTADO` (alias).
- Nunca dos celdas `android_native` en una ventana.
- Exclusión por copias declaradas.
- `encargo-nuevo` valida `zona_reservada` (dentro de 1080×1920) y `fotogramas` (2–10, con el mismo número de prompts).

**Sondas:** las de la sección 2, siempre supervisadas y sin publicar.

## Riesgos generales

- **La interfaz cambia sin aviso.** Actualizaciones, pruebas A/B o cambio de idioma. Mitigación: textos en tablas por app, fallo cerrado con captura y fixtures fechados por versión en `preflight`. Actualizar un fixture exige un volcado nuevo del teléfono, nunca editarlo a mano.
- **MaaS360 bloquea a mitad de flujo** y deja un borrador abierto. La siguiente ventana lo ve como `BorradorPendiente` y no toca nada; lo resuelve una persona. La regla de un teléfono por ventana reduce la exposición, pero no la elimina.
- **Volcados con retraso.** `esperar_estable` antes de cada lectura decisiva. La captura es la evidencia y la QA tiene la última palabra sobre lo visible.
- **Publicar como la identidad equivocada**, sobre todo en Facebook: doble comprobación antes de pulsar y comprobación del autor después. Si se detecta, alerta en el informe y no se repite.
- **Carga de audiencia.** Más celdas por teléfono, copias automáticas en Stories y coincidencias con producción. Todo se registra como factor de confusión; las copias no cuentan como celdas.
- **Datos personales.** Los volcados crudos de inicio y notificaciones contienen contenido ajeno. A `tests/` solo van fixtures podados y comprobados por prueba.
- **Calendario.** Con 17 días, el orden de la sección 5 prioriza A, B, C y D (25 celdas). E y F dependen de cambios en encargos y en el prompt de Codex, que el usuario tiene que volver a pegar.
- **Protocolo de scrcpy 4.1** en `phone_clipboard.py`: todos los flujos nuevos pegan texto por esa vía, así que una actualización de Homebrew los rompe todos a la vez. El test de bytes lo detecta.
