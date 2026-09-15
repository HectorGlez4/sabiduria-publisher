# LAB-LOCATION-011 · Un faro romano que sigue en servicio

- Campaign day: 11
- Family: location_story, place-led story with accurate label and native tag where available
- Image batch: I01, place-led direction (recognizable setting)
- Seed: none in `content/published/`; verified place chosen for this family. Not the place of LAB-PLACE-003 (no brief existed when this was written; LAB-PLACE-003 must choose a different place).
- Controlled variables: same factual core, headline, visible place label, generated master, palette and crop target in every cell.
- Changed variable: native place tag. Variant A (CELL-121/122/123, API) carries only the visible place label printed by the overlay, plus the native `location_id` on Threads if the API route has permission. Variant B (CELL-124/125/126, Android native) adds the native location sticker or tag only if the composer offers an exact match by name.
- Disclosure: the image is a generated editorial scene of the tower, not a photograph of the monument.

## Location

- Exact public place name (official sources): **Torre de Hércules** (UNESCO: *Tower of Hercules*). Roman name recorded by UNESCO: *Farum Brigantium*.
- City and country: A Coruña, Galicia, España.
- Visible place label printed by the overlay (exact text): `TORRE DE HÉRCULES · A CORUÑA`
- Native tag: search only for the exact name `Torre de Hércules` (A Coruña). Add the native `location_id` / sticker only if the platform offers that exact public place. Never use the phone's current location, «cerca de ti» suggestions, check-ins or private places. If no exact match appears, publish without a tag, keep the printed label, and record `location_not_offered`.
- Suggested run `location_treatment`: `{"visual_place": "generated editorial scene of the Torre de Hércules headland", "text_label": "TORRE DE HÉRCULES · A CORUÑA", "native_place_id": null, "native_place_label": null}`. Fill `native_place_id` and `native_place_label` only with what the platform actually returned.

## Verified factual core

The Torre de Hércules in A Coruña is a Roman lighthouse built between the second half of the 1st century and the beginning of the 2nd century AD. A rock inscription at its base dedicates it to Mars Augustus and names Gaius Sevius Lupus, an architect from Aeminium (today Coimbra, Portugal) in Lusitania. In 1788 Carlos III authorized its restoration, financed by the Consulado del Mar. The engineer Eustaquio Giannini directed the work, which finished in 1790 and wrapped the Roman core in the stone exterior seen today. The tower still works as a maritime signal: the A Coruña Port Authority lists its white light with a range of 23 nautical miles. On 27 June 2009, at its session in Seville, the World Heritage Committee added it to the World Heritage List. UNESCO describes it as the only lighthouse of Greco-Roman antiquity to have kept a measure of structural integrity and functional continuity.

Sources opened on 2026-09-15:

- Torre de Hércules, official site (Concello da Coruña), «Antigüedad»: https://www.torredeherculesacoruna.com/torre/es/descubrela/dos-mil-anos-de-luz/antiguedad?argIdioma=es. Supports the Roman origin, Brigantium = A Coruña, and «el único faro romano que desde sus orígenes hasta la actualidad ha cumplido con su función».
- Official site, «Las restauraciones»: https://www.torredeherculesacoruna.com/torre/es/descubrela/dos-mil-anos-de-luz/las-restauraciones?argIdioma=es. Supports the authorization by Carlos III on 4 January 1788, financing by the Consulado del Mar, the project by Giannini, Cornide's collaboration, and the decision to keep the Roman structure.
- Official site, «Patrimonio Mundial»: https://www.torredeherculesacoruna.com/torre/es/patrimonio-mundial?argIdioma=es. Supports the inscription on 27 June 2009 at the 33rd session of the Committee in Seville (criterion iii) and that the lighthouse still works today.
- Autoridad Portuaria de A Coruña: https://www.puertocoruna.com/torre-de-hercules. Independent operator source for the active light: white light, range 23 nautical miles, focal plane 49 m above sea level. Dates it to the second half of the 1st century or the beginning of the 2nd.
- Concello da Coruña, Castro de Elviña, «Gaius Servius Lupus» and «Torre de Hércules»: https://www.coruna.gal/castroelvina/es/castro-habitado/personas/detalle/gaius-servius-lupus/contenido/1453606093829?argIdioma=es and https://www.coruna.gal/castroelvina/es/castro-habitado/objetos/detalle/torre-de-hercules/contenido/1453614280400?argIdioma=es. Support the inscription text (Mars Augustus, architect from Aeminium, Lusitanian, *ex voto*), the Flavian dating, and the 34 m Roman height against 55 m after Giannini.
- Xunta de Galicia, Turismo de Galicia, «Historia de la Torre»: https://www.turismo.gal/que-visitar/destacados/torre-de-hercules/historia-da-torre?langId=es_ES. Independent regional source for the end of the 1st or beginning of the 2nd century, the architect named in the base inscription, the 1788–1790 restoration by Giannini, and electrification in 1927.
- UNESCO Multimedia Archives, *Casting Light Through the Ages: Tower of Hercules*: https://www.unesco.org/archives/multimedia/document-1400. Supports *Farum Brigantium*, the late 1st century, 55 m on a 57 m rock, three levels, and the uniqueness claim. (The WHC list page `whc.unesco.org/en/list/1312` returned 403 to WebFetch.)

## Overlay

> UN FARO ROMANO  
> QUE SIGUE  
> EN SERVICIO

> Torre de Hércules · A Coruña · s. I–II

Visible notice printed by the overlay (`--aviso`): `ESCENA GENERADA · NO ES UNA FOTOGRAFÍA`

The subtitle carries a century range, not a single year, because the sources do not agree on an exact construction year. The place label in the subtitle is the only place text in the piece: it is printed by code, never generated in the image.

`lab.py render` values: `--titular "UN FARO ROMANO|QUE SIGUE|EN SERVICIO"`, `--subtitulo "Torre de Hércules · A Coruña · s. I–II"`, `--aviso "ESCENA GENERADA · NO ES UNA FOTOGRAFÍA"`. For stories (9:16), leave the lower quarter clear if a native location sticker will be placed there in variant B.

## Caption draft — Facebook / Instagram

En A Coruña hay un faro que Roma levantó entre finales del siglo I y comienzos del II, y que todavía hoy funciona como señal marítima: la Torre de Hércules.

Una inscripción en la roca de su base la dedica a Marte Augusto y nombra a Cayo Sevio Lupo, arquitecto de Aeminium, la actual Coímbra. En 1788, Carlos III autorizó restaurarla; el ingeniero Eustaquio Giannini envolvió el núcleo romano en la fachada de piedra que vemos hoy, sin derribarlo. La Autoridad Portuaria mantiene su luz blanca, con un alcance de 23 millas náuticas.

En 2009 entró en la Lista del Patrimonio Mundial. Para la UNESCO es el único faro de la Antigüedad grecorromana que conserva, en buena medida, su estructura y su función.

Imagen generada para este experimento: escena editorial, no fotografía del monumento. Fuentes: Concello da Coruña, Autoridad Portuaria de A Coruña, Turismo de Galicia y UNESCO.

#SabiduriaDeBolsillo #TorreDeHercules #ACoruña #HistoriaDeRoma

## Caption draft — Threads

En A Coruña, Roma levantó entre finales del siglo I y comienzos del II un faro que todavía funciona: la Torre de Hércules. Su inscripción nombra a Cayo Sevio Lupo, arquitecto de la actual Coímbra. En 1788 se restauró sin derribar el núcleo romano. Patrimonio Mundial desde 2009.

Imagen generada; no es una fotografía del monumento.

## Do not use

- Do not say it has worked without interruption for 2,000 years or «nunca se apagó»: the Concello's Castro de Elviña page says it was abandoned in the early Middle Ages and rebuilt later. Say only that it works today.
- Do not give a single construction year or attribute it firmly to Trajan: sources range from the Flavian era (69–96) to the beginning of the 2nd century, and one attributes it to Trajan while another places it before him.
- Do not say it is «el faro más antiguo del mundo» without qualification; use UNESCO's wording (the only lighthouse of Greco-Roman antiquity keeping structural integrity and functional continuity) or «faro romano que sigue en servicio».
- Do not present Gaius Sevius Lupus as the certain sole builder beyond what the inscription says; the spelling also varies (Sevius / Servius). The caption uses «Cayo Sevio Lupo», as on the Concello page.
- Do not repeat the Hercules and Geryon legend, the Breogán legend or the Brigantia origin myth as fact.
- Do not give a total height different from UNESCO's 55 m; do not mix it up with the focal plane (49 m) or the rock (57 m). The captions omit height.
- No check-in, no «estoy aquí», no phone GPS location, no «cerca de ti» suggestions, no private or approximate places; a native tag only for the exact public place `Torre de Hércules`.
- Do not present the generated image as a photograph of the tower, nor its details (lantern, windows, surroundings) as documentary evidence.
- Do not invent signs, plaques, inscriptions or place labels inside the image; the only place text is the printed overlay.
- Do not add nearby elements that have not been verified (sculptures, compass roses, lawns, walkways, city buildings).

## Image-generation prompts

Built-in image generation, `historical-scene`. No text requested in-image; the Spanish headline, place label and generated-scene notice are applied deterministically with `lab.py render` (`render_overlay.py`). One accepted image serves the 9:16 stories (CELL-121/122/124/125) and the Threads feed (CELL-123/126).

### Direction A — recognizable place, generated editorial scene

```text
Use case: historical-scene
Asset type: Sabiduría de Bolsillo social editorial, portrait master for 9:16 story and 4:5 feed crops
Primary request: Create a place-led editorial scene of the Torre de Hércules, the Roman lighthouse still in service on a rocky headland at the entrance of A Coruña harbour, Galicia, Spain.
Scene/backdrop: a windswept Atlantic headland at blue hour; the tower stands on a high granite rise above the open ocean, with dark rocks, low coastal grass and a restless sea below; distant horizon only, no modern city in frame.
Subject: the tower as a solid, sober stone lighthouse, square in plan, rising in three progressively smaller levels, with a restrained neoclassical granite exterior crossed by a subtle ascending diagonal band, topped by a small lantern emitting a single clear white beam across the sea.
Style/medium: premium editorial landscape photography with documentary restraint; physically plausible architecture, stone texture and light; not fantasy, not a postcard.
Composition/framing: vertical portrait, tower in the lower-middle area slightly right of centre, beam crossing toward the left, generous quiet sky across the upper third for a later Spanish headline; lower quarter calm (rocks and sea) so a native location sticker can sit there; crop-safe for 9:16 and 4:5.
Lighting/mood: deep blue dusk with a last warm glow on the horizon; cool granite, bright white lamp; calm, enduring, curious.
Color palette: deep Atlantic blue, slate granite, sea-foam white, restrained amber horizon.
Text (verbatim): none.
Constraints: no readable text, no signs, no plaques, no inscriptions, no place names, no maps, no logos, no watermark; one tower only; plausible scale and proportions; no people; no boats close enough to show markings.
Avoid: round or striped modern lighthouse, candy-cane stripes, castle battlements, ruins, Greek temple features, fantasy glow, fireworks, modern buildings or cranes, sculptures, compass roses, walkways, tourists, drones, lens flare text artifacts, garbled writing.
```

Result: pending generation.

## Assets and decisions

- Pendiente de generación por encargo.
- Visual QA must check: no generated text or pseudo-letters, tower read as square and three-level (not a modern striped lighthouse), headline space clear, lower quarter usable for a sticker in 9:16, and the notice `ESCENA GENERADA · NO ES UNA FOTOGRAFÍA` legible on the master.
- Native tag outcome per cell (tag offered by exact name / `location_not_offered`) is recorded in each run's `location_treatment` and `capability_evidence`, never inferred.
