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
- `construir` lee `narrados/ID/guion.json` y deja todo en `narrados/ID/build/` (borra primero el
  `informe.json` anterior y vacía la carpeta entera nada más empezar cada corrida, antes de leer el guion):
  `ID.mp4`, `hoja.jpg` (una captura por escena) e `informe.json` (`ok`, `fase`, `problemas`, `duracion`,
  `cita_tiempos`, `sha256_mp4`, `sha256_guion`, `veredicto`). El primer paso que falla detiene la corrida y
  su causa queda en el informe; sale con código 2. Desde Python, `salida` solo puede ser una carpeta
  `build` dentro de `narrados/ID/` o una carpeta dentro de la temporal del sistema, y nunca una que
  contenga `guion.json` o `.git`; cualquier otra cosa (o un id con `/` o `..`) es un ValueError antes de
  tocar el disco.
- `revisar` anota el veredicto de quien mira `hoja.jpg` y escucha el mp4. Solo funciona sobre un informe
  `ok`, y antes de anotar nada recalcula el sha256 del mp4 y de `guion.json`: si falta el mp4 o alguno
  cambió desde la construcción, se niega y hay que volver a construir. Cualquier cosa distinta de `PASS`
  marca el informe como inservible.

Qué comprueba `construir`, en orden: el guion contra la pieza (años, nombres, cifras, cita, pregunta,
estructura); la tabla de pronunciación (fase `pronunciacion`); que todos los nombres propios estén
aprobados; la voz de cada frase; que la narración dure 25–40 s (fase `tiempos`, antes de renderizar);
`hyperframes check` (errores, zona segura, texto bajo el mínimo); el render; el audio del mp4 (25–40 s, sin
silencios de más de 1,2 s mientras se habla, −17…−15 LUFS, pico ≤ −1,5 dB); y la ida y vuelta: Whisper
transcribe el mp4 y debe decir exactamente el guion. Solo en la posición de un nombre escrito con
mayúscula se admite otra palabra, y debe parecerse (≥ 0,6) al nombre o a su `dicho` aprobado.
`cita_tiempos` dice si las palabras de la cita entran con los tiempos de Whisper (`transcritos`) o
repartidas por igual porque Whisper no dio las mismas palabras (`repartidos`).

### Aprobar un nombre

Antes de construir, cada nombre propio de la voz necesita una entrada en `narrados/pronunciacion.json` con
`aprobado_por` y `fecha` rellenos. Lo hace una persona, después de escuchar cómo lo dice la voz con su
`dicho`; nunca se rellena por código. Sin eso, `construir` se detiene antes de sintetizar y lista los nombres.

La tabla solo admite nombres: cada clave empieza por mayúscula, cada entrada es un objeto y su `dicho` no
está vacío. Una clave en minúscula («no»), un `dicho` vacío o una entrada que no es un objeto paran
`construir` en la fase `pronunciacion`; la tabla nunca reescribe una palabra ordinaria.

### Qué cuenta como nombre

Una palabra con mayúscula que no abre frase es un nombre. Una que abre frase (tras `.`, `!`, `?`, `…`, `:`,
`¿`, `¡`, o al principio de la cadena) es:

1. ordinaria, si está en la lista cerrada de palabras funcionales (`FUNCIONALES` en
   `labkit/narrado_guion.py`: artículos, demostrativos, pronombres, preposiciones, conjunciones,
   interrogativos y adverbios como «no», «ya», «hoy», «también»);
2. si no, un nombre, si aparece con mayúscula sin abrir frase en la pieza o en otra parte del guion;
3. si no, ordinaria, si la pieza la trae en minúscula;
4. si no, un problema: reformula la frase o usa palabras de la pieza.

La misma regla decide qué nombres necesitan aprobación, cuáles reescribe la voz y dónde tolera la ida y vuelta.

### Escribir un `guion.json` (para el agente que lo redacta)

- La única fuente es el `core` de la pieza (`hook`, `body`, `question`, `quote`): nada que la pieza no diga.
  Ningún año ni nombre propio nuevo, ni en la voz ni en ningún texto de pantalla.
- Los años van en cifras («en 1888») y deben estar en la pieza; quien sintetiza los lee en palabras.
  Cualquier otro número se escribe con letras: «cuarenta veces», «veintiún años», «el noventa y nueve por
  ciento»; nada de «40», «1.500», «99 %» ni «12º».
- Entre 5 y 7 escenas, una frase por escena. Debe haber una `cita` y una `pregunta` como última escena;
  `tachado` solo en falsas atribuciones.
  `texto` es una escena de texto llano (`pantalla.texto`, una frase corta): sirve para partir una frase larga en dos.
- La `voz` y la `pantalla.texto` de la `cita` dicen `core.quote.text`, y las de la `pregunta`,
  `core.question`, palabra por palabra y en el mismo orden (en la voz se puede añadir puntuación para la
  entonación). La pantalla de la cita repite el texto exacto.
- `pantalla.nombre` lleva solo los nombres, tal como están en la pieza: nada de comentarios («el plagiario»).
- Cada texto de `pantalla` pasa los mismos controles que la `voz` (años, cifras, nombres, `do_not_use`).
- `pantalla` lleva solo lo que se ve; `voz` solo lo que se dice. El `pieza` del guion es el id superviviente
  de la cita en `candidatas.json`.

## Ritmo y ganchos

- `informe.json` lleva `avisos`: notas de ritmo que no frenan el build (gancho que acaba pasados 3 s, frase de más de 5 s, última línea sin eco del gancho). Reglas en `labkit/narrado_ritmo.py`.
- [ganchos.md](ganchos.md): menú de fórmulas para la primera frase y qué dicen los datos propios.
- `labkit/atipicos.py` ordena publicaciones por su múltiplo sobre la mediana de la cuenta (≥ 3× es señal, < 1,5× es ruido). Los datos se leen a mano del perfil; no hay rastreador.
