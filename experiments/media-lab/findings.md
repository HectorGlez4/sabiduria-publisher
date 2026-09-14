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
