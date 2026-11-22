# Narrated Reels, Phase 2 (posting from the lab phone) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `lab.py narrado subir | abrir | pie | publicar | verificar | descartar` takes a built, reviewed narrated reel and posts it as an Instagram Reel from the lab phone, with its own audio, the AI label on and cross-posting off — and proves afterwards that exactly one post landed.

**Architecture:** A new module `labkit/narrado_movil.py` drives the route the probe of 2026-11-22 found (Créer → «Nouveau reel» gallery → editor → details), using the guarded step framework in `labkit/pasos.py` so every tap goes through the "never tap a control that publishes" check and every step is testable with the fake phone. From the site loop it reuses only `exigir_cuenta` (the account check), through a module-level reference that tests replace; the toggles and the share tap are its own, so they pass the guard and run under the fake phone. It does not modify `sitio_instagram.py`. State between steps lives in `build/movil.json`; the gate to share is recomputed from a fresh screen dump, never trusted from that file.

**Tech Stack:** Python 3 (repo `.venv`), adb, the existing `labkit` phone framework, `phone_clipboard.py` for accented text.

**Spec:** `docs/superpowers/specs/2026-11-19-reels-narrados-design.md` (section 5) and the probe notes `experiments/media-lab/narrados/sonda-movil-2026-11-22.md`. Read both. Phase 1 outcome and known gaps: `docs/superpowers/plans/2026-11-19-reels-narrados-fase-1.md`, section "Outcome".

**Scope:** Instagram Reel only. One reel per manual run, started by a person or an agent step by step. The schedule (phase 3), TikTok and Facebook are separate plans.

## Global Constraints

- Nothing is shared unless ALL hold, checked at the moment of the tap: `informe.json` has `ok: true` and `veredicto: "PASS"`; the MP4 on disk matches `sha256_mp4` and the script matches `sha256_guion`; the file on the phone has that same sha256; the active Instagram account is `sabiduriabolsillo`; on a fresh dump of the details screen the AI label is on, the Threads and Facebook cross-posts are off, «Essai» is off, and the caption field shows the caption.
- Share is tapped at most once per run. After the tap, no step may tap share again, whatever verification says.
- Every tap goes through `pasos.tocar` or `pasos.enviar`. No raw `telefono.tocar`, no `telefono.shell`/`adb` calls from `narrado_movil.py`: phone I/O that does not exist yet is added to `telefono.py` as named functions.
- The phone is never woken or unlocked. A locked or asleep screen stops the run (`pasos.exigir_listo`).
- UI strings are French and are the ones recorded by the probe: «Créer» (`action_bar_left_button`), «Nouveau reel» (`gallery_title_text`), gallery tile `gallery_grid_item_thumbnail` with description «… Miniature de la vidéo du <date> <heure>», «Suivant» (`clips_right_action_button`), caption `caption_input_text_view`, «Audio d’origine», «Ajouter une mention IA», «Essai», «Partager aussi sur…», «Partager» (`share_button`), «Enregistrer le brouillon ?» / «Recommencer». Each lives once in `labkit/textos.py`.
- Never use Android's share sheet with `video/mp4` (it only offers direct messages) nor `com.instagram.share.ADD_TO_REEL`.
- Remote folder `/sdcard/Movies/SabiduriaLab/`; remote name `<pieza>-<8 first hex of sha256>.mp4`. The file is deleted from the phone and from MediaStore when the run ends, whatever the outcome.
- Caption: the piece's hook, a blank line, its question, a blank line, its tags as hashtags, a blank line, `Voz sintética`. No URL. At most 2200 characters.
- Lock owner `narrado`, taken before `subir` and released after `verificar` or `descartar`. A run never starts while the lock is held by `sitio`.
- Code, identifiers, messages and docs in Spanish. Tests in the plain-script style, with `TelefonoSimulado` (`tests/test_media_lab.py:593-749`); no test touches adb.
- Do not modify `labkit/sitio_instagram.py`, `src/`, `.github/` or `content/`. Do not push. Stage explicit paths only (another process commits to this checkout).
- The first real post happens in Task 8, with the user's explicit go-ahead in the conversation. No earlier task taps share on a real phone.

## Review Focus

1. **Instagram is on another account when the run starts** (it has switched mid-cycle before). Expected: the run stops before the gallery opens, naming the active account. → Task 3.
2. **The first gallery tile is not our video** (the probe saw a foreign 0:28 video). Expected: the tile is chosen by upload minute and duration; if none or more than one matches, the run stops. → Task 3.
3. **A toggle cannot be confirmed** (AI label has no id; cross-posts default to on; the list scrolled). Expected: `publicar` refuses, naming which condition failed; nothing is tapped. → Tasks 4 and 5.
4. **Share was tapped but the post cannot be found** (slow upload, grid not refreshed). Expected: the run is recorded as `incierto`, the quote is NOT offered again by `elegir`, and nothing re-shares. → Task 6.
5. **The reel was rebuilt after its PASS**, or the file on the phone is not the reviewed one. Expected: `subir` and `publicar` refuse on the sha mismatch. → Tasks 2 and 5.

---

## File Structure

```
experiments/media-lab/
  labkit/telefono.py            + video upload, lookup and removal (MediaStore de vídeo)
  labkit/textos.py              + the Reel-composer strings above
  labkit/narrado_pie.py         caption builder (pure)
  labkit/narrado_movil.py       the six steps
  labkit/narrado.py             + estado movil.json, registrar on verify, elegibles reads «incierto»
  labkit/narrado_proyecto.py    first frame carries the whole hook
  lab.py                        narrado subir|abrir|pie|publicar|verificar|descartar; owner `narrado`
  narrados/README.md            how to run a post, what each refusal means
tests/fixtures/narrados/movil/  sanitised probe dumps
tests/test_narrado_movil.py
```

---

### Task 1: The cover frame

The Reel's cover is the first frame, which today reads only «NO ES DE».

**Files:**
- Modify: `experiments/media-lab/labkit/narrado_proyecto.py`
- Test: `tests/test_narrados.py` → extend `seccion_proyecto`

**Interfaces:**
- Produces: for the first scene of any type, every text element is visible at t=0 with no entrance animation; only non-text marks (the strike-through line, rules) animate in. Later scenes are unchanged.

- [ ] **Step 1: Failing tests:** in the generated script for the sample script, no `sube(`/`fromTo(` targets a text element of scene 0 (`#s0a`, `#s0b`); the strike line `#s0r` still animates; scene 1's elements still animate. Same assertion with a script whose first scene is `nombre_ano` and one whose first scene is `texto`.
- [ ] **Step 2: Run** `.venv/bin/python tests/test_narrados.py` — fails.
- [ ] **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Rebuild** `lab.py narrado construir --pieza 2026-08-23-tarde`; expected `ok: true`. Run `npx --yes hyperframes@0.9.70 snapshot --at 0` in `build/proyecto` and read the frame: label and «Viktor Frankl» both visible, no strike yet. The rebuild clears the verdict; do not record a new one (the user re-reviews in Task 8).
- [ ] **Step 6: Commit** `narrado: el primer fotograma lleva el gancho entero`.

---

### Task 2: Video on the phone

**Files:**
- Modify: `experiments/media-lab/labkit/telefono.py`, `experiments/media-lab/lab.py` (`DUENOS_VENTANA` gains `"narrado"`)
- Test: `tests/test_narrado_movil.py` (new; header and `check` as in `tests/test_atipicos.py`)

**Interfaces:**
- Produces in `telefono.py`:
  - `URI_VIDEOS = "content://media/external/video/media"`, `CARPETA_VIDEOS = "/sdcard/Movies/SabiduriaLab"`
  - `consulta_video(nombre: str) -> str` — the `content query` command (projection `_id:_display_name:duration:width:height`); rejects unsafe names like `consulta_mediastore`.
  - `fila_de_video(salida: str, nombre: str) -> dict | None` — pure: `{"id", "duracion_ms", "ancho", "alto"}` of the newest row with that exact name.
  - `subir_video(local: Path, nombre: str) -> dict` — push, scan, poll up to `ESPERA_MEDIASTORE_S`, compare sha256; returns `{"remoto", "sha256", "subido_en", "duracion_ms", "ancho", "alto"}`. Raises `TelefonoError` on a missing row, a sha mismatch, or dimensions other than 1080×1920.
  - `borrar_video(nombre: str) -> bool` — removes the file and its MediaStore row; `True` when neither remains. Never raises on "already gone".
  - `sha256_de_video(nombre: str) -> str | None` — the sha256 of the file on the phone, `None` when it is not there.
- `telefono.subir` and the image path are untouched.

- [ ] **Step 1: Failing tests** for the pure parts, using the real line the probe got:

```python
linea = "Row: 0 _id=1000023376, _display_name=narrado-sonda.mp4, duration=27533, width=1080, height=1920"
check(telefono.fila_de_video(linea, "narrado-sonda.mp4") == {"id": 1000023376, "duracion_ms": 27533, "ancho": 1080, "alto": 1920}, "fila de vídeo")
check(telefono.fila_de_video(linea, "otro.mp4") is None, "otro nombre no casa")
check(telefono.fila_de_video("No result found.", "narrado-sonda.mp4") is None, "sin filas")
check("video/media" in telefono.consulta_video("a-1b2c3d4e.mp4"), "consulta en el MediaStore de vídeo")
```

Plus: `consulta_video("a b.mp4")` and `consulta_video("x';rm.mp4")` raise `TelefonoError`; with two rows of the same name the higher `_id` wins.

- [ ] **Step 2: Run** `.venv/bin/python tests/test_narrado_movil.py` — fails. **Step 3: Implement.** **Step 4: Run** — passes; `.venv/bin/python tests/test_media_lab.py` still passes.
- [ ] **Step 5: Commit** `telefono: subir, encontrar y borrar un vídeo; dueño de cerrojo «narrado»`.

---

### Task 3: Caption, state and `subir` / `abrir`

**Files:**
- Create: `experiments/media-lab/labkit/narrado_pie.py`, `experiments/media-lab/labkit/narrado_movil.py`, `tests/fixtures/narrados/movil/`
- Modify: `experiments/media-lab/labkit/textos.py`, `experiments/media-lab/labkit/narrado.py`
- Test: `tests/test_narrado_movil.py`

**Interfaces:**
- Consumes: `telefono.subir_video`, `pasos.exigir_listo`, `pasos.esperar_que`, `pasos.tocar`, `sitio_instagram.exigir_cuenta(cuenta)`, `instagram_pantallas.fecha_miniatura` / `miniatura_coincide(desc, subido_en)`, `instagram_pantallas.publicaciones_de_perfil(xml)`.
- Produces:
  - `narrado_pie.pie(pieza: dict) -> str` — pure; the caption per Global Constraints. Raises `ValueError` over 2200 characters or when the piece has no question.
  - `narrado.estado_movil(pieza_id, raiz=None) -> dict` and `narrado.guardar_estado_movil(pieza_id, estado, raiz=None)` — read/write `build/movil.json` atomically. Keys used: `nombre_remoto`, `sha256`, `subido_en`, `publicaciones_antes`, `pie_sha256`, `paso` (`subido|abierto|listo|compartido|verificado|incierto|descartado`), `compartido_en`.
  - `narrado.apto_para_publicar(pieza_id, raiz=None) -> list[str]` — pure on disk: problems with `informe.json` (`ok`, `veredicto`), `sha256_mp4`, `sha256_guion`. Empty when the reel may be posted.
  - `narrado_movil.subir(pieza_id, ev: Path) -> dict` — refuses when `apto_para_publicar` is not empty; uploads; stores state `subido`.
  - `narrado_movil.abrir(pieza_id, ev: Path) -> dict` — `exigir_listo`; `exigir_cuenta("sabiduriabolsillo")`; reads and stores `publicaciones_antes` from the profile; taps «Créer»; waits for «Nouveau reel»; picks the tile; waits for the editor (`clips_right_action_button`); taps «Suivant»; waits for the details screen (`caption_input_text_view` and title «Nouveau reel»); stores state `abierto`.
  - `narrado_movil.elegir_miniatura(xml: str, subido_en: str, duracion_ms: int) -> dict` — pure: the single `gallery_grid_item_thumbnail` whose description is a video dated within one minute of `subido_en` (phone local time) and whose duration label equals the rounded duration (`0:28`). Raises `PantallaInesperada` when zero or more than one tile matches.
- Fixtures: copy `03-crear.xml`, `04-editor.xml`, `05-detalles.xml`, `06-detalles-abajo.xml`, `07-mencion-ia.xml`, `09-atras-2.xml` from `experiments/media-lab/evidence/android/SONDA-NARRADO-20261122/` into `tests/fixtures/narrados/movil/`. Before committing, replace the three location-suggestion texts in 05–07 with `Lugar A`, `Lugar B`, `Lugar C` (they reveal where the phone has been) and confirm no other account's handle is in any of the six files.

- [ ] **Step 1: Failing tests:**

```python
p = narrado_pie.pie(pieza_ok)
check(p.splitlines()[0] == pieza_ok["core"]["hook"].splitlines()[0], "abre con el gancho de la pieza")
check(p.rstrip().endswith("Voz sintética"), "cierra con «Voz sintética»")
check("http" not in p and "#SabiduriaDeBolsillo" in p and len(p) <= 2200, "sin URL, con hashtags, dentro del límite")
m = nm.elegir_miniatura(fixture("03-crear.xml"), "2026-11-22T13:30:40+00:00", 27533)
check("22 novembre 2026 14:30" in m["desc"], "elige la miniatura por la hora de subida")
check(lanza(PantallaInesperada, nm.elegir_miniatura, fixture("03-crear.xml"), "2026-11-22T10:00:00+00:00", 27533), "sin miniatura de esa hora, se para")
check(lanza(PantallaInesperada, nm.elegir_miniatura, dos_iguales, "2026-11-22T13:30:40+00:00", 27533), "dos que casan, se para")
```

Plus: `apto_para_publicar` reports each of — no `informe.json`, `ok: false`, `veredicto` null, MP4 changed by one byte, script changed — and returns `[]` for a clean build; `subir` with a non-empty `apto_para_publicar` uploads nothing (the fake's `subir_video` records zero calls); `abrir` with the fake phone on another account (`perfil_propio` false) raises before any tap on «Créer»; `abrir` on the happy path taps, in order, «Créer», the chosen tile, «Suivant», and ends in state `abierto` with `publicaciones_antes` set.

- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Commit** `narrado: pie, estado del móvil y pasos subir y abrir`.

---

### Task 4: `pie` — caption, AI label, cross-posts

**Files:**
- Modify: `experiments/media-lab/labkit/narrado_movil.py`
- Test: `tests/test_narrado_movil.py`

**Interfaces:**
- Consumes: `pasos.escribir_texto(texto, paquete, *, campo, exigir, ...)`, `pasos.tocar`. Not `sitio_instagram.ajustar_cruces`: it taps without the guard and calls `telefono.shell`, which the fake phone forbids.
- Produces:
  - `narrado_movil.interruptor_de_fila(xml: str, titulo: str) -> dict | None` — pure: the `checkable` node whose vertical span overlaps the row of the node whose text equals `titulo` and that sits to its right. Works for the id-less `android.view.View` of «Ajouter une mention IA» and for the `Switch` described «Essai».
  - `narrado_movil.detalles_listos(xml: str, pie: str) -> list[str]` — pure: what is NOT yet right on the details screen: AI label off or not found; Threads on; Facebook on; «Essai» on; caption field not showing the caption's first line; «Audio d’origine» absent. Rows not on screen count as not found.
  - `narrado_movil.poner_pie(pieza_id, ev: Path) -> dict` — types the caption; closes the keyboard and any hashtag dropdown with back while the details screen stays in front; scrolls the list; turns the AI label on if off; turns «Essai» off if on; turns off the Threads row (title `sabiduriabolsillo`, subtitle «Threads · Public») and the Facebook row (title `Sabiduria De Bolsillo`, subtitle «Facebook · Public») with `interruptor_de_fila` and `pasos.tocar`; then requires `detalles_listos` to be empty on a fresh dump (scrolling as needed to bring each row on screen, never into the bottom bar); stores state `listo` with `pie_sha256`.

- [ ] **Step 1: Failing tests** on the fixtures:

```python
ia = nm.interruptor_de_fila(fixture("06-detalles-abajo.xml"), "Ajouter une mention IA")
check(ia["bounds"] == (889, 971, 1035, 1106) and ia["checked"] is False, "interruptor de la mención IA, apagado")
check(nm.interruptor_de_fila(fixture("07-mencion-ia.xml"), "Ajouter une mention IA")["checked"] is True, "encendido tras el toque")
faltan = nm.detalles_listos(fixture("06-detalles-abajo.xml"), pie)
check(any("IA" in f for f in faltan) and any("Threads" in f for f in faltan) and any("Facebook" in f for f in faltan), "la sonda: IA apagada y los dos cruces encendidos")
check(any("IA" in f for f in nm.detalles_listos(fixture("05-detalles.xml"), pie)), "fila fuera de pantalla = no confirmada")
```

Plus, with the fake phone: `poner_pie` never taps a node inside the bounds of `share_button` or `save_draft_button` (assert on the fake's tap log); when the AI toggle stays off after the tap it raises and state stays `abierto`; on the happy path the fake's final screen yields `detalles_listos == []` and state is `listo`.

- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Commit** `narrado: paso pie con mención IA, cruces apagados y comprobación de la pantalla`.

---

### Task 5: `publicar` and `descartar`

**Files:**
- Modify: `experiments/media-lab/labkit/narrado_movil.py`, `experiments/media-lab/labkit/textos.py` (the discard sheet «Enregistrer le brouillon ?» → «Recommencer», if `textos.DESCARTE` lacks it)
- Test: `tests/test_narrado_movil.py`

**Interfaces:**
- Consumes: `narrado.apto_para_publicar`, `detalles_listos`, `pasos.enviar(...)` (the only one-tap share), `pasos.descartar`, `telefono.borrar_video`, `telefono.sha256_de_video`.
- Produces:
  - `narrado_movil.publicar(pieza_id, ev: Path) -> dict` — in order: state must be `listo`; `apto_para_publicar` empty; the phone file's sha256 equals `sha256_mp4`; `exigir_listo`; fresh dump: `detalles_listos` empty and exactly one `share_button`; write state `compartido` with `compartido_en` BEFORE the tap; one `pasos.enviar`; then, for up to 30 s, answer the original-audio prompt with «Désactiver et partager» if it appears. Any refusal raises `NoPublicar(motivos: list[str])` with nothing tapped.
  - `narrado_movil.descartar(pieza_id, ev: Path) -> dict` — refuses when state is `compartido`, `verificado` or `incierto`; otherwise backs out through «Recommencer», deletes the video from the phone, state `descartado`.
- A second call to `publicar` in state `compartido` or later raises `NoPublicar(["ya se compartió"])`.

- [ ] **Step 1: Failing tests** with the fake phone: each precondition failing alone (state `abierto`; verdict missing; MP4 changed on disk; phone sha different; AI off on the fresh dump; Facebook on; two `share_button` nodes; screen locked) raises `NoPublicar`/`PantallaInesperada` and the fake's tap log is empty; the happy path taps `share_button` exactly once and leaves state `compartido`; calling `publicar` again taps nothing; if the tap itself raises, state is still `compartido` (never back to `listo`); `descartar` in state `listo` ends on the home screen with the video removed, and in state `compartido` refuses.
- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Commit** `narrado: publicar una sola vez con todas las condiciones a la vista, y descartar`.

---

### Task 6: `verificar` and the registry

**Files:**
- Modify: `experiments/media-lab/labkit/narrado_movil.py`, `experiments/media-lab/labkit/narrado.py`
- Test: `tests/test_narrado_movil.py`, `tests/test_narrados.py` (`seccion_candidatas`)

**Interfaces:**
- Produces:
  - `narrado_movil.verificar(pieza_id, ev: Path) -> dict` — state must be `compartido`. Opens the brand profile (`exigir_cuenta`), waits while an upload banner («Partage sur…») is present, refreshes, reads the post count. `encontrada` is true only when the count is `publicaciones_antes + 1` AND the newest Reel tile, opened, shows the caption's first line. Result: state `verificado` or, after 3 minutes without both, `incierto`. In both cases: `narrado.registrar({"pieza", "cita", "run", "construido_en", "publicado_en", "estado", "sha256_mp4"})`, delete the video from the phone, return `{"encontrada", "publicaciones_antes", "publicaciones_despues", "estado"}`.
  - `narrado.elegibles` already drops quotes present in the registry; an entry with `estado: "incierto"` drops it too (assert it).
- `verificar` never taps share, a draft, or anything in `textos.NO_TOCAR`.

- [ ] **Step 1: Failing tests** with the fake phone: count +1 and caption visible → `verificado`, one registry line, video deleted; count unchanged for the whole wait → `incierto`, one registry line with `estado: "incierto"`, video deleted, no tap on `share_button`; count +2 → `incierto` with a problem text saying two posts appeared; state `listo` → refuses. In `seccion_candidatas`: a registry line with `estado: "incierto"` removes that quote from `elegibles`.
- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Commit** `narrado: verificar por recuento y pie, y registro de lo publicado`.

---

### Task 7: `lab.py` wiring and the runbook

**Files:**
- Modify: `experiments/media-lab/lab.py` (`cmd_narrado` and its parser), `experiments/media-lab/narrados/README.md`
- Test: `tests/test_narrado_movil.py`

**Interfaces:**
- Produces: `lab.py narrado subir|abrir|pie|publicar|verificar|descartar --pieza ID`, each through `_paso_telefono(ev, nombre, fn)` with evidence in `evidence/android/NARRADO-<pieza>/`, JSON on stdout, exit 0 on success, 4 on `PantallaInesperada`, 2 on a refusal (`NoPublicar`, `ValueError`). Every phone step requires the lock to be held by `narrado` and refuses otherwise.
- README gains the runbook, in this order, one command per line and no compound shell commands: `lock-tomar --dueno narrado`, `narrado subir`, `narrado abrir`, `narrado pie`, `narrado publicar`, `narrado verificar`, `lock-soltar --dueno narrado`; then what to do for each refusal (which are safe to retry: everything before `publicar`; never `publicar` after state `compartido`), and that `descartar` is the way out of any step before `publicar`.

- [ ] **Step 1: Failing tests:** each sub-step without the lock, or with the lock held by `sitio`, exits 2 and calls no phone function; `publicar` maps `NoPublicar` to exit 2 and prints the reasons; the parser rejects an unknown step.
- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** all five suites (`test_atipicos`, `test_narrado_ritmo`, `test_narrados`, `test_narrado_movil`, `test_media_lab`) — no `✗`.
- [ ] **Step 5: Commit** `narrado: pasos del móvil en lab.py y guía de uso`.

---

### Task 8: Dress rehearsal on the phone, then the first real post

This task is run by the controller with the user, not by a subagent. It touches the real phone.

- [ ] **Step 1: Rehearsal without posting.** Take the lock. Run `subir`, `abrir`, `pie` for `2026-08-23-tarde` (the verdict must be recorded first: the user re-reviews the rebuilt video from Task 1). Read the evidence screenshots: caption with accents intact, AI label on, both cross-posts off, «Essai» off. Then run `descartar`. Expected: post count unchanged, «Brouillons» count unchanged, video gone from the phone. Fix anything the real phone shows that the fixtures did not, in code and fixtures, and repeat until one rehearsal is clean end to end.
- [ ] **Step 2: Ask the user** for an explicit go-ahead to post, showing them the caption text and the evidence screenshot of the details screen. Without a yes in the conversation, stop here.
- [ ] **Step 3: First real post.** `subir`, `abrir`, `pie`, `publicar`, `verificar`. Save the dumps of every screen Instagram shows after the tap as new fixtures (sanitised) and add tests for any prompt the code had to handle. Expected: `verificado`, count +1, one registry line.
- [ ] **Step 4: Look at the published Reel** on the profile with the user: cover, caption, the AI label as viewers see it, and that it was not cross-posted to Threads or Facebook (the site loop's memory says Instagram can cross-post without saying so).
- [ ] **Step 5: Commit** the registry line and any fixtures; write the outcome at the end of this plan.

## Decisions taken in this plan (the user may change them)

- «Essai» (trial Reel shown to non-followers first) stays off. It fits the goal of reaching non-followers but changes how the post behaves, so it is a decision for the user after the first normal post.
- The cover is fixed in the video (Task 1), not chosen in Instagram's cover editor.
- No music is added; the Reel keeps «Audio d’origine».
- One reel per run, started by hand. Scheduling is phase 3.

## Not in this plan

- Phase 3 schedule, TikTok, Facebook.
- The phase 1 gaps listed in that plan's "Outcome", except the registry call (Task 6).
- `lab.py sitio descartar` raises a KeyError for feed, reel and story today (`lab.py:1178-1187`); it belongs to the site loop.

---

## Outcome of tasks 1–7 (2026-11-22)

Built on main, in the commits titled `narrado:` / `telefono:` after the plan commit. `tests/test_narrado_movil.py` 542 checks, `tests/test_narrados.py` 313, `tests/test_media_lab.py` 1 214, all passing. Everything was tested against a fake phone and sanitised dumps from the 2026-11-22 probe; nothing has run on the real phone yet. Task 8 (rehearsal, then the first real post) is still to do, with the user.

Changes from this plan, decided during execution:

- The share is recorded in the committed registry `narrados/registro.jsonl` (and the state file) before the tap, durably, under a non-blocking `flock` on `narrados/.registro.lock`. `subir`, `publicar` and a rebuild refuse once the quote or the piece is in the registry. The registry protects only once it is committed; the runbook says to commit it between `publicar` and `verificar`.
- `verificar` never calls `exigir_cuenta` (its recovery force-closes Instagram). It reaches the profile by tapping the profile tab and checks the account from the dump.
- `publicar` proves the brand account from the Threads row title on the fresh details screen, at the moment of the tap.
- The video is deleted only after a confirmed `verificado` with no upload banner seen; every `incierto` keeps it. `limpiar` removes it, and refuses until 15 minutes after the share.
- `verificar` confirms the +1 with one more refresh, and stops at 360 s as `incierto`.
- A `contraste` scene cannot open a reel (the cover would hide its second line).
- After the share the step closes the WhatsApp status sheet with «Plus tard», as the site loop does.
- Exit code 3 means "finished, a person must look"; 1 means an unexpected error (check the state before doing anything).
- After an `incierto` the quote stays blocked until the user deletes its registry lines by hand; the code never does.

Known gaps, deferred:

- `narrado_movil.py` (about 1 600 lines) and `tests/test_narrado_movil.py` (about 2 600) should be split by step before more is added; four overlapping "already shared" tuples, three "details screen" predicates and three ways of reading the active account should be unified.
- `verificar` matches only the caption's first line; the confirmation round does not re-check the newest tile; the opening cap keys on a tile description that ignores row and column; a banner seen only in an earlier round still allows deleting after a clean `verificado`; the banner flag is module-level state.
- `elegibles` matches on quote text only, so a shared piece whose quote was edited is offered by `elegir` and then refused by `subir`.
- `F_FULLFSYNC` is not used on macOS; one malformed registry line blocks every quote (safe direction); multi-word tags are merged into one hashtag.
- The text of the «recuperado del registro» problem does not mention the 15-minute wait of `limpiar`; the runbook's code block ends with an unconditional `lock-soltar` while the prose says to keep the lock after an exit 3.

To settle on the phone, most likely to stop the first rehearsal first: what a playing Reel dumps like and which node holds its caption (a cut or prefixed caption makes every `verificar` `incierto`); what Instagram shows after «Partager» (audio notice, WhatsApp sheet, upload banner); whether the caption field equals the typed caption exactly; whether the AI-label switch opens a confirmation sheet; where «atrás» from the details screen goes; whether the Threads row (needed for the account check and for turning the cross-post off) is always present; pinned posts at the top of the grid; whether the gallery tile's duration is rounded or cut; whether the Facebook row scrolls fully into view; and real `verificar` wall time against the 600 s tool timeout.
