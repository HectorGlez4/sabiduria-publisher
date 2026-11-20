# Reels narrados: entorno de voz

La voz de producción es Kokoro (`em_santa`, español, velocidad 0,95), que `labkit/narrado_voz.py`
lanza a través de `hyperframes tts`. Necesita un entorno de Python 3.12 propio, sin comitear
(`experiments/media-lab/.venv-voz`). Con Python 3.14 falla con un error de `phontab` que no se
encuentra. Desde la raíz del repo:

```
uv venv --python 3.12 experiments/media-lab/.venv-voz
uv pip install --python experiments/media-lab/.venv-voz/bin/python kokoro-onnx soundfile
npx --yes hyperframes@0.9.70 telemetry disable
```

Los modelos se descargan solos la primera vez en `~/.cache/hyperframes/tts`.

Comprobación rápida:

```
cd experiments/media-lab && ../../.venv/bin/python -c "
from pathlib import Path
from labkit.narrado_voz import sintetizar
print(sintetizar('Esta frase no es de Viktor Frankl.', Path('/tmp/prueba-voz.wav')))"
```

Debe imprimir una duración entre 1,5 y 3,5 s. `say -v Paulina -r 165` existe solo como motor de
pruebas y de último recurso (`motor="say"`).

## Construir un reel narrado

Tres pasos, uno por llamada, con salida JSON (desde la raíz del repo, con `.venv/bin/python`):

```
experiments/media-lab/lab.py narrado elegir
experiments/media-lab/lab.py narrado construir --pieza ID [--motor kokoro|say]
experiments/media-lab/lab.py narrado revisar --pieza ID --veredicto PASS|FAIL
```

- `elegir` da la primera pieza elegible (`candidatas.json`, cita verificada, una por cita, nunca una ya
  registrada) y crea su carpeta.
- `construir` lee `narrados/ID/guion.json` y deja todo en `narrados/ID/build/` (se vacía entera nada más empezar cada corrida, antes de leer el guion):
  `ID.mp4`, `hoja.jpg` (una captura por escena) e `informe.json` (`ok`, `fase`, `problemas`, `duracion`,
  `veredicto`). El primer paso que falla detiene la corrida y su causa queda en el informe; sale con código 2.
- `revisar` anota el veredicto de quien mira `hoja.jpg` y escucha el mp4. Solo funciona sobre un informe
  `ok`; cualquier cosa distinta de `PASS` lo marca como inservible.

Qué comprueba `construir`, en orden: el guion contra la pieza (años, nombres, cita, estructura); que todos los
nombres propios estén aprobados; la voz de cada frase; `hyperframes check` (errores, zona segura, texto bajo
el mínimo); el render; el audio del mp4 (25–40 s, sin silencios de más de 1,2 s mientras se habla, −17…−15
LUFS, pico ≤ −1,5 dB); y la ida y vuelta: Whisper transcribe el mp4 y debe decir exactamente el guion.

### Aprobar un nombre

Antes de construir, cada nombre propio de la voz necesita una entrada en `narrados/pronunciacion.json` con
`aprobado_por` y `fecha` rellenos. Lo hace una persona, después de escuchar cómo lo dice la voz con su
`dicho`; nunca se rellena por código. Sin eso, `construir` se detiene antes de sintetizar y lista los nombres.

### Escribir un `guion.json` (para el agente que lo redacta)

- La única fuente es el `core` de la pieza (`hook`, `body`, `question`, `quote`): nada que la pieza no diga.
  Ningún año ni nombre propio nuevo.
- Los años van en cifras en `voz` («en 1888»); quien sintetiza los lee en palabras.
- Entre 5 y 7 escenas, una frase por escena. Debe haber una `cita` con el texto exacto de `core.quote.text`
  y una `pregunta` como última escena; `tachado` solo en falsas atribuciones.
- `pantalla` lleva solo lo que se ve; `voz` solo lo que se dice. El `pieza` del guion es el id superviviente
  de la cita en `candidatas.json`.
