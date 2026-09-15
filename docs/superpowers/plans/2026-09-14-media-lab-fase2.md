# Laboratorio de medios, fase 2 (publicación nativa por teléfono más allá del feed de Instagram) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la ventana de publicación de Claude saque por teléfono las 69 celdas `android_native` que hoy no puede elegir (Stories, Threads, Facebook, encuestas y multiimagen), cada flujo con lectores puros probados contra volcados reales podados, con su primera publicación en una ventana manual `confirmado` y sin ninguna celda sin PASS de QA visual.

**Architecture:** Lo genérico sale de `instagram_pantallas.py` e `instagram_feed.py` a `labkit/pantalla.py` (lectura pura), `labkit/pasos.py` (E/S común: esperas, escritura, envío con un solo toque) y `labkit/reloj.py`. Los textos de la interfaz viven en `labkit/textos.py` y son a la vez la lista blanca de los fixtures. Cada red y formato tiene un módulo de lectores puros (`<app>_pantallas.py`) y uno de pasos (`<app>_<superficie>.py`), y solo cuenta como implementado cuando entra en `labkit/recetas.py`, que también dice a la ventana qué comandos ejecutar y qué debe verse en cada captura.

**Tech Stack:** Python 3 del `.venv` del repo (pillow, requests), adb, scrcpy-server 4.1 (`phone_clipboard.py`), `gh`, GitHub Actions (`media-lab-verify`), tareas programadas de Claude.

**Spec:** `docs/superpowers/specs/2026-09-14-media-lab-fase2-design.md`. **Plan anterior (vigente en lo que este no cambia):** `docs/superpowers/plans/2026-09-14-media-lab-chatgpt-claude-fase1.md`.

**Valores por defecto aplicados (sección 6 de la spec):** se retira el LaunchAgent `phone-awake` (lo descarga el usuario); encuesta nativa clásica de 2 opciones con máster de zona reservada y colocación por arrastre (2 fallos → `blocked`); en feed, `feed_image_music` = receta de `feed_single_image`, y en Stories `story_image_music` añade el sticker de música visible; la copia automática de Instagram en la Story de la Página se deja activa y se registra; `confirmado` por lectura en pantalla más captura, con URL y `post_id` después por el modo `buscar`; ubicación solo de lugar público real citado en el brief; vídeo a la fase 3 (solo sonda G0); TikTok fuera; marcadores `selected_after_day_7` por la regla del 2026-09-20; Threads publica aunque haya casi duplicado con API o `hilos`.

**Convenciones (las de la fase 1):**

- Pruebas: script `tests/test_media_lab.py` con `check(cond, "mensaje")` y `FALLOS`, sin pytest. Cada sección nueva se añade antes de `SECCIONES` y se registra al final de esa lista. Comando único, desde la raíz del árbol en que se trabaja: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py` (el `.venv` solo existe en el árbol principal); en verde termina con `El laboratorio cumple sus contratos.`
- No ejecutar la batería mientras corre `lab.py generar`: la guardia tomaría sus escrituras por cambios ajenos.
- Commits con prefijo `media lab claude: ` y el trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Solo rutas concretas en `git add`, nunca `-A`. Se hace push (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`) en los commits que cambian lo que lee la ventana programada (prompt, recetas promovidas y selección), siempre antes de actualizar la tarea programada y antes de cada sesión supervisada con el teléfono, que usa el código ya integrado.
- Ningún paso de este plan pulsa un botón de envío salvo los de las ventanas manuales de primera publicación, que sigue Claude con la receta y el PASS de QA (sin confirmación humana, decisión del usuario).
- **Worktree.** Todas las tareas y subtareas de código se hacen en un git worktree separado (skill `superpowers:using-git-worktrees`), creado en la tarea 0 como `/Users/hec/dev/sabiduriaPublisher-fase2` en la rama `media-lab-fase2`: sus pruebas, sus `lab.py` sin teléfono y sus commits salen de ahí, y la integración es `git fetch origin main && git rebase origin/main && git push origin HEAD:main` desde el worktree. El árbol principal `/Users/hec/dev/sabiduriaPublisher` queda para las ventanas (que hacen `git fetch`/`git rebase` al empezar) y para las sesiones supervisadas con el teléfono y los cambios de datos (`coverage.json`, runs, fixtures de sondas), siempre con el cerrojo manual. Un subagente nunca trabaja en el árbol principal.
- Los pasos o subtareas marcados **«Controlador con el usuario presente (no subagente)»** los hace quien dirige la sesión, con el usuario delante: avisos al usuario, cambios de su configuración o de la tarea programada por MCP, sondas S1, S2, S3 y G0, comprobaciones en el teléfono real, ventanas manuales de primera publicación y el pegado del prompt de Codex. Un subagente no los ejecuta.
- Las cadenas marcadas **«confirmar contra el fixture de S1»** (o de S2/S3) son el texto esperado según la spec y `findings.md`. La tarea del flujo empieza sustituyéndolas por lo que la sonda anotó en `findings.md`; el código ya está escrito y no cambia de forma.
- Los números de línea de `tests/test_media_lab.py` cambian mientras otros trabajos avanzan: este plan cita funciones, nunca líneas de ese archivo.

**Desviaciones de la spec y decisiones de planificación:**

1. **Promoción en dos diccionarios.** `recetas.TODAS` guarda cada receta escrita; `recetas.RECETAS` solo las promovidas (`PROMOVIDAS`, con el run que las justifica) y `recetas.BORRADORES` el resto. `TELEFONO_IMPLEMENTADO` sale de `RECETAS`. Para la ventana manual de un flujo aún no promovido, `lab.py encargo-nuevo --borrador` y `lab.py receta --borrador` aceptan pares de `BORRADORES`; `seleccionar` nunca los elige.
2. **Una ventana manual por flujo, no por par.** En B y C, `feed_text` y `feed_image_music` se promueven con la ventana manual de `feed_single_image`: usan un subconjunto de sus pasos o los mismos, con la misma confirmación.
3. **Envío común.** `pasos.observar_envio(boton, observador, plazo=None, resultado=None)` (`plazo` resuelve a `OBSERVACION_S` si es `None`) devuelve `(estado, culpable)` en vez de escribir `fallo`/`estado` en el dict compartido; si se da `resultado`, solo recibe `submitted_at` y, si se confirma, `processing_completed_at` (los dos timestamps que dependen del instante de la observación). `pasos.enviar(*, paquete, nombre_app, etiqueta, evidencia, captura_antes, captura_final, captura_error, listo, botones, observador_nuevo, despues, extra=None, plazo=None)` envuelve la secuencia completa de `compartir` (doble volcado con `listo(xml, emergentes)`, un toque, observación, lectura posterior y capturas) para todas las apps; `captura_antes`/`captura_final`/`captura_error` sustituyen a la tupla `nombres` de la primera versión (revisión de la tarea 2). Rechaza con `ValueError` (antes de tocar nada) un `extra` que redefina una clave propia del resultado. `observador_nuevo(boton)` y una segunda `exigir_listo()` se llaman justo antes del toque pero fuera del `try` que lo envuelve: si fallan ahí, no se ha pulsado nada y no cuenta como `error_tras_pulsar`.
4. **Firma de `pasos.escribir_texto`.** La spec la da como `escribir_texto(campo, texto, paquete)`; aquí es `escribir_texto(texto, paquete, *, campo, exigir, desplegable_nodos, emergente, volcados_limpios=None, intentos_atras=None, timeout=None, verificar=None)`, porque cada app aporta cómo localizar el campo, cómo exigir su compositor y cómo reconocer su desplegable por nodos y como ventana emergente; los tres primeros parámetros opcionales sustituyen a `VOLCADOS_LIMPIOS`/`INTENTOS_ATRAS`/`ESTABILIZACION_TIMEOUT_S` cuando no son `None`, y `verificar(xml, texto)` decide si el texto pegado quedó bien escrito (por defecto, `pantalla.tiene_texto` exacto, lo probado hoy en Instagram; Threads y Facebook pueden necesitar otra comparación, a confirmar en S1).
5. **`pasos.esperar_estable(lectura, n=None, descripcion=...)`** recibe una lectura que devuelve un valor (bounds, texto…) y exige `n` (`VOLCADOS_LIMPIOS` si es `None`) volcados seguidos con el mismo valor no nulo; una función booleana también sirve.
6. **Reloj.** Las pruebas nuevas sustituyen `labkit.reloj`, pero `con_telefono_simulado` sigue sustituyendo también `time.sleep` y `time.monotonic` globales (vía `instagram_feed.time`), porque las pruebas de la fase 1 dependen de ello; como `reloj` llama a `time` en cada uso, las dos sustituciones son coherentes. La spec pedía parchear solo `reloj`.
7. **Zonas relativas exactas.** «arriba» es `y2 ≤ 300/2340` del alto y «abajo» `y1 ≥ 1900/2340` (≈12,8 % y 81,2 %, los 13 % y 81 % de la spec redondeados): sobre 2340 px dan los mismos límites de hoy y ninguna prueba existente cambia.
8. **Desplegables como ventanas emergentes en todas las apps (novedad de la 10f).** `pasos.escribir_texto` y `pasos.enviar` consultan `telefono.ventanas_emergentes` igual que el feed de Instagram, y cada app define la emergente que cuenta (`emergente_desplegable` en Instagram, `emergente_compositor` en Threads y Facebook, con sus controles de referencia a confirmar en S1). La lógica genérica (`emergente_solapada`, `parece_desplegable`, `describe_emergente`) pasa a `pantalla.py`.
9. **Guardia de envío fuera de `compartir` (revisiones C1 e I-5; el diseño de abajo es el vigente tras varias rondas de revisión de la tarea 3, la última en `e10c9f2`).** Cuenta como envío el texto exacto de `textos.ENVIO` o `ENVIO_HISTORIA` (publicación directa de Stories en francés, español e inglés), una etiqueta que EMPIEZA por un texto de `ENVIO_HISTORIA` seguida de un separador no alfanumérico («Votre story, 2 nouvelles», «Amis proches (12)»), el id del botón de publicar de Threads, o una etiqueta que empieza por uno de `PREFIJOS_ENVIO` y no está en `NO_ENVIO` (las excepciones solo valen para la regla de prefijos, nunca anulan un `ENVIO`/`ENVIO_HISTORIA` exacto o por prefijo). Los prefijos en inglés («post», «share», «send») también atrapan etiquetas como «Posts» o «Shared»: la guardia falla cerrado (no toca); si eso bloquea un flujo, se añade una excepción confirmada, no se quita el prefijo.

   La comparación pasa por `textos.normalizar` (NFKC, sin caracteres de categoría `Cf` —incluidos los de ancho cero—, espacios colapsados y casefold); los títulos de diálogo (borrado y descarte) pasan además por `textos.normalizar_titulo`, que a partir de `normalizar` quita también las comillas (rectas, tipográficas, angulares o de ancho completo: «» "" ‘' "' ＂＇) y el espacio antes de un «?» de cierre — las comillas se quitan DESPUÉS de NFKC, nunca antes, porque NFKC convierte una comilla de ancho completo en la recta correspondiente. `textos.es_titulo_borrado(v)` y `textos.es_titulo_descarte(v, app)` envuelven esa comparación contra `TITULOS_BORRADO` y `DESCARTE[app]["titulos"]`. Las formas normalizadas de `ENVIO`, `NO_TOCAR`, `NO_ENVIO`, `TITULOS_BORRADO` y `DESCARTE` (`_ENVIO_NORM`, `_NO_TOCAR_NORM`, `_NO_ENVIO_NORM`, `_TITULOS_BORRADO_NORM`, `_DESCARTE_TITULOS_NORM`) se precalculan una vez al importar `textos.py`, no en cada llamada; lo que llega de fuera (`permitir`/`ignorar`) se normaliza siempre al vuelo.

   `pantalla.es_envio(xml, n, ignorar=())` (sin parámetro `paquete`: la regla del centro no filtra por paquete, así que no hacía falta) cuenta como envío: el propio `n`; cualquier nodo del volcado (de cualquier paquete) cuyas bounds contengan el centro del toque y sea, él mismo, de envío; o cualquier nodo PULSABLE cuyas bounds contengan el centro y tenga un descendiente de envío (cubre tanto el antecesor clickable de la propia rama como cualquier otro contenedor pulsable de otra rama que solape ese punto — un botón de pantalla completa sin etiqueta propia que envuelve un «Partager» bloquea cualquier toque dentro, a propósito: falla cerrado). `pasos.tocar(n, xml, permitir=())` no pulsa ningún control de envío y es la vía de los toques sobre controles localizados en el volcado de los flujos nuevos. **No** pasan por ella, porque no apuntan a un control de la app sino a un campo de texto o a una posición calculada: el toque del campo en `escribir_texto` y `pegar_en`, el «+» del chip de audio (`punto_mas`), `tocar_derecha` en el visor y los arrastres; el feed de Instagram de la fase 1 (`instagram_feed`) conserva sus toques directos salvo la selección múltiple.

   `permitir` es una lista blanca explícita que exime, CAMPO a campo (texto, desc o resource-id), el valor que coincida —exacto o por prefijo seguido de un separador no alfanumérico, la misma regla que `ENVIO_HISTORIA`, vía `textos.coincide_o_prefijo`— con una etiqueta de la lista, en cualquier nodo del volcado que la tenga (no solo el nodo tocado), sin ocultar ningún otro control de envío. `coincide_o_prefijo` rechaza con `TypeError` un `candidatos` de tipo `str`/`bytes` (cada carácter contaría como un candidato distinto). La usará el visor propio de la fase 2 para abrir la Story propia de Instagram y la miniatura «Tu historia» de Facebook, tras verificar la pantalla. La spec no preveía esta guardia.
10. **Diálogos de borrado (revisión I1).** `textos.TITULOS_BORRADO` hace fallar cerrado a `boton_descarte`, y Threads no tiene diálogo de descarte automático hasta que S1 lo observe y no sea de borrado.
11. **Fixture en inglés sintético.** El Samsung SM-S918B ya no está conectado y los volcados crudos no se leen desde `evidence/` para las pruebas: el caso límite de idioma usa un volcado sintético con la estructura del perfil y los textos en inglés.
12. **Stickers en A.** `stickers.py`, `telefono.arrastrar` y `pasos.colocar_sticker` llegan con la Story de Instagram (11b-1), porque `story_image_music` los necesita; `story_image_music` (Instagram y Facebook) solo se promueve tras la sonda S2 (tarea 16c), que valida el arrastre.
13. **URL y métricas por `buscar`.** La URL de Threads y Facebook por teléfono solo se obtiene con el modo `buscar` de `media-lab-verify` (la spec lo admite como alternativa al permalink), con un margen de 2 min antes de `desde`. Las Stories de Instagram piden `insights` en la misma búsqueda; si no llegan, no se relanza y la métrica sale del teléfono o de `missing_data_reasons`. Las de Facebook no lanzan búsqueda de métricas.
14. **Resource-id de Threads sin respaldo por texto.** Si un resource-id del compositor cambia, el lector no encuentra el control y el paso falla cerrado; la búsqueda alternativa por texto que menciona la spec no se implementa.
15. **Pasos y subcomandos añadidos a la tabla 1D de la spec:** `actividad` en `ig-historia` y `fb-historia` (métricas por teléfono), `opciones` en `fb-historia` (lee «Compartir en Instagram» donde lo sitúe S1), `--fotogramas N` como argumento común, `--zona` en `lab.py render` (16a), la acción `lanzar` de `sonda`, `lab.py manifiesto-busqueda` y `lab.py fixture-podar`; y las evidencias de los runs `SONDA-F2-*` van a `evidence/android/sondas-f2/`, que el `.gitignore` vigente ya ignora (`evidence/android/*`).
16. **Ubicación (decisión 6).** La fase 2 no automatiza el sticker de ubicación: una celda que lo pida sale con la etiqueta impresa y `location_not_automated_phase2` en `missing_data_reasons` (no `location_not_offered`, que diría que se intentó).
17. **`publication.caption_path`** es un campo nuevo del run (ruta del pie publicado) que la ventana rellena en los runs de teléfono; lo lee la regla de 24 h de `lab.py fb pie`.
18. **Celdas solo de texto sin encargo.** `feed_text` de Threads y de Facebook no llevan imagen: `seleccion._necesita_encargo` las deja salir sin encargo aprobado cuando su receta tiene `formato_encargo` vacío.
19. **Prompt de la ventana por partes.** La tarea 8 solo sube lo que ya existe tras el refactor; cada subtarea de flujo añade su fragmento al prompt cuando su código existe y actualiza la tarea programada con el prompt entero, manteniendo su `cronExpression` y su paso 0.
20. **Primer push del refactor al final de la tarea 5**, tras una comprobación supervisada del feed de Instagram en el teléfono real sin publicar, y no en la tarea 4.
21. **Ritmo: una ventana cada 5 horas (decisión del usuario, 2026-09-15).** Sustituye las «3 ventanas al día» de la spec: 5 ventanas diarias cuya hora local se desplaza +1 h cada día, con hasta 2 celdas por ventana (hasta 10 al día). Lo implementa la fase 1, fuera de este plan: la tarea `sabiduria-media-lab` se dispara cada hora (`40 * * * *`) y su paso 0, `lab.py turno`, solo deja seguir en el turno de 5 h (ancla 2026-09-15 00:40 Europe/Madrid, `experiments/media-lab/turnos.json`). La misma tarea 15 de la fase 1 (`38c329a`, `38dc46b`, `d8ac308`) marca el turno atendido con `lab.py turno --marcar` tras tomar el cerrojo, sube la cola de encargos a 10 (`MAX_EN_COLA` y su prueba) y crea los másters con `lab.py render`/`lab.py tarjeta`. La tarea 0 lo comprueba; el prompt de la tarea 8 parte del de `d8ac308` y cada actualización de la tarea programada mantiene el cron. Las ventanas nocturnas suelen encontrar el teléfono bloqueado: publican solo por API (nunca se despierta el teléfono) y lo anotan en `exposure_context` como factor de confusión.
22. **Medición de Stories.** La spec dice «hacia las 6 h (la ventana siguiente)»; con ventanas cada 5 h la siguiente llega a unas 5 h. Regla: cada Story se mide en la primera ventana en que tenga entre 4 h y 20 h y, si no hubo ninguna, en la última antes de que caduque a las 24 h (paso 8 del prompt y `verificacion` de las recetas de Story).
23. **Cola de encargos de 10.** Con hasta 10 celdas al día hacen falta hasta 10 encargos en cola: la tarea 15 de la fase 1 ya subió `encargos.MAX_EN_COLA` a 10 y dejó la prueba de la cola con 10; la tarea 8 solo comprueba el valor y el paso 5 del prompt lo cita. La automatización de Codex sigue generando como mucho 2 encargos por pasada y con su frecuencia actual: si la cola no baja, la ventana usa el rescate `lab.py generar`, y queda como propuesta al usuario acercar la frecuencia de Codex al ritmo de 5 h.
24. **Worktree para el código.** Toda tarea de código trabaja en `/Users/hec/dev/sabiduriaPublisher-fase2` (rama `media-lab-fase2`) y se integra con push; el árbol principal es de las ventanas y de las sesiones con el teléfono. Las subtareas que la spec permitía en paralelo (12 con 11, 13 con 11 y 12) van en serie o cada una en su propio worktree, nunca en el mismo árbol a la vez.
25. **Cerrojo manual en toda sesión con el teléfono o en el árbol principal.** Tareas 5 (Step 6), 9, 16c, 17e, 18 (Step 5), 19, 20 y las ventanas manuales 11d, 12d, 14d, 15d, 16e y 17f empiezan mirando el turno y con `lab.py lock-tomar --dueno manual`, renuevan antes de 90 min y terminan con `lab.py lock-soltar --dueno manual`.
26. **La tarea 17 depende de 16a y 16b.** Usa `zona_reservada` (16a), `_encuesta` (16b-1) y la firma de `threads_feed.compartir` con `opciones` (16b-2), que 17c reescribe con fotogramas. Es lo más simple: el orden de la spec ya pone E antes que F.
27. **Piezas de un solo commit.** 11b, 16b y 17b se parten en 11b-1/11b-2, 16b-1/16b-2 y 17b-1/17b-2.
28. **Tarea 4: la receta no promete la URL desde el teléfono (revisión I-1 y M-1).** Ningún subcomando de `lab.py` abre el menú de la publicación, así que `verificacion` del feed de Instagram manda la URL a `manifiesto-verificacion --instagram-shortcode` si se conoce el shortcode y, si no, a `missing_data_reasons.post_url` (paso 7f del prompt); la sección 15 lo comprueba. El `ver` de `telefono-captura ig-06-perfil` avisa de que ese comando no navega: si la captura no muestra el perfil, se anota y se usa `ig-05-publicado`. **Pendiente (M-2, tarea posterior):** la prueba de existencia de comandos de la sección 15 solo mira subcomando y paso, no las opciones; hay que parsear cada comando con `ap.parse_args`, sustituyendo cada `<valor>` y quitando los corchetes de los opcionales.
29. **Tarea 5: ajustes al código real.** La importación de `labkit` en `lab.py` conserva `metricas` y `turnos` (llegaron después de escribir el plan) y solo añade `recetas` y `textos`; la sección 16 envuelve los pasos con `--borrador` en `receta_temporal` en vez de asignar y hacer `pop` a mano; `receta_temporal` rechaza con `ValueError` un par promovido. `_paso_telefono` captura `pantalla.PantallaInesperada`, que es la misma clase que `instagram_feed.PantallaInesperada`. `telefono-atras` usa `pasos.atras` con el paquete de `textos.PAQUETES` para todas las apps (sin la rama de `instagram_feed.atras`, que era la misma llamada con el mismo paquete); el error de `lab.py receta` empieza por la celda.
30. **Tarea 6: ajustes al código real.** `cmd_sonda` rechaza con `textos.es_no_tocar(valor)` (normalizado: mayúsculas, espacios y caracteres de ancho cero) en vez de `valor not in textos.NO_TOCAR`, y la sección 17 añade «partager», «Publicar», «ANULAR» y «\u200bPartager» a los rechazos (sin volcar, tocar ni capturar) y `volcar` con criterio. El toque pasa por `pasos.tocar(n, xml)` sobre el mismo volcado que `pantalla.nodo_sonda` (doble guardia con la regla del centro de `es_envio`), no por `telefono.tocar` directo; `nodo_sonda` conserva su parámetro `paquete` (solo para elegir el nodo), así que la llamada del plan cuadra. El mensaje de `--supervisada` dice «sesión de exploración dirigida, nunca desde la ventana desatendida»: el teléfono es dedicado y el usuario no tiene que estar presente, pero el flag sigue siendo obligatorio. La prueba de `_evidencia` compara con `raiz/evidence/sondas-f2/…` porque `LabAislado` redirige `EVIDENCIA` a `raiz/evidence`, y comprueba aparte que el `EVIDENCIA` real es `experiments/media-lab/evidence/android`. La regla que ignora `sondas-f2/` es `experiments/media-lab/evidence/.gitignore:1:android/*`. **Revisión de seguridad de la tarea 6:** (B1) `textos.BORRADO_VERBOS` y `textos.es_texto_borrado` (verbo normalizado seguido de fin o separador); `cmd_sonda` rechaza con 2 un criterio de borrado (el valor o el sufijo de su resource-id) antes de volcar, y `pantalla.nodo_sonda` falla cerrado si cualquier nodo del volcado es un título de `TITULOS_BORRADO` o si el toque cae en un control de borrado (el nodo, un nodo que contiene el centro o un descendiente de un pulsable que lo contiene, la regla del centro de `es_envio`). (B2) El nodo se elige con `pasos.esperar_estable` sobre la clave (bounds, texto, desc, resource_id) de `nodo_sonda` en `VOLCADOS_LIMPIOS` volcados frescos seguidos, y se toca sobre el último; si `nodo_sonda` falla en cualquiera (p. ej. «Partager» donde estaba «Suivant»), sale con 4 sin tocar. (I1) `ENVIO_IDS` añade `share_footer_button` (documentado en la sonda SONDA-10F de la fase 1); de Facebook no hay constancia de ningún id y no se añade ninguno. `es_texto_envio` ya comparaba el sufijo por igualdad exacta. `cmd_sonda` mira también el sufijo del resource-id, así que un criterio `post_*`/`share_*` por id se rechaza por la regla de prefijos (falla cerrado; en los nodos del volcado `_bloquea_toque` sigue mirando el id completo y un contenedor `post_capture_*` no bloquea). (I2) Antes de `pasos.tocar`, `telefono.tapado(xml, n)` y `pantalla.emergente_solapada(telefono.ventanas_emergentes(paquete), [n["bounds"]])` fallan cerrado. (I3) `textos.permitido(valor, app, atributo="text")`: hashtags `#[^\W\d_]\w*` solo en `text` (`PATRONES_TEXTO`), ningún valor con 6 o más cifras seguidas salvo un texto exacto de la tabla, edades de 1 a 3 cifras (`EDADES_FIXTURE`, derivado de `EDADES`, cuya tabla de lectura no cambia) y del chip de audio solo el literal «Audio suggéré.» (un fixture del editor pierde el texto del chip y el tema). `PATRONES` no lo usa ningún lector, así que no hubo que separar regex de lectura. `fixtures` vacía un `resource-id` que no case `[a-z0-9_.]+:id/[a-z0-9_]+` con el paquete de la app, quita todo elemento que no sea `hierarchy`/`node` (y el texto suelto), y `revisar` recorre `iter()` entero. (Menores) `fixture-podar` rechaza un destino que es enlace simbólico o cuya carpeta resuelta sale de `tests/fixtures/telefono/` (antes y después de `mkdir`), devuelve `VolcadoIlegible` ante un `ParseError` y `FixtureVacio` (`fixtures.vacio`) si tras podar no queda ningún nodo del paquete ni ningún texto conocido de la app. **Re-revisión:** `pantalla.nodo_sonda` falla cerrado ante un botón sin texto ni desc cuyo final de id, partido por «_», tenga una palabra de `textos.ENVIO_ID_PALABRAS` (`textos.es_id_envio`: `composer_post_button`, `direct_private_share_x`), en el nodo elegido o en un nodo PULSABLE bajo su centro, nunca en cualquier contenedor (`followers_share_content` y `post_capture_*` no pulsables no bloquean; uno pulsable sin etiqueta sí, falla cerrado, y la prueba del contenedor `post_capture_*` de la primera revisión pasa a no pulsable). Tras mirar las ventanas emergentes, un último `volcado_fresco` tiene que dar la misma clave de `nodo_sonda`, y `tapado` y `pasos.tocar` van sobre ese volcado. `fixture-podar` rechaza `--pantalla` con sufijo `.xml`. Un hashtag de fixture no lleva 4 o más cifras seguidas (`#[^\W\d_](?!\w*\d{4})\w*`; ninguna tabla ni prueba lo necesitaba). Los fixtures del editor no conservan el tema del chip; las pruebas que lo lean usan XML sintético (`xml_editor_audio_sintetico` en las tareas 11a y 11b-2). **Revisión de calidad:** la regla del centro de `es_envio` y de las dos guardias de `nodo_sonda` es un único helper, `pantalla._bajo_el_toque(lista, n, bloquea, *, descendientes, solo_pulsables)` (desaparecen `_subarbol_bloquea`, `_borrado_en_toque` y `_envio_por_id_en_toque`, con la misma semántica); el toque de la sonda vive en `lab._tocar_sonda(paquete, criterios, ev, nombre)` con `_clave`, `_volcar_sonda`, `ESPERA_TRAS_LANZAR_S` y `ESPERA_TRAS_TOCAR_S`; `textos.PATRONES` pasa a `PATRONES_FIXTURE` y `PATRONES_TEXTO` a `PATRONES_FIXTURE_TEXTO` (las tareas 11a, 12a, 14a y 17a añaden a `PATRONES_FIXTURE`; el código de la tarea 3 de este plan conserva el nombre antiguo), `EDADES_FIXTURE` falla al importar si una cifra de `EDADES` queda sin acotar a 1-3, y `fixtures` ya no tiene `SIEMPRE_AJENOS` (lo cubre `pkg != paquete`).
31. **Arranque en frío de Instagram en `ig abrir` si ningún volcado es legible.** Medido en el teléfono el 2026-09-15 (`findings.md`): `lanzar` reanuda un Reel en marcha y `uiautomator dump` no responde. `pasos.esperar_que` lanza `SinVolcado` (subclase de `PantallaInesperada`) cuando ningún volcado se leyó; solo entonces `instagram_feed.abrir_nueva_publicacion` comprueba `exigir_listo`, llama UNA vez a `telefono.forzar_cierre` (`am force-stop`), relanza, espera 4 s y vuelve a esperar con el mismo criterio, y devuelve `"arranque_en_frio": true`. Con cualquier volcado leído (borrador a medias incluido) no se fuerza nada. Sección 18 de las pruebas. **Revisión de seguridad:** (I1) todo `PantallaInesperada`, `TelefonoError` u `OSError` (este desde la revisión de calidad) desde el intento de `forzar_cierre` en adelante (espera fallida, el propio cierre, `BorradorPendiente` o cualquier paso posterior de `abrir`) sale con el mismo tipo y `AVISO_ARRANQUE_EN_FRIO`, «(tras un arranque en frío: am force-stop de com.instagram.android)», al final del mensaje; si el teléfono deja de estar listo antes del cierre, el error sale sin el aviso. (I2) Antes de forzar el cierre se hace la captura `ig-00-antes-de-arranque-en-frio.png` y se leen los focos (`telefono.focos()`: `telefono.focos_de` sobre `dumpsys window`, el mismo comando que `estado`, con los componentes de `mCurrentFocus` y `mFocusedApp`, en forma larga o corta). Si la captura falla, no se lee ningún foco o CUALQUIERA de los dos contiene `MediaCaptureActivity` (`com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity`, todo el flujo de creación: selector, editor y compositor; consta en el plan de la fase 1 como padre del desplegable de hashtags, sonda SONDA-10F, y el 2026-09-15 como foco con el selector «Nouvelle publication» abierto), no se fuerza el cierre y sale `SinVolcado` con el mensaje original y el motivo; un diálogo de otra app en `mCurrentFocus` con el compositor en `mFocusedApp` también lo impide. Las pruebas usan los datos reales de `MainTabActivity` (perfil) y del selector; los nombres de las demás actividades son sintéticos. (Menor) La cabecera de `lab.py` nombra `SinVolcado` en el código 4. **Revisión de calidad:** `foco_de`/`foco` se sustituyen por `focos_de`/`focos` (nadie más las usaba), así que las pruebas pedidas «de `foco_de`» comprueban la lista de `focos_de`; `AVISO_ARRANQUE_EN_FRIO`, `CAPTURA_ANTES_DE_ARRANQUE` y `ACTIVIDAD_CREACION` suben por encima de `abrir_nueva_publicacion`; el `except` que pone el aviso incluye `OSError` (`type(e)(mensaje)` funciona con un solo argumento), con prueba de un fallo de disco al guardar la captura del selector. **Menores de la última revisión:** (m-2) si `type(e)(mensaje)` lanza `TypeError` (subclases de `OSError` con constructor de varios argumentos, como `urllib.error.HTTPError`), el error sale como `PantallaInesperada` con «`<tipo>: <mensaje>`» y el aviso, encadenado al original; (m-3) la constante se llama `ACTIVIDAD_CREACION`, porque cubre todo el flujo de creación y no solo el compositor.
32. **Recuento del perfil refrescado antes de leer `publicaciones_antes` y `publicaciones_despues`.** Medido en el teléfono el 2026-09-15 (`findings.md`): con el perfil en memoria, Instagram mostró 3718 cuando ya eran 3719, y `ig compartir` habría dado `conteo_no_cuadra` con una publicación buena. `instagram_feed._recuento_fresco` desliza UNA vez hacia abajo (`telefono.deslizar`, nuevo: `input swipe`, del estilo de `tocar`) con el gesto de `instagram_pantallas.gesto_de_refresco` (x en el centro de «Modifier le profil»; y desde el punto medio entre el recuento y el botón, 600 px hacia abajo sin salir del volcado), espera 3 s y exige el mismo recuento en 2 volcados frescos con `pasos.esperar_estable`. Si el inicio o el final del gesto caen sobre algo que no se toca (`pantalla.punto_bloqueado`: las reglas de `nodo_sonda` para envío, id de envío y borrado) no desliza y se queda la lectura sin refrescar, con aviso; si el gesto o la espera fallan, el recuento es None, con aviso. `ig abrir` añade `recuento_refrescado` y `avisos`, y tras un gesto que no estabiliza vuelve a esperar el perfil de la marca antes de tocar «Créer». En `compartir` todo es posterior a pulsar: cualquier excepción del refresco va a `avisos`. Sección 19 de las pruebas; las de `abrir` de las secciones 6 y 18 llevan dos volcados más del perfil en su guion. Falta comprobarlo en el teléfono real.

**Correspondencia con el orden de la sección 5 de la spec:**

| Spec | Tareas de este plan |
|---|---|
| 0 Cerrar la fase 1 (hecho en `6260b70`) | Task 0 (comprobación) |
| 1 R. Refactor común | Tasks 1–7 (primer push en la 5) |
| 2 Prompt de la ventana | Task 8 (lo que ya existe) y el paso de prompt de 11c, 12c, 13, 14c, 15c, 16d y 17d |
| 3 Sonda S1 y fixtures | Task 9 |
| 4 A0 | Task 10 |
| 5 A. Story de Instagram | Tasks 11a–11d |
| 6 B. Feed de Threads | Tasks 12a–12d |
| 7 Modo `buscar` | Task 13 |
| 8 C. Feed de la Página de Facebook | Tasks 14a–14d |
| 9 D. Story de la Página de Facebook | Tasks 15a–15d |
| 10 S2 y E. Encuestas | Tasks 16a–16e |
| 11 S3 y F. Multiimagen y secuencias | Tasks 17a–17f |
| 12 G0 | Task 18 |
| Decisión 9 (2026-09-20) | Task 19 |
| Cierre (lo que no llegue queda `planned` con motivo) | Task 20 |
| Decisión del 2026-09-15: una ventana cada 5 h | Task 0 (comprueba la tarea 15 de la fase 1), 8 (prompt de `d8ac308` y medición de Stories) y cada actualización de la tarea programada |

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `experiments/media-lab/labkit/reloj.py` | Crear | `dormir` y `monotonic`: el único punto de tiempo que las pruebas nuevas sustituyen |
| `experiments/media-lab/labkit/pantalla.py` | Crear | Lectura pura genérica: elegir controles, zonas relativas, pulsable, desplegables, evaluación del envío, pista de idioma, envío prohibido en sondas, diálogo de descarte, miniatura por hora, edades, casillas, estado confirmado, selecciones ordenadas |
| `experiments/media-lab/labkit/pasos.py` | Crear | E/S común: teléfono listo, esperas, volcado estable, escritura con portapapeles, «atrás», descarte, lanzar app, envío con un toque, colocar sticker, recorrer fotogramas |
| `experiments/media-lab/labkit/textos.py` | Crear | Paquetes, marcas, idiomas, `TEXTOS[app][clave]`, `ENVIO`, `ENVIO_HISTORIA`, descarte, `TITULOS_BORRADO`, edades y patrones permitidos en fixtures |
| `experiments/media-lab/labkit/recetas.py` | Crear | `TODAS`, `PROMOVIDAS`, `RECETAS`, `BORRADORES`, `para`, `renderizar` |
| `experiments/media-lab/labkit/fixtures.py` | Crear | `podar(xml, app)` y `revisar(xml, app)` |
| `experiments/media-lab/labkit/stickers.py` | Crear | `sticker_en_zona`, `destino_arrastre`, `zona_en_pantalla`, `lienzo`, `contenedor_de`, `bounds_de`, `encuesta_escrita` |
| `experiments/media-lab/labkit/instagram_historia.py` | Crear | Pasos de la Story de Instagram |
| `experiments/media-lab/labkit/threads_pantallas.py` | Crear | Lectores puros de Threads |
| `experiments/media-lab/labkit/threads_feed.py` | Crear | Pasos del feed de Threads |
| `experiments/media-lab/labkit/facebook_pantallas.py` | Crear | Lectores puros de Facebook (feed y Story de la Página) |
| `experiments/media-lab/labkit/facebook_feed.py` | Crear | Pasos del feed de la Página |
| `experiments/media-lab/labkit/facebook_historia.py` | Crear | Pasos de la Story de la Página |
| `experiments/media-lab/labkit/instagram_pantallas.py` | Modificar | Reexporta lo movido a `pantalla.py`; añade lectores de Story y de multiselección |
| `experiments/media-lab/labkit/instagram_feed.py` | Modificar | Usa `pasos.py`; carrusel con N subidas |
| `experiments/media-lab/labkit/telefono.py` | Modificar | `checked`/`selected` en `nodos`, `arrastrar`, `recientes_mediastore`, `URI_VIDEOS`, `versiones` |
| `experiments/media-lab/labkit/seleccion.py` | Modificar | `TELEFONO_IMPLEMENTADO` (alias `TELEFONO_FASE_1`), un teléfono por ventana, exclusión por copias, borradores |
| `experiments/media-lab/labkit/encargos.py` | Modificar | `zona_reservada`, `fotogramas` y `prompts_fotogramas` (`MAX_EN_COLA = 10` ya viene de la tarea 15 de la fase 1) |
| `experiments/media-lab/labkit/codex_rescate.py` | Modificar | Rutas `-f<k>` y prompt por fotograma |
| `experiments/media-lab/labkit/colision.py` | Modificar | `pie_instagram_reciente` (regla de 24 h) |
| `experiments/media-lab/labkit/manifiesto.py` | Modificar | `manifiesto_busqueda` y `ruta_busqueda` |
| `experiments/media-lab/lab.py` | Modificar | `receta`, `sonda`, `fixture-podar`, `telefono-descartar`, `telefono-atras --app`, `telefono-subir` repetible, `manifiesto-busqueda`, `ig-historia`, `th`, `fb`, `fb-historia`, `preflight` con versiones, `encargo-nuevo --borrador/--prompt-fotograma` |
| `experiments/media-lab/render_overlay.py` | Modificar | `--zona`: nunca escribe texto dentro de la zona reservada |
| `experiments/media-lab/verify_api.py` | Modificar | Modo `--buscar <red>` de solo lectura |
| `.github/workflows/media-lab-verify.yml` | Modificar | Entrada `buscar` y los ids de Página, Instagram y Threads |
| `experiments/media-lab/claude-ventana-prompt.md` | Modificar | Receta en lugar de la secuencia fija, conciliación, copias, borradores abiertos, métricas de Stories |
| `experiments/media-lab/codex-heartbeat-prompt.md` | Modificar | Encargos con `prompts_fotogramas` |
| `experiments/media-lab/findings.md` | Modificar | Resultados de S1, S2, S3, G0 y lo aprendido en cada primera publicación |
| `experiments/media-lab/progress.md` | Modificar | LaunchAgent retirado, versiones, celdas que no lleguen |
| `experiments/media-lab/coverage.json` | Modificar | Solo en las ventanas manuales y en la tarea 19 |
| `tests/fixtures/telefono/<app>/<pantalla>.xml` | Crear | Volcados reales podados por `lab.py fixture-podar` |
| `tests/test_media_lab.py` | Modificar | Secciones 12–26 y extensiones de `TelefonoSimulado` / `con_telefono_simulado` |

---

### Task 0: Punto de partida (fase 1 cerrada, ritmo cada 5 h y worktree)
> **Aviso obligatorio antes de ejecutar (2026-09-15, tras la tarea 16 de la fase 1, `f0a9cbd`…`cc56724`):** los prompts literales de la ventana que aparecen en este plan (tareas 8, 11c, 12c, 13, 14c, 15c, 16d y 17d) se escribieron sobre el prompt de la tarea 15 (`d8ac308`). La tarea 16 cambió después `experiments/media-lab/claude-ventana-prompt.md`: nueva regla de `gh run list` por `displayTitle` y nombres de artefacto de cada workflow, el paso 7e (descarga de `media-lab-result-<id>`) y el paso 8 completo (métricas con `-M24H/-M72H/-M7D/-MSTORY`, `media-lab-verify -f metricas=true` y `lab.py metricas-registrar`). **Cada tarea que pegue un prompt debe partir del archivo vigente en `main` y aplicar solo su cambio propio**; nunca pegar el texto literal de este plan tal cual, que borraría la tarea 16. Las pruebas `seccion_prompt_ventana` de esas tareas deben exigir además los fragmentos «metricas-registrar», «-M24H» y «media-lab-result-». Los workflows `media-lab.yml` y `media-lab-verify.yml` ya llevan `run-name` con la ruta del manifiesto, y `verify_api.py` redacta tokens por patrón y por valor: la tarea 13 (modo `buscar`) debe partir de ese código.


La fase 1 está cerrada: tareas 1–14 y 10b–10f hechas (`6260b70`). La 10f dejó el desplegable de hashtags detectado como `PopupWindow` a partir de `dumpsys window windows`, porque `uiautomator dump` no lo ve (`telefono.ventanas_emergentes_de` y `ventanas_emergentes`; `instagram_pantallas.emergente_desplegable`, `hay_desplegable_por_ventana`, `parece_desplegable` y `describe_emergente`; `compositor_listo(..., emergentes=None)`). Las tareas 1 y 2 generalizan esa detección para todas las apps. La fase 1 no dejó fixtures en `tests/fixtures/`.

Por decisión del usuario del 2026-09-15, la fase 1 pasa la ventana de publicación a una cada 5 horas: `sabiduria-media-lab` se dispara cada hora (`40 * * * *`) y su paso 0, `lab.py turno`, solo deja seguir cuando toca (ancla 2026-09-15 00:40 Europe/Madrid, `experiments/media-lab/turnos.json`). Lo implementa la tarea 15 de la fase 1 (commits `38c329a`, `38dc46b` y `d8ac308`), que además marca el turno con `lab.py turno --marcar` tras el cerrojo, sube `MAX_EN_COLA` a 10 y crea los másters con `lab.py render`/`lab.py tarjeta`. Este plan no lo implementa: lo comprueba aquí.

**Files:** ninguno.

- [ ] **Step 1: Crear el worktree de la fase 2**

Con la skill `superpowers:using-git-worktrees`, desde `/Users/hec/dev/sabiduriaPublisher` y sin tocar sus archivos:

Run: `git fetch origin main && git worktree add ../sabiduriaPublisher-fase2 -b media-lab-fase2 origin/main`
Expected: el worktree en `/Users/hec/dev/sabiduriaPublisher-fase2` en la rama `media-lab-fase2`. Todas las tareas de código se hacen desde ahí.

- [ ] **Step 2: Comprobar el punto de partida (desde el worktree)**

Run: `git log --oneline -1 6260b70`
Expected: `6260b70 media lab claude: plan — fase 1 cerrada`

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python experiments/media-lab/lab.py turno`
Expected: JSON con `toca` y `siguiente_madrid` (sin `--marcar`: marcar es solo de la ventana programada), y `experiments/media-lab/turnos.json` existe.

Run: `grep -n "turno --marcar" experiments/media-lab/claude-ventana-prompt.md && grep -n "MAX_EN_COLA = 10" experiments/media-lab/labkit/encargos.py && grep -n 'add_parser("render")' experiments/media-lab/lab.py`
Expected: una línea de cada. Si falta alguna, la tarea 15 de la fase 1 no está en `origin/main`: parar y avisar al usuario.

- [ ] **Step 3: Comprobar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Con `mcp__scheduled-tasks__list_scheduled_tasks`: `sabiduria-media-lab` tiene `cronExpression` `40 * * * *` y un prompt cuyo paso 0 es `lab.py turno`. Si `lab.py turno`, `turnos.json` o ese cron no existen todavía, la fase 1 no ha terminado ese cambio: parar y avisar al usuario antes de seguir.

Sin commit.

---

### Task 1: `reloj.py` y `pantalla.py` (refactor R, parte 1)

**Files:**
- Create: `experiments/media-lab/labkit/reloj.py`
- Create: `experiments/media-lab/labkit/pantalla.py`
- Modify: `experiments/media-lab/labkit/instagram_pantallas.py`
- Test: `tests/test_media_lab.py`

(ajustado en `fc4a830`: raíz en el origen; firmas con etiqueta/texto/prefijo por nombre; elegir vacío → PantallaInesperada)
(ajustado en `5e9cc25`: alto_volcado exige además ancho completo y alto > LIMITE_ABAJO_PX en la raíz)
(sincronizado con `fc4a830` y `5e9cc25`: todas las llamadas del plan a tiene_texto/pulsable/hay_desplegable, en esta tarea y en las pendientes, pasan a etiqueta=/texto=/prefijo= por nombre)

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_pantalla_comun,` al final de la lista:

```python
def seccion_pantalla_comun() -> None:
    print("\n12. Fase 2: lectura común de pantallas y reloj")
    import time
    from labkit import instagram_pantallas as IP, pantalla as P, reloj

    check(P.PantallaInesperada is IP.PantallaInesperada, "PantallaInesperada es la misma clase en pantalla e instagram_pantallas")
    check(IP._elegir is P.elegir and IP.evaluar_envio is P.evaluar_envio and IP.CLASES_CAMPO == P.CLASES_CAMPO,
          "instagram_pantallas reexporta elegir, evaluar_envio y CLASES_CAMPO de pantalla")

    alto_2340 = jerarquia(nodo_xml("[0,0][1080,300]", texto="Créer"), nodo_xml("[0,301][1080,400]", texto="Bajo"),
                          nodo_xml("[0,1900][1080,2000]", texto="Profil"), nodo_xml("[0,1899][1080,1950]", texto="Alto"))
    check(P.alto_volcado(alto_2340) == 2340, "el alto del volcado sale del nodo raíz")
    arriba = [n["texto"] for n in P.coincidencias(alto_2340, PAQUETE_IG, "arriba")]
    abajo = [n["texto"] for n in P.coincidencias(alto_2340, PAQUETE_IG, "abajo")]
    check("Créer" in arriba and "Bajo" not in arriba, f"sobre 2340 px «arriba» sigue siendo y2 ≤ 300 ({arriba})")
    check("Profil" in abajo and "Alto" not in abajo, f"sobre 2340 px «abajo» sigue siendo y1 ≥ 1900 ({abajo})")

    alto_2316 = jerarquia(nodo_xml("[0,0][1080,296]", texto="Créer"), nodo_xml("[0,0][1080,297]", texto="Justo"),
                          nodo_xml("[0,1881][1080,1990]", texto="Profil"), nodo_xml("[0,1880][1080,1990]", texto="Casi"))
    alto_2316 = alto_2316.replace('bounds="[0,0][1080,2340]"', 'bounds="[0,0][1080,2316]"', 1)
    arriba = [n["texto"] for n in P.coincidencias(alto_2316, PAQUETE_IG, "arriba")]
    abajo = [n["texto"] for n in P.coincidencias(alto_2316, PAQUETE_IG, "abajo")]
    check(P.alto_volcado(alto_2316) == 2316 and arriba == ["Créer"] and abajo == ["Profil"],
          f"sobre 2316 px las zonas escalan (arriba ≤ 296,9; abajo ≥ 1880,5): {arriba}, {abajo}")
    try:
        P.coincidencias(alto_2340, PAQUETE_IG, "centro")
        ok = False
    except ValueError:
        ok = True
    check(ok, "una zona desconocida es ValueError")

    comp = xml_compositor()
    check(P.pulsable(comp, etiqueta="Partager", paquete=PAQUETE_IG) and IP.partager_pulsable(comp),
          "pulsable generaliza partager_pulsable (etiqueta dentro de un botón clickable)")
    check(not P.pulsable(comp, etiqueta="Partager", paquete="com.facebook.katana"), "pulsable exige el paquete")
    check(P.hay_desplegable(xml_compositor(despues=LISTA_HASHTAGS), PAQUETE_IG)
          and not P.hay_desplegable(xml_compositor(despues=LISTA_HASHTAGS), PAQUETE_IG, prefijo="@"),
          "hay_desplegable mira el prefijo pedido fuera del campo de texto")
    check(P.tiene_texto(comp, texto=PIE_PRUEBA, paquete=PAQUETE_IG) and not P.tiene_texto(comp, texto="otro", paquete=PAQUETE_IG),
          "tiene_texto compara el texto exacto dentro del paquete")
    check(P.nodo(comp, PAQUETE_IG, texto="Nouvelle publication")["texto"] == "Nouvelle publication",
          "nodo devuelve el control del paquete")
    try:
        P.nodo(comp, PAQUETE_IG, texto="No existe")
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "nodo sin coincidencias lanza PantallaInesperada")

    ancha = {"nombre": "PopupWindow:a", "frame": (0, 1448, 1080, 2205), "ancho_padre": 1080}
    estrecha = {"nombre": "PopupWindow:b", "frame": (400, 100, 500, 180), "ancho_padre": 1080}
    sin_frame = {"nombre": "PopupWindow:c", "frame": None, "ancho_padre": None}
    check(IP.parece_desplegable is P.parece_desplegable and IP.describe_emergente is P.describe_emergente,
          "instagram_pantallas reexporta parece_desplegable y describe_emergente de pantalla")
    boton = (45, 2081, 1035, 2205)
    check(P.emergente_solapada([estrecha, ancha], [boton]) is ancha and P.emergente_solapada([estrecha], [boton]) is None
          and P.emergente_solapada([estrecha], []) is estrecha and P.emergente_solapada([sin_frame], [boton]) is sin_frame
          and P.emergente_solapada([], [boton]) is None,
          "emergente_solapada: solape vertical con las referencias; sin referencias o sin frame cuenta (falla cerrado)")
    check(P.parece_desplegable(ancha) and not P.parece_desplegable(estrecha) and P.parece_desplegable(sin_frame)
          and "PopupWindow:a" in P.describe_emergente(ancha),
          "parece_desplegable mide el ancho y describe_emergente nombra la ventana")

    dormidos: list = []
    sleep_original, monotonic_original = time.sleep, time.monotonic
    try:
        time.sleep = dormidos.append
        time.monotonic = lambda: 42.0
        reloj.dormir(3)
        check(dormidos == [3] and reloj.monotonic() == 42.0,
              "reloj llama a time en cada uso (las sustituciones de la fase 1 siguen valiendo)")
    finally:
        time.sleep, time.monotonic = sleep_original, monotonic_original
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'pantalla' from 'labkit'` en la sección 12.

- [ ] **Step 3: Implementar `reloj.py`**

```python
"""
Reloj del laboratorio: el único sitio por donde pasa el tiempo de los pasos del teléfono.

Llama a `time` en cada uso, no guarda referencias: las pruebas de la fase 1 sustituyen
`time.sleep` y `time.monotonic` y siguen valiendo; las nuevas sustituyen solo este módulo.
"""
from __future__ import annotations

import time


def dormir(segundos: float) -> None:
    time.sleep(segundos)


def monotonic() -> float:
    return time.monotonic()
```

- [ ] **Step 4: Implementar `pantalla.py`**

```python
"""
Lectura pura y genérica de pantallas (Instagram, Threads, Facebook).

Nada de aquí toca el teléfono ni el reloj: recibe volcados de uiautomator y devuelve lo que
dicen, o lanza PantallaInesperada si un control falta o es ambiguo. Lo propio de cada app
vive en `<app>_pantallas.py`.

Las zonas «arriba» y «abajo» son relativas al alto del volcado: 300 y 1900 px sobre los 2340
del teléfono actual (≈12,8 % y 81,2 %), para que un volcado de otro alto no las desplace.
"""
from __future__ import annotations

from labkit import telefono

CLASES_CAMPO = ("android.widget.AutoCompleteTextView", "android.widget.EditText")
ALTO_REFERENCIA = 2340
LIMITE_ARRIBA_PX = 300
LIMITE_ABAJO_PX = 1900


class PantallaInesperada(RuntimeError):
    pass


def dice(n: dict, valor: str) -> bool:
    return valor in (n["texto"], n["desc"])


def area(n: dict) -> int:
    x1, y1, x2, y2 = n["bounds"]
    return (x2 - x1) * (y2 - y1)


def alto_volcado(xml: str) -> int:
    """Alto de la pantalla según el volcado: el borde inferior del nodo raíz (profundidad 0)
    que cuenta como la pantalla completa, o el alto de referencia si ninguno cuenta.

    Cuenta un nodo raíz cuya esquina superior izquierda está en el origen (0, 0), que ocupa
    todo el ancho de la pantalla (`x2 >= ANCHO_PANTALLA_PX`) y cuyo borde inferior pasa de
    `LIMITE_ABAJO_PX`. Un volcado de una ventana emergente enfocable tiene la emergente como
    raíz, con un origen que no es (0, 0); un contenedor en el origen pero más estrecho o más
    bajo que la pantalla tampoco es la pantalla completa. Ninguno de los dos debe usarse para
    escalar las zonas «arriba»/«abajo» (fallaría abierto: un nodo intermedio contaría como
    «abajo»)."""
    completas = [n["bounds"][3] for n in telefono.nodos(xml)
                 if n["profundidad"] == 0 and n["bounds"][:2] == (0, 0)
                 and n["bounds"][2] >= ANCHO_PANTALLA_PX and n["bounds"][3] > LIMITE_ABAJO_PX]
    return max(completas, default=ALTO_REFERENCIA)


def elegir(coincidencias: list[dict], que: object) -> dict:
    """Una sola coincidencia útil.

    Varias valen si comparten centro o si todas caben en la primera (un contenedor y su
    botón, un botón y su etiqueta); si no, es ambiguo. Entre las válidas se devuelve la
    única clickable si hay exactamente una y, si no, la de menor área."""
    if len(coincidencias) == 1:
        return coincidencias[0]
    primera = coincidencias[0]
    x1, y1, x2, y2 = primera["bounds"]
    for n in coincidencias[1:]:
        ox1, oy1, ox2, oy2 = n["bounds"]
        dentro = ox1 >= x1 and oy1 >= y1 and ox2 <= x2 and oy2 <= y2
        if n["centro"] != primera["centro"] and not dentro:
            raise PantallaInesperada(f"ambiguo: {que} en {[c['bounds'] for c in coincidencias]}")
    pulsables = [n for n in coincidencias if n["clickable"]]
    if len(pulsables) == 1:
        return pulsables[0]
    return min(coincidencias, key=area)


def coincidencias(xml: str, paquete: str | None, zona: str | None = None, **kw) -> list[dict]:
    """Nodos de `paquete` que cumplen los criterios de `telefono.buscar_todos`, en la zona dada."""
    if zona not in (None, "arriba", "abajo"):
        raise ValueError(f"zona desconocida: {zona}")
    todos = telefono.buscar_todos(xml, paquete=paquete, **kw)
    if zona is None:
        return todos
    alto = alto_volcado(xml)
    if zona == "arriba":
        return [n for n in todos if n["bounds"][3] * ALTO_REFERENCIA <= LIMITE_ARRIBA_PX * alto]
    return [n for n in todos if n["bounds"][1] * ALTO_REFERENCIA >= LIMITE_ABAJO_PX * alto]


def nodo(xml: str, paquete: str | None, zona: str | None = None, **kw) -> dict:
    """El control de `paquete` que coincide (en la zona, si se da)."""
    encontrados = coincidencias(xml, paquete, zona, **kw)
    if not encontrados:
        raise PantallaInesperada(f"no aparece {kw}" + (f" en zona {zona}" if zona else ""))
    return elegir(encontrados, kw)


def pulsable(xml: str, *, etiqueta: str, paquete: str) -> bool:
    """Algún control con `etiqueta` (texto o content-desc) de `paquete` se puede pulsar: el propio
    nodo es clickable y enabled o, si es una etiqueta, su antecesor clickable más cercano está
    enabled y es del mismo paquete. `etiqueta` y `paquete` son solo por nombre: los dos son
    `str` y un intercambio no debe fallar en silencio."""
    lista = telefono.nodos(xml)
    for i, n in enumerate(lista):
        if n["package"] != paquete or not dice(n, etiqueta):
            continue
        if n["clickable"]:
            if n["enabled"]:
                return True
            continue
        nivel = n["profundidad"]
        for anterior in reversed(lista[:i]):
            if anterior["profundidad"] >= nivel:
                continue
            nivel = anterior["profundidad"]
            if anterior["clickable"]:
                if anterior["enabled"] and anterior["package"] == paquete:
                    return True
                break
    return False


def tiene_texto(xml: str, *, texto: str, paquete: str) -> bool:
    """Algún nodo de `paquete` cuyo `text` (nunca `content-desc`) es exactamente `texto`.
    `texto` y `paquete` son solo por nombre: los dos son `str` y un intercambio no debe fallar
    en silencio."""
    return any(n["texto"] == texto for n in telefono.buscar_todos(xml, paquete=paquete))


def hay_desplegable(xml: str, paquete: str | None = None, *, prefijo: str = "#") -> bool:
    """Sugerencias abiertas: un texto que empieza por `prefijo` fuera de un campo de texto. Sin
    `paquete` se miran todos los nodos (ante la duda, se da por abierto). `prefijo` es solo por
    nombre: es un `str` como `paquete` y un intercambio no debe fallar en silencio."""
    return any(n["texto"].startswith(prefijo) and not n["clase"].endswith(("AutoCompleteTextView", "EditText"))
               for n in telefono.buscar_todos(xml, paquete=paquete))


def evaluar_envio(observaciones: list[dict]) -> str:
    """Resultado de las observaciones tomadas tras pulsar, en orden. Los volcados no
    válidos no cuentan.

    - «fallido»: algún volcado válido muestra un aviso de error (manda sobre lo demás).
    - «confirmado»: se vio el aviso de envío («banner») y los dos últimos válidos no tienen ni
      aviso ni compositor.
    - «sin_banner»: los dos últimos válidos no tienen compositor pero el aviso no se vio.
    - «timeout» en otro caso."""
    validas = [o for o in observaciones if o["valido"]]
    if any(o.get("fallo") for o in validas):
        return "fallido"
    ultimas = validas[-2:]
    limpias = len(ultimas) == 2 and not any(o["compositor"] or o["banner"] for o in ultimas)
    if limpias and any(o["banner"] for o in validas):
        return "confirmado"
    if limpias:
        return "sin_banner"
    return "timeout"


# --- Ventanas emergentes (tarea 10f de la fase 1) -----------------------------------
# Un desplegable de sugerencias puede ser una PopupWindow que `uiautomator dump` no incluye:
# se lee de `telefono.ventanas_emergentes` y se reconoce por su solape con controles que sí
# están en el volcado (las referencias las da cada app).

UMBRAL_ANCHO_DESPLEGABLE = 0.9  # fracción del ancho del padre que ocupa un desplegable real
ANCHO_PANTALLA_PX = 1080  # medida del Samsung del laboratorio, si la emergente no trae ancho_padre


def se_solapan_verticalmente(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[1] < b[3] and b[1] < a[3]


def emergente_solapada(emergentes: list[dict], referencias: list[tuple[int, int, int, int]]) -> dict | None:
    """La primera de `emergentes` que cuenta como abierta sobre los controles de `referencias`: sin frame
    legible cuenta siempre; con frame, si se solapa verticalmente con alguna referencia; sin referencias en
    el volcado, cuenta cualquiera (falla cerrado). None si ninguna cuenta."""
    for e in emergentes:
        frame = e.get("frame")
        if frame is None or not referencias or any(se_solapan_verticalmente(frame, r) for r in referencias):
            return e
    return None


def parece_desplegable(e: dict) -> bool:
    """El frame de `e` ocupa al menos UMBRAL_ANCHO_DESPLEGABLE del ancho de su padre (o de ANCHO_PANTALLA_PX):
    un desplegable ocupa casi todo el ancho, un tooltip no. Sin frame cuenta como desplegable (falla cerrado)."""
    frame = e.get("frame")
    if frame is None:
        return True
    return (frame[2] - frame[0]) >= UMBRAL_ANCHO_DESPLEGABLE * (e.get("ancho_padre") or ANCHO_PANTALLA_PX)


def describe_emergente(e: dict) -> str:
    """«ventana emergente <nombre> en <frame>», para mensajes de diagnóstico."""
    frame = e.get("frame")
    return f"ventana emergente {e['nombre']} en {frame if frame is not None else 'sin frame legible'}"
```

- [ ] **Step 5: `instagram_pantallas.py` reexporta lo movido**

Cambios, sin tocar `__all__` (la tarea 10f dejó en él `emergente_desplegable`, `hay_desplegable_por_ventana`, `parece_desplegable` y `describe_emergente`, que usan las pruebas):

1. Sustituir `from labkit import telefono` por:

```python
from labkit import pantalla, telefono
from labkit.pantalla import CLASES_CAMPO, PantallaInesperada
```

2. Borrar la línea `CLASES_CAMPO = ("android.widget.AutoCompleteTextView", "android.widget.EditText")`, la clase `PantallaInesperada` y las funciones `_dice` y `_area`, y poner en su lugar:

```python
_dice = pantalla.dice
_area = pantalla.area
```

3. Sustituir el cuerpo de `hay_desplegable_hashtags` (conservando su docstring) por:

```python
    return pantalla.hay_desplegable(xml, paquete, prefijo="#")
```

4. Sustituir el cuerpo de `partager_pulsable` (conservando su docstring) por:

```python
    return pantalla.pulsable(xml, etiqueta="Partager", paquete=PAQUETE)
```

5. Sustituir la función `evaluar_envio` completa por:

```python
evaluar_envio = pantalla.evaluar_envio
```

6. Sustituir `_elegir`, `_coincidencias` y `_nodo` completas por:

```python
_elegir = pantalla.elegir


def _coincidencias(xml: str, zona: str | None = None, **kw) -> list[dict]:
    return pantalla.coincidencias(xml, PAQUETE, zona, **kw)


def _nodo(xml: str, zona: str | None = None, **kw) -> dict:
    """El control de Instagram que coincide (en la zona, si se da). Puro: no toca el teléfono."""
    return pantalla.nodo(xml, PAQUETE, zona, **kw)
```

7. Sustituir las líneas `UMBRAL_ANCHO_DESPLEGABLE = 0.9 …` y `ANCHO_PANTALLA_PX = 1080 …` y las funciones `_se_solapan_verticalmente`, `parece_desplegable` y `describe_emergente` por:

```python
UMBRAL_ANCHO_DESPLEGABLE = pantalla.UMBRAL_ANCHO_DESPLEGABLE
ANCHO_PANTALLA_PX = pantalla.ANCHO_PANTALLA_PX
_se_solapan_verticalmente = pantalla.se_solapan_verticalmente
parece_desplegable = pantalla.parece_desplegable
describe_emergente = pantalla.describe_emergente
```

y el cuerpo de `emergente_desplegable` (conservando firma y docstring) por:

```python
    return pantalla.emergente_solapada(emergentes, _fila_musica_o_partager(xml, paquete))
```

- [ ] **Step 6: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 12 toda en `✓`, ninguna prueba anterior cambia y `El laboratorio cumple sus contratos.`

- [ ] **Step 7: Commit**

```bash
git add experiments/media-lab/labkit/reloj.py experiments/media-lab/labkit/pantalla.py experiments/media-lab/labkit/instagram_pantallas.py tests/test_media_lab.py
git commit -m "media lab claude: pantalla.py y reloj.py con la lectura común de pantallas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `pasos.py` e `instagram_feed.py` sobre él (refactor R, parte 2)

**Files:**
- Create: `experiments/media-lab/labkit/pasos.py`
- Modify: `experiments/media-lab/labkit/instagram_feed.py`
- Test: `tests/test_media_lab.py` (`TelefonoSimulado`, `con_telefono_simulado` y sección nueva)

- [ ] **Step 1: Extender el teléfono simulado**

En `TelefonoSimulado.__init__`, añadir tras `self.reloj = 1000.0`:

```python
        self.volcados_leidos = 0
        self.ultimo = None  # el último volcado leído: lo que había en pantalla
        self.toques_en: list[tuple] = []  # (x, y, volcado en pantalla al tocar)
```

y en `TelefonoSimulado.volcado`, como primera línea:

```python
        self.volcados_leidos += 1
```

justo antes de su `return v`:

```python
        self.ultimo = v
```

y en `TelefonoSimulado.tocar`, como primera línea:

```python
        self.toques_en.append((x, y, self.ultimo))
```

En `con_telefono_simulado`, cambiar `from labkit import instagram_feed, telefono` por `from labkit import instagram_feed, reloj, telefono` y añadir al final de la lista `cambios`:

```python
               (reloj, "dormir", lambda segundos: None),
               (reloj, "monotonic", sim.monotonic)]
```

(la lista pierde el `]` de su última entrada actual). Las entradas de `instagram_feed.time` se quedan: las pruebas de la fase 1 dependen de ellas.

- [ ] **Step 2: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_pasos_comunes,`:

```python
def seccion_pasos_comunes() -> None:
    print("\n13. Fase 2: pasos comunes del teléfono")
    from labkit import instagram_feed as IG, pasos, reloj, telefono as T

    check(IG.BorradorPendiente is pasos.BorradorPendiente and IG.TelefonoNoListo is pasos.TelefonoNoListo,
          "instagram_feed reexporta las excepciones de pasos")
    check(IG.ESTABILIZACION_TIMEOUT_S == pasos.ESTABILIZACION_TIMEOUT_S and IG.ATRAS == pasos.ATRAS,
          "instagram_feed reexporta las constantes de pasos")
    evid = pathlib.Path("evidencia-simulada")
    lectura_profil = lambda x: (T.buscar(x, texto="Profil") or {}).get("bounds")  # noqa: E731
    uno = jerarquia(nodo_xml("[864,2200][1080,2340]", desc="Profil"))
    otro = jerarquia(nodo_xml("[0,2200][216,2340]", desc="Profil"))

    sim = TelefonoSimulado([uno, otro, otro, otro])
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_estable(lectura_profil))
    check(err is None and res[1] == (0, 2200, 216, 2340) and sim.volcados_leidos == 4,
          f"esperar_estable devuelve la lectura tras 3 volcados seguidos iguales ({err!r}, {sim.volcados_leidos})")

    sim = TelefonoSimulado([uno, otro] * 40)
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_estable(lectura_profil))
    check(isinstance(err, pasos.PantallaInesperada) and str(pasos.ESTABILIZACION_TIMEOUT_S) in str(err),
          f"una lectura que nunca se estabiliza agota el plazo ({err!r})")

    th = jerarquia(nodo_xml("[0,0][1080,200]", texto="Fils", paquete="com.instagram.barcelona"))
    sim = TelefonoSimulado([th])
    res, err = con_telefono_simulado(sim, lambda: pasos.atras("com.instagram.barcelona", evid, "salida-1"))
    check(err is None and sim.teclas == [pasos.ATRAS] and sim.capturas == ["salida-1.png"],
          f"atras pulsa con la app pedida delante ({err!r}, {sim.teclas})")
    sim = TelefonoSimulado([th])
    res, err = con_telefono_simulado(sim, lambda: pasos.atras("com.facebook.katana", evid, "salida-1"))
    check(isinstance(err, pasos.PantallaInesperada) and sim.teclas == [], "atras no pulsa con otra app delante")

    boton = {"centro": (540, 2140), "bounds": (45, 2081, 1035, 2205)}
    aviso = jerarquia(nodo_xml("[0,250][1080,330]", texto="ENVIANDO", paquete="com.facebook.katana"))
    limpio = jerarquia(nodo_xml("[0,250][1080,330]", texto="Inicio", paquete="com.facebook.katana"))

    def observador(xml):
        return {"valido": True, "compositor": False, "banner": T.buscar(xml, texto="ENVIANDO") is not None, "fallo": False}

    sim = TelefonoSimulado([aviso, limpio, limpio])
    res, err = con_telefono_simulado(sim, lambda: pasos.observar_envio(boton, observador, 90))
    check(err is None and res["estado"] == "confirmado" and sim.toques == [boton["centro"]]
          and res["submitted_at"] and res["processing_completed_at"],
          f"observar_envio pulsa una vez y confirma con aviso y dos volcados limpios ({err!r}, {res})")

    sim = TelefonoSimulado([limpio], falla_tocar=T.TelefonoError("device offline"))
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete="com.facebook.katana", nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        nombres=("fb-antes.png", "fb-final.png", "fb-error.png"), listo=lambda x, e: [],
        botones=lambda x: [dict(boton, texto="Publicar", desc="", clickable=True)],
        observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(err is None and res["estado"] == "error_tras_pulsar" and len(sim.toques) == 1
          and sim.capturas == ["fb-antes.png", "fb-error.png"] and sim.plazos_captura[-1] == pasos.CAPTURA_ERROR_S,
          f"enviar: si el toque falla, error_tras_pulsar con captura corta y nada se propaga ({err!r}, {res})")

    sim = TelefonoSimulado([limpio], listo=False)
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete="com.facebook.katana", nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        nombres=("a.png", "b.png", "c.png"), listo=lambda x, e: [], botones=lambda x: [],
        observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(isinstance(err, pasos.TelefonoNoListo) and sim.toques == [] and sim.capturas == [],
          "enviar con el teléfono no listo no captura ni toca")

    sim = TelefonoSimulado([limpio], emergentes=(T.TelefonoError("dumpsys no responde"),))
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete="com.facebook.katana", nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        nombres=("a.png", "b.png", "c.png"), listo=lambda x, e: [], botones=lambda x: [],
        observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(isinstance(err, T.TelefonoError) and sim.toques == [],
          "enviar: si ventanas_emergentes falla, falla cerrado sin tocar")
    vistas: list = []
    emergente_fb = [{"nombre": "PopupWindow:sug", "frame": (0, 900, 1080, 1500), "ancho_padre": 1080}]
    sim = TelefonoSimulado([limpio], emergentes=(emergente_fb,))
    res, err = con_telefono_simulado(sim, lambda: pasos.enviar(
        paquete="com.facebook.katana", nombre_app="Facebook", etiqueta="Publicar", evidencia=evid,
        nombres=("a.png", "b.png", "c.png"), listo=lambda x, e: vistas.append(e) or (["emergente"] if e else []),
        botones=lambda x: [], observador_nuevo=lambda b: observador, despues=lambda r, e: e))
    check(isinstance(err, pasos.PantallaInesperada) and vistas == [emergente_fb] and sim.toques == [],
          "enviar pasa a listo las ventanas emergentes del paquete y no pulsa si hay problemas")

    check(reloj.dormir.__name__ == "dormir" and reloj.monotonic.__name__ == "monotonic",
          "con_telefono_simulado restaura el reloj")
```

- [ ] **Step 3: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: las secciones 1–12 siguen en `✓` (el simulador ya sustituye `reloj`, que existe desde la tarea 1) y la 13 acaba en traceback con `ImportError: cannot import name 'pasos' from 'labkit'`.

- [ ] **Step 4: Implementar `pasos.py`**

```python
"""
Pasos con E/S comunes a todos los flujos del teléfono.

Un paso por llamada y nunca a ciegas: si un control no aparece o es ambiguo se lanza
PantallaInesperada y no se toca nada más. Ningún paso despierta ni desbloquea el teléfono
(MaaS360). Todo el tiempo pasa por `labkit.reloj` y todo el teléfono por `labkit.telefono`,
para que las pruebas los sustituyan sin tocar nada más.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import phone_clipboard
from labkit import pantalla, reloj, telefono
from labkit.pantalla import PantallaInesperada

ATRAS, CTRL_IZQ, TECLA_A = 4, 113, 29
ESPERA_S = 25
OBSERVACION_S = 90
CAPTURA_ERROR_S = 10  # la captura tras un error es best-effort: no alarga la salida
VOLCADOS_LIMPIOS = 3  # seguidos, sin teclado ni desplegable, antes de dar un texto pegado por bueno
ESPERA_ENTRE_VOLCADOS_S = 2.5
INTENTOS_ATRAS = 2  # tope total de «atrás» para cerrar teclado o desplegable tras pegar
ESTABILIZACION_TIMEOUT_S = 60
VOLCADO_NO_VALIDO = {"valido": False, "compositor": False, "banner": False, "fallo": False}


class BorradorPendiente(PantallaInesperada):
    """La app abrió con una publicación a medias: la resuelve una persona."""


class TelefonoNoListo(PantallaInesperada):
    """Dormido, bloqueado o sin adb. No se intenta arreglar."""


def exigir_listo() -> None:
    e = telefono.estado()
    if not e["listo"]:
        raise TelefonoNoListo(f"el teléfono no está listo (no se despierta ni se desbloquea): {e}")


def esperar_que(cumple, descripcion: str) -> str:
    """Primer volcado válido que cumple la condición.

    El plazo de ESPERA_S se comprueba entre volcados y cada volcado recibe el tiempo que
    queda (5 s como mínimo), así que la espera total puede pasar de ESPERA_S en lo que tarde
    el último volcado."""
    inicio = reloj.monotonic()
    ultimo_error = ""
    while True:
        restante = max(5, int(ESPERA_S - (reloj.monotonic() - inicio)))
        try:
            xml = telefono.volcado(timeout=restante)
            if cumple(xml):
                return xml
        except telefono.TelefonoError as e:
            ultimo_error = f" (último error: {e})"
        transcurrido = reloj.monotonic() - inicio
        if transcurrido >= ESPERA_S:
            raise PantallaInesperada(f"no apareció {descripcion} tras {transcurrido:.1f} s{ultimo_error}")
        reloj.dormir(1.5)


def volcado_fresco() -> str:
    return esperar_que(lambda xml: True, "un volcado válido")


def esperar_estable(lectura, n: int = VOLCADOS_LIMPIOS, descripcion: str = "una lectura estable") -> tuple[str, object]:
    """(xml, valor) cuando `n` volcados frescos seguidos dan el mismo `lectura(xml)` no nulo
    (None y False reinician la cuenta). Los volcados pueden ir con retraso: esta es la regla
    antes de cualquier lectura decisiva. El plazo total se comprueba al empezar cada vuelta."""
    inicio = reloj.monotonic()
    previo, seguidos = None, 0
    while True:
        if reloj.monotonic() - inicio >= ESTABILIZACION_TIMEOUT_S:
            raise PantallaInesperada(f"no hubo {descripcion} en {n} volcados seguidos tras {ESTABILIZACION_TIMEOUT_S} s")
        xml = volcado_fresco()
        valor = lectura(xml)
        if valor is None or valor is False:
            previo, seguidos = None, 0
        elif seguidos and valor == previo:
            seguidos += 1
        else:
            previo, seguidos = valor, 1
        if seguidos >= n:
            return xml, valor
        reloj.dormir(ESPERA_ENTRE_VOLCADOS_S)


def escribir_texto(texto: str, paquete: str, *, campo, exigir, desplegable_nodos, emergente) -> str:
    """Pega `texto` en el campo y devuelve el volcado final con la pantalla estable.

    `campo(xml)` localiza el campo (None si no está), `exigir(xml)` lanza PantallaInesperada si la
    pantalla ya no es la del compositor con el texto, `desplegable_nodos(xml)` dice si el volcado muestra
    sugerencias abiertas y `emergente(xml, emergentes)` devuelve la ventana emergente de
    `telefono.ventanas_emergentes(paquete)` que se solapa con los controles del compositor, o None: un
    desplegable de sugerencias puede ser una PopupWindow que `uiautomator dump` no ve (tarea 10f). Una
    emergente que se solapa y parece un desplegable (`pantalla.parece_desplegable`) cuenta como abierto;
    una que se solapa pero no lo parece para con PantallaInesperada sin pulsar «atrás»; un TelefonoError de
    `ventanas_emergentes` se propaga sin pulsar nada.

    No da la pantalla por buena hasta ver VOLCADOS_LIMPIOS volcados frescos seguidos sin teclado ni
    desplegable: la app puede abrir sugerencias unos segundos después de pegar. Si solo el desplegable pide
    cerrar, se confirma con un volcado fresco antes de pulsar «atrás». Cada «atrás» reinicia la cuenta, con
    un tope de INTENTOS_ATRAS y otro de ESTABILIZACION_TIMEOUT_S (comprobado al empezar cada vuelta). Si no
    se sabe si el teclado está abierto, se para sin pulsar: un «atrás» con todo cerrado sacaría del
    compositor."""
    exigir_listo()
    xml = esperar_que(lambda x: campo(x) is not None, "el campo de texto")
    telefono.tocar(*campo(xml)["centro"])
    reloj.dormir(2)
    telefono.combinacion(CTRL_IZQ, TECLA_A)
    exigir_listo()
    try:
        phone_clipboard.pegar(texto, paste=True)
    except (RuntimeError, OSError) as e:
        raise telefono.TelefonoError(f"portapapeles: {e}") from e
    reloj.dormir(2)
    xml = volcado_fresco()
    if not pantalla.tiene_texto(xml, texto=texto, paquete=paquete):
        raise PantallaInesperada("el texto leído del teléfono no coincide con el archivo")

    def estado_cierre(x: str) -> tuple[bool, bool, dict | None]:
        teclado = telefono.teclado_estado()
        if teclado is None:
            raise PantallaInesperada("no se puede leer si el teclado está abierto")
        culpable = emergente(x, telefono.ventanas_emergentes(paquete))
        if culpable is not None and not pantalla.parece_desplegable(culpable):
            raise PantallaInesperada(f"una ventana emergente se solapa pero no parece un desplegable de sugerencias "
                                     f"({pantalla.describe_emergente(culpable)}): no se pulsa «atrás»")
        return teclado, desplegable_nodos(x) or culpable is not None, culpable

    atras_usados = 0
    limpios = 0
    inicio = reloj.monotonic()
    while limpios < VOLCADOS_LIMPIOS:
        if reloj.monotonic() - inicio >= ESTABILIZACION_TIMEOUT_S:
            raise PantallaInesperada(f"el compositor no se estabilizó tras {ESTABILIZACION_TIMEOUT_S} s pegando el texto")
        exigir(xml)
        teclado, abierto, culpable = estado_cierre(xml)
        if not teclado and abierto:
            xml = volcado_fresco()
            exigir(xml)
            teclado, abierto, culpable = estado_cierre(xml)
        if teclado or abierto:
            atras_usados += 1
            if atras_usados > INTENTOS_ATRAS:
                detalle = f" ({pantalla.describe_emergente(culpable)})" if culpable is not None else ""
                raise PantallaInesperada(f"el teclado o el desplegable siguen abiertos tras {INTENTOS_ATRAS} «atrás»{detalle}")
            telefono.tecla(ATRAS)
            reloj.dormir(2)
            xml = volcado_fresco()
            limpios = 0
            continue
        limpios += 1
        if limpios < VOLCADOS_LIMPIOS:
            reloj.dormir(ESPERA_ENTRE_VOLCADOS_S)
            xml = volcado_fresco()
    return xml


def atras(paquete: str, evidencia: Path, nombre: str) -> Path:
    """«Atrás» solo con `paquete` en primer plano."""
    exigir_listo()
    xml = volcado_fresco()
    if telefono.buscar(xml, paquete=paquete) is None:
        raise PantallaInesperada(f"{paquete} no está en primer plano: no se pulsa «atrás»")
    telefono.tecla(ATRAS)
    reloj.dormir(3)
    return telefono.captura(evidencia / f"{nombre}.png")


def observar_envio(boton: dict, observador, plazo: float = OBSERVACION_S, resultado: dict | None = None) -> dict:
    """Pulsa `boton` UNA vez y observa cada 1,5 s con `observador(xml) -> observación` hasta
    `plazo` o hasta que `pantalla.evaluar_envio` dé confirmado o fallido. Rellena y devuelve
    `resultado` con submitted_at, processing_completed_at, estado y, si falló, la observación
    culpable en `fallo`. Puede lanzar (el toque o el observador): quien llama lo recoge."""
    resultado = {} if resultado is None else resultado
    resultado["submitted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    telefono.tocar(*boton["centro"])
    observaciones: list[dict] = []
    inicio = reloj.monotonic()
    while reloj.monotonic() - inicio < plazo:
        reloj.dormir(1.5)
        try:
            observaciones.append(observador(telefono.volcado()))
        except telefono.TelefonoError:
            observaciones.append(dict(VOLCADO_NO_VALIDO))
        parcial = pantalla.evaluar_envio(observaciones)
        if parcial == "confirmado":
            resultado["processing_completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            break
        if parcial == "fallido":
            break
    resultado["estado"] = pantalla.evaluar_envio(observaciones)
    if resultado["estado"] == "fallido":
        resultado["fallo"] = next((o for o in observaciones if o.get("fallo")), None)
    return resultado


def enviar(*, paquete: str, nombre_app: str, etiqueta: str, evidencia: Path, nombres: tuple[str, str, str],
           listo, botones, observador_nuevo, despues, extra: dict | None = None,
           plazo: float = OBSERVACION_S) -> dict:
    """Comparte con un solo toque, para cualquier app.

    Antes de pulsar: teléfono listo, teclado cerrado, captura `nombres[0]`, `listo(xml, emergentes)` (con
    `telefono.ventanas_emergentes`, que falla cerrado si `dumpsys` falla) sin problemas en dos volcados seguidos y `botones(xml)` en los mismos bounds en los dos. Desde
    el toque nada se propaga: `despues(resultado, estado)` lee la confirmación de la app y
    devuelve el estado final, la captura final es `nombres[1]` y cualquier excepción deja
    «error_tras_pulsar» con la captura best-effort `nombres[2]`."""
    exigir_listo()
    if telefono.teclado_visible():
        raise PantallaInesperada("el teclado está visible (o no se sabe): no se comparte")
    captura_antes = str(telefono.captura(evidencia / nombres[0]))
    xml1 = volcado_fresco()
    problemas = listo(xml1, telefono.ventanas_emergentes(paquete))
    if problemas:
        raise PantallaInesperada(f"el compositor no está listo para compartir: {problemas}")
    reloj.dormir(1.5)
    xml2 = volcado_fresco()
    problemas = listo(xml2, telefono.ventanas_emergentes(paquete))
    if problemas:
        raise PantallaInesperada(f"el compositor no está listo para compartir (2.º volcado): {problemas}")
    posiciones = [[n["bounds"] for n in botones(x)] for x in (xml1, xml2)]
    if posiciones[0] != posiciones[1]:
        raise PantallaInesperada(f"«{etiqueta}» se ha movido entre volcados: {posiciones}")
    candidatos = botones(xml2)
    if not candidatos:
        raise PantallaInesperada(f"no aparece «{etiqueta}» de {nombre_app}")
    boton = pantalla.elegir(candidatos, etiqueta)

    resultado = {"estado": None, "error": None, "submitted_at": None, "processing_completed_at": None,
                 "captura": None, "captura_antes": captura_antes, "captura_error": None, "avisos": [],
                 **(extra or {})}
    avisos = resultado["avisos"]
    try:
        observar_envio(boton, observador_nuevo(boton), plazo, resultado)
        culpable = resultado.pop("fallo", None)
        if resultado["estado"] == "fallido" and culpable:
            avisos.append(f"{nombre_app} avisó de un error: {culpable.get('fallo_texto')!r} "
                          f"en {culpable.get('fallo_bounds')}")
        resultado["estado"] = despues(resultado, resultado["estado"])
        try:
            resultado["captura"] = str(telefono.captura(evidencia / nombres[1]))
        except telefono.TelefonoError as e:
            avisos.append(f"no se pudo capturar tras compartir: {e}")
    except Exception as e:  # noqa: BLE001 — tras pulsar, el resultado tiene que volver siempre
        resultado["estado"] = "error_tras_pulsar"
        resultado["error"] = f"{type(e).__name__}: {e}"
        try:
            resultado["captura_error"] = str(telefono.captura(evidencia / nombres[2], timeout=CAPTURA_ERROR_S))
        except Exception as e_captura:  # noqa: BLE001 — best-effort: el resultado vuelve igual
            avisos.append(f"no se pudo capturar tras el error: {type(e_captura).__name__}: {e_captura}")
    return resultado
```

- [ ] **Step 5: `instagram_feed.py` sobre `pasos.py`**

Sustituir el archivo completo. El comportamiento, los nombres de captura, el orden de las llamadas a `teclado_estado` y `ventanas_emergentes` y los mensajes que miran las pruebas («teclado», el tope de estabilización, «portapapeles:», nombre y frame de la emergente) no cambian; `_desplegable_abierto`, `_emergente_anomala` y `_estado_cierre` desaparecen porque su lógica está ahora en `pasos.escribir_texto`.

```python
"""
Feed de Instagram por teléfono, un paso por llamada.

Cada función deja una captura en la carpeta de evidencia y termina. Quien dirige (Claude)
mira la captura antes de pedir el siguiente paso: nada de pulsaciones a ciegas. Lo común
(esperas, escritura, envío con un toque) vive en `pasos`; la lectura pura de pantallas en
`instagram_pantallas`, que se reexporta desde aquí (`IG.observacion_de_volcado`, `IG._nodo`…
siguen funcionando).

Textos en francés: es el idioma configurado en el teléfono.
"""
from __future__ import annotations

import time  # noqa: F401 — las pruebas de la fase 1 sustituyen instagram_feed.time.sleep y .monotonic
from datetime import datetime
from pathlib import Path

from labkit import pasos, reloj, telefono
from labkit.instagram_pantallas import *  # noqa: F401,F403 — reexporta `instagram_pantallas.__all__`
from labkit.instagram_pantallas import (MARCA, PAQUETE, PantallaInesperada, _campos, _coincidencias,
                                        _exigir_compositor_con_pie, _nodo, _suivant, banners_de_volcado,
                                        campo_pie, compositor_listo, emergente_desplegable, hay_desplegable_hashtags,
                                        miniatura_coincide, observacion_de_volcado, perfil_activo,
                                        publicaciones_de_perfil, punto_mas, seleccion_unica, tema_de_chip)
from labkit.pasos import (ATRAS, CAPTURA_ERROR_S, CTRL_IZQ, ESPERA_ENTRE_VOLCADOS_S, ESPERA_S,  # noqa: F401
                          ESTABILIZACION_TIMEOUT_S, OBSERVACION_S, TECLA_A, BorradorPendiente, TelefonoNoListo)

VOLCADOS_LIMPIOS_TRAS_PEGAR = pasos.VOLCADOS_LIMPIOS
INTENTOS_ATRAS_PIE = pasos.INTENTOS_ATRAS


def _esperar(zona: str | None = None, **kw) -> str:
    return pasos.esperar_que(lambda xml: bool(_coincidencias(xml, zona, **kw)), f"{kw}")


def abrir_nueva_publicacion(evidencia: Path, subido_en: datetime | str) -> dict:
    """Desde el perfil de la marca hasta el selector con la foto recién subida marcada."""
    if isinstance(subido_en, str):
        subido_en = datetime.fromisoformat(subido_en)
    pasos.exigir_listo()
    try:
        telefono.cerrar_cortina()
    except telefono.TelefonoError:
        pass  # best-effort: si no se puede replegar, se sigue e Instagram decide si hay bloqueo
    telefono.lanzar(PAQUETE)
    reloj.dormir(4)
    xml = pasos.esperar_que(
        lambda x: bool(_coincidencias(x, "abajo", texto="Profil"))
        or telefono.buscar(x, texto="Nouvelle publication", paquete=PAQUETE) is not None
        or bool(_campos(x)),
        "Instagram listo (Profil, «Nouvelle publication» o el campo del pie)")
    if telefono.buscar(xml, texto="Nouvelle publication", paquete=PAQUETE) or _campos(xml):
        raise BorradorPendiente("Instagram abrió con una publicación a medias: no se toca")
    telefono.tocar(*_nodo(xml, "abajo", texto="Profil")["centro"])
    xml = _esperar(contiene="Modifier le profil")
    perfil = perfil_activo(xml)
    if perfil != MARCA:
        raise PantallaInesperada(f"el perfil activo es {perfil!r}, no @{MARCA}")
    publicaciones_antes = publicaciones_de_perfil(xml)
    telefono.tocar(*_nodo(xml, "arriba", texto="Créer")["centro"])
    xml = _esperar(texto="Publication")
    telefono.tocar(*_nodo(xml, texto="Publication")["centro"])
    xml = _esperar(texto="Nouvelle publication")
    sel = seleccion_unica(xml)
    if sel is None:
        raise PantallaInesperada("no hay exactamente una miniatura seleccionada")
    if not miniatura_coincide(sel["desc"], subido_en):
        raise PantallaInesperada(f"la miniatura seleccionada no es la subida a las {subido_en.isoformat()}: {sel['desc']}")
    return {"captura": str(telefono.captura(evidencia / "ig-01-selector.png")),
            "publicaciones_antes": publicaciones_antes}


def alternar_recorte(evidencia: Path) -> Path:
    """Pulsa el conmutador de recorte UNA vez. El volcado no muestra si queda en 4:5 (el
    contenedor mide lo mismo): quien dirige lo confirma en la captura."""
    pasos.exigir_listo()
    xml = _esperar(texto="Modifier le rognage")
    telefono.tocar(*_nodo(xml, texto="Modifier le rognage")["centro"])
    reloj.dormir(2)
    return telefono.captura(evidencia / "ig-02-recorte.png")


def siguiente(evidencia: Path, nombre: str) -> Path:
    pasos.exigir_listo()
    xml = _esperar(texto="Suivant")
    telefono.tocar(*_suivant(xml)["centro"])
    reloj.dormir(4)
    return telefono.captura(evidencia / f"{nombre}.png")


def anadir_audio_sugerido(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = _esperar(empieza="Audio suggéré.")
    chip = _nodo(xml, empieza="Audio suggéré.")
    tema = tema_de_chip(chip["desc"])
    if tema is None:
        raise PantallaInesperada(f"el chip de audio no dice qué tema es: {chip['desc']!r}")
    telefono.tocar(*punto_mas(chip["bounds"]))
    xml = _esperar(texto="Terminé")
    telefono.tocar(*_nodo(xml, texto="Terminé")["centro"])
    reloj.dormir(3)
    return {"tema": tema, "captura": str(telefono.captura(evidencia / "ig-03-audio.png"))}


def detalles(evidencia: Path) -> Path:
    """Del editor a la pantalla de detalles; quien dirige la mira antes de escribir el pie."""
    pasos.exigir_listo()
    xml = _esperar(texto="Suivant")
    telefono.tocar(*_suivant(xml)["centro"])
    pasos.esperar_que(lambda x: campo_pie(x) is not None, "el campo del pie")
    return telefono.captura(evidencia / "ig-03b-detalles.png")


def escribir_pie(pie: str, evidencia: Path) -> Path:
    """Pega el pie y solo captura con el compositor estable, sin teclado ni desplegable de hashtags, ya sea
    por nodos o como ventana emergente (tarea 10f); ver `pasos.escribir_texto`."""
    pasos.escribir_texto(pie, PAQUETE, campo=campo_pie,
                         exigir=lambda x: _exigir_compositor_con_pie(x, pie),
                         desplegable_nodos=lambda x: hay_desplegable_hashtags(x, paquete=PAQUETE),
                         emergente=emergente_desplegable)
    return telefono.captura(evidencia / "ig-04-compositor.png")


def atras(evidencia: Path, nombre: str) -> Path:
    """«Atrás» solo con Instagram en primer plano."""
    return pasos.atras(PAQUETE, evidencia, nombre)


def compartir(pie: str, tema: str | None, evidencia: Path, publicaciones_antes: int | None,
              produccion_cercana: bool = False) -> dict:
    """Pulsa Partager una sola vez (nunca se reintenta) y observa el resultado.

    Estados: «confirmado» (banner, compositor cerrado y el perfil suma una publicación),
    «confirmado_sin_conteo» (igual, pero falta uno de los dos conteos, o `produccion_cercana`:
    el publicador de producción pudo sumar la suya), «conteo_no_cuadra», «fallido»,
    «sin_banner», «timeout» y «error_tras_pulsar». Desde la pulsación nada se propaga."""

    def observador_nuevo(boton: dict):
        banners_vistos: list[tuple[int, int, int, int]] = []  # el error puede salir cuando el banner ya se fue

        def observar(xml: str) -> dict:
            obs = observacion_de_volcado(xml, boton["bounds"], banners_vistos)
            banners_vistos.extend(banners_de_volcado(xml))
            return obs
        return observar

    def despues(resultado: dict, estado: str) -> str:
        avisos = resultado["avisos"]
        try:
            if telefono.estado()["listo"]:
                xml = _esperar("abajo", texto="Profil")
                telefono.tocar(*_nodo(xml, "abajo", texto="Profil")["centro"])
                xml = _esperar(contiene="Modifier le profil")
                perfil = perfil_activo(xml)
                if perfil == MARCA:
                    resultado["publicaciones_despues"] = publicaciones_de_perfil(xml)
                else:
                    avisos.append(f"tras compartir el perfil activo es {perfil!r}")
            else:
                avisos.append("tras compartir el teléfono no está listo: no se leyó el perfil")
        except (PantallaInesperada, telefono.TelefonoError) as e:
            avisos.append(f"no se pudo leer el perfil tras compartir: {e}")
        if estado == "confirmado":
            despues_ = resultado["publicaciones_despues"]
            if publicaciones_antes is None or despues_ is None:
                estado = "confirmado_sin_conteo"
            elif despues_ != publicaciones_antes + 1:
                estado = "conteo_no_cuadra"
            elif produccion_cercana:
                estado = "confirmado_sin_conteo"
                avisos.append("producción publicó cerca: el +1 del perfil no prueba que sea esta publicación")
        return estado

    return pasos.enviar(
        paquete=PAQUETE, nombre_app="Instagram", etiqueta="Partager", evidencia=evidencia,
        nombres=("ig-05a-antes.png", "ig-05-publicado.png", "ig-05-error.png"),
        listo=lambda x, emergentes: compositor_listo(x, pie, tema, emergentes),
        botones=lambda x: telefono.buscar_todos(x, texto="Partager", paquete=PAQUETE),
        observador_nuevo=observador_nuevo, despues=despues,
        extra={"publicaciones_antes": publicaciones_antes, "publicaciones_despues": None})
```

- [ ] **Step 6: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: secciones 1–13 en `✓` (las de la fase 1 sin tocarlas) y `El laboratorio cumple sus contratos.`

- [ ] **Step 7: Commit**

```bash
git add experiments/media-lab/labkit/pasos.py experiments/media-lab/labkit/instagram_feed.py tests/test_media_lab.py
git commit -m "media lab claude: pasos.py con esperas, escritura y envío comunes; el feed de Instagram lo usa

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `textos.py`, pista de idioma, envío prohibido y descarte (refactor R, parte 3)

**Files:**
- Create: `experiments/media-lab/labkit/textos.py`
- Modify: `experiments/media-lab/labkit/pantalla.py`, `experiments/media-lab/labkit/pasos.py`
- Test: `tests/test_media_lab.py`
- (ajustado en `95a421c`: una revisión de especificación tras el commit `1f51ed1` encontró tres huecos bloqueantes (B1-B3) y tres importantes (I1-I3) en el diseño de esta tarea, no en su copia del código. `pantalla._es_de_envio`/`es_envio` y `boton_descarte` (Step 4) y `textos.es_texto_envio` (Step 3) quedan como se describe abajo, ya corregidos; el código de los Steps 1-6 de este documento es el ORIGINAL con el hueco, útil como referencia histórica de por qué se corrigió, no para copiarlo literal. Ver la desviación 9 actualizada para el diseño vigente.)

- [x] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` esta constante y la sección, y registrar `seccion_textos_y_descarte,`:

```python
XML_BOTON_ENVIO_CON_ICONO = jerarquia(
    nodo_xml("[45,2081][1035,2205]", clase="android.widget.Button", extra='clickable="true"',
             hijos=nodo_xml("[60,2100][120,2180]", desc="Icône", clase="android.widget.ImageView")
             + nodo_xml("[480,2115][600,2170]", texto="Partager")),
    nodo_xml("[847,92][1080,249]", texto="Suivant", extra='clickable="true"'))


def toques_sobre_envio(sim, paquete: str) -> list:
    """Toques del simulador que cayeron dentro de un control de envío (`textos.es_texto_envio` en texto, descripción
    o id) de `paquete` en el volcado que había en pantalla al tocar (`sim.toques_en`)."""
    from labkit import telefono, textos
    return [(x, y) for x, y, xml in sim.toques_en
            if isinstance(xml, str) and any(
                n["package"] == paquete
                and any(textos.es_texto_envio(v) for v in (n["texto"], n["desc"], n["resource_id"]))
                and n["bounds"][0] <= x < n["bounds"][2] and n["bounds"][1] <= y < n["bounds"][3]
                for n in telefono.nodos(xml))]


def seccion_textos_y_descarte() -> None:
    print("\n14. Fase 2: textos, pista de idioma, envío prohibido y descarte")
    from labkit import pantalla as P, pasos, telefono as T, textos as TX

    check(set(TX.APPS_TELEFONO) <= set(TX.PAQUETES) and all(a in TX.TEXTOS for a in TX.APPS_TELEFONO),
          "cada app de teléfono tiene paquete y tabla de textos")
    check(TX.texto("instagram", "perfil") == "Profil" and TX.texto("facebook", "publico") == "Público",
          "texto(app, clave) devuelve el texto exacto")
    for valor in ("Partager", "publier", " Publicar ", "Compartir historia", "Post", "Share",
                  "com.instagram.barcelona:id/new_thread_screen_post_button"):
        check(TX.es_texto_envio(valor), f"es de envío: {valor!r}")
    for valor in ("Vos stories", "Votre story", "Amis proches", "Envoyer à", "Tu historia", "Compartir en tu historia",
                  "Your story", "Close friends"):
        check(TX.es_texto_envio(valor), f"C1: publica una Story, cuenta como envío: {valor!r}")
    for valor in ("Suivant", "Siguiente", "Compartir en Instagram", ""):
        check(not TX.es_texto_envio(valor), f"no es de envío: {valor!r}")
    for valor in ("Partager maintenant", "Publier le fil", "Compartir ahora mismo", "Share now", "Envoyer", "Ajouter à votre story"):
        check(TX.es_texto_envio(valor), f"I-5: por prefijo, es de envío: {valor!r}")
    for valor in ("Partager à", "partager  sur Facebook", "Compartir en Instagram"):
        check(not TX.es_texto_envio(valor), f"I-5: excepción explícita NO_ENVIO, no es de envío: {valor!r}")
    no_envio = TX.NO_ENVIO
    try:
        TX.NO_ENVIO = no_envio | {"partager", "vos stories", "publier le fil"}
        exactos = TX.es_texto_envio("Partager") and TX.es_texto_envio("Vos stories")
        prefijo_exceptuado = not TX.es_texto_envio("Publier le fil")
    finally:
        TX.NO_ENVIO = no_envio
    check(exactos and prefijo_exceptuado,
          "I-5: NO_ENVIO solo exceptúa de la regla de prefijos; nunca anula un envío exacto de ENVIO o ENVIO_HISTORIA")
    check(TX.permitido("Profil", "instagram")
          and TX.permitido("Sélectionné Miniature de la photo du 14 septembre 2026 10:39", "instagram")
          and TX.permitido("#citasdiarias", "instagram") and TX.permitido("3 min", "instagram")
          and not TX.permitido("Hola Juan, ¿quedamos mañana?", "instagram"),
          "permitido acepta textos de la tabla, marca y patrones, y rechaza texto personal")
    check(TX.permitido("sabiduriabolsillo", "instagram") and TX.permitido("Photo de profil de sabiduriabolsillo", "instagram")
          and not TX.permitido("Juan ha comentado la foto de sabiduriabolsillo", "instagram")
          and not TX.permitido("Mensaje de Juan para Sabiduria De Bolsillo", "facebook"),
          "I4: la marca sola y sus formatos concretos se permiten; una frase personal que la menciona, no")

    ingles = (xml_perfil().replace('"Profil"', '"Profile"').replace("Modifier le profil", "Edit profile")
              .replace('"Créer"', '"Create"').replace("publications", "posts"))
    check("idioma" in P.pista_idioma(ingles, "instagram") and P.pista_idioma(xml_perfil(), "instagram") == "",
          "un perfil de Instagram en inglés da pista de idioma; en francés no")
    check(P.pista_idioma(ingles, "facebook") == "", "sin nodos de la app no hay pista")
    sim = TelefonoSimulado([ingles])
    res, err = con_telefono_simulado(sim, lambda: pasos.esperar_que(
        lambda x: T.buscar(x, texto="Profil") is not None, "Profil", app="instagram"))
    check(isinstance(err, P.PantallaInesperada) and "idioma" in str(err) and sim.toques == [],
          f"volcado en inglés: esperar_que falla cerrado con un mensaje de idioma ({err!r})")

    for criterio, label in (({"texto": "Partager"}, "la etiqueta de envío"),
                            ({"desc": "Icône"}, "un icono dentro del botón de envío")):
        try:
            P.nodo_sonda(XML_BOTON_ENVIO_CON_ICONO, PAQUETE_IG, **criterio)
            ok = False
        except P.PantallaInesperada:
            ok = True
        check(ok, f"nodo_sonda se niega a devolver {label}")
    check(P.nodo_sonda(XML_BOTON_ENVIO_CON_ICONO, PAQUETE_IG, texto="Suivant")["centro"] == (963, 170),
          "nodo_sonda devuelve un nodo único que no es de envío")
    th_publicar = jerarquia(nodo_xml("[800,100][1000,200]", desc="", clase="android.widget.Button",
                                     paquete="com.instagram.barcelona",
                                     extra='clickable="true" resource-id="com.instagram.barcelona:id/new_thread_screen_post_button"'))
    try:
        P.nodo_sonda(th_publicar, "com.instagram.barcelona", resource_id="new_thread_screen_post_button")
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "nodo_sonda se niega a devolver el botón de publicar de Threads por resource-id")

    icono = T.buscar(XML_BOTON_ENVIO_CON_ICONO, texto="Icône")
    sim = TelefonoSimulado([XML_BOTON_ENVIO_CON_ICONO])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(icono, XML_BOTON_ENVIO_CON_ICONO, PAQUETE_IG))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C1: pasos.tocar no pulsa un icono dentro del botón de envío")
    historia = jerarquia(nodo_xml("[40,600][300,860]", desc="Votre story", clase="android.widget.ImageView", extra='clickable="true"'))
    avatar = T.buscar(historia, texto="Votre story")
    sim = TelefonoSimulado([historia])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(avatar, historia, PAQUETE_IG))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C1: «Votre story» es envío si no está en la lista blanca")
    sim = TelefonoSimulado([historia])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(avatar, historia, PAQUETE_IG, permitir=("Votre story",)))
    check(err is None and sim.toques == [(170, 730)], "C1: con la lista blanca explícita, pasos.tocar abre el visor propio")
    tapado_envio = jerarquia(nodo_xml("[0,500][1080,1000]", texto="Vos stories", clase="android.widget.Button", extra='clickable="true"'),
                             nodo_xml("[40,600][300,860]", desc="Votre story", clase="android.widget.ImageView", extra='clickable="true"'))
    avatar_tapado = T.buscar(tapado_envio, texto="Votre story")
    sim = TelefonoSimulado([tapado_envio])
    res, err = con_telefono_simulado(sim, lambda: pasos.tocar(avatar_tapado, tapado_envio, PAQUETE_IG, permitir=("Votre story",)))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [],
          "permitir solo ignora «Votre story»: si su centro cae dentro de «Vos stories», no se toca")
    solapado = jerarquia(nodo_xml("[0,2000][1080,2200]", texto="Vos stories", clase="android.widget.Button", extra='clickable="true"'),
                         nodo_xml("[500,2050][600,2150]", desc="Flèche", clase="android.widget.ImageView"))
    flecha = T.buscar(solapado, texto="Flèche")
    check(P.es_envio(solapado, flecha, PAQUETE_IG), "C1: un nodo cuyo centro cae dentro de «Vos stories» cuenta como envío")
    try:
        P.nodo_sonda(solapado, PAQUETE_IG, texto="Vos stories")
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "C1: nodo_sonda se niega a devolver «Vos stories»")

    dialogo = jerarquia(nodo_xml("[100,900][980,1000]", texto="Recommencer ?"),
                        nodo_xml("[100,1100][980,1200]", texto="Recommencer", clase="android.widget.Button",
                                 extra='clickable="true"'),
                        nodo_xml("[100,1250][980,1350]", texto="Annuler", clase="android.widget.Button",
                                 extra='clickable="true"'))
    check(P.boton_descarte(dialogo, "instagram")["texto"] == "Recommencer", "boton_descarte lee el diálogo exacto")
    evid = pathlib.Path("evidencia-simulada")
    sim = TelefonoSimulado([dialogo])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(err is None and sim.toques == [(540, 1150)] and sim.capturas == ["descarte.png"],
          f"descartar pulsa solo el botón del diálogo y captura ({err!r}, {sim.toques})")
    sim = TelefonoSimulado([xml_compositor()])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "sin diálogo de descarte no se pulsa nada")
    borrar_th = jerarquia(nodo_xml("[100,900][980,1000]", texto="Supprimer le fil ?", paquete="com.instagram.barcelona"),
                          nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button",
                                   paquete="com.instagram.barcelona", extra='clickable="true"'))
    sim = TelefonoSimulado([borrar_th])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("threads", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "I1: «Supprimer le fil ?» es un borrado: telefono-descartar no pulsa")
    borrar_ig = jerarquia(nodo_xml("[100,800][980,880]", texto="Recommencer ?"),
                          nodo_xml("[100,900][980,1000]", texto="Supprimer la publication ?"),
                          nodo_xml("[100,1100][980,1200]", texto="Supprimer", clase="android.widget.Button", extra='clickable="true"'))
    sim = TelefonoSimulado([borrar_ig])
    res, err = con_telefono_simulado(sim, lambda: pasos.descartar("instagram", evid, "descarte"))
    check(isinstance(err, P.PantallaInesperada) and "borrado" in str(err) and sim.toques == [],
          "I1: un título de borrado hace fallar cerrado aunque el diálogo tenga también un título de descarte")
```

- [x] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'textos' from 'labkit'` en la sección 14.

- [x] **Step 3: Implementar `textos.py`**

```python
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
                  r"\d[\d \u00a0\u202f]*publications?",
                  r"[\d \u00a0\u202f]+ publications publiques",
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
```

- [x] **Step 4: Añadir a `pantalla.py` la pista de idioma, el envío prohibido y el descarte**

Cambiar `from labkit import telefono` por `from labkit import telefono, textos` y añadir al final:

```python
def pista_idioma(xml: str, app: str) -> str:
    """« (ningún texto conocido…)» si el volcado tiene nodos de `app` pero ninguno de su tabla de
    textos: la app ha podido cambiar de idioma. Cadena vacía en otro caso."""
    propios = telefono.buscar_todos(xml, paquete=textos.PAQUETES[app])
    if not propios:
        return ""
    conocidos = set(textos.TEXTOS.get(app, {}).values())
    if any(n["texto"] in conocidos or n["desc"] in conocidos for n in propios):
        return ""
    return f" (ningún texto conocido de {app} en {textos.IDIOMAS.get(app, '?')}: ¿cambió el idioma de la app?)"


def dentro(interior: tuple[int, int, int, int], exterior: tuple[int, int, int, int]) -> bool:
    return (interior[0] >= exterior[0] and interior[1] >= exterior[1]
            and interior[2] <= exterior[2] and interior[3] <= exterior[3])


def _es_de_envio(n: dict, ignorar: tuple[str, ...] = ()) -> bool:
    if any(p and (n["texto"] == p or n["desc"].startswith(p)) for p in ignorar):
        return False
    return (textos.es_texto_envio(n["texto"]) or textos.es_texto_envio(n["desc"])
            or textos.es_texto_envio(n["resource_id"]) or n["texto"] in textos.NO_TOCAR or n["desc"] in textos.NO_TOCAR)


def es_envio(xml: str, n: dict, paquete: str, ignorar: tuple[str, ...] = ()) -> bool:
    """Pulsar `n` podría enviar (o tocar un control prohibido): su texto, descripción o id son de envío; o hay un
    control de envío dentro de sus bounds; o, si no es clickable, lo hay dentro de su antecesor clickable más
    cercano, que es el que recibe el toque; o un control de envío del paquete contiene su centro. Los nodos cuya
    etiqueta está en `ignorar` (texto exacto o principio de la content-desc) no cuentan: es la lista blanca de
    `pasos.tocar`, que no oculta ningún otro control de envío."""
    if _es_de_envio(n, ignorar):
        return True
    lista = telefono.nodos(xml)
    clave = ("bounds", "texto", "desc", "resource_id", "clase")
    i = next((k for k, m in enumerate(lista) if all(m[c] == n[c] for c in clave)), None)
    zonas = [n["bounds"]]
    if i is not None and not n["clickable"]:
        nivel = n["profundidad"]
        for anterior in reversed(lista[:i]):
            if anterior["profundidad"] >= nivel:
                continue
            nivel = anterior["profundidad"]
            if anterior["clickable"]:
                if _es_de_envio(anterior, ignorar):
                    return True
                zonas.append(anterior["bounds"])
                break
    cx, cy = n["centro"]
    return any(m["package"] == paquete and _es_de_envio(m, ignorar)
               and (any(dentro(m["bounds"], z) for z in zonas)
                    or (m["bounds"][0] <= cx < m["bounds"][2] and m["bounds"][1] <= cy < m["bounds"][3]))
               for m in lista)


def nodo_sonda(xml: str, paquete: str, *, texto: str | None = None, desc: str | None = None,
               resource_id: str | None = None) -> dict:
    """El único nodo de `paquete` con ese texto, content-desc o resource-id (basta el final tras
    «/»), si pulsarlo no puede enviar. Solo para sondas supervisadas."""
    def rid(valor: str) -> str:
        return valor.rsplit("/", 1)[-1]

    lista = [n for n in telefono.nodos(xml) if n["package"] == paquete and (
        (texto is not None and n["texto"] == texto) or (desc is not None and n["desc"] == desc)
        or (resource_id is not None and n["resource_id"] and rid(n["resource_id"]) == rid(resource_id)))]
    if len(lista) != 1:
        raise PantallaInesperada(f"la sonda solo toca un nodo único: {len(lista)} coincidencias")
    if es_envio(xml, lista[0], paquete):
        raise PantallaInesperada("la sonda no pulsa controles de envío ni prohibidos")
    return lista[0]


def boton_descarte(xml: str, app: str) -> dict:
    """El botón de descartar de `app`, solo si el volcado muestra su diálogo de descarte con los
    textos exactos de `textos.DESCARTE`. Nunca un control de envío."""
    paquete = textos.PAQUETES[app]
    tabla = textos.DESCARTE[app]
    borrado = next((n for n in telefono.buscar_todos(xml, paquete=paquete)
                    if any(v.strip() in textos.TITULOS_BORRADO for v in (n["texto"], n["desc"]) if v)), None)
    if borrado is not None:
        raise PantallaInesperada(f"el diálogo parece de borrado ({borrado['texto'] or borrado['desc']!r}), no de descarte: no se pulsa nada")
    if not any(telefono.buscar(xml, texto=t, paquete=paquete) for t in tabla["titulos"]):
        raise PantallaInesperada(f"no se ve el diálogo de descarte de {app} {tabla['titulos']}: no se pulsa nada")
    for etiqueta in tabla["botones"]:
        candidatos = telefono.buscar_todos(xml, texto=etiqueta, paquete=paquete)
        if candidatos:
            boton = elegir(candidatos, etiqueta)
            if es_envio(xml, boton, paquete):
                raise PantallaInesperada(f"el botón {etiqueta!r} del diálogo parece de envío: no se pulsa")
            return boton
    raise PantallaInesperada(f"el diálogo de descarte de {app} no tiene {tabla['botones']}")
```

> **Diseño corregido en `95a421c` (revisión de especificación tras `1f51ed1`).** El bloque de arriba es el original con tres huecos bloqueantes (B1-B3) y tres importantes (I1-I3); no copiarlo literal. El código vigente en el worktree:
>
> - **B1.** `es_envio` ya no se limita a mirar el antecesor clickable más cercano de la propia rama de `n`: recorre TODOS los nodos `m` de `telefono.nodos(xml)` que sean `clickable` y cuyas bounds contengan el centro de `n`, y para cada uno comprueba con un recorrido de subárbol (`_subarbol_tiene_envio`, usando el orden de documento y `profundidad` para encontrar los descendientes de `m`) si `m` o cualquiera de sus descendientes es de envío. Cubre tanto el caso antiguo (antecesor clickable de la propia rama) como un contenedor pulsable de OTRA rama del árbol que solo solapa geométricamente el punto tocado.
> - **B2.** `_es_de_envio(n, ignorar)` deja de devolver `False` para el nodo entero cuando un campo coincide con `ignorar`: mira cada campo (`texto`, `desc`, `resource_id`) por separado, exime SOLO el campo cuyo valor coincide exactamente con una etiqueta de `ignorar`, y sigue comprobando los demás campos del mismo nodo (un `desc` permitido no oculta un `texto` o un id de envío en el mismo nodo).
> - **B3.** `boton_descarte` compara títulos, `TITULOS_BORRADO` y los textos de `DESCARTE` con `textos.normalizar(...)` en vez de comparación literal (un NBSP o un espacio fino antes del «?» ya no cuelan un título de borrado como si fuera de descarte), y la detección de BORRADO recorre `telefono.nodos(xml)` sin filtrar por `paquete` (falla cerrado también si el título de borrado aparece bajo otro paquete del volcado); la detección del diálogo de DESCARTE (títulos y botones esperados) sigue filtrando por el paquete de `app`.
> - **I1.** `es_texto_envio` añade una comprobación de prefijo específica para `ENVIO_HISTORIA`: si la etiqueta normalizada empieza por un texto normalizado de `ENVIO_HISTORIA` y el carácter siguiente no es alfanumérico (separador: coma, paréntesis, espacio, punto medio…), cuenta como envío («Votre story, 2 nouvelles», «Amis proches (12)»); sin separador (p. ej. «Votre storyX») no cuenta.
> - **I2.** Nueva `textos.normalizar(valor)`: NFKC, quita los caracteres de categoría Unicode `Cf` (incluye los de ancho cero y las marcas de dirección), colapsa espacios (NBSP y espacio fino incluidos, que `str.split()` ya trata como separador) y `casefold()`. `es_texto_envio` y `boton_descarte` la usan en vez de su propio `" ".join(...).casefold()` suelto.
> - **I3.** La regla del centro de `es_envio` ya no exige `m["package"] == paquete`: cualquier nodo pulsable de cualquier paquete del volcado cuyas bounds contengan el centro cuenta si él o su subárbol es de envío (falla cerrado). El parámetro `paquete` de `es_envio` se mantiene por compatibilidad de firma pero ya no filtra esta regla.
>
> Ver `experiments/media-lab/labkit/pantalla.py` y `experiments/media-lab/labkit/textos.py` en el worktree para el código exacto, y `tests/test_media_lab.py` (bloque «Revisión de especificación (B1-B3, I1-I3)» dentro de `seccion_textos_y_descarte`) para las pruebas.

- [x] **Step 5: `pasos.py`: pista de idioma en las esperas, `descartar` y `tocar` con guardia de envío**

Sustituir `esperar_que` completa por:

```python
def esperar_que(cumple, descripcion: str, app: str | None = None) -> str:
    """Primer volcado válido que cumple la condición.

    El plazo de ESPERA_S se comprueba entre volcados y cada volcado recibe el tiempo que
    queda (5 s como mínimo), así que la espera total puede pasar de ESPERA_S en lo que tarde
    el último volcado. Con `app`, el error añade la pista de idioma del último volcado."""
    inicio = reloj.monotonic()
    ultimo_error = ""
    ultimo_xml = None
    while True:
        restante = max(5, int(ESPERA_S - (reloj.monotonic() - inicio)))
        try:
            xml = telefono.volcado(timeout=restante)
            ultimo_xml = xml
            if cumple(xml):
                return xml
        except telefono.TelefonoError as e:
            ultimo_error = f" (último error: {e})"
        transcurrido = reloj.monotonic() - inicio
        if transcurrido >= ESPERA_S:
            pista = pantalla.pista_idioma(ultimo_xml, app) if app and ultimo_xml else ""
            raise PantallaInesperada(f"no apareció {descripcion} tras {transcurrido:.1f} s{ultimo_error}{pista}")
        reloj.dormir(1.5)
```

y añadir tras `atras`:

```python
def descartar(app: str, evidencia: Path, nombre: str) -> Path:
    """Pulsa descartar solo si el volcado muestra el diálogo de descarte exacto de `app`."""
    exigir_listo()
    xml = volcado_fresco()
    boton = pantalla.boton_descarte(xml, app)
    telefono.tocar(*boton["centro"])
    reloj.dormir(2)
    return telefono.captura(evidencia / f"{nombre}.png")


def tocar(n: dict, xml: str, paquete: str, permitir: tuple[str, ...] = ()) -> None:
    """Toca `n`, leído de `xml`, solo si pulsarlo no puede enviar ni tocar un control prohibido
    (`pantalla.es_envio`): los envíos solo salen de `enviar`. `permitir` es la lista blanca explícita de
    etiquetas (texto exacto o principio de la content-desc) cuyos nodos dejan de contar como envío en este toque;
    cualquier otro control de envío en ese punto sigue bloqueando. Solo la usa `_visor_propio` para abrir la
    Story propia, tras verificar la pantalla."""
    if pantalla.es_envio(xml, n, paquete, ignorar=permitir):
        raise PantallaInesperada(f"no se toca un control que puede enviar o está prohibido fuera de compartir: "
                                 f"{n['texto'] or n['desc'] or n['resource_id']!r} en {n['bounds']}")
    telefono.tocar(*n["centro"])
```

- [x] **Step 6: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 14 en `✓` y `El laboratorio cumple sus contratos.`

- [x] **Step 7: Commit**

```bash
git add experiments/media-lab/labkit/textos.py experiments/media-lab/labkit/pantalla.py experiments/media-lab/labkit/pasos.py tests/test_media_lab.py
git commit -m "media lab claude: textos por app, pista de idioma, envío prohibido en sondas y diálogo de descarte

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `recetas.py` y selección de la fase 2 (refactor R, parte 4)

**Files:**
- Create: `experiments/media-lab/labkit/recetas.py`
- Modify: `experiments/media-lab/labkit/seleccion.py`
- Test: `tests/test_media_lab.py`

- [x] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_recetas_y_seleccion,`:

Con `import contextlib` entre las importaciones de cabecera del archivo, y `receta_temporal` fuera de la sección para que la tarea 5 la reutilice:

```python
_SIN_RECETA = object()


@contextlib.contextmanager
def receta_temporal(par: tuple[str, str], receta: dict):
    """`receta` como borrador de `par` en `recetas.TODAS` y `recetas.BORRADORES` mientras dura el
    bloque; al salir RESTAURA lo que hubiera en cada diccionario (o su ausencia), en vez de hacer pop."""
    from labkit import recetas as RC
    registros = (RC.TODAS, RC.BORRADORES)
    previos = [d.get(par, _SIN_RECETA) for d in registros]
    try:
        for d in registros:
            d[par] = receta
        yield receta
    finally:
        for d, previo in zip(registros, previos):
            if previo is _SIN_RECETA:
                d.pop(par, None)
            else:
                d[par] = previo


def seccion_recetas_y_seleccion() -> None:
    print("\n15. Fase 2: recetas y selección (un teléfono por ventana, copias, borradores)")
    import argparse
    from labkit import recetas as RC, seleccion as S, textos as TX

    check(S.TELEFONO_FASE_1 == S.TELEFONO_IMPLEMENTADO == frozenset(RC.RECETAS),
          "TELEFONO_FASE_1 es alias de TELEFONO_IMPLEMENTADO, que sale de RECETAS")
    check(("instagram", "feed_single_image") in S.TELEFONO_IMPLEMENTADO, "el feed de Instagram sigue implementado")
    verificacion_ig = RC.TODAS[("instagram", "feed_single_image")]["verificacion"]
    check("menú" not in verificacion_ig and "missing_data_reasons.post_url" in verificacion_ig,
          "la receta del feed de Instagram no promete la URL desde el menú del teléfono: va a missing_data_reasons.post_url")
    check(set(RC.PROMOVIDAS) <= set(RC.TODAS) and not set(RC.RECETAS) & set(RC.BORRADORES)
          and set(RC.RECETAS) | set(RC.BORRADORES) == set(RC.TODAS),
          "PROMOVIDAS está en TODAS y RECETAS/BORRADORES la reparten")
    for par, receta in RC.TODAS.items():
        check(all(k in receta for k in RC.CLAVES) and receta["publicar"] and receta["estados_ok"] == ["confirmado"],
              f"{par}: receta con todas sus claves, un paso de publicar y solo confirmado sale con 0")
        check(all(set(cp) == {"red", "superficie", "nota"} and cp["red"] in set(TX.APPS_TELEFONO)
                  for cp in receta["copias"]),
              f"{par}: cada copia nombra una red conocida con superficie y nota")

    ap = modulo_lab().construir()
    subcomandos = next(a for a in ap._actions if isinstance(a, argparse._SubParsersAction)).choices
    for par, receta in RC.TODAS.items():
        check(receta["subcomando"] in subcomandos, f"{par}: el subcomando {receta['subcomando']} existe en lab.construir()")
        for fase in RC.FASES:
            for c in receta[fase]:
                sub = subcomandos.get(c["args"][0])
                paso = next((x for x in sub._actions if x.dest == "paso"), None) if sub else None
                check(sub is not None and (paso is None or c["args"][1] in paso.choices),
                      f"{par}/{fase}: «{' '.join(c['args'][:2])}» existe en lab.py")
    linea = RC.renderizar(RC.para("instagram", "feed_single_image"))["preparar"][1]["linea"]
    check(linea.startswith(".venv/bin/python experiments/media-lab/lab.py ig abrir --run <run>"),
          f"renderizar da la línea lista para ejecutar ({linea})")
    render = RC.renderizar(RC.para("instagram", "feed_single_image"))
    render["copias"][0]["red"] = "mutada"
    render["formato_encargo"]["ancho"] = 1
    render["preparar"][0]["args"][0] = "mutado"
    render["preparar"][0]["anota"].append("mutado")
    original = RC.TODAS[("instagram", "feed_single_image")]
    check(original["copias"][0]["red"] == "facebook" and original["formato_encargo"]["ancho"] == 1080
          and original["preparar"][0]["args"][0] == "telefono-subir" and original["preparar"][0]["anota"] == ["subido_en"]
          and "linea" not in original["preparar"][0],
          "mutar el resultado de renderizar no cambia RC.TODAS")
    try:
        RC.para("threads", "feed_video")
        ok = False
    except RC.RecetaNoDisponible:
        ok = True
    check(ok, "para() rechaza un par sin receta promovida")

    def celda(cid, plataforma, formato, ruta):
        return {"cell_id": cid, "platform": plataforma, "native_format": formato,
                "publishing_route": ruta, "status": "planned"}

    ig_tel = celda("A", "instagram", "feed_single_image", "android_native")
    th_tel = celda("B", "threads", "feed_video", "android_native")
    ig_api = celda("C", "instagram", "feed_single_image", "api")
    check(not S.compatibles(ig_tel, th_tel) and not S.compatibles(th_tel, ig_tel),
          "nunca dos celdas android_native en la misma ventana")
    check(S.compatibles(th_tel, ig_api), "sin copias declaradas, Threads por teléfono e Instagram por API son compatibles")
    par_th = ("threads", "feed_video")
    with receta_temporal(par_th, {**RC.TODAS[("instagram", "feed_single_image")],
                                  "copias": [{"red": "instagram", "superficie": "feed", "nota": "prueba"}]}):
        check(not S.compatibles(th_tel, ig_api) and not S.compatibles(ig_api, th_tel),
              "una copia declarada en la receta excluye esa red en la misma ventana")
        check(S._ruta_implementada(th_tel, borradores=True) and not S._ruta_implementada(th_tel),
              "un borrador solo cuenta como implementado con borradores=True")
        check(S.elegir([th_tel], [{"estado": "aprobado", "coverage_cell_ids": ["B"]}]) == [],
              "seleccionar nunca elige una celda de un borrador")
    check(par_th not in RC.TODAS and par_th not in RC.BORRADORES, "receta_temporal quita al salir un par que no existía")
    sin_copias = {k: v for k, v in RC.TODAS[("instagram", "feed_single_image")].items() if k != "copias"}
    with receta_temporal(par_th, sin_copias):
        check(lanza(lambda: S.compatibles(th_tel, ig_api), KeyError),
              "una receta sin clave copias falla visible en vez de quitar la exclusión en silencio")
    par_ig = ("instagram", "feed_single_image")
    original_ig = RC.TODAS[par_ig]
    with receta_temporal(par_ig, sin_copias):
        pass
    check(RC.TODAS[par_ig] is original_ig and par_ig not in RC.BORRADORES,
          "receta_temporal restaura el valor previo de TODAS y la ausencia en BORRADORES")
```

- [x] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'recetas' from 'labkit'` en la sección 15.

- [x] **Step 3: Implementar `recetas.py`**

```python
"""
Registro único de flujos del teléfono.

`TODAS` guarda cada receta escrita. Un par (red, native_format) solo cuenta como implementado
cuando está en `PROMOVIDAS`, con el run de su primera publicación `confirmado` en una ventana
manual. `RECETAS` son las promovidas (de ahí sale `seleccion.TELEFONO_IMPLEMENTADO`) y
`BORRADORES` las demás, que solo aceptan `lab.py encargo-nuevo --borrador` y
`lab.py receta --borrador` (tarea 5) para esa ventana manual.

Cada receta dice a la ventana, en orden, qué comandos de `lab.py` ejecutar en cada fase
(`preparar` hasta la captura de QA, `publicar` y `verificar`), qué valores anota cada uno para
los siguientes (`<valor>` en `args`), qué debe verse en su captura, qué estados salen con 0,
cómo se concilia un 5 y qué copias automáticas produce (`copias`, que también excluyen esa red
en la misma ventana).
"""
from __future__ import annotations

import copy

LAB = ".venv/bin/python experiments/media-lab/lab.py"
CLAVES = ("subcomando", "superficie", "formato_encargo", "preparar", "publicar", "verificar",
          "estados_ok", "conciliacion", "copias", "verificacion", "nota")
FASES = ("preparar", "publicar", "verificar")


class RecetaNoDisponible(ValueError):
    pass


def _cmd(*args: str, ver: str, anota: tuple[str, ...] = ()) -> dict:
    return {"args": list(args), "ver": ver, "anota": list(anota)}


FEED_INSTAGRAM = {
    "subcomando": "ig",
    "superficie": "feed",
    "formato_encargo": {"ancho": 1080, "alto": 1350},
    "preparar": [
        _cmd("telefono-subir", "--local", "<master>", ver="JSON con sha256 y subido_en; no hay captura",
             anota=("subido_en",)),
        _cmd("ig", "abrir", "--run", "<run>", "--subido-en", "<subido_en>",
             ver="ig-01-selector.png: «Nouvelle publication» con la foto subida marcada",
             anota=("publicaciones_antes",)),
        _cmd("ig", "recorte", "--run", "<run>", ver="ig-02-recorte.png: la imagen completa en 4:5 (el volcado no lo muestra)"),
        _cmd("ig", "editor", "--run", "<run>", ver="ig-02b-editor.png: editor con la imagen y el chip «Audio suggéré»"),
        _cmd("ig", "audio", "--run", "<run>", ver="ig-03-audio.png: chip de música añadido", anota=("tema",)),
        _cmd("ig", "detalles", "--run", "<run>", ver="ig-03b-detalles.png: detalles con la fila de música"),
        _cmd("ig", "pie", "--run", "<run>", "--pie", "<pie>",
             ver="ig-04-compositor.png: pie, música y «Partager» sin teclado ni desplegable (captura de la QA)"),
    ],
    "publicar": [
        _cmd("ig", "compartir", "--run", "<run>", "--pie", "<pie>", "--tema", "<tema>",
             "--publicaciones-antes", "<publicaciones_antes>", "[--produccion-cercana]",
             ver="ig-05-publicado.png: perfil de @sabiduriabolsillo tras compartir; "
                 "--produccion-cercana si el último preflight trajo espera"),
    ],
    "verificar": [
        _cmd("telefono-captura", "--run", "<run>", "--nombre", "ig-06-perfil",
             ver="ig-06-perfil.png: la publicación nueva arriba en la cuadrícula del perfil; "
                 "si no muestra el perfil, no navegues a ciegas: anótalo y usa ig-05-publicado"),
    ],
    "estados_ok": ["confirmado"],
    "conciliacion": ("Con 5 no repitas nada: mira captura y captura_antes, captura el perfil con telefono-captura y "
                     "compara la primera publicación con el máster y el pie antes de registrar; nunca por la otra ruta."),
    "copias": [{"red": "facebook", "superficie": "feed",
                "nota": "Instagram comparte la foto en la Página: va en publication.cross_posting del run"}],
    "verificacion": ("Identidad, imagen, pie y música en la captura del perfil. La URL no se lee en el teléfono: "
                     "por `manifiesto-verificacion --instagram-shortcode` si se conoce el shortcode; "
                     "si no, en `missing_data_reasons.post_url`."),
    "nota": "",
}

TODAS: dict[tuple[str, str], dict] = {
    ("instagram", "feed_single_image"): FEED_INSTAGRAM,
}
PROMOVIDAS: dict[tuple[str, str], str] = {
    ("instagram", "feed_single_image"): "CELL-018: primera ventana manual confirmada (2026-09-14)",
}
_faltan = set(PROMOVIDAS) - set(TODAS)
if _faltan:
    raise RuntimeError(f"PROMOVIDAS sin receta en TODAS: {sorted(_faltan)}")
RECETAS = {par: TODAS[par] for par in PROMOVIDAS}
BORRADORES = {par: receta for par, receta in TODAS.items() if par not in PROMOVIDAS}


def para(red: str, formato: str, borrador: bool = False) -> dict:
    """La promovida si existe; el borrador solo con `borrador=True`; si no, `RecetaNoDisponible`,
    con pista cuando hay borrador y no se pidió.

    Devuelve el objeto del propio registro: es de solo lectura (para una copia, `renderizar`)."""
    par = (red, formato)
    if par in RECETAS:
        return RECETAS[par]
    if borrador and par in BORRADORES:
        return BORRADORES[par]
    pista = "" if borrador or par not in BORRADORES else " (hay borrador: --borrador solo en ventana manual)"
    raise RecetaNoDisponible(f"{red}/{formato} no está implementado por teléfono{pista}")


def renderizar(receta: dict) -> dict:
    """Copia profunda de la receta con cada comando también como línea lista para ejecutar;
    mutarla no cambia el registro."""
    fuera = {k: copy.deepcopy(v) for k, v in receta.items() if k not in FASES}
    for fase in FASES:
        fuera[fase] = [{**copy.deepcopy(c), "linea": " ".join([LAB, *c["args"]])} for c in receta[fase]]
    return fuera
```

- [x] **Step 4: `seleccion.py` de la fase 2**

Sustituir el archivo completo:

```python
"""
Qué celdas salen en esta ventana.

Una celda es elegible si aún no se ha publicado, tiene un encargo aprobado o ya usado en otra
de sus celdas (el estado de cada celda impide republicar) y su red y formato están
implementados para su ruta: por API, `API_FASE_1`; por teléfono, las recetas promovidas
(`TELEFONO_IMPLEMENTADO`). Sin teléfono listo no se eligen celdas de teléfono.

Reglas entre las celdas de una ventana:
- La segunda difiere de la primera en red o ruta.
- Ninguna de Facebook con una de Instagram por teléfono, en cualquier formato.
- Como máximo una `android_native`: MaaS360 bloquea a los 120 s y la segunda saldría al menos
  21 min después, casi siempre con el teléfono bloqueado.
- Ninguna de una red que la receta de la celda de teléfono copia automáticamente (`copias`).
"""
from __future__ import annotations

from labkit import recetas

ESTADOS_ELEGIBLES = ("planned", "ready")
ESTADOS_ENCARGO_UTILES = ("aprobado", "usado")
TELEFONO_IMPLEMENTADO = frozenset(recetas.RECETAS)
TELEFONO_FASE_1 = TELEFONO_IMPLEMENTADO  # alias durante la transición a la fase 2
API_FASE_1 = {("facebook", "feed_single_image"), ("facebook", "story_image"),
              ("instagram", "feed_single_image"), ("instagram", "story_image"),
              ("threads", "feed_single_image")}


def _es_telefono(c: dict) -> bool:
    return c["publishing_route"] == "android_native"


def _ruta_implementada(c: dict, borradores: bool = False) -> bool:
    clave = (c["platform"], c["native_format"])
    if c["publishing_route"] == "api":
        return clave in API_FASE_1
    if _es_telefono(c):
        return clave in TELEFONO_IMPLEMENTADO or (borradores and clave in recetas.BORRADORES)
    return False


def elegibles(celdas: list[dict], todos_encargos: list[dict], telefono_listo: bool = True) -> list[dict]:
    utiles = {cid for e in todos_encargos if e["estado"] in ESTADOS_ENCARGO_UTILES
              for cid in e["coverage_cell_ids"]}
    return [c for c in celdas
            if c["status"] in ESTADOS_ELEGIBLES and c["cell_id"] in utiles and _ruta_implementada(c)
            and (telefono_listo or not _es_telefono(c))]


def _es_ig_telefono(c: dict) -> bool:
    return c["platform"] == "instagram" and _es_telefono(c)


def _redes_copiadas(c: dict) -> set[str]:
    """Redes que la receta de una celda de teléfono copia sola. Una receta sin `copias` falla
    visible (KeyError) en vez de quitar la exclusión en silencio."""
    if not _es_telefono(c):
        return set()
    receta = recetas.TODAS.get((c["platform"], c["native_format"]))
    return set() if receta is None else {copia["red"] for copia in receta["copias"]}


def compatibles(a: dict, b: dict) -> bool:
    if a["platform"] == b["platform"] and a["publishing_route"] == b["publishing_route"]:
        return False
    if (_es_ig_telefono(a) and b["platform"] == "facebook") or (_es_ig_telefono(b) and a["platform"] == "facebook"):
        return False
    if _es_telefono(a) and _es_telefono(b):
        return False
    if b["platform"] in _redes_copiadas(a) or a["platform"] in _redes_copiadas(b):
        return False
    return True


def elegir(celdas: list[dict], todos_encargos: list[dict], max_celdas: int = 2,
           telefono_listo: bool = True) -> list[dict]:
    elegidas: list[dict] = []
    for c in elegibles(celdas, todos_encargos, telefono_listo):
        if len(elegidas) >= max_celdas:
            break
        if all(compatibles(c, e) for e in elegidas):
            elegidas.append(c)
    return elegidas
```

- [x] **Step 5: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 15 en `✓`, la sección 4 de la fase 1 sin cambios y `El laboratorio cumple sus contratos.`

- [x] **Step 6: Commit**

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/labkit/seleccion.py tests/test_media_lab.py
git commit -m "media lab claude: recetas del teléfono, TELEFONO_IMPLEMENTADO y un teléfono por ventana

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `lab.py receta`, atrás por app, descarte y borradores (refactor R, parte 5)

**Files:**
- Modify: `experiments/media-lab/lab.py`
- Test: `tests/test_media_lab.py`

- [x] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_cli_fase2,`:

> **Nota (revisión de calidad de la tarea 4):** esta prueba debe usar `receta_temporal(par_th, RC.TODAS[("instagram", "feed_single_image")])` (definida en la tarea 4, fuera de la sección 15) alrededor de los pasos con `--borrador`, en vez de asignar a mano `RC.TODAS[par_th]`/`RC.BORRADORES[par_th]` y hacer `pop` en el `finally`: el gestor restaura lo que hubiera en vez de borrarlo. El código de abajo aún muestra la forma antigua; se adapta al implementar la tarea 5.

```python
def rechazo(res, fragmento: str, tipo: str = "ArgumentoNoValido") -> bool:
    """`res` = (código, datos, stderr) de lab.py: salió con 2, con `tipo` y un error que contiene `fragmento`."""
    if res is None:
        return False
    codigo, datos, _ = res
    return codigo == 2 and campo(datos, "tipo") == tipo and fragmento in str(campo(datos, "error") or "")


CELDAS_FASE2 = [
    {"cell_id": "C-IG-TEL", "platform": "instagram", "native_format": "feed_single_image",
     "publishing_route": "android_native", "status": "planned"},
    {"cell_id": "C-TH-TEL", "platform": "threads", "native_format": "feed_video",
     "publishing_route": "android_native", "status": "planned"},
    {"cell_id": "C-FB-API", "platform": "facebook", "native_format": "feed_single_image",
     "publishing_route": "api", "status": "planned"},
]


def entorno_lab_fase2():
    """Context manager: lab.py en proceso sobre una carpeta temporal con CELDAS_FASE2."""
    import contextlib
    import json
    import tempfile

    @contextlib.contextmanager
    def gestor():
        with tempfile.TemporaryDirectory() as d:
            raiz = pathlib.Path(d)
            (raiz / "encargos").mkdir()
            (raiz / "coverage.json").write_text(json.dumps({"cells": CELDAS_FASE2}), encoding="utf-8")
            (raiz / "prompt.txt").write_text("Un astrolabio de latón", encoding="utf-8")
            with LabAislado(raiz) as lab:
                yield lab, raiz
    return gestor()


def seccion_cli_fase2() -> None:
    print("\n16. Fase 2: lab.py receta, atrás por app, descarte y borradores")
    from labkit import pasos, recetas as RC

    recibido: dict = {}
    atras_original, descartar_original = pasos.atras, pasos.descartar
    par_th = ("threads", "feed_video")
    try:
        pasos.atras = lambda paquete, ev, nombre: recibido.update(atras=paquete) or ev / f"{nombre}.png"
        pasos.descartar = lambda app, ev, nombre: recibido.update(descartar=app) or ev / f"{nombre}.png"
        with entorno_lab_fase2() as (lab, raiz):
            codigo, datos, _ = lab("receta", "--celda", "C-IG-TEL")
            preparar = campo(datos, "preparar") or []
            check(codigo == 0 and campo(datos, "red") == "instagram" and campo(datos, "borrador") is False
                  and preparar and preparar[0]["args"][0] == "telefono-subir",
                  f"receta de una celda de teléfono implementada ({codigo}, {datos and list(datos)})")
            codigo, datos, _ = lab("receta", "--celda", "C-FB-API")
            check(rechazo((codigo, datos, _), "solo de teléfono"), f"receta rechaza una celda de API ({codigo}, {datos})")
            codigo, datos, _ = lab("receta", "--celda", "C-TH-TEL")
            check(rechazo((codigo, datos, _), "no está implementado"),
                  f"receta rechaza un par sin receta ({codigo}, {datos})")
            codigo, datos, _ = lab("receta", "--celda", "C-NADA")
            check(rechazo((codigo, datos, _), "no está en coverage.json"), "receta rechaza una celda que no existe")

            codigo, datos, _ = lab("telefono-atras", "--app", "threads", "--run", "RUN-1", "--nombre", "salida-1")
            check(codigo == 0 and recibido.get("atras") == "com.instagram.barcelona"
                  and str(campo(datos, "captura")).endswith("RUN-1/salida-1.png"),
                  f"telefono-atras --app threads usa el paquete de Threads ({codigo}, {recibido})")
            check(rechazo(lab("telefono-atras", "--app", "tiktok", "--run", "RUN-1", "--nombre", "s"), "--app"),
                  "telefono-atras rechaza una app sin flujo")
            codigo, datos, _ = lab("telefono-descartar", "--app", "facebook", "--run", "RUN-1", "--nombre", "descarte")
            check(codigo == 0 and recibido.get("descartar") == "facebook",
                  f"telefono-descartar pasa la app a pasos.descartar ({codigo}, {recibido})")
            check(rechazo(lab("telefono-descartar", "--run", "RUN-1", "--nombre", "descarte"), "--app"),
                  "telefono-descartar exige --app")

            nuevo = ("encargo-nuevo", "--cell", "C-TH-TEL", "--family", "LAB-CLI-002", "--brief", "b.md",
                     "--formato", '{"ancho":1080,"alto":1350}', "--prompt-file", raiz / "prompt.txt")
            codigo, datos, _ = lab(*nuevo)
            check(rechazo((codigo, datos, _), "no está implementado"),
                  f"encargo-nuevo rechaza una celda de teléfono sin receta ({codigo})")
            RC.TODAS[par_th] = RC.TODAS[("instagram", "feed_single_image")]
            RC.BORRADORES[par_th] = RC.TODAS[par_th]
            codigo, datos, _ = lab(*nuevo, "--borrador")
            check(codigo == 0 and campo(datos, "coverage_cell_ids") == ["C-TH-TEL"],
                  f"encargo-nuevo --borrador acepta una celda de un borrador ({codigo}, {datos})")
            codigo, datos, _ = lab("receta", "--celda", "C-TH-TEL", "--borrador")
            check(codigo == 0 and campo(datos, "borrador") is True, f"receta --borrador marca el borrador ({codigo})")
            check(rechazo(lab("receta", "--celda", "C-TH-TEL"), "--borrador"), "sin --borrador la receta de un borrador no sale")
    finally:
        pasos.atras, pasos.descartar = atras_original, descartar_original
        RC.TODAS.pop(par_th, None)
        RC.BORRADORES.pop(par_th, None)
```

- [x] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con, entre otros, `receta de una celda de teléfono implementada` y `telefono-descartar pasa la app a pasos.descartar` (argparse no conoce los subcomandos y sale con 2).

- [x] **Step 3: Implementar en `lab.py`**

1. Cambiar la importación de `labkit` por:

```python
from labkit import cerrojo, codex_rescate, colision, encargos, guardia, manifiesto, recetas, seleccion, textos  # noqa: E402
```

2. En `_comprobar_celdas`, cambiar la firma a `def _comprobar_celdas(ids: list[str], todos: list[dict], borradores: bool = False) -> None:` y la comprobación de ruta a:

```python
        if not seleccion._ruta_implementada(c, borradores):
```

3. En `cmd_encargo_nuevo`, cambiar `_comprobar_celdas(a.cell, todos)` por `_comprobar_celdas(a.cell, todos, a.borrador)`.

4. Añadir tras `cmd_seleccionar`:

```python
def cmd_receta(a) -> int:
    celdas = {c["cell_id"]: c for c in json.loads(COBERTURA.read_text(encoding="utf-8"))["cells"]}
    c = celdas.get(a.celda)
    _exigir(c is not None, f"{a.celda} no está en coverage.json")
    _exigir(c["publishing_route"] == "android_native",
            f"{a.celda} va por {c['publishing_route']}: las recetas son solo de teléfono")
    try:
        receta = recetas.para(c["platform"], c["native_format"], borrador=a.borrador)
    except recetas.RecetaNoDisponible as e:
        raise ArgumentoNoValido(str(e)) from e
    emitir({"celda": a.celda, "red": c["platform"], "formato": c["native_format"],
            "borrador": (c["platform"], c["native_format"]) not in recetas.RECETAS,
            **recetas.renderizar(receta)})
    return 0
```

5. En `_paso_telefono`, cambiar `from labkit import instagram_feed, telefono` por `from labkit import pantalla, telefono` y el `except` por `except (pantalla.PantallaInesperada, telefono.TelefonoError, OSError) as e:` (es la misma clase que `instagram_feed.PantallaInesperada`).

6. Sustituir `cmd_telefono_atras` y añadir `cmd_telefono_descartar`:

```python
def cmd_telefono_atras(a) -> int:
    from labkit import instagram_feed, pasos
    ev = _evidencia(a.run)
    if a.app == "instagram":
        return _paso_telefono(ev, f"{a.nombre}-inesperada",
                              lambda: {"captura": str(instagram_feed.atras(ev, a.nombre))})
    return _paso_telefono(ev, f"{a.nombre}-inesperada",
                          lambda: {"captura": str(pasos.atras(textos.PAQUETES[a.app], ev, a.nombre))})


def cmd_telefono_descartar(a) -> int:
    from labkit import pasos
    ev = _evidencia(a.run)
    return _paso_telefono(ev, f"{a.nombre}-inesperada",
                          lambda: {"captura": str(pasos.descartar(a.app, ev, a.nombre))})
```

7. En `construir`: añadir a `encargo-nuevo`

```python
    p.add_argument("--borrador", action="store_true",
                   help="admite celdas de recetas aún no promovidas (solo ventana manual)")
```

añadir tras `seleccionar`

```python
    p = sub.add_parser("receta")
    p.add_argument("--celda", required=True)
    p.add_argument("--borrador", action="store_true", help="también recetas aún no promovidas (solo ventana manual)")
    p.set_defaults(func=cmd_receta)
```

y sustituir el bucle `for nombre, func in (("telefono-captura", cmd_telefono_captura), ("telefono-atras", cmd_telefono_atras)):` completo por:

```python
    p = sub.add_parser("telefono-captura")
    p.add_argument("--run", required=True)
    p.add_argument("--nombre", required=True)
    p.set_defaults(func=cmd_telefono_captura)
    p = sub.add_parser("telefono-atras")
    p.add_argument("--app", choices=textos.APPS_TELEFONO, default="instagram")
    p.add_argument("--run", required=True)
    p.add_argument("--nombre", required=True)
    p.set_defaults(func=cmd_telefono_atras)
    p = sub.add_parser("telefono-descartar")
    p.add_argument("--app", choices=textos.APPS_TELEFONO, required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--nombre", required=True)
    p.set_defaults(func=cmd_telefono_descartar)
```

- [x] **Step 4: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 16 en `✓`, la 10 de la fase 1 sin cambios y `El laboratorio cumple sus contratos.`

- [x] **Step 5: Commit**

```bash
git add experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: lab.py receta, telefono-atras --app, telefono-descartar y encargos de borrador

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [x] **Step 6: Comprobación supervisada del refactor en el teléfono real (sin publicar)** — hecha el 2026-09-15 por el controlador sin el usuario presente (el móvil es un dispositivo dedicado del laboratorio, con permiso explícito del usuario). Primer `ig abrir` con 4 por un Reel reproduciéndose; reintento tras `am force-stop` correcto; perfil en 3718 antes y después. Ver `findings.md`.

> **Controlador con el usuario presente (no subagente).** Es la primera vez que el feed de Instagram corre sobre `pasos.py` en el teléfono: si falla, no se hace push.

**Cerrojo y turno:** el refactor aún no está integrado, así que el cerrojo se toma desde el árbol principal y los pasos con el teléfono salen del worktree. Antes de empezar, mirar el próximo turno con `cd /Users/hec/dev/sabiduriaPublisher && .venv/bin/python experiments/media-lab/lab.py turno` (sin `--marcar`) y tomar el cerrojo con `.venv/bin/python experiments/media-lab/lab.py lock-tomar --dueno manual` en ese mismo árbol (si devuelve `cerrojo: false`, esperar a que termine la ventana en curso y repetir); renovarlo igual antes de 90 min (`cerrojo.ABANDONO`). Los comandos de abajo se ejecutan desde el worktree con `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python experiments/media-lab/lab.py …`.

1. `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python experiments/media-lab/lab.py preflight` → `telefono.listo: true` (si no, pedir al usuario que desbloquee).
2. `lab.py telefono-subir --local <un máster 4:5 ya comiteado bajo experiments/media-lab/assets/>` y anotar `subido_en`.
3. `lab.py ig abrir --run SONDA-F2-R --subido-en <subido_en>`, `ig recorte --run SONDA-F2-R`, `ig editor --run SONDA-F2-R`, `ig audio --run SONDA-F2-R`, `ig detalles --run SONDA-F2-R` e `ig pie --run SONDA-F2-R --pie <un pie ya comiteado>`, abriendo cada captura con Read: selector con la foto, 4:5, editor, música añadida, detalles y compositor con pie, música y «Partager» sin teclado ni desplegable. Nunca `ig compartir`.
4. Salir: `lab.py telefono-atras --app instagram --run SONDA-F2-R --nombre salida-N` hasta que la captura muestre «Recommencer ?» y entonces `lab.py telefono-descartar --app instagram --run SONDA-F2-R --nombre descarte`; con el perfil delante, `lab.py telefono-captura --run SONDA-F2-R --nombre perfil` y comprobar que el número de publicaciones no cambió.
5. Si un paso sale con 4 o una captura no muestra lo esperado: no hay push (se suelta igualmente el cerrojo desde el árbol principal); se corrige en la tarea del refactor que corresponda y se repite este paso. Anotar el resultado en `findings.md` («Comprobación del refactor R en el teléfono (<fecha>, sin publicar)»). Las capturas de `SONDA-F2-R` no se comitean.

- [x] **Step 7: Primer push del refactor** — `568b41c` en `origin/main` (2026-09-15, 779 checks en verde en el worktree y en el árbol principal).

Solo si el Step 6 salió bien, desde el worktree:

```bash
git add experiments/media-lab/findings.md
git commit -m "media lab claude: refactor R comprobado en el teléfono sin publicar

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

Después, desde el árbol principal: `.venv/bin/python experiments/media-lab/lab.py lock-soltar --dueno manual`.

---

### Task 6: `lab.py sonda`, `fixtures.py` y `fixture-podar` (refactor R, parte 6)

**Files:**
- Create: `experiments/media-lab/labkit/fixtures.py`
- Modify: `experiments/media-lab/lab.py`
- Test: `tests/test_media_lab.py`

- [x] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_sonda_y_fixtures,`:

```python
def seccion_sonda_y_fixtures() -> None:
    print("\n17. Fase 2: sondas supervisadas y fixtures podados")
    from labkit import fixtures as FX, telefono as T, textos as TX

    crudo = jerarquia(
        nodo_xml("[0,0][1080,100]", texto="12:04", paquete="com.android.systemui"),
        nodo_xml("[0,200][1080,300]", texto="Profil", desc="Profil"),
        nodo_xml("[0,400][1080,500]", texto="Hola Juan, ¿quedamos mañana?", extra='hint="Écrivez à Juan"'),
        nodo_xml("[0,600][540,900]", desc="Sélectionné Miniature de la photo du 14 septembre 2026 10:39"),
        nodo_xml("[0,1000][1080,1100]", texto="#citasdiarias"))
    podado = FX.podar(crudo, "instagram")
    pares = [(n["texto"], n["desc"]) for n in T.nodos(podado)]
    check(all(n["package"] == PAQUETE_IG for n in T.nodos(podado)), "podar quita los nodos de com.android.systemui")
    check(("Profil", "Profil") in pares and ("#citasdiarias", "") in pares
          and ("", "Sélectionné Miniature de la photo du 14 septembre 2026 10:39") in pares,
          f"podar conserva textos de la tabla, hashtags y fechas de miniatura ({pares})")
    check("Juan" not in podado and "quedamos" not in podado, "podar vacía el texto y el hint personales")
    check(FX.revisar(podado, "instagram") == [] and FX.revisar(crudo, "instagram"),
          "revisar da limpio lo podado y señala lo crudo")

    base = ROOT / "tests" / "fixtures" / "telefono"
    for ruta in sorted(base.glob("*/*.xml")):
        app = ruta.parent.name
        problemas = (FX.revisar(ruta.read_text(encoding="utf-8"), app) if app in TX.APPS_TELEFONO
                     else [f"carpeta de app desconocida: {app}"])
        check(not problemas, f"{ruta.relative_to(ROOT)} está podado y sin com.android.systemui ({problemas[:3]})")

    with entorno_lab_fase2() as (lab, raiz):
        supervisada = ("--run", "SONDA-F2-T", "--nombre", "a", "--supervisada")
        check(lab.lab._evidencia("SONDA-F2-X") == raiz / "evidence" / "sondas-f2" / "SONDA-F2-X"
              and lab.lab._evidencia("LAB-X") == raiz / "evidence" / "LAB-X",
              "las evidencias de las sondas SONDA-F2-* van a sondas-f2/ (ignorada por git)")
        for extra, label in ((("--texto", "Partager"), "«Partager»"),
                             (("--desc", "Compartir historia"), "«Compartir historia»"),
                             (("--resource-id", "com.instagram.barcelona:id/new_thread_screen_post_button"),
                              "el id del botón de publicar de Threads"),
                             (("--texto", "Anular"), "«Anular»"),
                             (("--desc", "Votre story"), "«Votre story» (publica la Story)")):
            sim = TelefonoSimulado([xml_compositor()])
            res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, *extra))
            check(rechazo(res, "envío") and sim.toques == [] and sim.volcados_leidos == 0,
                  f"sonda tocar se niega a pulsar {label} antes de tocar el teléfono ({res and res[0]}, {err!r})")
        for args, fragmento, label in ((("sonda", "instagram", "volcar", "--run", "SONDA-F2-T", "--nombre", "a"), "--supervisada",
                                        "sin --supervisada"),
                                       (("sonda", "instagram", "volcar", "--run", "LAB-X", "--nombre", "a", "--supervisada"), "SONDA-F2-",
                                        "--run que no empieza por SONDA-F2-"),
                                       (("sonda", "instagram", "tocar", *supervisada), "--texto", "tocar sin criterio")):
            sim = TelefonoSimulado([xml_compositor()])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0, f"sonda rechaza {label}")

        sim = TelefonoSimulado([XML_BOTON_ENVIO_CON_ICONO])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--desc", "Icône"))
        check(res is not None and res[0] == 4 and sim.toques == [],
              f"sonda tocar no pulsa un icono dentro del botón de envío ({res and res[0]}, {err!r})")
        sim = TelefonoSimulado([XML_BOTON_ENVIO_CON_ICONO])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "instagram", "tocar", *supervisada, "--texto", "Suivant"))
        volcado = raiz / "evidence" / "sondas-f2" / "SONDA-F2-T" / "a.xml"
        check(res is not None and res[0] == 0 and sim.toques == [(963, 170)] and volcado.is_file()
              and sim.capturas == ["a.png"],
              f"sonda tocar pulsa un nodo único y deja volcado y captura ({res and res[0]}, {sim.toques})")
        sim = TelefonoSimulado([xml_perfil()])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "threads", "lanzar", "--run", "SONDA-F2-T",
                                                          "--nombre", "b", "--supervisada"))
        check(res is not None and res[0] == 0 and sim.orden == ["lanzar:com.instagram.barcelona"] and sim.toques == [],
              f"sonda lanzar abre la app y vuelca sin tocar ({res and res[0]}, {sim.orden})")

        rel = "experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-T/crudo.xml"
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text(crudo, encoding="utf-8")
        codigo, datos, _ = lab("fixture-podar", "--app", "instagram", "--desde", rel, "--pantalla", "perfil")
        destino = raiz / "tests" / "fixtures" / "telefono" / "instagram" / "perfil.xml"
        check(codigo == 0 and destino.is_file() and "Juan" not in destino.read_text(encoding="utf-8"),
              f"fixture-podar escribe el fixture podado ({codigo}, {datos})")
        for args, fragmento, label in ((("--desde", "/etc/hosts", "--pantalla", "x"), "--desde", "un origen fuera de evidence"),
                                       (("--desde", rel, "--pantalla", "../x"), "--pantalla", "una pantalla con ..")):
            check(rechazo(lab("fixture-podar", "--app", "instagram", *args), fragmento), f"fixture-podar rechaza {label}")
```

- [x] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'fixtures' from 'labkit'` en la sección 17.

- [x] **Step 3: Implementar `fixtures.py`**

```python
"""
Fixtures del teléfono: volcados reales podados de datos personales.

`podar` quita los nodos de otros paquetes (sistema, notificaciones, teclado) y vacía cualquier
atributo de texto que no esté en `textos` (interfaz, marca, envío, descarte) ni case con sus
patrones (fechas de miniatura, edades, recuentos, hashtags). `revisar` comprueba lo mismo sin
cambiar nada: lo usan `lab.py fixture-podar` antes de escribir y la prueba que recorre
tests/fixtures/telefono/. Un fixture nunca se edita a mano: se vuelve a volcar.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from labkit import textos

ESTRUCTURALES = frozenset({"index", "resource-id", "class", "package", "checkable", "checked", "clickable",
                           "enabled", "focusable", "focused", "scrollable", "long-clickable", "password",
                           "selected", "bounds", "drawing-order", "display-id", "visible-to-user",
                           "important-for-accessibility"})
SIEMPRE_AJENOS = ("com.android.systemui",)
CABECERA = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"


def _raiz(xml: str) -> ET.Element:
    return ET.fromstring(xml.lstrip().encode("utf-8"))


def podar(xml: str, app: str) -> str:
    paquete = textos.PAQUETES[app]
    raiz = _raiz(xml)

    def limpiar(padre: ET.Element) -> None:
        for hijo in list(padre):
            if hijo.tag == "node":
                if hijo.get("package") != paquete:
                    padre.remove(hijo)
                    continue
                for atributo, valor in list(hijo.attrib.items()):
                    if atributo not in ESTRUCTURALES and valor and not textos.permitido(valor, app):
                        hijo.set(atributo, "")
            limpiar(hijo)

    limpiar(raiz)
    return CABECERA + ET.tostring(raiz, encoding="unicode")


def revisar(xml: str, app: str) -> list[str]:
    paquete = textos.PAQUETES[app]
    problemas = []
    for el in _raiz(xml).iter("node"):
        pkg = el.get("package", "")
        if pkg in SIEMPRE_AJENOS or pkg != paquete:
            problemas.append(f"nodo de {pkg or 'sin paquete'} en un fixture de {app} ({el.get('bounds')})")
            continue
        for atributo, valor in el.attrib.items():
            if atributo not in ESTRUCTURALES and valor and not textos.permitido(valor, app):
                problemas.append(f"{atributo}={valor[:40]!r} no está en textos.py ({el.get('bounds')})")
    return problemas
```

- [x] **Step 4: Implementar `sonda` y `fixture-podar` en `lab.py`**

Sustituir `_evidencia` por:

```python
def _evidencia(run_id: str) -> Path:
    """Carpeta de evidencia de un run. Las sondas de la fase 2 (`SONDA-F2-…`) van a `sondas-f2/`, que está en
    .gitignore: sus capturas y volcados pueden tener contenido ajeno."""
    if run_id.startswith("SONDA-F2-"):
        return EVIDENCIA / "sondas-f2" / run_id
    return EVIDENCIA / run_id
```

y añadir tras `cmd_telefono_descartar`:

```python
def cmd_sonda(a) -> int:
    """Solo sesiones supervisadas: vuelca, toca un nodo único o pulsa «atrás». Nunca un control de envío."""
    from labkit import pantalla, pasos, reloj, telefono
    _exigir(a.supervisada, "sonda solo con --supervisada: sesión con el usuario presente")
    _exigir(a.run.startswith("SONDA-F2-"), "el --run de una sonda empieza por SONDA-F2-")
    criterios = {k: v for k, v in (("texto", a.texto), ("desc", a.desc), ("resource_id", a.resource_id)) if v}
    if a.accion == "tocar":
        _exigir(len(criterios) == 1, "tocar exige uno de --texto, --desc o --resource-id")
        valor = next(iter(criterios.values()))
        _exigir(not textos.es_texto_envio(valor) and valor not in textos.NO_TOCAR,
                f"la sonda no pulsa controles de envío ni prohibidos: {valor!r}")
    else:
        _exigir(not criterios, f"{a.accion} no admite --texto, --desc ni --resource-id")
    paquete = textos.PAQUETES[a.app]
    ev = _evidencia(a.run)

    def volcar(nombre: str) -> dict:
        xml = pasos.volcado_fresco()
        ev.mkdir(parents=True, exist_ok=True)
        (ev / f"{nombre}.xml").write_text(xml, encoding="utf-8")
        return {"volcado": str(ev / f"{nombre}.xml"), "captura": str(telefono.captura(ev / f"{nombre}.png"))}

    def paso() -> dict:
        pasos.exigir_listo()
        if a.accion == "volcar":
            return volcar(a.nombre)
        if a.accion == "lanzar":
            telefono.lanzar(paquete)
            reloj.dormir(4)
            return volcar(a.nombre)
        if a.accion == "atras":
            return {"captura": str(pasos.atras(paquete, ev, a.nombre))}
        n = pantalla.nodo_sonda(pasos.volcado_fresco(), paquete, **criterios)
        telefono.tocar(*n["centro"])
        reloj.dormir(2)
        return {"tocado": {k: n[k] for k in ("texto", "desc", "resource_id", "bounds")}, **volcar(a.nombre)}

    return _paso_telefono(ev, f"{a.nombre}-inesperada", paso)


def cmd_fixture_podar(a) -> int:
    from labkit import fixtures
    origen = _relativa_sin_salidas(a.desde, "experiments/media-lab/evidence/android/", "--desde")
    _exigir(bool(_NOMBRE.fullmatch(a.pantalla)) and ".." not in a.pantalla,
            f"--pantalla solo admite letras, dígitos, punto, guion y guion bajo: {a.pantalla!r}")
    podado = fixtures.podar(origen.read_text(encoding="utf-8"), a.app)
    problemas = fixtures.revisar(podado, a.app)
    if problemas:
        return _rechazo("FixtureNoPodado", problemas)
    destino = ROOT / "tests" / "fixtures" / "telefono" / a.app / f"{a.pantalla}.xml"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(podado, encoding="utf-8")
    emitir({"fixture": destino.relative_to(ROOT).as_posix()})
    return 0
```

y en `construir`, tras `telefono-descartar`:

```python
    p = sub.add_parser("sonda")
    p.add_argument("app", choices=textos.APPS_TELEFONO + ("edits",))
    p.add_argument("accion", choices=("volcar", "lanzar", "tocar", "atras"))
    p.add_argument("--run", required=True)
    p.add_argument("--nombre", required=True)
    p.add_argument("--supervisada", action="store_true")
    grupo = p.add_mutually_exclusive_group()
    grupo.add_argument("--texto")
    grupo.add_argument("--desc")
    grupo.add_argument("--resource-id")
    p.set_defaults(func=cmd_sonda)
    p = sub.add_parser("fixture-podar")
    p.add_argument("--app", choices=textos.APPS_TELEFONO, required=True)
    p.add_argument("--desde", required=True, help="volcado crudo bajo experiments/media-lab/evidence/android/")
    p.add_argument("--pantalla", required=True, help="nombre del fixture, sin .xml")
    p.set_defaults(func=cmd_fixture_podar)
```

- [x] **Step 5: Comprobar que los volcados crudos de las sondas quedan ignorados**

Run: `git check-ignore -v experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-X/a.xml`
Expected: una línea con la regla del `.gitignore` vigente que ya ignora `evidence/android/*`. No se añade ninguna regla; si no sale nada, parar y averiguar por qué antes de seguir.

- [x] **Step 6: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 17 en `✓` (el recorrido de fixtures no encuentra ninguno todavía) y `El laboratorio cumple sus contratos.`

- [x] **Step 7: Commit**

```bash
git add experiments/media-lab/labkit/fixtures.py experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: sonda supervisada que no pulsa envíos y fixtures podados por lab.py

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `preflight` con versiones y el LaunchAgent retirado (refactor R, parte 7)

**Files:**
- Modify: `experiments/media-lab/labkit/telefono.py`, `experiments/media-lab/lab.py`, `experiments/media-lab/progress.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_preflight_fase2,`:

```python
def seccion_preflight_fase2() -> None:
    print("\n18. Fase 2: preflight con versiones de las apps y el LaunchAgent")
    from labkit import telefono as T, textos as TX

    salida = "Packages:\n  versionName=446.0.0.49.77\n  User 0: installed=true\n  versionName=446.0.0.49.77\n"
    check(T.version_desde_dumpsys(salida) == "446.0.0.49.77", "versión única de dumpsys package")
    check(T.version_desde_dumpsys("versionName=445.0.0.45.83\nversionName=446.0.0.49.77")
          == "445.0.0.45.83 | 446.0.0.49.77", "dos versiones distintas (perfil de trabajo) salen las dos")
    check(T.version_desde_dumpsys("Unable to find package") is None, "sin versionName no hay versión")

    llamadas: list[str] = []

    def prohibido(nombre):
        def f(*args, **kwargs):
            llamadas.append(nombre)
            raise IntentoDeES(nombre)
        return f

    with entorno_lab_fase2() as (lab, raiz):
        modulo = lab.lab
        viejos = {"estado": T.estado, "versiones": getattr(T, "versiones", None), "lanzar": T.lanzar, "tocar": T.tocar,
                  "workflows": modulo.colision.workflows_en_curso,
                  "agente": getattr(modulo, "_agente_despierto", None)}
        try:
            T.lanzar, T.tocar = prohibido("lanzar"), prohibido("tocar")
            T.estado = lambda: {"adb": True, "despierto": False, "bloqueado": True, "listo": False}
            T.versiones = lambda paquetes: llamadas.append("versiones") or {app: "1.0" for app in paquetes}
            modulo.colision.workflows_en_curso = lambda: []
            modulo._agente_despierto = lambda: True
            codigo, datos, _ = lab("preflight")
            versiones = campo(datos, "versiones") or {}
            check(codigo == 0 and set(versiones) == set(TX.PAQUETES) and versiones.get("threads") == "1.0"
                  and campo(datos, "agente_phone_awake") is True and llamadas == ["versiones"],
                  f"preflight informa versiones y LaunchAgent sin abrir apps ({codigo}, {datos}, {llamadas})")
            llamadas.clear()
            T.estado = lambda: {"adb": False, "despierto": False, "bloqueado": None, "listo": False}
            codigo, datos, _ = lab("preflight")
            check(codigo == 0 and campo(datos, "versiones") == {} and llamadas == [],
                  f"sin adb no se piden versiones ({codigo}, {llamadas})")
        finally:
            T.estado, T.lanzar, T.tocar = viejos["estado"], viejos["lanzar"], viejos["tocar"]
            if viejos["versiones"] is not None:
                T.versiones = viejos["versiones"]
            modulo.colision.workflows_en_curso = viejos["workflows"]
            if viejos["agente"] is not None:
                modulo._agente_despierto = viejos["agente"]
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.telefono' has no attribute 'version_desde_dumpsys'` en la sección 18.

- [ ] **Step 3: Implementar en `telefono.py`**

Añadir tras `_SHA256 = re.compile(r"[0-9a-f]{64}")`:

```python
_VERSION = re.compile(r"versionName=(\S+)")
```

en la parte pura, tras `sha256_de_salida`:

```python
def version_desde_dumpsys(salida: str) -> str | None:
    """versionName de `dumpsys package`. Si hay varias distintas (p. ej. un perfil de trabajo de
    MaaS360), todas en orden separadas por « | »; None si no aparece."""
    vistas = list(dict.fromkeys(_VERSION.findall(salida)))
    return " | ".join(vistas) if vistas else None
```

y en la parte de E/S, tras `teclado_visible`:

```python
def versiones(paquetes: dict[str, str]) -> dict[str, str | None]:
    """Versión instalada de cada app (clave → paquete). Solo lee `dumpsys package`: no abre ninguna app."""
    fuera: dict[str, str | None] = {}
    for app, paquete in paquetes.items():
        try:
            fuera[app] = version_desde_dumpsys(shell(f"dumpsys package {paquete}", timeout=30))
        except TelefonoError:
            fuera[app] = None
    return fuera
```

- [ ] **Step 4: Implementar en `lab.py`**

Añadir tras `LOCK = LAB / ".ventana.lock"`:

```python
AGENTE_DESPIERTO = "com.sabiduria.medialab.phone-awake"
```

añadir antes de `cmd_preflight`:

```python
def _agente_despierto() -> bool | None:
    """¿Sigue cargado el LaunchAgent que mantenía despierto el teléfono? La fase 2 lo retira: la
    automatización nunca despierta el teléfono. Solo lee launchctl; lo descarga el usuario."""
    try:
        r = subprocess.run(["launchctl", "list", AGENTE_DESPIERTO], capture_output=True, text=True,
                           timeout=10, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.returncode == 0
```

y sustituir `cmd_preflight` completa por:

```python
def cmd_preflight(a) -> int:
    from labkit import telefono
    t = ahora()
    try:
        tel = telefono.estado()
    except Exception as e:  # noqa: BLE001 — preflight informa, nunca rompe
        tel = {"listo": False, "error": f"{type(e).__name__}: {e}"}
    versiones: dict = {}
    if tel.get("adb"):
        try:
            versiones = telefono.versiones(textos.PAQUETES)
        except Exception as e:  # noqa: BLE001
            versiones = {"error": f"{type(e).__name__}: {e}"}
    try:
        en_curso = colision.workflows_en_curso()
        espera = colision.motivo_espera(
            t, programadas=colision.programadas_de_cola(ROOT / "content" / "queue"),
            publicadas=colision.publicadas_recientes(ROOT / "content" / "published", t),
            en_curso=en_curso)
        github = True
    except Exception as e:  # noqa: BLE001
        github, espera = False, f"GitHub no responde ({type(e).__name__}): sin datos de producción cercana"
    emitir({"ahora": t.isoformat(timespec="seconds"), "telefono": tel, "versiones": versiones,
            "agente_phone_awake": _agente_despierto(), "github": github, "espera": espera})
    return 0
```

- [ ] **Step 5: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 18 en `✓` y `El laboratorio cumple sus contratos.`

- [ ] **Step 6: Retirar el LaunchAgent y fijar las versiones**

> **Controlador con el usuario presente (no subagente).**

Mensaje al usuario (es configuración persistente de su Mac y la descarga él): «Para aplicar la decisión 1 de la fase 2, descarga el LaunchAgent que mantenía despierto el teléfono: `launchctl bootout gui/$(id -u)/com.sabiduria.medialab.phone-awake`. La automatización ya no lo necesita: si el teléfono no está listo, salta las celdas de teléfono». Esperar su confirmación.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python experiments/media-lab/lab.py preflight`
(desde el worktree) Expected: `"agente_phone_awake": false` y `versiones` con las cuatro apps (con el teléfono conectado).

En `experiments/media-lab/progress.md`, en la viñeta que empieza por «MaaS360/Knox enforces», sustituir la frase «LaunchAgent `com.sabiduria.medialab.phone-awake` sends a neutral ADB activity event every 45 seconds while this exact serial is connected;» por:

```markdown
The LaunchAgent `com.sabiduria.medialab.phone-awake` was retired in phase 2 (2026-09-14): automation never wakes or unlocks the phone, `lab.py preflight` reports `agente_phone_awake`, and phone cells are skipped when the phone is not ready;
```

y en la viñeta que empieza por «The original Samsung SM-S918B has been replaced», sustituir la frase «Facebook 576.0.0.42.73, Instagram 445.0.0.45.83, Threads 446.0.0.32.78 and Edits 446.2.0.51.77 are installed.» por la frase siguiente, con los cuatro valores que devolvió el `preflight` de este paso:

```markdown
Installed versions come from `lab.py preflight` (`versiones`); on 2026-09-14 it reported Facebook <versiones.facebook>, Instagram <versiones.instagram>, Threads <versiones.threads> and Edits <versiones.edits> (earlier notes disagreed: 445.0.0.45.83 here and 446.0.0.49.77 in the runs).
```

- [ ] **Step 7: Commit y push**

```bash
git add experiments/media-lab/labkit/telefono.py experiments/media-lab/lab.py experiments/media-lab/progress.md tests/test_media_lab.py
git commit -m "media lab claude: preflight con versiones de las apps y el LaunchAgent phone-awake retirado

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

---

### Task 8: Prompt de la ventana con recetas (spec, fila 2)

Solo lo que ya existe tras el refactor: receta, pasos 7b y 7e, borradores y borrador abierto. Cada flujo añade su parte en el paso de prompt de su subtarea (11c, 12c, 13, 14c, 15c, 16d y 17d).

**Files:**
- Modify: `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_prompt_ventana,`:

```python
def seccion_prompt_ventana() -> None:
    print("\n19. Fase 2: el prompt de la ventana usa las recetas")
    texto = (ROOT / "experiments" / "media-lab" / "claude-ventana-prompt.md").read_text(encoding="utf-8")
    for fragmento in ("lab.py receta --celda", "`preparar`", "`publicar`", "`verificar`", "`conciliacion`",
                      "`copias`", "`estados_ok`", "telefono-descartar", "BorradorPendiente", "--borrador",
                      "location_not_automated_phase2", "missing_data_reasons.post_url", "lab.py turno",
                      "entre 4 h y 20 h", "máximo 10 en cola", "turno --marcar",
                      "lab.py render"):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
    check("TELEFONO_FASE_1" not in texto and "ig abrir --run RUN" not in texto,
          "el prompt ya no lleva la secuencia fija del feed de Instagram")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con las comprobaciones de la sección 19 (`lab.py receta --celda`, `preparar`… y «ya no lleva la secuencia fija»).

- [ ] **Step 3: Escribir el prompt**

El texto de abajo es el prompt de `d8ac308` (tarea 15 de la fase 1: paso 0 `lab.py turno`, `turno --marcar` tras el cerrojo, cola de 10, `lab.py render`/`lab.py tarjeta` en 7a y métricas sin bloquear) con solo los cambios de la fase 2: especificación de la fase 2, recetas en 7b–7g, borrador abierto, una celda de teléfono, ubicación, versiones, noches, `formato_encargo`, nota de Codex, medición de Stories e informe. Antes, revisar `git log -p d8ac308.. -- experiments/media-lab/claude-ventana-prompt.md` e incorporar cualquier cambio posterior de la fase 1 que no esté. Después, sustituir `experiments/media-lab/claude-ventana-prompt.md` completo por:

```markdown
Trabaja en el repo /Users/hec/dev/sabiduriaPublisher. Eres la ventana de publicación del laboratorio Sabiduría de Bolsillo. El diseño completo está en docs/superpowers/specs/2026-09-14-media-lab-chatgpt-claude-design.md y, para los flujos de teléfono de la fase 2, en docs/superpowers/specs/2026-09-14-media-lab-fase2-design.md: léelos si dudas.

## Reglas que no se rompen
- Códigos de salida de `lab.py`: 0 correcto; 1 fallo del paso; 2 argumentos o datos inválidos (JSON con `error`); 3 cerrojo no soltado; 4 pantalla inesperada o error del teléfono; 5 envío dudoso; 6 Codex cambió archivos no permitidos. Ante 2, corrige la llamada; ante 4 o 5, no toques más el teléfono en la ventana salvo para salir de un borrador abierto (regla de abajo).
- Solo usa estos comandos: `.venv/bin/python experiments/media-lab/lab.py …`, `.venv/bin/python tests/test_media_lab.py`, `gh run list …`, `gh run view …`, `gh run watch …`, `gh run download …`, `gh workflow run media-lab…`, `git add experiments/media-lab/…`, `git commit …`, `git fetch origin main`, `git rebase origin/main`, `git rebase --abort`, `git push origin HEAD:main`. Cualquier otro comando abre un permiso que nadie contesta y te deja colgada. Para leer archivos y capturas usa Read; para editar JSON, Edit o Write.
- Nunca publiques sin PASS explícito de un agente independiente sobre la captura final (experiments/media-lab/visual-qa-gate.md).
- `lab.py preflight` devuelve en `espera` la producción cercana. Es solo informativo: no esperes ni saltes celdas por ello (decisión del usuario, 2026-09-14). Cópialo en `exposure_context.nearby_production_posts` del run y repítelo justo antes de cada Compartir o workflow para registrarlo.
- Nunca pulses nada a ciegas: tras cada paso de teléfono de `lab.py` abre la captura con Read y confirma que muestra lo que dice el campo `ver` de su receta.
- Nunca reintentes un envío dudoso por la otra ruta; concilia contra la plataforma primero, como dice `conciliacion` en la receta.
- Como máximo una celda de teléfono por ventana (`seleccionar` ya lo aplica). Nunca uses `--borrador`: es solo para las ventanas manuales de primera publicación que dirige el usuario.
- Borrador abierto: si un paso de teléfono sale con 4 a mitad de flujo y la captura muestra un compositor o editor a medias, intenta salir con `lab.py telefono-atras --app <red> --run RUN --nombre salida-N`, mirando cada captura, y solo cuando la captura muestre el diálogo de descarte de un borrador, `lab.py telefono-descartar --app <red> --run RUN --nombre descarte` (se niega ante un diálogo de borrado). Si no puedes, déjalo escrito en el informe: la siguiente ventana lo encontrará como `BorradorPendiente` y no lo tocará.
- Ubicación nativa: solo un lugar público real citado en el brief (museo, monumento, ciudad), nunca la ubicación del teléfono ni sugerencias «cerca de ti». La fase 2 no automatiza el sticker de ubicación: la celda sale con la etiqueta visible impresa en el máster y `location_not_automated_phase2` en `missing_data_reasons` del run.
- A partir del 2026-10-02 no publiques: resume y pide al usuario que desactive esta tarea.

## Pasos
0. `lab.py turno`. Si no sale con 0 o `toca` es false, termina en silencio (si salió con 2, una sola línea de informe con el error; no edites `turnos.json` ni `.turno-hecho`).
1. `lab.py lock-tomar --dueno programada`; si `cerrojo` es false, termina sin marcar el turno. Luego `lab.py turno --marcar`; si no sale con 0 o no confirma el marcado, suelta el cerrojo (`lab.py lock-soltar --dueno programada`) y termina.
2. `git fetch origin main` y `git rebase origin/main`. Si falla: `git rebase --abort`, `lab.py lock-soltar --dueno programada` y termina informando.
3. `lab.py preflight`. Anota teléfono, versiones, github y espera. Si `telefono.listo` es false (bloqueado, dormido o desconectado), no toques el teléfono en toda la ventana: no intentes despertarlo ni desbloquearlo, salta las celdas `android_native`, sigue con las de API y di en el informe que el teléfono no estaba disponible para que el usuario lo desbloquee. Las ventanas de noche suelen encontrarlo bloqueado: es lo esperado, publican solo por API y en `exposure_context` de cada run de esa ventana anotas que la franja no permitió teléfono (factor de confusión).
4. `lab.py encargos`. Si algún encargo está en `bloqueado` y no figura aún en experiments/media-lab/progress.md, anótalo allí (id, celdas, motivo del último intento) e inclúyelo en el informe: nadie más lo va a ver. Revisa cada encargo `generado`: abre sus imágenes con Read. Apruébalo (`lab.py encargo-revisar --encargo ID --aprobado --motivo "…"`) solo si la imagen es verosímil, respeta el brief y do_not_use y no tiene texto. Si no: `--rechazado --motivo "…" --correccion "…"`.
5. Reposición: crea encargos con `lab.py encargo-nuevo` (la carpeta de destino sale sola de `--family`: experiments/media-lab/assets/<family_id>) para las próximas celdas `planned` de experiments/media-lab/coverage.json con brief verificado cuya red y formato estén implementados —de teléfono, si `lab.py receta --celda <id>` sale con 0; de API, si están en `API_FASE_1` de experiments/media-lab/labkit/seleccion.py—, sin mezclar en un mismo encargo celdas de feed (4:5) y de story (9:16), hasta como máximo 10 en cola (`encargos.MAX_EN_COLA`, pensado para hasta 10 celdas al día). En `--formato` usa el `formato_encargo` de la receta. La automatización de Codex genera como mucho 2 encargos por pasada y no va al ritmo de las ventanas: si la cola no baja, usa el rescate de abajo. El prompt de imagen va en un archivo temporal dentro de experiments/media-lab/results/. Si `lab.py seleccionar` devuelve [] y hay algún encargo en `pedido`, `lab.py generar --encargo <el más antiguo>` una sola vez, lanzándolo con el tiempo máximo de la herramienta Bash (`timeout: 600000`) y sin ejecutar la batería de pruebas mientras corre (escribe en el repo y la guardia lo tomaría por cambios ajenos); si genera, revísalo como en el paso 4. Si sale con código 6 (Codex cambió archivos no permitidos), no generes más en esta ventana, no comitees esos cambios y enumera los archivos en el informe para el usuario.
6. `lab.py seleccionar --max 2`, añadiendo `--sin-telefono` si `telefono.listo` era false. Si devuelve [], salta al paso 8.
7. Para cada celda elegida, en orden, dejando al menos 21 min entre la primera publicación y la segunda (vuelve a pasar `lab.py preflight`). Antes de cada celda renueva el cerrojo con `lab.py lock-tomar --dueno programada`; si devuelve `cerrojo: false`, otra sesión tomó el relevo: no publiques más celdas y salta al paso 9:
   a. Crea el máster final con texto determinista: `lab.py render --encargo ID --variante 1 --formato feed|story --titular "L1|L2|L3" --subtitulo "…" [--aviso "…"] --salida <nombre>` con el titular, subtítulo y aviso de la sección Overlay del brief (en Stories usa el formato `story` del encargo, 9:16), o `lab.py tarjeta …` para tarjetas de cita; nunca reutilices el máster de otro encargo. Añade el pie (verificado contra el brief, ≤2200 en Instagram, ≤500 en Threads) y el run JSON copiando experiments/media-lab/run-template.json.
   b. Teléfono: `lab.py receta --celda <id>` y ejecuta, en orden, los comandos de `preparar`, sustituyendo `<run>` por RUN, `<master>` por el máster, `<pie>` por el archivo del pie y cada otro `<valor>` por lo que devolvió el comando que lo anota (`anota`). Tras cada uno abre la captura y comprueba lo que dice `ver`. Si un paso sale con código 4 (`PantallaInesperada`, `BorradorPendiente`, `TelefonoNoListo` o `TelefonoError`), no toques más el teléfono en esta ventana salvo la regla del borrador abierto: regístralo con su captura y sigue con API.
      API: `lab.py manifiesto-api --run-group LAB-…-API --asset <máster> --caption facebook=<archivo> …`; commit y push del máster y el manifiesto (sección C de la spec) para que asset_url exista; la vista previa para QA es el máster con el pie.
   c. QA: lanza un agente independiente con la última captura de `preparar`, el máster, el pie y visual-qa-gate.md, y exige «VERDICT: PASS»; el revisor solo comprueba que no haya texto ni imagen cortados o tapados. Si FAIL, corrige una vez y repite. Si vuelve a FAIL, abandona la celda (en teléfono, regla del borrador abierto) y regístralo: pon la celda en `"status": "blocked"` con `reason_if_blocked_or_unsupported` en coverage.json para que la siguiente ventana no la vuelva a elegir.
   d. `lab.py preflight` y anota `espera` (producción cercana) y `versiones` en el run. No frena la publicación.
   e. Publica. Teléfono: ejecuta los comandos de `publicar` de la receta; lo que va entre corchetes (p. ej. `[--produccion-cercana]`) se añade solo cuando se cumple lo que dice su `ver`. Sale con 0 solo con un estado de `estados_ok`. Con 4 antes de pulsar es un bloqueo esperado: no reintentes en esta ventana. Con 5 el envío es dudoso: no repitas nada y concilia como dice `conciliacion` de la receta antes de registrar. API: `gh workflow run media-lab -f manifest=<ruta>`, sigue el run con `gh run watch`, descarga el resultado con `gh run download`. Con los post_id del resultado: `lab.py manifiesto-verificacion --run-group <el mismo> --post facebook=<id> …` (solo feed: si la celda es solo de historias, sáltate este paso de verificación), commit y push de ese manifiesto, y `gh workflow run media-lab-verify -f manifest=<ruta>`.
   f. Verifica: ejecuta los comandos de `verificar` de la receta y sigue su `verificacion` (identidad, audiencia, música). Si con los comandos permitidos no puedes obtener la URL de una publicación por teléfono, no la inventes: déjala en `missing_data_reasons.post_url` del run y sigue. Cada entrada de `copias` va en `publication.cross_posting` del run como publicación extra, no como celda.
   g. Actualiza el run (en teléfono, también `publication.native_app_and_version` con la versión del último preflight), la celda de coverage.json, `lab.py encargo-usado --encargo ID --run RUN` y experiments/media-lab/progress.md.
8. Métricas: captura las instantáneas vencidas (24 h, 72 h, 7 d; cada Story en la primera ventana en que tenga entre 4 h y 20 h o, si no hubo ninguna, en la última antes de que caduque a las 24 h) de los runs publicados y guárdalas en sus runs. Si no hay un comando permitido que lea las métricas, no bloquees: anota en `missing_data_reasons.audience_metrics` del run qué instantánea venció y sigue.
9. Commit solo de rutas propias: `git add experiments/media-lab/<rutas concretas>`, `git commit -m "media lab claude: …"`, `git fetch origin main`, `git rebase origin/main` y `git push origin HEAD:main`. Si hay conflicto: `git rebase --abort` e informa.
10. `lab.py lock-soltar --dueno programada`.

## Informe
Si no publicaste nada y no hubo fallo, basta con una línea con el motivo (por ejemplo, ningún encargo aprobado). Si publicaste, da celda, red, ruta, URL y veredicto de QA. Si algo bloqueó, di qué y qué decisión hace falta del usuario. Un borrador que no pudiste cerrar va al principio.
```

- [ ] **Step 4: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 19 en `✓` y `El laboratorio cumple sus contratos.`

- [ ] **Step 5: Comprobar la cola de 10 de la tarea 15**

La tarea 15 de la fase 1 ya dejó `MAX_EN_COLA = 10` en `experiments/media-lab/labkit/encargos.py` y la prueba de la cola con 10; esta tarea no cambia ninguno de los dos.

Run: `grep -n "MAX_EN_COLA = 10" experiments/media-lab/labkit/encargos.py`
Expected: una línea con `MAX_EN_COLA = 10`. Si no sale, la tarea 15 no está integrada: parar y avisar.

- [ ] **Step 6: Commit y push**

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana sigue las recetas del teléfono y mide las Stories por turnos

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 7: Actualizar la tarea programada (tras el push)**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro del nuevo `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno», «turno --marcar» y «lab.py receta --celda».

---

### Task 9: Sonda S1 y fixtures podados (spec, fila 3)

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

Supervisada, con el usuario presente (solo él desbloquea el teléfono) y **sin publicar**: la sonda se niega a pulsar cualquier texto de `textos.ENVIO` o `textos.ENVIO_HISTORIA` («Vos stories», «Votre story», «Tu historia»…) o que empiece por `textos.PREFIJOS_ENVIO` y no esté en `textos.NO_ENVIO`; si se niega ante un control que en pantalla no publica («Partager à»…), se anota en la tabla del Step 7 para confirmar `NO_ENVIO`. Cada `lab.py sonda … tocar` usa el texto, la descripción o el resource-id que se lee en el volcado anterior (`experiments/media-lab/evidence/android/sondas-f2/<run>/<nombre>.xml`) y en su captura; tras cada comando se abre la captura con Read antes del siguiente. Si un texto esperado no aparece, se usa el que muestre el volcado y se anota en la tabla del Step 7.

**Files:**
- Create: `tests/fixtures/telefono/{instagram,threads,facebook}/*.xml` (con `lab.py fixture-podar`)
- Modify: `experiments/media-lab/findings.md`
- Local, no se comitea: `experiments/media-lab/evidence/android/sondas-f2/`

- [ ] **Step 1: Comprobación previa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python experiments/media-lab/lab.py preflight`
Expected: `telefono.listo: true`, `versiones` con las cuatro apps y `agente_phone_awake: false`. Si el teléfono no está listo, pedir al usuario que lo desbloquee y repetir.

- [ ] **Step 2: Una imagen 9:16 en la galería**

Run: `git ls-files 'experiments/media-lab/assets/*story*'` y elegir un máster 9:16 ya comiteado.
Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python experiments/media-lab/lab.py telefono-subir --local <ese máster>`
Expected: JSON con `subido_en`. La miniatura de hoy es la que se toca en los selectores.

- [ ] **Step 3: Instagram (FR), run `SONDA-F2-S1-IG`**

En todos los comandos, `L=".venv/bin/python experiments/media-lab/lab.py"` y `S="--run SONDA-F2-S1-IG --supervisada"`:

```bash
$L sonda instagram lanzar $S --nombre ig-01-inicio
$L sonda instagram tocar $S --nombre ig-02-perfil --desc Profil
$L sonda instagram tocar $S --nombre ig-03-crear-menu --desc Créer
$L sonda instagram tocar $S --nombre ig-04-historia-selector --texto Story
$L sonda instagram tocar $S --nombre ig-05-historia-editor --desc "<content-desc de la miniatura de hoy en ig-04>"
$L sonda instagram volcar $S --nombre ig-06-historia-editor-audio
$L sonda instagram tocar $S --nombre ig-07-historia-stickers --desc "<botón de autocollants en ig-06>"
$L sonda instagram atras $S --nombre ig-07b-sin-stickers
# ig-08: la sonda no toca nada (ver el párrafo de abajo); si el usuario llevó el editor al destino:
$L sonda instagram volcar $S --nombre ig-08-historia-destino
$L sonda instagram atras $S --nombre ig-08b-atras
$L sonda instagram atras $S --nombre ig-09-descartar-dialogo
$L telefono-descartar --app instagram --run SONDA-F2-S1-IG --nombre ig-09b-descartado
```

Para `ig-08` nadie toca con la sonda un control que pueda publicar: si `ig-07b` muestra hacia el destino un control distinto de «Vos stories», «Amis proches», «Envoyer à» y sus equivalentes en inglés (p. ej. la flecha «Partager à»), el usuario, presente, lo pulsa a mano tras mirar la captura y Claude vuelca con `sonda instagram volcar`; si no está claro, `ig-08` se omite, las pruebas de la tarea 11a usan `xml_destino_historia()` y el volcado real se hace en la ventana manual de la tarea 11d.

En `ig-06` debe verse el chip «Audio suggéré»; si no viene añadido, se anota. En `ig-07` debe verse «Sondage» (o su equivalente) y «Musique». En `ig-08`, «Vos stories», «Amis proches» y el conmutador de Facebook con su estado por defecto. Si `atras` no lleva al diálogo de descarte en dos pasos, se sigue con `atras` mirando capturas hasta verlo.

Luego, el visor de la story propia y el selector múltiple del feed:

```bash
$L sonda instagram tocar $S --nombre ig-10-perfil --desc Profil
# ig-11: el usuario abre a mano la story propia desde el avatar (la sonda rechaza «Votre story») y:
$L sonda instagram volcar $S --nombre ig-11-historia-visor-propio
$L sonda instagram atras $S --nombre ig-11b-atras
$L sonda instagram tocar $S --nombre ig-12-crear-menu --desc Créer
$L sonda instagram tocar $S --nombre ig-13-feed-selector --texto Publication
$L sonda instagram tocar $S --nombre ig-14-feed-selector-multiple --desc "<botón de selección múltiple en ig-13>"
$L sonda instagram tocar $S --nombre ig-15-feed-dos-seleccionadas --desc "<segunda miniatura de ig-14>"
$L sonda instagram atras $S --nombre ig-16-atras
```

`ig-11` solo existe si hay una story propia viva; si no la hay, se salta y se anota (la ventana manual de la tarea 11 la vuelca). Salir con `atras` y, si aparece el diálogo, `telefono-descartar --app instagram`.

- [ ] **Step 4: Threads (FR), run `SONDA-F2-S1-TH`**

Con `S="--run SONDA-F2-S1-TH --supervisada"` y `ID=com.instagram.barcelona:id`:

```bash
$L sonda threads lanzar $S --nombre th-01-inicio
$L sonda threads tocar $S --nombre th-02-perfil --resource-id $ID/barcelona_tab_profile
$L sonda threads tocar $S --nombre th-03-compositor-vacio --resource-id $ID/barcelona_tab_create
$L sonda threads tocar $S --nombre th-04-galeria --resource-id $ID/new_thread_screen_gallery_button
$L sonda threads tocar $S --nombre th-05-galeria-multiple --desc "<segunda miniatura o conmutador de selección múltiple en th-04>"
$L sonda threads atras $S --nombre th-05b-atras
$L sonda threads tocar $S --nombre th-06-musica --resource-id $ID/new_thread_screen_music_button
$L sonda threads atras $S --nombre th-06b-atras
$L sonda threads tocar $S --nombre th-07-adjuntos --desc "<botón de más adjuntos en th-06b>"
$L sonda threads tocar $S --nombre th-08-encuesta --resource-id $ID/new_thread_screen_poll_button
$L sonda threads atras $S --nombre th-08b-atras
$L sonda threads tocar $S --nombre th-09-opciones --desc "<opciones de publicación en th-08b>"
$L sonda threads atras $S --nombre th-09b-atras
$L sonda threads atras $S --nombre th-10-descartar-dialogo
# th-10b: Threads no tiene descarte automático hasta S1 (textos.DESCARTE vacío): el usuario descarta a mano
# tras comprobar en la captura th-10 que el diálogo es de descarte de un borrador y no de borrado.
```

En `th-03` debe verse el botón de identidad `sabiduriabolsillo`; en `th-09`, cualquier conmutador «Partager aussi sur Instagram» y su estado por defecto. `th-02` debe mostrar el primer thread del perfil con su edad.

- [ ] **Step 5: Facebook (ES), run `SONDA-F2-S1-FB`**

Con `S="--run SONDA-F2-S1-FB --supervisada"`:

```bash
$L sonda facebook lanzar $S --nombre fb-01-inicio
```

Si `fb-01` muestra un interstitial, `$L sonda facebook volcar $S --nombre fb-01b-interstitial` y después `$L sonda facebook tocar $S --nombre fb-01c-inicio --texto "Ahora no"`; nunca «Anular» (la sonda lo rechaza). En `fb-01` debe verse que la Página «Sabiduria De Bolsillo» es el perfil activo; si no, parar y avisar al usuario.

```bash
$L sonda facebook tocar $S --nombre fb-02-compositor-pagina --texto "¿Qué estás pensando?"
$L sonda facebook tocar $S --nombre fb-03-galeria --texto "<botón de galería en fb-02>"
$L sonda facebook tocar $S --nombre fb-04-galeria-multiple --desc "<conmutador de selección múltiple en fb-03>"
$L sonda facebook atras $S --nombre fb-04b-atras
$L sonda facebook tocar $S --nombre fb-05-compositor-con-imagen --desc "<miniatura de hoy en fb-03>"
$L sonda facebook tocar $S --nombre fb-06-musica --texto Música
$L sonda facebook atras $S --nombre fb-06b-atras
$L sonda facebook tocar $S --nombre fb-07-pantalla-final --texto Siguiente
$L sonda facebook atras $S --nombre fb-07b-atras
$L sonda facebook atras $S --nombre fb-08-descartar-dialogo
$L telefono-descartar --app facebook --run SONDA-F2-S1-FB --nombre fb-08b-descartado
$L sonda facebook tocar $S --nombre fb-09-perfil-pagina --desc "<foto de la Página en fb-08b>"
$L sonda facebook atras $S --nombre fb-09b-atras
$L sonda facebook tocar $S --nombre fb-10-historia-creador --texto "Crear historia"
$L sonda facebook tocar $S --nombre fb-11-historia-editor --desc "<miniatura de hoy en fb-10>"
$L sonda facebook tocar $S --nombre fb-12-historia-stickers --desc "<botón de stickers en fb-11>"
$L sonda facebook atras $S --nombre fb-12b-atras
$L sonda facebook tocar $S --nombre fb-13-historia-opciones --desc "<ajustes o privacidad de la historia en fb-12b>"
$L sonda facebook atras $S --nombre fb-13b-atras
$L sonda facebook atras $S --nombre fb-14-descartar-historia
```

En `fb-02` debe verse la identidad «Sabiduria De Bolsillo» y «Público»; en `fb-07`, la audiencia y el botón final (no se pulsa); en `fb-12`, «Encuesta» y «Música»; en `fb-13`, el conmutador «Compartir en Instagram» y su estado. Salir con `atras` y, si aparece el diálogo, `telefono-descartar --app facebook`. Si se niega porque el título real del diálogo no coincide con `DESCARTE["facebook"]` (o parece de borrado), el usuario descarta a mano tras mirar la captura y el título real se anota en la tabla del Step 7. Si hay una story viva de la Página, el usuario la abre a mano desde el inicio (la sonda rechaza «Tu historia») y Claude vuelca con `sonda facebook volcar $S --nombre fb-15-historia-visor-propio`.

- [ ] **Step 6: Comprobar que no se publicó nada**

```bash
$L telefono-captura --run SONDA-F2-S1-IG --nombre fin-perfil-ig
$L telefono-captura --run SONDA-F2-S1-TH --nombre fin-perfil-th
$L telefono-captura --run SONDA-F2-S1-FB --nombre fin-perfil-fb
```

con cada app abierta en su perfil (Instagram y Threads) o en la Página (Facebook), llevándolas allí con `sonda … tocar`. Las capturas deben mostrar la misma primera publicación que antes de la sonda.

- [ ] **Step 7: Anotar en `findings.md`**

Añadir al final:

```markdown
## Sonda S1 de la fase 2 (<fecha>, sin publicar)

- Versiones (`lab.py preflight`): Instagram <v>, Threads <v>, Facebook <v>, Edits <v>.
- No se publicó nada: capturas `fin-perfil-*` iguales a las del inicio.
- Copias automáticas vistas (conmutador y estado por defecto): Instagram Story → Facebook <sí/no/no aparece>; Threads → Instagram <…>; Facebook Story → Instagram <…>.

| app | clave de textos.py | esperado | observado | fixture |
|---|---|---|---|---|
```

y una fila por cada clave marcada «confirmar contra el fixture de S1» en `textos.py` y en las tareas 11–17: Instagram `story`, `anadir_a_story`, `autocollants`, `musique`, `sondage`, `hacia_destino`, `vos_stories`, `amis_proches`, `partager_sur_facebook`, `compartir_historia`, `aviso_historia`, `votre_story`, `activite`, `seleccion_multiple`; Threads `publicar`, `aviso_publicado`, `anadir`, `sugerencias`, `adjuntos`, `opcion_1`, `opcion_2`, `compartir_en_instagram`, `fils` y el diálogo de descarte; Facebook `foto_video`, `listo`, `publicando`, `no_se_pudo`, `reintentar`, `stickers`, `sugeridas`, `compartir_historia`, `seleccionar_varios`, el diálogo de descarte, el formato de fecha de las miniaturas y el de las edades. Otra fila por cada excepción de `NO_ENVIO` («Partager à», «Partager sur Facebook», «Partager aussi sur Instagram», «Compartir en Instagram»): texto real y si es navegación o conmutador y no publica. Una línea final dice qué pantallas no aparecieron y por qué.

- [ ] **Step 8: Podar los fixtures**

Un comando por fila, con `D=experiments/media-lab/evidence/android/sondas-f2`:

| Volcado | App | Fixture (`--pantalla`) |
|---|---|---|
| `SONDA-F2-S1-IG/ig-01-inicio.xml` | instagram | `inicio` |
| `SONDA-F2-S1-IG/ig-02-perfil.xml` | instagram | `perfil` |
| `SONDA-F2-S1-IG/ig-03-crear-menu.xml` | instagram | `crear-menu` |
| `SONDA-F2-S1-IG/ig-04-historia-selector.xml` | instagram | `historia-selector` |
| `SONDA-F2-S1-IG/ig-05-historia-editor.xml` | instagram | `historia-editor` |
| `SONDA-F2-S1-IG/ig-06-historia-editor-audio.xml` | instagram | `historia-editor-audio` |
| `SONDA-F2-S1-IG/ig-07-historia-stickers.xml` | instagram | `historia-stickers` |
| `SONDA-F2-S1-IG/ig-08-historia-destino.xml` | instagram | `historia-destino` |
| `SONDA-F2-S1-IG/ig-09-descartar-dialogo.xml` | instagram | `descartar-dialogo` |
| `SONDA-F2-S1-IG/ig-11-historia-visor-propio.xml` (si existe) | instagram | `historia-visor-propio` |
| `SONDA-F2-S1-IG/ig-14-feed-selector-multiple.xml` | instagram | `feed-selector-multiple` |
| `SONDA-F2-S1-IG/ig-15-feed-dos-seleccionadas.xml` | instagram | `feed-dos-seleccionadas` |
| `SONDA-F2-S1-TH/th-01-inicio.xml` | threads | `inicio` |
| `SONDA-F2-S1-TH/th-02-perfil.xml` | threads | `perfil` |
| `SONDA-F2-S1-TH/th-03-compositor-vacio.xml` | threads | `compositor-vacio` |
| `SONDA-F2-S1-TH/th-04-galeria.xml` | threads | `galeria` |
| `SONDA-F2-S1-TH/th-05-galeria-multiple.xml` | threads | `galeria-multiple` |
| `SONDA-F2-S1-TH/th-06-musica.xml` | threads | `musica` |
| `SONDA-F2-S1-TH/th-07-adjuntos.xml` | threads | `adjuntos` |
| `SONDA-F2-S1-TH/th-08-encuesta.xml` | threads | `encuesta` |
| `SONDA-F2-S1-TH/th-09-opciones.xml` | threads | `opciones` |
| `SONDA-F2-S1-TH/th-10-descartar-dialogo.xml` | threads | `descartar-dialogo` |
| `SONDA-F2-S1-FB/fb-01-inicio.xml` | facebook | `inicio` |
| `SONDA-F2-S1-FB/fb-01b-interstitial.xml` (si existe) | facebook | `interstitial` |
| `SONDA-F2-S1-FB/fb-02-compositor-pagina.xml` | facebook | `compositor-pagina` |
| `SONDA-F2-S1-FB/fb-03-galeria.xml` | facebook | `galeria` |
| `SONDA-F2-S1-FB/fb-04-galeria-multiple.xml` | facebook | `galeria-multiple` |
| `SONDA-F2-S1-FB/fb-05-compositor-con-imagen.xml` | facebook | `compositor-con-imagen` |
| `SONDA-F2-S1-FB/fb-06-musica.xml` | facebook | `musica` |
| `SONDA-F2-S1-FB/fb-07-pantalla-final.xml` | facebook | `pantalla-final` |
| `SONDA-F2-S1-FB/fb-08-descartar-dialogo.xml` | facebook | `descartar-dialogo` |
| `SONDA-F2-S1-FB/fb-09-perfil-pagina.xml` | facebook | `perfil-pagina` |
| `SONDA-F2-S1-FB/fb-10-historia-creador.xml` | facebook | `historia-creador` |
| `SONDA-F2-S1-FB/fb-11-historia-editor.xml` | facebook | `historia-editor` |
| `SONDA-F2-S1-FB/fb-12-historia-stickers.xml` | facebook | `historia-stickers` |
| `SONDA-F2-S1-FB/fb-13-historia-opciones.xml` | facebook | `historia-opciones` |
| `SONDA-F2-S1-FB/fb-15-historia-visor-propio.xml` (si existe) | facebook | `historia-visor-propio` |

Run (ejemplo de la primera fila): `.venv/bin/python experiments/media-lab/lab.py fixture-podar --app instagram --desde $D/SONDA-F2-S1-IG/ig-01-inicio.xml --pantalla inicio`
Expected: `{"fixture": "tests/fixtures/telefono/instagram/inicio.xml"}`. Abrir cada fixture con Read: no debe quedar ningún nombre, mensaje ni pie ajeno, y deben seguir los textos de la interfaz ya presentes en `textos.py`, las menciones de la marca y las fechas de miniatura. La poda vacía todo lo que no está en `textos.py`: las tareas 11–17 añaden sus claves y vuelven a podar sus fixtures desde estos mismos volcados crudos; nunca se edita un XML.

- [ ] **Step 9: Batería**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 17 recorre todos los fixtures nuevos en `✓`; `El laboratorio cumple sus contratos.`

- [ ] **Step 10: Commit**

Antes de la tarea 11a, cada excepción de `NO_ENVIO` que S1 no confirmó (no apareció, o la captura muestra que publica) se quita de `NO_ENVIO` en `textos.py` y del bucle «I-5: excepción explícita» de `seccion_textos_y_descarte`, y se repite el Step 9. Si se quita «Partager à», en 11b-2 las comprobaciones de `IGH.destino` que esperan `err is None` pasan a esperar `PantallaInesperada` sin toques hasta que 11d la confirme a mano (su punto 3). Si el Step 8 añadió patrones a `textos.py` o se quitó alguna excepción, añadir también `experiments/media-lab/labkit/textos.py` (y `tests/test_media_lab.py` si cambió) al `git add`; si no cambiaron, no se añaden.

```bash
git add tests/fixtures/telefono experiments/media-lab/findings.md
git commit -m "media lab claude: sonda S1 de la fase 2 sin publicar y fixtures podados de Instagram, Threads y Facebook

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

El push deja los fixtures de S1 en `origin/main` antes de la tarea 11a, que los usa desde el worktree tras rebasar.

---

### Task 10: A0, feed de Instagram con música (spec, fila 4)

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir al final de `seccion_recetas_y_seleccion`:

```python
    musica = ("instagram", "feed_image_music")
    check(musica in S.TELEFONO_IMPLEMENTADO and RC.RECETAS[musica]["preparar"] == RC.RECETAS[("instagram", "feed_single_image")]["preparar"]
          and "tema" in RC.RECETAS[musica]["nota"],
          "A0: feed_image_music usa la receta de feed_single_image y pide anotar el tema")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON 1` con `A0: feed_image_music usa la receta de feed_single_image y pide anotar el tema`.

- [ ] **Step 3: Registrar el par**

En `recetas.py`, sustituir los diccionarios `TODAS` y `PROMOVIDAS` por:

```python
TODAS: dict[tuple[str, str], dict] = {
    ("instagram", "feed_single_image"): FEED_INSTAGRAM,
    ("instagram", "feed_image_music"): {
        **FEED_INSTAGRAM,
        "nota": ("Misma receta que feed_single_image: la música ya es obligatoria en toda foto. "
                 "Anota el tema de ig audio en audio_treatment del run; la celda se mide aparte."),
    },
}
PROMOVIDAS: dict[tuple[str, str], str] = {
    ("instagram", "feed_single_image"): "CELL-018: primera ventana manual confirmada (2026-09-14)",
    ("instagram", "feed_image_music"): "A0: misma receta y pasos que CELL-018, sin paso nuevo que probar",
}
```

- [ ] **Step 4: Ver que pasa**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

- [ ] **Step 5: Commit y push**

```bash
git add experiments/media-lab/labkit/recetas.py tests/test_media_lab.py
git commit -m "media lab claude: A0, el feed de Instagram con música usa la receta del feed

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

---

### Task 11a: A. Story de Instagram — textos y lectores contra fixtures (spec, fila 5)

Desbloquea `instagram/story_image` (se promueve en la tarea 11d) y deja escrito `instagram/story_image_music`, que se promueve en la tarea 16e tras validar el arrastre con la sonda S2.

**Files:**
- Modify: `experiments/media-lab/labkit/textos.py`, `experiments/media-lab/labkit/telefono.py` (`checked`/`selected` en `nodos`), `experiments/media-lab/labkit/pantalla.py`, `experiments/media-lab/labkit/instagram_pantallas.py`
- Test: `tests/test_media_lab.py`; fixtures `tests/fixtures/telefono/instagram/{perfil,crear-menu,historia-selector,historia-editor,historia-editor-audio,historia-destino,historia-visor-propio}.xml` (los dos últimos pueden faltar hasta 11d)

- [ ] **Step 1: Sonda complementaria (solo si S1 no dejó algún fixture)**

Comprobar que existen los fixtures de la lista **Files**. Por cada uno que falte, repetir su tramo del Step 3 de la tarea 9 con `--run SONDA-F2-A` y podarlo con `lab.py fixture-podar --app instagram --desde experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-A/<nombre>.xml --pantalla <fixture>`. `historia-visor-propio` puede faltar si no había story propia viva: las pruebas usan entonces `xml_visor_historia()` y la tarea 11d lo vuelca de verdad; lo mismo con `historia-destino` y `xml_destino_historia()` si S1 no pudo volcar el destino sin tocar un control que publica.

- [ ] **Step 2: Confirmar los textos de la Story contra S1**

Añadir a `TEXTOS["instagram"]` en `textos.py`, con el valor observado que anotó la tabla de S1 en `findings.md` si difiere del esperado, y quitar la marca de las que coincidan:

```python
        "story": "Story",  # confirmar contra el fixture de S1 (opción del menú Créer)
        "autocollants": "Autocollants",  # confirmar contra el fixture de S1 (botón del panel de stickers)
        "musique": "Musique",  # confirmar contra el fixture de S1 (sticker de música)
        "hacia_destino": "Partager à",  # confirmar contra el fixture de S1 (botón del editor hacia el destino)
        "vos_stories": "Vos stories",
        "amis_proches": "Amis proches",
        "partager_sur_facebook": "Partager sur Facebook",  # confirmar contra el fixture de S1 (conmutador del destino)
        "compartir_historia": "Partager",  # confirmar contra el fixture de S1 (botón de envío del destino)
        "aviso_historia": "Publication en cours",  # confirmar contra el fixture de S1 (aviso de subida)
        "votre_story": "Votre story",  # confirmar contra el fixture de S1 (content-desc del avatar con anillo)
        "activite": "Activité",
```

Añadir a la tupla `PATRONES_FIXTURE["instagram"]` el formato de la content-desc de las miniaturas del selector de Story que anotó S1, para que la poda no la vacíe:

```python
                  r"(?:Sélectionné |Désélectionné )?(?:Miniature de la photo|Photo|Vidéo) du \d{1,2}(?:er)? \S+ \d{4} \d{1,2}[:h]\d{2}",  # confirmar contra el fixture de S1
```

Si S1 anotó un formato de edad del visor distinto, ajustar `EDADES["instagram"]`. Después, volver a podar con `lab.py fixture-podar --app instagram` los fixtures de la lista **Files** desde sus volcados crudos de S1 (tabla del Step 8 de la tarea 9), para que conserven los textos recién confirmados.

- [ ] **Step 3: Escribir la prueba de los lectores**

Añadir antes de `SECCIONES` estos ayudantes y la sección, y registrar `seccion_instagram_historia,`:

```python
FIXTURES_TELEFONO = ROOT / "tests" / "fixtures" / "telefono"


def fixture(app: str, pantalla: str) -> str:
    return (FIXTURES_TELEFONO / app / f"{pantalla}.xml").read_text(encoding="utf-8")


def fixture_o(app: str, pantalla: str, sintetico: str) -> str:
    """El fixture real si la sonda lo capturó; si no (p. ej. no había story viva), el sintético."""
    ruta = FIXTURES_TELEFONO / app / f"{pantalla}.xml"
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else sintetico


def con_valor(xml: str, cumple, valor: str, atributo: str = "text") -> str:
    """Devuelve a un fixture podado el texto que la poda vació (un pie, una edad) en el primer nodo
    visible que cumple `cumple(n)`. AssertionError si ninguno cumple."""
    import re
    from xml.sax.saxutils import escape
    from labkit import telefono
    lista = telefono.nodos(xml)
    i = next((k for k, n in enumerate(lista) if cumple(n)), None)
    if i is None:
        raise AssertionError("con_valor: ningún nodo cumple la condición")
    bounds = lista[i]["bounds"]
    orden = sum(1 for n in lista[:i] if n["bounds"] == bounds)
    m = list(re.finditer(r'<node\b[^>]*\bbounds="\[%d,%d\]\[%d,%d\]"[^>]*>' % bounds, xml))[orden]
    nuevo = f'{atributo}="{escape(valor, {chr(34): "&quot;"})}"'
    patron = r'(?<![\w-])%s="[^"]*"' % re.escape(atributo)
    etiqueta = m.group(0)
    if re.search(patron, etiqueta):
        etiqueta = re.sub(patron, lambda _: nuevo, etiqueta, count=1)
    else:
        etiqueta = etiqueta.replace("<node ", f"<node {nuevo} ", 1)
    return xml[:m.start()] + etiqueta + xml[m.end():]


def con_nodo(xml: str, nodo: str) -> str:
    """El volcado con un nodo más al final (lo que aparece en pantalla tras un paso)."""
    return xml.replace("</hierarchy>", nodo + "</hierarchy>", 1)


def primera_fecha(xml: str, lector):
    from labkit import telefono
    for n in telefono.nodos(xml):
        fecha = lector(n["desc"]) if n["desc"] else None
        if fecha is not None:
            return fecha
    raise AssertionError("el fixture no tiene miniaturas con fecha")


def xml_visor_historia(cuenta: str = "sabiduriabolsillo", edad: str = "1 min") -> str:
    """Visor sintético de la story propia: solo si la sonda S1 no encontró una story viva."""
    from labkit import textos
    return jerarquia(nodo_xml("[150,120][500,180]", texto=cuenta), nodo_xml("[510,120][640,180]", texto=edad),
                     nodo_xml("[40,2150][300,2250]", texto=textos.TEXTOS["instagram"]["activite"]))


def xml_destino_historia() -> str:
    """Destino sintético de la Story: solo si S1 no pudo volcarlo sin tocar un control que publica."""
    from labkit import textos
    t = textos.TEXTOS["instagram"]
    return jerarquia(nodo_xml("[40,300][1040,420]", texto=t["vos_stories"]),
                     nodo_xml("[40,440][1040,560]", texto=t["amis_proches"]),
                     nodo_xml("[45,2081][1035,2205]", clase="android.widget.Button", extra='clickable="true"',
                              hijos=nodo_xml("[480,2115][600,2170]", texto=t["compartir_historia"])))


CHIP_AUDIO_SINTETICO = "Audio suggéré. Autumn Days par Morunas. Appuyez pour accéder à plus d’options …"


def xml_editor_audio_sintetico() -> str:
    """El editor de Story real con un chip de audio sintético encima. `fixture-podar` vacía la desc del chip real (el
    tema no se permite en un fixture), así que toda prueba que lea el tema del chip usa este XML."""
    return con_nodo(fixture("instagram", "historia-editor-audio"),
                    nodo_xml("[40,1880][760,2000]", desc=CHIP_AUDIO_SINTETICO, clase="android.widget.Button",
                             extra='clickable="true"'))


def seccion_instagram_historia() -> None:
    print("\n20. Fase 2 (A): Story de Instagram")
    from datetime import timedelta
    from labkit import instagram_pantallas as IP, pantalla as P, textos as TX

    t = TX.TEXTOS["instagram"]
    check(IP.perfil_activo(fixture("instagram", "perfil")) == IP.MARCA, "A: el perfil real es el de la marca")
    selector = fixture("instagram", "historia-selector")
    subida = primera_fecha(selector, IP.fecha_miniatura)
    check(bool(IP.miniatura_historia(selector, subida)["desc"]), "A: la miniatura de la subida se encuentra por hora en el selector real")
    try:
        IP.miniatura_historia(selector, subida + timedelta(hours=5))
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "A: sin miniatura a la hora de la subida, PantallaInesperada")
    editor = fixture("instagram", "historia-editor")
    check(IP.editor_historia_listo(editor) and not IP.editor_historia_listo(selector),
          "A: el editor de Story se reconoce solo en el editor")
    # `fixture-podar` vacía la desc del chip (el tema no se permite en un fixture): el tema sale de un chip sintético.
    chip = IP.chip_audio_historia(xml_editor_audio_sintetico())
    check(chip is not None and bool(chip["tema"]), f"A: el chip de audio (sintético sobre el editor real) dice el tema ({chip})")
    destino = fixture_o("instagram", "historia-destino", xml_destino_historia())
    d = IP.destino_historia_correcto(destino)
    check(d["problemas"] == [] and d["copia_facebook"] in (True, False, None), f"A: el destino real es «Vos stories» ({d})")
    check(bool(IP.destino_historia_correcto(editor)["problemas"]), "A: el editor no pasa por destino válido")

    visor = con_valor(fixture_o("instagram", "historia-visor-propio", xml_visor_historia()),
                      lambda n: P.edad_segundos(n["texto"], "instagram") is not None, "1 min")
    lectura = IP.historia_propia_reciente(visor)
    check(lectura["ok"] and lectura["edad_s"] == 60, f"A: visor propio con marca, edad y «Activité» ({lectura})")
    viejo = con_valor(visor, lambda n: P.edad_segundos(n["texto"], "instagram") is not None, "5 h")
    check(not IP.historia_propia_reciente(viejo)["ok"], "A: una story de hace 5 h no confirma")
    check(not IP.historia_propia_reciente(visor.replace('"sabiduriabolsillo"', '"otra.cuenta"'))["ok"],
          "A: el visor de otra cuenta no confirma")
    obs = IP.observacion_historia(xml_inicio(aviso=t["aviso_historia"]))
    check(obs["valido"] and obs["banner"] and not obs["compositor"] and not obs["fallo"],
          "A: el aviso de subida cuenta como banner")
    check(IP.observacion_historia(destino)["compositor"], "A: la pantalla de destino cuenta como compositor")
    check(IP.observacion_historia(xml_inicio(aviso="Impossible de publier. Réessayer"))["fallo"],
          "A: un aviso corto de error cuenta como fallo")

    avisos: list[str] = []
    check(P.estado_confirmado("sin_banner", {"ok": True}, False, []) == "confirmado"
          and P.estado_confirmado("confirmado", None, False, []) == "sin_confirmacion"
          and P.estado_confirmado("fallido", {"ok": True}, False, []) == "fallido"
          and P.estado_confirmado("confirmado", {"ok": True}, True, avisos, "motivo") == "confirmado_sin_prueba_unica"
          and avisos == ["motivo"],
          "estado_confirmado: lectura buena confirma; sin lectura, sin_confirmacion; fallido se queda; sin prueba única avisa")
    check(P.edad_segundos("À l’instant", "instagram") == 0 and P.edad_segundos("12 min", "instagram") == 720
          and P.edad_segundos("sabiduriabolsillo", "instagram") is None, "edad_segundos lee las edades de Instagram")
```

- [ ] **Step 4: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.instagram_pantallas' has no attribute 'miniatura_historia'` en la sección 20.

- [ ] **Step 5: Implementar los lectores**

En `telefono.nodos`, añadir al dict de cada nodo, junto a `"enabled"`:

```python
                                  "checkable": el.get("checkable", "false") == "true",
                                  "checked": el.get("checked", "false") == "true",
                                  "selected": el.get("selected", "false") == "true",
```

En `pantalla.py`, cambiar las importaciones a:

```python
import re
from datetime import datetime, timedelta

from labkit import telefono, textos
```

y añadir al final:

```python
def miniatura_por_hora(xml: str, paquete: str, subido_en: datetime, lector_fecha, tolerancia_min: int = 3) -> dict:
    """La única miniatura de `paquete` cuya content-desc lleva la hora de `subido_en` (±tolerancia).
    `lector_fecha(desc)` devuelve la fecha en UTC o None."""
    if subido_en.tzinfo is None:
        raise PantallaInesperada("subido_en sin zona horaria")
    candidatas = [n for n in telefono.buscar_todos(xml, paquete=paquete)
                  if n["desc"] and (f := lector_fecha(n["desc"])) is not None
                  and abs(f - subido_en) <= timedelta(minutes=tolerancia_min)]
    if not candidatas:
        raise PantallaInesperada(f"ninguna miniatura con la hora de la subida ({subido_en.isoformat()})")
    return elegir(candidatas, "miniatura de la subida")


def edad_segundos(valor: str, app: str) -> int | None:
    """Segundos de una edad escrita por la app («3 min», «Ahora»…); None si no es una edad."""
    for patron, factor in textos.EDADES.get(app, ()):
        m = re.fullmatch(patron, (valor or "").strip())
        if m:
            return int(m.group(1)) * factor if m.groups() else 0
    return None


def marcado_en_fila(xml: str, paquete: str, etiqueta: str) -> bool | None:
    """Estado de la casilla, radio o conmutador de la fila de `etiqueta` (la fila es el antecesor
    clickable de la etiqueta o, si no hay, la propia etiqueta). True si alguno está `checked` o
    `selected`; None si la etiqueta o la casilla no están."""
    lista = telefono.nodos(xml)
    indice = next((i for i, n in enumerate(lista) if n["package"] == paquete and dice(n, etiqueta)), None)
    if indice is None:
        return None
    fila = lista[indice]["bounds"]
    nivel = lista[indice]["profundidad"]
    for anterior in reversed(lista[:indice]):
        if anterior["profundidad"] >= nivel:
            continue
        nivel = anterior["profundidad"]
        if anterior["clickable"]:
            fila = anterior["bounds"]
            break
    casillas = [n for n in lista if n["package"] == paquete and fila[1] <= n["centro"][1] <= fila[3]
                and (n["checkable"] or n["clase"].endswith(("CheckBox", "RadioButton", "Switch", "CompoundButton")))]
    if not casillas:
        return None
    return any(n["checked"] or n["selected"] for n in casillas)


def estado_confirmado(envio: str, lectura: dict | None, sin_prueba_unica: bool, avisos: list[str],
                      motivo: str = "") -> str:
    """Estado final de un flujo de la fase 2 a partir del envío observado y de la lectura posterior
    en pantalla: «fallido» y «timeout» se quedan; sin lectura buena, «sin_confirmacion»; con
    lectura buena pero algo que no la distingue de otra publicación, «confirmado_sin_prueba_unica»
    (con `motivo` en avisos); si no, «confirmado»."""
    if envio in ("fallido", "timeout"):
        return envio
    if not lectura or not lectura.get("ok"):
        return "sin_confirmacion"
    if sin_prueba_unica:
        avisos.append(motivo or "la publicación se vio pero nada la distingue de otra: se concilia por captura")
        return "confirmado_sin_prueba_unica"
    return "confirmado"
```

En `instagram_pantallas.py`, cambiar `from labkit import pantalla, telefono` por `from labkit import pantalla, telefono, textos`, añadir a `__all__` `"miniatura_historia", "editor_historia_listo", "chip_audio_historia", "destino_historia_correcto", "historia_propia_reciente", "observacion_historia"` y añadir antes de `# --- Elección de controles`:

```python
# --- Story (fase 2, flujo A) -------------------------------------------------------

_T = textos.TEXTOS["instagram"]


def miniatura_historia(xml: str, subido_en: datetime) -> dict:
    """La miniatura del selector de Story con la hora de la subida."""
    return pantalla.miniatura_por_hora(xml, PAQUETE, subido_en, fecha_miniatura)


def editor_historia_listo(xml: str) -> bool:
    return (telefono.buscar(xml, texto=_T["autocollants"], paquete=PAQUETE) is not None
            and telefono.buscar(xml, texto=_T["hacia_destino"], paquete=PAQUETE) is not None)


def chip_audio_historia(xml: str) -> dict | None:
    """{"nodo", "tema", "anadido"} del chip «Audio suggéré» del editor de Story. `anadido` es True
    si el título del tema ya aparece fuera del chip."""
    chips = [n for n in telefono.buscar_todos(xml, paquete=PAQUETE) if n["desc"].startswith(_T["audio_sugerido"])]
    if not chips:
        return None
    chip = pantalla.elegir(chips, "chip de audio")
    tema = tema_de_chip(chip["desc"])
    titulo = tema.split(" par ")[0] if tema else None
    anadido = bool(titulo) and any(_es_textview(n) and n["texto"] == titulo and not pantalla.dentro(n["bounds"], chip["bounds"])
                                   for n in telefono.buscar_todos(xml, paquete=PAQUETE))
    return {"nodo": chip, "tema": tema, "anadido": anadido}


def destino_historia_correcto(xml: str) -> dict:
    """{"problemas", "copia_facebook"} de la pantalla de destino: «Vos stories» presente (y marcado
    si tiene casilla), «Amis proches» sin marcar y botón de envío visible, sin tapar y pulsable.
    `copia_facebook` es el estado del conmutador de Facebook (None si no aparece); no se cambia."""
    problemas = []
    if telefono.buscar(xml, texto=_T["vos_stories"], paquete=PAQUETE) is None:
        problemas.append(f"falta «{_T['vos_stories']}»")
    elif pantalla.marcado_en_fila(xml, PAQUETE, _T["vos_stories"]) is False:
        problemas.append(f"«{_T['vos_stories']}» no está marcado")
    if pantalla.marcado_en_fila(xml, PAQUETE, _T["amis_proches"]):
        problemas.append(f"«{_T['amis_proches']}» está marcado")
    botones = telefono.buscar_todos(xml, texto=_T["compartir_historia"], paquete=PAQUETE)
    if not botones:
        problemas.append(f"no hay botón «{_T['compartir_historia']}»")
    elif any(telefono.tapado(xml, b) for b in botones):
        problemas.append(f"«{_T['compartir_historia']}» está tapado")
    elif not pantalla.pulsable(xml, etiqueta=_T["compartir_historia"], paquete=PAQUETE):
        problemas.append(f"«{_T['compartir_historia']}» no se puede pulsar")
    return {"problemas": problemas, "copia_facebook": pantalla.marcado_en_fila(xml, PAQUETE, _T["partager_sur_facebook"])}


def historia_propia_reciente(xml: str, max_s: int = 180) -> dict:
    """{"ok", "problemas", "edad_s"} del visor de la story propia: cabecera @marca en el quinto
    superior, edad ≤ max_s y la barra propia «Activité»."""
    problemas = []
    alto = pantalla.alto_volcado(xml)
    arriba = [n for n in telefono.buscar_todos(xml, paquete=PAQUETE) if n["bounds"][3] * 5 <= alto]
    if not any(n["texto"] == MARCA for n in arriba):
        problemas.append(f"la cabecera del visor no es @{MARCA}")
    edades = [e for n in arriba if (e := pantalla.edad_segundos(n["texto"], "instagram")) is not None]
    edad = min(edades) if edades else None
    if edad is None:
        problemas.append("no se lee la edad de la story")
    elif edad > max_s:
        problemas.append(f"la story tiene {edad} s (máximo {max_s})")
    if telefono.buscar(xml, texto=_T["activite"], paquete=PAQUETE) is None:
        problemas.append(f"falta «{_T['activite']}»: no es la story propia")
    return {"ok": not problemas, "problemas": problemas, "edad_s": edad}


def observacion_historia(xml: str, boton_bounds: tuple[int, int, int, int] | None = None) -> dict:
    """Lo que dice un volcado tras pulsar el envío de la Story: `compositor` si sigue el destino
    (o el botón pulsado en los mismos bounds), `banner` si se ve el aviso de subida y `fallo` con
    un aviso corto de error de Instagram."""
    ig = telefono.buscar_todos(xml, paquete=PAQUETE)
    compositor = any(_dice(n, _T["vos_stories"]) or _dice(n, _T["amis_proches"]) for n in ig) or (
        boton_bounds is not None and any(_dice(n, _T["compartir_historia"]) and n["bounds"] == tuple(boton_bounds) for n in ig))
    aviso = any(v.startswith(_T["aviso_historia"]) for n in ig for v in (n["texto"], n["desc"]) if v)
    culpable = next((n for n in ig if _es_aviso_de_fallo(n, [])), None)
    return {"valido": bool(ig), "compositor": compositor, "banner": aviso, "fallo": culpable is not None,
            "fallo_texto": _recortado(_campo_de_aviso(culpable)) if culpable else None,
            "fallo_bounds": culpable["bounds"] if culpable else None}
```

- [ ] **Step 6: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 20 en `✓` y `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/telefono.py experiments/media-lab/labkit/pantalla.py experiments/media-lab/labkit/textos.py experiments/media-lab/labkit/instagram_pantallas.py tests/test_media_lab.py
git commit -m "media lab claude: lectores de la Story de Instagram probados contra los fixtures de S1

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11b-1: A. Story de Instagram — stickers y arrastre

**Files:**
- Create: `experiments/media-lab/labkit/stickers.py`
- Modify: `experiments/media-lab/labkit/telefono.py` (`arrastrar`), `experiments/media-lab/labkit/pasos.py` (`colocar_sticker`)
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de stickers y arrastre**

En `TelefonoSimulado.__init__` añadir `self.arrastres: list[tuple] = []` y el método:

```python
    def arrastrar(self, x1: int, y1: int, x2: int, y2: int, ms: int = 800) -> None:
        self.arrastres.append((x1, y1, x2, y2, ms))
```

En `con_telefono_simulado`, añadir a `cambios` `(telefono, "arrastrar", sim.arrastrar),`. Añadir al final de `seccion_instagram_historia`:

```python
    print("   · stickers y arrastre")
    import pathlib as _p
    from labkit import pasos, stickers as ST, telefono as T

    zona = (140, 760, 940, 1360)
    check(ST.sticker_en_zona((200, 800, 800, 1200), zona) and not ST.sticker_en_zona((100, 800, 800, 1200), zona),
          "sticker_en_zona exige los bounds completos dentro, no solo el centro")
    check(not ST.sticker_en_zona((200, 500, 800, 1200), (0, 0, 1080, 1920), ST.ZONAS_TEXTO_HISTORIA),
          "sticker_en_zona rechaza un sticker que pisa el panel de texto")
    check(ST.destino_arrastre((0, 0, 200, 100), zona) == (100, 50, 540, 1060), "destino_arrastre va del centro del sticker al de la zona")
    check(ST.zona_en_pantalla(zona, (0, 100, 1080, 2020)) == (140, 860, 940, 1460)
          and ST.zona_en_pantalla((0, 0, 1080, 1920), (54, 96, 594, 1056)) == (54, 96, 594, 1056),
          "zona_en_pantalla convierte píxeles del máster al lienzo")
    try:
        T.arrastrar(0, 0, 10, 10, 300)
        ok = False
    except T.TelefonoError:
        ok = True
    check(ok, "arrastrar rechaza un gesto de menos de 600 ms sin llamar a adb")

    lienzo = nodo_xml("[0,100][1080,2020]", clase="android.widget.ImageView")

    def con_sticker(bounds: str, hijo: str) -> str:
        return jerarquia(lienzo, nodo_xml(bounds, clase="android.widget.FrameLayout",
                                          hijos=nodo_xml(hijo, texto="Autumn Days")))

    antes = con_sticker("[100,300][700,500]", "[150,350][650,450]")
    despues = con_sticker("[240,1060][840,1260]", "[290,1110][790,1210]")
    check(ST.bounds_sticker_texto(antes, PAQUETE_IG, "Autumn Days") == (100, 300, 700, 500)
          and ST.lienzo(antes, PAQUETE_IG) == (0, 100, 1080, 2020),
          "bounds_sticker_texto devuelve el contenedor del sticker sobre el lienzo 9:16")
    localizar = lambda x: ST.bounds_sticker_texto(x, PAQUETE_IG, "Autumn Days")  # noqa: E731
    evid = _p.Path("evidencia-simulada")
    sim = TelefonoSimulado([antes, antes, antes, despues])
    res, err = con_telefono_simulado(sim, lambda: pasos.colocar_sticker(localizar, zona, PAQUETE_IG, evid, "sticker"))
    check(err is None and sim.arrastres == [(400, 400, 540, 1160, ST.DURACION_ARRASTRE_MS)] and res["arrastres"] == 1
          and sim.capturas == ["sticker.png"],
          f"colocar_sticker arrastra una vez y captura con el sticker dentro ({err!r}, {sim.arrastres})")
    sim = TelefonoSimulado([antes])
    res, err = con_telefono_simulado(sim, lambda: pasos.colocar_sticker(localizar, zona, PAQUETE_IG, evid, "sticker"))
    check(isinstance(err, pasos.PantallaInesperada) and len(sim.arrastres) == ST.ARRASTRES_MAX and sim.capturas == [],
          f"si el sticker no entra tras 2 arrastres, PantallaInesperada sin captura ({err!r}, {sim.arrastres})")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.telefono' has no attribute 'arrastrar'` en el primer uso de `con_telefono_simulado` (sección 6).

- [ ] **Step 3: Implementar `telefono.arrastrar`, `stickers.py` y `pasos.colocar_sticker`**

En `telefono.py`, junto a `tocar`:

```python
DURACION_MINIMA_ARRASTRE_MS = 600


def arrastrar(x1: int, y1: int, x2: int, y2: int, ms: int = 800) -> None:
    """`input swipe` lento: por debajo de 600 ms Android lo toma por un gesto rápido y no arrastra
    el sticker (a validar en la sonda S2)."""
    if ms < DURACION_MINIMA_ARRASTRE_MS:
        raise TelefonoError(f"un arrastre necesita al menos {DURACION_MINIMA_ARRASTRE_MS} ms, no {ms}")
    shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(ms)}")
```

`experiments/media-lab/labkit/stickers.py`:

```python
"""
Stickers de Story: dónde están, si caben en la zona reservada del máster y cómo llevarlos allí.

Puro. La zona reservada viene en píxeles del máster de 1080×1920 y se convierte a pantalla con
los bounds del lienzo de la Story. Las zonas de texto son las que `render_overlay.py --format
story` usa para el panel y la firma: un sticker no puede pisarlas.
"""
from __future__ import annotations

from labkit import pantalla, telefono
from labkit.pantalla import PantallaInesperada

MASTER = (1080, 1920)
ZONAS_TEXTO_HISTORIA = ((54, 170, 1026, 600), (0, 1775, 1080, 1828))  # panel y firma de render_overlay
ARRASTRES_MAX = 2
DURACION_ARRASTRE_MS = 800

Bounds = tuple[int, int, int, int]


def _interseca(a: Bounds, b: Bounds) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _area(b: Bounds) -> int:
    return (b[2] - b[0]) * (b[3] - b[1])


def sticker_en_zona(bounds_sticker: Bounds, zona_reservada: Bounds, zonas_texto=()) -> bool:
    """Los bounds completos del sticker dentro de la zona y sin tocar ninguna zona de texto."""
    return pantalla.dentro(bounds_sticker, zona_reservada) and not any(_interseca(bounds_sticker, z) for z in zonas_texto)


def destino_arrastre(bounds_sticker: Bounds, zona_reservada: Bounds) -> Bounds:
    """(x1, y1, x2, y2) del arrastre: del centro del sticker al centro de la zona."""
    x1, y1, x2, y2 = bounds_sticker
    zx1, zy1, zx2, zy2 = zona_reservada
    return (x1 + x2) // 2, (y1 + y2) // 2, (zx1 + zx2) // 2, (zy1 + zy2) // 2


def zona_en_pantalla(zona_master: Bounds, lienzo_bounds: Bounds, master: tuple[int, int] = MASTER) -> Bounds:
    lx1, ly1, lx2, ly2 = lienzo_bounds
    ex, ey = (lx2 - lx1) / master[0], (ly2 - ly1) / master[1]
    x1, y1, x2, y2 = zona_master
    return lx1 + round(x1 * ex), ly1 + round(y1 * ey), lx1 + round(x2 * ex), ly1 + round(y2 * ey)


def lienzo(xml: str, paquete: str, master: tuple[int, int] = MASTER, tolerancia: float = 0.03) -> Bounds:
    """Bounds de la imagen de la Story: el nodo de `paquete` de mayor área con la proporción del
    máster (±3 %)."""
    objetivo = master[0] / master[1]
    candidatos = [n for n in telefono.buscar_todos(xml, paquete=paquete)
                  if abs((n["bounds"][2] - n["bounds"][0]) / (n["bounds"][3] - n["bounds"][1]) - objetivo) <= objetivo * tolerancia]
    if not candidatos:
        raise PantallaInesperada("no se encuentra el lienzo 9:16 de la Story en el volcado")
    return max(candidatos, key=pantalla.area)["bounds"]


def bounds_de(nodos: list[dict]) -> Bounds:
    """El rectángulo mínimo que contiene todos los nodos."""
    return (min(n["bounds"][0] for n in nodos), min(n["bounds"][1] for n in nodos),
            max(n["bounds"][2] for n in nodos), max(n["bounds"][3] for n in nodos))


def contenedor_de(xml: str, nodo: dict, paquete: str, lienzo_bounds: Bounds) -> Bounds:
    """Bounds del sticker que contiene `nodo`: su antecesor más grande de `paquete` que lo contiene y
    ocupa menos de la mitad del lienzo; si no hay, los del propio nodo."""
    lista = telefono.nodos(xml)
    clave = ("bounds", "texto", "desc", "clase")
    i = next((k for k, m in enumerate(lista) if all(m[c] == nodo[c] for c in clave)), None)
    mejor = nodo["bounds"]
    if i is None:
        return mejor
    limite = _area(lienzo_bounds) / 2
    nivel = nodo["profundidad"]
    for anterior in reversed(lista[:i]):
        if anterior["profundidad"] >= nivel:
            continue
        nivel = anterior["profundidad"]
        if anterior["package"] == paquete and _area(anterior["bounds"]) < limite and pantalla.dentro(nodo["bounds"], anterior["bounds"]):
            mejor = anterior["bounds"]
        else:
            break
    return mejor


def bounds_sticker_texto(xml: str, paquete: str, texto: str) -> Bounds | None:
    """Bounds del único sticker del lienzo que muestra `texto` (título del tema, pregunta de la
    encuesta); None si no está o hay más de uno."""
    try:
        lz = lienzo(xml, paquete)
    except PantallaInesperada:
        return None
    nodos = [n for n in telefono.buscar_todos(xml, paquete=paquete)
             if texto in (n["texto"], n["desc"]) and pantalla.dentro(n["bounds"], lz)]
    if len(nodos) != 1:
        return None
    return contenedor_de(xml, nodos[0], paquete, lz)
```

En `pasos.py`, cambiar `from labkit import pantalla, reloj, telefono` por `from labkit import pantalla, reloj, stickers, telefono` y añadir al final:

```python
def colocar_sticker(localizar, zona_master: tuple[int, int, int, int], paquete: str, evidencia: Path, nombre: str) -> dict:
    """Lleva el sticker que devuelve `localizar(xml) -> bounds | None` a la zona reservada (píxeles
    del máster, convertidos al lienzo) sin pisar las zonas de texto del máster. Cada lectura con
    volcado estable; hasta stickers.ARRASTRES_MAX arrastres. Si no queda dentro, PantallaInesperada
    (el borrador se abandona). La QA tiene la última palabra sobre la captura."""
    exigir_listo()
    arrastres = 0
    while True:
        xml, bounds = esperar_estable(localizar, descripcion="la posición del sticker")
        lz = stickers.lienzo(xml, paquete)
        zona = stickers.zona_en_pantalla(zona_master, lz)
        zonas_texto = [stickers.zona_en_pantalla(z, lz) for z in stickers.ZONAS_TEXTO_HISTORIA]
        if stickers.sticker_en_zona(bounds, zona, zonas_texto):
            return {"bounds": list(bounds), "zona_pantalla": list(zona), "arrastres": arrastres,
                    "captura": str(telefono.captura(evidencia / f"{nombre}.png"))}
        if arrastres >= stickers.ARRASTRES_MAX:
            raise PantallaInesperada(f"el sticker {bounds} no quedó dentro de la zona {zona} tras {arrastres} arrastres")
        telefono.arrastrar(*stickers.destino_arrastre(bounds, zona), stickers.DURACION_ARRASTRE_MS)
        arrastres += 1
        reloj.dormir(2)
```

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/telefono.py experiments/media-lab/labkit/stickers.py experiments/media-lab/labkit/pasos.py tests/test_media_lab.py
git commit -m "media lab claude: stickers de Story, arrastre lento y colocación en la zona reservada

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11b-2: A. Story de Instagram — pasos con teléfono simulado

**Files:**
- Create: `experiments/media-lab/labkit/instagram_historia.py`
- Modify: `experiments/media-lab/labkit/pasos.py` (`lanzar_app`)
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de los pasos de la Story**

Añadir al final de `seccion_instagram_historia`:

```python
    print("   · pasos de la Story con teléfono simulado")
    from labkit import instagram_historia as IGH

    perfil_centro = T.buscar(xml_perfil(), texto="Profil")["centro"]
    crear = fixture("instagram", "crear-menu")
    sim = TelefonoSimulado([xml_inicio(), xml_perfil(), crear, selector])
    res, err = con_telefono_simulado(sim, lambda: IGH.abrir(evid, subida))
    story = P.nodo(crear, PAQUETE_IG, texto=t["story"])["centro"]
    check(err is None and len(sim.toques) == 3 and sim.toques[0] == perfil_centro and sim.toques[2] == story
          and sim.capturas == ["igh-01-selector.png"] and sim.orden == ["cortina", f"lanzar:{PAQUETE_IG}"],
          f"A abrir: Profil, Créer y Story; selector capturado ({err!r}, {sim.toques})")
    sim = TelefonoSimulado([xml_inicio(), xml_perfil(titulo="cuenta.personal")])
    res, err = con_telefono_simulado(sim, lambda: IGH.abrir(evid, subida))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [perfil_centro],
          f"A abrir con la cuenta personal: ningún toque de composición ({err!r}, {sim.toques})")
    sim = TelefonoSimulado([editor])
    res, err = con_telefono_simulado(sim, lambda: IGH.abrir(evid, subida))
    check(isinstance(err, pasos.BorradorPendiente) and sim.toques == [], "A abrir con una Story a medias: BorradorPendiente sin tocar")
    sim = TelefonoSimulado([xml_inicio()], listo=False)
    res, err = con_telefono_simulado(sim, lambda: IGH.abrir(evid, subida))
    check(isinstance(err, pasos.TelefonoNoListo) and sim.toques == [] and sim.orden == [],
          "A abrir con el teléfono no listo: nada")

    miniatura = IP.miniatura_historia(selector, subida)["centro"]
    sim = TelefonoSimulado([selector, editor])
    res, err = con_telefono_simulado(sim, lambda: IGH.elegir(evid, subida))
    check(err is None and sim.toques == [miniatura] and sim.capturas == ["igh-02-editor.png"],
          f"A elegir: un toque en la miniatura de la subida ({err!r}, {sim.toques})")

    editor_audio = xml_editor_audio_sintetico()  # el tema del chip no sobrevive a la poda del fixture
    chip_ig = IP.chip_audio_historia(editor_audio)
    titulo = chip_ig["tema"].split(" par ")[0]
    con_tema = con_nodo(editor_audio, nodo_xml("[1,1][3,3]", texto=titulo))  # fuera del chip: el tema ya añadido
    if chip_ig["anadido"]:
        guion_audio, toques_audio = [editor_audio], []
    else:
        guion_audio, toques_audio = [editor_audio, con_tema], [IP.punto_mas(chip_ig["nodo"]["bounds"])]
    sim = TelefonoSimulado(guion_audio)
    res, err = con_telefono_simulado(sim, lambda: IGH.audio(evid))
    check(err is None and res["tema"] == chip_ig["tema"] and sim.toques == toques_audio
          and sim.capturas == ["igh-03-audio.png"],
          f"A audio: añade el tema solo si no venía añadido ({err!r}, {sim.toques})")

    hacia = P.nodo(editor, PAQUETE_IG, texto=t["hacia_destino"])["centro"]
    sim = TelefonoSimulado([editor, destino])
    res, err = con_telefono_simulado(sim, lambda: IGH.destino(evid))
    check(err is None and sim.toques == [hacia] and "copia_facebook" in res and sim.capturas == ["igh-04-destino.png"],
          f"A destino: un toque hacia el destino y lee el conmutador de Facebook sin cambiarlo ({err!r}, {sim.toques})")
    sim = TelefonoSimulado([editor, destino], listo=False)
    res, err = con_telefono_simulado(sim, lambda: IGH.destino(evid))
    check(isinstance(err, pasos.TelefonoNoListo) and sim.toques == [], "A destino con el teléfono no listo a mitad de flujo: nada")
    for nombre_paso, guion_paso, accion in (
            ("abrir", [xml_inicio(), xml_perfil(), crear, selector], lambda: IGH.abrir(evid, subida)),
            ("elegir", [selector, editor], lambda: IGH.elegir(evid, subida)),
            ("audio", guion_audio, lambda: IGH.audio(evid)),
            ("destino", [editor, destino], lambda: IGH.destino(evid))):
        sim = TelefonoSimulado(guion_paso)
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and not toques_sobre_envio(sim, PAQUETE_IG),
              f"C1 A {nombre_paso}: fuera de compartir, ningún toque cae sobre un control de envío ({err!r}, {sim.toques})")
    stickers_fx = fixture("instagram", "historia-stickers")
    lista_musica = con_nodo(stickers_fx, nodo_xml("[100,1200][900,1300]", texto="Autumn Days", extra='clickable="true"'))
    hecho = jerarquia(nodo_xml("[860,20][1060,90]", texto=t["terminado"], clase="android.widget.Button", extra='clickable="true"'))
    colocado = jerarquia(nodo_xml("[0,100][1080,2020]", clase="android.widget.ImageView"),
                         nodo_xml("[240,960][840,1360]", clase="android.widget.FrameLayout",
                                  hijos=nodo_xml("[260,980][820,1040]", texto="Autumn Days")))
    sim = TelefonoSimulado([editor, stickers_fx, lista_musica, hecho, colocado, colocado, colocado])
    res, err = con_telefono_simulado(sim, lambda: IGH.sticker_musica(evid, (140, 760, 940, 1360), "Autumn Days par Morunas"))
    check(err is None and sim.arrastres == [] and sim.capturas == ["igh-03b-sticker-musica.png"] and not toques_sobre_envio(sim, PAQUETE_IG),
          f"C1 A sticker-musica: el sticker del tema queda en la zona sin tocar controles de envío ({err!r}, {sim.toques})")

    aviso = xml_inicio(aviso=t["aviso_historia"])
    limpio = xml_inicio()
    perfil_con_story = xml_perfil(abajo=nodo_xml("[40,600][300,860]", desc=t["votre_story"],
                                                 clase="android.widget.ImageView", extra='clickable="true"'))
    boton = P.nodo(destino, PAQUETE_IG, texto=t["compartir_historia"])["centro"]
    guion = [destino, destino, destino, aviso, limpio, limpio, limpio, perfil_con_story, visor]
    sim = TelefonoSimulado(guion)
    res, err = con_telefono_simulado(sim, lambda: IGH.compartir(evid))
    check(err is None and res["estado"] == "confirmado" and sim.toques.count(boton) == 1 and sim.toques[0] == boton
          and res["visor"]["ok"] and sim.capturas == ["igh-05a-antes.png", "igh-06-visor.png", "igh-07-final.png"],
          f"A compartir: exactamente un toque en el envío, visor propio y confirmado ({err!r}, {res and res['estado']}, {sim.toques})")
    sim = TelefonoSimulado(guion)
    res, err = con_telefono_simulado(sim, lambda: IGH.compartir(evid, produccion_cercana=True))
    check(err is None and res["estado"] == "confirmado_sin_prueba_unica" and sim.toques.count(boton) == 1 and res["avisos"],
          f"A compartir con una Story de producción cerca: confirmado_sin_prueba_unica ({res and res['estado']})")
    sim = TelefonoSimulado([destino, destino, destino, xml_inicio(aviso="Impossible de publier. Réessayer"),
                            limpio, perfil_con_story, visor])
    res, err = con_telefono_simulado(sim, lambda: IGH.compartir(evid))
    check(err is None and res["estado"] == "fallido" and sim.toques.count(boton) == 1,
          f"A compartir con aviso de error: fallido y un solo toque ({res and res['estado']})")
    sim = TelefonoSimulado([editor])
    res, err = con_telefono_simulado(sim, lambda: IGH.compartir(evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "A compartir fuera del destino: no se pulsa")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'instagram_historia' from 'labkit'`.

- [ ] **Step 3: Implementar `pasos.lanzar_app` e `instagram_historia.py`**

En `pasos.py`, tras `volcado_fresco`:

```python
def lanzar_app(paquete: str, app: str, *, listo, borrador, descripcion: str) -> str:
    """Teléfono listo, cortina replegada (best-effort), app lanzada y primer volcado en el que la app
    está lista o muestra una publicación a medias; en ese caso BorradorPendiente y no se toca."""
    exigir_listo()
    try:
        telefono.cerrar_cortina()
    except telefono.TelefonoError:
        pass
    telefono.lanzar(paquete)
    reloj.dormir(4)
    xml = esperar_que(lambda x: listo(x) or borrador(x), descripcion, app=app)
    if borrador(xml):
        raise BorradorPendiente(f"{app} abrió con una publicación a medias: no se toca")
    return xml
```

`experiments/media-lab/labkit/instagram_historia.py`:

```python
"""
Story de imagen de Instagram por teléfono, un paso por llamada (flujo A de la fase 2).

abrir → elegir → audio → [sticker-musica] → destino → QA → compartir. Cada paso exige el teléfono
listo, deja una captura y termina; quien dirige la mira antes del siguiente. La copia automática
en la Story de la Página se lee en el destino y no se cambia (decisión tomada).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from labkit import pantalla, pasos, reloj, stickers, telefono, textos
from labkit.instagram_pantallas import (MARCA, PAQUETE, PantallaInesperada, _campos, chip_audio_historia,
                                        destino_historia_correcto, editor_historia_listo, historia_propia_reciente,
                                        miniatura_historia, observacion_historia, perfil_activo, punto_mas)

T = textos.TEXTOS["instagram"]
VISOR_MAX_S = 180


def _esperar_texto(texto: str, zona: str | None = None) -> str:
    return pasos.esperar_que(lambda x: bool(pantalla.coincidencias(x, PAQUETE, zona, texto=texto)), f"«{texto}»",
                             app="instagram")


def _borrador(xml: str) -> bool:
    return (editor_historia_listo(xml) or telefono.buscar(xml, texto=T["vos_stories"], paquete=PAQUETE) is not None
            or telefono.buscar(xml, texto=T["nueva_publicacion"], paquete=PAQUETE) is not None or bool(_campos(xml)))


def _lanzar() -> str:
    return pasos.lanzar_app(PAQUETE, "instagram",
                            listo=lambda x: bool(pantalla.coincidencias(x, PAQUETE, "abajo", texto=T["perfil"])),
                            borrador=_borrador, descripcion="Instagram listo (Profil o una publicación a medias)")


def _perfil_de_marca(xml: str) -> str:
    """Desde una pantalla con la barra de abajo, al perfil; exige @marca."""
    pasos.tocar(pantalla.nodo(xml, PAQUETE, "abajo", texto=T["perfil"]), xml, PAQUETE)
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, contiene=T["modificar_perfil"], paquete=PAQUETE) is not None,
                            "el perfil", app="instagram")
    perfil = perfil_activo(xml)
    if perfil != MARCA:
        raise PantallaInesperada(f"el perfil activo es {perfil!r}, no @{MARCA}")
    return xml


def _bounds_miniatura(xml: str, subido_en: datetime):
    try:
        return miniatura_historia(xml, subido_en)["bounds"]
    except PantallaInesperada:
        return None


def abrir(evidencia: Path, subido_en: datetime) -> dict:
    """Perfil de la marca → Créer → Story → selector con la miniatura de la subida."""
    xml = _perfil_de_marca(_lanzar())
    pasos.tocar(pantalla.nodo(xml, PAQUETE, "arriba", texto=T["crear"]), xml, PAQUETE)
    xml = _esperar_texto(T["story"])
    pasos.tocar(pantalla.nodo(xml, PAQUETE, texto=T["story"]), xml, PAQUETE)
    _, bounds = pasos.esperar_estable(lambda x: _bounds_miniatura(x, subido_en), descripcion="la miniatura de la subida")
    return {"miniatura": list(bounds), "captura": str(telefono.captura(evidencia / "igh-01-selector.png"))}


def elegir(evidencia: Path, subido_en: datetime) -> dict:
    """Toca la miniatura de la subida y espera al editor."""
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: _bounds_miniatura(x, subido_en) is not None, "la miniatura de la subida", app="instagram")
    pasos.tocar(miniatura_historia(xml, subido_en), xml, PAQUETE)
    pasos.esperar_que(editor_historia_listo, "el editor de la Story", app="instagram")
    return {"captura": str(telefono.captura(evidencia / "igh-02-editor.png"))}


def audio(evidencia: Path) -> dict:
    """Chip «Audio suggéré»: se añade si no venía añadido y se anota el tema."""
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: chip_audio_historia(x) is not None, "el chip «Audio suggéré»", app="instagram")
    chip = chip_audio_historia(xml)
    if chip["tema"] is None:
        raise PantallaInesperada(f"el chip de audio no dice qué tema es: {chip['nodo']['desc']!r}")
    if not chip["anadido"]:
        telefono.tocar(*punto_mas(chip["nodo"]["bounds"]))
        xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["terminado"], paquete=PAQUETE) is not None
                                or bool((chip_audio_historia(x) or {}).get("anadido")), "el tema añadido", app="instagram")
        terminado = telefono.buscar_todos(xml, texto=T["terminado"], paquete=PAQUETE)
        if terminado:
            pasos.tocar(pantalla.elegir(terminado, T["terminado"]), xml, PAQUETE)
            reloj.dormir(3)
    pasos.esperar_que(editor_historia_listo, "el editor con el audio", app="instagram")
    return {"tema": chip["tema"], "captura": str(telefono.captura(evidencia / "igh-03-audio.png"))}


def sticker_musica(evidencia: Path, zona: tuple[int, int, int, int], tema: str) -> dict:
    """Sticker visible del tema (story_image_music) colocado dentro de la zona reservada."""
    pasos.exigir_listo()
    titulo = tema.split(" par ")[0]
    xml = pasos.esperar_que(editor_historia_listo, "el editor de la Story", app="instagram")
    pasos.tocar(pantalla.nodo(xml, PAQUETE, texto=T["autocollants"]), xml, PAQUETE)
    xml = _esperar_texto(T["musique"])
    pasos.tocar(pantalla.nodo(xml, PAQUETE, texto=T["musique"]), xml, PAQUETE)
    xml = pasos.esperar_que(lambda x: bool(telefono.buscar_todos(x, texto=titulo, paquete=PAQUETE)),
                            f"el tema «{titulo}» en la lista", app="instagram")
    pasos.tocar(pantalla.elegir(telefono.buscar_todos(xml, texto=titulo, paquete=PAQUETE), titulo), xml, PAQUETE)
    xml = _esperar_texto(T["terminado"])
    pasos.tocar(pantalla.nodo(xml, PAQUETE, texto=T["terminado"]), xml, PAQUETE)
    reloj.dormir(2)
    colocado = pasos.colocar_sticker(lambda x: stickers.bounds_sticker_texto(x, PAQUETE, titulo), zona, PAQUETE,
                                     evidencia, "igh-03b-sticker-musica")
    return {"tema": tema, **colocado}


def destino(evidencia: Path) -> dict:
    """Del editor a la pantalla de destino; exige «Vos stories» sin «Amis proches» y anota el conmutador de Facebook."""
    pasos.exigir_listo()
    xml = pasos.esperar_que(editor_historia_listo, "el editor de la Story", app="instagram")
    pasos.tocar(pantalla.nodo(xml, PAQUETE, texto=T["hacia_destino"]), xml, PAQUETE)
    xml, _ = pasos.esperar_estable(lambda x: telefono.buscar(x, texto=T["vos_stories"], paquete=PAQUETE) is not None,
                                   descripcion="la pantalla de destino")
    d = destino_historia_correcto(xml)
    if d["problemas"]:
        raise PantallaInesperada(f"el destino de la Story no es el esperado: {d['problemas']}")
    return {"copia_facebook": d["copia_facebook"], "captura": str(telefono.captura(evidencia / "igh-04-destino.png"))}


def _visor_propio(evidencia: Path, nombre: str) -> dict:
    xml = pasos.esperar_que(lambda x: bool(pantalla.coincidencias(x, PAQUETE, "abajo", texto=T["perfil"])),
                            "la barra con Profil", app="instagram")
    xml = _perfil_de_marca(xml)
    pasos.tocar(pantalla.nodo(xml, PAQUETE, empieza=T["votre_story"]), xml, PAQUETE, permitir=(T["votre_story"],))  # abre el visor, no publica
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["activite"], paquete=PAQUETE) is not None,
                            "el visor de la story propia", app="instagram")
    lectura = historia_propia_reciente(xml, VISOR_MAX_S)
    lectura["captura"] = str(telefono.captura(evidencia / f"{nombre}.png"))
    return lectura


def compartir(evidencia: Path, produccion_cercana: bool = False) -> dict:
    """Pulsa el envío del destino una sola vez y confirma en el visor de la story propia.

    Estados: «confirmado», «confirmado_sin_prueba_unica» (`produccion_cercana`: producción publicó
    una Story de Instagram en el margen y el visor no la distingue), «sin_confirmacion», «timeout»,
    «fallido» y «error_tras_pulsar»."""
    pasos.exigir_listo()
    copia = destino_historia_correcto(pasos.volcado_fresco())["copia_facebook"]

    def despues(resultado: dict, estado: str) -> str:
        avisos = resultado["avisos"]
        lectura = None
        try:
            if telefono.estado()["listo"]:
                lectura = _visor_propio(evidencia, "igh-06-visor")
                resultado["visor"] = lectura
            else:
                avisos.append("tras compartir el teléfono no está listo: no se abrió la story propia")
        except (PantallaInesperada, telefono.TelefonoError) as e:
            avisos.append(f"no se pudo abrir la story propia: {e}")
        return pantalla.estado_confirmado(
            estado, lectura, produccion_cercana, avisos,
            "producción publicó una Story de Instagram cerca: concilia pasando al revisor igh-06-visor.png y el máster")

    return pasos.enviar(
        paquete=PAQUETE, nombre_app="Instagram", etiqueta=T["compartir_historia"], evidencia=evidencia,
        captura_antes="igh-05a-antes.png", captura_final="igh-07-final.png", captura_error="igh-05-error.png",
        listo=lambda x, emergentes: destino_historia_correcto(x)["problemas"],
        botones=lambda x: telefono.buscar_todos(x, texto=T["compartir_historia"], paquete=PAQUETE),
        observador_nuevo=lambda boton: (lambda x: observacion_historia(x, boton["bounds"])),
        despues=despues, extra={"visor": None, "copia_facebook": copia})


def actividad(evidencia: Path) -> dict:
    """Métricas por teléfono cuando la API no las da: abre la story propia y desliza hacia «Activité»."""
    xml = _lanzar()
    lectura = _visor_propio(evidencia, "igh-08-visor")
    alto = pantalla.alto_volcado(pasos.volcado_fresco())
    telefono.arrastrar(540, round(alto * 0.85), 540, round(alto * 0.45), telefono.DURACION_MINIMA_ARRASTRE_MS)
    reloj.dormir(2)
    return {"visor": lectura, "captura": str(telefono.captura(evidencia / "igh-09-actividad.png"))}
```

(`actividad` usa `xml` solo para exigir que Instagram esté listo; `_visor_propio` vuelve a esperar la barra.)

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/pasos.py experiments/media-lab/labkit/instagram_historia.py tests/test_media_lab.py
git commit -m "media lab claude: pasos de la Story de Instagram con un solo toque de envío y visor propio

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11c: A. Story de Instagram — `lab.py ig-historia`, recetas en borrador y prompt

**Files:**
- Modify: `experiments/media-lab/lab.py`, `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Prueba de `lab.py ig-historia` y de las recetas**

Añadir al final de `seccion_instagram_historia`:

```python
    print("   · lab.py ig-historia y recetas de Story")
    from labkit import recetas as RC

    with entorno_lab_fase2() as (lab, raiz):
        for args, fragmento, label in ((("ig-historia", "abrir", "--run", "R"), "--subido-en", "abrir sin --subido-en"),
                            (("ig-historia", "elegir", "--run", "R", "--subido-en", "2026-09-14T10:00:00"), "zona horaria", "--subido-en sin zona"),
                            (("ig-historia", "sticker-musica", "--run", "R", "--tema", "T"), "--zona", "sticker-musica sin --zona"),
                            (("ig-historia", "sticker-musica", "--run", "R", "--tema", "T", "--zona", "0,0,2000,10"),
                             "--zona", "--zona fuera del máster"),
                            (("ig-historia", "audio", "--run", "R", "--produccion-cercana"), "--produccion-cercana", "--produccion-cercana fuera de compartir")):
            sim = TelefonoSimulado([xml_perfil()])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0 and sim.toques == [],
                  f"ig-historia rechaza {label} sin tocar el teléfono ({res and res[0]})")
        recibido: dict = {}
        original = IGH.compartir
        try:
            IGH.compartir = lambda ev, produccion_cercana=False: recibido.update(pc=produccion_cercana) or {
                "estado": "confirmado_sin_prueba_unica" if produccion_cercana else "confirmado"}
            codigo, _, _ = lab("ig-historia", "compartir", "--run", "R", "--produccion-cercana")
            check(codigo == 5 and recibido.get("pc") is True, f"ig-historia compartir: fuera de confirmado sale con 5 ({codigo})")
            codigo, _, _ = lab("ig-historia", "compartir", "--run", "R")
            check(codigo == 0 and recibido.get("pc") is False, f"ig-historia compartir confirmado sale con 0 ({codigo})")
        finally:
            IGH.compartir = original

    check(("instagram", "story_image") in RC.TODAS and ("instagram", "story_image_music") in RC.TODAS
          and any(c["args"][:2] == ["ig-historia", "sticker-musica"] for c in RC.TODAS[("instagram", "story_image_music")]["preparar"])
          and not any(c["args"][:2] == ["ig-historia", "sticker-musica"] for c in RC.TODAS[("instagram", "story_image")]["preparar"]),
          "A: recetas de Story; solo story_image_music lleva el sticker de música")
    check(("instagram", "story_image_music") in RC.BORRADORES, "A: story_image_music espera a la sonda S2")
```

- [ ] **Step 2: Ver que falla, implementar y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con los rechazos de `ig-historia` (argparse no conoce el subcomando: sale con 2 y `ArgumentoNoValido`, pero el mensaje no nombra el argumento esperado) y «A: recetas de Story…».

En `lab.py`, añadir antes de `class Analizador`:

```python
PASOS_IG_HISTORIA = ("abrir", "elegir", "audio", "sticker-musica", "destino", "compartir", "actividad")
LADO_MASTER_HISTORIA = (1080, 1920)


def _subidas(valores: list[str] | None) -> list[datetime]:
    fuera = []
    for valor in valores or []:
        try:
            fecha = datetime.fromisoformat(valor)
        except ValueError as e:
            raise ArgumentoNoValido(f"--subido-en no es una fecha ISO 8601: {valor!r}") from e
        _exigir(fecha.tzinfo is not None, "--subido-en necesita zona horaria")
        fuera.append(fecha)
    return fuera


def _zona(texto: str | None) -> tuple[int, int, int, int] | None:
    if texto is None:
        return None
    try:
        x1, y1, x2, y2 = (int(p) for p in texto.split(","))
    except ValueError as e:
        raise ArgumentoNoValido(f"--zona debe ser x1,y1,x2,y2 enteros: {texto!r}") from e
    ancho, alto = LADO_MASTER_HISTORIA
    _exigir(0 <= x1 < x2 <= ancho and 0 <= y1 < y2 <= alto, f"--zona fuera del máster de {ancho}×{alto}: {texto!r}")
    return x1, y1, x2, y2


def _codigo_compartir(paso: str):
    return (lambda res: 0 if res["estado"] == "confirmado" else 5) if paso == "compartir" else (lambda res: 0)


def cmd_ig_historia(a) -> int:
    from labkit import instagram_historia as igh
    ev = _evidencia(a.run)
    subidas = _subidas(a.subido_en)
    zona = _zona(a.zona)
    if a.paso in ("abrir", "elegir"):
        _exigir(len(subidas) == 1, f"{a.paso} exige un --subido-en (lo devuelve telefono-subir)")
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    if a.paso == "sticker-musica":
        _exigir(zona is not None and bool(a.tema), "sticker-musica exige --zona y --tema")
    pasos_ = {
        "abrir": lambda: igh.abrir(ev, subidas[0]),
        "elegir": lambda: igh.elegir(ev, subidas[0]),
        "audio": lambda: igh.audio(ev),
        "sticker-musica": lambda: igh.sticker_musica(ev, zona, a.tema),
        "destino": lambda: igh.destino(ev),
        "compartir": lambda: igh.compartir(ev, produccion_cercana=a.produccion_cercana),
        "actividad": lambda: igh.actividad(ev),
    }
    return _paso_telefono(ev, f"igh-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))


def _parser_flujo(sub, nombre: str, pasos_: tuple[str, ...], func):
    """Subcomando de un flujo de teléfono de la fase 2 con los argumentos comunes."""
    p = sub.add_parser(nombre)
    p.add_argument("paso", choices=pasos_)
    p.add_argument("--run", required=True)
    p.add_argument("--subido-en", action="append", help="subido_en de telefono-subir (repetible y en orden)")
    p.add_argument("--pie", help="archivo del pie o del texto")
    p.add_argument("--tema", help="tema que devolvió el paso de audio o música")
    p.add_argument("--produccion-cercana", action="store_true", help="solo en compartir")
    p.add_argument("--encuesta", help='JSON {"pregunta": "…", "opciones": ["…", "…"]}')
    p.add_argument("--zona", help="x1,y1,x2,y2 en píxeles del máster de 1080×1920")
    p.add_argument("--fotogramas", type=int, default=1, help="imágenes del carrusel o de la secuencia")
    p.set_defaults(func=func)
    return p
```

y en `construir`, antes de `return ap`:

```python
    _parser_flujo(sub, "ig-historia", PASOS_IG_HISTORIA, cmd_ig_historia)
```

En `recetas.py`, añadir antes de `TODAS`:

```python
HISTORIA_INSTAGRAM = {
    "subcomando": "ig-historia",
    "superficie": "story",
    "formato_encargo": {"ancho": 1080, "alto": 1920},
    "preparar": [
        _cmd("telefono-subir", "--local", "<master>", ver="JSON con sha256 y subido_en; no hay captura", anota=("subido_en",)),
        _cmd("ig-historia", "abrir", "--run", "<run>", "--subido-en", "<subido_en>",
             ver="igh-01-selector.png: selector de Story con la miniatura de la subida"),
        _cmd("ig-historia", "elegir", "--run", "<run>", "--subido-en", "<subido_en>",
             ver="igh-02-editor.png: editor de la Story con la imagen completa"),
        _cmd("ig-historia", "audio", "--run", "<run>", ver="igh-03-audio.png: audio del chip añadido, sin sticker grande",
             anota=("tema",)),
        _cmd("ig-historia", "destino", "--run", "<run>",
             ver="igh-04-destino.png: «Vos stories» elegido y «Amis proches» sin marcar (captura de la QA)",
             anota=("copia_facebook",)),
    ],
    "publicar": [
        _cmd("ig-historia", "compartir", "--run", "<run>", "[--produccion-cercana]",
             ver="igh-06-visor.png: story propia con cabecera sabiduriabolsillo, edad ≤ 3 min y «Activité»; "
                 "--produccion-cercana solo si el preflight trae una Story de Instagram de producción en el margen"),
    ],
    "verificar": [],
    "estados_ok": ["confirmado"],
    "conciliacion": ("Con confirmado_sin_prueba_unica, pasa al revisor igh-06-visor.png y el máster: ¿es esta imagen? "
                     "Con sin_confirmacion, timeout o fallido, abre la story propia con ig-historia actividad y compárala "
                     "con el máster antes de registrar; nunca por la otra ruta."),
    "copias": [{"red": "facebook", "superficie": "story",
                "nota": "si copia_facebook es true, la Story sale también en la de la Página: publication.cross_posting"}],
    "verificacion": ("Captura del visor propio; métricas en la primera ventana con la Story entre 4 h y 20 h o, "
                     "si no hubo, en la última antes de 24 h (paso 8 del prompt)."),
    "nota": "story_image: audio del chip sin sticker grande.",
}

HISTORIA_INSTAGRAM_MUSICA = {
    **HISTORIA_INSTAGRAM,
    "formato_encargo": {"ancho": 1080, "alto": 1920, "zona_reservada": [140, 760, 940, 1360]},
    "preparar": HISTORIA_INSTAGRAM["preparar"][:4] + [
        _cmd("ig-historia", "sticker-musica", "--run", "<run>", "--zona", "<zona_reservada>", "--tema", "<tema>",
             ver="igh-03b-sticker-musica.png: sticker del tema dentro de la zona reservada sin tapar texto"),
    ] + HISTORIA_INSTAGRAM["preparar"][4:],
    "nota": "story_image_music: además del audio, el sticker de música visible dentro de la zona reservada.",
}
```

y añadir a `TODAS`:

```python
    ("instagram", "story_image"): HISTORIA_INSTAGRAM,
    ("instagram", "story_image_music"): HISTORIA_INSTAGRAM_MUSICA,
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.` (la sección 15 comprueba también que `ig-historia` y sus pasos existen en `lab.py`).

```bash
git add experiments/media-lab/lab.py experiments/media-lab/labkit/recetas.py tests/test_media_lab.py
git commit -m "media lab claude: lab.py ig-historia y recetas de Story de Instagram en borrador

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 3: Prompt de la ventana**

Añadir al final de `seccion_prompt_ventana`:

```python
    for fragmento in ("ig-historia actividad",):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «el prompt de la ventana menciona …» para esos fragmentos.

En `experiments/media-lab/claude-ventana-prompt.md`:

Tras la frase «y guárdalas en sus runs.» del paso 8, añadir:

```markdown
 Story de Instagram sin métricas por otra vía y con el teléfono listo: `lab.py ig-historia actividad --run RUN` y lee la captura; si tampoco, anótalo en `missing_data_reasons` del run.
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana mide las Stories de Instagram por teléfono con ig-historia actividad

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 4: Actualizar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno» y «ig-historia actividad».

---

### Task 11d: A. Story de Instagram — ventana manual y promoción

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/findings.md`, `experiments/media-lab/coverage.json`, `experiments/media-lab/runs/<run>.json`, `experiments/media-lab/progress.md`, `tests/test_media_lab.py`
- Create: `tests/fixtures/telefono/instagram/historia-visor-propio.xml` (y `historia-destino.xml` si S1 no lo volcó)

- [ ] **Step 1: Primera publicación en ventana manual (`instagram/story_image`)**

Con el usuario presente y el teléfono listo, sin confirmación humana antes de publicar (basta el PASS de QA):

1. Elegir la celda `ready` (o, si no hay, la primera `planned`) de `instagram/story_image/android_native`:
   Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python -c "import json;print([(c['cell_id'],c['status']) for c in json.load(open('experiments/media-lab/coverage.json'))['cells'] if (c['platform'],c['native_format'],c['publishing_route'])==('instagram','story_image','android_native')])"`
2. Si no tiene encargo aprobado: `lab.py encargo-nuevo --borrador --cell <id> --family <familia del brief> --brief <brief> --formato '{"ancho":1080,"alto":1920}' --prompt-file <archivo en results/>`, generarlo (automatización de Codex o `lab.py generar`) y revisarlo como en el paso 4 del prompt.
3. Seguir el prompt de la ventana a mano. En la ventana manual se omiten los pasos 0, 1 y 10 del prompt (el cerrojo manual del bloque común sustituye al paso 1; en el paso 7 se renueva con `--dueno manual`), y en el paso 7b se usa `lab.py receta --celda <id> --borrador`. Si S1 no volcó el destino (`ig-08`) y por eso «Partager à» no está en `NO_ENVIO`, `ig-historia destino` se niega a tocarlo: la primera vez el usuario pulsa «Partager à» a mano tras mirar la captura del editor, Claude ejecuta `lab.py sonda instagram volcar --run SONDA-F2-A --supervisada --nombre historia-destino` y lo poda con `fixture-podar --pantalla historia-destino`; si la captura confirma que solo navega al destino, «Partager à» vuelve a `NO_ENVIO` y a su prueba en el commit del Step 2. Después sigue con `ig-historia compartir`.
4. Tras `ig-historia compartir` con `confirmado`, volcar el visor real para el fixture: el usuario abre a mano la story propia desde el avatar del perfil (la sonda no toca «Votre story») y Claude ejecuta `lab.py sonda instagram volcar --run SONDA-F2-A --supervisada --nombre visor-propio` y `lab.py fixture-podar --app instagram --desde experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-A/visor-propio.xml --pantalla historia-visor-propio`.
5. Si sale 5, conciliar como dice la receta y no promover: repetir el paso en otra ventana manual.

- [ ] **Step 2: `findings.md`, promoción y ajuste de la prueba de la fase 1**

Añadir a `experiments/media-lab/findings.md`:

```markdown
## Primera Story de Instagram por teléfono (<fecha>, <run>)

- Estado `confirmado` con visor propio (edad <n> s). Copia automática en la Página: <sí/no> (`copia_facebook`).
- Tiempos de cada paso, retrasos de volcado y cualquier texto que cambió respecto a S1.
- Fixture `historia-visor-propio` volcado en esta ventana (si S1 no lo tenía).
```

En `recetas.py`, añadir a `PROMOVIDAS`:

```python
    ("instagram", "story_image"): "<run>: primera Story de Instagram por teléfono confirmada (<fecha>)",
```

En `seccion_seleccion` (fase 1), la celda `C5` (`instagram/story_image/android_native`) ya es elegible: cambiar su `native_format` a `"reel_video"` y la etiqueta del check que la usa a `"el teléfono no publica pares sin receta promovida (vídeo)"`. Añadir al final de `seccion_instagram_historia`:

```python
    check(("instagram", "story_image") in RC.RECETAS, "A: story_image promovida tras su ventana manual")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

Si el Step 1 devolvió «Partager à» a `NO_ENVIO`, añadir también `experiments/media-lab/labkit/textos.py` y `tests/fixtures/telefono/instagram/historia-destino.xml` al `git add`.

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/findings.md experiments/media-lab/coverage.json experiments/media-lab/runs/<run>.json experiments/media-lab/progress.md tests/test_media_lab.py tests/fixtures/telefono/instagram/historia-visor-propio.xml
git commit -m "media lab claude: primera Story de Instagram por teléfono confirmada; story_image promovida

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

Con el push hecho, `lab.py lock-soltar --dueno manual`: la sesión edita, comitea y hace push con el cerrojo tomado.

---

### Task 12a: B. Feed de Threads — textos y lectores contra fixtures (spec, fila 6)

Usa lo común que añaden la tarea 11a (Step 5: `pantalla.miniatura_por_hora`, `edad_segundos`, `marcado_en_fila`, `estado_confirmado`) y la 11b-2 (Step 3: `pasos.lanzar_app`); `pasos.tocar` con guardia viene de la tarea 3. Va en serie después de la tarea 11d o en su propio worktree (rama aparte, rebasando sobre `origin/main` antes de cada push); nunca en el mismo árbol a la vez que la 11.

**Files:**
- Create: `experiments/media-lab/labkit/threads_pantallas.py`
- Modify: `experiments/media-lab/labkit/pantalla.py`, `experiments/media-lab/labkit/textos.py`
- Test: `tests/test_media_lab.py`; fixtures `tests/fixtures/telefono/threads/{inicio,perfil,compositor-vacio,galeria,musica,descartar-dialogo}.xml`

- [ ] **Step 1: Sonda complementaria (solo si S1 no dejó algún fixture)**

Por cada fixture de la lista **Files** que falte, repetir su tramo del Step 4 de la tarea 9 con `--run SONDA-F2-B` y podarlo con `lab.py fixture-podar --app threads --desde experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-B/<nombre>.xml --pantalla <fixture>`.

- [ ] **Step 2: Confirmar los textos de Threads contra S1**

Sustituir `TEXTOS["threads"]` en `textos.py` por este bloque, con el valor observado en la tabla de S1 cuando difiera, y ajustar `DESCARTE["threads"]`, `EDADES["threads"]` y, si las miniaturas de la galería de Threads no usan el formato «du 14 septembre 2026 10:39», la línea `lector_fecha` de `threads_pantallas.miniatura_galeria`:

```python
    "threads": {
        "publicar": "Publier",  # confirmar contra el fixture de S1
        "aviso_publicado": "Publié",  # confirmar contra el fixture de S1 (aviso tras publicar)
        "anadir": "Ajouter",  # confirmar contra el fixture de S1 (confirmación de la galería)
        "sugerencias": "Suggestions",  # confirmar contra el fixture de S1 (cabecera de la música)
        "compartir_en_instagram": "Partager aussi sur Instagram",  # confirmar contra el fixture de S1
        "fils": "Fils",  # confirmar contra el fixture de S1 (pestaña del perfil)
        "reintentar": "Réessayer",
        "echec": "Échec de la publication",  # confirmar contra el fixture de S1
    },
```

Añadir a la tupla `PATRONES_FIXTURE["threads"]` el formato de la content-desc de las miniaturas de la galería que anotó S1, para que la poda no la vacíe:

```python
    r"(?:Sélectionné |Désélectionné )?(?:Miniature de la photo|Photo|Image) du \d{1,2}(?:er)? \S+ \d{4} \d{1,2}[:h]\d{2}",  # confirmar contra el fixture de S1
```

Rellenar `DESCARTE["threads"]` con el título y el botón del diálogo de `th-10` solo si el título no está en `TITULOS_BORRADO`; si S1 solo vio un diálogo de borrado, se queda vacío y un borrador de Threads se cierra a mano (la regla del borrador abierto lo deja en el informe).

Si S1 vio «Partager aussi sur Instagram» **activo por defecto**, la receta de la tarea 12c (Step 3) declara la copia (`"copias": [{"red": "instagram", "superficie": "feed", …}]`) y la exclusión se aplica sola. Después, volver a podar con `lab.py fixture-podar --app threads` los fixtures de la lista **Files** desde sus volcados crudos de S1 (tabla del Step 8 de la tarea 9), para que conserven los textos recién confirmados.

- [ ] **Step 3: Escribir la prueba de los lectores**

Añadir antes de `SECCIONES` y registrar `seccion_threads,`:

```python
TEXTO_THREAD = "«La paciencia es amarga, pero su fruto es dulce». Jean-Jacques Rousseau lo escribió en el Emilio."


def seccion_threads() -> None:
    print("\n21. Fase 2 (B): feed de Threads")
    from datetime import timedelta
    from labkit import pantalla as P, telefono as T, threads_pantallas as TP

    perfil = fixture("threads", "perfil")
    compositor = fixture("threads", "compositor-vacio")
    check(TP.perfil_de_marca(perfil) and not TP.perfil_de_marca(compositor), "B: el perfil real es el de @sabiduriabolsillo")
    check(bool(TP.por_id(fixture("threads", "inicio"), TP.ID_PERFIL)) and bool(TP.por_id(perfil, TP.ID_CREAR)),
          "B: las pestañas de perfil y crear se encuentran por resource-id")
    check(TP.compositor_abierto(compositor) and TP.identidad_compositor(compositor) == TP.MARCA,
          "B: el compositor real publica como la marca")
    check(TP.identidad_compositor(compositor.replace('"sabiduriabolsillo"', '"cuenta.personal"')) is None,
          "B: con otra cuenta en el botón de identidad no hay identidad de marca")
    galeria = fixture("threads", "galeria")
    subida = primera_fecha(galeria, TP.lector_fecha)
    check(bool(TP.miniatura_galeria(galeria, subida)["desc"]), "B: la miniatura de la subida por hora en la galería real")
    try:
        TP.miniatura_galeria(galeria, subida + timedelta(hours=5))
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "B: sin miniatura a esa hora, PantallaInesperada")
    musica = fixture("threads", "musica")
    fila = next(n for n in T.nodos(musica) if n["package"] == TP.PAQUETE and n["clickable"]
                and n["bounds"][1] >= T.buscar(musica, texto=TP.T["sugerencias"])["bounds"][3])
    musica_con_tema = con_nodo(musica, nodo_xml("[%d,%d][%d,%d]" % (fila["bounds"][0] + 1, fila["bounds"][1] + 1,
                                                                    fila["bounds"][0] + 400, fila["bounds"][1] + 40),
                                                texto="Autumn Days", paquete=TP.PAQUETE))
    check(TP.tema_sugerido(musica_con_tema)["tema"].startswith("Autumn Days"), "B: el primer tema sugerido de la lista real")
    dialogo_th = fixture("threads", "descartar-dialogo")
    if TP.textos.DESCARTE["threads"]["titulos"]:
        check(P.boton_descarte(dialogo_th, "threads")["texto"] in TP.textos.DESCARTE["threads"]["botones"],
              "B: el diálogo de descarte real se reconoce")
    else:
        try:
            P.boton_descarte(dialogo_th, "threads")
            ok = False
        except P.PantallaInesperada:
            ok = True
        check(ok, "B: sin diálogo de descarte de Threads confirmado, telefono-descartar no pulsa nada")

    con_texto = con_valor(compositor, lambda n: n["resource_id"].endswith("/" + TP.ID_COMPOSITOR), TEXTO_THREAD)
    listo = con_valor(con_texto, lambda n: n["resource_id"].endswith("/" + TP.ID_PUBLICAR), "true", "enabled")
    check(TP.compositor_listo(listo, TEXTO_THREAD, False, None) == [], f"B: compositor listo ({TP.compositor_listo(listo, TEXTO_THREAD, False, None)})")
    check(any("texto" in p for p in TP.compositor_listo(listo, TEXTO_THREAD + ".", False, None)),
          "B: un texto parecido no vale")
    check(any("imagen" in p for p in TP.compositor_listo(listo, TEXTO_THREAD, True, None)), "B: con imagen pedida y sin adjunto no está listo")
    sugerencias = [{"nombre": "PopupWindow:sugerencias", "frame": None, "ancho_padre": None}]
    check(any("PopupWindow:sugerencias" in p for p in TP.compositor_listo(listo, TEXTO_THREAD, False, None, sugerencias)),
          "B: una ventana emergente de sugerencias sobre el compositor impide publicar")

    perfil_con_thread = con_nodo(con_nodo(perfil, nodo_xml("[900,1940][1040,1990]", texto="1 min", paquete=TP.PAQUETE)),
                                 nodo_xml("[40,2000][1040,2100]", texto=TEXTO_THREAD, paquete=TP.PAQUETE))
    lectura = TP.thread_reciente(perfil_con_thread, TEXTO_THREAD)
    check(lectura["ok"] and lectura["edad_s"] == 60, f"B: el primer thread del perfil con el texto exacto y 1 min ({lectura})")
    check(not TP.thread_reciente(perfil_con_thread, TEXTO_THREAD[:-1])["ok"], "B: con un texto parecido no confirma")
    viejo = perfil_con_thread.replace('text="1 min"', 'text="4 h"')
    check(not TP.thread_reciente(viejo, TEXTO_THREAD)["ok"], "B: un thread de hace 4 h no confirma")
    publicado = con_nodo(fixture("threads", "inicio"), nodo_xml("[0,2000][1080,2100]", texto=TP.T["aviso_publicado"], paquete=TP.PAQUETE))
    obs = TP.observacion(publicado)
    check(obs["valido"] and obs["banner"] and not obs["compositor"] and not obs["fallo"], "B: el aviso de publicado cuenta como banner")
    check(TP.observacion(listo)["compositor"], "B: el compositor abierto cuenta como compositor")
```

- [ ] **Step 4: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'threads_pantallas' from 'labkit'` en la sección 21.

- [ ] **Step 5: Implementar `pantalla.por_id` y `threads_pantallas.py`**

En `pantalla.py`, añadir tras `nodo`:

```python
def por_id(xml: str, paquete: str, rid: str) -> list[dict]:
    """Nodos de `paquete` cuyo resource-id termina en «/rid» (o es `rid`)."""
    return [n for n in telefono.buscar_todos(xml, paquete=paquete) if n["resource_id"].rsplit("/", 1)[-1] == rid]
```

y al final de `pantalla.py` lo que comparten Threads y Facebook:

```python
LARGO_AVISO_CORTO = 80
LADO_MINIMO_IMAGEN_PX = 150


def imagen_bajo(xml: str, paquete: str, bounds_campo: tuple[int, int, int, int],
                lado_minimo: int = LADO_MINIMO_IMAGEN_PX) -> bool:
    """Hay una imagen adjunta de `paquete` (ImageView de al menos `lado_minimo` px de lado) bajo el
    borde superior del campo del compositor."""
    return any(n["clase"].endswith("ImageView") and n["bounds"][1] >= bounds_campo[1]
               and min(n["bounds"][2] - n["bounds"][0], n["bounds"][3] - n["bounds"][1]) >= lado_minimo
               for n in telefono.buscar_todos(xml, paquete=paquete))


def tema_bajo_cabecera(xml: str, paquete: str, cabecera: str) -> dict:
    """{"nodo", "tema"}: la primera fila pulsable con texto bajo `cabecera` (lista de música sugerida);
    el tema son sus dos primeros textos unidos por « · » (título · artista)."""
    cab = telefono.buscar(xml, texto=cabecera, paquete=paquete)
    if cab is None:
        raise PantallaInesperada(f"no aparece «{cabecera}»")
    lista = telefono.nodos(xml)
    for fila in (n for n in lista if n["package"] == paquete and n["clickable"] and n["bounds"][1] >= cab["bounds"][3]):
        textos_fila = [m["texto"] for m in lista if m["package"] == paquete and m["texto"]
                       and dentro(m["bounds"], fila["bounds"])]
        if textos_fila:
            return {"nodo": fila, "tema": " · ".join(textos_fila[:2])}
    raise PantallaInesperada(f"no hay temas bajo «{cabecera}»")


def aviso_corto(xml: str, paquete: str, marcas: tuple[str, ...]) -> dict | None:
    """El primer texto corto (≤ LARGO_AVISO_CORTO) de `paquete`, fuera de un campo, con una marca de fallo."""
    return next((n for n in telefono.buscar_todos(xml, paquete=paquete) if n["clase"] not in CLASES_CAMPO
                 and any(m in v and len(v) <= LARGO_AVISO_CORTO for m in marcas for v in (n["texto"], n["desc"]) if v)),
                None)


def observacion_envio(xml: str, paquete: str, compositor: bool, avisos: tuple[str, ...],
                      marcas_fallo: tuple[str, ...]) -> dict:
    """Observación tras pulsar, para `evaluar_envio`: `compositor` lo decide quien llama, `banner` si algún
    texto empieza por uno de `avisos` y `fallo` con un aviso corto de error."""
    propios = telefono.buscar_todos(xml, paquete=paquete)
    banner = any(v.startswith(a) for n in propios for v in (n["texto"], n["desc"]) if v for a in avisos)
    culpable = aviso_corto(xml, paquete, marcas_fallo)
    return {"valido": bool(propios), "compositor": compositor, "banner": banner, "fallo": culpable is not None,
            "fallo_texto": (culpable["texto"] or culpable["desc"])[:100] if culpable else None,
            "fallo_bounds": culpable["bounds"] if culpable else None}
```

`experiments/media-lab/labkit/threads_pantallas.py`:

```python
"""
Lectura pura de las pantallas de Threads (flujo B de la fase 2).

Los controles del compositor se buscan por resource-id; si una actualización los cambia, los
lectores no los encuentran y el paso falla cerrado. Textos en francés.
"""
from __future__ import annotations

from datetime import datetime

from labkit import pantalla, telefono, textos
from labkit.instagram_pantallas import fecha_miniatura
from labkit.pantalla import PantallaInesperada

PAQUETE = textos.PAQUETES["threads"]
MARCA = textos.MARCAS["threads"]
T = textos.TEXTOS["threads"]
LIMITE_TEXTO = 500
ID_PERFIL = "barcelona_tab_profile"
ID_CREAR = "barcelona_tab_create"
ID_COMPOSITOR = "new_thread_screen_composer"
ID_GALERIA = "new_thread_screen_gallery_button"
ID_MUSICA = "new_thread_screen_music_button"
ID_ENCUESTA = "new_thread_screen_poll_button"
ID_PUBLICAR = "new_thread_screen_post_button"
lector_fecha = fecha_miniatura  # confirmar contra el fixture de S1 (formato de fecha de la galería)


def por_id(xml: str, rid: str) -> list[dict]:
    return pantalla.por_id(xml, PAQUETE, rid)


def nodo_id(xml: str, rid: str) -> dict:
    nodos = por_id(xml, rid)
    if not nodos:
        raise PantallaInesperada(f"Threads no muestra {rid}")
    return pantalla.elegir(nodos, rid)


def perfil_de_marca(xml: str) -> bool:
    """El perfil muestra @marca en el tercio superior."""
    alto = pantalla.alto_volcado(xml)
    return any(n["texto"] == MARCA and n["bounds"][3] * 3 <= alto for n in telefono.buscar_todos(xml, paquete=PAQUETE))


def compositor_abierto(xml: str) -> bool:
    return bool(por_id(xml, ID_COMPOSITOR))


def identidad_compositor(xml: str) -> str | None:
    """MARCA si el botón de identidad del compositor es el de la marca; None en otro caso."""
    return MARCA if any(n["clase"].endswith("Button") and MARCA in (n["texto"], n["desc"])
                        for n in telefono.buscar_todos(xml, paquete=PAQUETE)) else None


def adjunto_imagen(xml: str) -> bool:
    """Hay una imagen adjunta bajo el campo del compositor."""
    campo = por_id(xml, ID_COMPOSITOR)
    return bool(campo) and pantalla.imagen_bajo(xml, PAQUETE, campo[0]["bounds"])  # confirmar contra el fixture de S1


def compositor_listo(xml: str, texto: str | None, con_imagen: bool, tema: str | None,
                     emergentes: list[dict] | None = None) -> list[str]:
    """Problemas que impiden publicar; lista vacía = listo. `emergentes` (`telefono.ventanas_emergentes`)
    detecta sugerencias abiertas como ventana aparte que el volcado no muestra."""
    problemas = []
    if not compositor_abierto(xml):
        problemas.append("no está el compositor de Threads")
    if identidad_compositor(xml) != MARCA:
        problemas.append(f"el compositor no publica como @{MARCA}")
    if texto is not None and not pantalla.tiene_texto(xml, texto=texto, paquete=PAQUETE):
        problemas.append("el texto del teléfono no coincide con el archivo")
    if con_imagen and not adjunto_imagen(xml):
        problemas.append("no hay imagen adjunta")
    if tema:
        titulo = tema.split(" · ")[0]
        if not any(titulo == n["texto"] or titulo in n["desc"] for n in telefono.buscar_todos(xml, paquete=PAQUETE)):
            problemas.append(f"no aparece el tema «{titulo}»")
    botones = por_id(xml, ID_PUBLICAR)
    if not botones:
        problemas.append("no hay botón de publicar")
    elif any(telefono.tapado(xml, b) for b in botones):
        problemas.append("el botón de publicar está tapado")
    elif not all(b["enabled"] for b in botones):
        problemas.append("el botón de publicar no está activo")
    if pantalla.hay_desplegable(xml, PAQUETE, prefijo="#") or pantalla.hay_desplegable(xml, PAQUETE, prefijo="@"):
        problemas.append("sugerencias abiertas")
    culpable = emergente_compositor(xml, emergentes or [])
    if culpable is not None:
        problemas.append(f"sugerencias abiertas ({pantalla.describe_emergente(culpable)})")
    return problemas


def emergente_compositor(xml: str, emergentes: list[dict]) -> dict | None:
    """Ventana emergente (sugerencias de menciones o hashtags que `uiautomator dump` puede no ver) que se
    solapa con el campo del compositor o con el botón de publicar."""  # confirmar contra el fixture de S1
    referencias = [n["bounds"] for n in por_id(xml, ID_COMPOSITOR) + por_id(xml, ID_PUBLICAR)]
    return pantalla.emergente_solapada(emergentes, referencias)


def miniatura_galeria(xml: str, subido_en: datetime) -> dict:
    return pantalla.miniatura_por_hora(xml, PAQUETE, subido_en, lector_fecha)


def tema_sugerido(xml: str) -> dict:
    return pantalla.tema_bajo_cabecera(xml, PAQUETE, T["sugerencias"])


def copia_instagram(xml: str) -> bool | None:
    """Estado del conmutador «Partager aussi sur Instagram» si aparece; no se cambia."""
    return pantalla.marcado_en_fila(xml, PAQUETE, T["compartir_en_instagram"])


def observacion(xml: str, boton_bounds: tuple[int, int, int, int] | None = None) -> dict:
    th = telefono.buscar_todos(xml, paquete=PAQUETE)
    compositor = any(n["resource_id"].endswith("/" + ID_COMPOSITOR) for n in th) or (
        boton_bounds is not None and any(n["resource_id"].endswith("/" + ID_PUBLICAR) and n["bounds"] == tuple(boton_bounds) for n in th))
    return pantalla.observacion_envio(xml, PAQUETE, compositor, (T["aviso_publicado"],), (T["reintentar"], T["echec"]))


def thread_reciente(xml: str, texto: str, max_s: int = 180) -> dict:
    """{"ok", "problemas", "edad_s"} del perfil: el primer cuerpo de thread bajo la pestaña «Fils»
    (primer texto de 20 caracteres o más que no es de la interfaz, ni la marca, ni una edad) es
    exactamente `texto` y la edad más cercana por encima es ≤ max_s. El texto exacto identifica el
    thread: la producción cercana no rebaja el estado."""
    th = telefono.buscar_todos(xml, paquete=PAQUETE)
    pestana = next((n for n in th if T["fils"] in (n["texto"], n["desc"])), None)
    desde = pestana["bounds"][3] if pestana else 0
    conocidos = textos.conocidos("threads")
    cuerpos = [n for n in th if n["bounds"][1] >= desde and len(n["texto"]) >= 20 and n["texto"] not in conocidos
               and pantalla.edad_segundos(n["texto"], "threads") is None]
    problemas = []
    primero = cuerpos[0] if cuerpos else None
    if primero is None or primero["texto"] != texto:
        problemas.append("el primer thread del perfil no tiene el texto exacto")
    edades = [e for n in th if primero is not None and desde <= n["bounds"][1] and n["bounds"][3] <= primero["bounds"][1]
              and (e := pantalla.edad_segundos(n["texto"], "threads")) is not None]
    edad = edades[-1] if edades else None
    if edad is None:
        problemas.append("no se lee la edad del thread")
    elif edad > max_s:
        problemas.append(f"el thread tiene {edad} s (máximo {max_s})")
    return {"ok": not problemas, "problemas": problemas, "edad_s": edad}
```

- [ ] **Step 6: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 21 en `✓` y `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/pantalla.py experiments/media-lab/labkit/textos.py experiments/media-lab/labkit/threads_pantallas.py tests/test_media_lab.py
git commit -m "media lab claude: lectores de Threads por resource-id probados contra los fixtures de S1

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12b: B. Feed de Threads — pasos con teléfono simulado

**Files:**
- Create: `experiments/media-lab/labkit/threads_feed.py`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de los pasos de Threads**

Añadir al final de `seccion_threads`:

```python
    print("   · pasos de Threads con teléfono simulado")
    import pathlib as _p
    from labkit import pasos, threads_feed as TH

    evid = _p.Path("evidencia-simulada")
    inicio = fixture("threads", "inicio")
    tab_perfil = TP.nodo_id(inicio, TP.ID_PERFIL)["centro"]
    sim = TelefonoSimulado([inicio, perfil])
    res, err = con_telefono_simulado(sim, lambda: TH.abrir(evid))
    check(err is None and sim.toques == [tab_perfil] and sim.capturas == ["th-01-perfil.png"]
          and sim.orden == ["cortina", f"lanzar:{TP.PAQUETE}"], f"B abrir: pestaña de perfil y marca ({err!r}, {sim.toques})")
    ajeno = perfil.replace('"sabiduriabolsillo"', '"cuenta.personal"')
    sim = TelefonoSimulado([inicio, ajeno])
    res, err = con_telefono_simulado(sim, lambda: TH.abrir(evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [tab_perfil],
          f"B abrir con otra cuenta: ningún toque de composición ({err!r})")
    sim = TelefonoSimulado([compositor])
    res, err = con_telefono_simulado(sim, lambda: TH.abrir(evid))
    check(isinstance(err, pasos.BorradorPendiente) and sim.toques == [], "B abrir con un thread a medias: BorradorPendiente sin tocar")

    sim = TelefonoSimulado([perfil, compositor])
    res, err = con_telefono_simulado(sim, lambda: TH.nuevo(evid))
    check(err is None and sim.toques == [TP.nodo_id(perfil, TP.ID_CREAR)["centro"]] and sim.capturas == ["th-02-compositor.png"],
          f"B nuevo: un toque en crear y compositor con la marca ({err!r})")
    sim = TelefonoSimulado([perfil, compositor.replace('"sabiduriabolsillo"', '"cuenta.personal"')])
    res, err = con_telefono_simulado(sim, lambda: TH.nuevo(evid))
    check(isinstance(err, P.PantallaInesperada) and len(sim.toques) == 1, "B nuevo con otra identidad: se para antes de escribir")

    desplegable = con_nodo(con_texto, nodo_xml("[0,1200][1080,1300]", texto="#citas", paquete=TP.PAQUETE))
    sim = TelefonoSimulado([compositor, con_texto, desplegable, desplegable, con_texto], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: TH.texto(TEXTO_THREAD, evid))
    check(err is None and sim.pegados == [TEXTO_THREAD] and sim.teclas == [pasos.ATRAS] and sim.capturas == ["th-03-texto.png"],
          f"B texto: el desplegable del segundo volcado tras pegar se cierra con un «atrás» ({err!r}, {sim.teclas})")
    sim = TelefonoSimulado([compositor], listo=False)
    res, err = con_telefono_simulado(sim, lambda: TH.texto(TEXTO_THREAD, evid))
    check(isinstance(err, pasos.TelefonoNoListo) and sim.pegados == [] and sim.toques == [], "B texto con el teléfono no listo: nada")
    for nombre_paso, guion_paso, accion in (
            ("abrir", [inicio, perfil], lambda: TH.abrir(evid)),
            ("nuevo", [perfil, compositor], lambda: TH.nuevo(evid)),
            ("texto", [compositor, con_texto, desplegable, desplegable, con_texto], lambda: TH.texto(TEXTO_THREAD, evid))):
        sim = TelefonoSimulado(guion_paso, teclado=(False,))
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and not toques_sobre_envio(sim, TP.PAQUETE),
              f"C1 B {nombre_paso}: fuera de compartir, ningún toque cae sobre un control de envío ({err!r}, {sim.toques})")
    campo_c = TP.por_id(compositor, TP.ID_COMPOSITOR)[0]["bounds"]
    con_imagen = con_nodo(compositor, nodo_xml(f"[40,{campo_c[1] + 50}][440,{campo_c[1] + 450}]", clase="android.widget.ImageView",
                                               paquete=TP.PAQUETE))
    con_tema = con_nodo(compositor, nodo_xml("[40,1900][600,1960]", texto="Autumn Days", paquete=TP.PAQUETE))
    for nombre_paso, guion_paso, accion in (
            ("galeria", [compositor, galeria, galeria, con_imagen, con_imagen, con_imagen], lambda: TH.galeria(evid, subida)),
            ("musica", [compositor, musica_con_tema, con_tema, con_tema, con_tema], lambda: TH.musica(evid))):
        sim = TelefonoSimulado(guion_paso)
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and not toques_sobre_envio(sim, TP.PAQUETE),
              f"C1 B {nombre_paso}: camino feliz sin tocar controles de envío ({err!r}, {sim.toques})")

    publicar = TP.nodo_id(listo, TP.ID_PUBLICAR)["centro"]
    perfil_con_thread_tab = perfil_con_thread
    guion = [listo, listo, listo, publicado, inicio, inicio, inicio, perfil_con_thread_tab]
    sim = TelefonoSimulado(guion)
    res, err = con_telefono_simulado(sim, lambda: TH.compartir(TEXTO_THREAD, None, False, evid))
    check(err is None and res["estado"] == "confirmado" and sim.toques.count(publicar) == 1 and sim.toques[0] == publicar
          and res["perfil"]["ok"] and sim.capturas == ["th-06a-antes.png", "th-07-perfil.png"],
          f"B compartir: exactamente un toque en publicar y el thread exacto en el perfil ({err!r}, {res and res['estado']})")
    sim = TelefonoSimulado(guion)
    res, err = con_telefono_simulado(sim, lambda: TH.compartir(TEXTO_THREAD, None, False, evid, produccion_cercana=True))
    check(err is None and res["estado"] == "confirmado" and any("hilos" in a for a in res["avisos"]),
          "B compartir con producción cercana: el texto exacto identifica y no rebaja el estado")
    sim = TelefonoSimulado([listo, listo, listo, con_nodo(inicio, nodo_xml("[0,300][1080,380]", texto=TP.T["reintentar"], paquete=TP.PAQUETE)),
                            inicio, perfil])
    res, err = con_telefono_simulado(sim, lambda: TH.compartir(TEXTO_THREAD, None, False, evid))
    check(err is None and res["estado"] == "fallido" and sim.toques.count(publicar) == 1, "B compartir con «Réessayer»: fallido y un toque")
    sim = TelefonoSimulado([listo], emergentes=(sugerencias,))
    res, err = con_telefono_simulado(sim, lambda: TH.compartir(TEXTO_THREAD, None, False, evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "B compartir con sugerencias como ventana emergente: no se pulsa")
    campo_th = TP.por_id(con_texto, TP.ID_COMPOSITOR)[0]["bounds"]
    tooltip = [{"nombre": "PopupWindow:tooltip", "frame": (400, campo_th[1], 500, campo_th[1] + 40), "ancho_padre": 1080}]
    sim = TelefonoSimulado([compositor, con_texto, con_texto], teclado=(False,), emergentes=(tooltip,))
    res, err = con_telefono_simulado(sim, lambda: TH.texto(TEXTO_THREAD, evid))
    check(isinstance(err, P.PantallaInesperada) and sim.teclas == [] and "PopupWindow:tooltip" in str(err),
          "B texto: una emergente estrecha que se solapa con el compositor para sin pulsar «atrás»")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'threads_feed' from 'labkit'`.

- [ ] **Step 3: Implementar `threads_feed.py`**

```python
"""
Feed de Threads por teléfono, un paso por llamada (flujo B de la fase 2).

abrir → nuevo → texto → [galeria → musica] → QA → compartir. La URL y el post_id se completan
después con `media-lab-verify -f buscar=threads` (solo lectura).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from labkit import pantalla, pasos, reloj, telefono
from labkit import threads_pantallas as tp
from labkit.pantalla import PantallaInesperada


def _exigir_compositor(xml: str, texto: str) -> None:
    faltan = []
    if not tp.compositor_abierto(xml):
        faltan.append("compositor")
    if tp.identidad_compositor(xml) != tp.MARCA:
        faltan.append("identidad de marca")
    if not pantalla.tiene_texto(xml, texto=texto, paquete=tp.PAQUETE):
        faltan.append("texto exacto")
    if faltan:
        raise PantallaInesperada(f"tras pegar el texto falta: {faltan}")


def abrir(evidencia: Path) -> dict:
    xml = pasos.lanzar_app(tp.PAQUETE, "threads", listo=lambda x: bool(tp.por_id(x, tp.ID_PERFIL)),
                           borrador=tp.compositor_abierto, descripcion="Threads listo (pestaña de perfil)")
    pasos.tocar(tp.nodo_id(xml, tp.ID_PERFIL), xml, tp.PAQUETE)
    pasos.esperar_que(tp.perfil_de_marca, f"el perfil de @{tp.MARCA}", app="threads")
    return {"captura": str(telefono.captura(evidencia / "th-01-perfil.png"))}


def nuevo(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: bool(tp.por_id(x, tp.ID_CREAR)), "el botón de crear", app="threads")
    pasos.tocar(tp.nodo_id(xml, tp.ID_CREAR), xml, tp.PAQUETE)
    xml, _ = pasos.esperar_estable(tp.compositor_abierto, descripcion="el compositor de Threads")
    if tp.identidad_compositor(xml) != tp.MARCA:
        raise PantallaInesperada(f"el compositor de Threads no publica como @{tp.MARCA}")
    return {"copia_instagram": tp.copia_instagram(xml), "captura": str(telefono.captura(evidencia / "th-02-compositor.png"))}


def texto(texto_: str, evidencia: Path) -> dict:
    if not 0 < len(texto_) <= tp.LIMITE_TEXTO:
        raise ValueError(f"el texto de Threads tiene {len(texto_)} caracteres (1–{tp.LIMITE_TEXTO})")
    pasos.escribir_texto(texto_, tp.PAQUETE, campo=lambda x: (tp.por_id(x, tp.ID_COMPOSITOR) or [None])[0],
                         exigir=lambda x: _exigir_compositor(x, texto_),
                         desplegable_nodos=lambda x: pantalla.hay_desplegable(x, tp.PAQUETE, prefijo="#")
                         or pantalla.hay_desplegable(x, tp.PAQUETE, prefijo="@"),
                         emergente=tp.emergente_compositor)
    return {"captura": str(telefono.captura(evidencia / "th-03-texto.png"))}


def _hay_miniatura(xml: str, subido_en: datetime) -> bool:
    try:
        tp.miniatura_galeria(xml, subido_en)
        return True
    except PantallaInesperada:
        return False


def galeria(evidencia: Path, subido_en: datetime) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: bool(tp.por_id(x, tp.ID_GALERIA)), "el botón de galería", app="threads")
    pasos.tocar(tp.nodo_id(xml, tp.ID_GALERIA), xml, tp.PAQUETE)
    xml = pasos.esperar_que(lambda x: _hay_miniatura(x, subido_en), "la miniatura de la subida", app="threads")
    pasos.tocar(tp.miniatura_galeria(xml, subido_en), xml, tp.PAQUETE)
    reloj.dormir(1)
    xml = pasos.volcado_fresco()
    anadir = telefono.buscar_todos(xml, texto=tp.T["anadir"], paquete=tp.PAQUETE)
    if anadir:
        pasos.tocar(pantalla.elegir(anadir, tp.T["anadir"]), xml, tp.PAQUETE)
    pasos.esperar_estable(lambda x: tp.compositor_abierto(x) and tp.adjunto_imagen(x), descripcion="el compositor con la imagen")
    return {"captura": str(telefono.captura(evidencia / "th-04-imagen.png"))}


def musica(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: bool(tp.por_id(x, tp.ID_MUSICA)), "el botón de música", app="threads")
    pasos.tocar(tp.nodo_id(xml, tp.ID_MUSICA), xml, tp.PAQUETE)
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=tp.T["sugerencias"], paquete=tp.PAQUETE) is not None,
                            "la música sugerida", app="threads")
    sugerido = tp.tema_sugerido(xml)
    pasos.tocar(sugerido["nodo"], xml, tp.PAQUETE)
    titulo = sugerido["tema"].split(" · ")[0]
    pasos.esperar_estable(lambda x: tp.compositor_abierto(x) and any(titulo == n["texto"] or titulo in n["desc"]
                                                                     for n in telefono.buscar_todos(x, paquete=tp.PAQUETE)),
                          descripcion="el compositor con el tema")
    return {"tema": sugerido["tema"], "captura": str(telefono.captura(evidencia / "th-05-musica.png"))}


def compartir(texto_: str, tema: str | None, con_imagen: bool, evidencia: Path, produccion_cercana: bool = False) -> dict:
    """Pulsa publicar una sola vez y confirma con el primer thread del perfil (texto exacto, edad ≤ 3 min).

    Estados: «confirmado», «sin_confirmacion», «timeout», «fallido» y «error_tras_pulsar». La
    producción cercana (`hilos`) se anota y no rebaja: el texto exacto identifica el thread."""
    pasos.exigir_listo()
    copia = tp.copia_instagram(pasos.volcado_fresco())

    def despues(resultado: dict, estado: str) -> str:
        avisos = resultado["avisos"]
        if produccion_cercana:
            avisos.append("producción (hilos) publicó cerca: el texto exacto identifica el thread y no rebaja el estado")
        lectura = None
        try:
            if telefono.estado()["listo"]:
                xml = pasos.esperar_que(lambda x: bool(tp.por_id(x, tp.ID_PERFIL)), "la pestaña de perfil", app="threads")
                pasos.tocar(tp.nodo_id(xml, tp.ID_PERFIL), xml, tp.PAQUETE)
                xml, _ = pasos.esperar_estable(lambda x: tp.perfil_de_marca(x) and tp.thread_reciente(x, texto_)["ok"],
                                               descripcion="el thread nuevo en el perfil")
                lectura = tp.thread_reciente(xml, texto_)
            else:
                avisos.append("tras publicar el teléfono no está listo: no se leyó el perfil")
        except (PantallaInesperada, telefono.TelefonoError) as e:
            avisos.append(f"no se leyó el thread nuevo en el perfil: {e}")
        resultado["perfil"] = lectura
        return pantalla.estado_confirmado(estado, lectura, False, avisos)

    return pasos.enviar(
        paquete=tp.PAQUETE, nombre_app="Threads", etiqueta=tp.ID_PUBLICAR, evidencia=evidencia,
        captura_antes="th-06a-antes.png", captura_final="th-07-perfil.png", captura_error="th-06-error.png",
        listo=lambda x, emergentes: tp.compositor_listo(x, texto_, con_imagen, tema, emergentes),
        botones=lambda x: tp.por_id(x, tp.ID_PUBLICAR),
        observador_nuevo=lambda boton: (lambda x: tp.observacion(x, boton["bounds"])),
        despues=despues, extra={"perfil": None, "copia_instagram": copia})
```

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/threads_feed.py tests/test_media_lab.py
git commit -m "media lab claude: pasos del feed de Threads con un solo toque en publicar y texto exacto en el perfil

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12c: B. Feed de Threads — `lab.py th`, recetas en borrador y prompt

**Files:**
- Modify: `experiments/media-lab/lab.py`, `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/labkit/seleccion.py`, `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Prueba de `lab.py th` y de las recetas de Threads**

Añadir al final de `seccion_threads`:

```python
    print("   · lab.py th y recetas de Threads")
    import tempfile as _tf
    from labkit import recetas as RC

    with entorno_lab_fase2() as (lab, raiz):
        largo = raiz / "largo.txt"
        largo.write_text("x" * 501, encoding="utf-8")
        for args, fragmento, label in ((("th", "texto", "--run", "R"), "--pie", "texto sin --pie"),
                            (("th", "texto", "--run", "R", "--pie", largo), "máximo 500", "un texto de más de 500"),
                            (("th", "galeria", "--run", "R"), "--subido-en", "galeria sin --subido-en"),
                            (("th", "nuevo", "--run", "R", "--produccion-cercana"), "--produccion-cercana", "--produccion-cercana fuera de compartir")):
            sim = TelefonoSimulado([perfil])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0, f"th rechaza {label} sin tocar el teléfono ({res and res[0]})")
    for par in (("threads", "feed_single_image"), ("threads", "feed_text"), ("threads", "feed_image_music")):
        check(par in RC.TODAS and RC.TODAS[par]["subcomando"] == "th", f"B: receta de {par}")
    texto_receta = RC.TODAS[("threads", "feed_text")]
    check(not any(c["args"][0] == "telefono-subir" or c["args"][1:2] in (["galeria"], ["musica"]) for c in texto_receta["preparar"]),
          "B: feed_text no sube imagen ni añade música")
    check(any(c["args"][:2] == ["th", "musica"] for c in RC.TODAS[("threads", "feed_single_image")]["preparar"]),
          "B: feed_single_image lleva música (obligatoria, como en Instagram)")
    from labkit import seleccion as S
    celda_texto = {"cell_id": "TX", "platform": "threads", "native_format": "feed_text",
                   "publishing_route": "android_native", "status": "planned"}
    check(not S._necesita_encargo(celda_texto) and S._necesita_encargo(dict(celda_texto, native_format="feed_single_image"))
          and S._necesita_encargo(dict(celda_texto, publishing_route="api")),
          "B: una celda de teléfono solo de texto no necesita encargo; con imagen o por API, sí")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: los rechazos de `th` (argparse no conoce el subcomando) y las recetas de Threads salen en `✗`, y la sección acaba en traceback con `AttributeError: module 'labkit.seleccion' has no attribute '_necesita_encargo'`.

- [ ] **Step 3: Implementar `lab.py th` y las recetas**

En `lab.py`, junto a `PASOS_IG_HISTORIA`:

```python
PASOS_TH = ("abrir", "nuevo", "texto", "galeria", "musica", "compartir")
LIMITE_THREADS = 500


def _leer_texto(ruta: str | None, que: str, limite: int | None = None) -> str:
    _exigir(bool(ruta), f"--pie ({que}) es obligatorio en este paso")
    texto = Path(ruta).read_text(encoding="utf-8").rstrip("\n")
    _exigir(bool(texto.strip()), f"{que} vacío")
    _exigir(limite is None or len(texto) <= limite, f"{que} tiene {len(texto)} caracteres: máximo {limite}")
    return texto


def cmd_th(a) -> int:
    from labkit import threads_feed as th
    ev = _evidencia(a.run)
    subidas = _subidas(a.subido_en)
    texto = _leer_texto(a.pie, "el texto del thread", LIMITE_THREADS) if a.paso in ("texto", "compartir") else None
    if a.paso == "galeria":
        _exigir(len(subidas) == 1, "galeria exige un --subido-en (lo devuelve telefono-subir)")
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    pasos_ = {
        "abrir": lambda: th.abrir(ev),
        "nuevo": lambda: th.nuevo(ev),
        "texto": lambda: th.texto(texto, ev),
        "galeria": lambda: th.galeria(ev, subidas[0]),
        "musica": lambda: th.musica(ev),
        "compartir": lambda: th.compartir(texto, a.tema, bool(subidas), ev, produccion_cercana=a.produccion_cercana),
    }
    return _paso_telefono(ev, f"th-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))
```

y en `construir`, tras `ig-historia`: `_parser_flujo(sub, "th", PASOS_TH, cmd_th)`.

En `recetas.py`, añadir antes de `TODAS`:

```python
_TH_ABRIR_Y_TEXTO = [
    _cmd("th", "abrir", "--run", "<run>", ver="th-01-perfil.png: perfil de @sabiduriabolsillo"),
    _cmd("th", "nuevo", "--run", "<run>", ver="th-02-compositor.png: compositor con la identidad de la marca",
         anota=("copia_instagram",)),
    _cmd("th", "texto", "--run", "<run>", "--pie", "<pie>", ver="th-03-texto.png: texto exacto sin teclado ni sugerencias"),
]

FEED_THREADS_TEXTO = {
    "subcomando": "th",
    "superficie": "feed",
    "formato_encargo": {},
    "preparar": _TH_ABRIR_Y_TEXTO,
    "publicar": [
        _cmd("th", "compartir", "--run", "<run>", "--pie", "<pie>", "[--produccion-cercana]",
             ver="th-07-perfil.png: el primer thread del perfil con el texto exacto y edad ≤ 3 min; "
                 "--produccion-cercana si el preflight trae hilos cerca (solo se anota)"),
    ],
    "verificar": [],
    "estados_ok": ["confirmado"],
    "conciliacion": ("Con sin_confirmacion o timeout, captura el perfil con telefono-captura y busca el texto exacto; "
                     "antes de registrar, lab.py manifiesto-busqueda --red threads y media-lab-verify -f buscar=threads. "
                     "Nunca por la otra ruta."),
    "copias": [],
    "verificacion": ("URL y post_id: lab.py manifiesto-busqueda --red threads --pie <pie> --desde <submitted_at> y "
                     "gh workflow run media-lab-verify -f buscar=threads. Casi duplicado con API o hilos: exposure_context."),
    "nota": "feed_text: sin imagen ni música.",
}

FEED_THREADS_IMAGEN = {
    **FEED_THREADS_TEXTO,
    "formato_encargo": {"ancho": 1080, "alto": 1350},
    "preparar": [_cmd("telefono-subir", "--local", "<master>", ver="JSON con sha256 y subido_en; no hay captura",
                      anota=("subido_en",))] + _TH_ABRIR_Y_TEXTO + [
        _cmd("th", "galeria", "--run", "<run>", "--subido-en", "<subido_en>", ver="th-04-imagen.png: la imagen completa adjunta"),
        _cmd("th", "musica", "--run", "<run>", ver="th-05-musica.png: tema sugerido añadido (captura de la QA)", anota=("tema",)),
    ],
    "publicar": [
        _cmd("th", "compartir", "--run", "<run>", "--pie", "<pie>", "--tema", "<tema>", "--subido-en", "<subido_en>",
             "[--produccion-cercana]",
             ver="th-07-perfil.png: el primer thread con el texto exacto, la imagen y edad ≤ 3 min"),
    ],
    "nota": "feed_single_image y feed_image_music: la misma receta, con música obligatoria.",
}
```

y a `TODAS`:

```python
    ("threads", "feed_single_image"): FEED_THREADS_IMAGEN,
    ("threads", "feed_image_music"): FEED_THREADS_IMAGEN,
    ("threads", "feed_text"): FEED_THREADS_TEXTO,
```

En `seleccion.py`, añadir tras `_ruta_implementada`:

```python
def _necesita_encargo(c: dict) -> bool:
    """Las celdas de teléfono cuya receta no pide imagen (`formato_encargo` vacío) salen sin encargo."""
    if c["publishing_route"] != "android_native":
        return True
    receta = recetas.TODAS.get((c["platform"], c["native_format"]))
    return receta is None or bool(receta["formato_encargo"])
```

y en `elegibles` cambiar `c["cell_id"] in utiles` por `(c["cell_id"] in utiles or not _necesita_encargo(c))`.

Si la tabla de S1 dice que «Partager aussi sur Instagram» viene **activo por defecto**, poner en `FEED_THREADS_TEXTO` `"copias": [{"red": "instagram", "superficie": "feed", "nota": "Threads comparte también en Instagram: publication.cross_posting"}]`.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/lab.py experiments/media-lab/labkit/recetas.py experiments/media-lab/labkit/seleccion.py tests/test_media_lab.py
git commit -m "media lab claude: lab.py th, recetas del feed de Threads en borrador y celdas de texto sin encargo

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 4: Prompt de la ventana**

Añadir al final de `seccion_prompt_ventana`:

```python
    for fragmento in ("exposure_context", "formato_encargo` vacío", "salvo en celdas sin encargo"):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «el prompt de la ventana menciona …» para esos fragmentos.

En `experiments/media-lab/claude-ventana-prompt.md`:

En «## Reglas que no se rompen», antes de la línea que empieza por «- A partir del 2026-10-02», añadir la línea:

```markdown
- Threads por teléfono se publica aunque haya casi duplicado con la ruta API de su familia o ráfaga con `hilos`: anótalo en `exposure_context` del run y no frenes.
```

Tras la frase «En `--formato` usa el `formato_encargo` de la receta.» del paso 5, añadir:

```markdown
 Las celdas cuya receta tiene `formato_encargo` vacío (solo texto) no llevan encargo.
```

En el paso 7g, sustituir «`lab.py encargo-usado --encargo ID --run RUN`» por «`lab.py encargo-usado --encargo ID --run RUN` (salvo en celdas sin encargo)».

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana publica Threads junto a la API y celdas de texto sin encargo

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 5: Actualizar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno» y «salvo en celdas sin encargo».

---

### Task 12d: B. Feed de Threads — ventana manual y promoción

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/findings.md`, `experiments/media-lab/coverage.json`, `experiments/media-lab/runs/<run>.json`, `experiments/media-lab/progress.md`, `tests/test_media_lab.py`

- [ ] **Step 1: Primera publicación en ventana manual (`threads/feed_single_image`)**

Igual que el Step 1 de la tarea 11d, con la celda `ready` (CELL-010 u otra) o la primera `planned` de `threads/feed_single_image/android_native`, formato 1080×1350 y pie ≤ 500. Tras `th compartir` con `confirmado`, lanzar la búsqueda de solo lectura si la tarea 13 ya está hecha (si no, se completa cuando lo esté): `lab.py manifiesto-busqueda --run-group <run> --red threads --pie <pie> --desde <submitted_at>`, commit y push del manifiesto, y `gh workflow run media-lab-verify -f manifest=<ruta> -f buscar=threads`.

- [ ] **Step 2: `findings.md` y promoción**

Añadir a `experiments/media-lab/findings.md` una sección «Primer thread por teléfono (<fecha>, <run>)» con estado, edad leída, si hubo aviso «Publié», copia a Instagram y cualquier resource-id que cambió. En `recetas.py`, añadir a `PROMOVIDAS`:

```python
    ("threads", "feed_single_image"): "<run>: primer thread con imagen por teléfono confirmado (<fecha>)",
    ("threads", "feed_image_music"): "<run>: misma receta que feed_single_image",
    ("threads", "feed_text"): "<run>: subconjunto de los pasos de feed_single_image con la misma confirmación",
```

Añadir al final de `seccion_threads`:

```python
    check(all(p in RC.RECETAS for p in (("threads", "feed_single_image"), ("threads", "feed_image_music"), ("threads", "feed_text"))),
          "B: feed de Threads promovido tras su ventana manual")
    check([c["cell_id"] for c in S.elegir([celda_texto], [])] == ["TX"], "B: una celda feed_text de Threads se elige sin encargo")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/findings.md experiments/media-lab/coverage.json experiments/media-lab/runs/<run>.json experiments/media-lab/progress.md tests/test_media_lab.py
git commit -m "media lab claude: primer thread por teléfono confirmado; feed de Threads promovido

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

Con el push hecho, `lab.py lock-soltar --dueno manual`: la sesión edita, comitea y hace push con el cerrojo tomado.

---

### Task 13: Modo `buscar` de `media-lab-verify` (spec, fila 7)

Sin teléfono; puede hacerse en su propio worktree en paralelo con las tareas 11 y 12, rebasando sobre `origin/main` antes de cada push (nunca en el mismo árbol a la vez).

**Files:**
- Modify: `experiments/media-lab/verify_api.py`, `.github/workflows/media-lab-verify.yml`, `experiments/media-lab/labkit/manifiesto.py`, `experiments/media-lab/lab.py`, `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_busqueda_verify,`:

```python
def seccion_busqueda_verify() -> None:
    print("\n22. Fase 2: modo buscar de media-lab-verify (solo lectura)")
    import importlib.util
    import json
    from datetime import datetime, timedelta, timezone
    from labkit import manifiesto as M

    spec = importlib.util.spec_from_file_location("verify_api", ROOT / "experiments" / "media-lab" / "verify_api.py")
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)

    desde = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
    pie = "«La paciencia es amarga».\n\n#citasdiarias"
    publicaciones = [
        {"id": "3", "message": pie, "created_time": "2026-09-15T09:40:00+0000"},
        {"id": "2", "message": pie + " ", "created_time": "2026-09-15T10:01:00+0000"},
        {"id": "1", "message": pie, "created_time": "2026-09-15T10:02:00+0000"},
    ]
    check(V.coincidencia(publicaciones, pie, desde, "message", "created_time")["id"] == "1",
          "buscar: el pie exacto publicado desde la hora dada (ni uno parecido ni uno anterior)")
    check(V.coincidencia(publicaciones, "otro", desde, "message", "created_time") is None, "buscar: sin pie exacto no hay coincidencia")
    check(V.cuando(1757930400) == datetime(2025, 9, 15, 10, 0, tzinfo=timezone.utc)
          and V.cuando("2026-09-15T10:02:00+0000") == datetime(2026, 9, 15, 10, 2, tzinfo=timezone.utc)
          and V.cuando("no") is None, "buscar: lee fechas de Meta en epoch e ISO")
    historias = [{"id": "a", "timestamp": "2026-09-15T10:05:00+0000"}, {"id": "b", "timestamp": "2026-09-15T12:00:00+0000"}]
    check([h["id"] for h in V.candidatas_historia(historias, desde, "timestamp")] == ["a"],
          "buscar: Stories vivas dentro de ±15 min de la hora de envío")
    check(V.MARGEN_DESDE == timedelta(minutes=2), "buscar: margen de 2 min antes de desde")

    m = M.manifiesto_busqueda("LAB-F12-002-B-THREADS", "threads", pie, "2026-09-15T10:00:00+00:00")
    check(m == {"run_group_id": "LAB-F12-002-B-THREADS", "buscar": {"red": "threads", "pie": pie, "desde": "2026-09-15T10:00:00+00:00"}},
          "manifiesto_busqueda con red, pie y desde")
    for args, label in ((("LAB-X", "tiktok", pie, "2026-09-15T10:00:00+00:00"), "red sin búsqueda"),
                        (("LAB-X", "facebook", "", "2026-09-15T10:00:00+00:00"), "feed sin pie"),
                        (("LAB-X", "threads", pie, "2026-09-15T10:00:00"), "desde sin zona"),
                        (("X-1", "threads", pie, "2026-09-15T10:00:00+00:00"), "run_group sin LAB-")):
        try:
            M.manifiesto_busqueda(*args)
            ok = False
        except M.ManifiestoError:
            ok = True
        check(ok, f"manifiesto_busqueda rechaza: {label}")
    check(M.manifiesto_busqueda("LAB-X", "instagram_story", None, "2026-09-15T10:00:00+00:00")["buscar"]["pie"] == "",
          "una búsqueda de Story no necesita pie")

    with entorno_lab_fase2() as (lab, raiz):
        (raiz / "pie.txt").write_text(pie + "\n", encoding="utf-8")
        args = ("manifiesto-busqueda", "--run-group", "LAB-F12-002-B-THREADS", "--red", "threads", "--pie", raiz / "pie.txt",
                "--desde", "2026-09-15T10:00:00+00:00")
        codigo, datos, _ = lab(*args)
        escrito = raiz / M.ruta_busqueda("LAB-F12-002-B-THREADS", "threads")
        check(codigo == 0 and escrito.is_file() and json.loads(escrito.read_text(encoding="utf-8"))["buscar"]["pie"] == pie,
              f"lab.py manifiesto-busqueda escribe el manifiesto ({codigo}, {datos})")
        check(rechazo(lab(*args), "ya existe", "ManifiestoError"), "manifiesto-busqueda no pisa un manifiesto existente")

    flujo = (ROOT / ".github" / "workflows" / "media-lab-verify.yml").read_text(encoding="utf-8")
    check("buscar:" in flujo and "SDB_PAGE_ID" in flujo and "SDB_THREADS_USER_ID" in flujo and "SDB_IG_USER_ID" in flujo
          and "contents: read" in flujo, "el workflow acepta buscar, recibe los ids y sigue siendo de solo lectura")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'verify_api' has no attribute 'coincidencia'` en la sección 22.

- [ ] **Step 3: Implementar en `verify_api.py`**

Cambiar `from datetime import datetime, timezone` por `from datetime import datetime, timedelta, timezone`, añadir tras `CONSULTAS`:

```python
# red → (base, ruta con ids de entorno, campos, token, campo de texto o None, campo de fecha). Solo lectura.
BUSQUEDAS = {
    "facebook": (GRAPH, "{SDB_PAGE_ID}/posts", "id,permalink_url,created_time,message", "SDB_PAGE_TOKEN",
                 "message", "created_time"),
    "threads": (THREADS_GRAPH, "{SDB_THREADS_USER_ID}/threads", "id,permalink,timestamp,text", "SDB_THREADS_TOKEN",
                "text", "timestamp"),
    # insights de la Story viva si la API los da; si rechaza el campo, la búsqueda sale failed y la ventana no la repite
    "instagram_story": (GRAPH, "{SDB_IG_USER_ID}/stories", "id,media_type,permalink,timestamp,insights.metric(reach,replies)", "SDB_PAGE_TOKEN",
                        None, "timestamp"),
    "facebook_story": (GRAPH, "{SDB_PAGE_ID}/stories", "post_id,status,creation_time,url,media_type", "SDB_PAGE_TOKEN",
                       None, "creation_time"),
}
MARGEN_HISTORIA = timedelta(minutes=15)
MARGEN_DESDE = timedelta(minutes=2)  # los relojes del teléfono y de Meta no coinciden al segundo


def cuando(valor) -> datetime | None:
    """Fecha de Meta en epoch («1757930400») o ISO («2026-09-15T10:02:00+0000»); None si no se lee."""
    if valor is None:
        return None
    texto = str(valor)
    if texto.isdigit():
        return datetime.fromtimestamp(int(texto), timezone.utc)
    try:
        return datetime.strptime(texto, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


def coincidencia(publicaciones: list[dict], pie: str, desde: datetime, campo_texto: str, campo_fecha: str) -> dict | None:
    """La primera publicación con el pie exacto publicada desde `desde`. El contador redondeado no se usa."""
    for p in publicaciones:
        t = cuando(p.get(campo_fecha))
        if t is not None and t >= desde and (p.get(campo_texto) or "") == pie:
            return p
    return None


def candidatas_historia(historias: list[dict], desde: datetime, campo_fecha: str,
                        margen: timedelta = MARGEN_HISTORIA) -> list[dict]:
    """Stories vivas publicadas dentro de ±margen de la hora de envío: se concilian por captura."""
    return [h for h in historias if (t := cuando(h.get(campo_fecha))) is not None and desde - margen <= t <= desde + margen]


def buscar(manifest: dict) -> dict:
    b = manifest["buscar"]
    base, ruta, campos, token_env, campo_texto, campo_fecha = BUSQUEDAS[b["red"]]
    datos = _get(f"{base}/{ruta.format(**os.environ)}",
                 {"fields": campos, "limit": 25, "access_token": os.environ[token_env]}).get("data", [])
    desde = datetime.fromisoformat(b["desde"]) - MARGEN_DESDE
    if campo_texto:
        encontrada = coincidencia(datos, b["pie"], desde, campo_texto, campo_fecha)
        return {"status": "found" if encontrada else "not_found", "detail": encontrada}
    candidatas = candidatas_historia(datos, desde, campo_fecha)
    return {"status": "found" if candidatas else "not_found", "detail": candidatas,
            "con_metricas": any("insights" in h for h in candidatas)}
```

y sustituir `main` completa por:

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--buscar", choices=tuple(BUSQUEDAS), help="solo lectura: busca por pie exacto o por hora")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    output = {
        "run_group_id": manifest["run_group_id"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "results": {},
    }
    if args.buscar:
        try:
            red = (manifest.get("buscar") or {}).get("red")
            if red != args.buscar:
                raise ValueError(f"el manifiesto busca en {red!r}, no en {args.buscar!r}")
            output["results"][args.buscar] = buscar(manifest)
        except Exception as exc:  # noqa: BLE001
            output["results"][args.buscar] = {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:500]}
    else:
        for platform, post_id in manifest["post_ids"].items():
            try:
                base, fields, token_env = CONSULTAS[platform]
                detail = _get(f"{base}/{post_id}", {"fields": fields, "access_token": os.environ[token_env]})
                output["results"][platform] = {"status": "verified", "detail": detail}
            except Exception as exc:  # noqa: BLE001
                output["results"][platform] = {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print("MEDIA_LAB_VERIFY=" + json.dumps(output, ensure_ascii=False))
    return 1 if any(v["status"] == "failed" for v in output["results"].values()) else 0
```

- [ ] **Step 4: Implementar el manifiesto y `lab.py manifiesto-busqueda`**

En `manifiesto.py`, añadir `from datetime import datetime` a las importaciones y al final:

```python
REDES_BUSQUEDA = ("facebook", "threads", "facebook_story", "instagram_story")


def manifiesto_busqueda(run_group_id: str, red: str, pie: str | None, desde: str) -> dict:
    """Manifiesto del modo buscar de media-lab-verify: pie exacto en feed, hora en Stories."""
    _validar_run_group(run_group_id)
    if red not in REDES_BUSQUEDA:
        raise ManifiestoError(f"verify_api.py no busca en {red}")
    if red in FEED and not (pie or "").strip():
        raise ManifiestoError(f"buscar en {red} exige el pie exacto")
    try:
        cuando = datetime.fromisoformat(desde)
    except ValueError as e:
        raise ManifiestoError(f"desde no es una fecha ISO 8601: {desde!r}") from e
    if cuando.tzinfo is None:
        raise ManifiestoError("desde necesita zona horaria")
    return {"run_group_id": run_group_id, "buscar": {"red": red, "pie": pie or "", "desde": cuando.isoformat()}}


def ruta_busqueda(run_group_id: str, red: str) -> str:
    return f"experiments/media-lab/manifests/{run_group_id}-buscar-{red}.json"
```

En `lab.py`, tras `cmd_manifiesto_verificacion`:

```python
def cmd_manifiesto_busqueda(a) -> int:
    pie = Path(a.pie).read_text(encoding="utf-8").rstrip("\n") if a.pie else None
    m = manifiesto.manifiesto_busqueda(a.run_group, a.red, pie, a.desde)
    rel = manifiesto.ruta_busqueda(a.run_group, a.red)
    _escribir_manifiesto(rel, m)
    emitir({"manifiesto": rel, "buscar": a.red})
    return 0
```

y en `construir`, tras `manifiesto-verificacion`:

```python
    p = sub.add_parser("manifiesto-busqueda")
    p.add_argument("--run-group", required=True)
    p.add_argument("--red", choices=manifiesto.REDES_BUSQUEDA, required=True)
    p.add_argument("--pie", help="archivo del pie exacto (obligatorio en facebook y threads)")
    p.add_argument("--desde", required=True, help="submitted_at del run (ISO con zona)")
    p.set_defaults(func=cmd_manifiesto_busqueda)
```

- [ ] **Step 5: El workflow**

Sustituir `.github/workflows/media-lab-verify.yml` completo por:

```yaml
name: media-lab-verify

on:
  workflow_dispatch:
    inputs:
      manifest:
        description: "Verification manifest under experiments/media-lab/manifests/"
        required: true
        default: "experiments/media-lab/manifests/LAB-F12-001-A-verify.json"
      buscar:
        description: "Solo lectura: facebook, threads, instagram_story o facebook_story (vacío: verificar post_ids)"
        required: false
        default: ""

jobs:
  verify:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install --quiet -r requirements.txt
      - name: Verify live posts without mutation
        env:
          SDB_PAGE_TOKEN: ${{ secrets.SDB_PAGE_TOKEN }}
          SDB_THREADS_TOKEN: ${{ secrets.SDB_THREADS_TOKEN }}
          SDB_PAGE_ID: ${{ secrets.SDB_PAGE_ID }}
          SDB_IG_USER_ID: ${{ secrets.SDB_IG_USER_ID }}
          SDB_THREADS_USER_ID: ${{ secrets.SDB_THREADS_USER_ID }}
          MANIFEST: ${{ inputs.manifest }}
          BUSCAR: ${{ inputs.buscar }}
        run: |
          case "$BUSCAR" in
            ""|facebook|threads|instagram_story|facebook_story) ;;
            *) echo "buscar no válido: $BUSCAR"; exit 2 ;;
          esac
          python3 experiments/media-lab/verify_api.py "$MANIFEST" --output experiments/media-lab/verification-result.json ${BUSCAR:+--buscar "$BUSCAR"}
      - name: Preserve verification result
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: media-lab-verification-${{ github.run_id }}
          path: experiments/media-lab/verification-result.json
          if-no-files-found: warn
```

- [ ] **Step 6: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 22 en `✓` y `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/verify_api.py .github/workflows/media-lab-verify.yml experiments/media-lab/labkit/manifiesto.py experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: media-lab-verify busca por pie exacto o por hora en solo lectura

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 7: Prueba real de solo lectura con un thread ya publicado por API**

> **Controlador con el usuario presente (no subagente).** Push y workflow con los tokens de producción, desde el worktree.

Guardar en `experiments/media-lab/results/buscar-prueba.txt` el pie de Threads del manifiesto `experiments/media-lab/manifests/LAB-F12-001-A.json` (`captions.threads`, tal cual) y crear el manifiesto con `--desde` un minuto antes del `submitted_at` de `experiments/media-lab/runs/LAB-F12-001-A-THREADS.json`:

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python experiments/media-lab/lab.py manifiesto-busqueda --run-group LAB-F12-001-A-BUSCAR --red threads --pie experiments/media-lab/results/buscar-prueba.txt --desde <submitted_at − 1 min>`
Run: `git add experiments/media-lab/manifests/LAB-F12-001-A-BUSCAR-buscar-threads.json && git commit -m "media lab claude: manifiesto de prueba del modo buscar" && git fetch origin main && git rebase origin/main && git push origin HEAD:main` (con el trailer de siempre en el mensaje)
Run: `gh workflow run media-lab-verify -f manifest=experiments/media-lab/manifests/LAB-F12-001-A-BUSCAR-buscar-threads.json -f buscar=threads`, luego `gh run watch` y `gh run download`.
Expected: `results.threads.status == "found"` con el mismo `id` que el `post_id` del run. Si sale `not_found` porque el hilo es más antiguo que los 25 últimos, anotarlo en `findings.md` y repetir con el thread de la primera ventana manual de la tarea 12. No borrar `buscar-prueba.txt` del repo porque no se añadió: se queda en `results/`, que no se comitea.

- [ ] **Step 8: Prompt de la ventana**

Añadir al final de `seccion_prompt_ventana`:

```python
    for fragmento in ("buscar=", "con_metricas"):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «el prompt de la ventana menciona …» para esos fragmentos.

En `experiments/media-lab/claude-ventana-prompt.md`:

Tras la frase «Cada entrada de `copias` va en `publication.cross_posting` del run como publicación extra, no como celda.» del paso 7f, añadir:

```markdown
 Para URL y `post_id` de Facebook y Threads por teléfono: `lab.py manifiesto-busqueda --run-group <RUN> --red <facebook|threads> --pie <archivo> --desde <submitted_at>`, commit y push de ese manifiesto y `gh workflow run media-lab-verify -f manifest=<ruta> -f buscar=<red>`; cuando termine, `gh run download` y copia `post_id` y URL al run. No retrases la ventana esperándolo: si no ha terminado, lo recoge la siguiente.
```

Tras la frase «y guárdalas en sus runs.» del paso 8, añadir:

```markdown
 Stories de Instagram: una sola `lab.py manifiesto-busqueda --run-group <RUN> --red instagram_story --desde <submitted_at>` y `gh workflow run media-lab-verify -f manifest=<ruta> -f buscar=instagram_story`; si el resultado trae `con_metricas: false` o `failed`, no la repitas y usa el teléfono o `missing_data_reasons`. Stories de Facebook: no lances workflows de métricas (la búsqueda no las devuelve).
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana obtiene URL y métricas de Stories con media-lab-verify buscar

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 9: Actualizar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno» y «buscar=».

---

### Task 14a: C. Feed de la Página de Facebook — textos y lectores contra fixtures (spec, fila 8)

Depende de la tarea 13 (URL por `buscar=facebook`) y usa los ayudantes comunes de `pantalla.py` que añade la tarea 12a en su Step 5 (`por_id`, `imagen_bajo`, `tema_bajo_cabecera`, `aviso_corto`, `observacion_envio`) y los de la tarea 11. Publicar como perfil personal es el riesgo principal: la identidad de la Página y «Público» se exigen antes de cualquier toque de composición, otra vez en dos volcados antes de pulsar y en el autor después.

**Files:**
- Create: `experiments/media-lab/labkit/facebook_pantallas.py`
- Modify: `experiments/media-lab/labkit/textos.py`
- Test: `tests/test_media_lab.py`; fixtures `tests/fixtures/telefono/facebook/{inicio,compositor-pagina,galeria,compositor-con-imagen,musica,pantalla-final,descartar-dialogo,perfil-pagina}.xml` e `interstitial.xml` si S1 lo vio

- [ ] **Step 1: Sonda complementaria (solo si S1 no dejó algún fixture)**

Por cada fixture de la lista **Files** que falte, repetir su tramo del Step 5 de la tarea 9 con `--run SONDA-F2-C` y podarlo con `lab.py fixture-podar --app facebook --desde experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-C/<nombre>.xml --pantalla <fixture>`. Nunca se toca «Siguiente» sin volver atrás ni ningún texto de envío.

- [ ] **Step 2: Confirmar los textos de Facebook contra S1**

Añadir a `TEXTOS["facebook"]`, con el valor observado en la tabla de S1 cuando difiera:

```python
        "foto_video": "Foto/video",  # confirmar contra el fixture de S1 (botón de galería del compositor)
        "listo": "Listo",  # confirmar contra el fixture de S1 (confirmación de la galería o de la música)
        "sugeridas": "Sugerencias",  # confirmar contra el fixture de S1 (cabecera de la música)
        "publicando": "Publicando",  # confirmar contra el fixture de S1 (principio del aviso tras publicar)
        "no_se_pudo": "No se pudo publicar",  # confirmar contra el fixture de S1
        "reintentar": "Reintentar",  # confirmar contra el fixture de S1
        "cambiaste_a": "Cambiaste a",
        "anular": "Anular",
```

Sustituir `DESCARTE["facebook"]` por `{"titulos": ("¿Descartar publicación?", "¿Guardar borrador?"), "botones": ("Descartar",)}` con los textos observados, y `PATRONES_FIXTURE["facebook"]` por:

```python
    "facebook": (r"#\S+",
                 r"Foto del perfil de Sabiduria De Bolsillo",  # confirmar contra el fixture de S1
                 r"Sabiduria De Bolsillo ?✓",  # cabecera verificada; confirmar contra el fixture de S1
                 r"(?:Foto|Imagen|Miniatura)(?: tomada el| del)? \d{1,2} de \S+ de \d{4},?(?: a las)? \d{1,2}:\d{2}"),  # confirmar contra el fixture de S1 (fecha de las miniaturas)
```

Si las miniaturas de la galería de S1 no llevan «14 de septiembre de 2026, 10:39» o similar, ajustar `_FECHA` en `facebook_pantallas.py` (Step 5) al formato observado. Después, volver a podar con `lab.py fixture-podar --app facebook` los fixtures de la lista **Files** desde sus volcados crudos de S1 (tabla del Step 8 de la tarea 9), para que conserven fechas, menciones de la Página y textos recién confirmados.

- [ ] **Step 3: Escribir la prueba de los lectores**

Añadir antes de `SECCIONES` y registrar `seccion_facebook_feed,`:

```python
PIE_FACEBOOK = "«Saber no ocupa lugar».\n\nUna frase que ya circulaba en el siglo XVII.\n\n#citasdiarias"


def xml_interstitial_fb(boton: str = "Ahora no") -> str:
    """Interstitial sintético: solo si la sonda S1 no vio ninguno."""
    return jerarquia(nodo_xml("[80,800][1000,900]", texto="Novedades", paquete="com.facebook.katana"),
                     nodo_xml("[80,1500][1000,1600]", texto=boton, clase="android.widget.Button",
                              paquete="com.facebook.katana", extra='clickable="true"'))


def publicacion_pagina_xml(base: str, autor: str, edad: str, pie: str) -> str:
    """La primera publicación del perfil de la Página: autor, edad, «Público» y pie añadidos al final."""
    fb = "com.facebook.katana"
    return con_nodo(con_nodo(con_nodo(con_nodo(base,
        nodo_xml("[150,1480][700,1530]", texto=autor, paquete=fb)),
        nodo_xml("[150,1540][300,1590]", texto=edad, paquete=fb)),
        nodo_xml("[310,1540][360,1590]", desc="Público", clase="android.widget.ImageView", paquete=fb)),
        nodo_xml("[40,1650][1040,1800]", texto=pie, paquete=fb))


def seccion_facebook_feed() -> None:
    print("\n23. Fase 2 (C): feed de la Página de Facebook")
    from datetime import timedelta
    from labkit import facebook_pantallas as FP, pantalla as P, telefono as T

    inicio = fixture("facebook", "inicio")
    compositor = fixture("facebook", "compositor-pagina")
    check(FP.inicio_listo(inicio) and FP.identidad_pagina(inicio), "C: el inicio real tiene «¿Qué estás pensando?» y la Página activa")
    check(FP.identidad_y_audiencia(compositor) == [], f"C: el compositor real es de la Página y público ({FP.identidad_y_audiencia(compositor)})")
    personal = compositor.replace("Sabiduria De Bolsillo", "Juan Pérez")
    check(any("Sabiduria De Bolsillo" in p for p in FP.identidad_y_audiencia(personal)), "C: con el perfil personal el compositor no vale")
    inter = fixture_o("facebook", "interstitial", xml_interstitial_fb())
    check(FP.interstitial(inter) is not None and FP.interstitial(inicio) is None, "C: interstitial de la tabla reconocido; el inicio no lo es")
    check(FP.interstitial(xml_interstitial_fb("Continuar")) is None, "C: un interstitial desconocido no se reconoce (se falla cerrado)")
    cambio = con_nodo(inicio, nodo_xml("[0,2000][800,2080]", texto="Cambiaste a Sabiduria De Bolsillo", paquete=FP.PAQUETE)
                      + nodo_xml("[820,2000][1060,2080]", texto="Anular", clase="android.widget.Button", paquete=FP.PAQUETE,
                                 extra='clickable="true"'))
    check(FP.aviso_cambio_perfil(cambio) == "Cambiaste a Sabiduria De Bolsillo", "C: se anota el aviso «Cambiaste a…»")

    galeria = fixture("facebook", "galeria")
    subida = primera_fecha(galeria, FP.fecha_miniatura_es)
    check(bool(FP.miniatura_galeria(galeria, subida)["desc"]), "C: miniatura de la subida por hora en la galería real")
    try:
        FP.miniatura_galeria(galeria, subida + timedelta(hours=5))
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "C: sin miniatura a esa hora, PantallaInesperada")
    musica = fixture("facebook", "musica")
    cab = T.buscar(musica, texto=FP.T["sugeridas"], paquete=FP.PAQUETE)
    fila = next(n for n in T.nodos(musica) if n["package"] == FP.PAQUETE and n["clickable"] and n["bounds"][1] >= cab["bounds"][3])
    musica_con_tema = con_nodo(musica, nodo_xml("[%d,%d][%d,%d]" % (fila["bounds"][0] + 1, fila["bounds"][1] + 1,
                                                                    fila["bounds"][0] + 400, fila["bounds"][1] + 40),
                                                texto="Autumn Days", paquete=FP.PAQUETE))
    check(FP.tema_sugerido(musica_con_tema)["tema"].startswith("Autumn Days"), "C: primer tema sugerido de la lista real")
    con_imagen = fixture("facebook", "compositor-con-imagen")
    con_pie = con_valor(con_imagen, lambda n: n["clase"] in P.CLASES_CAMPO and n["package"] == FP.PAQUETE, PIE_FACEBOOK)
    check(FP.compositor_con_pie(con_pie, PIE_FACEBOOK, True, None) == [],
          f"C: compositor real con imagen y pie exacto listo ({FP.compositor_con_pie(con_pie, PIE_FACEBOOK, True, None)})")
    check(FP.compositor_con_pie(con_pie, PIE_FACEBOOK + ".", True, None), "C: un pie parecido no vale")
    final = fixture("facebook", "pantalla-final")
    check(FP.pantalla_final_lista(final) == [], f"C: pantalla final real con Página, «Público» y «Publicar» ({FP.pantalla_final_lista(final)})")
    check(FP.pantalla_final_lista(final.replace("Sabiduria De Bolsillo", "Juan Pérez")), "C: la pantalla final con el perfil personal no vale")
    emergente_final = [{"nombre": "PopupWindow:fb", "frame": None, "ancho_padre": None}]
    check(any("PopupWindow:fb" in p for p in FP.pantalla_final_lista(final, emergente_final)),
          "C: una ventana emergente sobre la pantalla final impide publicar")
    check(P.boton_descarte(fixture("facebook", "descartar-dialogo"), "facebook")["texto"] == "Descartar",
          "C: el diálogo de descarte real se reconoce")

    perfil = fixture("facebook", "perfil-pagina")
    reciente = publicacion_pagina_xml(perfil, "Sabiduria De Bolsillo", "Ahora", PIE_FACEBOOK)
    lectura = FP.publicacion_reciente_pagina(reciente, PIE_FACEBOOK)
    check(lectura["ok"] and lectura["identidad"] == "pagina" and lectura["edad_s"] == 0 and not lectura["repetido"],
          f"C: primera publicación de la Página con autor, «Ahora», «Público» y pie exacto ({lectura})")
    check(not FP.publicacion_reciente_pagina(reciente, PIE_FACEBOOK[:-1])["ok"], "C: un pie parecido no confirma")
    como_personal = FP.publicacion_reciente_pagina(publicacion_pagina_xml(perfil, "Juan Pérez", "Ahora", PIE_FACEBOOK), PIE_FACEBOOK)
    check(not como_personal["ok"] and como_personal["identidad"] == "personal", "C: autor personal: identidad personal")
    check(not FP.publicacion_reciente_pagina(publicacion_pagina_xml(perfil, "Sabiduria De Bolsillo", "3 h", PIE_FACEBOOK), PIE_FACEBOOK)["ok"],
          "C: una publicación de hace 3 h no confirma")
    doble = con_nodo(reciente, nodo_xml("[40,1900][1040,2050]", texto=PIE_FACEBOOK, paquete=FP.PAQUETE))
    check(FP.publicacion_reciente_pagina(doble, PIE_FACEBOOK)["repetido"], "C: el mismo pie dos veces en pantalla: repetido")
    obs = FP.observacion(con_nodo(inicio, nodo_xml("[0,300][1080,380]", texto=FP.T["publicando"] + "…", paquete=FP.PAQUETE)))
    check(obs["valido"] and obs["banner"] and not obs["compositor"], "C: «Publicando…» cuenta como banner")
```

- [ ] **Step 4: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'facebook_pantallas' from 'labkit'` en la sección 23.

- [ ] **Step 5: Implementar `facebook_pantallas.py`**

```python
"""
Lectura pura de las pantallas de Facebook con la Página activa (flujos C y D de la fase 2).

Textos en español. La identidad de la Página («Sabiduria De Bolsillo») y la audiencia «Público»
se exigen antes de cualquier toque de composición y antes de pulsar; nunca se toca «Anular» del
aviso «Cambiaste a…» (está en `textos.NO_TOCAR`).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from labkit import pantalla, telefono, textos
from labkit.pantalla import PantallaInesperada

PAQUETE = textos.PAQUETES["facebook"]
PAGINA = textos.MARCAS["facebook"]
T = textos.TEXTOS["facebook"]
INTERSTITIALS = (T["ahora_no"], T["not_now"])
ZONA_LOCAL = ZoneInfo("Europe/Madrid")
BANDA_AUTOR_PX = 120
BANDA_FILA_PX = 60
DISTANCIA_CABECERA_PX = 400
_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_FECHA = re.compile(r"\b(\d{1,2}) de (\w+) de (\d{4}),?(?: a las)? (\d{1,2}):(\d{2})\b")  # confirmar contra el fixture de S1


def fecha_miniatura_es(desc: str) -> datetime | None:
    """Fecha de «… 14 de septiembre de 2026, 10:39» (hora de Madrid) en UTC."""
    m = _FECHA.search(desc or "")
    if not m:
        return None
    dia, mes, anio, hora, minuto = m.groups()
    numero = _MESES.get(mes.lower())
    if numero is None:
        return None
    try:
        return datetime(int(anio), numero, int(dia), int(hora), int(minuto), tzinfo=ZONA_LOCAL).astimezone(timezone.utc)
    except ValueError:
        return None


def _propios(xml: str) -> list[dict]:
    return telefono.buscar_todos(xml, paquete=PAQUETE)


def _arriba(xml: str, denominador: int = 3) -> list[dict]:
    alto = pantalla.alto_volcado(xml)
    return [n for n in _propios(xml) if n["bounds"][3] * denominador <= alto]


def interstitial(xml: str) -> dict | None:
    """El botón «Ahora no» / «Not Now» de un interstitial de la tabla; None si no hay."""
    candidatos = [n for n in _propios(xml) if n["texto"] in INTERSTITIALS or n["desc"] in INTERSTITIALS]
    return pantalla.elegir(candidatos, "interstitial") if candidatos else None


def aviso_cambio_perfil(xml: str) -> str | None:
    return next((n["texto"] for n in _propios(xml) if n["texto"].startswith(T["cambiaste_a"])), None)


def inicio_listo(xml: str) -> bool:
    return telefono.buscar(xml, texto=T["que_piensas"], paquete=PAQUETE) is not None


def identidad_pagina(xml: str) -> bool:
    """La Página aparece (texto o descripción) en el tercio superior."""
    return any(PAGINA in n["texto"] or PAGINA in n["desc"] for n in _arriba(xml))


def nodo_pagina(xml: str) -> dict:
    """El control de la Página en el tercio superior (su avatar o su nombre) para abrir su perfil."""
    candidatos = [n for n in _arriba(xml) if PAGINA in n["texto"] or PAGINA in n["desc"]]
    if not candidatos:
        raise PantallaInesperada(f"no aparece «{PAGINA}» arriba: Facebook no está con la Página activa")
    return pantalla.elegir(candidatos, PAGINA)  # confirmar contra el fixture de S1 (qué abre el perfil de la Página)


def campo_pie(xml: str) -> dict | None:
    campos = [n for n in _propios(xml) if n["clase"] in pantalla.CLASES_CAMPO]
    return pantalla.elegir(campos, "campo del pie") if campos else None


def compositor_abierto(xml: str) -> bool:
    return campo_pie(xml) is not None and telefono.buscar(xml, texto=T["publico"], paquete=PAQUETE) is not None


def emergente_compositor(xml: str, emergentes: list[dict]) -> dict | None:
    """Ventana emergente (sugerencias que `uiautomator dump` puede no ver) que se solapa con el campo del pie,
    «Siguiente» o «Publicar»."""  # confirmar contra el fixture de S1
    campo = campo_pie(xml)
    referencias = ([campo["bounds"]] if campo else []) + [
        n["bounds"] for n in _propios(xml) if pantalla.dice(n, T["siguiente"]) or pantalla.dice(n, T["publicar"])]
    return pantalla.emergente_solapada(emergentes, referencias)


def identidad_y_audiencia(xml: str) -> list[str]:
    problemas = []
    if not identidad_pagina(xml):
        problemas.append(f"no publica como «{PAGINA}»")
    if telefono.buscar(xml, texto=T["publico"], paquete=PAQUETE) is None:
        problemas.append(f"la audiencia no es «{T['publico']}»")
    return problemas


def adjunto_imagen(xml: str) -> bool:
    campo = campo_pie(xml)
    return campo is not None and pantalla.imagen_bajo(xml, PAQUETE, campo["bounds"])  # confirmar contra el fixture de S1


def compositor_con_pie(xml: str, pie: str | None, con_imagen: bool, tema: str | None,
                       emergentes: list[dict] | None = None) -> list[str]:
    problemas = identidad_y_audiencia(xml)
    if pie is not None and not pantalla.tiene_texto(xml, texto=pie, paquete=PAQUETE):
        problemas.append("el pie del teléfono no coincide con el archivo")
    if con_imagen and not adjunto_imagen(xml):
        problemas.append("no hay imagen adjunta")
    if tema:
        titulo = tema.split(" · ")[0]
        if not any(titulo == n["texto"] or titulo in n["desc"] for n in _propios(xml)):
            problemas.append(f"no aparece el tema «{titulo}»")
    if telefono.buscar(xml, texto=T["siguiente"], paquete=PAQUETE) is None:
        problemas.append(f"no hay «{T['siguiente']}»")
    if pantalla.hay_desplegable(xml, PAQUETE, prefijo="#"):
        problemas.append("sugerencias abiertas")
    culpable = emergente_compositor(xml, emergentes or [])
    if culpable is not None:
        problemas.append(f"sugerencias abiertas ({pantalla.describe_emergente(culpable)})")
    return problemas


def pantalla_final_lista(xml: str, emergentes: list[dict] | None = None) -> list[str]:
    """La pantalla tras «Siguiente»: Página, «Público» y «Publicar» visible, sin tapar y pulsable."""
    problemas = identidad_y_audiencia(xml)
    botones = telefono.buscar_todos(xml, texto=T["publicar"], paquete=PAQUETE)
    if not botones:
        problemas.append(f"no hay botón «{T['publicar']}»")
    elif any(telefono.tapado(xml, b) for b in botones):
        problemas.append(f"«{T['publicar']}» está tapado")
    elif not pantalla.pulsable(xml, etiqueta=T["publicar"], paquete=PAQUETE):
        problemas.append(f"«{T['publicar']}» no se puede pulsar")
    culpable = emergente_compositor(xml, emergentes or [])
    if culpable is not None:
        problemas.append(f"ventana emergente abierta ({pantalla.describe_emergente(culpable)})")
    return problemas


def miniatura_galeria(xml: str, subido_en: datetime) -> dict:
    return pantalla.miniatura_por_hora(xml, PAQUETE, subido_en, fecha_miniatura_es)


def tema_sugerido(xml: str) -> dict:
    return pantalla.tema_bajo_cabecera(xml, PAQUETE, T["sugeridas"])


def observacion(xml: str, boton_bounds: tuple[int, int, int, int] | None = None) -> dict:
    fb = _propios(xml)
    compositor = campo_pie(xml) is not None or (
        boton_bounds is not None and any(pantalla.dice(n, T["publicar"]) and n["bounds"] == tuple(boton_bounds) for n in fb))
    return pantalla.observacion_envio(xml, PAQUETE, compositor, (T["publicando"],), (T["no_se_pudo"], T["reintentar"]))


def publicacion_reciente_pagina(xml: str, pie: str, max_s: int = 120) -> dict:
    """{"ok", "problemas", "identidad", "repetido", "edad_s"} del perfil de la Página.

    La primera publicación con el pie exacto (la más alta) debe tener, en la línea de edad más cercana
    por encima (a ≤ DISTANCIA_CABECERA_PX), edad ≤ max_s («Ahora» o «1 min») y «Público», y justo encima
    de esa línea el autor. `identidad` es «pagina» si el autor es la Página, «personal» si hay otro
    nombre y None si no se lee. `repetido` si el pie exacto está más de una vez en pantalla (p. ej. la
    copia automática de una foto de Instagram): el estado baja a confirmado_sin_prueba_unica."""
    fb = _propios(xml)
    con_pie = sorted((n for n in fb if n["texto"] == pie), key=lambda n: n["bounds"][1])
    if not con_pie:
        return {"ok": False, "problemas": ["no aparece el pie exacto en el perfil de la Página"], "identidad": None,
                "repetido": False, "edad_s": None}
    cuerpo = con_pie[0]
    techo = cuerpo["bounds"][1] - DISTANCIA_CABECERA_PX
    edades = [(n, e) for n in fb if techo <= n["bounds"][1] and n["bounds"][3] <= cuerpo["bounds"][1]
              and (e := pantalla.edad_segundos(n["texto"], "facebook")) is not None]
    problemas = []
    identidad = None
    edad = None
    if not edades:
        problemas.append("no se lee la edad de la publicación")
    else:
        linea, edad = edades[-1]
        autores = [n for n in fb if linea["bounds"][1] - BANDA_AUTOR_PX <= n["bounds"][1] < linea["bounds"][1] and n["texto"]]
        if any(n["texto"] == PAGINA for n in autores):
            identidad = "pagina"
        elif autores:
            identidad = "personal"
        if edad > max_s:
            problemas.append(f"la publicación tiene {edad} s (máximo {max_s})")
        if not any(T["publico"] in n["texto"] or T["publico"] in n["desc"] for n in fb
                   if abs(n["centro"][1] - linea["centro"][1]) <= BANDA_FILA_PX):
            problemas.append("la publicación no es pública")
    if identidad != "pagina":
        problemas.append(f"el autor no es «{PAGINA}» ({identidad})")
    return {"ok": not problemas, "problemas": problemas, "identidad": identidad, "repetido": len(con_pie) > 1, "edad_s": edad}
```

- [ ] **Step 6: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 23 en `✓` y `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/facebook_pantallas.py experiments/media-lab/labkit/textos.py tests/test_media_lab.py
git commit -m "media lab claude: lectores del feed de la Página de Facebook con identidad, audiencia y autor

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14b: C. Feed de la Página de Facebook — pasos con teléfono simulado

**Files:**
- Create: `experiments/media-lab/labkit/facebook_feed.py`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de los pasos**

Añadir al final de `seccion_facebook_feed`:

```python
    print("   · pasos del feed de Facebook con teléfono simulado")
    import json
    import pathlib as _p
    from datetime import datetime, timezone
    from labkit import colision, facebook_feed as FB, pasos

    evid = _p.Path("evidencia-simulada")
    que_piensas = P.nodo(inicio, FP.PAQUETE, texto=FP.T["que_piensas"])["centro"]
    ahora_no = FP.interstitial(inter)["centro"]
    sim = TelefonoSimulado([inter, inicio])
    res, err = con_telefono_simulado(sim, lambda: FB.abrir(evid))
    check(err is None and sim.toques == [ahora_no] and sim.capturas == ["fb-01-inicio.png"],
          f"C abrir: un interstitial de la tabla se pulsa una vez ({err!r}, {sim.toques})")
    sim = TelefonoSimulado([xml_interstitial_fb("Continuar")])
    res, err = con_telefono_simulado(sim, lambda: FB.abrir(evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C abrir: un interstitial desconocido detiene el flujo sin tocar")
    sim = TelefonoSimulado([cambio])
    res, err = con_telefono_simulado(sim, lambda: FB.abrir(evid))
    check(err is None and sim.toques == [] and res["aviso_cambio_perfil"], "C abrir: «Cambiaste a…» se anota y «Anular» nunca se toca")
    sim = TelefonoSimulado([inicio.replace("Sabiduria De Bolsillo", "Juan Pérez")])
    res, err = con_telefono_simulado(sim, lambda: FB.abrir(evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C abrir sin la Página activa: ningún toque")

    sim = TelefonoSimulado([inicio, compositor])
    res, err = con_telefono_simulado(sim, lambda: FB.nuevo(evid))
    check(err is None and sim.toques == [que_piensas] and sim.capturas == ["fb-02-compositor.png"], f"C nuevo: compositor de la Página ({err!r})")
    sim = TelefonoSimulado([inicio, personal])
    res, err = con_telefono_simulado(sim, lambda: FB.nuevo(evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [que_piensas],
          "C nuevo con el perfil personal: se para sin ningún toque de composición")

    desplegable = con_nodo(con_pie, nodo_xml("[0,1200][1080,1300]", texto="#citas", paquete=FP.PAQUETE))
    sim = TelefonoSimulado([con_imagen, con_pie, desplegable, desplegable, con_pie], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: FB.pie(PIE_FACEBOOK, evid))
    check(err is None and sim.pegados == [PIE_FACEBOOK] and sim.teclas == [pasos.ATRAS] and sim.capturas == ["fb-05-pie.png"],
          f"C pie: el desplegable del segundo volcado se cierra con un «atrás» ({err!r}, {sim.teclas})")
    for nombre_paso, guion_paso, accion in (
            ("abrir", [inter, inicio], lambda: FB.abrir(evid)),
            ("nuevo", [inicio, compositor], lambda: FB.nuevo(evid)),
            ("pie", [con_imagen, con_pie, desplegable, desplegable, con_pie], lambda: FB.pie(PIE_FACEBOOK, evid))):
        sim = TelefonoSimulado(guion_paso, teclado=(False,))
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and not toques_sobre_envio(sim, FP.PAQUETE),
              f"C1 C {nombre_paso}: fuera de compartir, ningún toque cae sobre un control de envío ({err!r}, {sim.toques})")
    # si S1 muestra «Música» en otra pantalla, se cambia el flujo (FB.musica), no esta prueba
    check(T.buscar(con_imagen, texto=FP.T["musica"], paquete=FP.PAQUETE) is not None, "S1: «Música» en compositor-con-imagen")
    con_imagen_tema = con_nodo(con_imagen, nodo_xml("[40,1900][600,1960]", texto="Autumn Days", paquete=FP.PAQUETE))
    for nombre_paso, guion_paso, accion in (
            ("galeria", [compositor, galeria, galeria, con_imagen, con_imagen, con_imagen], lambda: FB.galeria(evid, subida)),
            ("musica", [con_imagen, musica_con_tema, musica_con_tema, con_imagen_tema, con_imagen_tema, con_imagen_tema],
             lambda: FB.musica(evid)),
            ("siguiente", [con_pie, final, final, final], lambda: FB.siguiente(evid))):
        sim = TelefonoSimulado(guion_paso)
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and not toques_sobre_envio(sim, FP.PAQUETE),
              f"C1 C {nombre_paso}: camino feliz sin tocar controles de envío ({err!r}, {sim.toques})")

    publicar = P.nodo(final, FP.PAQUETE, texto=FP.T["publicar"])["centro"]
    aviso = con_nodo(inicio, nodo_xml("[0,300][1080,380]", texto=FP.T["publicando"] + "…", paquete=FP.PAQUETE))
    pagina = FP.nodo_pagina(inicio)["centro"]
    guion = [final, final, aviso, inicio, inicio, inicio, reciente]
    sim = TelefonoSimulado(guion)
    res, err = con_telefono_simulado(sim, lambda: FB.compartir(PIE_FACEBOOK, evid))
    check(err is None and res["estado"] == "confirmado" and sim.toques.count(publicar) == 1 and sim.toques[:2] == [publicar, pagina]
          and res["identidad"] == "pagina" and sim.capturas == ["fb-07a-antes.png", "fb-08-perfil.png"],
          f"C compartir: exactamente un toque en «Publicar» y la publicación de la Página con el pie exacto ({err!r}, {res and res['estado']})")
    sim = TelefonoSimulado(guion[:-1] + [publicacion_pagina_xml(perfil, "Juan Pérez", "Ahora", PIE_FACEBOOK)])
    res, err = con_telefono_simulado(sim, lambda: FB.compartir(PIE_FACEBOOK, evid))
    check(err is None and res["estado"] == "fallido" and res["identidad"] == "personal" and "personal" in res["avisos"][0],
          f"C compartir con autor personal: fallido, identidad personal y aviso destacado ({res and res['estado']})")
    sim = TelefonoSimulado(guion[:-1] + [doble])
    res, err = con_telefono_simulado(sim, lambda: FB.compartir(PIE_FACEBOOK, evid))
    check(err is None and res["estado"] == "confirmado_sin_prueba_unica", f"C compartir con el pie repetido: sin prueba única ({res and res['estado']})")
    sim = TelefonoSimulado([final.replace("Sabiduria De Bolsillo", "Juan Pérez")])
    res, err = con_telefono_simulado(sim, lambda: FB.compartir(PIE_FACEBOOK, evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C compartir con la pantalla final del perfil personal: no se pulsa")
    sim = TelefonoSimulado([final], emergentes=(emergente_final,))
    res, err = con_telefono_simulado(sim, lambda: FB.compartir(PIE_FACEBOOK, evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "C compartir con una ventana emergente abierta: no se pulsa")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'facebook_feed' from 'labkit'`.

- [ ] **Step 3: Implementar `facebook_feed.py`**

`experiments/media-lab/labkit/facebook_feed.py`:

```python
"""
Feed de la Página de Facebook por teléfono, un paso por llamada (flujo C de la fase 2).

abrir → nuevo → [galeria → musica] → pie → siguiente → QA → compartir. La URL y el post_id se
completan después con `media-lab-verify -f buscar=facebook` (solo lectura). Si la publicación sale
con el autor personal, el estado es «fallido» con `identidad: personal` y el aviso va el primero.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from labkit import facebook_pantallas as fp
from labkit import pantalla, pasos, reloj, telefono
from labkit.pantalla import PantallaInesperada

T = fp.T


def _exigir_pagina(xml: str, que: str) -> None:
    problemas = fp.identidad_y_audiencia(xml)
    if problemas:
        raise PantallaInesperada(f"{que}: {problemas}")


def abrir(evidencia: Path) -> dict:
    """Facebook con la Página activa en el inicio. Un interstitial de la tabla se pulsa como mucho una
    vez; cualquier otro detiene el flujo. «Cambiaste a…» se anota y «Anular» no se toca."""
    xml = pasos.lanzar_app(fp.PAQUETE, "facebook", listo=lambda x: fp.inicio_listo(x) or fp.interstitial(x) is not None,
                           borrador=fp.compositor_abierto, descripcion="Facebook listo (inicio o interstitial conocido)")
    if not fp.inicio_listo(xml):
        pasos.tocar(fp.interstitial(xml), xml, fp.PAQUETE)
        xml = pasos.esperar_que(fp.inicio_listo, "el inicio de Facebook tras el interstitial", app="facebook")
    if not fp.identidad_pagina(xml):
        raise PantallaInesperada(f"Facebook no está con la Página «{fp.PAGINA}» activa: no se toca nada")
    return {"aviso_cambio_perfil": fp.aviso_cambio_perfil(xml), "captura": str(telefono.captura(evidencia / "fb-01-inicio.png"))}


def nuevo(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(fp.inicio_listo, "«¿Qué estás pensando?»", app="facebook")
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, texto=T["que_piensas"]), xml, fp.PAQUETE)
    xml, _ = pasos.esperar_estable(lambda x: fp.campo_pie(x) is not None, descripcion="el compositor de la Página")
    _exigir_pagina(xml, "el compositor no es el de la Página")
    return {"captura": str(telefono.captura(evidencia / "fb-02-compositor.png"))}


def _hay_miniatura(xml: str, subido_en: datetime) -> bool:
    try:
        fp.miniatura_galeria(xml, subido_en)
        return True
    except PantallaInesperada:
        return False


def _tocar_si_hay(texto: str) -> None:
    xml = pasos.volcado_fresco()
    candidatos = telefono.buscar_todos(xml, texto=texto, paquete=fp.PAQUETE)
    if candidatos:
        pasos.tocar(pantalla.elegir(candidatos, texto), xml, fp.PAQUETE)


def galeria(evidencia: Path, subido_en: datetime) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["foto_video"], paquete=fp.PAQUETE) is not None,
                            f"«{T['foto_video']}»", app="facebook")
    _exigir_pagina(xml, "antes de adjuntar la imagen")
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, texto=T["foto_video"]), xml, fp.PAQUETE)
    xml = pasos.esperar_que(lambda x: _hay_miniatura(x, subido_en), "la miniatura de la subida", app="facebook")
    pasos.tocar(fp.miniatura_galeria(xml, subido_en), xml, fp.PAQUETE)
    reloj.dormir(1)
    _tocar_si_hay(T["listo"])
    xml, _ = pasos.esperar_estable(lambda x: fp.campo_pie(x) is not None and fp.adjunto_imagen(x),
                                   descripcion="el compositor con la imagen")
    _exigir_pagina(xml, "tras adjuntar la imagen")
    return {"captura": str(telefono.captura(evidencia / "fb-03-imagen.png"))}


def musica(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["musica"], paquete=fp.PAQUETE) is not None,
                            f"«{T['musica']}»", app="facebook")
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, texto=T["musica"]), xml, fp.PAQUETE)
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["sugeridas"], paquete=fp.PAQUETE) is not None,
                            "la música sugerida", app="facebook")
    sugerido = fp.tema_sugerido(xml)
    pasos.tocar(sugerido["nodo"], xml, fp.PAQUETE)
    reloj.dormir(1)
    _tocar_si_hay(T["listo"])
    titulo = sugerido["tema"].split(" · ")[0]
    xml, _ = pasos.esperar_estable(lambda x: fp.campo_pie(x) is not None and any(titulo == n["texto"] or titulo in n["desc"]
                                                                                 for n in telefono.buscar_todos(x, paquete=fp.PAQUETE)),
                                   descripcion="el compositor con el tema")
    _exigir_pagina(xml, "tras añadir la música")
    return {"tema": sugerido["tema"], "captura": str(telefono.captura(evidencia / "fb-04-musica.png"))}


def pie(pie_: str, evidencia: Path) -> dict:
    def exigir(xml: str) -> None:
        _exigir_pagina(xml, "tras pegar el pie")
        if not pantalla.tiene_texto(xml, texto=pie_, paquete=fp.PAQUETE):
            raise PantallaInesperada("tras pegar el pie falta el pie exacto")

    pasos.escribir_texto(pie_, fp.PAQUETE, campo=fp.campo_pie, exigir=exigir,
                         desplegable_nodos=lambda x: pantalla.hay_desplegable(x, fp.PAQUETE, prefijo="#"),
                         emergente=fp.emergente_compositor)
    return {"captura": str(telefono.captura(evidencia / "fb-05-pie.png"))}


def siguiente(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["siguiente"], paquete=fp.PAQUETE) is not None,
                            f"«{T['siguiente']}»", app="facebook")
    _exigir_pagina(xml, "antes de «Siguiente»")
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, texto=T["siguiente"]), xml, fp.PAQUETE)
    xml, _ = pasos.esperar_estable(lambda x: telefono.buscar(x, texto=T["publicar"], paquete=fp.PAQUETE) is not None,
                                   descripcion="la pantalla final con «Publicar»")
    problemas = fp.pantalla_final_lista(xml)
    if problemas:
        raise PantallaInesperada(f"la pantalla final no está lista: {problemas}")
    return {"captura": str(telefono.captura(evidencia / "fb-06-final.png"))}


def compartir(pie_: str, evidencia: Path) -> dict:
    """Pulsa «Publicar» una sola vez y confirma en el perfil de la Página (autor, edad, «Público», pie exacto).

    Estados: «confirmado», «confirmado_sin_prueba_unica» (el pie exacto sale dos veces), «sin_confirmacion»,
    «timeout», «fallido» (también con `identidad: personal`) y «error_tras_pulsar»."""

    def despues(resultado: dict, estado: str) -> str:
        avisos = resultado["avisos"]
        lectura = None
        try:
            if telefono.estado()["listo"]:
                xml = pasos.esperar_que(fp.inicio_listo, "el inicio tras publicar", app="facebook")
                pasos.tocar(fp.nodo_pagina(xml), xml, fp.PAQUETE)
                xml, _ = pasos.esperar_estable(
                    lambda x: (lambda l: l["ok"] or l["identidad"] == "personal")(fp.publicacion_reciente_pagina(x, pie_)),
                    descripcion="la publicación nueva en el perfil de la Página")
                lectura = fp.publicacion_reciente_pagina(xml, pie_)
            else:
                avisos.append("tras publicar el teléfono no está listo: no se leyó el perfil de la Página")
        except (PantallaInesperada, telefono.TelefonoError) as e:
            avisos.append(f"no se leyó la publicación en el perfil de la Página: {e}")
        resultado["perfil"] = lectura
        if lectura and lectura["identidad"] == "personal":
            resultado["identidad"] = "personal"
            avisos.insert(0, "ATENCIÓN: la publicación salió con el perfil personal, no con la Página: requiere al usuario")
            return "fallido"
        resultado["identidad"] = lectura["identidad"] if lectura else None
        return pantalla.estado_confirmado(estado, lectura, bool(lectura and lectura["repetido"]), avisos,
                                          "el pie exacto aparece dos veces en la Página: se concilia por captura")

    return pasos.enviar(
        paquete=fp.PAQUETE, nombre_app="Facebook", etiqueta=T["publicar"], evidencia=evidencia,
        captura_antes="fb-07a-antes.png", captura_final="fb-08-perfil.png", captura_error="fb-07-error.png",
        listo=fp.pantalla_final_lista,
        botones=lambda x: telefono.buscar_todos(x, texto=T["publicar"], paquete=fp.PAQUETE),
        observador_nuevo=lambda boton: (lambda x: fp.observacion(x, boton["bounds"])),
        despues=despues, extra={"perfil": None, "identidad": None})
```

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/facebook_feed.py tests/test_media_lab.py
git commit -m "media lab claude: pasos del feed de la Página de Facebook con identidad antes y después de publicar

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14c: C. Feed de la Página de Facebook — regla de 24 h, `lab.py fb`, recetas en borrador y prompt

**Files:**
- Modify: `experiments/media-lab/labkit/colision.py`, `experiments/media-lab/lab.py`, `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de la regla de 24 h y de `lab.py fb`**

Añadir al final de `seccion_facebook_feed`:

```python
    import json
    from datetime import datetime, timezone
    from labkit import colision

    print("   · regla de 24 h del pie y lab.py fb")
    with entorno_lab_fase2() as (lab, raiz):
        ahora = datetime.now(timezone.utc)
        (raiz / "experiments/media-lab/runs").mkdir(parents=True)
        (raiz / "experiments/media-lab/assets/F").mkdir(parents=True)
        (raiz / "experiments/media-lab/assets/F/pie-ig.txt").write_text(PIE_FACEBOOK + "\n", encoding="utf-8")
        run = {"run_id": "LAB-F-B-INSTAGRAM", "platform": "instagram",
               "publication": {"route_id": "ANDROID-MASTER", "submitted_at": (ahora - timedelta(hours=2)).isoformat(),
                               "caption_path": "experiments/media-lab/assets/F/pie-ig.txt"}}
        (raiz / "experiments/media-lab/runs/LAB-F-B-INSTAGRAM.json").write_text(json.dumps(run), encoding="utf-8")
        runs = raiz / "experiments/media-lab/runs"
        check(colision.pie_instagram_reciente(PIE_FACEBOOK, runs, ahora, raiz) == "LAB-F-B-INSTAGRAM"
              and colision.pie_instagram_reciente(PIE_FACEBOOK + "x", runs, ahora, raiz) is None
              and colision.pie_instagram_reciente(PIE_FACEBOOK, runs, ahora + timedelta(hours=30), raiz) is None,
              "pie_instagram_reciente: el mismo pie de un run de Instagram por teléfono de las últimas 24 h")
        (raiz / "pie.txt").write_text(PIE_FACEBOOK + "\n", encoding="utf-8")
        for args, fragmento, label in ((("fb", "pie", "--run", "R", "--pie", raiz / "pie.txt"), "idéntico", "un pie igual al de Instagram por teléfono de hace 2 h"),
                            (("fb", "pie", "--run", "R"), "--pie", "pie sin --pie"),
                            (("fb", "galeria", "--run", "R"), "--subido-en", "galeria sin --subido-en"),
                            (("fb", "compartir", "--run", "R"), "--pie", "compartir sin --pie")):
            sim = TelefonoSimulado([inicio])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0, f"fb rechaza {label} sin tocar el teléfono ({res and res[0]})")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.colision' has no attribute 'pie_instagram_reciente'` en la sección 23.

- [ ] **Step 3: Implementar `colision.pie_instagram_reciente` y `lab.py fb`**

En `colision.py`, añadir al final:

```python
def pie_instagram_reciente(pie: str, runs: Path, ahora: datetime, raiz: Path, horas: int = 24) -> str | None:
    """run_id de un run de Instagram por teléfono (`publication.route_id` ANDROID…) enviado en las últimas
    `horas` cuyo pie (`publication.caption_path`) es idéntico a `pie`. Instagram copia esa foto en la
    Página: el mismo pie en Facebook no se distinguiría de la copia."""
    desde = ahora - timedelta(hours=horas)
    for p in sorted(runs.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pub = d.get("publication") or {}
        if d.get("platform") != "instagram" or not str(pub.get("route_id") or "").startswith("ANDROID"):
            continue
        if not pub.get("submitted_at") or not pub.get("caption_path"):
            continue
        try:
            cuando = _dt(pub["submitted_at"])
            texto = (raiz / pub["caption_path"]).read_text(encoding="utf-8").rstrip("\n")
        except (ValueError, OSError):
            continue
        if desde <= cuando <= ahora and texto == pie:
            return d.get("run_id") or p.stem
    return None
```

En `lab.py`, junto a `PASOS_TH`:

```python
PASOS_FB = ("abrir", "nuevo", "galeria", "musica", "pie", "siguiente", "compartir")


def cmd_fb(a) -> int:
    from labkit import facebook_feed as fb
    ev = _evidencia(a.run)
    subidas = _subidas(a.subido_en)
    pie = _leer_texto(a.pie, "el pie de Facebook") if a.paso in ("pie", "compartir") else None
    if a.paso == "pie":
        repetido = colision.pie_instagram_reciente(pie, ROOT / "experiments" / "media-lab" / "runs", ahora(), ROOT)
        _exigir(repetido is None, f"el pie es idéntico al de {repetido} (Instagram por teléfono, últimas 24 h): "
                                  "la copia automática lo haría indistinguible")
    if a.paso == "galeria":
        _exigir(len(subidas) == 1, "galeria exige un --subido-en (lo devuelve telefono-subir)")
    _exigir(not a.produccion_cercana, "fb no usa --produccion-cercana: el pie exacto identifica la publicación")
    pasos_ = {
        "abrir": lambda: fb.abrir(ev),
        "nuevo": lambda: fb.nuevo(ev),
        "galeria": lambda: fb.galeria(ev, subidas[0]),
        "musica": lambda: fb.musica(ev),
        "pie": lambda: fb.pie(pie, ev),
        "siguiente": lambda: fb.siguiente(ev),
        "compartir": lambda: fb.compartir(pie, ev),
    }
    return _paso_telefono(ev, f"fb-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))
```

y en `construir`: `_parser_flujo(sub, "fb", PASOS_FB, cmd_fb)`.

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/colision.py experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: regla de 24 h del pie de Facebook y lab.py fb

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Recetas del feed de Facebook**

Añadir al final de `seccion_facebook_feed`:

```python
    from labkit import recetas as RC
    for par in (("facebook", "feed_single_image"), ("facebook", "feed_text"), ("facebook", "feed_image_music")):
        check(par in RC.TODAS and RC.TODAS[par]["subcomando"] == "fb", f"C: receta de {par}")
    check(not any(c["args"][1:2] in (["galeria"], ["musica"]) or c["args"][0] == "telefono-subir"
                  for c in RC.TODAS[("facebook", "feed_text")]["preparar"]), "C: feed_text sin imagen ni música")
    check([c["args"][1] for c in RC.TODAS[("facebook", "feed_single_image")]["preparar"] if c["args"][0] == "fb"]
          == ["abrir", "nuevo", "galeria", "musica", "pie", "siguiente"], "C: el orden de pasos de la spec")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «C: receta de …».

En `recetas.py`, antes de `TODAS`:

```python
_FB_FINAL = [
    _cmd("fb", "pie", "--run", "<run>", "--pie", "<pie>",
         ver="fb-05-pie.png: pie exacto con la Página y «Público», sin teclado ni sugerencias"),
    _cmd("fb", "siguiente", "--run", "<run>",
         ver="fb-06-final.png: pantalla final con «Sabiduria De Bolsillo», «Público» y «Publicar» (captura de la QA)"),
]

FEED_FACEBOOK_TEXTO = {
    "subcomando": "fb",
    "superficie": "feed",
    "formato_encargo": {},
    "preparar": [
        _cmd("fb", "abrir", "--run", "<run>", ver="fb-01-inicio.png: inicio con la Página activa; anota aviso_cambio_perfil",
             anota=("aviso_cambio_perfil",)),
        _cmd("fb", "nuevo", "--run", "<run>", ver="fb-02-compositor.png: compositor con la Página y «Público»"),
    ] + _FB_FINAL,
    "publicar": [
        _cmd("fb", "compartir", "--run", "<run>", "--pie", "<pie>",
             ver="fb-08-perfil.png: la primera publicación de la Página con autor, «Ahora» o «1 min», «Público» y el pie exacto"),
    ],
    "verificar": [],
    "estados_ok": ["confirmado"],
    "conciliacion": ("Con identidad personal: no repitas nada y avisa al usuario al principio del informe. Con "
                     "confirmado_sin_prueba_unica, pasa al revisor fb-08-perfil.png y el máster. Con sin_confirmacion o "
                     "timeout, lab.py manifiesto-busqueda --red facebook y media-lab-verify -f buscar=facebook antes de "
                     "registrar; nunca por la otra ruta."),
    "copias": [],
    "verificacion": ("URL y post_id: lab.py manifiesto-busqueda --red facebook --pie <pie> --desde <submitted_at> y "
                     "gh workflow run media-lab-verify -f buscar=facebook."),
    "nota": "feed_text: sin imagen ni música.",
}

FEED_FACEBOOK_IMAGEN = {
    **FEED_FACEBOOK_TEXTO,
    "formato_encargo": {"ancho": 1080, "alto": 1350},
    "preparar": [
        _cmd("telefono-subir", "--local", "<master>", ver="JSON con sha256 y subido_en; no hay captura", anota=("subido_en",)),
    ] + FEED_FACEBOOK_TEXTO["preparar"][:2] + [
        _cmd("fb", "galeria", "--run", "<run>", "--subido-en", "<subido_en>", ver="fb-03-imagen.png: la imagen completa adjunta"),
        _cmd("fb", "musica", "--run", "<run>", ver="fb-04-musica.png: tema sugerido en el compositor", anota=("tema",)),
    ] + _FB_FINAL,
    "nota": ("feed_single_image y feed_image_music: la misma receta con música. Una foto con música puede salir como "
             "vídeo: anota el tipo real en actual_native_format del run."),
}
```

y a `TODAS`:

```python
    ("facebook", "feed_single_image"): FEED_FACEBOOK_IMAGEN,
    ("facebook", "feed_image_music"): FEED_FACEBOOK_IMAGEN,
    ("facebook", "feed_text"): FEED_FACEBOOK_TEXTO,
```

Si S1 vio en el compositor un conmutador «Compartir en Instagram» activo por defecto, poner en `FEED_FACEBOOK_TEXTO` `"copias": [{"red": "instagram", "superficie": "feed", "nota": "Facebook comparte también en Instagram: publication.cross_posting"}]`.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py tests/test_media_lab.py
git commit -m "media lab claude: recetas del feed de la Página de Facebook en borrador

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 6: Prompt de la ventana**

Añadir al final de `seccion_prompt_ventana`:

```python
    for fragmento in ("identidad: personal", "caption_path"):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «el prompt de la ventana menciona …» para esos fragmentos.

En `experiments/media-lab/claude-ventana-prompt.md`:

En «## Reglas que no se rompen», antes de la línea que empieza por «- A partir del 2026-10-02», añadir la línea:

```markdown
- Si una publicación de Facebook sale con `identidad: personal`, no repitas nada y ponlo al principio del informe: requiere al usuario.
```

En el paso 7g, sustituir «(en teléfono, también `publication.native_app_and_version`» por «(en teléfono, también `publication.caption_path` con la ruta del pie y `publication.native_app_and_version`».

En «## Informe», sustituir «Un borrador que no pudiste cerrar va al principio.» por «Una identidad personal en Facebook o un borrador que no pudiste cerrar van al principio.»

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana vigila la identidad de la Página y guarda el pie publicado

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 7: Actualizar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno» y «identidad: personal».

---

### Task 14d: C. Feed de la Página de Facebook — ventana manual y promoción

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/findings.md`, `experiments/media-lab/coverage.json`, `experiments/media-lab/runs/<run>.json`, `experiments/media-lab/progress.md`, `tests/test_media_lab.py`

- [ ] **Step 1: Primera publicación en ventana manual (`facebook/feed_single_image`)**

Igual que el Step 1 de la tarea 11d, con la celda `ready` (CELL-006 u otra) o la primera `planned` de `facebook/feed_single_image/android_native`, formato 1080×1350 y un pie que no coincida con ninguna foto de Instagram por teléfono de las últimas 24 h (`fb pie` lo rechaza si coincide). En esa ventana no sale ninguna celda de Instagram por teléfono. Tras `confirmado`: `lab.py manifiesto-busqueda --run-group <run> --red facebook --pie <pie> --desde <submitted_at>`, commit y push, y `gh workflow run media-lab-verify -f manifest=<ruta> -f buscar=facebook`; copiar `post_id` y URL al run.

- [ ] **Step 2: `findings.md` y promoción**

Añadir a `findings.md` «Primera publicación de la Página por teléfono (<fecha>, <run>)»: estado, autor leído, interstitials vistos, tipo real (foto o vídeo) con música y resultado de `buscar=facebook`. En `recetas.py`, añadir a `PROMOVIDAS`:

```python
    ("facebook", "feed_single_image"): "<run>: primera publicación de la Página por teléfono confirmada (<fecha>)",
    ("facebook", "feed_image_music"): "<run>: misma receta que feed_single_image",
    ("facebook", "feed_text"): "<run>: subconjunto de los pasos de feed_single_image con la misma confirmación",
```

Añadir al final de `seccion_facebook_feed`:

```python
    check(all(p in RC.RECETAS for p in (("facebook", "feed_single_image"), ("facebook", "feed_image_music"), ("facebook", "feed_text"))),
          "C: feed de la Página promovido tras su ventana manual")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/findings.md experiments/media-lab/coverage.json experiments/media-lab/runs/<run>.json experiments/media-lab/progress.md tests/test_media_lab.py
git commit -m "media lab claude: primera publicación de la Página por teléfono confirmada; feed de Facebook promovido

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

Con el push hecho, `lab.py lock-soltar --dueno manual`: la sesión edita, comitea y hace push con el cerrojo tomado.

---

### Task 15a: D. Story de la Página de Facebook — textos y lectores contra fixtures (spec, fila 9)

Depende de las tareas 11 (lectores y pasos de Story) y 14 (lectores de Facebook). Promueve `facebook/story_image`; `facebook/story_image_music` queda escrito y se promueve en la tarea 16 tras S2.

**Files:**
- Modify: `experiments/media-lab/labkit/facebook_pantallas.py`, `experiments/media-lab/labkit/textos.py`
- Test: `tests/test_media_lab.py`; fixtures `tests/fixtures/telefono/facebook/{historia-creador,historia-editor,historia-opciones}.xml` y `historia-visor-propio.xml` si S1 lo vio

- [ ] **Step 1: Sonda complementaria y textos**

Si falta algún fixture de la lista, repetir su tramo del Step 5 de la tarea 9 con `--run SONDA-F2-D` y podarlo. Añadir a `TEXTOS["facebook"]`, con lo observado en S1:

```python
        "stickers": "Stickers",  # confirmar contra el fixture de S1 (botón del editor de historia)
        "compartir_historia": "Compartir",  # confirmar contra el fixture de S1 (envío del editor de historia)
        "tu_historia": "Tu historia",  # confirmar contra el fixture de S1 (miniatura de la historia propia en el inicio)
        "aviso_historia": "Compartiendo",  # confirmar contra el fixture de S1 (principio del aviso de subida)
        "opciones_historia": "Opciones",  # confirmar contra el fixture de S1 (botón del editor que lleva a «Compartir en Instagram»)
```

Si S1 mostró que en Facebook la música de una historia siempre crea un sticker, `story_image` usa el estilo más pequeño que ofrezca el selector y la QA lo revisa; anotarlo en `findings.md`. Después, volver a podar con `lab.py fixture-podar --app facebook` los fixtures de historia de la lista **Files** desde sus volcados crudos de S1.

- [ ] **Step 2: Escribir la prueba de los lectores**

Añadir antes de `SECCIONES` y registrar `seccion_facebook_historia,`:

```python
def xml_visor_historia_fb(pagina: str = "Sabiduria De Bolsillo", edad: str = "1 min") -> str:
    """Visor sintético de la historia propia de la Página: solo si S1 no encontró una viva."""
    fb = "com.facebook.katana"
    return jerarquia(nodo_xml("[150,120][600,180]", texto=pagina, paquete=fb),
                     nodo_xml("[610,120][760,180]", texto=edad, paquete=fb),
                     nodo_xml("[40,2150][400,2250]", texto="Agregar nueva", paquete=fb))


def seccion_facebook_historia() -> None:
    print("\n24. Fase 2 (D): Story de la Página de Facebook")
    from labkit import facebook_pantallas as FP, pantalla as P, telefono as T

    inicio = fixture("facebook", "inicio")
    creador = fixture("facebook", "historia-creador")
    editor = fixture("facebook", "historia-editor")
    opciones = fixture("facebook", "historia-opciones")
    check(FP.creador_historia_listo(creador) and FP.identidad_pagina(creador), "D: el creador real con la identidad de la Página")
    subida = primera_fecha(creador, FP.fecha_miniatura_es)
    check(bool(FP.miniatura_galeria(creador, subida)["desc"]), "D: la miniatura de la subida por hora en el creador real")
    check(FP.editor_historia_fb_listo(editor) and not FP.editor_historia_fb_listo(creador), "D: el editor real se reconoce")
    destino = FP.destino_historia_fb(editor)
    check(destino["problemas"] == [],
          f"D: el editor real puede compartir como la Página ({destino})")
    check(FP.destino_historia_fb(editor.replace("Sabiduria De Bolsillo", "Juan Pérez"))["problemas"],
          "D: con el perfil personal no se comparte")
    check(FP.copia_instagram_historia(opciones) in (True, False), "D: el conmutador «Compartir en Instagram» real se lee")
    visor = con_valor(fixture_o("facebook", "historia-visor-propio", xml_visor_historia_fb()),
                      lambda n: P.edad_segundos(n["texto"], "facebook") is not None, "1 min")
    check(FP.historia_propia_fb(visor)["ok"], f"D: visor propio con la Página, edad y «Agregar nueva» ({FP.historia_propia_fb(visor)})")
    check(not FP.historia_propia_fb(visor.replace("Sabiduria De Bolsillo", "Juan Pérez"))["ok"], "D: el visor de otra cuenta no confirma")
```

- [ ] **Step 3: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.facebook_pantallas' has no attribute 'creador_historia_listo'` en la sección 24.

- [ ] **Step 4: Implementar los lectores de Story en `facebook_pantallas.py`**

Añadir al final:

```python
# --- Story de la Página (flujo D) --------------------------------------------------------


def creador_historia_listo(xml: str) -> bool:
    """El creador de historias: miniaturas con fecha en pantalla."""
    return any(fecha_miniatura_es(n["desc"]) for n in _propios(xml) if n["desc"])


def editor_historia_fb_listo(xml: str) -> bool:
    return (telefono.buscar(xml, texto=T["stickers"], paquete=PAQUETE) is not None
            and telefono.buscar(xml, texto=T["compartir_historia"], paquete=PAQUETE) is not None)


def copia_instagram_historia(xml: str) -> bool | None:
    """Estado del conmutador «Compartir en Instagram» si aparece; no se cambia."""
    return pantalla.marcado_en_fila(xml, PAQUETE, T["compartir_en_instagram"])


def destino_historia_fb(xml: str) -> dict:
    """{"problemas"} del editor antes de compartir (el conmutador de Instagram lo lee `opciones`): Página arriba y botón de compartir
    visible, sin tapar y pulsable."""
    problemas = [] if identidad_pagina(xml) else [f"la historia no se comparte como «{PAGINA}»"]
    botones = telefono.buscar_todos(xml, texto=T["compartir_historia"], paquete=PAQUETE)
    if not botones:
        problemas.append(f"no hay botón «{T['compartir_historia']}»")
    elif any(telefono.tapado(xml, b) for b in botones):
        problemas.append(f"«{T['compartir_historia']}» está tapado")
    elif not pantalla.pulsable(xml, etiqueta=T["compartir_historia"], paquete=PAQUETE):
        problemas.append(f"«{T['compartir_historia']}» no se puede pulsar")
    return {"problemas": problemas}


def historia_propia_fb(xml: str, max_s: int = 180) -> dict:
    """{"ok", "problemas", "edad_s"} del visor de la historia propia: la Página en el quinto superior, edad
    ≤ max_s y «Agregar nueva» o «Compartir como publicación» (pie de la historia propia)."""
    arriba = _arriba(xml, 5)
    problemas = []
    if not any(PAGINA in n["texto"] for n in arriba):
        problemas.append(f"la cabecera del visor no es «{PAGINA}»")
    edades = [e for n in arriba if (e := pantalla.edad_segundos(n["texto"], "facebook")) is not None]
    edad = min(edades) if edades else None
    if edad is None:
        problemas.append("no se lee la edad de la historia")
    elif edad > max_s:
        problemas.append(f"la historia tiene {edad} s (máximo {max_s})")
    if not any(telefono.buscar(xml, texto=T[k], paquete=PAQUETE) for k in ("agregar_nueva", "compartir_como_publicacion")):
        problemas.append("falta «Agregar nueva» / «Compartir como publicación»: no es la historia propia")
    return {"ok": not problemas, "problemas": problemas, "edad_s": edad}


def observacion_historia_fb(xml: str, boton_bounds: tuple[int, int, int, int] | None = None) -> dict:
    compositor = editor_historia_fb_listo(xml) or (boton_bounds is not None and any(
        pantalla.dice(n, T["compartir_historia"]) and n["bounds"] == tuple(boton_bounds) for n in _propios(xml)))
    return pantalla.observacion_envio(xml, PAQUETE, compositor, (T["aviso_historia"],), (T["no_se_pudo"], T["reintentar"]))
```

- [ ] **Step 5: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/facebook_pantallas.py experiments/media-lab/labkit/textos.py tests/test_media_lab.py
git commit -m "media lab claude: lectores de la Story de la Página de Facebook contra los fixtures de S1

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 15b: D. Story de la Página de Facebook — pasos con teléfono simulado

**Files:**
- Create: `experiments/media-lab/labkit/facebook_historia.py`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de los pasos**

Añadir al final de `seccion_facebook_historia`:

```python
    import pathlib as _p
    from labkit import facebook_historia as FH, pasos

    evid = _p.Path("evidencia-simulada")
    crear = P.nodo(inicio, FP.PAQUETE, texto=FP.T["crear_historia"])["centro"]
    sim = TelefonoSimulado([inicio, creador])
    res, err = con_telefono_simulado(sim, lambda: FH.abrir(evid))
    check(err is None and sim.toques == [crear] and sim.capturas == ["fbh-01-creador.png"], f"D abrir: «Crear historia» y creador de la Página ({err!r})")
    sim = TelefonoSimulado([inicio, creador.replace("Sabiduria De Bolsillo", "Juan Pérez")])
    res, err = con_telefono_simulado(sim, lambda: FH.abrir(evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [crear], "D abrir con el perfil personal: se para antes de elegir")
    sim = TelefonoSimulado([creador, editor])
    res, err = con_telefono_simulado(sim, lambda: FH.elegir(evid, subida))
    check(err is None and sim.toques == [FP.miniatura_galeria(creador, subida)["centro"]] and sim.capturas == ["fbh-02-editor.png"],
          f"D elegir: un toque en la miniatura ({err!r})")

    boton = P.nodo(editor, FP.PAQUETE, texto=FP.T["compartir_historia"])["centro"]
    aviso = con_nodo(inicio, nodo_xml("[0,300][1080,380]", texto=FP.T["aviso_historia"] + "…", paquete=FP.PAQUETE))
    con_propia = con_nodo(inicio, nodo_xml("[20,400][300,800]", desc=FP.T["tu_historia"], clase="android.widget.ImageView",
                                           paquete=FP.PAQUETE, extra='clickable="true"'))
    guion = [editor, editor, editor, aviso, con_propia, con_propia, con_propia, visor]
    sim = TelefonoSimulado(guion)
    res, err = con_telefono_simulado(sim, lambda: FH.compartir(evid))
    check(err is None and res["estado"] == "confirmado" and sim.toques.count(boton) == 1 and sim.toques[0] == boton
          and res["visor"]["ok"], f"D compartir: un toque y visor propio de la Página ({err!r}, {res and res['estado']})")
    sim = TelefonoSimulado(guion)
    res, err = con_telefono_simulado(sim, lambda: FH.compartir(evid, produccion_cercana=True))
    check(err is None and res["estado"] == "confirmado_sin_prueba_unica", "D compartir con una Story de producción cerca: sin prueba única")
    sim = TelefonoSimulado([editor.replace("Sabiduria De Bolsillo", "Juan Pérez")])
    res, err = con_telefono_simulado(sim, lambda: FH.compartir(evid))
    check(isinstance(err, P.PantallaInesperada) and sim.toques == [], "D compartir sin la Página: no se pulsa")
    boton_opciones = P.nodo(editor, FP.PAQUETE, texto=FP.T["opciones_historia"])["centro"]
    guion_opciones = [editor, opciones, opciones, opciones, editor]
    sim = TelefonoSimulado(guion_opciones)
    res, err = con_telefono_simulado(sim, lambda: FH.opciones(evid))
    check(err is None and sim.toques == [boton_opciones] and sim.teclas == [pasos.ATRAS] and "copia_instagram" in res
          and sim.capturas == ["fbh-04-opciones.png", "fbh-04b-editor.png"],
          f"D opciones: lee «Compartir en Instagram» sin cambiarlo y vuelve al editor ({err!r}, {sim.toques})")
    for nombre_paso, guion_paso, accion in (
            ("abrir", [inicio, creador], lambda: FH.abrir(evid)),
            ("elegir", [creador, editor], lambda: FH.elegir(evid, subida)),
            ("opciones", guion_opciones, lambda: FH.opciones(evid))):
        sim = TelefonoSimulado(guion_paso)
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and not toques_sobre_envio(sim, FP.PAQUETE),
              f"C1 D {nombre_paso}: fuera de compartir, ningún toque cae sobre un control de envío ({err!r}, {sim.toques})")
    musica_h = fixture("facebook", "musica")
    cab_h = T.buscar(musica_h, texto=FP.T["sugeridas"], paquete=FP.PAQUETE)
    fila_h = next(n for n in T.nodos(musica_h) if n["package"] == FP.PAQUETE and n["clickable"] and n["bounds"][1] >= cab_h["bounds"][3])
    musica_h_tema = con_nodo(musica_h, nodo_xml("[%d,%d][%d,%d]" % (fila_h["bounds"][0] + 1, fila_h["bounds"][1] + 1,
                                                                    fila_h["bounds"][0] + 400, fila_h["bounds"][1] + 40),
                                                texto="Autumn Days", paquete=FP.PAQUETE))
    colocado_fb = jerarquia(nodo_xml("[0,100][1080,2020]", clase="android.widget.ImageView", paquete=FP.PAQUETE),
                            nodo_xml("[240,960][840,1360]", clase="android.widget.FrameLayout", paquete=FP.PAQUETE,
                                     hijos=nodo_xml("[260,980][820,1040]", texto="Autumn Days", paquete=FP.PAQUETE)))
    # si S1 muestra «Música» en otra pantalla, se cambia el flujo (FH.audio), no esta prueba
    check(T.buscar(editor, texto=FP.T["musica"], paquete=FP.PAQUETE) is not None, "S1: «Música» en historia-editor")
    for nombre_paso, guion_paso, accion in (
            ("audio", [editor, musica_h_tema, musica_h_tema, editor], lambda: FH.audio(evid)),
            ("sticker-musica", [colocado_fb, colocado_fb, colocado_fb],
             lambda: FH.sticker_musica(evid, (140, 760, 940, 1360), "Autumn Days · Morunas"))):
        sim = TelefonoSimulado(guion_paso)
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and not toques_sobre_envio(sim, FP.PAQUETE),
              f"C1 D {nombre_paso}: camino feliz sin tocar controles de envío ({err!r}, {sim.toques})")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `ImportError: cannot import name 'facebook_historia' from 'labkit'`.

- [ ] **Step 3: Implementar `facebook_historia.py`**

`experiments/media-lab/labkit/facebook_historia.py`:

```python
"""
Story de la Página de Facebook por teléfono, un paso por llamada (flujo D de la fase 2).

abrir → elegir → audio → [sticker-musica] → QA → compartir. La identidad de la Página se exige en el
creador y antes de compartir; el conmutador «Compartir en Instagram» se lee y no se cambia.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from labkit import facebook_feed, facebook_pantallas as fp
from labkit import pantalla, pasos, reloj, stickers, telefono
from labkit.pantalla import PantallaInesperada

T = fp.T
VISOR_MAX_S = 180


def _lanzar() -> str:
    """Facebook en el inicio con la Página activa (mismo arranque que el feed, sin captura)."""
    xml = pasos.lanzar_app(fp.PAQUETE, "facebook", listo=lambda x: fp.inicio_listo(x) or fp.interstitial(x) is not None,
                           borrador=lambda x: fp.compositor_abierto(x) or fp.editor_historia_fb_listo(x),
                           descripcion="Facebook listo (inicio o interstitial conocido)")
    if not fp.inicio_listo(xml):
        pasos.tocar(fp.interstitial(xml), xml, fp.PAQUETE)
        xml = pasos.esperar_que(fp.inicio_listo, "el inicio de Facebook tras el interstitial", app="facebook")
    if not fp.identidad_pagina(xml):
        raise PantallaInesperada(f"Facebook no está con la Página «{fp.PAGINA}» activa: no se toca nada")
    return xml


def abrir(evidencia: Path) -> dict:
    xml = _lanzar()
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, texto=T["crear_historia"]), xml, fp.PAQUETE)
    xml, _ = pasos.esperar_estable(fp.creador_historia_listo, descripcion="el creador de historias")
    if not fp.identidad_pagina(xml):
        raise PantallaInesperada(f"el creador de historias no es el de «{fp.PAGINA}»")
    return {"captura": str(telefono.captura(evidencia / "fbh-01-creador.png"))}


def elegir(evidencia: Path, subido_en: datetime) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(lambda x: facebook_feed._hay_miniatura(x, subido_en), "la miniatura de la subida", app="facebook")
    pasos.tocar(fp.miniatura_galeria(xml, subido_en), xml, fp.PAQUETE)
    pasos.esperar_que(fp.editor_historia_fb_listo, "el editor de la historia", app="facebook")
    return {"captura": str(telefono.captura(evidencia / "fbh-02-editor.png"))}


def audio(evidencia: Path) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(fp.editor_historia_fb_listo, "el editor de la historia", app="facebook")
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, texto=T["musica"]), xml, fp.PAQUETE)
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["sugeridas"], paquete=fp.PAQUETE) is not None,
                            "la música sugerida", app="facebook")
    sugerido = fp.tema_sugerido(xml)
    pasos.tocar(sugerido["nodo"], xml, fp.PAQUETE)
    reloj.dormir(1)
    facebook_feed._tocar_si_hay(T["listo"])
    pasos.esperar_que(fp.editor_historia_fb_listo, "el editor con la música", app="facebook")
    return {"tema": sugerido["tema"], "captura": str(telefono.captura(evidencia / "fbh-03-audio.png"))}


def sticker_musica(evidencia: Path, zona: tuple[int, int, int, int], tema: str) -> dict:
    """El sticker de música que crea `audio` se lleva a la zona reservada (story_image_music)."""
    pasos.exigir_listo()
    titulo = tema.split(" · ")[0]
    colocado = pasos.colocar_sticker(lambda x: stickers.bounds_sticker_texto(x, fp.PAQUETE, titulo), zona, fp.PAQUETE,
                                     evidencia, "fbh-03b-sticker-musica")
    return {"tema": tema, **colocado}


def _visor_propio(evidencia: Path, nombre: str) -> dict:
    xml = pasos.esperar_que(lambda x: telefono.buscar(x, empieza=T["tu_historia"], paquete=fp.PAQUETE) is not None,
                            "la historia propia en el inicio", app="facebook")
    if not (fp.inicio_listo(xml) and fp.identidad_pagina(xml)):
        raise PantallaInesperada("la historia propia solo se abre desde el inicio con la Página activa")
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, empieza=T["tu_historia"]), xml, fp.PAQUETE,
                permitir=(T["tu_historia"],))  # abre el visor, no publica
    xml = pasos.esperar_que(lambda x: any(telefono.buscar(x, texto=T[k], paquete=fp.PAQUETE)
                                          for k in ("agregar_nueva", "compartir_como_publicacion")),
                            "el visor de la historia propia", app="facebook")
    lectura = fp.historia_propia_fb(xml, VISOR_MAX_S)
    lectura["captura"] = str(telefono.captura(evidencia / f"{nombre}.png"))
    return lectura


def compartir(evidencia: Path, produccion_cercana: bool = False) -> dict:
    """Comparte la historia con un solo toque y confirma en el visor propio de la Página."""
    pasos.exigir_listo()

    def despues(resultado: dict, estado: str) -> str:
        avisos = resultado["avisos"]
        lectura = None
        try:
            if telefono.estado()["listo"]:
                lectura = _visor_propio(evidencia, "fbh-06-visor")
                resultado["visor"] = lectura
            else:
                avisos.append("tras compartir el teléfono no está listo: no se abrió la historia propia")
        except (PantallaInesperada, telefono.TelefonoError) as e:
            avisos.append(f"no se pudo abrir la historia propia: {e}")
        return pantalla.estado_confirmado(
            estado, lectura, produccion_cercana, avisos,
            "producción publicó una Story de Facebook cerca: concilia pasando al revisor fbh-06-visor.png y el máster")

    return pasos.enviar(
        paquete=fp.PAQUETE, nombre_app="Facebook", etiqueta=T["compartir_historia"], evidencia=evidencia,
        captura_antes="fbh-05a-antes.png", captura_final="fbh-07-final.png", captura_error="fbh-05-error.png",
        listo=lambda x, emergentes: fp.destino_historia_fb(x)["problemas"],
        botones=lambda x: telefono.buscar_todos(x, texto=T["compartir_historia"], paquete=fp.PAQUETE),
        observador_nuevo=lambda boton: (lambda x: fp.observacion_historia_fb(x, boton["bounds"])),
        despues=despues, extra={"visor": None})


def actividad(evidencia: Path) -> dict:
    """Estadísticas por teléfono cuando la API no las da: abre la historia propia y desliza hacia arriba."""
    _lanzar()
    lectura = _visor_propio(evidencia, "fbh-08-visor")
    alto = pantalla.alto_volcado(pasos.volcado_fresco())
    telefono.arrastrar(540, round(alto * 0.85), 540, round(alto * 0.45), telefono.DURACION_MINIMA_ARRASTRE_MS)
    reloj.dormir(2)
    return {"visor": lectura, "captura": str(telefono.captura(evidencia / "fbh-09-actividad.png"))}
```

y añadir tras `sticker_musica`:

```python
def opciones(evidencia: Path) -> dict:
    """Lee sin cambiarlo el conmutador «Compartir en Instagram» donde lo situó S1 (las opciones de la historia)
    y vuelve al editor con «atrás»."""
    pasos.exigir_listo()
    xml = pasos.esperar_que(fp.editor_historia_fb_listo, "el editor de la historia", app="facebook")
    pasos.tocar(pantalla.nodo(xml, fp.PAQUETE, texto=T["opciones_historia"]), xml, fp.PAQUETE)
    xml, _ = pasos.esperar_estable(
        lambda x: telefono.buscar(x, texto=T["compartir_en_instagram"], paquete=fp.PAQUETE) is not None,
        descripcion="las opciones de la historia")
    copia = fp.copia_instagram_historia(xml)
    captura = str(telefono.captura(evidencia / "fbh-04-opciones.png"))
    pasos.atras(fp.PAQUETE, evidencia, "fbh-04b-editor")
    pasos.esperar_que(fp.editor_historia_fb_listo, "el editor tras las opciones", app="facebook")
    return {"copia_instagram": copia, "captura": captura}
```

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/facebook_historia.py tests/test_media_lab.py
git commit -m "media lab claude: pasos de la Story de la Página de Facebook con visor propio y opciones leídas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 15c: D. Story de la Página de Facebook — `lab.py fb-historia`, recetas en borrador y prompt

**Files:**
- Modify: `experiments/media-lab/lab.py`, `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de `lab.py fb-historia` y de las recetas**

Añadir al final de `seccion_facebook_historia`:

```python
    from labkit import recetas as RC
    check(("facebook", "story_image") in RC.TODAS and ("facebook", "story_image_music") in RC.BORRADORES,
          "D: recetas de Story de la Página; la de música espera a S2")
    with entorno_lab_fase2() as (lab, raiz):
        for args, fragmento, label in ((("fb-historia", "elegir", "--run", "R"), "--subido-en", "elegir sin --subido-en"),
                            (("fb-historia", "sticker-musica", "--run", "R", "--tema", "T"), "--zona", "sticker-musica sin --zona")):
            sim = TelefonoSimulado([inicio])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0, f"fb-historia rechaza {label}")
    check(any(c["args"][:2] == ["fb-historia", "opciones"] for c in RC.TODAS[("facebook", "story_image")]["preparar"]),
          "D: la receta lee «Compartir en Instagram» en las opciones antes de la QA")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «D: recetas de Story de la Página…», «D: la receta lee «Compartir en Instagram»…» y los rechazos de `fb-historia` (argparse no conoce el subcomando: el mensaje no nombra el argumento).

- [ ] **Step 3: Implementar `lab.py fb-historia` y las recetas**

En `lab.py`, junto a `PASOS_FB`:

```python
PASOS_FB_HISTORIA = ("abrir", "elegir", "audio", "opciones", "sticker-musica", "compartir", "actividad")


def cmd_fb_historia(a) -> int:
    from labkit import facebook_historia as fbh
    ev = _evidencia(a.run)
    subidas = _subidas(a.subido_en)
    zona = _zona(a.zona)
    if a.paso == "elegir":
        _exigir(len(subidas) == 1, "elegir exige un --subido-en (lo devuelve telefono-subir)")
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    if a.paso == "sticker-musica":
        _exigir(zona is not None and bool(a.tema), "sticker-musica exige --zona y --tema")
    pasos_ = {
        "abrir": lambda: fbh.abrir(ev),
        "elegir": lambda: fbh.elegir(ev, subidas[0]),
        "audio": lambda: fbh.audio(ev),
        "opciones": lambda: fbh.opciones(ev),
        "sticker-musica": lambda: fbh.sticker_musica(ev, zona, a.tema),
        "compartir": lambda: fbh.compartir(ev, produccion_cercana=a.produccion_cercana),
        "actividad": lambda: fbh.actividad(ev),
    }
    return _paso_telefono(ev, f"fbh-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))
```

y en `construir`: `_parser_flujo(sub, "fb-historia", PASOS_FB_HISTORIA, cmd_fb_historia)`.

En `recetas.py`, antes de `TODAS`:

```python
HISTORIA_FACEBOOK = {
    "subcomando": "fb-historia",
    "superficie": "story",
    "formato_encargo": {"ancho": 1080, "alto": 1920},
    "preparar": [
        _cmd("telefono-subir", "--local", "<master>", ver="JSON con sha256 y subido_en; no hay captura", anota=("subido_en",)),
        _cmd("fb-historia", "abrir", "--run", "<run>", ver="fbh-01-creador.png: creador de historias de la Página"),
        _cmd("fb-historia", "elegir", "--run", "<run>", "--subido-en", "<subido_en>", ver="fbh-02-editor.png: la imagen completa en el editor"),
        _cmd("fb-historia", "audio", "--run", "<run>", ver="fbh-03-audio.png: tema añadido (captura de la QA)", anota=("tema",)),
        _cmd("fb-historia", "opciones", "--run", "<run>",
             ver="fbh-04-opciones.png: «Compartir en Instagram» leído sin cambiarlo; fbh-04b-editor.png: de vuelta en el editor",
             anota=("copia_instagram",)),
    ],
    "publicar": [
        _cmd("fb-historia", "compartir", "--run", "<run>", "[--produccion-cercana]",
             ver="fbh-06-visor.png: historia propia con «Sabiduria De Bolsillo», edad reciente y «Agregar nueva»; "
                 "--produccion-cercana solo si el preflight trae una Story de Facebook de producción en el margen"),
    ],
    "verificar": [],
    "estados_ok": ["confirmado"],
    "conciliacion": ("Con confirmado_sin_prueba_unica, pasa al revisor fbh-06-visor.png y el máster. Con sin_confirmacion, "
                     "timeout o fallido, fb-historia actividad y compara con el máster antes de registrar; nunca por la otra ruta."),
    "copias": [],
    "verificacion": ("Captura del visor propio; métricas en la primera ventana con la Story entre 4 h y 20 h o, "
                     "si no hubo, en la última antes de 24 h (paso 8 del prompt)."),
    "nota": "story_image: música añadida con el estilo más discreto que ofrezca Facebook.",
}

HISTORIA_FACEBOOK_MUSICA = {
    **HISTORIA_FACEBOOK,
    "formato_encargo": {"ancho": 1080, "alto": 1920, "zona_reservada": [140, 760, 940, 1360]},
    "preparar": HISTORIA_FACEBOOK["preparar"] + [
        _cmd("fb-historia", "sticker-musica", "--run", "<run>", "--zona", "<zona_reservada>", "--tema", "<tema>",
             ver="fbh-03b-sticker-musica.png: sticker del tema dentro de la zona reservada sin tapar texto"),
    ],
    "nota": "story_image_music: sticker de música visible dentro de la zona reservada.",
}
```

y a `TODAS`:

```python
    ("facebook", "story_image"): HISTORIA_FACEBOOK,
    ("facebook", "story_image_music"): HISTORIA_FACEBOOK_MUSICA,
```

Si S1, `fb-historia opciones` o la ventana manual muestran «Compartir en Instagram» activo por defecto, poner en `HISTORIA_FACEBOOK` `"copias": [{"red": "instagram", "superficie": "story", "nota": "Facebook copia la historia en Instagram: publication.cross_posting"}]`: la exclusión en la ventana se aplica sola.

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/lab.py experiments/media-lab/labkit/recetas.py tests/test_media_lab.py
git commit -m "media lab claude: lab.py fb-historia y recetas de Story de la Página en borrador

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 5: Prompt de la ventana**

Añadir al final de `seccion_prompt_ventana`:

```python
    for fragmento in ("fb-historia actividad",):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «el prompt de la ventana menciona …» para esos fragmentos.

En `experiments/media-lab/claude-ventana-prompt.md`:

Tras la frase «y guárdalas en sus runs.» del paso 8, añadir:

```markdown
 Story de Facebook sin métricas por otra vía y con el teléfono listo: `lab.py fb-historia actividad --run RUN` y lee la captura; si tampoco, anótalo en `missing_data_reasons` del run.
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana mide las Stories de la Página por teléfono con fb-historia actividad

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 6: Actualizar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno» y «fb-historia actividad».

---

### Task 15d: D. Story de la Página de Facebook — ventana manual y promoción

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/findings.md`, `experiments/media-lab/coverage.json`, `experiments/media-lab/runs/<run>.json`, `experiments/media-lab/progress.md`, `tests/test_media_lab.py`
- Create: `tests/fixtures/telefono/facebook/historia-visor-propio.xml` si S1 no lo tenía

- [ ] **Step 1: Primera publicación en ventana manual, `findings.md` y promoción**

Igual que los Steps 1 y 2 de la tarea 11d, con la celda `ready` (CELL-007 u otra) o la primera `planned` de `facebook/story_image/android_native`, sin ninguna celda de Instagram por teléfono en esa ventana. Tras `confirmado`, el usuario abre a mano la historia propia desde el inicio (la sonda no toca «Tu historia») y Claude vuelca con `lab.py sonda facebook volcar --run SONDA-F2-D --supervisada --nombre visor-propio` y `fixture-podar --app facebook --pantalla historia-visor-propio` si S1 no lo tenía. En `findings.md`, «Primera Story de la Página por teléfono (<fecha>, <run>)» con el estado de «Compartir en Instagram» y si Facebook la copió. En `recetas.py`, añadir a `PROMOVIDAS` `("facebook", "story_image"): "<run>: primera Story de la Página por teléfono confirmada (<fecha>)"` y, al final de `seccion_facebook_historia`, `check(("facebook", "story_image") in RC.RECETAS, "D: story_image de la Página promovida")`.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/findings.md experiments/media-lab/coverage.json experiments/media-lab/runs/<run>.json experiments/media-lab/progress.md tests/test_media_lab.py tests/fixtures/telefono/facebook/historia-visor-propio.xml
git commit -m "media lab claude: primera Story de la Página por teléfono confirmada; story_image de Facebook promovida

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

Con el push hecho, `lab.py lock-soltar --dueno manual`: la sesión edita, comitea y hace push con el cerrojo tomado.

---

### Task 16a: E. Encuestas — zona reservada en encargos y másters (spec, fila 10)

Depende de las tareas 11, 12 y 15. Añade la zona reservada a encargos y másters, la encuesta en las Stories de Instagram y Facebook y en Threads, valida el arrastre con S2 y promueve `story_image_music` (Instagram y Facebook), `story_poll` (Instagram y Facebook) y `threads/feed_poll`. Si S2 demuestra que `input swipe` no mueve el sticker, esas cinco celdas pasan a `blocked` (decisión 2: no se sustituye por la pregunta impresa) y el motivo va a `progress.md`.

**Files:**
- Modify: `experiments/media-lab/render_overlay.py`, `experiments/media-lab/labkit/encargos.py`, `experiments/media-lab/lab.py` (`render --zona`)
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de la zona reservada**

Añadir antes de `SECCIONES` y registrar `seccion_encuestas,`:

```python
def seccion_encuestas() -> None:
    print("\n25. Fase 2 (E): encuestas y zona reservada")
    import importlib.util
    import tempfile
    from datetime import datetime, timezone
    from PIL import Image
    from labkit import encargos as E

    spec = importlib.util.spec_from_file_location("render_overlay", ROOT / "experiments" / "media-lab" / "render_overlay.py")
    RO = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(RO)
    comunes = dict(lines=["UNA", "DOS", "TRES"], sub="Autor · 1843", panel_rgb=(5, 39, 73), accent_rgb=(176, 220, 236),
                   disclosure="")
    with tempfile.TemporaryDirectory() as d:
        fuente = pathlib.Path(d) / "fuente.png"
        Image.new("RGB", (1080, 1920), (90, 70, 50)).save(fuente)
        destino = pathlib.Path(d) / "master.jpg"
        RO.render(fuente, destino, output_format="story", zona_reservada=(140, 760, 940, 1360), **comunes)
        check(destino.is_file(), "render_overlay con zona reservada libre escribe el máster de Story")
        for zona, formato, label in (((0, 500, 1080, 900), "story", "una zona que pisa el panel de texto"),
                                     ((0, 1700, 1080, 1850), "story", "una zona que pisa la firma"),
                                     ((140, 760, 940, 1300), "feed", "una zona en un máster de feed")):
            try:
                RO.render(fuente, pathlib.Path(d) / "x.jpg", output_format=formato, zona_reservada=zona, **comunes)
                ok = False
            except ValueError:
                ok = True
            check(ok, f"render_overlay rechaza {label}")

    t = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)

    def encargo(formato):
        return E.nuevo("ENC-20260916-001", coverage_cell_ids=["C"], family_id="F", brief_path="b", do_not_use=[],
                       formato=formato, prompt="p", restricciones=[], destino_assets="experiments/media-lab/assets/F", ahora=t)

    check(encargo({"ancho": 1080, "alto": 1920, "zona_reservada": [140, 760, 940, 1360]})["formato"]["zona_reservada"]
          == [140, 760, 940, 1360], "encargo de Story con zona reservada")
    for formato, label in (({"ancho": 1080, "alto": 1920, "zona_reservada": [140, 760, 1200, 1360]}, "zona fuera de 1080"),
                           ({"ancho": 1080, "alto": 1920, "zona_reservada": [940, 760, 140, 1360]}, "zona invertida"),
                           ({"ancho": 1080, "alto": 1350, "zona_reservada": [140, 760, 940, 1300]}, "zona en un encargo de feed"),
                           ({"ancho": 1080, "alto": 1920, "zona_reservada": [140, 760, 940]}, "zona de tres números")):
        try:
            encargo(formato)
            ok = False
        except E.EncargoError:
            ok = True
        check(ok, f"encargo-nuevo rechaza {label}")

    with entorno_lab_fase2() as (lab, raiz):
        for args, fragmento, label in ((("--formato", "feed", "--zona", "140,760,940,1360"), "story", "--zona en un máster de feed"),
                                       (("--formato", "story", "--zona", "140,760"), "--zona", "--zona de dos números")):
            sim = TelefonoSimulado([xml_perfil()])
            res, err = con_telefono_simulado(sim, lambda: lab("render", "--encargo", "ENC-20260916-001", "--titular", "A|B|C",
                                                              "--subtitulo", "S", "--salida", "m.jpg", *args))
            check(rechazo(res, fragmento), f"lab.py render rechaza {label} antes de leer el encargo ({res and res[0]})")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `TypeError: render() got an unexpected keyword argument 'zona_reservada'` en la sección 25.

- [ ] **Step 3: Implementar la zona en `render_overlay.py` y `encargos.py`**

En `render_overlay.py`, añadir tras `parse_rgb`:

```python
STORY_SIZE = (1080, 1920)


def parse_zona(value: str) -> tuple[int, int, int, int]:
    try:
        parts = tuple(int(part) for part in value.split(","))
    except ValueError as e:
        raise argparse.ArgumentTypeError("zona must be x1,y1,x2,y2 integers") from e
    if len(parts) != 4 or not (0 <= parts[0] < parts[2] <= STORY_SIZE[0] and 0 <= parts[1] < parts[3] <= STORY_SIZE[1]):
        raise argparse.ArgumentTypeError("zona must be x1,y1,x2,y2 inside the 1080x1920 story master")
    return parts


def _intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
```

sustituir la firma de `render` por:

```python
def render(
    source: Path,
    destination: Path,
    lines: list[str],
    sub: str,
    panel_rgb: tuple[int, int, int],
    accent_rgb: tuple[int, int, int],
    output_format: str,
    disclosure: str,
    zona_reservada: tuple[int, int, int, int] | None = None,
) -> None:
```

añadir, justo después de `is_story = output_format == "story"`:

```python
    if zona_reservada is not None and not is_story:
        raise ValueError("zona_reservada solo vale en un máster de Story (1080x1920)")
    boxes: list[tuple[int, int, int, int]] = []  # todo lo que se dibuja con texto o panel
```

añadir `boxes.append((54, panel_top, 1026, panel_bottom))` tras dibujar el panel, `boxes.append((x, y, x + box[2] - box[0], y + box[3] - box[1]))` tras cada `draw.text` de las líneas, `boxes.append((bx, brand_top, 1030, brand_top + 53))` tras el rectángulo de la firma y `boxes.append((50, disclosure_top, 50 + disclosure_width + 2 * pad, disclosure_top + 53))` tras el del aviso; y justo antes de `image = Image.alpha_composite(...)`:

```python
    if zona_reservada is not None:
        invaded = [b for b in boxes if _intersects(b, zona_reservada)]
        if invaded:
            raise ValueError(f"text would be drawn inside the reserved zone {zona_reservada}: {invaded}")
```

En `main`, añadir `parser.add_argument("--zona", type=parse_zona, default=None, help="x1,y1,x2,y2 reserved for a native sticker (story only)")` y pasar `args.zona` como último argumento de `render`.

En `lab.py` (tarea 15 de la fase 1), en el parser de `render` añadir `p.add_argument("--zona", help="x1,y1,x2,y2 reservada para un sticker nativo (solo --formato story)")`; en `cmd_render`, como primeras líneas tras los `import`:

```python
    zona = _zona(a.zona)
    _exigir(zona is None or a.formato == "story", "--zona solo vale con --formato story")
```

y en su `try`, pasar `zona_reservada=zona` como último argumento de `render_overlay.render(...)` y añadir antes del `finally`:

```python
    except ValueError as e:  # render_overlay no escribe texto dentro de la zona reservada
        return _rechazo("ImagenNoValida", [f"--zona: {e}"])
```

En `encargos.py`, añadir tras `_entero_positivo`:

```python
def _zona_valida(zona: object) -> bool:
    return (isinstance(zona, list) and len(zona) == 4
            and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in zona)
            and zona[0] < zona[2] <= 1080 and zona[1] < zona[3] <= 1920)
```

y en `nuevo`, tras la comprobación de `formato`:

```python
    if "zona_reservada" in formato:
        if (formato["ancho"], formato["alto"]) != (1080, 1920):
            raise EncargoError("zona_reservada solo en encargos de Story de 1080×1920")
        if not _zona_valida(formato["zona_reservada"]):
            raise EncargoError("zona_reservada debe ser [x1, y1, x2, y2] dentro de 1080×1920")
```

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 25 en `✓` y `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/render_overlay.py experiments/media-lab/labkit/encargos.py experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: zona reservada en encargos de Story y másters que no escriben texto dentro

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16b-1: E. Encuestas — encuesta en Stories con teléfono simulado

**Files:**
- Modify: `experiments/media-lab/labkit/pantalla.py`, `experiments/media-lab/labkit/stickers.py`, `experiments/media-lab/labkit/pasos.py`, `experiments/media-lab/labkit/textos.py`, `experiments/media-lab/labkit/instagram_historia.py`, `experiments/media-lab/labkit/facebook_historia.py`, `experiments/media-lab/lab.py`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Texto de la encuesta de Instagram**

Añadir a `TEXTOS["instagram"]` `"sondage": "Sondage",  # confirmar contra el fixture de S1`.

- [ ] **Step 2: Escribir la prueba de la encuesta en Stories**

Añadir antes de `SECCIONES`:

```python
PREGUNTA_ENCUESTA = "¿Qué prefieres para la próxima?"
OPCIONES_ENCUESTA = ["Trivia", "Misterio"]


def xml_encuesta_editando(paquete: str, hecho: str, pregunta: str = "", op1: str = "", op2: str = "") -> str:
    """Editor sintético del sticker de encuesta: lienzo 9:16, botón de terminar y tres campos."""
    return jerarquia(
        nodo_xml("[0,100][1080,2020]", clase="android.widget.ImageView", paquete=paquete),
        nodo_xml("[860,20][1060,90]", texto=hecho, clase="android.widget.Button", paquete=paquete, extra='clickable="true"'),
        nodo_xml("[180,340][900,420]", texto=pregunta, clase="android.widget.EditText", paquete=paquete),
        nodo_xml("[180,460][900,540]", texto=op1, clase="android.widget.EditText", paquete=paquete),
        nodo_xml("[180,580][900,660]", texto=op2, clase="android.widget.EditText", paquete=paquete))


def xml_encuesta_colocada(paquete: str, x1: int, y1: int, x2: int, y2: int) -> str:
    """El sticker de encuesta ya terminado sobre el lienzo, en los bounds dados."""
    return jerarquia(
        nodo_xml("[0,100][1080,2020]", clase="android.widget.ImageView", paquete=paquete),
        nodo_xml(f"[{x1},{y1}][{x2},{y2}]", clase="android.widget.FrameLayout", paquete=paquete,
                 hijos=nodo_xml(f"[{x1 + 20},{y1 + 20}][{x2 - 20},{y1 + 80}]", texto=PREGUNTA_ENCUESTA, paquete=paquete)))
```

y al final de `seccion_encuestas`:

```python
    print("   · encuesta escrita, pegada y colocada")
    import pathlib as _p
    from labkit import facebook_historia as FH, instagram_historia as IGH, pantalla as P, pasos, stickers as ST
    from labkit import telefono as T, textos as TX, threads_feed as TH, threads_pantallas as TP

    evid = _p.Path("evidencia-simulada")
    completa = xml_encuesta_editando(PAQUETE_IG, "Terminé", PREGUNTA_ENCUESTA, *OPCIONES_ENCUESTA)
    check(ST.encuesta_escrita(completa, PREGUNTA_ENCUESTA, OPCIONES_ENCUESTA, "instagram") == [],
          "encuesta_escrita: pregunta y opciones exactas")
    check(len(ST.encuesta_escrita(xml_encuesta_editando(PAQUETE_IG, "Terminé", PREGUNTA_ENCUESTA, "Trivia", "Misterio."),
                                  PREGUNTA_ENCUESTA, OPCIONES_ENCUESTA, "instagram")) == 1,
          "encuesta_escrita señala una opción parecida")

    for app, paquete, editor_fx, panel_fx, etiqueta, hecho, modulo, prefijo in (
            ("instagram", PAQUETE_IG, "historia-editor", "historia-stickers", TX.TEXTOS["instagram"]["sondage"],
             TX.TEXTOS["instagram"]["terminado"], IGH, "igh-03c-encuesta.png"),
            ("facebook", "com.facebook.katana", "historia-editor", "historia-stickers", TX.TEXTOS["facebook"]["encuesta"],
             TX.TEXTOS["facebook"]["listo"], FH, "fbh-03c-encuesta.png")):
        editor = fixture(app, editor_fx)
        panel = fixture(app, panel_fx)
        vacia = xml_encuesta_editando(paquete, hecho)
        con_p = xml_encuesta_editando(paquete, hecho, PREGUNTA_ENCUESTA)
        con_p1 = xml_encuesta_editando(paquete, hecho, PREGUNTA_ENCUESTA, OPCIONES_ENCUESTA[0])
        llena = xml_encuesta_editando(paquete, hecho, PREGUNTA_ENCUESTA, *OPCIONES_ENCUESTA)
        fuera = xml_encuesta_colocada(paquete, 140, 300, 940, 700)
        dentro = xml_encuesta_colocada(paquete, 240, 960, 840, 1360)
        guion = [editor, panel, vacia, con_p, con_p1, llena, llena, llena, llena, fuera, fuera, fuera, dentro]
        encuesta = {"pregunta": PREGUNTA_ENCUESTA, "opciones": OPCIONES_ENCUESTA}
        sim = TelefonoSimulado(guion)
        res, err = con_telefono_simulado(sim, lambda: modulo.encuesta(evid, encuesta, (140, 760, 940, 1360)))
        check(err is None and sim.pegados == [PREGUNTA_ENCUESTA, *OPCIONES_ENCUESTA] and len(sim.arrastres) == 1
              and sim.toques[1] == P.nodo(panel, paquete, texto=etiqueta)["centro"] and sim.toques[-1] == (960, 55)
              and sim.capturas == [prefijo] and not toques_sobre_envio(sim, paquete),
              f"E {app}: encuesta pegada, releída, terminada y arrastrada una vez a la zona ({err!r}, {sim.toques})")
        sim = TelefonoSimulado(guion[:-1])
        res, err = con_telefono_simulado(sim, lambda: modulo.encuesta(evid, encuesta, (140, 760, 940, 1360)))
        check(isinstance(err, P.PantallaInesperada) and len(sim.arrastres) == ST.ARRASTRES_MAX and sim.capturas == [],
              f"E {app}: si no entra en la zona tras 2 arrastres, PantallaInesperada y la celda se abandona ({err!r})")

    with entorno_lab_fase2() as (lab, raiz):
        for args, fragmento, label in ((("ig-historia", "encuesta", "--run", "R", "--zona", "140,760,940,1360",
                                         "--encuesta", '{"pregunta": "P", "opciones": ["A", "B", "C"]}'), "opciones", "tres opciones en una Story"),
                                       (("ig-historia", "encuesta", "--run", "R", "--zona", "140,760,940,1360", "--encuesta", "{no"),
                                        "no es JSON", "JSON ilegible"),
                                       (("ig-historia", "encuesta", "--run", "R", "--encuesta", '{"pregunta": "P", "opciones": ["A", "B"]}'),
                                        "--zona", "sin --zona"),
                                       (("fb-historia", "encuesta", "--run", "R", "--zona", "140,760,940,1360",
                                         "--encuesta", '{"opciones": ["A", "B"]}'), "pregunta", "Story sin pregunta")):
            sim = TelefonoSimulado([xml_perfil()])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0, f"lab.py rechaza la encuesta: {label} ({res and res[0]})")
```

- [ ] **Step 3: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.stickers' has no attribute 'encuesta_escrita'`.

- [ ] **Step 4: Implementar la encuesta en Stories**

En `pantalla.py`, al final:

```python
def campos(xml: str, paquete: str) -> list[dict]:
    """Los campos de texto de `paquete` en orden de documento."""
    return [n for n in telefono.buscar_todos(xml, paquete=paquete) if n["clase"] in CLASES_CAMPO]
```

En `stickers.py`, cambiar `from labkit import pantalla, telefono` por `from labkit import pantalla, telefono, textos` y añadir al final:

```python
def encuesta_escrita(xml: str, pregunta: str | None, opciones: list[str], app: str) -> list[str]:
    """Problemas de la encuesta leída: la pregunta (si se da) y cada opción deben estar con el texto exacto."""
    paquete = textos.PAQUETES[app]
    problemas = []
    if pregunta is not None and not pantalla.tiene_texto(xml, texto=pregunta, paquete=paquete):
        problemas.append("la pregunta de la encuesta no coincide")
    problemas += [f"la opción {k} de la encuesta no coincide" for k, opcion in enumerate(opciones, 1)
                  if not pantalla.tiene_texto(xml, texto=opcion, paquete=paquete)]
    return problemas
```

En `pasos.py`, tras `escribir_texto`:

```python
def pegar_en(campo: dict, texto: str, paquete: str) -> str:
    """Toca el campo, pega `texto` con el portapapeles y relee: devuelve el volcado con el texto exacto.
    No cierra el teclado: dentro de un sticker, «atrás» lo descartaría."""
    exigir_listo()
    telefono.tocar(*campo["centro"])
    reloj.dormir(1)
    telefono.combinacion(CTRL_IZQ, TECLA_A)
    try:
        phone_clipboard.pegar(texto, paste=True)
    except (RuntimeError, OSError) as e:
        raise telefono.TelefonoError(f"portapapeles: {e}") from e
    reloj.dormir(1.5)
    xml = volcado_fresco()
    if not pantalla.tiene_texto(xml, texto=texto, paquete=paquete):
        raise PantallaInesperada("el texto pegado no se lee en el campo")
    return xml


def encuesta_de_historia(app: str, paquete: str, *, boton_stickers: str, etiqueta_encuesta: str, terminar: str,
                         encuesta: dict, zona: tuple[int, int, int, int], editor_listo, evidencia: Path, nombre: str) -> dict:
    """Sticker de encuesta clásica en una Story: panel de stickers → encuesta → pregunta y opciones pegadas
    y releídas con volcado estable → terminar → colocado en la zona reservada."""
    exigir_listo()
    pregunta, opciones = encuesta["pregunta"], encuesta["opciones"]
    xml = esperar_que(editor_listo, "el editor de la Story", app=app)
    tocar(pantalla.nodo(xml, paquete, texto=boton_stickers), xml, paquete)
    xml = esperar_que(lambda x: telefono.buscar(x, texto=etiqueta_encuesta, paquete=paquete) is not None,
                      f"«{etiqueta_encuesta}»", app=app)
    tocar(pantalla.nodo(xml, paquete, texto=etiqueta_encuesta), xml, paquete)
    xml = esperar_que(lambda x: len(pantalla.campos(x, paquete)) >= 1 + len(opciones), "los campos de la encuesta", app=app)
    for indice, texto in enumerate([pregunta, *opciones]):
        xml = pegar_en(pantalla.campos(xml, paquete)[indice], texto, paquete)
    xml, _ = esperar_estable(lambda x: stickers.encuesta_escrita(x, pregunta, opciones, app) == [],
                             descripcion="la encuesta escrita")
    tocar(pantalla.nodo(xml, paquete, texto=terminar), xml, paquete)
    reloj.dormir(2)
    colocado = colocar_sticker(lambda x: stickers.bounds_sticker_texto(x, paquete, pregunta), zona, paquete, evidencia, nombre)
    return {"encuesta": encuesta, **colocado}
```

En `instagram_historia.py`, al final:

```python
def encuesta(evidencia: Path, encuesta_: dict, zona: tuple[int, int, int, int]) -> dict:
    """Encuesta clásica de 2 opciones colocada en la zona reservada (story_poll)."""
    return pasos.encuesta_de_historia("instagram", PAQUETE, boton_stickers=T["autocollants"], etiqueta_encuesta=T["sondage"],
                                      terminar=T["terminado"], encuesta=encuesta_, zona=zona, editor_listo=editor_historia_listo,
                                      evidencia=evidencia, nombre="igh-03c-encuesta")
```

En `facebook_historia.py`, al final:

```python
def encuesta(evidencia: Path, encuesta_: dict, zona: tuple[int, int, int, int]) -> dict:
    """Encuesta clásica de 2 opciones colocada en la zona reservada (story_poll)."""
    return pasos.encuesta_de_historia("facebook", fp.PAQUETE, boton_stickers=T["stickers"], etiqueta_encuesta=T["encuesta"],
                                      terminar=T["listo"], encuesta=encuesta_, zona=zona, editor_listo=fp.editor_historia_fb_listo,
                                      evidencia=evidencia, nombre="fbh-03c-encuesta")
```

En `lab.py`, cambiar `PASOS_IG_HISTORIA` a `("abrir", "elegir", "audio", "sticker-musica", "encuesta", "destino", "compartir", "actividad")` y `PASOS_FB_HISTORIA` a `("abrir", "elegir", "audio", "opciones", "sticker-musica", "encuesta", "compartir", "actividad")`; añadir tras `_zona`:

```python
def _encuesta(texto: str | None, *, con_pregunta: bool, max_opciones: int) -> dict | None:
    if texto is None:
        return None
    try:
        datos = json.loads(texto)
    except ValueError as e:
        raise ArgumentoNoValido(f"--encuesta no es JSON: {e}") from e
    _exigir(isinstance(datos, dict), "--encuesta debe ser un objeto JSON")
    opciones = datos.get("opciones")
    _exigir(isinstance(opciones, list) and 2 <= len(opciones) <= max_opciones
            and all(isinstance(o, str) and o.strip() for o in opciones),
            f"--encuesta necesita entre 2 y {max_opciones} opciones de texto")
    _exigir(len(set(opciones)) == len(opciones), "--encuesta tiene opciones repetidas")
    if con_pregunta:
        _exigir(isinstance(datos.get("pregunta"), str) and bool(datos["pregunta"].strip()), "--encuesta necesita la pregunta")
    return {"pregunta": datos.get("pregunta"), "opciones": opciones}
```

En `cmd_ig_historia` y `cmd_fb_historia`, antes del dict de pasos:

```python
    encuesta = _encuesta(a.encuesta, con_pregunta=True, max_opciones=2)
    if a.paso == "encuesta":
        _exigir(encuesta is not None and zona is not None, "encuesta exige --encuesta y --zona")
```

y en el dict `"encuesta": lambda: igh.encuesta(ev, encuesta, zona),` (en `cmd_fb_historia`, `fbh.encuesta`).

- [ ] **Step 5: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/pantalla.py experiments/media-lab/labkit/stickers.py experiments/media-lab/labkit/pasos.py experiments/media-lab/labkit/textos.py experiments/media-lab/labkit/instagram_historia.py experiments/media-lab/labkit/facebook_historia.py experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: encuestas en Stories de Instagram y Facebook, pegadas, releídas y colocadas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16b-2: E. Encuestas — encuesta de Threads con teléfono simulado

**Files:**
- Modify: `experiments/media-lab/labkit/textos.py`, `experiments/media-lab/labkit/threads_pantallas.py`, `experiments/media-lab/labkit/threads_feed.py`, `experiments/media-lab/lab.py`
- Test: `tests/test_media_lab.py`; fixtures `tests/fixtures/telefono/threads/{adjuntos,encuesta}.xml` (S1)

- [ ] **Step 1: Textos de la encuesta de Threads**

Añadir a `TEXTOS["threads"]` `"adjuntos": "Plus",  # confirmar contra el fixture de S1 (botón que abre los adjuntos)`, `"opcion_1": "Option 1",  # confirmar contra el fixture de S1` y `"opcion_2": "Option 2",  # confirmar contra el fixture de S1`. Volver a podar `threads/adjuntos` y `threads/encuesta` desde sus volcados de S1.

- [ ] **Step 2: Escribir la prueba de la encuesta de Threads**

Añadir al final de `seccion_encuestas`:

```python
    print("   · encuesta de Threads")
    compositor = fixture("threads", "compositor-vacio")
    con_texto = con_valor(compositor, lambda n: n["resource_id"].endswith("/" + TP.ID_COMPOSITOR), TEXTO_THREAD)
    listo = con_valor(con_texto, lambda n: n["resource_id"].endswith("/" + TP.ID_PUBLICAR), "true", "enabled")
    adjuntos = fixture("threads", "adjuntos")
    vacia_th = fixture("threads", "encuesta")
    campos_th = TP.campos_encuesta(vacia_th)
    con1 = con_valor(vacia_th, lambda n: n["bounds"] == campos_th[0]["bounds"] and n["clase"] in P.CLASES_CAMPO, OPCIONES_ENCUESTA[0])
    con12 = con_valor(con1, lambda n: n["bounds"] == campos_th[1]["bounds"] and n["clase"] in P.CLASES_CAMPO, OPCIONES_ENCUESTA[1])
    previos = [listo] if TP.por_id(listo, TP.ID_ENCUESTA) else [listo, adjuntos]
    sim = TelefonoSimulado(previos + [vacia_th, con1, con12, con12, con12, con12], teclado=(False,))
    res, err = con_telefono_simulado(sim, lambda: TH.encuesta(OPCIONES_ENCUESTA, evid))
    check(err is None and sim.pegados == OPCIONES_ENCUESTA and sim.capturas == ["th-05b-encuesta.png"] and sim.teclas == []
          and not toques_sobre_envio(sim, TP.PAQUETE),
          f"E threads: opciones pegadas y releídas en la encuesta del compositor ({err!r}, {sim.toques})")
    check(any("opción" in p for p in TP.compositor_listo(listo, TEXTO_THREAD, False, None, opciones=["Otra", "Distinta"])),
          "E threads: compartir no da el compositor por listo si las opciones no están en pantalla")

    with entorno_lab_fase2() as (lab, raiz):
        for args, fragmento, label in ((("th", "encuesta", "--run", "R", "--encuesta", '{"opciones": ["A"]}'), "opciones", "una sola opción"),
                                       (("th", "encuesta", "--run", "R", "--encuesta", '{"opciones": ["A", "A"]}'), "repetidas", "opciones repetidas")):
            sim = TelefonoSimulado([xml_perfil()])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0, f"lab.py rechaza la encuesta: {label} ({res and res[0]})")
```

- [ ] **Step 3: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.threads_pantallas' has no attribute 'campos_encuesta'`.

- [ ] **Step 4: Implementar la encuesta de Threads**

En `threads_pantallas.py`, cambiar `from labkit import pantalla, telefono, textos` por `from labkit import pantalla, stickers, telefono, textos`, añadir:

```python
def campos_encuesta(xml: str) -> list[dict]:
    """Los campos de las opciones de la encuesta: los de texto que no son el compositor."""
    return [n for n in pantalla.campos(xml, PAQUETE) if not n["resource_id"].endswith("/" + ID_COMPOSITOR)]
```

y sustituir la firma de `compositor_listo` por `def compositor_listo(xml: str, texto: str | None, con_imagen: bool, tema: str | None, emergentes: list[dict] | None = None, opciones: list[str] | None = None) -> list[str]:` añadiendo antes de `return problemas`:

```python
    if opciones:
        problemas += stickers.encuesta_escrita(xml, None, opciones, "threads")
```

En `threads_feed.py`, añadir tras `musica`:

```python
def encuesta(opciones: list[str], evidencia: Path) -> dict:
    """Adjunta la encuesta (el texto del thread es la pregunta) y pega y relee cada opción; duración por defecto."""
    pasos.exigir_listo()
    xml = pasos.volcado_fresco()
    if not tp.por_id(xml, tp.ID_ENCUESTA):
        pasos.tocar(pantalla.nodo(xml, tp.PAQUETE, texto=tp.T["adjuntos"]), xml, tp.PAQUETE)
        xml = pasos.esperar_que(lambda x: bool(tp.por_id(x, tp.ID_ENCUESTA)), "el botón de encuesta", app="threads")
    pasos.tocar(tp.nodo_id(xml, tp.ID_ENCUESTA), xml, tp.PAQUETE)
    xml = pasos.esperar_que(lambda x: len(tp.campos_encuesta(x)) >= len(opciones), "los campos de la encuesta", app="threads")
    for indice, opcion in enumerate(opciones):
        xml = pasos.pegar_en(tp.campos_encuesta(xml)[indice], opcion, tp.PAQUETE)
    pasos.esperar_estable(lambda x: stickers.encuesta_escrita(x, None, opciones, "threads") == [],
                          descripcion="las opciones de la encuesta")
    if telefono.teclado_estado():
        telefono.tecla(pasos.ATRAS)
        reloj.dormir(1.5)
        if not tp.compositor_abierto(pasos.volcado_fresco()):
            raise PantallaInesperada("al cerrar el teclado se cerró el compositor")
    return {"opciones": opciones, "captura": str(telefono.captura(evidencia / "th-05b-encuesta.png"))}
```

cambiar `from labkit import pantalla, pasos, reloj, telefono` por `from labkit import pantalla, pasos, reloj, stickers, telefono`, y en `compartir` añadir el parámetro `opciones: list[str] | None = None` al final de la firma, cambiar `listo` por `lambda x, emergentes: tp.compositor_listo(x, texto_, con_imagen, tema, emergentes, opciones)` y, en `despues`, cambiar la condición de `esperar_estable` y la lectura por:

```python
                xml, _ = pasos.esperar_estable(
                    lambda x: tp.perfil_de_marca(x) and tp.thread_reciente(x, texto_)["ok"]
                    and all(pantalla.tiene_texto(x, texto=o, paquete=tp.PAQUETE) for o in (opciones or [])),
                    descripcion="el thread nuevo en el perfil")
                lectura = tp.thread_reciente(xml, texto_)
```

En `lab.py`, cambiar `PASOS_TH` a `("abrir", "nuevo", "texto", "galeria", "musica", "encuesta", "compartir")`. En `cmd_th`, antes del dict:

```python
    encuesta = _encuesta(a.encuesta, con_pregunta=False, max_opciones=4)
    if a.paso == "encuesta":
        _exigir(encuesta is not None, "encuesta exige --encuesta con las opciones")
    opciones = encuesta["opciones"] if encuesta else None
```

añadir `"encuesta": lambda: th.encuesta(opciones, ev),` y cambiar el de compartir por `th.compartir(texto, a.tema, bool(subidas), ev, produccion_cercana=a.produccion_cercana, opciones=opciones)`.

- [ ] **Step 5: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/textos.py experiments/media-lab/labkit/threads_pantallas.py experiments/media-lab/labkit/threads_feed.py experiments/media-lab/lab.py tests/test_media_lab.py tests/fixtures/telefono/threads
git commit -m "media lab claude: encuesta de Threads con opciones pegadas y releídas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16c: E. Encuestas — sonda S2 del arrastre (sin publicar)

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Create: `tests/fixtures/telefono/{instagram,facebook}/historia-encuesta-colocada.xml`
- Modify: `experiments/media-lab/findings.md`, `experiments/media-lab/labkit/stickers.py`, `experiments/media-lab/labkit/textos.py`, `tests/test_media_lab.py`; si falla, `experiments/media-lab/coverage.json` y `progress.md`

- [ ] **Step 1: Sonda S2 supervisada (sin publicar)**

Con el usuario presente y el teléfono listo:

1. Crear el máster de prueba: `.venv/bin/python experiments/media-lab/render_overlay.py <imagen 9:16 comiteada> experiments/media-lab/results/s2-master.jpg --format story --zona 140,760,940,1360` y subirlo con `lab.py telefono-subir --local experiments/media-lab/results/s2-master.jpg` (anotar `subido_en`).
2. Instagram (los runs `SONDA-F2-*` guardan sus capturas en `evidence/android/sondas-f2/`, ignorada por git): `lab.py ig-historia abrir --run SONDA-F2-S2-IG --subido-en <subido_en>`, `ig-historia elegir …`, `ig-historia encuesta --run SONDA-F2-S2-IG --encuesta '{"pregunta": "¿Qué prefieres para la próxima?", "opciones": ["Trivia", "Misterio"]}' --zona 140,760,940,1360`, mirando cada captura. Luego `lab.py sonda instagram volcar --run SONDA-F2-S2-IG --supervisada --nombre encuesta-colocada`. Probar también `ig-historia audio` y `ig-historia sticker-musica --zona 140,760,940,1360 --tema <tema>` en el mismo borrador y volcar `sticker-musica-colocado`.
3. Salir sin publicar: `lab.py telefono-atras --app instagram --run SONDA-F2-S2-IG --nombre salida-N` hasta ver el diálogo y `lab.py telefono-descartar --app instagram --run SONDA-F2-S2-IG --nombre descarte`.
4. Facebook: lo mismo con `fb-historia abrir/elegir/audio/encuesta/sticker-musica`, run `SONDA-F2-S2-FB`, y salida con `--app facebook`.
5. Comprobar en los perfiles con `telefono-captura` que no se publicó nada.
6. Podar: `lab.py fixture-podar --app instagram --desde experiments/media-lab/evidence/android/sondas-f2/SONDA-F2-S2-IG/encuesta-colocada.xml --pantalla historia-encuesta-colocada` y el equivalente de Facebook.
7. En `findings.md`, «Sonda S2 de la fase 2 (<fecha>, sin publicar)»: si `input swipe` de 800 ms movió el sticker (si hizo falta más duración, cambiar `stickers.DURACION_ARRASTRE_MS`), si el volcado expone los bounds del sticker, si el arrastre lo escala o gira, cuántos arrastres hicieron falta y los textos reales de «Sondage», «Encuesta», «Terminé» y «Listo».
8. Si el sticker no se movió en ninguna de las dos apps: poner las celdas de `story_poll` (Instagram y Facebook) y de `story_image_music` (Instagram y Facebook) en `"status": "blocked"` con `reason_if_blocked_or_unsupported: "S2: input swipe no mueve el sticker nativo (decisión 2: no se sustituye por texto impreso)"`, anotarlo en `progress.md` y saltar a la tarea 16e solo para `threads/feed_poll`.

- [ ] **Step 2: Prueba con los volcados reales de S2**

Añadir al final de `seccion_encuestas`:

```python
    for app in ("instagram", "facebook"):
        colocada = fixture(app, "historia-encuesta-colocada")
        lienzo = ST.lienzo(colocada, TX.PAQUETES[app])
        pequenos = [n for n in T.nodos(colocada) if n["package"] == TX.PAQUETES[app] and P.dentro(n["bounds"], lienzo)
                    and P.area(n) * 2 < (lienzo[2] - lienzo[0]) * (lienzo[3] - lienzo[1])]
        check(bool(pequenos), f"S2 {app}: el volcado real expone el lienzo 9:16 y nodos del sticker dentro")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add tests/fixtures/telefono/instagram/historia-encuesta-colocada.xml tests/fixtures/telefono/facebook/historia-encuesta-colocada.xml experiments/media-lab/findings.md experiments/media-lab/labkit/stickers.py experiments/media-lab/labkit/textos.py tests/test_media_lab.py
git commit -m "media lab claude: sonda S2 del arrastre de stickers y volcados reales de la encuesta colocada

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16d: E. Encuestas — recetas en borrador y prompt

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Recetas de encuesta**

Añadir al final de `seccion_encuestas`:

```python
    from labkit import recetas as RC
    for par, sub in ((("instagram", "story_poll"), "ig-historia"), (("facebook", "story_poll"), "fb-historia"), (("threads", "feed_poll"), "th")):
        receta = RC.TODAS.get(par)
        check(receta is not None and any(c["args"][:2] == [sub, "encuesta"] for c in receta["preparar"]),
              f"E: receta de {par} con el paso de encuesta")
    for par in (("instagram", "story_poll"), ("facebook", "story_poll")):
        check(RC.TODAS[par]["formato_encargo"].get("zona_reservada") == [140, 760, 940, 1360], f"E: {par} pide zona reservada")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «E: receta de …».

En `recetas.py`, antes de `TODAS`:

```python
_ZONA_POR_DEFECTO = [140, 760, 940, 1360]

ENCUESTA_HISTORIA_INSTAGRAM = {
    **HISTORIA_INSTAGRAM,
    "formato_encargo": {"ancho": 1080, "alto": 1920, "zona_reservada": _ZONA_POR_DEFECTO},
    "preparar": HISTORIA_INSTAGRAM["preparar"][:4] + [
        _cmd("ig-historia", "encuesta", "--run", "<run>", "--encuesta", "<encuesta>", "--zona", "<zona_reservada>",
             ver="igh-03c-encuesta.png: encuesta de 2 opciones con pregunta y opciones exactas dentro de la zona, sin tapar texto"),
    ] + HISTORIA_INSTAGRAM["preparar"][4:],
    "nota": ("story_poll: encuesta clásica de 2 opciones; el máster no lleva las opciones impresas. Si el sticker no "
             "queda dentro tras 2 arrastres, la celda pasa a blocked (decisión 2). La QA recibe también la zona."),
}

ENCUESTA_HISTORIA_FACEBOOK = {
    **HISTORIA_FACEBOOK,
    "formato_encargo": {"ancho": 1080, "alto": 1920, "zona_reservada": _ZONA_POR_DEFECTO},
    "preparar": HISTORIA_FACEBOOK["preparar"] + [
        _cmd("fb-historia", "encuesta", "--run", "<run>", "--encuesta", "<encuesta>", "--zona", "<zona_reservada>",
             ver="fbh-03c-encuesta.png: encuesta de 2 opciones con pregunta y opciones exactas dentro de la zona, sin tapar texto"),
    ],
    "nota": ENCUESTA_HISTORIA_INSTAGRAM["nota"],
}

ENCUESTA_THREADS = {
    **FEED_THREADS_TEXTO,
    "preparar": FEED_THREADS_TEXTO["preparar"] + [
        _cmd("th", "encuesta", "--run", "<run>", "--encuesta", "<encuesta>",
             ver="th-05b-encuesta.png: opciones exactas bajo el texto del thread (captura de la QA)"),
    ],
    "publicar": [
        _cmd("th", "compartir", "--run", "<run>", "--pie", "<pie>", "--encuesta", "<encuesta>", "[--produccion-cercana]",
             ver="th-07-perfil.png: el thread con el texto exacto, la encuesta visible y edad ≤ 3 min"),
    ],
    "nota": "feed_poll: el texto del thread es la pregunta; la duración se deja por defecto.",
}
```

y a `TODAS`:

```python
    ("instagram", "story_poll"): ENCUESTA_HISTORIA_INSTAGRAM,
    ("facebook", "story_poll"): ENCUESTA_HISTORIA_FACEBOOK,
    ("threads", "feed_poll"): ENCUESTA_THREADS,
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py tests/test_media_lab.py
git commit -m "media lab claude: recetas de encuesta en Stories y Threads en borrador

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 2: Prompt de la ventana**

Añadir al final de `seccion_prompt_ventana`:

```python
    for fragmento in ("zona_reservada", "<encuesta>"):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «el prompt de la ventana menciona …» para esos fragmentos.

En `experiments/media-lab/claude-ventana-prompt.md`:

Tras la frase «En `--formato` usa el `formato_encargo` de la receta.» del paso 5, añadir:

```markdown
 En celdas de encuesta o de sticker de música en Story, la receta ya pide `"zona_reservada": [x1, y1, x2, y2]` en píxeles del máster de 1080×1920, libre del panel de texto y de la firma (por defecto `[140, 760, 940, 1360]`).
```

Tras la frase «y el run JSON copiando experiments/media-lab/run-template.json.» del paso 7a, añadir:

```markdown
 En Stories con sticker, añade a `lab.py render … --formato story` la opción `--zona x1,y1,x2,y2` con la `zona_reservada` del encargo.
```

En el paso 7b, sustituir «`<pie>` por el archivo del pie» por «`<pie>` por el archivo del pie, `<zona_reservada>` por la del encargo escrita `x1,y1,x2,y2`, `<encuesta>` por el JSON `{"pregunta": …, "opciones": […]}` que sale de `trivia` del run».

Tras la frase «el revisor solo comprueba que no haya texto ni imagen cortados o tapados.» del paso 7c, añadir:

```markdown
 En Stories con sticker pásale también la `zona_reservada`: el sticker debe quedar dentro y no tapar texto.
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana pide zona reservada y encuestas nativas en Stories

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 3: Actualizar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno» y «zona_reservada».

---

### Task 16e: E. Encuestas — ventanas manuales y promoción

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/findings.md`, `experiments/media-lab/coverage.json`, `experiments/media-lab/runs/`, `experiments/media-lab/progress.md`, `tests/test_media_lab.py`

- [ ] **Step 1: Primeras publicaciones en ventanas manuales**

Una ventana manual por par, en ventanas distintas (una celda de teléfono por ventana), igual que el Step 1 de la tarea 11d y con `--borrador` en `encargo-nuevo` y `receta`: `instagram/story_image_music`, `facebook/story_image_music`, `instagram/story_poll`, `facebook/story_poll` y `threads/feed_poll`. En las de Story el encargo lleva `"zona_reservada": [140, 760, 940, 1360]`, el máster se hace con `lab.py render … --formato story --zona 140,760,940,1360` y el revisor de QA recibe la zona. Si en una ventana el sticker no entra tras 2 arrastres, la celda pasa a `blocked` (decisión 2) y ese par no se promueve.

- [ ] **Step 2: `findings.md`, promoción y ajuste de las comprobaciones de espera**

En `findings.md`, una línea por ventana (run, estado, arrastres usados, veredicto de QA). En `recetas.py`, añadir a `PROMOVIDAS` cada par confirmado con su run, p. ej. `("instagram", "story_poll"): "<run>: primera encuesta en Story de Instagram confirmada (<fecha>)"`. En `seccion_instagram_historia`, sustituir

```python
    check(("instagram", "story_image_music") in RC.BORRADORES, "A: story_image_music espera a la sonda S2")
```

por

```python
    check(("instagram", "story_image_music") in RC.RECETAS, "A: story_image_music promovida tras S2 y su ventana manual")
```

y en `seccion_facebook_historia` sustituir

```python
    check(("facebook", "story_image") in RC.TODAS and ("facebook", "story_image_music") in RC.BORRADORES,
          "D: recetas de Story de la Página; la de música espera a S2")
```

por

```python
    check(("facebook", "story_image") in RC.TODAS and ("facebook", "story_image_music") in RC.RECETAS,
          "D: story_image_music de la Página promovida tras S2 y su ventana manual")
```

(si alguno de los dos quedó `blocked`, su comprobación pasa a `in RC.BORRADORES` con la etiqueta «bloqueado tras S2»). Añadir al final de `seccion_encuestas` una comprobación `in RC.RECETAS` por cada par promovido.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/findings.md experiments/media-lab/coverage.json experiments/media-lab/runs experiments/media-lab/progress.md tests/test_media_lab.py
git commit -m "media lab claude: encuestas y sticker de música promovidos tras sus ventanas manuales

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

Con el push hecho, `lab.py lock-soltar --dueno manual`: la sesión edita, comitea y hace push con el cerrojo tomado.

---

### Task 17a: F. Multiimagen y secuencias — partes puras, encargos y codex (spec, fila 11)

Depende de las tareas 11, 12, 14 y 15 y de 16a y 16b (usa `zona_reservada`, `_encuesta` y la firma de `threads_feed.compartir` con `opciones`, que 17c reescribe con fotogramas). Cambia encargos y el prompt de Codex, que el usuario vuelve a pegar. Promueve `instagram/feed_carousel`, `instagram/story_sequence`, `facebook/feed_multi_photo`, `facebook/story_sequence` y `threads/feed_carousel`.

**Files:**
- Modify: `experiments/media-lab/labkit/telefono.py`, `experiments/media-lab/labkit/pantalla.py`, `experiments/media-lab/labkit/encargos.py`, `experiments/media-lab/labkit/codex_rescate.py`, `experiments/media-lab/lab.py` (`encargo-nuevo --prompt-fotograma`, `codex-tomar`)
- Test: `tests/test_media_lab.py` (sección 26 y `TelefonoSimulado.recientes_mediastore`)

- [ ] **Step 1: Escribir la prueba de las partes puras**

Añadir antes de `SECCIONES` y registrar `seccion_secuencias,`:

```python
def xml_rejilla(ordinales: list, primera_seleccionada: bool = False, extra: str = "", paquete: str = PAQUETE_IG,
                descripcion: str = "{estado} Miniature de la photo du 16 septembre 2026 10:39") -> str:
    """Selector sintético con miniaturas de las 10:39 del 16-09-2026 (hora de Madrid) del `paquete` dado; un ordinal
    dibuja el número dentro de la miniatura. `descripcion` admite `{estado}` (Sélectionné o Désélectionné)."""
    hijos = []
    for i, ordinal in enumerate(ordinales):
        x = 10 + i * 270
        estado = "Sélectionné" if ordinal or (i == 0 and primera_seleccionada) else "Désélectionné"
        numero = nodo_xml(f"[{x + 200},1490][{x + 250},1540]", texto=str(ordinal), paquete=paquete) if ordinal else ""
        hijos.append(nodo_xml(f"[{x},1479][{x + 265},1744]", desc=descripcion.format(estado=estado),
                              clase="android.view.View", paquete=paquete, hijos=numero))
    return jerarquia(nodo_xml("[158,92][847,249]", texto="Nouvelle publication", paquete=paquete), *hijos, extra)


def seccion_secuencias() -> None:
    print("\n26. Fase 2 (F): multiimagen y secuencias")
    from datetime import datetime, timedelta, timezone
    from labkit import codex_rescate as R, encargos as E, facebook_pantallas as FP, instagram_pantallas as IP
    from labkit import pantalla as P, telefono as T, textos as TX, threads_pantallas as TP

    salida = ("Row: 0 _display_name=f3.png, date_added=1757930400\nRow: 1 _display_name=f1.png, date_added=1757930404\n"
              "Row: 2 _display_name=f2.png, date_added=1757930402\nRow: 3 _display_name=viejo.png, date_added=1757000000\n")
    filas = T.filas_recientes(salida, 3)
    check([f["nombre"] for f in filas] == ["f1.png", "f2.png", "f3.png"], "filas_recientes ordena por date_added descendente")
    check(T.orden_subidas(filas, ["f1.png", "f2.png", "f3.png"]) == [] and T.orden_subidas(filas, ["f3.png", "f2.png", "f1.png"]),
          "orden_subidas: el fotograma 1 es el más reciente")
    check(bool(T.orden_subidas([{"nombre": "a", "date_added": 1}, {"nombre": "b", "date_added": 1}], ["a", "b"])),
          "orden_subidas: dos subidas en el mismo segundo no dan un orden seguro")
    check("date_added DESC" in T.consulta_recientes(3), "consulta_recientes ordena en MediaStore")

    subida = datetime(2026, 9, 16, 8, 39, tzinfo=timezone.utc)
    subidas = [subida] * 3
    orden = P.selecciones_ordenadas(xml_rejilla([1, 2, 3, None]), PAQUETE_IG, subidas, IP.fecha_miniatura)
    check([n["bounds"][0] for n in orden] == [10, 280, 550], "selecciones_ordenadas: tres fotogramas en orden")
    for ordinales, label in (([3, 2, 1, None], "orden invertido"), ([1, 2, None, None], "N−1 seleccionadas"),
                             ([1, 3, 2, None], "ordinales cruzados"), ([1, 1, 2, None], "ordinal repetido")):
        try:
            P.selecciones_ordenadas(xml_rejilla(ordinales), PAQUETE_IG, subidas, IP.fecha_miniatura)
            ok = False
        except P.PantallaInesperada:
            ok = True
        check(ok, f"selecciones_ordenadas rechaza: {label}")
    try:
        P.selecciones_ordenadas(xml_rejilla([1, 2, 3, None]), PAQUETE_IG, [subida + timedelta(hours=2)] * 3, IP.fecha_miniatura)
        ok = False
    except P.PantallaInesperada:
        ok = True
    check(ok, "selecciones_ordenadas rechaza miniaturas de otra hora")
    t = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)

    def encargo(formato, prompts, variantes=1):
        return E.nuevo("ENC-20260916-002", coverage_cell_ids=["C"], family_id="F", brief_path="b", do_not_use=[], formato=formato,
                       prompt="Una secuencia", restricciones=["sin texto"], destino_assets="experiments/media-lab/assets/F",
                       ahora=t, variantes=variantes, prompts_fotogramas=prompts)

    e3 = encargo({"ancho": 1080, "alto": 1350, "fotogramas": 3}, ["uno", "dos", "tres"])
    check(R.rutas_imagen(e3) == [f"experiments/media-lab/assets/F/ENC-20260916-002-f{k}.png" for k in (1, 2, 3)]
          and e3["prompts_fotogramas"] == ["uno", "dos", "tres"], "F: un encargo de 3 fotogramas pide f1..f3")
    prompt = R.prompt_para(e3)
    check("1. uno" in prompt and "3. tres" in prompt and "-f3.png" in prompt, "F: el prompt de codex exec lleva un prompt por fotograma")
    for formato, prompts, variantes, label in (({"ancho": 1080, "alto": 1350, "fotogramas": 1}, ["uno"], 1, "1 fotograma"),
                                               ({"ancho": 1080, "alto": 1350, "fotogramas": 11}, ["x"] * 11, 1, "11 fotogramas"),
                                               ({"ancho": 1080, "alto": 1350, "fotogramas": 3}, ["uno", "dos"], 1, "menos prompts"),
                                               ({"ancho": 1080, "alto": 1350, "fotogramas": 3}, ["a", "b", "c"], 2, "dos variantes"),
                                               ({"ancho": 1080, "alto": 1350}, ["uno", "dos"], 1, "prompts sin fotogramas")):
        try:
            encargo(formato, prompts, variantes)
            ok = False
        except E.EncargoError:
            ok = True
        check(ok, f"F: el encargo rechaza {label}")
    imagen = lambda k: {"ruta": f"experiments/media-lab/assets/F/ENC-20260916-002-f{k}.png", "sha256": "ab",  # noqa: E731
                        "ancho": 1080, "alto": 1350}
    E.tomar(e3, "codex-heartbeat", t)
    try:
        E.marcar_generado(e3, "codex-heartbeat", [imagen(1), imagen(2)], t)
        ok = False
    except E.EncargoError:
        ok = True
    check(ok and e3["estado"] == "generando", "F: generado con fotogramas de menos se rechaza")
    E.marcar_generado(e3, "codex-heartbeat", [imagen(1), imagen(2), imagen(3)], t)
    check(e3["estado"] == "generado", "F: generado con todos los fotogramas")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.telefono' has no attribute 'filas_recientes'` en la sección 26.

- [ ] **Step 3: Implementar las partes puras, los fotogramas en encargos y codex**

En `telefono.py`, en la parte pura tras `fila_mediastore_presente`:

```python
def consulta_recientes(n: int, uri: str = URI_IMAGENES) -> str:
    """Orden de shell que lista las imágenes de MediaStore de más reciente a más antigua."""
    if not 1 <= n <= 20:
        raise TelefonoError(f"número de recientes fuera de rango: {n}")
    return (f"content query --uri {uri} --projection _display_name:date_added --sort "
            + shlex.quote("date_added DESC"))


def filas_recientes(salida: str, n: int) -> list[dict]:
    """Las `n` filas más recientes de `content query` como {"nombre", "date_added"}."""
    filas = []
    for linea in salida.splitlines():
        if not linea.startswith("Row:"):
            continue
        nombre = re.search(r"_display_name=(.*?)(?:, \w+=|$)", linea)
        fecha = re.search(r"date_added=(\d+)", linea)
        if nombre and fecha:
            filas.append({"nombre": nombre.group(1), "date_added": int(fecha.group(1))})
    return sorted(filas, key=lambda f: -f["date_added"])[:n]


def orden_subidas(filas: list[dict], nombres: list[str]) -> list[str]:
    """Problemas si las más recientes no son `nombres` en orden (el fotograma 1, subido el último, primero)
    con fechas distintas."""
    problemas = []
    vistos = [f["nombre"] for f in filas]
    if vistos != nombres:
        problemas.append(f"las más recientes son {vistos}, no {nombres}")
    fechas = [f["date_added"] for f in filas]
    if len(set(fechas)) != len(fechas):
        problemas.append("dos subidas con el mismo date_added: el orden de la rejilla no es seguro")
    return problemas
```

y en la parte de E/S, tras `subir`:

```python
def recientes_mediastore(n: int, uri: str = URI_IMAGENES) -> list[dict]:
    return filas_recientes(shell(consulta_recientes(n, uri)), n)
```

En `pantalla.py`, al final:

```python
def miniaturas(xml: str, paquete: str, lector_fecha) -> list[dict]:
    """Miniaturas de la rejilla (nodos con fecha en la content-desc) en orden de documento."""
    return [n for n in telefono.buscar_todos(xml, paquete=paquete) if n["desc"] and lector_fecha(n["desc"]) is not None]


def ordinal_de(xml: str, n: dict, paquete: str) -> int | None:
    """El número de orden dibujado sobre una miniatura seleccionada: un texto de solo dígitos dentro de
    sus bounds."""  # confirmar contra el fixture de S3
    for m in telefono.buscar_todos(xml, paquete=paquete):
        valor = m["texto"] or m["desc"]
        if m["bounds"] != n["bounds"] and valor.isdigit() and dentro(m["bounds"], n["bounds"]):
            return int(valor)
    return None


def selecciones_ordenadas(xml: str, paquete: str, subidas: list[datetime], lector_fecha,
                          tolerancia_min: int = 3) -> list[dict]:
    """Las N miniaturas seleccionadas en el orden de los fotogramas (generaliza la selección única).

    Exige exactamente N con ordinal, ordinales 1..N, que la de ordinal k sea la k-ésima miniatura de la
    rejilla (las subidas en orden inverso dejan el fotograma 1 el primero) y que su hora esté dentro de la
    tolerancia de subidas[k-1]."""
    todas = miniaturas(xml, paquete, lector_fecha)
    n = len(subidas)
    con_ordinal = [(ordinal_de(xml, m, paquete), m) for m in todas]
    seleccionadas = [(k, m) for k, m in con_ordinal if k is not None]
    if len(seleccionadas) != n:
        raise PantallaInesperada(f"hay {len(seleccionadas)} miniaturas seleccionadas, no {n}")
    ordinales = sorted(k for k, _ in seleccionadas)
    if ordinales != list(range(1, n + 1)):
        raise PantallaInesperada(f"ordinales {ordinales} en lugar de 1..{n}")
    por_ordinal = dict(seleccionadas)
    ordenadas = [por_ordinal[k] for k in range(1, n + 1)]
    if [m["bounds"] for m in ordenadas] != [m["bounds"] for m in todas[:n]]:
        raise PantallaInesperada("el orden de selección no es el de los fotogramas en la rejilla")
    for k, (m, subida) in enumerate(zip(ordenadas, subidas), 1):
        if abs(lector_fecha(m["desc"]) - subida) > timedelta(minutes=tolerancia_min):
            raise PantallaInesperada(f"la miniatura {k} no es la subida a las {subida.isoformat()}")
    return ordenadas
```

En `encargos.py`, añadir a la firma de `nuevo` el parámetro `prompts_fotogramas: list[str] | None = None`, añadir tras la comprobación de `zona_reservada`:

```python
    fotogramas = formato.get("fotogramas")
    if fotogramas is not None or prompts_fotogramas:
        if not (isinstance(fotogramas, int) and not isinstance(fotogramas, bool) and 2 <= fotogramas <= 10):
            raise EncargoError("fotogramas debe ser un entero entre 2 y 10")
        if variantes != 1:
            raise EncargoError("un encargo de fotogramas tiene una sola variante")
        if not (isinstance(prompts_fotogramas, list) and len(prompts_fotogramas) == fotogramas
                and all(isinstance(p, str) and p.strip() for p in prompts_fotogramas)):
            raise EncargoError("prompts_fotogramas debe traer un prompt no vacío por fotograma")
```

cambiar `return {` por `enc = {`, y tras el cierre del dict:

```python
    if fotogramas:
        enc["prompts_fotogramas"] = list(prompts_fotogramas)
    return enc
```

y en `marcar_generado` sustituir las dos líneas `if len(imagenes) > enc["variantes"]:` / `raise EncargoError(...)` por:

```python
    esperadas = (enc.get("formato") or {}).get("fotogramas")
    if esperadas:
        if len(imagenes) != esperadas:
            raise EncargoError(f"{len(imagenes)} imágenes para {esperadas} fotogramas")
    elif len(imagenes) > enc["variantes"]:
        raise EncargoError(f"{len(imagenes)} imágenes para {enc['variantes']} variante(s)")
```

En `codex_rescate.py`, sustituir `rutas_imagen` por:

```python
def rutas_imagen(enc: dict) -> list[str]:
    fotogramas = (enc.get("formato") or {}).get("fotogramas")
    if fotogramas:
        return [f"{enc['destino_assets']}/{enc['encargo_id']}-f{k}.png" for k in range(1, fotogramas + 1)]
    return [f"{enc['destino_assets']}/{enc['encargo_id']}-v{n}.png" for n in range(1, enc["variantes"] + 1)]
```

y en `prompt_para`, tras `restricciones = …`:

```python
    fotogramas = enc.get("prompts_fotogramas") or []
    bloque_fotogramas = ("Fotogramas (una imagen por ruta, en este orden; misma escena, estilo y paleta):\n"
                         + "\n".join(f"{k}. {p}" for k, p in enumerate(fotogramas, 1)) + "\n") if fotogramas else ""
```

cambiando la línea `f"Prompt:\n{enc['prompt']}\n\nRestricciones obligatorias:\n{restricciones}\n"` por `f"Prompt:\n{enc['prompt']}\n\n{bloque_fotogramas}Restricciones obligatorias:\n{restricciones}\n"`.

En `lab.py`:

4. `encargo-nuevo`: añadir `p.add_argument("--prompt-fotograma", action="append", help="archivo con el prompt de cada fotograma, en orden")` y pasar a `encargos.nuevo` `prompts_fotogramas=[Path(r).read_text(encoding="utf-8").strip() for r in a.prompt_fotograma] if a.prompt_fotograma else None`.

5. `cmd_codex_tomar`: añadir `"prompts_fotogramas": enc.get("prompts_fotogramas"),` al dict de cada encargo tomado.

- [ ] **Step 4: Extender el teléfono simulado**

En `TelefonoSimulado.__init__` añadir el parámetro `recientes: list | None = None` y `self.recientes = list(recientes or [])`, y el método:

```python
    def recientes_mediastore(self, n: int, uri: str = "") -> list:
        return self.recientes[:n]
```

y en `con_telefono_simulado` añadir `(telefono, "recientes_mediastore", sim.recientes_mediastore),`.

- [ ] **Step 5: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: la sección 26 en `✓`, la 7 (codex) sin cambios y `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/telefono.py experiments/media-lab/labkit/pantalla.py experiments/media-lab/labkit/encargos.py experiments/media-lab/labkit/codex_rescate.py experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: fotogramas en encargos, recientes de MediaStore y selección múltiple ordenada

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 17b-1: F. Multiimagen y secuencias — selección múltiple en Instagram

**Files:**
- Modify: `experiments/media-lab/labkit/textos.py`, `experiments/media-lab/labkit/pasos.py`, `experiments/media-lab/labkit/instagram_feed.py`, `experiments/media-lab/labkit/instagram_historia.py`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Textos de la selección múltiple (se confirman en la tarea 17e)**

Añadir las dos primeras a `TEXTOS["instagram"]` y la tercera a `TEXTOS["facebook"]`:

```python
        # instagram
        "seleccion_multiple": "Sélectionner plusieurs",  # confirmar contra el fixture de S3
        "publicacion_cuadricula": "Photo de sabiduriabolsillo",  # confirmar contra el fixture de S3 (desc de la cuadrícula del perfil)
        # facebook
        "seleccionar_varios": "Seleccionar varios",  # confirmar contra el fixture de S3
```

- [ ] **Step 2: Escribir la prueba de la selección múltiple en Instagram y del recorrido**

Añadir al final de `seccion_secuencias`:

```python
    print("   · selección múltiple simulada y recorrido")
    import pathlib as _p
    from labkit import instagram_feed as IG, pasos

    evid = _p.Path("evidencia-simulada")
    boton = nodo_xml("[900,1300][1060,1400]", desc=TX.TEXTOS["instagram"]["seleccion_multiple"], clase="android.widget.Button",
                     extra='clickable="true"')
    menu_crear = jerarquia(nodo_xml("[100,1500][980,1650]", texto="Publication"))
    inicial = xml_rejilla([None, None, None, None], primera_seleccionada=True, extra=boton)
    tras_multiple = xml_rejilla([1, None, None, None], extra=boton)
    final = xml_rejilla([1, 2, 3, None], extra=boton)
    sim = TelefonoSimulado([xml_inicio(), xml_perfil(), menu_crear, inicial, tras_multiple, final])
    res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subidas))
    check(err is None and sim.toques[3:] == [(980, 1350), (412, 1611), (682, 1611)] and sim.capturas == ["ig-01-selector.png"],
          f"F ig abrir: selección múltiple y las miniaturas 2 y 3 en orden ({err!r}, {sim.toques})")
    sim = TelefonoSimulado([xml_inicio(), xml_perfil(), menu_crear, inicial, tras_multiple, xml_rejilla([1, 3, 2, None], extra=boton)])
    res, err = con_telefono_simulado(sim, lambda: IG.abrir_nueva_publicacion(evid, subidas))
    check(isinstance(err, P.PantallaInesperada) and "ig-01-selector.png" not in sim.capturas,
          "F ig abrir: con el orden cruzado no se da el selector por bueno")
    sim = TelefonoSimulado([final])
    res, err = con_telefono_simulado(sim, lambda: pasos.recorrer_fotogramas(3, lambda: T.tocar(900, 1000), evid, "prueba"))
    check(err is None and sim.toques == [(900, 1000), (900, 1000)] and sim.capturas == ["prueba-f1.png", "prueba-f2.png", "prueba-f3.png"],
          "recorrer_fotogramas captura cada fotograma avanzando entre capturas")
    from labkit import instagram_historia as IGH
    boton_h = nodo_xml("[900,1300][1060,1400]", desc=TX.TEXTOS["instagram"]["seleccion_multiple"], clase="android.widget.Button",
                       extra='clickable="true"')
    sin_sel = xml_rejilla([None, None, None, None], extra=boton_h)
    final_h = xml_rejilla([1, 2, 3, None], extra=boton_h)
    sim = TelefonoSimulado([xml_inicio(), xml_perfil(), fixture("instagram", "crear-menu"), sin_sel, sin_sel, final_h])
    res, err = con_telefono_simulado(sim, lambda: IGH.abrir(evid, subidas))
    check(err is None and len(sim.toques) == 7 and sim.capturas == ["igh-01-selector.png"] and not toques_sobre_envio(sim, PAQUETE_IG),
          f"F ig-historia abrir: selección múltiple de tres fotogramas en orden sin tocar controles de envío ({err!r}, {sim.toques})")
```

- [ ] **Step 3: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «F ig abrir: selección múltiple…», «F ig abrir: con el orden cruzado…», «recorrer_fotogramas captura cada fotograma…» y «F ig-historia abrir…».

- [ ] **Step 4: Implementar los ayudantes de `pasos.py` y la selección múltiple de Instagram**

En `pasos.py`, al final:

```python
def _ordenadas_o_none(xml: str, paquete: str, subidas: list[datetime], lector_fecha):
    try:
        return tuple(m["bounds"] for m in pantalla.selecciones_ordenadas(xml, paquete, subidas, lector_fecha))
    except PantallaInesperada:
        return None


def seleccionar_en_orden(paquete: str, subidas: list[datetime], lector_fecha, boton_multiple: dict | None = None,
                         xml_boton: str | None = None) -> str:
    """Selección múltiple de los N fotogramas: activa la selección múltiple (si se da el botón), toca en orden
    las miniaturas de la rejilla que aún no tienen ordinal y exige `pantalla.selecciones_ordenadas` con
    volcado estable."""
    exigir_listo()
    if boton_multiple is not None:
        tocar(boton_multiple, xml_boton, paquete)
        reloj.dormir(1)
    xml = volcado_fresco()
    todas = pantalla.miniaturas(xml, paquete, lector_fecha)
    n = len(subidas)
    if len(todas) < n:
        raise PantallaInesperada(f"la rejilla tiene {len(todas)} miniaturas y hacen falta {n}")
    ya = sum(1 for m in todas[:n] if pantalla.ordinal_de(xml, m, paquete) is not None)
    for miniatura in todas[ya:n]:
        tocar(miniatura, xml, paquete)
        reloj.dormir(0.8)
    xml, _ = esperar_estable(lambda x: _ordenadas_o_none(x, paquete, subidas, lector_fecha),
                             descripcion="los fotogramas seleccionados en orden")
    return xml


def recorrer_fotogramas(n: int, avanzar, evidencia: Path, prefijo: str) -> list[str]:
    """Captura `<prefijo>-f1.png` … `-fN.png` llamando a `avanzar()` entre capturas."""
    capturas = [str(telefono.captura(evidencia / f"{prefijo}-f1.png"))]
    for k in range(2, n + 1):
        avanzar()
        reloj.dormir(1.5)
        capturas.append(str(telefono.captura(evidencia / f"{prefijo}-f{k}.png")))
    return capturas


def deslizar_media(xml: str, paquete: str):
    """Deslizar a la izquierda sobre la imagen más grande (carrusel)."""
    imagenes = [m for m in telefono.buscar_todos(xml, paquete=paquete) if m["clase"].endswith("ImageView")]
    if not imagenes:
        raise PantallaInesperada("no hay imagen que deslizar")
    x1, y1, x2, y2 = max(imagenes, key=pantalla.area)["bounds"]
    cy = (y1 + y2) // 2
    return lambda: telefono.arrastrar(x2 - 60, cy, x1 + 60, cy, telefono.DURACION_MINIMA_ARRASTRE_MS)


def tocar_derecha(xml: str):
    """Tocar el borde derecho a media altura (avanzar en el visor de una Story)."""
    ancho = max((n["bounds"][2] for n in telefono.nodos(xml) if n["profundidad"] == 0), default=1080)
    alto = pantalla.alto_volcado(xml)
    return lambda: telefono.tocar(round(ancho * 0.9), round(alto * 0.5))
```

En `instagram_feed.py`, cambiar `from labkit import pasos, reloj, telefono` por `from labkit import pantalla, pasos, reloj, telefono, textos`, cambiar la firma de `abrir_nueva_publicacion` a `(evidencia: Path, subido_en: datetime | str | list) -> dict`, quitar sus dos primeras líneas (`if isinstance(subido_en, str): …`) y sustituir su tramo final desde `xml = _esperar(texto="Nouvelle publication")` por:

```python
    xml = _esperar(texto="Nouvelle publication")
    subidas = [datetime.fromisoformat(s) if isinstance(s, str) else s
               for s in (subido_en if isinstance(subido_en, list) else [subido_en])]
    if len(subidas) > 1:
        boton = pantalla.nodo(xml, PAQUETE, texto=textos.TEXTOS["instagram"]["seleccion_multiple"])
        pasos.seleccionar_en_orden(PAQUETE, subidas, fecha_miniatura, boton, xml)
    else:
        sel = seleccion_unica(xml)
        if sel is None:
            raise PantallaInesperada("no hay exactamente una miniatura seleccionada")
        if not miniatura_coincide(sel["desc"], subidas[0]):
            raise PantallaInesperada(f"la miniatura seleccionada no es la subida a las {subidas[0].isoformat()}: {sel['desc']}")
    return {"captura": str(telefono.captura(evidencia / "ig-01-selector.png")),
            "publicaciones_antes": publicaciones_antes}
```

(añadiendo `fecha_miniatura` a la importación explícita de `instagram_pantallas`). Cambiar `anadir_audio_sugerido(evidencia: Path)` por `anadir_audio_sugerido(evidencia: Path, opcional: bool = False)` y su línea `xml = _esperar(empieza="Audio suggéré.")` por:

```python
    try:
        xml = _esperar(empieza="Audio suggéré.")
    except PantallaInesperada:
        if not opcional:
            raise
        return {"tema": None, "motivo": "music_unavailable_in_native_composer",
                "captura": str(telefono.captura(evidencia / "ig-03-audio.png"))}
```

Añadir a `compartir` el parámetro final `fotogramas: int = 1` y, en `despues`, justo antes de `return estado`:

```python
        if fotogramas > 1 and estado in ("confirmado", "confirmado_sin_conteo"):
            try:
                xml = pasos.volcado_fresco()
                primera = telefono.buscar_todos(xml, empieza=textos.TEXTOS["instagram"]["publicacion_cuadricula"], paquete=PAQUETE)
                if not primera:
                    raise PantallaInesperada("no aparece la publicación nueva en la cuadrícula")
                pasos.tocar(primera[0], xml, PAQUETE)
                xml, _ = pasos.esperar_estable(lambda x: telefono.buscar(x, contiene=f"1/{fotogramas}", paquete=PAQUETE) is not None,
                                               descripcion=f"la publicación con el indicador 1/{fotogramas}")  # confirmar contra el fixture de S3
                resultado["fotogramas"] = pasos.recorrer_fotogramas(fotogramas, pasos.deslizar_media(xml, PAQUETE), evidencia, "ig-06-carrusel")
            except (PantallaInesperada, telefono.TelefonoError) as e:
                avisos.append(f"no se recorrió el carrusel publicado: {e}")
```

En `instagram_historia.py`, añadir `fecha_miniatura` a la importación de `instagram_pantallas` y sustituir en `abrir` la línea `_, bounds = pasos.esperar_estable(...)` y el `return` por:

```python
    subidas = subido_en if isinstance(subido_en, list) else [subido_en]
    if len(subidas) > 1:
        xml = pasos.volcado_fresco()
        boton = pantalla.nodo(xml, PAQUETE, texto=T["seleccion_multiple"])
        pasos.seleccionar_en_orden(PAQUETE, subidas, fecha_miniatura, boton, xml)
        return {"miniaturas": len(subidas), "captura": str(telefono.captura(evidencia / "igh-01-selector.png"))}
    _, bounds = pasos.esperar_estable(lambda x: _bounds_miniatura(x, subidas[0]), descripcion="la miniatura de la subida")
    return {"miniatura": list(bounds), "captura": str(telefono.captura(evidencia / "igh-01-selector.png"))}
```

en `elegir`, tras `pasos.exigir_listo()`:

```python
    if isinstance(subido_en, list) and len(subido_en) > 1:
        xml = pasos.volcado_fresco()
        pasos.tocar(pantalla.nodo(xml, PAQUETE, texto=T["siguiente"]), xml, PAQUETE)
        pasos.esperar_que(editor_historia_listo, "el editor de la secuencia", app="instagram")
        return {"captura": str(telefono.captura(evidencia / "igh-02-editor.png"))}
```

en `audio`, sustituir la firma, `pasos.exigir_listo()` y la espera del chip por:

```python
def audio(evidencia: Path, opcional: bool = False) -> dict:
    """Chip «Audio suggéré»: se añade si no venía añadido y se anota el tema. Con `opcional` (varias imágenes),
    si no hay chip devuelve tema None y music_unavailable_in_native_composer."""
    pasos.exigir_listo()
    try:
        xml = pasos.esperar_que(lambda x: chip_audio_historia(x) is not None, "el chip «Audio suggéré»", app="instagram")
    except PantallaInesperada:
        if not opcional:
            raise
        return {"tema": None, "motivo": "music_unavailable_in_native_composer",
                "captura": str(telefono.captura(evidencia / "igh-03-audio.png"))}
```

y en `compartir` cambiar la firma a `def compartir(evidencia: Path, produccion_cercana: bool = False, fotogramas: int = 1) -> dict:` y, en `despues`, tras `resultado["visor"] = lectura`:

```python
                if fotogramas > 1 and lectura["ok"]:
                    resultado["fotogramas"] = pasos.recorrer_fotogramas(fotogramas, pasos.tocar_derecha(pasos.volcado_fresco()),
                                                                        evidencia, "igh-06-secuencia")
```

- [ ] **Step 5: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/textos.py experiments/media-lab/labkit/pasos.py experiments/media-lab/labkit/instagram_feed.py experiments/media-lab/labkit/instagram_historia.py tests/test_media_lab.py
git commit -m "media lab claude: selección múltiple verificada y capturas por fotograma en Instagram

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 17b-2: F. Multiimagen y secuencias — selección múltiple en Facebook y Threads

**Files:**
- Modify: `experiments/media-lab/labkit/facebook_feed.py`, `experiments/media-lab/labkit/facebook_historia.py`, `experiments/media-lab/labkit/threads_feed.py`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de la selección múltiple en Facebook y Threads**

Añadir al final de `seccion_secuencias`:

```python
    print("   · selección múltiple simulada en Facebook y Threads")
    from labkit import facebook_feed as FB, facebook_historia as FH, threads_feed as TH
    desc_fb = "Foto del 16 de septiembre de 2026, 10:39"
    boton_fb = nodo_xml("[700,300][1060,400]", texto=TX.TEXTOS["facebook"]["seleccionar_varios"], clase="android.widget.Button",
                        paquete=FP.PAQUETE, extra='clickable="true"')
    rejilla_fb = xml_rejilla([None, None, None, None], extra=boton_fb, paquete=FP.PAQUETE, descripcion=desc_fb)
    final_fb = xml_rejilla([1, 2, 3, None], paquete=FP.PAQUETE, descripcion=desc_fb)
    comp_th = fixture("threads", "compositor-vacio")
    campo_th = TP.por_id(comp_th, TP.ID_COMPOSITOR)[0]["bounds"]
    con_imagen_th = con_nodo(comp_th, nodo_xml(f"[40,{campo_th[1] + 50}][440,{campo_th[1] + 450}]", clase="android.widget.ImageView",
                                               paquete=TP.PAQUETE))
    rejilla_th = xml_rejilla([None, None, None, None], paquete=TP.PAQUETE)
    final_th = xml_rejilla([1, 2, 3, None], paquete=TP.PAQUETE)
    for nombre_flujo, paquete, guion_f, accion, capturas in (
            ("fb galeria", FP.PAQUETE, [fixture("facebook", "compositor-pagina"), rejilla_fb, rejilla_fb, final_fb, final_fb, final_fb,
                                        final_fb, fixture("facebook", "compositor-con-imagen")],
             lambda: FB.galeria(evid, subidas), ["fb-03-imagen.png"]),
            ("fb-historia elegir", FP.PAQUETE, [rejilla_fb, rejilla_fb, final_fb, final_fb, final_fb, final_fb, fixture("facebook", "historia-editor")],
             lambda: FH.elegir(evid, subidas), ["fbh-02-editor.png"]),
            ("th galeria", TP.PAQUETE, [comp_th, rejilla_th, final_th, final_th, final_th, final_th, con_imagen_th],
             lambda: TH.galeria(evid, subidas), ["th-04-imagen.png"])):
        sim = TelefonoSimulado(guion_f)
        res, err = con_telefono_simulado(sim, accion)
        check(err is None and sim.capturas == capturas and not toques_sobre_envio(sim, paquete),
              f"F {nombre_flujo}: tres fotogramas seleccionados en orden sin tocar controles de envío ({err!r}, {sim.toques})")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «F fb galeria…», «F fb-historia elegir…» y «F th galeria…».

- [ ] **Step 3: Implementar la selección múltiple de Facebook y Threads**

En `facebook_feed.py`, en `galeria` sustituir desde `xml = pasos.esperar_que(lambda x: _hay_miniatura(x, subido_en)…` hasta `_tocar_si_hay(T["listo"])` por:

```python
    subidas = subido_en if isinstance(subido_en, list) else [subido_en]
    if len(subidas) > 1:
        xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["seleccionar_varios"], paquete=fp.PAQUETE) is not None,
                                f"«{T['seleccionar_varios']}»", app="facebook")
        pasos.seleccionar_en_orden(fp.PAQUETE, subidas, fp.fecha_miniatura_es, pantalla.nodo(xml, fp.PAQUETE, texto=T["seleccionar_varios"]), xml)
    else:
        xml = pasos.esperar_que(lambda x: _hay_miniatura(x, subidas[0]), "la miniatura de la subida", app="facebook")
        pasos.tocar(fp.miniatura_galeria(xml, subidas[0]), xml, fp.PAQUETE)
        reloj.dormir(1)
    _tocar_si_hay(T["listo"])
```

y en `musica`, sustituir la firma, `pasos.exigir_listo()` y la espera de «Música» por:

```python
def musica(evidencia: Path, opcional: bool = False) -> dict:
    pasos.exigir_listo()
    try:
        xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["musica"], paquete=fp.PAQUETE) is not None,
                                f"«{T['musica']}»", app="facebook")
    except PantallaInesperada:
        if not opcional:
            raise
        return {"tema": None, "motivo": "music_unavailable_in_native_composer",
                "captura": str(telefono.captura(evidencia / "fb-04-musica.png"))}
```
 El multifoto de la Página se confirma igual que la foto única: la QA recibe `fb-08-perfil.png` y el run anota el tratamiento real (rejilla).

En `facebook_historia.py`, en `elegir`, tras `pasos.exigir_listo()`:

```python
    if isinstance(subido_en, list) and len(subido_en) > 1:
        xml = pasos.esperar_que(lambda x: telefono.buscar(x, texto=T["seleccionar_varios"], paquete=fp.PAQUETE) is not None,
                                f"«{T['seleccionar_varios']}»", app="facebook")
        pasos.seleccionar_en_orden(fp.PAQUETE, subido_en, fp.fecha_miniatura_es, pantalla.nodo(xml, fp.PAQUETE, texto=T["seleccionar_varios"]), xml)
        facebook_feed._tocar_si_hay(T["siguiente"])
        pasos.esperar_que(fp.editor_historia_fb_listo, "el editor de la secuencia", app="facebook")
        return {"captura": str(telefono.captura(evidencia / "fbh-02-editor.png"))}
```

en `audio`, sustituir la firma, `pasos.exigir_listo()` y la espera del editor por:

```python
def audio(evidencia: Path, opcional: bool = False) -> dict:
    pasos.exigir_listo()
    xml = pasos.esperar_que(fp.editor_historia_fb_listo, "el editor de la historia", app="facebook")
    if opcional and telefono.buscar(xml, texto=T["musica"], paquete=fp.PAQUETE) is None:
        return {"tema": None, "motivo": "music_unavailable_in_native_composer",
                "captura": str(telefono.captura(evidencia / "fbh-03-audio.png"))}
```

y en `compartir` cambiar la firma a `def compartir(evidencia: Path, produccion_cercana: bool = False, fotogramas: int = 1) -> dict:` con, tras `resultado["visor"] = lectura`:

```python
                if fotogramas > 1 and lectura["ok"]:
                    resultado["fotogramas"] = pasos.recorrer_fotogramas(fotogramas, pasos.tocar_derecha(pasos.volcado_fresco()),
                                                                        evidencia, "fbh-06-secuencia")
```

En `threads_feed.py`, en `galeria` sustituir desde `xml = pasos.esperar_que(lambda x: _hay_miniatura(x, subido_en)…` hasta `reloj.dormir(1)` por:

```python
    subidas = subido_en if isinstance(subido_en, list) else [subido_en]
    if len(subidas) > 1:
        pasos.seleccionar_en_orden(tp.PAQUETE, subidas, tp.lector_fecha)  # confirmar contra el fixture de S3 (sin conmutador)
    else:
        xml = pasos.esperar_que(lambda x: _hay_miniatura(x, subidas[0]), "la miniatura de la subida", app="threads")
        pasos.tocar(tp.miniatura_galeria(xml, subidas[0]), xml, tp.PAQUETE)
        reloj.dormir(1)
```

en `musica`, sustituir la firma, `pasos.exigir_listo()` y la espera del botón por:

```python
def musica(evidencia: Path, opcional: bool = False) -> dict:
    pasos.exigir_listo()
    try:
        xml = pasos.esperar_que(lambda x: bool(tp.por_id(x, tp.ID_MUSICA)), "el botón de música", app="threads")
    except PantallaInesperada:
        if not opcional:
            raise
        return {"tema": None, "motivo": "music_unavailable_in_native_composer",
                "captura": str(telefono.captura(evidencia / "th-05-musica.png"))}
```

y en `compartir` cambiar la firma a `def compartir(texto_: str, tema: str | None, con_imagen: bool, evidencia: Path, produccion_cercana: bool = False, opciones: list[str] | None = None, fotogramas: int = 1) -> dict:` con, tras `lectura = tp.thread_reciente(xml, texto_)`:

```python
                if fotogramas > 1 and lectura["ok"]:
                    resultado["fotogramas"] = pasos.recorrer_fotogramas(fotogramas, pasos.deslizar_media(xml, tp.PAQUETE),
                                                                        evidencia, "th-07-carrusel")
```

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/facebook_feed.py experiments/media-lab/labkit/facebook_historia.py experiments/media-lab/labkit/threads_feed.py tests/test_media_lab.py
git commit -m "media lab claude: selección múltiple verificada y capturas por fotograma en Facebook y Threads

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 17c: F. Multiimagen y secuencias — `telefono-subir` y subcomandos con fotogramas

**Files:**
- Modify: `experiments/media-lab/lab.py` (`telefono-subir` repetible, `ig`, `cmd_ig_historia`, `cmd_fb_historia`, `cmd_th`, `cmd_fb`)
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba de `telefono-subir` con fotogramas y de `--fotogramas`**

Añadir al final de `seccion_secuencias`:

```python
    print("   · telefono-subir con fotogramas y rechazos de --fotogramas")
    from PIL import Image
    from labkit import reloj

    with entorno_lab_fase2() as (lab, raiz):
        rels = []
        for k in (1, 2, 3):
            rel = f"experiments/media-lab/assets/F/m-f{k}.png"
            (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (1080, 1350), (10 * k, 20, 30)).save(raiz / rel)
            rels.append(rel)
        subidos: list[str] = []
        viejos = (T.subir, T.recientes_mediastore, T.captura, reloj.dormir)
        try:
            T.subir = lambda local, remoto: subidos.append(local.name) or {"sha256": "ab", "subido_en": f"2026-09-16T08:39:0{len(subidos)}+00:00"}
            T.captura = lambda destino, timeout=60: destino
            reloj.dormir = lambda segundos: None
            T.recientes_mediastore = lambda n, uri="": [{"nombre": f"m-f{k}.png", "date_added": 100 - k} for k in (1, 2, 3)][:n]
            args = ["telefono-subir"] + [x for rel in rels for x in ("--local", rel)]
            codigo, datos, _ = lab(*args)
            check(codigo == 0 and subidos == ["m-f3.png", "m-f2.png", "m-f1.png"] and len(campo(datos, "subido_en") or []) == 3
                  and str((campo(datos, "subidas") or [{}])[0].get("local", "")).endswith("m-f1.png"),
                  f"telefono-subir sube en orden inverso y devuelve subido_en en el orden de los fotogramas ({codigo}, {subidos})")
            T.recientes_mediastore = lambda n, uri="": [{"nombre": f"m-f{k}.png", "date_added": 100 + k} for k in (3, 2, 1)][:n]
            subidos.clear()
            codigo, datos, _ = lab(*args)
            check(codigo == 4 and campo(datos, "tipo") == "TelefonoError", "telefono-subir falla si las más recientes no están en orden")
        finally:
            T.subir, T.recientes_mediastore, T.captura, reloj.dormir = viejos
        for args, fragmento, label in ((("ig", "abrir", "--run", "R", "--subido-en", "2026-09-16T08:39:00+00:00", "--subido-en", "2026-09-16T08:39:02+00:00"),
                             "--fotogramas debe coincidir", "dos --subido-en con --fotogramas 1"),
                            (("ig-historia", "abrir", "--run", "R", "--fotogramas", "3", "--subido-en", "2026-09-16T08:39:00+00:00"),
                             "exige 3", "--fotogramas 3 con un solo --subido-en"),
                            (("th", "galeria", "--run", "R", "--fotogramas", "11", "--subido-en", "2026-09-16T08:39:00+00:00"), "--fotogramas va de 1 a 10", "11 fotogramas")):
            sim = TelefonoSimulado([xml_perfil()])
            res, err = con_telefono_simulado(sim, lambda: lab(*args))
            check(rechazo(res, fragmento) and sim.volcados_leidos == 0, f"lab.py rechaza {label} sin tocar el teléfono")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «telefono-subir sube en orden inverso…», «telefono-subir falla si las más recientes no están en orden» y los tres rechazos de `--fotogramas`.

- [ ] **Step 3: Implementar `telefono-subir` repetible y los `cmd_*` con fotogramas**

En `lab.py`:

1. `telefono-subir`: cambiar el argumento a `p.add_argument("--local", action="append", required=True, help="imagen bajo experiments/media-lab/ (.png, .jpg o .jpeg); repetible, un fotograma por vez y en orden")` y sustituir `cmd_telefono_subir` por:

```python
def _local_subida(rel: str) -> Path:
    local = _relativa_sin_salidas(rel, "experiments/media-lab/", "--local")
    _exigir(local.suffix.lower() in EXTENSIONES_SUBIDA, f"--local debe ser {', '.join(EXTENSIONES_SUBIDA)}: {rel}")
    _exigir(bool(_NOMBRE.fullmatch(local.name)), f"nombre de archivo no apto para MediaStore: {local.name}")
    return local


def cmd_telefono_subir(a) -> int:
    from labkit import reloj, telefono
    locales = [_local_subida(rel) for rel in a.local]
    _exigir(len({p.name for p in locales}) == len(locales), "--local repetido")
    _exigir(len(locales) <= 10, "como mucho 10 fotogramas")

    def subir() -> dict:
        subidas: dict[str, dict] = {}
        for local in reversed(locales):  # la rejilla muestra lo más reciente primero: el fotograma 1 se sube el último
            remoto = f"/sdcard/Pictures/SabiduriaLab/{local.name}"
            subidas[local.name] = {"local": local.relative_to(ROOT).as_posix(), "remoto": remoto, **telefono.subir(local, remoto)}
            if len(locales) > 1:
                reloj.dormir(2)  # date_added distinto y orden seguro en la rejilla
        ordenadas = [subidas[p.name] for p in locales]
        if len(locales) == 1:
            return ordenadas[0]
        problemas = telefono.orden_subidas(telefono.recientes_mediastore(len(locales)), [p.name for p in locales])
        if problemas:
            raise telefono.TelefonoError(f"las subidas no son las más recientes en orden: {problemas}")
        return {"subidas": ordenadas, "subido_en": [s["subido_en"] for s in ordenadas]}

    return _paso_telefono(_evidencia("subidas"), f"subir-inesperada-{locales[0].stem}", subir)
```

2. `ig`: cambiar `--subido-en` a `action="append"` y añadir `p.add_argument("--fotogramas", type=int, default=1)`. En `cmd_ig`, sustituir el bloque de `abrir` y el de `compartir` por:

```python
    _exigir(1 <= a.fotogramas <= 10, "--fotogramas va de 1 a 10")
    if a.paso == "abrir":
        subidas = _subidas(a.subido_en)
        _exigir(bool(subidas), "--subido-en es obligatorio en abrir (lo devuelve telefono-subir)")
        _exigir(len(subidas) == a.fotogramas, "--fotogramas debe coincidir con el número de --subido-en")
        subido = subidas if len(subidas) > 1 else subidas[0]
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    if a.paso == "compartir":
        _exigir((bool(a.tema) or a.fotogramas > 1) and a.publicaciones_antes is not None,
                "compartir exige --tema y --publicaciones-antes")
    extra = {"fotogramas": a.fotogramas} if a.fotogramas > 1 else {}
```

y en el dict de pasos `"audio": (lambda: ig.anadir_audio_sugerido(ev, opcional=True)) if a.fotogramas > 1 else (lambda: ig.anadir_audio_sugerido(ev)),` y `"compartir": lambda: ig.compartir(pie, a.tema, ev, a.publicaciones_antes, produccion_cercana=a.produccion_cercana, **extra),`. (Con `--fotogramas 1`, las llamadas son las de siempre: las pruebas de la fase 1 que sustituyen `compartir` no reciben argumentos nuevos.)

3. Añadir tras `_codigo_compartir`:

```python
def _subidas_de_flujo(a, obligatorio: bool) -> list[datetime] | datetime | None:
    """--subido-en de un paso de galería o selector: tantos como --fotogramas; una fecha si es uno, la lista si son varios."""
    _exigir(1 <= a.fotogramas <= 10, "--fotogramas va de 1 a 10")
    subidas = _subidas(a.subido_en)
    if not obligatorio:
        return None
    _exigir(len(subidas) == a.fotogramas, f"{a.paso} exige {a.fotogramas} --subido-en (los devuelve telefono-subir)")
    return subidas if len(subidas) > 1 else subidas[0]
```

y sustituir `cmd_ig_historia`, `cmd_fb_historia`, `cmd_th` y `cmd_fb` completas por su versión con fotogramas (incluye lo de la tarea 16):

```python
def cmd_ig_historia(a) -> int:
    from labkit import instagram_historia as igh
    ev = _evidencia(a.run)
    sel = _subidas_de_flujo(a, a.paso in ("abrir", "elegir"))
    zona = _zona(a.zona)
    encuesta = _encuesta(a.encuesta, con_pregunta=True, max_opciones=2)
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    if a.paso == "sticker-musica":
        _exigir(zona is not None and bool(a.tema), "sticker-musica exige --zona y --tema")
    if a.paso == "encuesta":
        _exigir(encuesta is not None and zona is not None, "encuesta exige --encuesta y --zona")
    varios = {"fotogramas": a.fotogramas} if a.fotogramas > 1 else {}
    opcional = {"opcional": True} if a.fotogramas > 1 else {}
    pasos_ = {
        "abrir": lambda: igh.abrir(ev, sel),
        "elegir": lambda: igh.elegir(ev, sel),
        "audio": lambda: igh.audio(ev, **opcional),
        "sticker-musica": lambda: igh.sticker_musica(ev, zona, a.tema),
        "encuesta": lambda: igh.encuesta(ev, encuesta, zona),
        "destino": lambda: igh.destino(ev),
        "compartir": lambda: igh.compartir(ev, produccion_cercana=a.produccion_cercana, **varios),
        "actividad": lambda: igh.actividad(ev),
    }
    return _paso_telefono(ev, f"igh-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))


def cmd_fb_historia(a) -> int:
    from labkit import facebook_historia as fbh
    ev = _evidencia(a.run)
    sel = _subidas_de_flujo(a, a.paso == "elegir")
    zona = _zona(a.zona)
    encuesta = _encuesta(a.encuesta, con_pregunta=True, max_opciones=2)
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    if a.paso == "sticker-musica":
        _exigir(zona is not None and bool(a.tema), "sticker-musica exige --zona y --tema")
    if a.paso == "encuesta":
        _exigir(encuesta is not None and zona is not None, "encuesta exige --encuesta y --zona")
    varios = {"fotogramas": a.fotogramas} if a.fotogramas > 1 else {}
    opcional = {"opcional": True} if a.fotogramas > 1 else {}
    pasos_ = {
        "abrir": lambda: fbh.abrir(ev),
        "elegir": lambda: fbh.elegir(ev, sel),
        "audio": lambda: fbh.audio(ev, **opcional),
        "opciones": lambda: fbh.opciones(ev),
        "sticker-musica": lambda: fbh.sticker_musica(ev, zona, a.tema),
        "encuesta": lambda: fbh.encuesta(ev, encuesta, zona),
        "compartir": lambda: fbh.compartir(ev, produccion_cercana=a.produccion_cercana, **varios),
        "actividad": lambda: fbh.actividad(ev),
    }
    return _paso_telefono(ev, f"fbh-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))


def cmd_th(a) -> int:
    from labkit import threads_feed as th
    ev = _evidencia(a.run)
    sel = _subidas_de_flujo(a, a.paso == "galeria")
    texto = _leer_texto(a.pie, "el texto del thread", LIMITE_THREADS) if a.paso in ("texto", "compartir") else None
    encuesta = _encuesta(a.encuesta, con_pregunta=False, max_opciones=4)
    if a.paso == "encuesta":
        _exigir(encuesta is not None, "encuesta exige --encuesta con las opciones")
    opciones = encuesta["opciones"] if encuesta else None
    _exigir(not a.produccion_cercana or a.paso == "compartir", "--produccion-cercana solo vale en compartir")
    varios = {"fotogramas": a.fotogramas} if a.fotogramas > 1 else {}
    opcional = {"opcional": True} if a.fotogramas > 1 else {}
    pasos_ = {
        "abrir": lambda: th.abrir(ev),
        "nuevo": lambda: th.nuevo(ev),
        "texto": lambda: th.texto(texto, ev),
        "galeria": lambda: th.galeria(ev, sel),
        "musica": lambda: th.musica(ev, **opcional),
        "encuesta": lambda: th.encuesta(opciones, ev),
        "compartir": lambda: th.compartir(texto, a.tema, bool(a.subido_en), ev, produccion_cercana=a.produccion_cercana,
                                          opciones=opciones, **varios),
    }
    return _paso_telefono(ev, f"th-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))


def cmd_fb(a) -> int:
    from labkit import facebook_feed as fb
    ev = _evidencia(a.run)
    sel = _subidas_de_flujo(a, a.paso == "galeria")
    pie = _leer_texto(a.pie, "el pie de Facebook") if a.paso in ("pie", "compartir") else None
    if a.paso == "pie":
        repetido = colision.pie_instagram_reciente(pie, ROOT / "experiments" / "media-lab" / "runs", ahora(), ROOT)
        _exigir(repetido is None, f"el pie es idéntico al de {repetido} (Instagram por teléfono, últimas 24 h): "
                                  "la copia automática lo haría indistinguible")
    _exigir(not a.produccion_cercana, "fb no usa --produccion-cercana: el pie exacto identifica la publicación")
    opcional = {"opcional": True} if a.fotogramas > 1 else {}
    pasos_ = {
        "abrir": lambda: fb.abrir(ev),
        "nuevo": lambda: fb.nuevo(ev),
        "galeria": lambda: fb.galeria(ev, sel),
        "musica": lambda: fb.musica(ev, **opcional),
        "pie": lambda: fb.pie(pie, ev),
        "siguiente": lambda: fb.siguiente(ev),
        "compartir": lambda: fb.compartir(pie, ev),
    }
    return _paso_telefono(ev, f"fb-inesperada-{a.paso}", pasos_[a.paso], _codigo_compartir(a.paso))
```

(En `fb`, `--fotogramas` solo cambia la galería y la música: el multifoto se confirma igual que la foto única.)

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.` (las pruebas de la fase 1 de `ig` y `telefono-subir` siguen igual)

```bash
git add experiments/media-lab/lab.py tests/test_media_lab.py
git commit -m "media lab claude: telefono-subir en orden inverso y subcomandos de teléfono con fotogramas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 17d: F. Multiimagen y secuencias — recetas en borrador, prompt de Codex y prompt de la ventana

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/codex-heartbeat-prompt.md`, `experiments/media-lab/claude-ventana-prompt.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Recetas de fotogramas y prompt de Codex**

Añadir al final de `seccion_secuencias`:

```python
    from labkit import recetas as RC
    for par in (("instagram", "feed_carousel"), ("instagram", "story_sequence"), ("facebook", "feed_multi_photo"),
                ("facebook", "story_sequence"), ("threads", "feed_carousel")):
        receta = RC.TODAS.get(par)
        check(receta is not None and receta["formato_encargo"].get("fotogramas") == 3
              and any("<subido_en…>" in c["args"] for c in receta["preparar"])
              and all("--fotogramas" in c["args"] for c in receta["publicar"])
              and all("--fotogramas" in c["args"] for c in receta["preparar"] if "<subido_en…>" in c["args"]),
              f"F: receta de {par} con fotogramas")
    heartbeat = (ROOT / "experiments" / "media-lab" / "codex-heartbeat-prompt.md").read_text(encoding="utf-8")
    check("prompts_fotogramas" in heartbeat, "F: el prompt de Codex explica prompts_fotogramas")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «F: receta de …» y «F: el prompt de Codex explica prompts_fotogramas».

En `recetas.py`, añadir antes de `TODAS`:

```python
def _fotogramas(receta: dict, nota: str, n: int = 3) -> dict:
    """La receta de una imagen convertida a `n` fotogramas: `--local` y `--subido-en` se repiten por fotograma
    (`<master…>`, `<subido_en…>`) y reciben `--fotogramas` los pasos con `<subido_en…>` (abrir, elegir, galeria) y
    los de audio, música y compartir."""
    def convertir(c: dict) -> dict:
        args = ["<master…>" if x == "<master>" else "<subido_en…>" if x == "<subido_en>" else x for x in c["args"]]
        if args[0] != "telefono-subir" and len(args) > 1 and (args[1] in ("audio", "musica", "compartir") or "<subido_en…>" in args):
            args += ["--fotogramas", "<fotogramas>"]
        return {**c, "args": args}

    return {**receta, "formato_encargo": {**receta["formato_encargo"], "fotogramas": n},
            **{fase: [convertir(c) for c in receta[fase]] for fase in FASES}, "nota": nota}
```

y a `TODAS`:

```python
    ("instagram", "feed_carousel"): _fotogramas(FEED_INSTAGRAM, (
        "Carrusel: selección múltiple en orden; la QA recibe ig-06-carrusel-f*.png y el orden de los másters. "
        "Sin chip de audio con varias imágenes: tema null y music_unavailable_in_native_composer.")),
    ("instagram", "story_sequence"): _fotogramas(HISTORIA_INSTAGRAM, (
        "Secuencia: un fotograma por imagen; la QA recibe igh-06-secuencia-f*.png y el orden de los másters.")),
    ("facebook", "feed_multi_photo"): _fotogramas(FEED_FACEBOOK_IMAGEN, (
        "Multifoto: la Página la muestra en rejilla, no en carrusel: anota el tratamiento real en el run.")),
    ("facebook", "story_sequence"): _fotogramas(HISTORIA_FACEBOOK, (
        "Secuencia: la QA recibe fbh-06-secuencia-f*.png y el orden de los másters.")),
    ("threads", "feed_carousel"): _fotogramas(FEED_THREADS_IMAGEN, (
        "Carrusel: la QA recibe th-07-carrusel-f*.png y el orden de los másters.")),
```

En `experiments/media-lab/codex-heartbeat-prompt.md`, sustituir el paso 3 por:

```markdown
3. Para cada encargo devuelto, genera con tu generación de imágenes integrada una imagen por cada ruta de "rutas", siguiendo "prompt" y todas las "restricciones". Si el encargo trae "prompts_fotogramas", la imagen de la ruta k (terminada en -f<k>.png) sigue además prompts_fotogramas[k-1]: son fotogramas de una misma secuencia, con la misma escena, estilo, paleta y personajes. Nunca pongas letras, números ni rótulos en la imagen. Guarda cada imagen exactamente en su ruta (PNG).
```

y en el paso 4 `[--imagen <ruta2>]` por `[--imagen <ruta2> …] (una --imagen por ruta, en orden)`.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/codex-heartbeat-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: recetas de carrusel, multifoto y secuencias y prompt de Codex con fotogramas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

> **Controlador con el usuario presente (no subagente).**

Mensaje al usuario: abrir la app de ChatGPT → Codex → Automatizaciones → «Media lab hasta 1 octubre» y sustituir el prompt por el contenido de `experiments/media-lab/codex-heartbeat-prompt.md`, sin cambiar el horario. Esperar confirmación y comprobar con `grep -c "prompts_fotogramas" ~/.codex/automations/media-lab-hasta-1-octubre/automation.toml` (esperado `1`). Hasta entonces no se crean encargos con `fotogramas`.

- [ ] **Step 2: Prompt de la ventana**

Añadir al final de `seccion_prompt_ventana`:

```python
    for fragmento in ("fotogramas", "music_unavailable_in_native_composer"):
        check(fragmento in texto, f"el prompt de la ventana menciona {fragmento}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `FALLARON` con «el prompt de la ventana menciona …» para esos fragmentos.

En `experiments/media-lab/claude-ventana-prompt.md`:

Tras la frase «En `--formato` usa el `formato_encargo` de la receta.» del paso 5, añadir:

```markdown
 En secuencias y carruseles, la receta ya pide `"fotogramas": N`: añade un `--prompt-fotograma <archivo>` por fotograma, en orden; un encargo no mezcla secuencias con imágenes sueltas.
```

Tras la frase «y el run JSON copiando experiments/media-lab/run-template.json.» del paso 7a, añadir:

```markdown
 En secuencias y carruseles, un máster por fotograma y en orden.
```

En el paso 7b, sustituir «`<pie>` por el archivo del pie» por «`<pie>` por el archivo del pie, `<master…>` y `<subido_en…>` por un `--local` o un `--subido-en` por fotograma y en orden, `<fotogramas>` por su número», y tras la frase «Tras cada uno abre la captura y comprueba lo que dice `ver`.» añadir:

```markdown
 Si un paso de música o audio devuelve `tema: null` con `music_unavailable_in_native_composer`, quita `--tema <tema>` de los comandos siguientes y anótalo en el run.
```

Tras la frase «el revisor solo comprueba que no haya texto ni imagen cortados o tapados.» del paso 7c, añadir:

```markdown
 En secuencias y carruseles, pásale todas las capturas por fotograma y el orden de los másters.
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/claude-ventana-prompt.md tests/test_media_lab.py
git commit -m "media lab claude: la ventana publica carruseles y secuencias con un máster por fotograma

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

- [ ] **Step 3: Actualizar la tarea programada**

> **Controlador con el usuario presente (no subagente).**

Llamar a `mcp__scheduled-tasks__update_scheduled_task` con `taskId: sabiduria-media-lab` y `prompt`: el contenido íntegro de `experiments/media-lab/claude-ventana-prompt.md`, sin cambiar su `cronExpression` (`40 * * * *`) ni el título: el prompt se pega entero, con su paso 0 `lab.py turno`. Comprobar con `mcp__scheduled-tasks__list_scheduled_tasks` que el cron sigue en `40 * * * *` y que el prompt guardado contiene «lab.py turno» y «fotogramas».

---

### Task 17e: F. Multiimagen y secuencias — sonda S3 (sin publicar)

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Create: `tests/fixtures/telefono/instagram/{feed-selector-tres,historia-selector-tres}.xml`, `tests/fixtures/telefono/threads/galeria-tres.xml`, `tests/fixtures/telefono/facebook/{galeria-tres,historia-creador-tres}.xml`
- Modify: `experiments/media-lab/labkit/textos.py`, `experiments/media-lab/labkit/pantalla.py` (solo si el ordinal va en la content-desc), `experiments/media-lab/findings.md`, `tests/test_media_lab.py`

- [ ] **Step 1: Sonda S3 supervisada (sin publicar)**

Con el usuario presente:

1. Subir tres imágenes 4:5 y tres 9:16 ya comiteadas, **cada serie en orden inverso** (la tercera primero) con `lab.py telefono-subir --local <imagen>` de una en una, dejando al menos 2 s entre ellas.
2. Instagram feed: `sonda instagram lanzar`, perfil, «Créer», «Publication», activar la selección múltiple (`--desc` del botón que anotó S1) y tocar la segunda y la tercera miniatura; `sonda instagram volcar --nombre feed-selector-tres`. Anotar si la primera recibe el ordinal 1 al activar la selección múltiple y dónde va el número (texto hijo o content-desc). Seguir con «Suivant» hasta el editor y anotar si aparece «Audio suggéré» con varias imágenes. Salir con `atras` y descarte.
3. Instagram Story: «Créer» → «Story» → selección múltiple → las tres 9:16 en orden; `volcar --nombre historia-selector-tres`; «Suivant» y anotar la vista previa de la secuencia y el chip de audio. Salir con descarte.
4. Threads: compositor → galería → tocar las tres 4:5 en orden; `volcar --nombre galeria-tres`; anotar si Threads admite varias sin conmutador y si ofrece música con varias imágenes. Salir con descarte.
5. Facebook: compositor de la Página → galería → «Seleccionar varios» → las tres; `volcar --nombre galeria-tres`; «Crear historia» → selección múltiple → las tres 9:16; `volcar --nombre historia-creador-tres`. Anotar música disponible. Salir con descarte.
6. Volcar también, desde el perfil de Instagram, una publicación con varias imágenes si la cuenta tiene alguna (`volcar --nombre ig-publicacion-carrusel`) para el content-desc de la cuadrícula y el indicador «1/N»; si no la hay, lo vuelca la ventana manual de la tarea 17f.
7. Comprobar con `telefono-captura` que no se publicó nada, podar los cinco volcados con `lab.py fixture-podar` a los fixtures de **Files** y escribir en `findings.md` «Sonda S3 de la fase 2 (<fecha>, sin publicar)» con: dónde va el ordinal, si la primera se preselecciona, texto del botón de selección múltiple por app, música con varias imágenes por app (`music_unavailable_in_native_composer` donde no la haya), indicador de páginas y content-desc de la cuadrícula del perfil.

- [ ] **Step 2: Confirmar los textos y volver a podar**

Con lo anotado en S3: sustituir en `textos.py` los valores de `seleccion_multiple`, `publicacion_cuadricula` y `seleccionar_varios` por los observados y quitar su marca; añadir a las tuplas `PATRONES_FIXTURE` de las tres apps el patrón `r"\d{1,2}"` (los ordinales de la selección múltiple). Si S3 mostró el ordinal en la content-desc y no como texto hijo, adaptar `pantalla.ordinal_de` (tarea 17a, Step 3) para leerlo de ahí y ajustar `xml_rejilla` en la prueba. Volver a podar los cinco volcados de S3 con `lab.py fixture-podar` a los fixtures de **Files** y abrirlos con Read.

- [ ] **Step 3: Prueba con los volcados reales de S3 y commit**

Añadir al final de `seccion_secuencias`:

```python
    for app, nombre, lector in (("instagram", "feed-selector-tres", IP.fecha_miniatura), ("instagram", "historia-selector-tres", IP.fecha_miniatura),
                                ("threads", "galeria-tres", TP.lector_fecha), ("facebook", "galeria-tres", FP.fecha_miniatura_es),
                                ("facebook", "historia-creador-tres", FP.fecha_miniatura_es)):
        xml = fixture(app, nombre)
        primeras = P.miniaturas(xml, TX.PAQUETES[app], lector)[:3]
        check(len(P.selecciones_ordenadas(xml, TX.PAQUETES[app], [lector(n["desc"]) for n in primeras], lector)) == 3,
              f"F: tres fotogramas en orden en el volcado real {app}/{nombre}")
```

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/textos.py experiments/media-lab/labkit/pantalla.py experiments/media-lab/findings.md tests/fixtures/telefono tests/test_media_lab.py
git commit -m "media lab claude: sonda S3 y volcados reales de la selección múltiple

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 17f: F. Multiimagen y secuencias — ventanas manuales y promoción

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

**Files:**
- Modify: `experiments/media-lab/labkit/recetas.py`, `experiments/media-lab/findings.md`, `experiments/media-lab/coverage.json`, `experiments/media-lab/runs/`, `experiments/media-lab/progress.md`, `tests/test_media_lab.py`, `tests/fixtures/telefono/`

- [ ] **Step 1: Primeras publicaciones en ventanas manuales y promoción**

Una ventana manual por par, en ventanas distintas y con `--borrador`, igual que el Step 1 de la tarea 11d: `instagram/feed_carousel`, `instagram/story_sequence`, `facebook/feed_multi_photo`, `facebook/story_sequence` y `threads/feed_carousel`. El encargo lleva `"fotogramas": 3` y tres `--prompt-fotograma`; la subida es un único `telefono-subir` con los tres `--local` en orden; la QA recibe todas las capturas por fotograma y el orden de los másters. En la ventana de `instagram/feed_carousel`, si S3 no volcó una publicación con varias imágenes, `lab.py sonda instagram volcar --run SONDA-F2-F --supervisada --nombre ig-publicacion-carrusel` con la publicación abierta y confirmar `publicacion_cuadricula` y el indicador «1/3». En `findings.md`, una línea por ventana (run, estado, orden verificado, música disponible o `music_unavailable_in_native_composer`, tratamiento real en Facebook). Añadir a `PROMOVIDAS` cada par confirmado con su run y, al final de `seccion_secuencias`, una comprobación `in RC.RECETAS` por par promovido.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/recetas.py experiments/media-lab/findings.md experiments/media-lab/coverage.json experiments/media-lab/runs experiments/media-lab/progress.md tests/test_media_lab.py tests/fixtures/telefono
git commit -m "media lab claude: carruseles, multifoto y secuencias promovidos tras sus ventanas manuales

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

Con el push hecho, `lab.py lock-soltar --dueno manual`: la sesión edita, comitea y hace push con el cerrojo tomado.

---

### Task 18: Sonda G0 de Edits y entrada para la fase 3 (spec, fila 12)

Depende de la tarea 9. Solo sonda: no se comparte y no se descarga ni se guarda nada con música del catálogo (decisión 7). «Export» se permite solo si es el único camino a «Choose where to share», sin tema del catálogo añadido. Las 12 celdas de vídeo quedan `planned` para la fase 3.

**Files:**
- Modify: `experiments/media-lab/labkit/telefono.py`, `experiments/media-lab/labkit/textos.py`, `experiments/media-lab/findings.md`, `experiments/media-lab/progress.md`
- Test: `tests/test_media_lab.py`

- [ ] **Step 1: Escribir la prueba**

Añadir antes de `SECCIONES` y registrar `seccion_edits_g0,`:

```python
def seccion_edits_g0() -> None:
    print("\n27. Fase 2 (G0): sonda de Edits sin compartir ni descargar")
    from labkit import telefono as T, textos as TX

    check(T.URI_VIDEOS == "content://media/external/video/media" and T.URI_VIDEOS in T.consulta_recientes(3, T.URI_VIDEOS),
          "G0: consulta de vídeos recientes en MediaStore")
    for valor in ("Download", "Télécharger", "Save to device", "Enregistrer sur l’appareil"):
        check(valor in TX.NO_TOCAR, f"G0: la sonda no pulsa «{valor}»")
    with entorno_lab_fase2() as (lab, raiz):
        sim = TelefonoSimulado([xml_perfil()])
        res, err = con_telefono_simulado(sim, lambda: lab("sonda", "edits", "tocar", "--run", "SONDA-F2-G0", "--nombre", "a",
                                                          "--supervisada", "--texto", "Download"))
        check(rechazo(res, "envío") and sim.toques == [] and sim.volcados_leidos == 0,
              "G0: sonda edits tocar se niega a descargar")
```

- [ ] **Step 2: Ver que falla**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: traceback con `AttributeError: module 'labkit.telefono' has no attribute 'URI_VIDEOS'` en la sección 27.

- [ ] **Step 3: Implementar**

En `telefono.py`, tras `URI_IMAGENES`:

```python
URI_VIDEOS = "content://media/external/video/media"
```

En `textos.py`, sustituir `NO_TOCAR` por:

```python
NO_TOCAR = frozenset({
    "Anular",  # «Cambiaste a…» de Facebook: deshace el cambio a la Página
    # Edits (sonda G0): nada se descarga ni se guarda en el dispositivo (decisión 7). «Export» no está: se permite
    # solo si es el único camino a «Choose where to share», sin música del catálogo.
    "Download", "Télécharger", "Save to device", "Enregistrer sur l’appareil",
})
```

- [ ] **Step 4: Ver que pasa y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/labkit/telefono.py experiments/media-lab/labkit/textos.py tests/test_media_lab.py
git commit -m "media lab claude: la sonda de Edits no descarga ni guarda y MediaStore lista vídeos

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Sonda G0 supervisada**

> **Controlador con el usuario presente (no subagente).**

**Sesión con el teléfono en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, con `.venv/bin/python experiments/media-lab/lab.py …` relativo), nunca a la vez que una ventana:

1. Mirar cuándo toca la próxima ventana con `lab.py turno` (sin `--marcar`: marcar es solo de la ventana programada) o `mcp__scheduled-tasks__list_scheduled_tasks` y empezar lejos de ella si se puede.
2. `lab.py lock-tomar --dueno manual`. Si devuelve `cerrojo: false`, hay una ventana en curso: esperar a que termine y repetir.
3. Antes de la sesión, desde el worktree, integrar lo comiteado en las subtareas anteriores (`git fetch origin main && git rebase origin/main && git push origin HEAD:main`); después, con el cerrojo tomado y en el árbol principal, `git fetch origin main && git rebase origin/main`. Si ese rebase falla: `git rebase --abort`, `lab.py lock-soltar --dueno manual`, avisar al usuario y no seguir.
4. Renovar con `lab.py lock-tomar --dueno manual` antes de que pasen 90 min (`cerrojo.ABANDONO`) desde la última toma. Mientras este cerrojo está tomado, una ventana programada que se dispare encuentra `cerrojo: false` y termina sin publicar. En una ventana manual de primera publicación se omiten los pasos 0, 1 y 10 del prompt: este cerrojo sustituye al paso 1, el paso 7 lo renueva con `--dueno manual` en lugar de `--dueno programada`, y se suelta solo al final de la sesión (punto 5).
5. Los commits de la sesión salen desde este árbol, con `git fetch origin main && git rebase origin/main && git push origin HEAD:main`; al terminar, `lab.py lock-soltar --dueno manual`. El worktree de código rebasa sobre `origin/main` antes de su siguiente commit.

Con el usuario presente y sin otra sonda pendiente, `S="--run SONDA-F2-G0 --supervisada"`:

1. `lab.py preflight` (anotar la versión de Edits) y `lab.py telefono-subir --local <máster 9:16 comiteado>`.
2. `lab.py sonda edits lanzar $S --nombre g0-01-inicio`; nuevo proyecto con `sonda edits tocar` sobre el botón que muestre el volcado (`g0-02-nuevo`), elegir la imagen de hoy (`g0-03-proyecto`) y comprobar en la captura que ocupa el 9:16 **sin franjas**.
3. Ajustar la duración a entre 8 y 15 s con los controles que muestre el volcado (`g0-04-duracion`) y anotar cómo se expresa la duración en el volcado.
4. Abrir la hoja de audio (`g0-05-audio`) y volcarla sin elegir ningún tema del catálogo para descargar.
5. Abrir «Choose where to share» o su equivalente (`g0-06-compartir-en`), tocar Instagram para ver el compositor de Reel (`g0-07-instagram-reel`) y volver con `sonda edits atras` / `sonda instagram atras`; tocar Facebook para ver el selector con la Página y Reel/Story (`g0-08-facebook`) y volver. Nunca «Share», «Post» ni «Publish» (la sonda los rechaza) y nunca descargar o guardar en el dispositivo; «Export» solo si es el único camino a «Choose where to share» y sin ningún tema del catálogo añadido.
6. Salir descartando el proyecto con `sonda edits atras` mirando capturas.
7. Comprobar que no se exportó ningún vídeo: `.venv/bin/python -c "import sys; sys.path.insert(0, 'experiments/media-lab'); from labkit import telefono as T; print(T.recientes_mediastore(3, T.URI_VIDEOS))"` y confirmar que ningún `date_added` es de la sesión; si se usó «Export», el vídeo exportado (sin música del catálogo) se anota en `findings.md` y el usuario decide si lo borra.

- [ ] **Step 6: `findings.md` y `progress.md`**

Añadir a `findings.md`:

```markdown
## Sonda G0 de Edits (<fecha>, sin compartir)

- Edits <versión>; imagen 9:16 sin franjas: <sí/no>; control de duración y cómo aparece en el volcado.
- Hoja de audio: qué ofrece sin descargar; si el audio del catálogo solo se puede usar compartiendo desde la app.
- «Choose where to share»: destinos, compositor de Reel de Instagram (controles de encuesta, ubicación, etiqueta de IA) y selector de Facebook (Página, Reel, Story).
- Preguntas abiertas para la fase 3: duración mínima por red, códec, montaje de másters de vídeo a partir de imágenes aprobadas y voz propia para LAB-NARRATED-009.
```

y en `progress.md`, una línea: «Fase 2: las 12 celdas de vídeo (reel_video, story_video, feed_video) quedan planned para la fase 3; sonda G0 hecha el <fecha> (findings.md)».

- [ ] **Step 7: Spec de la fase 3**

Con `superpowers:brainstorming`, a partir de la sección G0 de `findings.md`, las decisiones 7 y 8 de la spec de la fase 2 y las 12 celdas de vídeo de `coverage.json`, redactar `docs/superpowers/specs/<fecha>-media-lab-fase3-video-design.md`; su plan se escribe después con `superpowers:writing-plans`. No forma parte de la ejecución de este plan.

- [ ] **Step 8: Commit**

```bash
git add experiments/media-lab/findings.md experiments/media-lab/progress.md
git commit -m "media lab claude: sonda G0 de Edits sin compartir y entrada para la fase 3 de vídeo

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

---

### Task 19: Marcadores `selected_after_day_7` (decisión 9, el 2026-09-20)

Sin código propio: usa flujos ya promovidos.

**Cambios en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, que es de las ventanas): mirar el próximo turno con `lab.py turno` (sin `--marcar`); `lab.py lock-tomar --dueno manual` (si devuelve `cerrojo: false`, esperar a que termine la ventana en curso); `git fetch origin main && git rebase origin/main` (si falla, `git rebase --abort`, soltar el cerrojo, avisar y no seguir); hacer los cambios, commit y push renovando el cerrojo antes de 90 min (`cerrojo.ABANDONO`); y `lab.py lock-soltar --dueno manual`.

**Files:**
- Modify: `experiments/media-lab/coverage.json`, `experiments/media-lab/progress.md`

- [ ] **Step 1: Listar los marcadores y los pares promovidos**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python -c "import json; [print(c['cell_id'], c['platform'], c['native_format'], c['status']) for c in json.load(open('experiments/media-lab/coverage.json'))['cells'] if c['native_format'].endswith('selected_after_day_7')]"`
Expected: una fila por cada celda cuyo `native_format` acaba en `selected_after_day_7`; se trabajan todas las que salgan, sin suponer cuántas son.

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python -c "import sys; sys.path.insert(0, 'experiments/media-lab'); from labkit import recetas; print(sorted((par, r['superficie']) for par, r in recetas.RECETAS.items()))"`
Expected: los pares promovidos con su superficie.

- [ ] **Step 2: Elegir el formato de cada marcador**

Para cada marcador: superficie `story` si su `native_format` empieza por `story_`, si no `feed`. Candidatos: los formatos promovidos de esa red y superficie. Celdas maduras: las `published` por `android_native` de esos formatos con instantánea de 72 h en su run (`publication.snapshots`). Métrica: alcance a 72 h dividido entre `exposure_context.follower_count` del run. Si hay al menos dos celdas maduras comparables (dos formatos distintos con instantánea de 72 h), gana el formato de mayor alcance por seguidor; si no, `feed_single_image` en feed y `story_image` en Story.

- [ ] **Step 3: Registrar**

En `coverage.json`, en cada marcador: `native_format` pasa al formato elegido, `status` sigue `planned` y `capability_evidence` dice «Decisión 9 (2026-09-20): <formato> con <valor> de alcance por seguidor a 72 h frente a <otros formatos y valores> (runs <ids>)» o «Decisión 9 (2026-09-20): sin dos celdas maduras comparables, formato por defecto <formato>». En `progress.md`, una línea por marcador con la misma frase.

- [ ] **Step 4: Validar y commit**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python -c "import json; json.load(open('experiments/media-lab/coverage.json')); print('ok')"`
Expected: `ok`

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python tests/test_media_lab.py`
Expected: `El laboratorio cumple sus contratos.`

```bash
git add experiments/media-lab/coverage.json experiments/media-lab/progress.md
git commit -m "media lab claude: formatos de los marcadores selected_after_day_7 por la regla del día 7

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

---

### Task 20: Cierre de la campaña (2026-10-01)

**Cambios en el árbol principal** (`/Users/hec/dev/sabiduriaPublisher`, que es de las ventanas): mirar el próximo turno con `lab.py turno` (sin `--marcar`); `lab.py lock-tomar --dueno manual` (si devuelve `cerrojo: false`, esperar a que termine la ventana en curso); `git fetch origin main && git rebase origin/main` (si falla, `git rebase --abort`, soltar el cerrojo, avisar y no seguir); hacer los cambios, commit y push renovando el cerrojo antes de 90 min (`cerrojo.ABANDONO`); y `lab.py lock-soltar --dueno manual`.

**Files:**
- Modify: `experiments/media-lab/progress.md`

- [ ] **Step 1: Listar lo que no llegó**

Run: `/Users/hec/dev/sabiduriaPublisher/.venv/bin/python -c "import json, sys; sys.path.insert(0, 'experiments/media-lab'); from labkit import recetas; celdas = json.load(open('experiments/media-lab/coverage.json'))['cells']; [print(c['cell_id'], c['platform'], c['native_format'], c['status'], 'borrador' if (c['platform'], c['native_format']) in recetas.BORRADORES else 'sin receta' if (c['platform'], c['native_format']) not in recetas.RECETAS else 'promovida') for c in celdas if c['publishing_route'] == 'android_native' and c['status'] in ('planned', 'ready', 'blocked')]"`
Expected: una fila por celda de teléfono sin publicar, con el estado de su receta.

- [ ] **Step 2: Motivo en `progress.md`**

Añadir la sección «Fase 2: celdas de teléfono sin publicar a 2026-10-01» con una línea por par (red, formato, celdas) y su motivo: «receta en borrador, falta la ventana manual», «sonda S2/S3 pendiente», «blocked: <reason_if_blocked_or_unsupported>», «vídeo: fase 3» o «sin receta (fuera de la fase 2)». Las celdas siguen `planned` salvo las ya `blocked`.

- [ ] **Step 3: Commit**

```bash
git add experiments/media-lab/progress.md
git commit -m "media lab claude: celdas de teléfono que no llegaron a la fase 2 y su motivo

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

---

## Autorrevisión (writing-plans)

### 1. Cobertura de la spec y de las decisiones posteriores

| Requisito | Tarea |
|---|---|
| Objetivo: módulo con lectores puros probados contra volcados reales podados | 9, 11a, 12a, 14a, 15a, 16c, 17e |
| Primera publicación en ventana manual `confirmado` antes de que la tarea programada lo elija | 4 (`PROMOVIDAS`/`BORRADORES`, `--borrador`); 11d, 12d, 14d, 15d, 16e, 17f |
| Ninguna celda sin PASS de QA; copias en `publication.cross_posting` | 8 (prompt), `copias` de cada receta |
| Lo que no llegue queda `planned` con motivo en `progress.md` | 16c (S2 fallida), 18, 20 |
| Ritmo cada 5 h (decisión del 2026-09-15): turno, noches, medición de Stories, cola | 0, 8, cada actualización de la tarea programada; desviaciones 21–23 |
| 1A `pantalla.py` | 1, 3, 11a, 12a, 16b-1, 17a |
| 1A `pasos.py` | 2, 3 (`tocar` con guardia), 11b-1, 11b-2, 16b-1, 17b-1 |
| 1A `reloj.py` | 1, 2 |
| 1A `textos.py` | 3 (`ENVIO_HISTORIA`, `PREFIJOS_ENVIO`, `NO_ENVIO`, `TITULOS_BORRADO`); claves en 11a, 12a, 14a, 15a, 16b-1, 16b-2, 17b-1, 17e |
| 1A `telefono.py`: `arrastrar`, `recientes_mediastore`, `URI_VIDEOS` | 11b-1, 17a, 18 |
| 1A `instagram_pantallas.py` e `instagram_feed.py` | 1, 2, 5 (comprobación en el teléfono), 11a, 17b-1 |
| 1A `instagram_historia.py` | 11b-2, 16b-1, 17b-1 |
| 1A `threads_pantallas.py` / `threads_feed.py` | 12a, 12b, 16b-2, 17b-2 |
| 1A `facebook_pantallas.py` / `facebook_feed.py` / `facebook_historia.py` | 14a, 14b, 15a, 15b, 16b-1, 17b-2 |
| 1A `stickers.py` | 11b-1, 16b-1 |
| 1A `recetas.py` y `fixtures.py` | 4, 6 |
| 1B `TELEFONO_IMPLEMENTADO`, un teléfono por ventana, exclusión por copias | 4 |
| 1C `zona_reservada` / `fotogramas` y prompt de Codex / no mezclar formatos | 16a / 17a, 17d / `_comprobar_celdas`, 8, 17d |
| 1D subcomandos de flujo, `render --zona` (16a), `telefono-subir` repetible, `telefono-atras --app`, `telefono-descartar`, `receta`, `sonda`, `preflight` | 11c, 12c, 14c, 15c, 16b-1, 16b-2, 17c; 5, 6, 7 |
| 1E cambios del prompt | 8 (prompt de `d8ac308` de la tarea 15 más la fase 2) y pasos de prompt de 11c, 12c, 13, 14c, 15c, 16d, 17d, con anclas comprobadas contra ese texto |
| 2 Sondas S1, S2, S3 y G0, sin publicar y con cerrojo manual | 9, 16c, 17e, 18 |
| 3 Común: identidad, `BorradorPendiente`, doble volcado y un toque, estados | 2, 3, 11a, 11b-2, 12b, 14b, 15b |
| 3 A0 / A / B / C / D / E / F | 10 / 11a–11d / 12a–12d / 14a–14d / 15a–15d / 16a–16e / 17a–17f |
| 4 Modo `buscar` y métricas de Stories | 13; `actividad` en 11c y 15c; regla 4–20 h en 8 y en las recetas de Story |
| 5 Orden y condiciones de promoción | tabla de correspondencia; 4 |
| 6.1–6.10 Decisiones abiertas | 7; 16b-1, 16c, 16e; 10, 11c, 15c; 11c, 4; 12b, 13, 14b; 8; 18; fuera de alcance; 19; 12c |
| 7 Pruebas: fixtures, lectores, casos límite, simulador por flujo con un toque de envío y ningún toque de envío fuera de `compartir`, registro y validaciones | 1, 3, 4, 6, 11b-1, 11b-2, 12b, 14b, 15b, 16a, 16b-1, 16b-2, 17a, 17b-1, 17b-2 |

**Requisitos de la spec sin tarea:** ninguno. TikTok (decisión 8) queda fuera por la propia spec.

### 2. Puntos de la revisión final aplicados

- **C1:** el prompt literal de la tarea 8 parte del de `d8ac308` y solo añade la fase 2; paso 0, paso 1 con `turno --marcar` y 7a con `lab.py render`/`lab.py tarjeta` quedan idénticos (comprobado línea a línea al generar el plan). `seccion_prompt_ventana` exige también «turno --marcar» y «lab.py render». Las anclas de los prompts de 11c, 12c, 13, 14c, 15c, 16d y 17d existen una sola vez en ese texto; 16d usa `lab.py render … --zona`, que 16a añade a `lab.py render`.
- **I-a:** la tarea 8 ya no toca `encargos.py`: su Step 5 solo comprueba `MAX_EN_COLA = 10`; fuera de sus archivos, de su `git add` y del mapa. Desviaciones 21 y 23 y tarea 0 atribuyen la cola, `turno --marcar` y `render` a la tarea 15.
- **I-b:** 11d dice que en la ventana manual se omiten los pasos 0, 1 y 10 (el cerrojo manual sustituye al 1 y el 7 renueva con `--dueno manual`); ya no suelta el cerrojo antes del Step 2, y 11d, 12d, 14d, 15d, 16e y 17f lo sueltan tras el push final. El punto 4 del bloque común queda sin ambigüedad.
- **I-c:** la tarea 9 hace push de los fixtures de S1 antes de 11a.
- **I-d:** sin botón «Música» sintético: 14b y 15b exigen el texto en `compositor-con-imagen` y `historia-editor` reales.
- **I-e:** la tarea 9 quita de `NO_ENVIO` y de su prueba las excepciones que S1 no confirmó; 11d cubre «Partager à» a mano si falta `ig-08`; `NO_ENVIO` solo exceptúa de los prefijos, con prueba de que no anula un envío exacto.
- **Menores:** rebase fallido en el árbol principal → `git rebase --abort`, soltar el cerrojo, avisar y parar (bloque común y tareas 19–20); `lab.py turno` sin `--marcar` en sesiones manuales y en la tarea 5; prefijos ingleses que atrapan «Posts»/«Shared» anotados en la desviación 9 (falla cerrado).
- **Siguen vigentes de la revisión anterior:** ritmo cada 5 h, cerrojo manual en toda sesión con el teléfono, worktree para el código con push antes de sesiones y de actualizar la tarea programada, `_fotogramas` con `<subido_en…>`, guion de `FH.compartir`, dependencia de 17 en 16a/16b, `toques_sobre_envio` con el volcado de cada toque, regla de medición de Stories, `permitir` que solo ignora sus nodos y las piezas 11b-1/2, 16b-1/2 y 17b-1/2.

### 3. Escaneo de marcadores

- No hay «TBD», «TODO», «añadir validación adecuada» ni «igual que la tarea N» en pasos de código; los pasos operativos que remiten a otros nombran sus comandos.
- Los valores entre ángulos (`<run>`, `<fecha>`, `<versiones.threads>`, `<subido_en>`, `<content-desc … en ig-04>`) son datos de la ejecución.
- «confirmar contra el fixture de S1/S2/S3» sigue la convención de la cabecera, también en `NO_ENVIO`.

### 4. Coherencia de nombres y firmas

- `textos`: `ENVIO`, `ENVIO_IDS`, `ENVIO_HISTORIA`, `PREFIJOS_ENVIO`, `NO_ENVIO`, `NO_TOCAR`, `DESCARTE`, `TITULOS_BORRADO`, `EDADES`, `PATRONES_FIXTURE`, `PATRONES_FIXTURE_TEXTO`, `texto`, `normalizar`, `normalizar_titulo`, `coincide_o_prefijo`, `es_texto_envio`, `es_no_tocar`, `es_titulo_borrado`, `es_titulo_descarte`, `conocidos`, `permitido`.
- `pantalla`: `elegir`, `coincidencias`, `nodo`, `por_id`, `pulsable`, `tiene_texto`, `hay_desplegable`, `evaluar_envio`, `se_solapan_verticalmente`, `emergente_solapada`, `parece_desplegable`, `describe_emergente`, `pista_idioma`, `es_envio(xml, n, ignorar)`, `nodo_sonda`, `boton_descarte`, `miniatura_por_hora`, `edad_segundos`, `marcado_en_fila`, `estado_confirmado`, `imagen_bajo`, `tema_bajo_cabecera`, `aviso_corto`, `observacion_envio`, `campos`, `miniaturas`, `ordinal_de`, `selecciones_ordenadas`.
- `pasos`: `exigir_listo`, `esperar_que`, `volcado_fresco`, `esperar_estable`, `escribir_texto(texto, paquete, *, campo, exigir, desplegable_nodos, emergente)`, `atras`, `descartar`, `tocar(n, xml, permitir)`, `observar_envio`, `enviar(..., listo(xml, emergentes), ...)`, `lanzar_app`, `colocar_sticker`, `pegar_en`, `encuesta_de_historia`, `seleccionar_en_orden(paquete, subidas, lector_fecha, boton_multiple, xml_boton)`, `recorrer_fotogramas`, `deslizar_media`, `tocar_derecha`.
- `recetas`: `TODAS`, `PROMOVIDAS`, `RECETAS`, `BORRADORES`, `CLAVES`, `FASES`, `para`, `renderizar`, `RecetaNoDisponible`, `_cmd`, `_fotogramas`.
- `lab.py`: `_evidencia`, `_parser_flujo`, `_subidas`, `_zona`, `_encuesta`, `_leer_texto`, `_codigo_compartir`, `cmd_render` con `--zona` (16a), `_subidas_de_flujo`, `PASOS_*`; versiones finales de los `cmd_*` de flujo en 17c.
- Pruebas: `TelefonoSimulado` con `volcados_leidos`, `ultimo`, `toques_en`, `arrastres`, `recientes`; ayudantes `toques_sobre_envio(sim, paquete)`, `rechazo`, `entorno_lab_fase2`, `fixture`, `fixture_o`, `con_valor`, `con_nodo`, `primera_fecha`, `xml_visor_historia`, `xml_destino_historia`, `xml_visor_historia_fb`, `xml_interstitial_fb`, `publicacion_pagina_xml`, `xml_encuesta_editando`, `xml_encuesta_colocada`, `xml_rejilla(..., paquete, descripcion)`. Prueba de la fase 1 que cambia: `seccion_seleccion` (C5 a `reel_video`, 11d); la de la cola ya está en 10 desde la tarea 15 y no se toca.
