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
  `tachado` solo en falsas atribuciones. La primera escena es la portada del Reel: todo su texto está en
  pantalla desde el primer fotograma, y por eso no puede ser un `contraste`.
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

## Publicar desde el móvil

La primera publicación real se hace con el usuario mirando. Todos los comandos se lanzan desde la raíz del repo, uno
por línea: ningún `;`, `&&`, `||` ni `$?` (una ejecución desatendida se cuelga con comandos compuestos). Cada paso del
móvil imprime JSON y su código de salida dice qué hacer.

```
.venv/bin/python experiments/media-lab/lab.py narrado elegir
.venv/bin/python experiments/media-lab/lab.py narrado construir --pieza ID
.venv/bin/python experiments/media-lab/lab.py narrado revisar --pieza ID --veredicto PASS
.venv/bin/python experiments/media-lab/lab.py lock-tomar --dueno narrado --nuevo
.venv/bin/python experiments/media-lab/lab.py narrado subir --pieza ID
.venv/bin/python experiments/media-lab/lab.py narrado abrir --pieza ID
.venv/bin/python experiments/media-lab/lab.py narrado pie --pieza ID
.venv/bin/python experiments/media-lab/lab.py narrado publicar --pieza ID
git add experiments/media-lab/narrados/registro.jsonl
git commit -m "narrado: registro de ID compartido" -- experiments/media-lab/narrados/registro.jsonl
.venv/bin/python experiments/media-lab/lab.py narrado verificar --pieza ID
git add experiments/media-lab/narrados/registro.jsonl
git commit -m "narrado: registro de ID verificado" -- experiments/media-lab/narrados/registro.jsonl
git log -1 --stat
.venv/bin/python experiments/media-lab/lab.py lock-soltar --dueno narrado
```

El push solo cuando el usuario lo diga.

Si `lock-tomar` sale con 3, para y avisa al usuario: otro ciclo tiene el teléfono. Con el móvil bloqueado o con otra
cuenta activa de Instagram, para y avisa al usuario: no desbloquees ni cambies de cuenta.

La forma `git commit -m "…" -- <registro>` comitea solo esa ruta: si `git status` muestra otros archivos en el índice
(staged), se quedan como estaban. Tras el segundo commit, `git log -1 --stat` debe mostrar solo
`narrados/registro.jsonl`; si muestra algo más, para y avisa al usuario.

- `elegir` solo hace falta si no hay pieza escogida; `revisar --veredicto PASS` lo dice una persona (o el revisor
  visual) tras mirar `hoja.jpg` y escuchar el mp4: no se escribe por inercia.
- Tras `publicar` la línea de `narrados/registro.jsonl` existe pero **no está comiteada** y solo protege cuando lo
  está (y empujada): comitea ANTES de `verificar`, y otra vez después. Si `publicar` salió con 2 o con 1 y
  `git status` muestra `narrados/registro.jsonl` modificado, comitéalo igual con la forma segura de arriba (la línea
  bloquea la cita aunque no se pulsara). Si el archivo no existe, sáltate `git add` y el commit. Los pasos
  del móvil no ejecutan git: otro proceso comitea en este checkout.
- El cerrojo lo toma esta guía, nunca el paso. Todos los pasos del móvil (incluido `limpiar`) se niegan, con salida 2,
  si el cerrojo no es de `narrado` o lleva más de 90 minutos. Se suelta tras `verificar` con salida 0 (y tras
  `descartar`). Tras un `verificar` con salida 3 **NO se suelta** hasta que el usuario haya mirado el teléfono: con él
  suelto, el bucle del sitio podría cerrar Instagram a mitad de una subida.
- El cerrojo de la ventana dice QUIÉN tiene el teléfono, no QUÉ proceso: **no impide un segundo terminal** que corra
  los mismos pasos. Lo único que impide dos `publicar` a la vez es el cerrojo del registro
  (`narrados/.registro.lock`, fuera de git): el segundo se niega en el acto, sin esperar, y no pulsa. Aun así, una sola
  terminal por pieza.
- Los pasos del móvil tardan: `publicar` 1–2 minutos (incluidos 30 s vigilando tras el toque) y `verificar` hasta
  6 minutos (3 de plazo y un límite duro de 6). Cada paso se lanza con `timeout: 600000` y
  **nunca en segundo plano**: si se corta durante la vigilancia, el aviso «Désactiver et partager» queda sin contestar.
- La carpeta de evidencia (capturas y volcados) es `evidence/android/NARRADO-ID/`.
- `publicar` no admite más opción que `--pieza`: no hay `--force` ni `--si`. Además exige que el estado sea «listo».

### Códigos de salida

| Código | Significa | Qué hacer |
|---|---|---|
| 0 | El paso hizo lo suyo (`verificar` «verificado», `descartar` sin problemas, `limpiar` con `borrado: true`; `publicar` si volvió normal) | Seguir con el siguiente comando. Tras `publicar`, 0 no prueba que saliera: lo decide `verificar` |
| 1 | Error imprevisto (el JSON trae `error`; antes era un traceback) | No sigas: mira el estado con `cat experiments/media-lab/narrados/<pieza>/build/movil.json` y el registro, y avisa al usuario; nunca repitas `publicar` |
| 2 | Negativa o mal uso: cerrojo ajeno, estado que no toca, `NoPublicar`, id no válido, `ValueError` | Leer `error` / `motivos`; no insistir hasta entender la causa |
| 3 | El paso terminó pero una persona debe mirar: `verificar` «incierto», `descartar` con `problemas`, `limpiar` con `borrado: false` | Mirar el teléfono y el JSON (`problemas`); no repetir a ciegas; no publicar. Tras `verificar`: ver «Después de un «incierto»» y no soltar el cerrojo |
| 4 | Pantalla inesperada, otra cuenta o error del teléfono (hay captura en la carpeta de evidencia) | Mirar la captura; resolver a mano o `descartar`; no seguir con el siguiente paso |

### Qué dice cada negativa (salida 2)

| Mensaje | Qué significa |
|---|---|
| «el cerrojo de la ventana no es de «narrado»: lo tiene nadie / sitio / manual / programada» | Falta `lock-tomar --dueno narrado --nuevo`, o otro ciclo tiene el teléfono. Si dice «abandonado» llevaba más de 90 minutos: se retoma con `lock-tomar --nuevo`. Si dice «con hora futura (reloj desajustado)», avisa al usuario |
| «exige --pieza con un id válido» | El id lleva `/`, `..`, espacios o está vacío |
| «publicar exige el estado «listo»» | Falta `subir`, `abrir` o `pie`, o se descartó: repetir lo que falte |
| `NoPublicar` («ya se compartió», «ya hay un registro de esta cita», pie o vídeo distintos…) | `publicar` se negó sin tocar nada; no se vuelve a compartir. Si hay un motivo de pie o vídeo, `descartar` y repetir |
| «no se puede publicar» / «no se vuelve a subir» (`subir`) | La cita ya tiene registro o este build ya se compartió: no se reconstruye ni se vuelve a subir |

### Qué se puede repetir

- `subir`: si no se compartió nada (estado `subido` o anterior, o `descartado`).
- `abrir` y `pie`: después de `descartar` (hay que volver a `subir`, `abrir` y `pie` en orden).
- `publicar`: NUNCA otra vez. Si la salida fue rara, `verificar` decide; si no se sabe, una persona mira el perfil.
- Una reconstrucción tras «compartido» se rechaza: esa cita no se vuelve a subir.
- `descartar` es la salida de cualquier paso anterior a `publicar`: deja Instagram sin el borrador y borra el vídeo
  del teléfono. Tras «compartido», «verificado» o «incierto» se niega: eso es cosa de `verificar`.
- `limpiar` borra el vídeo de prueba que `verificar` conservó (todo «incierto» lo conserva, y un «verificado» si vio
  la barra de subida). Se niega (salida 2, con los minutos que faltan) hasta 15 minutos después de compartir; córrelo
  además solo sin el banner «Partage sur…» en el perfil: si no, cortaría la subida.

### Dónde se detiene el código a propósito

- Otra cuenta activa en Instagram: se detiene (salida 4, `CuentaAjena`); no cambia de cuenta.
- Teléfono bloqueado: se detiene; nunca lo despierta ni lo desbloquea.
- El plazo de verificación es de 3 minutos: si en ese tiempo no hay +1 publicación y el pie correcto, `verificar`
  devuelve «incierto» (salida 3) y conserva el vídeo. Pasados 6 minutos en total (límite duro, también a mitad de una
  lectura) acaba «incierto» con «tiempo máximo de verificación agotado».
- Una pantalla que no es la esperada: salida 4 con captura; nunca reintenta por su cuenta.

### Después de un «incierto»

La cita queda bloqueada a propósito: ningún paso la desbloquea.

1. Para y avisa al usuario. No corras `publicar` ni `subir` otra vez, y no sueltes el cerrojo.
2. El usuario mira el perfil de la marca en el teléfono: ¿salió el Reel? ¿el número de publicaciones subió en uno?
3. Si salió: no hay nada más que hacer salvo `limpiar` más tarde (15 minutos o más después de compartir y sin el
   banner «Partage sur…» en el perfil). Luego se suelta el cerrojo.
4. Si NO salió: el usuario cierra el compositor a mano en el teléfono («atrás» hasta la hoja «Enregistrer le
   brouillon ?» y luego «Recommencer»). La cita sigue bloqueada hasta que el usuario borre a propósito las líneas de
   esa cita en `narrados/registro.jsonl` con un editor de texto y lo comitee. Esa fricción es intencionada: borrar la
   línea a mano es la única forma, y el código nunca lo hace.
