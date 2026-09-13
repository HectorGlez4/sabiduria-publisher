# LAB-PERSON-002 · 88 filas para cambiar de frecuencia

- Campaign day: 2
- Family: generated person + sparse headline
- Image batch: I01, fictional-presenter versus object-led control
- Seed: `content/published/2026-09-07-extra88.json`
- Controlled variables: same factual core, headline, palette, lighting and crop target.
- Changed variable: presence of one explicitly fictional presenter.

## Verified factual core

US patent 2,292,387, *Secret Communication System*, names Hedy Kiesler Markey and George Antheil as equal coinventors. It was filed on 10 June 1941 and granted on 11 August 1942. The document describes synchronized frequency changes and a player-piano-style paper roll with eighty-eight longitudinal rows of perforations and eighty-eight carrier frequencies.

Sources retained from the verified seed:

- Patent US2292387A: https://patents.google.com/patent/US2292387A/en
- National Inventors Hall of Fame, Hedy Lamarr: https://www.invent.org/inductees/hedy-lamarr
- National Inventors Hall of Fame, George Antheil: https://www.invent.org/inductees/george-antheil
- National WWII Museum: https://www.nationalww2museum.org/war/articles/hedy-lamarrs-wwii-invention-helped-shape-modern-tech

## Overlay

> 88 FILAS  
> PARA CAMBIAR  
> DE FRECUENCIA

> Lamarr + Antheil · 1942

The face-led version also carries the visible label `PRESENTADORA FICTICIA`.

## Caption draft — Facebook / Instagram

En 1941, Hedy Kiesler Markey y George Antheil presentaron una patente para un sistema de comunicación secreto: transmisor y receptor cambiarían de frecuencia de forma sincronizada. El documento proponía un mecanismo inspirado en los rollos perforados de las pianolas y mencionaba 88 filas y 88 frecuencias portadoras. La patente US 2.292.387 se concedió el 11 de agosto de 1942.

No inventaron el wifi ni el bluetooth. Su trabajo fue un antecedente técnico del espectro ensanchado por salto de frecuencia.

La mujer de la imagen es una presentadora ficticia generada para este experimento; no representa a Hedy Lamarr. Escena editorial original, no fotografía histórica. Fuentes: patente US 2.292.387, National Inventors Hall of Fame y National WWII Museum.

#SabiduriaDeBolsillo #HedyLamarr #GeorgeAntheil #HistoriaDeLaTecnologia

## Caption draft — Threads

En 1941, Hedy Kiesler Markey y George Antheil presentaron una patente para que transmisor y receptor cambiaran de frecuencia de forma sincronizada. El mecanismo mencionaba un rollo perforado con 88 filas y 88 frecuencias portadoras.

No inventaron el wifi: fue un antecedente técnico.

Presentadora ficticia generada; no representa a Hedy Lamarr. Escena editorial, no foto histórica.

## Do not use

- Do not say Lamarr invented Wi-Fi or Bluetooth.
- Do not reduce Antheil to a secondary helper.
- Do not claim the Navy confiscated or classified the patent.
- Do not describe generated equipment, paper perforations, maps or labels as documentary evidence.
- Do not identify the fictional presenter as Lamarr, a witness or a real expert.

## Image-generation prompts

Built-in image generation, `ads-marketing`. No text was requested in-image; the Spanish overlay and fictional-presenter disclosure were applied deterministically with `render_overlay.py`.

### Direction A — fictional presenter

```text
Use case: ads-marketing
Asset type: Sabiduría de Bolsillo social editorial, portrait master for 4:5 and 9:16 crops
Primary request: Create the face-led direction for a controlled comparison about the 1941–1942 frequency-hopping patent by Hedy Kiesler Markey and George Antheil.
Scene/backdrop: a carefully reconstructed early-1940s radio engineering workroom or museum-like technical archive, with vacuum-tube radio equipment and a generic long punched-paper roll suggesting a player-piano mechanism.
Subject: one clearly fictional present-day female museum educator, adult, expressive and intelligent, holding the punched-paper roll and inviting curiosity; she is not Hedy Lamarr, not a historical witness, and must not resemble a recognizable celebrity.
Style/medium: premium editorial photography with subtly cinematic historical atmosphere, believable skin and hands, documentary restraint rather than advertising gloss.
Composition/framing: vertical portrait, educator placed in the lower-right/middle area, radio apparatus and paper roll visible, generous quiet negative space across the upper third for a later Spanish headline; crop-safe for 4:5 and 9:16.
Lighting/mood: warm tungsten work light with cool teal shadows, thoughtful and intriguing.
Color palette: deep teal, warm brass, cream paper, restrained amber.
Text (verbatim): none.
Constraints: no readable patent text, no numbers, no logos, no watermark; paper perforations may be schematic but physically plausible; historically plausible equipment; anatomically correct hands; no implication that the presenter is Hedy Lamarr; one person only.
Avoid: celebrity likeness, 1950s or modern electronics, Wi-Fi symbols, smartphones, futuristic holograms, glamorized pin-up styling, fake archival labels, extra fingers, garbled writing.
```

Result: accepted as the publishable face-led candidate after deterministic disclosure. Face, hands and headline space passed visual review.

### Direction B — object-led control

```text
Use case: ads-marketing
Asset type: Sabiduría de Bolsillo social editorial, object-led control for a 4:5 and 9:16 crop comparison
Primary request: Create the object-led direction for the exact same controlled comparison about the 1941–1942 frequency-hopping patent by Hedy Kiesler Markey and George Antheil.
Scene/backdrop: a carefully reconstructed early-1940s radio engineering workroom or museum-like technical archive.
Subject: no person; a generic long punched-paper player-piano roll passing through a plausible mechanical reader beside vacuum-tube radio equipment, with two analog tuning assemblies suggesting synchronized frequency changes.
Style/medium: premium editorial photography with subtly cinematic historical atmosphere, physical realism and documentary restraint.
Composition/framing: vertical portrait, paper roll and apparatus across the lower and middle area, generous quiet negative space across the upper third for a later Spanish headline; crop-safe for 4:5 and 9:16.
Lighting/mood: warm tungsten work light with cool teal shadows, thoughtful and intriguing.
Color palette: deep teal, warm brass, cream paper, restrained amber; match the paired face-led direction.
Text (verbatim): none.
Constraints: no readable patent text, no numbers, no logos, no watermark; perforations must look physically plausible but need not encode real data; historically plausible equipment; no human figure.
Avoid: Wi-Fi symbols, smartphones, futuristic holograms, modern electronics, fake archival labels, garbled writing, decorative fantasy machinery.
```

Result: retained as a comparison candidate but not publishable. Small simulated instrument labels violate the no-garbled-writing gate and the machinery must not be read as a reconstruction of the actual patent apparatus.

## Assets and decisions

- Publishable presenter master: `assets/LAB-PERSON-002/hedy-patent-fictional-presenter-4x5.jpg`, SHA-256 `5ca7bfcbb9a376388ada1b9fcb0919484928cfe334765f0bad218c7cf15e90f6`.
- Object control candidate: `assets/LAB-PERSON-002/hedy-patent-object-control-4x5.jpg`, SHA-256 `c7198bc84eeb9e8766723eacb74d7d4dcfffd6498ae73fa40d6e812307f599be`.
- The object control is not eligible for public release in its current form.
- No focused repair was requested in this batch; it remains available only for internal quality comparison.
