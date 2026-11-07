Trabaja en el repo /Users/hec/dev/sabiduriaPublisher. Eres un ciclo del bucle «sitio → Instagram»: una cita al azar de sabiduriadebolsillo.net sale en Instagram como publicación del feed, Reel y Story, cada una con su diseño al azar y un sonido al azar del top 10 de «Populaires». La receta, con lo que se ve en cada pantalla, está en experiments/media-lab/historias-y-reels-desde-el-sitio.md: léela si dudas.

## Reglas que no se rompen
- Solo usa estos comandos: `.venv/bin/python experiments/media-lab/lab.py …`, `git add experiments/media-lab/sitio-instagram/registro.jsonl`, `git commit …`, `git fetch origin main`, `git rebase origin/main`, `git rebase --abort`, `git push origin HEAD:main`. Ejecuta cada comando SOLO y exactamente con esa forma: nunca `; …`, `&& …`, `|| …`, `|`, `>`, `2>&1`, `cd …`, variables ni subshells. Un comando compuesto abre un permiso que nadie contesta y deja el ciclo colgado. Para leer capturas usa Read.
- Códigos de salida de `lab.py`: 0 correcto; 2 argumentos inválidos (corrige la llamada); 4 pantalla inesperada o error del teléfono (ver «Si algo falla»).
- Nunca publiques sin `VERDICT: PASS` de un revisor independiente. El sticker de enlace de la Story **nunca** tapa la cita, la atribución ni la firma (decisión del usuario).
- Nunca pulses nada a ciegas: tras cada paso abre su `captura` con Read y confirma lo que dice la columna «ver».
- No despiertes ni desbloquees el teléfono. Si un paso dice que no está listo, termina el ciclo (paso 5).
- Nunca termines un mensaje esperando algo ni dejes nada en segundo plano: la sesión se cerraría sin publicar ni soltar el cerrojo.

## Pasos
1. `lab.py lock-tomar --dueno sitio --nuevo`. Si `cerrojo` es false (sale con 3), otro ciclo o ventana usa el teléfono: termina con una línea de informe, sin soltar el cerrojo (no es tuyo).
2. `lab.py sitio elegir`. Anota `run`, `slug`, `url` y `plantillas` (una por formato).
3. Para cada formato, en este orden: `reel`, `feed`, `story` (el Reel primero: es el que llega a gente nueva, unas 130 cuentas por Reel frente a unas 6 de la foto o la Story). Llama RUN_F al `run` con el formato detrás (`SITIO-…-FEED`, `-REEL`, `-STORY`). Antes de cada formato, `lab.py lock-tomar --dueno sitio`; si devuelve `cerrojo: false`, salta al paso 5.

   | Paso | Comando | ver |
   |---|---|---|
   | a | `lab.py sitio compartir --run RUN_F --superficie F --url URL --plantilla P` (P = `plantillas.F`) | El editor de Instagram con la tarjeta de la cita: cuadrada en el feed, a pantalla completa en Reel y Story. Anota `pie`. |
   | b | `lab.py sitio musica --run RUN_F --superficie F` | La misma tarjeta, sin sticker de música encima. Anota `pista.titulo`. |
   | c (story) | `lab.py sitio enlace --run RUN_F --superficie story --url URL` | El sticker «LEER LA CITA» en un hueco libre, sin tocar ningún texto. |
   | c (feed, reel) | `lab.py sitio pie --run RUN_F --superficie F --pie PIE` (PIE = el `pie` del paso a) | El composer con el pie entero, sin teclado ni desplegable abiertos. |

   d. QA: lanza un agente independiente **en primer plano** (herramienta Agent, `run_in_background: false`) y espera su respuesta en este mismo turno. Dile, con estas palabras, que **solo puede usar Read y que no ejecute ningún comando** (ni Bash ni `python3 -c`). Pásale experiments/media-lab/visual-qa-gate.md y las capturas de a, b y c de este formato. Que compruebe solo que no hay texto ni imagen cortados o tapados; en la Story, además, que el sticker no toca la cita, la atribución ni la firma. Exige que termine con `VERDICT: PASS` o `VERDICT: FAIL`. Si es FAIL, no publiques ese formato: aplica «Borrador abierto» y sigue con el siguiente formato. Si la herramienta Agent responde que el revisor sigue en segundo plano, **no toques el teléfono ni descartes nada**: su veredicto llega como notificación en este mismo turno; espéralo y sigue con él (el 7 nov un ciclo descartó un Reel con PASS por no esperar, y al rehacerlo perdió la música).

   e. `lab.py sitio publicar --run RUN_F --superficie F --veredicto PASS --slug SLUG --pista "TITULO"`. Abre `captura`. Si sale con 4, **no repitas**: puede haber salido. Pasa directamente a f.

   f. `lab.py sitio verificar --run RUN_F --superficie F --pista "TITULO"` (en feed y reel añade `--pie PIE`). Si sale con 4, anótalo en el informe («publicado sin verificar»), pero no lo republiques.

4. Si quedó publicado al menos un formato: `git add experiments/media-lab/sitio-instagram/registro.jsonl`, `git commit -m "sitio a instagram: SLUG"`, `git fetch origin main`, `git rebase origin/main` y `git push origin HEAD:main`. Si el rebase falla, `git rebase --abort` y dilo en el informe.
5. `lab.py lock-soltar --dueno sitio`.

## Si algo falla
- **Borrador abierto** (un 4 en a, b o c, o un FAIL del revisor): Instagram tiene un editor a medias. Sal con `lab.py telefono-atras --app instagram --run RUN_F --nombre salida-N` mirando cada captura. Cuando la captura muestre el diálogo «Recommencer ?» o «Abandonner la photo ?», `lab.py telefono-descartar --app instagram --run RUN_F --nombre descarte`. Si no lo consigues en tres «atrás», para el ciclo (paso 5) y dilo en el informe: el siguiente ciclo encontraría el editor abierto.
- `SinHueco` en el paso c de la Story: la cita es demasiado larga para el sticker. Descarta el borrador como arriba y termina el ciclo con la Story sin publicar; no la publiques sin enlace.
- Un 4 con `CuentaAjena`: Instagram tiene activa otra cuenta, no @sabiduriabolsillo. No cambies de cuenta ni toques más el teléfono (paso 5); ponlo en la primera línea del informe para que el usuario la devuelva.
- Un 4 con `TelefonoNoListo`, `SinVolcado` o `TelefonoError` (por ejemplo «device not found»: el teléfono se desconectó del USB): no toques más el teléfono en este ciclo (paso 5) y dilo en la primera línea del informe para que el usuario lo reconecte.

## Informe
Una línea por formato: formato, diseño, pista, resultado (publicado y verificado / publicado sin verificar / no publicado y por qué). Si quedó un borrador abierto, ponlo lo primero.
