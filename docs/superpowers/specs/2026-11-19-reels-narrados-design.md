# Narrated reels, built on the Mac and posted from the lab phone

Date: 2026-11-19. Status: awaiting the user's approval. Size: a project.

## Intent

Sabiduría de Bolsillo publishes quote cards and a nine-second silent reel
(`src/render/reel.py`). Reels are the surface that reaches people who do not follow
the account, and the silent reel gives them little reason to stay. This project adds
a second reel format: a 25–40 second narrated micro-story (who really said it, when,
why it matters), animated in the brand's own typography, with a synthetic voice.

A throwaway spike on 2026-11-19 proved the chain works: one HTML page plus a voice
file rendered to a 29-second 1080×1920 MP4 in 16 seconds with HyperFrames
(`experiments/media-lab/results/spike-hyperframes/`).

## Goals

- Turn an already published, already verified piece into a narrated reel with no new
  research and no new facts.
- Build and check each reel on the Mac before anything is posted.
- Post it natively from the lab phone as an Instagram Reel with its own audio.
- Keep the voice engine swappable, so a better voice later costs one small module.

## Non-goals

- Rendering inside GitHub Actions. The publisher and its workflows are not touched.
- Facebook reels and TikTok in the first version (TikTok is the next step; see Phases).
- Music, sound effects, 3D (Blender), generated footage or images.
- A paid voice. It is reconsidered only if the free voices fail the listening test.

## Anti-goals

- A narration that states anything the source piece does not state.
- A reel that goes out with a mispronounced name, a clipped sentence, or text under
  Instagram's buttons.
- "Bouncing text". Motion stays restrained: fades, short rises, one background change.
  `reel.py` records that the brand is contemplative; narration is the only loosening.

## Constraints

- The phone loop (`lab.py sitio`, every 90 min, 08:00–23:00 Madrid) owns the phone
  most of the day. The narrated reel must take the phone lock and never overlap it.
- Reel safe zone used by the project: y 240–1500; HyperFrames also flags the right
  edge (TikTok buttons). Zero safe-zone warnings is the bar.
- Instagram may auto-share to the Facebook Page and switch accounts mid-flow; the
  existing account and cross-post checks in `labkit` apply.
- Scheduled runs must not use compound shell commands or background agents.
- Synthetic voice is disclosed on the end card and in the caption.

## Approaches considered

- **A. Render in Actions at publish time.** Keeps "video is a pure function of the
  JSON", but nobody hears the reel before it goes out, the workflow gains Node and
  Chrome, and a failed render blocks a slot. Rejected.
- **B. Pre-render on the Mac, upload through the existing API publisher.** Safest
  for the publisher, Facebook only. Not chosen.
- **C. Pre-render on the Mac, post from the lab phone.** Chosen by the user on
  2026-11-19: it reaches Instagram (and later TikTok) natively. Cost: it inherits
  the phone's fragility (screen lock, language changes, account switches).

## Design

### 1. Source and script

- Candidates: pieces in `content/published/` with `core.quote.attribution_verified`
  true and a `core.body`. Reissues are collapsed: one reel per distinct quote
  (about 130 today, of which about 34 are "who really said it" stories).
- First version: only the misattribution stories (see Decisions).
- The script lives in a new file per reel, `experiments/media-lab/narrados/<id>/guion.json`:
  an ordered list of 5–7 scenes, each `{tipo, voz, pantalla}`. `voz` is the sentence
  spoken; `pantalla` is the short on-screen text.
- Scene types (closed list, each optional except `cita` and `pregunta`; `tachado`
  only for misattribution pieces): `tachado` (a name struck through), `cita` (word by
  word), `nombre_ano` (name, year, one italic line), `contraste` (two lines, paper
  turns to ink), `pregunta` (closing question, signature, "Voz sintética").
- The agent in the routine writes the script from the piece's `core` only.
- A deterministic validator rejects the script when: a year, number or capitalised
  name in it is absent from the piece; the quote differs from `core.quote.text`; a
  term from `do_not_use` appears; the total is outside 25–40 s after synthesis.
  (Builder's call: years are compared as digits after expanding spelled-out numbers.)

### 2. Voice

- One interface: `sintetizar(frase, salida_wav)`. Engines behind it: `kokoro`
  (local, Apache-2.0) and `say` (macOS) now; a paid engine could be added later.
- Narration is synthesised one sentence per file. Measured durations define the
  timeline: scene start = previous end + gap (0.45 s; 0.7 s before the quote and
  the question).
- A small pronunciation table (`pronunciacion.json`) rewrites names and years for
  the voice only; the on-screen text is never altered.
- The mix is normalised to −16 LUFS, true peak −1.5 dB.
- Voice: Kokoro `em_santa` (see Decisions).
- Pronunciation needs a person's approval (see Decisions). The round trip in check 3 cannot catch a
  mangled name, because a recogniser tends to write "Nietzsche" correctly anyway.

### 3. Composition

- A generator writes a HyperFrames project (`index.html`, fonts, voice) from
  `guion.json` and the timeline. Templates live in the repo; fonts and GSAP are
  vendored so a render needs no network.
- Three designs, matching the site: Papel, Tinta, Siena; one chosen per reel.
  The spike only has the paper and ink palette; Siena's values come from the site
  repository (`~/dev/sitio-sdb`).
- Word-by-word timing in `cita` comes from word timestamps
  (`hyperframes transcribe --model small --language es`), not from estimates.
- The first frame already shows text (it is the thumbnail).
- HyperFrames is pinned (`hyperframes@0.9.70`) with telemetry disabled. It is not
  on PATH: the spike ran it through `npx`, and Kokoro needed a Python 3.12
  environment (3.14 fails) with models under `~/.cache/hyperframes/tts`. Setting
  this up reproducibly, and vendoring GSAP (the spike used a CDN), is part of phase 1.

### 4. Checks before posting

All must pass, in this order; any failure stops the run and leaves a note:

1. `hyperframes check`: zero errors and zero safe-zone or type-size warnings.
2. Audio: no silence longer than 1.2 s inside the narration, loudness in range,
   duration 25–40 s.
3. Round trip: the rendered audio is transcribed and compared with the script.
   Any missing or extra word fails. Names in the pronunciation table are compared
   by their written form.
4. Visual: the contact sheet of one frame per scene goes to a review agent, as the
   lab does today for images (PASS required).

### 5. Posting from the phone

New `lab.py narrado` steps, one per call, mirroring `lab.py sitio`:

```
lab.py lock-tomar --dueno narrado
lab.py narrado elegir                 # piece id and design
lab.py narrado construir --run R      # script check, voice, render, checks 1–3
lab.py narrado revisar --run R --veredicto PASS
lab.py narrado subir --run R          # telefono-subir of the MP4
lab.py narrado publicar --run R       # Reel composer, original audio, caption
lab.py narrado verificar --run R
lab.py lock-soltar --dueno narrado
```

- The Reel keeps its own audio: no track is added. The «Mise à jour de votre audio
  d'origine» prompt is answered «Désactiver et partager» (decision of 3 Nov).
- Cross-posting stays off, set on every run as `escribir_pie(..., cruzar=False)`
  and `ajustar_cruces(False)` already do.
- Caption: the piece's hook and question, the piece's `tags` as hashtags (builder's
  call: the repo records that captions without them reach only followers), and the
  line "Voz sintética". No URL, following the decision of 6 Nov for feed and Reel
  captions (`pie_para`).
- `narrado` is added to `DUENOS_VENTANA` in the lock.
- **Video upload is new work.** `telefono-subir` accepts only images and registers
  them in the images MediaStore, and every existing Reel enters through Chrome's
  share sheet with an image. Phase 2 starts with a phone probe, without posting:
  push an MP4, register it as video, open the Reel composer on it, record fixtures.
- Instagram's AI label is switched on (see Decisions); this adds a composer step
  and fixtures.
- `verificar` confirms the reel on the brand profile and records it in
  `narrados/registro.jsonl` (committed). Media and evidence stay out of git.
- Cadence (builder's default, the user may change it): one narrated reel a day,
  in a slot the 90-minute loop does not use.

### 6. Tests

Unit tests for the pure parts: script validator, timeline builder, pronunciation
rewrite, project generator (HTML contains the right scenes and times), transcript
comparison. Phone steps follow the fixture pattern of section 27 of
`tests/test_media_lab.py`.

## Phases

1. Builder: `elegir`, `construir`, checks, with the output reviewed by hand.
2. Phone: `subir`, `publicar`, `verificar`; first real reel posted with the user
   watching.
3. Scheduled daily run.
4. Later, separately decided: TikTok, Facebook, a paid voice.

## Left to the builder

- Module layout inside `labkit/`, template markup, exact easing and timings.
- How `elegir` orders candidates.
- Where vendored GSAP and the templates live.

## Decisions

Decided by the user on 2026-11-19:

- **Voice:** Kokoro `em_santa` (male, Spanish, local, Apache-2.0), chosen by ear
  from seven free samples. `say` stays as a fallback engine for tests only.
- **Instagram's «Ajouter une mention IA»:** on for every narrated reel. `publicar`
  sets it and `verificar` fails if it is not set.

Builder's defaults, recommended to the user and not yet confirmed by them:

- **Pronunciation:** a run stops when a name or year in the script has no entry in
  `pronunciacion.json` marked as approved by a person. The run leaves a note
  listing the missing entries.
- **Which pieces:** start with the ~34 misattribution stories; widening to any
  verified quote is a later, separate decision.
- **Cadence:** one narrated reel a day.
