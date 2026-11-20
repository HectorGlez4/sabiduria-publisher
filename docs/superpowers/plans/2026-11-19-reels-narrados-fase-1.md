# Narrated Reels, Phase 1 (builder on the Mac) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `lab.py narrado elegir | construir | revisar` turns a verified published piece plus a hand- or agent-written `guion.json` into a checked 25–40 s narrated MP4 on the Mac. Nothing is posted.

**Architecture:** Small pure modules in `experiments/media-lab/labkit/` (script validation, pronunciation, timeline, HTML generation, transcript comparison) with thin wrappers around three external tools: Kokoro for the voice, HyperFrames for render/check/transcribe, ffmpeg for the mix and measurements. The voice files define the timeline; the HTML is generated from the script and the timeline.

**Tech Stack:** Python 3 (repo `.venv`), `npx hyperframes@0.9.70`, Kokoro via a separate Python 3.12 environment, ffmpeg/ffprobe, GSAP 3.15.0 (vendored).

**Spec:** `docs/superpowers/specs/2026-11-19-reels-narrados-design.md`. Read it first. Working reference: `experiments/media-lab/results/spike-hyperframes/index.html`.

**Scope:** Phase 1 of the spec only. Phase 2 (posting from the phone) gets its own plan after a phone probe, because uploading a video and opening the Reel composer on it have no code or fixtures yet. Phase 3 (schedule) follows phase 2.

## Global Constraints

- Duration of the finished reel: 25–40 s. Canvas 1080×1920, 30 fps, H.264 + AAC.
- Safe zone: all text within y 240–1500; zero HyperFrames safe-zone or type-size warnings, zero errors.
- Loudness −16 LUFS, true peak −1.5 dB. No silence longer than 1.2 s inside the narration.
- Gap between sentences 0.45 s; 0.7 s before a `cita` scene and before `pregunta`; 0.6 s lead-in.
- Voice: Kokoro `em_santa`, language `es`, speed 0.95. `say -v Paulina -r 165` exists only as a test/fallback engine.
- Scene types, closed list: `tachado`, `cita`, `nombre_ano`, `contraste`, `pregunta`. `cita` and `pregunta` are required; `pregunta` is last; `tachado` only when the piece is in the misattribution list. 5–7 scenes.
- The end card shows "Sabiduría de Bolsillo" and "Voz sintética" (text ≥ 28 px).
- The narration states nothing the piece does not state. On-screen text is never altered by pronunciation rules.
- HyperFrames pinned to `0.9.70`, invoked as `npx --yes hyperframes@0.9.70`, with `DO_NOT_TRACK=1` and `HYPERFRAMES_SKIP_SKILLS=1` in the environment. No network at render: fonts and GSAP are local files.
- Motion: fades, rises of at most 40 px, one background change. Nothing else.
- Code, identifiers, messages and docs in this area are in Spanish, like the rest of `labkit`. Tests follow `tests/test_media_lab.py`: plain script, `check(cond, label)`, sections, run with `.venv/bin/python`.
- Do not touch `src/`, `.github/`, the phone, or the `sitio` loop. Do not push.
- Media and build output stay out of git; scripts, pronunciation table, candidate list and registry are committed.

## Review Focus

1. **A long quote.** A 140-character quote in `cita` must either fit (smaller type, never below 56 px) or stop `construir` with a message naming the scene; it must never render outside the safe zone. → Task 4.
2. **A sentence the voice returns empty or cut.** A voice file shorter than 0.3 s, or missing, stops the run naming the sentence; it is never mixed in. → Task 3.
3. **The recogniser splits words differently** ("porqué" / "por qué", "1888" / "mil ochocientos…", commas, capitals, accents). The round trip must pass on these and still fail on a dropped or added word. → Task 5.
4. **A malformed script** (unknown `tipo`, missing `cita`, `pregunta` not last, 4 or 8 scenes, empty `voz`). `construir` lists every problem at once and builds nothing. → Task 1.
5. **Re-running a run that died halfway.** `construir --run R` twice gives the same result; stale files from the first attempt never reach the MP4. → Task 7.

---

## File Structure

```
experiments/media-lab/
  labkit/narrado_guion.py        script schema + validator (pure)
  labkit/narrado_pronuncia.py    numbers to words, name table, approval gate (pure)
  labkit/narrado_voz.py          voice engines, per-sentence synthesis, timeline, mix
  labkit/narrado_proyecto.py     guion + timeline -> HyperFrames project (pure string building + file copy)
  labkit/narrado_chequeos.py     hyperframes check, audio measures, transcript round trip
  labkit/narrado.py              candidates, run folders, registry, orchestration
  narrados/README.md             setup commands, how to run, what each file is
  narrados/candidatas.json       ids of misattribution pieces (committed)
  narrados/pronunciacion.json    name table with approvals (committed)
  narrados/plantilla/gsap.min.js vendored GSAP 3.15.0
  narrados/plantilla/disenos.json  papel / tinta / siena colour values
  narrados/<id>/guion.json       the script (committed)
  narrados/<id>/build/           voice files, project, MP4, reports (ignored)
tests/test_narrados.py
```

`.gitignore` gains `experiments/media-lab/narrados/*/build/` and `experiments/media-lab/.venv-voz/`.

---

### Task 1: Script schema and validator

**Files:**
- Create: `experiments/media-lab/labkit/narrado_guion.py`
- Test: `tests/test_narrados.py` (new; copy the header, `check` and section runner from `tests/test_media_lab.py`)

**Interfaces:**
- Produces:
  - `TIPOS = ("tachado", "cita", "nombre_ano", "contraste", "pregunta")`
  - `validar(guion: dict, pieza: dict, es_falsa_atribucion: bool) -> list[str]` — every problem found, empty when valid.
  - `cargar(ruta: Path) -> dict` — reads `guion.json`, raises `ValueError` with the path on bad JSON.
- Script shape: `{"pieza": "<id>", "diseno": "papel|tinta|siena", "escenas": [{"tipo": ..., "voz": "...", "pantalla": {...}}]}`. `pantalla` per type:
  - `tachado`: `{"etiqueta", "nombre"}`
  - `cita`: `{"texto"}`
  - `nombre_ano`: `{"etiqueta", "nombre", "ano", "nota"}` (`nota` optional)
  - `contraste`: `{"claro", "oscuro"}`
  - `pregunta`: `{"texto"}`
- Years are written as digits in `voz` ("en 1888"); Task 2 expands them for the voice.

- [ ] **Step 1: Write the failing tests** in `seccion_guion()`, using `content/published/2026-11-10-re55-reel.json` as `pieza` and a valid six-scene script equivalent to the spike:

```python
check(validar(guion_ok, pieza, True) == [], "el guion del spike es válido")
check(any("tipo" in p for p in validar(con_tipo("baile"), pieza, True)), "tipo desconocido")
check(any("cita" in p for p in validar(sin("cita"), pieza, True)), "falta la escena cita")
check(any("última" in p for p in validar(pregunta_en_medio, pieza, True)), "pregunta no es la última")
check(len(validar(cuatro_escenas, pieza, True)) >= 1 and len(validar(ocho_escenas, pieza, True)) >= 1, "5 a 7 escenas")
check(any("1889" in p for p in validar(con_voz("La escribió en 1889."), pieza, True)), "año que la pieza no contiene")
check(any("Goethe" in p for p in validar(con_voz("Lo dijo Goethe."), pieza, True)), "nombre que la pieza no contiene")
check(any("cita" in p for p in validar(cita_cambiada, pieza, True)), "la cita difiere de core.quote.text")
check(any("tachado" in p for p in validar(guion_ok, pieza, False)), "tachado solo en falsas atribuciones")
check(len(validar(tres_fallos_a_la_vez, pieza, True)) >= 3, "devuelve todos los problemas, no el primero")
check(any("vacía" in p for p in validar(con_voz(""), pieza, True)), "voz vacía")
```

Also one check that a term listed in the piece's `do_not_use` appearing in any `voz` is reported.

- [ ] **Step 2: Run** `.venv/bin/python tests/test_narrados.py` — expected: fails on import.
- [ ] **Step 3: Implement `validar` and `cargar`.** "The piece contains it" means: the digits of every 3–4 digit number, and every capitalised word that is not sentence-initial, appear in the concatenation of `core.hook`, `core.body`, `core.question`, `core.quote.text`, `core.quote.author`. The quote comparison ignores surrounding quotation marks and whitespace only.
- [ ] **Step 4: Run** — expected: all `✓`.
- [ ] **Step 5: Commit** `narrado: esquema y validador del guion`.

---

### Task 2: Pronunciation and the approval gate

**Files:**
- Create: `experiments/media-lab/labkit/narrado_pronuncia.py`, `experiments/media-lab/narrados/pronunciacion.json`
- Test: `tests/test_narrados.py` → `seccion_pronuncia()`

**Interfaces:**
- Produces:
  - `numero_en_palabras(n: int) -> str` for 0–2999.
  - `nombres(voz: str) -> list[str]` — capitalised words that are not sentence-initial, plus sentence-initial ones present in the table.
  - `pendientes(guion: dict, tabla: dict) -> list[str]` — names with no approved entry, sorted, unique.
  - `para_la_voz(voz: str, tabla: dict) -> str` — digits expanded, names replaced by `dicho`.
- Table shape: `{"Nietzsche": {"dicho": "Niche", "aprobado_por": "", "fecha": ""}}`. An entry counts as approved only when `aprobado_por` is non-empty. `dicho` equal to the written name is valid (approved as is).
- Seed the table with `Nietzsche`, `Friedrich`, `Viktor`, `Frankl`, all unapproved: approval is the user's step.
- Deviation from the spec's wording, to confirm with the user at hand-off: years do not need a table entry, because `numero_en_palabras` is deterministic and tested.

- [ ] **Step 1: Failing tests:**

```python
check(numero_en_palabras(1888) == "mil ochocientos ochenta y ocho", "1888")
check(numero_en_palabras(1946) == "mil novecientos cuarenta y seis", "1946")
check(numero_en_palabras(2001) == "dos mil uno" and numero_en_palabras(1500) == "mil quinientos", "2001, 1500")
check(numero_en_palabras(21) == "veintiuno" and numero_en_palabras(100) == "cien", "21, 100")
check(pendientes(guion_ok, {}) == ["Frankl", "Friedrich", "Nietzsche", "Viktor"], "sin tabla, todos pendientes")
check(pendientes(guion_ok, tabla_sin_aprobar) != [], "una entrada sin aprobado_por no cuenta")
check(pendientes(guion_ok, tabla_aprobada) == [], "aprobada, nada pendiente")
check(para_la_voz("La escribió Nietzsche en 1888.", tabla_aprobada)
      == "La escribió Niche en mil ochocientos ochenta y ocho.", "reescribe solo para la voz")
```

- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Commit** `narrado: pronunciación y aprobación de nombres`.

---

### Task 3: Voice, timeline and mix

**Files:**
- Create: `experiments/media-lab/labkit/narrado_voz.py`, `experiments/media-lab/narrados/README.md`
- Modify: `.gitignore`
- Test: `tests/test_narrados.py` → `seccion_voz()`

**Interfaces:**
- Consumes: `para_la_voz` (Task 2).
- Produces:
  - `sintetizar(frase: str, salida: Path, motor: str = "kokoro") -> float` — writes a 48 kHz mono WAV trimmed of leading/trailing silence, returns its duration. Raises `VozFallida(frase, motivo)` when the file is missing or shorter than 0.3 s.
  - `linea_de_tiempo(tipos: list[str], duraciones: list[float]) -> list[dict]` — pure; each item `{"inicio", "fin", "escena_desde", "escena_hasta"}`; total is `fin` of the last + 2.3 s tail.
  - `mezclar(wavs: list[Path], inicios: list[float], total: float, salida: Path) -> None` — ffmpeg `adelay` + `amix=normalize=0` + `apad` + `loudnorm=I=-16:TP=-1.5`.
- Engines: `kokoro` runs `npx --yes hyperframes@0.9.70 tts <txt> -o <wav> -v em_santa -l es --speed 0.95 --json` with `HYPERFRAMES_PYTHON` pointing at `experiments/media-lab/.venv-voz/bin/python`; `say` runs `say -v Paulina -r 165`. Both then pass through the ffmpeg silence trim used in the spike.
- Scene boundaries: a scene starts 0.2 s before its sentence and ends where the next begins.
- README documents setup, verbatim: `uv venv --python 3.12 experiments/media-lab/.venv-voz`, then `uv pip install --python experiments/media-lab/.venv-voz/bin/python kokoro-onnx soundfile`, then `npx --yes hyperframes@0.9.70 telemetry disable`. Note that Python 3.14 fails with a missing `phontab` error.

- [ ] **Step 1: Failing tests** (pure part, no audio tools):

```python
t = linea_de_tiempo(["tachado", "cita", "nombre_ano", "nombre_ano", "contraste", "pregunta"],
                    [2.217, 3.872, 5.223, 6.24, 4.111, 1.207])
check([round(x["inicio"], 2) for x in t] == [0.6, 3.52, 7.84, 13.51, 20.2, 25.01], "inicios con huecos 0,45 y 0,7")
check(round(t[-1]["fin"] + 2.3, 2) == 28.52, "duración total con cola")
check(t[1]["escena_desde"] == round(t[1]["inicio"] - 0.2, 2), "la escena entra 0,2 s antes")
```

Plus, guarded by `shutil.which("say")`: `sintetizar("Hola.", tmp, motor="say") > 0.3`; and with a stub engine that writes a 0.1 s file, `VozFallida` is raised and names the sentence.

- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Manual verification.** Follow the README setup, then synthesise "Esta frase no es de Viktor Frankl." with `kokoro`. Expected: a WAV between 1.5 and 3.5 s.
- [ ] **Step 6: Commit** `narrado: voz por frases, línea de tiempo y mezcla`.

---

### Task 4: Project generator

**Files:**
- Create: `experiments/media-lab/labkit/narrado_proyecto.py`, `experiments/media-lab/narrados/plantilla/gsap.min.js` (GSAP 3.15.0, copied from the npm package `gsap@3.15.0`, file `dist/gsap.min.js`), `experiments/media-lab/narrados/plantilla/disenos.json`
- Test: `tests/test_narrados.py` → `seccion_proyecto()`

**Interfaces:**
- Consumes: script shape (Task 1), timeline items (Task 3).
- Produces:
  - `html(guion: dict, tiempos: list[dict], total: float, palabras: list[float] | None) -> str` — pure. `palabras` are start times for each word of the quote; `None` spaces them evenly across the sentence.
  - `escribir(destino: Path, guion: dict, tiempos: list[dict], total: float, palabras, voz: Path) -> Path` — writes `index.html`, `hyperframes.json`, `meta.json`, copies fonts from `assets/fonts/`, GSAP and the voice into `destino/assets/`; returns `destino`.
  - `tamano_cita(texto: str) -> int` — 84 px up to 70 characters, stepping down to a floor of 56 px; raises `NoCabe("cita", n_caracteres)` past 200 characters.
- Markup, CSS and easing follow the spike's `index.html`, with these fixed differences: GSAP and fonts load from `assets/`; box `left: 90px; right: 170px; top: 250px; height: 1080px`; the first scene's label is visible at t=0 with no entrance; signature at top 1290 px, "Voz sintética" at 1345 px and 28 px.
- `disenos.json` holds `papel` and `tinta` from the spike (`#f7f1e4`, `#eee4d0`, `#2c261c`, `#bf9b4e`, `#96722d`). Take `siena` from the site repository at `~/dev/sitio-sdb` (search its stylesheet for the Siena card colours). If that repository is not readable, leave `siena` out and make the validator reject it; say so in the task report.

- [ ] **Step 1: Failing tests:**

```python
h = html(guion_ok, tiempos_ok, 28.52, None)
check('data-duration="28.52"' in h and 'data-width="1080"' in h, "raíz con duración y tamaño")
check(h.count("<section") == 6, "una sección por escena")
check("cdn.jsdelivr" not in h and "http" not in h.split("<body")[0], "sin red: gsap y fuentes locales")
check("Voz sintética" in h and "Sabiduría de Bolsillo" in h, "firma y aviso")
check(h.count('class="p"') == 10, "la cita va palabra a palabra")
check("Niche" not in h, "la pantalla no lleva la pronunciación")
check('window.__timelines["main"]' in h, "línea de tiempo registrada")
check(tamano_cita("x" * 60) == 84 and tamano_cita("x" * 140) >= 56, "la cita larga encoge sin bajar de 56")
```

And `NoCabe` for 201 characters; and escaping: a `pantalla` text containing `<` and `&` appears escaped.

- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Commit** `narrado: generador del proyecto HyperFrames`.

---

### Task 5: Checks

**Files:**
- Create: `experiments/media-lab/labkit/narrado_chequeos.py`
- Test: `tests/test_narrados.py` → `seccion_chequeos()`

**Interfaces:**
- Produces:
  - `comparar(guion_voz: list[str], transcrito: str) -> str | None` — pure. `None` when equal; otherwise a message with about five words of context around the first divergence. Normalisation on both sides: digits to words (`numero_en_palabras`), lower case, accents folded, everything but letters removed (spaces too).
  - `silencios(mp4: Path) -> list[tuple[float, float]]` and `medidas(mp4: Path) -> dict` (`duracion`, `lufs`, `pico`) via ffmpeg `silencedetect=noise=-40dB:d=0.3` and `loudnorm=print_format=json`.
  - `audio_ok(mp4: Path, fin_narracion: float) -> list[str]` — problems: duration outside 25–40; any silence > 1.2 s that ends before `fin_narracion`; LUFS outside −17…−15; peak above −1.0 dB.
  - `chequeo_hyperframes(proyecto: Path) -> list[str]` — runs `npx --yes hyperframes@0.9.70 check` in the project; returns every error and every `outside_safe_zone` or `text_below_floor` warning. `timeline_track_too_dense` and `nested_structure_needs_subcomposition` warnings are ignored.
  - `transcribir(audio: Path) -> dict` — `npx --yes hyperframes@0.9.70 transcribe <audio> --model small --language es --json`; returns `{"texto", "palabras": [{"palabra", "inicio"}]}`.

- [ ] **Step 1: Failing tests** for `comparar`:

```python
voz = ["Quien tiene un porqué para vivir, soporta casi cualquier cómo.", "La escribió en 1888."]
check(comparar(voz, "quien tiene un por qué para vivir soporta casi cualquier como la escribio en mil ochocientos ochenta y ocho") is None,
      "tolera división de palabras, tildes, comas y cifras")
check("casi" in (comparar(voz, "quien tiene un porque para vivir soporta cualquier como la escribio en 1888") or ""),
      "detecta la palabra que falta")
check(comparar(voz, voz[0] + " " + voz[1] + " gracias por ver") is not None, "detecta palabras de más")
```

- [ ] **Step 2: Run** — fails. **Step 3: Implement `comparar`.** **Step 4: Run** — passes.
- [ ] **Step 5: Tool wrappers.** Before writing `chequeo_hyperframes` and `transcribir`, run each command once by hand against the spike (`experiments/media-lab/results/spike-hyperframes/nietzsche-frankl.mp4`; scaffold a project around `index.html` for `check`) and save the real outputs as fixtures under `tests/fixtures/narrados/`. Write the parsers against those fixtures, with checks that the spike's four right-edge warnings are reported and that its transcript compares equal to the spike script. If `transcribe` cannot install its runtime or cannot produce Spanish word timestamps, stop and report: the round trip is a required check and the fallback is a decision for the user.
- [ ] **Step 6: Tests for `audio_ok`** using ffmpeg-generated tones: a 30 s file with a 2 s hole at 10 s reports the silence; a 20 s file reports the duration; skip with a printed note when ffmpeg is absent.
- [ ] **Step 7: Run** — passes. **Step 8: Commit** `narrado: chequeos de composición, audio y transcripción`.

---

### Task 6: Candidates, run folders and registry

**Files:**
- Create: `experiments/media-lab/labkit/narrado.py`, `experiments/media-lab/narrados/candidatas.json`
- Test: `tests/test_narrados.py` → `seccion_candidatas()`

**Interfaces:**
- Produces:
  - `elegibles(publicadas: list[dict], candidatas: list[str], registro: list[dict]) -> list[dict]` — pure. Keeps pieces whose id is in `candidatas`, with `core.quote.attribution_verified` true and a non-empty `core.body`; collapses reissues (same normalised `core.quote.text`, and `reemision_de` chains) to the earliest id; drops quotes already in `registro`.
  - `elegir() -> dict` — first of `elegibles` ordered by id; `{"pieza", "run", "carpeta", "es_falsa_atribucion": True}`; run id `NARRADO-YYYYMMDD-HHMM`. Raises `SinCandidatas`.
  - `registrar(entrada: dict) -> None` — appends to `narrados/registro.jsonl`.
- `candidatas.json` is curated once in this task: list published pieces whose `core.subject`, `core.hook` or `core.body` match `atribu|no es de|no es suya|nunca (lo )?dijo|apócrif|falsamente|en realidad (es|la|lo)`, read each, and keep those that tell a "who really said it" story. Record the count in the task report (the spec estimates about 34).

- [ ] **Step 1: Failing tests** with four synthetic pieces: a reissue pair counts once and yields the earlier id; an unverified piece is dropped; a piece not in `candidatas` is dropped; a quote present in `registro` is dropped; an empty result makes `elegir` raise `SinCandidatas`.
- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Curate `candidatas.json`.** **Step 6: Commit** `narrado: candidatas, runs y registro`.

---

### Task 7: `lab.py narrado` and the end-to-end build

**Files:**
- Modify: `experiments/media-lab/lab.py` (new `cmd_narrado`; register `narrado` next to `sitio`, around line 1484), `experiments/media-lab/narrados/README.md`
- Create: `experiments/media-lab/narrados/2026-11-10-re55-reel/guion.json` (the spike's script in the Task 1 shape, design `papel`)
- Test: `tests/test_narrados.py` → `seccion_construir()`

**Interfaces:**
- Consumes: everything above.
- Produces the command, one step per call, JSON on stdout like `sitio`:
  - `lab.py narrado elegir` → prints `elegir()` and creates the run folder.
  - `lab.py narrado construir --pieza ID [--motor kokoro|say]` → in order: load and validate the script; stop on `pendientes` (exit non-zero, list the names, say that `pronunciacion.json` needs `aprobado_por`); delete `build/`; synthesise per sentence; timeline; mix; transcribe the quote sentence for word times (even spacing when the word count differs); write the project; `chequeo_hyperframes`; render with `npx --yes hyperframes@0.9.70 render`; `audio_ok`; transcribe the MP4 and `comparar`; snapshot one frame per scene (`snapshot --at` the midpoint of each) and report the contact-sheet path. Any failure stops, prints the problems, and leaves `build/informe.json` with what failed.
  - `lab.py narrado revisar --pieza ID --veredicto PASS|FAIL` → records the visual verdict in `build/informe.json`; anything but `PASS` marks the build unusable.
- `construir` in `narrado.py` takes its tools as parameters (`sintetizar`, `transcribir`, `render`, `chequeo`) so the test can inject fakes.
- Follow `lab.py`'s existing error and exit-code conventions (`_exigir`, the handling in `main`).

- [ ] **Step 1: Failing tests** with fake tools: a script with unapproved names stops before any synthesis (the fake `sintetizar` records zero calls); a stale file placed in `build/` before the run is gone afterwards; a fake transcript missing a word leaves `informe.json` with the round-trip failure and no "ok"; a clean fake run leaves `informe.json` with `"ok": true`, the MP4 path and the contact-sheet path; running it twice yields the same `informe.json` apart from timestamps.
- [ ] **Step 2: Run** — fails. **Step 3: Implement.** **Step 4: Run** — passes.
- [ ] **Step 5: Real build.** Ask the user to approve the four names in `pronunciacion.json` (they listen to the Task 3 sample or a fresh one; do not fill `aprobado_por` yourself). Then run `lab.py narrado construir --pieza 2026-11-10-re55-reel`. Expected: `"ok": true`, a 25–40 s MP4, zero check problems. Read the contact sheet yourself and fix any layout problem in the generator, not by hand in the project.
- [ ] **Step 6: Finish the README** (the three commands, where output lands, what each check means, how to approve a name) and add a short section for the agent that writes `guion.json`: source is the piece's `core` only, years as digits, 5–7 scenes, one sentence per scene.
- [ ] **Step 7: Run the whole suite:** `.venv/bin/python tests/test_narrados.py` and `.venv/bin/python tests/test_media_lab.py`. Expected: no `✗`.
- [ ] **Step 8: Commit** `narrado: lab.py narrado elegir, construir y revisar`.

---

## After this plan

- Hand the user the built MP4 for the Nietzsche piece and two more candidates' scripts to judge the format.
- Phase 2 starts with a phone probe that posts nothing: push an MP4, register it as a video, open the Reel composer on it, find the «Ajouter une mention IA» control, and record fixtures. Its plan is written from what the probe finds.
