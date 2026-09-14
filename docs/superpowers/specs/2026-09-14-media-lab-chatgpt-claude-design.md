# Laboratorio de medios: ChatGPT genera, Claude publica

Fecha: 2026-09-14 · Estado: diseño aprobado en conversación, pendiente de revisión escrita.

## Objetivo

Repartir el laboratorio (`experiments/media-lab/`) entre los dos agentes instalados en el Mac:

- **ChatGPT / Codex** genera imágenes y las guarda en el repo.
- **Claude** decide qué se genera y gestiona toda la publicación: teléfono Android (Samsung SM-S721B, serie `R5CXB1AWYNF`) y API (workflows de GitHub del laboratorio).

Motivo: el plan de Claude tiene muchos más tokens, y hoy la automatización de Codex hace todo el trabajo, teléfono incluido.

Criterio de éxito: durante una semana de ventanas programadas, el teléfono solo lo toca Claude y ninguna celda sale sin PASS de QA visual. Además, cada publicación del laboratorio registra la producción cercana en su run, y cada imagen publicada tiene un encargo con origen, hash y estado `usado`.

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Quién encarga cada imagen | Claude: elige la celda, verifica los datos y escribe prompt, pie y restricciones. |
| Automatización de Codex `media-lab-hasta-1-octubre` | Se mantiene con el mismo horario (10:10, 15:10 y 20:10, hasta el 1 de octubre), pero **solo genera**. |
| Ruta API | La lleva Claude, que lanza los workflows con `gh`. |
| Ritmo de Claude | 3 ventanas diarias (10:40, 15:40 y 20:40, hora de Madrid) y hasta 2 celdas por ventana. |
| Autocompartido Instagram → Facebook | Se deja activo. Cada copia en Facebook se registra como publicación extra y en esa ventana no sale otra celda de Facebook. |
| Colisión con producción | **No frena** (decisión del usuario, 2026-09-14): se publica aunque producción esté subiendo o acabe de publicar, y la producción cercana se anota en el run como factor de confusión. |
| Enfoque | Híbrido: cola de encargos atendida por la automatización de Codex, más una generación de rescate con `codex exec` si una ventana no tiene imágenes listas. |
| Cambio del prompt de Codex | Claude lo escribe en un archivo y el usuario lo pega en el editor de la automatización en la app de ChatGPT. Claude no edita `~/.codex/automations/*/automation.toml`. |

## 1. Arquitectura y papeles

| Pieza | Quién | Hace | No hace nunca |
|---|---|---|---|
| Encargos | Claude | Escribe `experiments/media-lab/encargos/<id>.json` a partir de celdas de `coverage.json` | — |
| Generación programada | Codex (10:10, 15:10 y 20:10) | Genera los encargos en `pedido` y guarda imagen, hash y estado | Publicar, usar `adb`, lanzar workflows, editar `coverage.json`, runs o `progress.md` |
| Generación de rescate | Claude, vía `codex exec` | Un encargo por ventana cuando no hay nada `generado` o `aprobado` | Saltarse un bloqueo vigente de Codex |
| Publicación | Claude (10:40, 15:40 y 20:40) | Comprobación previa, QA independiente, teléfono o API, verificación y registros | Publicar sin PASS |
| Punto de entrada | `experiments/media-lab/lab.py` | Todos los pasos de encargos, teléfono, API y comprobación previa como subcomandos | Borrar o cancelar publicaciones: eso sigue siendo manual con `media-lab-cancel` |

Los dos agentes solo se comunican mediante los archivos de encargos.

## 2. Encargos

Ruta: `experiments/media-lab/encargos/<encargo_id>.json`. Identificador: `ENC-AAAAMMDD-NNN`.

### Campos que escribe Claude

- `encargo_id`, `creado_en`, `coverage_cell_ids[]`, `family_id`
- `brief_path` y `do_not_use[]`
- `formato`: formato nativo y tamaño final, por ejemplo `feed_single_image` a 1080×1350 o story a 1080×1920
- `variantes` (1–2)
- `prompt` y `restricciones[]`. La imagen generada **no lleva texto**: Claude lo superpone después con `render_overlay.py` o `src/render/quote_card.py`, porque la tipografía generada falla (caso Hedy/objeto rechazado).
- `destino_assets`: carpeta bajo `experiments/media-lab/assets/<family_id>/`
- `max_intentos`: 2

### Campos que escribe quien genera

- `estado`, `lock_owner` (`codex-heartbeat` o `codex-exec`) y `lock_expira` (ahora + 30 min)
- `imagenes[]`: `ruta`, `sha256`, `ancho`, `alto`, `origen`, `generado_en`
- `intentos[]`: número, resultado y notas

### Campos que escribe solo Claude al revisar

- `revision`: `aprobado` o `rechazado`, motivo, `revisado_en`
- `runs[]`: los `run_id` en los que se publicó

### Estados

```
pedido → generando → generado → aprobado → usado
                         └→ rechazado → pedido  (mientras intentos < max_intentos)
                                     └→ bloqueado (al agotar intentos)
```

Reglas:

- Solo se puede tomar un encargo en `pedido`, o en `generando` con `lock_expira` vencido.
- Nadie edita un encargo con bloqueo vigente que no sea suyo.
- `aprobado`, `rechazado`, `usado` y `bloqueado` los pone solo Claude. Un `bloqueado` se anota en `progress.md`.
- La vuelta de `rechazado` a `pedido` también la hace Claude, en la misma revisión, añadiendo al `prompt` o a `restricciones[]` la corrección que motivó el rechazo. Codex nunca reencola.

## 3. Ventana de publicación de Claude

Tarea programada `sabiduria-media-lab`, cron `40 10,15,20 * * *` (hora local de Madrid). El mismo flujo sirve para una sesión manual.

1. **Cerrojo.** Crear `experiments/media-lab/.ventana.lock`. Si existe y tiene menos de 90 min, terminar sin hacer nada.
2. **Fecha.** A partir del 2026-10-02, no publicar y avisar al usuario de que desactive la tarea.
3. **`lab.py preflight`:**
   - teléfono en estado `device`, despierto y sin pantalla de bloqueo;
   - versiones de las apps;
   - GitHub accesible;
   - **producción cercana (solo informativo)**: anotar si `publicar` o `hilos` están en curso y las publicaciones de producción publicadas o programadas (`content/queue/*.json`, `publish_at`) a menos de 21 min. **No frena la publicación**: se registra como factor de confusión en el run.
4. **Reposición:**
   - Si no hay encargos `generado` o `aprobado` para las celdas elegibles, `lab.py generar --encargo <id>` (máximo uno por ventana).
   - Crear encargos nuevos hasta que haya como máximo 6 en `pedido` o `generando` para la automatización de Codex. Nunca más de 6.
5. **Revisión de imágenes nuevas.** Claude examina cada `generado` (verosimilitud, sin texto espurio ni defectos) y lo marca `aprobado` o `rechazado`.
6. **Selección.** Hasta 2 celdas elegibles, en el orden de `coverage.json`: la segunda difiere de la primera en red o ruta. La segunda sale al menos 21 min después de la primera.
7. **Máster.** Texto superpuesto determinista, sha256 y artefacto registrado. Para el teléfono, `lab.py telefono subir` con comprobación del hash en el dispositivo. Para API, manifiesto en `manifests/`.
8. **Composición nativa** (teléfono):
   - identidad de marca visible;
   - recorte correcto;
   - música elegida en la app en toda foto y en todo vídeo sin pista;
   - pie pegado con `phone_clipboard.py` y releído exacto;
   - cerrar el desplegable de hashtags.
   - **La evidencia final es `screencap`**, nunca un volcado de `uiautomator`, porque puede ir con retraso.
9. **QA visual.** Agente independiente con las rutas de captura, el máster, el pie y `visual-qa-gate.md`. Exige PASS explícito. El revisor solo comprueba que no haya texto ni imagen cortados o tapados, y no hay confirmación humana antes de publicar (decisión del usuario, 2026-09-14). Ante FAIL, corregir y repetir una vez; si vuelve a fallar, saltar la celda y registrarlo.
10. **Publicación.** Repetir `preflight` justo antes para anotar la producción cercana en el run, sin esperar. En el teléfono, pulsar Compartir; por API, `gh workflow run media-lab -f manifest=<ruta>` y después `media-lab-verify`.
11. **Verificación:**
    - URL o ID, identidad, audiencia pública y música en la publicación en directo;
    - una copia automática de Instagram en Facebook se registra en `cross_posting` del run, sin contarla como celda.
12. **Registros:**
    - run JSON, `coverage.json`, encargo pasado a `usado` y `progress.md`;
    - capturar las métricas que venzan (24 h, 72 h, 7 d, unas 6 h y antes de caducar en Stories).
13. **Commit y aviso.** Commit de las rutas propias (sección 4C). Avisar solo de publicación verificada, bloqueo o fallo.

### Errores

- **Teléfono ausente, bloqueado o con cuenta equivocada:** saltar las celdas de teléfono y seguir con API, métricas o encargos.
- **Envío ambiguo:** conciliar contra la plataforma antes de reintentar. Nunca reintentar por la otra ruta.
- **`codex exec` falla o supera 10 min:** registrar el intento; la ventana sigue sin esa celda.
- **Pantalla inesperada en la app:** captura, registro y abandono del borrador sin pulsar nada más. Nunca pulsaciones a ciegas.

## 4. Codex, rescate y commits

### A. Prompt de la automatización de Codex (solo generación)

Claude lo redacta en `experiments/media-lab/codex-heartbeat-prompt.md`. El usuario lo pega en la app. Contenido obligatorio:

- Leer `encargos/` y tomar hasta 2 en `pedido`, los más antiguos primero, con bloqueo.
- Generar con la generación de imágenes integrada y guardar en `destino_assets/<encargo_id>-v<n>.png`, registrando sha256 y dimensiones. Marcar `generado` o anotar el intento fallido.
- Comitear **solo** esos encargos e imágenes con el prefijo `media lab codex:` y hacer push (sección 4C).
- Prohibido publicar, usar `adb`, lanzar workflows o editar `coverage.json`, runs, manifiestos o `progress.md`.
- Sin encargos pendientes, terminar en silencio.

### B. Rescate: `lab.py generar --encargo <id>`

- Ejecuta `/Applications/ChatGPT.app/Contents/Resources/codex exec -C <repo> -s workspace-write --output-schema <esquema> -o <resultado>` con un prompt de un solo encargo y un límite de 10 min.
- Claude no se fía del mensaje final: comprueba que el archivo existe y que el hash y las dimensiones coinciden antes de marcar `generado` con origen `codex-exec`.

### C. Commits

- **Propiedad de rutas:**
  - Codex: imágenes generadas y campos de generación de los encargos.
  - Claude: todo lo demás del laboratorio (encargos, `coverage.json`, runs, manifiestos, `progress.md`, scripts).
  - Producción: `content/` y `docs/feed.xml`. Nadie más.
- `git add` solo con rutas explícitas, nunca `-A`.
- Antes de subir: `git fetch origin main`, `git rebase origin/main` y `git push origin HEAD:main`.
- Si el rebase entra en conflicto: `git rebase --abort`, dejar el commit en local, avisar y reintentar en la siguiente ventana. Nunca `reset --hard`: hay documentos sin seguimiento del usuario en el árbol.
- Prefijos: `media lab codex:` y `media lab claude:`.

## 5. Ejecución desatendida, pruebas y puesta en marcha

### A. Permisos (`.claude/settings.local.json`)

Se añaden:

- `Bash(.venv/bin/python experiments/media-lab/lab.py *)`. Todo `adb`, scrcpy y `codex exec` va dentro de `lab.py`.
- `Bash(gh workflow run media-lab*)`
- `Bash(gh run view *)`
- `Bash(git add experiments/media-lab/*)`
- `Bash(git fetch origin main)`
- `Bash(git rebase origin/main)`
- `Bash(git rebase --abort)`
- `Bash(git push origin HEAD:main)`

`git commit *` y `gh run list:*` ya están permitidos. Una orden no autorizada deja colgada la ejecución desatendida; ya ha pasado dos veces en otra rutina de este repo.

La tarea programada solo corre con la app de Claude abierta. Si está cerrada, corre al abrirla, así que la producción cercana se anota siempre en el momento de ejecutar, nunca a la hora nominal.

### B. Pruebas

**Automáticas (pytest, `tests/`):**

- máquina de estados de encargos y vencimiento de bloqueos;
- comprobación de colisión con cola y ejecuciones de producción de ejemplo;
- selección de hasta 2 celdas con la separación de 21 min;
- generación de manifiestos API;
- serialización de SET_CLIPBOARD de `phone_clipboard.py` contra los bytes del test de scrcpy 4.1.

**Sondas supervisadas, sin publicar:**

1. `codex exec` genera una imagen de un encargo de prueba y la guarda en la ruta pedida.
2. `lab.py telefono` compone un borrador de Instagram, lo captura y sale sin compartir.
3. Una ventana completa con el usuario presente antes de activar el calendario.

### C. Orden de puesta en marcha

1. Claude redacta el prompt de solo generación y el usuario lo pega en la automatización de Codex. Con `encargos/` vacío, Codex queda en reposo y deja de publicar.
2. Comitear los archivos pendientes del laboratorio: `phone_clipboard.py`, `assets/LAB-QUOTE-001/` y `runs/LAB-QUOTE-001-INSTAGRAM.json`.
3. `lab.py`, encargos y pruebas automáticas.
4. Sonda de `codex exec` y sonda del teléfono sin publicar.
5. Permisos.
6. Ventana supervisada.
7. Crear la tarea programada `sabiduria-media-lab`.
8. Actualizar `PLAN.md`, `START-HERE.md`, `schedule-preflight.md` y `progress.md` con el nuevo reparto.

## Riesgos conocidos

- `codex exec` con generación de imágenes sin interfaz no está probado: la sonda 1 lo decide. Si no funciona, el rescate queda desactivado y el sistema funciona con la cola atendida por la automatización de Codex (enfoque A).
- `phone_clipboard.py` depende del protocolo interno de scrcpy 4.1. Una actualización de Homebrew puede romperlo, y el test de bytes lo detectaría.
- La interfaz de las apps cambia sin aviso (Instagram en francés en este teléfono). Los scripts localizan los controles por texto o descripción y se detienen si no los encuentran.
- MaaS360 limita la pantalla a 120 s. Depende del LaunchAgent `com.sabiduria.medialab.phone-awake`, y un reinicio del teléfono exige un desbloqueo manual.
- Dos publicaciones por ventana, la copia automática en Facebook y las coincidencias con producción elevan la carga de audiencia; todo queda registrado como factor de confusión.
- El CDN raw de GitHub cachea unos 5 min: `publish_api.py` compara el sha256 del asset descargado con el del manifiesto y no publica si difieren, así que un reintento con la imagen corregida puede tener que esperar a la caché.
- Un encargo no comprueba que sus celdas compartan relación de aspecto: el prompt de la ventana prohíbe mezclar feed y story en un mismo encargo.
