# Media lab findings

Updated: 2026-09-13 22:23 Europe/Madrid

## Day 1 operational findings

The isolated API route published one original single-image editorial to the verified Sabiduría de Bolsillo Facebook Page, Instagram account and Threads account without altering the normal queue, schedule, feed or production workflows. All three submissions succeeded on the first attempt. Active publishing time was 5.332 seconds for Facebook, 13.637 seconds for Instagram and 12.749 seconds for Threads.

Read-only API checks confirmed caption and media fidelity, and native Android inspection confirmed that the correct brand account, image and caption were visible. Facebook additionally reported `is_published=true` and `is_hidden=false`. Threads required resolving the canonical permalink after publishing; constructing a numeric fallback URL was not reliable, so the lab publisher now retrieves the canonical URL.

The first image-generation direction was accepted and finished with a deterministic code overlay so Spanish spelling, dates and line breaks did not depend on generated text. The matched Merian direction needed one focused repair because the first pupa looked metallic and biologically implausible. That is evidence of an image-QA cost, not yet evidence that a paid image workflow would be better.

The Android phone is viable as a native route: ADB control is authorized; the three brand accounts were resolved; Facebook, Instagram and Threads composers opened; and the finished Android comparison image was transferred. Threads visibly exposes Poll and Location attachments. Facebook's brand Story editor exposes Poll, Question, Location, Music and Link stickers. Instagram's brand Story editor exposes Multi-option Poll, Question, Location, Music, Slider and Link, while its Story picker offers multi-select, Templates and Collage. These are verified draft capabilities; no Story was shared during the probe.

Edits successfully imported the Merian still and exported a local file, but its first default output was a silent 3.03-second, 1080×1920, 30 fps HEVC video with the 4:5 image letterboxed. It was rejected before publication: it is below the documented Facebook Reel minimum used by the project, has poor use of the vertical frame, contains no audible treatment and has not passed API codec compatibility. The next free test is an 8–15-second full-frame export with owned narration or licensed audio.

Edits also handed that export directly to Instagram's Reel composer and to a Facebook destination chooser that named `Sabiduria De Bolsillo` and offered both Reel and Story. Instagram's pre-share screen exposed Poll, Prompt, Location and AI-label controls. The handoffs establish route availability, but not delivery reliability, because the rejected master was never shared.

## Measurement limits

No audience-performance conclusion is available on launch day. The first experiment needs comparable 24-hour, 72-hour and seven-day snapshots, kept separate by platform metric definition. Nearby normal posts, topic, time of day and the additional lab posting volume remain confounders; baseline comparisons are observational.

The campaign currently has 136 explicit family × network × format × route cells. A safe first-wave ceiling of three extra releases per day fits 42 cells in fourteen days, leaving 94 explicit spillover cells unless probes establish that a combination is unsupported or a later decision raises audience load. A successful image on one network or route does not satisfy the other cells.

## Free workflow selected so far

1. Start from a verified published seed and retain its `do_not_use` constraints.
2. Generate artwork without exact text, then apply exact Spanish typography deterministically with the local renderer.
3. Gate anatomy, historical plausibility, labels, phone-size readability and disclosure before export.
4. Publish from an isolated lab manifest and collect a result artifact even when one destination fails.
5. Resolve canonical URLs through read-only platform calls, then inspect the final post natively on Android.
6. Keep the Android comparison as a distinct creative variant and release it only after a live production-collision check.

This workflow currently has zero incremental monetary spend. Included generation allowance, local compute and active human/agent time remain recorded costs rather than being described as universally free.

## Paid round: deferred pending evidence

No paid provider, trial or API call is recommended yet. The observed gaps all have an unexhausted zero-cost next test:

- **Image consistency:** one biological repair was needed. Repeat the selected workflow on at least two further people/scene seeds before pricing a paid consistency comparison.
- **Spanish voice:** no publishable matched voice sample exists. Test local synthesis and an optional owned human-phone narration first; private-only free outputs do not establish commercial suitability.
- **Motion/export:** the first Edits export failed the publishability gate. Correct duration, framing, audio rights and codec locally before attributing the problem to the product tier.
- **Native interactions:** Story polls/music and route-specific analytics still need account-level verification; payment cannot solve an unmeasured capability question.
- **Audience value:** no post has reached its first 24-hour measurement point. Do not pay to scale a treatment before retention, reach and meaningful engagement show a measurable gap or opportunity.

After mature measurements exist, a paid proposal should name the exact failed free baseline, the candidate provider, the matched retest, a spending cap, output/commercial rights, and cost per accepted piece including discarded attempts.

## Rescate codex exec (sonda del 2026-09-14)

- Versión probada: `codex-cli 0.154.0-alpha.6.2` (`/Applications/ChatGPT.app/Contents/Resources/codex`), con la configuración del usuario.
- `lab.py generar --encargo ENC-20260914-001 --timeout 600` (astrolabio, feed 1080×1350, «sin texto»): `ok` en unos 2 min, un PNG de 1080×1350 sin letras ni números, encargo en `generado` con `origen: codex-exec`, y la guardia no informó archivos ajenos. Rescate disponible.
- La nota de Codex dice que registró él mismo la imagen con `codex-generado`; el estado final coincide con el que deja `generar`.
- Hay que lanzarlo fuera del minuto de otras tareas programadas que comitean en el mismo árbol (p. ej. `sabiduria-respaldo-reloj`, hacia las :45 cada 2 h): un commit ajeno durante la generación la marcaría como cambios ajenos y bloquearía el encargo.

## Sonda del teléfono hasta el compositor (2026-09-14, sin publicar)

- `ig abrir` con la cortina de notificaciones desplegada sale con 4 (`PantallaInesperada`) y `telefono-atras` se niega fuera de Instagram: falla cerrado. Se cerró con `cmd statusbar collapse` y el reintento funcionó (`publicaciones_antes` 3714).
- `ig recorte` dejó el 4:5 completo (marco y firma visibles); `ig editor` y `ig audio` añadieron el tema sugerido («Feeling Good par Nina Simone»); `ig detalles` mostró la fila de música.
- **Fallo:** `ig pie` devolvió `ok` pero la captura mostraba el desplegable de hashtags sobre la música y «Partager»; aparece segundos después del volcado que lo comprueba. Un `telefono-atras` lo cerró sin tocar el pie. Sin arreglo, `ig compartir` fallaría cerrado en cada ventana (tarea 10e).
- Salida: dos «atrás» hasta «Recommencer ?», toque en «Recommencer», un «atrás» más hasta el perfil: sigue en 3714 publicaciones, no se publicó nada.

## Comprobación del refactor R en el teléfono (2026-09-15, sin publicar)

- Código del worktree `media-lab-fase2` en `f159243` (tareas 1-5: `pantalla`, `pasos`, `textos`, `recetas`, `lab.py receta`/`telefono-atras --app`/`telefono-descartar`), cerrojo `manual` tomado desde el árbol principal, run `SONDA-F2-R`, máster `LAB-SMOKE-001/lab-open-feed.jpg` y el pie de `LAB-PERSON-002/caption-instagram.txt`.
- **Primer `ig abrir` salió con 4** (`PantallaInesperada`: `uiautomator dump` sin respuesta en 5 s). Instagram estaba en un Reel reproduciéndose (abierto desde un mensaje directo): con vídeo en marcha el volcado no llega a reposo. `telefono.lanzar` (`monkey … LAUNCHER`) reanuda la pantalla donde se quedó la app, en la fase 1 igual que en el refactor, así que no es una regresión: una ventana desatendida habría fallado igual (cerrado). Tras `adb shell am force-stop com.instagram.android`, el reintento funcionó (`publicaciones_antes` 3718). Hecho en la rama `media-lab-fase2`: si ningún volcado de la espera inicial es legible (`pasos.SinVolcado`), `abrir` hace la captura `ig-00-antes-de-arranque-en-frio.png`, lee los focos de ventana (`mCurrentFocus` y `mFocusedApp`) y solo entonces fuerza el cierre de Instagram una sola vez (`telefono.forzar_cierre`), relanza en frío, vuelve a esperar y lo anota con `"arranque_en_frio": true` en su JSON. No fuerza nada si algún volcado se leyó (un borrador a medias incluido), si la captura previa falla, si algún foco está en `MediaCaptureActivity` (el flujo de creación: selector, editor y compositor; con el selector «Nouvelle publication» abierto el foco es esa actividad, comprobado el 2026-09-15) o si no se puede leer ningún foco. Todo error tras el cierre lleva el aviso «(tras un arranque en frío: am force-stop de com.instagram.android)».
- `ig recorte` dejó el 4:5 completo (de «LABORATORIO ABIERTO» a «LAB-SMOKE-001»); `ig editor` mostró el chip «Audio suggéré»; `ig audio` añadió «Life is Art par Morunas»; `ig detalles` mostró la fila de música y «Partager».
- `ig pie` (ahora `pasos.escribir_texto`) pegó el pie con tildes y hashtags y la captura mostraba el compositor sin teclado ni desplegable de hashtags: el fallo de la sonda del 2026-09-14 no se repite.
- **Aviso:** durante `ig pie` entró una notificación flotante de un mensaje directo de otra cuenta y tapaba la parte alta de la vista previa en `ig-04-compositor.png`. No afecta a los volcados, pero en una ventana real la QA visual podría dar FAIL por imagen tapada; conviene repetir la captura si hay una notificación flotante encima.
- Salida: dos `telefono-atras --app instagram` (compositor → editor → «Recommencer ?»), `telefono-descartar --app instagram` volvió al selector sin borrador y un `telefono-atras` más llevó al perfil de @sabiduriabolsillo: sigue en **3718 publicaciones**, no se publicó nada. Las capturas de `SONDA-F2-R` no se comitean.

## Arranque en frío: camino normal en el teléfono (2026-09-15, sin publicar)

- Código `52882f7` de `media-lab-fase2` en una copia limpia, cerrojo `manual`, run `SONDA-F2-FRIO`. `ig abrir` salió con 0, `arranque_en_frio: false` y `publicaciones_antes` 3718; `ig recorte` dejó el 4:5 completo; un `telefono-atras` desde el selector volvió al perfil sin diálogo.
- Con el selector abierto, `telefono.foco()` (hoy `telefono.focos()`) devolvió `com.instagram.android/instagram.features.creation.activity.MediaCaptureActivity`: la guardia del arranque en frío protege todo el flujo de creación.
- **Recuento del perfil desfasado:** al volver, el perfil decía **3719**. El laboratorio no publicó nada (nunca se tocó «Partager» y la miniatura de `LAB-SMOKE-001` no está en la cuadrícula). Producción había publicado `2026-09-14-extra88` en Instagram a las 05:33Z; el perfil que `ig abrir` leyó a las 06:43Z era el que Instagram tenía en memoria desde las 05:07Z. Consecuencia: `publicaciones_antes` puede quedarse corto si Instagram no recarga el perfil, y entonces `ig compartir` daría `conteo_no_cuadra` (código 5) aunque la publicación sea buena. Antes de atribuir un +1 del perfil al laboratorio, mirar las horas de `content/published/*.json`. Hecho en la rama `media-lab-fase2` (solo probado con el teléfono simulado): antes de leer `publicaciones_antes` (`ig abrir`) y `publicaciones_despues` (`ig compartir`), `instagram_feed._recuento_fresco` desliza una vez hacia abajo sobre el perfil para forzar la recarga (`telefono.deslizar`, `input swipe`, desde el punto medio entre el recuento y «Modifier le profil» y 600 px hacia abajo; no desliza si el inicio o el final caen sobre un control de envío o de borrado, si algo de otra app tapa el inicio o si una ventana emergente se solapa con él), espera 3 s y exige el mismo recuento en 3 volcados seguidos. `ig abrir` emite `recuento_refrescado`; si no se estabiliza, el recuento es `null`, va a `avisos` y `ig compartir` se llama con `--publicaciones-antes none` (sale `confirmado_sin_conteo`). Falta comprobar en el teléfono real:
  - que el gesto recarga de verdad el perfil y no toca nada de la cabecera;
  - si `swipe_refresh_animated_progressbar_container` (en reposo, `[441,249][638,446]`, con su fondo en `[0,249][1080,250]`) cambia de bounds o desaparece durante la recarga;
  - cuánto tarda en cambiar el recuento tras el gesto, y si con 3 s de espera no salen tres volcados seguidos con el recuento viejo.
