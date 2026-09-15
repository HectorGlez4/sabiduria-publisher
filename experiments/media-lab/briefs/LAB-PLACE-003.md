# LAB-PLACE-003 · Nan Madol, patrimonio y en peligro el mismo día

- Campaign day: 3
- Family: place-led image with factual location text (`place_led_image`)
- Image batch: I04-style place setting; one object/landscape-led master, no person
- Seed: `content/published/2026-09-08-extra94.json` (Nan Madol, los islotes de basalto de Pohnpei)
- Cells: CELL-021…025 (variant A, API) and CELL-026…030 (variant B, Android native) — Facebook feed + Story, Instagram feed 4:5 + Story 9:16, Threads image.
- Controlled variables: same factual core, same generated master, same headline, subtitle, disclosure, palette and crop target; same captions per network.
- Changed variable: publishing route (A = API, B = Android native). Treatment under test for the day: the place is carried by a recognisable setting plus an accurate place label in the deterministic overlay. **No native location tag, Location sticker or check-in on any cell** (that is Day 11, LAB-LOCATION-011); in the Android route, leave the composers' Location controls untouched.
- Production proximity (not blocking, record in the run): the same topic is queued in production as `content/queue/2026-09-25-re62-story.json` (publish_at 2026-09-25T20:26:00Z). Every other place candidate in the corpus (Caral, Göbekli Tepe, Angkor, Gran Zimbabue, Meroe, Tombuctú, Aksum) also has a queued repost, several of them sooner.

## Verified factual core

Nan Madol is a complex of nearly a hundred artificial islets built on the reef off the south-east coast of Pohnpei, in the Federated States of Micronesia, separated by tidal canals and walled with columnar basalt and coral. It was the ceremonial centre of the Saudeleur dynasty: megalithic construction with columnar basalt began around AD 1200 and the Saudeleur chiefdom fell apart in the early 1600s. In July 2016, at the 40th session of the World Heritage Committee (Istanbul), it was inscribed on the World Heritage List and simultaneously placed on the List of World Heritage in Danger, because siltation of the waterways is feeding the unchecked growth of mangroves that undermines the structures. A study led by Mark D. McCoy (Southern Methodist University), published in *Quaternary Research* 86(3), 2016, used ²³⁰Th/U coral dating to place the start of monument building at Nan Madol in AD 1180–1200, at the tomb of Nandauwas (80 × 60 m, walls more than 8 m high), built with basalt brought from the opposite side of the island.

Sources opened for this brief (all fetched 2026-09-15):

- UN News (United Nations), «UNESCO adds four new sites to World Heritage List», July 2016: https://news.un.org/en/story/2016/07/534472 — inscription in 2016 by the 40th session in Istanbul; simultaneous Danger List listing; reason (siltation → unchecked mangroves → weakened edifices); «99 artificial islets»; built 1200–1500; Saudeleur dynasty.
- International Archaeological Research Institute (IARII), «Monumental Architecture of Nan Madol»: https://iarii.org/research/monumental-architecture-of-nan-madol/ — «over 90 rectilinear islets»; ~80 ha; artificial islets by AD 900; columnar-basalt megalithic construction from AD 1200 with the Saudeleur; collapse in the early 1600s; basalt quarried on the main island, columns of several tons or more.
- SMU Research blog, «Evidence of first chief indicates Pacific islanders invented a new society on city they built of coral and basalt», 18 Oct 2016: https://blog.smu.edu/research/2016/10/18/evidence-of-first-chief-indicates-pacific-islanders-invented-a-new-society-on-city-they-built-of-coral-and-basalt/ — Nandauwas 80 × 60 m, walls over 8 m; stones moving by 1180, first interment by 1200; basalt from a volcanic plug on the opposite side of the island; coral and basalt; «98» islets; described by SMU as the first monumental-scale burial site on the remote Pacific islands.
- McCoy, Alderson, Hemi, Cheng & Edwards, *Quaternary Research* 86(3), Nov 2016 (abstract, Cambridge Core): https://www.cambridge.org/core/journals/quaternary-research/article/earliest-direct-evidence-of-monument-building-at-the-archaeological-site-of-nan-madol-pohnpei-micronesia-identified-using-230thu-coral-dating-and-geochemical-sourcing-of-megalithic-architectural-stone/0338E86D312973BA0B32D56A5D297FAF — AD 1180–1200 as the beginning of monument building at Nan Madol; monument building elsewhere in Oceania from AD 1300–1600.

Not opened (HTTP 403 to WebFetch, like Britannica/Cervantes/congress.gov): UNESCO World Heritage Centre, https://whc.unesco.org/en/list/1503/ and https://whc.unesco.org/en/news/1524. Nothing in the captions depends only on them.

## Overlay

> PATRIMONIO MUNDIAL  
> Y EN PELIGRO  
> EL MISMO DÍA

> Nan Madol, Pohnpei · 2016

Visible notice (all cells): `ESCENA GENERADA · NO ES FOTOGRAFÍA`

The subtitle is the accurate place label for this test; it is set only by the overlay, never generated inside the image. `render_overlay.py` does not auto-fit the subtitle (fixed 38/42 px), so keep it at this length.

## Caption draft — Facebook / Instagram

En julio de 2016, la UNESCO inscribió Nan Madol, frente a la costa sureste de Pohnpei (Estados Federados de Micronesia), en la Lista del Patrimonio Mundial y, a la vez, en la Lista del Patrimonio Mundial en Peligro.

Son casi un centenar de islotes artificiales levantados sobre el arrecife y separados por canales, con muros de basalto columnar y coral. Fue el centro ceremonial de la dinastía Saudeleur. Un equipo dirigido por el arqueólogo Mark McCoy fechó la tumba monumental de Nandauwas —80 por 60 metros, muros de más de 8 de alto— entre 1180 y 1200, con piedras traídas del otro lado de la isla.

El motivo del «en peligro» no es el saqueo: los canales se están azolvando, y en ese sedimento crecen sin control manglares que debilitan los muros.

¿Qué se te está cerrando por falta de mantenimiento y no de valor?

La imagen es una escena generada para este experimento, no una fotografía de Nan Madol. Fuentes: Naciones Unidas (UN News, 2016), International Archaeological Research Institute, Southern Methodist University y Quaternary Research (McCoy et al., 2016).

#SabiduriaDeBolsillo #NanMadol #Micronesia #PatrimonioMundial

## Caption draft — Threads

En julio de 2016, la UNESCO inscribió Nan Madol (Pohnpei, Micronesia) como Patrimonio Mundial y, a la vez, en la Lista en Peligro.

Casi un centenar de islotes artificiales de basalto y coral sobre el arrecife, centro ceremonial de la dinastía Saudeleur. La amenaza: canales azolvados donde crecen manglares que debilitan los muros.

Escena generada, no fotografía del sitio.

## Do not use

- Do not give a closed number of islets (sources say 99, 98 and «over 90»); say «casi un centenar».
- Do not claim it is still on the Danger List today, or that it has left it: the latest state (48th Committee session, 2026) was not verified. Keep the fact dated to 2016.
- Do not say nobody knows who built it or imply a mystery/aliens/lost continent: Pohnpeian tradition and archaeology attribute it to the Saudeleur. The exact transport method is what remains unsettled.
- Do not say the basalt columns were carved: it is natural columnar basalt, quarried and moved.
- Do not repeat «750.000 toneladas», «5 toneladas de media» or «hasta 50 toneladas»; verifiable wording is «varias toneladas o más».
- Do not call it «la Venecia del Pacífico» or «ciudad perdida».
- Do not date its end to 1500 or say it was abandoned suddenly; the Saudeleur collapse is early 1600s.
- Do not call the Nandauwas date the oldest monumental construction in all Oceania as an unqualified fact; attribute any such framing to the McCoy/SMU team. Do not attribute the study to PNAS (it is *Quaternary Research*).
- Do not say mangrove roots «push the walls from inside» as sourced fact in these captions: the opened sources say mangroves undermine/weaken the structures; the root-dislodging wording was only seen in an unopened UNESCO excerpt.
- Representation limits: the image is a generated editorial scene, not documentary evidence of the site's current condition; do not describe specific walls, islets or damage in it as real. No invented signage, plaques or map labels inside the image. No native location tag, Location sticker or check-in on this family, nothing implying the brand was physically there, no phone GPS. No private location of any kind.

## Image-generation prompts

Built-in image generation, `historical-scene` / `ads-marketing`. No text in-image; the Spanish overlay, place label and notice are applied deterministically with `lab.py render` (`render_overlay.py`). The overlay panel covers roughly the top 30 % of the feed crop (y 76–405 of 1350) and y 250–680 of 1920 in Story, with the notice and brand pills at y 1542–1660 (the Story viewer covers the top 250 px and the bottom 260 px), so the upper third and that bottom band must be quiet.

### Direction A — place-led landscape (publishable direction)

```text
Use case: historical-scene
Asset type: Sabiduría de Bolsillo social editorial, portrait master crop-safe for 4:5 (1080×1350) and 9:16 (1080×1920)
Primary request: Create a place-led editorial scene evoking the present-day ruins of Nan Madol, a complex of artificial islets on the reef off the south-east coast of Pohnpei, Micronesia, inscribed as World Heritage and as World Heritage in Danger in 2016 because silted canals let mangroves grow over the walls.
Scene/backdrop: a shallow tidal canal at low water between two low artificial islets; walls built of long dark natural columnar basalt prisms stacked horizontally in alternating crisscross courses (header-and-stretcher, like a log cabin), with coral rubble fill; muddy silted water; young mangroves and tropical vegetation growing along and out of the wall bases; dense green rainforest and a hazy volcanic ridge in the far background.
Subject: no people; the basalt wall and the encroaching mangroves are the subject.
Style/medium: premium documentary-style editorial photography, physically believable stone, water and vegetation, restrained and respectful rather than adventurous or mysterious.
Composition/framing: vertical; canal leading the eye from lower foreground into the middle distance; basalt walls occupying the lower and middle thirds; soft overcast sky and treetops forming generous quiet negative space across the upper third for a later Spanish headline; keep the bottom 8 % free of important detail for small labels; crop-safe for 4:5 and 9:16.
Lighting/mood: humid soft overcast tropical daylight with gentle haze, calm, slightly melancholic.
Color palette: deep basalt charcoal, mangrove green, silt brown, muted teal water, pale grey sky.
Text (verbatim): none.
Constraints: no readable text, no signs, plaques, map labels or numbers, no logos, no watermark; basalt must look like natural hexagonal-section columns, not carved or dressed blocks; no mortar; plausible scale (walls a few metres high); no human figures, boats or modern objects.
Avoid: tourists, guides, kayaks, drones, fantasy or "lost city" ruins, glowing effects, carved reliefs, Maya/Inca/Angkor/Egyptian stonework, pyramids, moai, Venetian imagery, dramatic storm skies, turquoise resort water, garbled writing.
```

Result: pending.

### Direction B — minimal background control (optional, only if an I04 comparison is scheduled)

```text
Use case: historical-scene
Asset type: Sabiduría de Bolsillo social editorial, portrait master crop-safe for 4:5 and 9:16
Primary request: Create the minimal-background control for the same comparison: the same kind of stacked natural columnar basalt wall with a young mangrove growing from its base, isolated from any recognisable landscape.
Scene/backdrop: plain soft mid-grey-green seamless background with a faint shallow-water reflection, no forest, no canal, no horizon.
Subject: a short section of dark columnar basalt prisms stacked in alternating crisscross courses, a young mangrove rooted at its base; no people.
Style/medium: premium editorial still-life photography, physically believable stone and plant.
Composition/framing: vertical; wall and mangrove in the lower and middle thirds; generous quiet negative space across the upper third for a later Spanish headline; crop-safe for 4:5 and 9:16.
Lighting/mood: soft diffuse daylight, calm.
Color palette: match Direction A — basalt charcoal, mangrove green, silt brown, muted teal, pale grey.
Text (verbatim): none.
Constraints: no readable text, signs, numbers, logos or watermark; natural uncarved basalt columns; no human figures.
Avoid: carved blocks, mortar, fantasy ruins, glowing effects, garbled writing.
```

Result: pending. Direction B is not needed for Day 3 publication; the family's cells all use Direction A.

## Assets and decisions

- Pendiente de generación por encargo. No master, derivative, hash or run exists yet for LAB-PLACE-003.
- Feed cells (CELL-021, 023, 025, 026, 028, 030) and Story cells (CELL-022, 024, 027, 029) must go in separate encargos (4:5 vs 9:16).
- Decision: the place label lives only in the overlay subtitle; the native place tag is deferred to LAB-LOCATION-011.
