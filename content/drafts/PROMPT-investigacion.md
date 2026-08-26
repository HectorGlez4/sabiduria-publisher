# PROMPT-investigacion.md

Lo lee `.github/workflows/preparar-borradores.yml` y sustituye `{{FRANJA}}` y `{{PIEZAS}}` antes
de pasárselo a `claude -p`. Editar aquí cambia lo que hacen las tres ejecuciones diarias.

---

Estás dentro del repo `sabiduria-publisher`, rama `main`. Franja de esta ejecución: **{{FRANJA}}**.
Investiga y escribe **{{PIEZAS}}** piezas nuevas.

## Antes de escribir nada

Lee, en este orden:

1. `content/schema.json` — el contrato de la unidad de contenido. Manda sobre cualquier cosa que
   diga este prompt.
2. `content/drafts/LEEME.md` — las reglas de la carpeta.
3. `src/variants.py` — para ver qué deriva el código a partir de `core`. Todo lo que derive
   `variants.py` **no se escribe a mano**.
4. Los nombres de archivo de `content/published/` y `content/queue/` — son los ids ocupados.

## Reglas que no se negocian

- `"status": "draft"`. Sin `publish_at`. Sin `results`.
- El `id` es `AAAA-MM-DD-{manana|tarde|noche}` y **es el nombre del archivo**. No puede coincidir
  con ningún id de `content/published/` ni de `content/queue/`: esos ids son la clave del
  historial y sobrescribir uno borra una publicación real. Las franjas libres empiezan en
  `2026-09-02-manana`. Toma siempre la siguiente libre en orden cronológico.
- **No escribas copy por plataforma.** Solo `core`: `hook`, `body`, `question`. Los textos de
  Facebook, Instagram, Threads, X y LinkedIn los deriva `src/variants.py`. Si te ves escribiendo
  algo con etiquetas o adaptado a una red, estás fuera del contrato.
- `sources`: mínimo una entrada por afirmación, con la afirmación exacta que sostiene cada
  fuente. Sin fuente, la pieza no se publica.
- Lo que circule sobre el tema pero esté disputado o sea falso va en `do_not_use`, con el motivo.
  Nunca en `core.body`. Es memoria institucional: impide que una sesión futura reintroduzca un
  error ya cazado.
- **No escribas en `content/queue/` ni en `content/published/`.** Solo en `content/drafts/`.

## Cómo trabajar

1. Elige {{PIEZAS}} temas distintos para la franja **{{FRANJA}}**:
   - `manana` → figura histórica, curiosidad o dato olvidado, arte y ciencia
   - `tarde` → citas, de autores y tradiciones distintas entre sí
   - `noche` → civilizaciones, mitología, filosofía aplicada
2. Comprueba **antes de investigar** que ninguno repite tema, figura o cita presente en
   `content/published/`, `content/queue/` o `content/drafts/`. Repetir es el fallo más caro.
3. Verifica con búsqueda web. Mínimo tres fuentes independientes y de calidad: institución,
   museo, universidad, edición crítica. Para citas la exigencia es mayor: obra, capítulo o
   sección, y año de la edición. Si la frase solo aparece en páginas de citas, descártala y
   busca otra.
4. Escribe primero `do_not_use`, con lo que encontraste y hay que evitar. Después `core`.
5. **Escribe cada archivo en cuanto lo termines**, antes de empezar el siguiente. Si te quedas
   sin turnos, es mejor dejar dos piezas completas que {{PIEZAS}} a medias.

## Voz

Español neutro latinoamericano. Tono reposado, ligeramente solemne. Frases cortas. Sin emojis,
sin exclamaciones, sin lenguaje motivacional. Siempre un dato concreto —fecha, cifra, nombre—.
`question` es una sola pregunta abierta y breve; nunca pide comentar ni compartir.

## Al terminar

Un resumen de una línea por pieza: id, pilar, sujeto y número de fuentes. Si algún tema no llegó
a verificarse, dilo. **No inventes que se verificó.** El commit lo hace el workflow, no tú.
