# LAB-TRIVIA-004 · ¿Cuándo adoptó su propia escuela el braille?

- Campaign day: 4
- Family: four-option single-choice trivia image + explanation (`single_choice_trivia`)
- Image batch: object-led editorial master (no person), same palette logic as I01's object control; one master for 4:5 and 9:16 crops
- Seed: `content/published/2026-08-28-manana.json` (el braille: publicado en 1829, prohibido en su propia escuela, adoptado oficialmente en 1854)
- Cells: CELL-031…035 (variant A, API) and CELL-036…040 (variant B, Android native): Facebook feed + Story, Instagram feed 4:5 + Story 9:16, Threads image. CELL-041…043 (variant POLL, Android native): Facebook Story poll, Instagram Story poll, Threads feed poll.
- Controlled variables: same question, same four choices in the same order, same correct id, same explanation, same generated master, same headline, subtitle, disclosure, palette and crop target; same caption per network.
- Changed variable: publishing route (A = API, B = Android native). The POLL cells change a second dimension on purpose: native single-choice poll interaction instead of choices printed on the image and in the caption. POLL results are not compared with A/B as if only the route had changed.
- Correct-answer position: **C**. Record it in the run so later trivia families can rotate.
- Production proximity (not blocking, record in the run): the same topic was reposted as a Story in production (`content/published/2026-09-10-re57-story.json`, published 2026-09-11) and the seed went out on Threads on 2026-09-13; `content/queue/2026-09-24-re55-reel.json` (publish_at 2026-09-25T01:26:00Z) also contains the Braille topic. The A and B variants share the same factual creative on the same feeds; record each twin as a confounder, as with CELL-013/CELL-018.

## Trivia

- `response_mode`: `single`
- `question`: ¿En qué año adoptó oficialmente el braille la escuela de París donde lo creó Louis Braille?
- `choices`:
  - `A`: 1829
  - `B`: 1840
  - `C`: 1854
  - `D`: 1878
- `correct_choice_ids`: [`C`]
- `explanation`: 1854, dos años después de la muerte de Braille (6 de enero de 1852). En 1829 solo publicó su método; en 1840 el nuevo director, Pierre-Armand Dufau, lo prohibió y los alumnos siguieron usándolo a escondidas; tras la demostración de 1844 en la sede nueva volvió a usarse, pero la adopción oficial no llegó hasta 1854. En 1878 lo que ocurrió fue otra cosa: un congreso internacional en París lo propuso como sistema de referencia para todo el mundo.
- `reveal_placement`:
  - Facebook / Instagram feed (CELL-031, 033, 036, 038): `caption`, in the same post, below the question and choices after a visible "Respuesta" marker.
  - Threads image (CELL-035, 040): `caption`, at the end of the same post.
  - Stories (CELL-032, 034, 037, 039): `story_frame_2`, a reveal frame published immediately after the question frame as part of the same cell (at most two frames; campaign limit is three).
  - Story polls (CELL-041, 042): `story_frame_2`, published immediately after the poll frame. The poll frame carries the question only; the choices live in the sticker and must not be repeated on the image (see the LAB-SMOKE-001 sticker defect in `progress.md`).
  - Threads poll (CELL-043): `linked_reply`, a reply to the poll post published in the same session and recorded in the run.
- Poll labels (all native polls): `1829`, `1840`, `1854`, `1878`, in that order. Four characters each, well within any option-length limit. If a composer offers fewer than four options (check the Facebook Story poll sticker in the real composer), do not cut or merge choices: record the cell as unsupported with evidence. Do not build a two-option fallback; in particular `1844` must never appear as a choice (see Do not use).
- Why the distractors are plausible but false:
  - `1829` is the year Braille published his method at that same school, not an adoption.
  - `1840` is the year of a school decision about braille, but it was the ban.
  - `1878` is a real official adoption, but by an international congress, not by the Paris school.

## Verified factual core

Louis Braille was born on 4 January 1809 in Coupvray and died in Paris on 6 January 1852, aged 43. In 1829 the Institution Royale des Jeunes Aveugles in Paris published his *Procédé pour écrire les paroles, la musique et le plain-chant au moyen de points*; he was twenty. On 7 May 1840 the director, Pignier, was forced to retire and was succeeded by Pierre-Armand Dufau, who opposed Braille's code and banned it; students kept using it in secret. At the dedication of the new building on 22 February 1844, Joseph Guadet demonstrated the code, and from then on it was used again at the school. The system was finally adopted by the institute in 1854, two years after Braille's death. In 1878 a congress in Paris decided to adopt braille as the international writing system for blind people.

Sources opened for this brief (2026-09-15):

- American Printing House for the Blind, *Blindness History Basics: The First Publication of the Braille Code*: https://www.aph.org/blog/blindness-history-basics-the-first-publication-of-the-braille-code/ — 1829 publication by the Paris institution; Braille was twenty.
- Musée Louis Braille (Coupvray), *Braille l'inventeur*: https://museelouisbraille.com/fr/braille-l-inventeur — birth on 4 January 1809; blindness after an accident at three; editions of 1829 and 1837.
- Musée Louis Braille (Coupvray), *National Institute for Blind Youth*: https://museelouisbraille.com/en/institut-des-jeunes-aveugles — Dufau, opposed to braille, banned it and students kept using it in secret; demonstrations at the inauguration of the new premises in 1844.
- American Foundation for the Blind, *Recognition of the Braille Code*: https://afb.org/about-afb/history/online-museums/life-and-legacy-louis-braille/braille-recognized — 7 May 1840: Dufau succeeds Pignier and bans the code for students and teachers.
- American Foundation for the Blind, *Braille's Code Demonstrated*: https://afb.org/about-afb/history/online-museums/life-and-legacy-louis-braille/braille-recognized/braille — 22 February 1844 demonstration by Guadet at the new building.
- American Foundation for the Blind, *The Final Years of Louis Braille*: https://afb.org/about-afb/history/online-museums/life-and-legacy-louis-braille/braille-recognized/final-years — death on 6 January 1852, two days after his 43rd birthday.
- Wikipedia (English), *Louis Braille*: https://en.wikipedia.org/wiki/Louis_Braille — 1840 Dufau; reintroduction in 1844; "finally adopted by the Institute in 1854, two years after his death".
- Wikipedia (English), *Pierre-Armand Dufau*: https://en.wikipedia.org/wiki/Pierre-Armand_Dufau — Dufau director from 1840 and suppression of braille that year.
- American Foundation for the Blind, *The Unseen Minority*, ch. 8 "Language of the Fingers": https://afb.org/online-library/unseen-minority-0/chapter-8 — "braille's official adoption in Paris in 1854". Use only for 1854: the same chapter gives other dates (death on 16 January; alphabetic code in 1834) that contradict the museum and AFB's own biography pages.
- Institut de France, podcast *Louis Braille : le jeune surdoué inventeur d'une écriture pour les aveugles*: https://podcasts.institutdefrance.fr/emissions/parcours/louis-braille-le-jeune-surdoue-inventeur-dune-ecriture-pour-les-aveugles — 1829 first publication by the Institut royal; death on 6 January 1852; in 1854 France officially recognised the invention.
- WIPO Magazine, *Bicentenary of Louis Braille*: https://www.wipo.int/en/web/wipo-magazine/articles/bicentenary-of-louis-braille-the-world-at-our-fingertips-36832 — 1829 publication; adoption two years after Braille's death.
- American Foundation for the Blind, *Dissemination of Braille*: https://afb.org/about-afb/history/online-museums/life-and-legacy-louis-braille/braille-recognized/dissemination — 1878 congress in Paris adopts braille as the international system.
- Musée Louis Braille (Coupvray), *Reconnaissance universelle*: https://museelouisbraille.com/fr/reconnaissance-universelle — 1878 Congrès universel in Paris proposes braille as the reference system; transfer to the Panthéon on 21 June 1952.

Independence per critical claim:

- 1854 official adoption: Wikipedia *Louis Braille*, AFB *Unseen Minority* and the Institut de France (France's official recognition). WIPO corroborates "two years after his death". Britannica also states it for the Paris school (seed), but returned 403 and was not opened.
- 1840 ban: AFB and the Coupvray museum; year also confirmed by Wikipedia *Dufau*.
- 1829 publication: APH, the Coupvray museum and the Institut de France.
- 1878 congress: AFB and the Coupvray museum.

Sources not opened (403 on WebFetch) and therefore not cited in public copy: Britannica (*Braille writing system*), Perkins School for the Blind (*Louis Braille, Charles Barbier, and the making of a myth*), Library of Congress NLS (*Louis Braille 1809–1852*), National Federation of the Blind.

## Overlay

> ¿CUÁNDO ADOPTÓ  
> SU PROPIA ESCUELA  
> EL BRAILLE?

> A 1829 · B 1840 · C 1854 · D 1878

Disclosure label on every master: `ESCENA GENERADA · NO ES FOTO HISTÓRICA`.

`lab.py render` values: `--titular "¿CUÁNDO ADOPTÓ|SU PROPIA ESCUELA|EL BRAILLE?"`, `--subtitulo "A 1829 · B 1840 · C 1854 · D 1878"`, `--aviso "ESCENA GENERADA · NO ES FOTO HISTÓRICA"`.

### POLL question frame (CELL-041, 042)

Same three headline lines and disclosure. Subtitle replaced by `Vota en la encuesta` so the choices are not duplicated under the sticker. The central band must stay free for the sticker; verify with the real sticker in each composer before sharing (`visual-qa-gate.md`).

### Reveal frame (Stories and Story polls)

> RESPUESTA C:  
> EN 1854, TRAS  
> SU MUERTE

> Prohibido en 1840 · usado de nuevo en 1844

Same master, palette and disclosure. The Threads poll has no reveal frame; its reveal goes in the linked reply below.

## Caption draft — Facebook / Instagram

¿En qué año adoptó oficialmente el braille la escuela de París donde lo creó Louis Braille?

A) 1829
B) 1840
C) 1854
D) 1878

Deja tu letra en los comentarios antes de leer la respuesta.

·
·
·

Respuesta: C) 1854.

Louis Braille publicó su método en 1829 en esa misma escuela, la Institución Real de Jóvenes Ciegos de París. Tenía veinte años. En 1840 llegó un director nuevo, Pierre-Armand Dufau, y lo prohibió; los alumnos siguieron usándolo a escondidas. En 1844, en la inauguración de la sede nueva, se hizo una demostración pública y el sistema volvió a usarse. Pero la adopción oficial no llegó hasta 1854, dos años después de la muerte de Braille, el 6 de enero de 1852.

¿Y 1878? Ese año, un congreso internacional reunido en París adoptó el braille como sistema de escritura para personas ciegas de todo el mundo. Fue otro reconocimiento, no el de su escuela.

La imagen es una escena editorial generada para este experimento; no es una fotografía histórica ni reproduce una página real en braille. Fuentes: American Printing House for the Blind, American Foundation for the Blind, Museo Louis Braille de Coupvray e Institut de France.

#SabiduriaDeBolsillo #Braille #LouisBraille #HistoriaDeLaEducacion

## Caption draft — Threads

¿En qué año adoptó oficialmente el braille la escuela de París donde lo creó Louis Braille?

A) 1829 B) 1840 C) 1854 D) 1878

Respuesta: C) 1854, dos años después de su muerte. Lo publicó allí en 1829; en 1840 un director nuevo lo prohibió y los alumnos lo siguieron usando a escondidas. Volvió a usarse en 1844, pero no fue oficial hasta 1854.

Escena generada, no foto histórica.

### Threads poll post (CELL-043)

¿En qué año adoptó oficialmente el braille la escuela de París donde lo creó Louis Braille? Vota y encontrarás la solución en la primera respuesta a este post.

### Threads poll linked reply (CELL-043)

Respuesta: 1854, dos años después de la muerte de Braille. En 1829 publicó su método en esa escuela; en 1840 un director nuevo lo prohibió; en 1844 volvió a usarse. 1878 fue el congreso internacional que lo adoptó para todo el mundo. Fuentes: APH, AFB y Museo Louis Braille.

## Do not use

- Do not offer `1844` as a choice, and do not call 1844 "la adopción oficial": the AFB page says that day is "often said" to be when the code was accepted, so it would give the question a second defensible answer.
- Do not say France passed a national law adopting braille in 1854. The sources support adoption by the Paris institute and France's official recognition that year, not a specific legal act.
- Do not say Braille invented the system at twelve (he met Barbier's system then; he published his own in 1829, at twenty) or at fifteen (a common popular version).
- Do not say Barbier invented "night writing" for Napoleon's soldiers (myth; seed `do_not_use`).
- Do not say Dufau burned braille books (not supported by the institutional sources; seed `do_not_use`).
- Do not say Braille and Barbier were enemies, or that they met before 1833.
- Do not call braille a language; it is a writing system.
- Do not date the ban's exception for music notation as a firm fact in public copy: Wikipedia *Dufau* mentions it, AFB does not.
- Do not use the dates from AFB *Unseen Minority* for death (16 January) or the alphabetic code (1834).
- Do not phrase the question as "¿Cuándo aceptaron el braille?" or "¿Cuándo se reconoció el braille?" without "oficialmente" and "la escuela de París": 1844 and 1878 would become defensible.
- Representation limits: no portrait or likeness of Louis Braille; no blind child with bandaged eyes, dark glasses or pity framing; no generated braille that could be read as real text; nothing that suggests death or mourning, a year, a calendar or a congress, since those would hint at the answer.

## Image-generation prompts

Built-in image generation, `historical-scene`. No text is requested in-image; the headline, choices, reveal and disclosure are applied deterministically with `lab.py render`. One master serves the feed crop (4:5), the Story crops (9:16) and the reveal frame.

### Direction A — object-led study table

```text
Use case: historical-scene
Asset type: Sabiduría de Bolsillo social editorial, portrait master for 4:5 and 9:16 crops
Primary request: Create an object-led editorial image for a four-option trivia post about when the Paris school for blind youth officially adopted Louis Braille's raised-dot writing system. The image must set the scene without revealing or hinting at the answer.
Scene/backdrop: a quiet study room in a Paris school for blind youth in the 1830s–1840s, wooden desk by a tall window, plain plaster wall, a few bound books of heavy paper stacked at the side.
Subject: no person and no hands; on the desk, a sheet of thick cream paper covered in neat rows of small raised dots in six-dot cells, a period hand writing frame (slate) with a small wooden-handled stylus resting beside it.
Style/medium: premium editorial photography with subtly cinematic historical atmosphere, tactile realism, documentary restraint rather than advertising gloss.
Composition/framing: vertical portrait; desk, paper and slate across the lower third; a calm middle band free of important detail (a native poll sticker may cover it in Stories); generous quiet negative space across the upper third for a later Spanish headline panel; crop-safe for 4:5 and 9:16.
Lighting/mood: soft side daylight from the window raking across the paper so the dots cast tiny shadows; curious, respectful, thoughtful.
Color palette: warm cream paper, walnut wood, muted slate blue-grey, restrained brass.
Text (verbatim): none.
Constraints: no readable text of any kind, no numbers, no dates, no letters, no logos, no watermark; the raised dots are schematic texture and must not spell real braille words; historically plausible 19th-century objects; no human figure or body parts.
Avoid: portraits or likeness of Louis Braille, calendars, clocks showing dates, candles or flowers suggesting mourning, gravestones, banners, flags, crowds or congress halls, modern braille displays, plastic, eyeglasses, bandages, printed labels, garbled writing, fantasy machinery.
```

Result: pendiente de generación por encargo.

## Assets and decisions

- Master image: pendiente de generación por encargo.
- Feed masters (4:5), Story question masters, POLL question masters and reveal-frame masters (9:16): pendientes de generación por encargo; rendered later from the approved image with the Overlay values above.
- Editorial decisions still open for the run: whether the Facebook Story poll sticker exposes four options (if not, CELL-041 is recorded as unsupported, not adapted); and the exact moment of the Threads poll linked reply (proposed: same session, right after the poll post).
